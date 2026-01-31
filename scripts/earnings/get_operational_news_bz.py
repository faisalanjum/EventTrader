#!/usr/bin/env python3
"""Get Benzinga operational news for a ticker based on its industry/sector keywords."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

KEYWORDS_FILE = Path(__file__).parent / "operational_guidance_keywords.json"

COMPANY_QUERY = "MATCH (c:Company {ticker: $ticker}) RETURN c.industry AS industry, c.sector AS sector"

NEWS_QUERY = """
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE date(datetime(n.created)) > date($start) AND date(datetime(n.created)) < date($end)
  AND (any(kw IN $keywords WHERE toLower(n.title) CONTAINS toLower(kw))
       OR any(kw IN $keywords WHERE toLower(n.body) CONTAINS toLower(kw))
       OR any(kw IN $keywords WHERE toLower(n.teaser) CONTAINS toLower(kw)))
RETURN n.id AS id, left(n.created, 10) AS date, n.title AS title
ORDER BY n.created
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_operational_news_bz.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]

    with open(KEYWORDS_FILE) as f:
        config = json.load(f)

    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            # Get industry and sector
            r = s.run(COMPANY_QUERY, ticker=ticker.upper()).single()
            if not r:
                print(error("NO_COMPANY", f"Company not found for {ticker}")); sys.exit(1)
            industry, sector = r['industry'], r['sector']

            # Try industry keywords first, fallback to sector
            source = None
            if industry and industry in config['industries']:
                keywords = config['industries'][industry]['operational_keywords']
                source = f"industry={industry}"
            elif sector and sector in config['sectors']:
                keywords = config['sectors'][sector]['fallback_keywords']
                source = f"sector={sector} (fallback)"
            else:
                print(error("NO_KEYWORDS", f"No keywords for industry '{industry}' or sector '{sector}'")); sys.exit(1)

            # Search news
            rows = [f"{r['id']}|{r['date']}|{r['title']}" for r in s.run(NEWS_QUERY, ticker=ticker.upper(), start=start, end=end, keywords=keywords)]
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)

    print(f"# {source} keywords={len(keywords)}")
    print("id|date|title\n" + "\n".join(rows) if rows else ok("NO_OPS_NEWS", f"0 operational news {ticker} {start}->{end}"))
