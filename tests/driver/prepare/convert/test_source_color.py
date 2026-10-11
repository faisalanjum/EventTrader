"""Required foreground colour survives with its own occurrence (colour-preservation-implement-20261011; the public contract
validation_next_20261007/public/test_complete_case_review_06_v1/QUALIFIER_CONTRACT.md and its invented witness). Expected values are the CSS
cascade's computed colours, written per source occurrence before the code (CSS Color: purple rgb(128, 0, 128), green rgb(0, 128, 0), red
rgb(255, 0, 0), blue rgb(0, 0, 255), #c00000 rgb(192, 0, 0); the initial colour rgb(0, 0, 0)). Every shown bound run keeps its colour, a default one
too; a run the render cannot bind, a hidden run or a page whose sheet no evidence answers claims none."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid

Source = screen_grid.Source
PURPLE, GREEN, RED, BLUE, DARK, BLACK = 'rgb(128, 0, 128)', 'rgb(0, 128, 0)', 'rgb(255, 0, 0)', 'rgb(0, 0, 255)', 'rgb(192, 0, 0)', 'rgb(0, 0, 0)'
WITNESS = b'<!doctype html><meta charset="utf-8"><p><span style="color:purple">Lantern</span> beside <span style="color:green">Harbor</span>.</p>\n'


class SourceColor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def prepare(self, raw, members=None):
        return html_route.prepare(raw, 'doc', hashlib.sha256(raw).hexdigest(), self.browser, source=Source('doc.htm', {'doc.htm': raw, **(members or {})}))[0]

    def owners(self, route):  # (owner, final text) in reading order: text units, and each table's cells (a cell by its table and its anchor's first byte)
        for u in route['units']:
            if u.get('kind') == 'table':
                for c in u.get('cells') or []: yield {'unit': u['id'], 'cell': c['anchor']['byte_start']}, c.get('text') or ''
            elif u.get('kind') != 'image': yield {'unit': u['id']}, u.get('text') or ''

    def colours(self, route, word, n=0):  # the colours recorded over the n-th occurrence of `word` in the owners' final text; it must be covered whole
        found = [(o, i) for o, t in self.owners(route) for i in range(len(t)) if t.startswith(word, i)]
        (o, i), span, got, covered = found[n], set(range(found[n][1], found[n][1] + len(word))), set(), set()
        for r in route['source_color']['records']:
            for w in r.get('owners') or []:
                if w.get('unit') == o['unit'] and w.get('cell') == o.get('cell'):
                    for a, b in w['text_at']:
                        if span & set(range(a, b)): got.add(r['color']); covered |= span & set(range(a, b))
        return got if covered == span else ('not covered whole', got)

    def test_each_word_keeps_its_own_colour_and_ordinary_text_its_default(self):  # the public invented witness
        route = self.prepare(WITNESS)
        self.assertEqual(route['status'], 'OK')
        self.assertEqual(self.colours(route, 'Lantern'), {PURPLE}); self.assertEqual(self.colours(route, 'Harbor'), {GREEN})
        self.assertEqual(self.colours(route, 'beside'), {BLACK}); self.assertEqual(self.colours(route, '.'), {BLACK})

    def test_uniform_mixed_and_inherited_cells(self):
        raw = (b'<html><body><table><tr><td style="color:red">Loss</td><td>Net <span style="color:#c00000">(5)</span></td></tr>'
               b'<tr style="color:green"><td>Gain</td><td>4</td></tr></table></body></html>')
        route = self.prepare(raw)
        self.assertEqual(self.colours(route, 'Loss'), {RED}); self.assertEqual(self.colours(route, 'Net'), {BLACK}); self.assertEqual(self.colours(route, '(5)'), {DARK})
        self.assertEqual(self.colours(route, 'Gain'), {GREEN}); self.assertEqual(self.colours(route, '4'), {GREEN})

    def test_document_and_declared_sheet_classes_and_the_missing_sheet(self):
        inner = self.prepare(b'<html><head><style>.neg{color:#c00000}</style></head><body><p>Class <span class="neg">(9)</span></p></body></html>')
        self.assertEqual(self.colours(inner, '(9)'), {DARK}); self.assertEqual(self.colours(inner, 'Class'), {BLACK})
        raw = b'<html><head><link rel="stylesheet" href="s.css"></head><body><p>Sheet <span class="neg">(1)</span></p></body></html>'
        declared = self.prepare(raw, {'s.css': b'.neg{color:#c00000}'})
        self.assertEqual(declared['status'], 'OK'); self.assertEqual(self.colours(declared, '(1)'), {DARK}); self.assertEqual(self.colours(declared, 'Sheet'), {BLACK})
        missing = self.prepare(raw)  # the same page, its sheet answered by no evidence: the fallback render's colour is no proved original style
        self.assertEqual(missing['status'], 'PARTIAL'); self.assertFalse(missing['source_color']['read']); self.assertNotIn('records', missing['source_color'])

    def test_repeated_text_keeps_its_own_occurrence(self):
        route = self.prepare(b'<html><body><p><span style="color:red">7</span> and 7</p></body></html>')
        self.assertEqual(self.colours(route, '7', 0), {RED}); self.assertEqual(self.colours(route, '7', 1), {BLACK})

    def test_a_word_split_by_markup_keeps_each_part_its_own_colour(self):
        route = self.prepare(b'<html><body><p>Pro<span style="color:blue">fit</span> line</p></body></html>')
        self.assertIn('Profit line', [t for _, t in self.owners(route)])
        self.assertEqual(self.colours(route, 'Pro'), {BLACK}); self.assertEqual(self.colours(route, 'fit'), {BLUE}); self.assertEqual(self.colours(route, 'line'), {BLACK})

    def test_hidden_and_misread_runs_claim_no_owner_colour(self):
        route = self.prepare(b'<html><body><p>Seen</p><p style="display:none"><span style="color:red">Gone</span></p></body></html>')
        self.assertEqual(self.colours(route, 'Seen'), {BLACK}); self.assertNotIn('Gone', ''.join(t for _, t in self.owners(route)))
        self.assertFalse([r for r in route['source_color']['records'] if r['color'] == RED and r.get('owners')])
        misread = self.prepare(b'<html><body><p>Caf\xc3\xa9 <span style="color:red">net</span></p></body></html>')  # no declaration: the browser reads windows-1252
        self.assertEqual(misread['status'], 'PARTIAL'); self.assertEqual(self.colours(misread, 'Caf'), ('not covered whole', set()))
        self.assertTrue(misread['source_color']['unresolved'])

    def test_prior_inline_and_formatting_records_stay(self):
        route = self.prepare(b'<html><body><p>Area x<sup>2</sup> and <s>old</s> text</p></body></html>')
        self.assertEqual([r['raw'] for r in route['source_inline']['records']], ['2'])
        self.assertEqual(self.colours(route, 'Area'), {BLACK})


if __name__ == '__main__':
    unittest.main()
