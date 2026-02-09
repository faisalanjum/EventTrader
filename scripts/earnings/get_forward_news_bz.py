#!/usr/bin/env python3
"""Get Benzinga forward-looking news for a ticker based on guidance keywords."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

KEYWORDS_FILE = Path(__file__).parent / "operational_guidance_keywords.json"

NEWS_QUERY = """
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE date(datetime(n.created)) > date($start) AND date(datetime(n.created)) < date($end)
  AND (any(kw IN $keywords WHERE toLower(n.title) CONTAINS toLower(kw))
       OR any(kw IN $keywords WHERE toLower(n.body) CONTAINS toLower(kw))
       OR any(kw IN $keywords WHERE toLower(n.teaser) CONTAINS toLower(kw)))
  AND NOT (n.channels CONTAINS 'Analyst Ratings' OR n.channels CONTAINS 'Price Target'
       OR n.channels CONTAINS 'Upgrades' OR n.channels CONTAINS 'Downgrades'
       OR n.channels CONTAINS 'Initiation' OR n.channels CONTAINS 'Reiteration')
RETURN n.id AS id, left(n.created, 10) AS date, n.title AS title
ORDER BY n.created
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_forward_news_bz.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]

    with open(KEYWORDS_FILE) as f:
        config = json.load(f)

    # Combine all forward-looking keywords
    fwd = config['forward_looking_keywords']
    keywords = fwd['directional'] + fwd['guidance_actions'] + fwd['timeframes']

    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            rows = [f"{r['id']}|{r['date']}|{r['title']}" for r in s.run(NEWS_QUERY, ticker=ticker.upper(), start=start, end=end, keywords=keywords)]
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)

    print(f"# keywords={len(keywords)}")
    print("id|date|title\n" + "\n".join(rows) if rows else ok("NO_FWD_NEWS", f"0 forward-looking news {ticker} {start}->{end}"))
