"""Accepted evaluator repairs (public scorer v15 lineage, v16, cell closing boundary v2) on saved public invented sources and routes:
the cell whose own source bytes hold the key's anchor (through its own closing tag) owns it, a holder of it never does; a title carried
inside a larger faithful cell; a heading in an earlier row of the value's own table, in source order. Fixtures: fixtures/source_ownership."""
import copy
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade

F = Path(__file__).with_name('fixtures') / 'source_ownership'
NESTED = (F / 'nested_cell.htm').read_bytes()
NESTED_ROUTE = json.loads((F / 'nested_cell_route.json').read_text())


def at(raw, text, n=1, upto=None):  # byte span of the n-th occurrence of `text` in the source; `upto`: through the next occurrence of that text
    i = -1
    for _ in range(n): i = raw.index(text, i + 1)
    return {'byte_start': i, 'byte_end_exclusive': raw.index(upto, i + len(text)) + len(upto) if upto else i + len(text)}


def nested_target(anchor):
    return {'key_id': 'public/T1', 'file_id': NESTED_ROUTE['file_id'], 'type': 'cell', 'format': 'cell/html', 'split': 'public', 'anchor': anchor, 'excluded': set(),
            'alternatives': {}, 'support': {'row_label': {'anchors': [at(NESTED, b'Inventory')]}, 'header_path': {'anchors': [at(NESTED, b'2031')]}},
            'fields': {'printed_value': '37', 'display_value': '37', 'value_kind': 'number', 'row_label': 'Inventory', 'header_path': ['2031'], 'table_title': [],
                       'section_path': [], 'footnote_markers': [], 'periods': []}}


def verdicts(route, raw, t, check=None):
    g = grade.Grader(copy.deepcopy(t), grade.RouteFile(copy.deepcopy(route), raw)); g.grade_cell(); rows = {r['check']: r['verdict'] for r in g.rows}
    return rows if check is None else rows.get(check, 'no_row')


def inner_table(route):  # the innermost route table holding a cell at the value's own content
    return min((u for u in route['units'] if u.get('kind') == 'table' and any(grade.overlap(c.get('anchor'), at(NESTED, b'37')) for c in u.get('cells', []))),
               key=lambda u: u['anchor']['byte_end_exclusive'] - u['anchor']['byte_start'])


class NestedCellOwnershipTests(unittest.TestCase):
    def test_every_source_bound_form_of_the_value_cell_names_the_inner_cell(self):
        for anchor in (at(NESTED, b'37'), at(NESTED, b'<td id="value">37'), at(NESTED, b'<td id="value">37</td>'),
                       [at(NESTED, b'<td id="value">'), at(NESTED, b'37</td>')]):
            self.assertEqual({k: v for k, v in verdicts(NESTED_ROUTE, NESTED, nested_target(anchor)).items() if k in ('value', 'row_label', 'header_path')},
                             {'value': 'pass', 'row_label': 'pass', 'header_path': 'unresolved'}, anchor)  # header_path: semantic truth unchanged (correct); its cross-row order is byte order only, unproved (table-order-conservative)

    def test_a_wrong_inner_value_fails_and_never_borrows_the_holders_text(self):
        bad = copy.deepcopy(NESTED_ROUTE); [c.update(text='38') for c in inner_table(bad)['cells'] if grade.overlap(c.get('anchor'), at(NESTED, b'37'))]
        for anchor in (at(NESTED, b'37'), at(NESTED, b'<td id="value">37</td>')):
            self.assertEqual(verdicts(bad, NESTED, nested_target(anchor), 'value'), 'fail')

    def test_a_lost_inner_table_leaves_the_value_unlocated_never_the_holder(self):
        lost = copy.deepcopy(NESTED_ROUTE); lost['units'] = [u for u in lost['units'] if u is not inner_table(lost)]
        for anchor in (at(NESTED, b'37'), at(NESTED, b'<td id="value">37</td>')):
            self.assertEqual(verdicts(lost, NESTED, nested_target(anchor), 'value'), 'no_row')

    def test_the_same_bytes_claimed_by_two_tables_is_ambiguous(self):
        for before in (True, False):
            dup = copy.deepcopy(NESTED_ROUTE); t = inner_table(dup); fake = copy.deepcopy(t); fake['id'] = 'dup'
            [c.update(text='99') for c in fake['cells'] if grade.overlap(c.get('anchor'), at(NESTED, b'37'))]
            i = dup['units'].index(t); dup['units'].insert(i if before else i + 1, fake)
            self.assertEqual(verdicts(dup, NESTED, nested_target(at(NESTED, b'<td id="value">37</td>')), 'value'), 'unresolved')

    def test_an_anchor_reaching_past_its_own_close_or_into_another_cell_is_not_the_inner_cells(self):
        for anchor in (at(NESTED, b'<td id="value">37</td></tr>'), at(NESTED, b'<td id="value">', upto=b'Outer closing text'), at(NESTED, b'<td id="label">', upto=b'37</td>')):
            self.assertNotEqual(verdicts(NESTED_ROUTE, NESTED, nested_target(anchor), 'value'), 'pass', anchor)

    def test_a_route_holder_anchored_through_its_own_close_never_owns_the_inner_value(self):
        raw = b'<!doctype html><html><body><table><tr><td>Total</td><td><table><tr><td>37</td></tr></table></td></tr></table></body></html>'
        holder = {'byte_start': raw.index(b'<td><table>'), 'byte_end_exclusive': raw.index(b'</td></tr></table></body>') + 5}
        route = {'schema': 'prepare-route-output/1', 'file_id': 'pub/flatten.htm', 'status': 'OK', 'units': [{'id': 't0', 'kind': 'table', 'anchor': at(raw, b'<table>'), 'cells': [
            {'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Total', 'anchor': at(raw, b'<td>Total</td>')}, {'r': 0, 'c': 1, 'rs': 1, 'cs': 1, 'text': '37', 'anchor': holder}]}]}
        t = dict(nested_target(at(raw, b'37')), file_id='pub/flatten.htm', support={}, fields=dict(nested_target(None)['fields'], row_label=None, header_path=[]))
        for anchor in (at(raw, b'37'), at(raw, b'<td>37</td>')):
            self.assertEqual(verdicts(route, raw, dict(t, anchor=anchor), 'value'), 'no_row')


class TitleCarrierTests(unittest.TestCase):
    RAW = (F / 'title_qualifier.htm').read_bytes(); ROUTE = json.loads((F / 'title_qualifier_route.json').read_text())

    def target(self, title):
        raw = self.RAW; s = raw.index(b'<strong'); sh = raw.index(b'<th id="label">'); vi = raw.index(b'<td id="value">')
        return {'key_id': 'public/T1', 'file_id': self.ROUTE['file_id'], 'type': 'cell', 'format': 'cell/html', 'split': 'public', 'excluded': [], 'alternatives': {},
                'anchor': {'byte_start': vi, 'byte_end_exclusive': raw.index(b'</td>', vi) + 5}, 'table_anchor': at(raw, b'<table', upto=b'</table>'),
                'support': {'row_label': {'anchors': [at(raw, b'<th id="label">', upto=b'</th>')]}, 'table_title': {'anchors': [{'byte_start': s, 'byte_end_exclusive': raw.index(b'</strong>', s) + 9}]}},
                'fields': {'display_value': '43', 'footnote_markers': [], 'header_path': [], 'periods': [], 'printed_value': '43', 'row_context': [], 'row_label': 'Crates',
                           'section_path': [], 'table_title': [title], 'value_kind': 'number'}}

    def retitled(self, text):
        r = copy.deepcopy(self.ROUTE); next(u for u in r['units'] if u.get('kind') == 'table')['cells'][0]['text'] = text; return r

    def test_a_title_inside_a_larger_faithful_carrier_is_carried(self):
        self.assertEqual(verdicts(self.ROUTE, self.RAW, self.target('Capacity summary (unaudited)'), 'table_title'), 'unresolved')  # title-native-order (Root-approved 2026-10-11): truth unchanged; before/after rests on byte or route order only, unproved

    def test_an_altered_missing_or_invented_qualifier_or_a_wrong_title_is_not_carried(self):
        for text in ('Capacity summary Preliminary', 'Capacity summary (audited) Preliminary', 'Capacity summary (unaudited, restated) Preliminary'):
            self.assertEqual(verdicts(self.retitled(text), self.RAW, self.target('Capacity summary (unaudited)'), 'table_title'), 'fail', text)
        self.assertEqual(verdicts(self.ROUTE, self.RAW, self.target('Capacity totals (unaudited)'), 'table_title'), 'fail')


class SameTableHeadingTests(unittest.TestCase):
    def test_a_heading_in_an_earlier_row_of_the_values_table_in_source_order(self):
        H = F / 'heading'; raw = (H / 'invented_source.htm').read_bytes(); t = json.loads((H / 'ORIGINAL_TARGET.json').read_text()); t['excluded'] = set(t.get('excluded') or [])
        for name, want in json.loads((H / 'EXPECTATIONS.json').read_text())['expected_section_path'].items():
            self.assertEqual(verdicts(json.loads((H / f'{name}.json').read_text()), raw, t, 'section_path'), want, name)


if __name__ == '__main__':
    unittest.main()
