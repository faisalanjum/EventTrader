# A7 grader — non-AI code checkpoint

Status: the owner's final five-item pass and local qualification are complete.
Independent review and publication remain pending.
A7 remains UNMEASURED, not PASS. No new AI call was made. Main and production
code are unchanged.

The approved three-pass design is PLAN.md. STATUS.md preserves execution history.
CODE_FILES.json freezes the 93-file current harness and five current external
candidate/signature/lock owners. The recovery branch remains
`recovery/a3-a7-verified`, based on `1416bf946be4ef008f255bcef33ee14af387b455`.

EVIDENCE_MANIFEST.tsv binds the compact raw records, attempt maps and executed
payloads; EXTERNAL_EVIDENCE.json binds the full generated artifacts kept outside
this code-only publication. PUBLICATION_MANIFEST.tsv is the exact proposed
file allowlist, with SHA-256 and byte size for each path. It excludes itself;
the mailbox binds its exact hash. No attempt or export directory is staged
wholesale. The test environment uses the recorded durable input maps and the
existing virtual environment; this is not a standalone experimental-data export.

## Owner checklist — final scoped pass

| Requirement | Status / change | Verification |
|---|---|---|
| 1. Generality and hardcoding | Verified locally. Counts/names come from inputs; legal rules stay fixed. Extra-answer choices now use the same current scorer as the verdicts. | final_owner_red reproduced the retired dependency; final_owner_green passed all 94 score-boundary tests, including every legal/invalid extra shape and blind pair after disabling that retired owner. |
| 2. Complete workflow and dependencies | Verified locally on the final code. Cold producer → identity → meaning/extras → official score, exact saved-result reuse and source/key failures all pass. No new production layer is needed. | path_final5 asserts the exact INCONCLUSIVE decisions and 1/35 matched/required per score, not just successful execution; source_final2 passes 10/10 and preserves the real success; proposed4 proves cold export dependencies. |
| 3. Duplication and organization | Verified locally. Removed three further uncalled private helpers, six unused constants, five unused imports and one unused local tally. Public entry points and frozen history remain. | Current and tracked caller searches; FINAL_OWNER_CHANGES.json preserves removed functions and compares surviving bodies. Only the extras accessor and removal of the unused completion tally changed surviving functions. |
| 4. Simplicity | Verified locally. Reused the existing scorer binding; no new options, framework, model rules, wrapper or dependency. Kept distinct workflow, scoring and evidence duties separate. | Final source comparison: less code, one current extras owner, no change to legal answer choices or score bars. Existing route/matcher/publication owners remain shared. |
| 5. Tests and expected outcomes | Verified locally. All 36 current modules pass, with two explained historical-only skips. The restored-old-owner mutation fails at its intended assertion. | final_owner_red: one intended failure; final_owner_green: 94 passes; mut_owner: one intended failure; native_final5: 559 passes; ordinary_final4: 1017 passes / two skips. The unchanged production-dependency suite adds 3031 passes. |

## What changed, and why

| Required behavior | Smallest repair / owner |
|---|---|
| Callable current pipeline | Existing test boundary serves the complete current driver package, support scripts and exact recorded fixtures. No host-module preloading. |
| Complete reply/fact accounting | a7_conservation consumes the existing trace and frozen schedule; preserves every attempt, split branch and union origin. Packet grouping belongs once to a7_g23_build. |
| Unsubstitutable grading input | a7_g23_build revalidates the producer/manifest and compares a freshly derived input descriptor at the context boundary. |
| Write-once evidence | All six existing artifact writers use the existing raw_transport.write_new owner, via G._write_new; prompts first, candidate last. |
| Generic model prompt | G3's answer example became a schema placeholder; existing meaning definitions and bucket choices are unchanged. |
| Exact recall bar | Current scorer compares integer matched/required counts with the exact declared ratio, not rounded display output. |
| Interrupted capture | Existing audit owner checks capture length before indexing; missing evidence returns a named refusal. |
| One current extras contract | a7_g23_build.extras_buckets reads the already bound current scorer, just like meaning_fields; no duplicate configuration or new binding. |

Each behavior repair has red evidence, a lawful control, green evidence and an
intended removed-safeguard mutation. No second matcher, validator, scheduler,
schema framework or semantic word list was added.

## Final executed qualification

All paths below are relative to this directory unless explicitly prefixed REC.
Raw exits, stdout/stderr, collected IDs, JUnit results, exact commands, served
maps and per-attempt source freezes accompany the results.

| Evidence | Observed result |
|---|---|
| attempts/ordinary_final4 | 25 modules: 1017 passed, two historical skips, exit 0, 751.27 seconds. Current scorer used throughout. |
| attempts/native_final5 | 11 modules: 559 passed, no skips/errors, exit 0, 195.92 seconds. Includes the current seven-aspect/nonempty lifecycle, exact counts, 274 identity relation cases and the extras-owner regression. |
| attempts/external_final1 | 50 complete existing production-dependency modules: 3031 passed, 53 live/database tests explicitly deselected, exit 0. Unchanged code/tests reused after cleanup. |
| attempts/path_final5 | Actual cold generated-launcher path: 204/204 synthetic producer replies, completed G1, six G2 and six G3 lanes, exact 1/35 matched/required scores and INCONCLUSIVE decisions for deliberately unresolved extras. Zero model calls. |
| attempts/source_final2 | Exact saved real answer remains bound and not retryable; 35 source events still missing. Partial key refuses. Complete TEST source materialize/finalize/lock passes 10/10; missing native handoff refuses; restored control passes. |
| REC/a7_recovery/unit_1957/logs/attempt_signA, signB, signC | Reused exact unchanged key/signing owners: valid signing, missing-input refusal, restored signing and every lock-field mutation. These are TEST signatures, not reviewed source truth. |
| exports/proposed4 | Clean export: all 98 proposed code/assets present; 27 entry points and 54 loaded modules resolve to proposed or committed bytes; dynamic scorer, sibling reads and nonempty real no-write route/scoring execute. One retired extras-owner import is no longer needed. Not yet a staged-Git claim. |

Total final harness: 1576 passes and two historical skips across all 36 current
modules. Combined with unchanged external coverage: 4607 passes. These totals
are software checks, not a measured model accuracy or mathematical guarantee.

FINAL_TEST_CASES.json records every final harness ID. RECONCILIATION.json maps
every original failure: 191 exact IDs now pass, seven obsolete positives have
named current positive/negative replacements, zero unresolved rows. The original
198 failed/error records are preserved in ORIGINAL_FAILURES_AND_CLEANUP.json.

The two skips are explicit historical-only outputs:

- `test_the_v10_ledger_shell_derives_exactly_the_v9_key`: the old v10 correction
  shell is not prepared or used by the current approved-key path. Current key
  derivation/signing is proved by source_final2, signA/B/C and the current
  completed-run tests, including rejection of old positional data.
- `test_the_budget_receipt_is_derived_from_live_owners`: its retired receipt
  file is absent. Current accounting is proved by the completed-run ledger,
  current G1 freeze, never-called/missing-arm tests and exact schedule mutation.
  Historical budget arithmetic still passes in test_a7_postrun_identity_1521.

Neither skip waives a current requirement or is counted as a passing test.

## Required behavior matrix

Module names below mean their complete collected tests in FINAL_TEST_CASES.json,
not a hand-picked subset. Several families share tests; never add their counts.

| Plan family | Exact test/evidence home |
|---|---|
| T01 current identity/pins/era | test_a7_current_1473, test_a7_postrun_identity_1521, both test_a6_fixture_isolation modules, test_a7_g1_precall_freeze_1525 |
| T02 strict reader envelope | test_a1_invalid_response, test_a1_serial_transport, test_harness_guards reader/V2 public-door cases |
| T03 numbers/locators | test_harness_guards numeric/occurrence cases; external_final1 including exact movement, exact sign and complete relocation modules |
| T04 schedule/attempts/branches | test_a7_trace_1471, test_a7_current_postrun, test_a7_runstates_1470 |
| T05 matching/duplicates/positions | test_harness_guards matcher/union cases; test_a7_corrections_1454; trace branch/origin proofs |
| T06 both blind relations | test_a7_identity_relations: all 256 two-by-two relations with reordered rows/indices, sparse indices, 17 malformed identity cases and complete/missing envelopes; mut_identity1 |
| T07 seven meaning aspects | test_a7_score_boundaries: every aspect x nine blind pairs, false beside unknown; test_a7_corrections_1454 |
| T08 extras agreement/accounting | test_a7_score_boundaries legal bucket/null pairs; test_a7_corrections_1454 and test_a7_g23_lifecycle_1464 |
| T09 prompt/source isolation | test_a1_prompt_contract, test_a1_no_tools, test_a7_corrections_1454, test_a7_input_binding |
| T10 context substitution | all test_a7_input_binding cases: cold/warm, same-source altered context, manifest claims and byte-identical aliases |
| T11 actual no-write route | test_a7_trace_1471, test_harness_guards, external_final1; path_final5 and proposed4 nonempty execution |
| T12 raw/transcript binding | test_a7_raw_binding_1483, test_a7_closeout_integrity_1482, test_g1_declared_input_1792, test_g1_cached_resume_1781, test_a7_g23_lifecycle_1464 |
| T13 retries/reuse | test_a7_cached_rows_1413, test_g1_cached_resume_1781, test_a1_serial_transport, test_a7_trace_1471 invalid-primary/valid-retry, source_final2 |
| T14 interrupted error captures | all seven test_a7_interrupted_capture cases; mut_capture |
| T15 immutable publication | test_a7_publication: every writer, interrupted prompt writes and competing processes; mut_publish |
| T16 complete official population | test_a7_g23_lifecycle_1464; test_a7_current_postrun; current precall and identity tests |
| T17 exact bars/precedence | test_a7_score_boundaries and test_harness_guards official-bar/reliability tests; mut_counts |
| T18 union/original safety | test_harness_guards same-tier union, original veto, abstention and duplicate cases; test_a7_trace_1471 origins |
| T19 real TEST lifecycle | path_final5; source_final2; unchanged unit_1957 signA/B/C; full nonempty test_a7_g23_lifecycle_1464 |
| T20 actual saved evidence/full regression | exact source_final2 raw replay, both final harness runs and external_final1 |

REVIEW_INVENTORY.json rederives the current function/exception inventory and
links owners to these required families. Its syntax counts are navigation,
not a claim of exhaustive line coverage. No changed behavioral branch is
left as an unexplained in-scope failure.

## Mutations and preserved failed attempts

R2: mutation1 wrong identity; mut_schedule2 missing trace arm (204 required,
102 observed). R3: mut_inputs substituted context. R4: mut_publish all six
second-write cases. R5: mut_template actual answer instead of placeholder.
R6: mut_counts rounds 440/449 up to the 98% bar. R7: mut_capture missing/short
capture. T06: mut_identity1 ignores one reviewer's competing link; 112 intended
failures and 144 unaffected passes. These raw exit-1 runs are killed mutants,
never passing candidate runs. Each mutated function's source is saved; later
cleanup left those surviving function bodies unchanged.

R8: final_owner_red reproduces the retired extras-owner dependency; after the
one-line owner change, final_owner_green passes 94 checks. mut_owner restores
the retired dependency in-process and fails at that exact assertion. The cold
proof's strengthened result assertion is executed in path_final5; path_final4
was prepared but never launched. No successful model call was repeated.

mut_schedule survived the earlier inadequate test; retain it alongside its
improved test and killed successor. native_final3 used a mistyped validators
hash and ended with 479 passes/79 setup errors; native_final4 corrected only
the command's expected pin. Export probes proposed1/proposed2 exposed proof
setup dependencies; proposed3 runs the actual nonempty route without importing
the data-dependent general test module. Preserve every earlier failed attempt.

## Final genericness, duplication and scope decisions

Current populations derive from the supplied run plan and approved key; current
reference names come from signed packet/fact rows. The current test poisons the
historical count/span tables and varies population counts; results remain correct.
Historical source-specific span data is never a rule for new inputs. Schema keys,
legal verdict buckets, score bars and exact evidence pins are required contracts,
not arbitrary examples to erase. Unsupported inputs are rejected, not guessed.

One shared identity owner, one packet-group owner, one immutable writer, one
current scoring owner, one input-binding owner. G1 relation handling, G2/G3
meaning questions and saved-workflow validation remain separate required jobs.
The last AST comparison of 14 active owners found only three identical one-line
wrappers of the standard SHA-256 primitive; a new abstraction would add no rule
or safety. No further restructuring is warranted.

Removed one duplicate candidate test file, six obsolete saved-run positives,
obsolete weaker accounting/publication/context helpers, and five uncalled
private helpers from the current scorer plus their orphan constants/imports.
No surviving scorer function changed in that last cleanup. Original bytes and
old attempts remain recoverable. The producer-era scorer is retained because
frozen evidence hashes it; it is not an alternative current grading policy.
No historical snapshot is deleted or re-signed.

The owner's final pass additionally removed three uncalled private helpers,
six unused constants, five unused imports and one unused completion tally.
FINAL_OWNER_CHANGES.json preserves the removed functions and the exact body
comparison. Public callable entry points stay even when they have no static
caller in the harness: the cold workflow calls some of them from outside it.
The old/current helper comparison was repeated; retained routing, matching,
union construction and identity helpers are identical. This preserves the
explicit PLAN 7.2.1 decision without moving current scoring law back to history.

This grader is an offline evaluator, not a new production service. The real
production number/identity/route owners are already shared unchanged. Step 3
later moves the adopted reader/parser/prompt owner rather than copying it;
Step 5 owns integration. This checkpoint neither activates production nor
claims every later-step integration test has passed.

## Independent review and publication gate

Review the frozen code, required behavior matrix, raw proof and exact input
bindings, not this summary or a green count alone. Raise only an observed
required correctness/safety gap; no style-only rewrites, model calls, later-step
work, edits or publication by Core. One combined response, then wait.

Publish only the exact independently approved code/test/evidence slice on the
existing recovery branch, verify staged identity and normal push, and preserve
unrelated files. Full test inputs/attempts remain durable, hash-named external
evidence; this code checkpoint is not a complete distributable AI experiment.
Before claiming A7 PASS, W7 still needs remaining source/key meaning review
(reuse the one saved success), and W8 needs actual authorized producer and
grader answers, complete scoring and independent verification. No A8/later step
starts on an inconclusive or failed A7 result.
