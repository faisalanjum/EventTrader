# Checked score causes — working review, not replacement grades

Codex 01a05829-3086-73e0-89c9-e5773b322d80, 2026-09-15 UTC.
Scope: the already completed A7 score and its actual findings. No new model
call, raw-answer edit, manual grading override, key change or production patch.

## Exact measured result and replay

The native A7_CORRECTED_SCORE.json remains
656c18bd363ac3941a737d4d3ae55b101f303c209727ed261325a42e9664f08a.
Its P1/P2/UNION recall is 123/165, 116/165, 71/165; these are required-fact
matches, NOT overall accuracy or a source-verified final score. Native
wrong-accept flags are 9/9/8. All three results fail and grading is unfinished.

CORRECTED_SCORE_TRACE_2167.json
b3a759b5abf9fc94ab0c89f9e4826b7588f32cab7c25e02f516d9d6230942f27
uses the real matcher and scorer, not a second implementation. Its caller
trace_corrected_score_2167.py is
580f1d0b93c47eb6061cae46e9c1f4ac9f3480d6ba28425b15e325122f106ee8.
The saved command completed with exit 0. It reproduces all 310 matched pairs
and 16 native measurements per leg exactly. It does NOT replay response
reliability, external G1 group findings or the final tier decision.

Inventory: 185 recall misses (42/49/94); 33 negative meaning questions,
including 23 route-accepted; 116 incomplete meaning questions (48/45/23);
114 agreed extras (100 key_miss, 11 duplicate, 3 unsupported). The two
unresolved extra judgments remain in measured.UNION.ambiguous_rows, not the
114 agreed-extra rows. Together with five missing P2 G1 rulings they account
for all seven native ambiguous_rows. This is not seven additional AI calls.

All 857 captured native error-counter events are retained, including 512
field mismatches. FableExperimentWorkOrder EXP-5 explicitly compares the
three raw numeric fields; equal converted amounts do NOT authorize changing
that formula. Exact dates, defaults and measurement-token comparisons also
remain the locked raw-field measurement, not a second source-truth judgment.

## Every route-accepted negative flag

The following table covers EXACTLY the 26 native wrong-accept flags, each
once. A supported cause means at least one actual source/rule error was
located. It does not endorse every negative aspect or claim to recover a
grader's unrecorded reasoning. Six rows remain unclosed; do not turn them
into manual positive judgments. The 20 other rows have the stated concrete
cause. This is review data, not an alternative numeric precision score.

| Question | Source-backed cause or exact remaining question |
|---|---|
| M35df46a5d2795d66 | P1 fuel: exact change 4 billion does not preserve the source's greater-than-4-billion bound. Magnitude alone is correct. Guidance state is a separate issue. |
| Mec9e16d57c989430 | P1 tax expense: -94 versus -175 increases on the signed axis; the record says decreased. |
| M292ac8520c3978ff | P1 adjusted pretax income: -327 versus -530 increases; the record says decreased. |
| Md5b6d93a0e42868a | P1 restaurant sale: the same source reports its July 14, 2025 closing; announced is not the latest stage. |
| M6d2b09a6d78a96e6 | P1 sale: -0.26 is a per-share earnings adjustment, not transaction consideration without a per-share basis. |
| M6d9dd25a44c4125e | OPEN: 2.68/2.74 diluted continuing EPS, prior year and Q3 FY2026 are supported. A null change value alone does not establish the negative growth/whole-record judgments. Preserve the original verdicts. |
| Mc0fee81b5ffc9975 | P1 Habit: 79 percent is the company-operated share of U.S. stores, not unit_count. |
| Mcb1fb316d377bb0a | P1 Chipotlane performance: an empty metric population asserts whole-company scope; this source statement concerns Chipotlanes. |
| Md2061d63bedc8f75 | OPEN: a 90-percent floor is not an exact rendering of 'in the 90s'. Whether this deliberately weaker bound is a wrong accepted fact, rather than incomplete precision, needs an explicit source/rule disposition. Do not invent an upper bound or use a digit heuristic. |
| M63a211408d38ee40 | P2 fuel: raw 4000 times 1e9 is 4,000,000 million dollars, not 4,000 million. The greater-than bound is also lost. P1's raw 4 is the positive magnitude control, not whole-record approval. |
| Mde7d5e39712de0c7 | OPEN: 171 million is shown in the consolidated table and attributed to Health in surrounding text. The action's empty population, and the table's dash versus a stored zero, need exact rule disposition; table/card equality alone proves neither negative aspect. |
| M53a1b3ba077cabd8 | P2 restaurant sale: same source-confirmed completed sale, not merely announced. |
| Mc6c32dee91400e91 | OPEN: this record actually has an EMPTY population, not a Bahama Breeze slice. The footnote says primarily Bahama Breeze, not exclusively. The current gold row also has an empty population. A pre-tax measurement omission is separate from the unsupported negative slice explanation. |
| M6a52868797fca479 | P2 sale: the -0.26 per-share adjustment is not the sale value. |
| M0c5dd9bbeece43b0 | P2 adjusted EPS: source supplies 1.73 versus 1.61 and +8%; reported ignores the source-stated prior comparison. |
| M884c4845393d55ce | P2 Habit: 79 percent ownership share is not a unit count. |
| Mf91a92c59065852f | P2 AAL: exact 10-percent change is not the source's less-than-10-percent statement. |
| M8351d2825bae0891 | P2 gates: 17 gates belong to a future project due to break ground in 2027, not an already reported current metric. |
| X0cca68dc69dcd11b | UNION adjusted pretax: -327 versus -530 is an increase, not decreased. A correct underlying key claim already exists. |
| M8624b63494238990 | OPEN: domestic online share 31.8/31.4, Q3 FY2026 and increased are supported. Complete fiscal framing need not invent endpoint dates. No actual whole-record error is established by the existing negative label. |
| Xa2480c79b460e114 | UNION sale: -0.26 is the per-share earnings adjustment, not sale consideration. |
| X4ebf8857741ae6a8 | UNION sale: the other raw rendering retains that same wrong consideration meaning. Its differing scale-evidence/time fields do not cure it. |
| M31b20a4a0b7e5203 | UNION adjusted EPS: reported ignores the same source-stated 1.73/1.61 comparison. Do not use a separate growth-basis uncertainty to erase that state error. |
| Ma31af1665347b9ec | OPEN: 'nearly 60%' does not require an exact 60. Preserve cautious omission; system-sales scope and digital_mix naming still need their own disposition. |
| M02d957fa99800507 | UNION AAL: exact 10 percent versus less than 10 percent. |
| M8f3cb6b387ec8ba9 | UNION Pizza Hut: projected -15-percent business growth is placed in change_value, but guidance growth belongs in level slots; change_value is only the guide's own revision. Unknown state is not the error. |

These are not all possible reader errors: some records with positive grader
judgments have already proved magnitude/state errors in CAUSE_REVIEW_PROGRESS_2165.md.
Preserve those false-negative grading findings too. Never obtain an improved
score by reviewing only the negative flags.

Existing source evidence, reused without another model call:

| File in this directory | SHA-256 |
|---|---|
| G2_CARRIED_FALSE_SOURCE_EVIDENCE_2165.json | 82d727fdb7dc6ee8eaef8e0db6326e1663de5a310aed6d098aedc1527fa74281 |
| G2_CORRECTIVE_BATCH0_SOURCE_EVIDENCE_2165.json | 1a614e29cfc954751fb6d73252a281b7835cc90ae4a77774edb8f4592c5db3a2 |
| G2_CORRECTIVE_BATCH1012_SOURCE_EVIDENCE_2165.json | 08a439d6f26ee2019d4e51f8ae0192ad156dd4ccd24aaf73709332214f1d3300 |
| G2_CORRECTIVE_BATCH345_SOURCE_EVIDENCE_2165.json | 055a479c8ba9e7b92cc7aaf2de3d5e7e5b4475dfebe7f9c7989188841a0e4913 |
| G2_CORRECTIVE_BATCH67_SOURCE_EVIDENCE_2165.json | 94d8aaa2946572b1cc5fd10928943d05c18d421206e49c20e639403fada84222 |
| G3_CORRECTIVE_BATCH1921_SOURCE_EVIDENCE_2165.json | 647f5db51ebe28e7a88bbb3be38fc63b4a12da03402d6a99f9073e0f4654667c |
| G3_CORRECTIVE_BATCH78910_SOURCE_EVIDENCE_2165.json | a94ef2b5340d6a722fb73c8bd90380fd41118573ecfc2546d35b0114eead71fa |

## Core2163's 100 key_miss dispositions

The 100 consumed identities and all their question hashes independently
match the native report exactly. Core's four file hashes also match. This
validates the inventory, not its 86 blanket semantic approvals. A shared
sentence and a Decimal value set are insufficient to establish a complete
fact's population, unit, bound, period and meaning. The earlier source review
already locates errors inside that supposed 86-row correct-record class.

No new missing key fact has been independently established by this review.
That is NOT a claim that all 100 labels have now received a final qualified
replacement. Do not infer either 86 correct reader answers or 100 corrected
grades. The live Plan amendment permits verified key corrections to be
regraded on the same saved answers; it does not force a fresh whole exam.

Core's two Starlink rows do have accessible key-side evidence: the native
report's key['0000092380-26-000044'][5] is the announcement. Its explicit
source-only ambiguity_note deliberately keeps the 300-aircraft deployment
target and year-end horizon in the quote, without a forced split or level.
Produced UNION[1] adds a 300 floor and Q1 FY2026 instant; UNION[3] adds the
floor but no time. Neither proves the announcement is absent from the key.
The added quantity/time assertions remain a separate meaning question; do
not replace their buckets using code or infer missing key truth from an
empty card value list. No further key call is justified by missing access.

## State-contract decision still to settle

FINAL_DESIGN 4.3 explicitly routes a source-stated metric prior comparison
to increased/decreased rather than reported. The served grading contract
does tell graders to keep that comparison apart from a bare reported level
and uses signed numerical direction, but does not spell out that mapping.
This is a concrete instruction-clarity lead, not yet proof that a new call is
required. Check the actual whole contract and controlled producer task before
calling it a test defect. Do not add a company list, infer temporal comparison
from two card values, or reroll valid replies merely because an explicit
sentence might produce a preferred answer. No prompt was changed here.

## Bounded checklist after this pass

| Item | Status and verification |
|---|---|
| Generality / hardcoding | Unchanged supported grading owners; no new semantic code, company rules or score adjustments. Review IDs are exact evidence identities, not executable decision rules. |
| Workflow / correctness | Native completion and score already verified; independent 310-pair / 16-measurement replay passes. Source dispositions and raw G1 miss causes remain open as identified above. |
| Duplication / organization | Real matcher, scorer, routes and existing source evidence reused. This note records causes only; it is not another scoring implementation. |
| Simplicity / scope | No speculative production/local-model work or rerun. Core2168 has the single bounded 185-miss raw-cause task; Codex owns remaining semantic decisions. |
| Tests / limitations | Existing affected regression: 239 tests plus 29 subtests, exit 0, 2.96s. New work here is read-only replay/review data, not a behavior change. Table population and evidence hashes checked separately. No final semantic score, universal reliability or A7 PASS claim. |
