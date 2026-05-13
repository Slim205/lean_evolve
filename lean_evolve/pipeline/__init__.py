from abc import ABC, abstractmethod

from lean_evolve.stores import Store, Solution
from lean_evolve.mutate import Mutator
from lean_evolve.evaluation import Rater, Rating
from lean_evolve.utils import log,apply_search_replace
from typing import Any
from lean_evolve.models.llm_utils import GLOBAL_LLM_CALLS
from lean_evolve.models.llm_utils import completion
from lean_evolve.evaluation.prompts import HINT_PROMPT
from lean_evolve.evaluation.lean_utils import extract_search_replace_blocks
import time


class Pipeline:
    """
    Base class for a pipeline.
    """

    def __init__(
        self,
        store: Store,
        mutator: Mutator,
        rater: Rater,
        max_budget: Any,
        is_inspiration,
    ):
        self.store = store
        self.mutator = mutator
        self.rater = rater
        self.max_budget = max_budget
        self.is_inspiration = is_inspiration

    def run(self) -> Solution | None:
        """
        Run the pipeline.
        """
        attempt = self.store.get_attempt()

        log.info(f"Current attempt : {attempt}")
        change = True
        # while True :
        while GLOBAL_LLM_CALLS.summary()["calls"] < self.max_budget:
            attempt += 1
            log.info(
                f"Current budget : {GLOBAL_LLM_CALLS.summary()['calls']}/{self.max_budget}"
            )
            current_budget = GLOBAL_LLM_CALLS.summary()["calls"]

            start = time.perf_counter()

            tau = 1.

            # if change : 
            #     solution = self.store.sample(method="ucb", k=attempt, tau=tau)

            # solution = self.store.sample(method='random')
            
            # solution = self.store.get_program(18)
            c = len(self.store.get_all_programs()) -1

            solution = self.store.get_program(c)
            max_children = 15
            while c > 0 and (solution.get_score() < 0 or self.store.get_n_visits(solution) >= max_children or len(self.store.get_children(solution)) >= 4 ):
                c-=1
                solution = self.store.get_program(c)

            if self.store.get_n_visits(solution) >= max_children or solution.get_score() < 0 or len(self.store.get_children(solution)) >= 4 :
                log.info('Stop mutation.')
                return None, attempt

            if not self.is_inspiration:
                inspiration = solution
                log.info(f"Start Mutation : Program {solution.id()}")
            else:
                log.info(
                    f"Start Mutation : Program {solution.id()} | Inspiration : {inspiration.id()} "
                )

            # inspiration = self.store.get_program(8)

            start_time = time.time()
            try:                

                mutated_solution: Solution = self.mutator.mutate(
                    solution, inspiration=inspiration
                )

                log.info("Mutation Completed")
                rating = self.rater.rate(mutated_solution)
                log.info("Rating Completed")

                mutated_solution.set_rating(rating)
                if rating.is_correct:
                    return mutated_solution, attempt

                # sketch = mutated_solution.sketch()
                # errors = mutated_solution.get_errors()

                mutated_solution = self.store.add(mutated_solution)
                log.info("Insertion into store Completed")

                # if False : 
                # if errors : 
                #     log.info('Creating Lean Hints !')
                #     PROMPT = HINT_PROMPT.format(
                #         sketch=sketch, error_message=errors
                #     )
                #     hints = completion(PROMPT)
                #     solution.set_hints(hints)

                self.store.describe()

                log.info(GLOBAL_LLM_CALLS.summary())
                self.store.set_attempt(attempt)
                failed = False


            except Exception as e:
                log.error(f"Attempt FAILED : {e}")
                self.store.update_failed_attempts(
                    {
                        "program_id": solution.id(),
                        "attempt": attempt,
                        "budget": GLOBAL_LLM_CALLS.summary()["calls"] - current_budget,
                    }
                )
                failed = True


            end_time = time.time()
            log.info(f"Mutation process took {end_time - start_time:.3f} seconds")
            elapsed = time.perf_counter() - start
            mutation_budget = GLOBAL_LLM_CALLS.summary()["calls"] - current_budget
            mutation_history = {
                "program_id": solution.id(),
                "attempt": attempt,
                "time": elapsed,
                "budget": mutation_budget,
                "failed": failed,
                "temperature": tau,
                "inspiration": inspiration.id(),
            }
            self.store.update_history(mutation_history)
            # return None, attempt
        return None, attempt
