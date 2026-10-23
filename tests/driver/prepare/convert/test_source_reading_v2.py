"""Typed whole-source reading, as corrected by Root (ROOT_SOURCE_READING_CHOICE_REVIEW_20261022T2115) and Smart's run-record family; OCR. The SAME
native parse with hidden authored content kept (`anchor.Visible(source=True)`; `edgartools_html.named` deletes nothing), rebuilt from the DISPLAYED
route's own saved visibility evidence (no new render), typed as a source reading (never a display state). Every proved-hidden run is a
`source_hidden` record placed by the one run-to-owner rule (`screen_grid._owners`: owners + code-point `text_at`), or listed `unresolved`
(route PARTIAL). The caller saves it as its own attempt under source_reading/, pinned by the parent's COMPLETE and held to the same custody gate.
Expected values come from each fixture's own bytes; real-content expectations from the ORIGINAL DOM (lxml), never from our reader. Real inputs: public CCL R1 (two definitions no control reaches) and AMG R1. The damage check (a fresh reading of the same bytes) is a consistency check, not source truth.
Run: python -I -B -m unittest discover -s tests/driver/prepare/convert -p test_source_reading_v2.py -t ."""
import copy, hashlib, json, re, tempfile, unittest
from pathlib import Path
from driver.prepare.convert import anchor, edgartools_html as eh, html_route, screen_grid as sg
from driver.prepare import document, reconstruct
from driver.prepare.get import acquire, archive

PUBLIC = Path('/home/faisal/prepare_work/extraction_closeout_20261010/production_qualification_20261022/ocr_no_click')
def doc(body): raw = ('<html><body>%s</body></html>' % body).encode(); return raw, hashlib.sha256(raw).hexdigest()
def items(r): return [x for u in r['units'] for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u])]
def site(r, o):  # the unit or cell a saved owner names (reconstruct's own owner rule)
    by_id = {u['id']: u for u in r['units']}; u = by_id[o['unit']]
    return u if 'cell' not in o else next(c for c in u['cells'] if reconstruct._first_byte(c) == o['cell'])
def hidden(r):  # [(owner text, [hidden slices])] from the saved family, in record order
    return [(site(r, o)['text'], [site(r, o)['text'][a:b] for a, b in o['text_at']]) for rec in r['source_hidden']['records'] for o in rec['owners']]
def defrefs(raw):
    t = raw.decode('utf-8', 'replace'); return re.findall(r'id="(defref_[^"]+)"', t), set(re.findall(r"Show\.showAR\( this, '([^']+)'", t))
import lxml.html  # the original document's own DOM (native lxml): the independent oracle for real content, never our reader
norm = lambda s: re.sub(r'\s+', '', s.replace('\xa0', ' '))
def table_text(raw, tid):  # one definition table's text as the ORIGINAL DOM holds it (lxml text_content), white space removed
    return norm(lxml.html.fromstring(raw).xpath('//table[@id=$i]', i=tid)[0].text_content())
def joined(r): return norm(' '.join(x.get('text', '') for x in items(r)))
def damage(raw, saved, displayed):  # a SAVED source reading must equal a fresh one of the same bytes and the same displayed evidence
    fresh, _ = html_route.source_reading(raw, saved['file_id'], saved['sha256'], displayed); out = []
    for k in ('units', 'source_hidden', 'uncovered', 'status'):
        if json.dumps(saved.get(k), sort_keys=True) != json.dumps(fresh.get(k), sort_keys=True): out.append(k + ' differs')
    return out


class Synthetic(unittest.TestCase):  # certain scans: the displayed route is the plain conversion (no browser verdict needed)
    def read(self, body):
        raw, sha = doc(body); shown = eh.convert(raw, 'x.htm', sha); r, why = html_route.source_reading(raw, 'x.htm', sha, shown); return raw, sha, shown, r, why

    def test_mixed_words_keep_the_displayed_sentence_and_place_the_hidden_word(self):
        raw, sha, shown, r, _ = self.read('<p>Revenue grew <span style="display:none">quietly</span> strongly.</p>')
        self.assertEqual([x['text'] for x in items(shown)], ['Revenue grew strongly.'])
        self.assertEqual(r['route']['settings']['reading'], 'source (not a display state)'); self.assertTrue(r['route']['name'].endswith('+source-reading'))
        self.assertEqual(hidden(r), [('Revenue grew quietly strongly.', ['quietly'])]); self.assertEqual(r['status'], 'OK')

    def test_inline_white_space_is_never_a_hidden_place(self):
        raw, sha, shown, r, _ = self.read('<p>A<span style="display:none"> b c </span>d</p>')
        self.assertEqual([w for _, ws in hidden(r) for w in ws], ['b', 'c'])

    def test_an_ordinary_page_has_no_source_reading_and_says_why(self):
        raw, sha, shown, r, why = self.read('<p>Plain shown text.</p>')
        self.assertIsNone(r); self.assertEqual(why, 'no proved-hidden span')

    def test_hidden_heading_and_nested_table_kept_in_place(self):
        raw, sha, shown, r, _ = self.read('<h2 style="display:none">Secret heading</h2><p>Shown</p><table><tr><td>Outer<table style="display:none"><tr><td>Inner hidden</td></tr></table></td></tr></table>')
        self.assertNotIn('Secretheading', joined(shown))  # joined() removes white space
        got = {t: ws for t, ws in hidden(r)}
        self.assertEqual(got.get('Secret heading'), ['Secret', 'heading'])
        self.assertTrue(any('Inner hidden' in t for t in got), got)
        self.assertNotIn('Shown', got)  # shown text carries no hidden record

    def test_ix_hidden_is_an_explicit_gap_and_keeps_the_reading_partial(self):
        raw, sha, shown, r, _ = self.read('<div style="display:none"><ix:header><ix:hidden><ix:nonNumeric name="dei:X">Hidden fact</ix:nonNumeric></ix:hidden></ix:header></div><p>Body</p>')
        self.assertNotIn('Hiddenfact', joined(r)); self.assertTrue(r['uncovered'])
        self.assertTrue(r['source_hidden'].get('unresolved')); self.assertEqual(r['status'], 'PARTIAL')
        self.assertIn('not placed', r['error'])

    def test_an_uncertain_scan_without_a_browser_verdict_is_unproved_not_empty(self):
        raw, sha = doc('<link rel="stylesheet" href="missing.css"><p>A <span style="display:none">b</span> c</p>')
        shown = eh.convert(raw, 'x.htm', sha); self.assertNotIn('page_visibility', shown)
        r, why = html_route.source_reading(raw, 'x.htm', sha, shown)
        self.assertIsNone(r); self.assertIn('unproved', why)

    def test_the_readback_composes_the_family_and_reports_unresolved_runs(self):
        raw, sha, shown, r, _ = self.read('<p>Revenue grew <span style="display:none">quietly</span> strongly.</p>')
        R = reconstruct.readback(r); self.assertEqual(reconstruct.preserved(r, R), [])
        self.assertEqual([u for u in R['unknowns'] if u.get('family') == 'source_hidden'], [])
        self.assertIn('source_hidden', R)  # composed as an attached run family, not carried as an unread field
        raw, sha, shown, r2, _ = self.read('<div style="display:none"><ix:header><ix:hidden><ix:nonNumeric name="dei:X">Hidden fact</ix:nonNumeric></ix:hidden></ix:header></div><p>Body</p>')
        R2 = reconstruct.readback(r2); self.assertTrue([u for u in R2['unknowns'] if u.get('family') == 'source_hidden'])

    def test_saved_custody_binds_the_child_and_fails_on_damage(self):
        raw, sha = doc('<p>Revenue grew <span style="display:none">quietly</span> strongly.</p>'); row = {'file_id': 'x.htm', 'source_sha256': sha}
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / 'attempt'; a.mkdir(); shown = eh.convert(raw, 'x.htm', sha)
            document.source_child(a, row, raw, shown, {'path': 'x.htm'}, html_route, eh, archive, acquire)
            self.assertEqual(shown['facts']['source_reading'], {'made': True, 'status': 'OK'})
            document.finish(a, row, shown, {}, archive, document.save)
            route, _, custody = reconstruct._custody(a); self.assertIn('source_reading_complete_sha256', custody)
            child = json.loads((a / 'source_reading' / 'ROUTE.json').read_bytes()); self.assertEqual(hidden(child), [('Revenue grew quietly strongly.', ['quietly'])])
            self.assertTrue((a / 'RAW_READING.json').exists() is False and (a / 'source_reading' / 'RAW_READING.json').exists())  # the child's own receipt; the parent's untouched
            p = a / 'source_reading' / 'ROUTE.json'; body = p.read_bytes(); p.chmod(0o600); p.write_bytes(body.replace(b'quietly', b'QUIETLY'))
            with self.assertRaises(ValueError): reconstruct._custody(a)  # a changed child route fails the parent
            p.write_bytes(body); reconstruct._custody(a)
            (a / 'source_reading' / 'COMPLETE.json').rename(a / 'source_reading' / 'COMPLETE.moved')
            with self.assertRaises(ValueError): reconstruct._custody(a)  # a missing child completion fails the parent


class RealReports(unittest.TestCase):  # the displayed route through the production html_route.prepare (browser verdict saved), then the source reading
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.got = {}
        for name in ('CCL_R1.htm', 'AMG_R1.htm'):
            raw = (PUBLIC / name).read_bytes(); sha = hashlib.sha256(raw).hexdigest()
            css = (PUBLIC / 'AMG_report.css').read_bytes()  # the public SEC stylesheet both R pages name (include/report.css), saved earlier: the displayed route gets its browser verdict
            src = sg.Source(name, {name: raw, 'include/report.css': css})
            shown, _ = html_route.prepare(raw, name, sha, cls.browser, src); r, why = html_route.source_reading(raw, name, sha, shown)
            cls.got[name] = (raw, sha, shown, r, why)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_ccl_r1_keeps_both_unreachable_definitions_once_and_invents_no_relation(self):
        raw, sha, shown, r, why = self.got['CCL_R1.htm']; ids, targets = defrefs(raw); orphans = [i for i in ids if i not in targets]
        self.assertEqual(len(orphans), 2); self.assertIsNotNone(r, why)
        self.assertEqual(r['route']['settings']['hidden_basis'], 'browser verdict of the displayed route')
        for tid in orphans:
            want = table_text(raw, tid); self.assertEqual(joined(r).count(want), 1, tid); self.assertNotIn(want, joined(shown))
        self.assertEqual([l['href'] for l in r['source_links']], [l['href'] for l in shown['source_links']])

    def test_amg_r1_keeps_every_definition(self):
        raw, sha, shown, r, why = self.got['AMG_R1.htm']; ids, _ = defrefs(raw)
        self.assertEqual(len(ids), 27); self.assertEqual([tid for tid in ids if table_text(raw, tid) not in joined(r)], [])

    def test_saved_damage_is_detected(self):
        raw, sha, shown, r, _ = self.got['CCL_R1.htm']; self.assertEqual(damage(raw, r, shown), [])
        ids, targets = defrefs(raw); want = table_text(raw, [i for i in ids if i not in targets][0])
        cut = copy.deepcopy(r); cut['units'] = [u for u in cut['units'] if want[:20] not in norm(' '.join(x.get('text', '') for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u])))]
        self.assertTrue(damage(raw, cut, shown))  # deletion of a hidden definition
        chg = copy.deepcopy(r); x = items(chg)[-1]; x['text'] = x.get('text', '') + ' extra'; self.assertTrue(damage(raw, chg, shown))  # changed text
        swp = copy.deepcopy(r); swp['units'][0], swp['units'][-1] = swp['units'][-1], swp['units'][0]; self.assertTrue(damage(raw, swp, shown))  # order
        vis = copy.deepcopy(r); vis['source_hidden']['records'] = vis['source_hidden']['records'][1:]; self.assertTrue(damage(raw, vis, shown))  # visibility annotation


if __name__ == '__main__':
    unittest.main()
