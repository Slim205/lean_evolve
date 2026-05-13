from abc import ABC, abstractmethod

from lean_evolve.stores.program import Program
from lean_evolve.utils import (
    process_subgoal,
    log,
    get_compilation_unit,
    check_lean,
    extract_failures_to_json,
    LEAN4_DEFAULT_HEADER,
)
from lean_evolve.models.llm_utils import completion
from typing import List, Dict, Any, Optional

from lean_evolve.evaluation.prompts import (
    EXTRACT_GOAL_SYSTEM,
    EXTRACT_SUBGOALS_FROM_SKETCH_PROMPT,
    REPAIR_GOAL_SYSTEM,
    REPAIR_EXTRACT_SUBGOALS_PROMPT,
    ERROR_CORRECTION_SYSTEM_PROMPT,
    THEOREM_CORRECTION_PROMPT,
    # CLASSIFIER_SYSTEM,
    # CLASSIFIER_USER,
    CORRECT_ALL_THEOREMS_PROMPT,
)
import re
from lean_evolve.evaluation.lean_utils import (
    extract_all_lean_blocks,
    extract_theorem_name,
    remove_import_statements,
    extract_lean_block,
    remove_comments,
    lean_signature,
    prune_lean_sketch
)

from lean_evolve.models.llm_utils import GLOBAL_LLM_CALLS
from lean_evolve.evaluation.verifier import LeanVerifier
from typing import List


class Extractor(ABC):
    """
    Base class for a rater.
    """

    @abstractmethod
    def extract_goals(self, solution: Program, re_extract=True) -> str:
        """
        Extract subgoals.
        """
        pass


_COMMENT_BLOCK_RE = re.compile(r"/-.*?-/", re.DOTALL)
_COMMENT_LINE_RE = re.compile(r"--.*?$", re.MULTILINE)


def _strip_comments(s: str) -> str:
    s = _COMMENT_BLOCK_RE.sub("", s)
    s = _COMMENT_LINE_RE.sub("", s)
    return s


def _decl_ends_with_sorry(decl_text: str) -> bool:
    t = _strip_comments(decl_text).strip()
    return re.search(r"(?:^|\s)sorry\s*$", t) is not None


def _find_decl_name(decl_text: str, kind: str) -> str:
    m = re.match(rf"^{kind}\s+([A-Za-z_][\w']*)", decl_text)
    return m.group(1) if m else ""


def _split_top_level_decls(lean_text: str) -> List[str]:
    """
    Split into chunks starting at column 0 with `lemma` or `theorem`.
    """
    start_re = re.compile(r"(?m)^(lemma|theorem)\s+")
    starts = list(start_re.finditer(lean_text))
    if not starts:
        return []
    chunks = []
    for i, m in enumerate(starts):
        s = m.start()
        e = starts[i + 1].start() if i + 1 < len(starts) else len(lean_text)
        chunks.append(lean_text[s:e].rstrip())
    return chunks


def _extract_decl_header(decl_text: str) -> str:
    """
    Return the declaration header up to (and including) ':= by' if present,
    otherwise up to the first 'by'. This is often what you want to "prove next"
    (the statement), without the full sorry-body noise.
    """
    m = re.search(r":=\s*by\b", decl_text)
    if m:
        return decl_text[: m.end()].rstrip()
    m2 = re.search(r"\bby\b", decl_text)
    if m2:
        return decl_text[: m2.end()].rstrip()
    return decl_text.strip()


class extract_parser(Extractor):

    def count_sorry_tokens(self, s: str) -> int:
        s = remove_comments(s)
        # count whole-word `sorry`
        return len(re.findall(r"\bsorry\b", s))

    def verif_duplicated_signature(self, theorems) -> bool:
        """
        Return True if there are NO duplicated Lean signatures among theorems,
        False otherwise.
        """
        signatures = [lean_signature(t["formal_statement"]) for t in theorems]
        return len(set(signatures)) != len(signatures)

    def extract_goals(self, solution: Program, re_extract: bool = True) -> List[str]:
        sketch = solution.sketch()
        pruned_src, kept, removed = prune_lean_sketch(sketch)
        
        decls = _split_top_level_decls(sketch)
        theorem_list: List[str] = []
        pruned_list=[]
        for d in decls:
            kind = d.split(None, 1)[0]  # "lemma" or "theorem"
            name = _find_decl_name(d, kind)
            if not name:
                continue

            if not _decl_ends_with_sorry(d):
                continue

            if kind != "lemma":
                continue
            if name not in removed : 
                theorem_list.append(
                    {
                        "name": name,
                        "formal_statement": _extract_decl_header(d),
                    }
                )
            else :
                pruned_list.append(_extract_decl_header(d))

        for theorem in theorem_list:
            log.info(theorem["formal_statement"])
            log.info("-" * 100)

        solution.set_subgoals(theorem_list)

        if removed : 
            log.info(f"Abundant lemmas: {removed}")
            solution.set_pruned_lemmas(pruned_list)

        sorry_count = self.count_sorry_tokens(sketch)
        goal_count = len(theorem_list) + len(pruned_list)

        if goal_count != sorry_count:
            log.error(
                "Mismatch between extracted subgoals and `sorry` tokens. "
                f"subgoals={goal_count} sorry_tokens={sorry_count}"
            )
        #             raise RuntimeError(
        #                 f"Invalid sketch: expected {goal_count} `sorry` tokens (one per subgoal), found {sorry_count}."
        #  )

        return theorem_list


class extract_goal(Extractor):

    def extract_goals(self, solution: Program, re_extract=True) -> str:
        """Run extract_goal on the sketch, save extracted subgoals, and return compiler errors."""
        sketch = solution.sketch()

        sketch = sketch.replace(":= sorry", ":= by extract_goal")
        sketch = sketch.replace("exact sorry", "exact by extract_goal")
        sketch = sketch.replace("sorry", "extract_goal")

        results = get_compilation_unit(sketch)

        theorem_list = []
        count = 0
        extracted_prefix = f"{solution.data['name']}.extracted_1"

        for msg in results["messages"]:
            data = msg["data"]

            if data.startswith("theorem"):
                name = f"subgoal_{count}"
                formal = data.replace(extracted_prefix, name).replace(
                    "extracted_1", name
                )

                theorem_list.append(
                    {
                        "name": name,
                        "formal_statement": formal,
                    }
                )
                count += 1

        solution.set_subgoals(theorem_list)
        log.debug(
            f"Extracted {len(theorem_list)} subgoals out of {len(sketch.split('sorry')) - 1}"
        )

        return theorem_list


class llm_extractor(Extractor):

    def process_subgoals(self, extracted_theorems: List[str]) -> List[Dict[str, Any]]:
        """
        Verifies, corrects, and normalizes extracted Lean subgoal theorems.
        """

        # Sanity check: exactly one theorem per string
        for theorem in extracted_theorems:
            log.info(theorem)
            log.info("-" * 100)

        # if len(re.findall(r"\s+theorem\s+", theorem)) != 1:
        #         log.error(
        #             "Invalid subgoal format: expected exactly one theorem definition."
        #         )
        # raise ValueError(
        #     "Malformed subgoal: multiple or missing theorem keywords."
        # )

        # Verify and correct Lean code
        corrected_theorems = self.verify_and_correct_lean(extracted_theorems)

        final_theorems: List[Dict[str, Any]] = []

        if corrected_theorems:
            for theorem in corrected_theorems:
                if re.search(r"\btheorem\b", theorem):
                    final_theorems.append(
                        {
                            "name": extract_theorem_name(theorem),
                            "formal_statement": remove_import_statements(theorem),
                        }
                    )
                else:
                    log.error(
                        f"Corrected output does not contain a theorem definition; skipping.\n{theorem}"
                    )

        return final_theorems

    def extract_goals(self, solution: Program, re_extract: bool = False) -> str:
        """
        Extracts Lean subgoals from a proof sketch, stores them, and returns any compiler error messages.
        """

        # Reuse existing subgoals unless forced
        if solution.get_subgoals() and not re_extract:
            log.info("Using previously extracted subgoals.")
            return ""

        # Extract subgoals only if sketch compiles
        initial_calls = GLOBAL_LLM_CALLS.summary()["calls"]

        log.info("Extracting subgoals from proof sketch.")
        prompt = EXTRACT_SUBGOALS_FROM_SKETCH_PROMPT.format(sketch=solution.sketch())
        output = completion(prompt, EXTRACT_GOAL_SYSTEM)

        extracted_theorems = extract_all_lean_blocks(output)
        final_theorems = self.process_subgoals(extracted_theorems)

        solution.set_subgoals(final_theorems)
        solution.set_calls(GLOBAL_LLM_CALLS.summary()["calls"] - initial_calls)

        return final_theorems

    def verify_and_correct_lean(self, theorems: List[str]) -> List[str]:
        """
        Verifies Lean theorems, corrects failing ones using LLM feedback, and returns the updated list.
        """

        # Prepare samples for Lean verification
        samples = []
        for i, theorem in enumerate(theorems):
            if "import Mathlib" not in theorem:
                theorem = LEAN4_DEFAULT_HEADER + theorem
                theorems[i] = theorem
            samples.append({"custom_id": str(i), "proof": theorem})

        # Run Lean verifier
        lean_verifier = LeanVerifier()
        results = lean_verifier.compile(samples)
        results.sort(key=lambda x: int(x["custom_id"]))

        corrected_theorems: List[str] = []
        theorem_to_correct = {}

        # Collect failing theorems and error messages
        for result in results:
            theorem = theorems[int(result["custom_id"])]
            if result.get("pass", False):
                corrected_theorems.append(theorem)
            else:
                error_messages = [
                    f"ERROR from position {e['pos']} to {e['endPos']}:\n{e['data']}"
                    for e in result.get("errors", [])
                    if e.get("severity") == "error"
                ]
                # error = "\n\n".join(error_messages)
                # if "has already been declared" in  error :
                #     theorem = rename_lean_theorem(theorem)
                theorem_to_correct[theorem] = "\n\n".join(error_messages)
        log.info(
            "%d/%d theorems require correction.",
            len(theorem_to_correct),
            len(results),
        )

        if len(theorem_to_correct) > 1:
            corrected_theorems.extend(
                self.correct_error_in_all_theorems(theorem_to_correct)
            )
            return corrected_theorems

        for theorem, error_message in theorem_to_correct.items():

            log.info(f"Correcting theorem : \n{theorem}\n\n{error_message}")

            new_theorem = self.correct_error_in_theorem(
                error_message=error_message,
                problem=theorem,
            )
            corrected_theorems.append(new_theorem)

        return corrected_theorems

    def correct_error_in_theorem(
        self,
        error_message: str,
        problem: str,
        max_attempt: int = 4,
    ) -> str:
        """
        Iteratively corrects syntax or semantic errors in a Lean theorem statement.
        """

        generated_statement: str = problem

        for i in range(max_attempt):
            log.info("Theorem correction attempt %d/%d", i + 1, max_attempt)

            prompt = THEOREM_CORRECTION_PROMPT.format(
                error_message=error_message,
                theorem=problem,
            )

            final_answer = completion(prompt, ERROR_CORRECTION_SYSTEM_PROMPT)
            generated_statement = extract_lean_block(final_answer)
            generated_statement = remove_import_statements(generated_statement)

            res = check_lean(generated_statement)

            error_message = ""
            for err in res.get("errors", []):
                if err.get("severity") == "error":
                    error_message += (
                        f"ERROR from position {err['pos']} to {err['endPos']}:\n"
                        f"{err['data']}\n\n"
                    )

            if res.get("pass", False):
                log.info("*" * 80)
                log.info("THEOREM CORRECTED SUCCESSFULLY:\n%s", generated_statement)
                log.info("*" * 80)
                return generated_statement

        log.error("*" * 80)
        log.error("THEOREM NOT FIXED AFTER %d ATTEMPTS", max_attempt)
        log.error("Last attempt:\n%s", generated_statement)
        log.error("Remaining errors:\n%s", error_message)
        log.error("*" * 80)

        return generated_statement

    def correct_error_in_all_theorems(
        self,
        theorem_dict: Dict[str, str],
        max_attempt: int = 4,
    ) -> List[str]:
        """
        Iteratively corrects syntax or semantic errors in multiple Lean theorems using batched LLM repair.
        """

        corrected_theorems: List[str] = []

        for attempt in range(max_attempt):
            log.info("Correction attempt %d/%d", attempt + 1, max_attempt)
            log.info("Correcting %d theorems", len(theorem_dict))

            # Build batched problem description
            problem_blocks = []
            for idx, (theorem, error) in enumerate(theorem_dict.items(), start=1):
                problem_blocks.append(
                    f"Theorem {idx}:\n```lean\n{theorem}\n```\n"
                    f"Error {idx}:\n{error}\n"
                )

            prompt = CORRECT_ALL_THEOREMS_PROMPT.format(
                problem_str="\n".join(problem_blocks)
            )

            final_answer = completion(prompt, ERROR_CORRECTION_SYSTEM_PROMPT)

            generated_statements = [
                remove_import_statements(stmt)
                for stmt in extract_all_lean_blocks(final_answer)
            ]

            # Prepare samples for Lean verification
            samples = []
            for i, theorem in enumerate(generated_statements):
                if "import Mathlib" not in theorem:
                    theorem = LEAN4_DEFAULT_HEADER + theorem
                    generated_statements[i] = theorem
                samples.append({"custom_id": str(i), "proof": theorem})

            # Verify corrected theorems
            lean_verifier = LeanVerifier()
            results = lean_verifier.compile(samples)

            # Reset remaining failures
            new_theorem_dict: Dict[str, str] = {}

            for res in results:
                theorem = generated_statements[int(res["custom_id"])]

                error_message = ""
                for err in res.get("errors", []):
                    if err.get("severity") == "error":
                        error_message += (
                            f"ERROR from position {err['pos']} to {err['endPos']}:\n"
                            f"{err['data']}\n\n"
                        )

                if res.get("pass", False):
                    log.info("*" * 80)
                    log.info("THEOREM CORRECTED:\n%s", theorem)
                    log.info("*" * 80)
                    corrected_theorems.append(theorem)
                else:
                    new_theorem_dict[theorem] = error_message
                    log.error("*" * 80)
                    log.error(f"THEOREM NOT FIXED :\n{theorem}\n{error_message}")
                    log.error("*" * 80)

            theorem_dict = new_theorem_dict

            if not theorem_dict:
                log.info("All theorems corrected successfully.")
                return corrected_theorems

        log.error("%d theorem(s) could not be fixed.", len(theorem_dict))

        corrected_theorems.extend(theorem_dict.keys())
        return corrected_theorems

    def repair_subgoals(self, solution: Program, failed_subgoals: str):

        initial_calls = GLOBAL_LLM_CALLS.summary()["calls"]
        full_theorems = solution.get_subgoals()

        failed_subgoals_msg = ""
        succes_theorems = []
        for theorem_dict in full_theorems:
            if theorem_dict["formal_statement"] not in failed_subgoals:
                succes_theorems.append(theorem_dict)
            else:
                failed_subgoals_msg += theorem_dict["formal_statement"] + "\n"
        assert len(failed_subgoals_msg) > 0
        proof_sketch = solution.sketch()
        prompt = REPAIR_EXTRACT_SUBGOALS_PROMPT.format(
            sketch=proof_sketch, failed_subgoals=failed_subgoals_msg
        )

        log.info("Start Repairing extracted subgoals.")
        output = completion(prompt, REPAIR_GOAL_SYSTEM)
        extracted_theorems = extract_all_lean_blocks(output)
        final_theorems = self.process_subgoals(extracted_theorems)
        new_n_calls = GLOBAL_LLM_CALLS.summary()["calls"] - initial_calls
        solution.update_subgoal_data(new_n_calls)

        if final_theorems:
            succes_theorems.extend(final_theorems)
            solution.set_subgoals(succes_theorems)
        else:
            solution.set_subgoals([])

    # def repair_subgoals(self, solution: Program, failed_subgoals: str):

    #     initial_calls = GLOBAL_LLM_CALLS.summary()["calls"]
    #     full_theorems = solution.get_subgoals()
    #     failed_subgoals_msg = ""
    #     for theorem_dict in full_theorems:
    #         if theorem_dict["formal_statement"]  in failed_subgoals:
    #             failed_subgoals_msg += theorem_dict["formal_statement"] + "\n"
    #     assert len(failed_subgoals_msg) > 0

    #     proof_sketch = solution.sketch()
    #     prompt = CLASSIFIER_USER.format(sketch=remove_comments(proof_sketch),failed_subgoals=failed_subgoals_msg)
    #     log.info("Start Classifying extracted subgoals.")
    #     output = completion(prompt, CLASSIFIER_SYSTEM)
    #     solution.set_classification_output(output)

    #     classification_results = extract_failures_to_json(output)

    #     sub_to_repair = {}
    #     hints = ""
    #     for result in classification_results :
    #         if result['failure_mode']=='EXTRACTION' :
    #             sub_to_repair[result['subgoal_name']] = result['recommendation']
    #         else :
    #             hints+=f"Subgoal : {result['subgoal_name']}\nRecommendation : {result['recommendation']}\n\n"

    #     solution.set_hints(hints)

    #     succes_theorems = []
    #     failed_subgoals_msg = ""
    #     for theorem_dict in full_theorems:
    #         subg_name=extract_theorem_name(theorem_dict["formal_statement"])
    #         if theorem_dict["formal_statement"] in failed_subgoals and subg_name in sub_to_repair.keys() :
    #             failed_subgoals_msg += theorem_dict["formal_statement"] + "\n" + sub_to_repair[subg_name] + '\n'
    #         else :
    #             succes_theorems.append(theorem_dict)

    #     if len(failed_subgoals_msg) > 0 :

    #         log.info(f'REPAIRING : {list(sub_to_repair.keys())}')

    #         prompt = REPAIR_EXTRACT_SUBGOALS_PROMPT.format(
    #             sketch=remove_comments(proof_sketch), failed_subgoals=failed_subgoals_msg
    #         )

    #         log.info("Start Repairing extracted subgoals.")
    #         output = completion(prompt, REPAIR_GOAL_SYSTEM)
    #         extracted_theorems = extract_all_lean_blocks(output)
    #         final_theorems = self.process_subgoals(extracted_theorems)

    #         if final_theorems:
    #             succes_theorems.extend(final_theorems)
    #             solution.set_subgoals(succes_theorems)
    #         else:
    #             solution.set_subgoals([])
    #     else :
    #         log.info(f'No Repair needed.')

    #     new_n_calls = GLOBAL_LLM_CALLS.summary()["calls"] - initial_calls
    #     solution.update_subgoal_data(new_n_calls)

    #     return len(failed_subgoals_msg) > 0
