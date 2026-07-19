#!/usr/bin/env python3
"""EXECUTABLE census evidence (rounds 24/26/27, committed): invalid-address classes across 11
tickers (the wp1 cohort + CAG), every 10-K/10-Q FinancialStatementContent blob.
ROUND-26 CORRECTION (reviewer): the first version measured PARSED pairs — but seg_parse REJECTS
padded names, so the padded counter was structurally blind. This version inspects the FOUR RAW
storage shapes directly, independently of seg_parse.
ROUND-27 (reviewer): POSITIVE CONTROLS run first — each raw detector must FIRE on a synthetic
violation before the scan counts anything (a census whose counters cannot fire proves nothing);
every malformed/unknown shape is counted AND asserted zero, never silently skipped.
Re-run 2026-07-19: dimensioned facts=47,152 — 0 repeated-axis / 0 padded / 0 mixed /
0 unreadable / 0 unknown-shape.

    venv/bin/python data/driver_catalog_seed/wp1_evidence/census_dimension_addresses.py
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'scripts', 'driver_seed'))
import run_code_tier as RC

TICKERS = ['A', 'AA', 'AAL', 'AAPL', 'ABT', 'ACI', 'ACN', 'ADM', 'AEE', 'AFL', 'CAG']


def raw_names(seg):
    """(axis, member) RAW strings from the four storage shapes — NO parser, NO stripping.
    None marks an unknown/unreadable entry — INCLUDING a dict that yields no names or yields a
    non-string side (round-28: malformed dictionary shapes count as unknown; nothing is
    invisible)."""
    out = []
    for it in (seg if isinstance(seg, list) else [seg]):
        if not isinstance(it, dict):
            out.append(None)
            continue
        got = 0
        if 'value' in it:
            out.append((it.get('dimension'), it.get('value'))); got += 1
        em = it.get('explicitMember')
        if isinstance(em, list):
            for m in em:
                out.append((m.get('dimension'), m.get('$t')) if isinstance(m, dict) else None)
                got += 1
        elif isinstance(em, dict):
            out.append((em.get('dimension'), em.get('$t'))); got += 1
        elif isinstance(em, str):
            out.append((it.get('dimension'), em)); got += 1
        if got == 0:
            out.append(None)               # a dict entry yielding NOTHING is unknown, not invisible
    return [n if (n is None or (isinstance(n[0], str) and n[0].strip()
                                and isinstance(n[1], str) and n[1].strip())) else None
            for n in out]              # round-29: BLANK axis/member strings are unknown too


def _positive_controls():
    """Round-27 (reviewer): prove each RAW detector can actually SEE its violation class."""
    padded = [{'dimension': ' x:A ', 'value': ' x:M '}]
    assert any(isinstance(x, str) and x != x.strip()
               for n in raw_names(padded) if n for x in n), "padded detector blind"
    rep = [{'dimension': 'x:A', 'value': 'x:M1'}, {'dimension': 'x:A', 'value': 'x:M2'}]
    axes = [a for n in raw_names(rep) if n for a in [n[0]] if isinstance(a, str)]
    assert len(axes) != len(set(axes)), "repeated-axis detector blind"
    mixed = [{'dimension': 'x:A', 'value': 'x:M',
              'explicitMember': {'dimension': 'x:B', '$t': 'x:N'}}]
    assert any(isinstance(it, dict) and 'value' in it and 'explicitMember' in it
               for it in mixed), "mixed-format detector blind"
    assert None in raw_names(['unknown-shape-entry']), "unknown-shape detector blind"
    assert None in raw_names([{'weird': 'no-keys'}]), "empty-yield dict not counted unknown"
    assert None in raw_names([{'dimension': 123, 'value': 'x:M'}]), "non-string side not unknown"
    assert None in raw_names([{'dimension': '  ', 'value': 'x:M'}]), "blank axis not unknown"
    print("positive controls: all raw detectors fire on synthetic violations")


def main():
    _positive_controls()
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'),
                                     os.environ['NEO4J_PASSWORD']))
    rep_ax = padded = mixed = total = 0
    unreadable_blobs = nondict_blobs = nonfact_entries = unknown_shape = 0
    with drv.session() as s:
        for tk in TICKERS:
            for row in s.run("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) "
                             "WHERE r.formType IN ['10-K','10-Q'] "
                             "MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent) "
                             "RETURN f.value AS xb", tk=tk):
                try:
                    data = json.loads(row['xb'])
                except Exception:
                    unreadable_blobs += 1
                    continue
                if not isinstance(data, dict):
                    nondict_blobs += 1
                    continue
                for con, facts in data.items():
                    for fc in (facts if isinstance(facts, list) else [facts]):
                        if not isinstance(fc, dict):
                            nonfact_entries += 1
                            continue
                        if not fc.get('segment'):
                            continue
                        total += 1
                        names = raw_names(fc['segment'])
                        if any(n is None for n in names):
                            unknown_shape += 1
                        axes = [a for n in names if n for a in [n[0]] if isinstance(a, str)]
                        if len(axes) != len(set(axes)):
                            rep_ax += 1
                        if any(isinstance(x, str) and x != x.strip()
                               for n in names if n for x in n):
                            padded += 1
                        items = fc['segment'] if isinstance(fc['segment'], list) else [fc['segment']]
                        if any(isinstance(it, dict) and 'value' in it and 'explicitMember' in it
                               for it in items):
                            mixed += 1
    drv.close()
    print(f"tickers={len(TICKERS)}  dimensioned facts={total}  repeated-axis={rep_ax}  "
          f"padded-names={padded}  mixed-format-entries={mixed}  "
          f"unreadable-blobs={unreadable_blobs}  nondict-blobs={nondict_blobs}  "
          f"nonfact-entries={nonfact_entries}  unknown-shape={unknown_shape}")
    assert total > 0, "empty live scan proves nothing"
    assert (rep_ax == padded == mixed == unknown_shape == 0), \
        "violation classes must be zero — a nonzero count may NEVER exit green"
    assert (unreadable_blobs == nondict_blobs == nonfact_entries == 0), \
        "malformed/unknown data must be investigated, never silently skipped"


if __name__ == '__main__':
    main()
