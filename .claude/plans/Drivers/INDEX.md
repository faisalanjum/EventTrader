# Drivers — Index & Rules

**What this folder is:** the design + build pipeline for **ONE shared Driver catalog** — a single, reusable, traceable list of the real-world *causes* that move stock prices (`same_store_sales`, `oil_price`, `fed_rate`), which every automated producer reuses.

**The whole point in one line:** the **same cause always gets the same name everywhere** → scattered events become one queryable time-series per cause → learn → predict → trade.

**Read in this order →** the **[Reading order](#reading-order)** box below (newest-truth first). The two live authorities = **`WIP/DriverGraphSchema.md`** (node spec) + **`Consolidation/UnitExtraction.md`** (units / per-X).

> This file replaces the old `README.md` (stale since Jun 11). It is a map + a rule sheet, not a spec — the canonical files above are the source of truth.

---

## Reading order
*(newest-truth first — read top to bottom. The [Consistency](#consistency--whats-stale--how-to-fix-it) box says which of these are not-yet-resynced.)*

```
1  INDEX.md  (this file)             which docs are current vs stale
2  WIP/DriverGraphSchema.md          the node spec = SOURCE OF TRUTH (fact_type · fact_scope · EXPLAINED_BY edge · weightage · units)
3  Consolidation/UnitExtraction.md   units + per-X-in-name (newest, Jun 20)
4  WIP/unit_probe/FINDINGS.md        the unit verdict  (read this, NOT RESULTS.md)
5  DriverCatalogProcess.html + WIP/cards/driver_state_cards.html   the locked driver_state lanes
6  DriverExperiment.md               the WHY (v1 closed-vocab died · v2 over-merge died · v3 = LLM judges meaning)
7  DriverOntology.md → Drivers.md    LAST + with caution — still carry pre-finalization drift (see Consistency)
✗  skip unless tracing history:  README.md · DriverContext.md · WIP/XBRL_Guidance_Borrow.md · WIP/unit_probe/RESULTS.md · workflows/catalog_first.js
```

---

## Menu
- **[Reading order](#reading-order)** — the order to read the folder (newest-truth first)
- **[1. Where things stand](#1-where-things-stand)** — what's done vs open, in 6 lines
- **[Consistency — what's stale & how to fix it](#consistency--whats-stale--how-to-fix-it)** — the ~10% drift + the minimal fix path
- **[2. File map](#2-file-map)** — every file, its date, status, and who superseded it
- **[3. The rules (never re-litigate)](#3-the-rules-never-re-litigate)** — purpose · properties · naming · DriverUpdate · tensions
- **[4. Still open (don't build yet)](#4-still-open-dont-build-yet)**

---

## 1. Where things stand

| Layer | Status |
|---|---|
| **Driver CLASS** (name + `fact_type` + optional links) | ✅ **finalized + validated** |
| **DriverUpdate** fact / number / state layer | 🟡 agreed-in-principle, **not locked** (states & enum validated; number layer "agreed") |
| **EXPLAINED_BY** verdict edge | 🟡 designed/locked-in-principle, **not started** |
| **Build pipeline** (leaf → fold → repair) | ✅ built + 257 tests green |
| **Actual graph** | ⛔ **0 nodes built**; first seed run frozen at 32/969 menus |
| **The core hypothesis** (does same-name actually emerge across companies?) | ⛔ **UNPROVEN** — the honesty/fitness gate has **never run**. All green gates so far are mechanical (structure + cost), not the real test. |

History in one breath: **v1** died (closed word-list rejected 82% of even-correct names) → **v2** died (merged aggressively → 3 different demand stories collapsed into one generic `revenue_demand`, failed its held-out exam) → **v3** (now): *LLM judges meaning, code only checks structure, err specific.*

---

## Consistency — what's stale & how to fix it

**Crux:** the folder is **~90% consistent.** The 4 newest files agree (`WIP/DriverGraphSchema.md` · `Consolidation/UnitExtraction.md` · `WIP/unit_probe/FINDINGS.md` · this `INDEX.md`). All drift = **two docs this map still calls CURRENT but that were never re-synced — `DriverOntology.md` + `Drivers.md`** — plus a few files that already self-flag as stale, plus build code that can't emit `fact_type` yet.

| | What's inconsistent | Where | Fix |
|---|---|---|---|
| 🔴 | says `magnitude` (now **`weightage`**) + shows the verdict **on the node, not the `EXPLAINED_BY` edge**; has **no** `fact_type`, **no** per-X rule | `DriverOntology.md`, `Drivers.md` | rename → `weightage`; move the verdict axes onto the `EXPLAINED_BY` edge; add 1 line each for per-X + `fact_type`; header-point to `DriverGraphSchema.md` |
| 🔴 | illegal example `driver_state = cut` (not a lane word) | `DriverOntology.md` §5 | change the example to a real lane state (`announced` / `decreased`) |
| 🟡 | still asserts `$/physical → unknown` — its own sibling `FINDINGS.md` reversed it | `WIP/unit_probe/RESULTS.md` | add a 1-line "SUPERSEDED by FINDINGS.md" banner (no body rewrite) |
| 🟡 | old key grammar, never mentions `fact_scope` | `WIP/XBRL_Guidance_Borrow.md` | add a 1-line "SUPERSEDED on key grammar" banner |
| ✅ | `eps_surprise` / `revenue_guidance` suffix vs `fact_type` redundancy is RESOLVED: the suffix stays in `driver_name`; `fact_type` stays as the permanent lane; `<base>_guidance` and `<base>_surprise` connect to base metric `<base>` via `BASE_METRIC`, never `SAME_AS` | `WIP/DriverGraphSchema.md` metric-family rule + `Consolidation/README.md` (2026-06-21) | no action |
| 🔧 | build never assigns/validates `fact_type`; the naming prompt never says "per-X → name" | `workflows/` (`menu_build.js`, `assemble_catalog.py`, `validate_catalog.py`) | **code, not docs:** add the final Opus `fact_type` step + a `fact_type`/per-X check |
| ⚪ | already self-flagged stale — no action | `README.md` · `DriverContext.md` · `workflows/catalog_first.js` | leave as-is |

**Minimal path to fully consistent (docs only):** ① edit `DriverOntology.md` + `Drivers.md` (the two 🔴 rows) → ② add the two 🟡 one-line banners. The former suffix-vs-`fact_type` open item is now resolved in `DriverGraphSchema.md` (2026-06-21). The 🔧 row is separate, real build work.

---

## 2. File map

Grouped by era. Arrows = supersession. `↻` = partial (only the noted topic is stale).

### Archive (May 29 – Jun 7) — fully superseded, kept for history
| File | Status | What it was | → |
|---|---|---|---|
| `archive/ConceptualRequirements.md` | ARCHIVE | Owner's original requirements (3 producer sets, one global list) | → `Drivers.md` |
| `archive/DriverNameRisks.md` | ARCHIVE | Scratch lists of naming failure modes | → `DriverOntology.md` |
| `archive/CombinedPlan.md` | ARCHIVE | The old all-in-one v1 plan | → split into `Drivers.md` + `DriverExperiment.md` + `HierarchicalCatalogPlan.md` |
| `archive/DriverProcess.html` | ARCHIVE | v1 visual explainer (Driver/DriverChange, closed vocab) | → `DriverCatalogProcess.html` |
| `archive/EmbeddingReference.md` | ARCHIVE | Reuse existing vector indexes to surface dup candidates | — |
| `archive/isolated_llm_call_pattern.py` | ARCHIVE | Reference snippet (metered OpenAI — not the prod path) | — |

### ERA 1 — catalog design + build (Jun 9 – 12)
| File | Date | Status | Purpose |
|---|---|---|---|
| `Drivers.md` | 06-09 | **CURRENT** | Core design: Driver=class, DriverUpdate=instance, G1/G2 gates, honesty gate |
| `DriverExperiment.md` | 06-09 | **CURRENT** | The WHY + operator guide + Primary priorities (the purpose statement) |
| `DriverOntology.md` | 06-09→16 | **CURRENT** | The naming rules R1–R10 (one specific reusable noun) + banned content |
| `HierarchicalCatalogPlan.md` | 06-12 | **CURRENT** `↻` | Locked build plan (bottom-up Company→Industry→Sector→Global; D1–D8). **This + its prompts built the old names-only catalog;** creation rules (`fact_type`, per-X/basis naming) now updated by `WIP/DriverGraphSchema.md` — see its top banner |
| `CostCutting.md` | 06-11 | **CURRENT** | Cost/token lever ledger — what's adopted / rejected / open (Master Rule lives here) |
| `C5_BatchedRepair.md` | 06-11 | **CURRENT** | Batched duplicate-repair spec; GO for leaves, folds pending a gate |
| `C1_FoldInheritance.md` | 06-12 | **WIP/shelved** | Study only: skip re-judging unchanged records at folds (honest save only ~5–22%) |
| `DriverCatalogProcess.html` (+`.pdf`) | 06-17 | **CURRENT** | Visual explainer of the current end-to-end build (replaces archive HTML) |
| `DriverContext.md` | 06-12 | **STALE** `↻` | Full-depth snapshot (run-state, code nuances). *Stale on all ERA-3 work; still good for ERA-1 run-state.* |
| `README.md` | 06-11 | **STALE** | Old start-here index. → **this file** (predates everything in ERA 3) |

### ERA 2 — WIP refinements (Jun 11 – 14)
| File | Date | Status | Purpose |
|---|---|---|---|
| `WIP/XBRL_Guidance_Borrow.md` | 06-11 | **WIP** | How to copy Guidance's XBRL-linking + identity recipe; linking is a post-build layer |
| `WIP/Fable-to-Opus_Reader_FinalPlan.md` | 06-14 | **WIP** | Swap the chunk-reader Fable→Opus (Opus has coverage dead-zones) + 2-pass re-read; not applied |
| `WIP/IncrementalRefresh_FinalDesign.md` | 06-14 | **WIP** | Re-run only on NEW events; old↔old frozen; needs a verdict memory; design-locked, no code |

### ERA 3 — node spec, states, units, taxonomy (Jun 15 – 20) = CURRENT FRONTIER
| File | Date | Status | Purpose |
|---|---|---|---|
| **`WIP/DriverGraphSchema.md`** | 06-17 | **WIP ★** | **The latest, ~80%.** DriverUpdate node spec: §0 creation contract, fact_type, states, number layer, EXPLAINED_BY, guidance-link |
| `WIP/GuidanceDriverConsolidation.md` | 06-18 | **WIP** | Fold the live Guidance pipeline in as `fact_type=guidance`; regenerate-not-migrate; reuse matrix |
| `WIP/THROWAWAY_lane_prompt_optimization.md` | 06-17 | **THROWAWAY** | Scratch: make state prompts pass on the weakest model; disposable |
| `WIP/unit_probe/FINDINGS.md` | 06-18 | **WIP** | Verdict: borrow Guidance's V2 unit resolver (+ hints) for all fact_types (probe % being re-run) |
| `WIP/unit_probe/RESULTS.md` | 06-18 | WIP `↻` | The 115-case scoreboard. → `FINDINGS.md` *(FINDINGS corrects its `$/barrel→unknown` line — see [3d](#3d-driverupdate-node))* |
| `WIP/unit_probe/unit_resolver.py` (+`test_`) | 06-18 | CODE | The **shared** unit resolver for Guidance + Driver (the deliverable; 25/25 + parity) |
| `WIP/unit_probe/unit_extract.py`, `run_probe*.py`, `probe_name_vs_unit.py`, `cases.json` | 06-18 | CODE/DATA | Evidence-only probe scripts. `unit_extract.py` → `unit_resolver.py` |
| `WIP/cards/driver_state_cards.html` (+`.pdf`, `gen_driver_cards.py`) | 06-18 | WIP/CODE | Printable index cards: 4 fact_types + 27 state cards (real CAKE drivers) |
| `Consolidation/Personal.md` | 06-18 | **WIP** | Owner's raw brainstorm bullets (mimic Guidance flow; ID recipe; model choice; open Qs) |
| `Consolidation/UnitExtraction.md` | 06-20 | **WIP ★** | Locked per-X / unit naming rules + the V2 unit-resolver contract (set-in-stone rules; supersedes the old "stays-bare" per-X line). Probe re-run still pending |
| `RavenPack/RavenPack_Taxonomy.md` | 06-17 | **WIP** | Source-grounded reconstruction of the ~7,400 event taxonomy (free union = 970) |
| `RavenPack/RavenPack_Taxonomy_vs_Drivers.md` | 06-17 | STALE `↻` | Earlier taxonomy + same/different comparison. → `RavenPack_Taxonomy.md` (970-union) |
| `RavenPack/*.py` · `RavenPack/*.csv/.txt/.pdf` | 06-17 | CODE/DATA | merge/analyze/dump scripts + the assembled taxonomy CSVs + source files |

### Code & data (generated)
| Path | Status | Purpose |
|---|---|---|
| `workflows/menu_build.js` | CODE | Seed build: blind per-chunk bots coin candidate names (the reader = Fable→Opus swap target) |
| `workflows/reconcile.js` | CODE | Step-2: dedup ‖ G2 gate → Refute → deterministic assemble → validate |
| `workflows/gate.js` | CODE | G2 independent gate: reuse / admit / rewrite / skip |
| `workflows/repair_duplicates.{js,py}` | CODE | Required whole-catalog late-duplicate repair pass (C5 batched on leaves) |
| `workflows/fold_catalogs.{js,py}` · `build_tree.js` | CODE | Industry→Sector→Global folds; walk repairs each leaf before it folds |
| `workflows/assemble_catalog.py` · `validate_catalog.py` | CODE | Zero-judgment writer + structure-only hard-fail validator (the ONLY deterministic gate) |
| `workflows/fetch_company_sources.py` · `chunk_company_sources.py` · `resolve_driver_scope.py` · `build_seed.py` · `resume_menus.py` | CODE | Source pull (full text) · no-loss chunking · Neo4j scope resolver · seed grouping · per-chunk resume |
| `workflows/catalog_first.js` | CODE/**stale** | G1 propose-first module — lags the locked design, NOT wired; raise to owner before use |
| `workflows/ab_*.{py,js}` · `rescue_review.py` · `slice_seed.py` | CODE | A/B cost-gate harness + one-off rescue helpers |
| `workflows/tests/` | CODE | 257-test pytest suite — run before trusting any change |
| `runs/<id>/` | DATA | One run = one industry. `sources/*.json` git-ignored (big); manifests/seed/catalog committed |

---

## 3. The rules (never re-litigate)

### 3a. Why the catalog exists — purpose + 3 priorities
1. **PURPOSE.** A global inventory of Drivers, each specific enough to **(a) trace its evolution over time** and **(b) drive automated workflows that detect a change and trigger buy/sell signals.**
2. **MINIMAL, BUT SAME-NAME-WHEN-SAME-MEANING.** As small as possible *without* sacrificing #1 — no bloat. Use the **exact same name whenever two drivers mean exactly the same thing**; late duplicates get reversible **SAME_AS** (never a destructive merge). **Inverse guarantee: ONE NAME = ONE MEANING** — a name must never span two real causes.
   - **Same metric family, different fact kind:** keep separate names and separate Drivers, then connect guidance/surprise to the base metric with `BASE_METRIC`. `revenue_guidance -> BASE_METRIC -> revenue`; `revenue_surprise -> BASE_METRIC -> revenue`. They are never `SAME_AS` and never merge numeric series. Full rule: `Consolidation/README.md`.
3. **LIVE REUSE ORDER** (production). Per event the producer: **(a)** coins its own exact name from the evidence *before* seeing the catalog → **(b)** is shown the most-related catalog drivers (sorted company→industry→sector→meaning) → **(c)** reuses **only on exact same meaning**, else keeps its new candidate (which still passes G2).

> The catalog's moat vs RavenPack/Bigdata is the **attribution layer** (EXPLAINED_BY graded against the realized return) — they have none. Don't drift toward their event-cataloging model.

### 3b. What a Driver must be (properties, ranked)
**Primary:**
- **Specific** — name as specific as the evidence allows. **Breadth is never coined by the LLM; it EMERGES only when the same name is reused.** (Coining a generic word is exactly what killed v2.)
- **A reusable CLASS** — a class that recurs (`government_shutdown` once is fine); a name bound to one date/instance (`q1_2026_shutdown_effect`) is rejected.
- **Consistently named** — spelling/plural/acronym/word-order variants resolve to one canonical form.
- **Only the causal noun** — the name carries the cause and nothing else (state, impact, date, company, period, magnitude, unit, quote all live in other fields).
- **Source-grounded** — open vocabulary; every important noun comes from the source text or an existing driver.

**Secondary (meaning-distinguishing → kept IN the name):**
- **Measurement basis** — `adjusted`/`non_gaap`/`core`/`constant_currency`, diluted vs basic. `adjusted_eps ≠ eps`, never SAME_AS'd.
- **Per-X denominator** — `eps`, `sales_per_square_foot`, `dividend_per_share`, `oil_price_per_barrel`. There is **NO per-X unit**; the unit stays the base (usually `usd`/`count`). **Rule (set-in-stone, supersedes the old "stays-bare" line): transcribe whatever per-X the source states — business AND physical, no "physical vs business" judgment.** Source states it → the name carries it; source doesn't → bare name (`oil rose 8%` → `oil_price`, never invent `_per_barrel`). A different per-X basis = a **different Driver**, never SAME_AS (`oil_price_per_barrel` ≠ `oil_price_per_tonne`).
- **Brand/segment level** — `taco_bell_same_store_sales` is its OWN driver, separate from `same_store_sales`. Segment/geography **default to `fact_scope`** (the read-time series already partitions by segment + period); put it in the NAME only when the source treats it as a standalone, recurring cause.

**Driver node fields:** `id` (code-built) · `name` · `fact_type` · `created` · `definition` (optional) · `SAME_AS` (edge, not a property — no aliases array) · optional `MAPS_TO_CONCEPT/MEMBER/GUIDANCE` links on the class. **No units, no `evhash16` on the class.**

### 3c. Naming + creation rules (the locked list)
- **Open vocabulary only.** Closed vocab = 82% reject = v1's death. Never reintroduce.
- **G1 — propose-first reuse.** Coin your own exact name first, *then* compare the retrieved related catalog, reuse on exact meaning only. (Anchoring on the catalog up front invites lazy over-reuse.)
- **G2 — independent admission gate** (a *different* model): `reuse / admit / rewrite / skip`. A **rewrite fixes wording, never meaning.** Skip only if vague / rule-breaking / bound to ONE event-date.
- **Producer-agnostic catalog.** NO route bucket, NO `kind` tag, NO fundamental/news split. *Which* producer used a driver lives on `DriverUpdate.llm_producer`, not the catalog. (`fed_rate` is `fed_rate`, whoever emits it.)
- **3-check for any reuse / SAME_AS / rewrite:** same object **+** same scope **+** same mechanism. Both reviewers judge from the **evidence** (quote/source/date), not the bare string.
- **SAME_AS = reversible link, NEVER a destructive merge.** Both nodes survive with their own evidence; trading/read-through code must follow the links. Merge only on exact same meaning.
- **Fail-close: err SPECIFIC.** Over-merge = the v2 catastrophe (permanent → bad trade); over-reject = v1. Default = keep-separate. Under-merge is recoverable; over-merge is not.
- **Never silently union a mixed-meaning same-name collision (D5):** Refute-confirmed SAME → union; DIFFERENT → split into more-specific names; UNCLEAR → park.
- **Refute** (merge-skeptic) runs on *every* fusion (SAME_AS, meaning-changing rewrite, D5 union) — it tries to BREAK the merge; can't-break → union, else keep-separate. High-blast fusion (≥8 companies / global ≥2 children) gets a 2nd AND-voted Refute. **Refute is the last line of defense against over-merge — never downgrade it to a cheaper model.**
- **Judgment → LLM; structure → code.** `validate_catalog.py` is the ONLY deterministic gate (structure-only, hard-fail). **No deterministic name/word-matching for meaning** — tickers/brands are common words (`WING`, `SHAK`, "shake") → false-positives. Hard-bad names are G2's job; if the gate misses, fix the **prompt**, never add brittle code.
- **Bottom-up fold:** Company→Industry→Sector→Global, same reconcile pipeline each level; **only the leaf coins names**, higher levels only consolidate. Sector is size-optional. Carry prior SAME_AS forward (never auto-break). Chunk text, never truncate; never split one event.
- **Late-duplicate repair is a REQUIRED build step:** embeddings *suggest* pairs (cosine 0.60) → Refute decides → code writes SAME_AS → validate. Embeddings never decide equality.
- **Build creates only the CLASS.** Producers create every DriverUpdate (see 3d).
- **Any rule change = ONE general principle, never sector-specific examples** (examples overfit — how v1 died).

### 3d. DriverUpdate node
- **§0 creation contract (LOCKED 06-15).** Catalog build makes the complete Driver **CLASS** (name + `fact_type` + optional links) in one run and **NEVER** a DriverUpdate. **Producers** (`earnings-learner` / `news-driver`), live **and** backfill, are the ONLY DriverUpdate creators. No build-time seeder. KPI-only evidence (fiscal.ai, no event) makes a **name only**.
- **A DriverUpdate = a real event-level FACT** (a state, change, surprise, guidance item, or action) — **not a mere mention**, and **no `X→Y` change required** (a CEO resignation / FDA approval / store closure is a valid fact). The "only seed if >2 events" idea was **dropped**; recurrence is a read-time view, never a write gate.
- **`fact_type` (LOCKED 06-15, 4 values, validated on 1,282 names):** `metric` · `guidance` · `surprise` · `action_event`. Set **once** per Driver by a **strong model (Opus)** as the mandatory final build step; routes the state vocabulary. Decider = the **persistence test** (is there a standing level you could re-read? yes → metric, no → action_event); `_surprise`/`_guidance` framing overrides; dual framing allowed (`dividend` vs `dividend_per_share`).
- **`driver_state` (LOCKED 06-15, validated on 3,825 quotes; on the DriverUpdate, never the name) — lane per fact_type:**
  - metric → `increased / decreased / unchanged / mixed / reported / persists / unknown`
  - guidance → `introduced / raised / lowered / reaffirmed / withdrawn / unknown`
  - surprise → `beat / in_line / missed / unknown`
  - action_event → `at_risk / announced / occurred / continued / resolved / canceled / suspended / rumored / failed / unknown` *(`rumored`+`failed` added & validated 06-17; `failed` = an outside party blocked it, ≠ `canceled` = the company's own withdrawal)*
- **Number layer (AGREED 06-16; all nullable; producer-fills, code-decides):** `level_low/high/bound/unit` · `change_value` (signed delta, not the level) `/unit` · `comparison_low/high/baseline`. `comparison_baseline ∈ {consensus, prior_year, sequential_period, previous_guidance, null}` (store the **primary** only). **Store-when-stated; never fabricate a number.** These hold the **driver's own** number, never the stock effect.
- **Units = Guidance `canonical_unit` enum, VERBATIM** (`m_usd, usd, percent, percent_yoy, percent_points, basis_points, count, x, unknown`) so the Guidance link + dedup line up with no translation table. Borrow Guidance's **V2** resolver (not V1) via the shared `unit_resolver.py`: producer always sends `unit_kind_hint` (+ `money_mode_hint` when money), **code decides the final unit + scaling**, and the gate asserts the **scaled value**, not just the unit string. Call it **separately** for `level_*` and `change_*` (`margin "rose 60 bps to 17.6%"` → `level_unit=percent`, `change_unit=basis_points`). **No `comparison_unit` field** — comparison values share `level_unit`; a different-unit baseline stays in the `quote`. Reject any final unit outside the 9 (`usd_per_share`, `shares`, `dollars_per_store` = resolver/prompt failure).
  - **Physical-price per-X is NOT `unknown`** (old probe text corrected): a source-stated `$/barrel` is named `oil_price_per_barrel` and resolves to **`usd`**. The only guard = if the source states `$/X` but the name lacks `_per_X` → **naming failure, flag for rename** (do **not** add a `$/physical → unknown` guard). *(`RESULTS.md` + the 94% scoreboard are stale on this — they assumed `$/X → unknown` and are being re-run; `FINDINGS.md` + `Consolidation/UnitExtraction.md` carry the corrected rule.)*
- **Identity = the Guidance recipe; CODE builds every key, AI never.** Fact key = `event + driver + fact_scope` (**no producer** → two readers of one fact converge to one node). `fact_scope` = code-built `{period, basis/scope}` (prefer structured; quote-hash only when no clean scope) — **identity-only, never in the name.** `evhash16` = a value-hash property (not a key). Re-runs **merge in place**.
- **Edges:** `OF_DRIVER` (DriverUpdate→Driver, exactly 1). **The verdict is NOT a node** — it's the property-laden **`EXPLAINED_BY`** edge `Event→DriverUpdate`, added only when a producer blames the move on the fact. **Company is never in the driver layer** — reached via `Event→Company` (which carries the realized return); a market-wide driver (`oil_price`) takes the identical shape.
- **EXPLAINED_BY verdict (FINAL 06-16) — 3 orthogonal axes:** `stock_impact` (long/short = direction) · `weightage` (deciles 0.1–1.0 or null = an **independent** force, never summed, never auto-set to max — a move can be partly unexplained) · `confidence` (deciles 0–100). `produced_mode`: **live wins** over backfill. The realized share is **never stored, never shown to the predictor** (PIT). Verdict key = `+producer`.
- **Deliberately NOT fields** (don't re-add): `mid`, `usd_per_share`, `unit_raw`, `accounting_basis` (it's in the name), free-text `qualitative`.

### 3e. Core tensions → how each was resolved
| Tension (recurring) | Resolution |
|---|---|
| Specific vs generic name | **Err SPECIFIC.** Breadth comes from reuse + read-time retrieval, never a coined generic. (`revenue_demand` killed v2.) |
| Add a family/ontology/route/`kind` tag for peers? | **No.** Producer-agnostic. Peer grouping = retrieval (industry + embeddings), never identity. |
| Seed a DriverUpdate "for free" at build / only if >2 events? | **No.** Build = class only; producers create facts; a single event is valid. |
| Per-X & accounting basis: in the NAME or a unit/field? | **In the NAME.** No per-X unit, no `basis_norm` field. **All source-stated per-X (business + physical) → name**; not stated → bare; a different per-X = a different Driver. |
| Cheaper models for Refute / readers / clerks? | **Rejected.** Refute is the last over-merge defense; reader recall loss is unrecoverable; clerks unsafe as a bundle. |
| Fable reader expiring → Opus drops recall? | Swap + 3 prompt lines + a 2-pass re-read (Opus has positional coverage **dead-zones**, not a judgment gap). |
| Incremental append to save tokens | Needs a **verdict memory** — the merge secretly re-pays the full judge bill. Old↔old frozen; judge only the new seam. |
| `weightage` = share summing to 100%? | **No — independent force**; share derived at read time. Sum-to-1 broke in 9/20 stress cases. |
| Unify Guidance: migrate or regenerate? | **Regenerate** (live nodes are disposable). Node label `:GuidanceUpdate` vs `:DriverUpdate` still **open**. |
| Import RavenPack's 7,400 categories as vocabulary? | **No — recall CHECKLIST only** (closed vocab = v1's death). Borrowed only the `rumored`/`failed` states. |

---

## 4. Still open (don't build yet)
- **The honesty/fitness gate has never run** — *does same-name actually emerge across companies, and do fresh events reuse correctly?* This is the real test; everything green so far is mechanical. **0 nodes built.**
- **DriverUpdate number/magnitude + EXPLAINED_BY layer:** agreed in principle, **not locked**, not built.
- **`fact_scope` quote-hash** is the one spot where AI judgment touches identity — prefer code-built `{period, basis}`; harden before build.
- **Guidance unify:** the node-label fork (L1 `:GuidanceUpdate` / L2 `:DriverUpdate` / L3 dual-label) and whether to amend §0 for guidance class-coining — decide **before** any build.
- **`MAPS_TO_GUIDANCE` resolver:** measured ~98–100% precision but restaurant-only; nothing built; 4 owner decisions pending.
- **Driver-ID methodology** (reuse Guidance's slot-ID recipe?) and **amendments handling** — owner questions in `Consolidation/Personal.md`.
- **Units:** re-run the 115-case probe with the corrected per-X expectations (the 94% is stale; `run_probe_hints.py` shows 7 false failures); add a naming-lint, then wire the producer. Open enum question: add **`percent_qoq`**?
- **`company_confirmed` tag** — proposed as a property-only enum (never in the key); suggestion only.
- **Production duplicate-repair path** (suggest → Refute → SAME_AS) is required before steady-state production trust.
- **First seed run** is frozen at 32/969 menus — resume before the calibration verdict.
- **The old restaurants catalog is names-only** (built pre-`fact_type`, pre-final-per-X, Fable reader) → must be **re-created / upgraded** to match `WIP/DriverGraphSchema.md`. The build plan (`HierarchicalCatalogPlan.md`) + its prompts (`menu_build.js`, `reconcile.js`) + naming authority (`DriverOntology.md`) all need the new `fact_type` step + per-X/basis rules wired in.
