# READER TEST RECORD — Phase-5 LAST GATE, run 3 (2026-07-16)

**VERDICT: FAIL — 9/10 (PASS RULE: 10/10 required; Phase 5 remains NOT complete; the rerun writes `READER_TEST_RECORD_2026-07-16_phase5-final-run4.md`). This failed record stays per the never-overwrite law.**

- Workflow run: `wf_24f2541d-271` · agent label `phase5-final-reader-run3` · ~198k subagent tokens · fresh zero-context reader.
- Constraint: reader restricted to the SEVEN root files; archive/ forbidden.
- **Preamble disclosure:** the ten exercises are the UNMODIFIED official §14.3 ten; the preamble carries the run-2 completeness instruction PLUS "where a rule has multiple cases, state EVERY case" (execution-side emphasis; changes no correctness bar).

## Per-question grades

| Q | Grade | Notes |
|---|---|---|
| 1-3, 5-8, 10 | PASS | Exact throughout; Q3 carries all five states + per-lane FORBIDDEN sets; Q7 incorporates the round-22 scoping (stored link revocable, consumed reads not undone). |
| 4 | **FAIL** | Same omission as run 2 (withdrawn round 22): states the one-sibling trigger + in-batch case but NOT the multi-sibling ladder — with several siblings, hash requires conflict-with-ALL; exact MERGES; compatible-but-not-exact PARKS as ambiguous (FD §5.1; origin 66:336-339). Third consecutive reader with the identical omission. |
| 9 | PASS | All eight buckets; HISTORICAL correctly states 29 originals + 3 snapshots in the archive (the run-2 failure cured by the round-22 banner fix). |

## Cause disposition (fix round)

Three consecutive independent readers omitted the SAME multi-sibling cases while the answers were otherwise exact — by the same evidentiary standard that justified the run-1 Q7 file fix (which cured Q7 in one run), this is a file-DENSITY defect, not reader failure: FD §5.1 packed FIVE collision outcomes into one 60-word mid-bullet sentence. **Fix applied:** the sentence is restructured into an explicit per-case ladder (NO sibling / ONE sibling / MULTIPLE siblings / two-competitors) with identical wording per case — zero rule-meaning change. The official question text remains UNMODIFIED. If run 4 fails Q4 the same way despite the explicit ladder, the question's wording escalates to the owner.

## Tested file hashes (SHA-256, full — the seven-file set)

```
f3656e732bd82ecbe28d5d387a13a1232fe483ffbf04244b4df58659949d448e  FINAL_DESIGN.md
9e6ffcbbcbc1a34e3792a1afa37469915ddfe02cbeac20c978cdd09b89292cea  ChannelContract.md
4e151f0b1db138a773dd54b8e975433ea88cc09ff6926310dafb0df8fb028b30  BUILD_AND_OPERATIONS.md
c6f82b44b6749f7a8af8e615fd4b5c6997038eda71baef89fe2aa3d748fe9c85  STATUS_AND_HISTORY.md
aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c  15_CandidateFactPacket.md
51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472  FableExperimentPlan.md
57a6b86090083560af476f23125a2f95bbce2e572bb93cc132e9ed6cdff9033e  FableExperimentWorkOrder.md
```

## The exact prompt (complete, inline — per the round-22 standard)

```
You are a brand-new engineer with ZERO prior context. Your ONLY permitted sources are these SEVEN files (read fully; open NOTHING else — nothing in archive/, no other repo files):
1. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md
2. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/ChannelContract.md
3. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md
4. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md
5. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md
6. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableExperimentPlan.md
7. /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md
Answer ALL TEN official exercises, terse, each answer with file+section cited. A documented-open-gap or owner-ruled answer (with citation) is CORRECT; never guess. Distinguish a file DESTINATION from its CURRENT location. Answer EVERY part of every question explicitly — an unstated required element is a wrong answer; where a rule has multiple cases, state EVERY case.
1. Explain Driver versus DriverUpdate and the over-merge safety law.
2. Take one source quote through channel, decomposition, name/slice/measurement/unit/period, identity, validation, write, and read (official fixture: "Q3 iPhone revenue rose 12% year-over-year to $42.6B" from an 8-K).
3. Construct one metric, guidance, actual surprise, guidance-vs-consensus surprise, and action example without violating a lane (driver_state + the FORBIDDEN fields per lane).
4. Derive the scope slot order and the collision signature (when quote_hash appears; the ten hashed slots exactly).
5. List all 24 fields and identify code versus semantic ownership.
6. Explain why own parts are slices, external causes stay in names, and portions stay in names.
7. Explain why concept/member links may be absent and why wrong links are worse.
8. Distinguish the raw channel submission from the internal Candidate Fact Packet.
9. Identify what is final-but-unbuilt, design-incomplete, conditional, approved-working-design, candidate, open, retired, and historical.
10. Find every original source and its replacement anchor without opening chat history: name the file+sections that map every source file, rule-ID range, T-group, and transferred ratified-design element.
Final message = the ten numbered answers only.
```

## The reader's full answers (verbatim)

1. **Driver vs DriverUpdate; the one law.** A **Driver** is one reusable, atomic cause or standing thing that can matter to a company/market — a class node: name + permanent `fact_type` + `SAME_AS`/`BASE_METRIC` links + birth evidence. A **DriverUpdate** is one real, source-backed occurrence of a Driver in one source event — the fact node (FINAL_DESIGN §0). **Over-merge safety law (asymmetric):** merging different meanings causes permanent damage; keeping the same meaning separate is repairable — **when unsure, keep separate**. True duplicates stay recoverable via reversible `SAME_AS`; nodes/facts are never deleted or re-keyed (FINAL_DESIGN §1).

2. **Fixture walkthrough** ("Q3 iPhone revenue rose 12% year-over-year to $42.6B", 8-K):
- **Channel** (ChannelContract §1–§5): channel only FETCHES/SUBMITS one packet per source event — envelope {`source_id`=the 8-K accession (must exist in Neo4j, else PARK-RETRY), `source_type=8k`, ticker, `fye_month`, `event_time`} + raw item {verbatim quote, raw label, signed unscaled 42.6 + raw unit text "$…B", period signals}; it never sends names/ids/fact_scope/fiscal quarter/measurement/canonical units/computed numbers (§4).
- **Decomposition** (15_CandidateFactPacket Part B; BUILD §2): strip direction word "rose" → measurement peel = ∅ (never assume GAAP) → per_x none → portion none → local role test: iPhone = own product → `slice_tokens=[product:iphone]` (kind from frozen axis table if XBRL member present, else the FS-15 ladder) → LLM-proposed name = `revenue` (never code-parsed) → fact_type = `metric` (DU-05/06 persistence test; prior-year comparison is a metric change, not a surprise — FINAL_DESIGN §7.2 routing).
- **Name/slice/measurement/unit/period:** name `revenue`; slice `product:iphone`; measurement empty; unit — resolver canonicalizes glued billions → `level_low=level_high=42600`, `level_unit=m_usd` (×1,000), `change_value=12`, `change_unit=percent_yoy` (OD-11 YoY wording), `comparison_baseline=prior_year`, `driver_state=increased`, `level_shape_hint=point` (FINAL_DESIGN §4.3, §6.1, §7.1); period — "Q3" + fye_month through the one shared fiscal resolver → real quarter window, `gp_` DriverPeriod, `period_scope=quarter`, `time_type=duration` (required semantic output) (§6.2).
- **Identity** (FINAL_DESIGN §5.1; BUILD §5): base identity = event + driver + fact_scope; code builds `id = du:{safe_source_id}:revenue:period=<gp_id>|slice=product:iphone`; producer never in the key; kernel reuses the typed `revenue` Driver (exact ATTACH) or born-complete CREATEs it with this packet's Block 2 as its first fact (§4.2; BUILD §8.1.2).
- **Validation** (BUILD §5): existing typed Driver, lane matrix (metric: expectation baselines forbidden, prior_year legal), state-in-lane, shape-hint cross-check then discard, sign validator (`increased` ⇒ positive change), unit/scaling and per-X lint, period-edge/scope symmetry both ways, quote required.
- **Write** (FINAL_DESIGN §5.1/§7.1; BUILD §5): one atomic MERGE on id (dry-run default), `created` once, no null-clobber, OD-8 collision probe vs pre-batch graph; edges `OF_DRIVER`/`FROM_SOURCE`/`HAS_PERIOD`, enrichment `MAPS_TO_MEMBER` (slice part) + metric-only `MAPS_TO_CONCEPT`/`xbrl_qname` best-effort (§7.3/§8).
- **Read** (FINAL_DESIGN §9): grouped by the full series key (company · Driver · fact_type · slice · resolved period · period_scope · measurement · series_unit · time_type); same-day collapse rank `8k > transcript > 10q > 10k > news`; across days latest wins, priors kept as PIT history; backtest strict `date < as_of`; results labeled raw/reconciled; derived changes computed at read.

3. **Five lane-legal examples** (states from §4.3; forbids from §7.2 matrix):
- **Metric:** `revenue`, `driver_state=increased`, level+prior_year comparison. FORBIDDEN: expectation baselines (`consensus`/`previous_guidance` — only prior_year/sequential), `surprise=`, `value_text`, `conditions`, `company_confirmed`. Direct XBRL allowed.
- **Guidance:** `revenue_guidance` (`BASE_METRIC→revenue`), `driver_state=raised` (source-stated), target period REQUIRED, `company_confirmed` REQUIRED (core-derived who-said-it), `value_text`/`conditions` allowed under exact rules. FORBIDDEN: `consensus` baseline, `surprise=`, direct XBRL (inherits).
- **Actual surprise:** `revenue_surprise` (`BASE_METRIC→revenue`), `driver_state=beat`, `surprise=actual_vs_consensus` (code-composed: `surprise_basis_hint=actual` × `comparison_baseline=consensus`), reported period, metric home fact required in the same event. FORBIDDEN: `value_text`, `conditions`, `company_confirmed`, direct XBRL (§5.1 OD-21).
- **Guidance-vs-consensus surprise:** same `revenue_surprise` Driver (one surprise Driver holds all three types, NAME-17), `surprise=guidance_vs_consensus` (`basis_hint=guidance` × `consensus`), period = the guidance TARGET period (required, even if ended — §6.2), guidance home fact required; a guide vs the company's OWN prior guide is guidance MOVEMENT, never a surprise (F5 REJECT, BUILD §5).
- **Action:** `buyback` (OD-2 worked example), `driver_state=announced`, period only when a real window is stated (rare). FORBIDDEN: `surprise=`, `value_text`, `conditions`, `company_confirmed`, XBRL (abstains).

4. **Scope slot order + collision signature** (FINAL_DESIGN §5.1): order = `period=<period_u_id>` | `slice=<';'-joined code-sorted kind:value parts>` | `measurement=<comma-joined code-sorted tokens>` | `surprise=<type>` (surprise lane only) | `quote_hash=<full sha256>` (rare collision member only); absent slots omitted; never `slice=total`. **quote_hash appears** only on a collision member: a fact conflicting with a sibling on ≥1 shared non-null signature slot (decided against the PRE-BATCH graph state), or multiple initially pairwise-conflicting in-batch facts (all hashed); at most one bare member per group. **The ten hashed slots exactly (OD-8):** `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions` — quote text, state, confirmation, producer, source type, date, XBRL enrichment all EXCLUDED; preimage = fixed-order compact JSON array, ASCII-escaped, null ≠ empty string, canonical decimals, full untruncated SHA-256.

5. **The 24 fields** (FINAL_DESIGN §7.1): **Code, 6:** `id · fact_scope · series_unit · created · date · source_type`. **Semantic/enrichment, 18:** `driver_state · quote · level_low · level_high · level_unit · change_value · change_unit · comparison_low · comparison_high · comparison_baseline · value_text · conditions · company_confirmed · xbrl_qname · fiscal_year · fiscal_quarter · period_scope · time_type`. Recovery-only `disputed` is outside the count.

6. **Slices vs names** (FINAL_DESIGN §3): **NAME-10/11** — a reporting company's OWN measured segment/product/geography/customer group/sales channel/owned entity goes to the slice (a business population passing the "revenue/earnings from ___" test, §5.2), keeping the name cause-only (NAME-01) so the same cause reuses across companies; an **external** actor/object/platform/policy/event/product causing the outcome IS the cause, so it stays in the name (NAME-15/16 carve-out: `fed_rate`, `aws_outage`, `tiktok_ban`); unclear role → keep in the name (over-split-safe). **OD-17 portions** — `current`/`funded`/`fee_earning`-type population qualifiers stay in the NAME and differ from the bare Driver (a different measured population, not an own business part); omit the slice only for the true consolidated population; portion-qualifier supersets are PERMANENT `SAME_AS` auto-refusals (BUILD §8.1.6) — merging them would fuse different meanings.

7. **Absent vs wrong XBRL links** (FINAL_DESIGN §8): the goal is attach the exact company-reported concept or attach NOTHING — links are best-effort enrichment, never identity: `MAPS_TO_CONCEPT` metric-only zero-or-one, `MAPS_TO_MEMBER` may be absent (§5.2 FS-21); guards G0/G1/G2 (events, ratios/derived, non-GAAP), the default-REFUTED verifier, and the abstain-only veto deliberately produce abstention (conceptless classes ~100%, XC-17). A **wrong** link is far worse: its damage is SILENT until detected, and reads/decisions already made on it are not undone (the stored link is revocable by design — XC-18 reification dormant, XC-17 monitoring — but not the consumed reads); an **absent** link self-heals on re-runs at zero risk ("missing links are safer than wrong links", §1).

8. **Raw submission vs internal packet** (FINAL_DESIGN §2): the **raw channel submission** (ChannelContract §3) is the public input boundary — envelope + raw items AS STATED (verbatim quote, raw label, signed unscaled values + raw unit text, period signals, XBRL qname + exact context with verified-empty `dimensions=[]`, guidance `value_text`/`conditions`/attribution EVIDENCE); the never-send list (§4) bans final names, fact ids/fact_scope, computed fiscal fields, measurement tokens, canonical units, computed numbers. The **internal Candidate Fact Packet** (frozen v1.0 — 15_CandidateFactPacket Part A; BUILD §2) is the core object the shared decomposer produces: Block 0 envelope · Block 1 transient identity signals {proposed_name, slice_tokens[], measurement_spans[], per_x, quote, event_time} · Block 2 the proven fact · Block 3 optional verdict; kernel Stage-0 `evidence_atom` ≡ the Block-2 item, Blocks 1+2 travel as one object, and on CREATE Block 2 becomes the first DriverUpdate; code (not the packet) builds `id/fact_scope/series_unit/created/date`.

9. **Status buckets** (STATUS_AND_HISTORY §1/§2 own the lists; FINAL_DESIGN §10 is the generated mirror):
- **FINAL/BUILD-PENDING:** Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 wiring · PER-20 resolver + 21 tests · slice table materialization + PIT menu code · concept-linker vetoes C/D + PIT query build · the whole Track B writer/validator/CLI/park-ledger stack · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh.
- **DESIGN-INCOMPLETE:** the production running layer (BUILD §7's runbook list); the OD-5 change scanner is a recommendation only.
- **CONDITIONAL:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (DORMANT until P19 X-XL0-3 bars + every hard pre-gate + EXP-6) · multi-run concept stability/caching.
- **APPROVED WORKING DESIGN (owner 2026-07-15, NOT activated, gates/OFF-switches in force):** Admission Kernel v3.4 · the XBRL-native materializer (mechanics BUILD §8.1/§8.2).
- **CANDIDATE:** Bayes learner proposal (unvetted) · Driver Genesis restructure (rationale only).
- **OPEN (owner):** catalog 796-vs-786 + lifecycle/IPO · full model/cost policy beyond signed EXP-2 · FS-23 · 8-K taxonomy · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` enablement.
- **RETIRED:** old Guidance replay plan · fixed-vocabulary v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range` · `gp_UNDEF` quiet fallback · `evhash16` · FS-22 · RavenPack import · catalog-first live reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all sync.
- **HISTORICAL (evidence only, never authority):** everything in `archive/2026-07-15_pre-consolidation/` — the 29 originals + 3 snapshots incl. both ratified-design originals and the archived CONSOLIDATION.md (STATUS §7; BUILD §8 authority tiers); the retired `13_Track` file's own GI rows (§7.1); `66` D-1..13 doc-debt; FablePrompt/v2 executed briefs (provenance); DriverPlan.html; budget history (BUILD §9).

10. **The complete source→anchor map lives in STATUS_AND_HISTORY.md:** **§7** maps all 33 source files → destinations (distinguishing DESTINATION from CURRENT location: the archived sources' destination is DONE at `archive/2026-07-15_pre-consolidation/`; `15_CandidateFactPacket.md` is CURRENTLY the temporary fifth live file at root — relocation needs separate owner approval + byte/hash proof, BUILD §2; the byte-pinned `FableExperimentPlan.md` + `FableExperimentWorkOrder.md` are CURRENTLY live at root, destined for archive only after the experiment program migrates); **§7.1** maps every stable rule-ID range (NAME, FS, UNIT, PER, MF, DU, XC, PIPE, FACT, T, GI, D1-D8, `66` D-rows, OD-1..21 via the §3 additions list, K2, contract clauses, packet blocks) → its one live anchor with per-ID exceptions; **§7.2** maps every census T-group (T1–T12) → exact live anchors; **§7.1b** is the ratified-design destination proof mapping every transferred kernel section (§1–§16) and XBRL element (recipe, P1-P17/P19 pins, the ten amendments) → its live anchor in BUILD §8.1/§8.2 + FINAL_DESIGN. Supersessions themselves = STATUS §3 (the 42 rows).
