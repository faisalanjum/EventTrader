#!/usr/bin/env python3
"""Pre-fetch extraction caches and content via direct Bolt connection.

Eliminates agent transcription errors (E1) and MCP persisted-output truncation (E4)
by running queries verbatim from a script instead of through MCP.

Usage:
    warmup_cache.py TICKER                           # Runs queries 2A + 2B
    warmup_cache.py TICKER --transcript TRANSCRIPT_ID # Runs query 3B
    warmup_cache.py TICKER --mda ACCESSION           # Runs query 5B (MD&A content)
    warmup_cache.py TICKER --8k ACCESSION            # Runs queries 4J + 4K (8-K content)
    warmup_cache.py TICKER --8k-packet ACCESSION     # Builds 8k_packet.v1 (earnings orchestration)
    warmup_cache.py TICKER --8k-packet ACCESSION --out-path /path/to/8k_packet.json
    warmup_cache.py TICKER --inter-quarter --prev-8k ISO8601 --context-cutoff ISO8601 [--out-path PATH] [--cutoff-reason REASON]
    warmup_cache.py TICKER --guidance-history          # Builds guidance_history.v1
    warmup_cache.py TICKER --guidance-history --pit 2024-08-28T20:30:00Z
    warmup_cache.py TICKER --guidance-history --pit 2024-08-28T20:30:00Z --out-path /path/to/guidance_history.json

Outputs:
    /tmp/concept_cache_{TICKER}.json                  (query 2A)
    /tmp/member_cache_{TICKER}.json                   (query 2B)
    /tmp/transcript_content_{TRANSCRIPT_ID}.json      (query 3B, --transcript mode)
    /tmp/mda_content_{ACCESSION}.json                 (query 5B, --mda mode)
    /tmp/8k_content_{ACCESSION}.json                  (queries 4J+4K, --8k mode)
    /tmp/earnings_8k_packet_{ACCESSION}.json          (8k_packet.v1, --8k-packet mode)
    /tmp/earnings_guidance_{TICKER}.json               (guidance_history.v1, --guidance-history mode)
"""

import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

from neograph.Neo4jConnection import get_manager

# ---------------------------------------------------------------------------
# Query 2A — Concept Usage Cache (from queries-common.md:102-118)
# Verbatim copy. Do NOT edit — update queries-common.md first if needed.
# ---------------------------------------------------------------------------
QUERY_2A = """
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE rk.formType = '10-K'
WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last_10k_date
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q']
  AND r.created >= last_10k_date
  AND f.is_numeric = '1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
WITH con.qname AS qname, con.label AS label, count(f) AS usage
ORDER BY usage DESC
RETURN qname, label, usage
"""

# ---------------------------------------------------------------------------
# Query 2B — Member Profile Cache (DIAGNOSTIC ONLY, from queries-common.md:127-177)
# The authoritative member source is QUERY_MEMBER_MAP below.
# 2B is retained for diagnostics (shows which members have XBRL context usage).
# Verbatim copy. Do NOT edit — update queries-common.md first if needed.
# ---------------------------------------------------------------------------
QUERY_2B = """
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE size(ctx.dimension_u_ids) > 0 AND size(ctx.member_u_ids) > 0
UNWIND range(0, size(ctx.member_u_ids)-1) AS i
WITH ctx.dimension_u_ids[i] AS dim_u_id, ctx.member_u_ids[i] AS mem_u_id
WHERE dim_u_id IS NOT NULL AND mem_u_id IS NOT NULL
WITH DISTINCT dim_u_id, mem_u_id
WITH dim_u_id, mem_u_id,
     split(mem_u_id, ':')[0] AS mem_cik_raw
WITH dim_u_id, mem_u_id,
     CASE
       WHEN mem_cik_raw =~ '^[0-9]+$'
       THEN toString(toInteger(mem_cik_raw)) + substring(mem_u_id, size(mem_cik_raw))
       ELSE mem_u_id
     END AS mem_u_id_nopad
MATCH (m:Member)
WHERE m.u_id = mem_u_id OR m.u_id = mem_u_id_nopad
WITH m.qname AS member_qname,
     m.u_id AS member_u_id,
     m.label AS member_label,
     dim_u_id,
     split(dim_u_id, ':') AS dim_parts,
     count(*) AS usage
WITH member_qname,
     member_u_id,
     member_label,
     dim_u_id AS axis_u_id,
     dim_parts[size(dim_parts)-2] + ':' + dim_parts[size(dim_parts)-1] AS axis_qname,
     usage
ORDER BY member_qname, usage DESC
WITH member_qname,
     collect({
       member_u_id: member_u_id,
       member_label: member_label,
       axis_qname: axis_qname,
       axis_u_id: axis_u_id,
       usage: usage
     }) AS versions
RETURN member_qname,
       versions[0].member_u_id AS best_member_u_id,
       versions[0].member_label AS best_member_label,
       versions[0].axis_qname AS best_axis_qname,
       versions[0].axis_u_id AS best_axis_u_id,
       versions[0].usage AS best_usage,
       reduce(total = 0, v IN versions | total + v.usage) AS total_usage
"""

# ---------------------------------------------------------------------------
# Member Map — Authoritative CIK-based member lookup (all company members)
# Replaces inline Neo4j query in guidance_write_cli.py. Produces a precomputed
# normalized_label -> [u_id, ...] dict for use in both dry-run and write modes.
# ---------------------------------------------------------------------------
QUERY_MEMBER_MAP = """
MATCH (c:Company {ticker: $ticker})
WITH toString(c.cik) AS cik
WITH cik,
     CASE WHEN cik =~ '^0+[1-9].*'
          THEN toString(toInteger(cik))
          ELSE cik END AS cik_stripped
MATCH (m:Member)
WHERE m.u_id STARTS WITH cik_stripped + ':' OR m.u_id STARTS WITH cik + ':'
RETURN m.label AS label, m.qname AS qname, head(collect(m.u_id)) AS u_id
"""


def _build_member_map(rows):
    """Build normalized label -> [u_id, ...] lookup dict from CIK-based Member query."""
    from guidance_ids import normalize_for_member_match
    member_map = {}
    for row in rows:
        if row.get('label'):
            norm = normalize_for_member_match(row['label'])
            if norm:
                member_map.setdefault(norm, []).append(row['u_id'])
    return member_map


# ---------------------------------------------------------------------------
# Query 3B — Structured Transcript Content (from transcript-queries.md:25-46)
# Verbatim copy. Do NOT edit — update transcript-queries.md first if needed.
# ---------------------------------------------------------------------------
QUERY_3B = """
MATCH (t:Transcript {id: $transcript_id})
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WITH t, pr,
     qa ORDER BY toInteger(qa.sequence)
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
RETURN t.id AS transcript_id,
       t.conference_datetime AS call_date,
       t.company_name AS company,
       t.fiscal_quarter AS fiscal_quarter,
       t.fiscal_year AS fiscal_year,
       prepared_remarks,
       qa_exchanges
"""


def run_warmup(ticker):
    """Run queries 2A and 2B, write cache files."""
    manager = get_manager()
    try:
        concepts = manager.execute_cypher_query_all(QUERY_2A, {'ticker': ticker})
        concept_path = f'/tmp/concept_cache_{ticker}.json'
        with open(concept_path, 'w') as f:
            json.dump(concepts, f, default=str)
        print(f'2A: {len(concepts)} concepts → {concept_path}')

        members = manager.execute_cypher_query_all(QUERY_2B, {'ticker': ticker})
        member_path = f'/tmp/member_cache_{ticker}.json'
        with open(member_path, 'w') as f:
            json.dump(members, f, default=str)
        print(f'2B: {len(members)} members → {member_path}')

        member_rows = manager.execute_cypher_query_all(QUERY_MEMBER_MAP, {'ticker': ticker})
        member_map = _build_member_map(member_rows)
        map_path = f'/tmp/member_map_{ticker}.json'
        with open(map_path, 'w') as f:
            json.dump(member_map, f)
        print(f'MemberMap: {len(member_map)} keys ({len(member_rows)} raw) → {map_path}')
    finally:
        manager.close()


def run_transcript(ticker, transcript_id):
    """Run query 3B, write transcript content file."""
    manager = get_manager()
    try:
        rows = manager.execute_cypher_query_all(QUERY_3B, {'transcript_id': transcript_id})
        out_path = f'/tmp/transcript_content_{transcript_id}.json'
        with open(out_path, 'w') as f:
            json.dump(rows, f, default=str)
        print(f'3B: {len(rows)} records → {out_path}')
    finally:
        manager.close()


# ---------------------------------------------------------------------------
# Query 5B — Canonical MD&A Section (from 10k-queries.md / 10q-queries.md)
# Handles both 10-K (curly apostrophe) and 10-Q (no apostrophe) variants.
# Verbatim match logic. Do NOT edit — update asset query files first if needed.
# ---------------------------------------------------------------------------
QUERY_5B = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name STARTS WITH 'Management'
  AND s.section_name CONTAINS 'DiscussionandAnalysisofFinancialCondition'
RETURN s.id AS section_id,
       s.section_name AS section_name,
       s.content AS content,
       size(s.content) AS content_length,
       r.accessionNo AS accessionNo,
       r.formType AS formType,
       r.created AS filing_date,
       r.periodOfReport AS periodOfReport
"""


def run_mda(accession):
    """Run query 5B via direct Bolt, write MD&A content file.

    Bypasses MCP to avoid persisted-output truncation on large MD&A sections
    (p90 ~90KB, max ~372KB). Same pattern as run_transcript().
    """
    manager = get_manager()
    try:
        rows = manager.execute_cypher_query_all(QUERY_5B, {'accession': accession})
        out_path = f'/tmp/mda_content_{accession}.json'
        with open(out_path, 'w') as f:
            json.dump(rows, f, default=str)
        if rows:
            print(f'5B: MD&A {rows[0].get("content_length", "?")} chars → {out_path}')
        else:
            print(f'5B: No MD&A section found → {out_path} (empty)')
    finally:
        manager.close()


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

# ---------------------------------------------------------------------------
# Guidance History — all GuidanceUpdate nodes for a ticker
# Two variants: full history and PIT-filtered
# NOTE: explicit AS aliases required — Neo4j Python driver returns
# 'gu.basis_norm' not 'basis_norm' for unaliased dotted property access.
# ---------------------------------------------------------------------------
QUERY_GUIDANCE_HISTORY = """
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(concept:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(member:Member)
RETURN g.label AS metric, g.id AS metric_id,
       gu.basis_norm AS basis_norm, gu.segment AS segment,
       gu.segment_slug AS segment_slug,
       gu.period_scope AS period_scope,
       gu.canonical_unit AS canonical_unit, gu.time_type AS time_type,
       gu.fiscal_year AS fiscal_year, gu.fiscal_quarter AS fiscal_quarter,
       gu.given_date AS given_date, gu.low AS low, gu.mid AS mid,
       gu.high AS high,
       gu.source_type AS source_type, gu.derivation AS derivation,
       gu.qualitative AS qualitative, gu.conditions AS conditions,
       gu.evhash16 AS evhash16,
       gp.start_date AS period_start, gp.end_date AS period_end,
       concept.qname AS xbrl_qname,
       collect(DISTINCT member.qname) AS member_qnames
ORDER BY g.label, gu.basis_norm, gu.segment_slug, gu.period_scope,
         gu.canonical_unit, gu.time_type, gu.given_date
"""

QUERY_GUIDANCE_HISTORY_PIT = """
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE datetime(gu.given_date) <= datetime($pit)
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(concept:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(member:Member)
RETURN g.label AS metric, g.id AS metric_id,
       gu.basis_norm AS basis_norm, gu.segment AS segment,
       gu.segment_slug AS segment_slug,
       gu.period_scope AS period_scope,
       gu.canonical_unit AS canonical_unit, gu.time_type AS time_type,
       gu.fiscal_year AS fiscal_year, gu.fiscal_quarter AS fiscal_quarter,
       gu.given_date AS given_date, gu.low AS low, gu.mid AS mid,
       gu.high AS high,
       gu.source_type AS source_type, gu.derivation AS derivation,
       gu.qualitative AS qualitative, gu.conditions AS conditions,
       gu.evhash16 AS evhash16,
       gp.start_date AS period_start, gp.end_date AS period_end,
       concept.qname AS xbrl_qname,
       collect(DISTINCT member.qname) AS member_qnames
ORDER BY g.label, gu.basis_norm, gu.segment_slug, gu.period_scope,
         gu.canonical_unit, gu.time_type, gu.given_date
"""

# Source priority for deterministic merge ordering: 8k > transcript > 10q > 10k > news
_SOURCE_PRIORITY = {'8k': 0, 'transcript': 1, '10q': 2, '10k': 3, 'news': 4}


def _extract_given_day(ts):
    """Extract calendar date string from ISO timestamp."""
    return str(ts)[:10] if ts else None


def _normalize_qualitative(q):
    """Normalize qualitative string for collapse comparison.

    Handles verified real-world variants: 'low single-digit' vs 'low-single-digits',
    'flat to 3%' vs 'Flat to 3%'. Null treated as empty string.
    """
    s = (q or "").lower().strip()
    s = s.replace('-', ' ')
    words = s.split()  # also collapses multiple spaces
    if words and len(words[-1]) > 1 and words[-1].endswith('s'):
        words[-1] = words[-1][:-1]
    return ' '.join(words)


def resolve_unit_groups(rows):
    """For each base series (5D key without unit), if exactly one non-unknown
    canonical_unit exists, remap all 'unknown' entries to that unit.
    Prevents false series splits from extraction quality gaps."""

    base_units = {}  # (metric_id, basis, seg_slug, scope, tt) → set of non-unknown units
    for r in rows:
        base = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                r['period_scope'], r['time_type'])
        if r['canonical_unit'] != 'unknown':
            base_units.setdefault(base, set()).add(r['canonical_unit'])

    for r in rows:
        if r['canonical_unit'] == 'unknown':
            base = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                    r['period_scope'], r['time_type'])
            real_units = base_units.get(base, set())
            if len(real_units) == 1:
                r['resolved_unit'] = next(iter(real_units))
            else:
                r['resolved_unit'] = 'unknown'
        else:
            r['resolved_unit'] = r['canonical_unit']

    return rows


# ─────────────────────────────────────────────────────────────────────
# SHARED OWNERSHIP WARNING
#
# _fetch_8k_core()     — private helper, shared by BOTH pipelines below
# run_8k()             — used by GUIDANCE EXTRACTION (extraction_worker.py)
# build_8k_packet()    — used by EARNINGS ORCHESTRATION (earnings-orchestrator)
#
# Changing _fetch_8k_core() affects BOTH pipelines.
# Changing run_8k() affects guidance extraction ONLY.
# Changing build_8k_packet() affects earnings orchestration ONLY.
# ─────────────────────────────────────────────────────────────────────


def _fetch_8k_core(manager, accession):
    """Private helper: run 4J + 4K queries, return (sections, exhibits_99).

    Shared by run_8k() (guidance extraction) and build_8k_packet() (earnings orchestration).
    """
    sections = manager.execute_cypher_query_all(QUERY_4J, {'accession': accession})
    exhibits = manager.execute_cypher_query_all(QUERY_4K, {'accession': accession})
    return sections, exhibits


def run_8k(accession):
    """Run queries 4J + 4K via direct Bolt, write combined 8-K content file.

    Bypasses MCP to avoid persisted-output truncation on large aggregate payloads
    (p95 ~175KB combined, 4,248 filings > 80KB). Same pattern as run_transcript().
    """
    manager = get_manager()
    try:
        sections, exhibits = _fetch_8k_core(manager, accession)
        result = {
            'sections': sections,
            'exhibits': exhibits,
        }
        out_path = f'/tmp/8k_content_{accession}.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, default=str)
        sec_total = sum(len(s.get('content', '')) for s in sections)
        ex_total = sum(len(e.get('content', '')) for e in exhibits)
        print(f'4J+4K: {len(sections)} sections ({sec_total // 1000}KB) + {len(exhibits)} exhibits ({ex_total // 1000}KB) → {out_path}')
    finally:
        manager.close()


def build_8k_packet(accession, ticker, out_path=None):
    """Assemble canonical 8k_packet.v1 for earnings orchestration.

    Steps: 4G metadata → _fetch_8k_core() → non-99 exhibits → filing text fallback → assemble → atomic write.
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
            print(f'ERROR: No Report found for accession={accession} ticker={ticker}', file=sys.stderr)
            sys.exit(1)
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

        sec_total = sum(len(s.get('content', '')) for s in sections)
        ex99_total = sum(len(e.get('content', '')) for e in exhibits_99)
        print(f'8k_packet.v1: {len(sections)} sections ({sec_total // 1000}KB) + '
              f'{len(exhibits_99)} EX-99 ({ex99_total // 1000}KB) + '
              f'{len(exhibits_other)} other exhibits'
              f'{" + filing_text fallback" if filing_text else ""}'
              f' → {out_path}')
    finally:
        manager.close()


# ─────────────────────────────────────────────────────────────────────
# build_guidance_history() — EARNINGS ORCHESTRATION only
# Reads Guidance/GuidanceUpdate/GuidancePeriod nodes written by
# guidance extraction (guidance_writer.py). Read-only — never writes
# to Neo4j. Changes here do NOT affect guidance extraction.
# ─────────────────────────────────────────────────────────────────────


def _format_value(low, mid, high, unit, qualitative, derivation):
    """Format numeric/qualitative guidance value for rendered text."""
    is_numeric = (low is not None or mid is not None or high is not None)
    if not is_numeric:
        return qualitative or '(qualitative missing)'

    def _fmt_num(v, u):
        if v is None:
            return '?'
        if u == 'm_usd':
            if abs(v) >= 1000:
                return f'${v / 1000:g}B'
            return f'${v:g}M'
        elif u == 'usd':
            return f'${v:g}'
        elif u == 'percent':
            return f'{v:g}%'
        elif u == 'basis_points':
            return f'{v:+g} bps' if v != 0 else '0 bps'
        elif u == 'percent_yoy':
            return f'{v:g}% YoY'
        elif u == 'percent_points':
            return f'{v:g} pp'
        elif u == 'x':
            return f'{v:g}x'
        else:
            return f'{v:g}'

    # Point: all three equal or only mid
    if low == mid == high and mid is not None:
        return _fmt_num(mid, unit)
    if low is None and high is None and mid is not None:
        return f'~{_fmt_num(mid, unit)}'

    # Range — suffix only on high value
    if low is not None and high is not None:
        hi_s = _fmt_num(high, unit)
        # Strip unit suffix from lo for clean ranges (e.g., "$345-$355M" not "$345M-$355M")
        if unit == 'm_usd':
            lo_b, hi_b = abs(low) >= 1000, abs(high) >= 1000
            if lo_b and hi_b:
                lo_s = f'${low / 1000:g}'
            elif not lo_b and not hi_b:
                lo_s = f'${low:g}'
            else:
                lo_s = _fmt_num(low, unit)  # mixed scales — keep both suffixes
        elif unit == 'usd':
            lo_s = f'${low:g}'
        elif unit in ('percent', 'percent_yoy', 'percent_points'):
            lo_s = f'{low:g}'
        elif unit == 'basis_points':
            lo_s = f'{low:+g}' if low != 0 else '0'
        elif unit == 'x':
            lo_s = f'{low:g}'
        else:
            lo_s = f'{low:g}'
        # Use "to" when either value is negative or basis_points
        if low < 0 or high < 0 or unit == 'basis_points':
            return f'{lo_s} to {hi_s}'
        return f'{lo_s}-{hi_s}'

    # Floor/ceiling (only one bound)
    if low is not None:
        return f'>={_fmt_num(low, unit)}'
    if high is not None:
        return f'<={_fmt_num(high, unit)}'
    return f'~{_fmt_num(mid, unit)}'


def render_guidance_text(packet):
    """Render guidance_history.v1 packet to planner-readable text."""
    ticker = packet['ticker']
    series = packet['series']
    summary = packet['summary']

    if not series:
        return f'=== GUIDANCE HISTORY: {ticker} ===\n(no guidance data available)'

    pit_str = packet.get('pit')
    header_parts = [f'{summary["total_series"]} series',
                    f'{summary["total_updates_collapsed"]} events']
    if pit_str:
        pit_day = _extract_given_day(pit_str)
        header_parts.append(f'cutoff {pit_day}')
    header = f'=== GUIDANCE HISTORY: {ticker} ({", ".join(header_parts)}) ==='

    lines = [header, '']
    for s in series:
        # Series header with simplification rules
        parts = [s['period_scope']]
        if s['resolved_unit'] and s['resolved_unit'] != 'unknown':
            parts.append(s['resolved_unit'])
        if s['basis_norm'] and s['basis_norm'] != 'unknown':
            parts.append(f'{s["basis_norm"]} basis')
        if s['segment'] and s['segment'] != 'Total':
            parts.append(f'{s["segment"]} segment')
        if s['time_type'] and s['time_type'] != 'duration':
            parts.append(s['time_type'])
        lines.append(f'{s["metric"]} ({", ".join(parts)}):')

        for u in s['updates']:
            # Period label
            fy = u.get('fiscal_year')
            fq = u.get('fiscal_quarter')
            if fq:
                period = f'FY{fy}-Q{fq}'
            else:
                period = f'FY{fy}'

            # Value
            val = _format_value(u.get('low'), u.get('mid'), u.get('high'),
                                s['resolved_unit'], u.get('qualitative'),
                                u.get('derivation'))

            # Sources
            src_str = '+'.join(u.get('sources', []))

            # Build update line
            parts = [f'{u["given_day"]}', f'sources: {src_str}']
            if u.get('derivation'):
                parts.append(u['derivation'])
            cond = u.get('conditions')
            if cond:
                cond_trunc = cond[:100] + '...' if len(cond) > 100 else cond
                parts.append(cond_trunc)
            lines.append(f'  {period}: {val} ({", ".join(parts)})')

        lines.append('')

    return '\n'.join(lines).rstrip()


def build_guidance_history(ticker, pit=None, out_path=None):
    """Assemble canonical guidance_history.v1 for earnings orchestration.

    Steps: query → resolve units → 6D grouping → collapse duplicates → sort → JSON → atomic write.
    """
    if out_path is None:
        out_path = f'/tmp/earnings_guidance_{ticker}.json'

    manager = get_manager()
    try:
        # 1. Query
        query = QUERY_GUIDANCE_HISTORY_PIT if pit else QUERY_GUIDANCE_HISTORY
        params = {'ticker': ticker, 'pit': pit} if pit else {'ticker': ticker}
        rows = manager.execute_cypher_query_all(query, params)
        total_raw = len(rows)

        if not rows:
            packet = {
                'schema_version': 'guidance_history.v1',
                'ticker': ticker,
                'pit': pit,
                'series': [],
                'summary': {
                    'total_series': 0,
                    'total_updates_raw': 0,
                    'total_updates_collapsed': 0,
                    'earliest_date': None,
                    'latest_date': None,
                },
                'assembled_at': datetime.now(timezone.utc).isoformat(),
            }
            out_dir = os.path.dirname(out_path) or '.'
            os.makedirs(out_dir, exist_ok=True)
            tmp_path = out_path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(packet, f, default=str)
            os.replace(tmp_path, out_path)
            text = render_guidance_text(packet)
            print(text)
            print(f'guidance_history.v1: 0 series, 0 events → {out_path}')
            return

        # 2. Resolve unit groups
        rows = resolve_unit_groups(rows)

        # 3. Group by 6D key
        series_map = defaultdict(list)
        for r in rows:
            key = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                   r['period_scope'], r['resolved_unit'], r['time_type'])
            series_map[key].append(r)

        # 4. For each series: select display segment, collapse duplicates
        all_series = []
        for key, updates in series_map.items():
            metric_id, basis_norm, segment_slug, period_scope, resolved_unit, time_type = key

            # Display segment: most frequent non-null label, tie-break lexicographic
            seg_counter = Counter()
            for u in updates:
                seg = u.get('segment')
                if seg is not None:
                    seg_counter[seg] += 1
            if seg_counter:
                display_segment = sorted(seg_counter.items(),
                                         key=lambda x: (-x[1], x[0]))[0][0]
            else:
                display_segment = segment_slug or 'Total'

            # raw_unit_variants: sorted distinct canonical_unit values
            raw_units = sorted(set(u['canonical_unit'] for u in updates
                                   if u.get('canonical_unit')))

            metric_label = updates[0]['metric']

            # Collapse same-day cross-source duplicates
            collapse_groups = defaultdict(list)
            for u in updates:
                given_day = _extract_given_day(u.get('given_date'))
                fy = u.get('fiscal_year')
                fq = u.get('fiscal_quarter')
                low, mid, high = u.get('low'), u.get('mid'), u.get('high')
                is_numeric = (low is not None or mid is not None or high is not None)

                if is_numeric:
                    ckey = (fy, fq, given_day, low, mid, high)
                else:
                    norm_q = _normalize_qualitative(u.get('qualitative'))
                    ckey = ('qual', fy, fq, given_day, norm_q)
                collapse_groups[ckey].append(u)

            collapsed_updates = []
            for ckey, group in collapse_groups.items():
                # Sort by source priority for deterministic primary selection
                group.sort(key=lambda u: _SOURCE_PRIORITY.get(
                    u.get('source_type', ''), 99))

                # Merge sources (sorted by priority)
                sources = sorted(
                    {u['source_type'] for u in group if u.get('source_type')},
                    key=lambda s: _SOURCE_PRIORITY.get(s, 99))

                # Conditions: keep richest (longest non-null)
                conditions = None
                for u in group:
                    c = u.get('conditions')
                    if c and (conditions is None or len(c) > len(conditions)):
                        conditions = c

                # Qualitative: keep richest (longest non-null)
                qualitative = None
                for u in group:
                    q = u.get('qualitative')
                    if q and (qualitative is None or len(q) > len(qualitative)):
                        qualitative = q

                # Derivation from primary source (first by priority)
                derivation = group[0].get('derivation')

                # xbrl_qname: first non-null
                xbrl_qname = None
                for u in group:
                    if u.get('xbrl_qname'):
                        xbrl_qname = u['xbrl_qname']
                        break

                # member_qnames: union all, sorted alphabetically
                all_members = set()
                for u in group:
                    for m in (u.get('member_qnames') or []):
                        if m:
                            all_members.add(m)

                # evhash16: first
                evhash16 = group[0].get('evhash16')

                # given_date_ts: earliest
                timestamps = [str(u['given_date']) for u in group
                              if u.get('given_date')]
                given_date_ts = min(timestamps) if timestamps else None
                given_day = _extract_given_day(given_date_ts)

                # Period dates from primary source
                period_start = str(group[0]['period_start']) if group[0].get('period_start') else None
                period_end = str(group[0]['period_end']) if group[0].get('period_end') else None

                collapsed_updates.append({
                    'fiscal_year': group[0].get('fiscal_year'),
                    'fiscal_quarter': group[0].get('fiscal_quarter'),
                    'given_date_ts': given_date_ts,
                    'given_day': given_day,
                    'low': group[0].get('low'),
                    'mid': group[0].get('mid'),
                    'high': group[0].get('high'),
                    'sources': sources,
                    'derivation': derivation,
                    'qualitative': qualitative,
                    'conditions': conditions,
                    'evhash16': evhash16,
                    'period_start': period_start,
                    'period_end': period_end,
                    'xbrl_qname': xbrl_qname,
                    'member_qnames': sorted(all_members),
                })

            # Sort updates: given_day, fiscal_year, fiscal_quarter
            collapsed_updates.sort(key=lambda u: (
                u.get('given_day') or '',
                u.get('fiscal_year') or 0,
                u.get('fiscal_quarter') or 0,
            ))

            all_series.append({
                'metric': metric_label,
                'metric_id': metric_id,
                'basis_norm': basis_norm,
                'segment': display_segment,
                'segment_slug': segment_slug,
                'period_scope': period_scope,
                'raw_unit_variants': raw_units,
                'resolved_unit': resolved_unit,
                'time_type': time_type,
                'updates': collapsed_updates,
            })

        # 5. Sort series: alphabetical by metric, Total first within same metric_id
        all_series.sort(key=lambda s: (
            s['metric'],
            0 if s['segment_slug'] == 'total' else 1,
            s['segment_slug'],
        ))

        # Compute summary
        all_days = []
        total_collapsed = 0
        for s in all_series:
            total_collapsed += len(s['updates'])
            for u in s['updates']:
                if u.get('given_day'):
                    all_days.append(u['given_day'])

        packet = {
            'schema_version': 'guidance_history.v1',
            'ticker': ticker,
            'pit': pit,
            'series': all_series,
            'summary': {
                'total_series': len(all_series),
                'total_updates_raw': total_raw,
                'total_updates_collapsed': total_collapsed,
                'earliest_date': min(all_days) if all_days else None,
                'latest_date': max(all_days) if all_days else None,
            },
            'assembled_at': datetime.now(timezone.utc).isoformat(),
        }

        # 6-7. Atomic write
        out_dir = os.path.dirname(out_path) or '.'
        os.makedirs(out_dir, exist_ok=True)
        tmp_path = out_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(packet, f, default=str)
        os.replace(tmp_path, out_path)

        # Print rendered text + summary
        text = render_guidance_text(packet)
        print(text)
        print(f'\nguidance_history.v1: {len(all_series)} series, '
              f'{total_raw} raw → {total_collapsed} collapsed → {out_path}')
    finally:
        manager.close()


# ─────────────────────────────────────────────────────────────────────
# build_inter_quarter_context() — EARNINGS ORCHESTRATION only
# Reads Date/HAS_PRICE, News/INFLUENCES, Report/PRIMARY_FILER,
# Dividend, Split nodes. Read-only — never writes to Neo4j.
# ─────────────────────────────────────────────────────────────────────

# --- Inter-quarter query constants ---

QUERY_IQ_PRICES = """
MATCH (d:Date)-[hp:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= $prev_day AND d.date <= $cutoff_day
OPTIONAL MATCH (d)-[spy:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)-[:BELONGS_TO]->(sec:Sector)
OPTIONAL MATCH (d)-[sec_hp:HAS_PRICE]->(sec)
OPTIONAL MATCH (d)-[ind_hp:HAS_PRICE]->(ind)
RETURN d.date AS date,
       hp.open AS open,
       hp.high AS high,
       hp.low AS low,
       hp.close AS close,
       hp.daily_return AS daily_return,
       hp.volume AS volume,
       hp.vwap AS vwap,
       hp.transactions AS transactions,
       hp.timestamp AS price_timestamp,
       spy.daily_return AS spy_return,
       sec_hp.daily_return AS sector_return,
       sec.name AS sector_name,
       ind_hp.daily_return AS industry_return,
       ind.name AS industry_name
ORDER BY d.date
"""

QUERY_IQ_NEWS = """
MATCH (n:News)-[rel:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(n.created) > datetime($prev_8k_ts)
  AND datetime(n.created) < datetime($context_cutoff_ts)
RETURN n.created AS created,
       n.market_session AS market_session,
       n.id AS news_id,
       n.title AS title,
       n.channels AS channels,
       n.authors AS authors,
       n.tags AS tags,
       n.url AS url,
       n.updated AS updated,
       n.returns_schedule AS returns_schedule,
       rel.hourly_stock AS hourly_stock,
       rel.session_stock AS session_stock,
       rel.daily_stock AS daily_stock,
       rel.hourly_sector AS hourly_sector,
       rel.session_sector AS session_sector,
       rel.daily_sector AS daily_sector,
       rel.hourly_industry AS hourly_industry,
       rel.session_industry AS session_industry,
       rel.daily_industry AS daily_industry,
       rel.hourly_macro AS hourly_macro,
       rel.session_macro AS session_macro,
       rel.daily_macro AS daily_macro
ORDER BY datetime(n.created)
"""

QUERY_IQ_FILINGS = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE datetime(r.created) > datetime($prev_8k_ts)
  AND datetime(r.created) < datetime($context_cutoff_ts)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(sec:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
RETURN r.created AS created,
       r.market_session AS market_session,
       r.formType AS form_type,
       r.accessionNo AS accession,
       r.id AS report_id,
       r.description AS description,
       r.items AS items,
       r.exhibits AS exhibits,
       r.periodOfReport AS period_of_report,
       r.isAmendment AS is_amendment,
       r.xbrl_status AS xbrl_status,
       r.primaryDocumentUrl AS primary_doc_url,
       r.linkToTxt AS link_to_txt,
       r.linkToHtml AS link_to_html,
       r.linkToFilingDetails AS link_to_filing_details,
       r.returns_schedule AS returns_schedule,
       collect(DISTINCT sec.section_name) AS section_names,
       count(DISTINCT ft) > 0 AS has_filing_text,
       count(DISTINCT fs) AS financial_statement_count,
       pf.hourly_stock AS hourly_stock,
       pf.session_stock AS session_stock,
       pf.daily_stock AS daily_stock,
       pf.hourly_sector AS hourly_sector,
       pf.session_sector AS session_sector,
       pf.daily_sector AS daily_sector,
       pf.hourly_industry AS hourly_industry,
       pf.session_industry AS session_industry,
       pf.daily_industry AS daily_industry,
       pf.hourly_macro AS hourly_macro,
       pf.session_macro AS session_macro,
       pf.daily_macro AS daily_macro
ORDER BY datetime(r.created)
"""

QUERY_IQ_DIVIDENDS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_DIVIDEND]->(div:Dividend)
WHERE div.declaration_date > $prev_day
  AND div.declaration_date < $cutoff_day
RETURN div.id AS dividend_id,
       div.declaration_date AS declaration_date,
       div.ex_dividend_date AS ex_dividend_date,
       div.cash_amount AS cash_amount,
       div.currency AS currency,
       div.frequency AS frequency,
       div.dividend_type AS dividend_type,
       div.pay_date AS pay_date,
       div.record_date AS record_date
ORDER BY div.declaration_date
"""

QUERY_IQ_SPLITS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_SPLIT]->(sp:Split)
WHERE sp.execution_date > $prev_day
  AND sp.execution_date < $cutoff_day
RETURN sp.id AS split_id,
       sp.execution_date AS execution_date,
       sp.split_from AS split_from,
       sp.split_to AS split_to
ORDER BY sp.execution_date
"""

QUERY_IQ_COMPANY_CONTEXT = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)
OPTIONAL MATCH (ind)-[:BELONGS_TO]->(sec:Sector)
RETURN ind.name AS industry_name,
       sec.name AS sector_name
"""

# --- Inter-quarter helper functions ---


def _iq_parse_json_field(raw, fallback=None):
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _norm_ret(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return round(f, 2)


def _fmt_vol(v):
    if v is None:
        return '?'
    if v == int(v):
        return f'{int(v):,}'
    return f'{v:,.2f}'


def _fmt_txn(v):
    if v is None:
        return '?'
    return f'{int(v):,}'


def _safe_adj(a, b):
    if a is None or b is None:
        return None
    return round(a - b, 2)


def _event_ref(event_type, native_id):
    return f'{event_type}:{native_id}'


def _day_from_ts(ts):
    return str(ts)[:10] if ts else None


def _build_forward_returns(created, market_session_val, returns_schedule_raw, metrics,
                           session_helper, context_cutoff_ts):
    """Build forward returns for a news or filing event.

    Returns are nulled for any horizon whose window end extends past context_cutoff_ts.
    This is the PIT safety gate — it prevents return values from capturing the
    current earnings reaction even when the event itself is legitimately pre-cutoff.
    """
    schedule = _iq_parse_json_field(returns_schedule_raw, {}) or {}

    hourly_start = session_helper.get_interval_start_time(created)
    hourly_end = schedule.get('hourly') or session_helper.get_interval_end_time(
        created, 60, respect_session_boundary=False
    ).isoformat()

    session_start = session_helper.get_start_time(created)
    session_end = schedule.get('session') or session_helper.get_end_time(created).isoformat()

    daily_start, daily_end_fallback = session_helper.get_1d_impact_times(created)
    daily_end = schedule.get('daily') or daily_end_fallback.isoformat()

    def pack(prefix, start_ts, end_ts):
        stock = _norm_ret(metrics.get(f'{prefix}_stock'))
        sector = _norm_ret(metrics.get(f'{prefix}_sector'))
        industry = _norm_ret(metrics.get(f'{prefix}_industry'))
        macro = _norm_ret(metrics.get(f'{prefix}_macro'))
        return {
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'stock': stock,
            'sector': sector,
            'industry': industry,
            'macro': macro,
            'adj_macro': _safe_adj(stock, macro),
            'adj_sector': _safe_adj(stock, sector),
            'adj_industry': _safe_adj(stock, industry),
        }

    result = {}
    for horizon, prefix, start_ts, end_ts in [
        ('hourly', 'hourly', hourly_start.isoformat(), hourly_end),
        ('session', 'session', session_start.isoformat(), session_end),
        ('daily', 'daily', daily_start.isoformat(), daily_end),
    ]:
        # PIT safety: null the entire horizon if its window extends past the cutoff
        if str(end_ts) > context_cutoff_ts:
            result[horizon] = None
        else:
            result[horizon] = pack(prefix, start_ts, end_ts)

    return result


def _cutoff_boundary_price_role(context_cutoff_ts):
    """Determine if the cutoff boundary day's close-to-close price is within-window.

    Rule: ordinary if cutoff time >= 16:00 (market close), reference_only otherwise.
    No MarketSessionClassifier needed — pure timestamp check.
    """
    hour = int(context_cutoff_ts[11:13])
    return 'ordinary' if hour >= 16 else 'reference_only'


def _best_safe_horizon(forward_returns):
    """Return the best safe horizon dict for compact news rendering.

    Priority: daily (most informative) -> session -> hourly.
    Returns (horizon_name, horizon_dict) or (None, None) if all null.
    """
    if forward_returns is None:
        return None, None
    for name in ('daily', 'session', 'hourly'):
        h = forward_returns.get(name)
        if h is not None and h.get('stock') is not None:
            return name, h
    return None, None


def _report_summary(form_type, items, description, accession):
    """Render label for report event. Always prepend [form_type]."""
    text = None
    if items:
        text = items[0]
    if not text and description:
        text = description
    if not text:
        text = accession
    return f'[{form_type}] {text}'


# --- Rendered text helpers ---


def _render_window_label_news(start_ts, end_ts):
    """Compact HH:MM->HH:MM for news react lines (no date prefix)."""
    s_time = str(start_ts)[11:16]
    e_time = str(end_ts)[11:16]
    return f'({s_time}->{e_time})'


def _render_window_label_filing(start_ts, end_ts, event_date, horizon):
    """Detailed window label for filing horizon lines.

    - Daily: MM/DD close->MM/DD close
    - Hourly/session: HH:MM or MM/DD HH:MM when cross-day
    """
    s_day = str(start_ts)[:10]
    e_day = str(end_ts)[:10]
    s_time = str(start_ts)[11:16]
    e_time = str(end_ts)[11:16]

    if horizon == 'daily':
        s_label = f'{s_day[5:7]}/{s_day[8:10]} close'
        e_label = f'{e_day[5:7]}/{e_day[8:10]} close'
        return f'({s_label}->{e_label})'

    # For hourly/session: add date prefix when cross-day
    if s_day != event_date:
        s_label = f'{s_day[5:7]}/{s_day[8:10]} {s_time}'
    else:
        s_label = s_time
    if e_day != s_day:
        e_label = f'{e_day[5:7]}/{e_day[8:10]} {e_time}'
    else:
        e_label = e_time
    return f'({s_label}->{e_label})'


def _render_horizon_line_filing(horizon_name, h, event_date):
    """Render one filing horizon line: stock, sector, industry, SPY, adj_macro, window."""
    if h is None:
        return f'  {horizon_name:7s} (nulled -- window extends past cutoff)'
    if h.get('stock') is None:
        return None  # skip this horizon
    parts = [f'{horizon_name:7s} stock {h["stock"]:+.2f}%']
    if h.get('sector') is not None:
        parts.append(f'sector {h["sector"]:+.2f}%')
    if h.get('industry') is not None:
        parts.append(f'industry {h["industry"]:+.2f}%')
    if h.get('macro') is not None:
        parts.append(f'SPY {h["macro"]:+.2f}%')
    if h.get('adj_macro') is not None:
        parts.append(f'adj_macro {h["adj_macro"]:+.2f}%')
    wl = _render_window_label_filing(h['start_ts'], h['end_ts'], event_date, horizon_name)
    parts.append(wl)
    return '  ' + ' | '.join(parts)


def _render_news_react_line(forward_returns):
    """Render one compact react: line for news using best safe horizon."""
    h_name, h = _best_safe_horizon(forward_returns)
    if h_name is None:
        return None
    parts = [f'{h_name} stock {h["stock"]:+.2f}%']
    if h.get('macro') is not None:
        parts.append(f'SPY {h["macro"]:+.2f}%')
    if h.get('adj_macro') is not None:
        parts.append(f'adj_macro {h["adj_macro"]:+.2f}%')
    wl = _render_window_label_news(h['start_ts'], h['end_ts'])
    parts.append(wl)
    return '  react: ' + ' | '.join(parts)


def render_inter_quarter_text(packet):
    """Render canonical JSON into compact text timeline for LLM prompt."""
    ticker = packet['ticker']
    s = packet['summary']
    lines = []

    # Header
    lines.append(f'=== INTER-QUARTER TIMELINE: {ticker} ===')
    lines.append(f'Industry: {packet.get("industry") or "?"} | Sector: {packet.get("sector") or "?"}')
    lines.append(
        f'{s["trading_days_ordinary"]} ordinary trading days | '
        f'{s["boundary_days_rendered"]} boundary days | '
        f'{s["total_news"]} news | {s["total_filings"]} filings | '
        f'{s["total_dividends"]} dividends | {s["total_splits"]} splits'
    )
    lines.append(f'{s["significant_move_days"]} significant move days | {s["gap_days"]} gap days')
    lines.append('')
    lines.append('Legend:')
    lines.append('pre_market  = session -> 09:35, daily = prior close -> same-day close')
    lines.append('in_market   = session -> same-day close, daily = prior close -> same-day close')
    lines.append('post_market = session -> next-day 09:35, daily = same-day close -> next-day close')
    lines.append('market_closed = exact windows shown explicitly when they differ')

    for day in packet['days']:
        lines.append('')
        d = day['date']
        br = day.get('boundary_role')
        pr = day.get('price_role', 'ordinary')
        is_td = day.get('is_trading_day', False)
        price = day.get('price')

        # --- Day header ---
        if br == 'prev_boundary':
            lines.append(f'{d} | boundary day after previous earnings')
            prev_time = packet['prev_8k_ts'][11:19]
            lines.append(f'  previous 8-K filed at {prev_time}; only later timestamped events are included')
            if price:
                dr = price.get('daily_return')
                sr = day.get('spy_return')
                dr_s = f'{dr:+.2f}%' if dr is not None else '?'
                sr_s = f'{sr:+.2f}%' if sr is not None else '?'
                lines.append(f'  same-day close-to-close ({dr_s} vs SPY {sr_s}) is reference only')

        elif br == 'cutoff_boundary':
            cutoff_time = packet['context_cutoff_ts'][11:19]
            lines.append(f'{d} | cutoff boundary (context cutoff at {cutoff_time})')
            lines.append(f'  only events before cutoff are included')
            if pr == 'ordinary':
                lines.append(f'  same-day close-to-close is fully pre-cutoff and therefore within-window')
                if price:
                    dr = price.get('daily_return')
                    sr = day.get('spy_return')
                    adj = day.get('adj_return')
                    dr_s = f'{dr:+.2f}%' if dr is not None else '?'
                    sr_s = f'{sr:+.2f}%' if sr is not None else '?'
                    adj_s = f'{adj:+.2f}%' if adj is not None else '?'
                    lines.append(f'  {ticker} {dr_s} vs SPY {sr_s} | adj {adj_s}')
            else:
                lines.append(f'  same-day close-to-close extends past cutoff and is reference only')

        elif not is_td:
            lines.append(f'{d} | non-trading event day')

        else:
            # Ordinary trading day
            dr = price.get('daily_return') if price else None
            sr = day.get('spy_return')
            adj = day.get('adj_return')
            dr_s = f'{dr:+.2f}%' if dr is not None else '?'
            sr_s = f'{sr:+.2f}%' if sr is not None else '?'
            adj_s = f'{adj:+.2f}%' if adj is not None else '?'
            header = f'{d} | {ticker} {dr_s} vs SPY {sr_s} | adj {adj_s}'
            if day.get('is_significant'):
                header += '  ***'
            if day.get('is_gap_day'):
                header += '  GAP'
            lines.append(header)
            if price:
                lines.append(f'  open={price["open"]}  high={price["high"]}  low={price["low"]}  close={price["close"]}')
                lines.append(f'  vol={_fmt_vol(price.get("volume"))}  vwap={price.get("vwap")}  txns={_fmt_txn(price.get("transactions"))}')
                sec_ret = day.get('sector_return')
                ind_ret = day.get('industry_return')
                bench_parts = []
                if sec_ret is not None:
                    bench_parts.append(f'Sector {sec_ret:+.2f}%')
                if ind_ret is not None:
                    bench_parts.append(f'Industry {ind_ret:+.2f}%')
                if bench_parts:
                    lines.append(f'  {" | ".join(bench_parts)}')

        # --- Events ---
        events = day.get('events', [])
        if not events and is_td and br is None and day.get('is_gap_day'):
            lines.append('')
            lines.append('  (no news, no filings)')
        for ev in events:
            lines.append('')
            etype = ev['type']
            if etype == 'news':
                ts_time = str(ev['created'])[11:16]
                ms = ev.get('market_session', '')
                ref = ev['event_ref']
                title = ev.get('title', '')
                header = f'  {ts_time} {ms} | {ref} | {title}'
                channels = ev.get('channels', [])
                if channels:
                    header += f' [{", ".join(channels)}]'
                lines.append(header)
                react = _render_news_react_line(ev.get('forward_returns'))
                if react:
                    lines.append(f'  {react.strip()}')

            elif etype == 'filing':
                ts_time = str(ev['created'])[11:16]
                ms = ev.get('market_session', '')
                ref = ev['event_ref']
                summary = _report_summary(
                    ev.get('form_type', '?'),
                    ev.get('items', []),
                    ev.get('description'),
                    ev.get('accession', '?')
                )
                lines.append(f'  {ts_time} {ms} | {ref} | {summary}')
                # Detail line 1: accession + period + amendment
                det1 = f'    accession: {ev.get("accession", "?")}'
                if ev.get('period_of_report'):
                    det1 += f' | period: {ev["period_of_report"]}'
                if ev.get('is_amendment'):
                    det1 += ' | amendment'
                lines.append(det1)
                # Detail line 2: sections + exhibits
                sn = ev.get('section_names', [])
                ek = ev.get('exhibit_keys', [])
                det2 = f'    sections: {len(sn)}'
                if ek:
                    det2 += f' | exhibits: {", ".join(ek)}'
                else:
                    det2 += ' | exhibits: none'
                lines.append(det2)
                # Horizon lines (all 3 for filings)
                ev_date = str(ev['created'])[:10]
                fr = ev.get('forward_returns') or {}
                for h_name in ('hourly', 'session', 'daily'):
                    h = fr.get(h_name)
                    if h is None and h_name in fr:
                        # Horizon was explicitly nulled by PIT safety
                        lines.append(f'    {h_name:7s} (nulled -- window extends past cutoff)')
                    elif h is None:
                        continue  # horizon not present at all
                    else:
                        hl = _render_horizon_line_filing(h_name, h, ev_date)
                        if hl:
                            lines.append(f'  {hl.strip()}')

            elif etype == 'dividend':
                ref = ev['event_ref']
                amt = ev.get('cash_amount', '?')
                cur = ev.get('currency', '')
                freq = ev.get('frequency', '')
                lines.append(f'  date-only | {ref} | Dividend declared: ${amt} {cur} {freq}'.rstrip())
                ex_d = ev.get('ex_dividend_date', '?')
                pay_d = ev.get('pay_date', '?')
                dtype = ev.get('dividend_type', '?')
                lines.append(f'    ex-date {ex_d} | pay-date {pay_d} | type {dtype}')

            elif etype == 'split':
                ref = ev['event_ref']
                ratio = ev.get('ratio_text', '?')
                lines.append(f'  date-only | {ref} | Split effective: {ratio}')

    return '\n'.join(lines)


def build_inter_quarter_context(ticker, prev_8k_ts, context_cutoff_ts,
                                out_path=None, context_cutoff_reason=None):
    """Build inter-quarter context timeline artifact (inter_quarter_context.v1).

    Args:
        ticker: Company ticker (e.g. 'CRM')
        prev_8k_ts: ISO8601 timestamp of previous earnings 8-K
        context_cutoff_ts: Upper bound for event inclusion (exclusive)
        out_path: Output file path (default: /tmp/earnings_inter_quarter_{ticker}.json)
        context_cutoff_reason: Optional metadata label (e.g. 'historical_release_session_floor')

    Returns:
        (out_path, rendered_text)
    """
    from utils.market_session import MarketSessionClassifier

    # 1. Parse inputs
    prev_day = prev_8k_ts[:10]
    cutoff_day = context_cutoff_ts[:10]
    if out_path is None:
        out_path = f'/tmp/earnings_inter_quarter_{ticker}.json'

    # 2. Initialize helpers
    session_helper = MarketSessionClassifier()

    manager = get_manager()
    try:
        # 3. Query
        print(f'Querying inter-quarter data for {ticker} ({prev_day} -> {cutoff_day})...')

        price_rows = manager.execute_cypher_query_all(QUERY_IQ_PRICES, {
            'ticker': ticker, 'prev_day': prev_day, 'cutoff_day': cutoff_day
        })
        print(f'  prices: {len(price_rows)} trading days')

        news_rows = manager.execute_cypher_query_all(QUERY_IQ_NEWS, {
            'ticker': ticker, 'prev_8k_ts': prev_8k_ts, 'context_cutoff_ts': context_cutoff_ts
        })
        print(f'  news: {len(news_rows)} events')

        filing_rows = manager.execute_cypher_query_all(QUERY_IQ_FILINGS, {
            'ticker': ticker, 'prev_8k_ts': prev_8k_ts, 'context_cutoff_ts': context_cutoff_ts
        })
        print(f'  filings: {len(filing_rows)} events')

        div_rows = manager.execute_cypher_query_all(QUERY_IQ_DIVIDENDS, {
            'ticker': ticker, 'prev_day': prev_day, 'cutoff_day': cutoff_day
        })
        print(f'  dividends: {len(div_rows)} events')

        split_rows = manager.execute_cypher_query_all(QUERY_IQ_SPLITS, {
            'ticker': ticker, 'prev_day': prev_day, 'cutoff_day': cutoff_day
        })
        print(f'  splits: {len(split_rows)} events')

        # 4. Build base day_map from price rows
        day_map = {}
        top_sector = None
        top_industry = None

        for row in price_rows:
            d = str(row['date'])
            dr = row.get('daily_return')
            sr = row.get('spy_return')
            day_map[d] = {
                'date': d,
                'is_trading_day': True,
                'boundary_role': None,
                'price_role': 'ordinary',
                'price': {
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'daily_return': dr,
                    'volume': row.get('volume'),
                    'vwap': row.get('vwap'),
                    'transactions': row.get('transactions'),
                    'timestamp': row.get('price_timestamp'),
                },
                'spy_return': sr,
                'sector_return': row.get('sector_return'),
                'industry_return': row.get('industry_return'),
                'adj_return': _safe_adj(dr, sr),
                'is_significant': None,
                'is_gap_day': None,
                'events': [],
            }
            if top_sector is None and row.get('sector_name'):
                top_sector = row['sector_name']
            if top_industry is None and row.get('industry_name'):
                top_industry = row['industry_name']

        # Company context fallback
        if top_sector is None or top_industry is None:
            ctx_rows = manager.execute_cypher_query_all(QUERY_IQ_COMPANY_CONTEXT, {'ticker': ticker})
            if ctx_rows:
                if top_industry is None:
                    top_industry = ctx_rows[0].get('industry_name')
                if top_sector is None:
                    top_sector = ctx_rows[0].get('sector_name')

        # 5. Ensure boundary day entries exist
        for bd in [prev_day, cutoff_day]:
            if bd not in day_map:
                day_map[bd] = {
                    'date': bd,
                    'is_trading_day': False,
                    'boundary_role': None,
                    'price_role': 'ordinary',
                    'price': None,
                    'spy_return': None,
                    'sector_return': None,
                    'industry_return': None,
                    'adj_return': None,
                    'is_significant': None,
                    'is_gap_day': None,
                    'events': [],
                }

        # 6. Mark boundary roles
        day_map[prev_day]['boundary_role'] = 'prev_boundary'
        day_map[cutoff_day]['boundary_role'] = 'cutoff_boundary'

        # 7. Set price roles
        if day_map[prev_day]['is_trading_day']:
            day_map[prev_day]['price_role'] = 'reference_only'
        cutoff_pr = _cutoff_boundary_price_role(context_cutoff_ts)
        if day_map[cutoff_day]['is_trading_day']:
            day_map[cutoff_day]['price_role'] = cutoff_pr

        # 8. Merge news events
        for row in news_rows:
            created = str(row['created'])
            day_key = created[:10]
            channels = _iq_parse_json_field(row.get('channels'), [])
            authors = _iq_parse_json_field(row.get('authors'), [])
            tags = _iq_parse_json_field(row.get('tags'), [])
            rs_raw = row.get('returns_schedule')
            metrics = {k: row.get(k) for k in [
                'hourly_stock', 'session_stock', 'daily_stock',
                'hourly_sector', 'session_sector', 'daily_sector',
                'hourly_industry', 'session_industry', 'daily_industry',
                'hourly_macro', 'session_macro', 'daily_macro',
            ]}
            fr = _build_forward_returns(created, row.get('market_session'), rs_raw,
                                        metrics, session_helper, context_cutoff_ts)
            ev = {
                'event_ref': _event_ref('news', row['news_id']),
                'type': 'news',
                'available_precision': 'timestamp',
                'created': created,
                'market_session': row.get('market_session'),
                'title': row.get('title'),
                'channels': channels,
                'forward_returns': fr,
                # JSON-only fields
                'id': row.get('news_id'),
                'url': row.get('url'),
                'authors': authors,
                'tags': tags,
                'updated': row.get('updated'),
                'returns_schedule_raw': rs_raw,
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 9. Merge filing events
        for row in filing_rows:
            created = str(row['created'])
            day_key = created[:10]
            items = _iq_parse_json_field(row.get('items'), [])
            exhibits_parsed = _iq_parse_json_field(row.get('exhibits'), {})
            exhibit_keys = sorted(exhibits_parsed.keys()) if isinstance(exhibits_parsed, dict) else []
            rs_raw = row.get('returns_schedule')
            section_names = sorted([s for s in (row.get('section_names') or []) if s])
            metrics = {k: row.get(k) for k in [
                'hourly_stock', 'session_stock', 'daily_stock',
                'hourly_sector', 'session_sector', 'daily_sector',
                'hourly_industry', 'session_industry', 'daily_industry',
                'hourly_macro', 'session_macro', 'daily_macro',
            ]}
            fr = _build_forward_returns(created, row.get('market_session'), rs_raw,
                                        metrics, session_helper, context_cutoff_ts)
            ev = {
                'event_ref': _event_ref('report', row['accession']),
                'type': 'filing',
                'available_precision': 'timestamp',
                'created': created,
                'market_session': row.get('market_session'),
                'form_type': row.get('form_type'),
                'accession': row.get('accession'),
                'period_of_report': row.get('period_of_report'),
                'is_amendment': row.get('is_amendment'),
                'description': row.get('description'),
                'items': items,
                'exhibit_keys': exhibit_keys,
                'forward_returns': fr,
                # JSON-only fields
                'report_id': row.get('report_id'),
                'filing_links': {
                    'primary_doc_url': row.get('primary_doc_url'),
                    'link_to_txt': row.get('link_to_txt'),
                    'link_to_html': row.get('link_to_html'),
                    'link_to_filing_details': row.get('link_to_filing_details'),
                },
                'section_names': section_names,
                'has_filing_text': row.get('has_filing_text'),
                'xbrl_status': row.get('xbrl_status'),
                'financial_statement_count': row.get('financial_statement_count'),
                'returns_schedule_raw': rs_raw,
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 10. Merge dividends
        for row in div_rows:
            day_key = str(row['declaration_date'])
            ev = {
                'event_ref': _event_ref('dividend', row['dividend_id']),
                'type': 'dividend',
                'available_precision': 'date',
                'event_day': day_key,
                'declaration_date': day_key,
                'ex_dividend_date': row.get('ex_dividend_date'),
                'cash_amount': row.get('cash_amount'),
                'currency': row.get('currency'),
                'frequency': row.get('frequency'),
                'dividend_type': row.get('dividend_type'),
                'forward_returns': None,
                # JSON-only
                'id': row.get('dividend_id'),
                'pay_date': row.get('pay_date'),
                'record_date': row.get('record_date'),
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 11. Merge splits
        for row in split_rows:
            day_key = str(row['execution_date'])
            sf = row.get('split_from')
            st = row.get('split_to')
            ev = {
                'event_ref': _event_ref('split', row['split_id']),
                'type': 'split',
                'available_precision': 'date',
                'event_day': day_key,
                'execution_date': day_key,
                'split_from': sf,
                'split_to': st,
                'ratio_text': f'{sf}:{st}',
                'forward_returns': None,
                # JSON-only
                'id': row.get('split_id'),
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 12. Remove empty non-trading non-boundary days (synthetic entries with no events)
        # (Steps 8-11 already created synthetic entries only when events exist)

        # 13. Sort events within each day
        type_order = {'filing': 0, 'news': 1, 'dividend': 2, 'split': 3}
        for day in day_map.values():
            day['events'].sort(key=lambda e: (
                0 if e.get('available_precision') == 'timestamp' else 1,
                str(e.get('created', 'zzzz')),
                type_order.get(e['type'], 9),
            ))

        # 14. Compute ordinary-day significance markers
        for day in day_map.values():
            br = day['boundary_role']
            pr = day['price_role']
            if day['is_trading_day'] and (
                (br is None and pr == 'ordinary') or
                (br == 'cutoff_boundary' and pr == 'ordinary')
            ):
                adj = day['adj_return']
                if adj is not None:
                    day['is_significant'] = abs(adj) >= 2.0
                    news_count = sum(1 for e in day['events'] if e['type'] == 'news')
                    filing_count = sum(1 for e in day['events'] if e['type'] == 'filing')
                    day['is_gap_day'] = day['is_significant'] and news_count == 0 and filing_count == 0
                else:
                    day['is_significant'] = False
                    day['is_gap_day'] = False

        # Build sorted day list and remove days with no events and no price (non-boundary)
        sorted_days = []
        for d in sorted(day_map.keys()):
            day = day_map[d]
            # Keep if: has events, has price, or is a boundary day
            if day['events'] or day['price'] is not None or day['boundary_role'] is not None:
                sorted_days.append(day)

        # 15. Build summary counts
        total_news = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'news')
        total_filings = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'filing')
        total_dividends = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'dividend')
        total_splits = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'split')
        trading_ordinary = sum(1 for day in sorted_days if day['is_trading_day'] and day['boundary_role'] is None)
        boundary_rendered = sum(1 for day in sorted_days if day['boundary_role'] is not None)
        non_trading_event = sum(1 for day in sorted_days if not day['is_trading_day'])
        sig_days = sum(1 for day in sorted_days if day.get('is_significant') is True)
        gap_days = sum(1 for day in sorted_days if day.get('is_gap_day') is True)

        summary = {
            'total_day_blocks': len(sorted_days),
            'trading_days_ordinary': trading_ordinary,
            'boundary_days_rendered': boundary_rendered,
            'non_trading_event_days': non_trading_event,
            'significant_move_days': sig_days,
            'gap_days': gap_days,
            'total_news': total_news,
            'total_filings': total_filings,
            'total_dividends': total_dividends,
            'total_splits': total_splits,
        }

        # 16. Assemble and write canonical JSON
        packet = {
            'schema_version': 'inter_quarter_context.v1',
            'ticker': ticker,
            'prev_8k_ts': prev_8k_ts,
            'context_cutoff_ts': context_cutoff_ts,
            'context_cutoff_reason': context_cutoff_reason,
            'prev_day': prev_day,
            'cutoff_day': cutoff_day,
            'industry': top_industry,
            'sector': top_sector,
            'days': sorted_days,
            'summary': summary,
            'assembled_at': datetime.now(timezone.utc).isoformat(),
        }

        out_dir = os.path.dirname(out_path) or '.'
        os.makedirs(out_dir, exist_ok=True)
        tmp_path = out_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(packet, f, default=str, indent=2)
        os.replace(tmp_path, out_path)

        # 17. Render text from JSON
        rendered = render_inter_quarter_text(packet)
        print(rendered)
        print(f'\ninter_quarter_context.v1: {len(sorted_days)} days, '
              f'{total_news} news, {total_filings} filings, '
              f'{total_dividends} dividends, {total_splits} splits → {out_path}')

        return out_path, rendered

    finally:
        manager.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: warmup_cache.py TICKER [--transcript TID | --mda ACCESSION | --8k ACCESSION | --8k-packet ACCESSION | --guidance-history | --inter-quarter] [--pit ISO8601] [--out-path PATH]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1]

    if '--inter-quarter' in sys.argv:
        prev_8k = None
        context_cutoff = None
        out_path = None

        if '--prev-8k' not in sys.argv:
            print('Error: --inter-quarter requires --prev-8k', file=sys.stderr)
            sys.exit(1)
        if '--context-cutoff' not in sys.argv:
            print('Error: --inter-quarter requires --context-cutoff', file=sys.stderr)
            sys.exit(1)

        pidx = sys.argv.index('--prev-8k')
        if pidx + 1 >= len(sys.argv):
            print('Error: --prev-8k requires ISO8601 argument', file=sys.stderr)
            sys.exit(1)
        prev_8k = sys.argv[pidx + 1]

        cidx = sys.argv.index('--context-cutoff')
        if cidx + 1 >= len(sys.argv):
            print('Error: --context-cutoff requires ISO8601 argument', file=sys.stderr)
            sys.exit(1)
        context_cutoff = sys.argv[cidx + 1]

        if '--out-path' in sys.argv:
            oidx = sys.argv.index('--out-path')
            if oidx + 1 >= len(sys.argv):
                print('Error: --out-path requires PATH argument', file=sys.stderr)
                sys.exit(1)
            out_path = sys.argv[oidx + 1]

        cutoff_reason = None
        if '--cutoff-reason' in sys.argv:
            ridx = sys.argv.index('--cutoff-reason')
            if ridx + 1 >= len(sys.argv):
                print('Error: --cutoff-reason requires argument', file=sys.stderr)
                sys.exit(1)
            cutoff_reason = sys.argv[ridx + 1]

        build_inter_quarter_context(ticker, prev_8k, context_cutoff, out_path, cutoff_reason)

    elif '--guidance-history' in sys.argv:
        pit = None
        if '--pit' in sys.argv:
            pit_idx = sys.argv.index('--pit')
            if pit_idx + 1 >= len(sys.argv):
                print("Error: --pit requires ISO8601 argument", file=sys.stderr)
                sys.exit(1)
            pit = sys.argv[pit_idx + 1]
        out_path = None
        if '--out-path' in sys.argv:
            op_idx = sys.argv.index('--out-path')
            if op_idx + 1 >= len(sys.argv):
                print("Error: --out-path requires PATH argument", file=sys.stderr)
                sys.exit(1)
            out_path = sys.argv[op_idx + 1]
        build_guidance_history(ticker, pit, out_path)
    elif '--transcript' in sys.argv:
        idx = sys.argv.index('--transcript')
        if idx + 1 >= len(sys.argv):
            print("Error: --transcript requires TRANSCRIPT_ID argument", file=sys.stderr)
            sys.exit(1)
        run_transcript(ticker, sys.argv[idx + 1])
    elif '--mda' in sys.argv:
        idx = sys.argv.index('--mda')
        if idx + 1 >= len(sys.argv):
            print("Error: --mda requires ACCESSION argument", file=sys.stderr)
            sys.exit(1)
        run_mda(sys.argv[idx + 1])
    elif '--8k-packet' in sys.argv:
        idx = sys.argv.index('--8k-packet')
        if idx + 1 >= len(sys.argv):
            print("Error: --8k-packet requires ACCESSION argument", file=sys.stderr)
            sys.exit(1)
        accession = sys.argv[idx + 1]
        out_path = None
        if '--out-path' in sys.argv:
            op_idx = sys.argv.index('--out-path')
            if op_idx + 1 >= len(sys.argv):
                print("Error: --out-path requires PATH argument", file=sys.stderr)
                sys.exit(1)
            out_path = sys.argv[op_idx + 1]
        build_8k_packet(accession, ticker, out_path)
    elif '--8k' in sys.argv:
        idx = sys.argv.index('--8k')
        if idx + 1 >= len(sys.argv):
            print("Error: --8k requires ACCESSION argument", file=sys.stderr)
            sys.exit(1)
        run_8k(sys.argv[idx + 1])
    else:
        run_warmup(ticker)


if __name__ == '__main__':
    main()
