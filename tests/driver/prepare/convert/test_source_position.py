"""Positioned inline boxes keep their native evidence in `source_inline`: an inline box whose computed position is not static is admitted beside
sup/sub and vertical-align boxes, and every admitted ancestor that is positioned carries the browser's raw computed position, top, bottom, left and
right (static ancestors stay compact). Evidence only: no displacement is measured or judged, nothing is read as a footnote. Expected values are the
browser's own getComputedStyle readings of the same element, or literals read off the real source slices. Runs Chrome (offline)."""
import copy
import hashlib
import unittest

from driver.prepare import reconstruct
from driver.prepare.convert import html_route

# BXP q42025supplemental.htm (sha256 1c54918d971bb59d3bc45aefb26fc35d4aae84cf8c91f6431f7c829b2c62209f): bytes 60183-60812, a table row whose
# footnote mark 2 (byte 60579) is <font ... position:relative;top:-2.8pt;vertical-align:baseline>; bytes 82008-82576, the footnote line, mark 1 at 82235.
ROW = b'<tr><td colspan="3" style="padding:2px 1pt;text-align:left;vertical-align:bottom"><div><font style="color:#000000;font-family:\'Arial\',sans-serif;font-size:8pt;font-weight:400;line-height:100%">Consolidated Market Capitalization </font><font style="color:#000000;font-family:\'Arial\',sans-serif;font-size:5.2pt;font-weight:400;line-height:100%;position:relative;top:-2.8pt;vertical-align:baseline">2</font></div></td><td colspan="3" style="padding:2px 1pt;text-align:left;vertical-align:bottom"><font style="color:#000000;font-family:\'Arial\',sans-serif;font-size:8pt;font-weight:400;line-height:100%">$28.5 billion</font></td></tr>'
NOTE = b'<div style="margin-top:2pt;padding-left:4.5pt;text-indent:-4.5pt"><font style="color:#000000;font-family:\'Arial\',sans-serif;font-size:5.2pt;font-weight:400;line-height:120%;position:relative;top:-2.8pt;vertical-align:baseline">1</font><font style="color:#000000;font-family:\'Arial\',sans-serif;font-size:8pt;font-weight:400;line-height:120%;padding-left:1.61pt">Common units and LTIP units are units of limited partnership interest in Boston Properties Limited Partnership, the entity through which the Company conducts substantially all of its business.  </font></div>'
FIELDS = ('tag', 'display', 'vertical_align', 'position', 'top', 'bottom', 'left', 'right')
CASES = (b'<p>a<span data-case="A" style="position:relative;top:-0.4em">A</span> b<span data-case="B" style="position:relative;top:0.4em">B</span>'
         b' c<span data-case="C" style="position:relative;bottom:3px">C</span> d<span data-case="D" style="position:relative;top:0">D</span>'
         b' e<span data-case="E" style="position:static;top:-5px">E</span> f<span data-case="F" style="position:relative">F</span>'
         b' g<sup data-case="G">G</sup> h<span style="position:relative;top:-4px"><span data-case="H" style="position:relative;top:4px">H</span></span>'
         b' i<span data-case="I" style="position:relative;top:calc(-20% - 1px)">I</span> j<span data-case="J" style="position:relative;inset-block-start:-3px">J</span>'
         b' m<span data-case="M" style="position:sticky;top:2px">M</span> n<span data-case="N" style="position:absolute;top:-3px">N</span>'
         b' o<span data-case="O" style="position:fixed;top:0">O</span> p<sup data-case="P" style="position:relative;top:-1px">P</sup>'
         b' q<sub data-case="Q" style="position:relative;left:2px">Q</sub> r<span data-case="R" style="position:relative;left:3px;right:1px">R</span></p>'
         b'<p style="writing-mode:vertical-rl">s<span data-case="S" style="position:relative;inset-block-start:-3px;inset-inline-end:1px">S</span></p>'
         b'<div data-case="K" style="position:relative;top:-3px">K</div><p>l<span data-case="L" style="display:inline-block;transform:translateY(-3px)">L</span></p>'
         b'<p>z<span style="position:relative;top:-1px">2</span> w<span style="position:relative;top:-2px">1</span> v<span style="position:relative;top:-1px">2</span></p>')
PAGES = {'row': b'<table>' + ROW + b'</table>', 'note': NOTE, 'cases': CASES}
NATIVE_JS = """() => Object.fromEntries([...document.querySelectorAll('[data-case]')].map(e => { const c = getComputedStyle(e), p = e.parentElement, q = getComputedStyle(p);
  return [e.dataset.case, {tag: e.localName, display: c.display, vertical_align: c.verticalAlign, position: c.position, top: c.top, bottom: c.bottom, left: c.left, right: c.right,
          parent: {tag: p.localName, display: q.display, vertical_align: q.verticalAlign, position: q.position, top: q.top, bottom: q.bottom, left: q.left, right: q.right}}]; }))"""
POSITIONED = 'ABCDFHIJMRS'  # inline boxes whose computed position is not static (zero and unset insets included: evidence, not displacement)
NEGATIVE = 'EKLNO'  # static top, a positioned block, a transform, absolute and fixed (blockified)


class SourcePosition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                cls.routes = {k: html_route.prepare(v, k + '.htm', hashlib.sha256(v).hexdigest(), browser)[0] for k, v in PAGES.items()}
                page = browser.new_page(java_script_enabled=False)
                try:
                    page.set_content(CASES.decode()); cls.native = page.evaluate(NATIVE_JS)
                finally: page.close()
            finally: browser.close()

    def at(self, case):  # the records at the one character inside the element marked data-case
        i = CASES.index(b'data-case="' + case.encode() + b'"'); i = CASES.index(b'>', i) + 1
        return [r for r in self.routes['cases']['source_inline']['records'] if r['at']['byte_start'] <= i < r['at']['byte_end_exclusive']]

    def reading(self, case, parent=False):
        e = self.native[case]['parent'] if parent else self.native[case]
        return {k: e[k] for k in FIELDS}

    def test_slices_are_the_source_bytes(self):
        self.assertEqual((hashlib.sha256(ROW).hexdigest(), hashlib.sha256(NOTE).hexdigest()),
                         ('854962bc7f49ed8155a1bbd2fbb4dcc22b97fb0048bd2d87ad818b6fc4bc8faa', 'e6cc446c2b49ee1ed6101aafaada6aeaef911e1065ed010cae1e225b2adac24b'))

    def test_real_marks_keep_their_extent_insets_and_owner(self):
        mark = {'tag': 'font', 'display': 'inline', 'vertical_align': 'baseline', 'position': 'relative', 'top': '-3.73333px', 'bottom': '3.73333px', 'left': '0px', 'right': '0px'}
        self.assertEqual(self.routes['row']['source_inline']['records'],
                         [{'at': {'byte_start': 403, 'byte_end_exclusive': 404}, 'raw': '2', 'ancestors': [mark], 'owners': [{'unit': 't0', 'cell': 200, 'text_at': [[35, 36]]}]}])
        cell = next(c['text'] for c in self.routes['row']['units'][0]['cells'] if (c.get('anchor') or {}).get('byte_start') == 200)
        self.assertEqual((cell, cell[35:36]), ('Consolidated Market Capitalization 2', '2'))
        self.assertEqual(self.routes['note']['source_inline']['records'],
                         [{'at': {'byte_start': 227, 'byte_end_exclusive': 228}, 'raw': '1', 'ancestors': [mark], 'owners': [{'unit': 'u0', 'text_at': [[0, 1]]}]}])
        text = self.routes['note']['units'][0]['text']
        self.assertEqual((text[:40], text[0:1]), ('1 Common units and LTIP units are units ', '1'))

    def test_positioned_inline_boxes_carry_the_browser_readings(self):
        for case in POSITIONED:
            with self.subTest(case=case):
                recs = self.at(case); self.assertEqual(len(recs), 1)
                want = [self.reading(case)] + ([self.reading(case, parent=True)] if case == 'H' else [])  # nested: each element's own reading, nearest first
                self.assertEqual(recs[0]['ancestors'], want)

    def test_boundaries_get_no_record(self):
        for case in NEGATIVE:
            with self.subTest(case=case): self.assertEqual(self.at(case), [])
        self.assertEqual([self.native[c]['display'] for c in 'NO'], ['block', 'block'])  # absolute and fixed are blockified by the browser

    def test_sup_and_sub_add_fields_only_when_positioned(self):
        self.assertEqual(self.at('G')[0]['ancestors'], [{'tag': 'sup', 'display': 'inline', 'vertical_align': 'super'}])
        for case in 'PQ':
            with self.subTest(case=case): self.assertEqual(self.at(case)[0]['ancestors'], [self.reading(case)])

    def test_repeated_marks_in_reversed_order_bind_by_their_own_bytes(self):
        recs = [r for r in self.routes['cases']['source_inline']['records'] if r['raw'] in ('1', '2')]
        tail = CASES[CASES.rindex(b'<p>z'):]; base = len(CASES) - len(tail)
        starts = [base + i for i in (tail.index(b'>2<') + 1, tail.index(b'>1<') + 1, tail.rindex(b'>2<') + 1)]
        self.assertEqual([(r['raw'], r['at']['byte_start'], r['ancestors'][0]['top']) for r in recs], [('2', starts[0], '-1px'), ('1', starts[1], '-2px'), ('2', starts[2], '-1px')])
        unit = next(u for u in self.routes['cases']['units'] if u['text'].startswith('z2'))
        self.assertEqual([unit['text'][a:b] for r in recs for o in r['owners'] for a, b in o['text_at']], ['2', '1', '2'])
        self.assertEqual(len({tuple(map(tuple, o['text_at'])) for r in recs for o in r['owners']}), 3)

    def test_reconstruction_carries_the_records_and_rejects_damage(self):
        E = self.routes['cases']; R = reconstruct.readback(E); self.assertEqual((reconstruct.preserved(E, R), reconstruct.annotations(E, R)), ([], []))
        D = copy.deepcopy(R); D['source_inline']['records'][0]['ancestors'][0]['top'] = 'auto'; self.assertNotEqual(reconstruct.preserved(E, D), [])
        D = copy.deepcopy(R)
        def drop(x):
            if isinstance(x, dict):
                if 'source_inline' in x.get('attached', {}): x['attached']['source_inline'] = x['attached']['source_inline'][1:]; return True
                return any(drop(v) for v in x.values())
            return isinstance(x, list) and any(drop(v) for v in x)
        self.assertTrue(drop(D['sequence'])); self.assertNotEqual(reconstruct.preserved(E, D), [])


if __name__ == '__main__':
    unittest.main()
