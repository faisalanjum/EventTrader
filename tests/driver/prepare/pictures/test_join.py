"""One document's pictures joined (pictures/join.py; Root ROOT_CONNECTION_ORDER and ROOT_CONNECTION_REVIEW_V3, Oct 9): every picture unit of the route
is an occurrence of it, the route returned whole; every input is archived before any reader starts and is what all three records read; one packet per
input, named by it, measured from its exact bytes; the raw records stay with every occurrence; failures stay explicit; a broken binding stops.
Routes and inputs are the real html_route.prepare and inputs.prepare on test_inputs' standard pictures, in offline Chrome (playwright is required: a
missing install fails, never skips). Fake readers only: no model, no network - this is the connection, not OCR accuracy."""
import copy
import gzip
import hashlib
import io
import os
import tempfile
import types
import unittest

from PIL import Image

from driver.prepare.convert import html_route
from driver.prepare.get import archive
from driver.prepare.get.acquire import AcquisitionError
from driver.prepare.pictures import inputs, join, packets, read_picture, readers
from tests.driver.prepare.pictures.test_inputs import BLACK, MEMBERS, OPAQUE, page

sha = join.sha
DOC = page(b'<img src="opaque.png"><div style="background:#ffffff;padding:4px"><img src="black.png"></div>'
           b'<div style="background:#8899aa;padding:4px"><img src="black.png"></div><table><tr><td>Revenue</td><td><img src="opaque.png"></td></tr></table>')
BLOCK = '<div data-bbox="0 0 1000 1000" data-label="Text"><p>FAKE text</p></div>'


def fakes(calls, html=BLOCK, tokens=7, fail_ox=(), crash=False, boxes=None, settings=None, wider=0):  # the three readers, real status rules, every read logged
    def counted(name, f):
        def read(data): calls.append((name, sha(data))); return f(data)
        return read
    def chandra(data):
        if crash: raise MemoryError('fake: the machine ran out')
        readers._image(data); return [html, dict(generation_tokens=tokens)]
    def free(tool):
        def read(data):
            im = readers._image(data)
            if tool == 'ox' and sha(data) in fail_ox: raise RuntimeError('fake OnnxTR failure')
            return dict(w=im.width + wider, h=im.height, boxes=boxes(im) if boxes else [dict(t='FAKE', box=[1, 1, im.width - 1, im.height - 1])])
        return read
    mk = lambda name, f, status, s: (lambda: types.SimpleNamespace(read=counted(name, f), settings=s, status=status))
    return dict(chandra=mk('chandra', chandra, readers._chandra_status, settings or dict(reader='fake chandra', max_tokens=readers.MAX_TOKENS)),
                pp=mk('pp', free('pp'), readers._free_status, dict(reader='fake pp')), ox=mk('ox', free('ox'), readers._free_status, dict(reader='fake ox')))


class Join(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.routes = {}

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.folder = self.tmp.name; self.calls = []

    def route(self, raw, fid='test/doc.htm'):  # the real route, made once per page; a fresh copy each time (inputs.prepare marks it)
        if raw not in self.routes:
            r, _ = html_route.prepare(raw, fid, sha(raw), self.browser); assert r['status'] == 'OK', r; self.routes[raw] = r
        return copy.deepcopy(self.routes[raw])

    def run_doc(self, raw=DOC, members=MEMBERS, **kw):
        route = self.route(raw); return route, join.read_pictures(raw, route, members, self.browser, self.folder, fakes(self.calls, **kw))[1]

    def test_reference_names_the_packet_and_the_default_is_unchanged(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as f:
            f.write(OPAQUE); f.flush(); free = dict(w=300, h=80, pp=[dict(t='FAKE', box=[1, 1, 299, 79])], ox=[dict(t='FAKE', box=[1, 1, 299, 79])])
            _, flags, plain, rec = read_picture('p', f.name, BLOCK, 7, free, readers.MAX_TOKENS)
            _, flags2, named, rec2 = read_picture('p', f.name, BLOCK, 7, free, readers.MAX_TOKENS, picture_ref='sha256:x')
            self.assertEqual(named.replace('src="sha256:x"', f'src="{f.name}"'), plain); self.assertEqual(flags, flags2)
            self.assertEqual(rec2['picture'], 'sha256:x'); self.assertEqual(dict(rec2, picture=f.name), rec)
            self.assertEqual(packets.packet('p', f.name, BLOCK, None, None, free=free), packets.packet('p', f.name, BLOCK, None, None, free=free, picture_ref=None))

    def test_occurrences_inputs_records_packets_and_the_whole_route(self):
        route, out = self.run_doc(); units = route['units']
        self.assertEqual([e['unit'] for e in out], [k for k, u in enumerate(units) if u['kind'] == 'image'])   # every picture unit, route order
        self.assertEqual([e['input']['how'] for e in out], ['member', 'page', 'page', 'member'])
        for e in out:
            s = e['input']['input_sha256']; self.assertIs(e['input'], units[e['unit']]['input']); self.assertEqual(e['occurrence'], f"test/doc.htm#{e['id']}")
            self.assertEqual({e['records'][r]['image_sha256'] for r in join.READERS}, {s})
            self.assertTrue(e['packet'].startswith(f'<picture id="sha256:{s}" src="sha256:{s}" size='))
        white, dark = out[1], out[2]                         # one transparent member on two backgrounds: two inputs, each its own capture and size
        self.assertEqual(white['input']['member_sha256'], dark['input']['member_sha256']); self.assertNotEqual(white['input']['input_sha256'], dark['input']['input_sha256'])
        for e in (white, dark): self.assertEqual(e['packet_record']['size'], e['input']['size'])
        cell = units[out[3]['unit']]['cell']; table = [u for u in units if u['id'] == cell.get('table')]   # the table-cell picture's table is in the same route
        self.assertEqual(table[0]['kind'], 'table'); self.assertTrue(any('Revenue' in c['text'] for c in table[0]['cells']))
        self.assertEqual(sorted(s for n, s in self.calls if n == 'chandra'), sorted({e['input']['input_sha256'] for e in out}))   # one read per input

    def test_the_archive_holds_the_exact_bytes_after_the_temporary_files_are_gone(self):
        _, out = self.run_doc()
        for e in out:
            s = e['archive']['sha256']; data = archive.load_blob(e['archive']['root'], s)
            self.assertEqual(sha(data), s); self.assertEqual(list(Image.open(io.BytesIO(data)).size), e['packet_record']['size'])
            self.assertEqual(e['packet_record']['picture'], f'sha256:{s}'); self.assertNotIn(tempfile.gettempdir(), e['packet'])

    def test_a_relative_folder_records_an_absolute_archive_root(self):
        _, (e,) = self.run_doc(page(b'<img src="opaque.png">')); self.assertEqual(e['archive']['root'], os.path.join(self.folder, 'inputs'))   # absolute: as before
        here = os.getcwd(); self.addCleanup(os.chdir, here); os.chdir(self.folder); os.mkdir('cwd')
        route = self.route(page(b'<img src="opaque.png">')); _, (r,) = join.read_pictures(page(b'<img src="opaque.png">'), route, MEMBERS, self.browser, 'run', fakes([]))
        os.chdir('cwd')                                                                    # the caller moves on: the recorded root still names the blob
        self.assertEqual(r['archive']['root'], os.path.join(self.folder, 'run', 'inputs')); self.assertEqual(sha(archive.load_blob(r['archive']['root'], r['archive']['sha256'])), r['archive']['sha256'])

    def test_a_wrong_or_missing_archive_blob_stops(self):
        route = self.route(DOC); got = inputs.prepare(DOC, route, MEMBERS, self.browser); s = route['units'][[u['kind'] for u in route['units']].index('image')]['input']['input_sha256']
        path = archive._path(self.folder + '/inputs', s); path.parent.mkdir(parents=True); path.write_bytes(gzip.compress(b'other bytes'))
        with self.assertRaises(AcquisitionError): join.join(route, got, self.folder, fakes(self.calls))
        self.assertEqual(self.calls, [])                                                  # stopped before any reader
        self.folder = tempfile.mkdtemp(dir=self.tmp.name); _, out = self.run_doc(); path = archive._path(out[1]['archive']['root'], out[1]['archive']['sha256']); path.unlink()
        with self.assertRaises(FileNotFoundError): archive.load_blob(out[1]['archive']['root'], out[1]['archive']['sha256'])

    def test_every_input_is_durable_before_any_reading(self):
        route = self.route(DOC); got = inputs.prepare(DOC, route, MEMBERS, self.browser)
        with self.assertRaises(MemoryError): join.join(route, got, self.folder, fakes(self.calls, crash=True))   # the first reading stops the job
        self.assertEqual(len(self.calls), 1)
        for s in {u['input']['input_sha256'] for u in route['units'] if u['kind'] == 'image'}: self.assertEqual(sha(archive.load_blob(self.folder + '/inputs', s)), s)

    def test_one_packet_and_one_second_reading_per_input(self):
        raw = page(b'<img src="opaque.png"><p>again</p><img src="opaque.png"><p>and again</p><img src="opaque.png">'); asked = []
        table = '<div data-bbox="0 0 1000 1000" data-label="Table"><table><tr><td>FAKE</td></tr></table></div>'   # a table: the second reader is asked
        route = self.route(raw); got = inputs.prepare(raw, route, MEMBERS, self.browser)
        _, out = join.join(route, got, self.folder, fakes(self.calls, html=table), enable_sonnet=True, second=lambda p: asked.append(p) or (None, None))
        self.assertEqual(len(out), 3); self.assertEqual(len({e['occurrence'] for e in out}), 3); self.assertEqual(len(asked), 1)
        self.assertTrue(all(e['sonnet_asked'] for e in out)); self.assertEqual(len({e['packet'] for e in out}), 1)
        self.assertEqual([n for n, _ in self.calls], ['chandra', 'pp', 'ox'])

    def test_free_evidence_outside_chandra_blocks_stays_in_the_records(self):
        corner = '<div data-bbox="0 0 100 100" data-label="Text"><p>FAKE</p></div>'
        boxes = lambda im: [dict(t='FAKE', box=[1, 1, 20, 8]), dict(t='Net debt $47.2 million', box=[150, 50, 290, 75])]
        _, out = self.run_doc(page(b'<img src="opaque.png">'), html=corner, boxes=boxes); e = out[0]
        self.assertNotIn('47.2', e['packet']); self.assertNotIn('47.2', str(e['packet_record']))       # the packet is a projection (Root's boundary note)
        for r in ('pp', 'ox'): self.assertIn('Net debt $47.2 million', [b['t'] for b in e['records'][r]['result']['boxes']])

    def test_failures_stay_explicit_with_their_occurrences(self):
        raw = page(b'<img src="broken.png" width="10" height="10"><img src="opaque.png"><div style="background:#ffffff"><img src="black.png"></div>')
        route = self.route(raw); got = inputs.prepare(raw, route, MEMBERS, self.browser); cap = [u['input']['input_sha256'] for u in route['units'] if u.get('input', {}).get('how') == 'page']
        _, (broken, good, captured) = join.join(route, got, self.folder, fakes(self.calls, fail_ox=cap))
        self.assertEqual(broken['input']['how'], 'member'); self.assertNotIn('packet', broken); self.assertIn('picture_error', broken)   # undecodable: no packet,
        self.assertTrue(all(broken['records'][r]['status'] == 'error' and 'PictureError' in broken['records'][r]['error'] for r in join.READERS))   # its errors kept
        self.assertIn('packet', good)
        self.assertEqual((captured['records']['pp']['status'], captured['records']['ox']['status']), ('complete', 'error')); self.assertIn('packet', captured)
        _, (missing,) = self.run_doc(page(b'<img src="missing.png">'))
        self.assertEqual(missing['input'], {'error': 'not a member of the package'}); self.assertNotIn('records', missing)
        self.folder = tempfile.mkdtemp(dir=self.tmp.name); _, out = self.run_doc(page(b'<img src="opaque.png">'), tokens=readers.MAX_TOKENS)   # a new folder: no saved reading
        self.assertEqual(out[0]['records']['chandra']['status'], 'cut off'); self.assertIn('cut off', out[0]['flags'])
        self.assertIn('INCOMPLETE: Chandra stopped at its output limit', out[0]['packet'])

    def test_broken_bindings_stop(self):
        route = self.route(DOC); got = inputs.prepare(DOC, route, MEMBERS, self.browser); img = [u for u in route['units'] if u['kind'] == 'image']
        s1, s2 = img[1]['input']['input_sha256'], img[2]['input']['input_sha256']
        cases = {'bytes swapped': (route, {**got, s1: got[s2], s2: got[s1]}, {}), 'member bytes for a capture': (route, {**got, s1: BLACK}, {}),
                 'bytes missing': (route, {k: v for k, v in got.items() if k != s1}, {}),
                 'no max_tokens': (route, got, dict(settings=dict(reader='fake chandra'))),
                 'a free frame not the picture': (route, got, dict(wider=1))}
        for name, (r, g, kw) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError): join.join(copy.deepcopy(r), g, d, fakes([], **kw))
        missing = self.route(page(b'<img src="opaque.png"><img src="missing.png"><img src="missing.png">'))
        g = inputs.prepare(page(b'<img src="opaque.png"><img src="missing.png"><img src="missing.png">'), missing, MEMBERS, self.browser); u = [x for x in missing['units'] if x['kind'] == 'image']
        for name, ids in (('an error unit shares an input unit\'s id', (0, 1)), ('two error units share an id', (1, 2))):
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                r = copy.deepcopy(missing); v = [x for x in r['units'] if x['kind'] == 'image']; v[ids[1]]['id'] = v[ids[0]]['id']
                with self.assertRaises(ValueError): join.join(r, g, d, fakes([]))
        with tempfile.TemporaryDirectory() as d:
            r = copy.deepcopy(missing); next(x for x in r['units'] if x['kind'] == 'image').pop('input')
            with self.assertRaises(ValueError): join.join(r, g, d, fakes([]))
        with self.assertRaises(ValueError): join.read_pictures(DOC, self.route(page(b'<img src="opaque.png">')), MEMBERS, self.browser, self.folder, fakes([]))   # stale route


if __name__ == '__main__':
    unittest.main()
