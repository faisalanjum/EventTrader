"""Exercise the caller's report expression without its expensive native setup.

The full native job separately proves the actual lifecycle and consumer.
These checks only cover lossless JSON reporting of their tuple-keyed result.
"""
import ast
from collections import OrderedDict
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


class ResolutionReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name('prepare_current_g23_2157.py')
        tree = ast.parse(path.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'prepare')
        assignment = next(n for n in fn.body if isinstance(n, ast.Assign)
                          and isinstance(n.targets[0], ast.Name)
                          and n.targets[0].id == 'g1_review')
        value = next(k.value for k in assignment.value.keywords
                     if k.arg == 'resolutions')
        cls.expression = compile(ast.Expression(value), str(path), 'eval')
        comparison = next(n.test for n in ast.walk(fn)
                          if isinstance(n, ast.Assert)
                          and any(isinstance(x, ast.Name) and x.id == 'frozen'
                                  for x in ast.walk(n.test)))
        cls.comparison = compile(ast.Expression(comparison), str(path), 'eval')

    def render(self, resolutions):
        before = copy.deepcopy(resolutions)
        result = eval(self.expression, {'resolutions': resolutions})
        text = json.dumps(result, sort_keys=True)
        self.assertEqual(resolutions, before)
        return json.loads(text)

    def test_exact_bindings_and_null_or_zero_decisions_survive(self):
        rows = {'unfamiliar-arm': {('source|one', 2): None,
                                  ('source', 12): 0,
                                  ('source', 2): 19}}
        self.assertEqual(self.render(rows), {'unfamiliar-arm': [
            [['source', 2], 19], [['source', 12], 0],
            [['source|one', 2], None]]})

    def test_empty_and_sparse_results_remain_empty(self):
        self.assertEqual(self.render({}), {})
        self.assertEqual(self.render({'unmatched-arm': {}}), {'unmatched-arm': []})

    def test_row_order_does_not_change_the_report(self):
        pairs = [(('event-b', 3), None), (('event-a', 8), 0)]
        self.assertEqual(self.render({'arm': dict(pairs)}),
                         self.render({'arm': dict(reversed(pairs))}))

    def compare(self, frozen, expected):
        return eval(self.comparison, {
            'frozen': frozen, 'kind': 'G2', 'doc': {'key_identity': 'key'},
            'rows': [], 'GR': SimpleNamespace(kind_candidate=lambda *a: expected),
            'G': SimpleNamespace(_plain=lambda x: json.dumps(x, sort_keys=True))})

    def test_full_candidate_json_roundtrip_ignores_only_container_representation(self):
        expected = OrderedDict([('population', {'arm|event': [(4, 7), (9, 0)]}),
                                ('key_identity', 'key'), ('questions', 2)])
        frozen = json.loads(json.dumps(expected, sort_keys=True),
                            object_pairs_hook=OrderedDict)
        self.assertTrue(self.compare(frozen, expected))

    def test_roundtrip_comparison_still_rejects_every_changed_field(self):
        expected = {'population': {'arm|event': [(4, 7)]},
                    'key_identity': 'key', 'questions': 1,
                    'rules_block_sha256': 'rules', 'task_kind': 'G2'}
        frozen = json.loads(json.dumps(expected))
        self.assertTrue(self.compare(frozen, expected))
        for field in expected:
            changed = copy.deepcopy(frozen)
            changed[field] = 'different'
            with self.subTest(field=field):
                self.assertFalse(self.compare(changed, expected))


if __name__ == '__main__':
    unittest.main()
