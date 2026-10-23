"""Hidden link ownership in the typed whole-source reading (v2: scan certainty or the page's native link proof is kept as the ownership boundary; only the shown/hidden filter is purpose-aware). Fixture anchors carry no on* attribute (a declared handler makes the scanner uncertain, so a synthetic page would need a browser verdict); UI controls with handlers are covered by the real public AMG page below. (Root SMART_SOURCE_LINK_OWNERSHIP_20261023T0022). The source reading keeps hidden text in
its units, so a hidden <a href> whose element the scanner proves whole (its own </a> found, not split by a table boundary) has holders there, exactly as
a shown link does in the displayed reading; `edgartools_html.source_links` must not reuse the displayed reading's visibility predicate (`not hidden`,
scan certainty / page proof of what SHOWS) for a reading whose claim is what the element CONTAINS. Containment proofs stay: a split, unclosed or
reopened element never gets an owner; the displayed reading is unchanged (hidden links stay unassociated there); an uncertain scan without a browser
verdict still makes no source reading at all. Expected values come from the standard library's parser and lxml over the SOURCE, never from the adapter."""
import hashlib
import json
import re
import unittest
from pathlib import Path

import lxml.html

from driver.prepare.convert import anchor, html_route
from driver.prepare.convert import edgartools_html as eh

norm = lambda s: re.sub(r'\s+', ' ', (s or '').replace('\xa0', ' ')).strip()
def doc(body): raw = ('<html><head><meta charset="utf-8"></head><body>%s</body></html>' % body).encode(); return raw, hashlib.sha256(raw).hexdigest()
def items(r): return [x for u in r['units'] for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u])]
def site(r, o):  # the unit or table cell a saved owner names
    u = next(x for x in r['units'] if x['id'] == o['unit'])
    return u if 'cell' not in o else next(c for c in u['cells'] if anchor.spans(c.get('anchor'))[0]['byte_start'] == o['cell'])
def anchors_in_source(raw):  # [(byte_start, href, text)] of every <a href> as lxml reads the ORIGINAL, in source order
    t = raw.decode('utf-8'); out = []
    for m in re.finditer(r'<a\b[^>]*\bhref=', t): out.append(len(t[:m.start()].encode()))
    texts = [norm(a.text_content()) for a in lxml.html.fromstring(raw).xpath('//a[@href]')]
    assert len(texts) == len(out), (len(texts), len(out)); return list(zip(out, texts))
def hidden_rec(r, start): return next(l for l in r['source_links'] if l['tag']['byte_start'] == start)

HIDDEN = ('<p>Shown: <a href="#n1">note one</a>.</p>'
          '<div style="display:none"><table id="def1"><tr><td><a href="javascript:void(0);">X</a></td></tr>'
          '<tr><td>Definition: revenue recognized in the period. See <a href="https://standard.invalid/asc/606">ASC 606-10-50</a>.</td>'
          '<td><a href="javascript:void(0);">+ Details</a></td></tr>'
          '<tr><td><table id="nested1"><tr><td>Reference <a href="#n1">one</a> and <a href="#n2">two</a> in one cell</td></tr></table></td></tr></table></div>'
          '<p id="n1">Note one text.</p><p id="n2">Note two text.</p>')


class SourceLinkOwnership(unittest.TestCase):
    def reading(self, body):
        raw, sha = doc(body); shown = eh.convert(raw, 'x.htm', sha); r, why = html_route.source_reading(raw, 'x.htm', sha, shown); return raw, shown, r, why

    def test_hidden_links_are_owned_in_the_source_reading_by_the_cells_holding_their_text(self):  # red before the repair: owners None for every hidden link
        raw, shown, r, why = self.reading(HIDDEN); self.assertIsNotNone(r, why)
        for start, text in anchors_in_source(raw):
            rec = hidden_rec(r, start)
            if not rec.get('hidden'): continue
            self.assertIsNotNone(rec['extent'], (start, text)); self.assertIsNotNone(rec['owners'], (start, text)); self.assertNotIn('unheld', rec)
            self.assertTrue(rec['owners'], (start, text)); held = ' '.join(norm(site(r, o).get('text')) for o in rec['owners'])
            self.assertIn(text, held, (start, text, held))  # the owner's saved text holds the anchor's own text, as the original has it
        hidden = [l for l in r['source_links'] if l.get('hidden')]; self.assertEqual(len(hidden), 5)  # X, ASC 606-10-50, + Details, one, two
        nested = [u['id'] for u in r['units'] if u.get('cell')]  # nested tables name their holder cell (existing: each a table unit naming its holder cell)
        for l in hidden:  # a link in a plain cell has exactly that one owner; a link inside a NESTED table is held by the nested cell and by its holder cell's span (existing _holders semantics, unchanged here)
            if any(o['unit'] in nested for o in l['owners']): self.assertEqual(len(l['owners']), 2, l)
            else: self.assertEqual(len(l['owners']), 1, l)

    def test_substantive_and_control_hidden_links_alike_and_nested_cell_boundaries(self):
        raw, shown, r, why = self.reading(HIDDEN); self.assertIsNotNone(r, why); by_text = {t: hidden_rec(r, s) for s, t in anchors_in_source(raw)}
        self.assertTrue(any(u.get('cell') for u in r['units']))  # the nested table is its own unit in the source reading, naming its holder cell
        one, two = by_text['one'], by_text['two']; self.assertEqual(one['owners'], two['owners'])  # two links in one nested cell: the same owner
        nested_unit = next(u for u in r['units'] if any(norm(c.get('text')).startswith('Reference') for c in u.get('cells') or []))
        self.assertIn(nested_unit['id'], [o['unit'] for o in one['owners']])  # the NESTED table's cell is among the owners (with the holder cell whose span contains it)
        self.assertNotEqual(by_text['X']['owners'], by_text['ASC 606-10-50']['owners'])  # different cells, different owners

    def test_the_displayed_reading_is_unchanged_hidden_links_stay_unassociated(self):
        raw, shown, r, why = self.reading(HIDDEN)
        for l in shown['source_links']:
            if l.get('hidden'): self.assertIsNone(l['owners']); self.assertIsNone(l['extent'])
            else: self.assertTrue(l['owners'])  # the shown link keeps its owner
        self.assertEqual([l['tag'] for l in shown['source_links']], [l['tag'] for l in r['source_links']])  # same records, same order, in both readings

    def test_containment_proofs_still_rule_split_or_unclosed_hidden_links_get_no_owner(self):
        body = ('<div style="display:none"><table><tr><td><a href="#a">split a</td><td>b</a></td></tr></table>'
                '<table><tr><td><a href="#b">unclosed hidden')  # the first anchor is split across cells; the second never closes
        raw, shown, r, why = self.reading(body + '</td></tr></table></div><p id="a">A</p><p id="b">B</p>'); self.assertIsNotNone(r, why)
        for l in r['source_links']:
            self.assertTrue(l.get('hidden')); self.assertIsNone(l['extent'], l); self.assertIsNone(l['owners'], l)  # source mode certifies no malformed containment

    def test_an_uncertain_scan_without_a_verdict_still_makes_no_source_reading(self):
        raw, sha = doc('<link rel="stylesheet" href="sheet.css">' + HIDDEN); shown = eh.convert(raw, 'x.htm', sha); self.assertNotIn('page_visibility', shown)
        r, why = html_route.source_reading(raw, 'x.htm', sha, shown); self.assertIsNone(r); self.assertIn('unproved', why)

    def test_source_order_permutation_owners_follow_the_source(self):
        a = HIDDEN; b = HIDDEN.replace('See <a href="https://standard.invalid/asc/606">ASC 606-10-50</a>.</td><td><a href="javascript:void(0);">+ Details</a></td>',
                                      'See <a href="javascript:void(0);">+ Details</a>.</td><td><a href="https://standard.invalid/asc/606">ASC 606-10-50</a></td>')
        self.assertNotEqual(a, b)
        for body in (a, b):
            raw, shown, r, why = self.reading(body); self.assertIsNotNone(r, why); recs = [l for l in r['source_links'] if l.get('hidden')]
            self.assertEqual([l['tag']['byte_start'] for l in recs], sorted(l['tag']['byte_start'] for l in recs))  # records in source order
            for s, t in anchors_in_source(raw):
                rec = hidden_rec(r, s)
                if rec.get('hidden'): self.assertIn(t, ' '.join(norm(site(r, o).get('text')) for o in rec['owners']), (s, t))

    def test_public_amg_r1_every_whole_hidden_link_is_owned_and_held(self):  # real page, browser verdict from its saved displayed route; design page
        fx = Path(__file__).parent / 'fixtures' / 'public_amg_r1'; raw = (fx / 'AMG_R1.htm').read_bytes(); d = json.loads((fx / 'displayed_page_visibility.json').read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), d['sha256']); r, why = html_route.source_reading(raw, 'AMG_R1.htm', d['sha256'], {'sha256': d['sha256'], 'page_visibility': d['page_visibility']})
        self.assertIsNotNone(r, why); hidden = [l for l in r['source_links'] if l.get('hidden')]; self.assertEqual(len(hidden), 100)
        owned = [l for l in hidden if l['owners']]; self.assertEqual(len(owned), 100, [l['tag'] for l in hidden if not l['owners']][:5])
        texts = dict(anchors_in_source(raw))
        for l in owned:
            self.assertFalse(l.get('unheld')); self.assertIn(texts[l['tag']['byte_start']], ' '.join(norm(site(r, o).get('text')) for o in l['owners']), l['tag'])
        self.assertTrue(all(l.get('certain') is False for l in r['source_links']))  # the visibility uncertainty of the real page is still said on every record

    def test_a_hidden_link_whose_native_proof_is_missing_stays_unowned_while_the_proved_ones_qualify(self):  # negative beside the real positive: uncertain real page
        fx = Path(__file__).parent / 'fixtures' / 'public_amg_r1'; raw = (fx / 'AMG_R1.htm').read_bytes(); d = json.loads((fx / 'displayed_page_visibility.json').read_text())
        pv = json.loads(json.dumps(d['page_visibility'])); proved = list(pv['links']['proved']); hidden_links = [l for l in anchor.Visible(raw, page=pv).links if l['hidden']]
        victim = hidden_links[len(hidden_links) // 2]['start']; self.assertIn(victim, proved); pv['links']['proved'] = [s for s in proved if s != victim]  # only this link's proof removed; hidden spans and all else unchanged
        r, why = html_route.source_reading(raw, 'AMG_R1.htm', d['sha256'], {'sha256': d['sha256'], 'page_visibility': pv}); self.assertIsNotNone(r, why)
        rec = next(l for l in r['source_links'] if l['tag']['byte_start'] == victim); self.assertTrue(rec.get('hidden')); self.assertIs(rec.get('certain'), False)
        self.assertIsNone(rec['extent']); self.assertIsNone(rec['owners'])  # source=True certifies no containment the page did not prove in an uncertain scan
        others = [l for l in r['source_links'] if l.get('hidden') and l['tag']['byte_start'] != victim]; self.assertEqual(len(others), 99); self.assertTrue(all(l['owners'] for l in others))
        texts = dict(anchors_in_source(raw))
        for l in others: self.assertIn(texts[l['tag']['byte_start']], ' '.join(norm(site(r, o).get('text')) for o in l['owners']), l['tag'])
        shown = eh.convert(raw, 'AMG_R1.htm', d['sha256'], vis=anchor.Visible(raw, page=pv)); self.assertTrue(all(l['owners'] is None for l in shown['source_links'] if l.get('hidden')))  # displayed reading: hidden links unowned as before



if __name__ == '__main__': unittest.main()
