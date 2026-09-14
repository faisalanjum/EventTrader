"""Focused tests of the two new seams, without importing the native harness.

The separate test_cold_history_2134 exercises the real saved population. These
tests isolate input identity, restoration and failures, including mutations.
"""
import ast
import collections
import contextlib
import functools
import hashlib
import json
import os
from pathlib import Path
import types
import unittest

OWNER = Path(__file__).with_name('a4_v6_successor_chain.review_2134.py')


@contextlib.contextmanager
def using(owner, **values):
    old = {k: getattr(owner, k) for k in values}
    try:
        for k, v in values.items():
            setattr(owner, k, v)
        yield
    finally:
        for k, v in old.items():
            setattr(owner, k, v)


def fixture(mutation=False):
    tree = ast.parse(OWNER.read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('_checked_prefixes', '_round_input_scope')]
    if mutation:
        changed = 0
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets):
                n.value = ast.copy_location(ast.Name(id='expected', ctx=ast.Load()), n.value)
                changed += 1
        assert changed == 1
    Bound = collections.namedtuple('Bound', 'package decision_correction_v6')
    bound = Bound('/fixture/carrier', 'round')
    V2 = types.SimpleNamespace(served_prefix=lambda b: 'old')
    calls = []

    def base_prefix(package, keys):
        if package != bound.package:
            raise ValueError('different carrier')
        return V2.served_prefix(bound) + ':' + ','.join(keys)

    F = types.SimpleNamespace(v6_prefix=base_prefix)

    @functools.lru_cache(maxsize=None)
    def cache(event_dir, b, phase, receipt_sha, expected):
        calls.append((event_dir, phase, expected))
        return F.v6_prefix(bound.package, ('source', 'rows')) == 'new:source,rows'

    F._accepted_shards_cached = cache
    namespace = dict(contextlib=contextlib, json=json, os=os, F=F,
                     R=types.SimpleNamespace(_using=using),
                     C2065=types.SimpleNamespace(V2=V2), PHASE='phase',
                     K=types.SimpleNamespace(_sha=lambda text: hashlib.sha256(text.encode()).hexdigest()),
                     _ORIGINAL={'_accepted_shards_cached': cache})
    exec(compile(tree, str(OWNER), 'exec'), namespace)

    def scope(prefixes=None, findings=None, rounds=(), signatures=None):
        return namespace['_round_input_scope'](
            bound, findings or {}, [], rounds, signatures, prefixes or {})

    def read(phase='phase', run='round'):
        return F._accepted_shards_cached(run, bound, phase, 'receipt', ('source',))

    return types.SimpleNamespace(ns=namespace, bound=bound, F=F, V2=V2,
                                 cache=cache, calls=calls, scope=scope, read=read)


class RoundInputTests(unittest.TestCase):
    def test_positive_negative_positive_within_one_operation(self):
        f = fixture()
        for prefixes, expected in (({'round': lambda b: 'new'}, True), ({}, False),
                                   ({'round': lambda b: 'new'}, True)):
            with f.scope(prefixes):
                self.assertEqual(f.read(), expected)
        self.assertEqual(len(f.calls), 2)
        self.assertIs(f.F._accepted_shards_cached, f.cache)
        self.assertEqual(f.F.v6_prefix(f.bound.package, ('source',)), 'old:source')

    def test_full_finding_order_and_history_are_input(self):
        f = fixture()
        rows = [collections.OrderedDict([('a', 1), ('b', 2)]),
                collections.OrderedDict([('b', 2), ('a', 1)])]
        for row in rows:
            with f.scope({'round': lambda b: 'new'}, findings=row):
                self.assertTrue(f.read())
        with f.scope({'round': lambda b: 'new'}, findings=rows[0], rounds=(('earlier', []),)):
            self.assertTrue(f.read())
        with f.scope({'round': lambda b: 'new'}, findings=rows[0], signatures={'round': 'signature'}):
            self.assertTrue(f.read())
        self.assertEqual(len(f.calls), 4)

    def test_prefix_only_swap_and_carrier_failure_restore(self):
        f = fixture()
        original = f.F.v6_prefix
        with self.assertRaisesRegex(ValueError, 'different carrier'):
            with f.scope({'round': lambda b: 'new'}):
                self.assertEqual(f.V2.served_prefix(f.bound), 'old')
                self.assertEqual(f.F.v6_prefix(f.bound.package, ('unfamiliar',)), 'new:unfamiliar')
                self.assertEqual(f.V2.served_prefix(f.bound), 'old')
                f.F.v6_prefix('/different', ())
        self.assertIs(f.F.v6_prefix, original)
        self.assertIs(f.F._accepted_shards_cached, f.cache)
        self.assertEqual(f.V2.served_prefix(f.bound), 'old')

    def test_other_phase_or_run_keeps_existing_cache_key(self):
        f = fixture()
        with f.scope({'round': lambda b: 'new'}):
            self.assertTrue(f.read(phase='earlier'))
            self.assertTrue(f.read(run='other'))
            self.assertEqual([call[2] for call in f.calls], [('source',), ('source',)])
            f.F._accepted_shards_cached.cache_clear()
            self.assertEqual(f.cache.cache_info().currsize, 0)

    def test_declarations(self):
        check = fixture().ns['_checked_prefixes']
        self.assertEqual(check(None, ('round',)), {})
        fn = lambda b: 'new'
        self.assertEqual(check({'round': fn}, ('round',)), {'round': fn})
        with self.assertRaisesRegex(ValueError, 'outside this history'):
            check({'foreign': fn}, ('round',))
        with self.assertRaisesRegex(ValueError, 'must be callable'):
            check({'round': 'not a function'}, ('round',))

    def test_renderer_exception_restores_scope(self):
        f = fixture()

        def fail(bound):
            raise ValueError('renderer failure')

        with self.assertRaisesRegex(ValueError, 'renderer failure'):
            with f.scope({'round': fail}):
                f.read()
        with f.scope({'round': lambda b: 'new'}):
            self.assertTrue(f.read())
        self.assertEqual(f.V2.served_prefix(f.bound), 'old')

    def test_removing_input_identity_reproduces_the_wrong_accept(self):
        f = fixture(mutation=True)
        with f.scope({'round': lambda b: 'new'}):
            self.assertTrue(f.read())
        with f.scope():
            self.assertTrue(f.read(), 'mutant must actually credit the wrong input')
        self.assertEqual(len(f.calls), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
