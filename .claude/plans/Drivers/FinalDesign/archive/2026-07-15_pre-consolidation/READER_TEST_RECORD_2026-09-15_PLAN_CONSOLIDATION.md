# Plan consolidation — independent reader record, 2026-09-15

## Result: NOT QUALIFIED

The reader did not complete the required source reading: WorkOrder lines
634–862 (229 lines) were never returned by a Read call. The saved answers
also fail the locked correctness rule. Codex's independent answer assessment
is **6 pass / 4 fail**, not a valid qualification score for an incomplete run.
Core SEQ 2181's **10/10 PASS is not accepted**. No failed answer is repaired,
replaced or counted as correct. No repeat model call was made.

This is a document-understanding check, **not an A7 grading run**. The Plan
move itself preserves every original byte and its affected checks pass.
Neither that preservation nor this failed reader run establishes Step 6,
production readiness, approval of pending Plan V2, or permission to resume A7.
Publication remains held pending a valid review or an explicit owner exception
for publishing the layout-only checkpoint with this failure disclosed.

## Exact frozen source

- Main freeze: `d9ec0cdcffd5ca78811fe539880b004c0c8ffded`;
  tree `ea049f3dc6c0198e1679dc9e8b61a9fe4745ad86`.
- Recovery freeze: `b4b8b840ae4fef08deed61ef5f1a94c2edf8c559`;
  tree `637350beaac68c7fd4e1b306bacf73eb543bfd83`.
- Detached read/test copy: `/home/faisal/EventMarketDB-plan-review.Ccv1z8`,
  at the main freeze. All six documents equal the recovery freeze.
- Hashes were checked before and after the run. The detached tree remains
  unchanged and clean. This append-only record does not alter its inputs.

| File in FinalDesign | SHA-256 | Actual lines read / total |
|---|---|---|
| FINAL_DESIGN.md | `497c21f52c6ecf253b7482c1c9ee1bd04ac9fc02a10a66e3ebf76cb9af771d10` | 321/321 |
| ChannelContract.md | `fd3a90a55c7e890e870f1b30418b0bb9864e9b91623d50bbbf0ec1eadbc1717d` | 719/719 |
| BUILD_AND_OPERATIONS.md | `7963b80a5852bf5a51c847604a22e4124d669ecbde907cf16752cc4ea42d4a1a` | 879/879 |
| STATUS_AND_HISTORY.md | `38ed372737d58367ff3b49797af43d7a4f0555269fdd8af45717fe890f34fc04` | 786/786 |
| FableExperimentPlan.md | `7ee647382b6d53bdef4e55be3047eb864541745e7d4eff5388c26afc918e3a9b` | 669/669 |
| FableExperimentWorkOrder.md | `23854f459500e44d4ba238cc118bbd74bc1de405c071de2b43d9015875751343` | 633/862 |

The 11 Read results were compared line-by-line with the frozen files: no
returned line differed. Five files were read completely. The second WorkOrder
read requested offset 334, limit 300, and stopped at line 633; no later read
covered its remaining 229 lines. All file-reading tools stayed within the six
permitted files. The only other tool was the final SendMessage.

## Execution and identity evidence

- Codex task: SEQ 2183, SHA-256
  `757d758d2a83b9c09fe41e7f767e3f8307575a5531a375f6e8af8caf3f65c5ce`.
- Core final report: SEQ 2181, in reply to 2183, SHA-256
  `4ef3a2b0bbd660009b9148c9ceecbcb96960b17e9c3059b228facf6077e5d323`;
  byte-identical to `/home/faisal/.core827-orchestrator/archive_CORE_2181.md`.
- Core session: `5ae9b86b-f0f6-4449-beee-9cac7cfa7200`;
  Codex thread: `01a05829-3086-73e0-89c9-e5773b322d80`.
- Native Agent launch: 2026-09-15 22:46:58.887 UTC,
  `toolu_01DUFCMH2YkW9F4LuoXrzHgC`, requested `sonnet`,
  agent `lean-probe`, name `r8reader`, in-process subscription teammate.
- Returned model in the native child transcript: **`claude-sonnet-5`**.
  Core reports high effort, but the saved Agent input has no effort field;
  runtime high-effort selection is **not independently proved**.
- Full answer sent at 2026-09-15T22:52:08.086Z,
  message UUID `5c0b5906-4e86-4569-9187-885bc3ada8f9`,
  tool ID `toolu_01NLaN8Aa6KkKn2Yc4FrBcuS`.
- Native child transcript:
  `/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/subagents/agent-ar8reader-f8455fd852e91114.jsonl`;
  SHA-256 `789996e4a7e72e3b5e737e403ce2ab46f391ceb35367eebbd88701265bbfa5de`.
- Public prompt/receipts and Core grade:
  `/home/faisal/.core827_backups/plan_docs_2183/`.
  Core's GRADE.md SHA-256:
  `b9b939f811b0b493840f51503deac335e67212170873423e60ea80f95156c277`.
  Its assertion of a complete read and 10/10 is contradicted by the raw evidence.
- Prompt SHA-256:
  `0c4a819cc0b1155a4a9d4ee915a908df4db8513a0582d2de69766f79ca7c2e59`.
  The reader's initial message contains this exact prompt. Against the
  July final-run15 R7 prompt, only seven-to-six source count, removal of the
  relocated packet entry, source numbering and frozen absolute paths changed.
  No question, answer hint or grading rule changed.

## Independent answer assessment

Authority: the frozen live documents, with the locked natural-reading/no-rescue
rule in `READER_TEST_RECORD_2026-07-16_phase5-final-run15.md` §§1/7–8.
A disclosure that an assumption was invented does not supply the missing evidence.

| Question | Assessment | Evidence |
|---|---|---|
| 1 | PASS | Correct class/fact distinction, asymmetric merge risk and reversible repair; FINAL_DESIGN §§0–1. |
| 2 | FAIL | Explicit “year-over-year” is wrongly justified with OD-11's **bare** dated-period fallback. “Rose” supplies direction, but the answer cites an unstated prior numeric value as the state mechanism. It also applies same-day source rank to a **later** 10-Q; different days use latest date. FINAL_DESIGN §§4.3, 6.1, 9. |
| 3 | FAIL | The actual-surprise quote supplies an actual and a consensus expectation, not temporal direction; its metric home must be **reported**, not **increased**. The guidance home “above” is a 2100–2200 range, not the asserted 2150 point, so the required normalized-value match is false. FINAL_DESIGN §§1, 4.3, 5.1, 7.1 DU-15. |
| 4 | FAIL | “Conflict against a sibling” is insufficient when multiple siblings exist: only conflict-with-ALL hashes; compatible-but-not-exact parks. The full multiple-sibling/competitor cases are omitted despite the explicit all-cases instruction. FINAL_DESIGN §5.1 OD-8. |
| 5 | PASS | Exact 24-field list and 6 code / 18 semantic-enrichment ownership; FINAL_DESIGN §7.1. |
| 6 | PASS | Own populations, external causes and qualifying portions correctly distinguished; FINAL_DESIGN §3 NAME-10/11 and OD-17. |
| 7 | PASS | Correct abstention and wrong-link asymmetry; FINAL_DESIGN §§1, 7.3, 8. |
| 8 | PASS | Correct raw-public versus interpreted-internal boundary, separate responsibilities and Part III location; ChannelContract opening table and Parts I/III. |
| 9 | PASS | Status categories distinguished and later settled-for-v1 exceptions retained; STATUS §§1–2 and FINAL_DESIGN §10. |
| 10 | FAIL | Calls the §7 file crosswalk a “33-row table”; it has **26 data rows**, grouping historical sources. The locked prompt explicitly requires exact counts. Its main destination/current-location distinctions are otherwise correct. |

The material errors in questions 2–4 independently prevent a pass; the result
does not depend on the table-count finding or on missing effort proof.
These are mistakes in this reader answer, not proof that the Plan move
changed Driver rules. Do not alter those rules or coach/relabel the answer
to manufacture a passing review.

Core also identified stale original-file packaging instructions in the
dated 2026-08-11 STATUS freeze paragraph (lines 559/564 at this snapshot).
The current ChannelContract cover and STATUS §1 already define Part I public
V1, Part II staged public V2 and Part III internal V1. A short location note
should make the dated paragraph's old file names and promotion/deletion
instructions explicitly historical; retain the original freeze text and hashes.

## Deterministic preservation and checks

- Both original Plan bodies compare byte-for-byte with pre-move Git blobs:
  V1 336 lines, SHA-256
  `05c9c8381063fcb436e560d1ad271e8ca8e64d7a2682b3a855fcacdc2404128b`;
  V2 277 lines, SHA-256
  `6d66d3b8197d521d9ebf3f0e88fac18786f68fda82af62a142d3cb7f91807716`.
  All **613** original lines survive; V1 active and V2 PENDING O-b remain separate.
- WorkOrder is unchanged, separately stored and hashed above.
- Both working trees: 14 direct tests passed, including deletion of every
  original line, 10 boundary corruptions, section-scoped V2 assertions and the
  real package artifact reader's positive/missing-file controls.
- Frozen committed clean tree: **400 passed, 0 failed, 0 skipped**, 62.23 seconds;
  pytest exit 0. Modules: `test_rev4_gate.py` (14),
  `test_harness_guards.py` (360), `test_no_semantic_patterns.py` (26).
  Command: `PYTHONDONTWRITEBYTECODE=1 /home/faisal/EventMarketDB/venv/bin/python -B -m pytest -q -p no:cacheprovider .claude/plans/Drivers/experiments/harness/test_rev4_gate.py .claude/plans/Drivers/experiments/harness/test_harness_guards.py .claude/plans/Drivers/experiments/harness/test_no_semantic_patterns.py --junitxml=/tmp/plan-consolidation-check.AN2tQk/frozen-publication.xml`.
- Broader preparation run in **each** worktree: 515 passed, 3 pre-existing
  failures, 2 deselected. The two underlying failures were reproduced again
  on the exact committed clean tree (pytest exit 1, 2 failed / 118 deselected):
  `test_G19_two_rebuilds_are_byte_identical` and
  `test_the_pin_inventory_is_REPEATABLE_and_matches_disk`. The third failure,
  `test_the_registrys_CLEAN_proofs_run_GREEN_without_any_credential`, reports
  the patch failure. No frozen artifact was regenerated to force green.
- Saved patch: generated
  `ba98b69412a8837c62082e34687a3386f35a84f0fe9f817ab5518e0f6a6fcfeb`
  versus saved
  `5405a4bc66295722d2cdf5bc5ccccb4a9a21672d3b5e83237a0be9f099f392f0`.
  Pin inventory: generated
  `b38a03af15d517a72aa00545afad9e836d769334dc74a028b8631d0c2fce4c83`
  versus saved
  `7388fca392006c2b2ac8c6097c28969b75364bdfcc9de4b977ed11ed597b626f`.
- Correction to the preparation status: only the graph-registry check was
  live-dependent. The other excluded test,
  `test_LIVE_workflow_handoff_delivers_Decimal_to_the_validator`, is explicitly
  an offline/no-AI check and passed in the clean 400-test run. No AI workflow
  success is claimed from that test's name.
- JUnit detail: `/tmp/plan-consolidation-check.AN2tQk/{main,recovery,frozen-publication,frozen-existing-failures}.xml`.
  These logs are local diagnostic copies; this record preserves their results
  and the committed tests permit reproduction. Unrelated owner changes were
  excluded from both commits.

## Exact prompt

```text
You are a brand-new engineer with ZERO prior context. Your ONLY permitted sources are these SIX files (read fully; open NOTHING else — nothing in archive/, no other repo files):
1. /home/faisal/EventMarketDB-plan-review.Ccv1z8/.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md
2. /home/faisal/EventMarketDB-plan-review.Ccv1z8/.claude/plans/Drivers/FinalDesign/ChannelContract.md
3. /home/faisal/EventMarketDB-plan-review.Ccv1z8/.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md
4. /home/faisal/EventMarketDB-plan-review.Ccv1z8/.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md
5. /home/faisal/EventMarketDB-plan-review.Ccv1z8/.claude/plans/Drivers/FinalDesign/FableExperimentPlan.md
6. /home/faisal/EventMarketDB-plan-review.Ccv1z8/.claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md
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

## Saved reader answer — verbatim, not corrected or endorsed

<!-- BEGIN SAVED READER ANSWER -->
1. **Driver vs DriverUpdate + over-merge law.** Driver = "one reusable, atomic cause or standing thing... A class node: name + permanent fact_type + SAME_AS/BASE_METRIC links + birth evidence." DriverUpdate = "one real, source-backed occurrence of a Driver in one source event. The fact node." (FINAL_DESIGN.md §0 Glossary). Over-merge law — "The one law (asymmetric): merging different meanings causes permanent damage; keeping the same meaning separate is repairable. When unsure, keep separate." + "True duplicates stay recoverable through reversible SAME_AS; nodes and facts are never deleted or re-keyed to make history look cleaner." (FINAL_DESIGN.md §1).

2. **One quote through the pipeline** — fixture "Q3 iPhone revenue rose 12% year-over-year to $42.6B" (8-K; assumed AAPL, FYE Sept — not stated by the fixture, flagged as my assumption).
- *Channel* (ChannelContract.md Part I §3): envelope source_type=`8k` (press-release quote = the 8-K's own accession, §3 XBRL row note), ticker/fye_month/event_time from the 8-K; raw item quote verbatim, stated value "$42.6B" signed/unscaled + format flags, period signal "Q3" + cadence.
- *Decomposition* (ChannelContract.md Part III Part B steps 0–7 / BUILD_AND_OPERATIONS.md §2): step0 strip "rose" (NAME-11 step0); step1 measurement_spans=∅ (none stated); step2 per_x=none; step3 portion=none (OD-17 n/a); step4 name-vs-slice: "iPhone"=Apple's own product → slice=`product:iphone` (NAME-10/11, mirrors the iPhone worked example, ChannelContract Part III "Worked examples"); step5 name assembly → `revenue` (NAME-05/06); step6 fact_type: bare name → OD-2 path, DU-06 persistence test → **metric**; step7 unit: "$42.6B"→ canonical `m_usd`, value 42600, `unit_scale_evidence`="B" (smallest in-quote scale marker, UNIT-04 §6.1).
- *Name/slice/measurement/unit/period*: name=`revenue`, slice=`product:iphone`, measurement=∅, level_unit=`m_usd`, level_low=level_high=42600; growth "12% year-over-year" → OD-11 bare dated-period default = `percent_yoy` (§6.1), stored as change_value=12/change_unit=percent_yoy, comparison_baseline=`prior_year` (temporal comparison, never `consensus` — a metric change, not a surprise, §7.2 routing). Period: PER-21 governs 8-K-to-periodic routing upstream (BUILD §3); the fact's own window resolves via cadence+adjacent-wording→fiscal math (no XBRL context in this text quote) to Apple's fiscal Q3; time_type=`duration` (revenue = "amount over a window", BUILD §3); period_scope=`quarter`.
- *driver_state*: source states a comparison alongside the value → **increased** (FINAL_DESIGN §4.3 Metric state rule: "A prior value stated IN THE SOURCE alongside the value routes to increased/decreased instead of reported").
- *Identity* (§5.1): id=`du:{8-K accession}:revenue:{fact_scope}`; fact_scope=`period=<gp_id>|slice=product:iphone` (measurement/surprise/quote_hash omitted — all empty/n-a).
- *Validation* (BUILD §5 validator groups): lane matrix for metric — period required(real) ✓, level/change stated ✓, comparison baseline prior_year allowed (consensus forbidden) ✓, surprise=/value_text/conditions/company_confirmed all correctly absent (forbidden on metric, §7.2); shape hints point+signed-change; quote required ✓.
- *Write* (BUILD §5 Writer / FINAL_DESIGN §4.2): atomic MERGE on id; if no "revenue" Driver exists yet for the company this is **born-complete** (Driver created WITH this first DriverUpdate, §4.2); edges OF_DRIVER→revenue, FROM_SOURCE→the 8-K Event, HAS_PERIOD→DriverPeriod; MAPS_TO_CONCEPT/MAPS_TO_MEMBER absent at write (text-created; XBRL enrichment runs later, §8) — "attach the exact concept or attach nothing."
- *Read* (§9): series key = company·revenue·metric·slice(product:iphone)·period·quarter·measurement(∅)·series_unit·duration; render = level ($42.6B) → signed change (+12% YoY) → comparison(prior_year) → quote fallback; labeled `raw`; source-rank ties `8k>transcript>10q>10k>news` apply if a later 10-Q restates the same fact.

3. **Lane-safe examples** (fields per FINAL_DESIGN §7.2 matrix; forbidden fields omitted as noted):
- *Metric*: Driver `revenue`. Quote "Revenue increased 8% to $500M." **driver_state=increased**. comparison_baseline=prior_year (consensus FORBIDDEN on metric, §7.2); surprise=/value_text/conditions/company_confirmed correctly absent.
- *Guidance*: Driver `revenue_guidance` (BASE_METRIC→revenue). Quote "We now expect full-year revenue of $2.1–2.2B, up from our prior range of $2.0–2.1B." **driver_state=raised** (midpoint up, §4.3 Guidance vocabulary). company_confirmed=true REQUIRED (§7.2); comparison_baseline=previous_guidance-or-null (consensus FORBIDDEN); value_text stays null (numeric, not numberless-only, §7.1); surprise= correctly absent.
- *Actual surprise (actual_vs_consensus)*: Driver `revenue_surprise` (BASE_METRIC→revenue; OD-21 — one surprise Driver holds all 3 types). Quote "Q3 revenue of $42.6B beat consensus estimates of $41.0B." **driver_state=beat** (meaning judgment, not from sign, OD-13). surprise=`actual_vs_consensus`, comparison_baseline=consensus (REQUIRED, §7.2). **Required same-event home fact**: the metric fact `revenue`=$42.6B, **home driver_state=increased**, family=revenue, period=Q3(same), period_scope=quarter, slice=∅, measurement=∅, normalized level=42600 m_usd — matches the surprise's own level 42600 m_usd exactly (FINAL_DESIGN §5.1: "Match family, period, period scope, slice, measurement, and normalized value/unit").
- *Guidance-vs-consensus surprise*: same Driver `revenue_surprise`. Quote "Management's new guidance of $2.15B midpoint compares to Street estimates of $2.05B." **driver_state=beat**. surprise=`guidance_vs_consensus`, comparison_baseline=consensus, period = the guidance **target** period (FINAL_DESIGN §6.2, even if ended). **Required home fact** = the `revenue_guidance` fact above, **home driver_state=raised**, family=revenue, period_scope=annual, slice=∅, measurement=∅, normalized level 2150(m_usd midpoint) matching the surprise fact's own level.
- *Action*: Driver `restructuring` (bare-root DU-06 default → action_event, §4.1). Quote "The company announced a restructuring plan to reduce headcount by 5%." **driver_state=announced**. Period omitted (no real window stated — legal, periodless action has no edge, §6.2); comparison values/baseline null (none stated); value_text/conditions/company_confirmed/direct-XBRL all correctly absent (forbidden on action, §7.2; enrichment abstains on action, §8).

4. **Scope slot order & collision signature** (FINAL_DESIGN §5.1): order is `period=<period_u_id>|slice=<sorted kind:value>|measurement=<sorted tokens>|surprise=<type>` (surprise lane only) `|quote_hash=<sha256>` (rare collision member only) — absent slots omitted, never `slice=total`. **quote_hash appears only in the hash cases** of OD-8's outcome ladder: multiple pairwise-conflicting in-batch facts (all hashed), or a CONFLICT against a sibling under the pre-batch graph state (creates a flagged hashed member) — never on a bare fact or a compatible fill. The ten hashed slots exactly: `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions` — quote/state/producer/source/date/XBRL excluded. Preimage = fixed-order compact JSON array, ASCII-escaped, compact separators, null≠empty-string, one shared text normalizer + one decimal canonicalizer, full untruncated SHA-256.

5. **24 fields** (FINAL_DESIGN §7.1): Code-owned (6): `id · fact_scope · series_unit · created · date · source_type`. Semantic/enrichment-owned (18): `driver_state · quote · level_low · level_high · level_unit · change_value · change_unit · comparison_low · comparison_high · comparison_baseline · value_text · conditions · company_confirmed · xbrl_qname · fiscal_year · fiscal_quarter · period_scope · time_type`.

6. **Own parts vs external causes vs portions**: NAME-10 — "a reporting company's own measured segment, product, geography, customer group, sales channel, or owned entity goes to the slice, not the name," because a slice is "a business population for which 'revenue/earnings from ___' makes sense" (§5.2) — it subdivides ONE population without being a different cause, keeping the Driver name reusable across companies/time (§1 mission) since NAME-01 requires "the name contains the cause only." External causes stay in the name (NAME-11 local role test + NAME-15/16 carve-out: "an external company/platform/institution/person whose own independent action or state IS the cause stays," e.g. `fed_rate`, `aws_outage`) because they ARE a distinct cause, not a population the reporting company measures — NAME-09 "one name carries one cause; split independent causes." Portions (OD-17: `current`, `funded`, `fee_earning`…) stay in the name because they redefine WHICH standing population counts at all (a genuinely different metric/series), not merely a partition of one whole — so `current_rpo` vs `rpo` are permanently different Drivers, never SAME_AS, and portion-qualifier supersets are permanently auto-refused in the LINK judge (BUILD §8.1.6), unlike a slice which never changes Driver identity.

7. **Concept/member links may be absent; wrong is worse**: FINAL_DESIGN §8 — "Goal: attach the exact company-reported concept or attach NOTHING. A wrong concept is far worse than an absent one — the damage is SILENT until detected... while an absent link self-heals on re-runs at zero risk." `MAPS_TO_CONCEPT` is "metric-only, zero-or-one, best-effort" and `MAPS_TO_MEMBER` is "zero-or-more on any lane... may be absent" (§7.3) precisely because the whole pipeline (guards→PIT menu→cheap pick→adversarial verify, default-refute→deterministic veto→write-or-abstain, §8) is built to abstain under any doubt, per the §1 mission law "missing links are safer than wrong links." Wrong links are worse because even after detection and revocation (XC-18 ConceptResolution states), "reads/decisions already made on it before detection are not undone" — the error already propagated silently, whereas an absent link never asserted anything false and heals for free on the next run.

8. **Raw channel submission vs internal Candidate Fact Packet**: The raw submission (ChannelContract.md Part I §3) is the PUBLIC INPUT — source-stated, as-stated-by-source, per-event: envelope + raw items (verbatim quote, raw_label_or_claim, signed unscaled value+format flags, period signals, raw XBRL bundle, guidance evidence); §4 bans sending any final driver name, fact id/fact_scope, computed fiscal_year/quarter, measurement tokens, canonical units, or derived numbers — "sent anyway ⇒ ignored and recomputed." The internal Candidate Fact Packet (ChannelContract.md Part III, frozen v1.0) is the shared core's OWN object, produced BY THE SHARED DECOMPOSER from that raw input, never handed over by the channel: Block 0 envelope, Block 1 transient IDENTITY SIGNALS (proposed_name/slice_tokens/measurement_spans/per_x/quote), Block 2 the PROVEN FACT (driver_name/driver_state/quote/value slots/period fields; code alone builds id/fact_scope/series_unit/created/date), optional Block 3 verdict — Block 1+2 travel together and Block 2 becomes the first DriverUpdate on CREATE (born-complete). Note: ChannelContract.md's own opening "Differences and work still required" table flags that Part III's internal text says the channel "hands" Core the object, while "Part III C/D and the public boundary require raw evidence and shared Core interpretation... Channels follow the public contract, not the internal field list" — i.e. the live, current position is that channels only ever submit the raw §3 shape; the shared Core does the decomposition that builds the internal packet's Blocks 1–2, not the channel.

9. **Status categories** (BUILD_AND_OPERATIONS.md §10 tags + STATUS_AND_HISTORY.md §2):
- *Final-but-unbuilt* = "FINAL / BUILD-PENDING": e.g. Track A remainder, UNIT-14 wiring, PER-20 guard, full slice-table materialization, concept-linker vetoes C/D, Track B remainder, read layer, verdict/DCM writer, channel adapters+certification, Track C execution, incremental refresh.
- *Design-incomplete* = "DESIGN-INCOMPLETE": the production running layer itself (schedules, ledger, retries, backfill, QA/alerting/budgets, model policy, recovery — BUILD §7) plus the OD-5 change scanner ("a RECOMMENDATION only, never final design").
- *Conditional* = "CONDITIONAL": OD-19 (inert until K-pairs.v2 zero wrong-same), XC-16 timing, model-role membership, XBRL-native materializer + `09` rider (dormant until P19), multi-run concept caching (only if monitoring justifies).
- *Approved-working-design* = "APPROVED WORKING DESIGN (owner 2026-07-15; NOT activated)": Admission Kernel v3.4 and the XBRL-native materializer — design only, every gate/dormant state/OFF switch stays in force.
- *Candidate* = "CANDIDATE": Bayes learner proposal (unvetted), Driver Genesis restructure (rationale only).
- *Open* = "OPEN (owner)": catalog target 796-vs-786, full model/cost policy, FS-23, 8-K item taxonomy (earnings-8K pairing itself is CLOSED by PER-21), DCM threshold, dual-producer thresholds, non-USD, value_text/conditions revisit triggers, Genesis charter questions, Track-C history-gap, third-party company_confirmed=false — **exception**: STATUS §2 "Already settled for the first release" narrows several of these (no fixed 786/796 target, no FS-23, no non-USD, no item taxonomy, empty Step-12B channel set) so they are settled-for-v1, not open triggers.
- *Retired* = STATUS §2 "Retired approaches stay retired": Guidance replay, fixed-vocabulary v1, eager/catalog-first live reuse, `slice=total`, alias layers, `long_range` scope, quiet `gp_UNDEF`, `evhash16`, cross-company slice recurrence (FS-22), RavenPack vocabulary, materialize-all sync.
- *Historical* = STATUS §2 "Historical proposals only" (Bayes learner, Driver Genesis restructure — note these are ALSO tagged CANDIDATE in BUILD §10: candidate = never-adopted/unvetted, historical = preserved-but-inactive, same two items carry both labels) plus the obsolete July OPEN/build lists ("preserved in Git..., not repeated as current instructions") and FINAL_DESIGN §10's generated status summary, which "predates later Steps.md rulings" and "cannot reopen those choices."

10. **Source crosswalk** (STATUS_AND_HISTORY.md §7/§7.1/§7.1b/§7.2 — the only in-scope map, per the task's "without opening chat history" limit):
- *File→destination* (§7, 33-row table): e.g. `02_DriverCatalog`→FINAL_DESIGN §3 (archived); `03_Slices_FactScope`→§5; `08_XBRL_ConceptLinking`→§8+BUILD §5; `09_DriverUpdate_Fields`→§7/§9; `12_FactPipeline`→BUILD §5; `13_TrackC`→BUILD §6; `15_CandidateFactPacket`→**moved byte-identically into ChannelContract.md Part III on 2026-09-15** (no separate live file remains — DESTINATION = Part III, and that is now also its CURRENT location); `FableAdmissionKernelDesign`/`XBRLIntegrationDesign`→ratified, mechanics in BUILD §8.1/§8.2, **originals already archived** 2026-07-15; `FableExperimentPlan`/`WorkOrder`→destination BUILD §9, but **current location remains the live files at FinalDesign root** — archiving is deferred "only after the experiment program migrates" (this is the DESTINATION-vs-CURRENT-LOCATION distinction the task calls for); `ChannelContract`→stays the ACTIVE live file itself (not archived); `CONSOLIDATION.md`→moved into the dated archive at Phase-5 step 7.
- *Rule-ID ranges* (§7.1 table, "total over every ID"): `NAME-01..19`→FINAL_DESIGN §3 inline; `FS-01..27`→§5.1–§5.4 (FS-22 RETIRED, FS-23 deferred); `UNIT-01..14`→§6.1 (UNIT-14 build wiring→BUILD §5); `PER-01..21`→§6.2 (PER-20 build→BUILD §5; PER-21 procedure→BUILD §3); `MF-01..12`→§4.1 (MF-11→§7.1 company_confirmed); `DU-01..24`→§4.1–§4.3/§7.1/§7.3 (DU-13..18 explicitly replaced by `09`'s contract); `XC-01..18`→§8; `PIPE-01..37`→BUILD §4; `FACT-01..36`→BUILD §5; `OD-1..21`→per-ID anchors in STATUS §3's additions list; `K2`→BUILD §4; the 43 supersession rows→STATUS §3.
- *T-groups* (§7.2, census `11`): T1 mission constraints→FINAL_DESIGN §1; T2 24-field record→§7.1; T3 identity/scope→§5.1 (OD-8 replaces T3.4); T4 edges→§7.3; T5 verdict→§7.3; T6 lane matrix→§4.1/§4.3/§7.2; T7 DriverPeriod→§6.2 (T7.12 build gate→BUILD §5); T8 units→§6.1 (T8.10→BUILD §5); T9 slice/member→§5.2; T10 concept link→§8; T11 producer contract→§4.2/§5.1/§6.1/§7.1/§9/BUILD §5; T12 read contract→§9.
- *Transferred ratified-design elements* (§7.1b): every Kernel section §1–§16 → its own BUILD §8.1.x sub-anchor (e.g. §6.1 LINK op→§8.1.6, §9 immune system→§8.1.9, §10 recovery→§8.1.10, §15/§16 MVP split/residuals→§8.1's three dedicated blocks); every XBRL design section/pin (§3, §5.2 steps 1-9, §5.3+P14, P1-P17/P19, the ten amendments)→BUILD §8.2's recipe/pin-map, each of the ten amendments individually gate-tagged to its owning section (e.g. amendment 5→§8.1.6 eligibility, amendment 6→FINAL_DESIGN §8 XC-18, amendment 10→§9 collapse rank).
<!-- END SAVED READER ANSWER -->
