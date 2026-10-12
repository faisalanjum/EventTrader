"""Consecutive joined levels retain uncertainty; no joined carrier earns a pass.

The fixed fifty fixtures are Root's independently invented source-first controls.
Their truths and expected states predate this correction. Both actual callers use
the same headings; the cell caller adds an unrelated, independently bound table.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.tests.test_association_governing import table

CASES = json.loads((Path(__file__).with_name('fixtures') / 'heading_joined_levels' / 'cases.json').read_text())


def rows(case, caller):
    key, route, raw = copy.deepcopy(case['key']), copy.deepcopy(case['route']), case['raw']
    if caller == 'cell':
        raw = raw.replace('</body>', '<table><tr><td>Cedar count</td><td>47</td></tr></table></body>')
        tb = table(raw.encode(), 'count-table', 0, [['Cedar count', '47']])
        route['units'] = route['units'][:-1] + [tb]
        key.update(type='cell', format='cell/html', anchor=tb['cells'][1]['anchor'], table_anchor=tb['anchor'])
        key['fields'] = {'printed_value': '47', 'display_value': '47', 'section_path': key['fields']['section_path']}
    route['sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    key['excluded'] = set(key.get('excluded') or [])
    g = grade.Grader(key, grade.RouteFile(route, raw.encode(), 'html'))
    (g.grade_cell if caller == 'cell' else g.grade_structure)()
    return g.rows


def section(case, caller):
    return next(r for r in rows(case, caller) if r['check'] == 'section_path')


def long_case(n, joined):
    labels = ['Canopy layer ' + str(i) for i in range(n)]
    text = 'The public forest count is recorded below.'
    raw = '<html><body>' + ''.join('<h2>' + s + '</h2>' for s in labels) + '<p>' + text + '</p></body></html>'
    def at(s):
        a = raw.index(s)
        return {'byte_start': a, 'byte_end_exclusive': a + len(s)}
    heads = [{'id': 'level-' + str(i), 'kind': 'heading', 'text': s, 'anchor': at(s)} for i, s in enumerate(labels)]
    units = ([{'id': 'joined', 'kind': 'heading', 'text': '\n'.join(labels),
               'anchor': {'byte_start': heads[0]['anchor']['byte_start'], 'byte_end_exclusive': heads[-1]['anchor']['byte_end_exclusive']}}]
             if joined else copy.deepcopy(heads))
    units.append({'id': 'count', 'kind': 'text', 'text': text, 'anchor': at(text)})
    key = {'key_id': 'invented/long-prefix', 'file_id': 'public/forest-long.html', 'type': 'structure', 'format': 'structure/html',
           'split': 'public', 'anchor': at(text), 'fields': {'printed_text': text, 'kind': 'paragraph', 'section_path': labels},
           'support': {'section_path': {'how': 'reviewed', 'anchors': [h['anchor'] for h in heads]}}, 'alternatives': {}, 'excluded': []}
    return {'raw': raw, 'key': key, 'route': {'file_id': key['file_id'], 'units': units}}


class JoinedLevelTests(unittest.TestCase):
    def test_fixed_fifty_source_first_controls_both_callers(self):
        for name, case in CASES.items():
            for caller in ('structure', 'cell'):
                with self.subTest(name=name, caller=caller):
                    got = section(case, caller)
                    self.assertIn(got['verdict'], case['expected'])
                    if case['source_truth'] == 'faithful' and len(case['group_lengths']) < sum(case['group_lengths']):
                        self.assertEqual((got['verdict'], got['reason']), ('unresolved', 'joined_levels'))

    def test_longer_joined_prefixes_both_callers(self):
        for n in (6, 12, 31):
            for caller in ('structure', 'cell'):
                with self.subTest(levels=n, caller=caller):
                    got = section(long_case(n, True), caller)
                    self.assertEqual((got['verdict'], got['reason']), ('unresolved', 'joined_levels'))

    def test_longer_separated_positive_and_wrong_source_negative(self):
        for n in (6, 12, 31):
            case = long_case(n, False)
            damaged = copy.deepcopy(case)
            damaged['route']['units'][0]['anchor'] = case['key']['anchor']
            for caller in ('structure', 'cell'):
                with self.subTest(levels=n, caller=caller):
                    self.assertEqual(section(case, caller)['verdict'], 'pass')
                    self.assertEqual(section(damaged, caller)['verdict'], 'fail')


if __name__ == '__main__':
    unittest.main()
