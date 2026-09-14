"""Input routing only; use the real A5 file/lock readers on isolated files.

These fixtures are NOT real signatures. Native signature/lock proof belongs
to the separate existing owner; here we prove immutable expectations, exact
alias routing and restoration rather than reproduce its signature algorithm.
"""
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

import a7_signed_key_input_2149 as INPUT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def functions(path, names, namespace):
    nodes = [n for n in ast.parse(path.read_text()).body
             if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


class SignedInput(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory(prefix='key-input-test-', dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.A5 = types.ModuleType('isolated_a5')
        self.A5.__dict__.update(io=io, json=json, os=os, hashlib=hashlib)
        functions(root / 'unit_2008/harness_g1v3/build_a5_exp5_kit.py',
                  ('_pinned_file', 'a4_lock_receipt_path', 'a4_lock'), self.A5.__dict__)
        scope_ns = {'contextlib': contextlib}
        functions(root / 'unit_2009/owner/a4_review_composite.py', ('_using',), scope_ns)
        self.A5.APPROVED_LOCK_PIN = '/tmp/a7_approved_key/a4_final_key_lock.json'
        self.A5.APPROVED_RECEIPT_PIN = '/tmp/a7_approved_key/a4_final_key_lock_receipt.json'
        self.A5._binding_pin = lambda logical: 'other-original-pin'
        self.E = types.SimpleNamespace(
            G=types.SimpleNamespace(_sha_file=sha),
            K=types.SimpleNamespace(_load=lambda p: json.loads(Path(p).read_text())),
            R=types.SimpleNamespace(_using=scope_ns['_using']))
        self.old = self.make('old', {'run': 'older'})
        self.new = self.make('new', {'run': 'later', 'recovery': 'retained'})
        old = self.old[2]
        self.A5.APPROVED_KEY_DIR = self.A5.A4_LOCK_DIR = old['candidate']
        self.A5.A4_LOCK_PATH = old['lock']
        self.A5.A4_LOCK_SHA = old['lock_sha256']
        self.A5.A4_LOCK_RECEIPT_SHA = old['receipt_sha256']
        self.original = {k: getattr(self.A5, k) for k in (
            'APPROVED_KEY_DIR', 'A4_LOCK_DIR', 'A4_LOCK_PATH', 'A4_LOCK_SHA',
            'A4_LOCK_RECEIPT_SHA', '_binding_pin', '_pinned_file')}
        self.A5.a4_lock()  # genuine old-input positive control
        with self.use(self.new):
            self.assertEqual(self.ordinary(), {'run': 'later', 'recovery': 'retained'})
        self.restored()

    def write(self, path, data):
        path.write_text(json.dumps(data))
        return str(path), sha(path)

    def make(self, name, ordinary):
        candidate = self.root / name
        candidate.mkdir()
        lock, lock_sha = self.write(candidate / 'a4_final_key_lock.json', {
            'state': 'LOCKED', 'signer': {'signed': True, 'blocked': []}, 'test_key': name})
        receipt, receipt_sha = self.write(candidate / 'a4_final_key_lock_receipt.json', {
            'lock_sha256': lock_sha, 'every_bound_value_refuses_when_mutated': True})
        ordinary_path, ordinary_sha = self.write(candidate / 'ordinary_bound.json', ordinary)
        report = dict(candidate=str(candidate), lock=lock, lock_sha256=lock_sha,
                      receipt=receipt, receipt_sha256=receipt_sha,
                      ordinary=ordinary_path, ordinary_sha256=ordinary_sha)
        path, digest = self.write(candidate / 'report.json', report)
        return path, digest, report

    def use(self, values):
        return INPUT.approved_inputs(self.E, self.A5, values[0], values[1])

    def ordinary(self):
        path = '/tmp/a7_approved_key/ordinary_bound.json'
        return self.A5._pinned_file(path, self.A5._binding_pin(path), 'ordinary')

    def restored(self):
        for key, value in self.original.items():
            self.assertEqual(getattr(self.A5, key), value, key)
        self.A5.a4_lock()

    def test_two_supported_keys_and_all_three_aliases(self):
        third = self.make('unfamiliar', {'arbitrary': ['different', 'values']})
        for values in (self.new, third):
            with self.use(values):
                for logical, path, pin in (
                    (self.A5.APPROVED_LOCK_PIN, values[2]['lock'], values[2]['lock_sha256']),
                    (self.A5.APPROVED_RECEIPT_PIN, values[2]['receipt'], values[2]['receipt_sha256'])):
                    self.assertEqual(self.A5._binding_pin(logical), pin)
                    self.assertEqual(self.A5._pinned_file(logical, pin, 'alias'),
                                     json.loads(Path(path).read_text()))
                self.assertEqual(self.ordinary(), json.loads(Path(values[2]['ordinary']).read_text()))
            self.restored()

    def test_wrong_external_report_pin_refuses(self):
        with self.assertRaisesRegex(ValueError, 'unapproved signed-key report'):
            with INPUT.approved_inputs(self.E, self.A5, self.new[0], '0' * 64):
                self.fail('entered unapproved context')
        self.restored()

    def test_each_input_drift_refuses(self):
        for field in ('lock', 'receipt', 'ordinary'):
            with self.subTest(field=field):
                path = Path(self.new[2][field])
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'moved'):
                        with self.use(self.new):
                            self.fail('accepted moved input')
                finally:
                    path.write_bytes(original)
                self.restored()

    def test_coherent_changed_pair_does_not_invent_new_expectation(self):
        lock, receipt = (Path(self.new[2][f]) for f in ('lock', 'receipt'))
        self.write(lock, {'state': 'LOCKED', 'signer': {'signed': True, 'blocked': []},
                          'test_key': 'wrong-but-self-consistent'})
        self.write(receipt, {'lock_sha256': sha(lock), 'every_bound_value_refuses_when_mutated': True})
        with self.assertRaisesRegex(ValueError, 'moved'):
            with self.use(self.new):
                self.fail('accepted self-consistent substituted files')
        self.restored()

    def test_unknown_input_keeps_original_reader(self):
        path, digest = self.write(self.root / 'other.json', {'kept': True})
        with self.use(self.new):
            self.assertEqual(self.A5._binding_pin(path), 'other-original-pin')
            self.assertEqual(self.A5._pinned_file(path, digest, 'other'), {'kept': True})
        self.restored()

    def test_body_failure_restores_every_binding(self):
        with self.assertRaisesRegex(ValueError, 'downstream refusal'):
            with self.use(self.new):
                raise ValueError('downstream refusal')
        self.restored()

    def test_changed_report_during_use_refuses_and_restores(self):
        with self.assertRaisesRegex(ValueError, 'signed-key report changed'):
            with self.use(self.new):
                path = Path(self.new[0])
                path.write_bytes(path.read_bytes() + b' ')
        self.restored()


if __name__ == '__main__':
    unittest.main(verbosity=2)
