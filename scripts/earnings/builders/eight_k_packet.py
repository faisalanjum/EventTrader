#!/usr/bin/env python3
"""8-K packet builder — orchestration side.

Owns:
  - QUERY_4J, QUERY_4K       (8-K sections + EX-99 exhibits)
  - QUERY_4G_META            (8-K metadata + inventory)
  - QUERY_4K_OTHER_PREVIEW   (non-99 exhibit previews)
  - QUERY_4F                 (filing text fallback)
  - _fetch_8k_core(manager, accession) -> (sections, exhibits_99)
  - build_8k_packet(accession, ticker, out_path=None) -> packet dict

Re-exported from scripts.earnings.builders.warmup_cache for back-compat —
adapters, tests, and the .claude skill shim continue to import from
warmup_cache without change.

─────────────────────────────────────────────────────────────────────
SHARED OWNERSHIP WARNING

_fetch_8k_core() is shared by:
  - warmup_cache.run_8k()       — extraction CLI mode (--8k)
  - build_8k_packet()           — earnings orchestration

warmup_cache.run_8k accesses _fetch_8k_core via the warmup_cache facade
re-export, so identity is preserved across both call sites. Changing
_fetch_8k_core() affects BOTH pipelines.
─────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from ._paths import ensure_legacy_paths
ensure_legacy_paths()

from neograph.Neo4jConnection import get_manager


# ---------------------------------------------------------------------------
# Queries 4J + 4K — 8-K Sections + EX-99.x Exhibits (from 8k-queries.md)
# Verbatim match logic. Do NOT edit — update 8k-queries.md first if needed.
# ---------------------------------------------------------------------------
QUERY_4J = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
RETURN s.section_name AS section_name, s.content AS content
ORDER BY s.section_name
"""

QUERY_4K = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number STARTS WITH 'EX-99'
RETURN e.exhibit_number AS exhibit_number, e.content AS content
ORDER BY e.exhibit_number
"""

# ---------------------------------------------------------------------------
# 4G-enriched — inventory + all Report metadata in one query
# Joins PRIMARY_FILER to validate accession belongs to the expected ticker
# ---------------------------------------------------------------------------
QUERY_4G_META = """
MATCH (r:Report {accessionNo: $accession})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
WITH r, c, coalesce(c.sector, head(collect(DISTINCT sec.name))) AS sector
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
RETURN r.created AS filed_8k,
       r.formType AS form_type,
       r.items AS items,
       r.periodOfReport AS period_of_report,
       r.market_session AS market_session,
       r.isAmendment AS is_amendment,
       r.cik AS cik,
       sector AS sector,
       collect(DISTINCT e.exhibit_number) AS exhibit_numbers,
       collect(DISTINCT s.section_name) AS section_names,
       count(DISTINCT ft) > 0 AS has_filing_text
"""

# ---------------------------------------------------------------------------
# Non-99 exhibits — preview (first 2500 chars) + full_size
# ---------------------------------------------------------------------------
QUERY_4K_OTHER_PREVIEW = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE NOT e.exhibit_number STARTS WITH 'EX-99'
RETURN e.exhibit_number AS exhibit_number,
       left(e.content, 2500) AS content_preview,
       size(e.content) AS full_size
ORDER BY e.exhibit_number
"""

# ---------------------------------------------------------------------------
# 4F — Filing text fallback
# ---------------------------------------------------------------------------
QUERY_4F = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content
"""


def _fetch_8k_core(manager, accession):
    """Private helper: run 4J + 4K queries, return (sections, exhibits_99).

    Shared by run_8k() (guidance extraction) and build_8k_packet() (earnings orchestration).
    """
    sections = manager.execute_cypher_query_all(QUERY_4J, {'accession': accession})
    exhibits = manager.execute_cypher_query_all(QUERY_4K, {'accession': accession})
    return sections, exhibits


def build_8k_packet(accession, ticker, out_path=None):
    """Assemble canonical 8k_packet.v1 for earnings orchestration.

    Steps: 4G metadata → _fetch_8k_core() → non-99 exhibits → filing text fallback → assemble → atomic write.
    Returns: packet dict (8k_packet.v1).
    """
    if out_path is None:
        out_path = f'/tmp/earnings_8k_packet_{accession}.json'

    manager = get_manager()
    try:
        # 1. 4G-enriched metadata (validates ticker owns this accession)
        meta_rows = manager.execute_cypher_query_all(QUERY_4G_META, {
            'accession': accession, 'ticker': ticker,
        })
        if not meta_rows:
            raise ValueError(f'No Report found for accession={accession} ticker={ticker}')
        meta = meta_rows[0]

        # Parse r.items from JSON string to array; normalize nulls
        raw_items = meta.get('items') or '[]'
        if isinstance(raw_items, str):
            try:
                items = json.loads(raw_items)
            except json.JSONDecodeError:
                items = [raw_items]
        else:
            items = raw_items

        # Strip nulls from inventory arrays
        section_names = [s for s in (meta.get('section_names') or []) if s is not None]
        exhibit_numbers = [e for e in (meta.get('exhibit_numbers') or []) if e is not None]

        # 2. _fetch_8k_core() for sections + EX-99.x
        sections, exhibits_99 = _fetch_8k_core(manager, accession)

        # 3. Non-99 exhibits via inventory diff → preview
        #    inventory.exhibit_numbers - fetched_ex99_numbers = other exhibits to preview
        ex99_numbers = {e['exhibit_number'] for e in exhibits_99}
        other_numbers = [n for n in exhibit_numbers if n not in ex99_numbers]
        exhibits_other = []
        if other_numbers:
            other_rows = manager.execute_cypher_query_all(QUERY_4K_OTHER_PREVIEW, {
                'accession': accession,
            })
            exhibits_other = [
                {
                    'exhibit_number': r['exhibit_number'],
                    'content_preview': r['content_preview'],
                    'full_size': r['full_size'],
                }
                for r in other_rows if r.get('exhibit_number')
            ]

        # 4. Filing text fallback — only if sections + all exhibits empty
        filing_text = None
        if not sections and not exhibits_99 and not exhibits_other:
            ft_rows = manager.execute_cypher_query_all(QUERY_4F, {'accession': accession})
            if ft_rows and ft_rows[0].get('content'):
                filing_text = ft_rows[0]['content']

        # 5. Assemble 8k_packet.v1
        packet = {
            'schema_version': '8k_packet.v1',
            'ticker': ticker,
            'accession_8k': accession,
            'filed_8k': meta.get('filed_8k'),
            'form_type': meta.get('form_type'),
            'items': items,
            'period_of_report': meta.get('period_of_report'),
            'market_session': meta.get('market_session'),
            'is_amendment': bool(meta.get('is_amendment')),
            'cik': meta.get('cik'),
            'sector': meta.get('sector'),
            'content_inventory': {
                'section_names': section_names,
                'exhibit_numbers': exhibit_numbers,
                'has_filing_text': bool(meta.get('has_filing_text')),
            },
            'sections': sections,
            'exhibits_99': exhibits_99,
            'exhibits_other': exhibits_other,
            'filing_text': filing_text,
            'assembled_at': datetime.now(timezone.utc).isoformat(),
        }

        # 6. Atomic write (temp file + rename)
        out_dir = os.path.dirname(out_path) or '.'
        os.makedirs(out_dir, exist_ok=True)
        tmp_path = out_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(packet, f, default=str)
        os.replace(tmp_path, out_path)

        return packet
    finally:
        manager.close()
