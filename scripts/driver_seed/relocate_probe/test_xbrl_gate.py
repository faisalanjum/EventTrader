"""THE durable 150-case live XBRL gate (WP2; the exact-row corrective round).

Laws: FIXED cases — the seed-7 selection under the FULL-identity stable filter (complete
concept qname + complete (axis,member) pairs + semantic unit_name/is_divide equality between
lock and target), pinned by a selection hash · each case fetches its exact target Fact.id from
the STRUCTURED graph, requires EXACTLY ONE nonblank raw f.unit_ref, and verifies its semantic
(Unit) node against the truth row (unit_name + is_divide) — semantic names are NEVER passed as
raw ids and expected_unit heuristics are NEVER substituted (opaque raw ids like Unit12 make
both unsafe) · the TARGET-LOCAL raw id drives the matcher's unit filter · exact-Decimal on the
RAW value_raw (never str()-laundered) · EVERY case pinned individually with verdict + reason +
raw unit (abstain→ok = safe re-pin; ok→abstain/wrong = STOP, keyed losses to the owner) ·
abstention reasons are honest (no_source_xbrl ≠ concept_missing ≠ no_candidate) · buckets sum
to exactly 150 · only genuine graph unavailability skips; setup/auth/config errors FAIL.

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

SELECTION_SHA = "f3d3835b3aa85cf4d3f87fd5370bab6162512f308be28cc99ed38c48b362c3bb"
EXPECTED_FILE = os.path.join(HERE, 'xbrl_gate_expected.json')


def _pairs_of(side):
    return tuple(sorted((f['axis_qname'], f['member_qname']) for f in side['facets']))


def _case_key(r):
    """EXACT-row identity: the pool's stable pair_key + the target's fact_id, plus the
    human-readable identity fields (concept · period · value · semantic unit · time shape ·
    sorted pair id)."""
    t = r['target']
    shape = 'instant' if t['period_start'] == t['period_end'] else 'duration'
    pair_id = ";".join(f"{a}={m}" for a, m in _pairs_of(t))
    return (f"{r['pair_key']}|{t['fact_id']}|{t['concept_qname']}|{t['period_start']}|"
            f"{t['period_end']}|{t['value_raw']}|{t['unit_name']}|{shape}|{pair_id}")


def _selection():
    rows = [json.loads(l) for l in open(f'{HERE}/benchmark/multiaxis_pool/truth_pool.jsonl')]
    assert rows, "empty truth pool proves nothing"
    stable = [r for r in rows
              if r['lock']['concept_qname'] == r['target']['concept_qname']
              and _pairs_of(r['lock']) == _pairs_of(r['target'])
              and r['lock']['unit_name'] == r['target']['unit_name'] == 'iso4217:USD'
              and r['lock']['unit_is_divide'] == r['target']['unit_is_divide']
              and all(f.get('status') == 'confirmed' for f in r['target']['facets'])]
    random.seed(7)
    sample = random.sample(stable, 150)
    sha = hashlib.sha256("\n".join(sorted(_case_key(r) for r in sample)).encode()).hexdigest()
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
    """Exact-Decimal semantics on FRACTIONAL values (the int(float()) class corrupted these)."""
    for raw in ('1.23', '0.1'):
        blob = json.dumps({'EarningsPerShareDiluted': [{
            'value': raw, 'unitRef': 'usdPerShare',
            'period': {'startDate': '2024-01-01', 'endDate': '2024-12-31'}}]})
        got = LOC.match_facts([blob], 'us-gaap:EarningsPerShareDiluted', [],
                              '2024-01-01', '2024-12-31')
        assert got == XN.dec(raw) and str(got) == raw, f"{raw} -> {got!r}"


def _unit_rows(session, fact_ids):
    """{fact_id: [(raw_unit_ref, semantic_name, is_divide), ...]} from the STRUCTURED layer."""
    out = {}
    for rec in session.run(
            """MATCH (f:Fact)-[:HAS_UNIT]->(u:Unit) WHERE f.id IN $ids
               RETURN f.id AS fid, f.unit_ref AS raw, u.name AS uname,
                      u.is_divide AS div""", ids=fact_ids):
        out.setdefault(rec['fid'], []).append((rec['raw'], rec['uname'], rec['div']))
    return out


def test_150_case_gate_exact_rows_target_units():
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
        units = _unit_rows(s, [r['target']['fact_id'] for r in sample])
    drv.close()
    assert xbrl, "empty live fetch proves nothing — the gate may never silently skip"
    verdicts, wrongs = {}, []
    for r in sample:
        t = r['target']
        key = _case_key(r)
        urows = units.get(t['fact_id'], [])
        assert len(urows) == 1, \
            f"target fact must carry EXACTLY ONE structured unit, got {len(urows)}: {key}"
        raw_unit, sem_name, sem_div = urows[0]
        assert isinstance(raw_unit, str) and raw_unit.strip(), f"blank raw unit_ref: {key}"
        assert sem_name == t['unit_name'] and sem_div == t['unit_is_divide'], \
            f"semantic Unit mismatch vs truth ({sem_name}, {sem_div}): {key}"
        blobs = xbrl.get(t['accession'], [])
        if not blobs:
            verdicts[key] = {'verdict': 'abstain', 'reason': 'no_source_xbrl',
                             'raw_unit': raw_unit}
            continue
        got, reason = LOC.match_facts_explain(
            blobs, t['concept_qname'], list(_pairs_of(t)),
            t['period_start'], t['period_end'], unit_ref=raw_unit)
        if got is None:
            verdicts[key] = {'verdict': 'abstain', 'reason': reason, 'raw_unit': raw_unit}
        elif got == XN.dec(t['value_raw']):             # RAW value_raw — never str()-laundered
            verdicts[key] = {'verdict': 'ok', 'reason': 'ok', 'raw_unit': raw_unit}
        else:
            verdicts[key] = {'verdict': 'wrong', 'reason': reason, 'raw_unit': raw_unit}
            wrongs.append((key, str(got)))
    assert not wrongs, f"deterministic lane returned WRONG values: {wrongs}"
    counts = {'ok': 0, 'abstain': 0, 'wrong': 0}
    for v in verdicts.values():
        counts[v['verdict']] += 1
    assert sum(counts.values()) == 150, "every case must land in exactly one bucket"
    gained = sorted(k for k, v in verdicts.items() if v['verdict'] == 'ok'
                    and expected.get(k, {}).get('verdict') == 'abstain')
    lost = sorted(k for k, v in verdicts.items() if v['verdict'] == 'abstain'
                  and expected.get(k, {}).get('verdict') == 'ok')
    assert verdicts == expected, (
        f"per-case pins moved — counts now {counts}; SAFE gains (abstain→ok, re-pin allowed): "
        f"{gained}; LOSSES (ok→abstain, STOP + keyed cases to the OWNER): {lost}")
    print(f"[ok] 150-case gate (exact rows, target-local raw units): {counts}")
