# STATUS_AND_HISTORY.md — the one mutable dashboard, supersession ledger, and crosswalk

> **Status: PROVISIONAL LIVE (Phase 3, 2026-07-15).** This file owns STATUS and HISTORY only — live rule
> wording stays in `FINAL_DESIGN.md`; procedures stay in `BUILD_AND_OPERATIONS.md`; channel duties stay in
> `ChannelContract.md`. Any status shown in another live file is a generated summary of THIS file. A status
> change edits this dashboard — and only if rule meaning changed through owner approval, the one owning rule
> section plus a new supersession row here.
>
> **Reading order (front door = `FINAL_DESIGN.md`):** FINAL_DESIGN → ChannelContract (adapters only) →
> BUILD_AND_OPERATIONS (builders/operators) → this file (what is open, replaced, or archived). Temporary fifth
> live file: `15_CandidateFactPacket.md` (owner-frozen v1.0 + the 2026-07-15 Q4 amendment, sha `038a0f89…`).

## 1. One-page dashboard (2026-07-15)

| Layer | Design | Code | Tests | Production run |
|---|---|---|---|---|
| Rule meaning (FINAL_DESIGN §1-§9) | FINAL (locked set + 5 owner rulings 2026-07-15) | — | — | — |
| Track A catalog engine | FINAL | PARTIAL (WP-FC-EDITS `5db902f`) | 260 pass + 1 skip | NEVER RUN (no graph catalog; fitness gate never run) |
| Fiscal.ai channel adapter (S1) | FINAL | BUILT | smoke 16 packets / 175 items, 0 tokens | not live |
| Track B fact stack | FINAL (all decisions made; affected contracts NOT implementation-ready — BUILD §11 gaps) | UNBUILT (S3 awaits owner GO) | — | — |
| Track C guidance retirement | FINAL v2.0 (no replay) | not started | — | — |
| Concept linker (text facts) | FINAL | PARTIAL (vetoes C/D + PIT query spec-only) | 31-co + 274-co evidence | not rolled out |
| Admission kernel | accepted parts FINAL; bundle CANDIDATE | — | — | — |
| XBRL-native materializer | CANDIDATE (dormant + `09` rider dormant) | — | EXP-1 signed | — |
| Experiment program | EXP-0/1/2 SIGNED PASS | — | — | EXP-3..6 / WP-FC-RUN PENDING |
| Running layer (schedules/ledger/QA) | NOT designed-complete | — | — | — |
| Consolidation itself | Phase 3 files written | — | Phase 4 §14 checks PENDING | archive (Phase 5) pending |

## 2. Lists by status

- **FINAL / BUILD-PENDING · CONDITIONAL · OPEN(owner) · CANDIDATE:** the authoritative tag lists live in
  `FINAL_DESIGN.md` §10 (generated from this file's rows). Owner-question detail: `CONSOLIDATION.md` §9.2/§10
  until Phase 5, then here.
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
| 34 | Guidance history | store derived movement | §9 (read-derived) |
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
OD-6 fitness gate (BUILD §4) · OD-7 broader live admission = tracked recommendation only · OD-8 (§5.1) ·
OD-9..15 (§5.3/§6.1/§4.3) · OD-16 resolved 2026-07-15 → lazy born-complete (§4.2) · OD-17 (§3) · OD-18 (§5.4;
CLAIM separate, ships off) · OD-19 (§5.4) · OD-20 (§5.4) · OD-21 (§5.1/§6.2/§7) · frozen packet v1.0 + Channel
Contract v1.0 (boundary files) · Track C full no-replay reversal (BUILD §6).

## 4. Owner rulings record (2026-07-15, all five §10.2 questions)

Q1 `company_confirmed`: CORE derives from who-said-it evidence; unclear = SKIP (ruling's own content); `false`
stays reserved for explicitly-ALLOWED future third-party classes (enabling any class = part-2/news-channel
decision) → FINAL_DESIGN §7.1. · Q2 non-slice/elimination: NO change — frozen packet PARK+log stands; FS-20
auto-demotion is the drain → §3 OD-17. · Q3 catalog sync: resolution (b) — offline catalog + lazy born-complete
nodes; OD-16 narrowed → §4.2. · Q4 XBRL packet shape: amendment APPLIED 2026-07-15 to ChannelContract + frozen
packet (`dimensions=[]` verified-empty; both axis+member; never fragments). · Q5 first-fact guard scoped to
bare names; suffix-proven lanes may be born `unknown` → §4.2. Full decision text + verification trail:
`CONSOLIDATION.md` §10.2/§16 (moves to the archive with it at Phase 5).

## 5. Signed experiment decisions + remaining gates (authority = signed decision.json artifacts)

EXP-1 PASS 07-09 (O13 dimension binding owner-ratified) · EXP-0 PASS 07-10 (grader = 2× `claude-sonnet-5`
@effort=high; the (model,effort) pair binds) · WP-FC-EDITS `5db902f` 07-10 · WP-FA + O2 signed 07-10 · K-reader
v3 LOCKED 07-10 · EXP-2 PASS 07-11 (sonnet-5@high/40k/1-run) · PENDING: EXP-3..6, remaining keys, WP-FC-RUN,
F-C freeze. Standing gates: ra_0007 kernel-§6.1 review BEFORE K-pairs.v2; Plan sha `51966848…7472` byte-pinned;
WorkOrder current sha `4911a22f…` (status board stale at `1586761a…` — fix before next run). Artifacts:
`.claude/plans/Drivers/experiments/`.

## 6. Known documentation/logic issues (open; no new authority)

- The 24 stale-text items (per-file) and the interim hazard rule: `CONSOLIDATION.md` §10.1 + Phase-2 note.
  Biggest traps: `03`/`11`/`12` old collision text (OD-8 is current) · `04` one-hint-pair (per-slot is current) ·
  `09 §8`/`07 §D` expectation-baseline wording · stale experiment headers (signed artifacts win) ·
  `15` "already built" = "fully specified" (stale-item 11).
- Missing build recipes (packet lifecycle · born-complete transaction · ID namespaces · machine contracts):
  BUILD §11.
- Truly open owner choices: FINAL_DESIGN §10 OPEN list.

## 7. Source crosswalk (33 files → destinations; every row re-verified at Phase 4/5)

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
| 15_CandidateFactPacket | FROZEN v1.0 + Q4 amendment | temporary fifth live file (sha `038a0f89…`) |
| 66_IssuesToBeHandled | owner blocks + stale tail | rules → FINAL_DESIGN; status here; archive |
| 90_OpenItems · 95_Supersession · 99_Codex audit | status · 42-row ledger · history | this file §1-§3; archive (99 wholesale) |
| BayesProposal | unvetted proposal | BUILD §8.3 pointer; archive under proposals |
| ChannelContract | ACTIVE live file | kept (amended 2026-07-15, sha `4fdeb821…`) |
| DriverGenesisRestructure | unapproved rationale | open charter questions in FINAL_DESIGN §10; archive |
| DriverPlan.html | stale study export | none (regenerate later from live docs); archive |
| FableAdmissionKernelDesign | candidate + accepted inserts | FINAL_DESIGN §4/§5 (accepted) + BUILD §8.1; archive after exact candidate map preserved |
| FableContextPack · WorkflowContextPack | stale navigation/code maps | archive (Workflow pack: after live-code re-audit + link repair) |
| FableExperimentPlan · WorkOrder | pinned plan · runbook | BUILD §9; keep Plan byte-identical until program migrates; archive after |
| FablePrompt · FablePromptv2 | executed briefs | provenance entries only; archive |
| XBRLIntegrationDesign | pending candidate | BUILD §8.2; archive once exact candidate map preserved |
| CONSOLIDATION.md | audit + migration map | moves into the same dated archive after the four live files pass review (never a fifth rule source) |

**External inbound citations (verified 2026-07-15):** 12 files cite exact FinalDesign filenames — the
experiments board/handover/exhibits/keys/harness plus the engine prompts `workflows/menu_build.js`,
`reconcile.js`, `gate.js` (their inlined rulebooks cite `02_DriverCatalog.md` as verbatim provenance — keep
resolvable or re-point in the same change). Stem scans reach 21; bare-word 22 incl. one `INDEX.md` name-collision
false positive. Re-run both scans at migration; update or validate every hit BEFORE moving sources.

## 8. Archive manifest + evidence pointers

- **Freeze manifest:** `archive/2026-07-15_pre-consolidation/MANIFEST.json` — all 33 sources sha-256-pinned
  (11,320 lines / 1,362,208 bytes verified), git provenance, commits `49f1cd8`/`87bc150`. Owner-amended
  live-continuing files verify against post-amendment hashes: ChannelContract `4fdeb821…` · packet `038a0f89…`
  (recorded in `CONSOLIDATION.md` §16).
- **Evidence/rejected-alternative pointers:** v1/v2 death evidence, unit proofs (117/117 · 29/29+7 · 3×33/33),
  concept-link proofs (31-co zero-wrong · 274-co 100%/~70%/98% + caveat) → BUILD §12. Bayes proposal → BUILD
  §8.3. Executed prompt briefs (FablePrompt/v2) → archive provenance. Experiment artifacts + signed decisions →
  `.claude/plans/Drivers/experiments/`. Relocation/harvest engine state (separate track) →
  `scripts/driver_seed/relocate_probe/STATE.md`.
