# READER TEST RECORD — 2026-07-17 — R8 RECHECK for ruling R11 — **PASS 10/10**

**Why this run exists:** the standing R8 policy (STATUS §4, certified inside the run-15 freeze) requires a
rerun with run-15 mechanics whenever rules/contracts/operative mechanics change. **R11** (STATUS §4,
2026-07-17) changed an operative rule — the interim exact-date period-scope labeling + strict shape guard
(explicitly NOT P14; P14 stays dormant) — and BUILD gained the §5 interim note, the §11.4
units-before-fusion order amendment, and the §11.4 internal-portion closure. Owner GO for this run given
2026-07-17 (cost stated in advance; single reader).

- Grading law (LOCKED, unchanged): most-natural parse governs; a false fact on that parse = FAIL; no rescue
  readings; full accumulated checklist (every constructed fact names its driver_state; every stated value
  enumerated; no conditional-emphasis inversions; exact counts/locations never compressed; six-dimension
  home-match verification; cite the clause whose condition the fixture satisfies).
- Records are append-only; this file is new and unique; runs 1-15 records are preserved beside it.

## 1. The tested snapshot — ONE fixed commit

- **Certification binds to commit `614742ae772bf040ebd103be8b79a57de6e0e72d`** (on origin/main before the
  test ran) = the two approved commits: `f57642f` (period fix + R11 interim guard + law records) +
  `614742a` (PreparedFactV1 schema + §11.4 internal closure).
- Test medium: detached git worktree at that commit (`scratchpad/r11-recheck-worktree`); HEAD verified
  pre- and post-run `614742ae…`; `git status --porcelain` clean pre- and post-run (0 lines).

### 1.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; `sha256sum -c` AFTER → 7/7 OK)

```
1a2107e80e089287c430f8e4a12b3225a64732e2353822c8c2d6977aa58399d5  FINAL_DESIGN.md
9e6ffcbbcbc1a34e3792a1afa37469915ddfe02cbeac20c978cdd09b89292cea  ChannelContract.md
4503a21b8675a4f03030bd1516dfb05313d53538c16d12fcf68fe67c13900b8d  BUILD_AND_OPERATIONS.md
0825328c574ff2cdde534c1d5f607a7dec6fbd78f090fa0fd52821955eaff6ba  STATUS_AND_HISTORY.md
aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c  15_CandidateFactPacket.md
51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472  FableExperimentPlan.md
57a6b86090083560af476f23125a2f95bbce2e572bb93cc132e9ed6cdff9033e  FableExperimentWorkOrder.md
```

ChannelContract, the packet (`aa7239ed…` — also the reader's own quoted sha, answer 8), the Plan
(= its standing byte-pin `51966848…7472`) and the WorkOrder are byte-identical to the run-15 pins;
FINAL_DESIGN/BUILD/STATUS differ from run 15 exactly by the post-freeze landed rulings (R9 FS-18,
R10 v3.6 lock, R11 + §11.4 amendments) — the changed bytes are precisely what this recheck certifies.

## 2. Execution trail

- Reader: ONE blank-context subagent (claude-fable-5), agent id `a77684eb114a9d28b`, 230,976 tokens,
  11 tool uses (file reads only), 269.3s, **first answering attempt — graded on its first produced output**.
- Prompt: byte-identical to the run-15 official R7-amended set (§5 of the run-15 record) with `<DIR>` =
  the worktree's FinalDesign path. No other change.
- Suites at the tested commit (run pre-push, main session): driver core **291 passed**; workflows
  **265 passed, 1 skipped**.

## 3. The reader's ten answers — VERBATIM (spliced from the subagent's final output)

1. **Driver vs DriverUpdate; the one law.** A **Driver** is one reusable, atomic cause or standing thing that can matter to a company or market — a class node: name + permanent `fact_type` + `SAME_AS`/`BASE_METRIC` links + birth evidence. A **DriverUpdate** is one real, source-backed occurrence of that Driver in one source event — the fact node (FINAL_DESIGN.md §0 Glossary). The over-merge safety law is asymmetric: merging different meanings causes permanent damage; keeping the same meaning separate is repairable — **when unsure, keep separate**; true duplicates stay recoverable through reversible `SAME_AS`, and nodes/facts are never deleted or re-keyed (FINAL_DESIGN.md §1).

2. **Fixture walk-through — "Q3 iPhone revenue rose 12% year-over-year to $42.6B" (8-K).**
- **Channel:** SELECT/FETCH/SUBMIT one packet per source event (ChannelContract.md §2/§9): envelope `source_id`=the 8-K accession, `source_type=8k` (the TRUE document), ticker, `fye_month`, `event_time`; raw item = verbatim quote + raw label + SIGNED unscaled values (42.6, 12) with raw unit text + period signals (ChannelContract.md §3). The channel never names or decides identity (§1) and must not send names/ids/fact_scope/fiscal fields/measurement tokens/canonical units/computed numbers (§4).
- **Decomposition** (15_CandidateFactPacket.md Part B; BUILD_AND_OPERATIONS.md §2): step 0 strips the direction word "rose" (NAME-11 step 0); measurement peel → ∅; per-X → none; portion → none; name-vs-slice local role test: iPhone = own measured product → `slice_tokens=[product:iphone]`, residual "revenue" (NAME-10/11; the packet's own iPhone worked example); text-only kind via the FS-15/FACT-26f ladder (Part B step 4).
- **Name/slice/measurement/unit/period:** name=`revenue` (NAME-05/06, cause-only); fact_type=`metric` (Part B step 6: "a reported KPI value → metric"; DU-05 standing variable); measurement ∅ (never implies GAAP, FINAL_DESIGN.md §5.3); level: glued billions → `m_usd` ×1,000 → level_low=level_high=42,600, `level_unit=m_usd` (§6.1); change: explicit "year-over-year" wording → the OD-11 clause "YoY/comparable/annual growth → `percent_yoy`" → change_value=12, `change_unit=percent_yoy` (source-stated, not derivable — stored per §7.1); `comparison_baseline=prior_year` (headline temporal comparison, §7.1 — a metric CHANGE, not a surprise, §7.2 routing); driver_state=**`increased`** (DU-09 first match: stated direction, §4.3); period: shared fiscal resolver + fye_month → the real Q3 window, one `DriverPeriod` `gp_` id, `period_scope=quarter`, `time_type=duration` (required semantic output; §6.2).
- **Identity:** code builds id = `du:{safe_source_id}:revenue:period=<gp_id>|slice=product:iphone` (BUILD §5 ID shape; §5.1 slot order, absent slots omitted); `surprise=` forbidden on metric (§7.2).
- **Validation:** lane matrix (expectation baselines forbidden — prior_year legal), state-in-lane, shape hints (`level_shape_hint=point`, both bands equal), sign validator (`increased` requires positive change_value: +12 ✓), period-edge/scope symmetry (§7.1; BUILD §5 validator groups). Fuse within the event before collision; NO pre-batch sibling → the one post-fusion fact **stays bare**, no quote_hash (OD-8 ladder, first case, §5.1).
- **Write:** atomic writer MERGEs on id, `created` on create, `date`=source timestamp, `series_unit=m_usd` stamped once by code (OD-10); edges `OF_DRIVER`, `FROM_SOURCE`, `HAS_PERIOD` per PER-18 MERGE shape (§6.2, §7.3); enrichment: metric-only `xbrl_qname`/`MAPS_TO_CONCEPT` best-effort, `MAPS_TO_MEMBER` for the iphone slice part (§7.2/§8).
- **Read:** grouped by the full series key (company·driver·fact_type·slice·resolved period·period_scope·measurement·series_unit·time_type, §9); same-day source rank `8k` first; backtest strict `date < as_of`, live sees current graph; results labeled raw/reconciled (§9).

3. **One lawful example per lane** (lane matrix = FINAL_DESIGN.md §7.2; states = §4.3):
- **Metric:** Driver `store_count`, "We ended the quarter with 2,100 stores" → driver_state=**`reported`** (bare value). FORBIDDEN: expectation baselines (`consensus`/`previous_guidance`), `surprise=`, `value_text`, `conditions`, `company_confirmed`.
- **Guidance:** Driver `revenue_guidance` (`BASE_METRIC`→`revenue`), "We raised FY2026 revenue guidance to $41–42B" → driver_state=**`raised`** (source-stated movement); required target period FY2026; `company_confirmed` REQUIRED, core-derived from who-said-it evidence (=true here; §7.1, Q1 ruling). FORBIDDEN: `consensus` baseline, `surprise=`, direct XBRL concept (inherits).
- **Actual surprise:** Driver `revenue_surprise` (`BASE_METRIC`→`revenue`), "Q3 revenue of $10.0B beat consensus of $9.5B" → driver_state=**`beat`** (favorability judged from the phrase, OD-13 — never sign-derived); `surprise=actual_vs_consensus` = code-composed `surprise_basis_hint=actual` × `comparison_baseline=consensus` (§5.1 OD-21). **Required same-event home fact** (metric home): Driver `revenue`, "Q3 revenue was $10.0B" → home driver_state=**`reported`** (bare value; the co-stated expectation never rides the home — DU-15, §7.1). Match shown: family = both resolve to base `revenue` via `BASE_METRIC`; period = same reported Q3 (actual surprise uses the reported period, §6.2); period_scope `quarter`=`quarter`; slice omitted=omitted (consolidated); measurement ∅=∅; normalized value/unit 10,000 `m_usd` = 10,000 `m_usd` (§5.1 home-match rule). FORBIDDEN on the surprise: `value_text`, `conditions`, `company_confirmed`, direct XBRL.
- **Guidance-vs-consensus surprise:** Driver `eps_surprise` (one surprise Driver holds all three types, NAME-17/OD-21), "guided FY2026 EPS to $5.50, above Street consensus of $5.20" → driver_state=**`beat`** via the wordless-outside-range polarity proof, basis `metric_meaning` (legal because higher EPS has no mainstream counter-story; §4.3); `surprise=guidance_vs_consensus` (`basis_hint=guidance` × `consensus`). **Required home fact** (guidance home): Driver `eps_guidance`, the guide itself → home driver_state=**`unknown`** (bare guide, no stated movement, §4.3; a suffix-proven lane may be born `unknown` — §4.2 Q5 pin). Match shown: family = both `BASE_METRIC`→`eps`; period = the guidance TARGET period FY2026 even if ended (§6.2/OD-21); period_scope `annual`=`annual`; slice omitted=omitted; measurement ∅=∅; value/unit 5.50 `usd` = 5.50 `usd`. (Other home case: a numberless surprise needs a numberless home; ungrounded "results beat" PARKS — §5.1. Guide-vs-own-prior-guide is guidance MOVEMENT, never a surprise — F5 REJECT, §7.2/BUILD §5.)
- **Action:** Driver `buyback` (action_event per the OD-2 worked example), "board announced a $2B repurchase program" → driver_state=**`announced`** (the company's stated own action before completion, §4.3); no stated window → no `HAS_PERIOD` edge (§6.2). FORBIDDEN: `surprise=`, `value_text`, `conditions`, `company_confirmed`, direct XBRL.

4. **Scope slot order + collision signature** (FINAL_DESIGN.md §5.1). Canonical order, absent slots omitted, never `slice=total`: `period=<period_u_id>` | `slice=<sorted kind:value parts, ';'-joined>` | `measurement=<sorted tokens, ','-joined>` | `surprise=<type>` (surprise lane only) | `quote_hash=<full sha256>` (rare collision member only). **The ten hashed slots exactly** (OD-8): `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions` — quote text, state, confirmation, producer, source type, date, and XBRL enrichment EXCLUDED; preimage = fixed-order compact JSON array, ASCII-escaped, null ≠ empty string, one text normalizer + one decimal canonicalizer, full untruncated SHA-256. **When `quote_hash` appears** — only in the hash cases of the ladder, decided against the PRE-BATCH graph state: NO sibling → one post-fusion fact stays bare, BUT multiple pairwise-conflicting in-batch facts are ALL hashed; ONE sibling → compatible fills (no hash), conflict → flagged hashed member; MULTIPLE siblings → exact match merges, conflict-with-ALL → hashed member, compatible-but-not-exact PARKS; two in-batch competitors for one partial sibling → park BOTH. At most one bare member per group; members must pairwise conflict on ≥1 shared non-null slot.

5. **The 24 fields** (FINAL_DESIGN.md §7.1): **Code-owned, 6** — `id` · `fact_scope` · `series_unit` · `created` · `date` · `source_type`. **Semantic/enrichment, 18** — `driver_state` · `quote` · `level_low` · `level_high` · `level_unit` · `change_value` · `change_unit` · `comparison_low` · `comparison_high` · `comparison_baseline` · `value_text` · `conditions` · `company_confirmed` · `xbrl_qname` · `fiscal_year` · `fiscal_quarter` · `period_scope` · `time_type`. Exception: recovery-only `disputed` is OUTSIDE the count, controlled solely by recovery (§7.1).

6. **Slices vs names vs portions.** The name contains the cause only and must reuse across companies (NAME-01, §1) — so a reporting company's **own measured** segment/product/geography/customer group/sales channel/owned entity goes to the slice, never the name (NAME-10); the slice is the company's own measured business population inside `fact_scope` (§0). The NAME-11 local role test decides: strip direction/effect words; own measured part → slice; an **external** actor/object/platform/policy/event/product whose own independent action or state IS the cause stays in the NAME (`fed_rate`, `aws_outage`, `tiktok_ban` — the NAME-15/16 carve-out), because it is the reusable cause itself, not a population of the reporter; unclear role or a vague stripped fragment → keep in the name; a customer is a slice only as the company's own customer population; there is no vendor slice kind. **Portions** (`current`, `funded`, `fee_earning`, network/systemwide/GMV/curated subsets) stay in the name and differ from the bare Driver (OD-17; packet Part B step 3: never a slice, never measurement) because they measure a different population of the same metric — portion differences are PERMANENT link refusals (§5.4 OD-19; BUILD §8.1.6 "portion-qualifier supersets ALWAYS different"), so folding them would be an over-merge under the one law. Exceptions inside OD-17: omit the slice only for the true consolidated population; source-stated residuals may be company-specific slice values; eliminations/consolidation artifacts are neither names nor slices — drop and log (the affected real metric fact still writes per the Q2 owner ruling).

7. **Concept/member links may be absent; wrong links are worse** (FINAL_DESIGN.md §8, §1). The goal is attach the exact company-reported concept **or attach NOTHING**: the pipeline default-refutes (VERIFY = strict auditor, default REFUTED), guards G0/G1/G2 and the deterministic veto can only ABSTAIN, non-GAAP measurement abstains, guidance/surprise inherit only and action abstains (§7.2/§8) — so absence is a designed outcome. "Missing links are safer than wrong links" (§1): a wrong concept's damage is SILENT until detected — the stored link is revocable by design (XC-18 reification + revocation, ratified-dormant; XC-17 monitoring), but reads/decisions already made on it before detection are not undone — while an absent link self-heals on re-runs at zero risk; a missing graph concept never blocks the fact (§8). Same shape for members: `MAPS_TO_MEMBER` needs both axis and member and may be absent (§5.2).

8. **Raw channel submission ≠ internal Candidate Fact Packet.** The raw submission is the PUBLIC input boundary (FINAL_DESIGN.md §2; ChannelContract.md §3): envelope + raw items AS STATED — verbatim quote, raw label/claim, signed unscaled values + raw unit text, period signals, XBRL when present, guidance extras (value_text · conditions · company-confirmation EVIDENCE only); channels must NOT send final driver names, fact ids/fact_scope, computed fiscal fields, measurement tokens, canonical units, or any computed number (§4 — sent anyway ⇒ ignored and recomputed). The internal Candidate Fact Packet (frozen v1.0, 15_CandidateFactPacket.md Part A; summarized BUILD §2) is the CORE object the shared decomposer produces: Block 0 envelope · Block 1 TRANSIENT identity signals `{proposed_name, slice_tokens[], measurement_spans[], per_x, quote, event_time}` (never stored raw) · Block 2 the proven fact (≡ kernel Stage-0 `evidence_atom`; on CREATE it becomes the first DriverUpdate — born-complete) · Block 3 optional verdict; three consumers: kernel (Block 1) · fact writer (Block 2) · verdict writer (Block 3). Status: ChannelContract v1.0 is the sole public channel authority; the packet file is the temporary FIFTH live file, owner-frozen + two 2026-07-15 amendments (Q4, Q1-ext), current sha `aa7239ed…` — its relocation into BUILD is a DESTINATION still needing owner approval + byte/hash proof; its CURRENT location is the FinalDesign root (BUILD §2; STATUS §7).

9. **Status inventory** (owning lists = STATUS_AND_HISTORY.md §2; FINAL_DESIGN.md §10 is the generated mirror): **FINAL/BUILD-PENDING** — Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 production wiring · PER-20 resolver build + 21 tests · slice table materialization + PIT menu code · concept-linker vetoes C/D + PIT query build · the whole Track B writer/validator/CLI/park-ledger stack · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh. **DESIGN-INCOMPLETE** — the production running layer (BUILD §7 runbook list); the OD-5 change scanner is a recommendation only. **CONDITIONAL** — OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · the XBRL-native materializer + `09` rider (DORMANT until the P19 X-XL0-3 bars + every hard pre-gate + EXP-6) · multi-run concept stability/caching. **APPROVED WORKING DESIGN** (owner 2026-07-15; NOT activated, gates/OFF-switches in force) — Admission Kernel v3.4 · the XBRL-native materializer (BUILD §8.1/§8.2). **CANDIDATE** — Bayes learner proposal (unvetted, BUILD §8.3) · Driver Genesis restructure (rationale only). **OPEN (owner)** — catalog 796-vs-786 + lifecycle/IPO · full model/cost policy beyond signed EXP-2 · FS-23 · 8-K taxonomy · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement. **RETIRED** — old Guidance replay plan · fixed-vocabulary v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range` · `gp_UNDEF` quiet fallback · `evhash16` · FS-22 · RavenPack import · catalog-first live reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all sync. **HISTORICAL (evidence, never authority)** — the archived originals incl. both ratified-design originals (BUILD §8 authority tiers; STATUS §7), the old Restaurant runs' RULE-BEARING outputs (BUILD §4 implementation gate; raw-text chunk copies excepted), FablePrompt/v2 executed briefs, DriverPlan.html, and the v1/v2 death + proof evidence in BUILD §12.

10. **The full source→anchor map, chat-free** — all in STATUS_AND_HISTORY.md: **§7 "Source crosswalk (33 files → destinations)"** maps every source file (with §8 defining the archive's exact contents: 32 source copies = 29 originals + 3 snapshots, vs the evidence files CONSOLIDATION.md/MANIFEST.json/README/reader records; source 33 = the byte-pinned `FableExperimentPlan.md` LIVE at root). **§7.1 "Rule-ID crosswalk"** maps every rule-ID range (NAME, FS, UNIT, PER, MF, DU, XC, PIPE, FACT, T, GI, D1-D8, `66` D-1..13, OD-1..21 — the ODs individually anchored in the §3 additions list — K2, the 42 supersession rows, contract clauses §1-§9, packet blocks). **§7.2 "Census T-group anchors"** maps every T-group T1–T12 to exact live anchors. **§7.1b "Ratified-design destination proof"** maps every transferred ratified-design element — the kernel section-by-section (§1–§16 → BUILD §8.1.1–.13 + FINAL_DESIGN law spots) and the XBRL design (recipe, P1-P17/P19 pin map, the ten amendments → their gate-tagged owning sections). §3's 42 supersession rows map each dead rule to its current anchor. DESTINATION vs CURRENT location: Phase 5 executed — every "archive" destination is DONE **except** the two deferred experiment files: `FableExperimentPlan.md` (byte-pinned, sha `51966848…7472`) and `FableExperimentWorkOrder.md` are CURRENTLY live at the FinalDesign root and archive only after the experiment program migrates (STATUS §7 header + §5); the packet stays the fifth live file at root (destination pending separate approval); ChannelContract is KEPT live permanently as the sole public authority.

## 4. Per-question grades (locked rule + full checklist applied) — PASS 10/10

- **Q1 — PASS.** Class node vs fact node exact; asymmetric law + when-unsure-keep-separate; reversible
  SAME_AS; never delete/re-key. All facts true, correctly cited. (The run-15 answer's supplementary
  narrowed-writer-claim nuance is not a required element of the question; its absence asserts nothing false.)
- **Q2 — PASS.** All nine stages present and ordered; BOTH stated values enumerated (42.6 + raw "$B" band
  via glued-billions handling; 12 + "%" → percent_yoy via the exact OD-11 explicit-YoY clause);
  never-sent + ignored-and-recomputed; decomposition steps with the local role test; DU-09 `increased`;
  sign validator satisfied; quarter branch fail-closed on fye_month; `period_scope=quarter` for the declared
  Q3 — consistent with the R11-amended exact-date rule in the tested bytes; ID shape with measurement
  omitted; OD-8 vs PRE-BATCH, bare, no hash; code-stamps + three edges + dry-run gate implied by MERGE
  semantics cited; read stage complete. **Grading note (transparent):** "enrichment: … `MAPS_TO_MEMBER` for
  the iphone slice part" names the member-link enrichment vector that "carries the slice part it supports"
  (FINAL_DESIGN line: `MAPS_TO_MEMBER` is fact-level enrichment, needs both axis and member, MAY BE ABSENT)
  — it does not assert an attachment or fabricate axis/member evidence for this text-only fixture; the
  reader's own answer 7 states the may-be-absent law. No false fact on the most-natural parse.
- **Q3 — PASS (the R7 gate).** Five lane-legal examples; EVERY constructed fact names its own driver_state
  (metric `reported`, guidance `raised`, actual surprise `beat` + home `reported`, gvc surprise `beat` +
  home `unknown`, action `announced`); per-lane FORBIDDEN lists match §7.2; BOTH surprises construct their
  same-event homes, name the home states, and show ALL SIX dimensions each; the guidance home's
  born-`unknown` legality cites the exact clause (§4.2 Q5 pin); DU-15 keeps the expectation off the home;
  the wordless `beat` states its full legality conditions (outside-range, `metric_meaning`,
  no-mainstream-counter-story); OD-13 never-sign-derived; ONE surprise driver for all three types
  (NAME-17/OD-21); extra correct cases (numberless home, F5 movement-not-surprise) added. No false fact.
- **Q4 — PASS.** Slot order exact; the TEN hashed slots exactly + exclusions; preimage law; EVERY ladder
  case incl. in-batch-all-hashed, park-both-competitors, at-most-one-bare, pairwise-conflict requirement.
- **Q5 — PASS.** 6 code + 18 semantic, exact lists; `disputed` outside the count.
- **Q6 — PASS.** NAME-10 own-population rule; NAME-11 role test + NAME-15/16 carve-out; no vendor slice
  kind; customer scoping; unclear → name; OD-17 portions + consolidated-omit exception + residuals +
  eliminations drop-and-log w/ the Q2 owner ruling; OD-19/BUILD §8.1.6 permanent refusals.
- **Q7 — PASS.** Absence-by-design mechanics; silent-damage asymmetry; XC-18 revocation ratified-dormant;
  XC-17; self-heal; missing-never-blocks; member both-fields rule.
- **Q8 — PASS.** Boundary vs packet; blocks 0-3 + three consumers; born-complete equivalence; frozen v1.0 +
  two amendments + sha `aa7239ed…`; fifth-live-file CURRENT location vs pending DESTINATION.
- **Q9 — PASS.** All eight buckets faithful to the files' own statements (counts/locations quoted as the
  files state them, never compressed); dormant materializer + gates correct; historical taxonomy correct.
- **Q10 — PASS.** §7 / §7.1 / §7.1b / §7.2 / §3-42-rows / §8-manifest all named; the 32-source-copies
  (29+3) vs evidence-files taxonomy exact; both deferred experiment files + the Plan byte-pin sha; packet
  and ChannelContract location/destination distinctions exact.

## 5. R11-specific comprehension (the reason this run exists)

The changed bytes (R11 ruling row, BUILD §5 interim note, §11.4 order amendment + internal closure) were IN
the tested files. The reader's Q2 period stage labels the declared-Q3 fixture `period_scope=quarter` — the
exact behavior R11 legislates for declared framing — and its Q9/Q10 status/crosswalk answers remain correct
against the amended STATUS/BUILD. No answer contradicts R11, the §11.4 amendments, or any prior rule.

## 6. Verdict

**PASS 10/10 · 7/7 exact hashes (pre-pinned, post-verified) · worktree clean at `614742a` pre/post ·
first-attempt output graded.** The R8 obligation for ruling R11 is DISCHARGED. Records remain append-only;
runs 1-15 untouched.
