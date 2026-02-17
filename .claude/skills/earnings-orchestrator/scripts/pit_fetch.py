#!/usr/bin/env python3
"""PIT-aware external data wrapper.

Current source support:
- bz-news-api (Benzinga News REST API)
- perplexity (Perplexity AI Search/Chat APIs)

Output contract:
- JSON envelope with `data[]` and `gaps[]`
- In PIT mode, each item includes `available_at` and `available_at_source`
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
try:
    from pit_time import parse_timestamp, to_new_york_iso, NY_TZ
except ModuleNotFoundError:
    # Support module-style imports (e.g., `import scripts.pit_fetch`)
    from scripts.pit_time import parse_timestamp, to_new_york_iso, NY_TZ

# --- Benzinga constants ---
API_URL = "https://api.benzinga.com/api/v2/news"
DEFAULT_LIMIT = 50
DEFAULT_MAX_PAGES = 10
DEFAULT_LOOKBACK_MINUTES = 24 * 60

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "macro": (
        "macro",
        "economy",
        "economic",
        "fed",
        "federal reserve",
        "inflation",
        "cpi",
        "rates",
        "interest rate",
        "gdp",
        "treasury",
    ),
    "oil": (
        "oil",
        "crude",
        "wti",
        "brent",
        "opec",
        "energy",
        "natural gas",
    ),
}

# --- Perplexity constants ---
PPLX_SEARCH_URL = "https://api.perplexity.ai/search"
PPLX_CHAT_URL = "https://api.perplexity.ai/chat/completions"

PPLX_OP_MODEL: dict[str, str | None] = {
    "search": None,           # POST /search, no model
    "ask": "sonar-pro",
    "reason": "sonar-reasoning-pro",
    "research": "sonar-deep-research",
}


# ── Shared helpers ──

def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_dt(value: Any) -> datetime | None:
    return parse_timestamp(value)


def _to_new_york_iso(dt: datetime) -> str:
    return to_new_york_iso(dt)


# ── Perplexity date helpers ──

def _to_pplx_date(iso_date: str) -> str:
    """YYYY-MM-DD -> MM/DD/YYYY for Perplexity date filters."""
    parts = iso_date.split("-")
    return f"{parts[1]}/{parts[2]}/{parts[0]}"


def _pit_to_pplx_date(pit_str: str) -> str | None:
    """PIT ISO8601 -> MM/DD/YYYY (the PIT day in NY tz, for 'before' filter)."""
    dt = _parse_dt(pit_str)
    if dt is None:
        return None
    return dt.astimezone(NY_TZ).strftime("%m/%d/%Y")


# ── Benzinga helpers ──

def _as_names(value: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(value, list):
        return out
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
            continue
        if isinstance(item, dict):
            name = item.get("name") or item.get("symbol")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


def _normalize_bz_item(raw: Any) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    if not isinstance(raw, dict):
        return None, None, "raw item is not an object"

    created_raw = raw.get("created")
    created_dt = _parse_dt(created_raw)
    if created_dt is None:
        ident = raw.get("id", "unknown")
        return None, None, f"item {ident} missing/unparseable created timestamp"

    symbols = _as_names(raw.get("stocks")) or _as_names(raw.get("symbols"))
    channels = _as_names(raw.get("channels"))
    tags = _as_names(raw.get("tags"))

    body = raw.get("body")
    if not isinstance(body, str):
        body = None

    item = {
        "available_at": _to_new_york_iso(created_dt),
        "available_at_source": "provider_metadata",
        "id": str(raw.get("id", "")),
        "title": raw.get("title"),
        "teaser": raw.get("teaser"),
        "body": body,
        "url": raw.get("url"),
        "symbols": symbols,
        "channels": channels,
        "tags": tags,
        "created": created_raw,
        "updated": raw.get("updated"),
    }
    return item, created_dt, None


# ── Perplexity normalizer ──

def _normalize_pplx_result(raw: Any) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    """Normalize a Perplexity search result into envelope item.

    Works for both /search results and /chat/completions search_results.
    Uses `date` (publication date) for PIT. `last_updated` is preserved as
    metadata but never used for available_at derivation.
    """
    if not isinstance(raw, dict):
        return None, None, "raw item is not an object"

    date_raw = raw.get("date")
    if not isinstance(date_raw, str) or not date_raw.strip():
        url = raw.get("url", "unknown")
        return None, None, f"item {url} missing publication date field"

    pub_dt: datetime | None = None
    text = date_raw.strip()
    # Date-only YYYY-MM-DD -> start-of-day NY tz
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


# ── Filters (BZ-specific) ──

def _matches_filters(
    item: dict[str, Any],
    tickers: set[str],
    channels: set[str],
    tags: set[str],
    keywords: list[str],
) -> bool:
    item_symbols = {
        s.strip().upper()
        for s in item.get("symbols", [])
        if isinstance(s, str) and s.strip()
    }
    item_channels = {
        c.strip().lower()
        for c in item.get("channels", [])
        if isinstance(c, str) and c.strip()
    }
    item_tags = {
        t.strip().lower()
        for t in item.get("tags", [])
        if isinstance(t, str) and t.strip()
    }

    if tickers and not (item_symbols & tickers):
        return False
    if channels and not (item_channels & channels):
        return False
    if tags and not (item_tags & tags):
        return False

    if keywords:
        blob_parts: list[str] = []
        for key in ("title", "teaser", "body"):
            val = item.get(key)
            if isinstance(val, str):
                blob_parts.append(val)
        blob_parts.extend(item.get("channels", []))
        blob_parts.extend(item.get("tags", []))
        blob = " ".join(str(v) for v in blob_parts).lower()
        if not any(k in blob for k in keywords):
            return False

    return True


# ── API fetchers ──

def _fetch_bz_items(api_key: str, args: argparse.Namespace) -> list[Any]:
    page = 0
    # Over-fetch raw pages so PIT/filtering can still satisfy small limits.
    page_size = max(1, min(99, max(args.limit, DEFAULT_LIMIT)))
    max_pages = max(1, args.max_pages)
    all_items: list[Any] = []

    while page < max_pages:
        params: dict[str, Any] = {
            "token": api_key,
            "page": page,
            "pageSize": page_size,
            "displayOutput": "full",
            "sort": "updated:desc",
        }
        if args.date_from:
            params["dateFrom"] = args.date_from
        if args.date_to:
            params["dateTo"] = args.date_to
        if args.updated_since is not None:
            params["updatedSince"] = args.updated_since
        if args.tickers:
            params["tickers"] = ",".join(args.tickers)

        url = f"{API_URL}?{urlencode(params)}"
        request = Request(url, headers={"accept": "application/json", "user-agent": "pit-fetch/1.0"})
        with urlopen(request, timeout=args.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, list):
            raise ValueError("Benzinga response is not a JSON array")
        if not payload:
            break

        all_items.extend(payload)
        if len(payload) < page_size:
            break
        page += 1

    return all_items


def _build_pplx_date_filters(args: argparse.Namespace) -> dict[str, str]:
    """Build server-side date filters for Perplexity API (coarse prefilter)."""
    filters: dict[str, str] = {}
    if args.pit:
        pplx_date = _pit_to_pplx_date(args.pit)
        if pplx_date:
            filters["search_before_date_filter"] = pplx_date
    elif args.date_to:
        filters["search_before_date_filter"] = _to_pplx_date(args.date_to)
    if args.date_from:
        filters["search_after_date_filter"] = _to_pplx_date(args.date_from)
    return filters


def _fetch_pplx_search(api_key: str, args: argparse.Namespace) -> list[Any]:
    """POST /search — raw ranked results, no model."""
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


def _fetch_pplx_chat(api_key: str, args: argparse.Namespace, model: str) -> tuple[list[Any], str, list[str]]:
    """POST /chat/completions — synthesized answer + search_results."""
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


# ── Input file loaders ──

def _load_input_items(path: str) -> list[Any]:
    """Load BZ input file (JSON array or {items: []})."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("items"), list):
        return raw["items"]
    raise ValueError("input file must contain a JSON array or {'items': [...]}")


def _load_pplx_input(path: str, is_chat: bool) -> tuple[list[Any], str, list[str]]:
    """Load Perplexity input file. For chat ops, also extracts answer + citations."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items: list[Any] = []
    answer = ""
    citations: list[str] = []

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if is_chat:
            items = raw.get("search_results", raw.get("results", raw.get("items", [])))
            answer = raw.get("answer", "")
            citations = raw.get("citations", [])
        else:
            items = raw.get("results", raw.get("items", []))

    if not isinstance(items, list):
        items = []
    if not isinstance(answer, str):
        answer = ""
    if not isinstance(citations, list):
        citations = []

    return items, answer, citations


# ── Parser ──

def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PIT-aware external data fetch wrapper")
    p.add_argument("--source", required=True,
                   choices=["bz-news-api", "benzinga", "benzinga-news", "perplexity"])
    p.add_argument("--pit", help="ISO8601 PIT timestamp (optional)")
    p.add_argument("--date-from", dest="date_from", help="YYYY-MM-DD")
    p.add_argument("--date-to", dest="date_to", help="YYYY-MM-DD")
    p.add_argument("--updated-since", dest="updated_since", type=int, help="Unix timestamp")
    p.add_argument(
        "--lookback-minutes",
        type=int,
        default=DEFAULT_LOOKBACK_MINUTES,
        help=f"Default updated-since lookback when no date range provided (default: {DEFAULT_LOOKBACK_MINUTES})",
    )
    p.add_argument("--tickers", help="Comma-separated symbols")
    p.add_argument("--channels", help="Comma-separated channel filters")
    p.add_argument("--tags", help="Comma-separated tag filters")
    p.add_argument("--keywords", help="Comma-separated keyword contains filters")
    p.add_argument("--themes", help="Comma-separated theme aliases (macro,oil)")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Max search results returned (default: {DEFAULT_LIMIT}). Chat ops append synthesis separately.")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help=f"Max pages fetched (default: {DEFAULT_MAX_PAGES})")
    p.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    p.add_argument("--input-file", help="Optional local JSON file for offline testing")
    # Perplexity-specific
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
    return p


def main() -> None:
    parser = _make_parser()
    args = parser.parse_args()
    args.limit = max(1, args.limit)

    is_pplx = args.source == "perplexity"

    # BZ-specific filter setup (only when not perplexity)
    if not is_pplx:
        args.tickers = [t.upper() for t in _csv(args.tickers)]
        requested_tickers = set(args.tickers)
        requested_channels = {c.lower() for c in _csv(args.channels)}
        requested_tags = {t.lower() for t in _csv(args.tags)}
        requested_keywords = [k.lower() for k in _csv(args.keywords)]
        requested_themes = [t.lower() for t in _csv(args.themes)]

        for theme in requested_themes:
            requested_keywords.extend(THEME_KEYWORDS.get(theme, (theme,)))

        if (
            args.updated_since is None
            and not args.date_from
            and not args.date_to
            and not args.input_file
        ):
            args.updated_since = int(
                (datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)).timestamp()
            )

    envelope: dict[str, Any] = {
        "data": [],
        "gaps": [],
    }

    pit_dt = _parse_dt(args.pit) if args.pit else None
    if args.pit and pit_dt is None:
        envelope["gaps"].append({
            "type": "invalid_pit",
            "reason": f"Unparseable --pit timestamp: {args.pit}",
        })

    raw_items: list[Any] = []
    answer_text = ""
    citations_list: list[str] = []

    # ── Fetch raw data ──
    if is_pplx:
        if not args.op:
            envelope["gaps"].append({"type": "config", "reason": "--op required for perplexity"})
        elif not args.queries:
            envelope["gaps"].append({"type": "config", "reason": "--query required"})
        elif args.input_file:
            try:
                is_chat = PPLX_OP_MODEL.get(args.op) is not None
                raw_items, answer_text, citations_list = _load_pplx_input(
                    args.input_file, is_chat
                )
            except Exception as exc:
                envelope["gaps"].append({
                    "type": "input_error",
                    "reason": f"Failed to load input file: {exc}",
                })
        else:
            _load_env()
            api_key = os.getenv("PERPLEXITY_API_KEY")
            if not api_key:
                envelope["gaps"].append({
                    "type": "config", "reason": "PERPLEXITY_API_KEY not set",
                })
            else:
                model = PPLX_OP_MODEL[args.op]
                try:
                    if model is None:
                        raw_items = _fetch_pplx_search(api_key, args)
                    else:
                        raw_items, answer_text, citations_list = _fetch_pplx_chat(
                            api_key, args, model
                        )
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    envelope["gaps"].append({
                        "type": "upstream_error",
                        "reason": f"Perplexity API failed: {exc}",
                    })
                except Exception as exc:
                    envelope["gaps"].append({
                        "type": "internal_error",
                        "reason": f"Unexpected: {exc}",
                    })
    else:
        # Existing BZ path
        if args.input_file:
            try:
                raw_items = _load_input_items(args.input_file)
            except Exception as exc:
                envelope["gaps"].append({
                    "type": "input_error",
                    "reason": f"Failed to load input file: {exc}",
                })
        else:
            _load_env()
            api_key = os.getenv("BENZINGANEWS_API_KEY") or os.getenv("BENZINGA_API_KEY")
            if not api_key:
                envelope["gaps"].append({
                    "type": "config",
                    "reason": "BENZINGANEWS_API_KEY is not set",
                })
            else:
                try:
                    raw_items = _fetch_bz_items(api_key, args)
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    envelope["gaps"].append({
                        "type": "upstream_error",
                        "reason": f"Benzinga API request failed: {exc}",
                    })
                except Exception as exc:
                    envelope["gaps"].append({
                        "type": "internal_error",
                        "reason": f"Unexpected wrapper error: {exc}",
                    })

    # ── Normalize + filter ──
    invalid_created = 0
    pit_excluded = 0

    if is_pplx:
        seen_urls: set[str] = set()
        pit_date_str = pit_dt.astimezone(NY_TZ).strftime("%Y-%m-%d") if pit_dt else None

        for raw in raw_items:
            item, pub_dt, err = _normalize_pplx_result(raw)
            if err:
                invalid_created += 1
                continue
            if item is None or pub_dt is None:
                invalid_created += 1
                continue

            # Two-tier PIT filtering:
            #   Full timestamp (ISO8601 with time+tz): exact comparison
            #   Date-only (YYYY-MM-DD): exclude PIT day entirely
            if pit_dt is not None:
                date_raw_str = (item.get("date") or "").strip()
                if len(date_raw_str) == 10:  # date-only YYYY-MM-DD
                    if date_raw_str >= pit_date_str:
                        pit_excluded += 1
                        continue
                else:  # full timestamp
                    if pub_dt > pit_dt:
                        pit_excluded += 1
                        continue

            # Dedup by URL
            url = item.get("url") or ""
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            envelope["data"].append(item)
            if len(envelope["data"]) >= args.limit:
                break

        # Synthesis item for chat ops (open mode only, appended separately from --limit)
        if args.op and args.op != "search" and answer_text:
            if pit_dt is None:
                synthesis_item = {
                    "record_type": "synthesis",
                    "answer": answer_text,
                    "citations": citations_list,
                    "available_at": _to_new_york_iso(datetime.now(timezone.utc)),
                    "available_at_source": "provider_metadata",
                }
                envelope["data"].append(synthesis_item)
            # PIT mode: synthesis excluded (available_at = now > PIT)
    else:
        seen_ids: set[str] = set()

        for raw in raw_items:
            item, created_dt, err = _normalize_bz_item(raw)
            if err:
                invalid_created += 1
                continue
            if item is None or created_dt is None:
                invalid_created += 1
                continue

            if pit_dt is not None and created_dt > pit_dt:
                pit_excluded += 1
                continue

            if not _matches_filters(
                item, requested_tickers, requested_channels, requested_tags, requested_keywords
            ):
                continue

            key = f"{item.get('id')}::{item.get('available_at')}"
            if key in seen_ids:
                continue
            seen_ids.add(key)
            envelope["data"].append(item)
            if len(envelope["data"]) >= args.limit:
                break

    if invalid_created:
        envelope["gaps"].append({
            "type": "unverifiable",
            "reason": (
                f"Dropped {invalid_created} item(s) with missing/unparseable "
                f"{'date' if is_pplx else 'created'} timestamp"
            ),
        })
    if pit_excluded:
        envelope["gaps"].append({
            "type": "pit_excluded",
            "reason": f"Dropped {pit_excluded} item(s) published after PIT cutoff",
        })
    if not envelope["data"]:
        envelope["gaps"].append({
            "type": "no_data",
            "reason": "No items matched the query and PIT constraints",
        })

    # Debug metadata -> stderr (not consumed by agents or pit_gate.py)
    if is_pplx:
        meta: dict[str, Any] = {
            "source": "perplexity",
            "op": args.op,
            "mode": "pit" if args.pit else "open",
            "pit": args.pit,
            "model": PPLX_OP_MODEL.get(args.op) if args.op else None,
            "queries": args.queries,
            "search_mode": args.search_mode,
        }
    else:
        meta = {
            "source": "bz-news-api",
            "mode": "pit" if args.pit else "open",
            "pit": args.pit,
            "coverage": {
                "date_from": args.date_from,
                "date_to": args.date_to,
                "updated_since": args.updated_since,
            },
            "query": {
                "tickers": args.tickers,
                "channels": sorted(requested_channels),
                "tags": sorted(requested_tags),
                "keywords": requested_keywords,
                "themes": requested_themes,
                "limit": args.limit,
            },
        }
    print(json.dumps(meta), file=sys.stderr)

    # Contract output -> stdout (data + gaps only, per DataSubAgents section 4.7)
    print(json.dumps(envelope))


if __name__ == "__main__":
    main()
