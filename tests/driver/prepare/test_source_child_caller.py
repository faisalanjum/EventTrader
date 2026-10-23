"""The typed source reading through the ACTUAL caller (Root ROOT_SOURCE_CHILD_CALLER_REVIEW_20261022T2140; OCR). driver/prepare/job.py must give the
attempt's source_reading/ child the SAME check as every other owned reading (reconstruct, verify, status, pictures) and show it in the returned row;
a child PARTIAL keeps the whole document incomplete. Real document.py, reconstruct and browser; three loose rows, written here from literal bytes:
an ordinary page (no hidden content, no child), a mixed page (one hidden word: a complete child, composed and verified), and an inline-XBRL hidden
fact (a child whose hidden run cannot be placed: PARTIAL). Expected values come from each row's own bytes.
Run with the qualified interpreter from this checkout: python -I -B tests/driver/prepare/test_source_child_caller.py
Environment: BROWSER_EXECUTABLE (default: the pinned headless shell path below)."""
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
EXE = os.environ.get('BROWSER_EXECUTABLE', '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell')
sha = lambda b: hashlib.sha256(b).hexdigest()
PAGES = {'ordinary': b'<html><body><p>Plain shown text.</p></body></html>',
         'mixed': b'<html><body><p>Revenue grew <span style="display:none">quietly</span> strongly.</p></body></html>',
         'hidden_fact': b'<html><body><div style="display:none"><ix:header><ix:hidden><ix:nonNumeric name="dei:X">Hidden fact</ix:nonNumeric></ix:hidden></ix:header></div><p>Body</p></body></html>'}


class SourceChildThroughTheCaller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=EXE); version = b.version; b.close()
        cls.t = t = Path(tempfile.mkdtemp(prefix='source_child_caller_')); rows = []
        for name, raw in PAGES.items():
            d = t / name; d.mkdir(); (d / 'page.htm').write_bytes(raw)
            rows.append({'file_id': name + '/page.htm', 'dispatch': 'html', 'directory': str(d), 'filename': 'page.htm', 'source_sha256': sha(raw), 'base': None, 'bundle': None,
                         'members': {'page.htm': {'sha256': sha(raw), 'bytes': len(raw)}}})
        files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / 'driver').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
        man = t / 'MANIFEST.json'; man.write_text(json.dumps({'files': files}))
        body = json.dumps({'runtime_root': str(ROOT), 'runtime_manifest': {'path': str(man), 'sha256': sha(man.read_bytes())}, 'browser_executable': EXE,
                           'browser_executable_sha256': sha(Path(EXE).read_bytes()), 'browser_version': version, 'source_commands': rows}).encode()
        plan = t / 'PLAN.json'; plan.write_bytes(body); cls.out = t / 'out'
        p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'driver/prepare/job.py'), str(plan), sha(body), str(cls.out)],
                           env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', str(t))}, stdin=subprocess.DEVNULL, capture_output=True, timeout=900)
        (t / 'job.stderr').write_bytes(p.stderr); cls.exit = p.returncode
        cls.rows = {r['file_id'].split('/')[0]: r for r in json.loads((cls.out / 'RESULT.json').read_bytes())['rows']}

    def logs(self, name): return self.out / ('logs_%d' % self.rows[name]['ordinal'])
    def attempt(self, name): return self.out / ('attempt_%d' % self.rows[name]['ordinal'])

    def test_ordinary_page_unchanged_no_child(self):
        r = self.rows['ordinary']
        self.assertEqual(r['outcome'], 'verified_saved_output', r.get('reasons'))
        self.assertFalse((self.attempt('ordinary') / 'source_reading').exists()); self.assertNotIn('source_reading', r)
        self.assertFalse((self.logs('ordinary') / 'source_reading').exists())

    def test_mixed_child_is_composed_verified_and_carries_the_hidden_word(self):
        r = self.rows['mixed']; s = r.get('source_reading') or {}
        self.assertEqual((r['outcome'], s.get('native_status'), s.get('reconstruct_exit'), s.get('verify_exit'), s.get('reasons')), ('verified_saved_output', 'OK', 0, 0, []), r.get('reasons'))
        R = json.loads((self.logs('mixed') / 'source_reading' / 'R.json').read_bytes())  # the child's OWN reconstruction (a parent-only R cannot satisfy this)
        recs = R['source_hidden']['records']; units = {u['id']: u for u in json.loads((self.attempt('mixed') / 'source_reading' / 'ROUTE.json').read_bytes())['units']}
        words = [units[o['unit']]['text'][a:b] for rec in recs for o in rec['owners'] for a, b in o['text_at']]
        self.assertEqual(words, ['quietly'])
        texts = [n['record'].get('text') for n in R['sequence'] if isinstance(n, dict) and 'record' in n]
        self.assertIn('Revenue grew quietly strongly.', texts)  # the composed child body holds the hidden word in place
        parent = json.loads((self.logs('mixed') / 'R.json').read_bytes()); self.assertNotIn('source_hidden', parent)

    def test_unplaceable_hidden_fact_child_blocks_whole_document_success(self):
        r = self.rows['hidden_fact']; s = r.get('source_reading') or {}
        self.assertEqual(s.get('native_status'), 'PARTIAL'); self.assertEqual(r['outcome'], 'incomplete')
        self.assertTrue(any(x.startswith('source reading: native status PARTIAL') for x in r['reasons']), r['reasons'])
        self.assertTrue((self.logs('hidden_fact') / 'source_reading' / 'R.json').is_file())

    def test_job_exit_is_not_success_with_an_incomplete_row(self):
        self.assertEqual(self.exit, 1)


if __name__ == '__main__':
    unittest.main()
