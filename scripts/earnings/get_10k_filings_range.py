#!/usr/bin/env python3
"""Get 10-K content sources for a ticker in date range [start, end).

Returns one line per content source:
- exhibit: Press releases, agreements (EX-99.1, EX-10.x)
- section: MD&A, Risk Factors, Business, etc.
- filing_text: Raw filing text (rare)
- financial_stmt: Structured financial statements (BalanceSheets, StatementsOfIncome, etc.)
- xbrl: XBRL data available flag (query for specific facts)

Each line can be processed by a separate guidance extraction agent.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

QUERY = """
MATCH (r:Report {formType: '10-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE datetime(r.created) >= datetime($start) AND datetime(r.created) < datetime($end)
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(f:FilingTextContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)
WITH r,
     collect(DISTINCT {type: 'exhibit', key: e.exhibit_number}) as exhibits,
     collect(DISTINCT {type: 'section', key: s.section_name}) as sections,
     collect(DISTINCT {type: 'filing_text', key: f.id}) as filing_texts,
     collect(DISTINCT {type: 'financial_stmt', key: fs.statement_type}) as financial_stmts,
     CASE WHEN x IS NOT NULL THEN [{type: 'xbrl', key: 'available'}] ELSE [] END as xbrl
RETURN r.accessionNo AS report_id,
       left(r.created, 10) AS date,
       exhibits + sections + filing_texts + financial_stmts + xbrl AS sources
ORDER BY r.created
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_10k_filings_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]
    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            rows = []
            for r in s.run(QUERY, ticker=ticker.upper(), start=start, end=end):
                report_id = r['report_id']
                date = r['date']
                for source in r['sources']:
                    if source['key']:  # skip nulls from OPTIONAL MATCH
                        rows.append(f"{report_id}|{date}|{source['type']}|{source['key']}")
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)
    print("report_id|date|source_type|source_key\n" + "\n".join(rows) if rows else ok("NO_10K_CONTENT", f"0 10-K content sources {ticker} {start}->{end}"))
