# READER TEST RECORD — official §14.3 run 10 (2026-07-15)

**Status: PASS (graded 10/10 by the session lead against FINAL_DESIGN/BUILD/STATUS law; grade recorded in CONSOLIDATION.md §16).**
> **ROUND-18 REGRADE (2026-07-15): the 10/10 is WITHDRAWN — re-graded 6/10 strict; certification value VOID (the tested FINAL/STATUS bytes carried an EXP-6 omission). See the CORRECTION ADDENDUM at the end of this file. Original text above and below is untouched.**
Durable evidence per the round-17 standard: agent id, full prompt, full answers with citations, full tested hashes — repo-portable, no machine-local paths required.

- Workflow run: `wf_2e462b6d-c84` · agent label `official-reader-run-10` · subagent tokens ~127k.
- Constraint: the reader was restricted to the five live files; archive/ and all other sources forbidden.

## Tested file hashes (SHA-256, full)
```
1aaaedfa891c8fb3f167c67bc687264c920b4b35e73b5b0baca7abf7be9aa1af  FINAL_DESIGN.md
9e6ffcbbcbc1a34e3792a1afa37469915ddfe02cbeac20c978cdd09b89292cea  ChannelContract.md
f5988ed08ccf513d23b57fdd1dcd75b8c2c01c5e06c3dc8a8e3cdb32e9a02c76  BUILD_AND_OPERATIONS.md
7110fa18dd3fea1320665c43fd89dd6c9df8948324748d0011956bfefd346bd2  STATUS_AND_HISTORY.md
aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c  15_CandidateFactPacket.md
```

## The exact prompt (from the persisted workflow script)
```js
const Q = [
 'You are a brand-new engineer with ZERO prior context. Your ONLY permitted sources are these five files (read fully; open NOTHING else, nothing in archive/):',
 '1. ' + DIR + '/FINAL_DESIGN.md',
 '2. ' + DIR + '/ChannelContract.md',
 '3. ' + DIR + '/BUILD_AND_OPERATIONS.md',
 '4. ' + DIR + '/STATUS_AND_HISTORY.md',
 '5. ' + DIR + '/15_CandidateFactPacket.md',
 'Answer ALL TEN official exercises, terse, each with file+section cited. A documented-open-gap or owner-ruled answer (with citation) is CORRECT; never guess. Distinguish a file DESTINATION from its CURRENT location.',
 '1. Explain Driver versus DriverUpdate and the over-merge safety law.',
 '2. Take one source quote through channel, decomposition, name/slice/measurement/unit/period, identity, validation, write, and read. Use "Q3 iPhone revenue rose 12% year-over-year to $42.6B" from an 8-K.',
 '3. Construct one metric, guidance, actual surprise, guidance-vs-consensus surprise, and action example without violating a lane (driver_state + the FORBIDDEN fields per lane).',
 '4. Derive the scope slot order and the collision signature (when quote_hash appears; the ten hashed slots exactly).',
 '5. List all 24 fields and identify code versus semantic ownership.',
 '6. Explain why own parts are slices, external causes stay in names, and portions stay in names.',
 '7. Explain why concept/member links may be absent and why wrong links are worse.',
 '8. Distinguish the raw channel submission from the internal Candidate Fact Packet.',
 '9. Identify what is final-but-unbuilt, design-incomplete, conditional, approved-working-design, candidate, open, retired, and historical.',
 '10. Find every original source and its replacement anchor without opening chat history: name the file+sections that map every source file, rule-ID range, T-group, and transferred ratified-design element.',
 'Final message = the ten numbered answers only.',
].join('\n
```

## The reader's full answers (verbatim)

1. **Driver vs DriverUpdate; the over-merge law.** A Driver is one reusable, atomic cause or standing thing that can matter to a company/market — a class node: name + permanent `fact_type` + `SAME_AS`/`BASE_METRIC` links + birth evidence. A DriverUpdate is one real, source-backed occurrence of that Driver in one source event — the fact node (FINAL_DESIGN.md §0 Glossary; graph shape §2). The safety law is asymmetric: merging different meanings causes permanent damage, keeping the same meaning separate is repairable — **when unsure, keep separate**; true duplicates stay recoverable via reversible `SAME_AS`, never deletion/re-key (FINAL_DESIGN.md §1).

2. **"Q3 iPhone revenue rose 12% year-over-year to $42.6B" (8-K), end to end.**
- **Channel:** FETCH-only; one packet per source event — envelope {source_id=8-K accession (press-release quote = the 8-K's own accession), source_type=`8k`, ticker, fye_month, event_time} + raw item {verbatim quote, raw label, SIGNED unscaled values + raw unit text, period signals, XBRL context if present}; no names, no ids, no canonical units (ChannelContract.md §1–§4).
- **Decomposition** (15_CandidateFactPacket.md Part B; BUILD §2): strip direction ("rose") → measurement peel (none, never assume GAAP) → per-X none → portion none → local role test: iPhone = own product → `slice_tokens=[product:iphone]` (NAME-10/11) → name=`revenue` (LLM-proposed, never code-parsed) → fact_type=`metric` (DU-05/06) → units.
- **Name/slice/measurement/unit/period:** name `revenue`; slice `product:iphone`; measurement ∅; glued billions → `level_unit=m_usd`, level_low=level_high=42,600 (×1,000; FINAL_DESIGN §6.1); change_value=+12, `change_unit=percent_yoy` (OD-11 YoY); `driver_state=increased` (stated direction, DU-09 §4.3); `comparison_baseline=prior_year` (headline comparison, §7.1); shared fiscal resolver + fye_month → Q3 `DriverPeriod` real dates, `period_scope=quarter`, `time_type=duration` (§6.2).
- **Identity:** code builds `id=du:{safe_source_id}:revenue:{fact_scope}`, `fact_scope=period=<gp_id>|slice=product:iphone`; base identity = event+driver+fact_scope, producer never in the key (§5.1; BUILD §5). Kernel reuses existing `revenue` (ATTACH) or CREATEs born-complete with this as first fact (§4.2).
- **Validation:** lane matrix (expectation baselines forbidden on metric), state-in-lane, sign check (increased ⇒ positive change), shape hints, unit/scale, period-edge symmetry (§7; BUILD §5).
- **Write:** atomic MERGE on id, dry-run default; `created`/`date`/`source_type`/`series_unit=m_usd` code-stamped; edges `OF_DRIVER`/`FROM_SOURCE`/`HAS_PERIOD` (+`MAPS_TO_MEMBER` if tagged); metric-only concept enrichment menu→pick→verify→veto or abstain (§7.3, §8; BUILD §5).
- **Read:** full series key (company·driver·fact_type·slice·period·period_scope·measurement·series_unit·time_type); same-day source rank `8k` first; PIT backtest strict `date < as_of`; labeled raw/reconciled (§9).

3. **Five lane-legal examples** (FINAL_DESIGN §7.2 matrix, §4.3 states, §5.1 OD-21):
- **Metric:** `revenue`, state=`increased`, level+change stated, baseline=`prior_year`. Forbidden here: expectation baselines (consensus/previous_guidance), `surprise=`, value_text, conditions, company_confirmed.
- **Guidance:** `revenue_guidance` (BASE_METRIC→revenue), "raised FY2026 outlook to $180–185B" → state=`raised` (source-stated movement; guide-vs-own-prior is movement, never a surprise — F5, BUILD §5), target period REQUIRED, `company_confirmed` REQUIRED (core-derived), value_text/conditions allowed. Forbidden: `consensus` baseline, `surprise=`, direct XBRL.
- **Actual surprise:** `eps_surprise`, "Q3 EPS $1.50 beat consensus $1.40" → state=`beat` (meaning-judged, OD-13), `surprise=actual_vs_consensus` REQUIRED (code-composed: basis_hint `actual` × baseline `consensus`), reported period ended (F7), metric home fact required same event.
- **Guidance-vs-consensus surprise:** same `eps_surprise` Driver (one surprise Driver holds all three types, NAME-17), `surprise=guidance_vs_consensus` (basis `guidance` × `consensus`), guidance TARGET period even if ended, guidance home fact required.
- **Action:** `acquisition`, fact_type=`action_event`, state=`announced`. Forbidden: `surprise=`, value_text, conditions, company_confirmed, direct XBRL; period only when a real window is stated (sentinels hard-fail, §6.2).

4. **Scope order + collision signature** (FINAL_DESIGN §5.1): `period=<period_u_id>` | `slice=<code-sorted kind:value parts, ;-joined>` | `measurement=<sorted tokens, comma-joined>` | `surprise=<type>` (surprise lane only) | `quote_hash=<full sha256>` (rare collision member only); absent slots omitted, never `slice=total`. `quote_hash` appears only when same-id siblings CONFLICT on ≥1 shared non-null signature slot (OD-8; ≤1 bare member per group; pre-batch graph state decides). The ten hashed slots exactly: `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions` — fixed-order compact JSON array preimage, full untruncated SHA-256; quote/state/producer/source/date/XBRL excluded.

5. **The 24 fields** (FINAL_DESIGN §7.1): **Code (6):** `id · fact_scope · series_unit · created · date · source_type`. **Semantic/enrichment (18):** `driver_state · quote · level_low · level_high · level_unit · change_value · change_unit · comparison_low · comparison_high · comparison_baseline · value_text · conditions · company_confirmed · xbrl_qname · fiscal_year · fiscal_quarter · period_scope · time_type`. Recovery-only `disputed` is outside the count.

6. **Own parts = slices; external causes = names; portions = names.** The name carries the cause only, so the same Driver reuses across companies (NAME-01, §1 mission); a company's own measured business population (segment/product/geography/customer/channel/owned entity — "revenue/earnings from ___" works) is identity's slice slot, not a new name (NAME-10, FS §5.2). An external actor/platform/policy whose own independent action IS the cause stays in the name (`fed_rate`, `aws_outage`) — there is no vendor slice kind, and the local role test keeps unclear roles in the name (NAME-11, NAME-15/16 carve-outs, §3). Portion qualifiers (`current`, `funded`, `fee_earning`) change the measured population itself → a different Driver, never a slice or measurement (OD-17 §3; portion-qualifier supersets are PERMANENT link auto-refusals, BUILD §8.1.6) — all governed by the asymmetric law: collapsing different meanings is permanent damage (§1).

7. **Absent concept/member links.** Goal: attach the exact company-reported concept or NOTHING (FINAL_DESIGN §8). Links may be absent by design: guards G0/G1/G2 abstain (events/macro, ratios/derived, non-GAAP measurement), verify defaults REFUTED when unsure, deterministic vetoes can only ABSTAIN, action never links, guidance/surprise only inherit via `BASE_METRIC` (blocked on non-GAAP), `MAPS_TO_CONCEPT` is zero-or-one best-effort and `MAPS_TO_MEMBER` zero-or-more (§7.3, §5.2); a missing graph concept never blocks the fact and self-heals later. Wrong links are worse because "missing links are safer than wrong links" (§1): a wrong concept silently corrupts cross-company series/reads permanently, while absence is repairable — the measured veto evidence (42→18→1 wrong at no recall cost, XC-07) and XC-17 monitoring exist to keep wrongs near zero, not to maximize coverage.

8. **Raw channel submission vs internal Candidate Fact Packet.** Raw submission = the public boundary (ChannelContract.md §3): envelope + as-stated raw items (verbatim quote, raw label/claim, signed unscaled values + raw unit text, period signals, exact XBRL context with verified `dimensions=[]`, guidance attribution EVIDENCE); channels must NOT send names, ids/fact_scope, fiscal fields, measurement tokens, canonical units, or computed numbers (§4 — sent anyway ⇒ ignored/recomputed). The internal Candidate Fact Packet (frozen v1.0, 15_CandidateFactPacket.md Part A; summarized BUILD §2) is what the SHARED DECOMPOSER produces from that raw input: Block 0 envelope · Block 1 TRANSIENT identity signals incl. `proposed_name`/slice_tokens/measurement_spans/per_x (proposals for the kernel, never stored raw) · Block 2 the proven fact + transients (code builds id/fact_scope/series_unit/created/date) · Block 3 optional verdict. FINAL_DESIGN §2 states the split: public input boundary = ChannelContract; internal core object = the frozen packet.

9. **Status buckets** (owning rows = STATUS_AND_HISTORY.md §1/§2; FINAL_DESIGN §10 is the generated mirror):
- **Final-but-unbuilt:** Track A remainder (incl. OD-6 fitness gate, never run) · UNIT-14 wiring · PER-20 resolver+21 tests · slice table + PIT menu code · concept-linker vetoes C/D + PIT query · the whole Track B writer/validator/CLI/park-ledger stack (S3 awaits owner GO) · read layer · verdict/DCM writer · channel adapters+certification · Track C execution · incremental refresh.
- **Design-incomplete:** the production running layer (BUILD §7 runbook list); OD-5 scanner is a recommendation only.
- **Conditional:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (dormant until P19 proofs X-XL0-3 + hard pre-gates) · multi-run concept stability/caching.
- **Approved working design (owner 2026-07-15, NOT activated, gates/OFF-switches in force):** Admission Kernel v3.4 (BUILD §8.1) · XBRL-native materializer (BUILD §8.2).
- **Candidate:** Bayes learner proposal (unvetted, BUILD §8.3) · Driver Genesis restructure (rationale only).
- **Open (owner):** G1 reuse display · 796-vs-786 + lifecycle/IPO · model/cost policy beyond EXP-2 · FS-23 · 8-K taxonomy · DCM threshold/pure-macro/two-catalyst · dual-producer thresholds · non-USD · metric value_text/action conditions revisit triggers · Driver Genesis charter · Track C history-gap · `company_confirmed=false` class enablement.
- **Retired:** old Guidance replay · fixed-vocab v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range` · quiet `gp_UNDEF` · `evhash16` · FS-22 · RavenPack import · catalog-first reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all sync (STATUS §2 RETIRED).
- **Historical:** the 42 supersession rows' dead rules (STATUS §3), archived originals as evidence-only (both ratified-design originals archived 2026-07-15; BUILD §8 banner), retired `13_Track` GI rows, `66` D-1..D-13.

10. **The complete source→replacement map lives in STATUS_AND_HISTORY.md §7 family:** §7 = the 33-source-file crosswalk (each file → status → destination); §7.1 = the rule-ID crosswalk (every stable ID range — NAME/FS/UNIT/PER/MF/DU/XC/PIPE/FACT/T/GI/D/OD/K2/contract clauses/packet blocks — → its one live anchor, with per-ID exceptions); §7.2 = the census T-group anchors (T1–T12); §7.1b = the ratified-design destination proof (every transferred kernel §1–§16 element → BUILD §8.1.x, every XBRL element/pin/amendment → BUILD §8.2 + owning sections). Supporting: STATUS §3 (42 dead-rule supersession rows + OD-1..21 additions) and §8 (freeze manifest `archive/2026-07-15_pre-consolidation/MANIFEST.json`). Destination ≠ current location: most crosswalk destinations say "archive" but Phase 5 pends owner GO, so the 33 frozen sources currently remain in place as the byte evidence baseline (FINAL_DESIGN banner; BUILD banner) — the exceptions already moved are the two ratified-design originals (archived 2026-07-15, byte-verified); currently still live at root: the four live files, `15_CandidateFactPacket.md` (temporary fifth live file, sha `aa7239ed…`), and `FableExperimentPlan.md`/`FableExperimentWorkOrder.md` until the experiment program migrates; `ChannelContract.md` is kept (moves with the code at reorg).

---

## ROUND-18 CORRECTION ADDENDUM (2026-07-15 — additive; nothing above was rewritten)

**The 10/10 grade is WITHDRAWN → re-graded 6/10 strict. The run's file-certification value is VOID:** the tested FINAL_DESIGN/STATUS bytes themselves omitted the EXP-6 convergence evidence from the materializer/rider unlock (fixed in round 18; BUILD stated all three conditions at test time).

Answer flaws found in the round-18 external review, each verified against the live law:

1. **Q3** — the rubric demanded `driver_state` + the FORBIDDEN fields per lane for EACH of the five examples; the actual-surprise example lists no forbidden fields, and the guidance-vs-consensus example lists neither its state nor its forbidden fields.
2. **Q7** — "corrupts cross-company series/reads permanently" overstates: wrong links are revocable by design (XC-18 ConceptResolution revocation states, ratified 2026-07-15, dormant until the materializer enables — FINAL_DESIGN §8). The correct claim: wrong links corrupt SILENTLY until detected, which is why missing links are safer than wrong links.
3. **Q9** — the conditional bucket omitted EXP-6 from the materializer/rider unlock. File-induced (FINAL §10/STATUS §2 omitted it at test time) — but BUILD §8.2 stated all three conditions inside the same permitted source set, and the reader did not flag the discrepancy.
4. **Q10** — "the 33 frozen sources currently remain in place" is wrong as stated (31 remained at root; the two ratified-design originals were already archived) — the sentence contradicts its own exception clause.

**Prompt-block truncation repair:** the stored snippet above ends mid-expression at `].join('\n`. The persisted workflow manifest (session `workflows/wf_2e462b6d-c84.json`, field `script`) ends:

```js
].join('\n')
phase('Test')
return await agent(Q, { label: 'official-reader-run-10', phase: 'Test' })
```

All ten Q-array lines quoted above were and are complete; only the closing `')` and the two dispatch lines were cut from the stored snippet.

**The definitive reader test** is the Phase-5 post-move run (execution card step (10) / step 24b): the official §14.3 ten, unmodified, against the post-archive seven-file root, with a durable in-repo record.
