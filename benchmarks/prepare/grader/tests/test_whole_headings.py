"""The tool's heading reading, fixed at its boundary (adapters.edgartools_html.whole_headings): a block the tool takes for a heading is read whole — every
descendant's text — as it reads <h1>–<h6>. Runs under the tool's own environment; skipped where EdgarTools is not installed."""
import unittest

from benchmarks.prepare.grader import anchor
from benchmarks.prepare.grader.adapters import edgartools_html as adapter


class WholeHeadings(unittest.TestCase):
    def setUp(self):
        try: from edgar.documents import parse_html; from edgar.documents.strategies import document_builder
        except ImportError: self.skipTest('EdgarTools not installed')
        self.parse = parse_html; adapter.whole_headings()

    def units(self, raw):
        vis = anchor.Visible(raw); return [(u.get('kind'), u.get('text')) for u in adapter.to_units(adapter.dump(self.parse(adapter.named(raw, vis, adapter.codes(raw, vis))).root))]

    def test_a_block_taken_for_a_heading_is_read_whole(self):
        body = b'<p>Body text follows here, long enough to be a paragraph of its own.</p>'
        self.assertEqual(self.units(b'<div style="font-weight:bold">Commission File Number <ix:nonNumeric name="dei:EntityFileNumber" contextRef="c1">001-35672</ix:nonNumeric></div>' + body)[0][1], 'Commission File Number 001-35672')  # the cover fact after the inline-XBRL tag (lost before)
        self.assertEqual(self.units(b'<div style="font-weight:bold">Item 1A. <a name="x"></a>Risk Factors</div>' + body)[0], ('heading', 'Item 1A. Risk Factors'))  # the title after an anchor (named: the anchor is removed, the heading read whole either way)
        self.assertEqual(self.units(b'<div style="font-weight:bold">Item 6. <a id="x"><!--Anchor--></a>Exhibits</div>' + body)[0], ('heading', 'Item 6. Exhibits'))
        self.assertEqual(self.units(b'<h2>Item 7. <a name="y"></a>MD&amp;A</h2>' + body)[0], ('heading', 'Item 7. MD&A'))  # an <h2>: the tool's own whole reading, unchanged
        self.assertEqual(self.units(b'<ix:nonNumeric name="x"><table><tr><td>a</td><td>1</td></tr></table></ix:nonNumeric>' + body)[0][0], 'table')  # a wrapper holding a table: the table
        cover = b'<div style="font-weight:bold">OR</div><div style="text-align: center; font-size: 10pt; font-weight: bold;">For the quarterly period ended <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c1">December 28, 2024</ix:nonNumeric></div>'
        self.assertEqual(self.units(cover + body)[1], ('heading', 'For the quarterly period ended December 28, 2024'))  # the cover line after a short bold block: the tool takes the whole block for a heading and read it to its first child — the date was lost (one file of 60)
        got = self.units(b'<div style="font-weight:bold">For the quarterly period ended <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c1">December 28, 2024</ix:nonNumeric></div>' + body)
        self.assertEqual(got[:2], [('text', 'For the quarterly period ended'), ('heading', 'December 28, 2024')])  # alone, the tool takes the fact itself for a heading (its skip list is case-mismatched): both parts present, two units — the tool's, stated
        adapter.whole_headings(); self.assertEqual(self.units(b'<div style="font-weight:bold">Item 1A. <a name="x"></a>Risk Factors</div>' + body)[0][1], 'Item 1A. Risk Factors')  # idempotent
        f, u = b'<font style="font-size:9pt;font-weight:400;line-height:120%">', b'<font style="font-size:9pt;font-weight:400;line-height:120%;text-decoration:underline">'
        inline = b'<div style="margin-bottom:12pt;text-align:justify">' + f + b'(b)&#160;&#160;If any Lender requests increased costs referred to in </font>' + u + b'Section 2.11(m)</font>' + f + b', or </font>' + u + b'Section 2.13(d)(i)</font>' + f + b' or amounts under </font>' + u + b'Section 2.14(a)</font>' + f + b' relative to this Agreement.</font></div>'
        self.assertIn('Section 2.11(m), or Section 2.13(d)(i) or amounts under Section 2.14(a) relative', ' '.join(t for _, t in self.units(inline) if t))  # an underlined run inside a sentence that the tool takes for a heading keeps the space before it: not re-read (a first version glued 331 words in the legal exhibits)


if __name__ == '__main__':
    unittest.main()
