"""Contradictory nonempty row spans (ROOT_TABLE_ORDER, Oct 9): inside one declared candidate grid, a cell's row span must not cover a DIFFERENT
nonempty cell of the same certain source table - the route then states a false row/heading relationship. A failure-only gate: same-source
fragments, nested source tables, separate candidate grids (split/continued tables), empty or padding cells and unproved identities never fail,
and the gate's passing grants no whole-table credit. The gate reports the FIRST proved collision per file - a failure witness, never a count of
pairs (root's ROOT_TABLE_V1_REVIEW). Public invented data only (table_native_review_20261009) plus synthetic sources here."""
import copy
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
from benchmarks.prepare.grader import grade

PROOF = HERE / 'fixtures' / 'table_spans'   # the dependency closure of the public table_native_review_20261009 fixture this test reads
RAW = (PROOF / 'evidence/packets/synthetic/source.htm').read_bytes()
WHOLE = json.loads((PROOF / 'outputs/whole/saved.json').read_text())
CROSS = json.loads((PROOF / 'outputs/cross_group_rowspan/saved.json').read_text())   # Metric's rowspan extended over the nonempty North heading


def collisions(route, raw=RAW):
    return grade.gates_for_file(grade.RouteFile(copy.deepcopy(route), raw), route.get('status', 'OK'))['span_collisions']


def cell_of(route, text, n=0):
    return [c for c in route['units'][0]['cells'] if c['text'] == text][n]


def at(raw, text, n=0):  # the byte span of the n-th occurrence of text in raw
    i = -1
    for _ in range(n + 1): i = raw.index(text.encode(), i + 1)
    return {'byte_start': i, 'byte_end_exclusive': i + len(text.encode())}


def table(raw, cells, tid='t0'):  # a one-table route over raw with the given (r, c, rs, cs, text, anchor) cells
    return {'file_id': 'synthetic/source.htm', 'sha256': grade.sha256(raw), 'status': 'OK',
            'units': [{'id': tid, 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)},
                       'cells': [dict(r=r, c=c, rs=rs, cs=cs, text=t, anchor=a) for r, c, rs, cs, t, a in cells]}]}


class TableSpans(unittest.TestCase):
    def test_the_original_negative_fails_and_its_untouched_positive_passes(self):
        self.assertEqual(collisions(WHOLE), [])
        found = collisions(CROSS)
        self.assertEqual(len(found), 1)
        metric, north = cell_of(CROSS, 'Metric'), cell_of(CROSS, 'North')
        self.assertEqual(found[0]['spanning'][:2], [metric['r'], metric['c']]); self.assertEqual(found[0]['covered'][:2], [north['r'], north['c']])

    def test_adjacency_is_not_overlap(self):  # a span that ends right above the next nonempty cell covers nothing of it
        route = copy.deepcopy(CROSS); cell_of(route, 'Metric')['rs'] = 2
        self.assertEqual(collisions(route), [])

    def test_any_spanning_column_that_meets_the_covered_cell_counts(self):  # Note (column 3) extended over row 2: North spans columns 0-3, so it IS covered
        route = copy.deepcopy(WHOLE); cell_of(route, 'Note')['rs'] = 3
        self.assertEqual(len(collisions(route)), 1)
        route = copy.deepcopy(WHOLE); cell_of(route, '2026')['rs'] = 2; cell_of(route, '2026')['c'] = 1   # 2026 over row 2 col 1: North again
        self.assertEqual(len(collisions(route)), 1)

    def test_repeated_equal_text_is_identity_by_source_not_by_text(self):
        route = copy.deepcopy(WHOLE); second = cell_of(route, 'Metric', 1); second['rs'] = 3   # the second Metric over South: different cells, same text elsewhere
        self.assertEqual(len(collisions(route)), 1)
        route = copy.deepcopy(WHOLE)   # two equal texts that do not overlap stay clean
        self.assertEqual(collisions(route), [])

    def test_fragments_of_one_source_cell_are_one_cell(self):
        raw = b'<table><tr><td>Total revenue</td><td>5</td></tr><tr><td>Other</td><td>6</td></tr></table>'
        route = table(raw, [(0, 0, 2, 1, 'Total', at(raw, 'Total')), (1, 0, 1, 1, 'revenue', at(raw, 'revenue')), (0, 1, 1, 1, '5', at(raw, '5')),
                            (2, 0, 1, 1, 'Other', at(raw, 'Other')), (2, 1, 1, 1, '6', at(raw, '6'))])
        self.assertEqual(collisions(route, raw), [])
        route['units'][0]['cells'][1].update(text='Other', anchor=at(raw, 'Other'))   # the covered fragment replaced by a different source cell: a collision
        self.assertEqual(len(collisions(route, raw)), 1)

    def test_nested_source_tables_are_separate_grids(self):
        raw = b'<table><tr><td>Outer A<table><tr><td>Inner 1</td></tr><tr><td>Inner 2</td></tr></table></td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>'
        route = table(raw, [(0, 0, 2, 1, 'Outer A', at(raw, 'Outer A')), (1, 0, 1, 1, 'Inner 1', at(raw, 'Inner 1')), (0, 1, 1, 1, 'B', at(raw, 'B')),
                            (2, 0, 1, 1, 'C', at(raw, 'C')), (2, 1, 1, 1, 'D', at(raw, 'D'))])
        self.assertEqual(collisions(route, raw), [])

    def test_split_or_continued_grids_are_never_compared(self):
        route = copy.deepcopy(CROSS); unit = route['units'][0]; cells = unit['cells']
        top = [c for c in cells if c['r'] < 2]; rest = [c for c in cells if c['r'] >= 2]
        route['units'] = [dict(unit, id='part1', cells=top), dict(unit, id='part2', cells=rest)]   # Metric's span reaches row 2 only in its own grid
        self.assertEqual(collisions(route), [])

    def test_empty_and_padding_cells_are_not_graded(self):
        route = copy.deepcopy(WHOLE); route['units'][0]['cells'].append(dict(r=2, c=0, rs=1, cs=1, text='', anchor=None))   # an empty slot under Metric
        cell_of(route, 'Metric')['rs'] = 2
        self.assertEqual(collisions(route), [])
        route = copy.deepcopy(WHOLE); blank = next(c for c in route['units'][0]['cells'] if c['text'] == '' and c.get('anchor'))
        blank['rs'] = 2                                                                                   # an empty cell's span covers a nonempty one
        self.assertEqual(collisions(route), [])

    def test_unknown_ownership_never_fails(self):
        route = copy.deepcopy(CROSS); north = cell_of(route, 'North')
        north['anchor'] = {'byte_start': north['anchor']['byte_start'], 'byte_end_exclusive': cell_of(route, 'Revenue')['anchor']['byte_end_exclusive']}
        self.assertIsNone(grade.RouteFile(copy.deepcopy(route), RAW).source_cell(north['anchor']))
        self.assertEqual(collisions(route), [])                  # North's place spans two source cells: no unique identity
        uncertain = RAW.replace(b'<body>', b'<body><style>th{display:var(--x)}</style>')
        self.assertFalse(grade.Visible(uncertain).certain)
        moved = copy.deepcopy(CROSS)
        for c in moved['units'][0]['cells']:
            if c.get('anchor'): c['anchor'] = {k: v + len(uncertain) - len(RAW) for k, v in c['anchor'].items()}
        self.assertEqual(collisions(moved, uncertain), [])       # an uncertain reading proves no identity

    def test_huge_declared_spans_and_rows_only_visit_existing_rows(self):  # Root: never range over a declared span; valid huge integers must not hang
        import time
        t0 = time.perf_counter()
        route = copy.deepcopy(WHOLE); cell_of(route, 'Metric')['rs'] = 10 ** 15   # first Metric over every later row: ONE witness, from the full pair set
        found = collisions(route)
        self.assertEqual(len(found), 1)
        self.assertIn(tuple(found[0]['covered']), {(2, 0), (3, 0), (4, 0), (5, 0), (7, 0), (8, 0), (9, 0)})
        route = copy.deepcopy(WHOLE); cell_of(route, 'Cost', 1)['rs'] = 10 ** 15     # the last row's cell: nothing below it
        self.assertEqual(collisions(route), [])
        raw = b'<table><tr><td>Head</td></tr><tr><td>Far</td></tr></table>'           # sparse, with a valid huge row number
        route = table(raw, [(0, 0, 10 ** 12 + 1, 1, 'Head', at(raw, 'Head')), (10 ** 12, 0, 1, 1, 'Far', at(raw, 'Far'))])
        self.assertEqual(len(collisions(route, raw)), 1)
        route['units'][0]['cells'][0]['rs'] = 10 ** 12
        self.assertEqual(collisions(route, raw), [])                                    # adjacency at a huge row number
        self.assertLess(time.perf_counter() - t0, 2.0)

    def test_a_damaged_grid_yields_one_witness_from_its_full_pair_set(self):  # OCR's cost finding (2,000 x 5 measured by OCR): every cell of 400 x 5 spans 10**12
        import time
        rows, cols = 400, 5
        raw = b'<table>' + b''.join(b'<tr>' + b''.join(b'<td>v%d_%d</td>' % (r, c) for c in range(cols)) + b'</tr>' for r in range(rows)) + b'</table>'
        route = table(raw, [(r, c, 10 ** 12, 1, 'v%d_%d' % (r, c), at(raw, 'v%d_%d<' % (r, c))) for r in range(rows) for c in range(cols)])
        for cell in route['units'][0]['cells']: cell['anchor']['byte_end_exclusive'] -= 1   # the text only, not the '<' that made it unique
        t0 = time.perf_counter(); found = collisions(route, raw); took = time.perf_counter() - t0
        self.assertEqual(len(found), 1)                                          # a failure witness, not a census of every pair
        (s, c, _), (s2, c2) = found[0]['spanning'], found[0]['covered']
        self.assertTrue(c2 == c and s2 > s)                                      # one of the (r, c) -> (r' > r, c) pairs the damage makes
        self.assertLess(took, 2.0)

    def test_two_separate_contradictions_give_one_witness_from_either(self):
        route = copy.deepcopy(WHOLE); cell_of(route, 'Metric')['rs'] = 3; cell_of(route, 'Metric', 1)['rs'] = 3   # Metric over North, second Metric over South
        found = collisions(route)
        self.assertEqual(len(found), 1)
        self.assertIn((tuple(found[0]['spanning'][:2]), tuple(found[0]['covered'])), {((0, 0), (2, 0)), ((5, 0), (7, 0))})

    def test_cell_order_is_irrelevant(self):
        for seed in range(5):
            route = copy.deepcopy(CROSS); random.Random(seed).shuffle(route['units'][0]['cells'])
            self.assertEqual(len(collisions(route)), 1)
            route = copy.deepcopy(WHOLE); random.Random(seed).shuffle(route['units'][0]['cells'])
            self.assertEqual(collisions(route), [])

    def test_the_run_reports_the_gate_and_changes_no_target(self):
        target = grade.load_key(PROOF / 'key_required', catalog=PROOF / 'catalog.csv')[0]; fid = target['file_id']
        verdicts = {}
        for name, route in (('whole', WHOLE), ('cross', CROSS)):
            with tempfile.TemporaryDirectory() as d:
                routes = Path(d) / 'routes'; (routes / fid).parent.mkdir(parents=True)
                (routes / (fid + '.json')).write_text(json.dumps(route))
                report = grade.run(PROOF / 'key_required', routes, Path(d) / 'out', catalog=PROOF / 'catalog.csv')
                verdicts[name] = {k: v['verdict'] for k, v in report['targets'].items()}
                gate = report['gates']['table_spans']
                self.assertEqual(gate['pass'], name == 'whole')
                self.assertEqual(len(gate['collisions'].get(fid, [])), 0 if name == 'whole' else 1)
                self.assertTrue(all(v['pass'] for k, v in report['gates'].items() if k != 'table_spans'))
        self.assertEqual(verdicts['whole'], verdicts['cross'])   # the targets' own verdicts are untouched: the guard is a file gate


if __name__ == '__main__':
    unittest.main()
