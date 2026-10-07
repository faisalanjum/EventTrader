"""The tool's own heading evidence travels beside the text as a claim (the worktree's cases; its two iXBRL cases are not taken: that payload is not copied into a route)."""
from dataclasses import dataclass
import unittest

from driver.prepare.convert import edgartools_html as eh


@dataclass
class HeadingStyle:
    font_weight: str = 'bold'
    font_size: float = 14.0


class EdgarHeadingMetadataTests(unittest.TestCase):
    def test_native_heading_evidence_survives_direct_and_nested_claims(self):
        heading = type('HeadingNode', (), {
            'text': lambda self: 'Risk', 'children': [], 'level': 2,
            'metadata': {'detection_method':'style', 'confidence':0.74},
            'style': HeadingStyle(), 'semantic_type':None, 'semantic_role':'section'})()
        paragraph = type('ParagraphNode', (), {
            'text': lambda self: 'Risk Remaining text.', 'children':[heading]})()
        for original in (heading, paragraph):
            tree = eh.dump(original)
            claim = tree.get('heading', tree)
            self.assertEqual(claim['native']['metadata'], {'detection_method':'style', 'confidence':0.74})
            self.assertEqual(claim['native']['style'], {'font_weight':'bold', 'font_size':14.0})
            units = eh.to_units(tree)
            self.assertEqual(units[0]['native_heading'], claim['native'])
            self.assertEqual(units[0]['text'], 'Risk')
            if len(units)>1:self.assertNotIn('native_heading',units[1])

    def test_plain_text_does_not_gain_a_heading_claim(self):
        node = type('TextNode', (), {'text':'ordinary', 'children':[]})()
        tree = eh.dump(node)
        self.assertNotIn('native',tree)
        self.assertNotIn('native_heading',eh.to_units(tree)[0])


class EdgarHeadingRuleTests(unittest.TestCase):
    """Each condition of the heading-in-a-paragraph rule and of the evidence (added in the merge; the cases above are the worktree's)."""
    paragraph = staticmethod(lambda head, words: type('ParagraphNode', (), {'text': lambda self: words, 'children': [type('HeadingNode', (), {'text': lambda self: head, 'children': [], 'level': 1})()]})())

    def test_evidence_keeps_what_the_tool_gives_and_nothing_it_does_not(self):
        heading = type('HeadingNode', (), {'text': lambda self: 'Risk', 'children': [], 'level': 2, 'metadata': {}, 'style': None, 'semantic_type': None, 'semantic_role': 'section'})()
        self.assertEqual(eh.dump(heading)['native'], {'metadata': {}, 'semantic_role': 'section'})

    def test_a_heading_at_the_end_is_a_heading_one_in_the_middle_or_empty_is_none(self):
        last = eh.dump(self.paragraph('Risk', 'Some text. Risk'))
        self.assertEqual((last['heading']['text'], last['rest'], last['order']), ('Risk', 'Some text.', 'head_last'))
        self.assertEqual([(u['kind'], u['text']) for u in eh.to_units(last)], [('text', 'Some text.'), ('heading', 'Risk')])
        for head, words in (('Risk', 'Some Risk text.'), ('', 'Some text.')):
            with self.subTest(head=head): self.assertNotIn('heading', eh.dump(self.paragraph(head, words)))

    def test_a_tree_saved_without_evidence_gives_units_without_it(self):
        units = eh.to_units({'type': 'ParagraphNode', 'text': 'Risk Remaining.', 'heading': {'text': 'Risk', 'level': 2}, 'rest': 'Remaining.', 'order': 'head_first'})
        self.assertEqual([(u['kind'], 'native_heading' in u) for u in units], [('heading', False), ('text', False)])
