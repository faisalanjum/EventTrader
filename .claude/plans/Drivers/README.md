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
│   └── validate_catalog.py  # deterministic post-reconcile validator (HARD-FAIL; zero judgment)
└── runs/<run_id>/           # one run = one industry (run_id = <UTC-timestamp>_<slug>); generated
    ├── manifest·scope·sources_manifest·seed·catalog·validation .json/.txt   # COMMITTED (small: proof + outputs)
    └── sources/<TICKER>.json # GIT-IGNORED (big raw dumps; sha256 recorded in sources_manifest.json)
```

Everything else in this folder is historical draft, evidence, or prior experiment material unless one of the files above explicitly points to it.

Current next step: **build `HierarchicalCatalogPlan.md` Phase 0 + Phase 0.5 FIRST** (`approved.json` + D1 fusion check + deterministic writer, then full-text chunking) — only THEN the clean-slate run: `menu_build.js` with `args={industry:'Restaurants'}` (resolves tickers + stamps a run_id → writes `runs/<run_id>/seed.json`), then `reconcile.js` with `args={run_id:'<that run_id>'}` (→ `runs/<run_id>/catalog.json`; the Validate phase must pass). Do NOT run the seed build on the old un-hardened pipeline. Do not write to Neo4j during calibration.

After Phase 0/0.5 hardening lands, the repeat run is locked: run `menu_build.js` with `args={industry:'<name>'}` (resolver auto-pulls tickers + stamps a run_id) → `reconcile.js` with `args={run_id:'<run_id>'}` → re-run for any industry; docs + README point a
  fresh bot to the right place.
