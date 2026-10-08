"""Reader packets (pictures/packets.py): block statuses come from the checker, uncertainty survives, tables pair only by content at their own
place, the second reading reaches the packet, declared math decodes plain symbols only, and a visual region's free-OCR boxes are evidence kept
whole. Ported from prepare_work reader_packets/selftest.py (Codex's block, r2, r3, r4, r6 and real336 review probes) on 2026-10-06; the probes
that need saved readings (Simon p28 values, the real fcpt2 slide) read the pinned fixtures (SavedProbes, 2026-10-07)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from driver.prepare.pictures import packets as p
from tests.driver.prepare.pictures.saved import Saved

CASES = os.path.join(os.path.dirname(__file__), 'cases')
block = lambda text, label='Text': dict(box=(0, 0, 1000, 1000), label=label, html=text)
box = lambda x, label='Text', extra='': f'<div data-bbox="0 0 1000 1000" data-label="{label}"{extra}>{x}</div>'
judge = lambda chandra, sonnet: [v[0] for v in p.statuses(p.blocks_of(chandra), sonnet)[0].values()]
TABLE = '<table><tr><th>Metric</th><th>2025</th></tr><tr><td>Revenue</td><td>10</td></tr></table>'
t = lambda v: f'<table><tr><th>Metric</th><th>Value</th></tr><tr><td>Revenue</td><td>{v}</td></tr></table>'
chandra = lambda *parts: ''.join(box(x, 'Table') if x.startswith('<table') else box(f'<h2>{x}</h2>', 'Section-Header') for x in parts)
sonnet = lambda *parts: ''.join(x if x.startswith('<table') else f'<h2>{x}</h2>' for x in parts)


class PacketTests(unittest.TestCase):
    def setUp(self):  # packet() reads only the picture's size
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup)
        self.picture = os.path.join(d.name, 'page.png'); Image.new('RGB', (638, 826), 'white').save(self.picture)

    def test_block_status_is_the_checkers(self):  # Codex block review
        cases = [('valid paragraph', '<p>Revenue $10.</p>', '<p>Revenue $10.</p>', 'agree'),
                 ('changed value', '<p>Revenue $10.</p>', '<p>Revenue $11.</p>', 'unresolved'),
                 ('literal marker', '<p>Revenue* $10.</p>', '<p>Revenue $10.</p>', 'unresolved'),
                 ('shared unread placeholder', '<p>Revenue [?].</p>', '<p>Revenue [?].</p>', 'unresolved'),
                 ('uncertain original reading', '<p data-uncertain>Revenue $10.</p>', '<p>Revenue $10.</p>', 'unresolved'),
                 ('uncertain second reading', '<p>Revenue $10.</p>', '<p data-uncertain>Revenue $10.</p>', 'unresolved'),
                 ('uncertain container around the second reading', '<p>Revenue $10.</p>', '<div data-uncertain><p>Revenue $10.</p></div>', 'unresolved'),
                 ('empty readings', '<p></p>', '<p></p>', 'unresolved'),
                 ('unsupported input', '<p><input type=text value=10>Revenue</p>', '<p>Revenue</p>', 'unresolved'),
                 ('plain lines of one paragraph', '<p>Revenue rose 10 percent</p>', 'Revenue rose\n10 percent', 'agree')]
        for name, a, b, want in cases:
            with self.subTest(name=name):
                self.assertEqual(p.statuses([block(a)], b)[0][0][0], want)

    def test_context_is_its_own_block(self):  # block agreement: the table agrees; its differing context is its own unresolved block
        bs = [block('<p>USD</p>', 'Section-Header'), block('<p>2025</p>'), block('<p>Operating results</p>', 'Section-Header'), block(TABLE, 'Table'), block('<p>Note 1: unaudited.</p>')]
        st = p.statuses(bs, f'<p>EUR</p><p>2025</p><p>Operating results</p>{TABLE}<p>Note 1: unaudited.</p>')[0]
        self.assertEqual((st[0][0], st[3][0]), ('unresolved', 'agree'))

    def test_second_reading_reaches_the_packet(self):
        extra = '<table><tr><th>Metric</th><th>2025</th></tr><tr><td>Profit</td><td>4567</td></tr></table>'
        text, _ = p.packet('probe', self.picture, box('<p>Revenue 10.</p>'), '<p>Revenue 10.</p>' + extra, 'probe')
        self.assertIn('<td>4567</td>', text); self.assertNotIn(p.TAB, text)          # a second-reader-only table arrives as its own raw table
        text, rec = p.packet('probe', self.picture, box('<p>Revenue 10.</p>') + '<p>Debt 9876.</p>', None, None)
        self.assertIn('9876', text); self.assertEqual(rec['blocks'][1]['label'], 'Unlabelled')   # text outside Chandra's blocks is a block of its own

    def test_uncertainty_survives_the_input_path(self):  # Codex r2 C1, with certain controls
        for name, a, b, want in (('block uncertain', box('<p>Revenue 10.</p>', extra=' data-uncertain'), '<p>Revenue 10.</p>', ['unresolved']),
                                 ('container uncertain', '<section data-uncertain>' + box('<p>Revenue 10.</p>') + '</section>', '<p>Revenue 10.</p>', ['unresolved']),
                                 ('unlabelled block inherits it', '<section data-uncertain><p>Revenue 10.</p></section>', '<p>Revenue 10.</p>', ['unresolved']),
                                 ('certain control', box('<p>Revenue 10.</p>'), '<p>Revenue 10.</p>', ['agree']),
                                 ('certain table control', box(TABLE, 'Table'), TABLE, ['agree'])):
            with self.subTest(name=name):
                self.assertEqual(judge(a, b), want)

    def test_tables_pair_by_content_at_their_own_place(self):  # Codex r2 C2
        self.assertEqual(judge(chandra('2024', t(10), '2025', t(20)), sonnet('2024', t(20), '2025', t(10))), ['agree', 'unresolved', 'agree', 'unresolved'])   # swapped under unchanged years
        text, _ = p.packet('swap', self.picture, chandra('2024', t(10), '2025', t(20)), sonnet('2024', t(20), '2025', t(10)), 'probe')
        first = text[text.index('<h2>2024</h2>'):text.index('<h2>2025</h2>')]                                 # under 2024: Chandra 10, Sonnet 20, flagged
        self.assertIn('Chandra "10" / Sonnet "20"', first); self.assertIn('ALTERNATIVE', first); self.assertIn('<td>20</td>', first)
        self.assertEqual(judge(chandra('A', t(10), 'B', t(10)), sonnet('A', t(10), 'B', t(10))), ['agree'] * 4)                  # repeated identical tables, different headings
        self.assertEqual(judge(chandra('A', t(10), 'B', t(20)), sonnet('A', t(10), 'B')), ['agree', 'agree', 'agree', 'unresolved'])   # a table Sonnet lacks
        text, _ = p.packet('extra', self.picture, chandra('A', t(10)), sonnet('A', t(10), 'B', t(30)), 'probe')
        self.assertIn('ONE READER ONLY', text); self.assertIn('<td>30</td>', text); self.assertEqual(text.count('[AGREE'), 2)          # a table only Sonnet has
        self.assertEqual(judge(chandra('A', t(10), 'B', t(20)), sonnet('A', t(10), 'B', t(20))), ['agree'] * 4)                  # same order, valid
        self.assertEqual(judge(chandra('Operating results 2025', t(10)), 'Operating results\n2025' + t(10)), ['agree', 'agree'])   # a heading wrapped differently
        self.assertEqual(judge(chandra(t(10), t(20)), sonnet(t(20), t(10))), ['unresolved'] * 2)                                 # content pairs that cross: unproved
        self.assertEqual(judge(chandra(t(10), t(10)), sonnet(t(10), t(10))), ['unresolved'] * 2)                                 # tied candidates: never chosen arbitrarily

    def test_direct_text_in_containers(self):  # Codex r3: 24 container cases
        cases = json.loads(Path(CASES, 'containers_codex_r3.json').read_text())
        self.assertEqual(len(cases), 24)
        for c in cases:
            with self.subTest(name=c['name']):
                self.assertEqual(judge(c['chandra'], c['sonnet']), c['expected'])

    def test_declared_math_decodes_plain_symbols_only(self):  # Codex real336 review: everything else stays exactly as written
        for raw, want in (('<math>25.5 \\pm 6.0</math>', '25.5 ±6.0'), ('<math>8 3/8\\%</math>', '8 3/8%'), ('<math>1\\% 2\\%</math>', '1% 2%'),
                          ('<math>1} -9</math>', None), ('<math>1\\pm2} -9</math>', None),                      # spacing kept, malformed math
                          ('<math>8\\frac{3}{8}\\%</math>', None), ('<math>x^{2}</math>', None), ('<math>\\unknown 5</math>', None),   # fraction, group, unknown
                          ('<p>\\pm outside math</p>', None)):                                                  # prose: kept
            with self.subTest(raw=raw):
                self.assertEqual(p.decode_math(raw), want or raw)
        self.assertEqual(judge(box('<p>Age (mean, <math>25.5 \\pm 6.0</math>)</p>'), '<p>Age (mean, 25.5±6.0)</p>'), ['agree'])      # notation, not a fact
        self.assertEqual(judge(box('<p>Age (mean, <math>25.5 \\pm 6.0</math>)</p>'), '<p>Age (mean, 25.5±6.9)</p>'), ['unresolved'])  # control

    def test_visual_region_evidence_is_kept_whole(self):  # Codex r3: nothing is selected by a reader
        def visual(primary, pp, ox=None):
            free = dict(w=1000, h=1000, pp=[dict(t=pp, box=[10, 10, 990, 35])], ox=[dict(t=ox or pp, box=[10, 10, 990, 35])])
            return p.free_notes([dict(label='Figure', box=(0, 0, 1000, 1000), html='<p>' + primary + '</p>')], {0: ('visual', [], [], [], None)}, [], free)[0]
        for primary, pp in (('Revenue 10', 'Revenue 10'), ('Revenue is guaranteed', 'Revenue is not guaranteed'), ('Revenue $10', 'Revenue $10 million'),
                            ('Income 10%', 'Income -10%'), ('~17,000 U.S. patients', '~17,000 U.S. cGVHD patients')):
            with self.subTest(primary=primary, pp=pp):              # the whole box, as read: negation, scale, sign, qualifier kept
                v = visual(primary, pp); self.assertEqual((v['pp'], v['ox_other']), ([pp], []))
        v = visual('A 10 B 20', 'A 10 B 20', 'A 20 B 10'); self.assertEqual((v['pp'], v['ox_other']), (['A 10 B 20'], ['A 20 B 10']))   # both readings of a swap
        v = visual('', '8 8 8'); self.assertEqual((v['pp'], v['matching_words']), (['8 8 8'], 0))                                     # free-only text

    def test_onnxtr_alternative_whenever_its_words_differ(self):  # Codex r4: a deletion or nothing too
        w = lambda s: [dict(t=s, box=[10, 10, 990, 35])] if s else []
        for pp, ox in (('Revenue not 10', 'Revenue not 10'), ('Revenue not 10', 'Revenue 10'), ('Revenue not 10', ''), ('', 'Revenue 10'),
                       ('A 10 B 20', 'A 20 B 10'), ('Revenue $10', 'Revenue $ 10')):
            with self.subTest(pp=pp, ox=ox):
                v = p.free_notes([dict(label='Figure', box=(0, 0, 1000, 1000), html='<p>Revenue 10</p>')], {0: ('visual', [], [], [], None)}, [], dict(w=1000, h=1000, pp=w(pp), ox=w(ox)))[0]
                d = p.toks(pp, 'text') != p.toks(ox, 'text')
                self.assertEqual((v['ox_differs'], v['ox_other']), (d, [ox] if ox and d else []))

    def test_single_reader_said_plainly(self):  # Codex r6: never "unresolved" against nothing (every real picture's single-reader packet: test_replay)
        txt, _ = p.packet('single', self.picture, box('<p>Revenue 10.</p>') + box(TABLE, 'Table'), None, None)
        self.assertIn('[CHANDRA ONLY', txt); self.assertIn('read by Chandra only', txt)
        self.assertNotIn('[UNRESOLVED', txt); self.assertNotIn('Sonnet (nothing)', txt)


    def test_every_stored_free_ocr_alternative_is_printed_whole(self):  # Codex, Oct 8 (PACKET_EVIDENCE_WORK_ORDER): no display cap or cut hides one
        long = 'Investment income, before expense, for the quarter ended March 31, 2025, in millions of dollars'   # > 80 characters, the difference at the end
        cases = {'more than four, the material one last': dict(conflicts=[('$', '')] * 4 + [('660', '650')], support=[]),
                 'difference past 80 characters': dict(conflicts=[(long + ' 660', long + ' 650')], support=[]),
                 'empty sides': dict(conflicts=[('As of or for the', ''), ('', 'Note 3')], support=[]),
                 'normal short control': dict(conflicts=[('Dycorn', 'Dycom')], support=[]),
                 'two readers, supports past four': dict(conflicts=[], support=[('$', '', 'Chandra')] * 4 + [('660', '650', 'Sonnet')])}
        q = lambda x: f'"{x}"' if x else '(nothing)'
        for name, ev in cases.items():
            with self.subTest(name):
                other = '<p>Ordinary context.</p>' if ev['support'] else None
                with patch.object(p, 'free_notes', return_value={0: ev}):
                    txt, rec = p.packet('evidence', self.picture, box('<p>Ordinary context.</p>'), other, 'saved:other' if other else None, free={'saved': True})
                self.assertEqual(rec['blocks'][0]['free_ocr'], ev)                          # the stored evidence, unchanged
                self.assertIn('<p>Ordinary context.</p>', txt)                               # the reading itself, as written
                want = ([f'[FREE OCR conflict, unverified: this block has {q(c)} where both free tools read {q(o)}]' for c, o in ev['conflicts']]
                        + [f"[FREE OCR support, unverified: at Chandra {q(c)} / Sonnet {q(o)} both free tools read {w}'s version]" for c, o, w in ev['support']])
                self.assertEqual([x for x in txt.split('\n') if x.startswith('[FREE OCR')], want)   # every item, in order, whole, unverified; no "+N more"

class SavedProbes(unittest.TestCase):  # the probes on saved readings, through the pinned fixtures (ported 2026-10-07)
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(tmp.cleanup)
        cls.s = Saved(tmp.name)

    def test_simon_p28_values_the_second_reading_holds(self):  # KNOWN CHANDRA ERROR (Codex): Chandra wrote other values; Sonnet's are printed
        name, pic, html, _, _, (son, src) = self.s.inputs(self.s.by_name['simon10k_p28_75'])
        text, _ = p.packet(name, pic, html, son, src)
        for v in ('2,121,975', '1,450,887', '476,600', '608,739', '763,262', '1,263,516', '926,223', '1,169,321'):
            with self.subTest(v):
                self.assertNotIn(v, html)                                  # Chandra alone lacks it: the error stays explicit
                self.assertIn(v, son); self.assertIn(v, text)              # the optional second reading carries it to the packet

    def test_the_real_fcpt2_slide_pairs_each_table_with_its_own(self):
        _, _, html, _, _, (son, _) = self.s.inputs(self.s.by_name['fcpt2_s8'])
        st = p.statuses(p.blocks_of(html), son)
        self.assertIn('Net debt to Adjusted EBITDA', st[1][st[0][5][4]]['raw'])
        self.assertIn('Common dividend', st[1][st[0][4][4]]['raw'])


if __name__ == '__main__':
    unittest.main()
