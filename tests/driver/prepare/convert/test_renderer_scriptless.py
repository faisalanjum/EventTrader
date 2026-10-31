"""SCRIPTLESS prototype: a Renderer report page on the script-free path. (1) its include/report.css answered by the same package's IDEA report.css
only where the package proves the page is its Renderer output and nothing answers that exact address; (2) its declared Show.* controls decided by
the existing content rule on the JS-disabled page. Public package fixtures only (AMG 0001004434-23-000015, EQR 0000906107-25-000005)."""
import re
import copy, gzip, hashlib, json, unittest
from pathlib import Path
from driver.prepare.get import acquire
from driver.prepare.convert import context, html_route, screen_grid as sg

FX = Path(__file__).resolve().parents[1] / 'get' / 'fixtures'
COPIES = json.loads((FX / 'sec_copies.json').read_bytes())
BROWSER = '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell'
h = lambda b: hashlib.sha256(b).hexdigest()


def fetch(url):  # the public recorded SEC copy (a test fixture), never the network
    c = COPIES.get(url)
    return gzip.open(FX / c['file']).read() if c else None


def package(acc):
    e = json.loads((FX / f'{acc}.expected.json').read_bytes()); i = e['identity']
    m, f = acquire.parse_package(gzip.open(FX / f'{acc}.txt.gz').read(), acc, i['ciks'][0], i['form'], fetch=fetch)
    base = acquire._url(acquire._identity(acc, i['ciks'][0], i['form'])).rsplit('/', 1)[0] + '/'
    return m, f, base


AMG, EQR = package('0001004434-23-000015'), package('0000906107-25-000005')


class Bundle(unittest.TestCase):
    def test_binding_holds_only_for_the_packages_listed_renderer_page(self):
        for m, f, _ in (AMG, EQR):
            b = html_route.renderer_bundle('R1.htm', m, f)
            self.assertIsNotNone(b)
            self.assertEqual((b['member'], b['sha256']), ('report.css', h(f['report.css'])))
            self.assertEqual(b['report'], 'R1.htm')
        self.assertIsNone(html_route.renderer_bundle('amg-20230501.htm', *AMG[:2]))  # a filer document is no Renderer report

    def test_binding_refused_when_any_bundle_fact_differs(self):
        m, f, _ = AMG
        self.assertIsNone(html_route.renderer_bundle('R1.htm', m, dict(f, **{'report.css': f['report.css'] + b'\n.report td{display:none}'})))  # unreviewed bytes
        self.assertIsNone(html_route.renderer_bundle('R1.htm', m, {k: v for k, v in f.items() if k != 'report.css'}))  # unresolved/missing member
        self.assertIsNone(html_route.renderer_bundle('R1.htm', m, {k: v for k, v in f.items() if k != 'FilingSummary.xml'}))  # no Renderer manifest
        m2 = copy.deepcopy(m); next(x for x in m2['members'] if x['filename'] == 'report.css')['description'] = 'EX-99'
        self.assertIsNone(html_route.renderer_bundle('R1.htm', m2, f))  # not an SEC-added IDEA document


class Remap(unittest.TestCase):
    def setUp(self):
        self.m, self.f, self.base = AMG; self.b = html_route.renderer_bundle('R1.htm', self.m, self.f); self.url = self.base + 'include/report.css'

    def test_unbound_reference_is_answered_as_a_recorded_transformation(self):
        s = sg.Source('R1.htm', self.f, base=self.base, renderer_css=self.b); s.at('http://x.invalid/', self.f['R1.htm'])
        self.assertEqual(s.answer(self.url, 'stylesheet'), (200, 'text/css', self.f['report.css']))
        r = s.records[self.url]
        self.assertEqual((r['status'], r['reference'], r['member'], r['sha256']), ('renderer-remap', 'include/report.css', 'report.css', h(self.f['report.css'])))
        self.assertIn('url', r); self.assertNotEqual(r['status'], 200)  # never claimed as SEC's answer

    def test_never_for_navigation_other_names_or_other_kinds(self):
        s = sg.Source('R1.htm', self.f, base=self.base, renderer_css=self.b); s.at('http://x.invalid/', self.f['R1.htm'])
        self.assertIsNone(s.answer(self.url, 'document', navigation=True))
        self.assertIsNone(s.answer(self.base + 'include/other.css', 'stylesheet'))
        self.assertIsNone(s.answer(self.url, 'script'))

    def test_exact_member_and_recorded_response_win(self):
        s = sg.Source('R1.htm', dict(self.f, **{'include/report.css': b'p{}'}), base=self.base, renderer_css=self.b); s.at('http://x.invalid/', self.f['R1.htm'])
        self.assertEqual(s.answer(self.url, 'stylesheet')[2], b'p{}')
        s = sg.Source('R1.htm', self.f, base=self.base, observed={self.url: {'status': 404, 'observed_at': '2026-10-30T00:00:00Z', 'sha256': None}}, renderer_css=self.b); s.at('http://x.invalid/', self.f['R1.htm'])
        self.assertEqual(s.answer(self.url, 'stylesheet')[0], 404); self.assertEqual(s.records[self.url]['status'], 404)

    def test_never_with_a_context(self):
        with self.assertRaises(ValueError): sg.Source('R1.htm', self.f, base=self.base, context=object(), renderer_css=self.b)

    def test_no_binding_is_todays_refusal(self):
        s = sg.Source('R1.htm', self.f, base=self.base); s.at('http://x.invalid/', self.f['R1.htm']); self.assertIsNone(s.answer(self.url, 'stylesheet'))


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(executable_path=BROWSER, headless=True)

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def run_page(self, pkg=AMG, edit=None, members=None, bound=True, observed=None):
        m, f, base = pkg; f = dict(f, **(members or {})); raw = f['R1.htm'] if edit is None else edit(f['R1.htm']); f['R1.htm'] = raw; sha = h(raw)
        src = sg.Source('R1.htm', f, base=base, observed=observed, renderer_css=html_route.renderer_bundle('R1.htm', m, f) if bound else None)
        q = (lambda r: context.renderer_controls(raw, r, html_route.source_reading(raw, 'R1', sha, r)[0], self.browser, src)) if bound else None
        return html_route.prepare(raw, 'R1', sha, self.browser, src, qualify=q)

    def test_positive_public_pages_complete_with_recorded_warning(self):
        for pkg in (AMG, EQR):
            route, facts = self.run_page(pkg)
            self.assertEqual((route['status'], route.get('error')), ('OK', None))
            self.assertTrue(route['text_proved'])
            rc = facts['renderer_controls']; self.assertEqual(rc['reasons'], []); self.assertTrue(rc['outcome'].startswith('warning'))
            self.assertEqual([d['status'] for d in route['resources']['dependencies']], ['renderer-remap'])

    def assertKept(self, route, facts, part):
        self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('declared script action(s) not qualified', route['error'])
        self.assertTrue(any(part in w for w in facts['renderer_controls']['reasons']), facts['renderer_controls']['reasons'])

    def test_renamed_target_id(self):
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'id="defref_dei_AmendmentFlag"', b'id="defref_dei_AmendmentFlaX"')), "defref_dei_AmendmentFlag")

    def test_changed_show_js_bytes(self):
        self.assertKept(*self.run_page(members={'Show.js': AMG[1]['Show.js'] + b'\nShow.showAR=function(){};'}), 'Show.js')

    def test_extra_inline_script(self):
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'</head>', b'<script type="text/javascript">document.title="x";</script></head>', 1)), 'script')

    def test_non_renderer_action(self):
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'onclick="Show.hideAR();"', b'onclick="alert(1);"', 1)), 'not one renderer action')

    def test_top_form_is_its_own_show_on_this_standalone_page(self):  # CHANGED (Root/Codex final delta): a top-level page with no frame is its own top window
        route, facts = self.run_page(edit=lambda b: b.replace(b'onclick="Show.toggleNext( this );"', b'onclick="top.Show.toggleNext( this );"', 1))
        self.assertEqual((route['status'], facts['renderer_controls']['reasons']), ('OK', []))

    def test_a_source_class_outside_the_renderer_profile(self):  # CHANGED (Root 9:57 PM, Codex-confirmed Renderer-only flag): a viewer-only utility class (recorded
        # bootstrap .text-decoration-line-through) on an allowed <p> is inert on the EXACT reviewed Renderer route (only c564d6d0 applies; it names no such class).
        # The shared default (viewer path, late fallback) still refuses it: test_shared_guard_default_stays_conservative.
        route, facts = self.run_page(edit=lambda b: b.replace(b'<p>', b'<p class="text-decoration-line-through">', 1))
        self.assertEqual((route['status'], facts['renderer_controls']['reasons']), ('OK', []))

    def test_shared_guard_default_stays_conservative(self):  # the viewer path and late fallback call _dom_action_reasons without the flag
        acts = {'actions': [], 'ids': {}, 'reveal': {'targets': {}, 'toggles': [], 'source_styles': 0, 'classes': ['finTable'], 'decls': [], 'sheets': [], 'adopted': []}}
        self.assertTrue(any('source classes outside the reviewed Renderer profile' in w for w in context._dom_action_reasons(acts, {}, {}, [])))
        self.assertEqual(context._dom_action_reasons(acts, {}, {}, [], unknown_classes_inert=True), [])
        acts['reveal']['source_styles'] = 1  # the flag lifts ONLY the class-name reason
        self.assertEqual(len(context._dom_action_reasons(acts, {}, {}, [], unknown_classes_inert=True)), 1)

    def test_unknown_class_is_inert_under_the_exact_reviewed_sheet(self):  # Root 9:57 PM; the held fixed1000 classes
        for name in (b'item-list-element-wrapper', b'finTable'):
            route, facts = self.run_page(edit=lambda b: b.replace(b'<p>', b'<p class="' + name + b'">', 1))
            self.assertEqual((route['status'], facts['renderer_controls']['reasons']), ('OK', []), name)

    def test_unknown_class_stays_refused_with_a_changed_sheet(self):  # negative: unreviewed report.css bytes
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'<p>', b'<p class="finTable">', 1), members={'report.css': AMG[1]['report.css'] + b'\n.finTable{display:none}'}), 'no Renderer bundle binding')  # refused before the class check: no flag

    def test_unknown_class_stays_refused_with_an_additional_sheet(self):  # negative: a second stylesheet
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'<p>', b'<p class="finTable">', 1).replace(b'</head>', b'<link rel="stylesheet" type="text/css" href="extra.css"/></head>', 1)), 'source classes outside the reviewed Renderer profile')

    def test_unknown_class_stays_refused_with_another_handler(self):  # negative: an extra script / handler
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'<p>', b'<p class="finTable">', 1).replace(b'</head>', b'<script type="text/javascript">document.title="x";</script></head>', 1)), 'source classes outside the reviewed Renderer profile')
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'<p>', b'<p class="finTable">', 1), members={'Show.js': AMG[1]['Show.js'] + b'\nShow.showAR=function(){};'}), 'source classes outside the reviewed Renderer profile')

    def test_memory_error_is_a_resource_failure_not_no_binding(self):
        from edgar.sgml import filing_summary
        def boom(*a, **k): raise MemoryError('synthetic')
        saved = filing_summary.FilingSummary.parse; filing_summary.FilingSummary.parse = boom
        try:
            with self.assertRaises(MemoryError): html_route.renderer_bundle('R1.htm', *AMG[:2])
        finally: filing_summary.FilingSummary.parse = saved

    # Root ROOT_CSS_FALSE_SUCCESS_CHALLENGE (labelled synthetic negatives, never claims of SEC responses): the reviewed package member EXISTS, but the render
    # actually used something else at the page's own address - the route must not be upgraded to OK.
    def test_recorded_404_at_the_exact_address_is_not_upgraded(self):
        url = AMG[2] + 'include/report.css'
        route, facts = self.run_page(observed={url: {'status': 404, 'observed_at': 'SYNTHETIC-NEGATIVE-CONTROL', 'sha256': None}})
        self.assertKept(route, facts, 'effective stylesheet')
        self.assertIn(404, [d['status'] for d in route['resources']['dependencies']])  # the real (here: labelled) response stays the record

    def test_other_bytes_at_the_exact_address_are_not_upgraded(self):
        route, facts = self.run_page(members={'include/report.css': b'.report th { font-weight: normal; }'})
        self.assertKept(route, facts, 'effective stylesheet')

    # Codex T2 (independently reproduced false OK; its own baseline not repeated): a page <style> rule styles the clone Show.showAR makes (id removed)
    def test_inline_style_element_is_unproved_css(self):
        css = b'<style>table.authRefData:not([id])::before{content:"Amounts in millions."}</style>'  # Codex check_extra_css.py:15, byte-exact
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'</head>', css + b'</head>', 1)), 'source <style> elements: 1')  # the SHARED guard (both routes)

    def test_inline_style_attribute_generated_marker(self):  # Codex T3, byte-exact (check_inline_marker.py:15-16): no style element, no sheet, no script
        extra = b'<p style="display:list-item;list-style-position:inside;list-style-type:\'Amounts in millions. \'">'
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'<p>', extra, 1)), 'outside the supported reveal profile')

    # Known R38 class (Root 5:48 PM, INLINE_GAP_ASSESSMENT B): an XBRL text block's ordinary inline formatting in a VISIBLE value cell, outside every
    # reveal's context (not an ancestor of any control, target or toggle DIV). Declarations copied from the known page's own text block.
    TEXT_BLOCK = (b'<td class="text"><div style="text-indent:36pt"><span style="color:#000000;font-family:\'Times New Roman\',serif;font-size:10pt;'
                  b'font-weight:400;line-height:120%">8-K</span></div><span></span>')
    CONTROL_CELL = b'<td class="pl" style="border-bottom: 0px;" valign="top"><a class="a" href="javascript:void(0);" onclick="Show.showAR( this, \'defref_dei_DocumentType\', window );">'

    def test_visible_text_block_formatting_outside_every_reveal_context(self):
        route, facts = self.run_page(edit=lambda b: b.replace(b'<td class="text">8-K<span></span>', self.TEXT_BLOCK, 1))
        self.assertEqual((route['status'], route.get('error')), ('OK', None)); self.assertTrue(route['text_proved'])
        self.assertEqual(facts['renderer_controls']['reasons'], [])

    def test_same_formatting_on_a_controls_ancestor_is_refused(self):  # the clone's insertion context: inherited by what showAR reveals there
        edit = lambda b: b.replace(self.CONTROL_CELL, self.CONTROL_CELL.replace(b'border-bottom: 0px;', b"border-bottom: 0px;font-family:'Times New Roman',serif;text-indent:36pt;"), 1)
        self.assertKept(*self.run_page(edit=edit), 'source inline declarations outside the effect profile')

    def test_symbol_font_on_the_targets_ancestor_is_refused(self):  # inherited by every definition
        self.assertKept(*self.run_page(edit=lambda b: re.sub(rb'(</table>\s*<div style="display: none;)', rb'\1font-family:Wingdings;', b, count=1)),
                        'source inline declarations outside the effect profile')

    MARKER = b"display:list-item;list-style-position:inside;list-style-type:'Amounts in millions. '"  # Codex T3's own declarations

    DECIMAL = b'display:list-item;list-style-position:inside;list-style-type:decimal'  # a real counter consumer: its marker prints the list-item counter
    # A sibling counter change, in no reveal's ancestor chain. Native probe 6:07 PM (pinned Chromium 147): counter-reset/-set/-increment on a plain sibling or
    # on the parent left the decimal marker at '1. '; only a preceding sibling LIST ITEM (its own marker hidden) with counter-increment moved it to '42. '.
    RESET = b'<div style="display:list-item;list-style-type:none;counter-increment: list-item 41"></div>'

    def markers(self, edit):
        route, facts = self.run_page(edit=edit)
        return route['status'], facts['renderer_controls']['reasons'], [g['fragments'] for g in route['generated_content']['records'] if g['pseudo'] == 'marker']

    def test_cross_sibling_counter_changes_a_visible_decimal_marker(self):  # independent native positive control (Root 6:01 PM): the effect is real
        item = b'<div style="' + self.DECIMAL + b'">8-K</div><span></span>'
        plain = self.markers(lambda b: b.replace(b'<td class="text">8-K<span></span>', b'<td class="text">' + item, 1))
        moved = self.markers(lambda b: b.replace(b'<td class="text">8-K<span></span>', b'<td class="text">' + self.RESET + item, 1))
        self.assertEqual((plain, moved), (('OK', [], [['1. ']]), ('OK', [], [['42. ']])))  # same page, only the sibling differs

    def test_cross_sibling_counter_reaching_a_target_is_held_by_the_target_guard(self):  # the same consumer INSIDE a definition, the reset on its container's preceding sibling
        edit = lambda b: re.sub(rb'(</table>\s*)(<div style="display: none;">)', lambda m: m.group(1) + self.RESET + m.group(2), b, count=1).replace(
            b'<p>', b'<p style="' + self.DECIMAL + b'">', 1)
        route, facts = self.run_page(edit=edit); self.assertKept(route, facts, 'outside the supported reveal profile')
        self.assertTrue(any(w.startswith('Show.showAR target') and 'display: list-item' in w for w in facts['renderer_controls']['reasons']), facts['renderer_controls']['reasons'])  # the TARGET guard holds it

    def test_visible_marker_outside_every_reveal_context_is_read_by_the_ordinary_generated_content_carrier(self):  # as on any HTML page
        route, facts = self.run_page(edit=lambda b: b.replace(b'<td class="text">8-K<span></span>', b'<td class="text"><div style="' + self.MARKER + b'">8-K</div><span></span>', 1))
        self.assertEqual((route['status'], facts['renderer_controls']['reasons']), ('OK', []))
        self.assertIn(('marker', ['Amounts in millions. '], 'inserts'), [(g['pseudo'], g['fragments'], g['role']) for g in route['generated_content']['records']])

    # Known R4 class (Root 6:35 PM): Renderer footnotes - a superscript reference marker and the outerFootnotes/outerFootnote block, markup copied from the
    # known page's own footnote (its footnote text shortened). The marker sits in an ordinary value cell; the block closes the report table.
    SUP = b'<td class="text">8-K<sup>[1]</sup><span></span>'
    FOOTNOTES = (b'<tr><td colspan="2"><table class="outerFootnotes" width="100%"><tr class="outerFootnote"> <td style="vertical-align: top; width: 12pt;" valign="top">[1]</td>'
                 b' <td style="vertical-align: top;" valign="top">Footnote text</td></tr></table></td></tr>')

    def with_sup(self, b): return b.replace(b'<td class="text">8-K<span></span>', self.SUP, 1)
    def with_footnotes(self, b): return re.sub(rb'(</table>)(\s*<div style="display: none;">)', lambda m: self.FOOTNOTES + m.group(1) + m.group(2), b, count=1)

    def ok(self, edit):
        route, facts = self.run_page(edit=edit)
        self.assertEqual((route['status'], route.get('error'), facts['renderer_controls']['reasons']), ('OK', None, []))
        return route

    def test_footnote_block_only(self):  # split positive (a): the singular Renderer row class no reviewed sheet references
        self.ok(self.with_footnotes)

    # Footnote reference cells (Root 10:07 PM, FN_PROOF): the real fixed1000 R-page shape - a <td class="fn"> beside a value cell, empty or holding <sup>[n]</sup>.
    FN_CELL = b'<td class="fn" style="border-bottom: 0px;"><sup>[1]</sup></td>'
    FN_EMPTY = b'<td class="fn" style="border-bottom: 0px;"></td>'

    def test_fn_footnote_reference_cells_are_admitted_and_kept(self):
        cell = b'<td class="text">8-K<span></span>\n</td>'
        def edit(b):
            assert b.count(cell) == 1, 'fixture cell'  # the edit must really insert the fn cells
            return self.with_footnotes(b.replace(cell, cell + self.FN_CELL + self.FN_EMPTY, 1))
        route = self.ok(edit)
        cells = sorted((c for u in route['units'] for c in u.get('cells') or []), key=lambda c: c['source']['byte_start'])
        fn = [c for c in cells if c['text'] == '[1]' and c['tag'] == 'td']
        self.assertTrue(fn, 'the fn cell is a cell of its row')
        sups = [x for x in route['source_inline']['records'] if x.get('raw') == '[1]' and any(a.get('tag') == 'sup' and a.get('vertical_align') == 'super' for a in x.get('ancestors') or [])]
        self.assertEqual([o['cell'] for x in sups for o in x['owners']], [fn[0]['anchor']['byte_start']])  # exactly one raised marker, owned by the fn cell

    # The remaining c564 roles (Root 10:24 PM, ROLE_GUARD proof): each effect read by its EXISTING carrier on the script-free path; no role guard is left.
    CELL8K = b'<td class="text">8-K<span></span>'

    def styled(self, edit, text):
        raw = edit(AMG[1]['R1.htm']); assert raw.count(text) == 1, 'the edit must insert the text once'
        route = self.ok(edit); i = raw.index(text)
        return route, [r for r in route['source_style']['records'] if r['at']['byte_start'] == i]

    def test_note_role_is_kept_as_italic_bold(self):  # .report .text .note { font-style: italic; font-weight: bold }
        route, rec = self.styled(lambda b: b.replace(self.CELL8K, b'<td class="text"><span class="note">Note text</span> 8-K<span></span>', 1), b'Note text')
        self.assertEqual([(r['font_style'], r['weight'], bool(r['boxes'])) for r in rec], [('italic', '700', True)])

    def test_more_role_is_a_hidden_run_kept_without_owner(self):  # .report .text .more { display: none }: kept, never shown
        route, rec = self.styled(lambda b: b.replace(self.CELL8K, b'<td class="text">8-K<span class="more">Hidden tail</span><span></span>', 1), b'Hidden tail')
        self.assertEqual([(r['boxes'], r.get('owners')) for r in rec], [([], None)])
        self.assertFalse(any('Hidden tail' in c['text'] for u in route['units'] for c in u.get('cells') or []))  # not composed as shown text

    def test_rc_role_background_is_recorded(self):  # .report .rc { background-color: #f0f0f0 } on the ROW, as in the real R pages
        def edit(b):
            i = b.index(self.CELL8K); j = b.rindex(b'<tr', 0, i); k = b.index(b'>', j)
            return b[:j] + b'<tr class="rc">' + b[k + 1:]
        route, rec = self.styled(edit, b'8-K<span>')
        self.assertTrue(rec and all(any(g[1] == 'rgb(240, 240, 240)' for g in r.get('background') or []) for r in rec), rec)

    def test_superscript_marker_only(self):  # split positive (b): the marker kept by the tag-based lift carrier
        route = self.ok(self.with_sup)
        self.assertIs(route['source_inline'].get('read'), True); self.assertIn('[1]', json.dumps(route['source_inline']))  # the raised run is recorded

    def test_superscript_marker_and_footnote_block(self):  # P1
        self.ok(lambda b: self.with_footnotes(self.with_sup(b)))

    def test_superscript_inside_a_definition_is_refused(self):  # the target tag profile has no sup
        self.assertKept(*self.run_page(edit=lambda b: b.replace(b'<p>', b'<p><sup>[1]</sup>', 1)), 'outside the supported reveal profile')

    def test_fetched_but_not_applied_on_screen(self):
        link = b'<link rel="stylesheet" type="text/css" href="include/report.css">'
        self.assertKept(*self.run_page(edit=lambda b: b.replace(link, link[:-1] + b' media="print">', 1)), 'applied on screen')
        self.assertKept(*self.run_page(edit=lambda b: b.replace(link, link.replace(b'rel="stylesheet"', b'rel="alternate stylesheet" title="x"'), 1)), 'applied on screen')

    def test_no_binding_keeps_todays_outcome(self):
        route, facts = self.run_page(bound=False)
        self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('cannot be read offline', route['error']); self.assertNotIn('renderer_controls', facts)


if __name__ == '__main__':
    unittest.main()
