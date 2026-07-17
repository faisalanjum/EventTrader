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
import os
from collections import namedtuple
from decimal import Decimal

from driver.core.driver_ids import IdLawError, norm, num_canon, signature_hash

__all__ = ["WriterError", "FakeGraph", "PlanResult", "plan_event_write",
           "signature", "stamp_series_unit", "assert_writes_enabled"]

WRITE_GATE_ENV = "ENABLE_DRIVER_WRITES"

SIGNATURE_FIELDS = ("level_low", "level_high", "level_unit", "change_value",
                    "change_unit", "comparison_low", "comparison_high",
                    "comparison_baseline", "value_text", "conditions")
_NUMERIC_SIG = ("level_low", "level_high", "change_value",
                "comparison_low", "comparison_high")   # fixed order: deterministic reports
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
            try:
                v = num_canon(v)
            except IdLawError as e:
                raise WriterError(f"{k}: {e} — validators must reject first")
        elif v is not None and k in _TEXT_SIG:
            v = norm(str(v))         # THE one approved text normalizer — no second cleaner
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


def storable(value):
    """The owner exactness storage law (2026-07-17): whole numbers -> Neo4j INTEGER
    (long range); a non-integral decimal -> Neo4j float ONLY when storing-and-reading
    provably reproduces the exact original decimal (repr round-trip); anything else is
    NOT storable and the fact PARKS. Returns (kind, native_value) or None.
    Read-adapter corollary (S3.5): stored floats are exact by construction, so
    Decimal(repr(read_float)) recovers the original — the graph adapter converts on
    read before any signature comparison."""
    d = value if isinstance(value, Decimal) else Decimal(value)
    if d == d.to_integral_value():
        i = int(d)
        return ("int", i) if -(2 ** 63) <= i < 2 ** 63 else None   # the full long range
    try:
        f = float(d)
    except OverflowError:
        return None
    return ("float", f) if Decimal(repr(f)) == d else None


def _store_numeric(props):
    """Convert the numeric props to their native storage form; None = a non-storable
    value was found (caller parks). The signature/hash was computed on the EXACT
    values before this conversion."""
    for k in _NUMERIC_SIG:
        val = props.get(k)
        if val is None:
            continue
        st = storable(val)
        if st is None:
            return k, val
        props[k] = st[1]
    return None


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
    for f in facts:
        fid = f.get("id")
        if not isinstance(fid, str) or not fid.startswith("du:") or fid.count(":") < 3:
            raise WriterError(f"fact without a valid id reached the writer "
                              f"({fid!r}) — validators run first")
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
    # exact in-batch duplicates FUSE deterministically — input order must never pick
    # the surviving quote/state: representative = latest date, then lexicographic quote
    sig_groups = {}
    for i, fact in group:
        sig_groups.setdefault(signature(fact), []).append((i, fact))
    kept, dedups = [], []
    for items in sig_groups.values():
        # total deterministic order: latest date, then ALL non-signature content —
        # two duplicates differing in ANY field always fuse the same way
        ordered = sorted(items,
                         key=lambda t: tuple(str(t[1].get(k)) for k in _LWW_FIELDS))
        ordered = sorted(ordered, key=lambda t: t[1].get("date") or "", reverse=True)
        rep_i, rep = ordered[0]
        kept.append((rep_i, rep))
        for i, f in ordered[1:]:
            diffs = {k: f.get(k) for k in _LWW_FIELDS
                     if f.get(k) is not None and f.get(k) != rep.get(k)}
            ops = [{"op": "log", "event": "in_batch_duplicate_fused",
                    "dropped_fields": diffs}] if diffs else []
            dedups.append((i, rep_i, ops))
    kept.sort(key=lambda t: t[0])
    out = _plan_kept(bare_id, kept, graph, prior_series_units)
    survivors = dict(out)
    for i, rep_i, ops in dedups:       # duplicates report the SURVIVOR's real id/status
        rep = survivors[rep_i]
        out.append((i, PlanResult(rep.fact_id, "deduped",
                                  f"exact in-batch duplicate — fused onto "
                                  f"{rep.fact_id} ({rep.outcome})", ops)))
    return out


def _plan_kept(bare_id, kept, graph, prior_series_units):
    out = []
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
    if hashed:
        # quote_hash is a fact_scope SLOT (FINAL §5.1 grammar) — id and scope stay
        # the same string down to the byte: scope == everything after the 3rd colon
        props["fact_scope"] = fact_id.split(":", 3)[3]
    if set(props) != STORED_FACT_FIELDS:               # drift guard: exactly the 24
        raise WriterError(f"stored-field drift: {set(props) ^ STORED_FACT_FIELDS}")
    bad = _store_numeric(props)
    if bad is not None:
        return PlanResult(fact["id"], "parked",
                          f"{bad[0]}={bad[1]} is not exactly storable "
                          f"(owner exactness law) — park, never approximate", [])
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
    if late:
        # OD-8 rule 9: all collision flags are counters/LOGS — zero new stored artifacts
        ops.append({"op": "log", "event": "late_collision", "fact_id": fact_id})
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
    if sets:
        # OD-10 on merges: a null series_unit FILLS when merged content now defines an
        # axis; a merge whose content would CHANGE a stored axis parks (repair lane).
        merged = {**target, **sets}
        try:
            prospective = stamp_series_unit(merged)
        except WriterError:
            prospective = target.get("series_unit")
        current = target.get("series_unit")
        if current is None and prospective is not None:
            sets["series_unit"] = prospective
            logs.append({"op": "log", "field": "series_unit", "old": None,
                         "new": prospective, "fact_id": target["id"]})
        elif current is not None and prospective is not None and prospective != current:
            return PlanResult(target["id"], "parked",
                              f"series_unit conflict: stored {current!r} vs "
                              f"merged-content axis {prospective!r} — repair lane only",
                              [])
    if not sets:
        return PlanResult(target["id"], "noop", None, [])
    bad = _store_numeric(sets)
    if bad is not None:
        return PlanResult(target["id"], "parked",
                          f"{bad[0]}={bad[1]} is not exactly storable "
                          f"(owner exactness law) — park, never approximate", [])
    ops = [{"op": "set_fields", "id": target["id"], "fields": sets}] + logs
    outcome = "filled" if rel == "compatible" and any(
        k in SIGNATURE_FIELDS for k in sets) else "updated"
    return PlanResult(target["id"], outcome, None, ops)
