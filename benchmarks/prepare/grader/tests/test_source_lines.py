"""A unit that runs over a line break the source certifies (<br>) is split into its lines (Codex's held-out review: three section boundaries were
hidden in one unit); nothing else is split, nothing is promoted to a heading, and the strikes are read again for each line. The screen step's endpoint
boxes prove two units apart only when Chrome shows them apart (`grade.screen_boundary`)."""
import copy
import unittest

from benchmarks.prepare.grader import anchor, grade
from benchmarks.prepare.grader.adapters import source_formatting
from benchmarks.prepare.grader.adapters.edgartools_html import split_lines


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


class ScreenBoundary(unittest.TestCase):
    def test_only_boxes_shown_apart_prove_separation(self):
        left = {'shown': True, 'x': 10, 'r': 20, 't': 10, 'b': 20}
        self.assertIsNone(grade.screen_boundary(left, {'shown': True, 'x': 20, 'r': 30, 't': 10, 'b': 20}))  # touching: never certifies
        self.assertIs(grade.screen_boundary(left, {'shown': True, 'x': 24, 'r': 34, 't': 10, 'b': 20}), False)  # a gap on one line
        self.assertIs(grade.screen_boundary(left, {'shown': True, 'x': 10, 'r': 20, 't': 25, 'b': 35}), False)  # another line
        self.assertIsNone(grade.screen_boundary(left, dict(left)))
        self.assertIsNone(grade.screen_boundary(None, left))
        self.assertIsNone(grade.screen_boundary(left, {'shown': True, 'x': 30, 'r': 20, 't': 10, 'b': 20}))  # an impossible box
        self.assertIsNone(grade.screen_boundary(left, {'shown': False, 'x': 24, 'r': 34, 't': 10, 'b': 20}))  # a box not shown


class PrintedAlternatives(unittest.TestCase):
    def row(self, got, allowed):
        raw = b'<p>Alpha Beta</p>'; anchor_ = {'byte_start': 3, 'byte_end_exclusive': 13}
        target = {'key_id': 'fixture:T01', 'file_id': 'fixture.htm', 'split': 'development', 'format': 'structure/htm', 'type': 'structure', 'fields': {'kind': 'paragraph'},
                  'alternatives': {'printed_text': allowed}, 'support': {}, 'excluded': set(), 'anchor': anchor_}
        saved = copy.deepcopy(target)
        g = grade.Grader(target, grade.RouteFile({'file_id': 'fixture.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': got, 'anchor': anchor_}]}, raw)); g.grade_structure()
        self.assertEqual(target, saved)  # the key is never changed
        rows = [r for r in g.rows if r['check'] == 'printed_text']; self.assertEqual(len(rows), 1); return rows[0]['verdict']

    def test_every_declared_alternative_goes_through_the_check(self):  # Codex's held-out review: an empty expected text against an empty picture unit read as zero error
        self.assertEqual(self.row('Alpha Beta', ['Alpha Beta', 'Other Words']), 'pass')
        self.assertEqual(self.row('Alpha Beta', ['Other Words', 'Alpha Beta']), 'pass')
        self.assertEqual(self.row('Nope', ['Alpha Beta', 'Other Words']), 'fail')
        self.assertEqual(self.row('', ['Alpha Beta', 'Other Words']), 'fail')


if __name__ == '__main__':
    unittest.main()
