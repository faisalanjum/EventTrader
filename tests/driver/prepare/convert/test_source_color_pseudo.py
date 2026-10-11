"""The named limit of an element's computed colour (Root, OCR_COLOR_NATIVE_LIMIT_NOTE_20261011): a `::first-letter` or `::first-line` rule may paint
some of a run's characters in another colour than the element holding them; which characters depends on layout. Such a run keeps the element's colour
only with the pseudo-element's colour beside it as an explicit uncertainty, never as a proved colour of every character. A pseudo rule that changes no
colour, and ordinary text, stay plain. Expected values are CSS's (red rgb(255, 0, 0), blue rgb(0, 0, 255), green rgb(0, 128, 0), initial rgb(0, 0, 0))."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid

Source = screen_grid.Source
RED, BLUE, GREEN, BLACK = 'rgb(255, 0, 0)', 'rgb(0, 0, 255)', 'rgb(0, 128, 0)', 'rgb(0, 0, 0)'


class FirstLetterLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def records(self, raw, word):  # the colour records over `word` in its text unit's final text
        route = html_route.prepare(raw, 'doc', hashlib.sha256(raw).hexdigest(), self.browser, source=Source('doc.htm', {'doc.htm': raw}))[0]
        unit = next(u for u in route['units'] if word in (u.get('text') or '')); i = unit['text'].index(word); span = set(range(i, i + len(word)))
        return [r for r in route['source_color']['records'] for o in r.get('owners') or [] if o['unit'] == unit['id'] and any(span & set(range(a, b)) for a, b in o['text_at'])]

    def test_a_first_line_or_first_letter_colour_is_kept_beside_as_uncertainty(self):
        raw = b'<html><head><style>p.a::first-line{color:red} p.b::first-letter{color:blue}</style></head><body><p class="a">Alpha beta</p><p class="b">Gamma</p></body></html>'
        line, letter = self.records(raw, 'Alpha'), self.records(raw, 'Gamma')
        self.assertTrue(line and letter)
        self.assertTrue(all(['::first-line', RED] in r.get('pseudo', []) for r in line)); self.assertTrue(all(['::first-letter', BLUE] in r.get('pseudo', []) for r in letter))

    def test_a_pseudo_rule_that_sets_no_colour_and_plain_text_stay_plain(self):
        raw = b'<html><head><style>p.c::first-letter{font-weight:bold}</style></head><body><p class="c" style="color:green">Delta</p><p>Plain</p></body></html>'
        delta, plain = self.records(raw, 'Delta'), self.records(raw, 'Plain')
        self.assertEqual({r['color'] for r in delta}, {GREEN}); self.assertEqual({r['color'] for r in plain}, {BLACK})
        self.assertFalse([r for r in delta + plain if 'pseudo' in r])


if __name__ == '__main__':
    unittest.main()
