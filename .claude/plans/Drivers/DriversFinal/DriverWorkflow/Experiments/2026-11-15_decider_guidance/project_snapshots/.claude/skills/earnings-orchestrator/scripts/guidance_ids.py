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

def _is_per_share_label(label_slug: str) -> bool:
    """Detect per-share metrics via slug token patterns.

    Rules (any match → True):
      1. Exact: 'eps' or 'dps'
      2. Prefix: starts with 'eps_' or 'dps_' (catches XBRL-ordered labels like eps_diluted)
      3. Suffix: ends with '_eps' or '_dps' (catches adjusted_eps, non_gaap_eps, etc.)
      4. Contains: 'per_share' or 'per_unit' (catches ffo_per_share, distributions_per_unit, etc.)
    """
    if label_slug in ('eps', 'dps'):
        return True
    if label_slug.startswith('eps_') or label_slug.startswith('dps_'):
        return True
    if label_slug.endswith('_eps') or label_slug.endswith('_dps'):
        return True
    if 'per_share' in label_slug or 'per_unit' in label_slug:
        return True
    return False

# Legacy constant — no longer used internally. Kept for backward compatibility
# in case external code imports this name.
PER_SHARE_LABELS = {'eps', 'dps', 'earnings_per_share', 'dividends_per_share'}


# ── Share-count classifier ─────────────────────────────────────────────────

_KNOWN_SHARE_COUNT_LABELS = frozenset({
    'share_count',
    'shares_outstanding',
})


def _is_share_count_label(label_slug: str) -> bool:
    """Detect reviewed share-count metrics that should use 'count', not 'm_usd'.

    Scope is intentionally narrow: only share-count labels proven in the current
    pipeline, plus safe share-specific token variants.

    Rules (any match → True):
      1. Exact: in _KNOWN_SHARE_COUNT_LABELS
      2. Suffix: ends with '_share_count' (diluted_share_count)
      3. Suffix: ends with '_shares' (diluted_shares, basic_shares)
    """
    if label_slug in _KNOWN_SHARE_COUNT_LABELS:
        return True
    if label_slug.endswith('_share_count'):
        return True
    if label_slug.endswith('_shares'):
        return True
    return False


# ── V2 Unit Resolution (spec V2 §3–§6) ───────────────────────────────────

VALID_UNIT_KIND_HINTS = {'money', 'ratio', 'count', 'multiplier', 'unknown'}
VALID_MONEY_MODE_HINTS = {'aggregate', 'price_like', 'unknown'}


def _normalize_unit_text(text: Optional[str]) -> str:
    """Lowercase, strip, collapse whitespace. None/empty → ''."""
    if not text:
        return ''
    s = text.lower().strip()
    return re.sub(r'\s+', ' ', s)


# ── V2 scale table (absolute multipliers, mode-independent) ──────────────

_ABSOLUTE_SCALE = {
    'trillion': 1e12, 'trillions': 1e12, 't': 1e12,
    'billion': 1e9, 'billions': 1e9, 'bn': 1e9, 'b': 1e9,
    'million': 1e6, 'millions': 1e6, 'mm': 1e6, 'mn': 1e6, 'm': 1e6,
    'thousand': 1e3, 'thousands': 1e3, 'k': 1e3,
    'cent': 0.01, 'cents': 0.01,
}


def _extract_scale_factor(unit_raw: str) -> Optional[float]:
    """Return the raw absolute scale multiplier from unit_raw, or None."""
    text = _normalize_unit_text(unit_raw)
    if not text:
        return None
    for token in text.split():
        if token in _ABSOLUTE_SCALE:
            return _ABSOLUTE_SCALE[token]
    return None


# ── V2 surface / evidence detectors ──────────────────────────────────────

def _has_ratio_surface(unit_raw: str) -> bool:
    """§5.1 P1: ratio markers in unit_raw (token/word level)."""
    text = _normalize_unit_text(unit_raw)
    if not text:
        return False
    if '%' in text:
        return True
    if any(p in text for p in (
        'basis point', 'percentage point',
        'year over year', 'year-over-year',
    )):
        return True
    tokens = set(text.split())
    return bool(tokens & {
        'pct', 'percent', 'percentage',
        'yoy', 'y/y', 'yr/yr',
        'bp', 'bps', 'pp', 'ppt', 'ppts',
    })


def _has_multiplier_surface(unit_raw: str) -> bool:
    """§5.1 P2: multiplier markers (isolated x, 2.5x, times, multiple)."""
    text = _normalize_unit_text(unit_raw)
    if not text:
        return False
    for token in text.split():
        if token in ('x', 'times', 'multiple'):
            return True
        if token.endswith('x') and len(token) > 1:
            try:
                float(token[:-1])
                return True
            except ValueError:
                pass
    return False


def _has_money_surface(unit_raw: str) -> bool:
    """§5.1 P3: money markers (token level — cent/cents never substring of percent)."""
    text = _normalize_unit_text(unit_raw)
    if not text:
        return False
    if '$' in text:
        return True
    tokens = set(text.split())
    return bool(tokens & {'usd', 'dollar', 'dollars', 'cent', 'cents'})


_XBRL_PER_SHARE_MARKERS = ('PerShare', 'PerUnit', 'PerDilutedShare', 'PerBasicShare')

_XBRL_COUNT_RE = re.compile(
    r'SharesOutstanding|ShareCount'
    r'|WeightedAverage\w*Shares'
    r'|NumberOf\w*Shares'
)


def _has_price_like_surface(unit_raw: str, xbrl_qname: Optional[str] = None) -> bool:
    """§5.2 P1–P2: XBRL per-share markers OR surface 'per <noun>'."""
    if xbrl_qname:
        for marker in _XBRL_PER_SHARE_MARKERS:
            if marker in xbrl_qname:
                return True
    text = _normalize_unit_text(unit_raw)
    if text and ' per ' in f' {text} ':
        return True
    return False


def _has_hard_label_money_signal(label_slug: str) -> bool:
    """§5.1 P6: isolated eps/dps token, or slug contains per_share/per_unit."""
    if not label_slug:
        return False
    if 'per_share' in label_slug or 'per_unit' in label_slug:
        return True
    tokens = label_slug.split('_')
    return 'eps' in tokens or 'dps' in tokens


def _has_hard_label_price_like_signal(label_slug: str) -> bool:
    """§5.2 P3: isolated per/eps/dps token, or per_share/per_unit in slug."""
    if not label_slug:
        return False
    if 'per_share' in label_slug or 'per_unit' in label_slug:
        return True
    tokens = set(label_slug.split('_'))
    return bool(tokens & {'per', 'eps', 'dps'})


# ── V2 resolvers ─────────────────────────────────────────────────────────

_COUNT_LABEL_PRIORS = frozenset({'shares_outstanding', 'share_count', 'headcount'})
_PRICE_LIKE_LABEL_PRIORS = frozenset({
    'average_selling_price', 'average_daily_rate', 'asp', 'adr', 'arpu', 'revpar',
})


def _resolve_kind(unit_kind_hint: Optional[str], unit_raw: str,
                  xbrl_qname: Optional[str], label_slug: str) -> str:
    """§5.1: resolve semantic kind from all evidence, contradictions → unknown.

    Contradiction detection uses surface (P1-P3) + XBRL (P4-P5) only.
    Label evidence (P6) participates in precedence, not contradiction,
    because compound labels like 'eps_growth' contain 'eps' as a modifier
    of a ratio metric, not as a standalone money signal.
    """
    # P1–P3 + P4–P5: hard evidence (participates in contradiction check)
    hard_evidence = set()

    if _has_ratio_surface(unit_raw):
        hard_evidence.add('ratio')
    if _has_multiplier_surface(unit_raw):
        hard_evidence.add('multiplier')
    if _has_money_surface(unit_raw):
        hard_evidence.add('money')

    if xbrl_qname:
        has_ps = any(m in xbrl_qname for m in _XBRL_PER_SHARE_MARKERS)
        if not has_ps and _XBRL_COUNT_RE.search(xbrl_qname):
            hard_evidence.add('count')
        elif has_ps:
            hard_evidence.add('money')

    # Contradiction among hard evidence → unknown
    if len(hard_evidence) > 1:
        return 'unknown'
    if hard_evidence:
        return hard_evidence.pop()

    # P6: label evidence (precedence only, not contradiction)
    if _has_hard_label_money_signal(label_slug):
        return 'money'

    # P7: LLM hint
    if unit_kind_hint and unit_kind_hint in VALID_UNIT_KIND_HINTS and unit_kind_hint != 'unknown':
        return unit_kind_hint

    # P8: conservative count prior
    if label_slug in _COUNT_LABEL_PRIORS:
        return 'count'

    # P9: fallback
    return 'unknown'


def _resolve_money_mode(money_mode_hint: Optional[str], unit_raw: str,
                        xbrl_qname: Optional[str], label_slug: str,
                        resolved_kind: str) -> str:
    """§5.2: resolve aggregate vs price_like (only when kind==money)."""
    if resolved_kind != 'money':
        return 'unknown'

    # P1–P2: XBRL per-share / surface denominator
    if _has_price_like_surface(unit_raw, xbrl_qname):
        return 'price_like'

    # P3: strong label evidence
    if _has_hard_label_price_like_signal(label_slug):
        return 'price_like'

    # P4: LLM hint
    if money_mode_hint and money_mode_hint in VALID_MONEY_MODE_HINTS and money_mode_hint != 'unknown':
        return money_mode_hint

    # P5: narrow label prior
    if label_slug in _PRICE_LIKE_LABEL_PRIORS:
        return 'price_like'

    # P6: fallback
    return 'aggregate'


def _resolve_ratio_subtype(unit_raw: str, quote: Optional[str] = None) -> str:
    """§5.3: resolve ratio subtype. Quote restricted to YoY context only."""
    text = _normalize_unit_text(unit_raw)
    tokens = set(text.split()) if text else set()

    # P1: bps markers (unit_raw only)
    if tokens & {'bp', 'bps'} or 'basis point' in text:
        return 'basis_points'

    # P2: points markers (unit_raw only)
    if (tokens & {'pp', 'ppt', 'ppts', 'point', 'points'}
            or 'percentage point' in text):
        return 'percent_points'

    # P3: YoY markers (unit_raw only)
    if (tokens & {'yoy', 'y/y', 'yr/yr'}
            or 'year over year' in text
            or 'year-over-year' in text):
        return 'percent_yoy'

    # Secondary: quote for YoY temporal context ONLY (never bps/points)
    if quote:
        qt = _normalize_unit_text(quote)
        qt_tokens = set(qt.split()) if qt else set()
        if (qt_tokens & {'yoy', 'y/y', 'yr/yr'}
                or 'year over year' in qt
                or 'year-over-year' in qt):
            return 'percent_yoy'

    # P4: fallback
    return 'percent'


def _combine_resolved_unit(resolved_kind: str, resolved_money_mode: str,
                           resolved_ratio_subtype: str) -> str:
    """§4 mapping table: axes → canonical_unit."""
    if resolved_kind == 'money':
        return 'usd' if resolved_money_mode == 'price_like' else 'm_usd'
    if resolved_kind == 'ratio':
        return resolved_ratio_subtype
    if resolved_kind == 'count':
        return 'count'
    if resolved_kind == 'multiplier':
        return 'x'
    return 'unknown'


# ── V2 scale functions ───────────────────────────────────────────────────

def _scale_aggregate_money(value: float, unit_raw: str) -> float:
    """§6.1: scale to millions of USD. Guards: cents contradiction + pre-scaled."""
    text = _normalize_unit_text(unit_raw)
    if text and set(text.split()) & {'cent', 'cents'}:
        raise ValueError(
            f"aggregate money cannot use cents scale (unit_raw='{unit_raw}')")

    factor = _extract_scale_factor(unit_raw)
    if factor is None:
        return value

    to_millions = factor / 1e6
    if to_millions > 1 and value > 999:
        raise ValueError(
            f"{value} with '{unit_raw}' looks pre-scaled — "
            f"pass the number exactly as stated in source")
    return round(value * to_millions, 6)


def _scale_price_like_money(value: float, unit_raw: str) -> float:
    """§6.2: scale to face dollars. No pre-scaled guard."""
    factor = _extract_scale_factor(unit_raw)
    if factor is None:
        return value
    return round(value * factor, 6)


def _scale_count_absolute(value: float, unit_raw: str) -> float:
    """§6.3: scale to absolute quantity. Pre-scaled guard (billion+)."""
    factor = _extract_scale_factor(unit_raw)
    if factor is None:
        return value

    if factor > 1e6 and value > 999:
        raise ValueError(
            f"{value} with '{unit_raw}' looks pre-scaled — "
            f"pass the number exactly as stated in source")
    return round(value * factor, 6)


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
      4. Per-share override: per-share labels force 'usd' (never 'm_usd')
         via _is_per_share_label() token-pattern detection.
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

    # 4. Per-share override: always usd, never m_usd
    if canonical == 'm_usd' and _is_per_share_label(label_slug):
        return 'usd'

    # 5. Share-count override: share-count labels with scale words → count, not m_usd
    if canonical == 'm_usd' and _is_share_count_label(label_slug):
        return 'count'

    return canonical


def canonicalize_value(value: Optional[float], unit_raw: str, canonical_unit: str,
                       label_slug: str,
                       resolved_kind: Optional[str] = None,
                       resolved_money_mode: Optional[str] = None) -> Optional[float]:
    """
    Normalize a numeric value to canonical scale.

    V2 path (when resolved_kind is provided): scale according to resolved axes.
    V1 fallback (when resolved_kind is None): preserve legacy behavior.
    """
    if value is None:
        return None

    # ── V2 path: scale by resolved axes ──
    if resolved_kind is not None:
        if resolved_kind == 'money':
            if resolved_money_mode == 'price_like':
                return _scale_price_like_money(value, unit_raw)
            if resolved_money_mode == 'aggregate':
                return _scale_aggregate_money(value, unit_raw)
        if resolved_kind == 'count':
            return _scale_count_absolute(value, unit_raw)
        return value

    # ── V1 fallback path (preserve existing legacy behavior) ──

    # Share-count scaling: scale to absolute when raw unit is a scale word
    if canonical_unit == 'count' and _is_share_count_label(label_slug) and unit_raw:
        _, multiplier = _parse_numeric_with_scale(f"{value}{unit_raw}")
        if multiplier is not None:
            if multiplier > 1 and value > 999:
                raise ValueError(
                    f"{value} with '{unit_raw}' looks pre-scaled — "
                    f"pass the number exactly as stated in source"
                )
            return round(value * multiplier * 1e6, 6)

    if canonical_unit not in ('m_usd', 'usd'):
        return value

    # Per-share: no scaling
    if _is_per_share_label(label_slug):
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

def normalize_for_member_match(s: str) -> str:
    """Normalize for segment↔member matching: lowercase alphanum, strip XBRL tokens, trailing 's'."""
    n = re.sub(r'[^a-z0-9]', '', s.lower().replace('&', 'and'))
    n = n.replace('member', '').replace('segment', '')
    if n.endswith('s'):
        n = n[:-1]
    return n


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
    # V2 optional params
    unit_kind_hint: Optional[str] = None,
    money_mode_hint: Optional[str] = None,
    quote: Optional[str] = None,
    xbrl_qname: Optional[str] = None,
    existing_guidance_id: Optional[str] = None,
    existing_resolved_kind: Optional[str] = None,
    existing_resolved_money_mode: Optional[str] = None,
    existing_resolved_ratio_subtype: Optional[str] = None,
    existing_resolution_version: Optional[str] = None,
    resolution_mode: str = 'v1',
) -> dict:
    """
    Single entry point for all ID normalization.

    Supports resolution_mode:
      'v1':     V1 behavior only (UNIT_ALIASES + label overrides)
      'v2':     V2 resolver (3-axis evidence chain)
      'shadow': V1 as effective payload + nested V2 diff for observability

    Returns dict with:
        guidance_id, guidance_update_id, evhash16,
        label_slug, segment_slug,
        canonical_unit, canonical_low, canonical_mid, canonical_high,
        (V2/shadow): resolved_kind, resolved_money_mode,
                     resolved_ratio_subtype, resolution_version
        (shadow only): shadow_v2 nested diff block
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

    # 1. Validate hint enums if present
    if unit_kind_hint and unit_kind_hint not in VALID_UNIT_KIND_HINTS:
        raise ValueError(f"invalid unit_kind_hint: '{unit_kind_hint}'")
    if money_mode_hint and money_mode_hint not in VALID_MONEY_MODE_HINTS:
        raise ValueError(f"invalid money_mode_hint: '{money_mode_hint}'")

    # 2. Compute slugs
    label_slug = slug(label)
    segment_slug = slug(segment) if segment and segment.strip() else 'total'

    # ── V1 path ──────────────────────────────────────────────────────
    def _compute_v1():
        cu = canonicalize_unit(unit_raw, label_slug)
        cl = canonicalize_value(low, unit_raw, cu, label_slug)
        cm = canonicalize_value(mid, unit_raw, cu, label_slug)
        ch = canonicalize_value(high, unit_raw, cu, label_slug)
        if cm is None and cl is not None and ch is not None:
            cm = round((cl + ch) / 2, 6)
        return cu, cl, cm, ch

    # ── V2 path ──────────────────────────────────────────────────────
    def _compute_v2():
        # 3. Resolve axes
        rk = _resolve_kind(unit_kind_hint, unit_raw, xbrl_qname, label_slug)
        rmm = _resolve_money_mode(money_mode_hint, unit_raw, xbrl_qname, label_slug, rk)
        rrs = _resolve_ratio_subtype(unit_raw, quote) if rk == 'ratio' else 'unknown'

        # 4. Existing resolved-axis fallback (V2-written rows only)
        if rk == 'unknown' and existing_resolution_version and existing_resolution_version >= 'v2':
            if existing_guidance_id and existing_guidance_id == f'guidance:{label_slug}':
                if existing_resolved_kind and existing_resolved_kind != 'unknown':
                    rk = existing_resolved_kind
                    if rk == 'money' and existing_resolved_money_mode:
                        rmm = existing_resolved_money_mode
                    if rk == 'ratio' and existing_resolved_ratio_subtype:
                        rrs = existing_resolved_ratio_subtype

        # 5. Derive canonical_unit
        cu = _combine_resolved_unit(rk, rmm, rrs)

        # 6. Compute canonical values using resolved axes
        cl = canonicalize_value(low, unit_raw, cu, label_slug,
                                resolved_kind=rk, resolved_money_mode=rmm)
        cm = canonicalize_value(mid, unit_raw, cu, label_slug,
                                resolved_kind=rk, resolved_money_mode=rmm)
        ch = canonicalize_value(high, unit_raw, cu, label_slug,
                                resolved_kind=rk, resolved_money_mode=rmm)
        if cm is None and cl is not None and ch is not None:
            cm = round((cl + ch) / 2, 6)
        return cu, cl, cm, ch, rk, rmm, rrs

    # ── Mode dispatch ────────────────────────────────────────────────
    if resolution_mode == 'v1':
        canonical_unit, canonical_low, canonical_mid, canonical_high = _compute_v1()
        resolved_kind = None
        resolved_money_mode = None
        resolved_ratio_subtype = None
        shadow_v2 = None

    elif resolution_mode == 'v2':
        (canonical_unit, canonical_low, canonical_mid, canonical_high,
         resolved_kind, resolved_money_mode, resolved_ratio_subtype) = _compute_v2()
        shadow_v2 = None

    elif resolution_mode == 'shadow':
        # V1 is the effective write payload
        canonical_unit, canonical_low, canonical_mid, canonical_high = _compute_v1()
        resolved_kind = None
        resolved_money_mode = None
        resolved_ratio_subtype = None
        # V2 computed for diff only
        v2_cu, v2_cl, v2_cm, v2_ch, v2_rk, v2_rmm, v2_rrs = _compute_v2()
        shadow_v2 = {
            'canonical_unit': v2_cu,
            'canonical_low': v2_cl,
            'canonical_mid': v2_cm,
            'canonical_high': v2_ch,
            'resolved_kind': v2_rk,
            'resolved_money_mode': v2_rmm,
            'resolved_ratio_subtype': v2_rrs,
        }
    else:
        raise ValueError(f"resolution_mode must be 'v1', 'v2', or 'shadow', got '{resolution_mode}'")

    # 7. Evidence hash (from effective canonical_unit)
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

    # 8. Build result
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

    # 8a. V2 additive fields (writer-authoritative, not raw hints)
    if resolution_mode == 'v2' and resolved_kind is not None:
        result['resolved_kind'] = resolved_kind
        result['resolved_money_mode'] = resolved_money_mode
        result['resolved_ratio_subtype'] = resolved_ratio_subtype
        result['resolution_version'] = 'v2'

    # 8b. Shadow diff block (observability only, not written to graph)
    if shadow_v2 is not None:
        result['shadow_v2'] = shadow_v2

    return result
