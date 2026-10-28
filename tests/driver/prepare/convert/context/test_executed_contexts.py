"""Scope.code at the native boundary (pinned Chromium, real Scope, no caller): a same-origin srcdoc child frame that replaces the parent's
Show.showAR and removes itself before measurement leaves no frame and no foreign script in the top main world, but its execution context was
created in this page's lifetime and is recorded as an unqualified executed context; a page without one records none (Root review 1d8612d8).
Public invented fixture; expected values are the fixture's own facts."""
import unittest
from driver.prepare.convert import context

SHOW = b"<script>var Show = {showAR: function (a, r, w) { return 'native'; }};</script>"
PLAIN = b'<html><head>' + SHOW + b'</head><body><a href="javascript:void(0);" onclick="Show.showAR( this, \'t\', window );">x</a><table id="t"><tr><td>d</td></tr></table></body></html>'
DETACHED = PLAIN.replace(b'</body>', b'<iframe srcdoc="&lt;script&gt;parent.Show.showAR = function () { return \'replaced\'; }; frameElement.remove();&lt;/script&gt;"></iframe></body>')


class ExecutedContexts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def inventory(self, body):
        ctx = self.browser.new_context(); page = ctx.new_page()
        try:
            page.route('https://fixture.invalid/**', lambda r: r.fulfill(status=200, content_type='text/html', body=body))
            scope = context.Scope(page, lifetime=True); page.goto('https://fixture.invalid/page.html', wait_until='load')
            return page.evaluate("() => Show.showAR(null, 't', window)"), scope.code()
        finally:
            ctx.close()

    def test_a_detached_frame_that_replaced_parent_code_is_recorded(self):
        result, code = self.inventory(DETACHED)
        self.assertEqual(result, 'replaced')  # fixture fact: the child frame's script really replaced the parent function
        self.assertEqual((code.get('frames'), code.get('contexts')), (0, []))  # gone at measurement: the frame counts alone cannot see it
        self.assertTrue([x for x in code['executed_contexts'] if not x['own_frame']], code['executed_contexts'])

    def test_a_page_without_a_child_frame_records_none(self):
        result, code = self.inventory(PLAIN)
        self.assertEqual(result, 'native'); self.assertEqual(code.get('executed_contexts'), [], code.get('executed_contexts'))


if __name__ == '__main__':
    unittest.main()
