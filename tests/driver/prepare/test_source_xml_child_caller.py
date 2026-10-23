"""The existing strict XML route as the typed source reading of well-formed inline-XBRL HTML, through the ACTUAL caller (Root
OCR_NATIVE_XML_SOURCE_IMPLEMENT_20261022T2213; OCR). driver/prepare/job.py runs real document.py, reconstruct and browser on loose rows written here
from literal bytes. Expected header content comes from each page's own bytes through lxml (strict) and the standard library's expat - never from
our converter. Rows: the inline-XBRL namespace under two prefixes (with an unused context and unit and a shown, prepared picture); a wrong namespace
and a malformed page (today's HTML source reading, still incomplete); a hidden-only picture (reported, document incomplete); a parent picture that
cannot be prepared (the parent's own check keeps the document incomplete).
Run with the qualified interpreter from this checkout: python -I -B -m unittest tests.driver.prepare.test_source_xml_child_caller
Environment: BROWSER_EXECUTABLE (default: the pinned headless shell path below)."""
import copy, hashlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
import xml.parsers.expat as expat
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
EXE = os.environ.get('BROWSER_EXECUTABLE', '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell')
IX = 'http://www.xbrl.org/2013/inlineXBRL'; XI = 'http://www.xbrl.org/2003/instance'; XHTML = 'http://www.w3.org/1999/xhtml'
sha = lambda b: hashlib.sha256(b).hexdigest()


def page(prefix, ns, body, close_p=True):
    p = prefix
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="{XHTML}" xmlns:{p}="{ns}" xmlns:xbrli="{XI}" xmlns:dei="http://xbrl.sec.gov/dei/2024">'
            f'<head><title>t</title></head><body><div style="display:none"><{p}:header><{p}:hidden>'
            f'<{p}:nonNumeric name="dei:DocumentType" contextRef="c1">10-Q</{p}:nonNumeric></{p}:hidden><{p}:resources>'
            f'<xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000000001</xbrli:identifier></xbrli:entity>'
            f'<xbrli:period><xbrli:instant>2024-03-31</xbrli:instant></xbrli:period></xbrli:context>'
            f'<xbrli:context id="unused"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000000002</xbrli:identifier></xbrli:entity>'
            f'<xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period></xbrli:context>'
            f'<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></{p}:resources></{p}:header></div>'
            f'<p>Revenue grew strongly.{"</p>" if close_p else ""}{body}</body></html>').encode()


SHOWN = '<p><img src="a.png" alt="logo"/></p>'
ROOT_POSITIVE = b'<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><head><meta charset="utf-8"/></head><body><p>Visible words.</p><div style="display:none"><ix:header><ix:hidden><ix:nonNumeric name="fact" contextRef="c">Hidden qualifier</ix:nonNumeric></ix:hidden></ix:header></div></body></html>'
ROOT_HIDDEN = b'<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><head><meta charset="utf-8"/></head><body><p>Visible words.</p><div style="display:none"><ix:header><ix:hidden><ix:nonNumeric name="fact" contextRef="c">Hidden qualifier</ix:nonNumeric></ix:hidden></ix:header><img src="missing.png"/></div></body></html>'
PAGES = {'ix_q': page('q', IX, SHOWN), 'ix_ix': page('ix', IX, SHOWN), 'wrong_ns': page('ix', 'urn:example:not-inline-xbrl', SHOWN),
         'malformed': page('ix', IX, SHOWN, close_p=False), 'hidden_img': page('ix', IX, SHOWN + '<div style="display:none"><img src="b.png" alt="h"/></div>'),
         'parent_pic_fail': page('ix', IX, '<p><img src="missing.png" alt="m"/></p>'),
         # Root OCR_XML_PICTURE_RULE_REVIEW_20261022T2242, exact bytes: the inline-XBRL namespace, an ordinary img with NO XML namespace
         'root_positive': ROOT_POSITIVE, 'root_hidden_present': ROOT_HIDDEN, 'root_hidden_missing': ROOT_HIDDEN,
         'svg_shown': page('ix', IX, '<p><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg></p>')}
ASSETS = {'root_hidden_present': ('missing.png',), 'root_hidden_missing': (), 'root_positive': ()}  # which named pictures each row's package holds (default: a.png, b.png where named)


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (4, 3), (200, 30, 30)).save(b, 'PNG'); return b.getvalue()


def header_expected(raw):
    """Every element inside the inline-XBRL header, independently: lxml strict DOM (name, attributes, own text) and stdlib expat start bytes."""
    from lxml import etree
    tree = etree.fromstring(raw, etree.XMLParser(recover=False, resolve_entities=False)); starts = []
    p = expat.ParserCreate(namespace_separator='}'); p.StartElementHandler = lambda n, a: starts.append((p.CurrentByteIndex, '{' + n if '}' in n else n)); p.Parse(raw, True)
    order = [e for e in tree.iter() if isinstance(e.tag, str)]; assert [e.tag for e in order] == [n for _, n in starts], 'lxml and expat disagree'
    at = {id(e): s for e, (s, _) in zip(order, starts)}; hdr = next(tree.iter('{%s}header' % IX))
    return [(at[id(e)], e.tag, dict(e.attrib), (e.text or '') + ''.join(c.tail or '' for c in e)) for e in hdr.iter() if isinstance(e.tag, str)]


def flat(R):
    out = {}
    def walk(n):
        out[n['anchor']['byte_start']] = n
        for c in n.get('content') or []:
            if isinstance(c, dict): walk(c)
    for n in R['xml']['elements']: walk(n)
    return out


class XmlSourceChildThroughTheCaller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=EXE); version = b.version; b.close()
        cls.t = t = Path(tempfile.mkdtemp(prefix='source_xml_child_caller_')); rows = []; pic = png()
        for name, raw in PAGES.items():
            d = t / name; d.mkdir(); (d / 'page.htm').write_bytes(raw); members = {'page.htm': {'sha256': sha(raw), 'bytes': len(raw)}}
            for m in ASSETS.get(name, ('a.png', 'b.png')):
                if m.encode() in raw: (d / m).write_bytes(pic); members[m] = {'sha256': sha(pic), 'bytes': len(pic)}
            rows.append({'file_id': name + '/page.htm', 'dispatch': 'html', 'directory': str(d), 'filename': 'page.htm', 'source_sha256': sha(raw), 'base': None, 'bundle': None, 'members': members})
        files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / 'driver').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
        man = t / 'MANIFEST.json'; man.write_text(json.dumps({'files': files}))
        body = json.dumps({'runtime_root': str(ROOT), 'runtime_manifest': {'path': str(man), 'sha256': sha(man.read_bytes())}, 'browser_executable': EXE,
                           'browser_executable_sha256': sha(Path(EXE).read_bytes()), 'browser_version': version, 'source_commands': rows}).encode()
        plan = t / 'PLAN.json'; plan.write_bytes(body); cls.out = t / 'out'
        p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'driver/prepare/job.py'), str(plan), sha(body), str(cls.out)],
                           env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', str(t))}, stdin=subprocess.DEVNULL, capture_output=True, timeout=900)
        (t / 'job.stderr').write_bytes(p.stderr); cls.exit = p.returncode
        cls.rows = {r['file_id'].split('/')[0]: r for r in json.loads((cls.out / 'RESULT.json').read_bytes())['rows']}

    def logs(self, name): return self.out / ('logs_%d' % self.rows[name]['ordinal'])
    def attempt(self, name): return self.out / ('attempt_%d' % self.rows[name]['ordinal'])
    def load(self, p): return json.loads(Path(p).read_bytes())

    def test_complete_xml_child_under_the_html_parent(self):
        for name in ('ix_q', 'ix_ix'):
            with self.subTest(name):
                r, a = self.rows[name], self.attempt(name); s = r.get('source_reading') or {}
                self.assertEqual((r['outcome'], s.get('native_status'), s.get('reconstruct_exit'), s.get('verify_exit'), s.get('reasons')), ('verified_saved_output', 'OK', 0, 0, []), r.get('reasons'))
                child = self.load(a / 'source_reading' / 'ROUTE.json'); parent = self.load(a / 'ROUTE.json')
                self.assertEqual(child['route']['name'], 'xml-fields+source-reading'); self.assertEqual(child['route']['settings']['reading'], 'source (not a display state)')
                self.assertEqual((child['file_id'], child['sha256']), (parent['file_id'], parent['sha256']))
                self.assertEqual(self.load(a / 'source_reading' / 'SOURCE.json'), dict(self.load(a / 'SOURCE.json'), reading='source (not a display state)'))
                self.assertEqual(self.load(a / 'COMPLETE.json')['source_reading_complete_sha256'], sha((a / 'source_reading' / 'COMPLETE.json').read_bytes()))
                self.assertFalse(parent['route']['name'].endswith('+source-reading')); self.assertNotIn('xml_elements', parent)  # the displayed route stays the HTML route
                R = self.load(self.logs(name) / 'source_reading' / 'R.json'); self.assertEqual(R['kind'], 'xml'); els = flat(R)
                want = header_expected(PAGES[name]); self.assertGreater(len(want), 10)
                for start, tag, attrs, text in want:
                    got = els.get(start); self.assertIsNotNone(got, (start, tag))
                    self.assertEqual((got['name'], got.get('attributes') or {}, ''.join(x for x in got.get('content') or [] if isinstance(x, str))), (tag, attrs, text))
                ids = {(e['name'], (e.get('attributes') or {}).get('id')) for e in els.values()}
                self.assertIn(('{%s}context' % XI, 'unused'), ids); self.assertIn(('{%s}unit' % XI, 'usd'), ids)  # unused records kept
                pics = [u for u in parent['units'] if u.get('kind') == 'image']; self.assertEqual(len(pics), 1); u = pics[0]
                self.assertIn('input_sha256', u['input'])  # the parent occurrence is prepared, and its own check passed (row verified)
                img = [e for e in els.values() if e['name'] == '{%s}img' % XHTML]; self.assertEqual(len(img), 1)
                self.assertEqual((img[0]['anchor'], img[0]['attributes']['src']), (u['anchor'], u['src']))  # the same complete source span and src
                self.assertNotIn('xml', self.load(self.logs(name) / 'R.json'))  # the parent R is the displayed HTML reading

    def test_wrong_namespace_and_malformed_keep_todays_html_source_reading(self):
        for name in ('wrong_ns', 'malformed'):
            with self.subTest(name):
                r = self.rows[name]; child = self.load(self.attempt(name) / 'source_reading' / 'ROUTE.json')
                self.assertNotEqual(child['route']['name'].split('+')[0], 'xml-fields'); self.assertTrue(child['route']['name'].endswith('+source-reading'))
                self.assertEqual(((r.get('source_reading') or {}).get('native_status'), r['outcome']), ('PARTIAL', 'incomplete'), r.get('reasons'))

    def test_hidden_only_picture_is_reported_and_keeps_the_document_incomplete(self):
        r = self.rows['hidden_img']; raw = PAGES['hidden_img']; child = self.load(self.attempt('hidden_img') / 'source_reading' / 'ROUTE.json')
        b = raw.index(b'<img src="b.png"'); e = raw.index(b'/>', b) + 2
        self.assertEqual(child['status'], 'PARTIAL'); self.assertIn(f'{b}-{e}', child['error'])
        self.assertEqual(r['outcome'], 'incomplete'); self.assertIn('source reading: native status PARTIAL', r['reasons'])

    def test_parent_picture_failure_keeps_the_document_incomplete(self):
        r = self.rows['parent_pic_fail']; s = r.get('source_reading') or {}
        self.assertEqual(s.get('native_status'), 'OK'); self.assertEqual(r['outcome'], 'incomplete')
        self.assertTrue(any(x.startswith('picture preparation error') for x in r['reasons']), r['reasons'])

    def test_missing_or_damaged_xml_child_fails_parent_custody(self):
        sys.path.insert(0, str(ROOT))
        from driver.prepare import reconstruct
        src = self.attempt('ix_q'); reconstruct._custody(src)  # whole: holds
        for how in ('missing', 'route', 'complete'):
            with self.subTest(how):
                d = Path(tempfile.mkdtemp(prefix='xml_child_damage_')) / 'a'; shutil.copytree(src, d)
                c = d / 'source_reading'
                if how == 'missing': shutil.rmtree(c)
                elif how == 'route': (c / 'ROUTE.json').write_bytes((c / 'ROUTE.json').read_bytes().replace(b'0000000002', b'0000000003'))
                else: (c / 'COMPLETE.json').unlink()
                with self.assertRaises(ValueError): reconstruct._custody(d)

    def test_root_positive_and_hidden_unnamespaced_picture(self):  # Root's actual-job false pass: the hidden img must be reported whether its asset is present or not
        r = self.rows['root_positive']; s = r.get('source_reading') or {}
        self.assertEqual((r['outcome'], s.get('native_status')), ('verified_saved_output', 'OK'), r.get('reasons'))
        self.assertEqual(self.load(self.attempt('root_positive') / 'source_reading' / 'ROUTE.json')['route']['name'], 'xml-fields+source-reading')
        b = ROOT_HIDDEN.index(b'<img src="missing.png"'); e = ROOT_HIDDEN.index(b'/>', b) + 2
        for name in ('root_hidden_present', 'root_hidden_missing'):
            with self.subTest(name):
                r = self.rows[name]; child = self.load(self.attempt(name) / 'source_reading' / 'ROUTE.json')
                self.assertEqual(child['route']['name'], 'xml-fields+source-reading'); self.assertEqual(child['status'], 'PARTIAL'); self.assertIn(f'{b}-{e}', child['error'])
                self.assertEqual(r['outcome'], 'incomplete'); self.assertIn('source reading: native status PARTIAL', r['reasons'])

    def test_shown_svg_stays_honest(self):  # an inline svg: its XML element runs to its end tag; the parent's own preparation decides it, never a pass by span size
        r = self.rows['svg_shown']; self.assertEqual(r['outcome'], 'incomplete', r.get('reasons'))
        self.assertTrue(any('picture' in x for x in r['reasons']), r['reasons'])

    def test_duplicate_displayed_occurrence_is_rejected(self):
        sys.path.insert(0, str(ROOT))
        from driver.prepare.convert import html_route
        raw = PAGES['ix_ix']; shown = self.load(self.attempt('ix_ix') / 'ROUTE.json')
        ok, _ = html_route.source_reading(raw, 'ix_ix/page.htm', sha(raw), copy.deepcopy(shown)); self.assertEqual(ok['status'], 'OK', ok.get('error'))
        dup = copy.deepcopy(shown); u = next(x for x in dup['units'] if x.get('kind') == 'image'); dup['units'].append(dict(copy.deepcopy(u), id=u['id'] + '-again'))
        bad, _ = html_route.source_reading(raw, 'ix_ix/page.htm', sha(raw), dup)
        self.assertEqual(bad['status'], 'PARTIAL'); self.assertIn('%d-%d' % (u['anchor']['byte_start'], u['anchor']['byte_end_exclusive']), bad['error'])

    def test_job_exit_is_not_success_with_incomplete_rows(self):
        self.assertEqual(self.exit, 1)


if __name__ == '__main__':
    unittest.main()
