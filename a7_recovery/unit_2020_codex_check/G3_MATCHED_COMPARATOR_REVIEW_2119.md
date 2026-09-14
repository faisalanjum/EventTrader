# G3 duplicate prerequisite — bounded cause review, Codex

Status: reproduced mismatch; the minimal repair below is not implemented or
approved for a call. Do not change Core's currently frozen2120 proof mid-run.

## Evidence and scope

The live exp5_scoring_spec_v3.md §5 defines an extra duplicate as a duplicate
of a MATCHED fact. PartD retains independent identity adjudication and forbids
choosing a winner from an invalid group. The historical bucket definition in
unit_2006/harness_g1v3/a7_g23_build.py instead says any claim already stated
elsewhere in the run. Its packet includes all other produced assertions, even
unmatched or refused ones, and its rule4 also permits other asked extras as
comparison records. Two unsupported or unresolved assertions can therefore
satisfy the stated duplicate definition without satisfying the actual rule.

CORRECTION_SCOPE_DIAGNOSTIC_2119.json and its exact saved command derive the
full population from trace0b4a3f62 and the actual existing matched_pairs owner.
Positive controls reproduce ALL baseline matched counts:121/114/71.
There are92 agreed duplicate labels:1/1/90 across P1/P2/UNION. Fourteen UNION
labels are in events with ZERO matched facts, so they cannot mean "duplicate
of a matched fact":

- 0000898173-26-000006: produced2,4,6.
- 0001104659-25-118458: produced0,1,3,4,5,6,7,8,9.
- bzNews_50877032: produced0,1.

The other78 labels are not proved correct by there being some unrelated match
in their event. This is a population-wide input/rule boundary, not14 semantic
exceptions. The separate accounting correction already keeps unresolved G1
groups visible and the baseline FAIL unchanged; it does not validate these
G3 bucket labels. No original reply or score was changed by this diagnosis.

## Smallest proposed repair to verify before use

Reuse the existing G2 full population: it IS the exact final matched-pair
inventory, produced by the existing matcher/G1 owners. For a corrected G3
packet, expose only the raw produced comparison records named by that
inventory for the same leg/source. Preserve the full source and all reviewed
reference cards. Never replace semantic matching with labels or exact text.

Do not send any G1 verdict, detector finding, grade or interpreted answer-key
field to G3. These remain raw comparison records for an independent meaning
judgment, just as G2 already receives raw paired records from the same match
inventory. Presence in the comparison pool does not prove source correctness.
The grader must check the complete asked claim against the full source and
field contract before calling it a supported duplicate; repeated unsupported
assertions do not become truth. If a source-backed claim has neither a valid
duplicate relation nor a genuine key omission, null remains lawful.

Keep the existing two-field G3 reply and existing parser/completion/scorer.
No duplicate_of schema, second relation matcher or new grader is justified
if this filtered raw-comparison pool proves the required boundary. Bind its
complete matched population to the NEW candidate and compare it against the
consumer's already-derived required G2 population before accepting a G3
correction. This makes membership deterministic and auditable, not a caller's
unchecked assertion or a separate semantic rule.

Required proof: all117 current G3 questions retain exact question/source/card
identities and receive exactly their event's matched comparison records;
empty pools stay explicit; other asked unmatched questions cannot stand in
for a matched comparator; unrelated or altered populations refuse; valid
matched duplicates still work. Exercise positive/negative, unfamiliar and
multi-question/batch cases through the existing consumer. Preserve old
versions and rerun affected prompt, input-fit, native and mutation checks.
No AI call before this boundary and the final affected population are frozen.

## Two separate source-key leads, not yet adjudicated

The original source-only task accepts only each frozen raw_label_or_claim and
its fixed quote, using the full event as interpretation context. It is NOT an
exhaustive new-source harvest. This matters before commissioning any review:

- ORLY original row3/#052 targets "Ending domestic store count", fixed quote
  "Ending domestic store count [zero-width spacing] 6,447". The actual source
  table supplies prior counts. The delivered Rule4 explicitly says a prior
  value stated in the SOURCE beside the value implies direction; check that
  boundary independently without extending the quote or adding numeric
  operands outside the allowed evidence. Geography remains separate.
- CAKE original row4 selects "North Italia operating information: Comparable
  restaurant sales vs. prior year". Its fixed quote includes all four values,
  -4%,1%,-2%,2%; its target contains no current-year-only restriction. The full
  table supplies the periods. The key's deliberate omission of the two prior
  columns therefore needs review against the actual selected target and
  DU-03, not a newly invented current-period-only gate.

Both original row arrays were read from the preserved source-only2068 scripts,
not reconstructed from tested outputs. Any new key owner must still be fresh,
isolated and source-only. Do NOT supply this output-informed review note, the
tested replies or grades to that owner. Use the original frozen targets,
sources and governing rules; preserve all valid completed source reviews.
