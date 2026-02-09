#!/usr/bin/env python3
"""Get transcript Prepared Remarks for a ticker in date range [start, end)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

QUERY = """
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(t.conference_datetime) >= datetime($start) AND datetime(t.conference_datetime) < datetime($end)
MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
RETURN t.id AS transcript_id, left(t.conference_datetime, 10) AS date, pr.id AS pr_id
ORDER BY t.conference_datetime
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_transcript_pr_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]
    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            rows = [f"{r['transcript_id']}|{r['date']}|{r['pr_id']}" for r in s.run(QUERY, ticker=ticker.upper(), start=start, end=end)]
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)
    print("transcript_id|date|pr_id\n" + "\n".join(rows) if rows else ok("NO_PR", f"0 prepared remarks {ticker} {start}->{end}"))
