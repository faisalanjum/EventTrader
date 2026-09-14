"""The collection command must run its configured entry, not silently do nothing.

No harness import or model call: missing required configuration must fail
before a run is created. The real configured success is proved separately
through the native boundary on an isolated, empty-answer packet.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path


class CollectionEntryTest(unittest.TestCase):
    def test_missing_configuration_cannot_succeed_silently(self):
        entry = Path(__file__).with_name('collect_questions_2136.py')
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('A7_') and key != 'PYTHONPATH'}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        result = subprocess.run([sys.executable, str(entry)], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0,
                            'the collection command exited successfully '
                            'without running or requiring its inputs')
        self.assertIn('A7_REAL_CANDIDATE_BUILD', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
