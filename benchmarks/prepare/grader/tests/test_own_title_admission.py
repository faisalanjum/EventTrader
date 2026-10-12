"""Source-bound own-title admission (Root-approved design C2, 2026-10-11) and the same-function whole_carrier class control. Invented sources
(fixtures/own_title): certain.htm, and uncertain.htm = the same bytes plus a hiding-property rule no element uses (the scanner's reading is
uncertain; every truth is unchanged). Routes from the real HTML converter at main e0eca7f46. Truths from the markup alone: A's <th rowspan=2> title
band is printed in the target's own <tr> (Crates 43) and spans Boxes 12; B's title row is the target itself; G's struck title band beside Rafts 8;
H's struck title inside a larger faithful carrier ('(draft)') above Moorings 14; E's own <caption>; C repeats A's words as a row label and has no
title. A same-row title is admitted only by the key's own anchor, the source's own table and <tr> and the route's row and in-row order; an uncertain
reading never creates a pass, and its doubt opens a pass only after the content, placement and strike checks (`field`)."""
import copy
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade

F = Path(__file__).with_name('fixtures') / 'own_title'
SOURCES = {n: ((F / f'{n}.htm').read_bytes(), json.loads((F / f'{n}_route.json').read_text())) for n in ('certain', 'uncertain')}
TH_A, TH_B, TH_G, TH_H = (b'<th rowspan="2">Fleet capacity (unaudited)</th>', b'<th colspan="2">Harbor summary</th>', b'<th rowspan="2"><s>Legacy fleet</s></th>',
                          b'<th colspan="2"><s>Dock tariffs</s> (draft)</th>')


def at(raw, needle, inner=None):  # bytes of `inner` inside the first `needle` (or the whole needle)
    i = raw.index(needle); j = i + (needle.index(inner) if inner else 0); return {'byte_start': j, 'byte_end_exclusive': j + len(inner or needle)}


def keys(raw, route):
    def key(tid, value, title, title_at, label=None, basis=False, kind='number', target=None, alts=None):
        support = {'table_title': {'anchors': [title_at]}}
        if label: support['row_label'] = {'anchors': [at(raw, b'<td>%s</td>' % label.encode(), label.encode())]}
        if basis: support['segment_or_basis'] = {'anchors': [at(raw, TH_A, b'(unaudited)')]}
        fields = {'printed_value': value, 'display_value': value, 'value_kind': kind, 'row_label': label, 'header_path': [], 'periods': [], 'footnote_markers': [],
                  'section_path': [], 'row_context': [], 'table_title': title}
        if basis: fields['segment_or_basis'] = ['(unaudited)']
        i = raw.index(b'<table id="%s">' % tid)
        return {'key_id': 'invented/' + value, 'file_id': route['file_id'], 'type': 'cell', 'format': 'cell/html', 'split': 'public', 'excluded': set(),
                'alternatives': {'table_title': alts} if alts else {}, 'anchor': target or at(raw, b'<td>%s</td>' % value.encode(), value.encode()),
                'table_anchor': {'byte_start': i, 'byte_end_exclusive': raw.index(b'</table>', i) + 8}, 'support': support, 'fields': fields}
    fc = at(raw, TH_A, b'Fleet capacity')
    return {'A43': key(b'A', '43', ['Fleet capacity'], fc, 'Crates', True), 'A12': key(b'A', '12', ['Fleet capacity'], fc, 'Boxes', True),
            'Btitle': key(b'B', 'Harbor summary', ['Harbor summary'], at(raw, TH_B, b'Harbor summary'), kind='text', target=at(raw, TH_B, b'Harbor summary')),
            'B7': key(b'B', '7', ['Harbor summary'], at(raw, TH_B, b'Harbor summary'), 'Cranes'),
            'G8': key(b'G', '8', ['~~Legacy fleet~~'], at(raw, TH_G, b'Legacy fleet'), 'Rafts'),
            'H14': key(b'H', '14', ['~~Dock tariffs~~'], at(raw, TH_H, b'Dock tariffs'), 'Moorings'),
            'E21': key(b'E', '21', ['Dock rates'], at(raw, b'<caption>Dock rates</caption>', b'Dock rates'), 'Berths'),
            'A43_right_first': key(b'A', '43', ['Fleet capacity'], fc, 'Crates', True, alts=[['Fleet capacity'], ['Fleet register']]),
            'A43_wrong_first': key(b'A', '43', ['Fleet register'], fc, 'Crates', True, alts=[['Fleet register'], ['Fleet capacity']])}


def mutated(route, name):
    r = copy.deepcopy(route); tables = [u for u in r['units'] if u.get('kind') == 'table']
    find = lambda text: next((t, c) for t in tables for c in t['cells'] if c.get('text') == text)
    ta, th = find('Fleet capacity (unaudited)'); tg, thg = find('Legacy fleet'); _, thh = find('Dock tariffs (draft)')
    if name == 'title_altered_A': th['text'] = 'Fleet size (unaudited)'
    elif name == 'title_altered_B': find('Harbor summary')[1]['text'] = 'Harbor summaries'
    elif name == 'title_missing_A': ta['cells'].remove(th)
    elif name == 'title_missing_G': tg['cells'].remove(thg)
    elif name == 'wrong_occurrence': th['anchor'] = [c for t in tables for c in t['cells'] if c.get('text') == 'Fleet capacity (unaudited)'][1]['anchor']
    elif name == 'other_table': ta['cells'].remove(th); find('Harbor summary')[0]['cells'].append(dict(th, r=0, c=2, rs=1))
    elif name == 'moved_down_A': th.update(r=1, rs=1)
    elif name == 'moved_down_G': thg.update(r=1, rs=1)
    elif name == 'target_moved_up': find('12')[1].update(r=0); find('Boxes')[1].update(r=0)
    elif name == 'after_target_A': th.update(c=3)
    elif name == 'after_target_G': thg.update(c=3)
    elif name == 'qualifier_lost': th['text'] = 'Fleet capacity'
    elif name == 'strike_lost_G': assert thg.pop('struck')
    elif name == 'strike_lost_H': assert thh.pop('struck')
    else: raise KeyError(name)
    return r


def graded(source, k, mutation=None):
    raw, route = SOURCES[source]; g = grade.Grader(copy.deepcopy(keys(raw, route)[k]), grade.RouteFile(mutated(route, mutation) if mutation else copy.deepcopy(route), raw)); g.grade_cell()
    rows = {r['check']: (r['verdict'], r['reason']) for r in g.rows}
    return rows.get('table_title'), grade.verdict_of(g.rows), rows


OPEN, ORDER = ('unresolved', 'source_reading'), ('unresolved', 'source_order')


class OwnTitleAdmission(unittest.TestCase):
    def test_the_fixture_readings_are_what_the_truths_say(self):
        for source, certain in (('certain', True), ('uncertain', False)):
            raw, route = SOURCES[source]
            self.assertIs(grade.RouteFile(copy.deepcopy(route), raw).vis.certain, certain, source)

    def test_own_row_and_self_titles_never_pass_on_an_unproved_side(self):
        self.assertEqual(graded('certain', 'Btitle')[:2], (('pass', None), 'PASS'))  # the target's own cell: membership, no side to prove
        for k in ('A43', 'G8', 'A43_right_first', 'A43_wrong_first'):  # both orders of the accepted values give the same verdict
            with self.subTest(key=k):  # one <tr> proves membership, not which side shows (title-native-order): open on bytes alone
                self.assertEqual(graded('certain', k)[:2], (ORDER, 'UNRESOLVED'))
        for k in ('A43', 'Btitle', 'G8', 'A43_right_first', 'A43_wrong_first'):
            with self.subTest(source='uncertain', key=k):
                self.assertEqual(graded('uncertain', k)[:2], (OPEN, 'UNRESOLVED'))

    def test_every_proved_contradiction_still_fails_on_either_reading(self):
        cases = {('A43', 'title_altered_A'): ('fail', 'text'), ('Btitle', 'title_altered_B'): ('fail', 'text'), ('A43', 'title_missing_A'): ('fail', 'missing'),
                 ('G8', 'title_missing_G'): ('fail', 'missing'), ('A43', 'wrong_occurrence'): ('fail', 'missing'), ('A43', 'other_table'): ('fail', 'placement'),
                 ('A43', 'moved_down_A'): ('fail', 'placement'), ('G8', 'moved_down_G'): ('fail', 'placement'), ('A12', 'target_moved_up'): ('fail', 'placement'),
                 ('G8', 'strike_lost_G'): ('fail', 'struck')}
        for source in ('certain', 'uncertain'):
            for (k, m), want in cases.items():
                with self.subTest(source=source, key=k, mutation=m):
                    title, whole, _ = graded(source, k, m)
                    if source == 'uncertain' and m in ('moved_down_A', 'moved_down_G'): self.assertEqual((title, whole), (ORDER, 'UNRESOLVED')); continue  # an uncertain reading proves no rendered row for a literal <tr>
                    self.assertEqual((title, whole), (want, 'FAIL'))

    def test_a_title_moved_after_its_target_never_passes(self):
        for k, m in (('A43', 'after_target_A'), ('G8', 'after_target_G')):
            self.assertEqual(graded('certain', k, m)[:2], (ORDER, 'UNRESOLVED'))  # which side shows is written order only (a dir can turn it): open, never a pass
            self.assertEqual(graded('uncertain', k, m)[:2], (OPEN, 'UNRESOLVED'))

    def test_a_lost_qualifier_fails_its_own_check_whatever_the_title_says(self):
        for source, title in (('certain', ORDER), ('uncertain', OPEN)):
            got, whole, rows = graded(source, 'A43', 'qualifier_lost')
            self.assertEqual((got, whole, rows['segment_or_basis']), (title, 'FAIL', ('fail', 'missing')))

    def test_unrelated_positives_and_the_byte_order_doubt_are_unchanged(self):
        for source in ('certain', 'uncertain'):
            self.assertEqual(graded(source, 'B7')[:2], (ORDER, 'UNRESOLVED'))  # a title row above the target: written order only
            self.assertEqual(graded(source, 'E21')[:2], (('pass', None), 'PASS'))
            title, whole, rows = graded(source, 'A12')  # a title above the target; its basis leans on cross-row byte order (table-order-conservative)
            self.assertEqual((title, whole, rows['segment_or_basis']), (ORDER, 'UNRESOLVED', ('unresolved', 'source_order')))

    def test_a_text_only_same_row_match_is_never_a_title(self):
        raw, route = SOURCES['certain']; k = keys(raw, route)['A43']
        t = dict(k, anchor=at(raw, b'<td>99</td>', b'99'), support={}, fields=dict(k['fields'], printed_value='99', display_value='99', row_label=None, table_title=['Fleet capacity (unaudited)'], segment_or_basis=None))
        g = grade.Grader(t, grade.RouteFile(copy.deepcopy(route), raw)); g.grade_cell()
        self.assertEqual(next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'table_title'), ('fail', 'placement'))  # C's row label beside 99 has A's words


class WholeCarrierClass(unittest.TestCase):
    """The same function's other uncertainty: a struck title inside a larger faithful carrier (whole_carrier). Its doubt must not hide a strike
    the route provably lost."""
    def test_the_larger_carrier_is_open_on_either_reading(self):
        self.assertEqual(graded('certain', 'H14')[:2], (ORDER, 'UNRESOLVED'))  # above its target on written order only
        self.assertEqual(graded('uncertain', 'H14')[:2], (OPEN, 'UNRESOLVED'))

    def test_a_lost_strike_on_the_larger_carrier_fails_on_either_reading(self):
        for source in ('certain', 'uncertain'):
            with self.subTest(source=source):
                self.assertEqual(graded(source, 'H14', 'strike_lost_H')[:2], (('fail', 'struck'), 'FAIL'))


if __name__ == '__main__':
    unittest.main()
