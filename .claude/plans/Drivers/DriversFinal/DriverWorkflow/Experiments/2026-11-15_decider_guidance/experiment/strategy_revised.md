# Decider guidance extraction — next experiment

**Latest review:** `final_review_assessment.md` now qualifies this draft. All six source readings are saved in `reference_key/`; they are not yet adjudicated gold. Evidence-based field input is the next direction, but the measured unit batches shared all quote blocks in one state, not hard per-record isolation. The existing D full-call instruction and unsolved C copying steps below are not a finalized replacement procedure. Main strategy remains unchanged.

Reviewed 2026-11-15 (America/Toronto, EST). **No tested configuration has yet produced complete, correct extraction.** This document separates the next procedure from what has actually passed; it is not approval to run thousands of calls.

**Goal:** every eligible management forecast, with its correct meaning, fields and exact source evidence; then minimize time and code. Use local `pplx-decider-v1.3:8bit` through `config/local_llm.py`. No stronger model, company-specific rules, existing-name menu during discovery, runtime changes or database writes. [DRIVER_RULES_Categorized.md](../DRIVER_RULES_Categorized.md) governs; legacy GuidanceUpdates are comparison material, not exhaustive truth.

```text
Whole call → relevant complete passages → exact source candidates
           → establish their meaning and required evidence
           → fill supported fields → check complete record proposals
```

**Main simplification:** code preserves source locations and supplies printed numbers; the model judges what they mean. Define each task and its options once in shared state. Short occurrence questions retain the exact target text and its visible ID; passage/sentence checks use their source tags. Do not ask Locate to rediscover a number code already holds, or ask expensive metadata questions before required evidence exists.

## 1. Source preparation

Start with the agreed English, standard-format cohort. Read-only storage audit, 2026-11-15:

| Stored format | Count | Trial |
| --- | ---: | --- |
| Prepared remarks + structured Q&A, without alternative representations | 9,167 | Include |
| Structured Q&A, but missing prepared remarks or also having another representation | 305 | Defer |
| Q&A section/full text without structured exchanges | 136 | Defer |

All 9,472 structured-Q&A sources had ordered exchanges; all 9,320 prepared lists had nonempty blocks. This verifies storage structure, not completeness against publication. The 136 are not proved to be older calls. Recheck membership; audit: `/tmp/transcript_numbering_audit_20261115/server_report.json`.

1. Reuse read-only `QUERY_3B` and decoding in `scripts/earnings/builders/warmup_cache.py`. Require `HAS_PREPARED_REMARKS` and `HAS_QA_EXCHANGE`, neither `HAS_QA_SECTION` nor `HAS_FULL_TEXT`; the query does not load alternatives.
2. Number prepared blocks and complete Q&A exchanges in source order. Keep every speaker, question, answer and follow-up. Leave absent answers absent; the audit found 4,867 question-only exchanges. Attribution is judged from the actual speech, not just the stored speaker label.
3. Preserve immutable text and exact mappings for added passage `[P]`, sentence `[S]` and occurrence `[V]` tags. Use unique, collision-checked IDs. Equal text at different positions remains distinct. Offsets stay in code, never in prompts; tags/metadata are not quoted evidence.
4. The shared state contains task/option definitions, verified company/call/fiscal metadata, then the **whole call**, including unselected passages. Source text is evidence, not instructions. No truncation. A source too large for the runtime remains an explicit incomplete case.

Shared guidance definition:

> Guidance is a specific financial or operating forecast, target or outlook stated or clearly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and assumptions or qualifications that change a forecast's meaning. An assumption is independently guidance only when management forecasts that measure. Exclude actual results, merely recalled earlier forecasts, analyst-only estimates, vague optimism and boilerplate. A hypothetical illustration is not a committed forecast. Resolve references using the entire call; do not invent missing facts.

## 2. Fixed procedure to test

Save exact prompts, options and batching. Put reusable definitions in state once; independent questions share a request. Create another round only when its questions depend on earlier outputs. For a numeric/copied occurrence, `{T}` means **the exact source occurrence `"{literal}"` at `[{ID}]`**; a sentence target means **the whole sentence `[{S}]`**. Do not repeat entire passages in each question. Substitute source data and earlier outputs only, never expected answers.

### A. Retain complete relevant passages

One `noul` per prepared block/complete exchange, with the whole call:

> Under the guidance definition, does [{P}] state, reaffirm, withdraw or qualify management guidance? Use the whole call; an analyst's question alone is not confirmation.

Provisional development gate: `P(yes) >= 0.25`. Save every score. Check rejected passages against independently reviewed source truth; do not run every expensive extraction step on known negatives. This cutoff is not calibrated for production.

### B. Identify occurrences and roles

Within retained passages, use native `pysbd==0.3.4`, `Segmenter(language="en", clean=False, char_span=True)`, for sentence boundaries. Assert exact text, nonoverlap and complete non-whitespace coverage. It uses generic language rules; add no financial/company exceptions. Sentence boundaries identify targets, never limit context or imply one fact per sentence.

Code enumerates digit-bearing source tokens, retaining original punctuation/signs:

```python
[(m.start(), m.end(), m.group())
 for m in re.finditer(r"\S+", source_text)
 if any(c.isdecimal() for c in m.group())]
```

These are **locations, not parsed financial amounts**. Dates, repeated values and confirmed analyst wording cannot silently disappear. A token containing several numbers is not automatically one number or a range; unsupported splitting/normalization remains unresolved.

Batch full-context questions:

- **Numeric role, one `choice` per occurrence:** “What is the role of {T} under NUMERIC_ROLES?” Define these options once: `current` = current forecast amount, including endpoint/tolerance/explicit revision; `qualification` = supporting condition/bound/comparison; `earlier`; `actual`; `analyst_only` = unconfirmed; `hypothetical`; `other` = dates/identifiers/non-amounts; `unclear`. Do not use Locate as the number gate.
- **All guidance, one `noul` per sentence in retained passages:** “Does sentence [{S}] state, reaffirm, withdraw or qualify management guidance under the shared definition, whether numerical or expressed in words?” Include spelled-out numbers and references; use the full call. This replaces the worded-only question, rather than adding another detector. It detects coverage, not complete records.

For the next development trial, advance numeric occurrences whose selected role is `current`, `qualification` or `unclear`; a low probability flags uncertainty but does not discard a predicted work candidate. Retain guidance sentences at `P(yes) >= 0.5`, saving all scores for reference-based recall checks. These are work-routing choices, not accepted-record confidence thresholds. Supporting qualifiers do not automatically become independent forecasts; earlier/actual amounts remain available as evidence. A positive sentence can legitimately contain an old amount, date or actual comparison. **A sentence and its numbers are not separate forecasts by default; one record does not prove that a multi-fact sentence is covered.**

### C. Establish the whole candidate expression, then its evidence

For a current numeric amount, code already holds its literal text. Ask two `choice` questions, **lower** and **upper**, using all numeric occurrence IDs from its complete local passage, including endpoints that a role test rejected. Definitions once in `BOUND_SELECTION_RULES`:

> Select the stated lower/upper value of the current management forecast containing the target. A point uses the same occurrence twice; a closed range uses its stated endpoints; an unstated side of a one-sided bound is absent. If the target is not a current forecast amount, choose `no_current_forecast`. Never substitute another forecast or calculate an unstated amount.

Also provide `no_stated_bound`, `elsewhere`, `several`, `unclear`. Each short question still includes the literal and ID. Source tags supply numeric option text; special-option meanings appear once. Do not truncate a menu beyond the native 255-choice limit. Only consume bounds for an eligible role; later form/field checks must establish compatibility. **Bounds do not replace the role gate:** date references selected nearby forecast values in testing. Centre/tolerance is not a range; a source span with several numbers still needs supported numeric interpretation.

For numeric candidates with supported bounds, construct the exact continuous source span covering those selected occurrences. A missing side keeps the available occurrence, never an invented endpoint. Add an `[F]` tag and retain the original `[V]` IDs. Group only identical source spans for identical questions, preserving every alias; **this groups work, not facts**. One span may still describe several measures/periods. Unavailable/ambiguous bounds stay unresolved.

For worded candidates, use one Locate in the whole prepared section or complete Q&A:

> For sentence [{S}], copy each current expectation, reaffirmation or withdrawal, including limiting words. Keep separate forecasts separate; do not substitute actuals or old guidance.

A selected sentence is not itself a value or one record. Missing/multiple unassociated expressions remain unresolved. Broad and targeted worded-value copying have repeatedly failed; no count/word/ordinal repair chain.

Now `{T}` identifies an established candidate **expression**, with its exact literal and `[F]` tag. Before expensive interpretation, batch two Locate fields in its whole prepared section/complete Q&A:

| Field | Instruction, naming {T} |
| --- | --- |
| Measure and qualifiers | Copy source wording naming this financial/operating measure and its measurement/business-scope qualifiers. Resolve references, including clearly confirmed analyst wording. A bare amount, unit or date is not a measure name. |
| Required support | Copy wording establishing this forecast's period, unit/scale, limiting words and attribution where not already established by its other copied evidence. |

Remote references need their actual source evidence; local copying cannot silently borrow it. Empty, ambiguous or multiple unassociated required fields are unresolved. **Repeated measure/support Locate tests have not solved this step (§5).** Do not add a known-name catalogue or another prompt-repair chain. Whole-expression targeting is the next bounded test, not a claimed repair of Locate.

### D. Interpret only viable candidates

Use the full call. Put `FIELD_RULES`, fiscal-period meanings and unit definitions once in state; ask “For {T}, answer `{field}` using FIELD_RULES.” Each menu includes `unclear`; all probabilities are saved. The short shared-definition configuration must pass before replacing the older wording.

| Field | Options / rule |
| --- | --- |
| Form | Point; closed range; floor; ceiling; words; revision only; qualification only; reaffirmation; withdrawal; centre-plus-tolerance; several; none; unclear. Keep separate measures/periods separate. |
| Subject/scope | Whole call company; stated part; another identified subject; genuinely shared; unclear. Additional subject/scope wording requires exact evidence; never assume unknown means shared. |
| Period | Verified concrete fiscal **and calendar** periods with dates; explicit short/medium/long/undefined horizon; other stated; several; unclear. No nearest-period guess. |
| Unit/scale | Evidenced combinations under 3.28/3.54/9.1; other stated; numberless; unknown; several. A percentage level differs from growth. No basis inferred from the metric name/magnitude/history. |
| Sign | Positive; negative; zero; nonnumeric; several; unclear. Respect the quantity's meaning and each amount; mixed/unsupported cases remain unresolved. |
| Movement | Introduced; raised; lowered; reaffirmed; withdrawn; not stated; unclear. `not stated` → `unknown`; never calculate movement. |
| Time type | Duration; instant; unclear. No default. |

Calendar menus require verified subject metadata, including fiscal-year naming and week calendars. The development fixture's month-end calendar is not a universal resolver. Unit menus must use the saved official lists; no invented codes. `other stated` requires evidence/resolution, not a forced common unit.

**Unit evidence:** keep one unit/scale question, explicitly grounded in the candidate's actual quote: “What unit and scale does QUOTE explicitly support for `{literal}` at [{ID}], under the unit rules? A percentage level is not growth.” This passed the 12-control comparison (§5); do not add a mandatory yes/no, separate basis question or keyword parser. Apply 3.33, including points/basis-points precedence, annual sequential → yearly, vague horizons and percentage-on-percentage limits. Preserve two explicitly stated bases separately. No stated basis → `unknown`; missing applicable evidence is an extraction failure, not evidence of absence. Widen quotes under 3.29 when needed; these tests do not establish automatic quote completeness. This question can use a short complete quote; do not assume the containing sentence always suffices.

In this batch, also ask two `noul` presence questions:

> Does management attach an assumption, exclusion, dependency or qualification changing this forecast's meaning, including an applicable shared statement elsewhere? Exclude boilerplate and mere causes.

> Does management attach an explicitly stated earlier-forecast comparison or revision amount? Exclude arithmetic deductions.

Name `{T}` in each. Copy the corresponding field with Locate **only when presence is >= 0.5**, using the full call for shared/remote evidence. Request every applicable source-stated qualification, or the stated comparison/revision with unit/baseline. A false no, empty copy after yes, or incomplete copy is a failure; nonempty does not mean exhaustive. No blanket copying after no.

### E. Assemble and check

- Reconstruct every span from immutable source; check exact offsets/text and remove only inserted tags through the map. Code builds one continuous quote covering the fact, attribution and every meaning-changing qualification, including a question when required. No separate Evidence Locate or joined-fragment quote schema.
- A complete proposal needs subject, measure, scope, qualifiers, period, value, unit/scale/sign, stated movement, conditions and explicit comparisons/revisions as applicable. Do not zip lists, pick the first name, collapse several forecasts, or accept merely because the schema is valid.
- Exact normalization only: no invented endpoints, midpoints, revisions, units or repaired transcription. Preserve approximations/inequalities; management-stated calculations may be copied. Unresolved centre/tolerance, compound numeric strings or word-number parsing stay held with raw evidence. Unsupported is not absent.
- Numberless guidance follows 4.7: `value_text` at most 200 characters, numeric fields empty, period anchors allowed. Meaningful missing qualifiers are never trimmed away. Conditions are assumptions, not inferred causes (4.8).
- Apply the subject's calendar/history/slices (3.9, 3.17–3.18), not the affected stock's or automatically the call owner's. Preserve qualifiers (3.26). Discovery stays blind to existing Driver names (1.14); global canonical matching remains later.
- Preserve exact rescaling once, the bare-dollar convention (9.1), and source-backed growth basis (3.33). `unknown` is allowed where the rulebook permits it and the source genuinely does not settle the field; failed extraction of stated evidence is different. An unresolved period without an explicit horizon fails.
- Forecast growth is a value; `change` means an explicit revision (4.6). Broad reaffirmation/withdrawal requires proven prior scope (3.35, 4.18–4.21). Apply fact-type boundaries (1.23/10.5) and management confirmation (1.26/4.9).
- Merge duplicate targets only after the complete same fact is established; equal numbers, spans or endpoint pairs alone do not prove identity. Preserve conflicting claims. Account for every retained target and every independently expected fact.

Return proposals, raw evidence/probabilities and explicit unresolved/rejected/technical outcomes. No database writes or legacy writer. No automatic acceptance based solely on model probability.

## 3. Current rules and pending owner choices

1. Rule 1.24 requires one exact quote and does not explicitly limit it to one speaker; cross-block evidence still needs verification. How this extractor should handle far conditions remains **undecided**; this permission is not an approved extraction workflow or new storage exception.
2. An explicitly forecast tax/interest amount may be its own guidance fact and an assumption supporting another forecast. Not every numeric assumption or actual is guidance.
3. Standing targets follow source words: this year → that fiscal year; “going forward” → explicitly `undefined`, not automatically long-term (3.40). Two records require two established target periods. Add no interpretation to conditions.

**Pending, not approved:** range-relative values may keep a restated range plus position wording, otherwise wording only; centre/tolerance may remain held with both printed numbers and a reason; blanket reaffirmations/withdrawals may remain held and counted as “no named metric.” Do not implement these as new rules until reviewed. Details and the latest preliminary suggestions: `/tmp/decider_claude_review_20261115/pending_claude_review.md`.

## 4. Runtime, tests and stop rules

```python
from config import local_llm as L
result = L.decide(state, questions, mode="isolated", timeout=1800)
```

- Pin source hashes, model, actual weights/conversion/runtime, rendering, prompts/options and grouping. The copied Mac guide does not verify running hashes. Local Locate includes a punctuation change.
- `isolated` shares state reading; an extra question is **not** automatically another whole-call read. Extra rounds/batches reread, and Locate/decisions use separate passes. Shared context can also reflect the question group: matched wording variants must run separately. No assumed cross-request cache/CUDA speedup.
- Local limits: 32,768 tokens including protocol/questions; <=128 total questions if Locate is present; <=255 choice options. Use native packing/accounting, not silent text/menu truncation or custom retry chains. Locate's proposal/span caps and score filter do not guarantee completeness; no wrapper cutoff setting exists.
- Native checks: pySBD exact offsets/coverage passed nine snapshots. Legacy numeric parsing fails on general percentages/ranges and uses floats; Decimal helpers preserve exact values but do not parse financial meaning. Existing month-based fiscal helpers do not prove 52/53-week dates. Reuse tested native behavior; record a demonstrated gap before writing custom code.

**Test order:** establish source-based expected records in two independent review passes; use legacy rows only for comparison. Run the complete procedure on development calls; inspect rejected passages against the key rather than extracting all negatives. Fix priority follows **distinct complete facts affected**, not memorable examples, duplicate targets or raw legacy counts.

Keep a new step only if its measured gain in complete correct records justifies its time/questions/code. Component success justifies a bounded next test, not production adoption. After three unsuccessful fixes to a failure class, log it open and move on; keep those facts in the denominator. After every test append three lines to `progress.md`: test, result, next.

Then freeze the configuration and test untouched companies, calendars, units and styles, including negative controls and generic reorder/paraphrase/missing-context tests. All six CTAS/PAYX and three MU/FDX/OLLI snapshots used here are development data now. Approximately 300 independently checked records would support a stronger estimate, not universal certainty; calls are correlated. Do not tune on the final test.

**Pass:** every eligible reference fact is complete and correct, with no wrong/duplicate accepted records. Report correct complete records, wrong accepts, missing/partial facts, extras, holds and technical failures separately. A held expected fact is incomplete extraction. If nothing passes, say so; never substitute “all difficult cases flagged” for success. Named-Driver lookup is a separate later task, not permission to use known names during discovery.

## 5. Measured findings and open work

| Measured change | Result and limit |
| --- | --- |
| Frozen original A–E main path | 42m55s, 1,001 questions; 49 unresolved and four rejected targets, no complete proposal. Some evidence checks were redundant; this rejects that baseline, not every possible Decider procedure. |
| Exact literal + occurrence ID instead of ID alone | 25/25 numeric role controls correct, previously 16/25; 190s versus 189s. It did not repair Locate field copying. |
| Numeric bounds selected from source IDs; shared definitions and short questions | 25/25 checked bound pairs correct in 256s; original verbose test was 22/25 in 674s. Numeric value copying through Locate is unnecessary for these cases. |
| Fields asked once per identical, model-established expression | 90→54 questions; 274→231s; 36/36 unambiguous categorical choices correct. Two unsupported growth units and shared-condition misses remained. Grouping work is not merging facts. |
| Shared numeric roles + all-guidance sentence check | 333 questions in 343s; all 16 required numeric occurrences advanced, two extra actuals also advanced. Thirteen chosen guidance sentences retained and six actual controls rejected. No complete sentence/record key, so no overall recall or false-positive rate. |
| Growth-basis evidence presence | 4/4 checks correct in 183s. One evidence-based choice also passed 4/4 in 193s and identifies the basis without a separate boolean. |
| Broader evidence-basis choice | 18/18 top choices: eight real excerpts and ten controlled variations, 47s on short quotes. Four real excerpts overlap the preceding test; one annual-comparison answer was only 0.538. This tests the component, not quote construction or full extraction. |
| Existing full unit choice grounded in each exact quote | 12/12 controls in 33s / 2,867 input tokens, versus 11/12 in 196s / 16,998 tokens with the earlier whole-call framing. No separate presence/basis question needed in this comparison. Automatic complete evidence remains unproved. |
| Source sentence pointer → short measure Locate | 11/15 naming pointers correct in 220s; short copying took 35s. Twelve nonempty outputs included two confidently wrong measure labels and incomplete/overwide names. Indirect references and complete measure fields remain unresolved; do not adopt this as a solved replacement. |
| Forecast-to-support-sentence association | 108 questions in 215s; all 12 known positives found, two extra selections among 76 known negatives; 20 other pairs unadjudicated. This selects evidence, not the final conditions field. |
| Units after automatic evidence selection | Continuous quotes: 3/4 correct in 75s; same selected sentences with gaps omitted from inference: 4/4 in 19s. Original continuous quotes were preserved. This is four unit checks, not full extraction. |

Verified review counts: speaker annotations account for 363/1,050 numeric tokens across the six snapshots, including 19/120 B questions. Reuse proven stored-turn/header boundaries to omit these metadata candidates while keeping names and original source mappings; the existing census helper strips the whole prefix, so do not feed its speaker-less output to the model. Full-cohort format verification and measured time savings remain pending.

The supplied 69-core/6-borderline inventory's arithmetic is verified, but it has no quotations/offsets and is not a complete gold key. Its six calls cover only two companies. Neighbour-number grouping and blanket condition-sentence linking remain untested suggestions, not approved layers. Sentence-pointer→short-Locate was tested and remains unresolved. Do not turn a neighbouring-number relation chain into automatic record merging.

The required blind measure, worded-value/multiple-forecast and complete-condition paths remain unresolved. The independent full-record answer key, running-runtime fingerprints, complete revised end-to-end test and untouched test are unfinished. Do not launch a corpus-wide extraction or extrapolate complete-pipeline time from component timings.

Evidence, all 66 review dispositions, scripts, exact requests/results and `progress.md`: `/tmp/decider_claude_review_20261115/`. Supplied review evidence: `/tmp/claude_decider_review_20261115/`. Temporary files may disappear; preserve a reviewed evidence snapshot before implementation handoff. This document supplies the procedure independently.

The final nine-point review is preserved verbatim as `/tmp/claude_decider_review_20261115/final_review_20261115.md`; item-by-item review status is in `pending_claude_review.md`. It has not been adopted wholesale. Source-based scoring must follow `record_policy.md`, including the distinction between a missing helper output and genuinely missing evidence.

References: [Decider model/API](https://huggingface.co/perplexity-ai/pplx-decider-v1.3), [pinned native Locate](https://huggingface.co/perplexity-ai/pplx-decider-v1.3/blob/9c2ebb27470d3dec2ad7ab727727e40d142c7213/source/src/pplx_decider/locate.py), [TypeSafe candidate selection](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), [composition](https://docs.typesafe.ai/concepts/how-to-build-with-system-one), [pySBD offsets](https://github.com/nipunsadvilkar/pySBD/blob/v0.3.4/pysbd/segmenter.py).

## Hosted comparison — separate future test

Pin `pplx-decider-v1.3`, never `-latest`; treat hosted and our modified local runtime as different configurations. Hosted precision/runtime parity was not established. Revalidate on development data; never tune on the final test.

The [official API contract](https://docs.perplexity.ai/docs/decisions/quickstart) documents grouped questions, <=128 questions when Locate is present, a 256K input limit and default 10 requests/second plus model-specific token limits. It exposes no local isolated/separate, temperature or Locate-cutoff controls. Keep web grounding off; extraction uses its own source. Hosted inputs leave the Mac.

Do not automatically add spaces around punctuation. First test original-text results on the boundary suite and real sources; any demonstrated transformation requires exact offset mapping and revalidation. No hosted calls were made in this review.
