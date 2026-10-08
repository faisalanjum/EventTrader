"""Native style runs must not create new word or amount boundaries in output."""
import unittest

from driver.prepare.convert import edgartools_html as eh
from driver.prepare.convert import anchor


def paragraph(text, head):
    heading = type('HeadingNode', (), {'text': lambda self: head, 'children': [], 'level': 2})()
    rest = text[len(head):] if text.startswith(head) else text[:-len(head)]
    plain = type('TextNode', (), {'text': lambda self: rest, 'children': []})()
    kids = [heading, plain] if text.startswith(head) else [plain, heading]
    return type('ParagraphNode', (), {'text': lambda self: text, 'children': kids})()


class HeadingBoundaryTests(unittest.TestCase):
    def test_every_internal_cut_of_words_and_amounts_stays_one_paragraph(self):
        for word in ('Financial', 'EXHIBITS', 'résumé', 'risk_factor', '2025', '12,345.67', 'Cafe\u0301', 'Re\u0301sume\u0301', '31st', '10Q', "Company's", 'Company’s', 'don’t', '2024’s', 'cafe\u0301’s'):
            for cut in range(1, len(word)):
                for head in (word[:cut], word[cut:]):
                    with self.subTest(word=word, cut=cut, head=head):
                        tree = eh.dump(paragraph(word, head))
                        self.assertNotIn('heading', tree)
                        units = eh.to_units(tree)
                        self.assertEqual([(u['kind'], u['text']) for u in units], [('text', word)])

    def test_whitespace_delimited_claims_keep_their_order(self):
        for whole, head, rest, order in (
            ('Risk remaining text', 'Risk', 'remaining text', 'head_first'),
            ('Risk\u00a0remaining text', 'Risk', 'remaining text', 'head_first'),
            ('Risk: remaining text', 'Risk:', 'remaining text', 'head_first'),
            ('Risk. Remaining text', 'Risk.', 'Remaining text', 'head_first'),
            ('Earlier text. Risk', 'Risk', 'Earlier text.', 'head_last'),
            ('Earlier text: Risk', 'Risk', 'Earlier text:', 'head_last'),
            ('Cafe\u0301: Details', 'Cafe\u0301:', 'Details', 'head_first'),
        ):
            with self.subTest(whole=whole, head=head):
                tree = eh.dump(paragraph(whole, head))
                self.assertEqual((tree['heading']['text'], tree['rest'], tree['order']), (head, rest, order))

    def test_punctuation_attached_to_a_style_run_stays_with_the_whole_paragraph(self):
        # A genuine no-space run-in label is conservatively kept in its paragraph,
        # too. Punctuation is not evidence of a separate block or heading.
        for whole, head in (
            ('Risk: remaining text', 'Risk'),
            ('Earlier text:Risk', 'Risk'),
            ('Plan (the “Agreement”) applies', 'Plan (the “'),
            ('Journey® continues', 'Journey'),
            ('STOCKHOLDERS’ EQUITY', 'STOCKHOLDERS'),
            ('STOCKHOLDERS’  EQUITY', 'STOCKHOLDERS'),
            ('Signature __/s/Signer', 'Signature __'),
            ('(Continued)(1)', '(Continued)'),
            ('In 2024, 2023 and 2022', 'In 2024'),
        ):
            with self.subTest(whole=whole, head=head):
                tree = eh.dump(paragraph(whole, head))
                self.assertNotIn('heading', tree)
                self.assertEqual([(u['kind'], u['text']) for u in eh.to_units(tree)], [('text', whole)])

    def test_a_complete_heading_and_real_block_siblings_are_unchanged(self):
        tree = eh.dump(paragraph('Overview', 'Overview'))
        self.assertEqual([(u['kind'], u['text']) for u in eh.to_units(tree)], [('heading', 'Overview')])
        h = type('HeadingNode', (), {'text': lambda self: 'Section', 'children': [], 'level': 2})()
        p = type('ParagraphNode', (), {'text': lambda self: 'Details', 'children': []})()
        block = type('ContainerNode', (), {'children': [h, p]})()
        self.assertEqual([(u['kind'], u['text']) for u in eh.to_units(eh.dump(block))], [('heading', 'Section'), ('text', 'Details')])

    def test_a_declined_claim_does_not_drop_inline_links(self):
        link = type('LinkNode', (), {'text': lambda self: 'Financial', 'href': '#note'})()
        node = paragraph('Financial', 'Finan')
        node.walk = lambda: iter([node, *node.children, link])
        units = eh.to_units(eh.dump(node))
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]['text'], 'Financial')
        self.assertEqual(units[0]['links'], [{'text': 'Financial', 'href': '#note', 'to': None}])

    def test_rejecting_a_prefix_does_not_move_its_claim_to_an_identical_suffix(self):
        tree = eh.dump(paragraph('Financial words Finan', 'Finan'))
        self.assertNotIn('heading', tree)
        self.assertEqual(eh.to_units(tree)[0]['text'], 'Financial words Finan')

    def test_an_internal_claim_cannot_take_an_identical_word_at_an_edge(self):
        node = paragraph('Risk already described Risk applies', 'Risk')
        heading = node.children[0]
        node.children = [type('TextNode', (), {'text': lambda self: 'Risk already described '})(),
                         heading, type('TextNode', (), {'text': lambda self: ' applies'})()]
        tree = eh.dump(node)
        self.assertNotIn('heading', tree)
        self.assertEqual(eh.to_units(tree)[0]['text'], node.text())

    def test_old_saved_parses_cannot_hide_the_repaired_boundaries(self):
        self.assertEqual(eh.SETTINGS.get('heading_boundaries'), 'source matched')

    def test_source_proof_requires_the_whole_parent_and_discards_private_claims(self):
        for source, certain, placed, expected in (
            ('Risk Factors', True, True, ['heading', 'text']),
            ('Risk\u200bFactors', True, True, ['text']),
            ('Risk\u00adFactors', True, True, ['text']),
            ('Risk X Factors', True, True, ['text']),
            ('Risk Factors', False, True, ['text']),
            ('Risk Factors', True, False, ['text']),
        ):
            with self.subTest(source=source, certain=certain, placed=placed):
                raw = ('<p>' + source + '</p>').encode()
                vis = anchor.Visible(raw); vis.certain = certain
                units = eh.to_units(eh.dump(paragraph('RiskFactors', 'Risk')))
                if placed: units[0]['anchor'] = {'byte_start': 3, 'byte_end_exclusive': len(raw)-4}
                result = eh.split_lines(raw, units, vis)
                self.assertEqual([u['kind'] for u in result], expected)
                self.assertTrue(all('_heading' not in u for u in result))
                self.assertEqual(''.join(u['text'] for u in result), 'RiskFactors')

    def test_redline_reading_separators_are_not_source_layout_gaps(self):
        for source, whole, head, expected in (
            ('clause (<s>1</s>) applies', 'clause (1) applies', 'clause (', ['text']),
            ('Term B<s>-5</s>-6 Note', 'Term B-5-6 Note', 'Term B', ['text']),
            ('Risk<s><del>Factors</del></s>', 'RiskFactors', 'Risk', ['text']),
            ('Risk <s>Factors</s>', 'RiskFactors', 'Risk', ['heading', 'text']),
            ('Risk<br><s>Factors</s>', 'RiskFactors', 'Risk', ['heading', 'text']),
            ('<s>Risk</s><br>Factors', 'RiskFactors', 'Risk', ['heading', 'text']),
        ):
            with self.subTest(source=source):
                raw = ('<p>' + source + '</p>').encode()
                vis = anchor.Visible(raw)
                units = eh.to_units(eh.dump(paragraph(whole, head)))
                units[0]['anchor'] = {'byte_start': 3, 'byte_end_exclusive': len(raw)-4}
                result = eh.split_lines(raw, units, vis)
                self.assertEqual([u['kind'] for u in result], expected)
                self.assertEqual(''.join(u['text'] for u in result), whole)


class NativeHeadingBoundaryTests(unittest.TestCase):
    def prepared(self, body):
        raw = ('<html><body><p>' + body + '</p><p>Other ordinary reporting text.</p></body></html>').encode()
        result = eh.convert(raw, 'case.htm', anchor.sha256(raw))
        self.assertEqual(result['status'], 'OK')
        self.assertTrue(all('_heading' not in u for u in result['units']))
        self.assertEqual(result['units'][-1]['text'], 'Other ordinary reporting text.')
        return result['units'][:-1]

    def test_source_breaks_are_preserved_before_a_heading_is_split(self):
        head = '<span style="font-weight:700;font-size:24px">{}</span>'
        for body in (
            head.format('Item 1A<br/>') + '<span>Risk Factors</span>',
            head.format('Item 1A') + '<span><br/>Risk Factors</span>',
            head.replace('font-weight:', 'display:block;font-weight:').format('Item 1A') + '<span>Risk Factors</span>',
            head.format('Item 1A') + '<span style="display:block">Risk Factors</span>',
            head.format('Item 1A') + '<a>   </a><span>Risk Factors</span>',
            head.format('Item 1A') + '<a href="#n">   </a><span>Risk Factors</span>',
            head.format('Item 1A') + '<ix:nonnumeric><span style="padding-left:13pt">Risk Factors</span></ix:nonnumeric>',
        ):
            with self.subTest(body=body):
                units = self.prepared(body)
                self.assertEqual([(u['kind'], u['text']) for u in units], [('heading', 'Item 1A'), ('text', 'Risk Factors')])
                self.assertLessEqual(units[0]['anchor']['byte_end_exclusive'], units[1]['anchor']['byte_start'])

    def test_hidden_or_absent_source_gaps_do_not_create_a_split(self):
        head = '<span style="font-weight:700;font-size:24px">{}</span>'
        for body in (
            head.format('Item 1A') + '<span>Risk Factors</span>',
            head.replace('font-weight:', 'display:inline;font-weight:').format('Item 1A') + '<span>Risk Factors</span>',
            head.format('Item 1A<br style="display:none"/>') + '<span>Risk Factors</span>',
            head.format('Item 1A<span style="display:none"><br/></span>') + '<span>Risk Factors</span>',
            head.format('Item 1A') + '<a></a><span>Risk Factors</span>',
            head.format('Item 1A') + '<a style="display:none">   </a><span>Risk Factors</span>',
            head.format('Item 1A') + '<ix:nonnumeric><span style="display:none;padding-left:13pt">Hidden</span><span>Risk Factors</span></ix:nonnumeric>',
        ):
            with self.subTest(body=body):
                units = self.prepared(body)
                self.assertEqual([(u['kind'], u['text']) for u in units], [('text', 'Item 1ARisk Factors')])

    def test_nested_gap_is_not_borrowed_from_later_text(self):
        units = self.prepared('<span style="font-weight:700;font-size:24px">Item 1A</span>'
                           '<ix:nonnumeric>R<span style="padding-left:13pt">isk Factors</span></ix:nonnumeric>')
        self.assertEqual(units[0]['kind'], 'text')
        self.assertTrue(units[0]['text'].startswith('Item 1AR'))

    def test_a_native_possessive_claim_stays_in_its_paragraph(self):
        for head, rest in (('Item 1. Company', '’s policy applies'), ('Item 1. Company’', 's policy applies'),
                           ('Item 1. FY 2024', '’s policy applies')):
            with self.subTest(head=head):
                units = self.prepared('<span style="font-weight:700;font-size:24px">' + head + '</span><span>' + rest + '</span>')
                self.assertEqual([(u['kind'], u['text']) for u in units], [('text', head + rest)])

    def test_format_marks_cannot_disguise_a_native_within_word_cut(self):
        for mark in ('\u200d', '\u00ad', '\u200c'):
            for head, rest in (('Item 1A', 'Risk Factors'), ('Item 1. Company', '’s policy applies')):
                with self.subTest(mark=mark, head=head):
                    units = self.prepared('<span style="font-weight:700;font-size:24px">' + head + '</span>' + mark + '<span>' + rest + '</span>')
                    self.assertEqual([u['kind'] for u in units], ['text'])
                    self.assertEqual(anchor.squash(units[0]['text']), anchor.squash(head + rest))

    def test_native_redline_transition_keeps_the_complete_paragraph(self):
        units = self.prepared('<span style="font-weight:700;font-size:24px">Item 1. clause (</span><s>1</s><span>) applies</span>')
        self.assertEqual([(u['kind'], u['text']) for u in units], [('text', 'Item 1. clause (1) applies')])

    def test_standard_css_spelling_does_not_erase_a_source_block_boundary(self):
        for display in ('BLOCK', 'block !important', '/*comment*/block', 'block!important;display:inline', 'flex', 'grid', 'flow-root'):
            with self.subTest(display=display):
                units = self.prepared('<span style="display:' + display + ';font-weight:700;font-size:24px">Item 1A</span><span>Risk Factors</span>')
                self.assertEqual([(u['kind'], u['text']) for u in units], [('heading', 'Item 1A'), ('text', 'Risk Factors')])

    def test_nested_gap_uses_declared_precedence_without_changing_text_or_styles(self):
        for css in ('padding-left:13pt!important', 'padding-left:/*comment*/13pt', 'padding-left:13pt!important;padding-left:0', 'padding:0 0 0 13pt'):
            with self.subTest(css=css):
                units = self.prepared('<span style="font-weight:700;font-size:24px">Item 1A</span><ix:nonnumeric><span style="' + css + '">Risk Factors</span></ix:nonnumeric>')
                self.assertEqual([(u['kind'], u['text']) for u in units], [('heading', 'Item 1A'), ('text', 'Risk Factors')])
        for css in ('padding-left:0', 'padding-left:13pt;padding:0', 'padding-left:13', 'padding-left:13 pt',
                    'padding-left:13pt;margin-left:-13pt', 'padding-left:13pt;padding:var(--unknown)'):
            with self.subTest(css=css):
                units = self.prepared('<span style="font-weight:700;font-size:24px">Item 1A</span><ix:nonnumeric><span style="' + css + '">Risk Factors</span></ix:nonnumeric>')
                self.assertEqual([(u['kind'], u['text']) for u in units], [('text', 'Item 1ARisk Factors')])
