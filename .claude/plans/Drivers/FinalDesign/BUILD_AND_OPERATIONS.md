# BUILD_AND_OPERATIONS.md — how to build, test, run, and retire the Driver system

> **Status: LIVE — Phase 4 verified through round 11 (2026-07-15); Phase 5 archive pends owner GO.** This file owns PROCEDURE: build steps, contracts'
> mechanics, gates, run rules, and hazards. Rule MEANING lives only in `FINAL_DESIGN.md` (rule IDs referenced
> here, never restated). Public channel duties live only in `ChannelContract.md`. Status/history/supersessions
> live only in `STATUS_AND_HISTORY.md`. Until Phase 5 archives them, the frozen sources remain
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
  2026-07-14, amended twice by the owner 2026-07-15 (Q4 XBRL row, then the Q1-extension on the FETCH
  guidance clause; current post-amendment sha `aa7239ed…`, pre-amendment baseline `86b2fc17…` pinned in the
  Phase-1 manifest). Relocating its content into this file requires explicit
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
  Finalization = PIPE-24/25, the mandatory end-of-build pass (`finalize_catalog.py`) — stamps every surviving
  Driver once, permanently; no consumer ever sees a fact_type-less Driver (the sidecar gate blocks
  pre-finalization catalogs). Artifacts: `fact_type_decisions.json` · `families.json` · `fact_type_disagreements.json`.
  **BASE_METRIC lookup order (deterministic, all via `norm()`, suffix stripped ONCE):** (1) the stripped name is
  a record (self-canonical or final-level variant) → the edge targets the STRIPPED NAME ITSELF, never re-pointed
  at the head (`net_sales_guidance → BASE_METRIC → net_sales → SAME_AS → revenue`); (2) the stripped name matches
  a string in any record's `same_as_variants` → the edge targets that containing rep (a collapsed name never
  becomes a node); (3) found nowhere → the name goes in `families.json.latent` ONLY — a latent is NOT a
  catalog.json record, can never enter a fold input or retrieval view, is implicitly `fact_type=metric`, and
  graduates AUTOMATICALLY when a later build gives the exact `norm()` name real evidence; `action_event` gets no
  edge; a suffixed rolled-up variant inherits the family through its `SAME_AS` rep (no edge of its own). Final
  checks cover type completeness, family target/type, suffix coherence, latent sanity, and cross-flavor
  disagreement — no hand edits.
- **Exact constants (carry, never re-derive):** 40,000-char chunks · seed limits 400 records / 300,000
  compact-JSON chars · evidence 20 items/side, smallest side first, round-robin least-represented company, one
  per source type first, next disjoint 20 for view 2, no padding · high blast = 8 companies or a global fold
  with ≥2 children · repair: Python `limit=2000`, JS per-pair `200`, batched `0`=all (`600` is a page),
  `PIECE_ROWS=100`, batch `k=10`, record-disjoint deterministic h32 shuffle, canary `0.02` min `5` · retrieval:
  `text-embedding-3-large`, `top_k=5`, `min_score=0.60`, embeddings suggestion-only · `norm()` = strip+lowercase;
  h32 = non-cryptographic 31-polynomial UTF-16 rolling hash.
- **Finalization exactness (PIPE-24/26/35 operational guards):** the classifier prompt = DU-05's four
  definitions + DU-06's decider, both VERBATIM, nothing else — a tested extra clause overfit (DU-07); input per
  record = name + representative evidence. Verdicts for BOTH populations land in `fact_type_decisions.json`,
  each row tagged `self_canonical: true/false`, bound by `--expect`+h32, run in name-sorted ≤400/≤300k batches,
  relayed via `PIECE_ROWS` piece-writes; stamps come ONLY from `self_canonical:true` rows (variants copy their
  canonical's type). Finalize HARD-FAILS if any input record already carries `fact_type` (re-stamping reachable
  only through the re-assemble remediation path). All three outputs written temp-file + atomic rename; crash
  recovery = re-run assemble → validate → finalize. `validate_catalog.py --final` rewrites `validation_exit.json`
  with the new catalog sha + `families_sha256` + `final:true` + the PRESERVED `fold` flag. PIPE-35 consumers
  verify all of that FIRST, then read only clean `catalog[]` records; side-lists, UNCLEAR parks, and latent
  names are never tradeable and never reuse candidates. **K2:** fold repair stays per-pair; batched fold repair
  is a deferred optimization needing its own experiment.
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
- **Writer:** one atomic write; MERGE on id; no-op re-runs detected by DIRECT FIELD COMPARISON against the
  existing node (no stored fact hash — `evhash16` retired); `created` only on create; legal non-null fields; a sparse rerun
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
  YTD+TTM, parity, write-once mismatch guard, and the `HAS_XBRL` race guard shipped as a PRODUCER ELIGIBILITY
  check, never inside the resolver — PER-20) · 3 unit relocation + per-slot hints + lint (keep the resolver
  parity test in permanent CI — it calls private old-Guidance helpers) · 4 writer/constraints/field validators/
  lane fixtures · 5 CLI · 6 optional old-Guidance dry-run QA fixture (never production replay) · 7 slice/menu
  tables from a FRESH graph census · 8 verdict writer + DCM · 9 concept linker + rollout gates (vetoes C/D and
  the historical PIT menu query were spec-only — build before rollout) · 10 read layer + golden tests · 11
  dual-producer probe when real producers exist.
- **Acceptance gates (in order, every one mechanical — `12` §12):**
  1. Resolver gates: the 21 period tests + YTD/TTM proof + `_ensure_period` parity · unit relocation 29+7 green + parity tripwire · full validator suite TDD (every FACT-16 rule has a failing-then-green test).
  2. Archive-backed guidance fixture test (optional QA, never a Track C gate): old rows sampled in DRY-RUN for resolver/read parity; test-only shims derive the missing hints (shape from low/high pattern, unit from `canonical_unit`); fixture Driver nodes minted from the sampled label_slugs in DRY-RUN; exact mappings: label_slug → driver_name VERBATIM · a real narrower segment → `segment:slug(segment)` · legacy Total/empty → omitted slice; member-linkless; never writes production facts.
  3. Synthetic lane fixtures: one golden item per lane × shape (point/range/floor/ceiling/numberless/delta-only) + planted traps (point-as-low-only · missing hint · sign flip · consensus-on-metric · value_text-with-number · duration start==end · fabricated period · two-scenario same-event collision → both quote_hashed · per-X name/unit mismatch · unknown-axis hex round-trip). **OD-21 FAILURE traps (validate BEFORE fusion; must hard-fail/PARK with the right reason):** F1 `surprise=` missing on a surprise fact · F2 `surprise=` on a non-surprise fact · F3 missing/misplaced `surprise_basis_hint` · F4 missing `comparison_baseline` · F5 `guidance`+`previous_guidance` combo → REJECT (guide-vs-own-prior = movement, not surprise) · F6 grounded surprise with no in-batch home fact → fail-closed PARK, then the WHOLE event re-extracted (never orphan-only replay) · F7 impossible tense (`actual_vs_*` on a not-ended period) · F8 ungrounded surprise ("results beat") → PARK, never dropped · F9 a candidate sibling mismatching on ANY ONE of {family, period, period_scope, slice, measurement, value, unit} — each tested SEPARATELY — rejected as a match → PARK. **OD-21 POSITIVE fixtures (must pass):** P1 outlook surprise + later earnings surprise on the same driver+period survive as TWO series · P2 same-event "beat consensus AND own guidance" splits into TWO surprise facts · P3 guide range containing consensus → `in_line` · P4 an old guide restated after period end stays `guidance_vs_consensus` via the basis hint · P5 a numberless grounded surprise writes WITH its numberless home sibling · P6 all three valid basis×baseline mappings compose · P7 two facts identical on every key field except `surprise=` stay SEPARATE · P8 a lower-is-better beat (opex/cost/inventory) is ACCEPTED, not sign-rejected. Only P1/P2/P7 need the real fusion + read-collapse code and are BLOCKED until the Track-B build; the failure traps and other positives are static/validator-level and run now.
  4. Concept-link gates: backstop A-D unit tests + `vetoed_correct == 0` invariant + PIT menu-query proof + XC-16 before any full-universe run · the XC-17 sampling monitor live at rollout (balance/period_type-vs-expected-signature check + abstention-by-fact_type tracking; structural slips only — scope mismatches need XC-16/the periodic audit) · XC-18 scale rules (resolve once per company × base-metric driver + store; one batched LLM call per company; cache only if volume bites).
  5. Dual-producer probe: ≥2 independent producer runs over a pre-registered PIT-filtered sample; score field-level, state-lane, and fact-PRESENCE disagreement; grader ≠ producer, graded once; thresholds proposed after first calibration (protocol pinned now, bar = owner after data).
  6. Read-view gates: collapse/tie-break/day-boundary golden tests (incl. an after-hours 8-K ET-vs-UTC case) · T12.9 grouping fixtures (renamed label groups; a CONFLICT stays split) · two-mode PIT proof (backtest at T excludes a date==T fact; live sees it).
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
  consumers (exact search list: `GuidanceUpdate`, `Guidance`, `build_guidance_history`, `guidance_history.v1`,
  old guidance extraction profiles, guidance daemons/workers, old writer scripts) → cut prediction/learner
  readers over or prove empty-history tolerance → prove no old packet/read path remains → owner approval for
  deletion → delete → remove seams (old writer, CLI, shell wrapper, concept resolver, extraction profiles,
  worker guidance sidecars).
- **Exact deletion target:** delete `GuidanceUpdate` and `Guidance` nodes; delete ONLY orphan `GuidancePeriod`
  nodes with no `DriverPeriod` label AND no incoming DriverUpdate links; drop old guidance constraints/indexes;
  **never relabel old `GuidancePeriod` into `DriverPeriod` as a transition shortcut.** Gate check: archive edge
  counts must match the old graph for `UPDATES`, `FOR_COMPANY`, `FROM_SOURCE`, `HAS_PERIOD`, `MAPS_TO_CONCEPT`,
  and `MAPS_TO_MEMBER`.
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

> **Candidate-file policy (round 11):** the two candidate documents — `FableAdmissionKernelDesign.md` and
> `XBRLIntegrationDesign.md` — **stay LIVE at the root until their ratification decisions**, exactly like the
> experiment Plan/WorkOrder. This section's job (per the consolidation spec) is the accepted-vs-pending SPLIT
> and the exact ratification bundles — NOT a duplicate of the candidates' full mechanics: an independent
> enumeration found ~68 kernel-only build-critical elements (park codes, the five LINK-check meanings, V1-V14
> definitions, falsifier definitions, phase/gauntlet mechanics…) whose faithful transfer would copy the whole
> unratified file into this guide. On ratification, accepted content transfers into the law/build files
> properly; a rejected candidate archives. Until then the live candidate file is the full text.

### 8.1 Admission Kernel v3.4 — LOCK CANDIDATE (live file at root until ratified)

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
- **Kernel §15.0 MVP split (transferred whole — the exact first-build fence):**
  - Day-1 core: kernel Stages 0-3 (ATTACH+confirm · ADOPT · CREATE born-complete · SKIP/PARK) · async LINK trigger + deferred-pair ledger with no-mint-on-flagged-head · frozen birth anchors · evidence-mass gate + skeptic-minted ESTABLISHED (cannot defer: the day-1 sweep's eligibility rule depends on it) + BROAD split · validators V1-V14 · falsifier signals (i)(ii)(iii)+(vii) + ATTACH-audit · minimal calibration stream · recovery core (quarantine + variant/family propagation + RecoveryEvent) · seed + gauntlet static scans (S-A2/A3/A6) · park/outage discipline. **Coverage rule:** if the MVP admits no-XBRL (news/qualitative/action) drivers, falsifier (v) ships day-1; otherwise admission is FENCED to XBRL-backed sources until (v) ships — the qualitative space is never live-and-uninstrumented.
  - Deferred (flag/experiment-gated, inert until enabled): CLAIM-ON (S3) · anchor enrichment M2 · item-codes M3 · UNSURE valve · union-preview · falsifier (iv)(vi) · full dynamic gauntlet P1-P9 if the owner ships the seed YOUNG-only · transitive-drift cadence beyond quarterly · exotic-latent propagation · head-degree sharding · time-keyed anchor revalidation · sampled-audit rate tuning · type-CORRECTION lane (recall optimization; parking covers safety).
- **Kernel §16 honest residuals (transferred whole):** the irreducible floor = a single-shot hardened judge wrong on a genuinely co-extensive-looking pair at FIRST encounter, before any falsifier signal — measured by OD-6, reversible by recovery once evidence accumulates (zero-by-construction impossible; zero-by-measurement with honest upper bounds is the promise) · homonym facts written before detection stay on the quarantined node as flagged history — contained, never erased, excluded from features · all in-session judges share one model vendor; the falsifier is the only fully independent oracle · **qualitative homonyms have no model-independent tripwire** (for no-XBRL non-numeric heads, falsifier channels (i)-(iv) are silent and (v) detects duplicates, not one-name-two-meanings; only drift/dispersion probes and audits watch; the quarterly held-out gate re-runs are the backstop — the stated deepest worry) · history completeness is the ambition's success metric (duplicate half-life + reconciliation efficacy + park drain + false-refusal rate as a first-class dashboard number) · conservative splits and deferred thin pairs under-attribute during their window — the safe direction, visible in metrics.
- **The exact ratification bundle (what the owner must ratify to activate the candidate):** (1) the v3.2 architecture (variant-anchored storage · one LINK mechanism/two triggers · frozen birth anchors + split-reconciliation lane · skeptic-minted establishment with CLAIM_FROZEN de-mint) · (2) edge-state recovery + D4 scoping (automatic tightening-only quarantine for all links, 2-grader confirmed on RAW EVIDENCE with no falsifier framing, 3-grader for seed links; INCONCLUSIVE escalates the RULE, not the case) · (3) the seed gauntlet as a launch gate incl. seed cards earning ESTABLISHED (unprovable → YOUNG) · (4) launch blockers: corrected model-free falsifier + ATTACH audit before production writes; flagged-head audit intensity bounded — 100% for the first N/T, then risk-stratified — with a hard SLA that never hangs on the owner queue · (5) CLAIM ships OFF; shadow-log from Phase 2; ON only after S3 passes with zero wrong links (S3 controls: pre-locked keys, per-arm forked state, ratchet instrumentation, false-refusal/recall metrics) · (6) carried items: gate protocol amendment · experiment promotion rules (M2/M3 default OFF) · G1 display spec · OD-7 born-complete · the [PIN] set · reject auto in-context teaching · thresholds post-calibration · time/standard-keyed anchor revalidation as an owner RULE question · outage discipline (RETRY-age alarms, drain rate-limiter, catalog-frozen signal flag) · ADOPT takes the same 3-part confirmation as ATTACH.
- Never call the whole file ratified because the title says v3.4 or some OD rules were inserted.

### 8.2 XBRL-native materializer — CANDIDATE, dormant (live file at root until ratified; title says FINAL, status = pending)

- Text remains the only path that creates Drivers and narrative facts. The existing text-fact concept linker
  (FINAL_DESIGN §8) stays current.
- The candidate: deterministic code materializes entity-scoped numeric metric facts for already-admitted ACTIVE
  (company, driver)→concept resolutions. Covered facts need in-filing entity match, approved measurement fold,
  representable axes, allowed unit, exact period, source-stated value. Non-GAAP, unlinked, qualitative, causal,
  guidance, and action material stays text-side. **Unit whitelist v1: USD, shares, USD-per-share — eligible
  EPS/per-share facts ARE materialized (per-X in the name per NAME-13); every other unit skips + counts.**
- **The exact materializer recipe (candidate map — per Report (10-K/10-Q/10-K-A/10-Q-A) with
  `xbrl_status=COMPLETED`, per registrant with active resolutions):** 1. load ACTIVE `(company, driver)→qname` resolutions — full catalog records only,
  latents excluded [P4e] · 2. select Facts entity-scoped via `IN_CONTEXT→Context→FOR_COMPANY` (no edge → skip +
  count), filters `is_numeric='1'`/`is_nil='0'` [P4f] · 3. unit whitelist + map [P4c]: `iso4217:USD` → money on
  the driver's canonical scale · `shares` → count · `iso4217:USD/shares` → usd per-share level (EPS materialized,
  per-X in the name) · everything else (pure, other currencies, utr/custom, other divides) → skip + count
  (`pure`→percent ×100 is a fenced-out value rewrite) · 4. intra-filing dedupe + collision [P4g]: drop identical
  concept+context+value duplicates; within a fact_scope keep the highest-precision Fact when values agree within
  stated `decimals`; disagreement beyond precision → skip the WHOLE scope + log `xbrl_internal_conflict`, never
  fuse · 5. axes never dropped (FS-09): frozen table → `kind:normalized_member_label`; unknown axis → the hex
  sentinel; any NON_SLICE axis or HARD-EXCLUDE member → skip the whole fact, logged [P4d] · 6. period from the
  exact context (its own §5.3) · 7. id = `du:{R.source_id}:{d}:{fact_scope}` · 8. primary ⇔ the Fact's period end
  == `periodOfReport` (write always); everything else writes ONLY as backfill (no same-scope fact exists) or
  RESTATEMENT (canonical value differs) — identical-value re-tags skipped + counted; null `periodOfReport` →
  derive as max duration-period end among the report's own facts, else skip the report [P4b/P4h] · 9. write via
  `driver_writer`, atomic, all validators on, `level_shape_hint='point'` [P4i]; stamps: `origin=xbrl_link` ·
  `level_low=level_high` = the exact signed value scaled [P4a] · change/comparison/value_text/conditions/
  company_confirmed = FORBID (XBRL states levels only) · `driver_state=reported` · `quote=[XBRL] <qname> <period>
  = <scaled value>` · `measurement=∅` always [P3] · `date`=`R.created` (public filing time — PIT) ·
  `created`=write time · `source_type`=`10q`|`10k` · edges `OF_DRIVER`/`FROM_SOURCE`/`HAS_PERIOD`/
  `MAPS_TO_MEMBER`+`slice_part` (P7/P10 add provenance + `MAPS_TO_CONCEPT`/`xbrl_qname`).
- Materialize before text; text twins dedupe only on same event/head/period/slice/fold/value; mismatch splits
  or parks. Same-series exact XBRL wins ties; same-day 8-K remains; compatible upgrades via repair lane +
  auditable UpgradeEvent.
- **Non-numeric/TextBlock facts, dispositioned:** numeric XBRL is the ONLY materialization path. TextBlocks
  never create Drivers, DriverUpdates, slices, state, SAME_AS, or concept links; they may serve only as
  source-text aids (chunking experiments, read-time context packets, possible change-flag scanner input).
  TextBlocks-only extraction is forbidden; full section text remains the completeness baseline.
- Active/revoked ConceptResolution lifecycle, cohort exclusion, recovery/re-extraction, menu-evidence invariant,
  isolated kernel falsifier, duplicate/miss ledger. Honest non-repair lanes for divergent periods/slices remain.
- **The ratification pin map (P1-P17 and P19; no P18 — the source removed it). The LIVE candidate file
  `XBRLIntegrationDesign.md` remains the full text until ratification; this map is the ratification index:**
  - **P1** activate the `09 §10` rider items 1-4 as written (origin · `[XBRL]` quote · `reported` state · exact windows · member→slice · full-producer validators); **P1a** normal-order no-enrichment (a text twin is skipped whole; the xbrl node never gains prose).
  - **P2** rider item 5 closed: NO new stored rank slot; read-time tie-break addendum — within one event and one series, `origin=xbrl_link` beats `origin=llm` at collapse.
  - **P3** xbrl `measurement` always ∅; the DECLARED GAAP-family fold — {∅, gaap, reported, as_reported} ∪ the linked concept's own Basic/Diluted token — applied in the skip test AND as the rider-3 read bucket's extension (xbrl-side-only, value-gated, fixed token set; stored ids never change); basic never folds against diluted.
  - **P4** materialization: **a** value = as-tagged signed exact, canonical scale, decimals = precision-only · **b** primary ⇔ period end == `periodOfReport`; non-primary on new-scope-or-value-change · **c** unit whitelist {USD→money, shares→count, USD/shares→usd-per-share}; all else skip+count [exp enablement] · **d** SLICE_AXES + hex sentinel; NON_SLICE/elimination → skip whole fact · **e** latent bases excluded · **f** entity-scoping via `IN_CONTEXT→FOR_COMPANY`; no-context Facts skip; multi-registrant = per-registrant runs · **g** intra-filing collision (highest precision wins within rounding; beyond-rounding → skip + `xbrl_internal_conflict`) · **h** null-`periodOfReport` fallback (max duration end, else skip report) · **i** `level_shape_hint='point'` on every item · **j** falsifier (iv) runs over `origin≠xbrl_link` only · plus: no Q4 derivation, no auto-surprise, raw-duplicate dedupe, `is_numeric='1'`/`is_nil='0'`.
  - **P5 a** materialize-before-text per event; no-XBRL filings unsuppressed · **b** head-scoped skip, crossing SAME_AS edge ids recorded in the skip log · **c** value-compatibility gate: the text value matches the xbrl value within the text's own stated precision (half-ULP of its least significant digit, post-canonicalization); compatible → skip, logged with the deferred-to fact id + crossing edge ids · **d** `xbrl_conflict` STATE-BASED park (re-enqueues on revocation/edge-quarantine; TERMINAL only after graders re-confirm) + falsifier exhibit · **e** writer REJECT backstop `duplicate_of_xbrl`, same state-based keying. A QUARANTINED target driver → PARK-RETRY; CLAIM_FROZEN does NOT block materialization (the kernel blocks QUARANTINED only).
  - **P6** xbrl facts/resolutions excluded from BROAD/ESTABLISHED eligibility evidence (kernel §6.5 amendment).
  - **P7** provenance: `attach_mode='xbrl_link'` · `attached_via=resolution_id` · `xbrl_fact_id` (kernel V9/§10.1 wording).
  - **P8** `ConceptResolution` reified: `{resolution_id, company, driver, qname, method, model_id, menu_sha, date, state ∈ {active, revoked}}` — method/model_id/menu_sha are read by the risk-stratified re-verification and revocation graders to reproduce the original pick context · **a** revoke = 2 strong graders + RecoveryEvent + read-time cohort exclusion; enrichment consumes active only · **b** un-revoke at the same bar + counter-event · **c** gap repair triggered by revocation OR recorded-edge quarantine: parks re-enqueue + skip-log-bounded re-extraction · **d** the declared XC-09 judgment-exception for backfill eras, with era re-resolution.
  - **P9** strong-judge-tier FINAL VERIFY for materialization-grade resolutions — LOCKED per kernel §11.0 (only tier membership stays [exp] via PIPE-32); XC-16 + full-universe = hard pre-gate · **b** qualifier veto (adjusted/organic/pro-forma-class tokens in a candidate qname → refuse).
  - **P10** lane-matrix carve-outs, origin-gated: `xbrl_qname`/`MAPS_TO_CONCEPT` written at write time by this code producer only; `reported` legal on the metric lane for `origin=xbrl_link`.
  - **P11** reverse-order upgrade: **a** repair-grade in-place upgrade on value-compatible · **b** immutable `UpgradeEvent` with full prior payload; no prior_* fields · **c** writer validator: origin flip ⇔ exactly one event · **d** graded reversal: on 2-strong-grader confirmation, re-apply the UpgradeEvent's archived payload through the same repair lane, emitting a counter-event — lossless both directions, zero humans · **e** conflict → xbrl parks, the written fact stands · **f** fold-equivalent twins converge at read, not in storage.
  - **P12** resolution-on-create enqueues materialize(company, driver, all filings incl. current); text never waits.
  - **P13** `xbrl_twin_suspect{slice|period}` tripwire (measurement-diff EXCLUDED); `twin_suspect_rate` gates rollout [exp bar].
  - **P14** period pins: the shared deterministic scope classifier in the FACT-18 wrapper — quarter > Q1-YTD; ytd = FY-start-anchored; `half` = non-FY-start two-quarter; annual/ttm/monthly; else `exact_range`+WARN · **a** fiscal fields null-not-guessed · **b** sentinels illegal · **c** classifier + text-label resolution anchor on company-ACTUAL period ends (XBRL history / SEC cache first; month-math fallback) — the 52/53-week convergence rule · instants `period_scope=null` (the FACT-16.17 carve-out).
  - **P15** `effective_driver_state` read field: stored-if-stated; derived-if-`reported` with the comparator by DriverPeriod DATE ARITHMETIC (YoY ±7d for quarter/ytd; prior collapsed annual for annual); fallback `reported` on missing/ambiguous comparator; instants `reported` [exp]; never written back.
  - **P16** menus narrow, EVIDENCE creates (five-point structural enforcement: quote-required validator · FS-16 no-near-snap · the materializer's in-filing gate · PIPE-21 producers never see concept data · kernel blindness); never extend hints to values or scales.
  - **P17** prompt-narrowing = a cost experiment only; code-side suppression is the guarantee.
  - **P19** (renumbered; no reserved slots) the X-XL0-3 proofs + pre-gates + a fresh Neo4j census + industry-by-industry rollout are the enablement condition; all graph counts re-read at implementation.
- **The ten declared amendments to locked docs (all additive; zero reversals — ratified WITH the bundle):**
  (1) `12` FACT-16.17 instant `period_scope=null` carve-out · (2) kernel V9/§2/§10.1 `attach_mode` gains
  `xbrl_link`, `attached_via` gains resolution-ids, `xbrl_fact_id` added · (3) `12` FACT-16(3)/(4) origin-gated
  write-time `xbrl_qname`/`MAPS_TO_CONCEPT` + `reported` legality · (4) `09 §10` rider item 3 read-bucket token
  set extended to the P3 family, same fold in the write-side skip test · (5) kernel §6.5 eligibility-evidence
  exclusion · (6) `08` XC-05 qualifier veto; XC-18 ConceptResolution reification + revocation states · (7) `12`
  FACT-17b/18 period_scope classifier as the shared exact-date-branch authority · (8) kernel §9.1(iv) origin
  scoping · (9) `12` state-based park-class additions + CLI skip/no-enrichment rules + the UpgradeEvent writer
  validator · (10) `09 §6.9` intra-event origin tie-break addendum. Declared but not an amendment: the XC-09
  backfill-era judgment exception (P8d).
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
5. **Exact-block transfers — CLOSED (Phase 4 round 8):** kernel §15.0 MVP split + §16 residuals + the
   ratification bundle → §8.1 above; `12` §12's six acceptance gates incl. the F1-F9/P1-P8 fixture set → §5
   above; the XBRL materializer exact recipe + pins → §8.2 above. Prompt text: the XC PICK/VERIFY prompts and
   the classifier prompt content live in FINAL_DESIGN §8/§4.1 + §4 here; the hash-pinned experiment Plan/
   WorkOrder prompt packs stay live files until the experiment program migrates (their pins forbid edits).

## 12. Evidence worth keeping once

Fixed-vocabulary v1 rejected ~82% of useful names; eager-reuse v2 merged distinct demand stories — the two
deaths that justify open vocabulary + err-toward-separation. Units: 117/117 main + 29/29+7 guards + three 33/33
runs (components, not wiring). Concept links: 31-company proof — 0 wrong links/249 accepted, 0 wrong abstentions/
1,178, ~99.4% tail recall; 274-company validation — 100% sampled precision, ~70% recall, 98% three-run identity,
with an incomplete hand list and a known "one wrong" tuning caveat (keep the caveat beside the numbers).
