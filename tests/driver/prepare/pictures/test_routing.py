"""The existing checks on Chandra's reading and the free OCR (pictures/routing.py): with Sonnet off they are the flags in the status line;
with Sonnet on they decide which picture is read again. Ported from prepare_work reader_packets/selftest.py (routing v5, owner + Codex r7;
v6, Codex r10) on 2026-10-06."""
import unittest

from driver.prepare.pictures import routing

TEXT = '<div data-bbox="0 0 1000 1000" data-label="Text"><p>{}</p></div>'
both = lambda s: dict(w=1000, h=100, pp=[dict(t=s, box=[20, 20, 980, 80])] if s else [], ox=[dict(t=s, box=[20, 20, 980, 80])] if s else [])


class RoutingTests(unittest.TestCase):
    def test_word_contradictions_are_flags_not_calls(self):  # v5: shown as free-OCR conflict lines; spacing is harmless
        for a, b in (('We expect growth.', 'We expect growth.'), ('We expect growth.', 'We do not expect growth.'), ('Including taxes', 'Excluding taxes'),
                     ('Revenue 10', 'Revenue 11'), ('Revenue $10', 'Revenue $ 10'), ('Revenue 10%', 'Revenue 10 %'), ('Net sales (1.2)', 'Net sales ( 1.2 )')):
            with self.subTest(chandra=a, free=b):
                self.assertFalse(routing.route(TEXT.format(a), 50, both(b))[0])

    def test_a_table_with_no_free_evidence(self):  # a table is flagged; no free evidence is no support
        table = '<div data-bbox="0 0 1000 1000" data-label="Table"><table><tr><td>Debt</td><td>5.1x</td></tr></table></div>'
        self.assertEqual(routing.route(table, 50, None), (True, ['table', 'no support']))

    def test_no_support_guard(self):  # v6: a text block none of whose words either free tool reads at its place
        self.assertEqual(routing.route(TEXT.format('DRAPE'), 50, both('')), (True, ['no support']))
        self.assertEqual(routing.route(TEXT.format('DRAPE'), 50, both('ORACLE')), (True, ['no support']))
        self.assertEqual(routing.route(TEXT.format('Total DRAPE'), 50, both('Total ORACLE')), (False, []))   # one shared word: a warning, never a certificate

    def test_missing_or_failed_reading(self):
        self.assertEqual(routing.route('', None, None), (True, ['no reading']))
        self.assertTrue(routing.route(None, None, None)[0])


if __name__ == '__main__':
    unittest.main()
