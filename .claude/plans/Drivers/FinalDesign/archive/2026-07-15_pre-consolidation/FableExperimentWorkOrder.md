# FableExperimentWorkOrder — execution work order for FableExperimentPlan v1.0

> **STATUS (2026-07-09): WORK ORDER v1.8 — execution-ready, derived 1:1 from `FableExperimentPlan.md` (sha256 `51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472`).**
> **v1.1 (same day)** = v1.0 + owner decision closing O3: the K-fields gate = the locked DU-03 write gate ("DriverUpdate-worthy fact", significance-agnostic); schema field renamed `market_moving` → `du_worthy` (§3 K-fields · §4 EXP-5 · §7 · §8).
> **v1.2 (same day)** = v1.1 + owner decision closing O1 (+ the company half of O2): the **Phase-1 corpus** = 12 companies in 3 groups — Restaurants base {CAKE, DRI, MCD, YUM, CMG} · SpecialtyRetail adjacent {AZO, ORLY, BBY, ULTA} · Airlines cross-sector contrast {DAL, AAL, LUV} (§3 WP-FA · §8 O1/O2/O7/O8 · §10 D6). **Phase-1 pass ≠ whole-market readiness** — it only unlocks a later, wider sector-wave validation before broad production; do NOT expand the Phase-1 corpus in-program. No bars changed.
> **v1.3 (same day)** = v1.2 + owner decision closing O7/O8: DB verified **frozen at 2026-04-28** → the time-split is EMPTY → leakage control = **company-split + per-event PIT** (§10 D7); F-C catalog roster = **8 Restaurants {CAKE, DRI, MCD, YUM, CMG, SBUX, QSR, TXRH}**, 600-chunk checkpoint KEPT with trim priority **TXRH → QSR → SBUX**; same-industry hold-outs = **{BLMN, SHAK}**; retail + airlines stay out-of-catalog candidate groups. The 12-company F-A event/key corpus is UNCHANGED. No bars changed.
> **v1.4 (same day)** = v1.3 + owner decision on O2 events: the **36-event DRAFT set is ACCEPTED** — mix kept **12/8/8/4/4**; the 32 filing/transcript source_ids pinned verbatim (§3 WP-FA step 5); the 4 news slots (AAL · MCD · BBY · CMG) filled with Fable-drafted article ids; the **catalog-independence leakage rule** added (EXP-5/EXP-6 may overlap mini-catalog companies; producer never sees gold/returns/future context; K-fields gold labeled from event TEXT only, never XBRL). **O2 stays OPEN until the five sign-off review checks are run and recorded** — a failed check swaps the smallest number of events, never a bar. No bars changed.
> **v1.5 (same day)** = v1.4 + owner acceptance of the coverage-check results: **O2 is READY FOR FABLE SIGN-OFF** — the six review checks are RECORDED (twins · OD-12 · guidance · numberless · action_event all PASS; **OD-11 sequential BORDERLINE-accepted** with a pinned contingency); final news IDs pinned incl. the **MCD action-state-diversity swap → `bzNews_42014391`** (E. coli $100M — an occurred/at-risk incident state); the **OD-11 contingency** pinned (ULTA 10-Q → LUV 10-Q `0000092380-26-000047` iff K-fields drafting finds <5 sequential facts); EXP-1 mandatory fixtures stay separate probes. Mix 12/8/8/4/4 unchanged; no bars changed.
> **v1.6 (same day)** = v1.5 + owner decisions closing the pre-run operational items **O4/O5/O6/O9**: K-route real-candidate quotas **LOCKED** (≥40 reuse · ≥40 create · ≥20 skip · ≤20 free/best-available hard; a stratum shortfall is RECORDED and STOPS for Fable/owner review — never silently re-quotaed) · EXP-2 shared-miss **reruns FORBIDDEN without a Fable-named concrete fix** (exhibits always) · the **8,000-char chunk arm KEPT** vs the 40k baseline (no one-paragraph switch; an optional "8k + neighbor rescue" follow-on noted as an experiment option only) · EXP-4's `opus_anchor` arm fires **mechanically ONLY on a Sonnet wrong-SAME** (zero wrong-SAME → skipped, +250 strong calls saved). O10/O11/O12 stay open (result-dependent); O13/O14/O15 unchanged (conditional implementation checks). No bars changed.
> **v1.7 (2026-07-09)** = v1.6 + owner decision closing **O16 (cheap-tier fallback policy)**: if a Haiku cheap arm FAILS its pre-registered bar in EXP-2/EXP-3/EXP-5 — or Fable marks the cheap-tier result inconclusive — Fable may authorize ONE optional fallback arm on **DeepSeek V4 Flash via OpenRouter** (`cheap_fallback` — §1.3 rule · §7 · §8 O16 · §9 row). NEVER by default; Haiku stays the default cheap tier; `none qualifies → Sonnet` stays the terminal fallback; a second, conditional METERED lane via `OPENROUTER_API_KEY` (key absent today — setup deferred to trigger time); a passing fallback arm informs PRODUCTION model strategy only (no in-program engine port). **No bars changed.**
> **v1.8 (2026-07-09)** = v1.7 + Fable/owner execution decision on **K-pairs.v1 drafting**: drafted **0-LLM by the Opus implementer**, with **Fable authoring/rewriting a subset (≥~25%, spread across families)** — instrument independence: the primary tier under test (Sonnet) must not author its own test, and calibration plants are designer-authored by kernel §9.6's own pattern. Fable still adjudicates EVERY record + signs the lock; strata, schema, and all EXP-0 bars unchanged. **Guardrail:** if the Sonnet tier fails EXP-0 and Opus alone qualifies, O10 ratification additionally requires a fresh Fable-authored probe subset (~24 pairs, unseen by the implementer) before the tier is trusted. Scope: K-pairs.v1 only — the other keys' drafting routes are decided at their own drafting time. Saves ~40–60 Sonnet drafting calls. **No bars changed.**
> **What this is:** the HOW for the plan's WHAT. Experiment IDs (EXP-0…EXP-6), sequence, and every pass/fail bar are preserved verbatim from the plan. This file adds only execution detail: paths, queries, schemas, prompt contracts, scoring logic, gates, scheduling, and budget. It amends no design doc.
> **Ambiguity rule:** anything the plan or the design docs do not pin is marked **`OPEN FOR OWNER/FABLE`** (register §8) — an implementer must STOP on those, never improvise. Genuine operationalizations (where the plan's intent needed a concrete recipe) are declared in §10, none changes a bar.
> **Authority:** topic docs + `95` > `90`/`14` > lock candidates (`FableAdmissionKernelDesign.md`, `XBRLIntegrationDesign.md` — still candidates under test) > context packs > this file. All asset paths below verified on disk 2026-07-08.

---

## §0 Implementer protocol (Opus/Sonnet — one experiment at a time)

1. Read §1 (conventions) + §2 (assets) + your EXP block in §4 + its WP dependencies in §3. Open cited design docs ONLY at the cited sections; before trusting any topic-doc prose, check `95_Supersession.md` and `66 §0.2-B` for staleness (D-1/D-2/D-3 stale spots are known).
2. Verify every dependency gate artifact exists (key `.lock.json` files, `catalog_fc/FREEZE.lock.json`, upstream `decision.json` with `outcome: PASS`). Missing → stop.
3. Build/verify your harness pieces (§2.2). Every runner supports `--dry3` (first 3 records only). Show Fable the dry-3 output BEFORE any full arm.
4. Assemble prompts ONLY from the verbatim source blocks named in your EXP's prompt contract. Compute sha256 of each assembled prompt template; record in the run manifest. Prompts are byte-identical across arms except the model slot (the `ab_pair_judge.js` discipline).
5. Resolve model aliases to EXACT model IDs at run start; record in the manifest (§1.3). Never write an alias into a manifest.
6. Write `manifest.json` (`status: "planned"`) → run arms → append-only `responses.jsonl` → update `BUDGET.json` after every arm.
7. Run the scorer (§4 per-EXP command) → `scores.json` (+ gate) → `decision.json`.
8. File exhibits (`wm_*` wrong-merge, `ra_*` rule-ambiguity) to `experiments/exhibits/`. Keys are IMMUTABLE after lock: never edit a key; never re-run a failed arm without Fable's written named-fix + fresh-sample authorization (plan §2.1).
9. Update `experiments/WORKORDER_STATUS.md` (one row per package: state, run_id, gate result, blockers).
10. Anything under-specified for your task: STOP, file an `ra_*` exhibit, add it to the §8 register, and hand back to Fable. Do NOT invent a design choice.

---

## §1 Global conventions

### 1.1 Roots & directory layout (create in WP-0)

All paths repo-relative to `/home/faisal/EventMarketDB`.

```
.claude/plans/Drivers/experiments/            ← EXP_ROOT (new)
├── WORKORDER_STATUS.md                       ← living status board (one row per WP/EXP)
├── BUDGET.json                               ← call ledger (§1.7)
├── fixtures/
│   ├── scope_{restaurants,specialtyretail,airlines}.json + scope_phase1.json   ← WP-FA (resolver outputs + the 12-ticker corpus scope)
│   ├── FA_selection.json                     ← WP-FA (companies + 36 events; Fable-signed)
│   ├── frozen_restaurants/                   ← copied chunks + manifests (never resume the source run)
│   ├── rechunk_para/                         ← paragraph re-chunk output (EXP-2 arms A4/A5)
│   ├── events/<safe_source_id>.json          ← WP-FA Track-B event packets
│   ├── fixture_resolutions.json              ← EXP-1 fixture (company,qname)→fx driver map
│   └── FIXTURES_MANIFEST.json                ← shas of everything above
├── keys/
│   ├── K-pairs/  {protocol.md, K-pairs.v1.jsonl, K-pairs.v1.lock.json, K-pairs.v2.jsonl, K-pairs.v2.lock.json}
│   ├── K-reader/ {protocol.md, K-reader.jsonl, K-reader.lock.json}
│   ├── K-route/  {protocol.md, K-route.jsonl,  K-route.lock.json}
│   ├── K-fields/ {protocol.md, K-fields.jsonl, K-fields.lock.json}
│   └── K-stamp/  {protocol.md, K-stamp.jsonl,  K-stamp.lock.json}
├── catalog_fc/
│   ├── FC_RUN.txt                            ← pointer to the engine run dir (runs/<utc>_restaurants_fc)
│   ├── families_fixture.json                 ← EXP-4B output (PIPE-25 shape)
│   ├── fact_type_decisions_fixture.json      ← EXP-4B memo rows (OD-2 extended fields)
│   ├── terminal_admissions_fixture.json      ← EXP-4B OD-1 memos
│   ├── retrieval_index.jsonl                 ← embedded catalog cards (EXP-3)
│   └── FREEZE.lock.json                      ← shas of catalog.json/approved.json/families/index
├── harness/                                  ← ALL throwaway code (§2.2); never imported by production builds
│   └── scorers/
├── exhibits/                                 ← wm_*.json, ra_*.json (cross-EXP)
└── exp0_graders/ exp1_xbrl/ exp2_reader/ exp3_router/ exp4_judge/ exp5_fields/ exp6_twins/
    └── runs/<utc>[_<arm>]/ {manifest.json, responses.jsonl, views/(EXP-3 only), scores.json, decision.json, logs/}
```

Windows note: on `S:\` never create symlinks; pointers are plain `.txt`/`.json` files. All JSON writes are temp-file + atomic rename, UTF-8, sorted keys where the file is consumed by shas.

### 1.2 Environment & access

- **Neo4j: READ-ONLY.** Reads are standing-approved (`12 §16`); ANY write query = global abort (§1.8). Connection env-first (`NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD`); never the hardcoded fallback URI (10 §12 footgun 16).
- **Billing:** every LLM-spawning workflow starts with the step-0 guard `test -z "$ANTHROPIC_API_KEY" || exit 9`. All LLM calls = in-session workflow `agent()` (subscription). `claude -p` / `claude_agent_sdk` FORBIDDEN (95 #22, 10 §11).
- **Embeddings (the ONE metered lane today; O16's conditional OpenRouter fallback would add a second — §1.3):** OpenAI `text-embedding-3-large`, env `OPENAI_API_KEY`; suggest-only; `min_score=0.60` where a threshold applies (10 §10). Used only by: `mine_pairs.py` (suggester channel) and `retrieval_index.py` (EXP-3 view).
- **Graph facts to respect everywhere** (validated schema refs): `Fact.value`/`is_numeric`/`is_nil`/`decimals` are STRINGS (`is_numeric='1'`); `Period.end_date` may be the string `'null'` (instants); `Report.formType` is camelCase; `Report.created` is an ISO string with TZ; some Fact values are comma-formatted (`"2,898,810,000"`) — parse by stripping commas before float; 12,939 Facts have no `IN_CONTEXT` edge (fail-closed skip + count, XBRL P4f).

### 1.3 Model registry & resolution rule

| Role key | Tier | Candidate exact ID (2026-07-08) | Rule |
|---|---|---|---|
| `cheap` | cheap producer | `claude-haiku-4-5-20251001` | |
| `strong` | strong-judge candidate | Sonnet 5 — resolve alias `sonnet` at run start to the dated snapshot ID | never store the alias (PIPE-32 alias trap) |
| `escalation` | escalation/reference | `claude-opus-4-8` | |
| `fable` | adjudication ONLY | `claude-fable-5` | Fable work happens in the owner's main session, NEVER as a workflow `agent()` arm |
| `cheap_fallback` | OPTIONAL fallback cheap producer (O16) | DeepSeek V4 Flash via OpenRouter — resolve the exact model slug + provider route at trigger time | NEVER by default; fires only per the O16 rule below; exact slug + provider recorded in `manifest.models`; env `OPENROUTER_API_KEY` (absent today — key setup is a trigger-time execution detail) |

Resolution: at run start, resolve every alias via the harness runtime, write the exact ID into `manifest.models`, and use that exact ID for every call in the run. A mid-run CLI/model change = abort the run (restart with a fresh manifest).

**O16 — cheap-tier fallback rule (owner 2026-07-09; policy decided, run conditional).** Scope: the cheap arms only — EXP-2 (A1 + the best-cheap arms A4/A6/A7), EXP-3 (R1), EXP-5 (P3/P4). Trigger: the Haiku cheap arm FAILS its pre-registered bar in that EXP, OR Fable marks the cheap-tier result inconclusive in `decision.json`. On trigger, Fable may authorize ONE fallback arm on `cheap_fallback` (DeepSeek V4 Flash via OpenRouter): same locked key, same sample, byte-identical prompts (model slot only), same bars including the §1.5 invalid-rate ≤ 0.02 reliability gate; run via a direct OpenRouter HTTP runner — NOT workflow `agent()` (the step-0 `ANTHROPIC_API_KEY` guard is unchanged; OpenRouter is a second, conditional METERED lane, cost-capped at 1.5× the failed arm's call count; `BUDGET.json` updated per arm as usual). The fallback never runs by default, never replaces or reruns the failed arm's record, and adds no bars; the fresh-sample rule is not implicated (an additional pre-registered candidate under an unchanged bar, not a rerun of a failed arm). Haiku stays the default cheap tier and `none qualifies → Sonnet` stays the terminal fallback. A PASSING fallback arm produces evidence + a Fable memo for the owner's PRODUCTION model strategy only — in-program downstream steps (e.g., WP-FC-RUN's reader, EXP-3 candidate generation) still use the best qualifying Anthropic tier, because the workflow engine runs `agent()`-only; porting it to OpenRouter is out of scope for this program.

### 1.4 Shared JSON schemas

**run manifest — `exp*/runs/<utc>/manifest.json`**
```jsonc
{
  "exp_id": "EXP-3",
  "run_id": "2026-07-11T14:00:00Z",
  "plan_sha256": "51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472",
  "workorder_sha256": "<sha256 of this file at run time>",
  "git_commit": "<repo HEAD>",
  "models": {"router": "<exact id>", "grader": "<exact id>"},          // role → EXACT resolved id
  "prompt_shas": {"router": "<sha256>", "grader": "<sha256>"},
  "keys": {"K-route": "<sha256 from K-route.lock.json>"},
  "fixtures": {"FREEZE": "<sha256 of FREEZE.lock.json>"},
  "arms": ["haiku_k10full", "sonnet_k10full", "sonnet_k25full", "sonnet_k10stripped"],
  "caps": {"max_calls": 900},
  "counts": {"planned_calls": 640, "made_calls": 0, "invalid_retries": 0},
  "pit": {"visible_from_filter": true},
  "status": "planned|running|scored|PASS|FAIL|ABORTED",
  "started": "<iso>", "finished": null
}
```

**key lock — `keys/<K>/<K>.lock.json>`**
```jsonc
{"file": "K-route.jsonl", "sha256": "<hex>", "n_records": 150,
 "strata": {"planted": 30, "real": 120, "gold_arm": {"ATTACH": 0, "...": 0}},
 "locked_by": "fable", "locked_at": "<iso>", "drafted_by": "<exact model id>",
 "protocol_sha256": "<sha256 of protocol.md>"}
```
Rules: runner MUST verify the key sha before the first call; scorer re-verifies; mismatch = abort the EXP. A locked key is never edited — corrections require a NEW versioned key file + Fable lock + the fresh-sample rule (plan §2.1).

**wrong-merge exhibit — `exhibits/wm_<exp>_<nnnn>.json`**
```jsonc
{"id": "wm_exp3_0001", "exp_id": "EXP-3", "arm": "haiku_k10full", "case_ref": "kt_0117",
 "family": "homonym", "model_output": { }, "gold": { }, "target_visible": true,
 "fable_review": null}   // Fable fills {"verdict": "confirmed|overturned|key_erratum", "note": "..."}
```

**rule-ambiguity exhibit — `exhibits/ra_<nnnn>.json`** (plan §2.7 — filed regardless of pass/fail)
```jsonc
{"id": "ra_0007", "raised_in": "K-fields drafting", "doc": "09", "rule": "OD-13",
 "case_ref": "kf_0042", "description": "<what the rule text under-determines>",
 "adjudicators_split": true, "proposed_amendment": null, "status": "open|proposed|closed"}
```

**scores — `exp*/runs/<utc>/scores.json`**
```jsonc
{"exp_id": "EXP-3", "run_id": "...", "key_sha_verified": true,
 "gate": {"expr": "wrong_merge==0 && retrieval_recall>=0.95 && missed_reuse<=0.15", "pass": true},
 "metrics": { }, "per_arm": { }, "denominators": { },
 "upper_bounds": {"wrong_merge_ub95": "<=3/150 = 2.0%"},          // rule-of-three, plan §2.8
 "exhibit_refs": ["wm_exp3_0001"]}
```

**decision — `exp*/runs/<utc>/decision.json`**
```jsonc
{"exp_id": "EXP-2", "outcome": "PASS|FAIL|PARTIAL",
 "adopted": {"reader_model": "<exact id>", "chunking": "40k|para8k", "runs": 1},
 "failure_attribution": [{"cause": "model|context|rules|chunking|display|runs|tiering", "evidence": "..."}],
 "fable_signoff": null}
```

**BUDGET.json** — `{"global_cap": 4000, "abort_at": 6000, "entries": [{"pkg": "EXP-0", "run_id": "...", "calls": 500, "by_model": {"<id>": 340}}], "totals": {"all": 0, "strong_tier": 0}}`. Update after every arm. Projection rule: before an arm starts, `made + planned_remaining > 1.5 × pkg cap` → ABORT the package and report (plan §8); global `abort_at` = the plan's 1.5× convention applied to the 4,000 total.

### 1.5 Grading conventions ("judged, never string-matched" — plan §2.2)

- Graders = the EXP-0-qualified tier ONLY (two independent instances where the protocol says 2-grader). Grader input = RAW evidence (quotes, names, values) — never detector conclusions, never the other grader's output, never provenance/family labels (kernel §9's smoke-alarm doctrine).
- Batched grading (scorer-driven judgments only, NOT EXP-0/EXP-4 arms): ≤10 independent judgment items per call via `harness/scorers/grade_batch.js`; per-item JSON verdicts; items must be unrelated cases.
- Invalid model output (bad JSON / off-enum): retry ONCE with the same prompt; still invalid → count in `invalid` bucket (never silently coerced). Any arm with `invalid_rate > 0.02` fails on reliability.
- Every "0 wrong in n" is reported with its rule-of-three 95% upper bound `≤3/n` (plan §2.8).

### 1.6 Determinism conventions

- All sampling = h32-seeded deterministic shuffle (the 31-poly UTF-16 rolling hash used by the repair kit, 10 §10); seed string recorded in the manifest.
- All key/fixture files sorted by their id field; ids zero-padded (`kp_0001`).
- Quote locators resolve by exact substring match in the chunk/event text (byte-conservation guarantees presence); if a quote occurs >1×, `occurrence` selects (1-based).
- Scripts that write consumed artifacts: temp + atomic rename; sha recorded in the consuming manifest.

### 1.7 Cost classes

S ≤100 calls · M 101–700 · L 701–1500. "Strong tier" = Sonnet-5 + Opus calls. Ledger per §1.4.

### 1.8 Global stop conditions (any one → stop; report to owner + Fable)

1. **EXP-0 ends with NO qualified grader tier ≤ Opus** → STOP all graded work (EXP-2/3/4/5 scoring, EXP-6 spot-grading). EXP-1 (code-only) continues. Resolution path: Fable-tier grading decision (plan EXP-0 failure action).
2. Any attempted **Neo4j write** from experiment code.
3. `ANTHROPIC_API_KEY` found set in any runner environment (billing guard trip).
4. **Key sha mismatch** at run or scoring time (stops that EXP; investigate before anything else runs).
5. **BUDGET totals ≥ 6,000** calls (1.5× the plan's ~4,000) or any package projected > 1.5× its cap.
6. Any instruction to edit a locked key or re-run a failed arm without a named fix + fresh sample → refuse + stop (retune-to-pass is forbidden, plan §2.1).
NOT a stop: F-C hard-check failures (fixture-grade — fix and re-run, plan §4 F-C); individual arm FAILs (they produce attribution, not aborts).

---

## §2 Asset inventory

### 2.1 REUSE — existing files (paths verified on disk 2026-07-08; never edit except §2.3)

| Path | Use here |
|---|---|
| `.claude/plans/Drivers/workflows/resolve_driver_scope.py` | WP-FA scope; EXP-3 candidate scope (gains `--exclude`, §2.3) |
| `.claude/plans/Drivers/workflows/fetch_company_sources.py` | WP-FA event text (ALL non-news sources, full text) |
| `.claude/plans/Drivers/workflows/chunk_company_sources.py` | fresh-chunk fallback; paragraph re-chunk (gains `--budget-chars`, §2.3); `--verify` conservation check |
| `.claude/plans/Drivers/workflows/menu_build.js` · `build_seed.py` · `resume_menus.py` · `slice_seed.py` · `reconcile.js` · `gate.js` · `assemble_catalog.py` · `validate_catalog.py` · `repair_duplicates.py/.js` | WP-FC mini-catalog build (after §2.3 edit batch) |
| `.claude/plans/Drivers/workflows/ab_stratum.py` · `ab_differ.py` · `ab_pair_judge.js` | selection/stats/pattern donors (PIPE-32 kit); `ab_differ` math imported by `scorers/stats.py` |
| `.claude/plans/Drivers/runs/2026-06-11_204218_restaurants/` (+ `2026-06-09_190054_restaurants`, `2026-06-10_005333_restaurants` as fallbacks) | frozen chunks source (COPY ONLY — footgun 12: never resume) |
| `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py` · `fiscal_math.py` · `pit_time.py` | EXP-6 id/period recipes by READ-ONLY import (`build_guidance_period_id`, `slug`, `canonicalize_source_id`, `period_to_fiscal`) |
| `.claude/plans/Drivers/WIP/unit_probe/unit_resolver.py` | EXP-5/6 value canonicalization by read-only import |
| `.claude/plans/Drivers/WIP/concept_link_revalidation/universe_pull.py` | MENU_Q shape donor for the PIT concept menu (EXP-1) |
| `plans/Drivers/WIP/concept_link_probe/` (repo-root `plans/`, NOT `.claude/plans/` — real trap) | reference only (concept linking NOT re-run, plan §3.1) |
| `.claude/plans/Drivers/Consolidation/XBRL_SliceAxis_Catalog.md` | frozen axis tables + Reproduce Cypher (EXP-1 axes, EXP-5 slice menu) |
| `02_DriverCatalog.md` · `03_Slices_FactScope.md` · `07_DriverUpdate.md` · `09` · `12` · kernel · XBRL design | verbatim prompt-block sources (§4 contracts) |

### 2.2 CREATE later — complete inventory (ALL throwaway; live under `experiments/harness/`; never imported by production Track A/B code)

`xbrl_census.py` · `xbrl_dryrun_materializer.py` · `pit_menu_probe.py` · `news_pull.py` · `retrieval_index.py` · `router_probe.js` · `grader_probe.js` · `judge_probe.js` · `reader_probe.js` · `producer_probe.js` · `stamp_fixture.py` · `stamp_classify.js` · `slice_menu_probe.py` · `mine_pairs.py` · `rechunk.py` · `recall_floor_check.py` · `id_recipe.py` · `key_lint.py` · `sha_lock.py` · `scorers/{score_exp0.py … score_exp6.py, stats.py, fact16_checks.py, grade_batch.js}`.

Rule: if Track B `12 §17` steps 1–2 (`driver_ids.py`, `driver_period_resolver.py`) have shipped before EXP-6 runs, `id_recipe.py` MUST import them instead of its own subset, with a parity assert (drift guard). `*.js` runners follow the existing workflow-script conventions (step-0 billing guard, `MODELS` slot, args parse shim, PIECE_ROWS-style chunked writes + h32 asserts for any large agent Write — footguns 7/8).

### 2.3 MODIFY later — the WP-FC edit batch (production-grade; = Track A `10 §9` steps 1–3 brought forward; exact targets from `WorkflowContextPack.md §5`)

1. `menu_build.js` — RULES block → inlined NAME-01…19 + OD-3 local-role rule (source: `02_DriverCatalog.md`, verbatim); DROP `xbrl_or_null` from MENU_SCHEMA + prompt (`:29-30,:142`); reader `model:'fable'` (`:144`) → `MODELS.reader` slot. Keep return schema null-tolerant (footgun 18).
2. `build_seed.py` — drop first-xbrl copy (`:75-89`) + dead no-op loop (`:116-118` ONLY; line 115 is live).
3. `resume_menus.py` — drop `xbrl_or_null` from `CANDIDATE_FIELDS` (`:35-36,:63`) in lockstep.
4. `reconcile.js` — rulebook pointer → `02` inline (`:15`); delete brand-lines `:84/:90/:96/:104`; INLINE MF-02 ("different flavors of one topic — base vs `_guidance` vs `_surprise` — are NEVER the same driver; never SAME_AS, never a cross-flavor rewrite target") into dedup/G2/Refute prompts (PIPE-16); judges `model:'opus'` → `MODELS.{dedup,gate,refute,d5}` slots.
5. `gate.js` — ADD step-0 billing guard; ADD `MODELS` slot (today pins nothing); ADD args parse shim; rulebook swap; fix brand-admit `:33`.
6. `assemble_catalog.py` — stop emitting `optional_links` (`:104/:236/:410`).
7. `repair_duplicates.py` — `min_score` 0.72→**0.60** (`:82,:110,:491`); embeddings default ON; suggest `limit:0`.
8. `repair_duplicates.js` — model pins → `MODELS` slots.
9. `chunk_company_sources.py` — ADD `--budget-chars` CLI flag (default 40000, backward-compatible).
10. `resolve_driver_scope.py` — ADD `--exclude T1,T2` flag (pins the F-C build to the 8-ticker roster: `--exclude BLMN,SHAK,WING,CBRL,EAT,PZZA` — O7/O8, decided).
11. `workflows/tests/` — lockstep fixture updates dropping `optional_links`/`xbrl_or_null` per the pack §4 table (`test_build_seed`, `test_slice_seed`, `test_assemble_catalog`, `test_validate_catalog_d1`, `test_validate_fold`, `test_fold_catalogs`, `test_fold_repair_review`, `test_repair_duplicates`, `test_resume_menus`, `test_stage0_hardening` fixture noise).
Acceptance for the batch: full workflow test suite green (261+1skip baseline). Prompt-mirror tests (10 §9 step 1's ADD) are Track A's deliverable — NOT an F-C blocker; note in status if absent. Fold/build_tree files untouched (F-C is one leaf; no folds).

### 2.4 NEVER USE

`catalog_first.js` (dead catalog-first G1, 95 #21) · `rescue_review.py` (one-off relic) · `concept_resolver.py` (curated dictionary, 95 #13) · `segment_aliases/` as a grouping mechanism (owner-rejected) · `unit_probe/unit_extract.py` · any `runs/*` NAME data (calibration relics — chunks are the only reusable artifact class, PIPE-33).

---

## §3 Shared-fixture work packages

### WP-0 — bootstrap (S; 0 LLM)
Create the §1.1 tree; write `BUDGET.json` (zeroed), `WORKORDER_STATUS.md` (all rows `PENDING`); record repo `git_commit`; resolve + record candidate model IDs (§1.3); confirm Neo4j read access + `OPENAI_API_KEY` presence (embeddings). Blocks: everything.

### WP-FA — corpus (S; 0 LLM except nothing)

1. **The Phase-1 corpus — ✅ DECIDED (owner 2026-07-08; closes O1 + the company half of O2).** Twelve companies, three groups (Opus recommendation adopted; coverage figures from live-DB reads 2026-07-08 — cheap re-confirm at run time, P19 spirit):

   | Role | Industry (`Industry.name`, DB-confirmed spelling) | Sector | Tickers |
   |---|---|---|---|
   | **Base / calibration** (the F-C catalog vocabulary) | `Restaurants` | ConsumerCyclical | CAKE, DRI, MCD, YUM, CMG |
   | **Adjacent** (same sector; overlapping drivers → legit reuse) | `SpecialtyRetail` | ConsumerCyclical | AZO, ORLY, BBY, ULTA |
   | **Contrast** (cross-sector; same words, different mechanisms) | `Airlines` | Industrials | DAL, AAL, LUV |

   Why (owner's rationale): SpecialtyRetail supplies TRUE cross-company reuse (AZO↔ORLY comparable-store-sales; comps/traffic/ticket vocabulary); Airlines supplies REAL over-merge landmines in real filings (traffic = RPMs · capacity = ASMs · yield · per-ASM unit economics vs the restaurant/retail senses of the same words). 5 of the 12 are 52/53-week filers across 4 fiscal months (DRI-May · AZO-Aug · BBY/ULTA-Jan/Feb · CAKE-Dec/Jan boundary) — the plan's 52/53-week mandatory fixture is satisfied IN-corpus. Every one of the 12 has ≥3 COMPLETED-XBRL 10-Ks · ≥9 10-Qs · ≥12 earnings 8-Ks · ≥10 transcripts · 320+ news (Opus, live counts).
   **Phase-1 scope note (owner 2026-07-08):** this corpus is **PHASE 1**. Passing every Phase-1 gate does NOT prove whole-market readiness — it only unlocks a later, wider **sector-wave validation** before broad production. Do not expand the Phase-1 corpus during this program. Known Phase-1 limits (by design, recorded): non-USD facts thinly covered; financials/utilities/energy vocabulary and pure-macro news attribution out of scope — deferred to the sector wave.
   Mechanics: verify each `Industry.name` spelling (`MATCH (i:Industry) WHERE toLower(i.name) CONTAINS $frag RETURN i.name`), run `resolve_driver_scope.py` once per industry (`--industry "Restaurants" | "SpecialtyRetail" | "Airlines"`) → `fixtures/scope_{restaurants,specialtyretail,airlines}.json`, then write **`fixtures/scope_phase1.json` = exactly the 12 tickers above** (the corpus is the ticker list, NOT the full industries; this file is the scope every fetch pins against).

   **Catalog-side roster (O7/O8 — ✅ DECIDED owner 2026-07-08; catalog machinery, NOT an F-A corpus expansion — the 36-event/key corpus stays the 12 above):**

   | Set | Tickers | Role |
   |---|---|---|
   | F-C mini-catalog build (O8) | CAKE, DRI, MCD, YUM, CMG + **SBUX, QSR, TXRH** | the frozen catalog's vocabulary (Restaurants-only; filings + transcripts ≤ T0; news never enters the leaf build) |
   | Same-industry hold-outs (O7) | **BLMN, SHAK** | never in the catalog; their events feed EXP-3's same-industry candidates (casual-dining + fast-casual — reuse SHOULD fire on comps/traffic/labor/commodity) |
   | Out-of-catalog candidate groups | AZO, ORLY, BBY, ULTA · DAL, AAL, LUV | adjacent reuse + cross-sector over-merge traps (already corpus members) |

   Always-hidden from the catalog: BLMN, SHAK, AZO, ORLY, BBY, ULTA, DAL, AAL, LUV. The Restaurants industry's remaining 4 (WING, CBRL, EAT, PZZA) are unused in Phase 1. **Split axis = COMPANY + per-event PIT, not time** — the DB is verified frozen at **2026-04-28** (max `Report.created` / `Transcript.conference_datetime` / `News.created`), so "events later than the catalog" do not exist (§10 D7).
3. **Frozen chunks:** copy `chunks/ + chunks_manifest.json + sources_manifest.json` from `runs/2026-06-11_204218_restaurants/` → `fixtures/frozen_restaurants/`; run `chunk_company_sources.py --verify` against the copy. Missing/verify-fail → older restaurant runs (§2.1), else FRESH `fetch → chunk` on the scope (both options are PIPE-33-sanctioned); record which in `FIXTURES_MANIFEST.json`. **Pre-run check (d):** confirm `chunks_manifest.json` covers all 8 catalog-roster tickers + BLMN/SHAK (10 of the industry's 14; expected present), and read its per-ticker chunk counts for the 8-ticker roster — the O8 pre-estimate (live chunk-source counts put the 8-set ≈ 478 of the industry's ≈ 805).
4. **Mandatory-fixture discovery + pre-run data checks** (exact property names per validated schema; compute date math in Python — `Period.end_date` may be `'null'`). **Sourcing rules (updated for verified data, see §10 D6):** `filer_5253` = IN-corpus, default pick = **DRI** (clean May 52/53; 5 verified candidates: DRI, AZO, BBY, ULTA, CAKE — FA-Q1 re-confirms) · `multi_registrant_report` = **corpus-WIDE** (Opus verified NONE exists among the 12) — an EXP-1-ONLY dry-run fixture; no keys/events attach to it · `null_periodofreport_report` = corpus-wide IF a COMPLETED-XBRL one exists (the 3 known null-pOR reports are all `xbrl_status=FAILED`), else **SYNTHETIC** (a real COMPLETED report's pull with `periodOfReport` blanked in the harness input — fixture-only, never a graph write) · `precision_dup_pair` = backfilled by the EXP-1 dry-run (unchanged). Queries:
```cypher
-- FA-Q1 52/53-week filers in scope (tolerance 363–371 days on annual duration windows)
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
WHERE c.ticker IN $tickers AND r.formType IN ['10-K','10-K/A'] AND r.xbrl_status='COMPLETED'
MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:IN_CONTEXT]->(:Context)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type='duration' AND p.end_date<>'null'
RETURN c.ticker, p.start_date, p.end_date
-- FA-Q2 multi-registrant filings (run scoped to candidate tickers; full-graph variant only inside xbrl_census with slicing)
MATCH (r:Report)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:IN_CONTEXT]->(:Context)-[:FOR_COMPANY]->(c:Company)
WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A']
WITH r, count(DISTINCT c) AS n WHERE n>1 RETURN r.id, r.formType, n LIMIT 10
-- FA-Q3 null periodOfReport
MATCH (r:Report)-[:HAS_XBRL]->(:XBRLNode)
WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A']
  AND (r.periodOfReport IS NULL OR r.periodOfReport='' OR r.periodOfReport='null')
RETURN count(r) AS n, collect(r.id)[..10] AS sample
-- FA-Q4 earnings 8-Ks per ticker
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$ticker})
WHERE r.formType='8-K' AND r.items CONTAINS '2.02'
RETURN r.id, r.created ORDER BY r.created DESC LIMIT 10
-- FA-Q5 news per ticker (INFLUENCES; News.created is an ISO string; add size(n.body)>500 for substance)
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker:$ticker})
WHERE n.created >= $from AND n.created <= $to
RETURN n.id, n.title, n.created ORDER BY n.created DESC LIMIT 20
-- FA-Q6 action-event backstop (only if sign-off check 1 fails): non-earnings 8-K items
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
WHERE c.ticker IN $tickers AND r.formType='8-K' AND NOT r.items CONTAINS '2.02'
  AND (r.items CONTAINS '5.02' OR r.items CONTAINS '1.01' OR r.items CONTAINS '2.05' OR r.items CONTAINS '8.01')
RETURN c.ticker, r.id, substring(r.created,0,10) AS d, r.items ORDER BY r.created DESC LIMIT 40
-- FA-Q7 text-part sanity (run over the 24 chosen filings before signing)
MATCH (r:Report) WHERE r.id IN $chosen_ids
RETURN r.id, r.formType,
  COUNT { (r)-[:HAS_EXHIBIT]->(:ExhibitContent) } AS exhibits,
  COUNT { (r)-[:HAS_SECTION]->(:ExtractedSectionContent) } AS sections
```
   Transcript pull: verify edge direction first (`MATCH (a)-[:HAS_TRANSCRIPT]->(b) RETURN labels(a), labels(b) LIMIT 1`; Opus-verified 2026-07-08: `Company→Transcript`), then select 8 transcripts by `conference_datetime`.
   **Remaining pre-run checks (Opus's "still to run" — data checks, NOT closed facts):** **(a)** the corpus-wide multi-registrant search (FA-Q2 pattern, run sliced/off-hours) — required because none exists among the 12; **(b)** the COMPLETED-XBRL null-pOR existence query — if it returns 0, P4h uses the synthetic fixture; **(c)** EXP-6 twin-feasibility census per ticker (matched earnings-8-K + same-quarter 10-Q/10-K: `MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company) WHERE c.ticker IN $twelve AND ((r.formType='8-K' AND r.items CONTAINS '2.02') OR r.formType IN ['10-Q','10-K']) RETURN c.ticker, r.formType, r.periodOfReport, r.created ORDER BY c.ticker, r.created`); **(d)** the frozen-run coverage disk check (step 3); **(e)** hold-out overlap: confirm BLMN/SHAK filings/transcripts state the driver families the catalog will coin (comps / traffic / labor / commodity costs) so reuse CAN fire — quick fulltext/section check; **(f)** candidate supply: count harvestable ≤-T0 events across the 9 always-hidden companies — expect ≫ 150 (live: ~50–70 chunk-sources each); **(g)** T0: re-confirm the 2026-04-28 frozen-DB boundary if the graph is ever refreshed (time-split then becomes available as a supplement — §10 D7). Results land in `FIXTURES_MANIFEST.json.preflight`.
5. **The 36-event set — ✅ ACCEPTED by owner 2026-07-08 (mix kept 12/8/8/4/4); coverage checks RECORDED same day (results table below) → READY FOR FABLE SIGN-OFF.** Two pinned review notes ride along: the MCD action-state pick (already applied) and the OD-11 contingency swap (below). Filings/transcripts = the latest of each type per company, Feb–Apr 2026, ≤ T0 (PIT-clean); per-company spread ≤ 4 (DRI/YUM/DAL/AAL/BBY = 4 · MCD/CMG/AZO/ULTA = 3 · CAKE = 2 · ORLY/LUV = 1). Copy verbatim into `FA_selection.json.events`.

   **12 earnings 8-K:** CAKE `0001104659-26-017090` (02-18; +Item 8.01 action, +7.01) · DRI `0000940944-26-000005` (03-19) · MCD `0000063908-26-000032` (02-11; constant-currency → OD-9) · YUM `0001041061-26-000003` (02-04; multi-brand, CC) · CMG `0001058090-26-000007` (02-03) · AZO `0001171843-26-001288` (03-03) · ORLY `0000898173-26-000006` (02-04) · BBY `0000764478-26-000005` (03-03) · ULTA `0001104659-26-027061` (03-12) · DAL `0000027904-26-000020` (04-08; CASM lower-is-better → OD-13) · AAL `0000006201-26-000031` (04-23; +Item 7.01 guidance deck) · LUV `0000092380-26-000044` (04-22).
   **8 transcripts:** DAL `DAL_2026-04-08T10.00` · AAL `AAL_2026-04-23T08.30` · DRI `DRI_2026-03-19T08.30` · YUM `YUM_2026-02-04T08.15` · CMG `CMG_2026-02-03T16.30` · MCD `MCD_2026-02-11T16.30` · BBY `BBY_2026-03-03T08.00` · ULTA `ULTA_2026-03-12T16.30`.
   **8 10-Q (all `xbrl_status='COMPLETED'`; trap in parens):** AZO `0001104659-26-032757` (2026-02-14; 52/53 shifted quarter) · DRI `0000940944-26-000009` (2026-02-22; 52/53, 9-mo YTD) · BBY `0000764478-25-000057` (2025-11-01; 52/53 Q3, 9-mo YTD) · ULTA `0001104659-25-118458` (2025-11-01; 52/53 Q3; **subject to the pinned OD-11 contingency swap below**) · YUM `0001041061-25-000109` (2025-09-30; multi-brand slices) · CAKE `0001104659-25-105631` (2025-09-30; Q3) · DAL `0000027904-26-000022` (2026-03-31; Q1 3mo=YTD edge) · AAL `0000006201-26-000032` (2026-03-31; Q1, unit-cost slices).
   **4 10-K:** DRI `0000940944-25-000038` (FY 2025-05-25; 52/53 May) · AZO `0001104659-25-102611` (FY 2025-08-30; 52/53 Aug) · YUM `0001041061-26-000084` (FY 2025-12-31; multi-brand) · DAL `0000027904-26-000013` (FY 2025-12-31; airline geo regions).
   **4 news — ✅ FINAL (owner 2026-07-08; ids live-verified same day; action states in parens):** AAL `bzNews_50877032` (2026-02-26 — invests $1B in Miami airport expansion; announced/capex) · MCD `bzNews_42014391` (2024-11-15 — spends $100M to move past the E. coli outbreak; **occurred/at-risk incident response** — the owner's action-state-diversity swap; DATE OUTLIER, ≤ T0) · BBY `bzNews_51962983` (2026-04-22 — appoints Jason Bonfig as CEO; announced/leadership) · CMG `bzNews_49256211` (2025-12-08 — authorizes an additional $1.8B for share repurchases; announced/buyback; ≤ T0). Alternates on file if a late veto ever needs one (O2 close-out appendix): AAL `bzNews_40839967` (contract ratified — resolved state) · BBY `bzNews_35439277` (recall — occurred) · CMG `bzNews_45236504` (COO appointment) · MCD `bzNews_43613789` (store expansion).

   **O2 sign-off checklist (owner 2026-07-08 — run + record in `FA_selection.json.review_checks` BEFORE Fable signs; any failure → swap the SMALLEST number of events using FA-Q6/FA-Q7 + the named swap-candidates, never changing the 12/8/8/4/4 mix, any bar, or the design):**
   (1) **action_event coverage ≥ 5** gold-able facts across **≥ 4 action states** (the thinnest lane: 4 news + CAKE's Item 8.01 + 10-K business/risk + transcript Q&A);
   (2) **OD-12 loss/signed examples ≥ 5** (impairments / charges / special items in the selected quarters);
   (3) **OD-11 sequential-basis examples ≥ 5** (airline sequential capacity/CASM framing — restaurants skew YoY);
   (4) **guidance actually present in each selected earnings 8-K** (record the raised/lowered/reaffirmed mix; AAL's 7.01 deck helps);
   (5) **the EXP-1 mandatory fixtures stay SEPARATE from the 36** unless naturally inside (multi-registrant + null-pOR are corpus-wide/synthetic per §10 D6);
   plus **FA-Q7 text-part sanity**: every chosen filing returns extractable exhibits/sections > 0.

   **✅ RECORDED RESULTS (Opus coverage run, live Neo4j; owner-ACCEPTED 2026-07-08 — copy into `FA_selection.json.review_checks` at materialization):**
   | Check | Verdict | Headline evidence |
   |---|---|---|
   | XBRL/text twins | **PASS** (huge margin) | 5,253 consolidated primary facts across the 12 XBRL filings; 52/53 filers alone supply thousands |
   | OD-12 loss/signed | **PASS** (huge margin) | 232 impairment/restructuring/write-off facts (BBY 10-Q 125 · DRI 10-Q 44 · …) + 1,323 negative-signed facts |
   | Guidance in earnings 8-Ks | **PASS** | 11/12 carry guidance language; BBY's guidance arrives via its selected transcript |
   | Numberless / qualitative | **PASS** | 13 numberless-guidance exchanges (DRI 4 · DAL 2 · AAL 2 · …) + qualitative state language across all 8 transcripts |
   | action_event ≥5 / ≥4 states | **PASS with the MCD swap** | 4 quantified news actions + CAKE Item 8.01 + 10-K legal/business + Q&A; MCD E. coli adds the occurred/at-risk state (news otherwise skews "announced") |
   | OD-11 sequential | **BORDERLINE — accepted** | ~6 events carry sequential framing (DAL/CAKE/AAL 10-Q · AAL 8-K · AAL/MCD Q&A), airline-concentrated; prepared remarks likely add more → contingency below |
   | FA-Q7 text sanity | **PASS** | per-filing exhibit/section content confirmed in the coverage run's text checks |
   Drafting note (bonus, not a check): the ISS-16 surprise lane rests on the 12 earnings 8-Ks — at K-fields drafting, confirm each surprise gold fact cites a STATED expectation comparison, never a market-implied one.

   **PINNED OD-11 CONTINGENCY (owner 2026-07-08 — the one live swap):** if K-fields drafting yields **< 5** sequential-basis facts, swap **ULTA 10-Q `0001104659-25-118458` → LUV 10-Q `0000092380-26-000047`** (adds a third airline quarterly: sequential-rich unit cost/capacity + more twins). Mix stays 12/8/8/4/4; four 52/53-week 10-Qs remain (AZO, DRI, BBY, CAKE) plus two 52/53 10-Ks, so EXP-6's ≥10-twins-from-52/53 quota survives the swap. Apply ONLY if short; record the trigger evidence in `review_checks.od11_sequential.evidence`.
```jsonc
{"phase": 1,   // Phase-1 corpus (owner 2026-07-08). Phase-1 pass ≠ whole-market readiness —
               // a later, wider sector-wave validation gates broad production. Never expand in-program.
 "groups": {"base":     {"industry": "Restaurants",    "tickers": ["CAKE","DRI","MCD","YUM","CMG"]},
            "adjacent": {"industry": "SpecialtyRetail","tickers": ["AZO","ORLY","BBY","ULTA"]},
            "contrast": {"industry": "Airlines",       "tickers": ["DAL","AAL","LUV"]}},
 "catalog_side": {   // O7/O8 (owner 2026-07-08) — catalog machinery; NOT part of the 36-event corpus
   "fc_build_tickers": ["CAKE","DRI","MCD","YUM","CMG","SBUX","QSR","TXRH"],
   "holdout_tickers": ["BLMN","SHAK"],
   "trim_priority": ["TXRH","QSR","SBUX"],
   "t0_frozen_db": "2026-04-28"},
 "companies": [{"ticker": "CAKE", "cik": "...", "group": "base", "is_5253": true}],
 "draft_accepted_by_owner": "2026-07-08",   // O2: 36 events accepted + checks RECORDED (step 5 results table); ready for Fable sign-off
 "events": [ /* the 36 events pinned in step 5, copied VERBATIM: {source_id, source_type, ticker, date, why} */ ],
 "review_checks": {   // copy the RECORDED verdicts from step 5's results table (owner-accepted 2026-07-08)
   "xbrl_text_twins":        {"pass": true,  "evidence": "5,253 primary facts / 12 filings"},
   "od12_loss_signed":       {"pass": true,  "evidence": "232 charge facts + 1,323 negative-signed"},
   "guidance_in_8ks":        {"pass": true,  "evidence": "11/12; BBY via its transcript"},
   "numberless_qualitative": {"pass": true,  "evidence": "13 numberless-guidance exchanges + 8 transcripts"},
   "action_event_cov":       {"pass": true,  "evidence": ">=5 across >=4 states WITH the MCD E.coli pick"},
   "od11_sequential":        {"pass": "borderline_accepted", "evidence": "~6 sequential events; LUV-swap contingency pinned (step 5)"},
   "exp1_fixtures_separate": {"pass": true,  "evidence": "multi-registrant + null-pOR corpus-wide/synthetic; precision-dup via EXP-1 dry run"},
   "text_part_sanity":       {"pass": true,  "evidence": "FA-Q7 content hits per filing (coverage run)"}},
 "mandatory_fixtures": {
   "filer_5253": "<in-corpus ticker; 5 verified candidates: DRI, AZO, BBY, ULTA, CAKE (FA-Q1 re-confirms)>",
   "multi_registrant_report": "<rep id — corpus-WIDE, EXP-1-only fixture (none exists among the 12)>",
   "null_periodofreport_report": "<rep id if a COMPLETED-XBRL one exists, else \"SYNTHETIC\" (P4h harness fixture)>",
   "precision_dup_pair_report": "<rep id — found by EXP-1 dry-run, backfilled>"},
 "signed_off_by": null}
```
6. **Event packets:** filings/transcripts via `fetch_company_sources.py` per company — all 12 corpus companies, scope-pinned against `fixtures/scope_phase1.json` → select the 36 by `source_id`; news via `harness/news_pull.py` (FA-Q5 + `title/teaser/body`). Write `fixtures/events/<safe_source_id>.json`:
```jsonc
{"source_id": "...", "source_type": "8k|transcript|10q|10k|news", "ticker": "...", "cik": "...",
 "date": "<Report.created | Transcript.conference_datetime | News.created>",
 "fye_month": 12,   // = month of the company's latest 10-K periodOfReport (deterministic recipe)
 "text_parts": [{"part": "exhibit_99_1|mdna|risk|business|prepared_remarks|qa|items|body", "content": "..."}],
 "sha256": "<of concatenated content>"}
```
Parallel with: everything. Blocks: K-reader/K-fields/K-route drafting, EXP-1 dry-run, EXP-5.

### WP-KEYS — the five keys (drafting M ≈120 Sonnet calls total; adjudication = Fable, main session)

Common protocol (every `keys/<K>/protocol.md` restates it + key-specific rules): drafts by `strong` (Sonnet) following the protocol (**K-pairs.v1 exception — v1.8:** drafted 0-LLM by the Opus implementer + a Fable-authored/rewritten subset; independence rationale + the Opus-only-qualification guardrail in the v1.8 header note); `harness/key_lint.py` validates schema + strata quotas; **Fable adjudicates every record** (hard calls double-adjudicated; splits → `ra_*` exhibits); `harness/sha_lock.py` writes the `.lock.json`. Locked keys are immutable (§1.4).

**K-pairs** (`kp_` records; v1 = planted 160, locks before EXP-0; v2 = v1 + 90 mined, locks before EXP-4A):
- **v2 additions (owner 2026-07-11):** a PORTION family (gold-DIFFERENT `current_rpo`/`rpo`, `funded_backlog`/`backlog` + one window-vs-portion trap) — GATES OD-19 (wrong-same = 0 required); one sibling-instrument pair (`sofr_rate` vs `fed_funds_rate`, gold-DIFFERENT) — proves the NAME-07 precedence clause.
```jsonc
{"pair_id": "kp_0001", "provenance": "planted|mined",
 "family": "bookings_billings|adjusted_vs_gaap|gross_net|segment_consolidated|deferred_recognized|genus_species|benchmark_siblings|cause_consequence|channel_homonym|ownership_axis|per_x|cross_flavor|synonym|mined",
 "side_a": {"name": "...", "quotes": ["<≥1 verbatim-style quote>"], "slice_tokens": [], "per_x": null, "industry": "...", "fact_type": null},
 "side_b": { ... }, "rival": null,          // optional third card name+quote for check-4 cases
 "gold": "SAME|DIFFERENT", "gold_rationale": "<1-2 sentences>", "hard": false}
```
Strata: 110 planted-DIFFERENT (≥8 per family across the ≥9 families; plan §4) + 50 planted-SAME synonyms. Planted quotes may be synthetic-but-realistic filing language (they are calibration plants — kernel §9.6's own pattern). Where the Phase-1 corpus provides them, PREFER its real language: planted-DIFFERENT from the cross-domain homonym set (traffic = guest count vs store foot-traffic vs RPMs · capacity = throughput vs ASMs · yield · unit = store vs per-ASM · the "comparable/comps" senses); planted-SAME from real synonym clusters (AZO↔ORLY comparable-store-sales; multi-brand system-sales). Synthetic remains the legal fallback. Mined 90 (v2): run `harness/mine_pairs.py` on the frozen F-C catalog — suggestion channels exactly `token-overlap ∪ rare-token ∪ embeddings(top_k=5, min_score=0.60)` (the repair suggester's channels) → `ab_stratum.py`-style selection stratified by channel + score band → Fable adjudicates gold.

**K-reader** (`kr_`; 40 chunks; locks before EXP-2):
```jsonc
{"key_id": "kr_0001", "source_id": "...", "ticker": "...",
 "chunk_ref": {"file": "<frozen chunk filename>"},
 "evidence_locator": {"quote": "<verbatim ≥60 chars from the chunk>", "occurrence": 1},
 "gold_cause": {"proposed_name": "<NAME-rule-canonical form>", "acceptable_alt_names": ["..."],
                "slice_expected": null, "per_x": null},
 "rule_refs": ["NAME-04", "OD-3"], "hard": false}
```
Chunk sample: 40 from `chunks_manifest.json`, h32-seeded, stratified by source_type proportional to corpus mix; the SAMPLE LIST is part of the protocol (pre-registered). Key = every admissible cause in those chunks under NAME-01…19 + OD-3 (drafts propose; Fable prunes/adds). `acceptable_alt_names` guide the grader; matching is judged, never string.

**K-route** (`kt_`; 150; locks before EXP-3; needs frozen F-C + candidate pool):
```jsonc
{"key_id": "kt_0001",
 "candidate": {"proposed_name": "...", "quote": "...", "slice_tokens": [], "per_x": null,
               "event_time": "<ISO>", "source_id": "...", "ticker": "...", "industry": "..."},
 "gold_arm": "ATTACH|ADOPT|CLAIM|CREATE|SKIP", "gold_target": "<catalog driver_name|null>",
 "planted_family": "P1|P3|P4|P5|P6|P7|P8|P9|null", "rationale": "..."}
```
120 real candidates (generation recipe in EXP-3) + 30 planted probes = the gauntlet families (P1 three-demand-stories · P3 own-segment-vs-external · P4 measurement words · P5 per-X trio · P6 brand/geo slice traps · P7 same-words-different-mechanism homonyms · P8 genus-species · P9 benchmark identity — kernel §8.3; draw P7-style homonyms from the corpus's real airline/retail language where available). Real-candidate strata quotas — **✅ LOCKED (owner 2026-07-08; closes O4):** ≥40 reuse-gold · ≥40 create-gold · ≥20 skip-gold · remaining ≤20 free / best-available HARD real cases (= the 120 real; + 30 planted = 150). **Shortfall rule:** if any required stratum cannot be filled from real candidate data, RECORD the shortfall in the protocol and **STOP for Fable/owner review** — quotas are never silently changed.

**K-fields** (`kf_`; ~150 gold facts over the 36 events; locks before EXP-5):
```jsonc
{"key_id": "kf_0001", "source_id": "...", "ticker": "...", "lane": "metric|guidance|surprise|action_event",
 "du_worthy": true,   // the locked DU-03 gate (owner 2026-07-08, closes O3): "DriverUpdate-worthy fact" —
                      // NOT stock-move attribution (that is EXPLAINED_BY's job, DU-21…24).
                      // false = OPTIONAL near-miss exemplar row (gate-dropped bare mention / boilerplate),
                      // excluded from EVERY recall denominator; adjudication context + precision spot-checks only.
 "gold_item": { /* the FULL FACT-17b item, incl. transients — field list §4/EXP-5 */ },
 "gold_extra": {"expectation_comparison_present": false},   // ISS-16 trigger ground truth
 "trap_class": "shape_point|OD-12_loss_floor|OD-11_sequential|OD-9_spans|OD-13_favorability|ISS-16_routing|slice_menu|unknown_axis|OD-17_portion|T1-05_menu_ambiguous|null"}
```
**The gate — ✅ DECIDED (owner 2026-07-08; closes O3): `du_worthy` ≡ the locked DU-03 write gate ("DriverUpdate-worthy fact"), significance-agnostic.** A gold fact exists iff the source STATES a real, non-boilerplate fact about a driver in one of the four lanes. DU-03 verbatim (`07` :25-29, `[LOCKED]`): *"does this event carry a real fact about the driver (state/change/surprise/guidance/action)? A bare mention → NO DriverUpdate. Generic risk boilerplate ('litigation could harm us', 'weather may affect results') → dropped."* Explicitly NOT part of the gate — no recurrence, no "must be a change", no materiality/significance bar, no realized-price-move test: those are read-time filters, never write gates (DU-01 · `11` T11.1 · `95` #4/#5). Numberless/qualitative facts COUNT (DU-05; ~19.2% of real facts are numberless — `09` §1). Threat-like language: the one locked lane-level boundary is DU-11's `at_risk` STRICT (a specific, current, source-flagged adverse threat = fact; generic = drop); fuzzy-middle cases on the other lanes have NO locked boundary — file `ra_*` exhibits at drafting, never invent one. Stock-move attribution is `EXPLAINED_BY` (DU-21…24) and NEVER enters this gate — the field is named `du_worthy` so no implementer misreads it as attribution; wherever the plan says "market-moving facts", read `du_worthy==true`. Two axes, never blurred in gold labeling: the GATE decides fact-vs-no-fact; `trap_class` grades how an admitted fact is ENCODED (`12 §12.3` field classes). The ~150 target counts `du_worthy:true` facts only. Trap quotas: every `12 §12.3` planted class + OD-9/11/12/13/14 + ISS-16 represented ≥5× each. An expectation comparison yields TWO gold facts (ISS-16/OD-21): a reported ACTUAL → metric + surprise (`actual_vs_*`); a forward GUIDE-vs-Street → guidance + surprise (`guidance_vs_consensus`); a grounded NUMBERLESS surprise still gets its numberless home sibling (`driver_state=unknown` + quote); an UNGROUNDED "results beat" (no identifiable metric) is parked. **Adjudication independence (owner 2026-07-08):** K-fields gold is labeled from the event TEXT ONLY — drafters and adjudicators must NOT consult the filing's XBRL facts while labeling (EXP-6's text-vs-XBRL twin comparison would otherwise be circular); the producer is never shown gold labels, realized returns, or any > event_time context. **Two drafting-time hooks (O2 close-out):** (a) count sequential-basis facts as drafting proceeds — if the total lands **< 5**, fire the pinned OD-11 contingency (§3 WP-FA step 5: ULTA 10-Q → LUV 10-Q) BEFORE locking this key; (b) every surprise-lane gold fact must cite a STATED expectation comparison from the text, never a market-implied one.

**K-stamp** (`ks_`; ~100; locks before EXP-4B):
```jsonc
{"key_id": "ks_0001", "driver_name": "...",
 "evidence": [{"company": "...", "source_type": "...", "source_id": "...", "date": "...", "quote": "..."}],
 "gold_fact_type": "metric|guidance|surprise|action_event",
 "gold_base_metric": "<name|null>", "gold_latent_expected": false,
 "class": "suffixed|deceptive_suffix|bare_metric|bare_action|latent_base|cross_flavor_trap"}
```
Mix: real F-C records (post-run) + planted (all 5 `deceptive_suffix` are plants of the `regulatory_guidance` class — residue is a document/action, not a metric). Strata: 30 suffixed (incl. the 5 plants) · 40 bare metric/action-ambiguous (OD-2 worked-example style: `bookings`, `buyback`, `dividend`, `restructuring`) · 15 latent-base (OD-1) · 15 cross-flavor F3 traps.

### WP-FC — mini-catalog (two stages)

**WP-FC-EDITS** (code work; before EXP-2): apply §2.3 items 1–11; suite green. Unblocks EXP-2 (the inlined reader prompt is EXP-2's rulebook block) and WP-FC-RUN.

**WP-FC-RUN** (after EXP-2's `decision.json`; **O8 ✅ DECIDED owner 2026-07-08**): run the existing engine via the in-session Workflow tool — `menu_build.js {industry: "Restaurants"}` with the company scope pinned BEFORE fetch to the **8-ticker catalog roster** {CAKE, DRI, MCD, YUM, CMG, SBUX, QSR, TXRH} via `resolve_driver_scope.py --industry "Restaurants" --exclude BLMN,SHAK,WING,CBRL,EAT,PZZA` (§2.3 item 10). Build inputs = the roster's filings + transcripts ≤ T0 only (news never enters the leaf build). Then `reconcile.js` → `repair_duplicates.js` → `validate_catalog.py` (WITH `approved.json` — footgun 3). Models: `MODELS.reader` = EXP-2's adopted reader; `MODELS.{dedup,gate,refute,d5,repair}` = `strong` (Sonnet — kernel §11.0 owner default; exact IDs in the run's `manifest.models`).
**FiscalAI source snapshot note (2026-07-10):** KPI/segment files now live at `data/fiscal_ai_segments/runs/2026-05-07/` (`kpi_catalog/`, `raw/`, CSV/SQLite snapshots, and `xbrl_link_audit/`). This is source/audit provenance only; it does not change the WP-FC-RUN rule that the reader pipeline builds the catalog.
**FiscalAI holistic reference:** `data/fiscal_ai_segments/runs/2026-07-10/viz/kpi_reference.csv` is the current one-file KPI/segment reference view for audits/browsing; it is not a seeding or scoring input unless separately ruled.
**FiscalAI coverage-audit reminder:** after F-C freeze, FiscalAI KPI labels may be used as coverage QA only (for example: covered / valid_missing / needs_text / not_driver), never as catalog seeding, patching, scoring, or a rerun trigger unless Fable/owner later makes a separate ruling.
**Budget checkpoint (KEPT, owner 2026-07-08):** after chunking, if fresh chunk-file count > 600 → **trim the density adds in reverse priority: drop TXRH, re-count; still > 600 → drop QSR; then SBUX** (floor = the 5 corpus restaurants; no other trims). Pre-estimate before fetch from the frozen 2026-06-11 manifest (check d: 8-set ≈ 478 — expected UNDER the cap); the FRESH manifest is definitive.
**Hard checks** (fixture-grade; fix-and-rerun allowed — plan §4 F-C): `validation_exit.json` exit==0 incl. D1 · brand/measurement token scan = deterministic lint over coined names against (a) measurement tokens {adjusted, diluted, constant_currency, organic, pro_forma, gaap, non_gaap, reported, as_reported} and (b) a gazetteer = scope companies' names/tickers ∪ their XBRL Member labels (via the EXP-5 slice-menu query) — hits reviewed by Fable (NAME-11 ladder survivors are legal) · per-X spot-check · same-name convergence PRESENT across companies (PIPE-20; absence = override-layer failure) · `harness/recall_floor_check.py` (tickers with ≥2000 content chars and 0 candidates — the PIPE-10 ADD is unbuilt; this is its fixture stand-in) · D5/Refute traffic counts reported.
Then EXP-4B stamps → write `catalog_fc/{families_fixture.json, fact_type_decisions_fixture.json, terminal_admissions_fixture.json}` → `harness/retrieval_index.py` embeds cards → `FREEZE.lock.json` (shas of catalog.json + approved.json + validation_exit.json + the three fixture files + retrieval_index.jsonl). F-C NEVER feeds the real fitness gate.

---

## §4 Experiment work packages

> Bars quoted from the plan are BINDING and verbatim. Every runner: billing guard, manifest, key-sha verify, `--dry3` gate, budget update.

---

### EXP-0 — Grader + key instrument validation

**Plan bars (verbatim):** a tier qualifies iff wrong-SAME = **0/110** AND false-refusal ≤ **10%**; shared miss on a family ⇒ generation-blindness flag + discount + kernel §14.2 escalation. Cap ~500 small judge calls.

- **Inputs:** `keys/K-pairs/K-pairs.v1.jsonl` (+lock) — planted subset only (110 DIFFERENT + 50 SAME).
- **Reuse:** `ab_pair_judge.js` pattern (byte-identical prompt across arms; model slot only). **Create:** `harness/grader_probe.js`, `harness/scorers/score_exp0.py`.
- **Arms:** `g_sonnet_a`, `g_sonnet_b` (two independent agent() instances, zero shared context), `g_opus`. One pair per call; h32-shuffled order per arm.
- **Prompt contract (grader):** input = the pair's two sides RAW (`name, quotes, slice_tokens, per_x, industry` per side) — never family/provenance/rival labels. Framing (sources: kernel §10.3 recovery-grader + PIPE-13 Refute): default-DIFFERENT ("treat as different causes unless the evidence compels sameness"); decide via the 3-check — same OBJECT, same SCOPE (business population + ownership class), same MECHANISM — citing a verbatim quote from EACH side; over-merge is permanent, over-split is cheap. Output:
```jsonc
{"pair_id": "kp_0001", "verdict": "SAME|DIFFERENT", "cited_a": "<verbatim>", "cited_b": "<verbatim>", "reason": "<≤60 words>"}
```
- **Scoring logic (`score_exp0.py`):** per arm g: `wrong_same(g) = |{gold=DIFFERENT ∧ verdict=SAME}|` /110 · `false_refusal(g) = |{gold=SAME ∧ verdict=DIFFERENT}|` /50 · `invalid_rate(g)` (§1.5) · per-family table · `shared_miss(family) = |{gold=DIFF ∧ BOTH sonnet instances said SAME}|`.
- **PASS check:** `python3 harness/scorers/score_exp0.py --run <dir>` → gate `EXISTS tier T: ∀ instance g∈T: wrong_same(g)==0 && false_refusal(g)<=0.10 && invalid_rate(g)<=0.02` (sonnet tier = both instances; opus = its one). Qualified tier written to `decision.json.adopted.grader_tier`.
- **Parallel:** with EXP-1, WP-FA, WP-FC-EDITS. **Blocks:** all graded scoring (EXP-2/3/4/5, EXP-6 spot-grading). **Stops whole run:** no tier qualifies (§1.8.1).
- **Calls/cost:** 160×3 + retries ≈ 500 · class M (all strong-tier).
- **Decisions:** **O10** Fable ratifies the grader tier + records per-family blindness discounts in `decision.json`.

---

### EXP-1 — XBRL substrate reality + determinism probe (code-only, zero LLM)

**Plan bars (verbatim):** 100% field determinism (dry X-XL0) · period classifier: 0 windows unclassifiable except the declared `exact_range`+WARN fallback · every skip class counted · PIT menu proof passes · ANY two-ways-to-code-it ambiguity = FAIL.

- **Inputs:** Neo4j (read-only); `FA_selection.json` (the 12 Phase-1 companies / ~60 filings + the mandatory fixtures — multi-registrant and null-pOR may be out-of-corpus or synthetic per §3 WP-FA step 4 and §10 D6); `XBRLIntegrationDesign.md` §5.2/§5.3 pins P1–P17 (the spec under test); `fixtures/fixture_resolutions.json`.
- **Fixture-resolution recipe (PINNED):** per FA company C: candidate concepts = concepts of numeric non-nil Facts in C's 10-K/10-Q with usage ≥4 (2023–2026), ranked by usage, top ≤40; driver name = `"fx_" + slug(qname local part)`; deliberately include ≥5 non-whitelist-unit concepts per company where they exist (to exercise skip counters). 1:1 qname→driver (see §10-D1).
- **Create:** `harness/xbrl_census.py` → `census.json`; `harness/xbrl_dryrun_materializer.py` → `materialized.jsonl` + `skips.jsonl` + `determinism_report.json` + `comparator_census.json` + `collision_census.json` + `ambiguity_register.json`; `harness/pit_menu_probe.py` → `pit_menu_proof.json`; `harness/scorers/score_exp1.py`.
- **Step 0 — schema binding (mandatory; P19's own instruction):** record in `census.json.schema_bindings`: (a) Fact→Period path in use (`(f)-[:HAS_PERIOD]->` direct vs via Context — verify both, pick per XBRL design's `HAS_PERIOD → Period` off the Fact, fall back to Context path where absent); (b) axis↔member pairing method — candidates: `(f)-[:FACT_DIMENSION]->(d:Dimension)-[:HAS_DOMAIN]->(:Domain)-[:HAS_MEMBER]->(m)` reachability test per fact, or `Context.member_u_ids` parsing; if NEITHER yields a deterministic pairing for multi-axis facts → skip those facts fail-closed + count + **O13**; (c) `Concept.balance` presence (if absent, the PIT menu drops that column — **O15**).
- **Census queries (samples/LIMIT where full scans are heavy; Fact ≈ 9.9M):** unit inventory `MATCH (f:Fact)-[:HAS_UNIT]->(u:Unit) RETURN u.name, u.is_divide, count(f) ORDER BY count(f) DESC LIMIT 100` · no-context cohort `MATCH (f:Fact) WHERE NOT EXISTS {(f)-[:IN_CONTEXT]->()} RETURN count(f)` · null-periodOfReport (FA-Q3) · `xbrl_status` distribution · decimals distribution (1M-fact sample slice) · comma-value count (sample slice) · multi-registrant (FA-Q2 pattern, form-type/year slices) · raw-duplicate rate (python-side over the dry-run pull).
- **Per-report pull (materializer input):**
```cypher
MATCH (r:Report {id:$report_id})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.is_numeric='1' AND f.is_nil='0'
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context) OPTIONAL MATCH (ctx)-[:FOR_COMPANY]->(rc:Company)
OPTIONAL MATCH (f)-[:HAS_PERIOD]->(p:Period)   // per binding (a)
OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit)
RETURN f.id AS fact_id, con.qname AS qname, f.value AS value, f.decimals AS decimals,
       ctx.context_id AS context_id, ctx.member_u_ids AS member_u_ids, rc.ticker AS registrant,
       p.period_type AS ptype, p.start_date AS pstart, p.end_date AS pend,
       u.name AS unit_name, u.is_divide AS is_divide
```
  (+ the dimension/member pull per binding (b); comma-stripping before float; `pend='null'` handling.)
- **Dry-run materializer:** implements XBRL §5.2 steps 1–8 EXACTLY (P4a–P4j: entity-scoping via `IN_CONTEXT→FOR_COMPANY` incl. no-context skip; unit whitelist {`iso4217:USD`→money, `shares`→count, `iso4217:USD/shares`→usd-per-share} else skip+count; intra-filing raw-duplicate drop then the P4g collision rule (agree-within-coarser-decimals → keep highest precision; beyond → skip scope + `xbrl_internal_conflict`); axes via the frozen table from `XBRL_SliceAxis_Catalog.md` (SLICE_AXES kind / unknown-axis hex sentinel / NON_SLICE+elimination → skip whole fact); §5.3 period classifier P14 incl. company-actual fiscal ends + 364/371 handling + quarter>Q1-YTD + `exact_range`+WARN catch-all + instants `period_scope=null`; primary ⇔ period end == `periodOfReport` with the null-pOR P4h fallback; id `du:{R.id}:{fx_driver}:{fact_scope}`). Writes NOTHING to Neo4j.
- **Materialized row schema (`materialized.jsonl`):**
```jsonc
{"du_id": "du:...", "report_id": "...", "registrant": "...", "driver": "fx_revenues",
 "qname": "us-gaap:Revenues", "xbrl_fact_id": "...", "value_canonical": -2000.0, "decimals": "-6",
 "level_unit": "m_usd", "period": {"gp_id": "gp_2026-01-01_2026-03-31", "period_scope": "quarter",
   "time_type": "duration", "fiscal_year": 2026, "fiscal_quarter": 1},
 "slices": ["segment:north_america"], "primary": true, "write_reason": "primary|backfill|restatement"}
```
- **Determinism (two halves):** (1) run the whole materializer TWICE in fresh processes → output shas identical; (2) dry X-XL0: an INDEPENDENT verifier function re-reads each materialized row's source Fact raw and re-derives every field — `field_match_rate` must be 1.0.
- **PIT menu probe (FACT-30's verified gap — the ADD):**
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$ticker})
WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] AND r.xbrl_status='COMPLETED' AND r.created <= $event_time
MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(:Context)
WHERE f.is_numeric='1'
RETURN con.qname AS qname, con.label AS label, con.period_type AS period_type, count(f) AS usage
ORDER BY usage DESC
```
  Proof on 5 FA events: every menu concept's earliest carrying `r.created` ≤ event_time AND a programmatically-found post-event-only concept is ABSENT from the menu.
- **comparator_census (P15 data check):** over `materialized.jsonl`: fraction of quarter/ytd rows having a prior row in the same (registrant, driver, slices, series) with window end within ±7 days of (end − 1 year); annual analog.
- **collision_census (see §10-D1):** (a) post-dedup multi-row (registrant, period, qname, fact_scope) groups — MUST be 0 (P4g working); (b) informational confusability base rate: (registrant, period) pairs where ≥2 different qnames carry identical canonical values.
- **PASS check:** `score_exp1.py` gate = `determinism_shas_equal && field_match_rate==1.0 && unclassified_windows==0 && pit_menu_proof.pass && len(ambiguity_register)==0`. Every `ambiguity_register` entry (a place where two implementers could code differently) = a named pin-amendment proposal for the XBRL ratification bundle.
- **Parallel:** fully parallel from WP-0 (census) / WP-FA (dry-run). **Blocks:** EXP-6; the owner's XBRL ratification. **Stops whole run:** never (code-only), but FAIL blocks ratification.
- **Calls/cost:** 0 LLM · class S. Ops note: run heavy scans in slices; off-hours if slow.
- **Decisions:** **O12/O13/O15**; Fable turns `ambiguity_register` into the pin-amendment list.

---

### EXP-2 — Blind-producer grid

**Plan bars (verbatim):** cheap reader ADOPTED only at recall ≥ (strong arm − 2 pts) AND precision within the Wilson noise gate · paragraph chunks adopted only if recall AND precision non-inferior AND cost drops · multi-run union adopted only if recall gain ≥ 5 pts AND junk stays under the single-run precision bar. Cap ≤ ~350 reader calls + grading.

- **Inputs:** `fixtures/frozen_restaurants/` chunks; `keys/K-reader/` (locked; its protocol pre-registers the 40-chunk sample); the WP-FC-EDITS reader prompt (menu_build.js post-edit RULES block = the inlined `02` NAME-01…19 + OD-3).
- **Create:** `harness/reader_probe.js` (one blind reader call per chunk×arm, byte-identical prompt except MODELS slot + rules block variant), `harness/rechunk.py` (re-chunk the 40 key chunks' source events via `chunk_company_sources.py --budget-chars 8000` — **O6 ✅ DECIDED (owner 2026-07-08): the 8,000-char arm is KEPT against the 40k baseline; do NOT switch to one-paragraph chunks**), `harness/scorers/score_exp2.py`.
- **Optional follow-on — "8k + neighbor rescue" (owner 2026-07-08; an experiment OPTION, never production law):** trigger = the 8k arm loses recall specifically because facts cross chunk boundaries (boundary-adjacent misses in the attribution tables). Shape: extract from 8k chunks first → rerun ONLY the flagged incomplete/ambiguous items with the adjacent chunk's context appended → adopt only if recall improves WITHOUT added junk (same Wilson discipline, fresh sample). Not one of the 8 pre-registered arms; spec it fully only if triggered.
- **Arms (8, pre-registered):**
  | Arm id | model | chunks | runs | rules |
  |---|---|---|---|---|
  | A1 `haiku_40k_1` | cheap | 40k | 1 | full |
  | A2 `sonnet_40k_1` | strong | 40k | 1 | full |
  | A3 `opus_40k_1` | escalation | 40k | 1 | full |
  | A4 `cheap_para_1` | best-cheap | para-8k | 1 | full |
  | A5 `opus_para_1` | escalation | para-8k | 1 | full |
  | A6 `cheap_40k_2u` | best-cheap | 40k | 2 (union) | full |
  | A7 `cheap_40k_3u` | best-cheap | 40k | 3 (union) | full |
  | A8 `cheap_40k_norules` | best-cheap | 40k | 1 | ABLATED |
  **best-cheap selection rule (pinned):** the cheaper of {Haiku, Sonnet} whose A1/A2 judged recall ≥ max(A1,A2,A3) − 2 pts; none qualifies → Sonnet. **Ablated rules text (pinned verbatim):** `RULES: From this chunk only, list reusable market/company cause candidates. Each candidate: a lowercase_underscore name (letters/digits/_, starts with a letter) + one verbatim quote from the chunk. Do not invent causes not stated in the text.`
- **Reader output schema:** the post-edit MENU_SCHEMA (no `xbrl_or_null`): `{"chunk_id": "...", "candidates": [{"proposed_name": "...", "quote": "<verbatim>", "evidence": {"company","source_type","source_id","date"}, "per_x": null, "slice_note": null}]}`. Null-tolerant (footgun 18). Readers receive the chunk text inline in the packet (probe-served; the Bash-`cat` rule applies to the production flow, not this probe).
- **Scoring logic:** per key item k, per arm a: `covered(a,k)` = grader-judged — do the candidates from the chunk(s) containing k's `evidence_locator` include one capturing the same cause (gold name + alts shown to the grader as REFERENCE, judged not string-matched)? `recall(a) = Σcovered/|K|`. `precision(a)` = judged-valid fraction of 60 h32-sampled candidates of that arm (valid = a real reusable, source-grounded cause named within the rules — grader cites the quote). Union arms: candidate set = per-chunk union deduped by `norm(name)`; `junk(run j) = 1 − precision(new items first appearing in run j)`. Grading batched ≤10 (§1.5). Cost/chunk recorded per arm.
- **PASS check:** `score_exp2.py` emits the three adoption verdicts per the verbatim bars (Wilson gate via `stats.py`, `ab_differ` math) + attribution tables: per-item miss lists by arm · misses shared by ALL arms (→ `ra_*` exhibits ALWAYS; **rerun rule ✅ DECIDED — owner 2026-07-08, closes O5: NO automatic rerun. A rerun happens ONLY after Fable names a CONCRETE fix** — rule wording · prompt wording · scorer/key bug · chunk-boundary problem · missing source context; **a rerun without a named fix is FORBIDDEN**; the fresh-sample rule of §2 still applies) · A8-vs-best delta (rules doing work?) · para-vs-40k miss overlap (boundary effects). `decision.json.adopted = {reader_model, chunking, runs}`.
- **Parallel:** needs EXP-0 (grading) + WP-FC-EDITS + K-reader lock; runs parallel with WP-FA leftovers. **Blocks:** WP-FC-RUN (reader choice), EXP-3 candidate generation. **Stops whole run:** never.
- **Calls/cost:** readers 8 arms ≈ 360 (A6/A7 add runs on 40 chunks each) · grading ≈ 100–140 batched calls · class M.
- **Decisions:** adoption verdicts → Fable sign-off in `decision.json`; **O5**, **O6**.

---

### EXP-3 — Admission routing + reuse-display (G1) probe

**Plan bars (verbatim):** wrong merges = **0** per surviving arm (0/150 ⇒ ≤2% upper bound; the fine 0.1% bound stays the fitness gate's) · retrieval recall ≥ **95%** · missed-reuse ≤ **15%**. Cap ~600 router calls + suggest-only embeddings.

- **Prereqs:** `catalog_fc/FREEZE.lock.json` (post EXP-4B stamps) · `retrieval_index.jsonl` · `keys/K-route/` locked · EXP-0 grader.
- **Candidate generation (recipe — O7 ✅ DECIDED owner 2026-07-08; leakage control = COMPANY-split + per-event PIT, §10 D7):** candidate companies = the **9 always-hidden tickers** — same-industry hold-outs **BLMN, SHAK** (casual-dining + fast-casual; reuse SHOULD fire on comps/traffic/labor/commodity) + adjacent **AZO, ORLY, BBY, ULTA** + contrast **DAL, AAL, LUV**. In-catalog companies' events are NEVER candidates (their text built the catalog — the company boundary IS the leak barrier; the time-split is empty on the frozen DB). fetch → chunk → EXP-2's ADOPTED reader, blind → candidate pool → h32 sample 120 per the LOCKED O4 quotas (≥40 reuse · ≥40 create · ≥20 skip · ≤20 free-hard; stratum shortfall → record + STOP, see WP-KEYS), **preferring the most-recent (Q1-2026) events first** — the catalog is fully populated there, so the over-merge temptation is maximal (fill from older events only if a stratum runs short) — and preferring the corpus's REAL trap language where the pool provides it (airline traffic/capacity/yield/per-ASM unit economics; retail comps/foot-traffic). Supply is abundant (9 companies × ~50–70 chunk-sources each ≫ 120; pre-run check f). Each candidate carries its own `event_time`; the retrieval PIT filter (`visible_from ≤ event_time`, quotes PIT-cut) governs what it sees. ~40–60 reader calls.
- **Create:** `harness/retrieval_index.py`, `harness/router_probe.js`, `harness/scorers/score_exp3.py`.
- **Retrieval (pinned):** embedding text (BOTH sides, symmetric — HCP §13.1.2-3 shape): `"{name} | {quote≤300 chars} | {industry}"`; catalog-side quote = the record's first evidence quote by (date, company) sort. Cosine top-K; **PIT filter `visible_from ≤ candidate.event_time`** where `visible_from` = record's earliest non-empty evidence date (PIPE-34; KPI-only records excluded fail-close). **Cluster-dedup:** group hits by `canonical_name`, keep max-score per group. **Exact slot:** an exact-`norm()` name match is forced into slot 1 flagged `EXACT` (kernel Stage-0). Card fields (kernel §3): `name · fact_type (from EXP-4B stamps) · companies_count · badge · base_metric_line (families_fixture) · same_as_variants · ≤2 evidence quotes PIT-cut to date ≤ event_time`. Badge = `"YOUNG"` uniformly (no establishment machinery pre-build — declared limitation §10-D3).
- **Arms:** R1 `haiku_k10full` · R2 `sonnet_k10full` · R3 `sonnet_k25full` · R4 `sonnet_k10stripped` (cards minus badges/quotes; keep name + fact_type + counts). Each = 150 calls, ONE candidate per call. Plus RB `sonnet_k10full_batched` — report-only replay grouping candidates per event (kernel Stage-1's ≤400/≤300k batch shape; ~30 calls; §10-D2).
- **Router prompt contract:** input = candidate `{proposed_name, quote, slice_tokens, per_x, event_time}` + the card view; instruction = kernel §3 verbatim: *"ATTACH only on an EXACT card whose evidence shows the same cause, scope, AND mechanism. ADOPT trivial reorders. CLAIM a differently-worded claim-eligible card only when the evidence supports same cause — a skeptic decides, and your reasoning is not forwarded to it. Never claim YOUNG (except your own company's per-X causes), never claim QUARANTINED. When unsure, keep separate."* + G2 arm definitions (PIPE-13: reuse=exact same cause+scope; admit=valid reusable cause per naming rules; skip=vague/rule-breaking/single-event-bound; reusable event CLASSES admitted even if seen once). Output:
```jsonc
{"candidate_id": "kt_0001", "arm": "ATTACH|ADOPT|CLAIM|CREATE|SKIP|UNSURE",
 "target": "<card name|null>", "mechanism_note": "<≤40 words>",
 "quotes": {"candidate": "<verbatim>", "card": "<verbatim|null>"}}
```
  The exact card view served per candidate is LOGGED to `views/` (mandatory — it is the target-visible attribution evidence).
- **Scoring logic:** `wrong_merge` = arm∈{ATTACH,ADOPT} onto a card that is a different cause per key (target ≠ gold_target → grader confirms "different cause?" on the chosen card vs candidate; grader-SAME on a non-gold card → still counted per key, filed as `wm_*` for Fable review incl. possible key-erratum note — score never retro-edited). `missed_reuse` = arm=CREATE while gold∈{ATTACH,ADOPT,CLAIM} AND gold_target ∈ served view / |gold reuse cases|. `retrieval_recall` = gold_target ∈ served view / |cases with gold_target| (pure code). `skip_acc` on gold-SKIP. `UNSURE` = never a wrong merge; counts as a miss of the gold arm; rate reported. Per-planted-family table. CLAIM correctness = arm=CLAIM where gold=CLAIM (proposal-level; pair truth is EXP-4's).
- **PASS check:** `score_exp3.py` gate per arm = `wrong_merge==0 && retrieval_recall>=0.95 && missed_reuse<=0.15`. Attribution: every wrong merge classified `target_visible: true|false` (visible → judgment/tier failure; not visible → display/retrieval failure — PIPE-37's grader distinction). One family failing across ALL arms → `ra_*` + owner rule question.
- **Parallel:** with EXP-4A (both post-freeze). **Blocks:** the router verdict memo (**O11** if triggered). **Stops whole run:** never.
- **Calls/cost:** 600 + 30 replay + ~60 candidate-gen readers + ~40 grading ≈ 730 · class L boundary (cap 900).
- **Decisions:** **O4** (quotas at lock) · **O7** (before WP-FC-RUN) · **O11** (owner, only on trigger) · Fable router-verdict memo either way.

---

### EXP-4 — Identity judge + family stamping

**Plan bars (verbatim):** **A)** chosen tier wrong-SAME = 0 on BOTH input shapes · false-refusal ≤ 10% on full evidence (anchor may refuse more, never wrong-SAME more). **B)** suffix path 100% (assert) · classifier ≥ 95% with ZERO wrong stamps on suffixed records · OD-2 zero unproven-metric stamps · S-A6 0 false alarms on clean fixtures AND 5/5 deceptive-suffix detection. Cap ~900 strong-tier calls (see §10-D5).

**A) SAME_AS pair judge**
- **Inputs:** `keys/K-pairs/K-pairs.v2.jsonl` (~250; locked after mining from the frozen catalog).
- **Create:** `harness/judge_probe.js` (modeled on `ab_pair_judge.js`; workflow kit untouched), `harness/scorers/score_exp4.py` (shared with B).
- **Arms:** J1 `sonnet_anchor` (250) · J2 `sonnet_full` (250) · J3 `opus_full` (planted subset, 110) · J4 `opus_anchor` (250) — **trigger ✅ DECIDED (owner 2026-07-08, closes O9): J4 fires ONLY if Sonnet shows ANY wrong-SAME on either input shape; zero wrong-SAME → J4 is SKIPPED and the +250 strong calls are not spent.** The firing (or skip) is recorded in the run manifest.
- **Input shapes (pinned):** *anchor-shape* — side A = `{name, quotes(≤2), slice_tokens, per_x, industry}`, side B = frozen-anchor form `{name, birth_quotes(=2 earliest by date, deterministic), industry}` (kernel §6.3's shape; for key pairs "earliest" = first 2 quotes listed). *full-evidence* — up to 20 quotes/side via the deterministic draw (sort by (company, date); round-robin least-represented company — HCP §12.8 discipline).
- **Judge prompt contract (kernel §6.1 VERBATIM — code-assembled input, no producer advocacy, default `survives=false`, each check quoting BOTH sides):** (1) same OBJECT — co-extensive, never hyponym: either side a narrower species of the other → REFUSE (breadth only from the SAME name recurring); (2) same SCOPE — business population AND referent ownership class {own-entity-internal | external-market | counterparty} (a firm-realized quantity is never the external market variable driving it); (3) same MECHANISM — same measured quantity at the same causal position; upstream/downstream/correlated on one chain → REFUSE; the financial transmission channel must match; (4) NO RIVAL — evaluated ONLY when the pair record carries `rival ≠ null`: unless the quote uniquely discriminates ONE target → REFUSE (else auto-pass); (5) head anchor MONO-mechanism — an anchor spanning mechanisms → REFUSE + flag. Output:
```jsonc
{"pair_id": "kp_0001", "survives": false,
 "checks": {"object": {"pass": false, "quote_a": "...", "quote_b": "..."}, "scope": {...},
            "mechanism": {...}, "no_rival": {"pass": true, "quote_a": null, "quote_b": null},
            "mono_anchor": {...}},
 "reason": "<≤60 words>"}
```
  Scorer validates `survives == AND(all checks)`; mismatch = invalid row.
- **Scoring/PASS:** per arm: `wrong_same` (gold-DIFFERENT ∧ survives=true; **0 required**) · `false_refusal` (gold-SAME ∧ ¬survives; ≤0.10 on J2 only — J1's higher refusal is measured, reported, not failed) · per-check firing attribution · anchor-vs-full delta table. Gate: `wrong_same(J1)==0 && wrong_same(J2)==0 && false_refusal(J2)<=0.10` (Sonnet as chosen tier), else the Opus arms decide per the plan's failure ladder.

**B) fact_type / BASE_METRIC stamping** (doubles as F-C's finalization dry-run — outputs freeze into `catalog_fc/`)
- **Inputs:** `keys/K-stamp/` (locked) + the F-C catalog records.
- **Create:** `harness/stamp_fixture.py` (code paths + memo writing) + `harness/stamp_classify.js` (LLM calls).
- **Pipeline (per PIPE-24/25 + OD-1 + OD-2, in order):**
  1. CODE: terminal `_guidance`/`_surprise` suffix (TERMINAL token only; stacked = invalid) ⇒ fact_type deterministically — assert 100%.
  2. OD-1 gate on every terminal-suffix admission — strip exactly one suffix; ask **verbatim (66 §0.R OD-1):** *"Is the residue a standing metric or condition whose level, state, or severity can be re-read over time, and is this source forecasting/guiding/targeting it (`_guidance`) or comparing it to expectation (`_surprise`)?"* — asked TWICE via two independent `strong` calls; both YES → admit; any NO/UNCLEAR/disagreement → not admitted. Memo rows → `terminal_admissions_fixture.json` {driver_name, suffix, stripped_base, evidence_ref, check_1, check_2}.
  3. Classifier (C1) on non-suffixed records: prompt = `07_DriverUpdate.md` DU-05's four definitions + DU-06's decider, BOTH VERBATIM, NOTHING added (DU-07's overfit lesson). Arms: `sonnet_cls`(100) and `opus_cls`(100). Output `{"name": "...", "fact_type": "...", "decider": "persistence|suffix_framing|outlook_verb|dual_framing|bare_root_default", "evidence_used": ["..."]}`.
  4. OD-2: C1=action_event → stamp (no second check). C1=guidance/surprise on a bare name → NAMING defect (no stamp; F3-class exhibit). C1=metric → C2 metric-proof on full evidence, **verbatim (66 §0.R OD-2):** *"Using only the evidence: is this name itself a standing level, value, condition, or severity that can be read again over time? Answer NO if the name is mainly a one-time action, decision, event, or plan — even if a related amount/rate/balance could be measured under a more specific metric name. Quote the exact evidence phrase."* YES + verbatim quoted phrase → metric; else action_event + `metric_proof_defaulted=true` (counted). Memo fields per OD-2: {c1_verdict, c1_evidence_ref, c2_required, c2_result, c2_extract, final_fact_type, metric_proof_defaulted, decision_reason} → `fact_type_decisions_fixture.json`.
  5. BASE_METRIC: PIPE-25 lookup order over F-C (record → variant string → latent), strip ONCE; latents obey OD-1's rules (valid standalone name, non-suffixed, collision-free) → `families_fixture.json {base_metric:[{from,to}], latent:[...]}`.
  6. S-A6: judge-tier re-derives fact_type/base from EVIDENCE ONLY (suffix masked from the prompt) for all 30 suffixed records; disagreement = flag.
- **Scoring/PASS:** `cls_acc = matches/100` per model (gate on the chosen tier ≥0.95) · `wrong_suffixed_stamps == 0` (over the 30) · `od1_gate`: the 5 deceptive plants NOT admitted (0 admissions) AND the true suffixed families admitted · `od2_unproven_metric_stamps == 0` (pipeline invariant — verified over outputs) · `sa6_false_alarms == 0` (25 clean) AND `sa6_detections == 5/5` (plants).
- **Parallel:** B runs immediately after WP-FC-RUN (it produces the freeze inputs); A runs post-freeze parallel with EXP-3. **Blocks:** B blocks F-C FREEZE → EXP-3; A blocks the judge verdict/tier memo. **Stops whole run:** never.
- **Calls/cost:** A: 250+250+110 (+250 conditional) = 610–860 · B: 200 cls + 60 OD-1 + ~40 C2 + 30 S-A6 ≈ 330 · total ≈ 940 (§10-D5) · class L (all strong-tier).
- **Decisions:** **O9** (conditional arm) · Fable: judge-tier + anchor-policy verdicts; S-A6 misses → owner note (kernel L1 lane power).

---

### EXP-5 — DriverUpdate item-contract extraction probe

**Plan bars (verbatim):** recall ≥ **95%** single or ≥ **98%** 2-run union on market-moving facts · wrong-lane = **0** after routing rules · value/shape accuracy ≥ **98%** · driver_state ≥ **95%** · would-park ≤ **10%**. Cap ~150 extraction calls + ~400 grading calls.

**Terminology (owner 2026-07-08, closes O3):** the plan's phrase "market-moving facts" = `du_worthy` facts — the locked DU-03 "DriverUpdate-worthy" gate (§3 K-fields), significance-agnostic. It does NOT mean proven stock-movers; stock-move attribution is `EXPLAINED_BY` (DU-21…24) and never enters this gate or these bars.

- **Inputs:** `fixtures/events/` (36 packets); `keys/K-fields/` (locked); PIT slice menus via `harness/slice_menu_probe.py`.
- **Leakage rule (owner 2026-07-08):** EXP-5/EXP-6 are **CATALOG-INDEPENDENT** — the 36 events may freely overlap the mini-catalog companies; no hold-out applies here (the EXP-3 candidate hold-outs are a SEPARATE selection — never reuse the 36's restaurant events as EXP-3 candidates). The producer sees ONLY event text + the PIT slice menu + the item-contract instructions: no gold labels, no realized returns, no > event_time context; K-fields gold is text-only-labeled (§3 WP-KEYS).
- **Slice menu (read-only FS-14 approximation; pre-build catalog-used half = empty, stated honestly in the packet):**
```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$ticker})
WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] AND r.created <= $event_time
MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:FACT_MEMBER]->(m:Member)
MATCH (f)-[:FACT_DIMENSION]->(d:Dimension)
RETURN DISTINCT d.qname AS axis, m.qname AS member_qname, m.label AS member_label
```
  classified by the frozen axis tables (`XBRL_SliceAxis_Catalog.md` — SLICE_AXES kinds; NON_SLICE dropped from the menu); labels normalized per `03` FS-18's recipe VERBATIM (if FS-18's text under-determines a character class → `ra_*` + **O14**).
- **Create:** `harness/producer_probe.js`, `harness/scorers/{score_exp5.py, fact16_checks.py}` (+ `grade_batch.js` shared).
- **Arms:** P1 `sonnet_run1` · P2 `sonnet_run2` · P3 `haiku_run1` · P4 `haiku_run2` (all 36 events) · P5 `opus_ref` (12-event h32 subsample). Runs within a tier are independent calls (no shared context).
- **Producer prompt contract:** packet = event `text_parts` + `{ticker, fye_month}` + the slice menu + the ITEM CONTRACT instructions assembled VERBATIM from: `12` FACT-17b (field list) · `09 §3` value shapes (point fills BOTH bands; low-only=floor, high-only=ceiling; shape hints REQUIRED with numbers) + OD-12 signed-value rules · `09 §7` producer contract (OD-11 basis routing; OD-9 span copying into `measurement_raw_spans`; per-slot unit hints; money `money_mode_hint`; non-empty `unit_raw` on numeric facts) · `12 §10.5` ISS-16 routing (expectation comparison ⇒ (reported actual) metric + surprise / (forward guide-vs-Street) guidance + surprise, per OD-21; temporal ⇒ metric change; forward guide-vs-own-prior ⇒ guidance movement) + OD-13 favorability (producer meaning judgment; doubt → `unknown`) + OD-21 (a surprise item carries the transient `surprise_basis_hint ∈ {actual, guidance}`; a forward guide-vs-Street ⇒ guidance fact + a `guidance_vs_consensus` surprise; code composes the stored `surprise=` = basis × comparison_baseline; producer NEVER emits `surprise=`) · OD-14 (bare guidance movement → `driver_state=unknown`, store stated movements only) · `12` FACT-26f / 03 FS-15 slice-kind ladder (verbatim — OD-17/T1-05, owner 2026-07-11). Output = `{"source_id","source_type","ticker","fye_month","items":[<FACT-17b item>]}` with the item fields exactly:
```
driver_name · driver_state · quote · level_low · level_high · change_value · comparison_low ·
comparison_high · comparison_baseline · value_text · conditions · company_confirmed ·
level_unit_raw · change_unit_raw · level_unit_kind_hint · level_money_mode_hint ·
change_unit_kind_hint · change_money_mode_hint · level_shape_hint · comparison_shape_hint · surprise_basis_hint ·
measurement_raw_spans[] · period_start_date · period_end_date · fiscal_year · fiscal_quarter ·
half · month · long_range_start_year · long_range_end_year · sentinel_class · time_type ·
period_scope · slice[]
```
- **Scoring logic:** (1) MATCH produced items ↔ gold facts: same event; code first (quote ≥20-char overlap with gold quote OR value equality post-canonicalization via `unit_resolver` import); ties/unclear → grader confirms same-fact. (2) `recall(arm)` per run and per same-tier 2-run union (item sets unioned before matching); denominator = gold `du_worthy==true` (the DU-03 gate, §3 K-fields; `du_worthy:false` exemplar rows never enter any denominator). (3) `fact16_checks.py` = the deterministic FACT-16 subset — rules 3 (lane matrix incl. value_text/conditions/company_confirmed guidance-only + metric expectation-baseline FORBID), 5 (shape-hint coherence, point-as-low-only trap), 8 (baseline enum), 9 (unit-required-when), 14 (value_text lint), 15 (start==end illegal), 17 (period_scope enum), 18 (OD-21: **compose `surprise=` (basis×baseline) BEFORE validation**; `surprise=` REQ-on-surprise / FORBID-elsewhere; basis hint + `comparison_baseline` both REQUIRED; every GROUNDED surprise requires its home sibling [numberless allowed via unknown+quote; ungrounded parked; missing = fail-closed], numeric equality only when numbers exist; impossible-tense) → `would_park` rate + reason codes. Authority for these checks = `12` FACT-16 + the `09 §4` matrix — NEVER `99 §7.2`, whose validator mirror is known-incomplete (ISS-50). (4) Field accuracy on matched pairs: code-comparable directly (values post-scaling, shapes, signs per OD-12, enums, measurement token SETS after OD-9 code normalization: lowercase → non-alphanumeric runs → `_` → trim → collapse; maximal contiguous spans = one token); meaning fields via grader (driver_state, lane routing incl. the ISS-16 surprise-twin presence, OD-13 favorability, OD-11 basis, slice pick vs menu). (5) `wrong_lane` = matched fact on the wrong lane OR a missing gold surprise twin where `expectation_comparison_present=true` OR (OD-21) a wrong/missing `surprise=` label, an outlook-vs-earnings over-merge on one driver+period, or a restated-guide mis-tagged as `actual_vs_*`. (6) `presence_disagreement(tier)` = captured-by-exactly-one-run / captured-by-either. (7) Per-OD-rule error table (OD-9/11/12/13/14/21, ISS-16, shapes, slices). (EXP-5 scores PRODUCER output only — the real fusion + read-collapse verification of the OD-21 merge/collapse fixtures lives in the Track-B acceptance gates §12.3, BLOCKED until the Track-B build §17 builds `driver_write_cli` fusion + `driver_read` collapse; NOT part-2.)
- **PASS check:** `score_exp5.py` gate per tier = `(recall_single>=0.95 || recall_union>=0.98) && wrong_lane==0 && value_shape_acc>=0.98 && state_acc>=0.95 && would_park<=0.10`.
- **Parallel:** needs only EXP-0 + K-fields + WP-FA; runs parallel with Phase-2 (EXP-3/4). **Blocks:** EXP-6; part-2 packet design. **Stops whole run:** never.
- **Calls/cost:** 36×4 + 12 = 156 producer calls (large prompts) + ~50–60 batched grading calls · class M.
- **Decisions:** O3 ✅ decided (owner 2026-07-08 — the DU-03 gate, §3 K-fields); Fable: per-field failure attributions; §12.5 threshold basis handed to owner.

---

### EXP-6 — Text↔XBRL twin identity convergence

**Plan bars (verbatim):** id-equality ≥ **99%** on true twins · value gate: zero suppressed non-twins in a hand-checked sample · every divergence classified {period, slice, measurement, value} with a named fix. Cap ~0 LLM + small spot-grading.

- **Inputs:** `exp1/.../materialized.jsonl` · EXP-5 winning-tier responses (union of its 2 runs; their gold was TEXT-only labeled per the K-fields independence guard — the text side never derives from XBRL) · `harness/id_recipe.py`.
- **`id_recipe.py` (pinned):** fact_scope serialization per FACT-11/T3.2 (`period=<gp_id>|slice=<kind:value;…>|measurement=<tok,…>`, absent slots omitted; slices code-sorted; measurement tokens code-normalized per OD-9 and sorted); period ids: exact-date branch first (`gp_<start>_<end>`), else READ-ONLY import of `guidance_ids.build_guidance_period_id` + `fiscal_math` (FACT-18's "what moves"), with the driver-wrapper deltas (period_scope `long_range`→`exact_range`; no silent gp_UNDEF). If Track B's real `driver_ids.py`/`driver_period_resolver.py` exist by run time → import THEM + parity-assert against the local subset (§2.2 rule).
- **Twin recipe (pinned):** candidates = pairs (text metric item i from a 10-Q/10-K event E, materialized row m of the SAME report E) with: same registrant; value match within half-ULP of the text value's least significant digit (both post-canonical scaling); period windows equal after resolution (or the text label resolves to m's window). Fable confirms same-quantity on the full candidate list (≤150) → `true_twins`. Target ≥100 twins, ≥10 from the 52/53-week filer; shortfall → widen to more FA 10-Q/10-K events (never to cross-event pairs — different events = different ids by design).
- **Scoring logic:** per twin, component equality: `period_u_id` · slice set (post FS-18 normalization on the text side vs member→slice on the XBRL side) · measurement fold (text token set ⊆ {∅, gaap, reported, as_reported} ∪ concept's Basic/Diluted token — the P3 fold — vs XBRL ∅) · value gate (P5c half-ULP). `id_equal` = ALL components equal (event + driver equal by twin construction; the driver-name component's cross-lane equality is the concept-linker's separately-validated job — plan §3.1). Divergences classified with the named fix per the plan's failure map.
- **PASS check:** `score_exp6.py` gate = `id_equal_rate>=0.99 && suppressed_nontwin_count==0` (the latter over a 30-twin h32 hand-check sample adjudicated by Fable) `&& every divergence classified`.
- **Parallel:** last (needs EXP-1 + EXP-5). **Blocks:** the XBRL ratification memo. **Stops whole run:** never.
- **Calls/cost:** ~0 LLM + ≤30 spot-grading · class S.
- **Decisions:** Fable: divergence-fix list → pin amendments (with **O12**); >5% systematic failure → P5 suppression design re-opens pre-ratification (plan).

---

## §5 Dependency & scheduling table

| Package | Needs (gate artifacts) | Unblocks | Parallel lane |
|---|---|---|---|
| WP-0 | — | all | — |
| EXP-1 census | WP-0 | — | Lane X (immediately) |
| WP-FA | WP-0 | keys drafting · EXP-1 dry-run · EXP-5 | Lane A |
| EXP-1 dry-run | WP-FA (`FA_selection`) | EXP-6 · XBRL ratification | Lane X |
| K-pairs.v1 lock | protocol + Fable | EXP-0 | Lane A |
| **EXP-0** | K-pairs.v1.lock | ALL graded scoring | Lane A |
| WP-FC-EDITS | WP-0 | EXP-2 · WP-FC-RUN | Lane B |
| K-reader lock | frozen chunks + Fable | EXP-2 | Lane B |
| **EXP-2** | EXP-0 PASS · WP-FC-EDITS · K-reader.lock | WP-FC-RUN · EXP-3 candidates | Lane B |
| WP-FC-RUN | EXP-2 decision (O7/O8 ✅ decided — roster + hold-outs pinned) | K-pairs.v2 mining · EXP-4B | Lane B |
| **EXP-4B** | WP-FC-RUN · K-stamp.lock · EXP-0 PASS | F-C FREEZE | Lane B |
| F-C FREEZE | EXP-4B outputs | EXP-3 · K-pairs.v2 · retrieval index | Lane B |
| K-route lock | FREEZE + candidate pool + Fable | EXP-3 | Lane B |
| **EXP-3** | FREEZE · K-route.lock · EXP-0 PASS | router memo (O11) | Lane B1 |
| K-pairs.v2 lock | FREEZE (mining) + Fable | EXP-4A | Lane B2 |
| **EXP-4A** | K-pairs.v2.lock · EXP-0 PASS | judge memo | Lane B2 |
| K-fields lock | WP-FA events (O2 SIGNED — review checks recorded) + Fable (O3 ✅) | EXP-5 | Lane C |
| **EXP-5** | EXP-0 PASS · K-fields.lock | EXP-6 · packet basis | Lane C |
| **EXP-6** | EXP-1 PASS · EXP-5 scored | ratification memo | final |

Max parallelism: Lanes X, A, B, C run concurrently; B1 ∥ B2 ∥ C after the freeze. The critical path is A→B (EXP-0 → EXP-2 → FC-RUN → 4B → freeze → EXP-3/4A).

---

## §6 Stop conditions — summary

Global (§1.8). Per-package FAILs never stop the program (they produce attribution + decisions), with two exceptions: EXP-0 total failure (global stop of graded work) and the O8 F-C budget checkpoint (pauses Lane B for a scope decision). EXP-1 FAIL blocks only the XBRL ratification path (Lane X output), not Lanes A/B/C.

---

## §7 Decision-point register

| When | Who | Decision |
|---|---|---|
| WP-FA | Fable | O1 ✅ decided · O2 checks ✅ RECORDED (owner-accepted 2026-07-08) — remaining: Fable signs `FA_selection.json` at materialization; OD-11 contingency live during K-fields drafting |
| Key locks | Fable | every key adjudication + lock (O3 ✅ DU-03 gate · O4 ✅ quotas locked — a stratum shortfall STOPS for review) |
| Before WP-FC-RUN | Owner/Fable | O7/O8 ✅ decided 2026-07-08 (8-ticker roster · {BLMN, SHAK} hold-outs · TXRH→QSR→SBUX trim rule); remaining = run pre-run checks (d)–(g) + the chunk pre-estimate |
| EXP-0 scoring | Fable | O10 grader-tier ratification + blindness discounts |
| EXP-2 scoring | Fable | reader/chunking/runs adoption (O5 ✅ rerun-only-with-named-fix · O6 ✅ 8k arm kept + optional neighbor-rescue) |
| Cheap-arm FAIL / inconclusive (EXP-2/3/5) | Fable | O16 ✅ policy decided (owner 2026-07-09) — authorize (or decline) the single `cheap_fallback` DeepSeek-via-OpenRouter arm; memo to owner either way |
| EXP-4A | mechanical | O9 ✅ decided: J4 `opus_anchor` fires on any Sonnet wrong-SAME, else skipped — no separate approval step |
| EXP-3 verdict | Owner | O11 ATTACH synchronous strong-confirm (only if triggered; memo either way) |
| EXP-1/6 done | Owner | O12 XBRL pin-amendment bundle → ratification (with XBRL §11) |
| Program end | Fable→Owner | tier-membership table + `manifest.models` pins · kernel §15 memo · plan §10 review list |

---

## §8 OPEN FOR OWNER/FABLE register (consolidated — implementers STOP on these)

| # | Item | Default recommendation (not a decision) |
|---|---|---|
| O1 | ✅ **DECIDED (owner 2026-07-08):** the **Phase-1 corpus** = Restaurants {CAKE, DRI, MCD, YUM, CMG} + SpecialtyRetail {AZO, ORLY, BBY, ULTA} + Airlines {DAL, AAL, LUV}. Phase-1 pass ≠ whole-market readiness — a later, wider sector-wave validation gates broad production; do NOT expand in-program | closed — §3 WP-FA step 1 |
| O2 | **✅ READY FOR FABLE SIGN-OFF (owner 2026-07-08):** 36 events final — 32 filing/transcript ids + 4 news (AAL `bzNews_50877032` · MCD `bzNews_42014391` E.coli occurred/at-risk · BBY `bzNews_51962983` CEO · CMG `bzNews_49256211` $1.8B buyback). All checks RECORDED: twins/OD-12/guidance/numberless/action_event PASS · **OD-11 BORDERLINE-accepted** with the pinned ULTA→LUV 10-Q contingency (fires only if K-fields drafting finds <5 sequential facts). **REMAINING:** Fable's signature at WP-FA materialization + the live contingency | sign-off unblocked; contingency during K-fields drafting |
| O3 | ✅ **DECIDED (owner 2026-07-08):** the K-fields gate = the locked **DU-03** write gate ("DriverUpdate-worthy fact") — real, source-stated, non-boilerplate, one of the 4 lanes; NO recurrence/materiality/significance/price-move threshold (DU-01 · T11.1 · 95 #4/#5); bare mentions + generic risk boilerplate excluded; attribution stays `EXPLAINED_BY`; field renamed `du_worthy` | closed — full wording at §3 K-fields |
| O4 | ✅ **DECIDED (owner 2026-07-08):** K-route quotas LOCKED — ≥40 reuse-gold · ≥40 create-gold · ≥20 skip-gold · remaining ≤20 free/best-available hard real cases. A required stratum that cannot be filled from real data → RECORD the shortfall + **STOP for Fable/owner review**; never silently re-quota | closed — WP-KEYS K-route |
| O5 | ✅ **DECIDED (owner 2026-07-08):** NO automatic EXP-2 rerun on shared misses. Exhibits ALWAYS; a rerun only after Fable names a concrete fix (rule wording · prompt wording · scorer/key bug · chunk boundary · missing source context); **rerun without a named fix = FORBIDDEN** | closed — EXP-2 PASS check |
| O6 | ✅ **DECIDED (owner 2026-07-08):** the 8,000-char smaller-chunk arm KEPT vs the 40k baseline; NO one-paragraph switch. Optional later experiment noted: "8k + neighbor rescue" (rerun flagged boundary-incomplete items with adjacent-chunk context; adopt only if recall gains without junk) — an option, not production law | closed — EXP-2 arms |
| O7 | ✅ **DECIDED (owner 2026-07-08):** same-industry hold-outs = **{BLMN, SHAK}** (never in the catalog; the PRIMARY same-industry candidate source) + retail {AZO, ORLY, BBY, ULTA} and airlines {DAL, AAL, LUV} stay out-of-catalog candidate groups. Split axis = **company + per-event PIT** — the time-split is empty at the verified frozen-DB boundary T0 = 2026-04-28 (§10 D7) | closed — §3 WP-FA roster · EXP-3 recipe |
| O8 | ✅ **DECIDED (owner 2026-07-08):** F-C catalog = **8 Restaurants {CAKE, DRI, MCD, YUM, CMG, SBUX, QSR, TXRH}**. 600-chunk checkpoint KEPT — if the fresh chunk count exceeds it, trim the density adds in reverse priority **TXRH → QSR → SBUX** (floor = the 5 corpus restaurants). Pre-estimate ≈ 478 chunk-sources (under cap); the fresh manifest is definitive | closed — §3 WP-FC-RUN |
| O9 | ✅ **DECIDED (owner 2026-07-08):** J4 `opus_anchor` fires MECHANICALLY iff Sonnet shows any wrong-SAME in EXP-4 (either input shape); zero wrong-SAME → skipped, the +250 strong calls are not spent | closed — EXP-4 arms |
| O10 | Grader-tier ratification post-EXP-0 | per gate result |
| O11 | ATTACH strong-confirm design change | only if EXP-3 triggers; owner memo either way |
| O12 | XBRL pin-amendment bundle text | Fable drafts from EXP-1/6 registers; owner ratifies |
| O13 | Axis↔member pairing binding (if neither candidate path deterministic) | fail-closed skip + count meanwhile |
| O14 | FS-18 slice-label normalizer exact recipe (if 03 under-determines) | raise `ra_*`; Fable pins |
| O15 | `Concept.balance` absent from graph | menu ships without the column; note in census |
| O16 | ✅ **DECIDED (owner 2026-07-09):** optional cheap-tier fallback arm — DeepSeek V4 Flash via OpenRouter (`cheap_fallback`, §1.3) — fires ONLY on a Haiku cheap-arm bar FAIL in EXP-2/3/5 or a Fable-marked inconclusive cheap result; Fable authorizes; same key/sample/prompts/bars; `OPENROUTER_API_KEY` required (setup deferred to trigger time); Haiku stays default; `none → Sonnet` terminal rule and all bars unchanged; passing evidence informs production strategy only (no in-program engine port) | closed — §1.3 O16 rule |

---

## §9 Budget ledger — estimates

| Package | Est. calls | Strong-tier | Class | Cap (abort at 1.5×) |
|---|---|---|---|---|
| WP-KEYS drafting | ~120 | ~120 | M | 200 |
| EXP-0 | ~500 | ~500 | M | 500 |
| EXP-1 | 0 | 0 | S | — |
| EXP-2 (+grading) | ~480 | ~150 | M | 350 readers + grading |
| WP-FC-RUN | ~480 readers (8-ticker roster; ≈478 chunk-sources pre-est.) + ~90 judges/repair | ~90 | M/L | >600-chunk checkpoint + TXRH→QSR→SBUX trim |
| EXP-3 (+candidates+grading) | ~730 | ~500 | L | 900 |
| EXP-4 A+B | ~940 (+250 conditional) | ~940 | L | 900 (§10-D5) |
| EXP-5 (+grading) | ~215 | ~170 | M | 550 |
| EXP-6 | ≤30 | ≤30 | S | 50 |
| O16 fallback arms (conditional) | 0 by default; on trigger ≈ the failed arm's volume (EXP-2 ≈40 · EXP-3 150 · EXP-5 72) | 0 | S | 1.5× the failed arm's calls (metered $, OpenRouter) |
| **Totals** | **≈ 3,600–4,300 (+ conditionals + F-C readers)** | **≈ 1,900–2,100** | | global abort 6,000 |

See §10-D4: the plan's "~4,000 total / ~1,500 strong" were approximations; refined arithmetic lands ≈4,300–4,900 all-in with F-C at full industry scale. No bar changes; the plan's own 1.5× convention governs (per-package aborts; global 6,000).

---

## §10 Operationalizations & deviations found (declared, none changes a plan bar)

- **D1 — falsifier-(iii) dry-run:** under EXP-1's 1:1 fixture resolutions, the literal signal (two drivers sharing one concept) is degenerate. Operationalized as `collision_census`: (a) the P4g invariant check (0 post-dedup multi-rows) + (b) the informational value-confusability base rate. Intent (feed detector calibration) preserved.
- **D2 — router batching:** the kernel batches Stage-1 per event; the probe's primary arms are per-candidate calls (scoring isolation), plus one report-only batched replay (RB, ~30 calls) to measure the batch-vs-single delta. Primary bars score the per-candidate arms only.
- **D3 — badge ablation limitation:** all F-C cards carry badge `YOUNG` (no establishment machinery exists pre-build) → the badge's routing effect has no variance pre-build; R4 still ablates quotes/BASE_METRIC/fact_type-line. Recorded as a known limitation, not a bar.
- **D4 — budget arithmetic:** the plan's "~4,000 / ~1,500 strong" under-counted F-C readers and EXP-3's Sonnet arms; refined totals in §9. Caps interpreted via the plan's own 1.5× abort convention; no experiment shrunk.
- **D5 — EXP-4 cap:** summed pre-registered arms ≈940 vs the plan's "~900" — within rounding; the conditional J4 arm fires mechanically on any Sonnet wrong-SAME (O9 ✅ owner 2026-07-08). Abort stays at 1.5× (1,350).
- **D6 — mandatory-fixture sourcing vs the plan's F-A wording (owner corpus decision, 2026-07-08):** the plan places the multi-registrant filing and the null-`periodOfReport` report INSIDE F-A; verified data says the Phase-1 corpus cannot supply them — no multi-registrant 10-K/10-Q exists among the 12 (live-DB check), and the only null-pOR reports graph-wide are `xbrl_status=FAILED`. Operationalized: the 52/53-week filer stays IN-corpus (5 candidates); multi-registrant + null-pOR become **EXP-1-only dry-run fixtures sourced corpus-wide**, with null-pOR falling back to a **synthetic harness fixture** if pre-run check (b) finds no COMPLETED one. Intent (exercise the P4f entity-scoping and P4h null-pOR code paths) preserved; keys, events, and bars unaffected.
- **D7 — company-split replaces the plan's "candidates strictly later than catalog evidence" (owner 2026-07-08):** verified frozen-DB boundary — max `Report.created` / `Transcript.conference_datetime` / `News.created` all = **2026-04-28** — makes the plan's time-split EMPTY (0 post-T0 events across all 34 companies; the latest activity is the Q1-2026 earnings wave). Operationalized per owner decision: the catalog/candidate boundary is drawn **BY COMPANY** (the 8-ticker build roster vs the 9 always-hidden candidate companies), and **per-event PIT** (`visible_from ≤ event_time`; quotes PIT-cut; strict `<` on history reads; ET day) controls what each candidate sees — nothing a candidate's router view shows postdates its event. If the DB is refreshed past 2026-04-28, the time-split becomes available again as a supplement. Honest limits while the DB stays frozen (recorded): post-T0 / live-arrival behavior is not provable pre-refresh, and all catalog cards carry `YOUNG` badges (D3). Bars unchanged.

---

*Assembled 2026-07-08 by Fable from the locked `FableExperimentPlan.md` (sha `5196…7472`) plus targeted re-reads of: kernel §§2/3/6/8/9/11/12 · XBRL design §§5/9/11/12 · `10` PIPE-13/16…37/§10/§12 · `12` FACT-9…35/§10/§12/§17 · `09` §3/§6/§7 · `66 §0.R` OD-1/OD-2 (verbatim gate wording) · `WorkflowContextPack` (paths + traps, re-verified on disk) · the validated Neo4j schema references. On any conflict, the cited topic doc wins; this file adds execution mechanics only.*
