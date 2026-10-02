import copy
import json
import tempfile
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from driver.prepare.campaign import Campaign
from driver.prepare.transport import DownloadError


class CampaignTests(unittest.TestCase):
    def test_shared_rate_limit_includes_retries_and_cache_replay_is_offline(self):
        clock = [0.0]
        calls = []
        responses = iter([(429, {}, b''), (200, {}, b'one'), (200, {}, b'two')])
        def sender(url, *args):
            calls.append((url, clock[0]))
            return next(responses)
        def sleep(delay):
            clock[0] += delay
        with tempfile.TemporaryDirectory() as directory:
            with Campaign(directory, live=True, sender=sender, now=lambda: clock[0], sleep=sleep,
                          requests_per_second=1) as run:
                self.assertEqual(run.fetch('https://www.sec.gov/Archives/one')[0], b'one')
                self.assertEqual(run.fetch('https://www.sec.gov/Archives/two')[0], b'two')
                self.assertTrue(run.fetch('https://www.sec.gov/Archives/one')[1]['cache_hit'])
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(b[1] - a[1] >= 1 for a, b in zip(calls, calls[1:])))
            with Campaign(directory, sender=lambda *a: self.fail('offline network call')) as run:
                self.assertEqual(run.fetch('https://www.sec.gov/Archives/two')[0], b'two')
                with self.assertRaises(ValueError):
                    run.fetch('https://www.sec.gov/Archives/missing')

    def test_403_stops_other_urls_and_survives_restart(self):
        calls = []
        def blocked(url, *args):
            calls.append(url)
            return 403, {}, b''
        with tempfile.TemporaryDirectory() as directory:
            with Campaign(directory, live=True, sender=blocked) as run:
                with self.assertRaises(DownloadError):
                    run.fetch('https://www.sec.gov/Archives/one')
                with self.assertRaises(ValueError):
                    run.fetch('https://www.sec.gov/Archives/two')
            with Campaign(directory, live=True, sender=blocked) as run:
                with self.assertRaises(ValueError):
                    run.fetch('https://www.sec.gov/Archives/three')
            self.assertEqual(len(calls), 1)
            self.assertTrue((Path(directory) / 'STOP.json').is_file())

    def test_failed_attempt_is_kept_but_never_selected_so_live_mode_retries(self):
        replies = iter([(503, {}, b'')] * 3 + [(200, {}, b'ok')])
        clock, url = [0.0], 'https://www.sec.gov/Archives/one'
        def sleep(delay):
            clock[0] += delay
        with tempfile.TemporaryDirectory() as directory:
            settings = dict(sender=lambda *args: next(replies), now=lambda: clock[0], sleep=sleep)
            with Campaign(directory, live=True, **settings) as run:
                with self.assertRaises(DownloadError):
                    run.fetch(url)
            with Campaign(directory, **settings) as run:
                with self.assertRaisesRegex(ValueError, 'Uncached'):  # offline never retries
                    run.fetch(url)
            with Campaign(directory, live=True, **settings) as run:
                self.assertEqual(run.fetch(url)[0], b'ok')
                failed = [json.loads(receipt) for _, receipt in run.db.execute('SELECT * FROM failures')]
            self.assertEqual([a['status'] for a in failed[0]['attempts']], [503, 503, 503])

    def test_corrupt_cache_wrong_url_and_second_writer_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            with Campaign(directory, live=True, sender=lambda *a: (200, {}, b'original')) as run:
                _, receipt = run.fetch('https://www.sec.gov/Archives/one')
                blob = Path(directory) / 'blobs' / (receipt['sha256'] + '.gz')
                blob.write_bytes(b'broken')
                with self.assertRaises(ValueError):
                    run.fetch('https://www.sec.gov/Archives/one')
                for url in ('https://example.com/a', 'http://www.sec.gov/Archives/a', 'https://www.sec.gov/Archives/a?q=1'):
                    with self.assertRaises(ValueError):
                        run.fetch(url)
                with self.assertRaises(OSError):
                    with Campaign(directory):
                        pass

    def test_reopening_campaign_keeps_configured_request_spacing(self):
        clock, starts = [0.0], []
        def sender(url, *args):
            starts.append(clock[0])
            return 200, {}, url.encode()
        def sleep(delay):
            clock[0] += delay
        with tempfile.TemporaryDirectory() as directory:
            for name in ('one', 'two'):
                with Campaign(directory, live=True, sender=sender,
                              now=lambda: clock[0], sleep=sleep) as run:
                    run.fetch('https://www.sec.gov/Archives/' + name)
        self.assertEqual(len(starts), 2)
        self.assertGreaterEqual(starts[1] - starts[0], 0.2)

    def test_corrupt_response_selection_never_returns_other_bytes_or_refetches(self):
        first, second = ('https://www.sec.gov/Archives/' + name for name in ('one', 'two'))
        clock = [0.0]
        def sleep(delay):
            clock[0] += delay
        with tempfile.TemporaryDirectory() as directory:
            with Campaign(directory, live=True, sender=lambda url, *args: (200, {}, url.encode()),
                          now=lambda: clock[0], sleep=sleep) as run:
                run.fetch(first)
                run.fetch(second)
                original = run.records
            path = Path(directory) / 'responses.sqlite3'
            swapped = copy.deepcopy(original)
            swapped[first] = swapped[second]
            wrong_size = copy.deepcopy(original)
            wrong_size[first]['bytes'] = 0
            cases = [swapped, wrong_size]
            for value in ({}, None, False, []):
                changed = copy.deepcopy(original)
                changed[first] = value
                cases.append(changed)
            for changed in cases:
                with sqlite3.connect(path) as db:
                    db.executemany('UPDATE responses SET receipt=? WHERE url=?',
                                   [(json.dumps(record), url) for url, record in changed.items()])
                before = path.read_bytes()
                with self.subTest(record=changed[first]), self.assertRaises(ValueError):
                    with Campaign(directory, live=True,
                                  sender=lambda *args: self.fail('corrupt record triggered a request')) as run:
                        run.fetch(first)
                self.assertEqual(path.read_bytes(), before, 'corrupt metadata was silently repaired')

    def test_403_remains_terminal_when_stop_marker_write_fails(self):
        calls, clock = [], [0.0]
        def sender(url, *args):
            calls.append(url)
            return 403, {}, b''
        def sleep(delay):
            clock[0] += delay
        with tempfile.TemporaryDirectory() as directory:
            with Campaign(directory, live=True, sender=sender,
                          now=lambda: clock[0], sleep=sleep) as run:
                original_save = run._save
                def save(name, value):
                    if name == 'STOP.json':
                        raise OSError('simulated full disk')
                    return original_save(name, value)
                with patch.object(run, '_save', side_effect=save):
                    with self.assertRaises((ValueError, OSError)):
                        run.fetch('https://www.sec.gov/Archives/one')
                    self.assertEqual(len(calls), 1, 'a received 403 was retried after marker failure')
                    with self.assertRaises(ValueError):
                        run.fetch('https://www.sec.gov/Archives/two')
                self.assertEqual(len(calls), 1)

    def test_non_object_response_cache_fails_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'responses.json'
            for value in ([], None, False, 0, 'not a response map'):
                path.write_text(json.dumps(value))
                before = path.read_bytes()
                with self.subTest(value=value), self.assertRaises(ValueError):
                    with Campaign(directory, live=True,
                                  sender=lambda *args: self.fail('invalid cache triggered a request'),
                                  sleep=lambda delay: None) as run:
                        run.fetch('https://www.sec.gov/Archives/one')
                self.assertEqual(path.read_bytes(), before)
