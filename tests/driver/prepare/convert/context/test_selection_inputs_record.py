"""The compared selection inputs are kept with every observation attempt (Root OCR_REPLAY_FAILURE_EVIDENCE_20261023T1545). Context._native_node refuses
when the inputs a replay received before the selection differ from the recorded parent state's; the exact received/refused sets it compared must stay
in that attempt's record even when it refuses before a native snapshot. Public invented fixture (test_native_selection's scripted-menu parent).
Expected sets come from the fixture's own recorded parent state (acquisition's NativeSelection.state_facts, unchanged code), never from the
changed record: the unchanged replay receives exactly those inputs, so a mutated recording differs from them by exactly the mutation."""
import copy, unittest
from .cases import context, sg, evidence, ANON, ROOT, rep
from .test_native_selection import SCRIPTED, select, declared

S = lambda xs: {tuple(x) for x in xs}
COUNTED = b'<nav></nav><script>let n = Number(sessionStorage.getItem("attempt") || 0) + 1; sessionStorage.setItem("attempt", n); fetch("/portal/attempt-" + n).catch(() => 0);</script>'  # Root's control: a deterministic, different GET in every attempt


def replay(browser, sel, parent=SCRIPTED, drop=()):  # one Context render of the initial view with the given declared selection: (error, the render's record)
    ev = evidence(child=ANON, parent=parent, drop=drop); ev['selection'] = sel
    ctx = context.Context(ev); src = context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx); page = err = None
    try:
        page = ctx.page(browser, None, ('https://trial.invalid/', ANON), src); page.goto('trial')
    except Exception as e:
        err = repr(e)[:300]
    finally:
        if page is not None: page.close()
    return err, ctx.records[0]


class SelectionInputsRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        r, s, _ = select(cls.browser, evidence(child=ANON, parent=SCRIPTED)); assert r['verdict'] == 'selected', r.get('verdict')
        cls.sel = declared(r, s)
        cls.delivered, cls.refused = S(s.state_facts['delivered']), S(s.state_facts['refused_get'])  # the fixture's recorded parent state
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def per_attempt(self, rec):  # every attempt's kept selection inputs: earlier attempts in their own records, the last one in the record itself (keep's rule)
        return [a.get('selection_inputs') for a in rec['attempts'][:-1]] + [rec.get('selection_inputs')]

    def refused_with(self, change):
        sel = copy.deepcopy(self.sel); change(sel['state_inputs']); err, rec = self.replay(sel)
        self.assertIsNotNone(err); self.assertIn('different inputs', rec.get('refused') or '')
        self.assertEqual([a['outcome'] for a in rec['attempts']], ['not used: refused'] * 3)
        got = self.per_attempt(rec); self.assertTrue(all(g is not None for g in got), got)
        for g in got: self.assertEqual((S(g['received']), S(g['refused_get'])), (self.delivered, self.refused))  # what was actually compared, each attempt
        return sel, got

    def replay(self, sel): return replay(self.browser, sel)

    def test_a_positive_selection_keeps_the_inputs_it_compared(self):
        err, rec = self.replay(copy.deepcopy(self.sel))
        self.assertIsNone(err, err); self.assertNotIn('refused', rec)
        g = rec.get('selection_inputs'); self.assertIsNotNone(g)
        self.assertEqual((S(g['received']), S(g['refused_get'])), (self.delivered, self.refused))

    def test_equal_count_different_identity_is_refused_and_the_difference_kept(self):
        first = sorted(self.delivered)[0]; changed = [first[0], first[1], '0' * 64]
        sel, got = self.refused_with(lambda si: si.__setitem__('delivered', [changed if tuple(x) == first else x for x in si['delivered']]))
        self.assertEqual(len(sel['state_inputs']['delivered']), len(self.delivered))  # equal counts
        for g in got: self.assertEqual(S(g['received']) ^ S(sel['state_inputs']['delivered']), {first, tuple(changed)})

    def test_a_recorded_input_absent_from_the_replay(self):
        extra = ('https://museum.invalid/absent.css', 200, '1' * 64)
        sel, got = self.refused_with(lambda si: si['delivered'].append(list(extra)))
        for g in got: self.assertEqual(S(sel['state_inputs']['delivered']) - S(g['received']), {extra})

    def test_a_replay_input_extra_to_the_recording(self):
        drop = sorted(self.delivered)[-1]
        sel, got = self.refused_with(lambda si: si.__setitem__('delivered', [x for x in si['delivered'] if tuple(x) != drop]))
        for g in got: self.assertEqual(S(g['received']) - S(sel['state_inputs']['delivered']), {drop})

    def test_a_recorded_refused_input_absent_from_the_replay(self):
        gone = ('https://museum.invalid/never.js', 'script')
        sel, got = self.refused_with(lambda si: si['refused_get'].append(list(gone)))
        for g in got: self.assertEqual(S(sel['state_inputs']['refused_get']) - S(g['refused_get']), {gone})

    def test_an_actual_refused_stylesheet_and_its_missing_delivered_tuple(self):  # (Smart's control) the browser's OWN refused request, not a changed recording
        css = [x for x in self.delivered if x[0] == ROOT + '/shared/frame.css']; self.assertEqual((len(css), self.refused), (1, set()))  # fixture facts: recorded, nothing refused
        err, rec = replay(self.browser, copy.deepcopy(self.sel), drop=(css[0][0],))  # the replay evidence lacks the recorded stylesheet
        self.assertIsNotNone(err); self.assertIn('different inputs', rec.get('refused') or '')
        rows = rec['attempts'][:-1] + [rec]; self.assertEqual(len(rows), 3)
        for row in rows:
            asked = {(q[2], q[3]) for q in row['requests'] if q[1] == 'GET' and q[2] == css[0][0]}; self.assertEqual(asked, {(css[0][0], 'stylesheet')})  # its own raw request log
            g = row['selection_inputs']; self.assertEqual(S(g['refused_get']), asked)
            self.assertEqual((self.delivered - S(g['received']), S(g['received']) - self.delivered), (set(css), set()))  # exactly the missing delivered tuple

    def test_each_attempt_keeps_its_own_requests_against_its_raw_log(self):  # Root's control: distinct actual sets per attempt; swap/overwrite damage detected
        err, rec = replay(self.browser, copy.deepcopy(self.sel), parent=rep(SCRIPTED, b'<nav></nav>', COUNTED))
        self.assertIsNotNone(err); self.assertIn('different inputs', rec.get('refused') or '')
        rows = rec['attempts'][:-1] + [rec]; self.assertEqual(len(rows), 3)
        def agrees(rows):  # each kept record equals the attempt-address requests of that attempt's own raw log
            for row in rows:
                own = {(q[2], q[3]) for q in row['requests'] if q[1] == 'GET' and q[2].startswith(ROOT + '/portal/attempt-')}
                if len(own) != 1 or S(row['selection_inputs']['refused_get']) != own: return False
            return True
        self.assertTrue(agrees(rows))
        for i, row in enumerate(rows, 1): self.assertEqual(row['selection_inputs']['refused_get'], [[ROOT + '/portal/attempt-%d' % i, 'fetch']])
        swapped = copy.deepcopy(rows); swapped[0]['selection_inputs'], swapped[1]['selection_inputs'] = swapped[1]['selection_inputs'], swapped[0]['selection_inputs']
        overwritten = copy.deepcopy(rows); overwritten[0]['selection_inputs'] = copy.deepcopy(overwritten[-1]['selection_inputs'])
        self.assertFalse(agrees(swapped)); self.assertFalse(agrees(overwritten))  # the check itself detects damage

    def test_earlier_attempts_are_never_overwritten(self):
        _, got = self.refused_with(lambda si: si['delivered'].append(['https://museum.invalid/x.css', 200, '2' * 64]))
        self.assertEqual(len(got), 3); self.assertEqual(len({id(g) for g in got}), 3)  # three separate records, one per attempt


if __name__ == '__main__':
    unittest.main()
