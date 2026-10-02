"""Offline checks of the overnight runner: success, resume, and each safe stop."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from driver.prepare.campaign import Campaign
from scripts.driver.prepare import full_run

FIXTURES = Path(__file__).with_name('fixtures')
AMG = dict(acc='0001004434-23-000015', form='8-K', cik='1004434')
BASE = 'https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/'
MISSING = [dict(acc=f'0000000001-23-00000{i}', form='8-K', cik='1') for i in range(1, 4)]


class FullRunTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
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
        inputs.write_text(json.dumps(dict(filings=filings)))
        return full_run.run(inputs, self.root / 'out', live=True, min_free_gb=settings.pop('min_free_gb', 0),
                            campaign_class=self.campaign, **settings)

    def rows(self):
        path = self.root / 'out' / 'results.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_success_then_resume_makes_no_requests(self):
        summary = self.run_with([AMG])
        self.assertEqual((summary['finished'], summary['counts']), (True, {'OK': 1}))
        self.assertEqual((self.rows()[0]['members'], len(self.calls)), (17, 2))
        self.assertEqual(json.loads((self.root / 'out' / 'progress.json').read_text())['done'], 1)
        self.run_with([AMG])
        self.assertEqual((len(self.rows()), len(self.calls)), (1, 2))

    def test_consecutive_failures_stop_the_run(self):
        summary = self.run_with(MISSING, max_consecutive_failures=2)
        self.assertIn('2 consecutive failures', summary['stop'])
        self.assertEqual([row['status'] for row in self.rows()], ['FAILED', 'FAILED'])

    def test_low_disk_stops_before_any_request_and_records_nothing(self):
        summary = self.run_with([AMG], min_free_gb=10**9)
        self.assertIn('storage', summary['stop'])
        self.assertEqual((self.rows(), self.calls), ([], []))

    def test_http_403_stops_without_marking_the_filing_done(self):
        self.status = 403
        summary = self.run_with([AMG] + MISSING)
        self.assertIn('403', summary['stop'])
        self.assertEqual((self.rows(), len(self.calls)), ([], 1))
        self.assertTrue((self.root / 'out' / 'campaign' / 'STOP.json').exists())


if __name__ == '__main__':
    unittest.main()
