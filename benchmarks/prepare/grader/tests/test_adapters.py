"""Docling HTML adapter: Docling's document dict -> common route format (shape rules only; no company, no filing text)."""
import copy
import json
import unittest

from benchmarks.prepare.grader.adapters import docling_html as dh
from benchmarks.prepare.grader.adapters import edgartools_html as eh

DOC = {  # the DoclingDocument JSON shape that matters: reading order in body, texts, tables with rich cells, groups, pictures
    'furniture': {'children': []},
    'body': {'children': [{'$ref': '#/texts/0'}, {'$ref': '#/tables/0'}, {'$ref': '#/groups/1'}, {'$ref': '#/pictures/0'}, {'$ref': '#/texts/4'}]},
    'texts': [
        {'self_ref': '#/texts/0', 'label': 'section_header', 'level': 2, 'text': 'Free Cash Flow', 'parent': {'$ref': '#/body'}},
        {'self_ref': '#/texts/1', 'label': 'text', 'text': '(LFL)', 'parent': {'$ref': '#/groups/0'}},
        {'self_ref': '#/texts/2', 'label': 'text', 'text': '(a)', 'parent': {'$ref': '#/groups/0'}, 'formatting': {'bold': False, 'italic': False, 'underline': False, 'strikethrough': False, 'script': 'super'}},
        {'self_ref': '#/texts/3', 'label': 'list_item', 'text': 'First point', 'parent': {'$ref': '#/groups/1'}},
        {'self_ref': '#/texts/4', 'label': 'text', 'text': 'See the table below', 'parent': {'$ref': '#/body'}, 'hyperlink': '#tbl'},
        {'self_ref': '#/texts/5', 'label': 'footnote', 'text': '(a) Like for like', 'parent': {'$ref': '#/tables/0'}}],
    'groups': [{'self_ref': '#/groups/0', 'name': 'rich_cell_group_1_2_0', 'label': 'unspecified', 'parent': {'$ref': '#/tables/0'}, 'children': [{'$ref': '#/texts/1'}, {'$ref': '#/texts/2'}]},
               {'self_ref': '#/groups/1', 'name': 'list', 'label': 'list', 'parent': {'$ref': '#/body'}, 'children': [{'$ref': '#/texts/3'}]}],
    'tables': [{'self_ref': '#/tables/0', 'captions': [], 'footnotes': [{'$ref': '#/texts/5'}], 'data': {'num_rows': 3, 'num_cols': 2, 'table_cells': [
        {'start_row_offset_idx': 0, 'end_row_offset_idx': 1, 'start_col_offset_idx': 0, 'end_col_offset_idx': 2, 'text': 'Revenue', 'column_header': True},
        {'start_row_offset_idx': 1, 'end_row_offset_idx': 2, 'start_col_offset_idx': 0, 'end_col_offset_idx': 1, 'text': '', 'column_header': False},
        {'start_row_offset_idx': 1, 'end_row_offset_idx': 2, 'start_col_offset_idx': 1, 'end_col_offset_idx': 2, 'text': '769', 'column_header': False},
        {'start_row_offset_idx': 2, 'end_row_offset_idx': 3, 'start_col_offset_idx': 0, 'end_col_offset_idx': 1, 'text': '', 'column_header': False, 'ref': {'$ref': '#/groups/0'}}]}}],
    'pictures': [{'self_ref': '#/pictures/0', 'label': 'picture'}],
}


NESTED = {'furniture': {'children': [{'$ref': '#/texts/3'}]},
          'body': {'children': [{'$ref': '#/texts/0'}]},
          'texts': [{'self_ref': '#/texts/0', 'label': 'section_header', 'text': 'Part I', 'children': [{'$ref': '#/texts/1'}, {'$ref': '#/texts/2'}]},
                    {'self_ref': '#/texts/1', 'label': 'text', 'text': 'First paragraph.'},
                    {'self_ref': '#/texts/2', 'label': 'text', 'text': 'Second paragraph.'},
                    {'self_ref': '#/texts/3', 'label': 'page_footer', 'text': 'Page 1'}],
          'groups': [], 'tables': [], 'pictures': []}


class DoclingHtmlAdapterTests(unittest.TestCase):
    def test_children_of_a_text_item_are_emitted_after_it_and_furniture_after_the_body(self):
        self.assertEqual([u['text'] for u in dh.to_units(NESTED)], ['Part I', 'First paragraph.', 'Second paragraph.', 'Page 1'])
        self.assertEqual(dh.to_units(NESTED)[3]['kind'], 'clutter')

    def test_route_units_keep_the_tools_own_order_and_furniture_is_marked(self):
        # the gate measures the tool's reading order; the adapter never re-sorts by source position (R8); furniture is a layer, not an order fault
        raw = b'<p>Page 1</p><p>Part I</p><p>First paragraph.</p><p>Second paragraph.</p>'
        route = dh.route_for(NESTED, raw, 'acc/f.htm', 'sha', seconds=0.1, version='2.x')
        self.assertEqual([u['text'] for u in route['units']], ['Part I', 'First paragraph.', 'Second paragraph.', 'Page 1'])
        self.assertEqual([u.get('layer') for u in route['units']], [None, None, None, 'furniture'])
        self.assertTrue(all(u.get('anchor') for u in route['units']))

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

    def test_both_html_adapters_keep_the_same_wrong_order_so_the_gate_measures_the_tool(self):
        first, second = 'First paragraph is sufficiently long for an unambiguous match.', 'Second paragraph is sufficiently long for an unambiguous match.'
        raw = ('<p>' + first + '</p><p>' + second + '</p>').encode()
        doc = {'body': {'children': [{'$ref': '#/texts/0'}, {'$ref': '#/texts/1'}]}, 'texts': [{'self_ref': '#/texts/0', 'label': 'text', 'text': second}, {'self_ref': '#/texts/1', 'label': 'text', 'text': first}]}
        tree = {'type': 'DocumentNode', 'children': [{'type': 'ParagraphNode', 'text': second}, {'type': 'ParagraphNode', 'text': first}]}
        from benchmarks.prepare.grader import grade
        breaks = [grade.gates_for_file(grade.RouteFile(r, raw, 'htm'), 'OK')['order_breaks'] for r in
                  (dh.route_for(doc, raw, 'acc/o.htm', 'sha', 0, 't'), eh.route_for(tree, raw, 'acc/o.htm', 'sha', 0, 't'))]
        self.assertEqual(breaks, [1, 1])

    def test_a_rich_cell_whose_content_sits_in_a_nested_inline_group_keeps_its_text(self):
        doc = json.loads(json.dumps(DOC)); groups = doc.setdefault('groups', []); gi, ti = len(groups), len(doc['texts'])
        groups += [{'self_ref': f'#/groups/{gi}', 'name': 'rich_cell_group_x', 'label': 'unspecified', 'children': [{'$ref': f'#/groups/{gi + 1}'}]},
                   {'self_ref': f'#/groups/{gi + 1}', 'name': 'group', 'label': 'inline', 'children': [{'$ref': f'#/texts/{ti}'}]}]
        doc['texts'].append({'self_ref': f'#/texts/{ti}', 'label': 'text', 'text': 'no later than the Delivery Date'})
        doc['tables'][0]['data']['table_cells'].append({'start_row_offset_idx': 2, 'end_row_offset_idx': 3, 'start_col_offset_idx': 0, 'end_col_offset_idx': 1, 'text': '', 'ref': {'$ref': f'#/groups/{gi}'}})
        cells = next(u for u in dh.to_units(doc) if u['kind'] == 'table')['cells']
        self.assertIn('no later than the Delivery Date', [c['text'] for c in cells])

    def test_a_footnote_body_only_referenced_from_its_table_is_still_emitted_once(self):
        units = dh.to_units(DOC)
        ids = [u['id'] for u in units]
        self.assertEqual(ids.count('#/texts/5'), 1)
        self.assertEqual(ids.index('#/texts/5'), ids.index('#/tables/0') + 1)  # right after its table
        self.assertEqual(next(u for u in units if u['id'] == '#/texts/5')['kind'], 'footnote')


    def test_units_follow_reading_order_with_mapped_kinds(self):
        units = dh.to_units(DOC)
        self.assertEqual([(u['id'], u['kind']) for u in units],
                         [('#/texts/0', 'heading'), ('#/tables/0', 'table'), ('#/texts/5', 'footnote'), ('#/texts/3', 'list_item'), ('#/pictures/0', 'image'), ('#/texts/4', 'text')])
        self.assertEqual(units[0]['level'], 2)
        self.assertEqual(units[5]['links'], [{'text': 'See the table below', 'href': '#tbl', 'to': None}])

    def test_rich_cells_are_read_from_their_pieces_with_marks_apart_and_empty_cells_dropped(self):
        table = dh.to_units(DOC)[1]
        self.assertEqual([(c['r'], c['c'], c['rs'], c['cs'], c['text'], c.get('markers'), c['header']) for c in table['cells']],
                         [(0, 0, 1, 2, 'Revenue', None, True), (1, 1, 1, 1, '769', None, False), (2, 0, 1, 1, '(LFL)', ['(a)'], False)])
        self.assertEqual(table['notes'], ['#/texts/5'])
        self.assertFalse(any(u['id'] in ('#/texts/1', '#/texts/2') for u in dh.to_units(DOC)))  # pieces are not separate units

    def test_marks_come_from_docling_formatting_not_from_their_shape(self):
        doc = json.loads(json.dumps(DOC)); doc['texts'][2]['formatting']['script'] = 'baseline'; doc['texts'][2]['text'] = '(a)'
        self.assertEqual(dh.to_units(doc)[1]['cells'][2], {'r': 2, 'c': 0, 'rs': 1, 'cs': 1, 'text': '(LFL) (a)', 'header': False})  # not raised: part of the text
        doc['texts'][2]['formatting']['script'] = 'super'; doc['texts'][2]['text'] = 'TM'
        self.assertEqual(dh.to_units(doc)[1]['cells'][2]['markers'], ['TM'])  # raised: kept apart, whatever its shape

    def test_source_formatting_step_writes_the_sources_own_strike_through_onto_units_and_cells(self):
        # ledger class I: redlines marked with CSS line-through (and the three tags) become `struck` phrases by anchor; a tool's own wrong claim is dropped
        from benchmarks.prepare.grader.adapters import source_formatting as sf
        from benchmarks.prepare.grader import anchor as an
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
        raw3 = b'<style>.x{text-decoration:line-through}</style><p>plain words here.</p>'  # a sheet rule could add a strike: nothing is certified either way
        units3 = an.link(raw3, [{'id': 'u', 'kind': 'text', 'text': 'plain words here.', 'struck': ['plain']}])['units']
        self.assertIsNone(sf.apply(raw3, units3)); self.assertEqual(units3[0].get('struck'), ['plain'])

    def test_xml_fields_route_reads_names_paths_groups_text_and_positions_and_refuses_broken_input(self):
        # agreement point 4: a strict standard parser, no field list; names expanded, ancestors kept, "n of m" from the nearest repeated ancestor, exact byte spans
        from benchmarks.prepare.grader.adapters import xml_fields as xf
        import xml.parsers.expat as expat
        raw = (b'<?xml version="1.0"?><sub xmlns="urn:x"><data><title>Common &amp; Preferred</title><persons><person><name>Alpha</name><shares>10</shares></person>'
               b'<person><name>Beta</name><shares>0</shares></person></persons></data></sub>')
        units = xf.units_of(raw); R, P1 = raw.index(b'<sub'), raw.index(b'<person>'); P2 = raw.index(b'<person>', P1 + 1)  # an instance is named by its start tag (Codex N2)
        self.assertEqual([(u['name'], u['text'], u['group']) for u in units], [('{urn:x}title', 'Common & Preferred', {'index': 1, 'count': 1, 'at': R}), ('{urn:x}name', 'Alpha', {'index': 1, 'count': 2, 'at': P1}), ('{urn:x}shares', '10', {'index': 1, 'count': 2, 'at': P1}), ('{urn:x}name', 'Beta', {'index': 2, 'count': 2, 'at': P2}), ('{urn:x}shares', '0', {'index': 2, 'count': 2, 'at': P2})])
        facts = {}; us = xf.units_of(b'<r><note>Ownership is <b>not</b> zero.</note><holding amount="10" unit="shares"/><q>1</q><q>2</q></r>', facts)
        self.assertEqual([(u['name'], u['text'], u['siblings']) for u in us], [('note', 'Ownership is not zero.', {'index': 1, 'count': 1}), ('q', '1', {'index': 1, 'count': 2}), ('q', '2', {'index': 2, 'count': 2})])  # prose with an inline element is one field; repeated leaves report their own place
        self.assertEqual(facts, {'attribute_values': 2})  # attribute values are not read, and the route says so
        self.assertEqual(units[3]['path'], ['{urn:x}sub', '{urn:x}data', '{urn:x}persons', '{urn:x}person'])
        a = units[3]['anchor']; self.assertEqual(raw[a['byte_start']:a['byte_end_exclusive']], b'<name>Beta')  # from the start tag to the end of the text: the key's name and text anchors both fall inside
        a = units[0]['anchor']; self.assertEqual(raw[a['byte_start']:a['byte_end_exclusive']], b'<title>Common &amp; Preferred')  # entities inside the text do not shift the span
        with self.assertRaises(expat.ExpatError): xf.units_of(b'<root><number>10</number><discarded')  # Codex R10: a truncated document is refused, never repaired
        raw2 = b'<r><note><![CDATA[a > b & c]]></note></r>'; u = xf.units_of(raw2)[0]  # CDATA: character data; the anchor still starts at the element's own tag
        self.assertEqual((u['text'], raw2[u['anchor']['byte_start']:u['anchor']['byte_end_exclusive']]), ('a > b & c', b'<note><![CDATA[a > b & c]]>'))

    def test_a_cell_printed_wholly_raised_is_kept_as_a_cell(self):
        # Codex round 7 (R7-1): a raised 4 is still the cell's text; superscript is formatting, not proof of a footnote
        doc = copy.deepcopy(DOC); doc['groups'][0]['children'] = [{'$ref': '#/texts/2'}]; doc['texts'][2]['text'] = '4'
        for script, want in (('baseline', ('4', None)), ('super', ('4', None))):
            doc['texts'][2]['formatting']['script'] = script
            cells = next(u for u in dh.to_units(doc) if u['kind'] == 'table')['cells']
            self.assertEqual([(c['text'], c.get('markers')) for c in cells if c['r'] == 2 and c['c'] == 0], [want], script)
        doc['texts'][2]['formatting']['script'] = 'baseline'; doc['texts'][2]['formatting']['strikethrough'] = True
        cells = next(u for u in dh.to_units(doc) if u['kind'] == 'table')['cells']
        self.assertEqual(next(c.get('struck') for c in cells if c['r'] == 2 and c['c'] == 0), ['4'])

    def test_struck_pieces_are_reported_as_struck(self):
        doc = json.loads(json.dumps(DOC)); doc['texts'][4]['formatting'] = {'bold': False, 'italic': False, 'underline': False, 'strikethrough': True, 'script': 'baseline'}
        self.assertEqual(dh.to_units(doc)[5]['struck'], ['See the table below'])

    def test_route_file_is_anchored_by_the_shared_linker(self):
        raw = b'<p>Free Cash Flow</p><table><tr><td colspan="2">Revenue</td></tr><tr><td></td><td>769</td></tr><tr><td>(LFL)<sup>(a)</sup></td></tr></table><ul><li>First point</li></ul><img src="x.jpg"><p>See the table below</p><p>(a) Like for like</p>'
        route = dh.route_for(DOC, raw, 'acc/f.htm', 'sha', seconds=0.1, version='2.x')
        self.assertEqual(route['status'], 'OK'); self.assertEqual(route['route']['tool'], 'docling')
        cell = route['units'][1]['cells'][2]
        self.assertEqual(raw[cell['anchor']['byte_start']:cell['anchor']['byte_end_exclusive']], b'(LFL)<sup>(a)')  # the anchor ends at the last visible character
        self.assertTrue(all(x.get('anchor') for u in route['units'] for x in (u.get('cells') or [u])))


if __name__ == '__main__':
    unittest.main()


from benchmarks.prepare.grader.adapters import edgartools_html as eh

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
        route = eh.route_for(TREE, raw, 'acc/f.htm', 'sha', seconds=0.1, version='5.60.0')
        self.assertEqual(route['route']['tool'], 'edgartools')
        self.assertTrue(all(x.get('anchor') for u in route['units'] for x in (u.get('cells') or [u])))


from benchmarks.prepare.grader.adapters import docling_pdf as dp

PDFDOC = {  # Docling's PDF output: items carry prov (page, bottom-left box, char span); pages carry sizes
    'furniture': {'children': []}, 'body': {'children': [{'$ref': '#/texts/0'}, {'$ref': '#/tables/0'}, {'$ref': '#/texts/1'}]},
    'pages': {'1': {'size': {'width': 612.0, 'height': 792.0}, 'page_no': 1}, '2': {'size': {'width': 612.0, 'height': 792.0}, 'page_no': 2}},
    'texts': [{'self_ref': '#/texts/0', 'label': 'section_header', 'level': 1, 'text': 'Same-Store Operating Information',
               'prov': [{'page_no': 1, 'bbox': {'l': 100.0, 't': 742.0, 'r': 500.0, 'b': 722.0, 'coord_origin': 'BOTTOMLEFT'}, 'charspan': [0, 32]}]},
              {'self_ref': '#/texts/1', 'label': 'text', 'text': 'A paragraph that continues onto the next page.',
               'prov': [{'page_no': 1, 'bbox': {'l': 50.0, 't': 100.0, 'r': 550.0, 'b': 80.0, 'coord_origin': 'BOTTOMLEFT'}, 'charspan': [0, 20]},
                        {'page_no': 2, 'bbox': {'l': 50.0, 't': 760.0, 'r': 550.0, 'b': 740.0, 'coord_origin': 'BOTTOMLEFT'}, 'charspan': [20, 46]}]}],
    'tables': [{'self_ref': '#/tables/0', 'captions': [], 'footnotes': [], 'prov': [{'page_no': 1, 'bbox': {'l': 40.0, 't': 700.0, 'r': 570.0, 'b': 300.0, 'coord_origin': 'BOTTOMLEFT'}}],
                'data': {'num_rows': 2, 'num_cols': 2, 'table_cells': [
                    {'start_row_offset_idx': 0, 'end_row_offset_idx': 1, 'start_col_offset_idx': 1, 'end_col_offset_idx': 2, 'text': 'YTD 24', 'column_header': True, 'bbox': {'l': 400.0, 't': 690.0, 'r': 460.0, 'b': 680.0, 'coord_origin': 'BOTTOMLEFT'}},
                    {'start_row_offset_idx': 1, 'end_row_offset_idx': 2, 'start_col_offset_idx': 0, 'end_col_offset_idx': 1, 'text': '', 'column_header': False},
                    {'start_row_offset_idx': 1, 'end_row_offset_idx': 2, 'start_col_offset_idx': 1, 'end_col_offset_idx': 2, 'text': '1,970', 'column_header': False, 'bbox': {'l': 454.0, 't': 343.0, 'r': 474.0, 'b': 334.0, 'coord_origin': 'BOTTOMLEFT'}}]}}],
    'groups': [], 'pictures': [],
}


class DoclingPdfAdapterTests(unittest.TestCase):
    def test_pdf_routes_declare_their_page_sizes(self):
        route = dp.route_for_pdf(PDFDOC, 'acc/d.pdf', 'sha', 1.0, '2.x')
        self.assertEqual(route['pages'], {1: [612.0, 792.0], 2: [612.0, 792.0]})

    def test_native_pdf_anchors_are_top_left_page_regions_from_docling_boxes(self):
        route = dp.route_for_pdf(PDFDOC, 'acc/deck.pdf', 'sha', seconds=12.0, version='2.x')
        heading, table, para = route['units']
        self.assertEqual(heading['anchor'], {'page': 1, 'region': [100.0, 50.0, 500.0, 70.0]})   # 792 - 742 = 50, 792 - 722 = 70
        self.assertEqual(table['cells'][1]['anchor'], {'page': 1, 'region': [454.0, 449.0, 474.0, 458.0]})
        self.assertEqual([c['text'] for c in table['cells']], ['YTD 24', '1,970'])  # empty cells dropped
        self.assertEqual(para['anchor'], [{'page': 1, 'region': [50.0, 692.0, 550.0, 712.0]}, {'page': 2, 'region': [50.0, 32.0, 550.0, 52.0]}])  # a block over two pages
        self.assertEqual(route['status'], 'OK'); self.assertEqual(route['route']['tool'], 'docling')
        self.assertTrue(all(not k.startswith('_') for u in route['units'] for c in (u.get('cells') or [u]) for k in c))

    def test_a_reread_page_takes_its_place_with_unique_ids(self):
        # ledger §17 / DOCLING_FEATURES #12: a page Docling grades POOR on parsing is converted again with full-page OCR; its units replace the page's, order and ids kept sound
        u = lambda i, page, text: {'id': f'#/texts/{i}', 'kind': 'text', 'text': text, 'anchor': {'page': page, 'region': [0, 0, 10, 10]}}
        first = [u(0, 1, 'one'), u(1, 2, '\u2588CF H<9'), u(2, 3, 'three'), {'id': '#/texts/3', 'kind': 'text', 'text': 'spans 2-3', 'anchor': [{'page': 2, 'region': [0, 0, 1, 1]}, {'page': 3, 'region': [0, 0, 1, 1]}]}]
        out = dp.spliced(first, {2: [u(0, 2, 'For the'), u(1, 2, 'three months')]})
        self.assertEqual([(x['id'], x['text']) for x in out], [('#/texts/0', 'one'), ('p2:#/texts/0', 'For the'), ('p2:#/texts/1', 'three months'), ('#/texts/2', 'three')])  # the unreadable unit and the unit spanning the re-read page go
        self.assertEqual(len({x['id'] for x in out}), 4)
        self.assertEqual(dp.spliced(first, {}), first)


from benchmarks.prepare.grader.adapters import prestep_headings as ph

HTML_STYLED = (b'<html><body><div style="font-weight:bold">Item 2. Management\xe2\x80\x99s Discussion</div>'
               b'<p><span style="font-weight:700">Free Cash Flow</span></p>'
               b'<p style="text-decoration:underline">RESULTS OF OPERATIONS</p>'
               b'<p>Our consolidated free cash flow for the Quarter and Prior Quarter are summarized as follows:</p>'
               b'<p><b>Note:</b> amounts in millions, except per share data, and this sentence runs on for a while to be a sentence.</p>'
               b'<div><div style="font-weight:bold">PART I</div><div>text under part one</div></div>'
               b'<table><tr><td style="font-weight:bold">Total</td><td>5</td></tr></table></body></html>')


class HeadingPrestepTests(unittest.TestCase):
    def test_lines_inside_table_cells_are_never_wrapped(self):
        raw = b'<table><tr><td><div style="font-weight:bold">Total revenue</div></td><td><p><b>2024</b></p></td></tr></table><div style="font-weight:bold">PART I</div>'
        out = ph.mark_headings(raw)
        self.assertEqual(out.count(b'<h2>'), 1); self.assertIn(b'<td><div style="font-weight:bold">Total revenue</div></td>', out)

    def test_short_styled_standalone_lines_become_headings_and_nothing_else_changes(self):
        out = ph.mark_headings(HTML_STYLED)
        self.assertEqual(out.count(b'<h2>'), 4)  # Item 2 line, Free Cash Flow, RESULTS OF OPERATIONS, PART I
        for kept in (b'summarized as follows:</p>', b'amounts in millions', b'<td style="font-weight:bold">Total</td>'):
            self.assertIn(kept, out)  # a sentence, a styled opener of a sentence, and table cells are left alone
        from benchmarks.prepare.grader.anchor import Visible
        self.assertEqual(Visible(out).text.replace(' ', ''), Visible(HTML_STYLED).text.replace(' ', ''))  # visible characters untouched


from benchmarks.prepare.grader.adapters import screen_grid as sg


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
