"""One exact-evidence resource boundary for every browser render (resource-composition-implement-20261011). A document is read at its declared
member path inside a verified bundle; the browser itself resolves every reference, which only the member at exactly that path or a recorded
observation of exactly that URL answers; anything else is refused, and a refused style sheet keeps the page PARTIAL. Visibility, geometry and
picture inputs read the same page, and the route names every dependency once. Expected values come from CSS, URL and encoding semantics."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from driver.prepare.convert import anchor, edgartools_html, html_route, screen_grid
from driver.prepare.pictures import inputs

Source = screen_grid.Source
DOC = (b'<html><head><link rel="stylesheet" href="g.css"><link rel="stylesheet" href="../shared/h.css"></head><body>'
       b'<table><tr><td>Alpha</td><td>Beta</td></tr><tr><td>Gamma</td><td>Delta</td></tr></table><div style="display:none"><p>Inline hidden</p></div></body></html>')
SHEETS = {'sub/g.css': b'@import "i.css"; table{direction:rtl}', 'sub/i.css': b'td{color:#000}', 'shared/h.css': b'div{display:block !important}'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def png(mode, colour, size=(8, 8)):
    out = io.BytesIO(); Image.new(mode, size, colour).save(out, 'PNG'); return out.getvalue()


FONTS = Path('/usr/share/fonts/truetype/dejavu')  # real installed font files: the font control needs them (a missing file fails, never skips)


class Boundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def prepare(self, raw, source=None):
        return html_route.prepare(raw, 'an opaque id, never an address', sha(raw), self.browser, source)[0]

    @staticmethod
    def pieces(route, text):
        return [p for u in route['units'] for p in [u] + list(u.get('cells') or []) if text in (p.get('text') or '')]

    def image(self, route):
        return next(u for u in route['units'] if u.get('kind') == 'image')

    def test_every_sheet_is_read_at_the_declared_address_and_recorded_once(self):
        route = self.prepare(DOC, Source('sub/doc.htm', SHEETS))
        self.assertEqual(route['status'], 'OK')
        self.assertEqual({r['member']: r['sha256'] for r in route['resources']['dependencies'] if 'member' in r}, {k: sha(v) for k, v in SHEETS.items()})  # sibling, its @import, the parent path
        shown = self.pieces(route, 'Inline hidden')
        self.assertTrue(shown and all(p.get('anchor') for p in shown))  # h.css (!important) shows what the inline style hid: shown text, linked

    def test_without_a_source_the_route_is_as_today(self):
        route = self.prepare(DOC)
        self.assertEqual(route['status'], 'PARTIAL'); self.assertNotIn('resources', route)

    def test_a_sheet_without_exact_evidence_stays_partial(self):
        rest = {k: v for k, v in SHEETS.items() if k != 'sub/g.css'}
        for members in (rest, {**rest, 'g.css': SHEETS['sub/g.css']}):  # missing; present only under another path (never an alias)
            route = self.prepare(DOC, Source('sub/doc.htm', members))
            self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('cannot be read offline', route['error'])
            self.assertIn({'path': 'sub/g.css', 'status': 'refused', 'kind': 'stylesheet'}, route['resources']['dependencies'])

    def test_a_recorded_answer_is_used_and_an_unrecorded_url_is_refused(self):
        raw = DOC.replace(b'</head>', b'<link rel="stylesheet" href="https://ext.example/a.css"></head>')
        seen = {'https://ext.example/a.css': {'status': 404, 'content_type': 'application/xml', 'observed_at': '2026-10-11T15:14:28Z'}}
        route = self.prepare(raw, Source('sub/doc.htm', SHEETS, observed=seen))
        self.assertEqual(route['status'], 'OK')
        self.assertIn({'url': 'https://ext.example/a.css', 'status': 404, 'observed_at': '2026-10-11T15:14:28Z', 'sha256': None, 'kind': 'stylesheet'}, route['resources']['dependencies'])
        self.assertEqual(self.prepare(raw, Source('sub/doc.htm', SHEETS))['status'], 'PARTIAL')

    def test_a_member_path_never_answers_a_navigation(self):
        raw = DOC.replace(b'</body>', b'<iframe src="frame.htm"></iframe></body>')
        route = self.prepare(raw, Source('sub/doc.htm', {**SHEETS, 'sub/frame.htm': b'<p>framed</p>'}))
        self.assertIn({'path': 'sub/frame.htm', 'status': 'refused', 'kind': 'navigation'}, route['resources']['dependencies'])
        self.assertFalse(any(r.get('member') == 'sub/frame.htm' for r in route['resources']['dependencies']))

    def test_geometry_reads_the_same_sheets(self):  # direction: rtl lays the first cell out to the right of the second
        vis = anchor.Visible(DOC); prefix = screen_grid.marker_prefix(DOC); marked, _ = screen_grid.tag_cells(DOC, vis, (), (), prefix)
        x = lambda by_table: {c['g']: c['x'] for cells in by_table.values() for c in cells}
        with self.assertRaisesRegex(RuntimeError, 'geometry is unproved'): screen_grid.measure(marked, self.browser, prefix, raw=DOC)  # no evidence: the sheets are not drawn, so nothing is certified
        now = x(screen_grid.measure(marked, self.browser, prefix, raw=DOC, source=Source('sub/doc.htm', SHEETS))[0])
        self.assertGreater(now[0], now[1])

    def test_a_non_utf8_page_is_read_in_the_browsers_charset(self):
        raw = b'<html><body><table><tr><td>Caf\xe9</td><td>\x93q\x94</td></tr></table></body></html>'  # windows-1252 bytes; no charset named
        source = Source('doc.htm', {}); page = screen_grid._document(self.browser, raw, raw, source)[0]
        try: self.assertEqual((source.charset, page.evaluate('document.body.innerText').split()), ('windows-1252', ['Café', '“q”']))
        finally: page.close()
        vis = anchor.Visible(raw); prefix = screen_grid.marker_prefix(raw); marked, _ = screen_grid.tag_cells(raw, vis, (), (), prefix)
        self.assertEqual(len([c for t in screen_grid.measure(marked, self.browser, prefix, raw=raw, source=Source('doc.htm', {}))[0].values() for c in t]), 2)

    def test_a_picture_is_the_member_at_the_address_the_page_resolves(self):  # sub/doc.htm's img/a.png is sub/img/a.png, never a namesake at the root
        raw = b'<html><body><p>Logo</p><img src="img/a.png" width="8" height="8"></body></html>'
        true, decoy = png('RGB', (200, 10, 10)), png('RGB', (10, 200, 10))
        for members, want in (({'sub/img/a.png': true, 'img/a.png': decoy}, {'member_sha256': sha(true), 'input_sha256': sha(true), 'how': 'member'}),
                              ({'img/a.png': decoy}, {'error': 'not a member of the package'})):
            source = Source('sub/doc.htm', members); route = self.prepare(raw, source); inputs.prepare(raw, route, members, self.browser, source)
            self.assertEqual(self.image(route)['input'], want)
        self.assertIn({'member': 'sub/img/a.png', 'sha256': sha(true), 'status': 200, 'kind': 'image'}, self.prepare_with_pictures(raw, {'sub/img/a.png': true})['resources']['dependencies'])

    def prepare_with_pictures(self, raw, members):
        source = Source('sub/doc.htm', members); route = self.prepare(raw, source); inputs.prepare(raw, route, members, self.browser, source); return route

    def test_the_dependencies_survive_the_picture_join(self):  # read_pictures returns the whole route: its record of what the renders asked stays
        import tempfile
        from driver.prepare.pictures import join
        raw = b'<html><body><p>Logo</p><img src="img/a.png" width="8" height="8"></body></html>'
        members = {'img/a.png': png('RGB', (1, 2, 3))}  # only a namesake at the root: the input is an error, so no reader runs
        source = Source('sub/doc.htm', members); route = self.prepare(raw, source)
        with tempfile.TemporaryDirectory() as folder: got, out = join.read_pictures(raw, route, members, self.browser, folder, {}, source=source)
        self.assertIs(got, route); self.assertEqual(out[0]['input'], {'error': 'not a member of the package'})
        self.assertIn({'path': 'sub/img/a.png', 'status': 'refused', 'kind': 'image'}, got['resources']['dependencies'])

    def test_a_transparent_picture_is_captured_from_the_same_page_and_its_bytes_are_bound(self):
        raw = b'<html><body><p>Chart</p><img src="img/t.png" width="8" height="8"></body></html>'
        first, changed = png('RGBA', (0, 0, 255, 0)), png('RGBA', (0, 0, 255, 1))
        for t in (first, changed):
            route = self.prepare_with_pictures(raw, {'sub/img/t.png': t})
            self.assertEqual((self.image(route)['input']['how'], self.image(route)['input']['member_sha256']), ('page', sha(t)))
            self.assertIn({'member': 'sub/img/t.png', 'sha256': sha(t), 'status': 200, 'kind': 'image'}, route['resources']['dependencies'])

    def test_a_route_that_records_its_evidence_takes_only_the_same_source(self):  # Root's shared-source gate: one Source per document, passed through; identity is never inferred from bytes alone
        import copy
        raw = b'<html><head><link rel="stylesheet" href="n.css"></head><body><p>Note</p><img src="o.png" width="8" height="8"><img src="t.png" width="8" height="8"></body></html>'
        a = {'n.css': b'p{display:none}', 'o.png': png('RGB', (9, 9, 9)), 't.png': png('RGBA', (0, 0, 255, 0))}  # o: an opaque member; t: captured from the page
        b = dict(a, **{'n.css': b'p{color:red}', 'o.png': png('RGB', (8, 8, 8))})  # package B: the same document bytes, another sheet and picture
        for bundle in ('A', None):  # a named bundle and an unnamed one
            source = Source('doc.htm', a, bundle=bundle); route = self.prepare(raw, source); before = copy.deepcopy(route)
            for name, members, other in (('no Source', a, None), ('another bundle', a, Source('doc.htm', a, bundle='B')), ('another package', b, Source('doc.htm', b, bundle=bundle)),
                                         ('another path', a, Source('other.htm', a, bundle=bundle)), ('a fresh equivalent', a, Source('doc.htm', a, bundle=bundle))):
                with self.subTest(bundle=bundle, rejected=name):
                    with self.assertRaisesRegex(ValueError, 'same Source'): inputs.prepare(raw, route, members, self.browser, other)
                    self.assertEqual(route, before)  # the rejected call changed nothing: its bytes and records stay
            got = inputs.prepare(raw, route, a, self.browser, source); again = inputs.prepare(raw, route, a, self.browser, source)  # the same Source: a legitimate repeat
            o, t = [u['input'] for u in route['units'] if u.get('kind') == 'image']
            self.assertEqual((o['how'], o['member_sha256'], t['how'], t['member_sha256'], got.keys() == again.keys()), ('member', sha(a['o.png']), 'page', sha(a['t.png']), True))
            self.assertTrue(all(r in route['resources']['dependencies'] for r in before['resources']['dependencies']))  # no prior observation disappears or is replaced
            self.assertIn({'member': 'o.png', 'sha256': sha(a['o.png']), 'status': 200, 'kind': 'image'}, route['resources']['dependencies'])
        with self.assertRaisesRegex(ValueError, 'same Source'): inputs.prepare(raw, self.prepare(raw), a, self.browser, Source('doc.htm', a))  # a route that records no evidence takes no Source

    def test_a_refused_resource_withholds_the_geometry_and_keeps_every_reading(self):  # Root v5 item 1: a font no evidence answers leaves the geometry unproved; the run readings stay
        raw = (b'<html><head><style>@font-face{font-family:"F";src:url(f.woff)}</style></head><body><table><tr><td style="font-family:F">Label</td><td>12</td></tr></table>'
               b'<p>Yes <span style="font-family:Wingdings">&#254;</span> x<sup>2</sup></p></body></html>')
        route, facts = html_route.prepare(raw, 'r.htm', sha(raw), self.browser)
        self.assertEqual((route['status'], '+screen' in route['route']['name'], 'screen_endpoints' in route), ('PARTIAL', False, False))  # explicit, and nothing unproved applied
        self.assertRegex(route['error'], 'geometry is unproved: http://[^ ]*/f\\.woff')
        self.assertEqual([(r['raw'], r['status']) for r in route['source_symbols']['records']], [('\u00fe', 'decoded')])  # the symbol reading survives the refused font
        self.assertEqual([r['raw'] for r in route['source_inline']['records']], ['2'])  # and so does the raised reading
        self.assertEqual(facts['screen']['cells_regridded'], 0)
        with self.assertRaisesRegex(RuntimeError, 'geometry is unproved'): screen_grid.measure(raw, self.browser, raw=raw)  # a direct caller keeps the honest failure

    def test_a_file_that_is_not_utf8_is_compared_in_the_scans_own_reading(self):  # Root v5 item 3: the scan reads such a file one cp1252 character per byte (anchor.Visible); the page agrees, or the geometry is unproved
        cases = ((b'<html><head><meta charset="windows-1252"></head><body><table><tr><td>Caf\xe9 \x96 net</td><td>\x805</td></tr></table></body></html>', True),  # declared windows-1252: the page shows the scan's characters
                 (b'<p><span style="font-family:Wingdings">\xfe</span></p>', False),  # unlabelled: Chrome guesses another code page ('\u015f'), the scan reads '\u00fe' - a real disagreement
                 (b'<html><head><meta charset="windows-1252"></head><body><p>a\x81b</p></body></html>', False))  # a byte cp1252 leaves undefined: the scan keeps U+FFFD, the page U+0081
        for raw, grid in cases:
            with self.subTest(raw=raw):
                route = self.prepare(raw); self.assertEqual('+screen' in route['route']['name'], grid)
                if not grid: self.assertIn('source run otherwise than the scan reads it, so its geometry is unproved', route['error'])

    def test_the_route_names_its_document_and_bundle(self):
        route = self.prepare(DOC, Source('sub/doc.htm', SHEETS, bundle='package-sha256-xyz'))
        self.assertEqual(route['resources']['document'], {'path': 'sub/doc.htm', 'base': None, 'bundle': 'package-sha256-xyz', 'sha256': sha(DOC)})

    def test_a_recorded_200_is_used_only_with_the_bytes_its_hash_names(self):
        raw = DOC.replace(b'</head>', b'<link rel="stylesheet" href="https://ext.example/b.css"></head>')
        body = b'p{color:#000}'; ok = {'status': 200, 'content_type': 'text/css', 'observed_at': 't1', 'sha256': sha(body), 'body': body}
        self.assertEqual(self.prepare(raw, Source('sub/doc.htm', SHEETS, observed={'https://ext.example/b.css': ok}))['status'], 'OK')
        for bad in (dict(ok, body=b'p{color:red}'), {k: v for k, v in ok.items() if k != 'body'}):  # other bytes than recorded; no bytes at all: never an empty success
            route = self.prepare(raw, Source('sub/doc.htm', SHEETS, observed={'https://ext.example/b.css': bad}))
            self.assertEqual(route['status'], 'PARTIAL')
            self.assertIn({'url': 'https://ext.example/b.css', 'status': 'refused', 'kind': 'stylesheet', 'why': 'observed bytes are not the recorded sha256'}, route['resources']['dependencies'])

    def test_a_source_is_one_documents_evidence(self):
        source = Source('sub/doc.htm', SHEETS); self.prepare(DOC, source)
        with self.assertRaises(ValueError): self.prepare(DOC.replace(b'Alpha', b'Omega'), source)  # reused on other bytes
        with self.assertRaises(ValueError): self.prepare(DOC, Source('sub/doc.htm', {**SHEETS, 'sub/doc.htm': b'<p>another document</p>'}))  # the declared member is other bytes

    def test_a_render_failure_is_said_on_each_picture_and_a_resource_error_propagates(self):
        from unittest import mock
        raw = b'<html><body><p>Logo</p><img src="img/a.png" width="8" height="8"></body></html>'
        members = {'sub/img/a.png': png('RGB', (200, 10, 10))}
        source = Source('sub/doc.htm', members); route = self.prepare(raw, source)
        with mock.patch.object(screen_grid, '_document', side_effect=RuntimeError('render failed')):
            inputs.prepare(raw, route, members, self.browser, source)
        self.assertEqual(self.image(route)['input'], {'error': "page: RuntimeError('render failed')"})
        with mock.patch.object(screen_grid, '_document', side_effect=MemoryError()), self.assertRaises(MemoryError):
            inputs.prepare(raw, route, members, self.browser, source)

    def test_an_unobserved_font_or_image_leaves_the_geometry_unproved(self):  # a fallback face or a broken-image box is not the original's geometry
        doc = (b'<html><head><style>@font-face{font-family:Probe;src:url("f.ttf")} td{font-family:Probe,serif}</style></head><body>'
               b'<table><tr><td><img src="img/w.png"></td><td>Label</td></tr></table></body></html>')
        font, other, pic = (FONTS / 'DejaVuSans.ttf').read_bytes(), (FONTS / 'DejaVuSansMono.ttf').read_bytes(), png('RGB', (9, 9, 9), (200, 40))
        for members, status in (({'sub/f.ttf': font, 'sub/img/w.png': pic}, 'OK'), ({'sub/f.ttf': other, 'sub/img/w.png': pic}, 'OK'),
                                ({'sub/img/w.png': pic}, 'PARTIAL'), ({'sub/f.ttf': font}, 'PARTIAL')):
            route = self.prepare(doc, Source('sub/doc.htm', members))
            self.assertEqual(route['status'], status); self.assertTrue(self.pieces(route, 'Label'))  # content and its source kept either way
            if status == 'PARTIAL': self.assertIn('geometry', route['error'])
        ext = doc.replace(b'url("f.ttf")', b'url("https://ext.example/f.ttf")')
        seen = {'https://ext.example/f.ttf': {'status': 404, 'content_type': 'text/html', 'observed_at': '2026-10-11T16:40:00Z'}}
        self.assertEqual(self.prepare(ext, Source('sub/doc.htm', {'sub/img/w.png': pic}, observed=seen))['status'], 'OK')  # an observed 404: the fallback is that observation's
        self.assertEqual(self.prepare(ext, Source('sub/doc.htm', {'sub/img/w.png': pic}))['status'], 'PARTIAL')  # unrecorded: never an observed 404

    def test_a_failed_conversion_keeps_its_resources(self):
        doc = b'<html><head><link rel="stylesheet" href="g.css"></head><body><p>x</p></body></html>'
        failed = lambda raw, fid, digest, vis=None: edgartools_html.unsupported(fid, digest, edgartools_html.version(), 'FAILED', "ValueError('parse failed')")
        with mock.patch.object(edgartools_html, 'convert', side_effect=failed): route = self.prepare(doc, Source('sub/doc.htm', {'sub/g.css': b'p{}'}))
        self.assertEqual(route['status'], 'FAILED')
        self.assertIn({'member': 'sub/g.css', 'sha256': sha(b'p{}'), 'status': 200, 'kind': 'stylesheet'}, route['resources']['dependencies'])
        self.assertEqual(json.loads(json.dumps(route)), route)

    def test_a_marked_page_that_fails_to_load_is_closed_and_its_error_propagates(self):  # inventory gap (current_inventory_reconciliation_v1): _document's close-and-reraise
        real, made = screen_grid._offline_page, []
        def opening(fail):
            def make(browser, asked=None, document=None, source=None):
                page = real(browser, asked, document, source); made.append(page)
                if fail is not None and document is not None and len(document) == 3:  # the marked page (address, body, charset); the charset page is read first
                    def goto(*a, **k): raise fail('injected goto failure')
                    page.goto = goto
                return page
            return make
        with mock.patch.object(screen_grid, '_offline_page', opening(None)): page, address, first = screen_grid._document(self.browser, DOC, DOC, Source('sub/doc.htm', SHEETS))
        self.assertEqual((page.is_closed(), [p.is_closed() for p in made]), (False, [True, False]))  # the loaded page is returned open (the charset page was closed)
        page.close()
        for fail in (RuntimeError, MemoryError):  # an ordinary and a machine failure: either way the page is closed and the same error propagates
            made.clear()
            with self.subTest(error=fail.__name__), mock.patch.object(screen_grid, '_offline_page', opening(fail)), self.assertRaises(fail):
                screen_grid._document(self.browser, DOC, DOC, Source('sub/doc.htm', SHEETS))
            self.assertEqual([p.is_closed() for p in made], [True, True])

    def test_the_declared_address_never_silently_misresolves(self):
        for bad in (dict(path='doc.htm', base='https://example.test/dir'), dict(path='doc.htm', base='dir/'), dict(path='/doc.htm'), dict(path='doc.htm', members={'a.css': bytearray(b'x')}),
                    dict(path='doc.htm', observed={'https://example.test/a.css': {'status': 404}})):  # no trailing slash; not absolute; absolute path; mutable bytes; an observation without its time
            with self.assertRaises(ValueError): Source(bad.pop('path'), bad.pop('members', {}), **bad)
        route = self.prepare(DOC, Source('sub/my doc \u00e9.htm', SHEETS))  # a member path a URL must encode
        self.assertEqual(route['status'], 'OK')
        self.assertEqual({r['member'] for r in route['resources']['dependencies'] if 'member' in r}, set(SHEETS))

    def test_one_documents_evidence_cannot_change_between_renders(self):
        members = dict(SHEETS); source = Source('sub/doc.htm', members); self.prepare(DOC, source)
        members['sub/g.css'] = b'table{direction:ltr}'  # the caller's mapping changes after the first render
        vis = anchor.Visible(DOC); prefix = screen_grid.marker_prefix(DOC); marked, _ = screen_grid.tag_cells(DOC, vis, (), (), prefix)
        x = {c['g']: c['x'] for t in screen_grid.measure(marked, self.browser, prefix, raw=DOC, source=source)[0].values() for c in t}
        self.assertGreater(x[0], x[1])  # still the bytes the source was given (rtl), the bytes its record names
        self.assertIn({'member': 'sub/g.css', 'sha256': sha(SHEETS['sub/g.css']), 'status': 200, 'kind': 'stylesheet'}, source.identity()['dependencies'])

    def test_a_verified_package_composes_through_the_package_reader(self):  # read_package -> html_route.prepare -> inputs.prepare with one Source
        from driver.prepare.get.acquire import acquire, read_package
        from tests.driver.prepare.get.test_acquire import ACCESSION, CIK, FORM, package, uu
        doc = b'<html><head><link rel="stylesheet" href="s.css"></head><body><p>Filing</p><img src="logo.png" width="8" height="8"></body></html>'
        lone = b'<html><head><link rel="stylesheet" href="missing.css"></head><body><p>Exhibit</p></body></html>'
        logo = png('RGB', (1, 2, 3))
        data = package([('main.htm', doc, '8-K', '1', None), ('s.css', b'p{color:#000}', 'GRAPHIC', '2', None), ('logo.png', uu(logo, 'logo.png'), 'GRAPHIC', '3', None), ('ex99.htm', lone, 'EX-99', '4', None)])
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'input.txt'; src.write_bytes(data)
            manifest, files = read_package(acquire(ACCESSION, CIK, FORM, Path(tmp) / 'out', package=src, sha256=sha(data)))
        shas = {m['filename']: m['sha256'] for m in manifest['members']}
        source = Source('main.htm', files, bundle=manifest['package']['sha256']); route = self.prepare(files['main.htm'], source)
        inputs.prepare(files['main.htm'], route, files, self.browser, source)
        self.assertEqual(route['status'], 'OK'); self.assertEqual(self.image(route)['input']['member_sha256'], shas['logo.png'])
        self.assertEqual(route['resources']['document'], {'path': 'main.htm', 'base': None, 'bundle': manifest['package']['sha256'], 'sha256': shas['main.htm']})
        self.assertEqual({r['member']: r['sha256'] for r in route['resources']['dependencies'] if 'member' in r}, {'s.css': shas['s.css'], 'logo.png': shas['logo.png']})
        other = self.prepare(files['ex99.htm'], Source('ex99.htm', files, bundle=manifest['package']['sha256']))  # no observed resource: the absence stays explicit
        self.assertEqual(other['status'], 'PARTIAL'); self.assertIn({'path': 'missing.css', 'status': 'refused', 'kind': 'stylesheet'}, other['resources']['dependencies'])

    def test_the_default_call_never_certifies_geometry_it_did_not_draw(self):  # no Source: a picture or a font the page names is unread, its layout unproved
        for raw, status in ((b'<html><body><table><tr><td><img src="img/w.png"></td><td>Label</td></tr></table></body></html>', 'PARTIAL'),
                            (b'<html><head><style>@font-face{font-family:Probe;src:url("f.ttf")} td{font-family:Probe,serif}</style></head><body><table><tr><td>Label</td><td>12</td></tr></table></body></html>', 'PARTIAL'),
                            (b'<html><body><table><tr><td>Label</td><td>12</td></tr></table></body></html>', 'OK')):  # the positive: a page that names nothing
            route = self.prepare(raw)
            self.assertEqual(route['status'], status); self.assertTrue(self.pieces(route, 'Label'))  # content and its source kept either way
            if status == 'PARTIAL': self.assertIn('geometry is unproved', route['error'])



class ObservationBodyIdentity(unittest.TestCase):  # Root FABLE_FINAL_BODY_GUARD_20261023T1715: a SUPPLIED body must match its recorded digest whatever the status
    URL = 'https://evidence.invalid/f/dep.css'
    BODY = b'p { color: navy }'

    def observe(self, status, body, digest):  # one recorded observation answered through the Source's own rule: (returned or None, its record)
        o = {'status': status, 'observed_at': 'invented test evidence', 'content_type': 'text/css', 'sha256': digest}
        if body is not None: o['body'] = body
        s = Source('d.html', {'d.html': b'<p>d</p>'}, base='https://evidence.invalid/f/', observed={self.URL: o})
        return s.observation(self.URL, 'stylesheet'), s.records[self.URL]

    def assertServed(self, got, rec, status, body):
        self.assertEqual(got, (status, 'text/css', body)); self.assertEqual((rec['status'], rec['sha256']), (status, hashlib.sha256(body).hexdigest()))  # the record names the bytes returned
    def assertRefused(self, got, rec):
        self.assertIsNone(got); self.assertEqual((rec['status'], rec['why']), ('refused', 'observed bytes are not the recorded sha256'))

    def test_a_200_needs_its_body_and_the_matching_digest(self):
        h, e = hashlib.sha256(self.BODY).hexdigest(), hashlib.sha256(b'').hexdigest()
        self.assertServed(*self.observe(200, self.BODY, h), 200, self.BODY)
        self.assertServed(*self.observe(200, b'', e), 200, b'')  # an explicitly supplied empty body with its own digest
        self.assertRefused(*self.observe(200, None, h)); self.assertRefused(*self.observe(200, None, None))  # no body
        self.assertRefused(*self.observe(200, self.BODY, e)); self.assertRefused(*self.observe(200, self.BODY, None))  # wrong or missing digest

    def test_a_supplied_non_200_body_must_match_its_digest(self):  # failed before: any non-200 body was returned and recorded unchecked
        h, e = hashlib.sha256(self.BODY).hexdigest(), hashlib.sha256(b'').hexdigest()
        self.assertServed(*self.observe(404, self.BODY, h), 404, self.BODY)  # valid supplied 404
        self.assertRefused(*self.observe(404, self.BODY, hashlib.sha256(b'other').hexdigest()))  # corrupted supplied 404
        self.assertRefused(*self.observe(404, self.BODY, None))  # a supplied body with a missing digest
        self.assertRefused(*self.observe(404, b'', None))  # an explicitly supplied empty body with a missing digest
        self.assertServed(*self.observe(404, b'', e), 404, b'')  # an explicitly supplied empty body with its own digest
        self.assertRefused(*self.observe(500, self.BODY, e))  # any non-200 status, same rule

    def test_a_digest_without_a_supplied_body_is_refused_whatever_the_status(self):  # Root FABLE_BODY_PAIR_COMPLETION_20261023T1725: failed before (non-200 accepted)
        for status in (404, 500):
            self.assertRefused(*self.observe(status, None, hashlib.sha256(self.BODY).hexdigest()))
            self.assertRefused(*self.observe(status, None, hashlib.sha256(b'').hexdigest()))

    def test_the_full_status_body_digest_matrix(self):  # accepted ONLY: a supplied body equal to its digest, or a non-200 with BOTH body and digest absent
        for status in (200, 404):
            for body in (None, b'', self.BODY):
                for digest in (None, hashlib.sha256(b'').hexdigest(), hashlib.sha256(self.BODY).hexdigest()):
                    ok = (body is not None and digest == hashlib.sha256(body).hexdigest()) or (status != 200 and body is None and digest is None)  # the invariant, by hashlib
                    got, rec = self.observe(status, body, digest)
                    with self.subTest(status=status, body=body, digest=digest):
                        if ok: self.assertEqual(got, (status, 'text/css', body if body is not None else b''))
                        else: self.assertRefused(got, rec)

    def test_a_native_failure_without_body_or_digest_stays_an_explicit_failure(self):  # the real controls' only non-200 form (null hash, no body)
        got, rec = self.observe(404, None, None); self.assertEqual(got, (404, 'text/css', b'')); self.assertEqual((rec['status'], rec['sha256']), (404, None))


if __name__ == '__main__':
    unittest.main()
