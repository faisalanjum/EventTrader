# BUILD_AND_OPERATIONS.md — how to build, test, run, and retire the Driver system

> **Status: LIVE — consolidation Phases 1-5 EXECUTED (owner GO 2026-07-16); the definitive reader test's outcome, per-question grades, and tested hashes live in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run10.md` — Phase 5 is COMPLETE ONLY IF that exact record shows 10/10 PASS.** This file owns PROCEDURE: build steps, contracts'
> mechanics, gates, run rules, and hazards. Rule MEANING lives only in `FINAL_DESIGN.md` (rule IDs referenced
> here, never restated). Public channel duties live only in `ChannelContract.md`. Status/history/supersessions
> live only in `STATUS_AND_HISTORY.md`. The 33 frozen sources are fully accounted for, byte-verified (29 originals + 3 snapshots archived; the
> byte-pinned Plan live at root) — evidence baseline = `archive/2026-07-15_pre-consolidation/MANIFEST.json`;
> audit trail = the archived `CONSOLIDATION.md`.
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
- **State (rounds 22-26 changes, 2026-07-16):** engine-prompt changes since the certified baseline — runtime
  archive reads removed + authority labels → FINAL_DESIGN §3 (round 22) · NAME-17 synced to OD-21 law in all
  three rulebooks (round 23; the pre-OD-21 "actual vs expected" form is gone) · drift guard
  (`workflows/tests/test_rulebook_sync.py`: gate==reconcile identical, menu_build prefix, OD-21 markers, all 19
  NAME headings, law-coupling anchors vs FINAL_DESIGN) · suite GREEN 2026-07-16: **265 passed + 1 skip**
  (root-runnable: `venv/bin/python3 -m pytest .claude/plans/Drivers/workflows/tests/ -q`); all three engine
  scripts parse clean harness-wrapped.
  **THE TRACK A IMPLEMENTATION GATE (owner-directed close-out, round 25 — replaces the round-24 recipe, which
  wrongly referenced `5db902f` baseline OUTPUTS that never existed; that certification was tests-only and
  WP-FC-RUN never ran):** before ANY Track A run, the implementing agent must (1) verify EVERY rule-bearing
  component — the three engine rulebooks, judge prompts, thresholds, model slots — against the THEN-CURRENT
  live design, and (2) pass a pinned current-law certification it defines and records at that time (suite green
  incl. the drift guard is necessary, never sufficient). The old Restaurant runs' RULE-BEARING outputs
  (menus, seed, catalog, decisions — anything produced under the superseded rules; `runs/2026-06-*`) are
  HISTORICAL EVIDENCE ONLY — never inputs, never baselines. Carve-out: their mechanical RAW-TEXT chunk copies
  (rule-independent source slices) remain legitimate pinned experiment inputs exactly where the WorkOrder
  already sanctions them (frozen-chunks source, copy-only + hash-verified, PIPE-33; WorkOrder §2.1/§3 step 3). Pending code cleanup, recorded not implemented:
  `gate.js` meta description still claims a default Restaurants seed the code removed (the code correctly
  throws without `args.candidates`).
- **State:** WP-FC-EDITS landed (`5db902f`, 2026-07-10; 260 tests + 1 skip): NAME rules inlined, dead leaf XBRL
  code removed, MF-02 + model slots + `min_score=0.60` at all four sites. Remaining: fold/tree prompt mirrors —
  re-verified on disk 2026-07-16 (pre-archive audit of WorkflowContextPack): the same fix classes are still open
  in the fold layer only — `fold_catalogs.js` (old-ontology prompt pointer `:84` + `model:'opus'` pins),
  `build_tree.js` (`model:'opus'` pins; its read-only `{list:true}` mode lacks the step-0 billing guard the
  fold/walk modes embed), `fold_catalogs.py` + the three fold tests (`optional_links` machinery/fixtures),
  `ab_pair_judge.js` (`model:'opus'` pins; its pair prompt is already MF-02-current), `validate_catalog.py:8`
  (stale docstring nit) — plus finalizer, hardening/recall floor, fixture rebuild, calibration leaf, first real
  two-industry fold, finalization, then the OD-6 fitness gate.
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
  surprise composition/home/tense (all OD-21 cases). **Ratified-XBRL amendments, DORMANT until the materializer
  enables (owner 2026-07-15):** instants take `period_scope=null` (the FACT-16.17 carve-out) · origin-gated
  write-time `xbrl_qname`/`MAPS_TO_CONCEPT` + `reported`-state legality for the xbrl producer only
  (FACT-16(3)/(4)) · the shared deterministic `period_scope` classifier as the FACT-17b/18 exact-date-branch
  authority · the state-based park classes `xbrl_conflict`/`duplicate_of_xbrl`/`xbrl_internal_conflict` + the
  CLI skip/no-enrichment rules + the UpgradeEvent writer validator (origin flip ⇔ exactly one event).
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

## 8. Ratified working designs (owner 2026-07-15; NOT activated) + unvetted proposals

> **🏛️ RATIFIED (owner, 2026-07-15):** the Admission Kernel v3.4 and XBRL Integration designs are APPROVED as
> the current WORKING DESIGNS — no longer pending candidates. **This approval does NOT authorize
> implementation, activation, or production use**: every experiment gate, dormant state, OFF switch, and
> unresolved item stays in force and marked. Their complete mechanics are being integrated into the four live
> documents — DONE (INT-2..INT-5 complete; per-element destination proof = STATUS §7.1b; the integration-era
> reader tests passed — the archive-gate run + the post-integration standard run; the DEFINITIVE post-move
> reader test = the Phase-5 gate — executed: outcome, per-question grades, and tested hashes live in the
> archive's `READER_TEST_RECORD_2026-07-16_phase5-final-run10.md`). Both originals are ARCHIVED (2026-07-15, byte-verified vs the Phase-1 manifest); the full
> operative mechanics live in §8.1/§8.2 below, with the archived originals as historical evidence.
> **Authority, three tiers (round 16 wording; both designs now ratified + archived):** `FINAL_DESIGN.md` owns
> CURRENT LAW · THIS guide's §8.1/§8.2 own the ratified designs' OPERATIVE MECHANICS (the archived originals'
> internal "topic docs win on conflict" lines resolve against FINAL_DESIGN as the topic docs' successor) ·
> archived files — including both design originals — are EVIDENCE ONLY, never authority. **Where this guide records a NAMED CORRECTION to an archived original (e.g. the graph-verified
> `10-K/A`/`10-Q/A` slash literals in §8.2), the correction OVERRIDES the original's text — corrections are
> part of the operative map, verified against ground truth, and traveled into the bundle at ratification.**
> **Reading rule for the split below:** where a name appears on BOTH sides (born-complete, recovery, CLAIM-off),
> the accepted side is the PRINCIPLE — already law in FINAL_DESIGN — while the design side is this kernel's
> specific IMPLEMENTATION of it (stages, arms, recipes, thresholds); the 2026-07-15 ratification approved the
> implementation, never re-opening the principle.

### 8.1 Admission Kernel v3.4 — APPROVED WORKING DESIGN (owner 2026-07-15; NOT activated; gates in force)

**Already-law pieces (carried in FINAL_DESIGN):** born-complete admission + first fact (§4.2) · cheap roles
never final-confirm (§1/§4.2) · OD-18 flagged-ATTACH confirmation incl. triggers (§5.4) · quarantine +
`disputed` recovery paths (§5.4) · OD-19 gate + permanent refusals (§5.4) · OD-20 continuity (§5.4). Everything
below is the ratified IMPLEMENTATION — gates and OFF-switches in force.

**8.1.1 Strategy (anchor-first, live-always):** D1 a head-focused machine-built gate-proven seed (stratified
leaves, default 3 companies/industry, X-S1-tuned; the never-run fitness gate must go GREEN before launch) · D2
live kernel from day 1 (exact ATTACH · code-verified ADOPT · the LINK mechanism · born-complete CREATE ·
fail-closed PARK) · D3 the async LINK trigger (event-driven + nightly) as backstop · D4 write-time-final signal
eligibility. The old leaf→industry→sector workflow = seed-builder, contingency deep-clean, component donor —
never a scheduled production backbone. Three amendments to the eight strategy answers: seed cards are NOT
auto-ESTABLISHED (gauntlet-earned); ESTABLISHED is skeptic-minted, never count-minted; cross-company signal
features key off BROAD, not ESTABLISHED.

**8.1.2 The decision flow.** INPUT per candidate (from the blind extraction pass): {proposed_name, quote,
evidence_atom, slice_tokens[], measurement_spans[], per_x, event_time}.
- **Stage 0 — deterministic intake (code, zero LLM):** `norm()` absorbs ALL typography (case/separators/
  whitespace/unicode) and NEVER plural/stem/acronym — that is meaning (the v1 line; plural convergence comes
  from canonical coining + sweep SAME_AS, plural handling experiment-gated OFF) → NAME-05 format check →
  banned-token lint (exact full-token, tiny frozen list) → terminal-suffix scan → collision probe over records
  ∪ variant nodes ∪ latent anchors → PIT retrieval (embed name+quote+scope; `visible_from` ≤ event date;
  cluster-deduped top-K; an exact-norm match is flagged EXACT in slot 1; badges ESTABLISHED / YOUNG /
  CLAIM_FROZEN / QUARANTINED) → build the G1 reuse view.
- **Stage 1 — the G2 router (ONE batched call per event, ≤400 records/≤300k chars; ATTACH/CLAIM discrimination
  is strong-judge-tier identity work per §8.1.11; CREATE/SKIP may run cheap where experiments prove no loss):**
  ATTACH(card) = EXACT card only, same cause + same causal scope + SAME MECHANISM confirmed from the card's
  evidence · ADOPT(card) = sorted-token-multiset reorder, code-verified → ATTACH · CLAIM(card) = different
  wording, same cause as a claim-eligible card → routes the pair to the LINK judge (the router only PROPOSES;
  the judge's input is code-assembled — producer rationale never reaches it) · CREATE = no surviving match,
  NAME-18(a-g), born-complete · SKIP = vague/not-reusable/single-event-bound · UNSURE = one strong-tier
  re-judge. Hard rules: never claim across flavors; never claim a QUARANTINED card; a homonym-quarantined exact
  name forces a more-specific re-coin; unsure → keep separate.
- **Stage 2 — arm execution:** ATTACH writes the fact to the exact-matched node (its own wording, always).
  CLAIM **[SHIPS OFF — shadow-log only until S3 passes]**: when ON, the LINK judge fires synchronously;
  APPROVED → ONE atomic tx (variant node created with fact_type copied from the head + `SAME_AS`→head edge +
  judge memo on the edge + the fact written TO THE VARIANT — union joins the head series at write time);
  REFUSED/timeout → fall through to CREATE, pair → the deferred ledger. CREATE: collision routing → stamping
  (OD-1 ×2 | DU-06 roots | C1→C2; live thin-evidence UNCLEAR → PARK-RETRY, never a default) → BASE_METRIC
  (PIPE-25) → atomic tx → indexed immediately → first fact flagged `new_driver=true` → pair enqueued to the
  suggester. SKIP/PARK: the park ledger.
- **Stage 3 — fact guards (the Track B writer, unchanged):** FACT-16 + the first-fact lane-exercise guard →
  write | park. **Provenance on every fact:** `attach_mode ∈ {exact, adopt, claim, create}` + `attached_via`
  (birth-id); seed/fold-built facts get lineage recorded at sync.
- **Async:** the LINK sweep (second trigger) + the immune system + edge-state recovery.
- **Storage ruling (owner ruling 3, carried):** NO `head_id` denormalization initially — reads use the locked
  one-hop union over committed `SAME_AS` edges; if ever added: same-tx invalidation + version-stamped
  derivations + a head-degree SLO watched from day 1.
- **The real-time guarantee (axiom C, scoped):** at write the fact sits on its own wording-node — final forever
  (ids immutable) — and is event-level signal-eligible immediately. Cross-wording SERIES membership completes
  synchronously only with CLAIM ON; with CLAIM OFF it completes asynchronously (minutes-to-nightly) by ADDING
  committed edges — additive, safe-direction latency (nothing wrong is asserted meanwhile; splits
  under-attribute). A later quarantine only REMOVES a link confirmed wrong. No written fact ever moves, re-keys,
  or waits on a cleanup job.

**8.1.3 G1 reuse display:** propose-first; Tier-0 exact probe + Tier-1 semantic top-K=10, cluster-deduped.
Cards show: name · fact_type · companies-count (tie-break only) · the ESTABLISHED/YOUNG/QUARANTINED badge ·
BASE_METRIC line · SAME_AS variants · ≤2 evidence quotes PIT-cut to `date ≤ event date`. NEVER shown: the full
catalog, facts/values, XBRL, latents/parked/quarantined-as-targets, scores, future text, hierarchy lanes.
Producer instruction (verbatim): "ATTACH only on an EXACT card whose evidence shows the same cause, scope, AND
mechanism. ADOPT trivial reorders. CLAIM a differently-worded claim-eligible card only when the evidence
supports same cause — a skeptic decides, and your reasoning is not forwarded to it. Never claim YOUNG (except
your own company's per-X causes), never claim QUARANTINED. When unsure, keep separate."

**8.1.4 Arms + parks:** ATTACH = exact-name only + the 3-part confirmation; a homonym verdict → more-specific
re-coin (one cycle) else PARK-TERMINAL. ADOPT = code-verified reorder only. CLAIM = at most ONE claim per
candidate per event; refused claims CREATE and defer the pair. **Park classes (exact):** RETRY
{`gate_unavailable`, `stamp_thin_evidence`, `base_unresolved`, `stamp_conflict`, `lane_unexercised`} — drains
on arrival; TERMINAL {`vague_skip`, `rule_reject`, `gate_rejected`} — counted + aged. Parks drain ONLY through
the full kernel; park rates are never model targets.

**8.1.5 Family policy:** ONE `stamp_fact_type()` (suffix → OD-1 gate ×2 → DU-06 roots → C1 → C2; live UNCLEAR
parks, never defaults) and ONE `resolve_base_metric()` (PIPE-25 order; OD-1 latent rules; the proven-metric F2
gate), shared by seed finalize AND live admission. CLAIM-approved variants copy the head's fact_type — stamped
only AFTER judge approval (a refused claim takes full CREATE stamping). Latent graduation exact-norm only;
stamp conflicts park; `visible_from = min(existing, new evidence date)`; batch imports treat live nodes as
PROTECTED.

**8.1.6 The LINK mechanism — one judge, two triggers.**
- **Pair assembly (code, no producer advocacy):** side A = the proposal/new node's name + quote(s) + slice
  tokens + per_x + industry tag; side B = the target head's FROZEN definitional anchor + industry tag.
- **Auto-refusals (code, pre-judge), each classified for repairability:** PERMANENT-BY-LOCKED-RULE (re-opening
  one is an owner RULE question): cross-flavor · terminal-suffix mismatch · per-X mismatch · portion-qualifier
  supersets (current_rpo vs rpo) ALWAYS different. GATED: the token-subset species (brent_oil_price vs
  oil_price) moves to judge-territory once OD-19's K-pairs.v2 gate passes wrong-same=0; until then auto-refused.
  STATE-BASED (auto-re-enqueued when the state clears): target not claim-eligible · either side
  QUARANTINED/flagged. JUDGE-TERRITORY: sibling named-series pairs (Brent vs WTI, SOFR vs fed_funds — code
  cannot know two benchmarks are distinct without a curated list, the v1 pattern) → the judge's check-1 with a
  dedicated fixture family.
- **THE JUDGE (strong tier, default survives=false, code-assembled input only) — 5 checks, ALL must hold, each
  quoting both sides:** (1) same OBJECT — CO-EXTENSIVE, never hyponym: a narrower species of the other's object
  (iphone⊂smartphone, brent⊂oil) → REFUSE; breadth may only emerge from the SAME name recurring, never
  absorption. (2) same SCOPE — business population AND referent ownership class {own-entity-internal ·
  external-market · counterparty}: a firm-realized quantity is never the external variable driving it
  (fx_headwind ≠ dollar_strength). (3) same MECHANISM — same measured quantity at the same causal position:
  upstream/downstream/correlated on one chain → REFUSE (energy_costs ≠ oil_price); the financial transmission
  channel to equity must match; same-flavor cross-industry homonyms refuse here (telecom churn ≠ deposit churn).
  (4) NO RIVAL — with ≥2 claim-eligible cards above threshold, the judge sees the top rival and REFUSES unless
  the quote uniquely discriminates ONE target. (5) the head's own anchor is MONO-mechanism — an anchor spanning
  mechanisms → REFUSE + flag.
- **HIGH-BLAST second skeptic:** a link onto a head spanning ≥8 companies gets a SECOND independent lens-split
  (object/scope/mechanism) AND-voted skeptic on a disjoint evidence view.
- **Apply (code):** `SAME_AS` variant→head + memo {trigger, judge model id, date, anchor hash, verdict quotes};
  head election: ESTABLISHED beats YOUNG, then earlier `visible_from`, then lexicographic; star-flatten;
  D1-traceable. **Cache:** refuted pairs cached; re-judged only when either side gains ≥1 distinct company;
  approved links never LOOSENED automatically — tightening (quarantine) is the recovery path.
- **Two triggers:** synchronous CLAIM (ships OFF; shadow-log from Phase 2 — the judge fires and the would-be
  edge + verdict log in strict admission order against PIT catalog state, nothing written; ON only after S3
  passes with ZERO wrong links; one confirmed wrong production link flips it OFF again) · the async SWEEP:
  on-create enqueue to the suggester (embeddings top_k=5 min_score=0.60 ∪ token-overlap ∪ rare-token — suggest,
  never decide); corroborated pairs judged immediately; fresh single-quote thin pairs → the DEFERRED-PAIR
  LEDGER, auto-re-judged on evidence growth; batch passes event-driven keyed to the earnings calendar /
  CREATE-burst detector, nightly as backstop.
- **Deferred-ledger hygiene:** a claim against a falsifier-flagged head parks as `deferred(head_flagged)` — no
  node minted (a false flag must not cause a duplicate storm); recovery resolution RE-ENQUEUES every pair
  deferred against that head immediately. Deferred pairs age → after N periods a TERMINAL-defer class —
  counted, reported, re-openable on any evidence growth.
- **The frozen definitional anchor (the anti-ratchet):** every card carries `definitional_evidence` with an
  immutable `birth_quotes` sub-field — seed cards: the build-stack evidence draw + slice tokens; live cards:
  the RAW quotes from the first qualifying events — never an LLM distillation. Every judge and audit judges
  against THIS anchor only; the drift probe pins to `birth_quotes` forever. Claim-attached quotes are
  display-only. The anchor accumulates a frozen REFUTED-NEGATIVE set (refused pairs sharpen what the card is
  NOT). Anchor ENRICHMENT is experiment-gated, default OFF. Anchor RE-FREEZE: when recovery graders confirm an
  anchor quote itself was mis-attributed, the anchor is RE-DRAWN from the next clean qualifying events in one
  RecoveryEvent-audited step — re-drawn, never distilled.
- **Union-preview:** suggested-but-unjudged pairs are consumed ABSTAIN-ONLY — they may suppress a
  "this signal is narrow" conclusion, never assert a merged signal.
- **Claim-eligibility + establishment:** `BROAD(card)` ⇔ evidence from ≥K distinct companies (K=2 default,
  X-S4) — a pure code count used only for cross-company signal features. `ESTABLISHED(card)` (=claim-eligible)
  ⇔ SKEPTIC-MINTED: crossed an eligibility floor (BROAD, or seed-built + gauntlet-passed) AND passed a ONE-TIME
  mono-mechanism coherence check by the LINK judge over its accumulated evidence (default-suspect); fails →
  stays YOUNG + flagged. Single-company causes: a claim may target a YOUNG card iff same company AND same per_x
  AND entity-bound family (a company converging its own wordings); macro/standard-KPI families require BROAD.
  "Distinct event" everywhere = a distinct primary filing/earnings event (accession-level), never news
  re-quotes. REJECTED as gate inputs: source-quality ranks and LLM-graded quote clarity. **Eligibility is read
  LIVE, in-tx:** `claim_eligible = ESTABLISHED ∧ ¬falsifier_flagged ∧ ¬quarantined ∧ ¬CLAIM_FROZEN`, re-checked
  inside the commit transaction with an edge-set version bump (a stale retrieval badge can never authorize a
  claim). CLAIM_FROZEN = the de-mint state: a formerly-established card whose evidence turns incoherent loses
  claim-eligibility while its existing edges route to per-edge adjudication. (XBRL amendment 5, dormant with
  the materializer: `origin=xbrl_link` facts/resolutions never count toward BROAD/ESTABLISHED eligibility.)
- **The split-reconciliation lane (recall's governed exit, mirroring quarantine):** frozen anchors + cached
  refusals could make two valid synonyms refuse each other forever; so periodically (and on TERMINAL-defer
  aging) mutual-refusal and long-deferred pairs where BOTH sides are now evidence-rich are re-judged by the
  BATCH-GRADE process — full evidence on both sides, lens-split skeptic, high-blast rules — never the
  frozen-anchor fast judge. Two regimes matched to their information: frozen anchors govern thin-evidence live
  claims (anti-ratchet); full-evidence batch-grade judgment governs mature-pair reconciliation
  (anti-permanent-split). Reconciliation approvals are ordinary reversible `SAME_AS` links with memos;
  false-refusal rate and time-to-reconcile are first-class metrics.

**8.1.7 Validators V1-V14 (all code, zero LLM, hard-fail):** V1 format/lint · V2 link legality (claims only on
claim-eligible targets; auto-refusal classes enforced pre-judge; ADOPT reorder-only) · V3 OD-1 memo
completeness · V4 exactly-one BASE_METRIC on a proven-metric target · V5 suffix⇔fact_type · V6 latent sanity ·
V7 create-collision invariants · V8 admission atomicity + ON-CREATE-only fact_type · V9 fact-side (FACT-16 +
lane-exercise) + attach_mode/attached_via provenance present on every fact (XBRL amendment 2, dormant with the
materializer: `attach_mode` gains `xbrl_link`, `attached_via` gains resolution-ids, `xbrl_fact_id` added) · V10 park-ledger integrity · V11
link-side (memo'd, D1-traceable, deterministic head election/star-flatten, refuted-cache respected) · V12
variant rules (copied fact_type + memo + edge in one tx; variants never claim targets) · V13 anchor integrity
(`definitional_evidence` frozen at establishment, hash-pinned, never rewritten; judge inputs assembled from it
verbatim) · V14 recovery integrity (quarantine is edge-state only, plus the two reversible recovery-lane
booleans — fact `disputed`, `ContinuationClaim.quarantined` — set only by the recovery machinery; no mutation
of fact identity/content, no deletion; every recovery emits a RecoveryEvent).

**8.1.8 Phases, the seed gauntlet, eligibility, contingency:**
- Sequence: Phase 0 stale-trap fixes + FINALIZE build → Phase 1 SEED (stratified leaves → folds → finalize →
  validate --final → GAUNTLET → fitness gate GREEN → graph sync) → Phase 2 shadow burn-in → Phase 3 production
  with priority backfill → forever: the async LINK trigger + the immune system + quarterly fresh-key gate
  re-runs.
- The seed: the head of every industry's vocabulary through the full defense stack; sizing X-S1 (default 3
  companies/industry); by-products = keys, fixtures, the gate's frozen catalog.
- **The gauntlet (pre-sync, zero-tolerance). Layer A — static (code + ONE strong-model pass):** S-A1
  single-token scan (forced through S-A4 + homonym adjudication before any standing) · S-A2 bare NAME-16
  category scan (hard-fail) · S-A3 brand/measurement/ticker/period/direction token scan vs a gazetteer
  (hard-fail — the `taco_bell_same_store_sales`/`adjusted_eps` prompt-drift classes, deterministically) · S-A4
  mechanism-spread audit (embed each card's own evidence; internal dispersion ≥2 clusters flags; embeddings
  flag, a strong model adjudicates) · S-A5 gravity-well scan (retrieval-neighbors of many distinct causes) ·
  S-A6 suffix-blind fact_type/BASE_METRIC re-derivation (a strong model re-derives from evidence IGNORING the
  suffix; disagreement on any `_guidance`/`_surprise` card = hard fail). **Layer B — dynamic probes (crafted
  candidates through the live kernel against the frozen seed; meaning-graded, 2-grader, zero merge tolerance):**
  P1 three-demand-stories (three different demand mechanisms must yield three creates) · P2
  metric/guidance/surprise routing + family edges · P3 own-segment vs external cause · P4 measurement words
  route to the slot, never an `adjusted_*` card · P5 the per-X trio · P6 brand/geo slice traps · P7
  same-words-different-mechanism homonym pairs (any double-accept quarantines the card) · P8 genus-species
  traps (species candidates at a genus card must CREATE) · P9 benchmark identity (Brent/WTI/generic).
  **Pass bar:** zero S-A2/A3/A6 hits; every S-A1/A4/A5 flag adjudicated clean or the card quarantined from the
  seed; zero wrong convergences across P1-P9. Seed cards earn ESTABLISHED only by passing; unprovable cards
  ship YOUNG. Failure → bootstrap-time D4 out-of-band fix → FULL gauntlet re-run; no partial sync.
- Signal eligibility: write-time-final, deterministic; every written fact immediately event-signal-eligible;
  `new_driver` flags empty-history-by-construction; cross-company/history-weighted features key off BROAD;
  parked invisible; quarantined never; signal-quarantine pauses history-weighted features on detector-fired
  links pending confirmation (event-level reads unaffected).
- Contingency ladder: judge/cadence/suggester escalations → claim-flag OFF (trigger-2-only, zero redesign) →
  partial batch rebuilds (live nodes PROTECTED) → full Track A build.

**8.1.9 The immune system (the anti-"looks clean while corrupting" layer).** Principle: every detector uses NO
model, a DIFFERENT information channel than the decision's, or measures the graders themselves. **Smoke-alarm
doctrine:** code surfaces form-level contradictions and takes exactly ONE automatic action — the reversible
signal-quarantine; code never concludes "different causes" (that verdict belongs to the recovery graders, who
receive RAW FACTS only — never the falsifier's conclusion or framing; a shared code-derived prior would
collapse two graders into one).
- **The model-free merge FALSIFIER (deterministic graph queries, ~free):** (i) one head whose SAME-COMPANY
  facts map to ≥2 distinct XBRL concepts or inconsistent dimensional members (cross-company multi-concept is
  NORMAL; flagged only as an industry-partitioned concept split — the cross-industry-homonym signature) ·
  (ii) co-occurring same-company same-fiscal-normalized-period same-scope members with OPPOSITE numeric
  directions — suspicion only · (iii) two differently-named heads repeatedly sharing company+period+XBRL-concept
  — the duplicate oracle, independent of the embedding suggester · (iv) periodicity coherence: a metric-stamped
  head whose per-company facts never recur across periods behaves like a mistyped one-off · (v) company-set ×
  event-time co-occurrence — the XBRL-free DUPLICATE channel for qualitative space (high company-Jaccard +
  tight temporal co-occurrence; 8-K item-code family sets as abstain-only evidence, fail-OPEN when absent) ·
  (vi) bimodal post-event return signatures — abstain-only audit priority · (vii) live suffix-blind
  re-derivation as a SAMPLED ops lane (disagreement = raw-evidence exhibit → recovery). Runs offline over
  stored facts. Every flag → recovery as raw evidence; features gate on `BROAD ∧ ¬falsifier_flagged ∧
  ¬homonym_suspect ∧ ¬CLAIM_FROZEN`. (Ratified-XBRL amendment 8, dormant: detector (iv) periodicity is scoped
  to `origin≠xbrl_link`.)
- The ATTACH-channel audit (triggers/flow already law — FINAL_DESIGN §5.4) with its P7 counters: flag rate ·
  refuse rate · escalation-disagreement rate · re-coin-failure rate; the post-write sampled audit continues.
- Transitive-drift probe: per established head per period, EARLIEST anchor quote vs LATEST attached quote as a
  hypothetical fresh pair; refusal = drift → freeze claims + recovery; plus a deterministic centroid-drift
  alarm on the frozen-anchor embedding vs newest members.
- Evidence-dispersion re-cluster: S-A4 run continuously on live heads; bifurcation into ≥2 stable mechanism
  clusters = homonym tripwire.
- Risk-stratified audits + honest bounds: the audit budget concentrates on structurally risky cases
  (cross-industry, homonym-shaped names, just-crossed-K thin sides, high-connectivity heads —
  blast-radius-weighted toward 100%); dashboards publish the statistical UPPER BOUND (0 wrong in n ⇒ ≤3/n at
  95%) × live population against a permanent-error budget; a published "0 wrong in n" bounds the
  flagged/audited strata ONLY — the unflagged stratum is bounded pre-launch (gauntlet + fixture families + one
  pre-registered unflagged sample) and monitored by the detectors.
- Planted calibration stream + grader-independence measurement: a permanent stream of known-answer
  surface-similar pairs (bookings/billings · adjusted-vs-GAAP EBITDA · gross/net · segment/consolidated ·
  deferred/recognized revenue) through the live judge AND both graders — in a tagged SHADOW namespace, never
  admissible to the live graph. The shared-miss rate quantifies generation-level blindness (measured and
  reported, NEVER auto-applied as a gate discount — owner decision); a suspiciously LOW grader-disagreement
  rate is itself an alarm. The stream also injects known-SYNONYM pairs at the suggester (retrieval-recall
  decay watch); suggester tuning faces a JOINT promotion bar (planted-synonym recall AND false-merge rate).
  Honest limitation: all in-session judges are one vendor's models — the falsifier is the only fully
  independent channel, which is why it is a launch blocker.
- Flow metrics: per-head fan-in rate + evidence-spread trend (fan-in, not sweep_link_ratio, is the gravity-well
  detector) · duplicate_half_life SLO · claim_refusal_rate · park drain age.
- **Launch blockers: detectors (1) and (2) must exist before Phase 3.**

**8.1.10 Edge-state recovery (automatic, no-human, reversible) — full mechanics:** (1) immutable write-time
provenance (attach_mode + attached_via; link memos + anchor hashes; frozen anchors) · (2) detect →
signal-quarantine (pauses history-weighted features through the link; event-level reads untouched) · (3)
confirm: two independent blind strong graders must confirm "different cause" citing evidence; unresolved → one
blind re-grade; still split → INCONCLUSIVE: the signal-quarantine stays, the case becomes a calibration-stream
fixture, and the CLASS goes to the owner as a RULE question — never a silent keep · (4) quarantine = the only
write: `quarantined=true` on the SAME_AS edge, never deleted, one edge-flip tx; the variant reverts to a
standalone driver (revert is a STATE: in-flight facts PARK-RETRY(`variant_reverting`); recoveries serialize per
SAME_AS component). A confirmed homonym NODE gets the `homonym_quarantined` badge — never claim-eligible,
excluded from cross-company features; future exact proposals router-forced to more-specific re-coins; existing
facts stay as flagged history. Propagation: homonym-quarantining a head with variants signal-quarantines ALL
its variant edges → per-edge two-grader adjudication; quarantining a BASE signal-quarantines its
BASE_METRIC-derived members pending re-resolution to a clean base, else they revert standalone; the tx re-keys
or drops latent anchors keyed to the quarantined exact-norm name (no permanently ungraduatable latents) · (5)
audit + regate: every recovery emits an immutable RecoveryEvent (detector, both grader memos, frozen evidence
snapshot, edge/node ids); the case joins the regression fixtures; remediation may DISABLE a claim-class
immediately (reversible) but a model/prompt change only lands through the locked A/B gate · (6) wrong
quarantine = an over-split: reversible — the pair re-enters the suggester once either side grows, re-judged
with the quarantine memo in view; un-quarantine is the same one-flip tx · (7) D4 scoping (ratified `95` #39):
absolute against automatic LOOSENING; automatic TIGHTENING enabled for ALL link origins, seed-built links
require a THIRD grader · (8) fact-level `disputed` (already law — FINAL_DESIGN §5.4).

**8.1.11 Model tiers (§11.0 — LOCKED rule, owner 2026-07-07):** any second-check or confirmation that can
change Driver identity, family/type, `SAME_AS` state, `BASE_METRIC`, claim-eligibility, quarantine state, seed
standing, or fact placement (incl. flagged exact-ATTACH) MUST be strong-judge tier; cheap models may propose/
extract/route/draft but NEVER final-confirm a permanent identity decision. Three tiers by ROLE (never a
hard-coded model name): cheap producer · strong judge · exceptional/fallback. The RULE is locked; tier
MEMBERSHIP is experiment-gated via the locked A/B gate + pinned model IDs. Current owner defaults (2026-07-08,
survive only if experiments show no loss): Haiku-class as the blind leaf producer; Sonnet 5 as the strong-judge
candidate (G2, Refute, LINK judging, BASE_METRIC/fact_type confirmations, quarantine confirmation,
establishment-minting, gauntlet adjudication, every recovery grader); Opus 4.8 / GPT-5.5 / Fable as escalation.
One LINK judge (absorbs the reuse-skeptic/sweep-judge roles; lens-split high-blast variant). **The ROUTER's
promotion bar adds claim-precision/recall AND zero wrong-ATTACH on the cross-industry fixture family;
establishment-minting checks and gauntlet adjudications use the judge tier.** **Principles
P1-P7 (unchanged):** structure over model strength · diversity over repetition · cheap-first with zero-loss
promotion · strong-by-default on permanent classes · structural escalation only · pinned IDs + canary ·
park/skip rates never targets. Graders' independence is measured, never assumed. **The falsifier and ALL §8.1.9 pre-filters are CODE — no
model ever.** Billing: subscription workflow agents + step-0 guards; SDK banned; embeddings remain the one
metered, suggest-only lane.

**8.1.12 Kernel experiments (designed, NOT run — gates in force):** S1 seed-size knee · S2 three-world
shootout · S3 synchronous-vs-async LINK trigger (zero wrong-link tolerance; must instrument the RATCHET —
head-meaning drift across sequential approvals vs the frozen anchor) · S4 K + eligibility floors · ladders
X0-X9 (X0 fixtures: genus-species, benchmark siblings, cause-vs-consequence, transmission-channel homonyms,
ownership-axis pairs, no-rival ambiguity, calibration pairs) · X-G the gauntlet itself (a launch gate) · X-IM
immune-system proofs (each detector must catch its seeded corruption class; each validator has a failing
mutation test; a seeded mis-attach must end `disputed=true`) · X-C chunking granularity (paragraph-at-a-time
leaf inputs — an experiment, never a locked prompt shape).

**8.1.13 Reject-conditions (what would flip pieces OFF after testing):** any confirmed wrong synchronous link
S3 shows the async path avoided → CLAIM flag OFF · a shared-miss rate the falsifier cannot compensate →
judge-tier escalation via the A/B gate, else the claim class disables and the owner is told the honest limit ·
the gauntlet failing to reach zero on P1/P7/P8 after two remediation rounds → the seed ships YOUNG-only · a
falsifier fire-rate above the permanent-error budget in shadow → Phase 3 blocked, contingency ladder ·
X-S1 showing no coverage knee → re-open the D1 seed strategy WITH THE OWNER · batch/live equivalence
divergence (X8) → fork bug, build stops.
**Rejected alternatives (terse, load-bearing):** attach-to-head physicalization (irreversible wrong merges) ·
physical fact replay as recovery · count-minted establishment + persistence lanes (echo-maturity) ·
"seed-built ⇒ ESTABLISHED" (born-fat gravity) · CLAIM-off as PERMANENT posture (it must EARN ON through S3) ·
LLM-distilled card definitions (re-broadening) · union-preview as signal input (abstain-only) · plus the
carried v1/v2 rejections: closed vocabulary, unguarded semantic reuse, hand-seeded vocabulary, alias caches,
morphology in code, self-declared-confidence routing, LLM validators, threshold-decided admissions,
full-catalog display.
- **Kernel §15.0 MVP split (transferred whole — the exact first-build fence):**
  - Day-1 core: kernel Stages 0-3 (ATTACH+confirm · ADOPT · CREATE born-complete · SKIP/PARK) · async LINK trigger + deferred-pair ledger with no-mint-on-flagged-head · frozen birth anchors · evidence-mass gate + skeptic-minted ESTABLISHED (cannot defer: the day-1 sweep's eligibility rule depends on it) + BROAD split · validators V1-V14 · falsifier signals (i)(ii)(iii)+(vii) + ATTACH-audit · minimal calibration stream · recovery core (quarantine + variant/family propagation + RecoveryEvent) · seed + gauntlet static scans (S-A2/A3/A6) · park/outage discipline. **Coverage rule:** if the MVP admits no-XBRL (news/qualitative/action) drivers, falsifier (v) ships day-1; otherwise admission is FENCED to XBRL-backed sources until (v) ships — the qualitative space is never live-and-uninstrumented.
  - Deferred (flag/experiment-gated, inert until enabled): CLAIM-ON (S3) · anchor enrichment M2 · item-codes M3 · UNSURE valve · union-preview · falsifier (iv)(vi) · full dynamic gauntlet P1-P9 if the owner ships the seed YOUNG-only · transitive-drift cadence beyond quarterly · exotic-latent propagation · head-degree sharding · time-keyed anchor revalidation · sampled-audit rate tuning · type-CORRECTION lane (recall optimization; parking covers safety).
- **Kernel §16 honest residuals (transferred whole):** the irreducible floor = a single-shot hardened judge wrong on a genuinely co-extensive-looking pair at FIRST encounter, before any falsifier signal — measured by OD-6, reversible by recovery once evidence accumulates (zero-by-construction impossible; zero-by-measurement with honest upper bounds is the promise) · homonym facts written before detection stay on the quarantined node as flagged history — contained, never erased, excluded from features · all in-session judges share one model vendor; the falsifier is the only fully independent oracle · **qualitative homonyms have no model-independent tripwire** (for no-XBRL non-numeric heads, falsifier channels (i)-(iv) are silent and (v) detects duplicates, not one-name-two-meanings; only drift/dispersion probes and audits watch; the quarterly held-out gate re-runs are the backstop — the stated deepest worry) · history completeness is the ambition's success metric (duplicate half-life + reconciliation efficacy + park drain + false-refusal rate as a first-class dashboard number) · conservative splits and deferred thin pairs under-attribute during their window — the safe direction, visible in metrics.
- **The ratification bundle (RATIFIED by the owner 2026-07-15 — the six items below are what was approved; activation remains gated by the experiments and launch blockers):** (1) the v3.2 architecture (variant-anchored storage · one LINK mechanism/two triggers · frozen birth anchors + split-reconciliation lane · skeptic-minted establishment with CLAIM_FROZEN de-mint) · (2) edge-state recovery + D4 scoping (automatic tightening-only quarantine for all links, 2-grader confirmed on RAW EVIDENCE with no falsifier framing, 3-grader for seed links; INCONCLUSIVE escalates the RULE, not the case) · (3) the seed gauntlet as a launch gate incl. seed cards earning ESTABLISHED (unprovable → YOUNG) · (4) launch blockers: corrected model-free falsifier + ATTACH audit before production writes; flagged-head audit intensity bounded — 100% for the first N/T, then risk-stratified — with a hard SLA that never hangs on the owner queue · (5) CLAIM ships OFF; shadow-log from Phase 2; ON only after S3 passes with zero wrong links (S3 controls: pre-locked keys, per-arm forked state, ratchet instrumentation, false-refusal/recall metrics) · (6) carried items: gate protocol amendment · experiment promotion rules (M2/M3 default OFF) · G1 display spec · OD-7 born-complete · the [PIN] set · reject auto in-context teaching · thresholds post-calibration · time/standard-keyed anchor revalidation as an owner RULE question · outage discipline (RETRY-age alarms, drain rate-limiter, catalog-frozen signal flag) · ADOPT takes the same 3-part confirmation as ATTACH.
- The design IS now ratified (owner 2026-07-15) — as a WORKING DESIGN only; nothing above is activated, and
  every experiment gate (S1-S4, X0-X9, X-G, X-IM), the CLAIM-OFF posture, the launch blockers, and the
  reject-conditions remain binding exactly as written.

### 8.2 XBRL-native materializer — APPROVED WORKING DESIGN (owner 2026-07-15; DORMANT until the P19 enablement condition + experiment gates; NOT activated)

- Text remains the only path that creates Drivers and narrative facts. The existing text-fact concept linker
  (FINAL_DESIGN §8) stays current.
- The ratified design (DORMANT): deterministic code materializes entity-scoped numeric metric facts for already-admitted ACTIVE
  (company, driver)→concept resolutions. Covered facts need in-filing entity match, approved measurement fold,
  representable axes, allowed unit, exact period, source-stated value. Non-GAAP, unlinked, qualitative, causal,
  guidance, and action material stays text-side. **Unit whitelist v1: USD, shares, USD-per-share — eligible
  EPS/per-share facts ARE materialized (per-X in the name per NAME-13); every other unit skips + counts.**
- **The exact materializer recipe (the materialization map — per Report with `xbrl_status=COMPLETED`, per registrant with
  active resolutions). Filing-type filter, GRAPH-VERIFIED LITERALS (Neo4j census 2026-07-15): `formType` ∈
  {`10-K`, `10-Q`, `10-K/A`, `10-Q/A`} — the amended forms use a SLASH (137× `10-K/A`, 41× `10-Q/A` live); the
  archived original's "10-K-A/10-Q-A" notation is prose shorthand — matching it literally would silently skip
  every amended filing:** 1. load ACTIVE `(company, driver)→qname` resolutions — full catalog records only,
  latents excluded [P4e] · 2. select Facts entity-scoped via `IN_CONTEXT→Context→FOR_COMPANY` (no edge → skip +
  count), filters `is_numeric='1'`/`is_nil='0'` [P4f] · 3. unit whitelist + map [P4c]: `iso4217:USD` → money on
  the driver's canonical scale · `shares` → count · `iso4217:USD/shares` → usd per-share level (EPS materialized,
  per-X in the name) · everything else (pure, other currencies, utr/custom, other divides) → skip + count
  (`pure`→percent ×100 is a fenced-out value rewrite) · 4. intra-filing dedupe + collision [P4g]: drop identical
  concept+context+value duplicates; within a fact_scope keep the highest-precision Fact when values agree within
  stated `decimals`; disagreement beyond precision → the WHOLE scope is NOT materialized and is recorded under
  the STATE-BASED park class `xbrl_internal_conflict` (fail-closed; never fuse, never last-write-wins). **RETRY
  TRIGGER — OWNER-RULED 2026-07-15 (round 16): retry ONLY when the affected report's parsed XBRL facts actually
  change; an amended filing is processed as a NEW report — it never silently rewrites the old filing.**
  (History: the source registered the class as state-based without naming its clearing state; round-14's
  proposed reading was refined into this ruling.) · 5. axes never dropped (FS-09): frozen table → `kind:normalized_member_label`; unknown axis → the hex
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
- **The pin map (P1-P17 and P19; no P18 — the source removed it). RATIFIED 2026-07-15 and the original
  archived: this map + the recipe above ARE the operative mechanics; the archived original is historical
  evidence only:**
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
  - **P13** the `xbrl_twin_suspect{slice|period}` tripwire — exact trigger, at TEXT-write time: same event + same head + value-compatible level + exactly ONE scope component differs (slice OR period; a measurement diff is EXCLUDED — a non-folding measurement is a legitimately different fact) → log `xbrl_twin_suspect{component}` with both ids; no park, no snap, no id change. It makes the silent over-split channels measurable, GATES rollout (`twin_suspect_rate` is an acceptance metric, bar pre-registered from X-XL2), and feeds the offline re-vet + the falsifier's exhibit stream.
  - **P14** period pins: the shared deterministic scope classifier in the FACT-18 wrapper — quarter > Q1-YTD; ytd = FY-start-anchored; `half` = non-FY-start two-quarter; annual/ttm/monthly; else `exact_range`+WARN · **a** fiscal fields null-not-guessed · **b** sentinels illegal · **c** classifier + text-label resolution anchor on company-ACTUAL period ends (XBRL history / SEC cache first; month-math fallback) — the 52/53-week convergence rule · instants `period_scope=null` (the FACT-16.17 carve-out).
  - **P15** `effective_driver_state` read field: stored-if-stated; derived-if-`reported` with the comparator by DriverPeriod DATE ARITHMETIC (YoY ±7d for quarter/ytd; prior collapsed annual for annual); fallback `reported` on missing/ambiguous comparator; instants `reported` [exp]; never written back.
  - **P16** menus narrow, EVIDENCE creates (five-point structural enforcement: quote-required validator · FS-16 no-near-snap · the materializer's in-filing gate · PIPE-21 producers never see concept data · kernel blindness); never extend hints to values or scales.
  - **P17** prompt-narrowing = a cost experiment only; code-side suppression is the guarantee.
  - **P19** (renumbered; no reserved slots) the proof plan below + pre-gates + a fresh Neo4j census + industry-by-industry rollout are the enablement condition; all graph counts re-read at implementation.
- **The enablement PROOF PLAN (exact bars — before any live enablement):**
  - **X-XL0 determinism:** code-diff every materialized DriverUpdate against its SURVIVING source Fact (value/scale, period dates, members→slice, unit, concept, entity). **Bar: 100%.** Required fixtures: a multi-registrant filing · a null-`periodOfReport` report · an intra-filing precision-duplicate pair · a 52/53-week filer.
  - **X-XL1 twin fidelity:** N (company, driver, period) triples with both a text and an xbrl fact — value agreement + period-window id-equality rate, every divergence classified. **Bar: ≥99% id equality on true twins**; 52/53-week filers mandatory in-sample.
  - **X-XL2 suppression + tripwire calibration:** suppression ON vs OFF over M 10-Qs — skip precision (**zero suppressed non-twins, hard zero**), `duplicate_of_xbrl`≈0, the `xbrl_conflict`/`xbrl_internal_conflict` census, `twin_suspect_rate` measured; **the rollout bar is PRE-REGISTERED from this run.**
  - **X-XL3 recall:** a pre-registered sha-locked key (the PIPE-37/OD-6 protocol) over K filings; (xbrl ∪ suppressed-text) coverage ≥ the text-only baseline; **zero market-moving fact lost — hard zero.**
  - **X-XL4 cost:** tokens/filing + backfill, hybrid vs text-only — INFORMATIONAL ONLY, never gating; the results are REPORTED TO THE OWNER.
  - **Hard pre-gates (locked, load-bearing):** XC-16 + the full-universe concept run · the PIT menu proof · a falsifier-(iii) dry-run over a materialized sample · the FRESH Neo4j census (counts, `FACT_MEMBER`/`FACT_DIMENSION` edge wiring, unit-type inventory, no-context and null-`periodOfReport` cohort sizes).
  - **Rollout:** flag-on, ONE industry → industry-by-industry; each promotion gated on the X-XL0-3 bars HOLDING (X-XL4 excluded from gating).
- **Dependency (round 13 — RESOLVED by the joint ratification 2026-07-15): the XBRL design is not
  independently decidable.** Its pins amend and consume the KERNEL's machinery (P6 eligibility exclusion →
  kernel §6.5 · P7 provenance → kernel V9/§10.1 · P8 revocation → the kernel recovery/grader lanes · P4j →
  kernel §9.1(iv)). Both bundles were ratified TOGETHER, so the rejection contingency is MOOT — kept for
  history: had the kernel been rejected, the XBRL bundle would have re-based onto whatever recovery/provenance
  machinery replaced it (the already-law recovery paths, FINAL_DESIGN §5.4, cover
  `SAME_AS`/`CONTINUES_AS`/`disputed`, NOT ConceptResolution revocation).
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
- P1-P17/P19 + the ten document amendments were RATIFIED by the owner 2026-07-15 (design only). **Activation
  still waits on ALL of: the P19 proof plan (the X-XL0-3 bars above) · every hard pre-gate · the EXP-6
  convergence evidence — approval is done; none of the gates moved.** **The dormant `09`
  rider stays dormant: no `origin`, no `xbrl_link`, no empty≡GAAP folding, no XBRL producer rules before
  ENABLEMENT (ratification is done — the P19 bars + every hard pre-gate + the EXP-6 convergence evidence unlock the rider, nothing less).**

### 8.3 Bayes learner proposal — UNVETTED

One company-event-return-window training row containing ALL Drivers (never one full return per Driver);
post-outcome only; strict outcome-blind train/live parity; versioned derived outputs that never mutate
Driver/fact/verdict data; must beat simple + joint baselines and pass its five proof gates before promotion.
Archive under proposals; import nothing without owner approval.

## 9. Experiment program (signed artifacts are the ONLY status authority)

- `FableExperimentPlan.md` defines WHAT to test (sha-pinned `51966848…7472` — keep byte-identical, no banner).
  `FableExperimentWorkOrder.md` defines HOW (sha recorded, never pinned — the CURRENT sha lives on
  `experiments/WORKORDER_STATUS.md`, re-recorded at every edit incl. the Phase-5 21c re-point; the board was
  UPDATED at Phase-5 step 21c (2026-07-16) with the full hash chain — its current_workorder_sha256 line is
  authoritative; frozen original `4911a22f…` = the archive MANIFEST). Neither amends production law.
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
2. **Born-complete transaction:** the exact atomic CREATE write + failure behavior — still an unwritten recipe
   (the 2026-07-15 kernel ratification changed design status only, not this gap; lazy-create-on-ATTACH
   mechanics land at the OD-7/live-admission pass).
3. **Source identity namespaces:** the complete cross-channel escaping/delimiter law + fixed test vectors
   (only fiscal `:`→`_` is explicit today).
4. **Adapter/writer machine contracts:** exact field types/nullability, versioned schema, complete
   outcome/reason codes, cursor/completeness record shapes, certification fixtures (contract not
   implementation-ready until closed).
5. **Exact-block transfers — CLOSED (Phase 4 round 8):** kernel §15.0 MVP split + §16 residuals + the
   ratification bundle → §8.1 above; `12` §12's six acceptance gates incl. the F1-F9/P1-P8 fixture set → §5
   above; the XBRL materializer exact recipe + pins → §8.2 above. Prompt text: the XC PICK/VERIFY prompts and
   the classifier prompt content live in FINAL_DESIGN §8/§4.1 + §4 here; the hash-pinned experiment Plan/
   WorkOrder prompt packs stay live files until the experiment program migrates (the PLAN's byte-pin forbids
   edits; the WorkOrder's hash is recorded-not-pinned — it IS edited and re-hashed at Phase-5 step 21c, with
   its frozen original snapshot-archived first).

## 12. Evidence worth keeping once

Fixed-vocabulary v1 rejected ~82% of useful names; eager-reuse v2 merged distinct demand stories — the two
deaths that justify open vocabulary + err-toward-separation. Units: 117/117 main + 29/29+7 guards + three 33/33
runs (components, not wiring). Concept links: 31-company proof — 0 wrong links/249 accepted, 0 wrong abstentions/
1,178, ~99.4% tail recall; 274-company validation — 100% sampled precision, ~70% recall, 98% three-run identity,
with an incomplete hand list and a known "one wrong" tuning caveat (keep the caveat beside the numbers).
