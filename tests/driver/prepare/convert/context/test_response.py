"""Public native boundary controls; source fixtures and expected cases retained."""
import json, unittest
from .cases import context, sg, evidence, obs, ANON, TARGET
from driver.prepare.get.acquire import _one_run


def render(browser, ev, raw=ANON):  # one unmarked Context render, as the caller's trial makes it: (error, gate reasons, render record)
    ctx = context.Context(ev); src = context.state_source(sg.Source('child.html', {'child.html': raw}), ev, ctx); page = err = None
    try:
        page = ctx.page(browser, None, ('https://trial.invalid/', raw), src); page.goto('trial')
    except Exception as e:
        err = repr(e)[:300]
    finally:
        if page is not None: page.close()
    return err, ctx.gate(), (ctx.records or [{}])[-1]

def inserted(at, run):  # the target response = the member with one run inserted before `at`; the proof as acquire records it (_one_run)
    i = ANON.index(at); resp = ANON[:i] + run + ANON[i:]; ev = evidence(child=ANON)
    ev['observed'][TARGET] = obs(resp, 'text/html'); ev['proof'] = {'form': 'bytes', 'inserted': _one_run(ANON, resp)}; return ev

def corrupt(url):  # only the recorded hash changes
    ev = evidence(child=ANON); ev['observed'][url] = dict(ev['observed'][url], sha256='0' * 64); return ev


class ResponseProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_positive(self):
        err, why, rec = render(self.browser, evidence(child=ANON)); self.assertEqual((err, why), (None, []))

    def test_parent_hash_refused(self):
        ev = corrupt(evidence()['parent_url']); err, why, _ = render(self.browser, ev)
        self.assertIn('parent response refused by the source rule', json.dumps(why))

    def test_target_hash_refused(self):
        err, why, _ = render(self.browser, corrupt(TARGET)); self.assertIn('target response refused by the source rule', json.dumps(why))

    def test_inserted_node_level_run_is_measured(self):
        err, why, rec = render(self.browser, inserted(b'<aside class="museum-note" id="note-indigo">', b'<script>/* inserted by the server */</script>'))
        self.assertEqual((err, why), (None, []), json.dumps(rec.get('overlay'))[:300]); self.assertIs(rec['node_level']['node_level'], True)

    def test_inserted_run_splitting_an_element_is_refused(self):
        err, why, rec = render(self.browser, inserted(b' are closed on Mondays', b'</p><p>'))
        self.assertIn('not node-level', json.dumps(why)); self.assertIs(rec['node_level']['node_level'], False)

if __name__ == '__main__':
    unittest.main()
