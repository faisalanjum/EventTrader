"""Docling HTML adapter: Docling's document dict -> common route format (shape rules only; no company, no filing text)."""
import copy
import unittest

from driver.prepare.convert.anchor import Visible
from driver.prepare.convert import edgartools_html as eh


class DoclingHtmlAdapterTests(unittest.TestCase):

    def test_a_heading_node_at_the_start_of_a_paragraph_becomes_a_heading_unit_plus_the_rest(self):
        def node(kind, text='', children=(), level=None):  # a stand-in for edgartools' node classes: the type name carries the kind
            cls = type(kind, (), {'text': lambda self: self._t})
            n = cls(); n._t, n.children, n.level = text, list(children), level; return n
        head = node('HeadingNode', 'Interest Rate Swap Agreements', level=3)
        para = node('ParagraphNode', 'Interest Rate Swap Agreements We use swaps to manage risk.', [head, node('TextNode', ' We use swaps to manage risk.')])
        tree = eh.dump(node('DocumentNode', children=[para, node('ParagraphNode', 'Plain paragraph.', [node('TextNode', 'Plain paragraph.')])]))
        units = eh.to_units(tree)
        self.assertEqual([(u['kind'], u['text']) for u in units], [('heading', 'Interest Rate Swap Agreements'), ('text', 'We use swaps to manage risk.'), ('text', 'Plain paragraph.')])
        self.assertEqual(units[0].get('level'), 3)

    def test_source_formatting_step_writes_the_sources_own_strike_through_onto_units_and_cells(self):
        # ledger class I: redlines marked with CSS line-through (and the three tags) become `struck` phrases by anchor; a tool's own wrong claim is dropped
        from driver.prepare.convert import source_formatting as sf
        from driver.prepare.convert import anchor as an
        raw = (b'<p>Applicable <span style="text-decoration:line-through">Eurocurrency Rate</span>Term SOFR Spread</p>'
               b'<table><tr><td><s>LIBOR</s> Loans</td><td>12</td></tr></table><p>Plain words.</p>')
        self.assertEqual([an.norm(an.Visible(raw).at(a, b)) for a, b in an.Visible(raw).struck_runs()], ['Eurocurrency Rate', 'LIBOR'])
        units = an.link(raw, [{'id': 'u0', 'kind': 'text', 'text': 'Applicable Eurocurrency RateTerm SOFR Spread'},
                              {'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'text': 'LIBOR Loans'}, {'r': 0, 'c': 1, 'text': '12'}]},
                              {'id': 'u2', 'kind': 'text', 'text': 'Plain words.', 'struck': ['Plain']}])['units']
        self.assertEqual(sf.apply(raw, units), 2)
        self.assertEqual(units[0]['struck'], ['Eurocurrency Rate']); self.assertEqual(units[1]['cells'][0]['struck'], ['LIBOR'])
        self.assertNotIn('struck', units[1]['cells'][1]); self.assertNotIn('struck', units[2])
        raw2 = b'<style>s{text-decoration:none}</style><p><s>maybe</s> plain words.</p>'  # Codex R10-1: a sheet rule can remove the tag's strike: the converter's own claim stands, nothing is written or dropped where the scanner saw a run
        units2 = an.link(raw2, [{'id': 'u', 'kind': 'text', 'text': 'maybe plain words.', 'struck': ['maybe']}, {'id': 'v', 'kind': 'text', 'text': 'absent'}])['units']
        self.assertEqual(sf.apply(raw2, units2), 0); self.assertEqual(units2[0].get('struck'), ['maybe'])
        for tag, dec in (('s', ''), ('span', ';text-decoration:line-through'), ('del', ''), ('strike', ';text-decoration:line-through')):  # Codex R18 N2: an element with no box paints no line of its own, so no strike is written from it
            raw3 = f'<div><{tag} style="display:contents{dec}">net</{tag}></div>'.encode(); u3 = {'id': 'u', 'kind': 'text', 'text': 'net', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw3)}}
            sf.apply(raw3, [u3]); self.assertNotIn('struck', u3, tag)
        raw4 = b'<p>x <s style="text-decoration-color:transparent">net</s> y</p>'; u4 = {'id': 'u', 'kind': 'text', 'text': 'x net y', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw4)}}
        sf.apply(raw4, [u4]); self.assertNotIn('struck', u4)  # round 19: a line in a colour that paints nothing is no strike to write
        raw3 = b'<style>.x{text-decoration:line-through}</style><p>plain words here.</p>'  # a sheet rule could add a strike: nothing is certified either way
        units3 = an.link(raw3, [{'id': 'u', 'kind': 'text', 'text': 'plain words here.', 'struck': ['plain']}])['units']
        self.assertIsNone(sf.apply(raw3, units3)); self.assertEqual(units3[0].get('struck'), ['plain'])


if __name__ == '__main__':
    unittest.main()


from driver.prepare.convert import edgartools_html as eh

TREE = {'type': 'ContainerNode', 'children': [  # the node dump the adapter makes under the edgartools environment
    {'type': 'HeadingNode', 'text': 'Item 2. Overview', 'level': 2},
    {'type': 'ParagraphNode', 'text': 'Free cash flow is not GAAP(1). See the table.', 'links': [{'text': 'the table', 'href': '#tbl'}]},
    {'type': 'TableNode', 'caption': None, 'rows': [
        [{'text': 'Title', 'colspan': 2, 'rowspan': 1, 'is_header': False}],
        [{'text': '', 'colspan': 1, 'rowspan': 2, 'is_header': False}, {'text': 'Three Months Ended', 'colspan': 3, 'rowspan': 1, 'is_header': True}],
        [{'text': 'Free cash flow(1)', 'colspan': 1, 'rowspan': 1, 'is_header': False}, {'text': '$', 'colspan': 1, 'rowspan': 1, 'is_header': False},
         {'text': '(506', 'colspan': 1, 'rowspan': 1, 'is_header': False}, {'text': ')', 'colspan': 1, 'rowspan': 1, 'is_header': False}]]},
    {'type': 'ListNode', 'children': [{'type': 'ListItemNode', 'text': 'First point'}]},
    {'type': 'ImageNode', 'src': 'x.jpg'},
    {'type': 'ParagraphNode', 'text': '(1) Note text.'}]}


class EdgartoolsHtmlAdapterTests(unittest.TestCase):
    def test_empty_and_control_only_texts_are_not_units(self):
        tree = {'type': 'ContainerNode', 'children': [{'type': 'TextNode', 'text': '\n'}, {'type': 'TextNode', 'text': '\u200e'}, {'type': 'ParagraphNode', 'text': 'Kept'}]}
        self.assertEqual([u['text'] for u in eh.to_units(tree)], ['Kept'])

    def test_units_follow_the_tree_with_mapped_kinds_and_links(self):
        units = eh.to_units(TREE)
        self.assertEqual([u['kind'] for u in units], ['heading', 'text', 'table', 'list_item', 'image', 'text'])
        self.assertEqual(units[0]['level'], 2); self.assertEqual(units[1]['links'], [{'text': 'the table', 'href': '#tbl', 'to': None}])

    def test_rowspans_expire_by_row_even_across_an_empty_or_short_row(self):
        # Codex round 7 (R7-2): A spans 3 rows and B 2; row 1 is empty; C must land in column 1 of row 2, D and E in columns 0 and 1 of row 3
        c = lambda text, rs=1: {'text': text, 'rowspan': rs, 'colspan': 1, 'is_header': False}
        t = {'type': 'TableNode', 'caption': None, 'rows': [[c('A', 3), c('B', 2)], [], [c('C')], [c('D'), c('E')]]}
        self.assertEqual([(x['text'], x['r'], x['c']) for x in eh.to_units(t)[0]['cells']], [('A', 0, 0), ('B', 0, 1), ('C', 2, 1), ('D', 3, 0), ('E', 3, 1)])

    def test_cells_get_grid_positions_from_colspan_and_rowspan(self):
        cells = eh.to_units(TREE)[2]['cells']
        self.assertEqual([(c['r'], c['c'], c['rs'], c['cs'], c['text'], c['header']) for c in cells],
                         [(0, 0, 1, 2, 'Title', False), (1, 1, 1, 3, 'Three Months Ended', True),
                          (2, 1, 1, 1, 'Free cash flow(1)', False), (2, 2, 1, 1, '$', False), (2, 3, 1, 1, '(506', False), (2, 4, 1, 1, ')', False)])

    def test_route_file_is_anchored_by_the_shared_linker(self):
        raw = (b'<p>Item 2. Overview</p><p>Free cash flow is not GAAP<sup>(1)</sup>. See <a href="#tbl">the table</a>.</p><table><tr><td colspan="2">Title</td></tr>'
               b'<tr><td rowspan="2"></td><td colspan="3">Three Months Ended</td></tr><tr><td>Free cash flow<sup>(1)</sup></td><td>$</td><td>(506</td><td>)</td></tr></table>'
               b'<ul><li>First point</li></ul><img src="x.jpg"><p>(1) Note text.</p>')
        tree = copy.deepcopy(TREE); tree['children'][4]['src'], = eh.codes(raw, Visible(raw))  # the tool is given the source with the picture's name as its code, and returns the code (test_picture_names)
        route = eh.route_for(tree, raw, 'acc/f.htm', 'sha', seconds=0.1, version='5.60.0')
        self.assertEqual(route['route']['tool'], 'edgartools')
        self.assertTrue(all(x.get('anchor') for u in route['units'] for x in (u.get('cells') or [u])))
        self.assertEqual(route['units'][-2]['src'], 'x.jpg')  # and the name is given back

    def test_a_tool_crash_is_a_failed_route_not_a_stop(self):  # the one-document call keeps the command line's error boundary
        def crash(raw, vis): raise RuntimeError('the tool stopped')
        route = eh.convert(b'<p>Revenue 10.</p>', 'a.htm', 'abc', crash)
        self.assertEqual((route['status'], route['units'], route['file_id'], route['sha256']), ('FAILED', [], 'a.htm', 'abc')); self.assertIn('the tool stopped', route['error'])
        tree = {'type': 'DocumentNode', 'children': [{'type': 'ParagraphNode', 'text': 'Revenue 10.'}]}
        ok = eh.convert(b'<p>Revenue 10.</p>', 'a.htm', 'abc', lambda raw, vis: (tree, 0.5, 'edgartools X'))
        self.assertEqual((ok['status'], [u['text'] for u in ok['units']], ok['route']['version'], ok['seconds'], ok['route']['settings']['picture_names']), ('OK', ['Revenue 10.'], 'edgartools X', 0.5, 'codes'))


from driver.prepare.convert import screen_grid as sg


class ScreenGridTests(unittest.TestCase):
    def test_every_cell_gets_a_marker_and_its_byte_span(self):
        raw = b'<table><tr><td colspan="2">Title</td></tr><tr><TH>a</TH><td>b</td></tr></table><table><tr><td>x</td></tr></table>'
        marked, spans = sg.tag_cells(raw)
        self.assertEqual(marked.count(b'data-g="'), 4); self.assertEqual(len(spans), 4)  # Title, a, b, x
        self.assertEqual(raw[spans[0][0]:spans[0][1]], b'<td colspan="2">Title</td>'); self.assertEqual(raw[spans[3][0]:spans[3][1]], b'<td>x</td>')
        self.assertTrue(marked.startswith(b'<table><tr><td data-g="0" colspan="2">'))

    def test_screen_columns_come_from_pixel_edges_not_from_colspan(self):
        # DOM says the header spans 2 columns; on screen the value sits under it, a spacer column pushed its DOM index away
        cells = [{'g': 0, 'row': 0, 'x': 100, 'w': 200}, {'g': 1, 'row': 1, 'x': 100, 'w': 20}, {'g': 2, 'row': 1, 'x': 120, 'w': 80}, {'g': 3, 'row': 1, 'x': 200, 'w': 100},
                 {'g': 4, 'row': 2, 'x': 0, 'w': 100}, {'g': 5, 'row': 2, 'x': 120, 'w': 80}, {'g': 6, 'row': 2, 'x': 300, 'w': 0}]  # g=6: hidden (no width)
        grid = sg.screen_grid(cells)
        self.assertEqual(grid[0], (0, 1, 3)); self.assertEqual(grid[1], (1, 1, 1)); self.assertEqual(grid[2], (1, 2, 1)); self.assertEqual(grid[3], (1, 3, 1))
        self.assertEqual(grid[4], (2, 0, 1)); self.assertEqual(grid[5], (2, 2, 1)); self.assertNotIn(6, grid)

    def test_route_cells_take_the_screen_grid_by_their_byte_anchor(self):
        raw = b'<table><tr><td colspan="4">Three Months Ended</td></tr><tr><td>Label</td><td></td><td>$</td><td>769</td></tr></table>'
        marked, spans = sg.tag_cells(raw)
        measured = [{'g': 0, 'row': 0, 'x': 50, 'w': 300}, {'g': 1, 'row': 1, 'x': 0, 'w': 50}, {'g': 2, 'row': 1, 'x': 50, 'w': 0}, {'g': 3, 'row': 1, 'x': 50, 'w': 20}, {'g': 4, 'row': 1, 'x': 70, 'w': 280}]
        units = [{'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 4, 'text': 'Three Months Ended', 'anchor': {'byte_start': spans[0][0], 'byte_end_exclusive': spans[0][1]}},
                                                        {'r': 1, 'c': 3, 'rs': 1, 'cs': 1, 'text': '769', 'anchor': {'byte_start': spans[4][0], 'byte_end_exclusive': spans[4][1]}}]}]
        n = sg.apply(units, spans, {0: measured})
        self.assertEqual(n, 2)
        self.assertEqual((units[0]['cells'][0]['c'], units[0]['cells'][0]['cs']), (1, 2)); self.assertEqual(units[0]['cells'][1]['c'], 2)
