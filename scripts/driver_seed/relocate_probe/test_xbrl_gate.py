"""THE durable 150-case live XBRL gate (WP2 plan v4 step 3; pair-complete build round).

Laws (reviewer-specified): FIXED cases — the exact seed-7 selection from the archived pool,
pinned by a selection hash · FULL (axis,member) PAIRS drive the match (the wrong-axis class
can never bind — a member under the wrong axis is a different identity) · exact-Decimal
comparison · ZERO wrong · EVERY case pinned INDIVIDUALLY (committed per-case verdict fixture:
abstain→ok = safe recall improvement, re-pin without the owner; ok→abstain or any wrong = FAIL
and OWNER-GATED) · the buckets sum to exactly 150 · CANNOT silently skip — only genuine graph
unavailability skips; database setup/auth/config errors FAIL.

    venv/bin/python -m pytest scripts/driver_seed/relocate_probe/test_xbrl_gate.py -q
"""
import hashlib
import json
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'driver', 'relocation'))
import exact_numbers as XN
import locator as LOC
import xbrl_lane

SELECTION_SHA = "84274ebe8730949bc09fe6f59c050456026a9da45615449a5aa4a43912a1259f"
EXPECTED_FILE = os.path.join(HERE, 'xbrl_gate_expected.json')   # per-case verdict pins


def _case_key(t):
    return (f"{t['accession']}|{t['concept_qname']}|{t['period_start']}|"
            f"{t['period_end']}|{t['value_raw']}")


def _selection():
    rows = [json.loads(l) for l in open(f'{HERE}/benchmark/multiaxis_pool/truth_pool.jsonl')]
    assert rows, "empty truth pool proves nothing"

    def ident(s):
        return (s['concept_qname'].split(':')[-1],
                frozenset(f['member_qname'] for f in s['facets']))
    stable = [r for r in rows if ident(r['lock']) == ident(r['target'])
              and r['lock']['unit_name'] == 'iso4217:USD'
              and all(f.get('status') == 'confirmed' for f in r['target']['facets'])]
    random.seed(7)
    sample = random.sample(stable, 150)
    sha = hashlib.sha256("\n".join(sorted(_case_key(r['target'])
                                          for r in sample)).encode()).hexdigest()
    return sample, sha


def _graph():
    """Connect or skip ONLY on genuine unavailability — setup/auth/config errors FAIL."""
    import run_code_tier as RC
    RC.load_env_neo4j()                      # missing env vars raise -> FAIL (never skip)
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    try:
        drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                                   auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'),
                                         os.environ['NEO4J_PASSWORD']))
        drv.verify_connectivity()
        return drv
    except (ServiceUnavailable, OSError, ConnectionError) as e:
        pytest.skip(f"live graph genuinely unavailable: {e}")


def test_fractional_decimal_exactness_synthetic():
    """Exact-Decimal semantics on FRACTIONAL values (the int(float()) class corrupted these):
    1.23 and 0.1 must round-trip exactly through the neutral matcher."""
    for raw in ('1.23', '0.1'):
        blob = json.dumps({'EarningsPerShareDiluted': [{
            'value': raw, 'unitRef': 'U_USDperShare',
            'period': {'startDate': '2024-01-01', 'endDate': '2024-12-31'}}]})
        got = LOC.match_facts([blob], 'us-gaap:EarningsPerShareDiluted', [],
                              '2024-01-01', '2024-12-31')
        assert got == XN.dec(raw) and str(got) == raw, f"{raw} -> {got!r}"


def test_150_case_gate_pair_complete_individually_pinned():
    sample, sha = _selection()
    assert len(sample) == 150, f"selection must be exactly 150, got {len(sample)}"
    assert sha == SELECTION_SHA, f"selection drifted: {sha}"
    assert os.path.exists(EXPECTED_FILE), \
        "per-case pin fixture missing — the gate may never run unpinned"
    expected = json.load(open(EXPECTED_FILE))
    assert len(expected) == 150, f"fixture must pin all 150, has {len(expected)}"
    drv = _graph()
    with drv.session() as s:
        res = s.run("""MATCH (r:Report)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
                       WHERE r.accessionNo IN $a
                       RETURN r.accessionNo AS acc, collect(DISTINCT f.value) AS xb""",
                    a=sorted({r['target']['accession'] for r in sample}))
        xbrl = {row['acc']: [v for v in row['xb'] if v] for row in res}
    drv.close()
    assert xbrl, "empty live fetch proves nothing — the gate may never silently skip"
    verdicts, wrongs = {}, []
    for r in sample:
        t = r['target']
        got = xbrl_lane.resolve(xbrl.get(t['accession'], []), t['concept_qname'], None,
                                t['period_start'], t['period_end'],
                                pairs=[(f['axis_qname'], f['member_qname'])
                                       for f in t['facets']])
        key = _case_key(t)
        if got is None:
            verdicts[key] = 'abstain'
        elif got == XN.dec(str(t['value_raw'])):        # EXACT Decimal — never int(float())
            verdicts[key] = 'ok'
        else:
            verdicts[key] = 'wrong'
            wrongs.append((key, str(got)))
    assert not wrongs, f"deterministic lane returned WRONG values: {wrongs}"
    counts = {'ok': 0, 'abstain': 0, 'wrong': 0}
    for v in verdicts.values():
        counts[v] += 1
    assert sum(counts.values()) == 150, "every case must land in exactly one bucket"
    gained = sorted(k for k, v in verdicts.items()
                    if v == 'ok' and expected.get(k) == 'abstain')
    lost = sorted(k for k, v in verdicts.items()
                  if v == 'abstain' and expected.get(k) == 'ok')
    assert verdicts == expected, (
        f"per-case pins moved — counts now {counts}; SAFE gains (abstain→ok, re-pin allowed): "
        f"{gained}; LOSSES (ok→abstain, OWNER-GATED): {lost}")
    print(f"[ok] 150-case gate (pair-complete): {counts} — per-case pins hold")
