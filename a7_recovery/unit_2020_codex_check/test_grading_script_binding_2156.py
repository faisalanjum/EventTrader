"""The transport correction changes one proved location, never answer checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_grading_script_binding_2156 as T


class ScriptBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='test_a7_script_binding_')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.calls = []
        self.extra_problem = []
        self.paths = {}
        for name, value in [('state', {'status': 'completed'}),
                            ('invocation', {'scriptPath': 'published', 'args': [{'task': 'unfamiliar'}]}),
                            ('precall', {'frozen_script_path': 'published',
                                         'staged_script_path': 'executed',
                                         'frozen_script_sha256': 'script-pin',
                                         'staged_script_sha256': 'script-pin'}),
                            ('proof', {'reviewed_before_admission': True})]:
            path = self.base / (name + '.json')
            path.write_text(json.dumps(value), encoding='utf-8')
            self.paths[name] = str(path)
        self.owner = self.base / 'native_owner.py'
        self.owner.write_text('# independently pinned native owner\n', encoding='utf-8')
        self.record = dict(schema='A7-executed-script-binding-v1',
                           published_script_path='published', executed_script_path='executed',
                           script_sha256='script-pin', state_path=self.paths['state'],
                           invocation_path=self.paths['invocation'], precall_path=self.paths['precall'],
                           native_audit_sha256=G._sha_file(str(self.owner)),
                           evidence_files={p: G._sha_file(p) for p in self.paths.values()})
        self.report = self.base / 'binding.json'
        self.freeze()
        self.expect = dict(script_path='published', script_sha256='script-pin',
                           args=[{'task': 'unfamiliar'}], rows=[{'prompt': 'do the supported task'}],
                           captures=[{'text': 'saved answer'}], effort='other supported setting')

        def native(state, expected):
            self.calls.append((state, copy.deepcopy(expected)))
            if state != self.paths['state']:
                return ['unrelated run stays refused'], {}
            if expected['script_path'] != 'executed':
                return ['actual script differs from the publication'], {}
            return list(self.extra_problem), {'answer': 'UNCHANGED'}

        self.native = native
        self.audit = SimpleNamespace(__file__=str(self.owner), g1_state_audit=native)
        self.addCleanup(patch.stopall)
        patch.object(T, 'AUD', self.audit).start()
        # Every negative starts with an actual successful control.
        with T.scope(str(self.report), self.pins):
            self.assertEqual(self.audit.g1_state_audit(self.paths['state'], self.expect),
                             ([], {'answer': 'UNCHANGED'}))
        self.calls.clear()

    def freeze(self):
        self.report.write_text(json.dumps(self.record), encoding='utf-8')
        self.pins = {T.CODE_PIN: G._sha_file(T.__file__),
                     T.BINDING_PIN: G._sha_file(str(self.report))}

    def test_only_script_location_changes_and_original_refusal_is_preserved(self):
        self.assertEqual(self.native(self.paths['state'], self.expect)[0],
                         ['actual script differs from the publication'])
        before = copy.deepcopy(self.expect)
        with T.scope(str(self.report), self.pins):
            self.assertEqual(self.audit.g1_state_audit(self.paths['state'], self.expect),
                             ([], {'answer': 'UNCHANGED'}))
        self.assertEqual(self.expect, before)
        self.assertEqual(self.calls[-1][1], dict(before, script_path='executed'))
        self.assertIs(self.audit.g1_state_audit, self.native)

    def test_both_external_pins_are_required(self):
        for key in self.pins:
            pins = dict(self.pins, **{key: 'not approved'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                with T.scope(str(self.report), pins):
                    self.fail('unapproved input entered')
        self.assertEqual(self.calls, [])

    def test_every_evidence_file_and_native_owner_is_checked(self):
        for p in list(self.paths.values()) + [str(self.owner)]:
            path = Path(p)
            before = path.read_bytes()
            try:
                path.write_bytes(before + b' ')
                with self.subTest(path=path.name), self.assertRaises(ValueError):
                    with T.scope(str(self.report), self.pins):
                        self.fail('changed evidence entered')
            finally:
                path.write_bytes(before)
        self.assertEqual(self.calls, [])

    def test_published_path_script_hash_and_full_args_must_match(self):
        for field in ('script_path', 'script_sha256', 'args'):
            changed = dict(self.expect, **{field: 'changed'})
            with T.scope(str(self.report), self.pins):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.audit.g1_state_audit(self.paths['state'], changed)
        self.assertEqual(self.calls, [])

    def test_native_answer_or_identity_failure_is_never_removed(self):
        self.extra_problem = ['wrong prompt or response identity']
        with T.scope(str(self.report), self.pins):
            self.assertEqual(self.audit.g1_state_audit(self.paths['state'], self.expect),
                             (self.extra_problem, {'answer': 'UNCHANGED'}))

    def test_other_runs_are_unchanged(self):
        with T.scope(str(self.report), self.pins):
            self.assertEqual(self.audit.g1_state_audit('other run', self.expect),
                             (['unrelated run stays refused'], {}))
        self.assertEqual(self.calls[-1], ('other run', self.expect))

    def test_changed_evidence_during_scope_refuses_and_restores(self):
        with self.assertRaises(ValueError):
            with T.scope(str(self.report), self.pins):
                Path(self.paths['state']).write_text('changed', encoding='utf-8')
                self.audit.g1_state_audit(self.paths['state'], self.expect)
        self.assertEqual(self.calls, [])
        self.assertIs(self.audit.g1_state_audit, self.native)

    def test_exception_restores_the_original_auditor(self):
        with self.assertRaisesRegex(RuntimeError, 'caller stopped'):
            with T.scope(str(self.report), self.pins):
                raise RuntimeError('caller stopped')
        self.assertIs(self.audit.g1_state_audit, self.native)

    def test_pre_call_record_and_invocation_cannot_name_other_scripts(self):
        for field in ('published_script_path', 'executed_script_path', 'script_sha256', 'invocation_path'):
            original = copy.deepcopy(self.record)
            try:
                self.record[field] = 'different'
                self.freeze()
                with self.subTest(field=field), self.assertRaises(ValueError):
                    with T.scope(str(self.report), self.pins):
                        self.fail('inconsistent pre-call proof entered')
            finally:
                self.record = original
                self.freeze()


if __name__ == '__main__':
    unittest.main()
