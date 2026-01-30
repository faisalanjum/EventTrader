#!/usr/bin/env python3
"""
Find similar news with impact data for driver validation.

Usage:
    python find_similar_news.py TICKER NEWS_ID [DRIVER_TEXT]

    TICKER: Company ticker (e.g., AAPL)
    NEWS_ID: bzNews_123 (Benzinga) OR URL OR "N/A"
    DRIVER_TEXT: Required if NEWS_ID is URL or N/A (for embedding generation)

Output:
    OK|SAME_TICKER|count
    news_id|similarity|date|daily_stock|direction
    ...
    OK|SECTOR|count
    news_id|similarity|ticker|date|daily_stock|direction
    ...

    OR on error:
    ERROR|CODE|message|hint
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error
load_env()

import os
from openai import OpenAI

# Constants
MIN_SIMILARITY = 0.75
SAME_TICKER_LIMIT = 15
SECTOR_LIMIT = 10


def get_embedding_from_neo4j(session, news_id: str) -> list | None:
    """Get embedding for a Benzinga news item."""
    query = "MATCH (n:News {id: $news_id}) RETURN n.embedding as embedding"
    result = session.run(query, news_id=news_id).single()
    return result["embedding"] if result and result["embedding"] else None


def generate_embedding(text: str) -> list:
    """Generate embedding using OpenAI text-embedding-3-large."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text,
        dimensions=3072
    )
    return response.data[0].embedding


def get_company_sector(session, ticker: str) -> str | None:
    """Get sector for a company."""
    query = "MATCH (c:Company {ticker: $ticker}) RETURN c.sector as sector"
    result = session.run(query, ticker=ticker).single()
    return result["sector"] if result else None


def find_similar_same_ticker(session, embedding: list, ticker: str, exclude_id: str = None) -> list:
    """Find similar news for the same ticker with impact data."""
    query = """
    CALL db.index.vector.queryNodes('news_vector_index', 50, $embedding)
    YIELD node, score
    MATCH (node)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
    WHERE score >= $min_sim AND r.daily_stock IS NOT NULL
      AND ($exclude_id IS NULL OR node.id <> $exclude_id)
    RETURN node.id as news_id, score, substring(node.created, 0, 10) as date,
           r.daily_stock as daily_stock,
           CASE WHEN r.daily_stock >= 0 THEN 'up' ELSE 'down' END as direction
    ORDER BY score DESC LIMIT $limit
    """
    return [dict(r) for r in session.run(query, embedding=embedding, ticker=ticker,
                                          min_sim=MIN_SIMILARITY, exclude_id=exclude_id,
                                          limit=SAME_TICKER_LIMIT)]


def find_similar_sector(session, embedding: list, ticker: str, sector: str, exclude_id: str = None) -> list:
    """Find similar news for sector peers with impact data."""
    query = """
    CALL db.index.vector.queryNodes('news_vector_index', 50, $embedding)
    YIELD node, score
    MATCH (node)-[r:INFLUENCES]->(c:Company)
    WHERE score >= $min_sim AND r.daily_stock IS NOT NULL
      AND c.ticker <> $ticker AND c.sector = $sector
      AND ($exclude_id IS NULL OR node.id <> $exclude_id)
    RETURN node.id as news_id, score, c.ticker as peer_ticker,
           substring(node.created, 0, 10) as date, r.daily_stock as daily_stock,
           CASE WHEN r.daily_stock >= 0 THEN 'up' ELSE 'down' END as direction
    ORDER BY score DESC LIMIT $limit
    """
    return [dict(r) for r in session.run(query, embedding=embedding, ticker=ticker,
                                          sector=sector, min_sim=MIN_SIMILARITY,
                                          exclude_id=exclude_id, limit=SECTOR_LIMIT)]


def main():
    if len(sys.argv) < 3:
        print(error("USAGE", "find_similar_news.py TICKER NEWS_ID [DRIVER_TEXT]"))
        sys.exit(1)

    ticker = sys.argv[1].upper()
    news_id = sys.argv[2]
    driver_text = sys.argv[3] if len(sys.argv) > 3 else None

    with neo4j_session() as (session, err):
        if err:
            print(err)
            sys.exit(1)

        try:
            # Get embedding
            exclude_id = None
            if news_id.startswith("bzNews_"):
                embedding = get_embedding_from_neo4j(session, news_id)
                if not embedding:
                    print(error("NOT_FOUND", f"News {news_id} not found or has no embedding"))
                    sys.exit(1)
                exclude_id = news_id
            elif news_id == "N/A" or news_id.startswith("http"):
                if not driver_text:
                    print(error("MISSING_TEXT", "DRIVER_TEXT required for external news"))
                    sys.exit(1)
                embedding = generate_embedding(driver_text)
            else:
                print(error("INVALID_ID", f"Unrecognized news_id: {news_id}"))
                sys.exit(1)

            # Get sector
            sector = get_company_sector(session, ticker)
            if not sector:
                print(error("TICKER_NOT_FOUND", f"Company {ticker} not found"))
                sys.exit(1)

            # Same ticker results
            same = find_similar_same_ticker(session, embedding, ticker, exclude_id)
            print(f"OK|SAME_TICKER|{len(same)}")
            for r in same:
                print(f"{r['news_id']}|{r['score']:.3f}|{r['date']}|{r['daily_stock']:+.2f}|{r['direction']}")

            # Sector results
            sect = find_similar_sector(session, embedding, ticker, sector, exclude_id)
            print(f"OK|SECTOR|{len(sect)}")
            for r in sect:
                print(f"{r['news_id']}|{r['score']:.3f}|{r['peer_ticker']}|{r['date']}|{r['daily_stock']:+.2f}|{r['direction']}")

        except Exception as e:
            print(error("EXCEPTION", str(e)))
            sys.exit(1)


if __name__ == "__main__":
    main()
