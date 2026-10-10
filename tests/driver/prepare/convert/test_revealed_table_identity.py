"""A table's source identity is a fact of the original bytes, apart from whether the page shows it: a table a sheet shows again, or whose descendant
restores its visibility, keeps its own start tag (`source_table`), as a shown one does; a hidden table still gives no visible fact; repeated and nested tables
each keep their own tag in either order. Expected positions are read off the original bytes (Root, OCR_TABLE_IDENTITY_RELEASE; root's five controls)."""
import unittest

from driver.prepare.convert import anchor, edgartools_html as eh, html_route

REVEAL = b'<style>.s{display:table!important}.v{visibility:visible!important}</style>'


def page(body, head=REVEAL): return b'<!doctype html><html><head><meta charset="utf-8">' + head + b'</head><body>' + body + b'</body></html>'


class InTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def route(self, raw):
        r, facts = html_route.prepare(raw, 'f.htm', anchor.sha256(raw), self.browser)
        return r, [u for u in r['units'] if u['kind'] == 'table'], [u for u in r['units'] if u['kind'] == 'image']

    def test_a_table_a_sheet_shows_again_keeps_its_own_tag(self):  # failed before: source_table None (the tag was listed only where the scanner saw it shown)
        for cell in (b'<td><img src="p.png" width="20" height="20"></td>', b'<td>Revenue</td><td>12</td>'):  # picture-only, text-bearing
            raw = page(b'<p>a</p><table class="s" style="display:none"><tr>' + cell + b'</tr></table><p>b</p>')
            with self.subTest(cell=cell):
                r, tables, pics = self.route(raw)
                self.assertEqual([t['source_table'] for t in tables], [{'tag_start': raw.index(b'<table class="s"'), 'claims': 1}])
                self.assertTrue(all(p['cell']['table'] == tables[0]['id'] for p in pics))

    def test_a_table_whose_descendant_restores_visibility_keeps_its_own_tag(self):
        for cell in (b'<td><img class="v" src="p.png" width="20" height="20"></td>', b'<td class="v">Shown</td>'):
            raw = page(b'<p>a</p><table style="visibility:hidden"><tr>' + cell + b'</tr></table><p>b</p>')
            with self.subTest(cell=cell):
                r, tables, _ = self.route(raw)
                self.assertEqual([t['source_table'] for t in tables], [{'tag_start': raw.index(b'<table style'), 'claims': 1}])

    def test_a_hidden_table_still_gives_no_visible_fact(self):
        for head in (b'<style>table{display:none}</style>', b''):  # uncertain (a sheet hides it) and certified (inline)
            raw = page(b'<p>a</p><table style="display:none"><tr><td>Secret</td><td><img src="p.png" width="20" height="20"></td></tr></table><p>b</p>', head)
            with self.subTest(head=head):
                r, tables, pics = self.route(raw)
                self.assertEqual((tables, pics, any('Secret' in (u.get('text') or '') for u in r['units'])), ([], [], False))

    def test_repeated_and_nested_tables_each_keep_their_own_tag_in_either_order(self):
        shown, revealed = b'<table><tr><td>Same</td></tr></table>', b'<table class="s" style="display:none"><tr><td>Same</td></tr></table>'
        for first, second in ((shown, revealed), (revealed, shown)):
            raw = page(b'<p>a</p>' + first + b'<p>m</p>' + second + b'<p>b</p>')
            with self.subTest(first=first[:12]):
                _, tables, _ = self.route(raw)
                a = raw.index(first); b = raw.index(second, a + len(first))
                self.assertEqual([t['source_table'] for t in tables], [{'tag_start': a, 'claims': 1}, {'tag_start': b, 'claims': 1}])
        raw = page(b'<table><tr><td>Outer</td><td><table class="s" style="display:none"><tr><td>Inner</td></tr></table></td></tr></table>')
        _, tables, _ = self.route(raw)
        self.assertEqual([t['source_table']['tag_start'] for t in tables], [raw.index(b'<table><tr><td>Outer'), raw.index(b'<table class="s"')])
        self.assertEqual(tables[1]['cell']['table'], tables[0]['id'])  # its holder, as before

    def test_old_saved_parses_are_not_reused(self):  # the tool's input gains a code on tables the scanner reads as hidden: the setting names it
        self.assertEqual(eh.SETTINGS['table_identity'], 'own start tag, shown or hidden')
