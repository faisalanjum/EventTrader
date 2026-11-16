# What the actual proposals show

2026-11-15, America/Toronto (EST). Current Driver rules govern. This reviews the measured stages assembled in `normalized.json`; it is not a new single-pipeline run, an independent blind gold evaluation, or a production acceptance decision.

| Proposal | Source-based review |
| --- | --- |
| Revenue $11.21B–$11.24B | Amount and basic fields are present. The selected condition copies retain constant FX but omit other stated shared assumptions. Incomplete. |
| Revenue growth 8.4%–8.7% | Same condition gap; growth wording/underlying revenue association is not fully separated. The comparison choice invents prior-year comparison despite the basis answer saying it was not stated. Incomplete. |
| Adjusted diluted EPS $4.86–$4.90 | Amount and raw measure wording are present. Copied exclusion is useful evidence but does not replace the missing shared assumptions or separately represented measurement qualifiers. Incomplete. |
| EPS growth 10.5%–11.4% | Same conditions/qualifiers gap; growth meaning must remain distinct from the EPS level. The comparison choice also invents prior-year comparison. Incomplete. |
| Approximately $101M annual net interest expense | The assembled proposal now has the required content for this narrow source claim: raw measure, 101/101 m_usd, FY2026 duration, approximately, source company scope, unknown movement, and exact supporting source. Ready for independent full-record review, not runtime acceptance. |
| 20% annual effective tax rate | Required content is present for this narrow source claim, including explicit prior-year baseline without an invented comparison number. Ready for independent full-record review, not runtime acceptance. |

The last two are the source's stated numeric assumptions, also eligible as forecasts of their own measures under the current rules. Their raw measure wording still includes the fiscal period; that is allowed at this extraction boundary and must not become the final Driver name. Final naming, company-ID binding, identity matching and graph writes remain outside the trial. No stronger writer filled a field.

**Counts:** six diagnostic proposals; four incomplete; two with required content in this source review; **zero certified/runtime accepts**. The reference is not independent blind gold and these six were selected for field testing, so 2/6 is not transcript recall or expected corpus accuracy. Tax-rate movement's winning probability is only .494; interest sign/movement are about .620/.642. No acceptance threshold has been calibrated. Do not turn a correct top choice into a confidence guarantee.

## Three bounded copy configurations

| Configuration | Choices | Copying | Time / input tokens |
| --- | --- | --- | --- |
| Complete prepared section, indirect copy-task references | 56/60 raw; 58/60 after existing 3.33 absence rule | No copied spans | 237.47 s / 18,226; two native sequences |
| Same state/grouping, explicit generic copy labels | Identical choice answers | Four spans; still no approximation or shared assumptions | 209.41 s / 18,412; two sequences |
| Same explicit copy labels on actual earlier model-selected sentences | Copy-only; no new choice answers | Five spans: constant-FX assumption twice, EPS exclusion twice, approximately once | 13.58 s / 1,124; one sequence |

The third input was selected by earlier model outputs, not by the reference key. It also removed unrelated field definitions and choices, so this is a practical copy-stage test, **not** a controlled claim that text length alone caused the improvement. All five returned spans map exactly and continuously to the original source. Five copies are not five recovered facts; two phrases repeat across targets.

The copy stage still misses the explicit no-future-acquisitions assumption despite that sentence being present. It also omits future-buyback/economic-disruption assumptions; several required qualifiers remain missing. Record this as **O4: incomplete modifier/assumption copying** and stop this repair chain. Do not change the runtime, lower Locate cutoffs, add a phrase list or invent missing tags. Broader measure/reference and worded-forecast problems remain open too.

## What this changes in the design decision

1. Keep exact code-owned numeric bounds and the current-rule level/change/revision distinction. Raw copied measure wording need not be a finished Driver name.
2. Explicit Locate labels are better supported than task-name indirection for this field-copy task, but still fail completeness.
3. Small automatically selected evidence can make copying much cheaper and recover a qualifier. Its selection cost and omissions still count; the 13.58-second result is not whole-pipeline latency.
4. The complete prepared section is a simple lawful continuous quote for these checked claims and restores the raising lead-in. It is **not** demonstrated to cover all applicable Q&A conditions or to be the best storage choice. No universal quote rule is adopted.
5. Do not add more fields/repair rounds just to make this sample pass. The next useful work is to reconcile the full procedure and its open cases, not keep tuning these six examples or declare the main strategy ready.

## Mechanical normalization check

`proposal_numbers.py` adapts the existing test unit menu, uses installed Babel 2.17 strict decimal parsing and the existing exact power-of-ten helper. Native source was inspected; Babel does not consume currency/percent signs or sentence punctuation. The only new lexical code recognizes one entire numeric token and removes those wrappers before native parsing. It does not find numbers within prose or infer their meaning. It rejects unsupported spelling, sign conflicts and unsupported unit choices.

Tests first failed because the adapter was absent, then passed real endpoint forms, zero/negative/leading-decimal controls, malformed/nonfinite inputs, exact scaling and a >28-digit precision control. All ten distinct numeric endpoint spellings in these six proposals normalize exactly. This is not an all-currency/all-locale parser claim. All 1,050 digit-bearing tokens in the six frozen calls are accounted for in `number_spelling_audit.json`: 553 lexically parseable, 497 unsupported. Those include years, quarter labels and speaker markers; these counts are neither accepted facts nor financial recall. Every unsupported token retains its original location and reason.

Rulebook, main strategy, runtime and database are unchanged. No commits, pushes or hosted calls.
