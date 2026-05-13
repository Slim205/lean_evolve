from __future__ import annotations
from dataclasses import dataclass

from lean_evolve.evaluation import Rating, Rater
from lean_evolve.stores.program import Program
from lean_evolve.evaluation.prover import run_prover

from lean_evolve.evaluation.extractor import extract_goal, llm_extractor, extract_parser
from lean_evolve.evaluation.lean_utils import get_sketch_errors
from lean_evolve.evaluation.prompts import REVIEWER_SYSTEM, REVIEWER_PROMPT,EVAL_MUTATION
from lean_evolve.models.llm_utils import completion
from lean_evolve.utils import log


@dataclass
class ProgramRating(Rating):
    """
    Rating for a Lean Program solution.
    """

    fitness: float
    n_errors: int
    succeeded_subgoals: int
    total_subgoals: int
    failed_lemma_str : str

    @property
    def is_correct(self) -> bool:
        # Criterion: no Lean errors and all subgoals solved.
        return (
            self.n_errors == 0  # We remove solutions having lean errors.
            and self.total_subgoals > 0
            and not self.failed_lemma_str # this is correct for solutions having lean errors.
            # and self.succeeded_subgoals == self.total_subgoals
        )


class ProgramRater(Rater):
    """
    Rater that knows how to evaluate a Program (Lean sketch).
    """

    def __init__(
        self,
        N_prover=4,
        verif_batch=16,
        extractor="extract_goal",
        re_extract=False,
    ):
        self.N_prover = N_prover
        self.verif_batch = verif_batch
        self.extractor = extractor
        self.re_extract = re_extract

    def is_correct(self, rating: Rating) -> bool:
        if not isinstance(rating, ProgramRating):
            raise TypeError(f"ProgramRater expected ProgramRating, got {type(rating)}")
        return rating.is_correct

    def rate(self, solution: Program,review_only=False) -> ProgramRating:
        """
        Run all the Lean + prover machinery and return raw evaluation stats.
        """
        if not review_only : 
            error_message = get_sketch_errors(
                solution.sketch(), solution.data["formal_statement"].replace("sorry", "")
            )

            solution.set_errors(error_message)

            n_succeeded, total, n_trivial = 0, 0, 0

            if not error_message:

                if self.extractor == "lemma_style":
                    extractor = extract_parser()
                    theorem_list = extractor.extract_goals(
                        solution, re_extract=self.re_extract
                    )
                    # sorry_count = extractor.count_sorry_tokens(solution.sketch())

                    # if len(theorem_list) != sorry_count:
                    #     error_message = "ERROR from : glue theorem/lemma contains `sorry`—only standalone subgoal lemmas may end with `sorry` (body = exactly `by sorry`), glue must be `sorry`-free and only assemble previously proved lemmas."
                    #     solution.set_errors(error_message)
                    # elif extractor.verif_duplicated_signature(theorem_list):
                    #     error_message = "ERROR from : Do NOT “decompose” by adding an auxiliary lemma with a (near-)identical statement and making the original proof just `exact/simpa/refine` that auxiliary;"
                    #     solution.set_errors(error_message)

                    # else:
                    n_succeeded, total, failed, n_trivial = run_prover(
                        solution.subgoals_path,
                        solution.eval_subgoals_path,
                        solution.data["name"],
                        n=self.N_prover,
                        verif_batch=self.verif_batch,
                        timeout=60,
                        remove_trivial=False,
                    )
                    solution.set_failing_subgoals(failed)

                else:
                    extractor = extract_goal()
                    extractor.extract_goals(solution, re_extract=self.re_extract)

                    n_succeeded, total, failed, n_trivial = run_prover(
                        solution.subgoals_path,
                        solution.eval_subgoals_path,
                        solution.data["name"],
                        n=4,
                        verif_batch=self.verif_batch,
                        timeout=60,
                        remove_trivial=False,
                    )
                    solution.set_failing_subgoals(failed)

                    if len(failed) > 0:
                        extractor = llm_extractor()
                        extractor.repair_subgoals(solution, failed)
                        n_succeeded, total, failed, n_trivial = run_prover(
                            solution.subgoals_path,
                            solution.eval_subgoals_path,
                            solution.data["name"],
                            n=self.N_prover,
                            verif_batch=self.verif_batch,
                            remove_trivial=False,
                        )
                        solution.set_failing_subgoals(failed)

            n_lean_errors = max(0, len(error_message.split("ERROR from")) - 1)

            meta = solution._load_data()
            meta.update(
                {
                    "n_lean_errors": n_lean_errors,
                    "succeeded_subgoals": n_succeeded,
                    "total_subgoals": total,
                }
            )
            solution._save_data(meta)
        else :
            log.info('Reviewing only mode.')
            meta = solution._load_data()
            n_lean_errors =meta['n_lean_errors'] 
            n_succeeded=meta['succeeded_subgoals']
            total = meta['total_subgoals']

        if total == 0:
            base = 0.0
        else:
            base = n_succeeded / total

        fitness = base - n_lean_errors / 10
        
        # sketch_rating = solution.get_feedback()
        # if review_only : 
        #     solution.set_feedback(sketch_rating,replace=False)
        #     sketch_rating=''
        # if n_lean_errors == 0 and not sketch_rating : 
        #     log.info("Starting Reviewing")
        #     previous_failure = solution.get_parent_feedback()
            
        #     failed_str = solution.get_failed_subgoals_msg()
        #     reviewer_prompt = REVIEWER_PROMPT.format(
        #         sketch=solution.sketch(), failed_subgoals=failed_str,previous_failure=previous_failure,informal_proof=solution.informal_proof
        #     )
        #     sketch_rating = completion(reviewer_prompt, REVIEWER_SYSTEM)
        #     solution.set_feedback(sketch_rating)


        rating = ProgramRating(
            fitness=fitness,
            n_errors=n_lean_errors,
            succeeded_subgoals=n_succeeded,
            total_subgoals=total,
            failed_lemma_str=solution.get_failed_subgoals_msg()
        )

        solution.set_rating(rating)

        return rating
