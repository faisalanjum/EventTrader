"""
Deterministic ID normalization for Guidance and GuidanceUpdate nodes.

Implements §2A of the Guidance System Implementation Spec (v3.0).
Every extraction code path MUST use these functions — never hand-build IDs.
"""

import hashlib
import re
import calendar
import logging
from typing import Optional

from fiscal_math import _compute_fiscal_dates

logger = logging.getLogger(__name__)


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
    't': 1e6,          # trillion → matches 'trillion' entry
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
            if multiplier > 1 and value > 999:
                raise ValueError(f"{value} with '{unit_raw}' looks pre-scaled — pass the number exactly as stated in source")
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


# ── DEPRECATED: Fiscal-keyed Period u_id builder ─────────────────────
# Kept for backward compatibility. Use build_guidance_period_id() instead.

def build_period_u_id(
    *,
    cik: str,
    period_type: str = 'duration',
    fiscal_year: Optional[int] = None,
    fiscal_quarter: Optional[int] = None,
    half: Optional[int] = None,
    long_range_start: Optional[int] = None,
    long_range_end: Optional[int] = None,
    medium_term: bool = False,
) -> str:
    """
    Build a fiscal-keyed Period u_id in the guidance_period_ namespace.

    Format: guidance_period_{cik}_{period_type}_{fiscal_key}

    Scenarios:
      Quarter:    guidance_period_320193_duration_FY2025_Q3
      Annual:     guidance_period_320193_duration_FY2025
      Half:       guidance_period_320193_duration_FY2025_H2
      LR (year):  guidance_period_320193_duration_LR_2028
      LR (span):  guidance_period_320193_duration_LR_2026_2028
      MT:         guidance_period_320193_duration_MT
      Undefined:  guidance_period_320193_duration_UNDEF
    """
    if not cik or not str(cik).strip():
        raise ValueError("cik must be non-empty")

    # Strip leading zeros from CIK
    cik_clean = str(int(str(cik).strip()))

    if period_type not in ('duration', 'instant'):
        raise ValueError(f"period_type must be 'duration' or 'instant', got '{period_type}'")

    prefix = f"guidance_period_{cik_clean}_{period_type}"

    # Medium-term (no FY)
    if medium_term:
        return f"{prefix}_MT"

    # Long-range
    if long_range_start is not None:
        if long_range_end is not None and long_range_end != long_range_start:
            return f"{prefix}_LR_{long_range_start}_{long_range_end}"
        return f"{prefix}_LR_{long_range_start}"

    # Standard fiscal periods
    if fiscal_year is not None:
        if half is not None:
            return f"{prefix}_FY{fiscal_year}_H{half}"
        if fiscal_quarter is not None:
            return f"{prefix}_FY{fiscal_year}_Q{fiscal_quarter}"
        return f"{prefix}_FY{fiscal_year}"

    # Undefined (no fiscal identity)
    return f"{prefix}_UNDEF"


# ── Calendar-based GuidancePeriod builder ────────────────────────────────

KNOWN_INSTANT_LABELS = frozenset({
    'cash_and_equivalents', 'total_debt', 'long_term_debt',
    'shares_outstanding', 'book_value', 'net_debt',
})

SENTINEL_MAP = {
    'short_term': 'gp_ST',
    'medium_term': 'gp_MT',
    'long_term': 'gp_LT',
    'undefined': 'gp_UNDEF',
}


def build_guidance_period_id(
    *,
    fye_month: int,
    fiscal_year: Optional[int] = None,
    fiscal_quarter: Optional[int] = None,
    half: Optional[int] = None,
    month: Optional[int] = None,
    long_range_start_year: Optional[int] = None,
    long_range_end_year: Optional[int] = None,
    calendar_override: bool = False,
    sentinel_class: Optional[str] = None,
    time_type: Optional[str] = None,
    label_slug: Optional[str] = None,
) -> dict:
    """
    Route LLM extraction fields to a calendar-based GuidancePeriod.

    Returns dict: {u_id, start_date, end_date, period_scope, time_type}

    Routing priority (first match wins):
      1. sentinel_class set       -> sentinel u_id, null dates
      2. long_range_end_year set  -> long_range, FY-based dates
      3. month set                -> monthly, calendar month
      4. half set                 -> half, compose from Q starts/ends
      5. fiscal_quarter set       -> quarter
      6. fiscal_year set (only)   -> annual
      7. fallthrough              -> gp_UNDEF (defensive)
    """
    fye = 12 if calendar_override else fye_month

    # Detect instant from label
    is_instant = (time_type == 'instant') or (
        label_slug is not None and label_slug in KNOWN_INSTANT_LABELS
    )
    resolved_time_type = 'instant' if is_instant else 'duration'

    # Step 1: Sentinel
    if sentinel_class is not None:
        if sentinel_class not in SENTINEL_MAP:
            raise ValueError(
                f"sentinel_class must be one of {set(SENTINEL_MAP)}, got '{sentinel_class}'"
            )
        return {
            'u_id': SENTINEL_MAP[sentinel_class],
            'start_date': None,
            'end_date': None,
            'period_scope': sentinel_class,
            'time_type': resolved_time_type,
        }

    # Step 2: Long range
    if long_range_end_year is not None:
        if long_range_start_year is not None:
            start = _compute_fiscal_dates(fye, long_range_start_year, "FY")[0]
        else:
            start = _compute_fiscal_dates(fye, long_range_end_year, "FY")[0]
        end = _compute_fiscal_dates(fye, long_range_end_year, "FY")[1]
        return _finalize(start, end, 'long_range', resolved_time_type, is_instant)

    # For steps 3-6, fiscal_year is required
    fy = fiscal_year

    # Step 3: Monthly (no FYE needed — calendar month)
    if month is not None:
        year = fy if fy is not None else 2000  # fy should always be set
        _, last_day = calendar.monthrange(year, month)
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{last_day:02d}"
        return _finalize(start, end, 'monthly', resolved_time_type, is_instant)

    # Step 4: Half
    if half is not None and fy is not None:
        if half == 1:
            start = _compute_fiscal_dates(fye, fy, "Q1")[0]
            end = _compute_fiscal_dates(fye, fy, "Q2")[1]
        elif half == 2:
            start = _compute_fiscal_dates(fye, fy, "Q3")[0]
            end = _compute_fiscal_dates(fye, fy, "Q4")[1]
        else:
            raise ValueError(f"half must be 1 or 2, got {half}")
        return _finalize(start, end, 'half', resolved_time_type, is_instant)

    # Step 5: Quarter
    if fiscal_quarter is not None and fy is not None:
        start, end = _compute_fiscal_dates(fye, fy, f"Q{fiscal_quarter}")
        return _finalize(start, end, 'quarter', resolved_time_type, is_instant)

    # Step 6: Annual
    if fy is not None:
        start, end = _compute_fiscal_dates(fye, fy, "FY")
        return _finalize(start, end, 'annual', resolved_time_type, is_instant)

    # Step 7: Fallthrough — should not happen if LLM set sentinel_class
    logger.warning("build_guidance_period_id: no fields matched, falling through to gp_UNDEF")
    return {
        'u_id': 'gp_UNDEF',
        'start_date': None,
        'end_date': None,
        'period_scope': 'undefined',
        'time_type': resolved_time_type,
    }


def _finalize(start_date: str, end_date: str, period_scope: str,
              time_type: str, is_instant: bool) -> dict:
    """Build the return dict, collapsing to instant if needed."""
    if is_instant:
        # Instant: start_date = end_date (the period's end date)
        return {
            'u_id': f"gp_{end_date}_{end_date}",
            'start_date': end_date,
            'end_date': end_date,
            'period_scope': period_scope,
            'time_type': 'instant',
        }
    return {
        'u_id': f"gp_{start_date}_{end_date}",
        'start_date': start_date,
        'end_date': end_date,
        'period_scope': period_scope,
        'time_type': 'duration',
    }


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
        guidance_update_id: "gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}"
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
        f":{basis_norm}:{segment_slug}"
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
