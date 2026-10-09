"""A block's place is its reader's box only when that box can be placed (Codex/Root, Oct 9, ocr_bbox_geometry_20261009, v3): four integers on
the reader's 0-1000 scale, ordered (x0 < x1, y0 < y1). A data-bbox div whose box cannot be placed - malformed, reversed, zero-area or beyond the
scale - keeps its text and declared label, its region is said to be unknown (never the whole picture, never pixels), and no free OCR word can
belong to it, so it is never counted as supported. A div with NO data-bbox is read as before (a wrapper: its content stands as 'Unlabelled'
elements), now also of unknown region; its declared label is kept only in the raw reading - label preservation is not claimed there. Wrappers,
labelled or not, keep the placed blocks inside them. A legitimate full-picture box stays a place. Through the public read_picture path; the
optional mode answers from a saved reading (no live second reader)."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from driver.prepare import pictures
from driver.prepare.pictures import readers

W, H = 1000, 500
TRUE_B = '0 840 1000 940'                                              # where the free tools read block B's words (y 420-470 px)
words = lambda text, y0, y1: [{'t': t, 'box': [10 + 120 * k, y0, 110 + 120 * k, y1]} for k, t in enumerate(text.split())]
FREE = {'file': 'probe.png', 'w': W, 'h': H, 'pp': words('Revenue rose sharply', 40, 80) + words('Net income grew', 430, 460),
        'ox': words('Revenue rose sharply', 40, 80) + words('Net income grew', 430, 460), 'pp_secs': 0, 'ox_secs': 0}
INVALID = {'three values': '0 840 1000', 'a decimal': '0.5 840 1000 940', 'a negative': '-5 840 1000 940', 'a double space': '0  840 1000 940',
           'letters': 'a b c d', 'reversed': '1000 940 0 840', 'zero width': '500 840 500 940', 'zero height': '0 840 1000 840',
           'beyond the scale by one': '0 840 1000 1001', 'beyond the scale': '0 400 1200 1500'}   # present, but no place


def reading(b_box, b_label='Text', b_body='<p>Net income grew</p>'):
    b = f'<div data-label="{b_label}">' if b_box is None else f'<div data-bbox="{b_box}" data-label="{b_label}">'
    return '<div data-bbox="0 0 1000 300" data-label="Text"><p>Revenue rose sharply</p></div>' + b + b_body + '</div>'


class BlockGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(tmp.cleanup)
        cls.picture = str(Path(tmp.name, 'probe.png')); Image.new('RGB', (W, H), 'white').save(cls.picture)

    def read(self, html, **kw):
        return pictures.read_picture('probe', self.picture, html, 100, FREE, readers.MAX_TOKENS, **kw)

    def heads(self, text):
        return [l for l in text.split('\n') if l.startswith('[CHANDRA ONLY') or l.startswith('[UNRESOLVED') or l.startswith('[AGREE')]

    def test_an_unplaceable_box_is_an_unknown_place_with_its_label_and_text(self):
        for why, box in INVALID.items():
            with self.subTest(box=why):
                _, flags, text, rec = self.read(reading(box))
                self.assertEqual(self.heads(text)[1], '[CHANDRA ONLY Text | region unknown]')
                self.assertIn('Net income grew', text)
                self.assertEqual((rec['blocks'][1]['label'], rec['blocks'][1]['box']), ('Text', None))
                self.assertNotIn('whole picture', text)

    def test_a_missing_box_is_read_as_before_and_its_place_is_unknown(self):  # the content of a box-less div stands as an 'Unlabelled' element
        _, flags, text, rec = self.read(reading(None))
        self.assertEqual(self.heads(text)[1], '[CHANDRA ONLY Unlabelled | region unknown]')
        self.assertIn('Net income grew', text)
        self.assertEqual((rec['blocks'][1]['label'], rec['blocks'][1]['box']), ('Unlabelled', None))
        self.assertNotIn('whole picture', text)

    def test_an_unknown_place_never_takes_free_words_as_support(self):  # the inflated or reversed box must not own the words the free tools read
        for why, box in dict(INVALID, missing=None).items():
            with self.subTest(box=why):
                _, flags, _, rec = self.read(reading(box))
                self.assertIn('no support', flags)                    # B's words belong to no block: B is unsupported, never supported by its box
                self.assertIn('missed', flags)                        # and the free tools' words for it stand outside every placed block

    def test_placeable_boxes_stay_places(self):  # controls: the true box, the full picture and the scale's own edges
        for box, region in ((TRUE_B, '0,420-1000,470 px'), ('0 0 1000 1000', '0,0-1000,500 px'), ('0 999 1 1000', '0,499-1,500 px')):
            with self.subTest(box=box):
                _, flags, text, rec = self.read(reading(box))
                self.assertEqual(self.heads(text)[1], f'[CHANDRA ONLY Text | region {region}]')
                self.assertEqual(rec['blocks'][1]['box'], tuple(map(int, box.split())))
        self.assertNotIn('no support', self.read(reading(TRUE_B))[1])

    def test_the_optional_mode_with_a_saved_answer_keeps_an_unknown_table(self):  # no live second reader: the saved answer is handed in
        table = '<table><tr><td>Net income</td><td>42</td></tr></table>'
        saved = ('<p>Revenue rose sharply</p><table><tr><td>Net income</td><td>24</td></tr></table>', 'saved:probe')
        for why, box in (('reversed', '1000 940 0 840'), ('missing', None), ('placeable', TRUE_B)):
            with self.subTest(box=why):
                asked, flags, text, rec = self.read(reading(box, 'Table', table), enable_sonnet=True, second=lambda _: saved)
                self.assertTrue(asked)
                label = 'Unlabelled' if box is None else 'Table'           # a box-less div is read as before: its table stands unlabelled
                self.assertEqual(rec['blocks'][1]['label'], label)
                self.assertIn('Net income', text)
                self.assertIn('region unknown' if box != TRUE_B else 'region 0,420-1000,470 px', [h for h in text.split('\n') if f'{label} |' in h][0])

    def test_a_labelled_wrapper_keeps_the_placed_blocks_inside_it(self):  # Root's review of v1: the block exception is the reader's own div only
        inner = '<div data-bbox="0 0 1000 300" data-label="Text"><p>Revenue rose sharply</p></div><div data-bbox="0 840 1000 940" data-label="Text"><p>Net income grew</p></div>'
        for tag in ('div', 'section', 'article', 'main', 'html', 'body'):
            with self.subTest(wrapper=tag):
                _, flags, text, rec = self.read(f'<{tag} data-label="Container">{inner}</{tag}>')
                self.assertEqual([(b['label'], b['box']) for b in rec['blocks']], [('Text', (0, 0, 1000, 300)), ('Text', (0, 840, 1000, 940))])
                self.assertEqual(self.heads(text), ['[CHANDRA ONLY Text | region 0,0-1000,150 px]', '[CHANDRA ONLY Text | region 0,420-1000,470 px]'])


if __name__ == '__main__':
    unittest.main()
