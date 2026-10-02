"""Scale regressions: bounded writes, restart, disk exhaustion and send timestamps."""
from datetime import datetime, timedelta, timezone
import errno
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from driver.prepare.campaign import Campaign


class ScaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock, self.calls = [0.0], []

    def sleep(self, delay):
        self.clock[0] += delay

    def sender(self, url, *args):
        self.calls.append((url, self.clock[0]))
        return 200, {}, url.encode()

    def campaign(self, **options):
        return Campaign(self.root, live=True, sender=self.sender, now=lambda: self.clock[0],
                        sleep=self.sleep, **options)

    def test_receipts_append_without_reserializing_history_and_replay_offline(self):
        with self.campaign() as run:
            for n in range(60):
                run.fetch(f'https://www.sec.gov/Archives/{n}')
            first = dict(run.records)
            original = json.dumps
            def small(value, *args, **kwargs):
                self.assertLess(len(original(value)), 4096, 'whole receipt history was serialized')
                return original(value, *args, **kwargs)
            with patch('json.dumps', side_effect=small):
                run.fetch('https://www.sec.gov/Archives/60')
            self.assertEqual({u: run.records[u] for u in first}, first)
        before = (self.root / 'responses.sqlite3').read_bytes()
        with self.campaign() as run:
            for n in range(61):
                self.assertTrue(run.fetch(f'https://www.sec.gov/Archives/{n}')[1]['cache_hit'])
        self.assertEqual(len(self.calls), 61)
        self.assertEqual((self.root / 'responses.sqlite3').read_bytes(), before)

    def test_actual_receipt_times_follow_pacing_including_retries_and_restart(self):
        clock = self.clock
        origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
        class WallClock:
            @staticmethod
            def now(tz=None):
                return origin + timedelta(seconds=clock[0])
        records = []
        def sender(url, *args):
            self.calls.append((url, self.clock[0]))
            return (429, {}, b'') if len(self.calls) == 1 else (200, {}, b'ok')
        with patch('driver.prepare.transport.datetime', WallClock):
            for n in range(2):
                with self.campaign(requests_per_second=5) as run:
                    run.sender = sender
                    records.extend(run.fetch(f'https://www.sec.gov/Archives/{n}')[1]['attempts'])
        starts = [(datetime.fromisoformat(r['started_at']) - origin).total_seconds() for r in records]
        self.assertEqual(starts, [round(time, 6) for _, time in self.calls])
        self.assertTrue(all(b - a >= 0.2 - 1e-12 for a, b in zip(starts, starts[1:])))
        self.assertEqual(len(starts), 3)

    def test_low_space_stops_before_a_request_but_cached_reads_still_work(self):
        url = 'https://www.sec.gov/Archives/saved'
        with self.campaign() as run:
            run.fetch(url)
        self.calls.clear()
        with self.campaign(minimum_free_bytes=10**30) as run:
            self.assertTrue(run.fetch(url)[1]['cache_hit'])
            with self.assertRaisesRegex(ValueError, '(?i)space'):
                run.fetch('https://www.sec.gov/Archives/new')
            self.assertTrue(run.stopped)
            with self.assertRaises(ValueError):
                run.fetch('https://www.sec.gov/Archives/another')
        self.assertEqual(self.calls, [])

    def test_disk_full_and_quota_errors_stop_all_later_downloads(self):
        for number in (errno.ENOSPC, errno.EDQUOT):
            with self.subTest(errno=number), self.campaign() as run:
                with patch('driver.prepare.campaign.store_blob', side_effect=OSError(number, 'disk unavailable')):
                    with self.assertRaises(ValueError):
                        run.fetch('https://www.sec.gov/Archives/new')
                self.assertTrue(run.stopped)
                count = len(self.calls)
                with self.assertRaises(ValueError):
                    run.fetch('https://www.sec.gov/Archives/another')
                self.assertEqual(len(self.calls), count)
                self.assertNotIn('https://www.sec.gov/Archives/new', run.records)

    def test_receipt_write_failure_does_not_select_unsaved_response(self):
        with self.campaign() as run:
            # Real SQLite write failure, without manufacturing a disk-error message.
            run.db.execute('PRAGMA query_only=ON')
            with self.assertRaises(ValueError):
                run.fetch('https://www.sec.gov/Archives/new')
            self.assertTrue(run.stopped)
            self.assertEqual(run.records, {})
        with self.campaign() as run:
            self.assertEqual(run.records, {})

    def test_old_receipts_import_once_without_downloads_or_evidence_changes(self):
        url, data = 'https://www.sec.gov/Archives/old', b'old exact bytes'
        sha = hashlib.sha256(data).hexdigest()
        (self.root / 'blobs').mkdir()
        (self.root / 'blobs' / (sha + '.gz')).write_bytes(gzip.compress(data))
        record = dict(url=url, bytes=len(data), sha256=sha, attempts=[])
        legacy = self.root / 'responses.json'
        legacy.write_text(json.dumps({url: record}))
        before = legacy.read_bytes()
        for _ in range(2):
            with self.campaign() as run:
                actual, receipt = run.fetch(url)
                self.assertEqual(actual, data)
                self.assertTrue(receipt.pop('cache_hit'))
                self.assertEqual(receipt, record)
                self.assertEqual(run.records, {url: record})
        self.assertEqual(self.calls, [])
        self.assertEqual(legacy.read_bytes(), before)

    def test_five_per_second_is_one_shared_gate_for_all_urls(self):
        with self.campaign() as run:
            for n in range(30):
                run.fetch(f'https://www.sec.gov/Archives/{n}')
        starts = [start for _, start in self.calls]
        self.assertTrue(all(b - a >= 0.2 - 1e-12 for a, b in zip(starts, starts[1:])))
        self.assertAlmostEqual(starts[-1], 6)
        for rate in (0, -1, 11, float('nan'), float('inf')):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                self.campaign(requests_per_second=rate)
