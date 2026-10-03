"""Offline checks of the overnight runner: success, resume, retries and each safe stop."""
from contextlib import closing
import errno
import gzip
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from driver.prepare.get.acquire import StorageError, acquire, read_package
from driver.prepare.get.campaign import Campaign
from driver.prepare.get import full_run

FIXTURES = Path(__file__).with_name('fixtures')
AMG = dict(acc='0001004434-23-000015', form='8-K', cik='1004434')
BASE = 'https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/'
MISSING = [dict(acc=f'0000000001-23-00000{i}', form='8-K', cik='1') for i in range(1, 4)]

# Offline restart of the real runner whose result insert pauses until it is killed.
CHILD = r'''
import sqlite3, sys, time
from driver.prepare.get import full_run
connect = sqlite3.connect
def hooked(*args, **kwargs):
    db = connect(*args, **kwargs)
    db.create_function('pause', 0, lambda: print('saving', flush=True) or time.sleep(30))
    return db
sqlite3.connect = hooked
full_run.run(sys.argv[1], sys.argv[2], min_free_percent=0)
'''


def frozen(filings):
    listed = json.dumps(filings, separators=(',', ':')).encode()
    return dict(count=len(filings), sha256_of_filings=hashlib.sha256(listed).hexdigest(), filings=filings)


class FullRunTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.out = self.root / 'out'
        self.responses = {BASE + AMG['acc'] + '.txt': (FIXTURES / (AMG['acc'] + '.txt.gz')).read_bytes(),
                          BASE + AMG['acc'] + '-index.html': (FIXTURES / 'amg_index.html.gz').read_bytes()}
        self.calls, self.status, self.clock = [], None, [0.0]

    def tearDown(self):
        self.temporary.cleanup()

    def campaign(self, directory, **settings):
        def sender(url, *args):
            self.calls.append(url)
            if self.status:
                return self.status, {}, b''
            body = self.responses.get(url)
            return (200, {}, gzip.decompress(body)) if body else (404, {}, b'')
        def sleep(delay):
            self.clock[0] += delay
        return Campaign(directory, sender=sender, now=lambda: self.clock[0], sleep=sleep, **settings)

    def run_with(self, filings, **settings):
        inputs = self.root / 'inputs.json'
        inputs.write_text(json.dumps(frozen(filings)))
        return full_run.run(inputs, self.out, live=True, min_free_percent=settings.pop('min_free_percent', 0),
                            campaign_class=self.campaign, **settings)

    def rows(self, table='results'):
        with closing(sqlite3.connect(self.out / 'results.sqlite3')) as db:
            return [json.loads(text) for (text,) in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]

    def test_success_then_resume_makes_no_requests(self):
        summary = self.run_with([AMG])
        self.assertEqual((summary['complete'], summary['counts']), (True, {'OK': 1}))
        self.assertEqual((self.rows()[0]['members'], len(self.calls)), (17, 2))
        self.assertEqual(json.loads((self.out / 'progress.json').read_text())['counts'], {'OK': 1})
        self.run_with([AMG])
        self.assertEqual((len(self.rows()), len(self.calls)), (1, 2))
        self.assertEqual(len(self.rows(table='launches')), 2)

    def test_failed_filing_is_retried_after_the_source_recovers(self):
        self.status = 503
        first = self.run_with([AMG])
        self.assertEqual((first['complete'], first['counts'], first['unresolved']),
                         (False, {'FAILED': 1}, [AMG['acc']]))
        self.status = None
        second = self.run_with([AMG])
        self.assertEqual((second['complete'], second['counts']), (True, {'OK': 1}))
        self.assertEqual([row['status'] for row in self.rows()], ['FAILED', 'OK'])
        with closing(sqlite3.connect(self.out / 'campaign/responses.sqlite3')) as db:  # failure evidence kept
            kept = [json.loads(receipt) for _, receipt in db.execute('SELECT * FROM failures')]
        self.assertEqual([attempt['status'] for attempt in kept[0]['attempts']], [503, 503, 503])

    def test_inventory_gap_is_a_failure_and_counts_toward_the_stop(self):
        url = BASE + AMG['acc'] + '-index.html'
        extra = (b'<tr><td>99</td><td>Required</td><td><a href="missing.htm">missing.htm</a></td>'
                 b'<td>EX-99.9</td><td>20</td></tr>')
        self.responses[url] = gzip.compress(gzip.decompress(self.responses[url]).replace(
            b'</table>', extra + b'</table>', 1))
        summary = self.run_with([AMG] + MISSING, max_consecutive_failures=1)
        self.assertEqual((summary['complete'], summary['counts']), (False, {'INVENTORY_GAP': 1, 'PENDING': 3}))
        self.assertIn('1 filings in a row not OK', summary['stop'])
        self.assertEqual(self.rows()[0]['missing'], ['missing.htm'])
        calls = len(self.calls)
        self.assertEqual(self.run_with([AMG])['counts'], {'INVENTORY_GAP': 1})  # rechecked, saved bytes only
        self.assertEqual(len(self.calls), calls)

    def test_consecutive_failures_stop_the_run(self):
        summary = self.run_with(MISSING, max_consecutive_failures=2)
        self.assertIn('2 filings in a row not OK', summary['stop'])
        self.assertEqual(summary['counts'], {'FAILED': 2, 'PENDING': 1})
        self.assertEqual([row['reason'] for row in self.rows()], ['DownloadError: HTTP 404'] * 2)

    def test_scattered_failures_do_not_stop_a_retry_but_consecutive_ones_do(self):
        filings = [MISSING[0], AMG, MISSING[1], MISSING[2]]
        self.run_with(filings)
        self.calls.clear()
        retry = self.run_with(filings, max_consecutive_failures=2)  # M0 fails, AMG is skipped, M1, M2 fail
        self.assertEqual(len(self.calls), 3)  # every failed filing was retried, including the last
        self.assertIn('2 filings in a row not OK', retry['stop'])  # M1 and M2 really are consecutive

    def test_low_disk_stops_before_any_request_and_leaves_the_filing_pending(self):
        summary = self.run_with([AMG], min_free_percent=1000)
        self.assertIn('Low disk space', summary['stop'])
        self.assertEqual((summary['counts'], self.rows(), self.calls), ({'PENDING': 1}, [], []))

    def test_http_403_stops_without_marking_the_filing_done(self):
        self.status = 403
        summary = self.run_with([AMG] + MISSING)
        self.assertIn('403', summary['stop'])
        self.assertEqual((summary['counts'], self.rows(), len(self.calls)), ({'PENDING': 4}, [], 1))
        self.assertTrue((self.out / 'campaign' / 'STOP.json').exists())

    def test_resume_redoes_an_ok_whose_saved_version_no_longer_verifies(self):
        # Codex audit 2026-10-03: any damage, or a version of another filing, is reported and left exactly as found.
        for damage in ('package', 'manifest', 'receipt', 'extra file', 'symlink', 'other filing'):
            with self.subTest(damage=damage):
                self.tearDown()
                self.setUp()
                self.run_with([AMG])
                version, filings = next((self.out / 'versions' / AMG['acc']).iterdir()), [AMG]
                if damage == 'package':
                    (version / 'submission.txt.gz').write_bytes(b'corrupt')
                elif damage == 'manifest':
                    manifest = json.loads((version / 'manifest.json').read_text())
                    manifest['members'][0]['sha256'] = '0' * 64
                    (version / 'manifest.json').write_text(json.dumps(manifest))
                elif damage == 'receipt':
                    (version / 'receipt.json').write_bytes(b'not json')
                elif damage == 'extra file':
                    (version / 'unexpected').write_bytes(b'not declared')
                elif damage == 'symlink':
                    outside = self.root / 'outside.json'
                    outside.write_bytes((version / 'manifest.json').read_bytes())
                    (version / 'manifest.json').unlink()
                    (version / 'manifest.json').symlink_to(outside)
                else:  # an OK row naming this valid version for the same accession under another form
                    filings = [dict(AMG, form='10-K')]
                    with closing(sqlite3.connect(self.out / 'results.sqlite3')) as db, db:
                        db.execute('INSERT INTO results VALUES (?)', (json.dumps(dict(self.rows()[-1], form='10-K')),))
                found = {p.name: os.readlink(p) if p.is_symlink() else p.read_bytes() for p in version.iterdir()}
                summary = self.run_with(filings)
                self.assertEqual((summary['complete'], summary['stop'], summary['counts'], len(self.calls)),
                                 (False, None, {'FAILED': 1}, 2))
                self.assertEqual({p.name: os.readlink(p) if p.is_symlink() else p.read_bytes() for p in version.iterdir()},
                                 found)

    def test_resume_verifies_each_filings_latest_result_once(self):
        self.run_with([AMG])
        shutil.rmtree(next((self.out / 'versions' / AMG['acc']).iterdir()))
        self.run_with([AMG])  # redone from the cached download: a second OK row for the same filing
        with patch('driver.prepare.get.full_run.read_package', wraps=full_run.read_package) as verify:
            summary = self.run_with([AMG])
        self.assertEqual(([r['status'] for r in self.rows()], summary['counts'], verify.call_count, len(self.calls)),
                         (['OK', 'OK'], {'OK': 1}, 1, 2))

    def test_every_new_name_is_flushed_before_success_is_recorded(self):
        # Codex audit 2026-10-03: file fsyncs alone left new names (blobs, versions, STOP.json) unflushed.
        synced, real = [], os.fsync

        def fsync(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                synced.append(Path(os.readlink(f'/proc/self/fd/{descriptor}')))
            return real(descriptor)

        with patch('os.fsync', side_effect=fsync):
            self.run_with([AMG])
            version = next((self.out / 'versions' / AMG['acc']).iterdir())
            for directory in (self.root, self.out, self.out / 'campaign', self.out / 'campaign' / 'blobs',
                              self.out / 'versions', version.parent):
                self.assertIn(directory, synced)
            self.assertTrue(any(p.parent == version.parent and p.name.startswith('.pending-') for p in synced))
            synced.clear()
            self.status = 403
            self.run_with([AMG, MISSING[0]])
            self.assertIn(self.out / 'campaign', synced)  # STOP.json's name

    def test_progress_is_written_while_earlier_results_are_verified(self):
        # Codex recheck 2026-10-03: verifying ~42k saved results takes hours; the old progress file looked stalled.
        self.run_with([AMG])
        with closing(sqlite3.connect(self.out / 'results.sqlite3')) as db, db:  # three more earlier OK results
            for filing in MISSING:
                db.execute('INSERT INTO results VALUES (?)', (json.dumps(dict(filing, status='OK', sha256='0' * 64)),))
        (self.out / 'progress.json').write_text('{"previous run": true}')
        clock, seen, real = [0.0], [], full_run._saved

        def slow(output, row):  # each check takes 100 s on a fake clock
            seen.append(json.loads((self.out / 'progress.json').read_text()).get('verified'))
            clock[0] += 100
            return real(output, row)

        with patch('driver.prepare.get.full_run._saved', side_effect=slow), \
                patch('driver.prepare.get.full_run.time', SimpleNamespace(monotonic=lambda: clock[0])):
            summary = self.run_with([AMG] + MISSING)
        self.assertEqual(seen, [f'{n} of 4 earlier results' for n in range(4)])
        self.assertEqual(summary['counts'], {'OK': 1, 'FAILED': 3})  # the three unverifiable OKs were redone

    def test_a_disk_read_error_on_a_saved_version_stops_everything(self):
        # Codex review 2026-10-03: any read error except "file missing" is the disk failing, never a bad filing.
        real = Path.read_bytes
        for name in ('submission.txt.gz', 'manifest.json', 'receipt.json'):
            for code in (errno.EIO, errno.EROFS, errno.EACCES):
                with self.subTest(file=name, errno=code):
                    self.tearDown()
                    self.setUp()
                    self.run_with([AMG])
                    version = next((self.out / 'versions' / AMG['acc']).iterdir())
                    calls, rows = len(self.calls), len(self.rows())

                    def failing(path):
                        if path == version / name:
                            raise OSError(code, 'injected cache read failure')
                        return real(path)

                    with patch.object(Path, 'read_bytes', failing):
                        with self.assertRaises(StorageError):
                            read_package(version)
                        with self.assertRaises(StorageError):
                            acquire(AMG['acc'], AMG['cik'], AMG['form'], self.out / 'versions', minimum_free_bytes=0,
                                    package=str(self.out / 'campaign' / 'blobs' / (version.name + '.gz')), sha256=version.name)
                        with self.assertRaises(StorageError):  # at startup: ends before any download
                            self.run_with([AMG, MISSING[0]])
                    self.assertEqual((len(self.calls), len(self.rows())), (calls, rows))

    def test_a_failed_flush_stops_the_whole_run_before_another_request(self):
        # Codex recheck 2026-10-03: a flush failure once became an ordinary per-filing error and the batch went on.
        real = os.fsync
        for site, directory, status in (('campaign/blobs', True, None), ('versions', True, None), ('campaign', True, 403),
                                        ('versions', False, None)):  # the last: a version file's own flush
            with self.subTest(site=site, directory=directory):
                self.tearDown()
                self.setUp()
                self.status = status
                target = self.out / site

                def fsync(descriptor):
                    path = Path(os.readlink(f'/proc/self/fd/{descriptor}'))
                    if stat.S_ISDIR(os.fstat(descriptor).st_mode) == directory and target in (path, *path.parents) and \
                            (site != 'campaign' or path == target):
                        raise OSError(errno.EIO, 'simulated flush failure')
                    return real(descriptor)

                with patch('os.fsync', side_effect=fsync):
                    summary = self.run_with([AMG, MISSING[0]])
                self.assertIn('flush failed' if directory else 'simulated flush failure', summary['stop'])
                self.assertEqual((summary['counts'], self.rows(), len(self.calls)), ({'PENDING': 2}, [], 1))

    def test_input_list_and_full_identity_are_checked(self):
        inputs = self.root / 'inputs.json'
        inputs.write_text(json.dumps(dict(frozen([AMG]), count=2)))
        with self.assertRaisesRegex(ValueError, 'declared'):
            full_run.run(inputs, self.out, campaign_class=self.campaign)
        self.run_with([AMG])
        changed = self.run_with([dict(AMG, form='10-K')])  # same accession, other form: never reused
        self.assertEqual(changed['counts'], {'FAILED': 1})
        self.assertIn('identity differs', self.rows()[-1]['reason'])

    def test_ok_filing_whose_saved_package_is_gone_is_rechecked(self):
        self.run_with([AMG])
        next((self.out / 'versions').glob('*/*/submission.txt.gz')).unlink()
        summary = self.run_with([AMG])
        self.assertEqual((summary['counts'], len(self.calls)), ({'FAILED': 1}, 2))  # no silent repair
        self.assertIn('Invalid cache', self.rows()[-1]['reason'])

    def test_kill_while_recording_a_result_keeps_earlier_results(self):
        self.run_with([AMG])
        with closing(sqlite3.connect(self.out / 'results.sqlite3')) as db:
            db.execute('CREATE TRIGGER interrupt AFTER INSERT ON results BEGIN SELECT pause(); END')
        inputs = self.root / 'inputs.json'
        inputs.write_text(json.dumps(frozen([AMG, MISSING[0]])))
        process = subprocess.Popen([sys.executable, '-B', '-S', '-c', CHILD, str(inputs), str(self.out)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 10)[0], 'runner did not reach the insert')
            self.assertEqual(process.stdout.readline().strip(), 'saving')
            process.kill()
            self.assertEqual(process.wait(timeout=5), -signal.SIGKILL)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
        with closing(sqlite3.connect(self.out / 'results.sqlite3')) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            db.execute('DROP TRIGGER interrupt')
        self.assertEqual([row['status'] for row in self.rows()], ['OK'])  # the killed insert left nothing
        summary = full_run.run(inputs, self.out, min_free_percent=0, campaign_class=self.campaign)
        self.assertEqual(summary['counts'], {'OK': 1, 'FAILED': 1})  # offline: the new filing is uncached
        self.assertEqual(len(self.calls), 2)


if __name__ == '__main__':
    unittest.main()
