# Source-first development reference

The current Driver rulebook governs, as the owner reaffirmed on November 15, 2026. Legacy Guidance/GuidanceUpdate rows used an older structure. Read `../record_policy.md` before grading.

All six development calls have now been read directly, covering **186 stored passages**. The JSON files preserve exact source locations and manually assessed fields, plus an outcome/reason for every passage. The 102 entries include distinct claims, repeated or related representations, unconfirmed analyst claims, supporting assumptions and unresolved interpretations. **102 is not an eligible-fact count or an accuracy denominator.**

| Call | Passages | Entries | Legacy rows | Draft rows, including borderline |
| --- | ---: | ---: | ---: | ---: |
| Cintas 2025-09-24 | 36 | 15 | 8 | 11 |
| Cintas 2025-12-18 | 28 | 17 | 11 | 14 |
| Paychex 2025-09-30 | 23 | 18 | 10 | 15 |
| Paychex 2025-12-19 | 29 | 15 | 10 | 12 |
| Paychex 2026-03-25 | 38 | 19 | 7 | 12 |
| Cintas 2026-03-25 | 32 | 18 | 8 | 11 |

Each `_comparison.md` maps the source reading to the older inventories **after** reading that call. The annotation scripts only construct test references; their manually supplied names, values and interpretations must never enter discovery prompts. They are not extraction heuristics or production code.

Limits: prior conversation exposure exists; this is not two blind independent passes. Full-record field/period normalization and disputed interpretations are not adjudicated. The six calls cover only two companies and are already development data. Exact text checks prove location, not semantic correctness or the published-original production contract. Keep permitted unknowns, source-insufficient records, genuine extraction failures and schema differences separate.

Useful checks now supported: locating missing evidence; comparing known source amounts without using obsolete field defaults; checking old/current/actual roles, business scope, qualifiers and conditions versus causes; and detecting omitted period-specific or numberless claims. Remaining work: adjudicate meaningful differences, freeze expected outputs independently, and test the complete automatic procedure on untouched calls. No production-readiness claim follows from this inventory.
