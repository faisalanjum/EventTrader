## Pipeline Architecture

### 7-Step Pipeline

```
0. Guidance     guidance-inventory {TICKER} → cumulative guidance history (once per ticker)
1. Discovery    get_quarterly_filings → event.json (all 8-K filings for ticker)
2. Filter       skip quarters with existing result.json (idempotent resume)
3. Quarter Loop (sequential, chronological):
   3a. Planner       reads 8-K + U1 planner_lessons + guidance → structured fetch_plan.json
   3b. DataFetch     orchestrator executes fetch plan via parallel Task sub-agents
   3c. Predictor     reads 8-K + full context bundle → prediction/result.json
4. Attribution  post-event learner writes feedback into attribution/result.json
5. Validation   outputs present + schema-valid (inline, not JSON Schema)
6. Complete     ORCHESTRATOR_COMPLETE {TICKER}
```

Quarters are **sequential** — Q(n) attribution must complete before Q(n+1) prediction so U1 feedback is available. Parallelism lives *within* each quarter at step 3b: the planner's `fetch` field is an array-of-arrays (tiers). Within a tier, all sources fan out as parallel Task sub-agents; across tiers, sequential fallback (tier N+1 only if tier N returned empty).

### Two Modes

| | Historical | Live |
|---|---|---|
| Trigger | User/batch invocation | Neo4j 8-K ingestion → Claude SDK |
| PIT | `--pit {filed_8k}` on all data queries, fail-closed | None needed — future data doesn't exist yet |
| Attribution | Same-run (data already exists) | N=35 day timer after 8-K |
| SDK prompt | `/earnings-orchestrator NOG` | `/earnings-orchestrator NOG --live --accession {acc}` |

Both modes run the identical pipeline code. The only differences are PIT gating and attribution trigger timing.

### Context Bundle

Two-layer design: **JSON as contract** (validate-able, persisted for audit) + **rendered sectioned text** (natural for LLM Skill invocation).

The orchestrator assembles `context_bundle.v1` JSON with: `8k_content`, `guidance_history` (raw markdown passthrough), `u1_feedback[]` (all prior quarters' feedback), and `fetched_data{}` (keyed by planner's `output_key`, each with sources/tier metadata). It then renders to fixed-order sectioned text: 8-K → Guidance → U1 Feedback → Fetched Data sections.

Planner receives a subset (8-K + U1 planner_lessons + guidance). Predictor receives the full bundle. Learner receives NO bundle — just 3 paths (prediction result, actual returns, context_bundle ref) and fetches its own post-event data autonomously.

### U1 Self-Learning Loop

Attribution writes a `feedback` block per quarter into `attribution/result.json`:

- `prediction_comparison` — predicted vs actual (signal, direction, move%)
- `what_worked` (max 2), `what_failed` (max 3), `why` (1-3 sentences)
- `predictor_lessons` (max 3), `planner_lessons` (max 3)

The orchestrator reads **ALL** prior quarters' feedback and passes it **raw** into the next quarter's context bundle. No digest, no scoring, no decay. The LLM IS the digest — it weights repeated patterns and discounts stale info naturally. Caps per field enforce signal quality at write time.

This is what makes sequential quarter processing non-negotiable: Q(n) attribution → Q(n+1) prediction is the feedback path. ~140 items across 10 quarters remains trivial context for an LLM.
