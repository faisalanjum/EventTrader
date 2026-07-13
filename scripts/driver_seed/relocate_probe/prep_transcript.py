#!/usr/bin/env python3
"""Phase 6 (B) — build TRANSCRIPT-target batches by REUSING the certified filing addresses.

For each existing validation pair, keep the lock ADDRESS but replace the candidates with snippets
located in the company's earnings-call TRANSCRIPT (PreparedRemark + QAExchange text) for the target
period. Everything else (the shape-neutral reader, the honest rounded-tolerant ruler) is reused.

    venv/bin/python scripts/driver_seed/relocate_probe/prep_transcript.py --n 40
Writes batches_transcript/batch_<i>.json + truth_transcript.jsonl (truth copied from validation).
"""
import os, re, sys, json, glob, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, link_lib as L
import run_code_tier as RC

HERE = os.path.dirname(__file__)


def fetch_transcript(session, ticker, period_target):
    """earnings-call text (prepared remarks + Q&A) for the target period — the call(s) held within
    ~120 days AFTER the period end (that Q4/annual call recaps the full year). Match on the ISO
    conference_datetime date prefix (fiscal_year is a comma-formatted string, unreliable)."""
    from datetime import date, timedelta
    d0 = date.fromisoformat(period_target[:10])
    lo, hi = d0.isoformat(), (d0 + timedelta(days=120)).isoformat()
    rows = list(session.run(
        """MATCH (tr:Transcript {symbol:$tk})
           WHERE substring(tr.conference_datetime,0,10) >= $lo AND substring(tr.conference_datetime,0,10) <= $hi
           MATCH (tr)-[]-(x) WHERE x:PreparedRemark OR x:QAExchange
           RETURN x.content AS c""",
        tk=ticker, lo=lo, hi=hi))
    return [r['c'] for r in rows if r['c']]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=40); a = ap.parse_args()
    truth = {t['id']: t for t in (json.loads(l) for l in open(f'{HERE}/truth_validation.jsonl'))}
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    bdir = f'{HERE}/batches_transcript'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    tr_out = open(f'{HERE}/truth_transcript.jsonl', 'w')
    made = has_txt = val_in_cand = 0
    tcache = {}
    with drv.session() as s:
        for i in sorted(truth):
            if made >= a.n:
                break
            fv = f'{HERE}/batches_validation/batch_{i}.json'
            if not os.path.exists(fv):
                continue
            b = json.load(open(fv)); t = truth[i]
            key = (t['ticker'], t['period_target'][:4])
            if key not in tcache:
                tcache[key] = fetch_transcript(s, t['ticker'], t['period_target'])
            texts = tcache[key]
            if not texts:
                continue
            has_txt += 1
            cands = prep.locate(texts, b['address'])          # same locator; prose path (digit windows)
            if not cands:
                continue
            present = any(L.value_ok(t['value_target'], t['fmt'], c['text']) for c in cands)
            val_in_cand += 1 if present else 0
            nb = {'id': i, 'ticker': t['ticker'], 'kpi': t['kpi'], 'fmt': t['fmt'],
                  'source': 'transcript', 'period_type': b['period_type'],
                  'period_target': t['period_target'], 'address': b['address'], 'candidates': cands}
            json.dump(nb, open(f'{bdir}/batch_{i}.json', 'w'))
            tr_out.write(json.dumps(t) + '\n')
            made += 1
    drv.close(); tr_out.close()
    print(f"transcript batches built: {made}")
    print(f"  had transcript text: {has_txt}")
    print(f"  target value present in located candidates: {val_in_cand}/{made} = "
          f"{100*val_in_cand/max(made,1):.0f}%   (this is the transcript recall ceiling)")


if __name__ == '__main__':
    main()
