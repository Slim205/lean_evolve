from lean_evolve.pipeline import Pipeline

from lean_evolve.stores.program import Program
from lean_evolve.stores.database import Database

from lean_evolve.utils import read_minif2f, log, lean_project_path, save_txt
from lean_evolve.evaluation.program import ProgramRater
from lean_evolve.mutate.program import RefineProgram

from lean_evolve.models.llm_utils import GLOBAL_LLM_CALLS

from pathlib import Path


def process_problem(
    problem_data: dict,
    output_path,
    initial_programs_per_island: int = 1,
    num_islands: int = 1,
    max_island_capacity: int = 1000,
    max_budget=1,
    N_prover: int = 16,
    verif_batch: int = 16,
    is_inspiration=False,
    review_only=False,
    s_id=0,
):

    population_db = Database(
        path=output_path,
        data=problem_data,
        n_islands=num_islands,
        n_programs=initial_programs_per_island,
        max_island_size=max_island_capacity,
    )

    budget = population_db.get_budget()
    GLOBAL_LLM_CALLS.reset(budget)

    log.info(GLOBAL_LLM_CALLS.summary())

    rater = ProgramRater(
        N_prover=N_prover,
        verif_batch=verif_batch,
        extractor="lemma_style",
        re_extract=False,
    )

    # Create missing islands (if database contains fewer than requested)
    current_population_size = population_db.get_size()
    for _ in range(num_islands - current_population_size):
        population_db.create_new_island()

    is_positive_program = False

    for island_store in population_db.get_islands():
        log.info(f"Island N {island_store.id()}")
        # if island_store.id() != 3 : 
        #     continue
        for program in island_store.get_all_programs():
            # if program.get_score() < 0 and program.id() > 6 and program.get_parent_id() > -1 : 
            #     log.info(program.id())
            #     # program.select_edits()
            #     rater.rate(program)
            # if program.id() == 0 : 
            # rater.rate(program)
            #     program.prune_sketch()
            #     rater.rate(program,review_only=True)
                # island_store.eval_parent_mutation(program)
            # print(program.id())
            # program.verif_current_proofs()
            # if program.get_score() >0 :
            #     is_positive_program=True
            # print(program.id())
            # print(island_store.get_n_visits(program))
            # print('-'*60)
            if program.get_score() == 1:
                log.info("All subgoals were proved !")
                lean_proof = program.get_full_proof()
                if program.is_proved():
                    log.info("Proof Correct !")
                    save_txt(
                        lean_proof, lean_project_path / f"{problem_data['name']}.lean"
                    )
                else:
                    log.error(
                        f"Inspect the program {program.id()}. The proof is incorrect ! "
                    )

                island_store.describe()
                population_db.set_budget(GLOBAL_LLM_CALLS.summary())
                return

        if not is_positive_program:
            current_size = island_store.get_size()
            for _ in range(initial_programs_per_island - current_size): 
                try : 
                    sketch = Program(
                        data=problem_data, informal_proof=island_store.get_informal_proof()
                    )
                    rating = rater.rate(sketch)

                    if rating.is_correct:
                        log.info("Problem Solved !")
                        lean_proof = sketch.get_full_proof()
                        if sketch.is_proved():
                            log.info("Proof Correct !")
                            save_txt(
                                lean_proof,
                                lean_project_path / f"{problem_data['name']}.lean",
                            )
                        else:
                            log.error(
                                f"Inspect the program {sketch.id()}. The proof is incorrect ! "
                            )

                        island_store.add(sketch)
                        island_store.describe()
                        population_db.set_budget(GLOBAL_LLM_CALLS.summary())
                        return
                    island_store.add(sketch)

                    if rating.fitness >= 0:
                        break
                except Exception as e : 
                    log.error(str(e))
        island_store.describe()

    island_store = population_db.get_island(s_id)
    log.info(f"Island N {island_store.id()}")
    mutator = RefineProgram()
    pipeline = Pipeline(
        store=island_store,
        rater=rater,
        mutator=mutator,
        max_budget=max_budget,
        is_inspiration=is_inspiration,
    )

    succ_solution, n_attempts = pipeline.run()
    island_store.set_attempt(n_attempts)

    if succ_solution is not None:
        log.info("Problem Solved !")
        lean_proof = succ_solution.get_full_proof()
        if succ_solution.is_proved():
            log.info("Proof Correct !")
            save_txt(lean_proof, lean_project_path / f"{problem_data['name']}.lean")
        else:
            log.error(
                f"Inspect the program {succ_solution.id()}. The proof is incorrect ! "
            )

        island_store.add(succ_solution)
        island_store.describe()
    # for island_store in population_db.get_islands():
    #     island_store.describe()

    population_db.set_budget(GLOBAL_LLM_CALLS.summary())


if __name__ == "__main__":
    minif2f_dataset = read_minif2f("data/minif2f_s1.jsonl", split="test")

    # for problem in minif2f_dataset:
        
    #     if problem['name'] == "mathd_algebra_320" :
    #         log.info("-" * 100)
    #         log.info(f"Selected problem: {problem['name']}")
    #         log.info(f"Formal statement:\n{problem['formal_statement']}")
    #         output_path = Path(f"./results/Population_26/{problem['name']}/")
    #         process_problem(problem,output_path=output_path,max_budget=80,N_prover=16) # 90 calls.

        # if problem["name"] == "numbertheory_fxeq4powxp6powxp9powx_f2powmdvdf2pown":
        #     log.info("-" * 100)
        #     log.info(f"Selected problem: {problem['name']}")
        #     log.info(f"Formal statement:\n{problem['formal_statement']}")
        #     output_path = Path(f"./results/Population_23/{problem['name']}/")
        #     process_problem(problem, output_path=output_path, max_budget=30) # 60 calls.

        # if problem['name'] == "imo_1997_p5" :
        #     log.info("-" * 100)
        #     log.info(f"Selected problem: {problem['name']}")
        #     log.info(f"Formal statement:\n{problem['formal_statement']}")
        #     output_path = Path(f"./results/Population_24/{problem['name']}/")
        #     process_problem(problem,output_path=output_path,max_budget=190) # 50 calls

        # if problem['name'] == "algebra_apbmpcneq0_aeq0anbeq0anceq0" :
        #     log.info("-" * 100)
        #     log.info(f"Selected problem: {problem['name']}")
        #     log.info(f"Formal statement:\n{problem['formal_statement']}")
        #     output_path = Path(f"./results/Population_24/{problem['name']}/")
        #     process_problem(problem,output_path=output_path,max_budget=400)

    minif2f_dataset = read_minif2f("data/putnam_s1.jsonl", split="test")

    for problem in minif2f_dataset:
        
        if problem['name'] == "putnam_2025_b3" :

            log.info("-" * 100)
            log.info(f"Selected problem: {problem['name']}")
            log.info(f"Formal statement:\n{problem['formal_statement']}")
            # problem['header'] = ''
            output_path = Path(f"./results/Population_26/{problem['name']}/")
            process_problem(problem, output_path=output_path, max_budget=400,s_id=0) # 80
            