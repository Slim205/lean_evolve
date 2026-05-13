import json
import os
import re
import csv
import re
from pathlib import Path
import logging
from client.client import Lean4Client
import traceback

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
lean_project_path = Path("~/projects/new_porject/NewPorject/minif2f").expanduser()
LEAN4_DEFAULT_HEADER = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat\n\n"


def read__file_csv(path_csv):

    data_dict = {}
    with open(path_csv, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for row in reader:
            data_dict[row["name"]] = row["correct"]

    return data_dict


def apply_search_replace(llm_output: str, sketch: str) -> str:
    """
    Extract all >>>>SEARCH / >>>>REPLACE blocks from llm_output
    and apply the replacements to the given sketch (in order).
    """

    # Regex to capture all pairs of SEARCH/REPLACE blocks
    pattern = re.compile(
        r">>>>SEARCH\s*(.*?)\s*>>>>REPLACE\s*(.*?)\s*(?=(>>>>SEARCH|$))", re.DOTALL
    )

    matches = pattern.findall(llm_output)

    if not matches:
        raise ValueError("No valid >>>>SEARCH/>>>>REPLACE blocks found.")

    updated = sketch

    for search_block, replace_block, _ in matches:
        search_block = search_block.rstrip()
        replace_block = replace_block.rstrip()

        if search_block not in updated:
            raise ValueError(f"SEARCH block not found in sketch:\n{search_block}")

        updated = updated.replace(search_block, replace_block, 1)

    return updated


def save_json(data, file_path, indent=2, ensure_ascii=False):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def save_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for i, th in enumerate(data):
            f.write(json.dumps(th) + "\n")


def read_minif2f(data_path, split="test"):
    data_list = []
    with open(data_path, "r") as file:
        for line in file:
            data = json.loads(line)
            if data["split"] == split:
                data_list.append(data)
    return data_list


def extrac_code(inputs):
    try:
        if "lean4" in inputs:
            return re.search(r"```lean4\n(.*?)\n```", inputs, re.DOTALL).group(1)
        else:
            return re.search(r"```lean\n(.*?)\n```", inputs, re.DOTALL).group(1)
    except:
        return "None"


def read_json(path):
    with open(path, "r") as f:
        return json.load(f)


def read_jsonl(path):
    data = []
    with open(path, "r") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def read_txt(path):
    with open(path, "r") as f:
        return f.read()


def save_txt(text: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def get_verification_results(old_result):
    custom_id = old_result["custom_id"]
    system_messages = old_result["error"]
    old_result = old_result["response"]

    try:

        result = {
            "sorries": old_result.get("sorries", []),
            "tactics": old_result.get("tactics", []),
            "errors": [
                m for m in old_result.get("messages", []) if m["severity"] == "error"
            ],
            "warnings": [
                m for m in old_result.get("messages", []) if m["severity"] == "warning"
            ],
            "infos": [
                m for m in old_result.get("messages", []) if m["severity"] == "info"
            ],
            "system_messages": system_messages,
            "system_errors": None,
        }
        result["pass"] = not result["errors"] and not bool(system_messages)
        result["complete"] = (
            result["pass"]
            and not result["sorries"]
            and not any(
                "declaration uses 'sorry'" in warning["data"]
                or "failed" in warning["data"]
                for warning in result["warnings"]
            )
        )
        result["verify_time"] = old_result["time"]

    except:
        result = {
            "pass": False,
            "complete": False,
            "system_errors": traceback.format_exc(),
            "system_messages": system_messages,
            "tactics": [],
        }
    result["custom_id"] = custom_id
    return result


def get_compilation_unit(lean_code):
    """
    Compile a Lean snippet and return its compilation units.

    """
    client = Lean4Client(base_url=os.environ.get("Evaluation_url"), disable_cache=False)
    if "import Mathlib" not in lean_code:
        lean_code = LEAN4_DEFAULT_HEADER + lean_code
    states = client.verify([{"proof": lean_code, "custom_id": "1"}], timeout=60)
    return states["results"][0]["response"]


def check_lean(lean_code, timeout=60):
    if "import Mathlib" not in lean_code:
        lean_code = LEAN4_DEFAULT_HEADER + lean_code

    client = Lean4Client(base_url=os.environ.get("Evaluation_url"), disable_cache=False)
    result = client.verify([{"proof": lean_code, "custom_id": "1"}], timeout=timeout)
    res = get_verification_results(result["results"][0])
    return res


def force_real_division(stmt: str) -> str:
    """
    Detects raw divisions like `a / b` in Lean code and forces only
    the LEFT operand to be interpreted as ℝ by inserting `(: ℝ)`.

    Example:
        "195 * (1 / 3) = 195 / 3"
    becomes:
        "195 * ((1 : ℝ) / 3) = ((195 : ℝ) / 3)"
    """

    # Match a bare identifier or number on the left and right of `/`
    div_pattern = re.compile(r"\b([A-Za-z0-9_]+)\s*/\s*([A-Za-z0-9_]+)\b")

    def repl(match):
        left, right = match.group(1), match.group(2)

        # If left already typed, do nothing
        if "ℝ" in left:
            return match.group(0)

        # Cast only the left operand
        return f"(({left} : ℝ) / {right})"

    return div_pattern.sub(repl, stmt)


def rewrite_minus_and_equals_integers(lean_code: str) -> str:
    """
    Replace integer literals that appear in:
      - binary subtraction: x - 3
      - equality: = 30
    turning them into (n : ℤ)

    Does NOT touch:
      - existing (n : ℤ)
      - numerals in other contexts
    """

    minus_pattern = r"(\S)\s*-\s*(\d+)\b(?!\s*:\s*ℤ)"

    def repl_minus(match):
        left = match.group(1)
        num = match.group(2)
        return f"{left} - ({num} : ℤ)"

    lean_code = re.sub(minus_pattern, repl_minus, lean_code)

    return lean_code


def process_subgoal(smt: str) -> str:
    if "log" in smt or "Complex" in smt or "ℂ" in smt or "cos" in smt or "sin" in smt:
        return transform_real_functions(smt)

    smt = force_real_division(smt)
    if "ℕ" in smt:
        smt = rewrite_minus_and_equals_integers(smt)

    return smt


def replace_up_arrow_log(s: str) -> str:
    # Pattern matches: (↑expr).log
    pattern = re.compile(r"\(\s*↑\s*([^)]+?)\s*\)\.log")

    def repl(match):
        expr = match.group(1).strip()
        return f"Real.log {expr}" if " " not in expr else f"Real.log ({expr})"

    s = pattern.sub(repl, s)

    # Matches expressions like: (↑w).((log : ℝ) / 24)
    pattern = re.compile(
        r"\(\s*↑\s*([^)]+?)\s*\)\.\s*\(\s*\(log\s*:\s*ℝ\)\s*/\s*([^)]+?)\s*\)"
    )

    def repl(match):
        var = match.group(1).strip()
        num = match.group(2).strip()
        return f"Real.log ({var} : ℝ) / ({num} : ℝ)"

    return pattern.sub(repl, s)


def transform_real_functions(text: str) -> str:
    """
    Transform patterns of the form:

        (EXPR).log
        (EXPR).sin
        (EXPR).cos
        (EXPR).exp

    into:

        Real.log (EXPR)
        Real.sin (EXPR)
        Real.cos (EXPR)
        Real.exp (EXPR)

    Handles nested parentheses, e.g.:
        (1 + (a*x)).log -> Real.log (1 + (a*x))
    """
    functions = {"log", "sin", "cos"}

    result_parts = []
    last_pos = 0
    i = 0
    n = len(text)

    while i < n:
        # Find next closing parenthesis
        close_idx = text.find(")", i)
        if close_idx == -1:
            break

        # Check if it's followed by ".funcname"
        if close_idx + 1 < n and text[close_idx + 1] == ".":
            # Read the function name (alphabetic characters)
            k = close_idx + 2
            while k < n and text[k].isalpha():
                k += 1
            func_name = text[close_idx + 2 : k]

            if func_name in functions:
                # Walk backwards from close_idx to find matching '('
                depth = 0
                j = close_idx
                while j >= 0:
                    if text[j] == ")":
                        depth += 1
                    elif text[j] == "(":
                        depth -= 1
                    if depth == 0:
                        break
                    j -= 1

                if j >= 0:
                    # Extract the expression inside (...)
                    inner_expr = text[j + 1 : close_idx]

                    # Append text before this block unchanged
                    result_parts.append(text[last_pos:j])

                    # Append transformed block
                    result_parts.append(f"Real.{func_name} ({inner_expr})")

                    # Move past the ").func"
                    last_pos = k
                    i = k
                    continue

        # If not a target pattern, just move on
        i = close_idx + 1

    # Append any remaining text after the last match
    result_parts.append(text[last_pos:])

    return "".join(result_parts)


def extract_failures_to_json(model_output: str):
    """
    Parses LLM output formatted with ######### blocks and writes a JSON file.
    """
    VALID_FAILURE_MODES = {"EXTRACTION", "HARD", "INCORRECT"}
    blocks = model_output.split("#########")
    results = []

    for block in blocks:
        if "Subgoal name" not in block:
            continue
        subgoal_match = re.search(r"Subgoal name\s*:\s*(.+)", block)
        mode_match = re.search(r"Failure mode\s*:\s*(EXTRACTION|HARD|INCORRECT)", block)
        rec_match = re.search(r"Recommendation\s*:\s*(.+)", block, re.DOTALL)

        if not (subgoal_match and mode_match and rec_match):
            raise ValueError(f"Malformed block:\n{block}")

        subgoal_name = subgoal_match.group(1).strip()
        failure_mode = mode_match.group(1).strip()

        if failure_mode not in VALID_FAILURE_MODES:
            raise ValueError(f"Invalid failure mode: {failure_mode}")

        recommendation = rec_match.group(1).strip()

        results.append(
            {
                "subgoal_name": subgoal_name,
                "failure_mode": failure_mode,
                "recommendation": recommendation,
            }
        )

    return results
