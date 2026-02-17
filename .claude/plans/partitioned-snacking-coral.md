# Perplexity PIT Implementation — 5 Agents, 2 Handlers

## Context

7/13 data subagents are PIT-DONE. The 5 Perplexity agents (search, ask, reason, research, sec) currently lack PIT compliance, envelope contracts, and hook validation. This plan adds one source (`--source perplexity`) with an `--op` flag to pit_fetch.py, rewrites all 5 agents to the Bash-wrapper archetype, and achieves full PIT/Open compliance.

**API reality (verified from docs):**
- `POST /search` — raw ranked results, $0.005/req flat, no token costs
- `POST /chat/completions` — synthesized answer + search_results, token-priced per model

Both endpoints return per-result `date` and `last_updated` fields. MCP server (any version) discards `search_results[]` from chat/completions — pit_fetch.py calls APIs directly, so we get everything.

**Agent-to-API mapping:**

| Agent | --op | API Endpoint | Model (internal) | Notes |
|---|---|---|---|---|
| perplexity-search | search | POST /search | n/a | Cheapest, raw results |
| perplexity-ask | ask | POST /chat/completions | sonar-pro | Synthesized answer |
| perplexity-reason | reason | POST /chat/completions | sonar-reasoning-pro | Answer + reasoning_steps |
| perplexity-research | research | POST /chat/completions | sonar-deep-research | Comprehensive report |
| perplexity-sec | search | POST /search | n/a | + --search-mode sec (locator-first) |

**Date mapping policy (decided):**
- **Full timestamp available** (ISO8601 with time+tz): use exact PIT datetime comparison (`created_dt > pit_dt` → excluded), same as BZ handler.
- **Date-only** (YYYY-MM-DD): exclude PIT day entirely. If PIT = 2024-06-15T16:00:00, articles dated 2024-06-15 or later are excluded. Only prior-day articles pass.
- Server-side `search_before_date_filter` is a **coarse prefilter** only. Client-side PIT filter in pit_fetch.py is the **source of truth**.

---

## 1. pit_fetch.py — One source, one --op flag

**File:** `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py` (398 → ~560 lines)

### 1.1 New constants

```python
PPLX_SEARCH_URL = "https://api.perplexity.ai/search"
PPLX_CHAT_URL = "https://api.perplexity.ai/chat/completions"

PPLX_OP_MODEL: dict[str, str | None] = {
    "search": None,           # POST /search, no model
    "ask": "sonar-pro",
    "reason": "sonar-reasoning-pro",
    "research": "sonar-deep-research",
}
```

### 1.2 New parser args

Extend `--source` choices:
```python
choices=["bz-news-api", "benzinga", "benzinga-news", "perplexity"]
```

New arguments:
```python
p.add_argument("--op", choices=["search", "ask", "reason", "research"],
               help="Perplexity operation mode (required when --source perplexity)")
p.add_argument("--query", action="append", dest="queries",
               help="Search query (repeatable for multi-pass)")
p.add_argument("--max-results", type=int, default=10, dest="max_results",
               help="Results per query (1-20, /search only)")
p.add_argument("--search-recency", dest="search_recency",
               choices=["hour", "day", "week", "month", "year"])
p.add_argument("--search-domains", dest="search_domains",
               help="Comma-separated domain allowlist or -prefixed denylist")
p.add_argument("--search-mode", dest="search_mode",
               choices=["web", "academic", "sec"], default="web")
p.add_argument("--search-context-size", dest="search_context_size",
               choices=["low", "medium", "high"], default="low")
```

### 1.3 Date helpers

```python
def _to_pplx_date(iso_date: str) -> str:
    """YYYY-MM-DD → MM/DD/YYYY for Perplexity date filters."""
    parts = iso_date.split("-")
    return f"{parts[1]}/{parts[2]}/{parts[0]}"

def _pit_to_pplx_date(pit_str: str) -> str | None:
    """PIT ISO8601 → MM/DD/YYYY (the PIT day itself, for 'before' filter)."""
    dt = _parse_dt(pit_str)
    return dt.strftime("%m/%d/%Y") if dt else None

def _pit_to_date_str(pit_str: str) -> str | None:
    """PIT ISO8601 → YYYY-MM-DD for client-side date comparison."""
    dt = _parse_dt(pit_str)
    return dt.strftime("%Y-%m-%d") if dt else None
```

### 1.4 `_normalize_pplx_result` (same tuple signature as `_normalize_bz_item`)

Works for both `/search` results and `/chat/completions` search_results — same schema.

```python
def _normalize_pplx_result(raw: Any) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    if not isinstance(raw, dict):
        return None, None, "raw item is not an object"

    # PIT validates PUBLICATION date, not modification date (DataSubAgents.md §4.3).
    # `date` = publication date (the field PIT cares about).
    # `last_updated` = modification date (NOT publication — different semantics).
    # If `date` is missing, the item has no reliable publication metadata → unverifiable gap
    # (DataSubAgents.md §4.3 line 130: "must be dropped in PIT mode or returned as a gap").
    # `last_updated` is preserved as metadata but NEVER used for PIT timestamp derivation.
    date_raw = raw.get("date")
    if not isinstance(date_raw, str) or not date_raw.strip():
        url = raw.get("url", "unknown")
        return None, None, f"item {url} missing publication date field"

    # YYYY-MM-DD → start-of-day NY (used only for PIT comparison ordering)
    pub_dt: datetime | None = None
    text = date_raw.strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        try:
            pub_dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=NY_TZ)
        except ValueError:
            pass
    if pub_dt is None:
        pub_dt = _parse_dt(date_raw)
    if pub_dt is None:
        return None, None, f"unparseable date: {date_raw}"

    item = {
        "available_at": _to_new_york_iso(pub_dt),
        "available_at_source": "provider_metadata",
        "url": raw.get("url"),
        "title": raw.get("title"),
        "snippet": raw.get("snippet", ""),
        "date": date_raw,
        "last_updated": raw.get("last_updated"),
    }
    return item, pub_dt, None
```

### 1.5 `_build_pplx_date_filters` (shared by both endpoints)

```python
def _build_pplx_date_filters(args: argparse.Namespace) -> dict[str, str]:
    filters: dict[str, str] = {}
    if args.pit:
        pplx_date = _pit_to_pplx_date(args.pit)
        if pplx_date:
            filters["search_before_date_filter"] = pplx_date  # excludes PIT day
    elif args.date_to:
        filters["search_before_date_filter"] = _to_pplx_date(args.date_to)
    if args.date_from:
        filters["search_after_date_filter"] = _to_pplx_date(args.date_from)
    return filters
```

### 1.6 Handler A: `_fetch_pplx_search` (POST /search)

```python
def _fetch_pplx_search(api_key: str, args: argparse.Namespace) -> list[Any]:
    all_results: list[Any] = []
    date_filters = _build_pplx_date_filters(args)
    for query in args.queries:
        body: dict[str, Any] = {
            "query": query,
            "max_results": min(20, max(1, args.max_results)),
        }
        body.update(date_filters)
        if args.search_recency:
            body["search_recency_filter"] = args.search_recency
        if args.search_domains:
            body["search_domain_filter"] = _csv(args.search_domains)
        if args.search_mode != "web":
            body["search_mode"] = args.search_mode

        data = json.dumps(body).encode("utf-8")
        req = Request(PPLX_SEARCH_URL, data=data, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "pit-fetch/1.0",
        }, method="POST")
        with urlopen(req, timeout=args.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        results = payload.get("results", [])
        if isinstance(results, list):
            all_results.extend(results)
    return all_results
```

### 1.7 Handler B: `_fetch_pplx_chat` (POST /chat/completions)

Returns `(search_results_list, answer_str, citations_list)`.

```python
def _fetch_pplx_chat(api_key: str, args: argparse.Namespace, model: str) -> tuple[list[Any], str, list[str]]:
    combined_query = "\n".join(args.queries)
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": combined_query}],
    }
    date_filters = _build_pplx_date_filters(args)
    body.update(date_filters)
    if args.search_recency:
        body["search_recency_filter"] = args.search_recency
    if args.search_domains:
        body["search_domain_filter"] = _csv(args.search_domains)
    if args.search_mode != "web":
        body["search_mode"] = args.search_mode
    if args.search_context_size != "low":
        body["web_search_options"] = {"search_context_size": args.search_context_size}

    data = json.dumps(body).encode("utf-8")
    req = Request(PPLX_CHAT_URL, data=data, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "pit-fetch/1.0",
    }, method="POST")
    with urlopen(req, timeout=max(args.timeout, 60)) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    search_results = payload.get("search_results", [])
    answer = ""
    choices = payload.get("choices", [])
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message", {})
        answer = msg.get("content", "")
    citations = payload.get("citations", [])

    return (
        search_results if isinstance(search_results, list) else [],
        answer if isinstance(answer, str) else "",
        citations if isinstance(citations, list) else [],
    )
```

### 1.8 Source dispatch in `main()`

```python
is_pplx = args.source == "perplexity"
answer_text = ""
citations_list: list[str] = []

if is_pplx:
    if not args.op:
        envelope["gaps"].append({"type": "config", "reason": "--op required for perplexity"})
    elif not args.queries:
        envelope["gaps"].append({"type": "config", "reason": "--query required"})
    else:
        _load_env()
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            envelope["gaps"].append({"type": "config", "reason": "PERPLEXITY_API_KEY not set"})
        else:
            model = PPLX_OP_MODEL[args.op]
            try:
                if model is None:  # --op search → POST /search
                    raw_items = _fetch_pplx_search(api_key, args)
                else:              # --op ask/reason/research → POST /chat/completions
                    raw_items, answer_text, citations_list = _fetch_pplx_chat(api_key, args, model)
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                envelope["gaps"].append({"type": "upstream_error", "reason": f"Perplexity API failed: {exc}"})
            except Exception as exc:
                envelope["gaps"].append({"type": "internal_error", "reason": f"Unexpected: {exc}"})
else:
    # Existing BZ path (unchanged)
    ...
```

### 1.9 PIT client-side filtering (two-tier)

The normalizer (`_normalize_pplx_result`) already parses the date into a `pub_dt` datetime. The PIT comparison logic in the normalize loop handles both cases:

```python
# Full timestamp (ISO8601 with time+tz): exact comparison (same as BZ)
# Date-only (YYYY-MM-DD): exclude PIT day entirely
if pit_dt is not None and created_dt is not None:
    if len(date_raw_str) == 10:  # date-only YYYY-MM-DD
        # Exclude PIT day: compare date strings
        pit_date_str = pit_dt.strftime("%Y-%m-%d")
        if date_raw_str >= pit_date_str:
            pit_excluded += 1; continue
    else:  # full timestamp
        if created_dt > pit_dt:
            pit_excluded += 1; continue
```

This honors the agreed rule: use exact PIT compare when a full timestamp exists; only use day-level exclusion for date-only results.

### 1.10 Synthesis item in data[] (chat ops)

For chat ops (ask/reason/research), the synthesized answer is added as a `data[]` item with `record_type: "synthesis"`. This keeps the single `{data[], gaps[]}` contract intact and ensures pit_gate.py validates it like any other item.

```python
if is_pplx and args.op != "search" and answer_text:
    # Use current time as available_at for synthesis (it was just generated)
    synthesis_item = {
        "record_type": "synthesis",
        "answer": answer_text,
        "citations": citations_list,
        "available_at": _to_new_york_iso(datetime.now(timezone.utc)),
        "available_at_source": "provider_metadata",
    }
    envelope["data"].append(synthesis_item)
```

In PIT mode, the synthesis `available_at` will be "now" which is always > PIT. To prevent pit_gate.py from blocking, the synthesis item should be **excluded in PIT mode** (the agent gets only raw search_results). In open mode, the synthesis item passes through normally.

### 1.11 Import change

```python
from pit_time import parse_timestamp, to_new_york_iso, NY_TZ
```

### 1.12 Stderr metadata

```python
meta = {
    "source": "perplexity",
    "op": args.op,
    "mode": "pit" if args.pit else "open",
    "model": PPLX_OP_MODEL.get(args.op),
    "queries": args.queries,
    "search_mode": args.search_mode,
    ...
}
```

---

## 2. test_pit_fetch.py — New offline tests

**File:** `.claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py` (223 → ~380 lines)

### Sample data

```python
SAMPLE_PPLX_RESULTS = [
    {"url": "https://example.com/a", "title": "AAPL Q1 beat", "snippet": "EPS $2.18...",
     "date": "2024-06-10", "last_updated": "2024-06-10"},
    {"url": "https://example.com/b", "title": "AAPL guidance", "snippet": "Revenue up...",
     "date": "2024-06-14", "last_updated": "2024-06-15"},
    {"url": "https://example.com/c", "title": "Undated article", "snippet": "No date"},
]
```

### Test cases (8 new)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_pplx_search_open` | --op search, no PIT. Envelope: 2 valid items, 1 undated gap |
| 2 | `test_pplx_search_pit_excludes_pit_day` | PIT=2024-06-14T16:00:00. date:2024-06-14 EXCLUDED (same day). Only date:2024-06-10 passes |
| 3 | `test_pplx_all_undated` | All items missing date → data=[], gaps has unverifiable+no_data |
| 4 | `test_pplx_date_summer_edt` | date:2024-06-10 → available_at: 2024-06-10T00:00:00-04:00 (EDT) |
| 5 | `test_pplx_date_winter_est` | date:2024-01-15 → available_at: 2024-01-15T00:00:00-05:00 (EST) |
| 6 | `test_pplx_dedup_by_url` | Two same-URL items → only first kept |
| 7 | `test_pplx_chat_open` | --op ask, open mode. data[] has search_results + synthesis item (record_type: "synthesis" with answer + citations). |
| 8 | `test_pplx_chat_pit` | --op ask + PIT. search_results filtered by PIT in data[]. Synthesis item EXCLUDED (available_at = now > PIT). data[] contains only PIT-filtered search results. |

Tests use `--input-file` + `--source perplexity --op search --query dummy`.

For chat tests (7-8): input file wraps results with answer/citations. Need small loader extension in pit_fetch.py for `--input-file` + chat ops.

---

## 3. Agent rewrites — Bash-wrapper archetype

All 5 agents get identical frontmatter (matching `bz-news-api.md`):

```yaml
---
name: <agent-name>
description: "<description>"
tools:
  - Bash
model: opus
permissionMode: dontAsk
skills:
  - <per-agent-skill>
  - pit-envelope
  - evidence-standards
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---
```

### 3.1 perplexity-search.md
- Command: `--source perplexity --op search --query "..." --max-results 10`
- Returns: raw search results in data[]. No answer field.

### 3.2 perplexity-ask.md
- Command: `--source perplexity --op ask --query "..." --search-context-size medium`
- Returns: data[] containing PIT-filtered search_results + synthesis item (record_type: "synthesis", open mode only). In PIT mode, synthesis excluded (available_at > PIT).

### 3.3 perplexity-reason.md
- Command: `--source perplexity --op reason --query "..." --search-context-size medium`
- Returns: data[] containing PIT-filtered search_results + synthesis item (record_type: "synthesis", open mode only). In PIT mode, synthesis excluded.

### 3.4 perplexity-research.md
- Command: `--source perplexity --op research --query "..." --search-context-size high --timeout 120`
- Returns: data[] containing PIT-filtered search_results + synthesis item (record_type: "synthesis", open mode only). In PIT mode, synthesis excluded. Slow (30+ sec).

### 3.5 perplexity-sec.md
- Command: `--source perplexity --op search --search-mode sec --query "..." --max-results 10`
- Returns: raw EDGAR filing results in data[] (locator-first, no synthesis)
- Replaces legacy `utils/perplexity_search.py` path
- Aligned with DataSubAgents.md SEC lane: cautious/locator-first approach

---

## 4. Skill rewrites — Command patterns

Each skill gets PIT/Open command examples following `bz-news-api-queries/SKILL.md` pattern.

### 4.1 perplexity-search/SKILL.md
```bash
# PIT mode
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search --query "AAPL earnings Q1 2025" \
  --pit 2025-02-01T00:00:00-05:00 --max-results 10 --limit 10

# Open mode (omit --pit)
python3 ... --source perplexity --op search --query "AAPL earnings" --max-results 10

# With filters
  --search-recency month --search-domains sec.gov,reuters.com --search-mode academic
```

### 4.2 perplexity-ask/SKILL.md
```bash
python3 ... --source perplexity --op ask \
  --query "What was AAPL's Q1 2025 EPS vs consensus?" --search-context-size medium
```
Notes: In open mode, data[] includes a synthesis item (record_type: "synthesis") with answer + citations. In PIT mode, synthesis excluded — agent works from filtered search_results only.

### 4.3 perplexity-reason/SKILL.md
```bash
python3 ... --source perplexity --op reason \
  --query "Why did AAPL drop after Q1 2025 earnings despite beating estimates?" \
  --search-context-size medium
```
Notes: Same envelope behavior as ask. Synthesis item in open mode only.

### 4.4 perplexity-research/SKILL.md
```bash
python3 ... --source perplexity --op research \
  --query "Comprehensive analysis of AAPL Q1 2025 earnings" \
  --search-context-size high --timeout 120
```
Notes: Same envelope behavior. Slow (30+ sec). --timeout 120 recommended.

### 4.5 perplexity-sec/SKILL.md
```bash
python3 ... --source perplexity --op search --search-mode sec \
  --query "AAPL 10-K risk factors FY2024" \
  --date-from 2024-01-01 --date-to 2024-12-31 --max-results 10
```
Notes: Locator-first — returns raw EDGAR filing links. Agent processes results directly.

---

## 5. lint_data_agents.py — PIT_DONE updates

**File:** `.claude/skills/earnings-orchestrator/scripts/lint_data_agents.py`

Add 5 entries to `PIT_DONE` (same pattern as `bz-news-api`):
```python
"perplexity-search":   {"skills": ["pit-envelope"], "pre": [], "post": ["Bash"]},
"perplexity-ask":      {"skills": ["pit-envelope"], "pre": [], "post": ["Bash"]},
"perplexity-reason":   {"skills": ["pit-envelope"], "pre": [], "post": ["Bash"]},
"perplexity-research": {"skills": ["pit-envelope"], "pre": [], "post": ["Bash"]},
"perplexity-sec":      {"skills": ["pit-envelope"], "pre": [], "post": ["Bash"]},
```

---

## 6. pit-envelope/SKILL.md — Add Perplexity rows

Add to Field Mapping Table:

| Agent | Source Field | Maps to `available_at` | `available_at_source` | Notes |
|-------|-------------|------------------------|----------------------|-------|
| perplexity-* (search) | result `date` | YYYY-MM-DD → start-of-day NY tz | `provider_metadata` | PIT: exclude PIT day entirely |
| perplexity-* (chat) | `search_results[].date` | same | `provider_metadata` | Chat ops add synthesis item (record_type: "synthesis") to data[] in open mode; excluded in PIT mode |

---

## 7. Files NOT modified

| File | Reason |
|------|--------|
| `pit_gate.py` | Unchanged. `WRAPPER_SCRIPTS` has `pit_fetch.py`. `VALID_SOURCES` has `provider_metadata`. Synthesis item in data[] uses `provider_metadata` source. |
| `pit_time.py` | Already exports `NY_TZ`, `parse_timestamp`, `to_new_york_iso`. |
| `utils/perplexity_search.py` | Legacy. Not modified/deleted — perplexity-sec agent stops using it. |

## 7.1 DataSubAgents.md cross-doc alignment (update during implementation)

Two policy updates needed in `DataSubAgents.md` to align with this plan:

**A. Date-only admissibility (line 355)**
Current wording: "Date-only is not PIT-compliant by itself; must resolve provider-backed publish datetime or gap"
Updated policy: Date-only items from days **strictly before** PIT are admissible under the conservative "exclude PIT day" rule. Items from the PIT day or later are excluded. This is fail-closed in spirit: even worst-case intra-day publication (23:59:59) on a prior day is before PIT.

Update line 355 to:
> `Perplexity Search API (POST /search) | date | ⚠️→✅ | Date-only: exclude PIT day entirely (prior-day items pass, PIT-day items excluded). Conservative fail-closed.`

**B. last_updated is NOT a publication date proxy (line 355-357)**
Clarify that `last_updated` is a modification timestamp, not publication metadata. The normalizer uses `date` only — items without `date` are dropped as unverifiable gaps per §4.3 line 130. `last_updated` is preserved as metadata but never used for `available_at` derivation.

**C. Chat ops (line 357)**
Update to reflect that pit_fetch.py calls the API directly (not MCP), so `search_results[]` with per-result `date` fields ARE available. This upgrades chat ops from "Lane 3: must extract from citations" to Lane 2 (structured-by-provider) for the search_results portion. The synthesis answer remains excluded in PIT mode.

---

## 8. Implementation order

1. **pit_fetch.py** — Add Perplexity source + both handlers (~160 new lines)
2. **test_pit_fetch.py** — Add 8 offline tests (~160 new lines)
3. Run: `python3 .claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py`
4. **5 agent files** — Rewrite to Bash-wrapper archetype
5. **5 skill files** — Rewrite with command patterns
6. **lint_data_agents.py** — Add 5 PIT_DONE entries
7. **pit-envelope/SKILL.md** — Add Perplexity rows
8. **DataSubAgents.md** — Update lines 355-357 per §7.1 (date-only policy, last_updated, chat ops lane)
9. Run: `python3 .claude/skills/earnings-orchestrator/scripts/lint_data_agents.py`
10. Run: `python3 .claude/hooks/test_pit_gate.py`

---

## 9. Verification

### Unit tests (offline)
```bash
python3 .claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py
```
Expected: 14/14 PASS (6 BZ + 8 perplexity)

### Linter
```bash
python3 .claude/skills/earnings-orchestrator/scripts/lint_data_agents.py
```
Expected: PASS | 0 errors | 13 agents checked (discovery scope unchanged)

### pit_gate tests
```bash
python3 .claude/hooks/test_pit_gate.py
```
Expected: 41/41 PASS (unchanged)

### Live smoke tests (requires PERPLEXITY_API_KEY)
```bash
# Search op
python3 .../pit_fetch.py --source perplexity --op search --query "AAPL earnings" --max-results 5

# Ask op
python3 .../pit_fetch.py --source perplexity --op ask --query "What was AAPL Q1 2025 EPS?"

# SEC mode
python3 .../pit_fetch.py --source perplexity --op search --search-mode sec --query "AAPL 10-K 2024"

# PIT mode (excludes PIT day)
python3 .../pit_fetch.py --source perplexity --op search --query "AAPL earnings" \
  --pit 2025-01-01T00:00:00-05:00 --max-results 5
```

---

## 10. API reference (for implementation)

### POST /search — Key fields
- Input: query (string|array≤5), max_results (1-20), search_before/after_date_filter (MM/DD/YYYY), search_mode (web/academic/sec), search_domain_filter, search_recency_filter
- Response: `results[].{title, url, snippet, date?, last_updated?}`

### POST /chat/completions — Key fields
- Input: model, messages[], search_before/after_date_filter, search_mode, search_domain_filter, search_recency_filter, web_search_options.search_context_size (low/medium/high), response_format
- Response: `choices[].message.content` (answer), `citations[]` (URLs), `search_results[].{title, url, snippet, date?, last_updated?, source}`, `usage.cost.total_cost`

### Models
| Model ID | Type | Input/1M | Output/1M |
|---|---|---|---|
| sonar-pro | Search | $3 | $15 |
| sonar-reasoning-pro | Reasoning | $2 | $8 |
| sonar-deep-research | Research | $2 | $8 |

### PIT date filtering strategy
- **Server-side (coarse prefilter):** `search_before_date_filter` = PIT date (MM/DD/YYYY). Treats API filter as best-effort hint, not authoritative.
- **Client-side (source of truth):** Two-tier logic in pit_fetch.py:
  - Full timestamp: exact `created_dt > pit_dt` comparison
  - Date-only: `result.date[:10] >= pit_date_str` → excluded (PIT day excluded entirely)
- **Net effect for date-only:** Articles from days strictly BEFORE the PIT date pass. Most conservative.

---

## Summary

| What | Count | Lines (est.) |
|------|-------|-------------|
| pit_fetch.py (1 source, 2 internal handlers) | 1 | +160 |
| test_pit_fetch.py tests | 8 | +160 |
| Agent rewrites | 5 | 5 × ~40 = 200 |
| Skill rewrites | 5 | 5 × ~50 = 250 |
| lint PIT_DONE entries | 5 | +20 |
| pit-envelope rows | 2 | +2 |
| DataSubAgents.md policy update | 3 | +5 |
| **Total** | | **~800 lines** |
