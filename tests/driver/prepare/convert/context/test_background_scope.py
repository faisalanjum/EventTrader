"""Background-image ownership in a context state (Root PRODUCTION_BACKGROUND_SCOPE_IMPLEMENT_20261022T1906; invented public fixtures cases.PARENT_UI /
cases.ANON; written before the candidate code). A visible background picture owes 'background image content not read' unless its painting element
is proved to be the parent's and holds none of the member. Expected outcomes come from each fixture's own authored source: which document's node
paints the picture, and what that node contains."""
import hashlib, unittest
from .cases import context, sg, evidence, rep, ANON, PARENT_UI, PNG
from driver.prepare.convert import html_route

I = 'background image content not read'
PIC = b'width:120px;height:30px;background-image:url(/portal/plan.png)'
MAST = b'<div id="masthead" style="' + PIC + b'"></div>'  # the parent's own header picture (the R2 shape)
MEMBER_BG = b'<div id="paper" style="width:16px;height:16px;background-image:url(plan.png)"></div>'  # the member's own picture (test_local_text_proof's BG)
AT_START = (b"window.onload = function() { chooseSheet('welcome'); };", b"window.onload = function() { chooseSheet('board'); };")  # the target is the parent's initial selection


def parent_with(*edits):
    p = PARENT_UI
    for a, b in edits: p = rep(p, a, b)
    return p
def route(browser, parent=PARENT_UI, child=ANON, initial=False, context_on=True):  # one state extraction, as contextual_routes' `one` makes it (html_route.prepare)
    members = {'child.html': child, 'plan.png': PNG}; src = sg.Source('child.html', members)
    if context_on:
        ev = evidence(child=child, parent=parent)
        if initial: ev['selection'] = {'initial': True}
        src = context.state_source(src, ev, context.Context(ev))
    r, _ = html_route.prepare(child, 'invented/child.html', hashlib.sha256(child).hexdigest(), browser, src)
    return r['generated_content']
def owes(g): return I in g.get('why', [])
def raw(g, node=None): return [x for x in g.get('background_images') or [] if node is None or x['node'] == node]


class BackgroundScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_parent_only_picture_owes_nothing_selected_path(self):
        g = route(self.browser, parent_with((b'<body><nav>', b'<body>' + MAST + b'<nav>')))
        self.assertFalse(owes(g), g.get('why')); self.assertEqual([x.get('outside_source_scope') for x in raw(g)], [True])  # kept raw, proved outside
    def test_member_picture_still_owed_selected_path(self):
        g = route(self.browser, parent_with((b'<body><nav>', b'<body>' + MAST + b'<nav>')), child=rep(ANON, b'<section id="native-note">', MEMBER_BG + b'<section id="native-note">'))
        self.assertTrue(owes(g), g.get('why')); self.assertEqual(sorted(str(x.get('outside_source_scope')) for x in raw(g)), ['False', 'True'])
    def test_parent_stylesheet_painting_member_still_owed(self):
        g = route(self.browser, parent_with((b'</head>', b'<style>#report-host p { background-image: url(/portal/plan.png); }</style></head>')))
        self.assertTrue(owes(g), g.get('why')); self.assertTrue(raw(g) and all(x.get('outside_source_scope') is False for x in raw(g)))
    def test_member_pseudo_picture_still_owed(self):
        g = route(self.browser, parent_with((b'</head>', b'<style>#report-host p::before { content: ""; display: inline-block; width: 8px; height: 8px; background-image: url(/portal/plan.png); }</style></head>')))
        self.assertTrue(owes(g), g.get('why')); self.assertTrue(raw(g) and all('outside_source_scope' not in x for x in raw(g)))  # a pseudo element is never exempted
    def test_parent_ancestor_painting_behind_member_still_owed(self):
        g = route(self.browser, parent_with((b'</head>', b'<style>#report-host { min-height: 30px; background-image: url(/portal/plan.png); }</style></head>')))
        self.assertTrue(owes(g), g.get('why')); self.assertEqual([x.get('outside_source_scope') for x in raw(g, 'DIV')], [False])  # a parent node holding member nodes
    def test_initial_path_parent_only_and_member_picture(self):
        start = parent_with(AT_START, (b'<body><nav>', b'<body>' + MAST + b'<nav>'))
        g = route(self.browser, start, initial=True); self.assertFalse(owes(g), g.get('why'))
        g = route(self.browser, start, child=rep(ANON, b'<section id="native-note">', MEMBER_BG + b'<section id="native-note">'), initial=True); self.assertTrue(owes(g), g.get('why'))
    def test_member_inserted_before_domcontentloaded_still_owed(self):  # boundary adequacy: the initial path's parent set is the parse-time snapshot
        early = parent_with((b'<div id="report-host"></div><script>', b'<div id="report-host"></div><script>(function () { var x = new XMLHttpRequest(); x.open("GET", "/bundle/item.html", false); x.send(); document.getElementById("report-host").innerHTML = x.responseText; })();'),
                            (AT_START[0], b"window.onload = function() {};"))
        g = route(self.browser, early, child=rep(ANON, b'<section id="native-note">', MEMBER_BG + b'<section id="native-note">'), initial=True)
        self.assertTrue(owes(g), (g.get('why'), raw(g)))
    def test_page_reassigned_predicate_still_owed(self):  # OCR's class: the scope predicate is a page-writable global read at measurement
        clob = parent_with((b'</head>', b'<script>setInterval(function () { window.__sourceScope = {outside: function () { return true; }}; }, 5);</script></head>'))
        g = route(self.browser, clob, child=rep(ANON, b'<section id="native-note">', MEMBER_BG + b'<section id="native-note">'))
        self.assertTrue(owes(g), (g.get('why'), raw(g)))
    def test_standalone_route_unchanged(self):
        g = route(self.browser, child=rep(ANON, b'<section id="native-note">', MEMBER_BG + b'<section id="native-note">'), context_on=False)
        self.assertTrue(owes(g), g.get('why')); self.assertEqual([x.get('outside_source_scope') for x in raw(g)], [None])  # no scope: unknown, owed
    def test_main_world_predicate_is_never_consulted(self):  # renamed (Root 2012): its purpose - a page-world predicate, even a throwing one, is never asked
        page = self.browser.new_page()
        try:
            page.set_content('<div style="width:20px;height:20px;background-image:url(data:image/gif;base64,R0lGODlhAQABAAAAACw=)"></div><script>window.__sourceScope = {outside: function () { throw new Error("deliberate"); }};</script>')
            got = sg._generated(page, 'zz')['background_images']
        finally: page.close()
        self.assertEqual([x.get('outside_source_scope') for x in got], [None])  # owed
        self.assertEqual(got[0].get('scope_error'), 'no context scope')  # revised (Root 1943 isolated world): a main-world predicate, even a throwing one, is never consulted (v1 pinned cand_bg's main-world error text)

    def test_fallback_control_located_in_the_isolated_scope_stable_vs_reordered(self):  # Root 1946: the fallback decides by node identity in one query
        from .cases import controls
        def located(parent):
            ev = evidence(child=ANON, parent=parent); ctx = context.Context(ev, control=controls(ANON)[0], label='trial')
            src = context.state_source(sg.Source('child.html', {'child.html': ANON, 'plan.png': PNG}), ev, ctx); page = None
            try:
                page = ctx.page(self.browser, None, ('http://trial.invalid/', ANON), src); page.goto('trial')
            except Exception: pass
            finally:
                if page is not None: page.close()
            r = ctx.records[0]; return [a.get('control_located') for a in r.get('attempts', [])] + [r.get('control_located')]
        stable = located(PARENT_UI); self.assertTrue(any(l and l.get('ok') is True and 'isolated' in l.get('how', '') for l in stable), stable)
        moved = located(parent_with((b"jQuery('#report-host').empty().append(data);", b"jQuery('#report-host').empty().append(data); if (choice === 'board') { var as = document.getElementById('report-host').querySelectorAll('a[href]'); as[0].parentNode.insertBefore(as[2], as[0]); }")))
        self.assertFalse(any(l and l.get('ok') is True for l in moved), moved)  # the member's link order no longer matches its source: never located by position


if __name__ == '__main__':
    unittest.main()
