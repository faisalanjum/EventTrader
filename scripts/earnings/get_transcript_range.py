#!/usr/bin/env python3
"""Get unique transcripts for a ticker in date range (exclusive).

Wrapper that combines PR and QA results, deduplicates by transcript_id,
and fetches fiscal quarter/year info.
"""
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

SCRIPTS_DIR = Path(__file__).parent

# Get fiscal info for transcript IDs
FISCAL_QUERY = """
MATCH (t:Transcript)
WHERE t.id IN $transcript_ids
RETURN t.id AS id, t.fiscal_quarter AS fiscal_quarter, t.fiscal_year AS fiscal_year
"""

def run_script(script_name: str, ticker: str, start: str, end: str) -> set:
    """Run a script and extract transcript_ids from output."""
    result = subprocess.run(
        ["python", str(SCRIPTS_DIR / script_name), ticker, start, end],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent.parent)
    )
    transcript_ids = set()
    for line in result.stdout.strip().split('\n'):
        if line.startswith('OK|') or line.startswith('ERROR|') or '|' not in line:
            continue
        if line.startswith('transcript_id|'):  # header
            continue
        parts = line.split('|')
        if parts[0]:
            transcript_ids.add(parts[0])
    return transcript_ids

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_transcript_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]

    # Run both PR and QA scripts, combine transcript IDs
    pr_ids = run_script("get_transcript_pr_range.py", ticker, start, end)
    qa_ids = run_script("get_transcript_qa_range.py", ticker, start, end)
    all_ids = pr_ids | qa_ids  # union

    if not all_ids:
        print(ok("NO_TRANSCRIPTS", f"0 transcripts {ticker} {start}->{end}"))
        sys.exit(0)

    # Get fiscal info and dates for each transcript
    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            # Get full transcript info
            query = """
            MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
            WHERE t.id IN $ids
            RETURN t.id AS id, left(t.conference_datetime, 10) AS date,
                   t.fiscal_quarter AS fiscal_quarter, t.fiscal_year AS fiscal_year
            ORDER BY t.conference_datetime
            """
            rows = []
            for r in s.run(query, ticker=ticker.upper(), ids=list(all_ids)):
                fq = r['fiscal_quarter'] or ''
                fy = r['fiscal_year'] or ''
                rows.append(f"{r['id']}|{r['date']}|{fq}|{fy}")
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)

    print("id|date|fiscal_quarter|fiscal_year")
    print("\n".join(rows))
