import sys
import unittest
from decimal import Decimal

sys.path.insert(0, '/tmp/decider_claude_review_20261115')
from proposal_numbers import printed_decimal, normalize


class PrintedNumberChecks(unittest.TestCase):
    def test_real_endpoint_and_boundary_forms(self):
        cases = {'$11.21': '11.21', '$11.24': '11.24', '8.4%': '8.4',
                 '8.7%.': '8.7', '$4.86': '4.86', '$4.90,': '4.90',
                 '10.5%': '10.5', '11.4%.': '11.4', '$101': '101',
                 '20%,': '20', '0': '0', '.5': '.5', '-0.10': '-0.10',
                 '$1,000.50': '1000.50', '101,': '101'}
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(printed_decimal(source), Decimal(expected))

    def test_unsupported_forms_never_become_guesses(self):
        for source in ['12,34', 'NaN', 'Infinity', '1_000', '1..',
                       '12-20', 'FY2026', '18.5%next', '(12.5)']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                printed_decimal(source)

    def test_exact_scaling_and_source_sign(self):
        self.assertEqual(normalize('$11.21', 'm_usd_from_billions', 'positive'), ('11210', 'm_usd'))
        self.assertEqual(normalize('8.4%', 'unknown', 'positive'), ('8.4', 'unknown'))
        self.assertEqual(normalize('0', 'percent', 'zero'), ('0', 'percent'))
        self.assertEqual(normalize('5', 'usd', 'negative'), ('-5', 'usd'))
        exact = '12345678901234567890123456789.123456789'
        self.assertEqual(normalize(exact, 'count_thousand', 'positive')[0],
                         '12345678901234567890123456789123.456789')
        for args in [('-5', 'usd', 'positive'), ('5', 'usd', 'zero'), ('5', 'other_stated', 'positive')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                normalize(*args)


if __name__ == '__main__':
    unittest.main()
