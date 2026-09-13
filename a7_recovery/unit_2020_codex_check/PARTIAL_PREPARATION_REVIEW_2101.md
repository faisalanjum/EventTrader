# Partial-score preparation: independent review

Codex, 2026-09-13. This approves the narrow reporting and request-size changes
for the recorded preparation. It is not an A7 score, PASS, or production gate.

## Completed checklist

| Requirement | Change and actual verification |
|---|---|
| Honest partial reporting | One scoped admission policy, 56 lines. Original evidence/parser/finalizer and scorer remain authoritative.24 focused tests;6 mutations killed with their intended assertions; restored control passes. |
| No silent loss or invented credit | Real signed key, all382 producer replies and194 G1 calls reach native TEST G2/G3 completions and the actual tier scorer. All99 event/leg routes occur exactly once;163 gold facts remain per leg; the5-question gap gets no credit. Removing only the policy restores the original refusal. |
| Generic, bounded request sizing | One existing grouping owner changed:26 added/5 removed lines. It uses the original renderer and existing size limit, splits oversized batches, never truncates a source item, and derives counts from actual rows.7 tests;6 mutations killed; exact byte boundary, escaped Unicode, unfamiliar inputs, whole-item refusal and empty/small controls covered. |
| No duplicated meaning or rule owner | No new semantic rule, prompt change, parser, scorer, runner or validity table. One reporting-policy owner, one batching owner, existing workflow-size owner. Historical frozen files remain evidence, not alternative active implementations. |
| Whole affected population | All423 questions and their source cards, context, produced records and controlling instructions remain identical after regrouping. All172 resulting lane scripts fit: G2max516367/G3max207821 versus524288. Fresh-process derivation agrees. |
| Affected regression |19 unchanged test modules against current grading owners:698 passed,2 explicit historical-artifact skips. No missing/extra/repeated module. Correct historical source-key verification context is separate from current grading code. |
| Real pre-launch path | Original Python preflights passed, but the platform then refused direct recovery execution. The2103 correction uses the proven2088 supported-path/durable-backing arrangement. Identical roots, arguments, questions and owners; both final operator preflights pass and wrong-receipt controls refuse. See `G23_TRANSPORT_REVIEW_2103.md`. No AI call. |
| Scope/simplicity | No DB/production change, old-key reconstruction, answer regeneration, general framework or unrelated cleanup. Independent review retained required constants/contracts and rejected treating TEST outputs as scores. |

## Identities and raw proof

- Policy `a7_partial_grading_2095.py`:
  `1a465b94ff57789bee9bc210b36e7b892768156975702160fe22cd46b16db959`.
- Grouping `../unit_2098_g23_transport/a7_g23_run.py`:
  `e7e3012229945480ba2b86a4eb00dccee0e3152af86d98ff738329f8cba7063d`.
- Native connection `codex_partialscore2099_c/SCORING_CONNECTION.json`:
  `30ae7917ec623986bd9d411e5fb907097d256cbdb4a74d3ac63bdfc5192e05cf`.
- Whole-question comparison `codex_g23compare2099_a/COMPARISON.json`:
  `8b6d37cd76f06ab06dbbc89b418d3aa37e49e2c31cacb06f2a315076cd519269`.
- Full transport `codex_g23transport2099_green/TRANSPORT.json`:
  `5a75dc81254bbd3a8ce1eb5d0cc764d754af92aa436bc17ed8c154e926d441b6`.
- Fresh derivation `codex_g23partial2099_cold/PREPARATION.json`:
  `ab93cf3f7581ada92699310573c55578f8280244027735fc1c8d9d0b4af0e17c`.
- Full regression stdout under `../unit_1957/logs/`:
  `attempt_grader_native2100/stdout.txt`
  `61eaddc2869467ac032d2e1361060ad00093702b3d0a95215be98cd5470cee04`;
  `attempt_grader_ordinary2100/stdout.txt`
  `ab504a06d9a8aae34769785575a291c5e820a546eb80cbe09b8d78877fc8bc14`.
- Focused/mutation raw logs under `../unit_1947/logs/`:
  `attempt_codex_partial2098_nolaunch_green`,
  `attempt_codex_partial2098_mutations`,
  `attempt_codex_g23transport2098_mutations`.
- Original unrun roots and local preflights: `G23_LAUNCH_REVIEW_2100.md`.
  Superseding supported execution paths and exact unchanged-request proof:
  `G23_TRANSPORT_REVIEW_2103.md`. The2100 roots must not be launched.

The earlier setup failures are preserved, not converted to passes. In
particular, a shell/payload exit0 did not make its failed test modules green.
Codex independently read the final raw per-module exits, compared each test
file and eleven directly relevant grading/transport/producer-owner files
against the real map, and found no owner/test drift in either final family.
The two disjoint final families cover exactly the complete19-module inventory.

## Why the regression initially failed

The old source-key fixture was signed under its original key and hard-review
owners. Current verification rebuilt those historical receipt fields from
newer owner bytes and a clarified hard-review prompt. Serving only the old
key owner changed the failure from `derived_from` to `prompts`; supplying
both correct historical source-key owners cleared that gate. The original
verifier still ran. No receipt was rewritten and no check relaxed.

Those historical source-key owners apply only to the preserved TEST key.
All grading owners remain current, including the new grouping owner. This
does not claim the old/new key owners are interchangeable under every later
configuration: the current version deliberately separates row and transcript
model identities, and the hard-review owner also supports partial schedules.
The real signed key uses its separately proved current source-only context.

The other fixture family uses a different source inventory and runtime input
declaration. Its old correction expects196 records; the wrongly mixed view
provided102. Running each unchanged test with its own documented fixture
family resolves that mismatch without changing counts or real source data.

## Explicit limitations / skips

- `test_the_v10_ledger_shell_derives_exactly_the_v9_key`: the optional old v10
  shell is not prepared. This artifact is not on the current source-only key
  path. Current key conservation/binding is proved by the signed163-fact key,
  fresh preparation and real-key native scorer connection above. Do not
  rebuild the obsolete11-pending-target shell merely to remove a skip.
- `test_the_budget_receipt_is_derived_from_live_owners`: the optional old
  budget artifact is absent. Its unrun1479 producer and still-unknown G3
  schedule are not this run. Current accounting has862 completed calls,
  including194 G1 calls, and172 required new grading calls:1034 after primaries,
  1206 maximum including one invalid-only retry per new lane. The194 are
  never added a second time. Actual frozen launch records
  derive these totals from their source ledgers and candidate rows.
- One regression module emitted a365-byte Neo4j driver destructor warning;
  this is recorded, not called stderr-free and not expanded into cleanup.
  The real preparation also retains four guidance-period warnings; their
  actual effects belong in scoring, not an unapproved production edit.
- G2/G3 meaning judgments remain uncollected. Native TEST verdicts exercise
  plumbing and failure accounting only. They cannot establish a real score
  or universal reliability. Real G1 already contains duplicate/disagreement
  findings; retain them in the final report and investigate actual failures
  under the approved correction/reuse rules afterward.

Next: freeze the exact publication manifest, stage only this reviewed
preparation/evidence, verify the staged tree, commit and push normally. Then
authorize bounded real G2/G3 collection; do not repeat successful calls.
