# -*- coding: utf-8 -*-
"""Exercise the real selection rule. Codex SEQ 2152. No model call, no run.

The population case runs the REAL owner over the REAL pinned 2150 report. The
refusal cases build their own minimal fixtures rather than copying the 96-batch
tree, because each refusal is a property of the rule, not of that data - and a
fixture small enough to read is a better negative than a large one.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

import g1_reuse_inputs_2152 as INPUTS

A7 = Path(__file__).resolve().parents[1]
REPORT = str(A7 / 'unit_2020_codex_check/codex_keygrading2150_a/KEY_GRADING_INPUTS.json')
REPORT_SHA = 'd7571670fc3ae38a4dc732a7e377f23c385a0ee59aad3eb38d52151cd590e9f7'


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, raw):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, 'wb') as fh:
        fh.write(raw)
    return sha_bytes(raw)


class RealPopulation(unittest.TestCase):
    def setUp(self):
        self.got = INPUTS.derive(REPORT, REPORT_SHA)

    def test_population_splits_into_carried_and_changed(self):
        got = self.got
        self.assertEqual(len(got['current_candidate']['batch_rows']), 96)
        self.assertEqual(len(got['carry_batches']), 81)
        self.assertEqual(len(got['changed_batches']), 15)
        self.assertEqual(len(got['carry_batches']) + len(got['changed_batches']), 96)
        self.assertFalse(set(got['carry_batches']) & set(got['changed_batches']))

    def test_eligible_lanes_are_exactly_the_changed_batches_in_root_order(self):
        got = self.got
        rows = got['current_candidate']['launchers']['rows']
        order = [r['lane_id'] for r in rows]
        self.assertEqual(len(got['eligible_lanes']), 30)
        self.assertEqual(len(set(got['eligible_lanes'])), 30)
        # exactly the changed batches, and in the root's own order
        self.assertEqual({l.rsplit('/', 1)[0] for l in got['eligible_lanes']},
                         set(got['changed_batches']))
        self.assertEqual(got['eligible_lanes'],
                         [l for l in order if l in set(got['eligible_lanes'])])
        # and NO carried batch contributes a lane
        self.assertFalse({l.rsplit('/', 1)[0] for l in got['eligible_lanes']}
                         & set(got['carry_batches']))

    def test_gold_only_changes_carry_and_are_marked(self):
        got = self.got
        self.assertEqual(len(got['gold_moved_batches']), 6)
        for batch in got['gold_moved_batches']:
            self.assertIn(batch, got['carry_batches'])
            self.assertNotIn(batch, got['changed_batches'])

    def test_carry_mapping_is_one_to_one_onto_original_batches(self):
        got = self.got
        originals = list(got['carry_batches'].values())
        self.assertEqual(len(set(originals)), len(originals))
        known = {r['batch_id'] for r in got['original_candidate']['batch_rows']}
        self.assertTrue(set(originals) <= known)

    def test_model_and_input_settings_are_preserved_for_every_eligible_lane(self):
        got = self.got
        fields = ('model', 'effort', 'agentType', 'disallowedTools',
                  'max_output_tokens')
        new_rows = {r['lane_id']: r for r in got['current_candidate']['launchers']['rows']}
        old_rows = {r['lane_id']: r for r in got['original_candidate']['launchers']['rows']}
        for lane in got['eligible_lanes']:
            for field in fields:
                self.assertEqual(new_rows[lane][field], old_rows[lane][field], lane)
        self.assertEqual(got['expected_input']['record_type'], 'attachment')

    def test_wrong_report_pin_refuses(self):
        with self.assertRaisesRegex(ValueError, 'not the pinned'):
            INPUTS.derive(REPORT, '0' * 64)


class Fixture(unittest.TestCase):
    """A two-event pair built here, so each refusal is readable in isolation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='g1reuse-', dir=str(Path(__file__).parent))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def build(self, mutate=None):
        events = [('P1', 'S-A'), ('P1', 'S-B')]
        prompts = {'G1-000': b'prompt-alpha', 'G1-001': b'prompt-beta'}
        def candidate(directory, prompt_bytes):
            rows, bindings, lanes = [], [], []
            for n, (leg, sid) in enumerate(events):
                batch = 'G1-%03d' % n
                rel = 'prompts/%s.prompt.txt' % batch
                digest = write(str(directory / rel), prompt_bytes[batch])
                rows.append({'batch_id': batch, 'items': 1,
                             'produced_idxs': [0], 'question_ids': ['Q%d' % n],
                             'prompt_path': rel, 'prompt_sha256': digest})
                bindings.append({'batch_id': batch, 'leg': leg, 'source_id': sid,
                                 'question_id': 'Q%d' % n})
                for letter in ('G1a', 'G1b'):
                    lanes.append({'lane_id': '%s/%s' % (batch, letter),
                                  'batch_id': batch, 'model': 'sonnet',
                                  'effort': 'high', 'agentType': 'lean-probe',
                                  'disallowedTools': ['Read'],
                                  'max_output_tokens': '128000'})
            return {'batch_rows': rows, 'question_bindings': bindings,
                    'launchers': {'lanes': ['G1a', 'G1b'], 'rows': lanes},
                    'questions': len(events)}
        def event_rows(prompt_bytes, gold):
            return [{'leg': leg, 'source_id': sid, 'batch_id': 'G1-%03d' % n,
                     'full_positions': [n],
                     'prompt': prompt_bytes['G1-%03d' % n].decode(),
                     'items': [{'question_id': 'Q%d' % n, '_gold': gold}]}
                    for n, (leg, sid) in enumerate(events)]
        new_dir, old_dir = self.root / 'new', self.root / 'old'
        state = {'new_prompts': dict(prompts), 'old_prompts': dict(prompts),
                 'new_gold': 'g', 'old_gold': 'g', 'tweak': None}
        if mutate:
            mutate(state)
        new = candidate(new_dir, state['new_prompts'])
        old = candidate(old_dir, state['old_prompts'])
        if state['tweak']:
            state['tweak'](new, new_dir)
        new_path = new_dir / INPUTS.CANDIDATE_NAME
        old_path = old_dir / INPUTS.CANDIDATE_NAME
        new_sha = write(str(new_path), json.dumps(new).encode())
        old_sha = write(str(old_path), json.dumps(old).encode())
        report = {'g1_candidate': str(new_path), 'g1_candidate_sha256': new_sha,
                  'original_g1': {'candidate_dir': str(old_dir),
                                  'pins': {'candidate_sha256': old_sha}},
                  'current_events': event_rows(state['new_prompts'], state['new_gold']),
                  'original_events': event_rows(state['old_prompts'], state['old_gold'])}
        path = self.root / 'REPORT.json'
        pin = write(str(path), json.dumps(report).encode())
        return str(path), pin

    def test_clean_fixture_carries_everything(self):
        got = INPUTS.derive(*self.build())
        self.assertEqual(len(got['carry_batches']), 2)
        self.assertEqual(got['changed_batches'], [])
        self.assertEqual(got['eligible_lanes'], [])
        self.assertEqual(got['gold_moved_batches'], [])

    def test_same_batch_id_with_a_different_prompt_is_changed_not_carried(self):
        def mutate(state):
            state['new_prompts']['G1-001'] = b'prompt-beta-CHANGED'
        got = INPUTS.derive(*self.build(mutate))
        self.assertEqual(got['changed_batches'], ['G1-001'])
        self.assertEqual(list(got['carry_batches']), ['G1-000'])
        self.assertEqual(got['eligible_lanes'], ['G1-001/G1a', 'G1-001/G1b'])

    def test_gold_only_difference_carries_and_is_marked(self):
        def mutate(state):
            state['new_gold'] = 'moved'
        got = INPUTS.derive(*self.build(mutate))
        self.assertEqual(got['changed_batches'], [])
        self.assertEqual(sorted(got['gold_moved_batches']), ['G1-000', 'G1-001'])

    def test_duplicate_event_binding_refuses(self):
        def mutate(state):
            def tweak(new, _dir):
                new['question_bindings'][1]['source_id'] = 'S-A'
            state['tweak'] = tweak
        with self.assertRaisesRegex(ValueError, 'two batches'):
            INPUTS.derive(*self.build(mutate))

    def test_lane_naming_an_unknown_batch_refuses(self):
        def mutate(state):
            def tweak(new, _dir):
                new['launchers']['rows'][0]['batch_id'] = 'G1-999'
            state['tweak'] = tweak
        with self.assertRaisesRegex(ValueError, 'names no batch'):
            INPUTS.derive(*self.build(mutate))

    def test_prompt_file_drift_refuses(self):
        def mutate(state):
            def tweak(_new, directory):
                write(str(directory / 'prompts/G1-000.prompt.txt'), b'tampered')
            state['tweak'] = tweak
        with self.assertRaisesRegex(ValueError, 'prompt for G1-000'):
            INPUTS.derive(*self.build(mutate))

    def test_report_prompt_that_is_not_the_candidate_prompt_refuses(self):
        path, pin = self.build()
        with io.open(path, encoding='utf-8') as fh:
            doc = json.load(fh)
        doc['current_events'][0]['prompt'] = 'something the candidate never serves'
        pin = write(path, json.dumps(doc).encode())
        with self.assertRaisesRegex(ValueError, 'not the candidate prompt'):
            INPUTS.derive(path, pin)


if __name__ == '__main__':
    unittest.main(verbosity=2)
