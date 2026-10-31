"""One observed parent start, replayed before target bytes and all source actions.

The accordion and jQuery are exact frozen public assets. All report content and
startup schedules are invented. Expected text and graph size come from this
fixture's one reveal and one same-target replacement, independently of replay.
"""
import hashlib
import json
import copy
import os
from pathlib import Path
import unittest
from .cases import context, sg, evidence, obs, rep, PARENT_UI, PARENT, TARGET, ROOT, controls
from driver.prepare.get import acquisition

ACCORDION = (Path(__file__).parents[2] / 'fixtures/invented_version_qualification/accordionMenu.js').read_bytes()
VIEWER_CSS = (Path(__file__).parents[2] / 'fixtures/invented_version_qualification/xbrlViewerStyle.css').read_bytes()
CHILD = b'''<section><a href="javascript:void(0)" onclick="MuseumCards.reveal(this,'note')">Show</a><aside id="note" style="display:none"><p>42 widgets</p></aside></section>'''
MENU = b'''<nav><ul id="menu"><li><a href="#">First category</a><ul id="first-category"><li><a class="xbrlviewer" id="open-welcome" href="javascript:void(0)" onclick="chooseSheet('welcome')">Introduction</a></li></ul></li><li><a href="#">Second category</a><ul><li><a class="xbrlviewer" id="open-board" href="javascript:void(0)" onclick="chooseSheet('board')">Report</a></li></ul></li></ul></nav>'''
PARENT_MENU = PARENT_UI[:PARENT_UI.index(b'<nav>')] + MENU + PARENT_UI[PARENT_UI.index(b'</nav>') + 6:]
PARENT_MENU = rep(PARENT_MENU, b'</head>', b'<script src="/shared/accordion.js"></script><link rel="stylesheet" href="/shared/viewer.css"></head>')
PARENT_MENU = rep(PARENT_MENU, b'return jQuery.ajax', b'document.getElementById(choice === "welcome" ? "open-welcome" : "open-board").parentNode.parentNode.style.display = "block"; return jQuery.ajax')


def marked(raw):
    p = sg.marker_prefix(raw); vis = sg.Visible(raw); runs, _ = sg.symbol_runs(raw, vis)
    return sg.tag_cells(raw, vis, (), [(a, b'<!--%ss:%d-->' % (p.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], p)[0]


class Scheduled:
    """Change only the fixture's settled start; never adjust after Context acts."""
    def __init__(self, browser, states, change=None):
        self.browser, self.states, self.change, self.count = browser, list(states), change, 0
    def is_connected(self): return self.browser.is_connected()
    def new_context(self, **kw): return self.browser.new_context(**kw)  # native declaration-only readers do not navigate the parent
    def new_page(self, **kw):
        page = self.browser.new_page(**kw); state = self.states[min(self.count, len(self.states) - 1)]; self.count += 1
        inflight = acquisition.count_requests(page); goto = page.goto
        def start(*args, **kwargs):
            result = goto(*args, **kwargs)
            if not acquisition.quiet_settle(page, inflight, 3): raise RuntimeError('fixture startup did not settle')
            page.evaluate("s => document.getElementById('first-category').style.display = s", state)
            if self.change: self.change(page, state)
            return result
        page.goto = start
        return page


class ViewerStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def ev(self, parent=PARENT_MENU, child=CHILD):
        ev = evidence(parent=parent, child=child); ev['observed'][ROOT + '/shared/accordion.js'] = obs(ACCORDION, 'application/javascript')
        ev['observed'][ROOT + '/shared/viewer.css'] = obs(VIEWER_CSS, 'text/css')  # exact native menu CSS: default browser bullets are not report content
        selector = acquisition.NativeSelection(PARENT, ev['observed'], TARGET, child, marked(child), sg.marker_prefix(child), offline=True)
        selector.prepare(self.browser)
        index, = [i for i, text in enumerate(selector.texts) if text == 'Report']
        path, tags, digest = selector.nodes[index]
        ev['selection'] = {'native_node': {'path': path, 'tags': tags, 'outer_html_sha256': digest},
                           'state_inputs': {k: selector.state_facts[k] for k in ('delivered', 'refused_get')}}
        return ev

    def read(self, ctx, browser, body=None):
        raw = ctx.evidence['observed'][TARGET]['body']; body = raw if body is None else body
        src = context.state_source(sg.Source('child.html', {'child.html': raw}), ctx.evidence, ctx)
        page = ctx.page(browser, None, ('https://trial.invalid/', body), src)
        try:
            page.goto('reading')
            return None, page.locator('#report-host').inner_text()
        except context.Refused as error: return str(error), None
        finally: page.close()

    def test_closed_original_is_restored_without_changing_the_reference(self):
        ev = self.ev(); ctx = context.Context(ev); browser = Scheduled(self.browser, ['none', 'block'])
        first = self.read(ctx, browser); reference = json.loads(json.dumps(ctx.reference))
        second = self.read(ctx, browser, marked(CHILD))
        self.assertEqual((first, second, ctx.gate()), ((None, 'Show'), (None, 'Show'), []))
        self.assertEqual(ctx.reference, reference)
        self.assertEqual(ctx.records[1]['native'], reference)
        self.assertEqual(len(ctx.records[1]['attempts']), 1)

    def test_matching_closed_start_has_no_extra_action(self):
        ctx = context.Context(self.ev()); browser = Scheduled(self.browser, ['none'])
        self.assertEqual(self.read(ctx, browser), (None, 'Show'))
        self.assertEqual(self.read(ctx, browser, marked(CHILD)), (None, 'Show'))
        self.assertEqual(ctx.gate(), [])
        self.assertEqual(ctx.records[1]['viewer_actions'], [])

    def test_open_original_is_restored_by_its_bound_handler(self):
        ctx = context.Context(self.ev()); br = Scheduled(self.browser, ['block', 'none'])
        self.assertEqual(self.read(ctx, br), (None, 'Show')); original = copy.deepcopy(ctx.reference)
        self.assertEqual(self.read(ctx, br, marked(CHILD)), (None, 'Show'))
        self.assertEqual((ctx.reference, ctx.records[1]['native'], ctx.gate()), (original, original, []))
        self.assertEqual(len(ctx.records[1]['viewer_actions']), 1)

    def test_original_initial_selection_keeps_its_prior_path(self):
        ev = self.ev(); ev['selection'] = {'initial': True}; ctx = context.Context(ev)
        br = Scheduled(self.browser, ['none'], lambda p, _: p.evaluate("chooseSheet('board')"))
        self.assertEqual(self.read(ctx, br), (None, 'Show'))
        self.assertEqual(self.read(ctx, br, marked(CHILD)), (None, 'Show'))
        self.assertEqual(ctx.gate(), []); self.assertIsNone(ctx.viewer_start)

    def seed(self, ev=None, state='none'):
        ctx = context.Context(ev or self.ev()); self.assertEqual(self.read(ctx, Scheduled(self.browser, [state])), (None, 'Show'))
        return ctx, json.loads(ctx.viewer_start)

    def test_plan_is_detached_from_its_saved_record(self):
        ctx, plan = self.seed(); ctx.records[0]['viewer_start']['controls'][0]['closed'] = False
        self.assertEqual(json.loads(ctx.viewer_start), plan)

    def test_plan_binding_rejects_changed_control_inputs_and_source(self):
        original, plan = self.seed()
        edits = [lambda p: p.update(source_sha256='0' * 64), lambda p: p.update(parent_sha256='0' * 64),
                 lambda p: p['controls'][0]['native_node'].update(outer_html_sha256='0' * 64),
                 lambda p: p['controls'][0].update(closed='false'), lambda p: p['controls'].pop(), lambda p: p['received'].pop()]
        for edit in edits:
            with self.subTest(edit=edits.index(edit)):
                bad = copy.deepcopy(plan); edit(bad); ctx = context.Context(original.evidence, viewer_start=bad)
                error, _ = self.read(ctx, Scheduled(self.browser, ['block']))
                self.assertIn('viewer start: original parent, input or control binding differs', error)
                self.assertIsNone(ctx.reference)

    def test_unsupported_shapes_keep_the_existing_strict_path(self):
        changes = ["document.getElementById('menu').id = 'other'", "document.querySelector('#menu > li > a').nextElementSibling.remove()",
                   "jQuery('#menu > li > a').first().on('click', function(){})", "jQuery('#menu > li').first().clone(true).appendTo('#menu')"]
        for script in changes:
            with self.subTest(script=script):
                ctx = context.Context(self.ev()); br = Scheduled(self.browser, ['none'], lambda p, _: p.evaluate("() => {" + script + "}"))
                self.assertEqual(self.read(ctx, br), (None, 'Show'))
                self.assertIsNone(ctx.viewer_start)
                self.assertEqual(self.read(ctx, br, marked(CHILD)), (None, 'Show'))

    def test_target_already_loaded_and_initial_selection_never_replay(self):
        original, plan = self.seed()
        for initial in (False, True):
            ev = copy.deepcopy(original.evidence)
            if initial: ev['selection'] = {'initial': True}
            ctx = context.Context(ev, viewer_start=plan)
            br = Scheduled(self.browser, ['block'], lambda p, _: p.evaluate("chooseSheet('board')"))
            error, _ = self.read(ctx, br)
            self.assertIn('viewer start: target already requested or no recorded native selection', error)
            self.assertFalse(any(r.get('viewer_actions') for r in ctx.records))

    def test_marked_first_cannot_establish_a_plan_or_reference(self):
        ctx = context.Context(self.ev()); error, _ = self.read(ctx, Scheduled(self.browser, ['none']), marked(CHILD))
        self.assertIn('no state reference', error); self.assertIsNone(ctx.reference); self.assertIsNone(ctx.viewer_start)

    def test_a_later_supported_render_cannot_attach_a_start_plan(self):
        ctx = context.Context(self.ev())
        first = Scheduled(self.browser, ['none'], lambda p, _: p.evaluate("() => { jQuery('#menu > li > a').first().on('click', function(){}); }"))
        self.assertEqual(self.read(ctx, first), (None, 'Show')); self.assertIsNone(ctx.viewer_start)
        self.assertEqual(self.read(ctx, Scheduled(self.browser, ['none']), marked(CHILD)), (None, 'Show'))
        self.assertIsNone(ctx.viewer_start)
        self.assertFalse(any('viewer_start' in r for r in ctx.records))

    def test_preparation_history_is_accepted_only_with_the_original_output(self):
        # A hidden counter alone is allowed. A changed required source label is
        # independently wrong ("Show" is the fixture source), even if caused by
        # the extra viewer click before the marked target exists.
        count = "jQuery.fx.step.height = function(){ delete jQuery.fx.step.height; window.viewerClicks = (window.viewerClicks || 0) + 1; }"
        for damage in (False, True):
            with self.subTest(damage=damage):
                parent = PARENT_MENU
                if damage: parent = rep(parent, b"jQuery('#report-host').empty().append(data);", b"jQuery('#report-host').empty().append(data); if(window.viewerClicks && choice === 'board') document.querySelector('#report-host a').textContent = 'Wrong';")
                ctx = context.Context(self.ev(parent=parent)); br = Scheduled(self.browser, ['none', 'block'], lambda p, _: p.evaluate("() => {" + count + "}"))
                self.assertEqual(self.read(ctx, br), (None, 'Show'))
                error, text = self.read(ctx, br, marked(CHILD))
                if damage: self.assertIn('differs from the state reference', error)
                else: self.assertEqual((error, text, ctx.gate()), (None, 'Show', []))

    def test_new_target_dependency_window_and_script_error_fail_closed(self):
        original, plan = self.seed()
        actions = [("chooseSheet('board')", 'category action requested the target'),
                   ("fetch('/new-required-input').catch(() => {})", 'request during the category action'),
                   ("fetch('/post-only', {method:'POST', body:'x'}).catch(() => {})", 'request during the category action'),
                   ("window.open('/new-window')", 'navigation, new page or script error')]
        for action, expected in actions:
            with self.subTest(action=action):
                script = "jQuery.fx.step.height = function(){ delete jQuery.fx.step.height; " + action + " }"
                ctx = context.Context(original.evidence, viewer_start=plan)
                error, _ = self.read(ctx, Scheduled(self.browser, ['block'], lambda p, _: p.evaluate("() => {" + script + "}")))
                self.assertIn(expected, error); self.assertIsNone(ctx.reference)

    def test_synchronous_handler_fault_propagates_without_a_retry(self):
        from playwright.sync_api import Error
        original, plan = self.seed(); ctx = context.Context(original.evidence, viewer_start=plan)
        script = "() => { jQuery.fx.step.height = function(){ delete jQuery.fx.step.height; throw new Error('viewer failure'); }; }"
        with self.assertRaisesRegex(Error, 'viewer failure'):
            self.read(ctx, Scheduled(self.browser, ['block'], lambda p, _: p.evaluate(script)))
        self.assertIsNone(ctx.reference); self.assertEqual(len(ctx.records[0]['attempts']), 1)

    def test_one_preparation_precedes_the_entire_outer_and_inner_sequence(self):
        original, plan = self.seed(); control, = controls(CHILD)
        ctx = context.Context(original.evidence, control=(control, control), viewer_start=plan)
        br = Scheduled(self.browser, ['block'])
        for body in (CHILD, marked(CHILD)):
            error, text = self.read(ctx, br, body)
            self.assertIsNone(error); self.assertIn('42 widgets', text)
        self.assertEqual(ctx.gate(), [])
        for r in ctx.records:
            self.assertEqual(len(r['viewer_actions']), 1)
            self.assertEqual(len(r['inner']), 1)
            self.assertEqual(r['final_controls'], [{'label': 'Show', 'shown': True}])  # the later source control's label, once; the first reveal is proved separately
            self.assertTrue(r['proof']); self.assertTrue(r['inner'][0]['replacement'])
            self.assertTrue(all(q[0] == 'selection' for q in r['requests'] if q[2] == TARGET))

    def test_whole_graph_uses_one_original_start_under_both_schedules(self):
        original, plan = self.seed(); control, = controls(CHILD); label = 'activated@' + str(control)
        for states in (['none', 'block'], ['block', 'none']):
            with self.subTest(states=states):
                res = context.contextual_routes(CHILD, 'invented/child', hashlib.sha256(CHILD).hexdigest(), Scheduled(self.browser, states),
                        sg.Source('child.html', {'child.html': CHILD}), original.evidence, viewer_start=plan)
                if os.environ.get('VIEWER_TEST_OUTPUT'):
                    folder = Path(os.environ['VIEWER_TEST_OUTPUT']); folder.mkdir(parents=True, exist_ok=True)
                    with (folder / ('GRAPH_' + '_'.join(states) + '.json')).open('x') as f: json.dump({k: v for k, v in res.items() if k != 'trial_captures'}, f, indent=2)
                self.assertEqual([s['label'] for s in res['states']], [label])
                self.assertTrue(all(s['route']['text_proved'] for s in res['states']), [(s['label'], s['route'].get('error')) for s in res['states']])
                graph = res['initial']['source_links'][0]['activations'][0]['state_graph']
                self.assertEqual((graph['frontier'], graph['unexpanded'], graph['refused']), ([], [], 0))
                self.assertEqual([e['kind'] for e in graph['edges']], ['equal state'])
                self.assertTrue(all(not t.get('refused') for t in res['trials']))

    def test_preparation_does_not_dispatch_ancestor_or_other_dom_listeners(self):
        parent = rep(PARENT_MENU, b"jQuery('#report-host').empty().append(data);", b"jQuery('#report-host').empty().append(data); if(window.unwantedClick && choice === 'board') document.querySelector('#report-host a').textContent = 'Wrong';")
        extra = "window.addEventListener('click', e => { if(e.target.matches('#menu > li > a[href=\"#\"]')) { window.unwantedClick = true; fetch('/post-only', {method:'POST'}).catch(() => {}); }}, true)"
        ctx = context.Context(self.ev(parent=parent)); br = Scheduled(self.browser, ['none', 'block'], lambda p, _: p.evaluate(extra))
        self.assertEqual(self.read(ctx, br), (None, 'Show'))
        self.assertEqual(self.read(ctx, br, marked(CHILD)), (None, 'Show'))
        self.assertEqual(ctx.gate(), [])
        self.assertFalse(any(q[0] == 'viewer start' for r in ctx.records for q in r['requests']))

    def test_unknown_dom0_or_spoofed_category_callback_is_not_supported(self):
        original, plan = self.seed()
        unknown = ["document.querySelector('#menu > li > a').onclick = () => { window.didRun = true; }",
                   "jQuery._data(document.querySelector('#menu > li > a'), 'events').click[0].handler = function(){ window.didRun = true; }; Function.prototype.toString = () => \"function(){$(this).next().slideToggle('normal')}\"",
                   "jQuery.fn.slideToggle = function(){ window.didRun = true; }",
                   "window.$ = (...args) => { window.didRun = true; return jQuery(...args); }"]
        for script in unknown:
            with self.subTest(script=script):
                ctx = context.Context(original.evidence, viewer_start=plan)
                error, _ = self.read(ctx, Scheduled(self.browser, ['block'], lambda p, _: p.evaluate("() => {" + script + "}")))
                self.assertIn('viewer start:', error); self.assertIsNone(ctx.reference)


if __name__ == '__main__': unittest.main()
