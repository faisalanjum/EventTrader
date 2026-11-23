# Predictions and Driver histories

## Qualifying move

A move qualifies when the absolute difference between stock and SPY (S&P 500) returns over the same hourly, session or daily window is **at least 2.2 percentage points**. Use this single threshold for all move checks. Verify prices and windows before using returns for triggers or grading. [Driver rule 10.1](DRIVER_RULES.md) · [Return checks](EXPLAINED_BY.md#8-return-measurements--open-checks-for-the-next-bot)

## Predictor

Make a paper call at every earnings event. Between earnings, call when news updates a Driver on the company’s watchlist. For shared news, apply each affected company’s watchlist.

Derive the watchlist from available `EXPLAINED_BY` links. Include a Driver while at least one link connects its update to that company’s qualifying close-to-close move. An intraday crossing can trigger research. Each link records a judgment about the day.

Seal one graph record per call. Reruns reuse it.

- Link the company and each DriverUpdate the Predictor relied on. Keep an immutable copy of the exact input shown, retrievable by the fingerprint on the prediction.
- Record the directional call (buy, sell or no trade), reason, model and mode from the producing run (live or replay).
- Record the input cutoff, code-stamped save time, chosen horizon and fixed end time. The replay input cutoff is the simulated decision time.

### Input cutoff

Apply the cutoff to the evidence, watchlist and histories. Require proof the cited source version was public before the cutoff. A prior result requires a completed window and verified prices available by then. [Driver rule 7.6](DRIVER_RULES.md)

Each daily explanation keeps its actual save time (`created`) and the Learner’s evidence cutoff. Live calls use only prior calls and results available when input closed, and explanations already saved by then. Replay may also use earlier steps completed in that replay. In both modes, each review used must have an evidence cutoff at or before the prediction’s cutoff. [Explanation records](EXPLAINED_BY.md#5-what-each-explanation-stores)

## Grading

Use the live save time or replay decision time to fix the end of the Predictor’s chosen hour, session or day when the call is saved. Enter at the first verified tradable price **after** that starting time. If entry is at or beyond the end, or either price is missing or unverified, leave the call ungraded. [Existing window calculations](../../../../eventReturns/EventReturnsManager.py)

Code saves the stock return once as `100 × (end price − entry price) / entry price`, rounded to two decimals. A buy wins on a rise, a sell on a fall. Flat prices win neither. For no trade, record the move skipped without a directional grade. Only live calls measure paper-trading performance.

## Learner reviews

| When | What to review |
|---|---|
| Every live call’s horizon ends | Briefly review the result, reason and original input, including for no trade. Keep feedback in the call’s Learner output. A deeper review due then for the same event covers both. |
| The next trading day closes after a qualifying move’s window ends | Investigate the move, even without a prediction or news. This close is the replay cutoff. |
| Earnings preview at the [evening calendar scan](../../../../k8s/processing/trade-ready-scanner.yaml) on the trading day before scheduled earnings | Use the release date known then. Revisit each qualifying move once at the first preview **after its initial review**, explained or unexplained. |
| After every earnings event | Live, review the results and transcript when the transcript arrives. In replay, stop just before the next earnings release or at the replay end, whichever comes first. If the release date was unknown at preview time, revisit moves still due a second look after their first. New evidence may correct an earlier explanation. |

Use only evidence available at the live review’s start or the replay cutoff. Process later disclosures on arrival. They can inform subsequent calls without reopening an old move. Discoveries from either agent follow the [normal DriverUpdate workflow](DRIVER_RULES.md).

Save supported daily explanations. Update changed judgments or explicitly withdraw those the evidence no longer supports. Omission alone leaves them in place. Compare each uncited explaining update with the call’s original input and cutoff. Record whether it was shown but unused (possible oversight), public but absent (input gap), first public later, or of unknown timing.

## Driver histories

Calculate both histories on read for a company, its industry or its sector, each with its own count.

- **Call outcomes.** Count each graded buy or sell that relied on the Driver once. Show wins and total by horizon, with live and replay separate.
- **Daily explanations.** Count distinct affected company-days linked to the Driver. Keep each judgment’s direction and strength. An absent link leaves the effect unknown.
