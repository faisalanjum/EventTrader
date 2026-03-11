#!/usr/bin/env python3
"""Audit transcript retrieval pain points to guide warmup_cache.py additions.

This is intentionally narrow: it does not attempt guidance extraction.
It measures whether transcript-side warmups should add:
  1. QuestionAnswer (3C-style) fallback coverage
  2. pre-windowed transcript snippets around guidance keywords
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/home/faisal/EventMarketDB")

from neograph.Neo4jConnection import get_manager


RAW_SIZE_THRESHOLD = 50_000
WINDOW_RADIUS = 600

KEYWORDS = (
    "expect",
    "expects",
    "expected",
    "anticipate",
    "anticipates",
    "project",
    "projects",
    "forecast",
    "forecasts",
    "outlook",
    "guidance",
    "target",
    "range",
    "raise",
    "raises",
    "lower",
    "lowers",
    "maintain",
    "maintains",
    "reaffirm",
    "reaffirms",
    "withdraw",
    "withdraws",
    "comfortable with consensus",
    "looking ahead",
    "approximately",
)

METRIC_RE = re.compile(
    r"\b("
    r"eps|earnings per share|revenue|sales|margin|gross margin|operating margin|"
    r"opex|operating expenses|operating income|tax rate|cash flow|free cash flow|"
    r"capex|capital expenditures|income"
    r")\b",
    re.IGNORECASE,
)
PERIOD_RE = re.compile(
    r"\b("
    r"q[1-4]|quarter|full year|fiscal year|fy\d{2,4}|first half|second half|h[12]"
    r")\b",
    re.IGNORECASE,
)
VALUE_RE = re.compile(
    r"("
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:billion|million|b|m))?|"
    r"\d+(?:\.\d+)?\s?%|"
    r"\d+(?:\.\d+)?\s?(?:bps|basis points|x)|"
    r"low single digits|mid single digits|high single digits|double digits|mid-teens|"
    r"between\s+\$?\d[\d,]*(?:\.\d+)?\s+and\s+\$?\d[\d,]*(?:\.\d+)?"
    r")",
    re.IGNORECASE,
)
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.IGNORECASE)


QUERY_SAMPLE_DISTINCT_TICKERS = """
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company)
WITH c.ticker AS ticker, t
ORDER BY ticker, t.conference_datetime DESC
WITH ticker, collect(t)[0] AS t
RETURN ticker,
       t.id AS transcript_id,
       t.conference_datetime AS call_date,
       t.fiscal_year AS fiscal_year,
       t.fiscal_quarter AS fiscal_quarter
ORDER BY call_date DESC
LIMIT $limit
"""

QUERY_SAMPLE_BY_TICKER = """
MATCH (t:Transcript)-[:INFLUENCES]->(:Company {ticker: $ticker})
RETURN $ticker AS ticker,
       t.id AS transcript_id,
       t.conference_datetime AS call_date,
       t.fiscal_year AS fiscal_year,
       t.fiscal_quarter AS fiscal_quarter
ORDER BY call_date DESC
LIMIT $limit
"""

QUERY_TRANSCRIPT_CONTENT = """
MATCH (t:Transcript {id: $transcript_id})
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
WITH t, pr
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WITH t, pr, qa ORDER BY toInteger(qa.sequence)
WITH t,
     pr.content AS prepared_remarks,
     [item IN collect({
       sequence: qa.sequence,
       questioner: qa.questioner,
       questioner_title: qa.questioner_title,
       responders: qa.responders,
       responder_title: qa.responder_title,
       exchanges: qa.exchanges
     }) WHERE item.sequence IS NOT NULL] AS qa_exchanges
OPTIONAL MATCH (t)-[:HAS_QA_SECTION]->(qas:QuestionAnswer)
WITH t, prepared_remarks, qa_exchanges, head(collect(qas.content)) AS qa_section
OPTIONAL MATCH (t)-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
RETURN t.id AS transcript_id,
       prepared_remarks,
       qa_exchanges,
       qa_section,
       head(collect(ft.content)) AS full_text
"""


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_stringify(v) for v in value if v is not None)
    if isinstance(value, dict):
        return "\n".join(_stringify(v) for v in value.values() if v is not None)
    return str(value)


def _merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not windows:
        return []
    windows.sort()
    merged = [windows[0]]
    for start, end in windows[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _build_window_stats(text: str) -> dict:
    if not text:
        return {
            "keyword_hits": 0,
            "window_count": 0,
            "window_chars": 0,
            "compression_ratio": None,
            "qualified_window_count": 0,
        }

    windows = []
    qualified = 0
    for match in KEYWORD_RE.finditer(text):
        start = max(0, match.start() - WINDOW_RADIUS)
        end = min(len(text), match.end() + WINDOW_RADIUS)
        snippet = text[start:end]
        if METRIC_RE.search(snippet) and (PERIOD_RE.search(snippet) or VALUE_RE.search(snippet)):
            qualified += 1
        windows.append((start, end))

    merged = _merge_windows(windows)
    window_chars = sum(end - start for start, end in merged)
    return {
        "keyword_hits": len(windows),
        "window_count": len(merged),
        "window_chars": window_chars,
        "compression_ratio": round(window_chars / len(text), 3) if text else None,
        "qualified_window_count": qualified,
    }


def _sample_transcripts(manager, limit: int, ticker: str | None):
    if ticker:
        return manager.execute_cypher_query_all(
            QUERY_SAMPLE_BY_TICKER, {"ticker": ticker, "limit": limit}
        )
    return manager.execute_cypher_query_all(QUERY_SAMPLE_DISTINCT_TICKERS, {"limit": limit})


def _audit_transcript(manager, meta: dict) -> dict:
    row = manager.execute_cypher_query(QUERY_TRANSCRIPT_CONTENT, {"transcript_id": meta["transcript_id"]})
    if not row:
        return {**meta, "error": "Transcript content not found"}

    prepared = _stringify(row.get("prepared_remarks"))
    qa_exchange_text = _stringify(row.get("qa_exchanges"))
    qa_section = _stringify(row.get("qa_section"))
    full_text = _stringify(row.get("full_text"))

    current_payload = {
        "transcript_id": row.get("transcript_id"),
        "prepared_remarks": row.get("prepared_remarks"),
        "qa_exchanges": row.get("qa_exchanges"),
    }
    enriched_payload = {
        **current_payload,
        "qa_section": row.get("qa_section"),
        "full_text": row.get("full_text"),
    }

    combined_current = "\n".join(part for part in (prepared, qa_exchange_text) if part)
    combined_enriched = "\n".join(
        part for part in (prepared, qa_exchange_text, qa_section, full_text) if part
    )
    window_stats = _build_window_stats(combined_enriched)

    return {
        **meta,
        "prepared_chars": len(prepared),
        "qa_exchange_chars": len(qa_exchange_text),
        "qa_section_chars": len(qa_section),
        "full_text_chars": len(full_text),
        "qa_exchange_count": len(row.get("qa_exchanges") or []),
        "has_qa_section_fallback": bool(qa_section and not row.get("qa_exchanges")),
        "current_3b_raw_bytes": len(json.dumps(current_payload, default=str)),
        "enriched_raw_bytes": len(json.dumps(enriched_payload, default=str)),
        "current_text_chars": len(combined_current),
        "enriched_text_chars": len(combined_enriched),
        "current_3b_over_threshold": len(json.dumps(current_payload, default=str)) > RAW_SIZE_THRESHOLD,
        "window_stats": window_stats,
    }


def _summarize(records: list[dict]) -> dict:
    with_data = [r for r in records if not r.get("error")]
    over_threshold = sum(1 for r in with_data if r["current_3b_over_threshold"])
    qa_section_gap = sum(1 for r in with_data if r["has_qa_section_fallback"])
    with_windows = [r for r in with_data if r["window_stats"]["keyword_hits"] > 0]

    avg_ratio = None
    if with_windows:
        avg_ratio = round(
            sum(r["window_stats"]["compression_ratio"] for r in with_windows) / len(with_windows),
            3,
        )

    return {
        "sample_size": len(records),
        "usable_records": len(with_data),
        "current_3b_over_threshold": over_threshold,
        "qa_section_fallback_needed": qa_section_gap,
        "keyword_hits_present": len(with_windows),
        "avg_window_compression_ratio": avg_ratio,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=8, help="Number of transcripts to sample")
    parser.add_argument("--ticker", help="Restrict sample to one ticker")
    parser.add_argument(
        "--out",
        default="/tmp/transcript_warmup_audit_sample.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    manager = get_manager()
    try:
        sample = _sample_transcripts(manager, args.limit, args.ticker)
        records = [_audit_transcript(manager, meta) for meta in sample]
    finally:
        manager.close()

    result = {
        "summary": _summarize(records),
        "records": records,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result["summary"], indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
