#!/usr/bin/env python3
"""Get transcript content sources for a ticker in date range [start, end).

Returns one line per transcript with source_type='transcript' and source_key='full'.
Each transcript includes both prepared remarks (PR) and Q&A exchanges together
to preserve cross-referencing context for guidance extraction.

Output format matches other content-level scripts: report_id|date|source_type|source_key
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

# Find transcripts that have either PR or QA content
QUERY = """
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(t.conference_datetime) >= datetime($start)
  AND datetime(t.conference_datetime) < datetime($end)
  AND (EXISTS { (t)-[:HAS_PREPARED_REMARKS]->(:PreparedRemark) }
       OR EXISTS { (t)-[:HAS_QA_EXCHANGE]->(:QAExchange) })
RETURN t.id AS transcript_id,
       left(t.conference_datetime, 10) AS date
ORDER BY t.conference_datetime
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_transcript_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]

    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            rows = []
            for r in s.run(QUERY, ticker=ticker.upper(), start=start, end=end):
                # Output format: report_id|date|source_type|source_key
                # transcript_id serves as report_id, source_key='full' means PR + Q&A together
                rows.append(f"{r['transcript_id']}|{r['date']}|transcript|full")
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)

    print("report_id|date|source_type|source_key\n" + "\n".join(rows) if rows else ok("NO_TRANSCRIPTS", f"0 transcripts {ticker} {start}->{end}"))
