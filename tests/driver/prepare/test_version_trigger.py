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



from tests.driver.prepare.convert.context import test_version_qualification as vq  # the producer tests' real saved-arm fixture (a module, so its tests are not collected twice)
FID = vq.FID
GOOD = {'status': 'done', 'generate_exit': 0, 'reconstruct_exit': 0, 'verify_exit': 0, 'states': {}, 'source_reading': {'reconstruct_exit': 0, 'verify_exit': 0}}
ROW_OK = dict(GOOD, outcome='verified_saved_output', reasons=[], native_status='OK', native_error=None, generate_observed={'wall_seconds': 22}, attempt_bytes=200)
ROW_PARTIAL = dict(GOOD, outcome='incomplete', reasons=['native status PARTIAL'], native_status='PARTIAL', native_error='diagnostic', generate_observed={'wall_seconds': 30}, attempt_bytes=300)
HELD = "held before WITHOUT: the NORMAL/explored evidence already fails the producer's own checks (no WITHOUT can pass it); WITHOUT and release not run"


def edit(p, fn): d = json.loads(Path(p).read_bytes()); fn(d); Path(p).write_text(json.dumps(d))


class ChildBoundaryAndRelease(unittest.TestCase):  # job.qualify_first with controlled child/observed seams (Root's reproduction method): no subprocess. Every arm's saved
    # products are the producer tests' real saved-arm fixture (vq.arm) and the parent plan is real and pinned, so the ACTUAL qualify_arms/qualify_version decide; no validation is mocked
    def setUp(self):
        self.t = Path(tempfile.mkdtemp()); self.store = self.t / 'store'; self.store.mkdir(); a = self.t / 'out' / 'attempt_0'
        self.fx = {k: vq.arm(self.t / 'fx', k, k) / 'attempt_0' for k in ('normal', 'explored', 'without')}; shutil.copytree(self.fx.pop('normal'), a)  # NORMAL: this row's held attempt
        self.plan = {'script_qualifications': str(self.store), 'source_commands': [{'file_id': FID}], 'runtime_manifest': {'sha256': 'a' * 64}}
        self.row = dict(GOOD, ordinal=0, file_id=FID, attempt=str(a), outcome='incomplete', reasons=['native status PARTIAL'], native_status='PARTIAL', native_error='held initial error',
                        generate_observed={'wall_seconds': 7}, attempt_bytes=100, source_reading={'native_status': 'OK', 'reconstruct_exit': 0, 'verify_exit': 0})
        self.record = {'rows': [self.row]}; self.result = self.t / 'out' / 'RESULT.json'; self.ran = []; self.spec = {}; self.after = {}
        self.saved = (job.child, job.observed)
        def child(argv, logs, name, cwd, env):  # one arm child: its own saved products and its RESULT naming its real plan file and pin
            out = Path(argv[7]); arm = out.name; self.ran.append(arm); code, rows = self.spec.get(arm, (0, None)); out.mkdir(parents=True)
            if arm in self.fx and self.fx[arm].exists(): shutil.copytree(self.fx[arm], out / 'attempt_0')
            if rows == 'malformed': (out / 'RESULT.json').write_text('{not json')
            elif rows != 'missing': (out / 'RESULT.json').write_text(json.dumps({'plan': argv[5], 'plan_sha256': argv[6], 'rows': [dict(r, attempt=str(out / 'attempt_0')) for r in (rows if isinstance(rows, list) else [dict(rows or (ROW_OK if code == 0 else ROW_PARTIAL), ordinal=0, file_id=FID)])]}))
            if arm in self.after: self.after[arm](out)
            return code
        job.child, job.observed = child, (lambda logs, name: {'wall_seconds': 1})
    def tearDown(self): job.child, job.observed = self.saved; shutil.rmtree(self.t)
    def go(self):
        body = json.dumps(self.plan).encode(); pp = self.t / 'PLAN.json'; pp.write_bytes(body)
        job.qualify_first(json.loads(body), pp, hashlib.sha256(body).hexdigest(), self.t / 'out', self.record, self.result, self.row, 0, 'document.py', 900, str(self.t)); return self.row
    def again(self): self.tearDown(); self.setUp()
    def kept_claim_only(self): self.assertEqual(sorted(p.name for p in self.store.iterdir()), [H + '.claim'])

    def test_the_ordinary_positive_runs_every_arm_and_binds_the_release_whole(self):  # explored PARTIAL exit 1 is the expected diagnostic outcome
        self.spec['explored'] = (1, None); r = self.go(); self.assertEqual(self.ran, ['explored', 'without', 'release'])
        self.assertEqual({k: r[k] for k in ('outcome', 'native_status', 'native_error', 'generate_observed', 'attempt_bytes', 'reasons')},
                         {'outcome': 'verified_saved_output', 'native_status': 'OK', 'native_error': None, 'generate_observed': {'wall_seconds': 22}, 'attempt_bytes': 200, 'reasons': []})
        self.assertTrue(r['attempt'].endswith('release/attempt_0')); self.assertEqual((r['ordinal'], r['file_id']), (0, FID))
        h = r['held']; self.assertEqual({k: h[k] for k in ('outcome', 'native_status', 'native_error', 'generate_observed', 'attempt_bytes')},
                                        {'outcome': 'incomplete', 'native_status': 'PARTIAL', 'native_error': 'held initial error', 'generate_observed': {'wall_seconds': 7}, 'attempt_bytes': 100})
        self.assertTrue(h['attempt'].endswith('out/attempt_0')); q = r['qualification']; self.assertEqual((q['outcome'], q['reasons']), ('passed', []))  # the real producer's verdict
        rec = json.loads(Path(q['record']).read_bytes()); self.assertEqual((rec['outcome'], rec['comparison']['all_equal'], sorted(rec['states'])), ('passed', True, ['activated@5', 'initial']))
    def test_an_abnormal_or_failed_explored_child_stops_before_any_other_arm(self):
        for case in ((2, None), (-9, None), (1, dict(ROW_PARTIAL, outcome='generation_failed', generate_exit=2)), (1, 'missing'), (1, 'malformed'),
                     (1, [dict(ROW_PARTIAL, ordinal=0, file_id=FID), dict(ROW_PARTIAL, ordinal=1, file_id=FID)]), (1, dict(ROW_PARTIAL, status='composing')),
                     (1, dict(ROW_PARTIAL, technical_failures=['R.json: ValueError'])), (1, dict(ROW_PARTIAL, reconstruct_exit=1)), (0, ROW_PARTIAL)):
            with self.subTest(case=str(case)[:80]):
                self.again(); self.spec['explored'] = case; r = self.go()
                self.assertEqual(self.ran, ['explored']); self.assertTrue(r['qualification']['outcome'].startswith('held: explored'), r['qualification'])
                self.assertEqual((r['outcome'], r['native_error'], r['attempt_bytes']), ('incomplete', 'held initial error', 100)); self.assertNotIn('held', r); self.kept_claim_only()
    def test_a_failed_without_child_stops_before_the_comparison(self):
        self.spec['without'] = (1, dict(ROW_PARTIAL, outcome='generation_failed', generate_exit=1)); r = self.go()
        self.assertEqual(self.ran, ['explored', 'without']); self.assertTrue(r['qualification']['outcome'].startswith('held: without'), r['qualification']); self.kept_claim_only()
    def test_an_abnormal_release_is_never_bound(self):
        self.spec['release'] = (-9, None); r = self.go(); self.assertEqual(self.ran, ['explored', 'without', 'release'])
        self.assertEqual((r['outcome'], r['native_error'], r['attempt_bytes']), ('incomplete', 'held initial error', 100)); self.assertNotIn('held', r)
        self.assertTrue(r['qualification']['release_outcome'].startswith('held: release'), r['qualification'])
    def test_a_normal_row_blocked_by_an_independent_failure_spends_no_arm(self):
        for bad in ({'generate_exit': 1}, {'technical_failures': ['x']}, {'reconstruct_exit': 1}, {'verify_exit': 2}, {'reasons': ['native status PARTIAL', 'reconstruct exit 1']},
                    {'states': {'activated@1': {'reconstruct_exit': 1}}}, {'source_reading': {'verify_exit': 1}}):
            with self.subTest(bad=bad):
                self.again(); self.row.update(bad); self.go(); self.assertEqual(self.ran, []); self.assertNotIn('qualification', self.row)
                self.assertFalse((self.store / (H + '.claim')).exists())

    # root-qualification-failure-propagation-and-retained-timeout-20261029t004424909762z: a technical child failure must reach the PARENT row's own
    # structured outcome contract (clean_row: the fields every row reader checks), never read as ordinary incompleteness; verdicts and holds stay clean
    TECHNICAL = ((2, None), (124, None), (-9, None), (1, 'missing'), (1, 'malformed'), (1, []), (1, [dict(ROW_PARTIAL, ordinal=0, file_id=FID)] * 2),
                 (1, dict(ROW_PARTIAL, status='composing')), (1, dict(ROW_PARTIAL, outcome='generation_failed', generate_exit=124)), (1, dict(ROW_PARTIAL, outcome='identity_mismatch')),
                 (0, ROW_PARTIAL), (1, ROW_OK), (1, dict(ROW_PARTIAL, technical_failures=['R.json: ValueError'])), (1, dict(ROW_PARTIAL, reconstruct_exit=1)),
                 (1, dict(ROW_PARTIAL, states={'activated@1': {'reconstruct_exit': 0, 'verify_exit': 2}})), (1, dict(ROW_PARTIAL, source_reading={'reconstruct_exit': 0, 'verify_exit': 1})))
    def test_a_technical_child_failure_of_any_arm_reaches_the_parent_row(self):
        for arm in ('explored', 'without', 'release'):
            for case in self.TECHNICAL:
                with self.subTest(arm=arm, case=str(case)[:80]):
                    self.again(); self.spec[arm] = case; r = self.go()
                    self.assertEqual(self.ran[-1], arm); self.assertEqual((r['outcome'], r['native_error'], r['attempt_bytes']), ('incomplete', 'held initial error', 100))  # never bound
                    self.assertFalse(job.clean_row(r)); self.assertEqual(len(r['technical_failures']), 1); self.assertEqual(len(r['reasons']), 2)
    def test_a_qualification_that_cannot_be_compared_is_technical(self):  # the real producer on damaged WITHOUT evidence (its acquisition record gone; its route not an object)
        for case, fn in (('no acquisition record', lambda out: edit(out / 'attempt_0' / 'CONTEXT_ACQUISITION.json', lambda d: d.pop('record'))),
                         ('route a list', lambda out: (out / 'attempt_0' / 'ROUTE.json').write_text('[]'))):
            with self.subTest(case=case):
                self.again(); self.after['without'] = fn; r = self.go(); self.assertEqual(self.ran, ['explored', 'without']); self.assertFalse(job.clean_row(r))
                self.assertEqual((r['qualification']['outcome'], len(r['technical_failures'])), ('held: qualification not comparable', 1)); self.kept_claim_only()
    def test_verdicts_and_holds_stay_clean(self):  # the expected diagnostic exit 1, a real comparison hold, a lost claim and a reused record are no technical failure
        self.spec['explored'] = (1, None); r = self.go(); self.assertEqual(r['outcome'], 'verified_saved_output'); self.assertTrue(job.clean_row(r)); self.assertNotIn('technical_failures', r)
        self.again(); self.after['without'] = lambda out: shutil.rmtree(out / 'attempt_0' / 'states'); r = self.go()  # WITHOUT saved no state: the producer's own held record
        q = r['qualification']; self.assertEqual((r['outcome'], q['outcome'], self.ran), ('incomplete', 'held', ['explored', 'without'])); self.assertIn('state sets differ: NORMAL 1, WITHOUT 0', q['reasons'])
        self.assertEqual(json.loads(Path(q['record']).read_bytes())['outcome'], 'held'); self.assertTrue(job.clean_row(r)); self.assertNotIn('technical_failures', r)
        self.again(); (self.store / (H + '.claim')).write_text(''); r = self.go(); self.assertEqual(self.ran, []); self.assertTrue(job.clean_row(r)); self.assertNotIn('technical_failures', r)
        self.again(); (self.store / (H + '.json')).write_text('{}'); r = self.go(); self.assertEqual(self.ran, []); self.assertNotIn('qualification', r); self.assertTrue(job.clean_row(r))


# root-bound-native-early-stop-and-damage-checks-20261029t095934395308z: the decision before WITHOUT is the producer's own NORMAL/explored reading and
# binding (job.qualify_arms, shared with qualify_version) plus compare_views' text operand on every explored route; damaged own evidence is a technical STOP
UNPROVED = (('state', 'false', lambda d: d['diagnostic'].__setitem__('text_proved_before_gate', False)), ('state', 'missing', lambda d: d.pop('diagnostic')),  # missing: the saved8 shape
            ('state', 'absent key', lambda d: d['diagnostic'].pop('text_proved_before_gate')), ('state', 'string', lambda d: d['diagnostic'].__setitem__('text_proved_before_gate', 'true')),
            ('state', 'one', lambda d: d['diagnostic'].__setitem__('text_proved_before_gate', 1)), ('state', 'empty', lambda d: d.__setitem__('diagnostic', {})),
            ('state', 'null', lambda d: d.__setitem__('diagnostic', None)), ('initial', 'false', lambda d: d.__setitem__('text_proved', False)), ('initial', 'missing', lambda d: d.pop('text_proved')),
            ('initial', 'null', lambda d: d.__setitem__('text_proved', None)), ('initial', 'diagnostic false', lambda d: d.update(diagnostic={'text_proved_before_gate': False})))
PROVED = (('state', 'diagnostic true', lambda d: None), ('state', 'plain true', lambda d: (d.pop('diagnostic'), d.__setitem__('text_proved', True))),
          ('initial', 'diagnostic true', lambda d: d.update(diagnostic={'text_proved_before_gate': True}, text_proved=False)))
ROUTE_OF = {'state': 'states/activated@5/ROUTE.json', 'initial': 'ROUTE.json'}
LABEL = {'state': 'activated@5', 'initial': 'initial'}
FALSE_PROOF = lambda where: f'{LABEL[where]}: explored text proof not TRUE, so compare_views text_proved fails'
BINDING = (  # (arm whose saved evidence changes, file, change, the producer's own reason): each is a held reason that needs no WITHOUT
    ('explored', 'COMPLETE.json', lambda d: d.__setitem__('source_sha256', '6' * 64), 'the arms read different sources'),
    ('explored', 'CONTEXT_ACQUISITION.json', lambda d: d['record']['target']['inserted_script'].__setitem__('response_sha256', 'e' * 64), 'the explored NORMAL run bound another inserted script'),
    ('explored', 'CONTEXT_TRIALS.json', lambda d: d[0].__setitem__('refused', 'non-GET request'), 'explored NORMAL left 1 action(s) unobserved (refused): their states are unqualified'),
    ('normal', 'ROUTE.json', lambda d: d.__setitem__('error', 'context: 2 declared script action(s) not attempted (report-control exploration disabled)'), 'NORMAL is held by more than its proved inserted bytes'),
    ('explored', 'RESULT.json', lambda d: d.__setitem__('plan_sha256', 'e' * 64), 'explored: plan differs from its pin'))
DAMAGE = (  # (case, change to the explored arm's saved products, a false proof can sit elsewhere): unreadable or malformed own evidence
    ('route not JSON', lambda a: (a / 'ROUTE.json').write_text('{not json'), 'state'), ('route a list', lambda a: (a / 'ROUTE.json').write_text('[]'), 'state'),
    ('state without route', lambda a: (a / 'states/activated@5/ROUTE.json').unlink(), 'initial'), ('state entry a file', lambda a: (a / 'states/stray').write_text('x'), 'initial'),
    ('diagnostic a list', lambda a: edit(a / ROUTE_OF['state'], lambda d: d.__setitem__('diagnostic', ['x'])), 'initial'), ('no explored attempt', lambda a: shutil.rmtree(a), None),
    ('acquisition without record', lambda a: edit(a / 'CONTEXT_ACQUISITION.json', lambda d: d.pop('record')), 'state'), ('trials not JSON', lambda a: (a / 'CONTEXT_TRIALS.json').write_text('{'), 'state'),
    ('trials of strings', lambda a: (a / 'CONTEXT_TRIALS.json').write_text('["x"]'), 'state'), ('no COMPLETE', lambda a: (a / 'COMPLETE.json').unlink(), 'state'))
NORMAL_DAMAGE = (('no source reading route', lambda a: (a / 'source_reading/ROUTE.json').unlink()), ('no inserted href', lambda a: edit(a / 'CONTEXT_ACQUISITION.json', lambda d: d['record']['target']['inserted_script'].pop('href'))))


def mutate(attempt, where, fn): edit(Path(attempt) / ROUTE_OF[where], fn)


class TheProducerHoldsWithoutNeedingWithout(unittest.TestCase):  # the independent expectation: the real qualify_version, whatever WITHOUT says
    def arms(self):
        self.t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.t); store = self.t / 'store'; store.mkdir()
        return store, [vq.arm(self.t, k, k) for k in ('normal', 'explored', 'without')]
    def test_unproved_held_proved_passed(self):
        for where, case, fn in UNPROVED + PROVED:
            with self.subTest(where=where, case=case):
                store, (n, x, w) = self.arms(); mutate(x / 'attempt_0', where, fn); rec = job.qualify_version(n, x, w, store, vq.M, vq.FID)
                if (where, case, fn) in PROVED: self.assertEqual((rec['outcome'], rec['reasons']), ('passed', []))
                else: self.assertEqual((rec['outcome'], [r for r in rec['reasons'] if r.endswith(': text_proved')]), ('held', [f'state {LABEL[where]} differs: text_proved']))
    def test_an_unproved_explored_state_is_held_whatever_states_without_saves(self):  # a state WITHOUT lacks is never compared, but the state sets then differ
        for where, case, fn in UNPROVED:
            with self.subTest(where=where, case=case):
                store, (n, x, w) = self.arms(); mutate(x / 'attempt_0', where, fn); shutil.rmtree(w / 'attempt_0' / 'states')
                rec = job.qualify_version(n, x, w, store, vq.M, vq.FID); self.assertEqual(rec['outcome'], 'held'); self.assertIn('state sets differ: NORMAL 1, WITHOUT 0', rec['reasons'])
    def test_each_normal_or_explored_binding_reason_is_held_with_a_passing_without(self):
        for arm, rel, fn, reason in BINDING:
            with self.subTest(reason=reason):
                store, arms = self.arms(); out = dict(zip(('normal', 'explored', 'without'), arms))[arm]; edit(out / rel if rel == 'RESULT.json' else out / 'attempt_0' / rel, fn)
                rec = job.qualify_version(*arms, store, vq.M, vq.FID); self.assertEqual(rec['outcome'], 'held'); self.assertIn(reason, rec['reasons'])
    def test_an_unreadable_plan_is_a_failure_not_a_reason(self):  # qualify_arms reads each arm's plan without catching: a read error is never a held reason
        store, arms = self.arms(); edit(arms[1] / 'RESULT.json', lambda d: d.__setitem__('plan', str(self.t / 'absent_PLAN.json')))
        with self.assertRaises(FileNotFoundError): job.qualify_version(*arms, store, vq.M, vq.FID)
        self.assertEqual(list(store.iterdir()), [])


class EarlyDecisionOnTheProducersOwnEvidence(unittest.TestCase):  # ChildBoundaryAndRelease's seams and fixtures, not its tests
    setUp, tearDown, go, again, kept_claim_only = (ChildBoundaryAndRelease.setUp, ChildBoundaryAndRelease.tearDown, ChildBoundaryAndRelease.go, ChildBoundaryAndRelease.again,
                                                   ChildBoundaryAndRelease.kept_claim_only)
    def held_early(self, reasons):
        r = self.row; q = r['qualification']; self.assertEqual(self.ran, ['explored']); self.assertEqual((q['outcome'], q['reasons']), (HELD, reasons)); self.assertEqual(q['explored']['exit'], 0)
        self.assertEqual((r['outcome'], r['reasons'], r['native_error'], r['attempt_bytes']), ('incomplete', ['native status PARTIAL'], 'held initial error', 100)); self.assertNotIn('held', r)
        self.assertTrue(job.clean_row(r)); self.assertNotIn('technical_failures', r); self.kept_claim_only(); self.assertFalse((self.t / 'out' / 'qualification_0' / 'without_PLAN.json').exists())
    def stopped_technical(self):
        r = self.row; q = r['qualification']; self.assertEqual(self.ran, ['explored']); self.assertEqual(q['outcome'], 'held: qualification not comparable'); self.assertNotIn('reasons', q)
        self.assertFalse(job.clean_row(r)); self.assertEqual(len(r['technical_failures']), 1); self.assertTrue(r['technical_failures'][0].startswith('qualification not comparable: '))
        self.assertEqual((r['outcome'], r['native_error'], r['attempt_bytes']), ('incomplete', 'held initial error', 100)); self.assertNotIn('held', r); self.kept_claim_only()

    def test_a_known_unproved_explored_route_is_held_before_without(self):
        for where, case, fn in UNPROVED:
            with self.subTest(where=where, case=case): self.again(); mutate(self.fx['explored'], where, fn); self.go(); self.held_early([FALSE_PROOF(where)])
    def test_every_proved_form_runs_every_arm_and_is_released_by_the_real_producer(self):
        for where, case, fn in PROVED:
            with self.subTest(where=where, case=case):
                self.again(); mutate(self.fx['explored'], where, fn); r = self.go(); self.assertEqual(self.ran, ['explored', 'without', 'release'])
                self.assertEqual((r['outcome'], r['qualification']['outcome']), ('verified_saved_output', 'passed'))
    def test_a_binding_failure_is_held_with_the_producers_own_reason_never_as_clean_proof(self):
        for arm, rel, fn, reason in BINDING:
            for also in (None, 'initial', 'state'):
                with self.subTest(reason=reason, also_false=also):
                    self.again()
                    if also: mutate(self.fx['explored'], also, UNPROVED[0][2] if also == 'state' else UNPROVED[7][2])
                    if rel == 'RESULT.json': self.after['explored'] = lambda out: edit(out / rel, fn)
                    else: edit((self.fx['explored'] if arm == 'explored' else Path(self.row['attempt'])) / rel, fn)
                    self.go(); self.held_early([reason] + ([FALSE_PROOF(also)] if also else []))
    def test_damaged_explored_evidence_stops_technically_before_without_even_beside_a_false_proof(self):
        for case, fn, other in DAMAGE:
            for also in (False, True) if other else (False,):
                with self.subTest(case=case, also_false=also):
                    self.again()
                    if also: mutate(self.fx['explored'], other, UNPROVED[0][2] if other == 'state' else UNPROVED[7][2])
                    fn(self.fx['explored']); self.go(); self.stopped_technical()
    def test_damaged_normal_evidence_stops_technically_before_without(self):
        for case, fn in NORMAL_DAMAGE:
            for also in (False, True):
                with self.subTest(case=case, also_false=also):
                    self.again()
                    if also: mutate(self.fx['explored'], 'state', UNPROVED[0][2])
                    fn(Path(self.row['attempt'])); self.go(); self.stopped_technical()
    def test_an_unreadable_explored_plan_stops_technically_and_a_different_plan_is_held(self):
        self.after['explored'] = lambda out: edit(out / 'RESULT.json', lambda d: d.__setitem__('plan', str(out / 'absent_PLAN.json'))); self.go(); self.stopped_technical()
        def other(out):  # a pinned plan whose common settings differ from NORMAL's
            pp = Path(json.loads((out / 'RESULT.json').read_bytes())['plan']); edit(pp, lambda d: d.__setitem__('context_campaign', {'campaign': '/other'}))
            edit(out / 'RESULT.json', lambda r: r.__setitem__('plan_sha256', hashlib.sha256(pp.read_bytes()).hexdigest()))
        self.again(); self.after['explored'] = other; self.go(); self.held_early(['the arms ran different plans'])
    def test_without_side_damage_after_a_clean_early_decision_stays_technical(self):  # a WITHOUT route that is not an object: the shared failure set, never a crash
        self.after['without'] = lambda out: (out / 'attempt_0' / 'ROUTE.json').write_text('[]'); r = self.go(); self.assertEqual(self.ran, ['explored', 'without'])
        self.assertEqual((r['qualification']['outcome'], len(r['technical_failures'])), ('held: qualification not comparable', 1)); self.kept_claim_only()


if __name__ == '__main__':
    unittest.main()
