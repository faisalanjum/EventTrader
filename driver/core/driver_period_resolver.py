"""The ONE shared fiscal period resolver (FINAL_DESIGN §6.2, PER-01..20; GuidancePeriod.md).

Wraps the PROVEN guidance period machinery BY REFERENCE (never copied):
  - pure math: guidance_ids.build_guidance_period_id -> fiscal_math (99.1%-proven)
  - cascade:   existing-graph window -> SEC exact dates -> predicted quarter -> pure math
New-law deltas over the old substrate (each anchored): exact-date branch first + ytd/ttm
windows (GuidancePeriod.md) · calendar_override routed BEFORE any company lookup (BUILD §10
hazard) · time_type required, label hint never overrides (FACT-18) · no quiet gp_UNDEF, no
year-2000 months (FINAL §6.2 / BUILD §10) · 'long_range' scope retired -> exact_range (95 #23).

Resolution fails CLOSED: any ambiguity raises PeriodResolutionError -> the caller PARKS.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fiscal_math import _compute_fiscal_dates                      # the ONE calendar canon
from guidance_ids import SENTINEL_MAP, build_guidance_period_id   # proven pure builder

from driver.core.driver_ids import IdLawError, _validate_period_id

__all__ = ["PeriodResolutionError", "ensure_driver_period"]

_SENTINEL_IDS = frozenset(SENTINEL_MAP.values())
_FIELD_KEYS = ("period_start_date", "period_end_date", "fiscal_year", "fiscal_quarter",
               "half", "month", "long_range_start_year", "long_range_end_year",
               "sentinel_class", "period_scope")


class PeriodResolutionError(ValueError):
    """The period is ambiguous or under-specified. Callers PARK — never guess."""


def ensure_driver_period(item, *, fact_type, fye_month, ticker=None,
                         calendar_override=False, lookups=None):
    """Resolve one item's period. Returns {period_u_id, period_scope, time_type,
    gp_start_date, gp_end_date} or None when the fact truly has no period fields."""
    if item.get("period_u_id"):
        return _preserved(item)
    if not any(item.get(k) for k in _FIELD_KEYS):
        return None

    cal = bool(calendar_override or item.get("calendar_override"))
    time_type = item.get("time_type")
    if time_type not in ("duration", "instant"):
        raise PeriodResolutionError(
            f"time_type is a required semantic judgment (got {time_type!r}) — park")
    scope_in = item.get("period_scope")
    if scope_in not in (None, "ytd", "ttm"):
        raise PeriodResolutionError(f"input period_scope may only be ytd/ttm, got {scope_in!r}")

    # 1. exact source/XBRL dates ALWAYS win over computed math (test 20; 52/53-week safety)
    if item.get("period_start_date") or item.get("period_end_date"):
        return _exact_dates(item, time_type, scope_in)

    # 2. explicit sentinel
    sentinel = item.get("sentinel_class")
    if sentinel is not None:
        if sentinel not in SENTINEL_MAP:
            raise PeriodResolutionError(f"unknown sentinel_class: {sentinel!r}")
        return _result(SENTINEL_MAP[sentinel], sentinel, time_type, None, None)

    fye = 12 if cal else fye_month
    # every lookup call below sits behind a `ticker` guard, so the pure-math lane
    # (ticker=None / calendar mode) never triggers the heavy substrate import
    lk = lookups if lookups is not None else (_default_lookups() if ticker else None)

    # 3. ytd/ttm cumulative windows (fiscal math; exact dates already handled above)
    if scope_in in ("ytd", "ttm"):
        return _cumulative(item, scope_in, time_type, fye, cal, ticker, lk)

    # 4. proven cascade A/B/C — standard duration quarter/annual, company-fiscal only
    fy = item.get("fiscal_year")
    fq = item.get("fiscal_quarter")
    is_standard = (time_type == "duration" and not item.get("half") and not item.get("month")
                   and not item.get("long_range_end_year"))
    if is_standard and not cal and ticker and fy:
        found = lk["existing"](ticker, fy, fq)
        if found:
            return _result(found["period_u_id"],
                           found.get("period_scope") or ("quarter" if fq else "annual"),
                           found.get("time_type") or "duration",
                           found.get("start_date"), found.get("end_date"))
        sec = lk["sec"](ticker, fy, f"Q{fq}" if fq else "FY")
        if sec:
            return _result(f"gp_{sec['start']}_{sec['end']}",
                           "quarter" if fq else "annual", "duration",
                           sec["start"], sec["end"])
        if fq:
            pred = lk["predict"](ticker, fy, fq)
            if pred:
                return _result(f"gp_{pred['start']}_{pred['end']}", "quarter", "duration",
                               pred["start"], pred["end"])

    # 5. pure fiscal math (step D) with the new-law fail-closed guards
    if not cal and ticker:
        corrected = lk["corrected_fye"](ticker)
        if corrected is not None:
            fye = corrected
    if fye is None:
        raise PeriodResolutionError(
            "fye_month required to compute a company fiscal period — never default December")
    if item.get("month") and not item.get("fiscal_year"):
        raise PeriodResolutionError("month without fiscal_year — the year-2000 mint is forbidden")

    built = build_guidance_period_id(
        fye_month=fye,
        fiscal_year=item.get("fiscal_year"),
        fiscal_quarter=item.get("fiscal_quarter"),
        half=item.get("half"),
        month=item.get("month"),
        long_range_start_year=item.get("long_range_start_year"),
        long_range_end_year=item.get("long_range_end_year"),
        calendar_override=cal,
        sentinel_class=None,          # handled above
        time_type=time_type,
        label_slug=None,              # hint only — never allowed to override time_type
    )
    if built["u_id"] == "gp_UNDEF":   # the old quiet fallthrough — forbidden now
        raise PeriodResolutionError(f"period fields do not resolve: { {k: item.get(k) for k in _FIELD_KEYS} }")
    scope = "exact_range" if built["period_scope"] == "long_range" else built["period_scope"]
    return _result(built["u_id"], scope, built["time_type"],
                   built["start_date"], built["end_date"])


def _exact_dates(item, time_type, scope_in):
    start, end = item.get("period_start_date"), item.get("period_end_date")
    if not end:
        raise PeriodResolutionError("exact-date input needs period_end_date")
    if time_type == "instant":
        if start and start != end:
            raise PeriodResolutionError(f"instant with two different dates: {start}..{end}")
        start = end
    elif not start:
        raise PeriodResolutionError("duration exact-date input needs period_start_date")
    elif start == end:
        raise PeriodResolutionError(f"duration with start == end is illegal input: {start}")
    if scope_in in ("ytd", "ttm") and time_type == "instant":
        raise PeriodResolutionError(f"{scope_in} is a cumulative window — cannot be instant")
    return _result(f"gp_{start}_{end}", scope_in or "exact_range", time_type, start, end)


def _cumulative(item, scope, time_type, fye, cal, ticker, lk):
    if time_type != "duration":
        raise PeriodResolutionError(f"{scope} is a cumulative window — cannot be instant")
    if item.get("half") or item.get("month"):
        raise PeriodResolutionError(f"{scope} conflicts with half/month fields")
    fy = item.get("fiscal_year")
    if not fy:
        raise PeriodResolutionError(f"{scope} needs fiscal_year")
    if not cal and ticker:
        corrected = lk["corrected_fye"](ticker)
        if corrected is not None:
            fye = corrected
    if fye is None:
        raise PeriodResolutionError("fye_month required for ytd/ttm fiscal math")
    q = item.get("fiscal_quarter") or 4
    end = _compute_fiscal_dates(fye, fy, f"Q{q}")[1]
    if scope == "ytd":
        start = _compute_fiscal_dates(fye, fy, "Q1")[0]
    else:  # ttm: day after the same fiscal quarter's end one year earlier
        prior_end = _compute_fiscal_dates(fye, fy - 1, f"Q{q}")[1]
        start = (date.fromisoformat(prior_end) + timedelta(days=1)).isoformat()
    return _result(f"gp_{start}_{end}", scope, "duration", start, end)


def _preserved(item):
    u_id = item["period_u_id"]
    _check(u_id)
    if u_id in _SENTINEL_IDS:
        start = end = None
    else:
        start, end = u_id[3:13], u_id[14:]
    return _result(u_id, item.get("period_scope"), item.get("time_type"), start, end,
                   validate=False)


def _result(u_id, scope, time_type, start, end, validate=True):
    if validate:
        _check(u_id)
        if time_type == "instant" and start != end:
            raise PeriodResolutionError(f"instant must be a one-day window: {u_id}")
    return {"period_u_id": u_id, "period_scope": scope, "time_type": time_type,
            "gp_start_date": start, "gp_end_date": end}


def _check(u_id):
    try:
        _validate_period_id(u_id)
    except IdLawError as e:
        raise PeriodResolutionError(str(e))


def _default_lookups():
    """The live cascade (Neo4j/Redis), imported LAZILY by reference from the read-only
    guidance substrate — never at module import, so tests and dry-runs stay pure.
    Transition note (GuidancePeriod.md): the existing-window lookup still searches the old
    guidance graph; it gains DriverPeriod once DriverUpdates exist (writer step, S3.4/5)."""
    import guidance_write_cli as g
    return {"existing": g._lookup_existing_period, "sec": g._lookup_sec_cache,
            "predict": g._predict_from_prev_quarter, "corrected_fye": g._get_sec_corrected_fye}
