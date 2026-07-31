"""score_exp5 v5 — EXP-5 scoring per the work-order §4 pinned logic
(FableExperimentWorkOrder :641-643), round-13 adversarial corrections applied.

Pipeline per arm:
 1. MATCH produced items <-> du_worthy gold (same event): quote >=20-char
    overlap OR canonical value equality — computed on the UNWRAPPED items with
    EXACT decimal comparison (dec_canon over the resolver's scaled value; NO
    float rounding). A gold fact with >1 candidate is AMBIGUOUS: it stays
    UNSCORED and its actual rows are emitted for the qualified graders.
 2. recall = unambiguously-matched gold / du_worthy gold.
 3. fact16_checks + the HOME-FACT rule -> would_park (each item parks ONCE).
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

Dry-run: python scorers/score_exp5.py --dry3
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
from driver.core.driver_units import (UnitResolutionError,             # noqa: E402
                                      resolve_driver_units)

from fact16_checks import check_item                                    # noqa: E402

CODE_FIELDS = ["level_unit_kind_hint",
               "level_money_mode_hint", "change_unit_kind_hint",
               "change_money_mode_hint",
               "comparison_baseline", "level_shape_hint",
               "comparison_shape_hint", "surprise_basis_hint",
               "period_start_date", "period_end_date", "fiscal_year",
               "fiscal_quarter", "half", "month", "long_range_start_year",
               "long_range_end_year", "sentinel_class", "period_scope",
               "time_type", "value_text", "conditions",
               "company_confirmed"]
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
    return f.get("gold_item", f) if isinstance(f, dict) else {}


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
    """Canonical value view for ONE item via the PRODUCTION exact path
    (driver_units.resolve_driver_units: level+comparison share level's unit;
    change has its own). Returns {"level": [(unit, canon)...], "comparison":
    [...], "change": [...]} — dec_canon'd exact decimals, no float bridge."""
    lv = [_dec(item.get("level_low")), _dec(item.get("level_high"))]
    cv = [_dec(item.get("comparison_low")), _dec(item.get("comparison_high"))]
    ch = _dec(item.get("change_value"))
    try:
        r = resolve_driver_units(
            str(item.get("driver_name") or "x"),
            level_values=lv, level_unit_raw=item.get("level_unit_raw"),
            level_unit_kind_hint=item.get("level_unit_kind_hint"),
            level_money_mode_hint=item.get("level_money_mode_hint"),
            comparison_values=cv,
            change_value=ch, change_unit_raw=item.get("change_unit_raw"),
            change_unit_kind_hint=item.get("change_unit_kind_hint"),
            change_money_mode_hint=item.get("change_money_mode_hint"),
            period_scope=item.get("period_scope"))
        lu, cu = r["level_unit"], r["change_unit"]
        out = {"level": [(lu, dec_canon(v)) for v in r["level_values"]
                         if v is not None],
               "comparison": [(lu, dec_canon(v)) for v in
                              r["comparison_values"] if v is not None],
               "change": ([(cu, dec_canon(r["change_value"]))]
                          if r["change_value"] is not None else [])}
        return out
    except UnitResolutionError:
        # ONLY a genuine unit-resolution failure falls back to unscaled values.
        # The old `except (UnitResolutionError, Exception)` was redundant AND
        # total — UnitResolutionError already subclasses Exception, so the tuple
        # merely LOOKED targeted while swallowing TypeError/KeyError/any bug and
        # silently producing WRONG value comparisons. Real errors now surface.
        return {"level": [(None, dec_canon(v)) for v in lv if v is not None],
                "comparison": [(None, dec_canon(v)) for v in cv
                               if v is not None],
                "change": [(None, dec_canon(ch))] if ch is not None else []}


def _canon_level(item):
    return _canon_item_values(item)["level"]


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


def _value_eq(g_fact, p_fact):
    """Automatic matching requires COMPLETE slot equality — the WHOLE
    canonical positional list, never a shared endpoint (5-10 != 5-999)."""
    gc = _canon_item_values(_item(g_fact))
    pc = _canon_item_values(_item(p_fact))
    for slot in ("level", "comparison", "change"):
        if gc[slot] and gc[slot] == pc[slot]:
            return True
    return False


def _shape_pair(item):
    """POSITIONAL canonical (low, high) — a point (5,5) is NOT a floor (5,None)."""
    c = _canon_item_values(item)["level"]
    lo = c[0] if item.get("level_low") is not None and c else None
    hi = (c[-1] if item.get("level_high") is not None and c else None)
    return (lo, hi) if (lo or hi) else None


def _base_driver(name):
    name = name if isinstance(name, str) else ""
    return name[:-len("_surprise")] if name.endswith("_surprise") else name


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


def match(gold_facts, produced_items):
    """Per-event matching. A gold fact with EXACTLY one EVIDENCE candidate
    pairs; anything else -> AMBIGUOUS (unscored; rows go to the grader).

    NOTHING is proof of identity on its own. Shared source evidence is a
    candidate LINK (one sentence can carry several facts — "revenue was $100M in
    Q1 and $120M in Q2"); equal value is a weaker LEAD. The full graph is built
    FIRST, then a fixpoint commits only mutually-unambiguous evidence pairs, so
    the result can never depend on gold or produced ORDER. Any group of facts
    sharing one span goes to the grader.
    Name + value can NEVER prove fact identity — reproduced counter-examples:
      · `revenue $100M`  vs `capital_expenditures $100M`  (different driver)
      · Q1 `revenue $100M` vs Q2 `revenue $100M`          (different period)
      · segment A vs segment B, GAAP vs Adjusted          (different slice /
                                                           measurement)
    Each shares a name and/or a number while being a DIFFERENT fact; auto-pairing
    them credits recall for a MISSED gold fact and compares fields across
    unrelated facts. Value equality therefore only forms a grader CANDIDATE —
    surfaced, never silently dropped, never auto-credited.
    Returns (pairs, unmatched_gold, unmatched_produced, ambiguous_rows)."""
    # ---- 1. build the FULL candidate graph first (order-free by construction) ----
    ambiguous = []
    ev_links, val_links = {}, {}
    for gi, g in enumerate(gold_facts):
        ev, val = set(), set()
        for pi, p in enumerate(produced_items):
            gk, pk = _ev_key(g), _ev_key(p)
            if gk is not None and gk == pk:
                ev.add(pi)                   # shared span = a candidate LINK
            elif _value_eq(g, p):
                val.add(pi)                  # equal value = a grader LEAD only
        ev_links[gi], val_links[gi] = ev, val

    # ---- 2. fixpoint on EVIDENCE links; commit only mutually-unambiguous pairs ----
    pairs, used, resolved = [], set(), set()
    changed = True
    while changed:
        changed = False
        live = {gi: ev_links[gi] - used
                for gi in ev_links if gi not in resolved}
        singles = {gi: next(iter(c)) for gi, c in live.items() if len(c) == 1}
        claimed = {}
        for gi, pi in singles.items():
            claimed.setdefault(pi, []).append(gi)
        for pi, gis in sorted(claimed.items()):
            if len(gis) == 1:                # one gold wants it, it wants one gold
                pairs.append((gis[0], pi))
                used.add(pi)
                resolved.add(gis[0])
                changed = True
    pairs.sort()

    # ---- 3. everything unresolved that still has ANY link -> the grader ----
    for gi in sorted(ev_links):
        if gi in resolved:
            continue
        live_ev = sorted(ev_links[gi] - used)
        live_val = sorted(val_links[gi] - used)
        cands = live_ev or live_val
        if not cands:
            continue
        if live_ev:
            reason = ("shared_span_multiple_facts" if len(live_ev) == 1
                      else "multi_evidence_candidate")
        else:
            reason = ("value_match_same_name" if any(
                _name_agrees(gold_facts[gi], produced_items[pi]) for pi in cands)
                else "value_match_different_name")
        ambiguous.append({"gold_idx": gi, "gold_quote": gold_facts[gi].get("quote"),
                          "produced_idxs": cands, "reason": reason,
                          "produced_quotes": [produced_items[pi].get("quote")
                                              for pi in cands]})
    unmatched_gold = [i for i in range(len(gold_facts))
                      if i not in {a for a, _ in pairs}
                      and i not in {r["gold_idx"] for r in ambiguous}]
    unmatched_prod = [i for i in range(len(produced_items)) if i not in used]
    return pairs, unmatched_gold, unmatched_prod, ambiguous


def apply_resolutions(pairs, amb, resolutions, sid):
    """THE ONE place grader tie-rulings are applied — shared by score_arm and
    presence_disagreement so the two can never diverge.

    Enforces GLOBAL one-produced-to-one-gold. A CONFLICT — two or more gold rows
    ruled onto the SAME produced fact, or a ruling onto a fact already consumed
    by an automatic pair — is a GRADER ERROR, never a race: "first wins" would
    make the outcome depend on gold ORDER (reproduced: [Q1,Q2] credits Q1,
    [Q2,Q1] credits Q2). The WHOLE conflicting group is therefore REJECTED —
    neither gold is credited, EVERY involved ruling is flagged, and the result
    stays INCOMPLETE until a grader corrects it.
    Returns (extra_pairs, no_match_gold_idxs, unresolved_or_bad_rows)."""
    auto_used = {pi for _, pi in pairs}
    extra, no_match, bad = [], [], []
    wanted = {}                       # produced_idx -> [rows ruled onto it]
    for row in sorted(amb, key=lambda r: r["gold_idx"]):
        row["source_id"] = sid
        res = (resolutions or {}).get((sid, row["gold_idx"]), "UNSET")
        if res == "UNSET":
            bad.append(row)
        elif res is None:                       # graded: genuinely no match
            no_match.append(row["gold_idx"])
        elif res not in row["produced_idxs"]:   # ruling names a non-candidate
            bad.append(dict(row, bad_resolution=res))
        else:
            wanted.setdefault(res, []).append(row)
    for pi, rows in sorted(wanted.items()):
        if len(rows) > 1 or pi in auto_used:    # CONFLICT -> reject the GROUP
            reason = ("duplicate_resolution" if len(rows) > 1
                      else "resolution_targets_consumed_fact")
            for r in rows:
                bad.append(dict(r, bad_resolution=pi, conflict=reason,
                                conflicting_gold_idxs=[x["gold_idx"]
                                                       for x in rows]))
        else:
            extra.append((rows[0]["gold_idx"], pi))
    return extra, no_match, bad


def dedup_items(items):
    """Union dedup: ONLY truly identical COMPLETE facts collapse — the key is
    the full canonical JSON of the fact (lane + quote + the entire item)."""
    seen, out = set(), []
    for f in items:
        key = json.dumps({"lane": f.get("lane"), "quote": f.get("quote"),
                          "item": _item(f)}, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def _home_ok(sp, produced, fye):
    """FINAL_DESIGN:153 VERBATIM law: 'Match family, period, period scope,
    slice, measurement, and normalized value/unit when value-bearing; a
    numberless surprise needs a numberless home.' Both periods must RESOLVE
    (unresolved never matches anything)."""
    s_item = _item(sp)
    basis = s_item.get("surprise_basis_hint")
    home_lane = {"actual": "metric", "guidance": "guidance"}.get(basis)
    if home_lane is None:
        return False
    base = _base_driver(s_item.get("driver_name"))
    s_pid = _resolved_period(s_item, "surprise", fye)
    if not base or s_pid is None:
        return False                      # an unresolvable period never matches
    s_pair = _shape_pair(s_item)
    for h in produced:
        if h is sp or h.get("lane") != home_lane:
            continue
        h_item = _item(h)
        if _base_driver(h_item.get("driver_name")) != base:
            continue
        h_pid = _resolved_period(h_item, home_lane, fye)
        if h_pid is None or h_pid != s_pid:
            continue                      # BOTH resolved AND equal
        if s_item.get("period_scope") != h_item.get("period_scope"):
            continue
        if set(s_item.get("slice") or []) != set(h_item.get("slice") or []):
            continue
        if _meas_tokens(s_item) != _meas_tokens(h_item):
            continue
        if s_pair:
            if s_pair != _shape_pair(h_item):
                continue                  # POSITIONAL identity: point != floor
        else:
            if _shape_pair(h_item):
                continue                  # numberless needs a NUMBERLESS home
            hq = h_item.get("quote")
            if h_item.get("driver_state") != "unknown" or                     not (isinstance(hq, str) and hq.strip()):
                continue                  # rule 18: the UNKNOWN + QUOTE sibling
        return True
    return False


def score_arm(gold_by_event, arm_by_event, event_meta,
              grader_verdicts=None, ambiguity_resolutions=None):
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
    tot_gold = matched = 0
    lane_wrong = park = items_n = wrong_name = 0
    code_ok = code_all = 0
    state_ok = state_all = 0
    other_ok = other_all = 0
    verdicts_missing = ambiguities_unresolved = 0
    ambiguous_rows = []
    err = {}

    def _e(code):
        err[code] = err.get(code, 0) + 1

    for sid, gold in gold_by_event.items():
        du = [g for g in gold if g.get("du_worthy") is True]
        tot_gold += len(du)
        produced = (arm_by_event.get(sid) or {}).get("facts", [])
        meta = event_meta[sid]
        for p in produced:
            items_n += 1
            codes = check_item(_item(p), p.get("lane"),
                               event_date=meta.get("event_date"),
                               fye_month=meta.get("fye_month"))[0]
            parked = bool(codes)
            for c in codes:
                _e(f"park:{c}")
            if (not parked and p.get("lane") == "surprise"
                    and not _home_ok(p, produced, meta.get("fye_month"))):
                parked = True
                _e("park:HOME_FACT_MISSING")
            if parked:
                park += 1
        pairs, ug, up, amb = match(du, produced)
        resolved_amb, no_match, bad = apply_resolutions(
            pairs, amb, ambiguity_resolutions, sid)
        for row in bad:
            ambiguities_unresolved += 1
            ambiguous_rows.append(row)
        ug = ug + no_match
        pairs = pairs + resolved_amb
        matched += len(pairs)
        for gi, pi in pairs:
            g, p = du[gi], produced[pi]
            g_item, p_item = _item(g), _item(p)
            if g.get("lane") != p.get("lane"):
                lane_wrong += 1
                _e("wrong_lane:matched")
            gn, pn = g_item.get("driver_name"), p_item.get("driver_name")
            if gn != pn:
                wrong_name += 1            # a wrong driver is NEVER a 2% slip
                _e("wrong_name:driver_name")
            for f in CODE_FIELDS:
                gv_f, pv_f = g_item.get(f), p_item.get(f)
                if gv_f is None and pv_f is None:
                    continue               # comparing nothing is not agreement
                code_all += 1
                if gv_f == pv_f:
                    code_ok += 1
                else:
                    _e(f"mismatch:{f}")
            gc, pc = _canon_item_values(g_item), _canon_item_values(p_item)
            for slot in ("level", "comparison", "change"):
                code_all += 1
                if gc[slot] == pc[slot]:
                    code_ok += 1
                else:
                    _e(f"mismatch:value:{slot}")
            code_all += 1
            if set(g_item.get("slice") or []) == set(p_item.get("slice") or []):
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
        for gi in set(ug):
            g = du[gi]
            if (g.get("lane") == "surprise"
                    and (g.get("gold_extra") or {}).get(
                        "expectation_comparison_present")):
                lane_wrong += 1
                _e("wrong_lane:missing_gold_twin")
    recall = matched / tot_gold if tot_gold else 0.0
    would_park = park / items_n if items_n else 0.0
    value_shape_acc = code_ok / code_all if code_all else 1.0
    state_acc = state_ok / state_all if state_all else None
    complete = (verdicts_missing == 0 and ambiguities_unresolved == 0
                and state_acc is not None)
    # DEFINITE FAIL short-circuit: axes no verdict/resolution could repair —
    # even resolving every tie caps recall at potential_recall; wrong_lane
    # from code, parks, and code-field accuracy are verdict-independent
    potential_recall = ((matched + ambiguities_unresolved) / tot_gold
                        if tot_gold else 0.0)
    definite_fail = (potential_recall < 0.95 or would_park > 0.10
                     or value_shape_acc < 0.98 or lane_wrong > 0
                     or wrong_name > 0)
    gate = None
    if complete:
        gate = (recall >= 0.95 and lane_wrong == 0 and wrong_name == 0
                and value_shape_acc >= 0.98 and state_acc >= 0.95
                and would_park <= 0.10)
    elif definite_fail:
        gate = False
    rollup = {r: 0 for r in OD_RULES}
    rollup["other"] = 0
    for code, n in err.items():
        rollup[_bucket(code)] = rollup.get(_bucket(code), 0) + n
    return {"recall": round(recall, 4), "wrong_lane": lane_wrong,
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
            "error_table": err, "PASS": gate}


def score_union(gold_by_event, arm_a, arm_b, event_meta,
                grader_verdicts=None, ambiguity_resolutions=None):
    """Same-tier 2-run union: DEDUPLICATED item union per event, matched once."""
    union = {}
    for sid in gold_by_event:
        fa = (arm_a.get(sid) or {}).get("facts", [])
        fb = (arm_b.get(sid) or {}).get("facts", [])
        union[sid] = {"facts": dedup_items(list(fa) + list(fb))}
    return score_arm(gold_by_event, union, event_meta, grader_verdicts,
                     ambiguity_resolutions=ambiguity_resolutions)


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

    def _captured(arm, resolutions):
        got = {}
        for sid, gold in gold_by_event.items():
            du = [g for g in gold if g.get("du_worthy") is True]
            pairs, _, _, amb = match(du, (arm.get(sid) or {}).get("facts", []))
            extra, _no_match, bad = apply_resolutions(
                pairs, amb, resolutions, sid)
            invalid.extend([b for b in bad if "bad_resolution" in b])
            got[sid] = {gi for gi, _ in pairs} | {gi for gi, _ in extra}
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
    legs = [_leg(single_result, 0.95), _leg(union_result, 0.98)]
    if True in legs:
        return True
    if all(l is False for l in legs):
        return False
    return None


def _dry3():
    q = ("Revenue for the quarter was $726 million, up strongly versus the "
         "prior year period of last year")
    base = {k: None for k in (
        "driver_name driver_state quote level_low level_high change_value "
        "comparison_low comparison_high comparison_baseline value_text "
        "conditions company_confirmed level_unit_raw change_unit_raw "
        "level_unit_kind_hint level_money_mode_hint change_unit_kind_hint "
        "change_money_mode_hint level_shape_hint comparison_shape_hint "
        "surprise_basis_hint measurement_raw_spans period_start_date "
        "period_end_date fiscal_year fiscal_quarter half month "
        "long_range_start_year long_range_end_year sentinel_class time_type "
        "period_scope slice").split()}
    gold_item = dict(base, driver_name="revenue", driver_state="increased",
                     quote=q, level_low=726, level_high=726,
                     level_unit_raw="USD millions", level_shape_hint="point",
                     level_unit_kind_hint="money",
                     level_money_mode_hint="aggregate",
                     comparison_baseline="prior_year",
                     period_start_date="2026-01-01",
                     period_end_date="2026-03-31", time_type="duration",
                     measurement_raw_spans=[], slice=[])
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": gold_item,
                    "gold_extra": {"expectation_comparison_present": False}}]}
    good = {"E1": {"facts": [{"lane": "metric", "quote": q,
                              "gold_item": dict(gold_item)}]}}
    bad_item = dict(gold_item, level_high=None, level_unit_raw=None,
                    period_scope="quarter", surprise_basis_hint="actual")
    bad = {"E1": {"facts": [{"lane": "guidance", "quote": q,
                             "gold_item": bad_item}]}}
    META = {"E1": {"event_date": "2026-04-23", "fye_month": 12}}
    FULL = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    g = score_arm(gold, good, META, FULL)
    b = score_arm(gold, bad, META, FULL)
    held = score_arm(gold, good, META)            # verdicts withheld
    print("GOOD:", json.dumps({k: g[k] for k in
                               ("recall", "would_park", "PASS")}))
    print("BAD :", json.dumps({k: b[k] for k in
                               ("recall", "wrong_lane", "would_park", "PASS")}))
    print("HELD:", held["PASS"], f"(verdicts_missing={held['verdicts_missing']})")
    assert g["PASS"] is True and b["PASS"] is False and held["PASS"] is None
    assert final_gate(g, None) is True
    print("DRY-RUN v5: good PASSES · bad FAILS · withheld verdicts = "
          "INCOMPLETE(None) — executes and discriminates.")


if __name__ == "__main__":
    if "--dry3" in sys.argv:
        _dry3()
    else:
        print("usage: score_exp5.py --dry3")
        sys.exit(2)
