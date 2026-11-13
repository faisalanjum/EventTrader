# Reasoning tasks

The meaning tasks, from [JEV.md](JEV.md) and the rules. Numbers are for reference only; which model does each task, and in what order, is still open.

**Answer** = the kind of answer · **Jev so far (exploratory)** = early test results, nothing adopted. Many tests mainly covered two airlines, and "caught 99% of known facts" does not mean 99% of answers are correct.

## 1 · Finding the fact

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 1 | Is there an eligible fact here (a sentence or passage, read with its surrounding context), or only a mention or boilerplate? | yes/no per sentence or passage | caught 99.1–99.6% of known facts |
| 2 | Find facts for a Driver we already know: its updates in a new source, or (after a metric Driver's first accepted fact) its history in the company's earlier sources, oldest first | select passages | |
| 3 | Is it set aside by the document (an outside forecast alone, a forecast of someone else's decision, "results beat" with no measure, a bookkeeping elimination)? | yes/no each | |
| 4 | Does one sentence or passage hold several facts, including different scenarios? Separate them | split | |
| 5 | Resolve references such as "the Company", "this program" or "year-end" | select words | |
| 6 | Copy its exact quote, with the numbers and unit words, and the context needed to support it | copy words, or select and let code copy | cannot write |
| 7 | Who stated or confirmed it? In a call: the company, or only an analyst's question? For guidance: did the company itself state or confirm it? | pick 1 of 3: the company, someone else, or unclear | |

## 2 · Kind

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 8 | Which kind: metric, guidance, surprise, or one-time event (action)? | pick 1 of 4 | 97–99.6% |
| 9 | For a metric: do the words show a standing level that can be read again? | yes/no + words | |
| 10 | For a name ending `_guidance` or `_surprise`: is the rest a real standing metric? | yes/no | |

## 3 · Name

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 11 | Say exactly what is being measured or what happened, and write a precise, reusable Driver name from the source's own words | write new words | cannot write |
| 12 | For each qualifying word: the company's own measured part, an outside cause, or unclear? | pick 1 of 3 | |
| 13 | Does a word change which portion is counted (the population measured, such as "funded" versus total assets), or only re-express the same amount? | pick 1 of 2 | |
| 14 | A stated benchmark or per-unit denominator ("per X"), which goes into the name | select words | |
| 15 | Is an acronym's expansion certain? | yes/no | |
| 16 | Does the name break a naming rule (a direction, period, company or number in it)? An outside company, platform, institution or person is allowed when its own action or state is the cause (`aws_outage`, `tiktok_ban`) | yes/no per rule | untested |
| 17 | Does the name keep the source's meaning and point at the right thing (the cause, or the charge actually recorded)? | yes/no | |

## 4 · Which Driver

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 18 | Find existing Drivers that might mean the same | shortlist | |
| 19 | Is it only a spelling or word-order variant of an existing name? | yes/no | |
| 20 | Independently judge: same Driver (its frozen meaning) or not, by five checks: same object, same population, same mechanism, no equal rival, one clear meaning | 5 yes/no | not good enough alone; as a veto it ruled out 94% of different pairs |
| 21 | Independently judge: does it belong to an existing metric/guidance/surprise family, measuring the same thing as the rest (revenue, revenue guidance, revenue surprise)? | yes/no | |
| 22 | Is a proposed new Driver a reusable kind, not a one-off, with one clear meaning and enough supporting evidence? | yes/no | |
| 23 | If refused: write a more specific name, or skip | write new words | cannot write |
| 24 | For a new Driver: select its first (defining) quote and the nearby context needed to understand it | select text | |

## 5 · State

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 25 | Metric's stated direction or condition: increased, decreased, unchanged, mixed, reported, persists, unknown | pick 1 of 7 | 91.9%, or 97.9% after rulings |
| 26 | One-time event (action) stage: rumored, at risk, announced, continued, suspended, canceled, failed, resolved, occurred, unknown | pick 1 of 10 | |
| 27 | Guidance movement, only when the source states it: introduced, raised, lowered, reaffirmed, withdrawn; otherwise unknown. A bare forecast is not automatically "introduced": code works out the movement later | pick 1 of 6 | |
| 28 | Is it only a correction, with no business change? | yes/no | |
| 29 | Surprise: what is compared? Actual versus consensus, actual versus the company's own forecast (guidance), or guidance versus consensus | pick 1 of 3 | 64 of 65 |
| 30 | Surprise result: beat, in line, missed, or unknown (also put as favorable or unfavorable) | pick 1 of 4 | 39 of 41 |
| 31 | Is the surprise tied to a specific measure, and which fact is its result? | yes/no + match | |

## 6 · Amounts

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 32 | Which numbers belong to this fact? | select | |
| 33 | What is each number: the value, the change, the compared value, a forecast revision, or another amount? ("revenue up 5%" is a change) | pick / label | |
| 34 | Is the number a point, a range, a minimum or a maximum? | pick 1 of 4 | |
| 35 | Sign, from the wording and context: loss, charge, benefit, "narrowed", brackets | pick | weak on signs and number comparisons |
| 36 | Unit (currency or other unit) of the value and of the change, with the words that prove it | pick from list | 97.4% and 97.5% |
| 37 | Stated scale: units, thousands, millions and so on | select words | |
| 38 | Growth basis of a growth percentage: year over year, sequential, points, basis points, unknown | pick 1 of 5 | |
| 39 | Main comparison: consensus, prior year, previous period, previous guidance, none | pick 1 of 5 | 98.1% |
| 40 | A forecast given only in words (no numbers): select the source wording, or write it down | copy or write | cannot write |
| 41 | Assumptions or conditions attached to a forecast | select words | |

## 7 · Period

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 42 | Which period is the fact about: which dates, fiscal year and quarter? | select | weak on dates |
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
| 51 | Does the text withdraw or reaffirm a forecast, and exactly which earlier ones? (Spreading a withdrawal to the earlier forecasts it covers is on hold: it needs rethinking.) | yes/no + scope | |
| 52 | Does the company say an old label continues under a new name? (release 2 in the document) | yes/no | |
| 53 | Which official line item in the filing data is exactly this metric, or none? | pick from the company's list, or no link | 72.6–95%; Haiku 88.6% |

## 10 · Checking

| # | Task | Answer | Jev so far (exploratory) |
|---|---|---|---|
| 54 | Before saving: does the quote support every filled field (each proposed reading)? | yes/no per field | caught planted errors, but only 2 of 32 real ones |
| 55 | Was a fact, or a meaningful qualifier, missed in this text (read with its surrounding context)? | yes/no per sentence or passage | |
| 56 | No safe answer: name the unresolved meaning and explain why | pick a reason | |

## Notes

- Which tasks write new words depends on the design: 11 and 23 do; 40 only if it does not reuse the source wording; 56 only if its reason is written rather than picked. 6 only copies words, or selects them for code to copy.
- Not in the list: mechanical work that code does exactly: IDs, arithmetic and rescaling numbers, date calculations (dates from the fiscal calendar), checking a quote is in the text (exact quote matching), duplicate handling, and saving.
- The previously deferred input-preparation work stays pending.

### Two corrections to Fable's prompt review, found while reading

- Eliminations: the document does say a fact about a bookkeeping elimination is set aside. GPT's line had a basis; Fable was wrong to dismiss it.
- Unit words: the document says the words that prove the unit (such as "in millions") must sit inside the quote. GPT was right, and Fable's prompt needs that added before you approve it.
