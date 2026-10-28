"""Scope.code's script inventory covers the page's whole lifetime, not only scripts still uncollected at measurement (pinned protocol: a late
Debugger.enable reports "known and uncollected" scripts only; Root native check 0178a98f). Pinned Chromium, real Scope, no caller. Invented fixture:
a page whose own short-lived script reassigns Show.showAR and is then garbage-collected (native HeapProfiler.collectGarbage); the
reassignment remains, so the mutator must still be in the inventory with its exact source. A page without one keeps none."""
import hashlib, unittest
from driver.prepare.convert import context

SHOW = b"<script>var Show = {showAR: function () { return 'native'; }, hideAR: function () { return 'hidden'; }};</script>"
PLAIN = b'<html><head>' + SHOW + b'</head><body><a href="javascript:void(0);" onclick="Show.showAR( this, \'t\', window );">x</a><table id="t"><tr><td>d</td></tr></table></body></html>'
MUTATOR = "Show.showAR = Show.hideAR; void 0;"
EPHEMERAL = PLAIN.replace(b'</body>', b'<script>setTimeout(function () { (0, eval)("' + MUTATOR.encode() + b'"); }, 0);</script></body>')


class ScriptLifetime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def inventory(self, body, collect):
        ctx = self.browser.new_context(); page = ctx.new_page()
        try:
            page.route('https://fixture.invalid/**', lambda r: r.fulfill(status=200, content_type='text/html', body=body))
            scope = context.Scope(page, lifetime=True); page.goto('https://fixture.invalid/page.html', wait_until='load'); page.wait_for_timeout(200)
            if collect:
                for _ in range(3): scope.cdp.send('HeapProfiler.collectGarbage')
            return page.evaluate("() => Show.showAR()"), scope.code()
        finally:
            ctx.close()

    def test_a_collected_mutator_stays_in_the_inventory(self):
        result, code = self.inventory(EPHEMERAL, collect=True)
        self.assertEqual(result, 'hidden')  # fixture fact: the short-lived script really replaced the function
        want = hashlib.sha256(MUTATOR.encode()).hexdigest()
        self.assertIn(want, {s['sha256'] for s in code['scripts']}, [(s['url'], s['bytes'], s.get('text')) for s in code['scripts']])

    def test_the_pinned_playwright_main_world_code_is_exact_tooling(self):  # its utility script and evaluate wrapper, collected or not
        ctx = self.browser.new_context(); page = ctx.new_page()
        try:
            page.route('https://fixture.invalid/**', lambda r: r.fulfill(status=200, content_type='text/html', body=PLAIN))
            scope = context.Scope(page, lifetime=True); page.goto('https://fixture.invalid/page.html', wait_until='load')
            page.evaluate('() => 1'); got = {s['sha256'] for s in scope.code()['scripts'] if not s['url']}
        finally:
            ctx.close()
        tooling = {h for h, v in context.TOOLING.items() if 'utility script' in v or 'evaluate wrapper' in v}
        self.assertEqual(len(tooling), 2); self.assertLessEqual(tooling, got)

    def test_no_mutator_none_recorded(self):
        result, code = self.inventory(PLAIN, collect=True)
        self.assertEqual(result, 'native')
        self.assertNotIn(hashlib.sha256(MUTATOR.encode()).hexdigest(), {s['sha256'] for s in code['scripts']})


if __name__ == '__main__':
    unittest.main()
