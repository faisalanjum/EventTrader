"""A unit that runs over a line break the source certifies (<br>) is split into its lines (Codex's held-out review: three section boundaries were
hidden in one unit); nothing else is split, nothing is promoted to a heading, and the strikes are read again for each line. The screen step's endpoint
boxes prove two units apart only when Chrome shows them apart (`grade.screen_boundary`)."""
import copy
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import source_formatting
from driver.prepare.convert.edgartools_html import split_lines


class Lines(unittest.TestCase):
    def output(self, raw, text, kind='text', **extra):
        return split_lines(raw, anchor.link(raw, [dict(id='a', kind=kind, text=text, **extra)])['units'])

    def test_real_breaks(self):
        out = self.output(b'<p>Before<br>Heading<br/>After</p>', 'Before Heading After')
        self.assertEqual([u['text'] for u in out], ['Before', 'Heading', 'After'])
        self.assertEqual([u['anchor'] for u in out], [{'byte_start': 3, 'byte_end_exclusive': 9}, {'byte_start': 13, 'byte_end_exclusive': 20}, {'byte_start': 25, 'byte_end_exclusive': 30}])
        self.assertEqual([(u['kind'], u['id']) for u in out], [('text', 'a_line_0'), ('text', 'a_line_1'), ('text', 'a_line_2')])

    def test_what_is_not_a_certified_break_stays_whole(self):
        for raw, text in ((b'<p>Before<br style="display:none">After</p>', 'BeforeAfter'), (b'<p data-x="<br>">BeforeAfter</p>', 'BeforeAfter'),
                          (b'<p>Before<b>After</b></p>', 'BeforeAfter'), (b'<style>br {display:none}</style><p>Before<br>After</p>', 'BeforeAfter')):
            with self.subTest(raw=raw): self.assertEqual(len(self.output(raw, text)), 1)  # a hidden break, a break in an attribute, inline markup, an uncertain reading

    def test_links_references_and_cells_stay_whole(self):
        self.assertEqual(len(self.output(b'<p>Before<br>After</p>', 'Before After', links=[{'text': 'Before After', 'href': '#x'}])), 1)
        raw = b'<p>Before<br>After</p>'; units = anchor.link(raw, [{'id': 'a', 'kind': 'text', 'text': 'Before After'}])['units']
        units.append({'id': 'b', 'kind': 'table', 'cells': [], 'notes': ['a']}); self.assertEqual(split_lines(raw, copy.deepcopy(units)), units)
        raw = b'<table><tr><td>Before<br>After</td></tr></table>'; units = anchor.link(raw, [{'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'text': 'Before After'}]}])['units']
        self.assertEqual(split_lines(raw, copy.deepcopy(units)), units)

    def test_strikes_are_read_again_for_each_line(self):
        raw = b'<p>Before<br><s>Old</s>New<br>After</p>'
        out = self.output(raw, 'Before OldNew After'); source_formatting.apply(raw, out)
        self.assertEqual([u['text'] for u in out], ['Before', 'OldNew', 'After'])
        self.assertEqual(out[1]['struck'], ['Old']); self.assertNotIn('struck', out[0]); self.assertNotIn('struck', out[2])


if __name__ == '__main__':
    unittest.main()
