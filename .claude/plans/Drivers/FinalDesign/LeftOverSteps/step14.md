# Step 14 — Optionally Qualify Cheaper Models After Closure

> **DORMANT under the 2026-08-14 Sonnet-5-only ruling.** No gate or model call
> in this file may run unless a future owner ruling permits a non-Sonnet
> candidate. Step 13 completion never waits for this file.

## Goal

Reduce measured model cost one production role at a time without changing the
finished system's meaning, code rules, prompts, contracts, safety, precision,
or recall.

Step 14 is optional. Step 13 already closes the complete system on qualified
strong models. Skipping Step 14, rejecting every candidate, or stopping after
one role leaves that accepted system complete.

## Required starting state

Do not begin until:

* Step 13 is complete, published, and owner-accepted;
* the exact strong-model release, model-role manifest, prompts, answer keys,
  tests, receipts, and quality results are frozen;
* the running system can be placed into no-write shadow for the role under
  test;
* no open defect, drift, outage, or missing evidence affects that role;
* a later owner ruling has reopened cheaper-model testing;
* the owner has selected one role and one candidate for the next comparison;
* every planned call is frozen inside one bounded packet.

## Authority

Apply the same owners used by the completed role:

1. `FINAL_DESIGN.md` for meaning and safety;
2. the live channel and internal contracts for input and output shape;
3. `BUILD_AND_OPERATIONS.md` for model, operation, rollout, and recovery law;
4. the Step 2 model-role memo and Step 13 release manifest for the accepted
   strong baseline;
5. the role's signed hidden-key, unseen-certification, and production tests.

This file authorizes no model, call, configuration change, activation, commit,
push, or graph write by itself.

## Strict scope

For one role, Step 14 may:

* compare one exact cheaper candidate with the accepted strong configuration;
* reuse the same prompt, schema, existing transport path, deterministic checks,
  and proof owners;
* run the candidate on locked regression cases and any fresh unseen cases the
  role's existing certification requires;
* measure quality, reliability, latency, and actual resource use;
* promote only the exact passing configuration after separate approval.

It must not:

* change product meaning, a prompt, answer key, sample truth, pass bar,
  contract, source query, deterministic guard, or production algorithm to help
  the candidate;
* add a model router, fallback, cascade, vote, second-pass rescue, provider
  substitution, role-specific wrapper, or parallel rule path;
* let a candidate create, see, or grade its own truth;
* tune on the unseen certification set and reuse that set as proof;
* promote a model into a role that the live design permanently reserves for a
  strong tier unless the candidate independently qualifies for that tier under
  the existing rule;
* test more than one role or one candidate at a time;
* modify graph data merely to run the comparison.

## Non-negotiable comparison rule

The accepted strong configuration is the control. The candidate receives the
same lawful information and must pass through the same code.

Cheaper means lower measured cost or resource use on the real approved
transport. It is not inferred from a model label. A claimed saving without raw
usage evidence is unknown.

Promotion requires no observed quality loss. A lower cost never excuses a
wrong acceptance, recall loss, invalid response, instability, or new park.

## Gate 14.0 — Select one bounded candidate

Derive the complete role list from the live Step 13 model manifest. Do not use
a hand-written list.

For the one selected role, freeze:

* the accepted strong model, version, effort, transport, prompt, and schema;
* one candidate model, version, effort, transport, and settings;
* the role's exact entry point, callers, outputs, refusal paths, and side
  effects;
* why the live design permits this role to be reconsidered;
* the existing quality bars and complete measured baseline;
* the expected calls, actual billing route, maximum spend, and stop conditions.

An alias, moving model name, unknown provider route, or unbounded spend stops
the gate.

## Gate 14.1 — Freeze independent evidence

Reuse the role's existing proof machinery. Add no framework unless it cannot
prove one named required behavior.

Freeze:

* every locked regression case used by the strong baseline;
* a fresh unseen set only where the role's existing certification requires
  one or the old set is no longer blind;
* the complete eligible denominator and required high-risk groups;
* independent truth and grading identities;
* exact precision, recall, wrong-accept, park, refusal, invalid, duplicate,
  stability, latency, and resource calculations;
* lawful positive controls, near misses, adversarial cases, permutations, and
  required mutations already owned by that role;
* proof that neither candidate nor strong output can alter the key or scorer.

The same evidence must grade both configurations. A case removed after seeing
candidate output invalidates the comparison.

## Gate 14.2 — Prove the unchanged execution path

Before a real candidate call, prove with saved replies that:

* the existing runner accepts the candidate through configuration alone;
* exact model and effort pins are recorded;
* raw replies are saved before parsing;
* both configurations receive byte-identical task content except the model
  slot and provider-required transport fields;
* every reply passes through the same parser, verifier, deterministic guards,
  accounting, audit, and no-write route;
* no hidden answer, future information, realized return, other producer answer,
  or grader conclusion reaches either model;
* an unavailable, changed, malformed, timed-out, or over-budget candidate
  stops rather than calling another model;
* the graph and live configuration remain unchanged.

If compatibility needs a new semantic adapter, prompt variant, or production
branch, reject the candidate instead of expanding the system.

## Gate 14.3 — Run one paired comparison

After the bounded call packet passes preflight:

1. recheck every frozen identity;
2. run the candidate once under the role's existing call law;
3. use the saved accepted strong results as the control, or rerun the strong
   configuration only when the existing proof requires a contemporaneous run
   and that run is included in the same frozen packet;
4. capture every raw request, response, error, retry, resource unit, latency,
   parsed result, deterministic outcome, grade, and abstention;
5. reconcile every expected case to exactly one terminal result;
6. replay both result sets through the same no-write production path;
7. report every difference individually before calculating totals.

Do not repair, rerun, or reinterpret a semantic failure. Transport retries may
occur only under the role's already-frozen retry rule and remain visible.

## Gate 14.4 — Apply the promotion test

The candidate passes only when all are true on the complete paired denominator:

* zero confirmed-wrong accepted fact, identity, link, source selection, or
  other role output;
* measured precision is no lower than the accepted strong baseline;
* measured recall is no lower than the accepted strong baseline;
* every existing role-specific safety and quality bar passes;
* invalid, duplicate, crash, timeout, instability, park, refusal, and
  abstention results are no worse than the baseline;
* every high-risk group and lawful positive control passes;
* every required attack and mutation is detected;
* the same prompt, schema, code path, and deterministic rules were used;
* actual resource use shows a real benefit worth the configuration change;
* an independent qualified reviewer confirms every semantic disagreement;
* no graph, source, cursor, cache, contract, or unrelated file changed.

Report confidence limits and every miss honestly. These results prove only the
measured role, model version, effort, transport, prompt, code, and population;
they are not a universal guarantee.

Any failed condition rejects the candidate. Keep the strong configuration and
do not tune against the same unseen set.

## Gate 14.5 — Promote one configuration safely

Promotion requires a separate owner decision tied to the exact evidence and
candidate identity.

If approved:

1. change only the single model configuration owner and mechanically derived
   manifests;
2. keep the strong configuration as a reviewed rollback choice, not an
   automatic runtime fallback;
3. run focused, full, isolated, mutation, no-write, and affected real-data
   regressions on the exact candidate;
4. rerun every Step 13 closure row whose evidence or identity changed, reusing
   only unchanged evidence whose exact binding remains valid;
5. run the candidate in bounded shadow under the existing operations law;
6. prove local, remote, deployed, and manifest identities match;
7. activate only that role through the existing configuration switch;
8. monitor it with the role's existing quality and drift owners;
9. stop and restore the strong configuration on any wrong acceptance,
   unexplained recall loss, invalid-rate movement, drift, or accounting gap.

Use one reviewed commit for one role. No other model, prompt, code cleanup, or
feature enters that commit.

## Gate 14.6 — Close or repeat serially

After one role is promoted or rejected:

* freeze its decision, evidence, exact identities, and measured result;
* update the existing model-role and status owners;
* discard no strong baseline evidence;
* obtain an explicit owner choice before selecting another role and candidate.

Never run two candidate roles in parallel. A result does not transfer to
another role, model version, effort, prompt, provider, or transport.

## Stop conditions

Stop the active candidate if:

* Step 13 is not closed or the strong baseline moved;
* the role, candidate, denominator, truth, grader, prompt, model, effort,
  transport, cost, or code identity is unknown;
* evidence is no longer blind or was influenced by candidate output;
* a model grades itself or sees another model's answer;
* a prompt, rule, threshold, schema, source population, or deterministic path
  must change;
* a weaker result is being excused by lower cost;
* any wrong acceptance, recall loss, new invalid, new park, instability, or
  unexplained disagreement appears;
* a fallback, cascade, vote, automatic substitution, or second rule path is
  proposed;
* a call is unplanned or over its frozen ceiling; an activation or graph
  change lacks exact approval; or a commit/push violates the completed-step
  ruling;
* any unrelated file or external state moves.

## Completion condition

Step 14 is complete when the owner ends the optional program and every tested
role has exactly one reviewed result: promoted or rejected.

For every promoted role, the exact cheaper configuration must match or exceed
the strong baseline on all measured quality and reliability evidence, pass its
full release checks, and be the only active runtime configuration. Every other
role remains on its accepted strong configuration.

No candidate is required to pass. The strong-model system accepted at Step 13
remains the safe final result throughout.
