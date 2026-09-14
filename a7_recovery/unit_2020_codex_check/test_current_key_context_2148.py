"""Exercise the real shared input boundary without starting the native run."""
import contextlib
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2143_source_authority'))
from test_signature_context_2148 import function
import a7_current_key_context_2148 as CURRENT


class SharedSignatureContext(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        using = function(root / 'unit_2009/owner/a4_review_composite.py',
                         '_using', {'contextlib': contextlib})
        self.R = types.SimpleNamespace(_using=using)
        self.C = types.SimpleNamespace(ORDINARY='new-key-input')
        self.inputs = {'earlier-one': 'one-input', 'earlier-two': 'two-input'}
        self.seen = []
        self.raise_on = None

        def read(candidate):
            self.seen.append((candidate, self.C.ORDINARY))
            if candidate == self.raise_on:
                raise ValueError('signature does not prove')
            return self.C.ORDINARY

        self.original = read
        self.X = types.SimpleNamespace(signature_accounting=read)

    def test_real_boundary_all_inputs_and_restore(self):
        with CURRENT.historical_inputs(self.R, self.C, self.X, self.inputs):
            for keys in (list(self.inputs), list(reversed(self.inputs))):
                for key in keys:
                    self.assertEqual(self.X.signature_accounting(key), self.inputs[key])
                    self.assertEqual(self.C.ORDINARY, 'new-key-input')
        self.assertIs(self.X.signature_accounting, self.original)

    def test_missing_history_refuses_after_positive(self):
        with CURRENT.historical_inputs(self.R, self.C, self.X, self.inputs):
            self.assertEqual(self.X.signature_accounting('earlier-one'), 'one-input')
            before = list(self.seen)
            with self.assertRaisesRegex(ValueError, 'no proved ordinary binding'):
                self.X.signature_accounting('unrecorded')
            self.assertEqual(self.seen, before)
        self.assertIs(self.X.signature_accounting, self.original)
        self.assertEqual(self.C.ORDINARY, 'new-key-input')

    def test_nested_real_boundary_and_failure_restore(self):
        with CURRENT.historical_inputs(self.R, self.C, self.X, self.inputs):
            first = self.X.signature_accounting
            self.assertEqual(first('earlier-one'), 'one-input')
            with CURRENT.historical_inputs(self.R, self.C, self.X, self.inputs):
                self.assertEqual(self.X.signature_accounting('earlier-two'), 'two-input')
                self.raise_on = 'earlier-one'
                with self.assertRaisesRegex(ValueError, 'signature does not prove'):
                    self.X.signature_accounting('earlier-one')
                self.assertEqual(self.C.ORDINARY, 'new-key-input')
            self.assertIs(self.X.signature_accounting, first)
        self.assertIs(self.X.signature_accounting, self.original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
