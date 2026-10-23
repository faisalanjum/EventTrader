"""The initial-only choice through the ACTUAL caller (Root FABLE_CORE_INITIAL_IMPLEMENT_20261023T1125). Real job.py, document.py, reconstruct and
browser on the public context fixture (convert/context/cases: its CHILD page, recorded parent and resources, written here as a pinned evidence
file). The job-level `context_explore: false` keeps the selected initial view, its raw reading, custody and typed source child, attempts no report
control and builds no state; the row stays incomplete with every declared scripted action unresolved. The same row with the default job gives the
same initial route units and the same source child. A non-boolean value is refused before any row.
Run with the qualified interpreter from this checkout. Environment: BROWSER_EXECUTABLE (default: the pinned headless shell path below)."""
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
EXE = os.environ.get('BROWSER_EXECUTABLE', '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell')
sha = lambda b: hashlib.sha256(b).hexdigest()
sys.path.insert(0, str(ROOT))
from tests.driver.prepare.convert.context import cases  # noqa: E402  (the fixtures' own facts)


def job(t, name, extra):
    d = t / name; d.mkdir(); (d / 'child.html').write_bytes(cases.CHILD); (d / 'plan.png').write_bytes(cases.PNG)
    ev = cases.evidence(); ev['observed'] = {u: dict(o, body=o['body'].hex()) for u, o in ev['observed'].items()}
    evb = json.dumps(ev).encode(); (d / 'EVIDENCE.json').write_bytes(evb)
    row = {'file_id': 'public-fixture/child.html', 'dispatch': 'html', 'directory': str(d), 'filename': 'child.html', 'source_sha256': sha(cases.CHILD), 'base': None, 'bundle': None,
           'members': {'child.html': {'sha256': sha(cases.CHILD), 'bytes': len(cases.CHILD)}, 'plan.png': {'sha256': sha(cases.PNG), 'bytes': len(cases.PNG)}},
           'context': {'evidence': str(d / 'EVIDENCE.json'), 'evidence_sha256': sha(evb)}}
    files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / 'driver').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    man = d / 'MANIFEST.json'; man.write_text(json.dumps({'files': files}))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw: b = pw.chromium.launch(executable_path=EXE); version = b.version; b.close()
    body = json.dumps(dict({'runtime_root': str(ROOT), 'runtime_manifest': {'path': str(man), 'sha256': sha(man.read_bytes())}, 'browser_executable': EXE,
                            'browser_executable_sha256': sha(Path(EXE).read_bytes()), 'browser_version': version, 'source_commands': [row]}, **extra)).encode()
    (d / 'PLAN.json').write_bytes(body); out = d / 'out'
    p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'driver/prepare/job.py'), str(d / 'PLAN.json'), sha(body), str(out)],
                       env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', str(t))}, stdin=subprocess.DEVNULL, capture_output=True, timeout=900)
    (d / 'job.stderr').write_bytes(p.stderr); return p.returncode, out, p.stderr.decode(errors='replace')


class InitialOnlyThroughTheCaller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = t = Path(tempfile.mkdtemp(prefix='initial_only_caller_'))
        cls.exit, cls.out, _ = job(t, 'initial_only', {'context_explore': False})
        cls.dexit, cls.dout, _ = job(t, 'default', {})
        cls.bad = job(t, 'bad_value', {'context_explore': 'false'})
        cls.row = json.loads((cls.out / 'RESULT.json').read_bytes())['rows'][0]; cls.drow = json.loads((cls.dout / 'RESULT.json').read_bytes())['rows'][0]

    def test_the_row_stays_incomplete_with_every_declared_action_unresolved(self):
        r = self.row; self.assertEqual((r['outcome'], r['native_status']), ('incomplete', 'PARTIAL'), r.get('reasons'))
        self.assertIn('%d declared script action(s) not attempted (report-control exploration disabled)' % len(cases.controls(cases.CHILD)), r['native_error'])
        self.assertIn(cases.BUTTON, r['native_error']); self.assertEqual(self.exit, 1)

    def test_no_report_control_is_attempted_and_no_state_is_built(self):
        trials = json.loads((self.out / 'attempt_0/CONTEXT_TRIALS.json').read_bytes())
        self.assertTrue(trials); self.assertTrue(all(t.get('skipped') for t in trials), [t for t in trials if not t.get('skipped')][:2])
        links = cases.sg.Visible(cases.CHILD).links  # fixture fact: two visible scripted links, one visible plain link, one hidden link
        self.assertEqual({t['controls'][0] for t in trials if t['skipped'].startswith('not attempted')}, {l['start'] for l in links if not l['hidden']})
        self.assertEqual({t['controls'][0] for t in trials if t['skipped'] == 'hidden in the initial reading'}, {l['start'] for l in links if l['hidden']})
        self.assertTrue(set(cases.controls(cases.CHILD)) <= {l['start'] for l in links if not l['hidden']})
        self.assertEqual(list((self.out / 'attempt_0/states').iterdir()), []); self.assertEqual(self.row.get('states') or {}, {})

    def test_the_initial_view_and_source_child_are_saved_with_custody(self):
        s = self.row.get('source_reading') or {}
        self.assertEqual((s.get('native_status'), s.get('reconstruct_exit'), s.get('verify_exit')), ('OK', 0, 0), s)
        comp = json.loads((self.out / 'attempt_0/COMPLETE.json').read_bytes())
        self.assertEqual(comp.get('source_reading_complete_sha256'), sha((self.out / 'attempt_0/source_reading/COMPLETE.json').read_bytes()))
        for f in ('attempt_0/RAW_READING.json', 'attempt_0/CONTEXT_RENDERS.json', 'attempt_0/CONTEXT_SELECTION.json', 'logs_0/R.json', 'logs_0/source_reading/R.json'):
            self.assertTrue((self.out / f).is_file(), f)
        self.assertEqual((self.row['reconstruct_exit'], self.row['verify_exit']), (0, 0))

    def test_same_initial_route_and_source_child_as_the_default_job(self):
        a, b = (json.loads((o / 'attempt_0/ROUTE.json').read_bytes()) for o in (self.out, self.dout))
        self.assertEqual(a['units'], b['units']); self.assertEqual(a['page_visibility'], b['page_visibility']); self.assertEqual(a['text_proved'], b['text_proved'])
        ca, cb = (json.loads((o / 'logs_0/source_reading/R.json').read_bytes()) for o in (self.out, self.dout))
        self.assertEqual(ca['sequence'], cb['sequence']); self.assertTrue(self.drow.get('states'))  # the default job still explores (its states exist)

    def test_a_non_boolean_choice_is_refused_before_any_row(self):
        code, out, err = self.bad
        self.assertNotEqual(code, 0); self.assertIn('context_explore must be true or false', err); self.assertFalse((out / 'RESULT.json').exists())


if __name__ == '__main__':
    unittest.main()
