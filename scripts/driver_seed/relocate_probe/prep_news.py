#!/usr/bin/env python3
"""PARKED (user decision 2026-07-14): NEWS IS A SEPARATE TRACK — design lives in news_track/
(GPT taxonomy + census + samples). This builder + the frozen news benchmark (100% precision,
5/18 recall baseline) are the EVIDENCE TO BEAT, not the path forward. The filing/transcript
algorithm is locked and must not grow news-specific logic.

NEWS-source pairs: lock a headline metric in the period's 10-Q (strict), relocate into NEWS articles
covering that period's earnings (created within [period_end, +90d]); truth = XBRL oracle. Census 2026-07-13:
10/10 tickers had headline revenue verbatim/rounded in coverage articles — news is a rich day-0 source.

    venv/bin/python scripts/driver_seed/relocate_probe/prep_news.py --n 40
"""
import os, sys, json, glob, argparse
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, oracle as O, link_lib as L, run_code_tier as RC
from prep_oracle import kind_word

HERE = os.path.dirname(__file__)


def fetch_news(session, ticker, period_end, days=90, limit=150):
    hi = (date.fromisoformat(period_end) + timedelta(days=days)).isoformat()
    rows = session.run("""MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker:$tk})
                          WHERE n.created >= $lo AND n.created <= $hi
                          RETURN n.title AS t, n.teaser AS te, n.body AS b
                          ORDER BY n.created LIMIT $lim""",
                       tk=ticker, lo=period_end, hi=hi, lim=limit).data()
    return [' '.join(filter(None, [r['t'], r['te'], r['b']])) for r in rows]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=40)
    ap.add_argument('--per-ticker', type=int, default=3); a = ap.parse_args()
    tickers = sorted({json.loads(l)['ticker'] for l in open(f'{HERE}/truth_validation.jsonl')})
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    bdir = f'{HERE}/batches_news'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    tr = open(f'{HERE}/truth_news.jsonl', 'w')
    made = ceil = 0
    with drv.session() as s:
        for tk in tickers:
            if made >= a.n:
                break
            ser = O.series(s, tk, 'quarter')
            per_tk = 0
            from prep_oracle import CANON
            ordered = sorted(ser.items(), key=lambda kv: (kv[0][0].split(':')[-1] not in CANON, kv[0][0]))
            cache = {}
            for (con, mk), pv in ordered:
                if made >= a.n or per_tk >= a.per_ticker:
                    break
                if mk:
                    continue                                     # headline metrics — what news reports
                for pB in sorted(pv, reverse=True)[:2]:          # 2 most-recent quarters, else move on
                    vB = pv[pB]
                    if pB not in cache:                          # fetch once per (ticker, period)
                        nw = fetch_news(s, tk, pB)
                        xb0, tx0, _ = RC.fetch_corpus(s, tk, '10-Q', pB)
                        cache[pB] = (nw, xb0, tx0 + RC.fetch_press_release(s, tk, pB) if (tx0 or xb0) else [])
                    news, xb, txf = cache[pB]
                    if not news or (not txf and not xb):
                        continue
                    name = kind_word(con)
                    strict, snips = L.scan_text(txf, name, vB, 'number')
                    lock_q = strict          # STRICT lossless lock only
                    if not lock_q:
                        continue
                    addr = prep.build_address(name, 'number', 1, txf, lock_q, vB, measurement='gaap')
                    cands = prep.locate(news, addr, keep=40)   # ~400 chunks/company -> keep=40 (their benchmark setting)
                    if not cands:
                        continue
                    json.dump({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number', 'source': 'news',
                               'period_type': 'quarterly', 'period_lock': pB, 'period_target': pB,
                               'address': addr, 'candidates': cands}, open(f'{bdir}/batch_{made}.json', 'w'))
                    tr.write(json.dumps({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number',
                             'period_target': pB, 'value_target': vB, 'source': 'news'}) + '\n')
                    if any(L.value_present_rounded(vB, 'number', c['text']) for c in cands):
                        ceil += 1
                    made += 1; per_tk += 1
                    break
    drv.close(); tr.close()
    kept, dropped = prep.drop_ambiguous(f'{HERE}/truth_news.jsonl', bdir)
    print(f"ambiguous-name pairs dropped: {dropped} (kept {kept})")
    print(f"news pairs built: {made}")
    print(f"  value present in candidates (ceiling): {ceil}/{made} = {100*ceil/max(made,1):.0f}%")


if __name__ == '__main__':
    main()
