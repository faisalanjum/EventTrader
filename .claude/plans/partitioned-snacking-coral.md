# Alpha Vantage Earnings PIT Implementation — Last Agent (13/13)

## STATUS: COMPLETE (2026-02-16)

All implementation done. 52/52 pit_fetch tests, 13/13 agents linter, 41/41 pit_gate tests.

**Implementation divergences from original plan below:**

| Plan assumption | Actual implementation | Impact |
|---|---|---|
| `reportTime` field exists in EARNINGS API | Does NOT exist — live API confirmed no `reportTime` | Quarterly earnings use date-only PIT (exclude PIT day, same as Perplexity) |
| Annual earnings: gap in PIT (no reportedDate) | Cross-reference PIT: annual `available_at` derived from matching Q4 quarterly `reportedDate` (`available_at_source: "cross_reference"`) | Annual items are PIT-capable, not gapped |
| EARNINGS_ESTIMATES: gap entirely in PIT | Coarse PIT via revision buckets (7/30/60/90d before fiscal end). Selects nearest bucket ≤ PIT. Returns `pit_consensus_eps` + `pit_bucket` (`available_at_source: "coarse_pit"`) | Historical estimates are PIT-capable, not gapped. Forward-looking still gapped. |
| pit_gate.py unchanged | Added `cross_reference` + `coarse_pit` to VALID_SOURCES | Gate validates new source types |
| 10 AV tests (41 total) | 21 AV tests (52 total): 10 earnings + 11 coarse PIT estimates | More comprehensive coverage |

---

## Context (original plan — see divergences above)

12/13 data subagents are PIT-complete. `alphavantage-earnings` is the last remaining agent. It currently uses 3 MCP tools directly (`EARNINGS_ESTIMATES`, `EARNINGS`, `EARNINGS_CALENDAR`) with no PIT compliance, no envelope contract, and no hook validation. This plan converts it to the Bash-wrapper archetype (same as BZ + Perplexity), adds `--source alphavantage` to pit_fetch.py, and achieves full 13/13 PIT compliance.

**Why wrapper over MCP tools:** DataSubAgents.md §4.6 decided this — MCP tools don't accept `--pit`, so hooks can't validate. The wrapper pattern (pit_fetch.py calls AV REST API directly, filters by PIT, returns sanitized envelope) is the only reliable approach.

**API reality (verified via live MCP calls — corrected post-implementation):**

| AV Function | pit_fetch `--op` | Response format | PIT-critical fields | PIT strategy |
|---|---|---|---|---|
| `EARNINGS` | `earnings` | JSON | `quarterlyEarnings[].reportedDate` (date-only, no reportTime) | Quarterly: date-only exclude PIT day. Annual: cross-reference via Q4 quarterly reportedDate |
| `EARNINGS_ESTIMATES` | `estimates` | JSON | Revision buckets (`eps_estimate_average_7/30/60/90_days_ago`) | Coarse PIT: nearest bucket ≤ PIT. Forward-looking gapped. |
| `EARNINGS_CALENDAR` | `calendar` | CSV | None (forward-looking snapshot) | Gap entirely in PIT mode |

**Quarterly earnings `available_at` derivation:**

`reportedDate` (YYYY-MM-DD) — date-only, no time-of-day field available:
- Start-of-day NY timezone (conservative)
- PIT comparison: exclude PIT day entirely (same as Perplexity date-only treatment)

**Annual earnings:** Cross-referenced via matching Q4 quarterly `reportedDate` (`available_at_source: "cross_reference"`). Unmatched annual items gapped.

---

## 1. pit_fetch.py — Add alphavantage source

**File:** `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py`

### 1.1 New constants

```python
# --- Alpha Vantage constants ---
AV_BASE_URL = "https://www.alphavantage.co/query"

AV_OP_FUNCTION: dict[str, str] = {
    "earnings": "EARNINGS",
    "estimates": "EARNINGS_ESTIMATES",
    "calendar": "EARNINGS_CALENDAR",
}

# Conservative report-time → hour mapping for datetime derivation
AV_REPORT_TIME_HOUR: dict[str, int] = {
    "pre-market": 6,    # 6 AM ET (conservative early morning)
    "post-market": 16,  # 4 PM ET (market close)
}
```

### 1.2 Parser changes

Extend `--source` choices:
```python
choices=["bz-news-api", "benzinga", "benzinga-news", "perplexity", "alphavantage"]
```

Remove `choices` constraint from `--op` (validate per-source instead):
```python
p.add_argument("--op", help="Operation mode (validated per source)")
```

Add AV-specific args:
```python
p.add_argument("--symbol", help="Single ticker symbol (alphavantage)")
p.add_argument("--horizon", choices=["3month", "6month", "12month"],
               default="3month", help="Calendar horizon (alphavantage --op calendar)")
```

### 1.3 `_normalize_av_quarterly` normalizer

```python
def _normalize_av_quarterly(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    """Normalize a quarterlyEarnings item into PIT envelope format."""
    reported_date = raw.get("reportedDate")
    if not isinstance(reported_date, str) or not reported_date.strip():
        fiscal = raw.get("fiscalDateEnding", "unknown")
        return None, None, f"quarterly item {fiscal} missing reportedDate"

    # Derive full datetime from reportedDate + reportTime
    report_time = (raw.get("reportTime") or "").strip().lower()
    hour = AV_REPORT_TIME_HOUR.get(report_time)

    if hour is not None:
        # Full datetime derivable
        try:
            pub_dt = datetime.strptime(reported_date.strip(), "%Y-%m-%d").replace(
                hour=hour, minute=15 if report_time == "post-market" else 0,
                tzinfo=NY_TZ
            )
        except ValueError:
            return None, None, f"unparseable reportedDate: {reported_date}"
    else:
        # Date-only fallback (no reportTime) — start-of-day NY
        try:
            pub_dt = datetime.strptime(reported_date.strip(), "%Y-%m-%d").replace(tzinfo=NY_TZ)
        except ValueError:
            return None, None, f"unparseable reportedDate: {reported_date}"

    item = {
        "available_at": _to_new_york_iso(pub_dt),
        "available_at_source": "provider_metadata",
        "record_type": "quarterly_earnings",
        "fiscalDateEnding": raw.get("fiscalDateEnding"),
        "reportedDate": reported_date,
        "reportTime": raw.get("reportTime"),
        "reportedEPS": raw.get("reportedEPS"),
        "estimatedEPS": raw.get("estimatedEPS"),
        "surprise": raw.get("surprise"),
        "surprisePercentage": raw.get("surprisePercentage"),
    }
    return item, pub_dt, None
```

### 1.4 `_normalize_av_annual` normalizer

```python
def _normalize_av_annual(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize an annualEarnings item (open mode only, no available_at)."""
    return {
        "record_type": "annual_earnings",
        "fiscalDateEnding": raw.get("fiscalDateEnding"),
        "reportedEPS": raw.get("reportedEPS"),
        # No available_at — open mode pass-through only
    }
```

### 1.5 `_normalize_av_estimate` normalizer

```python
def _normalize_av_estimate(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize an EARNINGS_ESTIMATES item (open mode only)."""
    return {
        "available_at": _to_new_york_iso(datetime.now(timezone.utc)),
        "available_at_source": "provider_metadata",
        "record_type": "estimate",
        "fiscalDateEnding": raw.get("date"),
        "horizon": raw.get("horizon"),
        "eps_estimate_average": raw.get("eps_estimate_average"),
        "eps_estimate_high": raw.get("eps_estimate_high"),
        "eps_estimate_low": raw.get("eps_estimate_low"),
        "eps_estimate_analyst_count": raw.get("eps_estimate_analyst_count"),
        "revenue_estimate_average": raw.get("revenue_estimate_average"),
        "revenue_estimate_high": raw.get("revenue_estimate_high"),
        "revenue_estimate_low": raw.get("revenue_estimate_low"),
        "revenue_estimate_analyst_count": raw.get("revenue_estimate_analyst_count"),
    }
```

### 1.6 `_normalize_av_calendar_row` normalizer

```python
def _normalize_av_calendar_row(row: dict[str, str]) -> dict[str, Any]:
    """Normalize a parsed CSV row from EARNINGS_CALENDAR (open mode only)."""
    return {
        "available_at": _to_new_york_iso(datetime.now(timezone.utc)),
        "available_at_source": "provider_metadata",
        "record_type": "earnings_calendar",
        "symbol": row.get("symbol"),
        "name": row.get("name"),
        "reportDate": row.get("reportDate"),
        "fiscalDateEnding": row.get("fiscalDateEnding"),
        "estimate": row.get("estimate"),
        "currency": row.get("currency"),
        "timeOfTheDay": row.get("timeOfTheDay"),
    }
```

### 1.7 `_fetch_av` handler

```python
def _fetch_av(api_key: str, function: str, params: dict[str, str], timeout: int) -> str:
    """Call Alpha Vantage REST API and return raw response text."""
    query_params = {"function": function, "apikey": api_key}
    query_params.update(params)
    url = f"{AV_BASE_URL}?{urlencode(query_params)}"
    req = Request(url, headers={"User-Agent": "pit-fetch/1.0"}, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")
```

### 1.8 `_load_av_input` for offline testing

```python
def _load_av_input(path: str) -> str:
    """Load AV response from local file for offline testing."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
```

### 1.9 Source dispatch in `main()` — AV branch

```python
is_av = args.source == "alphavantage"

if is_av:
    av_ops = {"earnings", "estimates", "calendar"}
    if not args.op or args.op not in av_ops:
        envelope["gaps"].append({"type": "config", "reason": f"--op required, one of: {sorted(av_ops)}"})
    else:
        symbol = args.symbol or (args.tickers[0] if hasattr(args, 'tickers') and args.tickers else None)
        if not symbol:
            envelope["gaps"].append({"type": "config", "reason": "--symbol required for alphavantage"})
        else:
            function = AV_OP_FUNCTION[args.op]
            av_params: dict[str, str] = {"symbol": symbol}
            if args.op == "calendar" and args.horizon:
                av_params["horizon"] = args.horizon

            try:
                if args.input_file:
                    raw_text = _load_av_input(args.input_file)
                else:
                    _load_env()
                    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
                    if not api_key:
                        envelope["gaps"].append({"type": "config", "reason": "ALPHAVANTAGE_API_KEY not set"})
                        raw_text = None
                    else:
                        raw_text = _fetch_av(api_key, function, av_params, args.timeout)
            except (HTTPError, URLError, TimeoutError) as exc:
                envelope["gaps"].append({"type": "upstream_error", "reason": f"AV API failed: {exc}"})
                raw_text = None

            if raw_text is not None:
                _process_av_response(raw_text, args.op, pit_dt, envelope, args)
```

### 1.10 `_process_av_response` — Per-op normalize + PIT filter

```python
def _process_av_response(raw_text: str, op: str, pit_dt: datetime | None,
                         envelope: dict[str, Any], args: argparse.Namespace) -> None:
    if op == "earnings":
        data = json.loads(raw_text)
        pit_date_str = pit_dt.astimezone(NY_TZ).strftime("%Y-%m-%d") if pit_dt else None

        # Quarterly earnings — PIT filterable
        pit_excluded = 0
        invalid = 0
        for raw in data.get("quarterlyEarnings", []):
            item, pub_dt, err = _normalize_av_quarterly(raw)
            if err:
                invalid += 1
                continue
            if pit_dt is not None and pub_dt is not None:
                report_time = (raw.get("reportTime") or "").strip().lower()
                if report_time in AV_REPORT_TIME_HOUR:
                    # Full datetime: exact comparison
                    if pub_dt > pit_dt:
                        pit_excluded += 1; continue
                else:
                    # Date-only: exclude PIT day entirely
                    date_str = (raw.get("reportedDate") or "").strip()
                    if date_str >= pit_date_str:
                        pit_excluded += 1; continue
            envelope["data"].append(item)
            if len(envelope["data"]) >= args.limit:
                break

        # Annual earnings — open mode only
        if pit_dt is None:
            for raw in data.get("annualEarnings", []):
                item = _normalize_av_annual(raw)
                envelope["data"].append(item)
        else:
            annual_count = len(data.get("annualEarnings", []))
            if annual_count > 0:
                envelope["gaps"].append({
                    "type": "pit_excluded",
                    "reason": f"{annual_count} annual earnings items excluded (no reportedDate for PIT verification)",
                })

        if pit_excluded > 0:
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": f"{pit_excluded} quarterly items post-PIT",
            })
        if invalid > 0:
            envelope["gaps"].append({
                "type": "unverifiable",
                "reason": f"{invalid} quarterly items with unparseable/missing reportedDate",
            })

    elif op == "estimates":
        if pit_dt is not None:
            # PIT mode: gap entirely (snapshot data, not PIT-verifiable)
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": "EARNINGS_ESTIMATES is a current snapshot — not PIT-verifiable. Use historical EARNINGS actuals for PIT backtests.",
            })
        else:
            data = json.loads(raw_text)
            for raw in data.get("estimates", []):
                item = _normalize_av_estimate(raw)
                envelope["data"].append(item)

    elif op == "calendar":
        if pit_dt is not None:
            # PIT mode: gap entirely (forward-looking snapshot)
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": "EARNINGS_CALENDAR is a forward-looking snapshot — not PIT-verifiable.",
            })
        else:
            # CSV parsing
            import csv, io
            reader = csv.DictReader(io.StringIO(raw_text))
            symbol_filter = (args.symbol or "").upper()
            for row in reader:
                if symbol_filter and row.get("symbol", "").upper() != symbol_filter:
                    continue
                item = _normalize_av_calendar_row(row)
                envelope["data"].append(item)
```

### 1.11 Stderr metadata for AV

```python
meta = {
    "source": "alphavantage",
    "op": args.op,
    "mode": "pit" if args.pit else "open",
    "symbol": symbol,
    "function": function,
    ...
}
```

### 1.12 Docstring update

```python
"""PIT-aware external data wrapper.

Current source support:
- bz-news-api (Benzinga News REST API)
- perplexity (Perplexity AI Search/Chat APIs)
- alphavantage (Alpha Vantage Earnings/Estimates/Calendar)
"""
```

---

## 2. test_pit_fetch.py — New offline tests

**File:** `.claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py`

### Sample data

```python
SAMPLE_AV_EARNINGS = {
    "symbol": "AAPL",
    "annualEarnings": [
        {"fiscalDateEnding": "2024-09-30", "reportedEPS": "6.08"},
        {"fiscalDateEnding": "2023-09-30", "reportedEPS": "6.12"},
    ],
    "quarterlyEarnings": [
        {"fiscalDateEnding": "2024-12-31", "reportedDate": "2025-01-30",
         "reportedEPS": "2.40", "estimatedEPS": "2.34", "surprise": "0.06",
         "surprisePercentage": "2.5641", "reportTime": "post-market"},
        {"fiscalDateEnding": "2024-09-30", "reportedDate": "2024-10-31",
         "reportedEPS": "1.64", "estimatedEPS": "1.60", "surprise": "0.04",
         "surprisePercentage": "2.50", "reportTime": "post-market"},
        {"fiscalDateEnding": "2024-06-30", "reportedDate": "2024-08-01",
         "reportedEPS": "1.40", "estimatedEPS": "1.35", "surprise": "0.05",
         "surprisePercentage": "3.70", "reportTime": "pre-market"},
        {"fiscalDateEnding": "2024-03-31", "reportedDate": "2024-05-02",
         "reportedEPS": "1.53", "estimatedEPS": "1.50", "surprise": "0.03",
         "surprisePercentage": "2.00"},  # no reportTime
    ],
}

SAMPLE_AV_ESTIMATES = {
    "symbol": "AAPL",
    "estimates": [
        {"date": "2025-06-30", "horizon": "next fiscal quarter",
         "eps_estimate_average": "1.72", "eps_estimate_high": "1.85",
         "eps_estimate_low": "1.61", "eps_estimate_analyst_count": "28",
         "revenue_estimate_average": "95000000000", "revenue_estimate_high": "100000000000",
         "revenue_estimate_low": "90000000000", "revenue_estimate_analyst_count": "30"},
        {"date": "2025-09-30", "horizon": "next fiscal year",
         "eps_estimate_average": "8.49", "eps_estimate_high": "8.97",
         "eps_estimate_low": "8.15", "eps_estimate_analyst_count": "38",
         "revenue_estimate_average": "465000000000", "revenue_estimate_high": "480000000000",
         "revenue_estimate_low": "449000000000", "revenue_estimate_analyst_count": "37"},
    ],
}

SAMPLE_AV_CALENDAR_CSV = """symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay
AAPL,APPLE INC,2025-07-31,2025-06-30,1.72,USD,post-market
MSFT,MICROSOFT CORP,2025-07-22,2025-06-30,3.25,USD,post-market
"""
```

### Test cases (10 new)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_av_earnings_open` | Open mode: all 4 quarterly + 2 annual items in data[]. No gaps. |
| 2 | `test_av_earnings_pit_filters_by_reported_date` | PIT=2024-11-01T10:00:00-05:00. Q4 (reported 2025-01-30) excluded. Q3 (reported 2024-10-31, post-market 16:15 < PIT) passes. Q2+Q1 pass. Annual gapped. |
| 3 | `test_av_earnings_pit_post_market_exact` | PIT=2024-10-31T16:15:00-04:00 (exactly at Q3 report time). `pub_dt > pit_dt` is false (equal) → passes. Verifies non-strict inequality. |
| 4 | `test_av_earnings_pit_pre_market` | Q2 reported pre-market 2024-08-01 → available_at = 06:00 ET. PIT at 2024-08-01T07:00:00 → passes (06:00 < 07:00). PIT at 2024-08-01T05:00:00 → excluded (06:00 > 05:00). |
| 5 | `test_av_earnings_pit_no_report_time` | Q1 has no reportTime. reportedDate=2024-05-02. PIT=2024-05-02T16:00:00 → EXCLUDED (date-only, PIT day excluded). PIT=2024-05-03T10:00:00 → passes. |
| 6 | `test_av_earnings_annual_gapped_in_pit` | PIT mode: annual items in gaps[], not data[]. Gap reason mentions count. |
| 7 | `test_av_estimates_open` | Open mode: all estimate items pass through with record_type="estimate". |
| 8 | `test_av_estimates_pit_gapped` | PIT mode: data=[], gaps has "not PIT-verifiable" reason. |
| 9 | `test_av_calendar_open` | Open mode: parsed CSV rows pass through. Only AAPL row (symbol filter). |
| 10 | `test_av_calendar_pit_gapped` | PIT mode: data=[], gaps has "forward-looking snapshot" reason. |

Tests use `--input-file` + `--source alphavantage --op <op> --symbol AAPL`.

---

## 3. Agent rewrite — Bash-wrapper archetype

**File:** `.claude/agents/alphavantage-earnings.md`

```yaml
---
name: alphavantage-earnings
description: "Consensus estimates, actuals, and earnings calendar. Use for beat/miss analysis and upcoming earnings dates."
tools:
  - Bash
model: opus
permissionMode: dontAsk
skills:
  - alphavantage-earnings
  - pit-envelope
  - evidence-standards
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---

# Alpha Vantage Earnings Agent

Query consensus estimates, actual results, and earnings calendar through `$CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py` only.

## Tools

| Op | AV Function | Returns |
|----|-------------|---------|
| `--op earnings` | EARNINGS | Quarterly actuals (EPS, estimates, surprise %) + annual EPS |
| `--op estimates` | EARNINGS_ESTIMATES | Forward + historical consensus (EPS, revenue, analyst count, revisions) |
| `--op calendar` | EARNINGS_CALENDAR | Next earnings date and time |

## Workflow
1. Parse request into wrapper arguments:
   - `--symbol` (required)
   - `--op` (required: `earnings`, `estimates`, or `calendar`)
   - optional `--pit` for historical mode
   - optional `--horizon` for calendar (3month/6month/12month)
   - optional `--limit` for earnings (controls quarterly results)
2. Execute one wrapper call via Bash:
   - Command: `python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source alphavantage --op <op> --symbol <TICKER> ...`
   - PIT mode: include `--pit <ISO8601>`
   - Open mode: omit `--pit`
3. If PIT mode is blocked by hook, retry up to 2 times.
4. Return wrapper JSON envelope as-is (`data[]`, `gaps[]`, no prose).

## PIT Response Contract
See pit-envelope skill for envelope contract, field mappings, and forbidden keys.

### PIT behavior per op:
- **earnings**: Quarterly items filtered by `reportedDate` + `reportTime` (full datetime when available, date-only exclusion otherwise). Annual items gapped (no reportedDate).
- **estimates**: Gapped entirely — current snapshot, not PIT-verifiable.
- **calendar**: Gapped entirely — forward-looking snapshot, not PIT-verifiable.

## Rules
- Use only `python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source alphavantage ...`.
- Bash is wrapper-only for this agent. Do not use Bash for unrelated shell commands.
- Do not call MCP tools directly. Do not call raw HTTP/curl.
- Authentication is automatic via `.env` (`ALPHAVANTAGE_API_KEY`) inside `pit_fetch.py`.
- If auth/env is missing, return wrapper `gaps[]` as-is.
- In PIT mode, never bypass hook validation.
```

---

## 4. Skill rewrite — Command patterns

**File:** `.claude/skills/alphavantage-earnings/SKILL.md`

```yaml
---
name: alphavantage-earnings
description: Consensus estimates and earnings data from Alpha Vantage.
---
```

### Command patterns:

```bash
# Quarterly + annual actuals (open mode)
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --op earnings --symbol AAPL

# Quarterly actuals (PIT mode — annual gapped, post-PIT quarters excluded)
python3 ... --source alphavantage --op earnings --symbol AAPL \
  --pit 2024-11-01T10:00:00-05:00

# Consensus estimates (open mode only — gapped in PIT)
python3 ... --source alphavantage --op estimates --symbol AAPL

# Earnings calendar (open mode only — gapped in PIT)
python3 ... --source alphavantage --op calendar --symbol AAPL --horizon 3month
```

### Response fields by op:

**--op earnings (quarterly):**
- `record_type`: "quarterly_earnings"
- `fiscalDateEnding`, `reportedDate`, `reportTime`
- `reportedEPS`, `estimatedEPS`, `surprise`, `surprisePercentage`
- `available_at` derived from reportedDate + reportTime

**--op earnings (annual, open mode only):**
- `record_type`: "annual_earnings"
- `fiscalDateEnding`, `reportedEPS`
- No `available_at` (open mode pass-through)

**--op estimates (open mode only):**
- `record_type`: "estimate"
- `fiscalDateEnding`, `horizon`
- EPS + revenue consensus (average/high/low/analyst_count)

**--op calendar (open mode only):**
- `record_type`: "earnings_calendar"
- `symbol`, `name`, `reportDate`, `fiscalDateEnding`, `estimate`, `currency`, `timeOfTheDay`

---

## 5. lint_data_agents.py — PIT_DONE update

**File:** `.claude/skills/earnings-orchestrator/scripts/lint_data_agents.py`

Add 1 entry to `PIT_DONE`:
```python
"alphavantage-earnings": {"skills": ["pit-envelope"], "pre": [], "post": ["Bash"]},
```

---

## 6. pit-envelope/SKILL.md — Add AV rows

Add to Field Mapping Table:

| Agent | Source Field | Maps to `available_at` | `available_at_source` | Notes |
|-------|-------------|------------------------|----------------------|-------|
| alphavantage (earnings quarterly) | `reportedDate` + `reportTime` | Full datetime when reportTime available; date-only start-of-day NY otherwise | `provider_metadata` | PIT: full datetime → exact compare; date-only → exclude PIT day |
| alphavantage (earnings annual) | — | open mode pass-through | — | No reportedDate; gapped in PIT mode |
| alphavantage (estimates) | — | open mode pass-through | — | Snapshot data; gapped entirely in PIT mode |
| alphavantage (calendar) | — | open mode pass-through | — | Forward-looking snapshot; gapped entirely in PIT mode |

---

## 7. DataSubAgents.md updates

- Update version line: 2.7 → 2.8, 13/13 PIT-complete
- Phase 4 remaining section: mark alphavantage-earnings as DONE
- Line 521: `pit_fetch.py` status → remove "Needs `alphavantage` source handler"
- Line 536: AV wrapper test → mark as PASSED
- Line 359 (AV EARNINGS): `⚠️` → `✅` with reportTime derivation note
- Line 597: remove "Alpha Vantage — not started"

---

## 8. earnings-orchestrator.md update

- Line 462: `alphavantage-earnings` → `Needs rework` → `**DONE**`
- Line 860: status → "13 of 13 agents fully PIT-compliant"

---

## 9. Files NOT modified

| File | Reason |
|------|--------|
| `pit_gate.py` | Unchanged. `WRAPPER_SCRIPTS` has `pit_fetch.py`. `VALID_SOURCES` has `provider_metadata`. |
| `pit_time.py` | Already exports needed utilities. |
| `alphavantage-routing/SKILL.md` | Reference doc, not affected. |

---

## 10. Implementation order

1. **pit_fetch.py** — Add AV source + handler (~130 new lines)
2. **test_pit_fetch.py** — Add 10 offline tests (~180 new lines)
3. Run: `python3 .claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py`
4. **Agent file** — Rewrite to Bash-wrapper archetype
5. **Skill file** — Rewrite with command patterns
6. **lint_data_agents.py** — Add 1 PIT_DONE entry
7. **pit-envelope/SKILL.md** — Add AV rows
8. **DataSubAgents.md** — Update status to 13/13
9. **earnings-orchestrator.md** — Update status to 13/13
10. Run: `python3 .claude/skills/earnings-orchestrator/scripts/lint_data_agents.py`
11. Run: `python3 .claude/hooks/test_pit_gate.py`

---

## 11. Verification

### Unit tests (offline)
```bash
python3 .claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py
```
Expected: 41/41 PASS (31 existing + 10 AV)

### Linter
```bash
python3 .claude/skills/earnings-orchestrator/scripts/lint_data_agents.py
```
Expected: PASS | 0 errors | 13 agents checked

### pit_gate tests
```bash
python3 .claude/hooks/test_pit_gate.py
```
Expected: 41/41 PASS (unchanged)

### Live smoke tests (requires ALPHAVANTAGE_API_KEY in .env)
```bash
# Earnings open mode
python3 .../pit_fetch.py --source alphavantage --op earnings --symbol AAPL

# Earnings PIT mode
python3 .../pit_fetch.py --source alphavantage --op earnings --symbol AAPL \
  --pit 2024-11-01T10:00:00-05:00

# Estimates open mode
python3 .../pit_fetch.py --source alphavantage --op estimates --symbol AAPL

# Calendar open mode
python3 .../pit_fetch.py --source alphavantage --op calendar --symbol AAPL

# Estimates PIT mode (should be all gaps)
python3 .../pit_fetch.py --source alphavantage --op estimates --symbol AAPL \
  --pit 2024-11-01T10:00:00-05:00
```

---

## Summary

| What | Count | Lines (est.) |
|------|-------|-------------|
| pit_fetch.py (1 source, 3 ops) | 1 | +130 |
| test_pit_fetch.py tests | 10 | +180 |
| Agent rewrite | 1 | ~55 |
| Skill rewrite | 1 | ~60 |
| lint PIT_DONE entry | 1 | +5 |
| pit-envelope rows | 4 | +4 |
| DataSubAgents.md update | ~6 lines | +10 |
| earnings-orchestrator.md update | 2 lines | +2 |
| **Total** | | **~450 lines** |
