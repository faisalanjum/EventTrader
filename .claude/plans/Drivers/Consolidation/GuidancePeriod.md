## Guidance Period

## Current conclusion

Use `GuidancePeriod` as a **guidance-specific required structure**, not as a mandatory structure for every `DriverUpdate`.

Plain shape:

```text
Driver = reusable cause/class
DriverUpdate = event-level fact
GuidancePeriod = target calendar window for guidance facts
```

## Decision

- `Driver` nodes get **no period**.
- `DriverUpdate` with `fact_type = guidance` should have exactly one `HAS_PERIOD -> GuidancePeriod` link.
- This applies to **all** guidance DriverUpdates, whether `company_confirmed = true` or `company_confirmed = false`.
- `DriverUpdate` with `fact_type = metric` or `surprise` should not be forced to use `GuidancePeriod` now. Add it later only if the fact truly needs a fiscal/calendar target period.
- `DriverUpdate` with `fact_type = action_event` should not use `GuidancePeriod`.
- `fact_scope` still exists for all fact types. It separates multiple versions of the same driver fact inside one event, for example `Q1` vs `April`.

## What GuidancePeriod means

`GuidancePeriod` is the calendar window the guided value is about.

Examples:

```text
FY2026 revenue guidance  -> GuidancePeriod = FY2026 calendar/fiscal window
Q2 margin guidance      -> GuidancePeriod = Q2 window
long-term target        -> GuidancePeriod = gp_LT sentinel
```

It is **not**:

- the event date
- the filing date
- a generic time label for every driver fact
- a replacement for `fact_scope`

## Why guidance needs it

Current Guidance production depends on this structure:

- Every `GuidanceUpdate` has exactly one `HAS_PERIOD` edge.
- `period_u_id` is part of the `GuidanceUpdate` identity.
- History queries read `GuidancePeriod.start_date` and `GuidancePeriod.end_date`.
- The CLI computes the final `gp_...` ID from LLM period fields plus deterministic code.

So for `fact_type = guidance`, reusing `GuidancePeriod` preserves current production behavior.

## Why not make it universal

For non-guidance facts, forcing `GuidancePeriod` creates fake structure:

- `action_event` often has no target period.
- many `metric` facts are just event facts, not forward-looking target windows.
- the guidance period resolver can fail closed when fiscal-year-end data is missing.
- adding period everywhere increases prompt and writer complexity without clear value.

Bottom line: use a fact-type profile.

```text
guidance      -> GuidancePeriod required
metric        -> optional later, only for true fiscal/calendar facts
surprise      -> optional later, only for true fiscal/calendar facts
action_event  -> off
```

`company_confirmed` is separate. It tells who confirmed the guidance; it does not change whether the guidance fact needs a period.

## Driver integration shape

For `fact_type = guidance`:

- producer emits guidance period fields, such as `fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_*`, `sentinel_class`, `time_type`
- code computes `period_u_id`, `gp_start_date`, `gp_end_date`, and `period_scope`
- writer links `DriverUpdate -[:HAS_PERIOD]-> GuidancePeriod`
- code may use the period when composing `fact_scope`, but the period node stores the real dates

For other fact types:

- keep using `fact_scope` for same-event distinctions
- do not create a `GuidancePeriod` unless a later measured need proves it

## Must preserve from Guidance

- calendar-based `gp_YYYY-MM-DD_YYYY-MM-DD` IDs
- sentinel nodes: `gp_ST`, `gp_MT`, `gp_LT`, `gp_UNDEF`
- the existing period routing order
- SEC-cache / existing-period / prediction / fiscal-year-end fallback behavior
- the `HAS_XBRL` race guard before running 10-Q/10-K guidance extraction, so period dates do not split

## Later checks before build

- confirm Driver producer has company fiscal-year-end available before calling the resolver
- run guidance sample-equivalence: same source should produce the same period IDs as current Guidance extraction
- ensure `GuidancePeriod` is invoked only behind a `fact_type = guidance` gate at first
- decide later whether any `metric` or `surprise` producer has enough period-heavy use cases to opt in

## Simplest modular reuse plan

Yes, there is a simple modular path. Do **not** have DriverUpdate import `guidance_write_cli._ensure_period()` directly.

Why not:

- `_ensure_period()` is the right logic, but it currently lives inside the full Guidance write CLI.
- importing the CLI also pulls in guidance writer, concept resolution, member resolution, hard-coded paths, and write-mode concerns.
- DriverUpdate only needs period resolution, not the whole Guidance write stack.

Best shape:

```text
new shared module:
  guidance_period_resolver.py

Guidance write CLI:
  imports guidance_period_resolver.ensure_guidance_period()

DriverUpdate writer:
  imports guidance_period_resolver.ensure_guidance_period()
  calls it ONLY when fact_type = guidance
```

This mirrors the unit resolver decision: one small shared module, both systems call it, no duplicated logic.

## What moves into the shared module

Move the current period-only logic out of `guidance_write_cli.py` into `guidance_period_resolver.py`:

- `_ensure_period()`
- `_lookup_existing_period()`
- `_lookup_sec_cache()`
- `_predict_from_prev_quarter()`
- `_get_sec_corrected_fye()`
- lazy Redis / Neo4j connection helpers used only for period resolution
- call to `build_guidance_period_id()` from `guidance_ids.py`

Keep `build_guidance_period_id()` itself where it is. It is already the pure deterministic period builder.

Public API should stay boring and small:

```python
ensure_guidance_period(item: dict, *, fye_month: int | None, ticker: str | None = None) -> dict
```

It should mutate/populate the same fields current Guidance uses:

```text
period_u_id
period_scope
time_type
gp_start_date
gp_end_date
```

## DriverUpdate call site

Inside the future DriverUpdate writer:

```python
if fact_type == "guidance":
    ensure_guidance_period(item, fye_month=company_fye_month, ticker=ticker)
    # then MERGE DriverUpdate and HAS_PERIOD
else:
    # do not call period resolver
```

Graph write shape for guidance DriverUpdates:

```cypher
MERGE (gp:GuidancePeriod {id: $period_u_id})
  ON CREATE SET gp.u_id = $period_u_id,
                gp.start_date = $gp_start_date,
                gp.end_date = $gp_end_date

MERGE (du)-[:HAS_PERIOD]->(gp)
```

Also create only the period constraint/sentinels needed by Driver:

```cypher
CREATE CONSTRAINT guidance_period_id_unique IF NOT EXISTS
FOR (gp:GuidancePeriod) REQUIRE gp.id IS UNIQUE

MERGE (gp:GuidancePeriod {id: 'gp_ST'})    SET gp.u_id='gp_ST',    gp.start_date=null, gp.end_date=null
MERGE (gp:GuidancePeriod {id: 'gp_MT'})    SET gp.u_id='gp_MT',    gp.start_date=null, gp.end_date=null
MERGE (gp:GuidancePeriod {id: 'gp_LT'})    SET gp.u_id='gp_LT',    gp.start_date=null, gp.end_date=null
MERGE (gp:GuidancePeriod {id: 'gp_UNDEF'}) SET gp.u_id='gp_UNDEF', gp.start_date=null, gp.end_date=null
```

## Exactness checks before wiring

Before DriverUpdate uses it:

1. move the logic without behavior changes
2. make `guidance_write_cli.py` call the shared function
3. run parity tests: old `_ensure_period()` output vs new `ensure_guidance_period()` output
4. test these cases at minimum:
   - quarter
   - annual
   - half
   - month
   - long range
   - short/medium/long/undefined sentinel
   - instant item
   - missing fiscal-year-end raises
   - existing `period_u_id` is preserved
5. run a sample-equivalence check against current Guidance extraction before retiring old Guidance nodes

## Nuances to preserve

- The LLM does **not** compute final period IDs. It only emits period fields like `fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_*`, `calendar_override`, `sentinel_class`, and `time_type`.
- Code computes the final `gp_...` ID.
- `fye_month` is required when dates must be computed.
- The resolver fails closed if needed fiscal-year-end data is missing.
- `company_confirmed` does not affect period resolution.
- `GuidancePeriod` is still used only for `fact_type = guidance` at first.
- If old `GuidanceUpdate` nodes are later retired, the "reuse existing period" lookup must be reviewed so it can also see the new guidance `DriverUpdate` path, not only old `GuidanceUpdate` nodes.

## Modular import — verified (2026-06-20)

**Proven in isolation** (system python, NO Neo4j/Redis loaded): `build_guidance_period_id(fye_month=12, fiscal_year=2025, fiscal_quarter=3)` → `gp_2025-07-01_2025-09-30`; `sentinel_class='long_term'` → `gp_LT`; omit `fye_month` → hard error. The period **math** is pure stdlib (+ the `fiscal_math` sibling) and imports exactly like `unit_resolver.py`.

### Two layers — pick the split on purpose
The design above (`guidance_period_resolver.py`) is the **full** version. It is **NOT** as light as `unit_resolver`, because the cascade it moves carries infra:

| | **(A) pure math only** | **(B) full cascade** *(the design above)* |
|---|---|---|
| Wraps | `build_guidance_period_id` | + `_lookup_existing_period` (Neo4j) · `_lookup_sec_cache` · `_predict_from_prev_quarter` · `_get_sec_corrected_fye` (Redis) |
| Needs infra | **none** | **Neo4j + Redis** |
| Dates | clean month-boundaries (can be ~1 month off for 52/53-week filers, e.g. Apple/retail) | **SEC-exact** |
| Touches production | no (sandbox/test) | yes (moves code out of `guidance_write_cli.py`) |
| = unit work | Steps 1-3 (prove the core) | Steps 5-7 (wire to production) |

**A = optional sandbox proof · B = the required final path.** The pure core is **already proven** to import + compute correctly (see the import proof above), so (A) — a full reusable wrapper + tests — is only worth building if you want a proof artifact right now. **(B) is the real target** (production guidance needs the Redis/Neo4j cascade for exact dates); build it **only when wiring DriverUpdate guidance to production** — not during this design phase.

### Verified footguns (new — add to the lists above)
- **Never silent-default FYE to December.** Keep the hard raise. Two OTHER code paths (`get_derived_fye`, the earnings builder) DO default to 12 — copying them hides a wrong-period bug.
- **`HAS_XBRL` guard = PLANNED, not shipped** (described in `GuidanceTrigger.md:9`, absent from `guidance_trigger_daemon.py`); it's a producer-eligibility gate, NOT the resolver's job → in "Must preserve" above, **ADD** it, don't "preserve" it.
- **`period_u_id` feeds the `guidance_update_id` hash** → changing a period changes the fact's identity (matters for regenerate-equivalence).
- **Periods are write-once** (`ON CREATE SET`) — a node first written with wrong dates won't self-correct on re-run.
- **SEC date/FYE Redis keys are loaded by `sec_quarter_cache_loader.py`, not `warmup_cache`** — running warmup does NOT prime them.
- **Routing is first-match-wins** (sentinel > long_range_end_year > month > half > fiscal_quarter > fiscal_year) — emit ONLY the fields for the stated period.
- **`time_type=instant`** also fires from a `driver_name` in 6 balance-sheet labels (`cash_and_equivalents, total_debt, long_term_debt, shares_outstanding, book_value, net_debt`); it collapses dates to `gp_{end}_{end}`. Pass `driver_name` through so this matches production.

---

## Findings & cross-check (2026-06-20) — 5-lens analysis + ChatGPT

**This CONFIRMS the decision above.** A 5-angle analysis (semantic fit · read-time queries · structural uniformity · producer complexity · redundancy-vs-`fact_scope`) all independently converged on the same answer, and ChatGPT agreed. Recorded so the reasoning isn't lost.

### Final simple answer (ChatGPT, agreed)
- `GuidancePeriod` = **required for guidance only**, regardless of `company_confirmed`.
- `metric` / `surprise` = **optional later, only with extra care** (see the ⚠️ caveat below).
- `action_event` = **never**.
- `fact_scope` still separates `Q1` vs `April` inside one event.

### The precise wording (ChatGPT correction — adopted)
An earlier framing said a metric's period ≈ "the event date." That is **wrong**: the event date is *statement-time* (a May 10-Q is dated May), while the period the metric covers is *Q1* (earlier). Correct version:
- **metric / surprise:** period-like wording stays in **`fact_scope` for now**, NOT a `GuidancePeriod` node.
- **guidance:** the future target window gets a `GuidancePeriod` node.
- **action_event:** never.
- *Refinement (independent):* `fact_scope` only **structures** the period when the source states it cleanly (`"Q1"`); otherwise it falls to `hash(quote)` and the period sits only in the text. So a metric/surprise **reporting** period is **not first-class queryable today** — which is exactly why it stays "optional later, with care," not solved now.

### ⚠️ Direction-collision — the one new, load-bearing caveat
If we ever let `metric`/`surprise` use period nodes, **do NOT blindly share the same `GuidancePeriod` node**:
- A **guided** FY2025 window and a **reported/actual** FY2025 window are the **identical `gp_` id** — same calendar window, opposite meaning (a *forecast* vs a *result*).
- The live Guidance history key is `(metric_id, basis_norm, segment_slug, period_scope, resolved_unit, time_type)`. It has **no forecast-vs-actual direction field**. A future unified query must not let forecast rows and actual rows collapse into one bucket just because the calendar window matches.
- **Fix:** use a SEPARATE reporting-period entity (or add a direction discriminator) — never reuse the guidance node blind. And the opt-in must only take a *stated* window, never freshly **derive** one, or it re-opens the period-race duplicate bug.

### Bottom line — why a shared period node exists at all
It earns its keep ONLY where **many separate facts converge on ONE window** — true for guidance, nowhere else:
- cross-company **"FY2025 guidance consensus"** (many firms → one future window)
- one company's **FY2025 guidance evolving across Q1→Q2→Q3 calls** (re-guidance → revision history collects on one shared anchor)

Backward facts (`metric`/`surprise`) state their period once and do not need the guidance revision anchor. For now, the event + `fact_scope` capture enough for storage; first-class reporting-period queries are deferred. `action_event` has no fiscal window at all.

### You already decided this (precedent — verified)
`GuidanceDriverConsolidation.md` already locks the same shape: **§6.1** per-fact_type "profile" (ON only where the fact has a period) · **§5.5** "Periods = guidance-scoped win… never force a period (a CEO resignation has no quarter)" · **Bucket 4** wires period behind a `fact_type=='guidance'` gate · the period resolver **fails closed / RAISES** without a fiscal-year-end — so the gate prevents a *crash* on action_event, not just a mis-tag.

### Period-specific open points to confirm
- Document the metric/surprise opt-in as DEFERRED-but-OFF now, or leave it out entirely until a fiscal producer asks?
- If the opt-in ever turns on: a SEPARATE reporting-period entity, or the shared node + a direction marker?
- Confirm `HAS_PERIOD` is strictly **per-DriverUpdate** (one event → many updates → each with its own period or none), mirroring guidance's 1:1 fan-out.

*(The broader 29-question guidance-migration checklist — IDs, XBRL, company_confirmed, amendments, dedup, node-label L1/L2/L3, regenerate-not-migrate — lives with the consolidation plan; ask if you want it dropped here too.)*
