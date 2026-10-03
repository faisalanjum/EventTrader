"""Acquire every listed SEC filing: package + SEC file list, resumable, with safe stops.

No conversion, AI or database writes. results.sqlite3 keeps one row per attempt; a
filing's latest row is its status. Only OK is final: re-running the same command
skips OK filings whose saved version still fully verifies and retries every other filing
(FAILED, INVENTORY_GAP, PENDING); saved responses make no requests. complete=true
means every listed filing is OK. Stops: any HTTP 403, free disk below the reserve,
or 20 filings in a row not OK; the filing in progress at a 403/disk stop stays PENDING.
"""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time

from driver.prepare.get.acquire import AcquisitionError, StorageError, acquire, read_package, _identity, _make_dirs, _url
from driver.prepare.get.campaign import Campaign
from driver.prepare.get.inventory import compare_inventory, parse_index

SOURCES = sorted(Path(__file__).resolve().parent.glob('*.py'))  # the get package, this runner included


def _write(path, value):
    pending = path.with_name(path.name + '.pending')
    pending.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(pending, path)


def _saved(output, row):
    """A previous OK stands only if its saved version still fully verifies as this filing."""
    try:
        identity = read_package(output / 'versions' / row['acc'] / row['sha256'])[0]['identity']
        return ((identity['accession'], identity['form']) == (row['acc'], row['form'])
                and _identity(row['acc'], row['cik'], row['form'])['cik'] in identity['ciks'])
    except StorageError:
        raise
    except AcquisitionError:
        return False


def _filing(campaign, output, reserve, accession, cik, form):
    """Package → one saved copy → verified readback → SEC file list → comparison."""
    package_url = _url(_identity(accession, cik, form))
    _, receipt = campaign.fetch(package_url)
    blob = campaign.root / 'blobs' / (receipt['sha256'] + '.gz')
    version = acquire(accession, cik, form, output / 'versions', package=str(blob),
                      sha256=receipt['sha256'], minimum_free_bytes=reserve)
    manifest, _ = read_package(version)
    index_url = package_url.rsplit('/', 1)[0] + '/' + accession + '-index.html'
    index, _ = campaign.fetch(index_url)
    gaps = compare_inventory(manifest, parse_index(index, index_url))
    return dict(status='INVENTORY_GAP' if gaps['missing'] or gaps['metadata_mismatch'] else 'OK',
                sha256=receipt['sha256'], members=len(manifest['members']),
                package_bytes=manifest['package']['bytes'], missing=gaps['missing'],
                metadata_mismatch=gaps['metadata_mismatch'], package_only=len(gaps['package_only']))


# Kubernetes nodes keep container images on this disk and evict pods below 15% free;
# stopping at 16% stays clear of that line on any node and disk size.
def run(inputs, output, *, live=False, every=1, limit=None, min_free_percent=16,
        max_consecutive_failures=20, requests_per_second=5, campaign_class=Campaign):
    frozen = json.loads(Path(inputs).read_text())
    listed = frozen['filings']
    if (len(listed) != frozen.get('count') or frozen.get('sha256_of_filings') !=
            hashlib.sha256(json.dumps(listed, separators=(',', ':')).encode()).hexdigest()):
        raise ValueError('Filing list differs from its declared count or SHA-256')
    keys = [(filing['acc'], filing['cik'], filing['form']) for filing in listed[::every][:limit]]
    output = Path(output).absolute()
    _make_dirs(output)
    reserve = int(shutil.disk_usage(output).total * min_free_percent / 100)
    launch = dict(started_at=datetime.now(timezone.utc).isoformat(), argv=sys.argv,
                  inputs_sha256=frozen['sha256_of_filings'],
                  code={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCES})
    with campaign_class(output / 'campaign', live=live, requests_per_second=requests_per_second,
                        minimum_free_bytes=reserve) as campaign, \
            closing(sqlite3.connect(output / 'results.sqlite3')) as db:
        db.execute('PRAGMA synchronous=FULL')
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS launches (row TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS results (row TEXT NOT NULL)')
            db.execute('INSERT INTO launches VALUES (?)', (json.dumps(launch),))
        state, latest = dict.fromkeys(keys, 'PENDING'), {}
        for (text,) in db.execute('SELECT row FROM results ORDER BY rowid'):
            row = json.loads(text)
            latest[row['acc'], row['cik'], row['form']] = row  # the latest row wins
        streak, stop, started = 0, None, time.monotonic()

        def report(position, **extra):
            _write(output / 'progress.json', dict(
                updated_at=datetime.now(timezone.utc).isoformat(), position=position, of=len(state),
                counts=Counter(state.values()), last=keys[position - 1][0] if position else None, stop=stop,
                free_gb=round(shutil.disk_usage(output).free / 1e9, 1), requests_this_run=campaign.sent_attempts,
                minutes_this_run=round((time.monotonic() - started) / 60, 1), **extra))

        earlier = [(key, row) for key, row in latest.items() if key in state]
        reported = started
        for checked, (key, row) in enumerate(earlier):
            if checked == 0 or time.monotonic() - reported >= 60:  # a long check of saved results never looks stalled
                report(0, verified=f'{checked} of {len(earlier)} earlier results')
                reported = time.monotonic()
            # an OK is redone unless its saved version still verifies; damage is left as found
            state[key] = row['status'] if row['status'] != 'OK' or _saved(output, row) else 'PENDING'
        report(0)
        for position, key in enumerate(keys, 1):
            if state[key] == 'OK':
                streak = 0  # a saved OK filing breaks a run of failures, so scattered retries continue
                continue
            accession, cik, form = key
            began = time.monotonic()
            try:
                row = _filing(campaign, output, reserve, accession, cik, form)
            except Exception as exc:  # record any per-filing error and continue; run-wide ones stop
                reason = f'{type(exc).__name__}: {exc}'[:300]
                if isinstance(exc, StorageError) or campaign.stopped or (campaign.root / 'STOP.json').exists():
                    stop = reason  # low disk, storage failure or HTTP 403: the filing stays PENDING
                row = dict(status='FAILED', reason=reason)
            if not stop:
                row = dict(acc=accession, form=form, cik=cik, **row, seconds=round(time.monotonic() - began, 2))
                with db:
                    db.execute('INSERT INTO results VALUES (?)', (json.dumps(row),))
                state[key] = row['status']
                streak = 0 if row['status'] == 'OK' else streak + 1
                if streak >= max_consecutive_failures:
                    stop = f'{streak} filings in a row not OK; last: {row.get("reason", row["status"])}'
            report(position)
            if stop:
                break
        counts = Counter(state.values())
        summary = dict(stop=stop, complete=counts['OK'] == len(state), of=len(state), counts=counts,
                       unresolved=sorted(key[0] for key, status in state.items()
                                         if status in ('FAILED', 'INVENTORY_GAP')), launch=launch)
        _write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--every', type=int, default=1, help='take every Nth filing (rehearsal sample)')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--min-free-percent', type=float, default=16)
    print(json.dumps(run(**vars(parser.parse_args())), indent=2))
