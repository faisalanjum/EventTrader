"""A renderer crash must end the attempt promptly as a technical failure (DEFERRED_TODO priority 2, Fable 2026-11-02): with the pinned
Playwright 1.59 / Chrome 147 a page call in flight or made after a crash never returns (measured: probe_native*.py in the proof folder), and
the only end was the job's child timeout, then up to three jobs. `screen_grid.watch` (every page the six factories make) marks the browser
lost and closes the page, so the waiting call raises now; `screen_grid.alive` (the one 'technical, propagate' test at every catch site)
then propagates it, so the job's existing retry runs the document again with a fresh browser. Healthy routes are unchanged. Offline pinned
Chrome; playwright is required (a missing install fails, never skips). Each test launches its own browser: a lost browser is never reused.
If `watch` is ever removed, the crash tests hang until the runner's own bound (a lost call cannot be interrupted in-process: a SIGALRM does not
free it, measured); the inventory test fails first and names the unguarded line. Popups are watched by their own handler (page 'popup' event);
in the pinned headless shell a popup shares its opener's renderer (same- and cross-origin alike, measured), so the parent's handler fires too."""
import hashlib
import os
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from driver.prepare.convert import html_route, screen_grid as sg

PAGE = (b'<html><head><style>.x{color:#000}</style></head><body><p>Revenue was 1,234 in 2025.</p>'  # a sheet: the visibility render runs
        b'<table><tr><td>A</td><td>2</td></tr></table></body></html>')
SHA = hashlib.sha256(PAGE).hexdigest()
BOUND = 5.0  # seconds: a crash must surface well inside any child budget (the probes measured 0.06-0.3 s)
MODULES = ('convert/screen_grid.py', 'convert/context.py', 'convert/html_route.py', 'get/acquisition.py', 'get/context_acquire.py', 'pictures/inputs.py')


def crash(page):  # the native way a renderer dies: navigating to chrome://crash kills the page's renderer process (its navigation error is expected)
    from playwright.sync_api import Error as PlaywrightError
    try: page.goto('chrome://crash')
    except PlaywrightError: pass


def chromium_children():  # every process under this test process (the pinned driver and what it launched) whose command names the browser
    found, todo = [], [str(os.getpid())]
    while todo:
        kids = subprocess.run(['pgrep', '-P', todo.pop()], capture_output=True, text=True).stdout.split(); todo += kids
        for k in kids:
            try: cmd = Path(f'/proc/{k}/cmdline').read_bytes()
            except OSError: continue
            if b'chrome' in cmd: found.append(k)
    return found


def crash_at_creation(real):  # the real watch(), then the crash itself: the renderer dies before the factory's first use of the page
    def make(page): page = real(page); crash(page); return page  # the native event is delivered during the step's next browser call (measured): no call waits
    return make


PARENT_URL = 'http://parent.invalid/index.html'
PARENT_BODY = b'<html><head><title>p</title></head><body><p>parent 1,234</p></body></html>'


def startup_fetch():  # a valid startup fixture for context_acquire._startup_dependencies: the parent observed as its own 200, nothing left to fetch
    from types import SimpleNamespace
    from tests.driver.prepare.convert.context.cases import obs
    return SimpleNamespace(observed={PARENT_URL: obs(PARENT_BODY, 'text/html')}, log=[])


def sha(b): return hashlib.sha256(b).hexdigest()


def crashing_factory(original, crashed):  # the real factory, then one crash right after the page's first load (as a renderer dying mid-step)
    def make(browser, asked=None, document=None, source=None):
        page = original(browser, asked, document, source); goto = page.goto
        def goto_then_crash(*a, **k):
            r = goto(*a, **k)
            if not crashed: crashed.append(True); crash(page)
            return r
        page.goto = goto_then_crash; return page
    return make


class RendererCrash(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
    @classmethod
    def tearDownClass(cls): cls.pw.stop()
    def setUp(self): self.browser = self.pw.chromium.launch()
    def tearDown(self): self.browser.close()

    def test_a_healthy_route_is_unchanged_and_the_browser_stays_alive(self):
        route, facts = html_route.prepare(PAGE, 'c.htm', SHA, self.browser)
        self.assertEqual(route['status'], 'OK', route.get('error')); self.assertNotIn('error', facts['screen'])
        self.assertTrue(sg.alive(self.browser)); self.assertTrue(self.browser.is_connected())

    def test_a_crash_in_the_visibility_render_raises_within_the_bound_and_marks_the_browser_lost(self):
        crashed = []
        with patch.object(sg, '_offline_page', crashing_factory(sg._offline_page, crashed)):
            t = time.time()
            with self.assertRaises(Exception) as got: html_route.prepare(PAGE, 'c.htm', SHA, self.browser)
            waited = time.time() - t
        self.assertTrue(crashed); self.assertLess(waited, BOUND, got.exception)
        self.assertFalse(sg.alive(self.browser)); self.assertTrue(self.browser.is_connected())  # lost for this attempt, not disconnected: the distinction the catch sites need

    def test_a_crash_with_a_cdp_call_in_flight_raises_within_the_bound(self):  # Scope.call's pattern (CDP session, no Playwright timeout)
        from playwright.sync_api import Error as PlaywrightError
        page = sg.watch(self.browser.new_page()); page.goto('data:text/html,<p>x</p>'); cdp = page.context.new_cdp_session(page)
        page.on('console', lambda m: crash(page))
        t = time.time()
        with self.assertRaises(PlaywrightError): cdp.send('Runtime.evaluate', {'expression': '(async () => { console.log("go"); await new Promise(r => setTimeout(r, 30000)); })()', 'awaitPromise': True})
        self.assertLess(time.time() - t, BOUND); self.assertTrue(page.is_closed()); self.assertFalse(sg.alive(self.browser))

    def test_a_popup_crash_frees_the_parent_and_the_context_cleanup_closes_the_popup(self):  # a popup shares the renderer; acquisition/context only count popups
        from playwright.sync_api import Error as PlaywrightError
        ctx = self.browser.new_context(); page = sg.watch(ctx.new_page()); page.goto('data:text/html,<p>x</p>')
        with page.expect_popup() as pop: page.evaluate('window.open("about:blank")')
        crash(pop.value); t = time.time()
        with self.assertRaises(PlaywrightError): page.evaluate('1')
        self.assertLess(time.time() - t, BOUND); self.assertFalse(sg.alive(self.browser))
        self.browser.new_context().close()  # one more browser call: the popup's own pending crash event is delivered during it
        self.assertTrue(pop.value.is_closed())  # the popup was watched by its own handler (page 'popup' event), not only through the parent
        ctx.close(); self.assertEqual(ctx.pages, [])

    def test_a_crash_at_creation_ends_each_factory_step_within_the_bound(self):  # dynamic control per factory: the consumer raises, the browser is lost
        from tests.driver.prepare.convert.context import cases
        from driver.prepare.get import acquisition, context_acquire
        from driver.prepare.convert import anchor, context
        members = {'child.html': cases.CHILD, 'plan.png': cases.PNG}; child_sha = hashlib.sha256(cases.CHILD).hexdigest()
        steps = {
            'screen_grid._offline_page (the route)': lambda br: html_route.prepare(PAGE, 'c.htm', SHA, br),
            'html_route.declarations': lambda br: html_route.declarations(anchor.Visible(b'<a href="javascript:x()">t</a>'), br),
            'context.Context.page (initial view)': lambda br: context.contextual_routes(cases.CHILD, 'invented/child.html', child_sha, br, sg.Source('child.html', members), cases.evidence(), explore=False),
            'acquisition.Selection._page': lambda br: acquisition.Selection(cases.PARENT, cases.evidence()['observed'], cases.TARGET, cases.CHILD, cases.CHILD, sg.marker_prefix(cases.CHILD)).act(br, 0),
            'context_acquire startup page': lambda br: context_acquire._startup_dependencies(startup_fetch(), br, PARENT_URL),
        }  # the sixth factory (acquire_context's node-level page) sits inside a whole acquisition (campaign + verified package + measured copy): inventory test + the shared watch(); a live control belongs in the acquisition lane's fixtures
        for name, step in steps.items():
            with self.subTest(factory=name):
                browser = self.pw.chromium.launch()
                try:
                    with patch.object(sg, 'watch', crash_at_creation(sg.watch)):
                        t = time.time()
                        with self.assertRaises(Exception) as got: step(browser)
                    self.assertLess(time.time() - t, BOUND, repr(got.exception)); self.assertTrue(browser.is_connected(), name)
                    stale = sg.alive(browser)  # a navigation can fail natively before the crash event is delivered (Selection's first goto): the flag is then still clear
                    browser.new_context().close()  # any later browser call delivers it: the attempt's completion guard (document.py) reads the flag after all browser work
                    self.assertFalse(sg.alive(browser), name); self.assertIn(stale, (True, False))
                finally: browser.close()

    def test_after_a_crash_a_fresh_browser_completes_the_same_document(self):  # the job's retry shape: a new child, a new browser, the same bytes
        crashed = []
        with patch.object(sg, '_offline_page', crashing_factory(sg._offline_page, crashed)):
            with self.assertRaises(Exception): html_route.prepare(PAGE, 'c.htm', SHA, self.browser)
        fresh = self.pw.chromium.launch()
        try:
            self.assertTrue(sg.alive(fresh)); route, facts = html_route.prepare(PAGE, 'c.htm', SHA, fresh)
            self.assertEqual(route['status'], 'OK', route.get('error')); self.assertTrue(sg.alive(fresh))
        finally: fresh.close()

    def test_after_a_crash_closing_the_browser_leaves_no_chromium_process_in_this_tree(self):  # the native cleanup the job's child relies on when it exits
        crashed = []
        with patch.object(sg, '_offline_page', crashing_factory(sg._offline_page, crashed)):
            with self.assertRaises(Exception): html_route.prepare(PAGE, 'c.htm', SHA, self.browser)
        self.assertTrue(chromium_children(), 'the control needs a live browser process to prove the cleanup')
        self.browser.close(); t = time.time()
        while time.time() - t < BOUND and chromium_children(): time.sleep(0.1)
        self.assertEqual(chromium_children(), [], 'a Chromium process survived browser.close() after a renderer crash')

    def test_the_node_level_page_of_acquire_context_binds_healthy_and_fails_fast_on_a_crash(self):  # the sixth factory: context_acquire.py:189-190 as written
        from playwright.sync_api import Error as PlaywrightError
        from driver.prepare.get import context_acquire as ca
        from driver.prepare.convert import overlay
        from tests.driver.prepare.get.test_inserted_script_binding import case, FILED, TARGET
        copy, _, _, _ = case(b'<script type="text/javascript" src="/Qp9qZ/J_/x"></script>'); member = FILED + b'</body></html>'  # the member = the published copy minus SEC's one inserted run
        fit = (member, {'form': 'equal', 'inserted': list(overlay._one_run(member, copy))})  # the proof as the acquisition's own alignment states it
        body, mrec = overlay.measurement_body(copy, member, member, sg.marker_prefix(member), fit[1]); self.assertIsNotNone(body, mrec); self.assertIn('window', mrec)
        def lines(browser):  # context_acquire.py:189-190 verbatim
            pg = sg.watch(browser.new_page(java_script_enabled=False))
            try: nl = overlay.node_level(pg, body, mrec, 'utf-8'); ins = ca.bind_inserted(pg, copy, fit, mrec, nl, TARGET) if nl['node_level'] else {'why': 'inserted run not node-level'}
            finally: pg.close()
            return nl, ins
        nl, ins = lines(self.browser)  # healthy: the inserted script is node-level and bound to its own address
        self.assertTrue(nl['node_level']); self.assertEqual(ins.get('href'), 'https://www.sec.gov/Qp9qZ/J_/x', ins); self.assertTrue(sg.alive(self.browser))
        fresh = self.pw.chromium.launch()
        try:
            with patch.object(sg, 'watch', crash_at_creation(sg.watch)):
                t = time.time()
                with self.assertRaises(PlaywrightError): lines(fresh)
            self.assertLess(time.time() - t, BOUND); fresh.new_context().close(); self.assertFalse(sg.alive(fresh)); self.assertTrue(fresh.is_connected())
        finally: fresh.close()

    def test_a_healthy_startup_fixed_point_is_unchanged(self):  # the valid positive beside the startup-page crash control
        from driver.prepare.get import context_acquire
        got = context_acquire._startup_dependencies(startup_fetch(), self.browser, PARENT_URL)
        self.assertTrue(got.get('fixed_point'), got); self.assertTrue(sg.alive(self.browser))

    def test_a_crash_in_the_first_job_is_a_prompt_technical_failure_and_the_next_job_completes(self):  # the job's shape of recovery, through job.py and document.main
        import json, os, subprocess, sys, tempfile
        from redisDB import prepared_filing as pf
        root = Path(html_route.__file__).resolve().parents[3]
        exe = os.environ.get('BROWSER_EXECUTABLE', '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell')
        b = self.pw.chromium.launch(executable_path=exe); version = b.version; b.close()
        folder = Path(tempfile.mkdtemp(prefix='renderer_crash_job_')); manifest = folder / 'MANIFEST.json'
        manifest.write_text(json.dumps({'files': {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted((root / 'driver').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}}))
        (folder / 'case.html').write_bytes(PAGE); marker = folder / 'CRASHED_ONCE'
        plan = dict(runtime_root=str(root), runtime_manifest=dict(path=str(manifest), sha256=sha(manifest.read_bytes())),
                    browser_executable=exe, browser_executable_sha256=sha(Path(exe).read_bytes()), browser_version=version,
                    source_commands=[dict(file_id='case.html', filename='case.html', source_sha256=SHA, dispatch='html', directory=str(folder),
                                          members={'case.html': dict(sha256=SHA, bytes=len(PAGE))}, base=None, bundle=None)],
                    renderer_crash_once=str(marker))
        body = json.dumps(plan).encode(); (folder / 'PLAN.json').write_bytes(body)
        generator = Path(__file__).resolve().parents[1] / 'fixtures/renderer_crash_generator.py'; rows = []
        for k in (1, 2):  # the adapter's retry runs the same plan again (max_jobs): here the second run of job.py
            t = time.time()
            process = subprocess.run([sys.executable, '-I', '-S', '-B', str(root / 'driver/prepare/job.py'), str(folder / 'PLAN.json'), sha(body), str(folder / f'job{k}'), str(generator), '40'],
                                     env={'PATH': '/usr/bin:/bin', 'HOME': os.environ['HOME']}, capture_output=True, timeout=150)
            wall = time.time() - t; result = folder / f'job{k}/RESULT.json'; row = json.loads(result.read_bytes())['rows'][0]
            status, reasons = pf.status(result, sha(body), [dict(filename='case.html', category='html', format_hint='html')])
            rows.append((k, status, row['outcome'], round(wall, 1), process.returncode, reasons))
        self.assertEqual([r[1:3] for r in rows], [('failed', 'generation_failed'), ('complete', 'verified_saved_output')], (rows, process.stderr[-800:]))
        self.assertLess(rows[0][3], 30, rows)  # the crashed first child ended promptly: no 40 s child timeout, no hang
        self.assertTrue(marker.exists())

    def test_every_page_factory_is_watched_and_every_technical_decision_is_alive(self):  # inventory control: a future factory or catch site cannot miss the guard
        root = Path(html_route.__file__).resolve().parents[1]
        for name in MODULES:
            text = (root / name).read_text()
            for line in text.splitlines():
                if 'new_page(' in line and 'def watch' not in line: self.assertIn('watch(', line, f'{name}: unwatched page factory: {line.strip()[:100]}')
                if 'is_connected()' in line and 'def alive' not in line: self.fail(f'{name}: a technical decision bypasses alive(): {line.strip()[:100]}')
            made = sum('new_page(' in l for l in text.splitlines()); guarded = sum('watch(' in l and 'def watch' not in l for l in text.splitlines())
            self.assertEqual(made, guarded, f'{name}: watch() lines must equal new_page() lines (one guard per factory, no stray call)')


if __name__ == '__main__':
    unittest.main()
