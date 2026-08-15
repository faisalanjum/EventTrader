# Prompt Generation Standard

> This file governs how prompts are built. It does not define Driver meaning. The live FinalDesign documents and the task's frozen owner decisions always win.

## Goal

Create the **shortest prompt that lets the qualified model complete one bounded task correctly on unseen inputs**.

Remove avoidable ambiguity. Do not hide genuine uncertainty: require the
contract's safe refusal, abstention, or parked result. Target zero observed
wrong accepted results and maximize measured recall without special cases or
extra machinery.

Use only a model qualified for the exact role and settings. Current Steps 1–13
use Sonnet 5 at high effort. Do not enlarge a prompt to compensate for a
weaker model. Cheaper-model qualification is a separate final step.

Rules 1–7 apply to every prompt. Rule 8 applies only to a real multi-step agent
task. Rules 9–11 apply only to prompts used to create, decide, or grade
production or experiment results; do not build proof machinery or manifests
for ordinary one-off instructions.

## Rules

1. **Give each prompt one task and every rule one owner.**

   * State the one required result.
   * Include only the active rules needed for that result.
   * Remove history, rationale, retired rules, repetition, and unavailable document labels.
   * Never add or change product meaning inside a prompt.

2. **Use the fewest words that preserve every requirement.**

   * Remove filler and vague language.
   * State every behavior-changing instruction explicitly.
   * Do not repeat an instruction in different words.
   * Do not add a workflow when one direct instruction is enough.

3. **Separate trusted instructions from untrusted input.**

   * Identify the controlling instructions and every input supplied only as evidence or data.
   * State that instructions found inside untrusted source text, tables, filings, or tool results must be ignored.
   * Bound each untrusted input clearly so its contents cannot alter the task or output format.

4. **Keep the model and code in their assigned roles.**

   * Ask the model only for meaning judgments assigned to it by the live design.
   * Leave source reconstruction, exact occurrence checks, normalization, arithmetic, identifiers, structural validation, accounting, and writes to their existing code owners.
   * Never ask the model to invent missing evidence or redo deterministic work already owned by code.

5. **Define inputs, evidence, and output exactly.**

   * Name every required input and any relevant time cutoff.
   * Require evidence to be copied or referenced exactly as the governing contract says.
   * When a structured owner contract exists, derive field names, allowed values, and output shape mechanically from it.
   * For structured output, allow no extra prose; missing, extra, or malformed fields are invalid.

6. **Generalize; never encode examples as law.**

   * No behavior-changing fixed string, number, range, regular expression, word list, pattern, or exception unless it comes from an official standard, a frozen owner contract, or is mechanically derived from either.
   * Use fixed `if → then` branches only for deterministic conditions owned by that authority.
   * Do not turn a meaning judgment into keyword matching or another rule engine.
   * Use an example only when it is necessary to explain a boundary; keep it non-exhaustive and authority-grounded.

7. **Define uncertainty and stopping behavior.**

   * Name the lawful result when evidence is absent, conflicting, or insufficient.
   * Preserve every lawful input; never reject merely because it differs from an example.
   * Never allow guessing, silent substitution, or an unapproved fallback.
   * Never hide retries, voting, provider fallback, or model replacement inside the prompt; when authorized, the caller or runtime owns it.
   * Do not weaken or rewrite semantic instructions for a particular model.

8. **Use a workflow only for a real multi-step task.**

   * Put prerequisites before dependent actions.
   * State each step's input, output, check, and stopping condition.
   * Do not let an agent silently change the order or widen the task.

9. **For evaluation prompts, protect independence.**

   * Never reveal hidden answers, future information, realized outcomes, another candidate's answer, or a grader's conclusion.
   * A model under test must not create or approve its own answer key.
   * Keep development examples separate from the final unseen test.

10. **For production or experiment prompts, test the fully assembled prompt.**

    * For a behavior change, first add a case that exposes the failure, then make the smallest prompt change.
    * Test the exact rendered prompt, not only its template or fragments.
    * Where relevant, include a lawful control, a near miss, missing evidence, malformed output, repeated evidence, reordered input, and an instruction hidden inside source data.
    * Use fresh unseen cases for final qualification; do not tune on them.
    * For prompts that select or accept facts, count accepted, refused, abstained, parked, wrong, and missed results. Require zero observed wrong accepted results and report every recall loss.
    * Reuse existing proof tools. Add no new proof framework unless existing tests cannot prove the requirement.

11. **Freeze every production or experiment prompt used as evidence.**

    * Record the exact assembled prompt hash, input-set hash, model identifier, model settings, and output identity in the run manifest.
    * Treat any behavior-changing prompt edit as a new version and rerun the affected proof.
    * Do not silently change a frozen prompt during a run.

## Final Quality Gate

Before accepting a prompt, verify:

* **Authoritative:** Every behavior-changing rule has one live owner.
* **Minimal:** Nothing can be removed without losing required behavior or safety.
* **Bounded:** It asks for one named result and cannot widen itself.
* **Clear:** Inputs, evidence, output, uncertainty, and stopping behavior need no guesswork.
* **General:** It contains no invented special case or disguised rule engine.
* **Safe:** Uncertain evidence cannot become an accepted fact.
* **Independent:** The model receives no hidden answer or future information.
* **Proven:** When required by Rules 9–11, the exact assembled prompt passed the focused and unseen checks.
* **Frozen:** When used as evidence, the reviewed prompt and run identities are recorded exactly.

If avoidable ambiguity remains, shorten or clarify the prompt. If the evidence itself is ambiguous, preserve that uncertainty and return the contract's safe outcome.
