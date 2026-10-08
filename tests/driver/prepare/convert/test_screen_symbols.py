"""A symbol font's code character keeps its meaning beside the text: `source_symbols` records, for every character the page sets in a typeface the
pinned decoder (dingbat-to-unicode 1.0.2) knows, the decoded character and its Unicode name, the raw character and its exact source bytes, and the
units that hold those bytes; the units' text is not touched. A cover page writes `Yes þ No ¨` in Wingdings: `þ` is BALLOT BOX WITH BOLD CHECK.
Never decoded: a name the decoder does not know, a typeface the document redefines (@font-face), a transformed glyph, a character no marker reaches."""
import hashlib
import unittest

from driver.prepare.convert import edgartools_html, html_route
from driver.prepare.convert import screen_grid as sg
from driver.prepare.convert.anchor import Visible

W = lambda t: b'<span style="font-family:Wingdings">' + t + b'</span>'
PAGE = (b'<html><head><style>.wd{font-family:Wingdings} @font-face{font-family:"Webdings";src:url(w.woff)} p.fl::first-letter{font-family:Arial}</style></head><body>'
        b'<p>Q1 Yes ' + W('þ'.encode()) + b' No ' + W('¨'.encode()) + b'</p>'
        b'<p>Yes ' + W('þ'.encode()) + b' twin</p><p>Yes ' + W('þ'.encode()) + b' twin</p>'
        b'<table><tr><td>Large accelerated filer</td><td>' + W(b'o') + b'</td></tr><tr><td>Accelerated filer</td><td>' + W(b'x') + b'</td></tr></table>'
        b'<p>Q2 refs ' + W(b'&#254;&#xFE;&thorn;') + b'</p>'
        b'<p>Q3 kept ' + W('☐'.encode()) + b' <span style="font-family:Symbol">&#183;&#xF0B7;</span> ' + W(b'&#xF0FE;&#xE000;') + b' <span style="font-family:Arial">&#xF0B7;</span>'
        b' <span style="font-family:\'Times New Roman\'">&#xF020;</span></p>'
        b'<p>Q4 names <span style="font-family:&quot;Wingdings 24&quot;">\xc3\xbe</span> <span style="font-family:Wingdings2">\xc3\xbe</span>'
        b' <span style="font-family:&quot;Wingdings, sans-serif&quot;">\xc3\xbe</span> ' + W(b' &nbsp; ') + b'<span style="font-family:Wingdings" title="\xc3\xbe"></span></p>'
        b'<p>Q5 inherited <span style="font-family:Wingdings"><b>x</b></span> <span class="wd">\xc3\xbd</span> <span style="font: 10pt &quot;Wingdings 2&quot;, serif">S</span></p>'
        b'<p>Q6 refused <span style="font-family:Webdings">a</span> <span style="font-family:Wingdings;text-transform:uppercase">x</span>'
        b' <span style="font-family:Wingdings;font-variant:small-caps">x</span></p>'
        b'<div style="display:none"><p>Q7 hidden ' + W('þ'.encode()) + b'</p></div>'
        b'<p class="fl" style="font-family:Wingdings">\xc3\xbe\xc2\xa8</p>'
        b'<p>Q8 look-alikes <!--j:0.0-->' + W(b'<!--j:0.0-->\xc3\xbe') + b' <!--s:0-->' + W(b'<!--s:0-->\xc3\xbe') + b'</p>'
        b'<p>Q9 <span class="t" style="font-family:Arial">x</span></p><script>document.querySelectorAll(".t").forEach(e => e.style.fontFamily = "Wingdings")</script>'
        b'<table>' + W('þ'.encode()) + b'<tr><td>Q10 cell</td></tr></table><table>&#xF0B7;<tr><td>Q11 cell</td></tr></table>'
        b'</body></html>')
JOIN = b'<p>CORP<i>ORATION</i> end <span style="margin-left:80px"><!--j:0.1-->Z</span> <!j:0.0>Y</p>'  # a source comment, and a bogus one, spelled as the gap marks were (Fable's CHECKS_v1 case 4)
SEEN = (b'<p>Q12 shown <span style="display:contents;font-family:Wingdings">\xc3\xbe</span> zero <span style="font-family:Wingdings;font-size:0">\xc3\xbe</span>'
        b' clear <span style="font-family:Wingdings;opacity:0">\xc3\xbe</span></p>')  # no style sheet: a scan the units can be anchored in


def at(raw, before, n=1):  # the source bytes of the character that follows the n-th `before`
    i = -1
    for _ in range(n): i = raw.index(before, i + 1)
    s = i + len(before); e = raw.index(b';', s) + 1 if raw[s:s + 1] == b'&' else s + len(raw[s:s + 4].decode('utf-8', 'ignore')[:1].encode())
    return s, e


class Route(unittest.TestCase):
    """The whole HTML route in Chrome (offline; playwright is required: a missing install fails, never skips)."""
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                cls.route, cls.facts = html_route.prepare(PAGE, 'symbols.htm', hashlib.sha256(PAGE).hexdigest(), browser)
                cls.seen = html_route.prepare(SEEN, 'seen.htm', hashlib.sha256(SEEN).hexdigest(), browser)[0]
                v = Visible(JOIN); cls.unit = {'id': 'u', 'kind': 'text', 'text': 'CORP ORATION end Z Y', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(JOIN)}}  # the tool's added space
                gaps = sg.gaps_of(v, [cls.unit]); k = sg.marker_prefix(JOIN); marked, _ = sg.tag_cells(JOIN, v, gaps, prefix=k)
                cls.joined = sg.join(gaps, sg.measure(marked, browser, k)[1], v)
            finally: browser.close()
        cls.sym = cls.route['source_symbols']; cls.by = {(r['at']['byte_start'], r['at']['byte_end_exclusive']): r for r in cls.sym['records']}
        cls.items = {(u['id'], None): u for u in cls.route['units']}
        cls.items.update({(u['id'], c['anchor']['byte_start']): c for u in cls.route['units'] for c in u.get('cells') or [] if isinstance(c.get('anchor'), dict)})

    def rec(self, before, n=1): return self.by[at(PAGE, before, n)]

    def owner_text(self, r): return [self.items[(o['unit'], o.get('cell'))]['text'] for o in r['owners']]

    def test_a_yes_no_pair_is_decoded_with_names_beside_the_raw_text_and_its_owner(self):
        self.assertTrue(self.sym['read'])
        yes, no = self.rec(b'Q1 Yes <span style="font-family:Wingdings">'), self.rec(b'</span> No <span style="font-family:Wingdings">')
        self.assertEqual((yes['raw'], yes['status'], yes['unicode']['name'], yes['unicode']['code_point']), ('þ', 'decoded', 'BALLOT BOX WITH BOLD CHECK', 'U+1F5F9'))
        self.assertEqual((no['raw'], no['unicode']['name']), ('¨', 'LIGHT WHITE SQUARE'))
        self.assertEqual(self.owner_text(yes), ['Q1 Yes þ No ¨']); self.assertEqual(yes['owners'], no['owners'])  # the raw text stays as the source writes it

    def test_twins_bind_to_their_own_bytes_and_cells_to_their_own_cell(self):
        a, b = self.rec(b'<p>Yes <span style="font-family:Wingdings">', 1), self.rec(b'<p>Yes <span style="font-family:Wingdings">', 2)
        self.assertNotEqual(a['owners'], b['owners']); self.assertEqual([len(a['owners']), len(b['owners'])], [1, 1])
        o, x = self.rec(b'Large accelerated filer</td><td><span style="font-family:Wingdings">'), self.rec(b'Accelerated filer</td><td><span style="font-family:Wingdings">')
        self.assertEqual((o['unicode']['name'], x['unicode']['name']), ('MEDIUM WHITE SQUARE', 'X IN A RECTANGLE BOX'))
        self.assertEqual([self.owner_text(o), self.owner_text(x)], [['o'], ['x']]); self.assertIn('cell', o['owners'][0])

    def test_character_references_are_recorded_at_their_own_bytes(self):
        base = PAGE.index(b'Q2 refs <span style="font-family:Wingdings">') + len(b'Q2 refs <span style="font-family:Wingdings">')
        for s, e in ((base, base + 6), (base + 6, base + 12), (base + 12, base + 19)):
            with self.subTest(ref=PAGE[s:e]): r = self.by[(s, e)]; self.assertEqual((r['raw'], r['unicode']['name']), ('þ', 'BALLOT BOX WITH BOLD CHECK'))

    def test_unicode_is_kept_private_use_is_decoded_only_in_a_decoder_typeface_else_unknown(self):
        q = PAGE.index(b'Q3 kept')
        got = [(PAGE[r['at']['byte_start']:r['at']['byte_end_exclusive']], r['status'], (r.get('unicode') or {}).get('name')) for k, r in sorted(self.by.items()) if q < k[0] < PAGE.index(b'Q4 names')]
        self.assertEqual(got, [('☐'.encode(), 'unicode_kept', None), (b'&#183;', 'decoded', 'BULLET'), (b'&#xF0B7;', 'decoded', 'BULLET'), (b'&#xF0FE;', 'decoded', 'BALLOT BOX WITH BOLD CHECK'),
                               (b'&#xE000;', 'unknown_code', None), (b'&#xF0B7;', 'unknown_pua', None), (b'&#xF020;', 'unknown_pua', None)])

    def test_names_the_decoder_does_not_know_white_space_and_attribute_text_have_no_record_but_a_no_break_space_is_a_code(self):
        q, r = PAGE.index(b'Q4 names'), PAGE.index(b'Q5 inherited'); got = [(PAGE[a:b], self.by[(a, b)]['unicode']['name']) for a, b in self.by if q < a < r]
        self.assertEqual(got, [(b'&nbsp;', 'BLACK VERY SMALL SQUARE')])  # Wingdings 160 (L2/12-368 1160); the ASCII spaces around it are white space

    def test_inherited_class_and_shorthand_families_are_the_browsers(self):
        b, c, s = self.rec(b'<b>'), self.rec(b'<span class="wd">'), self.rec(b'serif">')
        self.assertEqual([(x['typeface'], x['unicode']['name']) for x in (b, c, s)], [('WINGDINGS', 'X IN A RECTANGLE BOX'), ('WINGDINGS', 'BALLOT BOX WITH BOLD SCRIPT X'), ('WINGDINGS 2', 'BALLOT BOX WITH LIGHT X')])

    def test_a_first_letter_or_line_set_another_way_is_unresolved(self):
        for n in (1, 2):
            with self.subTest(n=n): r = self.rec(b'<p class="fl" style="font-family:Wingdings">' + ('þ'.encode() if n == 2 else b''), 1); self.assertEqual((r['status'], r['why']), ('unresolved', 'first letter or line'))

    def test_a_source_comment_spelled_as_a_gap_mark_does_not_move_a_measured_gap(self):
        self.assertEqual((self.joined, self.unit['text']), (1, 'CORPORATION end Z Y'))

    def test_a_redefined_typeface_and_a_transformed_glyph_are_unresolved(self):
        for before, why in ((b'font-family:Webdings">', 'font-face'), (b'text-transform:uppercase">', 'transform'), (b'font-variant:small-caps">', 'transform')):
            with self.subTest(why=why): r = self.rec(before); self.assertEqual((r['status'], r['why'], r.get('unicode')), ('unresolved', why, None))

    def test_visibility_comes_from_the_glyphs_boxes_hidden_and_unproven_have_no_owner(self):
        r = self.rec(b'Q7 hidden <span style="font-family:Wingdings">'); self.assertEqual((r['visibility'], r['owners'], r['status']), ('hidden', None, 'decoded'))
        by = {(x['at']['byte_start'], x['at']['byte_end_exclusive']): x for x in self.seen['source_symbols']['records']}
        c = by[at(SEEN, b'display:contents;font-family:Wingdings">')]; self.assertNotIn('visibility', c); self.assertEqual(c['owners'], [{'unit': self.seen['units'][0]['id']}])  # checkVisibility says hidden; its box is there
        z = by[at(SEEN, b'font-size:0">')]; self.assertEqual((z['visibility'], z['owners']), ('unproven', None))  # a box of no area
        o = by[at(SEEN, b'opacity:0">')]; self.assertEqual((o['visibility'], o['owners']), ('hidden', None))

    def test_source_comments_that_look_like_marks_bind_nothing_else(self):
        for before in (b'<!--j:0.0-->', b'<!--s:0-->'):  # the second of each stands inside the span, right before the glyph
            with self.subTest(before=before): r = self.rec(before, 2); self.assertEqual((r['status'], len(r['owners'])), ('decoded', 1))
        q = PAGE.index(b'Q8'); self.assertEqual(len([k for k in self.by if q < k[0] < PAGE.index(b'Q9')]), 2)

    def test_a_document_script_does_not_run(self):
        q = PAGE.index(b'Q9'); self.assertEqual([k for k in self.by if q < k[0] < PAGE.index(b'</script>')], [])

    def test_a_span_the_parser_moves_out_of_a_table_keeps_its_mark_but_no_unit_holds_it(self):
        r = self.by[at(PAGE, b'<table><span style="font-family:Wingdings">')]; self.assertEqual((r['status'], r['unicode']['name'], r['owners']), ('decoded', 'BALLOT BOX WITH BOLD CHECK', None))

    def test_text_the_parser_moves_away_from_its_mark_is_unresolved_without_owner(self):
        r = self.by[at(PAGE, b'</table><table>')]; self.assertEqual((r['status'], r['why'], r['owners']), ('unresolved', 'unbound', None))

    def test_units_keep_their_text_ids_kinds_and_anchors(self):
        bare = edgartools_html.convert(PAGE, 'symbols.htm', hashlib.sha256(PAGE).hexdigest(), vis=Visible(PAGE, page=self.route['page_visibility']))  # the conversion the route was made by (the page holds a script: the browser read its visibility)
        shape = lambda r: [(u['id'], u['kind'], u.get('anchor')) for u in r['units']]
        self.assertEqual(shape(self.route), shape(bare))
        self.assertTrue(any('Q1 Yes þ No ¨' == u.get('text') for u in self.route['units']))


class Unit(unittest.TestCase):
    def test_the_mark_prefix_is_one_the_source_nowhere_writes(self):
        raw = b'<p>x</p>'; k = sg.marker_prefix(raw); self.assertEqual(k, sg.marker_prefix(raw)); self.assertNotIn(k[1:].encode(), raw)
        hostile = raw + k[1:].encode(); self.assertNotIn(sg.marker_prefix(hostile)[1:].encode(), hostile)

    def test_a_page_that_cannot_be_measured_keeps_the_content_and_says_the_symbols_went_unread(self):
        class Browser:
            def new_page(self, **k): raise RuntimeError('no page')
            def is_connected(self): return True
        raw = b'<p>Yes <span style="font-family:Wingdings">\xc3\xbe</span></p>'; route = edgartools_html.convert(raw, 'f.htm', hashlib.sha256(raw).hexdigest())
        got = sg.step(raw, route, Browser()); self.assertIn('error', got)
        self.assertEqual(route['source_symbols'], {'read': False, 'error': "RuntimeError('no page')"})  # html_route also marks the route PARTIAL with the step's error


class Binding(unittest.TestCase):
    """Root's binding probes (ROOT_FONT_BINDING_V1): a reference read as two characters, a byte that is not UTF-8, a <noscript> the scan skips."""
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pages = {'combining': b'<p><span style="font-family:Wingdings">&NotEqualTilde; x</span></p>', 'cp1252': b'<p><span style="font-family:Wingdings">\xfe</span></p>',
                     'noscript': b'<noscript><p><span style="font-family:Wingdings">\xc3\xbe</span></p></noscript><p>shown</p>',
                     'legacy': b'<p><span style="font-family:Wingdings">A &copy x</span></p>'}  # no ';': the browser reads \u00a9, the scanner five characters
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try: cls.got = {k: html_route.prepare(v, k, hashlib.sha256(v).hexdigest(), browser)[0]['source_symbols'] for k, v in cls.pages.items()}
            finally: browser.close()

    def test_a_reference_read_as_two_characters_is_one_glyph_kept_as_unicode(self):
        r = self.got['combining']['records']; self.assertEqual([(x['raw'], x['status']) for x in r], [('\u2242\u0338', 'unicode_kept'), ('x', 'decoded')])

    def test_a_byte_that_is_not_utf8_is_unresolved_never_kept_unicode(self):
        r = self.got['cp1252']['records']; self.assertEqual([(x['raw'], x['status'], x['why'], x['bytes']) for x in r], [(None, 'unresolved', 'not UTF-8', 'fe')])

    def test_a_reference_the_scanner_and_the_browser_read_apart_is_unbound_with_its_source_text(self):
        self.assertEqual([(x['raw'], x['status'], x['why'], x['owners']) for x in self.got['legacy']['records']], [('A &copy x', 'unresolved', 'unbound', None)])

    def test_noscript_the_scan_skips_is_said_unread(self):
        g = self.got['noscript']; self.assertEqual([u['why'] for u in g['unread']], ['noscript']); self.assertEqual(g['records'], [])


class SymbolFailure(unittest.TestCase):
    def test_a_failed_symbol_reading_keeps_the_measured_geometry_and_says_why(self):
        from unittest.mock import patch
        from playwright.sync_api import sync_playwright
        raw = b'<table><tr><td>a</td><td>b</td></tr></table><p>Yes <span style="font-family:Wingdings">\xc3\xbe</span></p>'
        with sync_playwright() as pw, patch.object(sg, 'SYMBOLS_JS', '(p) => { throw new Error("no symbols"); }'):
            browser = pw.chromium.launch()
            try: route, facts = html_route.prepare(raw, 's.htm', hashlib.sha256(raw).hexdigest(), browser)
            finally: browser.close()
        self.assertEqual((route['status'], route['source_symbols']['read'], facts['screen']['cells_measured']), ('PARTIAL', False, 2)); self.assertIn('no symbols', route['error'])


class Faults(unittest.TestCase):
    """Root's probes (root_font_faults.py), ported unchanged: operational faults escape both browser evaluations, the route untouched; a document
    problem in either is an explicit read: false and the step's error (PARTIAL)."""
    class Browser:
        def __init__(self, error, at): self.error, self.at, self.closed = error, at, False
        def is_connected(self): return True
        def new_page(self, **kwargs):
            owner = self
            class Page:
                count = 0
                def route(self, *args): pass
                def set_content(self, *args, **kwargs): pass
                def close(self): owner.closed = True
                def evaluate(self, *args):
                    self.count += 1
                    if self.count == owner.at: raise owner.error('injected fault')
                    return {'cells': [], 'boxes': {}}
            return Page()

    def run_fault(self, error):
        raw = b'<p style="font-family:Wingdings">x</p>'
        for stage in (1, 2):
            with self.subTest(stage=stage):
                route = {'sha256': hashlib.sha256(raw).hexdigest(), 'units': [], 'route': {'name': 'probe'}}; browser = self.Browser(error, stage)
                with self.assertRaises(error): sg.step(raw, route, browser)
                self.assertTrue(browser.closed); self.assertNotIn('source_symbols', route)

    def test_storage_fault(self):
        from driver.prepare.get.acquire import StorageError
        self.run_fault(StorageError)

    def test_io_fault(self): self.run_fault(OSError)

    def test_memory_fault(self): self.run_fault(MemoryError)

    def test_dependency_fault(self): self.run_fault(ImportError)

    def test_document_problem_is_explicit_partial(self):
        raw = b'<p>x</p>'
        for stage in (1, 2):
            with self.subTest(stage=stage):
                route = {'sha256': hashlib.sha256(raw).hexdigest(), 'units': [], 'route': {'name': 'probe'}}; browser = self.Browser(ValueError, stage)
                result = sg.step(raw, route, browser)
                self.assertIn('error', result); self.assertFalse(route['source_symbols']['read']); self.assertTrue(browser.closed)


class WhiteSpace(unittest.TestCase):
    """Root's probes (root_font_whitespace_probe.py): only the white space CSS collapses is white space; a no-break space or U+0085 set in a
    decoder typeface is a code the decoder reads (literal, named and F000 forms alike)."""
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.got = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for body in ('\u00a0', '&nbsp;', '\u0085', '&#xF0A0;', ' ', ' \t '):
                    raw = ('<p style="font-family:Wingdings">' + body + '</p>').encode(); route = {'sha256': hashlib.sha256(raw).hexdigest(), 'units': [], 'route': {'name': 'probe'}}
                    sg.step(raw, route, browser); cls.got[body] = [(r['status'], (r.get('unicode') or {}).get('name')) for r in route['source_symbols']['records']]
            finally: browser.close()

    def test_no_break_space_named_literal_and_f000_and_u0085_are_decoded(self):
        for body, name in (('\u00a0', 'BLACK VERY SMALL SQUARE'), ('&nbsp;', 'BLACK VERY SMALL SQUARE'), ('&#xF0A0;', 'BLACK VERY SMALL SQUARE'), ('\u0085', 'DINGBAT CIRCLED SANS-SERIF DIGIT FIVE')):
            with self.subTest(body=body): self.assertEqual(self.got[body], [('decoded', name)])

    def test_ordinary_white_space_stays_harmless(self):
        self.assertEqual((self.got[' '], self.got[' \t ']), ([], []))


class Marks(unittest.TestCase):
    def test_a_mark_never_found_and_a_mark_whose_text_moved_are_said_apart(self):
        raw = b'<p><span style="font-family:Wingdings">\xc3\xbe</span></p>'; vis = Visible(raw); runs, _ = sg.symbol_runs(raw, vis)
        k = next(str(i) for i, r in enumerate(runs) if r[1][0][0] == raw.index(b'\xc3\xbe'))
        lost = sg.symbols(raw, vis, runs, {'marks': {}, 'faces': [], 'plain': ''}, []); moved = sg.symbols(raw, vis, runs, {'marks': {k: None}, 'faces': [], 'plain': ''}, [])
        self.assertEqual([r['why'] for r in lost], ['mark not found']); self.assertEqual([r['why'] for r in moved], ['unbound'])


if __name__ == '__main__':
    unittest.main()
