"""Package-row custody through a context (no browser): every state's Source keeps the caller's path, members, declared base, bundle and its own
observations unchanged, gains the context's recorded responses, and a context record that differs from one the source holds is refused."""
import hashlib, unittest
from driver.prepare import document
from driver.prepare.convert import context, screen_grid as sg
from driver.prepare.get import context_acquire
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
    def test_a_plan_row_and_the_context_holding_one_recorded_response_agree(self):  # root-retained-css-negative-native-contract-20261029t011143618421z
        """The same recorded response supplied as a plan row observation (document.declared_source) and held by the context (a 404 its campaign recorded,
        read through context_acquire._failed; a 200 in _get's shape): one response, so the state keeps it; any real difference stays refused."""
        css, at = BASE + 'include/r.css', '2026-10-28T20:14:00Z'
        def source(entry): return document.declared_source({'filename': 'doc.htm', 'observed_responses': [entry]}, {'identity': {'accession': 'a', 'ciks': ['1', '2'], 'form': '10-K'},
                                                           'package': {'sha256': 'b'}}, {'doc.htm': b'<p>x</p>'}, sg, None)[0]  # two CIKs, none requested: no address derived
        failed = {}; context_acquire._failed(failed, css, {'attempts': [{'status': 404, 'headers': {'content-type': 'text/html'}, 'started_at': at}]})
        row404 = {'url': css, 'status': 404, 'content_type': 'text/html', 'observed_at': at, 'sha256': None}  # a native failure has no body: its key omitted
        body = b'p{}'; got200 = {css: {'status': 200, 'content_type': 'text/css', 'observed_at': at, 'sha256': hashlib.sha256(body).hexdigest(), 'body': body}}
        row200 = {'url': css, 'status': 200, 'content_type': 'text/css', 'observed_at': at, 'sha256': hashlib.sha256(body).hexdigest(), 'body': body.hex()}
        for row, held, served in ((row404, failed, (404, 'text/html', b'')), (row200, got200, (200, 'text/css', body))):
            with self.subTest(status=row['status']):
                e = ev(held); self.assertEqual(context.state_source(source(row), e, context.Context(e)).observation(css, 'stylesheet'), served)
                for field, other in (('status', 410), ('observed_at', 'later'), ('content_type', 'text/plain'), ('sha256', 'f' * 64)):
                    with self.subTest(differs=field), self.assertRaises(ValueError): context.state_source(source(dict(row, **{field: other})), e, context.Context(e))
if __name__ == '__main__':
    unittest.main()
