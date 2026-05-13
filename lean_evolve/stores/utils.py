import re
from typing import List, Dict, Any, Tuple

# --- Regexes ---
BLOCK_RE = re.compile(
    r">>>>SEARCH\s*\n(?P<search>.*?)\n>>>>REPLACE\s*\n(?P<replace>.*?)(?=\n>>>>SEARCH|\Z)",
    re.S,
)

DECL_RE = re.compile(
    r"(?P<kw>lemma|theorem)\s+"
    r"(?P<name>[A-Za-z0-9_']+)\b"
    r"(?P<sig>.*?):=\s*by"
    r"(?P<body>.*?)(?=^\s*(?:lemma|theorem)\b|\Z)",
    re.S | re.M,
)


def _extract_decls(text: str) -> List[Dict[str, Any]]:
    """Extract top-level lemma/theorem decls from a Lean snippet (best-effort, regex-based)."""
    decls: List[Dict[str, Any]] = []
    for m in DECL_RE.finditer(text):
        kw = m.group("kw")
        name = m.group("name")
        sig = m.group("sig").strip()
        body = m.group("body").strip()

        has_sorry = bool(re.search(r"\bsorry\b", body))
        have_count = len(re.findall(r"\bhave\b", body))

        decls.append(
            {
                "kw": kw,
                "name": name,
                "sig": sig,
                "body": body,
                "has_sorry": has_sorry,
                "have_count": have_count,
            }
        )
    return decls


def _word_in_text(word: str, text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def analyze_mutation_output(mutation_output: str) -> List[Dict[str, Any]]:

    results: List[Dict[str, Any]] = []

    blocks = list(BLOCK_RE.finditer(mutation_output))
    for i, bm in enumerate(blocks):
        search_txt = bm.group("search")
        replace_txt = bm.group("replace")

        search_decls = _extract_decls(search_txt)
        replace_decls = _extract_decls(replace_txt)

        # --- finding: is_syntaxt ---
        # "search has 1 lemma with sorry"
        cond_search = len(search_decls) == 1 and search_decls[0]["has_sorry"] is True

        # "replace has two lemmas one is with sorry and the other one without sorry"
        # (order-agnostic)
        cond_replace = False
        if len(replace_decls) == 2:
            has = [d["has_sorry"] for d in replace_decls]
            cond_replace = has.count(True) == 1 and has.count(False) == 1

        is_syntaxt = bool(cond_search and cond_replace)

        # --- finding: is_sufficiant_have ---
        # For every decl that does NOT contain sorry, require >= 2 "have"
        ok = True
        for d in replace_decls:
            if not d["has_sorry"]:
                if d["have_count"] < 2:
                    ok = False
                    break
        is_sufficiant_have = ok

        # --- finding: is_first_lemma_used ---
        # "the first lemmas is used in the second lemmas"
        is_first_lemma_used = False
        if len(replace_decls) >= 2:
            first_name = replace_decls[0]["name"]
            second_body = replace_decls[1]["body"]
            is_first_lemma_used = _word_in_text(first_name, second_body)

        is_bad = is_syntaxt and is_first_lemma_used and not is_sufficiant_have

        if not is_bad:
            return False

    return True
