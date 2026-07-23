"""The backfill handoff gate (Design D14-v3, locked; Phase-5 item 4).

`backfill_candidate_driver_name` is one OPTIONAL, CORE-ONLY suggestion per
internal fact (Driver.name IS the unique key — no separate id exists), riding
the existing item/fact provenance as a plain side record. It is NEVER a public
packet field (the frozen PreparedFactV1 rejects it as unknown) and never a
registry. This module is the ONE pure gate the future S4 kernel calls; the
`reconfirmed` verdict is the kernel's own judgment FROM OLD-SOURCE EVIDENCE
ALONE (recorded during rehearsal, real at S4) — this gate never judges
evidence itself, it only enforces the handoff law fail-closed.
"""
from collections import namedtuple

from driver.core.driver_ids import valid_driver_name

__all__ = ["BackfillDecision", "backfill_gate"]

BackfillDecision = namedtuple("BackfillDecision", "driver_name reason")


def backfill_gate(candidates, *, reconfirmed):
    """EXACTLY one candidate may pass, and only reconfirmed (D14-v3):
    zero -> no_candidate (nothing is ever forced) · more than one entry ->
    ambiguous_multiple (duplicates included — dedup would be a silent
    judgment) · malformed -> malformed_candidate · the single candidate
    attaches ONLY on reconfirmed=True; False -> reconfirmation_failed;
    anything else -> reconfirmation_missing. Fail closed everywhere."""
    cands = list(candidates)
    if not cands:
        return BackfillDecision(None, "no_candidate")
    if len(cands) > 1:
        return BackfillDecision(None, "ambiguous_multiple")
    name = cands[0]
    if not valid_driver_name(name):           # THE one NAME-05 predicate —
        return BackfillDecision(None, "malformed_candidate")   # never cleaned
    if reconfirmed is True:
        return BackfillDecision(name, "reconfirmed")
    if reconfirmed is False:
        return BackfillDecision(None, "reconfirmation_failed")
    return BackfillDecision(None, "reconfirmation_missing")
