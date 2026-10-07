"""The screen step's cells are the source's cells: its marks and spans come from the scanner's record of the tables, and a cell that holds a table
resumes after it (Codex's worktree cases for `tag_cells` and `apply`, kept as written; merge group 2, C3)."""
import unittest

from driver.prepare.convert import screen_grid as sg


class CellTokenizerTests(unittest.TestCase):
    def test_fake_cells_in_non_markup_do_not_change_bytes_or_numbering(self):
        for fake in (b'<!-- <td>comment</td> -->',
                     b'<script>let x = "<td>script</td>";</script>',
                     b'<style>p:after {content:"<td>style</td>"}</style>',
                     b'<div title="<td>attribute</td>">text</div>',
                     b'<textarea><td>literal</td></textarea>',
                     b'<title><td>literal</td></title>'):
            with self.subTest(fake=fake):
                real = b'<table><tr><td>real</td></tr></table>'
                raw = fake + real
                marked, spans = sg.tag_cells(raw)
                self.assertEqual(marked, fake + real.replace(b'<td>', b'<td data-g="0">'))
                self.assertEqual([raw[s:e] for s, e in spans], [b'<td>real</td>'])

    def test_nested_cell_does_not_end_outer_cell(self):
        inner = b'<table><tr><th>inner</th></tr></table>'
        outer = b'<td>before' + inner + b'after</td>'
        raw = b'<table><tr>' + outer + b'<td>next</td></tr></table>'
        marked, spans = sg.tag_cells(raw)
        self.assertEqual([raw[s:e] for s, e in spans], [outer, b'<th>inner</th>', b'<td>next</td>'])
        self.assertEqual(marked.count(b'data-g="'), 3)
        cells = [{'text': text, 'r': 9, 'c': 9,
                  'anchor': {'byte_start': raw.index(text.encode()),
                             'byte_end_exclusive': raw.index(text.encode()) + len(text)}}
                 for text in ('before', 'inner', 'after', 'next')]
        boxes = {0: [{'g': 0, 'row': 0, 'x': 0, 'w': 100}, {'g': 2, 'row': 0, 'x': 100, 'w': 100}],
                 1: [{'g': 1, 'row': 0, 'x': 20, 'w': 20}]}
        sg.apply([{'kind': 'table', 'cells': cells}], spans, boxes)
        self.assertEqual([(c['r'], c['c']) for c in cells], [(0, 0), (0, 0), (0, 0), (0, 1)])

    def test_fake_end_tags_inside_cell_do_not_truncate_its_span(self):
        for literal in (b'<!-- </td> -->', b'<script>let x="</td>";</script>',
                        b'<span title="</td>">label</span>'):
            for cell_tag in (b'td', b'TH'):
                with self.subTest(literal=literal, cell_tag=cell_tag):
                    cell = b'<' + cell_tag + b'>before' + literal + b'after</' + cell_tag + b'>'
                    raw = b'<table><tr>' + cell + b'</tr></table>'
                    _, spans = sg.tag_cells(raw)
                    self.assertEqual([raw[s:e] for s, e in spans], [cell])

    def test_plaintext_keeps_everything_after_it_literal_including_fake_end_tag(self):
        real = b'<table><tr><td>real</td></tr></table>'
        literal = b'<plaintext><table><td>fake</td></table></plaintext><table><td>also fake</td></table>'
        marked, spans = sg.tag_cells(real + literal)
        self.assertEqual(marked, real.replace(b'<td>', b'<td data-g="0">') + literal)
        self.assertEqual(len(spans), 1)

    def test_omitted_cell_ends_stop_at_next_cell_row_or_table(self):
        raw = b'<table><tr><th>A<td>B<tr><td>C</table><p>outside</p>'
        _, spans = sg.tag_cells(raw)
        self.assertEqual([raw[s:e] for s, e in spans], [b'<th>A', b'<td>B', b'<td>C'])

    def test_byte_offsets_preserve_unicode_crlf_and_quoted_angle_brackets(self):
        raw = '<p>€</p>\r\n<table><tr><TD title="a > b">é</TD><td>x</td></tr></table>'.encode()
        marked, spans = sg.tag_cells(raw)
        self.assertEqual([raw[s:e] for s, e in spans], ['<TD title="a > b">é</TD>'.encode(), b'<td>x</td>'])
        self.assertEqual(marked.replace(b' data-g="0"', b'').replace(b' data-g="1"', b''), raw)

    def test_non_cell_markup_and_outside_text_are_not_regridded(self):
        raw = b'<table><tr><td>inside</td></tr></table><p>outside</p>'
        _, spans = sg.tag_cells(raw)
        cells = [{'text': text, 'r': 8, 'c': 8, 'anchor': {'byte_start': raw.index(text.encode())}}
                 for text in ('inside', 'outside')]
        sg.apply([{'kind': 'table', 'cells': cells}], spans, {0: [{'g': 0, 'row': 0, 'x': 0, 'w': 100}]})
        self.assertEqual(cells[0]['grid'], 'screen')
        self.assertNotIn('grid', cells[1])

    def test_text_after_a_table_with_omitted_cell_ends_is_no_cell_of_it(self):  # Codex G2-C3: the plain search ran the last cell on to the end of the source
        raw = b'<table><tr><td>A<td>B<tr><td>C</table><p>C</p>'
        _, spans = sg.tag_cells(raw)
        cells = [{'text': 'C', 'r': 8, 'c': 8, 'anchor': {'byte_start': raw.rindex(b'C'), 'byte_end_exclusive': raw.rindex(b'C') + 1}}]
        sg.apply([{'kind': 'table', 'cells': cells}], spans, {0: [{'g': 2, 'row': 1, 'x': 0, 'w': 100}]})
        self.assertNotIn('grid', cells[0])


if __name__ == '__main__':
    unittest.main()
