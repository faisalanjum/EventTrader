# THROWAWAY — Lane-Prompt Optimization (deep analysis + strategic plan)

> ⚠️ **THROWAWAY / SCRATCH FILE.** Created 2026-06-17. Nothing here touches production code or any existing `.md`. This is a working analysis only — delete freely. No prompt, schema, or pipeline has been changed.
> Status: **analysis + plan draft.** Recon workflow (`lane-prompt-recon`, read-only) is in flight; the 3 sections marked **⏳ PENDING RECON** get filled from its results.

---

## 0. The goal, in one box

Make the lane prompts so crisp that **Haiku (the weakest model)** picks the right **lane** and the right **state word** — **100% of the time, with zero wobble** — under these hard constraints:

| # | Constraint | Plain meaning |
|---|---|---|
| C1 | **Unambiguous** | exactly one correct answer per case, readable by a weak model |
| C2 | **No hardcoded examples** | examples over-anchor → hurt generalization |
| C3 | **Succinct** | shortest prompt that still works |
| C4 | **No ladders / no ordering rules** | definitions stand on their own; order must not matter |
| C5 | **Deterministic** | same input → same output, across reruns and across "infinite" samples |
| C6 | **Monotonic** | today's prompt = baseline; a new prompt may **only improve, never worsen** |
| C7 | **Empirical proof** | believe nothing without a test on a representative **golden set** + a separate **held-out** set |

> Assumption flagged: I read "as clear and as **ambiguous** as possible" as **un**ambiguous (C1). Everything below assumes that.

---

## 1. Plain what / why / what I'm proposing

- **What:** a measurement + auto-rewrite machine for the 4 lane prompts.
- **Why:** the only way you'll trust a prompt is a hard number on real data. So we must first be able to **measure**, then **search**, with a **gate** that can never let quality drop.
- **What I'm proposing (one line):** *Build the scoreboard first (golden + held-out + Haiku harness), lock today's prompt as the baseline score, then run a propose→test→gate loop that only keeps a rewrite if it beats the baseline everywhere and obeys C1–C5.*

The order matters: **you cannot optimize what you cannot measure.** So step 1 is the scoreboard, not new prompts.

---

## 1b. What recon found (the ground truth)

5 read-only agents mapped the repo. The big deltas vs my first draft:

| Question | Answer from recon |
|---|---|
| Are the 4-lane prompts wired into code? | **No** — spec-only (`DriverGraphSchema.md`). Task #738 pending. So the "baseline" must be *extracted* from the spec. |
| Is there an existing gold/harness? | **Yes, partly** — `drivers_harness/pass5` held-out + `ab_stratum.py`/`ab_differ.py`/`ab_pair_judge.js`. But the gold is **Opus-labeled + narrow** (M&A/biotech/IPO news only). |
| Was Haiku rejected? | Only for **coining names** (extraction — noisy, broke naming rules). For **classification** the floor test hit ~100%. So Haiku for lane+enum is *plausible*, not disproven. |
| How are models billed? | `agent()` → **metered pool** ($200/mo, overage OFF → fail-closed $0). Free-unlimited = Option #6 PTY, not yet wired. |
| Is an auto prompt-loop built? | **No** — recon's words: *"infrastructure ready, orchestration layer not."* That thin loop + confusion-matrix + linter is the real new build. |

Bottom line: **~70% of the machinery already exists and is TDD-tested.** The new work is the orchestration loop, a trustworthy+representative gold, and the constraint checks.

---

## 2. The constraints turned into *testable* properties

A constraint you can't measure is a wish. Here each becomes a check the machine runs automatically:

| Constraint | Made measurable as… |
|---|---|
| C1 Unambiguous | **on the gold set, exactly ONE enum definition fires per item** (Haiku's own reading). Two firing = ambiguous, by definition. |
| C2 No examples | a **linter**: reject any prompt containing a concrete instance (a specific company/number/quote). Principles allowed, instances banned (§4.4). |
| C3 Succinct | a **token budget** per lane prompt; the gate prefers the shorter of two equal-scoring prompts. |
| C4 No ladders | **order-invariance test**: shuffle the order the enum definitions appear in the prompt; the answers must not change. If they do, the prompt still secretly relies on order. |
| C5 Deterministic | **self-consistency**: run each gold item K times at temperature 0; any non-identical answer is a failure, even if the modal answer is right. |
| C6 Monotonic | **non-regression gate**: accept a candidate only if it ≥ baseline on gold AND held-out AND every per-lane AND every per-enum score. |
| C7 Empirical | the gold + held-out sets ARE the proof; nothing is "done" on argument alone. |

**This is the core trick:** "no ladder / unambiguous" stops being a style opinion and becomes two hard tests — *one-definition-fires* (C1) and *order-invariance* (C4). A prompt that passes both literally does not need a ladder.

---

## 3. The deepest insight: why "no ladder" is *possible* (the real lever)

A ladder ("pick the FIRST that matches") exists for ONE reason: the enum definitions **overlap**, so you need an order to break ties.

> Remove the overlap → remove the need for order.

So the real engineering target is not "write prettier prose." It is:

**Rewrite each lane's enum definitions until they are MECE — Mutually Exclusive (no two can fire on the same case) and Collectively Exhaustive (every real case fires exactly one).** Then order is irrelevant and the ladder deletes itself.

This is *measurable* (C1 + C4 above) and it's the thing the optimization loop actually searches for.

**Does the data allow MECE here? My honest read per lane:**

- **metric** — looks separable. Each word has a disjoint *trigger condition*:
  - direction stated → `increased`/`decreased`
  - same driver up AND down → `mixed`
  - explicitly flat/same number → `unchanged`
  - ongoing, no direction, no number → `persists`
  - a value, no comparison, no direction → `reported`
  - a real fact, none of the above readable → `unknown`
  These triggers don't overlap if each names its condition precisely ("has a comparison?", "has a direction?", "has a number?"). → **ladder likely removable.**
- **guidance** — already nearly MECE (first / up / down / same / pulled). Easy.
- **surprise** — 3 words vs an expectation. Trivially MECE. Easy.
- **action_event** — the hard one. The 10 words split cleanly along three independent axes:
  - **WHO**: the company itself vs a third party (→ `rumored`, `at_risk`)
  - **STAGE**: planned / ongoing / paused / done / dead
  - **CAUSE OF DEATH** (if dead): own choice (`canceled`) vs external block (`failed`) vs dispute-settled (`resolved`)
  These axes are independent → the labels are separable WITHOUT an order. **BUT** one piece of the current ladder is *not* a label-ordering rule and may be irreducible: **"classify the LATEST stage of the action."** That is a *scoping* rule (which fact in the text to read), not a tie-break between labels. Honest flag: scoping may have to stay as one short instruction even in a "no-ladder" prompt — it's choosing the subject, not the answer.

**Verdict:** MECE (and therefore ladder-free) is **plausible for all four lanes**, with one honest caveat — action_event may keep a single *scoping* sentence ("read the latest stage"), which is not the same as a tie-break ladder. The harness will tell us empirically whether the ladder-free form holds 100%.

---

## 4. Honest analysis of each ideal (no rubber-stamping)

### 4.1 "100% across infinite samples" — unprovable as stated; here's the rigorous version
You can never *measure* infinite samples. You can only prove 100% on a **finite, representative** set. So the operational target is:

**100% on a stratified golden set that covers every lane × every enum × every source type × every known hard-boundary pair, AND 100% on an independent held-out set built the same way.**

The *representativeness argument* (not raw count) is what lets you generalize the claim. 100% on a tiny set proves little; 100% on a set that deliberately includes every rare enum and every trap is strong evidence.

### 4.2 "Zero variability" — real, but has a hardware caveat
- We require **self-consistency**: K reruns at temp 0 must be byte-identical (C5).
- Caveat to be honest about: even at temp 0, an LLM API is **not guaranteed** bit-deterministic (batching / floating-point / mixture-of-experts routing can flip a token). So "zero variability" is **measured empirically**, not assumed. A prompt that is so crisp that the answer is never close to a boundary is the practical route to near-zero variability. We will *measure* it, not promise it from theory.

### 4.3 "No ladders" — achievable via MECE (see §3). One residual scoping sentence may remain for action_event.

### 4.4 "No examples" — the principle/instance line (so the linter can enforce it)
The constraint is real (examples over-anchor), but we must define it precisely or the linter can't run it:

| Allowed (a **principle** — a rule about a category) | Banned (an **instance** — a specific case) |
|---|---|
| "a worsening adverse condition counts as MORE of it" | "adverse weather worsened → increased" |
| "blocked by an outside party = failed; own withdrawal = canceled" | "the FTC sued to block the merger → failed" |
| "a value with no stated comparison = reported" | "AUV was $12.2M → reported" |

**Rule the linter enforces:** ban any token that is a concrete company, number, date, ticker, or quoted source phrase. Keep category-level rules. The current prompts already lean this way for action_event (deliberately example-free); the **metric** prompt still has parenthetical instances → those are the first thing the loop must convert to principles without losing accuracy.

### 4.5 There are TWO decisions, and one of them is harder than you may expect
- **Lane decision** = pick `fact_type` (metric/guidance/surprise/action_event). **Today this is done ONCE per Driver, by Opus, at catalog time** — *because the schema notes Haiku "wobbled" on it.* Asking Haiku to do the lane is therefore the **harder** target.
- **Enum decision** = pick the state word within a lane. Done per event by the producer. The 2026-06-17 floor test already showed Haiku ~100% in-scope per lane on the **enum** task. **Recon nuance:** Haiku was rejected only for *coining driver names* (recall-critical extraction — noisy + rule-breaking), NOT for classification. So prior evidence actually *supports* Haiku on the enum pick; the open risk is the **lane router**.

→ The loop must optimize **both** a lane-router prompt and 4 enum prompts. If, after the search, Haiku still can't hit 100% on the **lane** router, the honest fallback is "lane stays Opus, enum is Haiku-able," and the gate makes sure we report that truthfully instead of pretending.

### 4.6 The hidden tension in C6 ("only improve, never worsen")
Today's prompts **violate** your own ideal in places: the metric lane IS a 6-step ladder; action_event IS a ladder; metric has in-prompt examples. So a constraint-compliant rewrite (no ladder, no examples) is a **different, possibly lower-scoring** prompt at first. C6 says it can't score lower than today. So the loop must find a form that is **both** constraint-compliant **and** ≥ today's accuracy. That is exactly what the gate enforces — and it's why we keep today's (ladder-ful) prompt as the baseline to beat, not as the thing to ship.

### 4.7 Billing — concrete reality (recon-confirmed)
The whole driver pipeline runs `agent()` calls through `claude_agent_sdk` → entrypoint **`sdk-cli`** → a **metered monthly pool** ($200 on Max20x ≈ ~14 predictor runs), **not** the free OAuth subscription. Key safety facts:
- **Overage is OFF** (`org_level_disabled`): pool empty → request **rejected → $0**. No surprise charges, ever. Fail-closed.
- A **billing guard** (`test -z "$ANTHROPIC_API_KEY" || exit 9`) sits in every workflow → the raw paid API is never hit.
- **Haiku is runnable** via `agent(..., {model:'haiku'})` (alias → `claude-haiku-4-5`, confirmed live). It was *rejected only for coining names*, never for classification.
- **Cost math:** a full campaign (≈500-item gold × K=3 reruns × ~20 candidate iterations ≈ 30k Haiku calls) is on the order of **$60–100 of pool**, much of it cache-cheap (the prompt is shared across items). Cheap per-call, but it competes with the predictor's ~14 runs.
- **Unlimited-free path** = Option #6 (PTY interactive `run_once_v3`, entrypoint `cli` → subscription) — proven in isolation but **not yet wired** to classifiers; needs your OK.

**Decision #2 (billing):** run the loop on the **pool** (simple, fail-closed at $0, fine if iterations are capped) **or** invest in wiring Option #6 PTY for unlimited subscription runs. Recommend: start on the pool with a per-iteration cap; switch to Option #6 only if the campaign needs to be large.

---

## 5. The scoreboard (what to build first)

### 5.1 Golden set — representative AND trustworthily labeled
- **Source mix (your requirement):** News · Reports (8-K, 10-K, 10-Q — each separately) · Transcripts. Real text only.
- **Stratify across every cell**, oversampling the rare + hard ones (your known stratum preference — *union of extremes*, not an average):
  - lane × enum (include rares: `mixed`, `suspended`, `rumored`, `failed`, `unknown`)
  - source type (5 buckets above)
  - **hard-boundary pairs** (the traps): persists↔continued, rumored↔at_risk, failed↔canceled, surprise↔metric, reported↔increased, announced↔occurred
  - the **GATE** decision (a bare mention → *no DriverUpdate*) — arguably its own label in the test.
- **Trustworthy labels without hand-labeling everything:**
  - **Objective floor (zero-LLM):** where a deterministic rule can decide (e.g. "vs consensus" present → surprise), label by rule. This is the un-foolable floor (mirrors prior Drivers work).
  - **Strong-model consensus → human adjudication of disagreements only.** Two+ strong models (e.g. Opus + one more) label; agreements are provisional gold; **you adjudicate only the disagreements.** Freeze once adjudicated.
  - A gold item carries: `source_type, raw_quote, driver_name, gold_lane, gold_enum, label_source(rule|consensus|human), boundary_tag`.
- **Why labels can't be LLM-only:** if the same model both labels and is tested, the test is circular. The objective floor + human adjudication breaks the circle.
- **Recon reality:** an existing held-out set lives at `drivers_harness/pass5/_v2_heldout_*` — BUT it is **(a) Opus-labeled (model-made, not human)** and **(b) narrow** (M&A/biotech/IPO *news* only, built to validate `rumored`/`failed`). So the current "100%" means *Haiku agreed with Opus*, not *Haiku was right*. Reuse its **plumbing**; rebuild its **coverage + label trust**.

### 5.2 Held-out set
- A **second** frozen set, built by the identical recipe, **quarantined** from the loop (never seen during iteration).
- Its only job: detect overfitting. **Overfit alarm = gold score high but held-out score lags.**

### 5.3 The harness — mostly already exists (reuse, don't rebuild)
Recon found battle-tested machinery (257+ TDD tests) we adapt instead of writing fresh:
- **`ab_stratum.py`** — pure-code stratified selector (union-of-extremes + composite fill, noise spread evenly). Reuse to pick the hard/representative items.
- **`ab_differ.py`** — pure-code statistical GO/NO-GO gate (Wilson CI, one-sided binomial, degenerate-floor rule-of-three). Reuse as the **non-regression gate** engine (adapt the metric: merge-loss → classification accuracy).
- **`ab_pair_judge.js`** — parallel `agent()` fan-out with **byte-identical prompts** + **h32/SHA256 relay integrity** + billing guard. Reuse as the Haiku-runner.
- **`ab_differ_report.json`** — the results-JSON shape to mirror.
- **`drivers_harness/pass5/_v2_heldout_*`** + `pass4/_wf14_floor.py` / `_wf14_gold_adversarial.json` — existing held-out + adversarial-pair harness to seed plumbing from.
- **Genuinely new to build:** the thin **orchestration loop** (recon's own gap: *"prompt-iteration is currently manual… infrastructure ready, orchestration layer not"*), the **per-lane/per-enum confusion matrix**, the **constraint linter**, and the **order-invariance + consistency** checks.
- Discipline: Haiku pinned (`claude-haiku-4-5-20251001`), temp 0, **K reruns**; **only the prompt text changes** between runs (single variable). Clean experiment.

### 5.4 The constraint linter (automatic, zero-LLM)
Before any candidate is even tested, it must pass:
- **no instances** (C2 — §4.4 rule),
- **token budget** (C3),
- **order-invariance** harness hookable (C4),
- well-formed (every enum defined exactly once, lane set covered).
A candidate that fails the linter is discarded for free, before spending any Haiku call.

---

## 6. The optimization loop (automatic + monotonic)

```
            ┌─────────────────────────────────────────────┐
            │ BASELINE = today's prompt → score on gold +   │
            │ held-out + consistency (the number to beat)   │
            └───────────────────────┬─────────────────────┘
                                    │  (record confusion matrix = the errors)
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ PROPOSE (error-driven): a strong "prompt surgeon" model rewrites │
   │ ONLY the definition clauses that the confusion matrix shows are  │
   │ overlapping/missed. Must obey C2–C4 (linter pre-checks it).      │
   └───────────────────────────────┬────────────────────────────────┘
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ TEST candidate on gold + held-out with Haiku (K reruns).        │
   └───────────────────────────────┬────────────────────────────────┘
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ GATE (accept iff ALL hold):                                     │
   │   • ≥ baseline on gold  AND  ≥ baseline on held-out             │
   │   • no per-lane regression  AND  no per-enum regression         │
   │   • consistency not reduced  • linter passed                    │
   │  accept → candidate becomes new baseline ; else → keep baseline  │
   └───────────────────────────────┬────────────────────────────────┘
                                    ▼
        loop until gold = 100% AND held-out = 100% AND zero-wobble,
        OR no candidate improves for N rounds (local optimum) → STOP + report
```

- **Error-driven** (rewrite only what the confusion matrix flags) beats blind rewriting and converges far faster.
- The gate is **monotonic by construction** → C6 is *guaranteed*: the shipped prompt is never worse than today's on any measured axis.

**What I can and cannot guarantee (no overstatement):**
- ✅ **Guaranteed:** never worse than baseline; score is monotone non-decreasing; the loop converges to a fixed point.
- ✅ **Guaranteed if reachable:** if a constraint-compliant prompt that hits 100% exists in the search space, enough proposals will find it.
- ❌ **NOT guaranteed:** that 100% is reachable at all (that's an empirical property of language + Haiku, not something a plan can promise), nor a *global* optimum (prompt space is infinite). The harness's job is to **find the true achievable ceiling** and prove we sit at it.

---

## 7. What to do FIRST (ordered)

1. **Confirm the billing call** (Decision #2 above): pool (fail-closed at $0) vs Option #6 PTY. Pool is fine to *start*; no blocker as long as overage stays OFF.
2. **Extract the LOCKED spec text into a runnable baseline prompt** — verbatim from `DriverGraphSchema.md` L239–270 (the 4 lanes are currently spec-only; *no runtime prompt exists yet*). This faithful extraction = the baseline to beat. (Spec untouched; new throwaway prompt file.)
3. **Build the frozen golden + held-out sets** (objective floor → strong-model consensus → you adjudicate disagreements). *This is the long pole and needs your sign-off on construction.*
   - ⚠️ Pulling real source text means reading Neo4j — **off-limits without your explicit OK** (your standing rule). The plan describes it; I won't run it until you say so.
4. **Measure today's prompt** → baseline numbers + confusion matrices. *Now we have a scoreboard.*
5. **Stand up the linter + order-invariance + consistency checks.**
6. **Run the propose→test→gate loop** (error-driven), pausing before any large token spend (your rule: "a preview without a gate protects nothing").

> First *real action* the moment recon + your approvals land = **steps 1–2 (confirm path + baseline), then 3 (gold)**. Prompt rewriting is *last*, not first.

---

## 8. Open owner decisions + approvals needed

1. **Neo4j read approval** to pull real source text for the gold set (off-limits by default). Yes/no?
2. **Billing path** for Haiku at scale — confirm the subscription route (recon will propose the exact command).
3. **Gold-label authority:** do you adjudicate the strong-model disagreements yourself, or accept consensus where 2+ strong models agree?
4. **Scope of "lane" target:** optimize the Haiku **lane-router** too (harder — Opus does it today), or accept "lane = Opus, enum = Haiku" if the router can't hit 100%?
5. **Gold size per cell** (how many items per enum / per source type) — drives cost and tightness of the 100% claim.
6. **Spend cap** per iteration before the loop must pause for your go-ahead.

---

## 9. Risks / failure modes (so they're not silent)

- **Circular gold** (LLM labels + LLM tested) → broken by the objective floor + human adjudication (§5.1).
- **Overfitting to gold** → caught by the quarantined held-out set (§5.2).
- **100% may be unreachable** for intrinsically ambiguous source text → those items belong in `unknown` or are excluded from gold; the loop reports the true ceiling honestly.
- **Determinism is hardware-limited** → measured, not assumed (§4.2).
- **Cost blow-up** → linter pre-filters candidates for free; spend cap + pause-before-big-spend.
- **The "improve-only" tension** (§4.6) → the gate handles it; we keep today's ladder-ful prompt only as the *number to beat*, never as the thing to ship.

---

## 10. Reuse map — existing infra → role in this plan (recon-filled)

| existing artifact | reuse as | path |
|---|---|---|
| Locked 4-lane spec text | the **baseline prompt** (extract verbatim) | `.claude/plans/Drivers/WIP/DriverGraphSchema.md` L239–270 |
| Stratified selector (union-of-extremes) | pick hard/representative gold items | `…/Drivers/workflows/ab_stratum.py` |
| Statistical non-regression gate | the **gate** engine (adapt metric) | `…/Drivers/workflows/ab_differ.py` |
| Parallel judge + relay integrity + billing guard | the **Haiku runner** | `…/Drivers/workflows/ab_pair_judge.js` |
| Results-JSON shape | the results file format | `…/runs/2026-06-10_005333_restaurants_abscratch/ab_differ_report.json` |
| Existing held-out (Opus-made, narrow) | seed/plumbing only — rebuild coverage+trust | `drivers_harness/pass5/_v2_heldout_*` |
| Adversarial-pair floor harness | pattern for boundary-pair tests | `drivers_harness/pass4/_wf14_floor.py` + `_wf14_gold_adversarial.json` |
| Older flat state vocab (pre-schema) | ⚠️ do NOT reuse as baseline (different vocab) | `drivers_harness/vocab_seed.py` |
| Billing canonical doc + Option #6 PTY | the subscription path (if unlimited needed) | `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md` |
