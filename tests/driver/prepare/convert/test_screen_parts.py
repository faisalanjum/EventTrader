"""A boundary the tool drops between two characters the page sets apart comes back as one space by the screen step when Chrome lays the two out on one
baseline, apart: positioned boxes `1.` and `10700` read `1.10700` (a real subsidiaries list). The mirror of the joins: never on the text alone, never where
the two touch (one word or number set in positioned pieces), stand on another baseline (a raised or lowered mark), sit in two cells, or where a space would
part no two words or numbers (reflow at punctuation, E12)."""
import hashlib
import unittest
from pathlib import Path

from driver.prepare.convert import anchor, edgartools_html, html_route, source_formatting
from driver.prepare.convert import screen_grid as sg
from driver.prepare.convert.anchor import Visible

PAGE = (Path(__file__).parent / 'fixtures' / 'positioned_boundaries.html').read_bytes()  # original pieces and synthetic rows: its first line names them


def line(*pieces):  # one line of positioned pieces, as the original sets them
    return b'<div style="position: absolute; top: 2pt">' + b''.join(b'<font style="position: absolute; left: %dpt">%s</font>' % p for p in pieces) + b'</div>'


def unit(raw, text, **more):
    return {'id': 'u', 'kind': 'text', 'text': text, 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, **more}


def items(route):
    return [x for u in route['units'] for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u])]


class ToolJoins(unittest.TestCase):
    def test_a_boundary_the_tool_dropped_between_two_positioned_boxes_is_found_by_its_place(self):
        raw = line((4, b'1.'), (40, b'10700'), (70, b' '), (73, b'WILSHIRE,')); vis = Visible(raw)
        found = anchor.tool_joins(vis, unit(raw, '1.10700 WILSHIRE,'))
        self.assertEqual([(a, b) for a, b, _, _ in found], [(2, 2)]); self.assertEqual([vis.flat[k] + vis.flat[l] for _, _, k, l in found], ['.1'])

    def test_no_place_where_the_text_or_the_source_already_parts_them_or_a_space_parts_no_two_words_or_numbers(self):
        for raw, text in ((line((4, b'1.'), (40, b'10700')), '1. 10700'),  # the text has the space
                          (b'<p>CORP<i>ORATION</i> 1,2<a id="k"></a>34</p>', 'CORPORATION 1,234'),  # inline markup: the source prints them touching
                          (line((4, b'19.'), (40, b'AAA')), '19.AAA'),  # a letter after a list number: the period parts them already
                          (line((4, b'LLC'), (30, b'(DE)')), 'LLC(DE)')):  # punctuation reflows
            with self.subTest(text=text): self.assertEqual(anchor.tool_joins(Visible(raw), unit(raw, text)), [])
        raw = line((4, b'1.'), (40, b'10700')); vis = Visible(raw)
        self.assertEqual(anchor.tool_joins(vis, unit(raw, '2.10700')), [])  # not the source's text: nothing is said
        self.assertEqual(anchor.tool_joins(vis, {'text': '1.10700'}), [])  # no byte reading
        self.assertEqual(anchor.tool_spaces(vis, unit(raw, '1.10700')), [])  # and it is no added space


class Parting(unittest.TestCase):
    def setUp(self):
        self.raw = line((4, b'1.'), (40, b'10700'), (70, b' '), (73, b'WILSHIRE,')); self.vis = Visible(self.raw)

    def gaps(self, text='1.10700 WILSHIRE,'):
        self.item = unit(self.raw, text); return sg.gaps_of(self.vis, [self.item])

    def test_two_characters_laid_apart_on_one_baseline_are_parted_and_the_part_recorded(self):
        gaps = self.gaps(); self.assertEqual([(a, b) for _, a, b, _, _ in gaps], [(2, 2)])
        self.assertEqual(sg.join(gaps, {'0.0': dict(shown=True, x=10, r=14, t=0, b=12), '0.1': dict(shown=True, x=50.4, r=58, t=0, b=12)}), 1)
        self.assertEqual((self.item['text'], self.item['parts']), ('1. 10700 WILSHIRE,', [[2, 36.4]])); self.assertNotIn('joins', self.item)

    def test_touching_overlapping_reversed_hidden_another_baseline_or_a_missing_box_keeps_the_text(self):
        L, R = dict(shown=True, x=10, r=14, t=0, b=12), dict(shown=True, x=14, r=22, t=0, b=12)
        for why, left, right in (('touching', L, R), ('apart within the tolerance', L, dict(R, x=14.75)), ('overlapping within the tolerance', L, dict(R, x=13.25)),
                                 ('overlapping past the tolerance', L, dict(R, x=8)), ('a reversed pair: the right one laid out before the left', L, dict(R, x=-30, r=-22)),
                                 ('the left one not shown', dict(L, shown=False), dict(R, x=40)), ('the right one not shown', L, dict(R, x=40, shown=False)), ('no shown state', dict(L, shown=None), dict(R, x=40)),
                                 ('another line', L, dict(R, x=40, t=14, b=26)), ('a raised mark', L, dict(R, x=40, t=-3, b=6)), ('a lowered mark', L, dict(R, x=40, t=5, b=14)),
                                 ('no left box', None, R), ('no right box', L, None)):
            gaps = self.gaps(); boxes = {k: v for k, v in (('0.0', left), ('0.1', right)) if v}
            with self.subTest(why=why): self.assertEqual(sg.join(gaps, boxes), 0); self.assertEqual(self.item['text'], '1.10700 WILSHIRE,'); self.assertNotIn('parts', self.item)
        gaps = self.gaps(); self.assertEqual(sg.join(gaps, {'0.0': L, '0.1': dict(R, x=14.76)}), 1)  # past the tolerance: apart

    def test_a_join_and_a_part_in_one_item_are_both_placed_in_the_text_as_it_was_and_struck_places_read_again(self):
        raw = b'<div>1.<div>10700</div><s>old</s>new CORP<i>ORATION</i></div>'; vis = Visible(raw)  # a block parts them too; a struck run is read apart, never a layout gap
        item = unit(raw, '1.10700 oldnew CORP ORATION'); source_formatting.apply(raw, [item]); before = item['struck_at']
        gaps = sg.gaps_of(vis, [item]); self.assertEqual(sorted((a, b) for _, a, b, _, _ in gaps), [(2, 2), (19, 20)])
        L = dict(shown=True, x=0, r=8, t=0, b=12); boxes = {f'{n}.0': L for n in range(2)}
        for n, (_, a, b, _, _) in enumerate(gaps): boxes[f'{n}.1'] = dict(L, x=8 if a < b else 44)  # the added space touching, the dropped one apart
        self.assertEqual(sg.join(gaps, boxes, vis), 2); self.assertEqual(item['text'], '1. 10700 oldnew CORPORATION')
        self.assertEqual((item['joins'], item['parts']), ([[19, 20, 0]], [[2, 36]]))
        self.assertEqual(item['struck_at'], anchor.struck_at(vis, item)); self.assertEqual([item['text'][a:b] for a, b in item['struck_at']], ['old']); self.assertNotEqual(item['struck_at'], before)


class Route(unittest.TestCase):
    """The whole HTML route in Chrome (offline; playwright is required: a missing install fails, never skips) on the test page: the original's rows 1
    and 11 and synthetic siblings and controls, on a page box below the window (content-visibility: auto, as in the original: deferred rendering)."""
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try: cls.route, cls.facts = html_route.prepare(PAGE, 'positioned.htm', hashlib.sha256(PAGE).hexdigest(), browser)
            finally: browser.close()
        cls.texts = [x['text'] for x in items(cls.route)]

    def test_positioned_boxes_the_page_lays_apart_on_one_line_are_parted(self):
        for want in ('1. 10700 WILSHIRE, LLC (DE)', '11. 225 6th STREET MANAGER LLC (DE)', '7. 2250 OAK STREET, INC. (NY)'):
            with self.subTest(want=want): self.assertIn(want, self.texts)
        self.assertEqual((self.facts['screen']['parted'], self.facts['screen']['boundaries_the_tool_dropped']), (3, 7))  # 3 apart; 2 touching (407, 3.14); 2 on another baseline (6th, a raised 1)

    def test_touching_pieces_raised_marks_cells_amounts_and_a_period_before_a_letter_keep_their_text(self):
        for want in ('407 PARK', '3.14 PERCENT', '19.AAA HOLDINGS LLC', '1.', '10700', 'Total $1,234', 'Wholly-Owned  Active  Subsidiaries1', 'Exhibit 21.1',
                     '21.400 HIDDEN'):  # a box at opacity 0 beside a list number: the tool prints it, the page does not show it - no space for it
            with self.subTest(want=want): self.assertIn(want, self.texts)
        self.assertEqual(sorted(x for x in self.texts if ' ' not in x), ['1.', '10700'])  # the two cells stay two items

    def test_ids_kinds_and_anchors_stay_as_the_converter_gave_them(self):
        bare = edgartools_html.convert(PAGE, 'positioned.htm', hashlib.sha256(PAGE).hexdigest())
        shape = lambda r: [(u['id'], u['kind'], [x.get('anchor') for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u])]) for u in r['units']]
        self.assertEqual(shape(self.route), shape(bare))


if __name__ == '__main__':
    unittest.main()
