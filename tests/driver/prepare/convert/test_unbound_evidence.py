"""Text no browser verdict reaches on an uncertain page (Root, fostered_text_20261009/ROOT_DESIGN_GATE.md). Chromium moves text that stands loose in
a table, outside every cell, to before the table - out of a hidden row or table too - while the page-visibility mark (a comment) stays where it
was, so the verdict cannot bind it, and EdgarTools reads only a table's cells: the browser shows text no unit holds. Each such run keeps its unbound
span, and beside it its exact source fragment as unresolved evidence (`page_visibility['unresolved']`: `at`; `raw`, those bytes read as UTF-8
and nothing more - no reference decoded, so it encodes back to them exactly - or, where they are not UTF-8, the `bytes` in hex; `why`): source
spelling, never browser text, never a unit, never shown or hidden, its place unknown. The route is PARTIAL for it. Offline Chrome; playwright is required (a missing install fails, never skips)."""
import hashlib
import unittest

from driver.prepare.convert import anchor, edgartools_html as eh, html_route, screen_grid as sg


def page(body, head=b''): return b'<html><head>' + head + b'</head><body>' + body + b'</body></html>'


PAGES = {'hidden_row': page(b'<table><tr style="display:none">Net income was $56 million.<td>Hidden cell 99</td></tr><tr><td>Visible cell 77</td></tr></table>'),
         'hidden_table': page(b'<div><table style="display:none">Freed from a hidden table $9.9<tr><td>Hidden cell 98</td></tr></table></div><p>After 1.</p>'),
         'shown_loose': page(b'<table>Total revenue was $1,234 million in 2024.<tr><td>Q1 sales</td><td>310</td></tr></table><p>Plain paragraph after the table.</p>'),
         'shown_loose_heading': page(b'<table>Total revenue was $1,234 million.<tr><td>Q1 sales</td></tr></table>'),
         'hidden_controls': page(b'<table><span style="display:none">Hidden note 5</span><tr><td>Row cell 1</td></tr><tr style="display:none"><td>Hidden row cell 88</td></tr></table><p>Shown paragraph 3.</p>'),
         'repeated': page(b'<table><tr style="display:none">Total 42<td>h1</td></tr><tr><td>Total 42</td></tr><tr style="display:none">Total 42<td>h2</td></tr></table>'),
         'entities': page(b'<table><tr style="display:none">Fee &amp; tax &#36;7<td>h3</td></tr><tr><td>Shown 8</td></tr></table>'),
         'not_utf8': page(b'<table><tr style="display:none">\x93Quoted\x94 9<td>h4</td></tr><tr><td>Shown 9</td></tr></table>'),
         'failed': page(b'<table><tr style="display:none">Loose 10<td>h5</td></tr></table>', head=b'<link rel="stylesheet" href="s.css">')}
LITERAL = {'hidden': b'<html><body><xmp style="display:none">&amp; not shown</xmp></body></html>', 'shown': b'<html><body><xmp>&amp; not shown</xmp></body></html>'}  # Root's probe (ROOT_RAW_FRAGMENT_PROBE_v1)


def strings(x):  # every string anywhere in a route
    if isinstance(x, dict): return [s for v in x.values() for s in strings(v)]
    if isinstance(x, list): return [s for v in x for s in strings(v)]
    return [x] if isinstance(x, str) else []


def unit_texts(route): return [t for u in route['units'] for t in ([c['text'] for c in u.get('cells') or []] or [u.get('text', '')])]


class UnboundEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                cls.routes = {k: html_route.prepare(raw, k + '.htm', hashlib.sha256(raw).hexdigest(), browser) for k, raw in PAGES.items()}
                raw = PAGES['hidden_row']; cls.vis, _ = html_route.visibility(raw, anchor.Visible(raw), browser)
                cls.literal = {k: sg.page_visibility(raw, anchor.Visible(raw), browser) for k, raw in LITERAL.items()}  # the verdict itself, as Root's probe asked it
            finally: browser.close()

    def evidence(self, name):  # each unbound span with its fragment beside it, aligned
        pv = self.routes[name][0]['page_visibility']
        self.assertEqual([[r['at']['byte_start'], r['at']['byte_end_exclusive']] for r in pv['unresolved']], pv['unbound'])
        return pv['unresolved']

    def test_text_freed_from_a_hidden_row_or_table_is_kept_as_source_evidence_and_the_route_is_partial(self):  # failed before: OK; from the row, the text nowhere
        # units as before: out of a hidden row no unit holds it; a hidden table EdgarTools reads as a heading claim once its cells are left out
        for name, text, units in (('hidden_row', 'Net income was $56 million.', ['Visible cell 77']), ('hidden_table', 'Freed from a hidden table $9.9', ['Freed from a hidden table $9.9', 'After 1.'])):
            with self.subTest(name):
                route, facts = self.routes[name]; raw = PAGES[name]
                self.assertEqual((route['status'], route['error']), ('PARTIAL', 'page visibility: 1 text run without a browser verdict'))
                [rec] = self.evidence(name)
                self.assertEqual(rec, {'at': {'byte_start': raw.index(text.encode()), 'byte_end_exclusive': raw.index(text.encode()) + len(text)}, 'raw': text, 'why': 'unbound'})
                self.assertEqual(unit_texts(route), units)  # no unit made of it here
                self.assertEqual(route['uncovered'], [])  # nor read as shown (the scanner hides it)
                self.assertEqual(facts['visibility']['unresolved'], 1)

    def test_loose_text_in_a_shown_table_keeps_what_it_had_and_gains_the_same_evidence(self):  # failed before: OK
        for name, text, units, uncovered in (('shown_loose', 'Total revenue was $1,234 million in 2024.', ['Q1 sales', '310', 'Plain paragraph after the table.'], ['Total revenue was $1,234 million in 2024.']),
                                             ('shown_loose_heading', 'Total revenue was $1,234 million.', ['Total revenue was $1,234 million.'], ['Q1 sales'])):  # a one-cell table: EdgarTools' heading claim, as before
            with self.subTest(name):
                route, _ = self.routes[name]
                self.assertEqual(route['status'], 'PARTIAL'); self.assertEqual([r['raw'] for r in self.evidence(name)], [text])
                self.assertEqual([u['text'] for u in route['uncovered']], uncovered); self.assertEqual(unit_texts(route), units)  # as before

    def test_hidden_text_stays_out_everywhere_and_a_page_every_run_of_which_is_bound_stays_complete(self):
        route, facts = self.routes['hidden_controls']
        self.assertEqual((route['status'], route['error']), ('OK', None)); self.assertNotIn('unresolved', route['page_visibility']); self.assertNotIn('unresolved', facts['visibility'])
        every = ' '.join(strings(route))
        for hidden in ('Hidden note 5', 'Hidden row cell 88'): self.assertNotIn(hidden, every)
        for name in ('hidden_row', 'hidden_table'):
            self.assertFalse(any('Hidden cell' in s for s in strings(self.routes[name][0])))  # the hidden cells beside the freed text stay out

    def test_each_occurrence_is_its_own_record_never_matched_by_text(self):  # repeated identical text, shown once and freed twice
        route, _ = self.routes['repeated']; raw = PAGES['repeated']
        recs = self.evidence('repeated'); first = raw.index(b'Total 42'); last = raw.rindex(b'Total 42')
        self.assertEqual([(r['raw'], r['at']['byte_start']) for r in recs], [('Total 42', first), ('Total 42', last)])
        self.assertEqual(unit_texts(route), ['Total 42'])  # the shown cell, once
        self.assertEqual(route['error'], 'page visibility: 2 text runs without a browser verdict')

    def test_references_stay_as_written_and_bytes_that_are_not_utf8_are_kept_whole(self):
        [rec] = self.evidence('entities')
        self.assertEqual(rec['raw'], 'Fee &amp; tax &#36;7')  # the source spelling: no reference decoded (Root, ROOT_RAW_EVIDENCE_CORRECTION)
        [rec] = self.evidence('not_utf8'); raw = PAGES['not_utf8']
        self.assertNotIn('raw', rec)  # never a guessed character
        self.assertEqual(bytes.fromhex(rec['bytes']), raw[rec['at']['byte_start']:rec['at']['byte_end_exclusive']]); self.assertIn(b'\x93Quoted\x94', bytes.fromhex(rec['bytes']))

    def test_literal_text_is_kept_as_written_whether_its_page_hides_it_or_not(self):  # Root's probe: hidden, the record said "& not shown"
        for k in LITERAL:
            with self.subTest(k): self.assertEqual([(r['raw'], r['why']) for r in self.literal[k]['unresolved']], [('&amp; not shown', 'literal text')])

    def test_every_fragment_is_its_own_bytes_exactly(self):  # raw encodes back to them; bytes are them
        pages = [(PAGES[k], r['page_visibility']) for k, (r, _) in self.routes.items() if 'page_visibility' in r] + [(LITERAL[k], v) for k, v in self.literal.items()]
        recs = [(raw, x) for raw, pv in pages for x in pv.get('unresolved') or []]
        self.assertGreaterEqual(len(recs), 10)
        for raw, x in recs:
            got = x['raw'].encode('utf-8') if 'raw' in x else bytes.fromhex(x['bytes'])
            self.assertEqual(got, raw[x['at']['byte_start']:x['at']['byte_end_exclusive']])

    def test_a_page_the_browser_cannot_read_keeps_its_reason_alone(self):  # no verdict at all: no unbound span, no evidence, the failure as before
        route, facts = self.routes['failed']
        self.assertEqual(route['status'], 'PARTIAL'); self.assertTrue(route['error'].startswith("page visibility: RuntimeError('style sheets the page names cannot be read offline"))
        self.assertNotIn('without a browser verdict', route['error']); self.assertNotIn('page_visibility', route); self.assertEqual(list(facts['visibility']), ['error'])

    def test_a_saved_parse_reused_cannot_hide_the_evidence(self):  # the evidence is the verdict's, not the tool's: a parse saved earlier changes nothing
        raw = PAGES['hidden_row']; sha = hashlib.sha256(raw).hexdigest(); saved = eh.parse(raw, self.vis)
        reused = eh.convert(raw, 'hidden_row.htm', sha, parse=lambda r, v: saved, vis=self.vis)
        self.assertEqual(reused['page_visibility']['unresolved'], self.routes['hidden_row'][0]['page_visibility']['unresolved'])


if __name__ == '__main__':
    unittest.main()
