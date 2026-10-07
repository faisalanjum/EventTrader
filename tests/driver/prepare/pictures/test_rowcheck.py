"""The page checker's comparison rules (pictures/rowcheck.py): wrong readings never pass, the same content written differently
passes, unproven structure stays unresolved. Every case is the original checker's built-in case, verbatim, with its review note
(Codex v5-v8 probes included); ported from prepare_work rowcheck.py on 2026-10-06."""
import unittest

from driver.prepare.pictures.rowcheck import compare, read

# ---- the original case data, verbatim
SPAN2 = ('<table><tr><th></th><th colspan="2">Three Months</th><th colspan="2">Six Months</th></tr><tr><th></th><th>2025</th><th>2024</th>'
         '<th>2025</th><th>2024</th></tr><tr><td>Revenue</td><td>$ 10</td><td>$ 9</td><td>$ 20</td><td>$ 18</td></tr></table>')
must_differ = [  # wrong readings: each must be 'differs' or 'unresolved', never 'same' (v3 cases, then Codex's 14 of Oct 5)
    ('swapped rows', 'Revenue | 10\nCosts | 20', 'Revenue | 20\nCosts | 10'),
    ('single digit', 'Margin | 9%', 'Margin | 8%'),
    ('spaced minus', 'Loss - 10', 'Loss 10'),
    ('unit', 'Assets (in millions) | 10', 'Assets (in thousands) | 10'),
    ('qualifier', 'Profit not above 10', 'Profit above 10'),
    ('currency', 'Assets USD 10 million', 'Assets EUR 10 million'),
    ('quarter', 'Q1 revenue | 10', 'Q2 revenue | 10'),
    ('column headings', '| 2024 | 2023\nRevenue | 10 | 20', '| 2023 | 2024\nRevenue | 10 | 20'),
    ('long labels', 'Net income attributable to Blackstone | 10\nNet income attributable to non-controlling interests | 20',
                    'Net income attributable to Blackstone | 20\nNet income attributable to non-controlling interests | 10'),
    ('label typo', 'Revenue | 10', 'Revenu | 10'),
    ('months swapped', 'Three months ended March 31 | 10', 'Three months ended June 30 | 10'),
    ('nine vs three months', 'Nine months ended | 10', 'Three months ended | 10'),
    ('fraction misread', 'Series J 8 3/8% preferred', 'Series J 8 3/10% preferred'),
    ('placeholder vs minus', '$ | - | $ | 1,360,772', '$ | -1,360,772'),
    ('single-digit value', 'Employees | 5', 'Employees | 7'),
    ('single-digit omission', 'Employees | 5', 'Employees'),
    ('parenthesized value omitted', 'Loss (15)', 'Loss'),
    ('day changed', 'As of March 5, 2024\nRevenue | 10', 'As of March 7, 2024\nRevenue | 10'),
    ('non-date column headers swapped', 'Actual | Forecast\nRevenue | 10 | 20', 'Forecast | Actual\nRevenue | 10 | 20'),
    ('currency moved to another value', 'Revenue | 10 USD\nCosts | 20 EUR', 'Revenue | 10 EUR\nCosts | 20 USD'),
    ('scale moved to another value', 'Revenue | 10 million\nCosts | 20 thousand', 'Revenue | 10 thousand\nCosts | 20 million'),
    ('qualifier moved to another value', 'Revenue | 10 excluding leases\nCosts | 20 including leases', 'Revenue | 10 including leases\nCosts | 20 excluding leases'),
    ('quarter values swapped', 'Q1 revenue | 10\nQ2 revenue | 20', 'Q1 revenue | 20\nQ2 revenue | 10'),
    ('negation omitted', 'Revenue | 10 | 20\nWe do not expect growth', 'Revenue | 10 | 20\nWe expect growth'),
    ('invented prose', 'Revenue | 10 | 20', 'Revenue | 10 | 20\nWe expect a recession'),
    ('truncated label', 'Net income attributable to subsidiaries | 10', 'Net income | 10'),
    ('one-value rows swapped', 'Revenue | 10\nCosts | 20', 'Revenue | 20\nCosts | 10'),
    ('exponent omitted', 'Area m² | 20', 'Area m | 20'),
    ('chart estimate is not a printed value', 'Sales | 7.1%', 'Sales | ~7.1%'),
    ('inequality dropped', 'Leverage | < 60%', 'Leverage | 60%'),
    ('footnote mark dropped', 'Revenue¹ | 10', 'Revenue | 10'),
    ('mark joined to the next cell', 'Base Rent³ | % Total', 'Base Rent | 3% Total'),
    ('checkbox state changed', 'Large accelerated filer ☒', 'Large accelerated filer ☐'),
]
T1 = '<table><thead><tr><th></th><th>2024</th><th>2023</th></tr></thead><tbody><tr><td>Revenue</td><td>$ 10</td><td>$ 9</td></tr></tbody></table>'
must_agree = [  # the same content written differently: each must be 'same'
    ('identical prose', 'Revenue rose 10% to $5 million, not 4.', 'Revenue rose 10% to $5 million, not 4.'),
    ('identical table', T1, T1),
    ('spacing inside cells', '<table><tr><td>Revenue</td><td>$ 1,234</td><td>( 5.6 )</td><td>10 %</td></tr></table>',
                             '<table><tr><td>Revenue</td><td>$1,234</td><td>(5.6)</td><td>10%</td></tr></table>'),
    ('heading in thead or plain th row', '<table><thead><tr><th></th><th>2024</th></tr></thead><tbody><tr><td>Revenue</td><td>10</td></tr></tbody></table>',
                                         '<table><tr><th></th><th>2024</th></tr><tr><td>Revenue</td><td>10</td></tr></table>'),
    ('heading on two lines inside one cell', '<table><tr><th></th><th>June 30<br/>2025</th></tr><tr><td>Cash</td><td>2,375</td></tr></table>',
                                             '<table><tr><th></th><th>June 30 2025</th></tr><tr><td>Cash</td><td>2,375</td></tr></table>'),
    ('answer wrapped in a code fence', '```html\n' + T1 + '\n```', T1),
    ('wrapped label (no cells)', 'Net income attributable to\nnon-controlling interests 20', 'Net income attributable to non-controlling interests 20'),
    ('fraction forms', 'Series J 8³⁄₈% preferred', 'Series J 8 3/8% preferred'),
    ('fraction as HTML marks', '<p>Series J 8<sup>3</sup>/<sub>8</sub>% preferred</p>', 'Series J 8 3/8% preferred'),
    ('raised mark forms', 'Portfolio⁽¹⁾ 32.1%; Coverage² 4.5x', '<p>Portfolio<sup>(1)</sup> 32.1%; Coverage<sup>2</sup> 4.5x</p>'),
    ('single-cell table title (Codex v6: allowed shape)', '<table><tr><th>Credit facility (millions)</th></tr></table>' + T1, '<p>Credit facility (millions)</p>' + T1),
    ('caption and heading before the table', '<table><caption>As of December 31, 2024</caption>' + T1[7:], '<h2>As of December 31, 2024</h2>' + T1),
    ('raised mark as a tag, no table', 'Revenue<sup>1</sup> rose 5% (P &lt; 0.01)', 'Revenue¹ rose 5% (P < 0.01)'),
    ('entities and literal inequalities', '<p>Growth &lt;1% and &gt;0%.</p>', '<p>Growth <1% and >0%.</p>'),
    ('ligature and full-width', 'ﬁnancial ２０２４', 'financial 2024'),
    ('dot leaders', '▪ Item 1. Business . . .  .  .  . 4', '▪ Item 1. Business 4'),
]
must_unresolve = [  # the same text, relationships not proven or the same pieces in another order: never a pass
    ('heading on two lines (no grid)', 'March 31, | December 31,\n2024 | 2023\nRevenue | 10 | 20', 'March 31, 2024 | December 31, 2023\nRevenue | 10 | 20'),
    ('both readers read nothing', '', ' | \n'),
    ('section label: full-width span vs first column (no proof of the role, Codex v7)', T1.replace('<tbody>', '<tbody><tr><td colspan="3">Assets</td></tr>'),
                                             T1.replace('<tbody>', '<tbody><tr><td>Assets</td><td></td><td></td></tr>')),
    ('identical pipe table: no proof of columns', 'Revenue | 10 | 20', 'Revenue | 10 | 20'),
    ('heading span changed (Codex, Oct 5)', SPAN2, SPAN2.replace('colspan="2">Three', 'colspan="3">Three').replace('colspan="2">Six', 'colspan="1">Six')),
    ('value moved by a blank cell', 'Revenue | | 10\nCosts | | 20', 'Revenue | 10 |\nCosts | 20 |'),
    ('table without a grid', 'Revenue\t10\t20\nCosts\t30\t40', 'Revenue\t10\t20\nCosts\t30\t40'),
    ('grid against no grid', T1, '2024\t2023\nRevenue\t$ 10\t$ 9'),
    ('heading stacked differently', '<table><tr><th></th><th>June 30<br/>2025</th><th>December 31<br/>2024</th></tr><tr><td>Cash</td><td>2,375</td><td>3,652</td></tr></table>',
                                    ' | June 30 | December 31\n | 2025 | 2024\nCash | 2,375 | 3,652'),
    ('a cell the reader marks uncertain', T1, T1.replace('<th>2024</th>', '<th data-uncertain>2024</th>')),
    ('a heading alone in its row keeps its span', '<table><tr><th colspan="2">Three Months</th><th></th></tr><tr><th></th><th>2025</th><th>2024</th></tr><tr><td>Sales</td><td>5</td><td>4</td></tr></table>',
                                                  '<table><tr><th colspan="3">Three Months</th></tr><tr><th></th><th>2025</th><th>2024</th></tr><tr><td>Sales</td><td>5</td><td>4</td></tr></table>'),
    ('letter-spaced title against one word', 'F O O T N O T E S', 'FOOTNOTES'),
    ('spaced digits against one number', 'Counts by class 1 2 3 4', 'Counts by class 1234'),
]
span = ('<table><tr><th></th><th colspan="2">Three Months</th><th colspan="2">Six Months</th></tr>'
        '<tr><th></th><th>2025</th><th>2024</th><th>2025</th><th>2024</th></tr>'
        '<tr><td>Net sales</td><td>6022</td><td>5422</td><td>11888</td><td>10665</td></tr></table>')
head_label = span.replace('<th></th>', '<th>Measure</th>', 1)
wrong_span = lambda x: x.replace('colspan="2">Three', 'colspan="3">Three').replace('colspan="2">Six', 'colspan="1">Six')
short = '<table><tr><th></th><th>2024</th><th>2023</th><th>2022</th></tr><tr><td>Revenue</td><td>10</td><td>20</td><td></td></tr></table>'
qualifier = ('<table><tr><th></th><th>2024</th><th>2023</th></tr><tr><td>Revenue</td><td>10</td><td>20</td></tr>'
             '<tr><td>Basis</td><td>Audited</td><td></td></tr></table>')
scope = ('<table><tr><th></th><th>2024</th><th>2023</th></tr><tr><td>Revenue</td><td>10</td><td>20</td></tr></table>'
         '<table><tr><td>Costs</td><td>5</td><td>6</td></tr></table>')
codex_v5 = [  # Codex's v5 review (probes.py), verbatim: each must not pass
    ('old empty-label heading mutation', span, wrong_span(span)),
    ('nonempty heading label bypass', head_label, wrong_span(head_label)),
    ('blank pipe header guessed as continuation', '| Actual | | Forecast\nRevenue | 10 | 20 | 30',
     '<table><tr><th></th><th colspan="2">Actual</th><th>Forecast</th></tr><tr><td>Revenue</td><td>10</td><td>20</td><td>30</td></tr></table>'),
    ('value colspan ignored', short, short.replace('<td>20</td><td></td>', '<td colspan="2">20</td>')),
    ('text qualifier moved to wrong year', qualifier, qualifier.replace('<td>Audited</td><td></td>', '<td></td><td>Audited</td>')),
    ('table boundary ignored', scope, scope.replace('</table><table>', '')),
    ('footnote marker lost', 'Revenue* | 10\n* Excludes leases.', 'Revenue | 10\n* Excludes leases.'),
    ('single digit series merged', 'Counts by class 1 2 3 4', 'Counts by class 1234'),
    ('fraction rounded', 'Preferred rate 8 1/3%', 'Preferred rate 8.3333%'),
    ('inequality stripped by HTML regex', '<p>Growth <1% and >0%.</p>', '<p>Growth 0%.</p>'),
    ('only one table row without grid', 'Revenue\t10\t20', 'Revenue\t10\t20'),
]
TC = '<table><tr><th>2024</th><th>2023</th></tr><tr><td>10</td><td>20</td></tr></table>'
codex_v6 = [  # Codex's v6 review (probes.py), verbatim: each must not pass
    ('caption unit dropped', TC.replace('<table>', '<table><caption>Amounts in millions</caption>'), TC),
    ('caption sign/qualification changed', TC.replace('<table>', '<table><caption>Excludes leases</caption>'), TC.replace('<table>', '<table><caption>Includes leases</caption>')),
    ('loose printed text inside table', TC.replace('</table>', 'Note: unaudited</table>'), TC),
    ('data-uncertain table', TC, TC.replace('<table>', '<table data-uncertain>')),
    ('data-uncertain row', TC, TC.replace('<tr><td>', '<tr data-uncertain><td>')),
    ('unreadable placeholder duplicated', 'Income [?] million', 'Income [?] million'),
    ('numeric sole-row colspan', '<table><tr><th>2024</th><th>2023</th></tr><tr><td colspan="2">10</td></tr></table>', '<table><tr><th>2024</th><th>2023</th></tr><tr><td>10</td><td></td></tr></table>'),
    ('qualifier sole-row colspan', '<table><tr><th>Requirement</th><th>Actual</th></tr><tr><td colspan="2">Waived</td></tr></table>', '<table><tr><th>Requirement</th><th>Actual</th></tr><tr><td>Waived</td><td></td></tr></table>'),
    ('nested-table header span', '<table><tr><td>Summary</td></tr><tr><td><table><tr><th colspan="2">Quarter</th></tr><tr><td>10</td><td>20</td></tr></table></td></tr></table>',
     '<table><tr><td>Summary</td></tr><tr><td><table><tr><th>Quarter</th><th></th></tr><tr><td>10</td><td>20</td></tr></table></td></tr></table>'),
    ('rowspan zero treated as one', '<table><tbody><tr><td rowspan="0">Revenue</td><td>10</td></tr><tr><td>20</td></tr></tbody></table>', '<table><tbody><tr><td rowspan="1">Revenue</td><td>10</td></tr><tr><td>20</td></tr></tbody></table>'),
    ('footnote bullet removed', 'Revenue • 10\n• Excludes leases', 'Revenue 10\n• Excludes leases'),
    ('multiplication dot removed', 'Area = 3∙4', 'Area = 3 4'),
    ('superscript changes meaning', '<p>Area m<sup>2</sup></p>', '<p>Area m<sub>2</sub></p>'),
    ('fraction parts swapped (raised denominator)', '<p>Series J 8<sup>3</sup>/<sub>8</sub>%</p>', '<p>Series J 8<sub>3</sub>/<sup>8</sup>%</p>'),
    ('row split into two rows', '<table><tr><th></th><th>2024</th><th>2023</th></tr><tr><td></td><td>531</td><td>(4)</td></tr></table>',
     '<table><tr><th></th><th>2024</th><th>2023</th></tr><tr><td></td><td>531</td><td></td></tr><tr><td></td><td></td><td>(4)</td></tr></table>'),
]
declared = [  # Codex's v6 format cases: each reader's declared format, decoded once: must be 'same'
    ('escaped plain text, declared HTML', 'Growth &lt;1% and &gt;0%', 'Growth <1% and >0%', 'html', 'text'),
    ('heading-only HTML, declared', '<h2>Revenue</h2>', 'Revenue', 'html', 'text'),
]
Tv = '<table><tr><th></th><th>2024</th><th>2023</th></tr><tr><td>Revenue</td><td>10</td><td>20</td></tr></table>'
SH = '<table><tr><th>2024</th><th>2023</th></tr><tr><td>10</td><td>20</td></tr></table>'
codex_v7 = [  # Codex's v7 review (probes.py), verbatim, compared as declared HTML both ways: (name, a, b, expected)
    ('caption omitted closing tag', '<table><caption>Amounts in millions' + SH[7:], SH, 'not same'),
    ('caption unclosed at EOF', '<p>Sales 10</p><table><caption>Amounts in millions', '<p>Sales 10</p>', 'not same'),
    ('caption unsupported nested block', '<table><caption><p>Amounts in millions</p></caption>' + SH[7:], SH, 'not same'),
    ('numeric paragraphs in cell', '<table><tr><td><p>1</p><p>2</p></td><td>Counts</td></tr></table>', '<table><tr><td>12</td><td>Counts</td></tr></table>', 'not same'),
    ('numeric divs in cell', '<table><tr><td><div>1</div><div>2</div></td><td>Counts</td></tr></table>', '<table><tr><td>12</td><td>Counts</td></tr></table>', 'not same'),
    ('caption line break glues digits', '<table><caption>Year 2024<br>2023</caption>' + SH[7:], '<table><caption>Year 20242023</caption>' + SH[7:], 'not same'),
    ('fraction vs exponent quotient', '<p>Area m<sup>2</sup> / 4 locations</p>', '<p>Area m 2/4 locations</p>', 'not same'),
    ('fraction vs raised reference', '<p>Sales<sup>1</sup> / 2 brands</p>', '<p>Sales 1/2 brands</p>', 'not same'),
    ('Unicode raised reference vs fraction', 'Sales¹ / 2 brands', 'Sales 1/2 brands', 'not same'),
    ('bullet at cell start may be footnote', Tv.replace('<td>10</td>', '<td>• 10</td>'), Tv, 'not same'),
    ('checkbox unchecked vs checked', '<p><input type="checkbox" checked>Yes</p>', '<p><input type="checkbox">Yes</p>', 'not same'),
    ('checkbox disappears', '<p><input type="checkbox" checked>Yes</p>', '<p>Yes</p>', 'not same'),
    ('full-width qualifier with unheaded label column', Tv.replace('</table>', '<tr><td colspan="3">Waived</td></tr></table>'), Tv.replace('</table>', '<tr><td>Waived</td><td></td><td></td></tr></table>'), 'not same'),
    ('section numeric without heading first column', Tv.replace('</table>', '<tr><td colspan="3">10</td></tr></table>'), Tv.replace('</table>', '<tr><td>10</td><td></td><td></td></tr></table>'), 'not same'),
    ('rowspan crosses section boundary', '<table><thead><tr><th rowspan="2">Period</th><th>Year</th></tr></thead><tbody><tr><td>Revenue</td><td>10</td></tr></tbody></table>', '<table><tr><th rowspan="2">Period</th><th>Year</th></tr><tr><td>Revenue</td><td>10</td></tr></table>', 'not same'),
    ('no-heading numeric grid span lost', '<table><tr><td>10</td><td>20</td></tr><tr><td colspan="2">30</td></tr></table>', '<table><tr><td>10</td><td>20</td></tr><tr><td>30</td><td></td></tr></table>', 'not same'),
    ('valid equivalent fraction', '<p>Rate 8<sup>3</sup>/<sub>8</sub>%</p>', '<p>Rate 8⅜%</p>', 'same'),
    ('valid raised marker', '<p>Revenue<sup>1</sup></p>', 'Revenue¹', 'same'),
    ('valid caption vs immediate heading', '<table><caption>Amounts in millions</caption>' + SH[7:], '<h2>Amounts in millions</h2>' + SH, 'same'),
    ('valid inline styling split', '<table><tr><td>Rev<b>enue</b></td><td>12</td></tr></table>', '<table><tr><td>Revenue</td><td>12</td></tr></table>', 'same'),
    ('valid one cell text wrapper', '<table><tr><td>Headline</td></tr></table>' + Tv, '<p>Headline</p>' + Tv, 'same'),
    # Codex listed this as 'same' ('currently allowed'), but it has the very shape of 'Waived' above (only the word differs) and his
    # review asks to keep spans without a proven role and without word lists: no word-free rule can pass one and fail the other.
    ('section fold (same shape as Waived)', Tv.replace('</table>', '<tr><td colspan="3">Assets</td></tr></table>'), Tv.replace('</table>', '<tr><td>Assets</td><td></td><td></td></tr></table>'), 'not same'),
    ('colspan written ²', SH.replace('<td>10</td><td>20</td>', '<td colspan="²">10</td>'), SH.replace('<td>10</td><td>20</td>', '<td colspan="2">10</td>'), 'not same'),
    ('colspan written ٢', SH.replace('<td>10</td><td>20</td>', '<td colspan="٢">10</td>'), SH.replace('<td>10</td><td>20</td>', '<td colspan="2">10</td>'), 'not same'),
    ('duplicate colspan', SH.replace('<td>10</td><td>20</td>', '<td colspan="1" colspan="2">10</td><td>20</td>'), SH, 'not same'),
]
FN = '<p>Revenue• 10; Costs▪ 20</p><p>• Includes leases.</p><p>▪ Excludes leases.</p>'
codex_v7 += [  # Codex's v8 review (PROBES.json), verbatim, and the two withdrawn marker equivalences
    ('two footnote marks swapped', FN, '<p>Revenue▪ 10; Costs• 20</p><p>• Includes leases.</p><p>▪ Excludes leases.</p>', 'not same'),
    ('footnote definition marker removed', FN, FN.replace('<p>• Includes', '<p>Includes'), 'not same'),
    ('footnote definition marker changed', FN, FN.replace('<p>• Includes', '<p>▪ Includes'), 'not same'),
    ('correct footnotes unchanged', FN, FN, 'same'),
    ('literal markers keep their role', '<p>Revenue* 10</p><p>* Includes leases.</p>', '<p>Revenue* 10</p><p>Includes leases.</p>', 'not same'),
    ('list markup unchanged', '<ul><li>Lower costs</li><li>Higher sales</li></ul>', '<ul><li>Lower costs</li><li>Higher sales</li></ul>', 'same'),
    ('list wrapper versus explicitly printed marker needs its role', '<ul><li>Lower costs</li></ul>', '<p>• Lower costs</p>', 'not same'),
    ('different bullet shapes (withdrawn equivalence)', '<p>▪ Item 1. Business 4</p>', '<p>• Item 1. Business 4</p>', 'not same'),
]


def text_same(r):  # text agrees; relationships unproven or text unread (the original checker's helper)
    return r['verdict'] == 'same' or r['why'] in ('columns', 'unreadable')


class ComparisonRules(unittest.TestCase):
    def test_wrong_readings_never_pass(self):
        for name, a, b in must_differ + codex_v5 + codex_v6:
            with self.subTest(name=name):
                self.assertNotEqual(compare(b, a)['verdict'], 'same'); self.assertNotEqual(compare(a, b)['verdict'], 'same')
                self.assertTrue(text_same(compare(a, a)) and text_same(compare(b, b)), "control text must agree with itself")

    def test_same_content_written_differently_passes(self):
        for name, a, b in must_agree:
            with self.subTest(name=name):
                self.assertEqual(compare(b, a)['verdict'], 'same', (read(a)[0], read(b)[0]))

    def test_unproven_structure_or_order_is_unresolved(self):
        for name, a, b in must_unresolve:
            with self.subTest(name=name):
                self.assertEqual(compare(b, a)['verdict'], 'unresolved')

    def test_declared_formats_decode_once(self):
        for name, a, b, fa, fb in declared:
            with self.subTest(name=name):
                self.assertEqual(compare(b, a, fb, fa)['verdict'], 'same')

    def test_codex_v7_v8_html_cases_both_ways(self):
        for name, a, b, want in codex_v7:
            with self.subTest(name=name):
                r1, r2 = compare(b, a, 'html', 'html')['verdict'], compare(a, b, 'html', 'html')['verdict']
                if want == 'same': self.assertEqual((r1, r2), ('same', 'same'))
                else: self.assertTrue(r1 != 'same' and r2 != 'same', (r1, r2))

    def test_plain_text_marker_removed_is_not_same(self):  # Codex v8
        self.assertNotEqual(compare('Revenue• 10\nIncludes leases.', 'Revenue• 10\n• Includes leases.', 'text', 'text')['verdict'], 'same')


if __name__ == '__main__':
    unittest.main()
