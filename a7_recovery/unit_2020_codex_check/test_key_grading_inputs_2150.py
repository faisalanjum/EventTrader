"""Full event inputs, never a matching question id alone, decide sameness."""
import ast
import copy
from pathlib import Path
import unittest


class EventComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name('prepare_key_grading_2150.py')
        tree = ast.parse(path.read_text())
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'compare_events']
        assert len(nodes) == 1
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
        cls.compare = staticmethod(namespace['compare_events'])

    def setUp(self):
        self.old = {('arm', 'event'): {
            'prompt': 'all references and all candidates',
            'items': [{'question_id': 'Qsame', '_gold': {'value': 8},
                       'reference_card': {'name': 'a'},
                       'candidates': [{'produced_idx': 1, 'record': {'value': 8}}]}],
            'full_positions': [4], 'batch_id': 'G1-002'}}
        self.new = copy.deepcopy(self.old)
        self.assertEqual(self.compare(self.old, self.new), {
            'unchanged': [['arm', 'event']], 'changed': [], 'added': [], 'removed': []})

    def test_prompt_change_with_identical_ids_is_changed(self):
        self.new[('arm', 'event')]['prompt'] += ' another instruction'
        self.assertEqual(self.compare(self.old, self.new)['changed'], [['arm', 'event']])

    def test_each_question_input_change_is_changed(self):
        for field, replacement in (
            ('_gold', {'value': 9}), ('reference_card', {'name': 'b'}),
            ('candidates', [{'produced_idx': 1, 'record': {'value': 9}}])):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.new)
                changed[('arm', 'event')]['items'][0][field] = replacement
                self.assertEqual(self.compare(self.old, changed)['changed'], [['arm', 'event']])

    def test_missing_added_and_other_leg_are_not_reuse(self):
        changed = {('another arm', 'event'): self.new[('arm', 'event')]}
        self.assertEqual(self.compare(self.old, changed), {
            'unchanged': [], 'changed': [], 'added': [['another arm', 'event']],
            'removed': [['arm', 'event']]})

    def test_batch_number_is_not_the_input(self):
        self.new[('arm', 'event')]['batch_id'] = 'G1-073'
        self.assertEqual(self.compare(self.old, self.new)['unchanged'], [['arm', 'event']])

    def test_changed_full_row_binding_is_explicit(self):
        self.new[('arm', 'event')]['full_positions'] = [5]
        self.assertEqual(self.compare(self.old, self.new)['changed'], [['arm', 'event']])

    def test_input_is_not_mutated_and_order_is_stable(self):
        self.old[('z', 'event')] = copy.deepcopy(self.old[('arm', 'event')])
        self.new = dict(reversed(list(copy.deepcopy(self.old).items())))
        before = copy.deepcopy((self.old, self.new))
        self.assertEqual(self.compare(self.old, self.new)['unchanged'],
                         [['arm', 'event'], ['z', 'event']])
        self.assertEqual((self.old, self.new), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
