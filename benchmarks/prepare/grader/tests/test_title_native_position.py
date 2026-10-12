"""Where a title shows against its own table is not proved by bytes, DOM ordinals or the route's own order (title-native-order, 2026-10-11). Native fixtures:
title_native_direction (Root's controls: a struck title cell beside its value in one <tr>, written first or last, laid out left to right, right to left - the
converter's grid follows the measured display - or as blocks) and title_below (key-governed titles shown below or above their own tables by CSS order or
plain placement; below_browser.json: the measured tops). Never a pass on an unproved side; native ownership, missing text and lost strikes still decide."""
import copy
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade

N = Path(__file__).with_name('fixtures')
ORDER, OPEN = ('unresolved', 'source_order'), ('unresolved', 'source_reading')


def one(folder, name, title, value, words=None, mutate=None):
    """table_title and whole verdicts of a key whose title governs the table holding `value`, on a saved native-route fixture."""
    raw = (N / folder / f'{name}.htm').read_bytes(); route = json.loads((N / folder / f'{name}_route.json').read_text())
    route = mutate(copy.deepcopy(route)) if mutate else route
    cell = raw.index(b'>%s</td>' % value.encode()) + 1; tb = raw.rindex(b'<table', 0, cell); w = raw.index((words or title).encode())
    t = {'key_id': 'invented/' + name, 'file_id': route['file_id'], 'type': 'cell', 'format': 'cell/html', 'split': 'public', 'excluded': set(), 'alternatives': {},
         'anchor': {'byte_start': cell, 'byte_end_exclusive': cell + len(value)}, 'table_anchor': {'byte_start': tb, 'byte_end_exclusive': raw.index(b'</table>', tb) + 8},
         'support': {'table_title': {'anchors': [{'byte_start': w, 'byte_end_exclusive': w + len(words or title)}]}},
         'fields': {'printed_value': value, 'display_value': value, 'value_kind': 'number', 'row_label': None, 'header_path': [], 'periods': [], 'footnote_markers': [],
                    'section_path': [], 'row_context': [], 'table_title': [title]}}
    g = grade.Grader(t, grade.RouteFile(copy.deepcopy(route), raw)); g.grade_cell()
    return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'table_title'), grade.verdict_of(g.rows)


def unstruck(route):
    for u in route['units']:
        for x in [u] + list(u.get('cells') or []): x.pop('struck', None); x.pop('struck_at', None)
    return route


class TitleNativeDirection(unittest.TestCase):
    def test_every_layout_is_open_and_a_lost_strike_fails(self):
        for name in ('ltr', 'ltr_reverse', 'rtl', 'rtl_reverse', 'blocks', 'blocks_reverse'):
            with self.subTest(layout=name):
                self.assertEqual(one('title_native_direction', name, '~~Dock charges~~', '37', 'Dock charges'), (OPEN if name.startswith('blocks') else ORDER, 'UNRESOLVED'))
                self.assertEqual(one('title_native_direction', name, '~~Dock charges~~', '37', 'Dock charges', unstruck), (('fail', 'struck'), 'FAIL'))


KEYS = {'W': ('~~Berth tariffs~~', '4', 'Berth tariffs'), 'X': ('Wharf tariffs', '6', None), 'Y': ('Pier tariffs', '3', None), 'C': ('Dock rates', '21', None), 'K': ('Harbor fees', '9', None)}


def moved(text, table_text, after):  # the measured display order: the title unit on the other side of its table
    def f(r):
        u = next(x for x in r['units'] if x.get('kind') != 'table' and (x.get('text') or '').startswith(text))
        t = next(x for x in r['units'] if x.get('kind') == 'table' and any(c.get('text') == table_text for c in x['cells']))
        r['units'].remove(u); r['units'].insert(r['units'].index(t) + (1 if after else 0), u); return r
    return f


class TitleBelowItsTable(unittest.TestCase):
    def test_the_measured_display_is_what_the_fixture_says(self):
        tops = json.loads((N / 'title_below' / 'below_browser.json').read_text())
        self.assertGreater(tops['Berth tariffs'], tops['W']); self.assertLess(tops['Wharf tariffs'], tops['X']); self.assertGreater(tops['Pier tariffs'], tops['Y'])

    def test_unproved_sides_are_open_and_an_own_caption_passes(self):
        for k, (title, value, words) in KEYS.items():
            self.assertEqual(one('title_below', 'below', title, value, words), (('pass', None), 'PASS') if k == 'C' else (ORDER, 'UNRESOLVED'), k)
        self.assertEqual(one('title_below', 'below', *KEYS['W'], moved('Berth tariffs', 'Slips', True)), (ORDER, 'UNRESOLVED'))  # the route in display order
        self.assertEqual(one('title_below', 'below', *KEYS['X'], moved('Wharf tariffs', 'Docks', False)), (ORDER, 'UNRESOLVED'))

    def test_missing_another_tables_cell_and_a_lost_strike_still_fail(self):
        def missing(text): return lambda r: dict(r, units=[u for u in r['units'] if not (u.get('kind') != 'table' and (u.get('text') or '').startswith(text))])
        def owned_by_other(text):
            def f(r):
                u = next(x for x in r['units'] if x.get('kind') != 'table' and (x.get('text') or '').startswith(text)); r['units'].remove(u)
                q = next(x for x in r['units'] if x.get('kind') == 'table' and any(c.get('text') == 'Other' for c in x['cells']))
                q['cells'].append({'r': 1, 'c': 0, 'rs': 1, 'cs': 2, 'text': u['text'], 'anchor': u['anchor']}); return r
            return f
        for k in ('W', 'X', 'Y', 'K'):
            title, value, words = KEYS[k]
            self.assertEqual(one('title_below', 'below', title, value, words, missing(words or title)), (('fail', 'missing'), 'FAIL'), k)
            self.assertEqual(one('title_below', 'below', title, value, words, owned_by_other(words or title)), (('fail', 'placement'), 'FAIL'), k)  # its bytes are no cell of that table
        self.assertEqual(one('title_below', 'below', *KEYS['W'], unstruck), (('fail', 'struck'), 'FAIL'))


class TitleOnPageAndPictureBoxes(unittest.TestCase):
    """Root's coordinate controls (root_title_i_frame_review_v1): a PDF page or a picture has no source scanner, so its own boxes decide where the title stands.
    Invented boxes: the value in route row 1 at y 30-40; the title box above it (y 10-20) or below it (y 50-60) - the schema has no before-only title. Faithful
    routes list the title on its box's side and pass; a route that lists it on the other side is contradicted by the boxes and fails. No exception either way."""
    def graded(self, fmt, below, wrong_row):
        fid = 'invented/frame.' + fmt; box = (lambda b: {'page': 1, 'region': b}) if fmt == 'pdf' else (lambda b: {'file': fid, 'region': b})
        title, value, table = box([10, 50 if below else 10, 60, 60 if below else 20]), box([70, 30, 90, 40]), box([0, 0, 110, 70])
        row = (0 if below else 2) if wrong_row else (2 if below else 0)
        route = {'file_id': fid, 'units': [{'id': 't0', 'kind': 'table', 'anchor': table, 'cells': [{'r': row, 'c': 0, 'rs': 1, 'cs': 2, 'text': 'Dock charges', 'anchor': title},
                                                                                                   {'r': 1, 'c': 1, 'rs': 1, 'cs': 1, 'text': '37', 'anchor': value}]}]}
        t = {'key_id': 'invented/frame', 'file_id': fid, 'type': 'cell', 'format': 'cell/' + ('pdf' if fmt == 'pdf' else 'image'), 'split': 'public', 'excluded': set(), 'alternatives': {},
             'anchor': value, 'table_anchor': table, 'support': {'table_title': {'anchors': [title]}},
             'fields': {'printed_value': '37', 'display_value': '37', 'value_kind': 'number', 'row_label': None, 'header_path': [], 'periods': [], 'footnote_markers': [], 'section_path': [],
                        'row_context': [], 'table_title': ['Dock charges']}}
        g = grade.Grader(t, grade.RouteFile(route, None)); g.grade_cell()
        return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'table_title')

    def test_boxes_decide_the_side_on_pages_and_pictures(self):
        for fmt in ('pdf', 'png'):
            for below in (False, True):
                with self.subTest(fmt=fmt, below=below):
                    self.assertEqual(self.graded(fmt, below, False), ('pass', None))
                    self.assertEqual(self.graded(fmt, below, True), ('fail', 'placement'))


if __name__ == '__main__':
    unittest.main()
