#!/usr/bin/env python3
"""
Find similar Q&A exchanges with impact data for driver validation.

Usage:
    python find_similar_qa.py TICKER QA_ID [DRIVER_TEXT]

    TICKER: Company ticker (e.g., AAPL)
    QA_ID: Existing QAExchange id OR URL OR "N/A"
    DRIVER_TEXT: Required if QA_ID is URL or N/A (for embedding generation)

Output:
    OK|SAME_TICKER|count
    qa_id|similarity|date|daily_stock|direction
    ...
    OK|SECTOR|count
    qa_id|similarity|ticker|date|daily_stock|direction
    ...

    OR on error:
    ERROR|CODE|message|hint
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openai import OpenAI
from scripts.earnings.utils import error, load_env, neo4j_session

load_env()

# Constants
MIN_SIMILARITY = 0.75
SAME_TICKER_LIMIT = 15
SECTOR_LIMIT = 10


def get_embedding_from_neo4j(session, qa_id: str) -> list | None:
    """Get embedding for a QAExchange node."""
    query = "MATCH (q:QAExchange {id: $qa_id}) RETURN q.embedding as embedding"
    result = session.run(query, qa_id=qa_id).single()
    return result["embedding"] if result and result["embedding"] else None


def generate_embedding(text: str) -> list:
    """Generate embedding using OpenAI text-embedding-3-large."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text,
        dimensions=3072,
    )
    return response.data[0].embedding


def get_company_sector(session, ticker: str) -> str | None:
    """Get sector for a company."""
    query = "MATCH (c:Company {ticker: $ticker}) RETURN c.sector as sector"
    result = session.run(query, ticker=ticker).single()
    return result["sector"] if result else None


def find_similar_same_ticker(session, embedding: list, ticker: str, exclude_id: str = None) -> list:
    """Find similar QA exchanges for the same ticker with impact data."""
    query = """
    CALL db.index.vector.queryNodes('qaexchange_vector_idx', 50, $embedding)
    YIELD node, score
    MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
    MATCH (t)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
    WHERE score >= $min_sim
      AND r.daily_stock IS NOT NULL
      AND ($exclude_id IS NULL OR node.id <> $exclude_id)
    RETURN node.id as qa_id, score,
           substring(t.conference_datetime, 0, 10) as date,
           r.daily_stock as daily_stock,
           CASE WHEN r.daily_stock >= 0 THEN 'up' ELSE 'down' END as direction
    ORDER BY score DESC LIMIT $limit
    """
    return [
        dict(r)
        for r in session.run(
            query,
            embedding=embedding,
            ticker=ticker,
            min_sim=MIN_SIMILARITY,
            exclude_id=exclude_id,
            limit=SAME_TICKER_LIMIT,
        )
    ]


def find_similar_sector(
    session, embedding: list, ticker: str, sector: str, exclude_id: str = None
) -> list:
    """Find similar QA exchanges for sector peers with impact data."""
    query = """
    CALL db.index.vector.queryNodes('qaexchange_vector_idx', 50, $embedding)
    YIELD node, score
    MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
    MATCH (t)-[r:INFLUENCES]->(c:Company)
    WHERE score >= $min_sim
      AND r.daily_stock IS NOT NULL
      AND c.ticker <> $ticker
      AND c.sector = $sector
      AND ($exclude_id IS NULL OR node.id <> $exclude_id)
    RETURN node.id as qa_id, score, c.ticker as peer_ticker,
           substring(t.conference_datetime, 0, 10) as date,
           r.daily_stock as daily_stock,
           CASE WHEN r.daily_stock >= 0 THEN 'up' ELSE 'down' END as direction
    ORDER BY score DESC LIMIT $limit
    """
    return [
        dict(r)
        for r in session.run(
            query,
            embedding=embedding,
            ticker=ticker,
            sector=sector,
            min_sim=MIN_SIMILARITY,
            exclude_id=exclude_id,
            limit=SECTOR_LIMIT,
        )
    ]


def main():
    if len(sys.argv) < 3:
        print(error("USAGE", "find_similar_qa.py TICKER QA_ID [DRIVER_TEXT]"))
        sys.exit(1)

    ticker = sys.argv[1].upper()
    qa_id = sys.argv[2]
    driver_text = sys.argv[3] if len(sys.argv) > 3 else None

    with neo4j_session() as (session, err):
        if err:
            print(err)
            sys.exit(1)

        try:
            # Get embedding from existing QA item, or from text for external/untracked input.
            exclude_id = None
            if qa_id == "N/A" or qa_id.startswith("http"):
                if not driver_text:
                    print(error("MISSING_TEXT", "DRIVER_TEXT required for external Q&A input"))
                    sys.exit(1)
                embedding = generate_embedding(driver_text)
            else:
                embedding = get_embedding_from_neo4j(session, qa_id)
                if not embedding:
                    print(error("NOT_FOUND", f"QAExchange {qa_id} not found or has no embedding"))
                    sys.exit(1)
                exclude_id = qa_id

            sector = get_company_sector(session, ticker)
            if not sector:
                print(error("TICKER_NOT_FOUND", f"Company {ticker} not found"))
                sys.exit(1)

            same = find_similar_same_ticker(session, embedding, ticker, exclude_id)
            print(f"OK|SAME_TICKER|{len(same)}")
            for r in same:
                print(
                    f"{r['qa_id']}|{r['score']:.3f}|{r['date']}|"
                    f"{r['daily_stock']:+.2f}|{r['direction']}"
                )

            sect = find_similar_sector(session, embedding, ticker, sector, exclude_id)
            print(f"OK|SECTOR|{len(sect)}")
            for r in sect:
                print(
                    f"{r['qa_id']}|{r['score']:.3f}|{r['peer_ticker']}|"
                    f"{r['date']}|{r['daily_stock']:+.2f}|{r['direction']}"
                )

        except Exception as e:
            print(error("EXCEPTION", str(e)))
            sys.exit(1)


if __name__ == "__main__":
    main()
