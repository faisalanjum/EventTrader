"""A table of the tool that is one table of the source is linked inside that table, and row by row where the tool kept its rows (merge group 2).
The first four cases are the worktree's (Codex); the others are the controls of the rule: what it must not tie, and what it must leave as it was."""
import copy
import itertools
import re
import unittest

from benchmarks.prepare.grader.anchor import Visible, link


def table(values, width=2, uid='t', rows=None):
    return {'id': uid, 'kind': 'table', 'cells': [{'r': rows[i] if rows else i // width, 'c': i % width, 'text': v} for i, v in enumerate(values)]}


starts = lambda unit: [c['anchor']['byte_start'] if c.get('anchor') else None for c in unit['cells']]


class TableSourcesTests(unittest.TestCase):
    def test_moved_rows_keep_repeated_labels_with_their_values(self):
        raw = b'<table><tr><td>LEC</td><td>22</td></tr><tr><td>LEC</td><td>33</td></tr></table>'
        unit = link(raw, [table(('LEC', '33', 'LEC', '22'))])['units'][0]
        self.assertEqual(starts(unit), [raw.rindex(b'>LEC') + 1, raw.index(b'33'), raw.index(b'>LEC') + 1, raw.index(b'22')])
        self.assertEqual([c.get('link_flag') for c in unit['cells']], [None, None, 'out_of_order', 'out_of_order'])  # the row the tool moved, and only that row

    def test_repeated_cell_never_binds_inside_another_cells_word(self):
        raw = b'<table><tr><td>ELECTRIC</td><td>11</td></tr><tr><td>LEC</td><td>22</td></tr><tr><td>LEC</td><td>33</td></tr></table>'
        for values in [('LEC', '22', 'ELECTRIC', '11', 'LEC', '33'), ('ELECTRIC', '11', 'LEC', '22', 'LEC', '33')]:
            with self.subTest(values=values):
                unit = link(raw, [table(values)])['units'][0]
                self.assertEqual([c['anchor']['byte_start'] for c in unit['cells'] if c['text'] == 'LEC'], [raw.index(b'>LEC') + 1, raw.rindex(b'>LEC') + 1])

    def test_lifted_header_cannot_bind_to_an_earlier_table(self):
        raw = (b'<table><tr><td>2020</td><td>Earlier</td></tr></table>'
               b'<table><tr><td>All figures as printed</td></tr><tr><td>2020</td></tr><tr><td>Only this row</td><td>29</td></tr></table>')
        unit = {'id': 't', 'kind': 'table', 'cells': [{'text': '2020', 'r': 0, 'c': 0}, {'text': 'All figures as printed', 'r': 1, 'c': 0}, {'text': 'Only this row', 'r': 2, 'c': 0}, {'text': '29', 'r': 2, 'c': 1}]}
        cells = link(raw, [unit])['units'][0]['cells']
        self.assertEqual(cells[0]['anchor']['byte_start'], raw.rindex(b'2020'))
        for c in cells: self.assertEqual(raw[c['anchor']['byte_start']:c['anchor']['byte_end_exclusive']], c['text'].encode())

    def test_same_values_in_distinct_tables_keep_their_source_rows(self):
        raw = (b'<table><tr><td>Alpha overall comparison</td></tr><tr><td>2020</td></tr><tr><td>First basis</td><td>0</td></tr></table>'
               b'<table><tr><td>Beta overall comparison</td></tr><tr><td>2020</td></tr><tr><td>Second basis</td><td>0</td></tr></table>')
        units = [{'id': title, 'kind': 'table', 'cells': [{'text': text, 'r': i, 'c': 0} for i, text in enumerate(('2020', title, label, '0'))]}
                 for title, label in [('Alpha overall comparison', 'First basis'), ('Beta overall comparison', 'Second basis')]]
        out = link(raw, units)['units']
        self.assertEqual([u['cells'][0]['anchor']['byte_start'] for u in out], [raw.index(b'2020'), raw.rindex(b'2020')])

    def test_a_text_twice_in_a_row_keeps_the_rows_order(self):
        raw = b'<table><tr><td>3.1</td><td>Second</td><td>10-Q</td><td>3.1</td></tr><tr><td>3.2</td><td>Third</td><td>8-K</td><td>3.1</td></tr></table>'
        unit = link(raw, [table(('3.2', 'Third', '8-K', '3.1', '3.1', 'Second', '10-Q', '3.1'), width=4)])['units'][0]  # the rows moved: the first row's two "3.1" stay in their columns
        self.assertEqual(starts(unit)[3:], [raw.rindex(b'3.1'), raw.index(b'3.1'), raw.index(b'Second'), raw.index(b'10-Q'), raw.index(b'3.1', raw.index(b'10-Q'))])

    def test_a_cell_stands_in_a_cell_never_in_the_same_words_beside_the_cells(self):
        raw = b'<table><caption>Total</caption><tr><td>Net</td><td>7</td></tr><tr><td>Total</td><td>9</td></tr></table>'
        unit = link(raw, [table(('Total', '9', 'Net', '7'))])['units'][0]  # the tool lists the last row first: the caption's "Total" comes first in the source
        self.assertEqual(starts(unit), [raw.rindex(b'Total'), raw.index(b'9'), raw.index(b'Net'), raw.index(b'7')])

    def test_rows_the_tool_did_not_keep_are_no_evidence_and_no_cell_loses_its_place(self):
        raw = b'<table><tr><td>X</td><td>1</td></tr><tr><td>X</td></tr><tr><td>2</td></tr></table>'  # the tool's rows: X | 1 | X | 2 — its two rows "X" would both be the source's one row "X"
        unit = link(raw, [table(('X', '1', 'X', '2'), rows=[0, 1, 2, 3])])['units'][0]
        self.assertEqual(starts(unit), [raw.index(b'X'), raw.index(b'1'), raw.rindex(b'X'), raw.index(b'2')])
        self.assertFalse(any(c.get('link_error') for c in unit['cells']))

    def test_a_cell_whose_places_are_known_takes_the_one_that_is_free(self):
        raw = b'<table><tr><td>X</td><td>aXa</td></tr><tr><td>X</td><td>bXb</td></tr><tr><td>X</td><td>cXc</td></tr></table>'
        unit = link(raw, [table(('X', 'X', 'aXa', 'bXb', 'cXc', 'X'), rows=[0, 0, 0, 1, 2, 2])])['units'][0]  # rows the tool did not keep; the second X finds no X between its neighbours
        xs = [m.start() + 1 for m in re.finditer(b'>X<', raw)]
        self.assertEqual(starts(unit), [xs[0], xs[1], raw.index(b'aXa'), raw.index(b'bXb'), raw.index(b'cXc'), xs[2]])  # never the X inside another cell's word
        self.assertEqual([c.get('link_error') for c in unit['cells']], [None] * 6)

    def test_rows_not_kept_a_cell_still_starts_only_where_a_cell_starts(self):
        raw = b'<table><tr><td>LEC</td><td>1</td></tr><tr><td>ELECTRIC</td><td>2</td></tr><tr><td>LEC</td><td>3</td></tr></table>'
        unit = link(raw, [table(('LEC', '1', 'LEC', '3', 'ELECTRIC', '2'), rows=[0] * 6)])['units'][0]  # the second LEC looks between "1" and "3": ELECTRIC stands there
        self.assertEqual(starts(unit)[2], raw.rindex(b'>LEC') + 1)

    def test_not_between_its_neighbours_a_cell_takes_the_nearest_earlier_place_of_its_own(self):
        raw = b'<table><tr><td>LEC</td><td>1</td></tr><tr><td>LEC</td><td>2</td></tr><tr><td>ELECTRIC</td><td>3</td></tr><tr><td>LEC</td><td>4</td></tr></table>'
        unit = link(raw, [table(('3', 'LEC', '4', 'LEC', '1', 'LEC', '2', 'ELECTRIC'), rows=[0] * 8)])['units'][0]
        cells = [m.start() + 1 for m in re.finditer(b'>LEC<', raw)]
        self.assertEqual([starts(unit)[k] for k in (1, 3, 5)], [cells[2], cells[1], cells[0]])  # the second, listed after "4": not the taken last one, not inside ELECTRIC, not the first

    def test_rows_that_read_alike_are_not_told_apart(self):
        raw = b'<table><tr><td>A</td><td>1</td></tr><tr><td>A</td><td>1</td></tr><tr><td>B</td><td>2</td></tr></table>'
        unit = link(raw, [table(('A', '1', 'A', '1', 'B', '2'))])['units'][0]
        self.assertEqual(starts(unit), [m.start() + 1 for m in re.finditer(b'>[AB12]<', raw)])  # each in turn, none lost

    def test_a_place_another_cell_holds_is_never_taken_twice(self):
        raw = b'<table><tr><td>X</td><td>u</td></tr><tr><td>X</td><td>v</td></tr><tr><td>X</td><td>v</td></tr></table>'  # the first X is the row "X u"'s own, wherever the tool lists that row
        unit = link(raw, [table(('X', 'v', 'u', 'X', 'X', 'v'))])['units'][0]
        xs = [m.start() + 1 for m in re.finditer(b'>X<', raw)]
        self.assertEqual([starts(unit)[k] for k in (0, 3, 4)], [xs[1], xs[0], xs[2]])

    def test_a_cell_keeps_its_place_from_a_text_the_tool_lists_before_the_table(self):
        raw = b'<table><tr><td>Total</td><td>5</td></tr></table><p>Total</p>'
        out = link(raw, [{'id': 'p', 'kind': 'text', 'text': 'Total'}, table(('Total', '5'))])['units']
        self.assertEqual(starts(out[1]), [raw.index(b'Total'), raw.index(b'5')])

    def test_a_text_the_tool_lists_before_its_table_takes_no_cell_and_no_cell_leaves_its_table(self):  # Codex G2-C1, his four probes and their controls
        for value in ('Revenue from continuing operations', 'Adjusted income available to common shareholders'):
            for row in ([value, 'X'], ['X', value]):
                raw = ('<table>' + ''.join('<tr>' + ''.join('<td>' + x + '</td>' for x in row) + '</tr>' for _ in range(2)) + '</table><p>' + value + '</p>').encode()
                prose, own = {'id': 'p', 'kind': 'text', 'text': value}, [m.start() for m in re.finditer(re.escape(value.encode()), raw)]
                for units in ([table(row * 2), prose], [prose, table(row * 2)]):
                    with self.subTest(value=value, row=row, first=units[0]['kind']):
                        out = {u['id']: u for u in link(raw, copy.deepcopy(units))['units']}
                        self.assertEqual(out['p']['anchor']['byte_start'], own[2])  # the paragraph stands at the paragraph
                        self.assertEqual([c['anchor']['byte_start'] for c in out['t']['cells'] if c['text'] == value], own[:2])  # each label in its own row
                        self.assertTrue(all(isinstance(c['anchor'], dict) and c['anchor']['byte_end_exclusive'] <= raw.index(b'</table>') for c in out['t']['cells']))  # every cell exact, inside its table

    def test_a_text_not_between_its_neighbours_falls_back_on_no_cell_either(self):
        raw = b'<p>Total sum</p><table><tr><td>Total sum</td><td>X</td></tr><tr><td>Total sum</td><td>X</td></tr></table><p>end</p>'
        out = link(raw, [{'id': 'e', 'kind': 'text', 'text': 'end'}, {'id': 'p', 'kind': 'text', 'text': 'Total sum'}, table(('Total sum', 'X', 'Total sum', 'X'))])['units']
        own = [m.start() for m in re.finditer(b'Total sum', raw)]
        self.assertEqual((out[1]['anchor']['byte_start'], [c['anchor']['byte_start'] for c in out[2]['cells'] if c['text'] == 'Total sum']), (own[0], own[1:]))

    def test_a_long_text_looked_for_everywhere_passes_over_the_cells(self):
        label = 'Revenue from continuing operations'
        raw = ('<table>' + '<tr><td>%s</td><td>X</td></tr>' % label * 2 + '</table><p>%s</p><p>%s</p><p>closing words of this page</p>' % (label, label)).encode()
        prose = lambda k: {'id': k, 'kind': 'text', 'text': label}
        out = {u['id']: u for u in link(raw, [{'id': 'c', 'kind': 'text', 'text': 'closing words of this page'}, prose('p1'), prose('p2'), table((label, 'X') * 2)])['units']}
        own = [m.start() for m in re.finditer(label.encode(), raw)]
        self.assertEqual(([out[k]['anchor']['byte_start'] for k in ('p1', 'p2')], [c['anchor']['byte_start'] for c in out['t']['cells'] if c['text'] == label]), (own[2:], own[:2]))

    def test_a_text_the_source_prints_only_in_the_cells_is_pieced_onto_none(self):
        label = 'Revenue from continuing operations'
        raw = ('<table>' + '<tr><td>%s</td><td>X</td></tr>' % label * 2 + '</table><p>closing words of this page</p>').encode()
        out = {u['id']: u for u in link(raw, [{'id': 'p', 'kind': 'text', 'text': label}, table((label, 'X') * 2)])['units']}
        self.assertEqual((out['p']['anchor'], out['p'].get('link_error')), (None, 'not_in_source'))  # the tool gave the label a third time: the source has two, and they are the cells'
        self.assertEqual([c['anchor']['byte_start'] for c in out['t']['cells'] if c['text'] == label], [m.start() for m in re.finditer(label.encode(), raw)])

    def test_a_cell_between_its_marks_is_one_copy_for_one_unit(self):  # Codex G2-R2: the position kept was the first mark's, so the next cell that reads the same took the same copy
        for value in ('100', 'Revenue from continuing operations'):
            for marks in ([], ['(a)'], ['(a)', '(b)'], ['(b)', '(a)']):
                rows = [['(a)', value, '(b)'], ['(a)', value, '(b)'], ['X', 'Y', 'Z']]
                raw = ('<table>' + ''.join('<tr>' + ''.join('<td>' + x + '</td>' for x in row) + '</tr>' for row in rows) + '</table><p>' + value + '</p>').encode()
                own = [m.start() for m in re.finditer(re.escape(value.encode()), raw)][:2]
                for order in itertools.permutations(range(3)):
                    cells = [dict({'r': r, 'c': c, 'text': x}, **({'markers': marks} if x == value and marks else {})) for r in order for c, x in enumerate(rows[r])]
                    for units in ([{'id': 't', 'kind': 'table', 'cells': cells}], [{'id': 'p', 'kind': 'text', 'text': value}, {'id': 't', 'kind': 'table', 'cells': cells}]):
                        with self.subTest(value=value, marks=marks, order=order, prose_first=len(units) == 2):
                            out = next(u for u in link(raw, copy.deepcopy(units))['units'] if u['id'] == 't')
                            held = [next((p for p in own if isinstance(c.get('anchor'), dict) and c['anchor']['byte_start'] <= p and p + len(value) <= c['anchor']['byte_end_exclusive']), None) for c in out['cells'] if c['text'] == value]
                            self.assertEqual(sorted(p for p in held if p is not None), own)  # each of the two copies under one of the two cells

    def test_a_text_between_two_marks_is_one_copy_for_one_unit_outside_tables_too(self):
        label = 'Revenue from continuing operations'
        raw = ('<p><sup>1</sup>%s<sup>2</sup></p>' % label * 2 + '<p>closing words of this page</p>').encode()
        unit = lambda k: {'id': k, 'kind': 'text', 'text': label, 'markers': ['1', '2']}
        out = {u['id']: u for u in link(raw, [unit('a'), {'id': 'c', 'kind': 'text', 'text': 'closing words of this page'}, unit('b')])['units']}  # the second is listed after the page's last words: it is looked for from the start
        own = [m.start() for m in re.finditer(label.encode(), raw)]
        self.assertEqual([[p for p in own if out[k]['anchor']['byte_start'] <= p < out[k]['anchor']['byte_end_exclusive']] for k in ('a', 'b')], [[own[0]], [own[1]]])

    def test_two_tables_of_the_tool_with_one_tables_texts_are_tied_to_none(self):
        raw = b'<p>A 1</p><table><tr><td>A</td><td>1</td></tr></table>'  # which of the two is the source's table is not known: both are placed as before, between their neighbours
        units = [table(('A', '1'), uid='t1'), table(('A', '1'), uid='t2')]
        out = link(raw, copy.deepcopy(units))['units']
        self.assertEqual(starts(out[0]), [raw.index(b'A'), raw.index(b'1')])  # the first copy, in the paragraph: no tie held it to the table
        self.assertEqual(starts(out[1]), [raw.rindex(b'A'), raw.rindex(b'1')])

    def test_two_tables_of_the_source_with_the_same_texts_are_taken_in_order(self):
        one = b'<table><tr><td>A</td><td>1</td></tr></table>'
        raw = one + b'<p>between the two tables stands a sentence</p>' + one
        out = link(raw, [table(('A', '1'), uid='t1'), {'id': 'p', 'kind': 'text', 'text': 'between the two tables stands a sentence'}, table(('A', '1'), uid='t2')])['units']
        self.assertEqual(starts(out[0]) + starts(out[2]), [raw.index(b'A'), raw.index(b'1'), raw.rindex(b'A'), raw.rindex(b'1')])

    def test_an_empty_cell_is_placed_nowhere(self):
        raw = b'<table><tr><td>A</td><td></td></tr><tr><td>B</td><td>2</td></tr></table>'
        unit = link(raw, [table(('A', '', 'B', '2'))])['units'][0]
        self.assertNotIn('anchor', unit['cells'][1])
        self.assertEqual([s for s in starts(unit) if s is not None], [raw.index(b'A'), raw.index(b'B'), raw.index(b'2')])

    def test_a_nested_table_is_a_table_of_its_own(self):
        raw = b'<table><tr><td>7</td><td><table><tr><td>7</td><td>inner</td></tr></table></td></tr></table>'
        out = link(raw, [table(('7', 'inner'), uid='inner')])['units'][0]
        self.assertEqual(starts(out), [raw.rindex(b'7'), raw.index(b'inner')])  # the inner table's own 7, not the outer cell's

    def test_a_mark_kept_apart_is_still_covered_beside_its_cell(self):
        raw = b'<table><tr><td>Revenue</td><td>(1)</td><td>5</td></tr></table>'
        unit = {'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'markers': ['(1)']}, {'r': 0, 'c': 1, 'text': '(1)'}, {'r': 0, 'c': 2, 'text': '5'}]}
        cells = link(raw, [unit])['units'][0]['cells']
        self.assertEqual((cells[0]['anchor']['byte_start'], cells[2]['anchor']['byte_start']), (raw.index(b'Revenue'), raw.index(b'5')))


class SourceTablesTests(unittest.TestCase):
    """The scanner's record of the source's tables (the worktree's tokenizer cases, asked of the reader main already has)."""
    cells = staticmethod(lambda raw: [[[raw[a:b] for a, b in row] for row in t] for t in Visible(raw).tables])

    def test_each_table_owns_its_own_cells_and_a_nested_one_is_its_own(self):
        inner = b'<table><tr><th>inner</th></tr></table>'
        raw = b'<!-- <table><td>fake</td></table> --><table><tr><td>before' + inner + b'after</td><td>next</td></tr></table><table><tr><td>last</td></tr></table>'
        self.assertEqual(self.cells(raw), [[[b'<td>before' + inner + b'after', b'<td>next']], [[b'<th>inner']], [[b'<td>last']]])

    def test_empty_unclosed_and_omitted_ends(self):
        self.assertEqual(self.cells(b'<table></table><table><tr><td>first<td>last'), [[], [[b'<td>first', b'<td>last']]])
        self.assertEqual(self.cells(b'<table><tr><th>A<td>B<tr><td>C</table><p>outside</p>'), [[[b'<th>A', b'<td>B'], [b'<td>C']]])
        nested = b'<table><tr><td>inner</td></tr></table>'
        self.assertEqual(self.cells(b'<table><tr><td rowspan="2">A' + nested + b'</td><td>B<tr><td>C</table>'), [[[b'<td rowspan="2">A' + nested, b'<td>B'], [b'<td>C']], [[b'<td>inner']]])

    def test_a_cell_outside_any_row_stands_in_the_row_the_parser_makes(self):
        self.assertEqual(self.cells(b'<table><td>A<td>B</table><table><tr><th>C</th></tr></table>'), [[[b'<td>A', b'<td>B']], [[b'<th>C']]])
        self.assertEqual(self.cells(b'<table><tr><td>a</td></tr><td>b</td><tbody><td>c</td><td>d</td></tbody></table>'), [[[b'<td>a'], [b'<td>b'], [b'<td>c', b'<td>d']]])

    def test_what_is_no_markup_holds_no_cell_and_ends_none(self):
        real = b'<table><tr><td>real</td></tr></table>'
        for fake in (b'<!-- <td>comment</td> -->', b'<script>let x = "<td>script</td>";</script>', b'<style>p:after {content:"<td>style</td>"}</style>', b'<div title="<td>attribute</td>">text</div>',
                     b'<textarea><td>literal</td></textarea>', b'<title><td>literal</td></title>'):
            with self.subTest(fake=fake): self.assertEqual(self.cells(fake + real), [[[b'<td>real']]])
        for literal in (b'<!-- </td> -->', b'<script>let x="</td>";</script>', b'<span title="</td>">label</span>'):
            with self.subTest(literal=literal): self.assertEqual(self.cells(b'<table><tr><TH>before' + literal + b'after</TH></tr></table>'), [[[b'<TH>before' + literal + b'after']]])
        self.assertEqual(self.cells(real + b'<plaintext><table><td>fake</td></table></plaintext><table><td>also fake</td></table>'), [[[b'<td>real']]])

    def test_spans_are_bytes_of_the_original(self):
        raw = '<p>€</p>\r\n<table><tr><TD title="a > b">é</TD><td>x</td></tr></table>'.encode()
        self.assertEqual(self.cells(raw), [[['<TD title="a > b">é'.encode(), b'<td>x']]])


class NeverAcrossCells(unittest.TestCase):
    def test_a_text_is_never_found_across_two_cells(self):  # Codex C4: "10.8" was read from "10.1" and "0.82" in two cells of a table the linker had not tied
        raw = b'<table><tr><td>10.1</td><td>0.82</td></tr></table><p>then 10.8 here</p>'
        out = link(raw, [{'id': 'u', 'kind': 'text', 'text': '10.8'}])['units'][0]; self.assertEqual(raw[out['anchor']['byte_start']:out['anchor']['byte_end_exclusive']], b'10.8')
        raw = b'<table><tr><td>10.1</td><td>0.82</td></tr></table>'
        self.assertEqual(link(raw, [{'id': 'u', 'kind': 'text', 'text': '10.8'}])['units'][0].get('link_error'), 'not_in_source')
        raw = b'<table><tr><td>10.7</td><td>%</td><td>x</td></tr></table>'  # a value cell and its sign cell merged by the tool: whole cells, allowed
        u = link(raw, [{'id': 'u', 'kind': 'text', 'text': '10.7 %'}])['units'][0]; self.assertEqual(raw[u['anchor']['byte_start']:u['anchor']['byte_end_exclusive']], b'10.7</td><td>%')
        self.assertEqual(link(raw, [{'id': 'u', 'kind': 'text', 'text': '0.7 %'}])['units'][0].get('link_error'), 'not_in_source')  # part of one cell and the next: no
        self.assertEqual(link(raw, [{'id': 'u', 'kind': 'text', 'text': '% x'}])['units'][0].get('anchor', {}).get('byte_start'), raw.index(b'%'))
        raw = b'<table><tr><td>$</td><td>5</td><td>a</td><td>bc</td></tr></table>yz'  # one-character cells merge whole; a part of a cell never; a cell and the prose after the table never
        got = lambda text: link(raw, [{'id': 'u', 'kind': 'text', 'text': text}])['units'][0]
        self.assertEqual(raw[got('$5')['anchor']['byte_start']:got('$5')['anchor']['byte_end_exclusive']], b'$</td><td>5'); self.assertEqual(got('ab').get('link_error'), 'not_in_source'); self.assertEqual(got('cy').get('link_error'), 'not_in_source'); self.assertEqual(got('bcyz').get('link_error'), 'not_in_source')
        raw = b'<table><tr><td>alpha beta gamma delta epsilon zeta</td><td>eta theta iota kappa lambda mu nu xi omicron pi</td></tr></table>'
        u = link(raw, [{'id': 'u', 'kind': 'text', 'text': 'zeta eta theta iota kappa lambda mu nu xi omicron pi and words the source never prints anywhere at all'}])['units'][0]  # the first short piece straddles two cells: the chaining starts inside one
        self.assertTrue(all(raw[a['byte_start']:a['byte_end_exclusive']].count(b'<td') == 0 for a in anchor_spans(u.get('anchor'))))
        u = link(raw, [{'id': 'u', 'kind': 'text', 'text': 'alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi and words the source never prints anywhere at all'}])['units'][0]  # a block that would run on into the next cell stops at its edge
        self.assertEqual(u.get('link_flag'), 'pieced'); self.assertTrue(all(raw[a['byte_start']:a['byte_end_exclusive']].count(b'<td') == 0 for a in anchor_spans(u.get('anchor'))))
        raw = b'xy<table><tr><td>z</td></tr></table>'; self.assertEqual(link(raw, [{'id': 'u', 'kind': 'text', 'text': 'yz'}])['units'][0].get('link_error'), 'not_in_source')  # prose and a cell: never one text
        raw = b'<table><tr><td>total 10</td><td>.82 next</td></tr></table>'; long = 'total 10.82 next'  # nor pieced across them
        u = link(raw, [{'id': 'u', 'kind': 'text', 'text': long + ' and more words that the source does not print at all here'}])['units'][0]
        self.assertTrue(all(raw[a['byte_start']:a['byte_end_exclusive']].count(b'<td') == 0 for a in anchor_spans(u.get('anchor'))))

    def test_nor_found_before_its_window_across_two_cells(self):  # the backward search (out_of_order) refuses the same places
        raw = b'<table><tr><td>10.1</td><td>0.82</td></tr></table><p>later</p>'
        units = link(raw, [{'id': 'a', 'kind': 'text', 'text': 'later'}, {'id': 'u', 'kind': 'text', 'text': '10.8'}])['units']
        self.assertEqual(units[1].get('link_error'), 'not_in_source'); self.assertEqual(raw[units[0]['anchor']['byte_start']:], b'later</p>')


def anchor_spans(a):
    return a if isinstance(a, list) else [a] if isinstance(a, dict) else []


if __name__ == '__main__':
    unittest.main()
