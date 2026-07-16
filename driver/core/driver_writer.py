"""The deterministic fact-write PLANNER (BUILD §5 writer + OD-8 §5.1 + OD-10).

Pure: takes ONE source event's validated facts + a read-only pre-batch graph view,
returns per-fact outcomes with a neutral op list. The CLI executor (S3.5) translates
ops to Cypher inside one atomic tx, behind the ENABLE_DRIVER_WRITES gate — this module
never touches Neo4j, so every test and dry-run is write-free by construction.

Collision law (OD-8, decisions vs the PRE-BATCH state; quote_hash minted ONLY here):
no sibling -> bare · in-batch pairwise-conflicting -> ALL hashed · one sibling:
compatible fills without null-clobber / conflict -> flagged hashed member · multiple
siblings: exact MERGES / conflict-with-all -> hashed member / compatible-not-exact
PARKS · >1 in-batch competitors vs an existing sibling -> park BOTH. Non-signature
fields keep last-write-wins-WITH-LOG; a true signature correction is the repair lane.
"""
import math
import os
from collections import namedtuple

from driver.core.driver_ids import dec_canon, signature_hash

__all__ = ["WriterError", "FakeGraph", "PlanResult", "plan_event_write",
           "signature", "stamp_series_unit", "assert_writes_enabled"]

WRITE_GATE_ENV = "ENABLE_DRIVER_WRITES"

SIGNATURE_FIELDS = ("level_low", "level_high", "level_unit", "change_value",
                    "change_unit", "comparison_low", "comparison_high",
                    "comparison_baseline", "value_text", "conditions")
_NUMERIC_SIG = {"level_low", "level_high", "change_value",
                "comparison_low", "comparison_high"}
# The complete non-signature classification (OD-8: "non-signature fields keep
# last-write-wins-with-log"): IMMUTABLE = {id, fact_scope, created, series_unit}
# (identity + write-once); everything else stored and non-signature moves LWW+log.
_LWW_FIELDS = ("driver_state", "quote", "date", "source_type", "company_confirmed",
               "xbrl_qname", "fiscal_year", "fiscal_quarter", "period_scope",
               "time_type")
_TEXT_SIG = {"value_text", "conditions"}
_COPIED_FIELDS = SIGNATURE_FIELDS + _LWW_FIELDS + ("fact_scope",)
# THE 24 counted stored fields (FINAL_DESIGN §7.1) — the node stores these and NOTHING
# else (driver/company/source/period ride on edges; late_collision is the one
# law-mandated OD-8 member flag outside the count, like recovery's `disputed`)
STORED_FACT_FIELDS = frozenset(_COPIED_FIELDS) | {"id", "created", "series_unit"}
assert len(STORED_FACT_FIELDS) == 24

PlanResult = namedtuple("PlanResult", "fact_id outcome reason ops")


class WriterError(RuntimeError):
    """A structural writer invariant broke. The event batch aborts — never half-writes."""


class FakeGraph:
    """In-memory pre-batch graph view for tests/dry-runs (same read surface the
    real adapter must expose in S3.5)."""

    def __init__(self, facts=None, periods=None):
        self.facts = {f["id"]: f for f in (facts or [])}
        self.periods = dict(periods or {})

    def get_sibling_facts(self, bare_id):
        prefix = bare_id + "|quote_hash="
        return [f for i, f in self.facts.items()
                if i == bare_id or i.startswith(prefix)]

    def get_period(self, period_id):
        return self.periods.get(period_id)


def assert_writes_enabled():
    if os.environ.get(WRITE_GATE_ENV) != "1":
        raise WriterError(f"real writes need {WRITE_GATE_ENV}=1 — dry-run is the default")


def signature(fact):
    """The OD-8 ten-slot value signature in canonical form (null != ""). Numbers go
    through the ONE decimal canonicalizer (via repr — Python's deterministic
    shortest-roundtrip form, the sanctioned float bridge); text slots go through a
    light shared normalization (casefold + whitespace collapse) so trivial wording
    drift can never mint a spurious conflict sibling."""
    sig = []
    for k in SIGNATURE_FIELDS:
        v = fact.get(k)
        if v is not None and k in _NUMERIC_SIG:
            if isinstance(v, float) and not math.isfinite(v):
                raise WriterError(f"non-finite {k}: {v!r} — validators must reject first")
            v = dec_canon(repr(v))
        elif v is not None and k in _TEXT_SIG:
            v = " ".join(str(v).casefold().split())
        sig.append(v)
    return tuple(sig)


def _classify(a, b):
    """exact: all ten slots incl. nulls match · conflict: >=1 shared non-null slot
    disagrees · compatible: otherwise."""
    if a == b:
        return "exact"
    for x, y in zip(a, b):
        if x is not None and y is not None and x != y:
            return "conflict"
    return "compatible"


def stamp_series_unit(fact, prior_series_unit=None):
    """OD-10, written once at write. Conservative folds only — never absorbed:
    level-bearing -> the level's canonical axis · delta-only -> the exact change_unit
    (its own over-split group) · numberless -> null, EXCEPT a withdrawal/reaffirmation,
    which copies exactly one clear prior guide's series_unit and otherwise fails closed."""
    if fact.get("level_low") is not None or fact.get("level_high") is not None:
        return fact.get("level_unit")
    if fact.get("change_value") is not None:
        return fact.get("change_unit")
    if fact.get("driver_state") in ("withdrawn", "reaffirmed"):
        if prior_series_unit is None:
            raise WriterError(
                "series_unit for a withdrawal/reaffirmation copies exactly one clear "
                "prior guide — none provided, fail-closed")
        return prior_series_unit
    return None


def plan_event_write(facts, graph, prior_series_units=None):
    """Plan ONE source event's writes vs the pre-batch graph. Returns [PlanResult]."""
    if not facts:
        return []
    sources = {f["id"].split(":", 2)[1] for f in facts}
    if len(sources) != 1:
        raise WriterError(f"one invocation = one source event, got sources {sources}")

    prior_series_units = prior_series_units or {}
    results = []
    by_bare = {}
    for i, fact in enumerate(facts):
        by_bare.setdefault(fact["id"], []).append((i, fact))

    ordered = {}
    for bare_id, group in by_bare.items():
        for i, res in _plan_group(bare_id, group, graph, prior_series_units):
            ordered[i] = res
    for i in range(len(facts)):
        results.append(ordered[i])
    return results


def _plan_group(bare_id, group, graph, prior_series_units):
    # exact in-batch duplicates converge (idempotent re-submission)
    kept, out = [], []
    for i, fact in group:
        dup = next((k for k, (_, f) in enumerate(kept)
                    if signature(kept[k][1]) == signature(fact)), None)
        if dup is not None:
            out.append((i, PlanResult(bare_id, "deduped",
                                      "exact in-batch duplicate", [])))
        else:
            kept.append((i, fact))

    siblings = graph.get_sibling_facts(bare_id)

    if len(kept) > 1:
        if siblings:
            out.extend(_plan_competitors(kept, siblings, graph, prior_series_units))
            return out
        pairs = [(a, b) for x, (_, a) in enumerate(kept)
                 for _, b in (kept[y] for y in range(x + 1, len(kept)))]
        if all(_classify(signature(a), signature(b)) == "conflict" for a, b in pairs):
            for i, fact in kept:                       # ALL hashed, no bare member
                out.append((i, _create(fact, hashed=True, late=False,
                                       graph=graph,
                                       prior_series_units=prior_series_units)))
        else:
            for i, _ in kept:                          # fusion should have merged these
                out.append((i, PlanResult(bare_id, "parked",
                                          "compatible same-scope in-batch facts — "
                                          "fusion upstream should have merged them", [])))
        return out

    i, fact = kept[0]
    sig = signature(fact)

    if not siblings:
        out.append((i, _create(fact, hashed=False, late=False, graph=graph,
                               prior_series_units=prior_series_units)))
        return out

    if len(siblings) == 1:
        rel = _classify(sig, signature(siblings[0]))
        if rel == "conflict":
            out.append((i, _create(fact, hashed=True, late=True, graph=graph,
                                   prior_series_units=prior_series_units)))
        else:
            out.append((i, _merge_or_fill(fact, siblings[0], rel)))
        return out

    exact = next((s for s in siblings if _classify(sig, signature(s)) == "exact"), None)
    if exact is not None:
        out.append((i, _merge_or_fill(fact, exact, "exact")))
        return out
    if all(_classify(sig, signature(s)) == "conflict" for s in siblings):
        out.append((i, _create(fact, hashed=True, late=True, graph=graph,
                               prior_series_units=prior_series_units)))
        return out
    out.append((i, PlanResult(bare_id, "parked",
                              "ambiguous: compatible-but-not-exact with multiple "
                              "siblings — never guess which member to fill", [])))
    return out


def _plan_competitors(kept, siblings, graph, prior_series_units):
    """>1 in-batch facts with pre-existing siblings. Per OD-8, only true FILL
    competitors park ('two in-batch competitors for one partial sibling'); a fact
    that is order-independently decidable (exact match, or conflicts with every
    sibling AND every in-batch peer) proceeds."""
    out = []
    sib_sigs = [signature(s) for s in siblings]
    sigs = {i: signature(f) for i, f in kept}
    rels = {i: [_classify(sigs[i], ss) for ss in sib_sigs] for i, _ in kept}
    compat_count = sum(1 for i, _ in kept
                       if "exact" not in rels[i] and "compatible" in rels[i])
    for i, fact in kept:
        if "exact" in rels[i]:
            out.append((i, _merge_or_fill(fact, siblings[rels[i].index("exact")],
                                          "exact")))
        elif "compatible" in rels[i]:
            if compat_count > 1 or len(siblings) > 1:
                out.append((i, PlanResult(fact["id"], "parked",
                                          "in-batch competitors for one partial "
                                          "sibling — a richer rerun resolves", [])))
            else:
                out.append((i, _merge_or_fill(fact, siblings[0], "compatible")))
        elif all(_classify(sigs[i], sigs[j]) == "conflict"
                 for j, _ in kept if j != i):
            out.append((i, _create(fact, hashed=True, late=True, graph=graph,
                                   prior_series_units=prior_series_units)))
        else:
            out.append((i, PlanResult(fact["id"], "parked",
                                      "mixed in-batch/sibling ambiguity — "
                                      "fail closed, never guess", [])))
    return out


def _create(fact, *, hashed, late, graph, prior_series_units):
    prior = prior_series_units.get(fact["id"])
    if isinstance(prior, (list, tuple)):               # exactly-ONE clear prior, enforced
        if len(prior) != 1:
            return PlanResult(fact["id"], "parked",
                              f"series_unit: need exactly one clear prior guide, "
                              f"got {len(prior)} — fail closed", [])
        prior = prior[0]
    try:
        series_unit = stamp_series_unit(fact, prior)
    except WriterError as e:
        return PlanResult(fact["id"], "parked", f"series_unit: {e}", [])

    fact_id = fact["id"]
    if hashed:
        fact_id = f"{fact_id}|quote_hash={signature_hash(list(signature(fact)))}"

    props = {k: fact.get(k) for k in _COPIED_FIELDS}
    props.update(id=fact_id, created="__now__", series_unit=series_unit)
    if set(props) != STORED_FACT_FIELDS:               # drift guard: exactly the 24
        raise WriterError(f"stored-field drift: {set(props) ^ STORED_FACT_FIELDS}")
    if hashed:
        props["late_collision"] = late
    ops = [{"op": "create_fact", "id": fact_id, "props": props},
           {"op": "edge", "type": "OF_DRIVER", "from": fact_id,
            "to": fact["driver_name"]},
           {"op": "edge", "type": "FROM_SOURCE", "from": fact_id,
            "to": fact["id"].split(":", 2)[1]}]
    period_id = fact.get("period_u_id")
    if period_id:
        existing = graph.get_period(period_id)
        if existing and (existing.get("start_date") != fact.get("gp_start_date")
                         or existing.get("end_date") != fact.get("gp_end_date")):
            raise WriterError(
                f"DriverPeriod {period_id} write-once violation: node has "
                f"{existing.get('start_date')}..{existing.get('end_date')}, fact says "
                f"{fact.get('gp_start_date')}..{fact.get('gp_end_date')}")
        ops.append({"op": "merge_period", "id": period_id, "u_id": period_id,
                    "start_date": fact.get("gp_start_date"),
                    "end_date": fact.get("gp_end_date")})
        ops.append({"op": "edge", "type": "HAS_PERIOD", "from": fact_id,
                    "to": period_id})
    for ref in fact.get("member_refs") or ():
        ops.append({"op": "edge", "type": "MAPS_TO_MEMBER", "from": fact_id,
                    "to": ref["member"], "props": {"slice_part": ref["slice_part"]}})
    return PlanResult(fact_id, "created_member" if hashed else "created", None, ops)


def _merge_or_fill(fact, target, rel):
    """exact -> LWW-with-log on non-signature drift · compatible -> fill nulls only.
    Neo4j SET x = null DELETES a property — a null on our side is never written."""
    sets, logs = {}, []
    if rel == "compatible":
        new_sig, old_sig = signature(fact), signature(target)
        for k, new_c, old_c in zip(SIGNATURE_FIELDS, new_sig, old_sig):
            if old_c is None and new_c is not None:
                sets[k] = fact.get(k)                  # fill with the RAW value
    for k in _LWW_FIELDS:
        new = fact.get(k)
        if new is not None and new != target.get(k):
            sets[k] = new
            logs.append({"op": "log", "field": k, "old": target.get(k), "new": new,
                         "fact_id": target["id"]})
    if not sets:
        return PlanResult(target["id"], "noop", None, [])
    ops = [{"op": "set_fields", "id": target["id"], "fields": sets}] + logs
    outcome = "filled" if rel == "compatible" and any(
        k in SIGNATURE_FIELDS for k in sets) else "updated"
    return PlanResult(target["id"], outcome, None, ops)
