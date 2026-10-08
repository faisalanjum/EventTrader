"""A table whose every cell the screen step measures in one source table is listed row by row, as the route's cells are (DESIGN §4), whatever order the
tool listed its rows in (accuracy-fable-1, Codex's finding on the 86 repeated-text cells: ICE's quarters before their year, LPX's additions before their
opening balance); each cell record stays whole, only its place in the list moves. A table with a cell not measured, or with cells measured in two tables
(one inside the other), keeps the tool's order: their coordinates are not one grid."""
import unittest

from driver.prepare.convert import screen_grid as sg

RAW = b'<table><tr><td>2024</td></tr><tr><td>Fourth quarter</td><td>2,518</td></tr><tr><td>Third quarter</td><td>2,518</td></tr></table>'
TEXTS, ROWS, XS = ['2024', 'Fourth quarter', '2,518', 'Third quarter', '2,518'], [0, 1, 1, 2, 2], [0, 0, 100, 0, 100]  # source cells g 0..4


def table(order, unmeasured=()):  # the tool's table, its cells in `order` (source cell numbers); cells in `unmeasured` carry no anchor
    _, spans = sg.tag_cells(RAW)
    cells = [{'r': 9, 'c': 9, 'rs': 1, 'cs': 1, 'text': TEXTS[g], 'struck_at': [[0, 1]] if g == 3 else None,
              'anchor': None if k in unmeasured else {'byte_start': spans[g][0], 'byte_end_exclusive': spans[g][1]}} for k, g in enumerate(order)]
    return [{'id': 't', 'kind': 'table', 'cells': cells}], spans, {0: [{'g': g, 'row': ROWS[g], 'x': XS[g], 'w': 80} for g in range(5)]}


def kept(cell): return {k: v for k, v in cell.items() if k not in ('r', 'c', 'cs', 'grid')}


class ScreenRowMajor(unittest.TestCase):
    def test_a_table_measured_in_one_source_table_is_listed_row_by_row(self):  # failed before: the quarters stood before their year
        units, spans, measured = table([1, 2, 3, 4, 0]); before = {id(c): kept(c) for c in units[0]['cells']}
        sg.apply(units, spans, measured); cells = units[0]['cells']
        self.assertEqual([(c['text'], c['r'], c['c']) for c in cells], [('2024', 0, 0), ('Fourth quarter', 1, 0), ('2,518', 1, 1), ('Third quarter', 2, 0), ('2,518', 2, 1)])
        self.assertEqual({id(c): kept(c) for c in cells}, before)  # the same records, whole: only their place in the list and their measured coordinates

    def test_cells_that_share_a_place_keep_their_order(self):
        units, spans, measured = table([2, 1, 1, 0]); units[0]['cells'][1]['text'], units[0]['cells'][2]['text'] = 'Fourth', 'quarter'  # the tool split one source cell
        sg.apply(units, spans, measured)
        self.assertEqual([c['text'] for c in units[0]['cells']], ['2024', 'Fourth', 'quarter', '2,518'])

    def test_a_table_with_a_cell_not_measured_keeps_the_tool_order(self):
        units, spans, measured = table([1, 2, 3, 4, 0], unmeasured=(4,))
        sg.apply(units, spans, measured)
        self.assertEqual([c['text'] for c in units[0]['cells']], ['Fourth quarter', '2,518', 'Third quarter', '2,518', '2024'])

    def test_cells_measured_in_two_tables_keep_the_tool_order(self):
        inner = b'<table><tr><th>inner</th></tr></table>'; raw = b'<table><tr><td>before' + inner + b'after</td><td>next</td></tr></table>'
        _, spans = sg.tag_cells(raw)
        cells = [{'text': t, 'r': 9, 'c': 9, 'anchor': {'byte_start': raw.index(t.encode()), 'byte_end_exclusive': raw.index(t.encode()) + len(t)}} for t in ('next', 'inner', 'before')]
        sg.apply([{'kind': 'table', 'cells': cells}], spans, {0: [{'g': 0, 'row': 0, 'x': 0, 'w': 100}, {'g': 2, 'row': 0, 'x': 100, 'w': 100}], 1: [{'g': 1, 'row': 0, 'x': 20, 'w': 20}]})
        self.assertEqual([c['text'] for c in cells], ['next', 'inner', 'before'])


if __name__ == '__main__':
    unittest.main()
