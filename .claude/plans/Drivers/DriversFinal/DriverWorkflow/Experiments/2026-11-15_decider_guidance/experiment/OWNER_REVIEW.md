# Decider — one-page stopping memo

**Run finished November 15, 2026, 10:48:51 PM EST**, using local `pplx-decider-v1.3:8bit`. Both pending checks are finished. **Finding claims works better than completing reliable records; standalone extraction is not ready.**

**1. What is demonstrated.** Number-role classification passed 25/25 small controls; quote-based units passed 12/12. These are component results. The separate sentence check retained 21/22 positive controls at .25, missing a margin exclusion; some past results were also selected. The calendar check covered 9,167 transcripts/789 companies: 80 stored year-end months matched none of their recent annual endings, 45 matched some, and 124 companies had non-month-end endings. These are review categories, not 125 proven errors. Supplied exact dates work; general calendar acquisition/cache accuracy remains unverified.

**2. Owner rulings, with options.** These concern unusual representations, not ordinary extraction failures:

- Range plus “high/low end”: **keep printed bounds and exact wording** (recommended), or hold (`H_RULE_RANGE`); never calculate a point.
- Printed midpoint alongside a range: **retain it in that forecast’s quote** (recommended), or approve separate representation (`H_REPRESENTATION`).
- Centre ± tolerance: **hold both printed numbers** initially (recommended, `H_RULE_TOLERANCE`), or approve centre/tolerance fields.

Existing rules already allow numeric assumptions as forecasts, distinguish causes from conditions, require one continuous supporting quote, and treat “going forward” as an undefined horizon. These need implementation, not new owner rules. Ambiguous source interpretations still need reference review.

**3. What remains blocked.** Measured Decider failures include wrong range forms/comparison relationships and incomplete measure, period and qualification evidence. They do not prove the model incapable under every setup. Separate implementation gaps include worded-value extraction, complete comparison assembly, reversed signed bounds, redundant acceptance checks and general calendars. Five saved inputs also lack speaker metadata, causing 304 unnecessary timestamp questions.

Named test holds cover missing measure (`H_MEASURE`), association/bounds (`H_ASSOCIATION`, `H_BOUNDS`), evidence/modifiers/fields (`H_EVIDENCE`, `H_MODIFIERS`, `H_FIELD`), confidence (`H_CONFIDENCE`), words/multiple claims (`H_WORDS`, `H_MULTIPLE`), eligibility/prior scope (`H_ELIGIBILITY`, `H_PRIOR_SCOPE`), calendar/number/technical failures (`H_CALENDAR`, `H_NUMBER`, `H_TECHNICAL`), and detected sentences without records (`H_SENTENCE_UNRESOLVED`). These are experiment labels, not production retry queues.

**4. Full procedure actually run.** Preserve source text/positions; number sentences and numeric occurrences. With the whole call visible, screen sentences at .25 and classify number roles at .5; these cutoffs are uncalibrated. Retain positive sentences and uncertain numbers as holds; advance confident current numbers. Select lower/upper occurrences and combine identical pairs. Ask form, subject, period, unit/scale, sign, movement, time type, growth basis, amount meaning and comparison baseline. Copy measure/context/qualifiers from prepared remarks or Q&A; copy conditions/comparisons from the call only after positive presence checks. Reuse number/period helpers, retain raw answers/evidence/holds, then review against source without repairing outputs. No retries, alternate models or prompt changes. Exact procedure/requests: [runner](frozen_six_run.py), [saved run](frozen_six/).

| Call | Complete | Held | Missed |
|---|---:|---:|---:|
| Cintas Sep 2025 | 0 | 12 | 0 |
| Cintas Dec 2025 | 0 | 14 | 0 |
| Cintas Mar 2026 | 0 | 14 | 0 |
| Paychex Sep 2025 | 0 | 14 | 0 |
| Paychex Dec 2025 | 0 | 12 | 0 |
| Paychex Mar 2026 | 0 | 13 | 0 |
| **Total** | **0** | **79** | **0** |

“Complete” requires correct fields/evidence and no remaining hold; “held” includes partial extraction; “missed” means a confirmed claim was not retained. **Zero missed does not mean every detail was found.** Two proposals have correct reviewed content but remain held. One incorrect proposal cleared automatic holds and was caught by source review. Four repeated proposals were not counted twice.

The run took **2h 56m 52s** (24–39 minutes/call), selecting 408 sentences and producing 45 numeric proposals. Counts above cover 79 confirmed development claims; 23 other reference entries remain separate. This is two companies, an exposed reference, and extraction before final naming/writing—not independent certification. [Results](frozen_six/run_summary.json), [claim reviews](frozen_six/review_counts.json), [integrity checks](frozen_six/integrity.json). Production code, main plans and database unchanged. **Stopped; waiting for owner.**
