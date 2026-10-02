"""Acquire every listed SEC filing overnight: package + SEC file list, resumable, safe stops.

No conversion, AI or database writes. One line per finished filing in results.jsonl;
progress.json is rewritten after each filing for monitoring. Re-running the same
command resumes: finished filings are skipped and saved responses make no requests.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time

from driver.prepare.acquire import AcquisitionError, StorageError, acquire, read_package, _identity, _url
from driver.prepare.campaign import Campaign
from driver.prepare.inventory import compare_inventory, parse_index
from driver.prepare.transport import DownloadError


def _progress(output, value):
    temporary = output / 'progress.json.pending'
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, output / 'progress.json')


# This disk also serves the Kubernetes control plane: kubelet evicts pods below 15% free
# (150.6 GB of 1,004 GB). 162 GB keeps ~11 GB clear of that line.
def run(inputs, output, *, live=False, every=1, limit=None, min_free_gb=162,
        max_consecutive_failures=20, requests_per_second=5, campaign_class=Campaign):
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=True)
    filings = json.loads(Path(inputs).read_text())['filings'][::every][:limit]
    results = output / 'results.jsonl'
    finished = [json.loads(line) for line in results.read_text().splitlines()] if results.exists() else []
    done, counts = {row['acc'] for row in finished}, Counter(row['status'] for row in finished)
    streak, stop, started = 0, None, time.monotonic()
    reserve = int(min_free_gb * 1e9)
    with campaign_class(output / 'campaign', live=live, requests_per_second=requests_per_second,
                        minimum_free_bytes=reserve) as campaign, results.open('a') as log:
        for position, filing in enumerate(filings, 1):
            if filing['acc'] in done:
                continue
            accession, cik, form = filing['acc'], filing['cik'], filing['form']
            row, began = dict(acc=accession, form=form, cik=cik), time.monotonic()
            try:
                package_url = _url(_identity(accession, cik, form))
                _, receipt = campaign.fetch(package_url)
                blob = campaign.root / 'blobs' / (receipt['sha256'] + '.gz')
                version = acquire(accession, cik, form, output / 'versions', package=str(blob),
                                  sha256=receipt['sha256'], minimum_free_bytes=reserve)
                manifest, _ = read_package(version)  # verify the saved copy and decode it once
                index_url = package_url.rsplit('/', 1)[0] + '/' + accession + '-index.html'
                index, _ = campaign.fetch(index_url)
                gaps = compare_inventory(manifest, parse_index(index, index_url))
                row.update(status='OK' if not gaps['missing'] and not gaps['metadata_mismatch'] else 'INVENTORY_GAP',
                           members=len(manifest['members']), package_bytes=manifest['package']['bytes'],
                           missing=gaps['missing'], metadata_mismatch=gaps['metadata_mismatch'],
                           package_only=len(gaps['package_only']))
                streak = 0
            except StorageError as exc:  # low disk or storage failure: stop; this filing is retried on resume
                stop = 'storage: ' + str(exc)
            except (AcquisitionError, DownloadError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
                row.update(status='FAILED', reason=f'{type(exc).__name__}: {exc}'[:300])
                streak += 1
            if campaign.stopped or (campaign.root / 'STOP.json').exists():
                stop = stop or 'HTTP 403 or campaign stop; see campaign/STOP.json'
            if 'status' in row and not (stop and row['status'] == 'FAILED' and campaign.stopped):
                row['seconds'] = round(time.monotonic() - began, 2)
                log.write(json.dumps(row) + '\n')
                log.flush()
                done.add(accession)
                counts[row['status']] += 1
            if streak >= max_consecutive_failures:
                stop = f'{streak} consecutive failures'
            _progress(output, dict(
                updated_at=datetime.now(timezone.utc).isoformat(), position=position, of=len(filings),
                done=len(done), counts=dict(counts), last=accession, stop=stop,
                free_gb=round(shutil.disk_usage(output).free / 1e9, 1), requests_this_run=campaign.sent_attempts,
                minutes_this_run=round((time.monotonic() - started) / 60, 1)))
            if stop:
                break
    summary = dict(stop=stop, finished=stop is None, done=len(done), of=len(filings), counts=dict(counts))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--every', type=int, default=1, help='take every Nth filing (rehearsal sample)')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--min-free-gb', type=float, default=162)
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.output, live=args.live, every=args.every,
                         limit=args.limit, min_free_gb=args.min_free_gb), indent=2))
