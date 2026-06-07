# Drivers — Start Here

Current Driver work is about building **one shared Driver catalog** that all producers reuse.

Read only these files first:

```text
.claude/plans/Drivers/
├── DriverExperiment.md      # WHY (all decisions + reasoning) + procedure + status — READ FIRST after compaction
├── Drivers.md               # design + G1 catalog-first + G2 independent gate
├── DriverOntology.md        # naming rules for Driver names
├── workflows/
│   ├── fetch_company_sources.py # pulls ALL non-news sources WITH real text (MD&A/Risk/EX-99.1/transcript Q&A), tagged; NO >2% filter
│   ├── resolve_driver_scope.py # Neo4j: --industry X → tickers · --sector Y → industries · --list (feeds menu_build)
│   ├── menu_build.js        # SEED build (args.industry → resolver auto-pulls tickers): fetch → blind naming → converge
│   ├── catalog_first.js     # G1: catalog-first reuse (reuse/create/skip)
│   ├── gate.js              # G2: independent admission gate (reuse/admit/rewrite/skip)
│   ├── reconcile.js         # Step-2: dedup ‖ G2 (admit/rewrite/skip) → Refute skeptic (breaks bad SAME_AS/rewrites) → writes catalog
│   └── validate_catalog.py  # deterministic post-reconcile validator (HARD-FAIL; zero judgment)
└── runs/<run_id>/           # one run = one industry (run_id = <UTC-timestamp>_<slug>); generated
    ├── manifest·scope·sources_manifest·seed·catalog·validation .json/.txt   # COMMITTED (small: proof + outputs)
    └── sources/<TICKER>.json # GIT-IGNORED (big raw dumps; sha256 recorded in sources_manifest.json)
```

Everything else in this folder is historical draft, evidence, or prior experiment material unless one of the files above explicitly points to it.

Current next step: the method is locked for a clean-slate run. Run **from scratch** — `menu_build.js` with `args={industry:'Restaurants'}` (resolves tickers + stamps a run_id → writes `runs/<run_id>/seed.json`), then `reconcile.js` with `args={run_id:'<that run_id>'}` (→ `runs/<run_id>/catalog.json`; the Validate phase must pass). Do not write to Neo4j during calibration.

Everything's now locked for repeat: run `menu_build.js` with `args={industry:'<name>'}` (resolver auto-pulls tickers + stamps a run_id) → `reconcile.js` with `args={run_id:'<run_id>'}` → re-run for any industry; docs + README point a
  fresh bot to the right place.
