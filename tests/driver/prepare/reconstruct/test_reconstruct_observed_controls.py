"""Permanent reconstruction controls for `observed_controls` (OBSERVED_CONTROLS_CONTRACT v2; Root CONTEXT_LABEL_RECONSTRUCTION_SPLIT_20261022,
CONTEXT_OBSERVED_CONTROL_CONTRACT_REVIEW_20261022, CONTEXT_OCCURRENCE_CONTRACT_RECONCILIATION_20261022, CONTEXT_FINAL_NATIVE_OBSERVATION_CONTRACT_20261022).
Ported unchanged in logic and answers from the candidate suite (unittest, run from the repository root). Expectations come from the saved route's own
unit text slices and from the saved native render record (CONTEXT_RENDERS.json), never from re-running the composer on itself; every tamper control
changes one thing in R or in the saved records and expects the checker to say so. Three retained external dependencies are bound through the normal
hash-pinned fixture store (fixtures/observed_controls_manifest.json, PREPARE_TEST_DATA): Root's six ownership cases, the old saved label failure
(label_slice_run3 routes) and the new saved 01:18 state folders; a missing store fails, never skips. Smart, 2026-10-22."""
import copy, hashlib, json, os, tempfile, unittest
from pathlib import Path

from driver.prepare import reconstruct as rb
from driver.prepare.get import archive
from tests.driver.prepare.support import FixtureStore

STORE = FixtureStore(Path(__file__).with_name('fixtures') / 'observed_controls_manifest.json')


def saved_run(root):
    """The saved 01:18 run's folders (initial + states) rebuilt exactly from the pinned fixture bytes under `root`: the files reconstruct and verify read (routes, completions, render records, raw readings and prepared inputs)."""
    ids = STORE.members('saved_state_graph_0118'); labels = sorted({i.split('/')[1] for i in ids}); attempt = root / 'attempt_0'
    for lab in labels:
        d = attempt if lab == 'initial' else attempt / 'states' / lab; d.mkdir(parents=True, exist_ok=True)
        for i in ids:
            parts = i.split('/')
            if parts[1] != lab: continue
            if parts[2] in ('raw_reading', 'prepared'): archive.store_blob(d / parts[2], STORE.read(i))  # native blob archives rebuilt by the native owner
            else: STORE.materialize(i, d / parts[2])
    return attempt
canon = rb.canon
CAP, DOC = 'ab' * 32, 'cd' * 32
def span(a, b): return [{'byte_start': a, 'byte_end_exclusive': b}]
def link(tag0, tag1, end, owners): return {'tag': {'byte_start': tag0, 'byte_end_exclusive': tag1}, 'extent': {'byte_start': tag1, 'byte_end_exclusive': end}, 'href': 'javascript:void(0)', 'destination': {'kind': 'as_written'}, 'certain': True, 'owners': owners, 'owners_by': 'action'}
def record(control, extent, owners, before, after, controls=(60, 80), index=1, state='activated@60+80', occurrences=None, **over):
    occ = occurrences if occurrences is not None else [{'action_index': index, 'before': before, 'after': after, 'shown': True}]  # the producer's contract: every label-changing occurrence in action order; first before = original, final after/shown = observed
    r = {'control': control, 'extent': {'byte_start': extent[0], 'byte_end_exclusive': extent[1]}, 'state': state, 'status': 'complete', 'reasons': [], 'owners': owners, 'owners_by': 'action',
         'original': {'label': before}, 'observed': {'label': after, 'shown': True, 'by': 'action: native textContent after it'},
         'lineage': {'controls': list(controls), 'action_index': index, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': occ}}
    r.update(over); return r
def route(records=None, controls=(60, 80), state='activated@60+80'):
    """A saved contextual state route in its final saved shape: four units (a paragraph holding a control label with words around it, a paragraph of the
    same words outside any control, a table whose cell holds a control label, a short paragraph), the source link records that own them, the context."""
    units = [{'id': 'u1', 'kind': 'text', 'text': 'Notes Open notes here', 'anchor': span(100, 121)},
             {'id': 'u2', 'kind': 'text', 'text': 'Open notes', 'anchor': span(300, 310)},
             {'id': 'u3', 'kind': 'table', 'text': '', 'anchor': span(390, 430), 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Show all rows', 'anchor': span(400, 413), 'source': {'byte_start': 395, 'byte_end_exclusive': 420}}]},
             {'id': 'u4', 'kind': 'text', 'text': 'more', 'anchor': span(500, 504)}]
    links = [link(80, 106, 116, [{'unit': 'u1', 'text_at': [[6, 16]]}]), link(60, 117, 121, [{'unit': 'u1', 'text_at': [[17, 21]]}]), link(380, 400, 408, [{'unit': 'u3', 'cell': 400, 'text_at': [[0, 8]]}]), link(490, 500, 504, [{'unit': 'u1', 'text_at': [[17, 21]]}, {'unit': 'u4', 'text_at': [[0, 4]]}])]  # acted links: owners by action with their owned slices (the producer's _owners)
    E = {'schema': 'prepare-html/test', 'file_id': 'invented/child.html', 'sha256': DOC, 'route': {'name': 'edgartools-html+source-formatting+screen', 'settings': {}}, 'status': 'OK', 'error': None, 'seconds': 1.0,
         'units': units, 'source_links': links, 'page_visibility': {'shown': [], 'hidden': [], 'replaced': [[106, 116]]}, 'resources': {'document': {'path': 'child.html'}, 'context': {'controls': list(controls), 'control_source_link_tag_byte_start': controls[0], 'state': state}}, 'uncovered': []}
    if records is not None: E['observed_controls'] = records
    return E
def ONE(**o):  # state activated@60+80: outer control 60 revealed, then control 80 acted (action index 1); its inner record is the render's first
    r = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Close notes'); r.update(o); return r
def sites(R, family='observed_controls'):  # {unit id or (unit id, cell index): attached record indexes}
    out = {}
    for n, _, _ in rb._units_in_order(R['sequence']):
        if n.get('attached', {}).get(family): out[n['record']['id']] = n['attached'][family]
        for k, c in enumerate(n.get('cells', [])):
            if c.get('attached', {}).get(family): out[(n['record']['id'], k)] = c['attached'][family]
    return out
def inner(control, before, after, shown=True, changed=True): return {'control': control, 'label_before': before, 'label_after': after, 'control_shown_after': shown, 'effects': {'records': [{'where': 'control label'}] if changed else []}}
def renders(state='activated@60+80', before='Open notes', after='Close notes', shown=True, changed=True, control=80, cap=CAP, actions=None, final=None):
    acts = actions if actions is not None else [inner(control, before, after, shown, changed)]  # the render's inner actions, in action order: the tail of the state's control sequence (the outer activation has no inner record)
    last = {a['control']: a for a in acts}; fin = final if final is not None else [{'label': last[c]['label_after'], 'shown': last[c]['control_shown_after']} for c in dict.fromkeys(a['control'] for a in acts)]  # the producer's final_controls: one {label, shown} per acted control in order of first action, read after all actions (by default what each control's last action left)
    return [{'state': 'initial', 'native': {'document_sha256': DOC}}, {'state': state, 'native': {'document_sha256': DOC, 'capture': {'sha256': cap}}, 'inner': acts, 'final_controls': fin}]
def attempt(E, rends, pin=True):
    d = Path(tempfile.mkdtemp()); body = json.dumps(E).encode(); (d / 'ROUTE.json').write_bytes(body)
    complete = {'file_id': E['file_id'], 'source_sha256': E['sha256'], 'route_sha256': hashlib.sha256(body).hexdigest(), 'native_status': E['status'], 'prepared_input_sha256': [], 'reader_called': False}
    if rends is not None:
        rb_ = json.dumps(rends).encode(); (d / 'CONTEXT_RENDERS.json').write_bytes(rb_)
        if pin: complete['context_renders_sha256'] = hashlib.sha256(rb_).hexdigest()  # the caller's finish pins the render evidence (field agreed with Fable)
    (d / 'COMPLETE.json').write_text(json.dumps(complete))
    return d

class Composition(unittest.TestCase):
    def test_initial_route_without_records_reads_back_exactly_as_before(self):
        E = route(); R = rb.readback(E)
        self.assertEqual(R['readback_schema'], 'fable-readback/11'); self.assertNotIn('observed_controls', R); self.assertEqual(set(R), {'readback_schema', 'kind', 'identity', 'unknowns', 'not_composed', 'sequence', 'source_links'})
        self.assertEqual(rb.preserved(E, R), []); self.assertEqual(canon(rb.inverse(R)), canon(E)); self.assertFalse(any(u.get('family') == 'observed_controls' for u in R['unknowns']))
    def test_one_complete_record_attaches_to_its_owner_slices_only(self):
        E = route([ONE()]); R = rb.readback(E)
        self.assertEqual(R['observed_controls'], E['observed_controls']); self.assertEqual(sites(R), {'u1': [0]})  # u2 holds the same words outside the control: untouched
        self.assertEqual(E['units'][0]['text'][6:16], 'Open notes'); self.assertEqual(R['observed_controls'][0]['original']['label'], 'Open notes')  # the slice is the label's source text; the native before-label is kept apart from it
        self.assertEqual(rb.preserved(E, R), []); self.assertEqual(canon(rb.inverse(R)), canon(E)); self.assertEqual([u for u in R['unknowns'] if u.get('family') == 'observed_controls'], [])
        self.assertEqual(rb.inverse(R)['units'][0]['text'], 'Notes Open notes here')  # saved text intact; the view rule replaces the slice, never the record
    def test_two_controls_in_one_unit_compose_independently(self):
        seq, st = (60, 80, 60), 'activated@60+80+60'  # outer 60 revealed, 80 acted, 60 acted again: two controls in one unit, each at its own final occurrence
        one = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Close notes', controls=seq, index=1, state=st); two = record(60, (117, 121), [{'unit': 'u1', 'text_at': [[17, 21]]}], 'here', 'there', controls=seq, index=2, state=st)
        E = route([one, two], controls=seq, state=st); R = rb.readback(E); self.assertEqual(sites(R), {'u1': [0, 1]}); self.assertEqual(rb.preserved(E, R), [])
    def test_overlapping_slices_compose_neither(self):
        seq, st = (60, 80, 60), 'activated@60+80+60'
        one = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Close notes', controls=seq, index=1, state=st); two = record(60, (117, 121), [{'unit': 'u1', 'text_at': [[10, 18]]}], 'here', 'there', controls=seq, index=2, state=st)
        E = route([one, two], controls=seq, state=st); E['source_links'][1]['owners'] = [{'unit': 'u1', 'text_at': [[10, 18]]}]  # the saved link record itself states the crossing interval: two records would own one character
        R = rb.readback(E); self.assertEqual(sites(R), {}); self.assertEqual(sorted(u['record'] for u in R['unknowns'] if u.get('family') == 'observed_controls'), [0, 1]); self.assertEqual(rb.preserved(E, R), [])
    def test_rich_label_split_across_units_and_a_table_cell_owner(self):
        seq, st = (60, 380, 490), 'activated@60+380+490'
        cell = record(380, (400, 408), [{'unit': 'u3', 'cell': 400, 'text_at': [[0, 8]]}], 'Show all', 'Hide all', controls=seq, index=1, state=st); split = record(490, (500, 504), [{'unit': 'u1', 'text_at': [[17, 21]]}, {'unit': 'u4', 'text_at': [[0, 4]]}], 'heremore', 'less', controls=seq, index=2, state=st)
        E = route([cell, split], controls=seq, state=st); R = rb.readback(E); self.assertEqual(sites(R), {('u3', 0): [0], 'u1': [1], 'u4': [1]}); self.assertEqual(rb.preserved(E, R), [])
    def test_incomplete_record_is_listed_and_attached_nowhere(self):
        E = route([ONE(status='incomplete', reasons=['control not shown after the action'])]); R = rb.readback(E)
        self.assertEqual(sites(R), {}); self.assertEqual(R['observed_controls'], E['observed_controls']); self.assertIn({'family': 'observed_controls', 'record': 0, 'why': 'incomplete: control not shown after the action'}, R['unknowns']); self.assertEqual(rb.preserved(E, R), [])
    def test_records_that_do_not_fit_the_saved_route_do_not_compose(self):
        cases = {"extent is not the link record's own extent": ONE(extent={'byte_start': 106, 'byte_end_exclusive': 117}), 'control names no single source link record': ONE(control=81),
                 'an owner range is not a code-point range of its saved final text': ONE(owners=[{'unit': 'u1', 'text_at': [[6, 40]]}]), 'an owner is absent or unresolved': ONE(owners=[{'unit': 'u9', 'text_at': [[0, 4]]}]),
                 "owners differ from the link record's own owned intervals": ONE(owners=[{'unit': 'u2', 'text_at': [[0, 10]]}]), 'lineage controls differ from the route context': ONE(lineage={'controls': [60, 80, 60], 'action_index': 1, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}]}),
                 'state differs from the route context': ONE(state='another-state'), 'complete record with the control not shown': ONE(observed={'label': 'Close notes', 'shown': False, 'by': 'action: native textContent after it'}),
                 'an occurrence does not name the control in the action sequence': ONE(lineage={'controls': [60, 80], 'action_index': 0, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': [{'action_index': 0, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}]}),
                 'record is not the contract shape: lineage.occurrences': ONE(lineage={'controls': [60, 80], 'action_index': 1, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': []}),
                 'occurrences do not chain (a label changed without a recorded occurrence)': ONE(lineage={'controls': [60, 80, 60, 80], 'action_index': 3, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}, {'action_index': 3, 'before': 'Closed', 'after': 'Open notes', 'shown': True}]}, observed={'label': 'Open notes', 'shown': True, 'by': 'action: native textContent after it'}),
                 'action index is not the final recorded occurrence': ONE(lineage={'controls': [60, 80, 60, 80], 'action_index': 1, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}, {'action_index': 3, 'before': 'Close notes', 'after': 'Open notes', 'shown': True}]}),
                 "original label is not the first occurrence's label before the action": ONE(original={'label': 'Opened notes'}), 'observed label is not the last recorded change': ONE(observed={'label': 'Closed notes', 'shown': True, 'by': 'action: native textContent after it'}),
                 "owned intervals: wrong slice in the same unit": ONE(owners=[{'unit': 'u1', 'text_at': [[0, 5]]}]), "owned intervals: only part of the owned label": ONE(owners=[{'unit': 'u1', 'text_at': [[6, 10]]}]),
                 "owned intervals: an extra owner": ONE(owners=[{'unit': 'u1', 'text_at': [[6, 16]]}, {'unit': 'u4', 'text_at': [[0, 4]]}]), "owned intervals: an omitted owner": ONE(owners=[]),
                 'record is not the contract shape: owners_by': ONE(owners_by='text'),
                 'record is not the contract shape: reasons': ONE(reasons=['x']), 'record is not the contract shape: lineage': ONE(lineage={'controls': [60, 80], 'action_index': 1, 'render': 1, 'state_capture_sha256': None, 'occurrences': [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}]})}
        for why, rec in cases.items():
            with self.subTest(why=why):
                E = route([rec])
                if why in ('an owner range is not a code-point range of its saved final text', 'an owner is absent or unresolved'): E['source_links'][0]['owners'] = rec['owners']  # the saved link record states the same bad owner: the slice check itself must refuse
                R = rb.readback(E); self.assertEqual(sites(R), {}, why)
                expect = why if not why.startswith('owned intervals') else ("owners differ from the link record's own owned intervals" if rec['owners'] else 'record is not the contract shape: owners')  # omitted, reordered, extra or other slices: one class
                self.assertIn({'family': 'observed_controls', 'record': 0, 'why': expect}, R['unknowns']); self.assertEqual(rb.preserved(E, R), [])
        seq, st = (60, 490), 'activated@60+490'; reordered = record(490, (500, 504), [{'unit': 'u4', 'text_at': [[0, 4]]}, {'unit': 'u1', 'text_at': [[17, 21]]}], 'heremore', 'less', controls=seq, index=1, state=st)
        E = route([reordered], controls=seq, state=st); R = rb.readback(E); self.assertEqual(sites(R), {}); self.assertIn({'family': 'observed_controls', 'record': 0, 'why': "owners differ from the link record's own owned intervals"}, R['unknowns'])

class RepeatedControl(unittest.TestCase):
    """A control acted more than once in one state (reveal, another control, the first again): the record keeps the first native before-label as
    original, every label-changing occurrence in action order, and the final label/visibility as observed; a reverse action may return to the source label."""
    SEQ, ST = (60, 80, 60), 'activated@60+80+60'  # inner actions in order: [80, 60]; control 60's label changes at index 2 (its outer activation, index 0, has no inner record)
    def acts(self, order=(80, 60), final='Open panel'): return [inner(80, 'Open notes', 'Close notes') if c == 80 else inner(60, 'Close panel', final) for c in order]
    def rec60(self, after='Open panel', **o): return record(60, (117, 121), [{'unit': 'u1', 'text_at': [[17, 21]]}], 'Close panel', after, controls=self.SEQ, index=2, state=self.ST, **o)
    def test_final_occurrence_composes_and_binds_to_its_own_native_action(self):
        E = route([self.rec60()], controls=self.SEQ, state=self.ST); R = rb.readback(E); self.assertEqual(sites(R), {'u1': [0]}); self.assertEqual(rb.preserved(E, R), [])
        d = attempt(E, renders(state=self.ST, actions=self.acts())); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json')); self.assertEqual((v['custody'], v['preserved'], v['observed']), ([], [], []))
    def test_two_occurrences_of_one_control_return_to_the_source_label_and_compose(self):
        seq, st = (60, 80, 60, 80), 'activated@60+80+60+80'; occ = [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}, {'action_index': 3, 'before': 'Close notes', 'after': 'Open notes', 'shown': True}]
        rec = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Open notes', controls=seq, index=3, state=st, occurrences=occ)  # final label equals the source label: a real reverse, still a record of two native changes
        E = route([rec], controls=seq, state=st); R = rb.readback(E); self.assertEqual(sites(R), {'u1': [0]}); self.assertEqual([u for u in R['unknowns'] if u.get('family') == 'observed_controls'], [])
        acts = [inner(80, 'Open notes', 'Close notes'), inner(60, 'Close panel', 'Open panel'), inner(80, 'Close notes', 'Open notes')]
        d = attempt(E, renders(state=st, actions=acts)); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], [])
    def test_repeated_action_with_a_different_final_label_binds_each_occurrence(self):
        seq, st = (60, 80, 60, 80), 'activated@60+80+60+80'; occ = [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': True}, {'action_index': 3, 'before': 'Close notes', 'after': 'Notes closed', 'shown': True}]
        rec = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Notes closed', controls=seq, index=3, state=st, occurrences=occ); E = route([rec], controls=seq, state=st)
        acts = [inner(80, 'Open notes', 'Close notes'), inner(60, 'Close panel', 'Open panel'), inner(80, 'Close notes', 'Notes closed')]
        d = attempt(E, renders(state=st, actions=acts)); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json')); self.assertEqual((v['preserved'], v['observed']), ([], []))
    def test_a_damaged_intermediate_occurrence_is_refused_by_the_native_readings(self):
        seq, st = (60, 80, 60, 80), 'activated@60+80+60+80'; occ = [{'action_index': 1, 'before': 'Open notes', 'after': 'Closed notes', 'shown': True}, {'action_index': 3, 'before': 'Closed notes', 'after': 'Open notes', 'shown': True}]  # chains, but the intermediate label is not what the browser read
        rec = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Open notes', controls=seq, index=3, state=st, occurrences=occ); E = route([rec], controls=seq, state=st); R = rb.readback(E); self.assertEqual(sites(R), {'u1': [0]})
        acts = [inner(80, 'Open notes', 'Close notes'), inner(60, 'Close panel', 'Open panel'), inner(80, 'Close notes', 'Open notes')]
        d = attempt(E, renders(state=st, actions=acts)); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ['record 0: occurrence 1 differs from its native action reading'])
    def test_an_omitted_or_invented_occurrence_is_refused(self):
        seq, st = (60, 80, 60, 80), 'activated@60+80+60+80'; acts = [inner(80, 'Open notes', 'Close notes'), inner(60, 'Close panel', 'Open panel'), inner(80, 'Close notes', 'Open notes')]
        omitted = record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Close notes', controls=seq, index=1, state=st)  # only the first change recorded while the browser changed the label again
        E = route([omitted], controls=seq, state=st); d = attempt(E, renders(state=st, actions=acts)); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ['record 0: recorded occurrences differ from the native label-changing actions of this control'])
    def test_wrong_occurrence_order_in_the_saved_render_is_refused(self):
        E = route([self.rec60()], controls=self.SEQ, state=self.ST); d = attempt(E, renders(state=self.ST, actions=self.acts((60, 80)))); rb.main([str(d), str(d / 'R.json')])
        self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ["record 0: the render record's inner actions are not the state's control sequence"])
    def test_an_occurrence_before_the_first_inner_record_has_no_native_evidence(self):
        E = route([record(60, (117, 121), [{'unit': 'u1', 'text_at': [[17, 21]]}], 'here', 'there', controls=(60,), index=0, state='activated@60')], controls=(60,), state='activated@60'); R = rb.readback(E); self.assertEqual(sites(R), {'u1': [0]})
        d = attempt(E, renders(state='activated@60', actions=[])); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ['record 0: recorded occurrences differ from the native label-changing actions of this control'])

class FinalObservation(unittest.TestCase):
    """Final means final: `observed.shown`/`label` are bound to the end-of-actions native reading of the control (`final_controls`), while each occurrence
    binds to its own action record. A later action may hide or show an earlier changed control; the schema never equates the two."""
    SEQ, ST = (60, 80, 60), 'activated@60+80+60'  # 80 changes its label (action 1); the later action on 60 (action 2) may hide or show control 80 by an allowed attribute change
    def rec80(self, shown=True, **o): return record(80, (106, 116), [{'unit': 'u1', 'text_at': [[6, 16]]}], 'Open notes', 'Close notes', controls=self.SEQ, index=1, state=self.ST, observed={'label': 'Close notes', 'shown': shown, 'by': 'action: native textContent after it'}, **o)
    def acts(self): return [inner(80, 'Open notes', 'Close notes'), inner(60, 'Close panel', 'Open panel')]
    def test_unchanged_positive(self):
        E = route([self.rec80()], controls=self.SEQ, state=self.ST); d = attempt(E, renders(state=self.ST, actions=self.acts())); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json')); self.assertEqual((v['preserved'], v['observed']), ([], [])); self.assertEqual(sites(rb.readback(E)), {'u1': [0]})
    def test_later_action_hides_the_changed_control(self):
        fin = [{'label': 'Close notes', 'shown': False}, {'label': 'Open panel', 'shown': True}]  # the browser's final reading in first-action order (80, 60): control 80 hidden by the later action
        E = route([self.rec80(shown=True)], controls=self.SEQ, state=self.ST); d = attempt(E, renders(state=self.ST, actions=self.acts(), final=fin)); rb.main([str(d), str(d / 'R.json')])
        self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ['record 0: observed label or visibility differs from the final native observation'])  # a record still claiming shown is refused
        E2 = route([self.rec80(shown=False, status='incomplete', reasons=['control not shown in the final state'])], controls=self.SEQ, state=self.ST); R2 = rb.readback(E2); self.assertEqual(sites(R2), {}); self.assertIn({'family': 'observed_controls', 'record': 0, 'why': 'incomplete: control not shown in the final state'}, R2['unknowns'])  # the producer's correct record: represented, never called shown
        E3 = route([self.rec80(shown=False)], controls=self.SEQ, state=self.ST); self.assertIn({'family': 'observed_controls', 'record': 0, 'why': 'complete record with the control not shown'}, rb.readback(E3)['unknowns'])
    def test_later_action_shows_a_control_hidden_right_after_its_own_action(self):
        acts = [inner(80, 'Open notes', 'Close notes', shown=False), inner(60, 'Close panel', 'Open panel')]; fin = [{'label': 'Close notes', 'shown': True}, {'label': 'Open panel', 'shown': True}]
        rec = self.rec80(shown=True, lineage={'controls': list(self.SEQ), 'action_index': 1, 'render': 1, 'state_capture_sha256': CAP, 'occurrences': [{'action_index': 1, 'before': 'Open notes', 'after': 'Close notes', 'shown': False}]})  # history says hidden after its action; the final reading says shown
        E = route([rec], controls=self.SEQ, state=self.ST); self.assertEqual(sites(rb.readback(E)), {'u1': [0]}); d = attempt(E, renders(state=self.ST, actions=acts, final=fin)); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], [])
    def test_corrupt_or_missing_final_metadata_is_refused(self):
        E = route([self.rec80()], controls=self.SEQ, state=self.ST)
        for fin, problem in (([{'label': 'Close note', 'shown': True}, {'label': 'Open panel', 'shown': True}], 'observed label or visibility differs from the final native observation'), ([{'label': 'Open panel', 'shown': True}], 'no final native observation for this control'), ([], 'no final native observation for this control'), ({'80': {'label': 'Close notes', 'shown': True}}, 'no final native observation for this control')):  # a wrong length or a non-list is no reading of this control
            with self.subTest(final=fin):
                d = attempt(E, renders(state=self.ST, actions=self.acts(), final=fin)); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ['record 0: ' + problem])
        rends = renders(state=self.ST, actions=self.acts()); del rends[1]['final_controls']; d = attempt(E, rends); rb.main([str(d), str(d / 'R.json')]); self.assertEqual(rb.verify(str(d), str(d / 'R.json'))['observed'], ['record 0: no final native observation for this control'])

class Custody(unittest.TestCase):
    def test_render_evidence_is_bound_by_the_completion_pin(self):
        E = route([ONE()]); d = attempt(E, renders()); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json')); self.assertEqual(v['custody'], []); self.assertIn('context_renders_sha256', json.loads((d / 'R.json').read_bytes())['custody'])
        (d / 'CONTEXT_RENDERS.json').write_text(json.dumps(renders(after='Closed notes')))  # changed after the pin: custody fails and nothing else is claimed
        v = rb.verify(str(d), str(d / 'R.json')); self.assertEqual(v['custody'], ['custody not proved: CONTEXT_RENDERS.json missing or not the completion pin']); self.assertEqual(v['annotations'], ['not checked: custody failed'])
    def test_a_context_route_without_the_pin_fails_custody_and_an_ordinary_route_is_unchanged(self):
        E = route([ONE()]); d = attempt(E, renders(), pin=False); self.assertRaisesRegex(ValueError, 'context_renders_sha256 missing', rb.main, [str(d), str(d / 'R.json')])
        E0 = route(); d0 = attempt(E0, None); rb.main([str(d0), str(d0 / 'R.json')]); self.assertEqual(set(json.loads((d0 / 'R.json').read_bytes())['custody']), rb.CUSTODY_KEYS); self.assertNotIn('observed', rb.verify(str(d0), str(d0 / 'R.json')))

class RootProbe(unittest.TestCase):
    """Root's retained damage probe (reconstruction_owner_contract_red/CASES.json): the positive composes; every other case is listed with one reason and composes nowhere."""
    def test_cases(self):
        for name, E in json.loads(STORE.read('root_ownership_cases/CASES.json')).items():
            with self.subTest(case=name):
                E = copy.deepcopy(E)
                for rec in E['observed_controls']:  # Root's ownership cases predate lineage.occurrences: the one single occurrence the producer would record is added, nothing else changes
                    rec['lineage'].setdefault('occurrences', [{'action_index': rec['lineage']['action_index'], 'before': rec['original']['label'], 'after': rec['observed']['label'], 'shown': rec['observed']['shown']}])
                R = rb.readback(E); unknown = [u for u in R['unknowns'] if u.get('family') == 'observed_controls']
                if name == 'positive': self.assertEqual(sites(R), {'u1': [0]}); self.assertEqual(unknown, [])
                else: self.assertEqual(sites(R), {}); self.assertEqual(len(unknown), 1, unknown)
                self.assertEqual(rb.preserved(E, R), [])

class Damage(unittest.TestCase):
    def test_label_moved_to_the_equal_words_outside_the_control_is_rejected(self):
        E = route([ONE()]); R = rb.readback(E); nodes = {n['record']['id']: n for n, _, _ in rb._units_in_order(R['sequence'])}
        nodes['u2']['attached'] = nodes['u1'].pop('attached'); self.assertTrue(any('observed_controls owner attachments differ' in p for p in rb.preserved(E, R)))
    def test_label_stamped_twice_is_rejected(self):
        E = route([ONE()]); R = rb.readback(E); nodes = {n['record']['id']: n for n, _, _ in rb._units_in_order(R['sequence'])}
        nodes['u2']['attached'] = {'observed_controls': [0]}; self.assertTrue(any('observed_controls owner attachments differ' in p for p in rb.preserved(E, R)))
    def test_observed_or_original_text_changed_in_the_readback_is_rejected(self):
        E = route([ONE()])
        for path, value in ((('observed', 'label'), 'Closed notes'), (('original', 'label'), 'Open note'), (('owners',), [{'unit': 'u1', 'text_at': [[6, 15]]}])):
            with self.subTest(path=path):
                R = rb.readback(E); x = R['observed_controls'][0]
                for k in path[:-1]: x = x[k]
                x[path[-1]] = value; self.assertTrue(any('inverse differs from E' in p and 'observed_controls' in p for p in rb.preserved(E, R)))
    def test_saved_unit_text_changed_under_the_slice_is_rejected(self):
        E = route([ONE()]); R = rb.readback(E); R['sequence'][0]['record']['text'] = 'Notes Open  notes here'; self.assertTrue(any('inverse differs from E' in p for p in rb.preserved(E, R)))
    def test_a_dropped_or_silenced_unknown_fails_annotations(self):
        E = route([ONE(status='incomplete', reasons=['state route not OK'])]); R = rb.readback(E); R['unknowns'] = [u for u in R['unknowns'] if u.get('family') != 'observed_controls']
        self.assertEqual(rb.annotations(E, R), ['annotations or unknowns differ from a recomputation (reproducibility only)'])
    def test_a_record_attached_although_it_does_not_fit_is_rejected(self):
        E = route([ONE(control=81)]); R = rb.readback(E); nodes = {n['record']['id']: n for n, _, _ in rb._units_in_order(R['sequence'])}
        nodes['u1']['attached'] = {'observed_controls': [0]}; self.assertTrue(any('observed_controls owner attachments differ' in p for p in rb.preserved(E, R)))

class NativeBinding(unittest.TestCase):
    def test_verify_binds_the_record_to_the_saved_render(self):
        E = route([ONE()]); d = attempt(E, renders()); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json'))
        self.assertEqual((v['custody'], v['preserved'], v['annotations'], v['observed']), ([], [], [], []))
    def test_verify_reports_each_native_mismatch(self):
        E = route([ONE()])
        for rends, problem in ((renders(after='Close note'), 'occurrence 1 differs from its native action reading'), (renders(before='Open'), 'occurrence 1 differs from its native action reading'),
                               (renders(shown=False), 'occurrence 1 differs from its native action reading'),
                               (renders(state='activated@60'), 'state differs from the render record'), (renders(cap='ef' * 32), 'capture digest differs from the render record'), (renders(control=60), "the render record's inner actions are not the state's control sequence"),
                               (renders(changed=False), 'recorded occurrences differ from the native label-changing actions of this control'),
                               ([renders()[0]], 'lineage names no render record')):
            with self.subTest(problem=problem):
                d = attempt(E, rends); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json')); self.assertEqual(v['observed'], ['record 0: ' + problem]); self.assertEqual(v['preserved'], [])
    def test_initial_routes_have_no_observed_key(self):
        E0 = route(); d0 = attempt(E0, None); rb.main([str(d0), str(d0 / 'R.json')]); v0 = rb.verify(str(d0), str(d0 / 'R.json')); self.assertNotIn('observed', v0); self.assertEqual((v0['custody'], v0['preserved'], v0['annotations']), ([], [], []))
    def test_incomplete_record_is_not_bound_and_does_not_make_the_state_successful(self):
        E = route([ONE(status='incomplete', reasons=['control not shown after the action'])]); d = attempt(E, renders(after='anything')); rb.main([str(d), str(d / 'R.json')]); v = rb.verify(str(d), str(d / 'R.json'))
        self.assertEqual(v['observed'], []); self.assertIn('observed_controls', v['unrepresented'])

class OldSavedRouteEvidence(unittest.TestCase):
    """Old-failure evidence (retained fixture), fixed expectation: Fable's label_slice_run3 state routes carry v2 records while their acted link records still have no proved
    extent or owners, so every record must be listed with that one reason and compose nowhere. Not a producer acceptance."""
    def test_records_without_a_proved_link_record_are_refused(self):
        found = [(k, r) for k, r in json.loads(STORE.read('old_label_failure/ROUTES.json'))['states'].items() if r.get('observed_controls')]; self.assertTrue(found)
        for k, E in found:
            with self.subTest(state=k):
                R = rb.readback(E); self.assertEqual(rb.preserved(E, R), []); self.assertEqual(sites(R), {})
                self.assertEqual([u for u in R['unknowns'] if u.get('family') == 'observed_controls'], [{'family': 'observed_controls', 'record': j, 'why': "record is not the contract shape: lineage.occurrences" if 'occurrences' not in rec['lineage'] else "extent is not the link record's own extent"} for j, rec in enumerate(E['observed_controls'])])

class NewSavedFixture(unittest.TestCase):
    """The new saved public fixture run (the caller's state folders with filled acted link records and the render pin), fixed expected contract whose
    expectations come from the saved NATIVE final observation, never from the composer: a record whose control is shown in the state's final native
    reading (CONTEXT_RENDERS final_controls) must be complete, composed at exactly its owners' saved slices and listed under no unknown; a record whose
    control is finally hidden must be incomplete, listed with its reason and attached nowhere. The visible count is asserted; "all records visible" is
    never demanded. The folders are rebuilt from the pinned fixture store; a missing store fails."""
    def test_every_state_composes_its_visible_labels_and_lists_its_hidden_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.RUN = saved_run(Path(tmp)); self._states()
    def _states(self):
        states = sorted(p for p in (self.RUN / 'states').iterdir() if (p / 'ROUTE.json').is_file()); self.assertTrue(states)
        visible = hidden = 0
        for st in states:
            E = json.loads((st / 'ROUTE.json').read_bytes()); recs = E.get('observed_controls') or []
            with self.subTest(state=st.name):
                out = Path(tempfile.mkdtemp()) / 'R.json'; rb.main([str(st), str(out)]); v = rb.verify(str(st), str(out)); R = json.loads(out.read_bytes())
                self.assertEqual((v['custody'], v['preserved'], v['annotations']), ([], [], []))
                if not recs: continue
                renders = json.loads((st / 'CONTEXT_RENDERS.json').read_bytes()); want, listed = {}, []
                for j, rec in enumerate(recs):
                    rd = renders[rec['lineage']['render']]; order = list(dict.fromkeys(i['control'] for i in rd['inner'])); fin = rd['final_controls'][order.index(rec['control'])]  # the native final reading decides the expectation
                    if fin['shown'] is True:
                        visible += 1; self.assertEqual(rec['status'], 'complete', (st.name, j)); self.assertEqual(rec['observed'], {'label': fin['label'], 'shown': True, 'by': rec['observed']['by']}, (st.name, j))
                        for o in rec['owners']: want.setdefault(o['unit'] if 'cell' not in o else (o['unit'], [i for i, c in enumerate(next(u for u in E['units'] if u['id'] == o['unit'])['cells']) if rb._first_byte(c) == o['cell']][0]), []).append(j)
                    else:
                        hidden += 1; self.assertEqual(rec['status'], 'incomplete', (st.name, j)); self.assertFalse(rec['observed']['shown'], (st.name, j)); listed.append(j)
                unknown = sorted(u['record'] for u in R['unknowns'] if u.get('family') == 'observed_controls')
                self.assertEqual(unknown, sorted(listed), (st.name, 'only the finally hidden records may be listed; every visible one must compose'))
                self.assertEqual(sites(R), want, (st.name, 'visible labels at exactly their owners\' saved slices')); self.assertEqual(v['observed'], [], st.name)
        self.assertTrue(visible, 'no state carried a finally shown control record'); self.assertTrue(hidden, 'no state carried a finally hidden control record (the fixture must exercise both)')

if __name__ == '__main__': unittest.main()
