"""The selected route's three command lines (converter, source formatting, screen step over saved routes) end a document as html_route.prepare ends it
(Codex's review of the visibility candidate, 2026-10-08): a page whose screen step fails is PARTIAL with the step's reason; one whose visibility could
not be read keeps that reason first; a valid route is unchanged. Faults injected by name; offline Chrome (playwright required)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.adapters import edgartools_html as ae, screen_grid as ag, source_formatting as af
from driver.prepare.convert import html_route, screen_grid as sg

PAGES = {'uncertain.htm': b'<style>.gone{display:none}</style><p>FACT 125 <span class="gone">NOTFACT 714</span></p>', 'certain.htm': b'<p>FACT 125 <span style="display:none">NOTFACT 714</span></p>'}
FAULTS = {'none': {}, 'screen': {'measure': RuntimeError('screen fault')}, 'visibility': {'page_visibility': RuntimeError('visibility fault')},
          'both': {'measure': RuntimeError('screen fault'), 'page_visibility': RuntimeError('visibility fault')}}


def faults(names):
    ps = [patch.object(sg, name, side_effect=error) for name, error in names.items()]
    for p in ps: p.start()
    return ps


class Parity(unittest.TestCase):
    def test_the_command_lines_end_each_document_as_the_runtime_does(self):
        from playwright.sync_api import sync_playwright
        for fault, names in FAULTS.items():
            for fid, raw in PAGES.items():
                with self.subTest(fault=fault, page=fid), tempfile.TemporaryDirectory() as d:
                    sha = hashlib.sha256(raw).hexdigest(); src = Path(d) / fid; src.write_bytes(raw)
                    ps = faults(names)
                    try:
                        with sync_playwright() as pw:
                            browser = pw.chromium.launch()
                            try: runtime = html_route.prepare(raw, fid, sha, browser)[0]
                            finally: browser.close()
                        with patch.object(grade, 'load_sources', return_value=[{'file_id': fid, 'path': src, 'sha256': sha, 'split': 'development'}]):
                            ae.main(['--key', 'k', '--split', 'development', '--out', d + '/convert'])
                            af.main(['--key', 'k', '--route', d + '/convert/route', '--out', d + '/format'])
                            ag.main(['--key', 'k', '--route', d + '/format', '--out', d + '/screen'])
                    finally:
                        for p in ps: p.stop()
                    cli = json.loads((Path(d) / 'screen' / (fid + '.json')).read_text())
                    self.assertEqual((cli['status'], cli['error'], cli['units']), (runtime['status'], runtime['error'], runtime['units']))
                    want = {'none': 'OK', 'screen': 'PARTIAL', 'visibility': 'PARTIAL' if fid == 'uncertain.htm' else 'OK', 'both': 'PARTIAL'}[fault]
                    self.assertEqual(runtime['status'], want)  # a certain page asks the browser nothing first

    def test_bytes_the_hash_does_not_name_are_refused_before_any_browser_work(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'uncertain.htm'; src.write_bytes(PAGES['uncertain.htm'])
            with patch.object(sg, 'page_visibility') as asked, patch.object(grade, 'load_sources', return_value=[{'file_id': 'uncertain.htm', 'path': src, 'sha256': hashlib.sha256(b'other').hexdigest(), 'split': 'development'}]):
                with self.assertRaises(ValueError): ae.main(['--key', 'k', '--split', 'development', '--out', d + '/convert'])
            asked.assert_not_called()


if __name__ == '__main__': unittest.main()
