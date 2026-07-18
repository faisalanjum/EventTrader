#!/usr/bin/env python3
"""fiscal.ai CHANNEL-specific rules — NOT shared core.

Encodes fiscal.ai's OWN label convention: `% Chg` / `Common Size` are vendor-computed columns the filing
never states, so they can never be linked to a source quote. Other channels must NOT inherit this.
Kept out of link_lib (the shared value/gate core) on purpose. Moves to driver/channels/fiscal_ai/ at
end-reorg. Self-check: `venv/bin/python scripts/driver_seed/fiscal_ai_rules.py`.

NO magnitude 'plug' rule: a size threshold (<=1000) wrongly dropped legit small facts (78 'Total X = 0'
rows, 'International Stores = 86', 'ACPU = 670'). No value is pre-skipped by size — the locator proves a
value from its labeled context or it abstains (value_absent), per FINAL_DESIGN store-when-stated / abstain>guess.
"""


def is_derived(kpi):
    """fiscal.ai-computed rows (% change, common size). No filing states them -> never linkable."""
    return ('% Chg' in kpi) or ('%Chg' in kpi) or ('Common Size' in kpi)


if __name__ == '__main__':
    assert is_derived('Total Revenue % Chg.') and is_derived('Segment Revenue Common Size')
    assert not is_derived('iPhone Revenue') and not is_derived('Adjusted EBITDA')
    print('fiscal_ai_rules self-check OK')
