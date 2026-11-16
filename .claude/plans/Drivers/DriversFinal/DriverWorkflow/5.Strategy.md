# Decider extraction strategy

Updated 2026-11-15 (America/Toronto, EST). **Proposed experiment; not a proven extractor.**

## Goal and boundaries

Extract every eligible management forecast with correct fields, meaning and exact evidence, using **the local Decider plus existing code**. Target: 100% completeness and accuracy on independently checked, unseen sources; no guarantee for future documents. Correctness precedes speed.

- Model: `pplx-decider-v1.3:8bit`, through `config/local_llm.py::decide()`. No Opus, Qwen, Jev or hosted-model fallback in this experiment.
- Code handles source preparation, copying, existing normalization and checks. The Decider handles meaning. No company-specific prompts, guidance keyword filters, custom number-hunting rules, word-by-word fallback or repeated repair loop.
- Scope: **transcript guidance extraction**. SEC filings, news, other fact types, production Driver creation and database writes are not covered by this trial.
- [DRIVER_RULES_Categorized.md](../DRIVER_RULES_Categorized.md) governs meaning and storage. Existing GuidanceUpdates are comparison evidence, not exhaustive truth. This trial changes no graph rules.

```text
Full transcript → relevant complete passages → forecast candidates
                → individual fields → checked record proposals
```

Dependent stages need earlier answers; independent questions share a batch. Stages are not necessarily single requests.

## 1. Prepare once

**Start with the standard format only.** Read-only audit of all 9,608 transcripts on 2026-11-15 (EST):

| Stored format | Transcripts | First trial |
| --- | ---: | --- |
| Prepared remarks and structured Q&A, with no alternative representation | 9,167 | Include |
| Structured Q&A, but no separate prepared remarks or an additional representation | 305 | Defer |
| No structured Q&A; saved as a Q&A section and/or full text | 136 | Defer |

All **9,472** structured-Q&A transcripts have valid, sequentially ordered exchanges; all **9,320** saved prepared-remarks lists contain nonempty text blocks. This verifies storage structure, **not completeness against the original publication**. The 136 alternative-format transcripts are **not confirmed to be older**. Audit queries/results: `/tmp/transcript_numbering_audit_20261115/server_report.json`.

The first trial requires `HAS_PREPARED_REMARKS` and `HAS_QA_EXCHANGE`, with neither `HAS_QA_SECTION` nor `HAS_FULL_TEXT`. Defer the other **441** transcripts; do not add alternative-format handling in this trial. Recheck membership when selecting sources; these counts describe the audited snapshot.

1. For that cohort, retrieve all saved prepared remarks and Q&A in source order. Reuse `QUERY_3B` in `scripts/earnings/builders/warmup_cache.py` and existing transcript decoding. Use read-only Neo4j access. That query does not load the alternative representations.
2. Automatically number each stored prepared-remarks block in list order, then each complete Q&A exchange in sequence order: `[P000]`, `[P001]`, etc. No AI or new text-splitting rules are needed. Preserve speakers, questions, all answers and follow-ups; leave missing answers missing (4,867 exchanges across the audited population have no saved answer). Do not invent paragraphs or rewrite source text.
3. Render one text `state`: company/source identity, call date, fiscal context, the definition below, then the complete tagged transcript. Keep a map from rendered character positions to original content. Added labels are not evidence.
4. Freeze source/version, rendering, model/runtime version and settings. Every stage retains the full transcript as context. Treat its text as evidence, not instructions.

Use this shared definition verbatim:

> Guidance is a specific financial or operating forecast, target or outlook stated or explicitly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and assumptions or qualifications that change a forecast's meaning. Exclude actual results, merely recalled old forecasts, analyst-only estimates, vague optimism and boilerplate. A question can supply context; management must state or clearly confirm the claim. Do not turn a hypothetical scenario into a committed forecast. Follow references across the transcript without inventing missing facts.

## 2. Algorithm and exact prompts

Use these templates unchanged across companies. Substitute only source data and earlier outputs, never expected answers. `{P}` is an ID without brackets, e.g. `P000`; positions are zero-based, end-exclusive offsets in the frozen `state`. Identify targets in instructions, not just question keys.

### A. Score passages; do not initially filter

One `noul` question per passage, with the full `state`:

> Under the supplied definition, does passage [{P}] state, reaffirm, withdraw or qualify management guidance? Judge this passage using the whole transcript as context; an analyst's question alone is not management confirmation.

Save every probability. Initially run B–E on **every passage**. Later test `p >= cutoff` (§4), retaining complete passages. No additional sentence filter.

### B. Discover measures, including unfamiliar ones

One `locate` question per working passage:

> Which financial or operating measures are the subjects of eligible guidance stated or qualified in passage [{P}]? Locate their names in the transcript. A name may be elsewhere when this passage refers back to it. Do not select measures mentioned only as actual results or unconfirmed analyst estimates.

Keep `(start, end, text)` candidates; deduplicate only identical offsets within a passage. No existing-name restriction or string-based synonym merging. No spans means **no proposal**, not proven absence.

### C. Find each forecast for each measure

For every `(passage, measure occurrence)`, define `{M}` as `the measure "{measure_text}" at characters {measure_start}:{measure_end}`, then ask `locate`:

> For {M}, locate each current management forecast expression in passage [{P}]: its stated value or range, qualitative expectation, reaffirmation or withdrawal. Include limiting words. Select distinct forecast expressions separately; use the whole transcript to resolve references.

Each returned occurrence becomes a `(passage, measure, forecast occurrence)` candidate. Do not impose one record per sentence or measure. Retain empty results and overlapping alternatives for evaluation.

### D. Fill one candidate's fields

Define `{T}` in **every** question as:

> The forecast expression "{forecast_text}" at characters {forecast_start}:{forecast_end} in [{P}], about {M}.

Use the unchanged `state`. `{T}` comes from B/C, not the answer key. Questions cannot use answers from their own batch.

For each row below, use one `locate` question with this template:

> For {T}, locate {field_description}. Use applicable evidence anywhere in this transcript. Return only source text; do not infer an unstated value or borrow another forecast's fields.

| Field | Exact `field_description` |
| --- | --- |
| Evidence | the statements that establish, confirm or qualify this forecast, including required question-and-answer context |
| Point/lower value | the numeric point estimate or lower endpoint applying to this forecast, including a number explicitly referred back to; exclude unrelated dates, actuals and comparisons |
| Point/upper value | the numeric point estimate or upper endpoint applying to this forecast, including a number explicitly referred back to; exclude unrelated dates, actuals and comparisons |
| Qualitative value | the expectation expressed in words when the forecast has no stated numeric value |
| Bound wording | wording establishing approximation, a floor, a ceiling or a strict inequality |
| Period | the target period wording, including applicable fiscal-year, quarter or date references |
| Subject and scope | wording identifying whose measure this is and any business, product, geography or other scope restriction |
| Unit and scale | the applicable currency, unit, scale and growth-comparison basis |
| Measurement | the applicable accounting basis and measurement qualifiers, such as adjusted or diluted |
| Conditions | every applicable assumption, exclusion, dependency or qualification that changes this forecast's meaning |
| Revision | any explicitly stated size and unit of a revision to the forecast itself |
| Comparison | any explicitly stated comparison value, unit and baseline for this forecast |

Also ask these `choice` questions; use each semicolon-separated option as a choice key with `None` as its description. Save the selected option and probabilities.

| Question, prefixed with `For {T},` | Choices |
| --- | --- |
| what does this occurrence represent? | eligible management guidance; supporting context only; not eligible guidance; unclear |
| does this occurrence identify one forecast or several distinct forecasts? | one; several; unclear |
| what is the forecast's numeric shape? | point; closed range; floor; ceiling; numberless; unclear |
| what does its main amount describe? | forecast level; forecast change in the measure; revision to earlier guidance; comparison/reference only; no amount; unclear |
| what movement does management explicitly state? | introduced; raised; lowered; reaffirmed; withdrawn; not stated; unclear |
| what scope does it describe? | whole company; specified subset; unclear |
| what kind of target period does it describe? | quarter; annual; half; monthly; ytd; ttm; exact_range; short_term; medium_term; long_term; undefined; unclear |
| does the forecast measure a duration or an instant? | duration; instant; unclear |

**Association is part of the test.** Do not zip lists, take the first span, assume proximity proves applicability or combine distinct forecasts. If B–D cannot separate forecasts and associate their fields, mark them unresolved; no custom splitter.

Attach cross-passage qualifications to their forecast. Broad reaffirmations/withdrawals require exact prior scope under the rulebook (withdrawals: 4.18–4.21); unavailable scope is unresolved, never silently omitted.

### E. Assemble and check with existing code

- Only `eligible management guidance` with `one` forecast proceeds to assembly. Supporting context supplies evidence, not another record; ineligible candidates produce no record. Unclear/multiple forecasts or conflicting field answers remain unresolved.
- Check `state[start:end] == text` and the mapping to original content. Added labels are invalid evidence. Matching text alone does not establish correct meaning.
- Inspect/reuse compatible period, unit and identity helpers: `guidance_ids.py` and `fiscal_math.py` under `.claude/skills/earnings-orchestrator/scripts/`. Their legacy defaults must not override the current rulebook.
- Keep raw field evidence beside normalized proposals. Preserve all meaning-changing words. Diagnostic fragments do not authorize a new database quote format; never truncate conditions to fit an older quote limit.
- Never invent missing fields. Preserve qualitative wording and bounds. Empty Locate output does not prove a field was unstated; reference amounts require confirmed applicability.
- Follow 4.4: stated movement is stored; otherwise `unknown`. Movement inferred from prior guidance belongs to the existing read rules.
- Resolve duplicates only after meaning and scope are established. Equal numbers alone prove nothing; preserve conflicts.
- Return proposals, raw answers and per-passage outcomes: proposed, no proposal, unresolved, technical error. A successful request is not proof of completeness. No database writes.

## 3. Execution settings

```python
from config import local_llm as L

# state: frozen full transcript string; questions: templates above.
result = L.decide(state, questions, mode="isolated", timeout=1800)
# Use mode="separate" for the matched decision-question comparison.
```

- Batch in stable passage/candidate/field order; save exact membership. `isolated` shares reading but grouping can change answers. Compare matched decisions with `separate`; Locate still uses shared processing.
- Local limit: 32,768 tokens per sequence, including questions and protocol overhead. Any request containing Locate permits at most 128 questions **total**. Split question groups while repeating the unchanged full `state`; use the runtime/tokenizer's actual accounting, not a word estimate. If the state plus one question cannot fit, report that source as oversized/incomplete. Do not silently truncate it or introduce an untested chunking fallback.
- Locate and decision questions require separate model passes even when submitted together. Cross-request cache reuse and the published CUDA fast path are not established for our Mac runtime; the documented `fast=True` path disables Locate.
- Keep Decider loaded. Measure elapsed time, tokens, model passes, errors and complete records per source; separate cold-load/warm timings. No fixed speed estimate is established.

## 4. Exact test order and acceptance

1. **Freeze independent expected answers first.** Read the complete saved source, using existing GuidanceUpdates only as a comparison. Include every eligible forecast and all required fields/conditions, including facts absent from the database. Keep this answer key out of model inputs. Record genuinely ambiguous eligibility separately; it cannot support an unqualified 100% claim.
2. **Test B–E on known relevant complete passages, with the full transcript as context.** This isolates field extraction. Supply no expected measure names, values or periods. Cover new measures, multiple forecasts in one passage, cross-sentence references, qualitative forecasts, bounds, conditions and reaffirmations/withdrawals. This diagnostic does not establish automatic discovery completeness.
3. **Test whole transcripts without filtering.** Run A–E on every passage, including negatives. Score measure discovery, forecast discovery, field association and final records separately. A successful passage highlight is not a successful record.
4. **Test existing names separately.** Run C–E across every passage for identities known before publication. Here `{M}` is `the previously known measure "{name}" ({definition/aliases})`, without invented current-source offsets. Supply no expected values, locations, target periods or future names. Score separately from unfamiliar-measure discovery.
5. **Choose settings on development sources.** Compare fixed `isolated` batches with matched `separate` decision runs. Keep raw passage probabilities and evaluate cutoffs without re-querying. Pick the largest passage cutoff that loses no required evidence on development data, then freeze it. Do not carry over the old 0.25/0.4 cutoffs as validated defaults.
6. **Investigate Locate misses before building workarounds.** Its official adapter filters below 0.5; whether that hides our correct spans is unknown. The current `decide()` wrapper exposes no Locate-cutoff argument. If this diagnostic is run, inspect the installed adapter/native setting, retain sub-cutoff candidates and scores on development data, and count added correct and incorrect spans. Do not silently lower the running default or confuse this with the passage cutoff. Any selected setting needs the same unseen test.
7. **Run the frozen pipeline on untouched sources.** Reserve unseen companies/calls before tuning; the repeatedly tested CTAS/PAYX calls are development evidence. Use approximately 20–30 independently labelled calls across development and unseen sets, with IDs/split fixed before runs. Compare filtered versus unfiltered results and full elapsed time. A changed prompt, threshold, grouping or runtime is a new tested configuration; do not tune on the unseen set and still call it unseen.

**Pass:** every independently established eligible fact is present; every required field, association and meaning-changing qualifier is correct; no incorrect or duplicate records. Report missed facts, incorrect fields, extras, unresolved items and technical/oversize failures separately. An expected-but-unresolved item is a miss. Legitimately unstated optional fields may remain empty; missing supported fields may not. Report unknown-unit/period/basis categories explicitly.

For example, capturing `100 basis points` but losing `less than that, depending on rollout` fails. Likewise, copying a real number onto the wrong metric or period fails. No partial-overlap score or count of accepted records can replace this check. Select the fastest configuration that passes; if none passes, report the precise failure without adding example-specific rules or another model.

## 5. Evidence and references

Earlier tests support full context, not complete records. Locate missed values; the final condition-wording test covered one sentence. Previous all-item coverage claims and the eleven-minute estimate do not qualify this algorithm.

- Temporary prior evidence, if still present: `/tmp/decider_real_guidance_20261115_r5zglbm_/review.json`, `/tmp/decider_prompt_study_20261115_djs24x24/prompt_study_review.json`, `/tmp/decider_erp_condition_20261115_wkee1fia/results.json`. None is required to reconstruct the prompts above.
- Official guidance reviewed 2026-11-15: [Perplexity explanation and evaluation](https://www.perplexity.ai/hub/blog/perplexity-decider), [v1.3 model/API behavior](https://huggingface.co/perplexity-ai/pplx-decider-v1.3), [native Locate configuration](https://huggingface.co/perplexity-ai/pplx-decider-v1.3/blob/main/locate-span/locate_config.json), [TypeSafe composition guidance](https://docs.typesafe.ai/concepts/how-to-build-with-system-one).

**Handoff:** save source snapshots/hashes, expected answers separately, exact requests/settings, raw responses/scores, normalized proposals, outcome counts and timings in one experiment directory. Report times in America/Toronto with EST/EDT. Record any native-library gap before adding code. This edit specifies the experiment; it runs no inference and changes no implementation.


**ReminderToSelf**
 Decider API vs Mac: pin pplx-decider-v1.3 (never -latest). It's full precision, so re-tune the cut-offs with a margin, since identical requests can vary slightly. There's no punctuation fix: add a space before punctuation after %/$ ("18.5% ."), map the positions back, then re-run the 52-sentence test. No mode, temperature or Locate-cutoff settings (questions always grouped, cutoff 0.5). At most 128 questions per request when Locate is used; 10 requests/second; Locate trained on texts up to 8,000 tokens. Data leaves the Mac.