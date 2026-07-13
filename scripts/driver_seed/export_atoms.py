#!/usr/bin/env python3
"""Export the seed records as pipeline-ready EVIDENCE ATOMS (PIPE-14 5-tuple + full provenance).

The Driver build pipeline ingests evidence atoms `{company, source_type, source_id, date, quote}`
(10_BuildPipeline.md PIPE-14), with `source_type="fiscal.ai-kpi"` a first-class pseudo-source.
This exporter emits exactly that, and ALSO carries every extra field we have (period, value, unit,
xbrl concept/member, accession, content-node id) so the pipeline has everything it needs to build
BOTH the Driver (name, from the quote) and the DriverUpdate (fact: value/period/scope) — it picks
what it needs, nothing is missing.

`date` is filled with the real filing publication timestamp (fetched from Neo4j) rather than left
empty, so the atoms are DriverUpdate-capable, not catalog-only.

    venv/bin/python scripts/driver_seed/export_atoms.py --part 1
writes data/driver_catalog_seed/part<N>/evidence_atoms.jsonl (+ .csv)
"""
import json, re, os, argparse, csv, sys
sys.path.insert(0, os.path.dirname(__file__))

OUT = 'data/driver_catalog_seed'


def load_env_neo4j():
    for line in open('.env'):
        m = re.match(r'\s*(NEO4J_[A-Z_]+)=(.*)', line)
        if m:
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def slug(s):
    return re.sub(r'_+', '_', re.sub(r'[^a-z0-9]+', '_', (s or '').lower())).strip('_')


def fetch_filing_dates(accessions):
    """{accession: earliest filed_at ISO} from any content node carrying that filing_id."""
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    dates = {}
    with drv.session() as s:
        rows = s.run(
            """UNWIND $accs AS acc
               OPTIONAL MATCH (r:Report {id: acc})
               RETURN acc AS acc, r.created AS d""",
            accs=list(accessions))
        for x in rows:
            if x['d']:
                dates[x['acc']] = str(x['d'])
    drv.close()
    return dates


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--part', type=int, required=True)
    a = ap.parse_args()
    pdir = f'{OUT}/part{a.part}'
    recs = [json.loads(l) for l in open(f'{pdir}/seed_records.jsonl')]

    load_env_neo4j()
    accs = {r['filing_id'] for r in recs if r.get('filing_id')}
    dates = fetch_filing_dates(accs)

    atoms = []
    for r in recs:
        acc = r.get('filing_id')
        atom = {
            # --- PIPE-14 evidence-atom 5-tuple (the required contract) ---
            'company': r['ticker'],
            'source_type': 'fiscal.ai-kpi',
            'source_id': f"fiscal_ai:{r['ticker']}:{slug(r['kpi'])}",
            'date': dates.get(acc, ''),                       # real filing timestamp; '' allowed for this source_type
            'quote': r['quote'],
            # --- full provenance / DriverUpdate inputs (pipeline uses what it needs) ---
            'kpi_name': r['kpi'],                             # fiscal.ai's own name (source_id slug + human ref)
            'value': r['value'],                             # answer key (pipeline re-extracts from quote)
            'fmt': r.get('fmt'),
            'is_currency': r.get('is_currency'),
            'period_end': r['period'],                        # fiscal period end -> fact_scope.period
            'form': r.get('form'),                            # underlying filing form (10-K/10-Q)
            'accession': acc,                                 # real filing event, if the pipeline wants FROM_SOURCE
            'source_node_id': r.get('source_element_id'),     # exact Neo4j content node the quote is in
            'xbrl_concept': r.get('concept'),                 # XBRL qname (T1) -> MAPS_TO_CONCEPT
            'xbrl_member': r.get('member'),                   # dimension member (T1) -> slice/MAPS_TO_MEMBER
            'evidence_kind': r.get('source'),                 # section | exhibit_ex99 | financial_statement | xbrl_fact
            'link_tier': r.get('tier'),                       # T1-xbrl | T2-label | T3-llm (build provenance)
        }
        atoms.append(atom)

    with open(f'{pdir}/evidence_atoms.jsonl', 'w') as fh:
        for x in atoms:
            fh.write(json.dumps(x) + '\n')
    cols = list(atoms[0].keys())
    with open(f'{pdir}/evidence_atoms.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for x in atoms:
            w.writerow(x)

    n_date = sum(1 for x in atoms if x['date'])
    print(json.dumps({
        'atoms': len(atoms),
        'with_real_date': n_date,
        'date_coverage_pct': round(100 * n_date / max(len(atoms), 1), 1),
        'distinct_source_ids': len({x['source_id'] for x in atoms}),
        'companies': len({x['company'] for x in atoms}),
    }, indent=2))
    print("example atom:\n", json.dumps(atoms[0], indent=2)[:700])


if __name__ == '__main__':
    main()
