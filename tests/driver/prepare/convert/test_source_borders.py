"""A real total-row cue on the script-free path (Codex T1, public CCL 10-K R3, reused unchanged): report.css `.report .reu td {border-bottom: 1px solid
black}` underlines the 'Operating costs and expenses' row's number cells (its label cell's own style sets border-bottom 0). P keeps the source class (reu);
N changes only that class (re + space, same length). Each saved table cell must carry its OWN border sides as the browser computes them (the run-level stack was removed, Root final delta 4)."""
import hashlib, json, unittest
from pathlib import Path
from driver.prepare.convert import html_route, screen_grid as sg

FX = Path(__file__).resolve().parent / 'fixtures' / 'public_ccl_r3_total'
EXP = json.loads((FX / 'CODEX_T1_EXPECTED.json').read_bytes())
BROWSER = '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell'
NUMBERS = [(4972, 4986), (5023, 5036), (5073, 5086)]; LABEL = (4917, 4945)  # Codex T1's own saved cell anchors (SUMMARY selected_cells), the selected row's text runs
UNDER = ['bottom', '1px', 'solid', 'rgb(0, 0, 0)']


class TotalRowBorder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(executable_path=BROWSER, headless=True); cls.got = {}
        for v in ('P', 'N'):
            m = {n: (FX / v / n).read_bytes() for n in ('R3.htm', 'Show.js', 'include/report.css')}; raw = m['R3.htm']
            assert hashlib.sha256(raw).hexdigest() == (EXP['source_sha256'] if v == 'P' else EXP['negative_sha256'])
            cls.got[v] = html_route.prepare(raw, 'R3', hashlib.sha256(raw).hexdigest(), cls.browser, sg.Source('R3.htm', m))[0]
        # LABELLED boundary control (not a filing): P with the first number of the total row deleted, so that cell is EMPTY
        m = {n: (FX / 'P' / n).read_bytes() for n in ('R3.htm', 'Show.js', 'include/report.css')}; raw = m['R3.htm'].replace(b'11,757,000,000<span></span>', b'<span></span>', 1); m['R3.htm'] = raw
        cls.got['E'] = html_route.prepare(raw, 'R3', hashlib.sha256(raw).hexdigest(), cls.browser, sg.Source('R3.htm', m))[0]

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def cell(self, v, start):
        c = [c for u in self.got[v]['units'] if u.get('kind') == 'table' for c in u.get('cells') or [] if (c.get('source') or {}).get('byte_start') == start]
        self.assertEqual(len(c), 1, start); return c[0]

    def test_cells_own_their_borders(self):
        for s0 in (4955, 5006, 5056): self.assertIn(UNDER, self.cell('P', s0).get('borders') or [], s0)  # Codex T1 selected_cells source starts
        self.assertNotIn(UNDER, self.cell('P', 4738).get('borders') or [])  # the label cell: its own inline border-bottom 0px
        for s0 in (4955, 5006, 5056): self.assertNotIn(UNDER, self.cell('N', s0).get('borders') or [], s0)

    def test_empty_cell_keeps_its_own_border(self):
        c = self.cell('E', 4955); self.assertEqual((c.get('text') or '').strip(), ''); self.assertIn(UNDER, c.get('borders') or [])

    def test_everything_else_unchanged_between_P_and_N(self):
        strip = lambda units: [dict(u, cells=[{k: v for k, v in c.items() if k != 'borders'} for c in u['cells']]) if u.get('kind') == 'table' else u for u in units]
        a, b = self.got['P'], self.got['N']
        self.assertEqual(strip(a['units']), strip(b['units']))  # only the cells' own borders may differ (the changed class is exactly that)


if __name__ == '__main__':
    unittest.main()
