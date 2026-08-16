# STATUS_AND_HISTORY.md — the one mutable dashboard, supersession ledger, and crosswalk

> **Status: LIVE — consolidation Phases 1-5 EXECUTED (owner GO 2026-07-16); the definitive reader test's outcome, per-question grades, and tested hashes live in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run15.md` — Phase 5 is COMPLETE ONLY IF that exact record shows 10/10 PASS. Review rounds + decision trail = the archived `CONSOLIDATION.md` §10.2/§16.** This file owns STATUS and HISTORY only — live rule
> wording stays in `FINAL_DESIGN.md`; procedures stay in `BUILD_AND_OPERATIONS.md`; channel duties stay in
> `ChannelContract.md`. Any status shown in another live file is a generated summary of THIS file. A status
> change edits this dashboard — and only if rule meaning changed through owner approval, the one owning rule
> section plus a new supersession row here.
>
> **Reading order (front door = `FINAL_DESIGN.md`):** FINAL_DESIGN → ChannelContract (adapters only) →
> BUILD_AND_OPERATIONS (builders/operators) → this file (what is open, replaced, or archived). Temporary fifth
> live file: `15_CandidateFactPacket.md` (owner-frozen v1.0 + the two 2026-07-15 owner amendments Q4/Q1-ext,
> current sha `aa7239ed…`).

## 1. Current execution checkpoint (2026-08-13; identity re-measured 2026-08-16)

**Plain truth:** the rule design is mostly settled and the deterministic Core
foundation is strong, but the new Driver system is not live. V1 is still the
active contract. The real shared meaning reader, the admission/reuse kernel,
production Driver writes, the complete point-in-time read layer and the running
system do not yet exist. Old Guidance was intact at the 2026-07-03 re-census
recorded in `BUILD_AND_OPERATIONS.md` §6; its state since then has not been
rechecked.

### 1.1 Exact current identity and evidence

- Published head, measured 2026-08-16: `main == origin/main ==
  356146dd5275d9fee65c1d58c95c37a7db4d9a63`; tree
  `bd1248968e5ded892bbe1c87122d6e6ff869bc03`. `origin/main` is this clone's
  remote-tracking record at its last sync; the remote itself was not queried for
  this status update. Every path published since the EXP-5 freeze is
  documentation under `FinalDesign/LeftOverSteps/`, so no code, contract or test
  identity moved with it.
- Last code identity: `0dd71956e942c889c70fede4e547f4737a39cff0`; tree
  `9f80af23f037f68d0a4233b1d752421963549011`. This is the EXP-5 exam-kit freeze
  commit (below).
- The Core V2 dry-run bridge is NO LONGER an uncommitted candidate. It is
  published at `0edb1be860524556134ecdedab248279590b23b9`; tree
  `d806365c41def2108f04cfa7ec6cef8559415638`. It is built and tested, and it is
  **dormant — dry-run only**: it is not the live contract, it performs no graph
  write, and committing it activated nothing.
- Fiscal V2 staging is published at `971ba079`; the Fiscal channel relocation at
  `da9afa06`; the four withdrawn Route-A certification artifacts at
  `54844a9f`; and the exact instant-period correction at `e6c9a956`.
- **EXP-5 exam-kit freeze — `0dd71956…`.** One bounded commit carrying exactly
  51 paths (28 modified, 20 added, 3 deleted), whose tree equals the
  independently reviewed `9f80af23…`. The final reader-plan manifest is
  `bf9323bc3bdc75a45a7381ac97cf0d4e1403f8754f5ac419abe1136f589c3070`. Proof over
  that exact tree, reconstructed in isolation and measured 2026-08-13: the
  isolated tree's own write-tree equalled the commit; the clean lane ran with NO
  credentials of any kind and returned **3,682 passed / 0 failed / 0 skipped**,
  with all **3,741** pinned identities accounted for in a lane; **58**
  read-only live nodes plus
  **1** owner-gated write probe were pinned and the write probe was NOT run.
  Zero AI calls, zero filing fetches, zero Neo4j writes, no activation and no
  V1->V2 switch. This freezes the exam kit; it does not run the exam.
- Graph: this update performed NO database read, so no current count is claimed.
  An earlier draft of this section attributed one combined census to
  2026-08-12; that date has no surviving receipt and is WITHDRAWN. Each figure
  below now carries only the evidence that actually supports it:
  - old Guidance, at the **2026-07-03** re-census in `BUILD_AND_OPERATIONS.md`
    §6: `Guidance=548` anchors, `GuidanceUpdate=8,432`, `GuidancePeriod=237`,
    and **894** sources (532 Reports + 362 Transcripts);
  - `Driver=0` and `DriverUpdate=0`, at the **2026-07-24** read-only check
    recorded in `WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`;
  - the DriverPeriod count, the Driver uniqueness constraints and the four
    required DriverPeriod sentinels are **unknown**: no receipt for them was
    found, and none may be inferred from this document;
  - writes being refused is not a census claim at all — it is live code: the
    Neo4j adapter's `transaction()` raises rather than opening one.

  The bridge and exam-kit work itself made **zero Neo4j writes**. Every figure
  above is dated historical evidence and cannot exclude unrelated external
  changes since its own measurement date.

| Area | Current truth |
|---|---|
| Rule design | Mostly final; the running layer is still design-incomplete |
| Catalog builder | Partial; no production catalog or OD-6 fitness pass |
| Fiscal tagged-filing path | Strong offline/staged V2 path; live command still emits V1 |
| Core IDs, periods, units, validation, fusion, planning | Built and tested; dry-run only |
| V2 event bridge | Published at `0edb1be8`; dormant, dry-run only, not active |
| EXP-5 exam kit | Frozen and published at `0dd71956`; NOT run — no model quality is claimed |
| Shared meaning reader | Not built; tests inject recorded answers |
| Driver reuse/create decision system | Approved design and rehearsal seams only; production kernel not built |
| Graph writes | Disabled (current, from live code: the adapter's `transaction()` raises); the 2026-07-24 read-only check found `Driver=0` and `DriverUpdate=0` |
| Point-in-time read layer | Build-pending; the adapter's narrow reads are not the finished layer |
| Schedules, retries, monitoring and backfills | Not built; design is incomplete |
| Old Guidance retirement | Not started by this work; the 2026-07-03 re-census (BUILD §6) found the old graph intact (state since then not rechecked) |

Corrections to the 2026-08-12 outside status review:

1. The Fiscal instant-period defect is no longer open; it is published at
   `e6c9a956`. The Core bridge is no longer uncommitted either — it is published
   at `0edb1be8`.
2. **THIS ENTRY WAS WRONG AND IS WITHDRAWN 2026-08-13.** It previously read that
   the new Core tests "do not open Neo4j while pytest is collecting them" and
   that "the reported collection-time side effect was not reproduced". The
   effect is REAL and was reproduced during Step 4:
   `driver/core/test_v2_event_route.py` built its fixtures at module import via
   `_v2_events()`, which called `route_a_source.build_source()` ->
   `dotenv_values('.env')` -> `GraphDatabase.driver(...)` and then ran two Cypher
   reads. In the working tree collection therefore SUCCEEDED by querying the
   live database, so every green reading of that suite had been taken with the
   graph reachable; in the committed tree, which has no `.env`, collection
   failed with `KeyError: 'NEO4J_URI'` and all 187 tests became "0 collected, 1
   error". The outside reviewer's original report was correct and this file's
   rebuttal was not. Fixed in the test fixture only — the source entry is now
   built from the tracked packet's own `source_id` and prepared text, output
   byte-identical to the graph-built baseline, with a mutation-proven guard that
   fails if the call returns. Production `route_a_source.py` was not changed.

### 1.2 Immediate bounded unit

The staged V2 dry-run bridge foundation and the EXP-5 kit freeze are both DONE
and published. The live ordered sequence is now `LeftOverSteps/Steps.md`; the
reader work below is its Step 1 and begins only after Step 0 publishes the
roadmap and this document, and after Codex authorizes that step.

1. **The K-fields launch is NOT ready and is NOT lawfully frozen for a run.**
   **CORRECTED 2026-08-16** — an earlier draft of this entry called the
   preparation READY and made the next unit a model run. What is true: the
   frozen inputs and the 36-event schedule exist, and `made_calls` is 0 in
   `experiments/harness/launch_kfields_drafts.manifest.json`. What is also
   true, and blocks a run: that same manifest still schedules two lanes per
   event, `model: sonnet` and `model: opus`, and
   `launch_kfields_drafts.workflow.template.js` calls those aliases directly.
   An Opus lane may not run under the `Steps.md` first-release model ruling.
2. The immediate bounded work after Step 0 is therefore preparation, not calls.
   `step1.md` A1-A2 require replacing the Opus lane with a second independent
   blind Sonnet 5 high-effort call, resolving the exact runtime identity and
   transport, regenerating the manifest and launcher twice to identical bytes,
   freezing the exact launch packet, and passing its deterministic preflight.
   Only after that may the 72 calls run — 36 events read twice, one lane each.
   Those calls need no separate owner or spending approval: the owner ruling in
   `Steps.md` pre-authorizes every model call already bounded by a reviewed
   step. Neo4j writes and live activation keep their own separate
   fresh-approval requirement.
3. **CORRECTED 2026-08-16** — an earlier draft of this entry stated that the
   K-fields lock hash is unset and that a runner refuses to start without it.
   Those belong to the EXP-5 launcher (`launch_exp5_readers.manifest.json`
   carries `kfields_lock.sha256 = null` and its runner-refusal rule), not to
   the K-fields door, which has no lock field at all.
4. After the drafts exist, Fable settles every K-fields record and disputed
   result against the event text alone, then signs and hash-locks the key
   (`step1.md` Roles and A4). Fable is a live independent review role, not a
   superseded model tier: the `Steps.md` model ruling replaces the old tier
   choices, not Fable. Any model-assisted part of that review is a separate
   blind Sonnet 5 high-effort call, and no call may grade its own answer. Only
   then may EXP-5 run, and EXP-6 only if EXP-5 passes.

**EXP-5 HAS NOT RUN.** The exam kit is frozen and proved self-sufficient; no
model has sat the exam, so no reader accuracy, recall or model-quality claim
exists or may be inferred from this checkpoint.

This checkpoint does **not** build the real reader or kernel, run EXP-5, switch
contracts, enable writes, build the read/running layers, or activate native XBRL.

One named pre-switch issue remains. The candidate deliberately splits
`validate_via_production` into its existing conversion owner before fusion and
its one underlying `validate_fact` rule engine after fusion. That is not a
second validator, but the staged public V2 contract §6 literally requires the switched
pipeline to pass every prepared fact through the named
`validate_via_production` doorway. Before the atomic switch, either that named
owner must support the fused production value without duplicate conversion, or
the owner must explicitly amend the contract. The current dry-run checkpoint
must not be described as completing that switch-time requirement.

### 1.3 Ordered roadmap after the Core checkpoint

**OWNER-RULED 2026-08-12: EXP-5 is a pre-switch proof.** The Core bridge is now
committed (`0edb1be8`) and the EXP-5 bundle is frozen (`0dd71956`), both while
V1 remains the live production contract and all writes remain off. Only then may
K-fields and EXP-5 run. This supersedes the 2026-08-11 “switch-gated bundle”
timing, which became circular once the switch itself required the still-unbuilt
reader/kernel that EXP-5 must first prove.

The dependency order is:

1. ~~Regenerate and freeze the EXP-5 contract, prompts, checks and manifests
   against staged V2, using only the committed dry-run bridge; V1 stays live.~~
   **COMPLETED 2026-08-13** at `0dd71956` (tree `9f80af23`). V1 stayed live
   throughout and no write was enabled.
2. **← NEXT.** Run the remaining evidence program: reader lane = K-fields ->
   EXP-5 -> EXP-6. It starts with preparation, not calls: `step1.md` A1-A2
   first replace the Opus lane with a second blind Sonnet 5 high-effort lane,
   re-freeze the launch packet and pass preflight. The 72 calls follow that and
   need no separate owner approval; GO #1 is still UNFIRED;
   identity/catalog lane = WP-FC-RUN, K-stamp/EXP-4B, F-C, K-route/EXP-3 and
   K-pairs.v2/EXP-4A. `LeftOverSteps/step1.md` now owns that lane's exact plan:
   the WorkOrder supplies its dependencies, but its still-unrun model,
   escalation and fallback choices are superseded by `Steps.md`, and no lane may
   launch before Step 0 closes.
3. Record the result memo; no failed or uncertain experiment becomes code.
4. Build one shared reader/decomposer and one admission/reuse kernel. Reuse the
   existing validation, fusion, planning and audit owners.
5. Prove a complete no-write V2 run over real text and XBRL-backed events,
   including all five outcomes and reuse/create/refuse/park behavior.
6. Resolve the named validation-door issue, then perform one atomic V1->V2
   switch: promote V2, freeze the V2 internal packet, move every caller and pin,
   delete V1 and the temporary V2 contract, and prove zero V1 reachability.
   Graph writes remain off.
7. Finish the full catalog/OD-6 gate, independent Fiscal prose certification,
   point-in-time read layer, operating layer, shadow burn-in and recovery.
   Native-XBRL materialization, other channels, verdict/DCM work, old Guidance
   retirement and broader rollout remain separately gated.
8. Model calls bounded by a reviewed step are pre-authorized under `Steps.md`
   and need no separate owner or spending approval; freeze each one's exact plan
   and Sonnet 5 high-effort identity first. Obtain fresh owner approval
   immediately before any Neo4j write and before any live activation.

### 1.4 Earlier one-page dashboard (2026-07-22 baseline)

| Layer | Design | Code | Tests | Production run |
|---|---|---|---|---|
| Rule meaning (FINAL_DESIGN §1-§9) | FINAL (locked set + owner rulings through 2026-07-18, incl. PER-21) | — | — | — |
| Track A catalog engine | FINAL | PARTIAL (WP-FC-EDITS `5db902f` + rounds 22-23 prompt sync; implementation gate in BUILD §4 governs any run) | 266 pass + 1 skip (2026-07-22, incl. the strengthened rulebook-sync guard + the PER-21 authority pin guard in `workflows/tests/`) | NEVER RUN (no graph catalog; fitness gate never run; old June RULE-BEARING outputs = historical evidence only, chunk copies excepted per BUILD §4) |
| Fiscal.ai channel adapter (S1) | FINAL incl. PER-21 | S1 BUILT; PER-21 historical-router correction SHIPPED — WP1 re-gate CLOSED (`80bae52`). Universal Locator WP2–WP4 execution is governed by `../WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md`, the sole current execution amendment/work order over the locked `../WIP/UniversalLocator_Design_2026-07-18.md` base (reading order: locked Design base → FinalPlan changes/current steps → Review Record history). Older UniversalLocator WIP plans are history/evidence. This work order does not amend FINAL_DESIGN, ChannelContract, BUILD_AND_OPERATIONS, PER-21, Core ownership, or News. | smoke 16 packets / 175 items, 0 tokens; WP1 close gates green at `80bae52` (battery 149/149 · floors 28/28) | not live |
| Track B fact stack | FINAL + the §11.4 INTERNAL writer contract OWNER-LOCKED 2026-07-17, internal portion CLOSED (PreparedFactV1 schema approved; public channel portion = S4) | steps 1-5 + step-7 slice menu BUILT (`driver/core/`: ids · period resolver, PER-20 HAS_XBRL producer guard PENDING · units · validators/planner · fusion · write CLI `97a46ce` · Report-only Neo4j adapter, writes DISABLED · slice_menu + owner-approved frozen lists, R12) | 392 unit + 1 opt-in probe skip · live read-only 10/10 (separate gate) · Track A 266+1 | dry-run only; ENABLE_DRIVER_WRITES off; adapter transaction() raises |
| Track C guidance retirement | FINAL v2.0 (no replay) | not started | — | — |
| Concept linker (text facts) | FINAL | PARTIAL (vetoes C/D + PIT query spec-only) | 31-co + 274-co evidence | not rolled out |
| Admission kernel | **APPROVED WORKING DESIGN (owner 2026-07-15; not activated)** | — | gates in force; integration COMPLETE (BUILD §8.1; original archived) | — |
| XBRL-native materializer | **APPROVED WORKING DESIGN (owner 2026-07-15; DORMANT until P19 enablement + hard pre-gates + EXP-6)** | — | EXP-1 signed | — |
| Experiment program | EXP-0/1/2 SIGNED PASS | — | — | EXP-3..6 / WP-FC-RUN PENDING |
| Running layer (schedules/ledger/QA) | NOT designed-complete | — | — | — |
| Consolidation itself | Phases 1-5 EXECUTED (owner GO 2026-07-16); all 33 sources accounted for byte-verified (29 originals + 3 snapshots archived; the byte-pinned Plan at root); audit trail = the archived CONSOLIDATION.md | — | definitive blank-context reader test: outcome + per-question grades + authoritative tested hashes in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run15.md` — Phase 5 COMPLETE only if that record shows 10/10 PASS | root = the 7 sanctioned files + archive/; Plan + WorkOrder stay until the experiment program migrates |

## 2. Lists by status

- THIS file owns the status lists (one-copy law); `FINAL_DESIGN.md` §10 is the GENERATED mirror. The master lists:
- **FINAL / BUILD-PENDING:** Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 production wiring · PER-20 HAS_XBRL producer guard · full slice TABLE materialization (materializer-era; the step-7 PIT menu code IS built) · concept-linker vetoes C/D + PIT query build · Track B remainder (the internal writer/validators/fusion/CLI/audit + step-7 slice menu are BUILT `0d6c1d0`, dry-run only — remaining: S4 decomposer/kernel integration + public channel runtime, FS-18 step-7 menu-for-producers, write enablement behind the fitness gate) · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh.
- **DESIGN-INCOMPLETE:** the production running layer (BUILD §7's runbook list). The OD-5 change scanner is a recommendation only.
- **CONDITIONAL:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (RATIFIED as design 2026-07-15; DORMANT until the P19 enablement proof plan — X-XL0-3 bars — every hard pre-gate pass, and the EXP-6 convergence evidence) · multi-run concept stability/caching (only if monitoring justifies).
- **OPEN (owner):** catalog 796-vs-786 + lifecycle/IPO · full model/cost policy beyond signed EXP-2 · FS-23 · 8-K item/content taxonomy only (earnings 8-K pairing is CLOSED by PER-21) · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement (part-2/news-channel) · **Driver financial classification (owner 2026-07-19): NO field approved — for now derive exact facts (company-specific XBRL linkage, monetary units); revisit before production Driver creation ONLY if a named consumer and a testable definition exist; otherwise the field stays absent.**
- **APPROVED WORKING DESIGN (owner 2026-07-15; not activated; gates/OFF-switches in force):** Admission Kernel v3.4 · XBRL-native materializer — integration COMPLETE (INT-2..INT-5, destination proof §7.1b); both originals archived 2026-07-15, byte-verified vs the Phase-1 manifest. The kernel bundle also settled two formerly-open/tracked items: G1 reuse-display rules (→ BUILD §8.1.3) · OD-7's born-complete/live-create CORE (→ BUILD §8.1; the broader OD-7 design stays UNRATIFIED — FINAL §4.2 Q5 note; the mis-name/mis-type exit + exact recipes land at the future OD-7 pass, BUILD §11.2).
- **CANDIDATE:** Bayes proposal · Driver Genesis restructure (rationale). Owner-question decision record = §4 below; the full decision text + verification trail = the archived `CONSOLIDATION.md` §10.2/§16 (`archive/2026-07-15_pre-consolidation/`).
- **Change law (owner 2026-07-15):** every future design correction updates the ONE owning live section and adds a short history entry here; no parallel live copies.
- **RETIRED (never a production path):** old Guidance replay plan (`13_Track_RetiredDesign.md` — GI stale-trap
  rows in its GI-07) · fixed-vocabulary Driver v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range`
  scope value · `gp_UNDEF` quiet fallback · `evhash16` on DriverUpdate · FS-22 cross-company recurrence ·
  RavenPack import · catalog-first live reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all
  catalog sync (owner ruling 2026-07-15, Q3).

## 3. The 43 supersession rows (terse; dead rule kept once for audit; current wording ONLY at the anchor)

| # | Subject | Dead rule | Current anchor (FINAL_DESIGN unless noted) |
|---:|---|---|---|
| 1 | Own company parts | brand/segment in the name | §3 NAME-10/11 |
| 2 | Measurement | adjusted/diluted in the name | §3 NAME-14 · §5.3 |
| 3 | Per-X | omit denominator / treat as unit | §3 NAME-13 · §6.1 |
| 4 | What makes an update | only a change qualifies | §1 · §4.2 |
| 5 | Evidence count | require >2 events | §4.2 |
| 6 | Verdict size | `magnitude` | §7.3 |
| 7 | Verdict allocation | shares must total 100% | §7.3 |
| 8 | Verdict storage | verdict node/property | §7.3 (edge) |
| 9 | Related flavors | no family link / merge as synonyms | §4.1 |
| 10 | Period model | guidance-only period | §6.2 |
| 11 | Slice kinds | 4 kinds + `store_type` | §5.2 |
| 12 | Slice identity | XBRL member ID | §5.1/§5.2/§8 |
| 13 | Concept linking | curated dictionary | §8 |
| 14 | RavenPack | Driver vocabulary | §4.3 (DU-11 context) |
| 15 | Model default | Fable two-pass reader | signed EXP-2 (BUILD §9) |
| 16 | Number shapes | stored `level_bound`; low-only point | §7.1 |
| 17 | Qualitative value | no qualitative field | §7.1 `value_text` |
| 18 | Fact hash | DriverUpdate `evhash16` | §5.1 · §7.3 |
| 19 | Confirmation | confirmation enum | §7.1 `company_confirmed` |
| 20 | Non-GAAP guard | name regex primary | §8 XC-05 (measurement set) |
| 21 | Live reuse | show catalog first | BUILD §4 (propose-first) |
| 22 | Concept invocation | SDK/OAuth metered | §8 (subscription only) |
| 23 | Missing period | quiet `gp_UNDEF` | §6.2 sentinels |
| 24 | Metric expectation | previous-guidance baseline on metric | §7.2 matrix |
| 25 | Whole-company slice | store `slice=total` | §5.1/§5.2 |
| 26 | Unit hints | one hint pair per item | §6.1 per-slot |
| 27 | Slice label drift | human alias files / confident alias | §5.2 · §9 |
| 28 | Slice menu | latest prior filing only | §5.2 union menu |
| 29 | Bare fact type | trust one classifier | §4.1 OD-2 |
| 30 | Collision hash | quote/value truncated hash | §5.1 OD-8 |
| 31 | Surprise arithmetic | above=beat, sign hard-fail | §4.3 · §7.1 (OD-13) |
| 32 | Loss values | positive loss magnitude / loss Drivers | §6.1 OD-12 |
| 33 | Sequential percent | all growth = YoY | §6.1 OD-11 |
| 34 | Guidance chronology: movement, amendments, withdrawal fan-out, Event/DCM overlap | movement stored from the write-time prior view; creation-only DCM single-target; open amendment handling | §9 + §7.3 |
| 35 | Measurement tokens | producer-final tokens; droppable | §5.3 OD-9 |
| 36 | Unit grouping | read-time family map / absorption | §6.1 OD-10 · §9 |
| 37 | Slice recurrence | cross-company recurrence identity | §5.2 (FS-22 retired) |
| 38 | Brand/slice test | external-brand heuristic | §3 NAME-11 |
| 39 | Wrong `SAME_AS` | never reopen automatically | §5.4 recovery |
| 40 | Entity names | ban every entity token | §3 NAME-11/16 carve-out |
| 41 | Token subset | permanent automatic refusal | §5.4 OD-19 (conditional) |
| 42 | Surprise scope | actual-only; no subtype slot | §5.1 OD-21 |
| 43 | FS-20 self-heal | automatic activity-based demotion ("auto-demote, no human") | §5.2 FS-20 (offline-only governed correction — R12) |

**Additions that are not reversals (each anchored in FINAL_DESIGN):** born-complete + latent-base exception
(§4.2) · OD-1 suffix admission (§4.1) · OD-2 metric-proof + first-fact pin scoped to bare names (§4.1/§4.2) ·
OD-3 blind local role test (§3 NAME-11) · OD-4 = FS-22 retirement, no slice-value recurrence rule (§5.2, row 37) ·
OD-5 scanner recommendation (BUILD §7) · OD-6 fitness gate (BUILD §4) · OD-7 live admission = its
born-complete/live-create CORE is ratified inside Admission Kernel v3.4 (owner 2026-07-15, NOT activated —
BUILD §8.1); the BROADER OD-7 design stays UNRATIFIED (FINAL §4.2 Q5 note) — the mis-name/mis-type exit after
facts exist + the exact born-complete/lazy-create recipes land at the future OD-7/live-admission pass (BUILD
§11.2) · OD-8 (§5.1) · OD-9 (§5.3) · OD-10 (§6.1/§9) · OD-11 (§6.1) · OD-12 (§6.1) · OD-13
(§4.3/§7.1) · OD-14 (§9) · OD-15 = near-synonym live races accepted as normal over-splits, no new locking (§4.2) ·
OD-16 resolved 2026-07-15 → lazy born-complete (§4.2) · OD-17 (§3) · OD-18 (§5.4; CLAIM separate, ships off) ·
OD-19 (§5.4) · OD-20 (§5.4) · OD-21 (§5.1/§6.2/§7) · K2 = fold repair stays per-pair, batched fold repair
deferred (BUILD §4) · frozen packet v1.0 + Channel Contract v1.0 (boundary files) · Track C full no-replay
reversal (BUILD §6).

## 4. Owner rulings record (through 2026-08-12)

> Owner rulings made after that date are recorded in
> `LeftOverSteps/Steps.md`, not here; this section is not a complete record of
> them.

Q1 `company_confirmed`: CORE derives from who-said-it evidence; unclear = SKIP (ruling's own content); `false`
stays reserved for explicitly-ALLOWED future third-party classes (enabling any class = part-2/news-channel
decision) → FINAL_DESIGN §7.1. · Q2 non-slice/elimination: NO change — frozen packet PARK+log stands; FS-20
auto-demotion is the drain → §3 OD-17. · Q3 catalog sync: resolution (b) — offline catalog + lazy born-complete
nodes (created in the same write when an ATTACH targets a card with no node yet — mechanics TO BE specified at
the future OD-7/live-admission pass, recipe not yet written, BUILD §11.2); OD-16 narrowed → §4.2. · Q4 XBRL packet shape: amendment APPLIED 2026-07-15 to ChannelContract + frozen
packet (`dimensions=[]` verified-empty; both axis+member; never fragments). · Q5 first-fact guard scoped to
bare names; suffix-proven lanes may be born `unknown` → §4.2. · R6 (round 16) `xbrl_internal_conflict` retry
trigger: retry ONLY when the affected report's parsed XBRL facts actually change; an amended filing is a NEW
report, never a silent rewrite → BUILD §8.2 recipe step 4. · R7 (2026-07-16) official reader-test Q3 amended:
"For each surprise, construct its required same-event home fact, state the home's driver_state, and show the
required family, period, period scope, slice, measurement, and normalized value/unit match." — supersedes the
archived CONSOLIDATION §14.3 item-3 text; design files and preamble otherwise unchanged. · R8 (2026-07-16, final closure + standing reader-test policy): (a) the proposed "hash only the three law files" rule is REJECTED — every reader test pins EVERY file it reads (BUILD and STATUS carry essential design mechanics and decisions); (b) routine build/status progress updates do NOT require a full reader-test rerun; changes to rules, contracts, operative mechanics, gates, owner decisions, crosswalks, or major release handoffs DO; (c) final closure = ONE fresh R7-amended reader test against ONE committed seven-file freeze — 10/10 + 7/7 exact hashes + explicit command-exit checks required, the record added AFTER the test without changing the seven tested files, the freeze-commit SHA recorded in the definitive record — then the documentation track RETIRES (run 14's record preserved as qualified historical evidence). Full decision text + verification trail:
the archived `CONSOLIDATION.md` §10.2/§16 (`archive/2026-07-15_pre-consolidation/CONSOLIDATION.md`, archived at Phase-5 step 7, 2026-07-16).
· **R9 (2026-07-17) FS-18 kind-scoping ruling:** the fold equality is WITHIN one company on the complete
`kind:norm(value)` token only; equal values under different kinds (incl. `unknown`) never fold or share a
member link; member-label normalization = the shared format-only normalizer, never stemming/suffix-stripping →
FINAL_DESIGN §5.2 FS-18. Basis: third-bot DB finding, independently reproduced + corrected by the core bot
(real exact-collision population: `international` 5 cos · `corporateandother` 4 · `other` 3 · `corporate`/`us`
2, same label on both geo+segment axes at one company; suffix-stripped collisions americas 21 / northamerica
19 / europe 11 / emea 10 are NOT at risk — stripping was already unlawful, archived 03 "no stemming"); the
archived original FS-18 was equally silent (under-spec closure, NOT a reversal — supersession row 12 not
reopened; FS-15 "kind never reconsidered" + the unknown-axis sentinel already pointed within-kind). A
CLARIFICATION, not a meaning change → no supersession row. Five pinned test cases land with the S3 step-7
menu/dedupe build (same-kind fold · cross-kind separate · unknown-vs-known separate · Europe≠EuropeSegment ·
same member on different axes = separate exact axis/member links). No migration; no production code today.
· **R10 (2026-07-17) THE S3.5 INTERNAL WRITER CONTRACT LOCKED (v3.6):** operative text = BUILD §11.4 item 4.
Converged through the owner's zero-based simplification (the CLI is INTERNAL until the decomposer/kernel —
the entire public channel runtime is ONE deferral to S4; ChannelContract v1.0 stays ACTIVE law, only its
software connection deferred) + five reviewer passes, every accepted point independently reproduced. Key
pins: PreparedFactV1 anchored to packet sha `aa7239ed…` Block 2 (schema review = the remaining gate before
the internal portion CLOSES; §11.4 stays PERMANENTLY PARTIAL until S4 regardless) · fusion fills nulls only,
ten-signature-slot disagreement prevents fusion, unfused → the full OD-8 ladder with no hashing promise,
permutation-identical · whole-event non-retried tx w/ in-tx recheck+reads+final-plan, flock single-writer ·
truthful outcomes (rollback reports zero written; REJECT beats PARK; date=source time, created=commit time) ·
write-ahead audit file prepared→committed/failed/dry_run = the interim park ledger · SOURCE_COMPANY_AMBIGUOUS
via the ownership relationship only · MEMBER_LINK_DEFERRED pre-plan until step 7. CLI build authorized.
· **R11 (2026-07-17) INTERIM period-scope labeling — explicitly NOT P14; P14 stays DORMANT:** a period
audit reproduced the exact-date branch labeling the same window `exact_range` while the SEC path said
`quarter` (breaks the OD-21 surprise↔home scope match; `period_scope` is in the §9 read-series key). The
ratified cure (the BUILD §8.2 **P14** date-anchored classifier + instant `period_scope=null`) is DORMANT
until the XBRL materializer enables — so the owner ruled an INTERIM fix in `driver_period_resolver.py`:
scope labeled from the item's own declared fields via ONE mapping (fq→quarter · half→half · month→monthly ·
long_range→exact_range · fy→annual · none→exact_range; declared ytd/ttm wins) — paths converge when fiscal
framing is supplied; frameless exact dates honestly stay exact_range — plus ONE strict period-shape check
on every path: conflicting/mixed/out-of-range fields, sentinel+dated/fiscal combos, incomplete long-range
(start-only; end-only = the proven "by 2030" shape, legal), and invalid dates all PARK, never crash; zero
values are validated (is-not-None), never treated as absent. A declared label contradicting the window
length PARKS; bands sized so the KNOWN TESTED calendars pass (52/53-wk, 4-4-5, KR 16-wk Q1 = 112d, COST
84d/119d, full-year Q4-YTD 365/371d, January-to-date ytd — no ytd minimum). Instants keep live-law scope
until the dormant bundle flips coordinated with the validators. At materializer enablement P14 replaces
ONLY the temporary labels/bands — the basic input validation is permanent.
· **R12 (2026-07-17) FS-20 lists APPROVED as code + automatic demotion SUPERSEDED:** the owner approved
the frozen slice-axis lists in `driver/core/slice_axis_frozen.py` — 12 hand-vetted pure hard-exclude
eliminations · 79 provisional members · exactly 7 proven non-slice axes; every unreviewed axis takes the
unknown→provisional sentinel path (the a:EndMarketsAxis lesson: 246 real Agilent end-market facts sat in
a censused "non-slice complement", which is deleted and banned); unseen elimination names are never
pre-frozen. The catalog's "self-heal: auto-demote, no human" line is SUPERSEDED: occurrence counts never
auto-demote; the structured exclusion logs are evidence for a governed OFFLINE update that simply moves a
proven-mistake qname from hard-exclude to provisional. Same ruling batch: XBRL member links verify
FACT-LEVEL (concept + time_type + exact dates + COMPLETE dimension set, `[]` included, entity-scoped,
numeric non-nil, misaligned context arrays fail closed; stored ends exclusive per the 2026-07-09 decode);
fusion never combines two different complete dimension sets (identical sets fold, None inherits, anything
else parks — a union would fabricate a set no real XBRL fact carries); the step-7 slice menu replaced the
`MEMBER_LINK_DEFERRED` fence with `MEMBER_LINK_INVALID` (§11.4 amended).
· **2026-07-16 (S3 GO):** owner approved the S3.1 cross-channel ID law — 7 decisions one-by-one (reject-not-
escape · 4-segment id w/ trailing colon on empty scope · `[A-Za-z0-9._-]` source charset case-preserved ·
readable-date `gp_` ids · the one text normalizer w/ park-on-empty · the one decimal canonicalizer · text-based
10-slot sha256 fingerprint) → BUILD §5 ID-shape entry; BUILD §11.3 closed; operative law =
`driver/core/driver_ids.py` + its frozen vector suite. Owner also blessed the build sequence (S3 writer stack →
S4 kernel day-1 + pilot → enrichment); ratification-vs-authorization wording never blocks the agreed sequence.
· **R13 (2026-07-18) earnings 8-K period authority CLOSED:** the owner locked exactly two files for earnings
8-K routing. Historical/backfill exact periodic-accession pairing belongs to
`.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`, with `quarter_identity.py` used only
as an `AUTO_OK` trust gate; its fiscal label/projected dates do not join historical documents. Live, before
the target periodic filing exists, belongs to `scripts/earnings/quarter_identity.py` alone. Missing or
ambiguous evidence parks. Any third/copied fiscal-label, projected-date, or filing-sequence matcher is
superseded and forbidden. This source-routing decision is distinct from Driver fact-window resolution
(FINAL_DESIGN PER-21; procedure = BUILD §3). The frozen packet stays byte-identical at `aa7239ed…`: its
"shared resolver is the sole period authority" phrase means the fact's own window only, never 8-K source
pairing. Per the standing R8 policy the recheck remains OWED: the 2026-07-22 first run's PASS was WITHDRAWN
on regrade (one exercise failed under the locked no-rescue rule; detail =
`archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21_CORRECTION.md`; the original
record is preserved unedited beside it). A fresh blank-context rerun is prepared; this obligation is
DISCHARGED only if `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21-run2.md`
records PASS 10/10 with 7/7 unchanged pins at the commit carrying this sentence.

**2026-08-11 — per-X naming form (NAME-13): UNIFORM SPELL-OUT.** The owner ruled the naming-form
deferral of 2026-07-25. Both deferred rules are REMOVED from live law: the sole `eps` canonical-name
exception, and the open-class "familiar acronyms" sentence that let any acronym already carrying its
denominator keep the short form. (Neither rule is reproduced here: the residue guard requires this
file to be free of the retired wording, so it is described, never quoted.) Every stated
business/physical per-X denominator is now
written out in the canonical Driver name; the families are `earnings_per_share` /
`_guidance` / `_surprise`, and `dps` resolves to `dividend_per_share`. An acronym whose expansion
cannot be verified is NOT coined and NOT guessed — the reader skips, and a name↔per_x conflict parks
at admission (ONE owning component; no interim validator was added). Source quotes are NEVER
rewritten; `per_x` stays the fact-level signal; the stored unit stays base (`usd`);
adjusted/basic/diluted stay in measurement (NAME-14 unchanged). Per-X ONLY — NAME-07 familiar
market/policy names and NAME-08 whole phrases (`ebitda`, `fcf`, `fed_rate`, `cogs`, `rpo`) are
untouched. The NAME-13 deferral note is superseded and its ⏸ markers are deleted from FINAL_DESIGN
§3/§10 and the three live prompt rulebooks. Evidence: `experiments/WORKORDER_STATUS.md` 2026-07-25
pack · EXP-2C 40-chunk replay (zero eps forms emitted, correct spell-out, quotes verbatim) · EXP-2D
acronym probe (zero acronyms kept as names, unverifiable acronym skipped, ARPA-agency trap passed).
Guard: `workflows/tests/test_perx_naming_residue.py`. STILL OPEN and deliberately NOT in this batch:
the EXP-5 item-contract regeneration (`exp5_item_contract.md:127` still serves the old sentence) and
the launch-manifest re-pin. CORRECTED 2026-08-11 (reviewer SEQ 957/959): these do NOT belong to the
Core contract-freeze step. The 2026-08-11 conclusion that the whole bundle was
switch-gated is **SUPERSEDED by the 2026-08-12 owner ruling below**. K-fields
GO#1 was gated on the complete bundle being regenerated, hash-frozen and proved
against the committed staged-V2 dry-run bridge. **That condition was satisfied
on 2026-08-13 (`0dd71956`), and GO#1 is still UNFIRED.** The bundle was the
TECHNICAL PREREQUISITE, not the authorization: satisfying it did not by itself
start any call. **SUPERSEDED 2026-08-14** — this entry ended by keeping GO#1
owner-gated pending fresh approval at the moment of the run. The `Steps.md`
owner ruling pre-authorizes every model call already bounded by a reviewed step,
so GO#1 now waits on Step 1 freezing its exact bounded plan and pinning Sonnet 5
at high effort, not on a further owner approval.

**2026-08-11 — STAGED CORE V2 PUBLIC CHANNEL CONTRACT FROZEN (not live).**
`FinalDesign/ChannelContractV2.md` sha256 `d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b`.
The separately versioned V2 PUBLIC contract governing every channel; Fiscal is the first
staged consumer. It publishes the full three-stage flow: Stage A the CHANNEL RAW EVENT
(envelope, text_parts supplied once, raw items, the XBRL bundle, and the four RETIRED
Fiscal-authored fields that are never accepted or defaulted); Stage B reader/Core
preparation; Stage C outcomes. DIMENSIONS ARE TWO STAGES, never one: the PUBLIC raw
`xbrl.dimensions` entry is exactly {axis, member} and the channel never invents
`slice_part`; only the INTERNAL `member_refs` triple carries it, derived by Core. The
Stage-A raw fields are NOT mechanically compared to code — that boundary is unbuilt, so
they are owned by this hash freeze and reviewer approval until Fiscal writes its own
boundary tests. The exact first-consumer raw profile is PUBLISHED as the
`staged_raw_channel` object inside the single CONTRACT-SURFACES block (event, text-part,
item, xbrl, nested `ix`, dimension and retired-field spellings, plus the unchanged
source_type vocabulary), and the never-send / source-completeness duties are retained. It is STAGED, not live: `ChannelContract.md` (v1.0) remains the live public
authority and `15_CandidateFactPacket.md` remains the live INTERNAL packet law.
The freeze is ENFORCEABLE, not prose: `driver/core/test_v2_attacks.py` compares every CURRENT
CODE-OWNED surface to its existing code owner AND proves this sha256 equals the
document's real bytes, so a silent edit to either side fails.
PROMOTION RULE — at the atomic V1->V2 switch, in ONE batch: this document is PROMOTED to
`ChannelContract.md`; `15_CandidateFactPacket.md` is SEPARATELY re-frozen to its own V2
packet law (a distinct internal contract, never a copy of this public one); every live caller
and `aa7239ed` pin is moved; the already-frozen V2 EXP-5 bundle is verified rather than
regenerated; and `ChannelContractV2.md` IS DELETED. Nothing was activated, written, fetched
or run by this freeze.

**2026-08-12 — EXP-5 TIMING: PRE-SWITCH PROOF (owner-ratified).** The
2026-08-11 switch-gated timing above is superseded. Exact order: commit and
freeze the staged-V2 dry-run bridge -> regenerate and freeze the complete EXP-5
bundle against that staged contract while V1 remains live -> lock K-fields and
run EXP-5, then EXP-6 -> build the real shared reader/decomposer and
admission/reuse kernel from the signed evidence -> prove the complete V2
no-write route -> perform the atomic V1->V2 switch. This is a timing ruling only:
it activates no V2 caller, authorizes no paid model call, changes no fact rule
or test bar, and permits no Neo4j write. A failure stops before activation.

## 5. Signed experiment decisions + remaining gates (authority = signed decision.json artifacts)

EXP-1 PASS 07-09 (O13 dimension binding owner-ratified) · EXP-0 PASS 07-10 (grader = 2× `claude-sonnet-5`
@effort=high; the (model,effort) pair binds) · WP-FC-EDITS `5db902f` 07-10 · WP-FA + O2 signed 07-10 · K-reader
v3 LOCKED 07-10 · EXP-2 PASS 07-11 (sonnet-5@high/40k/1-run) · PENDING: EXP-3..6, remaining keys, WP-FC-RUN,
F-C freeze. Standing gates: ra_0007 kernel-§6.1 review BEFORE K-pairs.v2; Plan sha `51966848…7472` byte-pinned;
WorkOrder sha recorded, never pinned — authoritative record = `experiments/WORKORDER_STATUS.md`, re-recorded at
every edit incl. the Phase-5 21c re-point (board UPDATED at Phase-5 step 21c 2026-07-16 — the full hash chain recorded, its current line authoritative;
frozen original `4911a22f…` = archive MANIFEST). Artifacts:
`.claude/plans/Drivers/experiments/`.

## 6. Known documentation/logic issues (open; no new authority)

- The 24 stale-text items (per-file) and the interim hazard rule: the archived `CONSOLIDATION.md` §10.1 + Phase-2 note.
  Biggest traps: `03`/`11`/`12` old collision text (OD-8 is current) · `04` one-hint-pair (per-slot is current) ·
  `09 §8`/`07 §D` expectation-baseline wording · stale experiment headers (signed artifacts win) ·
  `15` "already built" = "fully specified" (stale-item 11).
- Missing build recipes (packet lifecycle · born-complete transaction · machine contracts; ID namespaces
  CLOSED 2026-07-16 — owner-approved S3.1 ID law, BUILD §5/§11.3):
  BUILD §11.
- Truly open owner choices: FINAL_DESIGN §10 OPEN list.

## 7. Source crosswalk (33 files → destinations; every row re-verified at Phase 4/5)

**Phase 5 EXECUTED 2026-07-16 (owner GO):** every "archive" destination below is DONE — EXCEPT the two
deferred experiment files (the byte-pinned Plan + the WorkOrder, which archive only after the experiment
program migrates) — all 27 remaining
sources moved byte-verified vs the manifest (the two ratified-design originals had already moved 2026-07-15);
the three pre-amendment/frozen-original snapshots sit beside them.

| Source | Status | Destination |
|---|---|---|
| 00_Coverage / 01_Overview | stale summaries | FINAL_DESIGN §1-§2; archive |
| 02_DriverCatalog | rule owner | FINAL_DESIGN §3; archive |
| 03_Slices_FactScope | rule owner | FINAL_DESIGN §5; archive |
| 04_Units | rule owner | FINAL_DESIGN §6.1; archive |
| 05_Periods | rule owner | FINAL_DESIGN §6.2; BUILD §5; archive |
| 06_MetricFamily | rule owner | FINAL_DESIGN §4.1; archive |
| 07_DriverUpdate | rule owner (DU-13..18 replaced by 09) | FINAL_DESIGN §4.3/§7.3; archive |
| 08_XBRL_ConceptLinking | rule owner | FINAL_DESIGN §8; BUILD §5; archive |
| 09_DriverUpdate_Fields | field/read authority | FINAL_DESIGN §7/§9; archive |
| 10_BuildPipeline | Track A manual | BUILD §4; archive |
| 11_TrackB Census · 12_FactPipeline | normative census + build manual | FINAL_DESIGN (rules) + BUILD §5; archive |
| 13_TrackC (active) · 13_Track_RetiredDesign | retirement plan · retired history | BUILD §6 · archive (one pointer to its still-useful non-replay analysis: GI-31 `<=` rationale, 894-source reachability audit, 4 stated-mid outliers) |
| 14_BuildReadiness | stale checklist | BUILD + this file's dashboard; archive |
| 15_CandidateFactPacket | FROZEN v1.0 + the two 2026-07-15 owner amendments (Q4, Q1-ext) | temporary fifth live file (current sha `aa7239ed…`) |
| 66_IssuesToBeHandled | owner blocks + stale tail | rules → FINAL_DESIGN; status here; archive |
| 90_OpenItems · 95_Supersession · 99_Codex audit | status · 43-row ledger · history | this file §1-§3; archive (99 wholesale) |
| BayesProposal | unvetted proposal | BUILD §8.3 pointer; ARCHIVED directly in the dated archive 2026-07-16 ✓ |
| ChannelContract | ACTIVE live file | kept — the SOLE public channel authority under the one-copy law; amended 2026-07-15 (XBRL/evidence/provenance) and 2026-07-18 (PER-21 source-completeness pointer); current sha tracked in git + CONSOLIDATION §16 hash freeze |
| DriverGenesisRestructure | unapproved rationale | open charter questions in FINAL_DESIGN §10; archive |
| DriverPlan.html | stale study export | none (regenerate later from live docs); archive |
| FableAdmissionKernelDesign | **RATIFIED working design (owner 2026-07-15; not activated)** | full mechanics → BUILD §8.1 + law-grade parts → FINAL_DESIGN (destination proof §7.1b); **original ARCHIVED 2026-07-15, byte-verified — DONE** |
| FableContextPack · WorkflowContextPack | stale navigation/code maps | ARCHIVED 2026-07-16 ✓ (the Workflow pack's 21b live-code re-audit PASSED pre-move — 34-claim verdict table; its one load-bearing residue carried into BUILD §4; links repaired) |
| FableExperimentPlan · WorkOrder | pinned plan · runbook | BUILD §9; keep Plan byte-identical until program migrates; archive after. The Plan's frozen authority ladder (lines 4/257) resolves externally: its "lock candidates" were RATIFIED 2026-07-15 (operative mechanics = BUILD §8.1/§8.2; originals = archive evidence); its topic docs resolve to the archive paths with meaning carried by the four live files (step 21c note) |
| FablePrompt · FablePromptv2 | executed briefs | provenance entries only; archive |
| XBRLIntegrationDesign | **RATIFIED working design (owner 2026-07-15; DORMANT until P19 + gates + EXP-6)** | recipe + pin map + the ten amendments → BUILD §8.2 + owning law sections (gate-tagged); **original ARCHIVED 2026-07-15, byte-verified — DONE** |
| CONSOLIDATION.md | audit + migration map | MOVED into the dated archive at Phase-5 step 7 (2026-07-16) ✓ — never a fifth rule source |

### 7.1 Rule-ID crosswalk (every stable ID range → its one live anchor; §14.1 artifact)

Coverage law: every ID in a range maps to the range's DEFAULT anchor unless it appears in the exceptions
column — the map is total over every ID listed in the archived `CONSOLIDATION.md` §14.1.

| Rule IDs | Default anchor | Per-ID exceptions (exact) |
|---|---|---|
| NAME-01..19 | FINAL_DESIGN §3 (inline, own numbers) | — |
| FS-01..04, 27 | FINAL_DESIGN §5.1 | FS-03's old collision text dead → OD-8 (§5.1) |
| FS-05..24 | FINAL_DESIGN §5.2 | FS-09 separators also §5.1 · FS-14 menu + PIT · FS-15 kind ladder · FS-16/18 code-exact rules · FS-20 buckets · FS-21 member link · FS-22 RETIRED (row 37) · FS-23 OPEN (§2) |
| FS-25 | FINAL_DESIGN §5.3 | — |
| FS-26 | FINAL_DESIGN §5.4 | storage shapes + guards + recovery inline |
| UNIT-01..13 | FINAL_DESIGN §6.1 | UNIT-04 replaced by per-slot hints (row 26) · UNIT-08 per-X also §3 NAME-13 |
| UNIT-14 | BUILD §5 | build wiring only |
| PER-01..19 | FINAL_DESIGN §6.2 | — |
| PER-20 | BUILD §5 | resolver build + 21 tests |
| PER-21 | FINAL_DESIGN §6.2 | earnings 8-K routing procedure → BUILD §3; owner ruling R13 |
| MF-01..10, 12 | FINAL_DESIGN §4.1 | MF-05 latent anchors also §4.2 · MF-10 inheritance also §8 |
| MF-11 | FINAL_DESIGN §7.1 | `company_confirmed` |
| DU-01..07 | FINAL_DESIGN §4.1/§4.2 | DU-05/06/07 classifier content §4.1; prompt pin BUILD §4 |
| DU-08..12 | FINAL_DESIGN §4.3 | state vocabularies |
| DU-13..18 | FINAL_DESIGN §7.1 | explicitly REPLACED by `09`'s contract (banner row `07`) — shapes, DU-15 baseline, sign rule, value_text/conditions/confirmed |
| DU-19..24 | FINAL_DESIGN §7.3 | edges, verdict, DCM |
| XC-01..18 | FINAL_DESIGN §8 | XC-04..08 verbatim blocks inline · XC-16 CONDITIONAL · rollout/vetoes-build → BUILD §5 |
| PIPE-01..37 (+27a/27c/27d/31b) | BUILD §4 | PIPE-12 relay-trust + PIPE-15 run layout summarized in D1-D8/constants · PIPE-16 authority swap (prompts inline NAME rules) · PIPE-24/25/26/35 finalization/consumption inline · PIPE-32 A/B gate |
| FACT-01..36 (+14b/17b/18a/26b/26e/26f) | BUILD §5 | FACT-16 validators + §12 gates (F1-F9/P1-P8) inline · FACT-17b = the internal packet → BUILD §2 · law mirrored in FINAL_DESIGN §5/§7 |
| T1.1..T12.9 (census `11`) | per-group anchors in the T-table below | the census DUPLICATES `09`/`12` normatively; numbering retires at archive |
| GI-01..04 + active `13` §§0-15 | BUILD §6 | runbook/deletion/gates inline; §§12-15 are meta sections (cross-doc edit log, non-goals, minimalism proof, drafting record) with no rule IDs — covered by the §7 file-level row |
| Retired `13_Track` file's OWN GI-01..07 and GI-10..36 (a separate numbering from the active file's GI-01..04; **no GI-08 or GI-09 exist**) | history only — §2 RETIRED list | never live mechanics; still-useful non-replay analysis pointer in §7 crosswalk row |
| Track A D1..D8 | BUILD §4 | — |
| `66` D-1..D-13 | doc-debt history, resolved in place | archive only |
| OD-1..21 | per-ID anchors in the §3 additions list | all 21 individually anchored there |
| K2 | BUILD §4 | — |
| 43 supersession rows | §3 above | — |
| Contract clauses §1-§9 | ChannelContract.md (live; one section per clause: what-a-channel-is · flow · packet · never-send · submission · outcomes · ledger duties · never-list · onboarding) | — |
| Packet blocks 0-3 + Parts B/C/D | the live frozen packet (structure summarized BUILD §2) | — |
| Ratified design bundles (formerly candidates) | BUILD §8.1 (kernel mechanics whole) · §8.2 (XBRL recipe + pin map + amendments) = the OPERATIVE text; the archived originals are historical evidence only (destination proof §7.1b) | — |
| Open items | §2 OPEN list (mirrored FINAL_DESIGN §10) + BUILD §11 missing recipes | — |

### 7.1b Ratified-design destination proof (owner order 2026-07-15: every transferred item → its exact live anchor)

**Kernel (FableAdmissionKernelDesign.md → live anchors; BUILD §8.1.x unless noted):**

| Kernel section | Content | Live anchor |
|---|---|---|
| §1 strategy D1-D4 + 8 answers/3 amendments | anchor-first live-always | BUILD §8.1.1 |
| §2 decision flow (Stage 0-3, async, axiom C) | intake/router/arms/guards/provenance | BUILD §8.1.2 |
| §3 G1 display | cards, never-shown, verbatim instruction | BUILD §8.1.3 |
| §4 arms + the 8 park codes | ATTACH/ADOPT/CLAIM rules, park governance | BUILD §8.1.4 |
| §5 family policy | stamp/resolve functions, variant stamping, latents | BUILD §8.1.5 (+ FINAL_DESIGN §4.1/§4.2 law) |
| §6.1 LINK operation | pair assembly, auto-refusal taxonomy, the 5 checks, high-blast, apply/memo/head election, cache | BUILD §8.1.6 |
| §6.2 two triggers + ledger hygiene | CLAIM-off/shadow, sweep, deferred ledger | BUILD §8.1.6 |
| §6.3 frozen anchor | birth_quotes, refuted negatives, enrichment-OFF, re-freeze | BUILD §8.1.6 |
| §6.4 union-preview | abstain-only | BUILD §8.1.6 |
| §6.5 eligibility/establishment | BROAD/ESTABLISHED/CLAIM_FROZEN, in-tx read, single-company exception | BUILD §8.1.6 |
| §6.6 split-reconciliation lane | batch-grade re-judgment of mutual refusals | BUILD §8.1.6 |
| §7 validators V1-V14 | full meanings | BUILD §8.1.7 (V14 also FINAL_DESIGN §5.4) |
| §8.1-8.5 phases/seed/gauntlet/eligibility/contingency | sequence, S-A1..6, P1..P9, pass bar, BROAD-keyed features, ladder | BUILD §8.1.8 |
| §9 immune system | doctrine, falsifier (i)-(vii), audits, calibration stream, flow metrics, launch blockers | BUILD §8.1.9 (ATTACH-audit law in FINAL_DESIGN §5.4) |
| §10 recovery items 1-8 | provenance, signal-quarantine, 2-grader confirm, propagation, RecoveryEvent, wrong-quarantine, D4 scoping, disputed | BUILD §8.1.10 (+ FINAL_DESIGN §5.4 law) |
| §11.0/§11 model tiers | locked rule, tiers, owner defaults, P1-P7 deltas | BUILD §8.1.11 (principle in FINAL_DESIGN §1) |
| §12 experiments | S1-S4, X0-X9, X-G, X-IM, X-C | BUILD §8.1.12 |
| §13 rejected · §14 reject-conditions | terse load-bearing lists | BUILD §8.1.13 |
| §15.0 MVP split · §15 bundle · §16 residuals | day-1 core/deferred/coverage rule · six ratified items · five residuals | BUILD §8.1 (the three dedicated blocks) |

**XBRL (XBRLIntegrationDesign.md → live anchors):** §3 coverage five-conditions + §5.2 recipe steps 1-9 +
graph-verified formType literals → BUILD §8.2 recipe · §5.3 period classifier + P14 → BUILD §8.2 pin map + §5
dormant-amendment note · pins P1-P17/P19 (incl. P16) → BUILD §8.2 pin map · the ten amendments → their owning
sections, gate-tagged: (1)(3)(7)(9) → BUILD §5 validator note · (2) → BUILD §8.1.7 V9 · (4) → FINAL_DESIGN §8
rider line · (5) → BUILD §8.1.6 eligibility · (6) → FINAL_DESIGN §8 XC-18 · (8) → BUILD §8.1.9 falsifier ·
(10) → FINAL_DESIGN §9 collapse rank · TextBlock disposition + half-ULP gate + ConceptResolution schema +
graded reversal + kernel-dependency note → BUILD §8.2.

### 7.2 Census T-group anchors (per-group exact map; within a group, rules share the group anchor unless a per-rule exception is listed)

| T-group | Census topic | Exact live anchor(s) |
|---|---|---|
| T1 (T1.1-T1.8) | Mission constraints & laws | FINAL_DESIGN §1; exceptions: T1.4 producer-free id → §5.1 · T1.6 enrichment-never-identity → §8 · T1.7 FROM_SOURCE ≠ EXPLAINED_BY → §7.3 |
| T2 (§2 tables, no T-bullets) | The record — 24 stored fields | FINAL_DESIGN §7.1 |
| T3 (T3.1-T3.8) | Identity — id + fact_scope grammar | FINAL_DESIGN §5.1 (OD-8 replaces T3.4); T3.5 measurement → §5.3 · T3.6/T3.8 slices → §5.2 · T3.7 period-both-places → §6.2 |
| T4 (§4 edge table) | Edges & neighbor nodes | FINAL_DESIGN §7.3; HAS_PERIOD lane rules → §6.2 |
| T5 (T5.1-T5.5) | The verdict edge | FINAL_DESIGN §7.3 |
| T6 (T6.1-T6.5) | Lanes — type × state × field matrix | per rule: T6.1 fact_type definitions + verbatim classifier → FINAL_DESIGN §4.1 · T6.2 state lanes → §4.3 · T6.3 state-in-lane hard-fail → §4.3 (final line) · T6.4 per-lane matrix + OD-21 amendments → §7.2 (+ §5.1 for the `surprise=` slot) · T6.5 revisit triggers → §10 OPEN list |
| T7 (T7.1-T7.12) | DriverPeriod | FINAL_DESIGN §6.2; T7.12 build gates (PER-20) → BUILD §5 |
| T8 (T8.1-T8.10) | Units | FINAL_DESIGN §6.1; T8.10 build gate (UNIT-14) → BUILD §5 |
| T9 (T9.1-T9.9) | Slice & member at write time | FINAL_DESIGN §5.2 |
| T10 (T10.1-T10.8) | XBRL concept link | FINAL_DESIGN §8; rollout/veto build → BUILD §5 gate 4 |
| T11 (T11.1-T11.11) | Producer interface contract | FINAL_DESIGN §4.2 (T11.1 real-fact gate; T11.2 who-fills-what: channel submits raw, the core alone fills state+numbers after the gate — contract side: ChannelContract §1 "never creates, never names, never decides identity" + §4 never-send list) · §5.1 (T11.3 fusion + basis hint) · §6.1/§7.1 (T11.5 hints, T11.8 %-guidance basis, T11.10 rate-vs-level) · §9 (T11.4 slices-beat-mixed · T11.6 chronological processing + the code-served strict-`<` PIT prior view, guidance-lane-only, with §4.3's no-graph-read rule — contract side: ChannelContract §5 "submit events chronologically per company" · T11.7 fan-out · T11.9 policy routing · T11.11 one-update-per-source-time-statement, trajectory always derived never stored — writer-side law only, no contract-side content by design) · BUILD §5 (CLI order + PIT prior view) |
| T12 (T12.1-T12.9) | Read contract | FINAL_DESIGN §9; T12.6 series_unit law also §6.1 |

**External inbound citations (link sweep EXECUTED at Phase-5 step 8, 2026-07-16; repo-wide scan clean):** 12 files
cite exact FinalDesign filenames — the experiments board/handover/exhibits/keys/harness plus the engine prompts
`workflows/menu_build.js`, `reconcile.js`, `gate.js` (re-pointed: labels name FINAL_DESIGN §3 as authority with
archived-02 provenance; runtime archive reads removed round 22; NAME-17 synced to OD-21 round 23 — rulebook-sync
test `workflows/tests/test_rulebook_sync.py` guards drift; the Track A implementation gate — BUILD §4 — governs
any future run: verify every rule-bearing component vs the then-current law + a pinned current-law certification;
the old Restaurant runs' RULE-BEARING outputs are historical evidence only, with the raw-text chunk copies
excepted where the WorkOrder pins them — the exact scoping lives in BUILD §4). Stem scans reach 21; bare-word 22 incl. one `INDEX.md` name-collision
false positive. Both scans were re-run at the Phase-5 move (2026-07-16); every hit updated or validated — the
repo-wide broken-reference scan came back clean (card step 8).

## 8. Archive manifest + evidence pointers

- **The archive's contents, exactly (two distinct kinds — never conflate):** (a) **32 SOURCE COPIES** = 29
  source originals + 3 pre-amendment/frozen-original snapshots; (b) **EVIDENCE FILES, which are NOT source
  copies** = the audit file `CONSOLIDATION.md`, `MANIFEST.json`, `README.md`, and the `READER_TEST_RECORD_*`
  files. Source 33, the byte-pinned `FableExperimentPlan.md`, remains at the root (manifest-verified in place).
- **Freeze manifest:** `archive/2026-07-15_pre-consolidation/MANIFEST.json` — all 33 sources sha-256-pinned
  (11,320 lines / 1,362,208 bytes verified), git provenance, commits `49f1cd8`/`87bc150`. Owner-amended
  live-continuing files verify against post-amendment hashes: ChannelContract (see git for current after the
  2026-07-15 provenance one-liner) · packet `aa7239ed…`
  (recorded in the archived `CONSOLIDATION.md` §16).
- **Evidence/rejected-alternative pointers:** v1/v2 death evidence, unit proofs (117/117 · 29/29+7 · 3×33/33),
  concept-link proofs (31-co zero-wrong · 274-co 100%/~70%/98% + caveat) → BUILD §12. Bayes proposal → BUILD
  §8.3. Executed prompt briefs (FablePrompt/v2) → archive provenance. Experiment artifacts + signed decisions →
  `.claude/plans/Drivers/experiments/`. Relocation/harvest engine state (separate track) →
  `scripts/driver_seed/relocate_probe/STATE.md`.
