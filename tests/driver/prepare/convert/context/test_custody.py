"""Package-row custody through a context (no browser): every state's Source keeps the caller's path, members, declared base, bundle and its own
observations unchanged, gains the context's recorded responses, and a context record that differs from one the source holds is refused."""
import unittest
from driver.prepare.convert import context, screen_grid as sg
BASE = 'https://www.sec.gov/Archives/edgar/data/1/000000000000000002/'  # a declared package address shape (test data)
OWN = {BASE + 'a.css': {'status': 200, 'content_type': 'text/css', 'observed_at': 't0', 'sha256': None}}
def ev(extra=None): return {'parent_url': 'https://p.invalid/x', 'target_url': 'https://p.invalid/c', 'selection': {'source_anchor': 0}, 'proof': {'form': 'equal', 'inserted': []},
                            'observed': {'https://p.invalid/x': {'status': 200, 'observed_at': 't1', 'body': b'<a href="#">x</a>'}, **(extra or {})}}
class Custody(unittest.TestCase):
    def test_state_source_keeps_package_custody(self):
        src = sg.Source('doc.htm', {'doc.htm': b'<p>x</p>'}, base=BASE, observed=OWN, bundle='bundle-sha'); e = ev(); ctx = context.Context(e, control=(5, 9))
        s = context.state_source(src, e, ctx)
        self.assertEqual((s.path, dict(s.members), s.base, s.bundle), ('doc.htm', {'doc.htm': b'<p>x</p>'}, BASE, 'bundle-sha'))
        self.assertEqual(dict(s.observed[BASE + 'a.css']), OWN[BASE + 'a.css']); self.assertIn('https://p.invalid/x', s.observed); self.assertIs(s.context, ctx)
        s.bind(b'<p>x</p>'); idt = s.identity(); self.assertEqual((idt['document']['base'], idt['document']['bundle'], idt['context']['controls']), (BASE, 'bundle-sha', [5, 9]))
    def test_conflicting_context_observation_is_refused(self):
        src = sg.Source('doc.htm', {'doc.htm': b'<p>x</p>'}, base=BASE, observed=OWN, bundle='bundle-sha')
        e = ev({BASE + 'a.css': {'status': 404, 'observed_at': 't9'}})
        with self.assertRaises(ValueError): context.state_source(src, e, context.Context(e))
if __name__ == '__main__':
    unittest.main()
