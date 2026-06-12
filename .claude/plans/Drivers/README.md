# Drivers — Start Here

Current Driver work is about building **one shared Driver catalog** that all producers reuse.

**🎯 Read first — the purpose:** the **`Primary priorities`** section at the top of **`DriverExperiment.md`** defines what the catalog is FOR (traceable + tradeable inventory · minimal but same-name-when-same-meaning · propose-first live reuse). Everything else serves it.

Read only these files first:

```text
.claude/plans/Drivers/
├── DriverExperiment.md      # WHY (all decisions + reasoning) + procedure + status — READ FIRST after compaction
├── Drivers.md               # design + G1 propose-first + G2 independent gate
├── DriverOntology.md        # naming rules for Driver names
├── HierarchicalCatalogPlan.md # LOCKED + owner-confirmed plan: harden the leaf (D1 fusion check + no-text-loss chunking) then fold Industry→Sector→Global; build order + exact specs (read before building the scale-up)
├── workflows/
│   ├── fetch_company_sources.py # pulls ALL non-news sources WITH real text (MD&A/Risk/EX-99.1/transcript Q&A), tagged; NO >2% filter
│   ├── resolve_driver_scope.py # Neo4j: --industry X → tickers · --sector Y → industries · --list (feeds menu_build)
│   ├── menu_build.js        # SEED build (args.industry → resolver auto-pulls tickers): fetch → blind naming → converge
│   ├── catalog_first.js     # G1: propose-first reuse (propose own name → compare catalog → reuse/create/skip)
│   ├── gate.js              # G2: independent admission gate (reuse/admit/rewrite/skip)
│   ├── reconcile.js         # Step-2: dedup ‖ G2 (admit/rewrite/skip) → Refute skeptic (breaks bad SAME_AS/rewrites) → writes catalog
│   ├── validate_catalog.py  # deterministic post-reconcile validator (HARD-FAIL; zero judgment; writes validation_exit.json sidecar)
│   ├── assemble_catalog.py  # ZERO-judgment catalog writer (decisions+D5 review → catalog/approved; anachronism guards)
│   ├── fold_catalogs.py     # fold machinery (part-a/part-b, norm, require_validated)
│   ├── build_tree.js        # Industry→Sector→Global folds; walk mode repairs every leaf BEFORE it folds
│   ├── repair_duplicates.py/.js # required §13.2 duplicate-repair pass; C5 batched lane GO for LEAVES (C5_BatchedRepair.md §8d: AND-gate + un-skippable 2% canary; folds stay per-pair)
│   ├── resume_menus.py      # A2 per-chunk resume: re-prove fetch+chunk byte-exact, fan out ONLY missing menus
│   ├── ab_stratum.py · ab_differ.py · ab_pair_judge.js · rescue_review.py # decision-④ A/B harness + the one-off transcript rescue (break-glass pattern)
│   └── tests/               # 257-test pytest suite (TDD; run before trusting any change)
└── runs/<run_id>/           # one run = one industry (run_id = <UTC-timestamp>_<slug>); generated
    ├── manifest·scope·sources_manifest·seed·catalog·validation .json/.txt   # COMMITTED (small: proof + outputs)
    └── sources/<TICKER>.json # GIT-IGNORED (big raw dumps; sha256 recorded in sources_manifest.json)
```

Newer decision docs (each self-contained): `CostCutting.md` (Focus-2 lever ledger — source of truth on what's adopted/rejected/open) · `C5_BatchedRepair.md` (batched repair spec; §8c incident, §8d GO ruling) · `C1_FoldInheritance.md` (shelved, free `--measure-inherit` rider) · `XBRL_Guidance_Borrow.md` (linking + DriverUpdate recipes; linking runs POST-Fable by decided verdict §D).

Everything else in this folder is historical draft, evidence, or prior experiment material unless one of the files above explicitly points to it.

**CURRENT STATE (2026-06-11): Fable front-load.** All phases built + gated (suite 257+1). The first production seed run (full Restaurants, 14 companies, 969 chunks) is IN FLIGHT, paused at 32/969 — resume any time with `menu_build.js` args `{"industry":"Restaurants","resume_run_id":"2026-06-11_204218_restaurants"}` (pays only the remainder). Fable windows = readers ONLY; reconcile/folds/repair are all-Opus and run later off the saved run dirs. After Restaurants completes: calibration verdict (tokens/company → achievable N of 786 → priority queue → C2 gate decision) — the orchestrator session computes it from transcripts.
