"""
apply_case_fixes.py — one-shot, transparent transform of cases.json to the LOCKED
per-X naming rules (2026-06-20). Prints EVERY change. Idempotent.

What it does (and ONLY this):
  1. Stale per-X flips: a USD per-X whose expected was the old '$/X -> unknown'
     becomes the new rule — denominator in the NAME, unit 'usd'. Names that
     lacked the denominator are renamed to carry it (..._per_barrel/_per_ton).
  2. system_units 'x': the 'x' was a bad producer token for a COUNT — clean it to
     '' (the hard 'x' multiplier surface otherwise beats even a count hint).
  3. expected_scaled_value: ground-truth scaled value on the money cases where
     scaling actually does work (the $B/$M ×1000 traps + the per-X usd cases),
     so the probe can assert VALUE, not just the unit string.
  4. Appends 2 naming-lint trigger cases (USD per-X, name lacks _per_) tagged
     expect_warning=true — proves the lint fires when the rule is BROKEN.

Run:  /usr/bin/python3 apply_case_fixes.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "cases.json")

# (driver_name, unit_raw, value) -> {new_name?, expected?, scaled?, unit_raw?}
FIXES = {
    # ── stale per-X flips: unknown -> usd, denominator into the NAME ──
    ("commodity_cost", "$/barrel", "80"):
        dict(new_name="commodity_cost_per_barrel", expected="usd", scaled=80.0),
    ("steel_cost", "$/ton", "700"):
        dict(new_name="steel_cost_per_ton", expected="usd", scaled=700.0),
    ("oil_price_realization_guidance", "$/barrel", "75"):
        dict(new_name="oil_price_realization_per_barrel_guidance", expected="usd", scaled=75.0),
    ("oil_price", "$/barrel", "80"):
        dict(new_name="oil_price_per_barrel", expected="usd", scaled=80.0),
    ("oil_price", "$ per barrel", "80"):
        dict(new_name="oil_price_per_barrel", expected="usd", scaled=80.0),
    ("fuel_cost_per_barrel", "$/barrel", "85"):
        dict(expected="usd", scaled=85.0),  # name already carries the denominator
    # ── system_units: 'x' was a bad token for a count ──
    ("system_units", "x", "1820"):
        dict(new_unit_raw="", scaled=1820.0),
    # ── value annotations: glued-$B/$M ×1000 traps + per-share (no rename) ──
    ("revenue_surprise", "$M", "50"): dict(scaled=50.0),
    ("revenue_surprise", "$B", "1.2"): dict(scaled=1200.0),
    ("revenue_miss", "$M", "-30"): dict(scaled=-30.0),
    ("ebitda_surprise", "$M", "75"): dict(scaled=75.0),
    ("share_repurchase", "$B", "2"): dict(scaled=2000.0),
    ("asset_impairment", "$B", "1.2"): dict(scaled=1200.0),
    ("goodwill_impairment", "$M", "340"): dict(scaled=340.0),
    ("debt_issuance", "$M", "500"): dict(scaled=500.0),
    ("senior_notes_offering", "$B", "1"): dict(scaled=1000.0),
    ("capex", "$B", "1.2"): dict(scaled=1200.0),
    ("buyback", "$B", "10"): dict(scaled=10000.0),
    ("share_repurchase_authorization", "$B", "10"): dict(scaled=10000.0),
    ("eps_surprise", "$", "0.05"): dict(scaled=0.05),
    ("dividend_per_share", "$", "0.50"): dict(scaled=0.50),  # 2 rows (action_event + guidance)
    ("adjusted_eps_diluted", "$", "3.2"): dict(scaled=3.2),
}

NEW_LINT_CASES = [
    {"fact_type": "metric", "driver_name": "crude_realization", "unit_raw": "$/barrel",
     "value": "80", "quote": "crude realization of $80/barrel",
     "expected_canonical_unit": "m_usd", "expect_warning": True,
     "trap_flag": "naming-lint", "category": "lint"},
    {"fact_type": "metric", "driver_name": "coal_cost", "unit_raw": "$ per ton",
     "value": "120", "quote": "coal cost of $120 per ton",
     "expected_canonical_unit": "usd", "expect_warning": True,
     "trap_flag": "naming-lint", "category": "lint"},
]


def main():
    cases = json.load(open(PATH))
    applied = set()
    changes = []
    for c in cases:
        key = (c.get("driver_name"), c.get("unit_raw"), str(c.get("value")))
        fx = FIXES.get(key)
        if not fx:
            continue
        applied.add(key)
        before = dict(c)
        if "new_name" in fx:
            c["driver_name"] = fx["new_name"]
        if "new_unit_raw" in fx:
            c["unit_raw"] = fx["new_unit_raw"]
        if "expected" in fx:
            c["expected_canonical_unit"] = fx["expected"]
        if "scaled" in fx:
            c["expected_scaled_value"] = fx["scaled"]
        diff = {k: (before.get(k), c.get(k)) for k in
                ("driver_name", "unit_raw", "expected_canonical_unit", "expected_scaled_value")
                if before.get(k) != c.get(k)}
        if diff:
            changes.append((key, diff))

    # report unmatched fixes (typo guard — every FIX must hit something)
    unmatched = [k for k in FIXES if k not in applied]

    # append lint-trigger cases (idempotent: skip if already present)
    existing = {(c.get("driver_name"), c.get("unit_raw")) for c in cases}
    added = []
    for nc in NEW_LINT_CASES:
        if (nc["driver_name"], nc["unit_raw"]) not in existing:
            cases.append(nc)
            added.append((nc["driver_name"], nc["unit_raw"]))

    json.dump(cases, open(PATH, "w"), indent=1)
    open(PATH, "a").write("\n")  # trailing newline

    print(f"=== applied {len(changes)} field-changes across {len(applied)} rows ===")
    for key, diff in changes:
        print(f"  {key[0]!r}/{key[1]!r}:")
        for f, (b, a) in diff.items():
            print(f"       {f}: {b!r} -> {a!r}")
    print(f"\n=== appended {len(added)} lint-trigger rows: {added} ===")
    if unmatched:
        print(f"\n!!! UNMATCHED FIXES (check for typos): {unmatched}")
    else:
        print("\nall FIXES matched a row.")
    print(f"\ntotal cases now: {len(cases)}")


if __name__ == "__main__":
    main()
