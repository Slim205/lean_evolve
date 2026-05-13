from __future__ import annotations

import re
from typing import List, Optional, Tuple, Dict, Set
from lean_evolve.utils import log, check_lean
from dataclasses import dataclass

def count_sorry_tokens( s: str) -> int:
    s = remove_comments(s)
    # count whole-word `sorry`
    return len(re.findall(r"\bsorry\b", s))
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

def verif_sorry_count(sketch) :

    decls = _split_top_level_decls(sketch)
    theorem_list: List[str] = []
    for d in decls:
        kind = d.split(None, 1)[0]  # "lemma" or "theorem"
        name = _find_decl_name(d, kind)
        if not name:
            continue

        if not _decl_ends_with_sorry(d):
            continue

        if kind != "lemma":
            continue

        theorem_list.append(
            {
                "name": name,
                "formal_statement": _extract_decl_header(d),
            }
        )

    sorry_count = count_sorry_tokens(sketch)
    goal_count = len(theorem_list)

    if goal_count != sorry_count:
        return (
            "ERROR from Mismatch between extracted subgoals and `sorry` tokens. "
            f"subgoals={goal_count} sorry_tokens={sorry_count}"
        )

    return ''
def get_sketch_errors(current_sketch: str, formal_stmt: str) -> str:
    """
    Return an error message string (possibly empty) if the sketch violates constraints.
    """
#  (" true", " True", ": Prop")
    if any(s in remove_comments(current_sketch) for s in [" true", " True", ": Prop"]):
        return (
            "ERROR from sketch : Trivial statements are not allowed.\n"
            "Do not use `True` or `Prop` or `true` as a statement.\n"
            "State an explicit mathematical proposition instead."
        )
    error_sorry_count=  verif_sorry_count(current_sketch)
    if error_sorry_count :
        return error_sorry_count

    errors = []
    if formal_stmt not in current_sketch:
        errors.append(
            f"ERROR from line 1: The main theorem was modified.\nPlease keep it as:\n{formal_stmt}"
        )

    lean_errors = get_lean_error_msg(current_sketch)
    errors.append(lean_errors)

    return "\n\n".join(errors)


def check_mutation(mutation_output: str) -> str:
    """
    Validate a mutation output and return the cleaned/validated mutation.

    Raises:
        ValueError: if mutation contains trivial statements or no meaningful changes.
    """
    # stripped = remove_comments(mutation_output)

    # Disallow trivial / non-informative statements
    # forbidden = (" true", " True", ": Prop")
    # if any(tok in stripped for tok in forbidden):
    #     log.info(mutation_output)
    #     raise ValueError(
    #         "Trivial statements are not allowed. State an explicit mathematical proposition instead."
    #     )

    new_mutation = assert_no_duplicate_signatures(mutation_output)

    # new_mutation should be a string; guard against None or whitespace-only output
    if not new_mutation or not new_mutation.strip():
        log.info(mutation_output)
        raise ValueError("No interesting mutation happening.")

        
    return new_mutation


def get_lean_error_msg(lean_code):

    res = check_lean(lean_code)

    error_message = ""
    for err in res.get("errors", []):
        if err.get("severity") == "error":
            error_message += (
                f"ERROR from position {err['pos']} to {err['endPos']}:\n"
                f"{err['data']}\n\n"
            )
    return error_message


_HAVE_ANY_DECL_RE = re.compile(
    r"""
    ^\s*have\s+                      # have
    (?P<name>[A-Za-z_]\w*)\s*        # theorem/lemma name
    :\s*(?P<type>\S+)\s*             # : <single token, no spaces>
    :=\s*by\b                        # := by
    """,
    re.VERBOSE | re.MULTILINE,
)


def find_have_placeholder_by(sketch: str) -> list[tuple[str, int]]:
    """
    Find occurrences of the pattern: `have <name> : True := by`
    Returns a list of (name, line_number) for each match.
    """
    hits: list[tuple[str, int]] = []
    for m in _HAVE_ANY_DECL_RE.finditer(sketch):
        name = m.group("name")
        line_no = sketch.count("\n", 0, m.start()) + 1
        hits.append((name, line_no))
    return hits


def extract_theorem_name(theorem_text: str) -> str:
    """
    Extract the name of a theorem from its declaration.
    """
    if "lemma" in theorem_text:
        theorem_text = theorem_text.replace("lemma", "theorem")
    # remove comments if any
    text = remove_comments(theorem_text)

    # find the keyword theorem
    if "theorem" not in text:
        raise ValueError("No theorem keyword found in theorem declaration")

    # find the name of the theorem
    name_start = text.find("theorem ") + len("theorem ")
    idx = name_start
    stop_chars = {":", "(", "{", "[", "⦃"}
    while idx < len(theorem_text) and text[idx] != ":" and text[idx] not in stop_chars:
        idx += 1
    name_end = idx
    name = text[name_start:name_end].strip()
    return name


def extract_all_lean_blocks(response: str) -> Optional[List[str]]:
    """
    Parse all Lean blocks from string.

    Args:
        response: string containing Lean blocks

    Returns:
        List of extracted Lean blocks, or None if no Lean blocks found
    """

    # Try to extract Lean code blocks first
    lean_pattern = r"```(?:lean4?|LEAN4?)\s*\n(.*?)\n```"
    theorems = re.findall(lean_pattern, response, re.DOTALL | re.IGNORECASE)
    if not theorems:
        return None  # No lean blocks found, don't try to parse forcefully

    return theorems


def remove_import_statements(text: str) -> str:
    all_lines = text.split("\n")
    to_include = []
    for idx, line in enumerate(all_lines):
        if line.startswith("theorem"):
            to_include = all_lines[idx:]
            break
    if not to_include:
        log.error("LLM output does not contain a theorem !")
        log.error(text)
        raise False
    new_text = "\n".join(to_include).strip()
    return new_text


_DECL_START_RE = re.compile(r"(?m)^(?:theorem|lemma)\s+")


def strip_prelude_before_first_decl(code: str) -> str:
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    m = _DECL_START_RE.search(code)
    if not m:
        return code
    return code[m.start() :]


def assemble_with_default_header(code: str, LEAN4_DEFAULT_HEADER: str) -> str:
    """
    Drop everything before the first theorem/lemma and prepend LEAN4_DEFAULT_HEADER.
    """
    body = strip_prelude_before_first_decl(code)
    return LEAN4_DEFAULT_HEADER.rstrip() + "\n\n" + body.lstrip()


def remove_comments(text: str) -> str:
    """
    Remove comments from Lean code while preserving structure.

    Args:
        text: Lean code with comments

    Returns:
        Lean code with comments removed
    """
    # First remove block comments (/- ... -/)
    result = ""
    i = 0
    while i < len(text):
        # Check for start of block comment
        if i < len(text) - 1 and text[i : i + 2] == "/-":
            # Find the end of block comment
            end_pos = text.find("-/", i + 2)
            if end_pos != -1:
                # Skip the entire block comment
                i = end_pos + 2
                continue
            else:
                # Unterminated block comment, remove rest of text
                break
        else:
            result += text[i]
            i += 1

    # Then remove single-line comments (-- comments)
    lines = result.split("\n")
    cleaned_lines = []

    for line in lines:
        if "--" in line:
            # Find the position of -- that's not inside a string
            comment_pos = line.find("--")
            if comment_pos != -1:
                line = line[:comment_pos].rstrip()

        cleaned_lines.append(line)
    new_txt = "\n".join(cleaned_lines)
    return new_txt.replace("\n\n", "\n")


def extract_lean_block(response):

    TRIPLE_TICK_PATTERN = re.compile(r"```(?:lean|lean4)\n?(.*?)\n?```", re.DOTALL)

    # Attempt to extract the content between triple ticks
    match = TRIPLE_TICK_PATTERN.findall(response)
    if len(match) == 1:
        return match[0]
    elif len(match) > 1:
        log.info("WARNING! Multiple Lean 4 blocks detected. Choosing the last one...")
        log.info("Full response:")
        log.info(response)
        return match[-1]
        # raise ValueError("Multiple Lean 4 code blocks detected.")
    else:
        log.info("No Lean 4 code blocks detected.")
        return None


def _split_at_first_assignment(
    text_input: str, start_idx: int = 0, return_idx: bool = False
) -> Tuple[str, str]:
    """
    Split text at the first := that's not inside parentheses/brackets and not part of a let statement.

    Args:
        text_input: String to split
        start_idx: the index to start the splitting process
        return_idx: whether or not to return the index of the first :=. Defaults to False.
    Returns:
        Tuple of (before_assignment, after_assignment)
    """
    # Use a stack to track bracket depth
    stack = []
    bracket_pairs = {"(": ")", "[": "]", "{": "}"}

    i = start_idx
    in_let_statement = False
    text = remove_comments(text_input)
    while i < len(text):
        char = text[i]
        # Handle brackets
        if char in bracket_pairs:
            stack.append(bracket_pairs[char])
        elif char in bracket_pairs.values():
            if stack and stack[-1] == char:
                stack.pop()
        # Check for "let" statements
        if i <= len(text) - 4 and text[i : i + 4] == "let ":
            # Make sure it's a word boundary
            if (i == 0 or not text[i - 1].isalnum()) and (
                i + 4 >= len(text) or not text[i + 3].isalnum()
            ):
                in_let_statement = True

        # Check for ":=" when stack is empty
        if i < len(text) - 1 and text[i : i + 2] == ":=":
            if in_let_statement:
                # Reset flag after processing let statement
                in_let_statement = False
            elif len(stack) == 0:
                # This is a terminal statement - extract declaration up to this point
                before = text[start_idx:i].strip()
                after = text[i + 2 :].strip()  # +2 to skip ":="
                if return_idx:
                    return before, after, i
                else:
                    return before, after

        i += 1

    # No assignment found at depth 0
    if return_idx:
        return text, "", None
    else:
        return text, ""


def _remove_all_nontheorem_lines(text):
    all_lines = text.split("\n")
    to_include = []
    for idx, line in enumerate(all_lines):
        if line.startswith("theorem") or line.startswith("lemma"):
            to_include = all_lines[idx:]
            break
    if not to_include:
        log.info(100 * "?")
        log.info("Theorem does not have non-theorem lines\n%s", text)
        log.info(100 * "?")
        return None

    new_text = "\n".join(to_include).strip()
    return new_text


def extract_theorem_signature(text):
    """
    Extracts the theorem statement from Lean 4 code, handling various proof constructs.
    Captures everything after 'theorem' up to ':='.
    """
    # if "lemma" in text:
    #     text = text.replace("lemma", "theorem")
    # remove all lines that don't begin with "theorem"
    new_text = _remove_all_nontheorem_lines(text)
    if not new_text:
        return None, None
    before, _ = _split_at_first_assignment(new_text)

    return before


_DECL_START_RE = re.compile(r"(?m)^(lemma|theorem)\s+")
_COMMENT_BLOCK_RE = re.compile(r"/-.*?-/", re.DOTALL)
_COMMENT_LINE_RE = re.compile(r"--.*?$", re.MULTILINE)


def _strip_lean_comments(s: str) -> str:
    s = _COMMENT_BLOCK_RE.sub("", s)
    s = _COMMENT_LINE_RE.sub("", s)
    return s


def _decl_ends_with_sorry(decl_text: str) -> bool:
    t = _strip_lean_comments(decl_text).strip()
    return re.search(r"(?:^|\s)sorry\s*$", t) is not None


def _extract_decl_header(decl_text: str) -> str:
    """
    Match the keys used by your succeeded_proofs.json:
    e.g. "lemma foo (x : ℝ) : P := by"
    """
    m = re.search(r":=\s*by\b", decl_text)
    if m:
        return decl_text[: m.end()].strip()
    # fallback (rare)
    m2 = re.search(r"\bby\b", decl_text)
    if m2:
        return decl_text[: m2.end()].strip()
    return decl_text.strip()


def _normalize_header_key(h: str) -> str:
    # Light normalization to be robust to spacing/newlines differences
    h = h.strip()
    h = re.sub(r"\s+", " ", h)
    return h


def _normalize_proof_text(p: str) -> str:
    # Ensure it ends with a newline for clean concatenation
    p = p.rstrip() + "\n"
    return p


def assemble_full_sketch_from_succeeded_proofs(
    sketch: str, succeeded_proofs: dict
) -> str:
    """
    Replace top-level declarations that end with `sorry` by their full proofs if available.
    The lookup key is the declaration header up to ':= by' (normalized).
    """
    # Build normalized lookup maps. Keep both lemma/theorem header variants.
    lookup = {}
    for k, v in succeeded_proofs.items():
        nk = _normalize_header_key(k)
        lookup[nk] = v
        # Also allow lemma<->theorem swap in the header key
        if nk.startswith("lemma "):
            lookup["theorem " + nk[len("lemma ") :]] = v
        elif nk.startswith("theorem "):
            lookup["lemma " + nk[len("theorem ") :]] = v

    starts = list(_DECL_START_RE.finditer(sketch))
    if not starts:
        return sketch

    out_parts = []
    # Keep everything before the first decl (imports, comments, etc.)
    out_parts.append(sketch[: starts[0].start()])

    for i, m in enumerate(starts):
        s = m.start()
        e = starts[i + 1].start() if i + 1 < len(starts) else len(sketch)
        decl = sketch[s:e].rstrip()

        if _decl_ends_with_sorry(decl):
            header = _extract_decl_header(decl)
            nheader = _normalize_header_key(header)

            proof = lookup.get(nheader)
            if proof is None:
                # Try lemma/theorem swapped header as a fallback
                if nheader.startswith("lemma "):
                    proof = lookup.get("theorem " + nheader[len("lemma ") :])
                elif nheader.startswith("theorem "):
                    proof = lookup.get("lemma " + nheader[len("theorem ") :])

            if proof is not None:
                out_parts.append(_normalize_proof_text(proof))
            else:
                out_parts.append(decl + "\n")
        else:
            out_parts.append(decl + "\n")

    return "".join(out_parts)


# def rename_lean_theorem(source: str, old: str) -> str:
#     new = old + '_renamed_1'
#     pattern = rf"\btheorem\s+{re.escape(old)}\b"
#     matches = re.findall(pattern, source)

#     if len(matches) != 1:
#         raise ValueError(
#             f"Expected exactly one theorem named '{old}', found {len(matches)}"
#         )

#     return re.sub(pattern, f"theorem {new}", source, count=1)
# import Mathlib
# import Aesop

# set_option maxHeartbeats 0

# open BigOperators Real Nat Topology Rat

# theorem factorization (k : ℕ) (f : ℕ → ℕ) (u v : ℕ)
#   (u_def : u = 2 ^ (2 ^ k)) (v_def : v = 3 ^ (2 ^ k))
#   (fk1_via_u_v : f (2 ^ (k + 1)) = u ^ 4 + u ^ 2 * v ^ 2 + v ^ 4)
#   (fk_via_u_v : f (2 ^ k) = u ^ 2 + u * v + v ^ 2)
#   (algebra : ((u ^ 2 + u * v + v ^ 2 : ℤ) * ((u ^ 2 : ℤ) - (u * v : ℤ) + (v ^ 2 : ℤ)) =
#     (u ^ 4 : ℤ) + (u ^ 2 * v ^ 2 : ℤ) + (v ^ 4 : ℤ))) :
#   f (2 ^ (k + 1)) = f (2 ^ k) * (u ^ 2 - u * v + v ^ 2) := by
#   sorry

# ERROR from position {'line': 6, 'column': 8} to {'line': 6, 'column': 21}:
# 'factorization' has already been declared


from typing import Callable, Dict, List, Any, Tuple
import re

BLOCK_RE = re.compile(
    r">>>>SEARCH\s*\n(?P<search>.*?)\n>>>>REPLACE\s*\n(?P<replace>.*?)(?=\n>>>>SEARCH|\Z)",
    re.S,
)

DECL_START_RE = re.compile(r"(?m)^(lemma|theorem)\s+([A-Za-z_][A-Za-z0-9_']*)\b")


def extract_search_replace_blocks(text: str) -> List[Dict[str, str]]:
    blocks = []
    for m in BLOCK_RE.finditer(text):
        blocks.append(
            {
                "search": m.group("search").strip(),
                "replace": m.group("replace").strip(),
            }
        )
    return blocks


def extract_decls_from_replace(replace_block: str) -> List[Dict[str, str]]:
    starts = list(DECL_START_RE.finditer(replace_block))
    decls: List[Dict[str, str]] = []
    if not starts:
        return decls

    for i, m in enumerate(starts):
        kind = m.group(1)
        name = m.group(2)
        start = m.start()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(replace_block)
        chunk = replace_block[start:end].rstrip()
        decls.append({"kind": kind, "name": name, "text": chunk})

    return decls


# start: lemma/theorem + name
HEAD_RE = re.compile(r"^\s*(?:lemma|theorem)\s+[A-Za-z_][A-Za-z0-9_']*\s*", re.S)

# split point: first ":=" (we'll accept ":= by" but don't require by)
SPLIT_RE = re.compile(r"\s*:=\s*by\b", re.S)  # prefer := by
SPLIT_RE_FALLBACK = re.compile(r"\s*:=\s*", re.S)  # fallback if no "by"

WS_RE = re.compile(r"\s+")


def lean_signature(decl_text: str) -> str:
    """
    Build a canonical signature string for a lemma/theorem decl.

    Steps:
      1) cut everything after first ':= by' (fallback ':=')
      2) remove leading 'lemma <name>' or 'theorem <name>'
      3) remove line breaks by normalizing all whitespace to single spaces
    """
    s = decl_text.strip()

    # 1) truncate at first ':= by' (or ':=')
    m = SPLIT_RE.search(s)
    if m:
        s = s[: m.start()]
    else:
        m2 = SPLIT_RE_FALLBACK.search(s)
        if m2:
            s = s[: m2.start()]

    # 2) remove lemma/theorem header (keyword + name)
    s = HEAD_RE.sub("", s, count=1)

    # 3) standardize whitespace / remove newlines
    s = WS_RE.sub(" ", s).strip()

    return s


def assert_no_duplicate_signatures(text: str) -> None:
    """
    Raises ValueError if any REPLACE block contains two decls with the same Lean signature.
    """
    blocks = extract_search_replace_blocks(text)
    blocks_out = []
    for bi, b in enumerate(blocks, start=1):

        replace_block = b["replace"]
        decls = extract_decls_from_replace(replace_block)

        search_decls = extract_decls_from_replace(b["search"])
        search_sig = []
        for d in search_decls : 
            sig = lean_signature(d["text"])
            search_sig.append(sig)

        buckets = {}
        for d in decls:
            sig = lean_signature(d["text"])
            buckets.setdefault(sig, []).append(d)
        duplicated = {sig: ds for sig, ds in buckets.items() if len(ds) > 1 and sig  in search_sig}

        if not duplicated:
            search = b['search']
            stripped = remove_comments(search)

            forbidden = (" true", " True", ": Prop")
            if any(tok in stripped for tok in forbidden):
                log.info(stripped)
                log.error(
                    "Removing : Trivial statements are not allowed. State an explicit mathematical proposition instead."
                )
            else : 
                blocks_out.append(
                    ">>>>SEARCH\n" f"{b['search']}\n" ">>>>REPLACE\n" f"{b['replace']}"
                )

    return "\n".join(blocks_out)

_WS_RE = re.compile(r"\s+")
_BLOCK_COMMENT_RE = re.compile(r"/-[\s\S]*?-/", re.MULTILINE)
_LINE_COMMENT_RE  = re.compile(r"--.*?$", re.MULTILINE)

# Fix: replace \b with a boundary that treats ' as part of the identifier
_DECL_RE = re.compile(
    r"^\s*(lemma|theorem)\s+([A-Za-z_][A-Za-z0-9_']*)(?![A-Za-z0-9_'])",
    re.MULTILINE,
)

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")

def one_line(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()

def strip_comments(src: str) -> str:
    src = re.sub(_BLOCK_COMMENT_RE, "", src)
    src = re.sub(_LINE_COMMENT_RE, "", src)
    return src

def _decl_header(src: str, start: int, end: int) -> str:
    chunk = src[start:end]

    m = re.search(r":=", chunk)
    cut = m.start() if m else None

    m2 = re.search(r"\bwhere\b", chunk)
    if m2 and (cut is None or m2.start() < cut):
        cut = m2.start()

    if cut is None:
        nl = chunk.find("\n")
        cut = nl if nl != -1 else len(chunk)

    return chunk[:cut].strip()

@dataclass(frozen=True)
class Decl:
    kind: str
    name: str
    start: int
    end: int
    body: str
    header1: str

def extract_decls(src: str) -> List[Decl]:
    ms = list(_DECL_RE.finditer(src))
    decls: List[Decl] = []
    for i, m in enumerate(ms):
        kind = m.group(1)
        name = m.group(2)
        start = m.start()
        body_start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(src)
        body = src[body_start:end]

        header = _decl_header(src, start, end)
        header1 = one_line(header)
        decls.append(Decl(kind, name, start, end, body, header1))
    return decls

def build_dependency_graph(decls: List[Decl]) -> Dict[str, Set[str]]:
    """
    Edges: d -> deps(d) (i.e. what d refers to by name).
    Uses only identifiers from the *body* and intersects with known decl names.
    """
    names = {d.name for d in decls}
    graph: Dict[str, Set[str]] = {d.name: set() for d in decls}
    for d in decls:
        tokens = set(_IDENT_RE.findall(d.body))
        graph[d.name] = (tokens & names) - {d.name}
    return graph

def reachable_from_roots(graph: Dict[str, Set[str]], roots: Set[str]) -> Set[str]:
    """Return all nodes reachable by following dependency edges starting at roots."""
    seen: Set[str] = set()
    stack = list(roots)
    while stack:
        u = stack.pop()
        if u in seen:
            continue
        seen.add(u)
        for v in graph.get(u, ()):
            if v not in seen:
                stack.append(v)
    return seen

def default_roots(decls: List[Decl], graph: Dict[str, Set[str]]) -> Set[str]:
    """
    Reasonable default:
    - all theorems are roots if present
    - otherwise, roots are "unreferenced" nodes (not depended-on by any other decl)
    """
    thms = {d.name for d in decls if d.kind == "theorem"}
    if thms:
        return thms

    referenced: Set[str] = set()
    for deps in graph.values():
        referenced |= deps
    return {d.name for d in decls if d.name not in referenced}

def prune_lean_sketch(src: str, roots: Optional[Set[str]] = None) -> tuple[str, Set[str], Set[str]]:
    """
    Returns:
      - pruned source
      - kept decl names
      - removed decl names
    """
    src=remove_comments(src)
    decls = extract_decls(src)
    if not decls:
        return src, set(), set()

    graph = build_dependency_graph(decls)

    if roots is None:
        roots = default_roots(decls, graph)
    else:
        # ignore unknown roots silently
        known = {d.name for d in decls}
        roots = set(r for r in roots if r in known)

    keep = reachable_from_roots(graph, roots)

    removed = {d.name for d in decls} - keep

    # Rebuild: keep prefix before first decl, then keep selected decl blocks in original order.
    out_parts: List[str] = []
    out_parts.append(src[:decls[0].start])

    for d in decls:
        if d.name in keep:
            out_parts.append(src[d.start:d.end])

    pruned = "".join(out_parts)
    return pruned, keep, removed

