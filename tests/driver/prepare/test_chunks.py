"""Whole-block splitting, independent of filing type or business content."""
import copy
import json
import unittest
from pathlib import Path

from driver.prepare.chunks import split_blocks
from driver.prepare.reconstruct import readback


class ChunkTests(unittest.TestCase):
    def test_equal_blocks_split_evenly(self):
        blocks = [{"text": str(i)} for i in range(8)]
        self.assertEqual(split_blocks(blocks, 4), [blocks[i:i + 2] for i in range(0, 8, 2)])

    def test_balance_uses_size_not_number_of_blocks(self):
        blocks = [{"text": "x" * n} for n in (1, 1, 1000, 1, 1)]
        self.assertEqual(split_blocks(blocks, 3), [blocks[:2], blocks[2:3], blocks[3:]])

    def test_large_first_block_leaves_remaining_work_balanced(self):
        blocks = [{"text": "x" * n} for n in (1000, 10, 10, 10, 10)]
        self.assertEqual(split_blocks(blocks, 3), [blocks[:1], blocks[1:3], blocks[3:]])

    def test_all_valid_counts_preserve_order_objects_and_content(self):
        blocks = [{"id": i, "text": "\u20ac\n| <tag> \\ \"" * (i + 1)} for i in range(25)]
        before = copy.deepcopy(blocks)
        for count in range(1, len(blocks) + 1):
            with self.subTest(count=count):
                chunks = split_blocks(blocks, count)
                self.assertEqual(len(chunks), count)
                self.assertTrue(all(chunks))
                flat = [block for chunk in chunks for block in chunk]
                self.assertEqual(flat, before)
                self.assertTrue(all(a is b for a, b in zip(flat, blocks)))
        self.assertEqual(blocks, before)

    def test_invalid_counts_fail_and_valid_controls_succeed(self):
        blocks = [{"text": "one"}, {"text": "two"}]
        for count in (0, -1, 3, True, False, 1.5, "2", None):
            with self.subTest(count=count), self.assertRaises(ValueError):
                split_blocks(blocks, count)
        self.assertEqual(split_blocks(blocks, 1), [blocks])
        self.assertEqual(split_blocks(blocks, 2), [[blocks[0]], [blocks[1]]])

    def test_empty_input_cannot_make_a_nonempty_chunk(self):
        with self.assertRaises(ValueError):
            split_blocks([], 1)
        self.assertEqual(split_blocks([{}], 1), [[{}]])

    def test_complete_tables_lists_and_captions_are_indivisible(self):
        table = {"record": {"id": "t0", "kind": "table"}, "captions": ["caption"],
                 "cells": [{"record": {"r": 0, "c": 0, "rs": 2, "cs": 3, "text": ""},
                            "children": [{"record": {"id": "t1", "kind": "table"}, "cells": []}]}]}
        listing = {"kind": "list", "items": [{"members": [table]}]}
        blocks = [{"text": "before"}, listing, {"text": "after"}]
        self.assertEqual(split_blocks(blocks, 3), [[blocks[0]], [listing], [blocks[2]]])

    def test_existing_readback_fixtures_keep_their_whole_blocks(self):
        fixtures = Path(__file__).parent / "reconstruct/fixtures"
        for name in ("h1_two_levels", "h2_repeated_siblings", "h3_child_caption",
                     "h4_linker_document", "amg_image_before_holder"):
            reading = readback(json.loads((fixtures / (name + ".json")).read_text())["route"])
            before = copy.deepcopy(reading)
            blocks = reading["sequence"]
            for count in sorted({1, min(4, len(blocks)), len(blocks)}):
                with self.subTest(fixture=name, count=count):
                    chunks = split_blocks(blocks, count)
                    self.assertEqual(len(chunks), count)
                    self.assertTrue(all(chunks))
                    self.assertEqual([b for c in chunks for b in c], before["sequence"])
                    self.assertEqual(reading, before)


if __name__ == "__main__":
    unittest.main()
