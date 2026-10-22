"""The context download seam retains ordinary absence and propagates broken custody/stops."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driver.prepare.get.acquire import AcquisitionError, StorageError
from driver.prepare.get.archive import store_blob
from driver.prepare.get.campaign import Campaign
from driver.prepare.get.context_acquire import _Fetcher, _get, _startup_dependencies


class ContextAcquisitionFailures(unittest.TestCase):
    def test_real_campaign_cache_and_stop_outcomes(self):
        url, data = 'https://www.sec.gov/Archives/evidence/control.html', b'<p>Original positive control</p>'
        expected = {'healthy': 'bytes', 'offline_missing': 'unavailable', 'ordinary_404': 'unavailable',
                    'wrong_receipt_url': 'raise', 'wrong_receipt_size': 'raise', 'wrong_blob_content': 'raise',
                    'stopped_flag': 'raise', 'stopped_file': 'raise', 'http_403': 'raise'}
        for case, want in expected.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                calls = []
                def sender(*args):
                    calls.append(args[0])
                    self.assertIn(case, ('ordinary_404', 'http_403'))
                    return (404 if case == 'ordinary_404' else 403), {}, b''
                with Campaign(directory, live=case in ('ordinary_404', 'http_403'), sender=sender,
                              sleep=lambda _: None, minimum_free_bytes=0) as campaign:
                    if case in ('healthy', 'wrong_receipt_url', 'wrong_receipt_size', 'wrong_blob_content'):
                        digest = store_blob(campaign.root / 'blobs', data)
                        receipt = {'url': url, 'sha256': digest, 'bytes': len(data)}
                        if case == 'wrong_receipt_url': receipt['url'] += '/other'
                        if case == 'wrong_receipt_size': receipt['bytes'] += 1
                        if case == 'wrong_blob_content':
                            other = store_blob(campaign.root / 'blobs', b'changed')
                            (campaign.root / 'blobs' / (digest + '.gz')).write_bytes(
                                (campaign.root / 'blobs' / (other + '.gz')).read_bytes())
                        campaign._record(url, receipt)
                    if case == 'stopped_flag': campaign.stopped = True
                    if case == 'stopped_file': (campaign.root / 'STOP.json').write_text('{"reason":"test stop"}')
                    log = []
                    if want == 'raise':
                        with self.assertRaises((AcquisitionError, OSError)):
                            _get(campaign, url, None, log)
                    else:
                        result = _get(campaign, url, None, log)
                        self.assertEqual(result, data if want == 'bytes' else None)
                        self.assertEqual(len(log), 1)
                    self.assertEqual(calls, [url] if case in ('ordinary_404', 'http_403') else [])

    def test_nonabsence_failures_escape(self):
        for fault in (MemoryError('exhausted'), OSError('device error'), StorageError('disk failure'),
                      AcquisitionError('custody failure'), ImportError('dependency missing')):
            with self.subTest(error=type(fault).__name__), tempfile.TemporaryDirectory() as directory:
                with Campaign(directory, minimum_free_bytes=0) as campaign:
                    with patch.object(campaign, 'fetch', side_effect=fault):
                        with self.assertRaises(type(fault)) as caught:
                            _get(campaign, 'https://www.sec.gov/Archives/evidence/control.html', None, [])
                    self.assertIs(caught.exception, fault)

    def test_response_map_uses_native_cache_validation_and_only_requested_files(self):
        url, data = 'https://www.sec.gov/Archives/evidence/style.css', b'p { font-weight: bold }'
        for case in ('healthy', 'wrong_url', 'wrong_size', 'unrelated_corruption'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                with Campaign(directory, live=True, minimum_free_bytes=0, sleep=lambda _: None,
                              sender=lambda *args: (200, {'content-type': 'text/css'}, data)) as campaign:
                    campaign.fetch(url)
                    changed = url
                    if case == 'unrelated_corruption':
                        changed = url + '-unused.css'
                        campaign.fetch(changed)
                    if case != 'healthy':
                        receipt = campaign.records[changed]
                        if case == 'wrong_size': receipt['bytes'] += 1
                        else: receipt['url'] += '/other'
                        with campaign.db:
                            campaign.db.execute('UPDATE responses SET receipt=? WHERE url=?', (json.dumps(receipt), changed))
                    fetch = _Fetcher(campaign, 80)
                    if case in ('wrong_url', 'wrong_size'):
                        with self.assertRaises(AcquisitionError): fetch.get(url)
                        self.assertEqual(fetch.observed, {})
                    else:
                        self.assertEqual(fetch.get(url), data)
                        self.assertEqual(set(fetch.observed), {url})
                        self.assertEqual(fetch.observed[url]['body'], data)

    def test_failed_response_replay_keeps_exact_status_and_url(self):
        url = 'https://www.sec.gov/Archives/evidence/missing.css'
        with tempfile.TemporaryDirectory() as directory:
            with Campaign(directory, live=True, minimum_free_bytes=0, sleep=lambda _: None,
                          sender=lambda *args: (404, {'content-type': 'text/plain'}, b'absent')) as campaign:
                fetch = _Fetcher(campaign, 80)
                self.assertIsNone(fetch.get(url))
                self.assertEqual(fetch.observed[url]['status'], 404)
            with Campaign(directory, live=False) as campaign:
                fetch = _Fetcher(campaign, 80)
                self.assertIsNone(fetch.get(url))
                self.assertEqual(fetch.observed[url]['status'], 404)
                self.assertIsNone(fetch.observed[url]['body'])
                self.assertIsNone(fetch.get(url + '-never-requested'))
                self.assertEqual(set(fetch.observed), {url})
                row = campaign.db.execute('SELECT rowid,receipt FROM failures WHERE url=?', (url,)).fetchone()
                receipt = json.loads(row[1]); receipt['url'] += '/other'
                with campaign.db:
                    campaign.db.execute('UPDATE failures SET receipt=? WHERE rowid=?', (json.dumps(receipt), row[0]))
                with self.assertRaises(AcquisitionError): _Fetcher(campaign, 80).get(url)

    def test_startup_parent_uses_the_shared_source_identity_rule(self):
        from playwright.sync_api import sync_playwright
        parent = 'https://www.sec.gov/Archives/evidence/parent.htm'
        css = parent.rsplit('/', 1)[0] + '/style.css'
        missing = parent.rsplit('/', 1)[0] + '/missing.css'
        raw = b'<html><head><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="missing.css"></head><body><p>parent</p></body></html>'
        def sender(url, *args):
            if url == parent: return 200, {'content-type': 'text/html'}, raw
            if url == css: return 200, {'content-type': 'text/css'}, b'p { font-weight: bold }'
            self.assertEqual(url, missing)
            return 404, {'content-type': 'text/plain'}, b'absent'
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for damaged in (False, True):
                    with self.subTest(damaged=damaged), tempfile.TemporaryDirectory() as directory:
                        with Campaign(directory, live=True, minimum_free_bytes=0, sleep=lambda _: None, sender=sender) as campaign:
                            fetch = _Fetcher(campaign, 80); fetch.get(parent)
                            if damaged:
                                fetch.observed[parent] = dict(fetch.observed[parent], body=raw.replace(b'parent', b'change'))
                                with self.assertRaises(AcquisitionError): _startup_dependencies(fetch, browser, parent)
                            else:
                                result = _startup_dependencies(fetch, browser, parent)
                                self.assertTrue(result['fixed_point'])
                                self.assertEqual({u: o['status'] for u, o in fetch.observed.items()}, {parent: 200, css: 200, missing: 404})
            finally:
                browser.close()

    def test_recorded_retry_failures_and_redirect_are_not_dependency_completion(self):
        from driver.prepare.get.transport import RETRY
        from playwright.sync_api import sync_playwright
        parent = 'https://www.sec.gov/Archives/evidence/parent.htm'
        css = 'https://www.sec.gov/Archives/evidence/style.css'
        raw = b'<html><head><link rel="stylesheet" href="style.css"></head><body><p>Source content</p></body></html>'
        # The existing transport owns the retry domain; a recorded error remains
        # evidence of failure, while 200 and original-absence404 are positive controls.
        statuses = [200, 404, 302, *sorted(RETRY)]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for status in statuses:
                    with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                        def sender(url, *args):
                            if url == parent: return 200, {'content-type': 'text/html'}, raw
                            self.assertEqual(url, css)
                            return status, {'content-type': 'text/css'}, b'p { font-weight:bold }' if status == 200 else b''
                        with Campaign(directory, live=True, minimum_free_bytes=0, sleep=lambda _: None, sender=sender) as campaign:
                            fetch = _Fetcher(campaign, 80); fetch.get(parent); fetch.get(css)
                        with Campaign(directory, live=False) as campaign:
                            fetch = _Fetcher(campaign, 80); fetch.get(parent)
                            result = _startup_dependencies(fetch, browser, parent)
                            self.assertEqual(result['fixed_point'], status in (200, 404), result)
                            self.assertEqual(fetch.observed[css]['status'], status)
                            self.assertEqual(campaign.sent_attempts, 0)
            finally:
                browser.close()

    def test_fallback_keeps_all_required_observation_origins(self):
        from driver.prepare.get import acquisition, context_acquire
        parent = 'https://www.sec.gov/Archives/evidence/parent.htm'
        dependency = 'https://www.sec.gov/Archives/evidence/required.css'
        other = 'https://www.sec.gov/Archives/evidence/next.htm'
        # Each earlier observation remains required evidence after switching
        # from source anchors to native nodes; a clean final result cannot erase it.
        cases = [('clean', None), *[(origin, fault)
                 for origin in ('source_initial', 'source_action', 'native_prepare')
                 for fault in ('unobserved', 'retry_status')],
                 ('source_initial', 'navigation'), ('native_prepare', 'navigation')]
        for origin, fault in cases:
            with self.subTest(origin=origin, fault=fault), tempfile.TemporaryDirectory() as directory:
                facts = {'delivered': [], 'refused_get': [], 'refused_navigation': [],
                         'outbound_attempts_refused': []}
                bad = dict(facts)
                if fault == 'unobserved': bad['refused_get'] = [(dependency, 'stylesheet')]
                if fault == 'retry_status': bad['delivered'] = [(dependency, 503, None)]
                if fault == 'navigation': bad['refused_navigation'] = [other]
                class SourceSelection:
                    def __init__(self, *args, **kwargs): pass
                    def run(self, browser):
                        return {'verdict': 'missing', 'baseline': {},
                                'initial': {'facts': {'true': bad if origin == 'source_initial' else facts}},
                                'attempts': [{'state': 'refused: source anchors do not correspond',
                                              'facts': bad if origin == 'source_action' else facts}]}
                class NativeSelection:
                    def __init__(self, *args, **kwargs): pass
                    def prepare(self, browser):
                        self.state_facts = bad if origin == 'native_prepare' else facts
                        return {'native_anchors': 1, 'facts': self.state_facts}
                    def run(self, browser):
                        return {'verdict': 'selected', 'baseline': {}, 'attempts': [
                            {'state': 'qualified', 'source_anchor': 0, 'facts': facts}]}
                with Campaign(directory, live=False, minimum_free_bytes=0) as campaign:
                    fetch = _Fetcher(campaign, 80)
                    if fault == 'retry_status':
                        fetch.observed[dependency] = {'status': 503, 'body': None, 'sha256': None,
                                                      'observed_at': '2026-10-21T00:00:00Z'}
                    with patch.object(acquisition, 'Selection', SourceSelection), patch.object(acquisition, 'NativeSelection', NativeSelection):
                        result, _ = context_acquire._select(fetch, None, parent, 'target', b'member', 'body', 'prefix', 200)
                    if origin == 'clean': self.assertEqual(result['verdict'], 'selected', result)
                    else: self.assertTrue(result['verdict'].startswith('incomplete:'), result)
                    self.assertEqual(campaign.sent_attempts, 0)
