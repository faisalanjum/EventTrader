# Decider guidance extraction — next experiment

Reviewed 2026-11-15 (America/Toronto, EST). **Experimental: a complete, accurate extractor has not passed.** The aim is complete, correct records with the least code and model work, using local `pplx-decider-v1.3:8bit` only. No stronger-model fallback, database writes or changes to the rulebook.

## Decision

**Keep the whole call as context; identify relevant source sentences; let code supply printed-number locations; use Decider questions to establish meaning and copy evidence.** A failed span search must remain visible, not turn into “nothing was said.”

This replaces both measure-first discovery and broad “find all worded forecasts” Locate as gates. Both missed real guidance in this review. It also removes the proposed all-values × all-measure-names comparison, existing-name menus during discovery, longest-span deletion, sentence retries, and blanket runtime/threshold changes.

This is the next procedure to test, not evidence that its untested stages work. [DRIVER_RULES_Categorized.md](../DRIVER_RULES_Categorized.md) governs. Old GuidanceUpdates are comparison evidence, not the answer key or the new writing contract.

## 1. Prepare once

Start with the agreed standard-format cohort:

| Audited storage, 2026-11-15 | Count | Trial |
| --- | ---: | --- |
| Prepared remarks + structured Q&A, with no alternative representation | 9,167 | Include |
| Structured Q&A, but missing prepared remarks or also having another representation | 305 | Defer |
| Q&A section/full text without structured exchanges | 136 | Defer |

All 9,472 structured-Q&A sources had ordered exchanges; all 9,320 prepared-remarks lists had nonempty blocks. These checks establish storage structure, not publication completeness. The 136 are not established to be older calls. Recheck membership when selecting sources. Audit: `/tmp/transcript_numbering_audit_20261115/server_report.json`.

1. Reuse read-only `QUERY_3B` and decoding in `scripts/earnings/builders/warmup_cache.py`. Require `HAS_PREPARED_REMARKS` + `HAS_QA_EXCHANGE`, neither `HAS_QA_SECTION` nor `HAS_FULL_TEXT`; this query does not load alternative formats.
2. Preserve all prepared blocks, questions, answers, follow-ups and speaker information, in order. Number existing prepared blocks and complete exchanges `[P000]`, etc. Missing answers stay missing: the earlier audit counted 4,867 question-only exchanges. Stored roles alone do not prove who stated a claim.
3. Number sentences `[S0000]`, etc., using native `pysbd==0.3.4`, `Segmenter(language="en", clean=False, char_span=True)`. This initial trial is English. Keep exact original offsets; assert nonoverlap, exact substring matches and coverage of every non-whitespace character. A failed assertion holds the source; do not add a company-specific splitting fix. The library has general language rules; no company or financial exceptions are added. Sentence boundaries identify targets; they never limit the context or define one fact per sentence.
4. Keep the immutable original and a map for every inserted tag. Render the **entire** call, source identity, verified fiscal context and the definition below. Added tags, menus and metadata are not quote evidence. Treat source content as data, not instructions. Never silently truncate an oversized call.

Shared definition, unchanged across companies:

> Guidance is a specific financial or operating forecast, target or outlook stated or clearly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and qualifications that change a forecast's meaning. Exclude actual results, merely recalled old forecasts, analyst-only estimates, vague optimism and boilerplate. A hypothetical illustration is not a committed forecast. Resolve references using the entire call; do not invent missing facts.

## 2. Algorithm

`S` identifies a source sentence, `V` a candidate occurrence, and `M` copied wording naming a measure. Put their tags in the model-visible text; character positions stay in code. Equal text at different positions remains distinct. Independent questions share a batch; dependent questions wait for the earlier answer. Use stable source/sentence/candidate/field order and save exact batch membership.

### A. Find relevant sentences with the full call

One `noul` per sentence, using this exact template:

> Under the supplied definition, does sentence [S] state or qualify management guidance elsewhere in this transcript? Use the whole call to resolve references; an analyst's question needs management confirmation.

Run this over **every sentence**. Do not first filter by passage, keyword, number or existing Driver. This replaces the earlier passage gate; it is not another gate stacked on top. Do not make one isolated request per sentence.

Save every probability. For the first development run, retain `P(yes) >= 0.25`; this is a conservative experimental setting, **not a validated cutoff**. Score recall against the independent answer key, including statements below the cutoff. Freeze any later choice using development data before testing unseen calls.

For copying fields, keep the whole prepared section or complete Q&A containing the retained sentence. Meaning questions always receive the full call, including unselected sentences and other speakers.

### B. Supply candidates without a fragile value-discovery gate

Code enumerates printed-number starting points once, on original source text:

```python
import re

numeric_seeds = [
    (m.start(), m.end(), m.group())
    for m in re.finditer(r"\S+", source_text)
    if any(c.isdecimal() for c in m.group())
]
```

These are source tokens, not parsed financial values. Keep punctuation, signs, dates, question text and repeated occurrences. Do not infer that two numbers form a range, choose only the longest overlap, or filter amounts by who spoke.

For each retained `S`, start with its numeric seeds **and the whole sentence as a worded/qualifying candidate**, each with a distinct `V` tag. The sentence candidate preserves forecasts written in words, numbers spelled out, references, reaffirmations and withdrawals. It is an extraction target, not automatically one fact or a valid `value_text`.

Locate may refine an anchor into distinct forecast expressions, with the complete local passage:

> For [V], copy the distinct forecast expressions stated or qualified here, including applicable values, limiting words and references. Keep different expressions separate.

Keep the original anchor if copying fails. Exact-offset duplicates may be removed; partial overlaps remain until their meaning is established. A relevant sentence with unresolved content remains incomplete even if another fact was extracted from it.

### C. Establish whose forecast and what it measures

For each `V`, use Locate in the complete local passage:

> For [V], copy the source wording naming the financial or operating measure or business quantity it refers to. Copy what is measured, not a bare amount, unit, date or period. Include antecedent wording when the target uses a reference.

Tag returned occurrences `M`. If the required antecedent is absent or unresolved locally, run the same targeted Locate with the full call once. No fixed neighbour window or repeated prompt repair. No usable name means unresolved, not no guidance.

Validate each proposed `M` with two separate `noul` questions, with the full call:

> Does the source phrase at [M] name a financial or operating measure or business quantity, rather than merely state a number, unit, date or period? The phrase may include an amount, but it must also identify what is being measured.

> Does [V] forecast or qualify the measure at [M], for that same subject and business scope, as management states or clearly confirms in this call?

Neither check proves the other. For this first experiment, both checks need `P(yes) >= 0.5` to advance; scores below 0.90 remain review flags. These thresholds are not validated. Multiple supported measures are allowed; missing or ambiguous associations are held. Whole-call targeted copying may still miss names; it has not passed a complete record test. This is a same-model consistency check, not independent validation.

Discovery reads **no existing guidance/Driver names** (1.14). An analyst's wording can identify the measure only with management support (1.26). Raw source wording is not a canonical Driver name. Later naming/matching remains global and independently checked under 2.40, 2.43 and 8.2; no alias list or company-only catalog is introduced. A named-Driver history search is a separate task.

### D. Select fields and copy their evidence

Use `choice` with meaningful descriptions, plus `unclear`; never force a plausible answer. Every question identifies `[V]` and `[M]`. Resolve the subject before using its calendar or business-scope menu.

| Question: `For [V], about [M], …` | Choices / required interpretation |
| --- | --- |
| `what role does this occurrence have?` | Current forecast point, lower endpoint, upper endpoint, floor, ceiling, centre, tolerance, relative bound, worded forecast, qualification, reaffirmation, withdrawal; revision amount; earlier forecast; actual; unconfirmed analyst figure; hypothetical; several; other; unclear. Earlier/actual amounts may support another forecast without becoming new guidance. |
| `whose measure is this?` | Source company; another source-identified subject; shared; unclear. Copy another subject's identity before using its context. |
| `what target period does management mean?` | Concrete verified fiscal **and calendar** periods with dates; explicit short/medium/long/undefined horizon; other stated period; several; unclear. |
| `what unit and scale does the source establish?` | Ask unit and scale separately. Units follow 3.28/3.54; scales: 1, thousand, million, billion, other stated, unclear. Retain source evidence. |
| `what sign does the source establish for this amount?` | Positive; negative; zero; several; not numeric; unclear. Respect the quantity's meaning, not only a printed minus (3.34). |
| `what movement is explicitly stated?` | Introduced; raised; lowered; reaffirmed; withdrawn; not stated; unclear. `not stated` stores `unknown` (4.4). |
| `which business scope does this describe?` | Whole company; verified earlier company slice values; new stated slice; several; unclear. Keep the slice kind, not just a segment name. |
| `does the forecast measure a duration or an instant?` | Duration; instant; unclear. |

Menu rules:

- Put reusable menu definitions and fiscal dates once in the shared state; use readable choice keys and brief descriptions. Pin that rendering and test it rather than repeating long calendars in every question or assuming equivalent scores.

- A fiscal year-end month does not establish a 52/53-week calendar or the company's fiscal-year naming convention. Verify both; exact source dates win. Calendar 2025 must not become FY2025. Include source-stated other dates/horizons; an absent option is not permission to select the nearest period. An unverified period is held.
- Units include the rulebook's currencies, percentage levels, growth bases, points/basis points, counts, multiples and official-list units. Use its currency convention (9.1); otherwise no currency/scale inference from company or magnitude. Growth without an evidenced comparison basis remains `unknown`, counted (3.33). Apply exact scale conversion once.
- Scope values come from earlier public company evidence (3.17–3.18). New wording remains explicit. No spelling fixes, company-specific aliases or preset metric lists. Native choice limit is 255; do not silently truncate a menu.

Copy each field in the complete local passage, using:

> For [V], about [M], locate {field}, including applicable references. Return only supporting source words; do not borrow another forecast's details.

`field` is each of: forecast values/expression and bounds; target-period wording; unit/scale evidence; subject/business scope; measurement qualifiers; assumptions/exclusions/dependencies; explicitly stated revision amount/unit; explicitly stated comparison value/unit/baseline. Return separate support spans without pretending they are a continuous quote.

For the last four optional groups—measurement qualifiers, conditions, revision, comparison—also ask `noul` with the full call:

> Does management explicitly attach {field} to [V], about [M], including an applicable shared statement elsewhere in this call? Exclude generic boilerplate and unrelated forecasts.

Initially run copying even after “no”, to measure whether that answer would lose fields. Only introduce optional-field skipping after validation. Yes-with-empty copying is unresolved; a nonempty result can still be incomplete. When local copying cannot resolve necessary support, use the same targeted full-call Locate once. Unresolved meaning is never guessed.

Several numbers/measures/periods require supported associations, not list zipping or a Cartesian product. `Several` is not a finished record. One anchor may be resolved by several individually supported proposals; never assume their presence exhausts it. Inseparable expected facts stay held and count against completeness.

### E. Assemble and check

- Prove every copied span equals the immutable original; remove only inserted tags through the position map. Code builds **one continuous quote** covering the fact, attribution and every meaning-changing qualifier, including an analyst's question when needed. No separate Evidence Locate or joined-fragment quote format.
- Normalize only established numbers/units/periods. Do not calculate an unstated endpoint, midpoint, revision or implied forecast; exact rescaling is permitted. Preserve approximation and relative-bound wording. A centre plus tolerance is not two range endpoints: retain both stated quantities in the proposal; do not invent a storage encoding or derived bounds.
- Apply the rulebook’s fact-type boundaries, including 1.23 and 10.5; unsupported representations are skipped/countable, not silently forced into guidance. Broad reaffirmations/withdrawals need proven prior scope under 3.35 and 4.18–4.21; the reader does not invent missing prior names or values.
- Preserve every qualifier (3.26). Forecast growth is a guidance value; `change` is only an explicit revision (4.6). Conditions are assumptions, not inferred causes (4.8). `value_text` follows 4.7, including its length/number rules; an entire retained sentence is not automatically valid for it.
- Deduplicate only after complete meaning, subject, measure, period, scope, measurement and conditions are established. Equal strings/numbers alone do not prove a duplicate. Conflicts remain visible.
- Keep proposals, raw spans, all probabilities, timing, and outcomes: complete proposal; no eligible fact; unresolved; technical/oversize failure. Track every retained sentence and numeric seed to its disposition. This accounts for processed input, not proof that every meaning was found.
- Start development review flags at selected-answer probability below `0.90` (use `probabilities`, not the API’s differently defined `confidence` field), explicitly uncalibrated; do not use confidence alone to declare a correct record. Record absent, unknown and unsupported fields separately. Held expected facts are incomplete extraction, not successes.
- No legacy Guidance writer or canonical Driver creation in this experiment. Proposed facts need the existing independent core checks before production writing.

## 3. Three policy clarifications — no rulebook change

1. **Conditions elsewhere:** attach only when the source establishes applicability. The exact continuous quote may span speakers; 1.24 does not say one speaker. If one quote cannot prove the meaning, hold/count the fact. No new separate-condition-quote schema.
2. **Numeric assumptions:** an explicitly forecast tax rate/interest expense can be its own guidance fact and an assumption supporting another forecast. Apply the same eligibility, period and attribution rules; do not turn every assumed number or actual into guidance.
3. **Standing targets:** follow the stated horizon. This fiscal year → that year; “going forward” → explicitly undefined, not automatically long-term (3.40). Two records require two established target periods. Never add interpretation to conditions.

## 4. Native capabilities, runtime and test order

```python
from config import local_llm as L
result = L.decide(state, questions, mode="isolated", timeout=1800)
```

Pin the exact prompt/options/grouping, rendering, source hashes, model, weights revision, conversion and runtime code. Our local punctuation-modified Locate differs from upstream. The copied Mac guide does not establish the running code/weights hashes; capture them before a reproducible benchmark.

- Local context limit: 32,768 tokens including protocol/questions. Use actual runtime/tokenizer accounting and stable batches; repeat the full state without truncation. At most 128 questions **total** in any request containing Locate. Oversized sources remain incomplete in this trial.
- Locate and decision questions require separate passes even in one request. Locate proposes at most 128 start/end positions per label and spans of at most 128 tokens; this is not a completeness guarantee. Native returned probability cutoff is 0.5 after label-relative scoring; `decide()` exposes no cutoff setting. No runtime modification now.
- Grouping can change answers. Freeze the actual batches. Do not run an expensive blanket `separate` comparison or assume cross-request caching/CUDA acceleration. Record warm/cold time, tokens, passes and errors; complete-run speed remains unmeasured.
- Library check: native pySBD offset output preserved all tested source characters on nine source snapshots; this is not proof of perfect linguistic boundaries. Installed only in the temporary test directory. Legacy `guidance_ids.py` does not parse general percentage/range text; `fiscal_math.py` supplies month-based dates, not verified week calendars; exact-number helpers do not establish financial meaning. Reuse compatible paths, test their real gaps, and do not build a second semantic parser.

Test sequence:

1. **Establish the answer key.** Read complete sources in two independent review passes against the rulebook. Correct legacy omissions/inconsistencies; keep expected answers out of prompts. The six CTAS/PAYX calls and newly probed MU/FDX/OLLI calls are now development material, not untouched final tests.
2. **Check selection first**, including qualifications, worded forecasts and negative sentences. Measure every missed reference sentence and additional flags. Compare sentence and passage selection on identical checked sources before making a speed/accuracy claim; source selection success does not prove field extraction.
3. **Check B–E on independently identified positive sentences, then on actual selections including negatives.** This separates field failures from selection failures. No need to run all expensive fields on known negative text just to score A. Test repeated values, pronouns, analyst confirmations, multiple forecasts, conditions, scales/signs, calendar conventions, corrupt source text and legitimate unknowns.
4. **Freeze and test whole calls from unseen companies.** Cover different units/calendars/styles; include generic reordering, repetition, paraphrase and missing-context tests with positive controls. Report complete correct facts, missing facts, accepted-wrong facts, extras/duplicates, unresolved facts and technical failures separately. Qualifier correctness is about meaning, not just overlapping words.
5. **Then optimize.** Keep only changes whose complete-record results preserve coverage and correctness. Test the separate named-Driver history task with previously known identities; report it separately from blind discovery. Review approximately 300 independently checked records across multiple unseen calls before a strong accuracy claim; clustered/selective samples do not establish a universal error rate. Changing configuration requires a new test, not retuning until the test passes.

**Pass:** every eligible reference fact is fully correct, with no accepted wrong or duplicate records. Legitimately absent fields may be empty; omitted supported fields may not. Rejecting everything is not a pass. If this procedure fails, record the precise generic failure; do not add company-specific rules or call a flagged item complete.

## 5. Evidence and limits

EVIDENCE_RESULTS_PENDING

Review inputs: `/tmp/claude_decider_review_20261115/`. Independent checks, all 66 finding dispositions, source snapshots, exact requests/results and timings: `/tmp/decider_claude_review_20261115/`. Temporary files may disappear; the procedure above stands independently of them. Preserve a reviewed evidence snapshot before a production handoff.

References: [Decider model/API](https://huggingface.co/perplexity-ai/pplx-decider-v1.3), [pinned Locate implementation](https://huggingface.co/perplexity-ai/pplx-decider-v1.3/blob/9c2ebb27470d3dec2ad7ab727727e40d142c7213/source/src/pplx_decider/locate.py), [TypeSafe: code supplies candidates, model judges meaning](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), [TypeSafe composition](https://docs.typesafe.ai/concepts/how-to-build-with-system-one), [pySBD 0.3.4 native offset API](https://github.com/nipunsadvilkar/pySBD/blob/v0.3.4/pysbd/segmenter.py).

**Handoff:** preserve sources, independent expected answers, exact requests/settings/fingerprints, raw scores, proposals, all failure counts and timings. Report times in America/Toronto with EST/EDT. This review changes the strategy only; runtime, production code and database remain unchanged.

## Hosted comparison reminder — separate future test

The API reminder added during this review is retained here with its intent clarified. Pin `pplx-decider-v1.3`, not `-latest`, and treat hosted versus our modified local runtime as different configurations. Revalidate thresholds on development data; never retune on the final test or assume differences are only rounding.

The [official API contract](https://docs.perplexity.ai/docs/decisions/quickstart) documents grouped questions, at most 128 questions when Locate is present, a 256K input limit, and default limits of 10 requests/second plus model-specific token limits. It does not expose the local `isolated`/`separate`, temperature or Locate-cutoff controls. Keep web grounding off: this extraction must use its own source. Hosted requests leave the Mac.

Do not automatically insert spaces around punctuation. First compare original-text results on the saved boundary suite and real calls; any demonstrated text transformation needs exact offset mapping and fresh validation. Hosted weights/precision and implementation parity were not established by this local review. No hosted calls were made.
