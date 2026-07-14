#!/usr/bin/env python3
"""MINI-EXAM fresh strata builder (grand cert): UNSEEN companies (ticker > 'D', never in any design
set), canonical headline metrics, strict locks, hybrid addresses, oracle truth. Two strata:

    venv/bin/python scripts/driver_seed/relocate_probe/prep_exam.py --stratum annual     --n 60
    venv/bin/python scripts/driver_seed/relocate_probe/prep_exam.py --stratum transcript --n 25
"""
import os, sys, json, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, oracle as O, link_lib as L, run_code_tier as RC
from prep_oracle import kind_word, CANON
from prep_transcript import fetch_transcript

HERE = os.path.dirname(__file__)


def fresh_tickers(session, form, need=80):
    """companies NEVER used in design (ticker > 'D'), having >=2 filings of `form` with XBRL."""
    rows = session.run("""MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company)
                          WHERE c.ticker > 'D'
                          WITH c.ticker AS tk, count(r) AS n WHERE n >= 2
                          RETURN tk ORDER BY tk LIMIT $need""", form=form, need=need).data()
    return [r['tk'] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stratum', required=True, choices=('annual', 'transcript'))
    ap.add_argument('--n', type=int, default=60); a = ap.parse_args()
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    dset = f'exam_{a.stratum}'
    bdir = f'{HERE}/batches_{dset}'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    tr = open(f'{HERE}/truth_{dset}.jsonl', 'w')
    form = '10-K' if a.stratum == 'annual' else '10-Q'
    kind = 'annual' if a.stratum == 'annual' else 'quarter'
    made = ceil = 0
    with drv.session() as s:
        for tk in fresh_tickers(s, form):
            if made >= a.n:
                break
            ser = O.series(s, tk, kind)
            ordered = sorted(ser.items(), key=lambda kv: (kv[0][0].split(':')[-1] not in CANON, kv[0][0]))
            per_tk = 0; cache = {}
            for (con, mk), pv in ordered:
                if made >= a.n or per_tk >= 3:
                    break
                if mk:
                    continue                                     # headline canonical metrics
                pers = sorted(pv)
                if len(pers) < 2:
                    continue
                if a.stratum == 'annual':
                    pA, pB = pers[-2], pers[-1]
                    if pv[pA] == pv[pB]:
                        continue
                else:
                    pA = pB = pers[-1]
                vA, vB = pv[pA], pv[pB]
                if pA not in cache:
                    xbA, txA, _ = RC.fetch_corpus(s, tk, form, pA)
                    cache[pA] = txA + RC.fetch_press_release(s, tk, pA) if (txA or xbA) else []
                txA = cache[pA]
                if not txA:
                    continue
                if a.stratum == 'annual':
                    if pB not in cache:
                        xbB, txB, _ = RC.fetch_corpus(s, tk, form, pB)
                        cache[pB] = txB + RC.fetch_press_release(s, tk, pB) if (txB or xbB) else []
                    target_texts = cache[pB]
                else:
                    target_texts = fetch_transcript(s, tk, pB)
                if not target_texts:
                    continue
                name = kind_word(con)
                strict, _ = L.scan_text(txA, name, vA, 'number')
                if not strict:
                    continue                                     # strict lossless lock only
                addr = prep.build_address(name, 'number', 1, txA, strict, vA, measurement='gaap')
                cands = prep.locate(target_texts, addr, keep=12)
                if not cands:
                    continue
                json.dump({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number', 'source': a.stratum,
                           'period_type': 'annual' if a.stratum == 'annual' else 'quarterly',
                           'period_lock': pA, 'period_target': pB,
                           'address': addr, 'candidates': cands}, open(f'{bdir}/batch_{made}.json', 'w'))
                tr.write(json.dumps({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number',
                         'period_target': pB, 'value_target': vB}) + '\n')
                if any(L.value_present_rounded(vB, 'number', c['text']) for c in cands):
                    ceil += 1
                made += 1; per_tk += 1
    drv.close(); tr.close()
    kept, dropped = prep.drop_ambiguous(f'{HERE}/truth_{dset}.jsonl', bdir)
    print(f"[{dset}] built {made} (dropped {dropped} ambiguous) | ceiling {ceil}/{made} = {100*ceil/max(made,1):.0f}%")


if __name__ == '__main__':
    main()
