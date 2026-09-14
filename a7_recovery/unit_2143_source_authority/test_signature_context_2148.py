"""Focused invocation-context tests; the separate native run proves the key.

Compile the actual nested boundary and actual existing _using function without
starting their expensive native setup. Only the downstream signature reader
is replaced here, to observe its received input and force a clean refusal.
"""
import ast
import contextlib
import os
import types
import unittest
from pathlib import Path


def function(path, name, namespace, mutant=False):
    found = [n for n in ast.walk(ast.parse(path.read_text()))
             if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(found) == 1
    node = found[0]
    if mutant:
        # Remove only the binding switch: the observed native defect.
        scope = [n for n in node.body if isinstance(n, ast.With)]
        assert len(scope) == 1
        node.body = [n for n in node.body if n is not scope[0]] + scope[0].body
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


class SignatureContext(unittest.TestCase):
    def setUp(self):
        unit = Path(__file__).resolve().parent
        self.candidate = types.SimpleNamespace(ORDINARY='current-binding')
        self.inputs = {'first-key': 'first-binding', 'second-key': 'second-binding'}
        self.calls = []
        self.raise_signature_error = False
        using = function(unit.parent / 'unit_2009/owner/a4_review_composite.py',
                         '_using', {'contextlib': contextlib})

        def read(candidate):
            self.calls.append((candidate, self.candidate.ORDINARY))
            if self.raise_signature_error:
                raise ValueError('native signature refuses')
            return self.candidate.ORDINARY

        self.verify_signature = function(unit / 'build_candidate_2148.py',
                            'historical_signature', {
                                'signature_inputs': self.inputs,
                                'R': types.SimpleNamespace(_using=using),
                                'C': self.candidate, 'original_signature': read},
                            mutant=os.environ.get('A7_CONTEXT_MUTANT') == '1')

    def positive(self):
        self.assertEqual(self.verify_signature('first-key'), 'first-binding')
        self.assertEqual(self.candidate.ORDINARY, 'current-binding')

    def test_own_binding_not_the_current_candidate(self):
        self.positive()
        self.assertEqual(self.calls, [('first-key', 'first-binding')])

    def test_all_declared_signatures_both_orders(self):
        self.positive()
        for keys in (list(self.inputs), list(reversed(self.inputs))):
            for key in keys:
                self.assertEqual(self.verify_signature(key), self.inputs[key])
                self.assertEqual(self.candidate.ORDINARY, 'current-binding')

    def test_unknown_signature_has_no_fallback(self):
        self.positive()
        before = list(self.calls)
        with self.assertRaisesRegex(ValueError, 'no proved ordinary binding'):
            self.verify_signature('unknown-key')
        self.assertEqual(self.calls, before)
        self.assertEqual(self.candidate.ORDINARY, 'current-binding')

    def test_failure_restores_the_current_binding(self):
        self.positive()
        self.raise_signature_error = True
        with self.assertRaisesRegex(ValueError, 'native signature refuses'):
            self.verify_signature('second-key')
        self.assertEqual(self.calls[-1], ('second-key', 'second-binding'))
        self.assertEqual(self.candidate.ORDINARY, 'current-binding')


if __name__ == '__main__':
    unittest.main(verbosity=2)
