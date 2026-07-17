"""S3.5 FUSION — same-event fragment fusion on CANONICAL values (BUILD §11.4 v3.6;
order amended 2026-07-17: units are canonicalized BEFORE this stage — raw '1 billion'
and raw '1 million' must never look equal).

Law: fusion FILLS NULLS ONLY. A disagreement in ANY of the fixed ten value-signature
slots prevents fusion — the facts stand and enter the OD-8 ladder as in-batch
competitors (fusion promises no hashing). quote/state/date differences use the
writer's deterministic last-write-with-log rule (latest date, then the full LWW
tuple). A group that neither folds cleanly nor conflicts on every pair is AMBIGUOUS
and PARKS whole (FUSION_AMBIGUOUS). Permutation-identical by construction: groups and
members are processed in sorted order, never input order.
"""
from collections import namedtuple

from driver.core.driver_ids import norm, num_canon
from driver.core.driver_writer import SIGNATURE_FIELDS, _LWW_FIELDS, _NUMERIC_SIG, _TEXT_SIG

__all__ = ["FusedFact", "FusionPark", "fuse_event"]

FusedFact = namedtuple("FusedFact", "fact indexes logs")
FusionPark = namedtuple("FusionPark", "indexes code reason")


def _slot_canon(k, v):
    if v is None:
        return None
    if k in _NUMERIC_SIG:
        return num_canon(v)          # rejects floats loudly — validators run later anyway
    if k in _TEXT_SIG:
        return norm(str(v))
    return str(v)


def _conflicts(a, b):
    if (a.get("company_confirmed") is not None and b.get("company_confirmed") is not None
            and a["company_confirmed"] != b["company_confirmed"]):
        return True                  # True-vs-False confirmation is a REAL disagreement
    for k in ("level_shape_hint", "comparison_shape_hint"):
        if a.get(k) is not None and b.get(k) is not None and a[k] != b[k]:
            return True              # point-vs-range descriptions never fuse —
                                     # the fragments validate separately
    return any(
        _slot_canon(k, a.get(k)) is not None and _slot_canon(k, b.get(k)) is not None
        and _slot_canon(k, a.get(k)) != _slot_canon(k, b.get(k))
        for k in SIGNATURE_FIELDS)


_TIEBREAK = _LWW_FIELDS + ("level_shape_hint", "comparison_shape_hint") + SIGNATURE_FIELDS


def _rep_order(members):
    """The writer's deterministic representative rule: latest date first, ties broken
    by the FULL content tuple (LWW fields + hints + signature slots) — input order can
    never pick the survivor; a remaining tie means byte-identical content."""
    ordered = sorted(members,
                     key=lambda t: tuple(str(t[1].get(k)) for k in _TIEBREAK))
    return sorted(ordered, key=lambda t: t[1].get("date") or "", reverse=True)


def fuse_event(items):
    """items = [(input_index, group_key, fact_dict)] — post-units, pre-id.
    Returns (fused: [FusedFact], parked: [FusionPark]), deterministic under any
    input permutation. Singleton groups pass through untouched."""
    groups = {}
    for idx, key, fact in items:
        groups.setdefault(key, []).append((idx, fact))

    fused, parked = [], []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda t: t[0])
        if len(members) == 1:
            fused.append(FusedFact(members[0][1], (members[0][0],), []))
            continue
        pairs = [(a, b) for i, a in enumerate(members) for b in members[i + 1:]]
        conflict_count = sum(1 for a, b in pairs if _conflicts(a[1], b[1]))
        if conflict_count == 0:
            ordered = _rep_order(members)
            rep = dict(ordered[0][1])
            logs = []
            fill = SIGNATURE_FIELDS + ("level_shape_hint", "comparison_shape_hint",
                                       "company_confirmed")   # never lose a True
            for _, m in ordered[1:]:
                for k in fill:                      # fill nulls only, never overwrite
                    if rep.get(k) is None and m.get(k) is not None:
                        rep[k] = m[k]
                diffs = {k: m.get(k) for k in _LWW_FIELDS
                         if m.get(k) is not None and m.get(k) != rep.get(k)}
                if diffs:
                    logs.append({"op": "log", "event": "fused_fragment",
                                 "dropped_fields": diffs})
            fused.append(FusedFact(rep, tuple(i for i, _ in members), logs))
        elif conflict_count == len(pairs):
            for idx, fact in members:               # all stand — the OD-8 ladder decides
                fused.append(FusedFact(fact, (idx,), []))
        else:
            parked.append(FusionPark(
                tuple(i for i, _ in members), "FUSION_AMBIGUOUS",
                f"{len(members)} fragments neither fold cleanly nor conflict "
                f"pairwise-everywhere — never guess which fuse"))
    fused.sort(key=lambda f: f.indexes[0])
    parked.sort(key=lambda p: p.indexes[0])
    return fused, parked
