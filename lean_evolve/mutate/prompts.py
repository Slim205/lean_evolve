SUBGOAL_MUTATION_SYSTEM_PROMPT = "Act as an expert Lean proof–sketch writer. Your task is to iteratively improve the current Lean sketch by analyzing the issues in the previous generation."

PROOF_SKETCH_CORRECTION_SYSTEM = "You are a Lean expert capable of interpreting Lean's error messages and feedback, and using them to refine and improve proof sketches."
# - Do not remove any have statement from the sketch.
# - If you see a no goals to be solved error, the goal was already solved by earlier tactics, so you can remove the remaining ones.


# PROOF_SKETCH_CORRECTION_PROMPT_old = """Your task is to minimally revise the Lean proof sketch using the Lean error messages below.

# You MUST modify **ONLY** the exact parts of the sketch that correspond to the reported errors.
# Do NOT introduce any new proof content.

# STRICT RULES :
# - Do NOT prove anything; all subgoals must remain as `sorry`.
# - Do NOT modify any part of the sketch unrelated to the failing errors.
# - Do NOT remove any existing `have` statements.
# - Preserve the original structure, ordering, and indentation of the sketch.
# - Ensure the result is valid Lean syntax.
# - Do not change the mathematical conclusion of each theorem. keep it as it is.

# Lean proof sketch:
# {sketch}

# Failing Lean errors:
# {error_message}

# RESPONSE FORMAT (mandatory):
# You MUST output one or more edit blocks using the following exact structure.
# Output NOTHING else.

# >>>>SEARCH
# <exact substring copied verbatim from the original sketch that contains the error>
# >>>>REPLACE
# <corrected version of that substring, preserving `sorry`>

# ADDITIONAL CONSTRAINTS (must always be satisfied):
# - Always cast numeric literals to an explicit type (`ℤ`, `ℚ`, or `ℝ`) before arithmetic when required.
# - Always specify the type of numeric literals in division or subtraction:
#   - Correct: `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`
#   - Incorrect: `2 / 3`

# Output ONLY the SEARCH/REPLACE blocks. No explanations, no comments, no extra text.
# """

PROOF_SKETCH_CORRECTION_PROMPT = """Fix the Lean *lemma-style* sketch using the Lean error messages.

You MUST edit ONLY the smallest parts that directly correspond to the reported errors.
Do NOT add new lemmas, new `have`s, or new proof steps. Do NOT change the proof plan.

STRICT RULES:
- Do NOT introduce any new `sorry`.
- Do NOT replace any existing proof term with `sorry`.
- Existing `sorry` may remain exactly where they already are.
- Do NOT modify any part of the sketch unrelated to the errors.
- Preserve the original structure, ordering, and indentation.
- Ensure the result is valid Lean syntax.

Lean sketch:
{sketch}

Lean errors:
{error_message}

RESPONSE FORMAT (mandatory):
Output ONLY one or more edit blocks, nothing else.

>>>>SEARCH
<exact substring copied verbatim from the sketch that contains the error>
>>>>REPLACE
<corrected version of that substring (no new `sorry`)>

Output ONLY the SEARCH/REPLACE blocks. No explanations, no comments, no extra text.
"""
# ADDITIONAL CONSTRAINTS:
# - Always cast numeric literals to an explicit type (`ℤ`, `ℚ`, or `ℝ`) before arithmetic when required.
# - Always type numeric literals in division/subtraction when needed:
#   - Correct: `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`
#   - Incorrect: `2 / 3`
# - Do NOT remove or reorder any existing `have` / `rcases` / `cases` / `by_cases`.

# ***IMPORTANT*** : 
# Change only the glue. Do not modify any lemma/theorem statements or goals or permises. Your task is to fix the Lean errors that arise in the glue code, which combines results by invoking the helper lemmas.

SUBGOAL_PROMPT = """Your task is to iteratively improve the given Lean sketch by analyzing why the previous generation failed.

A sketch can fail for two reasons:
1. Subgoals are too difficult — they need further decomposition.
2. Subgoals are logically incorrect or unprovable — the proof plan or structure must be revised.

Your job:
- Read the previous sketch and the failed subgoals carefully and identify exactly why they failed.
- Produce an improved sketch that:
  - Ensures all subgoals are logically correct.
  - Fixes incorrect or unprovable subgoals by adjusting the proof plan.
  - Breaks difficult subgoals into simpler helper subgoals.

Subgoal Evaluation Criteria:
1. Mathematical correctness: no logical errors or invalid assumptions.
2. Provability: the subgoal must be provable from the given premises.
3. Syntax is guaranteed correct; do not assess it.

This is the current proof sketch : 
{sketch}
Score: {score} (max 1 = fully correct).

The current subgoals that failed:
{sketch_errors}

-------------------------
CRITICAL RULES
-------------------------
- Do NOT prove any subgoal — all goals must still end with `sorry`.
- Maintain valid Lean syntax and proper indentation.
- Do NOT change anything in the original theorem statement.
- Decomposition means breaking failing subgoals into several intermediate steps, all ending with `sorry`.

-------------------------
OUTPUT FORMAT (MANDATORY)
-------------------------
Your response must follow *exactly* this structure:

>>>>SEARCH
[exact substring copied verbatim from the current sketch that contains the error]
>>>>REPLACE
[corrected version of that substring, with all `sorry` preserved]
"""


SUBGOAL_PROMPT_Hint = """Your task is to iteratively improve the given Lean sketch by analyzing why the previous generation failed.

A sketch can fail for two reasons:
1. Subgoals are too difficult — they need further decomposition.
2. Subgoals are logically incorrect or unprovable — the proof plan or structure must be revised.

Your job:
- Read the previous sketch and the failed subgoals carefully and identify exactly why they failed.
- Produce an improved sketch that:
  - Ensures all subgoals are logically correct.
  - Fixes incorrect or unprovable subgoals by adjusting the proof plan.
  - Breaks difficult subgoals into simpler helper subgoals.

Subgoal Evaluation Criteria:
1. Mathematical correctness: no logical errors or invalid assumptions.
2. Provability: the subgoal must be provable from the given premises.
3. Syntax is guaranteed correct; do not assess it.

-------------------------
CRITICAL RULES
-------------------------
- Do NOT prove any subgoal — all goals must still end with `sorry`.
- Maintain valid Lean syntax and proper indentation.
- Do NOT change anything in the original theorem statement.
- Decomposition means breaking failing subgoals into several intermediate steps, all ending with `sorry`.

-------------------------
OUTPUT FORMAT (MANDATORY)
-------------------------
Your response must follow *exactly* this structure:

>>>>SEARCH
[exact substring copied verbatim from the current sketch that contains the error]
>>>>REPLACE
[corrected version of that substring, with all `sorry` preserved]

This is the current proof sketch : 
{sketch}
Score: {score} (max 1 = fully correct).

The current subgoals that failed:
{sketch_errors}

Hints :
{hints}
"""

# REVIEWER_PROMPT_v1 = """Your task is to analyze why the previous Lean sketch failed.

# A sketch can fail for two reasons:
# 1. Subgoals are too difficult — they need further decomposition.
# 2. Subgoals are logically incorrect or unprovable — the proof plan or structure must be revised.

# Your job:
# - Read the previous sketch and the failed subgoals carefully and identify exactly why they failed.
# - Produce a natural-language diagnosis and recommendations that:
#   - Explain which assumptions or steps are invalid or missing.
#   - Indicate which subgoals are unprovable as stated.
#   - Identify subgoals that are likely provable but too complex and should be decomposed.
#   - Suggest *how* the proof plan should change, without writing Lean code.

# Subgoal Evaluation Criteria:
# 1. Mathematical correctness: no logical errors or invalid assumptions.
# 2. Provability: the subgoal must be provable from the given premises.
# 3. Syntax is guaranteed correct; do not assess it.

# -------------------------
# CRITICAL RULES
# -------------------------
# - Do NOT generate or modify any Lean code.
# - Do NOT prove any subgoal.
# - Do NOT propose a rewritten sketch.
# - Do NOT change the original theorem statement.
# - Focus strictly on diagnosis and high-level recommendations.
# - Be concise and precise.

# -------------------------
# INPUTS
# -------------------------
# CURRENT SKETCH:
# {sketch}

# FAILED SUBGOALS:
# {failed_subgoals}
# """

# SUBGOAL_MUTATION_PROMPT_V1 = """Your task is to iteratively improve the given Lean sketch by analyzing why the previous generation failed.

# A sketch can fail for two reasons:
# 1. Subgoals are too difficult — they need further decomposition.
# 2. Subgoals are logically incorrect or unprovable — the proof plan or structure must be revised.

# Your job:
# - Read the previous sketch carefully and identify exactly why it failed.
# - Produce an improved sketch that:
#   - Ensures all subgoals are logically correct.
#   - Fixes incorrect or unprovable subgoals by adjusting the proof plan.
#   - Breaks difficult subgoals into simpler helper subgoals.
#   - Leaves `sorry` for all nontrivial reasoning.

# Subgoal Evaluation Criteria:
# 1. Mathematical correctness: no logical errors or invalid assumptions.
# 2. Provability: the subgoal must be provable from the given premises.
# 3. Do NOT evaluate the correctness of the premises themselves.
# 4. Syntax is guaranteed correct; do not assess it.

# This is the current proof sketch : 
# {sketch_to_evolve}
# Score: {score} (max 1 = fully correct).

# The current subgoals that failed:
# {sketch_to_evolve_error}

# Inspiration Sketch:
# {inspiration_sketch}
# Score: {inspiration_score}

# Failed Subgoals from Inspiration Sketch:
# {inspiration_sketch_errors}

# -------------------------
# CRITICAL RULES
# -------------------------
# - Do NOT prove any subgoal — all goals must still end with `sorry`.
# - Maintain valid Lean syntax and proper indentation.
# - Keep every `sorry` placeholder exactly where it appears.

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# Your response must follow *exactly* this structure:

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, reusing inspiration where useful, with all `sorry` preserved]
# """


SUBGOAL_MUTATION_PROMPT = """Your task is to iteratively improve the given Lean sketch by analyzing why the previous generation failed.

A sketch can fail for two reasons:
1. Subgoals are too difficult — they need further decomposition.
2. Subgoals are logically incorrect or unprovable — the proof plan or structure must be revised.

Your job:
- Read the previous sketch and the failed subgoals carefully and identify exactly why they failed.
- Produce an improved sketch that:
  - Ensures all subgoals are logically correct.
  - Fixes incorrect or unprovable subgoals by adjusting the proof plan.
  - Breaks difficult subgoals into simpler helper subgoals.

Subgoal Evaluation Criteria:
1. Mathematical correctness: no logical errors or invalid assumptions.
2. Provability: the subgoal must be provable from the given premises.
3. Syntax is guaranteed correct; do not assess it.

Current proof sketch  : 
{sketch_to_evolve}
Score: {score} (max 1 = fully correct).

The current subgoals that failed:
{sketch_to_evolve_error}

Inspiration Sketch:
{inspiration_sketch}
Score: {inspiration_score} (max 1 = fully correct).

Failed Subgoals from Inspiration Sketch:
{inspiration_sketch_errors}

-------------------------
CRITICAL RULES
-------------------------
- Do NOT prove any subgoal — all goals must still end with `sorry`.
- Maintain valid Lean syntax and proper indentation.
- Do NOT change anything in the original theorem statement.
- Decomposition means breaking failing subgoals into several intermediate steps, all ending with `sorry`.

-------------------------
OUTPUT FORMAT (MANDATORY)
-------------------------
Your response must follow *exactly* this structure:

>>>>SEARCH
[exact substring copied verbatim from the current sketch that contains the error]
>>>>REPLACE
[corrected version of that substring, with all `sorry` preserved]
"""

# REVIEWER_SYSTEM = "You are an expert proof-plan reviewer for an evolutionary Lean sketch-repair framework. Your task is to analyze why the previous Lean sketch failed."

MUTATOR_SYSTEM = "Act as an expert Lean proof–sketch writer. Your task is to iteratively improve the current Lean sketch using the provided feedback."
# MUTATOR_PROMPT_v3 = """Your task is to improve the given Lean sketch using the provided feedback.

# Your job:
# - Produce an improved sketch by applying the feedback:
#   - Fix incorrect subgoals as identified in the feedback.
#   - Break difficult subgoals into several intermediate `have` statements when recommended.
#   - Leave all subgoals ending with `sorry`.

# RULES : 
# - You MUST base your changes exclusively on the provided feedback.
# - Extract as much concrete structure as possible from the feedback
# - Do NOT prove any subgoal — all goals must still end with `sorry`.
# - Do NOT change anything in the original theorem statement.
# - Maintain valid Lean syntax and proper indentation.

# OUTPUT FORMAT : 
# Your response must follow *exactly* this structure:

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]

# This is the current proof sketch :
# {sketch}

# Feedback:
# {sketch_rating}
# """

# MUTATOR_PROMPT_v_2026 = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

# A sketch can fail for two reasons:
# 1. Subgoals are too difficult — they need further decomposition.
# 2. Subgoals are logically incorrect or unprovable — the proof plan or structure must be revised.

# Your job:
# - Read the previous sketch and the reviewer feedback carefully.
# - Produce an improved sketch that:
#   - Fixes incorrect subgoals as identified in the feedback..
#   - Breaks difficult subgoals into simpler helper subgoals.
#   - Leave all subgoals ending with `sorry`.

# This is the current proof sketch :
# {sketch}

# Feedback:
# {sketch_rating}

# -------------------------
# CRITICAL RULES
# -------------------------
# - Do NOT prove any subgoal — all goals must still end with `sorry`.
# - Maintain valid Lean syntax and proper indentation.
# - Do NOT change anything in the original theorem statement.
# - Decomposition means breaking failing subgoals into several intermediate steps, all ending with `sorry`.

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# You MUST output one or more edit blocks using the following **exact** structure.

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """

# MUTATOR_PROMPT_v1 = """Your task is to improve the given Lean sketch using the provided feedback.

# RULES : 
# - Fix incorrect subgoals as identified in the feedback.
# - Break difficult subgoals into several intermediate `have` statements when recommended.
# - Do NOT prove any subgoal — all goals must still end with `sorry`.
# - Maintain valid Lean syntax and proper indentation.
# - Do NOT change anything in the original theorem statement.

# OUTPUT FORMAT : 
# Your response must follow *exactly* this structure:

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]

# This is the current proof sketch :
# {sketch}

# Feedback:
# {sketch_rating}
# """

# MUTATOR_PROMPT2 = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

# This sketch uses a lemma-first style:
# - There are top-level `lemma ... := by sorry` declarations.
# - The target lemma/theorem body should be *glue code* that chains lemma calls with:
#   `by_cases`, `have`, `rcases/cases`, `exact`.

# A sketch can fail for two reasons:
# 1) Subgoals are too difficult → they need further decomposition into helper lemmas.
# 2) Subgoals are logically incorrect/unprovable → revise the lemma statements and/or glue structure.

# Your job:
# - Read the current sketch and the feedback carefully.
# - Produce an improved sketch that:
#   - Fixes incorrect subgoals.
#   - Breaks difficult steps into helper lemmas.
#   - Critically: **rewrites the failing lemma/theorem body to USE the new helper lemmas**.

# This is the current proof sketch:
# {sketch}

# Feedback:
# {sketch_rating}

# -------------------------
# CRITICAL RULES
# -------------------------
# - Do NOT prove any nontrivial goal: helper lemmas must end with `sorry`.
# - Maintain valid Lean syntax and proper indentation.
# - Do NOT change anything in the original theorem statement.
# - Do NOT “cheat” by introducing a wrapper lemma equivalent to the original goal.
# - If you introduce helper lemmas, you MUST also:
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to *interleave* calls to those lemmas.

# -------------------------
# MANDATORY GLUE STRUCTURE
# -------------------------
# When decomposing a hard lemma L:
# 1) Add helper lemmas (top-level) with `:= by sorry`.
# 2) Replace the body of L with a glue chain that explicitly invokes them, e.g.

# by
#   have h1 : T1 := by exact helper1 ...
#   rcases h1 with ⟨...⟩   -- when T1 is existential/conjunction
#   have h2 : T2 := by exact helper2 ... -- using earlier bound vars
#   ...
#   -- final assembly    
#   exact ...     

# Do not include `sorry` in the glue chain. 

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# You MUST output one or more edit blocks using the following **exact** structure.

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """

# MUTATOR_PROMPT = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

# This sketch uses a lemma-first style:
# - There are top-level `lemma ... := by sorry` declarations.
# - The target lemma/theorem body should be *glue code* that chains lemma calls with:
#   `by_cases`, `have`, `rcases/cases`, `exact`.

# A sketch can fail for two reasons:
# 1) Subgoals are too difficult → they need further decomposition into helper lemmas.
# 2) Subgoals are logically incorrect/unprovable → revise the lemma statements and/or glue structure.

# Your job:
# - Read the current sketch and the feedback carefully.
# - Produce an improved sketch that:
#   - Fixes incorrect subgoals.
#   - Breaks difficult steps into helper lemmas.
#   - Critically: **rewrites the failing lemma/theorem body to USE the new helper lemmas**.

# This is the current proof sketch:
# {sketch}

# Feedback:
# {sketch_rating}
 
# -------------------------
# CRITICAL RULES
# -------------------------
# - Maintain valid Lean syntax and proper indentation.
# - Do NOT change anything in the original theorem statement.
# - Do NOT write a single wrapper lemma that proves the whole theorem and then `exact wrapper`.
# - The lemmas need to be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the provided feedback.
# - If you introduce helper lemmas, you MUST also:
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to *interleave* calls to those lemmas.

# -------------------------
# MANDATORY GLUE STRUCTURE
# -------------------------
# When decomposing a hard lemma L:
# 1) Add helper lemmas (top-level) with `:= by sorry`.
# 2) Replace the body of L with a glue chain that combines results by calling those helper lemmas, not by solving directly,  e.g.

# by
#   have h1 : T1 := by exact helper1 ...
#   rcases h1 with ⟨...⟩   -- when T1 is existential/conjunction
#   have h2 : T2 := by exact helper2 ... -- using earlier bound vars
#   ...
#   -- final assembly    
#   exact ...     

# Do not include `sorry` in the glue chain. 

# -------------------------
# EXAMPLE (FOLLOW THIS STYLE)
# -------------------------
# >>>>SEARCH
# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry
# >>>>REPLACE
# lemma notP_to_Q_lemma (P Q : Prop) (hnotP : ¬ P) : Q := by
#   sorry

# lemma Q_to_R_lemma (Q R : Prop) (hQ : Q) : R := by
#   sorry

# lemma R_to_disj_lemma (P R : Prop) (hR : R) : P ∨ R := by
#   sorry

# lemma P_to_disj_lemma (P R : Prop) (hP : P) : P ∨ R := by
#   sorry

# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by
#   by_cases hP : P
#   · -- Case 1: P
#     have h1 : P ∨ R := by
#       exact P_to_disj_lemma P R hP
#     exact h1
#   · -- Case 2: ¬P
#     have hQ : Q := by
#       exact notP_to_Q_lemma P Q hP
#     have hR : R := by
#       exact Q_to_R_lemma Q R hQ
#     have h2 : P ∨ R := by
#       exact R_to_disj_lemma P R hR
#     exact h2

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# You MUST output one or more edit blocks per failed subgoal using the following **exact** structure.

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """

# - Do NOT “decompose” by introducing an auxiliary lemma with a (near-)identical statement and making the original proof just `exact/simpa/refine` that lemma.
# - Do NOT “decompose” by adding an auxiliary lemma with a (near-)identical statement and making the original proof just `exact/simpa/refine` that auxiliary; decomposition must introduce genuinely simpler helper lemmas with different statements and the rewritten body must chain at least two of them via `have ... := by exact ...`.
# - - Do not use `True` or `Prop` or `true` as a statement. State an explicit mathematical proposition instead.

# -  Do not introduce any lemma whose conclusion is the same as (or a trivial rewrite of) the target theorem and then finish by exact-ing that lemma; helper lemmas must state strictly intermediate facts that the theorem combines.

#   exact ...              -- may still end with `sorry` only if absolutely needed,
#                          -- but must show the chain of lemma usage.

# The final line may be `sorry` ONLY if the remaining goal is small bookkeeping.
# If a whole proof body is just `sorry`, that is NOT acceptable after decomposition.


# MUTATOR_PROMPT_01_19 = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

# This sketch uses a lemma-first style:
# - There are top-level `lemma ... := by sorry` declarations.
# - The target lemma/theorem body should be *glue code* that chains lemma calls with:
#   `by_cases`, `have`, `rcases/cases`, `exact`.

# A sketch can fail for two reasons:
# 1) the lemma is too difficult → they need further decomposition into helper lemmas.
# 2) the lemma is logically incorrect/unprovable → revise the lemma statements and/or glue structure.

# Your job:
# - Read the current sketch and the feedback carefully.
# - Produce an improved sketch that:
#   - Fixes incorrect subgoals.
#   - Breaks difficult steps into helper lemmas.
#   - Critically: **rewrites the failing lemma/theorem body to USE the new helper lemmas**.

# This is the current proof sketch:
# {sketch}

# Feedback:
# {sketch_rating}
 
# -------------------------
# CRITICAL RULES
# -------------------------
# - Maintain valid Lean syntax and proper indentation.
# - Do NOT change anything in the original theorem statement.
# - Do NOT write a single wrapper lemma that proves the whole theorem and then `exact wrapper`.
# - The lemmas need to be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the provided feedback.
# - If you introduce helper lemmas, you MUST also:
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to *interleave* calls to those lemmas.

# -------------------------
# MANDATORY GLUE STRUCTURE
# -------------------------
# When decomposing a hard lemma L:
# 1) Add helper lemmas (top-level) with `:= by sorry`.
# 2) Replace the body of L with a glue chain that combines results by calling those helper lemmas, not by solving directly,  e.g.

# by
#   have h1 : T1 := by exact helper1 ...
#   rcases h1 with ⟨...⟩   -- when T1 is existential/conjunction
#   have h2 : T2 := by exact helper2 ... -- using earlier bound vars
#   ...
#   -- final assembly    
#   exact ...     

# Do not include `sorry` in the glue chain. 

# -------------------------
# EXAMPLE (FOLLOW THIS STYLE)
# -------------------------
# >>>>SEARCH
# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry
# >>>>REPLACE
# lemma notP_to_Q_lemma (P Q : Prop) (hnotP : ¬ P) : Q := by
#   sorry

# lemma Q_to_R_lemma (Q R : Prop) (hQ : Q) : R := by
#   sorry

# lemma R_to_disj_lemma (P R : Prop) (hR : R) : P ∨ R := by
#   sorry

# lemma P_to_disj_lemma (P R : Prop) (hP : P) : P ∨ R := by
#   sorry

# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by
#   by_cases hP : P
#   · -- Case 1: P
#     have h1 : P ∨ R := by
#       exact P_to_disj_lemma P R hP
#     exact h1
#   · -- Case 2: ¬P
#     have hQ : Q := by
#       exact notP_to_Q_lemma P Q hP
#     have hR : R := by
#       exact Q_to_R_lemma Q R hQ
#     have h2 : P ∨ R := by
#       exact R_to_disj_lemma P R hR
#     exact h2

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# You MUST output one or more edit blocks using the following **exact** structure.

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """

# MUTATE2 = """You will be given a solution consisting of:
# - an informal proof (a lemma-style informal sketch), and
# - a formal proof (a lemma-style Lean sketch).

# You will also be provided with failed lemmas: lemmas that were not proved by the prover.

# Your task is to improve the given solution (both the informal proof and the formal sketch). 


# You have three possible actions:
# 1) The failed lemma is incorrect in Lean.
#    - Modify the formal proof to correct it.
# 2) The failed lemma is mathematically correct but too difficult for the prover.
#    - Decompose it into simpler intermediate steps.
#    - In this case, you MUST edit BOTH the informal and formal proofs:
#      * Add the decomposition plan to the informal proof.
#      * Implement the same plan in the formal proof.
# 3) There exists a better proof plan that avoids the failed lemmas.
#    - Modify BOTH the informal and formal proofs to reflect this new plan.

# This is the current solution:
# {solution}

# {failed_str}

# ---------------------
# Informal Sketch Format
# ---------------------
# - First, declare several lemmas (at least 4) as top-level declarations of the form:
#     `lemma <lemma_name> : <concise mathematical statement>.`
# - Then, at the end, construct the glue: an informal explanation of how these lemmas combine to prove the original statement.
# - Each lemma should represent a single logical step that will be invoked in the glue.
# - Output ONLY the informal proof. No Lean code.
# - Do not create a lemma that has the same goal as the original statement.

# FORMAT
# lemma <lemma_name> : <statement>.
# ...
# theorem <formal_theorem_name> : <glue explanation>

# ---------------------
# Formal Sketch Format
# ---------------------
# - First, declare several lemmas (at least 4) as top-level declarations of the form:
#     `lemma ... := by sorry`
# - Then declare the target theorem as:
#     `theorem ... := by ...`
# - The theorem body MUST be glue code that:
#   * introduces intermediate results using `have`
#   * invokes previously declared lemmas using `exact lemma_name ...`
#   * combines results by sequencing lemma calls, not by solving goals directly
# - All lemmas must be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the informal sketch.
# - Use ALL lemmas introduced in the informal sketch.
# - The Lean sketch must be enclosed in a single ```lean4``` code block.

# -------------------
# DECOMPOSITION RULES
# -------------------
# - Decomposition means breaking a difficult lemma into simpler lemmas.
# - If you introduce helper lemmas, you MUST (for BOTH the informal and formal sketches):
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to interleave calls to the new helper lemmas.
# - Any mathematical change must be mirrored in BOTH the informal and formal proofs.
# - Do not change the format of the informal proof. Keep it lemma-style sketch.

# The object that you are improving contains two blocks : Informal lemma-style proof sketch and formal lemma-style lean sketch. Each have the same lemmas. Make the same modifications on both parts.
# the informal and formal sketch need to contain the same lemmas.

# --------------------------
# Example of a valid output:
# --------------------------
# >>>>SEARCH
# lemma demo_seed_style : prove P ∨ R.
# >>>>REPLACE
# lemma not_p_to_q : if P is false, then Q.

# lemma q_to_r : if Q is true, then R.

# lemma r_to_disjunction : if R is true, then P or R.

# lemma p_to_disjunction : if P is true, then P or R.

# lemma demo_seed_style : prove P ∨ R.
# To prove that P or R holds, split into cases on whether P is true.
# - If P is true, apply lemma p_to_disjunction to conclude P or R.
# - If P is false, use lemma not_p_to_q to obtain Q, then lemma q_to_r to obtain R,
#   and finally lemma r_to_disjunction to conclude P or R.

# >>>>SEARCH
# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry
# >>>>REPLACE
# lemma not_p_to_q (P Q : Prop) (hnotP : ¬ P) : Q := by
#   sorry

# lemma q_to_r (Q R : Prop) (hQ : Q) : R := by
#   sorry

# lemma r_to_disjunction (P R : Prop) (hR : R) : P ∨ R := by
#   sorry

# lemma p_to_disjunction (P R : Prop) (hP : P) : P ∨ R := by
#   sorry

# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by
#   by_cases hP : P
#   · have h1 : P ∨ R := by
#       exact p_to_disjunction P R hP
#     exact h1
#   · have hQ : Q := by
#       exact not_p_to_q P Q hP
#     have hR : R := by
#       exact q_to_r Q R hQ
#     have h2 : P ∨ R := by
#       exact r_to_disjunction P R hR
#     exact h2

# --------------
# OUTPUT FORMAT
# --------------
# You MUST output one or more edit blocks using the following EXACT structure.

# >>>>SEARCH
# [exact substring copied verbatim from the solution that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """
MUTATE2 = """You will be given a solution consisting of TWO LINKED PARTS:

PART A — Informal Proof:
- A lemma-style informal proof sketch written in natural language.

PART B — Formal Proof:
- A lemma-style Lean sketch enclosed in a single ```lean4``` block.

==================================================
CRITICAL INVARIANT (MUST HOLD AT ALL TIMES)
==================================================
- PART A and PART B describe THE SAME proof.
- They contain THE SAME lemmas, with THE SAME names, in THE SAME order.
- Every lemma appearing in PART A MUST appear in PART B.
- Every lemma appearing in PART B MUST appear in PART A.
- Any modification made to one part MUST be mirrored in the other.

You will also be provided with FAILED SUBGOALS: lemmas that were not proved by the prover.

Your task is to improve the solution by editing BOTH parts in a synchronized way.

--------------------------------
ALLOWED TRANSFORMATIONS (ONLY)
--------------------------------
You may perform ONE or MORE of the following actions:

1) INCORRECT LEMMA (Lean-level issue)
   - The lemma statement is incorrect or unprovable in Lean.
   - Fix the FORMAL lemma statement and/or its glue usage.
   - Update the INFORMAL lemma statement if its meaning changes.

2) CORRECT BUT TOO DIFFICULT (REQUIRES DECOMPOSITION)
   - The lemma is mathematically correct but too hard for the prover.
   - You MUST decompose it into simpler helper lemmas.

   DECOMPOSITION MEANS:
   - Replace ONE hard lemma with SEVERAL easier lemmas.
   - Each helper lemma should represent ONE logical step.
   - The original lemma/theorem STATEMENT must remain unchanged.

   REQUIRED STEPS WHEN DECOMPOSING:
   (A) Informal sketch (PART A):
       - Add new helper lemmas with clear informal statements.
       - Update the glue of the original lemma/theorem to EXPLICITLY
         explain how the helper lemmas are chained together.
       - Do NOT remove the original lemma/theorem.

   (B) Formal sketch (PART B):
       - Add corresponding helper lemmas as top-level
         `lemma ... := by sorry`.
       - Rewrite the body of the decomposed lemma/theorem as GLUE CODE
         that *calls the helper lemmas*, instead of solving directly.

3) BETTER PROOF PLAN
   - There exists a simpler plan that avoids the failed lemmas.
   - Replace BOTH PART A and PART B with the new plan.
   - The new plan MUST still be lemma-style in BOTH parts.

--------------------------------
CURRENT SOLUTION (TO BE EDITED)
--------------------------------
{solution}

--------------------------------
FAILED SUBGOALS
--------------------------------
{failed_str}

=====================
PART A — Informal Sketch Format
=====================
- Declare several lemmas (at least 4) as:

    lemma <lemma_name> : <concise mathematical statement>.

- Then declare the theorem with glue explaining how the lemmas combine.
- Each lemma represents ONE logical step.
- The glue MUST reference the lemmas by name.
- Do NOT introduce a lemma with the same goal as the theorem.
- Output ONLY informal proof text (no Lean syntax).

FORMAT:
lemma <lemma_name> : <statement>.
...
theorem <formal_theorem_name> : <glue explanation>

=====================
PART B — Formal Lean Sketch Format
=====================
- Declare the SAME lemmas (same names, same order) as:

    lemma ... := by sorry

- Declare the SAME theorem as:

    theorem ... := by ...

- The theorem/lemma bodies MUST be GLUE CODE that:
  * introduces intermediate facts using `have`
  * destructs structure using `rcases` / `cases` when needed
  * calls lemmas using `exact lemma_name ...`
  * assembles the final result step-by-step

- Do NOT solve goals directly inside glue.
- ALL lemmas must contain `sorry`.
- Use ALL lemmas from PART A.
- The Lean sketch MUST be enclosed in ONE ```lean4``` block.

=========================
DECOMPOSITION (MANDATORY PROCEDURE)
=========================
When a lemma L fails and is too hard:

1) Identify the logical sub-steps needed to prove L.
2) Introduce helper lemmas L₁, L₂, ..., each capturing ONE sub-step.
3) Keep the STATEMENT of L unchanged.
4) Rewrite the BODY of L as glue code of the form:

by
  have h1 : T1 := by exact helper1 ...
  rcases h1 with ⟨...⟩        -- if needed
  have h2 : T2 := by exact helper2 ...
  ...
  exact ...

5) Mirror this decomposition EXACTLY in the informal sketch:
   - The same helper lemmas
   - The same logical order
   - The same proof plan in words

Do NOT leave `sorry` in the glue code.
`sorry` is allowed ONLY in helper lemma bodies.

=========================
FINAL SYNCHRONIZATION CHECK
=========================
Before outputting:
- Verify that PART A and PART B list EXACTLY the same lemmas.
- Verify that lemma names, order, and roles match.
- If this invariant is violated, the output is INVALID.

=========================
OUTPUT FORMAT (STRICT)
=========================
You MUST output one or more edit blocks using EXACTLY this structure:

>>>>SEARCH
[exact substring copied verbatim from the solution]
>>>>REPLACE
[corrected version of that substring, with all `sorry` preserved]

Do NOT output anything else.
"""
# MUTATOR_PROMPT = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

# This sketch uses a lemma-first style:
# - There are top-level `lemma ... := by sorry` declarations.
# - The target lemma/theorem body should be *glue code* that chains lemma calls with: `have`and `exact`.

# A sketch can fail for two reasons:
# 1) the lemma is too difficult → they need further decomposition into helper lemmas.
# 2) the lemma is logically incorrect/unprovable → revise the lemma statements and/or glue structure.

# Your job:
# - Read the current sketch and the feedback carefully.
# - Produce an improved sketch that:
#   - Fixes incorrect subgoals.
#   - Breaks difficult steps into helper lemmas.
#   - Critically: **rewrites the failing lemma/theorem body to USE the new helper lemmas**.

# This is the current proof sketch:
# {sketch}

# Feedback:
# {sketch_rating}

# -------------------------
# CRITICAL RULES
# -------------------------
# - Maintain valid Lean syntax and proper indentation.
# - DO NOT change anything in the original theorem statement.
# - Do NOT write a single wrapper lemma that proves the whole theorem and then `exact wrapper`.
# - The lemmas need to be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the provided feedback.
# - If you introduce helper lemmas, you MUST also:
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to *interleave* calls to those lemmas.
# - For each helper lemma specify types for numeric literals in division or subtraction :  Use `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`, `((2 : ℤ) - 3)`, NOT `2 / 3`.

# -------------------------
# MANDATORY GLUE STRUCTURE
# -------------------------
# When decomposing a hard lemma L:
# 1) Add helper lemmas (top-level) with `:= by sorry`.
# 2) Replace the body of L with a glue chain that combines results by calling those helper lemmas, not by solving directly,  e.g.

# by
#   have h1 : T1 := by exact helper1 ...
#   have h2 : T2 := by exact helper2 ... -- using earlier bound vars
#   ...
#   -- final assembly    
#   exact ...     

# Do not include `sorry` in the glue chain. 

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# You MUST output one or more edit blocks using the following **exact** structure.

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """

MUTATOR_PROMPT = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

This sketch uses a lemma-first style:
- There are top-level `lemma ... := by sorry` declarations.
- The target lemma/theorem body should be *glue code* that chains lemma calls with:
  `by_cases`, `have`, `rcases/cases`, `exact`.

A sketch can fail for two reasons:
1) the lemma is too difficult → they need further decomposition into helper lemmas.
2) the lemma is logically incorrect/unprovable → revise the lemma statements and/or glue structure.

Your job:
- Read the current sketch and the feedback carefully.
- Produce an improved sketch that:
  - Fixes incorrect subgoals.
  - Breaks difficult steps into helper lemmas.
  - Critically: **rewrites the failing lemma/theorem body to USE the new helper lemmas**.

This is the current proof sketch:
{sketch}

Feedback:
{sketch_rating}

-------------------------
CRITICAL RULES
-------------------------
- Maintain valid Lean syntax and proper indentation.
- DO NOT change anything in the original theorem statement.
- Do NOT write a single wrapper lemma that proves the whole theorem and then `exact wrapper`.
- The lemmas need to be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the provided feedback.
- For each helper lemma specify types for numeric literals in division or subtraction :  Use `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`, `((2 : ℤ) - 3)`, NOT `2 / 3`.

-------------------------
MANDATORY GLUE STRUCTURE
-------------------------
When decomposing a hard lemma L:
1) Add helper lemmas (top-level) with `:= by sorry`.
2) Replace the body of L with a glue chain that combines results by calling those helper lemmas, not by solving directly,  e.g.

by
  have h1 : T1 := by exact helper1 ...
  rcases h1 with ⟨...⟩   -- when T1 is existential/conjunction
  have h2 : T2 := by exact helper2 ... -- using earlier bound vars
  ...
  -- final assembly    
  exact ...     

Do not include `sorry` in the glue chain. 

-------------------------
OUTPUT FORMAT (MANDATORY)
-------------------------
You MUST output one or more edit blocks using the following **exact** structure.

>>>>SEARCH
[exact substring copied verbatim from the current sketch that contains the error]
>>>>REPLACE
[corrected version of that substring]
"""
# - If you introduce helper lemmas, you MUST also:
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to *interleave* calls to those lemmas.

# -------------------------
# EXAMPLE (FOLLOW THIS FORMAT)
# -------------------------
# >>>>SEARCH
# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry
# >>>>REPLACE
# lemma notP_to_Q_lemma (P Q : Prop) (hnotP : ¬ P) : Q := by
#   sorry

# lemma Q_to_R_lemma (Q R : Prop) (hQ : Q) : R := by
#   sorry

# lemma R_to_disj_lemma (P R : Prop) (hR : R) : P ∨ R := by
#   sorry

# lemma P_to_disj_lemma (P R : Prop) (hP : P) : P ∨ R := by
#   sorry

# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by
#   by_cases hP : P
#   · -- Case 1: P
#     have h1 : P ∨ R := by
#       exact P_to_disj_lemma P R hP
#     exact h1
#   · -- Case 2: ¬P
#     have hQ : Q := by
#       exact notP_to_Q_lemma P Q hP
#     have hR : R := by
#       exact Q_to_R_lemma Q R hQ
#     have h2 : P ∨ R := by
#       exact R_to_disj_lemma P R hR
#     exact h2

# - Use ALL lemmas introduced in the feedback plan.
#

# - For each lemma in the feedback plan, generate a Lean lemma with the SAME name.


# - Always type numeric literals in division/subtraction when needed: `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`, `((2 : ℤ) - 3)`

# Arithmetic & Type Safety (CRITICAL):
# * ALWAYS cast to an appropriate type (`ℤ`, `ℚ`, or `ℝ`) before arithmetic when needed.
# * ALWAYS specify types for numeric literals in division or subtraction:
#   * Use `((2 : ℝ) / 3)` or `((2 : ℚ) / 3)`, NOT `2 / 3`.

# MUTATOR_PROMPT = """Your task is to iteratively improve the given Lean sketch using the provided feedback.

# This sketch uses a lemma-first style:
# - There are top-level `lemma ... := by sorry` declarations.
# - The target lemma/theorem body should be *glue code* that chains lemma calls with:
#   `by_cases`, `have`, `rcases/cases`, `exact`.

# Your job:
# - Read the current sketch and the feedback carefully.
# - Produce an improved sketch that:
#   - Breaks difficult steps into helper lemmas.
#   - Critically: **rewrites the failing lemma/theorem body to USE the new helper lemmas**.

# This is the current proof sketch:
# {sketch}

# Feedback:
# {sketch_rating}

# -------------------------
# CRITICAL RULES
# -------------------------
# - Maintain valid Lean syntax and proper indentation.
# - DO NOT change anything in the original theorem statement.
# - Do NOT write a single wrapper lemma that proves the whole theorem and then `exact wrapper`.
# - The lemmas need to be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the provided feedback.
# - If you introduce helper lemmas, you MUST also:
#   (A) keep the original lemma/theorem statement unchanged, AND
#   (B) update its proof body to *interleave* calls to those lemmas.

# -------------------------
# MANDATORY GLUE STRUCTURE
# -------------------------
# When decomposing a hard lemma L:
# 1) Add helper lemmas (top-level) with `:= by sorry`.
# 2) Replace the body of L with a glue chain that combines results by calling those helper lemmas, not by solving directly,  e.g.

# by
#   have h1 : T1 := by exact helper1 ...
#   rcases h1 with ⟨...⟩   -- when T1 is existential/conjunction
#   have h2 : T2 := by exact helper2 ... -- using earlier bound vars
#   ...
#   -- final assembly    
#   exact ...     

# Do not include `sorry` in the glue chain. 

# -------------------------
# EXAMPLE (FOLLOW THIS FORMAT)
# -------------------------
# >>>>SEARCH
# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by sorry
# >>>>REPLACE
# lemma notP_to_Q_lemma (P Q : Prop) (hnotP : ¬ P) : Q := by
#   sorry

# lemma Q_to_R_lemma (Q R : Prop) (hQ : Q) : R := by
#   sorry

# lemma R_to_disj_lemma (P R : Prop) (hR : R) : P ∨ R := by
#   sorry

# lemma P_to_disj_lemma (P R : Prop) (hP : P) : P ∨ R := by
#   sorry

# lemma demo_seed_style (P Q R : Prop) : P ∨ R := by
#   by_cases hP : P
#   · -- Case 1: P
#     have h1 : P ∨ R := by
#       exact P_to_disj_lemma P R hP
#     exact h1
#   · -- Case 2: ¬P
#     have hQ : Q := by
#       exact notP_to_Q_lemma P Q hP
#     have hR : R := by
#       exact Q_to_R_lemma Q R hQ
#     have h2 : P ∨ R := by
#       exact R_to_disj_lemma P R hR
#     exact h2

# -------------------------
# OUTPUT FORMAT (MANDATORY)
# -------------------------
# You MUST output one or more edit blocks using the following **exact** structure.

# >>>>SEARCH
# [exact substring copied verbatim from the current sketch that contains the error]
# >>>>REPLACE
# [corrected version of that substring, with all `sorry` preserved]
# """

