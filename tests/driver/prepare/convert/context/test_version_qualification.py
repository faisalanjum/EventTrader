"""context.qualify_version (the producer) and context.qualified_version (the consumer) together, on synthetic saved job outputs with the real file
names and fields (owner single-version policy; root-automatic-version-path-completion-20261028t202337210252z). Pure: no browser, no job. The explored
NORMAL states carry the diagnostic representation the runtime gives them (Context.gate makes text_proved False; the native proof before the gate is
kept apart in route.diagnostic). The native positive on real contextual_routes output is in test_diagnostic_continuation."""
import copy, hashlib, json, shutil, tempfile, unittest
from pathlib import Path
from driver.prepare.convert import context

H, HREF, M, FID, SRC = 'f' * 64, 'https://www.sec.gov/Qp9qZ/x', 'a' * 64, '0000815097-23-000012/R2.htm', '5' * 64
ROUTE = {'units': [{'id': 'u0', 'kind': 'table', 'cells': [['Revenue', '500'], ['Net income', '200']]}], 'page_visibility': {'hidden': [], 'shown': [[0, 9]]},
         'source_ids': {'records': []}, 'source_relations': [], 'source_style': [], 'source_inline': [], 'source_symbols': [], 'source_facts': [],
         'generated_content': [], 'uncovered': [], 'text_proved': True, 'facts': {'screen': {'cells_measured': 4, 'seconds': 1.0}, 'visibility': {}, 'formatting': {}},
         'source_links': [{'tag': {'byte_start': 5}, 'script_action': {'event_attributes': ['onclick']}}]}
STATE_UNITS = ROUTE['units'] + [{'id': 'u1', 'kind': 'table', 'cells': [['Defined', 'term']]}]


def arm(root, name, kind, h=H, href=HREF):  # kind: 'normal' (production settings), 'explored' (diagnostic NORMAL), 'without' (comparison-only)
    out = root / name; a = out / 'attempt_0'; (a / 'source_reading').mkdir(parents=True)
    plan = {'runtime_root': '/r', 'runtime_manifest': {'path': '/r/M.json', 'sha256': M}, 'context_campaign': {'campaign': '/c', 'live': False}, 'context_explore': kind != 'normal',
            'source_commands': [{'file_id': FID, 'source_sha256': SRC}], **({'qualification_diagnostic': True} if kind == 'explored' else {'qualification_withhold': True} if kind == 'without' else {})}
    pp = root / (name + '_PLAN.json'); pp.write_text(json.dumps(plan))
    r = copy.deepcopy(ROUTE)
    if kind == 'normal':
        r['status'], r['error'] = 'PARTIAL', 'context: 1 declared script action(s) not attempted (report-control exploration disabled)'
        r['facts']['optional_controls'] = {'other_objections': 0, 'inserted_version_objections': 21}
        target, row = {'inserted_script': {'href': href, 'response_sha256': h}}, {'outcome': 'incomplete', 'reasons': ['native status PARTIAL']}
    else:
        r['status'], r['error'] = 'OK', None; r['source_links'][0]['activations'] = [{'state': 'activated@5', 'status': 'complete' if kind == 'without' else 'incomplete'}]
        s = dict(r, units=STATE_UNITS)
        if kind == 'explored':  # the runtime's own diagnostic representation (contextual_routes.one + Context.gate)
            s = dict(s, status='PARTIAL', error='context: render 0: diagnostic continuation (qualification only, never a native success)', text_proved=False,
                     diagnostic={'text_proved_before_gate': True, 'gate': ['render 0: diagnostic continuation (qualification only, never a native success): [...]']})
        (a / 'states' / 'activated@5').mkdir(parents=True); (a / 'states' / 'activated@5' / 'ROUTE.json').write_text(json.dumps(s))
        (a / 'CONTEXT_TRIALS.json').write_text(json.dumps([{'label': 'trial@5', 'controls': [5], 'refused': None}, {'label': None, 'controls': [9], 'skipped': 'hidden in the initial reading'}]))
        target = ({'comparison_exception': {'bound': True, 'response_sha256': h, 'address_sha256': hashlib.sha256(href.encode()).hexdigest()}} if kind == 'without'
                  else {'inserted_script': {'href': href, 'response_sha256': h}})
        row = {'outcome': 'verified_saved_output', 'reasons': []} if kind == 'without' else {'outcome': 'incomplete', 'reasons': ['native status PARTIAL']}
    (a / 'ROUTE.json').write_text(json.dumps(r)); (a / 'source_reading/ROUTE.json').write_text(json.dumps({'units': ROUTE['units']}))
    (a / 'COMPLETE.json').write_text(json.dumps({'file_id': FID, 'source_sha256': SRC, 'raw_reading_sha256': '7' * 64, 'native_status': r['status']}))
    (a / 'CONTEXT_ACQUISITION.json').write_text(json.dumps({'outcome': 'associated', 'record': {'target': target}}))
    (out / 'RESULT.json').write_text(json.dumps({'plan': str(pp), 'plan_sha256': hashlib.sha256(pp.read_bytes()).hexdigest(),
                                                 'rows': [dict(row, ordinal=0, file_id=FID, attempt=str(a), source_reading={'native_status': 'OK'})]}))
    return out


def make_record(root, store, h=H, href=HREF, manifest=M):  # a real producer record from three saved arms (also used by test_optional_controls)
    arms = [arm(root, f'{k}_{h[:8]}', k, h, href) for k in ('normal', 'explored', 'without')]
    return context.qualify_version(*arms, store, manifest, FID), arms


class VersionQualification(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()); self.store = self.root / 'store'; self.store.mkdir()
        self.n, self.x, self.w = (arm(self.root, k, k) for k in ('normal', 'explored', 'without'))
    def tearDown(self): shutil.rmtree(self.root)
    def edit(self, out, rel, fn):
        p = out / rel if rel == 'RESULT.json' else out / 'attempt_0' / rel; d = json.loads(p.read_bytes()); fn(d); p.write_text(json.dumps(d))
    def produce(self): return context.qualify_version(self.n, self.x, self.w, self.store, M, FID)
    def consumer(self, h=H, href=HREF, url=None, manifest=M): return context.qualified_version({'inserted_script': {'href': href, 'response_sha256': h}, 'qualifications': {'folder': str(self.store), 'runtime_manifest_sha256': manifest}}, h, url or href)
    def forge(self, roles=('without_result',), **over):  # a handcrafted record, every field the consumer reads valid, written without the producer
        f = str(self.w / 'RESULT.json'); ev = [{'role': r, 'path': f, 'sha256': hashlib.sha256(Path(f).read_bytes()).hexdigest()} for r in roles]
        r = dict({'schema': context.QUALIFY_SCHEMA, 'script_sha256': H, 'outcome': 'passed', 'reasons': [], 'runtime_manifest_sha256': M, 'file_id': FID, 'comparison': {'all_equal': True}, 'states': {'initial': {}}, 'evidence': ev}, **over)
        (self.store / (H + '.json')).write_text(json.dumps(r))

    # the producer's positive on the runtime's actual diagnostic representation, and its damage
    def test_equal_views_and_states_pass_and_the_consumer_accepts_the_record(self):
        rec = self.produce(); self.assertEqual((rec['outcome'], rec['reasons']), ('passed', [])); self.assertEqual(self.consumer(), (True, None))
        self.assertEqual(sorted(rec['states']), ['activated@5', 'initial']); self.assertTrue(all(all(f.values()) for f in rec['states'].values()))
    def test_a_diagnostic_state_whose_native_proof_failed_is_held(self):
        self.edit(self.x, 'states/activated@5/ROUTE.json', lambda d: d['diagnostic'].__setitem__('text_proved_before_gate', False)); self.assertIn('state activated@5 differs: text_proved', self.produce()['reasons'])
    def test_a_diagnostic_state_without_its_kept_native_proof_is_held(self):
        self.edit(self.x, 'states/activated@5/ROUTE.json', lambda d: d.pop('diagnostic')); self.assertIn('state activated@5 differs: text_proved', self.produce()['reasons'])
    def test_the_record_is_never_overwritten(self):
        self.produce()
        with self.assertRaises(FileExistsError): self.produce()
    def test_a_changed_number_in_the_normal_view_is_held(self):
        self.edit(self.n, 'ROUTE.json', lambda d: d['units'][0]['cells'][1].__setitem__(1, '210'))
        rec = self.produce(); self.assertEqual(rec['outcome'], 'held'); self.assertIn('initial views differ: units', rec['reasons']); self.assertFalse(self.consumer()[0])
    def test_lost_visibility_is_held(self):
        self.edit(self.n, 'ROUTE.json', lambda d: d['page_visibility']['hidden'].append([0, 9])); self.assertIn('initial views differ: page_visibility', self.produce()['reasons'])
    def test_changed_layout_is_held(self):
        self.edit(self.n, 'ROUTE.json', lambda d: d['facts']['screen'].__setitem__('cells_measured', 3)); self.assertIn('initial views differ: screen', self.produce()['reasons'])
    def test_a_changed_relationship_is_held(self):
        self.edit(self.n, 'ROUTE.json', lambda d: d['source_relations'].append({'from': 'u0', 'to': 'x'})); self.assertIn('initial views differ: source_relations', self.produce()['reasons'])
    def test_a_state_that_differs_under_the_executing_script_is_held(self):
        self.edit(self.x, 'states/activated@5/ROUTE.json', lambda d: d['units'][1]['cells'][0].__setitem__(1, 'changed')); self.assertIn('state activated@5 differs: units', self.produce()['reasons'])
    def test_a_state_missing_in_the_explored_normal_run_is_held(self):
        shutil.rmtree(self.x / 'attempt_0' / 'states' / 'activated@5'); self.assertIn('state sets differ: NORMAL 0, WITHOUT 1', self.produce()['reasons'])
    def test_a_refused_normal_action_leaves_its_state_unqualified(self):
        (self.x / 'attempt_0' / 'CONTEXT_TRIALS.json').write_text(json.dumps([{'label': 'trial@5', 'controls': [5], 'refused': 'non-GET request'}]))
        self.assertIn('explored NORMAL left 1 action(s) unobserved (refused): their states are unqualified', self.produce()['reasons'])
    def test_a_shared_omission_passes_only_through_withouts_own_native_verification(self):
        for out in (self.n, self.x, self.w): self.edit(out, 'ROUTE.json', lambda d: d['units'][0]['cells'].pop())
        self.edit(self.w, 'RESULT.json', lambda d: d['rows'][0].__setitem__('outcome', 'incomplete')); self.assertIn('WITHOUT not verified', self.produce()['reasons'])
    def test_normal_held_by_anything_else_is_held(self):
        self.edit(self.n, 'ROUTE.json', lambda d: d['facts']['optional_controls'].__setitem__('other_objections', 1)); self.assertIn('NORMAL is held by more than its proved inserted bytes', self.produce()['reasons'])
    def test_a_different_withheld_response_is_held(self):
        self.edit(self.w, 'CONTEXT_ACQUISITION.json', lambda d: d['record']['target']['comparison_exception'].__setitem__('response_sha256', 'e' * 64))
        self.assertIn('the arms did not bind the same inserted address and response', self.produce()['reasons'])
    def test_an_explored_run_bound_to_another_script_is_held(self):
        self.edit(self.x, 'CONTEXT_ACQUISITION.json', lambda d: d['record']['target']['inserted_script'].__setitem__('response_sha256', 'e' * 64)); self.assertIn('the explored NORMAL run bound another inserted script', self.produce()['reasons'])
    def test_no_proved_inserted_script_is_not_qualified(self):
        self.edit(self.n, 'CONTEXT_ACQUISITION.json', lambda d: d['record']['target'].pop('inserted_script'))
        with self.assertRaises(ValueError): self.produce()

    # input binding through RESULT / COMPLETE / plan
    def test_an_arm_with_no_row_for_the_file_writes_no_record(self):  # nothing comparable: no record, so the version stays held (its claim is never retried)
        self.edit(self.w, 'RESULT.json', lambda d: d['rows'][0].__setitem__('file_id', 'other/R9.htm'))
        with self.assertRaisesRegex(ValueError, 'without: not exactly one row for the file'): self.produce()
        self.assertEqual(list(self.store.iterdir()), [])
    def test_a_concurrent_claim_has_one_winner(self):  # two jobs meeting the same new version at once: exactly one runs the qualification
        import threading
        got, go = [], threading.Barrier(8)
        def one(): go.wait(); got.append(context.claim_version(self.store, H))
        ts = [threading.Thread(target=one) for _ in range(8)]; [x.start() for x in ts]; [x.join() for x in ts]; self.assertEqual(sorted(got), [False] * 7 + [True])
    def test_the_files_row_is_found_among_others(self):
        self.edit(self.w, 'RESULT.json', lambda d: d['rows'].insert(0, {'ordinal': 0, 'file_id': 'other/R9.htm', 'outcome': 'incomplete'})); self.assertEqual(self.produce()['outcome'], 'passed')
    def test_another_source_is_held(self):
        self.edit(self.x, 'COMPLETE.json', lambda d: d.__setitem__('source_sha256', '6' * 64)); self.assertIn('the arms read different sources', self.produce()['reasons'])
    def test_an_incompatible_plan_is_held(self):
        p = Path(json.loads((self.w / 'RESULT.json').read_bytes())['plan']); d = json.loads(p.read_bytes()); d['context_campaign']['campaign'] = '/other'; p.write_text(json.dumps(d))
        self.edit(self.w, 'RESULT.json', lambda r: r.__setitem__('plan_sha256', hashlib.sha256(p.read_bytes()).hexdigest())); self.assertIn('the arms ran different plans', self.produce()['reasons'])
    def test_a_plan_that_no_longer_matches_its_pin_is_held(self):
        p = Path(json.loads((self.w / 'RESULT.json').read_bytes())['plan']); p.write_text(p.read_text() + ' '); self.assertIn('without: plan differs from its pin', self.produce()['reasons'])

    # the consumer: only the producer's complete chain admits
    def test_evidence_changed_after_the_record_is_refused(self):
        self.produce(); self.edit(self.w, 'ROUTE.json', lambda d: d.__setitem__('text_proved', False)); self.assertEqual(self.consumer(), (False, 'record evidence changed after recording'))
    def test_every_operand_the_producer_read_is_bound(self):  # Root's reproduced defect: each decision operand changed after recording -> refused
        for rel, fn in (('explored/attempt_0/ROUTE.json', lambda d: d.__setitem__('text_proved', False)), ('explored/attempt_0/COMPLETE.json', lambda d: d.__setitem__('raw_reading_sha256', '8' * 64)),
                        ('without/attempt_0/source_reading/ROUTE.json', lambda d: d['units'].pop()), ('normal/attempt_0/source_reading/ROUTE.json', lambda d: d['units'].pop()),
                        ('normal/attempt_0/COMPLETE.json', lambda d: d.__setitem__('source_sha256', '9' * 64)), ('explored/attempt_0/states/activated@5/ROUTE.json', lambda d: d.pop('diagnostic'))):
            with self.subTest(rel=rel):
                st = Path(tempfile.mkdtemp()); n, x, w = (arm(st, k, k) for k in ('normal', 'explored', 'without')); store = st / 'store'; store.mkdir()
                self.assertEqual(context.qualify_version(n, x, w, store, M, FID)['outcome'], 'passed')
                ok = lambda: context.qualified_version({'inserted_script': {'href': HREF, 'response_sha256': H}, 'qualifications': {'folder': str(store), 'runtime_manifest_sha256': M}}, H, HREF)
                self.assertEqual(ok(), (True, None)); p = st / rel; d = json.loads(p.read_bytes()); fn(d); p.write_text(json.dumps(d))
                self.assertEqual(ok(), (False, 'record evidence changed after recording')); shutil.rmtree(st)
        st = Path(tempfile.mkdtemp()); n, x, w = (arm(st, k, k) for k in ('normal', 'explored', 'without')); store = st / 'store'; store.mkdir()  # a plan file
        context.qualify_version(n, x, w, store, M, FID); p = st / 'normal_PLAN.json'; p.write_text(p.read_text() + ' ')
        self.assertEqual(context.qualified_version({'inserted_script': {'href': HREF, 'response_sha256': H}, 'qualifications': {'folder': str(store), 'runtime_manifest_sha256': M}}, H, HREF), (False, 'record evidence changed after recording')); shutil.rmtree(st)
    def test_an_arm_of_another_runtime_is_held(self):  # same-runtime arms only: the manifest is part of the common plan
        p = Path(json.loads((self.w / 'RESULT.json').read_bytes())['plan']); d = json.loads(p.read_bytes()); d['runtime_manifest']['sha256'] = 'c' * 64; p.write_text(json.dumps(d))
        self.edit(self.w, 'RESULT.json', lambda r: r.__setitem__('plan_sha256', hashlib.sha256(p.read_bytes()).hexdigest())); self.assertIn('the arms ran different plans', self.produce()['reasons'])
    def test_an_empty_without_result_is_refused(self):
        (self.w / 'RESULT.json').write_text(json.dumps({'rows': []})); self.forge(roles=sorted(context.QUALIFY_ROLES))  # the whole chain present, but no row
        self.assertEqual(self.consumer(), (False, 'record evidence has no verified WITHOUT row for its file'))
    def test_a_handcrafted_record_without_the_producer_chain_is_refused(self):
        self.forge(); self.assertEqual(self.consumer(), (False, 'record lacks the producer evidence chain'))
    def test_one_exclusive_claim_per_version(self):  # taken before any expensive run; a second caller (this job or another) is refused
        self.assertTrue(context.claim_version(self.store, H)); self.assertFalse(context.claim_version(self.store, H)); self.assertTrue(context.claim_version(self.store, 'b' * 64))
    def test_a_stale_runtime_record_is_refused(self):
        self.produce(); self.assertEqual(self.consumer(manifest='d' * 64), (False, 'record made by another runtime'))
    def test_the_consumer_refuses_other_bytes_and_a_script_not_at_this_files_proved_address(self):
        self.produce(); self.assertFalse(self.consumer(h='b' * 64)[0]); self.assertFalse(self.consumer(url='https://www.sec.gov/other')[0])
    def test_the_same_bytes_proved_inserted_at_another_address_reuse_the_version(self):  # the key is the exact bytes; each file proves its own address
        self.produce(); self.assertEqual(self.consumer(href='https://www.sec.gov/Zz9/y'), (True, None))


if __name__ == '__main__':
    unittest.main()
