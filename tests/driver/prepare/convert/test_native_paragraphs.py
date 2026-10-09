"""A paragraph of the tool's that our publication splits keeps one membership (Root, ROOT_ASSESSMENT_GATE of the checkbox-context assessment): the
units made from one EdgarTools ParagraphNode - a heading claim inside it, the blocks it holds, its <br> lines - share one `paragraph` number; a unit
of another paragraph, of no paragraph, or added from the source alone never shares it; a paragraph published as one unit carries none. Membership
is the tool's tree only - not one rendered line, not a question and its answer. Each test first reads the tool's own tree for the same bytes."""
import hashlib
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import edgartools_html as eh

BOX = ('<p style="font-family:Garamond;font-size:12pt;text-align:center"><span style="display:inline-block;width:0.425in">'
       '<span style="font-family:Wingdings;font-size:10pt">x</span><span style="font-size:10pt;font-weight:bold"> </span></span>'
       '<span style="font-size:12pt;font-weight:bold">Quarterly Report Pursuant to Section 13 or 15(d) of the Securities Exchange Act of 1934</span></p>')  # lnc's cover page (G)
RUN_IN = '<p><b>Item 1. Business.</b> We design and sell products to many customers.</p>'
PLAIN = '<p>An ordinary paragraph that stays whole.</p>'


def html(body): return ('<html><body>' + body + '</body></html>').encode()


def route(body):
    raw = html(body); return eh.convert(raw, 'x/t.htm', hashlib.sha256(raw).hexdigest())


def tool_paragraphs(body):
    """The tool's own paragraphs for these bytes, read without the adapter: each ParagraphNode's children as (type, text)."""
    from edgar.documents import parse_html
    out = []
    def walk(n):
        if type(n).__name__ == 'ParagraphNode': out.append([(type(k).__name__, (k.text() or '').strip()) for k in n.children])
        for k in getattr(n, 'children', None) or []: walk(k)
    walk(parse_html(html(body).decode()).root)
    return out


def members(r):
    """paragraph number -> its units as (kind, text), in order; and the units that carry none."""
    groups, alone = {}, []
    for u in r['units']:
        (groups.setdefault(u['paragraph'], []) if 'paragraph' in u else alone).append((u['kind'], u.get('text', '')))  # a table unit has cells, no text
    return groups, alone


class NativeParagraphs(unittest.TestCase):
    def test_a_heading_claim_cut_from_its_paragraph_keeps_the_paragraph(self):  # failed before: no membership; G's lnc box and its label
        for body, kinds in ((BOX, ['TextNode', 'HeadingNode']), (RUN_IN, ['HeadingNode', 'TextNode'])):
            with self.subTest(kinds=kinds):
                self.assertIn(kinds, [[k for k, t in p if t] for p in tool_paragraphs(body + PLAIN)])  # the tool's: one paragraph, a heading claim in it
                groups, alone = members(route(body + PLAIN))
                self.assertEqual(len(groups), 1); self.assertEqual(len(groups[0]), 2)
                self.assertEqual(sorted(k for k, _ in groups[0]), ['heading', 'text'])
                self.assertEqual(alone, [('text', 'An ordinary paragraph that stays whole.')])

    def test_lines_cut_at_br_keep_the_paragraph(self):  # failed before
        body = '<p>First line of an address<br>Second line of an address</p>' + PLAIN
        self.assertTrue(anchor.Visible(html(body)).certain)  # the control runs: lines are cut only on a certified page
        self.assertIn([('TextNode', 'First line of an address'), ('TextNode', ''), ('TextNode', 'Second line of an address')], tool_paragraphs(body))
        r = route(body); groups, alone = members(r)
        self.assertEqual(groups, {0: [('text', 'First line of an address'), ('text', 'Second line of an address')]})
        self.assertEqual([u['id'] for u in r['units'] if 'paragraph' in u], ['u0_line_0', 'u0_line_1'])  # the slices of one unit, its ids as before
        self.assertEqual(alone, [('text', 'An ordinary paragraph that stays whole.')])

    def test_a_paragraph_holding_a_picture_keeps_its_runs_and_its_picture(self):  # failed before
        body = '<p>Text before the picture <img src="box.png" alt="box"> text after the picture</p>' + PLAIN
        self.assertIn(['TextNode', 'ImageNode', 'TextNode'], [[k for k, _ in p] for p in tool_paragraphs(body)])
        groups, alone = members(route(body))
        self.assertEqual(groups, {0: [('text', 'Text before the picture'), ('image', ''), ('text', 'text after the picture')]})
        self.assertEqual(alone, [('text', 'An ordinary paragraph that stays whole.')])

    def test_neighbouring_paragraphs_never_share_even_with_the_same_words(self):  # Codex: identical text in two paragraphs stays two
        groups, alone = members(route(RUN_IN + RUN_IN + BOX))
        self.assertEqual(len(tool_paragraphs(RUN_IN + RUN_IN + BOX)), 3)
        self.assertEqual(len(groups), 3); self.assertEqual(groups[0], groups[1]); self.assertEqual([len(g) for g in groups.values()], [2, 2, 2])
        self.assertEqual(alone, [])

    def test_no_tool_paragraph_no_membership(self):  # never guessed: a block that is no ParagraphNode of the tool's groups nothing
        for body in ('<div>Intro text of the outer block <div>Inner block text here</div> tail text of the outer block</div>',
                     '<div>Lead text <table><tr><td>Cell A</td><td>Cell B</td></tr></table> trailing text</div>', PLAIN):
            with self.subTest(body=body[:30]):
                r = route(body); self.assertTrue(r['units'])
                self.assertEqual(members(r)[0], {})

    def test_a_picture_added_from_the_source_alone_gains_none(self):  # Codex, OCR: the tool made no unit for it, so the tool's tree says nothing of it
        for body in (RUN_IN + '<table><tr><td><img src="logo.png"> Cell text</td></tr></table>', '<p>Before the link <a href="https://x.test/"><img src="d.png"></a> after the link</p>' + RUN_IN):
            with self.subTest(body=body[-40:]):
                r = route(body); added = [u for u in r['units'] if u.get('from') == 'source']
                self.assertEqual(len(added), 1); self.assertNotIn('paragraph', added[0])
                self.assertEqual(len(members(r)[0]), 1)  # RUN_IN's split paragraph still has its number

    def test_a_paragraph_inside_a_paragraph_keeps_its_own(self):  # Root, OCR: the nearest wins. The parser nests one where an inline wrapper (an
        # iXBRL tag) holds a block inside a <p>; under a list item, which is no paragraph, the inner one alone has members
        inner = '<ix:nonNumeric name="a:b"><div>Inner one<br>Inner two</div></ix:nonNumeric>'
        for body, nested, want in (('<p>Outer run ' + inner + '</p>', True, ({0: [('text', 'Inner one'), ('text', 'Inner two')]}, [('text', 'Outer run')])),
                                   ('<p>Outer run ' + inner + ' tail</p>', True, ({0: [('text', 'Outer run'), ('text', 'tail')], 1: [('text', 'Inner one'), ('text', 'Inner two')]}, [])),
                                   ('<ul><li>Item text <p>Inner one<br>Inner two</p></li></ul>', False, ({0: [('text', 'Inner one'), ('text', 'Inner two')]}, [('text', 'Item text')]))):
            with self.subTest(body=body):
                self.assertTrue(anchor.Visible(html(body)).certain)
                self.assertEqual(any(t == 'ContainerNode' and 'Inner one' in s for p in tool_paragraphs(body) for t, s in p), nested)  # the tool's: Inner one's paragraph inside another
                self.assertEqual(members(route(body)), want)

    def test_the_nearest_paragraph_wins_in_the_tools_own_node_classes(self):  # the same rule on a tree built directly: a heading claim in the inner one
        from edgar.documents.nodes import HeadingNode, ParagraphNode, TextNode
        inner = ParagraphNode(); inner.add_child(HeadingNode(content='Inner head', level=2)); inner.add_child(TextNode(content=' inner rest'))
        outer = ParagraphNode(); outer.add_child(TextNode(content='Outer run ')); outer.add_child(inner); outer.add_child(TextNode(content=' outer tail'))
        raw = html('<p>Outer run</p><p>Inner head inner rest</p><p>outer tail</p>')
        groups, alone = members(eh.route_for(eh.dump(outer), raw, 'x/t.htm', hashlib.sha256(raw).hexdigest(), 0, 'test'))
        self.assertEqual(groups, {0: [('text', 'Outer run'), ('text', 'outer tail')], 1: [('heading', 'Inner head'), ('text', 'inner rest')]})
        self.assertEqual(alone, [])

    def test_the_numbers_are_the_documents_own_and_repeat_exactly(self):  # the tool's node ids are random; these are not
        body = RUN_IN + PLAIN + '<p>First line<br>Second line</p><p>Before <img src="a.png"> after</p>'
        self.assertTrue(anchor.Visible(html(body)).certain)  # <br> lines are cut only where the scanner certifies the page (BOX's inline-block does not)
        first, again = route(body), route(body)
        self.assertEqual([(u['id'], u.get('paragraph')) for u in first['units']], [(u['id'], u.get('paragraph')) for u in again['units']])
        self.assertEqual([u['paragraph'] for u in first['units'] if 'paragraph' in u], [0, 0, 1, 1, 2, 2, 2])
        self.assertFalse(any(k.startswith('_') for u in first['units'] for k in u))  # nothing internal is published


if __name__ == '__main__':
    unittest.main()
