  Evolution of .claude/plans/Drivers/ — what came before what

  The one-line story: the folder holds five generations of the same idea — build one shared catalog of stock-price
  causes ("drivers") — where each generation was killed or absorbed by measured evidence, and everything now funnels
  into the two FinalDesign* folders you started today.

  GEN 0  May 27–30   Closed word-list design ("v1")      → killed by test (82% wrong rejections), archived Jun 7
  GEN 1  Jun 4–12    Open-vocab catalog + build pipeline → still the base; code lives in workflows/
  GEN 2  Jun 13–14   WIP refinements (reader swap, incremental refresh)
  GEN 3  Jun 14–20   The node spec era (DriverGraphSchema, states, units, RavenPack) + INDEX.md map
  GEN 4  Jun 20–30   Consolidation/ lock wave (units, periods, naming/slices, XBRL linking)
  GEN 5  Jul 1 (now) FinalDesignClaude + FinalDesignCodex — merging all of the above, newest wins

  ---
  GEN 0 — the closed-vocabulary era (written May 27–30, deleted/archived Jun 7)

  Design idea: a fixed word list + deterministic Python (canonicalize()) names every driver. Died when the first real test showed the word list wrongly rejected 82% of correct names.

File: ChecklistProposals.md, DoubtsInHTML.md, DriverImprovements.md
What it was: Multi-bot critiques, owner's ~51 doubts, the "v10 self-heal" lever plan
Where it went: folded into → CombinedPlan.md, then all deleted Jun 7
────────────────────────────────────────
File: CombinedPlan.md
What it was: The all-in-one v1 plan (closed vocab, L1–L7 locks)
Where it went: → archive/CombinedPlan.md; its role (not text) split into Drivers.md + DriverExperiment.md +
  HierarchicalCatalogPlan.md
────────────────────────────────────────
File: DriverOntology_Implementation.md, DriverOntology Prompt.md, Neo4jXBRLDesign.md
What it was: The canonicalize() mechanics, a regeneration prompt, the v1 Neo4j schema
Where it went: deleted; schema authority is now WIP/DriverGraphSchema.md
────────────────────────────────────────
File: _workflow/ (9 files)
What it was: One-shot audit lenses on the v1 plan (coverage, consistency, reliability…)
Where it went: deleted; their method ancestors today's adversarial gates
────────────────────────────────────────
File: Harness/ (2 files)
What it was: Isolated pytest harness to prove the v1 name-cleaner
Where it went: deleted; abandoned with closed vocab
────────────────────────────────────────
File: UnifiedRedesignBrief.md (May 30)
What it was: The pivot document — falsify-first redesign handoff after the 82% result
Where it went: deleted Jun 7; its outcome IS Gen 1
────────────────────────────────────────
File: INGESTION_embedding_dedup.md
What it was: Reuse existing vector indexes to suggest (never decide) duplicates
Where it went: renamed Jun 6 → archived as archive/EmbeddingReference.md; its rule survives verbatim in Drivers.md
────────────────────────────────────────
File: DriverProcess.AUDITED.html → DriverProcess.html
What it was: v1 visual explainer
Where it went: → archive/; replaced by DriverCatalogProcess.html (Jun 17)
────────────────────────────────────────
File: ConceptualRequirements.md, DriverNameRisks.md, isolated_llm_call_pattern.py
What it was: Original requirements, naming risk lists, LLM-call snippet
Where it went: → archive/

(Reminder: "v2" — the over-merge design where three demand stories collapsed into one revenue_demand — lived and died inside the redesign-response window; no standalone file survives, only the history citations.)

GEN 1 — open-vocab catalog design + build (Jun 4–12) — "v3", still the base

┌─────────────────────────────────────┬──────────┬───────────────────────────────────────────────────────────────┐
│                File                 │   Date   │                        Today's status                         │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│                                     │          │ ACTIVE core design (Driver=class, DriverUpdate=instance, G1   │
│ Drivers.md                          │ Jun 4→9  │ propose-first / G2 admission gates) — but flagged by INDEX as │
│                                     │          │  carrying pre-finalization drift                              │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ DriverExperiment.md                 │ Jun 4→9  │ ACTIVE — the WHY (carries the v1/v2 death history)            │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│                                     │ May      │ ACTIVE naming rulebook R1–R10 — but two rules since reversed  │
│ DriverOntology.md                   │ 29→Jun   │ (see GEN 4)                                                   │
│                                     │ 16       │                                                               │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ README.md                           │ Jun 4→11 │ STALE — replaced by INDEX.md, though it has no banner saying  │
│                                     │          │ so                                                            │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ workflows/ (~25 scripts + 257       │ Jun 4–12 │ CODE, built + green; catalog_first.js stale; still can't emit │
│ tests)                              │          │  fact_type                                                    │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ runs/                               │ Jun 9–11 │ DATA — restaurant test-industry runs; the catalog they built  │
│                                     │          │ is names-only and must be re-created                          │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ HierarchicalCatalogPlan.md          │ Jun 9→12 │ ACTIVE ↻ — bottom-up build plan; its creation rules           │
│                                     │          │ superseded by DriverGraphSchema.md (its own Jun 20 banner)    │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ CostCutting.md,                     │ Jun      │ Cost-lever ledger (active), batched repair (GO for leaves),   │
│ C5_BatchedRepair.md,                │ 10–12    │ fold inheritance (shelved study)                              │
│ C1_FoldInheritance.md               │          │                                                               │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ XBRL_Guidance_Borrow.md             │ Jun 11   │ STALE — moved (uncommitted) to WIP/; its topic was later      │
│                                     │          │ solved properly by the concept-link chain                     │
├─────────────────────────────────────┼──────────┼───────────────────────────────────────────────────────────────┤
│ DriverContext.md                    │ Jun 12   │ STALE ↻ full-depth handoff snapshot — good for run-state,     │
│                                     │          │ blind to everything after                                     │
└─────────────────────────────────────┴──────────┴───────────────────────────────────────────────────────────────┘

GEN 2 — WIP refinements (Jun 13–14)

- WIP/Fable-to-Opus_Reader_FinalPlan.md (Jun 14) — reader swap + mandatory 2-pass re-read. Now contradicted by the Jun 30 test (more passes = junk, not recall).
- WIP/IncrementalRefresh_FinalDesign.md (Jun 14) — design-locked append-only refresh; no code; minor staleness (still calls fact_type pending).

GEN 3 — the node-spec era (Jun 14–20)

- WIP/DriverGraphSchema.md — the living authority, locked in layers: structure (06-14) → creation contract + fact_type + states (06-15) → number layer + EXPLAINED_BY verdict edge (06-16) → rumored/failed states validated (06-17) → units delegated (06-20) → DriverPeriod added (06-21, uncommitted edit).
- Satellites: THROWAWAY_lane_prompt_optimization.md (06-17, mooted scratch) · RavenPack/ (06-17, taxonomy recall-checklist — vocabulary import rejected) · DriverCatalogProcess.html/.pdf (06-17, current visual explainer) · WIP/cards/ (06-18, printable state cards) · WIP/GuidanceDriverConsolidation.md (06-18, owner's unify-by-regenerate decision) · WIP/unit_probe/ (06-18–20, V2 resolver, 117/117) · WIP/naming_probe/ (06-20, Rules 0–8 proof, 100%).
- INDEX.md (06-20) — replaced README.md as the folder map; accurate through this era, stale on everything after.

GEN 4 — Consolidation/ lock wave (Jun 20–30) — the layer just before your FinalDesign work

Four waves inside one folder:

┌───────┬──────────────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Wave  │                    Files                     │                    What got locked                     │
├───────┼──────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Jun   │ README.md (absorbed the now-deleted          │ units + per-X-in-name; DriverPeriod for all fact       │
│ 18–20 │ Personal.md), UnitExtraction.md,             │ types; BASE_METRIC family                              │
│       │ GuidancePeriod.md, MetricGuidanceFamily.md   │                                                        │
├───────┼──────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│       │                                              │ fact identity = event+driver+fact_scope; 6 slice       │
│ Jun   │ Naming_Slices_XBRL.md +                      │ kinds; measurement as a set; absorbed and deleted the  │
│ 26    │ XBRL_SliceAxis_Catalog.md                    │ ghost FactScope_IdentityDecision_PENDING.md — its      │
│       │                                              │ Q1–Q4+E are DECIDED, not open                          │
├───────┼──────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│       │ concept_link_probe/ (⚠️ sits in the wrong    │ the XBRL concept linker: probe invented it (Jun 26),   │
│ Jun   │ folder: repo-root plans/Drivers/WIP/,        │ revalidation re-proved it on 274 companies with        │
│ 26–27 │ untracked) → WIP/concept_link_revalidation/  │ non-LLM ground truth (Jun 27), spec locked it (Haiku + │
│       │ → XBRLConceptLinking.md                      │  backstop + component-veto)                            │
├───────┼──────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Jun   │ README.md §5d (uncommitted)                  │ reader model: Opus 4.8 reads, Sonnet 5 classifies —    │
│ 30    │                                              │ supersedes the Jun 14 Fable→Opus 2-pass plan           │
└───────┴──────────────────────────────────────────────┴────────────────────────────────────────────────────────┘

Two GEN-4 reversals that overwrite GEN-1 docs (important for your consolidators): brand = its own driver (DriverOntology R9) → reversed to slice-first; adjusted_eps in the name → reversed to eps + measurement label.

GEN 5 — FinalDesignClaude + FinalDesignCodex (today, Jul 1)

- Codex: 00_SourceLedger.md (05:08 — audit of ~40 source files, authority rule "Consolidation > WIP > root", 21-row superseded-decision map) → 01_FinalDecisions.md (16:46 — the merged rulebook, ~15 sections owner-stamped "approved", ~15 decisions still open; plans to split into files 02–06).
- Claude: five topic files, 13:32–16:46 — 01_Overview (WIP), 02_DriverCatalog (NAME-01…19, WIP trailer), 03_Slices_FactScope (FS-01…25), 04_Units (UNIT-01…14), 05_Periods (PER-01…20, created after my first listing).

Fresh divergences between the two your consolidators should reconcile:
1. Guidance transition: Claude 05_Periods PER-19 records an owner decision today (regenerate guidance as fact_type=guidance, retire the old pipeline); Codex §4.5/§9 still lists that node-label choice as OPEN.
2. Slice menu point-in-time: Claude FS-14 records today's owner ruling (menu = union of all 10-Q/10-K filings, point-in-time filter deliberately left open); Codex §5.4 locks "menu must be point-in-time".
3. Claude files reference 95_Supersession.md and 90_OpenItems.md — neither exists yet. Codex has content Claude lacks (DailyCompanyMoveEvent macro design, two-producer split, validator suites, build order).


