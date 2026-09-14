"""Proof-boundary controls, not substitutes for native evidence verification."""
import copy
from contextlib import contextmanager, ExitStack
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_partial_grading_2095 as P
import a7_g1_key_reuse_2152 as REUSE


def fixture():
    def state(names, selected):
        rows, lanes = [], {}
        for name in names:
            for letter in ('G1a', 'G1b'):
                lane = name + '/' + letter
                rows.append({'lane_id': lane, 'batch_id': name,
                             'prompt_sha256': 'same prompt ' + letter,
                             'expected_input': {'payload_sha256': 'approved input'}})
                lanes[lane] = {'batch_id': name, 'attempts': {1: True} if selected else {},
                               'selected': 1 if selected else None,
                               'relation': {7: [11]} if selected else None}
        root = {'rows': rows, 'lane': {'model': 'supported-model'},
                'owners': {'parser': 'unchanged'}, 'max_attempts': G.MAX_ATTEMPTS,
                'max_output_tokens': '128000', 'rules_block_sha256': 'same rules'}
        doc = {'schema': G.SCHEMA, 'launchers': {
            'lanes': ['G1a', 'G1b'], 'rows': copy.deepcopy(rows)}}
        return root, doc, lanes
    old = state(['old-keep', 'old-changed'], True)
    old[2]['old-keep/G1b'].update(attempts={1: False, 2: False},
                               selected=None, relation=None)
    new = state(['new-keep', 'new-changed'], False)
    selection = {'original_candidate': old[1], 'current_candidate': new[1],
                 'carry_batches': {'new-keep': 'old-keep'},
                 'eligible_lanes': ['new-changed/G1a', 'new-changed/G1b']}
    problems = [r['lane_id'] + ' has no selected valid attempt' for r in new[0]['rows']]
    return old, new, problems, selection, {}


class MergeProof(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        result, problems = REUSE._merge(*copy.deepcopy(self.data))
        self.assertEqual(result[2]['new-keep/G1a']['relation'], {7: [11]})
        self.assertEqual(problems, [n + ' has no selected valid attempt' for n in
                                  ('new-keep/G1b', 'new-changed/G1a', 'new-changed/G1b')])

    def test_copy_is_exact_except_packaging_name_and_inputs_are_unchanged(self):
        before = copy.deepcopy(self.data)
        result, _ = REUSE._merge(*self.data)
        expected = dict(self.data[0][2]['old-keep/G1a'], batch_id='new-keep')
        self.assertEqual(result[2]['new-keep/G1a'], expected)
        result[2]['new-keep/G1a']['relation'][7].append(99)
        self.assertEqual(self.data, before)

    def test_existing_partial_owner_refuses_changed_uncalled_and_preserves_old_invalid(self):
        state, problems = REUSE._merge(*self.data)
        pins = {P.POLICY_PIN: G._sha_file(P.__file__),
                P.RULE_PIN: G._sha_file(str(P.RULE_FILE))}
        g1 = {'candidate_dir': 'fixture', 'run_dir': 'fixture', 'pins': pins}
        with R._using(B, refuse=lambda *a: (state, problems)):
            with self.assertRaisesRegex(ValueError, 'new-changed/G1a.*not an exhausted'):
                P.lifecycle(g1)
        for lane in self.data[3]['eligible_lanes']:
            self.data[1][2][lane].update(attempts={1: True}, selected=1, relation={9: [13]})
        self.data[2][:] = [r['lane_id'] + ' has no selected valid attempt'
                          for r in self.data[1][0]['rows']
                          if self.data[1][2][r['lane_id']]['selected'] is None]
        state, problems = REUSE._merge(*self.data)
        with R._using(B, refuse=lambda *a: (state, problems)):
            admitted = P.lifecycle(g1)
        self.assertIsNone(admitted[2]['new-keep/G1b']['selected'])
        self.assertEqual(admitted[2]['new-keep/G1b']['attempts'], {1: False, 2: False})
        self.assertEqual(admitted[2]['new-changed/G1a']['relation'], {9: [13]})

    def test_every_runtime_rule_and_transport_drift_refuses(self):
        for field in ('lane', 'owners', 'max_attempts', 'max_output_tokens', 'rules_block_sha256'):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data[1][0][field] = 'changed'
                with self.assertRaises(ValueError):
                    REUSE._merge(*data)
        for field in ('expected_input', 'prompt_sha256'):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data[1][0]['rows'][0][field] = 'changed'
                with self.assertRaises(ValueError):
                    REUSE._merge(*data)

    def test_any_new_reservation_on_carried_task_refuses_even_without_answer(self):
        for attempt in (1, 2):
            data = copy.deepcopy(self.data)
            data[4][(attempt, 'new-keep/G1a')] = 1
            with self.assertRaisesRegex(ValueError, 'reserved'):
                REUSE._merge(*data)

    def test_carry_cannot_hide_any_new_attempt_or_relation(self):
        for field, value in (('attempts', {1: False}), ('selected', 1), ('relation', {})):
            data = copy.deepcopy(self.data)
            data[1][2]['new-keep/G1a'][field] = value
            with self.assertRaises(ValueError):
                REUSE._merge(*data)

    def test_unrelated_native_error_is_never_filtered(self):
        for problem in ('wrong request identity', 'unfinalized segment', 'unknown lane',
                        'missing raw answer', 'owner hash changed'):
            data = copy.deepcopy(self.data)
            data[2].append(problem)
            with self.assertRaisesRegex(ValueError, 'native evidence'):
                REUSE._merge(*data)

    def test_missing_or_extra_lane_and_changed_candidate_refuse(self):
        for change in ('missing', 'extra', 'candidate'):
            data = list(copy.deepcopy(self.data))
            if change == 'missing':
                del data[1][2]['new-keep/G1a']
            elif change == 'extra':
                data[1][2]['alien/G1a'] = copy.deepcopy(data[1][2]['new-keep/G1a'])
            else:
                data[1] = (data[1][0], dict(data[1][1], alien=True), data[1][2])
            with self.assertRaises(ValueError):
                REUSE._merge(*data)

    def test_selection_cannot_drop_changed_lanes_or_duplicate_old_credit(self):
        data = copy.deepcopy(self.data)
        data[3]['eligible_lanes'].pop()
        with self.assertRaises(ValueError):
            REUSE._merge(*data)
        data = copy.deepcopy(self.data)
        data[3]['carry_batches']['new-changed'] = 'old-keep'
        with self.assertRaises(ValueError):
            REUSE._merge(*data)


class PublicEntry(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(REUSE.SELECTION_DIR))
        import g1_reuse_inputs_2152 as SELECT
        import a7_reference_inventory as RI
        self.SELECT, self.RI = SELECT, RI
        self.old, self.new, self.problems, self.selection, self.claimed = fixture()
        self.old_producer, self.producer = {'run': 'old'}, {'run': 'new'}
        self.old[1]['producer_identity'] = self.old_producer
        self.new[1]['producer_identity'] = self.producer
        for batch, leg, source in (('new-keep', 'arm', 'kept event'),
                                    ('new-changed', 'arm', 'changed event')):
            self.new[1].setdefault('question_bindings', []).append(
                {'batch_id': batch, 'leg': leg, 'source_id': source})
        for lane in self.selection['eligible_lanes']:
            self.new[2][lane].update(attempts={1: True}, selected=1, relation={9: [13]})
        self.problems = [r['lane_id'] + ' has no selected valid attempt'
                         for r in self.new[0]['rows']
                         if self.new[2][r['lane_id']]['selected'] is None]
        self.hashes = {str(REUSE.__file__): 'reuse code',
                       str(REUSE.SELECTION_DIR / 'g1_reuse_inputs_2152.py'): 'selection code',
                       'report': 'input report', 'signed': 'signed report',
                       'reference': 'reference inventory',
                       REUSE.CURRENT.__file__: 'current context',
                       REUSE.INPUT.__file__: 'signed input',
                       P.__file__: 'partial code', str(P.RULE_FILE): 'partial rule'}
        partial = {P.POLICY_PIN: 'partial code', P.RULE_PIN: 'partial rule'}
        self.original_g1 = {'candidate_dir': 'old candidate', 'run_dir': 'old run',
                            'pins': dict(partial, run_tree_sha256='old tree', run_file_count=5)}
        self.g1 = {'candidate_dir': 'new candidate', 'run_dir': 'new run',
                   'pins': dict(partial, run_tree_sha256='new tree', run_file_count=3,
                                candidate_sha256='new candidate pin',
                                **{REUSE.CODE_PIN: 'reuse code',
                                   REUSE.SELECTION_PIN: 'selection code',
                                   REUSE.REPORT_PIN: 'input report'})}
        report = {'original_producer': self.old_producer, 'original_g1': self.original_g1,
                  'producer': self.producer, 'g1_candidate_sha256': 'new candidate pin',
                  'context_sha256': 'current context', 'input_owner_sha256': 'signed input',
                  'signed_key_report': 'signed', 'signed_key_report_sha256': 'signed report',
                  'reference_inventory': 'reference', 'reference_inventory_sha256': 'reference inventory',
                  'evaluation': 'evaluation', 'evaluation_sha256': 'evaluation pin',
                  'key_identity': {'key': 'approved'}}
        self.selection.update(report=report, candidate_dir='new candidate')
        self.phase, self.calls = 'old', []

    def execute(self, callback=None):
        def native(candidate, run, pins):
            self.calls.append((self.phase, candidate, run, copy.deepcopy(pins)))
            if run == 'old run':
                self.assertEqual(self.phase, 'old')
                return self.old, ['old-keep/G1b has no selected valid attempt']
            self.assertEqual(self.phase, 'new')
            return self.new, self.problems

        @contextmanager
        def key_scope(*args):
            self.assertEqual(len(self.calls), 1, 'old native proof must precede the new key')
            self.phase = 'new'
            try:
                yield None, 'approved Bound', None
            finally:
                self.phase = 'old'

        @contextmanager
        def input_scope(*args):
            yield {'signed': True}

        E = SimpleNamespace(g1=self.original_g1,
            K=SimpleNamespace(_load=lambda path: {'preparation': 'prep', 'preparation_sha256': 'prep pin'}),
            PR=SimpleNamespace(reuse=lambda *a: self.producer),
            with_prepared_inputs=lambda action: action(self.old_producer, 'source inputs'))
        def action(producer, inputs, g1):
            self.assertEqual((producer, inputs), (self.producer, 'source inputs'))
            self.assertEqual(self.RI.INVENTORY_PATH, 'reference')
            result = B.official_resolutions(g1, producer)
            self.assertEqual(result, {'arm': {('changed event', 9): 13}})
            self.assertEqual(B.g1_identity(g1)[REUSE.REPORT_PIN], 'input report')
            return result
        legs = {'arm': {'kept event': {'unmatched_gold': [7], 'unmatched_produced': [11]},
                        'changed event': {'unmatched_gold': [9], 'unmatched_produced': [13]}}}
        original_refuse, original_lifecycle, original_ref = B.refuse, B._lifecycle, self.RI.INVENTORY_PATH
        try:
            with ExitStack() as stack:
                for obj, name, value in (
                    (G, '_sha_file', lambda path: self.hashes[str(path)]),
                    (G, '_approved_bound', lambda: 'approved Bound'),
                    (G, 'live_key', lambda: ({}, {'key': 'approved'})),
                    (G, '_claimed', lambda run: self.claimed),
                    (G, 'inventory', lambda p: (legs, {}, {}, {}, {}, [])),
                    (REUSE.C, 'run_digest', lambda run: ('old tree', 5) if run == 'old run' else ('new tree', 3)),
                    (self.SELECT, 'derive', lambda *a: self.selection),
                    (REUSE.CURRENT, 'current_key', key_scope),
                    (REUSE.INPUT, 'approved_inputs', input_scope),
                    (B, 'refuse', native), (B, '_lifecycle', P.lifecycle)):
                    stack.enter_context(patch.object(obj, name, value))
                return REUSE.evaluate(E, 'report', self.g1, callback or action)
        finally:
            self.assertIs(B.refuse, original_refuse)
            self.assertIs(B._lifecycle, original_lifecycle)
            self.assertEqual(self.RI.INVENTORY_PATH, original_ref)
            self.assertEqual(self.phase, 'old')

    def test_real_resolution_consumer_and_partial_owner_receive_both_proven_contexts(self):
        self.execute()
        self.assertEqual([(phase, run) for phase, _, run, _ in self.calls],
                         [('old', 'old run'), ('new', 'new run')])

    def test_every_reuse_pin_is_required_before_any_source_work(self):
        for name in (REUSE.CODE_PIN, REUSE.SELECTION_PIN, REUSE.REPORT_PIN):
            with self.subTest(name=name):
                old = self.g1['pins'].pop(name)
                with self.assertRaisesRegex(ValueError, 'unapproved'):
                    self.execute()
                self.g1['pins'][name] = old
                self.assertEqual(self.calls, [])

    def test_native_problem_reaches_the_public_consumer_without_becoming_credit(self):
        self.problems.append('wrong native identity')
        with self.assertRaisesRegex(ValueError, 'native evidence'):
            self.execute()

    def test_scopes_restore_after_consumer_exception(self):
        def fail(*args):
            raise RuntimeError('test consumer exception')
        with self.assertRaisesRegex(RuntimeError, 'test consumer exception'):
            self.execute(fail)

    def test_another_current_candidate_never_enters_source_context(self):
        self.g1['candidate_dir'] = 'another candidate'
        with self.assertRaisesRegex(ValueError, 'another current candidate'):
            self.execute()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
