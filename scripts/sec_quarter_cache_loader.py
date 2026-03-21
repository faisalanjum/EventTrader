#!/usr/bin/env python3
"""
SEC Quarter Cache Loader
========================
Bootstrap + refresh of SEC fiscal quarter dates in Redis.

Fetches exact fiscal quarter/annual dates from SEC EDGAR XBRL Company Concept API
and caches them in Redis for use by the guidance extraction pipeline.

Usage:
    python3 scripts/sec_quarter_cache_loader.py                   # all active tickers
    python3 scripts/sec_quarter_cache_loader.py --ticker FIVE     # single ticker

Redis keys written:
    fiscal_quarter:{TICKER}:{FY}:Q{N}          → {"start":"2024-02-04","end":"2024-05-04"}
    fiscal_quarter:{TICKER}:{FY}:FY            → {"start":"2024-02-04","end":"2025-02-01"}
    fiscal_quarter_length:{TICKER}:Q{N}         → 91  (median span, for Step C prediction)
    fiscal_year_end:{TICKER}                    → {"raw":"0201","month_adj":1}
    fiscal_quarter:{TICKER}:last_refreshed      → ISO timestamp (no TTL)

SEC rate limit: 10 req/sec. User-Agent header required.
"""
import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── Path + env setup ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import redis

log = logging.getLogger("sec_quarter_cache")

REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))

SEC_USER_AGENT = "EventMarketDB research@eventmarketdb.com"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# Rate limiting: SEC allows 10 req/sec — stay safely under
_last_request_time = 0.0


def _sec_get(url):
    """GET from SEC EDGAR with rate limiting and User-Agent."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 0.12:
        time.sleep(0.12 - elapsed)
    req = Request(url, headers={"User-Agent": SEC_USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            _last_request_time = time.time()
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            return None
        raise


def _get_ticker_cik_map():
    """Download SEC company_tickers.json → {TICKER: zero-padded CIK}."""
    data = _sec_get(SEC_COMPANY_TICKERS_URL)
    if not data:
        return {}
    result = {}
    for entry in data.values():
        ticker = entry.get("ticker", "").upper()
        cik = str(entry.get("cik_str", entry.get("cik", "")))
        if ticker and cik:
            result[ticker] = cik.zfill(10)
    return result


def _get_cik_from_neo4j(ticker):
    """Fallback: query Company.cik from Neo4j."""
    try:
        from neograph.Neo4jConnection import get_manager
        mgr = get_manager()
        result = mgr.execute_cypher_query_all(
            "MATCH (c:Company {ticker: $ticker}) RETURN c.cik AS cik",
            {"ticker": ticker},
        )
        if result and result[0].get("cik"):
            return str(result[0]["cik"]).zfill(10)
    except Exception as e:
        log.debug(f"Neo4j CIK lookup failed for {ticker}: {e}")
    return None


def _parse_concept_units(data):
    """Extract quarterly and annual periods from XBRL concept response.

    Returns list of dicts: {fy, fp, start, end, filed, span}.
    """
    if not data or "units" not in data:
        return []
    periods = []
    # EPS uses USD/shares, NetIncomeLoss uses USD
    for unit_key in data["units"]:
        for entry in data["units"][unit_key]:
            fp = entry.get("fp", "")
            fy = entry.get("fy")
            start = entry.get("start")
            end = entry.get("end")
            filed = entry.get("filed")
            form = entry.get("form", "")
            if not all([fp, fy, start, end, filed]):
                continue
            if form not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue
            try:
                span = (date.fromisoformat(end) - date.fromisoformat(start)).days
            except ValueError:
                continue
            periods.append({
                "fy": int(fy), "fp": fp, "start": start,
                "end": end, "filed": filed, "span": span,
            })
    return periods


def _filter_and_dedupe(periods):
    """Filter quarterly (Q1-Q3, 60-130d) and annual (FY, 300-400d).

    Deduplicates by (fy, fp): keep latest filed date (handles amendments).
    Returns dict keyed by (fy, fp) → {"start": ..., "end": ...}.
    """
    filtered = []
    for p in periods:
        if p["fp"] in ("Q1", "Q2", "Q3") and 60 <= p["span"] <= 130:
            filtered.append(p)
        elif p["fp"] == "FY" and 300 <= p["span"] <= 400:
            filtered.append(p)

    result = {}
    for p in filtered:
        key = (p["fy"], p["fp"])
        if key not in result:
            result[key] = p
        else:
            existing = result[key]
            # Prefer latest end date (current year over comparative prior-year),
            # then latest filed date as tiebreaker (amendment over original).
            if (p["end"], p["filed"]) > (existing["end"], existing["filed"]):
                result[key] = p
    return {k: {"start": v["start"], "end": v["end"]} for k, v in result.items()}


def _derive_q4(periods):
    """Derive Q4: start = Q3.end + 1d, end = FY.end.

    SEC XBRL has no fp='Q4' — Q4 results are in the 10-K (fp='FY').
    """
    for fy in {fy for fy, _ in periods}:
        q3 = periods.get((fy, "Q3"))
        annual = periods.get((fy, "FY"))
        if q3 and annual and (fy, "Q4") not in periods:
            q4_start = (date.fromisoformat(q3["end"]) + timedelta(days=1)).isoformat()
            q4_end = annual["end"]
            q4_span = (date.fromisoformat(q4_end) - date.fromisoformat(q4_start)).days
            if 60 <= q4_span <= 130:
                periods[(fy, "Q4")] = {"start": q4_start, "end": q4_end}


def _compute_median_lengths(periods):
    """Compute median quarter length per Q{N} across all fiscal years.

    Length uses SEC inclusive convention: end - start + 1 (both days included).
    Returns {1: 91, 2: 91, 3: 91, 4: 92} (quarter number → median days).
    """
    lengths_by_q = defaultdict(list)
    for (fy, fp), dates in periods.items():
        if not fp.startswith("Q"):
            continue
        q_num = int(fp[1])
        try:
            length = (date.fromisoformat(dates["end"]) - date.fromisoformat(dates["start"])).days + 1
            if 60 <= length <= 140:
                lengths_by_q[q_num].append(length)
        except ValueError:
            continue
    return {q: int(median(lengths)) for q, lengths in lengths_by_q.items() if lengths}


def _apply_fye_adjustment(raw_fye):
    """Apply day<=5 adjustment for 52-week calendar companies.

    If DD <= 5, the fiscal year actually ends in the prior month.
    E.g., FYE "0201" (Feb 1) → month_adj=1 (January).
    """
    if not raw_fye or len(raw_fye) != 4:
        return None
    try:
        mm = int(raw_fye[:2])
        dd = int(raw_fye[2:])
    except ValueError:
        return None
    month_adj = (mm - 1 if mm > 1 else 12) if dd <= 5 else mm
    return {"raw": raw_fye, "month_adj": month_adj}


def refresh_ticker(redis_client, ticker, cik=None):
    """Refresh SEC quarter cache for a single ticker.

    Called by:
      - CLI bootstrap (all tickers, CIK pre-resolved)
      - Guidance trigger daemon (per-ticker, CIK resolved via Neo4j)
      - trigger-extract.py (per-ticker, CIK resolved via Neo4j)

    Args:
        redis_client: Redis client with decode_responses=True
        ticker: e.g., "FIVE"
        cik: optional pre-resolved 10-digit CIK string
    """
    if not cik:
        cik = _get_cik_from_neo4j(ticker)
    if not cik:
        log.warning(f"No CIK found for {ticker}, skipping")
        return

    # Fetch XBRL concept data (EPS first, then NetIncomeLoss fallback)
    concept_data = _sec_get(
        SEC_CONCEPT_URL.format(cik=cik, concept="EarningsPerShareBasic"))
    if not concept_data or "units" not in concept_data:
        concept_data = _sec_get(
            SEC_CONCEPT_URL.format(cik=cik, concept="NetIncomeLoss"))
    if not concept_data:
        log.warning(f"No XBRL concept data for {ticker} (CIK {cik})")
        return

    # Parse → filter → dedupe → derive Q4 → median lengths
    raw_periods = _parse_concept_units(concept_data)
    periods = _filter_and_dedupe(raw_periods)
    _derive_q4(periods)
    median_lengths = _compute_median_lengths(periods)

    # Fetch FYE from submissions endpoint
    fye_data = None
    submissions = _sec_get(SEC_SUBMISSIONS_URL.format(cik=cik))
    if submissions and "fiscalYearEnd" in submissions:
        fye_data = _apply_fye_adjustment(submissions["fiscalYearEnd"])

    # Write to Redis (pipelined)
    pipe = redis_client.pipeline()
    for (fy, fp), dates in periods.items():
        pipe.set(f"fiscal_quarter:{ticker}:{fy}:{fp}", json.dumps(dates))
    for q_num, length in median_lengths.items():
        pipe.set(f"fiscal_quarter_length:{ticker}:Q{q_num}", str(length))
    if fye_data:
        pipe.set(f"fiscal_year_end:{ticker}", json.dumps(fye_data))
    pipe.set(f"fiscal_quarter:{ticker}:last_refreshed", datetime.utcnow().isoformat())
    pipe.execute()

    log.info(f"  {ticker}: {len(periods)} periods, "
             f"{len(median_lengths)} median lengths"
             + (f", FYE={fye_data['raw']}" if fye_data else ""))


def main():
    parser = argparse.ArgumentParser(description="SEC Quarter Cache Loader")
    parser.add_argument("--ticker", help="Single ticker to refresh")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()

    if args.ticker:
        # Single ticker: resolve CIK via Neo4j (no full map download)
        refresh_ticker(r, args.ticker.upper())
        return

    # Full bootstrap: download CIK map, refresh all active tickers
    print("Downloading SEC company tickers map...", file=sys.stderr)
    cik_map = _get_ticker_cik_map()
    print(f"  {len(cik_map)} tickers in SEC map", file=sys.stderr)

    # Get active tickers from trade_ready:entries
    entries = r.hgetall("trade_ready:entries")
    tickers = sorted(entries.keys())
    if not tickers:
        print("No active tickers in trade_ready:entries", file=sys.stderr)
        sys.exit(1)

    # Check for tickers missing from SEC map → Neo4j fallback
    missing = [t for t in tickers if t not in cik_map]
    if missing:
        print(f"  {len(missing)} tickers missing from SEC map, trying Neo4j: "
              f"{missing[:10]}{'...' if len(missing) > 10 else ''}", file=sys.stderr)
        for t in missing:
            cik = _get_cik_from_neo4j(t)
            if cik:
                cik_map[t] = cik

    print(f"Refreshing {len(tickers)} tickers...", file=sys.stderr)
    success = 0
    failed = 0
    for i, ticker in enumerate(tickers):
        cik = cik_map.get(ticker)
        if not cik:
            print(f"  SKIP {ticker}: no CIK", file=sys.stderr)
            failed += 1
            continue
        try:
            refresh_ticker(r, ticker, cik=cik)
            success += 1
        except Exception as e:
            print(f"  FAIL {ticker}: {e}", file=sys.stderr)
            failed += 1
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(tickers)}", file=sys.stderr)

    print(f"\nDone: {success} success, {failed} failed "
          f"out of {len(tickers)} tickers", file=sys.stderr)


if __name__ == "__main__":
    main()
