"""context.optional_controls on the recorded public CCL R2 initial view: one actual caller run's own inputs (fixture public_ccl_r2_optional_controls:
the member bytes, the displayed route's fields, the source child, the three initial renders' native code inventories, the recorded evidence).
The recorded positive qualifies; each damage keeps the deficit with its own reason. Decision level, no browser: Scope.code itself and the caller
path ran in the recorded caller runs named in the fixture. The damaged-text case is one the job's reconstruct/verify gate alone does not catch."""
import copy, json, re, unittest
from pathlib import Path
from driver.prepare.convert import anchor, context, edgartools_html

FX = Path(__file__).with_name('fixtures') / 'public_ccl_r2_optional_controls'
RAW, PARENT, IN = (FX / 'R2.htm').read_bytes(), (FX / 'parent.html').read_bytes(), json.loads((FX / 'inputs.json').read_bytes())
SHOW_JS = 'https://www.sec.gov/include/Show.js'


def call(route=None, codes=None, child=None, sr=None, evidence=None, parent=None):
    r = copy.deepcopy(route if route is not None else IN['route']); r['facts'] = {'source_reading': copy.deepcopy(sr if sr is not None else IN['route_facts_source_reading'])}
    ev = copy.deepcopy(evidence if evidence is not None else AUGMENTED_EVIDENCE); ev['observed'][ev['parent_url']]['body'] = PARENT if parent is None else parent
    recs = [({'code': c} if c is not None else {}) for c in copy.deepcopy(codes if codes is not None else IN['codes'])]  # None: a render with no inventory
    return context.optional_controls(RAW, r, recs, ev, copy.deepcopy(child if child is not None else IN['child']))


def walk(raw):  # the production CODE_ACTIONS on `raw`, inserted after DOMContentLoaded as the viewer appends a report (source scope = the inserted nodes)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(); pg.add_init_script(context.ISO_INIT)
        pg.route('**/*', lambda r: r.fulfill(status=200, content_type='text/html', body='<html><head></head><body><div></div></body></html>') if r.request.url == 'http://viewer.invalid/' else r.abort())
        pg.goto('http://viewer.invalid/', wait_until='load'); pg.evaluate("h => document.body.firstElementChild.insertAdjacentHTML('beforeend', h)", raw.decode('ascii'))
        assert pg.evaluate('window.__sourceScope.useParse()') is True; got = pg.evaluate(context.CODE_ACTIONS); b.close()
    return got


BOT0 = '39f3dc5b34f614a78075f1824407dc3de33cffcb5e5e3c5fd59a1356d3385d97'  # AUGMENTED, not historical: the recorded caller evidence predates the per-file insertion
AUGMENTED_EVIDENCE = copy.deepcopy(IN['evidence'])  # proof, so the default adds the proof the new binder records for that run's own inserted script (its URL and recorded bytes)
AUGMENTED_EVIDENCE['inserted_script'] = {'href': next(u for u, o in IN['evidence']['observed'].items() if o.get('sha256') == BOT0), 'response_sha256': BOT0}
import tempfile as _tf
from . import test_version_qualification as TVQ
_QROOT = Path(_tf.mkdtemp()); (_QROOT / 'store').mkdir()  # AUGMENTED: a real producer record for the recorded bytes (the reviewed versions need one too now)
TVQ.make_record(_QROOT, _QROOT / 'store', BOT0, AUGMENTED_EVIDENCE['inserted_script']['href'], 'a' * 64)
AUGMENTED_EVIDENCE['qualifications'] = {'folder': str(_QROOT / 'store'), 'runtime_manifest_sha256': 'a' * 64}
HISTORICAL_CODES = copy.deepcopy(IN['codes'])  # the recorded caller renders' own fields, kept apart: they predate the Show.toggleNext walk


def walk_html(raw, expr):  # one DOM fact of `raw` inserted as walk() inserts it
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page()
        pg.route('**/*', lambda r: r.fulfill(status=200, content_type='text/html', body='<html><head></head><body><div></div></body></html>') if r.request.url == 'http://viewer.invalid/' else r.abort())
        pg.goto('http://viewer.invalid/', wait_until='load'); pg.evaluate("h => document.body.firstElementChild.insertAdjacentHTML('beforeend', h)", raw.decode('ascii'))
        got = pg.evaluate(expr); b.close()
    return got


def setUpModule():  # AUGMENTED, not historical: the walk facts and texts are computed by walk() (production CODE_ACTIONS) on the fixture's own R2 bytes and
    # merged into IN['codes'] only where every onclick and TABLE flag equal the recorded renders and every holder is DOM-unique there too
    got = walk(RAW)
    for c in IN['codes']:
        assert [x[:2] for x in c['actions']['actions']] == [x[:2] for x in got['actions']], 'walk computed on other controls than the recorded renders'
        assert all(c['actions']['ids'].get(k) == [1, 1] for x in got['actions'] if x[2] for k in x[2]['holders']), 'holders not DOM-unique in the recorded renders'
        c['actions']['actions'] = [list(x) for x in got['actions']]
        c['actions']['texts'] = dict(got['texts'])


def codes(fn):  # every render's inventory changed the same way (renders must agree)
    cs = copy.deepcopy(IN['codes'])
    for c in cs: fn(c)
    return cs


def show_links(route): return [l for l in route['source_links'] if l.get('script_action') and 'showAR' in l['declarations'][0]['value']]
def first_target(): return re.search(r"showAR\( this, '([^']+)'", show_links(IN['route'])[0]['declarations'][0]['value']).group(1)


class OptionalControls(unittest.TestCase):
    def assertKept(self, got, part):
        why, _ = got; self.assertTrue(why, 'the deficit must stay'); self.assertTrue(any(part in w for w in why), why)

    def test_recorded_positive_qualifies(self):
        why, facts = call(); self.assertEqual(why, [])
        self.assertEqual((facts['controls'], facts['targets'], facts['renders']), (18, 4, 3))  # fixture facts: 18 declared controls, 4 distinct targets, 3 initial renders
        self.assertEqual(len(facts['infrastructure']), 1)
        self.assertEqual(sorted(len(c['scripts']) for c in IN['codes']), [179, 181, 181])  # fixture fact: the renders' own-code counts differ (lifetime record)

    def test_unknown_action_form(self):
        r = copy.deepcopy(IN['route']); show_links(r)[0]['declarations'][0]['value'] = 'Show.load( this );'
        self.assertKept(call(route=r), 'not one renderer action')

    def test_following_table_branch_is_unsupported(self):
        def f(c): c['actions']['actions'][[i for i, (v, *_) in enumerate(c['actions']['actions']) if 'showAR' in v][0]][1] = True
        self.assertKept(call(codes=codes(f)), 'following TABLE')

    def test_missing_or_duplicated_target_id(self):
        t = first_target()
        for counts in ([0, 0], [2, 2], [1, 0]):
            self.assertKept(call(codes=codes(lambda c: c['actions']['ids'].__setitem__(t, counts))), 'not one source-scope id')

    def test_dom_controls_must_equal_the_native_declarations(self):
        self.assertKept(call(codes=codes(lambda c: c['actions']['actions'].pop())), 'differ from the native declarations')

    def test_unknown_page_code(self):
        self.assertKept(call(codes=codes(lambda c: c['scripts'].append({'url': '', 'sha256': 'f' * 64, 'bytes': 7, 'text': 'x = 1;'}))), 'unknown executable code')

    def test_changed_bot_artifact_is_not_infrastructure(self):
        def f(c):
            for s in c['scripts']:
                if s['sha256'] in context.INFRASTRUCTURE: s['sha256'] = 'e' * 64
        self.assertKept(call(codes=codes(f)), 'unknown executable code')

    def test_changed_viewer_template(self):
        def f(c):
            for s in c['scripts']:
                if s.get('template') == context.VIEWER_TEMPLATE: s['template'] = 'd' * 64; s['sha256'] = 'd' * 64
        self.assertKept(call(codes=codes(f)), 'unknown executable code')

    def test_known_code_must_be_the_recorded_response_at_its_address(self):
        ev = copy.deepcopy(IN['evidence']); ev['observed'][SHOW_JS]['sha256'] = '0' * 64
        self.assertKept(call(evidence=ev), 'is not the recorded response')

    def test_a_known_library_listener_on_an_ancestor(self):  # a delegated click handler (jQuery's own dispatch) on a container of the controls
        def f(c):
            jq = next(s for s in c['scripts'] if s['url'].endswith('jquery-latest.min.js'))
            c['listeners'].append({'type': 'click', 'window': False, 'relation': {'outside': True, 'ancestor': True, 'attributes': []}, 'script': {k: jq[k] for k in ('url', 'sha256', 'bytes')}})
        self.assertKept(call(codes=codes(f)), 'on an ancestor of source content')

    def test_a_source_node_listener_that_is_not_its_declaration(self):
        def f(c):
            l = next(x for x in c['listeners'] if (x.get('relation') or {}).get('outside') is False and not (x.get('relation') or {}).get('ancestor'))
            l['script'] = dict(l['script'], text='Show.showAR( this, \'defref_other\', window );')
        self.assertKept(call(codes=codes(f)), 'not its own declared action')

    def test_unknown_node_scope(self):
        self.assertKept(call(codes=codes(lambda c: c['listeners'][0].__setitem__('relation', None))), 'node scope unknown')

    def test_renders_disagree(self):  # one render lacks a page script
        cs = copy.deepcopy(IN['codes']); cs[1]['scripts'].remove(next(s for s in cs[1]['scripts'] if s['url'] == SHOW_JS))
        self.assertKept(call(codes=cs), 'disagree')

    def test_own_code_count_may_differ_page_code_may_not(self):  # this runtime's code runs once per its own call; the page's must agree
        wrapper = next(s for s in IN['codes'][0]['scripts'] if s['sha256'] in context.TOOLING and s['bytes'] == 61)
        cs = copy.deepcopy(IN['codes']); cs[1]['scripts'].append(dict(wrapper)); self.assertEqual(call(codes=cs)[0], [])
        cs = copy.deepcopy(IN['codes']); cs[1]['scripts'].append(dict(next(s for s in cs[1]['scripts'] if s['url'] == SHOW_JS)))
        self.assertKept(call(codes=cs), 'disagree')

    def test_no_or_unknown_inventory(self):
        self.assertKept(call(codes=[]), 'no initial render was recorded')
        self.assertKept(call(codes=[{'unknown': 'Debugger.enable failed'}]), 'code inventory unknown')

    def test_no_ok_source_reading(self):
        self.assertKept(call(sr={'made': False, 'why': 'nothing proved hidden'}), 'no OK typed source reading')
        self.assertKept(call(child=dict(IN['child'], status='PARTIAL')), 'no OK typed source reading')

    def test_a_target_the_reading_does_not_hold(self):
        t = first_target(); (a, b), = [(r['start'], r['end']) for r in IN['route']['source_ids']['records'] if r.get('by') == 'id' and r['value'] == t]
        child = copy.deepcopy(IN['child']); keep = []
        for u in child['units']:
            at = (u.get('anchor') or {}).get('byte_start'); cells = [c for c in u.get('cells') or []]
            inside = (at is not None and a <= at < b) or any(a <= s.get('byte_start', -1) < b for c in cells for s in ([c['anchor']] if isinstance(c.get('anchor'), dict) else c.get('anchor') or []) if isinstance(s, dict))
            if not inside: keep.append(u)
        self.assertLess(len(keep), len(child['units'])); child['units'] = keep
        self.assertKept(call(child=child), 'source reading, one run-to-owner rule')

    def test_damaged_text_with_unchanged_ranges(self):  # the reconstruct/verify gate alone passes this (recorded run child_damage_ccl_r2)
        t = first_target(); (a, b), = [(r['start'], r['end']) for r in IN['route']['source_ids']['records'] if r.get('by') == 'id' and r['value'] == t]
        child = copy.deepcopy(IN['child']); done = False
        for u in child['units']:
            for c in [u] + list(u.get('cells') or []):
                sp = [s for s in ([c['anchor']] if isinstance(c.get('anchor'), dict) else c.get('anchor') or []) if isinstance(s, dict) and 'byte_start' in s]
                txt = c.get('text') or ''
                if not done and sp and a <= sp[0]['byte_start'] < b and re.search('[A-Za-z]', txt):
                    k = re.search('[A-Za-z]', txt).start(); c['text'] = txt[:k] + ('Y' if txt[k] != 'Y' else 'Z') + txt[k + 1:]; done = True
        self.assertTrue(done); self.assertKept(call(child=child), 'source reading, one run-to-owner rule')

    def test_every_render_is_checked_on_its_own(self):  # Root 49eeee: damage present in a later render only must keep the deficit
        self.assertGreaterEqual(len(IN['codes']), 3)  # fixture fact: three initial renders
        cs = copy.deepcopy(IN['codes']); jq = next(s for s in cs[1]['scripts'] if s['url'].endswith('jquery-latest.min.js'))
        cs[1]['listeners'].append({'type': 'click', 'window': False, 'relation': {'outside': True, 'ancestor': True, 'attributes': []}, 'script': {k: jq[k] for k in ('url', 'sha256', 'bytes')}})
        self.assertKept(call(codes=cs), 'render 1: listener click on an ancestor')
        cs = copy.deepcopy(IN['codes']); cs[1]['actions']['ids'][first_target()] = [2, 2]
        self.assertKept(call(codes=cs), 'render 1: Show.showAR target')
        cs = copy.deepcopy(IN['codes']); a = cs[2]['actions']['actions']; a[[k for k, (v, *_) in enumerate(a) if 'showAR' in v][0]][1] = True
        self.assertKept(call(codes=cs), 'render 2: Show.showAR')

    def test_a_render_without_inventory_fails(self):
        cs = copy.deepcopy(IN['codes']); cs[2] = None
        self.assertKept(call(codes=cs), 'render 2: no code inventory')
        cs = copy.deepcopy(IN['codes']); cs[1] = {'unknown': 'Target.getTargets failed'}
        self.assertKept(call(codes=cs), 'render 1: code inventory unknown')

    def test_escaped_target_literal_is_refused_and_plain_literals_are_the_argument(self):
        for v in [l['declarations'][0]['value'] for l in IN['route']['source_links'] if l.get('script_action')]:  # recorded positives: no escape, so literal == runtime argument
            m = context.ACTION.fullmatch(v); self.assertTrue(m, v); self.assertNotIn('\\', m.group('id') or '')
        t = first_target()
        for esc in ('\\u0041', "\\'", '\\\\', '\\x41'):
            r = copy.deepcopy(IN['route']); l = show_links(r)[0]; l['declarations'][0]['value'] = l['declarations'][0]['value'].replace("'" + t + "'", "'" + t + esc + "'")
            self.assertKept(call(route=r), 'not one renderer action')

    def test_child_frames_or_other_active_contexts_keep_the_deficit(self):
        self.assertKept(call(codes=codes(lambda c: c.__setitem__('frames', 1))), 'unsupported active context')
        self.assertKept(call(codes=codes(lambda c: c.__setitem__('contexts', ['worker']))), 'unsupported active context')
        self.assertKept(call(codes=codes(lambda c: c.pop('frames'))), 'unsupported active context')  # an inventory without the frame count is not a zero

    def test_any_executed_context_beyond_the_page_and_own_worlds_keeps_the_deficit(self):  # Root lifetime review 1d8612d8: a detached child frame
        child_frame = {'own_frame': False, 'default': True, 'name': '', 'type': 'default'}
        self.assertKept(call(codes=codes(lambda c: c['executed_contexts'].append(child_frame))), 'unqualified executed context')
        foreign_world = {'own_frame': True, 'default': False, 'name': 'some_other_world', 'type': 'isolated'}
        self.assertKept(call(codes=codes(lambda c: c['executed_contexts'].append(foreign_world))), 'unqualified executed context')
        self.assertKept(call(codes=codes(lambda c: c.pop('executed_contexts'))), 'unqualified executed context')  # no record is not an empty one

    def test_a_child_frame_qualifies_only_when_the_identified_infrastructure_attached_it(self):
        infra = [u for u, o in IN['evidence']['observed'].items() if o.get('sha256') in context.INFRASTRUCTURE]; self.assertEqual(len(infra), 1)
        recorded = [x for c in IN['codes'] for x in c['executed_contexts']]
        self.assertTrue(recorded and all(not x['own_frame'] and x['creator'] and set(x['creator']) <= set(infra) for x in recorded))  # fixture fact: the bot artifact's own frames
        for creator in ([], infra + ['https://www.sec.gov/include/Show.js'], ['https://www.sec.gov/cgi-bin/viewer']):
            frame = {'own_frame': False, 'frame': 'F', 'default': True, 'name': '', 'type': 'default', 'creator': creator}
            self.assertKept(call(codes=codes(lambda c: c['executed_contexts'].append(dict(frame)))), 'unqualified executed context')

    def test_only_the_template_navigation_of_a_recorded_viewer_link_is_admitted(self):  # Root 52e626d2: literal href presence admitted arbitrary code
        nav = [s['text'] for c in IN['codes'] for s in c['scripts'] if not s['url'] and s.get('text') and context.VIEWER_NAVIGATION.fullmatch(s['text'])]
        self.assertTrue(nav and all(b'href="javascript:' + t.encode() + b'"' in PARENT for t in nav))  # fixture fact: the selection's loadReport(n) click, a recorded viewer link
        bad = "Show.showAR = function () { document.body.textContent = 'changed after click'; };"
        parent = PARENT.replace(b'</body>', b'<a href="javascript:' + bad.encode() + b'">x</a></body>')
        self.assertKept(call(parent=parent, codes=codes(lambda c: c['scripts'].append({'url': '', 'sha256': 'a' * 64, 'bytes': len(bad), 'text': bad}))), 'unknown executable code')
        joined = nav[0] + bad; parent = PARENT.replace(b'</body>', b'<a href="javascript:' + joined.encode() + b'">x</a></body>')
        self.assertKept(call(parent=parent, codes=codes(lambda c: c['scripts'].append({'url': '', 'sha256': 'b' * 64, 'bytes': len(joined), 'text': joined}))), 'unknown executable code')
        self.assertNotIn(b'loadReport(99999);', PARENT)  # fixture fact: no such link in the recorded viewer
        self.assertKept(call(codes=codes(lambda c: c['scripts'].append({'url': '', 'sha256': 'c' * 64, 'bytes': 18, 'text': 'loadReport(99999);'}))), 'unknown executable code')

    def test_toggle_walk_facts(self):  # fixture facts (production CODE_ACTIONS on R2): 4 '- Definition' toggles find a DIV with no inline display (pinned: no-op), 6 '+ References' a hidden one
        w = [x[2] for x in IN['codes'][0]['actions']['actions'] if x[2] is not None]
        self.assertEqual(sorted((x['div'], x['display']) for x in w), [(True, '')] * 4 + [(True, 'none')] * 6)
        self.assertTrue(all(len(x['holders']) == 1 and x['holders'][0].startswith('defref_') for x in w))

    def test_unknown_toggle_walk_facts(self):  # an inventory without the walk (an older recording) fails closed
        self.assertKept(call(codes=codes(lambda c: c['actions'].__setitem__('actions', [x[:2] for x in c['actions']['actions']]))), 'its DOM walk facts are unknown')

    def test_a_revealing_toggle_no_element_encloses(self):  # also the earlier admitted path: a toggle inside a held target whose DIV lies outside every id element
        def f(c):
            x = next(x for x in c['actions']['actions'] if x[2] and x[2]['display'] == 'none'); x[2] = dict(x[2], holders=[])
        self.assertKept(call(codes=codes(f)), 'no DOM-unique source-scope element encloses')

    def test_an_enclosing_element_that_is_not_dom_unique(self):
        def f(c):
            k = next(x for x in c['actions']['actions'] if x[2] and x[2]['display'] == 'none')[2]['holders'][0]; c['actions']['ids'][k] = [2, 1]
        self.assertKept(call(codes=codes(f)), 'no DOM-unique source-scope element encloses')

    def test_an_element_whose_dom_text_is_not_its_source_text(self):  # what a parser repair (moved node) leaves: the DOM element holds other characters
        def f(c):
            k = next(x for x in c['actions']['actions'] if x[2] and x[2]['display'] == 'none')[2]['holders'][0]; c['actions']['texts'][k] += 'MOVED'
        self.assertKept(call(codes=codes(f)), 'with exactly its own source text in the DOM')

    def test_a_white_space_only_dom_difference_passes(self):  # demonstrated limit (search form): a blank more in the DOM text is not a held character
        def f(c):
            k = next(x for x in c['actions']['actions'] if x[2] and x[2]['display'] == 'none')[2]['holders'][0]; c['actions']['texts'][k] += ' \n'
        self.assertEqual(call(codes=codes(f))[0], [])

    def test_historical_fields_predate_the_walk(self):  # provenance: the recorded caller renders carry no walk; the facts the other tests use are augmented
        self.assertTrue(all(len(x) == 2 for c in HISTORICAL_CODES for x in c['actions']['actions']))
        self.assertTrue(all(len(x) == 3 for c in IN['codes'] for x in c['actions']['actions']))

    def test_no_op_toggles_need_no_element(self):  # pinned Show.toggleNext: no DIV throws, a DIV without an inline display is left alone - nothing changes
        def f(c):
            for x in c['actions']['actions']:
                if x[2]: x[2] = dict(x[2], holders=[], display='' if x[2]['display'] == 'none' else x[2]['display'])
        self.assertEqual(call(codes=codes(f))[0], [])
        def g(c):
            for x in c['actions']['actions']:
                if x[2]: x[2] = {'div': False, 'display': None, 'holders': []}
        self.assertEqual(call(codes=codes(g))[0], [])

    def test_hide_needs_no_enclosing_element(self):  # pinned Show.js: hideAR only hides Show.LastAR, which only showAR sets - it reveals nothing
        r = copy.deepcopy(IN['route']); hide = [l for l in r['source_links'] if l.get('script_action') and l['declarations'][0]['value'] == 'Show.hideAR();']
        self.assertTrue(hide)  # fixture fact: Show.hideAR controls
        hide[0]['tag'] = {'byte_start': 0, 'byte_end_exclusive': 1}
        self.assertEqual(call(route=r)[0], [])



class MovedDom(unittest.TestCase):  # a real parser repair: text standing directly in a table is foster-parented out of it (HTML parsing, 'in table' mode)
    RAW = (b'<html><body><div><table id="p"><tr><td><a href="javascript:void(0);" onclick="Show.toggleNext( this );">+ R</a>'
           b'<div style="display: none;">ref</div></td></tr>MOVED</table></div></body></html>')

    def check(self, raw):
        got = walk(raw); vis = anchor.Visible(raw, source=True)
        (a, b), = [(r['start'], r['end']) for r in edgartools_html.source_ids(vis)['records'] if r['by'] == 'id' and r['value'] == 'p']
        w = got['actions'][0][2]; self.assertEqual((w['div'], w['display'], w['holders']), (True, 'none', ['p']))
        return context.same_text(vis, a, b, got['texts']['p']), got['texts']['p']

    def test_foster_parented_text_breaks_the_element_identity(self):
        same, dom = self.check(self.RAW); self.assertNotIn('MOVED', dom); self.assertFalse(same)

    def test_the_same_element_without_the_stray_text(self):  # positive control: nothing moved, the DOM element shows exactly its bytes' characters
        self.assertEqual(self.check(self.RAW.replace(b'MOVED', b'')), (True, '+ Rref'))

    def test_text_reordered_inside_the_element_is_caught(self):  # foster parenting INSIDE the holder: B stands directly in an inner table and is moved
        # before it, still within #p - the same characters, another order; the ordered search form refuses it
        raw = self.RAW.replace(b'MOVED', b'').replace(b'>ref<', b'><table><tr><td>A</td></tr>B</table><'); same, dom = self.check(raw)
        self.assertEqual(dom, '+ RBA'); self.assertFalse(same)

    def test_a_white_space_only_parser_change_passes(self):  # demonstrated limit: the parser drops the newline right after <pre>; white space is not
        # held material in the native search form (vis.idx, compare._WS) the held/owners rule counts, so the predicate passes; spacing roles stay with the reading's gates
        raw = self.RAW.replace(b'MOVED', b'').replace(b'>ref<', b'><pre>\nref</pre><'); same, dom = self.check(raw)
        self.assertEqual((same, dom), (True, '+ Rref')); self.assertIn(b'<pre>\nref', raw)

    def test_a_relationship_only_repair_keeps_every_character(self):  # misnested formatting: the parser re-parents (adoption agency) but moves no
        # character in, out or out of order - what a toggle can reveal is still exactly the element's own, held characters; structure is the reading's own gates' business
        raw = self.RAW.replace(b'MOVED', b'').replace(b'>ref<', b'>x<b>y<p>z</b>w</p><')
        same, dom = self.check(raw); self.assertEqual((same, dom), (True, '+ Rxyzw'))
        self.assertEqual(raw.count(b'<b>'), 1); self.assertEqual(walk_html(raw, "document.querySelectorAll('#p b').length"), 2)  # the DOM holds a second <b> the bytes do not



class PinnedShowBehaviour(unittest.TestCase):  # ground truth for the walk: the pinned renderer itself (fixture Show.js = KNOWN_CODE 2e4e3855) clicked in the browser
    def test_the_walk_predicts_each_toggle_and_its_effect_stays_in_its_holder(self):
        import hashlib
        from playwright.sync_api import sync_playwright
        show = (FX / 'Show.js').read_bytes(); self.assertEqual(context.KNOWN_CODE.get(hashlib.sha256(show).hexdigest()), 'renderer Show.js')
        facts = [x[2] for x in IN['codes'][0]['actions']['actions'] if x[2] is not None]; seen = []
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            for i, f in enumerate(facts):
                pg = b.new_page()
                pg.route('**/*', lambda r: r.fulfill(status=200, content_type='text/html', body='<html><head></head><body><div></div></body></html>') if r.request.url == 'http://viewer.invalid/' else r.abort())
                pg.goto('http://viewer.invalid/', wait_until='load'); pg.evaluate("h => document.body.firstElementChild.insertAdjacentHTML('beforeend', h)", RAW.decode('ascii'))
                pg.add_script_tag(content=show.decode('ascii'))
                seen.append(pg.evaluate('''([i, k]) => { const a = Array.from(document.querySelectorAll('[onclick]')).filter(x => /toggleNext/.test(x.getAttribute('onclick')))[i];
                    const h = document.getElementById(k), body0 = document.body.innerHTML, h0 = h.outerHTML, out0 = body0.replace(h0, '');
                    a.click(); const body1 = document.body.innerHTML, h1 = h.outerHTML;
                    return {changed: body1 !== body0, outside_same: body1.replace(h1, '') === out0}; }''', [i, f['holders'][0]])); pg.close()
            b.close()
        self.assertEqual([x['changed'] for x in seen], [bool(f['div'] and f['display']) for f in facts])  # predicted change == actual change, all 10
        self.assertTrue(all(x['outside_same'] for x in seen))  # every actual change lies inside the toggle's own holder


def untargeted(t):  # the route and its renders as if no showAR named popup `t`: its own close and toggle controls then stand outside every target
    r = copy.deepcopy(IN['route']); gone = {l['declarations'][0]['value'] for l in r['source_links'] if l.get('script_action') and f"'{t}'" in l['declarations'][0]['value']}
    r['source_links'] = [l for l in r['source_links'] if not (l.get('script_action') and l['declarations'][0]['value'] in gone)]
    def f(c):  # the same page without those controls: no DOM action, attribute listener or compiled handler of theirs
        c['actions']['actions'] = [x for x in c['actions']['actions'] if x[0] not in gone]
        c['listeners'] = [l for l in c['listeners'] if (l.get('script') or {}).get('text') not in gone]
        c['scripts'] = [s for s in c['scripts'] if s.get('text') not in gone]
    return r, codes(f)


def record(r, t): return next(x for x in r['source_ids']['records'] if x['by'] == 'id' and x['value'] == t)
def inside(r, t): a = record(r, t); return [l for l in r['source_links'] if l.get('script_action') and a['start'] < l['tag']['byte_start'] < a['end']]


class UntargetedPopup(unittest.TestCase):  # a popup no showAR control of the page names (case 6e619390's 6 close + toggle pairs have this shape)
    T = 'defref_ccl_AuditorInformationAbstract'
    assertKept = OptionalControls.assertKept

    def test_fixture_shape(self):  # fixture facts the cases below rest on
        r, _ = untargeted(self.T); forms = sorted(l['declarations'][0]['value'] for l in inside(r, self.T))
        self.assertEqual(forms, ['Show.hideAR();'] + ['Show.toggleNext( this );'] * 3)
        self.assertFalse([l for l in r['source_links'] if l.get('script_action') and self.T in l['declarations'][0]['value']])

    def test_its_controls_qualify_inside_its_dom_unique_held_element(self):  # the private 6+6 shape: close + toggles of a popup no showAR names
        r, cs = untargeted(self.T); why, facts = call(route=r, codes=cs)
        self.assertEqual(why, []); self.assertEqual((facts['controls'], facts['targets']), (17, 3))

    def test_two_native_records_for_its_id(self):
        r, cs = untargeted(self.T); r['source_ids']['records'].append(dict(record(r, self.T), start=0, end=1))
        self.assertKept(call(route=r, codes=cs), 'is held whole by the source reading')

    def test_its_content_the_reading_does_not_hold(self):
        r, cs = untargeted(self.T); a = record(r, self.T); child = copy.deepcopy(IN['child'])
        child['units'] = [u for u in child['units'] if not any(a['start'] <= s['byte_start'] < a['end'] for x in [u] + list(u.get('cells') or []) for s in ([x['anchor']] if isinstance(x.get('anchor'), dict) else x.get('anchor') or []) if isinstance(s, dict) and 'byte_start' in s)]
        self.assertLess(len(child['units']), len(IN['child']['units']))
        self.assertKept(call(route=r, codes=cs, child=child), 'is held whole by the source reading')

    def test_a_changed_indicator_in_the_reading(self):  # the toggle's own '+ ' indicator text, read as another sign
        r, cs = untargeted(self.T); child = copy.deepcopy(IN['child']); done = False
        for x in (x for u in child['units'] for x in [u] + list(u.get('cells') or [])):
            if not done and '+ References' in (x.get('text') or ''): x['text'] = x['text'].replace('+ References', '- References', 1); done = True
        self.assertTrue(done)  # fixture fact: the popup's revealing toggle text is held as '+ References'
        self.assertKept(call(route=r, codes=cs, child=child), 'is held whole by the source reading')

    def test_a_page_script_that_could_write_last_ar(self):  # hideAR's admission rests on every page script being known: no unknown script passes
        r, cs = untargeted(self.T)
        for c in cs: c['scripts'].append({'url': '', 'sha256': 'f' * 64, 'bytes': 30, 'text': 'Show.LastAR = document.body;'})
        self.assertKept(call(route=r, codes=cs), 'unknown executable code')

    def test_a_changed_renderer_program(self):
        r, cs = untargeted(self.T)
        for c in cs:
            for s in c['scripts']:
                if s['url'] == SHOW_JS: s['sha256'] = 'a' * 64
        self.assertKept(call(route=r, codes=cs), 'unknown executable code')

    def test_an_unrelated_handler_on_the_close_control(self):
        r, cs = untargeted(self.T); n = 0
        for c in cs:
            for x in c['listeners']:
                if (x.get('script') or {}).get('text') == 'Show.hideAR();' and (x.get('relation') or {}).get('outside') is False and not (x.get('relation') or {}).get('ancestor'):
                    x['script'] = dict(x['script'], text='Show.hideAR(); Show.showAR( this, \'defref_other\', window );'); n += 1; break
        self.assertTrue(n)  # fixture fact: each render records a close control's own attribute listener
        self.assertKept(call(route=r, codes=cs), 'not its own declared action')

    def test_no_ok_source_reading(self):
        r, cs = untargeted(self.T)
        self.assertKept(call(route=r, codes=cs, child=dict(IN['child'], status='PARTIAL')), 'no OK typed source reading')


BOT = '39f3dc5b34f614a78075f1824407dc3de33cffcb5e5e3c5fd59a1356d3385d97'  # the recorded CCL bot bytes: 2 no-URL copies, 1 URL copy, 18 listeners, its frames
BOT_URL = next(u for u, o in IN['evidence']['observed'].items() if o.get('sha256') == BOT)
MANIFEST = 'a' * 64


class SingleVersionQualification(unittest.TestCase):  # owner single-version policy: a version nobody reviewed is admitted only by its own record + this file's insertion proof
    def setUp(self):
        import tempfile
        self.saved = dict(context.INFRASTRUCTURE); del context.INFRASTRUCTURE[BOT]  # the recorded bytes play a NEW version (not in the reviewed list)
        self.dir = Path(tempfile.mkdtemp()); self.result = self.dir / 'WITHOUT_RESULT.json'
        self.result.write_text(json.dumps({'rows': [{'outcome': 'verified_saved_output'}]}))
    def tearDown(self):
        import shutil
        context.INFRASTRUCTURE.clear(); context.INFRASTRUCTURE.update(self.saved); shutil.rmtree(self.dir)
    def record(self, **over):  # the producer's own record (TVQ.make_record), then optionally altered by hand
        import os
        rec, self.arms = TVQ.make_record(self.dir, self.dir, BOT, BOT_URL, MANIFEST); q = self.dir / (BOT + '.json')
        if over: os.chmod(q, 0o644); d = json.loads(q.read_bytes()); d.update(over); q.write_text(json.dumps(d))
        return rec
    def ev(self, href=BOT_URL, sha=BOT, manifest=MANIFEST, inserted=True):
        e = copy.deepcopy(IN['evidence']); e['qualifications'] = {'folder': str(self.dir), 'runtime_manifest_sha256': manifest}
        if inserted: e['inserted_script'] = {'href': href, 'response_sha256': sha}
        return e
    def assertKept(self, got, part):
        why, _ = got; self.assertTrue(why, 'the deficit must stay'); self.assertTrue(any(part in w for w in why), why)

    def test_a_new_version_without_a_record_stays_held(self):  # the real current behaviour for the 11 files
        self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_a_passed_record_and_this_files_insertion_proof_admit_it(self):
        self.record(); why, facts = call(evidence=self.ev()); self.assertEqual(why, []); self.assertEqual(facts['qualified_versions'], [BOT])
    def test_a_record_for_other_bytes_does_not_admit(self):
        self.record(script_sha256='b' * 64); self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_without_this_files_insertion_proof_a_record_does_not_admit(self):
        self.record(); self.assertKept(call(evidence=self.ev(inserted=False)), 'unknown executable code')
    def test_an_insertion_proof_of_another_address_does_not_admit(self):
        self.record(); self.assertKept(call(evidence=self.ev(href='https://www.sec.gov/other/x')), 'unknown executable code')
    def test_an_insertion_proof_of_other_bytes_does_not_admit(self):
        self.record(); self.assertKept(call(evidence=self.ev(sha='c' * 64)), 'unknown executable code')
    def test_a_record_from_another_runtime_is_stale(self):
        self.record(); self.assertKept(call(evidence=self.ev(manifest='d' * 64)), 'unknown executable code')
    def test_a_held_record_does_not_admit(self):
        self.record(outcome='held'); self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_evidence_changed_after_recording_does_not_admit(self):
        self.record(); w = self.arms[2] / 'RESULT.json'; d = json.loads(w.read_bytes()); d['rows'][0]['outcome'] = 'incomplete'; w.write_text(json.dumps(d))
        self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_a_record_naming_no_evidence_does_not_admit(self):
        self.record(evidence=[]); self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_a_forged_flag_over_unverified_evidence_does_not_admit(self):  # the WITHOUT result made unverified and the record re-pinned by hand: still refused
        import hashlib
        self.record(); w = self.arms[2] / 'RESULT.json'; d = json.loads(w.read_bytes()); d['rows'][0]['outcome'] = 'incomplete'; w.write_text(json.dumps(d))
        rec = json.loads((self.dir / (BOT + '.json')).read_bytes()); ev = [dict(e, sha256=hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()) for e in rec['evidence']]
        import os; q = self.dir / (BOT + '.json'); os.chmod(q, 0o644); q.write_text(json.dumps(dict(rec, evidence=ev)))
        self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_a_record_whose_comparison_did_not_hold_does_not_admit(self):
        self.record(comparison={'all_equal': False}); self.assertKept(call(evidence=self.ev()), 'unknown executable code')
    def test_a_mismatched_recorded_response_is_held(self):
        self.record(); e = self.ev(); e['observed'][BOT_URL]['sha256'] = 'e' * 64; self.assertKept(call(evidence=e), 'not the recorded response')
    def test_button_damage_is_still_held_with_an_admitted_version(self):
        self.record(); self.assertKept(call(evidence=self.ev(), codes=codes(lambda c: c['actions']['actions'].pop())), 'differ from the native declarations')
    def test_a_reviewed_version_without_this_files_insertion_proof_is_held(self):  # no unconditional legacy-hash path
        context.INFRASTRUCTURE[BOT] = self.saved[BOT]; self.assertKept(call(evidence=copy.deepcopy(IN['evidence'])), 'unknown executable code')
    def test_a_reviewed_version_proved_at_another_address_is_held(self):
        context.INFRASTRUCTURE[BOT] = self.saved[BOT]; e = copy.deepcopy(AUGMENTED_EVIDENCE); e['inserted_script']['href'] = 'https://www.sec.gov/other/x'
        self.assertKept(call(evidence=e), 'unknown executable code')
    def test_a_reviewed_version_with_proof_but_no_record_is_held(self):  # no grandfathered approval: the same qualification as a new version
        context.INFRASTRUCTURE[BOT] = self.saved[BOT]; e = copy.deepcopy(AUGMENTED_EVIDENCE); e.pop('qualifications'); self.assertKept(call(evidence=e), 'unknown executable code')
    def test_the_reviewed_versions_pass_with_their_record_and_proof(self):  # the augmented default: this file's proof + the producer's record
        context.INFRASTRUCTURE[BOT] = self.saved[BOT]; why, _ = call(); self.assertEqual(why, [])


if __name__ == '__main__':
    unittest.main()
