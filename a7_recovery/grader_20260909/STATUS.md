# A7 grader repair — active implementation

Owner approved implementation after the three-pass plan review. Codex is the
only implementer. Core 1947 acknowledged Codex 1959 and remains paused until
the final independent review. No AI call, main edit, database write, activation,
new watcher or goal is authorized by this non-AI checkpoint.

## Frozen start

- Branch: `recovery/a3-a7-verified`.
- HEAD: `1416bf946be4ef008f255bcef33ee14af387b455`.
- Git tree: `bc76fa84c09cdfbea6848a2c2bdd6ff940d82244`.
- Tracked worktree and index were clean; existing untracked recovery evidence
  belongs to the owner and must not be staged or changed wholesale.
- Original: `../unit_1957/view/tree/harness_g1v3` (88 files).
- Original boundary SHA: `28a8d99ff230fefbb858cab890e4ffbb9745cafc5388ae5b23720eff3ea8dc72`.
- Original path-relative manifest SHA: `3884426ad55e9d83f4690890b6188ef79403a7b9532fa67e0fb554a392b1a90f`.
- Approved planning document SHA: `8d8e4e512674998dc389af81a16cfff2b75283109d18d7042834a42ab3510f60`.
- Saved real answer SHA: `625140d6eb637e029b885f356f3cb68a12ffb8c7ce1e8fded272e36b2471030b`;
  keep the answer and all its receipt/transcript bindings. Never repeat it.
- One existing watchmedo process verified (1035973); paused goal reused, not recreated.

## Work and completion gates

Follow PLAN.md W0–W6, in order. W0 snapshot is complete. W1 first repairs
test bindings and proves a cold complete offline path. Then repair only the
reproduced accounting, context binding, immutable publication, prompt placeholder,
exact score threshold and (if reproduced) interrupted-capture defects. Preserve
every failing run. Record focused/full/mutation evidence and every old failed
test's disposition. Do not call an import error or wrapper exit a passing test.

Final code readiness requires exact frozen changes and independent Core review.
Only then publish the reviewed non-AI code checkpoint. AI source/key collection
and actual A7 grading remain later W7/W8 work. Original run 1773 stays FAIL;
fresh A7 stays UNMEASURED. No production reader, later-step work or new framework.

## W1 checkpoint (2026-09-09 15:10 UTC)

Cold full path passed in `attempts/path7/logs/attempt_grader_path7/`:
204/204 synthetic producer replies finalized, actual G1 complete, G2 and G3
each six lanes (three event/leg questions, two blind answers apiece), actual
official scoring returns P1/P2 INCONCLUSIVE as expected for deliberately
unresolved extras. All 21 loaded driver modules come from the complete pinned
current bench/driver tree, with no pre-import from main or recovery masking it.
This is a usable nonempty test path, not experiment accuracy or a clean PASS.

The original 1957 tree is unchanged. Working-copy test helper `g1_fake_state`
now accepts an explicit TEST project root and unique run id so G1/G2/G3 share
one canonical store without overwriting each other's workflow state. The default
fixture behavior is unchanged. No application repair has been made yet.

Focused run `closure1`: 221 passed, four missing-helper import failures.
`closure2` exposed the next missing shared script and historical fixture
failures. `closure3`: 165 passed; all four remaining failures are the real
number-fix route tests importing missing recorded packet data. Their exact
data files will be bound before final regression. Existing 198 failure rows
remain open until individually reconciled; the W1 exit is the cold current
path, not a claim that the entire historical suite is green.

Preserve failed path1 (ordinary key/native input mismatch), path4 (older
native key/changed carrier mismatch), path5 (TEST extra had an invalid name),
and path6 (TEST input wrongly supplied a derived period scope). Path2/path3
were prepared but never launched. All were no-AI fixtures; no paid answer was
repeated. `path7` uses the previously proved 1957 native key/signC lineage,
not the stale 1942 key. No key or production rule was weakened.

Next W2: reproduce the live conservation failure, consume the existing trace,
and prove complete packet/fact/attempt accounting. Remaining R1 historical
fixture repairs are final-suite obligations in W5, not separate new features.

## Owner cleanup/publication instruction

After verification, remove superseded code in this grader component only when
caller/import/script/manifest checks prove it is unused and it is not needed
as historical evidence. Replace an old behavior in its existing owner; do not
leave a second active implementation. Preserve original snapshots and successful
raw answers with their bindings. Commit and push only the independently reviewed
checkpoint on `recovery/a3-a7-verified`, not a second branch. The W1 plumbing
pass is not approval to publish the still-unrepaired grader.

## W2 checkpoint (2026-09-09 15:44 UTC)

R2 reproduced publicly before editing: `trace_red5` had five failures, including
opening the old slot tuple as a file, rewalking sealed answers, and absent branch
accounting. The original failed owner is preserved in the original snapshot and
that attempt's immutable `view/harness_g1v3` copy.

The replacement stays in `a7_conservation.py` (189 lines, originally 204): it
reads the one materialized trace, preserves all parents/attempts, derives the
full required identities from the frozen plan, and keeps each fact's own route
outcome plus union origins. Route labels come from Core's PUBLIC_DECISIONS.
Packet-group derivation moved into the existing route owner in a7_g23_build;
the grader and accounting consumer share it. No semantic rule was added.
Removed the obsolete scalar/strongest-outcome logic. Removed the unused duplicate
key-preflight count from producer accounting: the existing B.preflight_problems
still owns that gate, and an uncalled producer can now be counted without first
preparing grader reference cards.

`trace_green4` ran 20 tests: all ten trace/accounting cases passed (real mixed
split, full uncalled and one missing arm, exact identities, route-loss mutations,
and actual invalid-primary/valid-retry finalizations with both raw attempts).
Its other ten tests were the NEW R3 red tests: six passed, four demonstrated
acceptance of substituted same-source inputs or forged manifest claims. Overall
exit 1 is expected at that red checkpoint, not a full passing suite.
`trace_green3` also ran both complete negative-number/guidance-fix modules;
all 165 external tests passed after their recorded input fixtures were served.
Its two remaining failures were test setup, corrected in green4.

Current TEST lifecycle fixtures must be generated under the CURRENT owner hashes.
Old path7 G1 pins correctly refuse after a7_g23_build changes. The already
executed source producer is still reused exactly; g1_fake_state now owns the
offline lifecycle helper moved from offline_path.py, so tests produce current
TEST G1 evidence without any model calls or forged pins. The copied TEST project
store contains the reused key and producer lineage; new fake workflows get new
paths. The original store, raw answers and old pins are unchanged.

Preparation now freezes a per-attempt harness copy, binds the required recorded
Core test data read-only, and records the actual selected-key environment. Set
`A7_APPROVED_KEY_DIR=/tmp/a7_logs_1781/life_native5/candidate_owed_002`,
`A7_TRACE_FIXTURE=/tmp/a7_logs_1781/attempt_grader_path7`, and
`A7_FIXTURE_PROJECTS=/tmp/a7_logs_1781/life_native5/TEST_projects` for current TEST
runs. Omitting the first was caught as a freeze mismatch in red2/red3, never
accepted by repinning. `--native --key-fixture --reuse path7` serves this lineage.

W3/R3 smallest source-binding repair is now applied after its four red cases:
the existing loader revalidates the producer and manifest, the descriptor carries
the manifest path, and context rendering rederives and compares the descriptor.
The earlier partial hash check was removed rather than kept as a second owner.
Next: run R3 green, then R4/R7, R5/R6, full/mutation reconciliation and Core review.
Nothing has been staged, committed or pushed; the overall grader remains unverified.

## W3 checkpoint (2026-09-09 15:53 UTC)

`input_green1`: all 20 accounting and source-binding tests passed, raw exit 0,
81.44 seconds. R3's changed path+hash, claimed manifest digest, and foreign
manifest now refuse at the single input owner; correct inputs and byte-identical
root aliases still render identical prompts. Cold and warmed source-run paths
both passed.

`publication_red`: ten R4 failures proved overwrite/interruption/race exposure;
both competing reference/sidecar writers reported successful publication. Two
R7 cases reached the real finalizer and raised IndexError on missing last-error
captures. One additional failure was a test assertion treating validity's list
as a dictionary; the public control itself had finalized successfully. That
test shape was corrected, not the validity owner.

R4 routes all six active artifact writers through the existing G._write_new ->
raw_transport.write_new owner, prompts first/candidate last. The two obsolete
check-then-rename implementations and their unused tempfile imports are removed
from this candidate, with original snapshots preserved. R7 only moves capture
length checking ahead of indexing; no catch-all or new interruption mechanism.

`publication_green1`: all 19 publication/interruption tests passed, raw exit 0,
36.40 seconds. Includes second-write byte preservation, partial builds that
cannot resume as complete, fresh-destination recovery, two independent writers,
and all seven error/capture shapes. Original saved producer/key evidence still
validates under these current owners. No successful model call was repeated.

Next W4: generic G3 placeholder and exact recall threshold, test first. W5 full
affected regression, mutation reconciliation and W6 independent Core review /
publication remain open. Do not publish based on these focused passes alone.

## W4 / W5 progress (2026-09-09 16:26 UTC)

R5 and R6 are repaired. `boundaries_red` reproduced four failures (an actual
answer shown as the G3 template, and rounded-display recall accepted at 98%).
`boundaries_green2`: 14 passed, raw exit 0, 1.29 seconds. Includes real no-write
route + current scorer: 440/449 displays 0.98 but fails the 98% union bar;
441/450 passes. A prior green attempt's remaining failure was a contradictory
test originals list, fixed in the test; the safety owner was right to refuse it.

W5 `lifecycle1`: all 79 current G2/G3 lifecycle tests passed, raw exit 0,
15.28 seconds. The fixture now reuses path7's source producer, builds current
TEST G1 pins once, derives its nonempty G23 once, and keeps every fake workflow
in the same copied canonical TEST store as key/producer lineage. Removed the
recovery-package pre-import workaround: the actual served bench/driver package
and approved validators hash are asserted in the test child. The mixed-question
completion test no longer silently skips a one-question batch; it explicitly
repacks two actual question ids only at the completion boundary. No model call.

`ordinary_full1`: 29 ordinary/historical modules, 1013 passed, 73 failed,
14 errors, 2 skipped; raw exit 1; 759.15 seconds. All 108 original missing-driver
dependency failures now pass. The remaining 87 IDs are saved exactly in the
attempt log. They remain open, not waived. This set intentionally excludes the
current native TEST modules, which run in their matching key/producer fixture.

Old artifact search recovered the exact retired launcher (0713ea41677bb1c...)
and matching old hard-review manifest (3666352de6f9217b...). The historical
test map serves those separately; the retired OD-1 owner is loaded by exact
file/hash only inside its four tests and cannot change active import paths.
Original evidence is unchanged. Two failed historical setup probes are retained:
one missing mountpoint under the overriding experiments row, one missing probe
output directory. Both are test setup errors, never claimed as passing evidence.
The corrected third probe is running; do not assume the old key derives until
its raw result proves that the paired package clears all remaining checks.

Fresh attempts now freeze the payload script as well as the harness, so later
test edits cannot change the code a recorded attempt names. Existing attempts
and failed outputs remain untouched. Current test fixture repairs in progress:
two frozen-input mutations moved to fresh TEST copies, old-era checks now pass
the required external pin, G1 pre-call proofs use the named current producer,
and the durable alias test derives its path from the actual map instead of 1792.

No staging, commit or push. W5 full reconciliation/mutations and W6 independent
review still required. Core remains paused. A7 is still UNMEASURED.

## W5 checkpoint (2026-09-09 17:12 UTC)

`boundaries_all1`: 93 passed, covering all seven meaning aspects × nine blind
true/false/null pairs, false beside unknown, full reliability thresholds and
real no-write route plus exact-count scoring. `current_full2`: 281 passed,
one stale refusal-result assertion failed (now corrected; native_focus4 passed).
`ordinary_full2`: 1015 passed, two failed, two historical skips. Its two failures
were the current source-approval refusal wording and a reversed pair of exact
historical generated-file hashes; corrected, not a loosened generation gate.

The complete 618-test general harness module now imports the CURRENT scorer,
not the producer-era frozen scorer. `scorer_full1`: 609 passed, nine failed.
Five old fake score dictionaries lacked the exact matched/gold counts; three
called a retired reliability argument; one was the same reversed hash pair.
Those tests now use current fields/API and the current rule: a union can rescue
low recall, never an unfinished required judgment. Production rules unchanged.

R2, R3, R4, R5, R6 and R7 removed-safeguard mutations all failed at their intended
behavioral assertions, not unrelated file-hash gates. R2_schedule initially
SURVIVED: the test kept the whole trace. The new dropped-trace-arm test passes
the correct implementation, and `mut_schedule2` fails at 102 != 204. Both
original success and missing-arm checks run before/after that mutation.
No mutation failure is counted as a passing qualification run.

`native_focus3` had a mistyped test id: no tests ran, raw exit 4; retained.
`native_focus4` used the exact collected id: both tests passed, raw exit 0.
`ordinary_focus3` exposed a test-order leak: the historical lock materializer
prepended its retired harness and the current scorer fixture loaded an old
grader. The source-correction test now restores sys.path after that historical
import. No production import/preload or pin bypass added. `ordinary_focus4`
will retest the exact stopped assertions before final suites.

Cleanup: removed the candidate's byte-identical duplicate recovery test file
and six obsolete saved-v1 positive functions. Their original bytes remain in
unit_1957; current equivalents are `test_a7_current_postrun` plus the real
invalid-primary/valid-retry trace test. Reconciliation must name each replaced
old id, not waive it. The old scorer file remains required by producer-era
hashes and shared identical pure helpers; only the bound current scorer owns
current grading. Do not delete pinned history or preserved real AI answers.

Next: finish the cold focused check, freeze one final candidate, run all current
harness modules and affected external tests, map all 198 original failed ids
and T01–T20 to exact proof, then Core's independent review and same-branch
publication. Nothing staged, committed or pushed. No AI calls. A7 UNMEASURED.

## W5 final evidence and owner-requested cleanup (2026-09-09 17:44 UTC)

The pre-cleanup complete runs finished: ordinary_final2 1017 passed / two
historical skips, native_final2 283 passed, identity_final1 274 passed. All
36 current harness modules are covered, with no failures. external_final1
passed all 3031 selected pure production-dependency tests; 53 live/database
tests were explicitly deselected, never counted as passes. Production bytes
and their tests have not changed since that external run.

path_final2 passed the actual cold no-AI lifecycle: 204/204 TEST producer
replies, complete G1, six G2 and six G3 lanes, correct INCONCLUSIVE final
decisions for deliberately unresolved extras. source_final1 revalidated the
exact saved real answer, counted all 35 missing source reviews, refused key
completion/repeated success, and passed the ten current synthetic source/key
lifecycle checks. T06 added exhaustive independent two-grader identity-relation
proof: 256 two-by-two relation pairs, permutations and sparse indices; removing
the contested-link protection fails 112 intended assertions. No AI calls.

Owner subsequently requested a final genericness and unused-code pass. Current
names derive from signed packet/fact rows; current counts derive from the run's
plan and approved key. Historical fixed counts and 36 source-span overrides are
preserved historical DATA, excluded from the current path (PLAN 7.2.6). A new
current-path test poisons those old tables and varies the declared population.

Caller search across current harness, lock owners, production/support code,
tracked code and the roadmap found five uncalled private current-scorer helpers:
_ev_key, _shape_pair, _base_driver, _resolved_period, _name_agrees. Removed only
those helpers, two orphan suffix constants and three orphan imports. Historical
scorers remain unchanged; current matching still has the single fact_match owner.
Every surviving scorer function is unchanged by this cleanup. Removed bytes
remain in the original snapshot and ordinary_final2's immutable view.

Final post-cleanup runs are ordinary_final3 and native_final4. native_final3
was accidentally launched with a mistyped expected validators hash; retain its
raw refusal/failure record, never repin code or count that run as qualification.
native_final4 uses the exact freshly measured, previously accepted hash.

Remaining: finish these post-cleanup regressions and cold path, reconcile every
one of the original 198 failed ids and T01–T20, freeze code/input/proof manifests,
independent Core review, then same-branch code-only commit/push. No new runtime
framework, semantic shortcut, later-step code, staging or publication so far.

## W5 complete; W6 independent-review checkpoint (2026-09-09 18:12 UTC)

Final post-cleanup results: ordinary_final3 1017 passed / two explicitly
historical skips; native_final4 558 passed / no skips or errors. All 36 current
harness modules are covered. external_final1's unchanged 3031 passing pure
dependency tests remain applicable; 53 live/database tests were excluded.
Combined software checks: 4606 passes, not measured AI accuracy.

path_final3 passed the cold no-AI generated-launcher path on the final code:
204/204 TEST replies, complete G1, six G2 and six G3 lanes, correct INCONCLUSIVE
decisions for deliberately unresolved extras. proposed3 proved all 98 proposed
code/assets and 55 loaded project modules in a clean export, including the
nonempty real no-write route. source_final1 and the unchanged signA/B/C proof
remain valid. The one saved real answer is preserved; 35 source events remain
missing and no AI call was made.

RECONCILIATION.json resolves all 198 original failures: 191 exact IDs now pass;
seven obsolete IDs were removed from the current suite and have named passing
current replacements. Removed bytes remain in frozen historical snapshots.
All safeguard mutations and their positive controls are recorded. The final
genericness/duplication check requires no further application changes.

FINAL_REVIEW.md is the review entry point. CODE_FILES.json freezes the current
code; EVIDENCE_MANIFEST.tsv freezes compact raw evidence, maps and payloads;
EXTERNAL_EVIDENCE.json identifies the separately preserved full generated
artifacts; PUBLICATION_MANIFEST.tsv is the exact proposed code-only selection.
Do not stage whole attempt/export directories or publish unfinished semantic
results. Core's independent review and the exact staged-identity/normal-push
checks remain. Nothing staged, committed or pushed at this checkpoint.

## Owner final five-item pass (2026-09-09 18:34 UTC)

The owner's explicit follow-up reopened the final scoped check before sending
anything to Core. No message 1960 has been sent. The earlier prospective
publication manifest is superseded, not approved. CODE_FILES.before_owner_final.json
preserves its exact prior 98-file code list; all prior attempts remain intact.

The live-name/ownership pass found that B.extras_buckets still read the frozen
producer scorer, whereas current verdicts read the bound current scorer. R8
switches that accessor to the same current owner; the legal three answers and
rendered rules are unchanged. final_owner_red fails on the retired dependency;
final_owner_green passes all 94 score-boundary tests. mut_owner restores that
dependency in-process and fails the exact intended assertion.

Removed three uncalled private helpers, six unused constants, five unused
imports and an unused completion tally. The saved function comparison is
FINAL_OWNER_CHANGES.json. Public entry points and frozen historical code stay;
no wrapper, configuration layer, speculative behavior or production change.

The cold proof now asserts exact INCONCLUSIVE decisions and exact matched/gold
counts, instead of accepting any non-PASS result. path_final4 was prepared but
NEVER LAUNCHED after this assertion improvement; path_final5 is the executed
final proof and passes. source_final2 revalidates the unchanged real answer,
counts all 35 missing events, forbids repeating the success and passes all ten
source/key lifecycle checks. proposed4 passes clean-export execution.

native_final5: 559 passed, no errors/skips, 195.92 seconds, exit 0. The final
ordinary_final4 regression is still running; do not substitute older counts
for its actual result. The five-item checklist is maintained in FINAL_REVIEW.md.
No AI call, staging, commit, push or Core launch/stop occurred.

## Final local checklist complete (2026-09-09 18:46 UTC)

ordinary_final4 finished at exit 0: 1017 passed, two explained historical
skips, 751.27 seconds. Together with native_final5, every one of the 36 current
modules is covered: 1576 passes / two skips. The unchanged external_final1
adds 3031 passes; 53 live/database cases remain explicitly outside this
no-write check. No current failure or unexplained original failure remains.

Final snapshots match all 98 CODE_FILES rows; the original harness, saved real
raw answer and production pins remain unchanged. FINAL_TEST_CASES and
RECONCILIATION now name these exact final runs. The five-item checklist is
complete locally. Independent review and exact same-branch publication are
still pending; A7's actual AI qualification remains UNMEASURED.
