"""
unit_resolver.py — SHARED, isolated unit canonicalization for Guidance AND Driver.

WHY: one source of truth so the guidance pipeline and the proposed Driver
producer resolve units identically (no divergence). This module IMPORTS the
production unit primitives from guidance_ids.py — it does NOT re-implement any
canonicalization logic — and reproduces the EXACT V2 sequence that
build_guidance_ids uses (guidance_ids.py:_compute_v2, lines 889-917):

    kind = _resolve_kind(hint, unit_raw, xbrl_qname, label_slug)
    money_mode = _resolve_money_mode(hint, unit_raw, xbrl_qname, label_slug, kind)
    ratio_subtype = _resolve_ratio_subtype(unit_raw, quote)   # only when kind=='ratio'
    canonical_unit = _combine_resolved_unit(kind, money_mode, ratio_subtype)
    scaled_value = canonicalize_value(value, unit_raw, canonical_unit, label_slug, kind, money_mode)

It adds a THIN, opt-in robustness layer on top of the real primitives (never
changes them):
  • input normalization so glued currency+scale tokens ('$B') scale correctly
    (the bare primitives drop the x1000 scale when '$' is glued to the token);
  • EXPLICIT surfacing of the cents-on-aggregate / pre-scaled guards — the real
    functions raise; we return result.error (or re-raise under strict=True)
    instead of silently returning None;
  • a denominator LINT: a per-X unit ('$/barrel') needs the denominator in the
    driver NAME (the name carries 'per X', the unit stays the base 'usd').
    We WARN — we never auto-rewrite to 'unknown'.

PRODUCTION NOTES (vs. the throwaway probe):
  - No hard-coded absolute path: self-locates guidance_ids.py (env override,
    co-location, or repo walk-up).
  - No fake source_id / period_u_id: calls the unit primitives directly, never
    the full build_guidance_ids (which needs IDs/periods we don't have here).
  - Honest provenance: real_source() returns the imported file path + a REAL
    sha256 of guidance_ids.py (no unverifiable claims).

USAGE (Driver: resolve level_* and change_* with SEPARATE calls):
    from unit_resolver import resolve_unit, resolve_driverupdate_units
    r = resolve_unit("revenue", "$B", 1.5, unit_kind_hint="money", money_mode_hint="aggregate")
    # r.canonical_unit == "m_usd"; r.scaled_value == 1500.0
"""

import os
import sys
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional


# ── self-locate the production guidance_ids.py (no hard-coded abs path) ──────
def _locate_scripts_dir() -> str:
    env = os.environ.get("GUIDANCE_SCRIPTS_DIR")
    if env and os.path.isfile(os.path.join(env, "guidance_ids.py")):
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isfile(os.path.join(here, "guidance_ids.py")):
        return here  # co-located in the scripts dir (the shared production home)
    d = here
    for _ in range(10):
        cand = os.path.join(d, ".claude", "skills", "earnings-orchestrator", "scripts")
        if os.path.isfile(os.path.join(cand, "guidance_ids.py")):
            return os.path.abspath(cand)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise ImportError(
        "unit_resolver: cannot locate guidance_ids.py. "
        "Set GUIDANCE_SCRIPTS_DIR or co-locate this file with guidance_ids.py."
    )


_SCRIPTS_DIR = _locate_scripts_dir()
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import guidance_ids as _gid  # noqa: E402  (the REAL production module)

CANONICAL_UNITS = _gid.CANONICAL_UNITS
VALID_UNIT_KIND_HINTS = _gid.VALID_UNIT_KIND_HINTS
VALID_MONEY_MODE_HINTS = _gid.VALID_MONEY_MODE_HINTS

_CURRENCY_SYMBOLS = "$€£¥"


@dataclass
class UnitResolution:
    canonical_unit: str
    scaled_value: Optional[float]
    kind: str
    money_mode: str
    ratio_subtype: str
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    normalized_unit_raw: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None


def real_source() -> dict:
    """Honest provenance — the real module path + a REAL sha256 (no fake claims)."""
    path = _gid.__file__
    try:
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        digest = None
    return {
        "guidance_ids_file": path,
        "guidance_ids_sha256": digest,
        "resolve_uses_module": _gid._resolve_kind.__module__,
        "reimplemented": False,
    }


def _normalize_scale_token(raw: str) -> str:
    """Strip currency symbols/whitespace so '$B'->'B' scales (kind detection still uses the raw)."""
    if not raw:
        return raw
    t = raw
    for c in _CURRENCY_SYMBOLS:
        t = t.replace(c, "")
    return t.strip()


def _per_denominator_in_unit(raw: str) -> bool:
    t = (raw or "").lower()
    return ("/" in t) or (" per " in f" {t} ")


def lint_per_x_naming(driver_name: Optional[str], unit_raw: Optional[str]) -> Optional[str]:
    """Hint-BLIND naming lint: a USD per-X unit needs the denominator in the NAME.

    Fires when ALL three hold (scoped to USD money per-X ONLY):
      • the unit numerator is USD money  ('$' or a usd/dollar/cents word)
      • the unit carries a denominator   ('/' or ' per ')
      • the driver_name has no '_per_' token to hold that denominator

    Why USD-only: only USD per-X collapses to the shared base 'usd' and silently
    merges in the read-time series key. Non-USD per-X ('€/barrel') already resolves
    to 'unknown', and non-money 'per' surfaces ('% per year', 'units per store') do
    NOT collapse to a shared base — none of them need a rename, so none are flagged.

    Takes NO hints by design: a price_like hint fixes the UNIT (-> usd) but NOT the
    NAME collision in the series key, so a hint must NEVER be able to mute this
    warning (this is the hole in a hint-gated lint). Returns a rename message, or
    None if the name is fine.
    """
    raw = "" if unit_raw is None else str(unit_raw)
    if not _gid._has_money_surface(raw):
        return None
    if not _per_denominator_in_unit(raw):
        return None
    if "_per_" in _gid.slug(driver_name or ""):
        return None
    return (
        f"money per-unit price ({raw!r}) but driver_name {driver_name!r} lacks a "
        f"'_per_X' denominator -> resolves to a base currency and will collide in the "
        f"series key with other per-X facts. Put the 'per X' in the driver_name "
        f"(unit stays base 'usd'). (hint-blind; not auto-converted to 'unknown'.)"
    )


def resolve_unit(
    driver_name: str,
    unit_raw: Optional[str],
    value=None,
    *,
    unit_kind_hint: Optional[str] = None,
    money_mode_hint: Optional[str] = None,
    quote: Optional[str] = None,
    xbrl_qname: Optional[str] = None,
    strict: bool = False,
) -> UnitResolution:
    """
    Canonicalize one unit-bearing quantity (a level OR a change) using the REAL
    production V2 sequence. Call once per field (level_*, then change_*).
    """
    if unit_kind_hint and unit_kind_hint not in VALID_UNIT_KIND_HINTS:
        raise ValueError(f"invalid unit_kind_hint: {unit_kind_hint!r}")
    if money_mode_hint and money_mode_hint not in VALID_MONEY_MODE_HINTS:
        raise ValueError(f"invalid money_mode_hint: {money_mode_hint!r}")

    warnings: List[str] = []
    error: Optional[str] = None
    label_slug = _gid.slug(driver_name or "")
    raw = "" if unit_raw is None else str(unit_raw)

    # Denominator lint: a USD per-X unit needs the denominator in the NAME.
    # Hint-BLIND on purpose — a price_like hint fixes the unit but NOT the name
    # collision, so it must not be able to mute this (see lint_per_x_naming).
    _lint = lint_per_x_naming(driver_name, raw)
    if _lint:
        warnings.append(_lint)

    # KIND/MODE/SUBTYPE detection uses the RAW unit (the '$', '/', '%' surfaces matter).
    kind = _gid._resolve_kind(unit_kind_hint, raw, xbrl_qname, label_slug)
    money_mode = _gid._resolve_money_mode(money_mode_hint, raw, xbrl_qname, label_slug, kind)
    ratio_subtype = _gid._resolve_ratio_subtype(raw, quote) if kind == "ratio" else "unknown"
    canonical_unit = _gid._combine_resolved_unit(kind, money_mode, ratio_subtype)

    # SCALING uses the normalized token so glued '$B' scales (fix for the x1000 drop).
    norm = _normalize_scale_token(raw)
    if norm != raw and norm:
        warnings.append(
            f"unit_raw {raw!r} normalized to {norm!r} for scale detection — "
            f"emit a clean scale token (e.g. 'B'/'billion'), not a glued '$B'."
        )

    scaled: Optional[float] = None
    if value is not None and value != "":
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = None
            warnings.append(f"value {value!r} is not a single number (a range?) — not scaled.")
        if v is not None:
            try:
                scaled = _gid.canonicalize_value(
                    v, norm, canonical_unit, label_slug,
                    resolved_kind=kind, resolved_money_mode=money_mode,
                )
            except ValueError as e:
                error = str(e)  # cents-on-aggregate / pre-scaled — SURFACED, not swallowed
                if strict:
                    raise

    return UnitResolution(
        canonical_unit=canonical_unit, scaled_value=scaled, kind=kind,
        money_mode=money_mode, ratio_subtype=ratio_subtype,
        warnings=warnings, error=error, normalized_unit_raw=norm,
    )


def resolve_driverupdate_units(
    driver_name: str,
    *,
    level_value=None, level_unit_raw: Optional[str] = None,
    change_value=None, change_unit_raw: Optional[str] = None,
    unit_kind_hint: Optional[str] = None, money_mode_hint: Optional[str] = None,
    quote: Optional[str] = None, xbrl_qname: Optional[str] = None, strict: bool = False,
) -> dict:
    """Resolve a DriverUpdate's level_* and change_* with SEPARATE calls (per the schema)."""
    out = {"level": None, "change": None}
    if level_unit_raw is not None or level_value is not None:
        out["level"] = resolve_unit(
            driver_name, level_unit_raw, level_value, unit_kind_hint=unit_kind_hint,
            money_mode_hint=money_mode_hint, quote=quote, xbrl_qname=xbrl_qname, strict=strict)
    if change_unit_raw is not None or change_value is not None:
        out["change"] = resolve_unit(
            driver_name, change_unit_raw, change_value, unit_kind_hint=unit_kind_hint,
            money_mode_hint=money_mode_hint, quote=quote, xbrl_qname=xbrl_qname, strict=strict)
    return out


if __name__ == "__main__":
    import json
    print("=== real_source (honest provenance) ===")
    print(json.dumps(real_source(), indent=2))
    print("\n=== smoke ===")
    for args, kw in [
        (("revenue", "$B", 1.5), dict(unit_kind_hint="money", money_mode_hint="aggregate")),
        (("eps", "$", 1.10), dict(unit_kind_hint="money", money_mode_hint="price_like")),
        (("fuel_cost_per_barrel", "$/barrel", 80), {}),
        (("oil_price", "$/barrel", 80), {}),
    ]:
        r = resolve_unit(*args, **kw)
        print(f"  {args} {kw} -> unit={r.canonical_unit} value={r.scaled_value} warn={len(r.warnings)} err={r.error}")
