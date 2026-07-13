#!/usr/bin/env python3
"""Step 3 — HEADLINE-metric pairs, relocated into a TRANSCRIPT (or news), graded vs the XBRL oracle.
Cross-SOURCE test: lock a headline metric (revenue / net income / EPS / gross profit) from the period's
10-Q, then find it in that period's EARNINGS-CALL transcript (spoken, rounded). Truth = oracle value.
Headline metrics are what calls actually state, so coverage should be high (unlike segment detail).

    venv/bin/python scripts/driver_seed/relocate_probe/prep_headline.py --n 40 --source transcript
"""
import os, sys, json, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, oracle as O, link_lib as L, run_code_tier as RC
from prep_oracle import kind_word
from prep_transcript import fetch_transcript

HERE = os.path.dirname(__file__)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=40)
    ap.add_argument('--source', default='transcript'); ap.add_argument('--per-ticker', type=int, default=4)
    a = ap.parse_args()
    tickers = sorted({json.loads(l)['ticker'] for l in open(f'{HERE}/truth_validation.jsonl')})
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    bdir = f'{HERE}/batches_headline'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    tr = open(f'{HERE}/truth_headline.jsonl', 'w')
    made = ceil = 0
    with drv.session() as s:
        for tk in tickers:
            if made >= a.n:
                break
            ser = O.series(s, tk, 'quarter')
            per_tk = 0
            for (con, mk), pv in ser.items():
                if made >= a.n or per_tk >= a.per_ticker:
                    break
                if mk:
                    continue                                     # HEADLINE only (0-axis)
                for pB in sorted(pv, reverse=True):              # recent quarters first
                    vB = pv[pB]
                    src_texts = fetch_transcript(s, tk, pB)      # target SOURCE = the earnings call
                    if not src_texts:
                        continue
                    xb, txf, _ = RC.fetch_corpus(s, tk, '10-Q', pB)
                    if not txf and not xb:
                        continue
                    txf = txf + RC.fetch_press_release(s, tk, pB)
                    name = kind_word(con)
                    strict, snips = L.scan_text(txf, name, vB, 'number')
                    lock_q = strict          # STRICT lossless lock only — a loose fallback can lock a wrong row (ACMR '8.4%')
                    if not lock_q:
                        continue                                 # can't lock the identity in the filing
                    addr = prep.build_address(name, 'number', 1, txf, lock_q, vB)
                    cands = prep.locate(src_texts, addr)         # candidates from the TRANSCRIPT
                    if not cands:
                        continue
                    json.dump({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number', 'source': a.source,
                               'period_type': 'quarterly', 'period_lock': pB, 'period_target': pB,
                               'address': addr, 'candidates': cands}, open(f'{bdir}/batch_{made}.json', 'w'))
                    tr.write(json.dumps({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number',
                             'period_target': pB, 'value_target': vB, 'source': a.source}) + '\n')
                    if any(L.value_present_rounded(vB, 'number', c['text']) for c in cands):
                        ceil += 1
                    made += 1; per_tk += 1
                    break                                        # one period per (company, concept)
    drv.close(); tr.close()
    kept, dropped = prep.drop_ambiguous(f'{HERE}/truth_headline.jsonl', bdir)
    print(f"ambiguous-name pairs dropped: {dropped} (kept {kept})")
    print(f"headline {a.source} pairs built: {made}")
    print(f"  value present (rounded) in candidates (ceiling): {ceil}/{made} = {100*ceil/max(made,1):.0f}%")


if __name__ == '__main__':
    main()
