#!/usr/bin/env python3
"""
Fetch 8-K report from Neo4j and save as folder with individual files.
Each file mirrors exactly one Neo4j node's content field.

Also creates _combined.txt with all sections + exhibits concatenated.
"""

from neo4j import GraphDatabase
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
#                              PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "RJF"               # Company ticker
ACCESSION = "0000720005-25-000049"  # Specific accession number (None = latest)
ITEM_FILTER = None           # Filter by Item code (None = any)

NEO4J_URI = "bolt://localhost:30687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "Next2020#"

OUTPUT_DIR = Path(__file__).parent

# ═══════════════════════════════════════════════════════════════════════════════


def fetch_report(tx, ticker, accession=None, item_filter=None):
    """Fetch one 8-K report with all content nodes."""

    where = ["r.formType = '8-K'", f"c.ticker = '{ticker}'"]
    if accession:
        where.append(f"r.accessionNo = '{accession}'")
    if item_filter:
        where.append(f"r.items CONTAINS '{item_filter}'")

    query = f"""
    MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
    WHERE {' AND '.join(where)}
    WITH c, r ORDER BY r.created DESC LIMIT 1

    OPTIONAL MATCH (r)-[:HAS_SECTION]->(sec:ExtractedSectionContent)
    OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(ex:ExhibitContent)
    OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)

    RETURN c.ticker AS ticker, c.name AS company, c.cik AS cik,
           r.accessionNo AS accession, r.created AS filed, r.items AS items,
           collect(DISTINCT sec) AS sections,
           collect(DISTINCT ex) AS exhibits,
           ft AS filing_text
    """
    result = list(tx.run(query))
    return result[0] if result else None


def concatenate_report_content(record) -> str:
    """
    Concatenate all sections and exhibits into a single text string.

    Priority:
    1. All sections (sorted by name)
    2. All exhibits (sorted by number)
    3. Fallback to filing_text ONLY if both above are empty

    Returns:
        Combined text string ready for LangExtract
    """
    parts = []

    # 1. Collect all sections
    sections = [s for s in record.get('sections', []) if s and s.get('content')]
    sections.sort(key=lambda s: s.get('section_name', ''))

    for sec in sections:
        name = sec.get('section_name', 'Unknown')
        content = sec.get('content', '')
        parts.append(f"{'='*60}\nSECTION: {name}\n{'='*60}\n\n{content}")

    # 2. Collect all exhibits
    exhibits = [e for e in record.get('exhibits', []) if e and e.get('content')]
    exhibits.sort(key=lambda e: e.get('exhibit_number', ''))

    for ex in exhibits:
        num = ex.get('exhibit_number', 'Unknown')
        content = ex.get('content', '')
        parts.append(f"{'='*60}\nEXHIBIT: {num}\n{'='*60}\n\n{content}")

    # 3. Fallback to filing_text only if sections AND exhibits are empty
    if not parts:
        ft = record.get('filing_text')
        if ft and ft.get('content'):
            parts.append(f"{'='*60}\nFILING TEXT (fallback)\n{'='*60}\n\n{ft['content']}")

    return '\n\n'.join(parts)


def save_report(record):
    """Save report as folder with individual files."""

    # Build folder name
    ticker = record['ticker']
    cik = record['cik'].lstrip('0') if record['cik'] else 'unknown'
    date = record['filed'][:10] if record['filed'] else 'unknown'
    accession = record['accession'].replace('-', '')

    folder = OUTPUT_DIR / f"{ticker}_{cik}_{date}_{accession}"
    folder.mkdir(exist_ok=True)

    # 1. Metadata file
    meta = f"""ticker: {record['ticker']}
company: {record['company']}
cik: {record['cik']}
accession: {record['accession']}
filed: {record['filed']}
items: {record['items']}
"""
    (folder / "_metadata.txt").write_text(meta)

    # 2. Section files (raw content only)
    for sec in record['sections']:
        if sec and sec.get('section_name'):
            name = sec['section_name']
            content = sec.get('content', '')
            (folder / f"section_{name}.txt").write_text(content)

    # 3. Exhibit files (raw content only)
    for ex in record['exhibits']:
        if ex and ex.get('exhibit_number'):
            num = ex['exhibit_number'].replace('/', '-')  # EX-99.1 safe
            content = ex.get('content', '')
            (folder / f"exhibit_{num}.txt").write_text(content)

    # 4. Filing text file (raw content only)
    ft = record['filing_text']
    if ft and ft.get('content'):
        (folder / "filing_text.txt").write_text(ft['content'])

    # 5. Combined file (all sections + exhibits concatenated)
    combined = concatenate_report_content(record)
    (folder / "_combined.txt").write_text(combined)

    return folder


def fetch_8k_combined(ticker, accession=None, item_filter=None):
    """
    Fetch 8-K report and return path to combined content file.

    Args:
        ticker: Company ticker (e.g., "DELL")
        accession: Specific accession number (None = latest 8-K)
        item_filter: Filter by Item code, e.g., "2.02" (None = any)

    Returns:
        tuple: (combined_path, combined_text) - Path to _combined.txt and its content

    Raises:
        ValueError: If no report found for the given parameters
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    try:
        with driver.session() as session:
            record = session.execute_read(
                fetch_report,
                ticker=ticker,
                accession=accession,
                item_filter=item_filter
            )

            if not record:
                raise ValueError(f"No 8-K report found for {ticker}" +
                               (f" accession={accession}" if accession else "") +
                               (f" item={item_filter}" if item_filter else ""))

            folder = save_report(record)
            combined_path = folder / "_combined.txt"
            combined_text = combined_path.read_text()

            return str(combined_path), combined_text

    finally:
        driver.close()


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    try:
        with driver.session() as session:
            record = session.execute_read(
                fetch_report,
                ticker=TICKER,
                accession=ACCESSION,
                item_filter=ITEM_FILTER
            )

            if not record:
                print(f"No report found for {TICKER}")
                return

            folder = save_report(record)
            print(f"Saved: {folder}/")
            for f in sorted(folder.iterdir()):
                print(f"  {f.name} ({f.stat().st_size:,} bytes)")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
