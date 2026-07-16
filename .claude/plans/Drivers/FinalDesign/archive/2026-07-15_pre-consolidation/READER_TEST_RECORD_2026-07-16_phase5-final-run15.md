# READER TEST RECORD — 2026-07-16 — Phase-5 FINAL / FINAL-CLOSURE run 15 — **PASS 10/10** — RETIREMENT RECORD

**THE definitive Phase-5 + final-closure record.** One fresh R7-amended blank-context reader test against ONE
committed seven-file freeze, per the owner's final-closure directive (verbatim below). Verdict: **PASS 10/10**,
**7/7 exact hashes** (pre-run pinned + post-run re-verified), battery **7/7 GREEN with explicit per-command
exit-status checks**. The documentation track **RETIRES** with this record.

- Grading law (LOCKED, unchanged): the most-natural parse governs; a false fact on that parse = FAIL; no rescue
  readings; plus the full accumulated checklist (every constructed fact — including homes — names its
  driver_state; every stated value enumerated; no conditional-emphasis inversions; exact counts/locations never
  compressed; six-dimension home-match verification; cite the clause whose condition the fixture satisfies).
- Records are append-only; this file is new and unique; run 1-14 records are preserved beside it.
- **Run 14 status (owner):** qualified historical evidence — its own addenda carry the retraction (parallel
  S3.1 changes were substantive; run 14 was not a valid frozen snapshot) and the qualification. Nothing here
  rewrites it.

## 1. Owner final-closure directive (verbatim, 2026-07-16)

> Core Steps 1–3 are committed at 12c38be203e6381bfba7e18029c7278548918030. Step 4 is paused.
>
> Starting from that commit, perform the final closure only:
>
> 1. Reject the proposed three-file-only hash rule. Every reader test must pin every file it reads.
> 2. Record that routine build/status progress does not require a full rerun; rules, contracts, operative
>    mechanics, gates, owner decisions, crosswalks, and major handoffs do.
> 3. Prepare the final record pointers, commit that seven-file freeze, and record its commit SHA.
> 4. Run one fresh R7-amended test against exactly that committed snapshot.
> 5. Require 10/10, 7/7 exact hashes, explicit command-exit checks, Plan pin, WorkOrder/board, manifest, root
>    layout, and suites.
> 6. Add the new record without changing the tested seven files, commit, push, and retire.
>
> Preserve run 14 as qualified historical evidence. Touch only consolidation files and never sweep unrelated
> changes.

Both directive-step-1 and step-2 policies are recorded as owner ruling **R8 in STATUS_AND_HISTORY §4**, INSIDE
the tested freeze (so the certified files themselves carry the standing policy).

## 2. The tested snapshot — ONE fixed commit

- **Freeze commit (certification binds to this): `5d0bd41b6df15329697b1634a30f0a30f08da21f`**
  ("SEVEN-FILE FREEZE for the final R7 reader test ..."), pushed to origin/main before the test ran.
- Parent: `12c38be203e6381bfba7e18029c7278548918030` — the core session's S3 steps 1-3 commit the directive
  told us to wait for (BUILD §5 ID-shape entry + §11.3 closed + STATUS S3-GO entry are IN the tested bytes).
- Freeze content: banners/pointers in FINAL_DESIGN, BUILD, STATUS + the archive README re-pointed to THIS
  record's exact filename; STATUS §4 gains ruling R8. 4 files changed, 7 insertions(+), 7 deletions(-) —
  surgical add, nothing else swept.
- Test medium: detached git worktree at the freeze commit (bytes physically immovable by any live session):
  `scratchpad/final-run-worktree`. Worktree HEAD verified `5d0bd41...` pre-run, post-run, and by the battery;
  `git status --porcelain` in the worktree: clean (pre- and post-run).

### 2.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; re-verified AFTER)

```
d77444685b0b40f737b581e1b7bab3369f7b5d9e21eb6d2e97b57c5bb2409d26  FINAL_DESIGN.md
9e6ffcbbcbc1a34e3792a1afa37469915ddfe02cbeac20c978cdd09b89292cea  ChannelContract.md
b0013f267c48779e0ecb1201b81bba21207d7522359f2297e02ea5881dbd956e  BUILD_AND_OPERATIONS.md
f9c11a6a491169c9cccca3c02d5b2c2e291bf8836991528eb50ff466edbdca98  STATUS_AND_HISTORY.md
aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c  15_CandidateFactPacket.md
51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472  FableExperimentPlan.md
57a6b86090083560af476f23125a2f95bbce2e572bb93cc132e9ed6cdff9033e  FableExperimentWorkOrder.md
```

Post-run re-verify: `sha256sum -c` → all seven `OK` (**7/7 MATCH**, exit-status-checked). The Plan hash equals
its standing byte-pin `51966848...ed7472`; the WorkOrder hash equals the board-recorded current sha
`57a6b860...033e` and appears verbatim on `experiments/WORKORDER_STATUS.md` — both also asserted by the battery.
The packet sha the reader itself quoted from the frozen files (`aa7239ed...`, answer 8) equals pin #5 —
an independent internal cross-proof.

## 3. Battery — 7/7 GREEN, every check tests its own exit status

Design note (closes the run-14 hole permanently): run 14's battery used `diff ... && echo OK` lists, which
`set -e` exempts — a failing diff continued silently. This battery routes EVERY check through a `ck` helper
that captures the command's own exit code (`out=$("$@" 2>&1); rc=$?`) and fails loudly on rc != 0; the script
exits nonzero if any check fails. No list-exemption path exists.

```
== worktree HEAD: 5d0bd41b6df15329697b1634a30f0a30f08da21f ==
PASS: 1. 7/7 pinned hashes (sha256sum -c, exit-checked)
PASS: 2. Plan byte-pin (51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472)
PASS: 3. WorkOrder sha == board-recorded current sha (57a6b860...) AND appears on the board
PASS: 4. Manifest 33/33 byte-verified (29 archived originals + 3 snapshots + Plan at root)
PASS: 5. Root layout = exactly the 7 sanctioned files + archive/
PASS: 6. Workflow drift-guard suite (rulebook sync + all workflow tests)
PASS: 7. Driver core suite at the freeze commit (S3 substrate)

BATTERY: ALL 7 CHECKS GREEN
```

Suite counts at the freeze commit: workflows `265 passed, 1 skipped`; driver core `111 passed`.
Manifest check mapping: each of the 33 MANIFEST.json entries verified byte-for-byte at its CURRENT location —
29 at `archive/<basename>`, the 3 frozen snapshots (`ChannelContract.pre-amendment.md`,
`15_CandidateFactPacket.pre-amendment.md`, `FableExperimentWorkOrder.md` [pre-21c original]), and the
byte-pinned Plan at the live root.

## 4. Execution trail

- Reader: one blank-context subagent (claude-fable-5), workflow run `wf_c6e61a68-f65`, agent `a24987ee04c81828b`,
  202,016 tokens, 11 tool uses (file reads), 411.5s, first answering attempt — graded on its first produced
  output. Script (persisted): `workflows/scripts/final-r7-retirement-run-wf_0152344c-de6.js` (session dir).
- Two earlier attempts produced NOTHING (API `529 Overloaded`, zero subagent tokens, zero tool uses — no
  partial reads, no answers): one pre-directive attempt aimed at `12c38be` (superseded by the owner's
  final-closure message and stopped), one at the freeze worktree. Neither influences grading.
- **Label integrity note:** the workflow's cosmetic meta description still reads "commit 12c38be" — it was
  authored before the owner's directive changed the target and lives outside the prompt. The PROMPT contains
  only the worktree file paths; the worktree's verified HEAD at pin-time, run-time, and post-run is
  `5d0bd41...`. Certification binds to `5d0bd41b6df15329697b1634a30f0a30f08da21f`, not to the label.
- **Pointer-before-record sequence (owner-ordered):** the freeze commit's banners name THIS record file, which
  did not yet exist at that commit — exactly the directive's sequence ("Prepare the final record pointers,
  commit that seven-file freeze ... Add the new record without changing the tested seven files"). No exercise
  reads the record file; this record lands in a LATER commit that touches none of the seven tested files
  (verified by `git diff 5d0bd41..HEAD -- <the seven>` = empty at write time).

## 5. The exact prompt

Constructed by the persisted workflow script as the newline-join of these lines, with
`DIR = <worktree>/.claude/plans/Drivers/FinalDesign` (the seven numbered files at their WORKTREE paths).
Preamble and questions are byte-identical to run 14's R7-amended official set (R7: Q3 amended; preamble and
all other questions unchanged):

```
You are a brand-new engineer with ZERO prior context. Your ONLY permitted sources are these SEVEN files (read fully; open NOTHING else — nothing in archive/, no other repo files):
1. <DIR>/FINAL_DESIGN.md
2. <DIR>/ChannelContract.md
3. <DIR>/BUILD_AND_OPERATIONS.md
4. <DIR>/STATUS_AND_HISTORY.md
5. <DIR>/15_CandidateFactPacket.md
6. <DIR>/FableExperimentPlan.md
7. <DIR>/FableExperimentWorkOrder.md
Answer ALL TEN official exercises, terse, each answer with file+section cited. A documented-open-gap or owner-ruled answer (with citation) is CORRECT; never guess. Distinguish a file DESTINATION from its CURRENT location. Answer EVERY part of every question explicitly — an unstated required element is a wrong answer; where a rule has multiple cases, state EVERY case; when you state a universal rule that has a documented exception, state the exception; quote counts and file locations exactly as the files state them, never compress them; EVERY constructed example must name its own driver_state; when you cite a rule as the mechanism for a step, cite the clause whose condition the fixture actually satisfies.
1. Explain Driver versus DriverUpdate and the over-merge safety law.
2. Take one source quote through channel, decomposition, name/slice/measurement/unit/period, identity, validation, write, and read (official fixture: "Q3 iPhone revenue rose 12% year-over-year to $42.6B" from an 8-K).
3. Construct one metric, guidance, actual surprise, guidance-vs-consensus surprise, and action example without violating a lane (driver_state + the FORBIDDEN fields per lane). For each surprise, construct its required same-event home fact, state the home's driver_state, and show the required family, period, period scope, slice, measurement, and normalized value/unit match.
4. Derive the scope slot order and the collision signature (when quote_hash appears; the ten hashed slots exactly).
5. List all 24 fields and identify code versus semantic ownership.
6. Explain why own parts are slices, external causes stay in names, and portions stay in names.
7. Explain why concept/member links may be absent and why wrong links are worse.
8. Distinguish the raw channel submission from the internal Candidate Fact Packet.
9. Identify what is final-but-unbuilt, design-incomplete, conditional, approved-working-design, candidate, open, retired, and historical.
10. Find every original source and its replacement anchor without opening chat history: name the file+sections that map every source file, rule-ID range, T-group, and transferred ratified-design element.
Final message = the ten numbered answers only.
```

## 6. The reader's ten answers — VERBATIM (spliced byte-identically from the workflow output JSON by script)

1. **Driver vs DriverUpdate; the one law.** A **Driver** is one reusable, atomic cause or standing thing that can matter to a company or market — a class node: name + permanent `fact_type` + `SAME_AS`/`BASE_METRIC` links + birth evidence. A **DriverUpdate** is one real, source-backed occurrence of that Driver in one source event — the fact node (FINAL_DESIGN §0). **The one law (asymmetric):** merging different meanings causes permanent damage; keeping the same meaning separate is repairable — **when unsure, keep separate**. True duplicates stay recoverable through reversible `SAME_AS`; nodes and facts are never deleted or re-keyed to make history look cleaner (FINAL_DESIGN §1). The narrowed claim scope: the writer guarantees "conflicting values never silently overwrite," NOT "over-merge impossible" — identity-level over-merge is guarded by kernel judges + falsifier + audits with measured upper bounds (15_CandidateFactPacket Part C ⑤; BUILD §8.1 §16 residuals).

2. **"Q3 iPhone revenue rose 12% year-over-year to $42.6B" (8-K), end to end.**
– **Channel** (ChannelContract §1–§3): fetch-only; one packet per source event; envelope `source_id`=the 8-K accession (must exist in Neo4j, else PARK-RETRY), `source_type=8k` (the TRUE document), ticker, `fye_month`, `event_time`; raw item = verbatim quote, `raw_label_or_claim`, SIGNED unscaled values (42.6 + raw "$B"; 12 + "%"), period signals (stated "Q3", cadence signal, adjacent wording). Never sent: names, ids/fact_scope, fiscal fields, measurement tokens, canonical units, computed numbers (§4) — sent anyway ⇒ ignored and recomputed.
– **Decomposition** (15_CandidateFactPacket Part B; BUILD §2): step 0 strip direction word "rose" (NAME-11 step 0); step 1 measurement peel → ∅ (never assume GAAP); step 2 per-X → none; step 3 portion → none; step 4 name-vs-slice local role test (NAME-10/11): iPhone = own product → `slice=product:iphone` (text-only here, so the producer proposes the kind via the FS-15/FACT-26f ladder — menu-match first), residual "revenue"; step 5 name = `revenue`; step 6 fact_type = `metric` (DU-05 standing variable; a reported KPI value → metric); step 7 units.
– **State/values:** `driver_state=increased` (DU-09 first match: stated direction — FINAL_DESIGN §4.3); `level_low=level_high=42600`, `level_unit=m_usd` (glued billions → m_usd ×1,000, §6.1; V2 resolver scales, sign untouched), `level_shape_hint=point`; `change_value=+12`, `change_unit=percent_yoy` (OD-11: YoY/comparable/annual growth → `percent_yoy` — explicit "year-over-year" here, not the bare-growth default); `comparison_baseline=prior_year` (headline temporal comparison, §7.1; expectation baselines forbidden on metric, §7.2).
– **Period:** shared fiscal resolver (quarter branch, needs `fye_month`; missing fails closed) → real Q3 window → `gp_<start>_<end>`; `period_scope=quarter`; `time_type=duration` (REQUIRED semantic output, never a default) (§6.2; PER-18 MERGE write shape).
– **Identity:** admission first — reuse existing `revenue` (exact ATTACH) or CREATE born-complete with this first fact (§4.2; first-fact pin satisfied: bare name, state≠unknown). Code builds `id = du:{safe_source_id}:revenue:{fact_scope}`, `fact_scope = period=<gp_id>|slice=product:iphone` (measurement absent → omitted; never `slice=total`) (§5.1; BUILD §5 ID law). Fuse same-event pieces, then OD-8 probe vs the PRE-BATCH graph: no sibling → the fact stays bare, no `quote_hash`.
– **Validation** (BUILD §5): lane matrix (metric forbids `surprise=`, value_text, conditions, company_confirmed), state-in-lane, shape-hint cross-check then discard, sign validator (`increased` ⇒ positive change), unit/per-X lint, period-edge/scope symmetry both ways, quote required.
– **Write:** atomic MERGE on id; `created` on create; no null-clobber; dry-run default, writes need the explicit environment gate; code-6 stamped (`id·fact_scope·series_unit·created·date·source_type`); `series_unit=m_usd` (OD-10, level-bearing); edges `OF_DRIVER`/`FROM_SOURCE`/`HAS_PERIOD` (§7.3). Enrichment: metric-only concept link (guards→PIT menu→pick→verify→veto→`xbrl_qname`+`MAPS_TO_CONCEPT`, else abstain) (§8).
– **Read:** grouped by the full series key (company·driver·fact_type·slice·resolved period·period_scope·measurement·series_unit·time_type), render level→signed change→comparison→quote; same-day source rank `8k > transcript > 10q > 10k > news`; PIT backtest strict `date < as_of`; results labeled raw/reconciled (§9).

3. **Five lane-legal examples** (forbidden fields per lane = FINAL_DESIGN §7.2; home law = §5.1):
– **Metric:** `revenue`, `driver_state=increased` (the Q2 fixture). FORBIDDEN: `surprise=` slot · value_text · conditions · company_confirmed · expectation baselines (`comparison_baseline` limited to prior_year/sequential). Direct XBRL allowed by enrichment.
– **Guidance:** `revenue_guidance` (suffix fixes fact_type; exactly one `BASE_METRIC→revenue`), quote "raising FY2026 revenue guidance to $180–184B" → `driver_state=raised` (stated movement), target period FY2026 REQUIRED, `period_scope=annual`, `company_confirmed=true` REQUIRED on every stored guidance fact (core-derived from who-said-it evidence — Q1 ruling). FORBIDDEN: consensus baseline · `surprise=` · direct XBRL (inherits via family). value_text/conditions allowed only under their exact rules (value_text numberless-only — absent here).
– **Actual surprise:** `eps_surprise` (`BASE_METRIC→eps`), quote "Q3 EPS of $2.10 beat consensus of $1.95" → `driver_state=beat`; scope `…|surprise=actual_vs_consensus` (code-composed pre-fusion: `surprise_basis_hint=actual` × REQUIRED `comparison_baseline=consensus`); level 2.10 usd, comparison 1.95–1.95, `change_value=null` (derivable). FORBIDDEN: value_text · conditions · company_confirmed · direct XBRL. **Home (same event, required — metric home):** `eps` fact, **home `driver_state=reported`** (bare stated actual; the co-stated expectation never rides the home — DU-15). Match: family (`eps_surprise→BASE_METRIC→eps`) ✓ · period = the same reported-Q3 `gp_` id (actual surprise uses the reported, ended period) ✓ · period_scope quarter=quarter ✓ · slice omitted=omitted ✓ · measurement ∅=∅ ✓ · normalized value/unit 2.10 usd = 2.10 usd ✓.
– **Guidance-vs-consensus surprise:** `revenue_surprise` (ONE surprise Driver holds all three types — NAME-17/OD-21), quote "guiding FY2027 revenue to $200B; Street consensus $190B" → `surprise=guidance_vs_consensus` (`basis_hint=guidance` × `comparison_baseline=consensus`); `driver_state=beat` via the wordless outside-range polarity proof (transient, discarded: polarity=higher-favorable, `basis=metric_meaning` — legal because revenue has no mainstream counter-story, §4.3); period = the guidance TARGET period FY2027 even if ended (OD-21). **Home (same event, required — guidance home):** `revenue_guidance` fact, **home `driver_state=unknown`** (bare guide, no stated movement; legal as a birth fact only because the lane is suffix-proven — §4.2 Q5 pin; readers derive `effective_driver_state`), `company_confirmed=true`. Match: family (both drivers `BASE_METRIC→revenue`) ✓ · period FY2027 target = FY2027 ✓ · period_scope annual=annual ✓ · slice omitted both ✓ · measurement ∅ both ✓ · value/unit 200,000 m_usd = 200,000 m_usd ✓.
– **Action:** `buyback` (OD-2 owner worked example → action_event), quote "board authorized a $1.8B repurchase program" → `driver_state=announced` (company's own stated action before completion), level 1800 m_usd (stated). No period edge (no real window stated — never force one; action sentinels hard-fail). FORBIDDEN: `surprise=` · value_text · conditions · company_confirmed · direct XBRL.

4. **Scope slot order + collision signature** (FINAL_DESIGN §5.1, OD-8; BUILD §5 ID law): canonical order, absent slots omitted: `period=<period_u_id>` | `slice=<code-sorted kind:value parts joined ";">` | `measurement=<normalized, code-sorted, comma-joined tokens>` | `surprise=<type>` (surprise lane only) | `quote_hash=<full sha256>` (rare collision member only). Never `slice=total`. **The ten hashed slots exactly:** `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions` — quote text, state, confirmation, producer, source type, date, and XBRL enrichment EXCLUDED. Preimage = fixed-order compact ASCII JSON array of canonical strings, null ≠ empty string, one text normalizer + one decimal canonicalizer (no exponent/trailing zeros, −0→0), full untruncated SHA-256. **When `quote_hash` appears** (decisions vs the PRE-BATCH graph; minted ONLY in the hash cases): NO sibling → post-fusion fact stays bare, but multiple initially pairwise-conflicting in-batch facts are ALL hashed; ONE sibling → compatible fills (no null-clobber), conflict → flagged hashed member; MULTIPLE siblings → exact MERGES, conflict-with-ALL → hashed member, compatible-but-not-exact PARKS; two in-batch competitors for one partial sibling → park BOTH. At most one bare member per group; members must pairwise conflict on ≥1 shared non-null slot; sibling probe = `id = bare_id OR id STARTS WITH bare_id + "|quote_hash="`.

5. **The 24 fields** (FINAL_DESIGN §7.1): **Code, 6:** `id · fact_scope · series_unit · created · date · source_type`. **Semantic/enrichment, 18:** `driver_state · quote · level_low · level_high · level_unit · change_value · change_unit · comparison_low · comparison_high · comparison_baseline · value_text · conditions · company_confirmed · xbrl_qname · fiscal_year · fiscal_quarter · period_scope · time_type`. Recovery-only `disputed` is outside the count, controlled solely by recovery.

6. **Slices vs names vs portions.** Own parts → slices: NAME-10 sends a company's own measured segment/product/geography/customer group/sales channel/owned entity to `fact_scope.slice`; a slice is the company's own measured business population ("revenue/earnings from ___" test, §5.2), so the cause NAME stays reusable across companies (NAME-02, §1 mission). External causes → names: NAME-11 — an external actor, object, platform, policy, event, or product causing the outcome stays in the name (carve-out NAME-15/16: `fed_rate`, `aws_outage`, `tiktok_ban`), because the name contains the cause only (NAME-01) and the external thing IS the cause; there is no vendor slice kind; a customer is a slice only when it is the reporting company's own customer population; unclear role → keep it in the name. Portions → names: OD-17 — `current`/`funded`/`fee_earning`-type population qualifiers change what population is measured, so they stay in the name as a DIFFERENT Driver from the bare one (omit the slice only for the true consolidated population; network/systemwide/GMV subsets stay qualified); portion-qualifier supersets (`current_rpo` vs `rpo`) are PERMANENT link auto-refusals (BUILD §8.1.6) — the over-merge-safety direction.

7. **Concept/member links may be absent; wrong links are worse** (FINAL_DESIGN §8, §1). Absent by design: `MAPS_TO_CONCEPT` is metric-only, zero-or-one, best-effort; the pipeline defaults to refute/abstain (loose PICK/VERIFY, deterministic guards G2→G0→G1 and vetoes A–D can only ABSTAIN); guidance/surprise inherit through `BASE_METRIC` (blocked on non-GAAP measurement), action abstains; a missing graph concept never blocks the fact and self-heals later; `MAPS_TO_MEMBER` needs BOTH axis and member and may be absent. Wrong is worse because the damage is SILENT until detected — reads/decisions already made on it are not undone (the stored link is revocable by design — XC-18 reification + revocation, ratified-dormant; XC-17 monitoring) — while an absent link self-heals on re-runs at zero risk: "Missing links are safer than wrong links." Rejected forever: live value match, token match, static dictionary, simple multi-method agreement.

8. **Raw channel submission ≠ internal Candidate Fact Packet** (FINAL_DESIGN §2; ChannelContract §3–§4; 15_CandidateFactPacket Part A; BUILD §2). The raw submission is the PUBLIC boundary a fetch-only channel emits: envelope (`source_id`, `source_type`, `ticker`, `fye_month`, `event_time`) + raw items AS STATED (verbatim quote, raw label/claim, signed unscaled values + raw unit text, period signals, XBRL with the EXACT context and verified-empty `dimensions=[]`, guidance value_text/conditions + attribution EVIDENCE); it must NOT contain names, ids/fact_scope, computed fiscal fields, measurement tokens, canonical units, or derived numbers. The Candidate Fact Packet (frozen v1.0 + the two 2026-07-15 owner amendments Q4/Q1-ext) is the INTERNAL core object the shared decomposer produces: Block 0 envelope · Block 1 TRANSIENT identity signals `{proposed_name, slice_tokens[], measurement_spans[], per_x, quote, event_time}` · Block 2 the proven fact (code builds `id·fact_scope·series_unit·created·date`) · Block 3 optional verdict; kernel Stage-0 `evidence_atom` ≡ the Block-2 item, so on CREATE the same packet's Block 2 becomes the first DriverUpdate (born-complete); three consumers: kernel (Block 1), fact writer (Block 2), verdict writer (Block 3). Location note: the packet spec is the temporary fifth live file `15_CandidateFactPacket.md` (current sha `aa7239ed…`); relocating its content into BUILD needs explicit owner approval + byte/hash proof.

9. **Status buckets** (owning rows = STATUS_AND_HISTORY §1–§2; FINAL_DESIGN §10 is the generated mirror): **FINAL/BUILD-PENDING (final-but-unbuilt):** Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 production wiring · PER-20 resolver build + 21 tests · slice table materialization + PIT menu code · concept-linker vetoes C/D + PIT query build · the whole Track B writer/validator/CLI/park-ledger stack · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh. **DESIGN-INCOMPLETE:** the production running layer (BUILD §7's runbook list); the OD-5 change scanner is a recommendation only. **CONDITIONAL:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (DORMANT until the P19 proof plan X-XL0-3, every hard pre-gate, and EXP-6 convergence evidence) · multi-run concept stability/caching. **APPROVED WORKING DESIGN (owner 2026-07-15; NOT activated; gates/OFF-switches in force):** Admission Kernel v3.4 · the XBRL-native materializer (mechanics BUILD §8.1/§8.2). **CANDIDATE:** Bayes learner proposal (unvetted) · Driver Genesis restructure (rationale only). **OPEN (owner):** catalog 796-vs-786 + lifecycle/IPO · full model/cost policy beyond signed EXP-2 · FS-23 · 8-K taxonomy · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement. **RETIRED:** old Guidance replay plan · fixed-vocabulary v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range` · `gp_UNDEF` quiet fallback · `evhash16` · FS-22 · RavenPack import · catalog-first live reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all sync. **HISTORICAL (evidence, never authority):** everything in `archive/2026-07-15_pre-consolidation/` including both ratified-design originals and the archived `CONSOLIDATION.md` (BUILD §8 authority tiers; STATUS §8); the old Restaurant runs' RULE-BEARING outputs (raw-text chunk copies excepted, BUILD §4); FablePrompt/v2 executed briefs; `HANDOVER_2026-07-12.md` as a dated snapshot (BUILD §9).

10. **The complete source→anchor map, on disk:** **STATUS_AND_HISTORY §7** — the source crosswalk mapping all 33 files → destinations (Phase 5 executed 2026-07-16: every archive destination DONE except the two deferred experiment files). **§7.1** — the rule-ID crosswalk: every stable range → its one live anchor with per-ID exceptions (NAME-01..19, FS-01..27, UNIT-01..14, PER-01..20, MF-01..12, DU-01..24, XC-01..18, PIPE-01..37(+27a/27c/27d/31b), FACT-01..36(+14b/17b/18a/26b/26e/26f), GI ranges incl. the retired file's own numbering (no GI-08/09 exist), Track A D1..D8, `66` D-1..D-13, OD-1..21, K2, the 42 rows, Contract clauses §1–§9, Packet blocks 0-3 + Parts B/C/D, ratified bundles, open items). **§7.1b** — the ratified-design destination proof: every transferred kernel section (§1–§16 → BUILD §8.1.1–8.1.13 + FINAL_DESIGN law anchors) and every XBRL element (recipe, P1-P17/P19 pin map, the ten amendments → their gate-tagged owning sections). **§7.2** — the census T-group anchors (T1–T12 with per-rule exceptions). Dead-rule wording → current anchors: **§3, the 42 supersession rows** (+ the additions-not-reversals list anchoring all 21 ODs). Byte baseline: **§8** — `archive/2026-07-15_pre-consolidation/MANIFEST.json` (all 33 sources sha-256-pinned, 11,320 lines / 1,362,208 bytes, commits `49f1cd8`/`87bc150`); the archive holds 32 SOURCE COPIES (29 originals + 3 snapshots) plus evidence files that are NOT source copies. Destination vs CURRENT location: `15_CandidateFactPacket.md` = temporary fifth live file at the FinalDesign root (destination move needs separate owner approval); `FableExperimentPlan.md` (byte-pinned sha `51966848…7472`) + `FableExperimentWorkOrder.md` (sha recorded-never-pinned; authoritative record = `experiments/WORKORDER_STATUS.md`; frozen original `4911a22f…` in the manifest) live at root and archive only after the experiment program migrates; the two ratified-design originals' archive destination is DONE (2026-07-15, byte-verified).
## 7. Per-question grades (locked rule + full checklist applied)

- **Q1 — PASS.** Class node vs fact node exact (name + permanent fact_type + SAME_AS/BASE_METRIC + birth
  evidence; one occurrence per source event); asymmetric law with when-unsure-keep-separate; reversible
  SAME_AS recovery; never delete/re-key. The narrowed writer-claim scope (no-silent-overwrite, NOT
  over-merge-impossible; kernel judges + falsifier + audits with measured bounds) is the documented Part C ⑤ /
  BUILD §8.1 nuance, correctly attributed. No false fact.
- **Q2 — PASS.** All nine required stages present and correctly ordered. BOTH stated values enumerated
  (42.6 + raw "$B"; 12 + "%"). Never-sent list + ignored-and-recomputed. Decomposition steps 0-7 with the
  local role test → `slice=product:iphone`, residual `revenue`, metric via DU-05. DU-09 first-match
  `increased`; glued-billions → `level=42600 m_usd`; OD-11 explicit-YoY → `percent_yoy` (not the bare-growth
  default); `comparison_baseline=prior_year` with expectation baselines forbidden. Quarter branch fail-closed
  on `fye_month`; `gp_` id; `period_scope=quarter`; `time_type=duration` as required semantic output. ATTACH
  vs born-complete CREATE with the first-fact pin stated as satisfied (bare name, state≠unknown). ID law +
  scope shape (measurement omitted; never `slice=total`); OD-8 vs the PRE-BATCH graph, no sibling → bare, no
  quote_hash. Lane matrix, sign validator, shape-hint discard, period symmetry, quote-required. MERGE
  semantics, code-6 stamp (all six fields), OD-10 `series_unit`, three edges, dry-run default + env gate;
  metric-only enrichment chain with abstain. Read: full series key, render order, source rank
  `8k > transcript > 10q > 10k > news`, strict PIT `date < as_of`, raw/reconciled labels. No false fact.
- **Q3 — PASS (the R7 gate).** Five lane-legal examples; EVERY constructed fact names its own driver_state
  (metric `increased`, guidance `raised`, actual surprise `beat` + home `reported`, gvc surprise `beat` +
  home `unknown`, action `announced`); per-lane FORBIDDEN lists match §7.2 including guidance's
  no-consensus-baseline/no-direct-XBRL and action's full set. BOTH surprises construct their required
  same-event homes, name the home states, and show ALL SIX dimensions each (family via BASE_METRIC; period —
  reported ended Q3 for actual, guidance TARGET FY2027 for gvc per OD-21; period scope; slice omitted=omitted;
  measurement ∅=∅; normalized value/unit equality). The guidance home's born-`unknown` legality cites exactly
  the clause whose condition the fixture satisfies (§4.2 suffix-proven-lane Q5 pin; readers derive
  effective_driver_state; DU-15 keeps the co-stated expectation off the home). The wordless `beat` on the gvc
  surprise states its full legality conditions (outside-range proof, transient-discarded polarity,
  `basis=metric_meaning`, no-mainstream-counter-story). ONE surprise driver holding all three types
  (NAME-17/OD-21) stated. No false fact; no unstated required element.
- **Q4 — PASS.** Slot order exact with absent-omitted and never-`slice=total`; the TEN hashed slots exactly
  (level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high,
  comparison_baseline, value_text, conditions) plus the exclusions; the preimage law (fixed-order compact
  ASCII JSON array, null ≠ empty string, the one text normalizer + one decimal canonicalizer, full untruncated
  SHA-256 — matching the S3.1 ID law present in the tested BUILD §5). EVERY ladder case stated: no-sibling →
  bare WITH the in-batch pairwise-conflict all-hashed override; one-sibling fill (no null-clobber) vs flagged
  hashed on conflict; multiple-sibling exact-MERGE / conflict-with-ALL hashed / compatible-not-exact PARKS;
  two in-batch competitors for one partial sibling → park BOTH; decisions vs the PRE-BATCH graph; at most one
  bare member; pairwise conflict on ≥1 shared non-null slot; the sibling probe pattern. Nothing missing.
- **Q5 — PASS.** 6 code + 18 semantic = 24, both lists exactly matching §7.1, field by field; recovery-only
  `disputed` correctly outside the count.
- **Q6 — PASS.** NAME-10 own-population slice with the "revenue/earnings from ___" test and the NAME-02
  reusability rationale; NAME-11 external-cause-in-name with NAME-15/16 carve-outs and the no-vendor-slice-kind
  + own-customer nuance + unclear→name default; OD-17 portions as DIFFERENT drivers (population qualifiers),
  consolidated-only slice omission WITH the network/systemwide/GMV exception; permanent superset auto-refusals
  (BUILD §8.1.6) as the over-merge-safety direction. No inversion.
- **Q7 — PASS.** Metric-only, zero-or-one, best-effort, abstain-default; guards/vetoes can only ABSTAIN;
  BASE_METRIC inheritance with the non-GAAP measurement block; action abstains; absence never blocks and
  self-heals. Wrong-is-worse with the CORRECT scoping: damage is silent until detected and reads/decisions
  already made are NOT undone, while the STORED link is revocable by design (XC-18 reification+revocation,
  ratified-dormant; XC-17 monitoring) — precisely the FINAL §8 wrong-link scoping. Rejected-forever list
  intact. No false fact.
- **Q8 — PASS.** The submission-vs-packet distinction is complete and correct on both sides: public boundary
  envelope + as-stated raw items with the never-contains list and ignored-and-recomputed; internal packet =
  frozen v1.0 + the two 2026-07-15 owner amendments, Blocks 0-3, three consumers, kernel Stage-0
  `evidence_atom` ≡ Block-2 (born-complete on CREATE), plus the location note (temporary fifth live file,
  current sha quoted — equal to pin #5 — and the owner-approval + byte/hash-proof relocation gate).
  Strict-parse check on the historical killer class: the phrase "XBRL with the EXACT context and
  verified-empty `dimensions=[]`" carries the exception marker INSIDE the phrase — a verified-empty
  dimensions list exists only where dimensions were verified empty — in a list whose members are
  kind-conditional (exactly like "guidance value_text/conditions" two items later, which no reader takes as
  universal). No universality assertion on the natural parse; materially DISTINCT from run 11's unqualified
  wording. Not graded as a rescue: the qualifier is in the quoted text itself.
- **Q9 — PASS.** Every bucket placement is file-faithful at the frozen commit: Track A remainder with
  WP-FC-RUN and the OD-6 gate explicitly never-run; the conditional bucket carries EXP-6 convergence evidence
  + the P19 X-XL0-3 proof plan + hard pre-gates for the DORMANT materializer, OD-19's zero-wrong-same trigger,
  XC-16, experiment-gated model-role membership; approved-working-design = the two ratified designs with
  owner-date, NOT-activated, gates/OFF-switches in force; candidates, opens (G1 correctly absent), retireds
  (all thirteen), and historicals including the Restaurant RULE-BEARING-outputs line WITH the raw-text-chunk
  carve-out (BUILD §4) and the archive-wide evidence-never-authority rule. No misplacement found.
- **Q10 — PASS.** The complete on-disk map: STATUS §7 (33-file crosswalk, EXECUTED with the two-experiment-file
  deferral exception), §7.1 (every rule-ID range with letter-suffixed exceptions and the no-GI-08/09 fact),
  §7.1b (ratified-design destination proof, kernel §1-§16 → BUILD §8.1.1-8.1.13 + the XBRL pin map and ten
  amendments), §7.2 (T1-T12), §3's 42 supersession rows + the 21-OD additions-not-reversals anchor, and §8's
  byte baseline (MANIFEST.json, 33 sources, EXACT totals 11,320 lines / 1,362,208 bytes, commits
  49f1cd8/87bc150; 32 source copies = 29 originals + 3 snapshots; evidence files NOT source copies).
  Destination-vs-current distinctions all correct (packet = temporary fifth live file gated on owner approval;
  Plan byte-pinned at root; WorkOrder sha recorded-never-pinned with the board as authoritative record and the
  frozen original `4911a22f…` in the manifest; ratified originals' archive destination DONE). Counts quoted
  exactly, never compressed.

**Checklist confirmation:** every constructed fact (7 total incl. both homes) names its driver_state · both
stated fixture values enumerated · no conditional-emphasis inversion found (Q8 examined hardest) · all counts
and locations exact (33; 11,320/1,362,208; 29+3; 24=6+18; ten slots; 42 rows; suffixed ID ranges) ·
six-dimension home-match shown for BOTH surprises · satisfying clauses cited (Q3 §4.2 suffix-proven pin, §4.3
polarity conditions; Q2 §4.2 ATTACH/born-complete + first-fact pin).

## VERDICT: **PASS 10/10** — under the R7-amended official set, the locked grading rule, and the full checklist.

## 8. Standing policy going forward (owner, 2026-07-16 — also recorded as STATUS §4 ruling R8 inside the freeze)

1. The "hash only three law files" proposal is **REJECTED** — every reader test pins EVERY file it reads
   (BUILD and STATUS contain essential design mechanics and decisions).
2. Routine build/status progress updates do NOT require a full reader-test rerun. Changes to **rules,
   contracts, operative mechanics, gates, owner decisions, crosswalks, or major release handoffs DO.**
3. Any future rerun follows this record's mechanics: detached worktree at ONE fixed commit, every read file
   sha-pinned pre-run and re-verified post-run, explicit per-command exit-status checks, append-only uniquely
   named record.

## 9. RETIREMENT

With **10/10 + 7/7 exact hashes at commit `5d0bd41b6df15329697b1634a30f0a30f08da21f`** and the battery green
under explicit exit checks, the Phase-5 consolidation gate is CLOSED and **the documentation bot is RETIRED**
per the owner's directive. The seven-file root + archive stand certified as a self-sufficient blank-context
design authority at the recorded commit. Future documentation work happens under the R8 standing policy;
implementation work proceeds under THE TRACK A IMPLEMENTATION GATE (BUILD §4) and the live files' own gates.
