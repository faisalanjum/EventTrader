"""OnnxTR's own DocumentBuilder (no model: the predictor's last step, given what a detector and a recognizer would return) through the free reader's
box step (root, Oct 10, native-reader-numbers). The pinned builder (onnxtr 0.9.0 models/builder.py _build_blocks) keeps a straight box's corners as
NumPy scalars, the dtype its detector gives (float32, or float64). Every reading must still be the free OCR record the status rule accepts: pixel
numbers from the picture's own size times the box's own relative corners, in the reading order of the geometry defined here, saved by the worker as
JSON and reused from that file. Expectations come from W, H and the boxes below, never from the code under test."""
import io
import tempfile
import types
import unittest

import numpy as np
from PIL import Image
from onnxtr.io.elements import Block, Document, Line, Page, Word
from onnxtr.models.builder import DocumentBuilder

from driver.prepare.pictures import readers, worker

W, H = 40, 20                                                    # the picture; a box is (x0, y0, x1, y1) relative to it
ONE = [('amount', (.25, .5, .75, 1.))]                           # root's source-defined control: [10, 10, 30, 20] in pixels
ORDER = [('b', (.6, .1, .8, .3)), ('a', (.1, .1, .3, .3)), ('c', (.1, .6, .3, .8))]   # given out of order: a b on the top line, then c
px = lambda box: [round(box[0] * W, 1), round(box[1] * H, 1), round(box[2] * W, 1), round(box[3] * H, 1)]


def native(words, dtype):  # OnnxTR's predictor as its DocumentBuilder finishes it, for one W x H page
    def ox(pages):
        return DocumentBuilder()(pages, [np.array([b for _, b in words], dtype=dtype).reshape(-1, 4)], [np.full(len(words), .9, dtype=dtype)],
                                 [[(t, .9) for t, _ in words]], [(H, W)], [[{'value': 0, 'confidence': None} for _ in words]])
    return ox


def picture():
    b = io.BytesIO(); Image.new('RGB', (W, H), 'white').save(b, format='PNG'); return b.getvalue()


class NativeBuilderNumbers(unittest.TestCase):
    def reading(self, ox):
        im = readers._image(picture()); return dict(w=im.width, h=im.height, boxes=readers._ox_boxes(ox, im))

    def test_the_builders_float32_and_float64_boxes_are_complete_readings_in_pixels(self):
        for dtype in (np.float32, np.float64):
            with self.subTest(dtype=dtype.__name__):
                r = self.reading(native(ONE, dtype))
                self.assertEqual(readers._free_status(r), 'complete')
                self.assertEqual(r['boxes'], [dict(t='amount', box=[10.0, 10.0, 30.0, 20.0])])

    def test_python_numbers_stay_a_complete_reading(self):  # the earlier hand-built control: the builder's word type with Python floats
        word = Word('amount', .9, ((.25, .5), (.75, 1.)), .9, {'value': 0, 'confidence': None})
        r = self.reading(lambda pages: Document([Page(pages[0], [Block([Line([word])])], 0, (H, W))]))
        self.assertEqual((readers._free_status(r), r['boxes']), ('complete', [dict(t='amount', box=[10.0, 10.0, 30.0, 20.0])]))

    def test_no_words_is_a_complete_empty_reading(self):
        for dtype in (np.float32, np.float64):
            with self.subTest(dtype=dtype.__name__):
                r = self.reading(native([], dtype)); self.assertEqual((readers._free_status(r), r['boxes']), ('complete', []))

    def test_several_words_keep_the_reading_order_and_their_own_boxes(self):
        for dtype in (np.float32, np.float64):
            with self.subTest(dtype=dtype.__name__):
                r = self.reading(native(ORDER, dtype)); by = dict(ORDER)
                self.assertEqual(readers._free_status(r), 'complete')
                self.assertEqual(r['boxes'], [dict(t=t, box=px(by[t])) for t in ('a', 'b', 'c')])

    def test_the_worker_saves_the_reading_as_json_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def make(ox):
                def read(data): calls.append(1); return self.reading(ox)
                return lambda: types.SimpleNamespace(read=read, settings=dict(reader='ox-native-builder-test'), status=readers._free_status)
            first = worker.run(folder, [('f.htm#p1', picture())], make(native(ONE, np.float32)))['f.htm#p1']
            self.assertEqual((first['status'], first['result']['boxes']), ('complete', [dict(t='amount', box=[10.0, 10.0, 30.0, 20.0])]))
            def never(pages): raise AssertionError('a saved reading is read again')
            again = worker.run(folder, [('f.htm#p1', picture())], make(never))['f.htm#p1']
            self.assertEqual((again, len(calls)), (first, 1))


if __name__ == '__main__':
    unittest.main()
