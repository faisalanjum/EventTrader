# BUILD_AND_OPERATIONS.md — how to build, test, run, and retire the Driver system

> **Status: PROVISIONAL LIVE (Phase 3, 2026-07-15).** This file owns PROCEDURE: build steps, contracts'
> mechanics, gates, run rules, and hazards. Rule MEANING lives only in `FINAL_DESIGN.md` (rule IDs referenced
> here, never restated). Public channel duties live only in `ChannelContract.md`. Status/history/supersessions
> live only in `STATUS_AND_HISTORY.md`. Until the section-14 zero-loss checks pass, the frozen sources remain
> the byte evidence baseline (`archive/2026-07-15_pre-consolidation/MANIFEST.json`).
>
> **Honest status banner (generated; owning dashboard = `STATUS_AND_HISTORY.md`):** DESIGN is final for
> everything labeled FINAL in `FINAL_DESIGN.md`. CODE/TESTS exist only where stated below (WP-FC-EDITS batch,
> S1 fiscal.ai adapter, proven substrate components). **No production Driver graph exists; the fitness gate has
> never run; the Track B writer stack is unbuilt (S3 awaits owner GO).** "Build-ready" never means "implemented"
> or "run."

## 1. The flow (one picture)

```text
channel adapter (SELECT · FETCH · SUBMIT, per ChannelContract.md)
   -> raw event packet (one per source event, chronological per company)
   -> shared decomposer (ONE prompt+code stack for ALL channels)
   -> internal Candidate Fact Packet (frozen v1.0 — §2)
   -> admission kernel (reuse/create/reject/park; strong-judge tier)
   -> deterministic writer + validators + enrichment
   -> outcomes returned to the channel ledger (written/merged/parked/skipped/rejected)
```

## 2. The internal core packet (frozen Candidate Fact Packet v1.0)

- **The frozen source file `15_CandidateFactPacket.md` stays the temporary FIFTH live file** — owner-frozen
  2026-07-14, amended once by the owner 2026-07-15 (Q4 XBRL row; post-amendment sha `038a0f89…`, pre-amendment
  baseline `86b2fc17…` pinned in the Phase-1 manifest). Relocating its content into this file requires explicit
  owner approval plus a byte/hash proof; until then this section only summarizes and points.
- Structure ("three blocks" = three required + one optional): Block 0 event envelope (source id/type, ticker,
  fiscal-year-end, optional calendar override, event time) · Block 1 transient identity signals (proposed name,
  slices, measurement spans, per-X, quote) · Block 2 the proven fact (all source values/text/conditions/
  attribution evidence, raw units + per-slot hints, shape hints, period inputs, slices; code builds identity) ·
  Block 3 optional verdict (target, direction, force, confidence, mode, producer).
- **The unification:** kernel Stage-0 `evidence_atom` ≡ the Block-2 fact item. Block 1 + Block 2 travel as ONE
  object; on CREATE the same packet's Block 2 becomes the Driver's first DriverUpdate (born-complete,
  FINAL_DESIGN §4.2). Three consumers: admission kernel (Block 1) · fact writer (Block 2) · verdict writer (Block 3).
- Shared decomposition order (fixed): strip direction/effect words → peel measurement spans → keep stated per-X
  in the name → keep portion qualifiers in the name → local own-part-vs-external name/slice test → assemble the
  canonical name → stamp permanent fact type (suffix gate, persistence test, metric-proof) → resolve units,
  stamp `series_unit`. Authority split: code owns format norm, axis tables, unit/period/ID build, ALL validators;
  the LLM proposes ONLY the semantic parts (name-vs-slice role, cause-only name, prose slice kind, fact_type);
  the kernel is final identity authority. **No channel ever code-derives a Driver name from its label.**
- A label-only proposal may be cached only with per-quote confirmation; quote-dependent measurement, time,
  state, and markers are never cached.
- Cross-channel same-event law = OD-8 (FINAL_DESIGN §5.1): same fact converges by id; compatible fills; conflict
  gets a flagged sibling; at most one bare member; read repair covers race duplicates. Channels never coordinate.

## 3. Fiscal.ai channel adapter (first channel; S1 adapter BUILT, smoke-passed)

- Map a real accession to the canonical Report/Event; `canonicalize_source_id` maps `:` → `_`. Graph event
  absent → PARK-RETRY. Store the TRUE document source type (`8k`/`10q`/`10k`); the offline `fiscal.ai-kpi`
  catalog evidence atom is NOT a DriverUpdate channel source type.
- Use the Report public timestamp for PIT order; company fiscal-year-end for fiscal math.
- Period evidence tiers: exact XBRL context first → cadence + adjacent wording → governed fiscal math.
  `time_type` is a REQUIRED semantic output, never defaulted; T1-sibling period type and `KNOWN_INSTANT_LABELS`
  are hints only (conflict → PARK). PARK on T1 context-vs-form mismatch or an explicit contradicting window
  marker. Duration with equal start/end is invalid; instant is the legal one-day form.
- Preserve signed unscaled source value + `fmt`; code scales without changing sign; boundary and sign guards on.
- Measurement from the quote first or a verified label path; otherwise park. Tagged members use the frozen
  axis/menu/unknown-sentinel logic; untagged prose uses the same local kind ladder.
- A bare table value is `reported`; a quote-stated comparison routes through DU-09. Quote required always.
- Vendor-computed changes/common-size are SKIPPED (observed ~62% of rows — evidence, not a threshold);
  source-stated growth is allowed. A missing value may be skipped only after a complete clean source search
  (reopen on new source / repaired corpus / certified locator upgrade).
- Old Guidance rows are NEVER converted; guidance is extracted fresh from source documents.
- Component accuracy ≠ end-to-end accuracy: the seed→kernel→writer pilot remains required before scale.

## 4. Track A — catalog build (PIPE-01..37; design final, unproved end-to-end)

**Pipeline:** billing guard → resolve scope → fetch source text → conservative chunks → blind leaf reader →
exact seed convergence → reconcile → G2/Refute → deterministic assembly → validate → bottom-up folds → repair →
class finalization → final validation → fitness gate.

- Track A builds the offline class catalog only (name, permanent type, `SAME_AS`/`BASE_METRIC`, evidence). It
  never writes DriverUpdates. Per the 2026-07-15 Q3 ruling, the finalized catalog stays an OFFLINE artifact +
  retrieval source; graph nodes are created lazily born-complete (FINAL_DESIGN §4.2). OD-16's sync tool is
  retired as materialize-all; its protected-input guard survives for whatever sync step ultimately exists:
  never rename/delete/retype/re-key/orphan a fact-bearing Driver; links add-only.
- Names are born at company/leaf level except a governed same-name split. Census shape: 11 sectors, 115
  industries, 796 companies (17 single-ticker; 796-vs-786 OPEN). Fetch all supported non-news sources; the
  99.1 earnings 8-K path is chunked with KPI evidence on the first chunk. Surface zero-yield events in the
  manifest (7/47 CAKE events yielded zero — keep the recall-floor counter).
- D1-D8 disciplines: complete approval trace · bounded deterministic tree · one reconcile law at every fold ·
  additive/reversible SAME_AS (quarantine path for confirmed-wrong) · explicit same-name split/rewrite/park ·
  strong-Refute dedup (never lexical) · byte completeness source→evidence · exact fold input/output/park
  accounting. Every consumer verifies sidecars, hashes, counts, fold flag, unchanged bytes; menus match the
  chunk manifest; every seed needs a gate result or review entry; repair judges only code-suggested pairs.
- Prompts use NAME-01..19 + slice law + MF-02 ONLY (never old ontology files). Delete class-level XBRL guesses
  and unused `optional_links`. Live reuse is propose-first + bounded PIT related view + strong admission.
  Finalization stamps permanent types and builds family records: a suffix base resolves to an existing record,
  a matching variant's representative, or a latent name in `families.json` (a latent is not a catalog record or
  retrieval candidate). Final checks cover type completeness, family target/type, suffix coherence, latent
  sanity, and cross-flavor disagreement — no hand edits.
- **Exact constants (carry, never re-derive):** 40,000-char chunks · seed limits 400 records / 300,000
  compact-JSON chars · evidence 20 items/side, smallest side first, round-robin least-represented company, one
  per source type first, next disjoint 20 for view 2, no padding · high blast = 8 companies or a global fold
  with ≥2 children · repair: Python `limit=2000`, JS per-pair `200`, batched `0`=all (`600` is a page),
  `PIECE_ROWS=100`, batch `k=10`, record-disjoint deterministic h32 shuffle, canary `0.02` min `5` · retrieval:
  `text-embedding-3-large`, `top_k=5`, `min_score=0.60`, embeddings suggestion-only · `norm()` = strip+lowercase;
  h32 = non-cryptographic 31-polynomial UTF-16 rolling hash.
- **Models:** configuration slots chosen by experiment. Reader = signed EXP-2: `claude-sonnet-5`, effort=high,
  40k chunks, one run. Strong identity/refute roles are governed separately and may NOT be weakened by that
  result. Any optimization changing a judge's visible context or model needs a measured A/B gate (PIPE-32);
  owner-locked rule supersessions are exempt. Pin exact model IDs in `manifest.models`.
- **PIT:** offline NAME creation may use full history (names carry no fact value); anything shown to a
  historical producer and every fact-time menu cuts at public time.
- **State:** WP-FC-EDITS landed (`5db902f`, 2026-07-10; 260 tests + 1 skip): NAME rules inlined, dead leaf XBRL
  code removed, MF-02 + model slots + `min_score=0.60` at all four sites. Remaining: fold/tree prompt mirrors,
  finalizer, hardening/recall floor, fixture rebuild, calibration leaf, first real two-industry fold,
  finalization, then the OD-6 fitness gate.
- **OD-6 fitness gate (never run):** freeze a catalog · fresh covered-industry events · ≥3,000 fixed
  pre-registered slots, key hash-locked before calls · ≥2 independent producers, grader ≠ producer ·
  name+direction floor 0.634 · inter-producer agreement floor 72% · ZERO two-grader-confirmed wrong merges ·
  zero unresolved flags after one blind regrade · red/inconclusive burns the key into regression fixtures.

## 5. Track B — fact stack (FACT-01..36; design final, UNBUILT — S3 awaits owner GO)

- Deliverables: IDs, writer/CLI/shell, period resolver, unit resolver, slice menu, concept linker, verdict/DCM
  writer, reads, park ledger, validators, tests. Producer-agnostic: build against the internal packet only.
- **ID shape:** `du:{safe_source_id}:{driver_name}:{fact_scope}` + the OD-8 collision overlay. Known mapping:
  fiscal `:`→`_`. STILL MISSING (10.3 gap — not implementation-ready): the complete cross-channel escaping/
  delimiter recipe, collision-safe namespaces, and fixed ID test vectors.
- **Writer:** one atomic write; MERGE on id; `created` only on create; legal non-null fields; a sparse rerun
  never null-clobbers a richer value (`SET x = null` REMOVES a property in Neo4j — validate before any SET);
  conflicting signature slot → sibling (repair lane only may correct); non-signature conflicts →
  last-write-wins-with-log; edges/periods/concepts/constraints inside the atomic path; dry-run DEFAULT, writes
  need the explicit environment gate; sidecars namespaced per source event. One source event = the fusion/
  collision locality; a missing surprise home re-extracts the WHOLE event.
- **Validator groups (all deterministic, machine-readable):** ID/scope build · existing typed Driver · lane
  matrix · state-in-lane · shape hints/grammar · signed-value rules · stated-only fields · baseline enum ·
  units/scaling/per-X · period-edge/scope symmetry both ways · ISO dates · quote required · value_text lint ·
  instant/duration legality · stated-movement midpoint (skips stored `unknown`) · period-scope/sentinel pairing ·
  surprise composition/home/tense (all OD-21 cases).
- **CLI order:** hints → compose/validate surprise → fuse → period/slice/measurement → units/canonical values →
  collision → ID → validate → write; plus code-served PIT prior view (`date <` source time), sidecar, park
  ledger, shell seam.
- **Build order:** 1 IDs/scope/unknown-axis round-trip · 2 period resolver + proofs (21 tests, Dec/non-Dec
  YTD+TTM, parity, write-once mismatch guard) · 3 unit relocation + per-slot hints + lint (keep the resolver
  parity test in permanent CI — it calls private old-Guidance helpers) · 4 writer/constraints/field validators/
  lane fixtures · 5 CLI · 6 optional old-Guidance dry-run QA fixture (never production replay) · 7 slice/menu
  tables from a FRESH graph census · 8 verdict writer + DCM · 9 concept linker + rollout gates (vetoes C/D and
  the historical PIT menu query were spec-only — build before rollout) · 10 read layer + golden tests · 11
  dual-producer probe when real producers exist.
- **Acceptance:** resolver/parity gates · synthetic fixtures for every lane and shape incl. all OD-21 cases ·
  concept backstop + PIT menu proof · ≥2 independent producers over a locked sample measuring field/state/
  fact-presence disagreement (threshold owner-set after calibration) · collapse/day-boundary/member-grouping/
  raw-reconciled/backtest-live read tests.
- Substrate floor: 468 tests + 7 guards is PROVENANCE of the audited old stack, not proof the new one passes.

## 6. Track C — old Guidance retirement (active v2.0; NO replay)

- Archive + retire the old Guidance graph/code/writers/readers/prompts/seams. Preserve evidence. NEVER mint
  production Drivers/DriverUpdates from old rows; no replay, no `legacy_name_map`, no packet bridge, no dual
  labels, no `regenerated_from`. New names via Track A/admission; new facts via Track B; fresh guidance from
  source documents.
- Old rows = QA evidence only (recall, qname/member answer keys, regression, resolver/read parity).
- Census evidence (2026-07-03 — RE-CENSUS at retirement): 8,432 updates · 894 sources (532 Reports, 362
  Transcripts) · 548 anchors · 237 periods · 4,148 fact-level qnames + 460 member links (answer-key evidence) ·
  `guidance_status` exists on only 24/894 sources — never a run ledger.
- Retirement order: freeze/drain old writers → export + verify (restorable archive: every property/edge/anchor/
  period, code/prompts, manifests/locators, hashes/counts, timestamps, git + database identity) → scan all
  consumers → cut prediction/learner readers over or prove empty-history tolerance → prove no old packet/read
  path remains → owner approval for deletion → delete old nodes/edges, orphan only old periods → remove seams.
- Green gates: exact export counts/evidence · drained writers · no remaining consumers · no replay marker ·
  acceptable empty-history behavior or explicit wait · owner acceptance of the temporary history gap · no
  production residue. Shared pure helpers may move under Track B ownership.

## 7. Running layer (NOT yet designed-complete — the runbook must still define and prove)

Source schedules + per-channel selection · all channel adapters + certifications (only fiscal.ai's S1 adapter
exists) · one central event/run ledger + returned channel outcomes · core ownership of parked facts,
whole-event retries, cursor updates · live + historical backfill orchestration · verdict production + open DCM
decisions · QA gates, alerting, budgets, exact model policy · catalog-to-graph lazy materialization + protected
imports · prediction/learner/scanner cutover + empty-history behavior · incremental refresh (below) · Track C
execution · production write approval + rollback/recovery checks.

**Incremental refresh rules (already recorded, must survive):** fold base+delta · freeze old-to-old decisions at
every level · source-id ledger · SKIP reopens while PARK stays terminal as specified · atomic `_state.json`
publish · inherit the locked ruleset hash · industry-level fold allow-list · verify Transcript-ID immutability
before the first run · re-run finalization with prior types frozen · latent bases stay out of fold inputs · a
finalizer-hash mismatch is a loud owner signal, never automatic type invalidation.

**OD-5 change scanner (recommendation only):** read-time, code-only consumer of collapsed series + PIT history;
triggers = named state transitions, closed-shape deltas over per-unit-family thresholds, derived `narrowed`,
exact inequality of normalized `value_text`; output = notification/flag events, never facts; no model; never
reads realized returns.

## 8. Candidate bundles (clearly split: accepted vs pending)

### 8.1 Admission Kernel v3.4 — LOCK CANDIDATE

- **Accepted / owner-approved (law, in FINAL_DESIGN):** born-complete admission + first fact · cheap roles never
  final-confirm · OD-18 flagged-ATTACH confirmation · `SAME_AS`/`CONTINUES_AS` quarantine + `disputed` recovery ·
  OD-19 conditional gate + permanent refusals · OD-20 continuity · role TIERS locked (exact membership
  experiment-driven).
- **Candidate (needs the named owner bundle/tests):** anchor-first live kernel + seed/deep-clean tree · blind
  candidate normalization/lint/suffix/collision/PIT top-K + arms (ATTACH/ADOPT/CLAIM/LINK/CREATE/SKIP + one
  UNSURE rejudge) · limited G1 view (exact + bounded related, safe badges; never full catalog/values/XBRL/
  latents/future data/hidden scores) · exact attach, reorder-only adopt, at-most-one claim, named retry/terminal
  park classes, one shared type/family resolver, protected live nodes · LINK pair assembly + five-check
  default-refuse judge + high-blast second skeptic + reversible SAME_AS memo/head/cache; CLAIM ships OFF until
  the named zero-wrong stage · frozen raw birth quotes + refuted negatives, no default evidence distillation,
  controlled refreeze · broad/established eligibility, live transaction freeze, split review, validators V1-V14,
  rollout gauntlet, smoke-alarm immune system, falsifier/attach audits, BASE_METRIC/family recovery propagation.
- **Transfer whole at migration, never re-derive:** kernel §15.0's exact MVP split (day-1 core vs deferred-inert,
  incl. no-XBRL admission fenced until falsifier (v) ships) and §16's honest residuals — above all: qualitative
  homonyms have NO model-independent tripwire (the design's stated deepest worry).
- Never call the whole file ratified because the title says v3.4 or some OD rules were inserted.

### 8.2 XBRL-native materializer — CANDIDATE, dormant (title says FINAL; status = pending ratification)

- Text remains the only path that creates Drivers and narrative facts. The existing text-fact concept linker
  (FINAL_DESIGN §8) stays current.
- The candidate: deterministic code materializes entity-scoped numeric metric facts for already-admitted ACTIVE
  (company, driver)→concept resolutions. Covered facts need in-filing entity match, approved measurement fold,
  representable axes, allowed unit, exact period, source-stated value. Non-GAAP, unlinked, qualitative, causal,
  guidance, and action material stays text-side. **Unit whitelist v1: USD, shares, USD-per-share — eligible
  EPS/per-share facts ARE materialized (per-X in the name per NAME-13); every other unit skips + counts.**
- Materialize before text; text twins dedupe only on same event/head/period/slice/fold/value; mismatch splits
  or parks. Prefer period-of-report facts; comparatives are backfill/restatement. Same-series exact XBRL wins
  ties; same-day 8-K remains; compatible upgrades via repair lane + auditable UpgradeEvent.
- Active/revoked ConceptResolution lifecycle, cohort exclusion, recovery/re-extraction, menu-evidence invariant,
  isolated kernel falsifier, duplicate/miss ledger. Honest non-repair lanes for divergent periods/slices remain.
- P1-P17/P19 + ten document amendments require owner approval after EXP-1/EXP-6 evidence. **The dormant `09`
  rider stays dormant: no `origin`, no `xbrl_link`, no empty≡GAAP folding, no XBRL producer rules before
  ratification.**

### 8.3 Bayes learner proposal — UNVETTED

One company-event-return-window training row containing ALL Drivers (never one full return per Driver);
post-outcome only; strict outcome-blind train/live parity; versioned derived outputs that never mutate
Driver/fact/verdict data; must beat simple + joint baselines and pass its five proof gates before promotion.
Archive under proposals; import nothing without owner approval.

## 9. Experiment program (signed artifacts are the ONLY status authority)

- `FableExperimentPlan.md` defines WHAT to test (sha-pinned `51966848…7472` — keep byte-identical, no banner).
  `FableExperimentWorkOrder.md` defines HOW (current sha `4911a22f…`; the status board still pins stale
  `1586761a…` as v1.8 — record the actual hash/version before more runs). Neither amends production law.
- Ladder: EXP-0 graders · EXP-1 deterministic XBRL reality · EXP-2 reader config · EXP-3 G1/router · EXP-4
  identity/type/families · EXP-5 the 24-field packet · EXP-6 text/XBRL convergence. Pre-register + hash-lock
  keys, grade once, PIT inputs, subscription execution, exact model IDs, ambiguity exhibits, recorded
  denominators, no retest of a rejected mechanism without a named fix.
- **Signed status (2026-07-15):** WP-0 DONE 07-09 · EXP-1 PASS 07-09 (incl. owner-ratified O13 dimension
  binding: explicit-dims positional pairing, typed dims dropped fail-closed) · EXP-0 PASS 07-10 (qualified
  grader = two independent `claude-sonnet-5` at effort=high; the (model, effort) PAIR is binding;
  `claude-opus-4-8`@high = backup) · WP-FC-EDITS DONE `5db902f` 07-10 · WP-FA corpus complete + O2 signed 07-10 ·
  K-reader v3 LOCKED (1,175 records) 07-10 · EXP-2 PASS 07-11 (sonnet-5@high, 40k, one run) · **EXP-3..6,
  remaining keys, WP-FC-RUN, F-C freeze: PENDING — never infer from stale headers.**
- Standing gates: the **ra_0007 carry-forward** (kernel §6.1 judge-contract semantics review) is due BEFORE
  K-pairs.v2 is drafted/adjudicated; the qualified-grader (model, effort) pair binds every downstream graded
  call. Budget history: Plan ~4,000 total/~1,500 strong is the rough cap; WorkOrder D4 refines to ~3,600-4,300
  calls (~1,900-2,100 strong) + a 6,000 global abort under the Plan's 1.5× convention — execution history, not
  an owner question. Kernel owner rules supersede old cheap-final-confirm / shared-miss-discount wording
  (shared miss is measured, not discounted). `HANDOVER_2026-07-12.md` is a dated snapshot (mislabels
  `FablePromptv2.md` as current), not a front door.

## 10. Load-bearing implementation hazards (verified; keep beside the procedures)

**Catalog/Track A:** never consume a catalog without green `validation_exit.json` + matching hashes + correct
fold flag · old `runs/` catalogs and CAKE artifacts = calibration evidence only; re-cut fixtures under current
rules · the reconcile command may not throw on failed validation — the sidecar check is load-bearing · the
two-argument validator path can skip approval checks with only a warning — always pass the approved file ·
resume/repair "plan" functions can unlink stale files (mutating!) · menu jobs finish out of order — resume by
exact filenames · long JSON lines/large agent writes can truncate — piece writes + counts + h32 asserts · workflow
args may arrive as JSON strings — keep the parse shim · fold parks don't roll up into the short summary — inspect
fold sidecars · `SAME_AS` precedence may resolve a direction conflict without a diff alarm (by design) ·
standalone repair downgrades a fold sidecar; only the governed tree flow restores it · source-manifest counts
count events, not KPI pseudo-sources · environment-first graph config (a hard-coded Neo4j fallback exists in old
fetch code — must never drive writes) · return schemas must accept real nulls · subscription billing guards
required — no metered SDK/CLI without approval; start large fan-outs in a fresh five-hour window; resume per chunk.

**Fact/Track B:** Neo4j `SET x = null` deletes the property — never let a sparse rerun erase a richer fact ·
DriverPeriod dates are write-once; mismatch hard-fails · the inherited period cascade may fail OPEN on infra
errors — log degradation; the Driver wrapper still hard-fails unresolved items · route `calendar_override`
before fiscal cache branches (read too late in the old substrate) · the pure old period builder can mint a
year-2000 month when fiscal year is missing — forbidden · the unit resolver calls private old-Guidance helpers —
parity test in permanent CI · raw `$/barrel` can resolve dangerously without hints — the per-X hard failure is
load-bearing · concept vetoes C/D + the PIT menu query were spec-only — build before rollout · `<` vs `<=`:
backtest/history reads strict `< as_of`; write/menu visibility `<= event public time` · the in-menu check is
exact string equality — same qname prefix form on both sides · graph quirks: `is_numeric` stored as string `'1'`;
consolidated membership = null OR empty array (preserve both checks) · no bare Python `assert` for production
validation · both `gp_` and deprecated period-id namespaces may exist — the new resolver emits only `gp_` ·
namespace Driver artifacts (old `/tmp` sidecars collide) · old concept experiment outputs point to a dead
scratch dir — revalidation re-pulls source data · the extraction worker snapshots allowed types at import
(adding `driver` needs a restart), has guidance-specific seams, and its metered SDK entry is NOT an approved
Driver path — use the subscription contract.

**External substrate pointers (reuse, never copy in):** HCP = `../HierarchicalCatalogPlan.md` (catalog-engine
mechanics) · `../Consolidation/GuidancePeriod.md` (21 period tests) · `../Consolidation/UnitExtraction.md`
(shared unit resolver — TRAP: its embedded naming block shows REVERSED examples `taco_bell_same_store_sales` /
`adjusted_eps`; copy only per-X Rules 2-6/8 into prompts, never its naming examples) ·
`../Consolidation/XBRL_SliceAxis_Catalog.md` (frozen axis table data). Never recover a current rule from
`Drivers.md`, `DriverOntology.md`, `INDEX.md` §3b, `WIP/unit_probe/RESULTS.md`, `WIP/DriverGraphSchema.md`
:331/:333, or the old archive tree.

## 11. Missing recipes (open build gaps — no new design authority here)

1. **Packet lifecycle:** when exactly the strong admission decision stamps the permanent type; how Block 1→2
   hand off without treating a proposal as final.
2. **Born-complete transaction:** the exact atomic CREATE write + failure behavior, specified WITHOUT ratifying
   the rest of the candidate kernel (lazy-create-on-ATTACH mechanics land at the OD-7/live-admission pass).
3. **Source identity namespaces:** the complete cross-channel escaping/delimiter law + fixed test vectors
   (only fiscal `:`→`_` is explicit today).
4. **Adapter/writer machine contracts:** exact field types/nullability, versioned schema, complete
   outcome/reason codes, cursor/completeness record shapes, certification fixtures (contract not
   implementation-ready until closed).
5. **Exact blocks still source-resident (transfer proved at Phase 4, per the front-door banner rule):**
   kernel §15.0's MVP split + §16's honest residuals (§8.1 above notes them) · `12` §12.3's exact fixture
   tables · any remaining prompt-block text the section-14 diff finds. Until each transfers, the frozen source
   carries it.

## 12. Evidence worth keeping once

Fixed-vocabulary v1 rejected ~82% of useful names; eager-reuse v2 merged distinct demand stories — the two
deaths that justify open vocabulary + err-toward-separation. Units: 117/117 main + 29/29+7 guards + three 33/33
runs (components, not wiring). Concept links: 31-company proof — 0 wrong links/249 accepted, 0 wrong abstentions/
1,178, ~99.4% tail recall; 274-company validation — 100% sampled precision, ~70% recall, 98% three-run identity,
with an incomplete hand list and a known "one wrong" tuning caveat (keep the caveat beside the numbers).
