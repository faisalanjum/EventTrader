"""A holder cell's own content told apart from the nested table it contains (Root OCR_NESTED_READBACK_20261023T0028; OCR). EdgarTools gives a cell only
its aggregate text (edgar/documents/strategies/table_processing.py `_extract_cell_content -> str`), so a holder cell's saved text also holds its
nested table's text, and the readback marked such a cell `aggregate: 'unresolved'`. The saved run records already state, for every run of a nested
cell, the holder cell's own code-point range too (two owners, each `text_at`). The readback states the nested table's range inside the holder text
ONLY when those records prove every non-white-space nested character, in order, inside one range holding nothing else; otherwise it stays
'unresolved'. Raw records are never changed.
Fixture: the real saved source-reading route of public CCL R2.htm (cand_decl job_pool15_decl attempt_14/source_reading/ROUTE.json), byte-identical.
Expected ranges come from the ORIGINAL's structure by plain arithmetic: in each of its 4 definition tables the body cell ends with a Details table of
10 one-line cells (R2.htm lines 59-82, 87-110, 115-138, 143-166), so that table is the holder text's last 10 lines. Never from the code under test.
Run with the qualified interpreter from a checkout: python -I -B -m unittest tests.driver.prepare.reconstruct.test_nested_aggregate"""
import copy, hashlib, json, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
FIXTURE = HERE / 'fixtures' / 'ccl_r2_source_child_route.json'
FIXTURE_SHA256 = 'bc656a3b1417828e9af0cd42540c9fdf9a0a270e89feb61cb2585451c949a5f3'
NESTED_LINES = 10  # the original's Details table: 5 rows x 2 one-line cells


def load():
    raw = FIXTURE.read_bytes(); assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256, 'fixture changed'
    return json.loads(raw)


def holders(route):  # (unit index, cell index, nested unit id) for every cell that names a nested table
    return [(i, k, t) for i, u in enumerate(route['units']) for k, c in enumerate(u.get('cells') or []) for t in c.get('tables') or []]


def expected(text):  # the nested table is the holder text's last NESTED_LINES lines (original structure); its range runs to the end
    tail = '\n'.join(text.split('\n')[-NESTED_LINES:]); return [len(text) - len(tail), len(text)]


def aggregates(R):  # (holder unit id, cell r, cell c) -> aggregate, from the composed body
    from driver.prepare import reconstruct
    out = {}
    for n, _, _ in reconstruct._units_in_order(R['sequence']):
        for c in n.get('cells', []):
            if 'aggregate' in c: out[(n['record']['id'], c['record']['r'], c['record']['c'])] = c['aggregate']
    return out


def shift_holder(route, i, k, by):  # move every run owner naming that holder cell by `by` code points (its saved text was prefixed by `by` characters)
    first = route['units'][i]['cells'][k]['anchor']['byte_start']
    for f in ('source_style', 'source_inline', 'source_hidden'):
        for rec in (route.get(f) or {}).get('records') or []:
            for o in rec.get('owners') or []:
                if o.get('unit') == route['units'][i]['id'] and o.get('cell') == first: o['text_at'] = [[a + by, b + by] for a, b in o['text_at']]


class NestedAggregateOnTheRealR2Child(unittest.TestCase):
    def setUp(self):
        from driver.prepare import reconstruct
        self.rc = reconstruct; self.route = load(); self.H = holders(self.route)
        self.assertEqual(len(self.H), 4)  # the original's 4 definition tables, each one Details table

    def check(self, route, want):  # want: {(holder id, r, c): expected aggregate}
        R = self.rc.readback(route); got = aggregates(R)
        self.assertEqual(got, want)
        self.assertEqual(self.rc.preserved(route, R), []); self.assertEqual(self.rc.annotations(route, R), [])  # raw records exact; the claim reproducible
        return R

    def want_all(self, route, unresolved=()):
        out = {}
        for i, k, t in self.H:
            u, c = route['units'][i], route['units'][i]['cells'][k]
            out[(u['id'], c['r'], c['c'])] = 'unresolved' if (i, k) in unresolved else {'nested': [{'unit': t, 'text_at': expected(c['text'])}]}
        return out

    def test_every_real_holder_states_its_nested_range(self):
        before = json.dumps(self.route, sort_keys=True)
        R = self.check(self.route, self.want_all(self.route))
        self.assertEqual(json.dumps(self.route, sort_keys=True), before)  # the readback never alters the saved route
        for i, k, t in self.H:  # the stated range holds exactly the nested table's own cell texts, in order (independent check of the expectation)
            c = self.route['units'][i]['cells'][k]; a, b = expected(c['text'])
            nested = next(u for u in self.route['units'] if u['id'] == t)
            self.assertEqual(c['text'][a:b].split('\n'), [x['text'] for x in nested['cells']])

    def test_a_missing_holder_owner_leaves_only_that_cell_unresolved(self):
        r = copy.deepcopy(self.route); i, k, t = self.H[0]; first = r['units'][i]['cells'][k]['anchor']['byte_start']
        rec = next(x for x in r['source_hidden']['records'] if any(o.get('unit') == t for o in x['owners']))
        rec['owners'] = [o for o in rec['owners'] if not (o.get('unit') == r['units'][i]['id'] and o.get('cell') == first)]
        self.check(r, self.want_all(r, unresolved={(i, k)}))

    def test_a_conflicting_holder_range_is_not_resolved(self):  # a nested run whose holder range points into the holder's own text
        r = copy.deepcopy(self.route); i, k, t = self.H[1]; first = r['units'][i]['cells'][k]['anchor']['byte_start']
        rec = next(x for x in r['source_hidden']['records'] if any(o.get('unit') == t for o in x['owners']))
        o = next(o for o in rec['owners'] if o.get('unit') == r['units'][i]['id'] and o.get('cell') == first); n = sum(b - a for a, b in o['text_at'])
        o['text_at'] = [[0, n]]
        self.check(r, self.want_all(r, unresolved={(i, k)}))

    def test_swapped_holder_ranges_break_the_order(self):
        r = copy.deepcopy(self.route); i, k, t = self.H[2]; first = r['units'][i]['cells'][k]['anchor']['byte_start']
        recs = [x for x in r['source_hidden']['records'] if any(o.get('unit') == t for o in x['owners'])]
        hold = [next(o for o in x['owners'] if o.get('unit') == r['units'][i]['id'] and o.get('cell') == first) for x in recs]
        hold[0]['text_at'], hold[-1]['text_at'] = hold[-1]['text_at'], hold[0]['text_at']
        self.check(r, self.want_all(r, unresolved={(i, k)}))

    def test_holder_text_before_and_after_the_table_including_repeated_nested_text(self):
        r = copy.deepcopy(self.route); i, k, t = self.H[3]; c = r['units'][i]['cells'][k]
        a, b = expected(c['text']); first_line = c['text'][a:b].split('\n')[0]  # 'Name:': a string search would find this copy first
        c['text'] = first_line + ' ' + c['text'] + '\nAfter'; shift_holder(r, i, k, len(first_line) + 1)
        want = self.want_all(r); want[(r['units'][i]['id'], c['r'], c['c'])] = {'nested': [{'unit': t, 'text_at': [a + len(first_line) + 1, b + len(first_line) + 1]}]}
        self.check(r, want)

    def two_tables(self, before):  # the first holder given a second nested table: a copy of its Details table, unit appended last (saved order), its text after (or before) the holder's
        r = copy.deepcopy(self.route); i, k, t = self.H[0]; c = r['units'][i]['cells'][k]; first = c['anchor']['byte_start']; hid = r['units'][i]['id']
        a, b = expected(c['text']); part = c['text'][a:b]; old = len(c['text'])
        clone = copy.deepcopy(next(u for u in r['units'] if u['id'] == t)); clone['id'] = 'tcopy'; r['units'].append(clone); c['tables'] = c['tables'] + ['tcopy']
        added = []
        for rec in r['source_hidden']['records']:
            n = next((o for o in rec['owners'] if o.get('unit') == t), None); h = next((o for o in rec['owners'] if o.get('unit') == hid and o.get('cell') == first), None)
            if n and h:
                at = (lambda x: x - a) if before else (lambda x: x - a + old + 1)
                added.append({**rec, 'owners': [dict(n, unit='tcopy'), dict(h, text_at=[[at(p), at(q)] for p, q in h['text_at']])]})
        r['source_hidden']['records'] += added
        if before:
            c['text'] = part + '\n' + c['text']; n0 = len(part) + 1
            for rec in r['source_hidden']['records'][:-len(added)]:
                for o in rec['owners']:
                    if o.get('unit') == hid and o.get('cell') == first: o['text_at'] = [[p + n0, q + n0] for p, q in o['text_at']]
        else: c['text'] = c['text'] + '\n' + part
        return r, (i, k, t), (a, b, old, len(part))

    def test_two_nested_tables_each_get_their_range_in_saved_order(self):
        r, (i, k, t), (a, b, old, n) = self.two_tables(before=False); c = r['units'][i]['cells'][k]
        want = self.want_all(self.route); want[(r['units'][i]['id'], c['r'], c['c'])] = {'nested': [{'unit': t, 'text_at': [a, b]}, {'unit': 'tcopy', 'text_at': [old + 1, old + 1 + n]}]}
        self.check(r, want)

    def test_two_nested_tables_out_of_saved_order_stay_unresolved(self):  # the later unit's text stands first: no ordered placement is proved
        r, (i, k, t), _ = self.two_tables(before=True)
        self.check(r, self.want_all(self.route, unresolved={(i, k)}))

    # Root OCR_AGGREGATE_REVIEW_20261023T0044: a claim must cover the WHOLE composed child. The composed kinds _resolve places are tables and images in
    # cells and captions on tables; each one the proof does not cover keeps that holder unresolved, beside the real positive (the other holders).
    def ref(self, r, i, k):  # a saved cell reference to units[i].cells[k], in the shape the producer writes (a nested unit's `cell`)
        c = r['units'][i]['cells'][k]; return {'table': r['units'][i]['id'], 'r': c['r'], 'c': c['c'], 'rs': c['rs'], 'cs': c['cs'], **c['source']}

    def test_root_caption_control_a_cell_text_moved_into_a_caption_is_not_resolved(self):
        r = copy.deepcopy(self.route); i, k, t = self.H[0]; nested = next(u for u in r['units'] if u['id'] == t); last = nested['cells'].pop()
        r['units'].append({'id': 'caption_control', 'kind': 'caption', 'text': last['text'], 'anchor': last['anchor'], 'source_table': nested['source_table']})
        for rec in r['source_hidden']['records']:
            for o in rec['owners']:
                if o.get('unit') == t and o.get('cell') == last['anchor']['byte_start']: o.pop('cell'); o['unit'] = 'caption_control'
        R = self.check(r, self.want_all(r, unresolved={(i, k)}))
        self.assertIn('caption_control', [c['record']['id'] for n, _, _ in self.rc._units_in_order(R['sequence']) for c in n.get('captions', [])])  # composed as a caption

    def test_an_image_beside_the_table_in_the_holder_is_not_resolved(self):
        r = copy.deepcopy(self.route); i, k, t = self.H[1]
        r['units'].append({'id': 'image_in_holder', 'kind': 'image', 'text': '', 'src': 'x.png', 'cell': self.ref(r, i, k)})
        self.check(r, self.want_all(r, unresolved={(i, k)}))

    def test_content_inside_the_nested_tables_cells_is_not_resolved(self):
        r = copy.deepcopy(self.route); i, k, t = self.H[2]; j = next(x for x, u in enumerate(r['units']) if u['id'] == t)
        r['units'].append({'id': 'image_in_nested', 'kind': 'image', 'text': '', 'src': 'x.png', 'cell': self.ref(r, j, 0)})
        self.check(r, self.want_all(r, unresolved={(i, k)}))

    def test_two_levels_claim_nothing_without_proof_at_either_level(self):  # a table inside the nested table: the outer and the inner holder stay unresolved
        r = copy.deepcopy(self.route); i, k, t = self.H[3]; j = next(x for x, u in enumerate(r['units']) if u['id'] == t)
        deep = copy.deepcopy(r['units'][j]); deep['id'] = 'tdeep'; deep['cell'] = self.ref(r, j, 0); r['units'].append(deep)
        r['units'][j]['cells'][0]['tables'] = ['tdeep']
        want = self.want_all(r, unresolved={(i, k)}); c0 = r['units'][j]['cells'][0]; want[(t, c0['r'], c0['c'])] = 'unresolved'
        self.check(r, want)

    def test_a_damaged_claim_in_R_is_caught(self):
        R = self.rc.readback(self.route); i, k, t = self.H[0]
        for n, _, _ in self.rc._units_in_order(R['sequence']):
            for c in n.get('cells', []):
                if isinstance(c.get('aggregate'), dict): c['aggregate']['nested'][0]['text_at'][0] += 1; break
            else: continue
            break
        self.assertNotEqual(self.rc.annotations(self.route, R), [])


if __name__ == '__main__':
    unittest.main()
