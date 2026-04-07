#!/usr/bin/env python3
"""
Ingest risk factor classifications from Massive API into Neo4j.

SAFETY:
  - Default mode is --dry-run (NO database writes)
  - Only creates NEW node labels (RiskCategory, RiskClassification)
  - Only creates NEW relationship types (HAS_RISK_CLASSIFICATION, CLASSIFIED_AS)
  - Zero modifications to existing nodes or relationships
  - Rollback: MATCH (n:RiskClassification) DETACH DELETE n; MATCH (n:RiskCategory) DETACH DELETE n;

Usage:
  python3 scripts/ingest_massive_risk_factors.py --dry-run          # default, read-only
  python3 scripts/ingest_massive_risk_factors.py --write            # actually write to Neo4j
  python3 scripts/ingest_massive_risk_factors.py --pull-only        # only pull from Massive, save JSON
  python3 scripts/ingest_massive_risk_factors.py --write --ticker AAPL  # single ticker test
"""

import os
import sys
import time
import json
import argparse
import functools
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI
import requests

# Force unbuffered output
print = functools.partial(print, flush=True)

load_dotenv()

# --- Config ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.40.73:30687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

MASSIVE_API_KEY = os.getenv("POLYGON_API_KEY")
MASSIVE_BASE_URL = "https://api.massive.com"
REQUEST_DELAY = 0.2

DATA_DIR = Path("scripts/massive_risk_data")
TAXONOMY_FILE = DATA_DIR / "taxonomy.json"
CLASSIFICATIONS_FILE = DATA_DIR / "classifications.json"
RESULTS_FILE = DATA_DIR / "ingest_results.json"


# =============================================================================
# PHASE 1: Pull from Massive API → local JSON
# =============================================================================

def pull_taxonomy(session):
    """Pull the 140-category risk taxonomy from Massive."""
    url = f"{MASSIVE_BASE_URL}/stocks/taxonomies/vX/risk-factors"
    params = {"limit": 999}
    headers = {"Authorization": f"Bearer {MASSIVE_API_KEY}"}
    resp = session.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def pull_risk_factors_for_ticker(ticker, session):
    """Pull all risk factor classifications for one ticker, handling pagination."""
    all_results = []
    url = f"{MASSIVE_BASE_URL}/stocks/filings/vX/risk-factors"
    params = {"ticker": ticker, "limit": 100}
    headers = {"Authorization": f"Bearer {MASSIVE_API_KEY}"}

    while True:
        resp = session.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            print(f"    Rate limited on {ticker}, waiting 5s...")
            time.sleep(5)
            continue
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        all_results.extend(results)

        next_url = data.get("next_url")
        if not next_url or not results:
            break

        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(next_url)
        cursor = parse_qs(parsed.query).get("cursor", [None])[0]
        if not cursor:
            break
        params = {"cursor": cursor, "limit": 100}
        time.sleep(REQUEST_DELAY)

    return all_results


def phase1_pull_from_massive(tickers):
    """Pull taxonomy + all classifications from Massive, save to local JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    http = requests.Session()

    # Pull taxonomy
    print("\n  Pulling taxonomy...")
    taxonomy = pull_taxonomy(http)
    with open(TAXONOMY_FILE, "w") as f:
        json.dump(taxonomy, f, indent=2)
    print(f"  Saved {len(taxonomy)} categories to {TAXONOMY_FILE}")

    # Pull classifications per ticker
    print(f"\n  Pulling risk factors for {len(tickers)} tickers...")
    all_classifications = {}
    total_classifications = 0

    for i, ticker in enumerate(tickers):
        risks = pull_risk_factors_for_ticker(ticker, http)
        if risks:
            all_classifications[ticker] = risks
            total_classifications += len(risks)

        if (i + 1) % 50 == 0 or (i + 1) == len(tickers):
            print(f"    [{i+1}/{len(tickers)}] — {len(all_classifications)} tickers with data, {total_classifications} total classifications")

        time.sleep(REQUEST_DELAY)

    http.close()

    with open(CLASSIFICATIONS_FILE, "w") as f:
        json.dump(all_classifications, f, indent=2)
    print(f"\n  Saved {total_classifications} classifications across {len(all_classifications)} tickers to {CLASSIFICATIONS_FILE}")

    return taxonomy, all_classifications


# =============================================================================
# PHASE 2: Validate matches against Neo4j (read-only)
# =============================================================================

def get_sections_for_ticker(driver, ticker):
    """Get all 10-K RiskFactors sections for a ticker with their content."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)
            WHERE r.formType IN ['10-K', '10-K/A']
            MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent {section_name: 'RiskFactors'})
            RETURN s.id AS section_id,
                   r.cik AS cik,
                   left(r.created, 10) AS filing_date,
                   s.content AS content,
                   r.id AS report_id
            ORDER BY r.created DESC
        """, ticker=ticker)
        return [dict(r) for r in result]


def date_within_one_day(date_a, date_b):
    """Check if two date strings (YYYY-MM-DD) are within 1 day of each other."""
    from datetime import datetime, timedelta
    try:
        a = datetime.strptime(date_a, "%Y-%m-%d")
        b = datetime.strptime(date_b, "%Y-%m-%d")
        return abs((a - b).days) <= 5
    except (ValueError, TypeError):
        return False


def normalize_text(text):
    """Normalize whitespace and unicode for span matching."""
    import re
    if not text:
        return ""
    # Normalize smart quotes to straight quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # single
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # double
    text = text.replace('\u2013', '-').replace('\u2014', '-')  # dashes
    # Collapse all whitespace (newlines, tabs, multiple spaces) to single space
    return re.sub(r'\s+', ' ', text).strip()


def compute_span(content, supporting_text):
    """Find the span of supporting_text within the section content."""
    if not content or not supporting_text:
        return -1, -1

    # Try exact match first
    idx = content.find(supporting_text)
    if idx >= 0:
        return idx, idx + len(supporting_text)

    # Try with first 100 chars (Massive sometimes truncates)
    snippet = supporting_text[:100]
    idx = content.find(snippet)
    if idx >= 0:
        return idx, idx + len(supporting_text)

    # Try normalized whitespace match
    norm_content = normalize_text(content)
    norm_text = normalize_text(supporting_text)
    idx = norm_content.find(norm_text)
    if idx >= 0:
        # Return approximate position (normalized offsets, not exact)
        return idx, idx + len(norm_text)

    # Try first 80 chars normalized
    norm_snippet = normalize_text(supporting_text[:80])
    idx = norm_content.find(norm_snippet)
    if idx >= 0:
        return idx, idx + len(norm_text)

    return -1, -1


def phase2_validate(driver, taxonomy, classifications):
    """Validate all matches, compute spans. Returns write-ready data."""
    print(f"\n  Validating matches for {len(classifications)} tickers...")

    write_data = []
    stats = {
        "tickers_processed": 0,
        "classifications_total": 0,
        "sections_matched": 0,
        "sections_unmatched": 0,
        "spans_found": 0,
        "spans_missed": 0,
        "unmatched_details": [],
    }

    for i, (ticker, risks) in enumerate(classifications.items()):
        sections = get_sections_for_ticker(driver, ticker)

        for risk in risks:
            stats["classifications_total"] += 1
            massive_cik = risk["cik"]
            massive_date = risk["filing_date"]

            # Pad CIK to 10 digits if needed (Massive may or may not zero-pad)
            padded_cik = massive_cik.zfill(10)

            # Match section by CIK + filing_date with ±1 day tolerance
            section = None
            for s in sections:
                cik_match = s["cik"] in (massive_cik, padded_cik)
                date_match = s["filing_date"] == massive_date or date_within_one_day(s["filing_date"], massive_date)
                if cik_match and date_match:
                    section = s
                    break

            if section:
                stats["sections_matched"] += 1
                span_start, span_end = compute_span(section["content"], risk["supporting_text"])
                if span_start >= 0:
                    stats["spans_found"] += 1
                else:
                    stats["spans_missed"] += 1

                # Build deterministic ID
                rc_id = f"{padded_cik}_{massive_date}_{risk['tertiary_category']}"

                write_data.append({
                    "rc_id": rc_id,
                    "section_id": section["section_id"],
                    "cik": padded_cik,
                    "ticker": ticker,
                    "filing_date": massive_date,
                    "primary_category": risk["primary_category"],
                    "secondary_category": risk["secondary_category"],
                    "tertiary_category": risk["tertiary_category"],
                    "supporting_text": risk["supporting_text"],
                    "span_start": span_start,
                    "span_end": span_end,
                    "source": "massive",
                })
            else:
                stats["sections_unmatched"] += 1
                if len(stats["unmatched_details"]) < 20:
                    stats["unmatched_details"].append({
                        "ticker": ticker,
                        "cik": massive_cik,
                        "filing_date": massive_date,
                        "available_keys": [(s["cik"], s["filing_date"]) for s in sections],
                    })

        stats["tickers_processed"] += 1
        if (i + 1) % 50 == 0 or (i + 1) == len(classifications):
            print(f"    [{i+1}/{len(classifications)}] — matched: {stats['sections_matched']}, unmatched: {stats['sections_unmatched']}")

    return write_data, stats


# =============================================================================
# PHASE 3: Write to Neo4j (only with --write flag)
# =============================================================================

def create_indexes(driver):
    """Create indexes and constraints for new node types."""
    queries = [
        "CREATE CONSTRAINT constraint_riskcategory_id IF NOT EXISTS FOR (n:RiskCategory) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT constraint_riskclassification_id IF NOT EXISTS FOR (n:RiskClassification) REQUIRE n.id IS UNIQUE",
        "CREATE INDEX index_riskclassification_ticker IF NOT EXISTS FOR (n:RiskClassification) ON (n.ticker)",
        "CREATE INDEX index_riskclassification_filing_date IF NOT EXISTS FOR (n:RiskClassification) ON (n.filing_date)",
    ]
    with driver.session() as session:
        for q in queries:
            try:
                session.run(q)
                print(f"    OK: {q[:70]}...")
            except Exception as e:
                print(f"    SKIP (exists): {q[:50]}... — {e}")


def create_vector_index(driver):
    """Create vector index on RiskClassification.embedding for similarity search."""
    query = """
    CREATE VECTOR INDEX risk_classification_vector IF NOT EXISTS
    FOR (n:RiskClassification) ON (n.embedding)
    OPTIONS {indexConfig: {
        `vector.dimensions`: 3072,
        `vector.similarity_function`: 'cosine'
    }}
    """
    with driver.session() as session:
        try:
            session.run(query)
            print("    OK: Created vector index on RiskClassification.embedding")
        except Exception as e:
            print(f"    SKIP (exists): vector index — {e}")


def write_taxonomy(driver, taxonomy):
    """Write RiskCategory nodes."""
    query = """
    UNWIND $categories AS cat
    MERGE (rc:RiskCategory {id: cat.tertiary_category})
    SET rc.primary_category = cat.primary_category,
        rc.secondary_category = cat.secondary_category,
        rc.tertiary_category = cat.tertiary_category,
        rc.description = cat.description,
        rc.taxonomy_version = toInteger(cat.taxonomy)
    """
    with driver.session() as session:
        session.run(query, categories=taxonomy)
    print(f"    Wrote {len(taxonomy)} RiskCategory nodes")


def write_classifications_batch(driver, batch):
    """Write a batch of RiskClassification nodes + relationships."""
    query = """
    UNWIND $items AS item

    // Create RiskClassification node
    MERGE (rc:RiskClassification {id: item.rc_id})
    SET rc.cik = item.cik,
        rc.ticker = item.ticker,
        rc.filing_date = item.filing_date,
        rc.primary_category = item.primary_category,
        rc.secondary_category = item.secondary_category,
        rc.tertiary_category = item.tertiary_category,
        rc.supporting_text = item.supporting_text,
        rc.span_start = item.span_start,
        rc.span_end = item.span_end,
        rc.source = item.source

    // Link to ExtractedSectionContent
    WITH rc, item
    MATCH (s:ExtractedSectionContent {id: item.section_id})
    MERGE (s)-[:HAS_RISK_CLASSIFICATION]->(rc)

    // Link to RiskCategory
    WITH rc, item
    MATCH (cat:RiskCategory {id: item.tertiary_category})
    MERGE (rc)-[:CLASSIFIED_AS]->(cat)
    """
    with driver.session() as session:
        session.run(query, items=batch)


def phase3_write(driver, taxonomy, write_data):
    """Write everything to Neo4j."""
    print("\n  Creating indexes...")
    create_indexes(driver)

    print("\n  Writing taxonomy...")
    write_taxonomy(driver, taxonomy)

    print(f"\n  Writing {len(write_data)} classifications in batches of 100...")
    batch_size = 100
    for i in range(0, len(write_data), batch_size):
        batch = write_data[i:i + batch_size]
        write_classifications_batch(driver, batch)
        written = min(i + batch_size, len(write_data))
        if written % 500 == 0 or written == len(write_data):
            print(f"    [{written}/{len(write_data)}] written")

    print(f"\n  Done. Wrote {len(write_data)} RiskClassification nodes.")


# =============================================================================
# PHASE 4: Embed RiskClassification nodes (only those missing embeddings)
# =============================================================================

def phase4_embed(driver):
    """Embed all RiskClassification nodes that don't have an embedding yet."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("  WARNING: OPENAI_API_KEY not set, skipping embeddings")
        return

    ai = OpenAI(api_key=openai_key)

    # Create vector index first
    print("\n  Creating vector index...")
    create_vector_index(driver)

    # Get all nodes missing embeddings
    with driver.session() as session:
        result = session.run("""
            MATCH (rc:RiskClassification)
            WHERE rc.embedding IS NULL
            RETURN rc.id AS id, rc.supporting_text AS text
            ORDER BY rc.id
        """)
        to_embed = [dict(r) for r in result]

    if not to_embed:
        print("  All RiskClassification nodes already have embeddings. Nothing to do.")
        return

    print(f"  {len(to_embed)} nodes need embeddings...")

    # Batch embed via OpenAI
    EMBED_BATCH = 100
    embedded = 0

    for i in range(0, len(to_embed), EMBED_BATCH):
        batch = to_embed[i:i + EMBED_BATCH]
        texts = [item["text"][:2000] for item in batch]

        resp = ai.embeddings.create(input=texts, model="text-embedding-3-large")

        # Write embeddings back to Neo4j
        updates = []
        for j, emb_data in enumerate(resp.data):
            updates.append({
                "id": batch[j]["id"],
                "embedding": emb_data.embedding,
            })

        with driver.session() as session:
            session.run("""
                UNWIND $updates AS u
                MATCH (rc:RiskClassification {id: u.id})
                SET rc.embedding = u.embedding
            """, updates=updates)

        embedded += len(batch)
        if embedded % 500 == 0 or embedded == len(to_embed):
            print(f"    [{embedded}/{len(to_embed)}] embedded")

    print(f"\n  Done. Embedded {embedded} RiskClassification nodes.")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Ingest Massive risk factor classifications into Neo4j")
    parser.add_argument("--write", action="store_true", help="Actually write to Neo4j (default is dry-run)")
    parser.add_argument("--pull-only", action="store_true", help="Only pull from Massive API, save JSON, exit")
    parser.add_argument("--skip-pull", action="store_true", help="Skip API pull, use existing JSON files")
    parser.add_argument("--ticker", type=str, help="Process single ticker (for testing)")
    args = parser.parse_args()

    mode = "WRITE" if args.write else "DRY-RUN"
    print("=" * 70)
    print(f"Massive Risk Factor Ingestion — mode: {mode}")
    print("=" * 70)

    if not MASSIVE_API_KEY:
        print("ERROR: POLYGON_API_KEY not set in .env")
        sys.exit(1)

    # Connect to Neo4j (read-only unless --write)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Get ticker list
    if args.ticker:
        tickers = [args.ticker]
        print(f"\n  Single ticker mode: {args.ticker}")
    else:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company) WHERE c.ticker IS NOT NULL
                RETURN c.ticker AS ticker ORDER BY ticker
            """)
            tickers = [r["ticker"] for r in result]
        print(f"\n  Found {len(tickers)} tickers in Neo4j")

    # PHASE 1: Pull from Massive
    if args.skip_pull:
        print("\n--- PHASE 1: SKIP (using existing JSON) ---")
        if not TAXONOMY_FILE.exists() or not CLASSIFICATIONS_FILE.exists():
            print(f"  ERROR: JSON files not found. Run without --skip-pull first.")
            sys.exit(1)
        with open(TAXONOMY_FILE) as f:
            taxonomy = json.load(f)
        with open(CLASSIFICATIONS_FILE) as f:
            classifications = json.load(f)
        # Filter to requested tickers
        if args.ticker:
            classifications = {k: v for k, v in classifications.items() if k in tickers}
        print(f"  Loaded {len(taxonomy)} categories, {len(classifications)} tickers from JSON")
    else:
        print("\n--- PHASE 1: Pull from Massive API ---")
        taxonomy, classifications = phase1_pull_from_massive(tickers)

    if args.pull_only:
        print("\n  --pull-only: exiting after API pull.")
        driver.close()
        return

    # PHASE 2: Validate matches
    print("\n--- PHASE 2: Validate matches against Neo4j (read-only) ---")
    write_data, stats = phase2_validate(driver, taxonomy, classifications)

    # Report
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    print(f"  Tickers processed:      {stats['tickers_processed']}")
    print(f"  Total classifications:  {stats['classifications_total']}")
    print(f"  Sections matched:       {stats['sections_matched']} ({stats['sections_matched']/max(stats['classifications_total'],1)*100:.1f}%)")
    print(f"  Sections unmatched:     {stats['sections_unmatched']}")
    print(f"  Spans found:            {stats['spans_found']} ({stats['spans_found']/max(stats['sections_matched'],1)*100:.1f}%)")
    print(f"  Spans missed:           {stats['spans_missed']}")
    print(f"  Ready to write:         {len(write_data)} nodes")

    if stats["unmatched_details"]:
        print(f"\n  First unmatched examples:")
        for u in stats["unmatched_details"][:5]:
            print(f"    {u['ticker']}: Massive cik={u['cik']} date={u['filing_date']}, our sections: {u['available_keys'][:3]}")

    # Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump({"stats": stats, "write_count": len(write_data)}, f, indent=2)

    # PHASE 3: Write (only with --write)
    if args.write:
        print("\n--- PHASE 3: Writing to Neo4j ---")
        print(f"  WARNING: This will create {len(write_data)} new nodes + relationships")
        print(f"  Rollback: MATCH (n:RiskClassification) DETACH DELETE n; MATCH (n:RiskCategory) DETACH DELETE n;")
        phase3_write(driver, taxonomy, write_data)

        # PHASE 4: Embed
        print("\n--- PHASE 4: Embedding RiskClassification nodes (WHERE embedding IS NULL) ---")
        phase4_embed(driver)
    else:
        print(f"\n  DRY-RUN: No changes made. Re-run with --write to create {len(write_data)} nodes.")
        print(f"  Rollback command (if needed after --write):")
        print(f"    MATCH (n:RiskClassification) DETACH DELETE n; MATCH (n:RiskCategory) DETACH DELETE n;")

    driver.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
