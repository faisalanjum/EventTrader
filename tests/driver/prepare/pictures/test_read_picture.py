"""One picture through read_picture (pictures/__init__.py): Sonnet is off by default and never called; enabled, it is asked only for a flagged
picture; the one status line says missing / incomplete or uncertain / possible skipped text / unconfirmed text and the reader state, from the
existing flags only. Ported from Codex's r20 follow-up (enabled but bypassed is separate from disabled) and the owner's status-line choice
(option B, 2026-10-06; modes.py's line checks)."""
import os
import tempfile
import unittest

from PIL import Image

from driver.prepare.pictures import read_picture, status

HTML = '<div data-bbox="0 0 1000 1000" data-label="Text"><p>Revenue 10.</p></div>'
WORD = {'t': 'Revenue 10.', 'box': [20, 20, 980, 80]}
FREE = {'w': 1000, 'h': 100, 'pp': [WORD], 'ox': [WORD]}
LIMIT = 12384


class ReadPictureTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup)
        self.picture = os.path.join(d.name, 'control.png'); Image.new('RGB', (1000, 100), 'white').save(self.picture); self.calls = []

    def second(self, picture):
        self.calls.append(picture); return '<p>SECOND_READER_SENTINEL</p>', 'saved-second-reading'

    def test_off_and_enabled_but_not_flagged_never_call(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                asked, flags, text, record = read_picture('control', self.picture, HTML, 50, FREE, LIMIT, enabled, self.second)
                self.assertEqual((asked, flags, self.calls), (False, [], []))
                self.assertNotIn('SECOND_READER_SENTINEL', text)
                self.assertEqual(record['sonnet'], 'on' if enabled else 'off')

    def test_off_never_calls_even_when_flagged(self):
        asked, flags, text, record = read_picture('control', self.picture, None, None, FREE, LIMIT, False, self.second)
        self.assertEqual((asked, flags, self.calls, record['sonnet']), (False, ['no reading'], [], 'off'))

    def test_enabled_and_flagged_asks_once(self):  # the positive control: a missing primary reading
        asked, _, text, _ = read_picture('control', self.picture, None, None, FREE, LIMIT, True, self.second)
        self.assertEqual((asked, self.calls), (True, [self.picture])); self.assertIn('SECOND_READER_SENTINEL', text)

    def test_enabled_needs_a_second_reader(self):
        with self.assertRaises(ValueError):
            read_picture('control', self.picture, HTML, 50, FREE, LIMIT, True, None)

    def test_the_status_line_is_the_one_text_addition(self):
        asked, flags, text, record = read_picture('control', self.picture, HTML, 50, FREE, LIMIT)
        lines = text.split('\n')
        self.assertEqual(lines[1], record['extraction_status']); self.assertTrue(lines[1].startswith('[EXTRACTION STATUS: '))
        self.assertEqual((record['flags'], record['format']), (flags, 'picture packet 2: extraction status line'))

    def test_status_wording_from_existing_flags_only(self):
        cases = [
            (dict(flags=[], enable_sonnet=False, asked=False, second_text=None, generated_tokens=10), '[EXTRACTION STATUS: single reader (Chandra; Sonnet off), unverified]'),
            (dict(flags=[], enable_sonnet=True, asked=False, second_text=None, generated_tokens=10), '[EXTRACTION STATUS: single reader (Chandra; Sonnet on, not asked), unverified]'),
            (dict(flags=['table'], enable_sonnet=True, asked=True, second_text=None, generated_tokens=10), '[EXTRACTION STATUS: single reader (Chandra; Sonnet on, no usable second reading), unverified]'),
            (dict(flags=['table'], enable_sonnet=True, asked=True, second_text='<p>x</p>', generated_tokens=10), '[EXTRACTION STATUS: two readers (Chandra + Sonnet), compared per block]'),
            (dict(flags=['no reading'], enable_sonnet=False, asked=False, second_text=None, generated_tokens=None), '[EXTRACTION STATUS: MISSING: Chandra wrote no usable reading; look at the picture; no reader text (Sonnet off)]'),
            (dict(flags=['no reading'], enable_sonnet=True, asked=True, second_text='<p>x</p>', generated_tokens=None), '[EXTRACTION STATUS: MISSING: Chandra wrote no usable reading; look at the picture; single reader (Sonnet; Chandra missing), unverified]'),
            (dict(flags=['table', 'cut off', 'chart text'], enable_sonnet=False, asked=False, second_text=None, generated_tokens=LIMIT), '[EXTRACTION STATUS: INCOMPLETE: Chandra stopped at its output limit; single reader (Chandra; Sonnet off), unverified]'),
            (dict(flags=['cut off'], enable_sonnet=False, asked=False, second_text=None, generated_tokens=LIMIT - 1), '[EXTRACTION STATUS: INCOMPLETE OR UNCERTAIN: Chandra marked text unreadable or uncertain; single reader (Chandra; Sonnet off), unverified]'),
            (dict(flags=['missed', 'no support'], enable_sonnet=False, asked=False, second_text=None, generated_tokens=10), "[EXTRACTION STATUS: possible skipped text: both free OCR tools read text outside Chandra's blocks; unconfirmed text: a Chandra block that no free OCR tool reads at its place; single reader (Chandra; Sonnet off), unverified]"),
        ]
        for kw, want in cases:  # table and chart text stay in the record only: the packet already shows them
            with self.subTest(flags=kw['flags'], sonnet=kw['enable_sonnet']):
                self.assertEqual(status(limit=LIMIT, **kw), want)


if __name__ == '__main__':
    unittest.main()
