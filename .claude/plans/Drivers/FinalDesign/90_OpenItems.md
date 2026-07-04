# 90 · Open items (what's not yet decided or not yet built)

**What this is:** every open thread in one place. Split into: **A** = design *decisions* still needing an owner call · **B** = design done, *code/wiring* not built · **C** = parked/deferred · **D** = design *sections* still to write · **E** = resolved (kept for the record).

---

## A. Open DESIGN decisions (need an owner call)
| ID | Question | Lean / note |
|---|---|---|
| ~~09 §8~~ | Field-spec amendment bundle | ✅ **APPROVED 2026-07-03** → §E |
| ~~FS-14~~ | Slice-menu point-in-time | ✅ **RESOLVED 2026-07-02: PIT for DriverUpdate write-time** (3-context split) → §E |
| **FS-23** | Cross-company **value** comparison (does "International" at A = "International" at B?) — a separate, not-yet-built layer | deferred; conservative bar |
| **UNIT-12** | Add `percent_qoq` to the 9-unit enum? | lean **no** — keep stable unless production evidence forces it |
| 8-K taxonomy | Is the 24-tag 8-K event taxonomy useful here? | open (README "To Resolve") |
| Amendments | How to handle filing amendments? | open (README "To Resolve") |
| **Model policy** | Reader default = **Opus reads + Sonnet classifies** (supersedes Fable/2-pass) — but exact model, number of runs, and job-by-job process need a **larger audit/experiment** | leading default set; full policy open |
| ~~ISS-16 routing~~ | actual vs own guidance: metric / surprise / both | ✅ **LOCKED 2026-07-03** (`12` §10.5) — expectation comparison → metric + surprise, state derived from stated numbers, in_line materialized; corpus-grounded + adversarially checked. OBJ-2 resolved: `previous_guidance` also forbidden on metric (95 #24). **Fully closed.** → §E |

## B. Design done — BUILD/WIRING not done
| ID | What | Status |
|---|---|---|
| **UNIT-14** | The shared unit resolver is proven in scratch (117/117), **not wired** into the producer (old Steps 5-7) | build-pending |
| **PER-20** | DriverPeriod design locked; **not built** — extract `driver_period_resolver.py`, pass the 21 tests, prove YTD/TTM math, write-once hardening | build-pending |
| **XC-16** | Concept-linker: replace the hand 4-entry deny-set with the us-gaap **calculation-hierarchy** veto | recommended **before** the full-universe run |
| Concept-link full run | Validated on 274/795 companies (~35%); a **full-universe run** is pending | pending |
| Guidance field-map / member-company reconciliation | No longer a Track C production-replay task. Old guidance fields and links are archived as QA evidence; fresh guidance field mapping and member/company reconciliation belong to Track B, part 2, and enrichment design. | re-homed |

## C. Parked / deferred (out of scope for now)
- **Macro/news attribution** — **core shape LOCKED 2026-07-02**: `DailyCompanyMoveEvent {id=dcm:<cik>:<trade_date>, trade_date, created}` `-FOR_COMPANY->Company` `-ON_DATE->Date`; verdict via `EXPLAINED_BY`; realized return **read from `Date-HAS_PRICE-Company`** (never duplicated); News stays `FROM_SOURCE`. **Open details:** the significance threshold · the source for a *pure-macro* driver (e.g. `oil_price` with no company news) · `subject_company` / 0..N `FROM_SOURCE` if ever needed.
- **§10 dormant rider** — creating 10-K/10-Q metric facts by **XBRL-linking** instead of LLM re-extraction (`origin` field, `[XBRL]` quote, etc.). Activates only if the "Codex §4.8" write-path decision is approved.
- **Blanket-withdrawal fan-out** — a "guidance withdrawn" fact fans out per open guide (the one place the producer writes beyond the literal quote); owner sign-off noted (09 §7).

## D. Design SECTIONS still to write
See `14_BuildReadiness.md` for the pre-coding readiness work order that organizes these sections plus exact-rule fixes and cross-doc cleanup.

- **Actual update / live-backfill process** — how fresh DriverUpdates are produced from reports/transcripts/news/filings over time, including fresh `fact_type=guidance` production from source documents.
- **Incremental refresh** — re-run only on new events; old↔old frozen; the append-seam rules. *(Seam notes vs the finalization step already in `10` §13.)*
- **Overview finish** — the 3-tracks map, the authority/reading map, a status dashboard.

## E. RESOLVED (for the record)
- **EXPLAINED_BY verdict layer** (DU-21…24 · `explained_target` key wording · verdict-edge `evhash16` kept · DailyCompanyMoveEvent = its own label; trade_date owned by the returns/trading-day layer) → **LOCKED by owner 2026-07-03** via the Track B plan (`12_TrackB_FactPipeline.md` §10.1); `07` upgraded.
- **09 §8 amendment bundle** (`level_bound`→self-describing shapes + transient hints · `qualitative`→`value_text` guidance-only · fact `evhash16` retired) → **APPROVED by owner 2026-07-03**; the per-fact_type field set is FINAL (95 #16–18 applied; DU-13/14/16/18 amendments live).
- **DriverCatalog build pipeline (Track A)** → **WRITTEN 2026-07-02: `10_BuildPipeline.md`** (engine reuse + overrides + class finalization + acceptance; the cost/fold levers folded into its §11; committed 281fd63).
- **Guidance retirement / QA evidence (Track C)** → **WRITTEN 2026-07-04: `13_TrackC_GuidanceIntegration.md`**. Old guidance is archived/retired and kept as QA evidence only; no production replay of old `GuidanceUpdate` rows.
- **Guidance node-label** (`:GuidanceUpdate` vs `:DriverUpdate` vs dual-label) → **archive/retire old `GuidanceUpdate`; create fresh `fact_type=guidance` DriverUpdate facts through the new Driver pipeline** (owner update, 2026-07-04 — Track C v2.0).
- **company_confirmed scope** → **guidance-only** (owner, 2026-07-01 — MF-11); type = **boolean** (09).
- **FactScope identity package (the old "Q1–Q4+E")** → resolved into `Naming_Slices_XBRL.md` (per memory); the `PENDING` file was deleted, don't reopen.
- **`_guidance`/`_surprise` suffix vs `fact_type` "redundant?"** → keep both (NAME-17 / MF-09).
- **FS-14 (slice-menu PIT)** → **PIT for DriverUpdate write-time** (owner, 2026-07-02); 3-context split (name-creation N/A · write=PIT · read/repair=all-history). Re-locked to `Naming_Slices §7` after a brief in-session reopen; slice-value immutability is orthogonal.
- **Macro/news core shape** → **LOCKED** (`DailyCompanyMoveEvent`, CIK-based id, returns from `HAS_PRICE`) — open *details* in §C.
