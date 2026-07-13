#!/usr/bin/env python3
"""Step 2 — QUARTERLY certification pairs from the XBRL oracle (0 LLM to build).
Leave-one-out across quarters: lock a metric in quarter A's 10-Q (address from the filer's OWN words,
found via value_A), relocate into quarter B's 10-Q; truth = oracle value_B; also record B's YTD (183/273d)
value as a labeled distractor so the grader can flag 3-month-vs-YTD misbinds. Reuses prep + oracle + link_lib.

    venv/bin/python scripts/driver_seed/relocate_probe/prep_oracle.py --n 40
"""
import os, re, sys, json, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, oracle as O, link_lib as L, run_code_tier as RC

HERE = os.path.dirname(__file__)


def kind_word(con):
    """concept qname -> a plain metric-kind label (universal financial vocab, not per-company)."""
    c = con.lower()
    for key, w in (('revenue', 'revenue'), ('sales', 'revenue'), ('grossprofit', 'gross profit'),
                   ('operatingincome', 'operating income'), ('operatingprofit', 'operating income'),
                   ('netincome', 'net income'), ('profitloss', 'net income'),
                   ('earningspershare', 'earnings per share'), ('costofgoods', 'cost'),
                   ('costofrevenue', 'cost'), ('assets', 'assets')):
        if key in c:
            return w
    return ' '.join(re.findall(r'[A-Z][a-z]+', con)).lower() or c


def row_label(quote, value):
    """the FILER'S OWN words for this row — alphabetic tokens just before the value in the lock quote
    (Fable's fix: use the filing's wording, not the XBRL-qname-derived name, esp. for multi-axis)."""
    for f in L._tableforms(value, 'number'):
        m = re.search(r'(?<![\d.,])' + re.escape(f) + r'(?![\d.,])', quote)
        if m:
            toks = re.findall(r"[A-Za-z][A-Za-z&]+", quote[max(0, m.start() - 70):m.start()])
            return ' '.join(toks[-6:])
    return ''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=40)
    ap.add_argument('--per-ticker', type=int, default=3); a = ap.parse_args()
    tickers = sorted({json.loads(l)['ticker'] for l in open(f'{HERE}/truth_validation.jsonl')})
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    bdir = f'{HERE}/batches_quarterly'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    tr = open(f'{HERE}/truth_quarterly.jsonl', 'w')
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
                pers = sorted(pv)
                if len(pers) < 2:
                    continue
                pA, pB = pers[-2], pers[-1]; vA, vB = pv[pA], pv[pB]
                if vA == vB:
                    continue                                     # need distinct values for a real test
                search_name = kind_word(con) + ((' ' + ' '.join(sorted(mk))) if mk else '')
                xbA, txA, _ = RC.fetch_corpus(s, tk, '10-Q', pA)
                xbB, txB, _ = RC.fetch_corpus(s, tk, '10-Q', pB)
                if (not txA and not xbA) or (not txB and not xbB):
                    continue                                     # both need their own 10-Q
                txA = txA + RC.fetch_press_release(s, tk, pA); txB = txB + RC.fetch_press_release(s, tk, pB)
                strict, snips = L.scan_text(txA, search_name, vA, 'number')
                lock_q = strict or (snips[0] if snips else None)
                if not lock_q:
                    continue                                     # can't lock value_A -> skip
                # IDENTITY = metric-kind (from concept) + XBRL member tokens (the filer's segment names).
                # NOTE: tried deriving the label from the lock-quote row words (row_label) — it grabbed
                # NEIGHBOURING cells for TOTAL lines (headline 93%->62%), so reverted to the derived name.
                name = search_name
                addr = prep.build_address(name, 'number', 1, txA, lock_q, vA)
                cands = prep.locate(txB, addr)
                if not cands:
                    continue
                ytd = O.clean_facts(xbB, 'ytd').get((con, mk), {}).get(pB)
                json.dump({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number', 'source': '10-Q',
                           'period_type': 'quarterly', 'period_lock': pA, 'period_target': pB,
                           'address': addr, 'candidates': cands}, open(f'{bdir}/batch_{made}.json', 'w'))
                tr.write(json.dumps({'id': made, 'ticker': tk, 'kpi': name, 'fmt': 'number',
                         'period_target': pB, 'value_target': vB, 'value_lock': vA, 'ytd_distractor': ytd,
                         'type': 'multi-axis' if len(mk) > 1 else ('segment' if mk else 'headline')}) + '\n')
                if any(L.value_ok(vB, 'number', c['text']) for c in cands):
                    ceil += 1
                made += 1; per_tk += 1
    drv.close(); tr.close()
    print(f"quarterly pairs built: {made}")
    print(f"  target value in candidates (ceiling): {ceil}/{made} = {100*ceil/max(made,1):.0f}%")


if __name__ == '__main__':
    main()
