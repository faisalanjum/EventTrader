"""Inner source-owned controls inside a proved target (invented public fixture; Root's finite inner-state class): an in-place visibility change after the
outer reveal is its own labelled state; a no-op gets no state; content damage is refused; coverage is counted across labelled states.
Run with the normal tests.driver.prepare suite."""
import json, unittest
from .cases import rep, run, controls, activations, state, ANON, RICH
from driver.prepare.convert import screen_grid as sg
TOGGLE = b"var g = this.parentNode.nextElementSibling; g.style.display = (g.style.display === 'none') ? 'block' : 'none';"
INNER = (b'<aside class="museum-note" id="note-amber"><p>Use the <b>east</b> stair.</p>\n'
         b'<p><a href="javascript:void(0)" onclick="' + TOGGLE + b'">Floor details</a></p>\n'
         b'<div style="display:none"><table><tr><th>Floor</th><th>Room</th></tr><tr><td>2</td><td>Prints</td></tr></table></div>\n'
         b'<p><a href="javascript:void(0)" onclick="void(0)">Opening notes</a></p>\n<div><ul><li>Open daily</li><li>Closed on holidays</li></ul></div></aside>')
CHILD_INNER = rep(ANON, RICH, INNER)
DAMAGE = rep(CHILD_INNER, TOGGLE, TOGGLE + b" g.querySelector('td').textContent = 'X';")
def inner_links(child): return [l['start'] for l in sg.Visible(child).links if l['href'].startswith('javascript:') and l['start'] > controls(child)[1]]

class InnerStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_hidden_group_revealed_in_place_and_noop(self):
        res = run(self.browser, CHILD_INNER); outer = activations(res, controls(CHILD_INNER)[0])[0]; toggle, noop = inner_links(CHILD_INNER)
        self.assertEqual(outer['status'], 'incomplete'); self.assertTrue(outer['coverage']['not_shown_in_state']['hidden'], 'the outer state lists the still-hidden group')
        inner = activations(res, toggle); self.assertTrue(inner, json.dumps(res['trials'])[:600]); a = inner[0]  # the state loop also tries it again from its own state (the reverse)
        self.assertEqual([x['status'] for x in inner if x['status'] == 'refused'], [], json.dumps(inner)[:600])
        self.assertEqual((a['status'], a['after']), ('complete', [controls(CHILD_INNER)[0]]), json.dumps(a['reasons'])[:400])
        self.assertTrue(any(attr == 'style' for _, attr, _, _ in a['inner_effects']))
        self.assertIn('table', [u['kind'] for u in state(res, a['state'])['route']['units'] if u['id'] in {p['unit'] for p in a['participants']}])
        self.assertEqual(outer['coverage_across_states']['never_affirmatively_shown_runs'], [])  # renamed with Root's caller review item 2 (affirmative evidence)
        self.assertEqual(activations(res, noop), [], 'a no-op control gets no state')

    def test_inner_content_damage_is_refused(self):
        res = run(self.browser, DAMAGE); a = activations(res, inner_links(DAMAGE)[0])
        self.assertTrue(a and a[0]['status'] != 'complete' and 'content or order' in json.dumps(a[0]['reasons']), json.dumps(a)[:500])

if __name__ == '__main__':
    unittest.main()
