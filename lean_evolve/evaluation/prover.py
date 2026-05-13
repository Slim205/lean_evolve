import json
import os
import requests
import pandas as pd

from lean_evolve.stores.prover_store import init_db, store_proof, has_theorem
from lean_evolve.utils import log, extrac_code, LEAN4_DEFAULT_HEADER, check_lean
from lean_evolve.evaluation.verifier import LeanVerifier
from lean_evolve.evaluation.lean_utils import (
    extract_theorem_signature,
    extract_theorem_name,
)
import re
from pathlib import Path

def extract_after_theorem_name(lean_code: str) -> str:
    # Match "theorem <name>" and capture everything after <name>
    if "lemma" in lean_code:
        lean_code = lean_code.replace("lemma", "theorem")
    m = re.search(r"\btheorem\s+[^\s(]+\s*(.*)", lean_code, re.DOTALL)
    if not m:
        log.error(lean_code)
        raise ValueError("No theorem declaration found")

    return m.group(1)


def remove_theorem_name(theorem):
    if "sorry" in theorem:
        theorem = extract_theorem_signature(theorem)
    # if theorem.count("theorem ") != 1 :
    #     log.info(f'Warning : {theorem}')
    # # print(extract_after_theorem_name(theorem))
    return extract_after_theorem_name(theorem)


# def remove_theorem_name(theorem):
#     if "sorry" in theorem:
#         theorem = extract_theorem_signature(theorem)
#     assert theorem.count("theorem ") == 1
#     return " ".join(theorem.split("theorem ")[1].split(" ")[1:])


# def get_theorem_name(theorem):
#     return theorem.split("theorem ")[1].split(" ")[0]


def call_model(prompts, n):
    url = os.environ.get("INFERENCE_URL")
    payload = {"inputs": prompts, "pass_n": n}

    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def process_formal_statement(theorem):
    new_theorem = extract_theorem_signature(theorem) + " := by"
    return new_theorem


def check_trivial(subgoals):
    theorems = [x["formal_statement"] for x in subgoals]

    samples = []
    for i, theorem in enumerate(theorems):
        if "import Mathlib" not in theorem:
            theorem = LEAN4_DEFAULT_HEADER + theorem
        samples.append({"custom_id": str(i), "proof": theorem.replace("sorry", "simp")})

    # Run Lean verifier
    lean_verifier = LeanVerifier()
    results = lean_verifier.compile(samples)
    results.sort(key=lambda x: int(x["custom_id"]))

    trivial_theorems = []

    for result in results:
        theorem = theorems[int(result["custom_id"])]
        if result.get("complete", False):
            trivial_theorems.append(theorem)

    log.info(
        "%d/%d trivial theorems detected :",
        len(trivial_theorems),
        len(results),
    )
    return trivial_theorems


def run_prover(
    input_path,
    output_dir,
    db_key,
    n=1,
    verif_batch=15,
    timeout=60,
    remove_trivial=False,
):

    with open(input_path, "r") as file:
        old_data_list = [json.loads(line) for line in file]

    os.makedirs("./results/db", exist_ok=True)
    db_path = f"./results/db/{db_key}.json"
    os.makedirs("./results/db_failure", exist_ok=True)
    db_path_failure = f"./results/db_failure/{db_key}.json"

    db = init_db(db_path)
    db_failure = init_db(db_path_failure)
    
    theorem_proof_dict = {}
    model_inputs = []
    data_list = []
    failed_theorems=[]
    trivial = 0
    # if remove_trivial:
    #     trivial_statements = check_trivial(old_data_list)
    #     for theorem in trivial_statements:
    #         is_proved, proof = has_theorem(db, theorem)
    #         if not is_proved:
    #             store_proof(
    #                 db,
    #                 remove_theorem_name(theorem),
    #                 remove_theorem_name(theorem.replace("sorry", "simp")),
    #             )
    #     trivial = len(trivial_statements)

    for data in old_data_list:

        text = "Complete the following Lean 4 code :\n\n```lean4\n{header}{formal_statement}".format(
            header=LEAN4_DEFAULT_HEADER,
            formal_statement=process_formal_statement(data["formal_statement"]),
        )
        thm = remove_theorem_name(data["formal_statement"])
        is_proved, proof = has_theorem(db, thm)
        is_failed , _ = has_theorem(db_failure, thm)
      
        if not is_proved:
            if not is_failed : 
                model_inputs.append(text)
                data_list.append(data)
            else :
                failed_theorems.append(data["formal_statement"])
        else:
            theorem_proof_dict[data["formal_statement"]] = (
                "theorem "
                + extract_theorem_name(data["formal_statement"])
                + " "
                + proof
            )

    log.info(f"Using {len(theorem_proof_dict)} previous proofs.")
    log.info(f"Avoiding {len(old_data_list)-len(data_list)-len(theorem_proof_dict)} previous failed proofs.")

    if len(data_list) == 0 :
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out_path = Path(output_dir) / "succeeded_proofs.json"
        with open(out_path, "w") as f:
            json.dump(theorem_proof_dict, f)

        return len(theorem_proof_dict), len(old_data_list), failed_theorems, 0
        
    # if len(theorem_proof_dict) == len(old_data_list):
    #     with open(f"{output_dir}/succeeded_proofs.json", "w") as f:
    #         json.dump(theorem_proof_dict, f)
    
    if len(theorem_proof_dict) == len(old_data_list):

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out_path = Path(output_dir) / "succeeded_proofs.json"
        with open(out_path, "w") as f:
            json.dump(theorem_proof_dict, f)

        return len(old_data_list), len(old_data_list), [], 0

    log.info(f"{len(model_inputs)} theorems to prove.")

    model_outputs = call_model(model_inputs, n)

    assert len(model_outputs) == len(model_inputs)

    to_inference_codes = []
    for i in range(len(data_list)):
        data_list[i]["model_input"] = model_inputs[i]
        data_list[i]["model_outputs"] = [output for output in model_outputs[i]]
        data_list[i]["full_code"] = [
            extrac_code(model_inputs[i] + output) for output in model_outputs[i]
        ]
        to_inference_codes += [
            {"name": data_list[i]["name"], "code": code}
            for code in data_list[i]["full_code"]
        ]

    os.makedirs(output_dir, exist_ok=True)
    output_file_path = f"{output_dir}/full_records.json"
    print(f"Outputting to {output_file_path}")
    with open(output_file_path, "w") as json_file:
        json.dump(data_list, json_file, indent=4)

    toinfer_file_path = f"{output_dir}/to_inference_codes.json"
    print(f"Outputting to {toinfer_file_path}")
    with open(toinfer_file_path, "w") as json_file:
        json.dump(to_inference_codes, json_file, indent=4)

    codes = to_inference_codes.copy()
    samples = []
    for i in range(len(codes)):
        codes[i]["custom_id"] = f"{codes[i]['name']}_{i}"
        samples.append({"custom_id": codes[i]["custom_id"], "proof": codes[i]["code"]})

    lean_verifier = LeanVerifier(verif_batch, timeout=timeout)
    compilation_results = lean_verifier.compile(samples)

    assert len(compilation_results) == len(codes)

    compilation_dict = {result["custom_id"]: result for result in compilation_results}

    for code in codes:
        custom_id = code["custom_id"]
        if custom_id in compilation_dict:
            code["compilation_result"] = compilation_dict[custom_id]
        else:
            print(custom_id)
    compilation_path = f"{output_dir}/code_compilation.json"

    with open(compilation_path, "w") as json_file:
        json.dump(codes, json_file, indent=4)

    proof_dict = {}
    for res in codes:
        if res["compilation_result"]["complete"]:
            if res["name"] not in proof_dict.keys():
                proof_dict[res["name"]] = res["code"]
            elif len(proof_dict[res["name"]]) > len(res["code"]):
                proof_dict[res["name"]] = res["code"]

    statement_dict = {x["name"]: x["formal_statement"] for x in data_list}
    theorem_dict = {statement_dict[x]: proof_dict[x] for x in proof_dict.keys()}

    full_theorems_str = LEAN4_DEFAULT_HEADER
    for x, y in theorem_dict.items():
        store_proof(db, remove_theorem_name(x), remove_theorem_name(y))
        theorem_proof_dict[x] = y.replace(LEAN4_DEFAULT_HEADER, "")
        full_theorems_str += "\n" + theorem_proof_dict[x]

    failure_list = []
    for res in codes:
        if res["name"] not in proof_dict.keys() :
            failure_list.append(res["name"])
    failure_thm = [statement_dict[x] for x in failure_list]
    for x in failure_thm :
        store_proof(db_failure, remove_theorem_name(x), 'FAILED')

    succeeded_proofs = f"{output_dir}/succeeded_proofs.json"

    with open(succeeded_proofs, "w") as f:
        json.dump(theorem_proof_dict, f, indent=2)

    partial_proof_verif = check_lean(full_theorems_str, timeout=300)
    if not partial_proof_verif["complete"]:
        log.error("Problem with this proof sketch ! Assembly will fail.")
        # raise ValueError('Problem with this proof sketch ! Assembly will fail.')
    else:
        log.info("All the selected theorems compiles.")

    n_succeded = len(theorem_proof_dict)
    total = len(old_data_list)

    df = pd.read_json(compilation_path)

    df["correct"] = df.compilation_result.apply(lambda x: x["complete"])

    df_grp = df.groupby("name")["correct"].sum()

    result = {
        "total": len(df_grp),
        "correct": sum(df_grp > 0),
        "accuracy": f"{sum(df_grp > 0) / len(df_grp)  * 100:.2f}",
        "field": "complete",
        "total_total": total,
        "total_correct": n_succeded,
        "total_acc": round(n_succeded / total * 100, 2),
    }
    compilation_summarize = f"{output_dir}/compilation_summarize.json"

    with open(compilation_summarize, "w") as f:
        json.dump(result, f)

    df_grp.reset_index()[["name", "correct"]].to_csv(
        compilation_summarize.replace(".json", ".csv"),
        index=False,
        header=True,
        sep="\t",
        quoting=1,
        na_rep="Missing",
    )

    print(result)

    failed = [
        sg["formal_statement"]
        for sg in data_list
        if int(df_grp.get(sg["name"], 0)) == 0
    ]

    for x in failed_theorems :
        failed.append(x)

    return n_succeded, total, failed, trivial


def run_single_proof(theorem, output_dir, n=1, verif_batch=15):

    model_inputs = []
    data_list = [{"formal_statement": theorem, "name": "test"}]
    text = "Complete the following Lean 4 code :\n\n```lean4\n{header}{formal_statement}".format(
        header=LEAN4_DEFAULT_HEADER,
        formal_statement=process_formal_statement(theorem),
    )
    model_inputs = [text]

    model_outputs = call_model(model_inputs, n)

    assert len(model_outputs) == len(model_inputs)

    to_inference_codes = []
    for i in range(len(data_list)):
        data_list[i]["model_input"] = model_inputs[i]
        data_list[i]["model_outputs"] = [output for output in model_outputs[i]]
        data_list[i]["full_code"] = [
            extrac_code(model_inputs[i] + output) for output in model_outputs[i]
        ]
        to_inference_codes += [
            {"name": data_list[i]["name"], "code": code}
            for code in data_list[i]["full_code"]
        ]

    os.makedirs(output_dir, exist_ok=True)
    output_file_path = f"{output_dir}/full_records.json"
    print(f"Outputting to {output_file_path}")
    with open(output_file_path, "w") as json_file:
        json.dump(data_list, json_file, indent=4)

    toinfer_file_path = f"{output_dir}/to_inference_codes.json"
    print(f"Outputting to {toinfer_file_path}")
    with open(toinfer_file_path, "w") as json_file:
        json.dump(to_inference_codes, json_file, indent=4)

    codes = to_inference_codes.copy()
    samples = []
    for i in range(len(codes)):
        codes[i]["custom_id"] = f"{codes[i]['name']}_{i}"
        samples.append({"custom_id": codes[i]["custom_id"], "proof": codes[i]["code"]})

    lean_verifier = LeanVerifier(verif_batch)
    compilation_results = lean_verifier.compile(samples)

    assert len(compilation_results) == len(codes)

    compilation_dict = {result["custom_id"]: result for result in compilation_results}

    for code in codes:
        custom_id = code["custom_id"]
        if custom_id in compilation_dict:
            code["compilation_result"] = compilation_dict[custom_id]
        else:
            print(custom_id)
    compilation_path = f"{output_dir}/code_compilation.json"

    with open(compilation_path, "w") as json_file:
        json.dump(codes, json_file, indent=4)

    df = pd.read_json(compilation_path)

    df["correct"] = df.compilation_result.apply(lambda x: x["complete"])

    df_grp = df.groupby("name")["correct"].sum()

    result = {
        "total": len(df_grp),
        "correct": sum(df_grp > 0),
        "accuracy": f"{sum(df_grp > 0) / len(df_grp)  * 100:.2f}",
        "field": "complete",
    }
    compilation_summarize = f"{output_dir}/compilation_summarize.json"

    with open(compilation_summarize, "w") as f:
        json.dump(result, f)

    df_grp.reset_index()[["name", "correct"]].to_csv(
        compilation_summarize.replace(".json", ".csv"),
        index=False,
        header=True,
        sep="\t",
        quoting=1,
        na_rep="Missing",
    )

    print(result)

    return


def run_prover_test():
    log.info("Test Started")
    theorem = "theorem trivial_1 : 1 + 1 = 2 := sorry"

    model_input = (
        "Complete the following Lean 4 code :\n\n```lean4\n"
        f"{LEAN4_DEFAULT_HEADER}{process_formal_statement(theorem)}"
    )

    output = call_model([model_input], n=1)[0][0]
    code = extrac_code(model_input + output)

    lean_verifier = LeanVerifier(1)
    result = lean_verifier.compile([{"custom_id": "test_0", "proof": code}])[0]
    log.info("Test Completed")

    assert result["complete"]
