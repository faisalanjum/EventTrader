"""A word or number the tool printed in two (a space the source does not have, across inline markup) is joined by the screen step when Chrome shows the two
characters touching on one baseline — never on the text alone (the page's styles may space them), never where the source itself spaces or breaks them."""
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import source_formatting
from driver.prepare.convert import screen_grid as sg
from driver.prepare.convert.anchor import Visible


def unit(raw, text, start=None, end=None, **more):
    return {'id': 'u', 'kind': 'text', 'text': text, 'anchor': {'byte_start': raw.index(b'<p>') if start is None else start, 'byte_end_exclusive': len(raw) if end is None else end}, **more}


class ToolSpaces(unittest.TestCase):
    def test_a_space_the_tool_added_inside_a_word_or_number_is_found_by_its_place(self):
        raw = b'<p>CVS HEALTH CORP<ix:nonNumeric name="x">ORATION</ix:nonNumeric> had 1,2<a id="k"></a>34 in <i>Oc</i>tober.</p>'
        vis = Visible(raw); found = anchor.tool_spaces(vis, unit(raw, 'CVS HEALTH CORP ORATION had 1,2 34 in Oc tober.'))
        text = 'CVS HEALTH CORP ORATION had 1,2 34 in Oc tober.'; self.assertEqual([(a, b) for a, b, _, _ in found], [(text.index(' ORATION'), text.index(' ORATION') + 1), (text.index(' 34'), text.index(' 34') + 1), (text.index(' tober'), text.index(' tober') + 1)])
        self.assertEqual([vis.flat[k] + vis.flat[l] for _, _, k, l in found], ['PO', '23', 'ct'])

    def test_a_space_the_source_has_or_that_reflows_punctuation_is_no_gap(self):
        raw = b'<p>Net sales<br>fell<div>by</div>2.5 (loss)<span> </span>x; Co.<b>Inc</b></p>'
        vis = Visible(raw); text = 'Net sales fell by 2.5 (loss) x; Co. Inc'
        self.assertEqual(anchor.tool_spaces(vis, unit(raw, text)), [])  # white space, a line break, a block, punctuation: the source or the rule spaces them
        self.assertEqual(anchor.tool_spaces(vis, unit(raw, 'Net sales fell by 2.5 (loss) x; Co.Inc')), [])  # a space the tool dropped is not this step's
        self.assertEqual(anchor.tool_spaces(vis, unit(raw, 'Net sales fell by 2.5 (loss) y; Co. Inc')), [])  # not the source's text: nothing is said

    def test_an_item_without_a_whole_byte_reading_says_nothing(self):
        raw = b'<p>CORP<i>ORATION</i> a&amp;b</p>'; vis = Visible(raw); text = 'CORP ORATION a&b'
        self.assertEqual(anchor.tool_spaces(vis, {'text': text}), []); self.assertEqual(anchor.tool_spaces(vis, {'text': text, 'anchor': [{'byte_start': 3, 'byte_end_exclusive': len(raw)}, {'page': 1, 'region': [0, 0, 1, 1]}]}), [])
        cut = raw.index(b'&amp;') + 2; self.assertEqual(anchor.tool_spaces(vis, {'text': 'CORP ORATION a', 'anchor': {'byte_start': 3, 'byte_end_exclusive': cut}}), [])  # a place that ends inside a character
        self.assertEqual(len(anchor.tool_spaces(vis, {'text': 'CORP ORATION', 'anchor': {'byte_start': 3, 'byte_end_exclusive': raw.index(b' a&amp;')}})), 1)
        self.assertEqual(anchor.tool_spaces(vis, unit(raw, 'CORP\u200bORATION a&b')), [])  # not white space between the two: not this step's
        self.assertEqual(anchor.tool_spaces(vis, {'text': '', 'anchor': {'byte_start': 0, 'byte_end_exclusive': 3}}), [])  # a place holding no character
        self.assertEqual(len(anchor.tool_spaces(vis, {'text': 'CORP ORATION a&b', 'anchor': {'byte_start': 3, 'byte_end_exclusive': raw.index(b'</p>')}})), 1)  # a place ending exactly where its last character ends

    def test_a_space_beside_a_numbers_own_separator_is_found(self):  # the gate reads "0.69" and "1,234" as one number each: a space beside the separator cuts it
        raw = b'<p>EPS was $0<b>.</b>69, up 1<i>,</i>234 and Co.<b>Inc</b> in the 10<sup>th</sup></p>'; text = 'EPS was $0. 69, up 1, 234 and Co. Inc in the 10 th'
        found = anchor.tool_spaces(Visible(raw), unit(raw, text))
        self.assertEqual([text[a - 1:b + 1] for a, b, _, _ in found], ['. 6', ', 2', '0 t'])  # the two separators' spaces, the digit-letter one as before; "Co. Inc" stays reflow at punctuation

    def test_the_keys_marks_do_not_shift_the_places(self):
        raw = b'<p><s>old</s>new CORP<i>ORATION</i></p>'
        self.assertEqual([(a, b) for a, b, _, _ in anchor.tool_spaces(Visible(raw), unit(raw, '~~old~~new CORP ORATION'))], [(15, 16)])  # the text's own position, the marks counted


def marked(raw, vis):  # the screen step's own body: cell and run marks only, no comment inside any text
    runs, _ = sg.symbol_runs(raw, vis); p = sg.marker_prefix(raw)
    return sg.tag_cells(raw, vis, (), [(a, b'<!--%ss:%d-->' % (p.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], p)[0], runs, p

UNMARKED = """([needle, nth]) => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let t, seen = 0;  // the character by its own UTF-16 place in the unmarked page
  while ((t = w.nextNode())) { let i = -1; while ((i = t.data.indexOf(needle, i + 1)) >= 0) { if (seen++ === nth) { const r = document.createRange(); r.setStart(t, i); r.setEnd(t, i + needle.length);
    const rs = r.getClientRects(); return rs.length === 1 ? {x: rs[0].left, r: rs[0].right, t: rs[0].top, b: rs[0].bottom} : null; } } } return null; }"""


class Tagging(unittest.TestCase):
    def test_gap_comments_are_refused_and_cell_marks_unchanged(self):
        raw = b'<table><tr><td>CORP<i>ORATION</i></td></tr></table>'; vis = Visible(raw); cell = {'id': 'c', 'kind': 'text', 'text': 'CORP ORATION', 'anchor': {'byte_start': 15, 'byte_end_exclusive': 30}}
        gaps = sg.gaps_of(vis, [cell]); self.assertTrue(gaps)
        with self.assertRaises(ValueError): sg.tag_cells(raw, vis, gaps)
        self.assertEqual(sg.tag_cells(raw)[0], b'<table><tr><td><!--g:0-->CORP<i>ORATION</i></td></tr></table>')
        runs, _ = sg.symbol_runs(raw, vis); want, unmapped = sg.gap_chars(raw, vis, runs, gaps)
        self.assertEqual((unmapped, [w[2:] for w in want]), ([], [(3, 1), (0, 1)]))  # P: run 0, 4th code point; O: run 1, 1st


class Joining(unittest.TestCase):
    def setUp(self):
        self.raw = b'<p>CORP<i>ORATION</i> and 1,2<a id="k"></a>34</p>'; self.vis = Visible(self.raw)

    def gaps(self, text='CORP ORATION and 1,2 34'):
        self.item = unit(self.raw, text); return sg.gaps_of(self.vis, [self.item])

    def test_touching_characters_on_one_line_are_joined_and_the_joins_recorded(self):
        gaps = self.gaps(); boxes = {'0.0': dict(x=10, r=18, t=0, b=12), '0.1': dict(x=18.3, r=26, t=0, b=12), '1.0': dict(x=40, r=46, t=0, b=12), '1.1': dict(x=45.5, r=52, t=0, b=12)}
        self.assertEqual(sg.join(gaps, boxes), 2); self.assertEqual((self.item['text'], self.item['joins']), ('CORPORATION and 1,234', [[4, 5, 0.3], [20, 21, -0.5]]))

    def test_a_joined_items_struck_places_are_read_again(self):  # Codex C3: the places count the text's characters, which the join moved
        raw = b'<p><s>old</s>new CORP<i>ORATION</i> <s>gone</s> 1,2<a id="k"></a>34 <s>x</s>y</p>'; vis = Visible(raw)
        item = unit(raw, 'oldnew CORP ORATION gone 1,2 34 xy'); source_formatting.apply(raw, [item]); before = item['struck_at']
        gaps = sg.gaps_of(vis, [item]); L = dict(x=0, r=8, t=0, b=12); boxes = {'0.0': L, '0.1': dict(L, x=8), '1.0': L, '1.1': dict(L, x=8)}
        self.assertEqual(sg.join(gaps, boxes, vis), 2); self.assertEqual(item['text'], 'oldnew CORPORATION gone 1,234 xy')
        self.assertEqual(item['struck_at'], anchor.struck_at(vis, item)); self.assertEqual([item['text'][a:b] for a, b in item['struck_at']], ['old', 'gone', 'x']); self.assertNotEqual(item['struck_at'], before)
        other = unit(raw, 'oldnew CORP ORATION gone 1,2 34 xy', struck_at=[[0, 3]]); self.assertEqual(sg.join(sg.gaps_of(vis, [other]), boxes), 2); self.assertNotIn('struck_at', other)  # without the reading, a stale place is dropped, never kept

    def test_a_gap_the_page_shows_or_another_line_or_a_missing_box_keeps_the_space(self):
        L, R = dict(x=10, r=18, t=0, b=12), dict(x=18, r=26, t=0, b=12)
        for why, left, right in (('a gap of the page', L, dict(R, x=21)), ('an overlap past the tolerance', L, dict(R, x=16)), ('another line', L, dict(R, t=14, b=26)), ('another bottom: a raised mark', L, dict(R, t=-3, b=6)), ('another bottom: a lowered mark', L, dict(R, t=5, b=14)),
                                 ('no left box', None, R), ('no right box', L, None)):
            gaps = self.gaps(); boxes = {k: v for k, v in (('0.0', left), ('0.1', right)) if v}
            with self.subTest(why=why): self.assertEqual(sg.join(gaps, boxes), 0); self.assertEqual(self.item['text'], 'CORP ORATION and 1,2 34'); self.assertNotIn('joins', self.item)
        for dt, db in ((1, 0), (0, 1), (-1, -1), (3, -1), (3, 0)):  # one baseline still: bottoms a pixel apart at most, the tops free (a smaller font: small capitals)
            gaps = self.gaps(); self.assertEqual(sg.join(gaps, {'0.0': L, '0.1': dict(R, t=dt, b=12 + db)}), 1)
        for gap in (0.75, -0.75, 0):  # within the tolerance, either way: joined
            gaps = self.gaps(); self.assertEqual(sg.join(gaps, {'0.0': L, '0.1': dict(R, x=18 + gap)}), 1); self.assertEqual(self.item['text'], 'CORPORATION and 1,2 34')
        self.assertEqual(sg.gaps_of(self.vis, [{'id': 't', 'kind': 'table'}]), [])  # a table unit without cells
        raw = b'<table><tr><td>CORP<i>ORATION</i></td></tr></table>'; cell = {'r': 0, 'c': 0, 'text': 'CORP ORATION', 'anchor': {'byte_start': 15, 'byte_end_exclusive': 30}}
        self.assertEqual(len(sg.gaps_of(Visible(raw), [{'id': 't', 'kind': 'table', 'cells': [cell]}])), 1)  # a table's cells are its items


class Measuring(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start(); self.browser = self.pw.chromium.launch(); self.page = self.browser.new_page(); self.page.route('**/*', lambda r: r.abort())
    def tearDown(self): self.browser.close(); self.pw.stop()

    def boxes(self, raw, vis, gaps):
        body, runs, p = marked(raw, vis); self.assertNotIn(b'j:', body); want, unmapped = sg.gap_chars(raw, vis, runs, gaps)
        self.page.set_content(body.decode(), wait_until='load'); return self.page.evaluate(sg.JS, [p, [list(x) for x in want]])['boxes'], unmapped
    def unmarked(self, raw, needle, nth=0):
        self.page.set_content(raw.decode(), wait_until='load'); return self.page.evaluate(UNMARKED, [needle, nth])

    def test_a_character_that_ends_one_gap_and_begins_the_next_is_measured_for_both(self):
        raw = b'<p>Pol<font style="letter-spacing:0.016em">i</font>cy</p>'; vis = Visible(raw); gaps = sg.gaps_of(vis, [unit(raw, 'Pol i cy')])
        boxes, unmapped = self.boxes(raw, vis, gaps); self.assertEqual((sorted(boxes), unmapped), (['0.0', '0.1', '1.0', '1.1'], []))
        self.assertEqual(boxes['0.1'], boxes['1.0'])
        self.assertAlmostEqual(boxes['0.1']['x'], boxes['0.0']['r'], places=3); self.assertAlmostEqual(boxes['1.1']['x'], boxes['1.0']['r'], places=3)
        self.assertEqual(sg.join(gaps, boxes), 2); self.assertEqual(gaps[0][0]['text'], 'Policy')
        self.assertEqual({k: boxes['0.1'][k] for k in 'xrtb'}, self.unmarked(raw, 'i'))  # independent: the same character on the unmarked page

    def test_a_numbers_separator_set_in_its_own_run_is_joined_and_a_list_number_set_apart_keeps_its_space(self):
        for raw, text, want in ((b'<p style="font-family:Calibri,sans-serif;font-size:11pt">was $0<font style="font-weight:bold">.</font>69, a year</p>', 'was $0. 69, a year', 'was $0.69, a year'),
                                (b'<p style="font-size:10pt">2.<span style="margin-left:24px">4.650% Notes</span></p>', '2. 4.650% Notes', '2. 4.650% Notes')):
            with self.subTest(text=text):
                vis = Visible(raw); gaps = sg.gaps_of(vis, [unit(raw, text, start=0)]); self.assertTrue(gaps)
                boxes, unmapped = self.boxes(raw, vis, gaps); self.assertEqual(unmapped, []); sg.join(gaps, boxes); self.assertEqual(gaps[0][0]['text'], want)

    def test_small_capitals_are_joined_and_raised_or_lowered_marks_keep_their_space(self):
        for raw, text, want in ((b'<p style="font-family:serif;font-weight:700"><span style="font-size:10pt">S</span><span style="font-size:8pt">IGNIFICANT</span></p>', 'S IGNIFICANT', 'SIGNIFICANT'),
                                (b'<p style="font-size:10pt">$5<sup>1</sup> million</p>', '$5 1 million', '$5 1 million'),
                                (b'<p style="font-size:10pt">CO<sub>2</sub> and NO<sub>x</sub></p>', 'CO 2 and NO x', 'CO 2 and NO x')):
            with self.subTest(text=text):
                vis = Visible(raw); gaps = sg.gaps_of(vis, [unit(raw, text, start=0)]); self.assertTrue(gaps)
                boxes, unmapped = self.boxes(raw, vis, gaps); self.assertEqual(unmapped, []); sg.join(gaps, boxes); self.assertEqual(gaps[0][0]['text'], want)

    def test_non_bmp_and_two_code_point_reference_are_measured_whole(self):
        for raw, text, needle in (('<p style="font-size:12pt">AB<b>\U0001D400C</b></p>'.encode(), 'AB \U0001D400C', '\U0001D400'),  # a surrogate pair: never half of it
                                  (b'<p style="font-size:12pt">a<b>&fjlig;ord</b></p>', 'a fjord', 'fj')):  # one reference, two code points (letters, so the tool sees a word gap)
            with self.subTest(text=text):
                vis = Visible(raw); gaps = sg.gaps_of(vis, [unit(raw, text, start=0)]); self.assertTrue(gaps)
                runs, _ = sg.symbol_runs(raw, vis); want, unmapped = sg.gap_chars(raw, vis, runs, gaps); self.assertEqual(unmapped, [])
                self.assertEqual([w[3] for w in want if w[0] == '0.1'], [len(needle)])  # the right side's extent: the whole character in code points
                boxes, _ = self.boxes(raw, vis, gaps); self.assertEqual({k: boxes['0.1'][k] for k in 'xrtb'}, self.unmarked(raw, needle))

    def test_a_source_comment_and_white_space_inside_a_run(self):  # the native walk crosses the page's own comment; white space is not counted, its offsets are kept
        raw = b'<p style="font-size:12pt">Rev<!-- authored -->enue \r\n  total<i>s</i></p>'; vis = Visible(raw); gaps = sg.gaps_of(vis, [unit(raw, 'Revenue total s', start=0)]); self.assertTrue(gaps)
        boxes, unmapped = self.boxes(raw, vis, gaps); self.assertEqual(unmapped, [])
        self.assertEqual({k: boxes['0.0'][k] for k in 'xrtb'}, self.unmarked(raw, 'l'))  # the last character of "total", across the comment and the CRLF
        sg.join(gaps, boxes); self.assertEqual(gaps[0][0]['text'], 'Revenue totals')

if __name__ == '__main__':
    unittest.main()
