#!/usr/bin/env python3
"""Step 1 — XBRL ORACLE: exact known-true values from a filing's own XBRL, the answer key for building
test pairs (unlocks quarterly + transcript/news grading). 0 LLM tokens.

Restricted to UNAMBIGUOUS facts so it sidesteps the multi-axis member-parse bug (which broke 50 certified
records): keep only 0-axis (headline totals) or 1-axis (single segment) facts, of the right DURATION
(annual ~365d / quarter ~91d, NOT the year-to-date 183/273d), whose value is UNIQUE within
(concept, member, endDate). Everything ambiguous is dropped, not guessed.

    venv/bin/python scripts/driver_seed/relocate_probe/oracle.py     # self-check + demo (needs Neo4j)
"""
import os, re, sys, json, collections
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import link_lib as L
import run_code_tier as RC

DUR = {'annual': (350, 380), 'quarter': (84, 100),      # 52/53-week aware
       'ytd': (150, 285)}                                # year-to-date (6mo/9mo) — the Q-vs-YTD distractor


def axis_count(fc):
    """number of explicit dimension members (0 = headline total; 1 = single segment; 2+ = multi-axis)."""
    seg = fc.get('segment')
    if not seg:
        return 0
    n = 0
    for s in (seg if isinstance(seg, list) else [seg]):
        if not isinstance(s, dict):
            continue
        em = s.get('explicitMember')
        if isinstance(em, list):
            n += len(em)
        elif em or isinstance(s.get('value'), str):
            n += 1
    return n


def _members_all(fc):
    """ALL member value strings incl. the multi-axis LIST shape (local; link_lib.seg_members drops lists
    — safe HERE because the oracle only READS members for identity, it never tier1-matches, so no ties)."""
    seg = fc.get('segment')
    if not seg:
        return []
    out = []
    for s in (seg if isinstance(seg, list) else [seg]):
        if not isinstance(s, dict):
            continue
        if isinstance(s.get('value'), str):
            out.append(s['value'])
        em = s.get('explicitMember')
        if isinstance(em, list):
            out += [m['$t'] for m in em if isinstance(m, dict) and m.get('$t')]
        elif isinstance(em, dict) and em.get('$t'):
            out.append(em['$t'])
        elif isinstance(em, str):
            out.append(em)
    return out


def _rows(xbrls):
    for blob in xbrls:
        try:
            d = json.loads(blob)
        except (ValueError, TypeError):
            continue
        if isinstance(d, dict):
            for con, facts in d.items():
                for fc in (facts if isinstance(facts, list) else [facts]):
                    if isinstance(fc, dict):
                        yield con, fc


def _days(fc):
    p = fc.get('period') or {}
    sd, ed = p.get('startDate'), p.get('endDate')
    if not sd or not ed:
        return None, ed
    try:
        return (date.fromisoformat(ed) - date.fromisoformat(sd)).days, ed
    except ValueError:
        return None, ed


def clean_facts(xbrls, kind):
    """{(concept, member_key): {endDate: value_int}} of UNAMBIGUOUS facts for the duration `kind`.
    member_key = frozenset of member tokens (empty for headline). Drops multi-axis facts and any
    (concept, member, endDate) whose value is not unique."""
    lo, hi = DUR[kind]
    groups = collections.defaultdict(set)                # (concept, member_key, endDate) -> {values}
    for con, fc in _rows(xbrls):
        ac = axis_count(fc)
        days, ed = _days(fc)
        if days is None or not (lo <= days <= hi) or not ed:
            continue
        v = str(fc.get('value', '')).strip()
        if not re.match(r'-?\d+(\.\d+)?$', v):
            continue
        if ac == 0:
            mk = frozenset()              # headline total (0-axis)
        else:
            mk = frozenset(L.member_tokens(_members_all(fc)))   # single- OR multi-axis: full slice combo
            if not mk:                    # member all-generic (a subtotal) -> slice unrecoverable, skip
                continue                  # (so it can't collide with the headline total)
        groups[(con.split(':')[-1], mk, ed)].add(int(round(float(v))))
    out = collections.defaultdict(dict)
    for (con, mk, ed), vals in groups.items():
        if len(vals) == 1:                               # unique -> unambiguous known-true value
            out[(con, mk)][ed] = next(iter(vals))
    return dict(out)


def series(session, ticker, kind):
    """merge unambiguous facts across ALL of a company's filings of the matching form
    (10-K for annual, 10-Q for quarter). Returns {(concept, member_key): {endDate: value}}."""
    form = '10-K' if kind == 'annual' else '10-Q'
    rows = session.run(
        """MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
           RETURN collect(DISTINCT f.value) AS xbrls""", form=form, tk=ticker).single()
    xbrls = [v for v in (rows['xbrls'] if rows else []) if v]
    merged = collections.defaultdict(dict)
    for k, per_val in clean_facts(xbrls, kind).items():
        merged[k].update(per_val)
    return dict(merged)


if __name__ == '__main__':
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    with drv.session() as s:
        aa, _, _ = RC.fetch_corpus(s, 'AA', '10-K', '2024-12-31')
        pn, _, _ = RC.fetch_corpus(s, 'PANW', '10-Q', '2025-01-31')
        cg, _, _ = RC.fetch_corpus(s, 'CAG', '10-K', '2025-05-25')
    drv.close()
    a = clean_facts(aa, 'annual'); q = clean_facts(pn, 'quarter'); c = clean_facts(cg, 'annual')
    REV = 'RevenueFromContractWithCustomerExcludingAssessedTax'
    GS = ('OperatingIncomeLoss', frozenset({'grocery', 'snacks'}))
    # 0-axis: AA total revenue 2024 = 11,895M (verified against its geography table "$ 11,895")
    assert a[(REV, frozenset())]['2024-12-31'] == 11895000000, "AA headline revenue"
    # quarter: every fact is a real 3-month duration, never the 183d YTD value (775.3M)
    assert all(v != 775300000 for pv in q.values() for v in pv.values()), "YTD (183d) leaked into quarter facts"
    # MULTI-AXIS (the design's FS-09 requirement): CAG Grocery&Snacks operating income, tagged on
    # OperatingSegments x GroceryAndSnacks, GAAP = 1,017M -> captured under the full slice combo.
    assert c[GS]['2025-05-25'] == 1017000000, "multi-axis fact must be captured"
    assert a and q and c, "no facts parsed"
    hl = lambda d: sum(1 for (_, mk) in d if not mk)
    print("oracle self-check OK  (headline + single-axis + multi-axis)")
    print(f"  AA   10-K annual: {len(a):>3} series ({hl(a)} headline / {len(a)-hl(a)} sliced)")
    print(f"  PANW 10-Q qtr   : {len(q):>3} series ({hl(q)} headline / {len(q)-hl(q)} sliced) — YTD excluded")
    print(f"  CAG  multi-axis Grocery&Snacks op income 2025 = {c[GS]['2025-05-25']:,}  (2-axis fact, captured)")
