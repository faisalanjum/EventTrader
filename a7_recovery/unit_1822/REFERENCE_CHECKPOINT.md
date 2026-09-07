# Reference-card correction — verified checkpoint

**Scope of the verdict.** Codex independently VERIFIED the fourteen reference-card
DATA corrections (SEQ 1822). That is all this checkpoint claims. It is **not** G1
semantic qualification, **not** an A7 PASS, and **not** proof that the full runtime
is ready. A3–A6 stay closed.

## What is corrected

Fourteen reference cards named a *sibling's* claim from the same source span.
Disposition over the whole population: **192 KEEP + 14 CHANGE + 0 UNRESOLVED = 206**.
Each replacement span is a verbatim substring of the card's own bound quote; across
all fourteen only `reference_name` (and `name_from_override`) moved — quote and
values are unchanged, and the other 192 rows are byte-equivalent.

## The pair that must travel together

| role | identity |
| --- | --- |
| corrected owner | `65f8e34128041d82e28ae92992e542675f2d2acfd9e2b67dc73b8c3b54cf5a63` |
| its candidate inventory | `9bb503da40b3112571e889075be03ecdcc3f694cdd3d252cce06c4cbb021f47a` |
| original owner (immutable) | `31c2ef67abf5a2b89bd820d0aa27a1a603ef8e3c0fd6414ae129bb71ad3ddae5` |
| original inventory (immutable) | `ae81caf4936c43432fe27d5ac686dfa090539c615620ce029eaeb00b2f900106` |

Owner and document are **one pair**. Serving the corrected owner the old document
makes the validation owner refuse it (`override_rows: expected 36, document has 22`)
and two further tests fail. That refusal is correct behaviour, not a defect.

## Proof reused, not repeated

- All 206 source-claim decisions and the 15 controlled mutations were independently
  reviewed and are **reused**; they are not re-run here.
- Real owner execution went RED on exactly the 14 rows, then GREEN (16/0) after the
  spans were added, with the owner asserted by file, digest and code-object.
- Paired regression (`test_a7_runstates_1470.py`): **both** the original pair and the
  corrected pair give **30 passed and the same single failure**,
  `test_a_mutation_after_identity_capture_refuses_before_any_answer`. The underlying
  `ValueError` correctly refuses changed run bytes; only its **wording** differs from
  the substring that test requires. Production behaviour must **not** be changed to
  satisfy that wording. It stays a named test limitation for the final affected
  regression.

## Superseded interpretations — read these before trusting the raw diagnostics

- `unit_1821/logs/GAP1_PAIRED_COMPARISON.json` reports
  `caused_by_the_correction = true`. **That interpretation is superseded** by
  `GAP1_CAUSE_ANALYSIS.json` and Codex's independent ruling: its comparison was raw
  string equality over text containing invocation-specific data.
- The full failure text carries **both** the measured and the required run digest as
  well as pytest's directory index — not only the two tokens shown in the truncated
  first-cause line.
- The paired wrapper does **not** save subprocess stderr separately.
- Core SEQ 1819 claimed the failure was pre-existing on evidence that could not
  support it: that subprocess never loaded the candidate owner. The claim was only
  established later, under an asserted owner.

These diagnostics are preserved exactly as produced. They are not rewritten for
cosmetic agreement.

## What this does NOT license

**No historical prompt or model result was produced with the new cards.** Every one
of the 392 producer answers, the 206 selected G1 replies and the 207 raw attempts
stands as recorded, against the OLD cards. The 14 new cards touch 42 current
questions across 27 event batches — that is a description, **not** rerun authority,
and no completed call may be relabelled as having used new prompts.

## Gates still open

1. G1 meaning/evidence qualification, including the malformed-ID counted-refusal boundary.
2. G2/G3 source and other-produced-claim context through the real batch renderer.
3. Qualified zero-wrong-accepted safety over every production field, distinct from pooled accuracy.
4. Invalid / duplicate / disputed / all-arm accounting at the real final consumer.
5. Current direct dependencies and the real write-disabled route → `score_leg_official`
   → final gate, with focused and full-affected regression and mutations.

Any changed A7 prompt still requires fresh UNSEEN affected-prompt proof under the
prompt standard. Completed EXP0 tier qualification is reused and must not be redone.
