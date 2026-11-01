# Start here — A7 manual recovery, owner review checkpoint

The current four-example checkpoint is finished. The wider A7 failure investigation is not finished. **STOP before T036 and wait for the owner's next instruction.** This file is the single entry point for a new session; the linked evidence remains in the two existing worktrees. It is not a standalone backup or a new rule document.

## What is different from the earlier Step 1 failures?

The original A7 results remain preserved: 191 source targets / 382 saved replies. That full test was not rerun or relabelled as passing. This later investigation manually inspected the complete inputs and public answers, tested separate naming and field tasks, and checked the assembled records through the existing code with writes disabled. Earlier failed attempts remain evidence, not current results.

The accumulated work has three parts; these are not three independently proved causes of every historical failure:

| Part | What changed and what was demonstrated | Current status |
|---|---|---|
| Extraction workflow | Faithful source/context review, then Sonnet names the fact and Luna fills the remaining fields. Three fresh Darden pairs got the financial facts and shortest `millions` span right; their original downstream failures exposed the separate date problem below. | Working local experiment. Splitting the task is not proved to be the unique historical naming cause. |
| Generic instructions | Earlier work clarified field duties, signed amounts and when a change is redundant. The latest addition is eight generic lines: retain a factor that defines what the quoted amount measures; exclude a factor that merely helps explain an overall total. Fuel now retains the price association in its name. | Latest fuel test passed 3/3; tax and two controls also passed. No example-specific rule or financial-text rewrite was added. Not adopted into the original full harness or production prompts. |
| Shared date code | Exact SEC fiscal dates take priority over an old stored window. A duration with one endpoint may be completed only from matching exact fiscal evidence or explicit calendar framing; conflicting/unproved completion is rejected. Darden FY2026 Q3 resolves to 2025-11-24–2026-02-22 instead of the old 2025-12-01–2026-02-28. | Committed and pushed earlier as `ac4cf6f28b5a1767610f859160a3623137365606`. All three saved pilot pairs then passed the write-disabled route. Broader company-calendar accuracy still needs review. |

The date commit changes exactly three files: `driver/core/driver_period_resolver.py`, its tests, and the review reminder in `FINAL_DESIGN.md`. Its recorded validation includes unresolved pre-existing suite failures; do not describe the whole repository as green. The [original three-run report](NAMING_FRESH_CHAIN_20260923/ROOT_REPORT.md) deliberately retains the failures observed **before** that fix.

## Latest independently reviewed result

| Example | Fresh complete records | Result |
|---|---:|---|
| Fuel T003 | 3 | PASS, including three independent readers of the assembled records |
| Tax T008 | 1 | PASS |
| Darden T049, original pilot | 1 | PASS |
| Best Buy T113, comparison control | 1 | PASS |

These are four source targets, six assembled records and 15 model calls: six naming calls, six field calls and three fuel readers. Three earlier investigation calls are separate. No silent retries or answer repairs. Model settings and exact actual inputs are preserved in the evidence. No database or calendar-cache writes occurred. This tests extraction and the existing write-disabled route, not full production identity admission or deduplication.

Fuel means an expense **increase strictly greater than $4B**, associated with higher jet-fuel prices, for FY2026. It is not the total fuel bill or a proved price-only allocation. Tax expense −94 versus −175 increased. Darden's $24.7M impairment is the direct charge; an extra before-tax measurement token is permitted but unnecessary under the existing meaning ruling. Do not reopen that settled review by treating an older answer as a mandatory key. Different lawful names/optional tokens still leave identity stability unproved.

The observed fuel failure was applying the naming rule to the wrong interpretation of the amount. The revised generic definition corrected the public diagnostic and all three subsequent complete tests. This supports that mechanism; it does not establish one exclusive cause for all old failures or guarantee unseen reliability.

## Evidence and exact locations

- [Final four-example report and evidence index](NEXT10_STAGED_20260923/ROOT_FOUR_CASE_CHECKPOINT_2430.md), SHA256 `42ef1b8cf536c333d344e2dc6532d253422a6d26082b1988e415ae6573cc3ee5`.
- [Frozen actual-input/result/code snapshot](/home/faisal/EventMarketDB-driver-recovery/a7_recovery/manual_failure_pilot_20260917/t003_attribution_scope_2420/RUN/FINAL_SNAPSHOT_2430.json), SHA256 `4ba8badad605a17e8e82d52b6e492b1e5838f0cf39bef198b553d85f0c3085ef`.
- [Independent snapshot verification](NEXT10_STAGED_20260923/ROOT_FINAL_SNAPSHOT_REVIEW_2430.json): 11 experiment manifests, 234 unique files. [Exact input comparisons](NEXT10_STAGED_20260923/ROOT_FOUR_CASE_INPUT_DIFF_2430.json): removing the eight new lines restores all four cases' earlier naming and field templates byte for byte, including financial source text.
- [Current failed-example tracker](/home/faisal/EventMarketDB-driver-recovery/a7_recovery/manual_failure_pilot_20260917/next10_staged_20260923/TRACKER.md) and its sibling `ATTEMPT_LEDGER.jsonl`; [independent tracker closure review](NEXT10_STAGED_20260923/ROOT_TRACKER_CLOSURE_REVIEW_2431.json).
- [Short continuing mental map](MENTAL_MAP.md), with understanding scores, settled meanings, open limits and protocol state. Re-read it every few turns; use primary design documents for rules.

The latest experiment is `a7_recovery/manual_failure_pilot_20260917/t003_attribution_scope_2420/` in `/home/faisal/EventMarketDB-driver-recovery`. Its builder has seven added wiring lines and reuses the earlier runner. It depends on sibling `t003_cause_scope_2416/cand_2419/CORE_ATTRIBUTION_SCOPE_2419.json`, the earlier `next10_staged_20260923/GENERIC_FIELDS_CONTROLS_2402` runner, and the tax base `CHANGE_ELIGIBILITY_FIELDS_2400`. Copying only the latest folder is not a verified reproducible package.

## What remains, and publication advice

Fuel and tax are two of the selected ten failed examples. Eight remain untouched: T036, T045, T050, T062, T067, T107, T142, T145. Darden and Best Buy are controls. The full original suite, unseen-case qualification, real identity admission, canonical-name stability and broader fiscal-calendar review remain open. The frozen naming input's item-first layout also needs resolution against the reader's item-last requirement before formal adoption. Neither 33 lexical candidates nor 15 manually reviewed naming boundaries means that many completed fixes.

Verified Git state when this handover was prepared: recovery branch `recovery/a3-a7-verified` and its actual remote both point to date-fix commit `ac4cf6f28b5a1767610f859160a3623137365606`. The newer experiment, tracker and Root review notes are untracked; they are not included in that push. Main also has unrelated local changes. Root notes live in main's workspace, while experiment artifacts live in the recovery worktree.

Recommendation: preserve this new work as a **separate, explicitly scoped checkpoint commit on the recovery branch**, including the handover, reviewed scripts, required dependencies and reviewable evidence. Keep old A7 results intact. First inventory the package and inspect session artifacts for private account data; do not bulk-stage either workspace. A push would preserve the experiment, not approve production adoption or claim the full test passed. This handover task performed no staging, commit, push or new experiment.

## Session continuity

Before coordinating, read `/home/faisal/EventMarketDB/AGENTS.md` and `FinalDesign/LeftOverSteps/Orchestration.md` and follow their startup steps. Core implements; Codex independently reviews. Use the owner's actual current session choices and runtime IDs, never copy a predecessor's ID as your own. The last bound pair was Codex `01a0b16d-134d-7683-b4bd-d01fea471cc5` / Core `b42117d6-33cb-47b0-81d9-c330b8263417`. Codex2431 was answered by Core2428 with final WAIT; no further acknowledgement or task was needed. Reuse existing watchers and preserve the broader unfinished goal. A separate owner request concerning Core's project-wide stop hook is not part of extraction completion; do not change or recreate hooks during handover.

**The next session begins at owner review, not at example T036.**
