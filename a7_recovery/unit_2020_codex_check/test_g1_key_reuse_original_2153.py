"""The original native lifecycle cannot be replaced by current-context credit."""
import unittest
import test_g1_key_reuse_2152 as BASE


class OriginalEvidence(unittest.TestCase):
    def setUp(self):
        self.case = BASE.PublicEntry()
        self.case.setUp()
        self.case.execute()                 # independent positive control
        self.case.setUp()

    def test_unfinished_original_reading_stops_before_current_key_context(self):
        self.case.old[2]['old-keep/G1b']['attempts'] = {}
        with self.assertRaisesRegex(ValueError, 'old-keep/G1b.*not an exhausted'):
            self.case.execute()
        self.assertEqual(len(self.case.calls), 1)

    def test_original_handle_changed_stops_before_native_work(self):
        self.case.selection['report']['original_g1'] = {'run_dir': 'different history'}
        with self.assertRaisesRegex(ValueError, 'original producer or G1 handle'):
            self.case.execute()
        self.assertEqual(self.case.calls, [])

    def test_moved_signed_report_stops_before_current_key_context(self):
        self.case.hashes['signed'] = 'moved signed report'
        with self.assertRaisesRegex(ValueError, 'signed-key report changed'):
            self.case.execute()
        self.assertEqual(len(self.case.calls), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
