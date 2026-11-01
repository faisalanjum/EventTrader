"""Large tables must not be rescanned for every saved owner; placements stay exact."""
import collections
import itertools
import unittest
from unittest.mock import patch

from driver.prepare import reconstruct as rb
from tests.driver.prepare.reconstruct.test_nested_aggregate import load, holders


def oracle(owner, units):
    """Independent source-record lookup: one unique unit and exactly one first span."""
    if not isinstance(owner, dict): return None
    hits = [i for i, u in enumerate(units) if u.get('id') == owner.get('unit')]
    if len(hits) != 1: return None
    i = hits[0]
    if 'cell' not in owner: return ('unit', i)
    if owner['cell'] is None: return None
    found = []
    for k, c in enumerate(units[i].get('cells') or []):
        if not isinstance(c, dict): continue
        spans = c.get('anchor'); spans = spans if isinstance(spans, list) else [spans]
        starts = [a['byte_start'] for a in spans if isinstance(a, dict) and 'byte_start' in a]
        if (starts[0] if starts else None) == owner['cell']: found.append(k)
    return ('cell', i, found[0]) if len(found) == 1 else None


class OwnerLookup(unittest.TestCase):
    def test_large_holder_has_linear_anchor_read_budget_in_builder_and_checker(self):
        route = load(); parent, _, _ = holders(route)[0]
        route['units'][parent]['cells'] += [dict(r=1000, c=k, rs=1, cs=1, text='',
                                               anchor={'byte_start': 10000000 + k}) for k in range(1024)]
        cells = sum(len(u.get('cells') or []) for u in route['units'])
        owners = sum(len(rec.get('owners') or []) for f in rb.ATTACHED
                     for rec in (route.get(f, []) if f in rb.LISTS else (route.get(f) or {}).get('records', [])))
        budget, reads = 8 * (cells + owners), 0
        first = rb._first_byte
        def bounded(cell):
            nonlocal reads
            reads += 1
            self.assertLessEqual(reads, budget, 'repeated full-table scans exceed linear source-anchor budget')
            return first(cell)
        with patch.object(rb, '_first_byte', bounded):
            result = rb.readback(route)
            self.assertEqual(rb.preserved(route, result), [])
            self.assertEqual(rb.annotations(route, result), [])
        self.assertEqual(rb.canon(rb.inverse(result)), rb.canon(route))

    def test_complete_scalar_and_malformed_anchor_pairs_match_independent_oracle(self):
        nan = float('nan')
        values = [None, False, 0, -0.0, True, 1, 1.0, 2.5, '1', float('inf'), nan, [1], {'x': 1}]
        queries = values + [float('nan'), [], {'x': 2}, 'missing']
        for pair in itertools.product(values, repeat=2):
            units = [dict(id='table', cells=[dict(anchor={'byte_start': v}) for v in pair])]
            index = rb._cell_index(units)
            for key in queries:
                owner = dict(unit='table', cell=key)
                with self.subTest(anchors=pair, key=key):
                    want = oracle(owner, units)
                    self.assertEqual(rb._owner_site(owner, units, {'table': 0}, index), want)
                    self.assertEqual(rb._owner_site(owner, units, {'table': 0}), want)

    def test_missing_null_anchor_shapes_and_non_dict_cells_keep_real_positive(self):
        units = [dict(id='table', cells=[None, 7, {}, dict(anchor=[]),
                                        dict(anchor=[None, {'other': 1}, {'byte_start': 12}, {'byte_start': 13}])])]
        index = rb._cell_index(units)
        for owner in (None, [], 'bad', {}, dict(unit='absent'), dict(unit='table'),
                      dict(unit='table', cell=None), dict(unit='table', cell=12), dict(unit='table', cell=13)):
            with self.subTest(owner=owner):
                self.assertEqual(rb._owner_site(owner, units, {'table': 0}, index), oracle(owner, units))
        self.assertEqual(rb._owner_site(dict(unit='table', cell=12), units, {'table': 0}, index), ('cell', 0, 4))
        for bad in ([], {}):
            with self.assertRaises(TypeError): rb._owner_site(dict(unit=bad), units, {'table': 0}, index)

    def test_duplicate_units_and_cell_permutations_and_new_route_do_not_share_index(self):
        units = [dict(id='table', cells=[dict(anchor={'byte_start': 10}), dict(anchor={'byte_start': 20})])]
        for cells in itertools.permutations(units[0]['cells']):
            route_units = [dict(id='table', cells=list(cells))]; index = rb._cell_index(route_units)
            for key in (10, 20, 30):
                owner = dict(unit='table', cell=key)
                self.assertEqual(rb._owner_site(owner, route_units, {'table': 0}, index), oracle(owner, route_units))
        duplicate = units + units
        counts = collections.Counter(u['id'] for u in duplicate)
        by_id = {u['id']: i for i,u in enumerate(duplicate) if counts[u['id']] == 1}
        self.assertIsNone(rb._owner_site(dict(unit='table', cell=10), duplicate, by_id, rb._cell_index(duplicate)))
        old = rb._cell_index(units); units[0]['cells'][0]['anchor']['byte_start'] = 30
        new = rb._cell_index(units)
        self.assertEqual(rb._owner_site(dict(unit='table', cell=30), units, {'table': 0}, new), ('cell', 0, 0))
        self.assertNotEqual(old, new)

    def test_unique_null_or_missing_unit_id_still_resolves_and_duplicate_null_does_not(self):
        for unit in (dict(cells=[dict(anchor={'byte_start': 10})]),
                     dict(id=None, cells=[dict(anchor={'byte_start': 10})])):
            units = [unit]; by_id = rb._resolve(units)[0]; index = rb._cell_index(units)
            self.assertEqual(rb._owner_site({}, units, by_id, index), ('unit', 0))
            self.assertEqual(rb._owner_site(dict(cell=10), units, by_id, index), ('cell', 0, 0))
            duplicate = [unit, unit]; by_id = rb._resolve(duplicate)[0]
            self.assertIsNone(rb._owner_site({}, duplicate, by_id, rb._cell_index(duplicate)))
            self.assertIsNone(rb._owner_site(dict(cell=10), duplicate, by_id, rb._cell_index(duplicate)))

    def test_unit_permutation_keeps_each_cells_index_with_its_unit(self):
        units = [dict(id='left', cells=[dict(anchor={'byte_start': 10})]),
                 dict(id='right', cells=[dict(anchor={'byte_start': 10}), dict(anchor={'byte_start': 20})])]
        for ordered in itertools.permutations(units):
            by_id = rb._resolve(ordered)[0]; index = rb._cell_index(ordered)
            for owner in (dict(unit='left', cell=10), dict(unit='right', cell=10), dict(unit='right', cell=20)):
                self.assertEqual(rb._owner_site(owner, ordered, by_id, index), oracle(owner, ordered))


if __name__ == '__main__': unittest.main()
