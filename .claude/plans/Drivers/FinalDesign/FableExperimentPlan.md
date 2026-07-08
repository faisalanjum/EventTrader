# FableExperimentPlan — pre-implementation proof / falsification program for Driver + DriverUpdate creation

> **STATUS (2026-07-08): EXPERIMENT PLAN v1.0 — designed, NOT run.** Written by Fable from a same-day first-hand read of `00_Coverage` · `FableContextPack` · `14_BuildReadiness` · `FableAdmissionKernelDesign v3.4` · `XBRLIntegrationDesign` · `WorkflowContextPack` · `10` · `66 §0` · `90` · `09` · `12`.
> **What this is:** the smallest production-like experiment set that can prove or falsify the current Driver/DriverUpdate creation design BEFORE the identity-bearing code is built. It adds **no design content** and amends no doc. On any conflict, topic docs + `95` win. `FableAdmissionKernelDesign.md` and `XBRLIntegrationDesign.md` are treated here as **candidates under test**, not ratified rules.
> **What this is NOT:** not a redesign; not a duplicate of the build-gated acceptance gates (gauntlet · S3 · fitness gate + OD-6 · X-XL0–3 final · XC-16 + full-universe) — those stay exactly where the docs put them (§3.2 below); nothing in this plan waives them.

---

## §0 One-sentence strategy + summary

**Strategy:** validate the measuring instruments first (graders + sha-locked adjudicated keys), then falsify the design's four load-bearing bets — cheap blind extraction, safe cheap routing over a propose-first display, zero-wrong-merge strong judging, and deterministic text↔XBRL identity convergence — on ONE shared, PIT-disciplined fixture corpus with pre-registered bars, before any identity-bearing code ships.

Plain summary:
- The design's experiment program already exists on paper (kernel §12: S1–S4/X0–X9/X-G/X-IM/X-C · XBRL §9: X-XL0–4 · `10` PIPE-32/33/37 · `12` §12). Most of it needs BUILT machinery. This plan extracts the **pre-code subset**, adds the one missing piece — **grader validation runs FIRST**, because every later pass/fail is scored by graders — and shares one fixture corpus + key set across everything.
- Seven experiments (EXP-0…EXP-6), four phases, ≤ ~4,000 model calls total (strong tier ≤ ~1,500), zero new standing machinery (3 throwaway harness pieces; everything else reuses `workflows/`, the `ab_*` kit, and read-only Neo4j).
- Every experiment is built to **separate failure causes**: model weakness vs missing context vs unclear rules vs bad chunking vs reuse-display defects vs too few runs vs wrong cheap/strong placement (§6 matrix).
- The owner's model-tiering default (Haiku blind producer · Sonnet 5 strong judge; kernel §11.0) is treated as a **hypothesis**: EXP-0/2/3/4/5 form the grid that proves or falsifies each tier placement (§7). The locked *rule* — cheap tier never final-confirms identity — is not under test; only tier membership is.

---

## §1 Object under test → coverage map

| Risk area (per the task) | What tests it here | What tests it later (build-gated) |
|---|---|---|
| Driver identity / admission (kernel v3.4) | EXP-0 (graders) · EXP-3 (router + G1 display) · EXP-4A (LINK/SAME_AS judge, anchor shape) | gauntlet X-G · S3 shadow · X-IM · fitness gate |
| Catalog creation (Track A) | F-C mini-catalog build (engine + PIPE-16…21 overrides, hard checks) · EXP-2 (blind readers) | full seed build · reader A/B re-run at scale · PIPE-36/37 |
| DriverUpdate extraction correctness | EXP-5 (24-field item contract, dual-producer) | `12` §12.5 full dual-producer probe with real writer |
| DriverUpdate write/read correctness | deterministic → NOT an experiment: owned by `12` §12/§17 TDD + golden tests. Pre-code data checks only: EXP-1 (comparator-hit census for P15) · EXP-6 (twin id convergence) | `12` §12.1/.3/.6 gates · X-XL0–3 on the real writer |
| SAME_AS / BASE_METRIC / fact_type / code | EXP-4A (pairs incl. cross-flavor) · EXP-4B (stamping, OD-1/OD-2, S-A6) | finalize + `--final` F1–F5 · repair at every level |
| XBRL lane (lock candidate) | EXP-1 (census + determinism dry-run + PIT menu proof) · EXP-6 (twins) | X-XL0–3 on `xbrl_link_writer` · falsifier (iii) live |
| Rollout blockers | §3.2 restated + §11 verdict | unchanged: the docs' own gates |

---

## §2 Standing rules (bind every EXP — no exceptions)

1. **Pre-register before any arm runs:** N, arms, metrics, bars — recorded in this file's per-EXP blocks; keys **sha-locked** before the first arm call; **graded once**; a failed arm re-runs ONLY after a named fix and on a **fresh key sample** (PIPE-33/37 + OD-6 discipline — never retune-to-pass).
2. **Judged, never string-matched** scoring against an adjudicated key (PIPE-32: quote-match measured ~99% while judged precision was ~29% — the historical false signal).
3. **Zero tolerance in the merge direction** everywhere (the one law: over-merge permanent, over-split cheap).
4. **PIT:** name-creation corpora may use full history (PIPE-34 exemption); every reuse view / routing probe filters `visible_from ≤ event date`; no realized returns or future facts near any producer (FS-14 · DU-23).
5. **Billing:** in-session workflow `agent()` calls only, step-0 billing guard everywhere; embeddings are the ONE metered lane (suggest-never-decide, `min_score=0.60`); no `claude -p`/SDK (95 #22, `10` §11).
6. **Provenance:** exact pinned model IDs per run in a run manifest (the alias trap, PIPE-32) + git commit + prompt sha.
7. **Rule-ambiguity exhibits:** any case where key adjudicators split, or the rule text under-determines the answer, is logged as `rule_ambiguity{doc, rule}`. Each exhibit becomes a one-line doc-amendment proposal **regardless of the experiment's pass/fail** — this is the dedicated "unclear rules" detection channel.
8. **Honest denominators:** "0 wrong in n" is always published with its rule-of-three upper bound (≤3/n at 95%) — never bare "zero wrong".
9. **Do not re-test rejected mechanisms:** same-prompt stability voting · alias layers · catalog-first display · curated XBRL dictionary · LLM-distilled anchors · threshold-decided admissions (kernel §13, `95`). Their rejections stand unless an experiment here fails in a way that names one.

---

## §3 What this plan deliberately does NOT run

### 3.1 Existing evidence reused as-is (re-running buys nothing)
Unit resolver 117/117 + 29+7 (UNIT-13/FACT-21) · period cascade + `fiscal_math` 99.1%/549 · concept-link ~100% precision / ~70% recall on 274/795 companies (XC-13/14 — only XC-16 + full-universe remain, build-gated) · naming/slice/fact_type golden 18/19 (Sonnet 5) vs 17/19 (Opus) (PIPE-31) · multi-pass junk (3rd pass ~82%) · the quote-match-vs-judged divergence · 261-test workflow suite + 468-test substrate floor.

### 3.2 Build-gated gates — unchanged homes, still the real rollout blockers
Seed **gauntlet** X-G (kernel §8.3, zero-tolerance, pre-sync) · **X-IM** immune-system proofs (each §9 detector catches its seeded corruption; validator mutation tests) · **S3** sync-vs-async LINK shadow (CLAIM stays OFF until S3 passes with zero wrong links) · **fitness/honesty gate + OD-6 budget** (freeze catalog → fresh PIT events → ≥3,000 pre-registered graded slots → zero confirmed wrong merges (2-grader) → beat 0.634 / 0.535 / 72%) · **X-XL0–3** on the real `xbrl_link_writer` (bars pinned in XBRL §9) · **XC-16 + full-universe concept run** · slice-menu HARD-EXCLUDE/PROVISIONAL list materialization + one owner vet (FACT-26e) · all `12` §12 TDD/golden gates.

### 3.3 Conscious cuts from the pre-code program (with reasons)
- **S1 (seed-size knee):** a seed-build-time sizing dial; nothing pre-code changes it.
- **S2 (three-world shootout):** the most expensive designed experiment for a strategy question v3.4 already answers with a contingency ladder (§8.5). Revisit ONLY on a RED fitness gate.
- **Catalog-scale retrieval decay:** owned in production by the planted-synonym stream (kernel §9.6); mini-scale retrieval recall is measured inside EXP-3.
- **Concurrency / atomicity / park drains / recovery mechanics:** code properties → build-time TDD (OD-15, V8, V14), not model experiments.
- **Judge multi-run voting:** same-prompt stability voting is a REJECTED mechanism; the design's answer is diversity + independence, measured in EXP-0 (shared-miss rate), not repetition.

---

## §4 Shared fixture assets (built once, reused by every EXP)

- **F-A — corpus.** Calibration industry (Restaurants; the Fable-era CAKE run's FROZEN chunks are mechanical raw-text artifacts, explicitly reusable per PIPE-33's corpus ruling) + one adjacent industry for cross-industry traps + **36 Track-B events** (12 earnings 8-K · 8 transcripts · 8 10-Q · 4 10-K · 4 news) across ~12 companies, mandatorily including ≥1 **52/53-week filer**, a **multi-registrant filing**, and a **null-`periodOfReport`** report.
- **F-B — keys** (all sha-locked before any arm runs; DRAFTED by a strong model, ADJUDICATED and locked by Fable; hard calls double-adjudicated; every split logged per §2.7):
  - **K-pairs (~250):** 110 planted-DIFFERENT across ≥9 trap families (kernel §9.6 + X0 lists: bookings/billings · adjusted-vs-GAAP EBITDA · gross/net · segment/consolidated · deferred/recognized revenue · genus–species · benchmark siblings (Brent/WTI, SOFR/fed_funds) · cause-vs-consequence · transmission-channel + ownership-axis homonyms · per-X · cross-flavor) + 50 true synonyms + ~90 real pairs mined from F-C's dedup/repair suggester (real distribution, not only traps).
  - **K-reader (40 chunks, stratified by source type):** candidate causes + evidence locations under the NEW NAME-01…19 / OD-3 rules.
  - **K-route (150 decisions):** the correct arm (ATTACH / ADOPT / CLAIM-defer / CREATE / SKIP) per candidate against the frozen F-C catalog — includes 30 planted probes = the gauntlet's P1/P3–P9 families run pre-seed (three-demand-stories · own-segment · measurement words · per-X trio · brand/geo slices · homonyms · genus-species · benchmark identity).
  - **K-fields (~150 facts over the 36 events):** the full FACT-17b payload per market-moving fact, incl. `12` §12.3 trap classes and OD-9/11/12/13/14 + ISS-16 cases; the "market-moving fact" definition is pinned inside the key protocol (itself a rule-clarity test).
  - **K-stamp (~100 records):** 30 suffixed (incl. 5 deceptive-suffix `regulatory_guidance`-class plants) · 40 bare names spanning metric/action ambiguity (OD-2) · 15 latent-base cases (OD-1) · 15 cross-flavor F3 traps.
- **F-C — mini-catalog (the Track-A smoke test, fixture-grade).** Run the EXISTING engine (`workflows/`) with the PIPE-16…21 **prompt/config overrides** (no new machinery — `10` §3's own claim, exercised here for the first time) on the calibration industry: leaf → reconcile → repair → validate; then EXP-4B stamps fact_type/families on the result; freeze + embed. **Hard checks** (fixture-grade, fix-and-rerun allowed — NOT graded-once): validators green incl. D1 · zero brand/measurement tokens in coined names · per-X transcribed where stated · same-name convergence PRESENT (PIPE-20 — its absence means the override layer failed) · `recall_floor_zero_yield` inspected (footgun 17) · sane D5/Refute traffic. F-C **never feeds the real fitness gate** (that gate is one-shot and post-build).
- **Machinery added (all throwaway; the complete list):** (1) a **scorer pack** — key-diff + the deterministic FACT-16 subset (lane matrix, shape-hint coherence, enums) + the Wilson/rule-of-three gate on the `ab_differ` pattern; (2) a **read-only XBRL census + materializer dry-run script** (computes would-be facts; writes nothing); (3) a **propose-first router-probe workflow** in the PIPE-37 minimal-probe shape (blind coin → PIT top-K card view → route). Reused: fetch/chunk/reconcile/repair/validate stack · `ab_stratum`/`ab_pair_judge`/`ab_differ` · embeddings suggester · Neo4j read tools. Nothing else is built for this plan.

---

## §5 The experiments

### EXP-0 — Grader + key instrument validation
*Instantiates kernel §9.6's calibration stream pre-code; qualifies the OD-6 2-grader protocol. Blocks all judged scoring.*
- **Question:** can the designated grader tier actually catch wrong merges — before graders are used to score every other experiment?
- **Dataset:** K-pairs planted subset (110 different + 50 true synonyms).
- **Models:** Sonnet 5 ×2 independent instances + Opus 4.8 ×1 — blind, default-refuse framing, raw-evidence-only input (smoke-alarm doctrine: no detector conclusions shown).
- **Metrics:** wrong-SAME per grader (a planted-different judged SAME) · false-refusal on true synonyms · shared-miss rate between same-tier instances · per-family blindness table.
- **Pass bar (pre-registered):** a tier qualifies iff wrong-SAME = **0/110** AND false-refusal ≤ **10%**. Any shared miss on a family ⇒ that family is flagged generation-blindness: later "clean" results on it are discounted by that rate and the class escalates per kernel §14.2.
- **Failure action:** Sonnet 5 fails → Opus 4.8 becomes grader tier (cost re-plan). Opus fails → Fable-tier grading for merge-direction judgments only, and the affected claim-classes go to the owner as the honest limit (kernel §14.2). No qualified grader = STOP: no downstream experiment result is meaningful.
- **Cost cap:** ~500 small judge calls.

### EXP-1 — XBRL substrate reality + determinism probe (code-only, zero LLM)
*Runs XBRL §9's P19 census + a dry X-XL0 + the FACT-30 PIT-menu proof + a falsifier-(iii) dry-run — all BEFORE owner ratification of the XBRL bundle.*
- **Question:** do the graph's real XBRL facts obey the materializer's pinned assumptions, and is the recipe deterministic with zero "builder decides" residue?
- **Dataset:** fresh full-graph census (unit-type inventory · no-`IN_CONTEXT` cohort · null-`periodOfReport` cohort · multi-registrant count · `decimals` distribution · raw-duplicate rates) + a **dry-run materializer** over ~60 filings / 12 companies incl. the mandatory fixtures (52/53-week · multi-registrant · null-pOR · an intra-filing precision-duplicate pair). Plus: the **PIT concept-menu query** written and proven on 5 historical events (menu ⊆ ≤ event-time concepts — the XC-09 lock; verified gap: no checked-in query has it) · a **P15 comparator-hit census** (how often the ±7-day YoY comparator exists on real series) · **falsifier (iii)** duplicate-oracle stats over the materialized sample (informational, feeds detector calibration).
- **Models:** none — that is the point.
- **Metrics / bars:** **100% field determinism** vs the surviving source Fact (value/scale · period dates · members→slice · unit · concept · entity — dry X-XL0) · period classifier: 0 windows unclassifiable except via the declared `exact_range`+WARN fallback; quarter-vs-YTD precedence and 364/371-day handling verified on real windows · every skip class counted (unit whitelist · no-context · NON_SLICE/elimination · latent) · PIT menu proof passes · **ANY discovered two-ways-to-code-it ambiguity = FAIL** (the worst class: identity forks between builders).
- **Failure action:** each ambiguity or broken assumption → a named pin amendment to `XBRLIntegrationDesign` BEFORE the owner ratifies (exactly what its P19 anticipates). No pass = no ratification request.
- **Cost cap:** read-only Cypher + scripts; 0 LLM tokens.

### EXP-2 — Blind-producer grid (reader recall/precision × chunking × runs × rulebook)
*Runs `10` PIPE-33's reader A/B + kernel §12 X-C together; feeds PIPE-30/31. The "cheap producer" half of the §11.0 hypothesis.*
- **Question:** what is the cheapest blind reader that loses nothing — and when an arm loses, is the cause the model, the chunk shape, the run count, or the rulebook?
- **Dataset:** K-reader's 40 pre-registered chunks (frozen corpus per PIPE-33's corpus ruling; scoring restricted to key chunks).
- **Arms (8, pre-registered):** Haiku·40k·1 | Sonnet 5·40k·1 | Opus·40k·1 | best-cheap·paragraph·1 | Opus·paragraph·1 | best-cheap·40k·2-run-union | best-cheap·40k·3-run-union | best-cheap·40k·1·**rulebook-ablated** (reader prompt without the inlined NAME rules — the rule-effect control).
- **Metrics:** judged recall + judged precision vs K-reader (EXP-0-qualified grader) · junk rate · error clustering by NAME-rule class · cost per chunk.
- **Pass bars:** a cheap reader is ADOPTED only at recall ≥ (strong arm − 2 pts) AND precision within the Wilson noise gate (zero-loss promotion, PIPE-30). Paragraph chunks adopted only if recall AND precision are non-inferior AND cost drops (X-C's own rule). Multi-run union adopted only if recall gain ≥ 5 pts AND junk stays under the single-run precision bar (the 82%-junk trap re-checked).
- **Failure attribution → action:** cheap arm misses what Opus catches on the SAME chunk → model weakness → tier up. ALL arms miss items present in the chunk → rulebook/prompt defect → fix the inlined block, ONE re-run on a fresh chunk sample. Misses cluster at chunk boundaries/long-chunk tails → chunking → adopt the paragraph arm. Rulebook-ablated ≈ rulebook-armed → the inlined rules do no work → rewrite the PIPE-16 block (rule-clarity finding, not a model finding).
- **Cost cap:** ≤ ~350 reader calls + grading.

### EXP-3 — Admission routing + reuse-display (G1) probe
*Pre-code rehearsal of the PIPE-37 minimal probe; answers the G1 display question (90 §A) at decision level; runs the gauntlet's P-families early. The "cheap router" half of §11.0.*
- **Question:** over a propose-first top-K card view, does the Stage-1 router route with ZERO wrong merges — and when it fails, is the cause the model tier or the display?
- **Dataset:** K-route's 150 decisions against frozen F-C. PIT enforced: candidates strictly later than catalog evidence; retrieval filters `visible_from ≤ event date`; cards per kernel §3 (name · fact_type · companies count · badge · BASE_METRIC line · SAME_AS variants · ≤2 PIT-cut quotes).
- **Arms (4):** router = Haiku·K10-full-cards | Sonnet 5·K10-full-cards | Sonnet 5·K25 | Sonnet 5·K10-stripped (no badges/quotes). **Retrieval recall is measured separately by code** (is the true target in the view?) so a display failure never scores as a judgment failure — PIPE-37's own grader distinction.
- **Metrics:** wrong-merge count (ATTACH/reuse onto a different meaning) · missed-reuse rate (CREATE despite an exact-meaning card in view = over-split; cheap but counted as duplicate cost) · SKIP accuracy · per-trap-family table · retrieval recall.
- **Pass bars:** wrong merges = **0** per surviving arm (0/150 ⇒ ≤2% upper bound — the fine 0.1% bound remains the fitness gate's job; this probe exists to falsify cheaply, not to certify) · retrieval recall ≥ **95%** (else the display/embedding text is wrong, not the model) · missed-reuse ≤ **15%**.
- **Failure attribution → action:** wrong merge WITH the target in view → judgment failure → that tier is disqualified as the lone router; the bounded design change is "cheap router proposes, strong tier confirms ATTACH synchronously" (the kernel's §9.2 ATTACH-audit concern promoted to write time) — an owner decision, proposed with the data. Wrong CREATE with the target NOT in view → display/retrieval fix (K, embed text = name+quote+scope). One trap family failing across ALL arms → rule text unclear → owner rule question + permanent fixture family.
- **Cost cap:** ~600 router calls + suggest-only embeddings.

### EXP-4 — Identity judge + family stamping
*Kernel §6's judge on the X0 fixture families; S-A6 pre-seed; OD-1/OD-2; PIPE-24's DU-05/06 classifier. The "strong judge" half of §11.0.*

**A) SAME_AS pair judge.**
- **Question:** does the 5-check judge at the default strong tier hold zero wrong-SAME without refusing everything — and does the frozen-anchor input shape (vs full evidence) change either?
- **Dataset:** K-pairs full (~250, incl. the ~90 real suggester pairs).
- **Arms:** Sonnet 5·anchor-shape (250) | Sonnet 5·full-evidence-20/side (250) | Opus·full-evidence (trap subset, 110) | Opus·anchor (only if Sonnet fails).
- **Metrics:** wrong-SAME (zero tolerance) · false-refusal on true synonyms · per-check attribution (which of checks 1–5 fired) · anchor-vs-full delta.
- **Pass bars:** the chosen tier: wrong-SAME = **0 on BOTH input shapes** · false-refusal ≤ **10%** on full evidence. Anchor-shape MAY refuse more (that is §6.6's designed trade — measured, not failed) but must not wrong-SAME more.
- **Failure action:** Sonnet 5 > 0 wrong-SAME → judge tier = Opus 4.8 (cost re-plan via the locked A/B discipline). Opus > 0 on a family → the claim-class disables or goes to the owner as the honest limit (kernel §14.2). Anchor-shape uniquely wrong-SAME → revisit §6.3's anchor policy BEFORE build.

**B) fact_type / BASE_METRIC stamping.**
- **Question:** do code-first stamping + the classifier + OD-1's double-check + OD-2's metric-proof produce zero wrong family stamps — including against deceptive suffixes?
- **Dataset:** K-stamp (~100). Doubles as F-C's finalization dry-run (the stamps this produces are frozen into the F-C fixture).
- **Arms:** classifier = Sonnet 5 vs Opus, DU-05 definitions + DU-06 decider VERBATIM (no added clauses — DU-07's overfit lesson) · OD-1 suffix gate asked ×2 independently · S-A6 suffix-blind re-derivation at the judge tier.
- **Metrics / bars:** deterministic suffix path 100% (code — assert, not measure) · classifier ≥ **95%** vs key with **ZERO wrong stamps on suffixed records** · OD-2: **zero unproven-metric stamps** (unproven bare names default action_event, counted) · S-A6: 0 false alarms on clean fixtures AND **5/5 detection** of the deceptive-suffix plants.
- **Failure action:** classifier below bar → strong tier for stamping (once-per-driver; negligible cost). S-A6 misses a plant → the kernel's L1 live falsifier lane needs a stronger model or more evidence per card — owner note before lock.
- **Cost cap (A+B):** ~900 strong-tier calls.

### EXP-5 — DriverUpdate item-contract extraction probe
*Pre-build subset of `12` §12.5's dual-producer probe with §12.3's planted traps live; exercises OD-9…OD-14 + ISS-16 field rules end-to-end.*
- **Question:** can producers fill the 24-field FACT-17b contract accurately enough that validators + parks stay rare — and which fields/rules fail, at which tier?
- **Dataset:** the 36 F-A events; K-fields (~150 facts). Slice menus served read-only from the catalog's Reproduce Cypher at ≤ event time (a query-level approximation of FACT-26's PIT menu — no write machinery).
- **Arms:** Sonnet 5 ×2 independent runs · Haiku ×2 · Opus ×1 on a 12-event subsample (strong reference).
- **Scoring:** the deterministic scorer for everything FACT-16 can check (lane matrix · shape-hint coherence · enums · hint presence · value_text lint) + the EXP-0-qualified grader for meaning fields (driver_state · ISS-16 expectation-vs-temporal routing · OD-13 favorability · OD-9 measurement spans · OD-11 basis · OD-12 signs · slice pick).
- **Metrics:** fact-presence recall (single + 2-run union) · per-field accuracy · wrong-lane rate (metric/guidance/surprise/action) · simulated would-park rate · run-to-run presence disagreement (ISS-62's measure) · per-OD-rule error table.
- **Pass bars (pre-registered):** recall ≥ **95%** single or ≥ **98%** 2-run union on market-moving facts · wrong-lane = **0** after routing rules · value/shape accuracy ≥ **98%** (values are the trading substance) · driver_state ≥ **95%** · would-park ≤ **10%**.
- **Failure attribution → action:** errors cluster by FIELD → rule/prompt defect → doc fix (e.g., OD-9 span copying under-specified) · by MODEL → tier up (Haiku out; Sonnet default) · by SOURCE TYPE → packet/chunking fix · high presence-disagreement → 2-run union becomes the default (cost re-plan). Each cause has a different named fix; none is a redesign.
- **By-product:** the empirical basis for part-2 producer packets + §12.5's [OWNER] thresholds.
- **Cost cap:** ~150 extraction calls (large prompts) + ~400 grading calls.

### EXP-6 — Text↔XBRL twin identity convergence
*Pre-build X-XL1. Mostly a free analysis join over EXP-1 × EXP-5 outputs + the pinned id-recipe script.*
- **Question:** do the two lanes' pinned recipes produce the SAME fact id for the same true fact (P14 period classifier · slice normalizer · P3 measurement fold · P5c value gate)?
- **Dataset:** EXP-5 extracted metric facts × EXP-1 materialized would-be facts → ≥ **100 true twin triples** (company, driver, period), ≥ 10 from 52/53-week filers.
- **Metrics / bars:** id-equality ≥ **99%** on true twins (X-XL1's bar) · value gate: **zero suppressed non-twins** in a hand-checked sample · every divergence classified {period, slice, measurement, value} with a named fix.
- **Failure action:** period divergences → P14/P14c amendment · slice → normalizer/menu fix · measurement → P3 token-set amendment · value → scaling rules. All are pre-ratification pin amendments. Systematic failure (> 5%) → the P5 suppression design re-opens before ratification.
- **Cost cap:** ~0 LLM (analysis) + small spot-grading.

---

## §6 Failure-cause separation matrix

| Suspected cause | Where it is isolated | The controlled comparison |
|---|---|---|
| Model weakness | EXP-2/3/4/5 model axes | same inputs, tier swapped |
| Missing context | EXP-4A anchor-vs-full · EXP-2 chunk sizes · EXP-3 card-content ablation | same model, context swapped |
| Unclear rules | EXP-2 rulebook-ablated arm · all-arms-fail clusters · §2.7 rule_ambiguity exhibits | same model+context, rules varied; adjudication splits |
| Bad chunking | EXP-2 paragraph-vs-40k at fixed model | X-C, run properly controlled |
| Catalog/reuse-display defects | EXP-3 retrieval recall measured separately + K/badge/quote ablations | judgment scored only when the target was visible |
| Too few runs | EXP-2 union arms · EXP-5 dual-run disagreement | 1 vs 2 vs 3 runs, same arm |
| Wrong cheap-vs-strong placement | the §7 grid | per-role tier swaps |

---

## §7 The tiering hypothesis grid (kernel §11.0's owner default as a testable claim)

| Role | Owner default | Falsifier | Decision rule |
|---|---|---|---|
| Blind reader / extractor | Haiku (or equally cheap) | EXP-2, EXP-5 | zero-loss promotion, else tier up |
| Stage-1 router (ONE cheap call incl. ATTACH) | cheap | EXP-3 | zero wrong merges, else ATTACH gets a synchronous strong confirm |
| LINK / SAME_AS judge | Sonnet 5 | EXP-4A | zero wrong-SAME both shapes, else Opus |
| fact_type / BASE_METRIC confirm | Sonnet 5 | EXP-4B | ≥ bars, else Opus (cost negligible) |
| Graders (OD-6 / quarantine / scoring) | Sonnet 5 ×2 | EXP-0 | qualification, else Opus, else Fable + owner honest-limit |
| Escalation / fallback | Opus 4.8 / GPT-5.5 / Fable | reference arms throughout | used only where the default measurably misses |

**Not under test:** the LOCKED rule that a cheap tier may never be the FINAL confirmer of an identity-changing decision (§11.0). These experiments select tier **membership** only — §11.0's own split.

---

## §8 Sequence, dependencies, caps

```
Phase 0 (parallel):  EXP-1 (code-only, start immediately)
                     F-A corpus assembly · K-pairs key draft → Fable lock → EXP-0
Phase 1:             K-reader key → EXP-2
                     F-C mini-catalog build (existing engine + PIPE-16…21 overrides)
Phase 2 (needs EXP-0 grader + F-C):
                     EXP-4B stamps F-C → freeze catalog → EXP-3  ‖  EXP-4A
Phase 3:             K-fields key → EXP-5 (may start any time after EXP-0)  → EXP-6
Then:                results memo → owner ratifications (kernel §15 · XBRL §11 bundle)
                     → coding proceeds → the build-gated gates of §3.2, unchanged.
```

**Global caps:** ≤ ~4,000 model calls total; strong tier ≤ ~1,500; any EXP projected to exceed 1.5× its stated cap ABORTS and reports rather than silently spending. All LLM work in-session subscription agents; embeddings the only metered lane. The dominant real cost is **Fable key adjudication** (five keys) — deliberately front-loaded, because sha-locked keys are what make every later run cheap and honest.

---

## §9 Delegation map (later, at run time)

- **Haiku:** blind reader arms · router arms · mechanical corpus prep (fetch/chunk orchestration).
- **Sonnet 5:** the candidate under test in every judge/grader/producer slot · key DRAFTS (never final) · scorer scripts · census queries · run bookkeeping.
- **Opus 4.8:** escalation arms · diversity grader · adversarial re-check of the scorer pack (a scorer bug fails everything silently — it gets its own reviewer).
- **Fable (NOT delegable):** key adjudication + sha-lock · every wrong-merge exhibit · 2-grader splits / INCONCLUSIVEs · rule_ambiguity dispositions → doc-amendment proposals · GO/NO-GO per pre-registered bar · any bounded design change · the §7 tier-membership recommendation · the owner ratification memo.

---

## §10 What Fable must still review AFTER the experiments

1. **Every wrong-merge exhibit, individually** — the permanent-error class; zero delegation.
2. **The rule_ambiguity ledger** → one-line doc-amendment proposals (the "unclear rules" harvest — expected to be nonzero even if every bar passes).
3. **Tier-membership recommendation** per role + `manifest.models` exact-ID pinning.
4. **EXP-3's router verdict** → whether ATTACH needs a synchronous strong confirm (owner decision memo either way).
5. **EXP-1/EXP-6 pin amendments** → the final XBRL ratification bundle text.
6. **The kernel §15 owner memo** — experiments inform §15.0's MVP dials (gauntlet-lite vs full P1–P9 · plural-ADOPT default OFF · UNSURE valve) with data instead of judgment alone.
7. **Anything INCONCLUSIVE** → escalates as an owner RULE question (the design's own path), never a silent keep.

---

## §11 Coding-readiness verdict

- **Can start NOW (no experiment gate):** Track B `12` §17 steps 1–4 (`driver_ids.py` · period-resolver carve-out · unit relocation · `driver_writer.py` + validators) — every identity recipe is owner-pinned (OD-8…OD-15) and the TDD gates are already specified. **Builder caveat:** read the OD blocks in `66 §0.R` + `95` directly; topic-doc prose still carries the D-1/D-2/D-3 stale spots (back-port debt), and stale prose formally wins for a reader of one doc alone. The three throwaway harness pieces (§4) may also be built now.
- **Must be PROVEN first (this plan):** model policy + router safety (EXP-0/2/3/4) BEFORE any live-kernel admission code and before `manifest.models` pins · XBRL data assumptions (EXP-1, EXP-6) BEFORE the owner ratifies the bundle or `xbrl_link_writer` is built · producer-packet viability (EXP-5) BEFORE part-2 producer build.
- **Must be OWNER-RATIFIED (experiments inform, never replace):** the kernel §15 bundle · the XBRL §11 bundle + its ten §12.3 amendments.
- **Unchanged rollout blockers (post-build):** §3.2's list. GREEN on this plan ≠ production GO; the fitness gate + OD-6 remains the only real GO.

---

## §12 Falsification map — which result forces which design change

| Result | Overturned element | Bounded response |
|---|---|---|
| Wrong merges at BOTH router tiers with the target visible (EXP-3) | Stage-1 single-cheap-call routing incl. ATTACH | synchronous strong ATTACH confirm (kernel §9.2's concern promoted to write time); owner decision |
| Wrong-SAME at Opus on full evidence (EXP-4A) | the 5-check judge for that family | claim-class disable + owner honest-limit (kernel §14.2) |
| Anchor-shape uniquely wrong-SAME (EXP-4A) | §6.3 frozen-anchor input shape | anchor-policy revision pre-build |
| Even-Opus reader misses in-chunk items (EXP-2) | reader prompt/rulebook or chunk shape | PIPE-16 block rewrite / X-C adoption |
| S-A6 misses a deceptive-suffix plant (EXP-4B) | the L1 live falsifier lane's power | stronger model / more evidence per card; owner note |
| Determinism or ambiguity break (EXP-1) | the specific XBRL pin | pin amendment pre-ratification |
| Twin id-equality < 99% (EXP-6) | P14 / P3 / normalizer pins; > 5% → the P5 suppression design | targeted amendments; re-open before ratification |
| A field misses its bar at ALL tiers (EXP-5) | that field's contract (e.g. OD-13 favorability) | rule-revision proposal to the owner |
| No grader tier qualifies (EXP-0) | the 2-grader confirmation layer's model floor | Fable-tier grading + owner honest-limit; downstream claims shrink honestly |

**What no result here overturns:** variant-anchored storage · code-built producer-free ids · propose-first · fail-closed parks · the one law. None of these is model-dependent — which is why they are not experiment subjects.

---

*Assembled 2026-07-08 by Fable from a first-hand same-day read of the FinalDesign set (reading order per the task brief; authority: topic docs + 95 > 90/14 > lock candidates > context packs). This plan adds no design content; every bar above is pre-registered here, and every key is sha-locked before its first arm runs. On any conflict, the cited topic doc wins.*
