> ## Documentation Index
> Fetch the complete documentation index at: https://docs.typesafe.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Confidence

> How Jev reports certainty, how it differs from probability, and how to use it to control system behavior.

All Score and Choice answers from Jev include a `probabilities` property representing the probability distribution across the options (for Choice) or levels (for Score). The *shape* of that distribution is what tells you how certain the model is: concentrated on one outcome means a confident answer, spread out means an uncertain one.

The answer's `confidence` property collapses that shape into a single number from 0 to 1. It is 1 when all the probability is on one outcome and 0 when the probability is spread evenly. (Noul answers don't carry one; see [Noul](#noul) below.) It describes how certain the answer is, but it isn't always the right number for your code to act on.

## Confidence is derived from the probabilities

`confidence` is a statistic computed from the probability distribution the answer already gives you. TypeSafe computes it for you and returns it on every Choice and Score answer, so the common case needs no extra work on your side.

Choice question with three options

See how probability distribution changes confidence

Confidence

Probability

Move a slider to change an option's probability. The other probabilities adjust to keep the total at 100%.

Clear winner
Spread out
Even split

<details>
  <summary>How this demo calculates Confidence</summary>

  TypeSafe computes confidence from how the probability is spread across the options. All of it on one option gives 1.0; the more evenly it spreads, the lower the confidence. With three options, the [Choice formula](#choice) is `(3 × largest probability − 1) / 2`, which is what this demo shows.
</details>

For a [Choice](https://docs.typesafe.ai/primitives/choice.md), the distribution is `probabilities` across your options. For a [Score](https://docs.typesafe.ai/primitives/score.md), it is the distribution across your levels. In both cases a flatter distribution means lower confidence: low confidence on a Choice often means none of the options are a clear winner over the others, and low confidence on a Score often means the levels are ambiguous, multi-dimensional, or the state doesn't contain enough to go on.

The exact formula for each question type is in [How confidence is calculated](#how-confidence-is-calculated), so you can see how any `confidence` value follows from the answer's own `probabilities`.

## "I don't know" is a useful signal

If an intelligent system, whether human or machine, cannot express honest uncertainty, the system cannot be trusted.

Confidence gives you a built-in mechanism for the model to say "I'm not sure about this one." This lets your code implement different behavior for different levels of certainty, which is the foundation for building systems you can actually rely on.

## Three paths for using confidence in your code

A useful starting pattern is to divide confidence into three ranges, each producing a different system behavior:

**High confidence:** Act automatically. The model has a clear read and you can proceed without human involvement.

**Medium confidence:** Proceed with caution. The model has a reasonable answer but is not certain. Depending on context, you might ask the user to confirm, flag for review, or gather more information before acting.

**Low confidence:** Do not act. Route to a human, request clarification, or fall back to a different system. The model is telling you it does not have enough information or the question is not a good fit.

Where you draw those boundaries depends on the stakes.

## Thresholds scale with risk

A confidence threshold is not one number. Different actions within the same system should use different thresholds depending on the consequences of getting it wrong.

```python theme={null}
response = client.system_one(
    state=user_message,
    questions={
        "action": Choice(
            instructions="What is the user trying to do?",
            criteria={
                "check_balance": "View account balance",
                "approve_transfer": "Approve the pending withdrawal request",
                "support": "Get help with an issue",
            },
        ),
    },
)

action = response.answers["action"]
confidence = action.confidence

if confidence < 0.5:
    # Model is genuinely unsure. Don't guess.
    route_to_human(user_message)

elif action.choice == "check_balance":
    # Low stakes. Showing the wrong screen is recoverable.
    show_balance(account_id)

elif action.choice == "approve_transfer":
    if confidence > 0.9:
        # High stakes, high confidence. Proceed with confirmation.
        confirm_then_execute(account_id)
    else:
        # High stakes, moderate confidence. Verify first.
        ask_user_to_confirm(account_id)
```

The 0.5 confidence floor catches anything the model reports as genuinely uncertain. Above that, the threshold for acting without confirmation is higher for a destructive operation than for a read-only one. Your code encodes the risk tolerance.

> [!NOTE]
>
> The correct threshold values depend on your domain and the performance of the model for your use case. Start with conservative thresholds, test with your own data, and adjust as you observe results.

## When to act on confidence

Confidence measures how concentrated the answer's probabilities are, which is different from the probability that the selected answer is correct. Before putting a threshold on it, decide what your code needs to know. For a Choice, a confidence of 0.5 corresponds to different top probabilities with two options vs. ten:

| Options | Top probability | `confidence` |
| - | - | - |
| 2 | 0.75 | 0.5 |
| 3 | 0.67 | 0.5 |
| 10 | 0.55 | 0.5 |

For a Choice question with a fixed number of options, confidence is a transformation of the top probability, so checking both adds no independent evidence. To distinguish a close runner-up from probability spread across many alternatives, inspect the other probabilities or the [top-to-second ratio](#choice).

What to put the threshold on instead:

* **For a Noul, the value itself.** It's already the probability that the statement is true. Good starting thresholds are 0.7 and 0.3: above 0.7 reads as yes, below 0.3 as no. Give the band between 0.3 and 0.7 its own outcome in code rather than rounding it to one side.
* **For a Choice, the probability of the option your code will act on.** It's the probability that the chosen option is correct, so a threshold on it is a statement about risk that anyone can read. In an answer with probabilities `{"check_balance": 0.05, "approve_transfer": 0.92, "support": 0.03}`, 0.92 is the probability that the user meant `approve_transfer`, and a rule that acts only above 0.9 says "act when the chance of the wrong option is under 10%". [Routing by probability](https://docs.typesafe.ai/patterns/probability-routing.md) sets a different threshold per action this way.
* **For a Score whose decision depends on one level, that level's probability.** The position can be between two levels and hide a split answer, where the probability is high on two separate levels. Probability on a neighboring level barely lowers confidence, so confidence doesn't show the split either ([When two levels split the answer](https://docs.typesafe.ai/patterns/confidence-routing.md#when-two-levels-split-the-answer)).

Check confidence first when your code needs to know whether a Score answer is settled at all. A Score's confidence measures how far the probability is from the most likely level, so it catches an answer spread across distant levels that the position alone doesn't. [Routing by confidence](https://docs.typesafe.ai/patterns/confidence-routing.md) checks confidence first and then routes on the score.

Confidence is also useful for comparing uncertainty across questions, because it's on the same 0-to-1 scale whatever the number of options or levels.

## How confidence is calculated

Each question type summarizes its distribution a little differently. A Noul has two outcomes, a Choice has any number of options in no particular order, and a Score's levels are ordered, so each formula below builds on the one before it.

TypeSafe's `confidence` is one reasonable way to summarize a distribution, not the only one. We return a fixed measure so that every answer comes with a sensible default: you can put a threshold on `confidence` from your first call, on the same 0 to 1 scale for every question, without first choosing and validating a statistic of your own. Because the formulas below are exact and every answer includes its full `probabilities`, you can compute whichever measure matters most to your application instead.

### Noul

A Noul answer is a single probability $p$ that the answer is yes, and TypeSafe returns no separate `confidence` for it. The probability already carries the uncertainty: a value near 0.5 is the model saying it is unsure. A good starting point is 0.7 for yes and 0.3 for no, and the [Noul](https://docs.typesafe.ai/primitives/noul.md#reading-a-noul) page covers when to move them.

If you want a confidence-style number anyway, for example to threshold Nouls and Choices with the same code, use the distance from 0.5:

$$
\text{confidence} = |2p - 1|
$$

This gives 0 at $p = 0.5$ and 1 at $p = 0$ or $p = 1$. It is also the Choice formula below applied to a yes-or-no Choice, so it sits on the same scale as Choice confidence.

### Choice

A Choice extends the same idea to any number of options. For a Choice with $n$ options, where $p_{\max}$ is the probability of the selected option:

$$
\text{confidence} = \frac{p_{\max} - \frac{1}{n}}{1 - \frac{1}{n}}
$$

This measures how far the top probability sits above an even split of $\frac{1}{n}$ per option, on a scale where the even split is 0 and certainty is 1. Only the top probability counts, so $(0.6, 0.3, 0.1)$ and $(0.6, 0.2, 0.2)$ both have confidence 0.4.

```python theme={null}
def choice_confidence(probabilities: list[float]) -> float:
    n = len(probabilities)
    return (max(probabilities) - 1 / n) / (1 - 1 / n)


choice_confidence(list(answer.probabilities.values()))
```

The [explorer at the top of this page](#confidence-is-derived-from-the-probabilities) uses this formula with three options.

Two simpler measures, computed from the same `probabilities`, are often very effective in practice and are worth trying alongside `confidence`:

* **Top probability**, $p_{\max}$. It reads directly as "how likely is the selected option", which makes thresholds easy to reason about. Its meaning depends on the number of options, since 0.5 is a weak answer among two options and a strong one among ten, so set its threshold per question.
* **Top-to-second ratio**, $p_{\max} / p_{\text{second}}$. It measures how clearly the selected option beats the runner-up and ignores how the rest is spread. Many real decisions come down to the top two candidates, and this ratio targets exactly that.

### Score

A Score's levels are ordered, so its formula also counts how far probability sits from the most likely level. For a Score with $n$ levels numbered $0$ to $n - 1$, where $p_i$ is the probability of level $i$ and $m$ is the most likely level:

$$
\text{confidence} = \max\left(0,\ 1 - \frac{\sum_i p_i \, |i - m|}{\text{MAD}_{\text{unif}}}\right)
\qquad
\text{MAD}_{\text{unif}} = \frac{1}{n} \sum_i \left| i - \frac{n - 1}{2} \right|
$$

The sum in the numerator is the probability-weighted average distance, in levels, between the answer and the most likely level. $\text{MAD}_{\text{unif}}$ is the same kind of average distance for an even spread across all levels, measured from the middle level. Confidence compares the two, and is floored at 0 when the answer is at least as spread out as an even spread.

Probability on a neighboring level lowers confidence less than the same probability on a level further away. With three levels, $(0, 0.5, 0.5)$ has confidence 0.25, because the model is torn between two adjacent levels. $(0.5, 0, 0.5)$ has confidence 0, because it is torn between opposite ends. The Choice formula would give both distributions 0.25.

Score question with five levels

See how distance between levels changes confidence

Confidence

Probability

Move a slider to change a level's probability. The other probabilities adjust to keep the total at 100%.

Clear peak
Split between neighbors
Split between ends
Even spread

<dl aria-live="polite">
  <dt>Score</dt><dd />

  <dt>Choice formula on the same probabilities</dt><dd />
</dl>

<details>
  <summary>How this demo calculates Confidence</summary>

  This demo uses the [Score formula](#score). It takes the average distance, in levels, between the answer and the peak, weighted by probability. It divides that by 1.2, the same average for an even spread over five levels measured from the middle level, and subtracts the result from 1, stopping at 0. Probability on a level next to the peak lowers confidence less than probability far from it, which the Choice formula does not take into account.
</details>

```python theme={null}
def score_confidence(probabilities: list[float]) -> float:
    n = len(probabilities)
    m = probabilities.index(max(probabilities))
    spread = sum(p * abs(i - m) for i, p in enumerate(probabilities))
    even_spread = sum(abs(i - (n - 1) / 2) for i in range(n)) / n
    return max(0.0, 1 - spread / even_spread)


levels = sorted(answer.probabilities)
score_confidence([answer.probabilities[level] for level in levels])
```

The `bug_severity` answer in the [Score response example](https://docs.typesafe.ai/primitives/score.md#response-structure) has probabilities $(0, 0.57, 0.43)$. The most likely level is 1, the spread is $0.43$, and $\text{MAD}_{\text{unif}}$ for three levels is $\frac{2}{3}$, so confidence is $1 - 0.43 / \frac{2}{3} \approx 0.35$.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.