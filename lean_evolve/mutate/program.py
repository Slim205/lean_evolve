from lean_evolve.mutate.prompts import (
    PROOF_SKETCH_CORRECTION_SYSTEM,
    PROOF_SKETCH_CORRECTION_PROMPT,
    SUBGOAL_MUTATION_SYSTEM_PROMPT,
    SUBGOAL_PROMPT_Hint,
    SUBGOAL_PROMPT,
    SUBGOAL_MUTATION_PROMPT,
    MUTATOR_PROMPT,
    MUTATOR_SYSTEM,
    MUTATE2,
)
from lean_evolve.evaluation.prompts import REVIEWER_SYSTEM, REVIEWER_PROMPT
import random
from lean_evolve.models.llm_utils import completion
from lean_evolve.evaluation.lean_utils import remove_comments, check_mutation
from lean_evolve.utils import apply_search_replace, log,extrac_code
from lean_evolve.stores import Solution
from . import Mutator
from lean_evolve.stores.program import Program


class RefineProgram(Mutator):

    def refine(self, solution: Solution):

        prompt = PROOF_SKETCH_CORRECTION_PROMPT.format(
            sketch=solution.sketch(), error_message=solution.get_errors()
        )
        output = completion(prompt, PROOF_SKETCH_CORRECTION_SYSTEM)
        updated = apply_search_replace(output, solution.sketch())
        return Program(
            sketch=updated,
            data=solution.data,
            informal_proof=solution.informal_proof,
            parent=solution.id(),
        )

    def decompose(self, solution: Program):

        failed_str = solution.get_failed_subgoals_msg()

        prompt = SUBGOAL_PROMPT.format(
            sketch=solution.sketch(),
            sketch_errors=failed_str,
            score=solution.get_score(),
        )
        output = completion(prompt, SUBGOAL_MUTATION_SYSTEM_PROMPT)

        updated = apply_search_replace(output, solution.sketch())

        return Program(
            sketch=updated,
            data=solution.data,
            informal_proof=solution.informal_proof,
            parent=solution.id(),
            mutation_output=output,
        )

    # def mutate_plan(self,solution : Program) : 
    #     pass
    def compress(self,feedback: str) -> str:
        ss = feedback.split('---------')

        incorrect = [x.strip() for x in ss if 'INCORRECT' in x]
        if incorrect:
            return "\n---------\n".join(incorrect)

        for x in ss:
            x = x.strip()
            if 'HARD' in x:
                return x

        log.error('INCORRECT FEEDBACK')
        

    def decompose_reviewer(self, solution: Program):

        sketch = solution.sketch()
        new_history= ""
        sketch_rating = solution.get_feedback()

        # if  sketch_rating : 
        #     solution.set_feedback(sketch_rating,replace=False)
        #     sketch_rating=''

        if not sketch_rating:
            log.info("Starting Reviewing before mutating !")
            previous_failure = solution.get_parent_feedback()
            # informal_proof = solution.informal_proof
            # print(informal_proof[:100])
            failed_str = solution.get_failed_subgoals_msg()
            # x = random.randint(1, 10)
            # if x >= 4 : 
            #     review_pt = REVIEWER_PROMPT
            # else : 
            #     review_pt = REVIEWER_PROMPT_old
            # log.info(x)
            reviewer_prompt = REVIEWER_PROMPT.format( sketch=sketch, failed_subgoals=failed_str)
             #,previous_failure=previous_failure,informal_proof=informal_proof)
            # print(reviewer_prompt)
            sketch_rating = completion(reviewer_prompt, REVIEWER_SYSTEM,is_response=True) #
            # log.info(f'Review : {sketch_rating}')
            solution.set_feedback(sketch_rating)
            # history = solution.get_history()
            # new_history= history + sketch_rating

        # print(sketch_rating)
        
        log.info("Starting mutating !")
        compressed_feedback = self.compress(sketch_rating)

        hints = solution.get_hints()
        if hints :
            compressed_feedback = compressed_feedback + '\n\n' + hints

        log.info(compressed_feedback)
        mutator_prompt = MUTATOR_PROMPT.format(
            sketch=sketch, sketch_rating = compressed_feedback
        )
        # print(mutator_prompt)


        output_old = completion(mutator_prompt, MUTATOR_SYSTEM)
        output = check_mutation(output_old)
        # print(output)
        updated = apply_search_replace(output, sketch)
        # print(updated)
        
        return Program(
            sketch=updated,
            data=solution.data,
            informal_proof=solution.informal_proof,
            parent=solution.id(),
            mutation_output=output,
            parent_rating=sketch_rating,
            old_mutation_output=output_old,
            compressed_feedback=compressed_feedback,
            # history=new_history,
        )
    def decompose2(self, solution: Program):

        sketch = solution.sketch()
        informal_proof = solution.get_informal_proof()
        solution_str =f"""{informal_proof}
```lean4
{sketch}
```"""
        # solution_str = solution.get_state()
        # print(sketch_rating)
        log.info("Starting mutating !")
        failed_str = solution.get_failed_subgoals_msg()
        mutator_prompt = MUTATE2.format(
            solution=solution_str, failed_str=failed_str
        )
        print(mutator_prompt)
        # print(mutator_prompt)
        output = completion(mutator_prompt)
        print(output)
        updated = apply_search_replace(output, solution_str)

        sketch = extrac_code(updated)
        informal_proof = updated.split('```lean4')[0]

        return Program(
            sketch = sketch,
            state=updated,
            data=solution.data,
            informal_proof=informal_proof,
            parent=solution.id(),
            mutation_output=output,
        )
    def decompose_inspiration(self, solution: Program, insp_solution: Program):
        failed_str = solution.get_failed_subgoals_msg()

        insp_errors = insp_solution.get_errors()
        if insp_errors:
            raise ValueError(
                f"Inspiration for decomposition problems should not have lean errors : {insp_errors}"
            )

        insp_errors = insp_solution.get_failed_subgoals_msg()

        prompt = SUBGOAL_MUTATION_PROMPT.format(
            sketch_to_evolve=solution.sketch(),
            sketch_to_evolve_error=failed_str,
            score=solution.get_score(),
            inspiration_sketch=insp_solution.sketch(),
            inspiration_sketch_errors=insp_errors,
            inspiration_score=insp_solution.get_score(),
        )
        output = completion(prompt, SUBGOAL_MUTATION_SYSTEM_PROMPT)

        updated = apply_search_replace(output, solution.sketch())
        return Program(
            sketch=updated,
            data=solution.data,
            informal_proof=solution.informal_proof,
            parent=solution.id(),
            inspiration=insp_solution.id(),
            mutation_output=output,
        )

    def mutate(self, solution: Program, inspiration: Program):
        if solution.get_errors():
            log.info("Refine")
            return self.refine(solution)
        else:
            log.info("Decompose")
            # if solution.id() != inspiration.id() :
            #     return self.decompose_inspiration(solution,inspiration)

            return self.decompose_reviewer(solution)
