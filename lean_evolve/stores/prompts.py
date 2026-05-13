# prompts.py

informal_proof_prompt_template= """
You are a mathematical expert whose goal is to solve problems with rigorous mathematical reasoning.

Instructions:
1. Provide a natural language, step-by-step proof for the given problem.
2. Start from the given premises and reason step-by-step to reach the conclusion.
3. Number each step of the proof as 1, 2, and so on.
4. Be as pedantic and thorough as possible.
5. Keep each step precise, increase the number of steps if needed.
6. Do NOT gloss over any step. Make sure to be as thorough as possible.
7. Show the explicit calculations/simplifications, theorem applications and case
analysis.

Informal theorem:
{informal}

Formal theorem (Lean):
{formal}
"""
informal_proof_prompt_templatedd = """You will be given an informal and a formal mathematical statement. Your task is to write an informal proof of the theorem by decomposing it into simpler steps.

The informal proof MUST:
- Be written as a numbered sequence of lemmas.

Informal theorem:
{informal}

Formal theorem (Lean):
{formal}
"""
# (at least 4) 
informal_proof_prompt_template_gla = """You are an expert mathematician. Your task is to write a lemma-style informal sketch.

TASK
Given:
(1) an informal theorem written in natural language, and
(2) a Lean theorem statement `formal_theorem`,
write a lemma-style informal sketch.

INPUTS
Informal theorem:
{informal}

Formal theorem (Lean):
{formal}

OUTPUT FORMAT (MUST MATCH)
- First, declare several lemmas as top-level declarations of the form:
    `lemma <lemma_name> : <concise mathematical statement>.`
- Then, at the end, construct the glue: an informal explanation of how these lemmas combine to prove the original statement.
- Each lemma should represent a single logical step that will be invoked in the glue.
- Output ONLY the informal proof. No Lean code.
- Do not create a lemma that has the same goal as the original statement.

FORMAT
lemma <lemma_name> : <statement>.
...
theorem <formal_theorem_name> : <glue explanation>

example :

-- Informal theorem:
--   Prove P ∨ R.
-- Formal theorem:
--   theorem demo_seed_style (P Q R : Prop) : P ∨ R := by sorry.

lemma not_p_to_q : if P is false, then Q.

lemma q_to_r : if Q is true, then R.

lemma r_to_disjunction : if R is true, then P or R.

lemma p_to_disjunction : if P is true, then P or R.

theorem demo_seed_style : prove P ∨ R.
To prove that P or R holds, split into cases on whether P is true.
- If P is true, apply lemma p_to_disjunction to conclude P or R.
- If P is false, use lemma not_p_to_q to obtain Q, then lemma q_to_r to obtain R,
  and finally lemma r_to_disjunction to conclude P or R.

Now output the lemma-style informal sketch."""

# IMPORTANT : 
# This sketch will be translated into Lean, so avoid using subtraction or division on natural numbers unless it is clearly justified or required by the theorem. In particular, only use expressions like x - y when assumptions such as x ≥ y are explicitly stated.

system_prompt_sketch = """You are an expert Lean 4 theorem-prover. You produce lemma-style Lean sketches."""
system_prompt_informal_proof = """You are an expert mathematician. You rewrite the theorem into a clear informal proof."""
sketch_prompt_template_gla = """You are a Lean theorem-proving assistant. Produce a lemma-style Lean sketch.

TASK
Given:
(1) a lemma-style informal sketch written in natural language, and
(2) a Lean theorem statement `formal_theorem`,
translate the informal sketch into a lemma-style Lean sketch.

INPUTS
[Informal proof]
{informal_proof}

[Lean theorem statement]
{formal}

OUTPUT FORMAT (MUST MATCH)
- First, declare several lemmas as top-level declarations of the form:
    `lemma ... := by sorry`
- Then declare the target theorem as:
    `theorem ... := by ...`
- The theorem body MUST be glue code that:
  * introduces intermediate results using `have`
  * invokes previously declared lemmas using `exact lemma_name ...`
  * combines results by sequencing lemma calls, not by solving goals directly
  * Does not contain  `sorry`.
- All lemmas must be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the informal sketch.
- The Lean sketch must be enclosed in a single ```lean4``` code block.
- For each helper new lemma specify types for numeric literals in division or subtraction :  Use `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`, `((2 : ℤ) - 3)`, NOT `2 / 3`.
- DO NOT change anything in the original theorem statement.

STYLE CONSTRAINTS
1) Lemmas:
   - For each lemma in the informal sketch, generate a Lean lemma with the SAME name.
2) Theorem:
   - Prefer structured control flow: `by_cases`, `have`, `rcases`, `exact`.
   - The glue code should closely follow the glue in the informal sketch, primarily sequencing lemma applications, e.g.:
       have h1 : ... := by exact lemma1 ...
       rcases h1 with ⟨..., ..., ...⟩
       have h2 : ... := by exact lemma2 ...
       ...
       exact lemma_last ...
3) Output ONLY Lean code. No English explanations.

example :

-- Informal proof idea:
lemma not_p_to_q : if P is false, then Q.

lemma q_to_r : if Q is true, then R.

lemma r_to_disjunction : if R is true, then P or R.

lemma p_to_disjunction : if P is true, then P or R.

theorem demo_seed_style : prove P ∨ R.
To prove that P or R holds, split into cases on whether P is true.
- If P is true, apply lemma p_to_disjunction to conclude P or R.
- If P is false, use lemma not_p_to_q to get Q, then lemma q_to_r to get R,
  then lemma r_to_disjunction to conclude P or R.

----
```lean4
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

lemma not_p_to_q (P Q : Prop) (hnotP : ¬ P) : Q := by
  sorry

lemma q_to_r (Q R : Prop) (hQ : Q) : R := by
  sorry

lemma r_to_disjunction (P R : Prop) (hR : R) : P ∨ R := by
  sorry

lemma p_to_disjunction (P R : Prop) (hP : P) : P ∨ R := by
  sorry

theorem demo_seed_style (P Q R : Prop) : P ∨ R := by
  by_cases hP : P
  · have h1 : P ∨ R := by
      exact p_to_disjunction P R hP
    exact h1
  · have hQ : Q := by
      exact not_p_to_q P Q hP
    have hR : R := by
      exact q_to_r Q R hQ
    have h2 : P ∨ R := by
      exact r_to_disjunction P R hR
    exact h2
```

Now output the lemma-style Lean sketch."""
# - Use ALL lemmas introduced in the informal sketch.

sketch_prompt_template = """You are a Lean theorem-proving assistant. Produce a lemma-style Lean sketch. 

TASK
Given:
(1) an informal proof in natural language, and
(2) a Lean theorem statement `formal_theorem`,
write a lemma-style Lean sketch. 


INPUTS
[Informal proof]
{informal_proof}

[Lean theorem statement]
{formal}

OUTPUT FORMAT (MUST MATCH)
- First, declare several lemmas (at least 4) as top-level `lemma ... := by sorry`.
- Then declare the target theorem as `theorem ... := by ...`.
- The theorem body MUST be “glue code” that:
  * creates intermediate facts with `have h1 : ... := by exact lemma_name ...`
  * destructs existentials with `rcases` / `cases` into named components
  * combines results by calling lemmas, not by solving directly
- Do NOT write a single wrapper lemma that proves the whole theorem and then `exact wrapper`.
- The lemmas need to be unproved (contain `sorry`), but their statements must be meaningful and correspond to steps in the informal proof.
- Always cast numeric literals to an explicit type (`ℤ`, `ℚ`, or `ℝ`) before arithmetic when required.
- Always type numeric literals in division/subtraction when needed:
  - Correct: `((2 : ℝ) / 3)`, `((2 : ℚ) / 3)`
  - Incorrect: `2 / 3`

STYLE CONSTRAINTS (IMPORTANT)
1) Lemmas:
   - Use top-level lemma declarations, not only local `have`.
   - Each lemma should be a “step” that will be invoked from the theorem.
2) Theorem:
   - Prefer structured control flow: `by_cases`, `have`, `rcases`, `exact`.
   - The theorem should mainly sequence lemma calls like:
       have h1 : ... := by exact lemma1 ...
       rcases h1 with ⟨..., ..., ...⟩
       have h2 : ... := by exact lemma2 ...
       ...
       exact lemma_last ...
3) Output ONLY Lean code. No English explanations.

example :

import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

-- Informal proof idea:
-- To prove P ∨ R:
-- If P holds, we're done.
-- Otherwise ¬P, use lemma1 to get Q, then lemma2 turns Q into R, so conclude P ∨ R.

lemma notP_to_Q_lemma (P Q : Prop) (hnotP : ¬ P) : Q := by
  sorry

lemma Q_to_R_lemma (Q R : Prop) (hQ : Q) : R := by
  sorry

lemma R_to_disj_lemma (P R : Prop) (hR : R) : P ∨ R := by
  sorry

lemma P_to_disj_lemma (P R : Prop) (hP : P) : P ∨ R := by
  sorry

theorem demo_seed_style (P Q R : Prop) : P ∨ R := by
  by_cases hP : P
  · -- Case 1: P
    have h1 : P ∨ R := by
      exact P_to_disj_lemma P R hP
    exact h1
  · -- Case 2: ¬P
    have hQ : Q := by
      exact notP_to_Q_lemma P Q hP
    have hR : R := by
      exact Q_to_R_lemma Q R hQ
    have h2 : P ∨ R := by
      exact R_to_disj_lemma P R hR
    exact h2


Now output the lemma-style Lean sketch."""

sketch_prompt_template_2026 = """You are a Lean 4 expert who is trying to help write a proof in Lean 4.

Problem Statement: 
{formal}

Informal Proof:
{informal_proof}

Instructions:

Use the informal proof to write a proof sketch for the problem in Lean 4 following these guidelines:
- Break complex reasoning into logical sub-goals using `have` statements.
- The subgoals should build up to prove the main theorem.
- Make sure to include all the steps and calculations from the given proof in the proof sketch.
- Each subgoal should ideally require applying just one key theorem or lemma, or a few tactic applications.
- Base subgoals around:
  - Useful theorems mentioned in the problem context
  - Standard library theorems (like arithmetic properties, set operations, etc.)
  - The supplied premises in the theorem statement
- Do NOT create subgoals identical to any of the given hypotheses
- Do NOT create subgoals that are more complex than the original problems. The subgoals should be SIMPLER than the given problem.
- Do NOT skip over any steps. Do NOT make any mathematical leaps.

**Subgoal Structure Requirements:**
- **Simplicity**: Each subgoal proof should be achievable with 1-3 basic tactics
- **Atomic reasoning**: Avoid combining multiple logical steps in one subgoal
- **Clear progression**: Show logical flow: `premises → intermediate steps → final result`
- **Theorem-focused**: Design each subgoal to directly apply a specific theorem when possible

NOTE: Only add sub-goals that simplify the proof of the main goal.

When writing Lean proofs, maintain consistent indentation levels.

Rules:
1. Same proof level = same indentation: All tactics at the same logical level must use identical indentation
2. Consistent characters: Use either tabs OR spaces consistently (don't mix)
3. Proper nesting: Indent sub-proofs one level deeper than their parent
4. Do NOT nest `have` statements in each other. Use distinct sub-goals as much as possible. Ensure all sub goals are named. Do NOT create anonymous have statements.
5. Do NOT include any imports or open statements in your code.
6. One line = One `have` subgoal. Do NOT split subgoals across different lines.
7. Use proper Lean 4 syntax and conventions. Ensure the proof sketch is enclosed in triple backticks ```lean```
8. Use `sorry` for all subgoal proofs - focus on structure, not implementation
9. **Do NOT use `sorry` for the main goal proof** - use your subgoals to prove it
10. NEVER use `sorry` IN the theorem statement itself
11. Ensure subgoals collectively provide everything needed for the main proof
12. Make the logical dependencies between subgoals explicit. Ensure that the subgoals are valid and provable in Lean 4.
13. Do NOT change anything in the original theorem statement.


IMPORTANT INSTRUCTION: Do NOT, under ANY circumstances, allow division and subtraction operations on natural number literals with UNDEFINED types, unless REQUIRED by the theorem statement. For example, do NOT allow literals like `1 / 3` or `2 / 5` or `1 - 3` ANYWHERE in ANY of the subgoals. ALWAYS specify the types. AVOID natural number arithmetic UNLESS NEEDED by the theorem statement.
ALWAYS specify types when describing fractions. For example, ((2 : ℝ) / 3) or ((2 : ℚ) / 3) instead of (2 / 3). Do this everywhere EXCEPT the given theorem statement.
IMPORTANT INSTRUCTION: Do NOT, under ANY circumstances, allow division and subtraction operations on variables of type natural numbers (Nat or ℕ), unless REQUIRED by the theorem statement. For example, do NOT allow expressions like (a-b) or (a/b) where a, b are of type ℕ. ALWAYS cast the variables to a suitable type (ℤ, ℚ or ℝ) when performing arithmetic operations. AVOID natural number arithmetic UNLESS NEEDED by the theorem statement.
"""


sketch_prompt_template_new = """Your task is to produce a proof sketch that follows the structure of the informal proof and makes each reasoning step explicit.

Instructions:
- Translate the informal proof into a sequence of **explicit, meaningful, atomic subgoals** that collectively prove the theorem.
- Use `have` statements to represent each atomic subgoal.
- Include every step and calculation from the informal proof (as one or more `have` subgoals).

**Subgoal Structure Requirements:**
- **Simplicity**: Each subgoal proof should be achievable with 1-3 basic tactics
- **Atomic reasoning**: Avoid combining multiple logical steps in one subgoal
- **Clear progression**: Show logical flow: `premises → intermediate steps → final result`

Rules:
1. Same proof level = same indentation: All tactics at the same logical level must use identical indentation
2. Do NOT include any imports or open statements in your code.
3. Use proper Lean 4 syntax and conventions. Ensure the proof sketch is enclosed in triple backticks ```lean```
4. Use `sorry` for all subgoal proofs - focus on structure, not implementation
5. **Do NOT use `sorry` for the main goal proof** - use your subgoals to prove it
6. Ensure subgoals collectively provide everything needed for the main proof
7. Make the logical dependencies between subgoals explicit. Ensure that the subgoals are valid and provable in Lean 4.
8. Do NOT create subgoals identical to any of the given hypotheses
9. Do NOT change anything in the original theorem statement.

Arithmetic & Type Safety (CRITICAL):
* ALWAYS cast to an appropriate type (`ℤ`, `ℚ`, or `ℝ`) before arithmetic when needed.
* ALWAYS specify types for numeric literals in division or subtraction:
  * Use `((2 : ℝ) / 3)` or `((2 : ℚ) / 3)`, NOT `2 / 3`.

Problem Statement: 
{formal}

Informal Proof:
{informal_proof}
"""


system_prompt_assemble = "You are a Lean 4 expert. Your goal is to write a proof in Lean 4, according to the given proof sketch, using the supplied theorems."

USE_SKETCH_AND_THEOREMS_TO_PROVE = """
You are a Lean 4 expert. Write a Lean 4 proof following the given proof sketch and using ONLY the supplied theorems.

Proof sketch:
{sketch}

Theorems:
{theorems_string}

Requirements:
1. Assume all supplied theorems are correct; use them directly.
2. Do NOT modify or re-prove the given theorems.
3. Do NOT alter the proof sketch steps; just replace each `sorry` with applications of the given theorems.
4. Do NOT use `sorry` anywhere.
5. Do NOT add imports, definitions, or open statements.
6. Do NOT write new proofs from scratch—ALWAYS use the supplied theorems.
7. Output ONLY one Lean 4 code block containing the completed proof.
***8. Do NOT change anything in the original theorem statement.***

Return a single Lean 4 code block with the final proof.
"""


USE_SKETCH_AND_THEOREMS_TO_PROVE_REPAIR = """
You are a Lean 4 expert. Produce a Lean 4 proof that follows the given proof sketch and uses ONLY the supplied theorems.

Proof sketch:
{sketch}

Theorems:
{theorems_string}

Your previous attempt failed:
{attempt}

Here are the errors:
{errors}

Rules:
1. Assume all provided theorems are correct; use them directly.
2. Do NOT modify or re-prove the theorems.
3. Do NOT change the proof sketch—only replace each `sorry` using the given theorems.
4. No `sorry` allowed anywhere.
5. Do NOT add imports, definitions, or open statements.
6. Do NOT create new proofs; ALWAYS use the supplied theorems.
7. Natural-number subtraction/division literals must have explicit types.  
   Forbidden: `1 / 3`, `1 - 3`.  
   Allowed: `((1 : ℝ) / 3)`, `((1 : ℚ) / 3)`.
8. Do NOT use subtraction or division on variables of type `Nat` or `ℕ` unless required by a theorem.
9. The sketch’s goal types must match the theorem goal types exactly—adjust the sketch (not the theorems) if necessary.
10. Output exactly ONE Lean 4 code block with the corrected, complete proof.
11. Do NOT change anything in the original theorem statement.

Return only the Lean 4 code block.
"""
META_STEP1_SYSTEM_MSG = (
    "You are an expert Lean theorem proving assistant analyzing an individual proof sketch. "
    "Create a standalone summary focusing on implementation details and "
    "evaluation feedback. Consider how this specific sketch performs and "
    "what proof construction choices were made."
)

META_STEP1_USER_MSG = (
    "# Proof Sketch to Analyze\n"
    "{sketch}\n{failed_subgoals}\n\n"
    "# Instructions\n\n"
    "Create a standalone summary for this proof sketch using the following "
    "exact format:\n\n"
    "**Sketch Name: [Short summary name of the proof approach "
    "(up to 10 words)]**\n"
    "- **Implementation**: [Key proof construction details (1-2 sentences)]\n"
    "- **Performance**: [Success/failure metrics or goal completion summary (1 sentence)]\n"
    "- **Feedback**: [Key insights from evaluation or failed subgoals (1-2 sentences)]\n\n"
    "Focus on:\n"
    "1. What specific proof construction details were used\n"
    "2. How these details affected goal completion\n"
    "3. Proof details that are relevant to the approach\n"
    "4. Any evaluation feedback that provides insights\n\n"
    "Keep the sketch summary concise but informative. "
    "Follow the format exactly."
)

META_STEP2_SYSTEM_MSG = (
    "You are an expert Lean theorem proving assistant analyzing specific proof "
    "evaluation results to extract actionable optimization insights. Focus "
    "on concrete performance data and proof construction details from the actual "
    "sketches that were evaluated."
)

META_STEP2_USER_MSG = (
    "# Individual Sketch Summaries\n"
    "{program_summaries}\n\n"
    "# Previous Global Insights (if any)\n"
    "{previous_insights}\n\n"
    "# Current Best Sketch\n"
    "{best_program_info}\n\n"
    "# Instructions\n\n"
    "Analyze the SPECIFIC proof sketch evaluation results above to extract "
    "concrete optimization insights. Look at the actual performance signals, "
    "proof construction details, and evaluation feedback to identify patterns. "
    "Reference specific sketches and their results.\n"
    "Make sure to incorporate the previous insights into the new insights.\n\n"
    "**CRITICAL: Pay special attention to the current best sketch and how it "
    "compares to other evaluated sketches. Ensure the best sketch's successful "
    "patterns are prominently featured in your analysis.**\n\n"
    "Update or create insights in these sections:\n\n"
    "## Successful Proof Patterns\n"
    "- Identify specific proof construction changes that led to improved "
    "goal completion or fewer failures\n"
    "- Reference which sketches achieved these improvements and their "
    "evaluation outcomes\n"
    "- **Highlight patterns from the current best sketch**\n"
    "- Note the specific techniques or approaches that worked "
    "(2-4 bullet points)\n\n"
    "## Ineffective Approaches\n"
    "- Identify specific proof construction choices that worsened "
    "performance\n"
    "- Reference which sketches had these issues and how evaluation "
    "results were affected\n"
    "- Note why these approaches failed based on evaluation feedback "
    "(2-4 bullet points)\n\n"
    "## Implementation Insights\n"
    "- Extract specific proof construction patterns/techniques from the evaluated "
    "sketches\n"
    "- **Analyze what makes the current best sketch effective**\n"
    "- Connect proof details to their impact on goal completion or failure\n"
    "- Reference concrete examples from the sketch summaries "
    "(2-4 bullet points)\n\n"
    "## Performance Analysis\n"
    "- Analyze actual changes and trends in proof success or failure across "
    "evaluated sketches\n"
    "- **Compare other sketches' performance against the current best**\n"
    "- Compare performance between different proof construction approaches\n"
    "- Identify outcome patterns and correlations (2-4 bullet points)\n\n"
    "CRITICAL: Base insights on the ACTUAL individual sketch summaries, "
    "previous insights, and the current best sketch information. "
    "Reference specific sketch names, evaluation outcomes, and proof construction details. "
    "Build upon previous insights with concrete evidence from the new evaluations. "
    "IMPORTANT: Make sure that the best results are not ignored and are "
    "prominently featured in your analysis."
    "Do not make recommendations for the next steps. ONLY PERFORM THE "
    "ANALYSIS."
)

# Step 3: Recommendations Generation
META_STEP3_SYSTEM_MSG = (
    "You are an expert Lean theorem proving assistant generating actionable "
    "recommendations for future proof sketch mutations based on successful "
    "patterns and insights."
)

META_STEP3_USER_MSG = (
    "# Global Insights\n"
    "{global_insights}\n\n"
    "# Previous Recommendations (if any)\n"
    "{previous_recommendations}\n\n"
    "# Current Best Sketch\n"
    "{best_program_info}\n\n"
    "# Instructions\n\n"
    "Based on the global insights above and the current best sketch, generate {max_recommendations} "
    "actionable recommendations for future proof sketch mutations. Each "
    "recommendation should be:\n\n"
    "1. **Specific**: Clear about what proof construction change to implement or try\n"
    "2. **Actionable**: Something that can be directly applied to a sketch\n"
    "3. **Evidence-based**: Grounded in the successful proof patterns identified\n"
    "4. **Diverse**: Cover different types of proof optimizations\n"
    "5. **Best-sketch informed**: Consider what makes the current best sketch successful\n\n"
    "Format as a numbered list:\n\n"
    "1. [Specific recommendation based on successful proof patterns]\n"
    "2. [Another recommendation focusing on a different aspect]\n"
    "...\n\n"
    "**CRITICAL: Prioritize recommendations that build upon or extend the successful "
    "patterns from the current best sketch. Consider both incremental improvements "
    "to the best sketch's approach and novel variations that could surpass it.**\n\n"
    "Focus on the most promising proof construction approaches that have shown success in "
    "recent evaluations, especially those demonstrated by the best sketch. "
    "Avoid generic advice - provide 2-3 sentences per recommendation. "
    "DO NOT RECOMMEND CHANGING THE EVALUATION CODE. ONLY "
    "MAKE PROOF-LEVEL OR ALGORITHMIC RECOMMENDATIONS."
)
