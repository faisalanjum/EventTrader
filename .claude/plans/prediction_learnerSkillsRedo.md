# Predictor Skill Redo — Issue Catalog & Restructure Plan

**Created**: 2026-05-03
**Status**: Issue catalog locked — ready to tackle one by one
**Scope**: `/home/faisal/EventMarketDB/.claude/skills/earnings-prediction/SKILL.md`
**Related**: `.claude/plans/predictor-revamp.md` (architecture + design decisions, still authoritative)

---

## 0. What this plan is

The current SKILL.md works (the validator passes, predictions land), but it has accumulated layered compliance rules — T1 lesson labels, U67 source_id catalog grounding, section audit — and the reasoning instructions got squeezed in the process. The skill now teaches the LLM that bookkeeping is primary and prediction is secondary. Plus there are real validator contradictions in the current text.

This document is the issue catalog + the restructure target. We'll tackle items one by one. Stable IDs (C1, H1, etc.) so we can cross-reference.

---

## 1. Diagnosis

**Priority inversion.** Of ~200 lines in SKILL.md:
- ~80 lines on Phase 0 (lesson labeling) and Phase 0.5 (section audit) — pre-reasoning bookkeeping
- ~10 lines on Phases 1-4 — the actual analyst reasoning the predictor exists to do
- The rest is field definitions and frontmatter

Both the user's read and ChatGPT's read converge: the analyst task feels second-class. The skill currently looks like *compliance rails with an analyst hiding underneath*. Target: *analyst process with compliance rails*.

**Compounding effect on validator integrity.** Because the compliance machinery is over-specified in prose and under-specified mechanically, two contradictions slipped in:
- The skill tells the predictor to write `source: "learner_file:<path>"` while the validator only checks `source_id`.
- Sidecar paths are not minted in the bundle's `evidence_source_catalog`, so even if the field name were right, U67 would reject them.

These are real bugs that will fire whenever the predictor uses the optional sidecar reads exactly as instructed.

---

## 2. Open decisions (need user sign-off before final rewrite)

These shape the rewrite — flag them up front.

### D1. Live mode strategy — one skill or two?

| Option | Pros | Cons |
|---|---|---|
| **One skill, mode contract in body** ("historical: bundle-only; live: bundle + MCP within budget") | Single source of truth; smaller surface | Doubles cognitive load (LLM must mentally branch each rule); MCP isn't actually granted unless allowed-tools changes per invocation, so prose says one thing and tools enforce another |
| **Two skills, body identical, allow-list differs** (`earnings-prediction` vs `earnings-prediction-live`) | Each skill is purpose-built and short; orchestrator picks one based on `pit_mode`; reliable under existing infra | Two SKILL.md files to keep in sync (mitigated by a small sync script) |

**ChatGPT's recommendation**: don't split yet — start with a single mode-contract skill.
**Claude's recommendation**: split, because the skill body is identical except for the input surface, and the LLM clarity gain outweighs the file duplication.
**Status**: TBD — user to decide. Default for this redo: **write the historical SKILL.md first, defer the live split until the historical body is solid.** The live skill will be a thin wrapper at that point.

### D2. Section audit strictness

| Option | Pros | Cons |
|---|---|---|
| **Loose (scratchpad discipline)** — orchestrator only checks the file exists | Lets the LLM use the audit as it actually helps — fact inventory before reasoning, not a contract | Easy to satisfy mechanically; no quality floor |
| **Strict (shape validator)** — add a JSON schema check | Quality floor; rejects degenerate audits | False precision on internal scratchpad work; adds maintenance |

**Default**: keep loose, document the looseness in the skill ("the audit is a discipline scaffold, not a contract — keep it minimal but real"). Don't add a validator. If we see the LLM gaming it, revisit.

### D3. Sidecar citation policy

The current contradiction (C1, C2 below) needs a policy decision:

| Option | Approach |
|---|---|
| **A. Catalog anchor only** | Sidecars are context-only deep reads; citations always go to the catalog anchor (e.g., `S10.lesson.L3` or `S6.filing.F2`) that brought the sidecar into scope. Sidecar bodies inform reasoning; their paths never appear in `source_id`. |
| **B. Extend catalog with synthetic IDs** | Bundle's `evidence_source_catalog` mints `learner_file:<path>` and `related_filing_file:<path>` IDs at build time so direct citation works. Touches `build_evidence_source_catalog` in orchestrator. |

**Default**: **A**. Smaller surgery, keeps catalog as exact bundle index, validator unchanged. SKILL.md needs to reflect this clearly.

### D4. Whether to keep the "ultrathink" trigger word in the skill body

Currently `ALWAYS use ultrathink for maximum reasoning depth.` is line 1 of the body. Combined with `effort: max` in frontmatter, this is belt-and-suspenders. Decision: keep one, drop the other. Default: **keep the keyword in the body** (orchestrator-version-resilient), drop `effort: max` if it ever conflicts with SDK options.

---

## 3. Issue catalog

### Severity legend
- **C** = Critical (validator-breaking or contract-breaking — fix without restructure)
- **H** = High (substantive reasoning gaps — drives the redesign)
- **M** = Medium (silent drift / clarity)
- **L** = Low (polish — apply during full rewrite)

---

### Critical — validator/contract bugs

#### C1. Field name mismatch: `source` vs `source_id`

**Where**: SKILL.md Input section, learner_result and related_filing_file paragraphs.

**The bug**: skill tells predictor to "set the `source` field in your `evidence_ledger` to `"learner_file:<path>"`" (and same for `related_filing_file:`). But `validate_prediction_result()` reads `source_id`, not `source`. A predictor following the SKILL.md literally writes the wrong key, which either fails the U67 source_id check or the required-field check.

**Fix**: rename to `source_id` and pair with C2's policy.

---

#### C2. Sidecar IDs not in `evidence_source_catalog`

**Where**: same lines as C1.

**The bug**: even with the field name fixed, `learner_file:<path>` and `related_filing_file:<path>` are not minted in `bundle.evidence_source_catalog`. The U67 set-membership check rejects them.

**Fix**: per **D3 option A**: drop the synthetic prefixes entirely. Tell the predictor:

> When sidecar context informs a claim, cite the catalog anchor that brought the sidecar into scope (the lesson's `S10.lesson.L#` or the filing's `S6.filing.F#`). Sidecar bodies inform your reasoning; their paths do not appear in `source_id`.

---

#### C3. Lesson_text positional equality fragility

**Where**: Phase 0 — lesson labeling rules.

**The bug**: validator does normalized-string equality between `lesson_labels[i].lesson_text` and the renderer-emitted expected list. The skill says "verbatim copy of the body — no L# prefix, no scope tag, no leading/trailing whitespace." Scope tags like `[sector: Technology]` / `[macro]` / `[cross: AVGO,QCOM,AMD,TXN]` are mentioned but never shown. Predictor is one whitespace error away from a positional mismatch.

**Fix**: include a before/after example showing one tagged marker and the exact `lesson_text` it should produce. Keep the rule wording minimal; let the example carry the load.

---

### High — substantive reasoning gaps (drives the redesign)

#### H1. Phase 0 forces labeling "before any reasoning" — framing bug

**Where**: Phase 0 opening sentence.

**Issue (ChatGPT and Claude both flag)**: "label before any reasoning" conflicts with "label based on whether the current bundle independently supports the mechanism" — you cannot honestly do the latter without inspecting the bundle.

**Fix (reframe, not reorder)**: Phase 0 becomes "after one orientation read of the bundle, label each lesson against what you've actually seen. Labeling is a lookup task — does the bundle independently show the lesson's mechanism? Do not form a directional view yet."

---

#### H2. Reasoning section under-specified vs plan §5

**Where**: SKILL.md Phases 1-4 vs `predictor-revamp.md` §5.

**Issue**: plan §5 specifies the 5-question cross-reference scaffold (dominant narrative; competing narratives; what THIS company's market cares about; what's the bar; ranked drivers) as Phase 2's anti-anchoring engine. SKILL.md collapses Phase 2 to one sentence.

**Fix**: lift the 5 questions into the reasoning body with an explicit anti-anchoring rule: *do not commit to a direction until all 5 are answered with bundle evidence.*

---

#### H3. Surprise formula not stated

**Where**: missing from SKILL.md entirely.

**Issue**: plan §5 specifies `((actual - expected) / |expected|) * 100`. Without it, predictor will compute differently around negative or near-zero expected values, undermining ledger reliability.

**Fix**: one line in Phase 1 or in a "Definitions" sub-block.

---

#### H4. Quality-check guidance lossy vs plan

**Where**: Phase 1 sentence "Flag any results driven by one-time items rather than durable operating performance."

**Issue**: plan §5 enumerates a richer quality check — organic vs acquisition-driven revenue; EPS beat from operations vs tax/restructuring/one-times; margin trajectory (mix vs pricing vs cost cuts). The compressed sentence loses the analytical bite.

**Fix**: restore the 3-4 quality dimensions explicitly.

---

#### H5. Confidence rubric softer than plan

**Where**: Field definition for `confidence_score`.

**Issue**: plan §5 rubric is sharper:
- high (70-100): 3+ converging signals, dominant narrative clear, no strong counter
- moderate (40-69): 1-2 clear signals with ambiguity, or strong signal + notable counter
- low (1-39): weak signals, significant missing data, or balanced conflicting evidence

Current SKILL.md uses generic "clear / mixed / weak" language. Predictor and learner can't calibrate against fuzzy buckets.

**Fix**: use the plan's exact rubric verbatim.

---

#### H6. `no_call` semantics for confidence/magnitude is ambiguous

**Where**: field definitions; rules.

**Issue**: plan §5 says "When direction = no_call: signal = hold, confidence/magnitude still recorded." But the SKILL.md doesn't say what those numbers MEAN for a no_call. Is `confidence_score` "how unsure I am of any direction"? Is `expected_move_range_pct` an implied volatility band, or `[0, 0]`?

**Fix**: a 2-3 line definition. Suggested: "On `no_call`, `confidence_score` reflects how strongly the bundle supports the no-call posture (e.g., genuinely balanced evidence at 60+; degraded-bundle no_call at 30 or below). `expected_move_range_pct` reports the band you'd expect the stock to trade in either direction."

---

#### H7. Evidence ledger doesn't cover qualitative claims

**Where**: field definition for `evidence_ledger`.

**Issue (ChatGPT's strongest point)**: ledger today is "every key NUMBER." But "management tone deteriorated", "guidance was conservative", "peer read-through was negative" are load-bearing claims with no ledger entry, and the analysis can smuggle them in unsourced.

**Fix**: extend ledger semantics — every load-bearing claim used in analysis, quantitative *or* qualitative, gets a ledger entry. Quantitative: number + source_id. Qualitative: short verbatim quote or specific bundle pointer + source_id.

---

#### H8. No explicit rule against using bundle's market-reaction data as proof

**Where**: missing entirely.

**Issue**: builders try to enforce PIT (no daily/hourly_stock for the target event), but inter-quarter price moves DO appear in §6 ("stock fell 8% on 2023-10-15 after analyst downgrade"), peer post-earnings reactions DO appear in §7, and macro returns DO appear in §8. These are all signal about *what's already priced in*, not about *what direction the print will go*.

**Fix**: explicit rule. "Pre-event price moves (§6 inter-quarter, §7 peer reactions, §8 macro) tell you what's already priced in and what the bar looks like. They are not proof of post-print direction. Do not use any post-cutoff data anywhere."

---

#### H9. Lessons risk becoming primary evidence

**Where**: lesson labeling and `cites_lesson_indices` instructions.

**Issue**: a confirmed lesson is a heuristic from prior events, not current-bundle evidence. The output shape `{driver, evidence, cites_lesson_indices}` can make a lesson feel like the driver's grounding when it isn't.

**Fix**: tighten wording — "`cites_lesson_indices` points to a prior heuristic that *supports your interpretation* of current-bundle facts. The driver's `evidence` field must always be grounded in current-bundle facts. A driver whose evidence is only the lesson is not a valid driver."

---

#### H10. `expected_move_range_pct` anchoring missing

**Where**: field definition.

**Issue**: predictor is told to provide `[low, high]` % but not where to anchor the magnitude. Risk: numbers pulled from thin air.

**Fix**: short anchoring guidance — "Anchor in (a) typical post-earnings move from prior-quarter lessons if shown, (b) peer reactions to similar surprises in §7, (c) current vol regime in §8 (VIX, sector beta). Width should reflect your uncertainty about magnitude, not direction."

---

#### H11. Degraded-bundle decision protocol missing

**Where**: rules section has only the one cap (consensus + guidance both missing → confidence ≤ 30).

**Issue**: real degraded states include EX-99.1 missing, builder errors (e.g. `[Consensus unavailable…]`), no prior financials, peer snapshot empty, macro snapshot partial. Predictor gets no guidance on how to behave.

**Fix**: small "Degraded bundle" subsection. Mechanical triggers favoring `no_call`:
1. Both consensus AND guidance missing
2. EX-99.1 missing or builder-erred
3. ≥3 builders in error state
4. Stress-test produces genuinely balanced evidence after honest review

When any trigger fires, default to `no_call` unless remaining evidence is exceptionally strong. List failed builders in `data_gaps`.

---

### Medium — silent drift, ambiguity

#### M1. `model: opus` may conflict with SDK config

**Where**: frontmatter.

**Issue**: orchestrator passes a specific model id via `PREDICTOR.as_sdk_kwargs()`. Frontmatter `model: opus` is either redundant (SDK wins) or could overshadow it.

**Fix**: drop the field, OR pin to the same exact ID the orchestrator uses. Single source of truth.

---

#### M2. Phase 2 5-question scaffold

(Subsumed by H2 — same fix.)

---

#### M3. Stress-test "both sides survive" path unhandled

**Where**: Phase 3.

**Issue**: skill addresses the failure case ("if neither side survives, no_call") but not the common case where both pass. Predictor doesn't get a tiebreaker.

**Fix**: explicit rule — "If both sides survive, the prediction goes to whichever has materially more evidence weight. If they're roughly balanced after honest weighting, lean toward `no_call` or low-confidence."

---

#### M4. Write discipline not explicit

**Where**: missing.

**Issue**: skill grants `Write` tool but doesn't say "only to SECTION_AUDIT_PATH and RESULT_PATH."

**Fix**: one rule line.

---

#### M5. `not_material_reason` rule is conditional and easy to trip

**Where**: Phase 0.5.

**Issue**: required *only* when key_facts/bullish/bearish/missing_or_unclear are ALL empty. Subtle counting; predictor may get it wrong.

**Fix**: replace with two simple worked examples — one section with material content, one with no material content. Let the examples carry the rule.

---

#### M6. Section audit only existence-validated

**Where**: orchestrator + skill.

**Issue**: shape isn't checked. Could be game-able.

**Fix**: per **D2**, document the looseness explicitly in the skill so the predictor knows the audit's role is discipline, not compliance.

---

#### M7. Final analysis can ignore audit findings

**Where**: missing rule.

**Issue**: predictor can technically audit all sections then make the call from §2 alone.

**Fix**: one sentence in Phase 4 — "your analysis must explicitly weigh evidence from the load-bearing sections (Results & Expectations, Forward Guidance, Consensus, Inter-Quarter Context) and from any other section that materially supports or contradicts your call. If a section's audit shows material signals you didn't weigh, explain why."

---

#### M8. `data_gaps` shape drift from plan

**Where**: field definition.

**Issue**: plan §4b: `[{"item": "consensus", "gap": "..."}]`. SKILL.md: `[{"gap": "..."}]`. Validator only checks list-of-anything. Loss of structured "what builder is missing" hurts learner attribution.

**Fix**: add `item` field to schema (required when known; optional when not) + an entry per failed builder.

---

#### M9. `key_drivers[i].direction` enum unenforced

**Where**: schema.

**Issue**: should be `long` or `short` only. Validator doesn't check.

**Fix**: state it explicitly. Optional: small validator bump (one line) to enforce.

---

#### M10. Bundle's PIT/Mode signal not surfaced to predictor

**Where**: missing reference in skill.

**Issue**: §1.0 Mode line (`live` / `historical`) and `pit_cutoff` exist in bundle, but the skill never tells the predictor to consult them. Becomes load-bearing for any future mode-conditional behavior.

**Fix**: brief note in Inputs — "the bundle's §1.0 header carries Mode (`live` / `historical`) and PIT cutoff; treat all bundle data as ≤ this cutoff (orchestrator's job; don't second-guess) and never use any post-cutoff signal."

---

#### M11. Builder errors not addressed

**Where**: missing.

**Issue**: when a builder fails, renderer emits `[Consensus unavailable — AV upstream failed: ...]` (saw it on NFLX live test). Skill says nothing about how to handle these markers.

**Fix**: rule — "if a section shows a `[... unavailable ...]` or `[BUILDER ERROR: ...]` marker, treat it as a data gap; list it in `data_gaps` with the named builder; apply degraded-bundle protocol (H11) if multiple sections are degraded."

---

#### M12. Phase 0 cognitive load is heavy

**Where**: Phase 0.

**Issue**: marker parsing rules + label enum + sentinel discipline + citation rules + analysis substring constraint + scope tag handling. All necessary, but front-loaded as a wall of text before any reasoning.

**Fix**: split into 3 small steps with one example per step. Move analysis-substring constraint to the Compliance appendix.

---

### Low — polish (apply during rewrite)

#### L1. Description doesn't note "called by orchestrator"

Description: "Predict stock direction after an 8-K earnings release from a prebuilt earnings context bundle." Could be slightly more diagnostic for future readers.

#### L2. ALWAYS / MUSTs heavy

Skill writing guide says these are yellow flags — better to explain *why* a rule exists. Most current rules have good reasons (validator, audit trail, anti-anchoring); surface those reasons.

#### L3. No example of scope-tagged lesson markers

(Same fix as C3 — show one example.)

#### L4. Audit example shows only 2 of 8 sections

Combined with the "silent omission not allowed" rule, the example understates the volume the predictor must produce.

#### L5. Order of compliance machinery vs reasoning

Both reviews flag this as core to clarity. The restructure (§4 below) is the fix.

---

## 4. Restructure target — proposed SKILL.md outline

Adopting ChatGPT's 7-section structure with one tweak (interleave compliance within reasoning rather than dumping it all at the end):

```
1. Mission and mode contract
   - One paragraph: senior earnings analyst making one directional call from bundle.
   - Mode contract (current scope = historical, bundle-only). Orchestrator owns PIT.

2. Inputs and allowed writes
   - Paths: BUNDLE_PATH, RENDERED_BUNDLE_PATH, SECTION_AUDIT_PATH, RESULT_PATH.
   - Allowlists: learner reports + related filings (D3-aligned).
   - Write discipline: ONLY to SECTION_AUDIT_PATH and RESULT_PATH.

3. Evidence review workflow (the work)
   - Read the rendered bundle once.
   - Compact section audit (~15 lines, two examples — material + not-material).
   - Lesson labeling (~15 lines): rules + one fully worked tagged-marker example.

4. Decision framework (the heart — largest section)
   - Phase 1 (Inventory):
     • Surprise formula (H3)
     • Quality check dimensions (H4)
   - Phase 2 (Cross-reference):
     • The 5 questions (H2 / plan §5)
     • Anti-anchoring rule
   - Phase 3 (Stress-test):
     • Long case + short case
     • Both-survive tiebreaker (M3)
   - Phase 4 (Decide):
     • Confidence rubric (H5 verbatim from plan)
     • Magnitude anchoring (H10)
     • no_call semantics (H6)
     • Mandatory cross-section weighing (M7)
     • Degraded bundle protocol (H11 / M11)

5. Output schema (concrete JSON example)
   - Field definitions, validator-aware
   - Evidence ledger discipline (H7 — qualitative + quantitative)
   - data_gaps shape (M8)
   - key_drivers direction enum (M9)
   - Citation rules (C1 / C2 / D3 fix)
   - Lesson-citation guardrail (H9)

6. Compliance appendix (the validator's traps)
   - U67 source_id catalog membership
   - T1 lesson_labels positional equality
   - Substring floor on analysis (lifted from current Phase 0)
   - Why each rule exists (so the predictor obeys for the right reason)

7. Hard rules block (5-7 short lines)
   - Bundle/allowlist only — no other reads
   - No post-cutoff signal anywhere (H8)
   - Lessons inform interpretation, never replace current-bundle evidence (H9)
   - Both consensus AND guidance missing → confidence ≤ 30 (existing)
   - Write only to the two output paths (M4)
```

Target length: ≤ 200 lines, with reasoning ≥ 50 lines, lessons ≤ 20 lines, audit ≤ 20 lines, compliance ≤ 30 lines.

---

## 5. Implementation order

Tackle in this sequence — each step independently shippable.

1. **Critical fixes (C1, C2, C3)** — surgical. No structural change. Fixes the validator-breaking bugs immediately. ~10 line edits.
2. **Restructure shell** — apply the 7-section outline; move existing content into the right place without rewriting it. Establishes the priority hierarchy.
3. **Reasoning rewrite (H2-H7, H10, M3)** — write the Decision Framework section against plan §5. This is where the real value lands.
4. **Discipline rules (H8, H9, H11, M7, M11)** — fold into Hard Rules + Phase 4.
5. **Audit + lessons trim (M5, M12, L3, L4)** — compact each to ≤ 20 lines with one good example.
6. **Validator-trap appendix** — pull the substring floor and citation rules into a single block; explain the *why* of each.
7. **Polish (M1, M4, M8, M9, L1, L2)** — small targeted edits.
8. **Verification — three sub-steps in order** (cheap → expensive):
   - **8a. Focused validator + renderer unit tests** — run `pytest scripts/earnings/test_validate_prediction_result.py scripts/earnings/test_validate_prediction_u67.py scripts/earnings/test_renderer_golden_full.py scripts/earnings/test_renderer_golden_sections.py scripts/earnings/test_section_audit_feature.py -v`. Catches any accidental Python regression. If we touched the validator for M9/M8, the new tests for those land here and gate the change.
   - **8b. Golden bundle smoke (no SDK)** — eyeball the four rendered goldens (`AVGO_Q3_FY2023`, `AVGO_Q4_FY2023`, `CHRW_Q4_FY2025`, `CXM_Q4_FY2026`) for unintended renderer drift.
   - **8c. End-to-end SDK smoke** — run predictor on AVGO Q4_FY2023 (the tickiest case: 6 L# markers including `[sector:]` + `[cross:]`). Verify result.json shape, validator passes, reasoning quality is preserved or improved.
9. **Live mode decision (D1)** — once historical SKILL.md is solid (i.e., 8a + 8b + 8c all green and reasoning quality confirmed), decide whether to fork into `earnings-prediction-live` and grant MCP. Separate task; not in this redo. The live skill becomes a thin wrapper around the canonical historical body; the cleaner the body, the smaller the wrapper.

---

## 6. Out of scope (deferred)

- **Turn-2 question loop** (predictor-revamp §6 / §10's "NOT BUILT") — separate decision; user has already noted it's likely overkill until learner data shows it's needed.
- **Live-mode MCP grant** — gated on D1.
- **U67 catalog extension to mint sidecar IDs** (D3 option B) — only if D3-A proves insufficient.
- **Audit-shape validator** (D2 strict) — only if loose audit proves game-able in production.
- **Section §15 (bundle rendering deep analysis)** — already implemented in `renderer/bundle.py`, not part of this skill redo.

---

## 7. Verification checklist (run after redo lands)

- [ ] Validator-breaking bugs gone: predictor writes `source_id`, never `learner_file:` or `related_filing_file:` strings.
- [ ] Reasoning section is the largest section by line count.
- [ ] Lesson labeling and section audit each ≤ 20 lines, each with one full example.
- [ ] Hard Rules block exists, ≤ 7 lines.
- [ ] Compliance appendix exists, explains the *why* of each rule.
- [ ] All four golden-render bundles smoke through the new SKILL.md without validator errors.
- [ ] Result.md sidecar still renders; thinking harvest still works.
- [ ] No new orchestrator changes required.

---

## 8. Notes from the two parallel reviews

Both reviews (Claude + ChatGPT) converged on:
- Priority inversion is the root issue.
- Phase 0 framing bug ("label before reasoning" vs "label based on bundle").
- Sidecar citation contradiction.
- Reasoning section is too thin.
- Degraded-bundle protocol missing.
- Evidence ledger should cover qualitative claims.
- Anti-anchoring scaffold (5 questions) is needed.

Claude additionally caught:
- The literal `source` vs `source_id` field-name bug (the most critical individual item).
- `learner_file:` strings not being in the catalog (the second most critical).
- `model: opus` frontmatter potentially conflicting with SDK config.
- Bundle Mode/PIT signal not surfaced to predictor.
- Builder error markers not addressed.

ChatGPT additionally emphasized:
- Mode contract should be explicit (live vs historical) — but the current skill's allowed-tools don't actually enable "live can read everything," so that needs to be a coordinated change.
- Output semantics tightening (no_call confidence, expected move discipline, driver direction enum) is where bad outputs can pass validator silently.

User additionally raised:
- Clarity is missing overall — the dominant concern.
- Reasoning + actual task feel like second-class citizens.
- Lessons rules and audit rules should be rethought line by line.
- PIT shouldn't dominate the skill (orchestrator's job).
- Considering parallel live skill that can read more freely within a turn budget.

All of these are captured in the issue list above.

---

## 9. Refinements after re-read (small but worth pinning down)

These are clarifications I'd add before we start tackling items — they answer questions that would otherwise come up the moment we touch the SKILL.md.

### R1. Workflow order in §3 of the restructure: audit BEFORE lessons

The current §4 outline lists audit and lessons as siblings under "Evidence review workflow" without a sequence. The natural sequence is:

1. Read the rendered bundle once (orientation).
2. Write `SECTION_AUDIT_PATH` (the audit IS the orientation read — facts inventory).
3. Label prior lessons against what the audit surfaced (lookup task, not synthesis).
4. Phases 1-4 (reasoning + decide).
5. Write `RESULT_PATH`.

Reframing audit as the orientation read, with lessons as a downstream lookup against the audit, resolves H1's framing tension cleanly: by the time you label, you've already seen the bundle through the audit's lens, so labels are honest.

### R2. D4 final answer: keep `ultrathink` keyword in body, drop `effort: max` from frontmatter

`effort: max` works (MEMORY confirms v2.1.80) but is belt-and-suspenders with the in-body `ultrathink` directive. Single signal is cleaner. Source-of-truth precedence: in-body keyword wins because it's visible in the prompt the model actually reads, whereas the effort frontmatter is interpretation-time only. **Decision: drop `effort: max` from frontmatter; keep `ALWAYS use ultrathink for maximum reasoning depth.` as the first line of the body, but with a brief *why* sentence appended (per L2).**

### R3. H7 evidence_ledger size discipline

"Every load-bearing claim" could explode the ledger to 50+ entries. **Add a soft rule: aim for 10-20 entries; aggregate near-duplicates (e.g., one entry per metric per period); drop genuinely minor claims that don't drive the call.** The ledger is for traceability of the *decision-relevant* facts, not an exhaustive transcript.

### R4. H6 no_call confidence — high vs low semantics

The fix wording was ambiguous. **Tighten to**:
> On `no_call`, `confidence_score` reflects how strongly the bundle supports the *no-call posture itself*:
> - **High no_call (60-100)**: bundle is rich and you're confident the right action is to NOT trade — evidence is genuinely balanced after stress-test, or volatility regime makes any directional bet poor risk/reward.
> - **Low no_call (≤30)**: bundle is degraded or you don't have enough information to even decide whether no_call is the right posture. Apply the H11 hard cap.
>
> `expected_move_range_pct` on no_call reports the magnitude band you'd expect the stock to trade in either direction, not [0, 0].

### R5. M9 driver direction enum — confirm long/short only

`key_drivers[i].direction` should be `long` or `short` only. **Rule out `no_call` at the driver level**: a driver represents a directional force; a "no_call" driver is meaningless. If a section is genuinely neutral, omit it from key_drivers and note it in `data_gaps`.

### R6. Renderer scope-tag format must be verified before writing the C3/L3 example

Before committing the worked example for tagged-marker stripping, confirm the renderer's actual emitted format across all four golden bundles (`AVGO_Q3_FY2023`, `AVGO_Q4_FY2023`, `CHRW_Q4_FY2025`, `CXM_Q4_FY2026`) plus the fresh `NFLX_Q3_FY2025`. If the format isn't 100% stable (e.g., space variants, bracket variants, missing colons), fix the renderer first or write a defensive normalization rule. **Check command**:
```bash
grep -E "^L[0-9]+\." scripts/earnings/tests/fixtures/golden_renders/full/*.txt | head -30
```

### R7. Frontmatter `Glob` tool — keep or drop?

Current frontmatter grants `Read`, `Write`, `Glob`. **Audit usage**: does the predictor ever need `Glob`? It would be needed to enumerate sidecar files, but the allowlists in the bundle name them explicitly, so `Glob` is unused in current operation. **Decision: drop `Glob`** unless we plan to relax the allowlist into pattern-based discovery (we don't). Smaller surface = easier reasoning about what the predictor can do.

### R8. §7 verification — explicit smoke-test command + golden coverage

The verification checklist says "smoke through the new SKILL.md." Be concrete:

```bash
# Re-render bundles under the new SKILL.md (no SDK call)
cd /home/faisal/EventMarketDB
for fixture in AVGO_Q3_FY2023 AVGO_Q4_FY2023 CHRW_Q4_FY2025 CXM_Q4_FY2026; do
    pytest scripts/earnings/test_renderer_golden_full.py::test_full_bundle_byte_equality \
        -k "${fixture}" -v
done
# End-to-end with the SDK on one ticker that has full learning_context (lesson labels exercise)
python scripts/earnings/earnings_orchestrator.py AVGO 0001730168-23-000093 \
    --predict --pit 2023-12-07T16:30:00-05:00
```

The AVGO Q4_FY2023 case exercises the full Phase 0 lesson-labeling path (it has 6 L# markers including a `[sector:]` and a `[cross:]` tag — the trickiest case). NFLX won't exercise lesson labeling because there's no learning_context for it yet (no prior predictions). CHRW/CXM are partial.

---

## 10. Status snapshot — agreement matrix

| Item | Claude agrees | ChatGPT agrees | User concern addressed |
|---|---|---|---|
| Priority inversion is the root issue | ✅ | ✅ | ✅ |
| C1 (`source` vs `source_id`) | ✅ | ✅ | (validator-strictness item) |
| C2 (sidecar IDs not in catalog) | ✅ | ✅ | (validator-strictness item) |
| C3 (lesson_text fragility) | ✅ | partial | (clarity item) |
| H1 (Phase 0 framing bug) | ✅ | ✅ | (lessons-rules-line-by-line item) |
| H2 (5-question scaffold) | ✅ | ✅ | (reasoning-second-class item) |
| H3-H5 (formula, quality, rubric from plan §5) | ✅ | partial | (reasoning-second-class item) |
| H6 (no_call semantics) | ✅ | ✅ | (clarity item) |
| H7 (qualitative ledger) | ✅ | ✅ (their strongest point) | (clarity item) |
| H8 (no market-reaction proof) | ✅ | ✅ | (PIT/clarity item) |
| H9 (lessons ≠ primary evidence) | ✅ | ✅ | (lessons-rules-line-by-line item) |
| H10 (magnitude anchoring) | ✅ | ✅ | (clarity item) |
| H11 (degraded bundle protocol) | ✅ | ✅ | (clarity item) |
| M10 (PIT/Mode signal) | ✅ | partial | (PIT-shouldn't-dominate item) |
| 7-section restructure | ✅ | ✅ | (reasoning-second-class item, clarity item) |
| Live skill split (D1) | recommends split | recommends one-skill-mode-contract first | (parallel-skill item) |
| Audit strictness (D2) | loose | loose | (audit-rules-line-by-line item) |
| Sidecar policy (D3) | option A | option A | n/a |
| Turn-2 question loop | out of scope | out of scope | (user noted: overkill) |

The only meaningful disagreement between Claude and ChatGPT is **D1** (split now vs defer). The plan defers — write historical first, decide after seeing how clean the body gets. That's the right call.
