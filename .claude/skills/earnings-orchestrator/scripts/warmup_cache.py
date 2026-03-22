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


def main():
    if len(sys.argv) < 2:
        print("Usage: warmup_cache.py TICKER [--transcript TID | --mda ACCESSION | --8k ACCESSION | --8k-packet ACCESSION | --guidance-history] [--pit ISO8601] [--out-path PATH]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1]

    if '--guidance-history' in sys.argv:
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
