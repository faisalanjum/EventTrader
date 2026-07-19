#!/usr/bin/env python3
"""WP1 verification — CHECK-ONLY by default (round-13).

Default (check) mode:
  1. output hashes must EQUAL the manifest's recorded hashes (tamper/drift detection — never
     silently replaced);
  2. completeness: line counts == the run's own summary (guards against mid-write reads);
  3. reconciliation BY DISTINCT RAW-ROW ID, BOTH directions: every raw id appears in >=1 outcome
     AND every output id exists in the raw slice (an INVENTED record fails); no id carries two
     different (kpi, value);
  4. mechanical compliance (safety checks, never called precision): value-token-in-quote and
     quote-is-exact-source-substring over EVERY resolved record (sources re-fetched live);
  5. zero fabricated (quote_source='xbrl_fact') records.
  Check mode writes NOTHING.

`--record` mode: same checks minus (1), then stamps output hashes + code commit (+ dirty flag) +
company-periods + consulted source accessions + denominators into the manifest and regenerates the
report. Run ONCE, deliberately, after a regenerate.

    venv/bin/python scripts/driver_seed/wp1_verify.py            # check
    venv/bin/python scripts/driver_seed/wp1_verify.py --record   # stamp after a regenerate
"""
import os, sys, json, hashlib, collections, argparse, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
import run_code_tier as RC, link_lib as L

D = 'data/driver_catalog_seed/wp1'
MAN = 'data/driver_catalog_seed/wp1_manifest.json'
OUTS = ('code_resolved.jsonl', 'residual.jsonl', 'abstain.jsonl',
        'packets.jsonl', 'skip_ledger.jsonl', 'park_ledger.jsonl', 'sources_ledger.jsonl')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _reconcile(raw_ids, out_ids):
    """BOTH directions (round-13): missing raw ids AND invented extra ids each fail."""
    missing = raw_ids - out_ids
    assert not missing, f"{len(missing)} raw rows produced NO id-carrying outcome"
    extra = out_ids - raw_ids
    assert not extra, f"{len(extra)} INVENTED output ids absent from the raw slice: {sorted(extra)[:3]}"


def _expect_hashes(saved, computed):
    """Check mode: recorded hashes are REQUIRED and COMPARED — never silently replaced."""
    assert saved, "no recorded hashes in the manifest — run --record ONCE after a deliberate regenerate"
    if saved != computed:
        diff = {k: {'recorded': (saved or {}).get(k), 'on_disk': computed.get(k)}
                for k in sorted(set(saved) | set(computed)) if (saved or {}).get(k) != computed.get(k)}
        raise AssertionError("output hash mismatch vs manifest: " + json.dumps(diff)[:500])


def _git_commit():
    try:
        c = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True,
                           text=True, cwd=HERE).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'scripts/driver_seed',
                                'driver/relocation'], capture_output=True, text=True,
                               cwd=os.path.join(HERE, '..', '..')).stdout.strip()
        return c + ('-dirty' if dirty else '')
    except OSError:
        return 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--record', action='store_true',
                    help='stamp hashes/commit/pins into the manifest (after a deliberate regenerate)')
    a = ap.parse_args()
    man = json.load(open(MAN))

    computed = {n: sha(f'{D}/{n}') for n in OUTS}
    if not a.record:
        _expect_hashes(man.get('output_sha256'), computed)

    res = [json.loads(l) for l in open(f'{D}/code_resolved.jsonl')]
    rem = [json.loads(l) for l in open(f'{D}/residual.jsonl')]
    ab = [json.loads(l) for l in open(f'{D}/abstain.jsonl')]
    ledger = [json.loads(l) for l in open(f'{D}/sources_ledger.jsonl')]
    summ = json.load(open(f'{D}/code_summary.json'))

    # completeness vs the run's own summary
    assert (len(res), len(rem), len(ab)) == (summ['records_resolved'], summ['residual'], summ['abstain']), \
        f"counts != summary: {(len(res), len(rem), len(ab))} vs {summ}"

    # reconciliation by distinct raw-row id (both directions)
    rows = [json.loads(l) for l in open('data/driver_catalog_seed/worklist.jsonl')
            if json.loads(l)['ticker'] in set(man['tickers'])]
    slice_sha = hashlib.sha256(''.join(sorted(json.dumps(r, sort_keys=True) for r in rows)).encode()).hexdigest()
    assert slice_sha == man['worklist_slice_sha256'], "worklist slice drifted vs the manifest"
    uniq_rows, dup_dropped = RC.dedupe_rows(rows)
    raw_ids = {RC._iid(r) for r in uniq_rows}
    assert len(raw_ids) == len(uniq_rows), "distinct rows must have distinct whole-row ids"
    out_ids = {r['item_id'] for r in res} | {r['item_id'] for r in rem} | {x['item_id'] for x in ab}
    _reconcile(raw_ids, out_ids)
    byid = collections.defaultdict(set)
    for r in res + rem + ab:
        byid[r['item_id']].add((r.get('kpi') or r.get('raw_label'), str(r.get('value'))))
    bad = {k: v for k, v in byid.items() if len(v) > 1}
    assert not bad, f"ids carrying different (kpi,value): {list(bad.items())[:3]}"

    # round-14 INDEPENDENT no-future-source proof happens INSIDE the live session below: for every
    # ACCEPTED 8-K the pairing is RE-DERIVED from the graph via the certified resolver's own prior
    # query (a different code path from the run's timeline) plus a fresh periodic-window query.
    # The round-13 check compared a label against a target identity computed by the SAME code under
    # test — circular (reviewer catch: WMS's wrong pairing would have passed it).
    cp_accepts = collections.defaultdict(set)

    # mechanical compliance on every resolved record
    fab = [r for r in res if r.get('quote_source') == 'xbrl_fact' or r.get('source') == 'xbrl_fact']
    assert not fab, f"fabricated quotes: {len(fab)}"
    bad_vq = [r for r in res if not L.value_ok(float(r['value']),
                                              None if r['fmt'] == 'number' else r['fmt'], r['quote'])]
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    _INDEP = """
    MATCH (r:Report {accessionNo:$acc})-[:PRIMARY_FILER]->(c:Company)
    OPTIONAL CALL (r, c) {
      MATCH (q:Report)-[:PRIMARY_FILER]->(c)
      WHERE q.formType IN ['10-Q','10-K'] AND date(q.periodOfReport) < date(datetime(r.created))
      WITH q ORDER BY q.periodOfReport DESC LIMIT 1
      RETURN q
    }
    RETURN r.created AS f8, q.accessionNo AS match_acc, q.created AS f10
    """
    from datetime import datetime as _DT

    def _h(a, b):
        return (_DT.fromisoformat(str(b)[:19]) - _DT.fromisoformat(str(a)[:19])).total_seconds() / 3600
    cache, bad_sub = {}, []
    with drv.session() as s:
        # ---- round-15 independent pairing proof for every ACCEPTED 8-K: re-derived STRAIGHT
        # from the graph with an inline query (a different code path than the shared matcher the
        # run imports), plus the production lag window. The round-13/14 checks re-used artifacts
        # of the code under test — circular (reviewer catch). ----
        for row in ledger:
            for e8 in row['eightk']:
                if e8['verdict'] != 'accept':
                    continue
                r2 = s.run(_INDEP, acc=e8['acc']).single()
                assert r2 and r2['match_acc'] == row['filing_acc'], \
                    f"independent pairing mismatch {e8['acc']} ({row['ticker']}): " \
                    f"graph says {r2 and r2['match_acc']}, run accepted {row['filing_acc']}"
                lag = _h(r2['f8'], r2['f10'])
                assert -24 <= lag <= 90 * 24, \
                    f"accepted 8-K outside the production lag window: {e8['acc']} lag={lag:.1f}h"
                cp_accepts[(row['ticker'], row['period'])].add(e8['acc'])
        for r in res:
            if r['source_type'] == '8k':
                assert r['source_id'] in cp_accepts[(r['ticker'], r['period_end'])], \
                    f"8-K record without an accept ledger row in its cp: {r['source_id']} {r['ticker']}"
        for r in rem:
            for cd in r.get('candidates', []):
                if cd.get('src_type') == '8k':
                    assert cd['src'] in cp_accepts[(r['ticker'], r['period'])], \
                        f"8-K candidate without an accept ledger row in its cp: {cd['src']} {r['ticker']}"
        # ---- mechanical compliance on every resolved record ----
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

    # coverage views
    def band(v):
        v = abs(float(v))
        if v == 0: return 'zero'
        if v != int(v): return 'decimal'
        return 'small' if v < 1000 else 'other'
    routes = collections.Counter((r['tier'], r['source_type']) for r in res)
    bands = collections.Counter(band(r['value']) for r in res)
    ab_reason = collections.Counter(x['reason'] for x in ab)
    incomplete = sum(1 for x in ab if x.get('sources_incomplete'))
    uniq_targets = len({(w['ticker'], w['kpi'], w['period']) for w in uniq_rows})
    gate_verdicts = collections.Counter(e['verdict'] for row in ledger for e in row['eightk'])
    src_accessions = sorted({r['source_id'] for r in res}
                            | {r['filing_id'] for r in rem}
                            | {c['src'] for r in rem for c in r.get('candidates', [])}
                            | {row['filing_acc'] for row in ledger}
                            | {e['acc'] for row in ledger for e in row['eightk']
                               if e['verdict'] == 'accept'})

    if a.record:
        man['output_sha256'] = computed
        man['verified_summary'] = summ
        man['code_commit'] = _git_commit()
        man['company_periods'] = sorted(f"{t}|{f}|{p}" for t, f, p in
                                        {(w['ticker'], w['form'], w['period']) for w in uniq_rows})
        man['source_accessions'] = src_accessions
        man['unique_targets_ticker_kpi_period'] = uniq_targets
        man['duplicate_rows_collapsed_in_slice'] = dup_dropped
        json.dump(man, open(MAN, 'w'), indent=1)

    rep = f"""# WP1 Report — regenerated cohort ({','.join(man['tickers'])})

Manifest (incl. output sha256s): `{MAN}` · slice sha `{man['worklist_slice_sha256'][:16]}…`
Command: `{man['command']}` · verifier: `scripts/driver_seed/wp1_verify.py` (CHECK-ONLY by default;
this report is regenerated only by `--record`; all assertions passed or it would have crashed).

## Mechanical compliance (safety checks — NOT precision; true P/R = WP4)
- value-token-in-quote: **{len(res)-len(bad_vq)}/{len(res)}**{'' if not bad_vq else ' VIOLATIONS ' + str(bad_vq[:3])}
- quote-is-exact-source-substring: **{len(res)-len(bad_sub)}/{len(res)}**{'' if not bad_sub else ' VIOLATIONS ' + str(bad_sub[:3])}
- fabricated quotes in THIS cohort: **0** (asserted) · older part1–4 artifacts: **STALE/INVALID**

## Reconciliation by distinct raw-row id (asserted, BOTH directions)
raw rows {len(rows)} ({dup_dropped} identical duplicates collapsed -> {len(uniq_rows)} distinct) =
unique ids {len(raw_ids)}; every id accounted for in resolved/residual/abstain; ZERO invented extra
ids; no id carries two different (kpi,value).
Denominators: **{len(rows)} raw rows** (reconciliation basis) · **{uniq_targets} unique
(ticker,kpi,period) targets** (coverage basis).

## Coverage
resolved {len(res)} (routes: {dict(routes)}) · residual {len(rem)} · abstain {len(ab)}
(reasons: {dict(ab_reason)}; sources_incomplete-flagged: {incomplete})
value bands (resolved): {dict(bands)}
8-K gate verdicts (sources_ledger): {dict(gate_verdicts)}
consulted/used source accessions pinned in manifest: {len(src_accessions)}

## 8-K selection honesty (round-14)
Selection = resolver AUTO_OK (its own benchmark documents a **0.24% warm-start wrong-fire
ceiling** — quarter_identity.py:100-104) AND pure STRUCTURAL PAIRING (the 8-K's certified prior
periodic == the target's predecessor, or the target itself for documented inversions) inside the
announcer window (period_end, next-period filing]. NO fiscal identities/labels anywhere — dei
conventions are inconsistent even within one company (WMS). Every accepted 8-K's pairing +
window is INDEPENDENTLY re-derived from the graph by this verifier (resolver's own prior query —
a different code path than the run's). Zero-error is a MEASURED claim (WP4), never assumed.

run summary: {json.dumps(summ)}
"""
    if a.record:
        open('data/driver_catalog_seed/wp1_report.md', 'w').write(rep)
    print(rep)
    assert not bad_vq and not bad_sub, "mechanical compliance violated"
    print(f"WP1 VERIFY ({'RECORD' if a.record else 'CHECK'}): ALL ASSERTIONS PASSED")


if __name__ == '__main__':
    main()
