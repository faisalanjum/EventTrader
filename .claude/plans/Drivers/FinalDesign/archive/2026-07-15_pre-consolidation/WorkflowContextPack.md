# WorkflowContextPack — the old build-workflow machinery, mapped for Fable

> **What this is:** a source-cited map of the existing Driver-Catalog **build code** in `/home/faisal/EventMarketDB/.claude/plans/Drivers/workflows/` — what each file does, where it sits, whether it is reusable, and every stale trap that must NOT be copied into new work. **It adds no design and solves nothing.** On any conflict, the FinalDesign topic docs + `95_Supersession.md` win over the code; **code that still runs can still be stale.**
>
> **Provenance:** every file below was read this session (2026-07-07) — 21 code files + 13 tests. Line/rule citations are exact. Where a stale trap is claimed, it is cross-checked against `10_BuildPipeline.md §3` and `95_Supersession.md`.

**Disposition legend:** ✅ **AS-IS** (reuse unchanged) · 🔧 **UPDATE** (reuse after a rule/prompt/config change) · 🧪 **EXPERIMENT-ONLY** (measurement kit, not a pipeline stage) · ⛔ **SUPERSEDED / DO-NOT-USE** · 📜 **NOT-A-STAGE** (historical relic).

---

## 1. Executive summary

**What the folder is for.** It is the **batch Track A build engine** — the code that turns raw company filings/transcripts into the shared **Driver *class* catalog** (reusable cause-names only; never DriverUpdate facts). It is the machinery `10_BuildPipeline.md` documents (`workflows/` + a 261-test suite, `10 PIPE-06`).

**How it originally supported Driver-Catalog creation.** A bottom-up folder-merge tree (`10 PIPE-09`): names are **born only at the per-industry leaf** (`menu_build.js`), deduped/admitted/refuted (`reconcile.js`), deterministically written (`assemble_catalog.py`), validated (`validate_catalog.py`), duplicate-repaired (`repair_duplicates.*`), then folded industry→sector→global (`build_tree.js` + `fold_catalogs.*`). A separate side-channel A/B kit (`ab_*`) measures whether cost optimizations (batched repair, cheaper models) lose merges.

**How it relates to the Driver Identity Admission Kernel** (`FableAdmissionKernelDesign.md` v3.4 — the current lock-candidate baseline; topic docs + `90`/`95` still win on conflicts). The kernel design re-roles this machinery:
| This code | Role in the v3.4 baseline | Cite |
|---|---|---|
| `repair_duplicates.*` (suggest→Refute→apply) | donor for the async LINK/sweep backstop and duplicate-repair experiments; must be updated to v3.4 rules before reuse | kernel §6/§12 |
| the whole leaf→fold→finalize pipeline | seed-builder, contingency deep-clean, and component donor — not a scheduled production backbone | kernel §1/§8/§15 |
| `ab_stratum.py`/`ab_pair_judge.js`/`ab_differ.py` | experiment harness pieces for the v3.4 proof program; update prompts/model slots first | kernel §12 |
| `gate.js` (G2), `reconcile.js` Refute 3-check, D5 | old batch orchestration of identity decisions; useful substrate, but stale until rulebook/model/display changes are applied | kernel §2/§6/§7 |

> **Two big absences a builder must know up front:** (1) **FINALIZE does not exist in this folder** — `fact_type` stamping + `BASE_METRIC` (`finalize_catalog.py`, `10 PIPE-24/25/26`) is an ADD, not built. (2) The **fitness/honesty gate has never run** (`10 PIPE-37`; 0 graph nodes). So this code coins and reconciles *names*; it does not stamp types, build families, or write Neo4j.

---

## 2. End-to-end old workflow (the actual code path)

```
LEAF  (menu_build.js orchestrates one industry)
  resolve_driver_scope.py  → tickers + run_id (read-only Neo4j, code-to-code scope file)
  fetch_company_sources.py → runs/<id>/sources/<T>.json  (ALL non-news sources, FULL text, uncapped)
  chunk_company_sources.py → runs/<id>/chunks/<T>__chunk_NNN.json  (byte-exact conservation)
  [1 BLIND reader per chunk, model:'fable'] → menus/<cid>.json  (candidate driver_names + evidence)
  build_seed.py            → seed.json  (deterministic group-by-norm(name), 5-tuple evidence dedup)
  resume_menus.py          → A2 crash-resume: re-run ONLY chunks missing a valid menu
RECONCILE  (reconcile.js orchestrates one seed)
  slice_seed.py            → name-sorted review batches (≤400 recs / ≤300k chars)
  parallel[ dedup(SAME_AS proposer) ‖ gate(G2 admit/rewrite/skip) ]   (both model:'opus')
  refute                   → skeptic breaks bad SAME_AS + meaning-changing rewrites (default FALSE)
  high-blast 2nd skeptic   → any fusion ≥8 companies → object/scope/mechanism AND-voted
  leaf D5 (flag-triggered) → SAME(Refute-confirmed) / DIFFERENT(split) / UNCLEAR(park)
  → decisions.json → assemble_catalog.py (5-way precedence + STAR-flatten) → catalog.json + approved.json
  → validate_catalog.py    → D1 fusion-approval + high-blast backstop → validation_exit.json (exit0 + sha)
FOLD  (build_tree.js walks sectors; fold_catalogs.js/.py per parent)
  fold_catalogs.py part-a  → collapse each child's SAME_AS clusters → cross-child collision queue
  draw                     → deterministic ≤20/side evidence views
  fold_catalogs.js         → review(SAME/DIFFERENT/UNCLEAR) + Refute + high-blast Refute2 (model:'opus')
  fold_catalogs.py part-b  → parent seed.json
  → reconcile.js (D3) → validate --fold (D8 pre-repair) → repair → validate --fold (D8 post-repair)
REPAIR  (repair_duplicates.js/.py — required at EVERY level)
  suggest(token ∪ rare-token ∪ embeddings) → judge(per-pair | C5 batched+blind-confirm+2% canary)
  → high-blast Refute2 → apply SAME_AS → re-validate.  C5 batched lane = LEAVES only; folds per-pair (K2).
FINALIZE   → finalize_catalog.py — NOT in this folder (ADD, 10 PIPE-24).  fact_type/BASE_METRIC absent.
FITNESS GATE → 10 PIPE-37 — never run, no code here.
--- side channels ---
EXPERIMENT KIT   ab_stratum.py → ab_pair_judge.js (arms 2/3) → ab_differ.py (GO/NO-GO)
STAGE-0 HARDENING (cross-cutting relay-trust: validation_exit.json · --expect+h32 · code-to-code scope
                   · candidate-set binding) — tested by test_stage0_hardening.py
DEAD  catalog_first.js (G1 catalog-first — superseded by propose-first) · rescue_review.py (one-off relic)
```

---

## 3. File-by-file map (code)

Paths are under `.claude/plans/Drivers/workflows/`.

| File | What it does · flow position | Inputs → Outputs | Disposition |
|---|---|---|---|
| `resolve_driver_scope.py` | Read-only Neo4j scope resolver (industry/sector → tickers). Stage 0. | `--industry/--sector/--out` → `{tickers[]}` + `_scope_<slug>.json` | ✅ AS-IS (cosmetic: hardcoded Neo4j URI fallback `:21`, `10 §12` footgun 16) |
| `fetch_company_sources.py` | Pulls ALL non-news sources, FULL text, no date window. Stage 0.5. | `--scope`/`--run-dir` → `sources/<T>.json` + `sources_manifest.json` | ✅ AS-IS (no date window is CORRECT — name-creation is PIT-exempt, `PIPE-34`; cosmetic URI `:33`) |
| `chunk_company_sources.py` | Splits sources into bounded chunks; byte-exact conservation (`--verify`). Leaf. | `run_dir` → `chunks/*.json` + `chunks_manifest.json` | ✅ AS-IS (`CHUNK_BUDGET_CHARS=40_000`; EX-99.1-iff-earnings `:56-57`) |
| **`menu_build.js`** | Orchestrates the leaf: resolve→fetch→chunk→**blind readers**→converge. Coins candidate names. | `{industry}` → `seed.json` (+run dir) | 🔧 **UPDATE** — 4 traps (§5): brand-in-name RULES `:44`, `DriverOntology.md` `:40`, `xbrl_or_null` schema `:29-30,:142`, reader `model:'fable'` `:144` |
| `build_seed.py` | Deterministic converge: group by `norm(name)`, 5-tuple evidence dedup, write `seed.json`. Leaf. | `menus/*.json` → `seed.json` | 🔧 **UPDATE** — drop `optional_links`+first-xbrl copy `:75-89`; delete dead no-op loop `:116-118` (`10 PIPE-27f`) |
| `slice_seed.py` | §11.11 review-batch slicer (≤400 recs/≤300k chars, name-sorted, fat record alone). Reconcile guard. | `seed.json` → `seed_batch_NNN.json` | ✅ AS-IS |
| `resume_menus.py` | A2 crash-resume planner: re-run only chunks missing a valid menu. Leaf. **Not read-only** (unlinks stale menus). | `run_dir` → todo plan | 🔧 **UPDATE** — `xbrl_or_null` in `CANDIDATE_FIELDS` `:35-36,:63` must drop in lockstep with `menu_build`/`build_seed` (`PIPE-21`) |
| **`reconcile.js`** | Reconcile orchestrator: dedup‖G2→Refute→2nd-skeptic→leaf D5→assemble→validate. | `{run_id}` → `catalog.json`+`approved.json`+`decisions.json`+`validation.txt` | 🔧 **UPDATE** — brand lines `:84/:90/:96/:104`, `DriverOntology.md` `:15`, every judge `model:'opus'`; MF-02 cross-flavor guard not inlined (`PIPE-16`) |
| **`gate.js`** | Standalone **G2 admission gate** (reuse/admit/rewrite/skip). Meta says "BATCH reconcile AND LIVE production" → closest analog to the kernel's router. | `{candidates, catalog}` → verdicts | 🔧 **UPDATE** — brand-admit `:33`, `DriverOntology.md` `:7`, **NO billing guard, NO model pin** (`10 PIPE-10/23/27e`) |
| `assemble_catalog.py` | DETERMINISTIC writer: 5-way precedence (skip>SAME_AS>rewrite>parked>self) + STAR-flatten + leaf D5 apply. Reconcile. | `seed.json`+`decisions.json` → `catalog.json`+`approved.json` | 🔧 **UPDATE** — emits `optional_links` `:104/:236/:410` (`PIPE-21`); precedence/STAR logic itself is current |
| `validate_catalog.py` | Structural validator: field integrity, D1 fusion-approval, `same_as_variants` mirror, HIGH_BLAST=8 backstop, D8 fold accounting. Writes the fail-closed sidecar. | `seed catalog [approved] [--fold]` → PASS/FAIL + `validation_exit.json` | ✅ AS-IS logic (only a stale docstring `:8` still lists `optional_links` — 1-line text fix) |
| `fold_catalogs.py` | Pure-python fold engine: part-a collapse, §12.8 draw, part-b assemble. Fold. Its collapse mechanics (`:147-206`) are cited as authoritative substrate by `PIPE-26/28`. | child catalogs → `fold_queue.json`/`seed.json`/`fold_sidecars.json` | 🔧 **UPDATE** — `optional_links`/`merge_optional_links` `:53,:124-142,:195,:401-403` (`PIPE-21` names it for deletion) |
| `fold_catalogs.js` | Fold orchestrator: draw→review(SAME/DIFFERENT/UNCLEAR)→Refute→high-blast Refute2→part-b. | fold args → review + seed via `.py` | 🔧 **UPDATE** — `DriverOntology.md` `:84`, `model:'opus'` `:67/79/92/103/114/146` |
| `build_tree.js` | Top-level tree orchestrator (list / single-fold / walk-and-fold). Chains fold→reconcile→D8→repair→D8. | leaf run dirs → folded catalog | 🔧 **UPDATE** — `{list:true}` mode has **no billing guard** (`10 PIPE-10` gap), `model:'opus'` pins `:42,72,77,97,117,128,192` |
| `repair_duplicates.py` | Pure-code repair half: suggest (token/rare-token/embeddings), C5 batched plan, canary, apply SAME_AS. Every level. | run dir → `repair_*.json` + updated catalog | 🔧 **UPDATE** — embeddings `min_score=0.72` `:82,110,491` must be **0.60** (`10 §10`, trap 11) |
| `repair_duplicates.js` | Repair orchestrator: suggest→judge(per-pair \| C5 batched+blind-confirm+2% canary)→Refute2→apply. Its per-pair prompt is byte-identical to `ab_pair_judge.js`. | `{run_id,...}` → repaired catalog | 🔧 **UPDATE** — `model:'opus'` pins (many); batch-on-fold-run is only a doc-level constraint, not code-enforced |
| `ab_stratum.py` | A/B stratum selector: ~100 marginal batched-DIFFERENT pairs + 40-pair noise. Side-channel. | repair_*.json → `ab_stratum.json` | 🧪 EXPERIMENT (✅ AS-IS — `PIPE-32` names it to reuse) |
| `ab_pair_judge.js` | A/B arm harness: re-judge pinned pairs solo with the byte-identical prompt. Side-channel. | `{run_id,idx,out}` → arm review file | 🧪 EXPERIMENT / 🔧 UPDATE — `model:'opus'` `:48/58/74` (alias trap, `PIPE-32`); inherits missing MF-02 guard |
| `ab_differ.py` | A/B GO/NO-GO differ: lost-merge vs noise floor, Wilson/rule-of-three, position gradient. Side-channel. | stratum+arm files → `ab_differ_report.json` | 🧪 EXPERIMENT (✅ AS-IS — `PIPE-32`) |
| `catalog_first.js` | **DEAD G1 catalog-first flow** (shows catalog BEFORE proposing). Its own header says "DO NOT rebuild/wire — propose-first supersedes." | `{events,catalog}` → reuse/create/skip | ⛔ **SUPERSEDED** (95 #21, `PIPE-22`) |
| `rescue_review.py` | One-off 2026-06-11 relay-truncation recovery, hash-pinned to a single dead run. | wf transcripts → one `repair_review.json` | 📜 NOT-A-STAGE (`10 §12` footgun 7; never runs in a new build) |

---

## 4. Test inventory (`workflows/tests/`)

| Test file | Behavior protected · production risk | Reusable for kernel experiments? | Needs update? |
|---|---|---|---|
| `test_build_seed.py` | Deterministic grouping + lowercase name, 5-tuple dedup, shared-drivers-only, sorted+self-canonical, CLI determinism + `--expect` cross-check, blank-name skip. Risk: silent evidence loss / non-deterministic seed. | Pattern for a kernel converge/dedup test. | 🔧 `cand()` default `xbrl="null"` `:25` + `test_first_xbrl_wins` `:59-65` drop when `build_seed` drops xbrl. |
| `test_slice_seed.py` | §11.11 batching: record/char caps, name-sorted contiguous, single fat record alone, real-seed proof. Risk: an oversized batch reaching a prompt. | Low (batch-infra). | 🔧 `rec()` fixture carries `optional_links` `:31` (noise). |
| `test_assemble_catalog.py` | 5-way precedence, STAR-flatten, cycle tie-break, D5 SAME/DIFFERENT/UNCLEAR partition, byte-determinism. Risk: dropped/duplicated evidence, non-deterministic canonical. | **High** — precedence + transitive-closure + split-partition test patterns. | 🔧 `optional_links` fixtures `:38,150,211,271`. |
| `test_validate_catalog_d1.py` | D1 fusion-approval (STAR-aware), variants mirror, **HIGH_BLAST=8** second-skeptic requirement. Risk: unapproved/too-broad merge shipping. | **High** — "when does a merge need extra scrutiny" calibration (kernel reuse-vs-create thresholds). | 🔧 `optional_links` fixtures `:30,145`. |
| `test_validate_fold.py` | D8 accounting: every child name exactly once, parent evidence = exact union, split partition disjoint+complete, no invented variants. Risk: fold silently losing/duplicating names. | **High** — "many batches → one lossless union" = batch/live equivalence proof. | 🔧 `optional_links` fixture `:34`; coupled to `fold_catalogs.py`. |
| `test_fold_catalogs.py` | Chain collapse/cycle/dangling, no evidence lost, Refute-survived required, exact-once assignment, §12.8 draw determinism, oversize=WARN. | **High** — fail-close + planted-trap templates. | 🔧 `rec()` `optional_links` `:40-46` + 2 optional_links-conflict tests `:456-477`. |
| `test_fold_repair_review.py` | Regression: a fold parent's already-consumed `same_name_review.json` must be IGNORED at repair re-assembly; CLI hard-blocks `--review` on fold parents. Risk: fold repair crashing or re-splitting resolved names. | Indirectly — artifact-authority discipline. | 🔧 `rec()` `optional_links` `:31-35`. |
| `test_repair_duplicates.py` | SAME_AS repair: clip-limit silence, batched-lane row loss, transposed verdicts, unconfirmed-SAME, canary hit/miss, chunked-write truncation (2026-06-11 incident), **prompt byte-identity to `ab_pair_judge.js`**, mutate-before-validate. | **High** — batch+blind-confirm+canary adversarial fixtures. | 🔧 `rec()` `optional_links` `:25`. |
| `test_ab_differ.py` | §8R stats gate: binomial/Wilson math, lost-merge counting, degenerate-floor guard, position smoking-gun, full GO/NO-GO. | **High** — the batch==live equivalence gate itself. | ✅ none. |
| `test_ab_stratum.py` | Adversarial-stratum selection: signal ranking, eligibility filter (excludes SAME/unjudged/confirm-flipped), union-of-extremes, noise-spread-not-top40. | **High** — adversarial-fixture selection pattern. | ✅ none. |
| `test_chunk_company_sources.py` | Byte-exact conservation, fallback ladder termination, `--verify`. Risk: silent evidence corruption before a paid reader. | Indirectly (fixture generation). | ✅ none. |
| `test_resume_menus.py` | 13+ fail-close states (corrupt/stale/orphan dir), menu-validity mirror. Risk: silently skipping a chunk that needs a reader, or wasted re-runs. | Template for a validator-mutation suite. | 🔧 `xbrl_or_null` in `menu()/full_menu()` `:39,211` + assertion `:225-231`. |
| `test_stage0_hardening.py` | **The relay-trust backbone** — 8 checks (`10 PIPE-12`): #1 validator sidecar, #2 chunk coverage, #3 gate coverage, #4/#5 `--expect`+h32 write-fidelity, #6 global-fold flag, #7 pair-identity binding, #8 code-to-code scope. Risk: a lying/stale/truncated agent relay silently corrupting the catalog. | **High** — the integrity discipline transfers directly to any kernel with agent-relayed artifacts. | 🔧 `rec()` `optional_links` `:55` (fixture noise). |

---

## 5. Superseded / stale-behavior audit (brutal — do NOT copy)

Checked against the user's list + `95_Supersession` + `10 §3`. **Present** traps first, then the ones verified **absent**.

### PRESENT — must be fixed before any reuse

| Trap | Where (file:line + quote) | Rule it violates |
|---|---|---|
| **Catalog-first G1** | `catalog_first.js` — the whole file; meta `:18` `driver-catalog-first-g1`, prompt `:43` "applying CATALOG-FIRST reuse … reuse before you create", shows `VISIBLE CATALOG NAMES` up front `:46`. Its own banner `:1-16` says propose-first supersedes it — DO NOT WIRE. | 95 #21 · `10 PIPE-22` (propose-first: coin blind, THEN see related) |
| **Brand/segment in the Driver NAME** | `menu_build.js:44` "a brand metric like **taco_bell_same_store_sales is its OWN driver**"; `reconcile.js:84` "NEVER link names with different … brands, segments"; `:90` "**Brand/segment-specific names ARE valid drivers — admit them**"; `:96` "KEEP brand/segment-specific names"; `:104` "Different brand/segment vs company-wide → FALSE"; `gate.js:33` same. | 95 #1 · `PIPE-17/19` (own measured part → **slice**, not name; scope-lens redefined) |
| **`DriverOntology.md` as the naming authority** | `menu_build.js:40` "authority = …/DriverOntology.md"; `reconcile.js:15` + dedup/gate/D5 prompts; `gate.js:7,:28`; `fold_catalogs.js:84`; `catalog_first.js:23`. | `PIPE-16` (rulebook = `02_DriverCatalog.md` NAME-01…19; DriverOntology is a **stale-trap doc**, 95 §Stale-traps) |
| **Reader XBRL guess (`xbrl_or_null`) + `optional_links{xbrl_concept,xbrl_member,guidance_ref}`** — the single most pervasive trap (~11 files) | `menu_build.js:29-30,:142` (schema+prompt); `build_seed.py:75-89` (copies first-non-null xbrl); `resume_menus.py:35-36,:63`; `assemble_catalog.py:104,236,410`; `fold_catalogs.py:53,124-142,195,401`; `validate_catalog.py:8` (docstring); + every test `rec()`/`cand()` fixture. | 95 #13 · `PIPE-21` (DROP the reader XBRL guess + `optional_links` from all record shapes; concept identity is company-specific **fact-level** enrichment) |
| **Hard model pins** | reader `model:'fable'` `menu_build.js:144`; judges `model:'opus'` across `reconcile.js`, `fold_catalogs.js`, `build_tree.js`, `repair_duplicates.js`, `ab_pair_judge.js`; `gate.js:37` **pins nothing**. | `PIPE-23/31/32` + kernel §11.0 (models = config slots; pin **exact IDs** in `manifest.models`; owner default to test first: cheap/Haiku-like blind leaf producer + Sonnet 5 strong-judge candidate; alias trap) |
| **Embeddings `min_score=0.72`** | `repair_duplicates.py:82,110,491`. | `10 §10` locks **0.60** (owner 2026-06-13/14; "code still says 0.72 → update") |
| **Billing-guard gaps** | `gate.js` (no step-0 guard); `build_tree.js {list:true}` mode (`:36-46`, no guard while fold/walk modes have it). | `PIPE-10` (3 named gaps) · CLAUDE.md subscription-only |
| **MF-02 cross-flavor guard not inlined** | dedup/G2/Refute/repair judge prompts (`reconcile.js`, `repair_duplicates.js`, `ab_pair_judge.js:16-26`) carry only the 3-check; no "base vs `_guidance`/`_surprise` are NEVER SAME_AS". | `PIPE-16` ("Also inline MF-02 into dedup/G2/Refute") |

### ABSENT — verified clean (do not go hunting for these here)

| Checklist item | Finding |
|---|---|
| adjusted/diluted/constant-currency **endorsed** in names | Not asserted anywhere — the reader prompts simply **predate** the measurement slot (NAME-14/FS-25); they must be updated to route measurement out (part of the `PIPE-16/18` prompt refresh), but no code claims `adjusted_eps` is valid. |
| per-X as a unit / "$/physical → unknown" | Not present (these files coin names only; no unit resolution here). |
| Hand-curated XBRL **dictionary** | Not in this folder — the curated `concept_resolver.py` dictionary lives in the Track B guidance skill dir, not here. What IS here is the reader `xbrl_or_null` hint (above). |
| Old Guidance replay / `gu:` ids / `legacy_name_map` | **Absent.** This is the Driver-catalog build, wholly separate from the guidance system. |
| Alias-layer / fuzzy slice merge / near-match snap | **Absent** — the code merges only on exact `norm()` + Refute-approved links; embeddings *suggest, never decide* (`repair_duplicates.py:3-7`). Respects `FS-16`. |
| `slice=total` | **Absent** — Track A coins names only; it writes no slices/facts. |

---

## 6. Reuse recommendations (four buckets)

> Mapping the existing machinery only — no new architecture.

**✅ Reusable as-is** (clean; wire unchanged): `resolve_driver_scope.py` · `fetch_company_sources.py` · `chunk_company_sources.py` · `slice_seed.py` · `validate_catalog.py` (logic; fix the 1-line stale docstring) · `ab_stratum.py` · `ab_differ.py` · tests `test_chunk_company_sources.py`, `test_ab_differ.py`, `test_ab_stratum.py`. *(Cosmetic nit on the two Neo4j pullers: hardcoded fallback URI, `10 §12` footgun 16.)*

**🔧 Reusable after a rule/prompt/config update** (the fix is named, the mechanics are current): `menu_build.js`, `reconcile.js`, `gate.js`, `fold_catalogs.js/.py`, `build_tree.js`, `assemble_catalog.py`, `build_seed.py`, `repair_duplicates.js/.py`, `resume_menus.py`, `ab_pair_judge.js` — plus every test that bakes in `optional_links`/`xbrl_or_null` fixtures (they must move in lockstep). The updates are exactly the PRESENT traps in §5 (drop `optional_links`/`xbrl_or_null`; swap `DriverOntology.md`→`02`; delete brand-in-name lines; model→config slots using the owner default baseline first; `min_score`→0.60; add missing billing guards; inline MF-02).

**🧪 Useful only for experiments** (measurement kit, not a pipeline stage): `ab_stratum.py`, `ab_pair_judge.js`, `ab_differ.py` (+ their tests). `PIPE-32` names them as the kit any future A/B must reuse.

**⛔ Superseded / do-not-use**: `catalog_first.js` (dead catalog-first G1 — its own banner forbids wiring). **📜 Not-a-stage**: `rescue_review.py` (one-off relic).

> **Note for the kernel proposal specifically:** `gate.js` (G2, "batch AND live") and `reconcile.js`'s Refute-3-check / high-blast / D5 are the closest existing analogs to the kernel's router + sweep-judge, and `repair_duplicates.*` is what the kernel calls "the sweep." They are **🔧 UPDATE**, not drop-in — the fixes above must land first.

---

## 7. Experiment-design relevance

Which existing components help build each experiment family (maps to the kernel's X0–X9, kernel §10). This is a *reuse map*, not a design.

| Experiment need | Existing machinery to reuse | Cite |
|---|---|---|
| **Batch/live equivalence** (same events → batch vs single-item live → same decisions) | `assemble_catalog.py` 5-way precedence (one-decision-per-call generalization); `validate_catalog.py --fold` D8 "many batches → one lossless union"; `build_tree.js` walk = the batch half; `fetch_company_sources.py` = the shared event shape both sides see | `PIPE-11 D8`; kernel §2.5/§10-X8 |
| **Reuse-Refute calibration** (when does a merge need a 2nd skeptic) | `test_validate_catalog_d1.py` HIGH_BLAST=8 backstop tests; `reconcile.js` Refute 3-check + high-blast pattern | `PIPE-13`; `10 PIPE-27d` |
| **SAME_AS repair / sweep tests** | `repair_duplicates.py/.js` (suggest→judge→canary→apply); `test_repair_duplicates.py` incident-driven fixtures | `10 §54`; kernel §6 |
| **Adversarial fixture families** | planted-trap style in `test_fold_catalogs.py` (cycle/dangling/homonym/false-merge) + `test_assemble_catalog.py`; `chunk_company_sources.py` for giant synthetic filings | `PIPE-11` |
| **Model A/B comparisons** | `ab_stratum.py`+`ab_pair_judge.js`+`ab_differ.py` (the kit); `test_ab_differ.py` GO/NO-GO scenarios. **Score judged precision/recall against an adjudicated key — never quote-match** (measured ~99% quote-match vs ~29% judged precision). | `PIPE-32` |
| **Cheapest-model experiments** | same `ab_*` kit; `gate.js` (unpinned) is the natural cheap-router probe surface | `PIPE-30/31` |
| **Run-count / iteration experiments** | `resolve_driver_scope.py` for reproducible populations; the A/B kit's arm structure | `PIPE-32` |
| **Validator / mutation tests** | `validate_catalog.py` + `test_validate_*`; `test_resume_menus.py` fail-close matrix; **`test_stage0_hardening.py`** relay-trust discipline | `PIPE-12` |
| **PIT / reuse-display tests** | `fetch_company_sources.py` (no date window = PIT-exempt name creation, `PIPE-34`); the kernel's own `visible_from ≤ event date` filter is NOT in this code (kernel §3, unbuilt). | `PIPE-34`; kernel §3 |

---

## 8. Final source map

| If Fable needs detail on… | Open |
|---|---|
| how a name is coined (leaf reader) | `menu_build.js` (+ `RULES` `:40-47`), `build_seed.py`; rule authority = `02 NAME-01…19` |
| dedup / G2 / Refute / D5 | `reconcile.js`; `gate.js` (standalone G2); design = `10 PIPE-13`, `03 FS-04` |
| deterministic catalog write | `assemble_catalog.py` (5-way precedence `:5-11`, STAR `:357-381`) |
| structural validation / D1 / D8 | `validate_catalog.py`; tests `test_validate_catalog_d1.py`, `test_validate_fold.py` |
| fold mechanics | `fold_catalogs.py` (`:147-206` collapse), `fold_catalogs.js`, `build_tree.js` |
| duplicate repair / the "sweep" | `repair_duplicates.py/.js`; kernel §6 |
| the A/B experiment kit | `ab_stratum.py`, `ab_pair_judge.js`, `ab_differ.py`; `PIPE-32` |
| relay-trust / integrity discipline | `test_stage0_hardening.py`; `10 PIPE-12` |
| crash-resume / ingestion | `resume_menus.py`, `fetch_company_sources.py`, `chunk_company_sources.py` |
| what is stale and why | this pack §5 + `95_Supersession.md` + `10_BuildPipeline.md §3` |
| what is NOT built here | FINALIZE (`finalize_catalog.py`, `10 PIPE-24`), fitness gate (`10 PIPE-37`), catalog→graph sync (`66 §0.R OD-16`) — none exist in this folder |

---

*Assembled 2026-07-07 from a first-hand read of all 21 code files + 13 test files, cross-checked against `10_BuildPipeline.md`, `12_TrackB_FactPipeline.md`, `66_IssuesToBeHandled.md`, `95_Supersession.md`, and `FableAdmissionKernelDesign.md`. Status/reuse map only — no code was edited and no design was created. On any conflict, the topic docs and `95` win over the code.*
