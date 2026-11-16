# Evidence-based field test

November 15, 2026, America/Toronto (EST). Current Driver rulebook governs; legacy guidance rows were not the answer key. Local `pplx-decider-v1.3:8bit`; no hosted calls, fallback model, runtime changes or database writes.

**Result:** the existing seven choice fields can be read correctly from reviewed evidence in this small development test. Automatic complete extraction is still unproved.

| Configuration | Correct fields | Time | Input tokens |
| --- | ---: | ---: | ---: |
| Existing field meanings, selected evidence | 40/42 | 140.02 s | 9,422 |
| Clear duration/instant definition, plus six semantic controls | 48/48 | 119.81 s | 10,084 |
| Same clearer definition, real company evidence only | 42/42 | 112.08 s | 9,516 |
| Same fields/rules, whole call instead of reviewed excerpts | 40/42 | 221.03 s | 19,803 |
| Whole call + explicit comparison-basis choice, then rule 3.33 | 42/42 resulting fields; 48/50 raw choices | 232.90 s | 20,621 |

The first run returned `unclear` for two annual growth time types; it did not confidently fill them incorrectly. The clarification uses quantity meaning: activity/performance/change over an interval versus a balance or snapshot at one instant. Fiscal-year wording alone does not decide. The controls pair cash flow with cash balance, store openings with stores operating at year end, and include growth and insufficient information. No company-specific rule or extra model question was added to the real-input configuration.

The final real-only comparison keeps the original 42 question IDs/order, options, all other field questions and byte-identical evidence blocks. Only the time-type definition and its six question references change. Thus the passing result does not require the synthetic examples in the state. All runs used one native sequence. Timing includes request wall time; cold-load and system-load effects are not separately established, so do not attribute the 28-second difference to wording.

The whole-call challenge restores every frozen source passage without supplying reviewed excerpts. It preserves question order, options and field rules; target addressing changes from a quote block to the corresponding exact occurrence in the call. It got both annual growth units wrong (`percent_yoy` instead of source-unsupported-basis `unknown`), at winning probabilities about .466 and .557. All 36 other field answers and four remaining units were correct. These are wrong choices, not measured wrong accepted records; no acceptance cutoff was applied. Whole-call visibility did not itself satisfy the rule against borrowing another figure's comparison basis.

This supports narrower evidence input for the tested field task, but does **not** prove a faster complete pipeline: automatically finding those excerpts has a cost and is not solved by this result. No extra evidence-selection layer is approved merely by the twofold field-stage timing difference.

The final alternative adds one comparison-basis choice per target to the **same native choice pass**, plus two real positive controls. All eight basis choices were correct: four nongrowth amounts, two growth amounts without stated basis, and two actual growth figures explicitly compared with the prior year. The original 42 questions and source remain unchanged; no reviewed excerpts enter the request. The original unit choices still got two answers wrong; applying the existing 3.33 absence rule produced the correct two `unknown` units. This is a tested policy decomposition, not a claim that all raw model answers became correct.

The two crucial absence scores were only **.521 and .590**. Thus 42/42 top-choice field outcomes do not establish reliable acceptance; no cutoff or full-record precision was calibrated. This prototype handles the tested absence rule, not every possible unit/shape/basis conflict. A clean separation of raw unit family from comparison basis would need testing before adoption, rather than presenting conflicting raw unit judgments as a finished normalizer.

Inspection also corrected an earlier comparison: `unit_basis_choice_request.json` included short `QUOTED_EVIDENCE` blocks alongside the call. Its earlier 4/4 result was not proof of a basis question using unscoped whole-call text alone. The new `basis_check_request.json` contains no such blocks.

## What the score covers

Six previously model-selected Cintas March expressions: revenue level/growth, adjusted diluted EPS level/growth, interest expense and tax rate. Each has seven choices: form, broad subject/scope, fiscal period label, unit/scale, sign, stated movement and duration/instant. The 36 non-unit expectations came from the saved source review; the six unit expectations follow current rules, including `unknown` for growth without an evidenced comparison basis.

The source review manually supplied evidence locations. Expected answers, reference meaning labels and legacy records never entered requests. Every excerpt was checked against frozen source offsets/hash. Source, calendar and speaker metadata accompany the excerpts. All six evidence blocks share one state; questions name their block. This is instruction-based scoping, not hard per-record isolation.

**Not tested:** automatic discovery/evidence completeness; exact measure association and canonical naming; all business slices; qualifier, condition and comparison extraction; independent fiscal-calendar resolution; complete records; unseen companies or transcripts. Forty-two fields are neither 42 independent facts nor six complete accepted records. Lowest winning probability in the final run was about 0.640; no acceptance cutoff was calibrated here.

The older whole-call comparison had 54 questions, including optional-field gates. Its 231-second runtime is not an exact matched comparison with these 42-question runs. Earlier unit-only results likewise must not be presented as full-record results.

## Reproduce and inspect

- `../quote_fields_probe.py prepare` freezes the original request and independent field key; `run` runs it.
- `../quote_fields_time_check.py` runs the clarified definition with controls; `--real-only` runs without them.
- `../quote_fields_whole_call_check.py` runs the matched whole-call field challenge without reviewed excerpts.
- `../quote_fields_basis_check.py` runs the added comparison-basis choice in that same whole-call batch; raw and rule-applied scores stay separate.
- Use the project `venv/bin/python`. Requests, references, results and scores are saved separately here. Read the request before re-running; existing files would be overwritten.
- Final request SHA-256: `b8669ce9f99025c2a6c3421407cfc0015b681a6c725e5f593e1e9610cae16046`.
- Main strategy and rulebook stayed unchanged. Running model/weight/conversion hashes remain unverified; the returned model name alone does not certify them.

**Decision:** retain this generic definition and evidence-based input as a supported component of the next complete test. Do not add another field layer or claim the unresolved measure/worded-forecast problems are solved. The next useful measurement is complete proposals with automatically selected evidence, scored by current rules.

Before building extensive sentence-to-forecast pairing, compare its total cost and full-record correctness with this narrowly tested same-batch alternative. The extra choices took one native sequence and about 12 more seconds in this run, whereas evidence selection has an additional unmeasured end-to-end cost. Both alternatives still need exact proof and cannot replace missing measure/condition/qualifier extraction. Neither is adopted as a complete procedure. Do not resume repeated isolated repairs of the three open failure classes.
