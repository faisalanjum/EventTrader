# 90 · Tracked items (not all are blockers)

**What this is:** the owner's tracked-items dashboard — every visible thread, bucketed by when to handle it. This file stays thin on purpose: definitions, evidence, and recommendations live at the pointers, never here, so nothing can drift. **The full validated issue census + recommended resolutions = `66_IssuesToBeHandled.md` §0 (2026-07-05) · the pre-coding readiness work order = `14_BuildReadiness.md`.**

Split: **A** = final Driver Catalog/live-admission pass · **B** = build/wiring/config · **C** = deferred or separate layer · **D** = downstream/part-2 sections · **E** = resolved (the record).

---

## A. Final Driver Catalog / live-admission pass before implementation
| ID | Question (one line) | Current bucket / home |
|---|---|---|
| G1 reuse-display rules | Blocks the live propose-first display + `catalog_first.js` rebuild — NOT the fitness gate | `10` §13 |
| Target N | 796 vs 786 tickers (unreconciled) | `10` §13 |
| Lifecycle / dormancy / IPO absorption | default lean: live G1/G2 absorbs | `10` §13 |
| **OD-7** | Live-created Driver wrong name/type escape path after facts exist | final live-create safety pass with G1 · `66` §0.R OD-7 |

## B. Build / wiring / execution config
| ID | What | Home |
|---|---|---|
| **Model policy** | Final model per job · number of runs · fallback · grading setup | leading default only ("Opus reads + Sonnet classifies", 95 #15); experiments per `10` §7 PIPE-30/32 |
| **UNIT-14** | Shared unit resolver proven in scratch (117/117), **not wired** into a producer | `04` · `12` §6 |
| **PER-20** | Extract `driver_period_resolver.py` · pass the 21 tests · prove YTD/TTM math · write-once hardening | `05` · `12` §5 |
| **XC-16** | Calc-hierarchy veto replaces the hand 4-entry deny set — recommended **before** the full-universe run | `08` · `12` §8 |
| Concept-link full run | Validated on 274/795 companies (~35%); full-universe run pending | `08` XC-13/15 |
| Catalog→graph sync | `catalog_graph_sync.py` — spec pinned, Track-B ownership recommended | `66` §0.R OD-16 |
| Guidance field-map / member reconciliation | re-homed: old guidance = archive/QA evidence (Track C v2.0); fresh mapping = Track B / part 2 | `13` §5 |

## C. Deferred / separate layers (not current Driver/DriverUpdate blockers)
- **FS-23** — cross-company slice-VALUE comparison ("International" at A = "International" at B?) is a separate, unbuilt comparison layer; stay conservative · `03` FS-23.
- **8-K taxonomy** — whether to reuse the old 24-tag 8-K event taxonomy for Driver extraction; low-urgency part-2 input (`99` §4.7).
- **Macro/news attribution details** — core DCM shape **LOCKED** (`dcm:<cik>:<trade_date>` · FOR_COMPANY/ON_DATE · returns read from `HAS_PRICE`; single-target-on-filing-days ✅ `12` §10.9). Still parked: the significance **threshold** · the **pure-macro source** (+ the `09` §4 pure-macro FROM_SOURCE carve-out that ships with it) · the two-independent-same-day-catalysts residual.
- **§10 dormant XBRL-link rider** — activates only with the Codex §4.8 write-path decision (`09` §10).

## D. Downstream / part-2 sections still to write
See `14_BuildReadiness.md` for the full pre-coding work order (running layer §2 · exact-rule fixes §3 · cross-doc cleanup §6).
- **Actual update / live-backfill process (part 2)** — incl. fresh `fact_type=guidance` production from source documents + the 894-source historical backfill.
- **Incremental refresh** — seam notes in `10` §13; design substrate `WIP/IncrementalRefresh_FinalDesign.md`.
- **Scanner / change-flag layer** — contract pinned in `66` §0.R OD-5; the component itself = part 2. *(row added 2026-07-05 — closes ISS-8's missing-row half)*
- **Overview finish** — the 3-tracks map · authority/reading map · status dashboard (`01`'s WIP note).

## E. RESOLVED (the record — one line each; detail lives at the pointer)
- **EXPLAINED_BY verdict layer** (DU-21…24 · explained_target key · edge evhash16 kept · DCM own label · trade_date owned by the returns layer) → **LOCKED** owner 2026-07-03 · `12` §10.1; `07` upgraded.
- **09 §8 amendment bundle** (self-describing shapes + transient hints · `value_text` · fact `evhash16` retired) → **APPROVED** 2026-07-03 · `09` §8 · 95 #16–18.
- **FS-14 slice-menu PIT** → **RESOLVED** 2026-07-02: PIT for DriverUpdate write-time, 3-context split · `03` FS-14.
- **ISS-16 routing** (expectation comparison → metric + surprise, `in_line` materialized; OBJ-1/2 folded; `previous_guidance` also metric-FORBID) → **LOCKED** 2026-07-03 · `12` §10.5 · 95 #24. *(surprise-STATE derivation amended by OD-13, 2026-07-06 — next line.)*
- **OD-13 lower-is-better surprise arithmetic** (favorability = producer MEANING judgment; code computes only polarity-free position + `in_line`; wordless-outside-range → transient discarded polarity proof, else `unknown`; proof allowed only when the chosen favorable direction has no common mainstream counter-story; amends ISS-16's `>high→beat` derivation + drops beat/missed from DU-16.2's sign rule; `change_value` stated-only + null-if-sign-ambiguous; report-only mixed-polarity monitor, no human) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-13; back-port → `12` §10.5 · `07` DU-16.2 · `14` §3 #7 · 95 #31.
- **OD-12 negative/loss sign convention** (SIGNED value-space on the driver's numeric AXIS, not good/bad; value-first — "loss up to $X" → floor, the mirror of "revenue up to $X" → ceiling; a charge amount positive, a benefit/reversal negative; zero-crossing ranges store both signed endpoints; comparatives polarity-read; numberless → no bounds; conditionals → narrative; co-bounds → existing fusion; naming pin: no loss-magnitude drivers; report-only history-based sign monitor, never keyword/primary; no new field/list/human) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-12; back-port → `09` §3 · `07` DU-14 · `02` (naming pin) · `14` §3 #6 · 95 #32.
- **OD-11 %-guide basis routing** (read the growth basis from the source, not a hard-stamp; **ADD `percent_sequential`** — period-agnostic, own series family, mirrors `percent_yoy`, resolves UNIT-12; metric-type gate first — static-% level bare "up X%" → `unknown`; sequential → `percent_sequential`, yoy/comparable/annual/bare-dated → `percent_yoy`, sentinel → `unknown`; measurement adjustments cc/organic/adjusted go in the MEASUREMENT slot and never decide the basis; annual: sequential==yoy → `percent_yoy`; growth never → plain percent; multi-basis → split; no new field/list/human) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-11; back-port → `09` §7 · `04` UNIT-01/12 · `07` DU-17 · `11` T8/T11 · `12` constants/deferred list · `14` §3 #5 · 95 #33.
- **OD-14 chronological writes / amendments** (order by public source time; guidance movement READ-DERIVED — bare→`driver_state=unknown`, read layer derives `effective_driver_state` from the prior COLLAPSED value in the canonical guidance series, never written back, validator skips `unknown`; correction events/wording are excluded; withdrawal fan-out stays WRITTEN but strictly bounded — clear withdrawal + exact resolved-scope, OPEN guides only, replace/reaffirm excluded, **add-only** for late covered guides, never delete; amendments = new facts at amendment time; Event/DCM resolved at READ on trade date, no stored flag; no repair queue/mutation/human) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-14; back-port → `11` T11.6/T11.7 · `12` §10.9 + validator scope · `09` driver_state + §6.9 · `14` §3 #8 · 95 #34.
- **OD-9 measurement tokenization** (open-vocab, source-grounded, NEVER-DROP sink; producer copies exact source spans → transient `measurement_raw_spans`, code alone normalizes: lowercase → each non-alphanumeric run → `_` → trim → collapse; MAXIMAL contiguous spans → one token ("adjusted diluted" → `adjusted_diluted`), separate only for non-contiguous spans; measurement = fail-closed bucket for any number-modifier not losslessly captured by driver/period/unit/slice/OD-11-unit — natural-home routing — a time-window like TTM's home is the PERIOD slot (routed there if the resolver builds the exact rolling-12M window ≠ FY, else kept as `measurement=ttm` never-drop fallback); a qualifier leaves measurement only on lossless capture elsewhere; unsure → keep, never drop; boundary: version-of-same-quantity → measurement, different quantity → driver name; NO write-time synonym merge/closed-list/human/aliasing — equivalent-label grouping is read-time only, never changes stored ids) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-9; back-port → `03` FS-25 · `09` §3 · `11` T3.5 · `12` FACT-17b · `14` §3 #3 · 95 #35 · cross-ref PER.
- **OD-10 unit-family grouping → `series_unit`** (decide the series axis at WRITE, group by plain equality at READ; add a code-written `series_unit` grouping tag — read = `GROUP BY … series_unit …`, NO read-time family map, NO unknown-absorption; level fact → the level's canonical axis, money canonicalized to the driver's ONE scale within a currency; delta-only → fold onto the driver's dimension axis ONLY when the fact's own EVIDENCE makes it uniquely clear (metric nature + quote, NEVER the name), else fail closed to exact `change_unit`/`unknown`; three danger pins — unstated growth-frame fails closed, evidence-not-name, hidden cc/GAAP measurement axes count as dimensions (+ cold-start); withdrawal copies exactly ONE clear prior's `series_unit`; numberless → null; `series_unit` is a GROUPING tag — `change_value`/`change_unit`/`level_*` stay SOURCE-FAITHFUL; over-merge structurally impossible, over-split the only failure mode) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-10; back-port → `09` §6.1 · `11` T12.6/T12.1 · `12` FACT-33 · `14` §3 #4 · 95 #36.
- **OD-15 concurrent live Driver creation** (exact duplicate Driver names already converge by `Driver.name` uniqueness + `MERGE`; near-synonym live names are accepted over-splits handled by normal SAME_AS repair/fold; no new lock/queue/serialization layer/special repair path) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-15; back-port → `14` §3 #9.
- **OD-3 name-vs-slice blind-reader rule** (reader uses only quote + source company; own measured part → slice; external/unclear cause → Driver name; customer slice only for the reporting company's own business with that customer; no vendor slice kind; no cross-company/world-knowledge test; no new field/list/human/read-time logic) → **APPROVED** owner 2026-07-06 · `66` §0.R OD-3; back-port → `02` NAME-10/11/16 · `10` PIPE-17/19/20 · 95 #38.
- **K2 fold-repair profile gate** (leaf repair may use the approved batched lane; fold repair stays slow per-pair for safety. Batched fold repair is deferred to a future optimization experiment/gate, not an open design blocker) → **APPROVED** owner 2026-07-06 · `10` §2/§11/§13 · `66` §0.R K2.
- **Track A build pipeline** → **WRITTEN** 2026-07-02: `10_BuildPipeline.md` (committed 281fd63).
- **Track C** → **archive/retire old guidance, NO production replay** (owner 2026-07-04, v2.0) · `13_TrackC_GuidanceIntegration.md`; the guidance node-label question closed the same way (fresh `fact_type=guidance` DriverUpdates; old `GuidanceUpdate` archived).
- **company_confirmed** → guidance-only **boolean** (owner 2026-07-01) · MF-11 + `09`.
- **FactScope identity package** (the old "Q1–Q4+E") → resolved into `Naming_Slices_XBRL.md`; the PENDING file was deleted — don't reopen.
- **`_guidance`/`_surprise` suffix vs `fact_type` "redundant?"** → keep both (NAME-17 / MF-09).
- **Macro/news core shape** → **LOCKED** (DCM · CIK-based id · returns from `HAS_PRICE`) — deferred details in §C.
