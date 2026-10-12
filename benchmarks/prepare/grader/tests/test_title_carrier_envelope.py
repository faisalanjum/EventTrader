"""A title proved inside a larger faithful carrier is the title's own place, not the carrier's whole envelope (Test's public placement controls T1/T2,
released by Root 2026-10-12). Invented source (fixtures/title_carrier): one outer cell prints the heading 'Compass stock (preliminary)', a scope sentence,
then two child tables, east (Copper 17) and west (Silver 29); uncertain.htm = the same markup plus an unavailable stylesheet. The key asks the title
of Silver's 29 at the heading's own bytes. T1 routes carry the whole outer cell as one faithful carrier; T2 routes the same bytes with the heading and
the sentence as their own units. Truth from the markup alone: the title is kept before both panels, east lies between it and west, and nothing proves
where they show - so both segmentations are UNRESOLVED, never PASS; the carrier's envelope holding east is its own child, not a misplaced title."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade

F = Path(__file__).with_name('fixtures') / 'title_carrier'
RAW = {n: (F / f'{n}.htm').read_bytes() for n in ('certain', 'uncertain')}
ROUTES = {(seg, n): json.loads((F / f'{seg}{"_uncertain" if n == "uncertain" else ""}_route.json').read_text()) for seg in ('T1_large', 'T2_separate') for n in RAW}
TITLE = 'Compass stock (preliminary)'


def at(raw, needle):
    i = raw.index(needle); return {'byte_start': i, 'byte_end_exclusive': i + len(needle)}


def key(raw, route):
    i = raw.index(b'<table id="west">')
    return {'key_id': 'invented/29', 'file_id': route['file_id'], 'type': 'cell', 'format': 'cell/html', 'split': 'public', 'excluded': set(), 'alternatives': {},
            'anchor': at(raw, b'29'), 'table_anchor': {'byte_start': i, 'byte_end_exclusive': raw.index(b'</table>', i) + 8},
            'support': {'table_title': {'anchors': [at(raw, TITLE.encode())]}},
            'fields': {'printed_value': '29', 'display_value': '29', 'value_kind': 'number', 'row_label': None, 'header_path': [], 'periods': [],
                       'footnote_markers': [], 'section_path': [], 'row_context': [], 'table_title': [TITLE]}}


def mutated(route, name, raw):
    r = copy.deepcopy(route); tables = {u['id']: u for u in r['units'] if u.get('kind') == 'table'}; carrier = tables['frame']['cells'][0]
    if name == 'title_lost': carrier['text'] = carrier['text'].replace('Compass stock ', '')
    elif name == 'qualifier_lost': carrier['text'] = carrier['text'].replace(' (preliminary)', '')
    elif name == 'wrong_owner': tables['east']['source_table']['tag_start'] = tables['west']['source_table']['tag_start']  # east claims west's start tag
    elif name == 'child_claims_carrier_table': tables['east']['source_table']['tag_start'] = tables['frame']['source_table']['tag_start']  # east claims the outer table
    elif name == 'carrier_cuts_child':  # an honest carrier whose one place ends inside east: no source cell, and east is not its whole child
        cut = tables['east']['cells'][0]['anchor']['byte_end_exclusive']; carrier['anchor'] = dict(carrier['anchor'], byte_end_exclusive=cut)
        carrier['text'] = grade.RouteFile(copy.deepcopy(route), raw).vis.at(carrier['anchor']['byte_start'], cut)
    elif name: raise ValueError(name)
    return r


def title(seg, reading, mutation=None):
    raw, route = RAW[reading], ROUTES[seg, reading]
    g = grade.Grader(key(raw, route), grade.RouteFile(mutated(route, mutation, raw), raw)); g.grade_cell()
    return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'table_title')


class TitleCarrierEnvelope(unittest.TestCase):
    def test_the_fixture_is_what_the_truth_says(self):
        for reading, raw in RAW.items():
            route = ROUTES['T1_large', reading]; frame, east, west = (next(u for u in route['units'] if u.get('id') == n) for n in ('frame', 'east', 'west'))
            cell, place = frame['cells'][0]['anchor'], at(raw, TITLE.encode())
            self.assertTrue(cell['byte_start'] <= place['byte_start'] < place['byte_end_exclusive'] <= east['anchor']['byte_start'])  # the title, then both panels
            self.assertTrue(east['anchor']['byte_end_exclusive'] <= west['anchor']['byte_start'] and west['anchor']['byte_end_exclusive'] <= cell['byte_end_exclusive'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), route['sha256']); self.assertEqual(ROUTES['T2_separate', reading]['sha256'], route['sha256'])  # T1 and T2: one source, the bytes each route names

    def test_a_faithful_larger_carrier_is_open_like_its_separate_twin(self):
        for reading in RAW:
            with self.subTest(reading=reading):
                self.assertEqual(title('T2_separate', reading)[0], 'unresolved')  # unchanged: the separate carrier
                self.assertEqual(title('T1_large', reading)[0], 'unresolved')  # was fail/placement: the envelope's own child is no misplacement
        self.assertEqual(title('T1_large', 'certain'), ('unresolved', 'source_order'))  # byte order only, never a pass

    def test_every_proved_contradiction_still_fails(self):
        for reading in RAW:
            for mutation, want in (('title_lost', ('fail', 'text')), ('qualifier_lost', ('fail', 'text')), ('wrong_owner', ('fail', 'placement')),
                                   ('child_claims_carrier_table', ('fail', 'placement')), ('carrier_cuts_child', ('fail', 'placement'))):
                with self.subTest(reading=reading, mutation=mutation):
                    self.assertEqual(title('T1_large', reading, mutation), want)


if __name__ == '__main__':
    unittest.main()
