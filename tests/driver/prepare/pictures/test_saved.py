"""Saved extraction -> OCR supplement, with no network or model execution."""
import hashlib
import io
import gzip
import json
import tempfile
import copy
import shutil
import unittest
from pathlib import Path

from PIL import Image

from driver.prepare.get import archive
from driver.prepare.pictures import readers, saved
from tests.driver.prepare.pictures.test_join import fakes
from tests.driver.prepare.pictures.test_pdf import made, CASES
from tests.driver.prepare.get.test_acquire import package, uu, ACCESSION, CIK, FORM
from driver.prepare.get.acquire import acquire


sha = lambda b: hashlib.sha256(b).hexdigest()


class SavedPictures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = []
        image = io.BytesIO()
        Image.new('RGB', (80, 40), 'white').save(image, format='PNG')
        self.image = image.getvalue()
        self.raw = b'<html><img src="a.png"><img src="a.png"></html>'

    def attempt(self):
        folder = self.root / 'attempt_0'
        folder.mkdir()
        pin = archive.store_blob(folder / 'prepared', self.image)
        route = dict(schema='prepare-route-output/1', file_id='doc.htm', sha256=sha(self.raw),
                     status='OK', error=None, route=dict(name='independent test input'),
                     resources=dict(dependencies=[dict(member='a.png', sha256=pin)]),
                     units=[dict(id=uid, kind='image', text='', input=dict(input_sha256=pin, member_sha256=pin, how='member'))
                            for uid in ('first', 'again')])
        body = json.dumps(route).encode()
        (folder / 'ROUTE.json').write_bytes(body)
        (folder / 'COMPLETE.json').write_text(json.dumps(dict(
            file_id='doc.htm', source_sha256=route['sha256'], route_sha256=sha(body), native_status='OK',
            prepared_input_sha256=[pin], reader_called=False)))
        return folder

    def filing(self, extra=()):
        source = self.attempt()
        raw = package([('doc.htm', self.raw, '8-K', '1', None),
                       ('a.png', uu(self.image, 'a.png'), 'GRAPHIC', '2', None)] + list(extra))
        supplied = self.root / 'package.gz'
        supplied.write_bytes(gzip.compress(raw))
        version = acquire(ACCESSION, CIK, FORM, self.root / 'versions', package=supplied, sha256=sha(raw))
        plan = self.root / 'PLAN.json'
        plan.write_text(json.dumps(dict(source_commands=[dict(file_id='doc.htm', filename='doc.htm', dispatch='html', source_sha256=sha(self.raw))])))
        result = self.root / 'RESULT.json'
        result.write_text(json.dumps(dict(plan_sha256=sha(plan.read_bytes()), rows=[dict(
            file_id='doc.htm', attempt=str(source), outcome='verified_saved_output', generate_exit=0, reconstruct_exit=0, verify_exit=0)])))
        pin = lambda p: dict(path=str(p), sha256=sha(p.read_bytes()))
        return dict(status='complete', version=str(version), package_sha256=sha(raw),
                    runtime_manifest_sha256='control', plan=pin(plan), result=pin(result), manifest=pin(version / 'manifest.json'))

    def test_saved_images_are_read_once_and_extraction_stays_byte_identical(self):
        source = self.attempt()
        before = {p.name: p.read_bytes() for p in source.glob('*.json')}
        result = saved.read_attempt(source, self.root / 'ocr', fakes(self.calls))
        self.assertEqual(len(result['pictures']), 2)
        self.assertEqual({x['input']['input_sha256'] for x in result['pictures']}, {sha(self.image)})
        self.assertEqual(self.calls, [('chandra', sha(self.image)), ('pp', sha(self.image)), ('ox', sha(self.image))])
        self.assertEqual({p.name: p.read_bytes() for p in source.glob('*.json')}, before)

    def test_compressed_saved_route_is_exact_and_corruption_stops_before_readers(self):
        source = self.attempt(); path = source / 'ROUTE.json'; original = path.read_bytes(); path.unlink()
        archive.write_record(path, original)
        result = saved.read_attempt(source, self.root / 'ocr', fakes(self.calls))
        self.assertEqual(len(result['pictures']), 2)
        self.assertEqual(archive.read_record(path), original)
        self.assertEqual(self.calls, [('chandra', sha(self.image)), ('pp', sha(self.image)), ('ox', sha(self.image))])
        self.calls.clear(); stored = archive.record_path(path); good = stored.read_bytes()
        for damage in ('corrupt', 'dual'):
            with self.subTest(damage=damage):
                if damage == 'corrupt': stored.write_bytes(b'not gzip')
                else: path.write_bytes(original)
                with self.assertRaises(ValueError): saved.read_attempt(source, self.root / 'ocr', fakes(self.calls))
                self.assertEqual(self.calls, [])
                path.unlink(missing_ok=True); stored.write_bytes(good)

    def test_a_changed_prepared_image_fails_before_any_reader(self):
        source = self.attempt()
        next((source / 'prepared').glob('*.gz')).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            saved.read_attempt(source, self.root / 'ocr', fakes(self.calls))
        self.assertEqual(self.calls, [])

    def test_pdf_pages_reuse_native_renderer_and_keep_every_page(self):
        raw = made((100, 100), (200, 100))
        result = saved.read_pdf(raw, 'original.pdf', sha(raw), self.root / 'ocr', fakes(self.calls))
        self.assertEqual(result['source']['sha256'], sha(raw))
        self.assertEqual([u['page'] for u in result['route']['units']], [1, 2])
        self.assertEqual(len(result['pictures']), 2)
        self.assertEqual(result['route']['status'], 'OK')

    def test_unread_pdf_forms_remain_incomplete_without_calling_readers(self):
        raw = (CASES / 'xfa.pdf').read_bytes()
        result = saved.read_pdf(raw, 'xfa.pdf', sha(raw), self.root / 'ocr', fakes(self.calls))
        self.assertEqual(result['route']['status'], 'PARTIAL')
        self.assertEqual(self.calls, [])
        self.assertTrue(saved.issues(result))

    def test_native_length_finish_and_repetition_are_explicit_in_packets(self):
        source = self.attempt()
        factories = fakes(self.calls)
        reader = factories['chandra']()
        original = reader.read
        def read(data):
            raw, run = original(data)
            return [raw, dict(run, finish_reason='length', repeated=True)]
        reader.read = read
        factories['chandra'] = lambda: reader
        result = saved.read_attempt(source, self.root / 'ocr', factories)
        self.assertTrue(saved.issues(result))
        self.assertIn('cut off', result['pictures'][0]['flags'])
        self.assertIn('repetition', result['pictures'][0]['flags'])
        self.assertIn('INCOMPLETE', result['pictures'][0]['packet'])

    def test_published_supplement_reuses_readings_and_never_certifies_accuracy(self):
        receipt = self.filing()
        config = dict(endpoint='http://unused.invalid/v1', identity=dict(model='control'))
        makers = fakes(self.calls, html='<div data-bbox="0 0 1000 1000" data-label="Text"><p>FAKE</p></div>')
        reference = saved.run(receipt, config, self.root / 'supplement', makers)
        report = saved.verify(reference, receipt)
        self.assertEqual(report['fidelity'], 'unverified')
        self.assertEqual(report['status'], 'complete')
        self.assertEqual(len(report['documents'][0]['pictures']), 2)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(saved.run(receipt, config, self.root / 'supplement', makers), reference)
        self.assertEqual(len(self.calls), 3)

    def test_published_record_damage_and_foreign_source_are_rejected(self):
        receipt = self.filing()
        reference = saved.run(receipt, dict(identity=dict(model='control')), self.root / 'supplement', fakes(self.calls))
        report = saved.verify(reference, receipt)
        record = report['documents'][0]['pictures'][0]['records']['chandra']
        path = Path(record['root']) / (record['sha256'] + '.gz')
        intact = path.read_bytes()
        path.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): saved.verify(reference, receipt)
        path.write_bytes(intact)
        self.assertEqual(saved.verify(reference, receipt)['fidelity'], 'unverified')
        foreign = dict(receipt, package_sha256='0' * 64)
        with self.assertRaises(ValueError): saved.verify(reference, foreign)

    def test_retry_keeps_good_readers_and_immutable_original_failure(self):
        receipt = self.filing()
        makers = fakes(self.calls, html='<div data-bbox="0 0 1000 1000" data-label="Text"><p>FAKE</p></div>')
        reader = makers['chandra'](); normal = reader.read
        def fail(_): raise RuntimeError('controlled first reading failure')
        reader.read = fail; makers['chandra'] = lambda: reader
        first = saved.run(receipt, {}, self.root / 'supplement', makers)
        self.assertEqual(first['status'], 'failed')
        reader.read = normal
        second = saved.run(receipt, {}, self.root / 'supplement', makers)
        self.assertEqual(second['status'], 'complete')
        self.assertEqual(saved.verify(first, receipt)['status'], 'failed')
        self.assertEqual(saved.verify(second, receipt)['status'], 'complete')
        self.assertEqual([role for role, _ in self.calls], ['pp', 'ox', 'chandra'])

    def test_pdf_publication_rejects_missing_extra_or_reordered_pages_even_when_repinned(self):
        raw = made((100, 100), (200, 100))
        receipt = self.filing([('courtesy.pdf', uu(raw, 'courtesy.pdf'), 'EX-99', '3', None)])
        reference = saved.run(receipt, {}, self.root / 'supplement', fakes(self.calls))
        report = saved.verify(reference, receipt)
        self.assertEqual([d['source']['file_id'] for d in report['documents']], ['doc.htm', 'courtesy.pdf'])
        for damage in ('missing', 'extra', 'reordered'):
            bad = copy.deepcopy(report); document = bad['documents'][1]
            if damage == 'missing':
                document['route']['units'].pop(); document['pictures'].pop()
            elif damage == 'extra':
                document['route']['units'].append(copy.deepcopy(document['route']['units'][-1]))
                document['pictures'].append(copy.deepcopy(document['pictures'][-1]))
            else:
                document['route']['units'].reverse(); document['pictures'].reverse()
            pin = archive.store_blob(reference['root'], saved.encode(bad))
            with self.subTest(damage=damage), self.assertRaises(ValueError): saved.verify(dict(reference, sha256=pin), receipt)
        self.assertEqual(len(saved.verify(reference, receipt)['documents'][1]['pictures']), 2)

    def test_missing_occurrence_or_changed_packet_is_not_verified_even_when_repinned(self):
        receipt = self.filing()
        reference = saved.run(receipt, dict(identity=dict(model='control')), self.root / 'supplement', fakes(self.calls))
        report = saved.verify(reference, receipt)
        for damage in ('omit_picture', 'omit_document', 'packet'):
            bad = copy.deepcopy(report)
            if damage == 'omit_picture': bad['documents'][0]['pictures'].pop()
            elif damage == 'omit_document': bad['documents'].pop()
            else: bad['documents'][0]['pictures'][0]['packet'] += ' invented'
            pin = archive.store_blob(reference['root'], saved.encode(bad))
            with self.subTest(damage=damage), self.assertRaises(ValueError):
                saved.verify(dict(reference, sha256=pin), receipt)
        self.assertEqual(saved.verify(reference, receipt)['fidelity'], 'unverified')

    def test_accepted_states_and_source_child_keep_separate_occurrences_and_shared_readings(self):
        receipt = self.filing()
        initial = self.root / 'attempt_0'
        for target in (initial / 'states/activated@1', initial / 'source_reading'):
            shutil.copytree(initial, target, ignore=shutil.ignore_patterns('states', 'source_reading'))
        complete = json.loads((initial / 'COMPLETE.json').read_text())
        complete['source_reading_complete_sha256'] = sha((initial / 'source_reading/COMPLETE.json').read_bytes())
        (initial / 'COMPLETE.json').write_text(json.dumps(complete))
        result = json.loads(Path(receipt['result']['path']).read_text())
        result['rows'][0].update(states={'activated@1': dict(reconstruct_exit=0, verify_exit=0)},
                                 source_reading=dict(reconstruct_exit=0, verify_exit=0))
        Path(receipt['result']['path']).write_text(json.dumps(result))
        receipt['result']['sha256'] = sha(Path(receipt['result']['path']).read_bytes())
        reference = saved.run(receipt, dict(identity=dict(model='control')), self.root / 'supplement', fakes(self.calls))
        report = saved.verify(reference, receipt)
        self.assertEqual([d['source']['view'] for d in report['documents']], ['initial', 'initial/source_reading', 'activated@1'])
        self.assertEqual([len(d['pictures']) for d in report['documents']], [2, 2, 2])
        self.assertEqual(len(self.calls), 3)


if __name__ == '__main__':
    unittest.main()
