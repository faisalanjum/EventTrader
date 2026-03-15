#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from neo4j import GraphDatabase


OUTPUT_JSON = Path("/home/faisal/EventMarketDB/.claude/plans/Extractions/haiku_10sample_validation.json")
MODEL = "claude-haiku-4-5-20251001"

# Core + extended semantic tags discussed in the strategy doc.
TAGS = [
    "EARNINGS",
    "GUIDANCE",
    "BUYBACK",
    "DIVIDEND",
    "RESTRUCTURING",
    "M_AND_A",
    "DEBT",
    "EXECUTIVE_CHANGE",
    "GOVERNANCE",
    "LITIGATION",
    "INVESTOR_PRESENTATION",
    "OTHER",
    "CYBER_INCIDENT",
    "RESTATEMENT",
    "ACCOUNTANT_CHANGE",
    "DELISTING_RIGHTS_CHANGE",
    "IMPAIRMENT",
    "SECURITIES_OFFERING",
    "PRODUCT_PIPELINE",
    "REGULATORY",
    "STRATEGIC_UPDATE",
    "CRISIS_COMMUNICATION",
]

PROMPT = """You are classifying SEC 8-K filings into semantic event tags.

The filing is a non-earnings 8-K sampled from the hybrid Haiku bucket, so do not
default to EARNINGS unless the text clearly shows an earnings-results announcement.

Return ONLY JSON with this exact shape:
{"primary_event":"TAG","secondary_events":["TAG1","TAG2"],"confidence":0.0}

Rules:
- primary_event must be one of: """ + ", ".join(TAGS) + """
- secondary_events must be zero or more distinct tags from the same list
- confidence must be a float from 0.0 to 1.0
- Use OTHER only when no meaningful tag applies
- Multi-label is allowed when the filing clearly contains more than one real event
- Ignore historical mentions of buybacks/dividends unless the filing announces a new authorization/declaration/increase
- Ignore generic optimism/boilerplate as GUIDANCE
- Use INVESTOR_PRESENTATION when the filing is mainly a deck, conference, or prepared remarks without a stronger event
- Use GOVERNANCE for vote results, bylaws/charter, rights changes, board governance
- Use DELISTING_RIGHTS_CHANGE for 3.01/3.03-type exchange or rights events
- Use ACCOUNTANT_CHANGE for 4.01
- Use RESTATEMENT for 4.02
- Use CYBER_INCIDENT for 1.05
- Use SECURITIES_OFFERING for 3.02 equity issuance/ATM/secondary-offering type events
"""


@dataclass
class FilingInput:
    accession: str
    ticker: str
    created: str
    form_type: str
    items: str
    sections: list[dict[str, Any]]
    exhibits: list[dict[str, Any]]


def load_config() -> tuple[str, str, str, str]:
    load_dotenv(".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:30687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "Next2020#")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return uri, user, pw, api_key


def sample_filings(driver) -> list[dict[str, Any]]:
    # Sample from the non-earnings hybrid-Haiku bucket:
    # exclude deterministic anchors and exclude Item 2.02 earnings filings.
    query = """
    MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
    WHERE r.formType IN ['8-K','8-K/A']
      AND NOT r.items CONTAINS 'Item 2.02'
      AND NOT (
        (r.items CONTAINS 'Item 2.01')
        OR (r.items CONTAINS 'Item 1.01' AND r.items CONTAINS 'Item 2.03' AND NOT r.items CONTAINS 'Item 2.01')
        OR (r.items CONTAINS 'Item 5.07' AND NOT r.items CONTAINS 'Item 7.01' AND NOT r.items CONTAINS 'Item 8.01')
      )
      AND (
        r.items CONTAINS 'Item 2.05'
        OR r.items CONTAINS 'Item 5.02'
        OR r.items CONTAINS 'Item 7.01'
        OR r.items CONTAINS 'Item 8.01'
        OR r.items = '["Item 9.01: Financial Statements and Exhibits"]'
        OR r.items CONTAINS 'Item 3.01'
        OR r.items CONTAINS 'Item 3.03'
        OR r.items CONTAINS 'Item 4.01'
        OR r.items CONTAINS 'Item 4.02'
        OR r.items CONTAINS 'Item 1.05'
      )
    RETURN r.accessionNo AS accession, c.ticker AS ticker, r.created AS created, r.formType AS form_type, r.items AS items
    ORDER BY rand()
    LIMIT 10
    """
    with driver.session() as session:
        return [dict(r) for r in session.run(query)]


def fetch_content(driver, accession: str) -> FilingInput:
    query = """
    MATCH (r:Report {accessionNo: $accession})-[:PRIMARY_FILER]->(c:Company)
    OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
    OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
    WITH r, c,
         collect(DISTINCT {section_name: s.section_name, content: s.content}) AS sections,
         collect(DISTINCT {exhibit_number: e.exhibit_number, content: e.content}) AS exhibits
    RETURN c.ticker AS ticker,
           r.accessionNo AS accession,
           r.created AS created,
           r.formType AS form_type,
           r.items AS items,
           sections,
           exhibits
    """
    with driver.session() as session:
        rec = session.run(query, accession=accession).single()
    return FilingInput(
        accession=rec["accession"],
        ticker=rec["ticker"],
        created=rec["created"],
        form_type=rec["form_type"],
        items=rec["items"],
        sections=[s for s in rec["sections"] if s.get("content")],
        exhibits=[e for e in rec["exhibits"] if e.get("content")],
    )


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def rank_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(section: dict[str, Any]) -> tuple[int, int]:
        name = (section.get("section_name") or "").lower()
        priority = 0
        if "otherevents" in name:
            priority += 4
        if "regulationfddisclosure" in name:
            priority += 3
        if "costsassociated" in name:
            priority += 3
        if "financialstatementsandexhibits" in name:
            priority += 2
        if "departureofdirectors" in name:
            priority += 2
        return (priority, len(section.get("content") or ""))

    return sorted(sections, key=score, reverse=True)


def rank_exhibits(exhibits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(exhibit: dict[str, Any]) -> tuple[int, int]:
        num = (exhibit.get("exhibit_number") or "").upper()
        priority = 0
        if num.startswith("EX-99"):
            priority += 5
        elif num.startswith("99"):
            priority += 5
        elif num.startswith("EX-10"):
            priority += 2
        return (priority, len(exhibit.get("content") or ""))

    return sorted(exhibits, key=score, reverse=True)


def build_packet(filing: FilingInput) -> str:
    pieces = [
        f"Ticker: {filing.ticker}",
        f"Accession: {filing.accession}",
        f"Created: {filing.created}",
        f"Form Type: {filing.form_type}",
        f"Items: {filing.items}",
    ]
    for section in rank_sections(filing.sections)[:3]:
        excerpt = clean_text(section["content"])[:1800]
        pieces.append(f"[SECTION: {section['section_name']}]\n{excerpt}")
    for exhibit in rank_exhibits(filing.exhibits)[:2]:
        excerpt = clean_text(exhibit["content"])[:1800]
        pieces.append(f"[EXHIBIT: {exhibit['exhibit_number']}]\n{excerpt}")
    return "\n\n".join(pieces)


def classify(client: anthropic.Anthropic, packet: str) -> dict[str, Any]:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=220,
        temperature=0,
        messages=[
            {"role": "user", "content": PROMPT + "\n\nFiling packet:\n" + packet},
        ],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", None) == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise RuntimeError(f"Haiku returned non-JSON content: {text[:500]}")
        data = json.loads(match.group(0))
    return {
        "raw_text": text,
        "primary_event": data["primary_event"],
        "secondary_events": data.get("secondary_events", []),
        "confidence": data.get("confidence"),
        "usage": {
            "input_tokens": getattr(msg.usage, "input_tokens", None),
            "output_tokens": getattr(msg.usage, "output_tokens", None),
        },
    }


def main() -> None:
    uri, user, pw, api_key = load_config()
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    client = anthropic.Anthropic(api_key=api_key)

    sampled = sample_filings(driver)
    results: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0

    for row in sampled:
        filing = fetch_content(driver, row["accession"])
        packet = build_packet(filing)
        pred = classify(client, packet)
        total_in += pred["usage"]["input_tokens"] or 0
        total_out += pred["usage"]["output_tokens"] or 0
        results.append(
            {
                "accession": filing.accession,
                "ticker": filing.ticker,
                "created": filing.created,
                "form_type": filing.form_type,
                "items": filing.items,
                "packet": packet,
                "prediction": pred,
            }
        )

    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "model": MODEL,
                "tag_set": TAGS,
                "sample_size": len(results),
                "total_input_tokens": total_in,
                "total_output_tokens": total_out,
                "results": results,
            },
            indent=2,
        )
    )
    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
