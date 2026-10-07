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
        self.assertEqual(self.units(b'<div style="font-weight:bold"><a id="Item3MarketRisk"><!--Anchor--></a>Item 3.&#160; Quantitative and Qualitative Disclosures about Market Risk</div>' + body)[0], ('heading', 'Item 3. Quantitative and Qualitative Disclosures about Market Risk'))  # the anchor first: the tool's detector saw a heading, its reader found no direct text and dropped it to a paragraph — seven section headings of one file (Codex R3-A)
        self.assertEqual(self.units(b'<div>10<a style="display:block"></a>20</div>' + body)[0], ('text', '10\n20'))  # an empty anchor laid out as a block breaks the line in the browser; left in, the tool keeps the break (removed, it glued "1020": Codex R3-A)
        self.assertEqual(self.units(b'<div>Revenue<a style="display:block"></a>20</div>' + body)[0][1], 'Revenue 20')  # the tool as installed read "Revenue" and lost the 20
        self.assertEqual(self.units(b'<div style="font-weight:bold">Totals<table><tr><td>a</td><td>1</td></tr></table></div>' + body)[0], ('heading', 'Totals'))  # the tool's own terminal heading over a block that holds a table: not read whole here — the table was swallowed by the tool before and is not made part of a heading by us (stated, the tool's)
        self.assertEqual([k for k, _ in self.units(b'<div style="font-weight:bold"><span>Totals</span><table><tr><td>a</td><td>1</td></tr></table></div>' + body)][:2], ['text', 'table'])  # no direct text and a table inside: the tool keeps the table; so do we
        self.assertEqual([t for _, t in self.units(b'<div style="font-weight:bold"><div style="display:inline"><font>H</font><font>unger</font></div> Games</div>' + body)][:2], ['Hunger', 'Games'])  # a block laid out inline keeps the tool's own reading (its "H unger" guard)
        self.assertEqual(self.units(b'<div style="font-weight:bold"><font>Aflac Japan</font></div>' + body)[0], ('text', 'Aflac Japan'))  # a bold line wrapped in a run: the tool's own reading stays (a wider rule made 3,723 such lines headings in 60 files: measured, not taken)
        self.assertEqual(self.units(b'<div style="font-weight:bold"><div>Item 1.</div><div>Business</div></div>' + body)[:2], [('text', 'Item 1.'), ('heading', 'Business')])  # a container of blocks keeps its own segmentation (two units, as the tool reads them)
        self.assertEqual(self.units(b'<div style="font-weight:bold"></div><div style="font-weight:bold"> </div>' + body)[0][1][:9], 'Body text')  # empty blocks: nothing, no error
        self.assertEqual(self.units(b'<p>See <a href="#n3">Note 3</a>, and the rest of the sentence.</p>' + body)[0], ('text', 'See Note 3, and the rest of the sentence.'))  # an ordinary link with text
        self.assertEqual(self.units(b'<p>Debt <a><!--one-->10 million<!--two--></a> outstanding.</p>' + body)[0], ('text', 'Debt 10 million outstanding.'))  # text between comments
        self.assertEqual(self.units(b'<div style="font-weight:bold">Commission File Number <ix:nonNumeric name="dei:EntityFileNumber" contextRef="c1">001-35672</ix:nonNumeric></div>' + body)[0][1], 'Commission File Number 001-35672')  # the cover fact after the inline-XBRL tag (lost before)
        self.assertEqual(self.units(b'<div style="font-weight:bold">Item 1A. <a name="x"></a>Risk Factors</div>' + body)[0], ('heading', 'Item 1A. Risk Factors'))  # the title after an anchor, the anchor left in
        self.assertEqual(self.units(b'<div style="font-weight:bold">Item 6. <a id="x"><!--Anchor--></a>Exhibits</div>' + body)[0], ('heading', 'Item 6. Exhibits'))
        self.assertEqual(self.units(b'<h2>Item 7. <a name="y"></a>MD&amp;A</h2>' + body)[0], ('heading', 'Item 7. MD&A'))  # an <h2>: the tool's own whole reading, unchanged
        self.assertEqual(self.units(b'<ix:nonNumeric name="x"><table><tr><td>a</td><td>1</td></tr></table></ix:nonNumeric>' + body)[0][0], 'table')
        self.assertEqual(self.units(b'<ix:footnote id="fn-1"><div><table><tr><td>Revenue</td><td>2025</td><td>2024</td></tr></table></div></ix:footnote>' + body)[0][0], 'table')  # an inline-XBRL footnote holding a table: the table, its cells apart (the tool as installed read one string, "Revenue20252024")
        self.assertEqual(self.units(b'<div><ix:footnote id="fn-2"><span>(2) Excludes the 2024 charge.</span></ix:footnote></div>' + body)[0], ('text', '(2) Excludes the 2024 charge.'))  # a footnote of inline runs: the tool's own inline reading  # a wrapper holding a table: the table
        cover = b'<div style="font-weight:bold">OR</div><div style="text-align: center; font-size: 10pt; font-weight: bold;">For the quarterly period ended <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c1">December 28, 2024</ix:nonNumeric></div>'
        self.assertEqual(self.units(cover + body)[1], ('heading', 'For the quarterly period ended December 28, 2024'))  # the cover line after a short bold block: the tool takes the whole block for a heading and read it to its first child — the date was lost (one file of 60)
        got = self.units(b'<div style="font-weight:bold">For the quarterly period ended <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c1">December 28, 2024</ix:nonNumeric></div>' + body)
        self.assertEqual(got[:2], [('text', 'For the quarterly period ended'), ('heading', 'December 28, 2024')])  # alone, the tool takes the fact itself for a heading (its skip list is case-mismatched): both parts present, two units — the tool's, stated
        adapter.whole_headings(); self.assertEqual(self.units(b'<div style="font-weight:bold">Item 1A. <a name="x"></a>Risk Factors</div>' + body)[0][1], 'Item 1A. Risk Factors')  # idempotent
        f, u = b'<font style="font-size:9pt;font-weight:400;line-height:120%">', b'<font style="font-size:9pt;font-weight:400;line-height:120%;text-decoration:underline">'
        inline = b'<div style="margin-bottom:12pt;text-align:justify">' + f + b'(b)&#160;&#160;If any Lender requests increased costs referred to in </font>' + u + b'Section 2.11(m)</font>' + f + b', or </font>' + u + b'Section 2.13(d)(i)</font>' + f + b' or amounts under </font>' + u + b'Section 2.14(a)</font>' + f + b' relative to this Agreement.</font></div>'
        self.assertIn('Section 2.11(m), or Section 2.13(d)(i) or amounts under Section 2.14(a) relative', ' '.join(t for _, t in self.units(inline) if t))  # an underlined run inside a sentence that the tool takes for a heading keeps the space before it: not re-read (a first version glued 331 words in the legal exhibits)


    def test_nested_inline_facts_are_read_whole(self):  # Codex's held-out review: the tool read an inline-XBRL text fact only to its first child; two cybersecurity paragraphs were lost
        text = lambda body: ' '.join(' '.join(u.get('text', '') for u in adapter.to_units(adapter.dump(self.parse('<html><body>' + body + '</body></html>').root))).split())
        self.assertEqual(text('<p><ix:nonNumeric>Our <ix:nonNumeric>Chief Financial Officer</ix:nonNumeric> oversees our team.</ix:nonNumeric></p>'), 'Our Chief Financial Officer oversees our team.')
        self.assertEqual(text('<p><ix:continuation>The <ix:nonNumeric>CSIRT</ix:nonNumeric> is responsible for all risks.</ix:continuation></p>'), 'The CSIRT is responsible for all risks.')
        self.assertEqual(text('<p><ix:nonNumeric>No significant incidents.</ix:nonNumeric></p>'), 'No significant incidents.')  # a plain fact, as before
        self.assertEqual(text('<p>ordinary <span>whole</span> text.</p>'), 'ordinary whole text.')
        units = adapter.to_units(adapter.dump(self.parse('<html><body><ix:nonNumeric><p>Amounts</p><table><tr><td>Revenue</td><td>100</td></tr><tr><td>Costs</td><td>50</td></tr></table></ix:nonNumeric></body></html>').root))
        self.assertEqual([[c['text'] for c in u['cells']] for u in units if u['kind'] == 'table'], [['Revenue', '100', 'Costs', '50']])  # a fact holding blocks and a table keeps the tool's own traversal


if __name__ == '__main__':
    unittest.main()
