from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
from lean_evolve.models.llm_utils import completion

from lean_evolve.utils import read_txt, save_txt, log, read_json, save_json
from lean_evolve.stores.prompts import (
    informal_proof_prompt_template,
    system_prompt_informal_proof,
    META_STEP2_SYSTEM_MSG,
    META_STEP2_USER_MSG,
    META_STEP3_SYSTEM_MSG,
    META_STEP3_USER_MSG,
)
from lean_evolve.stores.program import Program
from . import Store, Solution
from termcolor import colored
import numpy as np


def generate_informal_proof(data: Dict[str, Any]) -> str:
    """Generate an informal proof from the provided formal statement."""
    prompt = informal_proof_prompt_template.format(
        informal=data["informal_statement"],
        formal=data["formal_statement"],
    )
    return completion(prompt, system_prompt_informal_proof,is_response=True)


def mv_rm(old_path: Path, new_path: Path):
    new_path.mkdir(parents=True, exist_ok=True)
    for item in old_path.iterdir():
        shutil.move(str(item), str(new_path / item.name))
    shutil.rmtree(old_path)


class Island(Store):
    """
    Container of programs that share the same informal proof and theorem data.
    """

    path: Path
    data: Dict[str, Any]
    informal_path: Path
    max_size: int

    def __init__(self, path: Path, data: Dict[str, Any], max_size: int = 1):
        self.path = path
        self.data = data
        self.informal_path = self.path / "informal_proof.txt"
        self.max_size = max_size
        self.metadata_path = self.path / "metadata.json"
        self.path.mkdir(parents=True, exist_ok=True)

        # Ensure directory exists; only create informal_proof + metadata if missing
        if not self.informal_path.exists():
            self.create()  # full creation
        else:
            if not self.metadata_path.exists():
                self._save_data()  # reconstruct empty metadata

    def create(self):
        """Create the island and populate up to size N."""

        # Generate informal proof
        log.info("Generating new informal proof.")
        informal = generate_informal_proof(self.data)
        if not informal:
            raise ValueError("Generated informal proof is empty.")
        save_txt(informal, self.informal_path)
        self._save_data()

    def add(self, program: Solution):
        """Add a program inside the island (physical folder + metadata)."""
        program_id = self._new_program_id()
        program_path = self.path / f"program_{program_id}"

        if self.max_size <= len(self.get_programs()):
            worse_program = self.sample_worse_program()
            if worse_program.get_score() < program.get_score():
                self.delete(worse_program)
            else:
                log.info(f"No program will be added to the island.")
                self.update_failed_attempts(
                    {
                        "attempt": program_id,
                        "status": "Not inserted",
                        "score": program.get_score(),
                    }
                )
                return

        # Move the program data to the store
        mv_rm(program.path, program_path)

        program = Program(
            data=self.data, path=program_path, informal_proof=self.get_informal_proof()
        )
        program.update_data(program_id=program_id, island_id=self.id())

        # Update metadata (active = True)
        meta = self._load_data()
        meta["size"] = self.get_size() + 1
        meta["programs"].append(
            {
                "program_id": program_id,
                "active": True,
                "path": str(program_path),
                "parent": program.get_parent_id(),
            }
        )
        self._save_data(meta)

        log.info(f"Program {program_id} was successfully added to the island.")
        return program
        
    def delete(self, program: Solution):
        meta = self._load_data()
        pid = program.id()

        found = False
        for item in meta["programs"]:
            if item["program_id"] == pid:
                found = True
                if not item["active"]:
                    raise ValueError(f"Program {pid} already deactivated.")
                item["active"] = False

        if not found:
            raise ValueError(f"Program {pid} not found in island metadata.")

        self._save_data(meta)
        log.info(f"Program {pid} was successfully deleted from the island.")

    def id(self) -> int:
        """Extract island id from the path."""
        name = self.path.name
        return int(name.split("island_")[1])

    def get_programs(self) -> List[Solution]:
        """Return active programs only."""
        meta = self._load_data()
        active_items = [p for p in meta["programs"] if p["active"]]
        informal_proof = self.get_informal_proof()
        return [
            Program(
                path=Path(item["path"]), data=self.data, informal_proof=informal_proof
            )
            for item in active_items
        ]

    def get_all_programs(self) -> List[Solution]:
        """Return all programs ."""
        meta = self._load_data()
        informal_proof = self.get_informal_proof()
        return [
            Program(
                path=Path(item["path"]), data=self.data, informal_proof=informal_proof
            )
            for item in meta["programs"]
        ]

    def _load_data(self) -> dict:
        """Load metadata.json."""
        with open(self.metadata_path, "r") as f:
            return json.load(f)

    def _save_data(self, data: Optional[dict] = None):
        """Write metadata.json to disk."""
        if data is None:
            data = {
                "island_id": self.id(),
                "size": 0,
                "max_size": self.max_size,
                "created": self.informal_path.exists(),
                "MAX_MUTATION": 0,
                "programs": [],
            }
        with open(self.metadata_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_informal_proof(self) -> str:
        return read_txt(self.informal_path)

    def get_size(self):
        return len(self.get_programs())

    def _new_program_id(self) -> int:
        """Generate a fresh integer ID based on existing metadata."""
        meta = self._load_data()
        if not meta["programs"]:
            return 0
        return max(p["program_id"] for p in meta["programs"]) + 1

    def sample(
        self,
        method: str = "random",
        k: int = 1,
        tau=1,
    ) -> Solution:
        """
        Sample a Program from this island.

        - method='random': uniformly sample any active program.
        - method='best_program': return the single best active program.
        - method='best_program_k': return a random program among the top-k active programs.
        """
        if method == "random":
            program = self.sample_random_program()
            if program is None:
                raise RuntimeError("No programs available in island to sample.")
            return program

        elif method == "best_program":
            return self.sample_best_program(1)
        elif method == "best_program_k":
            return self.sample_best_program(k)
        elif method == "shinka":
            return self.sample_shinka()
        elif method == "ucb":
            return self.sample_ucb1(k, tau)

        else:
            raise ValueError(f"Unknown sampling method: {method}")

    def sample_random_program(self) -> Solution:
        """Sample a random active program."""
        active = self.get_programs()
        
        if not active:
            raise RuntimeError("No active programs in island.")

        active = [program for program in self.get_programs() if program.get_score()>0]
        
        return random.choice(active)

    def get_children(self, program):
        children_list = []
        program_id = program.id()
        for program_1 in self.get_all_programs():
            if program_1.get_parent_id() == program_id:
                children_list.append(program_1)
        return children_list

    def get_n_visits(self, program):
        n_childrens = len(self.get_children(program))
        failed_attempts = self.get_failed_attempts()
        s = 0
        program_id = program.id()
        for attempt in failed_attempts:
            if attempt["program_id"] == program_id:
                s += 1
        return s + n_childrens

    def get_depth(self, program):

        depth = program.get_depth()
        if depth != -1:  # depth wasn't set.
            return depth
        depth = 0
        parent_id = program.get_parent_id()
        while parent_id != -1:
            depth += 1
            new_parent = self.get_program(parent_id)
            parent_id = new_parent.get_parent_id()
        # print(f"{program.id()}  :   {depth}")
        program.set_depth(depth)
        return depth

    def sample_ucb1(self, iteration: int, tau) -> Solution:
        """
        Selects a program using the UCB1 strategy, balancing exploitation and exploration.
        """

        best_score = - np.inf
        best_program = None

        ucb_scores, exploit_scores, explore_scores = [], [], []
        programs = self.get_programs()
        for program in programs:
            exploitation = 10 * program.get_score()
            exploration = float(
                np.sqrt(
                    2 * np.log(iteration) / (self.get_n_visits(program) + 1)
                )
            )
            if exploitation < 0 :
                ucb_score = 10 * exploitation
            else : 
                ucb_score =   exploration  +  self.get_depth(program)

            # ucb_score = self.get_depth(program) / (0.3 * self.get_n_visits(program) + 1)

            # if program.get_score() < 0:
            #     ucb_score = 0
            ucb_scores.append(round(ucb_score, 4))
            # exploit_scores.append(round(exploitation, 4))
            # explore_scores.append(round(exploration, 4))

            if ucb_score > best_score:
                best_score = ucb_score
                best_program = program

        # log.info([max(x, 0) for x in ucb_scores])
        # log.info(ucb_scores)

        # ucb = np.array(ucb_scores, dtype=float)
        # z = (ucb - ucb.max()) / tau
        # weights = np.exp(z)
        # probs = weights / weights.sum()
        # log.info(f"Probs :\n{ {i: float(round(probs[i], 4)) for i in range(len(probs))} }")
        # log.info(f'Temperature : {tau}')
        # idx = np.random.choice(len(programs), p=probs)
        # # log.info(f"Using randomness: selected program ID {idx}")
        # # log.info(f"No randomness: selected program ID {best_program.id()}")
        # best_program = programs[idx]
        return best_program

    def sample_shinka(self, lambda_param: float = 10.0) -> Solution:
        """
        Samples a program probabilistically using SHINKA-style fitness and diversity weighting.
        """
        programs = self.get_programs()

        fitnesses = np.array([p.get_score() for p in programs])
        alpha0 = np.median(fitnesses)

        def sigmoid(x: float) -> float:
            return 1.0 / (1.0 + np.exp(-x))

        selection_pressure = np.array(
            [sigmoid(lambda_param * (p.get_score() - alpha0)) for p in programs]
        )

        diversity_penalty = np.array(
            [1.0 / (1.0 + len(self.get_children(p))) for p in programs]
        )
        weights = selection_pressure * diversity_penalty
        probs = weights / weights.sum()
        log.info(probs)
        # print(selection_pressure)
        # print(diversity_penalty)

        return random.choices(programs, weights=probs, k=1)[0]

    def sample_best_program(self, k: int = 1) -> Solution:
        """
        Return the best active program or one randomly sampled from the top-k active programs.
        """
        programs = self.get_programs()
        if not programs:
            raise RuntimeError("No active programs in island to select from.")

        scored_programs: List[tuple[float, Program]] = []

        for program in programs:
            score = program.get_score()
            scored_programs.append((score, program))

        scored_programs.sort(key=lambda x: x[0], reverse=True)
        sorted_programs = [p for (_, p) in scored_programs]

        if k <= 1 or len(sorted_programs) == 1:
            return sorted_programs[0]

        k = min(k, len(sorted_programs))
        return random.choice(sorted_programs[:k])

    def sample_worse_program(self, k: int = 1) -> Solution:
        """
        Return the worse active program.
        """
        programs = self.get_programs()
        if not programs:
            raise RuntimeError("No active programs in island to select from.")

        scored_programs: List[tuple[float, Program]] = []

        for program in programs:
            score = program.get_score()
            scored_programs.append((score, program))

        scored_programs.sort(key=lambda x: x[0])
        sorted_programs = [p for (_, p) in scored_programs]

        return sorted_programs[0]

    def _get_island_graph(self) -> Dict[int, List[int]]:
        """
        Return a mapping parent_program_id → list of child_program_ids,
        using only active programs.
        """
        parent_to_children: Dict[int, List[int]] = {}

        for program in self.get_all_programs():
            parent_id = program.get_parent_id()
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(program.id())

        return parent_to_children

    def describe(self):
        print(f"Island_{self.id()}")

        activated = {p.id() for p in self.get_programs()}
        graph = self._get_island_graph()
        id_to_program = {p.id(): p for p in self.get_all_programs()}
        roots = graph.get(-1, [])

        def style_name(name, active, score):
            if active:
                if score == 1.0:
                    return colored(name, "yellow", attrs=["bold"])
                return colored(name, "green", attrs=["bold"])

            return name

        def print_program(program_id, prefix="    ", is_last=True):
            program = id_to_program[program_id]
            active = program_id in activated
            score = round(program.get_score(), 4)
            connector = "└──" if is_last else "├──"
            name = style_name(program.path.name, active, score)

            print(f"{prefix}{connector} {name} (Score {score})")

            children = graph.get(program_id, [])
            child_prefix = prefix + ("   " if is_last else "│  ")
            for idx, child_id in enumerate(children):
                print_program(
                    child_id, prefix=child_prefix, is_last=(idx == len(children) - 1)
                )

        for idx, root in enumerate(roots):
            print_program(root, is_last=(idx == len(roots) - 1))

        self.get_n_calls_data()

    def get_program(self, program_id: int):
        """Returns a Program instance for the given program identifier."""
        program_path = self.path / f"program_{program_id}"
        return Program(
            data=self.data,
            path=program_path,
            informal_proof=self.get_informal_proof(),
        )

    def set_attempt(self, set_attempts: int) -> None:
        """Sets the maximum number of allowed mutation attempts."""
        data = self._load_data()
        data["MAX_MUTATION"] = set_attempts
        self._save_data(data)

    def update_failed_attempts(self, failed_attempts: Any) -> None:
        """Records a failed mutation attempt."""
        data = self._load_data()
        data.setdefault("Failed_mutations", []).append(failed_attempts)
        self._save_data(data)

    def get_failed_attempts(self) -> List[Any]:
        """Returns the list of recorded failed mutation attempts."""
        data = self._load_data()
        return data.get("Failed_mutations", [])

    def get_attempt(self) -> int:
        """Returns the maximum number of mutation attempts allowed."""
        data = self._load_data()
        # return int(data.get("MAX_MUTATION", 0))
        return len(data.get("mutations_history", []))
        
    def is_proved(self) -> bool:
        """Returns True if any generated program has successfully proved the theorem."""
        return any(program.is_proved() for program in self.get_all_programs())

    def update_history(self, history: Any) -> None:
        """Records mutation history."""
        data = self._load_data()
        data.setdefault("mutations_history", []).append(history)
        self._save_data(data)

    def get_n_calls_data(self) -> Dict[str, Any]:
        """
        Aggregates and records budget statistics for sketching, refinement, and proof generation.
        """

        n_extract_goal = 0
        n_calls_final_proof = 0
        n_refinement = 0
        n_reviewer = 0
        programs = self.get_all_programs()
        for program in programs:
            n_extract_goal += program.get_extract_goal_calls()
            n_refinement += program.get_refinement()
            if program.is_proved():
                n_calls_final_proof = program.get_full_proof_iteration()
            if program.get_score() > 0:
                n_reviewer += 1
        failed_budget = sum(x.get("budget", 0) for x in self.get_failed_attempts())

        n_sketch = len(programs)

        total = (
            1  # informal proof
            + n_sketch
            + n_extract_goal
            + n_calls_final_proof
            + n_refinement
            + failed_budget
            + n_reviewer
        )

        budget_program = {
            "informal_proof": 1,
            "sketch": n_sketch,
            "extract_goal": n_extract_goal,
            "final_proof": n_calls_final_proof,
            "refinement": n_refinement,
            "failed_attempts": failed_budget,
            "reviewer": n_reviewer,
            "total": total,
        }

        with open(self.path / "budget.json", "w") as f:
            json.dump(budget_program, f)
        return budget_program

    ### Test functions :
    def island_summary(self, re_generate=False):

        path = self.path / "summary.txt"
        if path.exists() and not re_generate:
            return read_txt(path)

        program_summaries = ""
        best = None
        maxi = -10
        for program in self.get_programs():
            score = program.get_score()
            if score > 0:
                program_summaries += (
                    f"Sketch ID : {program.id()}\n"
                    + program.get_summary()
                    + f"\nScore : {score}\n\n"
                )
                if score > maxi:
                    maxi = score
                    best = program.id()
        log.info(f"Creating summary for island {self.id()}")

        prompt = META_STEP2_USER_MSG.format(
            program_summaries=program_summaries,
            previous_insights="",
            best_program_info=f"program_{best} (Score {maxi})",
        )
        island_summary = completion(prompt, META_STEP2_SYSTEM_MSG)

        save_txt(island_summary, path)

        return island_summary

    def summary(self, re_generate=False):

        path = self.path / "recommendation.txt"
        if path.exists() and not re_generate:
            recommendation = read_txt(path)
            return recommendation

        island_summary = self.island_summary(re_generate=re_generate)
        best = self.sample_best_program(1)

        log.info(f"Creating recommendation for island {self.id()}")
        prompt = META_STEP3_USER_MSG.format(
            global_insights=island_summary,
            previous_recommendations="",
            best_program_info=f"program_{best.id()} (Score {best.get_score()})",
            max_recommendations=10,
        )
        recommendation = completion(prompt, META_STEP3_SYSTEM_MSG)
        save_txt(recommendation, path)

        for program in self.get_programs():
            program.set_hints(recommendation)
        return recommendation


# from lean_evolve.models.embedding import EmbeddingModel
# def verif_novelty_program(self, program) :
#     path = program.path /  'embedding/embd_dict.json'
#     if path.exists() :
#         return
#     parent = program.get_parent_id()
#     if parent < 0 :
#         return read_json(path)

#     embd_dict = {}
#     embd_model = EmbeddingModel()


#     for child in self.get_all_programs() :
#         if child.get_parent_id() == parent :
#             embd = embd_model.compare(program.get_replace_text(),child.get_replace_text())
#             embd_dict[child.id()] = embd
#     save_json(embd_dict,path)
#     maxi = 0
#     if len(embd_dict) > 0 :
#         maxi =  max(list(embd_dict.values()))
#         log.info(f'Max sim embedding is {maxi}')
#     return embd_dict


    def eval_parent_mutation(self,program) :
        
        if program.get_score() < 0 :
            return 

        from lean_evolve.models.llm_utils import completion
        from lean_evolve.evaluation.prompts import EVAL_MUTATION
        from lean_evolve.evaluation.lean_utils import extract_search_replace_blocks

        sketch_rating = program.get_feedback()
    
        if  'INCORRECT' in sketch_rating :
            parent_id = program.get_parent_id()
            parent = self.get_program(parent_id)

            log.info('Evaluating Parent sketch !')
            previous_feedback =parent.get_feedback()

            prompt_eval = EVAL_MUTATION.format(
            sketch=parent.sketch(), failed_subgoals=parent.get_failed_subgoals_msg(),
            previous_feedback=previous_feedback,children_feedback=sketch_rating
        )
            edit_blocks = completion(prompt_eval)
            parent.set_edit_feedback(edit_blocks)
            
            blocks = extract_search_replace_blocks(edit_blocks)
            new_feedback =''
            for block in blocks : 
                new_feedback = new_feedback+ block['replace']+ '\n'

            parent.set_feedback(previous_feedback,replace=False)
            parent.set_feedback(new_feedback.strip(),replace=True)

            program.update_score()
