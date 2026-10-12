"""The linker's own-cell boundary, at its native entry point anchor.link (Root, own-cell boundary findings, Oct 12). A cell bound to its own source cell
(`source`) is read only inside that cell - exact, pieced, with marks - and a proved source cell only narrows its table's places: a reading longer than
its cell never takes the next cell, an extent in another table or a table no source table is fails, `source: None` (a lost or repeated code) fails,
and a cell with no `source` field is read as before. Expected spans come from the source bytes. Invented sources."""
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert.anchor import link

RAW = b'<html><body><table><tr><td>ABCDEFGHIJKLMNOPQRSTUVWX</td><td>TAIL</td></tr></table><table><tr><td>ABCDEFGHIJKLMNOPQRSTUVWX</td></tr></table></body></html>'
TEXT = 'ABCDEFGHIJKLMNOPQRSTUVWX'
A = RAW.index(TEXT.encode()); B = A + len(TEXT); SECOND = RAW.index(TEXT.encode(), B); TAG = RAW.index(b'<table')


def cell(text, lo, hi, **more):
    return {'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': text, 'header': False, 'source': None if lo is None else {'byte_start': lo, 'byte_end_exclusive': hi}, **more}


def table(cells, tag=TAG):
    return {'id': 'u0', 'kind': 'table', 'cells': cells, **({} if tag is None else {'tag': tag})}


def spans(c):
    a = c.get('anchor'); return a if isinstance(a, list) else [a] if a else []


class OwnCellLink(unittest.TestCase):
    def test_root_boundaries_exact_own_longer_than_the_cell_and_a_foreign_extent(self):  # Root's REPRO cases, kept permanent
        for tag in (TAG, None):  # confined with or without the adapter's table tag
            with self.subTest(tag=tag, case='own'):
                c = cell(TEXT, A, B); link(RAW, [table([c], tag)])
                self.assertEqual(spans(c), [{'byte_start': A, 'byte_end_exclusive': B}])
            with self.subTest(tag=tag, case='longer than its cell'):
                c = cell(TEXT + 'TAIL', A, B); link(RAW, [table([c], tag)])
                self.assertTrue(all(A <= x['byte_start'] < x['byte_end_exclusive'] <= B for x in spans(c)))  # never the next cell's TAIL
        c = cell(TEXT, SECOND, SECOND + len(TEXT)); link(RAW, [table([c])])  # its table is the first; its extent is in the second
        self.assertEqual((spans(c), c.get('link_error')), ([], 'foreign_source_cell'))

    def test_an_unknown_source_table_stays_a_failure(self):
        c = cell(TEXT, A, B); link(RAW, [table([c], tag=RAW.index(b'<body'))])  # a tag that starts no table of the source
        self.assertEqual((spans(c), c.get('link_error')), ([], 'unknown_source_table'))

    def test_no_proved_own_cell_fails_and_no_source_field_reads_as_before(self):
        c = cell(TEXT, None, None); link(RAW, [table([c])])  # source None: a lost or repeated code (to_units)
        self.assertEqual((spans(c), c.get('link_error')), ([], 'unbound_source_cell'))
        c = cell(TEXT, A, B); del c['source']; link(RAW, [table([c])])  # no source field at all: the old placement
        self.assertTrue(spans(c))

    def test_a_long_pieced_reading_stays_inside_its_own_cell(self):  # the tool inserted "and" into a long cell text; the next cell prints "and"
        raw = b'<table><tr><td>This is the complete report heading, the words of it are printed here.</td><td>and</td></tr></table>'  # each block at least SHORT search characters
        first, second = b'This is the complete report heading,', b'the words of it are printed here.'
        lo = raw.index(first); hi = raw.index(b'</td>')
        for tag in (raw.index(b'<table'), None):
            with self.subTest(tag=tag):
                c = cell('This is the complete report heading, and the words of it are printed here.', lo, hi); link(raw, [table([c], tag)])
                self.assertEqual(c.get('link_flag'), 'pieced')
                self.assertEqual([raw[x['byte_start']:x['byte_end_exclusive']] for x in spans(c)], [first, second])  # from the source bytes
                self.assertEqual(c.get('inserted_chars'), len('and'))
                self.assertTrue(all(lo <= x['byte_start'] < x['byte_end_exclusive'] <= hi for x in spans(c)))

    def test_repeated_texts_short_spans_nested_overlap_and_marks(self):
        raw = b'<table><tr><td>Q</td><td>Q</td><td>(1)</td></tr></table>'; q1 = raw.index(b'Q'); q2 = raw.index(b'Q', q1 + 1); m = raw.index(b'(1)')
        for tag in (raw.index(b'<table'), None):
            with self.subTest(tag=tag, case='repeated, listed in reverse'):
                a, b = cell('Q', q2, q2 + 1, c=1), cell('Q', q1, q1 + 1); link(raw, [table([a, b], tag)])
                self.assertEqual((spans(a), spans(b)), ([{'byte_start': q2, 'byte_end_exclusive': q2 + 1}], [{'byte_start': q1, 'byte_end_exclusive': q1 + 1}]))
            with self.subTest(tag=tag, case='a short reading longer than its one-character cell'):
                a = cell('QQ', q1, q1 + 1); link(raw, [table([a], tag)])
                self.assertTrue(all(q1 <= x['byte_start'] < x['byte_end_exclusive'] <= q1 + 1 for x in spans(a)))
            with self.subTest(tag=tag, case='a mark printed in the next cell is not this cell\'s'):
                a = cell('Q', q2, q2 + 1, markers=['(1)']); link(raw, [table([a], tag)])
                self.assertTrue(spans(a) and all(q2 <= x['byte_start'] < x['byte_end_exclusive'] <= q2 + 1 for x in spans(a)))
        raw = b'<table><tr><td><table><tr><td>inner</td></tr></table></td><td>x</td></tr></table>'; outer, inner = raw.index(b'<td>'), raw.index(b'inner')
        holder = cell('inner', outer + 4, raw.index(b'</table>') + 8); child = cell('inner', inner, inner + 5)
        link(raw, [table([holder], raw.index(b'<table')), dict(table([child], raw.index(b'<table', 1)), id='u1')])  # a holder cell's flattened text reads its child's
        self.assertEqual((spans(child), [raw[x['byte_start']:x['byte_end_exclusive']] for x in spans(holder)]), ([{'byte_start': inner, 'byte_end_exclusive': inner + 5}], [b'inner']))


if __name__ == '__main__':
    unittest.main()
