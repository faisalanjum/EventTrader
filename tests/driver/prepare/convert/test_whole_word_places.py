"""A text is placed at a copy the source reads as whole words before a copy cut out of a longer word or number (OCR's recheck on main d9c478584,
furniture_citations_20261009: three page numbers were cited inside "2025" and "104", and a bullet "o" inside the "of" of a "Table of Contents" link
the tool left out). Whether a place cuts a word is the scanner's reading with the gate's own boundary test (anchor._cuts): the page prints the two
characters touching - an inline tag adds no space, so CORP<span>ORATION is one word - and a space there would part a word or a number. A cut the tool
made itself is no fault: the item next to it in the tool's order (pictures and empty units aside) goes on with the word, or the item's own mark stands
there - inline pieces, a mark read as a unit of its own, an ordinal, a split decimal stand where they stood, even with a whole copy of their text after
them. A whole copy is evidence, not proof: with no copy that cuts nothing, the first copy is taken, as before."""
import copy
import json
import unittest
from pathlib import Path

from driver.prepare.convert import anchor

CASES = json.loads((Path(__file__).parent / 'fixtures' / 'furniture_citations.json').read_text())['cases']  # the four, from their sources' own bytes (fixture_v2.py)


def placed(parts):  # markup, and (text,) for each unit the tool read - in its order, where it stands; ('',) an empty unit, None a picture -> got, wanted
    raw, units, want = b'', [], []
    for p in parts:
        if p is None: units.append({'id': 'u%d' % len(units), 'kind': 'image', 'src': 'logo.png'}); want.append((None, None)); continue
        if isinstance(p, tuple): want.append((len(raw) if p[0] else None, None)); units.append({'id': 'u%d' % len(units), 'kind': 'text', 'text': p[0]}); p = p[0]
        raw += p.encode()
    out = anchor.link(raw, units, vis=anchor.Visible(raw))['units']
    return [((u['anchor'] or {}).get('byte_start') if u.get('anchor') else None, u.get('link_flag')) for u in out], want


def exhibits_then(page):  # an exhibit table the tool read with its 104 row first (WST's and KHC's tables), then a page number and the next heading
    raw = ('<table><tr><td>99.1</td><td>Press release dated February 13, 2025.</td></tr><tr><td>104</td><td>Cover page of the report dated February 13, 2025.</td></tr></table>'
           '<div style="text-align:center">%s</div><p>SIGNATURE</p>' % page).encode()
    cell = lambda r, c, t: {'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': t}
    units = [{'id': 't0', 'kind': 'table', 'cells': [cell(0, 0, '104'), cell(0, 1, 'Cover page of the report dated February 13, 2025.'), cell(1, 0, '99.1'), cell(1, 1, 'Press release dated February 13, 2025.')]},
             {'id': 'u1', 'kind': 'text', 'text': page}, {'id': 'u2', 'kind': 'text', 'text': 'SIGNATURE'}]
    out = anchor.link(raw, units, vis=anchor.Visible(raw))['units']
    return (out[1]['anchor']['byte_start'], out[1].get('link_flag')), (raw.index(('>%s</div>' % page).encode()) + 1, None)


class FourOriginals(unittest.TestCase):
    def test_the_four_stand_at_their_own_place_unflagged(self):  # each failed before: inside "2025", "104", "104" and "of"
        for c in CASES:
            raw = c['html'].encode(); out = anchor.link(raw, copy.deepcopy(c['units']), vis=anchor.Visible(raw))['units']; u = next(x for x in out if x['id'] == c['unit'])
            with self.subTest(file=c['source']['file'], unit=c['unit']):
                self.assertEqual((u['anchor'], u.get('link_flag')), ({'byte_start': c['true'], 'byte_end_exclusive': c['true'] + len(c['text'].encode())}, None))

    def test_every_other_unit_and_cell_of_their_excerpts_stands_where_it_stood(self):
        for c in CASES:
            raw = c['html'].encode(); out = anchor.link(raw, copy.deepcopy(c['units']), vis=anchor.Visible(raw))['units']
            got = [[u['id'], None if x is u else [x['r'], x['c']], x.get('anchor'), x.get('link_flag'), x.get('link_error')] for u in out for x in (u.get('cells') or [u]) if u['id'] != c['unit']]
            with self.subTest(file=c['source']['file'], unit=c['unit']): self.assertEqual(got, c['others'])


class WholeWordsFirst(unittest.TestCase):
    def test_a_page_number_after_an_exhibit_table_is_not_read_inside_its_numbers(self):  # each failed before: "4" in "104", "2" in "2025"
        for page in ('4', '2'):
            with self.subTest(page=page): self.assertEqual(*exhibits_then(page))

    def test_a_bullet_is_not_read_inside_a_link_the_tool_left_out(self):  # each failed before: the "o" of "of"
        for link, bullet in (('Table of Contents', '<div style="display:flex"><span style="display:inline-flex">%s</span><div style="display:inline">%s</div></div>'),  # PAYX's own boxes: the bullet stands apart
                             ('Table&#160;of&#160;Contents', '<p><span>%s</span><span>%s</span></p>')):  # no-break spaces; a bullet the page prints touching its text: the tool's own cut
            parts = ['<p>', ('Growth in the number of clients served;',), '</p><p><a href="#toc">%s</a></p>' % link]
            head, tail = bullet.split('%s', 1)[0], bullet.split('%s', 1)[1]; mid, end = tail.split('%s', 1)
            with self.subTest(link=link, bullet=bullet[:12]): self.assertEqual(*placed(parts + [head, ('o',), mid, ('Higher product penetration.',), end]))

    def test_a_text_the_tool_moved_is_read_at_an_earlier_whole_copy_not_inside_a_word(self):  # failed before: the "7" of "1997", the nearest earlier copy
        raw = b'<div>7</div><p>Filed in 1997 under the rule of the exchange.</p><p>Closing text of the agreement here.</p>'
        out = anchor.link(raw, [{'id': 'u0', 'kind': 'text', 'text': 'Filed in 1997 under the rule of the exchange.'}, {'id': 'u1', 'kind': 'text', 'text': 'Closing text of the agreement here.'},
                                {'id': 'u2', 'kind': 'text', 'text': '7'}], vis=anchor.Visible(raw))['units']  # the tool listed the page number last
        self.assertEqual([(u['anchor']['byte_start'], u.get('link_flag')) for u in out], [(raw.index(b'Filed'), None), (raw.index(b'Closing'), None), (5, 'out_of_order')])

    def test_repeated_page_and_list_numbers_after_texts_that_hold_the_same_digits(self):
        self.assertEqual(*placed(['<p>', ('Filed on May 1, 2021, and amended in 2022.',), '</p><div>', ('1',), '</div><p>', ('2.',), '</p><p>', ('Filed 2012.',), '</p><div>', ('2',), '</div><p>', ('3.',), '</p>']))


class ToolsOwnCutsStay(unittest.TestCase):  # a piece the tool cut out of a word keeps it, even with a whole copy of its text later in its window
    def test_inline_split_pieces_and_ordinals_with_a_whole_copy_after_them(self):
        for parts in ((['<p>', ('CORP',), '<span>', ('ORATION',), '</span></p><p>', ('CORP',), '</p>']),
                      (['<p>', ('Our',), ' ', ('1',), '<sup>', ('st',), '</sup> ', ('quarter.',), '</p><div>', ('1',), '</div>']),
                      (['<p>', ('Soci',), '<span>', ('été',), '</span></p><p>', ('Soci',), '</p><p>', ('été',), '</p>']),  # letters beyond ASCII, bytes beyond one per letter
                      (['<p>', ('CORP',), None, ('',), '<span>', ('ORATION',), '</span></p><p>', ('CORP',), '</p>'])):  # a picture and an empty unit between the pieces, in the tool's order
            with self.subTest(parts=[p[0] if isinstance(p, tuple) else p for p in parts if p is not None]): self.assertEqual(*placed(parts))

    def test_a_split_decimal_and_a_mark_read_as_units_with_whole_copies_after_them(self):
        for parts in ((['<p>Rate ', ('10',), '<span>', ('.5',), '</span></p><div>', ('10',), '</div>']),
                      (['<p>', ('Revenue',), '<sup>', ('1',), '</sup> ', ('rose.',), '</p><p><sup>', ('1',), '</sup> ', ('Net of returns.',), '</p>'])):
            with self.subTest(parts=[p[0] if isinstance(p, tuple) else p for p in parts]): self.assertEqual(*placed(parts))

    def test_marks_whole_cells_and_pieces_inside_a_cell_read_as_before(self):
        raw = b'<table><tr><td>Total<sup>(1)</sup></td><td>(1,234)</td><td>10.7</td><td>%</td></tr></table><p>1</p>'
        cell = lambda c, t, **k: dict({'r': 0, 'c': c, 'rs': 1, 'cs': 1, 'text': t}, **k)
        units = [{'id': 't', 'kind': 'table', 'cells': [cell(0, 'Total', markers=['(1)']), cell(1, '('), cell(2, '1,234'), cell(3, ')'), cell(4, '10.7 %')]}, {'id': 'p', 'kind': 'text', 'text': '1'}]
        out = anchor.link(raw, units, vis=anchor.Visible(raw))['units']; at = lambda s, k=0: [i for i in range(len(raw)) if raw.startswith(s, i)][k]
        got = [(x['anchor']['byte_start'], x['anchor']['byte_end_exclusive'], x.get('link_flag')) for x in out[0]['cells']] + [(out[1]['anchor']['byte_start'], out[1]['anchor']['byte_end_exclusive'], out[1].get('link_flag'))]
        self.assertEqual(got, [(at(b'Total'), at(b'(1)') + 3, None), (at(b'(1,'), at(b'(1,') + 1, None), (at(b'1,234'), at(b'1,234') + 5, None), (at(b')</td><td>10'), at(b')</td><td>10') + 1, None),
                               (at(b'10.7'), at(b'%') + 1, None), (at(b'>1</p>') + 1, at(b'>1</p>') + 2, None)])


if __name__ == '__main__':
    unittest.main()
