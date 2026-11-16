# Decider guidance extraction: next experiment

Updated 2026-11-15 (America/Toronto, EST). **Experimental; complete, accurate extraction has not been demonstrated.**

## Goal and limits

Extract management forecasts, their meaning and exact evidence using **local `pplx-decider-v1.3:8bit` plus code**. Correctness comes before speed. No stronger-model fallback, database writes, production Driver creation or changes to the rulebook.

Use one generic process: preserve context → find candidates → decide meaning → copy supporting words → check records. No company-specific branches, remembered answers, keyword-based eligibility, inferred ranges, automatic transcript corrections or repeated prompt-repair loops. A generic algorithm is not proof of reliable answers on every company; that requires untouched tests.

[DRIVER_RULES_Categorized.md](../DRIVER_RULES_Categorized.md) governs. Old GuidanceUpdates are comparison evidence, not the answer key or the new storage contract.

## 1. Prepare the source

Start with the agreed standard-format cohort. Read-only audit on 2026-11-15:

| Stored format | Count | Initial trial |
| --- | ---: | --- |
| Prepared remarks + structured Q&A; no alternative representation | 9,167 | Include |
| Structured Q&A, but missing prepared remarks or an additional representation | 305 | Defer |
| Q&A section and/or full text without structured exchanges | 136 | Defer |

All 9,472 structured-Q&A transcripts had sequential exchanges; all 9,320 prepared-remarks lists had nonempty blocks. This checks storage, not completeness against the publication. The 136 are not established to be older transcripts. Audit: `/tmp/transcript_numbering_audit_20261115/server_report.json`. Recheck cohort membership at selection time.

1. Read prepared remarks and Q&A through the existing decoding and `QUERY_3B` in `scripts/earnings/builders/warmup_cache.py`. Require `HAS_PREPARED_REMARKS` + `HAS_QA_EXCHANGE`, neither `HAS_QA_SECTION` nor `HAS_FULL_TEXT`. That query does not load alternative formats.
2. Preserve every block, speaker, question, answer and follow-up in source order. Number prepared blocks and complete exchanges `[P000]`, `[P001]`, etc. Missing answers stay missing; the audit found 4,867 question-only exchanges. Stored speaker roles are not proof of who made or confirmed a claim.
3. Keep an immutable original and a position map for added tags. The full decision context contains the company, publication/call identity, verified fiscal context and the entire transcript. Source text is evidence, not instructions. Dates, menus and metadata are context, not quoted source words.
4. For short Locate requests, use the whole prepared section or one complete Q&A exchange. Never cut at a fixed number of sentences or discard an analyst's question. Meaning questions use the full call. Cross-passage references remain eligible; missing context must not become a guessed field.

The other 441 formats require source preparation to be checked before admission. This is a format boundary, not permission for company-specific extraction rules.

## 2. Meaning to preserve

Shared definition, included unchanged in decision requests:

> Guidance is a specific financial or operating forecast, target or outlook stated or clearly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and qualifications that change a forecast's meaning. Exclude actual results, merely recalled old forecasts, analyst-only estimates, vague optimism and boilerplate. A hypothetical illustration is not a committed forecast. Resolve references using the entire call; do not invent missing facts.

- **Discovery stays blind to existing names** (1.14). Measure wording may come from anywhere in this source, including a question when management supports its meaning (1.26). Raw source wording is not a canonical Driver name. Catalog matching follows discovery and the independent checks in 2.40, 2.43 and 8.2; no company-only catalog or alias map replaces them. A named-Driver history search is a separate permitted task, not evidence that blind discovery works.
- A specific forecast of tax, interest or another operating measure may be its own fact and also an explicitly stated assumption of another forecast. Do not turn actuals, causes or hypothetical figures into guidance. Conditions contain assumptions, not guessed causes (4.8).
- A standing target is annual only if the source establishes that period. Explicit “going forward” can use `undefined`; missing period is unresolved, not automatically long-term (3.37–3.41).
- Keep every meaning-changing qualification. One continuous source quote may span speakers; 1.24 does not impose a one-speaker limit. Include the question when needed. If one lawful quote cannot prove the fact, hold/count it; do not join fragments with invented ellipses.
- Preserve stated bounds and approximations. “High end” does not automatically equal an exact endpoint. Forecast growth is the guidance value; `change` means an explicitly stated revision to that forecast (4.6). Never silently repair a transcription such as a misheard unit.

## 3. Algorithm and prompts

`P` identifies a passage; `V` a candidate occurrence; `M` source wording for a measure. Put tags in the model-visible text. Character offsets stay in code, not prompts. Repeated identical words still need distinct tags, including measure occurrences.

### A. Identify relevant passages

Batch one `noul` per numbered passage, with the full call:

> Under the supplied definition, does [P] state, reaffirm, withdraw or qualify management guidance? Use the whole transcript as context. An analyst's question alone is not management confirmation.

Save all probabilities. First evaluate this against a complete, independently checked answer key; do not assume the existing records cover every positive passage. Start the development comparison at `passage_cutoff = 0.25`, explicitly provisional. Keep whole exchanges; when prepared remarks are relevant, retain the whole prepared section for Locate. Do not add a sentence filter.

Calibrate and freeze the cutoff before the untouched test. A positive passage below the cutoff is a discovery miss, even when later stages would have extracted it correctly. No universal cutoff is established.

### B. Find literal candidates without judging eligibility

**Printed digits: code, not another model search.** Enumerate source tokens containing digits, keeping punctuation and exact positions:

```python
import re

numeric_seeds = [
    (m.start(), m.end(), m.group())
    for m in re.finditer(r"\S+", source_text)
    if any(c.isdecimal() for c in m.group())
]
```

This only supplies starting locations. It does not parse quantities, classify forecasts, remove signs/units, decide that two numbers form a range, or exclude dates. Run it on original source content, not added tags or metadata. Keep question occurrences too: management can confirm a number stated only there. Earlier/actual amounts remain available as reference evidence, even when they produce no new fact.

**Words and measures: Locate on complete passages**, with these fixed labels. Search for word forecasts in retained passages. Collect measure wording throughout the source, including other passages: a definition or antecedent can occur outside a guidance passage. Preserve exact request grouping.

| Key | `instructions` |
| --- | --- |
| `word_forecasts` | `Forecast wording expressed in words, including qualitative expectations, relative bounds, reaffirmations and withdrawals` |
| `measure_wording` | `Financial or operating measures` |

The first label also needs testing on numbers written as words. It is deliberately not seeded with the troublesome sentences from our development calls. Its recall is unproven. A passage containing several forecasts can lose one even when another was found; “some output” is not a coverage check.

Assign `V` tags to numeric seeds and word-forecast spans, `M` tags to measure spans. Deduplicate identical offsets only. Do not keep only the longest overlapping span or merge equal strings. A measure span may include surrounding words; it must identify what is measured, not merely an amount/unit. Source measure discovery is not an eligibility gate: no usable `M` means an unresolved candidate, not “no guidance.”

Check each `M` once with `noul` in its complete source passage:

> Does the source phrase at [M] name a financial or operating measure or business quantity, rather than merely state a number, unit, date or period? The phrase may include an amount, but it must also identify what is being measured.

Keep its score and rejected/uncertain candidates for evaluation. A validity miss is still a discovery failure if it removes a real measure.

### C. Decide meaning with the full call

Batch independent questions; dependent answers belong in the next request. Use `choice` descriptions, not unexplained abbreviations. No answer-key labels, values or periods may enter a request.

**Role**, for each `V`:

> What role does the occurrence [V] have in this transcript? Distinguish management's current forecast from actuals and earlier forecasts; an analyst's figure needs clear management support.

Choices: current forecast level; current forecast growth/change; size of a revision; earlier forecast only; actual result; unconfirmed analyst figure; hypothetical illustration; qualification of current guidance; reaffirmation/withdrawal; unclear/other. A reference amount may support another candidate without becoming another current forecast.

**Measure association**, using tagged source occurrences, not existing Driver names:

> Does [M] identify what is being measured, and does [V] forecast or qualify that same measure for the same business scope, as management states or clearly confirms? Answer no if [M] only gives a number, unit or period, or concerns a different business scope. Use the whole transcript as context.

Ask associations for the retained source measure candidates; do not prune them by matching words, distance or a company catalog. Use the local passage to check whether an `M` actually names a measure, and the full call to check its association. Neither check proves the other. Multiple supported measures require separate proposals; do not force a single-choice winner. Unclear associations are held. The same model checking its own answer is a consistency check, not independent validation. Measure the resulting question count before claiming speed; a cheaper shortlist must prove that it preserves recall.

For each supported `(V, M)`, ask these fields with the full call. Prefix every question with `For [V], about [M],`:

| Question | Choices/data supplied |
| --- | --- |
| `what target period does management mean?` | Concrete periods with dates from the verified fiscal calendar; explicit short/medium/long/undefined horizon; other stated period; several; unclear. |
| `what unit does the source establish?` | Rule 3.28's units, with descriptions; another official currency/registry unit; unknown. |
| `what scale applies to the printed quantity before storage conversion?` | 1; thousand; million; billion; other stated scale; unclear. Preserve source scale evidence. |
| `what numeric shape is stated?` | Point; range; floor; ceiling; numberless; several distinct forecasts; unclear. |
| `what movement is explicitly stated?` | Introduced; raised; lowered; reaffirmed; withdrawn; not stated; unclear. `not stated` stores `unknown` (4.4). |
| `whose measure is this?` | Source company; another source-identified subject; shared; unclear. Resolve the subject before choosing its fiscal calendar or slice menu; no automatic source-owner inheritance. |
| `which business scope does this describe?` | Whole company; applicable earlier company slice values; new stated slice; several; unclear. Preserve the slice kind; this is not only a segment menu. |
| `does the forecast describe a duration or an instant?` | Duration; instant; unclear. |

Menus are source/context data, never company-specific rules:

- Fiscal options use the call's fiscal framing and a verified calendar, not call date plus year-end month alone. Include adjacent fiscal years, quarters/halves and source-stated periods; an unlisted period stays `other stated`, not the nearest option. Exact source dates beat fiscal shorthand. Do not use month arithmetic for 52/53-week or changed calendars. A missing calendar is unresolved. Generic horizons require explicit wording; `undefined` is not a fallback.
- Units include `percent`, `percent_yoy`, `percent_sequential`, percentage points, basis points, monetary totals/per-unit amounts, counts, multiples and official-list units under 3.28/3.54. Do not infer growth basis from the metric name or scale from number size. Apply scale exactly once; do not multiply twice because a stored unit already includes a scale. Unsupported menus must not force a plausible substitute.
- Slice values come from the company's earlier public filings and already used values under 3.17–3.18. No hand-built Paycor/Cintas spelling map; multiple slice parts remain possible. New source wording is preserved, not automatically merged.
- A choice has at most 255 options. Do not truncate a catalog/menu silently. Unsupported menu sizes are explicit trial failures until an existing compliant lookup path is established.

Also ask one `noul` for each open-text field:

> Does management explicitly attach {field} to [V], about [M], including a clearly applicable shared statement elsewhere in this call? Do not borrow another forecast's details or generic forward-looking boilerplate.

`field`: an assumption/exclusion/dependency; a measurement qualifier; a stated revision amount; a stated comparison/baseline. These checks expose some empty Locate results; a wrong “no” or a partial returned span can still lose information.

### D. Copy the supporting text

Use Locate on the whole prepared section or complete Q&A, adding the original passage containing the chosen `M` when needed. Keep tags mapped to the immutable source. For each applicable field:

> For [V], about [M], locate {field}. Copy only applicable source text, including references that establish its meaning. Exclude unrelated actuals, earlier forecasts and other measures.

| `{field}` | Required handling |
| --- | --- |
| `the stated forecast expression and its point/lower and upper values` | Preserve bounds/approximation and references. Code may reuse an already established exact numeric span; it must not infer endpoints from the count of numbers. |
| `the expectation expressed in words` | Keep qualitative values, relative bounds, reaffirmations and withdrawals; no invented numeric translation. |
| `the target period wording` | Supports the chosen period; copy explicit dates for `other stated`. No source-supported period means unresolved. |
| `the applicable unit and scale evidence` | Choices identify meaning but do not replace evidence required by 3.29. A sound quantity can retain `unknown` where the rule permits it; count it. |
| `the subject, business scope and measurement qualifiers` | Retain all qualifiers, including organic, adjusted, diluted and exclusions. Empty measurement tags do not mean GAAP. |
| `all applicable assumptions, exclusions and dependencies` | Required when present; distinguish them from stated causes. An empty or incomplete result does not prove absence. |
| `the explicitly stated revision amount and its unit` | Not an inferred difference between old and new guidance. |
| `the explicitly stated comparison value, unit and baseline` | Keep distinct from the current forecast and its revision. |

Initially test field copying even where the presence answer is “no”; this checks whether gating would hide fields. Only skip confidently absent optional fields after that behavior passes development checks. If a needed field refers outside the working passage, test the same targeted Locate against the full call once; no fixed-neighbour window, guessed attachment or open-ended retry. Failure remains unresolved.

Several values/measures/periods do not authorize a Cartesian product. Each proposed association must be source-supported. If the model cannot separate them, hold/count the affected proposals. “Several” is not a complete extraction.

### E. Assemble and validate

- Verify every span against the original content and its position map. Tags, model descriptions and menu text are never evidence.
- Normalize only established values/units/periods. Preserve signs, strict bounds and scale. Reuse compatible exact-number and calendar helpers; do not feed arbitrary ranges/percent strings to the legacy single-number parser. Inspect/test the native path before adding any missing lexical handling. Numerical parsing must not decide financial meaning.
- Build one continuous quote covering the fact and all required support, including management confirmation and qualifications. No separate “Evidence Locate” is needed. Taking a substring proves copying, not correct attribution or causation.
- Deduplicate only after full meaning, subject, period, scope and measurement are established. Do not merge equal numbers or discard conflicting same-slot proposals.
- Keep all answers/probabilities and outcomes: proposal, no eligible fact, unresolved, technical/oversize failure. Flag uncertain decisions, missing required fields, yes-with-empty copying, unmatched source words, conflicts and guidance passages with no proposal. These flags cannot certify that nothing was missed.
- Start development flagging at top-choice probability `0.90`, explicitly uncalibrated. Confidently absent means `P(no) >= 0.90`; other absence claims remain uncertain. Save raw probabilities and calibrate on checked development data, not the untouched test. Do not force an answer to reduce the flag count.
- No old Guidance writer, graph writes, inferred Driver aliases or canonical name creation in this trial. Proposals retain source measure evidence; production identity checks remain required separately.

## 4. Execution and test order

```python
from config import local_llm as L
result = L.decide(state, questions, mode="isolated", timeout=1800)
```

Freeze exact prompts, option descriptions/order, grouping, source rendering, mode, temperature setting, model/weight revision, conversion and runtime hashes. Our punctuation-modified Locate is not identical to the upstream implementation. The currently copied guide does not establish the running weights/runtime hashes; capture them before a reproducible benchmark.

- Local sequence limit: 32,768 tokens including protocol/questions. Use actual tokenizer accounting. Keep at most 128 questions total in a request containing Locate. Repeat unchanged context when batching; never silently truncate. An oversized source remains incomplete in this trial.
- Locate considers only the top 128 start/end positions per label and spans up to 128 tokens; this is not a guarantee of 128 complete entities. Its returned probability cutoff is 0.5; `decide()` exposes no cutoff control. Do not change the runtime for this experiment.
- `isolated` grouping can change answers. Pin groups and evaluate the actual configuration. Do not run a costly full `separate` sweep by default; use a matched diagnostic only for a demonstrated grouping failure. Do not assume the Mac's Locate modes match upstream without checking its source.
- Locate and decision questions use separate passes even in one request. No assumed cross-request cache or CUDA speedup. Record tokens, sequences, errors and elapsed time; separate cold-load/queue time from warm inference. No complete-run speed estimate is established.

Run in this order:

1. **Fix the answer key first.** Read each complete source in two independent review passes. Resolve disagreements against the rulebook. The 54 saved records contain real inconsistencies and omissions; counts such as “25 defective” or “10 missing” remain unverified until a row-by-row key exists. Never alter the database as part of this labeling.
2. **Check A on all six development calls.** Score complete passage recall, including qualifications, analyst confirmation and facts absent from the database. Compare the old measured speaker-turn setup with the proposed complete-exchange setup without presenting changed wording/context as a controlled comparison.
3. **Check B–E on the labeled positive passages, then the actual selected passages including negatives.** Count numeric/word-only candidate misses, wrong associations and every required-field error. An accurate passage flag is not an extracted record. No need to run every expensive field question over known negative passages merely to score A.
4. **Freeze before testing new companies/calls.** Select independent unseen sources covering financial/nonfinancial forecasts, different calendars, units and transcript styles. Test reordering, repeated values, paraphrases, missing context and ambiguous statements with real positive/negative controls. Do not add a hard-case phrase to a prompt and then count that same example as generalization.
5. **Run the complete pipeline on the untouched set.** Report correct complete records, missed facts, accepted-wrong records, extra/duplicate records, unresolved facts and technical failures separately. Check qualifiers by meaning, not only span overlap. Held expected facts remain incomplete extraction; rejecting everything is not success.

Target approximately 300 independently checked records across multiple unseen companies/calls before making a strong accuracy claim; count clustering and selection effects. Zero observed errors does not prove zero future errors. A changed prompt, group, threshold, runtime or model is a new configuration requiring validation, not automatic threshold retuning to fit the test.

**Pass:** every eligible reference fact is present with correct required fields and meaning; no accepted wrong/duplicate records. Legitimately absent optional fields may be empty. Select the fastest measured configuration that meets this test. If none does, report the remaining failure; do not call a flagged or guessed answer complete.

## 5. What this review established

- Claude's 66 findings reviewed an earlier summary, not the later detailed strategy. The boundary suite reproduced 56/60 expected short-text spans, with four name misses; it does not measure financial-record extraction.
- Using Claude's exact numeric label on Paychex's full prepared section still missed the new EPS range and a revenue forecast. Removing the second label recovered the revenue forecast but not the EPS range; different concrete labels recovered some values while losing others. This is why printed-number seeds now come directly from code, without sentence retries.
- Tags distinguished Paychex's actual, current and earlier occurrences of `11%`. Source measure occurrences need tags too; identical text-only association questions gave identical answers despite different source scopes.
- Concrete unit/period choices recovered the intended top answers for the two difficult Cintas examples. Confidence varied; this is not a calibrated acceptance result. Short-passage copying recovered additional fields, while measure identity/qualifier completeness remained problematic.
- A generic phrase-discovery label missed the ERP qualification that an example-containing label recovered. The latter explicitly included the target wording. That is development evidence, not proof of generic discovery. Word-only recall remains a required test.
- Live read-only checks matched all six saved source texts and all 54 saved record properties. Source-grounded counterexamples verify that two digits need not be a range, management can confirm analyst wording, cross-speaker qualifications are allowed, and existing names must remain hidden during discovery.

**Still unproved:** end-to-end completeness, reliable blind measure identity, complete word-only/qualification extraction, field gating, calendar/unit coverage, calibrated thresholds, performance on untouched companies and full-run speed. This document is the next experiment, not a claim that those tests passed.

Review inputs: `/tmp/claude_decider_review_20261115/`. Requests, responses, independent recomputation, graph comparison, helper checks and review notes: `/tmp/decider_claude_review_20261115/`. These temporary artifacts may disappear; the procedure above must stand without them.

References: [Decider model/API](https://huggingface.co/perplexity-ai/pplx-decider-v1.3), [pinned Locate code](https://huggingface.co/perplexity-ai/pplx-decider-v1.3/blob/9c2ebb27470d3dec2ad7ab727727e40d142c7213/source/src/pplx_decider/locate.py), [TypeSafe: code enumerates values, model judges meaning](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), [TypeSafe composition](https://docs.typesafe.ai/concepts/how-to-build-with-system-one). The Cintas calendar diagnostic used its [pre-call SEC filing index](https://www.sec.gov/Archives/edgar/data/723254/000072325426000002/0000723254-26-000002-index.htm); that does not validate other fiscal calendars.

**Handoff:** keep the source snapshots, separately checked answer key, exact requests, model/runtime fingerprints, raw scores, proposals, all failure categories and timings together. Display times in America/Toronto with EST/EDT. Only this strategy is revised; implementation and database remain unchanged.
