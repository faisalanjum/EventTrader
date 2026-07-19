#!/usr/bin/env python3
"""XBRL-FIRST deterministic lane (GPT final design, head-to-head verified 2026-07-13; task #767 step 1).

When the target source is a 10-K/10-Q with XBRL, a stable full identity resolves the value with NO AI:
    concept qname + EVERY (axis) member qname + unit(USD) + exact period  ->  unique fact value
Abstains (returns None) on anything ambiguous, missing, or non-unique — the text lane is the fallback.
Independently re-verified on 150 random pool pairs: 0 wrong, 0 ambiguous; unresolved = graph extraction
gaps (fact exists at SEC, absent from FinancialStatementContent -> SEC fallback is a future add).

SEPARATE from tier1 on purpose: parses multi-axis members locally and never touches the certified
zero/one-axis matching (the naive seg_members list-fix broke 50/1761 certified records — STATE.md).

    venv/bin/python scripts/driver_seed/relocate_probe/xbrl_lane.py   # self-check vs the archived pool
"""
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'driver', 'relocation'))
from oracle import _rows, _members_all
import exact_numbers as XN

HERE = os.path.dirname(__file__)


def resolve(xbrls, concept_qname, member_qnames, period_start, period_end, unit_ref=None):
    """unique fact value (exact Decimal) for the FULL identity in this filing's XBRL blobs, else
    None. Dates: normalize-once-by-known-format then EXACT (graph storage is inclusive — verified
    live; no ±1-day tolerance sets, they accepted convention-inconsistent pairs). start == end =
    the instant form (gp_DATE_DATE). Concepts: storage keys are BARE local names (verified live) —
    a request prefix strips deterministically; local names compare EXACTLY. Units: filer-local
    `unitRef` codes; a caller-supplied unit_ref filters; without one, candidates under CONFLICTING
    unitRefs are ambiguous → abstain."""
    con = concept_qname.split(':')[-1]
    want = frozenset(member_qnames)
    try:
        ps, pe = XN.period_key(period_start, period_end)
    except XN.ExactError:
        return None
    instant = (ps == pe)
    vals, units = set(), set()
    for c, fc in _rows(xbrls):
        if c.split(':')[-1] != con:
            continue
        p = fc.get('period') or {}
        if instant:
            if p.get('instant') != ps:
                continue
        else:
            if p.get('startDate') != ps or p.get('endDate') != pe:
                continue
        if frozenset(_members_all(fc)) != want:
            continue
        u = fc.get('unitRef')
        if unit_ref is not None and u != unit_ref:
            continue
        try:
            v = XN.dec(str(fc.get('value', '')).strip())
        except XN.ExactError:
            return None                       # non-numeric collision -> not cleanly resolvable
        vals.add(v)
        units.add(u)
    if len(vals) != 1:
        return None                           # unique or abstain
    if unit_ref is None and len(units) > 1:
        return None                           # unit conflict -> ambiguous, abstain
    return next(iter(vals))


if __name__ == '__main__':
    import run_code_tier as RC
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    rows = [json.loads(l) for l in open(f'{HERE}/benchmark/multiaxis_pool/truth_pool.jsonl')]

    def ident(s):
        return (s['concept_qname'].split(':')[-1], frozenset(f['member_qname'] for f in s['facets']))
    stable = [r for r in rows if ident(r['lock']) == ident(r['target'])
              and r['lock']['unit_name'] == 'iso4217:USD'
              and all(f.get('status') == 'confirmed' for f in r['target']['facets'])]
    random.seed(7)
    sample = random.sample(stable, 150)
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    with drv.session() as s:
        res = s.run("""MATCH (r:Report)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
                       WHERE r.accessionNo IN $a RETURN r.accessionNo AS acc, collect(DISTINCT f.value) AS xb""",
                    a=sorted({r['target']['accession'] for r in sample}))
        xbrl = {row['acc']: [v for v in row['xb'] if v] for row in res}
    drv.close()
    ok = absent = wrong = 0
    for r in sample:
        t = r['target']
        got = resolve(xbrl.get(t['accession'], []), t['concept_qname'],
                      [f['member_qname'] for f in t['facets']], t['period_start'], t['period_end'])
        if got is None:
            absent += 1                       # graph gap or ambiguity -> honest abstain
        elif got == int(float(t['value_raw'])):
            ok += 1
        else:
            wrong += 1
    print(f"xbrl_lane self-check: OK {ok} | abstain {absent} | WRONG {wrong}  (150 random stable pairs)")
    assert wrong == 0, "deterministic lane must NEVER return a wrong value"
    assert ok >= 125, "resolution rate collapsed vs the verified 130/150 baseline"
    print("xbrl_lane self-check PASSED (0 wrong — precision-safe; abstains = graph gaps)")
