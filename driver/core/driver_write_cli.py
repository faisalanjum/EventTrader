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
import hashlib
import json
import os
from decimal import Decimal

from driver.core.driver_fusion import fuse_event
from driver.core.driver_ids import IdLawError, _slice_value, build_id, norm
from driver.core.driver_period_resolver import PeriodResolutionError, ensure_driver_period
from driver.core.driver_units import UnitResolutionError, resolve_driver_units
from driver.core.driver_validators import (_expected_home_name, _home_mismatch,
                                           compose_surprise_scope, validate_fact)
from driver.core.driver_writer import WriterError, assert_writes_enabled, plan_event_write
from driver.core.slice_menu import (build_menu, check_member_refs,
                                    match_xbrl_fact)

__all__ = ["CLI_CODES", "run_event", "load_run_input"]

# every code the CLI itself can emit (planner codes ride on PlanResult.code;
# validator codes ride on Violation.code) — the every-branch test pins this set
CLI_CODES = frozenset({
    "SOURCE_MISSING", "SOURCE_COMPANY_AMBIGUOUS", "DRIVER_NOT_READY",
    "SURPRISE_COMPOSE", "PERIOD_UNRESOLVED", "UNIT_UNRESOLVED",
    "MEMBER_LINK_INVALID", "ID_LAW", "FUSION_AMBIGUOUS", "F7", "EMPTY_LABEL",
    "SURPRISE_HOME_NOT_ACCEPTED", "EXECUTION_FAILED", "WRITER_BUSY", "WRITE_GATE",
    "INTERNAL_UNTRACKED",
})   # MEMBER_LINK_DEFERRED retired at step 7 (fence removed) — §11.4 amendment
     # pending owner approval; MEMBER_LINK_INVALID = ref-level law breach parks
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
            {k: getattr(pf, k) for k in
             ("period_start_date", "period_end_date", "fiscal_year",
              "fiscal_quarter", "half", "month", "long_range_start_year",
              "long_range_end_year", "sentinel_class", "time_type", "period_scope")},
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
        # F7 tense: an ACTUAL surprise on a not-ended period is impossible
        if (surprise.startswith("actual") and period and period["gp_end_date"]
                and period["gp_end_date"] > src["date"][:10]):
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
            value_is_guide=(pf.surprise_basis_hint == "guidance"))
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
              period_lookups=None, now_fn=None, input_bytes=None, admissions=None):
    """Run ONE source event end-to-end. Returns the flat §5 output:
    {status, code?, items: [{index, fact_id, decision, codes, detail}]}.

    admissions (S4 v2.5 Step 3, the ONE kernel handoff — dry-run PLANS only):
    None → today's behavior unchanged (a missing Driver parks DRIVER_NOT_READY).
    A map {fact_index: {decision, driver_name, fact_type}} → verified all-three
    both paths; missing Drivers plan ONE born-complete create_driver bundle per
    group; combining a supplied map with enable_writes HARD-FAILS."""
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
    input_json = json.dumps(input_doc, default=_jsonable, sort_keys=True)
    run_id = (now_fn().replace(":", "").replace(".", "") + "_"
              + hashlib.sha256(input_json.encode()).hexdigest()[:12])
    audit = _Audit(audit_dir, run_id, {
        "input": json.loads(input_json),
        "input_bytes": (input_bytes.decode("utf-8", "replace")
                        if input_bytes is not None else input_json),  # EXACT bytes
        "prepared_at": now_fn()})
    n = len(run_input.facts)

    def _finish(status, items, code=None, plans=None, driver_plans=None):
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
                     "dims": {(r["axis"], r["member"]) for r in pf.member_refs}}
            if pf.xbrl_concept_raw not in xbrl_rows:   # once per concept per event
                xbrl_rows[pf.xbrl_concept_raw] = store.get_xbrl_fact_dimensions(
                    run_input.source_id, pf.xbrl_concept_raw)
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
    def _priors(reader):
        out = {}
        for ff, drv in final:
            f = ff.fact                            # priors are queried ONLY for the
            if not (drv["fact_type"] == "guidance"  # numberless withdrawn/reaffirmed
                    and f["driver_state"] in ("withdrawn", "reaffirmed")
                    and f["level_low"] is None and f["level_high"] is None
                    and f["change_value"] is None and f["value_text"] is None):
                continue
            units = reader.get_prior_guide_units(f)
            if units:                              # absent entry = no prior known
                out[f["id"]] = list(units)
        return out

    plans = []
    if final:
        results = plan_event_write([ff.fact for ff, _ in final], store,
                                   _priors(store))
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
    if menu_tokens is not None:                    # step-7 menu ran: FS-18 verdicts
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
                                               _priors(tx))
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
