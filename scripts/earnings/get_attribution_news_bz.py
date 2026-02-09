#!/usr/bin/env python3
"""Fetch Benzinga news with attribution-relevant channels for a ticker in date range.

Usage: get_attribution_news_bz.py TICKER START END [--channels CHANNEL1,CHANNEL2,...]

Channels are grouped into categories:
  earnings:   Earnings, Earnings Beats, Earnings Misses, Guidance
  analyst:    Analyst Ratings, Price Target, Upgrades, Downgrades, Initiation, Reiteration, Analyst Color
  corporate:  M&A, Dividends, Buybacks, Offerings, Stock Split, IPOs
  legal:      FDA, Legal, SEC, Regulations
  notable:    Management, Contracts, Insider Trades, Rumors

Default: All categories. Use --channels to filter, e.g. --channels earnings,analyst
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

# Channel categories for earnings attribution
CHANNEL_GROUPS = {
    "earnings": ["Earnings", "Earnings Beats", "Earnings Misses", "Guidance"],
    "analyst": ["Analyst Ratings", "Price Target", "Upgrades", "Downgrades",
                "Initiation", "Reiteration", "Analyst Color"],
    "corporate": ["M&A", "Dividends", "Buybacks", "Offerings", "Stock Split", "IPOs"],
    "legal": ["FDA", "Legal", "SEC", "Regulations"],
    "notable": ["Management", "Contracts", "Insider Trades", "Rumors"],
}

ALL_CHANNELS = [ch for group in CHANNEL_GROUPS.values() for ch in group]

QUERY = """
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE date(datetime(n.created)) > date($start) AND date(datetime(n.created)) < date($end)
  AND any(ch IN n.channels WHERE ch IN $channels)
  AND r.daily_stock IS NOT NULL
RETURN n.id AS id,
       left(n.created, 10) AS date,
       n.title AS title,
       [ch IN n.channels WHERE ch IN $channels] AS matched_channels,
       r.daily_stock AS daily_return
ORDER BY n.created
"""

def parse_channels(channel_arg: str) -> list:
    """Parse channel argument: can be group names or individual channels."""
    channels = set()
    for item in channel_arg.split(","):
        item = item.strip().lower()
        if item in CHANNEL_GROUPS:
            channels.update(CHANNEL_GROUPS[item])
        else:
            # Try to match individual channel (case-insensitive)
            for ch in ALL_CHANNELS:
                if ch.lower() == item:
                    channels.add(ch)
                    break
    return list(channels) if channels else ALL_CHANNELS

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_attribution_news_bz.py TICKER START END [--channels GROUPS]"))
        print("\nGroups: earnings, analyst, corporate, legal, notable")
        print("Example: get_attribution_news_bz.py AAPL 2024-01-01 2024-02-01 --channels earnings,analyst")
        sys.exit(1)

    ticker, start, end = sys.argv[1:4]

    # Parse optional --channels argument
    channels = ALL_CHANNELS
    if len(sys.argv) > 4 and sys.argv[4] == "--channels" and len(sys.argv) > 5:
        channels = parse_channels(sys.argv[5])

    with neo4j_session() as (s, e):
        if e:
            print(e)
            sys.exit(1)
        try:
            results = list(s.run(QUERY, ticker=ticker.upper(), start=start, end=end, channels=channels))
        except Exception as ex:
            print(parse_exception(ex))
            sys.exit(1)

    if not results:
        print(ok("NO_NEWS", f"0 attribution news {ticker} {start}->{end}"))
    else:
        # Output format: pipe-delimited for easy parsing
        print("id|date|channels|return|title")
        for r in results:
            chs = ",".join(r["matched_channels"]) if r["matched_channels"] else ""
            ret = f"{r['daily_return']:.2f}%" if r["daily_return"] else "N/A"
            title = (r["title"] or "")[:80].replace("|", "-")  # Truncate and escape
            print(f"{r['id']}|{r['date']}|{chs}|{ret}|{title}")
