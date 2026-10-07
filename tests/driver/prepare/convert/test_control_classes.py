"""The control sample's classes (2026-10-06): a table with no text is no unit; a table continued over a page break keeps its title; a corner of several stub
columns is the key's pieces; a row-label piece carried down a block (a stub printed once for several rows, no rowspan) still labels the row."""
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import edgartools_html as adapter


class Helpers(unittest.TestCase):

    def test_a_table_with_no_text_is_no_unit(self):
        tree = {'type': 'DocumentNode', 'children': [{'type': 'TableNode', 'caption': None, 'rows': [[{'text': ' ', 'colspan': 1, 'rowspan': 1, 'is_header': False}]]}, {'type': 'ParagraphNode', 'text': 'after'}]}
        self.assertEqual([u['kind'] for u in adapter.to_units(tree)], ['text'])
        tree['children'][0]['rows'][0][0]['text'] = 'x'; self.assertEqual([u['kind'] for u in adapter.to_units(tree)], ['table', 'text'])
        tree['children'][0]['rows'][0][0]['text'] = ' '; tree['children'][0]['caption'] = 'Outstanding debt at December 31'  # no text in any cell, a caption: the caption is read, and anchored (Codex R2-C4)
        units = adapter.to_units(tree); self.assertEqual([(u['kind'], u['text']) for u in units][0], ('caption', 'Outstanding debt at December 31'))
        raw = b'<table><caption>Outstanding debt at December 31</caption><tr><td></td></tr></table><p>after</p>'
        self.assertEqual(raw[anchor.link(raw, units)['units'][0]['anchor']['byte_start']:][:31], b'Outstanding debt at December 31')


if __name__ == '__main__':
    unittest.main()
