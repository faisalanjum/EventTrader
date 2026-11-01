"""Read-only, resumable metadata export. No AI or Neo4j writes."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import time
from contextlib import closing
from verify import verify as verify_result

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, separators=(',', ':'), ensure_ascii=False))
    temp.replace(path)


def classify_result(result):
    summary = result['summary']
    unsupported = set(summary.get('unsupported_namespaces', []))
    failed = {r['namespace'] for r in result.get('documentation_entrypoints', []) if not r['loaded']}
    errors = summary.get('load_errors', [])
    for row in result.get('elements', []):
        if not row['documentation']:
            row['documentation_status'] = ('retrieval_failed' if errors or row['namespace'] in failed
                                           else 'unsupported' if row['namespace'] in unsupported else 'absent')
    summary['documentation_status_counts'] = dict(Counter(r['documentation_status'] for r in result.get('elements', [])))
    return 'partial' if unsupported or failed or errors else 'complete'


def run_batch(reports, out, export, code_id):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    accessions = [r['accession'] for r in reports]
    if len(set(accessions)) != len(accessions) or any(not re.fullmatch(r'\d{10}-\d{2}-\d{6}', a) for a in accessions):
        raise ValueError('Inputs must have unique valid SEC accession numbers')
    started = time.monotonic()
    summary = {'read_only': True, 'code_id': code_id, 'processed': 0, 'skipped': 0, 'reports': []}
    for report in reports:
        accession = report['accession']
        path = out / (accession + '_result.json')
        receipt_path = out / (accession + '_receipt.json')
        request_id = digest({'report': report, 'code_id': code_id})
        try:
            receipt = json.loads(receipt_path.read_text())
            valid = (receipt['request_id'] == request_id and receipt['status'] == 'complete'
                     and receipt.get('acceptance_status') == 'accepted'
                     and hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256'])
        except (OSError, ValueError, KeyError, TypeError):
            valid = False
        if valid:
            summary['skipped'] += 1
            summary['reports'].append(dict(receipt, skipped=True))
            print(f"SKIP {report['ticker']} {accession}", flush=True)
            continue
        before = time.monotonic()
        try:
            result = export(report)
            status = classify_result(result)
            result['extraction_status'] = status
            validation = verify_result(result)
            if status == 'complete' and validation['source_status'] == 'passed':
                result.update(acceptance_status='accepted', verification=validation)
            else:
                status = 'abstained'
                result = {'summary': report, 'extraction_status': result['extraction_status'],
                          'acceptance_status': 'abstained', 'verification': validation}
        except Exception as exc:
            status = 'error'
            result = {'summary': report, 'extraction_status': 'error', 'acceptance_status': 'abstained',
                      'error_type': type(exc).__name__, 'error': str(exc)}
        save(path, result)
        receipt = {'accession': accession, 'ticker': report['ticker'], 'request_id': request_id,
                   'status': status, 'acceptance_status': result['acceptance_status'],
                   'seconds': round(time.monotonic() - before, 3),
                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'summary': result['summary']}
        save(receipt_path, receipt)
        summary['processed'] += 1
        summary['reports'].append(dict(receipt, skipped=False))
        print(f"{status.upper()} {report['ticker']} {accession} {receipt['seconds']}s", flush=True)
        save(out / 'batch_summary.json', summary)
    summary['seconds'] = round(time.monotonic() - started, 3)
    summary['status_counts'] = dict(Counter(r['status'] for r in summary['reports']))
    save(out / 'batch_summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, default=HERE / 'reports.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    from dotenv import load_dotenv
    from neo4j import GraphDatabase
    import metadata_audit
    load_dotenv(ROOT / '.env')
    args.out.mkdir(parents=True, exist_ok=True)
    metadata_audit.OUT = args.out
    versions = {p: importlib.metadata.version(p) for p in ('arelle-release', 'neo4j', 'lxml')}
    code_id = digest({'sources': {name: (HERE / name).read_text() for name in ('batch.py', 'metadata_audit.py', 'verify.py', 'source_notices.json')},
                      'dependencies': versions})
    with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD']),
                              connection_timeout=10, max_transaction_retry_time=0) as driver, \
            closing(metadata_audit.controller_for('batch')) as controller:
        result = run_batch(json.loads(args.reports.read_text()), args.out,
                           lambda r: metadata_audit.run_report(r, driver, controller), code_id)
    print(json.dumps({k: v for k, v in result.items() if k != 'reports'}), flush=True)
    return 0 if all(r['status'] == 'complete' for r in result['reports']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
