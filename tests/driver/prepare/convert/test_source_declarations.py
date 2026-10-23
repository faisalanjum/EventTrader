"""Source declarations and target identities kept in the saved route (Root OCR_DECLARATION_VALUES_IMPLEMENT_20261022T2320 and
OCR_DECLARATION_GATE_REVIEW_20261022T2341; OCR). The scanner already reads every start tag's attributes and every id: each link record keeps its tag's
on* declarations as written (name, value as the parser decodes it, and where that value stands in the source), and the route keeps the scanner's whole
id/name inventory (`source_ids`, raw: carried, never composed). Nothing is interpreted: the relation between a declaration and an id stays unresolved,
and a start byte is never proof of a target or of its end. Expected values come from the pinned browser's OWN HTML parsing of the original bytes
(an inert DOMParser document and template parsing from each saved start byte; every value slice parsed in its own quoting context), never from the
code under test. Scripts are data here: nothing is executed.
Run with the qualified interpreter from a checkout: python -I -B -m unittest tests.driver.prepare.convert.test_source_declarations
Environment: BROWSER_EXECUTABLE (default: the pinned headless shell path below)."""
import copy, hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
EXE = os.environ.get('BROWSER_EXECUTABLE', '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell')
sha = lambda b: hashlib.sha256(b).hexdigest()
PAGE = ('<html><body><p id="top">Intro <a href="#t1" onclick="show(&quot;d&#233;f&quot;, \'T1\')" onmouseover="hi()">Label</a> \u00e9t\u00e9</p>'
        '<p><a href="javascript:void(0);" ONCLICK=go(1)>Bare</a> <a href="#x" onclick>Empty</a> <a href="#y">Plain</a></p>'
        '<div style="display:none"><table id="t1"><tr><td>Hidden def</td></tr></table><a href="javascript:void(0)" onclick="close()" id="hc">x</a></div>'
        '<p id="d">1</p><p id="d">2</p><p id="">3</p><p><a name="n1">anchor</a></p><p><span onclick="go(\'t1\')">outside</span></p></body></html>').encode()
PAGES = {'mixed': PAGE,
         'ampersands': '<p><a href="#x" onclick="x(\'&not=1\', \'&notin;\', \'&amp;\', \'&noti\', \'&#233;\')">t</a></p><p id="x">x</p>'.encode(),  # literal vs decoded ampersands
         'raw_utf8': '<meta charset="utf-8"><p><a href="#x" onclick="say(\'\u00fc\u65e5\u672c\')">t</a></p><p id="\u00e9t\u00e9">u</p>'.encode('utf-8'),  # raw non-ASCII under declared UTF-8
         'unterminated_quote': b'<p><a href="#y" onclick="go(2)>Broken</a></p><p id="after">x</p><p>"tail</p>',  # malformed: the value runs on, as the parser reads it
         'unclosed': b'<div id="open"><p id="inner">x'}  # unproved extents: no end tag
FIRST = """(src) => { const t = document.createElement('template'); t.innerHTML = src; const e = t.content.firstElementChild; return e ? [e.localName, [...e.attributes].map(x => [x.name, x.value])] : null; }"""
VALUE = """([q, s]) => { const t = document.createElement('template'); t.innerHTML = q === '' ? '<i v=' + s + '>' : '<i v=' + q + s + q + '>'; const e = t.content.firstElementChild; return e ? e.getAttribute('v') : null; }"""
DOM = """(src) => { const d = new DOMParser().parseFromString(src, 'text/html'); const ids = [];
  for (const e of d.querySelectorAll('*')) { if (e.hasAttribute('id')) ids.push(['id', e.getAttribute('id')]); if (e.localName === 'a' && e.hasAttribute('name')) ids.push(['name', e.getAttribute('name')]); }
  return {links: d.querySelectorAll('a[href]').length, ids}; }"""


class DeclarationsInTheSavedRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from driver.prepare.convert import edgartools_html
        from playwright.sync_api import sync_playwright
        cls.routes = {k: edgartools_html.convert(raw, k + '.htm', sha(raw)) for k, raw in PAGES.items()}; cls.route = cls.routes['mixed']
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(executable_path=EXE)
        cls.page = cls.browser.new_context(offline=True).new_page()  # a blank page: template and DOMParser documents are inert (nothing in them runs)

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def native_tag(self, raw, start): return self.page.evaluate(FIRST, raw[start:].decode('utf-8', 'replace'))  # the original start tag at that byte, as the browser parses it

    def test_every_link_keeps_its_original_tags_declarations_with_honest_extents(self):
        for k, raw in PAGES.items():
            for l in self.routes[k]['source_links']:
                with self.subTest(page=k, tag=l['tag']['byte_start']):
                    tag = self.native_tag(raw, l['tag']['byte_start']); self.assertEqual(tag[0], 'a')
                    want = [[n, v] for n, v in tag[1] if n.startswith('on')]  # the browser's own attribute parsing: order, first occurrence, decoded value
                    self.assertEqual([[d['name'], d['value']] for d in l.get('declarations', [])], want)
                    if not want: self.assertNotIn('declarations', l)  # an absent declaration stays absent
                    for d in l.get('declarations', []):
                        if d['value_at'] is None: self.assertEqual(d['value'], ''); continue  # written with no value: no extent
                        a, b = d['value_at']; self.assertTrue(l['tag']['byte_start'] < a <= b < l['tag']['byte_end_exclusive'])
                        q = raw[a - 1:a].decode('latin-1'); q = q if q in ('"', "'") else ''
                        self.assertEqual(self.page.evaluate(VALUE, [q, raw[a:b].decode('utf-8')]), d['value'])  # the slice, parsed natively in its own quoting

    def test_the_raw_id_inventory_is_whole_and_each_start_is_its_own_tag(self):
        for k, raw in PAGES.items():
            with self.subTest(page=k):
                ids = self.routes[k]['source_ids']; self.assertIs(ids['read'], True)
                self.assertEqual([[r['by'], r['value']] for r in ids['records']], self.page.evaluate(DOM, raw.decode('utf-8'))['ids'])  # hidden, duplicate and empty ids, and names, in order
                for r in ids['records']:
                    tag = self.native_tag(raw, r['start']); self.assertIsNotNone(tag)
                    self.assertIn([r['by'], r['value']], [[n, v] for n, v in tag[1] if n == r['by'] and (n == 'id' or tag[0] == 'a')])  # that tag's own attribute
                    self.assertTrue(r['end'] is None or r['end'] > r['start'])  # where the scanner ends it, or unknown; never a claim about the target
        self.assertEqual([r['end'] for r in self.routes['unclosed']['source_ids']['records']], [None, None])  # no end tag: no end stated

    def test_a_malformed_tag_is_saved_once_as_written_never_as_the_parsers_clone(self):
        raw = PAGES['unterminated_quote']; links = self.routes['unterminated_quote']['source_links']
        self.assertEqual(len(links), 1); self.assertEqual(self.page.evaluate(DOM, raw.decode('utf-8'))['links'], 2)  # the tree builder re-opens the <a>: a copy, not a source tag
        self.assertEqual([[d['name'], d['value']] for d in links[0]['declarations']], [['onclick', 'go(2)>Broken</a></p><p id=']])
        self.assertEqual(self.routes['unterminated_quote']['source_ids']['records'], [])  # the would-be id is inside the value, for the browser too

    def test_reconstruction_carries_them_raw_and_preservation_catches_changes(self):
        from driver.prepare import reconstruct
        R = reconstruct.readback(self.route); self.assertEqual(reconstruct.preserved(self.route, R), [])
        self.assertEqual(R['not_composed']['source_ids'], self.route['source_ids']); self.assertNotIn('source_ids', R)  # raw: carried, not composed
        self.assertIn({'family': 'source_ids', 'why': 'not composed in this readback'}, R['unknowns'])
        damaged = []
        r1 = copy.deepcopy(R); d = next(l for l in r1['source_links'] if l.get('declarations')); d['declarations'][0]['value'] += ' '; damaged.append(r1)
        r2 = copy.deepcopy(R); next(l for l in r2['source_links'] if l.get('declarations'))['declarations'].pop(); damaged.append(r2)
        r3 = copy.deepcopy(R); recs = r3['not_composed']['source_ids']['records']; recs.append(dict(recs[0])); damaged.append(r3)
        r4 = copy.deepcopy(R); r4['not_composed']['source_ids']['records'].pop(); damaged.append(r4)
        for r in damaged: self.assertNotEqual(reconstruct.preserved(self.route, r), [])


class OutsideDeclarationThroughTheCaller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=EXE); version = b.version; b.close()
        t = Path(tempfile.mkdtemp(prefix='source_declarations_')); d = t / 'page'; d.mkdir(); (d / 'page.htm').write_bytes(PAGE)
        row = {'file_id': 'decl/page.htm', 'dispatch': 'html', 'directory': str(d), 'filename': 'page.htm', 'source_sha256': sha(PAGE), 'base': None, 'bundle': None,
               'members': {'page.htm': {'sha256': sha(PAGE), 'bytes': len(PAGE)}}}
        files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / 'driver').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
        man = t / 'MANIFEST.json'; man.write_text(json.dumps({'files': files}))
        body = json.dumps({'runtime_root': str(ROOT), 'runtime_manifest': {'path': str(man), 'sha256': sha(man.read_bytes())}, 'browser_executable': EXE,
                           'browser_executable_sha256': sha(Path(EXE).read_bytes()), 'browser_version': version, 'source_commands': [row]}).encode()
        plan = t / 'PLAN.json'; plan.write_bytes(body); cls.out = t / 'out'
        p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'driver/prepare/job.py'), str(plan), sha(body), str(cls.out)],
                           env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', str(t))}, stdin=subprocess.DEVNULL, capture_output=True, timeout=900)
        (t / 'job.stderr').write_bytes(p.stderr); cls.row = json.loads((cls.out / 'RESULT.json').read_bytes())['rows'][0]

    def test_outside_declaration_keeps_its_value_and_the_saved_output_verifies(self):
        route = json.loads((self.out / 'attempt_0' / 'ROUTE.json').read_bytes()); out = route['facts']['declared_outside_link_path']
        self.assertEqual([(d['tag'], [(x['name'], x['value']) for x in d['declarations']]) for d in out], [('span', [('onclick', "go('t1')")])])
        self.assertEqual((self.row.get('reconstruct_exit'), self.row.get('verify_exit')), (0, 0), self.row.get('reasons'))
        R = json.loads((self.out / 'logs_0' / 'R.json').read_bytes())
        self.assertEqual(R['not_composed']['source_ids'], route['source_ids']); self.assertEqual(R['not_composed']['facts'], route['facts'])
        self.assertEqual([l.get('declarations') for l in R['source_links']], [l.get('declarations') for l in route['source_links']])


if __name__ == '__main__':
    unittest.main()
