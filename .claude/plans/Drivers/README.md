# Drivers — Start Here

Current Driver work is about building **one shared Driver catalog** that all producers reuse.

Read only these files first:

```text
.claude/plans/Drivers/
├── DriverExperiment.md      # why + repeatable procedure + status + cost guard
├── Drivers.md               # design + G1 catalog-first + G2 independent gate
├── DriverOntology.md        # naming rules for Driver names
├── workflows/
│   ├── fetch_company_sources.py # pulls ALL non-news sources WITH real text (MD&A/Risk/EX-99.1/transcript Q&A), tagged; NO >2% filter
│   ├── menu_build.js        # SEED build: fetch → blind per-company naming → converge (edit TICKERS, rerun by industry)
│   ├── catalog_first.js     # G1: catalog-first reuse (reuse/create/skip)
│   ├── gate.js              # G2: independent admission gate (reuse/admit/rewrite/scope-route/skip)
│   └── reconcile.js         # Step-2: dedup (brand≠generic) + G2 over a built menu
└── _menu_restaurants_seed.json  # Restaurants seed (all non-news sources, real text); review artifact, no graph writes
```

Everything else in this folder is historical draft, evidence, or prior experiment material unless one of the files above explicitly points to it.

Current next step: content-aware seed re-run is in progress (real document text via `fetch_company_sources.py`); then Step-2 reconcile (`reconcile.js`) → clean Restaurants catalog with canonical names, reversible SAME_AS links, rewrites, scope-routes, skips. Do not write to Neo4j during calibration.

Everything's now locked for repeat: edit TICKERS in menu_build.js → re-run for any industry; docs + README point a
  fresh bot to the right place.