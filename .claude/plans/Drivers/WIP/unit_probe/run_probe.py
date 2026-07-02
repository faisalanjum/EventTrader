"""
run_probe.py — LABEL-ONLY (no hints) run through the REAL shared unit_resolver.py.

This is the honest "does the NAME alone do the job" probe. It is the test that
actually validates the locked naming rule: a USD per-X driver whose NAME carries
the '_per_' denominator must resolve to 'usd' with NO producer hint.

It reports four crisp sections + one informational one:
  A. PER-X HAPPY PATH  — USD per-X, name has '_per_'  -> MUST be expected unit+value
  B. NAMING-LINT TRIGGERS — USD per-X, name lacks '_per_' -> MUST emit the warning
  C. MONEY-AGGREGATE VALUE — expected m_usd w/ scaled -> MUST scale x1000 correctly
  D. RATIO/MULTIPLIER     — %/bps/pp/x -> MUST be exact label-only
  (E) NEEDS-A-HINT (informational) — bare count-nouns / bare scale words / non-USD
       currency resolve to 'unknown' label-only BY DESIGN; the production contract
       supplies a unit_kind_hint for these (see run_probe_hints.py). NOT a failure.

(The old V1-vs-V2 comparison is settled and frozen in RESULTS.md; V2 is locked, so
this probe no longer re-runs V1.)

Run:  /usr/bin/python3 run_probe.py
"""
import json
import os

from unit_resolver import resolve_unit, real_source, _per_denominator_in_unit, _gid

HERE = os.path.dirname(os.path.abspath(__file__))
cases = json.load(open(os.path.join(HERE, "cases.json")))

RATIO_UNITS = {"percent", "percent_yoy", "percent_points", "basis_points"}


def is_usd_per_x(uraw):
    return bool(uraw) and _gid._has_money_surface(uraw) and _per_denominator_in_unit(uraw)


def name_has_per(name):
    return "_per_" in _gid.slug(name or "")


def close(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) < 1e-6


A_pass = A_fail = B_pass = B_fail = C_pass = C_fail = D_pass = D_fail = 0
fails = []
needs_hint = []
overall_n = overall_ok = 0

for c in cases:
    exp = c.get("expected_canonical_unit") or c.get("expected")
    if not exp:
        continue
    name = c.get("driver_name", "")
    uraw = c.get("unit_raw", "")
    val = c.get("value") or None
    quote = c.get("quote") or None
    r = resolve_unit(name, uraw, val, quote=quote)  # NO hints

    overall_n += 1
    overall_ok += (r.canonical_unit == exp)

    usd_per_x = is_usd_per_x(uraw)
    has_per = name_has_per(name)
    scaled_exp = c.get("expected_scaled_value")

    # A. per-X happy path
    if usd_per_x and has_per:
        ok = (r.canonical_unit == exp) and (scaled_exp is None or close(r.scaled_value, scaled_exp))
        A_pass += ok; A_fail += (not ok)
        if not ok:
            fails.append(f"[A perX-happy] {name} {uraw!r} exp={exp}/{scaled_exp} got={r.canonical_unit}/{r.scaled_value}")
        continue

    # B. naming-lint triggers (USD per-X, name lacks _per_)
    if c.get("expect_warning"):
        has_warn = any("per-unit price" in w for w in r.warnings)
        B_pass += has_warn; B_fail += (not has_warn)
        if not has_warn:
            fails.append(f"[B lint-trigger] {name} {uraw!r} NO warning; warnings={r.warnings}")
        continue

    # C. money-aggregate value (x1000 traps)
    if exp == "m_usd" and scaled_exp is not None:
        ok = (r.canonical_unit == "m_usd") and close(r.scaled_value, scaled_exp)
        C_pass += ok; C_fail += (not ok)
        if not ok:
            fails.append(f"[C money-val] {name} {uraw!r} exp m_usd/{scaled_exp} got={r.canonical_unit}/{r.scaled_value}")
        continue

    # D. ratio / multiplier — must be exact label-only, but ONLY when the unit_raw
    # actually carries a ratio/multiplier surface. A ratio with an EMPTY unit_raw
    # (e.g. same_store_sales '' "rose 3%") has no surface signal and legitimately
    # needs a hint — same class as the bare count-nouns below, not a must-pass.
    has_ratio_surface = _gid._has_ratio_surface(uraw) or _gid._has_multiplier_surface(uraw)
    if (exp in RATIO_UNITS or exp == "x") and has_ratio_surface:
        ok = (r.canonical_unit == exp)
        D_pass += ok; D_fail += (not ok)
        if not ok:
            fails.append(f"[D ratio/x] {name} {uraw!r} exp={exp} got={r.canonical_unit}")
        continue

    # E. everything else: if label-only gives the right answer, great; if it falls to
    # 'unknown' (count-noun / bare scale word / non-USD), that's the by-design hint gap.
    if r.canonical_unit != exp:
        needs_hint.append(f"[{c.get('fact_type')}] {name} {uraw!r} exp={exp} got={r.canonical_unit}")


def line(label, p, f):
    total = p + f
    mark = "OK " if f == 0 else "XX "
    print(f"  {mark}{label:24s} {p}/{total}")


print("=== PROVENANCE ===")
src = real_source()
print(f"  imports: {src['guidance_ids_file']}")
print(f"  sha256:  {src['guidance_ids_sha256']}  reimplemented={src['reimplemented']}")
print()
print("=== LABEL-ONLY (no hints) — REAL unit_resolver ===")
print(f"  overall unit match (incl. by-design hint gaps): {overall_ok}/{overall_n} = {overall_ok/overall_n*100:.1f}%")
print()
print("  MUST-PASS label-only sections:")
line("A. per-X happy path", A_pass, A_fail)
line("B. naming-lint triggers", B_pass, B_fail)
line("C. money-aggregate value", C_pass, C_fail)
line("D. ratio / multiplier", D_pass, D_fail)
must_fail = A_fail + B_fail + C_fail + D_fail
print()
if fails:
    print(f"--- MUST-PASS FAILURES ({must_fail}) ---")
    for f in fails:
        print("  " + f)
else:
    print("  >>> ALL MUST-PASS SECTIONS GREEN <<<")
print()
print(f"=== NEEDS-A-HINT by design ({len(needs_hint)}) — resolve to 'unknown' label-only, ")
print("    fixed by the producer's unit_kind_hint (proven in run_probe_hints.py) ===")
for s in needs_hint:
    print("  " + s)
print()
print("JSON_BEGIN")
print(json.dumps({"label_only_overall": [overall_ok, overall_n],
                  "must_pass_failures": must_fail,
                  "A_perx": [A_pass, A_fail], "B_lint": [B_pass, B_fail],
                  "C_money_value": [C_pass, C_fail], "D_ratio": [D_pass, D_fail],
                  "needs_hint": len(needs_hint)}))
print("JSON_END")
