"""
Deterministic ID normalization for Guidance and GuidanceUpdate nodes.

Implements §2A of the Guidance System Implementation Spec (v2.3).
Every extraction code path MUST use these functions — never hand-build IDs.
"""

import hashlib
import re
from typing import Optional


# ── slug ────────────────────────────────────────────────────────────────────

def slug(text: str) -> str:
    """Lowercase, replace non-alphanumeric with _, collapse repeats, trim edges."""
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')


# ── Unit / scale canonicalization ───────────────────────────────────────────

# Canonical unit enum values (spec §2 field #9, §15F)
CANONICAL_UNITS = {
    'usd', 'm_usd',                                              # Currency
    'percent', 'percent_yoy', 'percent_points', 'basis_points',  # Ratios
    'x', 'count', 'unknown',                                     # Other
}

# Backward-compatible alias
VALID_UNITS = CANONICAL_UNITS

# Alias → canonical unit mapping (extensible registry, spec §15F)
# Adding a new unit: one entry in CANONICAL_UNITS + alias(es) here + test case.
# Per-share override (EPS/DPS → usd) applied AFTER alias resolution, not here.
UNIT_ALIASES = {
    # Currency (aggregate default is m_usd; per-share override applied later)
    '$': 'm_usd', 'dollars': 'm_usd',
    'm': 'm_usd', 'mm': 'm_usd', 'mn': 'm_usd',
    'million': 'm_usd', 'millions': 'm_usd', 'm usd': 'm_usd',
    'b': 'm_usd', 'bn': 'm_usd', 'billion': 'm_usd', 'billions': 'm_usd',
    'b_usd': 'm_usd', 'b usd': 'm_usd',
    'k': 'm_usd', 'thousand': 'm_usd', 'thousands': 'm_usd',
    # Percentages
    '%': 'percent', 'pct': 'percent', 'percentage': 'percent',
    '% yoy': 'percent_yoy', 'pct_yoy': 'percent_yoy', '% y/y': 'percent_yoy',
    'yoy': 'percent_yoy',
    # Percentage points (distinct from percent — "margin expanded 50 bps")
    '% points': 'percent_points', 'pp': 'percent_points',
    'percentage points': 'percent_points', 'ppts': 'percent_points',
    # Basis points (1 bp = 0.01%)
    'bps': 'basis_points', 'bp': 'basis_points', 'basis points': 'basis_points',
    # Multiplier
    'times': 'x', 'multiple': 'x',
    # Count
    'units': 'count', 'shares': 'count', 'employees': 'count', 'stores': 'count',
}

# Per-share metrics → always usd (not m_usd)
PER_SHARE_LABELS = {'eps', 'dps', 'earnings_per_share', 'dividends_per_share'}

# Scale multipliers for raw → m_usd conversion
_SCALE_TO_MILLIONS = {
    'b': 1000.0,
    'bn': 1000.0,
    'billion': 1000.0,
    't': 1000.0,       # trillion → not expected but safe
    'trillion': 1e6,
    'm': 1.0,
    'mm': 1.0,
    'mn': 1.0,
    'million': 1.0,
    'k': 0.001,
    'thousand': 0.001,
}


def _parse_numeric_with_scale(raw: str) -> tuple[Optional[float], Optional[float]]:
    """
    Parse a raw numeric string and return (value, multiplier_to_millions).
    Returns (None, None) if unparseable.

    Examples:
        "$1.13B"   → (1.13, 1000.0)
        "1130 M"   → (1130.0, 1.0)
        "94"       → (94.0, None)   — no scale detected
        "1,130M"   → (1130.0, 1.0)
    """
    if raw is None:
        return None, None
    s = str(raw).strip().lstrip('$').replace(',', '')
    # Try to split number from suffix
    m = re.match(r'^([+-]?\d+\.?\d*)\s*([a-zA-Z]*)\s*$', s)
    if not m:
        return None, None
    value = float(m.group(1))
    suffix = m.group(2).lower().rstrip('s')  # "billions" → "billion"
    if suffix in _SCALE_TO_MILLIONS:
        return value, _SCALE_TO_MILLIONS[suffix]
    if suffix in ('', 'usd'):
        return value, None  # no scale suffix
    return value, None


def canonicalize_unit(unit_raw: str, label_slug: str) -> str:
    """
    Map a raw unit string to the canonical enum value.

    Resolution order:
      1. Already canonical → passthrough
      2. UNIT_ALIASES lookup → canonical form
      3. No match → 'unknown'
      4. Per-share override: EPS/DPS force 'usd' (never 'm_usd')
    """
    u = unit_raw.lower().strip() if unit_raw else 'unknown'

    # 1. Already canonical
    if u in CANONICAL_UNITS:
        canonical = u
    # 2. Alias lookup
    elif u in UNIT_ALIASES:
        canonical = UNIT_ALIASES[u]
    # 3. No match
    else:
        canonical = 'unknown'

    # 4. Per-share override: EPS/DPS always usd, never m_usd
    if canonical == 'm_usd' and label_slug in PER_SHARE_LABELS:
        return 'usd'

    return canonical


def canonicalize_value(value: Optional[float], unit_raw: str, canonical_unit: str,
                       label_slug: str) -> Optional[float]:
    """
    Normalize a numeric value to canonical scale.

    Rules:
      - Aggregate currency metrics: value expressed in millions (m_usd).
        $1.13B → 1130.0, $94M → 94.0, $2000 (bare) → treated as already in millions.
      - Per-share (EPS/DPS): value in usd (no scale change).
      - Percent/count/x: no scale change.
    """
    if value is None:
        return None

    if canonical_unit not in ('m_usd', 'usd'):
        return value

    # Per-share: no scaling
    if label_slug in PER_SHARE_LABELS:
        return value

    # Aggregate currency: detect raw scale and convert to millions
    if canonical_unit == 'm_usd' and unit_raw:
        _, multiplier = _parse_numeric_with_scale(f"{value}{unit_raw}")
        if multiplier is not None:
            return round(value * multiplier, 6)

    # If unit was already 'm_usd' or 'million', value is already in millions
    return value


# ── Text normalization for hashing ──────────────────────────────────────────

def _normalize_text(text: Optional[str]) -> str:
    """Lowercase, trim, collapse whitespace. Null → '.'"""
    if text is None:
        return '.'
    s = text.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return s if s else '.'


def _normalize_numeric(value: Optional[float]) -> str:
    """Canonical decimal string. Null → '.'"""
    if value is None:
        return '.'
    # Remove trailing zeros: 1130.000000 → 1130.0, 1.5 → 1.5
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


# ── evhash16 ────────────────────────────────────────────────────────────────

def compute_evhash16(low: Optional[float], mid: Optional[float],
                     high: Optional[float], unit: str,
                     qualitative: Optional[str],
                     conditions: Optional[str]) -> str:
    """
    sha256("{low}|{mid}|{high}|{unit}|{qualitative}|{conditions}")[:16]

    All inputs must be ALREADY CANONICALIZED (values in canonical scale,
    unit as canonical enum). Nulls encoded as '.'.
    """
    parts = [
        _normalize_numeric(low),
        _normalize_numeric(mid),
        _normalize_numeric(high),
        unit,
        _normalize_text(qualitative),
        _normalize_text(conditions),
    ]
    payload = '|'.join(parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


# ── Source ID canonicalization ──────────────────────────────────────────────

def canonicalize_source_id(source_id: str) -> str:
    """Trim whitespace, replace ':' with '_' for delimiter safety."""
    return source_id.strip().replace(':', '_')


# ── Top-level builder ──────────────────────────────────────────────────────

def build_guidance_ids(
    *,
    label: str,
    source_id: str,
    period_u_id: str,
    basis_norm: str,
    segment: str = 'Total',
    low: Optional[float] = None,
    mid: Optional[float] = None,
    high: Optional[float] = None,
    unit_raw: str = 'unknown',
    qualitative: Optional[str] = None,
    conditions: Optional[str] = None,
) -> dict:
    """
    Single entry point for all ID normalization.

    Returns dict with:
        guidance_id:        "guidance:{label_slug}"
        guidance_update_id: "gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}:{evhash16}"
        evhash16:           16-char hex string
        label_slug:         normalized label
        segment_slug:       normalized segment
        canonical_unit:     canonical unit enum value
        canonical_low:      value in canonical scale (or None)
        canonical_mid:      value in canonical scale (or None)
        canonical_high:     value in canonical scale (or None)
    """
    # Validate required fields
    if not label or not label.strip():
        raise ValueError("label must be non-empty")
    if not source_id or not source_id.strip():
        raise ValueError("source_id must be non-empty")
    if not period_u_id or not period_u_id.strip():
        raise ValueError("period_u_id must be non-empty")

    # Validate basis_norm
    valid_bases = {'gaap', 'non_gaap', 'constant_currency', 'unknown'}
    if basis_norm not in valid_bases:
        raise ValueError(f"basis_norm must be one of {valid_bases}, got '{basis_norm}'")

    # Slugs
    label_slug = slug(label)
    segment_slug = slug(segment) if segment and segment.strip() else 'total'

    # Unit canonicalization
    canonical_unit = canonicalize_unit(unit_raw, label_slug)

    # Value canonicalization (scale normalization)
    canonical_low = canonicalize_value(low, unit_raw, canonical_unit, label_slug)
    canonical_mid = canonicalize_value(mid, unit_raw, canonical_unit, label_slug)
    canonical_high = canonicalize_value(high, unit_raw, canonical_unit, label_slug)

    # Compute mid if not provided but low+high are
    if canonical_mid is None and canonical_low is not None and canonical_high is not None:
        canonical_mid = round((canonical_low + canonical_high) / 2, 6)

    # Evidence hash
    evhash16 = compute_evhash16(
        canonical_low, canonical_mid, canonical_high,
        canonical_unit, qualitative, conditions,
    )

    # Source ID
    safe_source_id = canonicalize_source_id(source_id)

    # Assemble IDs
    guidance_id = f"guidance:{label_slug}"
    guidance_update_id = (
        f"gu:{safe_source_id}:{label_slug}:{period_u_id}"
        f":{basis_norm}:{segment_slug}:{evhash16}"
    )

    # Validate prefixes (spec Decision #33)
    assert guidance_id.startswith('guidance:'), f"Bad guidance_id: {guidance_id}"
    assert guidance_update_id.startswith('gu:'), f"Bad guidance_update_id: {guidance_update_id}"

    result = {
        'guidance_id': guidance_id,
        'guidance_update_id': guidance_update_id,
        'evhash16': evhash16,
        'label_slug': label_slug,
        'segment_slug': segment_slug,
        'canonical_unit': canonical_unit,
        'canonical_low': canonical_low,
        'canonical_mid': canonical_mid,
        'canonical_high': canonical_high,
    }

    # Preserve raw unit when canonicalization produced 'unknown' (§15F)
    if canonical_unit == 'unknown' and unit_raw and unit_raw.strip().lower() != 'unknown':
        result['unit_raw'] = unit_raw.strip()

    return result
