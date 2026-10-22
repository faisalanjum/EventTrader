"""Selection and measured-response custody at the shared source owner."""
import unittest
from .cases import sg, evidence, ANON, TARGET
from driver.prepare.get import acquisition
from driver.prepare.get.acquire import AcquisitionError
from driver.prepare.convert import overlay
P = sg.marker_prefix(ANON); vis = sg.Visible(ANON); runs, _ = sg.symbol_runs(ANON, vis)
MARKED = sg.tag_cells(ANON, vis, (), [(a, b'<!--%ss:%d-->' % (P.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], P)[0]


def corrupt(ev, url): ev['observed'][url] = dict(ev['observed'][url], sha256='0' * 64); return ev
def selection(browser, ev):
    body, _ = overlay.measurement_body(ev['observed'][TARGET]['body'], ANON, MARKED, P, ev['proof'])
    return acquisition.Selection(ev['parent_url'], ev['observed'], TARGET, ANON, body, P).run(browser)


class SelectionCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_healthy_evidence_selects(self): self.assertEqual(selection(self.browser, evidence(child=ANON))['verdict'], 'selected')
    def test_changed_parent_hash_fails_before_navigation(self):
        ev = evidence(child=ANON)
        with self.assertRaises(AcquisitionError): selection(self.browser, corrupt(ev, ev['parent_url']))
    def test_changed_target_hash_refused(self): self.assertNotEqual(selection(self.browser, corrupt(evidence(child=ANON), TARGET))['verdict'], 'selected')

    def test_measured_source_reuses_the_observation_rule(self):
        ev = evidence(child=ANON); body, _ = overlay.measurement_body(ev['observed'][TARGET]['body'], ANON, MARKED, P, ev['proof'])
        ok = overlay.MeasuredSource('t', {}, observed=ev['observed'], measured={TARGET: body}, prefix=P)
        self.assertEqual(ok.answer(TARGET, 'xhr')[2], body); r = ok.records[TARGET]
        self.assertEqual((r['sha256'], r['measured_sha256']), (ev['observed'][TARGET]['sha256'], overlay.sha(body)))  # original and measured identities kept apart
        bad = overlay.MeasuredSource('t', {}, observed=corrupt(evidence(child=ANON), TARGET)['observed'], measured={TARGET: body}, prefix=P)
        self.assertIsNone(bad.answer(TARGET, 'xhr')); self.assertEqual(bad.records[TARGET]['why'], 'observed bytes are not the recorded sha256')  # the Source's own refusal
        other = overlay.MeasuredSource('t', {}, observed=ev['observed'], measured={TARGET: body + b'<p>extra</p>'}, prefix=P)
        self.assertIsNone(other.answer(TARGET, 'xhr'))  # not the recorded response plus our comments

if __name__ == '__main__':
    unittest.main()
