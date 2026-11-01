#!/usr/bin/env python3
"""Pull census substrate from Neo4j (READ-ONLY) → local JSON cache.

Test bed = 8,432 GuidanceUpdate nodes (stand-in DriverUpdate inputs).
Answer key = each company's reported top-level XBRL Facts (value+period+concept).

We cache so the labeler/matchers iterate without re-hitting Neo4j.
Run from repo root:  venv/bin/python plans/Drivers/WIP/concept_link_probe/pull_data.py
ponytail: one-shot pull, overwrite cache; no incremental logic until a re-pull is slow.
"""
import json, os, sys, pathlib
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.getcwd())
from neograph.Neo4jConnection import get_manager

OUT = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
OUT.mkdir(parents=True, exist_ok=True)

GUIDANCE_Q = """
MATCH (g:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company)
OPTIONAL MATCH (g)-[:HAS_PERIOD]->(p:GuidancePeriod)
RETURN g.id AS id, g.label AS label, g.label_slug AS slug,
       g.low AS low, g.mid AS mid, g.high AS high,
       g.canonical_unit AS unit, g.segment AS segment,
       g.xbrl_qname AS existing_qname, g.concept_family_qname AS family,
       c.ticker AS ticker, c.cik AS cik,
       p.start_date AS pstart, p.end_date AS pend
"""

# Per-company top-level (no segment member) numeric facts, all periods.
# Same join discipline as production QUERY_2A but without the "since last 10-K"
# window (older guidance references older periods).
FACTS_Q = """
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker:$t})
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q'] AND f.is_numeric='1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids=[])
RETURN DISTINCT con.qname AS qname, con.label AS label,
       f.value AS value, f.period_ref AS period_ref, f.unit_ref AS unit_ref
"""

def main():
    m = get_manager()
    try:
        g = m.execute_cypher_query_all(GUIDANCE_Q, {})
        (OUT / "guidance.json").write_text(json.dumps(g))
        tickers = sorted({r["ticker"] for r in g if r["ticker"]})
        print(f"guidance: {len(g)} rows, {len(tickers)} companies")
        facts = {}
        for t in tickers:
            rows = m.execute_cypher_query_all(FACTS_Q, {"t": t})
            facts[t] = rows
            print(f"  facts {t}: {len(rows)}")
        (OUT / "facts.json").write_text(json.dumps(facts))
        tot = sum(len(v) for v in facts.values())
        print(f"facts total: {tot} rows across {len(facts)} companies → {OUT}")
    finally:
        m.close()

if __name__ == "__main__":
    main()
