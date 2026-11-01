# Fiscal/Core review guardrails — 2026-07-24

> **NON-AUTHORITATIVE REVIEW AID.** This file changes no Driver rule or plan.
> If it conflicts with a live source below, the live source wins. Its purpose is
> to prevent review drift and survive context loss.

## 1. Read authority in this order

1. `FinalDesign/FINAL_DESIGN.md` — system meaning and safety.
2. `FinalDesign/ChannelContract.md` — Fiscal's public duties and limits.
3. `FinalDesign/ChannelContract.md` Part III — live internal packet and
   responsibility split.
4. `FinalDesign/BUILD_AND_OPERATIONS.md` — build, test, run, and release gates.
5. `FinalDesign/STATUS_AND_HISTORY.md` — current system status.
6. `WIP/UniversalLocator_Design_2026-07-18.md` — locked Locator base.
7. `WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md`
   — current Fiscal amendment and work order.
8. `FinalDesign/FableExperimentPlan.md` and `FableExperimentWorkOrder.md` —
   formal experiment rules.

The Review Record is evidence and history, not rule authority. Phase-6 packages
are temporary work products. `FinalDesign/QwenTests/` is a diagnostic research
folder. None of those may silently change the sources above.

## 2. The primary task

```text
Fiscal finds and faithfully copies source evidence
    -> shared Core interprets it and decides identity/reuse
    -> deterministic Core code validates and writes
```

- A **Driver** is the reusable meaning.
- A **DriverUpdate** is one source-backed occurrence.
- Fiscal never creates, names, merges, or stores a Driver.
- Fiscal sends raw evidence in real publication-time order and keeps a complete
  outcome ledger.
- Core alone interprets meaning, chooses the Driver, decides reuse versus
  creation, and writes.
- Code owns mechanical work: source hashes, exact spans, number parsing,
  normalization, IDs, validation, and safe rejection.
- Models own meaning choices. Exact-label or vocabulary code must never replace
  a model's semantic decision.
- Missing evidence must fail closed. A missed match is repairable; a wrong
  match can corrupt identity.

### Orchestration boundary

- This review role manages and audits the **Fiscal bot only**.
- Core is a parallel owner-managed stream. Coordinate through the frozen
  channel contract and explicit handoffs; do not direct, redesign, or silently
  absorb Core's work.
- A Core dependency may block a Fiscal proof, but it does not broaden Fiscal's
  responsibility.

## 3. Smallest valid current table-reader test

For the isolated 8-K table capability test:

- One known, value-blind Driver anchor and one complete table per model call.
- The model returns only the exact marked numeric cell IDs, or `[]`.
- The model—not exact-label code—chooses which cells match the anchor's full
  meaning, including slice, measurement, unit, and time type.
- Code assigns IDs only to true numeric data cells, re-pulls the pinned source,
  reconstructs the selected cells, copies their evidence, and rejects drift,
  unknown IDs, duplicates, or incomplete evidence.
- Hidden truth is independently created and stored as stable source-cell
  addresses. A model being evaluated never creates or judges its own key.
- Exact-set grading stays strict: an extra cell is a wrong accept; a missing
  cell is a recall miss; `[]` is correct only when no table match exists.
- Certification must send the anchor to every eligible table; hidden truth may
  not preselect the winning table.

This one-target call shape isolates the model skill. It does not silently amend
the FinalPlan's production batching. Before activation, the exact deployed
multi-anchor batch shape must pass its own unseen test.

The other Fiscal reader lanes remain separate jobs and need the same
first-principles simplification review before testing:

- 8-K prose — select the exact sentence/occurrence for a known anchor.
- Prepared remarks — select the exact spoken update.
- Q&A — select the exact answer containing the update.
- Numberless evidence — select the exact source span.

Do not force one lane's response shape onto another. Start with the smallest
model choice and let code perform only source reconstruction and verification.

AI-reader designs remain open to improvement. Accept a change only when it:

- removes unnecessary work or materially improves the decision;
- preserves every source, safety, abstention, hidden-key, and zero-wrong gate;
- uses only rules that apply across the unknown source universe, not examples
  memorized from the test set; and
- proves the changed model-plus-code system on fresh unseen cases.

“100% reliable” is a release bar, not a mathematical promise: zero observed
wrong accepts on the locked unseen test, complete reporting of misses, and
fail-closed mechanical verification in production.

## 4. Review checklist for every proposed change

Before accepting a change:

1. Name the live rule that requires it.
2. Reproduce the claimed problem in live code and, when relevant, real data.
3. Ask whether existing code already handles it.
4. Reject any move of semantic matching into strings, regexes, labels, or
   answer-derived code.
5. Reject circular tests where the same rule creates and grades the answer.
6. Check that model inputs contain no value, target period, answer ID, hidden
   key, or other answer-derived clue unless the governing contract explicitly
   allows it.
7. Test a real positive, a real distractor/no-match, a wrong extra selection,
   a missing selection, malformed output, and stale/tampered source evidence.
8. Read the implementation and run the exact scenario; green totals alone are
   not proof.
9. Prefer the smallest design that preserves every required behavior. Do not
   add machinery for hypothetical future cases.
10. Stop for owner approval before any AI spend, Neo4j write, harvest,
    activation, or push that has not already been explicitly authorized.

## 5. Keep these experiments separate

- Fiscal Phase 6 measures **evidence location and copying for a known anchor**.
- Core EXP-5/K-fields measures **full DriverUpdate interpretation** over about
  150 facts. It is not the Fiscal table test.
- The Fiscal Route-A 150-case gate measures deterministic relocation against
  real Core-written anchors. A read-only graph check on 2026-07-24 found
  `Driver=0` and `DriverUpdate=0`, so that gate remains unmeasured.
- A Qwen diagnostic result never authorizes a production role. Each model and
  task needs its own unseen, hidden test and activation gate.

## 6. Current stop at this review (R15 audit)

- Fiscal Phases 1–5 are closed.
- The accepted 8-K table screen is development evidence, not production
  certification.
- Phase-6 truth expansion is still pre-call; no labeling/model call is
  authorized by this note.
- R15 correctly prices K1's proposal answer once, keeps K1 to sibling solves,
  uses 200-character table anchors, applies 3-bytes/token to the table flow, and
  keeps retrieval out of the current certification.
- R15 is still not ready to run:
  - the runner still has no post-anchor request manifest or response loader for
    the real K1-sibling/K2/K3/review stages. It accepts caller-supplied integer
    counts; arbitrary inflated counts pass. Its dry run compares a fabricated
    count dictionary, not actual response artifacts;
  - review files are not joined to an expected request set. Duplicate reviews
    for an unknown request ID pass and count. The validator checks JSON shape
    only, not the frozen anchor/table/source relationship;
  - the review prompt asks whether there is a single cell identified by an
    anchor period. This contradicts the actual task: the answer is a complete
    cell set across source-stated periods, and period is deliberately absent
    from the anchor;
  - the total ceiling still understates the span lane by 72,000 tokens: 240
    span cases × three 1,200-byte maximum outputs / 3 = 288,000, while the
    manifest records 216,000. The table estimator also serializes simplified
    objects rather than the real call envelopes, so model/settings/contract
    overhead is not yet priced through the execution serializer;
  - package version v17/R15 conflicts with the generated manifest label
    v16/R14, and the K3 model slot still says Opus 4.8 despite the owner's
    replacement with Opus 5.
- The durable AI rule must remain narrow: deterministic code owns universal
  reconstruction and verification; AI owns semantic choices only when no
  deterministic rule can generalize safely. It is not a global “prefer AI”
  instruction.
- Full no-preselection fan remains the certification baseline. A production
  retrieval shortcut is a separate future optimization and may be considered
  only after it proves zero misses on hidden full-fan truth and receives owner
  approval; cost alone cannot silently weaken the current test.
- Therefore: **do not call a model or commit this Phase-6 truth package until
  code, prompts, tests, package, manifest, and Review Record describe one
  identical design and that design passes an independent live audit.**

Refresh only this section when status changes. Never place new Driver law here.
