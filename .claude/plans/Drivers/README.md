# Drivers — Start Here

Current Driver work is about building **one shared Driver catalog** that all producers reuse.

Read only these files first:

```text
.claude/plans/Drivers/
├── DriverExperiment.md      # why + repeatable procedure + status + cost guard
├── workflows/menu_build.js  # reusable Step-1 menu builder; edit tickers, rerun by industry
├── Drivers.md               # design + G1 catalog-first + G2 independent gate
├── DriverOntology.md        # naming rules for Driver names
└── _menu_restaurants.json   # Restaurants pilot output; review artifact, no graph writes
```

Everything else in this folder is historical draft, evidence, or prior experiment material unless one of the files above explicitly points to it.

Current next step: run Step 2 reconcile on `_menu_restaurants.json` to produce a clean Restaurants review file with canonical names, proposed reversible SAME_AS links, scope-routes, rewrites, and skips. Do not write to Neo4j during calibration.

Everything's now locked for repeat: edit TICKERS in menu_build.js → re-run for any industry; docs + README point a
  fresh bot to the right place.