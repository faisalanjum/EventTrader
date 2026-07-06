# 90 · Open items (what's not yet decided or not yet built)

**What this is:** the owner's open-decisions DASHBOARD — every open thread, one line each, pointing at its home. This file stays thin on purpose: definitions, evidence, and recommendations live at the pointers, never here, so nothing can drift. **The full validated issue census + recommended resolutions = `66_IssuesToBeHandled.md` §0 (2026-07-05) · the pre-coding readiness work order = `14_BuildReadiness.md`.**

Split: **A** = design *decisions* still needing an owner call · **B** = design done, *code/wiring* not built · **C** = parked/deferred · **D** = design *sections* still to write · **E** = resolved (the record).

---

## A. Open DESIGN decisions (need an owner call)
| ID | Question (one line) | Lean / home |
|---|---|---|
| **FS-23** | Cross-company slice-VALUE comparison ("International" at A = "International" at B?) — a separate, unbuilt layer | deferred; conservative bar · `03` FS-23 |
| **UNIT-12** | Add `percent_qoq` to the 9-unit enum? | lean **no** — sequential-% counter first: `66` §0.R OD-11 |
| 8-K taxonomy | Reuse the 24-tag 8-K event taxonomy for Driver extraction? | open · part-2 input (`99` §4.7) |
| Amendments | How amended/corrected filings affect old facts and states | open · part-2 input; interacts with `66` §0.R OD-14 |
| **Model policy** | Final model per job · # runs · process | leading default only ("Opus reads + Sonnet classifies", 95 #15); experiments per `10` §7 PIPE-30/32 |
| G1 reuse-display rules | Blocks the live propose-first display + `catalog_first.js` rebuild — NOT the fitness gate | `10` §13 |
| K2 fold-repair profile gate | Batched repair on folds stays per-pair until decided | `10` §13 |
| Target N | 796 vs 786 tickers (unreconciled) | `10` §13 |
| Lifecycle / dormancy / IPO absorption | default lean: live G1/G2 absorbs | `10` §13 |
| **66 §0.R sign-off queue** | 9 pinned design recommendations + 3 paste-ready 95 rows (#26/#27/#28) awaiting one owner pass | `66` §0.R closing |

## B. Design done — BUILD/WIRING not done
| ID | What | Home |
|---|---|---|
| **UNIT-14** | Shared unit resolver proven in scratch (117/117), **not wired** into a producer | `04` · `12` §6 |
| **PER-20** | Extract `driver_period_resolver.py` · pass the 21 tests · prove YTD/TTM math · write-once hardening | `05` · `12` §5 |
| **XC-16** | Calc-hierarchy veto replaces the hand 4-entry deny set — recommended **before** the full-universe run | `08` · `12` §8 |
| Concept-link full run | Validated on 274/795 companies (~35%); full-universe run pending | `08` XC-13/15 |
| Catalog→graph sync | `catalog_graph_sync.py` — spec pinned, Track-B ownership recommended | `66` §0.R OD-16 |
| Guidance field-map / member reconciliation | re-homed: old guidance = archive/QA evidence (Track C v2.0); fresh mapping = Track B / part 2 | `13` §5 |

## C. Parked / deferred (out of scope for now)
- **Macro/news attribution details** — core DCM shape **LOCKED** (`dcm:<cik>:<trade_date>` · FOR_COMPANY/ON_DATE · returns read from `HAS_PRICE`; single-target-on-filing-days ✅ `12` §10.9). Still parked: the significance **threshold** · the **pure-macro source** (+ the `09` §4 pure-macro FROM_SOURCE carve-out that ships with it) · the two-independent-same-day-catalysts residual.
- **§10 dormant XBRL-link rider** — activates only with the Codex §4.8 write-path decision (`09` §10).
- **Blanket-withdrawal fan-out** — owner sign-off noted (`09` §7); final production rule lands with part 2.

## D. Design SECTIONS still to write
See `14_BuildReadiness.md` for the full pre-coding work order (running layer §2 · exact-rule fixes §3 · cross-doc cleanup §6).
- **Actual update / live-backfill process (part 2)** — incl. fresh `fact_type=guidance` production from source documents + the 894-source historical backfill.
- **Incremental refresh** — seam notes in `10` §13; design substrate `WIP/IncrementalRefresh_FinalDesign.md`.
- **Scanner / change-flag layer** — contract pinned in `66` §0.R OD-5; the component itself = part 2. *(row added 2026-07-05 — closes ISS-8's missing-row half)*
- **Overview finish** — the 3-tracks map · authority/reading map · status dashboard (`01`'s WIP note).

## E. RESOLVED (the record — one line each; detail lives at the pointer)
- **EXPLAINED_BY verdict layer** (DU-21…24 · explained_target key · edge evhash16 kept · DCM own label · trade_date owned by the returns layer) → **LOCKED** owner 2026-07-03 · `12` §10.1; `07` upgraded.
- **09 §8 amendment bundle** (self-describing shapes + transient hints · `value_text` · fact `evhash16` retired) → **APPROVED** 2026-07-03 · `09` §8 · 95 #16–18.
- **FS-14 slice-menu PIT** → **RESOLVED** 2026-07-02: PIT for DriverUpdate write-time, 3-context split · `03` FS-14.
- **ISS-16 routing** (expectation comparison → metric + surprise, state derived from stated numbers, in_line materialized; OBJ-1/2/3 folded; `previous_guidance` also metric-FORBID) → **LOCKED** 2026-07-03 · `12` §10.5 · 95 #24.
- **Track A build pipeline** → **WRITTEN** 2026-07-02: `10_BuildPipeline.md` (committed 281fd63).
- **Track C** → **archive/retire old guidance, NO production replay** (owner 2026-07-04, v2.0) · `13_TrackC_GuidanceIntegration.md`; the guidance node-label question closed the same way (fresh `fact_type=guidance` DriverUpdates; old `GuidanceUpdate` archived).
- **company_confirmed** → guidance-only **boolean** (owner 2026-07-01) · MF-11 + `09`.
- **FactScope identity package** (the old "Q1–Q4+E") → resolved into `Naming_Slices_XBRL.md`; the PENDING file was deleted — don't reopen.
- **`_guidance`/`_surprise` suffix vs `fact_type` "redundant?"** → keep both (NAME-17 / MF-09).
- **Macro/news core shape** → **LOCKED** (DCM · CIK-based id · returns from `HAS_PRICE`) — open *details* in §C.
