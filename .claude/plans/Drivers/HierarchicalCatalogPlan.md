# Hierarchical Driver-Catalog Build — Locked Plan

**Status:** decisions LOCKED + **owner-confirmed** (2026-06-09); final audit + 6 review passes applied (§10–§11) → internally consistent + fully defined. Chunking is foundational → built in **Phase 0.5** (§6).
**Scope:** how we build ONE global Driver catalog by consolidating bottom-up — Company → Industry → Sector → Global — reusing the same `reconcile` pipeline at every level.
**No code is written from this plan until the owner approves.** This file is the spec.

> Read `DriverExperiment.md` "Primary priorities / North Star" first — this plan serves it. Nothing here changes the existing locked design; it ADDS the hierarchical consolidation and the safety guards it needs.

---

## 0. Plain-English summary (crux)

We build the catalog from the bottom up, like merging folders:

```
                         GLOBAL catalog                 ← merge all SECTOR catalogs
                   = reconcile( all sector catalogs )
                    ▲            ▲            ▲
              SECTOR catalog (one per sector)           ← merge that sector's INDUSTRY catalogs
              = reconcile( its industry catalogs )
                 ▲        ▲        ▲
           INDUSTRY catalog (one per industry)          ← TODAY: blind bots + reconcile
        = menu_build (blind bot per company) + reconcile
              ▲     ▲     ▲
            co.   co.   co.                             ← leaf: each company named blind
```

- **Generation happens ONCE, at the leaf** (a blind bot per chunk file coins candidate names — one bot per company when small, several for a big filer) — *one narrow exception: the D5 homonym split (§3c) re-specifies a name above the leaf, drawn from that company's own evidence.*
- **Consolidation (`reconcile`) happens at EVERY level up.** The same dedup → gate → Refute → validate runs each level; only the *units* change (companies → industries → sectors).
- **The merge rule is bounded context:** keep every AI step small enough to judge carefully. Tiers are just batches; split smaller whenever a step is too big.
- **Worst failure = a wrong merge** (it becomes a false cross-company read-through → a bad trade), so every merge is fail-close (default keep-separate) and every merge is **approved by AI + Refute, then assembled AND structurally checked by code** (code checks approval + losslessness, never semantic truth — §11.19).

---

## 1. Locked decisions (the full list)

| # | Decision | Status |
|---|---|---|
| **D1** | **Fix the inner loop first — fusion-approval check.** A new mechanical validator check: for any record where `canonical_name != driver_name`, that exact `(driver_name → canonical_name)` link MUST be in the Refute-approved SAME_AS/rewrite list. Code checks *that the link was approved*, never *meaning*. | LOCKED |
| **D2** | **Bounded-context tree consolidation, not streaming.** Default run = Company → Industry → Sector → Global. **Sector is NOT hard-coded mandatory**: allow Industry → Global if small; **sub-split any step that's too big** (e.g. sector-batch → global-part → final-global). Run 3-level by default for the audit trail. The real rule is *keep each reconcile small enough to judge*. | LOCKED |
| **D3** | **Same `reconcile` pipeline at every level:** combine → dedup (same-meaning) → G2 gate → Refute → write → validate. **Only the company (leaf) level does raw extraction / name generation.** Higher levels only consolidate — *with one narrow exception* (D5 homonym split). | LOCKED |
| **D4** | **Carry prior SAME_AS links forward.** Lower-level links are preserved; higher levels **do not reopen or break** an approved link automatically. Higher levels only **add** new cross-industry / cross-sector links. **No human in the loop:** the automated pipeline NEVER breaks a link and never waits on a person — a link always carries forward (fail-closed). A wrong link can only be corrected by editing the committed artifacts out-of-band; the build never depends on it. | LOCKED |
| **D5** | **Same exact `driver_name` across children → SAME-NAME REVIEW** (NOT a silent auto-merge). Code finds identical names; the AI judges from a **representative evidence view** (§11.17; full evidence stays stored + validated): **SAME → Refute-confirmed union · DIFFERENT → split into more-specific source-grounded names + an explicit evidence-assignment map (§11.6), must pass G2/Refute · UNCLEAR → park as unresolved** (no rename, no merge). | LOCKED |
| **D6** | **Different names that may mean the same → `reconcile`** (dedup + Refute before any SAME_AS). e.g. `guest_count` vs `customer_transactions`. | LOCKED |
| **D7** | **Fewest blind bots; never drop text.** Default = one blind bot per company. *How = LOCKED (§8): measured ~62% clipping → `fetch` emits FULL content (caps REMOVED); `chunk_company_sources.py` splits at NATURAL boundaries — company-level + event-level (whole Q&A exchanges / sections), never mid-sentence; bot-per-chunk; Converge combines; HARD-FAIL on chunk-not-processed or missing event-part; part-tracking in manifest only (record unchanged).* | LOCKED |
| **D8** | **Fold validator (new).** After the deterministic combine builds a parent, code HARD-FAILS unless: (a) **every child `driver_name` is accounted for EXACTLY ONCE** — as a self-canonical parent record, OR in some record's `same_as_variants`, OR in `skips[]`/`unresolved_rewrites[]`/`unresolved_same_name[]`, OR present as a `from` name in the D5 split-map (full set in §11.2); (b) each parent record's evidence = the exact 5-tuple set-union of its children's evidence (nothing lost or duplicated) — **and for a D5 split, the `from` name's evidence is PARTITIONED across its split records per the assignment map, every `from`-ref assigned exactly once (§11.6)**; (c) `companies` = distinct over that union; (d) `same_as_variants` matches the actual links. Read-only, additive, fail-loud, zero judgment. | LOCKED |
| **+** | **`same_as_variants` field** on each canonical record = the list of variant names linked to it, so trading reads the whole same-as group in **one hop** (no tree-walk). A mirror of links that already exist; adds no new facts. | LOCKED |

**Two key clarifications from the discussion:**
- **D4 — what may change at higher levels:** *grouping* (which names are "the same") carries forward, never reopened. *New cross-cluster merges* are allowed/required (that's the point of the fold), and pass dedup→Refute. The canonical *label* (the pointer) may be **recomputed deterministically** (no AI) if desired — cosmetic only, never changes membership.
- **D5 — the narrow exception to "no name generation above the leaf":** the ONLY naming allowed above the leaf is the source-grounded homonym split, and only after a same-name review proves DIFFERENT, and the new names must pass G2/Refute.

---

## 2. The pipeline, level by level (exact procedure)

### 2a. LEAF — Company → Industry catalog (today, + hardening)

1. **Resolve** — `resolve_driver_scope.py --industry X` → tickers + a `run_id`.
2. **Fetch** — `fetch_company_sources.py --run-dir` → all non-news sources per company, emitting **FULL structured content** (caps removed, D7/§8; sha256-pinned in `sources/`). Then a **Chunk** phase (`chunk_company_sources.py`) writes bounded `chunks/` — splitting big companies + giant events at natural boundaries.
3. **Menus** — one **blind** bot **per chunk file** → candidate `driver_name` + `evidence_refs` (each `{company, source_type, source_id, date, quote}`), tagged with the company ticker. *(A company's chunks/parts re-union at Converge.)*
4. **Converge (deterministic JS)** — group by **lower-cased** `driver_name` → one self-canonical seed record per name; union `evidence_refs` (dedup by the 5-tuple); `companies = distinct(evidence.company)`. **Write `seed.json` with code** (not via an LLM).
5. **Reconcile** — dedup (same-meaning SAME_AS) ‖ G2 gate → Refute → **deterministic JS assembles `catalog.json`** (a thin agent writes it byte-for-byte, E2 — §11.19) **+ `approved.json`** (the Refute-approved links); sets `canonical_name` + `same_as_variants`. *(High-blast fusions get a 2nd AND-voted Refute — §11.18.)*
6. **Validate** — `validate_catalog.py seed catalog approved.json` → HARD-FAIL on any structural break, **including the D1 fusion-approval check**.

→ Output: an **Industry catalog** (records + `same_as_variants`, `approved.json`, `validation.txt`), pinned by git commit + source sha256.

### 2b. HIGHER LEVELS — Industry→Sector and Sector→Global (the fold; NEW)

Same `reconcile`, but the **input is built by a new deterministic combine step**, and a **same-name review** sits in front of it.

1. **Combine part A — `fold_catalogs` collapse + queue (deterministic, zero AI):** take N child catalogs → for each child resolve every SAME_AS cluster to its self-canonical **representative**, **union all variant `evidence_refs` onto the rep** (dedup by the 5-tuple), recompute `companies`, **carry the cluster's variant names into `same_as_variants`** (D4), and **drop `skips[]`/`unresolved_rewrites[]`/`unresolved_same_name[]`** (fail-close; the trail stays in the committed child catalog). Then group reps **across children by lower-cased `driver_name`**: a name in only one child passes through; an **identical name in ≥2 children is NOT merged — it is pushed to the SAME-NAME REVIEW queue**, each child's evidence labelled (D5). **No parent seed is written yet.**
2. **Same-name review (AI) — D5:** for each queued collision, judge from the evidence → **SAME** (a union proposal — an independent **Refute** must then fail to break it, else it falls to UNCLEAR; fail-close) · **DIFFERENT** (propose more-specific source-grounded names + the evidence assignment map) · **UNCLEAR** (mark park). Writes final post-Refute verdicts to `same_name_review.json` = reviews + split-map + assignments (§11.6).
3. **Combine part B — assemble the parent `seed.json` (deterministic, code):** apply the review — SAME → one Refute-confirmed unioned record (5-tuple-union evidence, recompute `companies`); DIFFERENT → split names as separate records using the assignment map (they must still clear G2/Refute in step 5); UNCLEAR → `unresolved_same_name[]`. Merge `optional_links` per key (**identical → keep; conflict → null + note**, never silently pick — §11.7). Flatten chains to a STAR; sort catalog by name + evidence by the 5-tuple. Write the seed in **leaf shape + `same_as_variants`** (§11.5).
4. **Fold validator (deterministic) — D8:** confirm nothing was dropped or lost (a–d; accounting set §11.2). HARD-FAIL otherwise.
5. **Reconcile (same pipeline) — D6:** dedup proposes new cross-child SAME_AS for **different** names that mean the same → G2 → Refute → deterministic JS assembly writes `catalog.json` + `approved.json` (+ `same_as_variants` updated). *(DIFFERENT-split names are gate/Refute-validated here before entering the catalog.)*
6. **Validate** — `validate_catalog.py` incl. D1 fusion check + the `same_as_variants` check + the D5 provenance / `unresolved_same_name` accounting (§11.3).

→ Output: a **Sector catalog** (then a **Global catalog** by repeating with sectors as the children).

**Why this is safe:** the combine is pure code and *never invents a merge of its own* — it only collapses links Refute already approved and routes identical-name collisions to review. New merges only happen through dedup→Refute (fail-close) or the Refute-confirmed same-name decision. An **unapproved or lossy** merge cannot pass `validate` (D1 + D8); a semantically-wrong-but-approved merge is **guarded — not provably blocked —** by AI review + Refute + fail-close.

---

## 3. New components (exact specs)

### 3a. `approved.json` + fusion-approval check (D1) — *do this FIRST*
- **`reconcile.js`** writes `<run_dir>/approved.json` = `{ "same_as": [{variant, canonical}], "rewrites": [{from, to}] }` (the `survivingLinks` / `appliedRewrites` it already computes).
- **`validate_catalog.py`** takes an optional 3rd arg `approved.json`. New check: for every catalog record with `norm(canonical_name) != norm(driver_name)`, the pair must appear in `approved.same_as` (variant→canonical) OR `approved.rewrites` (from→to) — else HARD-FAIL. Pure set membership, zero judgment.
- Runs at **every** level (leaf + every fold) automatically, since every level runs reconcile + validate.

### 3b. `fold_catalogs` (NEW deterministic combine) — see §2b step 1
- Pure **JS** (§11.13), no AI, no new merge judgment. Mirrors `menu_build`'s Converge, one level up. Numbered algorithm in §11.7.
- Outputs: the parent `seed.json` + the same-name-review queue + (later) `unresolved_same_name[]`.
- Deterministic: sorted everywhere; reproducible given the same child set.

### 3c. Same-name review (D5)
- Input: one normalized `driver_name` present in ≥2 children, with a **representative view** of each occurrence's evidence (§11.17; full evidence stays stored + validated).
- AI verdict: **SAME → an independent Refute must confirm the union** (it tries to BREAK it; can't-refute → union, refuted-or-missing → UNCLEAR; a **high-blast** union gets a 2nd AND-voted Refute — §11.18; the merge direction is the dangerous one) · DIFFERENT → split (more-specific names **drawn only from the existing evidence**, then G2/Refute) **+ an evidence-assignment map (§11.6): which child/refs → which new name** (default per `child_run_id`; code applies it to ALL refs; D8 verifies every `from` ref is assigned exactly once) · UNCLEAR → park.
- The **only** name-generation allowed above the leaf. Rare (the ontology already pushes specific names, so true homonyms are uncommon).

### 3d. Fold validator (D8)
- Extend `validate_catalog.py` with a **fold mode** (CLI in §11.9). Checks D8 (a–d) above — accounting unit = **names**, exact set in §11.2. **Required validator changes so D5 can't crash it (§11.3):** (1) PROVENANCE must accept D5-split target names (read the split-map, like `approved.json`) — they are legitimately non-seed; (2) COMPLETE must count `unresolved_same_name[]`. HARD-FAIL on any break. Read-only, additive, fail-loud.

### 3e. `same_as_variants` field
- On every self-canonical **CATALOG (output) record**: `same_as_variants: [names]` = all variant names linked to it, accumulated across levels.
- Written by: deterministic JS catalog assembly in reconcile (from `approved.json`); `fold_catalogs` (carry-forward + merge); higher reconcile (new links). Kept honest by the fold validator (d).
- **Provenance** (which child/industry each record came from) is **derivable** from `evidence_refs[].company` → its industry/sector — no separate field needed unless we choose to materialize it.

---

## 4. File-by-file changes

**NEW files**
- `workflows/fold_catalogs.js` — deterministic combine (§3b, algorithm §11.7) + the same-name-review step (§11.6) as a wrapper.
- `workflows/chunk_company_sources.py` — derived chunk layer (§8): the layered-fallback chunker → `chunks/` + `chunks_manifest.json`.
- `workflows/build_tree.js` (orchestrator) — **built in Phase 1**, minimal: **(i)** takes **explicit child `run_id`s** (no "latest", **no discovery-fold**, **no meaning**) and runs leaf → fold → reconcile → validate in order, **every step fail-closed**; **(ii)** ships a **READ-ONLY `--list` reader** that builds the Company→Industry→Sector tree from `resolve_driver_scope.py --list` **plus one join query** (`MATCH (c:Company) RETURN c.sector, c.industry, c.ticker` — `--list` alone returns only flat lists with NO edges) and **prints it for audit/calibration visibility only** (never a human production gate — no human in the steady-state loop, §5) — it does **NOT** auto-fold. **Phase 2 EXPANDS the same file** to WALK-AND-FOLD that tree with bounded-context batching (§2b, D2, **§11.20**).

**CHANGED files**
- `workflows/fetch_company_sources.py` — (D7/§8) **remove the per-sub-unit/count caps; emit FULL structured content** (the `qa_exchanges[]` / `sections[]` lists it already builds); **sort Q&A by `toInteger(qa.sequence)`** (numeric, not string); add a last-resort `clipped` field.
- `workflows/menu_build.js` — (E1) **lower-case** the Converge grouping key; (E2) write `seed.json` **with code, not an LLM agent**; (D7) add a **Chunk phase** + **one blind bot per chunk file**.
- `workflows/reconcile.js` — write `approved.json`; deterministic JS assembles `catalog.json` and populates `same_as_variants`. Consumes parent seeds unchanged (same shape).
- `workflows/validate_catalog.py` — add `approved.json` 3rd arg + D1 fusion check; add D8 fold-mode checks (CLI §11.9); add `same_as_variants` consistency check; **+ D5-split-name provenance + `unresolved_same_name[]` accounting (§11.3)**.
- **Record shape** — add `same_as_variants: []` (see §9).

**UNCHANGED / reused as-is**
- `resolve_driver_scope.py` (already has `--list`), `gate.js`, Refute logic, and the dedup/gate prompts — reused at every level. The old LLM writer prompt is replaced by deterministic JS assembly (§11.19).

---

## 5. Invariants & fail-close guarantees (must always hold)

- **Fail-close:** a missing or refuted verdict NEVER fuses; default keep-separate; UNCLEAR parks. Looping/folding can only ADD skeptic-survived structure, never relax it.
- **Judgment → LLM, structure → deterministic code.** `fold_catalogs`, both validators, and Converge decide nothing about meaning; they only union, count, set-compare, and HARD-FAIL.
- **An unapproved or lossy merge cannot ship.** D1 (every fusion's `canonical_name` must be in the Refute-approved set) + D8 (no record/evidence lost in the combine) make THAT a CODE invariant. *Code proves structure (approved + lossless), not meaning* — the residual risk of a semantically-wrong-but-**approved** merge is **minimized, not eliminated**, by independent AI review + Refute + fail-close defaults — **deepened on the highest-blast fusions by a second AND-voted Refute + an adversarial evidence view (§11.17/§11.18)**. And because the catalog is **assembled in deterministic JS** (§11.19), the writer **cannot fabricate** an unapproved `canonical_name` — the fusion hole is structurally closed; D1 is belt-and-suspenders.
- **SAME_AS is reversible; never a destructive merge.** *Reversible* = the link can always be undone and the originals reconstructed. At the **leaf**, both records survive in place. At a **fold**, the variant collapses to a NAME in `same_as_variants` (its evidence unioned onto the rep) and its full record stays recoverable from the committed child catalog. Trading reads the cluster via `same_as_variants`.
- **No new drivers above the leaf**, except the narrow source-grounded homonym split (D5).
- **Reproducible:** pinned git commit + source sha256 + a snapshot of the sector/industry taxonomy used; deterministic (sorted) fold. *(Note: the generated candidate NAMES are LLM output — the pipeline is reproducible; the exact vocabulary a re-run coins is not.)*
- **Cost:** all AI runs **in-session (subscription)**; embeddings (if ever) are OpenAI + suggest-only. NEVER `claude -p` / `claude_agent_sdk`.
- **Read-only Neo4j** during calibration.

---

## 6. Build order (exact sequencing)

**Phase 0 — Inner-loop hardening (preconditions; before any fold):**
1. `reconcile.js` writes `approved.json`.
2. `validate_catalog.py`: `approved.json` arg + D1 fusion check.
3. `menu_build.js`: lower-case Converge key (E1) + deterministic `seed.json` write (E2).
4. `reconcile.js` deterministic JS assembly populates `same_as_variants`; validator checks it.
5. **Re-run the leaf on the calibration industry; confirm GREEN.**

**Phase 0.5 — Chunking (foundational — the whole catalog depends on the leaf seeing full text):**
1. `fetch_company_sources.py`: remove ALL caps → emit FULL structured content; sort Q&A by `toInteger(qa.sequence)`; add the defensive `clipped` field (§8 step 2).
2. New `chunk_company_sources.py`: the layered-fallback chunker → `chunks/` + `chunks_manifest.json` (§8 step 3 + §11.1/§11.10).
3. `menu_build.js`: Chunk phase + one blind bot per chunk file; the two reliability HARD-FAILs (chunk-processed, all-parts-present).
4. **Re-run the leaf with chunking; confirm GREEN + byte-exact conservation holds (clipped never fires).**

**Phase 1 — The fold primitive (prove the 2-level fold):**
1. `fold_catalogs` (deterministic combine + same-name queue).
2. Same-name review step (reuse gate/Refute).
3. Fold validator (D8) in `validate_catalog.py`.
4. **SEED_MAX over-size GUARD** — in `fold_catalogs.js` + `reconcile.js` (NOT `build_tree.js`), a deterministic **HARD-FAIL** when a combined seed exceeds `SEED_MAX_RECORDS` (400) OR `SEED_MAX_CHARS` (300k) **before any reconcile/AI call** (pure size compare; one code site protects explicit mode now AND `--list` later). Demonstrate it fires on a fabricated 401-record / 300,001-char seed.
5. **Minimal `build_tree.js`** — orchestrate the existing steps for **explicit child `run_id`s** (no "latest", no discovery-fold, no meaning; every step fail-closed) **+ the READ-ONLY `--list` reader** (prints the tree for **audit/calibration only — not a production gate**; fail-loud on multi-parent/orphan; does NOT auto-fold).
6. **Run the whole 2-industry fold THROUGH `build_tree.js`** (not by hand): 2 industries → leaf each → fold the two → parent seed → reconcile → parent catalog → validate. Confirm GREEN + eyeball a few merges. *(Tests the real repeatable process early, not a manual version of it.)*

**Phase 2 — Scale + bounded-context tiering (D2):**
1. **EXPAND `build_tree.js` to WALK-AND-FOLD** the discovered tree (the over-size guard already exists from Phase 1; this only adds the auto-fold of each level). Must satisfy the **§11.20** acceptance criteria.
2. **Bounded-context batching** — run the **default 3-level tree** (D2; Sector is the default batch boundary, *not* size-gated). When a step trips the Phase-1 guard, **sub-split into batches** (reconcile each → combine → reconcile again). Collapse to 2-level (Industry → Global) only in the degenerate case where the all-industries global seed already fits one reconcile.
3. Run the full tree; **measure context sizes + wrong-merge rate** — an **OUTPUT** that may *retune* the constants; the batching never reads or waits on it.

**Phase 3 — Deferred (separate plans):**
1. Honesty gate, `catalog_first.js` (G1 live-reuse) rebuild, Neo4j writes / PIT registry.

---

## 7. Out of scope / unchanged here
- `catalog_first.js` (G1 production live-reuse) — still deferred; its header flags the pending propose-first rebuild.
- Honesty gate — runs AFTER the catalog is built (separate plan).
- Embedding-based homonym detection — **rejected** (over-engineering + not 100% reliable). Same-name review (D5) replaces it. Embeddings stay suggest-only for retrieval, never a decider.
- Live production wiring, PIT registry, Neo4j writes — not part of this plan.

---

## 8. Chunking (D7) — LOCKED (revised after measuring clipping)

**Why this changed:** sampling the current graph showed today's caps clip ~**62%** of report/transcript events (~52% reports, ~**100%** transcripts). Dropping that much text is a real recall loss, so we **stop dropping text**: `fetch` emits full content, and chunking bounds each bot's load by **splitting**, never by clipping. ("Measure first" → measured → caps removed.)

**Goal:** never drop source text; keep every blind bot's reading load bounded. Touches ONLY the leaf.

1. **Originals stay the truth.** `runs/<run_id>/sources/<TICKER>.json` = the raw fetched artifact, sha256-pinned, untouched.
2. **`fetch` emits FULL structured content (caps REMOVED).** Delete the **full set** of caps — `CAP_EVENT_REPORT`, `CAP_EVENT_TRANS`, `CAP_SECTION`, `CAP_EX991`, `CAP_PREPARED`, **`CAP_QA_EACH`** (the per-Q&A 900-char slice — the main cause of the ~100% transcript clipping), `QA_MAX=8`, plus the `substring()`/`[..]` slices in `TRANS_Q` and the final `[:CAP_EVENT_*]` slices in `build_report_content`/`build_trans_content` — and emit each event as the natural sub-units `fetch` already builds — full `prepared`, ALL `qa_exchanges[]`, full `sections[]`, full `ex991` — with `source_id`/`source_type`/`date` intact. **Sort Q&A numerically by `toInteger(qa.sequence)`** — `qa.sequence` is stored as a STRING (`"0"`,`"1"`,`"10"`), so the current `ORDER BY qa.sequence` sorts it alphabetically and scrambles Q&A order; this is a required `fetch` fix. (Removing the caps also makes `fetch` simpler — it stops capping + joining.)
3. **New helper `workflows/chunk_company_sources.py`** (derived layer): `sources/<TICKER>.json` → `runs/<run_id>/chunks/<TICKER>__chunk_NNN.json` + `chunks_manifest.json`. Deterministic, **fewest chunks**. Neo4j confirms stable boundaries (`HAS_SECTION` / `HAS_EXHIBIT`; `PreparedRemark` + `QAExchange.sequence`) **but some single blocks are huge** (EX-99.1 ≈1.96M chars · RiskFactors ≈544k · prepared ≈183k · one Q&A ≈54k) — so natural boundaries ALONE are not enough. Use a **layered fallback ladder** that ALWAYS finds a split point, so **no text is ever dropped**:
   - **(a) company-level** — group whole small events into a chunk until the per-bot budget is reached.
   - **(b) natural unit** — split a too-large event into units: report → section / exhibit; transcript → prepared remarks / each Q&A exchange; KPI → never split.
   - **(c) paragraph** — if one natural unit is still > budget, split it by paragraph.
   - **(d) sentence** — if one paragraph is still > budget, split by sentence.
   - **(e) char range** — if one sentence is still > budget, split by char range (last resort; astronomically rare).
   - Order is preserved at every level; KPIs in `chunk_001` only; the chunker **slices bytes, never mutates them**. Because (e) always succeeds, **no text is ever dropped** — proven by the byte-exact conservation check (§8.7c); `clipped` stays only as a defensive signal that should never fire.
4. **`menu_build.js`:** add a **Chunk phase** after Fetch (runs the helper); **Menus = one blind bot per chunk file** — each bot sees either a group of whole small events OR one part of one large event, and nothing else (no other company, no catalog). The **intermediate** menu result carries its `chunk_id` + `ticker` (the `chunk_id` is matched against `chunks_manifest.json` for the processed-check in step 7 — it is **NOT** added to the final `evidence_ref`).
5. **Combine = Converge (unchanged).** A company's chunks/parts auto-union by exact `driver_name`; candidates coined in different parts re-union here. No new combine code.
6. **Part-tracking lives in the manifest, NOT the record.** `chunks_manifest.json` records `ticker, source_id, part_index, part_count, split_level (natural|paragraph|sentence|char), char-range, sha256` — proving every unit/part was produced and processed. The final `evidence_ref` keeps its locked 5-tuple (`company, source_type, source_id, date, quote`) — **no new `evidence_ref` fields, no part-tracking in the record** (part data lives in `chunks_manifest.json`). *(The record does gain `same_as_variants` — that is the read-through field, unrelated to chunking; see §9.)*
7. **Reliability HARD-FAILS (deterministic):** (a) every `chunk_id` in `chunks_manifest.json` appears in a returned menu result (closes the `.filter(Boolean)` gap — no chunk silently dropped); (b) for any split event, **all parts `1..part_count` are present**; (c) **byte-exact conservation** — for every event, the ordered concatenation of its parts **equals the original event text** (compared by hash; **NO whitespace normalization** — the chunker *slices*, never mutates bytes); HARD-FAIL otherwise. This is the real no-text-loss proof; the `clipped` flag stays only as a defensive signal that, given rung (e), should never fire.
8. **No semantic decisions in chunking** — it only splits text and preserves evidence. G2/Refute still own naming validity + SAME_AS.
9. **Tradeoff accepted:** a split event = a bot sees only part of it (minor cross-part context loss), mitigated by natural boundaries + Converge re-union + a **generous per-bot budget** so splitting fires only for giant 10-Ks. Far better than dropping 62% of the text.

**Cost:** full content = more chunks = more bots (in-session, parallel, bounded). Keep the per-bot budget **high** to minimize chunk count.

**Higher-level batching = the SAME rule (D2/D8):** if any industry/sector/global combine is too big → split child catalogs into batches → reconcile each → combine → reconcile again. **Atomic unit = one *event-part* at the leaf, one *Driver record* above.** Every combine validator-checked (D8).

**Recall floor (fold in here):** warn/flag if a company with non-trivial source text yields 0 candidates.

**Build timing:** **Phase 0.5** (§6) — foundational, right after the Phase-0 leaf hardening (the whole catalog quality depends on the leaf seeing the full text).

---

## 9. Final record shape (catalog record)

```jsonc
{
  "driver_name": "...",
  "canonical_name": "...",                 // == driver_name for a self-canonical record; else an approved link target
  "companies": ["..."],                    // == distinct(evidence_refs.company)
  "evidence_refs": [
    {"company":"...", "source_type":"...", "source_id":"...", "date":"...", "quote":"..."}
  ],
  "same_as_variants": ["..."],             // NEW: variant names linked to this canonical (read-through cluster)
  "optional_links": { "xbrl_concept": null, "xbrl_member": null, "guidance_ref": null }
}
```
Side-lists on a catalog: `skips[]` = `{driver_name, why}`, `unresolved_rewrites[]` = `{driver_name, proposed_to, why}`, `unresolved_same_name[]` = `{name, occurrences:[{child_run_id, evidence_refs}], why}` (§11.4), and (fold only) `optional_links_conflicts[]` = `{driver_name, key, values}` (§11.7). Catalog-level fields (not per-record): `scope_name` + `scope_level` (§11.8). Written next to each catalog: `approved.json`; at fold levels also `same_name_review.json` (verdicts + split-map, §11.6) and `fold_manifest.json` (per-child kept/dropped counts, §11.16).

---

## 10. Final-audit status (2026-06-09)

A 5-agent adversarial audit verified **every code claim** and confirmed the plan's substance + North-Star alignment (fail-close, judgment→LLM/structure→code, reversible SAME_AS, D1–D8). It found **2 blockers, 1 slot contradiction, and ~10 undefined values** — **all resolved**:
- **Blocker 1 (validator would crash on D5):** the unchanged `validate_catalog.py` HARD-FAILS any non-seed name and ignores `unresolved_same_name[]`, so every legitimate D5 split / UNCLEAR-park would crash it. → fixed in §3d + §11.3 (Phase-1 precondition).
- **Blocker 2 (D8(a) contradicted the fold):** "every child driver appears exactly once / nothing dropped" clashed with the fold dropping skips/unresolved, collapsing variant *records* into *names*, splitting, and parking. → reworded to a **names**-accounting set (§1 D8 + §11.2).
- **Slot contradiction:** chunking was simultaneously LOCKED, OPEN, and Phase-3-deferred. → resolved to **Phase 0.5** (§6); status line + §8 aligned.
- **~10 undefined values** → pinned in §11. Items needing an **owner number/choice** are tagged **[OWNER]** with a recommended default already applied.
- **Second review pass (independently verified against the code):** 10 more items checked — **2 were already fixed** (chunking-slot, D8 accounting); **8 applied:** sector default → default-3 + size sub-split (§6.2/D2); no-human wording (D4); **same-name-review ORDER** now explicit (§2b: collapse+queue → review → assemble seed); SAME_AS survival = reversible-via-recoverable (§5); the `same_name_review.json` split-map approval artifact (§11.6); `optional_links` conflict → null+note, never silent-pick (§11.7); `chunk_id` in the intermediate menu result for the processed-check (§8.4/§8.7a); + a reconcile evidence-view cap (§11.17).
- **Third pass + owner confirmation (2026-06-09):** the two real residuals fixed — a `SEED_MAX_CHARS` cap alongside the 400-record cap (no AI overload, §11.11) and child drops recorded in `fold_manifest.json` (no silent loss, §11.16); plus the final `driver_name` = lowercase normalized form (§11.14) and `unresolved_same_name` explicitly excluded from trading (§11.4). All 6 owner settings **confirmed**.
- **Fourth pass + final consistency sweep (2026-06-09):** 3-agent sweep = **READY-TO-BUILD, zero blockers** (4 cosmetic nits fixed). 5 more applied: same-name **SAME → independent Refute-confirm, fail-close** (the union is a fusion — §2b/§3c/§11.6); the "wrong merge cannot ship" **overclaim corrected** to *unapproved/lossy only — semantic risk minimized, not eliminated* (§5/§2b); the 20-ref evidence cap **also covers the same-name review** (§11.17); + docs: README now lists this plan, and `DriverExperiment.md` "no char cap" → bounded-context caps, "Human review → next industry" → calibration-only/hands-off-at-scale.
- **Fifth pass (2026-06-09):** 2 blockers + 2 wording — D5 DIFFERENT split now carries an explicit **evidence-assignment map** (`assignments:[{child_run_id, to, evidence_ref_keys?}]`, §11.6) so code partitions evidence deterministically and **D8 verifies every `from`-ref is assigned exactly once** (§11.2 / D8(b)); §11.12 corrected — same-name review uses **Refute on SAME** + gate+Refute on DIFFERENT (was stale, a contradiction introduced in pass 4); D5/§3c "all evidence_refs" → "representative view" (§11.17); §0 "checked by code" → "approved by AI + Refute, structurally checked by code".
- **Sixth pass — simplify + improve audit (14 roles), suggestions folded (2026-06-09):** verdict = **NOT over-engineered**; ONE substantial reliability upgrade adopted. Applied: **(a)** blast-radius-gated **2nd Refute, AND-only** on fusions spanning ≥8 companies / ≥2 sectors (§11.18, owner #7); **(b)** the 20-ref view made **deterministic + adversarial** — spread + force-include minority-cluster quotes (§11.17); **(c) deterministic JS catalog writer** — pre-resolved kept-target map + full assembly in code → **structurally closes the fusion hole**, D1 = belt-and-suspenders (§11.19), consciously supersedes `DriverExperiment.md:62`; **(d)** chunking `clipped` flag → **byte-exact ordered-concatenation == original** conservation check, no whitespace normalization (§8.7c); **(e)** `build_tree.js` — **owner override (2026-06-09): built minimal in Phase 1** (explicit child `run_id`s, no discovery / no meaning, fail-close every step — tests the real repeatable process early), **expanded in Phase 2** for the full `--list` tree (§4/§6); **(f)** `SEED_MAX_CHARS` rationale fixed — bounds transport/validator memory, not the AI view (§11.11). **Declined (so not re-proposed):** merge the fold sidecars (clearer separate) · add D5 same-ticker lanes (premature) · collapse chunking rungs (only if implementation hurts). **Rejected as v1/v2 traps:** auto-merge identical names · objective-signal collision router · Tournament for the cosmetic canonical pick · **majority** voting · dedup convergence loop · per-source-type bots · driver-richness clip-classifier · re-introducing the embedding decider.
- **Seventh pass — `build_tree.js` full-tree timing (4-agent workflow, owner Q, 2026-06-09):** verified vs **live Neo4j + code**. `--list` returns only flat `{sectors, industries}` with **no edges** (strict 11→115→796 tree). Decomposed Phase 2 into 4 pieces → **pulled into Phase 1:** the **SEED_MAX over-size guard** (deterministic; the 2-industry fold can already trip it; lives in fold_catalogs/reconcile so it guards explicit + `--list` from one site) **+ a read-only `--list` reader** (prints the tree via a join query; no auto-fold). **Stays Phase 2:** the **auto-fold (C)** — cheap to write but the **footgun** (a giant sector through one reconcile = the v2 over-merge; only toy-testable = false green) — and **measure (D)** (an output, not a build input). Froze full-tree acceptance criteria in **§11.20** so it's never forgotten. *Corrected ChatGPT's premise:* `--list` does NOT return the tree, and "build both modes now" would ship an only-abortable auto-fold. **Owner-APPROVED 2026-06-09**, with one wording lock: the read-only `--list` reader is **audit/calibration-only, never a human production gate** (consistent with no-human-in-steady-state, §5).

## 11. Resolved definitions (so a builder never guesses)

**11.1 Per-bot char budget [OWNER].** Named constant `CHUNK_BUDGET_CHARS` in `chunk_company_sources.py`. **Default = 40,000 chars** (well under one call's context; room for RULES + schema). Drives the §8 ladder. Pin it so re-runs are deterministic.

**11.2 D8(a) accounting set (names, not records).** Every child `driver_name` must appear EXACTLY ONCE across the union of: parent self-canonical records ∪ every record's `same_as_variants` ∪ `skips[]` ∪ `unresolved_rewrites[]` ∪ `unresolved_same_name[]` ∪ the D5 split-map's `from` names. (Leaf vs fold differ on purpose: at the leaf a SAME_AS variant survives as its own record; at the fold it survives only as a NAME in `same_as_variants`, evidence unioned onto the rep.) **For a DIFFERENT split, D8 also verifies the assignment map (§11.6) is a complete PARTITION of the `from` name's evidence: every `evidence_ref` (across all children) is assigned to exactly one split target — none lost, duplicated, or orphaned; each split record's evidence = its assigned refs, `companies` = distinct over them.**

**11.3 Validator changes for D5 (Phase-1 precondition).** In `validate_catalog.py`: (a) PROVENANCE = `(catalog ∪ skips ∪ unresolved_rewrites ∪ unresolved_same_name) − (seed_names ∪ d5_split_targets)` must be empty — read the D5 split-map and accept its target names as legitimate non-seed names; (b) COMPLETE accounting must include `unresolved_same_name[]`. Without these, the unchanged validator HARD-FAILS every legitimate split/park.

**11.4 `unresolved_same_name[]` shape + re-entry.** Shape `{ name, occurrences:[{child_run_id, evidence_refs:[…]}], why }`. Policy: an UNCLEAR-parked collision **MAY be re-reviewed at the next fold** (more cross-evidence may resolve it) but **NEVER auto-merges**; it is dropped from each level's combine input and lives only on the level where it was parked. Because it is OUT of the clean catalog, a parked collision is **excluded from trading signals** until/unless a later fold resolves it.

**11.5 `same_as_variants` derivation + placement [OWNER → recommended].** Leaf reconcile: `same_as_variants[C] = { v : (v,C) ∈ approved.same_as } ∪ { f : (f,C) ∈ approved.rewrites AND C kept }`, EXCLUDING any name itself skipped/parked. Placement: **present on the parent seed**, absent/empty on the leaf seed; the seed validator treats it **optional-on-leaf / present-on-parent** (so parent seed = leaf shape + `same_as_variants`). *(This is about the SEED / reconcile input; the leaf CATALOG / output record still carries `same_as_variants` per §3e/§2a.)*

**11.6 Same-name review = a NEW small step + its artifact.** No existing tool emits SAME/DIFFERENT/UNCLEAR (`gate.js` = reuse|admit|rewrite|skip; embedded gate = admit|rewrite|skip; Refute = `survives:bool`). Define a step in `fold_catalogs.js`'s wrapper that writes **`same_name_review.json`** next to the parent catalog: `{ reviews:[{collision_name, verdict: SAME|DIFFERENT|UNCLEAR, new_names?:[…], why}], split_map:[{from, to:[names], assignments:[{child_run_id, to, evidence_ref_keys?}]}] }`. The validator reads `split_map` as the **approval artifact** for D5-split names (§11.3). **`assignments` partition the `from` name's evidence to the new names: default per `child_run_id` (all that child's refs → one `to`); optional `evidence_ref_keys` (the 5-tuples) for a rare within-one-child split. Code applies the assignment to ALL refs; D8 verifies the partition is complete (§11.2).** **On SAME, an independent Refute must try to break the union (cannot-refute → union; refuted or missing → UNCLEAR) — the union is a fusion, so it gets the same skeptic as every other merge.** On DIFFERENT, the proposed split names are gate+Refute-validated in the reconcile step before entering the catalog. *(The seed is assembled AFTER this review — §2b steps 1→2→3.)*

**11.7 `fold_catalogs` algorithm (numbered, deterministic).** **Part A (before review):** (1) per child: resolve each cluster to its self-canonical rep (follow `canonical_name` to a fixpoint); union variant `evidence_refs` onto the rep, dedup by the 5-tuple, recompute `companies`; record variant names into `same_as_variants`; DROP `skips`/`unresolved_rewrites`/`unresolved_same_name`. (2) group reps across children by `norm()`'d name; a unique name passes through; a cross-child identical-name collision → the same-name-review queue (do NOT pre-merge). **→ same-name review (§11.6) resolves the queue. Part B (after review):** (3) apply verdicts — SAME → one unioned record (5-tuple-dedup evidence, recompute `companies`); DIFFERENT → split names as separate records; UNCLEAR → `unresolved_same_name[]`. (4) representative tie-break when children disagree on a cluster's canonical: **shortest standard form (R6)**, then lexicographic. (5) merge `optional_links` per key: identical non-null → keep; **conflict → `null` + record it in `optional_links_conflicts[]`** (never silently pick); children visited in sorted `run_id` order. (6) flatten chains to a STAR (`canonical_name = driver_name`); sort catalog by `driver_name`, evidence by the 5-tuple; write the parent seed.

**11.8 Parent-seed scope field.** Replace the single `industry` with `scope_name` + `scope_level ∈ {industry, sector, global}` (sector fold → sector name; global → `"GLOBAL"`). The leaf keeps `industry`; readers treat it as `scope_name` when `scope_level=industry`.

**11.9 `validate_catalog.py` fold-mode CLI.** `validate_catalog.py <seed> <catalog> [approved.json] [--fold <child1.json> …]`. At fold level `<seed>` = the folded **parent seed** (NOT a child), so evidence-drift compares parent-catalog vs parent-seed; `--fold` passes the child catalogs so D8 can compare parent vs union-of-children.

**11.10 Paragraph / sentence splitters (ladder c/d).** Paragraph = split on `/\n\s*\n/` (blank line); sentence = split on `/(?<=[.!?])\s+/`. Pinned for reproducibility; fire only past budget (rare).

**11.11 'Too big' split trigger [OWNER].** Sub-split a combined seed into batches when it exceeds **`SEED_MAX_RECORDS` (default 400)** OR its serialized evidence exceeds **`SEED_MAX_CHARS` (default 300,000 chars)** — whichever hits first. The three "too big" knobs do **distinct** jobs (none redundant): `SEED_MAX_RECORDS` = how many records one reconcile reasons over; `RECONCILE_EVIDENCE_PER_RECORD` (§11.17) = the AI **prompt view** per record; **`SEED_MAX_CHARS` = the full serialized seed the *deterministic* fold/validator transport + hold in memory — NOT the AI prompt** (the AI never reads the full seed). Both tunable; pin as constants. **The over-size GUARD (this deterministic hard-fail / sub-split trigger) is built in PHASE 1** inside `fold_catalogs.js`/`reconcile.js` (the 2-industry fold can already trip it); Phase 2 only ADDS the walk-and-fold of the discovered tree on top of an already-guarded fold step. **Batching stays Phase 2; the guard does not.**

**11.12 Which gate variant.** Fold-level reconcile uses the **embedded `reconcile.js` gate** (admit|rewrite|skip; the dedup arm supplies reuse/SAME_AS). The same-name review uses **Refute on a SAME union** (tries to break it; fail-close) **AND gate + Refute on the DIFFERENT split-target names**.

**11.13 Language.** `fold_catalogs` + the same-name-review wrapper = **JS** (reuse `menu_build`'s `byName` / 5-tuple / `norm` helpers so dedup logic can't drift JS↔Python). `chunk_company_sources` = **Python** (next to `fetch`). Validators stay Python.

**11.14 E1 — final name is the lowercase normalized form.** Group by the lower-cased key, and the record's final `driver_name` **IS** that lower-cased form (DriverOntology already mandates lowercase; a capital is a producer slip, normalized away — never preserved as a display variant).

**11.15 Recall floor.** WARN (soft, never HARD-FAIL) when a ticker with `total_content_chars ≥ 2000` yields 0 candidates — a genuinely empty filer must not block the run.

**11.16 Child skips/unresolved — recorded, not silent.** The parent OMITS dropped child `skips`/`unresolved_rewrites`/`unresolved_same_name` from the clean catalog (no bloat), but **NOT silently**: the fold writes a **`fold_manifest.json`** recording, per child, `{child_run_id, scope_name, kept_count, skips_count, unresolved_rewrites_count, unresolved_same_name_count}` — so nothing is lost or untraceable over multi-day runs; the full text trail stays in the git-committed child catalog.

**11.17 Reconcile evidence-view cap [OWNER].** A single record can accumulate huge evidence at scale (e.g. `oil_price` across hundreds of companies). The reconcile gate/dedup/Refute **and the same-name review** prompts show **up to `RECONCILE_EVIDENCE_PER_RECORD` representative `evidence_refs` per record** (default = 20). The selection is **deterministic** (reproducible) and **adversarially built**: maximize spread across **companies / sectors / source-types / dates** and **force-include minority-cluster quotes** — at scale a big merge often passes review only because the one contradicting quote was never sampled, a failure no extra skeptic on the *same* 20 refs can fix. For a high-blast fusion (§11.18), optionally take **two disjoint draws and AND** the verdicts. The **FULL** evidence stays in the seed/catalog — this caps only the *prompt view*, never the data; **D8 + the validators run on the FULL stored `evidence_refs`**, not the 20-ref subset. Bounds the reconcile context independent of record count.

**11.18 Blast-radius-gated second Refute (AND-only) [OWNER].** A leaf wrong-merge hits 2–3 companies; a global one hits hundreds + many trades — v2 died on exactly a high-fan-out over-merge. So for any proposed fusion (a dedup SAME_AS, a meaning-changing rewrite, OR a same-name SAME union) whose merged record spans **≥ `HIGH_BLAST_COMPANIES` (default 8) distinct companies OR crosses ≥ 2 sectors**, require a **SECOND independent Refute**; the fusion survives only if **BOTH** return `survives=true` (**AND-vote** — any FALSE or missing → keep separate / UNCLEAR). One Refute everywhere else, unchanged. The gate + the AND are deterministic JS over the already-computed company/sector counts. **Never majority voting** (majority would relax fail-close in the over-merge direction). Cost = one extra agent call on the rare gated fusions; pairs with the adversarial evidence view (§11.17).

**11.19 Deterministic JS catalog assembly (the writer).** The reconcile/fold writer is now pure structure — apply the skeptic-approved maps (SAME_AS / rewrites / skips / D5 assignments) by fixed precedence and copy evidence verbatim. So **assemble `catalog.json` in deterministic JS** (inside `fold_catalogs.js`/`reconcile.js`), then a thin agent writes the pre-built JSON **byte-for-byte** (the locked E2 pattern). Two parts: **(a)** JS pre-resolves, for every surviving link/rewrite, whether its canonical/target is a **KEPT name** (not skipped/parked) → the writer's old error-prone "is the target alive?" 3-list join collapses to a flat lookup; **(b)** JS applies the **5-way record precedence** (skip · approved SAME_AS · approved rewrite · park · admit-as-self-canonical) + verbatim copy. **Safety:** a deterministic writer **cannot fabricate** a `canonical_name` Refute never approved, so this **structurally closes the fusion hole** — D1 becomes belt-and-suspenders, not the sole guard. **Meaning stays with dedup/gate/Refute; only assembly moves to code.** *(Consciously supersedes `DriverExperiment.md:62` "we rejected a Python merger" — that conflict-resolution moved to the fold's deterministic `optional_links` merge (§11.7); the leaf writer is now purely mechanical.)*

**11.20 Full-tree (`--list`) mode — acceptance criteria (frozen NOW so Phase 2 is never re-litigated).** **Key code fact:** `resolve_driver_scope.py --list` returns only TWO **flat** lists `{sectors, industries}` with **no parent-child links** (verified, lines 40-43; live shape = strict **11 sectors → 115 industries → 796 tickers**, every industry→1 sector, every ticker→1 industry, zero nulls). The fold-tree's **edges live only in `--sector`/`--industry`**, so `--list` mode MUST add one join query (`MATCH (c:Company) RETURN c.sector, c.industry, c.ticker`) — **never infer edges from list position.** Criteria:
1. **Deterministic, no 'latest':** the tree derives only from static `c.sector`/`c.industry`/`c.ticker`; two runs emit a byte-identical sorted tree.
2. **Edges resolved, not guessed:** every industry attaches to exactly one sector, every ticker to exactly one industry (from the join, not list order).
3. **Strict-tree fail-loud:** any industry with >1 sector parent, any ticker with >1 industry parent, or any orphan → HARD-FAIL naming the offender (the schema does not enforce 1:1, so this guard must be coded).
4. **Over-size hard-fail before any reconcile:** every fold step (industry→sector, sector→global, sub-batch) exceeding `SEED_MAX_RECORDS`/`SEED_MAX_CHARS` HARD-FAILs (or sub-splits, once batching exists) before the seed reaches an AI call — the guard lives in `fold_catalogs.js`/`reconcile.js`, identical in explicit + `--list` mode.
5. **Every level fully validated:** each industry/sector/global emits its catalog + `approved.json` and passes `validate_catalog.py` (incl. D1 + D8 `--fold`); any single failure fails the whole run (no level auto-skipped).
6. **Default 3-level; collapse only when global fits:** Company→Industry→Sector→Global by default (Sector not size-gated, D2); collapse to Industry→Global only when the global seed already passes the size check; the branch is decided by the deterministic size check, never a hidden heuristic.
7. **Degenerate leaves handled:** a 1-ticker industry (17 exist today) WARNs (not fail); a 0-ticker industry / 0-industry sector HARD-FAILs (matching the existing exit-1 guards).
8. **Exact-match raw graph strings** (`ConsumerCyclical`, `Restaurants`) — never slugified/case-folded (slugify is output-only).
9. **Reproducible + pinned:** records the taxonomy snapshot + pinned constants + git commit; a re-run on the same graph+commit reproduces the same tree, batch boundaries, and pass/fail (LLM-coined vocabulary excepted, §5).
10. **Measure = output, not gate input:** Phase-2 step-3 metrics are emitted AFTER the run; the batching/split logic never reads or waits on any measurement file.

---

### Owner-CONFIRMED settings (2026-06-09)
1. **Per-bot budget** = 40,000 chars (§11.1) — ✅ confirmed.
2. **'Too big' trigger** = 400 records (`SEED_MAX_RECORDS`) **AND** `SEED_MAX_CHARS` = 300,000 (§11.11) — ✅ confirmed. `SEED_MAX_CHARS` bounds the **full serialized-seed transport + deterministic fold/validator memory**, NOT the AI prompt (the AI view is the 20-ref cap, #3).
3. **Reconcile evidence-view** = 20 refs/record (§11.17) — ✅ confirmed as the **AI-display limit only**: drops no data; all `evidence_refs` stay stored and are validated on the FULL set.
4. **`same_as_variants` placement** = on the parent seed (§11.5) — ✅ confirmed; parent/global keep variants as **names**, child catalogs preserve the full records/history.
5. **Chunking slot** = Phase 0.5 / foundational (§6) — ✅ confirmed.
6. **Child skips/unresolved** = omitted from the clean catalog but **recorded in `fold_manifest.json`** (child run IDs + skipped/unresolved counts, §11.16) — ✅ confirmed (override of "silent drop": nothing disappears silently).
7. **High-blast double Refute** = a 2nd AND-voted Refute when a fusion spans ≥ `HIGH_BLAST_COMPANIES` (default 8) companies or ≥ 2 sectors (§11.18) — ✅ confirmed.
