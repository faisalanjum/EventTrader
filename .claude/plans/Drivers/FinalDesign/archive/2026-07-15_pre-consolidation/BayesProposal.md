# Bayesian Event-Level Learning Proposal

> **STATUS: UNVETTED PROPOSAL FOR REVIEW ONLY**
>
> **This is NOT approved, NOT locked, NOT part of FinalDesign, and NOT an
> implementation instruction. Do not build it unless the owner accepts it after
> adversarial review and the proposed experiment passes.**
>
> Purpose: give independent reviewers enough context to decide whether this is
> a high-value learning design or unnecessary complexity.

## 1. Proposal In One Sentence

After an event's return is known, deterministic code should create **one
learning example for the complete event** and use a tested joint statistical
model, potentially hierarchical Bayesian, to estimate future return
distributions and uncertainty; it must never update each Driver independently
as if each Driver owned the event's full return.

## 2. Decision Being Requested

Reviewers should decide separately whether to accept:

1. **The event-level learning boundary:** one company + one event + one return
   window is one observation containing every Driver that fired.
2. **The Bayesian candidate:** a hierarchical model is worth testing against
   simpler uncertainty-aware baselines.

The first can be correct even if the second is rejected. This proposal does
not claim that Bayesian methods must win.

## 3. Goal And Existing Boundary

The Driver system records reusable causes and dated facts:

- `Driver`: the reusable cause.
- `DriverUpdate`: what happened to that cause in one event.
- `EXPLAINED_BY`: a producer's post-event attribution judgment, including
  direction, force, and confidence.
- Return layer: what the stock, market, sector, and industry actually did.

The desired downstream question is:

> Given the Drivers visible now, their states, the company, and the surrounding
> conditions, what return distribution should we expect, and how uncertain is
> that estimate?

This proposal concerns that downstream learning question. It does **not**
change Driver identity, DriverUpdate identity, fields, graph edges, extraction,
or catalog admission.

## 4. Why The Observation Must Be The Whole Event

One event can contain several opposing Drivers but produces only one net
return.

```text
Event 101
  guidance cut       -> downward pressure
  cost improvement   -> upward pressure
  CEO resignation    -> downward pressure

Observed company return: -6%
```

The following training conversion is false:

```text
guidance cut       -> -6%
cost improvement   -> -6%
CEO resignation    -> -6%
```

It gives the same outcome to three facts, double/triple-counts one event, and
labels the cost improvement as harmful merely because stronger forces won.

The correct observation is:

```text
[guidance cut + cost improvement + CEO resignation + context] -> -6%
```

Across many events with different combinations, a joint model can estimate
conditional associations. It still cannot observe a true causal share for each
Driver. This matches the locked rule in `07_DriverUpdate.md` DU-23: reality
provides one net return, so verdicts are graded as a set, never against a known
per-Driver true share.

## 5. Why Sample Count Alone Is Not Enough

The motivating failure is simple:

```text
Pattern A: 2 independent events, both negative
Pattern B: 200 independent events, 140 negative
```

A flat view may make A's 100% look stronger than B's 70%. A simple 95% Wilson
interval already shows the difference:

```text
2 / 2 negative:       plausible rate roughly 34% to 100%
140 / 200 negative:   much narrower uncertainty around 70%
```

Therefore, Bayesian methods are **not required** merely to distinguish two
observations from two hundred. A Bayesian model earns its complexity only if
joint modeling, partial pooling, and full predictive uncertainty improve unseen
future predictions beyond simpler methods.

## 6. Evidence From The Current Repository

These facts explain feasibility and risk. They are not the reason for the
proposal; the event-level argument remains true even if the Driver pipeline is
perfectly built.

Read-only inspection on 2026-07-09 found:

- Live graph: 0 `Driver`, 0 `DriverUpdate`, and 0 `EXPLAINED_BY` records.
- The planned EV1 scorer is not built, and current production prediction,
  learning, and scoring result files are absent.
- The return substrate is promising: 10,831 earnings 8-K events across 792
  tickers have daily stock, market, and sector returns; 10,823 also have
  industry returns.
- A typical ticker has about 13 such earnings events, so exact
  company-by-Driver cells will remain sparse even after backfill.
- Observed earnings returns are heavy-tailed: approximately -77% to +85%, with
  1st/99th percentiles near -27%/+29%. A plain normal-error model is unsafe.

The older risk/news experiment is useful as a warning, not as training truth:

- `driver_strategy_results.json` has 251 company-by-risk cells; median count is
  13 and 70 cells have only 3-5 matches.
- `driver_strategy_scan.py` counts matched **articles**, not independent events,
  and caps each search at 100.
- Baxter's three matched M&A articles represent two trading days; Crocs' four
  matched articles represent two days.
- Some matches are semantically wrong, such as a guidance-cut headline matched
  to a tariff category.
- The study scans 5,005 pairs and ranks extremes, creating a multiple-testing
  and selection problem.

A Bayesian formula cannot repair duplicated or mislabeled observations. It can
make them confidently wrong.

## 7. Exact Placement In The Event Cycle

This is a **post-outcome statistical layer**. It runs after the Driver and
return foundations, then feeds a later prediction.

```text
Driver Catalog + DriverUpdate pipelines
                  |
                  v
          Current prediction
                  |
                  v
          Market return becomes known
                  |
                  v
   Current Learner / verdict production completes
                  |
                  v
  NEW: code builds one event learning example
                  |
                  v
  NEW: mathematical model updates automatically
                  |
                  v
          Next prediction reads the model
```

For earnings, the clean operational trigger is after the current learner and
return/scoring artifacts are complete. For news/DCM, it is after the chosen
return window closes and the `DailyCompanyMoveEvent` is ready.

The example can be recorded immediately. A joint model should initially refit
in batch, such as nightly or after a configured number of new examples. Do not
build online MCMC or an event-by-event state machine for the first version.

### Hard live-use prerequisite

> **Owner clarification (2026-07-09):** the planned DriverUpdate producer runs
> before the event return is known. Therefore, this proposal requires no change
> to Driver, Driver Catalog, or DriverUpdate meaning/schema/timing. Build-time
> verification must still prove that historical backfill and live production
> use the same outcome-blind rules and that the producer cannot read return
> fields.

At the next prediction cutoff, the system must be able to encode the current
event into the **same Driver/state/context feature shape** used during training,
without seeing its future return.

The feature producer must also be **outcome-blind** in both history and live
operation. If a post-event Learner saw the realized return before choosing
which DriverUpdates to create or emphasize, that selected Driver set cannot be
used as predictive training input. It must be re-extracted through the same
return-blind path available before a live prediction. Otherwise hindsight has
entered the features even when every source timestamp looks PIT-safe.

If current-event Driver facts exist only after the post-outcome learner runs,
then the model cannot make an event-specific live prediction. The downstream
design must provide either:

- PIT-safe current-event DriverUpdates before the outcome, or
- a transient, PIT-safe current-event encoder with exactly the same feature
  contract.

No outcome-blind train/live feature parity means **BLOCKED**, regardless of
backtest quality. This proposal does not silently invent that missing path.

## 8. Ownership By Layer

| Layer | Owns |
|---|---|
| Driver graph | What happened and where the fact came from |
| Return layer | What the stock and benchmarks did in defined windows |
| LLM learner | Sourced qualitative attribution and explanation |
| New statistical layer | Repeated-event patterns and mathematical uncertainty |
| Predictor | Final forward-looking judgment and any `no_call` decision |

The LLM does not perform Bayesian arithmetic. Normal code runs the model. The
mathematical learner itself adds no LLM calls or token cost. Current-event
Driver extraction is an existing/independent prerequisite; any new LLM call to
create those features would require separate review.

## 9. Minimal Learning Example Contract

Working name: `driver_event_example.v1`. This name and exact storage path are
not locked.

One row represents:

```text
one company x one explained event/target x one defined return window
```

Suggested logical shape:

```json
{
  "schema_version": "driver_event_example.v1",
  "example_id": "<deterministic id>",
  "company_id": "<stable id>",
  "event_id": "<Event or DailyCompanyMoveEvent id>",
  "event_group_id": "<one real company reaction group>",
  "event_time": "<public source time>",
  "prediction_cutoff": "<latest allowed input time>",
  "return_window": {
    "id": "<fixed window id>",
    "version": "<return calculation version>"
  },
  "drivers": [
    {
      "driver_id": "<canonical Driver id/name>",
      "driver_state": "<state>",
      "fact_type": "<metric|guidance|surprise|action_event>",
      "fact_scope": "<structured scope>",
      "numeric_shape": "<source-faithful normalized feature block>"
    }
  ],
  "context": {
    "market_session": "<pre|in|post market>",
    "industry": "<known before cutoff>",
    "pre_event_stock_momentum": "<value or null>",
    "pre_event_stock_volatility": "<value or null>",
    "pre_event_market_regime": "<structured values>",
    "pre_event_sector_regime": "<structured values>",
    "rates_vix_fx_commodity": "<small PIT-safe relevant set>"
  },
  "outcome": {
    "raw_return": "<signed value>",
    "macro_adjusted_return": "<signed value or null>",
    "sector_adjusted_return": "<signed value or null>",
    "industry_adjusted_return": "<signed value or null>"
  },
  "quality_flags": ["<overlap, halt, missing, contamination, etc.>"],
  "versions": {
    "example_builder": "<version>",
    "driver_read_rules": "<version>",
    "context_sources": "<version>"
  }
}
```

This is a rough logical contract, not a request to add all fields immediately.
Only features with a prediction-time consumer and proven PIT availability
should survive implementation review.

### Required row rules

1. Count the event once. Articles, quotes, and DriverUpdates are not separate
   return observations.
2. Include the complete Driver set for the target; do not create one row per
   Driver.
3. Include all eligible occurrences, including small/no-move and no-verdict
   events. Training only on significant or attributed moves inflates effects.
4. Duplicate articles/source records may remain, but all records describing one
   real company reaction share one `event_group_id` and contribute a combined
   evidence count of one. Perfect semantic deduplication is not required.
5. Every input feature must have been knowable by `prediction_cutoff`.
6. Driver feature presence must come from an outcome-blind producer. A
   post-return Learner's hindsight-selected Driver set is not a legal training
   feature set.
7. Post-event benchmark returns may calculate outcomes but cannot enter the
   input context.
8. Overlapping catalysts, halts, missing prices, and unclear windows remain
   visible as flags; they never disappear silently.
9. `EXPLAINED_BY.weightage` and `.confidence` are producer judgments, not true
   labels. Exclude them from the first predictive model. Test them later only as
   candidate features, never as fractional truth.
10. A missing `EXPLAINED_BY` edge does not mean a negative label.
11. Rebuilding the same example inputs with the same versions must give the
    same row.

### Initial market-context set

For v1, attach only this fixed context known before the return:

```text
S&P return in the last completed market session
sector return in the last completed market session
company return over the prior 20 trading days
company realized volatility over the prior 20 trading days
VIX at the latest completed close
event session: pre-market, in-market, or after-hours
```

Example: an event carrying `revenue_guidance: lowered -5%` and
`revenue_surprise: beat +3%` may react differently when the company's prior
20-day return is +18% and VIX is 28 than when the stock is flat and VIX is 14.

Rates, oil, FX, commodities, technical indicators, and alternate windows remain
out of v1. Add one only when it has a clear Driver-related mechanism and
repeatedly improves future-date tests.

## 10. Recommended Initial Outcome

To remain aligned with the current predictor/EV1 target, use the existing
report-window **raw stock return** as the pre-registered primary outcome.

Keep macro-, sector-, and industry-adjusted returns as secondary outcomes and
diagnostics. Do not select whichever outcome looks best after seeing the test
set. A later approved design may change the primary target, but it must do so
before the next frozen evaluation.

## 11. Mathematical Model Candidate

The recommended candidate is a robust hierarchical joint return model.

Plain meaning:

- It predicts the whole event return from all Drivers and context together.
- Rare Driver/state estimates stay close to a conservative shared baseline.
- As independent events accumulate, the Driver/state estimate relies more on
  its own evidence.
- It produces a probability distribution, not only one average.

Rough form:

```text
event_return_i ~ StudentT(df, expected_return_i, event_scale_i)

expected_return_i = context_baseline_i
                  + sum of conditional Driver/state effects in event i
```

Each Driver/state effect receives a population prior. The minimal safe version
shrinks rare effects toward the global/context baseline. It must not assume two
Drivers have the same economic effect merely because their names or embeddings
look similar.

Existing, validated graph relationships may later define additional pooling
levels, but only if walk-forward tests prove the grouping helps. Industry,
company, Driver interactions, and time-varying effects should be added one at a
time, not all at launch.

The Student-t outcome is proposed because observed returns are heavy-tailed.
The exact likelihood, priors, and hierarchy are experiment questions, not
locked facts.

The model's predictive distribution directly supplies:

```text
P(return > 0)
expected return
median return
10th/90th or other prediction bounds
uncertainty width
unique event count supporting the estimate
```

If trading costs or a material-move threshold matter, also derive
`P(return > threshold)` and `P(return < -threshold)`. Do not redefine success
after looking at test results.

## 12. Predictor-Facing Output

The predictor should receive a compact, code-generated, PIT-safe summary, not
the training rows or future outcomes. Working shape:

```json
{
  "model_version": "<id>",
  "trained_through": "<timestamp before prediction cutoff>",
  "matched_unique_events": 37,
  "probability_up": 0.31,
  "expected_return_pct": -1.7,
  "prediction_interval_pct": [-5.2, 2.4],
  "uncertainty": "medium",
  "unseen_drivers": ["new_ai_regulation"],
  "validation_summary": "60-70% calls realized 64%; 80% intervals covered 78%",
  "warnings": ["industry interaction weakly supported"]
}
```

This is supporting evidence for the Predictor, not a forced trade and not a
replacement for current-event facts. The Predictor retains `no_call` and must
not convert a narrow-looking model interval into certainty.

If a new Driver appears before retraining, its exact learned effect is unknown.
The model uses the conservative population baseline for that effect, widens the
return range, and flags the Driver. The Predictor LLM receives the known-input
model estimate, the new DriverUpdate's grounded facts, and relevant
future-tested calibration/coverage. It may adjust confidence or return
`no_call`. The model later learns only from the realized event row, never from
the LLM's guess.

Per-Driver contribution estimates may be exposed later for diagnostics, but
must be labeled **conditional model contributions, not causal shares**.

## 13. Storage And Mutation Boundary

Do **not** add posterior means, win rates, sample counts, or uncertainty fields
to:

- `Driver`
- `DriverUpdate`
- `EXPLAINED_BY`

Those objects record evidence and judgments. Model beliefs change when the
training cutoff, context, outcome window, prior, code, or repaired facts change.

Store examples, model versions, and evaluations as separate code-owned derived
artifacts. Illustrative module split:

```text
scripts/driver_learning/
  build_examples.py
  fit_baselines.py
  fit_bayes.py
  evaluate_walk_forward.py
  read_prediction_summary.py

<derived artifact root>/driver_learning/
  examples/
  models/
  evaluations/
```

Paths and file formats are implementation decisions. No new graph node or edge
is required for the experiment.

Keep DriverUpdate inputs in flexible long/list form rather than permanent
columns:

```text
event_101 | revenue_guidance  | lowered | -5 | percent
event_101 | revenue_surprise  | beat    | +3 | percent
event_102 | new_ai_regulation | announced | null | null
```

Training code creates a temporary sparse matrix for each model version. New
Drivers therefore do not require graph or database schema changes.

The current environment has SciPy but no PyMC, Stan, NumPyro, scikit-learn, or
statsmodels. Do not add a large probabilistic-programming dependency until the
experiment design is approved. A simple baseline can be written first; the
Bayesian arm may use a reviewed offline engine later.

## 14. Feedback-Loop Safety

The statistical model must not train on its own beliefs.

- Train on PIT-visible Driver facts, context, and objective return fields.
- Generate historical and live Driver feature presence through the same
  outcome-blind path; never train on hindsight-selected facts.
- Do not convert the model's prior prediction into a Driver label.
- Do not treat the LLM's `EXPLAINED_BY` confidence as observed truth.
- Keep the attribution producer blind to model contribution estimates during
  the initial experiment, preventing self-confirmation.
- Include events whether or not the Predictor traded or made a directional
  call. Otherwise the model learns the policy's selection bias.
- A prediction may consume a prior model artifact only when that artifact was
  trained entirely on outcomes knowable before the prediction cutoff.

## 15. Smallest Decisive Experiment

Build the event examples once, freeze them, then compare on identical splits:

### Arm A: simple uncertainty baseline

- Unique-event counts.
- Smoothed directional rate.
- Wilson intervals.
- Simple mean/median and robust spread by Driver/state where possible.

### Arm B: regularized joint baseline

- One joint event model using all Driver activations and a small fixed context
  set.
- Regularization/shrinkage.
- Date/event-blocked bootstrap uncertainty.

### Arm C: hierarchical Bayesian candidate

- Same event rows and feature set as Arm B.
- Robust return likelihood.
- Partial pooling and posterior predictive distribution.

### Arm D: optional Random Forest challenger

- Use exactly the same DriverUpdate rows and six context fields.
- Apply the same chronological tests.
- State how direction probabilities are calibrated and how uncertainty is
  produced; trees do not supply a Bayesian posterior by default.
- If it predicts unseen events better and remains calibrated, it wins. The
  Bayesian candidate receives no preference for being Bayesian.

Do not let Arm C use richer inputs than Arm B. Otherwise the test measures
feature advantage, not Bayesian value.

### Split protocol

- Walk forward chronologically; never use a random row split.
- Keep same-date events together because market conditions correlate them.
- Keep every version of one underlying event in one fold.
- Pre-register model forms, priors, context fields, thresholds, and primary
  outcome before opening the final test periods.
- Use at least three non-overlapping forward test periods if data permits.
- Never re-pick the test set after seeing results.

### Primary evaluation

For direction probabilities:

- Brier score.
- Log loss.
- Calibration: forecasts near 70% should succeed near 70%.
- Precision at pre-registered long/short thresholds.
- Coverage/recall: how many eligible events receive an actionable probability.
- False high-confidence rate.

For the return distribution:

- Proper interval or distribution score.
- Mean/median absolute error.
- Coverage of 50%, 80%, and 95% prediction intervals.
- Bias and error by sparse/common Driver, ticker, industry, event session, and
  time regime.

Trading P&L after costs is secondary. It cannot replace calibration and proper
forecast scores because strategy selection can overfit a backtest.

## 16. Hard Proof Gates

### Gate 1: example correctness

Must prove with code tests and sampled audits:

- one underlying company-event-window is counted once;
- every Driver included belongs to that target and cutoff;
- historical Driver feature extraction was blind to the realized return and
  matches the live feature-producing path;
- every input timestamp is at or before the prediction cutoff;
- return windows align correctly for pre-market, in-market, and after-hours;
- duplicate articles do not increase effective sample size;
- no-verdict and small/no-move events are included;
- overlap and missing-data flags reconcile to source counts;
- same inputs and versions reproduce identical examples.

Any leakage or duplicate event group counted as more than one independent
observation is a hard failure. Duplicate source records themselves are legal
when grouped and counted once.

### Gate 2: model honesty

Must prove:

- prior and likelihood sensitivity do not materially reverse conclusions;
- posterior computation converges and passes predictive checks;
- uncertainty intervals have reasonable out-of-time coverage;
- rare Drivers remain uncertain instead of becoming extreme;
- the model does not become more confident merely from repeated articles or
  same-day correlated events;
- performance gains survive multiple forward periods and relevant subgroups.

### Gate 3: simpler-alternative test

Arm C must improve the pre-registered proper forecast scores over the strongest
non-Bayesian baseline/challenger on unseen forward periods. Use paired
date-blocked uncertainty around score differences.

If the Bayesian and regularized baselines are statistically and operationally
equivalent, choose the simpler baseline. Complexity receives no credit by
itself.

### Gate 4: train/live agreement

Must prove:

- the current event can be encoded with the training feature contract before
  its return exists;
- the same outcome-blind producer constructs historical and live Driver
  features;
- live feature distributions match replay feature construction;
- the model artifact cutoff is strictly earlier than the prediction cutoff;
- missing current inputs degrade explicitly rather than silently defaulting;
- the summary reaches the Predictor within the required latency;
- no LLM or token-consuming call is required for numerical updating.

### Gate 5: shadow production

Run without influencing predictions first. Compare shadow forecasts with the
existing Predictor over a pre-declared live period. Promote only after the
owner sees both accuracy and failure examples.

## 17. Promotion And Rejection Rules

Promote only if all are true:

1. Example correctness and PIT gates are clean.
2. Bayesian predictions beat both simple and regularized baselines on the
   frozen forward tests using proper scores.
3. Calibration and interval coverage improve or remain honest.
4. Gains do not come only from one ticker, industry, or regime.
5. The live event feature path is structurally identical to replay.
6. Operational cost, latency, and failure recovery are acceptable.

Reject or simplify if any are true:

- gains exist only in-sample or only in selected P&L;
- a regularized non-Bayesian model performs equivalently;
- posterior conclusions are highly prior-sensitive;
- context interactions make the model unidentifiable or unstable;
- the live predictor cannot supply the same Driver features;
- effect signs reverse across companies/regimes without enough data to model
  the interaction;
- the system must count articles, LLM confidence, or selected verdicts as
  independent truth to obtain a result;
- maintenance burden exceeds the measured forecast gain.

## 18. Main Failure Modes And Controls

| Failure | Required control |
|---|---|
| Several Drivers share one return | Joint event row and joint model |
| Duplicate/syndicated news inflates `n` | Underlying-event deduplication |
| Only large/attributed moves are learned | Include all eligible Driver events |
| Future context leaks into training | Field-level PIT cutoff checks |
| After-hours return assigned to wrong day | Versioned return-window resolver |
| Driver effect changes by company/industry | Context/interaction tests; wide uncertainty |
| Market regime changes | Walk-forward tests; rolling/decay tested later |
| Return outliers dominate | Robust likelihood and robust baselines |
| Wrong semantic pooling | Conservative global shrinkage; validated parents only |
| LLM grades itself | Do not use verdict confidence as truth; blind attribution arm |
| Backtest model selection | Frozen tests and proper scoring rules |
| Graph repair changes history | Rebuild a new versioned model artifact |
| Posterior mistaken for causality | Label outputs conditional associations |

## 19. Deliberately Deferred Complexity

The first experiment must not add:

- Bayesian fields on graph records;
- one posterior object per Driver in Neo4j;
- real-time MCMC after every event;
- a dynamic state-space/regime model;
- arbitrary embedding-based pooling between Drivers;
- large interaction grids;
- a new LLM judge or model call;
- a human review queue;
- trade execution outcomes flowing back as prediction evidence;
- a claim that posterior contribution equals causal effect.

Each can be reconsidered only after a simpler model exposes a measured need.

## 20. Alternatives Considered

### Keep only prior learner reports

Lowest implementation cost, preserves qualitative nuance, but has no
mathematical sample-size weighting or calibrated uncertainty.

### Wilson intervals / smoothed counts only

Excellent first baseline. Solves two-versus-two-hundred for direction but
cannot correctly handle several Drivers and context acting together.

### Regularized joint regression

Strong alternative and mandatory baseline. It may deliver most of the benefit
with less computation and easier operations. If it matches Bayesian results,
use it.

### Independent Beta-Binomial per Driver

Rejected. It assumes a separate binary outcome per Driver, double-counts
multi-Driver events, ignores magnitude/context, and can become confidently
wrong.

### LLM-only learned weights

Rejected as the numerical learning mechanism. LLM explanations remain useful,
but self-reported confidence is not calibrated statistical evidence.

### Deep learning over all events

Premature. Current structured Driver history does not exist yet, data is sparse
relative to Driver/context combinations, and uncertainty would be harder to
audit.

### Full causal model

Separate problem. Observational event returns and LLM attribution do not by
themselves identify causal effects. This proposal estimates conditional
predictive associations.

## 21. Why This Is The Strongest Candidate, If It Passes

This design is attractive because it:

1. Matches the real outcome boundary: one event produces one net return.
2. Uses all Drivers jointly instead of inventing per-Driver labels.
3. Distinguishes two events from two hundred through honest uncertainty.
4. Handles a large, sparse Driver catalog through conservative shrinkage.
5. Conditions effects on company and pre-event market context.
6. Produces direction, magnitude, and uncertainty in one distribution.
7. Keeps evidence in the graph and changing beliefs in derived artifacts.
8. Uses normal code, with no LLM token cost and no human loop.
9. Is falsifiable against simpler models before production integration.

It is **not** proven to be the best design until those tests pass. No model can
guarantee near-100% market prediction because important information can be
missing, reactions change, and some market movement is irreducible noise.

The proposal's strongest claim is narrower:

> If the system wants to learn numerical Driver effects from returns, whole
> events with joint Drivers and explicit uncertainty are the most defensible
> foundation; independent per-Driver updates are not.

## 22. Open Decisions The Experiment Must Resolve

- Exact primary return window and material-move threshold.
- Raw versus adjusted return as the long-term primary target.
- Smallest useful PIT-safe macro/context feature set.
- Exact Driver/state encoding and numeric scaling.
- Whether any existing family/industry relation is safe for partial pooling.
- Rolling window, time decay, or full history.
- Model engine and acceptable dependency footprint.
- Batch update cadence.
- Predictor-facing output shape and attention budget.
- Minimum history required before showing a model summary.
- Promotion effect-size and subgroup non-regression margins.

These must be pre-registered before the final held-out evaluation. They should
not be chosen because one option produces the best backtest.

## 23. Instructions To Independent Reviewers

Review this proposal as if the Driver Catalog and DriverUpdate pipeline were
perfectly built. Do not accept or reject it merely because current Driver data
is absent.

Please return `ACCEPT`, `MODIFY`, or `REJECT`, then answer:

1. Is one company-event-return-window the correct observation unit?
2. Is there a cheaper design that preserves joint effects and uncertainty?
3. Can the proposed model separate co-occurring Drivers with realistic data?
4. Which pooling assumptions are unsafe or unidentifiable?
5. Does the live predictor have a credible same-shape current-event feature
   path, or is this proposal blocked at integration?
6. Where can future data, outcome data, duplicated sources, or model feedback
   leak into training?
7. Are raw and adjusted return targets handled correctly?
8. Are the baseline arms strong enough to prove Bayesian value rather than
   feature advantage?
9. Which prior, likelihood, regime, or heavy-tail failure could make the model
   confidently wrong?
10. Are the proof and kill gates sufficient to reject overengineering?
11. What is the strongest concrete counterexample to the design?
12. What minimal change would make the proposal stronger without adding a new
    store, actor, LLM, or human review process?

Reviewers should distinguish:

- **high-confidence structural rules:** whole-event observation, PIT inputs,
  unique-event counts, no verdict-confidence-as-truth, derived model storage;
- **testable hypotheses:** Bayesian model advantage, hierarchy, context set,
  update cadence, effect size.

## 23A. Practical Driver/DriverUpdate Sequence

This compact sequence preserves the use case discussed with the owner. It is a
preparation and validation order, not an approved build plan.

Running example:

```text
Company/Event: AAPL Q2 earnings, after-hours

Outcome-blind DriverUpdates:
  revenue_guidance  | lowered   | -5 percent
  revenue_surprise  | beat      | +3 percent
  gross_margin      | decreased | -120 basis_points

Pre-event context:
  S&P last-session return       = -1.2%
  sector last-session return    = -1.8%
  company prior-20-day return   = +18%
  company prior-20-day vol      = 42%
  VIX latest completed close    = 28
  event session                 = after-hours

Outcome after the return window closes:
  company return                = -7%
  market-adjusted return        = -6%
  sector-adjusted return        = -5%
```

1. **Lock the first target.** Start with earnings, one company-event row, and
   the existing report-aligned raw stock return as primary outcome. Keep
   benchmark-adjusted returns secondary.
2. **Create the base event row.** Record company, Event/DCM target, public time,
   prediction cutoff, return-window version, and `event_group_id`; do not read
   the return yet.
3. **Attach all DriverUpdates.** Use every outcome-blind DriverUpdate for that
   company/event, including Driver, state, fact type, scope, value/change, and
   unit. Do not select only the apparently important Drivers.
4. **Attach the six pre-event context fields.** Use the fixed set in section 9;
   do not let an LLM choose different context per event.
5. **Attach outcomes after the window closes.** Add raw and benchmark-adjusted
   returns as labels, never as inputs.
6. **Encode DriverUpdates numerically.** Each Driver/state gets a presence
   value; add magnitude only when a compatible canonical unit exists. Missing
   magnitude is not numeric zero.
7. **Group repeated source records.** Five articles for the same AAPL reaction
   remain legal records but share one `event_group_id` and count as one event.
   Multiple real catalysts sharing one return remain together and are flagged.
8. **Split by time.** Older events train; later events validate; newest events
   remain untouched for the final test. Same-date events stay together.
9. **Scale numeric inputs from training data only.** Put VIX, returns,
   volatility, percentages, and basis-point features on stable per-feature
   scales. Never mix incompatible units.
10. **Build temporary model inputs.** `X` contains DriverUpdate and pre-event
    context features; `Y` contains the later event return. Keep source storage
    in flexible long/list form rather than permanent Driver columns.
11. **Fit the simple joint baseline.** Use regularized regression on the same
    `X` and `Y` that the Bayesian arm will receive.
12. **Fit the Bayesian candidate.** Use hierarchical Student-t regression on
    the same rows/features; code/Stan/PyMC performs the math, not an LLM.
13. **Validate honestly.** Code passes validation `X` into each fitted model,
    saves predictions, then compares them with separately held validation `Y`.
14. **Run the untouched final test.** Freeze features/models first. This decides
    whether any observed gain survived model adjustment.
15. **Run live in shadow mode.** Save forecasts for new events without letting
    them influence the Predictor; score after returns become known.
16. **Feed a proven summary to the Predictor.** Include probability, expected
    return, interval, uncertainty, event support, relevant calibration, and any
    unseen Driver warning. The LLM treats it as evidence, not a command.
17. **Keep learning forward only.** Append each completed event row, retrain in
    batches, publish a new model version, and allow the outcome to affect only
    later predictions.

For a new Driver such as `new_ai_regulation` appearing before retraining, the
fitted model cannot know its exact effect. It uses the conservative population
baseline with wider uncertainty and flags the Driver. The Predictor LLM reasons
from that DriverUpdate's grounded current-event evidence. After the return is
known, the event becomes the first real training evidence for the next model
version.

## 24. Local Anchors

- `07_DriverUpdate.md` DU-21..24: verdict meaning, one net return, aggregate
  grading, and no per-Driver true share.
- `11_TrackB_DriverUpdate_Census.md` T5: verdict fields and aggregate grading.
- `12_TrackB_FactPipeline.md`: Driver read/PIT modes and verdict writer plan.
- `FableAdmissionKernelDesign.md` section 9: return-signature bimodality can be
  legitimate across companies, such as oil producers versus airlines.
- `PredictorLearner/Final.md` sections 6, 8, 12, and 18: prior learner reports,
  learner boundary, methodology, EV1 Brier/calibration scoring.
- `scripts/driver_strategy_scan.py`: article-level counts, 100-hit cap, and
  current ranking formula.
- `scripts/massive_risk_data/risk_driver_methodology.md`: older risk/news
  experiment and small-sample win-rate claims.
- `scripts/earnings/earnings_orchestrator.py` `normalize_actual_return` and
  `fetch_actual_return`: existing raw and benchmark return fields.

## 25. External Statistical References

- Stan, hierarchical partial pooling for repeated binary trials:
  https://mc-stan.org/learn-stan/case-studies/pool-binary-trials.html
- Gelman et al., Bayesian Workflow (model checking is part of the method, not
  optional cleanup): https://arxiv.org/abs/2011.01808
- Gneiting and Raftery, Strictly Proper Scoring Rules, Prediction, and
  Estimation: https://doi.org/10.1198/016214506000001437
- Grunwald and van Ommen, Bayesian inconsistency under model misspecification:
  https://arxiv.org/abs/1412.3730
- Bailey et al., The Probability of Backtest Overfitting:
  https://escholarship.org/uc/item/4w1110bb
