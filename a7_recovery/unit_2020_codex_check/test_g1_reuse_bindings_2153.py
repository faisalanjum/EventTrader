"""Freeze the implied reply binding over the complete approved population."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2152_g1_reuse'))
import g1_reuse_inputs_2152 as SELECT


class ActualBindings(unittest.TestCase):
    def test_every_carried_reply_has_exactly_the_same_parser_binding(self):
        path = Path(__file__).with_name('G1_REUSE_VALIDATION_INPUT_2153.json')
        approved = G._read(str(path))
        selected = SELECT.derive(approved['report'], approved['report_sha256'])
        compared = []
        for new, old in selected['carry_batches'].items():
            self.assertEqual(G.event_binding(selected['original_candidate'], old),
                             G.event_binding(selected['current_candidate'], new), new)
            compared.append(new)
        self.assertEqual(set(compared) | set(selected['changed_batches']),
                         {r['batch_id'] for r in selected['current_candidate']['batch_rows']})
        self.assertTrue(set(selected['gold_moved_batches']) <= set(compared))


if __name__ == '__main__':
    unittest.main(verbosity=2)
