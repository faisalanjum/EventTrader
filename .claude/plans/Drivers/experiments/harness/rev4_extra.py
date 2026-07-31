# Rev-4 additional edits v3 (applied on top of the rev-3 table) — addendum round folded in
EXTRA = {
".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md": [
("adapter emits `level_unit_raw` (usd/percent/count from fmt) + `level_unit_kind_hint` (money/ratio/count) + `level_money_mode_hint` (aggregate; price_like only for per-X KPIs) + `level_shape_hint='point'`; shared resolver canonicalizes scale (money → the driver's one scale) — deterministic division, no LLM, **sign untouched**",
 "adapter FORWARDS the raw declared facts only — `value` + `fmt` + `is_currency` + the structured XBRL shape (`xbrl.ix.scale`, `unit_ref`, exact concept/period/dimensions, `source_evidence.pieces` incl. header/footnote scale evidence) — the derived unit hints are RETIRED per O-f (atomically, after the boundary proof; raw values, format flags, scale evidence, periods, and exact XBRL metadata preserved); XBRL-backed facts scale ONCE by the DECLARED `ix.scale` (code-verified, never double-scaled); text facts scale by the reader's stated per-slot {value, scale_multiplier, unit_scale_evidence} — no LLM in the arithmetic, **sign untouched**"),
("resolver error (cents-on-aggregate, pre-scaled), value_ok fail",
 "conversion error (cents-on-aggregate, multiplier/evidence structure fail, declared-scale mismatch), value_ok fail"),
("# S2 — the ONE candidate-fact packet + decomposition spec ❄️ FROZEN v1.0",
 "# S2 — the ONE candidate-fact packet + decomposition spec ❄️ v1.0 (frozen) → v2.0 RE-FREEZE PENDING [O-a owner sign-off; the Block/recipe amendments below take effect at that re-freeze]"),
("- **LLM (proposes the SEMANTIC parts only):** name-vs-slice role test, the cause-only name, a prose slice's kind, fact_type. Per NAME-03/19 + v1's death, the NAME is ALWAYS LLM-proposed",
 "- **LLM (proposes the SEMANTIC parts only):** name-vs-slice role test, the cause-only name, a prose slice's kind, fact_type, driver_state, values/signs/shapes, the final canonical unit + the per-slot scale statement (TEXT lane), per_x, period framing, measurement spans, and abstention. Per NAME-03/19 + v1's death, the NAME is ALWAYS LLM-proposed"),
("code does format, measurement normalization (OD-9), units, member→slice via frozen axis — Part B",
 "code does format, measurement normalization (OD-9), exact Decimal multiplication of the reader's stated scale (TEXT lane) / declared `ix.scale` verification (XBRL lane), member→slice via frozen axis — Part B"),
],
".claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md": [
("unit relocation 29+7 green + parity tripwire · full validator suite TDD",
 "the new conversion suite green (multiply-only converter + evidence membership + the boundary fixtures; the hint-era 29+7/parity gate is RETIRED [PENDING O-c/O-d sign-off]) · full validator suite TDD"),
("test-only shims derive the missing hints (shape from low/high pattern, unit from `canonical_unit`)",
 "the optional test-only shims are RETIRED (rev-4): already-canonical fixture values admit no lawful {value, scale_multiplier, unit_scale_evidence} synthesis — a blind multiplier-1 shim would mis-scale m_usd a million-fold; define an exact evidence-backed inverse or drop the fixture (dropped)"),
("- **CLI order:** hints → compose/validate surprise",
 "- **CLI order:** per-slot statement intake (stated units + {value, scale_multiplier, unit_scale_evidence} objects) → compose/validate surprise"),
],
".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md": [
("Each `facts[]` record = `fact_type` + the 37 model-owned fields (code separates fact_type from the 37-field PreparedFactV1 payload; member_refs + xbrl_concept_raw are source/code-owned, out of the text exam) with the item fields exactly:",
 "Each `facts[]` record = `fact_type` + `part_ref` + `occurrence_in_part` + `per_x` + the `item` of 32 model-owned fields (PreparedFact v2; member_refs + xbrl_concept_raw source/code-owned, out of the text exam); the envelope carries ONE top-level `source_id` echo — the wrong-event ingestion guard — with the item fields exactly:"),
("fact_type (INSIDE each producer facts[] record; code separates it from this 37-field PreparedFactV1 payload) + the 37 model-owned fields:",
 "fact_type (INSIDE each producer facts[] record; code separates it from the 32-field PreparedFact v2 item) + the 32 model-owned fields:"),
("driver_name · driver_state · quote · level_low · level_high · change_value · comparison_low ·\ncomparison_high · comparison_baseline · value_text · conditions · company_confirmed ·\nlevel_unit_raw · change_unit_raw · level_unit_kind_hint · level_money_mode_hint ·\nchange_unit_kind_hint · change_money_mode_hint · level_shape_hint · comparison_shape_hint · surprise_basis_hint ·\nsequential_evidence · has_favorability_wording · polarity_proof ·\nmeasurement_raw_spans[] · period_start_date · period_end_date · fiscal_year · fiscal_quarter ·\nhalf · month · long_range_start_year · long_range_end_year · sentinel_class · time_type ·\nperiod_scope · slice_parts[]",
 "driver_name · driver_state · quote · level_low · level_high · change_value · comparison_low ·\ncomparison_high · comparison_baseline · value_text · conditions · company_confirmed ·\nlevel_unit · change_unit · level_shape_hint · comparison_shape_hint ·\nsurprise_basis_hint · has_favorability_wording · polarity_proof ·\nmeasurement_raw_spans[] · period_start_date · period_end_date · fiscal_year · fiscal_quarter ·\nhalf · month · long_range_start_year · long_range_end_year · sentinel_class · time_type ·\nperiod_scope · slice_parts[]\n(each of the five numeric slots is a {value, scale_multiplier, unit_scale_evidence} object;\nper_x + part_ref + occurrence_in_part ride at fact level, source_id once at the envelope top)"),
("ORDER-FREE 1:1 fixpoint (quote overlap on the UNIQUE-span quote OR value equality post-canonicalization via `unit_resolver` import); a matched produced fact is consumed globally so one produced fact never credits two gold facts; ties/unclear → grader confirms same-fact",
 "ORDER-FREE exact one-to-one bijection (exact complete canonical record + exact locator, unique both ways, per the rev-4 Part D law — no overlap, no value-equality commit); a matched produced fact is consumed globally so one produced fact never credits two gold facts; ALL remaining facts go to build-time grading"),
("located by the audit-only `occurrence` — a GLOBAL 1-based count over `text_parts` (parts in canonical order; matches left-to-right within a part; never reset per part; never spanning a part))",
 "located by `part_ref` + `occurrence_in_part` (per-part; null when the quote is unique in that part; code-verified against the part text))"),
("(4) Field accuracy over the `fact_type` + 37 model-owned fields on matched pairs",
 "(4) Field accuracy over the `fact_type` + `per_x` + the 32 model-owned item fields on matched pairs"),
("| `.claude/plans/Drivers/WIP/unit_probe/unit_resolver.py` | EXP-5/6 value canonicalization by read-only import |",
 "| `.claude/plans/Drivers/WIP/unit_probe/unit_resolver.py` | RETIRED (rev-4): EXP-5 uses the shared multiply-only converter; EXP-6 uses declared XBRL metadata — no unit_resolver import |"),
],
".claude/plans/Drivers/experiments/keys/K-fields/protocol.md": [
("**Producer output contract (what EXP-5 scores — distinct from this gold key).** The producer emits `{\"facts\":[<fact_type + the 37 fields above>], \"abstentions\":[{\"quote\",\"reason\",\"occurrence\"}]}`. `abstentions[]` is producer-only (never in the gold key): each row = a verbatim quote + short reason for a REAL candidate the producer cannot lawfully resolve. `occurrence` is CONDITIONAL — a GLOBAL 1-based count — scan the event's `text_parts` in canonical order and count each verbatim match left-to-right within a part, continuing the SAME count across parts (never reset at a part boundary); a match never spans two parts, REQUIRED only when the quote repeats, kept OUTSIDE the 37 PreparedFact fields (abstentions are never written). Scoring: a gold-linked abstention (1:1 to an otherwise-unmatched gold fact) is a park + recall miss; a non-fact abstention is diagnostic-only.",
 "**Producer output contract (what EXP-5 scores — distinct from this gold key).** BOTH roles emit the SAME envelope: `{\"source_id\", \"facts\":[{fact_type, part_ref, occurrence_in_part, per_x, item:{the 32 fields}}], \"abstentions\":[{\"quote\",\"reason\",\"part_ref\",\"occurrence_in_part\"}]}`. Abstentions are emitted by drafter AND producer; adjudication DROPS abstentions when building the final gold-key rows (they are never stored). `occurrence_in_part` is PER-PART: null when the verbatim quote appears exactly once in the named part, else the 1-based left-to-right count within THAT part — code-verified against the part text; this NARROWLY supersedes the earlier global count for event facts and abstentions only. The ONE top-level `source_id` echo is the wrong-event ingestion guard (harness-verified); the assembled prompt DELIVERS source_id in its event view for both roles. Scoring: a gold-linked abstention (1:1 to an otherwise-unmatched gold fact) is a park + recall miss; a non-fact abstention is diagnostic-only."),
],
".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md": [
("## 6. Decimal-safe transport — TO BE PROVEN (open implementation item)\n\nHonest status: this is NOT proven today. The current launcher returns\nSCHEMA-PARSED objects — the workflow `agent(..., schema=…)` path parses the\nmodel's JSON (default float parsing) before I ever see raw text, so a\nhigh-precision decimal is ALREADY lossy at that boundary. Saving \"raw bytes\"\nafter a parse proves nothing.\n\nThe required change (implementation, after approval): capture the model's reply\nas RAW TEXT at the agent boundary (the string, never a pre-parsed object), write\nthat exact text to disk, and ONLY THEN parse with `parse_float=Decimal`.\nNamed RED regression to WRITE at that point: a reply containing\n`1.000000000000000000001` and a `2^60`-vs-`2^60+1` pair round-trips through the\nreal transport → the on-disk raw string is byte-identical to the model's emit\nAND the parsed value is the EXACT Decimal (not a float). Until that test is\ngreen, Decimal-safety is a REQUIREMENT, not a fact. All downstream comparisons\nalready run dec_canon exact decimals with no float `repr` bridge; the open gap\nis purely the transport capture.",
 "## 6. Decimal-safe transport — PROVEN (built in the v2.0 arc)\n\nStatus: PROVEN. The launcher passes NO `schema:` — agents return RAW TEXT\n(the JS float boundary is removed entirely); `raw_transport.py` writes that\nexact text to disk (mode \"x\", refuses overwrite) and ONLY THEN parses with\n`parse_float=Decimal` (NaN/Infinity and duplicate JSON keys rejected at any\ndepth). The named RED regression EXISTS AND IS GREEN: a\n`1.000000000000000000001`-class pair round-trips byte-identical and parses to\nthe EXACT Decimal — mutation-verified by removing `parse_float=Decimal` and\nwatching it fail. All downstream comparisons run dec_canon exact decimals\nwith no float `repr` bridge."),
("The abstention's quote is located by its `occurrence` field — a GLOBAL 1-based count — scan the event's `text_parts` in canonical order and count each verbatim match left-to-right within a part, continuing the SAME count across parts (never reset at a part boundary); a match never spans two parts — required only when the quote repeats (audit-only, outside the 37 PreparedFact fields).",
 "The abstention's quote is located by `part_ref` + `occurrence_in_part` — per-part; null when the quote is unique in that part, else the 1-based left-to-right count within THAT part; code-verified against the part text (audit-only, outside the 32 PreparedFact v2 item fields)."),
],
}

EXTRA.setdefault(".claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md", []).append(
("- **The VERBATIM classifier prompt text (DU-05 + DU-06, copied exactly — per DU-07 add NO extra clauses or examples; a tested extra clause overfit):**",
 "- **The VERBATIM classifier prompt text (DU-05 + DU-06, copied exactly — per DU-07 add NO extra clauses or examples; a tested extra clause overfit):** **[v2.2-rev4 AMENDMENT — OWNER-APPROVED 2026-07-26, form O3 (F14): the reader-facing card may RESTATE these two definitions with ONLY plumbing labels (DU-05/06 names, the OD-21 tag, the provenance sentence) and typography changed; the terminal `_guidance`/`_surprise` suffix notation and the three comparison-type names are RETAINED; meaning-identical, side-by-side verified (rev-4 package F13); THIS locked text remains the meaning authority; DU-07's no-added-clauses rule is unchanged.]**"))

EXTRA[".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md"].extend([
("- **Producer prompt contract:** packet = event `text_parts` + `{ticker, fye_month}` + the slice menu",
 "- **Producer prompt contract:** packet = `source_id` + event `text_parts` + `{ticker, fye_month}` + the slice menu"),
("code-comparable directly (values post-scaling, shapes, signs per OD-12",
 "code-comparable directly (the three numeric-object fields EXACTLY — value, scale_multiplier, unit_scale_evidence; converted scalars serve storage and XBRL truth-comparison only; shapes, signs per OD-12"),
])
EXTRA[".claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md"].append(
("stamp `series_unit`. Authority split: code owns format norm, axis tables, unit/period/ID build, ALL validators;",
 "stamp `series_unit`. Authority split: the MODEL decides unit/scale/time meaning (stated per slot); code owns format norm, axis tables, exact Decimal arithmetic + declared-scale verification, period/ID build, ALL validators;"))
EXTRA[".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md"].append(
("The fixpoint below is HISTORICAL:",
 "\n\n### HISTORY — superseded matching algorithm (record only, not active law)"))

EXTRA[".claude/plans/Drivers/experiments/keys/K-fields/protocol.md"].append(
("drafters receive EXACTLY the producer packet — event\n`text_parts` + `{ticker, fye_month}` + the PIT slice menu + the verbatim ITEM\nCONTRACT — because gold `slice[]` picks are graded against that same menu",
 "drafters receive EXACTLY the producer prompt from the ONE shared builder —\n`source_id` + event `text_parts` + `{ticker, fye_month, event_date}` + the PIT\nslice menu, all inside the single assembled prompt (no separate contract file)\n— because gold `slice[]` picks are graded against that same menu"))
EXTRA[".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md"].append(
("of a matched fact → dedup, no penalty; (2)",
 "of a matched fact → deduplicated for counting (no double credit) BUT recorded\nas an emit-once CONTRACT VIOLATION feeding the reliability gate — a run with\nduplicates cannot PASS silently; (2)"))
EXTRA[".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md"].extend([
("value slots `level_low / level_high / change_value / comparison_low / comparison_high",
 "value slots — each populated numeric slot a `{value, scale_multiplier, unit_scale_evidence}` object — `level_low / level_high / change_value / comparison_low / comparison_high"),
("OUTPUT: `{proposed_name, slice_tokens[], measurement_spans[], per_x}` + `fact_type` + unit.",
 "OUTPUT: `{proposed_name, slice_tokens[], measurement_spans[], per_x}` + `fact_type` + the stated final unit + the per-slot `{value, scale_multiplier, unit_scale_evidence}` objects."),
("`{quote (verbatim) · raw_label_or_claim · stated value(s)/unit text · stated period fields",
 "`{quote (verbatim) · raw_label_or_claim · stated value(s)/unit text FORWARDED VERBATIM — the shared CORE decomposer (never the channel) produces the per-slot {value, scale_multiplier, unit_scale_evidence}; XBRL-backed rows carry STRUCTURED identity (ix.scale / unit_ref / source_evidence), never a fabricated text locator · stated period fields"),
("Block2{metric fact: level_low=level_high=201183, level_unit=m_usd, quote=\"iPhone $ 201,183\", period FY2024}",
 "Block2{metric fact — an XBRL-BACKED row: displayed value 201183 + STRUCTURED identity (ix.scale=6, unit_ref=usd, source_evidence pieces incl. the \"(in millions)\" header) → verified ONCE by code → 201,183 m_usd; level_unit=m_usd, quote=\"iPhone $ 201,183\", period FY2024. (A TEXT-lane fact would instead carry {value, scale_multiplier, unit_scale_evidence} with the evidence INSIDE its quote — extend or abstain.)"),
])
EXTRA[".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md"].append(
("**Audited scope (2026-07-25).** The `run_event` closure is 12 modules:",
 "**Audited scope — SUPERSEDED COUNTS (the closure is DERIVED at every gate run, never pinned).** The 2026-07-25 name-heuristic-era counts (12 modules; 37/35) were corrected the SAME DAY — the gate follows real imports (last derivation: 39 production / 37 exam files) and no fixed number is law. Option A (value_text) is OWNER-RESOLVED (2026-07-25). The exact evidence locator is REQUIRED; NO exact-quote fallback exists (rev-4 matching law). The historical module list below is record only:"))

EXTRA[".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md"].extend([
(" \"gold_item\": { /* the FULL FACT-17b item, incl. transients — field list §4/EXP-5 */ },",
 " \"part_ref\": \"p01\", \"occurrence_in_part\": null, \"per_x\": null,\n \"item\": { /* the PreparedFact v2 32-field item — field list §4/EXP-5 (rev-4) */ },"),
("**The one open item — `driver_validators.py:59 _VALUE_TEXT_NUMERIC`.** It asks",
 "**`driver_validators.py:59 _VALUE_TEXT_NUMERIC` — OWNER-RULED 2026-07-25 (Option A; no longer open).** It asks"),
("**OPEN OWNER DECISION** — see `experiments/OWNER_DECISION_value_text_numeric.md`\n(recommended: replace the text pattern with the structural rule *\"if any numeric\nslot is populated, `value_text` must be null\"*). Until the owner rules, it stays\nunchanged and this gate records it as OPEN — never as clean.",
 "**RULED question — Option A approved**: the structural rule (*\"any numeric slot\npopulated ⇒ `value_text` null\"*) + model judgment + hidden-grading attacks +\nabstention replace the text pattern; the regex deletes at the rev-4\nimplementation (`experiments/OWNER_DECISION_value_text_numeric.md`, example\nrows corrected 2026-07-26). Until implementation it is counted DEBT."),
("**Exam path status.** Zero patterns. The 20-char `_overlap` sliding window is\nDELETED and replaced by exact evidence identity (`evidence_locator`, else exact\nquote equality); `fact16_checks`/`_NUMY` retire with the run_event wiring.",
 "**Exam path status.** The 20-char `_overlap` sliding window is DELETED; matching\nrequires the EXACT locator (`part_ref` + `occurrence_in_part`) — NO quote-only\nfallback exists (rev-4 law); `fact16_checks`/`_NUMY` retire at the rev-4\nimplementation and are counted DEBT until then — never reported as \"zero\npatterns\"."),
])
EXTRA[".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md"].append(
("### Structured-channel nuance (needs owner confirm — folded into missing-rule #4)",
 "### Structured-channel nuance (RESOLVED by the rev-4 ownership table — final sign-off rides the A1-A6/O-f approvals)"))

EXTRA[".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md"].extend([
("\"abstentions\":[{\"quote\",\"reason\",\"occurrence?\"}]",
 "\"abstentions\":[{\"quote\",\"reason\",\"part_ref\",\"occurrence_in_part\"}]"),
("+ the event VIEW (`text_parts` + `{ticker, fye_month, event_date}` + the pinned model-view slice menu, honest decoded display)",
 "+ the event VIEW (`source_id` + `text_parts` + `{ticker, fye_month, event_date}` + the pinned model-view slice menu, honest decoded display; the untrusted-evidence BOUNDARY line precedes it and the event is LAST)"),
("Deduplicate emitted items (full canonical fact key) BEFORE the park rate",
 "Deduplicate emitted items (full canonical fact key) BEFORE the park rate — dedup prevents double credit ONLY; any duplicate emission is an emit-once CONTRACT VIOLATION feeding the reliability gate (a run with duplicates cannot PASS silently)"),
])
EXTRA[".claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md"].extend([
("- **CLI order:** per-slot statement intake (stated units + {value, scale_multiplier, unit_scale_evidence} objects) → compose/validate surprise → fuse → period/slice/measurement → units/canonical values →",
 "- **CLI order:** per-slot statement intake (stated units + {value, scale_multiplier, unit_scale_evidence} objects) → compose/validate surprise → period → units/canonical values (BEFORE fusion — the §11.4 owner amendment) → slice/measurement → fuse →"),
])
EXTRA[".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md"].extend([
("detected FIRST; ALL remaining facts go to build-time grading — no filters, no",
 "detected FIRST — the whole duplicate-gold group is INCONCLUSIVE (adjudication, never first-match); the exact complete canonical record compares the THREE object fields per numeric slot ({value, scale_multiplier, unit_scale_evidence} — converted scalars never score); ALL remaining facts go to build-time grading — no filters, no"),
])

EXTRA[".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md"].extend([
("set + LOCKED formulas (workorder:643):", "set + LOCKED formulas (the WorkOrder locked-bars block):"),
("code-comparable fields (score_exp5.py:423), NOT a per-field MIN**", "code-comparable fields (score_exp5.py::score_arm), NOT a per-field MIN**"),
("(claude-sonnet-5 @ effort=high; FableExperimentWorkOrder.md:164).", "(the EXP-0-qualified grader tier ONLY, two independent instances — the WorkOrder grader convention)."),
])
EXTRA[".claude/plans/Drivers/experiments/keys/K-fields/protocol.md"].append(
("gold labels, realized returns, or any\n> event_time context.", "gold labels, realized returns, or any post-event_time context."))

# ---- REV-4F corrective round (reviewer's post-4e sweep, 2026-07-26) ----
EXTRA.setdefault(".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md", []).append(
("A channel never mints a name. It hands the shared core ONE object. That object has three blocks, and all three field-lists already exist in the locked design:",
 "A channel never mints a name. It SUBMITS raw evidence (ChannelContract v1.0); the SHARED CORE decomposer assembles this ONE internal object from that submission — including the per-slot numeric objects, which the channel never builds. The object has three blocks, and all three field-lists already exist in the locked design:"))
EXTRA[".claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md"].extend([
("frozen vectors: `driver/core/driver_ids.py` + `driver/core/test_driver_ids.py` (52 tests incl. 14 pinned\n  vectors with computed hashes; changing a pinned vector = an owner-level ID-law amendment).",
 "frozen vectors: `driver/core/driver_ids.py` + `driver/core/test_driver_ids.py` (the pinned computed-hash\n  vector suite — counts live in the test file itself, never restated here; changing a pinned vector = an\n  owner-level ID-law amendment)."),
("   -> internal Candidate Fact Packet (frozen v1.0 — §2)",
 "   -> internal Candidate Fact Packet (frozen v1.0 → v2.0 re-freeze pending O-a — §2)"),
("## 2. The internal core packet (frozen Candidate Fact Packet v1.0)",
 "## 2. The internal core packet (frozen Candidate Fact Packet v1.0 → v2.0 RE-FREEZE PENDING [O-a])"),
("current post-amendment sha `aa7239ed…`, pre-amendment baseline `86b2fc17…` pinned in the\n  Phase-1 manifest)",
 "current post-amendment sha `aa7239ed…`, pre-amendment baseline `86b2fc17…` pinned in the\n  Phase-1 manifest; the sha is RE-STAMPED by the O-a v2.0 re-freeze sweep in the SAME atomic commit that applies the packet amendments — no stale-pin window)"),
])
EXTRA[".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md"].extend([
("## 1. Order-independent one-to-one matching (replaces greedy file-order)",
 "## 1. Matching — the rev-4 Part D law (exact one-to-one bijection)"),
("1. Build the full bipartite candidate graph gold ↔ produced per event.\n2. Repeat until no change, each round computed SIMULTANEOUSLY from the current\n   graph: (a) golds with exactly ONE live candidate; (b) a produced fact claimed\n   by exactly ONE such gold → COMMIT the pair, remove both; (c) a produced fact\n   claimed by >1 such golds → that connected group is AMBIGUOUS, removed.\n3. Anything still multi-candidate at fixpoint → AMBIGUOUS (grader channel;\n   unresolved ties still block PASS).\n4. A committed pair consumes its produced fact GLOBALLY (one-to-one everywhere,\n   presence_disagreement included).\nTests: permutation-invariance PROPERTY (score identical under random shuffles of\ngold AND produced order — the reproduced defect becomes the RED regression) +\nthe forced-choice propagation case (2 pairs, 0 ambiguous, both orders) + the\n>1-claimants case → grader queue in both orders.",
 "> **v3 (superseded by the rev-4 Part D law)** — the old fixpoint algorithm, record only:\n> 1. Build the full bipartite candidate graph gold ↔ produced per event.\n> 2. Repeat until no change, each round computed SIMULTANEOUSLY from the current\n>    graph: (a) golds with exactly ONE live candidate; (b) a produced fact claimed\n>    by exactly ONE such gold → COMMIT the pair, remove both; (c) a produced fact\n>    claimed by >1 such golds → that connected group is AMBIGUOUS, removed.\n> 3. Anything still multi-candidate at fixpoint → AMBIGUOUS (grader channel).\n> 4. A committed pair consumes its produced fact GLOBALLY.\n> Its permutation-invariance and propagation regressions carry forward against\n> the Part-D matcher (order-free must remain provable), rebuilt at implementation."),
])
