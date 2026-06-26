# DriverPeriod Consolidation

> **STATUS (2026-06-26) — DESIGN LOCKED · BUILD/VERIFY PENDING.** The decisions in this doc are final; the implementation is not. Open gates before production:
> - ⬜ extract `driver_period_resolver.py` (the cascade still lives in the Guidance write CLI)
> - ⬜ pass the 21 "Required Tests Before Wiring" (§Required Tests Before Wiring)
> - ⬜ prove the YTD/TTM math (Dec-FYE **and** non-Dec-FYE examples) before coding — pseudocode is unverified
> - ⬜ **decide the transition strategy** — regenerate guidance as DriverUpdate facts **vs** dual-label existing period nodes (the one genuinely open *decision*; §Cypher Shape)
> - ⬜ write-once-date hardening (parity tests + constraints; `ON CREATE SET` won't self-correct wrong dates — Guard 5)
> - ⬜ ship the `HAS_XBRL` race guard as a producer eligibility check (§Exactness Notes)
>
> These are build/verify gates, not redesigns — everything below is the locked target design.

## Final Decision

Replace the Driver-side concept of `GuidancePeriod` with a generic `DriverPeriod`.

Plain shape:

```text
Driver        = reusable cause/class, e.g. revenue, revenue_guidance
DriverUpdate  = one event-level fact about a Driver
DriverPeriod  = resolved calendar date window, e.g. gp_2025-01-01_2025-03-31

DriverUpdate -[:HAS_PERIOD]-> DriverPeriod
```

The period mechanism comes from Guidance. The name changes because the node is no longer guidance-only.

## Why This Changed

The older decision was: use `GuidancePeriod` only for `fact_type = guidance`.

That is now stale.

Reason: raw period text like `Q1` is not reliable enough.

```text
Company with Dec fiscal year: Q1 FY2025 = 2025-01-01 to 2025-03-31
Company with Sep fiscal year: Q1 FY2025 = 2024-10-01 to 2024-12-31
```

So a plain `period=Q1` string cannot safely compare facts across companies or even across fiscal calendars. Guidance already solved this by turning fiscal fields into a real calendar window. DriverUpdate should reuse that same solved mechanism.

## What DriverPeriod Means

`DriverPeriod` means only this:

```text
the calendar date window this DriverUpdate is about
```

Examples:

```text
FY2025 revenue guidance         -> DriverPeriod = FY2025 resolved date window
Q1 revenue was $5B              -> DriverPeriod = Q1 resolved date window
Q1 revenue beat consensus       -> DriverPeriod = Q1 resolved date window
CEO resigned                    -> no DriverPeriod
long-term margin target         -> DriverPeriod = gp_LT
going-forward guidance          -> DriverPeriod = gp_UNDEF
```

It is not:

- the event date
- the filing date
- the announcement date
- the source date
- a free-text label like `Q1`
- the thing that says forecast vs actual
- a replacement for `fact_scope`

Forecast vs actual comes from the `Driver.fact_type`, not from the period node.

## Node Name

Use `DriverPeriod`, not `Period`.

Reason: the graph already has an XBRL `Period` label for XBRL facts/contexts. Reusing `Period` would mix two concepts that are used by different pipelines.

Use `DriverPeriod`, not `GuidancePeriod`.

Reason: the target Driver design attaches the same resolved-period structure to period-bearing `metric`, `guidance`, `surprise`, and rare period-bearing `action_event` facts.

Keep the existing `gp_` ID prefix.

```text
Node label: DriverPeriod
ID value:   gp_2025-01-01_2025-03-31
```

Do not rename IDs to `dp_...`. The `gp_` prefix is what the proven Guidance period code already returns, and keeping it avoids translation/migration work.

## Graph Shape

Use one edge type:

```text
(:DriverUpdate)-[:HAS_PERIOD]->(:DriverPeriod)
```

Do not create separate edge names like `TARGETS_PERIOD`, `REPORTS_PERIOD`, or `OCCURS_DURING`.

Why: the same edge is enough. The meaning comes from the Driver's `fact_type`:

```text
guidance  + HAS_PERIOD -> future target window
metric    + HAS_PERIOD -> reported/covered window
surprise  + HAS_PERIOD -> actual-vs-expectation window
action_event + HAS_PERIOD -> rare stated action window/duration
```

## By Fact Type

| `fact_type` | DriverPeriod rule | Example |
|---|---|---|
| `guidance` | required | `FY2025 revenue guidance` |
| `metric` | used when the fact has a stated, source-implied, or code-derivable reported period | `Q1 revenue was $5B` |
| `surprise` | used when the fact has a stated, source-implied, or code-derivable reported period | `Q1 EPS beat consensus` |
| `action_event` | rare/optional; only when the action itself has a real stated window/duration | `three-year restructuring plan` |

Important:

- Do not force a period onto every fact.
- If the fact has a real period window, resolve it.
- If the fact has no real period window, do not attach `HAS_PERIOD`.
- For `fact_type = guidance`, both `company_confirmed = true` and `company_confirmed = false` still require a period. Confirmation says who confirmed the guidance; it does not change the period rule.

## Implied Reported Periods

For `metric` and `surprise`, the period may be implied by the source event even when the sentence does not restate it.

Example:

```text
Q1 10-Q / Q1 earnings release says: "revenue grew 12%"
```

The sentence does not say `Q1`, but the event/report is Q1. Resolve to the event's Q1 `DriverPeriod`, not `gp_UNDEF` and not no-period.

Rule:

```text
metric/surprise + omitted period + one clear event/report period
-> derive DriverPeriod from event/report metadata
```

Use this only when the period is deterministic from the source event, such as:

- filing/report period
- earnings release period
- transcript event period
- XBRL/report context already tied to the quoted fact

Do not guess from vague wording. If the source/event does not give one clear period, do not invent one.

```text
clear Q1 report context      -> use Q1 DriverPeriod
clear FY report context      -> use FY DriverPeriod
ambiguous market/news item   -> no DriverPeriod unless dates/window are stated
```

Source-type caution:

```text
10-Q / 10-K reported metrics -> wait for / prefer XBRL or SEC exact dates when available.
8-K / transcript / news      -> do NOT require XBRL; use Guidance-style period fields only when the source or event gives a clear fiscal/calendar anchor.
```

For 8-Ks specifically: if the source says `Q3 revenue`, `FY2025 guidance`, or gives exact dates, resolve a `DriverPeriod`. If it only says `revenue improved`, do not invent a period.

## Exact-Date Windows For YTD / TTM / Cumulative Facts

Do not collapse YTD/TTM/cumulative facts into only the discrete quarter.

This must be added to the shared Guidance period mechanism, not implemented as a separate Driver-only period system.

If the source or code gives exact start and end dates, store the exact window:

```text
Q3 revenue                       -> gp_2025-07-01_2025-09-30
nine months ended Sep 30, 2025   -> gp_2025-01-01_2025-09-30
TTM ended Sep 30, 2025           -> gp_<exact_12mo_start>_2025-09-30
```

Minimal builder extension:

```text
period_start_date + period_end_date -> gp_<start>_<end>
```

This is an exact-date path, not a new period ontology. It is needed because Guidance's existing period fields cover quarter / half / annual / month / long-range / sentinels, but not every reported metric shape such as nine-month YTD or TTM.

Priority:

```text
exact source/XBRL start_date + end_date first
else FYE-aware computed dates
else no period
```

Why: some companies use 52/53-week calendars, so month-boundary fiscal math can be slightly wrong. When the filing/XBRL gives exact dates, those exact dates win.

Rules:

- Use exact dates only when source-stated or deterministically available from report/XBRL metadata.
- Code validates ISO dates and `start_date <= end_date`.
- Code builds `period_u_id`; the LLM never writes it directly.
- If dates are not exact, do not guess. Keep the detail in `quote` and use `quote_hash` if identity must split.
- For this exact-date path, `period_scope = exact_range` and `time_type = duration`, unless start and end are the same day, in which case `time_type = instant`.

## Periodless Actions

Do not use `gp_UNDEF` for periodless actions.

```text
CEO resigned              -> no HAS_PERIOD
buyback authorized today  -> no HAS_PERIOD unless a real program window is stated
store closed permanently  -> no HAS_PERIOD unless the source gives a real period/window
```

Why: `gp_UNDEF` means "there is a period-like horizon, but it is undefined." A CEO resignation has no period-like horizon. Giving all such actions `gp_UNDEF` would create fake structure.

Periodless action identity is handled by:

```text
event + driver + fact_scope
```

If two actions under the same Driver appear in one event and need separation, the slice part of `fact_scope` must separate them, using a clean slice when available or `quote_hash=<hash>` as fallback.

## Sentinels

Keep Guidance sentinels exactly:

| sentinel | meaning | Use |
|---|---|---|
| `gp_ST` | short-term horizon | period-like, no exact dates |
| `gp_MT` | medium-term horizon | period-like, no exact dates |
| `gp_LT` | long-term horizon | period-like, no exact dates |
| `gp_UNDEF` | period-like horizon exists but is undefined | e.g. "going forward" guidance |

Do not use sentinels for facts with no time-window concept at all.

```text
"long-term target"    -> gp_LT
"going forward"       -> gp_UNDEF
"CEO resigned"        -> no DriverPeriod
```

## Reusing Guidance Mechanism

Yes, DriverUpdate can reuse the Guidance period mechanism.

Reuse exactly:

- `build_guidance_period_id()`
- `gp_YYYY-MM-DD_YYYY-MM-DD` ID shape
- `gp_ST`, `gp_MT`, `gp_LT`, `gp_UNDEF`
- fiscal-year-end math
- `calendar_override`
- `time_type`
- instant-period collapse
- existing-period lookup
- SEC cache lookup
- previous-quarter prediction
- SEC-corrected fiscal-year-end lookup
- fail-closed behavior when required fiscal-year-end data is missing

Add these minimal extensions to the shared Guidance period mechanism:

- direct exact-date input: `period_start_date + period_end_date -> gp_<start>_<end>`
- `period_scope = ytd`
- `period_scope = ttm`

Implementation note: add this in the future shared `driver_period_resolver` wrapper, not inside pure `build_guidance_period_id()`. Expected incremental code is small: exact-date branch + YTD fallback + optional TTM fallback + one helper/label update, roughly 15-20 lines total.

Implementation sketch for the next bot:

```text
Known-safe:
1. If exact start_date + end_date are present, build:
   u_id = gp_<start_date>_<end_date>
   start_date = exact start_date
   end_date = exact end_date

2. Otherwise call existing Guidance period code for quarter / half / annual / month / long-range / sentinels.

Needs verification with tests before coding:
3. YTD fallback: compute FY-start through stated period end.
4. TTM fallback: compute trailing 12-month window through stated period end.
```

Do not copy untested pseudocode directly. The next bot must prove YTD/TTM with Dec-FYE and non-Dec-FYE examples before wiring.

Do not let the LLM compute final period IDs. The LLM only emits period fields. Code computes the final `period_u_id`.

## What Can Be Used As-Is

### Pure Builder: yes, as-is

`build_guidance_period_id()` can be used as-is.

Verified behavior:

```text
build_guidance_period_id(fye_month=12, fiscal_year=2025, fiscal_quarter=1)
-> gp_2025-01-01_2025-03-31

build_guidance_period_id(fye_month=9, fiscal_year=2025, fiscal_quarter=1)
-> gp_2024-10-01_2024-12-31

build_guidance_period_id(fye_month=12, sentinel_class="long_term")
-> gp_LT
```

It is pure period math. It does not need Neo4j or Redis.

### Full Cascade: reuse behavior, but extract into a shared module

The full Guidance period path is correct, but it currently lives inside the Guidance write CLI.

Final shape:

```text
shared module:
  driver_period_resolver.py

Guidance writer:
  calls driver_period_resolver.ensure_driver_period(...)

DriverUpdate writer:
  calls driver_period_resolver.ensure_driver_period(...)
```

Move/reuse these period-only pieces from Guidance:

- `_ensure_period()`
- `_lookup_existing_period()`
- `_lookup_sec_cache()`
- `_predict_from_prev_quarter()`
- `_get_sec_corrected_fye()`
- Redis/Neo4j helpers needed only for period resolution
- call into `build_guidance_period_id()`

The behavior should remain the same. The graph label and call gates change.

## Public API Shape

Use one boring function:

```python
ensure_driver_period(
    item: dict,
    *,
    fact_type: str,
    fye_month: int | None,
    ticker: str | None = None,
    calendar_override: bool = False,
) -> dict | None
```

Return/populate:

```text
period_u_id
period_scope
time_type
gp_start_date
gp_end_date
```

Return `None` only when the fact truly has no period window.

Do not silently default missing fiscal-year-end to December.

## Producer Input Contract

The producer may emit period fields such as:

```text
period_start_date
period_end_date
fiscal_year
fiscal_quarter
half
month
long_range_start_year
long_range_end_year
calendar_override
sentinel_class
time_type
```

Rules:

- Emit only the fields needed for the period stated in the source.
- Prefer exact source/XBRL `period_start_date` + `period_end_date` over computed fiscal math whenever exact dates are available.
- Routing is first-match-wins:
  1. exact `period_start_date` + `period_end_date`
  2. `sentinel_class`
  3. `long_range_end_year`
  4. `month`
  5. `half`
  6. `fiscal_quarter`
  7. `fiscal_year`
  8. fallthrough `gp_UNDEF`
- Do not emit conflicting period fields.
- Do not write `period_u_id` directly unless it came from code.
- For omitted metric/surprise periods, code may derive period fields from event/report metadata before calling the resolver.

## DriverUpdate Identity

`DriverPeriod` is an edge for traversal and date queries.

The period must also be reflected in `fact_scope`, because `fact_scope` is part of the `DriverUpdate` identity key.

When a period exists:

```text
fact_scope includes: period=<period_u_id>
```

Examples:

```text
Q1 revenue fact
fact_scope = period=gp_2025-01-01_2025-03-31

Q1 franchise same-store-sales fact
fact_scope = period=gp_2025-01-01_2025-03-31|slice=channel:franchised

periodless CEO resignation
fact_scope = default or quote_hash=<hash>, no HAS_PERIOD
```

Never use raw `Q1`, `FY2025`, or `April` as the final identity token. Resolve to `gp_...` first.

The edge and `fact_scope` must be composed from the same `period_u_id`.

Validator:

```text
if DriverUpdate has HAS_PERIOD -> DriverPeriod(id=X)
then fact_scope must contain period=X

if fact_scope contains period=X
then DriverUpdate must have HAS_PERIOD -> DriverPeriod(id=X)
```

No hand-built duplicate period strings.

## Properties

`DriverPeriod` stores dates only:

```text
id
u_id
start_date
end_date
```

Keep these on `DriverUpdate`, not on `DriverPeriod`:

```text
fiscal_year
fiscal_quarter
period_scope
time_type
```

Why: the same calendar window can be described differently by different companies or sources. The node is the shared date window; the update keeps the source-specific fiscal framing.

These `DriverUpdate` fields are provenance / source framing only. The authoritative grouping key is the resolved `period_u_id` plus the `DriverPeriod` dates. Never recompute grouping from raw `fiscal_year` or `fiscal_quarter` after write.

## Cypher Shape

```cypher
MERGE (dp:DriverPeriod {id: $period_u_id})
  ON CREATE SET dp.u_id = $period_u_id,
                dp.start_date = $gp_start_date,
                dp.end_date = $gp_end_date

MERGE (du)-[:HAS_PERIOD]->(dp)
```

Constraint:

```cypher
CREATE CONSTRAINT driver_period_id_unique IF NOT EXISTS
FOR (dp:DriverPeriod) REQUIRE dp.id IS UNIQUE
```

Sentinels:

```cypher
MERGE (dp:DriverPeriod {id: 'gp_ST'})
  SET dp.u_id='gp_ST', dp.start_date=null, dp.end_date=null

MERGE (dp:DriverPeriod {id: 'gp_MT'})
  SET dp.u_id='gp_MT', dp.start_date=null, dp.end_date=null

MERGE (dp:DriverPeriod {id: 'gp_LT'})
  SET dp.u_id='gp_LT', dp.start_date=null, dp.end_date=null

MERGE (dp:DriverPeriod {id: 'gp_UNDEF'})
  SET dp.u_id='gp_UNDEF', dp.start_date=null, dp.end_date=null
```

During transition from old Guidance nodes, either regenerate guidance as DriverUpdate facts or dual-label existing guidance period nodes. Do not create duplicate `gp_...` windows with different labels in the final target.

If the existing lookup still searches `GuidancePeriod`, update it to search `DriverPeriod` in the final path. During transition only, it may search both labels so old guidance periods and new driver periods do not fork.

## Read-Time Guardrails

### Guard 1: never group by period alone

`DriverPeriod` does not say forecast vs actual.

This is safe:

```text
revenue_guidance + gp_2025...  -> forecast bucket
revenue          + gp_2025...  -> actual bucket
revenue_surprise + gp_2025...  -> surprise bucket
```

This is unsafe:

```text
all facts with gp_2025... -> one numeric series
```

Any read path using `DriverPeriod` must keep enough identity:

```text
Driver / fact_type / BASE_METRIC family / company / unit / time_type
```

Do not strip `_guidance` or `_surprise` and then merge those rows into the base metric numeric series.

### Guard 2: no fake period for no-time facts

No real period window means no `HAS_PERIOD`.

Use `gp_UNDEF` only for period-like wording that is undefined.

### Guard 3: market-wide facts use calendar mode

Some Drivers do not belong to a company fiscal calendar:

```text
oil_price
fed_funds_rate
commodity_price
minimum_wage
```

For those, use calendar mode / `calendar_override = true`. Do not require company fiscal-year-end.

This already exists in Guidance period code: `calendar_override = true` forces FYE month to December.

`time_type` also already exists:

```text
duration -> full window, e.g. gp_2025-01-01_2025-12-31
instant  -> one-day window at period end, e.g. gp_2025-12-31_2025-12-31
```

### Guard 4: fail closed

If a period-bearing company fact needs fiscal-year-end data and it is missing, raise an error. Do not guess December.

### Guard 5: write-once date caution

Guidance currently writes period dates with `ON CREATE SET`. A period node first created with wrong dates will not self-correct on rerun. Keep parity tests and constraints before production wiring.

### Guard 6: instant and duration are different windows

An instant period and a duration period are intentionally different nodes:

```text
duration FY2025 -> gp_2025-01-01_2025-12-31
instant FY2025  -> gp_2025-12-31_2025-12-31
```

This is correct. Do not merge them.

## Exactness Notes From Current Guidance

These are real Guidance behaviors to preserve:

- `GuidanceUpdate` currently has exactly one `HAS_PERIOD -> GuidancePeriod`.
- `period_u_id` is part of Guidance identity.
- Guidance history reads `GuidancePeriod.start_date` and `GuidancePeriod.end_date`.
- Current Guidance writer creates `GuidancePeriod` by `MERGE` on `period_u_id`.
- `build_guidance_period_id()` returns `{u_id, start_date, end_date, period_scope, time_type}`.
- Existing Guidance fields do not cover every metric period shape; add the exact-date path plus `ytd`/`ttm` period scopes to the shared Guidance period mechanism.
- Known instant labels include:
  - `cash_and_equivalents`
  - `total_debt`
  - `long_term_debt`
  - `shares_outstanding`
  - `book_value`
  - `net_debt`
- `time_type = instant` collapses start/end to the end date.
- `calendar_override = true` forces calendar periods instead of company fiscal periods.
- Missing required FYE should raise.
- SEC date/FYE Redis keys are loaded by `sec_quarter_cache_loader.py`, not by generic warmup.
- `HAS_XBRL` race guard is planned in Guidance docs but not shipped in the daemon; add it as a producer eligibility guard, not inside the period resolver.

## Required Tests Before Wiring

These must pass before DriverUpdate uses the shared resolver:

1. old Guidance `_ensure_period()` output equals new `ensure_driver_period()` output for the same guidance item
2. quarter period
3. annual period
4. half-year period
5. month period
6. long-range period
7. `gp_ST`, `gp_MT`, `gp_LT`, `gp_UNDEF`
8. `time_type = instant`
9. known instant label, such as `cash_and_equivalents`
10. `calendar_override = true`
11. missing required FYE raises, no December default
12. existing `period_u_id` is preserved
13. `metric`, `guidance`, and `surprise` facts with the same `gp_...` stay in separate read buckets
14. periodless `action_event` gets no `HAS_PERIOD`
15. `fact_scope` includes `period=<period_u_id>` whenever a period exists
16. omitted metric/surprise period derives from event/report period when exactly one clear period exists
17. YTD / cumulative exact-date window creates `gp_<start>_<end>`, not just the discrete quarter
18. TTM exact-date window creates `gp_<start>_<end>`
19. `HAS_PERIOD` target id equals the `period=` token inside `fact_scope`
20. exact source/XBRL dates win over computed month-boundary dates
21. `period_scope = ytd` and `period_scope = ttm` are accepted

## Examples

| Source text | `fact_type` | Driver | Period result |
|---|---|---|---|
| `We expect FY2025 revenue of $6B` | `guidance` | `revenue_guidance` | `HAS_PERIOD -> DriverPeriod(gp_FY2025 dates)` |
| `Q1 revenue was $5B` | `metric` | `revenue` | `HAS_PERIOD -> DriverPeriod(Q1 dates)` |
| `10-Q says "revenue grew 12%"` | `metric` | `revenue` | derive Q1/FY period from report metadata if exactly clear |
| `nine months ended Sep 30 revenue` | `metric` | `revenue` | exact-date DriverPeriod, e.g. `gp_2025-01-01_2025-09-30` |
| `TTM revenue ended Sep 30` | `metric` | `revenue` | exact-date DriverPeriod for the 12-month window |
| `Q1 revenue beat consensus` | `surprise` | `revenue_surprise` | `HAS_PERIOD -> DriverPeriod(Q1 dates)` |
| `CEO resigned` | `action_event` | `ceo_succession` | no `HAS_PERIOD` |
| `three-year restructuring plan` | `action_event` | `corporate_restructuring` | `HAS_PERIOD` only if dates/window can be resolved |
| `long-term margin target` | `guidance` | `margin_guidance` | `HAS_PERIOD -> DriverPeriod(gp_LT)` |
| `going forward, margins should improve` | `guidance` | `margin_guidance` | `HAS_PERIOD -> DriverPeriod(gp_UNDEF)` |
| `oil prices rose 8%` | `metric` | `oil_price` | no fiscal period unless a real calendar window is stated |
| `oil averaged $80/barrel in Q1` | `metric` | `oil_price_per_barrel` | calendar-mode Q1 DriverPeriod |

## Final Rule For A New Bot

If a `DriverUpdate` is about a real stated or code-derivable time window, resolve that window with the Guidance period mechanism and link:

```text
DriverUpdate -[:HAS_PERIOD]-> DriverPeriod
```

Also include the resolved `period_u_id` in `fact_scope`.

If a metric/surprise period is omitted but the event/report has exactly one clear reporting period, derive that period from the event/report metadata.

If the fact is YTD, TTM, or another cumulative exact window, use exact start/end dates and build `gp_<start>_<end>`. Do not collapse it to the discrete quarter.

This exact-date + `ytd`/`ttm` support belongs inside the shared Guidance period mechanism so Guidance and DriverUpdate do not fork.

If the fact has no real time window, do not attach a period.

Use `DriverPeriod` as the target label. Reuse Guidance period math and lookup behavior. Do not reuse the old guidance-only gate.
