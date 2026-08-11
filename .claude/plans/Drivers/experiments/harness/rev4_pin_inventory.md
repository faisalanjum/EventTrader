# Rev-4 pin inventory v9 — DERIVED from the INDEX (the commit itself); each pin RECOMPUTED; each occurrence classified by a STRUCTURAL marker; actions owned by Part F

Do not edit by hand: run `make_pin_inventory.py` and commit the result.

Hash method: **sha256(file bytes), first 8 hex**. An unlabelled digest is a pin nobody else can reproduce, so the method is stated rather than implied.

v4 addressed pins by `file:LINE`. A line number is not durable — one inserted sentence invalidated 73 of 76 rows while every hash stayed correct. Rows are keyed by the nearest enclosing heading, which moves only when the section is genuinely renamed. The inventory never lists itself or its generator.

v5 only LOCATED the hash text, which proves a pin is present and says nothing about whether it still describes its artifact. v6 recomputed, but called every difference STALE — which mislabels a dated record as a defect. **v7 separates the two:** a pin is recomputed ONCE, and each PLACE it is written is classified from its own line as a **current claim** or a **dated record**. Only a current claim can be WRONG. A record row states what was true on its date and is never corrected; a correction is APPENDED beside it.

**This inventory takes no action and owns none.** What should be DONE about a pin lives in `exp5_rev4_package.md` -> **PART F — GOVERNING-DOCUMENT CHANGES**, which is its sole owner. v8 dropped that relationship silently, and an inventory that hints at actions beside an owner that decides them is two authorities on one question. Rows below say what each pin IS and where it is written; read Part F for what happens next.

## Each pin, recomputed (sha256(file bytes), first 8 hex)

| pin | names | artifact | recomputed | agreement |
|---|---|---|---|---|
| `86b2fc17` | packet pre-amendment | `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/15_CandidateFactPacket.pre-amendment.md` | `86b2fc17` | **AGREES** |
| `aa7239ed` | packet v1.0 | `.claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md` | `aa7239ed` | **AGREES** |
| `d91443f8` | WorkOrder v2.0 | `.claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md` | `e224cf14` | **DIFFERS** |

## Where each pin is written, and what that place CLAIMS

| file | kind | semantic anchor (nearest heading) | pin | claims | n |
|---|---|---|---|---|---|
| `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md` | record | 11. Missing recipes (open build gaps — no new design authority here) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md` | record | 2. The internal core packet (frozen Candidate Fact Packet v1.0) | 86b2fc17 (packet pre-amendment) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md` | record | 2. The internal core packet (frozen Candidate Fact Packet v1.0) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md` | record | 4. Owner rulings record (through 2026-07-18) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md` | record | 7. Source crosswalk (33 files → destinations; every row re-verified at Phase 4/5) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md` | record | 8. Archive manifest + evidence pointers | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md` | record | STATUS_AND_HISTORY.md — the one mutable dashboard, supersession ledger, and crosswalk | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/CONSOLIDATION.md` | archived history | 16. Re-verification record | 86b2fc17 (packet pre-amendment) | dated record | 3 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/CONSOLIDATION.md` | archived history | 16. Re-verification record | aa7239ed (packet v1.0) | dated record | 13 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/CONSOLIDATION.md` | archived history | 5.2 Internal core packet (frozen Candidate Fact Packet v1.0) | 86b2fc17 (packet pre-amendment) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/CONSOLIDATION.md` | archived history | 5.2 Internal core packet (frozen Candidate Fact Packet v1.0) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/MANIFEST.json` | archived history | key "sha256" | 86b2fc17 (packet pre-amendment) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-15_official-run-10.md` | archived history | Tested file hashes (SHA-256, full) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-15_official-run-10.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run10.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run10.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run11.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run11.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run12.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run12.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run13.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run13.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run14.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run14.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run15.md` | archived history | 2.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; re-verified AFTER) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run15.md` | archived history | 6. The reader's ten answers — VERBATIM (spliced byte-identically from the workflow output JSON by script) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run2.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run2.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run3.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run4.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run5.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run6.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run6.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run7.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run7.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run8.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run8.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run9.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set; the post-Phase-5 live-file authority) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run9.md` | archived history | The reader's full answers (verbatim) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final.md` | archived history | Tested file hashes (SHA-256, full — the seven-file set) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-17_R8-recheck-R11.md` | archived history | 1.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; `sha256sum -c` AFTER → 7/7 OK) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-17_R8-recheck-R11.md` | archived history | 3. The reader's ten answers — VERBATIM (spliced from the subagent's final output) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-17_R8-recheck-R11.md` | archived history | 4. Per-question grades (locked rule + full checklist applied) — PASS 10/10 | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-17_R8-recheck-R12.md` | archived history | 1.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; `sha256sum -c` AFTER → 7/7 OK) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21-run2.md` | archived history | 1.1 The seven pinned hashes (pinned BEFORE the reader; `sha256sum -c` re-verified before the retry | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21-run2.md` | archived history | 3. Grades (locked rule — most-natural parse, no rescue readings — + the full checklist) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21.md` | archived history | 1.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; `sha256sum -c` AFTER → 7/7 OK) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | 1. WHO I AM, AND THE BOUNDARY WITH FISCAL | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | 8. HOLDS — none may be lifted without the owner's explicit word | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Core — #826 REWORK EXECUTED: the commit is PROVEN (2026-07-30) | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Core — #826 round 3: the CLEAN-LANE rework. All 7 blockers repaired (2026-07-30) | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Held, unchanged | d91443f8 (WorkOrder v2.0) | dated record | 2 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Holds — ALL still standing, none touched | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Holds, ALL unchanged | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Holds, unchanged | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Owner answers received | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Receipts | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Repository state at the time of writing this record | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | TWO THINGS WAITING ON THE OWNER — do not decide these alone | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | The owner's two corrections, applied | d91443f8 (WorkOrder v2.0) | dated record | 2 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | The six open defects, restated | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Two genuine findings for the OWNER | d91443f8 (WorkOrder v2.0) | dated record | 2 |
| `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md` | record | Untouched, non-negotiable | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` | record | 2026-07-24 — Work order v1.8 → v1.9 (Fable, owner instructions); K-fields GO #1 OPEN | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` | record | 2026-07-24 — Work order v1.8 → v1.9 (Fable, owner instructions); K-fields GO #1 OPEN | d91443f8 (WorkOrder v2.0) | dated record | 2 |
| `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` | record | WORKORDER_STATUS - FableExperimentWorkOrder v2.0 execution board | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `.claude/plans/Drivers/experiments/harness/exp5_rev4_package.md` | package | PART F — GOVERNING-DOCUMENT CHANGES (literal; carried by the companion | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/experiments/harness/rev3_build.py` | build script | (module level) | aa7239ed (packet v1.0) | dated record | 1 |
| `.claude/plans/Drivers/experiments/harness/rev4_extra.py` | build script | (module level) | 86b2fc17 (packet pre-amendment) | dated record | 2 |
| `.claude/plans/Drivers/experiments/harness/rev4_extra.py` | build script | (module level) | aa7239ed (packet v1.0) | dated record | 2 |
| `.claude/plans/Drivers/experiments/harness/test_g_suite.py` | test | (module level) | d91443f8 (WorkOrder v2.0) | dated record | 4 |
| `.claude/plans/Drivers/experiments/harness/test_g_suite.py` | test | function test_a_QUOTED_current_claim_inside_a_code_fence_claims_nothing | d91443f8 (WorkOrder v2.0) | dated record | 1 |
| `driver/core/driver_period_resolver.py` | production | (module level) | aa7239ed (packet v1.0) | dated record | 1 |
| `driver/core/prepared_fact.py` | production | (module level) | aa7239ed (packet v1.0) | dated record | 1 |
| `driver/core/test_driver_period_resolver.py` | test | (module level) | aa7239ed (packet v1.0) | dated record | 1 |
| `driver/core/test_prepared_fact.py` | test | (module level) | aa7239ed (packet v1.0) | dated record | 1 |
| `driver/relocation/inline_html.py` | production | function _has_number_fact | aa7239ed (packet v1.0) | dated record | 1 |

| | |
|---|---|
| **CURRENT claims whose pin no longer describes its artifact** | **0** |
| dated record occurrences (stand as written, never corrected) | 107 |
| rows | 77 |
| distinct files | 35 |
| total occurrences | 107 |
