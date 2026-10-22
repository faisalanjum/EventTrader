"""Native-node selection through the shared seam (port of context_candidate/tests/test_native_selection.py; public invented fixture).
The parent builds its menu links by script, so no parent source anchor corresponds: context_acquire._select's source-anchor pass finds none and
its native fallback qualifies one observed control (NativeSelection key: path, tag chain, outerHTML sha256, plus the recorded state's inputs).
The declared Context selection is derived from that actual native result exactly as acquire_context derives it. Negatives: another path,
another outerHTML, other inputs, a duplicated control (ambiguous)."""
import copy, json, tempfile, unittest
from .cases import context, sg, evidence, rep, ANON, PARENT_UI, PNG, controls, activations, hashlib
from . import cases as _cases
BUTTON = getattr(_cases, 'BUTTON', 'context: 1 declared event handler(s) outside the supported link path (not activated)')  # test_context_states.py's exact constant unless cases.py defines it
NAV = PARENT_UI[PARENT_UI.index(b'<nav>') + 5:PARENT_UI.index(b'</nav>')]
BUILD = (b"<script>(function () { var nav = document.querySelector('nav'); [['open-welcome', 'welcome', 'Portal introduction'], ['open-board', 'board', 'Open visitor board']]"
         b".forEach(function (x) { var a = document.createElement('a'); a.id = x[0]; a.href = 'javascript:void(0)'; a.setAttribute('onclick', \"chooseSheet('\" + x[1] + \"')\");"
         b" a.textContent = x[2]; nav.appendChild(a); }); })();</script>")
SCRIPTED = rep(PARENT_UI, b'<nav>' + NAV + b'</nav>', b'<nav></nav>' + BUILD)
DUPLICATED = rep(SCRIPTED, b"['open-board', 'board', 'Open visitor board']]", b"['open-board', 'board', 'Open visitor board'], ['open-board', 'board', 'Open visitor board']]")


def select(browser, ev):  # the shared seam's own selection on the fixture's recorded responses (no network: an offline Campaign, nothing requested)
    from driver.prepare.get.campaign import Campaign
    from driver.prepare.get.context_acquire import _Fetcher, _select
    from driver.prepare.convert import overlay
    vis = sg.Visible(ANON); runs, _ = sg.symbol_runs(ANON, vis); p = sg.marker_prefix(ANON)
    marked = sg.tag_cells(ANON, vis, (), [(a, b'<!--%ss:%d-->' % (p.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], p)[0]
    body, _ = overlay.measurement_body(ev['observed'][ev['target_url']]['body'], ANON, marked, p, ev['proof'])
    with tempfile.TemporaryDirectory() as d, Campaign(d, live=False, minimum_free_bytes=0) as campaign:
        fetch = _Fetcher(campaign, 80); fetch.observed.update(ev['observed'])
        r, s = _select(fetch, browser, ev['parent_url'], ev['target_url'], ANON, body, p, 200)
        sent = campaign.sent_attempts
    return r, s, sent


def declared(r, s):  # acquire_context's own derivation of the Context selection from a native result
    i = next(a['source_anchor'] for a in r['attempts'] if a['state'] == 'qualified')
    return {'native_node': {'path': s.nodes[i][0], 'tags': s.nodes[i][1], 'outer_html_sha256': s.nodes[i][2]},
            'state_inputs': {'delivered': s.state_facts['delivered'], 'refused_get': s.state_facts['refused_get']}}


def render(browser, ev):  # one Context render of the initial view: (error, gate reasons)
    ctx = context.Context(ev); src = context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx); page = err = None
    try:
        page = ctx.page(browser, None, ('https://trial.invalid/', ANON), src); page.goto('trial')
    except Exception as e:
        err = repr(e)[:300]
    finally:
        if page is not None: page.close()
    return err, ctx.gate()


class NativeSelectionReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.ev = evidence(child=ANON, parent=SCRIPTED); cls.r, cls.s, cls.sent = select(cls.browser, cls.ev)
        cls.sel = declared(cls.r, cls.s) if cls.r['verdict'] == 'selected' else None; cls.ev['selection'] = cls.sel
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_source_anchors_find_nothing_native_node_selected(self):
        self.assertEqual(self.sent, 0)
        self.assertEqual(self.r['kind'], 'native_node', self.r.get('verdict'))
        self.assertEqual(self.r['closure'][0]['source_anchor_result']['verdict'], 'missing')
        self.assertEqual(self.r['verdict'], 'selected', self.r.get('unobserved'))
        self.assertIn('native_node', self.sel); self.assertNotIn('source_anchor', self.sel)

    def test_states_complete_through_the_replayed_native_control(self):
        res = context.contextual_routes(ANON, 'invented/child.html', hashlib.sha256(ANON).hexdigest(), self.browser,
                                        sg.Source('child.html', {'child.html': ANON, 'plan.png': PNG}), self.ev)
        self.assertEqual((res['initial']['status'], res['initial'].get('error')), ('PARTIAL', BUTTON))  # the fixture's own unsupported button (Root CONTEXT_DECLARED_ACTION_BOUNDARY_20261022)
        self.assertEqual([activations(res, s)[0]['status'] for s in controls(ANON)], ['complete', 'complete'])

    def negative(self, change, why, parent=None):
        ev = evidence(child=ANON, parent=parent or SCRIPTED); ev['selection'] = sel = copy.deepcopy(self.sel); change(sel)
        err, reasons = render(self.browser, ev); self.assertIsNotNone(err); self.assertIn(why, json.dumps(reasons))
    def test_other_path_refused(self): self.negative(lambda s: s['native_node'].__setitem__('path', s['native_node']['path'][:-1] + [s['native_node']['path'][-1] + 1]), 'another path')
    def test_other_outer_html_refused(self): self.negative(lambda s: s['native_node'].__setitem__('outer_html_sha256', '0' * 64), 'matches 0 nodes')
    def test_other_inputs_refused(self): self.negative(lambda s: s['state_inputs']['delivered'].append(['https://museum.invalid/extra.css', 200, '0' * 64]), 'different inputs')
    def test_duplicated_control_ambiguous(self):  # inputs otherwise equal (the recorded parent identity is this parent's), so only the node key decides
        dup = hashlib.sha256(DUPLICATED).hexdigest(); parent = evidence()['parent_url']
        self.negative(lambda s: s['state_inputs'].__setitem__('delivered', [[u, st, dup if u == parent else h] for u, st, h in s['state_inputs']['delivered']]), 'matches 2 nodes', parent=DUPLICATED)
