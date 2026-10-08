"""Hidden text where the scanner cannot certify its reading (Codex CODEX_DESIGN_REVIEW, 2026-10-08): before the tool reads such a file the browser says
which of its text runs the page hides (`screen_grid.page_visibility`: the symbol marks' walk and rule, every run), and the tool is given the source
without exactly those runs - each whole source token, and only where the text a run's mark reached is the run's own. Nothing the browser did not prove
is left out: a span the scanner hides and a sheet shows again stays, as do literal text no mark can stand in, text the parser moves away from its mark
and text the browser reads otherwise than the scanner. The linker and the screen step read by the same verdict. Offline Chrome; playwright is required
(a missing install fails, never skips)."""
import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from driver.prepare.convert import anchor, edgartools_html as eh, html_route, screen_grid as sg

SHEET = b'<style>.gone{display:none}.show{display:inline !important}.vis{visibility:visible !important}</style>'  # a sheet: no reading here is certain
PAGE = (b'<html><head>' + SHEET + b'</head><body>'
        b'<table><tr><td>VAL835</td><td><span style="display:none">VAL835 </span>NEXTA</td></tr></table>'  # a hidden copy of the cell before it
        b'<p>BEFOREB <span class="gone">GONEB</span> AFTERB</p>'  # hidden by the sheet alone: the scanner reads it shown
        b'<p><span class="show" style="display:none">SHOWNC</span></p><p><span class="vis" style="visibility:hidden">SHOWND</span></p>'  # shown again by the sheet
        b'<p><span style="visibility:hidden">LEADE <b style="visibility:visible">CHILDE</b> TAILE</span> ENDE</p>'  # a visible child
        b'<p>REVF<span style="display:none">MIDF</span> million</p>'  # hidden text glued to a word
        b'<textarea class="show" style="display:none">LITG</textarea>'  # literal text: no mark can stand in it
        b'<table class="show" style="display:none">FOSTH<tr><td>CELLH</td></tr></table>'  # text the parser moves out of the table, away from its mark
        b'<p><span class="gone">MISI &copy2024</span></p>'  # the browser reads "\xa92024", the scanner six characters: not the run's own text
        b'<p>LEFTJ < RIGHTJ</p>'  # a lone "<": two marks at one byte, neither reaches its own text
        b'<div style="display:none"><img src="h.jpg" alt="ALTH"></div><p>PICK <img class="gone" src="s.jpg"><img class="show" style="display:none" src="r.jpg"></p>'
        b'</body></html>')
SHA = hashlib.sha256(PAGE).hexdigest()


def items(route):
    return [x for u in route['units'] if u.get('kind') != 'image' for x in (u.get('cells') or [u])]


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                cls.route, cls.facts = html_route.prepare(PAGE, 'v.htm', SHA, browser)
                cls.page = sg.page_visibility(PAGE, anchor.Visible(PAGE), browser)
            finally: browser.close()
        cls.scanned = eh.convert(PAGE, 'v.htm', SHA)  # the scanner's reading alone: what the route was before
        cls.texts = {x['text']: x for x in items(cls.route)}

    def held(self, text): x = self.texts[text]; self.assertTrue(x.get('anchor'), text); return x

    def test_what_the_browser_proves_hidden_is_left_out_and_the_shown_text_beside_it_anchors(self):
        self.assertEqual(self.route['status'], 'OK'); self.assertEqual(self.route['page_visibility'], self.page)
        cells = [(x['text'], x['c']) for u in self.route['units'] if u.get('kind') == 'table' for x in u['cells'] if x['text'] in ('VAL835', 'NEXTA')]
        self.assertEqual(cells, [('VAL835', 0), ('NEXTA', 1)])  # the hidden copy no longer runs the next cell into this one
        for text in ('VAL835', 'NEXTA', 'BEFOREB AFTERB', 'CHILDE ENDE', 'REVF million'): self.held(text)
        every = ' '.join(x.get('text') or '' for x in items(self.route))
        for word in ('GONEB', 'LEADE', 'TAILE', 'MIDF'): self.assertNotIn(word, every)

    def test_text_a_sheet_shows_again_is_kept_and_anchored(self):
        for text in ('SHOWNC', 'SHOWND'): self.held(text)
        self.assertEqual(len(self.page['shown']), 3)  # SHOWNC, SHOWND and CELLH: the sheet shows the table again

    def test_what_no_verdict_reaches_keeps_the_scanners_reading(self):
        before = {x['text']: bool(x.get('anchor')) for x in items(self.scanned)}
        for text in ('LITG', 'MISI \xa92024', 'LEFTJ < RIGHTJ'): self.assertIn(text, self.texts); self.assertEqual(bool(self.texts[text].get('anchor')), before[text])  # the tool, as the browser, reads \xa9
        self.assertNotIn('FOSTH', ' '.join(self.texts)); self.assertNotIn('FOSTH', ' '.join(before))  # as before: the tool prints no text from outside a cell
        listed = {PAGE[a:b].strip() for a, b in self.page['unbound']}  # said, by place: the literal, the moved, the misread and the two lone-"<" runs
        self.assertLessEqual({b'LITG', b'FOSTH', b'MISI &copy2024', b'LEFTJ', b'RIGHTJ'}, listed)

    def test_pictures_and_their_records_are_the_scanners(self):
        pics = lambda r: [{k: u.get(k) for k in ('src', 'alt', 'anchor', 'link_flag', 'cell', 'tag')} for u in r['units'] if u.get('kind') == 'image']
        self.assertEqual(pics(self.route), pics(self.scanned))

    def test_the_route_says_how_its_text_was_read(self):
        self.assertTrue(self.route['route']['settings']['hidden_text'].startswith('left out as the browser proved it '))
        self.assertEqual(self.facts['visibility'], {k: len(v) if isinstance(v, list) else v for k, v in self.page.items()})
        self.assertEqual(self.scanned['route']['settings']['hidden_text'], eh.SETTINGS['hidden_text'])


class Map(unittest.TestCase):
    """The scanner with a verdict in hand (`anchor.Visible(page=...)`), no browser."""
    RAW = b'<style>.x{display:none}</style><p><span style="display:none">HSPILL</span>&amp;VNEAR <span style="display:none">HTWO</span> END</p>'

    def at(self, word): s = self.RAW.index(word); return [s, s + len(word)]

    def given(self, hidden=(), shown=()):
        vis = anchor.Visible(self.RAW, page={'hidden': list(hidden), 'shown': list(shown), 'unproven': 0, 'unbound': 0}); return vis, eh.named(self.RAW, vis, eh.codes(self.RAW, vis))

    def test_an_empty_map_leaves_out_nothing(self):
        vis, text = self.given(); self.assertFalse(vis.certain); self.assertEqual(vis.browser_hidden, [])
        self.assertEqual(text, eh.named(self.RAW, anchor.Visible(self.RAW), eh.codes(self.RAW, anchor.Visible(self.RAW))))  # the uncertain scan's own reading
        self.assertIn('HSPILL', text); self.assertIn('HTWO', text)

    def test_a_partial_map_leaves_out_only_what_it_proves_and_never_the_token_beside_it(self):
        vis, text = self.given(hidden=[self.at(b'HSPILL')])
        self.assertEqual(vis.browser_hidden, [tuple(self.at(b'HSPILL'))]); self.assertNotIn('HSPILL', text); self.assertIn('&amp;VNEAR', text); self.assertIn('HTWO', text)
        s, e = self.at(b'HTWO'); vis, text = self.given(hidden=[[s, e - 1]])  # a run that holds the token only in part proves nothing of it
        self.assertEqual(vis.browser_hidden, []); self.assertIn('HTWO', text)

    def test_shown_again_enters_the_search_form_and_a_verdict_never_certifies(self):
        vis, text = self.given(shown=[self.at(b'HTWO')]); self.assertIn('HTWO', vis.flat); self.assertIn('HTWO', text); self.assertFalse(vis.certain)
        self.assertFalse(anchor.Visible(b'<p>plain</p>', page={'hidden': [], 'shown': [], 'unproven': 0, 'unbound': 0}).certain)  # tags and layout stay unproved


class Failures(unittest.TestCase):
    RAW = b'<style>.x{display:none}</style><p>ONE <span style="display:none">HID</span> TWO</p>'; SHA = hashlib.sha256(RAW).hexdigest()

    def test_a_page_whose_visibility_cannot_be_read_keeps_the_scanners_route_and_is_partial(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                with patch.object(sg, 'page_visibility', side_effect=RuntimeError('no visibility')): route, facts = html_route.prepare(self.RAW, 'f.htm', self.SHA, browser)
            finally: browser.close()
        self.assertEqual((route['status'], route['error'], facts['visibility']), ('PARTIAL', "page visibility: RuntimeError('no visibility')", {'error': "RuntimeError('no visibility')"}))
        self.assertEqual([u['text'] for u in route['units']], [u['text'] for u in eh.convert(self.RAW, 'f.htm', self.SHA)['units']])  # nothing unchecked left out
        self.assertNotIn('page_visibility', route)

    def test_a_disconnected_browser_and_operational_errors_propagate(self):
        gone = SimpleNamespace(is_connected=lambda: False)
        with patch.object(sg, 'page_visibility', side_effect=RuntimeError('closed')), self.assertRaises(RuntimeError): html_route.prepare(self.RAW, 'f.htm', self.SHA, gone)
        for error in (OSError('disk'), MemoryError('memory')):
            with self.subTest(error=type(error).__name__), patch.object(sg, 'page_visibility', side_effect=error), self.assertRaises(type(error)):
                html_route.prepare(self.RAW, 'f.htm', self.SHA, SimpleNamespace(is_connected=lambda: True))

    def test_a_style_sheet_the_browser_cannot_read_offline_gives_no_verdict(self):
        body = b'<body><p>BASE <span style="display:none">KEEPVALUE 714</span> END <span class="h">HIDEVALUE</span></p></body></html>'
        sheet = lambda head: b'<!doctype html><html><head>' + head + b'</head>' + body
        missing = {'link': b'<link rel="stylesheet" href="https://style.test/r.css">', 'relative link': b'<LINK REL=StyleSheet HREF=r.css>',
                   'import': b'<style>@import url("https://style.test/r.css");</style>', 'relative import': b"<style>@import 'r.css';</style>"}  # a sheet that may show KEEPVALUE again
        read = {'data link': b'<link rel="stylesheet" href="data:text/css,.h{display:none}">', 'inline': b'<style>.h{display:none}</style>',
                'XBRL schema reference': b'<style>.h{display:none}</style><link:schemaRef xlink:href="s.xsd"/>'}  # nothing out of reach: read as usual
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, head in {**missing, **read}.items():
                    raw = sheet(head); sha = hashlib.sha256(raw).hexdigest()
                    with self.subTest(page=name):
                        route, facts = html_route.prepare(raw, 'f.htm', sha, browser); text = ' '.join(u['text'] for u in route['units'])
                        if name in missing:
                            self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('style sheets the page names cannot be read offline', route['error'])
                            self.assertEqual([u['text'] for u in route['units']], [u['text'] for u in eh.convert(raw, 'f.htm', sha)['units']]); self.assertIn('KEEPVALUE 714', text)
                        else: self.assertEqual((route['status'], text.split()), ('OK', ['BASE', 'END']))  # KEEPVALUE's own display:none and the sheet's rule both proved
            finally: browser.close()

    def test_nothing_the_render_adds_and_no_doubtful_decoding_changes_the_verdict(self):
        pages = {'attribute selector': (b'<style>td[data-g]{display:none}</style><table><tr><td>KEEPVALUE 714</td></tr></table>', 'OK'),  # Root's marker controls: the copy adds no attribute
                 'own data-g': (b'<style>td[data-g="shown"]{display:table-cell}td[data-g="0"]{display:none}</style><table><tr><td data-g="shown">KEEPVALUE 714</td></tr></table>', 'OK'),
                 'ordinary table': (b'<style>.x{display:none}</style><table><tr><td><span style="display:none">HIDE</span>KEEPVALUE 714</td></tr></table>', 'OK'),
                 'cp1252': ('<meta charset="windows-1252"><style>.\xe9{display:none}</style><p><span class="\xe8">KEEPVALUE 714</span> CONTROL</p>'.encode('cp1252'), 'OK'),  # Root's encoding controls, read as the browser reads the bytes
                 'UTF-8 declared cp1252': ('<meta charset="windows-1252"><style>.\xe9{display:none}</style><p><span class="&eacute;">KEEPVALUE 714</span> CONTROL</p>'.encode(), 'OK'),
                 'UTF-8': ('<meta charset="utf-8"><style>.\xe9{display:none}</style><p><span class="\xe8">KEEPVALUE 714</span> CONTROL</p>'.encode(), 'OK'),
                 'UTF-8, no charset named': ('<style>.caf\xe9{display:none}</style><p><span class="caf&#233;">KEEPVALUE 714</span> CONTROL</p>'.encode(), 'OK'),  # OCR's: the browser reads windows-1252; the selector misses
                 'UTF-8 after a byte order mark': (b'\xef\xbb\xbf' + '<style>.\xe9{display:none}</style><p><span class="\xe9">HIDE</span>KEEPVALUE 714 CONTROL</p>'.encode(), 'OK')}  # the mark stays first: UTF-8, the sheet hides HIDE
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, (raw, status) in pages.items():
                    sha = hashlib.sha256(raw).hexdigest()
                    with self.subTest(page=name):
                        route, facts = html_route.prepare(raw, 'f.htm', sha, browser); text = ' '.join(x['text'] for u in route['units'] for x in (u.get('cells') or [u]))
                        self.assertEqual(route['status'], status); self.assertIn('KEEPVALUE 714', text); self.assertNotIn('HIDE', text)
            finally: browser.close()

    def test_the_marks_never_change_how_the_browser_decodes_the_page(self):  # Root: comments pushed a <meta> past the browser's early look
        late = b'<html><head></head><body>' + b'<p>WORD</p>' * 73 + b'<meta charset="%s"><style>.caf\xc3\xa9{display:none}</style><p>BASE <span class="caf&#195;&#169;">KEEPVALUE 714</span> END</p>'
        pages = {'UTF-8 named late': late % b'utf-8', 'windows-1252 named late': late % b'windows-1252',  # read as UTF-8 the rule misses KEEPVALUE; as windows-1252 it hides it
                 'a byte order mark over a <meta>': b'\xef\xbb\xbf' + late % b'windows-1252'}  # the mark wins: UTF-8
        want = {'UTF-8 named late': True, 'windows-1252 named late': False, 'a byte order mark over a <meta>': True}
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, raw in pages.items():
                    with self.subTest(page=name):
                        original = sg._offline_page(browser, None, ('http://x.invalid/', raw))
                        try: original.goto('http://x.invalid/'); shown = 'KEEPVALUE' in original.evaluate('document.body.innerText')  # the browser on the original bytes
                        finally: original.close()
                        route = html_route.prepare(raw, 'f.htm', hashlib.sha256(raw).hexdigest(), browser)[0]
                        self.assertEqual((shown, 'KEEPVALUE 714' in ' '.join(u['text'] for u in route['units']), route['status']), (want[name], want[name], 'OK'))
            finally: browser.close()

    def test_the_page_is_loaded_once_and_stays_the_one_loaded(self):  # Codex: no second copy for a frame, a refresh or a redirect; nothing replaces it
        body = b'<p>STAYS <span class="x" style="display:none">GONE</span></p>'
        pages = {'plain': b'<style>.x{display:inline}</style>' + body, 'child frame': b'<style>.x{display:inline}</style>' + body + b'<iframe src="/"></iframe>',
                 'refresh': b'<meta http-equiv="refresh" content="0">' + body, 'redirect': b'<meta http-equiv="refresh" content="0;url=http://other.invalid/">' + body}
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, raw in pages.items():
                    with self.subTest(page=name):
                        address = 'http://%s.invalid/' % sg.marker_prefix(raw); page = sg._offline_page(browser, [], (address, raw)); loaded = []
                        page.on('requestfinished', lambda r: loaded.append(r.url))
                        try: page.goto(address, wait_until='load'); page.wait_for_timeout(300); still = (page.url, page.evaluate('document.body.innerText'))  # a bounded wait: time for a refresh
                        finally: page.close()
                        self.assertEqual((loaded, still), ([address], (address, 'STAYS')))
                        route, facts = html_route.prepare(raw, 'f.htm', hashlib.sha256(raw).hexdigest(), browser)
                        self.assertEqual((facts['visibility'], ' '.join(u['text'] for u in route['units']).split()), ({'hidden': 1, 'shown': 0, 'unproven': 0, 'unbound': 0}, ['STAYS']))  # the screen step's own render may still race a refresh: its older limit, unchanged (a PARTIAL 'screen step' route)
            finally: browser.close()

    def test_a_certain_file_is_not_read_in_the_browser_first(self):
        raw = b'<p>ONE <span style="display:none">HID</span> TWO</p>'
        vis = anchor.Visible(raw); self.assertEqual(html_route.visibility(raw, vis, None), (vis, None))  # the scan as it is, no browser asked for


if __name__ == '__main__': unittest.main()
