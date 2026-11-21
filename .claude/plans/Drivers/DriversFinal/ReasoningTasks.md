# Reasoning tasks

[DRIVER_RULES.md](DRIVER_RULES.md) governs these judgments. Row numbers are references. Follow the [build order](DriverWorkflow/DriverWorkflow.md#top-10-build-and-test-steps) and use the cheapest model that passes each task’s tests (8.13).

**Answer** = the kind of answer · **Jev so far (exploratory)** = [earlier test results](JEV.md), often from two airlines. They apply only to the questions tested. Finding 99% of known facts measures coverage.

## 1 · Finding the fact

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 1 | Is there an eligible fact here (a sentence or passage, read with its surrounding context), or only a mention or boilerplate? | yes/no per sentence or passage | caught 99.1–99.6% of known facts |
| 2 | Find updates in a new source. After initial company context, a metric’s first accepted fact for that company starts one search of covered sources, oldest first, within the 12 months before its source’s known public time (8.16) | select passages | |
| 3 | Is the claim excluded, e.g. a bookkeeping elimination or “results beat” still lacking a measure after reading the full source (2.14, 4.15)? | yes/no each | |
| 4 | Separate distinct claims and scenarios. Return one candidate per actual period value stated in prose or a table, with its period, evidence and comparison context (8.14) | split | |
| 5 | Resolve references such as "the Company", "this program" or "year-end" | select words | |
| 6 | Select exact passages or cells proving the claim, including numbers, unit words, speaker, negation and conditions. Code verifies locations and copies each excerpt from that version (1.17, 1.24) | select evidence | cannot write |
| 7 | Who stated or confirmed the claim? Guidance is confirmed if the company states or adopts the outlook as its own, unconfirmed if only clearly attributed to it. Skip unclear authorship. An analyst’s question alone proves nothing (1.26, 4.9) | speaker + guidance confirmation if applicable | |

## 2 · Kind

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 8 | Which kind: metric, guidance, surprise, action_event or expectation? | pick 1 of 5 | 97–99.6% on the original four types |
| 9 | For a metric: do the words show a standing level that can be read again? | yes/no + words | |
| 10 | Does the suffix fit? `_guidance` requires a company-attributed forecast of a standing measure or condition. `_surprise` compares that measure with expectations. `_expectation` requires an outsider’s own forecast of a specific measure or event (2.23) | yes/no | |

## 3 · Name

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 11 | Before seeing saved names, write a precise, reusable Driver name from the source’s own words for what is measured or happened | write new words | cannot write |
| 12 | For each qualifying word: the company's own measured part, an outside cause, or unclear? | pick 1 of 3 | |
| 13 | Does a word change which portion is counted (the population measured, such as "funded" versus total assets), or only re-express the same amount? | pick 1 of 2 | |
| 14 | A stated benchmark or per-unit denominator ("per X"), which goes into the name | select words | |
| 15 | Is an acronym's expansion certain? | yes/no | |
| 16 | Does the name break a naming rule (a direction, period, company or number in it)? An outside company, platform, institution or person is allowed when its own action or state is the cause (`aws_outage`, `tiktok_ban`) | yes/no per rule | untested |
| 17 | Does the name keep the source's meaning and point at the right thing (the cause, or the charge actually recorded)? | yes/no | |

## 4 · Which Driver

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 18 | From the word and meaning search across companies, propose one same-type Driver. Before creation, compare every remaining same-type definition. At most one shortlist candidate and one different full-search candidate may be checked. Break ties under 2.41 (2.43) | one proposal or none | |
| 19 | Is it only a spelling or word-order variant of an existing name? | yes/no | |
| 20 | Independently check object, population, mechanism, ambiguity and the saved definition. For placement, refuse if another plausible reading changes the fit. Another fitting name alone is fine. Other identity checks require no equal rival. The original evidence must support one meaning and the saved name and type (2.40, 10.2) | 5 yes/no | earlier check insufficient alone, ruled out 94% of different pairs as a veto |
| 21 | Does the new metric, guidance, surprise or measure expectation concern the same measure as every existing family member? Independently check the underlying measure (2.26) | yes/no | |
| 22 | After the complete search, does the source prove a clear reusable kind at the level stated? An uncertain match can keep its own available name if all creation checks pass (2.20) | yes/no | |
| 23 | Try one more specific, source-backed name if a suffix is rejected (drop it), a family check fails, or the exact name is taken and a different meaning is proven. Use normal duplicate checks. If no safe name exists, skip and log (2.24, 2.26, 2.47) | name or skip | cannot write |
| 24 | For a new Driver: select its first (defining) quote and the nearby context needed to understand it | select text | |

## 5 · State

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 25 | Metric's stated direction or condition: increased, decreased, unchanged, mixed, reported, persists, unknown | pick 1 of 7 | 91.9%, or 97.9% after rulings |
| 26 | Action stage: rumored, at risk, announced, continued, suspended, canceled, failed, resolved, occurred, forecast, unknown. A company’s own stated plan is announced. Its prediction of another party’s action is forecast and proves no actual stage (10.5) | pick 1 of 11 | |
| 27 | For guidance, store raised, lowered or reaffirmed when stated. A bare forecast stores unknown. When read, a genuinely first confirmed forecast can be introduced. A withdrawal is an action (4.4, 4.18) | 5 guidance states including unknown | |
| 28 | Is it only a correction, with no business change? | yes/no | |
| 29 | Surprise: actual versus consensus, actual versus the company’s confirmed earlier guidance, or confirmed guidance versus consensus? | pick 1 of 3 | 64 of 65 |
| 30 | Surprise result: beat, in line, missed, or unknown (also put as favorable or unfavorable) | pick 1 of 4 | 39 of 41 |
| 31 | Which accepted fact in the same event supports the surprise: the matching result or confirmed guidance? Check the same claim, scope and conditions. Reread the event if missing (4.14–4.15) | match or missing | |

## 6 · Amounts

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 32 | Which numbers belong to this fact? | select | |
| 33 | What is each number: the value, the change, the compared value, a forecast revision, or another amount? ("revenue up 5%" is a change) | pick / label | |
| 34 | Is the fact a point, range, minimum, maximum or numberless? A table dash counts as zero only if the source explicitly defines it for that cell. An unexplained dash proves none of these (3.48, 10.4) | pick 1 of 5 when supported | |
| 35 | Sign, from the wording and context: loss, charge, benefit, "narrowed", brackets | pick | weak on signs and number comparisons |
| 36 | Unit (currency or other unit) of the value and of the change, with the words that prove it | pick from list | 97.4% and 97.5% |
| 37 | Stated scale: units, thousands, millions and so on | select words | |
| 38 | Growth basis of a growth percentage: year over year, sequential, points, basis points, unknown | pick 1 of 5 | |
| 39 | Main comparison: consensus, prior year, previous period, previous guidance, none | pick 1 of 5 | 98.1% |
| 40 | Numberless wording: tidy guidance, copy exact metric words that add meaning beyond the state, and keep an outside forecast’s wording in its quote (4.7, 9.11) | select or tidy words | cannot write |
| 41 | Identify stated assumptions on guidance or actions. For an action, copy the exact conditional clause. Outside forecasts keep conditions in the quote (4.8, 9.11) | select words | |

## 7 · Period

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 42 | Which dates, fiscal period or horizon does the source prove? A predicted window supplies no occurrence date. An outside price target may lack a deadline. A forecast total needs its measurement period (3.37, 9.11, 10.5) | select period if applicable | weak on dates |
| 43 | Kind of period: quarter, annual, half, year to date, exact range, short or long term (a vague horizon)… | pick 1 of 11 | 39 of 49 |
| 44 | A span of time or a single moment? | pick 1 of 2 | 94.1%, or 100% after rulings |

## 8 · Part of the company, and qualifiers

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 45 | Whole company, or a part of it? | yes/no | |
| 46 | Kind of part: segment, product, geography, customer, channel, owned stake, or unknown | pick 1 of 7 | 81.1%, or 100% where the rules decide |
| 47 | Which part: reuse a label from the company's own list, or create a new one grounded in the source | pick from list or copy | |
| 48 | Qualifying words on the number (measurement qualifiers such as adjusted, diluted, constant currency) | select words | |
| 49 | Offline setup: classify the filing's breakdown axes, from their members, as company parts or non-parts | pick per axis, done once | |

## 9 · Links

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 50 | Does the text explicitly say one fact caused another, or pushed against (offset) it? | yes/no per pair + words | pilot: 46 of 46, none false |
| 51 | Is the company withdrawing guidance, planning to withdraw it, or reaffirming it? Record each withdrawal once per source occurrence as an action with its scope, exceptions, conditions and timing. Reaffirmation stays guidance (3.7, 4.18) | classify + evidence | |
| 52 | Do the company’s own words prove that only the name changed, with the same contents and method? Independently verify both exact names on that company’s facts. An unused name alone gives no verdict (6.13–6.14) | kind + names + evidence, refuse or skip | |
| 53 | Which official line item in the filing data is exactly this metric, or none? | pick from the company's list, or no link | 72.6–95%; Haiku 88.6% |

## 10 · Checking

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 54 | Does the source support every filled field? Use this question in extraction and testing. The separate fact check judges the Driver choice. Code verifies the saved evidence (1.17, 8.2) | supported per field | caught planted errors, but only 2 of 32 real ones |
| 55 | In tests or a rule-authorized reread, was a fact or meaningful qualifier missed in context (4.15, 8.14–8.17)? | yes/no per sentence or passage | |
| 56 | No safe answer: name the unresolved meaning and explain why | pick a reason | |

## 11 · Additional judgments

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 57 | Whose fact is it? Identify the subject company from the quote and context, or establish that the fact is genuinely shared. Skip or hold an unresolved company-specific fact (3.9, 8.15) | company, shared or unresolved | |
| 58 | Who made the outside forecast, when, and what does the source say changed? A firm keeps one history across signers. Distinguish personal estimates and reported consensus. Never infer a revision from stored history (9.11) | credited forecaster and decision date when stated + introduced, raised, lowered, reaffirmed, withdrawn or unknown | |
| 59 | Do passages in one source version describe the same claim, Driver and scope? Combine compatible details with each citation. Keep distinct decisions and conditional alternatives separate. No extra AI pass (5.2) | combine, separate or unresolved | |
| 60 | During the fact check, flag shown definitions that appear equivalent or cite both when they clearly disagree. Code logs a disagreement only for names already joined. Independently judge each eligible new pair from its names, types and original evidence alone. Fact placement never waits (5.6) | flag or warning if warranted, yes/no on eligible pairs | |
| 61 | When reading current guidance, AI judges which open forecasts a company withdrawal covered when it took effect, confirmed or unconfirmed. Apply scope, conditions, exceptions and replacements in effective order using evidence public before the cutoff. Reuse the decision for identical inputs (2.46, 4.19–4.20, 8.1) | covered, unaffected or unresolved | |

## Notes

- Code handles IDs, arithmetic, rescaling, date calculations, exact citation checks and saving. Row 59 covers the judgment about whether two passages describe one claim.
- A later task judges which facts explain a company’s daily price move. See [EXPLAINED_BY.md](EXPLAINED_BY.md).

### Two corrections to Fable's prompt review, found while reading

- Eliminations: the document does say a fact about a bookkeeping elimination is set aside. GPT's line had a basis; Fable was wrong to dismiss it.
- Unit words: the document says the words that prove the unit (such as "in millions") must sit inside the quote. GPT was right, and Fable's prompt needs that added before you approve it.
