#!/usr/bin/env python3
"""
Fetch Claude Max / Pro plan usage from the OAuth usage endpoint.

Outputs:
  - raw JSON   (~/.cache/claude-usage/claude_usage_raw.json)
  - summary    (~/.cache/claude-usage/claude_usage_summary.json)

Usage:
  python3 scripts/claude_usage_fetch.py
  python3 scripts/claude_usage_fetch.py --no-cache
  python3 scripts/claude_usage_fetch.py --json
  python3 scripts/claude_usage_fetch.py --out-dir /tmp/claude-usage

Rate limits:
  The OAuth endpoint is aggressively rate-limited (~5 calls before 429
  that persists for hours). The script caches for 5 minutes by default.
  Use --no-cache sparingly. On 429, stale cached data (up to 24h) is shown.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
BETA_HEADER = "oauth-2025-04-20"
DEFAULT_TZ = "America/Toronto"
CACHE_TTL_SECONDS = 300  # 5 minutes — avoid 429s


@dataclass
class Bucket:
    name: str
    percent: float | None
    resets_at_utc: str | None
    resets_at_local: str | None


@dataclass
class Summary:
    fetched_at_utc: str
    fetched_at_local: str
    cached: bool
    source: str
    five_hour: Bucket
    seven_day: Bucket
    seven_day_sonnet: Bucket
    seven_day_opus: Bucket
    extra_usage_enabled: bool | None
    extra_usage_used_credits: float | None
    extra_usage_monthly_limit: float | None


def now_utc() -> datetime:
    return datetime.now(tz=ZoneInfo("UTC"))


def to_local(utc_str: str | None, tz_name: str) -> str | None:
    if not utc_str:
        return None
    s = utc_str.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %I:%M %p %Z")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Claude Max plan usage")
    p.add_argument("--out-dir", default=str(Path.home() / ".cache" / "claude-usage"))
    p.add_argument("--timezone", default=DEFAULT_TZ)
    p.add_argument("--no-cache", action="store_true", help="Bypass cache and force fresh fetch")
    p.add_argument("--json", action="store_true", help="Output summary as JSON to stdout")
    return p.parse_args()


def load_access_token() -> str:
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if not creds_path.exists():
        raise FileNotFoundError(f"Credentials not found: {creds_path}")
    data = json.loads(creds_path.read_text())
    token = (data.get("claudeAiOauth") or {}).get("accessToken", "")
    if not token:
        raise RuntimeError("No claudeAiOauth.accessToken in ~/.claude/.credentials.json")
    return token


def fetch_usage(token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        USAGE_URL,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "anthropic-beta": BETA_HEADER,
            "User-Agent": "claude-usage-fetch/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = e.headers.get("Retry-After", "unknown")
            raise RuntimeError(
                f"429 rate-limited (Retry-After: {retry_after}). "
                f"The OAuth usage endpoint is aggressively rate-limited. "
                f"Use --no-cache sparingly. Cached data may still be available."
            ) from e
        raise


def load_cache(cache_path: Path, ttl: int) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text())
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at < ttl:
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_cache(cache_path: Path, payload: dict[str, Any]) -> None:
    payload["_cached_at"] = time.time()
    cache_path.write_text(json.dumps(payload, indent=2) + "\n")


def make_bucket(name: str, payload: dict[str, Any], key: str, tz: str) -> Bucket:
    obj = payload.get(key)
    if obj is None:
        return Bucket(name=name, percent=None, resets_at_utc=None, resets_at_local=None)
    # The endpoint returns utilization as 0-100 (e.g. 37.0 = 37%)
    pct = obj.get("utilization")
    if pct is not None:
        pct = round(float(pct), 2)
    resets = obj.get("resets_at")
    return Bucket(name=name, percent=pct, resets_at_utc=resets, resets_at_local=to_local(resets, tz))


def build_summary(payload: dict[str, Any], tz: str, cached: bool) -> Summary:
    extra = payload.get("extra_usage") or {}
    ts = now_utc()
    return Summary(
        fetched_at_utc=ts.isoformat(),
        fetched_at_local=ts.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %I:%M %p %Z"),
        cached=cached,
        source=USAGE_URL,
        five_hour=make_bucket("5-hour", payload, "five_hour", tz),
        seven_day=make_bucket("7-day (all)", payload, "seven_day", tz),
        seven_day_sonnet=make_bucket("7-day (Sonnet)", payload, "seven_day_sonnet", tz),
        seven_day_opus=make_bucket("7-day (Opus)", payload, "seven_day_opus", tz),
        extra_usage_enabled=extra.get("is_enabled", extra.get("enabled")),
        extra_usage_used_credits=extra.get("used_credits", extra.get("amount_used")),
        extra_usage_monthly_limit=extra.get("monthly_limit", extra.get("amount_limit")),
    )


def print_table(summary: Summary) -> None:
    buckets = [summary.five_hour, summary.seven_day, summary.seven_day_sonnet, summary.seven_day_opus]
    print(f"\n{'Bucket':<18} {'Used':>8}   {'Resets (local)'}")
    print("-" * 65)
    for b in buckets:
        pct = "n/a" if b.percent is None else f"{b.percent:.1f}%"
        reset = b.resets_at_local or "n/a"
        print(f"{b.name:<18} {pct:>8}   {reset}")

    if summary.extra_usage_enabled is not None:
        status = "enabled" if summary.extra_usage_enabled else "disabled"
        print(f"\nExtra usage: {status}", end="")
        if summary.extra_usage_used_credits is not None:
            print(f"  (used: ${summary.extra_usage_used_credits}, limit: ${summary.extra_usage_monthly_limit})", end="")
        print()

    if summary.cached:
        print(f"\n(cached result — use --no-cache to force refresh)")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / "claude_usage_raw.json"
    summary_path = out_dir / "claude_usage_summary.json"
    cache_path = out_dir / "claude_usage_cache.json"

    try:
        # Try cache first
        cached = False
        if not args.no_cache:
            payload = load_cache(cache_path, CACHE_TTL_SECONDS)
            if payload:
                cached = True

        if not cached:
            token = load_access_token()
            payload = fetch_usage(token)
            save_cache(cache_path, payload)

        # Strip internal cache key before saving raw
        raw_payload = {k: v for k, v in payload.items() if k != "_cached_at"}

        summary = build_summary(raw_payload, args.timezone, cached)

        # Write files
        raw_path.write_text(json.dumps(raw_payload, indent=2) + "\n")
        summary_path.write_text(json.dumps(asdict(summary), indent=2) + "\n")

        if args.json:
            print(json.dumps(asdict(summary), indent=2))
        else:
            print_table(summary)

        return 0

    except Exception as e:
        # On error, try to show cached data if available
        stale = load_cache(cache_path, ttl=86400)  # accept up to 24h stale on error
        if stale:
            raw_payload = {k: v for k, v in stale.items() if k != "_cached_at"}
            summary = build_summary(raw_payload, args.timezone, cached=True)
            print(f"ERROR: {e}\n\nShowing last cached result:", file=sys.stderr)
            print_table(summary)
            return 1
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
