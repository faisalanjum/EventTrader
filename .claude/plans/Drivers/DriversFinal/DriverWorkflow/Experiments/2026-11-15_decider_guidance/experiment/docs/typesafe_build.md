> ## Documentation Index
> Fetch the complete documentation index at: https://docs.typesafe.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# How to build with TypeSafe

> Design AI-powered software by keeping code in control and giving Jev narrow, structured decisions.

Jev is TypeSafe's model for building AI-powered software, not agents. It does not generate code or choose its own next action. It provides AI primitives that embed into software, so code remains in control while the model handles common-sense judgments over unstructured data.

> [!NOTE]
>
> **Summary:** build a normal software workflow and insert Jev only where AI is needed.
>
> * Keep control flow, deterministic rules, and side effects in code.
> * Break broad judgments into narrow, typed questions with explicit instructions and criteria.
> * Give each question only the context it needs.
> * Use probabilities and confidence to act, ask for review, or escalate.
> * Ask independent questions together, then compose their answers in code.

## Three software architectures

TypeSafe is designed for building **AI-powered software**, where code owns the workflow and AI handles narrow, structured decisions.

> [tab] Traditional software
>
> Traditional code is a complex decision tree made from simple software primitives. Because each primitive is reliable, developers can compose them into higher-level abstractions.

> [tab] LLM agents
>
> An agent processes instructions and chooses its next step. This works well when a person is monitoring the process, but every loop introduces another opportunity to go off the rails.

> [tab] AI-powered software
>
> Code handles deterministic work and owns the control flow. The model appears only where the system needs programmable common sense or needs to interpret unstructured data. Each AI task is kept atomic and constrained.

![Traditional software, agents, and AI-powered software shown as three different system architectures.](https://mintcdn.com/ts-docs/aFVnpmCIX68NpsV1/images/how-to-build-with-typesafe/software-architectures-light.webp?fit=max\&auto=format\&n=aFVnpmCIX68NpsV1\&q=85\&s=35c7622176190d1b1f19dc712f2fbf11)

## What makes Jev composable

> [card] Structured
>
> Jev is type-safe by construction. Decisions and probabilities conform to the structured software types and JSON schema your code expects, so it never has to recover a value from generated prose.

> [card] Parallel
>
> Questions are evaluated independently and in parallel. One primitive's result does not become hidden context that changes another primitive's result.

> [card] Comparable
>
> Outputs are sortable and can drive smart `if` statements, thresholds, and comparisons.

> [card] Fast
>
> Most calls complete in about 100 ms. Jev is fast enough for real-time request paths and user interfaces.

> [card] Calibrated confidence
>
> [RLCD](https://docs.typesafe.ai/introduction/machine-learning-primer.md) communicates uncertainty through calibrated probabilities instead of tending toward overconfidence.

> [card] Self-consistent
>
> Jev is designed to return stable answers across repeated evaluations. See the [self-consistency cookbook](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook.md).

Because every output is constrained to the supplied options, the model returns a full probability distribution over those options rather than inventing a value outside the schema. TypeSafe's target is a greater than 100× intelligence-to-speed-and-cost ratio; the underlying bet is that cheaper intelligence will create much more demand.

## Design a System One workflow

### 1. Use code when you can

Keep deterministic work in code. It is reliable and cheap. Avoid agent `while` loops when a software workflow can express the same behavior.

> [accordion] Example: keep deterministic rules in code
>
> ```python theme={null}
> days_overdue = (today - invoice.due_date).days
>
> if days_overdue > 30:
>     route_to_collections(invoice)
> ```

Browse the [System One patterns](https://docs.typesafe.ai/patterns.md) for bounded ways to compose model decisions with code.

### 2. Decompose the input state

Include only the context relevant to the current questions. This helps the model avoid distractions and context rot. Do not rely on knowledge stored in model weights when current information can come from your own knowledge base.

> [accordion] Example: send only relevant context
>
> Try it in the Playground →

### 3. Use structure in the input state

Use nested JSON for the `state` and `questions` fields. Point questions at specific values when that removes ambiguity, and include the backtick characters around each path inside the question.

> [accordion] Example: reference a nested value
>
> Use a backticked dot-and-index path to point a question at a specific nested value, such as `support.tickets[0].message`.
>
> Try it in the Playground →

### 4. Decompose the questions

Ask the most explicit, narrow, specific, atomic questions you can. Break down complex or ill-defined questions into separate questions that each evaluate one property.

> [!NOTE]
>
> This is probably the most important concept in this guide. Broad questions hide several judgments behind one answer. Atomic questions expose those judgments so you can inspect, tune, and combine them in code.

> [accordion] Example: decompose spam detection
>
> Try it in the Playground →
>
> Try it in the Playground →

> [accordion] Example: verify a tool-call trace
>
> Try it in the Playground →
>
> Try it in the Playground →

### 5. Use structure in the questions

Keep questions short. `instructions` and `criteria` are usually strings, and for a short, unambiguous question a string is all you need. They can also be objects or arrays. Put the question in one field and the data that guides the question in the others.

Structure helps in these situations:

* The question needs context or examples. A long sentence of background information or a list of example inputs belongs in named fields next to the question, where your code can add to them or swap them without rewriting the question.
* Part of the question comes from your code. When a value comes from a database, put it in its own field instead of splicing it into a string template.
* Several questions have similar instructions. A request takes one state and can include multiple questions. Adding supplementary data can help make questions distinct.

> [accordion] Example: reference a record from your code
>
> This Noul question compares a resume in the state against a record from a candidate database. The record goes into `potential_duplicate` as it is, and the question refers to it by name.
>
> Try it in the Playground →

The "potential\_duplicate" data sourced from code can change over time. The "question" references it using backticks.

The descriptions inside `criteria` can be objects too. For a Choice question, each option's description can be an object that says what the option covers, what belongs to a different option, and a few examples. Use the same field names across options so the model can compare them directly.

> [accordion] Example: define contrastive Choice criteria
>
> Try it in the Playground →

Each question type's page has a worked example:

* [Noul](https://docs.typesafe.ai/primitives/noul.md#structured-instructions) compares one resume against several candidate records, one question per record, with the questions built in code.
* [Choice](https://docs.typesafe.ai/primitives/choice.md#structured-instructions-and-criteria) describes two easily confused options with what each covers, what it's not for, and examples.
* [Score](https://docs.typesafe.ai/primitives/score.md#structured-level-descriptions) gives each level a description and example situations.

The [structured-data-extraction cascade cookbook](https://docs.typesafe.ai/cookbooks/sde_cascade.md) shows the shared-wording case, asking the same battery of questions about every field of an extracted record.

A short, unambiguous question or criterion can remain a string. Add structure when it separates guidance that would otherwise blur together. For the full set of places structure is accepted, see [Advanced: structure](https://docs.typesafe.ai/primitives/advanced.md).

### 6. Ask a lot of questions

Ask many narrow, independent questions about the same state in one request. This is how you maximize effectiveness and intelligence per dollar with the API: questions run in parallel, and code can combine their signals without adding serial model round trips.

See the [Speculative fan-out pattern](https://docs.typesafe.ai/patterns/fan-out.md) and [Parallel questions cookbook](https://docs.typesafe.ai/cookbooks/parallel_questions.md).

### 7. Combine question outputs in code (or feed into a classical ML model)

Combine independent answers with deterministic rules or weighted sums. For learned composition, use the probabilities as features in a downstream classical machine-learning model.

> [accordion] Example: combine signals with a weighted score
>
> ```python theme={null}
> answers = response.answers
>
> # Combine independent signals into one application-specific score.
> quality = (
>     0.4 * answers["answers_request"].noul
>     + 0.4 * answers["citations_are_supported"].noul
>     + 0.2 * (1 - answers["contradicts_context"].noul)
> )
> ```

[Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring.md) shows how to preserve individual judgments while combining them. If you do not have labels for a downstream model, use an ensemble of expensive reasoning models to generate them; the [AutoResearch cookbook](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md) shows how to train a classical model on Jev outputs.

### 8. Route on uncertainty

Make code take different actions for confident and unconfident answers. Escalate uncertain cases to a person or a more expensive reasoning model. Test thresholds by plotting confidence against accuracy on your data. For a Noul, a good starting point is 0.7 for yes and 0.3 for no; see [Reading a Noul](https://docs.typesafe.ai/primitives/noul.md#reading-a-noul).

> [accordion] Example: route by confidence
>
> ```python theme={null}
> answer = response.answers["card_help_topic"]
>
> if answer.confidence < 0.8:
>     route_to_human_review(ticket)
> else:
>     route_to_handler(answer.choice, ticket)
> ```

See [Confidence](https://docs.typesafe.ai/confidence.md) and [Routing by probability](https://docs.typesafe.ai/patterns/probability-routing.md) for choosing thresholds and matching them to the risk of each action.

> [!TIP]
>
> Decomposition does not require more round trips. Questions over the same state run in parallel.

## Putting it all together

This support-ticket workflow keeps deterministic work in code, sends only relevant structured context, evaluates many atomic questions in one request, and composes the answers with explicit confidence thresholds.

```python title="triage_ticket.py" theme={null}
from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeClient


def triage_ticket(ticket, customer):
    # Handle deterministic states without calling a model.
    if ticket["status"] == "closed":
        return "no_action"

    open_orders = [
        order for order in customer["orders"] if order["status"] != "delivered"
    ]

    # Include only the structured context needed by the questions below.
    state = {
        "ticket": {
            "message": ticket["message"],
            "sender": ticket["sender"],
            "links": ticket["links"],
        },
        "customer": {
            "plan": customer["plan"],
            "open_orders": open_orders,
        },
        "policy": {
            "sensitive_credentials": ["password", "security code", "API key"],
        },
    }

    # Ask structured, atomic questions together so they run in parallel.
    questions = {
        "topic": Choice(
            instructions={
                "question": "Which team should handle `ticket.message`?",
                "focus": "Classify the customer's primary request.",
            },
            criteria={
                "billing": {
                    "what": "Charges, invoices, refunds, or subscriptions",
                    "not_for": "Order tracking or account access",
                    "examples": ["I was charged twice", "Where is my refund?"],
                },
                "orders": {
                    "what": "Order status, delivery, cancellation, or returns",
                    "not_for": "Charges or account access",
                    "examples": ["Where is my order?", "Cancel my shipment"],
                },
                "account": {
                    "what": "Login, profile, permissions, or security",
                    "not_for": "Charges or order tracking",
                    "examples": ["Reset my password", "I cannot sign in"],
                },
            },
        ),
        "requests_credentials": Noul(
            instructions={
                "question": "Does the message request a sensitive credential?",
                "compare": [
                    "`ticket.message`",
                    "`policy.sensitive_credentials`",
                ],
                "focus": "Look for a request to disclose the credential itself.",
            },
            criteria=NoulCriteria(
                true={
                    "what": "Asks the recipient to disclose a listed credential",
                    "examples": [
                        "Reply with your password",
                        "Send us your API key",
                    ],
                },
                false={
                    "what": "Does not ask the recipient to disclose a credential",
                    "not_for": "A legitimate instruction to reset a credential",
                    "examples": ["Use this link to reset your password"],
                },
            ),
        ),
        "sender_identity_mismatch": Noul(
            instructions={
                "question": "Does the claimed sender identity conflict with its domain?",
                "compare": [
                    "`ticket.sender.display_name`",
                    "`ticket.sender.email`",
                ],
                "focus": "Compare the named organization with the email domain.",
            },
            criteria=NoulCriteria(
                true={
                    "what": "Claims an organization unrelated to the email domain",
                    "examples": ["Acme Payroll sent from claim-bonus.example"],
                },
                false={
                    "what": "The identity and domain agree or make no conflicting claim",
                    "examples": ["Acme Payroll sent from acme.example"],
                },
            ),
        ),
        "unexpected_reward": Noul(
            instructions={
                "question": "Does the message announce an unexpected reward?",
                "inspect": "`ticket.message`",
                "focus": "Look for an unsolicited prize, payment, or reward claim.",
            },
            criteria=NoulCriteria(
                true={
                    "what": "Announces an unrequested prize, payment, or reward",
                    "examples": ["You were selected for a $1,000 bonus"],
                },
                false={
                    "what": "Contains no reward claim or discusses an expected payment",
                    "not_for": "A customer asking about a known refund or payroll deposit",
                    "examples": ["When will my approved refund arrive?"],
                },
            ),
        ),
        "refund_requested": Noul(
            instructions={
                "question": "Does the customer explicitly request a refund or credit?",
                "inspect": "`ticket.message`",
                "focus": "Require a requested remedy, not a billing complaint alone.",
            },
            criteria=NoulCriteria(
                true={
                    "what": "Directly asks for money back or an account credit",
                    "examples": ["Please refund the duplicate charge"],
                },
                false={
                    "what": "Does not ask for a refund or credit",
                    "not_for": "A complaint or billing question without a requested remedy",
                    "examples": ["Why was I charged twice?"],
                },
            ),
        ),
        "mentions_open_order": Noul(
            instructions={
                "question": "Does the message refer to a supplied open order?",
                "compare": [
                    "`ticket.message`",
                    "`customer.open_orders`",
                ],
                "focus": "Match an order id or other identifying details.",
            },
            criteria=NoulCriteria(
                true={
                    "what": "Refers to an open order by id or identifying details",
                    "examples": ["Where is order A-104?"],
                },
                false={
                    "what": "Does not identify any supplied open order",
                    "not_for": "A generic order question with no matching details",
                    "examples": ["How long does shipping usually take?"],
                },
            ),
        ),
        "frustration": Score(
            instructions={
                "question": "How frustrated does the customer appear?",
                "inspect": "`ticket.message`",
                "focus": "Judge expressed frustration, not issue severity.",
            },
            criteria=[
                {
                    "what": "Calm and matter-of-fact",
                    "signals": ["Neutral wording", "No complaint about the experience"],
                },
                {
                    "what": "Frustrated but civil",
                    "signals": ["Expresses annoyance", "Remains constructive"],
                },
                {
                    "what": "Very angry or threatening to leave",
                    "signals": ["Hostile language", "Threatens cancellation or churn"],
                },
            ],
        ),
    }

    with TypeSafeClient() as client:
        response = client.system_one(
            state=state,
            questions=questions,
        )

    # Compose independent spam signals with weights controlled by code.
    answers = response.answers
    spam_risk = (
        0.45 * answers["requests_credentials"].noul
        + 0.30 * answers["sender_identity_mismatch"].noul
        + 0.25 * answers["unexpected_reward"].noul
    )

    # Escalate uncertain judgments instead of guessing.
    spam_is_uncertain = 0.4 < spam_risk < 0.6
    if spam_is_uncertain or answers["topic"].confidence < 0.75:
        return route_to_human_review(ticket)
    if spam_risk >= 0.6:
        return quarantine_as_spam(ticket)

    # Let code decide which speculative answers matter on this path.
    if answers["topic"].choice == "billing":
        return route_to_billing(
            ticket,
            refund_requested=answers["refund_requested"].noul >= 0.7,
        )
    if answers["topic"].choice == "orders":
        return route_to_orders(
            ticket,
            mentions_open_order=answers["mentions_open_order"].noul >= 0.7,
        )

    priority = (
        "high"
        if answers["frustration"].confidence >= 0.7
        and answers["frustration"].score >= 1.5
        else "normal"
    )
    return route_to_account_support(ticket, priority=priority)
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.