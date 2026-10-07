"""Every picture the source shows stands in the output at its own tag (OCR review r12): the tool reads a table's cells and an inline run as text only, so a
picture there got no unit; the adapter adds it from the scanner's inventory, in order, with the cell it stands in — and changes nothing else."""
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import edgartools_html as adapter

RAW = (b'<p>Intro text here.</p>'
       b'<table><tr><td colspan="2"><img src="logo.png"></td></tr><tr><td>Revenue</td><td>10 <img src="up.png"></td></tr></table>'
       b'<p>Before <span><b><img src="x.png"></b></span> after.</p>'
       b'<div style="display:none"><img src="x.png"></div>'
       b'<table><tr><td>Outer <table><tr><td><img src="in.png"></td></tr></table></td></tr></table>'
       b'<p>End <img src="x.png"> end.</p>')


def tool(*children):
    """A stand-in for the tool's dump: the given nodes under a document; a table as rows of {text, colspan, rowspan, is_header}."""
    return {'type': 'DocumentNode', 'children': list(children)}


def para(text): return {'type': 'ParagraphNode', 'text': text}


def cells(*rows, code=None): return {'type': 'TableNode', 'caption': None, **({'code': code} if code else {}), 'rows': [[{'text': t, 'colspan': cs, 'rowspan': 1, 'is_header': False} for t, cs in row] for row in rows]}


def table_code(raw, k=0):  # the code the tool returns for the k-th shown table of the source (edgartools_html.codes; test_table_identity)
    return [c for c, (start, name) in sorted(adapter.codes(raw, anchor.Visible(raw)).items(), key=lambda kv: kv[1][0]) if name is None][k]


class EveryPicture(unittest.TestCase):
    def route(self, tree):
        vis = anchor.Visible(RAW); return adapter.route_for(tree, RAW, 'f.htm', 'sha', 0, 'v', vis=vis)

    def test_each_shown_picture_once_at_its_own_tag_in_order_with_its_cell(self):
        r = self.route(tool(para('Intro text here.'), cells([('', 2)], [('Revenue', 1), ('10', 1)], code=table_code(RAW)), para('Before after.'), para('Outer'), para('End end.')))
        units = r['units']; pics = [u for u in units if u['kind'] == 'image']
        tag = lambda name, k=0: [i for i in range(len(RAW)) if RAW.startswith(b'<img src="%s">' % name.encode(), i)][k]
        self.assertEqual([(u['src'], u['anchor']['byte_start']) for u in pics], [('logo.png', tag('logo.png')), ('up.png', tag('up.png')), ('x.png', tag('x.png')), ('in.png', tag('in.png')), ('x.png', tag('x.png', 2))])  # the hidden copy (the second x.png) gets none; the same bytes shown twice are two units
        self.assertTrue(all(u['from'] == 'source' and u['text'] == '' and u['id'] == 'p%d' % u['anchor']['byte_start'] for u in pics))
        kinds = [u['kind'] if u['kind'] != 'image' else u['src'] for u in units]
        self.assertEqual(kinds, ['text', 'logo.png', 'table', 'up.png', 'text', 'x.png', 'text', 'in.png', 'text', 'x.png'])  # each before the first unit that starts after its tag: the logo in the table's first row before the table unit (whose text starts at "Revenue"), the picture beside "10" after it, an inline one after its paragraph
        t = units[2]; logo, up, inner = pics[0], pics[1], pics[3]
        self.assertEqual((logo['cell']['table'], 'r' in logo['cell']), (t['id'], False))  # an image-only cell: the table unit, no route cell inside
        self.assertEqual((up['cell']['table'], up['cell']['r'], up['cell']['c']), (t['id'], 1, 1))  # among text in a cell: that cell's row and column
        self.assertTrue(RAW[up['cell']['byte_start']:up['cell']['byte_end_exclusive']].startswith(b'<td>10 <img'))  # the scanner's own cell span: from its <td> tag, as the linker and the screen step use it
        self.assertTrue(RAW[inner['cell']['byte_start']:inner['cell']['byte_end_exclusive']].startswith(b'<td><img src="in.png">'))  # nested tables: the innermost cell
        self.assertNotIn('cell', pics[2])  # inline in a paragraph: no cell
        self.assertEqual(r['route']['settings']['pictures'], 'every shown tag')

    def test_the_tools_own_units_and_everything_else_are_unchanged(self):
        vis = anchor.Visible(RAW); known = adapter.codes(RAW, vis); code = {name: c for c, (s, name) in known.items()}
        first_x = next(c for c, (s, name) in sorted(known.items(), key=lambda kv: kv[1][0]) if name == 'x.png')
        tree = tool(para('Intro text here.'), {'type': 'ImageNode', 'src': code['logo.png']}, para('Before after.'), {'type': 'ImageNode', 'src': first_x}, para('End end.'))
        linked = anchor.link(RAW, adapter.to_units(tree, known), vis=vis)['units']
        units = adapter.route_for(tree, RAW, 'f.htm', 'sha', 0, 'v', vis=vis)['units']
        mine = [u for u in units if u.get('from') != 'source']
        self.assertEqual([(u['id'], u['kind'], u.get('text'), u.get('anchor')) for u in mine], [(u['id'], u['kind'], u.get('text'), u.get('anchor')) for u in linked])  # ids, texts, anchors and order as the linker left them
        self.assertEqual(sorted(u['src'] for u in units if u.get('from') == 'source'), ['in.png', 'up.png', 'x.png'])  # only the tags no unit stands at

    def test_a_picture_in_the_documents_first_cell_is_tied_to_that_cell(self):  # the first source cell is index 0 of the scanner's cells
        raw = b'<table><tr><td>Total <img src="t.png"></td><td>5</td></tr></table>'; vis = anchor.Visible(raw)
        units = adapter.route_for(tool(cells([('Total', 1), ('5', 1)], code=table_code(raw))), raw, 'f.htm', 'sha', 0, 'v', vis=vis)['units']
        pic = next(u for u in units if u['kind'] == 'image')
        self.assertEqual((pic['cell'].get('table'), pic['cell'].get('r'), pic['cell'].get('c')), (units[0]['id'], 0, 0))

    def test_no_picture_shown_no_change(self):
        raw = b'<p>Only words.</p><div style="display:none"><img src="h.png"></div>'; vis = anchor.Visible(raw)
        units = [{'id': 'u0', 'kind': 'text', 'text': 'Only words.'}]
        self.assertIs(adapter.with_every_picture(units, vis), units)


if __name__ == '__main__':
    unittest.main()
