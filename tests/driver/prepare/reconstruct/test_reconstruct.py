"""Permanent reconstruction controls for driver.prepare.reconstruct (unittest, run from the repository root).
Ported from the qualified v10 suite (29 tests; two order expectations changed for v11, see the M2 note) and the M2 saved-order controls.
Three kinds kept apart: A. positives against hand-written fixture truth; B. a changed saved route E1 is kept faithfully (or reported);
C. damage to R with E unchanged fails the one boundary. Fixtures: fixtures/ (small frozen public routes; PROVENANCE.json pins each file).
The input-contract attempt is built here in a temporary folder through the native archive (no research folder or environment variable)."""
import copy, gzip, hashlib, json, shutil, tempfile, unittest
from pathlib import Path

from driver.prepare import reconstruct as rb
from driver.prepare.get import archive
from tests.driver.prepare.convert.test_xml_route_reading import oracle as _oracle

FIX = Path(__file__).with_name('fixtures')
_PINS = json.loads((FIX / 'PROVENANCE.json').read_text())['sha256']
RUN = PUBLIC_ATTEMPT = None
_tmp = None


def load(name):
    body = (FIX / f'{name}.json').read_bytes(); assert hashlib.sha256(body).hexdigest() == _PINS[f'{name}.json'], name
    return json.loads(body)


def _public_attempt(root):
    """A native-shaped v4 attempt: one prepared picture input and one kept raw reading, both stored and restored by the native archive."""
    E = load('h4_linker_document')['route']; a = root / 'public_attempt'; a.mkdir()
    S = archive.store_blob(a / 'prepared', b'\x89PNG public control bytes'); E['units'][4]['input'] = {'member_sha256': S, 'input_sha256': S, 'how': 'member'}
    P = archive.store_blob(a / 'raw_reading', json.dumps({'type': 'Document', 'children': []}).encode())
    body = json.dumps(E).encode(); (a / 'ROUTE.json').write_bytes(body)
    raw = json.dumps({'file_id': E['file_id'], 'source_sha256': E['sha256'], 'raw_reading_sha256': P}).encode(); (a / 'RAW_READING.json').write_bytes(raw)
    (a / 'COMPLETE.json').write_text(json.dumps({'file_id': E['file_id'], 'source_sha256': E['sha256'], 'route_sha256': hashlib.sha256(body).hexdigest(), 'native_status': E['status'],
                                                 'prepared_input_sha256': [S], 'reader_called': False, 'raw_reading_sha256': P, 'raw_reading_receipt_sha256': hashlib.sha256(raw).hexdigest()}))
    return a


def setUpModule():
    global RUN, PUBLIC_ATTEMPT, _tmp
    _tmp = tempfile.TemporaryDirectory(); RUN = Path(_tmp.name); PUBLIC_ATTEMPT = _public_attempt(RUN)


def tearDownModule():
    _tmp.cleanup()

fold = lambda s: ' '.join((s or '').split())  # truth side only, white space only

# Harness adaptation (pinned in HARNESS_DIFF.txt): the old projections read the version-2 shape (records inside nodes).
def shape(nodes):
    out = []
    for n in nodes:
        if 'record' not in n:
            out.append(('list', [shape(item['members']) for item in n['items']])); continue
        r = n['record']
        if r.get('kind') == 'table':
            cells = [(c['record']['r'], c['record']['c'], c['record']['rs'], c['record']['cs'], fold(c['record']['text'])) + ((shape(c['children']),) if c.get('children') else ()) for c in n['cells']]
            out.append(('table', cells, [fold(x['record']['text']) for x in n.get('captions', [])]))
        elif r.get('kind') == 'image':
            out.append(('image', r['src']))
        else:
            out.append((r['kind'], fold(r['text'])))
    return out

H1 = [('table', [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Asia'),
                 (1, 1, 1, 1, 'mid deep 7', [('table', [(0, 0, 1, 1, 'mid'), (0, 1, 1, 1, 'deep 7', [('table', [(0, 0, 1, 1, 'deep'), (0, 1, 1, 1, '7')], [])])], [])])], [])]
H2 = [('table', [(0, 0, 1, 1, 'Total'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Asia'),
                 (1, 1, 1, 1, 'Total 10 Total 10', [('table', [(0, 0, 1, 1, 'Total'), (0, 1, 1, 1, '10')], []), ('table', [(0, 0, 1, 1, 'Total'), (0, 1, 1, 1, '10')], [])])], [])]
H3 = [('table', [(0, 0, 1, 1, 'Asia'), (0, 1, 1, 1, 'Cap only', [('table', [(0, 0, 1, 1, '')], ['Cap only'])])], [])]
H4 = [('text', 'Item 2. Overview'), ('text', 'Free cash flow is not GAAP(1). See the table.'),
      ('table', [(0, 0, 1, 2, 'Title'), (1, 0, 2, 1, ''), (1, 1, 1, 3, 'Three Months Ended'), (2, 1, 1, 1, 'Free cash flow(1)'), (2, 2, 1, 1, '$'), (2, 3, 1, 1, '(506'), (2, 4, 1, 1, ')')], []),
      ('list', [[('list_item', 'First point')]]), ('image', 'x.jpg'), ('text', '(1) Note text.')]

def oracle():
    return _oracle

def tuples(R):  # harness adaptation: the existing tree() tuple composition over the records the version-2 tree represents
    els = rb._xml_records(R['xml']['elements']); at = {e['anchor']['byte_start']: i for i, e in enumerate(els)}
    return [(e['name'], e.get('attributes', {}), e.get('namespaces', {}), [('child', at[x['child']]) if isinstance(x, dict) else x for x in e.get('content', [])]) for e in els]

norm = lambda x: json.loads(json.dumps(x))
flat = units = lambda R: [n for n, _, _ in rb._units_in_order(R['sequence'])]
top = lambda R: [n for n in R['sequence'] if 'record' in n]
def node(R, unit):
    return next(n for n in units(R) if n['record'].get('id') == unit)

def ok(E, R, prepared=None): return rb.preserved(E, R) == [] and rb.annotations(E, R, prepared) == []
def bad(E, R): return rb.preserved(E, R) != []


class A_Positives(unittest.TestCase):
    def test_html_compositions_match_markup_truth_and_the_boundary(self):
        for name, want in (('h1_two_levels', H1), ('h2_repeated_siblings', H2), ('h3_child_caption', H3), ('h4_linker_document', H4)):
            with self.subTest(name):
                E = load(name)['route']; R = rb.readback(E)
                self.assertEqual(shape(R['sequence']), want); self.assertEqual(rb.preserved(E, R), []); self.assertEqual(rb.annotations(E, R), [])
                self.assertEqual(rb.canon(rb.inverse(R)), rb.canon(E))

    def test_holder_keeps_saved_aggregate_bytes_and_says_placement_is_unresolved(self):
        E = load('h1_two_levels')['route']; R = rb.readback(E)
        holder = next(c for c in node(R, 't0')['cells'] if c.get('children'))
        self.assertEqual(holder['record']['text'], E['units'][0]['cells'][3]['text']); self.assertEqual(holder['aggregate'], 'unresolved')

    def test_valid_repeats_survive(self):
        R = rb.readback(load('h2_repeated_siblings')['route'])
        kids = [c for c in node(R, 't0')['cells'] if c.get('children')][0]['children']
        self.assertEqual([k['record']['id'] for k in kids], ['t1', 't2'])

    def test_link_attached_to_its_saved_owner_and_unread_relations_stay_unknown(self):
        R = rb.readback(load('h4_linker_document')['route'])
        self.assertEqual([(R['source_links'][j]['href'], R['source_links'][j]['destination']['status']) for j in node(R, 'u1')['attached']['source_links']], [('#tbl', 'none')])
        self.assertTrue(any(u['family'] == 'source_relations' for u in R['unknowns']))

    def test_image_without_an_input_record_says_so(self):
        self.assertEqual(node(rb.readback(load('h4_linker_document')['route']), 'u4')['asset'], {'status': 'no_input_record'})

    def test_xml_matches_the_independent_reading_and_keeps_provenance(self):
        o = oracle()
        for name in ('x1_structure', 'x2_qname_value'):
            with self.subTest(name):
                f = load(name); E = f['route']; R = rb.readback(E)
                self.assertEqual(norm(tuples(R)), norm(o(f['raw'].encode()))); self.assertEqual(rb.preserved(E, R), [])
                self.assertEqual(rb.canon(rb._xml_records(R['xml']['elements'])), rb.canon(E['xml_elements']))  # anchors and parents recovered


class B_ChangedE(unittest.TestCase):
    def test_a_removed_cell_is_kept_removed_and_truth_sees_it(self):
        E1 = load('h1_two_levels')['route']; E1['units'][2]['cells'] = E1['units'][2]['cells'][:1]; R1 = rb.readback(E1)
        self.assertTrue(ok(E1, R1)); self.assertNotEqual(shape(R1['sequence']), H1)

    def test_a_same_coordinate_extra_cell_survives_and_truth_sees_it(self):
        E1 = load('h2_repeated_siblings')['route']; E1['units'][1]['cells'].append(copy.deepcopy(E1['units'][1]['cells'][0])); R1 = rb.readback(E1)
        self.assertEqual(len(node(R1, 't1')['cells']), 3); self.assertTrue(ok(E1, R1)); self.assertNotEqual(shape(R1['sequence']), H2)

    def test_two_null_caption_identities_never_match_and_the_saved_order_is_represented(self):
        # M2 v11 CHANGED expectation (TEST_DIFF_vs_v10.txt): saved order is now carried by ordinals, so this case round-trips exactly. Before (v10): the unattached caption's saved place lies inside the parent table's nested range, which this
        # containment cannot represent; v1 passed it silently, v2 must report it (readback unknown 'order' and a boundary failure).
        E1 = load('h3_child_caption')['route']
        for u in E1['units']: u['source_table'] = None
        R1 = rb.readback(E1)
        self.assertTrue(any(u['family'] == 'caption' for u in R1['unknowns'])); self.assertFalse(any(u['family'] == 'order' for u in R1['unknowns']))
        self.assertTrue(ok(E1, R1)); self.assertEqual(rb.canon(rb.inverse(R1)), rb.canon(E1))

    def test_list_membership_applies_to_every_member_kind(self):
        E1 = load('h4_linker_document')['route']; E1['units'][2]['lists'] = [{'list': 0, 'ordered': False, 'item': 0}]; R1 = rb.readback(E1)
        self.assertEqual(shape(R1['sequence'])[2][0], 'list'); self.assertEqual(shape(R1['sequence'])[2][1][0][0][0], 'table'); self.assertTrue(ok(E1, R1))

    def test_broken_holder_reference_stays_explicit(self):
        E1 = load('h1_two_levels')['route']; E1['units'][1]['cell']['table'] = 'nope'; R1 = rb.readback(E1)
        self.assertIn('t1', [n['record']['id'] for n in R1['sequence']]); self.assertEqual(node(R1, 't1')['holder'], 'unresolved')
        self.assertTrue(any(u['family'] == 'nesting' for u in R1['unknowns'])); self.assertTrue(ok(E1, R1))

    def test_inconsistent_holder_keeps_its_unknown_and_the_saved_order_is_represented(self):
        # M2 v11 CHANGED expectation (TEST_DIFF_vs_v10.txt): the nesting unknown stays; saved order is carried by ordinals. Before (v10): t1 stays unattached but t2 nests inside t0, so saved order t0,t1,t2 cannot be represented.
        E1 = load('h2_repeated_siblings')['route']; E1['units'][1]['cell']['byte_start'] = 0; R1 = rb.readback(E1)
        self.assertTrue(any(u['family'] == 'nesting' for u in R1['unknowns'])); self.assertFalse(any(u['family'] == 'order' for u in R1['unknowns']))
        self.assertTrue(ok(E1, R1)); self.assertEqual(rb.canon(rb.inverse(R1)), rb.canon(E1))

    def test_a_holder_loop_stays_unresolved_and_loses_no_unit(self):
        E1 = load('h1_two_levels')['route']; t1, t2 = E1['units'][1], E1['units'][2]
        t1['cell'] = dict(t2['cell'], table='t2', r=0, c=1, byte_start=t2['cells'][1]['source']['byte_start'], byte_end_exclusive=t2['cells'][1]['source']['byte_end_exclusive'])
        t2['cells'][1]['tables'] = ['t1']; R1 = rb.readback(E1); json.dumps(R1)
        self.assertTrue(any(u['why'] == 'holder references form a loop' for u in R1['unknowns'])); self.assertTrue(ok(E1, R1))

    def test_xml_binding_change_is_kept_and_truth_sees_it(self):
        f = load('x2_qname_value'); E1 = f['route']; E1['xml_elements'][0]['namespaces'] = {'p': 'urn:BBB'}; R1 = rb.readback(E1)
        self.assertTrue(ok(E1, R1)); self.assertNotEqual(norm(tuples(R1)), norm(oracle()(f['raw'].encode())))

    def test_xml_graph_prerequisites_keep_the_saved_records_as_unrepresented(self):
        cases = {'duplicate': lambda els: els[2]['anchor'].update(byte_start=els[1]['anchor']['byte_start']),
                 'dangling': lambda els: els[0]['content'].append({'child': 10 ** 9}),
                 'disconnected cycle': lambda els: els.extend([{'name': 'a', 'parent': 10 ** 6 + 1, 'anchor': {'byte_start': 10 ** 6}, 'content': [{'child': 10 ** 6 + 1}]},
                                                               {'name': 'b', 'parent': 10 ** 6, 'anchor': {'byte_start': 10 ** 6 + 1}, 'content': [{'child': 10 ** 6}]}])}
        for name, damage in cases.items():
            with self.subTest(name):
                E1 = load('x1_structure')['route']; damage(E1['xml_elements']); R1 = rb.readback(E1)
                self.assertIsNone(R1['xml']['elements']); self.assertTrue(any(u['family'] == 'xml_elements' for u in R1['unknowns']))
                self.assertEqual(R1['not_composed']['xml_elements'], E1['xml_elements']); self.assertTrue(ok(E1, R1))

    def test_assets_are_read_only_through_the_archive(self):
        data = b'\x89PNG public control bytes'; S = hashlib.sha256(data).hexdigest()
        good, empty, bad = RUN / 'prepared_ok', RUN / 'prepared_empty', RUN / 'prepared_bad'
        self.assertEqual(archive.store_blob(good, data), S); empty.mkdir(); bad.mkdir(); (bad / f'{S}.gz').write_bytes(gzip.compress(b'other bytes'))
        inp = {'member_sha256': S, 'input_sha256': S, 'how': 'member'}
        for prepared, i, want in ((good, inp, 'ok'), (empty, inp, 'missing'), (bad, inp, 'hash_mismatch'), (good, {'error': 'not a member of the package'}, 'error'), (None, inp, 'not_checked')):
            with self.subTest(want):
                E1 = load('h4_linker_document')['route']; E1['units'][4]['input'] = i; R1 = rb.readback(E1, prepared)
                self.assertEqual(node(R1, 'u4')['asset']['status'], want); self.assertEqual(rb.preserved(E1, R1), []); self.assertEqual(rb.annotations(E1, R1, prepared), [])

    def test_cli_binds_route_and_completion_and_refuses_a_mismatch(self):
        route = load('h4_linker_document')['route']; body = json.dumps(route).encode()
        for name, pin in (('attempt_ok', hashlib.sha256(body).hexdigest()), ('attempt_bad', '0' * 64)):
            a = RUN / name; a.mkdir(); (a / 'ROUTE.json').write_bytes(body)
            (a / 'COMPLETE.json').write_text(json.dumps({'file_id': route['file_id'], 'source_sha256': route['sha256'], 'route_sha256': pin, 'native_status': route['status'], 'prepared_input_sha256': [], 'reader_called': False}))
            if name == 'attempt_ok':
                rb.main([str(a), str(RUN / 'R_ok.json')]); R = json.loads((RUN / 'R_ok.json').read_text())
                self.assertEqual((R['custody']['route_sha256'], R['custody']['raw_reading_sha256']), (pin, None)); self.assertEqual(rb.preserved(route, R), [])
            else:
                with self.assertRaises(ValueError): rb.main([str(a), str(RUN / 'R_bad.json')])


class D_Version2(unittest.TestCase):
    def test_xml_field_units_are_carried_with_an_explicit_unknown(self):
        for name in ('x1_structure', 'x2_qname_value'):
            with self.subTest(name):
                E = load(name)['route']; R = rb.readback(E)
                self.assertNotIn('fields', R['xml']); self.assertEqual(R['not_composed']['units'], E['units'])
                self.assertTrue(any(u['family'] == 'units' for u in R['unknowns'])); self.assertEqual(rb.preserved(E, R), [])

    def test_verify_reports_preservation_unrepresented_and_annotations_separately(self):
        E = load('h4_linker_document')['route']; body = json.dumps(E).encode(); a = RUN / 'verify_attempt'; a.mkdir(); (a / 'ROUTE.json').write_bytes(body)
        (a / 'COMPLETE.json').write_text(json.dumps({'file_id': E['file_id'], 'source_sha256': E['sha256'], 'route_sha256': hashlib.sha256(body).hexdigest(), 'native_status': E['status'], 'prepared_input_sha256': [], 'reader_called': False}))  # v4 fixture correction
        rb.main([str(a), str(a / 'R.json')]); v = rb.verify(a, a / 'R.json')
        self.assertEqual((v['preserved'], v['annotations']), ([], [])); self.assertIn('source_relations', v['unrepresented'])


class C_DamagedR(unittest.TestCase):
    def test_every_damage_class_fails_the_one_boundary(self):
        E1, E3, E4, X = (load(n)['route'] for n in ('h1_two_levels', 'h3_child_caption', 'h4_linker_document', 'x1_structure'))
        R1, R3, R4, RX = rb.readback(E1), rb.readback(E3), rb.readback(E4), rb.readback(X)
        def d(R, f): R = copy.deepcopy(R); f(R); return R
        lst = lambda R: next(n for n in R['sequence'] if 'record' not in n)
        damages = {
            'missing child': (E1, d(R1, lambda R: [c for c in node(R, 't1')['cells'] if c.get('children')][0].update(children=[]))),
            'duplicate cell': (E1, d(R1, lambda R: node(R, 't0')['cells'].append(copy.deepcopy(node(R, 't0')['cells'][0])))),
            'altered text': (E1, d(R1, lambda R: node(R, 't0')['cells'][1]['record'].update(text='1O'))),
            'bool for int': (E1, d(R1, lambda R: node(R, 't0')['cells'][1]['record'].update(rs=True))),
            'absent instead of null-free key': (E1, d(R1, lambda R: node(R, 't0')['cells'][1]['record'].pop('header'))),
            'swapped cells': (E1, d(R1, lambda R: node(R, 't0')['cells'].reverse())),
            'child moved to another cell': (E1, d(R1, lambda R: (lambda cs: (cs[0].update(children=cs[1]['children']), cs[1].pop('children')))(node(R, 't1')['cells']))),
            'extra key in a node': (E1, d(R1, lambda R: node(R, 't2').update(note='x'))),
            'record states its own cells': (E1, d(R1, lambda R: node(R, 't2')['record'].update(cells=[]))),
            'caption moved to another table': (E3, d(R3, lambda R: node(R, 't0').update(captions=node(R, 't2').pop('captions')))),
            'caption position flipped': (E3, d(R3, lambda R: node(R, 't2')['captions'][0].update(position='after'))),
            'swapped units': (E4, d(R4, lambda R: R['sequence'].reverse())),
            'missing picture': (E4, d(R4, lambda R: R.update(sequence=[n for n in R['sequence'] if 'record' not in n or n['record'].get('kind') != 'image']))),
            'missing list member': (E4, d(R4, lambda R: lst(R)['items'][0].update(members=[]))),
            'list type flipped': (E4, d(R4, lambda R: lst(R).update(ordered=True))),
            'list membership dropped': (E4, d(R4, lambda R: R['sequence'].__setitem__(R['sequence'].index(lst(R)), lst(R)['items'][0]['members'][0]))),
            'missing link attachment': (E4, d(R4, lambda R: node(R, 'u1').pop('attached'))),
            'link moved to another owner': (E4, d(R4, lambda R: node(R, 'u0').update(attached=node(R, 'u1').pop('attached')))),
            'duplicated link attachment': (E4, d(R4, lambda R: node(R, 'u1')['attached']['source_links'].append(0))),
            'link record altered': (E4, d(R4, lambda R: R['source_links'][0].update(href='#other'))),
            'unrepresented family altered': (E4, d(R4, lambda R: R['not_composed']['source_relations'].update(read=True))),
            'identity altered': (E4, d(R4, lambda R: R['identity'].update(file_id='other'))),
            'extra top-level key': (E4, d(R4, lambda R: R.update(note='x'))),
            'xml attribute': (X, d(RX, lambda R: R['xml']['elements'][0]['attributes'].update(x='A and B'))),
            'xml bindings dropped': (X, d(RX, lambda R: R['xml']['elements'][0].update(namespaces={}))),
            'xml anchor lost': (X, d(RX, lambda R: R['xml']['elements'][0].pop('anchor'))),
            'xml node states its parent': (X, d(RX, lambda R: R['xml']['elements'][0].update(parent=None))),
            'xml children swapped': (X, d(RX, lambda R: (lambda c: c.reverse())(R['xml']['elements'][0]['content']))),
            'xml field text': (X, d(RX, lambda R: R['not_composed']['units'][0].update(text='-5'))),  # v2: XML field units are carry-through
            'xml field identity': (X, d(RX, lambda R: R['not_composed']['units'][0].update(id='another'))),
        }
        for name, (E, R) in damages.items():
            with self.subTest(name): self.assertNotEqual(rb.preserved(E, R), [])

    def test_annotation_damage_fails_the_reproducibility_check_only(self):
        E = load('h4_linker_document')['route']; R = rb.readback(E)
        for name, f in (('asset', lambda R: node(R, 'u4').update(asset={'status': 'ok'})), ('unknown dropped', lambda R: R.update(unknowns=[])),
                        ('asset status free text', lambda R: node(R, 'u4').update(asset={'status': 'fine'})), ('asset extra key', lambda R: node(R, 'u4')['asset'].update(text='x.jpg')),
                        ('asset on a non-image unit', lambda R: node(R, 'u0').update(asset={'status': 'ok'})), ('unknown entry extra key', lambda R: R['unknowns'][0].update(text='x')),
                        ('aggregate', None)):
            if f is None:
                E1 = load('h1_two_levels')['route']; R1 = copy.deepcopy(rb.readback(E1)); next(c for c in node(R1, 't0')['cells'] if c.get('children')).pop('aggregate')
                with self.subTest(name): self.assertEqual(rb.preserved(E1, R1), []); self.assertNotEqual(rb.annotations(E1, R1), [])
                continue
            D = copy.deepcopy(R); f(D)
            with self.subTest(name): self.assertEqual(rb.preserved(E, D), []); self.assertNotEqual(rb.annotations(E, D), [])


class E_Custody(unittest.TestCase):
    """v3: one custody gate shared by main and verify; custody shape in preserved; custody is verify's own fourth result."""
    def attempt(self, name, complete=None, route_from=None):
        E = load('h4_linker_document')['route']; body = json.dumps(E).encode(); a = RUN / name; a.mkdir(); (a / 'ROUTE.json').write_bytes(body); (a / 'prepared').mkdir()
        good = {'file_id': E['file_id'], 'source_sha256': E['sha256'], 'route_sha256': hashlib.sha256(body).hexdigest(), 'native_status': E['status'], 'prepared_input_sha256': [], 'reader_called': False}  # v4 fixture correction
        if complete != 'absent': (a / 'COMPLETE.json').write_text(json.dumps(good if complete is None else dict(good, **complete)))
        return E, a

    def test_a_faithful_attempt_passes_all_four_results(self):
        E, a = self.attempt('c_ok'); rb.main([str(a), str(a / 'R.json')]); v = rb.verify(a, a / 'R.json')
        self.assertEqual((v['custody'], v['preserved'], v['annotations']), ([], [], [])); self.assertIn('source_relations', v['unrepresented'])

    def test_custody_payload_or_types_fail_preserved(self):
        E, a = self.attempt('c_shape'); rb.main([str(a), str(a / 'R.json')]); R = json.loads((a / 'R.json').read_text())
        for name, c in (('fabricated key', dict(R['custody'], zz='x')), ('E.units copied into custody', dict(R['custody'], units=E['units'])), ('a string', 'free text'),
                        ('wrong JSON types', dict(R['custody'], prepared=1, route_sha256=None))):
            with self.subTest(name): self.assertNotEqual(rb.preserved(E, dict(R, custody=c)), [])

    def test_forged_or_mismatched_custody_fails_verify(self):
        E, a = self.attempt('c_base'); rb.main([str(a), str(a / 'R.json')]); R0 = json.loads((a / 'R.json').read_text())
        forged = {'route_sha256 forged': lambda R: R['custody'].update(route_sha256='0' * 64), 'complete_sha256 forged': lambda R: R['custody'].update(complete_sha256='0' * 64),
                  'prepared flipped': lambda R: R['custody'].update(prepared=False), 'raw_reading claimed': lambda R: R['custody'].update(raw_reading_sha256='a' * 64),
                  'custody removed': lambda R: R.pop('custody')}
        for name, f in forged.items():
            with self.subTest(name):
                R = copy.deepcopy(R0); f(R); out = RUN / f'c_R_{name.replace(" ", "_")}.json'; out.write_text(json.dumps(R))
                self.assertNotEqual(rb.verify(a, out)['custody'], [])
        for name, complete in (('reader_called true after readback', {'reader_called': True}), ('completion missing', 'absent'), ('completion names another route', {'route_sha256': '1' * 64})):
            with self.subTest(name):
                _, b = self.attempt('c_' + name.replace(' ', '_'), complete)  # the same route, a different completion than the readback was made from
                self.assertNotEqual(rb.verify(b, a / 'R.json')['custody'], [])


class F_InputContract(unittest.TestCase):
    """v4: the complete producer COMPLETE contract at the one custody gate, on native-shaped copies of a real public attempt."""
    def attempt(self, name, complete=None, route=None, prepared='copy', receipt='copy'):
        a = RUN / name; a.mkdir(); body = (PUBLIC_ATTEMPT / 'ROUTE.json').read_bytes() if route is None else json.dumps(route).encode()
        (a / 'ROUTE.json').write_bytes(body)
        c = json.loads((PUBLIC_ATTEMPT / 'COMPLETE.json').read_bytes()); c['route_sha256'] = hashlib.sha256(body).hexdigest()
        (a / 'COMPLETE.json').write_text(json.dumps(c if complete is None else complete(c)))
        if prepared == 'copy': shutil.copytree(PUBLIC_ATTEMPT / 'prepared', a / 'prepared')
        elif prepared == 'file': (a / 'prepared').write_bytes(b'not a directory')
        elif prepared == 'empty': (a / 'prepared').mkdir()
        if receipt == 'copy': shutil.copy(PUBLIC_ATTEMPT / 'RAW_READING.json', a / 'RAW_READING.json'); shutil.copytree(PUBLIC_ATTEMPT / 'raw_reading', a / 'raw_reading')
        elif receipt == 'altered': (a / 'RAW_READING.json').write_bytes((PUBLIC_ATTEMPT / 'RAW_READING.json').read_bytes() + b' '); shutil.copytree(PUBLIC_ATTEMPT / 'raw_reading', a / 'raw_reading')
        elif receipt == 'no_blob': shutil.copy(PUBLIC_ATTEMPT / 'RAW_READING.json', a / 'RAW_READING.json'); (a / 'raw_reading').mkdir()
        return a

    def check(self, a):
        try: rb.main([str(a), str(a / 'R.json')]); main_ok = True
        except ValueError: main_ok = False
        return main_ok, rb.verify(a, a / 'R.json')['custody'] if main_ok else None

    def test_the_native_shaped_public_attempt_passes(self):
        a = self.attempt('ic_faithful'); main_ok, custody = self.check(a)
        self.assertTrue(main_ok); self.assertEqual(custody, [])
        v = rb.verify(a, a / 'R.json'); self.assertEqual((v['preserved'], v['annotations']), ([], []))

    def test_a_consistent_partial_route_is_not_rejected_for_its_status(self):
        route = json.loads((PUBLIC_ATTEMPT / 'ROUTE.json').read_bytes()); route['status'] = 'PARTIAL'
        a = self.attempt('ic_partial', complete=lambda c: dict(c, native_status='PARTIAL'), route=route); main_ok, custody = self.check(a)
        self.assertTrue(main_ok); self.assertEqual(custody, [])
        self.assertTrue(any(u['family'] == 'status' for u in json.loads((a / 'R.json').read_text())['unknowns']))

    def test_every_contradicting_attempt_is_refused_at_the_gate(self):
        pin = json.loads((PUBLIC_ATTEMPT / 'COMPLETE.json').read_bytes())['prepared_input_sha256'][0]
        cases = {'native_status contradicts the route': dict(complete=lambda c: dict(c, native_status='FAILED')),
                 'declared prepared input missing': dict(prepared='empty'),
                 'prepared is a regular file': dict(prepared='file'),
                 'declared pins differ from the route inputs': dict(complete=lambda c: dict(c, prepared_input_sha256=sorted([pin, 'f' * 64]))),
                 'declared pins repeated': dict(complete=lambda c: dict(c, prepared_input_sha256=[pin, pin])),
                 'completion missing a producer field': dict(complete=lambda c: {k: v for k, v in c.items() if k != 'native_status'}),
                 'completion with an extra field': dict(complete=lambda c: dict(c, extra=1)),
                 'raw reading receipt altered': dict(receipt='altered'),
                 'raw reading blob missing': dict(receipt='no_blob'),
                 'raw reading claimed but receipt absent': dict(receipt='absent'),
                 'one raw pin without the other': dict(complete=lambda c: dict(c, raw_reading_receipt_sha256=None))}
        for name, kw in cases.items():
            with self.subTest(name):
                main_ok, _ = self.check(self.attempt('ic_' + name.replace(' ', '_'), **kw)); self.assertFalse(main_ok)

    def test_a_recipe_v1_or_v3_completion_without_raw_keys_passes(self):
        a = self.attempt('ic_v3_shape', complete=lambda c: {k: v for k, v in c.items() if k not in ('raw_reading_sha256', 'raw_reading_receipt_sha256')}, receipt='absent')
        main_ok, custody = self.check(a); self.assertTrue(main_ok); self.assertEqual(custody, [])

    def test_source_fields_named_like_annotations_stay_body(self):
        E = load('h4_linker_document')['route']; E['units'][0].update(asset={'status': 'ok'}, holder='unresolved', aggregate='unresolved', position='before')
        R = rb.readback(E); self.assertEqual((rb.preserved(E, R), rb.annotations(E, R)), ([], []))
        node(R, 'u0')['record']['asset'] = {'status': 'missing'}; self.assertNotEqual(rb.preserved(E, R), [])



class G_SavedOrder(unittest.TestCase):
    """M2: the real containment failure (AMG: images saved before their holder tables), from a small source-grounded saved route."""
    def setUp(self):
        self.E = load('amg_image_before_holder')['route']; self.R = rb.readback(self.E)

    def test_round_trip_keeps_saved_and_composed_order(self):
        E, R = self.E, self.R
        self.assertTrue(ok(E, R)); self.assertEqual(rb.canon(rb.inverse(R)), rb.canon(E))
        ords = [n['ordinal'] for n in flat(R)]; self.assertNotEqual(ords, sorted(ords))  # composed body order differs from saved order; both are carried
        self.assertFalse(any(u.get('family') == 'order' for u in R['unknowns']))

    def test_swap_with_ordinals_fails_although_sorting_would_restore(self):  # the crucial false-pass control
        E, R = self.E, self.R; s = R['sequence']; i, j = [k for k, n in enumerate(s) if 'record' in n][:2]; s[i], s[j] = s[j], s[i]
        self.assertEqual(rb.canon(rb.inverse(R)), rb.canon(E)); self.assertTrue(bad(E, R))

    def test_child_moved_to_root_or_another_cell_fails(self):
        E, R = self.E, self.R
        D = copy.deepcopy(R); h = [c for n in top(D) for c in n.get('cells', []) if c.get('children')]; self.assertEqual(len(h), 2)
        kid = h[0]['children'].pop(); h[0].pop('children'); D['sequence'].append(kid); self.assertTrue(bad(E, D))
        D = copy.deepcopy(R); h = [c for n in top(D) for c in n.get('cells', []) if c.get('children')]; h[1]['children'] += h[0].pop('children'); self.assertTrue(bad(E, D))


class Ordinals(unittest.TestCase):
    def setUp(self):
        self.E = load('h4_linker_document')['route']; self.R = rb.readback(self.E)

    def test_positive_and_schema(self):
        self.assertTrue(ok(self.E, self.R)); self.assertEqual(self.R['readback_schema'], 'fable-readback/11')
        self.assertTrue(all(type(n['ordinal']) is int for n in flat(self.R)))

    def test_ordinal_damage_fails(self):
        cases = {'duplicate': lambda ns: ns[1].update(ordinal=ns[0]['ordinal']), 'missing': lambda ns: ns[1].pop('ordinal'),
                 'out of range': lambda ns: ns[1].update(ordinal=len(ns)), 'negative': lambda ns: ns[0].update(ordinal=-1),
                 'bool': lambda ns: ns[1].update(ordinal=True), 'float': lambda ns: ns[1].update(ordinal=1.0), 'string': lambda ns: ns[1].update(ordinal='1'),
                 'ordinals swapped only': lambda ns: (lambda a, b: (ns[0].update(ordinal=b), ns[1].update(ordinal=a)))(ns[0]['ordinal'], ns[1]['ordinal'])}
        for name, f in cases.items():
            with self.subTest(name):
                D = copy.deepcopy(self.R); f(flat(D)); self.assertTrue(bad(self.E, D))

    def test_records_swapped_alone_fail(self):
        D = copy.deepcopy(self.R); a, b = top(D)[:2]; a['record'], b['record'] = b['record'], a['record']; self.assertTrue(bad(self.E, D))

    def test_top_level_swap_with_ordinals_fails(self):
        D = copy.deepcopy(self.R); s = D['sequence']; s[0], s[1] = s[1], s[0]
        self.assertEqual(rb.canon(rb.inverse(D)), rb.canon(self.E)); self.assertTrue(bad(self.E, D))

    def test_missing_and_extra_records_fail(self):
        D = copy.deepcopy(self.R); D['sequence'].pop(0); self.assertTrue(bad(self.E, D))
        D = copy.deepcopy(self.R); D['sequence'].append(copy.deepcopy(D['sequence'][0])); self.assertTrue(bad(self.E, D))


class Containment(unittest.TestCase):
    def test_cell_children_swap_with_ordinals_fails(self):
        E = load('h2_repeated_siblings')['route']; R = rb.readback(E); self.assertTrue(ok(E, R))
        kids = next(c for c in node(R, 't0')['cells'] if c.get('children'))['children']; kids.reverse()
        self.assertEqual(rb.canon(rb.inverse(R)), rb.canon(E)); self.assertTrue(bad(E, R))

    def test_nested_tables_keep_order_and_reject_changed_child(self):
        E = load('h1_two_levels')['route']; R = rb.readback(E); self.assertTrue(ok(E, R))
        D = copy.deepcopy(R); node(D, 't2')['cells'][0]['record']['text'] = 'other'; self.assertTrue(bad(E, D))
        D = copy.deepcopy(R); a, b = node(D, 't1'), node(D, 't2'); a['ordinal'], b['ordinal'] = b['ordinal'], a['ordinal']; self.assertTrue(bad(E, D))

    def test_captions_before_and_after_by_original_ordinal(self):
        base = load('h3_child_caption')['route']; cap = next(i for i, u in enumerate(base['units']) if u.get('kind') == 'caption')
        hold = next(i for i, u in enumerate(base['units']) if u.get('kind') == 'table' and u.get('source_table') == base['units'][cap]['source_table'])
        for side in ('before', 'after'):
            with self.subTest(side):
                E = copy.deepcopy(base); us = E['units']; c = us.pop(cap); h = us.index(base['units'][hold]); us.insert(h if side == 'before' else h + 1, c)
                R = rb.readback(E); self.assertTrue(ok(E, R)); n = next(x for x in flat(R) if x['record'].get('kind') == 'caption'); self.assertEqual(n['position'], side)
                D = copy.deepcopy(R); next(x for x in flat(D) if x['record'].get('kind') == 'caption')['position'] = 'after' if side == 'before' else 'before'
                self.assertEqual(rb.canon(rb.inverse(D)), rb.canon(E)); self.assertTrue(bad(E, D))  # the label alone is wrong: only the original-ordinal side check sees it

    def test_list_items_and_groups_reordered_fail(self):
        E = load('h4_linker_document')['route']
        for k in (0, 1): E['units'][k]['lists'] = [{'list': 7, 'ordered': True, 'item': k}]
        R = rb.readback(E); self.assertTrue(ok(E, R))
        lst = next(n for n in R['sequence'] if 'record' not in n and n.get('list') == 7)
        D = copy.deepcopy(R); l = next(n for n in D['sequence'] if 'record' not in n and n.get('list') == 7); l['items'].reverse(); self.assertTrue(bad(E, D))
        D = copy.deepcopy(R); s = D['sequence']; i = s.index(next(n for n in s if 'record' not in n and n.get('list') == 7)); s[i], s[i + 1] = s[i + 1], s[i]; self.assertTrue(bad(E, D))
        self.assertTrue(lst)

    def test_xml_unchanged(self):
        for name in ('x1_structure', 'x2_qname_value'):
            with self.subTest(name):
                E = load(name)['route']; R = rb.readback(E); self.assertTrue(ok(E, R)); self.assertNotIn('sequence', R)



if __name__ == '__main__':
    unittest.main(verbosity=1)
