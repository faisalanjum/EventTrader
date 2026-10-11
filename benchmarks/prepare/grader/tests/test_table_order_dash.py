"""An uncertain dash and an uncertain byte row order on one duty (table-order-conservative, last interaction). The fixture is test_grade's public
invented Preferred-stock lead-in (Codex R17-C5), with its line placed as an earlier row of the value's own table, so its order is byte order only.
Truths, written before the run: the source prints the phrase with that dash (correct; the in-table row order unproved) - never PASS, open; the
source prints no dash or a sign touching the number (wrong) - FAIL text, whatever the order; the same line as a paragraph before the table (route
order, no byte doubt) - PASS; listing the accepted values in either order never creates a PASS."""
import unittest

from benchmarks.prepare.grader import grade

REAL = 'Preferred stock – 10,000,000 shares authorized: see below.'
WANT = '10,000,000 shares authorized: see below.'


def lead(source, unit_text, want=WANT, pinned=None, inside=True, alternatives=None):
    line = source.encode()
    raw = (b'<table id="t"><tr><td colspan="2">' + line + b'</td></tr><tr><td>Total</td><td>5</td></tr></table>') if inside else (b'<p>' + line + b'</p><table id="t"><tr><td>Total</td><td>5</td></tr></table>')
    at = lambda x: {'byte_start': raw.index(x), 'byte_end_exclusive': raw.index(x) + len(x)}
    cells = [{'r': 0, 'c': 0, 'cs': 2, 'text': unit_text, 'anchor': at(line)}] if inside else []
    cells += [{'r': len(cells), 'c': 0, 'text': 'Total', 'anchor': at(b'Total')}, {'r': len(cells), 'c': 1, 'text': '5', 'anchor': at(b'>5<')}]
    table = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table'), 'byte_end_exclusive': len(raw)}, 'cells': cells}
    units = ([] if inside else [{'id': 'l', 'kind': 'text', 'text': unit_text, 'anchor': at(line)}]) + [table]
    t = {'key_id': 'syn/L', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': at(b'>5<'), 'table_anchor': table['anchor'],
         'alternatives': {'lead_in': alternatives} if alternatives else {}, 'excluded': set(), 'fields': {'printed_value': '5', 'lead_in': want},
         'support': {'lead_in': {'anchors': [at((pinned or want).encode())]}}}
    g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units}, raw, 'htm')); g.grade_cell()
    return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'lead_in'), grade.verdict_of(g.rows)


class DashAndOrder(unittest.TestCase):
    def test_a_fully_proved_lead_in_outside_the_table_still_passes(self):
        self.assertEqual(lead(REAL, REAL, inside=False), (('pass', None), 'PASS'))

    def test_the_kept_dash_in_an_order_open_row_is_open_never_pass(self):
        for pinned in (None, REAL):  # the key's own span; the whole line (its dash then undecided)
            with self.subTest(pinned=pinned):
                (verdict, _), overall = lead(REAL, REAL, pinned=pinned)
                self.assertEqual(verdict, 'unresolved'); self.assertEqual(overall, 'UNRESOLVED')

    def test_an_invented_or_touching_sign_fails_whatever_the_order(self):
        self.assertEqual(lead('Preferred stock 10,000,000 shares authorized: see below.', REAL)[0], ('fail', 'text'))  # the source prints no dash: the route invented one
        touching = 'Preferred stock –10,000,000 shares authorized: see below.'
        self.assertEqual(lead(touching, touching)[0], ('fail', 'text'))  # a sign touching its number stays protected

    def test_accepted_values_in_either_order_never_pass(self):
        for alts in ([WANT, REAL], [REAL, WANT]):
            with self.subTest(alternatives=alts):
                (verdict, _), overall = lead(REAL, REAL, alternatives=alts)
                self.assertNotEqual(verdict, 'pass'); self.assertNotEqual(overall, 'PASS')


if __name__ == '__main__':
    unittest.main()
