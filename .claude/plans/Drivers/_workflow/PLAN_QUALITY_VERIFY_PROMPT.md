# Drivers Plan — Quality & Effectiveness Verification Prompt (reusable)

> **🤖 If you are an AI agent handed this file:** read it in full and EXECUTE the prompt in the
> fenced block below as your task, right now, as a multi-agent **workflow**. Everything in the
> block is addressed to you. You need filesystem access to this repo for the paths to resolve.

> **How to use (human):** either (a) tell a bot *"read `.claude/plans/Drivers/_workflow/PLAN_QUALITY_VERIFY_PROMPT.md`
> and run it as a workflow"*, or (b) paste the block below as a new Claude Code message. The word "workflow"
> triggers multi-agent orchestration. Best run **after** any in-flight edits to the Drivers
> docs have landed — it reads every file FRESH, so it judges whatever on-disk state exists at
> run time. Read-only: it makes no changes.
>
> **What it does (and how it differs from the consistency audit):** the consistency audit asks
> *"do the docs agree with each other?"* This asks the harder question — *"is this a great
> plan?"* It (1) derives the requirements itself instead of trusting the plan's self-description,
> (2) builds its own "ideal minimal plan" as a yardstick, (3) scores the real plan on 7 axes
> where **minimalism/anti-bloat and effectiveness count as much as correctness**, and (4)
> deliberately ignores surface typos so it judges intrinsic plan merit.

---

```
Use a WORKFLOW to perform a world-class planner's verification of the Drivers plan.

ROLE: You are a world-class systems architect and planner — the kind whose plans are
correct, complete, minimal, and executable on the first try. You are skeptical, reason from
first principles, and you NEVER rubber-stamp (including your own reasoning). You are not a
copy-editor. Your job is to judge whether this is THE RIGHT plan, done MINIMALLY, that will
ACTUALLY WORK for its intended purpose.

MISSION: Determine whether the Drivers planning corpus is a PERFECT, MAXIMALLY-EFFECTIVE,
MINIMAL (non-bloated) plan for its intended purpose. If it is not perfect, state exactly how
far from perfect it is and the SMALLEST set of changes that would close the gap.

CONTEXT — DO NOT SKIP:
- The plan lives in /home/faisal/EventMarketDB/.claude/plans/Drivers/
- It may be edited by another process. Read every file FRESH at workflow start;
  trust no cached summary. Check `git log -p` / file mtimes if useful to get the latest state.
- A separate consistency audit handles cross-doc typos and stale-number mismatches, and those
  fixes may be landing concurrently. DO NOT spend effort re-flagging surface inconsistencies
  (e.g. "25 vs 29", a stale example) UNLESS the surface issue exposes a deeper design flaw.
  Your lens is PLAN QUALITY, not document tidiness.
- Project billing rule: harness real-LLM runs must use the in-session subscription, NEVER
  metered claude_agent_sdk / `claude -p`. Flag any plan step that would wire a metered path.

IMPLEMENT AS A MULTI-PHASE WORKFLOW:
  Phase 0  Derive ground truth (requirements) — independently
  Phase 1  Build an "ideal minimal plan" yardstick — independent designer panel
  Phase 2  Read the actual plan in full
  Phase 3  Per-dimension evaluation — one independent reviewer per axis (parallel)
  Phase 4  Red-team + adversarial verification of every finding
  Phase 5  Synthesis verdict

PHASE 0 — DERIVE THE GROUND TRUTH YOURSELF (do not assume, do not let the plan anchor you):
Read ConceptualRequirements.md, DriverNameRisks.md, and req_canonical.md. Produce an
INDEPENDENT statement of: the intended PURPOSE, every EXPLICIT requirement, every HARD
CONSTRAINT (including the 6 "Harness Test Requirements"), the SUCCESS BAR, and any
IMPLICIT/unstated requirement a strong planner would infer. Do this BEFORE reading the plan's
own self-assessment so you are not biased by its self-praise. This becomes your rubric.

PHASE 1 — BUILD THE "IDEAL PLAN" YARDSTICK: From first principles, independently design what a
PERFECT and MINIMAL plan to achieve that purpose would contain — essential components, the
determinism mechanism for stable cross-LLM naming, the reuse-vs-build-new split, and the test
strategy. Spawn 2–3 independent designers and synthesize one yardstick. You will measure the
actual plan against THIS, not against its own claims.

PHASE 2 — READ THE ACTUAL PLAN IN FULL (see file list below), plus the live artifacts it
depends on (the real earnings-learner SKILL.md producer, the real guidance pipeline code it
claims to reuse).

PHASE 3 — EVALUATE on these 7 dimensions. One independent reviewer per dimension; each reads
the actual files, scores 0–10, writes the rationale AND the precise gap to 10:
  1. FITNESS-FOR-PURPOSE / EFFECTIVENESS — If executed exactly, will it achieve the goal
     (deterministic, reuse-first driver naming at the stated accuracy bar)? Will the core
     mechanism actually produce STABLE names across different LLMs and runs? Name any
     mechanism that will not work in practice.
  2. COMPLETENESS / EXECUTABILITY — Is every component and phase FULLY defined (a stated
     requirement)? Could a builder LLM build it in ISOLATION with zero ambiguity? Flag
     undefined functions, missing algorithm bodies, unhandled edge/failure cases, orphan refs.
  3. MINIMALISM / ANTI-BLOAT (first-class — weight heavily) — What can be DELETED without
     lowering the bar? Redundant validators/levers, speculative Phase-2/3 scope smuggled into
     Phase-1, over-engineering, duplicated machinery. Is this the simplest design that hits the
     bar? Produce an explicit CUT LIST.
  4. LLM-vs-CODE BOUNDARY — Is each decision assigned to the right engine? Flag every place
     CODE is used where an LLM would be more accurate (semantic meaning/novelty/ambiguity), and
     every place an LLM is used where deterministic code is safer/cheaper (exact-match/format/
     repeatable fold). Flag where code would OVER-REJECT on a semantic call.
  5. ROBUSTNESS / RISK COVERAGE — Does it cover the hardest failure modes (use DriverNameRisks
     as adversarial cases)? Are residual risks declared honestly and either mitigated or
     explicitly deferred-with-rationale? Are accuracy/coverage claims SUPPORTED or overstated?
     Flag every unsupported number.
  6. REUSE CORRECTNESS — Is the reuse-vs-build-new split honest and right? Is it over-claiming
     reuse (to look cheaper) or rebuilding something that already exists?
  7. STRATEGIC / FIRST-PRINCIPLES SOUNDNESS (the planner's lens) — Step back: is this even the
     RIGHT approach? Is there a fundamentally simpler or more robust architecture that achieves
     the same purpose? Challenge the core design decisions (determinism approach, registry
     model, harness-first strategy), not just the details.

PHASE 4 — RED-TEAM + ADVERSARIAL VERIFY: Spawn a red team whose explicit job is to argue "this
plan will FAIL in production / is BLOATED / will NOT generalize across tickers and LLMs." Then
independently verify every Phase-3 finding by re-reading the cited text — REFUTE anything
reconcilable, a misread, or working-as-designed. Only confirmed findings survive into the
verdict.

PHASE 5 — VERDICT. Produce:
  (a) one-line verdict: is the plan perfect & effective & minimal? (yes / no + why)
  (b) a dimension SCORECARD (0–10 each + weighted overall)
  (c) a prioritized GAP-TO-PERFECT list — what's missing, wrong, or over-built — severity-
      ranked, each with file:line and a concrete fix
  (d) an explicit BLOAT CUT LIST (delete these) and MISSING-ADDITIONS LIST (add these)
  (e) the single HIGHEST-LEVERAGE change
  (f) an honest "DISTANCE TO PERFECT" statement (what would it take to make it a 10/10)

WHAT TO READ (fresh, in full):
  Anchors:
    - CombinedPlan.md            (canonical plan; spec edits E1–E30)
    - DriverProcess.html         (narrative process anchor; Parts A–F first-principles, Part H build conditions)
  Requirements / ground truth:
    - ConceptualRequirements.md  (intended purpose + foundation + 6 Harness Test Requirements)
    - DriverNameRisks.md         (hardest naming failure modes; scratch/non-canonical — use as adversarial cases only)
    - _workflow/req_canonical.md (deduped canonical requirements)
  Spec detail:
    - DriverOntology.md                 (LLM-facing naming rulebook)
    - DriverOntology_Implementation.md  (algorithms, validators V1–V15, schema, mirror map)
    - "DriverOntology Prompt.md"        (the ACTIVE author-prompt that regenerates the ontology — audit it as code)
    - Neo4jXBRLDesign.md                (Neo4j + XBRL schema)
  Harness (part of the intended purpose — "fully define every phase", "test with real LLMs", "easy to productionize"):
    - Harness/Harness_BuilderPrompt.md
    - Harness/TESTER_HANDOFF.md
    - isolated_llm_call_pattern.py
  Supporting analysis (INPUT, not gospel — do not treat as authoritative):
    - _workflow/BEST_WAY_driver_creation.md, reuse_map.md, scope_split.md,
      audit_consistency.md, audit_coverage.md, audit_minimalism.md, audit_reliability.md
    - DriverImprovements.md, ChecklistProposals.md, DoubtsInHTML.md
  Live dependencies to verify claims against:
    - the live earnings-learner SKILL.md (the actual Phase-1 producer artifact)
    - the live guidance pipeline code (e.g. guidance_ids.py / build_guidance_ids) to test reuse claims
    - how guidance extraction names things today (ConceptReq §1.4 open question: should driver
      nomenclature align with guidance nomenclature?)

RULES (non-negotiable):
  - Read-only. Make NO changes to any file.
  - Independent eval: verify against the primary source; never rubber-stamp the plan's own
    self-praise; flag EVERY overstatement (especially accuracy/coverage numbers).
  - Minimalism and effectiveness are CO-EQUAL with correctness. A bloated plan that "works" is
    NOT perfect.
  - Cite file:line for every claim and quote the text.
  - Distinguish "would mislead or break a builder" (real) from "cosmetic" (note briefly).
  - Do NOT re-litigate the surface inconsistencies being fixed elsewhere — judge the plan's
    intrinsic merit.

OUTPUT: a crux-first report in plain language — scorecard and gap/cut/add lists up front,
short enough to act on, tables over prose.
```
