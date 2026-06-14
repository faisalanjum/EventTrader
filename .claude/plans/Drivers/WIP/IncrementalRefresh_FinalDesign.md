# Incremental Refresh (Append) — Final Locked Design

**Status:** DESIGN-LOCKED (owner-approved over multiple review rounds + a measured embedding experiment, 2026-06-13/14). **No production code written yet** — this is the build contract. Supersedes the earlier `IncrementalAppend_Spec.md` (consolidated + multi-level finalized + the global-freeze correction).

---

## 0. Plain what / why

- **What:** when a new batch of filings/transcripts arrives, re-run the catalog build over **only the new documents** and **staple the result onto the locked existing catalog** — then push that change **up the tree** (industry → sector → global). No full rebuild.
- **Why:** a full rebuild re-reads every document (Fable readers) and re-judges every driver (Opus) — slow + expensive. Append reads only what's new and only judges pairs that touch new data.
- **Mental model:** the catalog is a **locked book**. Each refresh = write a **short new chapter, staple it on, re-check only the seams** — and let that ripple up the shelf (industry book → sector shelf → global library).
- **The two unbreakable rules:**
  1. **Old↔old stays FROZEN** — never re-judge two settled old drivers (re-judging can randomly create a *new wrong merge* = the one permanent, dangerous error). This holds at **every** level.
  2. **Prefer re-doing cheap work over silently skipping risky work; never re-read a document we already have; under-merge is safe, over-merge is permanent.**

---

## 1. Decisions at a glance (review list)

| # | Decision | One-line |
|---|---|---|
| 1 | **Append, not rebuild** | read only new docs, attach to the locked catalog |
| 2 | **Multi-level, finalized** | a delta climbs leaf → sector → global (not deferred) |
| 3 | **Three modes** | `fresh` / `resume` / `append`; a tiny `run_intent.json` records which |
| 4 | **Source ledger on disk** | checklist of every document read, built from `sources/<T>.json`; minimal rows `{ticker, source_type, source_id}` |
| 5 | **Skip by document ID, not date** | so a late-arriving old document is never missed |
| 6 | **KPI delta** | only new fiscal metric-names are read |
| 7 | **Merge = `fold(base, delta)`** | reuse the existing fold machinery; a fold is a fold |
| 8 | **Re-fold from REAL children (Shape A)** | rebuild each dirty parent from {updated child + real unchanged siblings} — NOT a shortcut "delta-child" |
| 9 | **Freeze old↔old at EVERY level** | leaf, sector, **and global**; only pairs touching new data are judged |
| 10 | **Old drivers immutable; old = canonical head** | never renamed/deleted/re-pointed; only gain a spoke or evidence (star-flatten). At the seam old is canonical **regardless of name length** (overrides the shortest-name rule). Same-name homonym: old stays, only the new side moves |
| 11 | **No verdict cache** | filtering out old↔old pairs means nothing is re-judged → nothing to cache |
| 12 | **Embeddings DEFAULT ON everywhere** | catch same-meaning-different-words dups; `min_score 0.60`, `top_k 5` (measured) |
| 13 | **`limit:0` — judge every candidate** | never silently drop a pair; fan out across calls if many |
| 14 | **SKIP re-opens, PARK terminal** | a vague skip can flip on new evidence; a homonym park stays parked (fresh rebuild revisits it) |
| 15 | **`ruleset_sha` version fingerprint** | only reuse an inherited verdict if rules + model + suggest-settings are identical |
| 16 | **base↔base-forbidden hard validator rule** | enforced at every level; append may never create/drop an old↔old link |
| 17 | **One atomic branch commit** | leaf'+sector'+global' flip live together in a single `os.rename`; crash before = old branch fully live |
| 18 | **First-run unchanged structurally** | only shared improvements: embeddings-on@0.60 + `limit:0`; existing catalog → fresh rebuild after finalize (not patched) |
| 19 | **Full re-judge = fresh-rebuild ONLY** | never an append behavior (a full re-judge re-opens old↔old = dangerous) |

---

## 1c. (ToDo — PENDING, NOT finalized) Driver `fact_type` field

*Owner 2026-06-14: add to the overall catalog plan (original build **and** delta), but **not finalized** — it depends on a separate **DriverUpdate-property decision** the owner is still making. Recorded here so the build accounts for it; do not wire it in yet.*

**Every Driver gains one permanent field `fact_type` ∈ {metric, guidance, surprise, action_event}:**

| fact_type | the Driver is about… | examples |
|---|---|---|
| `metric` | a value / KPI / condition / cost / rate / price / trend, or qualitative business condition | same_store_sales, traffic, commodity_cost, consumer_sentiment, market_share |
| `guidance` | a company outlook / target / forecast / plan / expected future value | eps_guidance, revenue_guidance, capital_expenditure_guidance |
| `surprise` | actual result vs expectation | eps_surprise, revenue_surprise, same_store_sales_surprise |
| `action_event` | a discrete action / decision / incident / one-off event | dividend, share_repurchase, restaurant_closure, ceo_succession, asset_impairment |

**Rule of thumb:** can go up/down over time → `metric`; future outlook → `guidance`; actual-vs-expectation → `surprise`; happened as an action/event → `action_event`.

**Invariants:** `fact_type` is the Driver's **permanent KIND** — do NOT put state in the Driver name; the changing state lives on **DriverUpdate**. Assigned at **coin time** (a per-driver judgment). **Immutable per driver** → in append it is **FROZEN like the name** (old drivers keep their `fact_type`; new delta drivers get one). Applies to BOTH the original build and the delta.

**Open question to resolve at finalize (the DriverUpdate dependency):** DriverOntology already encodes surprise/guidance as NAME suffixes (`eps_surprise`, `revenue_guidance`). Decide whether `fact_type` **coexists** with those suffixes (structured but redundant) or lets names **simplify** — this ties to how DriverUpdate carries state. Until the owner decides: do NOT change names or wire `fact_type` into validators.

---

## 2. Modes — `run_intent.json`

Every run writes `run_intent.json` **first** (before any fetch), so even a crashed dir is self-describing:
```json
{ "mode":"fresh"|"resume"|"append", "base_run_id":"<id|null>",
  "scope_slug":"...",
  "frozen_delta_source_keys":[ {"ticker":"CAKE","source_type":"transcript","source_id":"CAKE_2026-02-18T17.00"}, ... ],
  "created_at":"<UTC>" }
```
| Mode | Meaning |
|---|---|
| `fresh` | full rebuild from scratch (existing pipeline) |
| `resume` | finish a CRASHED run on the SAME data window (existing A2 `resume_menus.py`; disk-only) |
| `append` | NEW data window; build a delta + merge up the tree (this design) |

**Liveness is decided by the POINTER, not by `run_intent.json`** (see §10): a dir is *live* IFF the **single canonical tree-wide state file `runs/_state.json`** (ONE file for the whole catalog — §10) names it as the live run for its level. `run_intent.json` only marks a dir as *built-but-not-yet-committed* → a consumer skips a dir that **has `run_intent.json` AND is not named by the pointer** (a crashed/in-progress orphan). A pointer-named dir is live even if a stale `run_intent.json` hasn't been cleaned up yet — so the single pointer flip is the *only* thing that publishes, and there is **no window where the pointer names an "in-progress" dir.**

---

## 3. Source ledger (what's "already built") — disk, not DB

- **The FED set:** every `source_id` fetched into a built catalog, keyed `{ticker, source_type, source_id}` (minimal — no date/first_seen).
- **Built from `sources/<TICKER>.json`** (the fetch output) — the only **lossless** record (keeps zero-driver + empty-content events + KPI names). Never from `chunks_manifest` (drops KPI-only/empty-text) or `evidence_refs` (drops zero-driver sources).
- **KPI ledger (same canonical key shape as every source):** `{ticker, source_type:"fiscal.ai-kpi", source_id:"fiscal_ai:<ticker>:<metric>"}`, where `<metric>` is the **raw** metric name. The KPI delta is computed on the `<metric>` component (new raw metric names → new keys). **One canonical form everywhere** — never a bare `metric_name`.
- **Disk-not-DB:** once the base's fetch wrote ids to disk, the ledger lives entirely on disk. The **only** Neo4j touch on append is the delta fetch. (Append is pinned to fold mode → no tree-discovery query; ticker list carried from `runs/_scope_<slug>.json`.)
- **Authoritative, not cheaply rebuildable** (fold parents have no `sources/`); verify against `sources_manifest` counts before trusting any rebuild.
- **Delta marker uses the SAME key as the ledger:** `frozen_delta_source_keys` (in `run_intent.json`) and the "delta-touched" test use **`{ticker, source_type, source_id}`** — the same shape as the ledger, **not bare ids**. `source_type` is **load-bearing**: the fetch-exclude is partitioned by it (report ids → reports query, transcript ids → transcript query), so a bare id can't be routed. (KPI keys = `{ticker, "fiscal.ai-kpi", "fiscal_ai:<ticker>:<metric>"}`.)

---

## 4. Delta fetch (events + KPIs)

- **Events:** `fetch_company_sources.py` gains `--exclude-source-ids`, applied **inside the Cypher, PARTITIONED by source_type** (report ids → reports query; transcript ids → transcript query — separate queries, wrong wiring = silent no-op). Post-fetch assertion: no fetched id is in the ledger.
  - **Why ID not date:** the corpus gets late/backfilled/re-ingested events. A backfilled old-dated filing arrives under a NEW accession (new id) → absent from ledger → always fetched. A since-date would silently skip it. (Report id = SEC accession, immutable; amendments = new accession. Transcript id = `<ticker>_<datetime>`.)
- **KPIs:** `new_kpis[ticker] = current raw metric_names − { the <metric> component of each KPI ledger key for this ticker }`; only the new raw metric names enter `fiscal_kpis`. (The ledger stores full source-keys `fiscal_ai:<ticker>:<metric>`, so subtract on the raw `<metric>` part — not the whole key.) Cut value-hashing — KPI drivers are name-level only.

---

## 5. Delta build (reused unchanged)

`chunk_company_sources.py` (+ the byte-exact conservation proof), Fable per-chunk readers, `build_seed.py`, and `resume_menus.py` (A2 crash resume of THIS delta dir) run **unchanged** over the delta.

**Three zero-/low-yield cases — must NEVER re-read or re-judge forever:**
- **No new source IDs at all** (nothing to fetch) → **do nothing.**
- **New docs read, NO candidate names coined at all** → **source + KPI ledger-only commit** (record the read keys so they're never re-fetched); catalog pointer + reject ledger **UNCHANGED**.
- **New docs read, candidates coined but ALL gated-SKIP** → **source + KPI ledger AND reject-ledger commit** (we *learned* those names are rejected — persist the skips so they aren't re-judged next time, and a re-coin with the **same** evidence can't silently flip to admit); catalog pointer **UNCHANGED** (no admitted drivers).

⚠️ In every "new docs" case the source/KPI ledger MUST advance atomically — skipping it re-reads those documents on **every** future append (the ledger is the **FED set** = everything READ, not the produced set). The reject-ledger advance in the all-SKIP case prevents both wasted re-judging and silent reversal of a settled "no".

---

## 6. The merge = `fold(base, delta)` + the four buckets

Merge = the **existing fold pipeline** (`build_tree` fold mode), base + delta as two children. ⚠️ **This requires a small extension: `build_tree.js:90` currently rejects any `scope_level` except `sector`/`global`, so a leaf merge (`fold(base_leaf, delta_leaf)` at the `industry` level) cannot run as-is — add `industry` (a.k.a. `leaf`) to the allow-list (and to `fold_catalogs.py` / `validate_catalog.py --fold`). The high-blast 2nd-skeptic stays GLOBAL-only, so an industry fold uses the normal judge+Refute — correct for a leaf.** Every pair of drivers falls in one bucket:

```
                 OLD (base)        NEW (delta)
   OLD (base)  ┌ FROZEN ─────────┬ SEAM ───────────┐
               │ never re-judge   │ judge carefully  │
   NEW (delta) ├ SEAM ───────────┼ judge normally ──┤
               └─────────────────┴──────────────────┘
```
- **old↔old = FROZEN** — never re-judged; enforced as a HARD validator rule (§16). (Re-judging settled pairs can nondeterministically create a new over-merge — forbidden.)
- **new↔new = judged normally.**
- **new↔old = THE SEAM** — judged at the repair pass (§7-embeddings). Same-name new↔old → the fold's D5 same-name review; different-name-same-meaning → the repair suggester.
- **Old drivers immutable — old is ALWAYS the canonical head at the seam.** When old↔new merge, the OLD driver is canonical **regardless of name length** — this OVERRIDES the normal reconcile rule (which picks the *shortest* name, `reconcile.js:86` R6). The new driver gets a reversible SAME_AS pointing **to the old head** (star-flatten — never a chain, never re-points the old driver). An old driver can only **gain a spoke or evidence** — never renamed, deleted, or re-pointed. *(Needs a small code override of the canonical-pick for append-seam links — see §13.)*
- **Same-name old↔new collision (homonym): old FROZEN, only the NEW side moves — ENFORCED.** The existing fold D5 can reshape the **whole** same-name group (rename/re-partition every occurrence). **Append MUST restrict D5 to act only on the NEW (delta-touched) occurrences.** If old `traffic` (foot-traffic) meets new `traffic` (web-traffic): keep old `traffic` exactly as-is (**name + identity + partition frozen**); the new side may only be **split into a new distinct name, parked, or attached (SAME) onto the old head**. A validator **HARD-FAILS** any D5 output (`split_map` / `assignments`) that renames, re-partitions, or re-assigns an **OLD-side** record. (This is the D5-path teeth behind §10's base↔base-forbidden invariant.)
- **"delta-touched" = eligible at the seam:** an old driver that GAINS new evidence is re-considered; a pure-old driver (no new evidence) stays frozen.
- **No cache needed:** because old↔old pairs are **filtered out** of the candidate set (a pair is judged only if ≥1 record has new evidence), the only pairs judged are genuinely new → nothing to re-judge, nothing to cache. Across repeated appends each pair is judged **exactly once**.

---

## 7. The repair seam — embeddings, cutoff, `limit:0`

The duplicate-finder shortlists candidate pairs (3 nets: token-overlap ≥2, rare-token df≤5, **embeddings**); the Opus judge rules each SAME/DIFFERENT/UNCLEAR (EXACT_MEANING_RULE + Refute skeptic + 2nd skeptic at ≥8 companies). **Suggester suggests; the AI judge is the precision gate.**

- **Embeddings DEFAULT ON everywhere** (first-run + append + every fold level), `min_score = 0.60`, `top_k = 5`, model `text-embedding-3-large`, over **composite text MINUS `same_as_variants`** (name + companies + evidence quotes; variants stripped to avoid already-merged leakage).
- **`limit:0` — never silently drop.** Judge EVERY shortlisted pair; fan out across calls if there are many (batched on leaves; per-pair on folds). The old `limit=200` default silently dropped the tail. Wire it: the fold-parent repair call must pass `{run_id, limit:0}`.
- **Cross-pairs forced.** ⚠️ `top_k=5` bounds **only the embedding net** (each record's 5 nearest). The **token-overlap and rare-token nets add more pairs on top**, so the total candidate count is **not** bounded by `top_k` — it is (embedding ≤5/record) + token-overlap + rare-token. The judge bill scales with that total.
- **Cost posture (recall-first):** embedding cost ≈ pennies; the judge bill scales with candidate count. Fine at leaf scale (~990 pairs); watch at global; dial-back if it bites = raise cutoff or overflow-batch. **OpenAI key must be present wherever repair runs (incl. K8s).**

---

## 8. Multi-level propagation (leaf → sector → global)

A delta for one industry climbs its **dirty branch**, applying the **same** append at each level.

- **Shape (A): re-fold each dirty parent FROM ITS REAL CURRENT CHILDREN** (updated leaf + real unchanged sibling leaves; then updated sector + real unchanged sibling sectors). **NOT Shape (B)** ("propagate a shortcut delta-child").
  - **Why A:** the D8 validator checks `parent == exact 5-tuple union of the children passed to --fold`. Under A the children **are** the real updated leaves → parent = true union BY CONSTRUCTION → D8 catches any missed evidence. Under B the children would be {stale base, hand-built delta} → D8 would prove a *self-consistent lie* while never seeing the real leaf → silent missed evidence. B also has no producer + double-counts. So A is both safer and not more code.
- **Freeze at EVERY level, including GLOBAL** (corrected 2026-06-14): old↔old frozen at leaf, sector, **and** global; only pairs touching delta data are judged. `frozen_delta_source_keys` flows DOWN into the freeze-filter at every level (a **signature/provenance** test — a record is delta-touched iff any evidence ref in its cluster traces to a delta source_id, recursive up the tree — **never** a run-id proxy).
  - **Two seam paths, opposite handling:** different-name → `repair.suggest` skips a pair iff BOTH records are pure-old; identical-name collision → `fold_catalogs` part_a re-queues the WHOLE same-name group to D5 the instant ANY occurrence is delta-touched.
  - **If `0.60` under-recalls at global** (its composite text is a huge multi-company union) → that's an **under-merge (safe)** → measure & tune later; a periodic **fresh rebuild** re-clusters everything. **A full global re-judge is NEVER append** (it would re-open settled global↔global pairs = the dangerous over-merge) — it is only the explicit fresh-rebuild mode.
- **Per-cycle gather:** a cycle collects ALL dirty leaves, computes the dirty parent chain, and folds each dirty parent ONCE with ALL its changed children (N-ary). The **lock is scope-level** (whole tree) and spans the branch, so sibling-industry appends serialize on the shared sector/global.
- **inherit=OFF** asserted (SystemExit) at every level for append (C1 fold-inheritance excludes refresh folds).

---

## 9. Negative-verdict handling (SKIP / PARK)

- **Carry-forward (mandatory, both):** fold part_b unions base `skips[]`/`unresolved_*`/`fold_sidecars` parks into the merged parent (deterministic, zero LLM) — so a settled NO isn't dropped, re-coined, and silently re-admitted.
- **SKIP re-opens on new evidence:** "too vague" can flip when clearer evidence arrives (an EASY call). Reuse the stored NO if the record's evidence is unchanged; RE-JUDGE if it grew.
- **PARK stays TERMINAL in append:** a PARK is a same-name **homonym** (one name, ≥2 meanings) the reviewer+skeptic couldn't resolve. It is carried forward but **never re-opened** — it's a naming ambiguity (more evidence makes it messier), re-opening re-asks the AI its hardest call (risking the dangerous over-merge), parks are rare, and parked = the safe state. A **fresh rebuild** revisits it. Applies at every level.

---

## 10. Reliability, version fingerprint, crash-safety

- **`ruleset_sha`** = SHA256(DriverOntology.md + reconcile.js + repair_duplicates.js + gate.js + fold_catalogs.js + fold_catalogs.py + per-judge model-id + the LOCKED suggest-args `{use_embeddings:true, min_score:0.60, top_k:5, min_token_overlap:2}`). An inherited verdict is trusted only if `ruleset_sha` matches. (Beats `git_commit`: catches dirty edits + model swaps; doesn't over-fire on unrelated commits.)
- **base↔base-forbidden hard rule** at sector AND global validate `--fold`, plus the dual: every new↔old candidate the suggester emits must carry a this-run verdict (`limit:0`). pure-old recomputed from evidence-tuple bytes per level.
- **Cross-level coverage assertion** at commit: recursive `coverage(global')` ⊇ union of every dirty `leaf'` coverage, else HARD-FAIL.
- **One atomic branch commit (the pointer is the sole publisher):** build leaf'/sector'/global' in new immutable dirs (each carries `run_intent.json` → NOT live, skipped as orphans because the pointer doesn't name them yet), validate bottom-up, then **ONE `os.rename`** of the **single canonical tree-wide state file `runs/_state.json`** — **NOT one per industry** (a per-industry file would let two industries' commits split the global pointer). It holds the live run_id for **every** level (global + each sector + each leaf) plus the source/KPI/reject ledgers; the rename updates it to name the new leaf'/sector'/global'. **That single rename is what makes them live** (liveness = pointer-named, §2). `run_intent.json` is removed from the three dirs **lazily after** the flip (cleanup only, not part of the atomic step; a leftover stamp on a pointer-named dir is ignored). Restart invariant: refuse the flip unless all three exist, validate, and the `fold_manifest` chain coheres (global'→sector'→leaf'). Crash before the rename = all three OLD levels live + consistent, the new dirs are orphans (have `run_intent.json`, not pointer-named → skipped), ledger un-advanced → clean re-fetch.
- **Lock** scope-level; **SKIP re-open removes the name from the reject-ledger recursively at commit**; **LEAF-mode rule:** a SAME_AS merge may never SHRINK total evidence (stops below-the-fold poison).

---

## 11. What does NOT change (the first-run) + fresh rebuild

- The first-run build (menu→reconcile→repair→fold; Fable reads / Opus judges) is **structurally unchanged.** Append is a new additive sibling.
- **Only shared improvements** (both fix latent gaps, not restructures): embeddings default ON @0.60 in the shared repair finder (so the first run also catches word-distant dups it used to miss); `limit:0` in the shared fold-repair call.
- **No patching of the existing catalog.** Once this design is final → **clean slate → fresh rebuild** with embeddings-on@0.60 + `limit:0` from the start.

---

## 12. The `min_score = 0.60` measurement (justification)

Run 2026-06-13 on the CAKE Restaurants leaf (446-record pool incl. planted twins), composite-minus-variants, text-embedding-3-large ×3 (jitter 0.001 ≈ deterministic), pre-registered + graded once. Gold = 31 word-distant twins vs 26 hard-negatives, 7 scenarios.

- **No clean cutoff exists** — twin and hard-negative cosines overlap. A must-stay-separate brand pair `cheesecake_factory_same_store_sales`/`same_store_sales` scores **0.887 > the best true twin (0.844)**. ⇒ a cosine threshold **cannot** be a precision filter — the AI judge is the only precision gate.
- **Recall/cost frontier** (top_k 3..full identical → top_k not binding; `min_score` is the dial):

  | min_score | twin recall | hard-negs above | candidates |
  |---|---|---|---|
  | 0.60 | 100% | 17 | ~990 |
  | 0.65 | 94% | 10 | ~565 |
  | 0.72 (old default) | 58% | 5 | ~210 |
  | 0.80 | 10% | 2 | ~42 |

- **Decision:** the old 0.72 silently missed **42%** of word-distant dups. `0.60` maximizes recall. **The cutoff is NOT the precision gate — the AI judge is** (it rules every shortlisted pair). Lowering the cutoff doesn't change per-pair precision, but it DOES feed **more** candidates to the judge → slightly **more absolute over-merge exposure** (more chances for the judge's small error rate to slip a bad merge through). That extra exposure is acceptable here because the added pairs are lower-cosine **easy rejects** and the dangerous high-cosine look-alikes are judged at *any* cutoff. A missed dup at a seam is an under-merge (safe, recoverable by fresh rebuild). Caveat: recall % is on synthetic twins (optimistic); the overlap conclusion is robust. Fallback if cost bites = 0.65 (precision-identical). Full data: `/tmp/embed_cutoff_gold/experiment_report.json` (reproducible; commit gold + report for provenance).

---

## 13. Minimal new code surface

**Leaf:** **extend `build_tree` fold mode + `fold_catalogs`/`validate --fold` to accept an `industry`-level (leaf↔leaf) fold (`build_tree.js:90` allow-list — else the leaf merge can't run)** · `--exclude-source-ids` (split by type) + KPI set-diff + post-fetch assert · `repair_duplicates` defaults `use_embeddings=True, min_score=0.60` · fold-parent repair call passes `limit:0` · repair candidate filter (skip pure-old↔pure-old) · **append-seam canonical override (old driver always canonical, overriding the shortest-name R6 rule at `reconcile.js:86`/`assemble_catalog.py`)** · the single canonical tree state file `runs/_state.json` via temp+fsync+single `os.rename` + `coverage()` helper · SKIP/PARK carry-forward + SKIP re-open rule · `ruleset_sha` · validator base↔base-forbidden rule · `run_intent.json {mode}` + lock · **empty-delta ledger-only commit (advance ledger, keep catalog pointer)** · **D5 append-restriction (same-name review may only split/park/attach NEW occurrences; validator hard-fails any rename/re-partition of an OLD record)** · the append wrapper.

**Multi-level (additive on top):** dirty-branch resolver + per-cycle gather (N-ary fold) · thread `frozen_delta_source_keys` into the freeze-filter at repair.suggest + fold_catalogs part_a + reconcile gate/dedup · generalize the base↔base-forbidden rule to sector+global · branch-manifest commit (one rename for the chain) + restart invariant · cross-level coverage assertion · recursive reject-ledger re-admit edit · LEAF "SAME_AS may not shrink evidence" rule · `inherit=OFF` assertion per level. (≈8 small pieces, ~250 LOC.)

**Cut (verified-rejected):** quote-blind dedup · recursive-coverage-only ledger · KPI value-hashing · separate `_current/` file · 32-bit hash for signatures · `--reinclude` · `prompt_version` field · a repair verdict cache · the Shape-B delta-child + its differ/validator · editing the chunker · any full global re-judge in append.

---

## 14. Gates, deferred & remaining small confirms

- **GATE (before first append):** one read-only Neo4j query confirming `Transcript.id` is immutable across re-ingest. If not → key transcripts in `coverage()` by `ticker+fiscal_year+calendar_quarter+conference_datetime`.
- **Recall-tuning (not a gate):** re-measure `min_score=0.60` on a real multi-level fold (same knobs, no re-tuning) to know/improve global seam recall. (No longer a precondition — global is frozen-and-safe regardless; a miss is under-merge, fixed by tuning or fresh rebuild.)
- **Future task — risk nodes as driver hints, not current KPI-like inputs:** live Neo4j check (2026-06-14) found `RiskCategory`/`RiskClassification` are real and useful (140 categories; 39,821 classifications; all embedded; all linked to 10-K `RiskFactors` sections and categories), but they are **derived Massive classifications of filing text we already fetch**, not raw company metric names like fiscal.ai KPIs. Coverage is also uneven in Restaurants: 12/14 tickers have risk nodes, while `QSR` and `WING` have RiskFactors text but zero risk classifications; 4,416/39,821 span offsets are missing. Current decision: **do not make them required append sources now.** Future validation: test them as optional recall hints with stable source keys like `{ticker, source_type:"risk-classification", source_id:"risk_classification:<RiskClassification.id>"}` and use `supporting_text` as the quote; ship only if they improve driver recall without adding duplicate/noisy risk-disclosure drivers.
- **Previously-open confirms — now DECIDED (no open design questions remain):** (a) per-cycle branch gather + scope-level lock = **IN** (serializes sibling appends; reliability); (b) LEAF "SAME_AS may not shrink evidence" rule = **IN now** (cheap integrity); (c) recursive reject-ledger re-admit edit at commit = **IN** (correctness); (d) the 2-level recall test = **side-lane, does NOT block first production** (global is frozen-safe regardless; the test only tunes recall). The ONLY remaining pre-run item is the Transcript-ID GATE above — a verification, not a design choice.

---

## 15. Provenance

Owner-driven brainstorm 2026-06-13/14; multiple hardening rounds (ChatGPT critiques independently verified against code each round, not rubber-stamped — including the 2026-06-14 correction that a full global re-judge violates the freeze rule); embedding cutoff measured. Round-by-round record: memory `project_drivers_incremental_append.md`. Builds on `HierarchicalCatalogPlan.md` §13.4, `CostCutting.md` (master rule), `C5_BatchedRepair.md` (repair/judge gates), `C1_FoldInheritance.md` (refresh folds excluded from inherit).
