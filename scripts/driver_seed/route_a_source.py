"""THE durable read-only Fiscal Route-A source adapter (Phase 1 corrective item 4).

Builds ONE locate()-ready source dict per accession from the ACTUAL graph — Facts
(fact_id, value, context_id, unit_ref, period) + their semantic Unit (name, is_divide,
exact strings as stored) — plus the display inline HTML from the in-repo cache.
READ-ONLY toward the graph (zero Neo4j writes, zero Core imports, zero
public-schema changes). Display HTML comes from the in-repo cache; ON A CACHE MISS
the pinned lock_cell helper fetches it once from EDGAR (corrective-4 order).

    venv/bin/python -m pytest scripts/driver_seed/test_route_a_source.py -q
"""
import hashlib
import json
import os
import sys

from dotenv import dotenv_values
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'relocate_probe'))

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'relocate_probe', 'inline_html_cache')

_Q = """
MATCH (x:XBRLNode {accessionNo:$acc})<-[:REPORTS]-(f:Fact)-[:HAS_PERIOD]->(p:Period)
WHERE f.is_numeric='1' AND f.is_nil='0'
MATCH (f)-[:HAS_UNIT]->(u:Unit)
RETURN f.qname AS qname, f.fact_id AS fact_id, f.context_id AS context_id,
       f.value AS value, f.unit_ref AS unit_ref,
       u.name AS unit_name, u.is_divide AS is_divide,
       p.period_type AS ptype, p.start_date AS start, p.end_date AS end
"""


def _driver():
    cfg = dotenv_values(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '..', '..', '.env'))
    return GraphDatabase.driver(cfg['NEO4J_URI'],
                                auth=(cfg['NEO4J_USERNAME'], cfg['NEO4J_PASSWORD']))


_META_Q = """
MATCH (x:XBRLNode {accessionNo:$acc})<-[:HAS_XBRL]-(r:Report)
OPTIONAL MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN x.id AS url, r.formType AS form, c.id AS cik
"""


def build_source(accession, source_type=None, driver=None):
    """One locate()-ready source for the accession, or None (fail-closed).
    True report form + primary-filer CIK from the graph; display HTML from the
    cache, fetched ONCE via the pinned lock_cell helper on a miss; raw byte sha
    recorded."""
    own = driver is None
    drv = driver or _driver()
    try:
        with drv.session() as s:
            metas = list(s.run(_META_Q, acc=accession))
            rows = list(s.run(_Q, acc=accession))
    finally:
        if own:
            drv.close()
    if len(metas) != 1 or not rows:
        return None                          # FAIL-CLOSED: exactly one
    meta = metas[0]                          # Report/form/company or nothing
    if not meta['cik']:
        return None
    path = os.path.join(_CACHE, accession + '.htm')
    if not os.path.isfile(path):
        from lock_cell import fetch_inline_html
        path = fetch_inline_html(meta['url'], accession)
        if not path or not os.path.isfile(path):
            return None
    raw = open(path, 'rb').read()
    html = raw.decode('utf-8', errors='replace')
    if source_type is None:
        source_type = (meta['form'] or '10-Q').replace('-', '').lower()
    by_concept = {}
    for r in rows:
        period = ({'instant': r['start']} if r['ptype'] == 'instant'
                  else {'startDate': r['start'], 'endDate': r['end']})
        by_concept.setdefault(r['qname'], []).append({
            'value': r['value'], 'period': period, 'unitRef': r['unit_ref'],
            'fact_id': r['fact_id'], 'context_id': r['context_id'],
            'unit_name': r['unit_name'], 'is_divide': r['is_divide']})
    return {'source_id': accession, 'source_type': source_type,
            'xbrls': [json.dumps(by_concept)], 'texts': [],
            'inline_html': html,
            'company_cik': str(meta['cik'] or '').lstrip('0'),
            'raw_sha256': hashlib.sha256(raw).hexdigest()}
