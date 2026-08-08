"""The matching law (package Part D) — order is normative.

THE PRINCIPLE: evidence identity, INCLUDING a verified locator, proves the same
source SPAN — never the same fact. Location is where; identity is what. Two
different facts can share one sentence, so a locator may confirm a link and can
never create one.

WHAT AUTO-LINKS: an exact complete canonical record + an exact locator, unique
BOTH ways. Nothing else. No fuzzy pre-screen, no quote-overlap fallback, no
value-equality shortcut — every one of those was a way for two different facts
to be scored as one.

NUMERIC SLOTS COMPARE AS THE THREE OBJECT FIELDS (value, scale_multiplier,
unit_scale_evidence), never as the converted scalar: $1.3 billion emitted as
1300 x 10^6 converts to the same 1300 m_usd but is a DIFFERENT reading of the
source, and must never grade as correct.
"""
from dataclasses import dataclass, field
from types import MappingProxyType

from driver.core.prepared_fact_v2 import ITEM_FIELDS, PreparedFactV2

# ONE owner for the numeric-slot inventory: prepared_fact_v2 exports it and
# this module asks for it (#827 step 5). The identical literal used to sit
# in both files — two lists that must agree forever, by hand.
from driver.core.prepared_fact_v2 import NUMERIC_SLOTS as _NUMERIC_SLOTS


def _canon_slot(slot):
    if slot is None:
        return None
    # The THREE object fields, RAW. There is deliberately no normalize() step:
    # Decimal already compares AND hashes 1.30 and 1.3 as equal, so
    # normalization bought nothing — while normalize() rounds at the context
    # precision, which made two DIFFERENT 29-digit values collapse into one key
    # and auto-link. A wrong answer scored as exact is the worst failure this
    # matcher can have, so the raw values are the key.
    return (slot["value"], slot["scale_multiplier"], slot["unit_scale_evidence"])


def _canon_value(name, v):
    if name in _NUMERIC_SLOTS:
        return _canon_slot(v)
    if isinstance(v, (list, tuple)):
        return tuple(_canon_value(name, x) for x in v)
    if isinstance(v, (dict, MappingProxyType)):
        # a FROZEN mapping is unhashable, so a deep-frozen polarity_proof
        # crashed the matcher outright; canonicalise it to a sorted tuple
        return tuple(sorted((k, _canon_value(name, x)) for k, x in v.items()))
    return v


def record_key(f):
    """The complete comparable identity of one fact: lane + per_x + all 32 item
    fields + the evidence locator. Hashable, so grouping is order-free by
    construction."""
    if not isinstance(f, PreparedFactV2):
        raise TypeError(f"expected PreparedFactV2, got {type(f).__name__}")
    item = tuple(_canon_value(k, getattr(f.item, k)) for k in ITEM_FIELDS)
    return (f.fact_type, f.per_x, item,
            (f.part_ref, f.occurrence_in_part, f.item.quote))


@dataclass
class MatchResult:
    links: list = field(default_factory=list)              # (gold, produced)
    link_keys: list = field(default_factory=list)
    gold_inconclusive: list = field(default_factory=list)  # duplicate-gold groups
    produced_duplicates: list = field(default_factory=list)
    to_grading_gold: list = field(default_factory=list)
    to_grading_produced: list = field(default_factory=list)
    emit_once_violation: bool = False

    @property
    def can_pass(self):
        """A run carrying an emit-once violation or an unresolved duplicate-gold
        group cannot PASS silently, however good its other numbers look."""
        return not self.emit_once_violation and not self.gold_inconclusive


def _group(facts):
    out = {}
    for f in facts:
        out.setdefault(record_key(f), []).append(f)
    return out


def match_facts(gold, produced):
    """Run the law in its normative order. Deterministic and order-free: the
    result depends only on the SETS of records, never on input order."""
    result = MatchResult()
    gold_groups, produced_groups = _group(gold), _group(produced)

    # 1. Duplicate GOLD detection comes FIRST — before any linking, so a
    #    first-match-wins race can never silently pick one of two identical
    #    golds. The whole group goes to adjudication.
    linkable_gold = {}
    for key, members in gold_groups.items():
        if len(members) > 1:
            result.gold_inconclusive.append(members)
        else:
            linkable_gold[key] = members[0]

    # 2. Produced duplicates collapse for COUNTING (no double credit) and are a
    #    visible emit-once contract violation.
    collapsed = {}
    for key, members in produced_groups.items():
        if len(members) > 1:
            result.produced_duplicates.append(members)
            result.emit_once_violation = True
        collapsed[key] = members[0]

    # 3. AUTO-LINK: identical complete record + identical locator, unique both
    #    ways. Keys make the bijection structural rather than a search.
    for key in sorted(set(linkable_gold) & set(collapsed), key=repr):
        result.links.append((linkable_gold[key], collapsed[key]))
        result.link_keys.append(key)

    # 4. EVERYTHING else goes to build-time grading — no filter, no shortcut.
    #    Output is CANONICALLY ORDERED by the record key: an earlier version
    #    emitted in input order, so the same two sets produced different-looking
    #    results depending on how they arrived.
    linked = set(result.link_keys)
    unmatched_gold = [(k, g) for k, g in linkable_gold.items() if k not in linked]
    for group in result.gold_inconclusive:
        unmatched_gold += [(record_key(g), g) for g in group]
    result.to_grading_gold = [g for _, g in sorted(unmatched_gold, key=lambda kv: repr(kv[0]))]
    result.to_grading_produced = [p for _, p in sorted(
        ((k, p) for k, p in collapsed.items() if k not in linked),
        key=lambda kv: repr(kv[0]))]
    result.gold_inconclusive.sort(key=lambda grp: repr(record_key(grp[0])))
    result.produced_duplicates.sort(key=lambda grp: repr(record_key(grp[0])))
    return result
