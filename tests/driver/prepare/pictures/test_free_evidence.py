"""Free OCR as evidence (pictures/free_evidence.py): a free tool's words belong to a block by geometry alone, a spot is read only at its own
occurrence, and both tools reading the same other words is a conflict to show, never a decision. Codex's support review probes, re-expressed
on the runtime functions by Codex (r20 follow-up, the retired evaluation helpers select / spots_grade / verdict are not used); 2026-10-06."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from driver.prepare.pictures import free_evidence as evidence
from driver.prepare.pictures import packets
from tests.driver.prepare.pictures.saved import Saved

CASES = os.path.join(os.path.dirname(__file__), 'cases')
case = lambda name: json.loads(Path(CASES, name).read_text())


class FreeEvidenceTests(unittest.TestCase):
    def test_support_belongs_to_its_occurrence(self):  # a value read only at a later row or year is not this occurrence; full-context controls both orders
        c = case('wrong_occurrence.json'); correct, wrong, later = c['correct'], c['wrong'], c['free_only_later_occurrence']
        for first, second, answer in ((correct, wrong, 'Chandra'), (wrong, correct, 'Sonnet')):
            with self.subTest(first=' '.join(first)):
                self.assertEqual(evidence.support(first, second, later), [(first[2], second[2], None)])
                self.assertEqual(evidence.support(first, second, [correct, correct]), [(first[2], second[2], answer)])

    def test_a_shared_error_outside_the_spot_still_shows_as_a_conflict(self):
        c = case('shared_error.json')
        self.assertEqual(evidence.conflicts(c['chandra'], c['free']), [(4, 5, '99', '20')])

    def test_ownership_by_geometry_alone(self):  # the original PDF probes (y up), converted to picture pixels (y down: 800 - y)
        own = evidence.owner_of([(0, 0, 1000, 500), (0, 520, 1000, 1000)], 600, 800, 10)
        for x, y, expected in ((300, 10, 0), (300, 500, 1), (300, 397, 0), (300, 410, 1)):   # its own block; between two boxes the nearer within a letter height
            with self.subTest(x=x, y=y):
                self.assertEqual(own(x, y), expected)
        self.assertIsNone(evidence.owner_of([(0, 0, 1000, 100)], 600, 800, 10)(300, 500))     # far from every box: outside every block


class SavedFreeEvidence(unittest.TestCase):  # the real shared typo and a visible conflict, through the pinned fixtures (ported 2026-10-07)
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(tmp.cleanup)
        cls.s = Saved(tmp.name)

    def test_the_real_shared_typo_and_a_visible_conflict(self):
        r = self.s.by_name['simon10k_p1_75']
        self.assertEqual(len(r['free']['lines']), 1)                       # the probe reads the page's one free-OCR row
        name, pic, html, _, fr, (son, src) = self.s.inputs(r)
        bl = packets.blocks_of(html)
        free = [evidence.free_tokens(fr[t], bl, fr['w'], fr['h']).get(28, []) for t in ('pp', 'ox')]
        # KNOWN CHANDRA ERROR: the page prints the typo "restaetments"; Chandra (and Sonnet) silently corrected it; both free tools read it
        self.assertIn(('restatements', 'restaetments'), [(x, y) for _, _, x, y in evidence.conflicts(packets.toks(bl[28]['html'], 'html'), free)])
        text, rec = packets.packet(name, pic, html, son, src, free=fr)
        # KNOWN CHANDRA ERROR: printed "indicated", Chandra "indicate"; the conflict is shown, the block's status is unchanged
        self.assertIn('[FREE OCR conflict, unverified: this block has "indicate" where both free tools read "indicated"]', text)
        self.assertEqual(rec['blocks'][26]['status'], 'agree')
        probe = self.s.picture(self.s.by_name['udr_p5_75'])               # a block both readers agree on, with no free evidence: nothing added
        self.assertFalse(packets.packet('probe', probe, '<div data-bbox="0 0 1000 1000" data-label="Text"><p>Revenue 10.</p></div>', '<p>Revenue 10.</p>', 'probe')[1]['blocks'][0]['free_ocr'])


if __name__ == '__main__':
    unittest.main()
