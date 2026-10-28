"""context_acquire.bind_inserted: the ONE script SEC's server inserted into a published copy, bound only (owner single-version policy,
root-single-version-qualification-20261028t193735747002z). Pinned browser page with JavaScript off, as acquire_context uses it; no network."""
import unittest
from driver.prepare.get import context_acquire as ca

TARGET = 'https://www.sec.gov/Archives/edgar/data/1/000000000123000001/R2.htm'
FILED = b'<html><body><p>filed</p>'


def case(run, filed=FILED, placements=None):  # a published copy = the filed bytes + one inserted run, with node_level's own accepted placement
    copy = FILED + run + b'</body></html>'; q = len(FILED)
    return copy, (filed, {'inserted': [q, q + len(run)]}), {'window': [0, q]}, {'placements': [{'q': q, 'node_level': True}] if placements is None else placements}


class BindInserted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.pg = cls.browser.new_page(java_script_enabled=False)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def bind(self, run, **kw): return ca.bind_inserted(self.pg, *case(run, **kw), TARGET)

    def test_one_root_relative_script_is_bound(self):
        w = self.bind(b'<script type="text/javascript" src="/Qp9qZ/J_/x"></script>')
        self.assertEqual((w.get('href'), w.get('src'), w.get('run_start')), ('https://www.sec.gov/Qp9qZ/J_/x', '/Qp9qZ/J_/x', len(FILED)), w)
    def test_without_a_type_it_is_bound_too(self):
        self.assertEqual(self.bind(b'<script src="/a/b"></script>').get('href'), 'https://www.sec.gov/a/b')
    def test_inline_code_is_not_bound(self):
        self.assertEqual(self.bind(b'<script src="/a/b">x = 1;</script>'), {'why': 'script element shape'})
    def test_an_extra_attribute_is_not_bound(self):
        self.assertEqual(self.bind(b'<script async src="/a/b"></script>'), {'why': 'script element shape'})
    def test_a_relative_src_is_not_bound(self):
        self.assertEqual(self.bind(b'<script src="a/b"></script>'), {'why': 'src is not root-relative'})
    def test_another_host_is_not_bound(self):
        self.assertEqual(self.bind(b'<script src="//evil.example/a"></script>'), {'why': 'src is not root-relative'})
    def test_two_elements_are_not_bound(self):
        self.assertEqual(self.bind(b'<script src="/a"></script><script src="/b"></script>'), {'why': 'run is not exactly one script element'})
    def test_a_src_the_filed_bytes_name_is_held(self):
        self.assertIn('collision', self.bind(b'<script src="/a/b"></script>', filed=FILED + b'<a href="/a/b">x</a>')['why'])
    def test_no_or_two_accepted_placements_are_not_bound(self):
        self.assertEqual(self.bind(b'<script src="/a/b"></script>', placements=[]), {'why': '0 accepted node-level placements'})
        self.assertEqual(self.bind(b'<script src="/a/b"></script>', placements=[{'q': 3, 'node_level': True}, {'q': 4, 'node_level': True}]), {'why': '2 accepted node-level placements'})


if __name__ == '__main__':
    unittest.main()
