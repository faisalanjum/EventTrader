"""compare._FOLD is filled per character on first use (no import-time scans of every code point). The independent expectation is the former
full table, rebuilt here by its own expression; every code point, the table's own entries, and norm/squash with the unchanged _CF/_WS."""
import re, unicodedata, unittest
from unittest.mock import patch

from driver.prepare import compare

OLD_FOLD = str.maketrans({**{chr(i): ('"' if ('DOUBLE' in unicodedata.name(chr(i), '') or chr(i) == '"') else "'") for i in range(0x110000) if 'QUOTATION MARK' in unicodedata.name(chr(i), '')},
                          **{chr(i): '-' for i in range(0x110000) if unicodedata.category(chr(i)) == 'Pd' or unicodedata.name(chr(i), '') == 'MINUS SIGN'}})
EVERY = ''.join(chr(i) for i in range(0x110000))


class LazyFoldEqualsTheFullScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fold = patch.object(compare, '_FOLD', compare._Fold())
        cls.addClassCleanup(fold.stop)
        fold.start()

    def test_every_code_point_and_the_whole_range_translate_the_same(self):
        self.assertEqual([i for i in range(0x110000) if chr(i).translate(compare._FOLD) != chr(i).translate(OLD_FOLD)], [])
        self.assertEqual(EVERY.translate(compare._FOLD), EVERY.translate(OLD_FOLD))

    def test_the_tables_own_entries_are_the_former_table_once_filled(self):
        EVERY.translate(compare._FOLD)
        self.assertEqual({o: compare._FOLD[o] for o in OLD_FOLD}, OLD_FOLD)  # the former entries exactly, identity-valued ones ('"', '-') included
        self.assertEqual(len(compare._FOLD), 0x110000)
        self.assertEqual([o for o, v in compare._FOLD.items() if o not in OLD_FOLD and v != chr(o)], [])  # every other code point maps to itself

    def test_cf_and_ws_are_unchanged(self):
        cf = ''.join(chr(i) for i in range(0x110000) if unicodedata.category(chr(i)) == 'Cf')
        self.assertEqual(compare._CF, cf); self.assertEqual(compare._WS.pattern, '[\\s' + re.escape(cf) + ']+')

    def test_norm_and_squash_match_for_every_code_point_beside_tildes_spaces_and_letters(self):
        old_norm = lambda s: compare._WS.sub(' ', s.translate(OLD_FOLD).replace('~~', '')).strip()
        old_squash = lambda s: compare._WS.sub('', s.translate(OLD_FOLD).replace('~~', ''))
        for pattern in ('~{}~', '{}~~', '~~{}', ' {} ', 'a{}b', '{}{}', '~{} ~'):
            text = ''.join(pattern.format(c, c) for c in EVERY)
            with self.subTest(pattern=pattern):
                self.assertEqual(compare.norm(text), old_norm(text)); self.assertEqual(compare.squash(text), old_squash(text))
        for c in ('’', '“', '–', '−', '­', '​', '"', "'", '-', '~'):  # single characters, where strip and runs matter
            self.assertEqual((compare.norm(c), compare.squash(c)), (old_norm(c), old_squash(c)))


if __name__ == '__main__':
    unittest.main()
