"""Table choice (pictures/table_choice.py) on saved readings: a disputed table is resolved only by the picture's word positions, found
exactly, and never in favour of a damaged reading. The five saved picks (Codex real336 review, task 1, and the development review C2)
and the 546 damage cases frozen once from the retired generator (TABLE_DAMAGES_FROZEN.json: seed 7, 8 picks; each case names the
relationship it breaks). Expectations by construction, not by any runtime: a damaged reading is never chosen; the six harmless controls
keep their choice; each pick keeps its choice and passes decide() exactly the frozen arguments. Ported 2026-10-07 from prepare_work
reader_packets/selftest.py (pick) and table_choice_test.py, through the pinned fixtures only."""
import collections
import hashlib
import json
import tempfile
import unittest

from driver.prepare.pictures import packets as p, table_choice as T
from tests.driver.prepare.pictures.saved import Saved

DAMAGES = 'real575_20261005/fixture_manifest_20261007/TABLE_DAMAGES_FROZEN.json'
plain = lambda x: json.loads(json.dumps(x))


class TableChoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(tmp.cleanup)
        cls.s = Saved(tmp.name)

    def reading(self, name):  # Chandra's HTML, the saved second reading's text and the free-OCR row of one indexed picture
        r = self.s.by_name[name]; _, _, html, _, free, (text, _) = self.s.inputs(r)
        self.assertIsNotNone(html); self.assertIsNotNone(text); self.assertIsNotNone(free)
        return html, text, free

    def pick(self, n, i, edit=lambda r: r):  # the rule's choice for Chandra's block i of saved picture n; edit damages the second reading's table
        raw, son, rec = self.reading(n)
        bl = p.blocks_of(raw); st, el = p.statuses(bl, son); el = list(el); el[st[i][4]] = dict(el[st[i][4]], raw=edit(el[st[i][4]]['raw']))
        return T.choose(raw, bl, i, st, el, rec)[0]

    def test_the_five_saved_picks(self):
        n = '228_bfe8899ba5faff28.jpg'
        self.assertEqual(self.pick(n, 6), 'S')                                    # Codex's exact-match control
        self.assertIsNone(self.pick(n, 10))       # Chandra's bare table fits exactly but lacks the second reading's "Q3 2026 / Q3 2025" headings
        self.assertIsNone(self.pick(n, 6, lambda r: r.replace('Operating cash flows', 'Operating cash', 1)))   # a dropped word
        self.assertNotEqual(self.pick(n, 6, lambda r: r.replace('Operating cash flows', 'Not Operating cash flows', 1)), 'S')   # a negation
        self.assertIsNone(self.pick('236_ff1b1a20eb0fb433.jpg', 6))               # cells found only approximately

    def test_frozen_damages_are_never_chosen(self):
        fz = self.s.json(DAMAGES); args = {}
        self.assertEqual((len(fz['picks']), len(fz['cases']), fz['no_ops'], fz['malformed']), (8, 552, [], []))
        for k in fz['picks']:
            with self.subTest(pick=k['page']):
                raw, son, rec = self.reading(k['page'])
                self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), k['chandra_html_sha256'])
                bl = p.blocks_of(raw); st, el = p.statuses(bl, son); got, decide = [], T.decide
                T.decide = lambda *a: got.append(a) or decide(*a)
                try: who = T.choose(raw, bl, k['block'], st, el, rec)[0]
                finally: T.decide = decide
                C, S, bc, bs, page, frec, near = got[0]
                now = plain(dict(C=C, S=S, bc=bc, bs=bs, page_html_sha256=hashlib.sha256(page.encode()).hexdigest(),
                                 rec_sha256=hashlib.sha256(json.dumps(frec, sort_keys=True).encode()).hexdigest(), near=list(near)))
                self.assertEqual(who, k['chosen']); self.assertEqual(now, k['decide_args'])   # the undamaged control and its exact arguments
                args[k['pick']] = (C, S, bc, bs, page, frec, near, who)
        per_kind = collections.Counter()
        for c in fz['cases']:
            C, S, bc, bs, page, frec, near, who = args[c['pick']]
            self.assertEqual(c['damaged_side'], who)
            res = T.decide(c['table'], S, bc, bs, page, frec, near)[0] if who == 'C' else T.decide(C, c['table'], bc, bs, page, frec, near)[0]
            with self.subTest(case=c['id'], kind=c['kind'], breaks=c['breaks']):
                if c['kind'].startswith('HARMLESS'):
                    self.assertEqual(res, who)                                  # same meaning: the choice is kept
                else:
                    self.assertNotEqual(res, who)                               # the damaged reading is never chosen
            per_kind[c['kind']] += 1
        self.assertEqual(dict(per_kind), {'a_colspan': 15, 'b_swap_headings': 85, 'c_move_into_empty': 12, 'd_swap_values_in_row': 89,
                                          'f_swap_values_in_column': 96, 'g_swap_row_labels': 96, 'omitted row': 8, 'negation added': 75,
                                          'last word dropped': 70, 'HARMLESS: spaces in number cells removed': 6})


if __name__ == '__main__':
    unittest.main()
