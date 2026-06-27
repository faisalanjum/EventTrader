#!/usr/bin/env python3
"""Pull the FULL company universe (read-only) for re-validation:
per-company concept MENU (faithful QUERY_2A) + structural attributes (balance / item-type /
period-type) which are INDEPENDENT non-LLM signals for ground truth (e.g. revenue is a credit,
cost-of-revenue a debit → catches token-inversion links).

Writes scratchpad/clrv/menus/{ticker}.json and company_meta.json.
"""
import os, json, pathlib, sys
from dotenv import load_dotenv; load_dotenv()
sys.path.insert(0, os.getcwd())
from neograph.Neo4jConnection import get_manager

OUT = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")
(OUT / "menus").mkdir(parents=True, exist_ok=True)

# faithful QUERY_2A menu + concept structural attrs
MENU_Q = """
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$t})
WHERE rk.formType='10-K' WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last10k
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q'] AND r.created>=last10k AND f.is_numeric='1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids=[])
WITH con.qname AS qname, con.label AS label, con.balance AS balance,
     con.type_local AS type_local, con.period_type AS period_type, count(f) AS usage
RETURN qname, label, balance, type_local, period_type, usage ORDER BY usage DESC
"""

META_Q = """
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company) WHERE rk.formType IN ['10-K','10-Q']
WITH DISTINCT c
OPTIONAL MATCH (c)<-[:FOR_COMPANY]-(g:GuidanceUpdate)
RETURN c.ticker AS ticker, c.cik AS cik, c.sector AS sector, c.industry AS industry,
       c.mkt_cap AS mkt_cap, count(g) AS n_guidance
"""

def main():
    m = get_manager()
    try:
        meta = m.execute_cypher_query_all(META_Q, {})
        (OUT / "company_meta.json").write_text(json.dumps(meta))
        tickers = [r["ticker"] for r in meta if r["ticker"]]
        print(f"companies: {len(tickers)}", flush=True)
        done = 0
        for t in tickers:
            f = OUT / "menus" / f"{t}.json"
            if f.exists():
                done += 1; continue
            try:
                rows = m.execute_cypher_query_all(MENU_Q, {"t": t})
            except Exception as e:
                print(f"  ERR {t}: {e}", flush=True); rows = []
            f.write_text(json.dumps(rows))
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(tickers)} menus", flush=True)
        sizes = [len(json.loads((OUT / "menus" / f"{t}.json").read_text())) for t in tickers]
        nonempty = sum(1 for s in sizes if s > 0)
        print(f"DONE: {done} menus, {nonempty} non-empty, "
              f"median size {sorted(sizes)[len(sizes)//2]}", flush=True)
    finally:
        m.close()

if __name__ == "__main__":
    main()
