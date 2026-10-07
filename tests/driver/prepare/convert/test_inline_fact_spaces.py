"""The spaces at the edges of an inline-XBRL fact with no element inside: the page shows them ("Durham, North Carolina 27703"); the tool read such a fact
as terminal text and stripped them ("Carolina27703", "Debt125") - the inline-fact reading reached only facts with an element inside (accuracy-fable-1
A2, Codex's cause and controls). Expected = what Chrome shows; what the source joins stays joined; hidden, nested and table cases as before; the struck
places and anchors follow the kept space. Runs the real tool (required)."""
import hashlib
import unittest

from driver.prepare.convert import edgartools_html as eh
from driver.prepare.convert import source_formatting


def route(body):
    raw = ('<html><body>%s</body></html>' % body).encode()
    return raw, eh.convert(raw, 'x.htm', hashlib.sha256(raw).hexdigest())


def texts(body):
    return [u.get('text', '') for u in route(body)[1]['units']]


class InlineFactSpaces(unittest.TestCase):
    def test_the_spaces_at_a_facts_edges_are_kept_where_the_page_shows_them(self):  # each failed before: the words were glued
        for tag in ('ix:nonNumeric', 'ix:continuation'):
            for body, want in (('<p><b>Debt</b><%s> 125</%s></p>', 'Debt 125'), ('<p><%s>Debt </%s><b>125</b></p>', 'Debt 125'),
                               ('<p>Total<%s>\n125\n</%s>units</p>', 'Total 125 units')):
                with self.subTest(body=body % (tag, tag)): self.assertEqual(texts(body % (tag, tag)), [want])
        address = ('<p style="text-align:center;font-weight:bold"><ix:nonNumeric name="dei:EntityAddressCityOrTown" contextRef="c">Durham</ix:nonNumeric>,\n'
                   '<ix:nonNumeric name="dei:EntityAddressStateOrProvince" contextRef="c">North Carolina</ix:nonNumeric><ix:nonNumeric name="dei:EntityAddressPostalZipCode" contextRef="c"> 27703</ix:nonNumeric></p>')
        self.assertEqual(texts(address), ['Durham, North Carolina 27703'])  # the shape of Codex's real 8-K cover

    def test_what_the_source_joins_stays_joined_and_hidden_nested_and_cells_read_as_before(self):  # controls: the same before and after
        for tag in ('ix:nonNumeric', 'ix:continuation'):
            self.assertEqual(texts('<p><b>12</b><%s>5</%s></p>' % (tag, tag)), ['125'])
            self.assertEqual(texts('<p><b>Debt</b><%s><span> 125</span></%s></p>' % (tag, tag)), ['Debt 125'])
        self.assertEqual(texts('<p>CVS HEALTH CORP<ix:nonNumeric name="x">ORATION</ix:nonNumeric> had</p>'), ['CVS HEALTH CORPORATION had'])
        self.assertEqual(texts('<p>Debt<ix:nonNumeric style="display:none"> 125</ix:nonNumeric></p>'), ['Debt'])
        self.assertEqual(texts('<div style="display:none"><ix:header><ix:hidden><ix:nonNumeric name="dei:X" contextRef="c"> hidden</ix:nonNumeric></ix:hidden></ix:header></div><p>Shown</p>'), ['Shown'])
        t = route('<table><tr><td>Debt</td><td><ix:nonNumeric name="x" contextRef="c"> 125 </ix:nonNumeric></td></tr></table>')[1]['units'][0]
        self.assertEqual([c['text'] for c in t['cells']], ['Debt', '125'])

    def test_the_struck_places_and_the_anchor_follow_the_kept_space(self):
        raw, r = route('<p><s>Debt</s><ix:nonNumeric name="x" contextRef="c"> 125</ix:nonNumeric> due</p>')
        source_formatting.step(raw, r); u = r['units'][0]
        self.assertEqual((u['text'], u['struck'], u['struck_at']), ('Debt 125 due', ['Debt'], [[0, 4]]))  # before: "Debt125 due"
        a = u['anchor']; self.assertTrue(a['byte_start'] <= raw.index(b'Debt') and raw.index(b' due') < a['byte_end_exclusive'], a)


if __name__ == '__main__':
    unittest.main()
