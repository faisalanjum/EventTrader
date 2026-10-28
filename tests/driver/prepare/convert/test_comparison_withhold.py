"""plan.qualification_withhold at its native owners (screen_grid.Source.answer, acquisition.facts, context_acquire reset): the comparison-only exception
withholds exactly the bound kinds of the ONE proved inserted script's bound recorded response; everything else is an ordinary refusal or served as
recorded; strict (empty) by default and cleared per document. Pure, no browser (root-native-automatic-trigger-closeout-20261028t211651877057z)."""
import hashlib, unittest
from driver.prepare.convert import screen_grid as sg
from driver.prepare.get import acquisition, context_acquire

U, OTHER = 'https://www.sec.gov/X/inserted', 'https://www.sec.gov/include/Show.js'
BODY, CHANGED = b'var x;', b'var y;'
h = lambda b: hashlib.sha256(b).hexdigest()
def obs(body): return {'status': 200, 'observed_at': 't', 'sha256': h(body), 'body': body, 'content_type': 'application/javascript'}
def source(u_body=BODY, with_u=True):
    o = {OTHER: obs(BODY)}
    if with_u: o[U] = obs(u_body)
    s = sg.Source('context', {}, observed=o); s.root = 'https://www.sec.gov/'; return s
def bind(sha=h(BODY)): sg.WITHHELD.clear(); sg.WITHHELD[U] = {'kinds': frozenset({'script', 'xhr'}), 'sha256': sha}
def facts(s): return acquisition.facts({'source': s, 'log': []})


class ComparisonWithhold(unittest.TestCase):
    def tearDown(self): sg.WITHHELD.clear()
    def test_strict_by_default(self):
        self.assertEqual(sg.WITHHELD, {}); s = source(); self.assertIsNotNone(s.answer(U, 'script')); self.assertNotIn('withheld', facts(s))
    def test_bound_kinds_of_the_bound_response_are_withheld_not_served_not_inputs(self):
        bind(); s = source(); self.assertIsNone(s.answer(U, 'script')); self.assertIsNone(s.answer(U, 'xhr')); self.assertIsNotNone(s.answer(OTHER, 'script'))
        f = facts(s); self.assertEqual(f['withheld'], [(U, 'script', h(BODY)), (U, 'xhr', h(BODY))]); self.assertEqual(f['refused_get'], []); self.assertEqual([d[0] for d in f['delivered']], [OTHER])
    def test_any_other_kind_or_a_navigation_is_an_ordinary_refusal(self):
        bind(); s = source(); self.assertIsNone(s.answer(U, 'fetch')); f = facts(s); self.assertEqual(f['refused_get'], [(U, 'fetch')]); self.assertNotIn('withheld', f)
        s = source(); self.assertIsNone(s.answer(U, 'script', navigation=True)); self.assertNotIn('withheld', facts(s))
    def test_a_changed_recorded_response_is_an_ordinary_refusal(self):
        bind(); s = source(u_body=CHANGED); self.assertIsNone(s.answer(U, 'script')); f = facts(s)
        self.assertEqual(f['refused_get'], [(U, 'script')]); self.assertNotIn('withheld', f); self.assertIn('not the bound one', s.records[U]['why'])
    def test_no_recorded_response_is_an_ordinary_refusal(self):
        bind(); s = source(with_u=False); self.assertIsNone(s.answer(U, 'script')); self.assertEqual(facts(s)['refused_get'], [(U, 'script')])
    def test_an_unbound_sha_withholds_nothing(self):
        bind(sha=None); s = source(); self.assertIsNone(s.answer(U, 'script')); f = facts(s); self.assertEqual(f['refused_get'], [(U, 'script')]); self.assertNotIn('withheld', f)
    def test_acquire_context_resets_before_anything_else(self):
        bind(); self.assertTrue(sg.WITHHELD)
        with self.assertRaises(Exception): context_acquire.acquire_context(None, None, '/nonexistent/version_dir', 'R1.htm', False, '')
        self.assertEqual(sg.WITHHELD, {})


if __name__ == '__main__':
    unittest.main()
