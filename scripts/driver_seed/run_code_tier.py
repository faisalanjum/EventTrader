#!/usr/bin/env python3
"""Code tier (0 LLM tokens): resolve KPI->quote deterministically from Neo4j XBRL + sections.

Per company-period it fetches the 10-Q/10-K's FinancialStatementContent (XBRL JSON) and
ExtractedSectionContent (MD&A text), then runs the certified Tier-1 (XBRL) + Tier-2 (text
label) with the value gates from link_lib. Gate-clean hits -> code_resolved.jsonl. Everything
else -> residual.jsonl (handed to the batched LLM tier, which also reaches the 8-K press
release the code tier skips). Plugs (tiny number values) -> abstain.

    venv/bin/python scripts/driver_seed/run_code_tier.py --part 1 --nparts 4

Reads data/driver_catalog_seed/worklist.jsonl; writes data/driver_catalog_seed/part<N>/.
"""
import os, re, json, argparse, collections, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import link_lib as L

OUT = 'data/driver_catalog_seed'


def fetch_press_release(session, tk, period):
    """earnings 8-K EX-99.1 filed ~5-75 days AFTER the fiscal period end (announce-date offset)."""
    try:
        d0 = date.fromisoformat(period[:10])
    except ValueError:
        return []
    lo = (d0 + timedelta(days=5)).isoformat(); hi = (d0 + timedelta(days=75)).isoformat()
    rows = list(session.run(
        """MATCH (r:Report {formType:'8-K'})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport >= $lo AND r.periodOfReport <= $hi
           MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
           WHERE e.exhibit_number IN ['EX-99.1','EX-99','99.1']
           RETURN e.content AS content ORDER BY r.periodOfReport LIMIT 3""",
        tk=tk, lo=lo, hi=hi))
    return [x['content'] for x in rows if x['content']]


def load_env_neo4j():
    for line in open('.env'):
        m = re.match(r'\s*(NEO4J_[A-Z_]+)=(.*)', line)
        if m:
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def fetch_corpus(session, tk, form, period):
    """xbrls (list of JSON strings), texts (list of section strings), filing_ids."""
    rows = list(session.run(
        """MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport STARTS WITH $period
           OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
           OPTIONAL MATCH (r)-[:HAS_SECTION]->(x:ExtractedSectionContent)
           RETURN elementId(r) AS report_eid,
                  collect(DISTINCT f.value)      AS xbrls,
                  collect(DISTINCT x.content)    AS texts,
                  collect(DISTINCT f.filing_id)  AS ffids,
                  collect(DISTINCT x.filing_id)  AS xfids""",
        form=form, tk=tk, period=period))
    xbrls, texts, fids = [], [], []
    for r in rows:
        xbrls += [v for v in r['xbrls'] if v]
        texts += [v for v in r['texts'] if v]
        fids += [v for v in (r['ffids'] + r['xfids']) if v]
        if r['report_eid']:
            fids.append(r['report_eid'])
    # prefer a real filing_id (content node) over the report elementId, keep both
    seen = []
    for f in fids:
        if f not in seen:
            seen.append(f)
    return xbrls, texts, seen


def process_cp(items, xbrls, texts, filing_ids):
    """route each KPI in a company-period through the certified tiers. Returns (resolved, residual, abstain)."""
    resolved, residual, abstain = [], [], []
    fid = filing_ids[0] if filing_ids else None
    for it in items:
        name, val, fmt = it['kpi'], it['value'], it['fmt']
        per = it['period']
        base = {'ticker': it['ticker'], 'kpi': name, 'value': val, 'fmt': fmt, 'period': per,
                'form': it['form'], 'is_currency': it['is_currency'], 'category': it.get('category', ''),
                'filing_id': fid}
        if val is None:
            continue
        if L.is_derived(name):          # fiscal.ai-computed; no verbatim quote can exist
            abstain.append({**base, 'status': 'not_applicable', 'reason': 'derived_metric'}); continue
        if fmt in (None, 'number') and abs(float(val)) <= 1000:
            abstain.append({**base, 'status': 'no_evidence', 'reason': 'plug'}); continue
        t1 = L.tier1(xbrls, name, val, per) if (xbrls and fmt != '%') else None
        strict, snips = L.scan_text(texts, name, val, fmt)
        if t1 and not strict:
            # XBRL matched but the KPI's own wording isn't next to the number in the text.
            # Retry using the filer's own dimension-member wording as the label.
            strict = L.row_quote(texts, L.member_tokens([t1['member']]), val, fmt)
        if t1 and strict:
            rec = {**base, 'tier': 'T1-xbrl', 'member': t1['member'].split(':')[-1],
                   'concept': t1['concept'], 'quote': strict, 'source': 'section',
                   'xbrl_fact': t1['quote']}
        elif t1:
            rec = {**base, 'tier': 'T1-xbrl', 'member': t1['member'].split(':')[-1],
                   'concept': t1['concept'], 'quote': t1['quote'], 'source': 'xbrl_fact',
                   'xbrl_fact': t1['quote']}
        elif strict:
            rec = {**base, 'tier': 'T2-label', 'quote': strict, 'source': 'section'}
        elif snips:
            residual.append({**base, 'candidates': snips}); continue
        else:
            abstain.append({**base, 'status': 'no_evidence', 'reason': 'value_absent'}); continue
        # deterministic value gate; gate-fails fall to residual
        if L.value_ok(val, fmt, rec['quote']):
            resolved.append(rec)
        else:
            residual.append({**base, 'candidates': snips, 'gatefail_quote': rec['quote']})
    return resolved, residual, abstain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', type=int, required=True)
    ap.add_argument('--nparts', type=int, default=4)
    a = ap.parse_args()

    work = [json.loads(l) for l in open(f'{OUT}/worklist.jsonl')]
    tickers = sorted({w['ticker'] for w in work})
    # deterministic contiguous split
    chunk = (len(tickers) + a.nparts - 1) // a.nparts
    part_tickers = set(tickers[(a.part-1)*chunk: a.part*chunk])
    work = [w for w in work if w['ticker'] in part_tickers]
    cps = collections.defaultdict(list)
    for w in work:
        cps[(w['ticker'], w['form'], w['period'])].append(w)
    print(f"part {a.part}/{a.nparts}: {len(part_tickers)} tickers, {len(work)} instances, {len(cps)} company-periods")

    load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))

    pdir = f'{OUT}/part{a.part}'
    os.makedirs(pdir, exist_ok=True)
    R = open(f'{pdir}/code_resolved.jsonl', 'w')
    RES = open(f'{pdir}/residual.jsonl', 'w')
    AB = open(f'{pdir}/abstain.jsonl', 'w')
    nR = nRes = nAb = 0
    stats = collections.Counter()
    with drv.session() as s:
        for i, ((tk, form, period), items) in enumerate(sorted(cps.items())):
            xbrls, texts, fids = fetch_corpus(s, tk, form, period)
            texts = texts + fetch_press_release(s, tk, period)   # + 8-K earnings release tables
            if not xbrls and not texts:
                for it in items:
                    AB.write(json.dumps({**it, 'status': 'no_evidence', 'reason': 'corpus_missing'}) + '\n'); nAb += 1
                stats['cp_no_corpus'] += 1
                continue
            resolved, residual, abstain = process_cp(items, xbrls, texts, fids)
            for r in resolved: R.write(json.dumps(r) + '\n'); nR += 1
            for r in residual: RES.write(json.dumps(r) + '\n'); nRes += 1
            for r in abstain: AB.write(json.dumps(r) + '\n'); nAb += 1
            stats[('tier', 'T1')] += sum(1 for r in resolved if r['tier'] == 'T1-xbrl')
            stats[('tier', 'T2')] += sum(1 for r in resolved if r['tier'] == 'T2-label')
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(cps)} company-periods  resolved={nR} residual={nRes} abstain={nAb}")
    drv.close()
    R.close(); RES.close(); AB.close()
    tot = nR + nRes + nAb
    summary = {'part': a.part, 'instances': tot, 'company_periods': len(cps),
               'code_resolved': nR, 'residual_to_llm': nRes, 'abstain': nAb,
               'T1_xbrl': stats[('tier', 'T1')], 'T2_label': stats[('tier', 'T2')],
               'cp_no_corpus': stats['cp_no_corpus'],
               'code_pct': round(100*nR/max(tot, 1), 1)}
    json.dump(summary, open(f'{pdir}/code_summary.json', 'w'), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
