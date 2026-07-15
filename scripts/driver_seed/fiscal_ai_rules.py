#!/usr/bin/env python3
"""fiscal.ai CHANNEL-specific rules — NOT shared core.

These encode fiscal.ai's OWN quirks: a vendor label convention (`% Chg` / `Common Size` = computed
columns the filing never states) and a vendor plug threshold. Other channels must NOT inherit them.
Kept out of link_lib (the shared value/gate core) on purpose. Moves to driver/channels/fiscal_ai/ at
end-reorg. Self-check: `venv/bin/python scripts/driver_seed/fiscal_ai_rules.py`.
"""

PLUG_MAX = 1000   # a bare number this small is almost never a real KPI value in a fiscal.ai export


def is_derived(kpi):
    """fiscal.ai-computed rows (% change, common size). No filing states them -> never linkable."""
    return ('% Chg' in kpi) or ('%Chg' in kpi) or ('Common Size' in kpi)


def is_plug(value, fmt):
    """a tiny bare number fiscal.ai emits as filler; not a linkable fact."""
    return fmt in (None, 'number') and abs(float(value)) <= PLUG_MAX


if __name__ == '__main__':
    assert is_derived('Total Revenue % Chg.') and is_derived('Segment Revenue Common Size')
    assert not is_derived('iPhone Revenue') and not is_derived('Adjusted EBITDA')
    assert is_plug(12, 'number') and is_plug(1000, 'number')
    assert not is_plug(1001, 'number') and not is_plug(50, '%')   # % is not a plug (fmt gate)
    print('fiscal_ai_rules self-check OK')
