"""Native visual state through the actual page boundary (Root CONTEXT_NATIVE_STATE_GUARD_DECISION_20261021; Smart's five controls from
smart/context_lineage_spike/visual_guard_probe_v2.py, same trigger and CSS, on the invented public fixture): our marks make the parent change the
CSSOM (insertRule, an adopted sheet) or focus (a :focus-within rule strikes a heading) without any DOM change. Only the native full-page capture
differs, so each must refuse in the initial view and every activation; the clean page and a page taller than the viewport must not.
Boundary: the same five controls through Context.page with a run-marked body (pixel-neutral marks), so a negative cannot pass by accident.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_native_visual.py"""
import json, unittest
from .cases import run, controls, activations, PARENT_UI, ANON, CSS, rep, context, sg, evidence, BUTTON
TRIG = b"var w=document.createTreeWalker(document,NodeFilter.SHOW_COMMENT),n,k=0;while((n=w.nextNode()))if(/^m[0-9a-f]{8,}[a-z]:/.test(n.nodeValue))k++;"  # Smart's, verbatim
def with_script(js): return rep(PARENT_UI, b'</body>', b'<script>' + js + b'</script></body>')
CSS_FOCUS = CSS + b"\n#report-host section:focus-within h2{text-decoration:line-through}\n"
NEGATIVES = {
    'insertRule': (with_script(b"setInterval(function(){" + TRIG + b"if(k&&!window.__d){window.__d=1;document.styleSheets[0].insertRule('#report-host{text-decoration:line-through}',0);}},100);"), CSS),
    'adoptedSheet': (with_script(b"setInterval(function(){" + TRIG + b"if(k&&!window.__d){window.__d=1;var s=new CSSStyleSheet();s.replaceSync('#report-host{text-decoration:line-through}');document.adoptedStyleSheets=[s];}},100);"), CSS),
    'focus': (with_script(b"setInterval(function(){" + TRIG + b"if(k&&!window.__d){var a=document.querySelector('#report-host section a');if(a){window.__d=1;a.focus();}}},100);"), CSS_FOCUS)}
TALL = rep(PARENT_UI, b'</body>', b'<div style="height:2400px">tall parent content</div></body>')
vis = sg.Visible(ANON); runs, _ = sg.symbol_runs(ANON, vis); P = sg.marker_prefix(ANON)
RUN_MARKED = sg.tag_cells(ANON, vis, (), [(a, b'<!--%ss:%d-->' % (P.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], P)[0]  # run marks: pixel-neutral (evidence/visual_diag_run2)


def boundary(browser, parent, css=CSS):  # the page boundary itself: an unmarked reference render, then one run-marked render of the same state
    ev = evidence(child=ANON, parent=parent, css=css); ctx = context.Context(ev); src = context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx); errs = []
    for body in (ANON, RUN_MARKED):
        page = ctx.page(browser, None, ('https://trial.invalid/', body), src)
        try: page.goto('visual'); errs.append(None)
        except Exception as e: errs.append(repr(e)[:300])
        finally: page.close()
    return ctx, errs


class Boundary(unittest.TestCase):  # Smart's five controls through Context.page, with marks that do not themselves change pixels
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def refused(self, parent, css):
        ctx, errs = boundary(self.browser, parent, css); rec = ctx.records[1]
        self.assertIsNone(errs[0]); self.assertIsNotNone(errs[1]); self.assertNotIn('native', rec)
        self.assertEqual([a['outcome'] for a in rec['attempts']], ['not used: differs from the state reference (capture)'] * 3)  # the document is equal; only pixels differ
    def test_insert_rule(self): self.refused(*NEGATIVES['insertRule'])
    def test_adopted_sheet(self): self.refused(*NEGATIVES['adoptedSheet'])
    def test_focus_reveal(self): self.refused(*NEGATIVES['focus'])
    def used(self, parent):
        ctx, errs = boundary(self.browser, parent); self.assertEqual((errs, ctx.gate()), ([None, None], [])); self.assertEqual(ctx.records[1]['native'], ctx.reference); return ctx.reference['capture']
    def test_clean(self):
        cap = self.used(PARENT_UI); self.assertEqual((cap['options'], cap['viewport'], cap['device_scale_factor']), ({'full_page': True, 'type': 'png', 'caret': 'initial', 'animations': 'allow'}, [1400, 1000], 1))
    def test_tall_page(self):
        cap = self.used(TALL); self.assertGreater(cap['height'], 1000); self.assertEqual([cap['width'], cap['height']], cap['page_size'])


class NativeVisual(unittest.TestCase):  # whole routes (screen step included): blocked today by the gap marks' 4-pixel effect (evidence/visual_diag_run2)
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def refused_by_capture_only(self, parent, css):
        res = run(self.browser, ANON, parent=parent, css=css); err = res['initial'].get('error') or ''
        self.assertNotEqual(res['initial']['status'], 'OK'); self.assertIn('differs from the state reference (capture)', err)
        for s in controls(ANON):
            a = activations(res, s); self.assertTrue(a and a[0]['status'] != 'complete', json.dumps(a)[:300])
            self.assertTrue(any('differs from the state reference (capture)' in w for w in a[0]['reasons']), json.dumps(a[0]['reasons'])[:500])
    def test_insert_rule_refused(self): self.refused_by_capture_only(*NEGATIVES['insertRule'])
    def test_adopted_sheet_refused(self): self.refused_by_capture_only(*NEGATIVES['adoptedSheet'])
    def test_focus_reveal_refused(self): self.refused_by_capture_only(*NEGATIVES['focus'])

    def complete(self, parent):
        res = run(self.browser, ANON, parent=parent); self.assertEqual((res['initial']['status'], res['initial'].get('error')), ('PARTIAL', BUTTON))
        self.assertEqual([activations(res, s)[0]['status'] for s in controls(ANON)], ['complete', 'complete']); return res
    def test_clean_complete_and_recorded(self):
        res = self.complete(PARENT_UI); cap = res['states'][0]['records'][0]['native']['capture']
        self.assertEqual((cap['options'], cap['viewport'], cap['device_scale_factor']), ({'full_page': True, 'type': 'png', 'caret': 'initial', 'animations': 'allow'}, [1400, 1000], 1))
        self.assertTrue(cap['browser'] and len(cap['sha256']) == 64)
    def test_tall_page_full_capture(self):
        res = self.complete(TALL); cap = res['states'][0]['records'][0]['native']['capture']
        self.assertGreater(cap['height'], 1000); self.assertEqual([cap['width'], cap['height']], cap['page_size'])

if __name__ == '__main__':
    unittest.main()
