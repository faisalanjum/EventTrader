"""Failed browser observation of one action (Root CONTEXT_ACTION_OBSERVATION_REPAIR_20261022T0535).

DETERMINISTIC PHASE FAULTS, not a native reproduction: a stand-in page raises the pinned library's own public typed error
(playwright.sync_api.Error) at a chosen step of Selection.act (pre-action reading, click, settle, after-action reading).
The real Chromium mechanism (context destroyed by a navigation during quiet_settle) is OCR's public red, replayed by Root.
Runtime under test: CANDIDATE_RUNTIME when set (a runtime root holding driver/); otherwise the checkout's own driver/."""
import json, os, sys, unittest
if os.environ.get('CANDIDATE_RUNTIME'): sys.path.insert(0, os.environ['CANDIDATE_RUNTIME'])
from playwright.sync_api import Error as PlaywrightError
from driver.prepare.get import acquisition as aq
from driver.prepare.get.acquire import AcquisitionError

PARENT, TARGET = 'https://www.sec.gov/Archives/parent.htm', 'https://www.sec.gov/Archives/target.htm'


class Src:  # the Source surface facts() reads
    def __init__(self): self.records, self.refusals = {}, []


class Page:
    def __init__(self, rec): self.rec, self.fail, self.doc, self.closed, self.clicked = rec, None, 'D', False, False
    def is_closed(self): return self.closed
    def evaluate(self, js, *args):
        if js is aq.SER:
            if self.fail == 'after-action reading': raise PlaywrightError('deterministic phase fault: after-action reading')
            return [self.doc, 1]
        if js is aq.READ: return {'marks': [], 'shown': True, 'url': PARENT}
        return 0  # window.__m


class Handle:
    def __init__(self, page): self.page = page
    def evaluate(self, js):
        p = self.page
        if 'checkVisibility' in js:
            if p.fail == 'pre-action reading': raise PlaywrightError('deterministic phase fault: pre-action reading')
            return True
        p.clicked = True; p.rec['log'].append(('GET', TARGET, False)) if p.fail != 'no-target' else None
        p.rec['source'].records[TARGET] = {'url': TARGET, 'status': 200, 'measured_sha256': aq.sha(b'body')}
        if p.fail == 'click': raise PlaywrightError('deterministic phase fault: click')
        if p.fail == 'click-closed': p.closed = True; raise PlaywrightError('deterministic phase fault: page closed')
        if p.fail == 'click-oserror': raise OSError('storage fault')
        if p.fail == 'click-custody': raise AcquisitionError('custody fault')
        if p.fail == 'click-bug': raise KeyError('programming fault')


class Ctx:
    def close(self): pass


class Browser:
    def __init__(self, connected=True): self.connected = connected
    def is_connected(self): return self.connected


class S(aq.Selection):
    """Selection with stand-in pages; script[i] = the successive (fault, doc) of each act of control i."""
    def __init__(self, script, initial_target=False, initial_state=None):
        self.parent_url, self.target, self.prefix, self.body, self.settle_s, self.offline = PARENT, TARGET, 'zz', b'body', 0, True
        self.hrefs, self.expect, self.script, self.calls, self.initial_target, self.initial_state = [None] * len(script), [], script, {}, initial_target, initial_state
    def _page(self, browser, marked, rec):
        rec['source'] = Src(); rec['pages'] = [PARENT]; rec['initial_settled'] = True
        if self.initial_target: rec['log'].append(('GET', TARGET, False))
        return Ctx(), Page(rec)
    def _locate(self, page, i, rec=None):
        k = self.calls[i] = self.calls.get(i, 0) + 1; page.fail, page.doc = self.script[i][k - 1]
        return Handle(page), None
    def _settle(self, page):
        if page.clicked and page.fail == 'settle': raise PlaywrightError('deterministic phase fault: Execution context was destroyed')
        return True
    def initial(self, browser):
        self.initial_result = {'state': self.initial_state}; return self.initial_result


OK = (None, 'D')


class ActionObservationFailure(unittest.TestCase):
    def setUp(self):
        self.native = aq.sg.native_state; aq.sg.native_state = lambda page, prefix, blobs=None: ({'sha256': page.doc},)
    def tearDown(self): aq.sg.native_state = self.native

    def test_failed_action_is_recorded_with_raw_error_and_split_facts(self):
        for step in ('click', 'settle', 'after-action reading'):
            a = S([[(step, None)]]).act(Browser(), 0, True)
            self.assertEqual(a['state'], 'failed: browser observation during ' + step)
            self.assertEqual(a['error']['type'], 'playwright._impl._errors.Error'); self.assertIn('deterministic phase fault', a['error']['message'])
            self.assertIn('name', a['error']); self.assertIn('stack', a['error'])
            self.assertIn('pre_action_facts', a); self.assertIn('facts', a); self.assertEqual(a['requests_after_action'], [('GET', TARGET, False)])
            self.assertEqual(json.loads(json.dumps(a, default=str))['error']['type'], 'playwright._impl._errors.Error')  # survives the _strip round trip

    def test_failure_before_the_click_keeps_only_pre_action_facts(self):
        a = S([[('pre-action reading', None)]]).act(Browser(), 0, True)
        self.assertEqual(a['state'], 'failed: browser observation during pre-action reading')
        self.assertIn('pre_action_facts', a); self.assertNotIn('facts', a); self.assertNotIn('requests_after_action', a)

    def test_fatal_classes_still_propagate(self):
        with self.assertRaises(PlaywrightError): S([[('click', None)]]).act(Browser(connected=False), 0, True)  # browser loss
        with self.assertRaises(PlaywrightError): S([[('click-closed', None)]]).act(Browser(), 0, True)  # page/context loss
        with self.assertRaises(OSError): S([[('click-oserror', None)]]).act(Browser(), 0, True)
        with self.assertRaises(AcquisitionError): S([[('click-custody', None)]]).act(Browser(), 0, True)
        with self.assertRaises(KeyError): S([[('click-bug', None)]]).act(Browser(), 0, True)

    def test_healthy_action_unchanged(self):
        r = S([[OK, OK]]).run(Browser())
        self.assertEqual(r['verdict'], 'selected'); a = r['attempts'][0]
        self.assertEqual(a['state'], 'qualified'); self.assertNotIn('error', a)
        self.assertIn('pre_action_facts', a)  # v3 (Root 0558): the pre-action reading the action already took is kept on normal paths too

    def test_verdicts_zero_one_two_qualified_and_order(self):
        self.assertEqual(S([[('settle', None)]]).run(Browser())['verdict'], 'incomplete: 1 action observation(s) not decided')  # zero qualified, one failed: never missing
        self.assertEqual(S([[('no-target', 'D')]]).run(Browser())['verdict'], 'missing')  # zero qualified, all refused: unchanged
        r = S([[('settle', None)], [OK, OK]]).run(Browser()); self.assertEqual(r['verdict'], 'selected')  # a failed control before the qualified one
        self.assertTrue(any(a['state'].startswith('failed: browser observation') and 'error' in a for a in r['attempts']))  # the sibling's failure retained
        r = S([[OK, OK], [('settle', None)]]).run(Browser()); self.assertEqual(r['verdict'], 'selected')  # v3 (Root 1809): first fully qualified, the failing sibling is never run
        self.assertEqual((len(r['attempts']), r['search']['untried'], r['search']['untried_reason']), (1, 1, 'stopped at the first fully qualified context'))
        r = S([[OK, OK], [OK, OK]]).run(Browser())  # v3 (Root 1809): was 'ambiguous' (exhaustive); now the first qualified control, the second untried (not absent)
        self.assertEqual((r['verdict'], [a['source_anchor'] for a in r['attempts']], r['search']['untried']), ('selected', [0], 1))

    def test_failed_unmarked_repeat_stops_the_reading_and_is_kept(self):
        r = S([[OK, ('settle', None)]]).run(Browser()); a = r['attempts'][0]
        self.assertEqual(a['state'], 'failed: browser observation during settle'); self.assertEqual(r['verdict'], 'incomplete: 1 action observation(s) not decided')
        log = a['canonical']['attempts']; self.assertEqual(len(log), 1); self.assertTrue(log[0]['outcome'].startswith('fatal: browser observation during settle'))
        self.assertIn('error', log[0]['failed_attempt'])

    def test_failed_marked_repeat_stops_the_reading_and_is_kept(self):
        r = S([[(None, 'D-first'), OK, ('settle', None)]]).run(Browser()); a = r['attempts'][0]  # first marked differs from the reference, the next marked fails
        self.assertEqual(a['state'], 'failed: browser observation during settle')
        log = a['canonical']['attempts']; self.assertEqual([e['outcome'] for e in log][:2], ['reference', 'not used'])
        self.assertTrue(log[-1]['outcome'].startswith('fatal:')); self.assertIn('error', log[-1]['failed_attempt'])
        self.assertNotEqual(r['verdict'], 'missing')

    def test_initial_reading_failed_or_incomplete_is_not_missing(self):
        self.assertEqual(S([], initial_target=True, initial_state='failed: native capture refused: x').run(Browser())['verdict'], 'incomplete: initial reading failed: native capture refused: x')
        self.assertEqual(S([], initial_target=True, initial_state='incomplete: no settled unmarked reference within 3 attempts').run(Browser())['verdict'],
                         'incomplete: initial reading incomplete: no settled unmarked reference within 3 attempts')
        self.assertEqual(S([], initial_target=True, initial_state='refused: target not requested').run(Browser())['verdict'], 'missing')
        self.assertEqual(S([], initial_target=True, initial_state='qualified').run(Browser())['verdict'], 'initial')


PRE, POST, NAV = 'https://fixture.invalid/initial.css', 'https://fixture.invalid/action.css', 'https://fixture.invalid/initial-navigation'


class Declared(S):
    """The failing act's own Source declares a refused stylesheet and a refused navigation before the click, and another refused stylesheet after it."""
    def _locate(self, page, i, rec=None):
        h, why = super()._locate(page, i, rec)
        if page.fail == 'settle': rec['source'].records[PRE] = {'url': PRE, 'status': 'refused', 'kind': 'stylesheet'}; rec['source'].refusals.append((NAV, 'navigation'))
        return h, why
    def _settle(self, page):
        if page.clicked and page.fail == 'settle': page.rec['source'].records[POST] = {'url': POST, 'status': 'refused', 'kind': 'stylesheet'}; page.rec['log'].append(('GET', POST, False))
        return super()._settle(page)


CASES = {'failed first action': [[('settle', None)], [OK, OK]], 'failed unmarked repeat': [[OK, ('settle', None)], [OK, OK]],
         'failed marked repeat': [[(None, 'D-first'), OK, ('settle', None)], [OK, OK]]}  # each beside a healthy qualified sibling


class FailedRepeatFacts(unittest.TestCase):  # Root CONTEXT_FAILED_REPEAT_PROJECTION_20261022T0545
    def setUp(self):
        self.native = aq.sg.native_state; aq.sg.native_state = lambda page, prefix, blobs=None: ({'sha256': page.doc},)
    def tearDown(self): aq.sg.native_state = self.native

    def test_every_failed_record_reaches_reading_facts_in_its_own_role(self):
        from driver.prepare.get.context_acquire import _reading_facts, _strip
        for name, script in CASES.items():
            r = _strip(Declared(script).run(Browser())); self.assertEqual(r['verdict'], 'selected', name)
            reads = _reading_facts(r)
            initial = {u for f, first in reads if first for u, k in f['refused_get']}; nav = {u for f, first in reads if first for u in f['refused_navigation']}
            after = {u for f, first in reads if not first for u, k in f['refused_get']}
            self.assertIn(PRE, initial, name); self.assertIn(NAV, nav, name); self.assertIn(POST, after, name)
            self.assertNotIn(POST, initial, name)  # an after-action fact never becomes an initial one

    def test_actual_closure_with_a_healthy_selected_sibling(self):
        from driver.prepare.get import context_acquire as ca
        class Fetch: observed, log = {}, []
        real = aq.select_parent
        try:
            for name, script in CASES.items():
                aq.select_parent = lambda browser, *a, script=script, **k: (dict(Declared(script).run(browser), prepared_state={}), None)  # v3: _select's one selector, with the stand-in pages
                r, s = ca._select(Fetch(), Browser(), PARENT, TARGET, None, None, 'zz', 200)
                self.assertEqual((r['selection_verdict'], r['verdict']), ('selected', 'incomplete: pending navigation'), name)
                self.assertTrue({PRE, POST} <= set(r['unobserved']), name); self.assertIn(NAV, r['navigations'], name)
        finally: aq.select_parent = real

    def test_failed_repeat_is_neither_retried_nor_used_and_its_settling_is_unknown(self):
        for name in ('failed unmarked repeat', 'failed marked repeat'):
            script = CASES[name]; s = Declared(script); a = s.run(Browser())['attempts'][0]
            self.assertEqual(s.calls[0], len(script[0]), name)  # no act after the failure
            fail = a['canonical']['attempts'][-1]
            self.assertTrue(fail['outcome'].startswith('fatal: browser observation during settle'), name); self.assertIsNone(fail['settled'], name)
            self.assertEqual(fail['marked'], name == 'failed marked repeat'); self.assertIn('error', fail['failed_attempt'])
            self.assertEqual(a['state'], 'failed: browser observation during settle', name)


CSS_BEFORE, CSS_AFTER, CSS_INITIAL = 'https://fixture.invalid/before.css', 'https://fixture.invalid/after.css', 'https://fixture.invalid/initial-reading.css'


class Reads(S):
    """No browser error: a normal reading whose own Source refuses a stylesheet before the click ('css-before'), after it ('css-after') or both."""
    def _locate(self, page, i, rec=None):
        h, why = super()._locate(page, i, rec)
        if page.fail in ('css-before', 'css-both'): rec['source'].records[CSS_BEFORE] = {'url': CSS_BEFORE, 'status': 'refused', 'kind': 'stylesheet'}
        return h, why
    def _settle(self, page):
        if page.clicked and page.fail in ('css-after', 'css-both'):
            page.rec['source'].records[CSS_AFTER] = {'url': CSS_AFTER, 'status': 'refused', 'kind': 'stylesheet'}; page.rec['log'].append(('GET', CSS_AFTER, False))
        return super()._settle(page)


class InitialReads(S):
    """The real canonical initial reading (Selection.initial / _observe_view); every marked reading after the baseline refuses a stylesheet."""
    initial = aq.Selection.initial
    def _page(self, browser, marked, rec):
        ctx, page = super()._page(browser, marked, rec); self.loads = getattr(self, 'loads', 0) + 1
        if marked and self.loads > 1: rec['source'].records[CSS_INITIAL] = {'url': CSS_INITIAL, 'status': 'refused', 'kind': 'stylesheet'}
        return ctx, page


def roles(r):
    from driver.prepare.get.context_acquire import _reading_facts, _strip
    reads = _reading_facts(_strip(r))
    return ({u for f, first in reads if first for u, k in f['refused_get']}, {u for f, first in reads if not first for u, k in f['refused_get']})


class AllReadingFacts(unittest.TestCase):  # Root CONTEXT_ALL_READING_FACTS_20261022T0558: every canonical observation's facts reach _reading_facts
    def setUp(self):
        self.native = aq.sg.native_state; aq.sg.native_state = lambda page, prefix, blobs=None: ({'sha256': page.doc},)
    def tearDown(self): aq.sg.native_state = self.native

    def test_ordinary_refused_reference_repeat_reaches_closure_beside_a_selected_sibling(self):
        script = [[OK, ('css-after', 'D'), OK, OK], [OK, OK]]  # control 0's unmarked reference repeat is a normal refused reading; control 1 qualifies
        r = Reads(script).run(Browser()); self.assertEqual(r['verdict'], 'selected')
        self.assertTrue(r['attempts'][0]['state'].startswith('incomplete: no marked attempt matched'))
        initial, after = roles(r); self.assertIn(CSS_AFTER, after); self.assertNotIn(CSS_AFTER, initial)
        from driver.prepare.get import context_acquire as ca
        class Fetch: observed, log = {}, []
        real = aq.select_parent
        try:
            aq.select_parent = lambda browser, *a, **k: (dict(Reads(script).run(browser), prepared_state={}), None)  # v3: _select's one selector, with the stand-in pages
            got, s = ca._select(Fetch(), Browser(), PARENT, TARGET, None, None, 'zz', 200)
        finally: aq.select_parent = real
        self.assertEqual((got.get('selection_verdict'), got['verdict']), ('selected', 'incomplete: unobserved dependency')); self.assertIn(CSS_AFTER, got['unobserved'])

    def test_initial_and_action_phases_stay_separate(self):
        r = Reads([[OK, ('css-both', 'D'), OK, OK], [OK, OK]]).run(Browser()); initial, after = roles(r)
        self.assertIn(CSS_BEFORE, initial); self.assertIn(CSS_AFTER, after); self.assertNotIn(CSS_AFTER, initial)

    def test_unmatched_marked_repeat_beside_two_qualified(self):
        r = Reads([[(None, 'D-first'), OK, ('css-after', 'D'), OK], [OK, OK]]).run(Browser())  # control 0: first marked unmatched, next marked refused, third used
        self.assertEqual(r['verdict'], 'selected'); self.assertEqual([a['state'] for a in r['attempts']], ['qualified'])  # v3 (Root 1809): was 'ambiguous' with both qualified; control 1 now untried
        self.assertEqual(r['search']['untried'], 1)
        initial, after = roles(r); self.assertIn(CSS_AFTER, after)

    def test_canonical_initial_readings_are_initial(self):
        s = InitialReads([], initial_target=True); r = s.run(Browser())
        self.assertTrue(r['verdict'].startswith('incomplete: initial reading incomplete'))
        initial, after = roles(r); self.assertIn(CSS_INITIAL, initial); self.assertNotIn(CSS_INITIAL, after)

    def test_error_repeat_still_reaches_closure_without_a_failure_flag_in_the_collector(self):
        from driver.prepare.get.context_acquire import _reading_facts
        r = Declared(CASES['failed unmarked repeat']).run(Browser()); log = r['attempts'][0]['canonical']['attempts']
        self.assertIn('failed_attempt', log[-1]); self.assertIn('pre_action_facts', log[-1])  # raw failure kept; its facts carried by the same reading record
        initial, after = roles(r); self.assertIn(PRE, initial); self.assertIn(POST, after)


if __name__ == '__main__':
    unittest.main()
