# 00 · Coverage (the zero-loss map)

**What this is:** proof that **every source doc is accounted for** — either covered by a written section, pending a not-yet-written section, or explicitly excluded. Nothing is silently dropped.

Legend: ✅ covered · 🟡 partial · ⏳ pending (section not written yet) · ⛔ excluded / superseded (→ where it lives) · 📜 history only.

---

## 1. Sections written (the live plan)
| File | Content | Blocks | Status |
|---|---|---|---|
| `01_Overview.md` | mission · the one law · history · index-card model | ~15 | ✅ (still to add: 3-tracks map · authority map · dashboard) |
| `02_DriverCatalog.md` | naming rules NAME-01…19 | 19 | ✅ naming · build pipeline + model choice → `10` |
| `03_Slices_FactScope.md` | slices + fact_scope FS-01…25 | 25 | ✅ |
| `04_Units.md` | units UNIT-01…14 | 14 | ✅ |
| `05_Periods.md` | DriverPeriod PER-01…20 | 20 | ✅ |
| `06_MetricFamily.md` | BASE_METRIC family MF-01…12 | 12 | ✅ |
| `07_DriverUpdate.md` | fact_type · states · numbers · verdict DU-01…24 | 24 | ✅ (number layer → superseded by 09) |
| `08_XBRL_ConceptLinking.md` | concept-linking XC-01…18 | 18 | ✅ |
| `09_DriverUpdate_Fields.md` | the 23-field spec (owner-adjudicated) | 23 fields | ✅ (§8 acked 2026-07-03) |
| `10_BuildPipeline.md` | Track A build manual — engine census · overrides · finalization · model slots · acceptance | PIPE-01…37 | ✅ (adjudicated + committed 2026-07-02) |
| `11_TrackB_DriverUpdate_Census.md` | Track B requirements inventory | T1…T15 | ✅ |
| `12_TrackB_FactPipeline.md` | Track B build manual — writer · validators · enrichment · read views | FACT-01… | ✅ |
| `13_TrackC_GuidanceIntegration.md` | Track C active design — archive/retire old guidance; QA evidence only | GI-01… | ✅ |
| `13_Track_RetiredDesign.md` | retired Track C replay design | — | 📜 history only |
| `14_BuildReadiness.md` | remaining pre-coding readiness work — running layer, exact-rule fixes, open decisions, cross-doc cleanup | — | ✅ |
| `66_IssuesToBeHandled.md` | review backlog / issue ledger | ISS rows | ✅ |
| `95_Supersession.md` | 25 reversals + stale-trap docs | — | ✅ |
| `90_OpenItems.md` | all open threads (A–E) | — | ✅ |
| `00_Coverage.md` | this file | — | ✅ |

**Live coverage now spans `01`–`14` plus `66`, `90`, `95`, and `99` as history/audit.**

## 2. Source doc → where it's covered
### Consolidation/ (the authoritative set)
| Source | Covered by | Status |
|---|---|---|
| `Naming_Slices_XBRL.md` | 02 (naming) + 03 (slices/fact_scope) + FS-25 (measurement) | ✅ |
| `XBRL_SliceAxis_Catalog.md` | 03 (FS-06/13 axis data) | ✅ |
| `UnitExtraction.md` | 04 (units) + NAME-13 (per-X) | ✅ |
| `GuidancePeriod.md` | 05 (Periods) | ✅ |
| `MetricGuidanceFamily.md` | 06 (MetricFamily) | ✅ |
| `XBRLConceptLinking.md` | 08 (concept-linking) | ✅ |
| `README.md` | 01 + 06 + 90 (it's the resolution tracker) | ✅ |
| `FactScope_IdentityDecision_PENDING.md` | resolved into Naming_Slices (file deleted) | ⛔ → 90.E |

### WIP/ + origin
| Source | Covered by | Status |
|---|---|---|
| `WIP/DriverGraphSchema.md` | 07 (DriverUpdate) + 09 (fields) | ✅ |
| `DriverOntology.md` | 02 (naming R-rules); stale naming traps logged in 95 | ✅ / ⛔ stale bits |
| `Drivers.md` | 01 + 02 (origin; drift → 95) | ✅ / ⛔ stale bits in 95 |
| `INDEX.md` | 01 + 95 (the map + supersession); stale measurement/name bits logged in 95 | ✅ / ⛔ stale bits |
| `DriverExperiment.md` | 01 (the WHY) | ✅ |
| `WIP/GuidanceDriverConsolidation.md` | MF-11 (company_confirmed) + `13` active Track C archive/retire; live guidance producer/backfill belongs to part 2 | 🟡 |
| `HierarchicalCatalogPlan.md` | `10` (reuse-by-reference — HCP stays the detailed engine spec) | ✅ |
| `WIP/IncrementalRefresh_FinalDesign.md` | ⏳ incremental-refresh section (seam notes in `10` §13) | ⏳ |
| `WIP/Fable-to-Opus_Reader_FinalPlan.md` | `10` §7 (model slots; core decision superseded → 95 #15) | ✅ |
| `CostCutting.md` · `C1_FoldInheritance.md` · `C5_BatchedRepair.md` | `10` §11 (levers, by reference — the three files stay the detailed specs/gates) | ✅ |
| `WIP/XBRL_Guidance_Borrow.md` | superseded on key-grammar → 95; concept side → 08 | ⛔ / ✅ |
| `WIP/THROWAWAY_lane_prompt_optimization.md` | throwaway; the principle → DU-11 | ✅ (throwaway) |
| `DriverContext.md` | full-depth handoff snapshot; superseded by the plan | ⛔ historical |
| `DriverCatalogProcess.html` | naming → 02; pipeline → `10` | ✅ |

### Evidence (probes — cited, not re-locked)
| Source | Cited in |
|---|---|
| `WIP/unit_probe/` (FINDINGS/RESULTS) | UNIT-13 |
| `WIP/naming_probe/` | NAME-04 evidence |
| `WIP/concept_link_revalidation/` + `plans/Drivers/WIP/concept_link_probe/` | XC-13/14 |
| `WIP/cards/` | derived state-card aid; no separate design authority |

## 2b. Code / data / meta files (accounted for)
| File / folder | What it is | Status |
|---|---|---|
| `Drivers/README.md` | old start-here index | ⛔ STALE → `INDEX.md` |
| `evolution.md` | folder history / generations map | 📜 history only (no design rules); itself now stale post-rename |
| `DriverCatalogProcess.pdf` | same content as `DriverCatalogProcess.html` | ✅ = the .html (naming → 02, pipeline → `10`) |
| `workflows/` | the built catalog pipeline (code + 261 tests +1 skip, as of 2026-07-02) | ✅ CODE — design → `10` (upgrade delta = `10` §3–§4) |
| `runs/` | restaurant test-industry runs (names-only catalog, to re-create) | ⏳ generated DATA |
| `__pycache__/` · `*.pyc` | generated caches | ⛔ ignore (generated) |
| `FinalDesign/99_Codex_Decision_Audit.md` | Codex's parallel-review audit | ✅ review artifact |

## 3. Explicitly EXCLUDED (a decision, not an omission)
- `RavenPack/` — competitive-reference taxonomy; **not the naming vocabulary** (only `rumored`/`failed` states were borrowed). Lives in `RavenPack/`, out of the plan by design.
- `archive/` — the entire v1 design (closed-vocab, `canonicalize()`, aliases, slot-vocab). Fully superseded; the reversals are logged in `95_Supersession`.
- The old Codex parallel folder (now removed) — its review value is preserved in `99_Codex_Decision_Audit.md`; its source-ledger role is this `00_Coverage` map.

## 4. Zero-loss statement
- Every Consolidation doc → ✅ covered.
- Every origin/WIP doc → ✅ covered, 🟡 partially covered, ⏳ pending a named section, or ⛔ excluded-with-a-home.
- No source is unaccounted for.

**Still to write:** **incremental refresh** and the **actual update/live-backfill process**. Track C guidance archive/retire is written in `13`; fresh guidance production belongs to part 2, not old-guidance replay.
