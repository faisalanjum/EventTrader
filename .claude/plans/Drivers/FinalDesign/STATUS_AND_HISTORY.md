# STATUS_AND_HISTORY.md — the one mutable dashboard, supersession ledger, and crosswalk

> **Status: LIVE — consolidation Phases 1-5 EXECUTED (owner GO 2026-07-16); the definitive reader test's outcome, per-question grades, and tested hashes live in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run9.md` — Phase 5 is COMPLETE ONLY IF that exact record shows 10/10 PASS. Review rounds + decision trail = the archived `CONSOLIDATION.md` §10.2/§16.** This file owns STATUS and HISTORY only — live rule
> wording stays in `FINAL_DESIGN.md`; procedures stay in `BUILD_AND_OPERATIONS.md`; channel duties stay in
> `ChannelContract.md`. Any status shown in another live file is a generated summary of THIS file. A status
> change edits this dashboard — and only if rule meaning changed through owner approval, the one owning rule
> section plus a new supersession row here.
>
> **Reading order (front door = `FINAL_DESIGN.md`):** FINAL_DESIGN → ChannelContract (adapters only) →
> BUILD_AND_OPERATIONS (builders/operators) → this file (what is open, replaced, or archived). Temporary fifth
> live file: `15_CandidateFactPacket.md` (owner-frozen v1.0 + the two 2026-07-15 owner amendments Q4/Q1-ext,
> current sha `aa7239ed…`).

## 1. One-page dashboard (2026-07-16)

| Layer | Design | Code | Tests | Production run |
|---|---|---|---|---|
| Rule meaning (FINAL_DESIGN §1-§9) | FINAL (locked set + 5 owner rulings 2026-07-15) | — | — | — |
| Track A catalog engine | FINAL | PARTIAL (WP-FC-EDITS `5db902f` + rounds 22-23 prompt sync; implementation gate in BUILD §4 governs any run) | 265 pass + 1 skip (2026-07-16, incl. the strengthened rulebook-sync guard in `workflows/tests/`) | NEVER RUN (no graph catalog; fitness gate never run; old June RULE-BEARING outputs = historical evidence only, chunk copies excepted per BUILD §4) |
| Fiscal.ai channel adapter (S1) | FINAL | BUILT | smoke 16 packets / 175 items, 0 tokens | not live |
| Track B fact stack | FINAL (all decisions made; affected contracts NOT implementation-ready — BUILD §11 gaps) | UNBUILT (S3 awaits owner GO) | — | — |
| Track C guidance retirement | FINAL v2.0 (no replay) | not started | — | — |
| Concept linker (text facts) | FINAL | PARTIAL (vetoes C/D + PIT query spec-only) | 31-co + 274-co evidence | not rolled out |
| Admission kernel | **APPROVED WORKING DESIGN (owner 2026-07-15; not activated)** | — | gates in force; integration COMPLETE (BUILD §8.1; original archived) | — |
| XBRL-native materializer | **APPROVED WORKING DESIGN (owner 2026-07-15; DORMANT until P19 enablement + hard pre-gates + EXP-6)** | — | EXP-1 signed | — |
| Experiment program | EXP-0/1/2 SIGNED PASS | — | — | EXP-3..6 / WP-FC-RUN PENDING |
| Running layer (schedules/ledger/QA) | NOT designed-complete | — | — | — |
| Consolidation itself | Phases 1-5 EXECUTED (owner GO 2026-07-16); all 33 sources accounted for byte-verified (29 originals + 3 snapshots archived; the byte-pinned Plan at root); audit trail = the archived CONSOLIDATION.md | — | definitive blank-context reader test: outcome + per-question grades + authoritative tested hashes in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run9.md` — Phase 5 COMPLETE only if that record shows 10/10 PASS | root = the 7 sanctioned files + archive/; Plan + WorkOrder stay until the experiment program migrates |

## 2. Lists by status

- THIS file owns the status lists (one-copy law); `FINAL_DESIGN.md` §10 is the GENERATED mirror. The master lists:
- **FINAL / BUILD-PENDING:** Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 production wiring · PER-20 resolver build + 21 tests · slice table materialization + PIT menu code · concept-linker vetoes C/D + PIT query build · the whole Track B writer/validator/CLI/park-ledger stack · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh.
- **DESIGN-INCOMPLETE:** the production running layer (BUILD §7's runbook list). The OD-5 change scanner is a recommendation only.
- **CONDITIONAL:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (RATIFIED as design 2026-07-15; DORMANT until the P19 enablement proof plan — X-XL0-3 bars — every hard pre-gate pass, and the EXP-6 convergence evidence) · multi-run concept stability/caching (only if monitoring justifies).
- **OPEN (owner):** catalog 796-vs-786 + lifecycle/IPO · full model/cost policy beyond signed EXP-2 · FS-23 · 8-K taxonomy · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement (part-2/news-channel).
- **APPROVED WORKING DESIGN (owner 2026-07-15; not activated; gates/OFF-switches in force):** Admission Kernel v3.4 · XBRL-native materializer — integration COMPLETE (INT-2..INT-5, destination proof §7.1b); both originals archived 2026-07-15, byte-verified vs the Phase-1 manifest. The kernel bundle also settled two formerly-open/tracked items: G1 reuse-display rules (→ BUILD §8.1.3) · OD-7's born-complete/live-create CORE (→ BUILD §8.1; the broader OD-7 design stays UNRATIFIED — FINAL §4.2 Q5 note; the mis-name/mis-type exit + exact recipes land at the future OD-7 pass, BUILD §11.2).
- **CANDIDATE:** Bayes proposal · Driver Genesis restructure (rationale). Owner-question decision record = §4 below; the full decision text + verification trail = the archived `CONSOLIDATION.md` §10.2/§16 (`archive/2026-07-15_pre-consolidation/`).
- **Change law (owner 2026-07-15):** every future design correction updates the ONE owning live section and adds a short history entry here; no parallel live copies.
- **RETIRED (never a production path):** old Guidance replay plan (`13_Track_RetiredDesign.md` — GI stale-trap
  rows in its GI-07) · fixed-vocabulary Driver v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range`
  scope value · `gp_UNDEF` quiet fallback · `evhash16` on DriverUpdate · FS-22 cross-company recurrence ·
  RavenPack import · catalog-first live reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all
  catalog sync (owner ruling 2026-07-15, Q3).

## 3. The 42 supersession rows (terse; dead rule kept once for audit; current wording ONLY at the anchor)

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

## 4. Owner rulings record (2026-07-15)

Q1 `company_confirmed`: CORE derives from who-said-it evidence; unclear = SKIP (ruling's own content); `false`
stays reserved for explicitly-ALLOWED future third-party classes (enabling any class = part-2/news-channel
decision) → FINAL_DESIGN §7.1. · Q2 non-slice/elimination: NO change — frozen packet PARK+log stands; FS-20
auto-demotion is the drain → §3 OD-17. · Q3 catalog sync: resolution (b) — offline catalog + lazy born-complete
nodes (created in the same write when an ATTACH targets a card with no node yet — mechanics TO BE specified at
the future OD-7/live-admission pass, recipe not yet written, BUILD §11.2); OD-16 narrowed → §4.2. · Q4 XBRL packet shape: amendment APPLIED 2026-07-15 to ChannelContract + frozen
packet (`dimensions=[]` verified-empty; both axis+member; never fragments). · Q5 first-fact guard scoped to
bare names; suffix-proven lanes may be born `unknown` → §4.2. · R6 (round 16) `xbrl_internal_conflict` retry
trigger: retry ONLY when the affected report's parsed XBRL facts actually change; an amended filing is a NEW
report, never a silent rewrite → BUILD §8.2 recipe step 4. Full decision text + verification trail:
the archived `CONSOLIDATION.md` §10.2/§16 (`archive/2026-07-15_pre-consolidation/CONSOLIDATION.md`, archived at Phase-5 step 7, 2026-07-16).

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
- Missing build recipes (packet lifecycle · born-complete transaction · ID namespaces · machine contracts):
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
| 90_OpenItems · 95_Supersession · 99_Codex audit | status · 42-row ledger · history | this file §1-§3; archive (99 wholesale) |
| BayesProposal | unvetted proposal | BUILD §8.3 pointer; archive under proposals |
| ChannelContract | ACTIVE live file | kept — the SOLE public channel authority under the one-copy law; banner amended 2026-07-15 (owner batch: XBRL row, evidence row, provenance one-liner replacing the old "source of truth" phrasing); current sha tracked in git + CONSOLIDATION §16 hash freeze |
| DriverGenesisRestructure | unapproved rationale | open charter questions in FINAL_DESIGN §10; archive |
| DriverPlan.html | stale study export | none (regenerate later from live docs); archive |
| FableAdmissionKernelDesign | **RATIFIED working design (owner 2026-07-15; not activated)** | full mechanics → BUILD §8.1 + law-grade parts → FINAL_DESIGN (destination proof §7.1b); **original ARCHIVED 2026-07-15, byte-verified — DONE** |
| FableContextPack · WorkflowContextPack | stale navigation/code maps | archive (Workflow pack: after live-code re-audit + link repair) |
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
| 42 supersession rows | §3 above | — |
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
