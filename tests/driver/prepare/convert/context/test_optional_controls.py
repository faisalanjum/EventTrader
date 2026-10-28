"""context.optional_controls on the recorded public CCL R2 initial view: one actual caller run's own inputs (fixture public_ccl_r2_optional_controls:
the member bytes, the displayed route's fields, the source child, the three initial renders' native code inventories, the recorded evidence).
The recorded positive qualifies; each damage keeps the deficit with its own reason. Decision level, no browser: Scope.code itself and the caller
path ran in the recorded caller runs named in the fixture. The damaged-text case is one the job's reconstruct/verify gate alone does not catch."""
import copy, json, re, unittest
from pathlib import Path
from driver.prepare.convert import context

FX = Path(__file__).with_name('fixtures') / 'public_ccl_r2_optional_controls'
RAW, PARENT, IN = (FX / 'R2.htm').read_bytes(), (FX / 'parent.html').read_bytes(), json.loads((FX / 'inputs.json').read_bytes())
SHOW_JS = 'https://www.sec.gov/include/Show.js'


def call(route=None, codes=None, child=None, sr=None, evidence=None, parent=None):
    r = copy.deepcopy(route if route is not None else IN['route']); r['facts'] = {'source_reading': copy.deepcopy(sr if sr is not None else IN['route_facts_source_reading'])}
    ev = copy.deepcopy(evidence if evidence is not None else IN['evidence']); ev['observed'][ev['parent_url']]['body'] = PARENT if parent is None else parent
    recs = [({'code': c} if c is not None else {}) for c in copy.deepcopy(codes if codes is not None else IN['codes'])]  # None: a render with no inventory
    return context.optional_controls(RAW, r, recs, ev, copy.deepcopy(child if child is not None else IN['child']))


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
        def f(c): c['actions']['actions'][[i for i, (v, _) in enumerate(c['actions']['actions']) if 'showAR' in v][0]][1] = True
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
        cs = copy.deepcopy(IN['codes']); a = cs[2]['actions']['actions']; a[[k for k, (v, _) in enumerate(a) if 'showAR' in v][0]][1] = True
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

    def test_hide_or_toggle_outside_every_held_target(self):
        r = copy.deepcopy(IN['route']); inner = [l for l in r['source_links'] if l.get('script_action') and 'showAR' not in l['declarations'][0]['value']]
        if not inner: self.skipTest('fixture has no hide/toggle control')
        inner[0]['tag'] = {'byte_start': 0, 'byte_end_exclusive': 1}
        self.assertKept(call(route=r), 'outside every held target')


if __name__ == '__main__':
    unittest.main()
