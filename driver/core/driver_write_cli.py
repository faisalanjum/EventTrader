"""S3.5 INTERNAL writer CLI — the owner-locked §11.4 v3.6 contract in code.

Flow: prepared facts → load stored source + typed Driver → deterministic tail
(surprise compose → period → UNITS canonical → slice/measurement → member-ref law
via the PIT slice menu (step 7: frozen classification · FS-20 · FS-18 fold; invalid
refs park MEMBER_LINK_INVALID) → ids → FUSION on canonical values → full validation)
→ provisional plan → dry-run (DEFAULT) or ONE non-retried whole-event transaction
with in-tx recheck → durable write-ahead audit (prepared → committed/failed/dry_run).

Truthfulness: rollback/failure reports ZERO facts written — approved facts become
parked(EXECUTION_FAILED). REJECT beats PARK. date = the STORED source's public time;
created = commit time, stamped once. Fused facts share ONE fact_id across their input
indexes. ONE active local writer via flock (real writes only). Real writes need BOTH
enable_writes=True AND ENABLE_DRIVER_WRITES=1 — dry-run performs the SAME reads and
the SAME planning, executes nothing. Every non-written outcome carries an EXPLICIT
machine code (free text is never parsed). Internal tool until the S4 decomposer/kernel.
"""
import copy
import hashlib
import json
import os
from collections.abc import Mapping
from decimal import Decimal

from driver.core.driver_fusion import fuse_event
from driver.core.driver_ids import (GUIDANCE_BASIS, IdLawError, _slice_value,
                                    build_id, norm, valid_source_id)
from driver.core.driver_period_resolver import (PERIOD_ITEM_KEYS,
                                                PeriodResolutionError,
                                                ensure_driver_period)
from driver.core.driver_units import UnitResolutionError, resolve_driver_units
from driver.core.driver_validators import (_expected_home_name, _home_mismatch,
                                           _actual_surprise_before_period_end,
                                           compose_surprise_scope,
                                           SOURCE_TYPES, parse_source_timestamp,
                                           same_source_instant,
                                           _surprise_contract_violations,
                                           validate_fact)
from driver.core.driver_writer import WriterError, assert_writes_enabled, plan_event_write
from driver.core.outcome_codes import CHANNEL_CONTRACT_INVALID, READER_ABSTAINED
from driver.core.slice_menu import (axis_member_pairs, build_menu,
                                    check_member_refs, match_xbrl_fact)

# every code the CLI itself can emit (planner codes ride on PlanResult.code;
# validator codes ride on Violation.code) — the every-branch test pins this set
CLI_CODES = frozenset({
    "SOURCE_MISSING", "SOURCE_COMPANY_AMBIGUOUS", "DRIVER_NOT_READY",
    "SURPRISE_COMPOSE", "PERIOD_UNRESOLVED", "UNIT_UNRESOLVED",
    "MEMBER_LINK_INVALID", "ID_LAW", "FUSION_AMBIGUOUS", "F7", "EMPTY_LABEL",
    "SURPRISE_HOME_NOT_ACCEPTED", "EXECUTION_FAILED", "WRITER_BUSY", "WRITE_GATE",
    "INTERNAL_UNTRACKED",
    # LIVE and previously UNREGISTERED. `driver_writer` emits NOT_STORABLE on
    # two branches today, but the reachability test only proved that every
    # REGISTERED code is emitted — never that every EMITTED code is registered
    # — so a code the CLI really produces sat outside its own registry.
    "NOT_STORABLE",
})   # MEMBER_LINK_DEFERRED retired at step 7 (fence removed) — §11.4 amendment
     # pending owner approval; MEMBER_LINK_INVALID = ref-level law breach parks
     # The three staged XBRL defaults (SOURCE_UNAVAILABLE, XBRL_CONTRACT_INVALID,
     # XBRL_BINDING_UNAVAILABLE) are registered AT THE SWITCH, not before.
_ACCEPTED = ("created", "created_member", "noop", "filled", "updated", "deduped")
_DECISION = {"created": "written", "created_member": "written", "noop": "merged",
             "filled": "merged", "updated": "merged", "deduped": "merged",
             "parked": "parked"}


def load_run_input(path):
    """Exact JSON load: floats become Decimal; NaN/Infinity literals REJECT."""
    from driver.core.prepared_fact import RunInputV1, SchemaError

    def _no_const(name):
        raise SchemaError(f"non-finite JSON literal {name!r} rejected")
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw, RunInputV1.from_dict(
        json.loads(raw.decode("utf-8"), parse_float=Decimal,
                   parse_constant=_no_const))


def _item(index, decision, codes=(), fact_id=None, detail=None):
    return {"index": index, "fact_id": fact_id, "decision": decision,
            "codes": list(codes), "detail": detail}


def _jsonable(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Mapping):
        # THE ONE SERIALIZER, taught to copy any mapping — not a second one.
        # An immutable mapping is unknown to `json`, so it landed on the
        # `str(obj)` line below and the whole audit record was written as the
        # literal text "mappingproxy({...})". Values are handed back UNTOUCHED
        # so `json` keeps rendering ints as ints.
        return {str(k): v for k, v in obj.items()}
    if isinstance(obj, (set, frozenset, tuple)):
        return sorted(str(x) for x in obj) if isinstance(obj, (set, frozenset)) \
            else [_jsonable(x) for x in obj]
    return str(obj)


class _Audit:
    """Write-ahead audit: ONE unique never-overwritten file per run. `prepared` is
    durable BEFORE any mutation; the final state lands by atomic replace. A leftover
    `prepared` file = the run died mid-flight (manual reconcile, never assumed ok)."""

    def __init__(self, audit_dir, run_id, payload):
        os.makedirs(audit_dir, exist_ok=True)
        self.path = os.path.join(audit_dir, f"{run_id}.json")
        with open(self.path, "x", encoding="utf-8") as fh:   # unique or die
            json.dump({"run_id": run_id, "state": "prepared", **payload},
                      fh, default=_jsonable)
            fh.flush()
            os.fsync(fh.fileno())

    def _replace(self, mutate):
        tmp = self.path + ".tmp"
        with open(self.path, encoding="utf-8") as fh:
            doc = json.load(fh)
        mutate(doc)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, default=_jsonable)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)                            # atomic flip

    def update(self, extra):                                  # state STAYS prepared
        self._replace(lambda doc: doc.update(extra))

    def finalize(self, state, extra):
        self._replace(lambda doc: (doc.update(extra), doc.update(state=state)))


def resolve_or(pair):
    return [pair[0] if pair else None, pair[1] if len(pair) > 1 else None]


def _check_admissions(admissions, facts):
    """S4 v2.5 Step-3 map integrity, enforced BEFORE any planning (a violation is
    a fixture bug — hard-error, never a per-item park): completeness BOTH ways ·
    exact triple shape · admission/fact name agreement · per-driver group
    agreement on decision AND fact_type."""
    from driver.core.prepared_fact import SchemaError
    n = len(facts)
    if not isinstance(admissions, dict):
        raise SchemaError("admissions: must be a dict keyed by zero-based fact index")
    for k in admissions:
        if type(k) is not int:                 # bool True/False == 1/0 must NOT pass
            raise SchemaError(f"admissions: index keys must be exact ints, "
                              f"got {k!r} ({type(k).__name__})")
    if set(admissions) != set(range(n)):
        missing = sorted(set(range(n)) - set(admissions))
        extra = sorted(set(admissions) - set(range(n)))
        raise SchemaError(f"admissions map incomplete both ways: every fact needs "
                          f"exactly one entry and every entry a fact "
                          f"(missing {missing}, extra {extra})")
    groups = {}
    for i in range(n):
        a = admissions[i]
        if (not isinstance(a, dict)
                or set(a) != {"decision", "driver_name", "fact_type"}
                or a["decision"] not in ("attach", "create")
                or not all(isinstance(a[k], str) and a[k].strip()
                           for k in ("driver_name", "fact_type"))):
            raise SchemaError(f"admissions[{i}]: exactly "
                              f"{{decision: attach|create, driver_name, fact_type}} "
                              f"with non-blank strings")
        if a["fact_type"] != "metric":
            # the v2.5 Step-2 mechanical fence: the rehearsal era admits the
            # metric lane ONLY; widening is an explicit future owner change
            raise SchemaError(f"admissions[{i}]: fact_type {a['fact_type']!r} — "
                              f"the rehearsal fence admits 'metric' only "
                              f"(other lanes rehearse later, separately)")
        if a["driver_name"] != facts[i].driver_name:
            raise SchemaError(f"admissions[{i}]: driver_name {a['driver_name']!r} "
                              f"!= the fact's {facts[i].driver_name!r}")
        groups.setdefault(a["driver_name"], set()).add(
            (a["decision"], a["fact_type"]))
    for name, triples in sorted(groups.items()):
        if len(triples) > 1:
            raise SchemaError(f"admissions: group {name!r} carries disagreeing "
                              f"triples {sorted(triples)} — all facts of one "
                              f"Driver must agree on decision AND fact_type")


def _tail(i, pf, src, driver, fye_month, period_lookups, calendar_override):
    """One fact through the deterministic tail (pre-fusion). Returns
    ('ok', fact_dict) or ('parked'|'rejected', codes, detail)."""
    surprise = None
    if pf.surprise_basis_hint is not None:
        try:
            surprise = compose_surprise_scope(pf.surprise_basis_hint,
                                              pf.comparison_baseline)
        except (ValueError, IdLawError) as e:
            return ("rejected", ["SURPRISE_COMPOSE"], str(e))
    state = pf.driver_state

    try:
        period = ensure_driver_period(
            {k: getattr(pf, k) for k in PERIOD_ITEM_KEYS},
            fact_type=driver["fact_type"], fye_month=fye_month,
            ticker=src.get("ticker"), calendar_override=calendar_override,
            lookups=period_lookups)
    except PeriodResolutionError as e:
        return ("parked", ["PERIOD_UNRESOLVED"], str(e))

    try:
        units = resolve_driver_units(
            pf.driver_name,
            level_values=[pf.level_low, pf.level_high],
            level_unit_raw=pf.level_unit_raw,
            level_unit_kind_hint=pf.level_unit_kind_hint,
            level_money_mode_hint=pf.level_money_mode_hint,
            comparison_values=[pf.comparison_low, pf.comparison_high],
            change_value=pf.change_value, change_unit_raw=pf.change_unit_raw,
            change_unit_kind_hint=pf.change_unit_kind_hint,
            change_money_mode_hint=pf.change_money_mode_hint,
            period_scope=period["period_scope"] if period else None,
            sequential_evidence=pf.sequential_evidence,
            quote=pf.quote, xbrl_qname=pf.xbrl_concept_raw)
    except UnitResolutionError as e:
        return ("parked", ["UNIT_UNRESOLVED"], str(e))

    if surprise is not None:
        # F7 tense (OD-21) BEFORE fusion: REJECT beats PARK, so an invalid
        # actual must fall here and never turn a fillable fragment group into
        # FUSION_AMBIGUOUS (SEQ 292's three-fragment partial-conflict case).
        if period and _actual_surprise_before_period_end(
                pf.surprise_basis_hint, period["gp_end_date"], src["date"]):
            return ("rejected", ["F7"],
                    f"actual surprise but the period ends {period['gp_end_date']}, "
                    f"after the source time — impossible tense")
        # OD-21: position + the wordless in_line correction (surprise tail wiring)
        from driver.core.driver_validators import (apply_inline_correction,
                                                   surprise_position)
        lv = resolve_or(units["level_values"])
        cv = resolve_or(units["comparison_values"])
        position = surprise_position(
            lv[0], lv[1], cv[0], cv[1],
            value_is_guide=(pf.surprise_basis_hint == GUIDANCE_BASIS))
        state = apply_inline_correction(
            state, position,
            has_favorability_wording=bool(pf.has_favorability_wording))
        # §4.3 wordless polarity — MECHANICAL check only, no keyword engine: the
        # pinned two-value proof must exist AND agree with position × state, else
        # the state honestly becomes unknown (missing or inconsistent = same fate)
        if not pf.has_favorability_wording and state in ("beat", "missed"):
            expected = {("above", "beat"): "higher_favorable",
                        ("above", "missed"): "lower_favorable",
                        ("below", "beat"): "lower_favorable",
                        ("below", "missed"): "higher_favorable"}.get((position, state))
            proof = pf.polarity_proof
            if (proof is None or expected is None
                    or proof.get("polarity") != expected):
                state = "unknown"

    # ONE normalization, up front — ids, fusion, validation, and the surprise-home
    # match all see the same canonical text ('Adjusted' ≡ 'adjusted'). A label that
    # normalizes to NOTHING parks with its own code — never a reject, never a crash.
    try:
        slice_parts = [(k, _slice_value(k, v)) for k, v in pf.slice_parts]
        measurement_tokens = set()
        for s in pf.measurement_raw_spans:
            token = norm(s)
            if not token:
                raise IdLawError(f"measurement span normalizes to nothing: {s!r}")
            measurement_tokens.add(token)
        measurement_tokens = sorted(measurement_tokens)
    except IdLawError as e:
        return ("parked", ["EMPTY_LABEL"], str(e))

    fact = {
        "driver_name": pf.driver_name, "driver_state": state,
        "quote": pf.quote, "date": src["date"], "source_type": src["source_type"],
        "company_confirmed": pf.company_confirmed,
        "level_low": units["level_values"][0], "level_high": units["level_values"][1],
        "level_unit": units["level_unit"],
        "change_value": units["change_value"], "change_unit": units["change_unit"],
        "comparison_low": units["comparison_values"][0],
        "comparison_high": units["comparison_values"][1],
        "comparison_baseline": pf.comparison_baseline,
        "value_text": pf.value_text, "conditions": pf.conditions,
        "fiscal_year": pf.fiscal_year, "fiscal_quarter": pf.fiscal_quarter,
        "xbrl_qname": None,                       # enrichment-only, never from input
        "slice_parts": slice_parts, "measurement_tokens": measurement_tokens,
        "surprise_basis_hint": pf.surprise_basis_hint, "surprise": surprise,
        "level_shape_hint": pf.level_shape_hint,      # validated then discarded
        "comparison_shape_hint": pf.comparison_shape_hint,
        "period_u_id": period["period_u_id"] if period else None,
        "period_scope": period["period_scope"] if period else None,
        "time_type": period["time_type"] if period else None,
        "gp_start_date": period["gp_start_date"] if period else None,
        "gp_end_date": period["gp_end_date"] if period else None,
    }
    return ("ok", fact)


def run_event(run_input, *, store, audit_dir, lock_path=None, enable_writes=False,
              period_lookups=None, now_fn=None, input_bytes=None, admissions=None,
              raw_origin=None, n_raw=None, raw_terminals=(), reader=None,
              filing_provider=None):
    """Run ONE source event end-to-end. Returns the flat §5 output:
    {status, code?, items: [{index, fact_id, decision, codes, detail}]}.

    ONE ENTRY POINT, TWO INPUT CONTRACTS, until the owner-gated v1->v2 switch.
    A V2 Stage-A EVENT (a dict of the seven published fields) takes the V2
    route; a `RunInputV1` takes the legacy path unchanged. This is a dispatch on
    the input contract, not a public wrapper and not a second public function —
    at the switch the V1 branch is DELETED, leaving one route with no rename.

    admissions (S4 v2.5 Step 3, the ONE kernel handoff — dry-run PLANS only):
    None → today's behavior unchanged (a missing Driver parks DRIVER_NOT_READY).
    A map {fact_index: {decision, driver_name, fact_type}} → verified all-three
    both paths; missing Drivers plan ONE born-complete create_driver bundle per
    group; combining a supplied map with enable_writes HARD-FAILS."""
    # ONE ENTRY, TWO CONTRACTS — and neither may silently IGNORE the other's
    # arguments. V2 accepted `admissions`, the raw-accounting set and
    # `input_bytes` and did nothing with them; V1 accepted `reader` and
    # `filing_provider` and did nothing with them. Both returned a normal
    # result, so the caller could not see that its instruction was dropped.
    # ONE table, checked pure and before any I/O. Shared arguments (`store`,
    # `audit_dir`, `enable_writes`, `now_fn`) belong to both and are not listed.
    _contract_only = {
        "v1": (("lock_path", lock_path, None),
               ("period_lookups", period_lookups, None),
               ("input_bytes", input_bytes, None),
               ("admissions", admissions, None),
               ("raw_origin", raw_origin, None),
               ("n_raw", n_raw, None),
               ("raw_terminals", raw_terminals, ())),
        "v2": (("reader", reader, None),
               ("filing_provider", filing_provider, None)),
    }
    is_v2 = type(run_input) is dict
    foreign = [n for n, got, default in _contract_only["v1" if is_v2 else "v2"]
               if got != default]
    if foreign:
        raise RuntimeError(
            f"run_event received {'V1' if is_v2 else 'V2'}-only argument(s) "
            f"{sorted(foreign)} with a {'V2' if is_v2 else 'V1'} input — the "
            f"other contract cannot honour them, and ignoring them silently "
            f"drops the caller's instruction")
    if is_v2:                                   # the V2 Stage-A event contract
        return _run_event_v2(run_input, store=store, audit_dir=audit_dir,
                             reader=reader, enable_writes=enable_writes,
                             now_fn=now_fn, filing_provider=filing_provider)
    # RAW ACCOUNTING is a PURE caller-contract check and runs BEFORE any I/O.
    # None = pre-switch behaviour, one row per prepared fact, V1 untouched.
    if (raw_origin is None) != (n_raw is None) or (
            raw_origin is None and raw_terminals):
        raise RuntimeError(
            "raw accounting: the relation, n_raw and terminals are ONE argument "
            "set — a partial set silently reverted to legacy per-fact rows")
    if raw_origin is not None:
        raw_origin, raw_terminals = _freeze_raw_accounting(
            raw_origin, n_raw, raw_terminals, len(run_input.facts))
    now_fn = now_fn or (lambda: __import__("datetime").datetime.utcnow()
                        .strftime("%Y-%m-%dT%H:%M:%S.%f"))
    if input_bytes is not None:                    # bytes must BE the parsed input
        from driver.core.prepared_fact import RunInputV1
        reparsed = RunInputV1.from_dict(json.loads(
            input_bytes.decode("utf-8"), parse_float=Decimal))
        if reparsed != run_input:
            raise ValueError("input_bytes do not parse to the given run_input — "
                             "the audit would lie; refuse")
    if admissions is not None:
        # the v2.5 rehearsal clamp + map validation run FIRST — before the map
        # is serialized anywhere (a malformed map must raise the clean input
        # error, never a raw crash) and before any planning or side effect
        if enable_writes:
            raise WriterError("admissions + enable_writes is forbidden: recorded "
                              "admissions produce dry-run PLANS only (v2.5 clamp)")
        _check_admissions(admissions, run_input.facts)
    input_doc = {"source_id": run_input.source_id,
                 "calendar_override": run_input.calendar_override,
                 "facts": [{k: getattr(f, k) for k in type(f).FIELDS}
                           for f in run_input.facts]}
    if admissions is not None:                 # the decisions are RUN INPUT: they
        input_doc["admissions"] = {            # join the audit + the run-id hash so
            str(i): dict(admissions[i])        # the run is fully reconstructable
            for i in sorted(admissions)}
    if raw_origin is not None:                 # the accounting relation is RUN
        input_doc["raw_accounting"] = {        # INPUT too: it joins the audit and
            "n_raw": n_raw,                    # the run-id hash, so the run's raw
            "origin": list(raw_origin),        # provenance is reconstructable and
            "terminals": [dict(t) for t in raw_terminals]}   # cannot drift unseen
    input_json = json.dumps(input_doc, default=_jsonable, sort_keys=True)
    run_id = (now_fn().replace(":", "").replace(".", "") + "_"
              + hashlib.sha256(input_json.encode()).hexdigest()[:12])
    audit = _Audit(audit_dir, run_id, {
        "input": json.loads(input_json),
        "input_bytes": (input_bytes.decode("utf-8", "replace")
                        if input_bytes is not None else input_json),  # EXACT bytes
        "prepared_at": now_fn()})
    n = len(run_input.facts)
    # INTERNAL ONLY: which prepared facts failed fusion TOGETHER. `park.indexes`
    # already IS that group, so nothing is minted. A failed group is ONE relation
    # per raw item; two INDEPENDENT branches have no group and never collapse.
    fusion_group_of = {}

    def _finish(status, items, code=None, plans=None, driver_plans=None):
        if raw_origin is not None:         # ONE translation, every return path
            items = _raw_rows(items, raw_origin, raw_terminals,
                              fusion_group_of)
        out = {"status": status, "items": items}
        if code:
            out["code"] = code
        if driver_plans is not None:               # admissions mode only
            out["driver_plans"] = driver_plans
        audit.finalize(status, {"code": code, "results": items,
                                "plans": plans or [], "finished_at": now_fn()})
        return out

    # ---- source-first gates (§3): the stored source is the anchor ----
    src = store.get_source(run_input.source_id)
    if src is None:
        return _finish("failed",
                       [_item(i, "rejected", ["SOURCE_MISSING"]) for i in range(n)],
                       code="SOURCE_MISSING",
                       driver_plans=[] if admissions is not None else None)
    fye_month = src.get("fye_month")               # FYE comes from the STORED source's
                                                   # company, once — no caller override
    companies = store.get_source_companies(run_input.source_id)
    if len(companies) != 1:
        return _finish("dry_run" if not enable_writes else "committed",
                       [_item(i, "parked", ["SOURCE_COMPANY_AMBIGUOUS"],
                              detail=f"{len(companies)} companies via the ownership "
                                     f"relationship — multi-registrant is S4-era")
                        for i in range(n)],
                       driver_plans=[] if admissions is not None else None)

    # ---- PIT slice menu (step 7): fetched ONCE per event, cut at the stored
    # source's public time; refs verify FACT-LEVEL against the current filing
    # (match_xbrl_fact); law lives in slice_menu.py, retrieval in the store ----
    menu_tokens, menu_logs, fold_notes = None, [], {}
    xbrl_rows = {}                                 # concept -> verification rows,
    if any(pf.member_refs for pf in run_input.facts):  # fetched ONCE per event
        menu_raw = store.get_company_slice_menu(run_input.source_id, src["date"])
        menu_tokens, menu_logs = build_menu(menu_raw["xbrl_members"],
                                            menu_raw["used_scopes"])

    # ---- deterministic tail per fact ----
    items = {}
    staged = []                                    # (index, fact) surviving the tail
    resolved_drivers = {}                          # name -> the driver dict in force
    pending_create = {}                            # name -> fact_type (bundle owed)
    for i, pf in enumerate(run_input.facts):
        stored_driver = store.get_driver(pf.driver_name)
        a = admissions.get(i) if admissions is not None else None
        if a is None:
            driver = stored_driver
            if not driver or not driver.get("fact_type"):
                items[i] = _item(i, "parked", ["DRIVER_NOT_READY"],
                                 detail=f"driver {pf.driver_name!r} missing or untyped")
                continue
        elif stored_driver:
            # graph-backed: verify ALL THREE admission fields against the store
            if a["decision"] == "create":
                items[i] = _item(i, "parked", ["DRIVER_NOT_READY"],
                                 detail=f"admission requests CREATE but driver "
                                        f"{pf.driver_name!r} already exists — the "
                                        f"non-existence check failed")
                continue
            if (stored_driver.get("name") != a["driver_name"]
                    or stored_driver.get("fact_type") != a["fact_type"]):
                items[i] = _item(i, "parked", ["DRIVER_NOT_READY"],
                                 detail=f"graph-attach name/fact_type mismatch: "
                                        f"stored {stored_driver.get('name')!r}/"
                                        f"{stored_driver.get('fact_type')!r} != "
                                        f"admission {a['driver_name']!r}/"
                                        f"{a['fact_type']!r} — never silent")
                continue
            driver = stored_driver
        else:
            # CREATE or offline-card ATTACH: no graph node — the born-complete
            # bundle is PLANNED (same shape both, v2.5); fact_type FROM the
            # admission drives period resolution and validation
            driver = {"name": a["driver_name"], "fact_type": a["fact_type"]}
            pending_create[a["driver_name"]] = a["fact_type"]
        if a is not None:                      # admissions mode only — None mode
            resolved_drivers[pf.driver_name] = driver   # keeps the OLD read path
        res = _tail(i, pf, src, driver, fye_month, period_lookups,
                    run_input.calendar_override)
        if res[0] != "ok":
            items[i] = _item(i, res[0], res[1], detail=res[2])
            continue
        fact = res[1]
        if pf.member_refs is not None:             # the XBRL dims CLAIM — [] too
            fact["member_refs"] = [dict(r) for r in pf.member_refs]
            claim = {"time_type": pf.time_type, "start": pf.period_start_date,
                     "end": pf.period_end_date,
                     "dims": axis_member_pairs(pf.member_refs)}
            if pf.xbrl_concept_raw not in xbrl_rows:   # once per concept per event
                read = store.get_xbrl_fact_dimensions(
                    run_input.source_id, pf.xbrl_concept_raw)
                xbrl_rows[pf.xbrl_concept_raw] = read.rows
                # #828: the adapter's silent drops become visible here, ONCE per
                # concept (the cache guarantees it). v1 only CARRIES them — the
                # counting has one owner, in the adapter.
                menu_logs.extend(dict(x) for x in read.exclusions)
            matched = match_xbrl_fact(claim, xbrl_rows[pf.xbrl_concept_raw])
            if matched is None:
                items[i] = _item(i, "parked", ["MEMBER_LINK_INVALID"],
                                 detail="no fact in the current filing carries "
                                        "this exact concept + period + dimension "
                                        "set — the XBRL claim is unverifiable")
                continue
        if pf.member_refs:                         # step-7 member-ref law, pre-id
            fact_tokens = {f"{k}:{v}" for k, v in fact["slice_parts"]}
            problems, notes, ref_logs = check_member_refs(
                pf.member_refs, fact_tokens, menu_tokens, matched)
            menu_logs.extend(ref_logs)             # current-fact exclusions logged
            if problems:
                items[i] = _item(i, "parked", ["MEMBER_LINK_INVALID"],
                                 detail="; ".join(problems))
                continue
            fold_notes[str(i)] = notes             # FS-18 fold-vs-new, audit-bound
        try:
            fact_id, fact_scope = build_id(
                run_input.source_id, fact["driver_name"],
                period_id=fact["period_u_id"], slice_parts=fact["slice_parts"],
                measurement_tokens=fact["measurement_tokens"],
                surprise=fact["surprise"])
        except IdLawError as e:
            items[i] = _item(i, "rejected", ["ID_LAW"], detail=str(e))
            continue
        fact["id"], fact["fact_scope"] = fact_id, fact_scope
        staged.append((i, fact))

    # ---- FUSION on canonical values (units already ran) ----
    fused, fusion_parks = fuse_event([(i, f["id"], f) for i, f in staged])
    for park in fusion_parks:
        for i in park.indexes:
            items[i] = _item(i, "parked", [park.code], detail=park.reason)
            fusion_group_of[i] = park.indexes      # the group, not a new id

    # ---- full validation (REJECT beats PARK) ----
    final = []                                     # (FusedFact, driver)
    all_homes = [ff.fact for ff in fused if not ff.fact.get("surprise")]
    for ff in fused:
        # the driver IN FORCE for this fact: admission-constructed for pending
        # creations, stored otherwise (resolved once in the tail loop)
        driver = (resolved_drivers.get(ff.fact["driver_name"])
                  or store.get_driver(ff.fact["driver_name"]))
        homes = [h for h in all_homes if h is not ff.fact]
        violations = validate_fact(ff.fact, driver=driver, home_facts=homes)
        rejects = [x for x in violations if x.action == "REJECT"]
        parks = [x for x in violations if x.action == "PARK"]
        if rejects:                                # REJECT wins — fix first
            for i in ff.indexes:
                items[i] = _item(i, "rejected", [x.code for x in rejects],
                                 detail=rejects[0].message)
        elif parks:
            for i in ff.indexes:
                items[i] = _item(i, "parked", [x.code for x in parks],
                                 detail=parks[0].message)
        else:
            final.append((ff, driver))

    # ---- provisional plan (dry-run and real run share this exactly); prior guide
    # units ride along — the writer copies exactly ONE clear prior, else parks ----
    plans = []
    if final:
        results = plan_event_write([ff.fact for ff, _ in final], store,
                                   _prior_guide_units(final, store))
        for (ff, _), pr in zip(final, results):
            plans.append((ff, pr))

    # ---- surprise post-plan rule: a surprise writes ONLY if its home's final plan
    # is accepted — else park + whole-event re-extract (the F6 shape) ----
    accepted_ids = {pr.fact_id for ff, pr in plans if pr.outcome in _ACCEPTED}
    checked = []
    for ff, pr in plans:
        if ff.fact.get("surprise") and pr.outcome in _ACCEPTED:
            expected = _expected_home_name(ff.fact)
            home_ok = any(
                h_pr.outcome in _ACCEPTED
                and _home_mismatch(ff.fact, h_ff.fact, expected) is None
                for h_ff, h_pr in plans if h_ff is not ff)
            if not home_ok:
                for i in ff.indexes:
                    items[i] = _item(i, "parked", ["SURPRISE_HOME_NOT_ACCEPTED"],
                                     detail="home fact's final plan not accepted — "
                                            "park; re-extract the WHOLE event")
                accepted_ids.discard(pr.fact_id)
                continue
        checked.append((ff, pr))

    # ---- driver creation PLANS (v2.5 Step 3, dry-run only): group accepted
    # facts by driver_name; a pending Driver is planned ONLY if >=1 fact is
    # accepted (node invariant); exactly ONE create_driver per group, carrying
    # its born-complete evidence (name + fact_type + first fact + quote) ----
    driver_plans = None
    if admissions is not None:
        by_driver = {}
        for ff, pr in checked:
            if pr.outcome in _ACCEPTED and pr.fact_id in accepted_ids \
                    and ff.fact["driver_name"] in pending_create:
                by_driver.setdefault(ff.fact["driver_name"], []).append(
                    (min(ff.indexes), ff, pr))
        driver_plans = []
        for name in sorted(by_driver):
            entries = sorted(by_driver[name], key=lambda t: t[0])
            driver_plans.append({
                "op": "create_driver", "name": name,
                "fact_type": pending_create[name],
                "fact_ids": [pr.fact_id for _, _, pr in entries],
                "first_fact_id": entries[0][2].fact_id,
                # the LAWFUL evidence shape rebuild_anchor consumes:
                # driver_node.definitional_evidence.birth_quotes
                "definitional_evidence": {
                    "birth_quotes": [entries[0][1].fact["quote"]]}})
        # ATOMIC bundle (v2.5): the create_driver op HEADS its first accepted
        # fact's own plan ops — one dry-run group, never a detached side list
        first_ids = {p["first_fact_id"]: p for p in driver_plans}

        def _bundle(pairs):
            # each bundle injects EXACTLY once per Driver plan (belt: two prs
            # can share a fact_id only through writer-level dedup — held
            # unreachable post-fusion, but a double create must stay impossible)
            remaining = dict(first_ids)
            outp = []
            for ff, pr in pairs:
                p = remaining.pop(pr.fact_id, None)
                if p is not None and not (pr.ops and pr.ops[0].get("op")
                                          == "create_driver"):
                    pr = pr._replace(ops=[dict(p)] + list(pr.ops))
                outp.append((ff, pr))
            return outp
        plans = _bundle(plans)
        checked = _bundle(checked)

    # ---- write-ahead point: full provisional plan + fusion logs land in the audit
    # file (state stays `prepared`) BEFORE any mutation can happen ----
    plan_doc = [{"fact_id": pr.fact_id, "outcome": pr.outcome,
                 "code": pr.code, "ops": pr.ops} for _, pr in plans]
    audit_extra = {"plans": plan_doc,
                   "fusion_logs": [log for ff in fused for log in ff.logs]}
    if driver_plans is not None:
        audit_extra["driver_plans"] = driver_plans
    # EITHER a slice menu ran (FS-18 verdicts) OR something was excluded. The
    # menu test alone was a SECOND SILENT-DROP GATE: #828's exclusions were
    # collected into `menu_logs` and then discarded whenever no menu existed,
    # which is exactly the invisibility #828 exists to remove. A completely
    # clean no-menu run still emits nothing, so a quiet event stays quiet.
    if menu_tokens is not None or menu_logs:
        audit_extra["member_menu"] = {"folds": fold_notes,
                                      "exclusions": menu_logs}
    audit.update(audit_extra)

    approved = [(ff, pr) for ff, pr in checked
                if pr.outcome in _ACCEPTED and pr.fact_id in accepted_ids]
    status = "dry_run"
    run_code = None
    if enable_writes:
        lock_path = lock_path or os.path.join(audit_dir, "writer.lock")
        lockf = None

        def _park_all(code, detail):
            for ff, pr in approved:
                for i in ff.indexes:
                    items[i] = _item(i, "parked", [code], detail=detail)

        def _kept(checked):                        # planner parks SURVIVE a failed run
            return [(ff, pr) for ff, pr in checked if pr.outcome not in _ACCEPTED]

        try:
            assert_writes_enabled()
        except Exception as e:                     # gate missing = WRITE_GATE items
            _park_all("WRITE_GATE", str(e))
            return _finish("failed", _flatten(items, _kept(checked), n,
                                              executed=False),
                           code="WRITE_GATE", plans=plan_doc)
        try:
            import fcntl                           # MANDATORY one-writer lock
            lockf = open(lock_path, "w")
            try:
                fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                _park_all("WRITER_BUSY", "another writer holds the lock — "
                                         "nothing planned as final, nothing written")
                return _finish("failed", _flatten(items, _kept(checked), n,
                                                  executed=False),
                               code="WRITER_BUSY", plans=plan_doc)
            commit_time = now_fn()
            prov_types = {ff.fact["driver_name"]: drv["fact_type"]
                          for ff, drv in final}
            with store.transaction() as tx:
                # EVERY in-tx read goes through the tx object — one consistent
                # snapshot; the bare store is never read inside the transaction
                re_src = tx.get_source(run_input.source_id)
                if re_src != src or tx.get_source_companies(
                        run_input.source_id) != companies:
                    raise RuntimeError("in-tx recheck failed: the source (date/type/"
                                       "FYE/ticker) or its ONE company changed")
                for name, ftype in prov_types.items():
                    re_d = tx.get_driver(name)
                    if not re_d or re_d.get("fact_type") != ftype:
                        raise RuntimeError(f"in-tx recheck failed: driver {name!r} "
                                           f"vanished or re-typed")
                # FINAL plan happens INSIDE the tx: same reads, fresh graph state —
                # the provisional plan is audit/dry-run evidence, never executed blind
                final_plans = plan_event_write([ff.fact for ff, _ in final], tx,
                                               _prior_guide_units(final, tx))
                by_id = {pr.fact_id: pr for pr in final_plans}
                exact_ops = []
                for ff, prov in approved:
                    pr = by_id.get(prov.fact_id)
                    # the COMPLETE plan must match — outcome, code, and every op
                    if pr is None or (pr.outcome, pr.code, pr.ops) != (
                            prov.outcome, prov.code, prov.ops):
                        raise RuntimeError(
                            f"stale plan: {prov.fact_id} changed between provisional "
                            f"and in-tx planning — non-retried, resubmit")
                    for op in pr.ops:
                        if op.get("op") == "log":  # logs live in the AUDIT only —
                            continue               # zero new stored graph artifacts
                        if op.get("op") == "create_fact":
                            op = dict(op, props=dict(op["props"], created=commit_time))
                        exact_ops.append(op)
                # the EXACT ops (real timestamps included) become durable in the
                # audit BEFORE the first write — then exactly those ops execute
                audit.update({"final_plans": [
                    {"fact_id": pr.fact_id, "outcome": pr.outcome, "code": pr.code,
                     "ops": pr.ops} for pr in final_plans],
                    "final_ops": exact_ops, "commit_time": commit_time})
                for op in exact_ops:
                    tx.apply(op)
            status = "committed"
        except Exception as e:                     # NEVER retried; truthful rollback
            _park_all("EXECUTION_FAILED", f"transaction failed, nothing written: {e}")
            status, run_code = "failed", ("WRITE_GATE" if "ENABLE_DRIVER_WRITES"
                                          in str(e) else "EXECUTION_FAILED")
            approved = []
        finally:
            if lockf:
                lockf.close()

    out_items = _flatten(items, checked, n, executed=(status == "committed"))
    return _finish(status, out_items, code=run_code, plans=plan_doc,
                   driver_plans=driver_plans)


def _exact_index(v):
    """An EXACT non-negative int. `isinstance` admits bool and any int subclass,
    and the subclass then travels out as the public index — so this uses the
    project's exact-type style instead."""
    return type(v) is int and v >= 0


def _freeze_raw_accounting(raw_origin, n_raw, raw_terminals, n_facts):
    """THE raw-item accounting invariant, pure and BEFORE any I/O.

    `raw_origin[j]` is the raw position that produced prepared fact j — the
    smallest parallel relation, carried OUTSIDE PreparedFactV2. Every raw index
    is either linked to one-or-more facts OR has exactly one typed terminal;
    every prepared fact has one raw origin. Anything else is a CALLER BUG and
    raises: a fabricated public outcome would be worse than a loud stop."""
    # COPY FIRST, THEN VALIDATE. A generator is consumed by the check and the
    # later copy sees nothing, so the terminals vanished while validation passed.
    raw_origin = tuple(raw_origin)
    raw_terminals = tuple(raw_terminals)
    if not _exact_index(n_raw):
        raise RuntimeError(f"raw accounting: n_raw must be an exact count, got {n_raw!r}")
    if len(raw_origin) != n_facts:
        raise RuntimeError(
            f"raw accounting: {len(raw_origin)} origins for {n_facts} prepared "
            f"facts — every fact needs exactly one raw origin")
    for j, r in enumerate(raw_origin):
        if not _exact_index(r) or r >= n_raw:
            raise RuntimeError(
                f"raw accounting: prepared fact {j} claims raw origin {r!r}, "
                f"which is not an exact position below {n_raw}")
    seen = set()
    for t in raw_terminals:
        r = t.get("index")
        if not _exact_index(r) or r >= n_raw:
            raise RuntimeError(f"raw accounting: terminal claims raw {r!r}")
        if r in seen:
            raise RuntimeError(f"raw accounting: raw {r} has more than one terminal")
        seen.add(r)
    linked = set(raw_origin)
    both = linked & seen
    if both:
        raise RuntimeError(
            f"raw accounting: raw {sorted(both)} carries BOTH a produced fact and "
            f"a zero-fact terminal — contradictory")
    missing = set(range(n_raw)) - linked - seen
    if missing:
        raise RuntimeError(
            f"raw accounting: raw {sorted(missing)} is neither linked to a fact "
            f"nor given a terminal — never filled in silently")
    # FROZEN COPY, taken ONCE. The caller may hold a mutable list and change it
    # inside a later store callback; validating the caller's object and then
    # reading it again is a time-of-check/time-of-use hole that returned a raw
    # index the event never had.
    return raw_origin, tuple(_frozen_terminal(t) for t in raw_terminals)


def _frozen_terminal(t):
    """STRUCTURAL admissibility only — and that limit is deliberate.

    This refuses the shapes a caller must never send: not the five public fields,
    a fact_id on a zero-fact row, a non-terminal decision, or a code no owner
    declares. It does NOT certify that the decision/code PAIRING came from the
    typed emitter, and it must not pretend to: checking a pairing here would
    author a second mapping beside the real owner. At the V2 route the terminal
    is CONSTRUCTED by the existing typed emitter and accounting only joins it.
    The `skipped` code IS frozen (owner 2026-08-12, `READER_ABSTAINED`) and the
    V2 route constructs its terminals directly, so the open gap this note used to
    carry is closed. The structural-only limit stays deliberate: pairing belongs
    to the emitter, never to a second mapping here."""
    from driver.core.outcome_codes import OUTCOME_CODES
    if set(t) != {"index", "fact_id", "decision", "codes", "detail"}:
        raise RuntimeError(f"raw accounting: a terminal must carry exactly the "
                           f"five public fields, got {sorted(t)}")
    if t["fact_id"] is not None:
        raise RuntimeError("raw accounting: a zero-fact terminal has no fact_id")
    if t["decision"] not in ("skipped", "parked", "rejected"):
        raise RuntimeError(f"raw accounting: {t['decision']!r} is not a terminal "
                           f"decision for a raw item that produced no fact")
    # two SEPARATE owners, named as two — not merged into one pseudo-vocabulary
    # BUILD 838-843: every emitting non-written branch carries an EXPLICIT code.
    # A codeless terminal published a public outcome with no machine reason.
    if not t["codes"]:
        raise RuntimeError("raw accounting: a terminal carries no explicit code")
    bad = [c for c in t["codes"]
           if c not in OUTCOME_CODES and c not in CLI_CODES]
    if bad:
        raise RuntimeError(f"raw accounting: {bad} are declared by neither the "
                           f"outcome-code owner nor the CLI code owner")
    return _item(t["index"], t["decision"], list(t["codes"]), detail=t["detail"])


def _raw_rows(rows, raw_origin, raw_terminals, fusion_group_of=None):
    """THE one translation, at the ONE return boundary, so a normal finish, an
    early source failure, a write-gate refusal and a rollback all account the
    same way. `index` becomes the RAW position; a split keeps several rows."""
    out, seen = [], {}
    for row in rows:
        if "INTERNAL_UNTRACKED" in row["codes"]:
            raise RuntimeError(
                f"raw accounting: prepared fact {row['index']} disappeared inside "
                f"Core — an internal error, never a public outcome")
        raw = raw_origin[row["index"]]
        # A FAILED branch is NEVER deduped by value: two branches of one raw item
        # can fail with the same code and different detail, and content equality
        # cannot prove they are one relation — collapsing them LOSES a branch.
        # Only a SUCCESSFUL same-raw relation to the SAME final fact_id collapses,
        # because that is the actual fusion result.
        group = (fusion_group_of or {}).get(row["index"])
        if group is not None:
            # ONE failed fusion group -> ONE outcome per distinct raw item in it
            if (raw, group) in seen:
                continue
            seen[(raw, group)] = None
            out.append(dict(row, index=raw))
            continue
        fid = row["fact_id"]
        if fid is not None:
            prev = seen.get((raw, fid))
            if prev is not None:
                if prev != (row["decision"], tuple(row["codes"]), row["detail"]):
                    raise RuntimeError(
                        f"raw accounting: raw {raw} reaches fact {fid} with two "
                        f"different results — internal inconsistency, never a choice")
                continue
            seen[(raw, fid)] = (row["decision"], tuple(row["codes"]), row["detail"])
        out.append(dict(row, index=raw))
    out.extend(dict(t) for t in raw_terminals)
    out.sort(key=lambda r: r["index"])
    return out


def _prior_guide_units(final, reader):
    """Prior guide series units for the ONE case that needs them: a NUMBERLESS
    withdrawal/reaffirmation, whose series_unit copies exactly one clear prior.

    Hoisted out of `run_event` (it was a closure over `final`) so the V2 route
    calls the SAME rule rather than restating it. `reader` is the store on the
    provisional plan and the transaction on the final one — the caller decides,
    exactly as before.
    """
    out = {}
    for ff, drv in final:
        f = ff.fact
        if not (drv["fact_type"] == "guidance"
                and f["driver_state"] in ("withdrawn", "reaffirmed")
                and f["level_low"] is None and f["level_high"] is None
                and f["change_value"] is None and f["value_text"] is None):
            continue
        units = reader.get_prior_guide_units(f)
        if units:                                  # absent entry = no prior known
            out[f["id"]] = list(units)
    return out


def _flatten(items, planned, n, *, executed):
    for ff, pr in planned:
        for i in ff.indexes:
            if i in items:                         # already parked/rejected/overridden
                continue
            decision = _DECISION.get(pr.outcome, pr.outcome)
            codes = [pr.code] if pr.code else []
            items[i] = _item(i, decision, codes, fact_id=pr.fact_id,
                             detail=pr.reason)
    return [items.get(i) or _item(i, "parked", ["INTERNAL_UNTRACKED"],
                                  detail="index left the pipeline untracked — a CLI "
                                         "bug, never silent")
            for i in range(n)]

# ---------------------------------------------------------------------------
# THE V2 STAGE-A EVENT BOUNDARY (#827 Part 2).
#
# Core's own input contract, spelled from the published `staged_raw_channel`
# block in ChannelContractV2. Declared HERE rather than read from the document
# at runtime: production does not parse markdown. The block's own words govern
# what these mean — "Exact allowed spellings; lane-specific PRESENCE is
# described in prose, not implied here. Extra fields are not silently allowed."
# So ALLOWED is a closed set, and REQUIRED is only what §2 prose makes universal.
V2_EVENT_FIELDS = ("source_id", "source_type", "ticker", "fye_month",
                   "event_time", "text_parts", "items")
V2_ITEM_ALLOWED = ("raw_label_or_claim", "value", "fmt", "is_currency",
                   "period_end", "cadence", "quote", "period_evidence", "tier",
                   "quote_source", "xbrl")
V2_ITEM_REQUIRED = ("quote", "raw_label_or_claim")     # §2 prose: universal
V2_XBRL_FIELDS = ("concept", "period_start", "period_end", "ptype", "unit",
                  "ix", "source_evidence", "dimensions")
V2_IX_FIELDS = ("scale", "sign", "format", "unit_ref")
V2_DIM_FIELDS = ("axis", "member")
V2_REPLY_KEYS = ("source_id", "facts", "abstentions")
# FableExperimentWorkOrder:635 fixes the abstention shape EXACTLY.
V2_ABSTENTION_KEYS = ("quote", "reason", "part_ref", "occurrence_in_part")
# the envelope fields the STORED source owns; the channel may only echo them
V2_STORED_OWNED = ("source_type", "ticker", "fye_month")


def _exact_keys(obj, allowed, required, what):
    """Closed-set check DELEGATED to the one owner, plus the local required subset.

    `prepared_fact_v2._check_keys` never sorts or echoes the caller's keys — its
    own docstring records that sorting them raised a raw TypeError on mixed-type
    keys like {1, "zz"} and "survived in three doors after being fixed in one".
    Authoring a second sanitizer here made it a fourth. `missing` is safe to show
    because it is a subset of OUR key list.
    """
    from driver.core.prepared_fact_v2 import SchemaError, _check_keys
    if type(obj) is not dict:
        raise SchemaError(f"{what} must be an object, got {type(obj).__name__}")
    # exact=False: refuse EXTRAS but let the owner skip the missing check, since
    # lane-specific presence is prose law — then apply our own required subset.
    _check_keys(obj, allowed, what, exact=False)     # THE owner, never a second one
    missing = [f for f in required if f not in obj]
    if missing:
        raise SchemaError(f"{what}: missing required fields: {missing}")


def _check_v2_xbrl_identity(xb):
    """The raw identity `_v2_member_refs` CONSUMES before the sole door, checked
    at the pure boundary — concept, ptype, its context dates, and each
    axis/member. Every rule is DELEGATED:

      `xml_names.graph_qname_parts`  -> None for blank/non-string/unhashable
      `driver_period_resolver.PERIOD_TIME_TYPES` -> the two lawful time types
      `exact_numbers.stored_period_end` -> the exact date form
      `slice_menu.axis_member_pairs` -> the pair set (None = unusable)

    Without this, `dimensions=[{"axis": [], ...}]` reached `axis_member_pairs`
    and raised a raw `TypeError: unhashable type`, a blank axis performed a graph
    read and was then MISLABELLED `MEMBER_LINK_INVALID` rather than refused as
    malformed input, and — worst — any `ptype` other than the literal
    `"duration"` fell into `match_xbrl_fact`'s INSTANT branch and could match a
    real instant row. `unit`/`ix`/`source_evidence` are NOT rechecked here: they
    belong to the sole attach door and its certified binder.
    """
    from driver.core.driver_period_resolver import PERIOD_TIME_TYPES
    from driver.core.prepared_fact_v2 import SchemaError
    from driver.relocation.exact_numbers import ExactError, stored_period_end
    from driver.xml_names import graph_qname_parts

    if graph_qname_parts(xb["concept"]) is None:
        raise SchemaError("xbrl concept is not a usable qname")
    # OWNER-FROZEN 2026-08-12: an INSTANT context has no start. XBRL 2.1 §4.7.2
    # gives it an `instant` element, not a `startDate`, and Core V2 already
    # represents the absent internal period_start_date as None. So the raw
    # `period_start` MUST be JSON null — an empty string and a duplicated
    # instant date are NOT aliases. No conversion layer: the representation is
    # corrected at its own producer, and refused here.
    if xb["ptype"] == "instant" and xb["period_start"] is not None:
        raise SchemaError(
            "an instant xbrl context has no start: period_start must be null, "
            "not an empty string and not a duplicate of the instant date")
    if xb["ptype"] not in PERIOD_TIME_TYPES:
        raise SchemaError(
            f"xbrl ptype must be one of {PERIOD_TIME_TYPES} — an unlisted value "
            f"would silently take the instant branch")
    # BOTH lawful time types are matched against the stored EXCLUSIVE end, so
    # `end` is required and must be an exact date for either.
    try:
        stored_period_end(xb["period_end"])
    except (ExactError, ValueError, TypeError) as e:
        raise SchemaError(f"xbrl period_end is not an exact date: {e}")
    if xb["ptype"] == "duration":
        try:
            stored_period_end(xb["period_start"])   # same exact-date owner
        except (ExactError, ValueError, TypeError) as e:
            raise SchemaError(f"xbrl period_start is not an exact date: {e}")
    for dim in xb["dimensions"]:
        for field in V2_DIM_FIELDS:
            if graph_qname_parts(dim[field]) is None:
                raise SchemaError(f"xbrl dimension {field} is not a usable qname")
    pairs = axis_member_pairs(xb["dimensions"])
    if pairs is None:
        raise SchemaError("xbrl dimensions are not a usable axis/member set")
    return pairs                    # DERIVED ONCE — the route carries it on


def _check_v2_event(event):
    """The STRICT Stage-A boundary — every check pure, all of it BEFORE any I/O."""
    from driver.core.prepared_fact_v2 import SchemaError
    _exact_keys(event, V2_EVENT_FIELDS, V2_EVENT_FIELDS, "the Stage-A event")
    # THE ONE text-part owner already checks exact keys, string types, nonblank
    # labels AND duplicate labels. My own loop accepted two parts with the same
    # label, and the route then collapsed them with a dict comprehension so the
    # second silently overwrote the first (SEQ 994 item 2).
    from driver.core.xbrl_attach import _event_part_lookup
    parts = _event_part_lookup(event["text_parts"])
    # EXACT built-in containers: a generator is consumed by the first pass and a
    # str/dict would be walked as characters/keys (the attach-door lesson).
    if type(event["items"]) not in (list, tuple):
        raise SchemaError(
            f"items must be a list or tuple, got {type(event['items']).__name__}")
    # SOURCE ID — THE existing owner `driver_ids.valid_source_id`. Every bad id
    # ('x/y', '', None, 5, True, []) previously reached `store.get_source`, so
    # "all pure checks run before I/O" was not true (SEQ 1002 item 1). Its regex
    # is NOT copied here; the owner is called.
    if not valid_source_id(event["source_id"]):
        raise SchemaError("source_id is not a lawful source id")
    # SHAPE BEFORE MEMBERSHIP: `[]`/`{}` raised a raw `TypeError: unhashable
    # type` at the set test — the crash class these guards exist to exclude.
    if type(event["source_type"]) is not str:
        raise SchemaError(
            f"source_type must be a string, got "
            f"{type(event['source_type']).__name__}")
    # THE ONE vocabulary owner — `driver_validators.SOURCE_TYPES`. Copying the
    # published list into a `V2_SOURCE_TYPES` tuple created a third copy of a
    # rule that already had an owner (SEQ 1001).
    # EVENT TIME, at the PURE boundary — malformed channel stamps (None, a bare
    # date, a bad string, a list, a dict, the space-separator form) also reached
    # `store.get_source` first. The promoted owner runs HERE; the same-instant
    # comparison still happens after the source read (SEQ 1002 item 3).
    if parse_source_timestamp(event["event_time"]) is None:
        raise SchemaError(
            "event_time must be the full ISO source timestamp (date AND time)")
    if event["source_type"] not in SOURCE_TYPES:
        raise SchemaError(
            f"source_type must be one of {tuple(sorted(SOURCE_TYPES))} — the "
            f"published channel vocabulary")
    # ITEM-LOCAL, not event-wide (OWNER-FROZEN 2026-08-12): a malformed channel
    # item is ONE rejected row carrying CHANNEL_CONTRACT_INVALID, and its lawful
    # siblings still run. Event-level faults above stay event-wide.
    bad_items, xbrl_pairs = {}, {}
    for i, raw in enumerate(event["items"]):
        try:
            _exact_keys(raw, V2_ITEM_ALLOWED, V2_ITEM_REQUIRED, "a raw item")
            for f in V2_ITEM_REQUIRED:           # the two UNIVERSAL raw fields
                if type(raw[f]) is not str or not raw[f].strip():
                    raise SchemaError(
                        f"a raw item's {f} must be an exact non-blank string")
            if "xbrl" in raw:              # (absent = a lawful sparse TEXT item)
                xb = raw["xbrl"]
                _exact_keys(xb, V2_XBRL_FIELDS, V2_XBRL_FIELDS,
                            "a raw item's xbrl")
                _exact_keys(xb["ix"], V2_IX_FIELDS, V2_IX_FIELDS,
                            "an xbrl ix block")
                if type(xb["dimensions"]) is not list:
                    raise SchemaError("xbrl dimensions must be a list")
                for dim in xb["dimensions"]:
                    _exact_keys(dim, V2_DIM_FIELDS, V2_DIM_FIELDS,
                                "an xbrl dimension")
                xbrl_pairs[i] = _check_v2_xbrl_identity(xb)
        except SchemaError as exc:
            bad_items[i] = str(exc)
    # `xbrl_pairs[i]` is the identity owner's OWN result, carried out rather
    # than recomputed per item downstream (SEQ 1012 R7).
    return parts, bad_items, xbrl_pairs          # built ONCE, pre-I/O, reused


def _v2_same_quote(fact_quote, raw_quote):
    """The prepared fact must quote ITS OWN raw item verbatim. Exact equality on
    an already-validated value — no normalization, no content matching."""
    if fact_quote != raw_quote:
        from driver.core.prepared_fact_v2 import SchemaError
        raise SchemaError("a reader reply must quote its OWN raw item verbatim; "
                          "this reply restated the source")


def _v2_event_view(event, src):
    """What the per-item reader sees, built from the VERIFIED/STORED values.

    The raw POSITION stays in caller control and is never sent. The three
    stored-owned fields come from `src` — already proven equal to the envelope —
    so no conflicting channel value can reach the reader even if this function
    is later called before that check.

    `event_time` IS present and is the STORED canonical stamp — the reader needs
    the PIT cutoff, and omitting it would let a reader default or see later
    evidence. The channel's own value has already been proven to denote the same
    instant by `same_source_instant`; only the stored value travels.
    """
    view = {"source_id": event["source_id"], "text_parts": event["text_parts"],
            "event_time": src["date"]}          # the STORED canonical PIT stamp
    view.update({f: src[f] for f in V2_STORED_OWNED})
    return view


def _v2_check_reply(reply, source_id, raw, parts):
    """The exact `{source_id, facts, abstentions}` envelope, per raw item.

    `source_id` is the wrong-event ingestion guard. Exactly one of facts /
    abstentions carries content: both-empty says nothing about the item, and
    both-populated is two contradictory claims about the same raw position.

    THE ABSTENTION IS A CONTRACT, NOT A FREE-FORM NOTE. FableExperimentWorkOrder
    :635 fixes it as exactly `{quote, reason, part_ref, occurrence_in_part}`.
    Only the envelope was checked, so `{"wrong": "shape"}` became a public
    `skipped`/READER_ABSTAINED row — a typed outcome minted from an object that
    met no contract. An abstention must now locate itself exactly as a fact
    does: quoting its OWN raw item, in a part that exists, at the occurrence it
    names — through the SAME owners (`_v2_same_quote`, `verify_occurrence`).
    Malformed reader output stays a loud SchemaError; no second outcome exists.
    """
    from driver.core.prepared_fact_v2 import SchemaError, verify_occurrence
    _exact_keys(reply, V2_REPLY_KEYS, V2_REPLY_KEYS, "the reader reply")
    if reply["source_id"] != source_id:
        raise SchemaError(
            f"reader reply echoes source {reply['source_id']!r}, but this event "
            f"is {source_id!r} — wrong-event ingestion refused")
    facts, abst = reply["facts"], reply["abstentions"]
    if type(facts) is not list or type(abst) is not list:
        raise SchemaError("reader reply facts and abstentions must be lists")
    if bool(facts) == bool(abst):
        raise SchemaError(
            "a reader reply must carry facts OR exactly one abstention: "
            f"got {len(facts)} facts and {len(abst)} abstentions")
    if abst and len(abst) != 1:
        raise SchemaError(
            f"one raw item yields at most ONE abstention, got {len(abst)}")
    if abst:
        a = abst[0]
        _exact_keys(a, V2_ABSTENTION_KEYS, V2_ABSTENTION_KEYS,
                    "a reader abstention")
        if type(a["reason"]) is not str or not a["reason"].strip():
            raise SchemaError(
                "a reader abstention must give a nonblank reason — an untyped "
                "or empty one publishes a skipped row with no stated cause")
        # `part_ref` is used as a DICT KEY below, so its type must be checked
        # BEFORE the lookup: an unhashable `[]`/`{}` raised a raw TypeError
        # instead of the contract exception (SEQ 1014) — the same crash class as
        # the unhashable axis pair. Shape only; `verify_occurrence` still owns
        # whether the part exists and whether the quote occurs where it claims.
        if type(a["part_ref"]) is not str or not a["part_ref"].strip():
            raise SchemaError(
                "a reader abstention must name its part as an exact non-blank "
                f"string, got {type(a['part_ref']).__name__}")
        _v2_same_quote(a["quote"], raw["quote"])       # the SAME quote owner
        why = verify_occurrence(parts.get(a["part_ref"], ""), a["quote"],
                                a["occurrence_in_part"])
        if why:
            raise SchemaError(f"abstention occurrence check failed: {why}")


def _v2_member_refs(raw, store, source_id, pairs, rows_by_concept):
    """Public raw {axis, member} -> internal member_refs {axis, member,
    slice_part}, through the AUTHORIZED owners only (ChannelContractV2 §3-4).
    Labels come from the matched graph row; no rule is copied here."""
    from driver.core.driver_ids import encode_unknown_axis
    from driver.core.driver_member_fold import member_token
    from driver.core.slice_menu import classify_axis
    xb = raw["xbrl"]
    # THE PAIR SET HAS EXACTLY ONE OWNER — `slice_menu.axis_member_pairs` — and
    # it already ran in the pure boundary check, which REFUSES a repeated axis
    # before any I/O. Calling it again here ran the same rule twice per item;
    # the caller now carries the owner's own result in.
    claim = {"time_type": xb["ptype"], "start": xb["period_start"],
             "end": xb["period_end"], "dims": pairs}
    # THE REAL ADAPTER's method, the same one V1 calls. `store.xbrl_facts` is a
    # FakeStore-only convenience: Neo4jStore has no such attribute, so reading it
    # made this route work ONLY against the double (SEQ 991 item 1).
    # `.rows` — the adapter returns GraphFactRows(rows, exclusions); V1 reads
    # `.rows` the same way. Passing the namedtuple whole made match_xbrl_fact
    # iterate it as a 2-element sequence.
    # ONE READ PER CONCEPT PER EVENT: four CE items share one concept and made
    # four identical enrichment reads. The cache is EVENT-LOCAL — the caller
    # owns the dict and it dies with the run. Never global, never on the store.
    if xb["concept"] not in rows_by_concept:
        rows_by_concept[xb["concept"]] = store.get_xbrl_fact_dimensions(
            source_id, xb["concept"]).rows
    rows = rows_by_concept[xb["concept"]]
    matched = match_xbrl_fact(claim, rows)
    if matched is None:
        # `or []` turned an unverifiable nonempty claim into VERIFIED-EMPTY,
        # changing identity and evidence. V1's existing outcome (this file,
        # the MEMBER_LINK_INVALID branch) is the law: no exact concept + period
        # + dimension match -> park that item. None signals it to the caller.
        return None
    refs = []
    for row in matched:
        status, kind = classify_axis(row["axis"])
        token = (member_token(kind, row["label"]) if status == "slice"
                 else encode_unknown_axis(row["axis"], row["label"]))
        refs.append({"axis": row["axis"], "member": row["member"],
                     "slice_part": token})
    return refs


def _run_event_v2(event, *, store, audit_dir, reader, enable_writes=False,
                  now_fn=None, filing_provider=None):
    """THE Core V2 event route. ONE event in, five-field public rows out.

    Dry-run by default: `enable_writes=False` performs no mutation. The reader
    seam is PRIVATE and injected — it exists so the route can be proven before
    the real decomposer exists, and it is not a public contract.

    The reader-abstention `skipped` branch IS implemented (owner freeze
    2026-08-12): an abstention on a submitted item becomes a typed public
    `skipped` row carrying `READER_ABSTAINED`.
    """
    from driver.core import prepared_fact_v2
    from driver.core.prepared_fact_v2 import (PreparedFactV2, SchemaError,
                                              verify_occurrence)
    if enable_writes:
        # The V2 route is DRY-RUN ONLY until the writer is wired at the
        # owner-gated switch. Labelling rows "written" while writing nothing
        # would be a lie in the public output, so the flag is refused outright.
        raise WriterError("the V2 event route is dry-run only: enable_writes is "
                          "refused until the writer is wired at the switch")
    # NO WHOLE-EVENT COPY HERE, DELIBERATELY. The alias hazard is severed at the
    # ONE untrusted callback instead: the reader receives independent copies (see
    # the call site). An outer `deepcopy(event)` was tried and REMOVED — mutating
    # it away changed no observable behaviour, because the reader copies already
    # cut every alias and the attach door snapshots text parts/evidence itself
    # before its provider I/O. A second unobservable copy is not free either: it
    # turned a non-copyable event (a generator) into a raw TypeError, which then
    # needed its own repair. Smallest design that actually holds (SEQ 1013).
    parts, bad_items, xbrl_pairs = _check_v2_event(event)   # ALL pure, pre-I/O

    now_fn = now_fn or (lambda: __import__("datetime").datetime.utcnow()
                        .strftime("%Y-%m-%dT%H:%M:%S.%f"))
    source_id = event["source_id"]
    # THE WRITE-AHEAD AUDIT OPENS HERE, BEFORE THE SOURCE GATE — exactly where
    # V1 opens its own. BUILD 804-845 requires ONE never-overwritten audit file
    # per RUN, and both gate returns published a public result with ZERO audit
    # files: a run that decided something left no durable record that it ran.
    # Only the INPUT is hashed into the run id; Core's own raw accounting is
    # derived bookkeeping and is `update()`d in later, state still `prepared`.
    input_doc = {"source_id": source_id, "event": event}
    input_json = json.dumps(input_doc, default=_jsonable, sort_keys=True)
    run_id = (now_fn().replace(":", "").replace(".", "") + "_"
              + hashlib.sha256(input_json.encode()).hexdigest()[:12])
    audit = _Audit(audit_dir, run_id, {"input": json.loads(input_json),
                                       "input_bytes": input_json,
                                       "prepared_at": now_fn()})
    # SOURCE-FIRST, exactly as V1: the stored source and its company set gate the
    # whole event before any per-item work, through the REAL adapter methods.
    src = store.get_source(source_id)
    companies = store.get_source_companies(source_id) if src else ()
    gate = None
    if src is None:
        gate = ("rejected", "SOURCE_MISSING", f"no stored source {source_id!r}")
    elif len(companies) != 1:
        gate = ("parked", "SOURCE_COMPANY_AMBIGUOUS",
                f"source resolves to {len(companies)} companies, need exactly 1")
    if gate is not None:
        decision, code, detail = gate
        rows = [_item(i, decision, [code], detail=detail)
                for i in range(len(event["items"]))]
        # V1's status words, not a second vocabulary: a missing source FAILS the
        # run and carries the run-level code; an ambiguous company is a lawful
        # dry-run whose every row parked.
        status = "failed" if src is None else "dry_run"
        run_code = code if src is None else None
        audit.finalize(status, {"code": run_code, "results": rows, "plans": [],
                                "finished_at": now_fn()})
        out = {"status": status, "items": rows}
        if run_code:
            out["code"] = run_code
        return out
    # STORED metadata WINS — and now actually does. `_v2_event_view(event)` used
    # to hand the reader the untrusted envelope verbatim, so a channel could
    # steer decomposition with a different company or fiscal year while Core
    # later stored under the real source (SEQ 997 item B). The channel may only
    # ECHO these; a conflict is refused loudly at this staged step.
    for field in V2_STORED_OWNED:
        # EXACT ECHO — type AND value. `True == 1` is True in Python, so a bool
        # `fye_month` sailed past a value-only compare and produced a prepared
        # fact against stored `1` (SEQ 1002 item 4).
        if type(event[field]) is not type(src[field]) \
                or event[field] != src[field]:
            raise SchemaError(
                f"channel {field} does not match the stored source — the "
                f"channel may echo graph-owned metadata, never override it")
    # EVENT TIME — the PIT cutoff, verified through the ONE promoted owner.
    #
    # `15_CandidateFactPacket.md:136` fixes event_time = Report.created (the PIT
    # stamp) and FINAL_DESIGN makes the stored `date` the full source timestamp.
    # `driver_validators.same_source_instant` is that rule, now shared by the
    # validator and this check: aware/aware compares the INSTANT, naive/naive the
    # exact wall time, and MIXED awareness fails closed rather than invent a zone.
    # A missing, malformed or mismatched stamp stops BEFORE the reader.
    #
    # (`parse_filing_boundary` is deliberately NOT used: it owns XBRL
    # dateUnion-to-date binding and parking a timestamp is its correct behaviour,
    # not evidence that no owner exists. Reading its park as an UNKNOWN was my
    # error.)
    if not same_source_instant(event["event_time"], src["date"]):
        raise SchemaError(
            "channel event_time does not denote the same instant as the stored "
            "source timestamp — the PIT cutoff may not be steered by the channel")
    fye_month = src["fye_month"]
    view = _v2_event_view(event, src)
    n_raw = len(event["items"])

    origin, prepared, terminals = [], [], []
    rows_by_concept = {}          # EVENT-LOCAL enrichment cache (R7), not global
    door_items, door_origin, door_quote = [], [], []
    # ITEM-LOCAL malformed-channel rows (OWNER-FROZEN). The reader is never
    # asked about an item the channel already broke, and its siblings proceed.
    for i, why in sorted(bad_items.items()):
        terminals.append({"index": i, "fact_id": None, "decision": "rejected",
                          "codes": [CHANNEL_CONTRACT_INVALID], "detail": why})
    for index, raw in enumerate(event["items"]):        # THE CALLER'S OWN LOOP
        if index in bad_items:
            continue                     # already a rejected row; never read it
        # INDEPENDENT COPIES to the untrusted seam: whatever the reader does to
        # what it is given cannot reach the trusted snapshot Core audits.
        reply = reader(**copy.deepcopy(view), item=copy.deepcopy(raw))
        _v2_check_reply(reply, source_id, raw, parts)
        if reply["abstentions"]:
            # OWNER-FROZEN 2026-08-12: a reader abstention on a SUBMITTED item
            # is a typed public `skipped` row carrying READER_ABSTAINED. This
            # branch was fail-closed until the code existed; nothing was guessed.
            terminals.append({"index": index, "fact_id": None,
                              "decision": "skipped",
                              "codes": [READER_ABSTAINED],
                              "detail": reply["abstentions"][0].get("reason")})
            continue
        # ONCE PER RAW XBRL ITEM, never once per returned fact: a lawful split
        # with two facts and no graph match would otherwise emit TWO terminals
        # for one raw index, which the accounting owner correctly rejects as a
        # contradiction. A matched split reuses these same frozen refs.
        refs = None
        if "xbrl" in raw:
            refs = _v2_member_refs(raw, store, source_id, xbrl_pairs[index],
                                   rows_by_concept)
            if refs is None:
                terminals.append({
                    "index": index, "fact_id": None, "decision": "parked",
                    "codes": ["MEMBER_LINK_INVALID"],
                    "detail": "no fact in the current filing carries this exact "
                              "concept + period + dimension set — the XBRL claim "
                              "is unverifiable"})
                continue                          # never reaches the attach door
        for fact_dict in reply["facts"]:
            if "xbrl" in raw:                     # XBRL door: never from_dict
                door_items.append({
                    "fact": fact_dict, "concept": raw["xbrl"]["concept"],
                    "member_refs": refs,
                    "source_evidence": raw["xbrl"]["source_evidence"]})
                door_origin.append(index)
                door_quote.append(raw["quote"])
            else:                                 # model door + ONE occurrence
                # A SCHEMA-MALFORMED reader fact is a violation of the INJECTED
                # seam's own contract — a fixture bug, not a business outcome —
                # so it HARD-ERRORS exactly as a malformed admissions map does.
                # It is deliberately NOT converted into a public row: no
                # registered Core code covers it, and minting one is forbidden.
                # A "bad sibling" that stays local is a lawfully-shaped fact the
                # VALIDATOR rejects, which carries registered validator codes.
                fact = PreparedFactV2.from_dict(fact_dict)
                # ChannelContractV2 §2 (verbatim, never restated) + §7 (quote is
                # part of the locator). Compared on the TRUSTED value AFTER the
                # door — reading it off the untrusted reply dict beforehand would
                # be a partial model-schema parser in the route (SEQ 995).
                _v2_same_quote(fact.item.quote, raw["quote"])
                why = verify_occurrence(parts.get(fact.part_ref, ""),
                                        fact.item.quote, fact.occurrence_in_part)
                if why:
                    raise SchemaError(f"occurrence check failed: {why}")
                prepared.append(fact)
                origin.append(index)

    member_menu = None
    if door_items:
        from driver.core.xbrl_attach import attach_event_xbrl
        if filing_provider is None:
            # `test_round8_xbrl_binding` pins that Neo4jStore does NOT own
            # `get_filing_document`, so scraping the store for a provider could
            # never run the real door. It is a separate injected owner and its
            # absence FAILS CLOSED before anything is written.
            raise WriterError(
                "this event carries XBRL items but no filing_provider was "
                "supplied — the XBRL door cannot verify evidence; refusing")
        result = attach_event_xbrl(
            door_items, source_id=source_id, store=store,
            filing_provider=filing_provider, text_parts=event["text_parts"])
        member_menu = result.member_menu
        for subset_index, fact in result.facts:        # SUBSET -> RAW position
            _v2_same_quote(fact.item.quote, door_quote[subset_index])
            prepared.append(fact)
            origin.append(door_origin[subset_index])
        for row in result.preflight_outcomes:
            terminals.append({**dict(row), "index": door_origin[row["index"]]})

    raw_origin, raw_terminals = _freeze_raw_accounting(
        tuple(origin), n_raw, tuple(terminals), len(prepared))

    # The audit file already exists (opened before the source gate). Core's own
    # derived bookkeeping lands by `update`, so the state stays `prepared` and
    # the ONE file is never replaced by a second one.
    extra = {"raw_accounting": {"n_raw": n_raw, "origin": list(raw_origin),
                                "terminals": [dict(t) for t in raw_terminals]}}
    if member_menu is not None:                # #825: the door's audit SURVIVES
        extra["member_menu"] = member_menu
    audit.update(extra)

    # ---- CONVERSION + ID, once per prepared fact ----------------------------
    # `to_stored_fact` is the ONE owner that splits slice parts AND builds the
    # id (prepared_fact_v2:615-625). It used to run TWICE here — directly for
    # the id, then again inside `validate_via_production` — because the route
    # had nothing between the two halves of that composite. It now does: V1
    # puts FUSION between id-building and validation, so each half is called at
    # its own point and the duplicate conversion is gone.
    items, staged, drivers = {}, [], {}
    for i, fact in enumerate(prepared):
        driver = store.get_driver(fact.item.driver_name)
        if driver is None:
            items[i] = _item(i, "parked", ["DRIVER_NOT_READY"],
                             detail=f"no Driver {fact.item.driver_name!r}")
            continue
        # S4 Step 3 (55-57): the admitted Driver must agree on NAME *and*
        # fact_type. The reader's declared lane was simply dropped — every lane
        # rule downstream reads `driver["fact_type"]`, so a `guidance` fact on a
        # `metric` Driver validated as a metric and came back `written`. ONE
        # check here covers BOTH trust doors, and it reuses the existing
        # DRIVER_NOT_READY branch rather than minting a rule or a code.
        if fact.fact_type != driver["fact_type"]:
            items[i] = _item(
                i, "parked", ["DRIVER_NOT_READY"],
                detail=f"fact_type {fact.fact_type!r} does not match stored "
                       f"Driver {fact.item.driver_name!r} "
                       f"({driver['fact_type']!r})")
            continue
        # OD-21 STEP 1 — the surprise CONTRACT, before conversion and fusion.
        # NOT because fusion is mechanically unable to help: `comparison_baseline`
        # IS a signature field and fusion could fill a null one. It is the DESIGN
        # that decides — FINAL_DESIGN:152-153 requires the baseline on every
        # surprise item and composes before fusion, and BUILD:236 requires these
        # traps to fail with the RIGHT reason before fusion. Leaving them later
        # let fusion park the group as FUSION_AMBIGUOUS, and let
        # `compose_surprise_scope` fail in conversion as a generic park instead
        # of the exact F4/F5.
        # THE OWNER decides; the route only asks and publishes (SEQ 1016).
        od21 = _surprise_contract_violations(
            fact.item.surprise_basis_hint, fact.item.comparison_baseline,
            lane=driver["fact_type"])
        if od21:
            items[i] = _item(i, "rejected", [x.code for x in od21],
                             detail="; ".join(x.message for x in od21))
            continue
        try:
            stored = prepared_fact_v2.to_stored_fact(
                fact, driver=driver, source=src, fye_month=fye_month,
                source_id=source_id)
        except prepared_fact_v2.ProductionValidationError as exc:
            # ChannelContractV2 §9 + the exception's own docstring: callers PARK
            # these. The code is read STRUCTURALLY off the exception — never
            # parsed from its text — and nothing is minted. An unknown or
            # programming error is NOT caught here and still propagates loudly.
            code = getattr(exc, "code", None)
            if code is None:
                raise
            items[i] = _item(i, "parked", [code], detail=str(exc))
            continue
        # F7 needs the RESOLVED period, so it lands here — still before fusion.
        # Same shared predicate `_od21` uses; nothing is re-spelled.
        if _actual_surprise_before_period_end(
                fact.item.surprise_basis_hint, stored.get("gp_end_date"),
                stored.get("date")):
            items[i] = _item(
                i, "rejected", ["F7"],
                detail=f"actual surprise before period end "
                       f"({stored.get('gp_end_date')} > source day)")
            continue
        drivers[i] = driver
        staged.append((i, stored))

    # ---- FUSION on canonical values, keyed by the built id (V1's own key) ----
    # Fusion FILLS NULLS, so it must run BEFORE validation: validating first
    # would refuse fragments that fusion would have healed.
    fusion_group_of = {}
    fused, fusion_parks = fuse_event([(i, s["id"], s) for i, s in staged])
    for park in fusion_parks:
        for i in park.indexes:
            items[i] = _item(i, "parked", [park.code], detail=park.reason)
            fusion_group_of[i] = park.indexes      # the group, not a new id

    # ---- THE ONE RULE ENGINE, on the FUSED fact (REJECT beats PARK) ---------
    # `driver_validators.validate_fact` IS the single engine — the same one
    # `validate_via_production` delegates to. That composite takes a
    # PreparedFactV2 and has no parameter for a fused representative, which is
    # a stored dict no v2 fact corresponds to once nulls are filled. So the
    # route calls the engine directly, at the exact point V1 calls it. No
    # second engine, no wrapper, no re-validation.
    final = []                                     # (FusedFact, driver)
    all_homes = [ff.fact for ff in fused if not ff.fact.get("surprise")]
    for ff in fused:
        driver = drivers[ff.indexes[0]]
        homes = [h for h in all_homes if h is not ff.fact]
        violations = validate_fact(ff.fact, driver=driver, home_facts=homes)
        rejects = [x for x in violations if x.action == "REJECT"]
        parks = [x for x in violations if x.action == "PARK"]
        if rejects:                                # REJECT wins — fix first
            for i in ff.indexes:
                items[i] = _item(i, "rejected", [x.code for x in rejects],
                                 detail=rejects[0].message)
        elif parks:
            for i in ff.indexes:
                items[i] = _item(i, "parked", [x.code for x in parks],
                                 detail=parks[0].message)
        else:
            final.append((ff, driver))

    # ---- PROVISIONAL PLAN, through the ONE planner. DRY-RUN ONLY: nothing is
    # executed, and `enable_writes` was already refused at the top ------------
    plans = []
    if final:
        results = plan_event_write([ff.fact for ff, _ in final], store,
                                   _prior_guide_units(final, store))
        plans = list(zip((ff for ff, _ in final), results))

    plan_doc = [{"fact_id": pr.fact_id, "outcome": pr.outcome,
                 "code": pr.code, "ops": pr.ops} for _, pr in plans]

    # ---- surprise post-plan rule, V1's own (the F6 shape): a surprise stands
    # ONLY if its home's plan is accepted. This became reachable the moment the
    # route started planning — until this round a V2 surprise could not claim a
    # write at all, so its absence was invisible rather than harmless.
    checked = []
    for ff, pr in plans:
        if ff.fact.get("surprise") and pr.outcome in _ACCEPTED:
            expected = _expected_home_name(ff.fact)
            home_ok = any(
                h_pr.outcome in _ACCEPTED
                and _home_mismatch(ff.fact, h_ff.fact, expected) is None
                for h_ff, h_pr in plans if h_ff is not ff)
            if not home_ok:
                for i in ff.indexes:
                    items[i] = _item(i, "parked", ["SURPRISE_HOME_NOT_ACCEPTED"],
                                     detail="home fact's final plan not accepted — "
                                            "park; re-extract the WHOLE event")
                continue
        checked.append((ff, pr))

    audit.update({"plans": plan_doc,
                  "fusion_logs": [log for ff in fused for log in ff.logs]})
    rows = _raw_rows(_flatten(items, checked, len(prepared), executed=False),
                     raw_origin, raw_terminals, fusion_group_of)
    # V1's OWN status word. A bespoke "ok" beside `dry_run`/`committed`/`failed`
    # would be a second status vocabulary, and a row reading "written" under it
    # would claim a write that never happened.
    audit.finalize("dry_run", {"code": None, "results": rows,
                               "plans": plan_doc, "finished_at": now_fn()})
    return {"status": "dry_run", "items": rows}
