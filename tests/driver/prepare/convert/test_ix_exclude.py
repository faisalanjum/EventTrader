"""Shown text inside <ix:exclude> (text that belongs to no XBRL fact): the tool skipped the element and so deleted what the page shows - a scale line
"(in thousands)", the "not" of "Debt not guaranteed" (accuracy-fable-1 A4; Codex traced it to the tool's SKIP_ELEMENTS). It is read as the tool reads
its other inline-XBRL tags: inline in its sentence, a container where it holds blocks or a table; hidden stays hidden. Expected = what Chrome shows
(Codex's controls and six more). Runs the real tool (required)."""
import hashlib
import unittest

from driver.prepare.convert import edgartools_html as eh


def route(body):
    raw = ('<html><body>%s</body></html>' % body).encode()
    return raw, eh.convert(raw, 'x.htm', hashlib.sha256(raw).hexdigest())


def texts(r):
    return [x.get('text', '') for u in r['units'] for x in [u] + (u.get('cells') or [])]


class IxExclude(unittest.TestCase):
    def test_shown_text_inside_ix_exclude_is_read_where_the_page_shows_it(self):  # each failed before: the text was deleted
        for body, want in (('<p><ix:exclude>Amounts in millions</ix:exclude> Revenue 125</p>', ['Amounts in millions Revenue 125']),
                           ('<p>Debt <ix:exclude>not</ix:exclude> guaranteed</p>', ['Debt not guaranteed']),
                           ('<p>Total<ix:exclude> (unaudited)</ix:exclude> 125</p>', ['Total (unaudited) 125']),
                           ('<ix:exclude><p>Amounts in millions</p><table><tr><td>Debt</td><td>125</td></tr></table></ix:exclude>', ['Amounts in millions', '', 'Debt', '125']),
                           ('<div><ix:exclude><span style="font-weight:bold">(in thousands)</span></ix:exclude></div><p>Revenue 125</p>', ['(in thousands)', 'Revenue 125']),
                           ('<div style="text-align:center"><ix:exclude><div>Table of Contents</div><div>(Dollars in thousands)</div></ix:exclude></div>',
                            ['Table of Contents', '(Dollars in thousands)']),
                           # where filings put it: inside a tagged text block (a running page header between its paragraphs; a word of its sentence)
                           ('<ix:nonNumeric name="us-gaap:DebtDisclosureTextBlock" contextRef="c1"><div>Note 5. Debt</div><ix:exclude><div style="text-align:center">'
                            'Table of Contents</div><div>(in thousands)</div></ix:exclude><div>Term loan 125</div></ix:nonNumeric>',
                            ['Note 5. Debt', 'Table of Contents', '(in thousands)', 'Term loan 125']),
                           ('<ix:nonNumeric name="us-gaap:DebtDisclosureTextBlock" contextRef="c1"><p>The notes are <ix:exclude>not</ix:exclude> guaranteed.</p></ix:nonNumeric>',
                            ['The notes are not guaranteed.'])):
            with self.subTest(body=body[:60]): self.assertEqual(texts(route(body)[1]), want)

    def test_hidden_ix_exclude_stays_hidden(self):
        self.assertEqual([t.strip() for t in texts(route('<p><ix:exclude style="display:none">not</ix:exclude> guaranteed</p>')[1])], ['guaranteed'])

    def test_the_restored_words_are_anchored_at_their_source_bytes(self):
        raw, r = route('<p>Debt <ix:exclude>not</ix:exclude> guaranteed</p>')
        a = r['units'][0]['anchor']; at = raw.index(b'not')
        self.assertTrue(a['byte_start'] <= at and at + 3 <= a['byte_end_exclusive'], a)


if __name__ == '__main__': unittest.main()
