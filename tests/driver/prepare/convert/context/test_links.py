"""Revealed-link class (Root's link_class_run1 cases, synthetic verdicts as test data): a link the scan reads hidden is shown only with the page's own link
proof AND a shown part (text or picture); hidden parts stay marked; unproved or unbound or hidden-only links keep the scan; no verdict changes nothing."""
import unittest
from driver.prepare.convert import anchor
def doc(inner): return b'<html><body><div style="display:none"><p>' + inner + b'</p></div><p id="native-note">N</p></body></html>'
CASES = {'plain_text': b'<a href="#native-note">see access</a>', 'visible_and_hidden_children': b'<a href="#native-note">see access<span style="display:none">Unshown detail</span></a>',
         'picture_only': b'<a href="#native-note"><img src="plan.png" alt="floor plan"></a>', 'hidden_only': b'<a href="#native-note"><span style="display:none">Unshown detail</span></a>'}
def span(raw, t): a = raw.index(t); return [a, a + len(t)]
def link(raw, page): return [l for l in anchor.Visible(raw, page=page).links if l['href'] == '#native-note'][0]
def verdict(raw, proved=True, hidden=(), shown=(), pics=()):
    l0 = [l for l in anchor.Visible(raw).links if l['href'] == '#native-note'][0]
    return {'hidden': [span(raw, t) for t in hidden], 'shown': [span(raw, t) for t in shown], 'unbound': [], 'unproven': 0,
            'links': {'proved': [l0['start']] if proved else [], 'unproved': {} if proved else {str(l0['start']): ['tag']}}, 'pictures': {'hidden': [], 'shown': [raw.index(p) for p in pics], 'unbound': []}}
class LinkClass(unittest.TestCase):
    def test_static_unchanged(self):
        for name, inner in CASES.items(): self.assertTrue(link(doc(inner), None)['hidden'], name)
    def test_plain_text_positive(self):
        r = doc(CASES['plain_text']); self.assertFalse(link(r, verdict(r, shown=[b'see access']))['hidden'])
    def test_visible_and_hidden_children_positive_keeps_hidden_part(self):
        r = doc(CASES['visible_and_hidden_children']); l = link(r, verdict(r, shown=[b'see access'], hidden=[b'Unshown detail']))
        self.assertEqual((l['hidden'], l.get('partly_hidden')), (False, True))
    def test_picture_only_positive(self):
        r = doc(CASES['picture_only']); self.assertFalse(link(r, verdict(r, pics=[b'<img']))['hidden'])
    def test_hidden_only_negative(self):
        r = doc(CASES['hidden_only']); self.assertTrue(link(r, verdict(r, hidden=[b'Unshown detail']))['hidden'])
    def test_unproved_negative(self):
        r = doc(CASES['plain_text']); self.assertTrue(link(r, verdict(r, proved=False, shown=[b'see access']))['hidden'])
    def test_unbound_negative(self):  # the proof is present; the link's only run has no verdict the page could bind: keeps the scan (non-vacuous)
        r = doc(CASES['plain_text']); v = verdict(r); v['unbound'] = [span(r, b'see access')]; self.assertTrue(link(r, v)['hidden'])
    def test_no_verdict_negative(self):  # the proof is present, nothing inside the link has a verdict: keeps the scan (non-vacuous)
        r = doc(CASES['plain_text']); self.assertTrue(link(r, verdict(r))['hidden'])
if __name__ == '__main__':
    unittest.main()
