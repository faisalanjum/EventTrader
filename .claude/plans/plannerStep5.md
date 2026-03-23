# Step 5: Inter-Quarter Context

Standalone implementation spec for `build_inter_quarter_context()` in `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`.

This file is intentionally self-contained. Another implementer should be able to build Step 5 from this document alone without needing prior chat context.

---

## Goal

Build one canonical artifact, `inter_quarter_context.v1`, that gives the planner and predictor an exact timeline of:

- day-level market tape
- company news
- company filings
- dividends
- splits

between the **previous earnings 8-K** and the **current earnings 8-K**.

The artifact must let an LLM answer questions like:

- what happened between earnings?
- which events clearly moved the stock?
- which events had muted same-day reaction but large next-session/daily impact?
- which dates were unexplained gap days?
- which event should be fetched in full next?

This Step 5 artifact is a **timeline + reaction context**, not a full-content fetch. It should expose enough metadata and exact return windows for the LLM to decide what to request next by stable ID.

---

## Final Locked Decisions

1. There is **one unified timeline**, not separate `significant_moves`, `inter_quarter_news`, and `inter_quarter_8k` prompt sections.
2. The artifact has **one source of truth**:
   - canonical JSON on disk
   - rendered text generated from that same JSON
3. Timestamped events (`News`, `Report`) use an **exact timestamp-exclusive window**:
   - `prev_8k_ts < event_ts < context_cutoff_ts`
   - `context_cutoff_ts` is orchestrator-computed (see "Context Cutoff" section below):
     - **live** = `decision_cutoff_ts` (every news item available before prediction starts)
     - **historical** = release-session floor (excludes the entire current earnings release cluster)
4. Date-only events (`Dividend`, `Split`) use a **conservative date-exclusive window**:
   - `prev_day < event_day < cutoff_day`
   - `cutoff_day = context_cutoff_ts[:10]`
   - because exact intraday PIT is unknown for these event types
5. Every event carries a stable **`event_ref`** so the LLM can ask for full details later.
6. `News` and `Report` events include **event-specific forward returns** with exact start/end timestamps for:
   - hourly
   - session
   - daily
7. `Dividend` and `Split` events do **not** get synthetic intraday forward returns by default.
8. Boundary-day handling is explicit:
   - previous earnings day is a **special boundary day**
   - current earnings day is a **special boundary day**
   - ordinary day-level significance logic must not blindly apply there
9. `News.tags` and `returns_schedule` are also JSON strings and must be parsed like `channels`, `authors`, `items`, and `exhibits`.
10. Do **not** use `toString(created) > 'YYYY-MM-DD'` style timestamp filtering for `News` or `Report`. It is not exact and caused the Dec 3 boundary bug.

---

## Function Signature

```python
build_inter_quarter_context(
    ticker: str,
    prev_8k_ts: str,
    context_cutoff_ts: str,
    out_path: str | None = None,
    context_cutoff_reason: str | None = None,
) -> tuple[str, str]
```

### Inputs

- `ticker`
  - company ticker, e.g. `CRM`
- `prev_8k_ts`
  - exact ISO8601 timestamp of the previous earnings 8-K filing
  - example: `2024-12-03T16:03:38-05:00`
- `context_cutoff_ts`
  - upper bound for timestamped event inclusion (exclusive)
  - orchestrator-computed — this function is mode-unaware
  - **live**: `decision_cutoff_ts` (recorded at prediction-start)
  - **historical**: release-session floor (e.g., `2025-02-26T16:00:00-05:00` for post_market 8-K)
  - example (historical): `2025-02-26T16:00:00-05:00`
  - example (live): `2025-02-26T16:10:00-05:00`
- `context_cutoff_reason`
  - optional metadata label explaining why this cutoff value was chosen
  - passed through to the JSON artifact as-is — the function does not interpret it
  - `"historical_release_session_floor"` or `"live_decision_cutoff"` or `null` for CLI/debug
- `out_path`
  - explicit quarter-owned destination
  - default debug path:
    - `/tmp/earnings_inter_quarter_{ticker}.json`

### Outputs

- canonical JSON file: `inter_quarter_context.v1`
- rendered text string for planner/predictor prompt consumption
- return value:
  - `(out_path, rendered_text)`

The builder must both:

- write the canonical JSON artifact to disk
- return the final output path and the rendered text view

This keeps the warmup script usable both as:

- a file-producing CLI tool
- a direct helper for callers that need the rendered prompt section immediately

---

## Canonical JSON vs Rendered Text

These are the **same data in two forms**:

- **canonical JSON**
  - full structured artifact
  - machine-readable
  - exact timestamps
  - exact return windows
  - stable IDs
  - source of truth

- **rendered text**
  - compact readable timeline derived from the JSON
  - what gets shown to the LLM in the prompt

There must not be two different truths. The text view is just a readable projection of the JSON.

---

## Included Event Families

### Included

- `Date-[HAS_PRICE]->Company`
- `News-[INFLUENCES]->Company`
- `Report-[PRIMARY_FILER]->Company`
- `Company-[:DECLARED_DIVIDEND]->Dividend`
- `Company-[:DECLARED_SPLIT]->Split`

### Explicitly Excluded From This Step

- transcripts

Reason:
- transcripts can be added later using the same pattern
- they are not required for the first implementation of Step 5
- this spec must stay scoped and unambiguous

If transcripts are added in the future, they should use the same timestamped-event model as `News` and `Report` with event-specific forward returns and stable `event_ref`.

---

## Context Cutoff — Dual-Mode Design

This function is **mode-unaware**. The orchestrator computes `context_cutoff_ts` and passes it. Step 5 uses it as the upper bound without knowing whether it's a live or historical run.

### Orchestrator responsibility

| Mode | `context_cutoff_ts` value | Why |
|---|---|---|
| **Live** | `decision_cutoff_ts` (recorded at prediction-start) | Include every news item that existed before prediction started |
| **Historical** | Release-session floor (derived from current 8-K timestamp + market_session) | Exclude the entire current earnings release cluster, stay PIT-clean |

### Historical release-session floor rules

The orchestrator computes the floor using the current 8-K's `market_session`:

| Current 8-K session | Floor | Example |
|---|---|---|
| `post_market` | Same day 16:00 | 8-K at 16:03 → cutoff at 16:00 |
| `market_closed` (after 4 PM) | Same day 16:00 | 8-K at 21:04 → cutoff at 16:00 |
| `pre_market` | Same day 04:00 | 8-K at 07:02 → cutoff at 04:00 |
| `in_market` | Same day 09:30 | 8-K at 14:00 → cutoff at 09:30 |
| `market_closed` (before 4 PM or non-trading day) | Same day 00:00 | Weekend filing → cutoff at 00:00 |

This avoids any "is this headline earnings-related?" classification — it structurally excludes the entire release session.

### Orchestrator helper (lives in orchestrator, NOT in Step 5)

```python
def _release_session_floor(current_8k_ts, msc):
    """Compute conservative PIT-safe upper bound for inter-quarter context (historical mode)."""
    session = msc.get_market_session(current_8k_ts)
    day = current_8k_ts[:10]
    tz = current_8k_ts[19:]  # preserve timezone suffix e.g. '-05:00'
    if session == 'post_market':
        return f"{day}T16:00:00{tz}"
    if session == 'market_closed' and int(current_8k_ts[11:13]) >= 16:
        return f"{day}T16:00:00{tz}"
    if session == 'pre_market':
        return f"{day}T04:00:00{tz}"
    if session == 'in_market':
        return f"{day}T09:30:00{tz}"
    return f"{day}T00:00:00{tz}"  # non-trading day / early market_closed
```

---

## Exact Time / PIT Semantics

### 1. Timestamped events

For `News` and `Report`, inclusion rule is:

```text
prev_8k_ts < created_ts < context_cutoff_ts
```

Use exact timestamp comparison.

Use:

```cypher
WHERE datetime(node.created) > datetime($prev_8k_ts)
  AND datetime(node.created) < datetime($context_cutoff_ts)
```

Do **not** use:

```cypher
WHERE toString(node.created) > $start_day
```

because that incorrectly includes everything after midnight on the boundary day and is also weaker across DST offsets.

### 2. Date-only events

For `Dividend` and `Split`, exact intraday PIT is unavailable.

Use conservative date-only inclusion:

```text
prev_day < event_day < cutoff_day
```

Where `cutoff_day = context_cutoff_ts[:10]`.

Specifically:

- dividends use `declaration_date` as the event day
- splits use `execution_date` as the event day

Boundary-day date-only actions are excluded because exact ordering relative to the timestamp cutoff is unknowable.

### 3. Price rows

Daily price rows are used to build the day grid and provide day-level context.

Fetch price rows for:

```text
prev_day <= d.date <= cutoff_day
```

This is intentionally **inclusive** so the previous and current (cutoff) boundary days can be rendered correctly when needed.

---

## Boundary-Day Rules

This is the most important implementation nuance.

### Previous boundary day

The day `date(prev_8k_ts)` is always a **special boundary day**.

Rules:

- include only timestamped events with `created_ts > prev_8k_ts`
- exclude the previous earnings 8-K itself because the window is exclusive
- keep the trading-day price row in JSON if it exists, but mark it as:
  - `price_role = "reference_only"`
- do **not** treat its daily return as an ordinary inter-quarter move
- do **not** apply `***` or `GAP` markers to it

Reason:
- that day’s close-to-close row either predates the window or straddles the boundary
- it is useful as reference, but not an ordinary inter-quarter reaction day

### Cutoff boundary day

The day `date(context_cutoff_ts)` is also a special boundary day. Price handling depends on whether the cutoff is at or after market close.

#### If cutoff time >= 16:00 (e.g., historical post_market floor = 16:00, or live cutoff after close)

The close-to-close row ended at 16:00, which is at or before the cutoff. The price is fully within-window.

Set:

- `price_role = "ordinary"`

Still:

- include only timestamped events with `created_ts < context_cutoff_ts`
- allow ordinary `***` / `GAP` logic on this day because the close-to-close move is fully within-window

#### If cutoff time < 16:00 (e.g., historical pre_market floor = 04:00, or in_market floor = 09:30)

The close-to-close row extends past the cutoff — contaminated by post-cutoff trading.

Set:

- `price_role = "reference_only"`

And:

- do not apply `***` or `GAP`

### Non-trading boundary days

If a boundary date is not a trading day:

- create the day block if it contains included timestamped events
- `price = null`
- render as a special non-trading boundary day

---

## Exact Return Methodology

This section explains how the return windows are defined for event-level forward returns.

### Source of truth

The event-return pipeline already computes and stores:

- `event.created`
- `event.market_session`
- `event.returns_schedule`
- relationship return values on `INFLUENCES` / `PRIMARY_FILER`

Relevant code:

- [`EventReturnsManager.py:137`](/home/faisal/EventMarketDB/eventReturns/EventReturnsManager.py#L137)
- [`market_session.py:210`](/home/faisal/EventMarketDB/utils/market_session.py#L210)
- [`polygonClass.py:559`](/home/faisal/EventMarketDB/eventReturns/polygonClass.py#L559)

### What is stored vs reconstructed

`returns_schedule` stores the **end times** for:

- `hourly`
- `session`
- `daily`

The **start times** are not stored and must be reconstructed using `MarketSessionClassifier` from the original event timestamp.

### Exact per-horizon rules

#### Hourly

- `start_ts = market_session.get_interval_start_time(created)`
- `end_ts = returns_schedule["hourly"]`
- fallback if `returns_schedule.hourly` missing:
  - `market_session.get_interval_end_time(created, 60, respect_session_boundary=False)`

#### Session

- `start_ts = market_session.get_start_time(created)`
- `end_ts = returns_schedule["session"]`
- fallback if `returns_schedule.session` missing:
  - `market_session.get_end_time(created)`

#### Daily

- `start_ts = market_session.get_1d_impact_times(created)[0]`
- `end_ts = returns_schedule["daily"]`
- fallback if `returns_schedule.daily` missing:
  - `market_session.get_1d_impact_times(created)[1]`

### Session behavior summary

Use this exact legend in rendered text:

```text
Legend:
pre_market  = session -> 09:35, daily = prior close -> same-day close
in_market   = session -> same-day close, daily = prior close -> same-day close
post_market = session -> next-day 09:35, daily = same-day close -> next-day close
market_closed = exact windows shown explicitly when they differ
```

### Return families

For `News` and `Report`, each horizon must carry:

- `stock`
- `sector`
- `industry`
- `macro`
- `adj_macro = stock - macro`
- `adj_sector = stock - sector`
- `adj_industry = stock - industry`

If any component is missing, the derived adjusted return is `null`.

### No synthetic intraday returns for date-only actions

For `Dividend` and `Split`:

- do not fabricate hourly/session windows
- do not fabricate event-specific forward returns
- keep them as date-only corporate actions
- the enclosing day’s price tape already provides day-level context

---

## Stable Event References

Every event must have a stable `event_ref`.

### Rules

- news:
  - `event_ref = f"news:{news_id}"`
- report:
  - `event_ref = f"report:{accession}"`
- dividend:
  - `event_ref = f"dividend:{dividend_id}"`
- split:
  - `event_ref = f"split:{split_id}"`

These refs are what the LLM should cite when it wants full follow-up fetches.

Examples:

- `news:bzNews_42301752`
- `report:0001108524-24-000033`
- `dividend:FMC_2025-04-30_Regular`
- `split:ETR_2024-12-13_1.0_2.0`

---

## Relevant Fields To Include

### News

#### Render + JSON

- `event_ref`
- `type = "news"`
- `available_precision = "timestamp"`
- `created`
- `market_session`
- `title`
- `channels`
- `forward_returns`

#### JSON-only

- `id`
- `url`
- `authors`
- `tags`
- `updated`
- `returns_schedule_raw`

### Reports

#### Render + JSON

- `event_ref`
- `type = "filing"`
- `available_precision = "timestamp"`
- `created`
- `market_session`
- `form_type`
- `accession`
- `period_of_report`
  - nullable
  - omit the rendered `period:` fragment when null
- `is_amendment`
- `description`
- `items`
- `exhibit_keys`
- `forward_returns`

#### JSON-only

- `report_id`
- `filing_links`
- `section_names`
- `has_filing_text`
- `xbrl_status`
- `financial_statement_count`
- `returns_schedule_raw`

### Dividends

#### Render + JSON

- `event_ref`
- `type = "dividend"`
- `available_precision = "date"`
- `event_day = declaration_date`
- `declaration_date`
- `ex_dividend_date`
- `cash_amount`
- `currency`
- `frequency`
- `dividend_type`

#### JSON-only

- `id`
- `pay_date`
- `record_date`
- `forward_returns = null`

### Splits

#### Render + JSON

- `event_ref`
- `type = "split"`
- `available_precision = "date"`
- `event_day = execution_date`
- `execution_date`
- `split_from`
- `split_to`
- `ratio_text`
  - render as raw ratio text: `"{split_from}:{split_to}"`
  - preserve original string formatting, including commas when present

#### JSON-only

- `id`
- `forward_returns = null`

---

## Explicitly Excluded Fields

To avoid accidental bloat, do **not** include these in the timeline render:

- `News.body`
- `News.teaser`
- `Report.entities`
- `Report.symbols`
- `Report.extracted_sections`
- `Report.exhibit_contents`
- `Report.is_xml`
- `Report.xbrl_error`

These can be fetched later by `event_ref` if needed.

---

## Neo4j Data Types And Parsing Rules

### JSON string fields

The following Neo4j properties are stored as raw JSON strings and must be parsed with `json.loads()`:

- `News.channels`
- `News.authors`
- `News.tags`
- `News.returns_schedule`
- `Report.items`
- `Report.exhibits`
- `Report.returns_schedule`

Use one helper for all of them.

Use these exact fallbacks:

- `News.channels` -> `[]`
- `News.authors` -> `[]`
- `News.tags` -> `[]`
- `News.returns_schedule` -> `{}`
- `Report.items` -> `[]`
- `Report.exhibits` -> `{}`
- `Report.returns_schedule` -> `{}`

```python
def _parse_json_field(raw, fallback=None):
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback
```

### Return normalization helper

Neo4j return fields can contain:

- normal floats
- integer-valued floats
- `NaN`
- string `'NaN'`
- occasional list-valued hourly results in some historical shapes

Normalize them before storing/rendering.

```python
import math

def _norm_ret(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return round(f, 2)
```

### Volume / transactions formatting

Use current verified rules:

```python
def _fmt_vol(v):
    if v is None:
        return '?'
    if v == int(v):
        return f'{int(v):,}'
    return f'{v:,.2f}'

def _fmt_txn(v):
    if v is None:
        return '?'
    return f'{int(v):,}'
```

---

## Query Constants

All returned fields must use explicit `AS` aliases.

### 1. Trading-day price rows

Inclusive of boundary dates.

```python
QUERY_IQ_PRICES = """
MATCH (d:Date)-[hp:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= $prev_day AND d.date <= $cutoff_day
OPTIONAL MATCH (d)-[spy:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)-[:BELONGS_TO]->(sec:Sector)
OPTIONAL MATCH (d)-[sec_hp:HAS_PRICE]->(sec)
OPTIONAL MATCH (d)-[ind_hp:HAS_PRICE]->(ind)
RETURN d.date AS date,
       hp.open AS open,
       hp.high AS high,
       hp.low AS low,
       hp.close AS close,
       hp.daily_return AS daily_return,
       hp.volume AS volume,
       hp.vwap AS vwap,
       hp.transactions AS transactions,
       hp.timestamp AS price_timestamp,
       spy.daily_return AS spy_return,
       sec_hp.daily_return AS sector_return,
       sec.name AS sector_name,
       ind_hp.daily_return AS industry_return,
       ind.name AS industry_name
ORDER BY d.date
"""
```

### 2. Timestamped news events

Exact timestamp-exclusive window.

```python
QUERY_IQ_NEWS = """
MATCH (n:News)-[rel:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(n.created) > datetime($prev_8k_ts)
  AND datetime(n.created) < datetime($context_cutoff_ts)
RETURN n.created AS created,
       n.market_session AS market_session,
       n.id AS news_id,
       n.title AS title,
       n.channels AS channels,
       n.authors AS authors,
       n.tags AS tags,
       n.url AS url,
       n.updated AS updated,
       n.returns_schedule AS returns_schedule,
       rel.hourly_stock AS hourly_stock,
       rel.session_stock AS session_stock,
       rel.daily_stock AS daily_stock,
       rel.hourly_sector AS hourly_sector,
       rel.session_sector AS session_sector,
       rel.daily_sector AS daily_sector,
       rel.hourly_industry AS hourly_industry,
       rel.session_industry AS session_industry,
       rel.daily_industry AS daily_industry,
       rel.hourly_macro AS hourly_macro,
       rel.session_macro AS session_macro,
       rel.daily_macro AS daily_macro
ORDER BY datetime(n.created)
"""
```

### 3. Timestamped filings

Exact timestamp-exclusive window.

```python
QUERY_IQ_FILINGS = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE datetime(r.created) > datetime($prev_8k_ts)
  AND datetime(r.created) < datetime($context_cutoff_ts)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(sec:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
RETURN r.created AS created,
       r.market_session AS market_session,
       r.formType AS form_type,
       r.accessionNo AS accession,
       r.id AS report_id,
       r.description AS description,
       r.items AS items,
       r.exhibits AS exhibits,
       r.periodOfReport AS period_of_report,
       r.isAmendment AS is_amendment,
       r.xbrl_status AS xbrl_status,
       r.primaryDocumentUrl AS primary_doc_url,
       r.linkToTxt AS link_to_txt,
       r.linkToHtml AS link_to_html,
       r.linkToFilingDetails AS link_to_filing_details,
       r.returns_schedule AS returns_schedule,
       collect(DISTINCT sec.section_name) AS section_names,
       count(DISTINCT ft) > 0 AS has_filing_text,
       count(DISTINCT fs) AS financial_statement_count,
       pf.hourly_stock AS hourly_stock,
       pf.session_stock AS session_stock,
       pf.daily_stock AS daily_stock,
       pf.hourly_sector AS hourly_sector,
       pf.session_sector AS session_sector,
       pf.daily_sector AS daily_sector,
       pf.hourly_industry AS hourly_industry,
       pf.session_industry AS session_industry,
       pf.daily_industry AS daily_industry,
       pf.hourly_macro AS hourly_macro,
       pf.session_macro AS session_macro,
       pf.daily_macro AS daily_macro
ORDER BY datetime(r.created)
"""
```

### 4. Date-only dividends

Conservative date-exclusive window.

```python
QUERY_IQ_DIVIDENDS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_DIVIDEND]->(div:Dividend)
WHERE div.declaration_date > $prev_day
  AND div.declaration_date < $cutoff_day
RETURN div.id AS dividend_id,
       div.declaration_date AS declaration_date,
       div.ex_dividend_date AS ex_dividend_date,
       div.cash_amount AS cash_amount,
       div.currency AS currency,
       div.frequency AS frequency,
       div.dividend_type AS dividend_type,
       div.pay_date AS pay_date,
       div.record_date AS record_date
ORDER BY div.declaration_date
"""
```

### 5. Date-only splits

Conservative date-exclusive window.

```python
QUERY_IQ_SPLITS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_SPLIT]->(sp:Split)
WHERE sp.execution_date > $prev_day
  AND sp.execution_date < $cutoff_day
RETURN sp.id AS split_id,
       sp.execution_date AS execution_date,
       sp.split_from AS split_from,
       sp.split_to AS split_to
ORDER BY sp.execution_date
"""
```

### 6. Company context fallback

Use only if top-level `industry` and/or `sector` are still null after scanning price rows.

```python
QUERY_IQ_COMPANY_CONTEXT = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)
OPTIONAL MATCH (ind)-[:BELONGS_TO]->(sec:Sector)
RETURN ind.name AS industry_name,
       sec.name AS sector_name
"""
```

---

## Helper Functions To Implement

### ` _parse_json_field`

Already specified above.

### `_norm_ret`

Already specified above.

### `_safe_adj`

```python
def _safe_adj(a, b):
    if a is None or b is None:
        return None
    return round(a - b, 2)
```

### `_event_ref`

```python
def _event_ref(event_type, native_id):
    return f'{event_type}:{native_id}'
```

### `_day_from_ts`

```python
def _day_from_ts(ts):
    return str(ts)[:10] if ts else None
```

### `_build_forward_returns`

This function is only for `news` and `filing`.

**Return-window validation (PIT safety)**: Any return horizon whose measurement window extends past `context_cutoff_ts` is nulled. This prevents a previous-day post_market news item's daily/session returns from leaking the current earnings reaction — verified across all 11,541 events in the graph with zero leaks. Without this check, 939 return values leak across pre_market and in_market 8-K cases (e.g., CVNA prev-day news with `daily_stock: +40.10%` capturing the next-day earnings reaction).

```python
def _build_forward_returns(created, market_session, returns_schedule_raw, metrics,
                           session_helper, context_cutoff_ts):
    """Build forward returns for a news or filing event.

    Returns are nulled for any horizon whose window end extends past context_cutoff_ts.
    This is the PIT safety gate — it prevents return values from capturing the
    current earnings reaction even when the event itself is legitimately pre-cutoff.
    """
    schedule = _parse_json_field(returns_schedule_raw, {}) or {}

    hourly_start = session_helper.get_interval_start_time(created)
    hourly_end = schedule.get('hourly') or session_helper.get_interval_end_time(
        created, 60, respect_session_boundary=False
    ).isoformat()

    session_start = session_helper.get_start_time(created)
    session_end = schedule.get('session') or session_helper.get_end_time(created).isoformat()

    daily_start, daily_end_fallback = session_helper.get_1d_impact_times(created)
    daily_end = schedule.get('daily') or daily_end_fallback.isoformat()

    def pack(prefix, start_ts, end_ts):
        stock = _norm_ret(metrics.get(f'{prefix}_stock'))
        sector = _norm_ret(metrics.get(f'{prefix}_sector'))
        industry = _norm_ret(metrics.get(f'{prefix}_industry'))
        macro = _norm_ret(metrics.get(f'{prefix}_macro'))
        return {
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'stock': stock,
            'sector': sector,
            'industry': industry,
            'macro': macro,
            'adj_macro': _safe_adj(stock, macro),
            'adj_sector': _safe_adj(stock, sector),
            'adj_industry': _safe_adj(stock, industry),
        }

    result = {}
    for horizon, prefix, start_ts, end_ts in [
        ('hourly', 'hourly', hourly_start.isoformat(), hourly_end),
        ('session', 'session', session_start.isoformat(), session_end),
        ('daily', 'daily', daily_start.isoformat(), daily_end),
    ]:
        # PIT safety: null the entire horizon if its window extends past the cutoff
        if str(end_ts) > context_cutoff_ts:
            result[horizon] = None
        else:
            result[horizon] = pack(prefix, start_ts, end_ts)

    return result
```

### `_cutoff_boundary_price_role`

```python
def _cutoff_boundary_price_role(context_cutoff_ts):
    """Determine if the cutoff boundary day's close-to-close price is within-window.

    Rule: ordinary if cutoff time >= 16:00 (market close), reference_only otherwise.
    No MarketSessionClassifier needed — pure timestamp check.
    """
    hour = int(context_cutoff_ts[11:13])
    return 'ordinary' if hour >= 16 else 'reference_only'
```

### `_best_safe_horizon`

For news event rendering: pick the best available horizon in priority order.

```python
def _best_safe_horizon(forward_returns):
    """Return the best safe horizon dict for compact news rendering.

    Priority: daily (most informative) → session → hourly.
    Returns (horizon_name, horizon_dict) or (None, None) if all null.
    """
    for name in ('daily', 'session', 'hourly'):
        h = forward_returns.get(name)
        if h is not None and h.get('stock') is not None:
            return name, h
    return None, None
```

### `_report_summary`

Render label for report event. **Always prepend `[{form_type}]`**, then append the best available text:

1. `[{form_type}] {items[0]}` — if items is non-empty
2. `[{form_type}] {description}` — else if description is non-null
3. `[{form_type}] {accession}` — else fallback to accession

Examples:
- `[8-K] Item 5.02: Departure of Directors; Appointment of Officers`
- `[10-Q] Quarterly report`
- `[8-K] 0001108524-24-000036` (no items, no description)

---

## Canonical JSON Schema

```json
{
  "schema_version": "inter_quarter_context.v1",
  "ticker": "CRM",
  "prev_8k_ts": "2024-12-03T16:03:38-05:00",
  "context_cutoff_ts": "2025-02-26T16:00:00-05:00",
  "context_cutoff_reason": "historical_release_session_floor",
  "prev_day": "2024-12-03",
  "cutoff_day": "2025-02-26",
  "industry": "SoftwareApplication",
  "sector": "Technology",
  "days": [
    {
      "date": "2024-12-03",
      "is_trading_day": true,
      "boundary_role": "prev_boundary",
      "price_role": "reference_only",
      "price": {
        "open": 327.4,
        "high": 332.7999,
        "low": 323.65,
        "close": 331.43,
        "daily_return": 0.13,
        "volume": 7441873.0,
        "vwap": 329.01,
        "transactions": 173551.0,
        "timestamp": "2024-12-03 16:00:00-0500"
      },
      "spy_return": 0.05,
      "sector_return": 0.36,
      "industry_return": null,
      "adj_return": 0.08,
      "is_significant": null,
      "is_gap_day": null,
      "events": [
        {
          "event_ref": "news:bzNews_42301752",
          "type": "news",
          "available_precision": "timestamp",
          "created": "2024-12-03T16:04:37-05:00",
          "market_session": "post_market",
          "title": "Salesforce Sees Q4 Revenue $9.90B-$10.10B vs $10.05B Est...",
          "channels": ["News", "Guidance"],
          "id": "bzNews_42301752",
          "url": "https://www.benzinga.com/...",
          "authors": ["Benzinga Newsdesk"],
          "tags": ["BZI-AAR"],
          "updated": "2024-12-03T16:04:39-05:00",
          "forward_returns": {
            "hourly": {
              "start_ts": "2024-12-03T16:04:37-05:00",
              "end_ts": "2024-12-03T17:04:37-05:00",
              "stock": 3.12,
              "sector": 0.21,
              "industry": 0.18,
              "macro": 0.05,
              "adj_macro": 3.07,
              "adj_sector": 2.91,
              "adj_industry": 2.94
            },
            "session": {
              "start_ts": "2024-12-03T16:04:37-05:00",
              "end_ts": "2024-12-04T09:35:00-05:00",
              "stock": 6.18,
              "sector": 0.44,
              "industry": 0.31,
              "macro": 0.30,
              "adj_macro": 5.88,
              "adj_sector": 5.74,
              "adj_industry": 5.87
            },
            "daily": {
              "start_ts": "2024-12-03T16:00:00-05:00",
              "end_ts": "2024-12-04T16:00:00-05:00",
              "stock": 10.93,
              "sector": 1.83,
              "industry": null,
              "macro": 0.62,
              "adj_macro": 10.31,
              "adj_sector": 9.10,
              "adj_industry": null
            }
          }
        },
        {
          "event_ref": "report:0001108524-24-000034",
          "type": "filing",
          "available_precision": "timestamp",
          "created": "2024-12-03T21:04:12-05:00",
          "market_session": "market_closed",
          "form_type": "10-Q",
          "accession": "0001108524-24-000034",
          "period_of_report": "2024-10-31",
          "is_amendment": false,
          "description": "Quarterly report",
          "items": [],
          "exhibit_keys": [],
          "forward_returns": {
            "hourly": {
              "start_ts": "2024-12-04T04:00:00-05:00",
              "end_ts": "2024-12-04T05:00:00-05:00",
              "stock": 2.09,
              "sector": 0.11,
              "industry": 0.09,
              "macro": 0.06,
              "adj_macro": 2.03,
              "adj_sector": 1.98,
              "adj_industry": 2.00
            },
            "session": {
              "start_ts": "2024-12-03T20:00:00-05:00",
              "end_ts": "2024-12-04T09:35:00-05:00",
              "stock": -0.63,
              "sector": 0.14,
              "industry": 0.10,
              "macro": 0.27,
              "adj_macro": -0.90,
              "adj_sector": -0.77,
              "adj_industry": -0.73
            },
            "daily": {
              "start_ts": "2024-12-03T16:00:00-05:00",
              "end_ts": "2024-12-04T16:00:00-05:00",
              "stock": 10.93,
              "sector": 1.83,
              "industry": null,
              "macro": 0.62,
              "adj_macro": 10.31,
              "adj_sector": 9.10,
              "adj_industry": null
            }
          },
          "report_id": "0001108524-24-000034",
          "filing_links": {
            "primary_doc_url": "https://www.sec.gov/...",
            "link_to_txt": "https://www.sec.gov/...",
            "link_to_html": "https://www.sec.gov/...",
            "link_to_filing_details": "https://www.sec.gov/..."
          },
          "section_names": [],
          "has_filing_text": true,
          "xbrl_status": "COMPLETED",
          "financial_statement_count": 4
        }
      ]
    }
  ],
  "summary": {
    "total_day_blocks": 57,
    "trading_days_ordinary": 55,
    "boundary_days_rendered": 2,
    "non_trading_event_days": 0,
    "significant_move_days": 7,
    "gap_days": 3,
    "total_news": 73,
    "total_filings": 3,
    "total_dividends": 1,
    "total_splits": 0
  },
  "assembled_at": "2026-03-23T12:00:00Z"
}
```

### Important schema rules

- every day object must include the same top-level keys
- every event object must include:
  - `event_ref`
  - `type`
  - `available_precision`
- `forward_returns = null` for `dividend` and `split`
- `is_significant` and `is_gap_day` are:
  - `true` / `false` for ordinary trading days
  - `true` / `false` for cutoff-boundary trading days where `price_role = "ordinary"`
  - `null` for previous-boundary days, cutoff-boundary days where `price_role = "reference_only"`, and non-trading days

---

## Rendered Text Specification

### Header

Use:

```text
=== INTER-QUARTER TIMELINE: {ticker} ===
Industry: {industry} | Sector: {sector}
{trading_days_ordinary} ordinary trading days | {boundary_days_rendered} boundary days | {total_news} news | {total_filings} filings | {total_dividends} dividends | {total_splits} splits
{significant_move_days} significant move days | {gap_days} gap days

Legend:
pre_market  = session -> 09:35, daily = prior close -> same-day close
in_market   = session -> same-day close, daily = prior close -> same-day close
post_market = session -> next-day 09:35, daily = same-day close -> next-day close
market_closed = exact windows shown explicitly when they differ
```

### Ordinary trading day block

```text
2025-02-05 | CRM +1.10% vs SPY +0.41% | adj +0.69%
  open=345.72  high=348.04  low=338.87  close=347.93
  vol=4,521,009  vwap=344.95  txns=91,660
  Sector +1.39%
```

If `is_significant = true`, append `***`.

If `is_gap_day = true`, append `GAP`.

### Previous boundary day block

```text
2024-12-03 | boundary day after previous earnings
  previous 8-K filed at 16:03:38; only later timestamped events are included
  same-day close-to-close (+0.13% vs SPY +0.05%) is reference only
```

### Cutoff boundary day block

If `price_role = ordinary`:

```text
2025-02-26 | cutoff boundary (context cutoff at 16:00:00)
  only events before cutoff are included
  same-day close-to-close is fully pre-cutoff and therefore within-window
```

If this day also satisfies the ordinary day marker rules, append `***` and/or `GAP` exactly as for ordinary trading days.

If `price_role = reference_only`:

```text
2025-02-26 | cutoff boundary (context cutoff at 04:00:00)
  only events before cutoff are included
  same-day close-to-close extends past cutoff and is reference only
```

### Non-trading event day block

```text
2025-01-20 | non-trading event day
```

### Event render format

These rules are exact and are meant to remove implementation discretion.

- render events in this order within a day:
  - timestamped events sorted by exact `created`
  - then date-only `dividend`
  - then date-only `split`
- do not insert blank lines inside an event block
- a timestamped event always renders its header line even if all return lines are omitted
- a date-only event always renders:
  - one header line
  - one detail line
- default text render shows only `adj_macro`
  - `adj_sector` and `adj_industry` stay JSON-only
- if a field is null, omit that fragment rather than printing `null`, `[]`, or `{}` literally

#### News

News events render **one compact reaction line** using the best safe horizon (daily preferred, falling back to session, then hourly if earlier horizons are nulled by return-window validation). This keeps the planner timeline focused on significance rather than market microstructure. All 3 horizons remain in the canonical JSON for downstream consumers.

```text
16:04 post_market | news:bzNews_42301752 | Salesforce Sees Q4 Revenue... [News, Guidance]
  react: daily stock +10.93% | SPY +0.62% | adj_macro +10.31% (16:00->16:00)
```

If daily is nulled (return window extends past cutoff):

```text
03:25 market_closed | news:bzNews_42301752 | Euronet Worldwide Q3 EPS... [Earnings]
  react: hourly stock +1.20% | SPY +0.03% | adj_macro +1.17% (04:00->05:00)
```

Exact render rules:

- header format:
  - `{HH:MM} {market_session} | {event_ref} | {title}`
- append ` [{channel_1}, {channel_2}, ...]` only if `channels` is non-empty
- **one reaction line** using `_best_safe_horizon()`:
  - prefer `daily`, else `session`, else `hourly` (first non-null horizon with non-null `stock`)
  - prefix with `react:`
  - render fragments in this exact order:
    - horizon label (`daily`, `session`, or `hourly`)
    - `stock`
    - `sector` if non-null
    - `industry` if non-null
    - `SPY` if macro is non-null
    - `adj_macro` if non-null
    - window label `(start->end)`
  - omit any fragment whose value is null
- if all 3 horizons are null or have null `stock`, keep only the header line (no react line)

#### Filing

```text
21:04 market_closed | report:0001108524-24-000034 | [10-Q] Quarterly report
  accession: 0001108524-24-000034 | period: 2024-10-31
  sections: 0 | exhibits: none
  hourly  stock +2.09% | sector +0.11% | industry +0.09% | SPY +0.06% | adj_macro +2.03% (12/04 04:00->05:00)
  session stock -0.63% | sector +0.14% | industry +0.10% | SPY +0.27% | adj_macro -0.90% (12/03 20:00->12/04 09:35)
  daily   stock +10.93% | sector +1.83% | SPY +0.62% | adj_macro +10.31% (12/03 close->12/04 close)
```

Exact render rules:

- header format:
  - `{HH:MM} {market_session} | {event_ref} | {report_summary}`
- details line 1:
  - always include `accession: {accession}`
  - append ` | period: {period_of_report}` only when non-null
  - append ` | amendment` only when `is_amendment = true`
- details line 2:
  - always include `sections: {section_count}`
  - always include ` | exhibits: {comma-separated exhibit_keys}` when non-empty
  - otherwise render ` | exhibits: none`
- filing events render **all 3 horizons** (unlike news which renders one best-safe-horizon):
  - filings are rare (2-5 per quarter) and high-signal
  - the hourly/session/daily breakdown shows reaction speed (immediate vs overnight) which matters for filings
  - render in fixed order: `hourly`, `session`, `daily`
  - render a horizon line only if `forward_returns[horizon]` exists and `stock` is not null
  - if a horizon is nulled by return-window validation, render `{horizon} (nulled — window extends past cutoff)`
  - within each horizon line, render fragments in this exact order:
    - `stock`, `sector` if non-null, `industry` if non-null, `SPY` if non-null, `adj_macro` if non-null, window label `(start->end)`

#### Dividend

```text
date-only | dividend:CRM_2024-12-05_Regular | Dividend declared: $0.40 USD quarterly
  ex-date 2024-12-18 | pay-date 2025-01-08 | type Regular
```

#### Split

```text
date-only | split:ETR_2024-12-13_1.0_2.0 | Split effective: 1:2
```

### Render strategy by event type

- **News**: one `react:` line using `_best_safe_horizon()` (daily → session → hourly fallback). If all horizons null, header only.
- **Filing**: all 3 horizon lines (hourly, session, daily). If a horizon is nulled by return-window validation, show `(nulled — window extends past cutoff)`.
- **Dividend / Split**: no return lines.

### Render omissions

- omit horizon lines whose `stock` value is null
- omit `industry` fragments when unavailable
- omit channel brackets when `channels == []`
- omit `period:` when `period_of_report` is null
- omit `tags`, `authors`, `filing_links`, `section_names`, `returns_schedule_raw`, `adj_sector`, and `adj_industry` from default render
- keep all of those in JSON

---

## Exact Assembly Algorithm

```text
1. Parse inputs
   - prev_day = prev_8k_ts[:10]
   - cutoff_day = context_cutoff_ts[:10]

2. Initialize helpers
   - session_helper = MarketSessionClassifier()

3. Query:
   - prices using QUERY_IQ_PRICES with prev_day/cutoff_day inclusive
   - news using QUERY_IQ_NEWS with exact timestamp window
   - filings using QUERY_IQ_FILINGS with exact timestamp window
   - dividends using QUERY_IQ_DIVIDENDS with conservative date-exclusive window
   - splits using QUERY_IQ_SPLITS with conservative date-exclusive window
   - company context fallback using QUERY_IQ_COMPANY_CONTEXT only if needed

4. Build base day_map from price rows
   - key by date string
   - mark is_trading_day = true
   - fill price / spy / sector / industry / adj_return
   - `adj_return = daily_return - spy_return`
   - set top-level `sector` from the first non-null `sector_name` seen in price rows
   - set top-level `industry` from the first non-null `industry_name` seen in price rows
   - if either remains null after scanning price rows, run `QUERY_IQ_COMPANY_CONTEXT`
   - set boundary_role = null initially
   - set price_role = 'ordinary' initially

5. Ensure boundary day entries exist
   - prev_day and cutoff_day must exist in day_map if they have events, even if no price row

6. Mark boundary roles
   - day_map[prev_day].boundary_role = 'prev_boundary' if prev-day events or price row exist
   - day_map[cutoff_day].boundary_role = 'cutoff_boundary' if cutoff-day events or price row exist

7. Set price roles
   - prev boundary trading day -> price_role = 'reference_only'
   - cutoff boundary trading day:
     - ordinary if cutoff hour >= 16 (use _cutoff_boundary_price_role)
     - else reference_only

8. Merge news events
   - day_key = created[:10]
   - parse:
     - `channels = _parse_json_field(channels, [])`
     - `authors = _parse_json_field(authors, [])`
     - `tags = _parse_json_field(tags, [])`
     - `returns_schedule = _parse_json_field(returns_schedule, {})`
   - normalize all return metrics with _norm_ret
   - build event_ref = news:{news_id}
   - build forward_returns via _build_forward_returns(..., context_cutoff_ts)
     - horizons whose window extends past context_cutoff_ts are automatically nulled
   - append event to day_map[day_key].events

9. Merge filing events
   - day_key = created[:10]
   - parse:
     - `items = _parse_json_field(items, [])`
     - `exhibits = _parse_json_field(exhibits, {})`
     - `returns_schedule = _parse_json_field(returns_schedule, {})`
   - exhibit_keys = sorted(parsed_exhibits.keys())
   - section_names = sorted non-null unique section names
   - build event_ref = report:{accession}
   - build forward_returns via _build_forward_returns(..., context_cutoff_ts)
     - horizons whose window extends past context_cutoff_ts are automatically nulled
   - append event to day_map[day_key].events

10. Merge dividends
   - day_key = declaration_date
   - build event_ref = dividend:{dividend_id}
   - forward_returns = null
   - append event

11. Merge splits
   - day_key = execution_date
   - ratio_text = f'{split_from}:{split_to}'
   - build event_ref = split:{split_id}
   - forward_returns = null
   - append event

12. Create synthetic non-trading day entries as needed
   - if a date has events but no price row, create:
     - is_trading_day = false
     - price = null
     - spy/sector/industry/adj_return = null
     - boundary_role if applicable

13. Sort events within each day
   - timestamped events first, ordered by exact created timestamp
   - date-only corporate actions after timestamped events
   - tie-break type order: filing, news, dividend, split

14. Compute ordinary-day significance markers
   - for trading days where:
     - boundary_role is null and price_role == 'ordinary'
     - OR boundary_role == 'cutoff_boundary' and price_role == 'ordinary'
   - is_significant = abs(adj_return) >= 2.0
   - is_gap_day = is_significant and zero filing events and zero news events
   - dividends/splits do not clear GAP

15. Build summary counts
   - total_day_blocks = number of rendered day objects
   - trading_days_ordinary = trading days with boundary_role null
   - boundary_days_rendered = count of rendered days with boundary_role != null
   - non_trading_event_days = days with is_trading_day false
   - total_news / filings / dividends / splits
   - significant_move_days / gap_days from all days where the boolean is true

16. Write canonical JSON
   - atomic write with tmp file + os.replace

17. Render text from JSON
   - using exact rules above
```

---

## CLI Interface

Add to `warmup_cache.py`:

```bash
warmup_cache.py TICKER --inter-quarter --prev-8k ISO8601 --context-cutoff ISO8601 [--out-path PATH] [--cutoff-reason REASON]
```

For manual/debug use, `--context-cutoff` is the upper bound timestamp. The orchestrator computes it per mode; for manual CLI testing, pass the session floor (historical) or current time (live-like). `--cutoff-reason` is optional metadata (e.g., `historical_release_session_floor` or `live_decision_cutoff`); omit for debug runs.

### Parsing branch

Add before `--guidance-history`:

```python
if '--inter-quarter' in sys.argv:
    prev_8k = None
    context_cutoff = None
    out_path = None

    if '--prev-8k' not in sys.argv:
        print('Error: --inter-quarter requires --prev-8k', file=sys.stderr)
        sys.exit(1)
    if '--context-cutoff' not in sys.argv:
        print('Error: --inter-quarter requires --context-cutoff', file=sys.stderr)
        sys.exit(1)

    pidx = sys.argv.index('--prev-8k')
    if pidx + 1 >= len(sys.argv):
        print('Error: --prev-8k requires ISO8601 argument', file=sys.stderr)
        sys.exit(1)
    prev_8k = sys.argv[pidx + 1]

    cidx = sys.argv.index('--context-cutoff')
    if cidx + 1 >= len(sys.argv):
        print('Error: --context-cutoff requires ISO8601 argument', file=sys.stderr)
        sys.exit(1)
    context_cutoff = sys.argv[cidx + 1]

    if '--out-path' in sys.argv:
        oidx = sys.argv.index('--out-path')
        if oidx + 1 >= len(sys.argv):
            print('Error: --out-path requires PATH argument', file=sys.stderr)
            sys.exit(1)
        out_path = sys.argv[oidx + 1]

    cutoff_reason = None
    if '--cutoff-reason' in sys.argv:
        ridx = sys.argv.index('--cutoff-reason')
        if ridx + 1 >= len(sys.argv):
            print('Error: --cutoff-reason requires argument', file=sys.stderr)
            sys.exit(1)
        cutoff_reason = sys.argv[ridx + 1]

    build_inter_quarter_context(ticker, prev_8k, context_cutoff, out_path, cutoff_reason)
    sys.exit(0)
```

---

## Tests

### Required tests

1. **CRM exact window counts (historical mode)**
   - input:
     - prev = `2024-12-03T16:03:38-05:00`
     - context_cutoff = `2025-02-26T16:00:00-05:00` (post_market session floor)
   - verify:
     - `total_news = 73` (session floor at 16:00 excludes 1 additional Feb 26 event — the 16:01:48 earnings headline — vs old 74 with exact-8K-ts cutoff)
     - `total_filings = 3`
     - `total_dividends = 1`
   - note:
     - old `74 news / 4 filings` counts came from date-only and exact-8K-ts designs respectively

2. **CRM previous boundary day correctness**
   - verify Dec 3 includes:
     - 5 post-boundary news items
     - 1 later 10-Q at `21:04:12`
   - verify it excludes:
     - 4 earlier Dec 3 news items
     - the boundary 8-K itself at `16:03:38`

3. **CRM cutoff boundary day correctness (historical)**
   - context_cutoff = `2025-02-26T16:00:00-05:00`
   - verify Feb 26 includes 3 pre-cutoff news (08:44, 12:15, 14:21)
   - verify it excludes 16:01:48 earnings headline and everything after
   - verify `price_role = "ordinary"` (cutoff hour = 16 >= 16)

4. **Stored-window reconstruction**
   - verify news/report `forward_returns.*.end_ts` comes from parsed `returns_schedule`
   - verify start timestamps match `MarketSessionClassifier`

5. **Market-closed late filing case**
   - CRM 10-Q at `2024-12-03T21:04:12-05:00`
   - verify:
     - hourly `04:00 -> 05:00` next day
     - session `20:00 -> 09:35` next day
     - daily `12/03 close -> 12/04 close`

6. **JSON parsing**
   - `channels`, `authors`, `tags`, `items`, `exhibits`, `returns_schedule` all parse correctly

7. **Volume formatting**
   - ordinary CRM Dec 2024-Feb 2025 rows render integer volume
   - at least one 2026 row renders fractional volume with 2 decimals

8. **Dividend sample**
   - declaration-day merge works
   - event_ref uses native dividend ID

9. **Split sample**
   - `DECLARED_SPLIT` query works
   - ratio renders as `split_from:split_to`

10. **Gap day**
   - Jan 27 2025 for CRM still marked `*** GAP`
   - only if no news and no filings

11. **Empty ticker/window**
   - returns valid empty artifact

12. **Return-window validation: prev-day post_market → pre_market 8-K leak prevention**
   - Use a pre_market 8-K pair (e.g., CVNA 2023-07-19 or GME 2024-06-07)
   - Verify: prev-day post_market news IS included in the timeline (event timestamp is before session floor)
   - Verify: its `forward_returns.daily` is **null** (daily window end = next-day 16:00, which > session floor 04:00)
   - Verify: its `forward_returns.hourly` is **kept** (hourly window end = prev-day ~17:xx, which < session floor)
   - This is the critical PIT safety test — without window validation, CVNA shows `daily_stock: +40.10%` and GME shows `daily_stock: -39.42%`, both leaking the full earnings reaction
   - Verified: 939 return values across the graph would leak without this check, zero leak with it

13. **Live mode: return-window validation still applies**
   - With `context_cutoff_ts = decision_cutoff_ts` (e.g., 16:10 after 8-K)
   - Verify: events well before the cutoff have all forward_returns horizons kept
   - Verify: events near the cutoff (e.g., 16:05 news) may have session/daily horizons nulled because those windows extend past `decision_cutoff_ts` — this is correct behavior (those returns haven't been computed yet at prediction time)
   - Verify: the same `end_ts > context_cutoff_ts` rule applies uniformly in both modes
   - Verify: the persisted JSON artifact can be reused for exact replay without rebuilding from Neo4j

14. **News render fallback selection (`_best_safe_horizon`)**
   - Case A (daily safe): ordinary mid-window news → `react:` line shows `daily` with timing window
   - Case B (daily nulled, session safe): prev-day post_market news near a pre_market 8-K where daily is nulled by return-window validation but session is kept → `react:` line shows `session`
   - Case C (daily + session nulled, hourly safe): same scenario but session also extends past cutoff → `react:` line shows `hourly`
   - Case D (all nulled): all 3 horizons nulled → news event renders header only, no `react:` line
   - Verify: filing events are NOT affected — filings always render all 3 horizon lines regardless of this fallback logic

---

## Real CRM Sample

### Previous boundary day

```text
2024-12-03 | boundary day after previous earnings
  previous 8-K filed at 16:03:38; only later timestamped events are included
  same-day close-to-close (+0.13% vs SPY +0.05%) is reference only

  16:04 post_market | news:bzNews_42301752 | Salesforce Sees Q4 Revenue $9.90B-$10.10B...
    react: daily stock +10.93% | SPY +0.62% | adj_macro +10.31% (16:00->16:00)

  21:04 market_closed | report:0001108524-24-000034 | [10-Q] Quarterly report
    accession: 0001108524-24-000034 | period: 2024-10-31
    sections: 11 | exhibits: EX-10.3
    hourly  stock +2.09% | sector +0.11% | industry +0.09% | SPY +0.06% | adj_macro +2.03% (12/04 04:00->05:00)
    session stock -0.63% | sector +0.14% | industry +0.10% | SPY +0.27% | adj_macro -0.90% (12/03 20:00->12/04 09:35)
    daily   stock +10.93% | sector +1.83% | SPY +0.62% | adj_macro +10.31% (12/03 close->12/04 close)
```

### Ordinary day with filing + news

```text
2025-02-05 | CRM +1.10% vs SPY +0.41% | adj +0.69%
  open=345.72  high=348.04  low=338.87  close=347.93
  vol=4,521,009  vwap=344.95  txns=91,660
  Sector +1.39%

  17:05 post_market | report:0001193125-25-020881 | [8-K] Item 5.02: Departure of Directors; Appointment of Officers
    accession: 0001193125-25-020881 | period: 2025-02-05
    sections: 2 | exhibits: EX-10.1, EX-99.1
    hourly  stock -0.15% | sector +0.21% | industry +0.04% | SPY -0.04% | adj_macro -0.11% (17:05->18:05)
    session stock -2.18% | sector +0.31% | industry +0.02% | SPY +0.17% | adj_macro -2.35% (17:05->02/06 09:35)
    daily   stock -4.92% | sector +0.27% | industry +0.18% | SPY +0.32% | adj_macro -5.24% (02/05 close->02/06 close)

  17:09 post_market | news:bzNews_43514109 | Salesforce Says Robin Washington Will Become President...
    react: daily stock -4.92% | SPY +0.32% | adj_macro -5.24% (16:00->16:00)
```

### Gap day

```text
2025-01-27 | CRM +3.96% vs SPY -1.41% | adj +5.37%  ***  GAP
  open=332.00  high=353.00  low=330.00  close=347.00
  vol=15,661,109  vwap=...  txns=...
  Sector -4.90%

  (no news, no filings)
```

### Cutoff boundary day (historical, post_market floor = 16:00)

```text
2025-02-26 | cutoff boundary (context cutoff at 16:00:00)
  only events before cutoff are included
  same-day close-to-close is fully pre-cutoff and therefore within-window
  CRM +0.47% vs SPY +0.05% | adj +0.42%

  08:44 pre_market | news:bzNews_43972085 | How To Earn $500 A Month From Salesforce Stock... [Earnings, News, Trading Ideas]
    react: daily stock +0.44% | SPY +0.07% | adj_macro +0.37% (16:00->16:00)
  12:15 in_market | news:bzNews_43981295 | This Is What Whales Are Betting On Salesforce [Options, Markets]
    react: daily stock +0.44% | SPY +0.07% | adj_macro +0.37% (16:00->16:00)
  14:21 in_market | news:bzNews_43985887 | Salesforce Stock Drops Below Key Levels Ahead Of Q4... [Technicals, Previews, Tech]
    react: daily stock +0.44% | SPY +0.07% | adj_macro +0.37% (16:00->16:00)
```

Note: the `16:01:48` earnings headline ("Q4 EPS $2.78 Beats") is correctly excluded by the 16:00 cutoff.

---

## Final Notes For Implementer

- This spec intentionally supersedes the older Step 5 draft in `planner.md` where they conflict.
- This function is **mode-unaware**. The orchestrator computes `context_cutoff_ts` and passes it. Step 5 uses it as the upper bound without knowing whether it's a live or historical run.
- The biggest correctness rules are:
  - exact timestamp filtering for `News` and `Report` using `context_cutoff_ts`
  - **return-window validation**: null any forward_returns horizon where `end_ts > context_cutoff_ts` — this is the PIT safety gate that prevents prev-day post_market news from leaking earnings reactions via their daily/session return windows (verified: 939 values would leak without this, zero with it)
  - conservative date-exclusive filtering for `Dividend` and `Split` using `cutoff_day`
  - special boundary-day handling (prev_boundary + cutoff_boundary)
  - `event_ref` on every event
  - event-specific forward returns for `News` and `Report`
- Do not silently simplify the boundary-day rules. That is the main place the old design became misleading.
- INFLUENCES queries MUST use `[rel:INFLUENCES]`, never `[inf:INFLUENCES]` — property access on `inf` breaks because Neo4j resolves `inf` as the infinity literal.
- **Live replay**: To reproduce a live prediction exactly, reuse the persisted `inter_quarter_context.json` artifact — do NOT rebuild from Neo4j. Reason: News/Report nodes have `created`/`updated` but no ingestion timestamp. A later rebuild could include items that were not actually present in Neo4j when the live prediction ran.
