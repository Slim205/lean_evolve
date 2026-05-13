from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import json
import shutil
from lean_evolve.utils import (
    read_jsonl,
    read_txt,
    save_txt,
    extrac_code,
    read_json,
    log,
    check_lean,
    save_jsonl,
    save_json,
    LEAN4_DEFAULT_HEADER,
    apply_search_replace,
)
from lean_evolve.evaluation.lean_utils import (
    remove_comments,
    assemble_with_default_header,
    assemble_full_sketch_from_succeeded_proofs,
    extract_search_replace_blocks,
    prune_lean_sketch,
    extract_theorem_name,
)

from lean_evolve.models.llm_utils import completion,completion_msg
from lean_evolve.evaluation.lean_utils import (
    extract_theorem_signature,
    get_sketch_errors,
)

from lean_evolve.stores.prompts import (
    sketch_prompt_template,
    system_prompt_sketch,
    USE_SKETCH_AND_THEOREMS_TO_PROVE,
    USE_SKETCH_AND_THEOREMS_TO_PROVE_REPAIR,
    system_prompt_assemble,
    META_STEP1_SYSTEM_MSG,
    META_STEP1_USER_MSG,
)
from lean_evolve.mutate.prompts import (
    PROOF_SKETCH_CORRECTION_SYSTEM,
    PROOF_SKETCH_CORRECTION_PROMPT,
)

from . import Solution

TEMP_STORAGE = Path("results/temp")
import uuid
import re


def create_random_folder() -> Path:

    # Generate a random folder name (UUID makes collisions basically impossible)
    folder_name = uuid.uuid4().hex
    new_folder_path = TEMP_STORAGE / folder_name

    # Create the folder
    new_folder_path.mkdir(parents=True, exist_ok=False)

    return new_folder_path


class Program(Solution):
    """
    A single Lean program / proof attempt.

    Implements the Solution interface so it can be used inside the pipeline.
    """

    path: Path
    data: Dict[str, Any]
    informal_proof: str

    def __init__(
        self,
        data: Dict[str, Any],
        informal_proof : str,
        path: Path = None,
        sketch="",
        parent=-1,
        max_refine=4,
        mutation_output="",
        inspiration=None,
        parent_rating="",
        old_mutation_output="",
        state="",
        history="",
        compressed_feedback=""
    ):
        self.path = path
        self.data = data
        self.informal_proof = informal_proof
        self.parent = parent
        self.max_refine = max_refine
        self.inspiration = inspiration
        self.mutation_output = mutation_output
        self.parent_rating = parent_rating
        self.old_mutation_output = old_mutation_output
        self.state = state
        self.history=history
        self.compressed_feedback=compressed_feedback
        if not self.path:
            self.path = create_random_folder()
        self.metadata_path = self.path / "metadata.json"
        self.sketch_path = self.path / "sketch.txt"
        self.error_path = self.path / "errors.txt"
        self.subgoals_path = self.path / "subgoals.jsonl"
        self.eval_subgoals_path = self.path / "eval"

        self.path.mkdir(parents=True, exist_ok=True)        
        self._create_sketch(sketch=sketch)

    def _create_sketch(self, sketch: str = ""):
        """Create the sketch for this program, unless one already exists."""

        # save_txt(self.informal_proof, self.path/ 'informal_proof.txt')
        
#         state =f"""{self.informal_proof}
# ```lean4
# {self.sketch()}
# ```"""
#         save_txt(state, self.path / "state.txt")

        # Skip generation if a sketch is already stored
        if len(self.sketch()) > 0:
            return

        if sketch == "":
            log.info("Generating new sketch.")
            prompt = sketch_prompt_template.format(
                formal=self.data["formal_statement"],
                informal_proof=self.informal_proof,
            )
            sketch = completion(prompt, system_prompt_sketch,is_response=True)
            # print(sketch)
            if "```lean" in sketch:
                sketch = extrac_code(sketch)
            
            if not sketch:
                raise ValueError("Generated sketch is empty.")

        HEADER = self.data['header']
        # log.info(HEADER)
        if not HEADER : 
            HEADER = LEAN4_DEFAULT_HEADER

        sketch = assemble_with_default_header(sketch, HEADER).strip()
        # pruned_src, kept, removed = prune_lean_sketch(sketch)

        # if len(removed) > 0 :
        #     # cc= check_lean(pruned_src)
        #     # if cc['pass'] : 
        #     log.info(f'Removing those lemmas : {removed}')

            # save_txt(sketch, self.path/'refinement/sketch_prune.txt')

            # sketch = pruned_src

            
#         if self.state:
#             save_txt(self.state, self.path / "state.txt")
#         else : 
#             state =f"""{self.informal_proof}
# ```lean4
# {sketch}
# ```"""
#             save_txt(state, self.path / "state.txt")
        if self.history:
            save_txt(self.history, self.path / "history.txt")

        if self.mutation_output:
            save_txt(self.mutation_output, self.path / "mutation_output.txt")
        if self.old_mutation_output:
            save_txt(
                self.old_mutation_output,
                self.path / "refinement/mutation_output_old.txt",
            )
        if self.compressed_feedback:
            save_txt(
                self.compressed_feedback,
                self.path / "refinement/compressed_feedback.txt",
            )
        if self.parent_rating:
            save_txt(self.parent_rating, self.path / "parent_rating.txt")

        num_refinements = 0
        error_message = get_sketch_errors(
            sketch, self.data["formal_statement"].replace("sorry", "")
        )

        if len(error_message) > 0:
            num_refinements = self.correct_error_in_sketch(sketch, error_message)
            if num_refinements == 4 and self.parent > 0: 
                self.transform_sketch(self.mutation_output,sketch)
        else:        
            # pruned_src, kept, removed = prune_lean_sketch(sketch)

            # if len(removed) > 0 :
            #     cc= check_lean(pruned_src)
            #     if cc['pass'] : 
            #         log.info(f'Removing those lemmas after refinement : {removed}')

                    # save_txt(sketch, self.path/'refinement/sketch_prune_r.txt')
                    # sketch = pruned_src

            save_txt(sketch, self.sketch_path)
        data = {
            "program_id": None,
            "parent": self.parent,
            "inspiration": self.inspiration,
            "island_id": None,
            "num_refinements": num_refinements,
            "max_refinements": self.max_refine,
            "n_iter": 0,
        }
        self._save_data(data)

    def get_informal_proof(self) :
        path = self.path / 'informal_proof.txt'
        if path.exists() : 
            return read_txt(self.path / 'informal_proof.txt')
        return ''

    def correct_error_in_sketch(self, current_sketch: str, current_errors: str) -> int:
        """
        Iteratively repairs a proof sketch using compiler errors until success or refinement limit is reached.
        """
        i = 0
        # messages=[{"role": "system", "content": PROOF_SKETCH_CORRECTION_SYSTEM}]
        while i < self.max_refine and current_errors:
            if "Trivial statements are not allowed" in current_errors or 'Mismatch between extracted subgoals and' in current_errors:
                save_txt(current_sketch, self.path / f"sketch.txt")
                save_txt(current_errors, self.path / f"errors.txt")
                # if self.parent > 0 : 
                raise ValueError(current_errors)
                # return i
            save_txt(current_sketch, self.path / f"refinement/sketch_{i}.txt")
            save_txt(current_errors, self.path / f"refinement/errors_{i}.txt")

            log.info(f"Sketch repair attempt {i + 1}/{self.max_refine}")

            try:
                prompt = PROOF_SKETCH_CORRECTION_PROMPT.format(
                    sketch=current_sketch,
                    error_message=current_errors,
                )
                # messages=[{"role": "system", "content": PROOF_SKETCH_CORRECTION_SYSTEM}]
                # messages.append( {"role": "user", "content": prompt} )

                output = completion(prompt,PROOF_SKETCH_CORRECTION_SYSTEM)
                # messages.append({"role": "assistant", "content": output})

                save_txt(output, self.path / f"refinement/ref_output_{i}.txt")

                current_sketch = apply_search_replace(output, current_sketch)
                current_errors = get_sketch_errors(
                    current_sketch, self.data["formal_statement"].replace("sorry", "")
                )


            except Exception as e:
                log.error(f"Sketch repair failed at iteration {i}: {e}")

            i += 1

        save_txt(current_sketch, self.path / "sketch.txt")
        save_txt(current_errors, self.path / f"errors_{i}.txt")

        return i

    def id(self) -> Any:
        """Return the program's numeric ID, extracted from its directory name."""
        name = self.path.name
        if "program_" in name:
            return int(name.split("program_")[1])
        return None

    def sketch(self) -> str:
        """Return the stored Lean sketch, or an empty string if none exists."""
        return read_txt(self.sketch_path) if self.sketch_path.exists() else ""

    def _load_data(self) -> dict:
        """Load metadata.json."""
        with open(self.metadata_path, "r") as f:
            return json.load(f)

    def _save_data(self, data):
        """Write metadata.json to disk."""

        with open(self.metadata_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_refinement(self):
        data = self._load_data()
        return data["num_refinements"]

    def get_parent_id(self):
        data = self._load_data()
        return data["parent"]

    def set_rating(self, rating: Any):
        """Store the rating on disk as JSON."""
        path = self.path / "rating.json"
        with open(path, "w") as f:
            json.dump({"score": rating.fitness}, f, indent=2)

    def set_calls(self, n_calls: Any) -> None:
        """Stores the number of extract-goal calls made so far."""
        data = self._load_data()
        data["n_calls"] = n_calls
        self._save_data(data)

    def get_extract_goal_calls(self) -> int:
        """Returns the number of extract-goal calls recorded."""
        data = self._load_data()
        return int(data.get("n_calls", 0))

    def get_score(self):
        """Load and return the stored rating, or None if not present."""
        path = self.path / "rating.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)["score"]

    def update_data(self, program_id, island_id):
        data = self._load_data()
        data["program_id"] = program_id
        data["island_id"] = island_id
        self._save_data(data)

    def get_subgoals(self) -> List[Dict[str, str]]:
        """Return all extracted subgoals as a list of JSON dicts."""
        path = self.path / "subgoals.jsonl"
        return read_jsonl(path) if path.exists() else []

    def get_errors(self) -> str:
        """Return the raw error log from the Lean compiler."""
        path = self.path / "errors.txt"
        return read_txt(path) if path.exists() else ""

    def get_failed_subgoals_msg(self) -> str:
        """Return a formatted string listing all failed subgoals."""
        path = self.path / "errors_subgoals.txt"
        return read_txt(path) if path.exists() else ""
        # path = self.path / "errors_subgoals.txt"
        # if not path.exists()  : 
        #     return ''
        # errors= read_txt(path) 
        # lemmas = errors.split('lemma')
        # new_message = 'lemma'.join(lemmas[:2])
        # log.info(new_message)
        # return new_message

    def set_pruned_lemmas(self,lemmas):
        previous_str = "Pruned Lemmas : \n\n" + "\n".join(sg for sg in lemmas)
        save_txt(previous_str, self.path / "refinement/pruned_lemmas.txt")
 
    def set_failing_subgoals(self, failed):
        """
        writes errors_subgoals.txt listing failed subgoals.
        """
        if failed:
            failed_str = "Failed Lemmas : \n\n" + "\n".join(sg for sg in failed)
            save_txt(failed_str, self.path / "errors_subgoals.txt")

        # if failed:
        #     pruned_src, kept, removed = prune_lean_sketch(self.sketch())
            
        #     new_failure = []
        #     if len(removed) > 0 :
        #         log.info(f'Abondant lemmas : {removed}')
        #         for theorem in failed : 
        #             theorem_name = extract_theorem_name(theorem)
        #             if theorem_name  not in removed : 
        #                 new_failure.append(theorem)

        #     previous_str = "Failed Lemmas : \n\n" + "\n".join(sg for sg in failed)
        #     save_txt(previous_str, self.path / "refinement/old_errors_subgoals.txt")

        #     if new_failure : 
        #         failed_str = "Failed Lemmas : \n\n" + "\n".join(sg for sg in new_failure)
        #         save_txt(failed_str, self.path / "errors_subgoals.txt")

    def set_subgoals(self, theorem_list: List[Dict[str, Any]]) -> None:
        """
        Stores subgoal theorems and saves their formal statements into a consolidated text file.
        """
        save_jsonl(self.subgoals_path, theorem_list)

        all_subgoals = "\n".join(
            subgoal["formal_statement"] for subgoal in theorem_list
        )
        save_txt(all_subgoals, self.path / "allsubgoals.txt")

    def set_errors(self, error_message: str) -> None:
        "Records an error message describing why Lean proof assembly failed."
        save_txt(error_message, self.error_path)

    def is_proved(self) -> bool:
        """Returns whether the current theorem has been successfully proved."""
        data = self._load_data()
        return bool(data.get("is_proved", False))

    def get_full_proof_iteration(self) -> int:
        """Returns the number of proof assembly iterations performed so far."""
        data = self._load_data()
        return data.get("n_iter", 0)

    def validate_full_proof(
        self,
        llm_output: str,
        lean_full_context: str,
        theorems_string: str,
    ) -> Tuple[bool, str, bool]:
        """
        Validates a Lean proof generated by an LLM by checking both the proof sketch and the full assembled proof.
        """

        if "lean" in llm_output:
            llm_output = extrac_code(llm_output)

        formal_statement = self.data["formal_statement"]

        full_sketch = llm_output

        if formal_statement.replace("sorry", "") not in llm_output:
            log.warning(
                "Formal statement was modified by the LLM; reconstructing theorem signature."
            )
            full_sketch = (
                extract_theorem_signature(formal_statement)
                + " := by"
                + ":= by".join(llm_output.split(":= by")[1:])
            )

        lean_code = LEAN4_DEFAULT_HEADER + lean_full_context + full_sketch
        short_lean_code = LEAN4_DEFAULT_HEADER + theorems_string + full_sketch

        save_txt(lean_code, self.path / "full_proof.txt")
        save_txt(short_lean_code, self.path / "full_sketch.txt")

        sketch_eval: Dict[str, Any] = check_lean(short_lean_code, timeout=60)
        sketch_correct = sketch_eval.get("pass", False)

        if not sketch_correct:
            log.error("Proof sketch failed to compile (even with sorry).")
            save_json(sketch_eval, self.path / "full_proof.json")
            return False, lean_code, False

        log.info("Proof sketch compiled successfully.")

        full_eval: Dict[str, Any] = check_lean(lean_code, timeout=300)

        if not full_eval.get("complete", False):
            log.error(
                "Full proof failed to compile: sketch is valid, but the assembled proof is not."
            )
        else:
            log.info("Full proof compiled successfully.")

        save_json(full_eval, self.path / "full_proof.json")

        return full_eval.get("complete", False), lean_code, sketch_correct

    def repair_full_proof(self, iteration: int) -> Tuple[str, bool]:
        """
        Repairs a previously failed Lean proof using compiler errors and re-validates the sketch and full proof.
        """

        eval_data = read_json(self.path / "full_proof.json")
        save_json(eval_data, self.path / f"Assembley/full_proof_{iteration}.json")

        full_proof_txt = read_txt(self.path / "full_proof.txt")
        save_txt(full_proof_txt, self.path / f"Assembley/full_proof_{iteration}.txt")

        full_sketch_txt = read_txt(self.path / "full_sketch.txt")
        save_txt(full_sketch_txt, self.path / f"Assembley/full_sketch_{iteration}.txt")

        previous_attempt = "theorem " + full_sketch_txt.split("theorem ")[-1]

        error_messages = []
        for error in eval_data.get("errors", []):
            if error.get("severity") == "error":
                error_messages.append(
                    f"ERROR from position {error['pos']} to {error['endPos']}:\n{error['data']}"
                )

        formatted_errors = "\n\n".join(error_messages)

        succeeded_proofs = read_json(self.eval_subgoals_path / "succeeded_proofs.json")

        lean_full_context = "\n".join(succeeded_proofs.values()) + "\n"
        theorems_string = "\n".join(succeeded_proofs.keys()) + "\n"

        prompt = USE_SKETCH_AND_THEOREMS_TO_PROVE_REPAIR.format(
            sketch=self.sketch(),
            theorems_string=theorems_string,
            errors=formatted_errors,
            attempt=previous_attempt,
        )

        llm_output = completion(prompt, system_prompt_assemble)

        is_proved, lean_code, sketch_correct = self.validate_full_proof(
            llm_output,
            lean_full_context,
            theorems_string,
        )

        run_data = self._load_data()
        run_data["is_proved"] = is_proved
        run_data["n_iter"] += 1
        self._save_data(run_data)

        return lean_code, sketch_correct == is_proved

    def generate_full_proof(self) -> Tuple[str, bool]:
        """
        Generates an initial Lean proof attempt from a sketch and validates both the proof sketch and full proof.
        """

        full_proof_path = self.path / "full_proof.txt"

        if full_proof_path.exists() and self.is_proved():
            return read_txt(full_proof_path), True

        succeeded_proofs = read_json(self.eval_subgoals_path / "succeeded_proofs.json")

        lean_full_context = "\n".join(succeeded_proofs.values()) + "\n"
        theorems_string = "\n".join(succeeded_proofs.keys()) + "\n"

        prompt = USE_SKETCH_AND_THEOREMS_TO_PROVE.format(
            sketch=self.sketch(),
            theorems_string=theorems_string,
        )

        llm_output = completion(prompt, system_prompt_assemble)

        is_proved, lean_code, sketch_correct = self.validate_full_proof(
            llm_output,
            lean_full_context,
            theorems_string,
        )

        run_data = self._load_data()
        run_data["is_proved"] = is_proved
        run_data["n_iter"] = 1
        self._save_data(run_data)

        return lean_code, sketch_correct == is_proved

    def get_full_proof_old(self, max_attempt: int = 4) -> Optional[str]:
        """
        Orchestrates Lean proof generation and iterative repair until success or exhaustion of attempts.
        """

        log.info("Assembly | Initial proof attempt (iteration 0)")

        full_proof, is_normal = self.generate_full_proof()

        if self.is_proved():
            return full_proof

        if is_normal:
            for i in range(max_attempt):
                log.info(f"Assembly | Repair iteration {i + 1}")

                full_proof, is_normal = self.repair_full_proof(i)

                if self.is_proved():
                    return full_proof

                if not is_normal:
                    log.error("Assembly aborted: repair produced an abnormal result ")
                    break

        # Mark failure with a negative rating
        rating_path = self.path / "rating.json"
        with open(rating_path, "w") as f:
            json.dump({"score": -1}, f, indent=2)

        error_msg = (
            "Lean proof assembly failed after all attempts. "
            "Neither the initial generation nor subsequent repairs produced a valid proof."
        )
        self.set_errors(error_msg)

    def get_full_proof(self) -> Optional[str]:
        """
        get full proof.
        """

        log.info("Assembly | Initial proof attempt (iteration 0)")

        full_proof_path = self.path / "full_proof.txt"

        if full_proof_path.exists() and self.is_proved():
            return read_txt(full_proof_path)

        succeeded_proofs = read_json(self.eval_subgoals_path / "succeeded_proofs.json")

        sketch = self.sketch()
        pruned_src, kept, removed = prune_lean_sketch(sketch)

        if len(removed) > 0 :
            # cc= check_lean(pruned_src)
            # if not cc['pass'] : 
                # log.error('PRUNED SKETCH IS FALSE')

            log.info(f'Removing those lemmas : {removed}')

            save_txt(pruned_src, self.path/'refinement/sketch_prune.txt')

            sketch = pruned_src
            # print(sketch)

        lean_code = assemble_full_sketch_from_succeeded_proofs(
            sketch, succeeded_proofs
        )

        lean_code = assemble_with_default_header(lean_code, self.data['header'])

        save_txt(lean_code, self.path / "full_proof.txt")

        full_eval = check_lean(lean_code, timeout=300)
        save_json(full_eval, self.path / "full_proof.json")

        is_proved = full_eval.get("complete", False)
        run_data = self._load_data()
        run_data["is_proved"] = is_proved
        self._save_data(run_data)

        if is_proved:
            return lean_code

        log.error("Lean proof assembly failed.")

    # Test functions :
    def set_hints(self, hints):

        save_txt(hints, self.path / "refinement/hint_output.txt")
        for x in hints.split('------') : 
            if 'Hint' in x : 
                hint = x.strip()
                save_txt(hint, self.path / "refinement/hints.txt")
                # feedback = self.get_feedback()
                # new_feedback = feedback + '\n\n' + hint
                # self.set_feedback(feedback,replace=False)
                # self.set_feedback(new_feedback)
                # log.info(f'Feedback for program {self.id()} has changed.')
                # log.info(hint)
                break


    # def set_subgoal_hints(self, hints ) :
    #     save_txt(hints, self.path / 'hints.txt'  )
    def set_classification_output(self, output):
        save_txt(output, self.path / "classification_output.txt")

    def get_hints(self):
        path = self.path / "refinement/hints.txt"
        if path.exists():
            return read_txt(path)
        return ""

    def get_summary(self, re_generate=False):
        path = self.path / "summary.txt"
        if path.exists() and not re_generate:
            return read_txt(path)
        log.info(f"Creating summary for program {self.id()}")

        prompt = META_STEP1_USER_MSG.format(
            sketch=self.sketch(), failed_subgoals=self.get_failed_subgoals_msg()
        )
        summary = completion(prompt=prompt, system_prompt=META_STEP1_SYSTEM_MSG)
        save_txt(summary, path)
        return summary

    def update_subgoal_data(self, new_n_calls):
        current_calls = self.get_extract_goal_calls()
        self.set_calls(current_calls + new_n_calls)
        data = self._load_data()
        data["new_calls"] = new_n_calls
        self._save_data(data)

        def safe_copy(src, dst):
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        safe_copy(self.path / "subgoals.jsonl", self.path / "old_subgoals.jsonl")
        safe_copy(self.path / "allsubgoals.txt", self.path / "old_allsubgoals.txt")
        safe_copy(
            self.path / "errors_subgoals.txt", self.path / "old_errors_subgoals.txt"
        )
        safe_copy(
            self.path / "eval/compilation_summarize.csv",
            self.path / "eval/old_compilation_summarize.csv",
        )

    def set_new_fitness(self, score):
        save_json({"score": score}, self.path / "new_rating.json")

    def get_replace_text(self) -> str:

        path = self.path / "embedding/replace_block.txt"
        # if path.exists() :
        #     return read_txt(path)

        mutation_output = read_txt(self.path / "mutation_output.txt")

        pattern = re.compile(
            r">>>>SEARCH\s*(.*?)\s*>>>>REPLACE\s*(.*?)\s*(?=(>>>>SEARCH|$))",
            re.DOTALL,
        )

        matches = pattern.findall(mutation_output)

        replace_blocks = []
        for _, replace, _ in matches:
            replace_blocks.append(replace.rstrip())

        replace = remove_comments("\n".join(replace_blocks))
        save_txt(replace, path)
        return replace

    def set_feedback(self, feedback,replace=True):

        path = self.path / "feedback.txt"
        if not replace : 
            i = 0
            while path.exists():
                # log.info(f"feedback_{i}.txt")
                path = self.path / f"feedback_{i}.txt"
                i+=1
        save_txt(feedback, path)

    def get_feedback(self):
        path = self.path / "feedback.txt"
        if path.exists():
            return read_txt(path)

        log.info("No feedback was given for this problem.")
        return ""

    def detect_bad_mutation_old(self):
        if self.get_parent_id() == -1:
            return False
        from lean_evolve.stores.utils import analyze_mutation_output

        return analyze_mutation_output(read_txt(self.path / "mutation_output.txt"))

    def detect_bad_mutation(self):
        path = self.path / "mutation_output.txt"
        if path.exists():
            from lean_evolve.evaluation.lean_utils import assert_no_duplicate_signatures

            mutation_output = read_txt(self.path / "mutation_output.txt")
            new_mutation = assert_no_duplicate_signatures(mutation_output)

            if len(new_mutation) < 0.99 * len(mutation_output):
                print(
                    f"!!!!!!!! {self.id()}.  {round(len(new_mutation)/len(mutation_output) * 100,2)}"
                )

            ### add this function in the mutation output.
            return len(new_mutation) == 0
        return False

    def verif_current_proofs(self):

        if self.get_score() > 0:
            path = partial_proof_verif, self.path / "eval/succeeded_proofs_verif.json"
            if path.exists():
                return

            succeeded_proofs = read_json(self.path / "eval/succeeded_proofs.json")
            full_theorems_str = LEAN4_DEFAULT_HEADER

            for x, y in succeeded_proofs.items():
                full_theorems_str += "\n" + y

            partial_proof_verif = check_lean(full_theorems_str, timeout=300)
            if not partial_proof_verif["complete"]:
                log.error(
                    f"Problem with this proof sketch ! Assembly will fail. Program {self.id()}"
                )

            save_txt(full_theorems_str, self.path / "eval/succeeded_proofs.txt")
            save_json(
                partial_proof_verif, self.path / "eval/succeeded_proofs_verif.json"
            )

    def set_depth(self, depth: Any) -> None:
        """Stores the number of extract-goal calls made so far."""
        data = self._load_data()
        data["depth"] = depth
        self._save_data(data)

    def get_depth(self) -> None:
        """Stores the number of extract-goal calls made so far."""
        data = self._load_data()
        if "depth" in data.keys():
            return data["depth"]
        return -1

    def select_edits(self):
        path = self.path / "refinement/mutation_output_2.txt" 
        if path.exists() : 
            log.info('Changed already.')
            return

        mutation_output = read_txt(self.path / "mutation_output.txt")
        blocks = extract_search_replace_blocks(mutation_output)
        sketch = read_txt(self.path / "refinement/sketch_0.txt")
        self.transform_sketch(mutation_output,sketch)

    def transform_sketch(self,mutation_output,sketch):
        blocks = extract_search_replace_blocks(mutation_output)
        old_sketch = sketch
        old_mut = mutation_output
        
        for i in range(len(blocks)-1):
            block = blocks[len(blocks) - 1 - i]
            sketch = sketch.replace(block["replace"], block["search"])
            res = check_lean(sketch)
            
            if res["pass"]:
                log.info(f"Attempt can be save if we remove {(i+1)}/{len(blocks)} blocks.")
                save_txt(old_sketch,self.path / "refinement/old_sketch.txt")
                save_txt(old_mut,self.path / "refinement/mutation_output_2.txt")

                save_txt(sketch,self.path / "sketch.txt")
                blocks_in =[]
                for j in range(len(blocks) - 1 - i)  : 
                    b = blocks[j]
                    blocks_in.append(
                    ">>>>SEARCH\n" f"{b['search']}\n" ">>>>REPLACE\n" f"{b['replace']}"
                )
                new_mutation_output = "\n".join(blocks_in)
                save_txt(new_mutation_output,self.path / "mutation_output.txt")

                return
                

        log.info("Nothing to change for this program.")
        return 

    def get_state(self) : 
        path = self.path / 'state.txt'
        if path.exists() : 
            return read_txt(path)
    
#     def create_state(self,informal_proof,sketch) :
#             state =f"""{informal_proof}
# ```lean4
# {sketch}
# ```"""
#             save_txt(state,self.state_path)
    def get_parent_feedback(self) :
        path = self.path / 'parent_rating.txt' 
        if path.exists() : 
            return read_txt(self.path / 'parent_rating.txt')    
        return ''
    def get_history(self) :
        path = self.path / 'history.txt' 
        if path.exists() : 
            return read_txt(self.path / 'history.txt')    
        return ''

    def set_history(self,parent_history) : 
        feedback = self.get_feedback()
        history = parent_history + "Next Feedback :\n" + feedback
        save_txt(history, self.path / 'history.txt' )

    def set_edit_feedback(self,edit_feedback) :
        save_txt(edit_feedback, self.path / 'edit_feedback.txt' )

    def get_edit_feedback(self,edit):
        path = self.path / 'edit_feedback.txt'
        if path.exists(): 
            return read_txt(path)
        return ''

    def update_score(self) :
        rating_path = self.path / "rating.json"
        with open(rating_path, "w") as f:
            json.dump({"score": -1}, f, indent=2)

    # def update_feedback(self,previous_feedback,edit_blocks) : 
    def prune_sketch(self) :
        from lean_evolve.evaluation.lean_utils import prune_lean 
        sketch = self.sketch()
        new_sketch,is_changed = prune_lean(sketch)
        if is_changed : 
            cc = check_lean(new_sketch)
            if cc['complete'] : 
                # save_txt(sketch,self.path / 'refinement/sketch_to_prune.txt')
                print('New to change this sketch.')