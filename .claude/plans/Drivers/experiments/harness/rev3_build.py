import difflib, io
R = {
".claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md": [
("- The proven pure V2 resolver decides canonical unit and scale; the semantic extractor only copies signed unscaled source numbers + verbatim raw units.",
 "- The READER states the final canonical unit and, per numeric slot, the exact `{value, scale_multiplier, unit_scale_evidence}`; code validates structure and evidence membership and performs exact Decimal multiplication only — it never derives a unit or scale from a name, quote, label, or concept name."),
("- **Effective UNIT-04 (per-slot hints):** each numeric level or change slot carries its own required raw unit + a unit-kind hint (`money`|`ratio`|`count`|`multiplier`|`unknown`); money kind requires `money_mode` (`aggregate`|`price_like`|`unknown`), null otherwise. Resolve level and change separately.",
 "- **Effective UNIT-04 (per-slot statement):** each populated numeric slot carries its own `{value, scale_multiplier, unit_scale_evidence}`. TEXT-lane facts: the evidence span must appear INSIDE the fact's quote — the SMALLEST span supporting the multiplier (\"billion\" for 10^9; a unit marker like \"$\" suffices only at multiplier 1); the evidence may be null ONLY when the multiplier is 1 AND no unit or scale marker exists. XBRL-BACKED facts: verified structured metadata (`ix.scale` + `unit_ref` + `source_evidence.pieces`) replaces quote-local evidence entirely. Level and comparison share `level_unit`; `change_value` carries `change_unit`. Resolve level and change separately."),
("- Validate final enum AND scaled value: glued billions → `m_usd` ×1,000; cents-on-aggregate and pre-scaled mistakes hard-fail; non-USD gaps may stay `unknown` (monitored).",
 "- Validate the final enum AND the multiplied value: percent-family/`x` require `scale_multiplier` = 1; cents-on-aggregate hard-fails; non-USD money states `unknown` (monitored). No magnitude-based guessing exists on this path."),
("A stated per-X denominator lives in the NAME while the value uses the base unit; the per-X lint (money level + stated denominator + no `_per_` name) is a hard failure.",
 "A stated per-X denominator lives in the NAME while the value uses the base unit; the shared decomposer emits it once as the packet's `per_x` signal and the ADMISSION KERNEL validates name↔per_x↔evidence — a conflict PARKS (the numeric converter never receives names)."),
("OD-11 CONSUMES the upstream-resolved `period_scope` (the period resolver runs first) and never infers it.",
 "OD-11 is applied by the MODEL — the reader states the final growth-basis unit directly — and VALIDATED by code, which enforces only the mechanical validators: the annual pin (percent_sequential on an annual period is invalid) and the sentinel fail-close (a dateless horizon with a growth-basis unit parks); the resolved `period_scope` still arrives first."),
("caught by a report-only monitoring counter, never a human or a list.",
 "attacked by hidden-grading fixtures and watched by the report-only monitor, never a human or a list."),
],
".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md": [
("- transients (propose-then-discard): `level_unit_raw / change_unit_raw` · 4 per-slot hints (`level_unit_kind_hint / level_money_mode_hint / change_unit_kind_hint / change_money_mode_hint`) · `level_shape_hint / comparison_shape_hint` · `measurement_raw_spans`",
 "- transients (propose-then-discard): the per-slot `{value, scale_multiplier, unit_scale_evidence}` objects (the numeric slots themselves; converted then stored as canonical scalars) · `level_shape_hint / comparison_shape_hint` · `measurement_raw_spans` — adapter-derived unit-kind/money-mode hints are ADAPTER-INTERNAL, never rendered to the reader, never grading input; the raw `fmt`/`is_currency` facts remain packet evidence"),
("2. **Per-X peel** (NAME-13): a stated per-X denominator → `per_x` (goes IN the name; unit stays base). Not stated → none.",
 "2. **Per-X peel** (NAME-13): a stated per-X denominator → `per_x` (goes IN the name; unit stays base). Not stated → none. Applied exactly ONCE, before matching/writing and before `_guidance`/`_surprise` handling; a name↔per_x conflict PARKS — never a guess."),
("7. **Unit** (04 UNIT-01 · OD-10/OD-11 · unit_resolver): unit_raw + hints → 10-unit enum; code stamps `series_unit`.",
 "7. **Unit** (04 UNIT-01 · OD-10/OD-11): the reader STATES the 10-unit enum directly + the per-slot `{value, scale_multiplier, unit_scale_evidence}`; code multiplies exactly and stamps `series_unit`."),
("- **CODE (deterministic, never decides meaning):** format norm, measurement token normalization (OD-9), unit resolution, XBRL-member→slice-kind (frozen table), id/fact_scope build, ALL validators.",
 "- **CODE (deterministic, never decides meaning):** format norm, measurement token normalization (OD-9), exact Decimal unit multiplication (the reader states the unit and scale), XBRL-member→slice-kind (frozen table), id/fact_scope build, ALL validators."),
],
".claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md": [
("slices, measurement spans, per-X, quote) · Block 2 the proven fact (all source values/text/conditions/\n  attribution evidence, raw units + per-slot hints, shape hints, period inputs, slices; code builds identity) ·",
 "slices, measurement spans, per-X, quote) · Block 2 the proven fact (all source values/text/conditions/\n  attribution evidence, the per-slot {value, scale_multiplier, unit_scale_evidence} objects + stated final\n  units, the MODEL-owned shape hints (a NAME COLLISION with — not the same thing as — the RETIRED\n  adapter-derived O-f hint fields), period inputs, slices; code builds identity) ·"),
("Preserve signed unscaled source value + `fmt`; code scales without changing sign; boundary and sign guards on.",
 "Preserve signed unscaled source value + `fmt`; code multiplies the stated scale exactly without changing sign; sign guards on (no magnitude/boundary guessing on this path)."),
("3 unit relocation + per-slot hints + lint (keep the resolver\n  parity test in permanent CI — it calls private old-Guidance helpers)",
 "3 unit statement + per-slot objects + kernel-side per-X validation (the legacy\n  resolver-parity CI is retired for this path — it intentionally diverges from old-Guidance behavior)"),
("planted traps (point-as-low-only · missing hint · sign flip · consensus-on-metric · value_text-with-number · duration start==end · fabricated period · two-scenario same-event collision → both quote_hashed · per-X name/unit mismatch · unknown-axis hex round-trip)",
 "planted traps (point-as-low-only · missing/invalid scale_multiplier or unit_scale_evidence · sign flip · consensus-on-metric · value_text-with-number · duration start==end · fabricated period · two-scenario same-event collision → both quote_hashed · per-X name↔per_x mismatch (kernel-side) · unknown-axis hex round-trip)"),
("the unit resolver calls private old-Guidance helpers —\nparity test in permanent CI · raw `$/barrel` can resolve dangerously without hints — the per-X hard failure is\nload-bearing",
 "the retired hint-era resolver called private old-Guidance helpers —\nits parity CI retires with it · raw `$/barrel` resolves via the reader's stated unit + the `per_x` signal — the kernel-side name↔per_x park is\nload-bearing"),
("the INTERNAL WRITER CONTRACT v3.6 is OWNER-APPROVED and its INTERNAL portion CLOSED 2026-07-17\n   (PreparedFactV1 schema passed review — 39 fields, XBRL all-or-nothing, blanket blank rejection;",
 "the INTERNAL WRITER CONTRACT v4 [PENDING OWNER SIGN-OFF O-d; supersedes the owner-approved v3.6 of 2026-07-17]\n   (PreparedFact v2 schema — 34 total / 32 model-owned fields, XBRL all-or-nothing, blanket blank rejection;"),
("input = `PreparedFactV1` dataclass pinned to the frozen packet (sha `aa7239ed…`) Block 2 + `source_id` +",
 "input = the PreparedFact v2 dataclass pinned to the RE-FROZEN packet (v2.0 sha assigned at the O-a re-freeze) Block 2 + `source_id` +"),
],
".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md": [
("Candidate criterion unchanged (quote ≥20-char overlap OR canonical value\nequality). Resolution is a fixpoint, order-free by construction:",
 "Candidate criterion RETIRED (rev-4 Part D law): auto-link ONLY an exact\ncomplete canonical record + exact locator, unique both ways; duplicate golds\ndetected FIRST; ALL remaining facts go to build-time grading — no filters, no\nquote-only fallback. The fixpoint below is HISTORICAL:"),
("`PreparedFactV1.from_dict` and calls run_event dry-run; the produced-fact",
 "the PreparedFact v2 `from_dict` and calls run_event dry-run; the produced-fact"),
("  low-rate wrong-hint dilute (the round-17/18 dilution class). A fix — recompute\n  `value_shape_acc` as the MIN over the value/shape/unit-hint field group so a",
 "  low-rate wrong-unit dilute (the round-17/18 dilution class). A fix — recompute\n  `value_shape_acc` as the MIN over the value/shape/final-unit field group so a"),
("The exam measures the TEXT decomposer: the model owns `fact_type` + the 37\ntext-lane fields.",
 "The exam measures the TEXT decomposer: the model owns `fact_type` + `per_x` +\nthe evidence locator (`part_ref` + `occurrence_in_part`) + the 32 text-lane\nitem fields."),
],
".claude/plans/Drivers/experiments/keys/K-fields/protocol.md": [
(" \"gold_item\": { /* the FULL FACT-17b item, transients included — the 37\n                  model-owned fields (PreparedFact minus member_refs +\n                  xbrl_concept_raw); EVERY gold_item carries ALL 37 keys\n                  EXPLICITLY (null where genuinely absent) — never a subset */ },",
 " \"part_ref\": \"p01\", \"occurrence_in_part\": null, \"per_x\": null,\n \"item\": { /* the PreparedFact v2 item — the 32 model-owned fields (v2 minus\n                  member_refs + xbrl_concept_raw); EVERY item carries ALL 32\n                  keys EXPLICITLY (null where genuinely absent) — never a\n                  subset */ },"),
("UTF-8 AND a UNIQUE span (extend if the phrase repeats; else abstain — never\ndefault to first occurrence) · fact_type enum · gold_item keys == EXACTLY the 37\nmodel-owned fields (all 37 present on every record, null-filled; a missing OR",
 "UTF-8 with part_ref + occurrence_in_part locating every span (null when unique\nin that part; code-verified against the part text) · fact_type enum · item keys\n== EXACTLY the 32 model-owned fields (all 32 present, null-filled; a missing OR"),
],
".claude/plans/Drivers/experiments/OWNER_DECISION_value_text_numeric.md": [
('- **Currencies outside `$€£¥`** — "₹500 crore", "CHF 20", "R$ 30" pass.',
 '- **Currencies outside `$€£¥`** — CORRECTED 2026-07-26: "₹500 crore", "CHF 20", "R$ 30" are in fact FLAGGED by the bare-integer arm (verified live); the original passing claim was wrong.'),
('- **Continental decimals** — "1,5 %" is not `\\d+\\.\\d+`.',
 '- **Continental decimals** — CORRECTED 2026-07-26: "1,5 %" IS flagged (the `%` arm matches "5 %"); the original passing claim was wrong.'),
('  any bare integer, so "Q3", "top 5 markets", "our 3 segments", "Section 401(k)"\n  are flagged as numeric even though they carry no measured value.',
 '  any bare integer, so "top 5 markets", "our 3 segments", "Section 401(k)" are\n  flagged as numeric though they carry no measured value ("Q3" is NOT flagged —\n  no word boundary splits Q from 3; corrected 2026-07-26).'),
],
}
APPEND = {
".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md":
"\n> **v2.2-rev4 AMENDMENT BLOCK (drafted 2026-07-26 — PENDING owner sign-off; supersedes-on-approval, history above unedited):** PreparedFact v2 = 34 total / 32 model-owned item fields (the four unit hints, `sequential_evidence`, and the two raw-unit fields retired; each numeric slot becomes a `{value, scale_multiplier, unit_scale_evidence}` object; `level_unit`/`change_unit` stated by the reader from the 10-unit enum; conversion = exact Decimal multiplication only) · the §4/EXP-5 field lists and the producer-contract text around lines 634-646 are SUPERSEDED on approval — the evidence locator becomes `part_ref` + `occurrence_in_part` (per-part; null when unique; code-verified), NARROWLY replacing the global occurrence count for event facts and abstentions ONLY (chunk-era locator rules untouched — O-e) · matching per the rev-4 Part D law (exact-record + exact-locator bijection; duplicate golds first; ALL unmatched to build-time grading) · ONE prompt builder (gold drafting + EXP-5 arms + the future whole-event production reader) · ONE model-output envelope for both roles · `fact16_checks` retired at implementation · v2.1 and the v2.2 drafts superseded by the rev-4 package (`experiments/harness/exp5_rev4_package.md`).\n"
}
problems = []
hunks = []
for rel, edits in R.items():
    src = io.open(rel, encoding="utf-8").read(); mod = src
    for old, new in edits:
        n = mod.count(old)
        if n != 1: problems.append(f"{rel}: count={n}: {old[:70]!r}"); continue
        mod = mod.replace(old, new, 1)
    hunks.append((rel, src, mod))
for rel, extra in APPEND.items():
    src = io.open(rel, encoding="utf-8").read()
    hunks.append((rel, src, src + extra))
if problems:
    print("MISMATCHES:"); [print(" ", p) for p in problems]
else:
    out = []
    for rel, src, mod in hunks:
        out.append("".join(difflib.unified_diff(src.splitlines(keepends=True), mod.splitlines(keepends=True), fromfile="a/"+rel, tofile="b/"+rel)))
    patch = "".join(out)
    # a context line for a BLANK line is a bare newline, not one space:
    # `git diff --cached --check` flags the space, and git apply accepts
    # the empty form (strict apply + byte-identical output both verified)
    patch = "\n".join("" if ln == " " else ln for ln in patch.split("\n"))
    io.open(".claude/plans/Drivers/experiments/harness/exp5_rev3_docs.patch", "w", encoding="utf-8").write(patch)
    print(f"patch written: {len(hunks)} files, {len(patch)} bytes, 23 edits + 1 append")
