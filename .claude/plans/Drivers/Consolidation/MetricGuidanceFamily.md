# Metric / Guidance / Surprise / Action — the family, in plain English

*Plain-English companion to the locked rule. Source of truth = `WIP/DriverGraphSchema.md:225-232` (the `BASE_METRIC` metric-family rule) + this folder's `README.md:52-60`. If they ever disagree, the schema wins.*

**One idea:** the same topic (e.g. "revenue") shows up in different **flavors** — a forecast, a result, a beat. We keep them as **separate Drivers, but linked.** *Related, never merged.*

## The 4 flavors (`fact_type`)
A **Driver** = a reusable cause (a labeled folder). Its `fact_type` = its flavor, set **once**, permanent:

| Flavor | Plain meaning | Example words |
|---|---|---|
| **metric** | a real number you can re-read | "revenue **was** $5B" |
| **guidance** | the company's own **forecast** | "we **expect** $6B" |
| **surprise** | actual **vs** what was expected | "revenue **beat** by $0.2B" |
| **action_event** | a one-off thing that happened | "CEO resigned" · "$2B buyback" |

## The decision: different names, but linked
```
revenue            (metric)
revenue_guidance   (guidance)   ─┐
revenue_surprise   (surprise)   ─┴─ BASE_METRIC ─►  revenue
```
**Why separate?** Different **tradeable signals** — they can move the stock **opposite ways the same day**:
> *"We beat this quarter… but cut next year's guidance."* → stock **DOWN.**

Mash them into one "revenue" and you lose *which* signal moved the stock — the whole point.

**Why linked?** So you can ask *"did revenue beat its **own** forecast?"* — follow the arrows.

> **RELATED, never SAME.** *Same* = one merged number (never, for flavors). *Related* = separate folders + an arrow.

## One example, start to finish
> *"Revenue **was $5B**, **beating the $4.8B** estimate. We **expect $6B** next year. We also **authorized a $2B buyback**."*

```
"revenue was $5B"             → revenue          (metric)        state: increased   ◄─┐
"beating the $4.8B estimate"  → revenue_surprise (surprise)      state: beat      ──┤ BASE_METRIC
"we expect $6B next year"     → revenue_guidance (guidance)      state: introduced ──┘
"authorized a $2B buyback"    → share_repurchase (action_event)  state: announced   ✗ NO base metric
```
Each driver's **state word** comes from a flavor-specific list (you can't put "beat" on a metric, or "raised" on a result) — another reason they must be separate.

## The rules (with every gotcha)
- **Exactly one base, required.** Every `_guidance`/`_surprise` has one `BASE_METRIC` arrow to a metric. A validator enforces it → **catches an orphan** (`revenue_guidance` with no `revenue`).
- **Why an arrow, not name-guessing?** Only an arrow lets us *enforce* "exactly one" and catch orphans. (That's its real value — **not** solving synonyms.)
- **Base must exist** → create it in the same run if missing. *Edge:* the base may be **empty** (only ever forecast, never reported) — fine, a latent folder.
- **Only the END suffix counts.** `cost_guidance` → family (base `cost`). `guidance_revision_cost` ("guidance" in the *middle*) → **not** family.
- **`action_event` gets NO base.** One action touches **many** metrics (a buyback hits eps + share_count + cash) — many-to-many. Its link to metrics comes from **evidence/events** — the same Event, and **sometimes across multiple events over time** (a buyback authorized in Q1 shows up in share-count over later quarters). **No source-of-truth identity arrow**; if ever cached for search, it must be a **derived, non-identity** cache that never `SAME_AS` and never merges series.
- **Synonyms are a separate machine.** If "net sales" = "revenue," those two **metrics** are tied by **`SAME_AS`** (not `BASE_METRIC`):
  ```
  net_sales_guidance ─BASE_METRIC─► net_sales ─SAME_AS─► revenue
  ```
  *Edge:* miss a synonym → a **missing** comparison (safe), never a **wrong** merged number (dangerous).
- **`fact_type` stays** even though the name says `_guidance`. The suffix is just readable text (bare `revenue` has none); `fact_type` is the clean machine-label that picks the state list + whether to attach a guidance period.

## How we pick the flavor (the tricky calls)
- **Persistence test:** *"Is there a standing number I could re-read next quarter?"* **Yes → metric · No → action_event.** (`_surprise`/`_guidance` override.)
- **Future *value* vs future *action*:** "expect **$6B revenue**" → guidance (+ base metric). "expect the **FDA to approve** the drug" → action_event (no number → no base).
- **Dual framing allowed:** `dividend` (action_event — the *act*) vs `dividend_per_share` (metric — the *amount*). Same topic, two flavors, two drivers.

## The one rule underneath all of it
> **Over-merging is permanent; under-linking is recoverable.**
- Wrongly merge a forecast + a result into one number → the predictor can never untangle it → bad trades forever.
- Forget to *link* two related drivers → you just miss a comparison → fix it later.

So we **always err toward separate**, and add **links** (never merges) to say "these are related."

---
*Two adjacent guidance-only decisions (covered elsewhere): a guidance fact also gets a **GuidancePeriod** (the future window it's about — see `GuidancePeriod.md`) and a **`company_confirmed`** flag. Neither applies to metric/surprise/action.*
