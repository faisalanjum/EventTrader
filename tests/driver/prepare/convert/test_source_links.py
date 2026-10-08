"""Every link the source writes is kept as source evidence (Codex HREF_DESIGN_REVIEW / HREF_URL_REVIEW, Fable HREF_DESIGN_v2): one `source_links` record
per <a href> start tag - the href as written (decoded once, untouched), its tag, whether the page shows it - beside the units, which stay as they were.
Its extent (the bytes its own </a> closes) and the units or cells holding its text are given only where the scan proves them; a link the browser's
parser splits, nests, fosters or reopens is left unresolved. A same-document fragment names its source targets the way Chromium finds them (the
written fragment, then one percent-decoding; ids before names; every duplicate), and the unit a target stands in only where the target's own text is
in exactly one; an active <base href> is kept once and every href under it, relative or external, stays as written. Expected values are Chromium's
own readings (fixtures/link_browser_controls.json, recorded by Codex) or read off the source; never the candidate's."""
import copy
import html
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from driver.prepare.convert import anchor, html_route
from driver.prepare.convert import edgartools_html as eh

CASES = json.loads((Path(__file__).parent / 'fixtures' / 'link_browser_controls.json').read_text())['cases']
squash = lambda t: re.sub(r'\s+', '', t or '')


def route(raw): return eh.convert(raw, 'f.htm', anchor.sha256(raw))


def written(raw):
    """The <a href> start tags of a page as the standard library's own HTML parser reads them (no template content, script or comment): [href first
    written, decoded once; the text written from the tag to the next </a>]."""
    out, depth, open_ = [], [0], []
    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'template': depth[0] += 1
            elif tag == 'a' and not depth[0] and any(k == 'href' for k, _ in attrs): out.append([next(v for k, v in attrs if k == 'href') or '', '']); open_.append(out[-1])
        def handle_endtag(self, tag):
            if tag == 'template': depth[0] -= 1
            elif tag == 'a': open_.clear()
        def handle_data(self, data):
            for x in open_: x[1] += data
    P(convert_charrefs=True).feed(raw.decode())
    return out


def text_of(raw, rec):  # the visible text the record's extent holds
    e = rec['extent']; return anchor.Visible(raw).at(e['byte_start'], e['byte_end_exclusive'])


def target_attr(raw, byte):  # the id or name the start tag at this byte writes (decoded once)
    m = re.match(rb'<[A-Za-z]+((?:\s+[^\s=>]+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+))?)*)\s*/?>', raw[byte:])
    attrs = {k.lower(): html.unescape(v.strip('"\'')) for k, v in re.findall(r'([^\s=]+)\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', m.group(1).decode())}
    return attrs.get('id'), attrs.get('name')


class TheBrowsersControls(unittest.TestCase):
    def test_every_written_link_tag_once_with_its_href_as_written(self):  # failed before: no such record
        for name, case in CASES.items():
            raw = case['raw'].encode(); r = route(raw)
            self.assertEqual([x['href'] for x in r['source_links']], [h for h, _ in written(raw)], name)
            if case['links'] is not None: self.assertTrue({l['href'] for l in case['links']} <= {x['href'] for x in r['source_links']}, name)  # the browser's own href strings, exactly

    def test_an_extent_only_where_the_browser_reads_the_tag_as_written(self):
        """Two-sided: a link the browser keeps whole (as many anchors with that href as tags, its text that of the tag's own content) and the page shows
        has its extent, with that text; a link the browser splits, moves or cuts short has none - never a false owner."""
        for name, case in CASES.items():
            if case['links'] is None: continue  # (a target-only record)
            raw = case['raw'].encode(); r = route(raw); vis = anchor.Visible(raw); recs = r['source_links']; src = written(raw)
            for href in {x['href'] for x in recs}:
                mine = [(x, t) for x, (h, t) in zip(recs, src) if x['href'] == href]; dom = [l for l in case['links'] if l['href'] == href]
                for k, (rec, wrote) in enumerate(mine):
                    seen = squash(dom[k].get('shown', dom[k]['text'])) if len(dom) == len(mine) else None
                    if vis.certain and not rec.get('hidden') and seen == squash(wrote):  # the browser reads it as written: its extent, with that text
                        self.assertIsNotNone(rec['extent'], (name, href)); self.assertEqual(squash(text_of(raw, rec)), seen, (name, href))
                    else: self.assertIsNone(rec['extent'], (name, href)); self.assertIsNone(rec['owners'], (name, href))
        for name in ('reopened_a', 'formatting_reopens_link', 'fostered_a'):
            self.assertTrue(all(x['extent'] is None and x['owners'] is None for x in route(CASES[name]['raw'].encode())['source_links']), name)  # split or moved by the parser
        recs = route(CASES['nested_a']['raw'].encode())['source_links']
        self.assertEqual([(x['extent'], x.get('certain')) for x in recs], [(None, False)] * 2)  # an <a> opened inside an open one: the scanner does not follow it, so nothing is certified

    def test_proved_links_name_the_units_or_cells_holding_their_text(self):
        def owners(name):
            raw = CASES[name]['raw'].encode(); r = route(raw); by = {u['id']: u for u in r['units']}
            def text(o):
                u = by[o['unit']]
                return u['text'] if 'cell' not in o else next(c['text'] for c in u['cells'] if c['anchor']['byte_start'] == o['cell'])
            return [[(squash(text(o)) if by[o['unit']]['kind'] != 'image' else 'picture') for o in x['owners']] for x in r['source_links'] if x['owners'] is not None]
        self.assertEqual(owners('prose'), [['Revenue(1)was$25.']])
        self.assertEqual(owners('cell'), [['25(1)']])  # a table cell, named by its own anchor
        self.assertEqual(owners('heading'), [['Revenue']])
        self.assertEqual(owners('two_links_one_unit'), [['NoteandNote.'], ['NoteandNote.']])
        self.assertIn(owners('link_container'), ([['First', 'Second']], [['FirstSecond']]))  # one link around two blocks: whatever units hold them
        self.assertIn(owners('link_across_br'), ([['First', 'Second']], [['FirstSecond']]))  # across a line break: whatever units hold it
        self.assertEqual(owners('image'), [['picture']])

    def test_fragments_find_what_chromium_targets(self):  # the written fragment, then one percent-decoding; ids before names
        for name, case in CASES.items():
            if 'target' not in case: continue
            raw = case['raw'].encode(); r = route(raw); [rec] = r['source_links']; d = rec['destination']
            if 'source_base' in r: self.assertEqual(d, {'kind': 'as_written'}, name); continue  # under a base the document is not proved: kept as written (accepted for an empty base too)
            t = case['target']
            if not isinstance(t, dict): self.assertNotEqual(d.get('status'), 'one', name); continue  # Chromium targets nothing here, or another document
            self.assertEqual((d['kind'], d['status']), ('same_document', 'one'), name)
            self.assertEqual(target_attr(raw, d['targets'][0]), (t['id'] or None, t['name'] or None), name)

    def test_duplicates_collisions_and_empty_or_wide_targets(self):
        d = lambda n: route(CASES[n]['raw'].encode())['source_links'][0]['destination']
        self.assertEqual((d('duplicate_id')['status'], len(d('duplicate_id')['targets']), d('duplicate_id')['owner']), ('several', 2, None))  # both kept, none chosen
        raw = CASES['id_name_collision']['raw'].encode(); x = route(raw)['source_links'][0]['destination']
        self.assertEqual((x['by'], target_attr(raw, x['targets'][0])), ('id', ('n', None)))  # the id before the earlier name
        self.assertEqual((d('empty_target')['status'], d('empty_target')['owner']), ('one', None))  # an empty anchor is a place, not the next paragraph
        self.assertEqual(d('container_target')['owner'], None)  # a target holding several units names none
        self.assertEqual(d('hidden_target')['owner'], None)
        for n in ('empty_id', 'empty_name'): self.assertEqual(d(n), {'kind': 'same_document', 'targets': [], 'status': 'top'}, n)  # a bare # is the top of the page, whatever has an empty id or name
        self.assertEqual(d('encoded_empty_control')['status'], 'none')  # %00 decodes to no empty-id match
        self.assertEqual((d('style_id')['status'], d('style_id')['owner'], d('title_id')['status']), ('one', None, 'one'))  # a raw-text element is a target, with no unit
        r = route(CASES['prose']['raw'].encode()); by = {u['id']: u for u in r['units']}
        self.assertEqual(squash(by[r['source_links'][0]['destination']['owner']['unit']]['text']), '(1)Excludestax.')  # a target whose own text is one unit: that unit

    def test_a_base_is_kept_once_and_a_template_base_is_none(self):
        r = route(CASES['base']['raw'].encode())
        self.assertEqual((r['source_base']['href'], r['source_links'][0]['destination']), ('https://elsewhere.invalid/other.htm', {'kind': 'as_written'}))
        r = route(CASES['hidden_base']['raw'].encode()); self.assertIn('source_base', r)  # hidden, still active
        r = route(CASES['template_base']['raw'].encode()); self.assertNotIn('source_base', r)  # a template's base is inert
        self.assertEqual(r['source_links'][0]['destination']['status'], 'one')

    def test_hidden_and_uncertain_links_are_kept_unassociated(self):
        recs = route(CASES['hidden_origin']['raw'].encode())['source_links']
        self.assertEqual([(x.get('hidden'), x['extent'] is None, x['owners']) for x in recs][0], (True, True, None))  # removed: no reading, no owner
        self.assertTrue(not recs[1].get('hidden') and recs[1]['owners'])
        recs = route(CASES['foreign']['raw'].encode())['source_links']  # SVG content: the scan is not certain
        self.assertTrue(all(x.get('certain') is False and x['owners'] is None for x in recs))


    def test_what_a_link_shows_decides_its_owners_not_its_own_style(self):  # Codex: no visible text is no proof of a hidden link
        page = lambda body: b'<!doctype html><html><head><meta charset="utf-8"></head><body>' + body + b'<p id="n">Target.</p></body></html>'
        r = route(page(b'<p>Before <a href="#n" style="visibility:hidden"><span style="visibility:visible">Shown</span></a> after.</p>')); [x] = r['source_links']
        by = {u['id']: u for u in r['units']}
        self.assertEqual(('hidden' in x, [squash(by[o['unit']]['text']) for o in x['owners']]), (False, ['BeforeShownafter.']))  # its own box invisible, its text shown
        [x] = route(page(b'<p>Before <a href="#n" style="visibility:hidden">Unseen</a> after.</p>'))['source_links']
        self.assertEqual(('hidden' in x, x['owners']), (False, []))  # nothing shown, but not removed
        [x] = route(page(b'<p>Before <a href="#n"></a> after.</p>'))['source_links']
        self.assertEqual(('hidden' in x, x['owners']), (False, []))  # an empty link
        [x] = route(page(b'<div style="display:none"><a href="#n">Gone</a></div><p>Text.</p>'))['source_links']
        self.assertEqual((x.get('hidden'), x['owners']), (True, None))  # removed: no reading at all


class RealShapes(unittest.TestCase):
    """The shapes of the original-backed losses (Codex SOURCE_PROBES, DECK_LINK_GAPS): exhibit index cells, a financial-statement cell pointing to its note."""

    def test_exhibit_cells_keep_their_hrefs(self):
        raw = (b'<table><tr><td><a href="exhibit991-q32024earningsr.htm">Exhibit 99.1</a></td><td><a href="exhibit991-q32024earningsr.htm">Press release issued</a>'
               b' October 23, 2024</td></tr></table>')
        r = route(raw); t = next(u for u in r['units'] if u['kind'] == 'table')
        cells = {c['anchor']['byte_start']: c['text'] for c in t['cells']}
        self.assertEqual([(x['href'], x['destination'], [cells[o['cell']] for o in x['owners']]) for x in r['source_links']],
                         [('exhibit991-q32024earningsr.htm', {'kind': 'as_written'}, ['Exhibit 99.1']), ('exhibit991-q32024earningsr.htm', {'kind': 'as_written'}, ['Press release issued October 23, 2024'])])

    def test_a_statement_cell_points_to_its_note(self):
        raw = (b'<table><tr><td>Net sales (<a href="#n12">Note 12</a>)</td><td>4,000</td></tr></table><p>Other text.</p>'
               b'<p id="n12">Note 12. Reportable Operating Segments</p><p>The segments are as follows.</p>')
        r = route(raw); [x] = r['source_links']; by = {u['id']: u for u in r['units']}; t = next(u for u in r['units'] if u['kind'] == 'table')
        self.assertEqual([next(c['text'] for c in t['cells'] if c['anchor']['byte_start'] == o['cell']) for o in x['owners']], ['Net sales (Note 12)'])
        self.assertEqual((x['destination']['status'], by[x['destination']['owner']['unit']]['text']), ('one', 'Note 12. Reportable Operating Segments'))

    def test_the_units_are_not_touched(self):
        raw = CASES['prose']['raw'].encode(); vis = anchor.Visible(raw)
        units = route(raw)['units']; before = copy.deepcopy(units); eh.source_links(units, vis)
        self.assertEqual(units, before)



class ThroughTheSteps(unittest.TestCase):
    """The selected route (formatting step, screen step in Chrome) keeps the records and the base as the conversion made them: the hash-checked route
    is what a consumer is handed (Codex)."""

    def test_the_selected_route_keeps_them(self):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for name in ('cell', 'base', 'two_links_one_unit'):
                raw = CASES[name]['raw'].encode(); r, facts = html_route.prepare(raw, 'f.htm', anchor.sha256(raw), browser)
                self.assertEqual((r['status'], r['source_links'], r.get('source_base')), ('OK', route(raw)['source_links'], route(raw).get('source_base')), name)
            browser.close()


if __name__ == '__main__':
    unittest.main()
