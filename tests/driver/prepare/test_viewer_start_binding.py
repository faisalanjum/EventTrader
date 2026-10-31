"""The child plan must name its own normal run's original, pinned observation."""
import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from driver.prepare import job
from .convert.context import test_version_qualification as vq


class ViewerStartBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.n, self.x = (vq.arm(self.root, k, k) for k in ('normal', 'explored'))
        self.a = self.n / 'attempt_0'
        self.start = {'source_sha256': vq.SRC, 'parent_url': 'https://viewer.invalid/', 'target_url': 'https://viewer.invalid/report',
                      'parent_sha256': 'b' * 64, 'selection': {'path': [1, 0], 'tags': 'body>a', 'outer_html_sha256': 'c' * 64},
                      'received': [], 'refused_get': [], 'controls': [{'native_node': {'path': [1, 1], 'tags': 'body>a', 'outer_html_sha256': 'd' * 64}, 'closed': True}]}
        native = {'document_sha256': 'e' * 64}
        self.records = [{'state': 'initial', 'marked': False, 'viewer_start': self.start, 'viewer_before': self.start, 'native': native,
                         'attempts': [{'attempt': 1, 'outcome': 'used: the state reference', 'native': native}]}]
        self.bind()
    def tearDown(self): self.tmp.cleanup()
    def bind(self):
        renders = self.a / 'CONTEXT_RENDERS.json'; renders.write_text(json.dumps(self.records))
        complete = self.a / 'COMPLETE.json'; data = json.loads(complete.read_bytes()); data['context_renders_sha256'] = hashlib.sha256(renders.read_bytes()).hexdigest(); complete.write_text(json.dumps(data))
        self.ref = {'path': str(complete), 'sha256': hashlib.sha256(complete.read_bytes()).hexdigest()}
        self.child(self.ref)
    def child(self, value):
        p = self.root / 'explored_PLAN.json'; plan = json.loads(p.read_bytes())
        if value is None: plan.pop('context_viewer_start', None)
        else: plan['context_viewer_start'] = value
        p.write_text(json.dumps(plan)); result = self.x / 'RESULT.json'; r = json.loads(result.read_bytes()); r['plan_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest(); result.write_text(json.dumps(r))
    def compare(self): return job.qualify_arms((('normal', self.n), ('explored', self.x)), vq.FID, {})
    def test_bound_original_is_shared_without_relaxing_common_plan(self):
        self.assertEqual(self.compare()['why'], [])
    def test_missing_or_foreign_child_reference_is_held(self):
        for value in (None, dict(self.ref, path=str(self.x / 'attempt_0/COMPLETE.json')), dict(self.ref, sha256='0' * 64)):
            with self.subTest(value=value):
                self.child(value); self.assertIn('explored: viewer start is not the normal observation', self.compare()['why'])
    def test_changed_original_render_fails_as_damaged_evidence(self):
        (self.a / 'CONTEXT_RENDERS.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'viewer start.*render'): self.compare()
    def test_plan_cannot_be_attached_to_another_or_incomplete_observation(self):
        for field, value in (('marked', True), ('state', 'activated@5'), ('native', {'document_sha256': '0' * 64}), ('viewer_before', {}), ('refused', 'failed')):
            with self.subTest(field=field):
                old = copy.deepcopy(self.records); self.records[0][field] = value; self.bind()
                with self.assertRaisesRegex(ValueError, 'viewer start.*original'): self.compare()
                self.records = old
    def test_wrong_source_is_not_an_original_start_for_this_file(self):
        self.records[0]['viewer_start'] = dict(self.start, source_sha256='0' * 64); self.records[0]['viewer_before'] = self.records[0]['viewer_start']; self.bind()
        with self.assertRaisesRegex(ValueError, 'viewer start.*source'): self.compare()


if __name__ == '__main__': unittest.main()
