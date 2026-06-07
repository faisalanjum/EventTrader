# Driver Experiment — run / resume guide

Operator guide for building **ONE shared Driver catalog** (used by all producers), industry by industry,
scaling toward ~1000 companies. This file = the WHY + the repeatable procedure + the reusable scripts + status.
For the full spec, read the two canonical files first:

- **`Drivers.md`** — the design, the creation process (G1/G2 gates), the experiment, the honesty gate.
- **`DriverOntology.md`** — the naming rules (a Driver name = one specific, reusable noun).

---

## Why these decisions (don't re-litigate)

- **v1 and v2 both died the same way:** the producer made an **unanchored semantic judgment** and either
  **over-merged** (demand themes collapsed into a generic `revenue_demand`) or flip-flopped names run-to-run.
- **Root cause = two judgment moments** that rules can narrow but never remove:
  1. *"Is this already named?"* (→ synonym fragmentation if missed)
  2. *"Is this a real, specific-enough driver?"* (→ scope drift / over-broad names)
- **So the method is:**
  - **Open vocabulary** — a closed vocab scored **82%-reject**; do **not** bring it back. Names come from the source.
  - **Anchor the producer with the catalog (G1)** — reuse before create; this is what makes two LLMs converge.
  - **An independent gate (G2)** before any new name enters the one shared catalog.
- **Fail-close invariant (the safety rail):** err **specific**; **link (SAME_AS), never merge/overwrite**; merge only on
  **exact same meaning**. *Aggressive merging = the v2 collapse. A tighter rulebook = v1 overfit/over-reject.* Stay here.
- **Cross-company peer grouping = retrieval** (same-industry + embeddings) at read time, **not** a coined generic name.
  That coined-generic was the exact thing that failed; the name stays specific.
- **Hard-bad names at scale = G2's job, not code.** Peer company names + banned words are caught by the independent
  gate (R7), which runs on every new name (production too). Do **not** add deterministic name-matching code to block
  them — tickers/brands are common words (`WING`, `SHAK`, `YUM`, "shake") so it would false-positive and drop legit
  drivers (more harm than good). If the gate ever misses, reinforce the gate *prompt*, never brittle matching code.
- **Catalog is producer-agnostic → NO route bucket, NO fundamental/news split, NO `kind` tag.** A driver's only
  requirement is: a real, **reusable**, consistently-named cause (so DriverUpdates accumulate under one name — the whole
  payoff: learn → predict). "Fundamental vs news/trading" is *which producer* uses it (it lives on
  `DriverUpdate.llm_producer`), not a catalog property. So **G2 = reuse / admit / rewrite / skip**: a valid reusable
  driver is admitted (news/trading-style names too — the news producer reuses them later, or coins them live). We deleted
  `scope_route`/lanes because defining "news/trading" needs an open-ended list = the overfit trap; we dropped `kind`
  because brand-ness is already in the name and it was a writer mislabel surface.
- **Rewrite = wording only; skip by CLASS not count.** A rewrite fixes wording, never meaning. Skip only if vague /
  rule-breaking / bound to ONE specific event-date — a reusable event *class* (government_shutdown, food_safety_incident,
  goodwill_impairment) is admitted even if it appears once.
- **3-check for any reuse / SAME_AS / rewrite:** same object · same scope · same mechanism — if any is false/unclear,
  keep separate. **Both reviewers (dedup + gate) judge from each name's evidence** (quote/source/date), not the bare
  string; mixed evidence → prefer keep-separate.
- **Judgment → LLM; structure → code (never the reverse).** ALL judgment (dedup, gate, writer-merge incl. conflict
  resolution) stays in LLMs. The ONLY deterministic code is `validate_catalog.py` — it **decides nothing about any
  driver**; it just HARD-FAILS the run on self-contradiction / dropped names / dangling refs / forbidden buckets (route
  key, `kind`). "Catch, don't pray." We rejected a Python *merger* (the writer has real conflict-resolution judgment) and
  deterministic name/word matching (false-positives on brand-word tickers, per the bullet above).
- **Transport = full inline, no slice.** Workflow JS has **no filesystem**, so dedup/gate reach the writer via the prompt
  as schema-validated objects (no char cap; per-industry fits the model context — split the reconcile by batch only if an
  industry is ever too large).
- **Independent merge-skeptic (the `Refute` stage) = adversarial verification of the two FUSE decisions.** The gate is an
  independent check on the ADMIT arm, but the MERGE arm had none: `SAME_AS` (dedup proposes) and a meaning-changing
  `rewrite` (gate proposes) could silently fuse two different drivers, and the structural validator can't see meaning.
  So reconcile adds a skeptic **after dedup+gate, before the writer** that tries to REFUTE each SAME_AS link and each
  rewrite from the evidence (the 3-check); **default = keep separate**. JS then **mechanically filters** the rejected
  ones out of the writer's input — note it can't *truly* enforce (no fs → the writer writes the file), so the writer is
  told to copy the approved lists EXACTLY and the validator backstops structure. **Refuted SAME_AS → drop link** (both
  names stay separate); **refuted rewrite → parked in `unresolved_rewrites`** (not applied, not lost) — a **5th tracked
  outcome bucket** the validator counts. Scope = **SAME_AS + rewrite ONLY** (admit already has the gate; skip/drop can't fuse).

---

## The repeatable procedure (per industry, then scale)

1. **Build menu (blind, parallel)** — 1 subagent per company: pull its fiscal.ai KPIs (rewrite each to a standard
   `driver_name` — raw labels are suggestions only) + **all its non-news filings/transcripts** (real text), then coin candidate names per
   `DriverOntology.md`. Output per candidate: `driver_name` + `evidence_quote` + `source_type` + `source_id` (the event
   it was quoted from, or `fiscal_ai:<ticker>:<metric>`) + `date`. Converge then groups these (deterministic JS) into
   per-driver records `{driver_name, canonical_name, companies, evidence_refs, optional_links}`.
   *Blind/parallel is for the TEST only (measures raw convergence). Production is catalog-first (G1).*
   **Seed sources = ALL non-news company sources** (filings + transcripts + fiscal.ai KPIs). **`>2% daily_stock` is only a high-signal flag, not a filter** — nothing excluded for moving less.
   News/macro drivers accrete **LIVE in production** (reuse-or-create + G2); there is **no separate news build**.
2. **Reconcile (G1 + G2)** — embeddings surface possible matches only; for exact-same-meaning, an independent
   gate **chooses a canonical + proposes reversible SAME_AS** (never merge/delete); an **independent** model rules each name → **reuse / admit / rewrite (wording only)
   / skip**. Output: a review file.
   For any proposed SAME_AS, reuse, or rewrite, first verify all three are true: same object or metric; same scope;
   same mechanism. If any one is false or unclear, do not SAME_AS, reuse, or rewrite. Keep the names separate, admit
   separately, or skip. A rewrite may only change wording; it must not change the underlying driver.
   Then an **independent merge-skeptic** (`Refute`) tries to break each SAME_AS + rewrite from the evidence; refuted links
   drop (keep separate), refuted rewrites park in `unresolved_rewrites`. A deterministic validator hard-fails any
   structural break before the file ships.
3. **Honesty gate** — freeze the catalog → feed **fresh** events using only names/data visible on or before the event date → producer must reuse / create / skip; an
   **independent** grader scores against a **pre-written** key; **grade once** (see `Drivers.md` § Honesty gate).
4. **Human review → next industry.** Scale to ~1000 by repeating 1–3. Any rule change must be a **general principle**,
   never sector-specific examples (examples overfit — that's how v1 died).

No route/news lane and no fundamental/news split — a valid reusable driver is **admitted**; news/macro drivers are coined **LIVE** by the news producer (not in the seed). Both reviewers judge from each name's **evidence** (quote/source/date), not the bare string.

---

## Reusable artifacts (so a repeat = zero rework)

- **`workflows/resolve_driver_scope.py`** — Neo4j scope resolver: `--industry "X"` → its tickers · `--sector "Y"` → its industries · `--list`. Hard-errors on 0 results, warns on 1 ticker. Feeds menu_build's Resolve phase.
- **`workflows/menu_build.js`** — the blind per-company menu builder (Step 1): a **Resolve** phase runs `resolve_driver_scope.py --industry <args.industry>` → tickers (default Restaurants); bots coin candidates (each with a `source_id`); fetch writes sources + `sources_manifest.json` (sha256/file) into `runs/<run_id>/`; **deterministic JS grouping** writes `runs/<run_id>/seed.json` as per-driver records; a Record step writes `manifest.json` + `scope.json`. Run via **Workflow** with `args={industry:'<name>'}` (returns the run_id) — no editing a TICKERS list.
- **Data facts the builder relies on (verified):** returns live as **percent-point** properties on the event→Company
  edge — `(News|Transcript)-[:INFLUENCES]->(Company)` and `(Report)-[:PRIMARY_FILER]->(Company)`; fields
  `daily_stock` (raw) and `daily_macro` (market-relative). Threshold 2% = **2.0**, not 0.02. fiscal.ai KPIs:
  `data/fiscal_ai_segments/fiscal_segments.sqlite`, `section='Key Performance Indicators'` (no sqlite3 CLI → use python3).
- **`workflows/reconcile.js`** — Step-2 reconcile = dedup (canonical + reversible SAME_AS, **brand ≠ generic**) ‖ the G2 gate (admit/rewrite/skip) → a **`Refute` merge-skeptic** (refutes each SAME_AS + rewrite from evidence; refuted SAME_AS dropped, refuted rewrite → `unresolved_rewrites`; JS filters rejects out of the writer's input) → writer (assembles per-driver records: sets canonical_name + skips/unresolved side-lists) → the Validate phase (writes `validation.txt`). Run via **Workflow** with `args={run_id:'<run_id>'}` (the exact menu_build run, never "latest"); reads `runs/<run_id>/seed.json`, writes `catalog.json` there.
- **`workflows/validate_catalog.py`** — deterministic post-reconcile **validator** (zero judgment, HARD-FAIL) on the per-driver record shape, applied to **BOTH the seed and the catalog**. Per-record integrity (both): evidence_refs non-empty · `companies == distinct(evidence_refs.company)` with no dups · each ref has company/source_type/source_id/quote (+ date unless KPI). Seed-only: `catalog` is a NON-EMPTY list · entries well-formed · unique driver_name · every record self-canonical. Catalog-only: uniqueness · `canonical_name` → a SELF-canonical record (coined, no chains) · completeness (every seed name once across catalog/skips/unresolved) · provenance (no invented names) · evidence-drift (catalog ref == seed ref, incl. quote) · side-list fields · forbidden route/`kind`. Runs as `reconcile.js`'s final Validate phase; also `validate_catalog.py <seed> <catalog>`.
- **`workflows/gate.js`** — **G2** standalone (independent admission gate: reuse / admit / rewrite / skip). Reusable in LIVE production per new name + inside reconcile. `args = {candidates:[{driver_name, evidence_refs:[{company,source_type,source_id,date,quote}]}], catalog}` — judges from each candidate's evidence, not the bare name.
- **`workflows/catalog_first.js`** — **G1** standalone (catalog-first reuse: nearest visible names → reuse / create / skip). Reusable in production + the honesty gate. `args = {events, catalog}` where `catalog` is the already-retrieved visible names for that event.
- **`runs/<run_id>/`** (one per industry; run_id = `<UTC-timestamp>_<slug>`): `seed.json` = `{ catalog:[per-driver records], analysis }` (raw, all self-canonical) · `catalog.json` = `{ catalog:[records w/ canonical_name], skips[], unresolved_rewrites[], counts }` (reconciled) · `manifest.json` (args·git commit·tickers·seed counts) · `scope.json` (resolver output) · `sources_manifest.json` (sha256 + count + bytes per source file) · `validation.txt` (validator output) · `sources/<TICKER>.json` (raw dumps, **git-ignored**). All committed except `sources/`. (Read-only Neo4j during calibration.) Each record = `{driver_name, canonical_name, companies, evidence_refs:[{company, source_type, source_id, date, quote}], optional_links}`; `source_id` = the Neo4j event id (or `fiscal_ai:<ticker>:<metric>`) so date/company/return derive from it. Production `Driver` node stays small (name + edges); evidence lives on `DriverUpdate→event`.

---

## Status (2026-06-06)

- **Method locked for clean-slate rerun → all Restaurants outputs DELETED.** Removed
  the old flat `_menu_restaurants_*.json` / `_sources_*.json` — outputs built mid-change
  would mislead; new outputs land in `runs/<run_id>/`. **Run from scratch** (`menu_build.js` args={industry:'Restaurants'} → `reconcile.js` args={run_id}) so the FIRST
  Restaurants result reflects the EXACT process we scale to every industry. **No partial re-run while still changing the method.**
- **Pipeline shape (locked so far):** seed = **ALL non-news sources** (real text; `>2%` = flag) → `menu_build.js`
  (content-aware; prior run gave a ~250-name menu, convergence held, narrative drivers surfaced — to be regenerated).
  Reconcile = dedup (reuse arm) ‖ **G2 `admit/rewrite/skip`** (enum-locked; **no route, no kind, no fundamental/news
  split**; both reviewers judge from **evidence**; **no slice**) → **`Refute` merge-skeptic** (breaks bad SAME_AS +
  meaning-changing rewrites; refuted SAME_AS dropped, refuted rewrite → `unresolved_rewrites`) → writer (assembles
  per-driver records: sets canonical_name + skips/unresolved side-lists) → `validate_catalog.py` HARD-FAILS any
  structural break (uniqueness · companies==distinct(refs) · ref-fields · canonical→self-canonical · completeness ·
  provenance · evidence-drift vs seed · side-list fields · forbidden route/kind). **Record-shape build done + dry-run-proven 2026-06-06; not yet pipeline-run.**
- **THEN — honesty gate (Step 3):** freeze the clean catalog → **fresh** events → reuse / create / skip (G1 =
  `catalog_first.js`, G2 = `gate.js`); **independent** grade vs a **pre-written** key; **grade once**. Then a 2nd industry. Then scale.

## Cost guard
Workflow subagents run **in-session (subscription)**. Embeddings = OpenAI (cheap, separate key). **Never** use
`claude -p` / `claude_agent_sdk` (metered).
