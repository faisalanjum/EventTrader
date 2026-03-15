#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from neo4j import GraphDatabase


OUTPUT_JSON = Path("/home/faisal/EventMarketDB/.claude/plans/Extractions/haiku_10sample_presentation_guidance.json")
MODEL = "claude-haiku-4-5-20251001"

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
]

PROMPT = """You are classifying SEC 8-K filings, with special focus on whether an investor-presentation-type filing contains REAL guidance.

Return ONLY JSON with this exact shape:
{"primary_event":"TAG","secondary_events":["TAG1","TAG2"],"guidance_present":true,"guidance_type":"new|updated|reaffirmed|none","confidence":0.0}

Allowed tags:
""" + ", ".join(TAGS) + """

Rules:
- Use GUIDANCE only if the filing contains real forward-looking targets/ranges/outlook/reaffirmation/update for future periods.
- GUIDANCE can coexist with INVESTOR_PRESENTATION.
- Do NOT call generic optimism, long-term strategy slides, or historical discussion GUIDANCE.
- Do NOT call repeated stale guidance GUIDANCE unless the filing clearly reaffirms or updates it in the current filing.
- INVESTOR_PRESENTATION means the filing is mainly a deck, prepared remarks, conference materials, investor highlights, or similar presentation content.
- If guidance_present is false, guidance_type must be "none".
- primary_event must be one tag from the list above.
- secondary_events must be distinct tags from the same list.
- confidence must be a float from 0.0 to 1.0.
"""

PRESENTATION_TERMS = [
    "investor presentation",
    "presentation materials",
    "prepared remarks",
    "investor highlights",
    "fireside chat",
    "conference presentation",
    "presentation for",
    "slides",
]


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
    query = """
    MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
    WHERE r.formType IN ['8-K','8-K/A']
      AND (
        r.items CONTAINS 'Item 2.02'
        OR r.items CONTAINS 'Item 7.01'
        OR r.items CONTAINS 'Item 8.01'
      )
    OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
    OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
    WITH r, c,
         collect(DISTINCT toLower(coalesce(s.content,''))) AS section_texts,
         collect(DISTINCT toLower(coalesce(e.content,''))) AS exhibit_texts
    WITH r, c, section_texts, exhibit_texts,
         apoc.text.join(section_texts, ' ') + ' ' + apoc.text.join(exhibit_texts, ' ') AS text_blob
    WHERE """ + " OR ".join([f"text_blob CONTAINS '{term}'" for term in PRESENTATION_TERMS]) + """
    RETURN r.accessionNo AS accession, c.ticker AS ticker, r.created AS created, r.formType AS form_type, r.items AS items
    ORDER BY rand()
    LIMIT 10
    """
    with driver.session() as session:
        return [dict(r) for r in session.run(query)]


def fetch_content(driver, accession: str) -> dict[str, Any]:
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
    return {
        "ticker": rec["ticker"],
        "accession": rec["accession"],
        "created": rec["created"],
        "form_type": rec["form_type"],
        "items": rec["items"],
        "sections": [s for s in rec["sections"] if s.get("content")],
        "exhibits": [e for e in rec["exhibits"] if e.get("content")],
    }


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def rank_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(section: dict[str, Any]) -> tuple[int, int]:
        name = (section.get("section_name") or "").lower()
        priority = 0
        if "regulationfddisclosure" in name:
            priority += 5
        if "otherevents" in name:
            priority += 4
        if "resultsofoperations" in name:
            priority += 4
        if "financialstatementsandexhibits" in name:
            priority += 2
        return (priority, len(section.get("content") or ""))

    return sorted(sections, key=score, reverse=True)


def rank_exhibits(exhibits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(exhibit: dict[str, Any]) -> tuple[int, int]:
        num = (exhibit.get("exhibit_number") or "").upper()
        content = (exhibit.get("content") or "").lower()
        priority = 0
        if num.startswith("EX-99") or num.startswith("99"):
            priority += 5
        for term in PRESENTATION_TERMS:
            if term in content:
                priority += 2
                break
        return (priority, len(exhibit.get("content") or ""))

    return sorted(exhibits, key=score, reverse=True)


def build_packet(filing: dict[str, Any]) -> str:
    parts = [
        f"Ticker: {filing['ticker']}",
        f"Accession: {filing['accession']}",
        f"Created: {filing['created']}",
        f"Form Type: {filing['form_type']}",
        f"Items: {filing['items']}",
    ]
    for section in rank_sections(filing["sections"])[:3]:
        parts.append(f"[SECTION: {section['section_name']}]\n{clean_text(section['content'])[:2200]}")
    for exhibit in rank_exhibits(filing["exhibits"])[:2]:
        parts.append(f"[EXHIBIT: {exhibit['exhibit_number']}]\n{clean_text(exhibit['content'])[:2200]}")
    return "\n\n".join(parts)


def classify(client: anthropic.Anthropic, packet: str) -> dict[str, Any]:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=260,
        temperature=0,
        messages=[{"role": "user", "content": PROMPT + "\n\nFiling packet:\n" + packet}],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", None) == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise RuntimeError(f"Non-JSON response: {text[:500]}")
        data = json.loads(match.group(0))
    return {
        "raw_text": text,
        "primary_event": data["primary_event"],
        "secondary_events": data.get("secondary_events", []),
        "guidance_present": data["guidance_present"],
        "guidance_type": data["guidance_type"],
        "confidence": data["confidence"],
        "usage": {
            "input_tokens": getattr(msg.usage, "input_tokens", None),
            "output_tokens": getattr(msg.usage, "output_tokens", None),
        },
    }


def main() -> None:
    uri, user, pw, api_key = load_config()
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    client = anthropic.Anthropic(api_key=api_key)

    rows = sample_filings(driver)
    results = []
    total_in = 0
    total_out = 0
    for row in rows:
        filing = fetch_content(driver, row["accession"])
        packet = build_packet(filing)
        pred = classify(client, packet)
        total_in += pred["usage"]["input_tokens"] or 0
        total_out += pred["usage"]["output_tokens"] or 0
        results.append(
            {
                "accession": filing["accession"],
                "ticker": filing["ticker"],
                "created": filing["created"],
                "form_type": filing["form_type"],
                "items": filing["items"],
                "packet": packet,
                "prediction": pred,
            }
        )

    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "model": MODEL,
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
