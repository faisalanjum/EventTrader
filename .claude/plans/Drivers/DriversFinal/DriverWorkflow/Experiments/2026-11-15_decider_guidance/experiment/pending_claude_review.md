# Pending review — 2026-11-15, America/Toronto (EST)

These are preliminary suggestions supplied by the owner for independent verification. They are NOT approved graph rules or proven extraction steps. The current rulebook still governs. Preserve this distinction in any strategy update.

## Earlier emerging themes

- Put definitions in shared state once and keep questions short; claimed roughly half the cost.
- Code fixes text boundaries; Decider judges meaning.
- One role choice per printed number, not Locate for number discovery.
- Rank fixes by frequency of complete-fact failures, not memorable difficult examples.

## Later seven suggestions, not final

1. Group neighbouring printed numbers before fields. One relation choice per neighbouring pair: range endpoints / centre ± tolerance / earlier→newer / same amount restated / separate / unclear. Ask fields once per group.
2. Hide speaker markers such as `Todd Schneider [78]:` using stored structure, not a word list. Claimed 363/1,050 numeric tokens are markers, including 19/120 B questions.
3. One sentence question covering all guidance, numeric or worded. A disagreement with a number's role must remain visible.
4. Identify sentences expressing assumptions/exclusions/dependencies or stated raise/lower/reaffirm movement. For each forecast group × relevant sentence, judge applicability with yes/no, distinguishing causes from assumptions. Copy matched sentences whole; add a quote-start pointer for lead-ins such as year and stated movement.
5. Select the sentence naming a candidate's measure, including a confirmed analyst question; run Locate only on that sentence plus the forecast sentence. Validate that the output is a measure. Empty → visible hold. Explicitly untested. Broad passage-level metric discovery had already failed.
6. Score each stage against a draft source-based key before the next stage, prioritizing silent misses. Claimed rough distribution: 69 core facts across six calls, 71% plain numbers, 12% worded, 14% range-relative, one sentence containing a worded list. Finish complete numeric records first. Proposed 30,720-token request ceiling to avoid native splitting.
7. Rule 3.33: growth without a source-stated comparison basis uses `unknown`, not a percentage level. The legacy `percent` values must not define the answer key.

## Owner's current leanings — explicitly NOT final

1. Far conditions: undecided.
2. Values relative to a range: store the printed range plus position wording (for example, “at the high end of the range”) when the call restates the numbers; otherwise store wording only. Never compute a point.
3. Centre ± tolerance: hold with a reason code and both printed numbers for now; a new field may be considered after review.
4. Blanket reaffirmations: no special treatment; hold and count them as “no named metric”, never silently drop. Treat blanket withdrawals the same way, flagged.

## Independent checks completed so far

- Shared definitions/short questions are supported for the checked numeric-bound task: 50 questions fell from 673.80s/57,046 tokens/two sequences to 255.82s/22,248 tokens/one sequence. Correct top-choice bound pairs rose 22/25→25/25. This is one-call component evidence, not whole-pipeline performance or universal accuracy.
- Marker counts independently recomputed: exactly 363/1,050 across six source snapshots, and 19/120 in B. `speaker_marker_audit.json` contains every source count and B ID. An existing boundary helper was found in `scripts/driver_seed/relocate_probe/phase2/m1_transcript_census.py` (`SPEAKER`, `spoken_text`); its census helper removes the whole speaker prefix, so it must not be reused as model input while losing attribution. Reuse only verified header boundaries to exclude numeric annotations from candidate questions, preserving speaker identity. Prepared remarks are stored as strings containing the header; they do not expose a separate timestamp in the sampled `pr.content`. Q&A entries have separate speaker/title fields but still embed the marker in text. Therefore “just use structure” requires checking the actual ingestion/rendering boundary. Preserve speaker identity and exact original evidence; do not strip arbitrary bracketed numbers.
- Whole-expression fields were tested using already model-selected bounds, not neighbouring-pair inference: 90→54 questions, 273.75s→231.02s; range-form confidence improved, but missing conditions and unsupported inferred growth basis remained. Grouping identical source-span questions is not merging final records.
- Neighbour-only grouping is untested. It can miss remote references and link across different measures or periods. Typed relation chains must not become unconditional connected-component record merging. Detecting centre/tolerance does not resolve its permitted stored representation.
- Rule 3.33 directly supports unknown growth basis when no applicable comparison evidence exists. The tested shared-definition field questions instead chose `percent_yoy` for the two current growth ranges; this remains an error/open validation issue, not a passed unit result.
- The draft inventory is now supplied at `/tmp/claude_decider_review_20261115/draft_inventory_69.json`. Arithmetic independently verifies 69 core + 6 borderline rows: 49 point/range (71.0%), 8 worded (11.6%), 10 relative (14.5%), 2 reaffirmations (2.9%). This is not quote-level adjudication. Twelve core rows have far conditions; 25 near; eight have indirect measure wording; 29 have periods elsewhere. All rows reference the six known calls. No unique sentence IDs are supplied, so a count of distinct worded-list sentences requires source inspection. The old 54 rows are not a complete key. The proposed 30,720 limit is not a demonstrated runtime setting; actual token accounting and native packing must be checked, and fewer splits do not inherently prove lower total time.
- Sentence-wide conditions may preserve useful evidence, but a sentence can mix a forecast, assumptions, actual results and causes. Whole-sentence copying alone does not establish a clean conditions field. One quote-start pointer also does not establish that every later qualification was included.
- A sentence pointer plus local Locate is a plausible bounded experiment, not a verified fix. It needs none/elsewhere/several/unclear choices, complete context for reference resolution, exact mapping, and both measure type and correct association; “is a measure” alone cannot reject the wrong measure.

Do not promote any pending leaning or untested procedure based on this note. Reconcile the full review when supplied, using evidence and current owner decisions.

- The broader sentence question is being tested as a replacement, not an extra detector layer. A positive guidance sentence plus a negative number role is not necessarily a contradiction: the number may be its fiscal year, an actual comparison, or old guidance. One retained record also cannot establish completeness when the sentence contains several facts. Preserve source-to-candidate outcomes and check against the independent key.

## Storage implications to review before approving the leanings

- Range-relative wording: 4.7 forbids `value_text` alongside numeric values. Existing 3.24–3.26 can preserve source modifiers as measurement tags, but those tags participate in identity/series matching. A high-end-qualified range must not be read as an unqualified midpoint or assumed comparable to an untagged earlier range. This is a possible existing-field representation to review, not an approved encoding.
- Centre/tolerance: identifying the two numbers does not authorize calculating endpoints or adding a field. Preserve raw evidence/printed numbers in the experiment and keep the proposed hold policy pending.
- Blanket withdrawal: 4.18–4.21 currently allow propagation when prior scope is exact. A blanket “no named metric → always hold” policy is more restrictive and needs reconciliation if approved; the trial has not proved that history lookup. Blanket reaffirmations also depend on exact prior scope under 3.35.
- Far conditions: 1.24 requires one exact quote and does not explicitly say one speaker. A cross-block quote still needs proof under the existing source/evidence contract; this is not automatic approval of new quote machinery or a settled extraction policy.

## Additional growth-unit suggestion (pending)

Owner supplied Claude's proposal: ask whether the quote explicitly states the growth comparison basis; no → `unknown`; yes → code maps the stated basis to yearly/sequential, with annual sequential mapped to yearly under 3.33.

Independent issue: a boolean yes does not identify which basis, and code cannot recover arbitrary comparison wording without another source-grounded input. Literal keyword code would miss valid forms such as explicit fiscal-year comparisons, misapply nearby comparisons, and recreate a semantic parser. A minimal complete alternative is one evidence-based choice (same period a year earlier / immediately previous comparable period / both explicitly applicable / none / unclear) with the supporting source location, then deterministic rule mapping. This is a proposal to test, not a proven replacement; never infer a basis from the target period alone. The current one-batch unit test instead clarifies the existing rule and includes genuine positive controls.

- Inventory interpretation still needs review: the current CTAS call explicitly mentions an H2 average of 7.9 and repeats the transaction-cost estimate for Q4; the draft has a Q4-organic row and one transaction-cost row, but no quotations/value mappings to establish whether those additional period-specific claims were included. These are adjudication candidates, not an automatic corrected total. Its six calls cover only two companies, so proportions cannot establish prevalence across all transcripts.

### Growth-basis verification, 2026-11-15, 2:52 PM EST

- Rule 3.33 was reread directly. Its evidence requirement is already binding; no rulebook change is needed. A yes/no answer alone cannot identify the basis, so a keyword parser would add unsupported machinery.
- Evidence-presence yes/no: 4/4 correct on two unstated-basis Cintas forecasts and two explicit prior-year actual results, 183.00 seconds. Exact selected quotes plus the whole call were supplied. This first test alone did not establish forecast-positive behavior.
- One evidence-based choice on the same four quotes/full-call state: 4/4 correct, 192.58 seconds. Options: same period a year earlier / immediately previous comparable period / both explicitly stated / other stated comparison / not stated / unclear. It supplies evidence presence and basis identity together; there is no reason yet for a mandatory separate yes/no round.
- Broader short-quote check: 18/18 correct top choices in 46.52 seconds: eight real excerpts (including explicit forecast positives, sequential and two-basis wording) and ten controlled mutations (target-year-only, explicit annual comparisons, nearby unrelated comparisons, old forecast versus previous period, and wider quote framing). Four real excerpts overlap the earlier test; do not count these as 22 independent examples. Exact requests, independently written expected labels and probabilities: `main_path/unit_evidence_*`, `unit_basis_choice_*`, `unit_basis_boundary_*`.
- Recommendation for the next trial: ask which comparison the actual evidence establishes, then use deterministic 3.33 mapping. No evidence means `unknown` only when the source genuinely does not settle it. Missing applicable evidence is an extraction failure, not proof of absence. Preserve both stated bases; do not relabel another comparison as yearly/sequential. Points/basis-points precedence, vague horizons and percentage-on-percentage rules still apply. Verified annual sequential maps to yearly. This is a component result, not a complete-record or universal pass.
- The quote-selection prerequisite remains: a sentence-only quote can omit a valid framing statement elsewhere. Widen the evidence under 3.29 when applicable; this test does not prove automatic quote construction, field association or end-to-end extraction. Do not make a fixed one-sentence evidence policy.

**Simpler final component comparison:** the existing full unit-choice options, now explicitly grounded in each target's exact quote, passed **12/12** independent controls in **32.81 seconds / 2,867 input tokens**. The prior whole-call framing passed 11/12 in 196.47 seconds / 16,998 tokens. Controls include money/scale, percentage levels, explicit yearly growth, unstated growth basis, and basis points. This changed evidence framing and context; it is not an isolated model-speed comparison. The smallest next-trial choice is therefore **one quote-grounded unit question**, not an added yes/no or separate basis layer. This refines the recommendation above. Rule 3.33 still applies in code; automatic quote completeness and full-record integration remain unproved. Evidence: `main_path/unit_quote_request.json`, `unit_quote_scored.json`.

### Sentence pointer → short Locate: tested, still unresolved

- One full-call source-sentence choice was tested on the 14 numeric work targets remaining after six already established expression groups, plus the already-selected ERP qualifier. No metric-name catalogue entered the input. Eleven of 15 pointers found independently identified naming sentences in 220.20 seconds. The four indirect cases instead pointed to the value or an intervening reference, not the antecedent naming the measure.
- One unchanged Locate label then read only the selected sentence and target sentence, with exact occurrence tags and source maps: 15 calls took 34.51 seconds. Twelve returned spans. Two spans above 0.99 (“Q4 implied”, “average”) were not measure names; others omitted required measure context or included a fiscal period. All returned mapped text was exact, which does not prove its meaning is correct.
- This supports fast short-text copying where the relevant wording is already selected. It does not resolve source-only measure identity or indirect references, and it produced no complete-record pass. Do not promote the proposed two-step procedure or stack another repair layer. Evidence: `main_path/measure_pointer_*`, `measure_local_*`, especially `measure_local_reviewed.json`.

### Later evidence-selection checks

- Four annual forecast expressions × all 27 sentences retained by the frozen guidance screen: 108 support questions in 214.53 seconds / 18,066 tokens. On the partial independent key, 86/88 relations matched, including all 12 known positive assumptions/exclusions; two different cost-forecast statements were additionally selected. Twenty relationships remain unadjudicated. Selecting evidence is not final assignment to `conditions`; measurement exclusions and causes require their proper treatment. No complete-record pass.
- Unit choices on actual continuous quotes built from these selections: 3/4 correct in 74.56 seconds / 7,083 tokens. Revenue incorrectly received `usd` instead of the evidenced billion-to-million total unit/scale. Its winning probability was 0.528. Do not claim that another particular forecast caused this internal model error; that is a hypothesis, not established causation.
- Reusing exactly the selected sentences as field input, while preserving the same continuous original quote separately, passed 4/4 in 19.48 seconds / 1,762 tokens. Source slices and unchanged original quotes were verified. No new question type, semantic selection or fallback was added. This supports the smaller evidence input for the tested unit task; all-field performance and evidence completeness are still unproved.
- The original assembly over-required separate value/context Locate outputs even where source positions or a quote already provided them. New scoring must use the rulebook-derived `record_policy.md`; do not rewrite the frozen baseline result or call missing helper outputs missing facts without reviewing their evidence.

## Final nine-point review received — preserved, not adopted

Verbatim source: `/tmp/claude_decider_review_20261115/final_review_20261115.md`.

Review each item when its part of the work is reached. For each, record the claim, governing rule/current implementation, source/test evidence, the smallest alternative, verdict and confidence. Keep rule confidence distinct from performance confidence. No recommendation is approved solely because several reviewers endorse it.

| Item | Topic | Current review state |
| --- | --- | --- |
| 1 | Evidence-centred field inference | Under review now; unit evidence is available, other fields and required metadata/history exceptions still need verification. |
| 2 | Construct evidence; keep continuous quote separately | Under review now; selected-sentence unit test completed, complete evidence construction unproved. |
| 3 | Sentence role classification/routing | Pending; no role menu adopted. |
| 4 | Move naming and qualifier work out of Decider | Pending; reconcile with the actual requested output and no-stronger-model requirement before accepting any responsibility transfer. |
| 5 | Qualifier-preserving shape choices | Pending; no shape/menu/schema change approved. |
| 6 | Link earlier numbers to current forecasts | Pending; no new comparison rule approved. |
| 7 | Sentence as worded value; hold multi-forecast sentences | Pending; no scope reduction or new hold policy approved. |
| 8 | Check every candidate has a recorded outcome | Pending code audit; preserve original raw scores and frozen artifacts. |
| 9 | Six-call reference and broader company census | Pending review of existing evidence/key gaps; no quoted frequency treated as universal. |

The review's rejection of phrase menus, dependency-parser layers, clause chains and counting/ordinal layers is recorded. It is not proof that the retained procedure meets the extraction goal. Current main strategy remains unchanged until the reconciled procedure is ready.

### Independent assessment after the six source readings

Read `final_review_assessment.md` for the item-by-item conclusions, evidence and confidence. The received-review table above records the initial state, not the latest disposition. Key corrections: exclusive sentence roles lose overlapping meanings; approximate/strict qualifiers cannot be replaced by one exclusive shape; canonical naming may remain later but identifying a record's measure cannot disappear; and all eight C targets omitted from copying were already accounted for by E. Earlier threshold removals still need consolidated outcomes. `final_review_item8_audit.json` accounts for all 333 B targets. The six-call source inventory is complete as a reading/location inventory, not an adjudicated gold key. No strategy or rulebook change has been applied.
