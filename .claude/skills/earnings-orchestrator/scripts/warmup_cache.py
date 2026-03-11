#!/usr/bin/env python3
"""Pre-fetch extraction caches and transcript content via direct Bolt connection.

Eliminates agent transcription errors (E1) and MCP persisted-output truncation (E4)
by running queries verbatim from a script instead of through MCP.

Usage:
    warmup_cache.py TICKER                           # Runs queries 2A + 2B
    warmup_cache.py TICKER --transcript TRANSCRIPT_ID # Runs query 3B

Outputs:
    /tmp/concept_cache_{TICKER}.json                  (query 2A)
    /tmp/member_cache_{TICKER}.json                   (query 2B)
    /tmp/transcript_content_{TRANSCRIPT_ID}.json      (query 3B, --transcript mode)
"""

import json
import sys

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


def main():
    if len(sys.argv) < 2:
        print("Usage: warmup_cache.py TICKER [--transcript TRANSCRIPT_ID]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1]

    if '--transcript' in sys.argv:
        idx = sys.argv.index('--transcript')
        if idx + 1 >= len(sys.argv):
            print("Error: --transcript requires TRANSCRIPT_ID argument", file=sys.stderr)
            sys.exit(1)
        run_transcript(ticker, sys.argv[idx + 1])
    else:
        run_warmup(ticker)


if __name__ == '__main__':
    main()
