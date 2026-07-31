"""fact16_checks — the deterministic FACT-16 subset for EXP-5 scoring
(work-order §4 EXP-5 scoring logic step 3; authority = 12 FACT-16 + the 09 §4
matrix — NEVER 99 §7.2). Runs over ITEM dicts (the 34-field shape). Returns
(park_codes, notes) per item; would_park = any code. Rules implemented:
 3  lane matrix: value_text/conditions/company_confirmed GUIDANCE-only;
    metric FORBIDs expectation baselines (consensus, previous_guidance);
    guidance FORBIDs consensus (OD-21 symmetry)
 5  shape-hint coherence incl. the point-as-low-only trap (hint required when
    numbers present; FINAL_DESIGN:238)
 8  comparison_baseline enum
 9  unit-required-when: numeric level/comparison values need level_unit_raw
14  value_text lint: rejects numeric-valued text (allows anchors like Q2/2019)
15  start==end duration illegal (ISS-23: mark instant)
17  period_scope producer-side enum {ytd, ttm, null}
18  OD-21: surprise_basis_hint REQUIRED on surprise, FORBIDDEN elsewhere;
    surprise needs comparison_baseline; composed surprise= = basis x baseline
"""
import re

EXPECT_BASE = {"consensus", "previous_guidance"}
BASELINES = {"consensus", "prior_year", "sequential_period",
             "previous_guidance", None}
SHAPES = {"point", "range", "floor", "ceiling"}
_NUMY = re.compile(r"[$€£¥]\s?\d|\d+(\.\d+)?\s?%|\b\d+\s?bps\b|\b\d+(\.\d+)?\s?(million|billion|thousand)\b",
                   re.I)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _shape_code(low, high, hint, prefix):
    has = [x for x in (low, high) if x is not None]
    if has and not all(_num(x) for x in has):
        return [f"{prefix}_TYPE"]
    if not has:
        return [f"{prefix}_HINT_WITHOUT_NUMBERS"] if hint is not None else []
    if hint is None:
        return [f"{prefix}_HINT_MISSING"]
    if hint not in SHAPES:
        return [f"{prefix}_HINT_ILLEGAL"]
    actual = ("point" if low is not None and high is not None and low == high
              else "range" if low is not None and high is not None
              else "floor" if high is None else "ceiling")
    if low is not None and high is not None and low > high:
        return [f"{prefix}_REVERSED"]
    return [] if hint == actual else [f"{prefix}_HINT_MISMATCH"]


def check_item(item, lane, event_date=None, fye_month=None):
    codes, notes = [], []
    # 3 — lane matrix
    if lane != "guidance":
        for f in ("value_text", "conditions", "company_confirmed"):
            if item.get(f) is not None:
                codes.append(f"LANE_{f.upper()}_GUIDANCE_ONLY")
    if lane == "metric" and item.get("comparison_baseline") in EXPECT_BASE:
        codes.append("LANE_METRIC_EXPECTATION_BASELINE_FORBID")
    if lane == "guidance" and item.get("comparison_baseline") == "consensus":
        codes.append("LANE_GUIDANCE_CONSENSUS_FORBID")
    # 5 — shapes
    codes += _shape_code(item.get("level_low"), item.get("level_high"),
                         item.get("level_shape_hint"), "LEVEL")
    codes += _shape_code(item.get("comparison_low"), item.get("comparison_high"),
                         item.get("comparison_shape_hint"), "COMPARISON")
    # 8 — baseline enum
    if item.get("comparison_baseline") not in BASELINES:
        codes.append("BASELINE_ENUM")
    # 9 — unit-required-when
    numeric_present = any(_num(item.get(k)) for k in
                          ("level_low", "level_high", "comparison_low",
                           "comparison_high"))
    if numeric_present and not (item.get("level_unit_raw") or "").strip():
        codes.append("UNIT_REQUIRED_WHEN_NUMERIC")
    # FINAL_DESIGN:207 / 09 §3 Change row: change carries its OWN unit
    if _num(item.get("change_value")) and not (
            item.get("change_unit_raw") or "").strip():
        codes.append("CHANGE_UNIT_REQUIRED")
    # 14 — value_text lint
    vt = item.get("value_text")
    if isinstance(vt, str) and _NUMY.search(vt):
        codes.append("VALUE_TEXT_NUMERIC")
    # 15 — start==end duration
    if (item.get("time_type") == "duration"
            and item.get("period_start_date")
            and item.get("period_start_date") == item.get("period_end_date")):
        codes.append("START_EQ_END_DURATION")
    # 17 — producer-side period_scope
    if item.get("period_scope") not in ("ytd", "ttm", None):
        codes.append("PERIOD_SCOPE_ENUM")
    # 18 — OD-21: the composed surprise= must be one of the THREE legal types
    # (12 §10.5: actual_vs_consensus · actual_vs_guidance · guidance_vs_consensus);
    # a temporal baseline on a surprise is a metric CHANGE (never a surprise),
    # and guidance-vs-own-prior is a guidance MOVEMENT (case 0) — both park.
    LEGAL_SURPRISE = {("actual", "consensus"): "actual_vs_consensus",
                      ("actual", "previous_guidance"): "actual_vs_guidance",
                      ("guidance", "consensus"): "guidance_vs_consensus"}
    basis = item.get("surprise_basis_hint")
    if lane == "surprise":
        if basis not in ("actual", "guidance"):
            codes.append("SURPRISE_BASIS_REQUIRED")
        bl = item.get("comparison_baseline")
        if bl is None:
            codes.append("SURPRISE_BASELINE_REQUIRED")
        elif (basis, bl) not in LEGAL_SURPRISE:
            codes.append("SURPRISE_TYPE_ILLEGAL")
        else:
            notes.append(f"surprise={LEGAL_SURPRISE[(basis, bl)]}")
        # impossible tense: a reported ACTUAL cannot cover a period ending
        # after the event date — uses the RESOLVED end via the PRODUCTION
        # resolver so fiscal-only periods (no exact dates) are covered too
        if basis == "actual" and event_date and fye_month is not None:
            import os as _os
            import sys as _sys
            _repo = _os.path.abspath(_os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "..", "..", "..", "..", "..", ".."))
            if _repo not in _sys.path:
                _sys.path.insert(0, _repo)
            from driver.core.driver_period_resolver import (
                PeriodResolutionError, ensure_driver_period)
            try:
                r = ensure_driver_period(item, fact_type="surprise",
                                         fye_month=fye_month)
            except PeriodResolutionError:
                r = None                    # the period park is scored elsewhere
            if r and (r.get("gp_end_date") or "") > event_date:
                codes.append("IMPOSSIBLE_TENSE_ACTUAL_FUTURE")
    elif basis is not None:
        codes.append("SURPRISE_BASIS_FORBID_OFF_LANE")
    return codes, notes
