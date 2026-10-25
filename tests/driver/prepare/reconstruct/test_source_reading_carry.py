"""Portable controls for the carried typed source reading (Root FABLE_OUTPUT_ONLY_FINAL_20261025T1350 / PORTABLE_TESTS_20261025T1400): when a
completion binds `source_reading_complete_sha256`, reconstruct.main carries the child's own readback with its own custody, and verify holds it to the
same custody / preserved / annotations checks and reports its unrepresented families (an XML child's `xml.not_represented` included).
Built only from this suite's pinned fixtures (fixtures/PROVENANCE.json: h4_linker_document HTML, x1_structure XML) as native-shaped temporary
attempts. A child must name the parent's document (custody gate), so an XML child takes the parent's two identity fields; content is the fixture's.
Expected XML families are stated from the readback contract (five XML parts are never represented unless the route saves `xml_metadata`) and the
fixture facts (x1_structure saves none and carries field `units`, an explicit unknown), not from the code under test.
Run from the repository root: python -I -B -m unittest tests.driver.prepare.reconstruct.test_source_reading_carry"""
import copy, hashlib, json, shutil, tempfile, unittest
from pathlib import Path

from driver.prepare import reconstruct as rb
from tests.driver.prepare.reconstruct.test_reconstruct import load

XML_LIMITS = {'comments', 'processing_instructions', 'xml_declaration', 'doctype', 'source_spelling', 'units'}


def write(a, E, **extra):  # one native-shaped attempt: ROUTE.json bound by COMPLETE.json (the producer's completion keys); returns the COMPLETE pin
    a.mkdir(parents=True); body = json.dumps(E).encode(); (a / 'ROUTE.json').write_bytes(body)
    c = json.dumps({'file_id': E['file_id'], 'source_sha256': E['sha256'], 'route_sha256': hashlib.sha256(body).hexdigest(), 'native_status': E['status'],
                    'prepared_input_sha256': [], 'reader_called': False, **extra}).encode()
    (a / 'COMPLETE.json').write_bytes(c); return hashlib.sha256(c).hexdigest()


class SourceReadingCarry(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp)
        self.parent = load('h4_linker_document')['route']

    def attempt(self, child, name='a', bind=True):  # parent + optional child attempt; bind=False leaves the child folder unbound
        a = self.tmp / name; a.mkdir()
        pin = write(a / 'source_reading', child) if child is not None else None
        write_parent = {rb.SOURCE_READING_KEY: pin} if child is not None and bind else {}
        body = json.dumps(self.parent).encode(); (a / 'ROUTE.json').write_bytes(body)
        (a / 'COMPLETE.json').write_text(json.dumps({'file_id': self.parent['file_id'], 'source_sha256': self.parent['sha256'], 'route_sha256': hashlib.sha256(body).hexdigest(),
                                                     'native_status': self.parent['status'], 'prepared_input_sha256': [], 'reader_called': False, **write_parent}))
        return a

    def xml_child(self):
        x = load('x1_structure')['route']; self.assertNotIn('xml_metadata', x); self.assertIn('units', x)  # the fixture facts the XML limits rest on
        x['file_id'], x['sha256'] = self.parent['file_id'], self.parent['sha256']; return x

    def run_main(self, a):
        rb.main([str(a), str(a / 'R.json')]); return json.loads((a / 'R.json').read_bytes())

    def verify(self, a, R):
        p = a / 'R_checked.json'; p.unlink(missing_ok=True); p.write_text(json.dumps(R)); return rb.verify(a, p)

    def clean(self, v): self.assertEqual((v['custody'], v['preserved'], v['annotations']), ([], [], []), v)

    def test_html_child_positive(self):
        a = self.attempt(copy.deepcopy(self.parent)); R = self.run_main(a)
        self.assertEqual(R['source_reading']['kind'], 'html'); self.assertEqual(R['source_reading']['custody']['route_sha256'], json.loads((a / 'source_reading' / 'COMPLETE.json').read_bytes())['route_sha256'])
        self.clean(self.verify(a, R))

    def test_xml_child_positive_reports_its_xml_limits(self):
        a = self.attempt(self.xml_child()); R = self.run_main(a); v = self.verify(a, R)
        self.assertEqual(R['source_reading']['kind'], 'xml'); self.clean(v)
        want = {'source reading: ' + k for k in XML_LIMITS}
        self.assertLessEqual(want, set(v['unrepresented']), sorted(want - set(v['unrepresented'])))

    def test_no_child_no_carry(self):
        a = self.attempt(None); R = self.run_main(a); self.assertNotIn('source_reading', R); self.clean(self.verify(a, R))

    def test_absent_carried_child_fails_custody(self):
        a = self.attempt(copy.deepcopy(self.parent)); R = self.run_main(a); del R['source_reading']
        self.assertTrue(any('does not carry' in x for x in self.verify(a, R)['custody']))

    def test_extra_carried_child_fails_custody(self):
        a = self.attempt(None); R = self.run_main(a)
        b = self.attempt(copy.deepcopy(self.parent), name='b'); R['source_reading'] = self.run_main(b)['source_reading']
        self.assertTrue(any('does not bind' in x for x in self.verify(a, R)['custody']))

    def test_nested_extra_reading_inside_the_child_fails_custody(self):
        a = self.attempt(copy.deepcopy(self.parent)); R = self.run_main(a); R['source_reading']['source_reading'] = copy.deepcopy(R['source_reading'])
        self.assertTrue(any(x.startswith('source reading: ') and 'does not bind' in x for x in self.verify(a, R)['custody']))

    def test_mismatched_child_custody_fails(self):
        a = self.attempt(copy.deepcopy(self.parent)); R = self.run_main(a); R['source_reading']['custody']['route_sha256'] = '0' * 64
        self.assertTrue(any('source_reading.custody differs' in x for x in self.verify(a, R)['custody']))

    def test_tampered_child_content_fails_preservation(self):
        for kind, child in (('html', copy.deepcopy(self.parent)), ('xml', self.xml_child())):
            a = self.attempt(child, name=kind); R = self.run_main(a)
            if kind == 'html': next(n for n in R['source_reading']['sequence'] if (n.get('record') or {}).get('text'))['record']['text'] += ' extra'
            else: R['source_reading']['xml']['elements'][0]['attributes'] = {'tampered': 'yes'}
            self.assertTrue(any(x.startswith('source reading: ') for x in self.verify(a, R)['preserved']), kind)

    def test_custody_gate_refuses_unbound_wrong_pin_or_other_document(self):
        a = self.attempt(copy.deepcopy(self.parent), name='unbound', bind=False); (a / 'R0.json').write_text('{}')
        self.assertIn('does not bind it', rb.verify(a, a / 'R0.json')['custody'][0])
        b = self.attempt(copy.deepcopy(self.parent), name='pin'); (b / 'source_reading' / 'COMPLETE.json').write_bytes((b / 'source_reading' / 'COMPLETE.json').read_bytes() + b' ')
        (b / 'R0.json').write_text('{}')
        self.assertIn('not the completion pin', rb.verify(b, b / 'R0.json')['custody'][0])
        other = copy.deepcopy(self.parent); other['file_id'] = 'another/document.htm'; c = self.attempt(other, name='other'); (c / 'R0.json').write_text('{}')
        self.assertIn('another document', rb.verify(c, c / 'R0.json')['custody'][0])


if __name__ == '__main__':
    unittest.main()
