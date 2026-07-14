# News analysis for exact-value extraction

Scope: I analyzed the 8 records in `news_samples.json`. All 8 are tagged with `kpi: revenue`. I treat the target as the current-period actual revenue/sales value unless stated otherwise. Where a sample only has estimates, prior-period values, or peer/table values, I label it as a lookalike, not as current actual revenue.

Important grounding note: the sample is useful for article patterns, but it is small and selected. Recall estimates below use the brief's 34-case census where possible.

## 1. Taxonomy of earnings-news article types

### A. Pre-earnings preview

Observed sample:

- AA, `A Peek at Alcoa's Future Earnings`, created 2025-10-21, channels `Earnings`.

What it contains:

- The article is before the earnings release.
- It says Alcoa "will release" quarterly earnings on 2025-10-22.
- It gives expected EPS: analysts anticipate EPS of `$-0.02`.
- It gives historical EPS table values for prior quarters.
- It gives peer/company table values such as Alcoa `Revenue Growth 3.85%` and `Gross Profit $366M`.

Where values appear:

- Body only.
- Title does not include an exact metric value.
- Teaser is empty.

Phrasing patterns:

- Future tense: "will release its quarterly earnings report".
- Estimate language: "Analysts anticipate".
- Historical language: "Last quarter", "past performance".
- Table-like flattened text: `Company Consensus Revenue Growth Gross Profit Return on Equity`.

Extraction meaning:

- For current actual revenue, this is a false friend. It does not state current Q3 revenue.
- It may be useful only if the target metric is an estimate, historical EPS, revenue growth, gross profit, or another table value.

### B. Analyst forecast / ratings article ahead of earnings

Observed sample:

- AA, `Alcoa Earnings Are Imminent; These Most Accurate Analysts Revise Forecasts Ahead Of Earnings Call`, created 2025-10-22, channels `Earnings`, `News`, `Price Target`, `Markets`, `Analyst Ratings`, `Trading Ideas`.

What it contains:

- Consensus estimate for quarterly revenue: `$3.13 billion`.
- Year-ago comparison revenue: `$2.9 billion`.
- Analyst price targets: `$42.5`, `$40`, `$34`, `$27`, etc.

Where values appear:

- Body first paragraph has the estimate and year-ago revenue.
- Title has no current actual revenue.
- Teaser is empty.

Phrasing patterns:

- "Analysts expect".
- "The consensus estimate for Alcoa's quarterly revenue is $3.13 billion".
- "compared to $2.9 billion a year earlier".
- Analyst action phrasing: "raised the price target from $38 to $42.5".

Extraction meaning:

- For current actual revenue, this is also a false friend.
- It is especially risky because it is in `Earnings` and has `Price Target` / `Analyst Ratings`, but the revenue number is an estimate, not actual.

### C. Standard earnings beat/miss wire

Observed samples:

- AA, `Alcoa Q3 Adj. EPS $(0.02) Misses $0.01 Estimate, Sales $2.995B Miss $3.131B Estimate`, channels `Earnings`, `Earnings Misses`, `News`.
- ABBV, `AbbVie Q3 Adj. EPS $1.86 Beats $1.79 Estimate, Sales $15.776B Beat $15.590B Estimate`, channels `Earnings`, `Earnings Beats`, `News`, `Hot`.
- ABNB, `Airbnb Q3 EPS $2.21 Misses $2.32 Estimate, Sales $4.095B Beat $4.078B Estimate`, channels `Earnings`, `Earnings Beats`, `Earnings Misses`, `News`, `Hot`.

What it contains:

- Current actual EPS.
- Consensus EPS estimate.
- Current actual sales/revenue.
- Consensus sales/revenue estimate.
- Prior-year EPS and sales/revenue comparison.

Where values appear:

- Title has the current actual sales value and the estimate.
- Teaser starts with EPS and is truncated in all 3 samples before the full sales sentence.
- Body first paragraph repeats the exact actual sales value and estimate.

Phrasing patterns:

- Title: `Sales $X Beat/Miss $Y Estimate`.
- Body: "The company reported quarterly sales of $X which beat/missed the analyst consensus estimate of $Y by Z percent."
- Prior-year comparison: "This is a ... increase/decrease over sales of $Z the same period last year."

Extraction meaning:

- These are the strongest samples for exact current revenue extraction.
- For revenue, the actual value is the first value after `Sales`, or the value after "reported quarterly sales of".
- The value after `Estimate` or after "consensus estimate of" is not the actual.

### D. Post-earnings mover / market-reaction recap

Observed samples:

- AA, `Alcoa Stock Slides After Q3 Earnings Miss: What To Know`, channels `Earnings`, `News`, `Commodities`, `Top Stories`, `After-Hours Center`, `Movers`, `Trading Ideas`.
- ABNB, `Airbnb Shares Climb After Mixed Q3 Earnings: EPS Miss, Revenues Beat`, channels `Earnings`, `News`, `Travel`, `Top Stories`, `After-Hours Center`, `Movers`, `Trading Ideas`, `General`.

What it contains:

- A short market reaction framing.
- Current actual EPS and revenue.
- Consensus estimates.
- Stock price move.
- Other business metrics, segment details, quotes, and outlook.

Where values appear:

- Title says the result direction but usually not the exact revenue value.
- Teaser is generic: "Here's a look at..." and does not carry the exact value.
- Body early section carries the value.

Concrete examples:

- AA body: "Quarterly revenue of $2.99 billion came in below the Street estimate of $3.13 billion."
- ABNB body: "Quarterly revenue came in at $4.09 billion, which beat the Street estimate of $4.07 billion."

Phrasing patterns:

- "released its third-quarter earnings report".
- "Here's a look at the key figures".
- "The Details:".
- "Quarterly revenue of $X came in below/above the Street estimate of $Y."
- "stock was up/down ... in extended trading."

Extraction meaning:

- These articles often hide the value in the body, not the title.
- They also contain many non-target values. AA includes production, shipments, third-party revenue, segment revenue, and stock price. ABNB includes gross booking value, EBITDA, quote text, and Q4 revenue guidance.

### E. Broader earnings recap with guidance and analyst color

Observed sample:

- ABBV, `AbbVie Raises 2025 Outlook Helped By Strong Immunology Growth, Boost Dividend`, channels `Analyst Color`, `Biotech`, `Earnings`, `Large Cap`, `News`, `Guidance`, `Health Care`, `Analyst Ratings`, `Movers`, `Trading Ideas`, `General`.

What it contains:

- Current actual sales.
- Consensus estimate.
- Dividend change.
- CEO quote.
- Segment/product sales.
- Fiscal-year guidance.
- Analyst take.
- Stock move.

Where values appear:

- Teaser includes actual revenue: `$15.78 billion revenue`.
- Body first sentence includes actual sales: "reported third-quarter 2025 sales of $15.78 billion".
- Later body has segment/product values like immunology `$7.89 billion`, Skyrizi `$4.71 billion`, Rinvoq `$2.18 billion`, Humira `$993 million`, and fiscal 2025 EPS guidance `$10.61-$10.65`.

Phrasing patterns:

- "reported third-quarter 2025 sales of $X".
- "beating the consensus of $Y".
- "Sales increased ...".
- "Guidance: ... raised its fiscal 2025 adjusted earnings from ... to ...".
- "Analyst Take".

Extraction meaning:

- Good source for current actual revenue if the reader uses the first result sentence.
- High risk later in the article because segment/product revenue and guidance values are mixed with the company-level value.
- Exactness can differ by article: ABBV's standard wire says `$15.776B`; this recap rounds to `$15.78 billion`.

### F. AI-generated or templated summaries

Observed in samples:

- No explicit AI-generated disclaimer appears in the 8 sample records.
- The AA preview `A Peek at Alcoa's Future Earnings` looks templated because of generic setup text, a historical earnings table, and a peer ratings table. That is an observed style pattern, not proof of AI generation.

Extraction meaning:

- Since no explicit AI disclaimer is present in the samples, any AI-specific behavior is a hypothesis from the brief, not observed sample evidence.
- The grounded risk is that templated preview text can look earnings-related while carrying estimates, historical values, and peer values instead of actual current revenue.

## 2. Retrieval design using channels as priority, not filter

Goal: find a given metric's exact value in news without company-specific or metric-specific hardcoding.

### Fetch candidates broadly

Use ticker/company plus date first. Do not start with words from the saved filing quote, because the samples show journalist wording differs:

- Standard wires say `Sales $X`.
- Recaps say `Quarterly revenue of $X` or `Quarterly revenue came in at $X`.
- ABBV recap says `sales of $X`.
- Later article sections may say `net revenues`, `third-party revenue`, or guidance ranges.

Date windows:

- Primary window for actual results: earnings date through next calendar day.
  - In the samples, actual-result articles for AA, ABBV, and ABNB are all created on the earnings date: 2025-10-22, 2025-10-31, and 2025-11-06.
- Downrank pre-release articles for actual extraction.
  - AA preview on 2025-10-21 says "will release".
  - AA analyst forecast article on 2025-10-22 says "Analysts expect".
- Fallback window: a small wider window around the event, such as -2 to +3 calendar days, should be fetched but lower ranked.
  - This is a retrieval hypothesis. The sample only proves same-day and prior-day behavior, not the best wider window.
- If release timestamp exists, use it.
  - Articles created before the release should be treated as estimate/preview candidates unless they clearly say "reported" and give actuals.

### Use channels as ranking priors

Do not filter to `Earnings` only.

Brief census support:

- Value present anywhere: 18/34.
- Value present in an `Earnings`-channel article: 13/34.
- Therefore an `Earnings` filter has a measured ceiling of 13/18 present values, or 72% recall-of-present.
- The other 5 present values are in analyst/price-target style articles according to the brief.

Sample support:

- All 8 samples include `Earnings`, but many useful articles also include other channels.
- AA forecast article includes `Price Target` and `Analyst Ratings`.
- ABBV broader recap includes `Analyst Color`, `Guidance`, `Analyst Ratings`, and `Movers`.
- AA and ABNB recaps include `Movers`, `After-Hours Center`, `Top Stories`, and `Trading Ideas`.

Simple channel priority:

| Priority | Channels | Why |
|---|---|---|
| Highest | `Earnings`, `Earnings Beats`, `Earnings Misses` | Standard wires in samples carry exact values in title/body. Brief hit rates are highest here: 16-17%. |
| High | `Guidance`, `Movers`, `After-Hours Center`, `Top Stories`, `Hot` | Samples show recaps and broader earnings stories with values here. |
| Medium | `Analyst Ratings`, `Price Target`, `Analyst Color`, `Markets`, `Trading Ideas` | Brief says 5 present values hide outside Earnings-first; samples show these channels can carry forecasts or broader recaps. |
| Low but keep | `News`, `General`, sector channels | Brief says `News` has lower hit rate, but it is common on useful samples. |

### Rank articles by article type signals

Positive signals for current actual revenue:

- Title pattern like `Q3 ... Sales $X Beat/Miss $Y Estimate`.
  - Seen in AA, ABBV, ABNB standard wires.
- Body phrase "reported quarterly sales of $X".
  - Seen in AA, ABBV, ABNB standard wires.
- Body phrase "Quarterly revenue of $X" or "Quarterly revenue came in at $X".
  - Seen in AA and ABNB mover recaps.
- Body phrase "reported third-quarter 2025 sales of $X".
  - Seen in ABBV broader recap.
- Created on or just after earnings release date.

Negative/downrank signals for current actual revenue:

- Future tense: "will release".
  - Seen in AA preview.
- Estimate words before the metric value: "Analysts expect", "consensus estimate".
  - Seen in AA forecast.
- Historical words: "last quarter", "same period last year", "year-ago", "past performance".
  - Seen in AA preview and all standard wires' comparison sentences.
- Outlook words: "sees fourth-quarter revenue", "guidance", "range".
  - Seen in ABNB recap and ABBV recap.

### Rank fields and chunks

Use article fields as separate chunks with metadata:

1. Title.
2. Teaser.
3. First body chunk: first 1-3 paragraphs or first 6-10 sentences.
4. Later body chunks split by paragraph/section.

Why:

- Standard wires carry actual sales in title and first body paragraph.
- ABBV broader recap carries actual sales in teaser and first body sentence.
- AA and ABNB mover recaps carry exact revenue in the early body, not the title.
- Later body sections often contain segment/product/guidance values that are real but may be wrong for company-level actual revenue.

Do not rely on teaser alone:

- AA, ABBV, and ABNB standard-wire teasers are truncated after EPS text.
- A teaser may omit the revenue sentence even when title/body have it.

### Reader rules for exact-value extraction

For current actual revenue, accept a value only when the local sentence or title clearly says the company reported current-period revenue/sales.

Accept patterns observed in samples:

- `Sales $X Beat/Miss $Y Estimate` in a title: accept `$X`, reject `$Y`.
- "reported quarterly sales of $X": accept `$X`.
- "reported third-quarter 2025 sales of $X": accept `$X`.
- "Quarterly revenue of $X came in below/above the Street estimate": accept `$X`.
- "Quarterly revenue came in at $X": accept `$X`.

Reject or downrank:

- Values after "consensus estimate", "Street estimate", or "Analysts expect".
- Values after "compared to", "year earlier", "same period last year".
- Values in outlook/guidance ranges unless the target is guidance.
- Segment/product values unless the target is that segment/product.
- Stock prices, price targets, EPS, gross booking value, EBITDA, dividend, production, shipments.

Observed revenue aliases for this sample only:

- `sales`
- `revenue`
- `net revenues`
- `third-party revenue`

Use these as generic revenue aliases, not company-specific rules.

### Expected recall gain

Measured from the brief:

- Current quote-word ranking finds 10 of 18 values that are present in news, because it misses 8 of 18 present values. That is 56% recall-of-present.
- Filtering to `Earnings` has a 13/18 recall-of-present ceiling, or 72%, because 5 present values are outside `Earnings`.
- Channel-priority retrieval removes that known 72% ceiling by keeping analyst, price-target, mover, market, and general news candidates.

Observed from the 8 samples:

- For current actual revenue, 6 samples have clear actual-result values:
  - AA standard wire: `$2.995B`.
  - AA mover recap: `$2.99 billion` and later `$3 billion` total third-party revenue.
  - ABBV standard wire: `$15.776B`.
  - ABBV broader recap: `$15.78 billion`.
  - ABNB standard wire: `$4.095B`.
  - ABNB mover recap: `$4.09 billion`.
- The 2 AA preview/forecast samples should be rejected for current actual revenue because they carry estimates or historical/table values, not current actual revenue.

Estimated gain:

- A simple date + channel-priority + article-type ranker should recover many of the 8 misses caused by filing-quote word mismatch.
- A cautious expected range is about 14-16 of the 18 present values, or 78-89% recall-of-present, if articles are fetched by ticker/date and not filtered by channel.
- That 14-16/18 estimate is a hypothesis, not directly measured in the sample. The sample is too small and too selected to prove it.
- For the full 34-case census, even 16/18 present values would be only 47% recall overall, because news contains the value anywhere for only 18/34 cases.

## 3. Precision risks and guards

### Risk: consensus estimate confused with actual

Observed evidence:

- AA standard title has actual `Sales $2.995B` and estimate `$3.131B Estimate`.
- ABBV standard title has actual `Sales $15.776B` and estimate `$15.590B Estimate`.
- ABNB standard title has actual `Sales $4.095B` and estimate `$4.078B Estimate`.
- AA forecast article says "The consensus estimate for Alcoa's quarterly revenue is $3.13 billion".
- AA, ABNB recaps say revenue came in above/below the Street estimate.

Guard:

- In `Sales $X Beat/Miss $Y Estimate`, accept `$X`, reject `$Y`.
- In body text, accept values after "reported quarterly sales of", "reported ... sales of", or "quarterly revenue came in at/of".
- Reject values governed by "consensus estimate", "Street estimate", "Analysts expect", "estimate of", "versus consensus".

### Risk: stale prior-quarter or prior-year values

Observed evidence:

- AA preview has "Last quarter" and a historical EPS table with Q2 2025, Q1 2025, Q4 2024, Q3 2024.
- AA forecast compares consensus revenue to `$2.9 billion a year earlier`.
- AA standard wire compares current sales to `$2.904 billion the same period last year`.
- ABBV standard wire compares current sales to `$14.460 billion the same period last year`.
- ABNB standard wire compares current sales to `$3.732 billion the same period last year`.

Guard:

- Reject sentences or table rows with "last quarter", "past performance", "year earlier", "year-ago", "same period last year", or old quarter labels when the target is current actual.
- Require the sentence to match the target period when possible, for example Q3 2025.
- Prefer the first current-reporting sentence over historical comparison sentences.

### Risk: previews look like earnings articles but contain estimates

Observed evidence:

- AA `A Peek at Alcoa's Future Earnings` is in `Earnings`, but it says Alcoa "will release" results and gives expected EPS.
- AA `Earnings Are Imminent` is in `Earnings`, `Price Target`, and `Analyst Ratings`, but says "Analysts expect" and gives a consensus revenue estimate.

Guard:

- Downrank articles with "will release", "ahead of", "future earnings", "are imminent", "analysts expect", and "forecast" for actual extraction.
- If release timestamp is available, treat pre-release articles as estimate-only unless the article clearly says "reported".
- Keep these articles only for estimate targets, not actual targets.

### Risk: multiple real values in one article

Observed evidence:

- AA mover recap has quarterly revenue, Street estimate, production, shipments, segment revenue, total third-party revenue, and stock price.
- ABBV broader recap has company sales, consensus, dividend, immunology sales, product sales, neuroscience sales, fiscal-year EPS guidance, analyst valuation, and stock price.
- ABNB mover recap has quarterly revenue, Street estimate, gross booking value, adjusted EBITDA, shareholder-letter growth rates, Q4 revenue guidance, and stock price.

Guard:

- Require the metric noun and company-level scope near the value.
- Reject values near segment/product names unless the target asks for that segment/product.
- Reject values near "stock", "price target", "dividend", "EPS", "GBV", "EBITDA", "production", "shipments" when target is revenue.
- For company-level revenue, prefer sentences with "company reported", "quarterly revenue", or "reported quarterly sales".

### Risk: rounded values and exactness mismatch

Observed evidence:

- ABBV standard wire says `Sales $15.776B`; ABBV broader recap says `$15.78 billion`.
- AA standard wire says `$2.995B`; AA mover recap says `$2.99 billion` and later `$3 billion`.
- ABNB standard wire says `$4.095B`; ABNB mover recap says `$4.09 billion`.

Guard:

- Return the exact verbatim value from the selected article, not a normalized value as if it appeared in the text.
- If matching to a filing value, prefer the article sentence with the most precise form, usually the standard beat/miss wire.
- Treat rounded forms as lower confidence unless the task only needs a quote containing the metric value.
- Store both the raw quote and normalized numeric value so exact wording is not lost.

### Risk: paywalled or truncated teaser-only data

Observed evidence:

- Standard-wire teasers for AA, ABBV, and ABNB are truncated before the full article text.
- The teaser begins with EPS and may not include the sales sentence.

Guard:

- Do not extract from a cut-off teaser unless the value and full governing phrase are present.
- Prefer title and body over teaser when body exists.
- If only teaser is available and the sentence is incomplete, return no extraction rather than guessing.

### Risk: AI-generated article disclaimers

Observed evidence:

- No explicit AI disclaimer appears in the 8 samples.
- The AA preview has a templated style, but that is not proof of AI generation.

Guard:

- If a future article has an AI/automation disclaimer, require the same source-sentence evidence as any other article.
- Do not lower precision rules just because the article is in an `Earnings` channel.
- Treat generated preview/table text as lower confidence for actual results unless it clearly says the company reported the value.

### Risk: PR-wire reposts

Observed evidence:

- No clear PR-wire repost is visible in the 8 samples.

Guard:

- This is a brief-provided risk, not a sample-observed one.
- If an article is a repost or lightly edited press release, still require target period, company scope, metric noun, and actual-result verb.
- Watch for stale boilerplate and guidance sections; reject values in forward-looking sections unless the target is guidance.

### Risk: channel overconfidence

Observed evidence:

- All 8 samples have `Earnings`, but the brief says only 13/18 present values are in `Earnings` articles.
- AA forecast article has `Earnings` but contains estimates, not actuals.

Guard:

- Use channels as a prior, not a rule.
- Never accept a value because of channel alone.
- Never discard a candidate only because it lacks `Earnings`, especially analyst/price-target/mover/market articles.

## 4. Verdict on achievable recall

Near-100% recall across all test cases is not achievable from news alone.

Measured ceiling from the brief:

- News contains the value anywhere for 18/34 cases.
- Therefore the maximum possible recall over all 34 cases using news alone is 18/34, or 53%.
- No retrieval or ranking design can recover the 16/34 cases where the value is not present in news.

Near-100% recall-of-present is also unlikely with a precision-first reader.

Measured constraints:

- Current ranking finds 10/18 present values, or 56% recall-of-present.
- `Earnings`-only retrieval has a 13/18 ceiling, or 72% recall-of-present.
- Channel priority can remove the `Earnings`-only ceiling, but it cannot remove extraction ambiguity.

Observed structural issues in samples:

- Actual revenue can be in title and first body paragraph, as in standard beat/miss wires.
- Actual revenue can be only in body, as in AA and ABNB mover recaps.
- Actual revenue can be rounded differently across articles, as in ABBV `$15.776B` versus `$15.78 billion`.
- The same article can mix actuals, estimates, prior-year values, segment values, guidance, stock prices, and price targets.
- Preview articles can look like earnings articles but contain no current actual revenue.

Honest estimate:

- The proposed design should materially improve recall-of-present from 10/18.
- A reasonable target is about 14-16/18 present values, or 78-89%, for cases shaped like the samples and brief.
- This number is a hypothesis grounded in the sample patterns and brief census, not a measured result.
- Pushing beyond that likely requires manual review, source-specific parsers, exact release timestamps, stronger article-body access, and acceptance of more false-positive risk.

Bottom line:

- Use news as a high-precision fallback source, not as a complete recall source.
- Use `Earnings` and related channels to rank first, but keep non-Earnings analyst/price-target/mover candidates.
- Expect clear wins on standard beat/miss wires and market-reaction recaps.
- Do not promise near-100% recall, especially under precision-first rules.
