"""A short number, a roman numeral or "Page N" that the tool took for a page number (EdgarTools' DocumentBuilder._is_page_number_container, decided by
style alone) was deleted with the page numbers - a filer's ZIP code, a right-aligned "125" under "Shares outstanding", a tagged shares fact, a debt
class "IV" (accuracy-fable-1 A1; Codex's controls). Nothing is deleted now: what the page shows stays, in source order, and a real page number is
its own unit. Runs the real tool (required)."""
import hashlib
import unittest

from driver.prepare.convert import edgartools_html as eh


def texts(raw):
    route = eh.convert(raw, 'page.htm', hashlib.sha256(raw).hexdigest())
    return [x.get('text', '') for u in route['units'] for x in [u] + (u.get('cells') or [])]


class PageNumberCandidates(unittest.TestCase):
    def test_facts_the_tool_took_for_page_numbers_are_kept_in_order(self):  # each failed before: the element was deleted
        cases = (('<div>7035 Ridge Road, Hanover, Maryland</div><div style="margin-bottom:1pt;text-align:center"><ix:nonNumeric name="dei:EntityAddressPostalZipCode" contextRef="c">21076</ix:nonNumeric></div><p>Registrant telephone number</p>',
                  ['7035 Ridge Road, Hanover, Maryland', '21076', 'Registrant telephone number']),
                 ('<div>7035 Ridge Road, Hanover, Maryland</div><div style="margin-bottom:1pt;text-align:center">21076</div><p>Registrant telephone number</p>',
                  ['7035 Ridge Road, Hanover, Maryland', '21076', 'Registrant telephone number']),
                 ('<h1>Shares outstanding</h1><p style="text-align:right">125</p><p>at year end</p>', ['Shares outstanding', '125', 'at year end']),
                 ('<h1>Shares outstanding</h1><p style="text-align:center"><ix:nonFraction name="x:Shares" unitRef="shares" contextRef="current">125</ix:nonFraction></p>',
                  ['Shares outstanding', '125']),
                 ('<h1>Debt class</h1><p style="text-align:right">IV</p>', ['Debt class', 'IV']))
        for body, want in cases:
            with self.subTest(body=body[:60]): self.assertEqual(texts(('<html><body>%s</body></html>' % body).encode()), want)

    def test_a_page_number_stays_its_own_unit_in_source_order(self):  # a page number is kept as what the page shows; the key's page-number exclusions decide its scoring
        for footer in ('<div style="bottom:0;position:absolute;width:100%">12</div>', '<p style="text-align:center">12</p>',
                       '<div style="margin-bottom:0pt;text-align:center">12</div>'):
            raw = ('<html><body><p>The text of the page.</p>%s<p>The next page.</p></body></html>' % footer).encode()
            with self.subTest(footer=footer): self.assertEqual(texts(raw), ['The text of the page.', '12', 'The next page.'])


if __name__ == '__main__': unittest.main()
