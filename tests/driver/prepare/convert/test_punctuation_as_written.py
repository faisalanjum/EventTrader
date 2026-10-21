"""Punctuation stays as the source writes it. The tool's cleaner (EdgarTools 5.60.0 HTMLPreprocessor._fix_common_issues, pattern
missing_space_after_punct (\\w{2})([.!?])(?=[A-Z])) wrote a space into the raw page after . ! ? that two word characters precede and a capital
follows, so identifiers the page prints whole were split: "EQT.ST" became "EQT. ST" (AMG 8-K exhibit 99.1), "101.INS" became "101. INS" (LEVI 10-Q
exhibit index). Expected = the original bytes, which the page shows as written (no style here adds a space). The source's own spaces stay, after
punctuation and, as before, in front of it. Runs the real tool (required)."""
import gzip
import hashlib
import unittest
from pathlib import Path

from driver.prepare.convert import edgartools_html as eh

AMG_PACKAGE = Path(__file__).resolve().parents[1] / 'get' / 'fixtures' / '0001004434-23-000015.txt.gz'  # checked in: the whole AMG filing
AMG_SHA256 = '29d91f8e1ee2c61c95cc03f6a2bce509bfabc774d760ca02e41d5526400bd87a'  # amgq12023ex991.htm, 249,079 bytes
# LEVI 10-Q lvis-20240526.htm (sha256 4c1ffc6567c29411e1ed138eb99017bec6df2ea6985a9959f8e20704b4fceba4, 2,057,227 bytes): its exhibit-index row,
# bytes 2043452-2044405 copied verbatim ("101.INS" stands at 2043648-2043655).
LEVI_ROW = (b'<tr><td colspan="3" style="padding:2px 1pt;text-align:left;vertical-align:top"><span style="color:#000000;font-family:\'Times New Roman\','
            b'sans-serif;font-size:10pt;font-weight:400;line-height:100%">101.INS</span></td><td colspan="3" style="padding:0 1pt"/><td colspan="3" '
            b'style="padding:2px 1pt;text-align:justify;vertical-align:top"><span style="color:#000000;font-family:\'Times New Roman\',sans-serif;'
            b'font-size:10pt;font-weight:400;line-height:100%">XBRL Instance Document - the instance document does not appear in the Interactive Data '
            b'File because its XBRL tags are embedded within the Inline XBRL document. Filed herewith.</span></td><td colspan="3" style="padding:0 1pt"/>'
            b'<td colspan="3" style="padding:0 1pt"/><td colspan="3" style="padding:0 1pt"/><td colspan="3" style="padding:0 1pt"/><td colspan="3" '
            b'style="padding:0 1pt"/><td colspan="3" style="padding:0 1pt"/><td colspan="3" style="padding:0 1pt"/><td colspan="3" style="padding:0 1pt"/></tr>')
LEVI_SHA256 = 'a1b78e6ce67545889c5093781f6038f5908eebdce685df0e4e5f7885f2e2fd8c'  # measured on those original bytes


def convert(raw):
    return eh.convert(raw, 'x.htm', hashlib.sha256(raw).hexdigest())


def texts(route):  # every unit's text and every cell's text, in order
    return [x.get('text', '') for u in route['units'] for x in [u] + list(u.get('cells') or [])]


def page(body):
    return ('<html><body>%s</body></html>' % body).encode()


class PunctuationAsWritten(unittest.TestCase):
    def test_a_real_identifier_keeps_the_punctuation_the_page_prints(self):  # failed before: "EQT. ST"
        package = gzip.decompress(AMG_PACKAGE.read_bytes())
        at = package.index(b'<FILENAME>amgq12023ex991.htm'); start = package.index(b'<TEXT>\n', at) + 7
        amg = package[start:package.index(b'</TEXT>', start)]
        self.assertEqual(hashlib.sha256(amg).hexdigest(), AMG_SHA256)
        self.assertEqual(amg.count(b'(EQT.ST)'), 1)
        got = texts(convert(amg))
        self.assertTrue(any('(EQT.ST)' in t for t in got), [t for t in got if 'EQT' in t])
        self.assertFalse(any('EQT. ST' in t for t in got))

    def test_a_real_exhibit_number_keeps_its_written_punctuation(self):  # failed before: "101. INS"
        self.assertEqual(hashlib.sha256(LEVI_ROW).hexdigest(), LEVI_SHA256)
        cells = [c['text'] for u in convert(b'<html><body><table>' + LEVI_ROW + b'</table></body></html>')['units'] for c in u.get('cells') or []]
        self.assertIn('101.INS', cells)
        self.assertNotIn('101. INS', cells)

    def test_text_written_whole_stays_whole(self):  # the class: each failed before, the tool added a space the source does not have
        for written in ('Ameresco Inc.The plan', 'Stop!Now', 'Why?Because', 'EX-101.SCH', 'ABC.DEF', 'v12.Beta'):
            with self.subTest(written=written): self.assertEqual(texts(convert(page('<p>%s</p>' % written))), [written])

    def test_the_sources_own_spaces_and_untouched_shapes_read_as_before(self):  # controls: the same before and after
        for written in ('The plan ended. The new one', 'U.S. GAAP', 'see file.htm now', 'A.B', 'Total 1.5 Million'):
            with self.subTest(written=written): self.assertEqual(texts(convert(page('<p>%s</p>' % written))), [written])
        self.assertEqual(texts(convert(page('<p>Purchased under Sections .13, .14 of the rule .</p>'))), ['Purchased under Sections .13, .14 of the rule .'])  # the existing rule


if __name__ == '__main__':
    unittest.main()
