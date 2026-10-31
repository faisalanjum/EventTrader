"""Source table declarations beside the tool's own header verdict (MANUAL_M2_HEADER_IMPLEMENTATION_20261021.md; Smart's corrected design; Root's
binding review MANUAL_M2_HEADER_BINDING_REVIEW_20261021.md). The tool's verdict (EdgarTools 5.60.0 TableProcessor) stays unchanged, now as `header_guess`
(2026-10-31: `header` states the source markup only, test_header_markup_facts). Beside
it ride the source's own statements: each cell's `tag` (td/th as parsed), its `id`/`scope`/`headers` values as the parser reads them (`attrs`), and
its own source row group (`row_group`, an index into the table's `row_group_tags`: thead, tbody, tfoot, or 'table' for rows straight in the table),
carried on the cell itself so that it stays with that cell when the screen step re-grids rows. Expected declarations come from the fixture markup;
the expected `header` values are the verdicts the unchanged tool gave before this change. An old dump without declarations stays unknown."""
import hashlib
import unittest
from pathlib import Path

from driver.prepare.convert import edgartools_html as eh
from driver.prepare.convert import screen_grid as sg

# amrc_20251231x10-k.htm (sha256 afe1312a8aafe7c5496c2d06de07d1b7aa214b3088809cd0f0f53c13b406e498), bytes 2536382-2540933 (sha256
# b5fd7005f7548b6f676921dc35de8132c608f95722ed71d9bbf6f5d2dfbc61c4): its make-whole table's spacer row, title row and first data row,
# wrapped as <html><body>...</table></body></html>.
AMRC = Path(__file__).resolve().parent / 'fixtures' / 'amrc_t1522_slice.html'
AMRC_SHA256 = '93cfca60a03bddec2e8501a4e2cf6f88b2277157984da2e25dcb8420a77ec128'
STRUCT = (b'<html><body><table><thead><tr><th scope="col">Item</th><td>2025</td></tr></thead>'
          b'<tbody><tr><th scope="row" headers="h1">Revenue</th><td headers="c1 r1">1,234</td></tr></tbody>'
          b'<tbody><tr><td>Cost</td><td>900</td></tr></tbody><tfoot><tr><td>Total</td><td>334</td></tr></tfoot></table>'
          b'<table><tr><td>Direct row</td><td>5</td></tr><tr><td>Nested<table><tr><th scope="col">Inner</th></tr><tr><td>7</td></tr></table></td><td>x</td></tr></table></body></html>')
STRUCT_VERDICTS = [True, True, True, True, False, False, False, False, False, False, False, False, True, False]  # the unchanged tool's, before this change
IDS = (b'<html><body><table><tr><th id="a1">Amount</th><th id="a2">Amount</th></tr>'  # two headers that read alike: only the id tells them apart
       b'<tr><td headers="a2">5</td><td headers="a9">6</td><td headers="x&amp;y">7</td></tr></table></body></html>')  # a9 names no cell; &amp; is decoded


def route(raw, parse=eh.parse):
    return eh.convert(raw, 'x.htm', hashlib.sha256(raw).hexdigest(), parse=parse)


def tables(r):
    return [u for u in r['units'] if u.get('kind') == 'table']


def old_dump(*drop):  # a raw reading saved before these declarations (and, with 'row_groups', before group numbers)
    def parse(raw, vis):
        tree, seconds, made_by = eh.parse(raw, vis)
        def strip(d):
            if isinstance(d, dict):
                if isinstance(d.get('rows'), list):
                    for k in ('row_group_tags',) + drop: d.pop(k, None)
                    for row in d['rows']:
                        for cell in row: cell.pop('tag', None); cell.pop('attrs', None)
                for v in d.values(): strip(v)
            elif isinstance(d, list):
                for v in d: strip(v)
        strip(tree)
        return tree, seconds, made_by
    return parse


class SourceHeaderDeclarations(unittest.TestCase):
    def test_structural_declarations_ride_beside_the_unchanged_verdict(self):  # failed before: no tag, attrs or group (first version: no tag)
        r = route(STRUCT)
        got = [[(c['r'], c['c'], c.get('tag'), c.get('attrs'), c['header_guess']) for c in t['cells']] for t in tables(r)]
        self.assertEqual(got, [[(0, 0, 'th', {'scope': 'col'}, True), (0, 1, 'td', None, True), (1, 0, 'th', {'scope': 'row', 'headers': 'h1'}, True),
                                (1, 1, 'td', {'headers': 'c1 r1'}, True), (2, 0, 'td', None, False), (2, 1, 'td', None, False), (3, 0, 'td', None, False), (3, 1, 'td', None, False)],
                               [(0, 0, 'td', None, False), (0, 1, 'td', None, False), (1, 0, 'td', None, False), (1, 1, 'td', None, False)],
                               [(0, 0, 'th', {'scope': 'col'}, True), (1, 0, 'td', None, False)]])
        self.assertEqual([(t.get('row_group_tags'), [c.get('row_group') for c in t['cells']]) for t in tables(r)],
                         [(['thead', 'tbody', 'tbody', 'tfoot'], [0, 0, 1, 1, 2, 2, 3, 3]), (['table'], [0, 0, 0, 0]), (['table'], [0, 0])])
        self.assertFalse(any('row_groups' in t for t in tables(r)))  # no positional vector beside the screen grid: membership is the cell's own

    def test_membership_stays_with_its_cell_when_the_screen_regrids(self):  # the screen step moves rows; a positional join would swap the groups
        raw = b'<html><body><table><thead><tr><td>Head</td></tr></thead><tbody><tr><td>Body</td></tr></tbody></table></body></html>'
        units = route(raw)['units']; t = tables({'units': units})[0]
        _, spans = sg.tag_cells(raw)
        self.assertEqual([(c['r'], c['text'], t['row_group_tags'][c['row_group']]) for c in t['cells']], [(0, 'Head', 'thead'), (1, 'Body', 'tbody')])
        sg.apply(units, spans, {0: [{'g': 0, 'row': 1, 'x': 0, 'w': 100}, {'g': 1, 'row': 0, 'x': 0, 'w': 100}]})  # the page shows Body above Head
        self.assertEqual(sorted((c['r'], c['text'], t['row_group_tags'][c['row_group']]) for c in t['cells']), [(0, 'Body', 'tbody'), (1, 'Head', 'thead')])

    def test_ids_are_kept_so_a_headers_reference_resolves_without_text(self):  # failed before: no id
        cells = tables(route(IDS))[0]['cells']
        self.assertEqual([(c['text'], c['tag'], c.get('attrs')) for c in cells],
                         [('Amount', 'th', {'id': 'a1'}), ('Amount', 'th', {'id': 'a2'}), ('5', 'td', {'headers': 'a2'}), ('6', 'td', {'headers': 'a9'}), ('7', 'td', {'headers': 'x&y'})])
        ids = {c['attrs']['id']: (c['r'], c['c']) for c in cells if 'id' in (c.get('attrs') or {})}
        self.assertEqual(ids.get('a2'), (0, 1))  # the second "Amount", by its id, not by its text or row order
        self.assertIsNone(ids.get('a9'))  # a broken reference stays broken: no target is invented

    def test_a_real_table_keeps_the_tools_guess_and_states_td(self):  # failed before: no tag. AMRC t1522: the make-whole data row is the tool's guess, the source says td
        raw = AMRC.read_bytes(); self.assertEqual(hashlib.sha256(raw).hexdigest(), AMRC_SHA256)
        t = tables(route(raw)); self.assertEqual(len(t), 1); cells = t[0]['cells']
        self.assertEqual({c.get('tag') for c in cells}, {'td'})
        self.assertFalse(any('attrs' in c for c in cells))
        self.assertEqual([c['header_guess'] for c in cells], [False] * 27 + [True] * 20)  # the unchanged tool's verdict (title row and the data row alike)
        self.assertEqual((t[0].get('row_group_tags'), {c['row_group'] for c in cells}, 'row_groups' in t[0]), (['table'], {0}, False))
        self.assertEqual([c['text'] for c in cells if c['r'] == 2 and c['text']], ['Make-whole provisions', 'Liability', 'June/August 2018', 'December 2038', '$', '69'])

    def test_an_old_dump_without_declarations_stays_unknown(self):  # never an invented td, group or false
        r = route(STRUCT, parse=old_dump())
        self.assertTrue(all(c['tag'] is None and 'attrs' not in c for t in tables(r) for c in t['cells']))
        self.assertTrue(all('row_group_tags' not in t for t in tables(r)))
        self.assertEqual([c['header_guess'] for t in tables(r) for c in t['cells']], STRUCT_VERDICTS)
        r = route(STRUCT, parse=old_dump('row_groups'))
        self.assertTrue(all(c['row_group'] is None for t in tables(r) for c in t['cells']))

    def test_the_verdict_is_unchanged_and_named_as_the_tools(self):
        self.assertEqual([c['header_guess'] for t in tables(route(STRUCT)) for c in t['cells']], STRUCT_VERDICTS)
        self.assertEqual(eh.SETTINGS['table_header'], "header states the source's own markup only: true for a th or a cell in its own table's thead; false when the "
                                                      "cell's tag and row group are both recorded and neither marks a header (no such markup, not a judgment that the "
                                                      "cell is no heading); null (unknown) when that evidence is missing and no th or thead proves it; header_guess is "
                                                      "the tool's own verdict (EdgarTools 5.60.0 TableProcessor), read unchanged; a cell's tag, its attrs "
                                                      "(id, scope, headers as the parser reads them: character references decoded) and its row_group (the cell's own "
                                                      "source group, carried through re-gridding; its tag in the table's row_group_tags) are the source's statements; "
                                                      "an absent tag, attrs entry or group is unknown")


if __name__ == '__main__':
    unittest.main()
