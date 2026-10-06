"""HTML control/noncharacter references remain evidence, per WHATWG parsing."""
import unittest

from benchmarks.prepare.grader.anchor import Visible


class NumericReferences(unittest.TestCase):
    def test_controls_and_noncharacters_are_not_silently_deleted(self):
        for source, expected in [('&#2;', '\x02'), ('&#7;', '\x07'), ('&#11;', '\x0b'),
                                 ('&#xFFFF;', '\uffff'), ('&#xFDD0;', '\ufdd0'),
                                 ('&#x10FFFF;', '\U0010ffff')]:
            raw = ('<p>A' + source + 'B</p>').encode()
            v = Visible(raw)
            with self.subTest(source=source):
                self.assertEqual(v.at(3, len(raw) - 4), 'A' + expected + 'B')
                self.assertEqual(v.at(4, 4 + len(source)), expected)

    def test_defined_replacements_and_named_references_still_match(self):
        raw = b'<p>&#0;|&#xD800;|&#1114112;|&#x80;|&amp;#2;|&lt;|&unknown;</p>'
        self.assertEqual(Visible(raw).at(3, len(raw) - 4), '\ufffd|\ufffd|\ufffd|\u20ac|&#2;|<|&unknown;')

    def test_raw_text_is_not_decoded_and_hidden_references_stay_hidden(self):
        raw = b'<xmp>&#2;</xmp><p hidden>&#2;</p><p>B</p>'
        v = Visible(raw)
        self.assertEqual(v.at(5, 10), '&#2;')
        self.assertNotIn('\x02', v.text)
        self.assertGreater(v.hidden_chars, 0)


if __name__ == '__main__': unittest.main()
