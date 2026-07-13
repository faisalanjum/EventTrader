#!/usr/bin/env python3
"""Build the addressable KPI->quote work-list: every fiscal.ai KPI value that has a
matching filing in Neo4j.

Source of truth = raw fiscal.ai snapshots (full per-period history; free tier populates
only the latest ~2-3 periods). We keep every non-null (ticker, kpi, section, date, value)
and keep it only if Neo4j has the matching filing:
  Quarterly@date -> 10-Q with periodOfReport=date
  Annual@date    -> 10-K with periodOfReport=date
Periods Neo4j lacks (it runs ~1 quarter behind fiscal.ai) or LTM/TTM columns dated at a
quarter-end simply fall out here (no matching filing) and are reported as out-of-corpus.

Run with the project venv (has the neo4j driver):
    venv/bin/python scripts/driver_seed/build_worklist.py
"""
import gzip, json, glob, re, os, csv, collections, sys

RUN = 'data/fiscal_ai_segments/runs/2026-07-10'
OUT = 'data/driver_catalog_seed'
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
FORM = {'Quarterly': '10-Q', 'Annual': '10-K'}


def load_env_neo4j():
    for line in open('.env'):
        m = re.match(r'\s*(NEO4J_[A-Z_]+)=(.*)', line)
        if m:
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def ticker_of(path):
    base = os.path.basename(path)
    # "NasdaqGS-AAPL_quarterly.json.gz" -> "AAPL"
    stem = base.split('_')[0]
    return stem.split('-')[-1]


def extract_instances():
    """yield dict per non-null (ticker, kpi, section, date, value, fmt, is_currency)."""
    inst = []
    for f in sorted(glob.glob(f'{RUN}/raw/*.json.gz')):
        tk = ticker_of(f)
        try:
            d = json.load(gzip.open(f))
        except Exception as e:
            print(f"  WARN unreadable {f}: {e}", file=sys.stderr); continue
        data = (d.get('pageProps', {}).get('segmentsData', {}) or {}).get('data', {})
        for section, blocks in data.items():
            if section not in FORM:
                continue
            for cat, block in (blocks or {}).items():
                for row in block.get('rows', []):
                    met = row.get('metric', {})
                    nm = met.get('metricName') or met.get('name')
                    if not nm:
                        continue
                    for k, v in row.items():
                        if DATE.match(k) and isinstance(v, dict) and v.get('value') is not None:
                            inst.append({
                                'ticker': tk, 'kpi': nm, 'section': section, 'form': FORM[section],
                                'period': k, 'value': v['value'],
                                'fmt': met.get('format', 'number'),
                                'is_currency': 1 if met.get('isCurrency') else 0,
                                'category': met.get('category', ''),
                                'tag': met.get('metricTag', ''),
                            })
    return inst


def neo4j_periods(tickers):
    """{ticker: {(formType, periodOfReport)}} for 10-Q/10-K present in Neo4j."""
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    avail = collections.defaultdict(set)
    with drv.session() as s:
        rows = s.run(
            """MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
               WHERE c.ticker IN $tks AND r.formType IN ['10-Q','10-K']
                 AND r.periodOfReport IS NOT NULL
               RETURN c.ticker AS tk, r.formType AS form, r.periodOfReport AS por""",
            tks=list(tickers))
        for x in rows:
            avail[x['tk']].add((x['form'], x['por'][:10]))
    drv.close()
    return avail


def main():
    os.makedirs(OUT, exist_ok=True)
    inst = extract_instances()
    tickers = sorted({i['ticker'] for i in inst})
    print(f"raw instances (non-null): {len(inst)} across {len(tickers)} tickers")
    load_env_neo4j()
    avail = neo4j_periods(tickers)

    work, oob = [], []
    for i in inst:
        if (i['form'], i['period']) in avail.get(i['ticker'], ()):
            work.append(i)
        else:
            oob.append(i)

    with open(f'{OUT}/worklist.jsonl', 'w') as fh:
        for w in work:
            fh.write(json.dumps(w) + '\n')

    # coverage report
    by_tk = collections.Counter(w['ticker'] for w in work)
    cov = {
        'raw_instances': len(inst),
        'addressable': len(work),
        'out_of_corpus': len(oob),
        'tickers_total': len(tickers),
        'tickers_with_work': len(by_tk),
        'company_periods': len({(w['ticker'], w['form'], w['period']) for w in work}),
    }
    json.dump(cov, open(f'{OUT}/worklist_coverage.json', 'w'), indent=2)
    print(json.dumps(cov, indent=2))
    # tickers with ZERO overlap (Neo4j missing them entirely) — flag for May-fetch fallback
    zero = sorted(set(tickers) - set(by_tk))
    json.dump(zero, open(f'{OUT}/tickers_no_neo4j.json', 'w'), indent=2)
    print(f"tickers with NO Neo4j overlap: {len(zero)} (saved to tickers_no_neo4j.json)")


if __name__ == '__main__':
    main()
