"""The preparation boundary with a TEST consumer (not a final AI reader), on frozen routes and saved readings through the pinned fixtures.

Producer: for each of the 8 saved cases, the picture's OCR result from driver.prepare.pictures (computed once per picture bytes and mode,
reused) and one delivery per place a converted HTML document shows those bytes: the image identity, a hash-checked reference to the whole
route, the unit index and tag anchor, and the OCR result by a key bound to the image bytes and the mode. The serialized receipt must equal
the saved one: the current routes (converter of main d4639b096) deliver all 10 occurrences; the pre-fix routes leave AMG's table-cell
chart undelivered. Consumer: rebuilds everything from the delivery and the saved filing package alone (bytes, size and pixels through
driver.prepare.get; route and source hashes; the unit and its tag) and refuses all 9 wrong inputs. Allowed differences: the named route
prefix relocation (provenance.receipt_path_prefix) and the named picture relocation; routes are frozen fixtures and never refreshed here
(a converter change is reviewed as its own combined check). Ported 2026-10-07 from prepare_work handoff_20261006/handoff.py."""
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from driver.prepare import pictures
from driver.prepare.convert import anchor
from driver.prepare.get.acquire import read_package
from driver.prepare.pictures import readers
from tests.driver.prepare.pictures.saved import Saved

H = 'real575_20261005/handoff_20261006/'
RECEIPTS = {('route', False): 'real575_20261005/runs/20261007_main_d4639b096/HANDOFF_routes.json',
            ('route', True): 'real575_20261005/runs/20261007_main_d4639b096/HANDOFF_routes_sonnet_on.json',
            ('route_prefix_broken', False): H + 'HANDOFF_fixed.json', ('route_prefix_broken', True): H + 'HANDOFF_fixed_sonnet_on.json'}
AMG = '5-19_17_0001004434-23-000010_amg-20221231_g5.jpg'
sha = lambda b: hashlib.sha256(b).hexdigest()


class DeliveryError(Exception):
    pass


class Handoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(tmp.cleanup)
        s = cls.s = Saved(tmp.name); cls.tmp = Path(tmp.name)
        members = s.store.members('ocr.handoff') + s.store.members('ocr.handoff.prefix_proof')
        kind = lambda a: s.store.assets[a]['provenance']['kind']
        for a in dict.fromkeys(members):                                   # packages and routes, at their own relative places
            if kind(a) == 'filing_package': s.store.materialize(a, cls.tmp / 'versions' / a.split('/versions/', 1)[1])
        cls.routes = {}
        for k in ('route', 'route_prefix_broken'):
            ids = sorted(a for a in dict.fromkeys(members) if kind(a) == k)
            prefixes = {s.store.assets[a]['provenance']['receipt_path_prefix'] for a in ids}
            if len(ids) != 9 or len(prefixes) != 1: raise AssertionError(f'{k}: expected 9 routes under one named prefix')
            folder = cls.tmp / k
            for a in ids: s.store.materialize(a, folder / '/'.join(a.split('/')[-2:]))
            cls.routes[k] = dict(prefix=prefixes.pop(), folder=folder, ids=ids)
        cls.cases = s.json(H + 'cases.json')
        if len(cls.cases) != 8: raise AssertionError('8 saved cases')

    def route_file(self, path):  # the named prefix relocation, and nothing else
        for r in self.routes.values():
            if path.startswith(r['prefix'] + '/'): return r['folder'] / path[len(r['prefix']) + 1:]
        return Path(path)

    def resolve(self, version, member, expect_sha):  # the image bytes of a filing member, through the get API; anything else is a failure
        man, files = read_package(str(version))
        if member not in files: raise DeliveryError(f'{member}: not in the filing')
        row = next(m for m in man['members'] if m['filename'] == member); data = files[member]
        if sha(data) != row['sha256'] or sha(data) != expect_sha: raise DeliveryError(f'{member}: bytes are not the expected picture')
        try: im = Image.open(io.BytesIO(data)); im.load()
        except Exception as e: raise DeliveryError(f'{member}: does not decode ({type(e).__name__})')
        return data, im.size, files

    def consume(self, d, ocr_results, expected_mode):  # the test consumer: everything from the delivery and the saved package
        img, doc = d['image'], d['document']
        key = d.get('ocr_key')
        if key not in ocr_results: raise DeliveryError('no OCR result for this delivery')
        if key.rpartition(' | ')[2] != img['sha256']: raise DeliveryError('OCR result belongs to a different image')
        ocr = ocr_results[key]
        if ocr['mode'] != expected_mode or ocr['record']['sonnet'] != expected_mode.removeprefix('sonnet '):
            raise DeliveryError('OCR result belongs to a different extraction mode')
        data, size, files = self.resolve(self.tmp / 'versions' / img['accession'] / img['package_sha256'], img['member'], img['sha256'])
        if size != (img['width'], img['height']): raise DeliveryError('image size differs from the delivery')
        route_bytes = self.route_file(doc['route']['path']).read_bytes()
        if sha(route_bytes) != doc['route']['sha256']: raise DeliveryError('stale or wrong document: the route file is not the referenced one')
        route = json.loads(route_bytes); raw = files.get(doc['member'], b'')
        if route['file_id'] != doc['member'] or route['sha256'] != doc['source_sha256'] or sha(raw) != doc['source_sha256']:
            raise DeliveryError('stale or wrong document: the route was not made from this source document')
        units = route['units']
        if not 0 <= d['unit_index'] < len(units): raise DeliveryError('the occurrence is not at the referenced unit')
        u = units[d['unit_index']]; a = u.get('anchor') or {}
        if u['id'] != d['unit_id'] or u['kind'] != 'image' or u.get('src') != img['member'] or a != d['anchor']:
            raise DeliveryError('the occurrence is not at the referenced unit')
        tag = raw[a['byte_start']:a['byte_end_exclusive']]
        if not (tag.lower().startswith(b'<img') and img['member'].encode() in tag): raise DeliveryError('the anchor is not the picture tag')
        return dict(data=data, size=size, route=route, units=units, unit=u, raw=raw, packet=ocr['packet'], record=ocr['record'])   # the whole hash-checked route: every top-level field

    def produce(self, kind, on):
        ocr_by_bytes, deliveries, failures, owner = {}, [], [], {}
        rt = self.routes[kind]
        for case in self.cases:
            r = self.s.by_name[case['file']]; name, pic, html, tok, free, second = self.s.inputs(r)
            data, size, files = self.resolve(self.tmp / 'versions' / case['acc'] / case['package_sha256'], case['member'], case['sha256'])
            self.assertEqual(data, self.s.store.read(r['picture']))           # the bytes the readers read, and the same pixels
            self.assertEqual(Image.open(io.BytesIO(data)).tobytes(), Image.open(pic).tobytes())
            key = (sha(data), 'chandra-bf16 ocr_layout %d; PP-OCRv6 + OnnxTR; sonnet %s; %s' % (readers.MAX_TOKENS, 'on' if on else 'off', pictures.FORMAT))
            if key not in ocr_by_bytes:                                      # identical bytes and settings: one OCR result, reused
                asked, flags, text, rec = pictures.read_picture(name, pic, html, tok, free, readers.MAX_TOKENS, enable_sonnet=on, second=lambda _: tuple(second))
                ocr_by_bytes[key] = dict(key=key[1], mode='sonnet on' if on else 'sonnet off', flags=flags, sonnet_asked=asked, packet=text, record=rec); owner[key] = r
            ocr = ocr_by_bytes[key]; names = {n for n, b in files.items() if sha(b) == key[0]}
            for a in (x for x in rt['ids'] if x.split('/')[-2] == case['acc']):
                route_bytes = self.s.store.read(a); route = json.loads(route_bytes); raw = files[route['file_id']]
                shown = {start for start, n in anchor.Visible(raw).picture_sources.items() if n in names}
                for start in sorted(shown - {(u.get('anchor') or {}).get('byte_start') for u in route['units'] if u['kind'] == 'image'}):
                    failures.append(dict(case=case['file'], document=route['file_id'], tag_byte=start, failure='a picture the page shows has no unit in the HTML route: not delivered'))
                for i, u in enumerate(route['units']):
                    if u['kind'] != 'image' or u.get('src') not in names: continue
                    if not u.get('anchor'): failures.append(dict(case=case['file'], document=route['file_id'], unit_index=i, failure='a picture unit without a source anchor: not delivered')); continue
                    deliveries.append(dict(case=case['file'], image=dict(accession=case['acc'], package_sha256=case['package_sha256'], member=u['src'], sha256=key[0], width=size[0], height=size[1]),
                                           document=dict(member=route['file_id'], source_sha256=route['sha256'], route=dict(path=rt['prefix'] + '/' + '/'.join(a.split('/')[-2:]), sha256=sha(route_bytes))),
                                           unit_index=i, unit_id=u['id'], anchor=u['anchor'], ocr=ocr))
        out = dict(mode='sonnet on' if on else 'sonnet off', deliveries=[{k: v for k, v in d.items() if k != 'ocr'} | dict(ocr_key=d['ocr']['key'] + ' | ' + d['image']['sha256']) for d in deliveries],
                   ocr_results={o['key'] + ' | ' + h: {k: v for k, v in o.items() if k != 'key'} for (h, _), o in ocr_by_bytes.items()}, delivery_failures=failures)
        return json.loads(json.dumps(out)), {o['key'] + ' | ' + h: owner[h, o['key']] for (h, _), o in ocr_by_bytes.items()}

    def refusals(self, received):  # every wrong input fails explicitly, never passes as a path or a tag
        deliveries, refused = received['deliveries'], []
        d0 = deliveries[0]
        other_route = next(d['document'] for d in deliveries if d['document']['member'] != d0['document']['member'])
        for what, change in (('missing image', lambda d: d['image'].update(member=d['image']['member'] + '.missing')),
                             ('wrong bytes', lambda d: d['image'].update(sha256='0' * 64)),
                             ('stale document reference', lambda d: d['document']['route'].update(sha256='0' * 64)),
                             ('route of another document', lambda d: d['document'].update(route=dict(other_route['route']))),
                             ('wrong unit', lambda d: d.update(unit_index=d['unit_index'] + 1))):
            d = copy.deepcopy(d0); change(d)
            try: self.consume(d, received['ocr_results'], received['mode']); refused.append([what, 'NOT REFUSED'])
            except DeliveryError as e: refused.append([what, str(e)])
        other_key = next(d['ocr_key'] for d in deliveries if d['ocr_key'] != d0['ocr_key'])
        for what, change, mode in (("another image's OCR result", lambda d: d.update(ocr_key=other_key), received['mode']),
                                   ('unknown OCR key', lambda d: d.update(ocr_key=d['ocr_key'] + 'x'), received['mode']),
                                   ('missing OCR key', lambda d: d.pop('ocr_key'), received['mode']),
                                   ('another extraction mode', lambda d: None, 'sonnet off' if received['mode'] == 'sonnet on' else 'sonnet on')):
            d = copy.deepcopy(d0); change(d)
            try: self.consume(d, received['ocr_results'], mode); refused.append([what, 'NOT REFUSED'])
            except DeliveryError as e: refused.append([what, str(e)])
        d = copy.deepcopy(d0); d['ocr'] = received['ocr_results'][other_key]   # a stray inline OCR object is never used
        self.assertEqual(self.consume(d, received['ocr_results'], received['mode'])['packet'], received['ocr_results'][d0['ocr_key']]['packet'])
        return refused

    def check(self, kind, on):
        received, owners = self.produce(kind, on)
        refused = self.refusals(received)
        self.assertEqual(len(refused), 9); self.assertNotIn('NOT REFUSED', [m for _, m in refused])
        saved = copy.deepcopy(received)                                     # the receipt as saved: named picture relocation only
        for k, o in saved['ocr_results'].items():
            o['packet'], o['record'] = self.s.relocated(owners[k], o['packet'], o['record'])
        self.assertEqual(dict(saved, refused=refused), self.s.json(RECEIPTS[kind, on]))
        return received

    def test_current_routes_deliver_every_occurrence_with_its_full_context(self):
        for on in (False, True):
            with self.subTest(sonnet='on (saved readings)' if on else 'off'):
                received = self.check('route', on)
                deliveries, failures = received['deliveries'], received['delivery_failures']
                self.assertEqual((len(deliveries), len(received['ocr_results']), failures), (10, 8, []))
                got = [self.consume(d, received['ocr_results'], received['mode']) for d in deliveries]
                by = {}
                for d, g in zip(deliveries, got): by.setdefault(d['case'], []).append((d, g))
                for d, g in zip(deliveries, got):                           # the whole ordered document and the whole OCR output arrive
                    self.assertEqual(g['route'], json.loads(self.route_file(d['document']['route']['path']).read_text())); self.assertIs(g['units'], g['route']['units'])
                    self.assertEqual(g['packet'].split('\n')[1], g['record']['extraction_status']); self.assertEqual(g['record']['sonnet'], 'on' if on else 'off')
                (kd, kg), = by['20p_18_0001357615-23-000123_exhibit103kbr-warrantame001.jpg']   # a long neighbour, in full
                after = kg['units'][kd['unit_index'] + 1]
                self.assertEqual(len(after['text']), 3350); self.assertGreater(after['anchor']['byte_start'], kd['anchor']['byte_end_exclusive'])
                ch = by['2-4_29_0001091667-24-000121_chtr-20241101_g1.jpg']       # identical bytes in two documents: one OCR result, two contexts
                self.assertEqual((len(ch), len({d['document']['member'] for d, _ in ch})), (2, 2)); self.assertEqual(ch[0][0]['ocr_key'], ch[1][0]['ocr_key'])
                self.assertNotEqual(*[g['units'][d['unit_index'] + 1] for d, g in ch])
                eight_k = next(g for d, g in ch if d['document']['member'] == 'chtr-20241101.htm')   # a whole table and the note after it
                t = next(i for i, u in enumerate(eight_k['units']) if u['kind'] == 'table' and i + 1 < len(eight_k['units']) and eight_k['units'][i + 1].get('text', '').startswith('*'))
                table, note = eight_k['units'][t], eight_k['units'][t + 1]
                self.assertEqual(len(table['cells']), 6); self.assertTrue(all(c['text'].strip() and c.get('anchor') for c in table['cells'])); self.assertEqual(note['text'], '* furnished herewith')
                self.assertEqual(len(by['252_490aa199f819107e.jpg']), 2)       # the same picture twice in one document: two occurrences, one result
                for name, want in (('20p_14_0001558370-24-013452_adc-20240930xex10d2017.jpg', 'MISSING'), ('252_490aa199f819107e.jpg', 'INCOMPLETE'), ('253_4dc0fad449463f0e.jpg', 'INCOMPLETE')):
                    self.assertTrue(by.get(name)); self.assertTrue(all(want in g['packet'].split('\n')[1] for _, g in by[name]), name)   # marked as such
                self.assertIn(AMG, by)                                        # the table-cell chart is delivered

    def test_pre_fix_routes_leave_the_table_cell_chart_undelivered(self):
        for on in (False, True):
            with self.subTest(sonnet='on (saved readings)' if on else 'off'):
                received = self.check('route_prefix_broken', on)
                self.assertEqual([x['case'] for x in received['delivery_failures']], [AMG])
                self.assertEqual(len(received['deliveries']), 9)


if __name__ == '__main__':
    unittest.main()
