"""FACT-16 deterministic validators + the OD-21 surprise machinery (FINAL_DESIGN §4.3/§5.1/§7).

Every check is code, machine-readable, and fail-closed: REJECT = contract violation
(fix and resubmit) · PARK = waits for its blocker. The lane is the DRIVER's permanent
fact_type — a fact never declares its own lane. Dormant ratified-XBRL fields (origin,
xbrl_fact_id, attach_mode...) are NOT in the allowed field set, so they REJECT while
the materializer stays dormant — flip = extending _ALLOWED_FIELDS under owner order.
"""
import math
import re
from collections import namedtuple
from datetime import date, datetime
from decimal import Decimal

from driver.core.driver_ids import IdLawError, build_id, num_canon
from driver.core.driver_units import DRIVER_UNITS

__all__ = ["Violation", "validate_fact", "compose_surprise_scope",
           "surprise_position", "apply_inline_correction"]

Violation = namedtuple("Violation", "code action message")

LANES = ("metric", "guidance", "surprise", "action_event")
LANE_STATES = {
    "metric": {"increased", "decreased", "unchanged", "mixed", "reported", "persists",
               "unknown"},
    "guidance": {"introduced", "raised", "lowered", "reaffirmed", "withdrawn", "unknown"},
    "surprise": {"beat", "in_line", "missed", "unknown"},
    "action_event": {"at_risk", "announced", "occurred", "continued", "resolved",
                     "canceled", "suspended", "rumored", "failed", "unknown"},
}
BASELINES = {"consensus", "prior_year", "sequential_period", "previous_guidance"}
LANE_BASELINES = {"metric": {"prior_year", "sequential_period"},
                  "guidance": BASELINES - {"consensus"},
                  "surprise": {"consensus", "previous_guidance"},
                  "action_event": BASELINES}
SOURCE_TYPES = {"8k", "transcript", "10q", "10k", "news"}
PERIOD_SCOPES = {"quarter", "annual", "half", "monthly", "ytd", "ttm", "exact_range",
                 "short_term", "medium_term", "long_term", "undefined"}
SENTINEL_SCOPE = {"gp_ST": "short_term", "gp_MT": "medium_term", "gp_LT": "long_term",
                  "gp_UNDEF": "undefined"}
SURPRISE_TYPES = {"actual_vs_consensus", "actual_vs_guidance", "guidance_vs_consensus"}

_ALLOWED_FIELDS = frozenset({
    "driver_name", "driver_state", "quote", "date", "source_type", "event_time",
    "level_low", "level_high", "level_unit", "change_value", "change_unit",
    "comparison_low", "comparison_high", "comparison_baseline",
    "value_text", "conditions", "company_confirmed", "xbrl_qname",
    "fiscal_year", "fiscal_quarter", "period_scope", "time_type",
    "period_u_id", "gp_start_date", "gp_end_date",
    "slice_parts", "measurement_tokens", "surprise", "fact_scope_period_token",
    "level_shape_hint", "comparison_shape_hint", "surprise_basis_hint",
    "id", "fact_scope", "member_refs",
})
_NUMERIC_FIELDS = ("level_low", "level_high", "change_value",
                   "comparison_low", "comparison_high")
# value_text: numberless only — reject attached numeric values; bare 19xx/20xx year
# anchors are legal ("similar to 2024 levels")
_VALUE_TEXT_NUMERIC = re.compile(
    r"[$€£¥]\s*\d|\d+(?:\.\d+)?\s*%|\d+\.\d+|\b(?!(?:19|20)\d\d\b)\d+\b")


def _num_error(val):
    """Exact-number gate: int/Decimal only, inside the declared storage domain
    (<=15 significant digits after trailing-zero strip; integers within Neo4j's long).
    These checks run on EXACT values, so — unlike any float heuristic — they prove
    the source number is preserved end-to-end."""
    if val is None:
        return None
    if isinstance(val, bool) or isinstance(val, float) or \
            not isinstance(val, (int, Decimal)):
        return (f"must be an EXACT number (int/Decimal), got {type(val).__name__} — "
                f"parse the packet with parse_float=Decimal; floats are banned")
    d = Decimal(val)
    if not d.is_finite():
        return f"must be finite, got {val!r}"
    if len(d.normalize().as_tuple().digits) > 15:
        return (f"{val!r} exceeds the numeric storage domain "
                f"(>15 significant digits cannot round-trip float64 storage)")
    if isinstance(val, int) and abs(val) >= 2 ** 63:
        return f"{val!r} exceeds the storable integer range (Neo4j long)"
    return None


def compose_surprise_scope(basis_hint, comparison_baseline):
    """OD-21: CODE composes the surprise= slot from basis x baseline, pre-fusion."""
    pair = (basis_hint, comparison_baseline)
    if pair == ("actual", "consensus"):
        return "actual_vs_consensus"
    if pair == ("actual", "previous_guidance"):
        return "actual_vs_guidance"
    if pair == ("guidance", "consensus"):
        return "guidance_vs_consensus"
    if pair == ("guidance", "previous_guidance"):
        raise ValueError("guide vs own prior guide is guidance movement, never a surprise")
    raise ValueError(f"cannot compose surprise scope from {pair!r}")


def surprise_position(low, high, exp_low, exp_high, *, value_is_guide=False):
    """Polarity-free position of a compared value vs the expectation shape.

    Containment asymmetry (§4.3, exact law): a GUIDE range containing the consensus
    point is in_line-eligible ('including a guide RANGE that contains the consensus
    point'); an ACTUAL range bracketing the expectation is the UNCLEAR overlap case
    ('an actual range overlapping the expectation unclearly -> unknown unless the
    source states favorability')."""
    if exp_low is not None and exp_high is not None:                    # closed shape
        if low == exp_low == exp_high == high:
            return "inside"
        if low is not None and high is not None:
            if exp_low <= low and high <= exp_high:
                return "inside"                    # value inside the expectation range
            if value_is_guide and low <= exp_low and exp_high <= high:
                return "inside"                    # guide RANGE containing consensus (P3)
            if low > exp_high:
                return "above"
            if high < exp_low:
                return "below"
        return "overlap"
    if exp_low is not None:                                             # floor
        return "at_floor" if low == exp_low and high == exp_low else (
            "above" if low is not None and low > exp_low else "overlap")
    if exp_high is not None:                                            # ceiling
        return "at_ceiling" if low == exp_high and high == exp_high else (
            "below" if high is not None and high < exp_high else "overlap")
    return "overlap"


def apply_inline_correction(state, position, *, has_favorability_wording):
    """Code SETS in_line whenever there is NO favorability wording and the compared
    value sits inside/at a closed expectation shape (§4.3) — that includes a wordless
    `unknown` inside the range, and CORRECTS a wordless beat/missed. Stated
    favorability wording is never overridden (meaning beats arithmetic, OD-13)."""
    if (not has_favorability_wording
            and state in ("beat", "missed", "unknown")
            and position in ("inside", "at_floor", "at_ceiling")):
        return "in_line"
    return state


def validate_fact(fact, *, driver, home_facts=None):
    v = []
    add = lambda code, action, msg: v.append(Violation(code, action, msg))

    for key in fact:
        if key not in _ALLOWED_FIELDS:
            add("UNKNOWN_FIELD", "REJECT", f"field {key!r} is not in the stored contract")

    lane = (driver or {}).get("fact_type")
    if lane not in LANES:
        add("DRIVER", "REJECT", f"driver {fact.get('driver_name')!r} has no permanent "
                                f"fact_type — a typeless Driver cannot accept a fact")
        return v
    if driver.get("name") is not None and fact.get("driver_name") != driver["name"]:
        add("DRIVER", "REJECT", f"fact names driver {fact.get('driver_name')!r} but was "
                                f"validated against {driver['name']!r}")

    # TERMINAL numeric regime (round 7): numbers must be EXACT (int/Decimal). A float
    # may have already lost source digits at parse time, so floats reject wholesale —
    # dust can never enter, and nothing needs to "prove" preservation after the fact.
    malformed = False
    for k in _NUMERIC_FIELDS:
        val = fact.get(k)
        err = _num_error(val)
        if err:
            add("MALFORMED", "REJECT", f"{k}: {err}")
            malformed = True
    if malformed:
        return v

    # the CLI order builds id + fact_scope BEFORE validation — both are required here
    if fact.get("id") is None or fact.get("fact_scope") is None:
        add("ID", "REJECT", "id and fact_scope are required at validation time")

    if not fact.get("quote"):
        add("QUOTE", "REJECT", "verbatim quote required on every lane")
    if fact.get("source_type") not in SOURCE_TYPES:
        add("ISO", "REJECT", f"bad source_type {fact.get('source_type')!r}")
    try:
        datetime.fromisoformat(fact.get("date") or "")
        if "T" not in fact["date"]:
            raise ValueError("date-only")           # a bare date is NOT a full timestamp
    except (ValueError, TypeError, KeyError):
        add("ISO", "REJECT", f"date must be the full ISO source timestamp "
                             f"(date AND time), got {fact.get('date')!r}")
    if fact.get("driver_state") not in LANE_STATES[lane]:
        add("STATE", "REJECT",
            f"state {fact.get('driver_state')!r} outside the {lane} lane")

    _id_rebuild(fact, add)

    _shape(fact, "level", v)
    _shape(fact, "comparison", v)

    lo, hi = fact.get("level_low"), fact.get("level_high")
    clo, chi = fact.get("comparison_low"), fact.get("comparison_high")
    change = fact.get("change_value")

    if change is not None and fact.get("driver_state") in ("increased", "raised") \
            and change <= 0:
        add("SIGN", "REJECT", "increased/raised requires a positive change_value")
    if change is not None and fact.get("driver_state") in ("decreased", "lowered") \
            and change >= 0:
        add("SIGN", "REJECT", "decreased/lowered requires a negative change_value")

    baseline = fact.get("comparison_baseline")
    if baseline is not None:
        if baseline not in BASELINES:
            add("BASELINE", "REJECT", f"unknown baseline {baseline!r}")
        elif baseline not in LANE_BASELINES[lane]:
            add("BASELINE", "REJECT", f"baseline {baseline!r} forbidden on the {lane} lane")

    level_unit, change_unit = fact.get("level_unit"), fact.get("change_unit")
    for name, unit in (("level_unit", level_unit), ("change_unit", change_unit)):
        if unit is not None and unit not in DRIVER_UNITS:
            add("UNIT", "REJECT", f"{name} {unit!r} not in the 10-unit enum")
    if any(x is not None for x in (lo, hi, clo, chi)):
        if level_unit is None:
            add("UNIT", "REJECT", "level_unit required with numbers present")
    elif level_unit is not None and level_unit not in ("percent_yoy",
                                                       "percent_sequential"):
        add("UNIT", "REJECT", f"level_unit {level_unit!r} without numbers — only a "
                              f"numberless GROWTH fact may take a unit from source "
                              f"framing (OD-11)")
    if change is not None and change_unit is None:
        add("UNIT", "REJECT", "change_unit required with change_value present")
    if change is None and change_unit is not None:
        add("UNIT", "REJECT", "change_unit without change_value")
    if fact.get("period_scope") == "annual" and "percent_sequential" in (
            fact.get("level_unit"), fact.get("change_unit")):
        add("UNIT", "REJECT", "percent_sequential is invalid on an annual period (OD-11)")

    _period(fact, v, add)
    _period_lane(fact, lane, add)
    _lane_matrix(fact, lane, v, add)
    _movement(fact, lane, add)

    if lane == "surprise":
        _od21(fact, add, home_facts)
    else:
        if fact.get("surprise") is not None:
            add("F2", "REJECT", "surprise= slot is forbidden outside the surprise lane")
        if fact.get("surprise_basis_hint") is not None:
            add("F3", "REJECT", "surprise_basis_hint is forbidden outside the surprise lane")
    return v


_VALID_SHAPES = frozenset({"point", "range", "floor", "ceiling"})


def _shape(fact, prefix, v):
    low, high = fact.get(f"{prefix}_low"), fact.get(f"{prefix}_high")
    hint = fact.get(f"{prefix}_shape_hint")
    if hint is not None and hint not in _VALID_SHAPES:
        v.append(Violation("SHAPE", "REJECT", f"{prefix} hint {hint!r} is not a shape"))
        hint = None                                   # never lets 'invalid' self-certify
    if low is None and high is None:
        if hint is not None:
            v.append(Violation("SHAPE", "REJECT", f"{prefix} hint without numbers"))
        return
    if low is not None and high is not None and low > high:
        v.append(Violation("SHAPE", "REJECT",
                           f"{prefix} reversed range: {low} > {high}"))
        return
    actual = ("point" if low is not None and high is not None and low == high else
              "range" if low is not None and high is not None else
              "floor" if high is None else "ceiling")
    if hint is None:
        v.append(Violation("SHAPE", "REJECT",
                           f"{prefix}_shape_hint required when numbers present"))
    elif hint != actual:
        v.append(Violation("SHAPE", "REJECT",
                           f"{prefix} hint {hint!r} != actual shape {actual!r}"))


def _period(fact, v, add):
    u_id, scope = fact.get("period_u_id"), fact.get("period_scope")
    start, end = fact.get("gp_start_date"), fact.get("gp_end_date")
    if (u_id is None) != (scope is None):
        add("PERIOD_SYM", "REJECT", "period_u_id and period_scope must travel together")
    token = fact.get("fact_scope_period_token")
    if token is not None and token != u_id:
        add("PERIOD_SYM", "REJECT",
            f"fact_scope period token {token!r} != HAS_PERIOD target {u_id!r}")
    if scope is not None and scope not in PERIOD_SCOPES:
        add("SCOPE_PAIR", "REJECT", f"period_scope {scope!r} not in the enum")
    if u_id is None:
        return
    if fact.get("time_type") not in ("duration", "instant"):
        add("INSTANT", "REJECT", "time_type required (duration|instant) with a period")
    if u_id in SENTINEL_SCOPE:
        if scope != SENTINEL_SCOPE[u_id]:
            add("SCOPE_PAIR", "REJECT",
                f"sentinel {u_id} must pair with scope {SENTINEL_SCOPE[u_id]!r}")
        if start is not None or end is not None:
            add("SCOPE_PAIR", "REJECT", f"sentinel {u_id} stores null dates")
        return
    if scope in SENTINEL_SCOPE.values():
        add("SCOPE_PAIR", "REJECT", f"dated period {u_id} with sentinel scope {scope!r}")
    for d in (start, end):
        if d is not None:
            try:
                date.fromisoformat(d)
            except (ValueError, TypeError):
                add("ISO", "REJECT", f"bad ISO date {d!r}")
                return
    # a dated period's stored dates ARE the gp_ id's dates — no divergence, ever
    if (start, end) != (u_id[3:13], u_id[14:]):
        add("PERIOD_SYM", "REJECT",
            f"gp dates {start}..{end} do not match the period id {u_id}")
        return
    if fact.get("time_type") == "instant":
        if start != end:
            add("INSTANT", "REJECT", "instant must be a one-day window (gp_X_X)")
    elif fact.get("time_type") == "duration" and start == end:
        add("INSTANT", "REJECT", "duration with start == end is illegal input")


def _id_rebuild(fact, add):
    """FACT-16 group 1: a supplied id/fact_scope must equal the rebuild from components."""
    if fact.get("id") is None and fact.get("fact_scope") is None:
        return
    parts = (fact.get("id") or "").split(":", 3)
    if len(parts) != 4 or parts[0] != "du":
        add("ID", "REJECT", f"malformed fact id: {fact.get('id')!r}")
        return
    try:
        rebuilt_id, rebuilt_scope = build_id(
            parts[1], fact.get("driver_name"),
            period_id=fact.get("period_u_id"),
            slice_parts=fact.get("slice_parts") or (),
            measurement_tokens=fact.get("measurement_tokens") or (),
            surprise=fact.get("surprise"))
    except (IdLawError, TypeError, ValueError) as e:
        add("ID", "REJECT", f"id rebuild failed: {e}")
        return
    if fact.get("id") is not None and fact["id"] != rebuilt_id:
        add("ID", "REJECT", f"id {fact['id']!r} != rebuild {rebuilt_id!r}")
    if fact.get("fact_scope") is not None and fact["fact_scope"] != rebuilt_scope:
        add("ID", "REJECT",
            f"fact_scope {fact['fact_scope']!r} != rebuild {rebuilt_scope!r}")


def _period_lane(fact, lane, add):
    """§7.2 period column: guidance REQUIRED · g_v_c surprise REQUIRED · everyone else
    'when real' — sentinel horizons are guidance-lane only (action sentinels hard-fail)."""
    u_id = fact.get("period_u_id")
    if lane == "guidance" and u_id is None:
        add("PERIOD_LANE", "REJECT",
            "guidance requires its target period (real window or explicit sentinel)")
    if lane == "surprise" and fact.get("surprise") == "guidance_vs_consensus" \
            and u_id is None:
        add("PERIOD_LANE", "REJECT",
            "guidance_vs_consensus requires the guidance TARGET period")
    if lane != "guidance" and u_id in SENTINEL_SCOPE:
        add("PERIOD_LANE", "REJECT",
            f"{lane} facts use real periods only — sentinel horizon {u_id} is illegal "
            f"(action sentinels hard-fail; metric/surprise periods must be real)")


def _lane_matrix(fact, lane, v, add):
    confirmed = fact.get("company_confirmed")
    if lane == "guidance":
        if confirmed is False:
            add("LANE", "REJECT",
                "company_confirmed=false is the RESERVED third-party class — no such "
                "class is enabled today (enabling one is an owner decision)")
        elif confirmed is not True:
            add("LANE", "REJECT", "company_confirmed (core-derived, exactly boolean "
                                  "True) is REQUIRED on every stored guidance fact")
    elif confirmed is not None:
        add("LANE", "REJECT", "company_confirmed is guidance-only")
    if fact.get("xbrl_qname") is not None:
        add("LANE", "REJECT", "xbrl_qname is written by the concept-link enrichment "
                              "(metric lane only) — producers never supply it")

    vt = fact.get("value_text")
    if vt is not None:
        numbers = any(fact.get(k) is not None for k in
                      ("level_low", "level_high", "change_value",
                       "comparison_low", "comparison_high"))
        if lane != "guidance":
            add("VALUE_TEXT", "REJECT", "value_text is guidance-only")
        elif numbers:
            add("VALUE_TEXT", "REJECT", "value_text is numberless-only")
        elif len(vt) > 200:
            add("VALUE_TEXT", "REJECT", "value_text over 200 chars")
        elif _VALUE_TEXT_NUMERIC.search(vt):
            add("VALUE_TEXT", "REJECT",
                f"value_text carries a numeric value: {vt!r} (year anchors are legal)")

    cond = fact.get("conditions")
    if cond is not None:
        if lane != "guidance":
            add("CONDITIONS", "REJECT", "conditions is guidance-only")
        elif " ".join(cond.casefold().split()) not in " ".join(
                (fact.get("quote") or "").casefold().split()):
            add("CONDITIONS", "REJECT", "the conditions clause must remain in the quote")


def _movement(fact, lane, add):
    if lane != "guidance" or fact.get("driver_state") not in ("raised", "lowered",
                                                              "reaffirmed"):
        return
    lo, hi = fact.get("level_low"), fact.get("level_high")
    clo, chi = fact.get("comparison_low"), fact.get("comparison_high")
    if None in (lo, hi, clo, chi):
        return                     # open/missing shapes: the validator skips
    mid, cmid = (lo + hi) / 2, (clo + chi) / 2
    state = fact["driver_state"]
    ok = (mid > cmid) if state == "raised" else \
         (mid < cmid) if state == "lowered" else (mid == cmid)
    if not ok:
        add("MOVEMENT", "REJECT",
            f"stated {state} contradicts the midpoint rule ({mid} vs prior {cmid})")


def _od21(fact, add, home_facts):
    basis, baseline = fact.get("surprise_basis_hint"), fact.get("comparison_baseline")
    slot = fact.get("surprise")
    if basis not in ("actual", "guidance"):
        add("F3", "REJECT", "surprise_basis_hint (actual|guidance) required on every "
                            "surprise item")
    if baseline is None:
        add("F4", "REJECT", "comparison_baseline required on every surprise fact")
    if slot is None:
        add("F1", "REJECT", "surprise= scope slot required on every surprise fact")
    elif basis in ("actual", "guidance") and baseline is not None:
        try:
            expected = compose_surprise_scope(basis, baseline)
            if slot != expected:
                add("F1", "REJECT", f"surprise={slot} != composed {expected}")
        except ValueError as e:
            add("F5", "REJECT", str(e))

    # tense: an actual surprise before its period ends is rejected
    end, event_time = fact.get("gp_end_date"), fact.get("event_time")
    if (slot or "").startswith("actual_vs") and end and event_time and \
            end > event_time[:10]:
        add("F7", "REJECT", f"actual surprise before period end ({end} > event day)")

    # derivable delta must not be stored
    if fact.get("change_value") is not None and \
            fact.get("level_low") is not None and fact.get("level_low") == fact.get("level_high") and \
            fact.get("comparison_low") is not None and \
            fact.get("comparison_low") == fact.get("comparison_high"):
        add("DERIVABLE", "REJECT",
            "surprise delta derivable from its operands must stay null (derive at read)")

    if home_facts is None:
        # home checks are MANDATORY — an absent context is never a silent bypass
        add("F6", "PARK", "surprise home context not provided — the home-fact check "
                          "cannot be skipped")
        return
    home_lane_name = _expected_home_name(fact)
    candidates = list(home_facts)
    if not candidates:
        if (fact.get("driver_name") or "").endswith("_surprise"):
            # a NAMED surprise (numberless included) is grounded — its home should exist
            add("F6", "PARK", "named surprise with no same-event home fact — park and "
                              "re-extract the whole event, never an orphan-only replay")
        else:
            add("F8", "PARK", "ungrounded surprise ('results beat') parks until a home "
                              "fact exists")
        return
    reasons = []
    for home in candidates:
        reason = _home_mismatch(fact, home, home_lane_name)
        if reason is None:
            return                 # matched home found
        reasons.append(reason)
    add("F9", "PARK", f"no matching home fact: {reasons[0]}")


def _expected_home_name(fact):
    """Family via terminal-suffix strip — the deterministic FIRST rung of the PIPE-25
    BASE_METRIC lookup. PRODUCTION-BLOCKED beyond the pilot until the S4 kernel supplies
    real BASE_METRIC/SAME_AS edges (a variant-named home would over-park here — the
    safe direction, but a recall cost the kernel removes)."""
    name = fact.get("driver_name") or ""
    base = name[:-len("_surprise")] if name.endswith("_surprise") else name
    return base + "_guidance" if fact.get("surprise_basis_hint") == "guidance" else base


def _home_mismatch(s, h, expected_name):
    if h.get("driver_name") != expected_name:
        return f"family mismatch (home {h.get('driver_name')!r} != {expected_name!r})"
    if h.get("period_u_id") != s.get("period_u_id"):
        return "period mismatch"
    if h.get("period_scope") != s.get("period_scope"):
        return "period_scope mismatch"
    if _norm_parts(h.get("slice_parts")) != _norm_parts(s.get("slice_parts")):
        return "slice mismatch"
    if set(h.get("measurement_tokens") or ()) != set(s.get("measurement_tokens") or ()):
        return "measurement mismatch"
    s_numberless = s.get("level_low") is None and s.get("level_high") is None
    h_numberless = h.get("level_low") is None and h.get("level_high") is None
    if s_numberless != h_numberless:
        return "value mismatch (numberless surprise needs a numberless home)"
    if not s_numberless:
        if any(_num(h.get(k)) != _num(s.get(k)) for k in ("level_low", "level_high")):
            return "value mismatch"
        if h.get("level_unit") != s.get("level_unit"):
            return "unit mismatch"
    return None


def _norm_parts(parts):
    return frozenset(tuple(p) for p in (parts or ()))


def _num(x):
    if x is None:
        return None
    try:
        return num_canon(x)
    except IdLawError:
        return "«non-exact»"   # an unlawful number can never MATCH anything — park-safe
