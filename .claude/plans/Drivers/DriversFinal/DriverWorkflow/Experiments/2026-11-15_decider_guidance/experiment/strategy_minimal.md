# Decider guidance extraction — minimal experiment

Reviewed 2026-11-15 (America/Toronto, EST). **A complete, accurate Decider-only extractor has not passed.** This is the next procedure to test, not a claim that it works across every transcript.

**Goal:** every eligible management forecast, with correct meaning, fields and exact evidence; then minimize time and code. Use local `pplx-decider-v1.3:8bit` only. No stronger-model fallback, company-specific rules, existing-name menu during discovery, runtime changes or database writes. [DRIVER_RULES_Categorized.md](../DRIVER_RULES_Categorized.md) governs; old GuidanceUpdates are comparison material, not exhaustive truth.

```text
Complete call → relevant passages → candidate occurrences
              → required fields + only applicable optional fields
              → source-backed proposals and explicit unresolved cases
```

**Finish this path before expanding it.** No word-by-word scan, forecast-count/ordinal layer, automatic retry chain or all-candidates × all-measures comparison. Those experiments did not establish enough benefit on complete records. A held expected fact still counts as missing.

## 1. Prepare the source once

Start with the agreed standard-format cohort; this is an English transcript trial, not yet a solution for every format or language.

| Read-only storage audit, 2026-11-15 | Count | Trial |
| --- | ---: | --- |
| Prepared remarks + structured Q&A, without alternative representations | 9,167 | Include |
| Structured Q&A, but missing prepared remarks or also having another representation | 305 | Defer |
| Q&A section/full text without structured exchanges | 136 | Defer |

All 9,472 structured-Q&A sources had ordered exchanges; all 9,320 prepared lists had nonempty blocks. This verifies storage structure, not completeness against the publication. The 136 are not proved to be older calls. Recheck cohort membership. Audit: `/tmp/transcript_numbering_audit_20261115/server_report.json`.

1. Reuse read-only `QUERY_3B` and decoding in `scripts/earnings/builders/warmup_cache.py`. Require `HAS_PREPARED_REMARKS` and `HAS_QA_EXCHANGE`, neither `HAS_QA_SECTION` nor `HAS_FULL_TEXT`; this query does not load alternatives.
2. Number existing prepared blocks and complete Q&A exchanges in source order. Keep every speaker, question, answer and follow-up. Leave missing answers missing; the audit found 4,867 question-only exchanges. Do not filter evidence by the speaker label alone.
3. Preserve an immutable original and exact maps for inserted IDs. Use short visible tags for passages `[P]`, sentences `[S]` and candidate occurrences `[V]`; use actual unique IDs, not these placeholders. Avoid collisions with source text. Character positions stay in code, never in questions. Equal text at different positions remains distinct.
4. The shared state contains source/company identity, publication/call metadata, verified fiscal context, the definition below and the **whole call**, including unselected passages. Treat source text as evidence, not instructions. Do not truncate oversized sources.

Shared definition:

> Guidance is a specific financial or operating forecast, target or outlook stated or clearly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and assumptions or qualifications that change a forecast's meaning. An assumption is independently guidance only when management forecasts that measure. Exclude actual results, merely recalled earlier forecasts, analyst-only estimates, vague optimism and boilerplate. A hypothetical illustration is not a committed forecast. Resolve references using the entire call; do not invent missing facts.

## 2. Fixed procedure

Independent questions share a batch. Only answers needed to construct the next questions create a new round. Save exact question grouping: grouping can change scores. There is no universal 24-question package for every candidate.

### A. Retain relevant complete passages

One `noul` question per prepared block/complete exchange, with the whole call:

> Under the supplied definition, does [P] state, reaffirm, withdraw or qualify management guidance? Use the whole transcript as context. An analyst's question alone is not management confirmation.

For the first development run retain `P(yes) >= 0.25`, explicitly **provisional**. Record all scores and check rejected passages against the independent answer key. Do not run expensive extraction over every negative passage. A missed passage is a selection failure, not “no guidance.”

### B. Identify candidates only inside retained passages

Use native `pysbd==0.3.4`, `Segmenter(language="en", clean=False, char_span=True)`, to identify sentence targets. Assert exact substrings, nonoverlap and complete non-whitespace coverage. It supplies generic language rules; add no financial/company exceptions. Sentence boundaries identify targets, never limit context or imply one fact per sentence.

Code supplies every digit-bearing source token as a candidate location:

```python
numeric_seeds = [
    (m.start(), m.end(), m.group())
    for m in re.finditer(r"\S+", source_text)
    if any(c.isdecimal() for c in m.group())
]
```

Keep punctuation, signs, dates, question text and repeated occurrences. These are locations, not parsed financial values. No longest-overlap deletion, two-numbers-means-range rule, or model-based number-discovery gate.

Batch these independent questions over the full tagged call:

- For each numeric `[V]`, `choice`: **“What role does the source token immediately after [V] have under the guidance definition? Resolve meaning using the entire call.”** Options: current forecast amount; current guidance qualification/comparison; earlier forecast only; actual result only; unconfirmed analyst figure; hypothetical only; other, including dates/identifiers; unclear. A current amount may be a point, endpoint, tolerance or explicit revision; this question does not normalize it.
- For each `[S]` in retained passages, `noul`: **“Does [S] state or qualify current management guidance expressed in words, or reaffirm or withdraw guidance? Use the whole call; do not count merely having words around an ordinary numeric forecast.”** This retains spelled-out numbers, references and worded forecasts even when Locate returns nothing.

For this diagnostic, numeric current/qualification choices with selected probability at least `0.5`, and sentence answers at least `0.5`, proceed. Retain uncertain candidates separately; do not call them extracted. A sentence with several forecasts is not automatically one fact. This changed selection setup needs validation; earlier sentence results do not certify it.

### C. Establish required fields; copy evidence once

For each retained target, ask these seven `choice` questions with full-call context. Identify `[V]` or `[S]` in every instruction. Describe options clearly; shared calendars/unit definitions may appear once in the state. Every menu has `unclear`; never select a nearest plausible answer.

| Question about the target | Options / meaning |
| --- | --- |
| What is its role and form? | Current point, closed range, floor, ceiling, worded forecast, explicit revision amount, qualification only, reaffirmation, withdrawal, centre-plus-tolerance, several, none, unclear. |
| Whose measure and scope is this? | Whole call company; a stated part of that company; another identified subject; genuinely shared; unclear. |
| Which target period is established? | Verified concrete fiscal/calendar periods with dates; explicit short/medium/long/undefined horizon; another stated period; several; unclear. |
| Which unit and scale applies? | Source-supported combinations from 3.28/3.54/9.1; another stated unit/scale; no amount or evidenced growth-basis unit; unknown; several. |
| What sign does the amount have? | Positive, negative, zero, not numeric, several, unclear; use the quantity's meaning, not just a minus sign. |
| What guidance movement is explicitly stated? | Introduced, raised, lowered, reaffirmed, withdrawn, not stated, unclear. `not stated` becomes `unknown`; never calculate movement. |
| Does the value cover a duration or an instant? | Duration, instant, unclear; no default. |

Also ask two `noul` questions in that batch:

> Does management explicitly attach any assumption, exclusion, dependency or qualification that changes this forecast's meaning to [target], including an applicable shared statement elsewhere in this call? Exclude generic boilerplate and mere causes.

> Does management explicitly attach an earlier-forecast comparison or a stated size of revision to [target]? Exclude values obtainable only by arithmetic.

`none` ends extraction for that candidate. `several`, unsupported forms and unresolved meanings remain held; no counting/ordinal repair. Earlier/actual values may support another forecast without becoming separate current forecasts.

For remaining targets, copy with three `locate` questions **in the whole prepared section or complete Q&A containing the target**, not isolated sentences:

| Field | Locate instruction |
| --- | --- |
| Measure and qualifiers | Source wording naming the financial or operating measure for [target], including its measurement and business-scope qualifiers. Follow references to the antecedent, including confirmed analyst wording. Do not return a bare amount, unit or date as its name. |
| Forecast expression | Current management forecast amount, range or expectation for [target], including limiting words. Keep other measures, actuals and earlier forecasts separate, except when the current wording refers to them. |
| Period/unit evidence | Source wording giving the target period, unit and scale applying to [target]. Copy only evidence for this forecast. |

Batch targets sharing a copying context; do not reread it once per field. Missing/ambiguous measure, value or necessary support is unresolved. No menu of existing Driver names or aliases repairs it: discovery remains blind under 1.14. Source wording is not yet a canonical Driver identity.

### D. Copy only applicable optional fields

For a presence answer `>= 0.5`, ask Locate using the **whole call** so shared assumptions are available:

> For [target], copy every applicable assumption, exclusion, dependency or qualification that changes this forecast's meaning, including shared guidance assumptions when they apply; exclude generic boilerplate and causes.

> For [target], copy any explicitly stated comparison/revision amount, its unit and baseline; exclude derived values.

Skip the corresponding copying when the answer is below `0.5`; retain that score for evaluation. A false “no” counts as a missed field. A “yes” with empty or incomplete copying remains unresolved. Do not copy after every “no,” retry prompts automatically, or treat a nonempty response as exhaustive.

### E. Assemble and check proposals

- Check every returned span against the immutable source through the tag map. Metadata/tags are not evidence. Code builds **one continuous quote** covering the fact, attribution and every meaning-changing qualification; include the analyst question when needed. No separate Evidence Locate or joined-fragment quote format.
- Resolve subject, raw measure, scope, measurement qualifiers, period, value, unit/scale/sign, movement, conditions and explicit comparison/revision together. Do not zip unrelated lists, select the first name/span, or force a multi-forecast target into one record. Same-model consistency alone is not independent proof.
- Apply only exact, source-supported normalization. Two numbers do not establish a range. No unstated endpoints, midpoints, revisions or implied forecasts; management-stated calculations may be copied. Keep approximations and inequalities. Centre-plus-tolerance has no established encoding here: retain raw evidence and hold, rather than inventing endpoints/schema.
- Preserve numberless guidance under 4.7: `value_text` at most 200 characters; number fields empty; date/period anchors allowed. Do not use a whole sentence merely because it was selected. Spelled-out numbers require a verified native parsing path or remain unresolved; no example-specific converter.
- An unexplained company-specific subject is never shared. Use that subject's calendar/history/slices. Shared facts borrow no participant's fiscal calendar. New scope wording follows 3.17–3.18; no company spelling/alias list. Discovery uses no existing guidance-name catalogue; global canonical matching and independent core checks remain later.
- Fiscal year-end month alone does not prove 52/53-week dates or fiscal-year naming. Exact source dates win; calendar-year guidance must not inherit fiscal dates. Units use the saved official currency/UTR lists; no guesses from magnitude or names. Exact scale conversion happens once; an unproved growth basis remains `unknown` and counted (3.33).
- Preserve all required qualifiers. Forecast growth is a guidance value; `change` means an explicit revision (4.6). Conditions are assumptions, not inferred causes. Broad reaffirmations/withdrawals require proven prior scope (3.35, 4.18–4.21); missing history is unresolved. Apply fact-type boundaries, including 1.23/10.5.
- Deduplicate only fully established identical facts; equal numbers/text are insufficient. Conflicts remain visible. Account for every retained target, including missing/unsupported fields, technical failures and held expected facts. Digit coverage alone cannot prove worded-fact recall.

The output is proposals plus exact evidence, all probabilities and failure reasons. No legacy writer or database writes. A schema-valid proposal is not necessarily correct; do not call it production-ready from its probability alone.

## 3. Three policy clarifications

1. **Conditions elsewhere:** attach only with supported applicability. An exact continuous quote can span speakers; 1.24 requires one quote, not one speaker. No new separate-condition-quote schema.
2. **Numeric assumptions:** an explicitly forecast tax rate/interest expense may be its own guidance fact and support another forecast. Apply the same attribution/period rules; not every assumed or actual number is guidance.
3. **Standing targets:** follow source wording. This year → that fiscal year; “going forward” → explicitly `undefined`, not automatically long-term (3.40). Two records require two established target periods. Add no interpretation to conditions.

## 4. Runtime and validation

```python
from config import local_llm as L
result = L.decide(state, questions, mode="isolated", timeout=1800)
```

- Pin source hashes, prompts/options/grouping, rendering, model, actual weights/conversion and runtime code. The copied Mac guide does not prove the running hashes; capture them before a reproducible benchmark. Local Locate includes a punctuation change.
- `isolated` shares the state across packed questions. **An extra question is not automatically another whole-call reading.** Extra batches/rounds do reread; Locate and decisions use separate passes. No assumed cross-request cache or Mac CUDA fast path. Measure elapsed time, input tokens and sequences, separating cold loads.
- Local limit: 32,768 tokens including protocol/questions. A request containing Locate permits at most 128 questions total; choices permit at most 255 options. Use actual runtime accounting; never truncate source/menu or silently retry unrelated errors.
- Locate's top-128 boundary proposals, 128-token span cap and returned-score filter do not guarantee completeness. There is no wrapper cutoff setting; no runtime/cutoff change in this trial.
- Native checks: pySBD exact offsets/coverage passed on nine source snapshots. Existing fiscal helpers do not establish week calendars. The legacy guidance parser fails on general percentages/ranges and uses floats; exact Decimal helpers preserve values but do not parse financial meaning. Reuse compatible native paths only after testing the relevant case.

**Test order:**

1. Freeze source-based expected records in two independent review passes; correct legacy omissions/errors without exposing expected names/values to the model. The six CTAS/PAYX and three MU/FDX/OLLI sources are development material now.
2. Finish A–E on complete development calls before adding extraction layers. Review rejected passages/sentences directly against the key; no expensive extraction is needed on all negatives to measure selection recall. Report complete correct records, wrong accepted records, missing/partial records, extras/duplicates, holds and technical failures separately.
3. Count each failure class across calls. Keep a new generic step only if its measured complete-record gain justifies its time/questions/code. **After three unsuccessful fixes to a class, log it as open and continue with the remaining procedure.** Do not remove those cases from the denominator.
4. After each test append exactly three lines to `progress.md` in its test folder: what was tested, result, next step. Preserve exact requests/results and configuration fingerprints.
5. Freeze the chosen procedure and test untouched companies, calendars, units and transcript styles, including repeated values, references, cross-speaker conditions and negative controls. Add generic reordering/paraphrase/missing-context tests; never company-specific patches. Aim for roughly 300 independently reviewed records before a strong accuracy claim; sample size and correlated calls still limit conclusions.

**Pass:** every eligible reference fact is fully correct, with no wrong or duplicate accepted records. Legitimately absent optional fields may be empty; missing stated fields may not. A held expected fact is incomplete extraction. If no configuration passes, say so; do not substitute “all difficult items flagged” for success or guarantee unseen transcripts. Named-Driver lookup is a separate later test, not a loophole in blind discovery.

## 5. Evidence and open problems

EVIDENCE_TO_FINALIZE_AFTER_MAIN_PATH

Independent review, all 66 dispositions, source snapshots, prompts/results, timings and `progress.md`: `/tmp/decider_claude_review_20261115/`. Claude's supplied evidence: `/tmp/claude_decider_review_20261115/`. Temporary evidence can disappear; preserve a reviewed snapshot before implementation handoff. This document supplies the procedure independently.

References: [Decider model/API](https://huggingface.co/perplexity-ai/pplx-decider-v1.3), [pinned native Locate code](https://huggingface.co/perplexity-ai/pplx-decider-v1.3/blob/9c2ebb27470d3dec2ad7ab727727e40d142c7213/source/src/pplx_decider/locate.py), [TypeSafe candidate selection](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), [TypeSafe composition](https://docs.typesafe.ai/concepts/how-to-build-with-system-one), [pySBD offset API](https://github.com/nipunsadvilkar/pySBD/blob/v0.3.4/pysbd/segmenter.py).

## Hosted comparison reminder — separate future test

Pin hosted `pplx-decider-v1.3`, never `-latest`. Treat hosted and our modified local runtime as different configurations; revalidate on development data, never tune on the final test. Hosted precision/runtime parity was not established here.

The [official API contract](https://docs.perplexity.ai/docs/decisions/quickstart) documents grouped questions, at most 128 questions when Locate is present, a 256K input limit and default 10 requests/second plus model-specific token limits. It does not expose the local isolated/separate, temperature or Locate-cutoff controls. Keep web grounding off; extraction uses its own source. Hosted requests leave the Mac.

Do not automatically add spaces around punctuation. First compare original-text results on the boundary suite and real sources; any demonstrated transformation requires exact offset mapping and new validation. No hosted calls were made in this review.
