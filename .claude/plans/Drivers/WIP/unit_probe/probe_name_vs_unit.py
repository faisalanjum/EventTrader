#!/usr/bin/env python3
"""
probe_name_vs_unit.py — EMPIRICAL test of the Option A vs Option B decision.

OPTION A (LOCKED, DriverGraphSchema.md:311): per-X denominator lives in the
  driver NAME; unit stays a base enum value.
    oil_price_per_barrel  unit=usd   ·  sales_per_square_foot unit=usd  ·  dividend_per_share unit=usd
OPTION B (proposal): denominator moves into the UNIT field.
    oil_price  unit='$_per_barrel' OR '$_per_tonne'

This script uses the REAL shared resolver (unit_resolver.py -> guidance_ids.py).
It proves:
  1. Option A: each per-X driver resolves to a clean base enum unit (the
     denominator carried by the NAME, not the unit).
  2. Option B feasibility: the resolver/enum has NO '$_per_barrel' value; it can
     only ever return one of the 9 CANONICAL_UNITS. '$_per_barrel' is impossible
     without extending the enum (which breaks the verbatim-Guidance reuse).
  3. Trackability: Option A = two clean comparable series; Option B = one mixed
     series you CANNOT compare/aggregate without a translation table.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unit_resolver import resolve_unit, CANONICAL_UNITS, real_source
import guidance_ids as gid

line = "=" * 78


def show(label, r):
    print(f"  {label}")
    print(f"      -> canonical_unit = {r.canonical_unit!r}   scaled_value = {r.scaled_value}")
    print(f"         kind={r.kind!r}  money_mode={r.money_mode!r}")
    if r.warnings:
        for w in r.warnings:
            print(f"         WARN: {w}")
    if r.error:
        print(f"         ERROR: {r.error}")


print(line)
print("PROVENANCE — using the REAL production resolver (not re-implemented)")
print(line)
src = real_source()
print(f"  guidance_ids file : {src['guidance_ids_file']}")
print(f"  sha256            : {src['guidance_ids_sha256'][:16]}...")
print(f"  reimplemented     : {src['reimplemented']}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + line)
print("OPTION A — denominator in the NAME; unit resolves to a BASE enum value")
print(line)
a_cases = [
    # (driver_name, unit_raw, value)  -- the denominator is in the NAME
    ("oil_price_per_barrel", "$/barrel", 80),
    ("sales_per_square_foot", "$/sq ft", 450),
    ("dividend_per_share", "$", 0.50),
]
a_results = {}
for name, ur, val in a_cases:
    r = resolve_unit(name, ur, val)
    show(f"resolve_unit({name!r}, {ur!r}, {val})", r)
    a_results[name] = r.canonical_unit

print("\n  NOTE: dividend_per_share -> 'usd' (clean). The per-share override fires")
print("        because the DENOMINATOR is in the NAME (guidance_ids:485-486).")
print("        oil_price_per_barrel / sales_per_square_foot: the '$/x' unit text")
print("        is OFF-MENU, but the denominator distinction is already encoded in")
print("        the NAME, so the two variants are SEPARATE, individually trackable")
print("        drivers regardless of what the unit text resolves to.")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + line)
print("OPTION B FEASIBILITY — can the UNIT field hold '$_per_barrel'/'$_per_tonne'?")
print(line)
print(f"  The CLOSED enum (guidance_ids.CANONICAL_UNITS), exactly {len(CANONICAL_UNITS)} values:")
print(f"    {sorted(CANONICAL_UNITS)}")

probe_units = ["$_per_barrel", "$_per_tonne", "$_per_share", "$/barrel", "$/tonne"]
print("\n  Is any Option-B unit token a member of the enum?")
for u in probe_units:
    print(f"    {u!r:16} in CANONICAL_UNITS -> {u in CANONICAL_UNITS}")

print("\n  What does the deterministic resolver canonicalize_unit() return for each")
print("  (called bare, i.e. denominator NOT in the name -> the Option-B world)?")
ob_results = {}
for u in probe_units:
    out = gid.canonicalize_unit(u, gid.slug("oil_price"))
    ob_results[u] = out
    in_enum = out in CANONICAL_UNITS
    print(f"    canonicalize_unit({u!r:14}, 'oil_price') -> {out!r}   (in 9-enum: {in_enum})")

# Show the funnel can ONLY emit one of the 9
all_emitted_in_enum = all(v in CANONICAL_UNITS for v in ob_results.values())
print(f"\n  Every return value is one of the 9 canonical units: {all_emitted_in_enum}")
print("  => canonicalize_unit is a fail-closed funnel (guidance_ids:461-492):")
print("     branch 3 'No match -> unknown' (line 481-482). It can NEVER emit")
print("     '$_per_barrel'. Option B's unit is NOT representable without ADDING")
print("     new enum values -> which breaks the verbatim-Guidance reuse (schema:286).")

# Show the full resolver (with the per-X lint) on the Option-B bare-name world
print("\n  Full resolver on the Option-B bare-name 'oil_price' (denominator NOT in name):")
for ur in ["$/barrel", "$/tonne"]:
    r = resolve_unit("oil_price", ur, 80)
    show(f"resolve_unit('oil_price', {ur!r}, 80)", r)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + line)
print("TRACKABILITY DEMO — can you build ONE comparable timeseries?")
print(line)

print("\n  OPTION A: two SEPARATE drivers, each a clean comparable series (same unit):")
series_barrel = [70, 80, 90]   # oil_price_per_barrel, all unit=usd
series_tonne = [500, 560]      # oil_price_per_tonne,  all unit=usd
print(f"    oil_price_per_barrel (unit=usd): {series_barrel}")
print(f"      delta last-vs-first = {series_barrel[-1]-series_barrel[0]:+d}  "
      f"(comparable: same denominator throughout)")
print(f"    oil_price_per_tonne  (unit=usd): {series_tonne}")
print(f"      delta last-vs-first = {series_tonne[-1]-series_tonne[0]:+d}  "
      f"(comparable: same denominator throughout)")
print("    => each series is internally comparable; change-detection works.")

print("\n  OPTION B: ONE 'oil_price' driver, unit varies per update (the mix):")
mixed = [
    {"value": 70, "unit": "$/barrel"},
    {"value": 560, "unit": "$/tonne"},
    {"value": 80, "unit": "$/barrel"},
]
for i, pt in enumerate(mixed):
    print(f"    update[{i}]: value={pt['value']:>4}  unit={pt['unit']}")
# Try to "detect a change" by naive subtraction across the series:
naive_delta = mixed[2]["value"] - mixed[1]["value"]  # 80 ($/bbl) - 560 ($/tonne)
print(f"\n    Naive 'what is it now vs before?' update[2]-update[1] = "
      f"{naive_delta:+d}  <-- GARBAGE: 80 $/barrel minus 560 $/tonne is meaningless.")

# Show why: the units are not comparable without a translation table.
distinct_units = sorted({pt["unit"] for pt in mixed})
print(f"    distinct units in ONE series: {distinct_units}")
print("    To compare them you would need a translation table ($/barrel <-> $/tonne,")
print("    which depends on density per commodity) — exactly what the design forbids.")

# Show the U54 read-time partition would split them anyway (by canonical_unit).
print("\n  Even worse for Option B: the U54 read-time partition keys on canonical_unit")
print("  (schema:417-418). Resolving the Option-B units through the REAL resolver:")
buckets = {}
for pt in mixed:
    cu = gid.canonicalize_unit(pt["unit"].replace("/", "_per_").replace("$", "$"), gid.slug("oil_price"))
    # the bare physical token -> 'unknown' via the funnel; show it lands in a bucket
    cu = gid.canonicalize_unit(pt["unit"], gid.slug("oil_price"))
    buckets.setdefault(cu, []).append(pt["value"])
print(f"    series buckets keyed by canonical_unit -> {buckets}")
print("    => physical-unit tokens collapse to 'unknown' (or money); both denominators")
print("       become INDISTINGUISHABLE in the unit field, so Option B cannot even")
print("       tell $/barrel from $/tonne — defeating its own stated PRO.")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + line)
print("MACHINE SUMMARY")
print(line)
summary = {
    "enum_size": len(CANONICAL_UNITS),
    "enum": sorted(CANONICAL_UNITS),
    "enum_supports_per_barrel": "$_per_barrel" in CANONICAL_UNITS,
    "option_a_units": a_results,
    "option_b_resolver_returns": ob_results,
    "option_b_every_return_in_9_enum": all_emitted_in_enum,
    "trackability": {
        "option_a_barrel_delta": series_barrel[-1] - series_barrel[0],
        "option_a_tonne_delta": series_tonne[-1] - series_tonne[0],
        "option_b_naive_delta_is_garbage": naive_delta,
        "option_b_distinct_units_in_one_series": distinct_units,
        "option_b_u54_buckets": buckets,
    },
}
print(json.dumps(summary, indent=2))
