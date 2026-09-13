# A7 grader format recovery — owner decision, 2026-09-13

Codex asked whether exact quoted `"true"`, `"false"` and `"null"` in grader
verdict fields could be recovered while preserving/counting original format
failures, changing no judgments or passing thresholds, and avoiding repeated
completed calls. The owner answered: **"do whatever is best"**. Codex selects
that narrow deterministic recovery. This record owns only this format rule;
all existing product meaning, independent-grader, scoring and roadmap rules
remain unchanged.

Scope: G2's declared `verdicts` fields only. A JSON string exactly equal to the
JSON spelling of a boolean or null may be decoded to that value. Every other
type, string, structure, question identity, required field, duplicate-key,
transport, evidence, refusal and binding check remains the original owner's
responsibility. No case folding, trimming, numeric/truthiness conversion,
answer choice, field filling or meaning inference. `false` stays false;
`null` and reviewer disagreement stay unresolved.

Preserve raw/native bytes, original frozen owners, original validity and every
original invalid/retry count. A recovered reading is separately identified,
not relabelled as an originally schema-valid reply. Record each changed field,
its source reply hash and the original error. Both independent judgments are
still required. Recovery of a complete reading requires the original schema
validator to accept the entire mechanically converted reply; a second defect
prevents recovery. Never repeat a reading after its recovery is verified.

Before use for real scoring, independently validate original collection
evidence, pin this rule and its implementation externally, prove the recovery
through the existing whole-run completion and actual grading consumer, and
run focused, affected and meaningful negative/mutation checks. Saved scores
must identify the recovery version and all affected readings. No original
collection file or completion is overwritten. Original collection failures
remain in their reliability accounting, and no passing threshold is waived.

The already published but uncalled G2 segment5 is not cancelled, deleted,
fabricated or replaced by this rule. Its disposition needs a specific Codex
collection instruction after the recovery and original lifecycle are checked.
G1, G3, the 382 tested answers, source key, production and later gates are not
changed by this rule. A later grader-prompt correction is separate, explicitly
versioned work; the current frozen prompts remain unchanged.
