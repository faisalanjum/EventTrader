#!/usr/bin/env python3
"""WP1 verification + report — COMMITTED and reproducible (round-12 requirement 7).

Reads the pinned manifest + the regenerated wp1 outputs, then:
  1. completeness: line counts == the run's own summary (guards against mid-write reads);
  2. reconciliation BY DISTINCT RAW-ROW ID: every raw row's item_id appears in >=1 outcome
     (resolved / residual / abstain incl. corpus_missing); no id carries two different (kpi,value);
  3. mechanical compliance (safety checks, never called precision): value-token-in-quote and
     quote-is-exact-source-substring over EVERY resolved record (sources re-fetched live);
  4. zero fabricated (quote_source='xbrl_fact') records in this cohort;
  5. stamps sha256 output hashes back into the manifest; writes the report.

    venv/bin/python scripts/driver_seed/wp1_verify.py
"""
import os, sys, json, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
import run_code_tier as RC, link_lib as L

D = 'data/driver_catalog_seed/wp1'
MAN = 'data/driver_catalog_seed/wp1_manifest.json'
man = json.load(open(MAN))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    res = [json.loads(l) for l in open(f'{D}/code_resolved.jsonl')]
    rem = [json.loads(l) for l in open(f'{D}/residual.jsonl')]
    ab = [json.loads(l) for l in open(f'{D}/abstain.jsonl')]
    summ = json.load(open(f'{D}/code_summary.json'))

    # 1. completeness vs the run's own summary
    assert (len(res), len(rem), len(ab)) == (summ['records_resolved'], summ['residual'], summ['abstain']), \
        f"counts != summary: {(len(res), len(rem), len(ab))} vs {summ}"

    # 2. reconciliation by distinct raw-row id
    rows = [json.loads(l) for l in open('data/driver_catalog_seed/worklist.jsonl')
            if json.loads(l)['ticker'] in set(man['tickers'])]
    slice_sha = hashlib.sha256(''.join(sorted(json.dumps(r, sort_keys=True) for r in rows)).encode()).hexdigest()
    assert slice_sha == man['worklist_slice_sha256'], "worklist slice drifted vs the manifest"
    raw_ids = {RC._iid(r) for r in rows}
    assert len(raw_ids) == len(rows), "duplicate raw rows would need shared-id handling"
    out_ids = {r['item_id'] for r in res} | {r['item_id'] for r in rem} | {a['item_id'] for a in ab}
    missing = raw_ids - out_ids
    assert not missing, f"{len(missing)} raw rows produced NO id-carrying outcome"
    byid = collections.defaultdict(set)
    for r in res + rem + ab:
        byid[r['item_id']].add((r.get('kpi') or r.get('raw_label'), str(r.get('value'))))
    bad = {k: v for k, v in byid.items() if len(v) > 1}
    assert not bad, f"ids carrying different (kpi,value): {list(bad.items())[:3]}"

    # 3. mechanical compliance on every resolved record
    fab = [r for r in res if r.get('quote_source') == 'xbrl_fact' or r.get('source') == 'xbrl_fact']
    assert not fab, f"fabricated quotes: {len(fab)}"
    bad_vq = [r for r in res if not L.value_ok(float(r['value']),
                                              None if r['fmt'] == 'number' else r['fmt'], r['quote'])]
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    cache, bad_sub = {}, []
    with drv.session() as s:
        for r in res:
            key = (r['ticker'], r['form'], r.get('period') or r.get('period_end'),
                   r['source_type'], r['source_id'])
            if key not in cache:
                if r['source_type'] in ('10k', '10q'):
                    f = RC.fetch_filing(s, r['ticker'], r['form'], key[2])
                    cache[key] = (f or {}).get('texts', [])
                else:
                    q = list(s.run(
                        """MATCH (x:Report {accessionNo:$a})
                           OPTIONAL MATCH (x)-[:HAS_EXHIBIT]->(e:ExhibitContent)
                           OPTIONAL MATCH (x)-[:HAS_SECTION]->(sx:ExtractedSectionContent)
                           OPTIONAL MATCH (x)-[:HAS_FILING_TEXT]->(f:FilingTextContent)
                           RETURN collect(DISTINCT e.content)+collect(DISTINCT sx.content)
                                  +collect(DISTINCT f.content) AS cs""", a=r['source_id']))
                    cache[key] = [c for c in (q[0]['cs'] if q else []) if c]
            if not any(r['quote'] in t for t in cache[key]):
                bad_sub.append((r['item_id'], r['source_id'], r['quote'][:60]))
    drv.close()

    # 4. buckets / bands / routes
    def band(v):
        v = abs(float(v))
        if v == 0: return 'zero'
        if v != int(v): return 'decimal'
        return 'small' if v < 1000 else 'other'
    routes = collections.Counter((r['tier'], r['source_type']) for r in res)
    bands = collections.Counter(band(r['value']) for r in res)
    ab_reason = collections.Counter(a['reason'] for a in ab)
    incomplete = sum(1 for a in ab if a.get('sources_incomplete'))

    # 5. hashes into the manifest + the report
    man['output_sha256'] = {n: sha(f'{D}/{n}') for n in
                            ('code_resolved.jsonl', 'residual.jsonl', 'abstain.jsonl',
                             'packets.jsonl', 'skip_ledger.jsonl', 'park_ledger.jsonl')}
    man['verified_summary'] = summ
    json.dump(man, open(MAN, 'w'), indent=1)

    rep = f"""# WP1 Report — regenerated cohort ({','.join(man['tickers'])})

Manifest (incl. output sha256s): `{MAN}` · slice sha `{man['worklist_slice_sha256'][:16]}…`
Command: `{man['command']}` · verifier: `scripts/driver_seed/wp1_verify.py` (this file regenerates
this report; all assertions passed or it would have crashed).

## Mechanical compliance (safety checks — NOT precision; true P/R = WP4)
- value-token-in-quote: **{len(res)-len(bad_vq)}/{len(res)}**{'' if not bad_vq else ' VIOLATIONS ' + str(bad_vq[:3])}
- quote-is-exact-source-substring: **{len(res)-len(bad_sub)}/{len(res)}**{'' if not bad_sub else ' VIOLATIONS ' + str(bad_sub[:3])}
- fabricated quotes in THIS cohort: **0** (asserted) · older part1–4 artifacts: **STALE/INVALID**

## Reconciliation by distinct raw-row id (asserted)
raw rows {len(rows)} = unique ids {len(raw_ids)}; every id accounted for in
resolved/residual/abstain; no id carries two different (kpi,value).

## Coverage
resolved {len(res)} (routes: {dict(routes)}) · residual {len(rem)} · abstain {len(ab)}
(reasons: {dict(ab_reason)}; sources_incomplete-flagged: {incomplete})
value bands (resolved): {dict(bands)}

run summary: {json.dumps(summ)}
"""
    open('data/driver_catalog_seed/wp1_report.md', 'w').write(rep)
    print(rep)
    assert not bad_vq and not bad_sub, "mechanical compliance violated"
    print("WP1 VERIFY: ALL ASSERTIONS PASSED")


if __name__ == '__main__':
    main()
