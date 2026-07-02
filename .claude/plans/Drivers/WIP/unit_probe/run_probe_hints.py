"""
run_probe_hints.py — HINTS-ON scored run through the REAL shared unit_resolver.py.

This is the PRODUCTION-PATH probe: it assumes the producer supplies the coarse
unit KIND (money/ratio/count/multiplier) — the easy LLM classification — and asks
whether the deterministic resolver then lands the fine 9-enum unit AND the scaled
value. Imports unit_resolver (the deliverable), NOT the throwaway unit_extract.

Asserts THREE things per case (not just the unit string):
  • canonical_unit == expected_canonical_unit
  • scaled_value == expected_scaled_value (when given) OR passes the derived rule
    (ratio/x: value unchanged; usd/m_usd/count: must be non-None for a single value)
  • a naming-lint warning is present when the case is tagged expect_warning

Honest note: the kind hint is derived from each case's expected class (money cases
also get money_mode), so money is near-determined by construction. The genuinely
testing residual is ratio-subtype, count-nouns, the value scaling, and the lint.

Run:  /usr/bin/python3 run_probe_hints.py
"""
import json
import os

from unit_resolver import resolve_unit, real_source

HERE = os.path.dirname(os.path.abspath(__file__))
cases = json.load(open(os.path.join(HERE, "cases.json")))

RATIO_UNITS = {"percent", "percent_yoy", "percent_points", "basis_points"}
PASSTHRU_UNITS = RATIO_UNITS | {"x"}              # value must be unchanged
NONNULL_UNITS = {"usd", "m_usd", "count"}          # value must be non-None


def hint_from_expected(exp):
    if exp == "count":
        return ("count", None)
    if exp == "usd":
        return ("money", "price_like")
    if exp == "m_usd":
        return ("money", "aggregate")
    if exp in RATIO_UNITS:
        return ("ratio", None)
    if exp == "x":
        return ("multiplier", None)
    return (None, None)  # unknown -> producer honestly cannot classify


def get(c, *keys):
    for k in keys:
        if k in c and c[k] not in (None, ""):
            return c[k]
    return ""


def value_ok(c, exp, r):
    """Returns (ok, detail). Skips when no single value or expected unit is unknown."""
    val = c.get("value")
    if val in (None, "") or exp == "unknown":
        return True, ""
    try:
        fval = float(val)
    except (TypeError, ValueError):
        return True, ""  # range string — value-scaling intentionally not asserted
    if "expected_scaled_value" in c:
        want = c["expected_scaled_value"]
        ok = r.scaled_value is not None and abs(r.scaled_value - want) < 1e-6
        return ok, f"value got={r.scaled_value} want={want}"
    if exp in PASSTHRU_UNITS:
        ok = r.scaled_value is not None and abs(r.scaled_value - fval) < 1e-6
        return ok, f"passthru got={r.scaled_value} want={fval}"
    if exp in NONNULL_UNITS:
        return (r.scaled_value is not None), f"expected non-None scaled, got {r.scaled_value}"
    return True, ""


by_ft = {}
unit_fail, value_fail, warn_fail = [], [], []
n = unit_ok = 0
for c in cases:
    exp = get(c, "expected_canonical_unit", "expected")
    if not exp:
        continue
    ft = get(c, "fact_type") or "unknown"
    name = get(c, "driver_name")
    uraw = c.get("unit_raw", "")
    val = c.get("value") or None
    quote = c.get("quote") or None
    kind, mode = hint_from_expected(exp)
    r = resolve_unit(name, uraw, val, unit_kind_hint=kind, money_mode_hint=mode, quote=quote)

    n += 1
    u_ok = (r.canonical_unit == exp)
    unit_ok += u_ok
    d = by_ft.setdefault(ft, [0, 0])
    d[1] += 1
    d[0] += u_ok
    if not u_ok:
        unit_fail.append((ft, name, uraw, exp, r.canonical_unit, r.error))

    v_ok, vdetail = value_ok(c, exp, r)
    if not v_ok:
        value_fail.append((ft, name, uraw, vdetail))

    if c.get("expect_warning"):
        has = any("per-unit price" in w for w in r.warnings)
        if not has:
            warn_fail.append((ft, name, uraw, r.warnings))


print("=== PROVENANCE ===")
src = real_source()
print(f"  imports: {src['guidance_ids_file']}")
print(f"  sha256:  {src['guidance_ids_sha256']}")
print(f"  reimplemented: {src['reimplemented']}")
print()
print("=== HINTS-ON (correct kind supplied) — REAL unit_resolver ===")
print(f"  unit match: {unit_ok}/{n} = {unit_ok/n*100:.1f}%")
for ft, (m, t) in sorted(by_ft.items()):
    print(f"    {ft:14s} {m}/{t} = {m/t*100:.0f}%")
print(f"  value failures:   {len(value_fail)}")
print(f"  warning failures: {len(warn_fail)}")
print()
if unit_fail:
    print(f"--- UNIT MISMATCHES ({len(unit_fail)}) ---")
    for ft, name, uraw, exp, act, err in unit_fail:
        print(f"  [{ft}] {name} unit_raw={uraw!r} exp={exp} got={act}" + (f" ERR={err}" if err else ""))
if value_fail:
    print(f"--- VALUE MISMATCHES ({len(value_fail)}) ---")
    for ft, name, uraw, det in value_fail:
        print(f"  [{ft}] {name} unit_raw={uraw!r} {det}")
if warn_fail:
    print(f"--- MISSING-WARNING ({len(warn_fail)}) ---")
    for ft, name, uraw, w in warn_fail:
        print(f"  [{ft}] {name} unit_raw={uraw!r} warnings={w}")
if not (unit_fail or value_fail or warn_fail):
    print("ALL GREEN — unit, value, and lint all correct.")
print()
print("JSON_BEGIN")
print(json.dumps({"total": n, "unit_matched": unit_ok,
                  "value_failures": len(value_fail), "warning_failures": len(warn_fail),
                  "by_fact_type": {k: {"matched": v[0], "total": v[1]} for k, v in by_ft.items()}}))
print("JSON_END")
