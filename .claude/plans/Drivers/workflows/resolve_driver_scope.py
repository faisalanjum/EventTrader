#!/usr/bin/env python3
"""
Driver-scope resolver — Neo4j lookup for the driver-catalog pipeline (read-only).

  --industry "Restaurants"      -> { scope_type:"industry", scope_name, slug, tickers[], n_tickers }
  --sector  "ConsumerCyclical"  -> { scope_type:"sector",   scope_name, industries[], n_industries }
  --list                        -> { sectors:[...], industries:[...] }   (so a name can't be typo'd)

Guards: HARD-ERROR (exit 1) if a scope resolves to 0 results (hint: run --list).
        WARN (stderr) if an industry has only 1 ticker (convergence cannot be measured).
Prints the result JSON to stdout. Uses the graph's REAL sector/industry strings (e.g. "ConsumerCyclical").
"""
import os, sys, json, re, argparse
from pathlib import Path

ROOT = Path("/home/faisal/EventMarketDB")
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)
from neo4j import GraphDatabase

URI  = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PW   = os.getenv("NEO4J_PASSWORD")

def slugify(s):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", (s or "").lower())).strip("_")

def main():
    ap = argparse.ArgumentParser(description="Resolve a driver-catalog scope from Neo4j.")
    ap.add_argument("--industry", help="industry name -> its tickers")
    ap.add_argument("--sector",   help="sector name -> its industries")
    ap.add_argument("--list", action="store_true", help="list valid sectors + industries")
    ap.add_argument("--out", help="ALSO write the result JSON to this path (Stage-0 #8: "
                                  "code-to-code scope file for fetch_company_sources.py --scope)")
    ap.add_argument("--exclude", default=None,
                    help="comma-separated tickers to DROP from a resolved industry scope "
                         "(O7/O8 F-C roster pin, e.g. BLMN,SHAK,WING,CBRL,EAT,PZZA)")
    a = ap.parse_args()
    if not PW:
        print("ERROR: NEO4J_PASSWORD not set (.env)", file=sys.stderr); sys.exit(1)

    drv = GraphDatabase.driver(URI, auth=(USER, PW))
    try:
        with drv.session() as s:
            if a.list:
                secs = [r["x"] for r in s.run("MATCH (c:Company) WHERE c.sector IS NOT NULL RETURN DISTINCT c.sector AS x ORDER BY x")]
                inds = [r["x"] for r in s.run("MATCH (c:Company) WHERE c.industry IS NOT NULL RETURN DISTINCT c.industry AS x ORDER BY x")]
                print(json.dumps({"sectors": secs, "industries": inds}, indent=1)); return

            if a.industry:
                tickers = [r["t"] for r in s.run(
                    "MATCH (c:Company {industry:$ind}) WHERE c.ticker IS NOT NULL AND trim(c.ticker) <> '' "
                    "RETURN DISTINCT c.ticker AS t ORDER BY t", ind=a.industry)]
                if a.exclude:
                    drop = {t.strip().upper() for t in a.exclude.split(",") if t.strip()}
                    tickers = [t for t in tickers if t.upper() not in drop]
                if not tickers:
                    print(f"ERROR: industry '{a.industry}' resolved 0 tickers (run --list for valid names)", file=sys.stderr); sys.exit(1)
                if len(tickers) == 1:
                    print(f"WARN: industry '{a.industry}' has only 1 ticker — convergence cannot be measured", file=sys.stderr)
                payload = {"scope_type": "industry", "scope_name": a.industry, "slug": slugify(a.industry),
                           "tickers": tickers, "n_tickers": len(tickers)}
                print(json.dumps(payload))
                if a.out:
                    Path(a.out).write_text(json.dumps(payload) + "\n")
                return

            if a.sector:
                inds = [r["x"] for r in s.run(
                    "MATCH (c:Company {sector:$sec}) WHERE c.industry IS NOT NULL RETURN DISTINCT c.industry AS x ORDER BY x", sec=a.sector)]
                if not inds:
                    print(f"ERROR: sector '{a.sector}' resolved 0 industries (run --list for valid names)", file=sys.stderr); sys.exit(1)
                print(json.dumps({"scope_type": "sector", "scope_name": a.sector, "industries": inds, "n_industries": len(inds)})); return

            print("ERROR: pass --industry NAME, --sector NAME, or --list", file=sys.stderr); sys.exit(1)
    finally:
        drv.close()

if __name__ == "__main__":
    main()
