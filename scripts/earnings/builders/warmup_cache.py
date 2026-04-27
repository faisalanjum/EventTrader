#!/usr/bin/env python3
"""Pre-fetch extraction caches AND facade for earnings-orchestration builders.

This module owns:
  - Extraction CLI modes: run_warmup, run_transcript, run_mda, run_8k
  - Extraction Cypher: QUERY_2A, QUERY_2B, QUERY_MEMBER_MAP, QUERY_3B, QUERY_5B
  - _build_member_map (CIK-based member lookup)
  - main() — CLI dispatcher (8 modes)

And it re-exports (for back-compat with adapters, the .claude shim, and
existing tests) every symbol relocated to the three domain modules:
  - scripts.earnings.builders.eight_k_packet
  - scripts.earnings.builders.guidance_history
  - scripts.earnings.builders.inter_quarter_context

Identity contract: every re-exported symbol resolves to the SAME Python
object (Python `is`) as its canonical-domain counterpart. Verified by
test_builders_warmup_split.py and test_builders_imports.py. DO NOT replace
the re-export block with wrapper functions — that would silently break
the identity invariant.

Usage:
    warmup_cache.py TICKER                                   # 2A + 2B + MEMBER_MAP cache
    warmup_cache.py TICKER --transcript TRANSCRIPT_ID        # transcript content (3B)
    warmup_cache.py TICKER --mda ACCESSION                   # MD&A content (5B)
    warmup_cache.py TICKER --8k ACCESSION                    # 8-K sections + EX-99 (run_8k)
    warmup_cache.py TICKER --8k-packet ACCESSION             # 8k_packet.v1 (build_8k_packet)
    warmup_cache.py TICKER --guidance-history [--pit ISO]    # guidance_history.v1
    warmup_cache.py TICKER --inter-quarter --prev-8k ISO --context-cutoff ISO
    warmup_cache.py --test                                   # _run_v2_regression_tests

Output paths under /tmp/earnings_*/transcript_*/mda_*/8k_content_*. See
scripts/earnings/builders/{eight_k_packet,guidance_history,inter_quarter_context}.py
for the orchestration packet schemas.
"""

import json
import os
import sys

from ._paths import ensure_legacy_paths
ensure_legacy_paths()

from neograph.Neo4jConnection import get_manager

# ── Domain-module re-exports — back-compat for adapters, tests, .claude shim ──
# Stage 1.2: 8-K packet domain (eight_k_packet.py)
from .eight_k_packet import (
    build_8k_packet,
    _fetch_8k_core,
    QUERY_4J,
    QUERY_4K,
    QUERY_4G_META,
    QUERY_4K_OTHER_PREVIEW,
    QUERY_4F,
)
# Stage 2.2: guidance history domain (guidance_history.py)
from .guidance_history import (
    build_guidance_history,
    render_guidance_text,
    resolve_unit_groups,
    _format_value,
    _extract_given_day,
    _normalize_qualitative,
    _SOURCE_PRIORITY,
    QUERY_GUIDANCE_HISTORY,
    QUERY_GUIDANCE_HISTORY_PIT,
    _run_v2_regression_tests,
)
# Stage 3.2: inter-quarter context domain (inter_quarter_context.py)
from .inter_quarter_context import (
    build_inter_quarter_context,
    render_inter_quarter_text,
    _parse_dt_for_pit,
    _is_price_pit_safe,
    _build_forward_returns,
    _iq_parse_json_field,
    _norm_ret,
    _fmt_vol,
    _fmt_txn,
    _safe_adj,
    _event_ref,
    _day_from_ts,
    _cutoff_boundary_price_role,
    _best_safe_horizon,
    _report_summary,
    _render_window_label_news,
    _render_window_label_filing,
    _render_horizon_line_filing,
    _render_news_react_line,
    QUERY_IQ_PRICES,
    QUERY_IQ_NEWS,
    QUERY_IQ_FILINGS,
    QUERY_IQ_DIVIDENDS,
    QUERY_IQ_SPLITS,
    QUERY_IQ_COMPANY_CONTEXT,
)

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


# _fetch_8k_core re-exported from .eight_k_packet — same object, used by build_8k_packet too
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

        packet = build_inter_quarter_context(ticker, prev_8k, context_cutoff, out_path, cutoff_reason)
        rendered = render_inter_quarter_text(packet)
        print(rendered)
        summary = packet.get('summary', {})
        print(f'\ninter_quarter_context.v1: {summary.get("total_day_blocks", 0)} days, '
              f'{summary.get("total_news", 0)} news, {summary.get("total_filings", 0)} filings, '
              f'{summary.get("total_dividends", 0)} dividends, {summary.get("total_splits", 0)} splits → {out_path or f"/tmp/earnings_inter_quarter_{ticker}.json"}')

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
        packet = build_guidance_history(ticker, pit, out_path)
        text = render_guidance_text(packet)
        print(text)
        summary = packet.get('summary', {})
        print(f'\nguidance_history.v1: {summary.get("total_series", 0)} series, '
              f'{summary.get("total_updates_raw", 0)} raw → {summary.get("total_updates_collapsed", 0)} collapsed → {out_path or f"/tmp/earnings_guidance_{ticker}.json"}')
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
        packet = build_8k_packet(accession, ticker, out_path)
        sections = packet.get('sections', [])
        exhibits_99 = packet.get('exhibits_99', [])
        exhibits_other = packet.get('exhibits_other', [])
        sec_total = sum(len(s.get('content', '')) for s in sections)
        ex99_total = sum(len(e.get('content', '')) for e in exhibits_99)
        print(f'8k_packet.v1: {len(sections)} sections ({sec_total // 1000}KB) + '
              f'{len(exhibits_99)} EX-99 ({ex99_total // 1000}KB) + '
              f'{len(exhibits_other)} other exhibits'
              f'{" + filing_text fallback" if packet.get("filing_text") else ""}'
              f' → {out_path or f"/tmp/earnings_8k_packet_{accession}.json"}')
    elif '--8k' in sys.argv:
        idx = sys.argv.index('--8k')
        if idx + 1 >= len(sys.argv):
            print("Error: --8k requires ACCESSION argument", file=sys.stderr)
            sys.exit(1)
        run_8k(sys.argv[idx + 1])
    else:
        run_warmup(ticker)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(0 if _run_v2_regression_tests() else 1)
    main()
