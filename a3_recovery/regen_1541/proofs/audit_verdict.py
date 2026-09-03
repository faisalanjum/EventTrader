"""The exhaustive audit's pass/fail rule, separated so it can be tested (SEQ 1557 3).

It lives apart from `exhaustive_audit.py` because that script performs the whole audit
at import time: a control cannot import it to ask what a FALSE row should do without
running the audit. The rule is the only thing worth testing here, so the rule is what
is importable.
"""


def verdict(totals, drift):
    """-> process exit status. Nonzero if ANY row failed or ANY cache drifted.

    Previously the audit printed `NOT ACCEPTABLE` and exited zero, so the ordered
    runner treated a failed audit as a passed step and froze the package anyway.
    """
    return 1 if (totals.get("FALSE") or totals.get("ERROR") or drift) else 0
