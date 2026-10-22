"""Independent regressions for complete readings and the existing source-identity rule."""
import copy
import unittest

from .cases import ANON, context, evidence, sg


class RenderRecords(unittest.TestCase):
    def test_every_attempted_reading_needs_a_completed_observation(self):
        plain = {'marked': False, 'native': {'document_sha256': 'independent-content-digest',
                 'received': [], 'refused_get': []}}
        marked = dict(copy.deepcopy(plain), marked=True)
        cases = [
            ('equal_completed_pair', [plain, marked], True),
            ('no_observation', [], False),
            ('no_unmarked_reference', [marked], False),
            ('later_render_lacks_native_record', [plain, {'marked': True}], False),
            ('refused_later_render', [plain, {'marked': True, 'refused': 'observation interrupted'}], False),
            ('different_completed_pair', [plain, dict(marked, native=dict(marked['native'], document_sha256='changed'))], False),
        ]
        for name, records, expected in cases:
            with self.subTest(name=name):
                ctx = context.Context(evidence(child=ANON))
                ctx.records = copy.deepcopy(records)
                self.assertEqual(not ctx.gate(), expected)


class ResponseCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def test_context_reuses_the_original_response_identity_rule(self):
        for which in (None, 'parent_url', 'target_url'):
            with self.subTest(response=which or 'clean_positive'):
                ev = evidence(child=ANON)
                if which:
                    ev['observed'][ev[which]]['sha256'] = '0' * 64
                    ordinary = sg.Source('child.html', {'child.html': ANON}, observed=ev['observed'])
                    self.assertIsNone(ordinary.answer(ev[which], 'document'),
                                      'The pre-existing Source contract refuses these inconsistent bytes.')
                ctx = context.Context(ev)
                source = context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx)
                page, error = None, None
                try:
                    page = ctx.page(self.browser, None, ('https://trial.invalid/', ANON), source)
                    page.goto('trial')
                except Exception as exc:
                    error = exc
                finally:
                    if page is not None:
                        page.close()
                self.assertEqual(error is None and not ctx.gate(), which is None,
                                 (str(error), ctx.gate()))
