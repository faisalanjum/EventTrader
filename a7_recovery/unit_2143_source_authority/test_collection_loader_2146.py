"""Focused entry-loader tests; the real collection path has separate native proof.

Only the expensive prepared-input callback is stopped here. The actual main,
path/hash check and Python source loader execute, using a harmless owner file.
"""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_authority_2143 as C


class CollectionLoaderTest(unittest.TestCase):
    def run_entry(self, name, wrong_pin=False):
        with tempfile.TemporaryDirectory(prefix='a7-loader-test-') as folder:
            owner = Path(folder) / name
            owner.write_text('LOADER_TEST_MARKER = True\n', encoding='utf-8')
            digest = hashlib.sha256(owner.read_bytes()).hexdigest()
            entered = []
            environment = {
                'A7_COLLECT_REPORT': 'not-read-by-this-loader-test',
                'A7_COLLECT_REPORT_SHA256': 'not-read-by-this-loader-test',
                'A7_COLLECT_STATES': '[]', 'A7_TAG': 'loader-test',
                'A7_KEY_SUCCESSOR_CANDIDATE': str(owner),
                'A7_KEY_SUCCESSOR_CANDIDATE_SHA256':
                    '0' * 64 if wrong_pin else digest}
            E = types.ModuleType('prepare_g23_partial_2097')
            E.G = types.SimpleNamespace(_sha_file=lambda p:
                hashlib.sha256(Path(p).read_bytes()).hexdigest())
            E.with_prepared_inputs = entered.append
            with mock.patch.dict(os.environ, environment), \
                    mock.patch.dict(sys.modules, {'prepare_g23_partial_2097': E}), \
                    mock.patch.object(sys, 'path', list(sys.path)):
                if wrong_pin:
                    with self.assertRaisesRegex(ValueError, 'not the pinned'):
                        C.main()
                    self.assertEqual(entered, [])
                    self.assertFalse(hasattr(E, 'X'))
                else:
                    C.main()
                    self.assertTrue(E.X.LOADER_TEST_MARKER)
                    self.assertEqual(len(entered), 1)

    def test_python_path_positive_control(self):
        self.run_entry('owner.py')

    def test_pinned_source_is_not_selected_by_filename_suffix(self):
        for name in ('owner', 'owner.saved'):
            with self.subTest(name=name):
                self.run_entry(name)

    def test_wrong_pin_refuses_before_loading(self):
        self.run_entry('owner.py', wrong_pin=True)


if __name__ == '__main__':
    unittest.main()
