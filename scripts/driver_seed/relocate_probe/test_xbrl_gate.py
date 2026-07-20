"""THE durable 150-case live XBRL gate (WP2 plan v4 step 3 — replaces xbrl_lane's
uncollected __main__ check, which was in NO battery and compared int(float(...))).

Laws (reviewer-specified): FIXED cases — the exact seed-7 selection from the archived pool,
pinned by a selection hash so sampling can never drift · exact-Decimal comparison · ZERO wrong ·
deterministic output · CANNOT silently skip (empty pool/fetch FAILS; graph-unavailable is the
only legal skip) · the gate RECONCILES EXACTLY ALL 150: ok + abstain + wrong == 150 with the
ok/abstain split pinned to the measured baseline — any loss versus it is explained
case-by-case and OWNER-GATED before the pin moves.

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
import xbrl_lane

# Pinned at first measured run (2026-07-20): sha256 of the seed-7 selection's sorted identity
# list. If the pool file, the stable filter, or the sampling ever changes, this breaks LOUDLY.
SELECTION_SHA = "84274ebe8730949bc09fe6f59c050456026a9da45615449a5aa4a43912a1259f"
BASELINE = {"ok": 130, "abstain": 20, "wrong": 0}   # the verified 130/150 baseline


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
    key = sorted(f"{r['target']['accession']}|{r['target']['concept_qname']}|"
                 f"{r['target']['period_start']}|{r['target']['period_end']}|"
                 f"{r['target']['value_raw']}" for r in sample)
    sha = hashlib.sha256("\n".join(key).encode()).hexdigest()
    return sample, sha


def test_150_case_gate_fixed_exact_reconciled():
    sample, sha = _selection()
    assert len(sample) == 150, f"selection must be exactly 150, got {len(sample)}"
    assert sha == SELECTION_SHA, f"selection drifted: {sha}"
    import run_code_tier as RC
    try:
        RC.load_env_neo4j()
        from neo4j import GraphDatabase
        drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                                   auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'),
                                         os.environ['NEO4J_PASSWORD']))
        with drv.session() as s:
            s.run("RETURN 1").single()
    except Exception as e:
        if type(e).__name__ in ('ServiceUnavailable', 'KeyError', 'OSError',
                                'ConnectionError', 'AuthError', 'ConfigurationError'):
            pytest.skip(f"live graph genuinely unavailable: {e}")
        raise
    with drv.session() as s:
        res = s.run("""MATCH (r:Report)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
                       WHERE r.accessionNo IN $a
                       RETURN r.accessionNo AS acc, collect(DISTINCT f.value) AS xb""",
                    a=sorted({r['target']['accession'] for r in sample}))
        xbrl = {row['acc']: [v for v in row['xb'] if v] for row in res}
    drv.close()
    assert xbrl, "empty live fetch proves nothing — the gate may never silently skip"
    ok = absent = wrong = 0
    wrongs = []
    for r in sample:
        t = r['target']
        got = xbrl_lane.resolve(xbrl.get(t['accession'], []), t['concept_qname'],
                                [f['member_qname'] for f in t['facets']],
                                t['period_start'], t['period_end'])
        if got is None:
            absent += 1                     # graph gap or ambiguity -> honest abstain
        elif got == XN.dec(str(t['value_raw'])):    # EXACT Decimal — never int(float())
            ok += 1
        else:
            wrong += 1
            wrongs.append((t['accession'], t['concept_qname'], t['value_raw'], str(got)))
    assert ok + absent + wrong == 150, "every case must land in exactly one bucket"
    assert wrong == 0, f"deterministic lane returned WRONG values: {wrongs}"
    assert {"ok": ok, "abstain": absent, "wrong": wrong} == BASELINE, (
        f"gate moved vs the pinned baseline {BASELINE}: ok={ok} abstain={absent} — any loss "
        f"must be explained case-by-case and OWNER-GATED before this pin changes")
    print(f"[ok] 150-case gate: ok={ok} abstain={absent} wrong=0 — exact reconcile, "
          f"exact Decimal, pinned selection")
