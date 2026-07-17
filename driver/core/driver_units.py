"""Driver-law unit wrapper (FINAL_DESIGN §6.1: UNIT-01..14 effective form, OD-11).

All canonicalization mechanics live in the relocated PROVEN shared resolver
(unit_resolver.py, 117/117 + 29+7 evidence — untouched). This wrapper adds only
what current law layers on top:
  - per-slot hints: level and change each carry their OWN kind/money-mode hints
  - the per-X lint is a HARD failure on money levels (probe-era behavior: warn)
  - resolver errors (cents-on-aggregate, pre-scaled) raise -> caller PARKS
  - OD-11 growth basis: CONSUMES the upstream-resolved period_scope, never infers;
    annual pin; sequential only on in-document evidence; sentinel/missing scope
    fails closed to unknown; points/bps always win (they resolve upstream)
  - the 10-unit enum (adds percent_sequential to the substrate's 9)
"""
import math
from decimal import Decimal, InvalidOperation, localcontext

from driver.core.unit_resolver import CANONICAL_UNITS, resolve_unit

__all__ = ["DRIVER_UNITS", "UnitResolutionError", "resolve_driver_units"]

DRIVER_UNITS = frozenset(CANONICAL_UNITS | {"percent_sequential"})
_SENTINEL_SCOPES = frozenset({"short_term", "medium_term", "long_term", "undefined"})


class UnitResolutionError(ValueError):
    """A unit could not be resolved safely. Callers PARK — never guess."""


def resolve_driver_units(driver_name, *,
                         level_values=(), level_unit_raw=None,
                         level_unit_kind_hint=None, level_money_mode_hint=None,
                         comparison_values=(),
                         change_value=None, change_unit_raw=None,
                         change_unit_kind_hint=None, change_money_mode_hint=None,
                         period_scope=None, sequential_evidence=False,
                         percent_level_metric=None,
                         quote=None, xbrl_qname=None):
    """Resolve one fact's level_* and change_* units + scale its numbers.

    level_values = [low, high] (either may be None); comparison values share the
    level resolution (there is no comparison_unit by law). Returns
    {level_unit, level_values, comparison_values, change_unit, change_value, warnings}.
    """
    warnings = []
    out = {"level_unit": None, "level_values": list(level_values),
           "comparison_values": list(comparison_values),
           "change_unit": None, "change_value": change_value, "warnings": warnings}

    if level_unit_raw is not None or any(v is not None for v in level_values):
        res = _slot(driver_name, level_unit_raw, level_values,
                    level_unit_kind_hint, level_money_mode_hint, quote, xbrl_qname,
                    warnings, hard_lint=True)
        out["level_unit"] = _growth_basis(res.canonical_unit, period_scope,
                                          sequential_evidence)
        out["level_values"] = res.scaled
        out["comparison_values"] = _slot(
            driver_name, level_unit_raw, comparison_values,
            level_unit_kind_hint, level_money_mode_hint, quote, xbrl_qname,
            warnings, hard_lint=False).scaled

    if change_unit_raw is not None or change_value is not None:
        res = _slot(driver_name, change_unit_raw, [change_value],
                    change_unit_kind_hint, change_money_mode_hint, quote, xbrl_qname,
                    warnings, hard_lint=False)
        out["change_value"] = res.scaled[0] if res.scaled else None
        unit = res.canonical_unit
        if unit == "percent":
            is_pct_level = (percent_level_metric if percent_level_metric is not None
                            else (out["level_unit"] == "percent" if out["level_unit"] else None))
            if is_pct_level is False:
                unit = "percent_yoy"     # a plain-% change on a non-%-level metric is growth
            else:                        # %-level metric, or levelness unknown -> fail closed
                warnings.append(
                    "static-percent gate: plain % change is relative-vs-points ambiguous "
                    f"(percent_level_metric={is_pct_level}) -> unknown")
                unit = "unknown"
        out["change_unit"] = _growth_basis(unit, period_scope, sequential_evidence)

    return out


class _SlotResult:
    def __init__(self, canonical_unit, scaled):
        self.canonical_unit = canonical_unit
        self.scaled = scaled


def _slot(name, raw, values, kind_hint, money_hint, quote, xbrl_qname, warnings, *, hard_lint):
    """Resolve one slot via the proven resolver, then scale in EXACT Decimal math
    (owner exactness law 2026-07-17: no automatic 6-decimal rounding). The resolver
    stays authoritative for the UNIT, the guards, and the scale FACTOR (probed with
    value=1 — its scaling is linear-then-round); the VALUE itself is computed as
    Decimal(source) x factor, cross-checked against the resolver's own rounded output."""
    scaled, unit, factor = [], None, None
    for value in (list(values) or [None]):
        if isinstance(value, float):
            raise UnitResolutionError(
                f"source values must be exact (int/Decimal/str), got float {value!r}")
        try:
            exact_in = None if value is None else Decimal(str(value))
        except InvalidOperation:
            raise UnitResolutionError(f"not a number: {value!r}")
        try:
            probe_val = None if exact_in is None else float(exact_in)
        except OverflowError:
            probe_val = math.inf
        if probe_val is not None and not math.isfinite(probe_val):
            raise UnitResolutionError(
                f"{value!r} exceeds float range for the resolver's guards — park")
        r = resolve_unit(name, raw, probe_val,
                         unit_kind_hint=kind_hint,
                         money_mode_hint=money_hint, quote=quote, xbrl_qname=xbrl_qname)
        if r.error:
            raise UnitResolutionError(r.error)
        lint = [w for w in r.warnings if "per-unit price" in w]
        if lint and hard_lint and r.kind == "money":
            raise UnitResolutionError(lint[0])       # per-X needs '_per_X' in the NAME
        warnings.extend(w for w in r.warnings if w not in warnings)
        unit = r.canonical_unit
        if exact_in is not None:
            if r.scaled_value is None:
                scaled.append(None)
            else:
                if factor is None:
                    probe = resolve_unit(name, raw, 1.0, unit_kind_hint=kind_hint,
                                         money_mode_hint=money_hint, quote=quote,
                                         xbrl_qname=xbrl_qname).scaled_value
                    factor = Decimal(repr(probe)) if probe is not None else Decimal(1)
                with localcontext() as ctx:
                    # a x b needs exactly digits(a)+digits(b) precision — NEVER trust
                    # the ambient thread-global context (any library may lower it;
                    # even the default 28 silently rounds — review round 8)
                    ctx.prec = (len(exact_in.as_tuple().digits)
                                + len(factor.as_tuple().digits) + 2)
                    exact = exact_in * factor
                try:
                    approx = float(exact)
                except OverflowError:
                    approx = math.inf
                if not math.isfinite(approx):
                    raise UnitResolutionError(
                        f"scaled {value!r} {raw!r} exceeds float range — park")
                if round(approx, 6) != round(r.scaled_value, 6):
                    raise UnitResolutionError(
                        f"exact scaling diverged from the proven resolver for "
                        f"{value!r} {raw!r} ({exact} vs {r.scaled_value}) — park")
                scaled.append(exact)
        elif values:                                  # keep positional None (e.g. open range)
            scaled.append(None)
    return _SlotResult(unit, scaled if list(values) else [])


def _growth_basis(unit, period_scope, sequential_evidence):
    """OD-11: refine a growth-flavored percent unit by the fact's resolved period scope."""
    if unit != "percent_yoy":
        return unit                                   # points/bps/money/etc. already final
    if period_scope is None or period_scope in _SENTINEL_SCOPES:
        return "unknown"                              # sentinel/missing horizon fails closed
    if period_scope == "annual":
        return "percent_yoy"                          # annual pin: sequential == yoy
    return "percent_sequential" if sequential_evidence else "percent_yoy"
