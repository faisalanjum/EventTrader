"""A title kept above its table with the source's own separate table between them, on a certain reading and on an uncertain one (fixtures/title_between:
uncertain.htm = certain.htm plus a hiding-property rule no element uses; every truth unchanged; routes from the real HTML converter at main e0eca7f46).
Truths from the markup: each struck paragraph is its own table's title, printed before it - H's larger carrier '<s>Dock tariffs</s> (draft)' and K's
exact '<s>Harbor fees</s>' with T1 / T2 between, J's and M's directly above; Z is written after M. The tables' identity and the title's place are
byte facts on either reading; where they show is proved only on a certain one, so on an uncertain reading their written order is an order doubt
(`order_doubt`): never a pass, never a guessed displacement, and every other contradiction still fails."""
import copy
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade

F = Path(__file__).with_name('fixtures') / 'title_between'
SOURCES = {n: ((F / f'{n}.htm').read_bytes(), json.loads((F / f'{n}_route.json').read_text())) for n in ('certain', 'uncertain')}
TITLES = {'H14': (b'H', '14', 'Moorings', b'<p><s>Dock tariffs</s> (draft)</p>', 'Dock tariffs', 'Pilots'), 'K9': (b'K', '9', 'Berths', b'<p><s>Harbor fees</s></p>', 'Harbor fees', 'Tugs'),
          'J6': (b'J', '6', 'Cranes', b'<p><s>Quay rents</s> (draft)</p>', 'Quay rents', None), 'M8': (b'M', '8', 'Rafts', b'<p><s>Slip fees</s></p>', 'Slip fees', None)}


def at(raw, needle, inner):
    i = raw.index(needle); j = i + needle.index(inner); return {'byte_start': j, 'byte_end_exclusive': j + len(inner)}


def key(raw, route, k, alts=None):
    tid, value, label, para, words, _ = TITLES[k]; i = raw.index(b'<table id="%s">' % tid)
    return {'key_id': 'invented/' + k, 'file_id': route['file_id'], 'type': 'cell', 'format': 'cell/html', 'split': 'public', 'excluded': set(), 'alternatives': {'table_title': alts} if alts else {},
            'anchor': at(raw, b'<td>%s</td>' % value.encode(), value.encode()), 'table_anchor': {'byte_start': i, 'byte_end_exclusive': raw.index(b'</table>', i) + 8},
            'support': {'table_title': {'anchors': [at(raw, para, words.encode())]}, 'row_label': {'anchors': [at(raw, b'<td>%s</td>' % label.encode(), label.encode())]}},
            'fields': {'printed_value': value, 'display_value': value, 'value_kind': 'number', 'row_label': label, 'header_path': [], 'periods': [], 'footnote_markers': [],
                       'section_path': [], 'row_context': [], 'table_title': (alts or [['~~%s~~' % words]])[0]}}


def mutated(route, k, m):
    r = copy.deepcopy(route); words, between = TITLES[k][4], TITLES[k][5]
    unit = lambda text: next(u for u in r['units'] if u.get('kind') != 'table' and (u.get('text') or '').startswith(text))
    table = lambda text: next(u for u in r['units'] if u.get('kind') == 'table' and any(c.get('text') == text for c in u.get('cells') or []))
    tu = unit(words)
    if m == 'lost_strike': assert tu.pop('struck')
    elif m == 'missing_title': r['units'].remove(tu)
    elif m == 'wrong_occurrence': tu['anchor'] = unit('Harbor fees' if words != 'Harbor fees' else 'Dock tariffs')['anchor']
    elif m == 'moved_order': z = table('Later'); r['units'].remove(z); r['units'].insert(r['units'].index(tu) + 1, z)
    elif m == 'wrong_source_table': table(between)['source_table'] = dict(table(between)['source_table'], tag_start=table('Later')['source_table']['tag_start'])
    elif m is not None: raise KeyError(m)
    return r


def graded(source, k, m=None, alts=None):
    raw, route = SOURCES[source]; g = grade.Grader(key(raw, route, k, alts), grade.RouteFile(mutated(route, k, m), raw)); g.grade_cell()
    return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'table_title'), grade.verdict_of(g.rows)


class TitleBetweenTables(unittest.TestCase):
    def test_the_fixture_readings(self):
        for source, certain in (('certain', True), ('uncertain', False)):
            raw, route = SOURCES[source]; self.assertIs(grade.RouteFile(copy.deepcopy(route), raw).vis.certain, certain)

    def test_a_kept_arrangement_is_open_on_either_reading(self):
        for k in TITLES: self.assertEqual(graded('certain', k), (('unresolved', 'source_order'), 'UNRESOLVED'), k)  # title before its table on written order only (title-native-order)
        self.assertEqual(graded('uncertain', 'K9'), (('unresolved', 'source_order'), 'UNRESOLVED'))  # exact title: where the tables show is unproved
        self.assertEqual(graded('uncertain', 'H14'), (('unresolved', 'source_reading'), 'UNRESOLVED'))  # the larger carrier's own text over its place is unproved too
        self.assertEqual(graded('uncertain', 'J6'), (('unresolved', 'source_reading'), 'UNRESOLVED'))

    def test_written_order_alone_never_fails_or_passes(self):
        for k in TITLES:
            self.assertEqual(graded('certain', k, 'moved_order'), (('unresolved', 'source_order'), 'UNRESOLVED'), k)  # a reading's certainty does not prove layout order (a CSS order control)
            self.assertEqual(graded('uncertain', k, 'moved_order'), (('unresolved', 'source_order'), 'UNRESOLVED'), k)  # byte order proves no displayed order here

    def test_independent_contradictions_fail_on_either_reading(self):
        for source in ('certain', 'uncertain'):
            for k in TITLES:
                with self.subTest(source=source, key=k):
                    self.assertEqual(graded(source, k, 'lost_strike'), (('fail', 'struck'), 'FAIL'))
                    self.assertEqual(graded(source, k, 'missing_title'), (('fail', 'missing'), 'FAIL'))
                    self.assertEqual(graded(source, k, 'wrong_occurrence'), (('fail', 'missing'), 'FAIL'))
            for k in ('H14', 'K9'):
                self.assertEqual(graded(source, k, 'wrong_source_table'), (('fail', 'placement'), 'FAIL'))  # a table claim the source's bytes refute

    def test_the_order_of_accepted_values_never_changes_the_verdict(self):
        for source in ('certain', 'uncertain'):
            for k in ('H14', 'K9'):
                right, wrong = ['~~%s~~' % TITLES[k][4]], ['~~Unrelated name~~']
                self.assertEqual(graded(source, k, alts=[right, wrong]), graded(source, k, alts=[wrong, right]), (source, k))


if __name__ == '__main__':
    unittest.main()
