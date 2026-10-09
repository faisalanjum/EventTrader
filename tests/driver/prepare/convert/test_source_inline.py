"""Raised and lowered source text keeps its evidence beside the route: `source_inline` records, for each source run the page sets under a sup or sub
element or an inline box whose computed vertical-align is not baseline, that evidence nearest-first, the run's exact bytes and, where it shows and
its owners read it whole, the code-point ranges of their final text it stands at. The year cell `[______],2023<SUP>13</SUP>` (tm2323493d1_ex10-2,
superscript_meaning_20261009) is told from a literal `202313`; no text changes, nothing is read as a footnote or an exponent, no position is measured.
Expectations are the controls recorded before this field existed (root_design_review NATIVE_CONTROLS.json, OCR's DESIGN_PROBE_v1), or text positions
read off the final text by hand. Runs Chrome (offline; playwright is required: a missing install fails, never skips)."""
import copy
import hashlib
import unittest

from driver.prepare.convert import edgartools_html, html_route
from driver.prepare.convert import screen_grid as sg
from driver.prepare.convert.anchor import Visible

ROW = (b'<TR STYLE="font-size: 10pt; vertical-align: bottom">\n    <TD STYLE="font-size: 10pt"><FONT STYLE="font-size: 10pt">&nbsp;</FONT></TD>\n'
       b'    <TD STYLE="font: 10pt Times New Roman, Times, Serif; vertical-align: top; text-align: left"><FONT STYLE="font-size: 10pt">Premium Payment Date:</FONT></TD>\n'
       b'    <TD STYLE="font: 10pt Times New Roman, Times, Serif; text-align: left"><FONT STYLE="font-size: 10pt">[______],2023<SUP>13</SUP></FONT></TD></TR>')  # the source's own row (sha f7d2c397…, bytes 28483-28925)
YEAR = b'<TABLE STYLE="font-size: 10pt; border-collapse: collapse; width: 100%">\n  ' + ROW + ROW.replace(b'2023<SUP>13</SUP>', b'202313') + b'</TABLE>'  # and its twin printed flat
PAGES = {'year': YEAR, 'repeated': b'<p>13<sup>13</sup>13</p>', 'unicode': '<p>é😀&amp;<sup>&#49;&NotEqualTilde;</sup>X</p>'.encode(),
         'nested': (b'<p>A<sup><span>13</span></sup> B<sup style="vertical-align:baseline;font-size:inherit">14</sup> C<sup><span style="vertical-align:baseline">15</span></sup>'
                    b' D<sup style="display:contents">16</sup> E<sup>1<sub>7</sub></sup></p>'),
         'css': (b'<p>A<span style="vertical-align:4px"><b>13</b></span> B<span style="vertical-align:super">14</span> C<span style="vertical-align:sub">15</span>'
                 b' D<span style="position:relative;top:-0.4em">16</span> E<span style="display:inline-block;vertical-align:top">17</span></p><table><tr><td style="vertical-align:top">top</td><td style="vertical-align:middle">mid</td></tr></table>'
                 b'<div>F<table style="display:inline-table;vertical-align:text-bottom"><tr><td>whole table</td></tr></table></div>'),  # met-20241231 sets its tables so: a box of lines, not text raised on a line
         'hidden': b'<p>A<sup style="display:none">13</sup><sup style="opacity:0">3</sup><sup style="font-size:0">5</sup> end</p>',
         'foster': b'<table><sup>13</sup><tr><td>A</td></tr></table><table>14<tr><td>B</td></tr></table>'}
SUP, SUB = {'tag': 'sup', 'display': 'inline', 'vertical_align': 'super'}, {'tag': 'sub', 'display': 'inline', 'vertical_align': 'sub'}
CONTROLS = b'<!doctype html><meta charset="utf-8"><style>body{font:16px Arial}div{margin:12px}table{border-collapse:collapse}td{padding:0}</style><div data-case="block_super"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:super;font-size:16px">13</span></div><div data-case="block_length"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:4px;font-size:16px">13</span></div><div data-case="block_percent"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:40%;font-size:16px">13</span></div><div data-case="block_calc"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:calc(1px + 10%);font-size:16px">13</span></div><div data-case="block_zero_px"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:0px;font-size:16px">13</span></div><div data-case="block_zero_percent"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:0%;font-size:16px">13</span></div><div data-case="block_negative"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:-4px;font-size:16px">13</span></div><div data-case="flex_super"><span class="base">2023</span><span class="mark" style="display:inline-flex;vertical-align:super;font-size:16px">13</span></div><div data-case="grid_sub"><span class="base">2023</span><span class="mark" style="display:inline-grid;vertical-align:sub;font-size:16px">13</span></div><div data-case="inline_super"><span class="base">2023</span><span class="mark" style="vertical-align:super;font-size:16px">13</span></div><div data-case="inline_length"><span class="base">2023</span><span class="mark" style="vertical-align:4px;font-size:16px">13</span></div><div data-case="inline_text_bottom"><span class="base">2023</span><span class="mark" style="vertical-align:text-bottom;font-size:16px">13</span></div><div data-case="atomic_text_bottom"><span class="base">2023</span><span class="mark" style="display:inline-block;vertical-align:text-bottom;font-size:16px">13</span></div><div data-case="noninline_super"><span class="base">2023</span><span class="mark" style="display:block;vertical-align:super;font-size:16px">13</span></div><div data-case="cell_super"><span class="base">2023</span><span class="mark" style="display:table-cell;vertical-align:super;font-size:16px">13</span></div><div data-case="sup_baseline"><span class="base">2023</span><sup class="mark" style="vertical-align:baseline;font-size:16px">13</sup></div><div data-case="sup_contents"><span class="base">2023</span><sup class="mark" style="display:contents;font-size:16px">13</sup></div><div data-case="sup_block"><span class="base">2023</span><sup class="mark" style="display:block;font-size:16px">13</sup></div><div data-case="sup_cell"><span class="base">2023</span><sup class="mark" style="display:table-cell;font-size:16px">13</sup></div><div data-case="table_alignment"><span class="base">2023</span><table class="mark" style="display:inline-table;vertical-align:text-bottom"><tr><td>13</td></tr></table></div><div data-case="table_super"><span class="base">2023</span><table class="mark" style="display:inline-table;vertical-align:super"><tr><td>13</td></tr></table></div>'  # root's own control page (source_inline_20261009/root_design_followup/controls.html, sha 497e8cbc…), verbatim
BOXES = {'block_super': ('span', 'inline-block', 'super'), 'block_length': ('span', 'inline-block', '4px'), 'block_percent': ('span', 'inline-block', '40%'),
         'block_calc': ('span', 'inline-block', 'calc(10% + 1px)'), 'block_zero_px': ('span', 'inline-block', '0px'), 'block_zero_percent': ('span', 'inline-block', '0%'),
         'block_negative': ('span', 'inline-block', '-4px'), 'flex_super': ('span', 'inline-flex', 'super'), 'grid_sub': ('span', 'inline-grid', 'sub'),
         'inline_super': ('span', 'inline', 'super'), 'inline_length': ('span', 'inline', '4px'), 'inline_text_bottom': ('span', 'inline', 'text-bottom'),
         'sup_baseline': ('sup', 'inline', 'baseline'), 'sup_contents': ('sup', 'contents', 'super'), 'sup_block': ('sup', 'block', 'super'), 'sup_cell': ('sup', 'table-cell', 'super'),
         'table_super': ('table', 'inline-table', 'super'),
         'atomic_text_bottom': None, 'noninline_super': None, 'cell_super': None, 'table_alignment': None}  # root's EVIDENCE.json: the nearest admitted box, or none


def at(raw, text, n=1):  # the bytes of the n-th `text` in the source
    i = -1
    for _ in range(n): i = raw.index(text, i + 1)
    return {'byte_start': i, 'byte_end_exclusive': i + len(text)}


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                cls.routes = {k: html_route.prepare(v, k + '.htm', hashlib.sha256(v).hexdigest(), browser)[0] for k, v in dict(PAGES, controls=CONTROLS).items()}
                raw = b'<p>CORP<i>ORATION</i><sup>13</sup></p>'  # the tool's added space across inline markup, as the join tests give it: removed by the step
                cls.joined = {'sha256': hashlib.sha256(raw).hexdigest(), 'route': {'name': 'probe'}, 'units': [{'id': 'u0', 'kind': 'text', 'text': 'CORP ORATION13', 'anchor': {'byte_start': 3, 'byte_end_exclusive': len(raw) - 4}}]}
                sg.step(raw, cls.joined, browser)
            finally: browser.close()

    def inline(self, page): return self.routes[page]['source_inline']

    def test_a_raised_year_mark_is_told_from_the_same_digits_printed_flat(self):  # the source's own row: its row and cell alignment raise nothing
        cells = [c for c in self.routes['year']['units'][0]['cells'] if c['text'] == '[______],202313']; self.assertEqual(len(cells), 2)
        mark = YEAR.index(b'13</SUP>')
        self.assertEqual(self.inline('year'), {'read': True, 'records': [{'at': {'byte_start': mark, 'byte_end_exclusive': mark + 2}, 'raw': '13', 'ancestors': [SUP],
                                                                         'owners': [{'unit': 't0', 'cell': cells[0]['anchor']['byte_start'], 'text_at': [[13, 15]]}]}], 'unresolved': []})

    def test_repeated_equal_tokens_are_told_apart_by_their_own_bytes(self):
        self.assertEqual([(r['at'], r['owners']) for r in self.inline('repeated')['records']], [(at(PAGES['repeated'], b'13', 2), [{'unit': 'u0', 'text_at': [[2, 4]]}])])

    def test_nested_and_overridden_marks_keep_every_declared_and_computed_ancestor(self):  # an inner baseline does not cancel an outer sup; a baseline or contents sup keeps its tag
        text = self.routes['nested']['units'][0]['text']; self.assertEqual(text, 'A13 B14 C15 D16 E1 7')
        got = [(r['raw'], r['ancestors'], [text[a:b] for o in r['owners'] for a, b in o['text_at']]) for r in self.inline('nested')['records']]
        self.assertEqual(got, [('13', [SUP], ['13']), ('14', [dict(SUP, vertical_align='baseline')], ['14']), ('15', [SUP], ['15']), ('16', [dict(SUP, display='contents')], ['16']),
                               ('1', [SUP], ['1']), ('7', [SUB, SUP], ['7'])])
        self.assertEqual([o['text_at'] for r in self.inline('nested')['records'] for o in r['owners']], [[[1, 3]], [[5, 7]], [[9, 11]], [[13, 15]], [[17, 18]], [[19, 20]]])

    def test_css_only_raises_are_recorded_cell_and_box_alignment_and_relative_position_are_not(self):  # a relative offset is geometry only, an inline block's or table's alignment moves a box of lines: the unmeasured boundary
        got = [(r['raw'], r['ancestors']) for r in self.inline('css')['records']]
        self.assertEqual(got, [('13', [{'tag': 'span', 'display': 'inline', 'vertical_align': '4px'}]), ('14', [dict(SUP, tag='span')]), ('15', [dict(SUB, tag='span')])])

    def test_other_inline_boxes_count_super_sub_and_numbers_never_an_alignment_keyword(self):  # root's 21 controls: a raised number in a box, zero kept as evidence
        recs = self.inline('controls')['records']
        for case, box in BOXES.items():
            s = CONTROLS.index(b'data-case="%s"' % case.encode()); e = CONTROLS.find(b'<div data-case=', s + 1); e = len(CONTROLS) if e < 0 else e
            got = [(r['raw'], (r['ancestors'][0]['tag'], r['ancestors'][0]['display'], r['ancestors'][0]['vertical_align'])) for r in recs if s <= r['at']['byte_start'] < e]
            with self.subTest(case=case): self.assertEqual(got, [('13', box)] if box else [])

    def test_code_point_offsets_count_characters_not_bytes(self):  # a supplementary character, an entity, a reference read as two code points
        r, = self.inline('unicode')['records']; text = self.routes['unicode']['units'][0]['text']
        self.assertEqual((text, r['raw'], r['owners']), ('é😀&1≂̸X', '1≂̸', [{'unit': 'u0', 'text_at': [[3, 6]]}]))

    def test_offsets_are_read_in_the_final_joined_text(self):
        u = self.joined['units'][0]; self.assertEqual(u['text'], 'CORPORATION13')
        self.assertEqual([r['owners'] for r in self.joined['source_inline']['records']], [[{'unit': 'u0', 'text_at': [[11, 13]]}]])

    def test_hidden_and_zero_area_marks_have_no_owner(self):
        got = [(r['raw'], r.get('visibility'), r['owners']) for r in self.inline('hidden')['records']]
        self.assertEqual(got, [('13', 'hidden', None), ('3', 'hidden', None), ('5', 'unproven', None)])

    def test_a_fostered_mark_stays_bound_and_fostered_text_is_unresolved_never_guessed(self):  # the parser moves both out of their tables
        g = self.inline('foster'); self.assertEqual([(r['raw'], r['ancestors'], r.get('certain')) for r in g['records']], [('13', [SUP], False)])
        self.assertEqual([(r['raw'], r['why'], r['at']) for r in g['unresolved']], [('14', 'unbound', at(PAGES['foster'], b'14'))])

    def test_units_and_every_other_field_are_untouched(self):
        for page, raw in dict(PAGES, controls=CONTROLS).items():
            route = self.routes[page]; vis = Visible(raw, page=route.get('page_visibility')); runs, _ = sg.symbol_runs(raw, vis); units = copy.deepcopy(route['units'])
            sg.inline(raw, vis, runs, {'marks': {}, 'plain': '', 'inline': {}}, units)
            with self.subTest(page=page): self.assertEqual(units, route['units'])
        bare = edgartools_html.convert(PAGES['repeated'], 'repeated.htm', hashlib.sha256(PAGES['repeated']).hexdigest())
        self.assertEqual([(u['id'], u['kind'], u['text'], u['anchor']) for u in self.routes['repeated']['units']], [(u['id'], u['kind'], u['text'], u['anchor']) for u in bare['units']])


class Failure(unittest.TestCase):
    def test_a_page_that_cannot_be_read_says_the_inline_evidence_went_unread(self):
        class Browser:
            def new_page(self, **k): raise RuntimeError('no page')
            def is_connected(self): return True
        raw = b'<p>2023<sup>13</sup></p>'; route = edgartools_html.convert(raw, 'f.htm', hashlib.sha256(raw).hexdigest()); sg.step(raw, route, Browser())
        self.assertEqual(route['source_inline'], {'read': False, 'error': "RuntimeError('no page')"}); self.assertIsNot(route['source_inline'], route['source_symbols'])  # two records, not one shared

    def test_a_failed_mark_reading_says_the_inline_evidence_went_unread(self):
        from unittest.mock import patch
        from playwright.sync_api import sync_playwright
        raw = b'<p>2023<sup>13</sup></p>'
        with sync_playwright() as pw, patch.object(sg, 'SYMBOLS_JS', '(p) => { throw new Error("no marks"); }'):
            browser = pw.chromium.launch()
            try: route, _ = html_route.prepare(raw, 's.htm', hashlib.sha256(raw).hexdigest(), browser)
            finally: browser.close()
        self.assertEqual((route['status'], route['source_inline']['read']), ('PARTIAL', False)); self.assertIn('no marks', route['source_inline']['error'])


class Marks(unittest.TestCase):
    def test_a_mark_never_found_and_text_its_mark_does_not_reach_are_unresolved(self):
        raw = b'<p>2023<sup>13</sup></p>'; vis = Visible(raw); runs, _ = sg.symbol_runs(raw, vis); k = str(next(i for i, r in enumerate(runs) if r[1][0][0] == raw.index(b'13<')))
        lost = sg.inline(raw, vis, runs, {'marks': {}, 'plain': '', 'inline': {}}, [])
        moved = sg.inline(raw, vis, runs, {'marks': {k: None}, 'plain': '', 'inline': {}}, [])
        misread = sg.inline(raw, vis, runs, {'marks': {}, 'plain': k, 'inline': {k: {'text': '14', 'visibility': 'shown', 'ancestors': [SUP]}}}, [])
        self.assertEqual([[(r['raw'], r['why']) for r in g['unresolved'] if r['raw'] == '13'] for g in (lost, moved, misread)], [[('13', 'mark not found')], [('13', 'unbound')], [('13', 'unbound')]])
        self.assertEqual([g['records'] for g in (lost, moved, misread)], [[], [], []])  # no role read into text the mark did not reach


if __name__ == '__main__':
    unittest.main()
