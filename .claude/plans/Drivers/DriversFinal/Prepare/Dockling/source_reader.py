"""Read stored documents for the Prepare notebook; no conversion or database writes."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, Query, READ_ACCESS

PROJECT = next(
    (p for p in Path(__file__).resolve().parents if (p / ".git").exists()), Path.cwd()
)
load_dotenv(PROJECT / ".env")
LABELS = {"sec": "Report", "transcript": "Transcript", "news": "News"}


def _read_query(query, **parameters):
    """Close the connection after each read; never display credentials."""
    with GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
        connection_timeout=10,
    ) as connection:
        with connection.session(database="neo4j", default_access_mode=READ_ACCESS) as session:
            return session.run(Query(query, timeout=30), parameters).data()


def list_documents(source="sec", form="10-K", limit=5):
    """List document metadata. The form filter applies only to SEC reports."""
    if source not in LABELS:
        raise ValueError('Choose "sec", "transcript", or "news".')
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")
    rows = _read_query(f"""
        MATCH (n:{LABELS[source]})
        WHERE $form IS NULL OR n.formType = $form
        RETURN $source AS source, n.id AS id, n.formType AS form,
               coalesce(n.conference_datetime, n.created) AS date,
               coalesce(n.title, n.company_name, n.description, n.id) AS title,
               coalesce(n.primaryDocumentUrl, n.url) AS source_url
        ORDER BY date DESC, id
        LIMIT $limit
    """, source=source, form=(form or None) if source == "sec" else None, limit=limit)
    if not rows:
        raise ValueError("No matching documents. Try a different form.")
    return rows


def fetch_document(selected):
    """Load a listed document, keeping its stored parts, IDs and source links."""
    rows = _read_query(f"""
        MATCH (n:{LABELS[selected['source']]} {{id: $id}})
        OPTIONAL MATCH (n)-[rel:HAS_SECTION|HAS_EXHIBIT|HAS_FILING_TEXT|
            HAS_PREPARED_REMARKS|HAS_QA_EXCHANGE|HAS_QA_SECTION|HAS_FULL_TEXT]->(part)
        WITH n, rel, part
        ORDER BY CASE type(rel)
            WHEN 'HAS_FILING_TEXT' THEN 0
            WHEN 'HAS_FULL_TEXT' THEN 0
            WHEN 'HAS_PREPARED_REMARKS' THEN 0
            ELSE 1 END, part.sequence, part.id
        RETURN n.body AS body, n.teaser AS teaser, n.exhibits AS exhibits,
               [item IN collect(CASE WHEN part IS NOT NULL THEN {{
                   id: part.id, kind: head(labels(part)),
                   name: coalesce(part.section_name, part.exhibit_number),
                   sequence: part.sequence, content: part.content,
                   exchanges: part.exchanges
               }} ELSE {{}} END) WHERE item <> {{}}] AS parts
    """, id=selected["id"])
    if not rows:
        raise ValueError("Document not found. Run Choose again.")
    loaded = rows[0]
    parts = loaded["parts"]
    if selected["source"] == "news":
        parts = [{"id": selected["id"], "kind": "News", "content": loaded["body"],
                  "teaser": loaded["teaser"]}]
    document = {**selected, "parts": parts}
    if selected["source"] == "sec":
        document["exhibit_urls"] = json.loads(loaded["exhibits"] or "{}")
    return document


# Notebook display only: fetching does not depend on pandas or IPython.
def show_choices(candidates):
    import pandas as pd
    from IPython.display import display

    display(pd.DataFrame(candidates)[["source", "id", "form", "date", "title"]])


def _part_text(part):
    return part.get("content") or part.get("exchanges") or part.get("teaser") or ""


def show_document(document):
    """Show a short preview; leave the complete document unchanged."""
    import pandas as pd
    from IPython.display import display

    parts = document["parts"]
    print(f"Loaded: {document['id']} | {len(parts)} stored part(s)")
    if document["source_url"]:
        print("Original source:", document["source_url"])
    display(pd.DataFrame([
        {"part": i, "kind": part["kind"], "name": part.get("name"),
         "id": part["id"], "characters": len(_part_text(part))}
        for i, part in enumerate(parts)
    ]))
    preview = next((_part_text(part) for part in parts if _part_text(part)), "")
    print("Preview (first 1,200 characters):\n",
          preview[:1200] or "No text stored; use the source link.")
