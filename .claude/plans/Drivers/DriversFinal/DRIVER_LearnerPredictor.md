# Predictions and Driver histories

## Qualifying move

A move qualifies when the absolute difference between stock and SPY (S&P 500) returns over the same hourly, session or daily window is **at least 2.2 percentage points**. Use this single threshold for all move checks. Hourly and session checks require a timed source event. Without one, check the daily close-to-close move. Verify prices and windows before using returns for triggers or grading. [Driver rule 10.1](DRIVER_RULES.md) · [Return checks](EXPLAINED_BY.md#8-return-measurements--open-checks-for-the-next-bot)

## Predictor

Make a paper call at each earnings release. Any other newly public source version, including the earnings transcript, triggers a separate call if it yields a verified DriverUpdate matching the company’s watchlist, even while an earlier call is open. Holding, exiting or adding to a position is a separate trading decision.

Derive the watchlist from available `EXPLAINED_BY` links. Include a Driver while at least one link connects its update to that company’s qualifying close-to-close move. **(Tentative.)** An intraday crossing can trigger research. Each link records a judgment about the day.

- **Company-specific update.** Match its Driver and subject company to those of an update that explained the watching company’s move.
- **Shared update.** Match only shared entries for the same Driver. The source reader determines scope from the cited passage. A market-wide change triggers all matching watchers. An event limited to particular companies triggers only matching watchers the passage identifies as parties. If scope is unclear, keep the update without triggering a call.

Seal one graph record per company, triggering source ID and version, separately for live calls and for each replay. Multiple qualifying updates in one version and retries reuse that call. Separate publications may each qualify even when they repeat the same claim.

- Link the company and each DriverUpdate the Predictor relied on. Keep an immutable copy of the exact input shown, retrievable by the fingerprint on the prediction. **(Tentative.)**
- Record the directional call (buy, sell or no trade), reason, model and mode from the producing run (live or replay).
- Record the input cutoff, code-stamped save time, chosen horizon and fixed end time. The replay input cutoff is the simulated decision time.

### Input cutoff

Apply the cutoff to the evidence, watchlist and histories. Require proof the cited source version was public before the cutoff. A prior result requires a completed window and verified prices available by then. [Driver rule 7.6](DRIVER_RULES.md)

Each daily explanation keeps its actual save time (`created`) and the Learner’s evidence cutoff. Use a review only if its evidence cutoff is at or before the call’s input cutoff.

- **Live calls** use shared history built by live runs and historical backfills designated at launch. Read only prior calls, results and [explanations](EXPLAINED_BY.md#5-what-each-explanation-stores) available there when input closed. Backfill calls keep replay mode.
- **Replay calls** read shared history available at the simulated cutoff plus earlier completed steps from the same replay. Each replay retains one ID on its calls and Learner outputs across retries. Practice replays save judgments and withdrawals only in their own Learner outputs, using the same explanation key. For each key, the replay’s latest eligible decision takes precedence within that replay, including a withdrawal.

## Grading

Use the live save time or replay decision time to fix the end of the Predictor’s chosen hour, session or day when the call is saved. Enter at the first verified tradable price **after** that starting time. If entry is at or beyond the end, or either price is missing or unverified, leave the call ungraded. [Existing window calculations](../../../../eventReturns/EventReturnsManager.py)

Code saves the stock return once as `100 × (end price − entry price) / entry price`, rounded to two decimals. A buy wins if the saved return is positive, a sell if it is negative. Zero wins neither. For no trade, record the move skipped without a directional grade. Only live calls measure paper-trading performance.

## Learner reviews

| When | What to review |
|---|---|
| Every live call’s horizon ends | Briefly review the result, reason and original input, including for no trade. Keep feedback in the call’s Learner output. A deeper review due then for the same event covers both. |
| At the close of the first trading day after the qualifying window’s end date (Eastern time) | Investigate the move, even without a prediction or news. This close is the replay cutoff. |
| Earnings preview at the [evening calendar scan](../../../../k8s/processing/trade-ready-scanner.yaml) on the trading day before scheduled earnings | Use the release date known then. Revisit each qualifying move once at the first preview **after its initial review**, explained or unexplained. |
| After every earnings event | Live, review the results and transcript when the transcript arrives. In replay, stop just before the next earnings release or at the replay end, whichever comes first. If the release date was unknown at preview time, revisit moves still due a second look after their first. New evidence may correct an earlier explanation. |

Use only evidence available at the live review’s start or the replay cutoff. Process later disclosures on arrival. They can inform subsequent calls without reopening an old move. Discoveries from either agent follow the [normal DriverUpdate workflow](DRIVER_RULES.md).

Save supported daily explanations in the [run’s history](#input-cutoff). Update changed judgments or explicitly withdraw those the evidence no longer supports. Omission alone leaves them in place. Compare each uncited explaining update with the call’s original input and cutoff. Record whether it was shown but unused (possible oversight), public but absent (input gap), first public later, or of unknown timing.

## Driver histories

Calculate both histories on read for a company, its industry or its sector, each with its own count.

- **Call outcomes.** Count each graded buy or sell that relied on the Driver once. Show wins and total by horizon, with live and replay separate. Overlapping calls on one company can reflect the same stock move.
- **Daily explanations.** Count distinct affected company-days linked to the Driver. Keep each judgment’s direction and strength. An absent link leaves the effect unknown.
