"""job.qualify_first's guards at the native row-result boundary (root-native-automatic-trigger-closeout-20261028t211651877057z): it starts NO child job
unless the row is held only by its own proved inserted version, no record exists, the plan is an ordinary one with a store, and this caller wins the one
exclusive claim. Pure: every case below returns before any child job (the end-to-end path is the native fixture test)."""
import hashlib, json, shutil, tempfile, unittest
from pathlib import Path
from driver.prepare import job

H = 'f' * 64


class TriggerGuards(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp()); self.store = self.t / 'store'; self.store.mkdir(); a = self.t / 'out' / 'attempt_0'; a.mkdir(parents=True)
        (a / 'ROUTE.json').write_text(json.dumps({'facts': {'optional_controls': {'other_objections': 0, 'inserted_version_objections': 21}}}))
        (a / 'CONTEXT_ACQUISITION.json').write_text(json.dumps({'record': {'target': {'inserted_script': {'href': 'https://www.sec.gov/b/x', 'response_sha256': H}}}}))
        self.row = {'ordinal': 0, 'file_id': 'f/R1.htm', 'attempt': str(a), 'outcome': 'incomplete', 'reasons': ['native status PARTIAL'],
                    'status': 'done', 'generate_exit': 0, 'reconstruct_exit': 0, 'verify_exit': 0}  # an otherwise clean held row: each guard below is the only reason it stops
        self.record = {'rows': [self.row]}; self.result = self.t / 'out' / 'RESULT.json'
    def tearDown(self): shutil.rmtree(self.t)
    def go(self, **plan):
        job.qualify_first(dict({'script_qualifications': str(self.store), 'source_commands': [{'file_id': 'f/R1.htm'}], 'runtime_manifest': {'sha256': 'a' * 64}}, **plan),
                          self.t / 'PLAN.json', 'p' * 64, self.t / 'out', self.record, self.result, self.row, 0, 'document.py', 900, str(self.t))
        return self.row
    def untouched(self): self.assertNotIn('qualification', self.row); self.assertFalse((self.t / 'out' / 'qualification_0').exists())

    def test_no_store_starts_nothing(self): self.go(script_qualifications=None); self.untouched()
    def test_a_diagnostic_or_withhold_plan_never_qualifies(self):
        self.go(qualification_diagnostic=True); self.untouched(); self.go(qualification_withhold=True); self.untouched()
    def test_a_row_held_by_anything_else_starts_nothing(self):
        p = Path(self.row['attempt']) / 'ROUTE.json'; p.write_text(json.dumps({'facts': {'optional_controls': {'other_objections': 1, 'inserted_version_objections': 21}}})); self.go(); self.untouched()
    def test_no_proved_inserted_script_starts_nothing(self):
        (Path(self.row['attempt']) / 'CONTEXT_ACQUISITION.json').write_text(json.dumps({'record': {'target': {}}})); self.go(); self.untouched()
    def test_an_existing_record_is_reused_never_requalified(self):
        (self.store / (H + '.json')).write_text('{}'); self.go(); self.untouched()
    def test_a_lost_claim_holds_without_any_child_job(self):  # another job (or an earlier attempt) holds this version's one claim
        (self.store / (H + '.claim')).write_text(''); r = self.go()
        self.assertEqual(r['qualification'], {'script_sha256': H, 'outcome': 'held: this version is claimed by another qualification'}); self.assertFalse((self.t / 'out' / 'qualification_0').exists())
        self.assertEqual((r['outcome'], r['attempt']), ('incomplete', self.row['attempt']))



GOOD = {'status': 'done', 'generate_exit': 0, 'reconstruct_exit': 0, 'verify_exit': 0, 'states': {}, 'source_reading': {'reconstruct_exit': 0, 'verify_exit': 0}}
ROW_OK = dict(GOOD, outcome='verified_saved_output', reasons=[], native_status='OK', native_error=None, generate_observed={'wall_seconds': 22}, attempt_bytes=200)
ROW_PARTIAL = dict(GOOD, outcome='incomplete', reasons=['native status PARTIAL'], native_status='PARTIAL', native_error='diagnostic', generate_observed={'wall_seconds': 30}, attempt_bytes=300)


class ChildBoundaryAndRelease(unittest.TestCase):  # job.qualify_first with controlled child/observed/qualify_version seams (Root's reproduction method): no subprocess
    def setUp(self):
        self.t = Path(tempfile.mkdtemp()); self.store = self.t / 'store'; self.store.mkdir(); a = self.t / 'out' / 'attempt_0'; a.mkdir(parents=True)
        (a / 'ROUTE.json').write_text(json.dumps({'facts': {'optional_controls': {'other_objections': 0, 'inserted_version_objections': 21}}}))
        (a / 'CONTEXT_ACQUISITION.json').write_text(json.dumps({'record': {'target': {'inserted_script': {'href': 'https://www.sec.gov/b/x', 'response_sha256': H}}}}))
        self.row = dict(GOOD, ordinal=0, file_id='f/R1.htm', attempt=str(a), outcome='incomplete', reasons=['native status PARTIAL'], native_status='PARTIAL', native_error='held initial error',
                        generate_observed={'wall_seconds': 7}, attempt_bytes=100)
        self.record = {'rows': [self.row]}; self.result = self.t / 'out' / 'RESULT.json'; self.ran = []; self.spec = {}
        self.saved = (job.child, job.observed, job.qualify_version)
        def child(argv, logs, name, cwd, env):
            out = Path(argv[7]); arm = out.name; self.ran.append(arm); code, rows = self.spec.get(arm, (0, None)); out.mkdir(parents=True)
            if rows == 'malformed': (out / 'RESULT.json').write_text('{not json')
            elif rows != 'missing': (out / 'RESULT.json').write_text(json.dumps({'rows': [dict(r, attempt=str(out / 'attempt_0')) for r in (rows if isinstance(rows, list) else [dict(rows or (ROW_OK if code == 0 else ROW_PARTIAL), ordinal=0, file_id='f/R1.htm')])]}))
            return code
        def qualify(normal, explored, without, store, manifest, file_id):
            (Path(store) / (H + '.json')).write_text('{}'); return {'outcome': 'passed', 'reasons': []}
        job.child, job.observed, job.qualify_version = child, (lambda logs, name: {'wall_seconds': 1}), qualify
    def tearDown(self): job.child, job.observed, job.qualify_version = self.saved; shutil.rmtree(self.t)
    def go(self):
        job.qualify_first({'script_qualifications': str(self.store), 'source_commands': [{'file_id': 'f/R1.htm'}], 'runtime_manifest': {'sha256': 'a' * 64}},
                          self.t / 'PLAN.json', 'p' * 64, self.t / 'out', self.record, self.result, self.row, 0, 'document.py', 900, str(self.t)); return self.row

    def test_the_ordinary_positive_runs_every_arm_and_binds_the_release_whole(self):  # explored PARTIAL exit 1 is the expected diagnostic outcome
        r = self.go(); self.assertEqual(self.ran, ['explored', 'without', 'release'])
        self.assertEqual({k: r[k] for k in ('outcome', 'native_status', 'native_error', 'generate_observed', 'attempt_bytes', 'reasons')},
                         {'outcome': 'verified_saved_output', 'native_status': 'OK', 'native_error': None, 'generate_observed': {'wall_seconds': 22}, 'attempt_bytes': 200, 'reasons': []})
        self.assertTrue(r['attempt'].endswith('release/attempt_0')); self.assertEqual((r['ordinal'], r['file_id']), (0, 'f/R1.htm'))
        h = r['held']; self.assertEqual({k: h[k] for k in ('outcome', 'native_status', 'native_error', 'generate_observed', 'attempt_bytes')},
                                        {'outcome': 'incomplete', 'native_status': 'PARTIAL', 'native_error': 'held initial error', 'generate_observed': {'wall_seconds': 7}, 'attempt_bytes': 100})
        self.assertTrue(h['attempt'].endswith('out/attempt_0')); self.assertEqual(r['qualification']['outcome'], 'passed')
    def test_an_abnormal_or_failed_explored_child_stops_before_any_other_arm(self):
        for case in ((2, None), (-9, None), (1, dict(ROW_PARTIAL, outcome='generation_failed', generate_exit=2)), (1, 'missing'), (1, 'malformed'),
                     (1, [dict(ROW_PARTIAL, ordinal=0, file_id='f/R1.htm'), dict(ROW_PARTIAL, ordinal=1, file_id='f/R1.htm')]), (1, dict(ROW_PARTIAL, status='composing')),
                     (1, dict(ROW_PARTIAL, technical_failures=['R.json: ValueError'])), (1, dict(ROW_PARTIAL, reconstruct_exit=1)), (0, ROW_PARTIAL)):
            with self.subTest(case=str(case)[:80]):
                self.tearDown(); self.setUp(); self.spec['explored'] = case; r = self.go()
                self.assertEqual(self.ran, ['explored']); self.assertTrue(r['qualification']['outcome'].startswith('held: explored'), r['qualification'])
                self.assertEqual((r['outcome'], r['native_error'], r['attempt_bytes']), ('incomplete', 'held initial error', 100)); self.assertNotIn('held', r)
    def test_a_failed_without_child_stops_before_the_comparison(self):
        self.spec['without'] = (1, dict(ROW_PARTIAL, outcome='generation_failed', generate_exit=1)); r = self.go()
        self.assertEqual(self.ran, ['explored', 'without']); self.assertTrue(r['qualification']['outcome'].startswith('held: without'), r['qualification']); self.assertFalse((self.store / (H + '.json')).exists())
    def test_an_abnormal_release_is_never_bound(self):
        self.spec['release'] = (-9, None); r = self.go(); self.assertEqual(self.ran, ['explored', 'without', 'release'])
        self.assertEqual((r['outcome'], r['native_error'], r['attempt_bytes']), ('incomplete', 'held initial error', 100)); self.assertNotIn('held', r)
        self.assertTrue(r['qualification']['release_outcome'].startswith('held: release'), r['qualification'])
    def test_a_normal_row_blocked_by_an_independent_failure_spends_no_arm(self):
        for bad in ({'generate_exit': 1}, {'technical_failures': ['x']}, {'reconstruct_exit': 1}, {'verify_exit': 2}, {'reasons': ['native status PARTIAL', 'reconstruct exit 1']},
                    {'states': {'activated@1': {'reconstruct_exit': 1}}}, {'source_reading': {'verify_exit': 1}}):
            with self.subTest(bad=bad):
                self.tearDown(); self.setUp(); self.row.update(bad); self.go(); self.assertEqual(self.ran, []); self.assertNotIn('qualification', self.row)
                self.assertFalse((self.store / (H + '.claim')).exists())


if __name__ == '__main__':
    unittest.main()
