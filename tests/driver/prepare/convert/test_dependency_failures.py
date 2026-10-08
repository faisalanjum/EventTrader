"""A dependency the HTML route's fixes need fails loudly and changes nothing (accuracy-fable-1 A6, Codex's probe ported): before, a missing import
returned quietly - the conversion went on without the fixes SETTINGS names - or left them marked applied after a later import failed. Each case runs
in a fresh interpreter, since applying the fixes is once per process: the controlled failure stops the real conversion with an ImportError, nothing is
marked applied, no hook changed; a healthy retry applies once, a second call changes nothing, and the A2/A4 controls read right. Needs EdgarTools."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROBE = r'''
import builtins, sys
from driver.prepare.convert import anchor, edgartools_html as eh
from edgar.documents.strategies import document_builder as db
from edgar.documents.processors.preprocessor import HTMLPreprocessor as P
from edgar.documents.strategies.style_parser import StyleParser
B = db.DocumentBuilder
hooks = lambda: (B._create_node_for_element, B._get_element_text, P._compile_patterns, B._is_page_number_container, B.SKIP_ELEMENTS, B.INLINE_ELEMENTS, StyleParser.parse)
fault, before, real, saved = sys.argv[1], hooks(), builtins.__import__, None
def broken(name, *a, **k):
    if name == fault: raise ImportError('controlled dependency failure')
    return real(name, *a, **k)
if fault == 'SKIP_ELEMENTS': saved = B.SKIP_ELEMENTS; del B.SKIP_ELEMENTS
else: builtins.__import__ = broken
try:
    raw = b'<p>Control 125</p>'; eh.convert(raw, 'case.htm', anchor.sha256(raw)); outcome = 'returned'
except ImportError: outcome = 'ImportError'
finally:
    builtins.__import__ = real
    if saved is not None: B.SKIP_ELEMENTS = saved
assert outcome == 'ImportError', outcome
assert not getattr(B, '_whole_headings', False) and hooks() == before, 'marked applied or changed after the failure'
eh.whole_headings(); once = hooks(); eh.whole_headings(); assert once == hooks() and B._whole_headings, 'not applied once'
raw = b'<p>Debt <ix:exclude>not</ix:exclude> guaranteed</p><p>Debt<ix:nonNumeric> 125</ix:nonNumeric></p>'
r = eh.convert(raw, 'control.htm', anchor.sha256(raw)); assert r['status'] == 'OK' and [u['text'] for u in r['units']] == ['Debt not guaranteed', 'Debt 125'], r
'''


class DependencyFailures(unittest.TestCase):
    def test_a_failed_dependency_stops_the_conversion_and_changes_nothing_and_a_healthy_retry_applies_once(self):  # each failed before
        for fault in ('edgar.documents.nodes', 'edgar.documents.processors.preprocessor', 'edgar.documents.strategies.style_parser', 'SKIP_ELEMENTS'):
            with self.subTest(fault=fault):
                r = subprocess.run([sys.executable, '-B', '-c', PROBE, fault], cwd=ROOT, env=dict(os.environ, PYTHONPATH=''), capture_output=True, text=True, timeout=300)
                self.assertEqual(r.returncode, 0, r.stderr[-3000:])


if __name__ == '__main__':
    unittest.main()
