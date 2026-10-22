"""Fatal infrastructure failures must escape the native reading boundary."""
import hashlib
import unittest
from unittest.mock import patch
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from driver.prepare.convert import screen_grid as sg
from driver.prepare.get.acquire import StorageError


class NativeCaptureFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1400, 'height': 1000})
        self.page.set_content('<html><body><h1>Visible positive</h1></body></html>')

    def tearDown(self):
        self.page.close()

    def test_real_positive_capture(self):
        state, image = sg.native_state(self.page, 'unused-test-prefix')
        self.assertEqual(state['capture']['sha256'], hashlib.sha256(image).hexdigest())
        self.assertEqual([state['capture']['width'], state['capture']['height']], [1400, 1000])

    def test_fatal_classes_propagate_and_native_timeout_refuses(self):
        for fault in (MemoryError('exhausted'), OSError('storage failure'), StorageError('disk failure'),
                      ImportError('dependency missing'), PlaywrightTimeout('native capture timeout')):
            expected = sg.CaptureError if isinstance(fault, PlaywrightTimeout) else type(fault)
            with self.subTest(error=type(fault).__name__):
                with patch.object(self.page, 'screenshot', side_effect=fault):
                    with self.assertRaises(expected) as caught:
                        sg.native_state(self.page, 'unused-test-prefix')
                self.assertIs(type(caught.exception), expected)
