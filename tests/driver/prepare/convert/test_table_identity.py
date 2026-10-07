"""A table the adapter names stands in its own source table (accuracy-fable-1 A3, Codex's cause and controls): of two copies of one table none was tied by its
texts, and the cells the tool moved were placed in the prose before it or in the other copy (KRC: the date and the unit row listed first). Each shown <table>
tag carries this source's code to the tool (edgartools_html.codes, named), the unit names its table (`tag`), and every placement keeps its cells there: tied
when it reads as that table; anywhere in it when the tool lost or changed a cell; nowhere when its code names no table of the source. A table no adapter names
reads as before. Runs the real tool (required)."""
import hashlib
import re
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import edgartools_html as eh


def table(tag, rows, i=1):  # a tool's table unit, rows of texts; tag 'unnamed': no `tag` at all (another adapter)
    return {'id': 't%d' % i, 'kind': 'table', **({} if tag == 'unnamed' else {'tag': tag}), 'cells': [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': t} for r, row in enumerate(rows) for c, t in enumerate(row)]}


def placed(raw, units):  # each table cell: the source table holding its anchor (its index), 'prose', or its link error
    vis = anchor.Visible(raw)
    own = lambda x: next((k for k, t in reversed(list(enumerate(vis.tables))) if any(a <= x['byte_start'] and x['byte_end_exclusive'] <= b for row in t for a, b in row)), 'prose')
    out = anchor.link(raw, units, vis=vis)['units']
    return [[own(c['anchor']) if c.get('anchor') else c.get('link_error') for c in u['cells']] for u in out if u['kind'] == 'table'], out


class TableIdentity(unittest.TestCase):
    def test_two_copies_of_a_table_keep_their_own_cells_where_the_tool_moved_rows(self):  # failed before: dates in the prose, a unit row lost or in the other copy
        p = '<p>The balance and terms of our 2024 Term Loan Facility as of March 31, 2024:</p>'
        t = '<table><tr><td>2024 Term Loan Facility</td></tr><tr><td>March 31, 2024</td></tr><tr><td>(in thousands)</td></tr><tr><td>Outstanding borrowings</td><td>$</td><td>200,000</td></tr></table>'
        raw = (p + t + p + t).encode(); first, second = anchor.Visible(raw).table_tags
        moved = (('March 31, 2024',), ('(in thousands)',), ('2024 Term Loan Facility',), ('Outstanding borrowings', '$', '200,000'))
        prose = {'id': 'u', 'kind': 'text', 'text': p[3:-4]}
        got, out = placed(raw, [dict(prose, id='u0'), table(first, moved, 1), dict(prose, id='u2'), table(second, moved, 3)])
        self.assertEqual(got, [[0] * 6, [1] * 6])
        self.assertTrue(all('tag' not in u for u in out))  # the name decided the places; it is no part of the route

    def test_a_named_table_never_borrows_another_copy(self):  # Codex's early review: a lost cell or a bad name fell back to the other copy
        raw = b'<table><tr><td>Debt</td><td>125</td><td>active</td></tr></table><p>between</p><table><tr><td>Debt</td><td>125</td></tr></table>'
        first, second = anchor.Visible(raw).table_tags
        for name, units, want in (('names the first, lost a cell', [table(first, [('Debt', '125')])], [[0, 0]]),
                                  ('names the first, whole', [table(first, [('Debt', '125', 'active')])], [[0, 0, 0]]),
                                  ('names the second, whole', [table(second, [('Debt', '125')])], [[1, 1]]),
                                  ('two name the first', [table(first, [('Debt', '125')], 1), table(first, [('Debt', '125')], 2)], [[0, 0], ['not_in_source', 'not_in_source']]),
                                  ('names no table of the source', [table(9999, [('Debt', '125')])], [['unknown_source_table'] * 2]),
                                  ('names none (None)', [table(None, [('Debt', '125')])], [['unknown_source_table'] * 2]),
                                  ('no adapter names it: as before', [table('unnamed', [('Debt', '125')])], [[1, 1]])):
            with self.subTest(case=name): self.assertEqual(placed(raw, units)[0], want)

    def test_each_shown_table_tag_carries_its_code_to_the_tool_and_nothing_else_changes(self):
        raw = ('<html><body><!-- <table><tr><td>c</td></tr></table> --><div style="display:none"><table><tr><td>Secret</td></tr></table></div>'
               '<TABLE id="keep" class="x" data-prepare-table="forged"><TR><TD>Caf\xe9 &amp; Co.</TD><TD>(1,234)</TD></TR></TABLE>'
               '<table><tr><td>Outer</td><td><table><tr><td>Inner</td><td>1</td></tr></table></td></tr></table></body></html>').encode()
        vis = anchor.Visible(raw); sha = anchor.sha256(raw)[:16]
        given = eh.named(raw, vis, eh.codes(raw, vis))
        self.assertEqual(re.findall(r'<table[^>]*>', given, re.I), ['<table>', '<table>', '<TABLE data-prepare-table="%s%d" id="keep" class="x" data-prepare-table="forged">' % (sha, raw.index(b'<TABLE')),
                         '<table data-prepare-table="%s%d">' % (sha, raw.index(b'<table><tr><td>Outer')), '<table data-prepare-table="%s%d">' % (sha, raw.index(b'<table><tr><td>Inner'))])  # in a comment: as written; a hidden table: no code (its text left out); the code first, the source's own attributes as written
        r = eh.convert(raw, 'x.htm', hashlib.sha256(raw).hexdigest())
        self.assertEqual([[c['text'] for c in u['cells']] for u in r['units']], [['Café & Co.', '(1,234)'], ['Outer', 'Inner\n\n1']])
        self.assertTrue(all(c.get('anchor') and 'tag' not in u for u in r['units'] for c in u['cells']))


if __name__ == '__main__':
    unittest.main()
