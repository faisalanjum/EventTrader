"""Public native boundary controls; source fixtures and expected cases retained."""
import json, unittest
from .cases import context, sg, evidence, rep, ANON, PARENT_UI, TARGET
SWITCH = (b"<script>var n = +(sessionStorage.getItem('n') || 0); sessionStorage.setItem('n', n + 1); var seq = window.__seq || ['A'];"
          b" if (seq[Math.min(n, seq.length - 1)] === 'B') document.documentElement.className = 'state-b';</script>")
ALT = rep(PARENT_UI, b'</head><body>', b'<style>.state-b #report-host { font-weight: bold; }</style></head><body>' + SWITCH)
vis = sg.Visible(ANON); runs, _ = sg.symbol_runs(ANON, vis); P = sg.marker_prefix(ANON)
MARKED = sg.tag_cells(ANON, vis, (), [(a, b'<!--%ss:%d-->' % (P.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], P)[0]


class Scheduled:  # the test's browser: each new Page carries its declared state sequence, one entry per navigation (attempt)
    def __init__(self, browser, plan): self.b, self.plan = browser, [list(x) for x in plan]
    def new_page(self, **kw):
        page = self.b.new_page(**kw); page.add_init_script('window.__seq = %s;' % json.dumps(self.plan.pop(0))); return page
    def is_connected(self): return self.b.is_connected()


class CanonicalState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def readings(self, plan, bodies, ev=None):  # one state (one Context), one render per body, in order; the caller's goto, then close
        ev = ev or evidence(child=ANON, parent=ALT); ctx = context.Context(ev); src = context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx)
        br, errs = Scheduled(self.browser, plan), []
        for body in bodies:
            page = ctx.page(br, None, ('https://trial.invalid/', body), src)
            try: page.goto('reading'); errs.append(None)
            except Exception as e: errs.append(repr(e)[:300])
            finally: page.close()
        return ctx, errs
    def outcomes(self, rec): return [a['outcome'] for a in rec.get('attempts', [])]

    def test_matching_positive(self):
        ctx, errs = self.readings([['A'], ['A']], [ANON, MARKED])
        self.assertEqual((errs, ctx.gate()), ([None, None], [])); self.assertEqual(self.outcomes(ctx.records[1]), ['used'])

    def test_mismatch_then_match_both_kept(self):
        ctx, errs = self.readings([['A'], ['B', 'A']], [ANON, MARKED]); rec = ctx.records[1]
        self.assertEqual((errs, ctx.gate()), ([None, None], [])); self.assertEqual(rec['native'], ctx.reference)
        self.assertEqual(self.outcomes(rec), ['not used: differs from the state reference (document_sha256, capture)', 'used'])  # B differs in document and pixels
        self.assertIn('startup', rec['attempts'][0]); self.assertTrue(rec['attempts'][0]['requests'])  # the unused attempt's own observation is kept

    def test_exhaustion_leaves_the_reading_incomplete(self):
        ctx, errs = self.readings([['A'], ['B', 'B', 'B']], [ANON, MARKED]); rec = ctx.records[1]
        self.assertIsNotNone(errs[1]); self.assertNotIn('native', rec); self.assertEqual(len(rec['attempts']), 3)
        self.assertIn('no observation attempt equalled the state reference', json.dumps(ctx.gate()))

    def test_alternating_states_no_hybrid(self):  # every used reading is the reference state; the B attempts were really another state
        ctx, errs = self.readings([['A'], ['B', 'A'], ['A'], ['B', 'B', 'A']], [ANON, MARKED, MARKED, MARKED])
        self.assertEqual((errs, ctx.gate()), ([None] * 4, []))
        self.assertTrue(all(r['native'] == ctx.reference for r in ctx.records))
        b = [a for r in ctx.records for a in r['attempts'] if a['outcome'].startswith('not used')]
        self.assertEqual(len(b), 3); self.assertTrue(all(a['native']['document_sha256'] != ctx.reference['document_sha256'] for a in b))

    def test_reference_is_never_changed(self):  # the first completed unmarked observation (B) stays the reference; later A readings never replace it
        ctx, errs = self.readings([['B'], ['A', 'A', 'A']], [ANON, MARKED]); ref = ctx.reference
        self.assertIsNotNone(errs[1]); self.assertEqual(ctx.reference, ref); self.assertEqual(ctx.records[0]['native'], ref)
        self.assertEqual(len(ctx.records[1]['attempts']), 3)

    def test_marked_reading_without_a_reference_is_refused_once(self):
        ctx, errs = self.readings([['A']], [MARKED]); rec = ctx.records[0]
        self.assertIsNotNone(errs[0]); self.assertEqual(len(rec['attempts']), 1); self.assertIn('no state reference', rec['attempts'][0]['outcome'])
        self.assertIn('neutrality: no unmarked reference render of this state', ctx.gate())

    def test_invalid_response_hash_fails_without_attempts(self):
        ev = evidence(child=ANON, parent=ALT); ev['observed'][TARGET] = dict(ev['observed'][TARGET], sha256='0' * 64)
        ctx, errs = self.readings([['A']], [ANON], ev); self.assertIsNotNone(errs[0]); self.assertNotIn('attempts', ctx.records[0])
        self.assertIn('target response refused by the source rule', json.dumps(ctx.gate()))

if __name__ == '__main__':
    unittest.main()
