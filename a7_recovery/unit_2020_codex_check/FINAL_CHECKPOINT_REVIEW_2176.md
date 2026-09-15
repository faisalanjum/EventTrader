# Final A7 measurement checkpoint — FAIL, not qualification

Codex, 2026-09-15 UTC. Reviewed parent:
37dd71d2901f448dc8fe373f4fd8f35157cee4f6 on recovery/a3-a7-verified.
Owner authorized verified partial commits/pushes on this same branch.
This checkpoint preserves a verified calculation and its limitations; it
does not assert that all model judgments are correct or that A7 passed.

## Results

FINAL_SCORE_FINDINGS_2174.md is the concise result/cause report. Native output
966d14bc71ee487afdeff88a41fbf59ccf0e68c349a342c96a60aa0ff733a062:
123/165 (74.55%) and116/165 (70.30%) matched facts; strict combined71/165
(43.03%). Wrong-accept flags9/9/8; incomplete meaning judgments48/38/18.
All three safety results FAIL. No single overall model-accuracy percentage.

The final score used99 actual no-write routes and4 distinct native completion
loads with zero new model calls. Both new completions were independently
re-derived/persisted/loaded. Full426-question comparison proves all388
unaffected questions unchanged;24 selected outcomes changed and14 did not.
All26 collected attempts are bound to their original state, raw reply,
script/invocation and child transcript. The two retries followed invalid
format only. Original382 reader answers and earlier evidence remain intact.

The source review establishes concrete defects in23 of26 flagged records,
not in the other3. It also identifies grader errors/uncertainty; raw labels
are not silently replaced. Core2171 independently rechecked and conceded the
four qualifications to Core2170. No new key omission is established by that
review, and no unchanged successful judgment is rerolled for a better grade.

## Completed checklist and actual verification

| Pass | Result and evidence |
|---|---|
| Hardcoding/generality | VERIFIED for this delta. Reporting derives distinct lanes and remaining attempts from frozen structured records. No issuer/example rule or semantic code. Frozen model/hash/run strings remain required provenance. |
| Workflow/correctness | VERIFIED calculation/evidence connection, with explicitly unresolved semantic judgments. Native99-route/four-load score and all426-question comparison, not just a green unit-test count. |
| Duplication/organization | VERIFIED. Existing capture, parser, completion, revision, reader, route and scorer retained. One current progress owner; earlier executable scripts preserved only as historical execution evidence. |
| Simplicity | VERIFIED. Only the proved reporting-counter defect changed behavior. Offline reuse work adds tests and a review, no client/engine, provider framework, second grader or extra AI round. |
| Testing | VERIFIED within stated scope:318 tests plus29subtests passed in3.34s,exit0. Reporting fix first failed7 tests with2 passing controls; then9 focused tests and4 executed reversion mutants passed.15 offline reuse checks include unfamiliar input through the real no-write route/scorer and confirm known local-client limitations. |

The exact final regression command is FINAL_REGRESSION_COMMAND_2176.sh;
OFFLINE_VERIFICATION_2176.json/c8ae5a8f0b8e37f9cefbd27cc2b4cb756e5f4e8a69c3b86fbaabaed436826daf
preserves the actual focused and full-regression tool results. Earlier native
stdout/stderr/raw-exit and all raw collection evidence are retained unchanged.
The numeric trace is a separate deterministic check, not a meaning judge.

## Model reuse is deliberately qualified

MODEL_REUSE_OFFLINE_REVIEW_2176.md/73c658b89882f11d3b62a9b5468d2218c1667cea3014be9a444585e53082ddb7
documents15 passing offline checks. The shared grader is reusable. A local
model-name-only launch is NOT verified: host capacity, actual returned model/
completion capture and the local receipt connection remain open for the
separate host task. No live local inference or engine/client change happened.
The two owner-named local instruction files are untracked in main; exact
read-only evidence copies are preserved under snapshots_2176, with the same
hashes as the originals. Those snapshots are NOT new live authorities.

## Publication boundary

FINAL_CHECKPOINT_FILES_2176.json/5737b55b1155d2efef2418ffb0ff437d4396794f4345573eae602785b35be8be
freezes722 payload files,40921784 bytes, largest1705884 bytes. These are mostly
saved answers, execution evidence and99 route reports, not722 source modules.
The manifest, this review and the final shared work order are additional
metadata covered by the Git tree. All payload files are regular files; no
symlink or blob at/above100MiB. Parsed Python and shell syntax checks pass;
the scoped secret-pattern check found no hits. Exact staged bytes and the
manifest must agree before normal commit/push; no history rewrite.

Preserve and exclude the unrelated dirty build_inventory_review.py SHA
2ec3bd338f7dce181ff6794790cf634c6f68e73217daef88a25e365731ee4ed2,
all unrelated untracked files and test working directories. Main HEAD stays
2dc0ad39f30dba4756078573f5e80038465939cc; none of its dirty files are edited.

After normal recovery-branch publication, report these results and STOP/WAIT
as the owner requested. A8 and later steps are not authorized, A7 PASS is not
earned, Step14 stays dormant, and the old all-steps goal is not achieved.
