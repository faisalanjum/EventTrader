"""Real child controls for the worker's total filing time limit; no SEC/model calls."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import psutil

from redisDB import prepared_filing as adapter


class FilingDeadline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.filing = dict(accessionNo='0001004434-23-000015', cik='1004434', formType='8-K')
        self.receipt = json.loads((Path(__file__).parent / 'fixtures/real_receipt.json').read_bytes())
        self.receipt['plan']['path'] = str(self.root / 'PLAN.json')
        self.saved = self.root / 'RECEIPT.json'
        self.saved.write_text(json.dumps(self.receipt))
        self.executable = self.root / 'adapter-control'
        self.executable.write_text(f'#!{sys.executable}\n' + '''
import json, os, sys, time
from pathlib import Path
config = json.loads(Path(sys.argv[-1]).read_text())
Path(config['marker']).write_text(str(os.getpid()))
json.loads(sys.stdin.read())
time.sleep(config.get('delay', 0))
print(Path(config['reply']).read_text())
''')
        self.executable.chmod(0o700)
        self.config = dict(python=str(self.executable), reply=str(self.saved),
                           marker=str(self.root / 'launched'), filing_seconds=2)

    def call(self, **settings):
        config = self.root / 'config.json'
        config.write_text(json.dumps(dict(self.config, **settings)))
        start = time.monotonic()
        result = adapter.pointer(self.filing, config)
        return result, time.monotonic() - start

    def test_healthy_and_repeat_preserve_receipt_and_identity(self):
        original = self.saved.read_bytes()
        for seconds in (1, 2):
            result, elapsed = self.call(filing_seconds=seconds, delay=0.02)
            self.assertEqual(result['status'], 'complete', result)
            self.assertEqual(result['package_sha256'], self.receipt['package_sha256'])
            self.assertEqual(result['receipt']['path'], str(self.saved))
            self.assertEqual(self.saved.read_bytes(), original)
            self.assertLess(elapsed, seconds)

    def test_slow_child_cannot_be_credited_and_repaired_call_succeeds(self):
        original = self.saved.read_bytes()
        result, elapsed = self.call(filing_seconds=0.1, delay=0.6)
        self.assertEqual(result['status'], 'failed', result)
        self.assertFalse(adapter.prepared_done(dict(prepared_extraction=result)))
        self.assertLess(elapsed, 0.5)
        self.assertEqual(self.saved.read_bytes(), original)
        recovered, _ = self.call(filing_seconds=2, delay=0)
        self.assertEqual(recovered['status'], 'complete', recovered)

    def test_invalid_budget_refuses_work_with_a_real_positive_control(self):
        self.assertEqual(self.call()[0]['status'], 'complete')
        marker = Path(self.config['marker'])
        for value in (0, -1, True, None, '1', float('nan'), float('inf')):
            marker.unlink(missing_ok=True)
            with self.subTest(value=repr(value)):
                result, _ = self.call(filing_seconds=value)
                self.assertEqual(result['status'], 'failed', result)
                self.assertFalse(marker.exists(), 'invalid limit started the child')

    def test_form_limits_include_amendments_and_an_explicit_fallback(self):
        limits = {'8-K': 2, 'default': 1}
        for form in ('8-K', '8-K/A', '425'):
            self.filing['formType'] = form
            self.receipt['form'] = form
            self.saved.write_text(json.dumps(self.receipt))
            with self.subTest(form=form):
                self.assertEqual(self.call(filing_seconds=limits)[0]['status'], 'complete')
        self.assertEqual(self.call(filing_seconds={'10-K': 2})[0]['status'], 'failed')

    def test_late_receipt_validation_cannot_turn_into_success(self):
        self.assertEqual(self.call()[0]['status'], 'complete')
        read = Path.read_bytes
        def slow(path):
            if path == self.saved: time.sleep(0.25)
            return read(path)
        with patch.object(Path, 'read_bytes', slow):
            result, _ = self.call(filing_seconds=0.2)
        self.assertEqual(result['status'], 'failed', result)
        self.assertIn('receipt validation', result['reasons'][0])

    def test_cancellation_stops_the_real_child_and_remains_cancellation(self):
        self.assertEqual(self.call()[0]['status'], 'complete')
        communicate = adapter.subprocess.Popen.communicate
        for error in (KeyboardInterrupt, SystemExit):
            def cancelled(process, *args, **kwargs):
                try: communicate(process, *args, **dict(kwargs, timeout=0.1))
                except adapter.subprocess.TimeoutExpired: raise error()
                self.fail('the delayed control unexpectedly finished')
            with self.subTest(error=error.__name__), patch.object(adapter.subprocess.Popen, 'communicate', cancelled):
                with self.assertRaises(error): self.call(delay=1)
            self.assertFalse(psutil.pid_exists(int(Path(self.config['marker']).read_text())))


if __name__ == '__main__':
    unittest.main()
