"""Measuring a page must not change it (Root, render-mark boundary, Oct 12). The screen step named each table cell by adding an attribute
(data-g="n") to its start tag: a sheet that selects attributes then styled the measured page differently from the original - a presence
or absence selector, or the source's own attribute of that name - and the route recorded the wrong style and place with status OK. A cell is
now named by a prefixed comment right after its start tag's end (the scanner's own tag end, never a '>' search): no selector sees a comment,
and :empty / structural selectors ignore it. Truths: the original page's own computed style and text boxes, read in the same browser with
no marks at all. Invented sources."""
import hashlib
import unittest

from driver.prepare.convert import anchor, html_route, screen_grid

STYLE = 'td{padding:2px}'
CASES = {  # name -> (style, body); every case compared against the unmarked original
    'presence_selector': ('td[data-g]{font-weight:900;color:#ee3311;padding-left:80px}', '<table><tr><td>Cedar</td><td>418</td></tr></table>'),
    'absence_selector': ('td:not([data-g]){font-style:italic}', '<table><tr><td>Cedar</td><td>418</td></tr></table>'),
    'original_attribute': ('td[data-g="source"]{font-weight:900}', '<table><tr><td data-g="source">Cedar</td><td>418</td></tr></table>'),
    'quoted_bracket': ('td[title="a>b"]{font-weight:900}', '<table><tr><td title="a>b" class="q">Cedar</td><td>418</td></tr></table>'),
    'empty_and_structural': ('td:empty{width:200px}td:first-child{font-style:italic}', '<table><tr><td>Cedar</td><td></td><td>418</td></tr></table>'),
    'nested_and_omitted_ends': ('td td{font-weight:900}', '<table><tr><td>Outer<table><tr><td>Inner</td></tr></table><td>418</table>'),
    'row_groups': ('tfoot td{font-style:italic}', '<table><tfoot><tr><td>Total 9</td></tr></tfoot><tbody><tr><td>Cedar</td><td>418</td></tr></tbody></table>'),
    'control_class': ('td.native{font-weight:900;color:#ee3311}', '<table><tr><td class="native">Cedar</td><td>418</td></tr></table>'),
    'parent_selector': ('table:has([data-g]){direction:rtl}', '<table><tr><td>North</td><td>South</td></tr><tr><td>418</td><td>627</td></tr></table>'),  # Root's relationship control
    'control_rtl': ('table{direction:rtl}', '<table><tr><td>North</td><td>South</td></tr><tr><td>418</td><td>627</td></tr></table>'),  # its ordinary positive: drawn right to left
}
ORIGINAL = """() => { const out = {}; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) { if (!n.data.trim()) continue; const cs = getComputedStyle(n.parentElement), r = document.createRange(); r.selectNodeContents(n);
    const b = r.getBoundingClientRect(); out[n.data] = {weight: cs.fontWeight, font_style: cs.fontStyle, color: cs.color, x: b.left, y: b.top}; }
  return out; }"""


def page(style, body): return ('<!doctype html><html><head><meta charset="utf-8"><style>%s%s</style></head><body>%s</body></html>' % (STYLE, style, body)).encode()


class RenderMarks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def original(self, raw):  # the page itself, unmarked, at the same window the screen step uses
        p = self.browser.new_page(viewport={'width': 1400, 'height': 1000})
        try: p.set_content(raw.decode()); return p.evaluate(ORIGINAL)
        finally: p.close()

    def test_the_measured_page_is_the_original(self):
        for name, (style, body) in CASES.items():
            with self.subTest(case=name):
                raw = page(style, body); want = self.original(raw)
                route = html_route.prepare(raw, 'invented/%s.htm' % name, hashlib.sha256(raw).hexdigest(), self.browser, screen_grid.Source('doc.htm', {'doc.htm': raw}))[0]
                self.assertEqual(route['status'], 'OK'); recs = route['source_style']['records']
                got = {raw[r['at']['byte_start']:r['at']['byte_end_exclusive']].decode(): r for r in recs}
                self.assertEqual(sorted(got), sorted(want))
                for text, w in want.items():
                    r = got[text]
                    self.assertEqual((r['weight'], r['font_style'], r['color']), (w['weight'], w['font_style'], w['color']), text)
                    self.assertAlmostEqual(r['boxes'][0][0], w['x'], delta=0.5, msg=text); self.assertAlmostEqual(r['boxes'][0][1], w['y'], delta=0.5, msg=text)
                for u in route['units']:  # each row's cells in the column order the original page draws them
                    rows = {}
                    for c in u.get('cells') or []:
                        if c.get('text') in want: rows.setdefault(c['r'], []).append(c)
                    for cells in rows.values(): self.assertEqual([c['text'] for c in sorted(cells, key=lambda c: c['c'])], [c['text'] for c in sorted(cells, key=lambda c: want[c['text']]['x'])])

    def test_the_cell_mark_is_a_comment_after_the_start_tag(self):
        raw = b'<table><tr><td title="a>b">x</td><td>y</td></tr></table>'; k = screen_grid.marker_prefix(raw)
        marked, spans = screen_grid.tag_cells(raw, prefix=k)
        self.assertEqual(marked, raw.replace(b'"a>b">x', b'"a>b"><!--%sg:0-->x' % k.encode()).replace(b'<td>y', b'<td><!--%sg:1-->y' % k.encode()))  # the source's own bytes, a comment added
        self.assertEqual(spans, [(raw.index(b'<td title'), raw.index(b'</td>') + 5), (raw.index(b'<td>y'), raw.rindex(b'</td>') + 5)])
        self.assertEqual(screen_grid.tag_cells(raw, prefix=k, cells=False), (raw, []))

    def test_only_native_html_cells_are_named(self):  # Fable's guard addendum: in SVG/MathML the parser makes <td>/<th> foreign elements, no cells
        native = "() => Array.from(document.querySelectorAll('*')).filter(e => e instanceof HTMLTableCellElement).map(e => e.firstChild ? e.firstChild.textContent : '')"
        for name, body, want in (('svg_td_th', '<table><tr><td>A<svg><td>X</td><th>Y</th></svg></td></tr></table>', ['A']),
                                 ('math_td_th', '<table><tr><td>A<math><td>X</td><th>Y</th></math></td></tr></table>', ['A']),
                                 ('table_breaks_out_of_svg', '<table><tr><td>A<svg><table><tr><td>X</td></tr></table></svg></td></tr></table>', ['A', 'X']),  # the parser leaves foreign content for <table>
                                 ('html_table_in_foreignObject', '<table><tr><td>A<svg width="200" height="60"><foreignObject width="200" height="60"><table><tr><td>F</td></tr></table></foreignObject></svg></td></tr></table>', ['A', 'F'])):
            with self.subTest(case=name):
                raw = page('', body); p = self.browser.new_page()
                try: p.set_content(raw.decode()); self.assertEqual(p.evaluate(native), want)  # the original's own cells
                finally: p.close()
                vis = anchor.Visible(raw); k = screen_grid.marker_prefix(raw); marked, spans = screen_grid.tag_cells(raw, vis, (), (), k)
                tables, _, _ = screen_grid.measure(marked, self.browser, k, raw=raw, source=screen_grid.Source('doc.htm', {'doc.htm': raw}))
                named = sorted(c['g'] for cells in tables.values() for c in cells)
                self.assertEqual([raw[spans[g][0]:spans[g][1]].split(b'>', 1)[1][:1].decode() for g in named], want)  # exactly the native cells, each by its own source cell


if __name__ == '__main__':
    unittest.main()
