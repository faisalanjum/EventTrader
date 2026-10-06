"""A word or number the tool printed in two (a space the source does not have, across inline markup) is joined by the screen step when Chrome shows the two
characters touching on one line — never on the text alone (the page's styles may space them), never where the source itself spaces or breaks them."""
import unittest

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.adapters import screen_grid as sg
from benchmarks.prepare.grader.anchor import Visible


def unit(raw, text, start=None, end=None):
    return {'id': 'u', 'kind': 'text', 'text': text, 'anchor': {'byte_start': raw.index(b'<p>') if start is None else start, 'byte_end_exclusive': len(raw) if end is None else end}}


class ToolSpaces(unittest.TestCase):
    def test_a_space_the_tool_added_inside_a_word_or_number_is_found_by_its_place(self):
        raw = b'<p>CVS HEALTH CORP<ix:nonNumeric name="x">ORATION</ix:nonNumeric> had 1,2<a id="k"></a>34 in <i>Oc</i>tober.</p>'
        vis = Visible(raw); found = grade.tool_spaces(vis, unit(raw, 'CVS HEALTH CORP ORATION had 1,2 34 in Oc tober.'))
        text = 'CVS HEALTH CORP ORATION had 1,2 34 in Oc tober.'; self.assertEqual([(a, b) for a, b, _, _ in found], [(text.index(' ORATION'), text.index(' ORATION') + 1), (text.index(' 34'), text.index(' 34') + 1), (text.index(' tober'), text.index(' tober') + 1)])
        self.assertEqual([vis.flat[k] + vis.flat[l] for _, _, k, l in found], ['PO', '23', 'ct'])

    def test_a_space_the_source_has_or_that_reflows_punctuation_is_no_gap(self):
        raw = b'<p>Net sales<br>fell<div>by</div>2.5 (loss)<span> </span>x; Co.<b>Inc</b></p>'
        vis = Visible(raw); text = 'Net sales fell by 2.5 (loss) x; Co. Inc'
        self.assertEqual(grade.tool_spaces(vis, unit(raw, text)), [])  # white space, a line break, a block, punctuation: the source or the rule spaces them
        self.assertEqual(grade.tool_spaces(vis, unit(raw, 'Net sales fell by 2.5 (loss) x; Co.Inc')), [])  # a space the tool dropped is not this step's
        self.assertEqual(grade.tool_spaces(vis, unit(raw, 'Net sales fell by 2.5 (loss) y; Co. Inc')), [])  # not the source's text: nothing is said

    def test_an_item_without_a_whole_byte_reading_says_nothing(self):
        raw = b'<p>CORP<i>ORATION</i> a&amp;b</p>'; vis = Visible(raw); text = 'CORP ORATION a&b'
        self.assertEqual(grade.tool_spaces(vis, {'text': text}), []); self.assertEqual(grade.tool_spaces(vis, {'text': text, 'anchor': [{'byte_start': 3, 'byte_end_exclusive': len(raw)}, {'page': 1, 'region': [0, 0, 1, 1]}]}), [])
        cut = raw.index(b'&amp;') + 2; self.assertEqual(grade.tool_spaces(vis, {'text': 'CORP ORATION a', 'anchor': {'byte_start': 3, 'byte_end_exclusive': cut}}), [])  # a place that ends inside a character
        self.assertEqual(len(grade.tool_spaces(vis, {'text': 'CORP ORATION', 'anchor': {'byte_start': 3, 'byte_end_exclusive': raw.index(b' a&amp;')}})), 1)
        self.assertEqual(grade.tool_spaces(vis, unit(raw, 'CORP\u200bORATION a&b')), [])  # not white space between the two: not this step's
        self.assertEqual(grade.tool_spaces(vis, {'text': '', 'anchor': {'byte_start': 0, 'byte_end_exclusive': 3}}), [])  # a place holding no character
        self.assertEqual(len(grade.tool_spaces(vis, {'text': 'CORP ORATION a&b', 'anchor': {'byte_start': 3, 'byte_end_exclusive': raw.index(b'</p>')}})), 1)  # a place ending exactly where its last character ends

    def test_the_keys_marks_do_not_shift_the_places(self):
        raw = b'<p><s>old</s>new CORP<i>ORATION</i></p>'
        self.assertEqual([(a, b) for a, b, _, _ in grade.tool_spaces(Visible(raw), unit(raw, '~~old~~new CORP ORATION'))], [(15, 16)])  # the text's own position, the marks counted


class Tagging(unittest.TestCase):
    def test_the_two_characters_of_each_gap_get_a_span_of_their_own_beside_the_cell_marks(self):
        raw = b'<table><tr><td>CORP<i>ORATION</i></td></tr></table>'; vis = Visible(raw); cell = {'id': 'c', 'kind': 'text', 'text': 'CORP ORATION', 'anchor': {'byte_start': 15, 'byte_end_exclusive': 30}}
        gaps = sg.gaps_of(vis, [cell]); marked, spans = sg.tag_cells(raw, vis, gaps)
        self.assertEqual(marked, b'<table><tr><td data-g="0">COR<span data-j="0.0">P</span><i><span data-j="0.1">O</span>RATION</i></td></tr></table>')
        self.assertEqual(sg.tag_cells(raw)[0], b'<table><tr><td data-g="0">CORP<i>ORATION</i></td></tr></table>')  # without gaps, as before


class Joining(unittest.TestCase):
    def setUp(self):
        self.raw = b'<p>CORP<i>ORATION</i> and 1,2<a id="k"></a>34</p>'; self.vis = Visible(self.raw)

    def gaps(self, text='CORP ORATION and 1,2 34'):
        self.item = unit(self.raw, text); return sg.gaps_of(self.vis, [self.item])

    def test_touching_characters_on_one_line_are_joined_and_the_joins_recorded(self):
        gaps = self.gaps(); boxes = {'0.0': dict(x=10, r=18, t=0, b=12), '0.1': dict(x=18.3, r=26, t=0, b=12), '1.0': dict(x=40, r=46, t=0, b=12), '1.1': dict(x=45.5, r=52, t=0, b=12)}
        self.assertEqual(sg.join(gaps, boxes), 2); self.assertEqual((self.item['text'], self.item['joins']), ('CORPORATION and 1,234', [[4, 5, 0.3], [20, 21, -0.5]]))

    def test_a_gap_the_page_shows_or_another_line_or_a_missing_box_keeps_the_space(self):
        L, R = dict(x=10, r=18, t=0, b=12), dict(x=18, r=26, t=0, b=12)
        for why, left, right in (('a gap of the page', L, dict(R, x=21)), ('an overlap past the tolerance', L, dict(R, x=16)), ('another line', L, dict(R, t=14, b=26)), ('another top', L, dict(R, t=2)), ('another bottom', L, dict(R, b=14)),
                                 ('no left box', None, R), ('no right box', L, None)):
            gaps = self.gaps(); boxes = {k: v for k, v in (('0.0', left), ('0.1', right)) if v}
            with self.subTest(why=why): self.assertEqual(sg.join(gaps, boxes), 0); self.assertEqual(self.item['text'], 'CORP ORATION and 1,2 34'); self.assertNotIn('joins', self.item)
        for dt, db in ((1, 0), (0, 1), (-1, -1)):  # one line still: tops or bottoms a pixel apart
            gaps = self.gaps(); self.assertEqual(sg.join(gaps, {'0.0': L, '0.1': dict(R, t=dt, b=12 + db)}), 1)
        for gap in (0.75, -0.75, 0):  # within the tolerance, either way: joined
            gaps = self.gaps(); self.assertEqual(sg.join(gaps, {'0.0': L, '0.1': dict(R, x=18 + gap)}), 1); self.assertEqual(self.item['text'], 'CORPORATION and 1,2 34')
        self.assertEqual(sg.gaps_of(self.vis, [{'id': 't', 'kind': 'table'}]), [])  # a table unit without cells
        raw = b'<table><tr><td>CORP<i>ORATION</i></td></tr></table>'; cell = {'r': 0, 'c': 0, 'text': 'CORP ORATION', 'anchor': {'byte_start': 15, 'byte_end_exclusive': 30}}
        self.assertEqual(len(sg.gaps_of(Visible(raw), [{'id': 't', 'kind': 'table', 'cells': [cell]}])), 1)  # a table's cells are its items


if __name__ == '__main__':
    unittest.main()
