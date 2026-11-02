"""Lost saved browser evidence is a technical failure eligible for retry."""
import json
import shutil
import unittest

from redisDB import prepared_filing as adapter
from tests.driver.prepare import test_caller as caller


class CaptureFailures(unittest.TestCase):
    def setUp(self):
        caller.Caller.setUp(self)
        self.addCleanup(shutil.rmtree, self.t)

    def run_capture(self, damage, where):
        row = caller.row(0)
        row['probe'].update(capture=damage, capture_where=where)
        code, out, *_ = caller.Caller.go(self, rows=(row,))
        result = json.loads((out / 'RESULT.json').read_bytes())
        status, reasons = adapter.status(out / 'RESULT.json', result['plan_sha256'],
                                         [dict(filename=row['file_id'], category='html')])
        return code, status, result['rows'][0], reasons

    def test_intact_capture_is_verified_in_each_owned_reading(self):
        for where in ('initial', 'state', 'source'):
            with self.subTest(where=where):
                code, status, row, reasons = self.run_capture('good', where)
                self.assertEqual((code, status, row['outcome']), (0, 'complete', adapter.VERIFIED), reasons)

    def test_each_native_corruption_is_retryable_in_each_owned_reading(self):
        for where in ('initial', 'state', 'source'):
            for damage in ('missing', 'not_gzip', 'truncated', 'wrong_hash', 'bad_deflate', 'bad_crc'):
                with self.subTest(where=where, damage=damage):
                    code, status, row, reasons = self.run_capture(damage, where)
                    self.assertEqual((code, status), (1, 'failed'), reasons)
                    self.assertTrue(row.get('technical_failures'), row)

    def test_a_fresh_intact_attempt_recovers_after_capture_damage(self):
        self.assertEqual(self.run_capture('truncated', 'initial')[1], 'failed')
        self.assertEqual(self.run_capture('good', 'initial')[1], 'complete')


if __name__ == '__main__':
    unittest.main()
