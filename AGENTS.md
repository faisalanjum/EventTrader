# EventMarketDB - Agent Instructions

## User Communication Rules

These rules are permanent for this project and apply after compaction/resume too.

1. Use plain words only. Before sending any message, check: "Would a new person with no project context understand this?" If not, rewrite it or explain the word.
2. Be very concise. Keep normal replies to a few sentences. If more detail is needed, start with the short answer first.
3. Use simple visuals when helpful: tiny diagrams, before/after examples, and small tables.
4. Make answers easy to follow: one idea at a time, short bullets, clear next step, no wall of text.
5. Remind the user of important earlier context before relying on it. Example: "Reminder: we already found that X works, but Y failed."
6. Avoid project jargon in user-facing messages. If a project term is unavoidable, define it in plain English the first time.
7. Report times to the owner in Eastern time using `America/Toronto` (EDT while daylight saving applies, EST otherwise), with the timezone label. Require the same in delegated reports. Preserve existing UTC evidence and exact deadline instants; changing the display timezone never resets a deadline.

For Driver work specifically: keep explaining the goal in simple terms before discussing files, tests, or plans. Do not bury the main point inside history.

Before directing or auditing Fiscal/Core Driver work, read
`.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`.
It is a non-authoritative continuity checklist; the live plans it cites always win.

## IBKR Protection — Owner Update, 2026-11-01

- The owner reports that both live and paper accounts were logged in, all four services were healthy, and both connections passed IBKR health checks on **November 1, 2026, at 8:10 AM EST**. Automatic login is running again; phone approval requests are expected when IBKR requires verification. This is the owner's recovery report, not a new check by this agent.
- Unrelated cleanup must preserve the `mcp-services` deployments `ibkr`, `ibkr-paper`, `ibkr-ib-gateway`, and `ibkr-paper-gateway`, their login state, configuration, credentials, and required running/recovery images in both Docker and Kubernetes. The recovery needed local images that could not be downloaded; an image appearing unused in Docker alone does not establish that it is disposable.
- Do not stop, disable, scale down, delete, or reconfigure these services as part of cleanup. IBKR changes belong to the separately authorized IBKR maintenance task; coordinate with its agent. Preserve the related runbook at `.claude/plans/IBKR/deployment.md`.

## TypeSafe

Use the TypeSafe skill for relevant AI work in this project. Read
`.agents/skills/typesafe-ai/SKILL.md` and follow its guidance, including checking
the current TypeSafe docs before designing or changing an integration.

## Scope Discipline - Highest Priority

These standing requirements apply to every step and future session: minimal, generic,
well-organized code; efficient execution and storage; comprehensive evidence-based
checks. Reuse existing code, measure optimizations, and never reduce correctness or
coverage merely to reduce line count. Carry these requirements into every handoff.

1. Build the smallest solution that fully preserves required behavior, correctness, and safety.
2. Before every feature, layer, abstraction, or edge-case rule, decide immediately whether it is required or can be removed or handled by existing code. Build it only when required; otherwise cut it.
3. Do not build machinery for hypothetical future needs. Handle real and likely cases only.
4. When a genuine feature tradeoff needs owner judgment, ask one specific keep-or-cut question, explain the impact plainly, and recommend the smaller safe choice.
5. Do not defer scope decisions or leave vague future work. Decide each point as it arises.
6. Re-check scope throughout implementation. Prior discussion or approval does not protect unnecessary complexity.

**Mandatory library check (owner, 2026-10-08):** before building or extending in-house behavior, inspect the selected package's existing APIs, settings and helpers at the pinned version (including Docling, EdgarTools and Chandra). Check its actual source/official documentation and test the relevant native path; do not rely on memory or assume a capability is absent. Reuse native functionality wherever it satisfies the required behavior. Any custom code must identify the demonstrated library gap and be the smallest generic integration needed to close it. Do not copy or rebuild behavior the package already provides. Record this check in implementation handoffs and reviews.

## Evidence and Testing

1. Use TDD for behavior changes: first reproduce the failure with a test, then make the smallest fix, then run the focused and regression suites.
2. Do not trust a green test count alone. Read the live code and run the exact scenario behind each important claim.
3. When a decision depends on real graph data, verify it with read-only queries against the existing Neo4j database. Synthetic fixtures may supplement this check, not replace it.
4. Neo4j writes still require the user's explicit approval.
5. When guiding Claude or another bot, require these same steps before accepting its conclusion.

## Class-Wide Defect Rule - Permanent

When a defect reveals a wider class, never fix or test only the reported
example.

1. Find the rule-owning function or boundary and make the smallest general fix
   there. Do not add a word list, example-specific branch, or second rule
   engine when structured data or existing code can solve the whole class.
2. For a finite observed domain, test the complete live population and report
   every accepted, parked, and rejected category with counts and reasons. For
   an open domain, use real examples plus boundary, adversarial, permutation,
   and mutation tests.
3. Derive the audit inventory from the live code: public entry points, failure
   branches and exception outcomes, deferred or gated items, changed files,
   and relevant database categories. Do not rely on memory or a hand-written
   sample list.
4. Every negative test needs a real positive control. Expected answers must
   come from an independent source or calculation, never from the code being
   tested.
5. Before declaring readiness, freeze the reviewed snapshot, reconcile every
   inventory row to a test or an explicitly named open item, run focused and
   full regressions, and state any remaining untested or semantic-only risk.

## Cleanup preservation — owner-approved, 2026-11-01

Keep the current extraction/OCR implementation, Driver plans, reference code and
required test inputs. The old recovery worktrees and experiment replay payloads
were deliberately retired after selected source/evidence preservation; historical
folder mentions do not require rebuilding those deleted experiments. The private
keepers and exact original-path indexes are in
`/home/faisal/prepare_cleanup_review_20261031/clean_worktree_20261101/`.
Preserve that directory and the explicitly held local files listed by the cleanup
record. Unresolved material and unfinished Phase-6 source were not certified or
published by cleanup. IBKR protection above remains in force.
