"""
Post-Processing Pipeline for 8-K XBRL Fact Extraction

Handles:
- Value parsing (priority-based, deterministic)
- Period normalization and validation
- Qname validation against catalog
- Unit validation against catalog
- Status determination (COMMITTED, CANDIDATE_ONLY, REVIEW)
"""

import re
import logging
from typing import Optional, Set, List, Tuple
from datetime import datetime

from extraction_schema import (
    RawExtraction,
    ProcessedFact,
    ExtractionStatus,
    UNMATCHED
)

logger = logging.getLogger(__name__)

# Commit threshold - facts with confidence >= this get COMMITTED status
COMMIT_THRESHOLD = 0.90

# =============================================================================
# VALUE PARSING (Priority-Based)
# =============================================================================

MULTIPLIERS = {
    "trillion": 1e12, "t": 1e12,
    "billion": 1e9, "b": 1e9,
    "million": 1e6, "m": 1e6,
    "thousand": 1e3, "k": 1e3,
}


def parse_number_from_text(text: str, unit: str = None) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse the PRIMARY numeric value from extraction text using priority-based matching.

    This is the ONLY source of truth for numeric values.
    DO NOT trust any numeric output from the LLM.

    CRITICAL: Uses priority-based matching to avoid "first match" bugs.
    Example: "increased 10% to $2.75 billion"
      - Buggy (first match): returns 10
      - Correct (priority): returns 2,750,000,000

    Priority order:
    0. Parentheses-negative: "($2.3 billion)" → -2.3B (accounting convention)
    1. Currency + multiplier: "$2.75 billion" (strongest signal)
    2. Currency + large number: "$2,750,000,000"
    3. Multiplier alone: "2.75 billion"
    4. Percentage: "23.5%" (only if unit suggests ratio)
    5. Smart fallback: prefer decimals/commas, avoid year-like numbers

    Args:
        text: The extraction_text from LangExtract
        unit: Optional unit hint (for percentage handling)

    Returns:
        Tuple of (parsed_value, error_message)
        - (float, None) on success
        - (None, error_string) on failure
    """
    if not text:
        return None, "Empty extraction text"

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 0: Parentheses-negative (accounting convention for losses)
    # "($2.3 billion)" or "(2.3 billion)" → negative value
    # Note: (?![^)]*%) prevents matching percentages like (10%)
    # ═══════════════════════════════════════════════════════════════════════
    paren_match = re.search(
        r'\(\s*(?![^)]*%)\$?\s*([\d,]+\.?\d*)\s*(trillion|billion|million|thousand|[TBMK])?\s*\)',
        text, re.IGNORECASE
    )
    if paren_match:
        num_str = paren_match.group(1)
        multiplier = paren_match.group(2)
        if multiplier:
            return -_apply_multiplier(num_str, multiplier), None
        try:
            return -float(num_str.replace(",", "")), None
        except ValueError:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 1: Currency + multiplier (e.g., "$2.75 billion", "$450M")
    # ═══════════════════════════════════════════════════════════════════════
    match = re.search(
        r'\$\s*([\d,]+\.?\d*)\s*(trillion|billion|million|thousand|[TBMK])\b',
        text, re.IGNORECASE
    )
    if match:
        return _apply_multiplier(match.group(1), match.group(2)), None

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 2: Currency + large number (e.g., "$2,750,000,000")
    # ═══════════════════════════════════════════════════════════════════════
    for match in re.finditer(r'\$\s*([\d,]+\.?\d*)', text):
        try:
            value = float(match.group(1).replace(",", ""))
            if value >= 1000:  # Large enough to be a real financial value
                return value, None
        except ValueError:
            continue

    # Also handle small currency amounts (for EPS like "$4.80")
    match = re.search(r'\$\s*([\d,]+\.?\d*)', text)
    if match:
        try:
            return float(match.group(1).replace(",", "")), None
        except ValueError:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 3: Multiplier without currency (e.g., "2.75 billion revenue")
    # ═══════════════════════════════════════════════════════════════════════
    match = re.search(
        r'([\d,]+\.?\d*)\s*(trillion|billion|million|thousand)\b',
        text, re.IGNORECASE
    )
    if match:
        return _apply_multiplier(match.group(1), match.group(2)), None

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 4: Percentage (only for ratio/pure units)
    # ═══════════════════════════════════════════════════════════════════════
    if unit and unit.lower() in ("pure", "ratio", "percent"):
        match = re.search(r'([\d.]+)\s*%', text)
        if match:
            try:
                return float(match.group(1)) / 100, None
            except ValueError:
                pass

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 5: Smart fallback
    # Prefer numbers with decimals/commas over plain integers
    # Exclude year-like integers (1900-2100) when better candidates exist
    # REJECT if only number is a percentage and unit isn't ratio/pure
    # ═══════════════════════════════════════════════════════════════════════

    # Check if text only contains percentage - reject for non-ratio units
    pct_only = re.fullmatch(r'.*?(\d+\.?\d*)\s*%.*', text, re.DOTALL)
    if pct_only:
        # Count non-percentage numbers (handle comma percents like "1,200%")
        all_nums = re.findall(r'[\d,]+\.?\d*', text)
        pct_nums = re.findall(r'[\d,]+\.?\d*(?=\s*%)', text)
        non_pct_nums = [n for n in all_nums if n not in pct_nums]
        if not non_pct_nums:
            # Only percentage numbers exist
            if not unit or unit.lower() not in ("pure", "ratio", "percent"):
                return None, f"Only percentage found, but unit is {unit}"

    numbers = re.findall(r'[\d,]+\.?\d*', text)
    if numbers:
        decimal_numbers = []  # Has decimal point or comma
        non_year_integers = []  # Plain integers, not year-like
        year_integers = []  # Year-like integers (1900-2100)

        for n in numbers:
            cleaned = n.replace(",", "")
            if not cleaned or cleaned == ".":
                continue
            try:
                value = float(cleaned)
                if '.' in n or ',' in n:
                    decimal_numbers.append(value)
                else:
                    int_val = int(value)
                    if 1900 <= int_val <= 2100:
                        year_integers.append(value)
                    else:
                        non_year_integers.append(value)
            except ValueError:
                continue

        # Prefer decimal numbers (most likely to be financial values)
        if decimal_numbers:
            return max(decimal_numbers), None

        # Then non-year plain integers
        if non_year_integers:
            return max(non_year_integers), None

        # Last resort: year-like numbers
        if year_integers:
            return max(year_integers), None

    return None, f"Could not parse number from: {text[:50]}..."


def _apply_multiplier(num_str: str, multiplier: str) -> float:
    """Apply multiplier word/letter to number string."""
    num = float(num_str.replace(",", ""))
    m = multiplier.lower() if len(multiplier) > 1 else multiplier.lower()
    return num * MULTIPLIERS.get(m, 1)


# =============================================================================
# PERIOD VALIDATION & NORMALIZATION
# =============================================================================

# Regex patterns for period formats
INSTANT_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DURATION_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})→(\d{4}-\d{2}-\d{2})$')

# Arrow variants the LLM might produce (normalize to →)
# Note: Do NOT include '-' alone - it would match hyphens inside dates (YYYY-MM-DD)
ARROW_VARIANTS = ['-->', '->', '—>', '–>', ' - ', ' – ', ' — ', ' to ']


def normalize_period(period: str) -> Tuple[str, bool]:
    """
    Normalize period format.

    1. Normalize arrow variants to → (with whitespace stripping)
    2. If duration has start == end, convert to instant
       Example: "2025-06-30→2025-06-30" → "2025-06-30"

    Args:
        period: Period string from LLM output

    Returns:
        Tuple of (normalized_period, was_normalized)
    """
    if not period:
        return period, False

    normalized = period
    was_normalized = False

    # Normalize arrow variants to canonical →
    for variant in ARROW_VARIANTS:
        if variant in normalized:
            normalized = normalized.replace(variant, '→')
            was_normalized = True
            break  # Only one variant should match

    # Strip whitespace around the arrow (e.g., "2024-01-01 → 2024-12-31" → "2024-01-01→2024-12-31")
    if '→' in normalized:
        normalized = re.sub(r'\s*→\s*', '→', normalized).strip()

    # Check if it's a duration with start == end → convert to instant
    duration_match = DURATION_PATTERN.match(normalized)
    if duration_match:
        start, end = duration_match.groups()
        if start == end:
            # Convert to instant
            return start, True
        return normalized, was_normalized

    return normalized, was_normalized


def validate_period(period: str) -> bool:
    """
    Validate period format.

    Must match: "YYYY-MM-DD" (instant) OR "YYYY-MM-DD→YYYY-MM-DD" (duration)

    Args:
        period: Period string (should be normalized first)

    Returns:
        True if valid format, False otherwise
    """
    if not period:
        return False

    # Check instant format
    if INSTANT_PATTERN.match(period):
        try:
            datetime.strptime(period, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    # Check duration format
    duration_match = DURATION_PATTERN.match(period)
    if duration_match:
        start, end = duration_match.groups()
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            return start_dt <= end_dt  # Start must be <= end
        except ValueError:
            return False

    return False


# =============================================================================
# QNAME VALIDATION
# =============================================================================

def validate_qname(qname: str, valid_qnames: Set[str]) -> Tuple[str, bool]:
    """
    Validate qname against the set of valid qnames from the catalog.

    NO FUZZY MATCHING - invalid qnames become UNMATCHED.

    Args:
        qname: Qname to validate (or "UNMATCHED")
        valid_qnames: Set of valid qnames from the catalog

    Returns:
        Tuple of (validated_qname, was_valid)
        - If qname is valid or UNMATCHED: (qname, True)
        - If qname is invalid: ("UNMATCHED", False)
    """
    if not qname:
        return UNMATCHED, False

    if qname == UNMATCHED:
        return UNMATCHED, True

    if qname in valid_qnames:
        return qname, True

    # Invalid qname - log warning and return UNMATCHED
    logger.warning(f"Invalid qname '{qname}' not in catalog, setting to UNMATCHED")
    return UNMATCHED, False


# =============================================================================
# UNIT VALIDATION
# =============================================================================

def validate_unit(unit: str, valid_units: Set[str]) -> Tuple[str, bool]:
    """
    Validate unit against the set of valid units from the catalog.

    Args:
        unit: Unit string from LLM output
        valid_units: Set of valid units from the catalog

    Returns:
        Tuple of (unit, is_valid)
    """
    if not unit:
        return unit, False

    if unit in valid_units:
        return unit, True

    # Check case-insensitive match
    unit_lower = unit.lower()
    for valid_unit in valid_units:
        if valid_unit.lower() == unit_lower:
            return valid_unit, True  # Return the catalog's version

    logger.warning(f"Unit '{unit}' not in catalog units: {valid_units}")
    return unit, False


# =============================================================================
# STATUS DETERMINATION
# =============================================================================

def determine_status(
    concept_top1: str,
    confidence: float,
    value_parsed: Optional[float],
    period_valid: bool,
    qname_valid: bool,
    unit_valid: bool
) -> Tuple[ExtractionStatus, bool]:
    """
    Determine extraction status based on validation results.

    Args:
        concept_top1: Validated concept qname or UNMATCHED
        confidence: Confidence score from LLM
        value_parsed: Parsed numeric value (None if parse failed)
        period_valid: Whether period format is valid
        qname_valid: Whether concept_top1 was in valid set
        unit_valid: Whether unit was in valid set

    Returns:
        Tuple of (status, committed)
    """
    # Hard failures → REVIEW
    if value_parsed is None:
        return ExtractionStatus.REVIEW, False

    if not period_valid:
        return ExtractionStatus.REVIEW, False

    if not unit_valid:
        return ExtractionStatus.REVIEW, False

    # High confidence + valid concept → COMMITTED
    if (concept_top1 != UNMATCHED and
        qname_valid and
        confidence >= COMMIT_THRESHOLD):
        return ExtractionStatus.COMMITTED, True

    # Everything else → CANDIDATE_ONLY
    return ExtractionStatus.CANDIDATE_ONLY, False


# =============================================================================
# MAIN POSTPROCESSING FUNCTION
# =============================================================================

def postprocess(
    raw_extractions: List[RawExtraction],
    valid_qnames: Set[str],
    valid_units: Set[str]
) -> List[ProcessedFact]:
    """
    Post-process raw extractions from LangExtract.

    Applies:
    1. Qname validation (concept_top1, concept_top2)
    2. Period normalization and validation
    3. Unit validation
    4. Value parsing (deterministic, priority-based)
    5. Status determination

    Args:
        raw_extractions: List of RawExtraction from LangExtract
        valid_qnames: Set of valid concept qnames from catalog
        valid_units: Set of valid units from catalog

    Returns:
        List of ProcessedFact with all validations applied
    """
    processed = []

    for raw in raw_extractions:
        # 1. Validate concept_top1
        concept_top1, qname_valid = validate_qname(raw.concept_top1, valid_qnames)

        # 2. Validate concept_top2 (optional)
        concept_top2 = None
        if raw.concept_top2:
            concept_top2, _ = validate_qname(raw.concept_top2, valid_qnames)
            if concept_top2 == UNMATCHED:
                concept_top2 = None  # Invalid top2 becomes None, not UNMATCHED

        # 3. Normalize and validate period
        period, period_normalized = normalize_period(raw.matched_period)
        period_valid = validate_period(period)

        # 4. Validate unit
        unit, unit_valid = validate_unit(raw.matched_unit, valid_units)

        # 5. Parse value deterministically (use validated unit for percentage handling)
        value_parsed, parse_error = parse_number_from_text(
            raw.extraction_text,
            unit=unit  # Use validated unit, not raw
        )

        # 6. Determine status
        status, committed = determine_status(
            concept_top1=concept_top1,
            confidence=raw.confidence,
            value_parsed=value_parsed,
            period_valid=period_valid,
            qname_valid=qname_valid,
            unit_valid=unit_valid
        )

        # Create ProcessedFact
        fact = ProcessedFact(
            extraction_text=raw.extraction_text,
            char_start=raw.char_start,
            char_end=raw.char_end,
            concept_top1=concept_top1,
            concept_top2=concept_top2,
            matched_period=period,
            matched_unit=unit,
            confidence=raw.confidence,
            reasoning=raw.reasoning,
            matched_dimension=raw.matched_dimension,
            matched_member=raw.matched_member,
            value_parsed=value_parsed,
            committed=committed,
            status=status,
            qname_valid=qname_valid,
            unit_valid=unit_valid,
            period_normalized=period_normalized,
            parse_error=parse_error
        )

        processed.append(fact)

        # Log status
        if status == ExtractionStatus.REVIEW:
            logger.warning(
                f"REVIEW needed: {raw.extraction_text[:50]}... "
                f"(parse_error={parse_error}, period_valid={period_valid})"
            )
        elif status == ExtractionStatus.COMMITTED:
            logger.info(
                f"COMMITTED: {concept_top1} = {value_parsed} "
                f"(confidence={raw.confidence:.2f})"
            )

    return processed
