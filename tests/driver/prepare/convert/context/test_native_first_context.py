"""One fully qualified native target context (Root PRODUCTION_NATIVE_SELECTION_IMPLEMENT_20261022; invented public fixture cases.PARENT_UI, written
before the v3 code). The parent's recorded native state holds its own menu (open-welcome, open-board) and, after its startup sheet loads, any
anchors that sheet inserts. open-board loads the target. Expected outcomes come from the fixture's own source and Root's stated contract: the
first fully qualified control is chosen; the action limit caps controls TRIED, never the domain; untried or undecided controls are never absent."""
import hashlib, json, tempfile, unittest
from .cases import context, sg, evidence, rep, obs, ANON, PARENT_UI, ROOT, TARGET, WELCOME, PNG, controls, activations
from driver.prepare.convert import overlay

P = sg.marker_prefix(ANON); _vis = sg.Visible(ANON); _runs, _ = sg.symbol_runs(ANON, _vis)
MARKED = sg.tag_cells(ANON, _vis, (), [(a, b'<!--%ss:%d-->' % (P.encode(), k)) for k, (a, _, _, ok) in enumerate(_runs) if ok], P)[0]
BOARD = b'<a id="open-board" href="javascript:void(0)" onclick="chooseSheet(\'board\')">Open visitor board</a>'
AGAIN = b'<a id="board-again" href="javascript:void(0)" onclick="chooseSheet(\'board\')">Board, again</a>'
LATE = (b'<a id="board-late" href="javascript:void(0)" onclick="chooseSheet(\'board\'); var l = document.createElement(\'link\'); l.rel = \'stylesheet\';'
        b' l.href = \'/portal/late.css\'; document.head.appendChild(l);">Board with a late style</a>')
BUTTON = 'context: 1 declared event handler(s) outside the supported link path (not activated)'


def sheet(n): return rep(WELCOME, b'</section>', b''.join(b'<a href="#note%d">note %d</a>' % (k, k) for k in range(n)) + b'</section>')
def ev_with(parent=PARENT_UI, inserted=0):
    ev = evidence(child=ANON, parent=parent)
    if inserted: ev['observed'][ROOT + '/bundle/welcome.html'] = obs(sheet(inserted), 'text/html')
    return ev
def body(ev): return overlay.measurement_body(ev['observed'][TARGET]['body'], ANON, MARKED, P, ev['proof'])[0]
def seam(browser, ev, max_actions=200, measured=None):  # the shared production seam, offline: nothing requested
    from driver.prepare.get.campaign import Campaign
    from driver.prepare.get.context_acquire import _Fetcher, _select
    with tempfile.TemporaryDirectory() as d, Campaign(d, live=False, minimum_free_bytes=0) as campaign:
        fetch = _Fetcher(campaign, 80); fetch.observed.update(ev['observed'])
        r, s = _select(fetch, browser, ev['parent_url'], TARGET, ANON, measured or body(ev), P, max_actions); sent = campaign.sent_attempts
    return r, s, sent
def qualified(r): return [a['source_anchor'] for a in r.get('attempts', []) if a['state'] == 'qualified']
def states(r): return [a['state'] for a in r.get('attempts', [])]


class NativeFirstContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_domain_over_the_limit_with_an_early_qualified_control(self):  # the CCL shape: the loaded sheet inserts 200 anchors after the menu
        r, _, sent = seam(self.browser, ev_with(inserted=200)); self.assertEqual(sent, 0)
        self.assertEqual((r['verdict'], r.get('kind'), qualified(r)), ('selected', 'native_node', [1]), (r['verdict'], r.get('search')))
        self.assertEqual(r['search'], {'domain': 202, 'tried': 2, 'untried': 200, 'untried_reason': 'stopped at the first fully qualified context'})
        self.assertEqual(r['closure'][0]['search'], r['search'])  # v3.1 (Root 1822): each closure round keeps its own counts

    def test_only_qualified_control_beyond_the_limit_is_incomplete(self):
        r, _, _ = seam(self.browser, ev_with(inserted=3), max_actions=1)
        self.assertTrue(r['verdict'].startswith('incomplete'), r['verdict']); self.assertEqual(qualified(r), [])
        self.assertEqual((r['search']['tried'], r['search']['untried']), (1, 4))

    def test_none_qualifying_full_versus_partial_search(self):
        none = rep(PARENT_UI, BOARD, b'')
        r, _, _ = seam(self.browser, ev_with(parent=none)); self.assertEqual((r['verdict'], r['search']['untried']), ('missing', 0), states(r))  # every control tried and decided
        r, _, _ = seam(self.browser, ev_with(parent=none, inserted=3), max_actions=2)
        self.assertTrue(r['verdict'].startswith('incomplete'), r['verdict']); self.assertEqual(r['search']['untried'], 2)

    def test_duplicate_native_keys_are_undecided_never_missing(self):
        r, _, _ = seam(self.browser, ev_with(parent=rep(PARENT_UI, BOARD, BOARD + b'\n' + BOARD)))
        self.assertTrue(r['verdict'].startswith('incomplete'), (r['verdict'], states(r)))
        self.assertTrue(all(s.startswith('incomplete') and 'matches 2 nodes' in s for s in states(r)[1:3]), states(r))

    def test_two_qualifying_controls_first_chosen_second_untried_both_orders(self):
        for parent, first in ((rep(PARENT_UI, BOARD, BOARD + AGAIN), 1), (rep(PARENT_UI, BOARD, AGAIN + BOARD), 1)):
            r, s, _ = seam(self.browser, ev_with(parent=parent))
            self.assertEqual((r['verdict'], qualified(r), r['search']['untried']), ('selected', [first], 1), states(r))
            self.assertEqual(s.nodes[first][1].split('>')[-1], 'a')

    def test_unresolved_attempt_then_qualified_keeps_its_history(self):
        r, _, _ = seam(self.browser, ev_with(parent=rep(PARENT_UI, BOARD, LATE + BOARD)))
        self.assertTrue(states(r)[1].startswith('incomplete') and 'unresolved' in states(r)[1], states(r))  # requested the target, did not qualify: undecided, kept
        self.assertEqual(qualified(r), [2]); self.assertIn('/portal/late.css', json.dumps(r.get('unobserved')))  # its dependency still reaches the closure

    def test_job_caller_uses_the_same_selector_and_replays(self):
        from driver.prepare import document
        ev = ev_with(inserted=3); sel, summary = document.select(self.browser, {'context': {'evidence': 'invented', 'evidence_sha256': 'invented'}}, ev, ANON, sg, lambda x: None)
        self.assertEqual((summary['by'], summary['verdict'], summary['qualified'], summary['search']['tried']), ('NativeSelection', 'selected', [1], 2), summary)
        self.assertIn('native_node', sel); self.assertNotIn('source_anchor', sel)
        ev['selection'] = {k: v for k, v in sel.items() if k != 'by'}
        res = context.contextual_routes(ANON, 'invented/child.html', hashlib.sha256(ANON).hexdigest(), self.browser, sg.Source('child.html', {'child.html': ANON, 'plan.png': PNG}), ev)
        self.assertEqual((res['initial']['status'], res['initial'].get('error')), ('PARTIAL', BUTTON))
        self.assertEqual([activations(res, x)[0]['status'] for x in controls(ANON)], ['complete', 'complete'])

    def test_unavailable_target_stays_incomplete(self):
        ev = ev_with(inserted=3); measured = body(ev); del ev['observed'][TARGET]
        r, _, sent = seam(self.browser, ev, measured=measured); self.assertEqual(sent, 0); self.assertTrue(r['verdict'].startswith('incomplete'), r['verdict'])

    def test_ordinary_and_initial_selection(self):
        r, _, _ = seam(self.browser, ev_with()); self.assertEqual((r['verdict'], qualified(r)), ('selected', [1]))
        start = rep(PARENT_UI, b"window.onload = function() { chooseSheet('welcome'); };", b"window.onload = function() { chooseSheet('board'); };")
        r, _, _ = seam(self.browser, ev_with(parent=start)); self.assertEqual((r['verdict'], r['attempts']), ('initial', []))
        self.assertEqual((r['search']['tried'], r['search']['untried']), (0, r['search']['domain']))  # v3.1 (Root 1822): initial target success = zero controls tried (v2 wrongly fixed domain 2: the startup target adds its own anchors)

    def test_unqualified_initial_reading_with_controls_is_incomplete(self):  # OCR v3.1 review: a no-action load that only prefetches the target
        pre = rep(PARENT_UI, b"window.onload = function() { chooseSheet('welcome'); };", b"window.onload = function() { chooseSheet('welcome'); jQuery.ajax({url: sheetAddresses.board, dataType: 'text'}); };")
        r, _, _ = seam(self.browser, ev_with(parent=pre)); self.assertTrue(r['verdict'].startswith('incomplete'), r['verdict']); self.assertEqual(r['search']['tried'], 0)


if __name__ == '__main__':
    unittest.main()
