"""`header` states only the source's own markup; `header_guess` is the tool's claim (Root/owner 2026-10-31, header-label defect).
header = True when the cell is a source <th> or sits in its own table's <thead>; False only when the cell's tag and its row group are both recorded and
neither marks a header (False = no such markup, not a judgment that the cell is not a heading); None (unknown) when that evidence is missing and no th or
thead proves True. header_guess = EdgarTools 5.60.0 TableProcessor is_header, unchanged (a keyword/style heuristic plus th/thead).
Expected `header` values are computed from the fixture markup with lxml (never from the code under test)."""
import hashlib
import unittest

import lxml.html

from driver.prepare.convert import edgartools_html as eh
from tests.driver.prepare.convert.test_source_header_declarations import AMRC, AMRC_SHA256, STRUCT, STRUCT_VERDICTS, route, tables

CSS = (b'<html><body><table><tbody style="display:table-header-group"><tr><td style="font-weight:bold">Year</td><td style="font-weight:bold">2025</td></tr></tbody>'
       b'<tbody><tr><th style="display:table-cell;font-weight:normal">Revenue</th><td>5</td></tr></tbody></table></body></html>')  # styling never makes or unmakes a header
NESTED = (b'<html><body><table><thead><tr><th>Outer<table><tr><td>inner of a th</td></tr></table></th></tr></thead>'  # an outer thead never reaches a nested table
          b'<tbody><tr><td>Body<table><thead><tr><td>inner head</td></tr></thead><tr><td>inner row</td></tr></table></td></tr></tbody></table></body></html>')
YEARS = b'<html><body><table><tr><td></td><td>2025</td><td>2024</td></tr><tr><td>Revenue</td><td>1,234</td><td>1,100</td></tr></table></body></html>'


def source_headers(raw):
    """Per table (document order), its own cells in row order: True for a th or a cell in the table's own thead, else False."""
    out = []
    for table in lxml.html.fromstring(raw).iter('table'):
        own = [c for c in table.iter('td', 'th') if next(c.iterancestors('table')) is table]
        group = lambda c: next((a.tag for a in c.iterancestors('thead', 'tbody', 'tfoot', 'table')), None)
        out.append([c.tag == 'th' or group(c) == 'thead' for c in own])
    return out


def dump_without(tags=False, groups=False):  # a raw reading that lost the cell tags and/or the row-group tags
    def parse(raw, vis):
        tree, seconds, made_by = eh.parse(raw, vis)
        def strip(d):
            if isinstance(d, dict):
                if isinstance(d.get('rows'), list):
                    if groups: d.pop('row_group_tags', None)
                    for row in d['rows']:
                        for cell in row:
                            if tags: cell.pop('tag', None); cell.pop('attrs', None)
                for v in d.values(): strip(v)
            elif isinstance(d, list):
                for v in d: strip(v)
        strip(tree)
        return tree, seconds, made_by
    return parse


def flags(r, key):
    return [[c[key] for c in t['cells']] for t in tables(r)]


class HeaderStatesSourceMarkupOnly(unittest.TestCase):
    def test_header_is_the_sources_own_th_or_thead(self):
        for name, raw in (('struct', STRUCT), ('css', CSS), ('nested', NESTED), ('years', YEARS)):
            with self.subTest(name):
                self.assertEqual(flags(route(raw), 'header'), source_headers(raw))

    def test_a_mixed_row_marks_only_its_th_while_the_guess_marks_the_row(self):
        t = tables(route(STRUCT))[0]
        row = {c['text']: (c['tag'], c['header'], c['header_guess']) for c in t['cells'] if c['r'] == 1}
        self.assertEqual(row, {'Revenue': ('th', True, True), '1,234': ('td', False, True)})

    def test_the_guess_is_the_tools_unchanged_verdict(self):
        self.assertEqual([c['header_guess'] for t in tables(route(STRUCT)) for c in t['cells']], STRUCT_VERDICTS)
        self.assertTrue(all(type(c['header_guess']) is bool for raw in (STRUCT, CSS, NESTED, YEARS) for t in tables(route(raw)) for c in t['cells']))

    def test_styling_never_makes_a_header(self):
        cells = {c['text']: (c['header'], c['header_guess']) for c in tables(route(CSS))[0]['cells']}
        self.assertEqual({k: v[0] for k, v in cells.items()}, {'Year': False, '2025': False, 'Revenue': True, '5': False})
        self.assertTrue(cells['Year'][1] and cells['2025'][1])  # the tool reads the bold row as a header: kept only as its guess

    def test_a_guessed_years_row_is_no_header(self):
        cells = tables(route(YEARS))[0]['cells']
        self.assertEqual([(c['text'], c['header'], c['header_guess']) for c in cells if c['r'] == 0 and c['text']], [('2025', False, True), ('2024', False, True)])

    def test_groups_belong_to_their_own_table(self):
        got = {c['text'].split('inner')[0].strip() or c['text']: c['header'] for t in tables(route(NESTED)) for c in t['cells']}
        self.assertEqual((got['inner of a th'], got['inner head'], got['inner row']), (False, True, False))

    def test_a_real_table_states_td_and_keeps_the_guess(self):  # AMRC t1522: all td, rows straight in the table; the tool guesses the data row a header
        raw = AMRC.read_bytes(); self.assertEqual(hashlib.sha256(raw).hexdigest(), AMRC_SHA256)
        cells = tables(route(raw))[0]['cells']
        self.assertEqual([c['header'] for c in cells], [False] * 47)
        self.assertEqual([c['header_guess'] for c in cells], [False] * 27 + [True] * 20)

    def test_missing_evidence_is_unknown_unless_markup_proves_a_header(self):
        def per_cell(parse):
            return [(c['text'].split('inner')[0].strip() or c['text'], c['header'], c['header_guess']) for t in tables(route(STRUCT, parse=parse)) for c in t['cells']]
        none = per_cell(dump_without(tags=True, groups=True))
        self.assertTrue(all(h is None for _, h, _ in none))  # nothing recorded: unknown, never False
        self.assertEqual([g for _, _, g in none], STRUCT_VERDICTS)  # the guess is unaffected
        no_tags = dict((t, h) for t, h, _ in per_cell(dump_without(tags=True)))
        self.assertEqual((no_tags['Item'], no_tags['2025'], no_tags['Revenue'], no_tags['Cost']), (True, True, None, None))  # thead proves; tbody cannot say
        no_groups = dict((t, h) for t, h, _ in per_cell(dump_without(groups=True)))
        self.assertEqual((no_groups['Item'], no_groups['2025'], no_groups['Revenue'], no_groups['1,234']), (True, None, True, None))  # th proves; td cannot say

    def test_both_flags_stay_with_their_cell_when_the_screen_regrids(self):  # the screen step moves rows; the flags are the cell's own, never positional
        from driver.prepare.convert import screen_grid as sg
        raw = b'<html><body><table><thead><tr><td>Head</td></tr></thead><tbody><tr><td>Body</td></tr></tbody></table></body></html>'
        units = route(raw)['units']; t = tables({'units': units})[0]
        before = {c['text']: (c['r'], c['header'], c['header_guess']) for c in t['cells']}
        self.assertEqual({k: v[1] for k, v in before.items()}, {'Head': True, 'Body': False})
        _, spans = sg.tag_cells(raw)
        sg.apply(units, spans, {0: [{'g': 0, 'row': 1, 'x': 0, 'w': 100}, {'g': 1, 'row': 0, 'x': 0, 'w': 100}]})  # the page shows Body above Head
        after = {c['text']: (c['r'], c['header'], c['header_guess']) for c in t['cells']}
        self.assertEqual((after['Head'][0], after['Body'][0]), (1, 0))  # the rows did move
        self.assertEqual({k: v[1:] for k, v in after.items()}, {k: v[1:] for k, v in before.items()})

    def test_settings_say_what_each_flag_means(self):
        self.assertEqual(eh.SETTINGS['table_header'],
                         "header states the source's own markup only: true for a th or a cell in its own table's thead; false when the cell's tag and row group "
                         "are both recorded and neither marks a header (no such markup, not a judgment that the cell is no heading); null (unknown) when that "
                         "evidence is missing and no th or thead proves it; header_guess is the tool's own verdict (EdgarTools 5.60.0 TableProcessor), read "
                         "unchanged; a cell's tag, its attrs (id, scope, headers as the parser reads them: character references decoded) and its row_group (the "
                         "cell's own source group, carried through re-gridding; its tag in the table's row_group_tags) are the source's statements; an absent "
                         "tag, attrs entry or group is unknown")


if __name__ == '__main__':
    unittest.main()
