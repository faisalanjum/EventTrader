"""EFFECTIVE STYLES on the old (viewer) route: context._effective_sheet_reasons on the REAL sheet facts of a fresh viewer replay of public AMG R1
(fixtures/public_amg_viewer_sheets, cand OUT_GREEN5 render 0, the browser's own cssText) with the same campaign's recorded answers.
Real: every reviewed sheet's current native text equals one of its DEMONSTRATED native serializations (bootstrap: clean <link> parse or the same-DOM
JS-disabled parse, Codex S0b) -> no reason. Labelled negatives: a rule changed after load, @import, adopted sheet, unknown bytes, unreviewed inline."""
import copy, json, unittest
from pathlib import Path
from driver.prepare.convert import context

FX = json.loads((Path(__file__).resolve().parents[1] / 'fixtures' / 'public_amg_viewer_sheets' / 'REVEAL_SHEETS.json').read_bytes())
OBSERVED = {u: r['sha256'] for u, r in FX['recorded'].items() if r and r['status'] == 200}
ANSWERED = {u: r['status'] for u, r in FX['recorded'].items() if r}
RV = {'sheets': FX['sheets'], 'adopted': FX['adopted']}
K = lambda word: next(k for k, x in enumerate(FX['sheets']) if x[0] and word in x[0])
why = lambda rv, obs=OBSERVED: context._effective_sheet_reasons(rv, obs, ANSWERED)


class EffectiveSheets(unittest.TestCase):
    def test_real_viewer_native_text_is_reviewed(self):  # bootstrap: its live text is the DEMONSTRATED same-DOM native serialization (Codex S0b 12bc2d06)
        self.assertEqual(why(RV), [])  # 404 cgi-bin/include/report.css (no rules) and print.css skipped

    def test_the_known_t2_rule_inserted_into_bootstrap_is_caught(self):  # Codex S0b: insertRule leaves the response bytes (and CDP getStyleSheetText) unchanged; the live text is not
        rv = copy.deepcopy(RV); rv['sheets'][K('bootstrap')][5] += '\ntable.authRefData:not([id])::before { content: "Amounts in millions."; }'
        self.assertTrue(any('bootstrap' in x for x in why(rv)))

    def test_a_rule_changed_after_load_is_caught(self):  # same served bytes, different current native text (what insertRule/deleteRule would leave)
        rv = copy.deepcopy(RV); rv['sheets'][K('interactive2')][5] += '\n.report td::before { content: "Amounts in millions."; }'
        self.assertTrue(any('interactive2' in x for x in why(rv)))

    def test_import_adopted_unknown_bytes_and_inline_are_caught(self):
        rv = copy.deepcopy(RV); rv['sheets'][K('interactive2')][6] = 1; self.assertTrue(any('interactive2' in x for x in why(rv)))
        self.assertTrue(any('adopted' in x for x in why(dict(RV, adopted=1))))
        obs = dict(OBSERVED); obs[FX['sheets'][K('report.css')][0]] = 'f' * 64; self.assertTrue(any('include/report.css' in x for x in why(RV, obs)))
        rv = copy.deepcopy(RV); rv['sheets'].append([None, False, '', 'style', 'td::after{content:"x"}', 'td::after { content: "x"; }', 0]); self.assertTrue(any('(inline)' in x for x in why(rv)))

    def test_a_404_that_applies_rules_is_not_skipped(self):
        rv = copy.deepcopy(RV); rv['sheets'][K('cgi-bin')][5] = 'td { color: red; }'; self.assertTrue(any('cgi-bin' in x for x in why(rv)))


    def test_missing_adopted_fact_is_unknown_not_none(self):  # Root/Codex d235 review: a missing 'adopted' must not read as zero adopted sheets
        import collections, re
        acts = json.loads((Path(__file__).resolve().parents[1] / 'fixtures' / 'public_amg_viewer_sheets' / 'REAL_CODE_ACTIONS.json').read_bytes())['actions']
        declared = dict(collections.Counter(v for v, _, _ in acts['actions']))
        targets = {k: m.group(1) for k, (v, _, _) in enumerate(acts['actions']) for m in [re.match(r"Show\.showAR\( this, '([^']+)', window \);$", v or '')] if m}
        unknown = 'reveal profile facts unknown (shared guard)'
        self.assertNotIn(unknown, context._dom_action_reasons(acts, declared, targets, []))  # the real facts, adopted present
        bare = copy.deepcopy(acts); del bare['reveal']['adopted']
        self.assertIn(unknown, context._dom_action_reasons(bare, declared, targets, []))

if __name__ == '__main__':
    unittest.main()
