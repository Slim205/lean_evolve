EXTRACT_GOAL_SYSTEM = "You are an expert Lean instructor tasked with extracting subgoals from a proof sketch."

EXTRACT_SUBGOALS_FROM_SKETCH_PROMPT = """From this proof sketch, extract any missing proofs (specified with `sorry`) as independent subgoals (theorems). 
Instructions:
1. Each subgoal should have the relevant context from the previous subgoals needed to simplify the proof as much as possible.
2. If a local object was introduced as a definition or abbreviation, you must include its defining equation in the subgoal context.
3. There should be as many extracted theorems as `sorry`s in the given theorem.
4. Do NOT include any imports or open statements. Do NOT add any definitions. ONLY include the theorem statement.
5. Use a separate Lean 4 ``lean`` block for each subgoal.
6. Use sorry for the proof. Do NOT prove any theorem.
7. Do NOT change the conclusion of the theorems from the extracted subgoals. Keep them AS IT IS.
8. Do NOT change the conclusions of the preceding theorems when presenting them as hypotheses for the next subgoals. Keep them AS IT IS.
9. Do NOT duplicate theorem names. Use distinct theorem names for the different theorems. Use similar names to the `have` statements.
10. Make sure the names and types of the premises/arguments in the extracted theorems MATCH the subgoals from which they are extracted.

IMPORTANT INSTRUCTION: Do NOT, under ANY circumstances, allow division and subtraction operations on natural number literals with UNDEFINED types, unless REQUIRED by the theorem statement. For example, do NOT allow literals like `1 / 3` or `2 / 5` or `1 - 3` ANYWHERE in the theorem statement. ALWAYS specify the types. AVOID natural number arithmetic UNLESS NEEDED by the theorem statement.
ALWAYS specify types when describing fractions. For example, ((2 : ℝ) / 3) or ((2 : ℚ) / 3) instead of (2 / 3)

Proof Sketch:
```lean4
{sketch}
```"""


ERROR_CORRECTION_SYSTEM_PROMPT = """You are an expert Lean 4 assistant tasked with repairing theorems from Lean compiler feedback.

Instructions:
1. Enclose the theorem in a ```lean ``` block.
2. Do not include any imports or open statements.
3. Do not include any other Lean code blocks except for the corrected theorem.
"""

THEOREM_CORRECTION_PROMPT = """
The following Lean 4 theorem has compilation errors. Please fix the errors while maintaining the mathematical meaning. 

{theorem}

{error_message}
Instructions:
1. Analyze why the error is happening, step-by-step. Add a brief explanation.
2. Then, provide a corrected version of the Lean 4 code that addresses these specific errors.
3. Do NOT include any other Lean code blocks except for the theorem.
4. Use sorry for the proof.
5. Do NOT include any imports or open statements.
"""

CORRECT_ALL_THEOREMS_PROMPT = """
The following Lean 4 theorems have compilation errors. Your task is to fix the errors while maintaining the mathematical meaning. 

Instructions:
1. Analyze why the error is happening, step-by-step. Add a brief explanation.
2. Then, provide a corrected version of the Lean 4 code that addresses these specific errors.
3. Do NOT include any other Lean code blocks except for the theorem.
4. Use sorry for the proof.
5. Do NOT include any imports or open statements.
6. Enclose each theorem in a ```lean ``` block.

{problem_str}

"""

REPAIR_GOAL_SYSTEM = (
    "You are an expert Lean 4 assistant tasked with repairing subgoal extraction."
)
REPAIR_EXTRACT_SUBGOALS_PROMPT = """The following subgoals were extracted from a Lean 4 proof sketch, but the extraction is incomplete and/or incorrect.
Your task is to REPAIR the extraction while preserving the original intent and keeping each subgoal's conclusion unchanged.

Hard requirements (must follow):

1) Do NOT change the conclusion of any subgoal. Keep it EXACTLY as written (same syntax/formatting where possible).
2) For each subgoal, include ONLY the hypotheses/variables that are necessary and sufficient to make the subgoal well-typed
   and to support a straightforward proof from the sketch (i.e., minimal sufficient context; avoid unrelated leftovers).
3) If a subgoal depends on results from earlier subgoals, include those earlier subgoals' statements as assumptions
   (or include the specific hypotheses they would provide) so the later subgoal can be proved in sequence.
4) Do NOT introduce new definitions, lemmas, abbreviations, notation, imports, `open`, or `variable` sections.
5) Output ONLY theorem statements, one per Lean 4 code block.
6) Use a separate Lean 4 ```lean``` block for EACH subgoal, in the SAME ORDER as the previously extracted subgoals.
7) Each theorem must end with `:= by sorry` (or `by sorry`) and NOTHING ELSE. Do NOT attempt any proofs.
8) Do NOT re-extract from scratch. Only repair what is already extracted: keep the same number of subgoals.
9) Maintain valid Lean 4 syntax and proper indentation.
10) Use explicit types/casts where needed, e.g. `((2 : ℝ) / 3)`, `(k : ℝ)`, `(b : ℤ)`, etc.
11) Move any leading `→` premises in the statement into named hypotheses (arguments) of the theorem whenever possible.
    (Example: turn `A → B → C` into `(hA : A) (hB : B) : C`.) Do NOT change the conclusion.
12) Normalize notation and coercions in the CONTEXT ONLY to standard Lean forms (e.g. replace `* (4 : ℤ) * x` with
    `((4 : ℝ) * x)` if appropriate, normalize casts like `↑a` to `(a : ℝ)`), but DO NOT alter the conclusion text.

Input proof sketch:
```lean
{sketch}
```
Previously extracted subgoals:
{failed_subgoals}
"""

REPAIR_EXTRACT_SUBGOALS_PROMPT_v1 = """The following subgoals were previously extracted from a proof sketch, but the extraction is incomplete or incorrect.
Your task is to REPAIR the extraction while preserving the original intent.

Requirements:

1) Each subgoal should have the relevant context from the previous subgoals needed to simplify the proof as much as possible.
2) Do NOT change the conclusion of any subgoal. Keep it EXACTLY as written.
3) Output ONLY theorem statements (no imports, `open`, or new definitions).
4) Use a separate Lean 4 ```lean``` block for EACH subgoal.
5) Each theorem must end with `by sorry`.
6) Do NOT attempt to prove anything.
7) Do not extract all the subgoals again.
8) Maintain valid Lean syntax and proper indentation.
9) Make sure the types of the premises/arguments in the extracted theorems MATCH the subgoals from which they are extracted.
10) Prefer hypotheses in the context over long `→` chains, and normalize notation and coercions to standard Lean forms without changing the conclusion.

IMPORTANT INSTRUCTION: Do NOT, under ANY circumstances, allow division and subtraction operations on natural number literals with UNDEFINED types, unless REQUIRED by the theorem statement. For example, do NOT allow literals like `1 / 3` or `2 / 5` or `1 - 3` ANYWHERE in the theorem statement. ALWAYS specify the types. AVOID natural number arithmetic UNLESS NEEDED by the theorem statement.
ALWAYS specify types when describing fractions. For example, ((2 : ℝ) / 3) or ((2 : ℚ) / 3) instead of (2 / 3)

Proof sketch:
```lean
{sketch}
```
Previously extracted (incorrect) subgoals:
{failed_subgoals}
"""

REVIEWER_SYSTEM = "You are an expert Lean proof-sketch reviewer who analyzes failed subgoals and provides feedback on the proof sketch."

# REVIEWER_PROMPTs = """You are given:
# 1) A Lean proof sketch.
# 2) One or more failed subgoals produced during the proof.

# Task:
# For each failed subgoal, analyze why it failed and classify the failure into exactly ONE of the following modes.

# Failure modes:

# - HARD: The subgoal is valid but too difficult as stated and requires further decomposition.
#   Recommendation MUST be written in a Lean-like informal proof-plan style (natural language only; NO Lean code), making all non-trivial moves explicit as separate lemma-like steps with dependency tracking.

#   REQUIRED recommendation format for HARD:

#   Lemma chain (dependency-tracked plan)
#   Provide a numbered sequence of lemma-like steps. Each step MUST have:

#   Step k (Lemma <name_k>):
#     Statement: Prove that <precise mathematical statement that advances toward the subgoal>.
#     Input: [ONLY hypotheses from the current subgoal context and/or Outputs of earlier Steps]
#     Output: [exactly one new mathematical fact]

#   Final step :
#     Statement: Prove that <the failed subgoal statement, rewritten as a clear mathematical sentence>.
#     Input: [specific earlier Outputs/Hypotheses that close the goal]
#     Output: [the subgoal statement]
#     Justification (short): <1–3 sentences>

#   HARD constraints:
#   - NO Lean code and NO tactic/command talk.
#   - Do NOT use vague phrases like "clearly", "it follows", "routine", "by rewriting/simplification/cases/induction" without creating an explicit Step that states the needed intermediate fact.
#   - Single-output discipline: each Step produces exactly ONE Output; split if needed.
#   - Keep the plan concise but complete: prefer more steps over hidden reasoning.

# - INCORRECT: The subgoal is either mathematically incorrect or not provable in Lean from the given premises.
#   Recommendation MUST be organized and explicit:

#   REQUIRED recommendation format for INCORRECT:
#   - Why it fails : identify the exact blocker (missing assumption, false claim, wrong direction, type mismatch, insufficient premises).
#   - Minimal repair :
#     * Add assumption: state the minimal additional premise needed; 
#     * Change strategy: propose an alternative intermediate claim that matches available premises and would allow progress.

# Output format (repeat for each failed subgoal):
# #########
# <subgoal>
# Failure mode: <HARD | INCORRECT>
# Recommendation:
# <use the REQUIRED format above>
# #########

# Inputs:
# {sketch}
# {failed_subgoals}
# """

# REVIEWER_PROMPT_new = """You are given:
# 1) A Lean proof sketch.
# 2) One or more failed subgoals produced during the proof.

# Task:
# For each failed subgoal, analyze why it failed and classify the failure into exactly ONE of the following modes.

# Failure modes:

# - HARD: The subgoal is valid but too difficult as stated and requires further decomposition.
#   → Recommendation: Propose a proof *plan* that decomposes this subgoal into smaller intermediate subgoals.
#     REQUIRED format for HARD (lemma chain with dependencies):
#     - Give a numbered sequence of lemma-like steps
#     - Do NOT mention Lean tactics, commands, or implementation details

#     For each step k (Lemma <name_k>):
#       - Statement: A precise mathematical claim that advances toward the subgoal
#       - Input: Only hypotheses from the current subgoal and/or outputs of earlier steps
#       - Output: Exactly ONE new mathematical fact

# - INCORRECT: The subgoal is either mathematically incorrect or not provable in Lean from the given premises.
#   → Recommendation: 
#       - Explain why it is incorrect (missing assumption, false claim, type mismatch, insufficient premises).
#       - Propose how to revise the proof strategy or statement.


# Output format (repeat for each failed subgoal):
# #########
# <subgoal>
# Failure mode: <HARD | INCORRECT>
# Recommendation: <concise, actionable guidance>
# #########

# Inputs:
# {sketch}
# {failed_subgoals}
# """



# REVIEWER_PROMPT = """You are given:
# 1) A Lean proof sketch.
# 2) One or more failed lemmas produced during the proof.

# Task:
# For each failed lemma, analyze why it failed and classify the failure into exactly ONE of the following modes.

# Failure modes:

# - HARD: The lemma is valid but too difficult as stated and requires further decomposition.
#   → Recommendation: Propose a proof *plan* that decomposes this lemma into smaller intermediate subgoals.
#     The plan MUST:
#     - Be written as a numbered sequence of subgoals
#     - Avoid mentioning Lean tactics, commands, or implementation details

# - INCORRECT: The lemma is either mathematically incorrect or not provable in Lean from the given premises.
#   → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.

# Output format (repeat for each failed lemma):
# #########
# <lemma>
# Failure mode: <HARD | INCORRECT>
# Recommendation: <concise, actionable guidance>
# #########

# Inputs:
# {sketch}
# {failed_subgoals}
# """
    #   - Missing assumption: state the needed assumption
    #   - False statement : propose a global change to make the plan work.

# REVIEWER_PROMPT_test = """You are given:
# 1) A Lean proof sketch.
# 2) One failed lemma produced during the proof.
# 3) Informal sketch to prove this lemma.

# The informal sketch has failed to be fully translated. Most likely contain a logical flaw, improve it.
# Inputs:
# {sketch}
# {failed_subgoals}
# """


# REVIEWER_PROMPT_previous = """You are given:
# 1) Previous feedback. 
# 2) A Lean proof sketch after applying the previous feedback.
# 3) One or more failed lemmas produced during the proof.

# Task:
# For each failed lemma, analyze why it failed and classify the failure into exactly ONE of the following modes.

# Failure modes:

# - HARD: The lemma is valid but too difficult as stated and requires further decomposition.
#   → Recommendation: Propose a proof *plan* that decomposes this lemma into smaller intermediate subgoals.

#     OUTPUT FORMAT
#     - First, declare several lemmas (at least 4) as top-level declarations of the form:
#         `lemma <lemma_name> : <concise mathematical statement>.`
#     - Then, at the end, construct the glue: an informal explanation of how these lemmas combine to prove the original statement.
#     - Each lemma should represent a single logical step that will be invoked in the glue.
#     - Output ONLY the informal proof. No Lean code.
#     - Do not create a lemma that has the same goal as the original statement.

#     FORMAT
#     lemma <lemma_name> : <statement>.
#     ...
#     theorem <formal_theorem_name> : <glue explanation>

#     example :

#     -- Formal theorem:
#     --   lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry.

#     lemma not_p_to_q : if P is false, then Q.

#     lemma q_to_r : if Q is true, then R.

#     lemma r_to_disjunction : if R is true, then P or R.

#     lemma p_to_disjunction : if P is true, then P or R.

#     lemma demo_seed_style : prove P ∨ R.
#     To prove that P or R holds, split into cases on whether P is true.
#     - If P is true, apply lemma p_to_disjunction to conclude P or R.
#     - If P is false, use lemma not_p_to_q to obtain Q, then lemma q_to_r to obtain R,
#     and finally lemma r_to_disjunction to conclude P or R.

# - INCORRECT: The lemma is either mathematically incorrect or not provable in Lean from the given premises.
#   → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.

# Output format (repeat for each failed lemma):
# #########
# <Failed lemma>
# Failure mode: <HARD | INCORRECT>
# Recommendation: <concise, actionable guidance>
# #########

# Inputs:
# {previous_failure}
# {sketch}
# {failed_subgoals}
# """

EVAL_MUTATION = """You are given:
1) A Lean proof sketch.
2) One or more failed lemmas produced during the proof.
3) A previous mutation plan that was proposed to improve the current sketch.
4) Feedback from executing that mutation plan on the Lean sketch.

Your task is to edit the previous mutation plan to reflect the insights obtained from the feedback after executing it.

This is how a mutation plan / feedback is constructed:
      For each failed lemma, analyze why it failed and classify the failure into exactly ONE of the following modes.

      Failure modes:

      - HARD: The lemma is valid but too difficult as stated and requires further decomposition.
        → Recommendation: Propose a proof *plan* that decomposes this lemma into smaller intermediate subgoals.

        OUTPUT FORMAT
        - First, declare several lemmas (at least 4) as top-level declarations of the form:
            `lemma <lemma_name> : <concise mathematical statement>.`
        - Then, at the end, construct the glue: an informal explanation of how these lemmas combine to prove the original statement.
        - Each lemma should represent a single logical step that will be invoked in the glue.
        - Output ONLY the informal proof. No Lean code.
        - Do not create a lemma that has the same goal as the original statement.

        FORMAT
        lemma <lemma_name> : <statement>.
        ...
        theorem <formal_theorem_name> : <glue explanation>

        Example:

        -- Formal theorem:
        --   lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry.

        lemma not_p_to_q : if P is false, then Q.
        lemma q_to_r : if Q is true, then R.
        lemma r_to_disjunction : if R is true, then P or R.
        lemma p_to_disjunction : if P is true, then P or R.

        lemma demo_seed_style : prove P ∨ R.
        To prove that P or R holds, split into cases on whether P is true.
        - If P is true, apply lemma p_to_disjunction to conclude P or R.
        - If P is false, use lemma not_p_to_q to obtain Q, then lemma q_to_r to obtain R,
          and finally lemma r_to_disjunction to conclude P or R.

      - INCORRECT: The lemma is either mathematically incorrect or not provable in Lean from the given premises.
        → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.

      Output format (repeat for each failed lemma):
      #########
      <Failed lemma>
      Failure mode: <HARD | INCORRECT>
      Recommendation: <concise, actionable guidance>
      #########

For your improved mutation plan, For each failed lemma :
        - Add one sentence explaining what the previous plan did and whether you will kepp it or changed.
        - add one sentence presenting the ideas that we should not try in future mutations based on the feedback.
        - Present this part in this format : 
            Previous Mistakes : <concise, actionable guidance>

Inputs:
Current sketch:
{sketch}

Failed subgoals:
{failed_subgoals}

---------------------------------------------------------------
This is the previous mutation plan that you will edit:
{previous_feedback}
---------------------------------------------------------------

This is the feedback obtained after executing the previous mutation plan:
{children_feedback}

-------------------------
OUTPUT FORMAT (MANDATORY)
-------------------------
You MUST output one or more edit blocks using the following **exact** structure.

>>>>SEARCH
[exact substring copied verbatim from the previous mutation plan that contains the error]
>>>>REPLACE
[corrected version of that substring]
"""

# 1) Previous feedback. 
# 0) the informal proof for the sketch.
# 1) Previous feedback. 

#  (at least 4)
REVIEWER_PROMPThhh = """You are given:
1) A Lean proof sketch after applying the previous feedback.
2) One or more failed lemmas produced during the proof.

Task:
For each failed lemma, analyze why it failed and classify the failure into exactly ONE of the following modes.

Failure modes:

- HARD: The lemma is valid but too difficult as stated and requires further decomposition.
  → Recommendation: Propose a proof *plan* that decomposes this lemma into smaller intermediate subgoals.

    OUTPUT FORMAT
    - First, declare several lemmas as top-level declarations of the form:
        `lemma <lemma_name> : <concise mathematical statement>.`
    - Then, at the end, construct the glue: an informal explanation of how these lemmas combine to prove the original statement.
    - Each lemma should represent a single logical step that will be invoked in the glue.
    - Output ONLY the informal proof. No Lean code.
    - Do not create a lemma that has the same goal as the original statement.
    - While decomposing prefer using lemmas that are already in the sketch and appears before the failed lemma.

    FORMAT
    lemma <lemma_name> : <statement>.
    ...
    theorem <formal_theorem_name> : <glue explanation>

    example :

    -- Formal theorem:
    --   lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry.

    lemma not_p_to_q : if P is false, then Q.

    lemma q_to_r : if Q is true, then R.

    lemma r_to_disjunction : if R is true, then P or R.

    lemma p_to_disjunction : if P is true, then P or R.

    lemma demo_seed_style : prove P ∨ R.
    To prove that P or R holds, split into cases on whether P is true.
    - If P is true, apply lemma p_to_disjunction to conclude P or R.
    - If P is false, use lemma not_p_to_q to obtain Q, then lemma q_to_r to obtain R,
    and finally lemma r_to_disjunction to conclude P or R.

- INCORRECT: The lemma is either mathematically incorrect or not provable in Lean from the given premises.
  → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.

Output format (repeat for each failed lemma):
---------
<Failed lemma>
Failure mode: <HARD | INCORRECT>
Recommendation: <concise, actionable guidance>
---------

IMPORTANT: 
In Nat, subtraction and division are truncated.
  In particular, x - y = 0 whenever x ≤ y, and / is integer (floor) division.
  Over ℕ, x - y is a true difference only when y ≤ x.

Inputs:
{sketch}
{failed_subgoals}
"""
# Informal proof : 
# {informal_proof}
# Current Sketch :   Propose a clear plan on how to change the overall proof to avoid this lemma.

# Explain why it is incorrect and how to revise the proof strategy or statement.
# {informal_proof}
# {previous_failure}
# IMPORTANT:
# Be aware of subtraction and division truncation in Lean. In Nat, x - y does not behave the same way as in Int, and the same applies to division (/). Therefore, in your reasoning, make sure to account for these differences. Recommendation: always check whether expressions are evaluated in Nat or Int, and convert explicitly when necessary.
# IMPORTANT INSTRUCTION: Do NOT, under ANY circumstances, allow division and subtraction operations on natural number literals with UNDEFINED types, unless REQUIRED by the theorem statement. For example, do NOT allow literals like `1 / 3` or `2 / 5` or `1 - 3` ANYWHERE in the theorem statement. ALWAYS specify the types. AVOID natural number arithmetic UNLESS NEEDED by the theorem statement.
# ALWAYS specify types when describing fractions. For example, ((2 : ℝ) / 3) or ((2 : ℚ) / 3) instead of (2 / 3)

# IMPORTANT: 
# In Nat, subtraction and division are truncated.
#   In particular, x - y = 0 whenever x ≤ y, and / is integer (floor) division.
#   Do not treat x - y as a true difference unless you have y ≤ x.

# IMPORTANT: 
# In Nat, subtraction and division are truncated.
#   In particular, x - y = 0 whenever x ≤ y, and / is integer (floor) division.
#   Over ℕ, x - y is a true difference only when y ≤ x.
  

REVIEWER_PROMPT_1_llm = """You are given:
1) A Lean proof sketch after applying the previous feedback.
2) One failed lemma produced during the proof.

Task:
Analyze why the lemma failed and classify the failure into exactly ONE of the following modes.

Failure modes:

- HARD: The lemma is valid but too difficult as stated and requires further decomposition.
  → Recommendation: Propose a proof *plan* that decomposes this lemma into smaller intermediate subgoals.
    The plan MUST:
    - Be written as a numbered sequence of subgoals
    - Avoid mentioning Lean tactics, commands, or implementation details

- INCORRECT: The lemma is either mathematically incorrect or not provable in Lean from the given premises.
  → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.


Output format :
---------
<Failed lemma>
Failure mode: <HARD | INCORRECT>
Recommendation: <concise, actionable guidance>
---------

IMPORTANT: 
In Nat, subtraction and division are truncated.
  In particular, x - y = 0 whenever x ≤ y, and / is integer (floor) division.
  Over ℕ, x - y is a true difference only when y ≤ x.

Inputs:
{sketch}
{failed_subgoals}
"""

REVIEWER_PROMPT_old = """You are given:
1) A Lean proof sketch.
2) One or more failed subgoals produced during the proof.

Task:
For each failed subgoal, analyze why it failed and classify the failure into exactly ONE of the following modes.

Failure modes:

- HARD: The subgoal is valid but too difficult as stated and requires further decomposition.
  → Recommendation: Propose a proof *plan* that decomposes this subgoal into smaller intermediate subgoals.
    The plan MUST:
    - Be written as a numbered sequence of subgoals
    - Avoid mentioning Lean tactics, commands, or implementation details

- INCORRECT: The subgoal is either mathematically incorrect or not provable in Lean from the given premises.
  → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.

Output format (repeat for each failed subgoal):
#########
<subgoal>
Failure mode: <HARD | INCORRECT>
Recommendation: <concise, actionable guidance>
#########

Inputs:
{sketch}
{failed_subgoals}
"""

REVIEWER_PROMPT= """You are given:
1) A Lean proof sketch.
2) One or more failed lemmas produced during the proof.

Task:
For each failed lemma, analyze why it failed and classify the failure into exactly ONE of the following modes.

Failure modes:

- HARD: The lemma is valid but too difficult as stated and requires further decomposition.
  → Recommendation: Propose a proof *plan* that decomposes this subgoal into smaller intermediate lemmas.
    The plan MUST:
    - Be written as a numbered sequence of lemmas
    - Avoid mentioning Lean tactics, commands, or implementation details

- INCORRECT: The lemma is either mathematically incorrect or not provable in Lean from the given premises.
  → Recommendation: Explain why it is incorrect and how to revise the proof strategy or statement.

Output format (repeat for each failed lemma):
Output format :
---------
<Failed lemma>
Failure mode: <HARD | INCORRECT>
Recommendation: <concise, actionable guidance>
---------

IMPORTANT: 
In Nat, subtraction and division are truncated.
  In particular, x - y = 0 whenever x ≤ y, and / is integer (floor) division.
  Over ℕ, x - y is a true difference only when y ≤ x.

Inputs:
{sketch}
{failed_subgoals}
"""

    # - While decomposing prefer using lemmas that are already in the sketch and appears before the failed lemma. : the llm can do it by itself.

HINT_PROMPT = """You are given a Lean sketch that failed to compile.

Carefully read the Lean sketch and the Lean error messages, and identify the main cause of the lean error.

Then write a one-line hint describing a general best practice for formalisation that would help avoid similar syntax errors in the future.

Lean sketch:
{sketch}

Lean errors:
{error_message}

Output format:
------
Cause: <cause>
------
Hint: <hint>
"""
