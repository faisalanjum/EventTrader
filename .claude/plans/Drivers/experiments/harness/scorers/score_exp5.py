"""score_exp5 v5 — EXP-5 scoring per the work-order §4 pinned logic
(FableExperimentWorkOrder :641-643), round-13 adversarial corrections applied.

Pipeline per arm:
 1. MATCH produced items <-> du_worthy gold (same event) through the ONE
    identity owner, `fact_match.record_key`: an auto-link needs an IDENTICAL
    complete V2 record plus an identical evidence locator. The retired
    20-char quote OVERLAP and canonical VALUE-EQUALITY rules are GONE — both
    could link two genuinely different facts, and B-15 forbids value equality
    from linking at all. Everything not auto-linked goes to the qualified
    grader; only its VALIDATED one-to-one rulings add pairs.
 2. recall = unambiguously-matched gold / du_worthy gold.
 3. the PUBLIC route's own decisions -> would_park (B-16: the scorer runs
    no rule engine of its own; only a public `parked` row counts).
    HOME-FACT (owner pin 2026-07-24): a produced surprise requires, in the
    SAME event, a produced fact on the basis-correct lane (actual->metric,
    guidance->guidance) whose driver is the surprise's BASE driver
    (terminal `_surprise` stripped), with the SAME resolved period, and the
    SAME canonical value when the surprise carries numbers. Numberless
    surprises are checked too. An unrelated metric never qualifies.
 4. Field accuracy on matched pairs: code-comparable fields + slice as SETS +
    measurement as OD-9-normalized token sets + canonical value slots
    (level/comparison with level's unit; change with change_unit_raw).
 5. wrong_lane per the pinned definition (wrong lane / missing gold twin).
 6. MEANING fields (driver_state, lane routing incl. twin presence, OD-13
    favorability, OD-11 basis, slice-vs-menu) REQUIRE grader verdicts for
    every matched pair: PASS stays None (INCOMPLETE) until they are complete.
 7. Per-OD-rule error table emitted.
 8. Two-run union: DEDUPLICATED item union BEFORE matching; presence
    disagreement = captured-by-exactly-one / captured-by-either.
 9. Final gate: (single>=0.95 OR union>=0.98) && wrong_lane==0 &&
    value_shape_acc>=0.98 && state_acc>=0.95 && would_park<=0.10.

No CLI entry point: `--dry3` and its demo were deleted with the V1 residue
(SEQ 1131). The pytest suite is the check.
"""
import json
import os as _os
import sys

_REPO = _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)),
    "..", "..", "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
from decimal import Decimal                                             # noqa: E402

from driver.core.driver_ids import dec_canon, norm as _norm             # noqa: E402
from driver.core.driver_period_resolver import (PeriodResolutionError,  # noqa: E402
                                                ensure_driver_period)


#: WorkOrder §649 gives the GRADER the meaning fields — `driver_state`, lane
#: routing, OD-13 favorability, OD-11 basis, and slice pick-vs-menu. Those are
#: the only exclusions from direct code accuracy; everything else in the frozen
#: V2 item set is code-comparable.
GRADER_OWNED = ("driver_state", "surprise_basis_hint",
                "has_favorability_wording", "polarity_proof")


#: The two item fields with their OWN specialized comparison: `slice_parts` is
#: compared as a SET (membership, not order) and `measurement_raw_spans` through
#: the OD-9 span owner. Named here once, and SUBTRACTED from the generic pool so
#: they are measured exactly once rather than in both places.
SPECIALIZED_COLLECTIONS = ("slice_parts", "measurement_raw_spans")

#: The fact-level measurements WorkOrder §649 names alongside the item fields.
#: `fact_type` also feeds the separate hard `wrong_lane` gate, which is kept.
FACT_LEVEL_FIELDS = ("fact_type", "per_x")


def _code_fields():
    """The generic pooled item fields, taken MECHANICALLY from the frozen V2 set.

    Never a copied 32-field list (Codex SEQ 1131): a hand-written copy is how
    the four retired unit/money hints — deleted from V2 with no successor —
    were still being compared here long after they stopped existing.

    EXACTLY-ONCE (Codex SEQ 1132.1): the numeric slots and the two specialized
    collections are subtracted, because each already has its own comparison
    below. Leaving them in pooled them AND counted them again in their
    specialized form, silently double-weighting those fields.
    """
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, NUMERIC_SLOTS
    excluded = set(GRADER_OWNED) | set(NUMERIC_SLOTS) | set(SPECIALIZED_COLLECTIONS)
    excluded.add("quote")                     # evidence, not a scored field
    return [f for f in ITEM_FIELDS if f not in excluded]


CODE_FIELDS = _code_fields()


def field_accounting():
    """Every frozen fact-level + item field, mapped to the ONE place it is
    measured. Derived, never a copied schema list — so a new V2 field shows up
    as unaccounted instead of silently going unscored (Codex SEQ 1132)."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, NUMERIC_SLOTS
    where = {}
    for f in FACT_LEVEL_FIELDS:
        where[f] = "fact_level"
    for f in ITEM_FIELDS:
        if f == "quote":
            where[f] = "evidence_locator"
        elif f in GRADER_OWNED:
            where[f] = "grader_owned"
        elif f in NUMERIC_SLOTS:
            where[f] = "numeric_slot_exact"
        elif f in SPECIALIZED_COLLECTIONS:
            where[f] = "specialized_collection"
        else:
            where[f] = "pooled"
    return where
MEANING_FIELDS = ["driver_state", "lane_routing", "favorability_od13",
                  "basis_od11", "slice_vs_menu"]
OD_RULES = ["OD-9", "OD-11", "OD-12", "OD-13", "OD-14", "OD-21", "ISS-16",
            "shapes", "slices"]


_RULE_OF = {
    # mismatch/verdict field names (lowercase)
    "level_shape_hint": "shapes", "comparison_shape_hint": "shapes",
    "slice": "slices", "slice_vs_menu": "slices",
    "measurement-OD-9": "OD-9",
    "driver_state": "OD-14", "favorability_od13": "OD-13",
    "basis_od11": "OD-11", "lane_routing": "ISS-16",
    "surprise_basis_hint": "OD-21", "comparison_baseline": "ISS-16",
    "value_text": "OD-14", "conditions": "OD-14",
    "company_confirmed": "OD-14",
    "value:level": "OD-12", "value:comparison": "OD-12",
    "value:change": "OD-12", "driver_name": "other",
    "matched": "ISS-16", "missing_gold_twin": "ISS-16",
}


def _bucket(code):
    """ACTUAL code -> pinned rule bucket; both code styles covered
    (uppercase park codes + lowercase field names); unmapped -> other."""
    c = code.split(":", 1)[1] if ":" in code else code
    if c in _RULE_OF:
        return _RULE_OF[c]
    if c.startswith("value:"):
        return "OD-12"
    if c.startswith(("LEVEL_", "COMPARISON_")):
        return "shapes"
    if c.startswith(("SURPRISE_", "IMPOSSIBLE_", "HOME_FACT")):
        return "OD-21"
    if len(c) > 1 and c[0] == "F" and c[1:].isdigit():
        # B-16: the rollup now reads the ROUTE's real codes. The retired
        # scorer-invented spellings above (HOME_FACT_MISSING, SURPRISE_*) are
        # what the deleted engine emitted; production emits F1..F9 for the same
        # family. `driver_validators` says so in its own module docstring —
        # "FACT-16 deterministic validators + the OD-21 surprise machinery" — so
        # this is a like-for-like vocabulary swap, NOT a new rule and NOT a
        # restructured table. Without it every route code fell into "other" and
        # the rule table silently stopped counting the surprise family.
        return "OD-21"
    if c.startswith(("CHANGE_UNIT", "UNIT_REQUIRED")):
        return "OD-12"
    if c.startswith("LANE_"):
        return "ISS-16"
    if c.startswith("VALUE_TEXT"):
        return "OD-14"
    if c.endswith(("unit_kind_hint", "money_mode_hint")):
        return "OD-12"
    return "other"


def _item(f):
    """THE V2 item. It used to be `f.get("gold_item", f)`, which on a V2 fact
    found no wrapper and returned the WHOLE FACT — so every item-field lookup
    (`level_low`, `period_scope`, ...) read None on both sides and the
    comparison "agreed" while comparing nothing (Codex SEQ 1131.1)."""
    return (f.get("item") or {}) if isinstance(f, dict) else {}


class ExactValueError(ValueError):
    """A value reached scoring in a form that cannot be compared exactly."""


def _dec(v):
    """The EXACT numeric path: int and Decimal only.

    Drafts are parsed with `parse_float=Decimal`, so a float here means digits
    were already lost upstream — production rejects floats outright, and so do
    we. The old `Decimal(repr(v))` float bridge is GONE (it laundered a contract
    violation), and so is the silent `return None` tail that made a Decimal —
    the very type the transport now produces — VANISH from every comparison."""
    if v is None:
        return None
    if isinstance(v, bool):
        raise ExactValueError("bool is not a number")
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, Decimal):
        if not v.is_finite():
            raise ExactValueError(f"non-finite Decimal {v}")
        return v
    raise ExactValueError(
        f"{type(v).__name__} cannot be compared exactly — parse with "
        f"parse_float=Decimal (floats lose digits)")


def _canon_item_values(item):
    """The EXACT V2 numeric-slot view — the three raw object fields, unconverted.

    B-16 / WorkOrder §649: EXP-5 field truth is the numeric OBJECT
    `(value, scale_multiplier, unit_scale_evidence)` compared EXACTLY. Converted
    scalars serve storage and XBRL truth-comparison, never field scoring.

    This replaces a call into `driver_units.resolve_driver_units` that treated
    slots as scalars, passed the four DELETED unit/money hints, and fell back to
    unscaled values on a resolution failure — three separate ways for two facts
    to compare equal while differing (Codex SEQ 1131.4). There is no resolver
    here, no inferred unit and no fallback: a slot either matches field for
    field or it does not.

    Returns {slot_name: None | (value, scale_multiplier, unit_scale_evidence)}
    over the FROZEN `NUMERIC_SLOTS`, so a new slot is picked up automatically
    and a retired one disappears without a hand edit.
    """
    from driver.core.prepared_fact_v2 import NUMERIC_SLOTS
    from driver.core.slot_convert import SLOT_KEYS
    out = {}
    for name in NUMERIC_SLOTS:
        slot = item.get(name)
        if slot is None:
            out[name] = None
        elif isinstance(slot, dict):
            out[name] = tuple(slot.get(k) for k in SLOT_KEYS)
        else:
            # a bare scalar is NOT a V2 slot; refusing beats silently comparing
            # a number against an object and calling them different
            raise ExactValueError(
                f"{name} is {type(slot).__name__}, not a V2 numeric slot object")
    return out


def _canon_level(item):
    return [_canon_item_values(item)[k]
            for k in ("level_low", "level_high")]


def _meas_tokens(item):
    spans = item.get("measurement_raw_spans") or []
    return {_norm(s) for s in spans if isinstance(s, str) and _norm(s)}


def _ev_key(f):
    """EXACT evidence identity — no fuzz, no window, no substring.

    Preferred: the audit-only `evidence_locator` (part_ref + occurrence_in_part)
    plus the verbatim quote. Fallback when a fact carries no locator: EXACT quote
    string equality. Both are mechanical equality; the deleted `_overlap(n=20)`
    was a 20-character sliding window that could link two unrelated sentences
    sharing a boilerplate run ("for the quarter ended").

    An evidence match still only means SAME SPAN, never same fact — one sentence
    can carry several facts, so the graph/grader still decides identity."""
    it = _item(f)
    loc = it.get("evidence_locator") or (f.get("evidence_locator")
                                         if isinstance(f, dict) else None)
    q = (f.get("quote") if isinstance(f, dict) else None) or it.get("quote")
    if not q:
        return None
    if isinstance(loc, dict) and loc.get("part_ref"):
        return ("loc", loc["part_ref"], loc.get("occurrence_in_part"), q)
    return ("quote", q)


# `_value_eq` DELETED (B-15 / Codex SEQ 1110). It let VALUE EQUALITY link two
# records — exactly what B-15 forbids, since two genuinely different facts can
# share a value. `fact_match.record_key` is the one identity owner; it had zero
# callers left here, so nothing replaces it.


def _shape_pair(item):
    """POSITIONAL exact (low, high) — a point (5,5) is NOT a floor (5,None).

    Each endpoint is the slot's exact three-field object, so two facts agree on
    shape only when they agree on value AND scale AND the scale's evidence.
    """
    slots = _canon_item_values(item)
    lo, hi = slots.get("level_low"), slots.get("level_high")
    return (lo, hi) if (lo is not None or hi is not None) else None


# THE ORACLE'S OWN NAME-17 SPELLINGS (FINAL_DESIGN NAME-17: terminal
# `_guidance` / `_surprise`; strip once). INDEPENDENT COPY on purpose —
# this scorer grades production, so it must never import the production
# splitter: a shared defect would deform both sides identically and
# false-green exactly when the scorer must fail.
_ORACLE_SURPRISE_SUFFIX = "_surprise"
_ORACLE_GUIDANCE_SUFFIX = "_guidance"


def _base_driver(name):
    name = name if isinstance(name, str) else ""
    return (name[:-len(_ORACLE_SURPRISE_SUFFIX)]
            if name.endswith(_ORACLE_SURPRISE_SUFFIX) else name)


def _resolved_period(item, lane, fye):
    try:
        r = ensure_driver_period(item, fact_type=lane or "metric",
                                 fye_month=fye)
        return r and r.get("period_u_id")
    except (PeriodResolutionError, TypeError, ValueError, AttributeError):
        return None


def _name_agrees(g_fact, p_fact):
    """Mechanical (never semantic) base-name equality — normalized, terminal
    `_surprise` stripped. ANNOTATION ONLY: it enriches a grader row, it never
    decides a match."""
    gn = _norm(_base_driver(_item(g_fact).get("driver_name") or ""))
    pn = _norm(_base_driver(_item(p_fact).get("driver_name") or ""))
    return bool(gn) and gn == pn


from driver.core.driver_writer import FakeGraph as _PreBatchGraph


class _ReplayStore(_PreBatchGraph):
    """A temporary READ-ONLY store for ONE replay (Codex SEQ 1126.7).

    Built AFTER the reply, from that reply's OWN unique `(driver_name,
    fact_type)` pairs plus the event's source/company. It exists so the scorer
    can reach the pinned public `run_event` without importing a Core TEST
    fixture into runtime code, which SEQ 1126.7 forbids.

    Read-only is enforced, not merely intended: `transaction()` refuses. The
    caller always passes `enable_writes=False`, so a transaction here would mean
    the route tried to write during scoring, and failing loudly beats silently
    buffering an op nobody reads.
    """

    def __init__(self, drivers, source, companies):
        # The EMPTY pre-batch graph view. `_PreBatchGraph` is
        # `driver_writer.FakeGraph` — PRODUCTION code, documented as the
        # "in-memory pre-batch graph view for tests/dry-runs (same read surface
        # the real adapter must expose)". It supplies `get_sibling_facts` and
        # `get_period`, which the writer reaches through this same object.
        # Core's `FakeStore` would ALSO have supplied them, but it lives in a
        # Core TEST module and SEQ 1126.7 bars importing one into runtime code.
        super().__init__()
        self._drivers, self._source, self._companies = drivers, source, companies

    def get_source(self, source_id):
        return self._source

    def get_source_companies(self, source_id):
        return self._companies

    def get_driver(self, name):
        return self._drivers.get(name)

    def get_prior_guide_units(self, fact):
        """Empty prior set for this deliberately EMPTY temporary pre-batch graph.

        The pinned route reads this for a numberless guidance
        withdrawal/reaffirmation (OD-10 series_unit). Returning the empty list
        states NO semantic rule — it inspects no name and no text; it simply
        reports that this scratch graph holds no prior guide, which is true by
        construction. The route's own fail-closed handling then owns the
        outcome. Missing this method raised AttributeError instead of returning
        a public row (Codex SEQ 1127).
        """
        return []

    def get_company_slice_menu(self, source_id, date):
        return {"xbrl_members": [], "used_scopes": []}

    def get_xbrl_fact_dimensions(self, source_id, concept):
        from driver.core.driver_neo4j_adapter import GraphFactRows
        return GraphFactRows(rows=[], exclusions=())

    def transaction(self):
        raise RuntimeError(
            "the scoring replay store is READ-ONLY: run_event was reached with "
            "writes enabled, which scoring must never do")


def _replay_drivers(reply):
    """The reply's own unique `(driver_name, fact_type)` pairs.

    A name carrying two different fact_types in one reply FAILS LOUDLY — silently
    keeping one would hand the route a fabricated registry and quietly change
    which facts pair with which home.
    """
    drivers = {}
    for fact in reply.get("facts") or []:
        name = (fact.get("item") or {}).get("driver_name")
        if name is None:
            continue
        fact_type = fact.get("fact_type")
        prior = drivers.get(name)
        if prior is not None and prior["fact_type"] != fact_type:
            raise ValueError(
                f"reply gives driver {name!r} conflicting fact_types "
                f"{prior['fact_type']!r} and {fact_type!r}; the replay store "
                f"cannot invent which one the graph holds")
        drivers[name] = {"name": name, "fact_type": fact_type}
    return drivers


def route_reply(reply, event, audit_dir):
    """Replay ONE reply through the PINNED public route and return the exact
    result plus the exact index map (Codex SEQ 1126.7).

    This is the UPSTREAM operation. It lives beside the other replay helpers on
    purpose — no new module — and it is the only thing that calls `run_event`.
    `score_arm` consumes what this returns and never routes anything itself.
    """
    from driver.core.driver_write_cli import run_event
    from driver.core.prepared_fact_v2 import verify_occurrence
    parts = {p["part"]: p["content"] for p in event.get("text_parts", [])}
    for i, abstention in enumerate(reply.get("abstentions") or []):
        part_ref = abstention.get("part_ref")
        if part_ref not in parts:
            raise ValueError(f"abstention[{i}] names unknown part {part_ref!r}")
        bad = verify_occurrence(parts[part_ref], abstention.get("quote") or "",
                                abstention.get("occurrence_in_part"))
        if bad:
            # THE ONE occurrence owner (SEQ 1135) — no second quote rule is
            # written here. An abstention with an unsound locator is refused at
            # the seam, because a reply that cannot say WHERE it declined is not
            # a lawful reply to route.
            raise ValueError(f"abstention[{i}] locator: {bad}")
    items, reader = replay_reader(reply)
    _, index_map = project_replay_items(reply)
    source = {"date": event["event_time"], "source_type": event["source_type"],
              "ticker": event["ticker"], "fye_month": event["fye_month"]}
    store = _ReplayStore(_replay_drivers(reply), source, [event["ticker"]])
    result = run_event({**event, "items": items}, store=store,
                       audit_dir=audit_dir, enable_writes=False, reader=reader)
    return {"result": result, "index_map": index_map}


def _to_v2_with_positions(records):
    """Convert scorer dicts to the records Core's matcher requires, keeping an
    `id(instance) -> original index` sidecar (SEQ 1108).

    `match_facts` hands back the SAME instances it was given, so identity is the
    only honest way to recover a record's original position. Equality,
    `list.index`, `record_key`, the locator or value/quote logic would each
    either conflate duplicates or re-implement matching — the very engine this
    change deletes. Transport bookkeeping; it states no rule.
    """
    from driver.core.prepared_fact_v2 import PreparedFactV2
    from kf_lint import GOLD_ONLY          # THE owner of the gold-only field set
    converted, position = [], {}
    for i, rec in enumerate(records):
        # A GOLD fact is the exact V2 model fact plus ONLY `kf_lint.GOLD_ONLY`
        # (du_worthy, gold_extra, ambiguity_note). Strip that imported owner set
        # mechanically — never a copied three-key list here, and never by
        # weakening `from_dict`. Produced facts carry none of them and pass
        # through unchanged.
        obj = PreparedFactV2.from_dict(
            {k: v for k, v in rec.items() if k not in GOLD_ONLY})
        position[id(obj)] = i
        converted.append(obj)
    return converted, position


def dedup_items(items):
    """Union dedup through the ONE identity owner, `fact_match.record_key`.

    B-16: the retired key was canonical JSON over `lane` + outer quote + item.
    `lane` no longer exists, so that key silently collapsed to `None` for every
    fact and identity rested on the item alone. `record_key` is the same owner
    the matcher uses, so a union can never disagree with a match about whether
    two facts are the same fact.
    """
    from driver.core.fact_match import record_key
    from driver.core.prepared_fact_v2 import PreparedFactV2
    from kf_lint import GOLD_ONLY
    seen, out = set(), []
    for f in items:
        key = record_key(PreparedFactV2.from_dict(
            {k: v for k, v in f.items() if k not in GOLD_ONLY}))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


#: Addendum-A extras buckets. EXACTLY these three, no other bucket and no string
#: heuristic: `duplicate` (already mechanically collapsed), `key_miss` (a genuine
#: gold-key miss -> the run is INCONCLUSIVE, not failed), and `unsupported` (a
#: fact the source does not support -> a CONFIRMED-WRONG ACCEPTED fact).
EXTRAS_BUCKETS = ("duplicate", "key_miss", "unsupported")


def classify_extras(verdicts, sid, accepted_unmatched):
    """Validate ONE fake extras verdict per unmatched ROUTE-ACCEPTED produced
    fact (Codex SEQ 1133).

    Only route-ACCEPTED facts are eligible: a parked, rejected or skipped row is
    reported elsewhere but must never enter the accepted-fact safety count —
    the system already refused it, so counting it as a wrong ACCEPTANCE would
    punish the safety gate for working.

    Returns `(tally, problems)`. Fake verdicts only; nothing here calls a grader
    or an AI, and nothing infers a bucket from text.
    """
    problems = []
    eligible = set(accepted_unmatched)
    if verdicts is None:
        # Same hole as the rulings path: an unmatched route-WRITTEN fact with no
        # verdict is INCOMPLETE, not clean. With nothing eligible — including a
        # run whose extras were all parked/rejected/skipped — supplying no
        # verdict is lawfully complete.
        return ({b: 0 for b in EXTRAS_BUCKETS},
                [{"sid": sid, "reason": "extras_verdict_missing",
                  "produced_idx": i} for i in sorted(eligible)])
    mine = {i: v for (s, i), v in verdicts.items() if s == sid}
    for idx in sorted(set(mine) - eligible):
        problems.append({"sid": sid, "reason": "extras_verdict_out_of_range",
                         "produced_idx": idx})
    for idx in sorted(eligible - set(mine)):
        problems.append({"sid": sid, "reason": "extras_verdict_missing",
                         "produced_idx": idx})
    tally = {b: 0 for b in EXTRAS_BUCKETS}
    for idx in sorted(eligible & set(mine)):
        bucket = mine[idx]
        if bucket not in EXTRAS_BUCKETS:
            problems.append({"sid": sid, "reason": "extras_verdict_malformed",
                             "produced_idx": idx, "bucket": bucket})
        else:
            tally[bucket] += 1
    return tally, problems


def reconcile_rulings(first, second):
    """Two INDEPENDENT grader inputs produce a scorable ruling only where they
    AGREE (Codex SEQ 1133/1134).

    The smallest existing reconciliation seam — no grader framework: agreement
    is dict equality on the same key. A key present in one input only, or
    carrying different answers, yields NO ruling, so the pair stays unmatched
    and the run stays INCOMPLETE. Silently preferring one input would be the
    scorer choosing between two qualified graders, which is not its call.

    Returns `(agreed, disagreements)`.
    """
    if first is None or second is None:
        return None, []
    agreed, disagreements = {}, []
    for key in sorted(set(first) | set(second), key=repr):
        a, b = first.get(key, _ABSENT), second.get(key, _ABSENT)
        if a is _ABSENT or b is _ABSENT or a != b:
            disagreements.append({"sid": key[0], "reason": "ruling_disagreement",
                                  "gold_idx": key[1],
                                  "answers": [None if a is _ABSENT else a,
                                              None if b is _ABSENT else b]})
        else:
            agreed[key] = a
    return agreed, disagreements


_ABSENT = object()


def _locator(record, item=None):
    """The EXACT evidence locator: (part_ref, occurrence_in_part, quote).

    The same triple `fact_match.record_key` uses, so an abstention and a gold
    fact are "the same evidence" here on exactly the terms the matcher uses.
    """
    src = item if item is not None else record
    return (record.get("part_ref"), record.get("occurrence_in_part"),
            src.get("quote"))


def classify_abstentions(abstentions, gold_facts, unmatched_gold):
    """Split abstentions into GOLD-LINKED, DIAGNOSTIC and INVALID-LOCATOR.

    Codex SEQ 1126.5 / 1135. A gold-linked abstention — the producer declined on
    evidence that carries a real gold fact — enters BOTH the would-park
    numerator and its denominator, and remains a recall miss: declining to
    answer is not the same as being right. A diagnostic abstention, on evidence
    no gold covers, enters NEITHER but is still reported; charging it would
    punish a producer for correctly saying nothing about a non-fact.

    The split comes from the record's own LOCATOR, never from the spelling of a
    route decision — every lawful abstention shares the one `skipped` decision,
    so a decision-derived split would put them all in one bucket.

    THREE THINGS THIS OWES ITS AUTHORITY (SEQ 1135):
      * the locator is validated by `prepared_fact_v2.verify_occurrence` against
        the EXACT NAMED PART — no second quote/occurrence rule is written here;
      * a gold abstention links ONE-TO-ONE to an otherwise-UNMATCHED gold fact,
        so two abstentions can never both claim the same gold row and be charged
        twice for one miss;
      * an unsound locator is neither linked nor diagnostic: it is a problem.
    """
    available = {}
    for gi in unmatched_gold:
        available.setdefault(_locator(gold_facts[gi], _item(gold_facts[gi])),
                             []).append(gi)

    linked, diagnostic = [], []
    for i, abstention in enumerate(abstentions):
        # LOCATOR SOUNDNESS IS PROVEN UPSTREAM by `route_reply`, through the
        # `prepared_fact_v2.verify_occurrence` owner and the exact named part.
        # It cannot be checked here: SEQ 1126.2 says a route entry carries ONLY
        # the result and the index map, so the scorer has no part text. Raised
        # to Codex rather than smuggling the event in as a third key.
        key = _locator(abstention)
        if available.get(key):
            linked.append((i, available[key].pop(0)))   # ONE-TO-ONE
        else:
            diagnostic.append(i)
    return linked, diagnostic


def grade_unmatched(rulings, sid, unmatched_gold, unmatched_produced):
    """Validate the build-time grader's one-to-one gold<->produced rulings.

    WorkOrder §649 sends every UNMATCHED gold and produced fact to the qualified
    grader, because `match_facts` auto-links only IDENTICAL complete records —
    so any fact carrying a real field error is unmatched by construction and
    would otherwise never reach field scoring at all (Codex SEQ 1132.2).

    This validates rulings; it never SUGGESTS one. No quote or value heuristic,
    no revived candidate matcher: an unmatched pair is linked here only because
    a qualified grader said so, by index.

    A ruling is `{(sid, gold_idx): produced_idx or None}`. `None` means "no
    produced fact corresponds" — a decided MISS, which is valid and still counts
    against recall. Returns `(valid_pairs, problems)`; any problem blocks PASS,
    because a scorer that proceeds on a malformed ruling is inventing the
    grader's answer.
    """
    problems = []
    pending_gold, pending_prod = set(unmatched_gold), set(unmatched_produced)
    if rulings is None:
        # THE GRADER WAS NOT RUN. My earlier claim that existing accounting
        # covered this was WRONG and Codex verified it: a raw unmatched row
        # increments neither `ambiguities_unresolved` nor `verdicts_missing`,
        # and `potential_recall` omits it — so an unrun grading could PASS with
        # unmatched gold sitting there ungraded.
        #
        # A ruling is REQUIRED exactly when unmatched gold exists. With none,
        # not running the grader is lawfully complete.
        return [], [{"sid": sid, "reason": "ruling_missing", "gold_idx": g}
                    for g in sorted(pending_gold)]
    mine = {g: p for (s, g), p in rulings.items() if s == sid}

    for gold_idx in sorted(set(mine) - pending_gold):
        problems.append({"sid": sid, "reason": "ruling_out_of_range",
                         "gold_idx": gold_idx})
    for gold_idx in sorted(pending_gold - set(mine)):
        # rulings WERE supplied for this run, so an unmatched gold left unruled
        # is an INCOMPLETE grader answer and blocks PASS
        problems.append({"sid": sid, "reason": "ruling_missing",
                         "gold_idx": gold_idx})

    claimed, valid = {}, []
    for gold_idx in sorted(pending_gold & set(mine)):
        produced_idx = mine[gold_idx]
        if produced_idx is None:
            continue                       # a DECIDED miss: valid, no pair
        if produced_idx not in pending_prod:
            problems.append({"sid": sid, "reason": "ruling_out_of_range",
                             "gold_idx": gold_idx, "produced_idx": produced_idx})
        elif produced_idx in claimed:
            # one produced fact credited to two golds is exactly the double
            # credit the emit-once law exists to prevent
            problems.append({"sid": sid, "reason": "ruling_duplicate_produced",
                             "produced_idx": produced_idx,
                             "gold_idxs": [claimed[produced_idx], gold_idx]})
        else:
            claimed[produced_idx] = gold_idx
            valid.append((gold_idx, produced_idx))
    return valid, problems


def _rows_for_event(route, sid, n_facts, n_abstentions):
    """Validate ONE event's completed route and return {(kind, i): outcome row}.

    Codex SEQ 1126.3 — every one of these is a REFUSAL, never a repair:
      * the routed result must carry each outcome index exactly once;
      * the index map must point only at rows the result actually has;
      * every emitted fact and abstention needs exactly one mapped row.
    A scorer that quietly tolerates any of these is attributing a decision to a
    record that did not produce it, which is worse than refusing to score.
    """
    entry = route[sid]
    if set(entry) != {"result", "index_map"}:
        raise ValueError(f"route[{sid!r}] must carry exactly result and index_map, "
                         f"got {sorted(entry)}")
    items = entry["result"]["items"]
    seen = [r["index"] for r in items]
    if len(seen) != len(set(seen)):
        raise ValueError(f"route[{sid!r}] repeats outcome index(es) "
                         f"{sorted(i for i in set(seen) if seen.count(i) > 1)}")
    rows = {r["index"]: r for r in items}
    index_map = entry["index_map"]
    missing = [k for k, v in index_map.items() if v not in rows]
    if missing:
        raise ValueError(f"route[{sid!r}] maps {missing} onto absent outcome rows")
    expected = {("fact", i) for i in range(n_facts)}
    expected |= {("abstention", i) for i in range(n_abstentions)}
    if set(index_map) != expected:
        raise ValueError(
            f"route[{sid!r}] maps {sorted(set(index_map) ^ expected)} — every "
            f"emitted fact and abstention needs exactly one mapped row")
    if len(set(index_map.values())) != len(index_map) or set(rows) != set(index_map.values()):
        raise ValueError(f"route[{sid!r}] rows and map are not a bijection")
    return {k: rows[v] for k, v in index_map.items()}


def invalid_response_stats(responses):
    """The WorkOrder's reliability gate: invalid-response rate and its
    rule-of-three bound (step3 §10).

    `responses` is `{"total": N, "invalid": K}` — the counts the RUNNER
    observes. Step 3 makes no model call, so in this step the rate is
    NOT APPLICABLE rather than zero: reporting 0% for zero responses would be
    inventing data about reliability nobody measured.

    RULE OF THREE: with K == 0 observed failures in N trials, the 95% upper
    bound on the true rate is 3/N. A run of 156 clean replies does NOT show a 0%
    failure rate — it shows at most ~1.9%. Reported so a small clean run cannot
    be read as proof of reliability it does not carry.
    """
    if not responses:
        return {"applicable": False, "rate": None, "upper95": None,
                "why": "no responses observed — Step 3 makes no model call"}
    total = responses.get("total") or 0
    invalid = responses.get("invalid") or 0
    if total <= 0:
        return {"applicable": False, "rate": None, "upper95": None,
                "why": "zero responses"}
    return {"applicable": True, "rate": invalid / total,
            "upper95": (3.0 / total) if invalid == 0 else None,
            "total": total, "invalid": invalid}


def passes_official_bars(*, recall, lane_wrong, wrong_name, value_shape_acc,
                         state_acc, would_park, safety_result,
                         invalid_response_rate=None):
    """THE OFFICIAL BARS, in ONE place.

    Factored out so the boundary controls can drive the REAL expression instead
    of re-copying it into a test (Codex SEQ 1143). A copied expression is a
    second rule owner: it can agree with itself while the scorer does something
    else, and a source-text search cannot tell a live fragment from a dead or
    reordered one.

    Every bar is INCLUSIVE at its own value — `>=` on the minimums, `<=` on the
    park maximum — so a run that exactly meets a bar passes it. Safety is ANDed
    in, never averaged.
    """
    # THE RELIABILITY GATE (§10): at most 2% invalid responses. `None` means
    # NOT APPLICABLE — Step 3 observes no responses at all — and an
    # inapplicable metric cannot be read as a passing one, so it neither passes
    # nor fails this bar here; a real run supplies the counts.
    if invalid_response_rate is not None and invalid_response_rate > 0.02:
        return False
    return (recall >= 0.95 and lane_wrong == 0 and wrong_name == 0
            and value_shape_acc >= 0.98 and state_acc >= 0.95
            and would_park <= 0.10
            and safety_result == "PASS")


def score_arm(gold_by_event, arm_by_event, event_meta,
              grader_verdicts=None, ambiguity_resolutions=None, *, route,
              extras_verdicts=None):
    """event_meta MANDATORY per event. grader_verdicts: {(sid, gold_idx):
    {meaning_field: bool}} — required for EVERY matched pair. ambiguity_
    resolutions: {(sid, gold_idx): produced_idx|None} — the grader's tie
    rulings; an UNRESOLVED ambiguity blocks PASS (None). driver_state accuracy
    is computed SEPARATELY (its own bar); a FALSE lane_routing verdict
    increments wrong_lane. The error table carries ACTUAL failure codes."""
    if not isinstance(event_meta, dict):
        raise ValueError("event_meta is REQUIRED: {sid: {event_date, fye_month}}")
    for sid in gold_by_event:
        m = event_meta.get(sid) or {}
        if not m.get("event_date") or m.get("fye_month") is None:
            raise ValueError(f"event_meta missing/incomplete for {sid!r}")
    if set(route) != set(gold_by_event):
        raise ValueError(
            f"route must cover exactly the scored events; extra "
            f"{sorted(set(route) - set(gold_by_event))}, missing "
            f"{sorted(set(gold_by_event) - set(route))}")
    tot_gold = matched = 0
    lane_wrong = park = items_n = wrong_name = 0
    code_ok = code_all = 0
    state_ok = state_all = 0
    other_ok = other_all = 0
    verdicts_missing = ambiguities_unresolved = 0
    confirmed_wrong_accepted = 0
    # Grader/extras INPUT problems block completeness but are NOT resolvable
    # ties: counting them in `ambiguities_unresolved` inflated
    # `potential_recall`, because that formula assumes every unresolved row
    # COULD still become a match. A missing ruling is not a potential match, and
    # an empty answer was reaching PASS=None instead of a definite fail.
    grader_problems = 0
    # Counted for the ONE-TO-ONE upper bound (SEQ 1140.3), never guessed:
    #   repairable_pairs — per-event min(open gold, free produced), SUMMED.
    #                      Accumulating the two sides separately and taking ONE
    #                      global min let a spare candidate in event B raise the
    #                      ceiling for missing gold in event A — a pair no
    #                      grader can make, since matching is same-event
    #                      (WorkOrder EXP-5 point 1, Codex SEQ 1141).
    #   key_erratum_seen — a duplicate-gold group was found
    #   other_problem    — any problem that is NOT a pure key erratum
    repairable_pairs = 0
    key_erratum_seen = False
    other_problem = False
    extras_tally = {b: 0 for b in EXTRAS_BUCKETS}
    ambiguous_rows = []
    err = {}

    def _e(code):
        err[code] = err.get(code, 0) + 1

    for sid, gold in gold_by_event.items():
        du = [g for g in gold if g.get("du_worthy") is True]
        tot_gold += len(du)
        produced = (arm_by_event.get(sid) or {}).get("facts", [])
        meta = event_meta[sid]
        # B-16: the scorer COUNTS the public route's decisions. It runs no
        # second rule engine — no `check_item`, no `_home_ok`, no home logic of
        # its own. Only a public `parked` enters the parked NUMERATOR; every
        # deduplicated emitted fact enters its DENOMINATOR. `rejected` and
        # `skipped` are reported with their REAL codes and are never renamed
        # parked, which would overstate the park rate and hide a contract
        # violation behind a routine-looking number (SEQ 1126.4).
        outcomes = _rows_for_event(route, sid, len(produced),
                                   len((arm_by_event.get(sid) or {}).get(
                                       "abstentions") or []))
        # ONE MATCHER (B-15), hoisted ABOVE the decision loop because the
        # deduplicated denominator needs the identity owner's answer first.
        from driver.core.fact_match import match_facts
        gold_v2, gold_pos = _to_v2_with_positions(du)
        prod_v2, prod_pos = _to_v2_with_positions(produced)
        mr = match_facts(gold_v2, prod_v2)
        # THE DENOMINATOR IS DEDUPLICATED (SEQ 1135). `MatchResult` already
        # collapsed produced duplicates through `fact_match.record_key`; counting
        # the raw list instead let one fact emitted twice inflate the
        # denominator and dilute the park rate for free.
        duplicate_extra = {prod_pos[id(x)]
                           for group in mr.produced_duplicates for x in group[1:]}
        for orig_i, _p in enumerate(produced):
            if orig_i in duplicate_extra:
                continue
            items_n += 1
            row = outcomes[("fact", orig_i)]
            decision = row["decision"]
            if decision == "parked":
                park += 1
            for c in row["codes"]:
                _e(f"park:{c}" if decision == "parked" else f"{decision}:{c}")
            if decision not in ("parked", "written") and not row["codes"]:
                _e(f"{decision}:UNCODED")
        # ONE MATCHER (B-15). MatchResult stays visible; only `links` become
        # index pairs, via the identity sidecar. Every non-auto-linked record
        # flows to grading through `to_grading_*` — the retired ambiguity
        # candidate path is gone, not renamed.
        pairs = [(gold_pos[id(g)], prod_pos[id(pr)]) for g, pr in mr.links]
        up = [prod_pos[id(pr)] for pr in mr.to_grading_produced]
        # DUPLICATE GOLD IS A KEY ERRATUM, NOT A MODEL FAILURE (SEQ 1139.2).
        # Two identical gold rows mean the KEY is wrong; the producer cannot
        # lawfully answer both, and reporting that as recall 0 blames the model
        # for a defect in the answer key. The group leaves the denominator, is
        # recorded as inconclusive, and is NOT sent through ordinary pair
        # rulings — which is why these indexes are excluded from `ug` below.
        inconclusive_gold = set()
        for group in mr.gold_inconclusive:        # duplicate gold NEVER credits
            ambiguities_unresolved += 1
            idxs = [gold_pos[id(g)] for g in group]
            inconclusive_gold.update(idxs)
            ambiguous_rows.append({"sid": sid, "reason": "duplicate_gold",
                                   "gold_idxs": idxs})
        tot_gold -= len(inconclusive_gold)
        # ...and they never enter ordinary pair grading, which was raising a
        # `ruling_missing` per duplicate member for a defect no ruling can fix.
        ug = [gold_pos[id(g)] for g in mr.to_grading_gold
              if gold_pos[id(g)] not in inconclusive_gold]
        for group in mr.produced_duplicates:
            ambiguous_rows.append({"sid": sid, "reason": "duplicate_produced",
                                   "produced_idxs": [prod_pos[id(x)] for x in group]})
        if mr.emit_once_violation:
            # A produced duplicate earns NO recall and must BLOCK PASS, not just
            # leave an error string behind (SEQ 1135). `MatchResult.can_pass`
            # already says so; the scorer was recording it and passing anyway.
            _e("emit_once_violation")
            grader_problems += 1
        # THE GRADER'S RULED PAIRS join the auto-linked ones for field scoring.
        # Only VALID rulings; every problem is recorded and blocks PASS.
        ruled, ruling_problems = grade_unmatched(ambiguity_resolutions, sid, ug, up)
        for problem in ruling_problems:
            grader_problems += 1
            ambiguous_rows.append(problem)
            _e("grader_ruling:" + problem["reason"])
        pairs = pairs + ruled

        # ABSTENTIONS (SEQ 1126.5 / 1135): locator-validated, linked ONE-TO-ONE
        # to an otherwise-unmatched gold row.
        abstentions = (arm_by_event.get(sid) or {}).get("abstentions") or []
        # A gold row already answered via a VALID grader ruling is no longer
        # available to an abstention — otherwise an answered fact and an
        # abstention would both charge the same gold row (Codex SEQ 1136.1).
        ruled_gold = {gi for gi, _pi in ruled}
        still_unanswered = [gi for gi in ug if gi not in ruled_gold]
        linked_abst, diagnostic_abst = classify_abstentions(
            abstentions, du, still_unanswered)
        for ai, _gi in linked_abst:
            row = outcomes[("abstention", ai)]
            items_n += 1                  # enters the would-park DENOMINATOR
            park += 1                     # ...and its NUMERATOR
            _e("abstained_on_gold:" + (row["codes"][0] if row["codes"]
                                       else row["decision"]))
        for ai in diagnostic_abst:        # reported, charged to NEITHER side
            _e("abstention:diagnostic")

        # ADDENDUM-A EXTRAS. Only ROUTE-ACCEPTED produced facts that no ruling
        # linked are eligible; a parked/rejected/skipped row is reported but is
        # NOT a wrong ACCEPTANCE — the system already refused it.
        ruled_produced = {pi for _gi, pi in ruled}
        # A produced fact blocked ONLY by a duplicate-gold key erratum is not an
        # "extra" — its gold exists, twice. Asking a grader to classify it as
        # duplicate/key-miss/unsupported would be charging the model for a
        # defect in the answer key (SEQ 1140.2). Identity comes from the ONE
        # owner: same `record_key` as an inconclusive gold row.
        from driver.core.fact_match import record_key as _rk
        erratum_keys = {_rk(g) for grp in mr.gold_inconclusive for g in grp}
        blocked_by_erratum = {prod_pos[id(pr)] for pr in prod_v2
                              if _rk(pr) in erratum_keys}
        accepted_unmatched = [i for i in up
                              if i not in ruled_produced
                              and i not in blocked_by_erratum
                              and outcomes[("fact", i)]["decision"] == "written"]
        tally, extras_problems = classify_extras(extras_verdicts, sid,
                                                 accepted_unmatched)
        for problem in extras_problems:
            grader_problems += 1
            ambiguous_rows.append(problem)
            _e("extras:" + problem["reason"])
        for bucket, n in tally.items():
            extras_tally[bucket] += n
        # The DUPLICATE bucket is filled from the identity owner, not by asking
        # a fake grader to rediscover exact duplicates `MatchResult` already
        # collapsed (Codex SEQ 1136.2). Emit-once still blocks PASS.
        extras_tally["duplicate"] += len(duplicate_extra)
        # an UNSUPPORTED accepted fact is a confirmed-wrong ACCEPTED fact
        confirmed_wrong_accepted += tally["unsupported"]

        # --- the one-to-one ceiling, counted from the existing sets ---
        if inconclusive_gold:
            key_erratum_seen = True
        decided_miss = {gi for (sid_k, gi), pi in (ambiguity_resolutions or {}).items()
                        if sid_k == sid and pi is None}
        decided_miss |= {gi for _ai, gi in linked_abst}   # a park AND a non-match
        still_open_gold = [gi for gi in ug
                           if gi not in ruled_gold and gi not in decided_miss]
        free_produced = [pi for pi in up if pi not in {p for _g, p in ruled}]
        repairable_pairs += min(len(still_open_gold), len(free_produced))
        if (ruling_problems or extras_problems or mr.emit_once_violation
                or verdicts_missing):
            other_problem = True

        matched += len(pairs)
        for gi, pi in pairs:
            g, p = du[gi], produced[pi]
            g_item, p_item = _item(g), _item(p)
            if g.get("fact_type") != p.get("fact_type"):
                lane_wrong += 1
                _e("wrong_lane:matched")
            gn, pn = g_item.get("driver_name"), p_item.get("driver_name")
            if gn != pn:
                wrong_name += 1            # a wrong driver is NEVER a 2% slip
                _e("wrong_name:driver_name")
            # FACT-LEVEL measurements (WorkOrder §649 / Codex SEQ 1132.1).
            # `fact_type` also drives the separate hard `wrong_lane` gate above;
            # `per_x` has no other owner, so without this it was DECLARED in the
            # accounting and never actually compared.
            for f in FACT_LEVEL_FIELDS:
                gv_f, pv_f = g.get(f), p.get(f)
                if gv_f is None and pv_f is None:
                    continue
                code_all += 1
                if gv_f == pv_f:
                    code_ok += 1
                else:
                    _e(f"mismatch:{f}")
            for f in CODE_FIELDS:
                gv_f, pv_f = g_item.get(f), p_item.get(f)
                if gv_f is None and pv_f is None:
                    continue               # comparing nothing is not agreement
                code_all += 1
                if gv_f == pv_f:
                    code_ok += 1
                else:
                    _e(f"mismatch:{f}")
            # EXACT numeric-slot comparison over the FROZEN slot set: each
            # slot's three raw object fields must agree (WorkOrder §649). The
            # retired grouping ("level"/"comparison"/"change") came from the
            # unit RESOLVER's output, which no longer runs.
            from driver.core.prepared_fact_v2 import NUMERIC_SLOTS
            gc, pc = _canon_item_values(g_item), _canon_item_values(p_item)
            for slot in NUMERIC_SLOTS:
                code_all += 1
                if gc[slot] == pc[slot]:
                    code_ok += 1
                else:
                    _e(f"mismatch:value:{slot}")
            code_all += 1
            if (set(g_item.get("slice_parts") or [])
                    == set(p_item.get("slice_parts") or [])):
                code_ok += 1
            else:
                _e("mismatch:slice")
            code_all += 1
            if _meas_tokens(g_item) == _meas_tokens(p_item):
                code_ok += 1
            else:
                _e("mismatch:measurement-OD-9")
            v = (grader_verdicts or {}).get((sid, gi))
            if not (isinstance(v, dict)
                    and all(k in v and isinstance(v[k], bool)
                            for k in MEANING_FIELDS)):
                verdicts_missing += 1
            else:
                # ADDENDUM-A: a FALSE required meaning verdict on a
                # ROUTE-ACCEPTED matched fact is ALSO a confirmed-wrong accepted
                # fact — the system accepted a fact the grader says is wrong.
                # A parked/rejected/skipped row is reported but never counted
                # here; refusing it is the safety gate working, not failing.
                if (not all(v[k] for k in MEANING_FIELDS)
                        and outcomes[("fact", pi)]["decision"] == "written"):
                    confirmed_wrong_accepted += 1
                state_all += 1
                if v["driver_state"]:
                    state_ok += 1
                else:
                    _e("verdict:driver_state")
                if not v["lane_routing"]:
                    lane_wrong += 1        # a false routing verdict = wrong lane
                    _e("verdict:lane_routing")
                for k in ("favorability_od13", "basis_od11", "slice_vs_menu"):
                    other_all += 1
                    if v[k]:
                        other_ok += 1
                    else:
                        _e(f"verdict:{k}")
        # ONLY gold still unmatched AFTER valid rulings and gold-linked
        # abstentions may count as a missing twin (Codex SEQ 1139.1). Raw `ug`
        # is the PRE-grader set, so a surprise the grader had linked was still
        # charged as missing — reproduced as matched=1, recall=1.0 AND
        # wrong_lane=1 on the same fact.
        # ONLY a valid RULED pair answers the twin. A gold-linked abstention is
        # explicitly a park AND a recall NON-match (WorkOrder EXP-5 scoring
        # point 3), so it does not supply the required surprise twin — Codex
        # SEQ 1140.1 corrected my earlier subtraction of both.
        answered = set(ruled_gold)
        for gi in set(ug) - answered:
            g = du[gi]
            if (g.get("fact_type") == "surprise"
                    and (g.get("gold_extra") or {}).get(
                        "expectation_comparison_present")):
                lane_wrong += 1
                _e("wrong_lane:missing_gold_twin")
    recall = matched / tot_gold if tot_gold else 0.0
    would_park = park / items_n if items_n else 0.0
    value_shape_acc = code_ok / code_all if code_all else 1.0
    state_acc = state_ok / state_all if state_all else None
    # ADDENDUM-A SAFETY RESULT, the owner-approved SIXTH criterion.
    #   FAIL          — at least one confirmed-wrong ACCEPTED fact
    #   INCONCLUSIVE  — a genuine gold-key miss leaves the question open
    #   PASS          — neither
    if confirmed_wrong_accepted:
        safety_result = "FAIL"
    elif extras_tally["key_miss"]:
        safety_result = "INCONCLUSIVE"
    else:
        safety_result = "PASS"
    complete = (verdicts_missing == 0 and ambiguities_unresolved == 0
                and grader_problems == 0 and state_acc is not None)
    # DEFINITE FAIL short-circuit: axes no verdict/resolution could repair —
    # even resolving every tie caps recall at potential_recall; wrong_lane
    # from code, parks, and code-field accuracy are verdict-independent
    # THE MECHANICAL ONE-TO-ONE UPPER BOUND (Codex SEQ 1140.3, correcting his
    # own SEQ 1139 framing and my `ambiguities_unresolved` shortcut). A missing
    # ruling CAN still become a match — but only if an unused unmatched produced
    # candidate exists to pair with. So the ceiling is what a perfect grader
    # could still achieve, counted, never guessed:
    #   matched  +  SUM over events of min(open gold, free produced)
    # Decided misses (explicit None rulings, gold-linked abstentions) and
    # duplicate-gold key errata are NOT repairable and earn no potential credit.
    # This is count bookkeeping, not a second matcher.
    potential_recall = ((matched + repairable_pairs) / tot_gold
                        if tot_gold else 0.0)
    # A PURE KEY ERRATUM IS INCONCLUSIVE, NOT A FAILURE (SEQ 1140.2). When the
    # only problem is duplicate gold, the run cannot be called False — the key
    # is broken, so there is nothing to conclude about the model.
    only_key_erratum = (key_erratum_seen and not other_problem
                        and tot_gold == 0 and matched == 0)
    definite_fail = (not only_key_erratum) and (
                     potential_recall < 0.95 or would_park > 0.10
                     or value_shape_acc < 0.98 or lane_wrong > 0
                     or wrong_name > 0
                     or confirmed_wrong_accepted > 0)   # <- Addendum-A, sixth
    gate = None
    if complete:
        # THE SIXTH CRITERION IS ANDed IN, never averaged: one confirmed-wrong
        # ACCEPTED fact fails the run outright, however good the other five
        # numbers look. An INCONCLUSIVE safety result cannot PASS either — an
        # open question is not a pass.
        gate = passes_official_bars(
            recall=recall, lane_wrong=lane_wrong, wrong_name=wrong_name,
            value_shape_acc=value_shape_acc, state_acc=state_acc,
            would_park=would_park, safety_result=safety_result)
    elif definite_fail:
        gate = False
    rollup = {r: 0 for r in OD_RULES}
    rollup["other"] = 0
    for code, n in err.items():
        rollup[_bucket(code)] = rollup.get(_bucket(code), 0) + n
    return {"route_codes": dict(err),      # B-16 point 4: the REAL public codes,
            #   `decision:CODE` for every non-parked outcome and `park:CODE` for
            #   a park. `error_table_by_rule` below buckets into fixed RULE
            #   names, which cannot carry a channel-contract or lane code — so a
            #   rejection would otherwise be reported only as "other", losing
            #   exactly the information a rejection exists to convey.
            "recall": round(recall, 4), "wrong_lane": lane_wrong,
            "wrong_name": wrong_name,
            "error_table_by_rule": rollup,
            "value_shape_acc": round(value_shape_acc, 4),
            "state_acc": None if state_acc is None else round(state_acc, 4),
            "other_meaning_acc": (None if not other_all
                                  else round(other_ok / other_all, 4)),
            "would_park": round(would_park, 4), "gold_n": tot_gold,
            "matched": matched, "ambiguous_rows": ambiguous_rows,
            "ambiguities_unresolved": ambiguities_unresolved,
            "verdicts_missing": verdicts_missing,
            "confirmed_wrong_accepted": confirmed_wrong_accepted,
            "safety_result": safety_result, "extras": dict(extras_tally),
            "error_table": err, "PASS": gate}


def union_answer(gold_by_event, arm_a, arm_b):
    """The DEDUPLICATED union answer, exposed so the caller can route IT.

    Codex SEQ 1126.6: a union needs its OWN completed route over this answer —
    the two single-run routes may never be combined, because fusion and planning
    are event-set dependent and a fact that stood alone in one run can collide in
    the union. The caller cannot build that route without first seeing the union,
    so the union stops being a private step of `score_union`.
    """
    union = {}
    for sid in gold_by_event:
        fa = (arm_a.get(sid) or {}).get("facts", [])
        fb = (arm_b.get(sid) or {}).get("facts", [])
        union[sid] = {"facts": dedup_items(list(fa) + list(fb))}
    return union


def score_union(gold_by_event, arm_a, arm_b, event_meta,
                grader_verdicts=None, ambiguity_resolutions=None, *, route,
                extras_verdicts=None, tiers=None):
    """Same-tier 2-run union: DEDUPLICATED item union per event, matched once.

    SAME-TIER ONLY (WorkOrder EXP-5 arms; step3 §11). `tiers` is the two arms'
    tier labels — the same ones the reader plan pins per arm. A CROSS-TIER union
    is REFUSED, because unioning a stronger arm into a weaker one would report a
    recall the weaker tier never achieved. Omitting `tiers` keeps the existing
    behaviour for callers that already know both arms are one tier.

    `route` MUST be the route over `union_answer(...)`, not either single run's.
    `extras_verdicts` is FORWARDED — it was ACCEPTED and then dropped, which
    silently exempted every union from the Addendum-A safety requirement
    (Codex SEQ 1134.3).
    """
    if tiers is not None:
        a, b = tiers
        if a != b:
            raise ValueError(
                f"cross-tier union refused: {a!r} vs {b!r} — same-tier unions "
                f"only; unioning tiers reports a recall the weaker tier never "
                f"achieved")
    return score_arm(gold_by_event, union_answer(gold_by_event, arm_a, arm_b),
                     event_meta, grader_verdicts,
                     ambiguity_resolutions=ambiguity_resolutions, route=route,
                     extras_verdicts=extras_verdicts)


def presence_disagreement(gold_by_event, arm_a, arm_b, event_meta,
                          resolutions_a=None, resolutions_b=None):
    """captured-by-exactly-one-run / captured-by-either. Tie DECISIONS flow
    in per arm through THE SAME `apply_resolutions` helper scoring uses, so one
    produced fact can never be credited to two gold facts here either.

    Returns **None (INCOMPLETE)** whenever a ruling is INVALID — duplicate,
    targeting an already-consumed fact, or naming a non-candidate. Those are
    grader ERRORS: the input is unusable, so it must never be reported as a
    clean number. A merely UNGRADED tie is a different, PENDING state: it
    counts as not-captured here and is separately tracked (and blocks PASS) by
    `score_arm`, exactly as before."""
    invalid = []

    def _rulings(resolutions):
        """One grader input, or TWO independent ones to reconcile.

        A 2-tuple means two qualified graders answered the same question: only
        their AGREEMENT is scorable (`reconcile_rulings`). A disagreement yields
        no ruling and is recorded as invalid, so the run stays INCOMPLETE rather
        than the scorer picking a winner.
        """
        if isinstance(resolutions, tuple) and len(resolutions) == 2:
            agreed, disagreements = reconcile_rulings(*resolutions)
            invalid.extend(disagreements)
            return agreed
        return resolutions

    def _captured(arm, resolutions):
        got = {}
        rulings = _rulings(resolutions)
        for sid, gold in gold_by_event.items():
            du = [g for g in gold if g.get("du_worthy") is True]
            # SECOND call site of the retired matcher (presence capture). Same
            # law as the primary one: Core matches, MatchResult stays visible,
            # and the retired resolution path is gone rather than renamed.
            from driver.core.fact_match import match_facts
            gold_v2, gold_pos = _to_v2_with_positions(du)
            prod_v2, prod_pos = _to_v2_with_positions(
                (arm.get(sid) or {}).get("facts", []))
            mr = match_facts(gold_v2, prod_v2)
            captured = {gold_pos[id(g)] for g, _p in mr.links}
            # VALID GRADER-LINKED MATCHES COUNT AS CAPTURED (Codex SEQ 1135).
            # Auto-links alone understate capture, because any fact with a real
            # field error is unmatched by construction. Same validating owner
            # the scorer uses — `apply_resolutions` is NOT revived and no
            # candidate matcher proposes a pair.
            ug = [gold_pos[id(g)] for g in mr.to_grading_gold]
            up = [prod_pos[id(pr)] for pr in mr.to_grading_produced]
            if rulings is None and ug and up:
                # An unmatched CANDIDATE exists and required grading is absent:
                # the WorkOrder sends every unmatched fact to a qualified
                # grader, so a clean numeric diagnostic here would be a made-up
                # number (Codex SEQ 1139.3). A truly empty / no-candidate run
                # still reports 0.0 — nothing was missed there.
                invalid.append({"sid": sid, "reason": "grading_required",
                                "unmatched_gold": sorted(ug),
                                "unmatched_produced": sorted(up)})
            if rulings is not None:
                # A merely UNGRADED tie is a PENDING state, not a grader ERROR —
                # this metric's own contract. `score_arm` separately blocks PASS
                # for it. So rulings are consulted only when supplied; passing
                # None through would have reported every unmatched row as
                # invalid and made the metric refuse to emit a number at all.
                ruled, problems = grade_unmatched(rulings, sid, ug, up)
                invalid.extend(problems)
                captured |= {gi for gi, _pi in ruled}
            got[sid] = captured
        return got
    a, b = _captured(arm_a, resolutions_a), _captured(arm_b, resolutions_b)
    if invalid:                       # a grader ERROR -> refuse to emit a number
        return None
    only = sum(len(a[s] ^ b[s]) for s in gold_by_event)
    either = sum(len(a[s] | b[s]) for s in gold_by_event)
    return (only / either) if either else 0.0


def _leg(res, recall_bar):
    """One leg's three-valued verdict from a score_arm result."""
    if res is None:
        return False
    hard_fail = (res.get("wrong_lane", 0) > 0 or res.get("wrong_name", 0) > 0
                 or res["would_park"] > 0.10 or res["value_shape_acc"] < 0.98
                 or res["recall"] < recall_bar and res["PASS"] is False)
    if res["PASS"] is None:
        # pending verdicts/ties — but a known failure takes priority over None
        if res["recall"] < recall_bar and res["PASS"] is False:
            return False
        if hard_fail and res["recall"] >= recall_bar:
            return False
        if res["recall"] >= recall_bar and not hard_fail:
            return None                    # could still turn True
        return False if res["PASS"] is False else (
            None if res["recall"] >= recall_bar else False)
    if not res["PASS"] and res["recall"] >= recall_bar:
        return False
    if res["PASS"] and res["recall"] >= recall_bar:
        return True
    return False


def final_gate(single_result, union_result=None):
    """The workorder:643 tier decision as a THREE-VALUED OR:
    tier = single-leg (recall>=0.95 + the single's axes)
        OR union-leg (recall>=0.98 + the UNION'S OWN axes).
    True if either leg is True; False only when BOTH legs are definitively
    False (known failures take priority over None); None otherwise."""
    # THE SPEC IS EXPLICIT: an UNSAFE arm is never rescued by union recall. A
    # plain OR returned True whenever the union leg passed, even with a
    # confirmed-wrong ACCEPTED fact in the single arm (Codex SEQ 1134). Safety
    # is a VETO over the tier decision, not one more leg to average against —
    # and it is checked BEFORE the legs, so an unsafe arm short-circuits.
    for result in (single_result, union_result):
        if (result or {}).get("confirmed_wrong_accepted"):
            return False
    legs = [_leg(single_result, 0.95), _leg(union_result, 0.98)]
    if True in legs:
        return True
    if all(l is False for l in legs):
        return False
    return None


# `_dry3()` and its `--dry3` entry point are DELETED (Codex SEQ 1131).
#
# It was a manual smoke demo carrying a HAND-COPIED 32-field V1 item list —
# including `slice`, `level_unit_raw` and the four retired unit/money hints —
# which is precisely the copied-list residue B-16 exists to remove. It was also
# already broken: it called `score_arm` without the required `route`. The pytest
# suite is the real check, so this is deleted per the frozen denominator rather
# than rebuilt on V2; nothing here was law and nothing is preserved.


def project_replay_items(reply):
    """STEP 3 §7 / B-14 — the recorded-answer replay projection.

    MECHANICAL and TEST-ONLY: it copies each record's own quote into both
    `quote` and `raw_label_or_claim` and derives no label, value or meaning.
    Facts in emitted order, then abstentions; the returned map is exact.
    Duplicates stay SEPARATE positions and a lawful zero-fact answer projects to
    zero items.
    """
    items, index_map = [], {}
    for kind, records in (("fact", reply.get("facts") or []),
                          ("abstention", reply.get("abstentions") or [])):
        for original_index, record in enumerate(records):
            quote = (record.get("item") or {}).get("quote") if kind == "fact" \
                else record.get("quote")
            index_map[(kind, original_index)] = len(items)
            items.append({"quote": quote, "raw_label_or_claim": quote})
    return items, index_map


def replay_reader(reply):
    """STEP 3 §7 / B-14 — the recorded-answer callback `run_event` calls.

    Each reply is built from the ALREADY-CAPTURED record at the mapped position
    and nothing else: no fact constructed, no meaning derived, no value invented.

        fact       -> {source_id, facts: [that record], abstentions: []}
        abstention -> {source_id, facts: [], abstentions: [that record]}
    """
    items, index_map = project_replay_items(reply)
    source_id = reply.get("source_id")
    by_raw = {}
    for (kind, original_index), raw_index in index_map.items():
        records = reply.get("facts") if kind == "fact" else reply.get("abstentions")
        by_raw[raw_index] = (kind, (records or [])[original_index])
    served = {"n": 0}

    def reader(**_kw):
        i = served["n"]
        served["n"] += 1
        if i not in by_raw:
            raise IndexError(f"run_event asked for raw item {i}; the captured "
                             f"answer projected {len(by_raw)}")
        kind, record = by_raw[i]
        return {"source_id": source_id,
                "facts": [record] if kind == "fact" else [],
                "abstentions": [] if kind == "fact" else [record]}

    return items, reader
