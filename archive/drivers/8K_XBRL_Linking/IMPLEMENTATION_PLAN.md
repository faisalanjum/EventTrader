# LangExtract 8-K → XBRL Fact Extraction & Linking

## Final Implementation Plan

---

## Executive Summary

**Goal**: Extract financial facts from SEC 8-K filings using LangExtract and link them to XBRL concepts in Neo4j.

**Approach**: Additional Context + Post-Processing (no LangExtract modifications)

**Key Design Decisions**:
- Single extraction class (`financial_fact`)
- Top-2 candidate matching (`concept_top1`, `concept_top2`)
- Deterministic value parsing (don't trust LLM for numbers)
- Commit threshold ≥ 0.90
- No fuzzy matching (silent wrong links are worse than no links)
- Three statuses: `COMMITTED`, `CANDIDATE_ONLY`, `REVIEW`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           8-K FILING TEXT                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         XBRL CATALOG GENERATOR                          │
│                         (xbrl_catalog.py)                               │
│                                                                         │
│  • Fetches company's XBRL schema from Neo4j                            │
│  • Generates LLM-friendly additional_context                           │
│  • Includes qnames, labels, historical values, dimensions              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           LANGEXTRACT                                   │
│                                                                         │
│  lx.extract(                                                           │
│      text_or_documents = 8k_text,                                      │
│      prompt_description = PROMPT,                                      │
│      examples = 6_EXAMPLES,                                            │
│      additional_context = xbrl_catalog,  ← Schema injection            │
│      model_id = "gemini-2.5-flash",                                    │
│      extraction_passes = 1,                                            │
│      temperature = 0.1                                                 │
│  )                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       POST-PROCESSING PIPELINE                          │
│                                                                         │
│  1. Validate qnames against Neo4j                                      │
│  2. Parse values deterministically (value_parsed)                      │
│  3. Validate period format                                             │
│  4. Compute commit status                                              │
│  5. Output structured results                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         NEO4J LINKING                                   │
│                                                                         │
│  COMMITTED → Auto-link to XBRL Concept nodes                           │
│  CANDIDATE_ONLY → Store with flag for human review                     │
│  REVIEW → Requires manual intervention                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 1: Extraction Schema

### 1.1 Single Extraction Class

```python
extraction_class: "financial_fact"
```

No separate classes for segmented vs non-segmented. Segmentation is indicated by presence of `matched_dimension` and `matched_member` fields.

### 1.2 LLM-Provided Attributes

| Attribute          | Type          | Required | Description                                                  |
|--------------------|---------------|----------|--------------------------------------------------------------|
| `concept_top1`     | string        | Yes      | Best match qname OR `"UNMATCHED"`                            |
| `concept_top2`     | string \| null| **No**   | Second best qname OR `null` (optional)                       |
| `matched_period`   | string        | Yes      | `"YYYY-MM-DD"` (instant) or `"YYYY-MM-DD→YYYY-MM-DD"` (duration) |
| `matched_unit`     | string        | Yes      | `"USD"`, `"shares"`, `"pure"`, `"USD/share"`                 |
| `confidence`       | float         | Yes      | 0.0 to 1.0                                                   |
| `reasoning`        | string        | Yes      | Brief explanation (1-2 sentences)                            |

### 1.3 Optional Attributes (when segmented)

| Attribute           | Type   | When to Include         |
|---------------------|--------|-------------------------|
| `matched_dimension` | string | When fact is segmented  |
| `matched_member`    | string | When fact is segmented  |

### 1.4 Post-Processing Adds

| Field          | Type          | Computed By                                               |
|----------------|---------------|-----------------------------------------------------------|
| `value_parsed` | number \| null | Deterministic parsing of `extraction_text`               |
| `committed`    | boolean       | `concept_top1 != "UNMATCHED" AND confidence >= 0.90`     |
| `status`       | string        | `"COMMITTED"`, `"CANDIDATE_ONLY"`, or `"REVIEW"`         |

---

## STEP 2: Prompt Description

**Note**: This is the ONLY place where output instructions live. The XBRL catalog
contains pure data only - no instructions, no warnings, no format specifications.

```text
ROLE:
You are extracting financial facts from SEC 8-K filings and matching them
to XBRL concepts from the company's XBRL catalog provided in the context.

The context contains XBRL reference data wrapped in <<<BEGIN_XBRL_REFERENCE_DATA>>>
and <<<END_XBRL_REFERENCE_DATA>>> markers. Use this data to match your extractions.

EXTRACTION RULES:
• Extract EXACT text spans from the document (do not paraphrase)
• Extract all quantitative financial metrics mentioned
• Include the numeric value and any period context in the extraction

MATCHING RULES:
• Match each extraction to a concept qname from the XBRL CATALOG in the context
• Use EXACT qnames as written in the catalog - do not modify or invent qnames
• For segmented data (by business segment, geography, etc.), include matched_dimension and matched_member
• If no concept in the catalog matches, use "UNMATCHED" for concept_top1

VALID VALUES FOR concept_top1 / concept_top2:
• Any exact qname from the CONCEPTS list in the catalog (e.g., "us-gaap:NetIncomeLoss")
• "UNMATCHED" - use this when no concept in the catalog applies

CONFIDENCE GUIDELINES:

• CONFIDENT (0.90+): One clear, unambiguous match
  → concept_top1 = qname from catalog
  → concept_top2 = null (omit)

• AMBIGUOUS (0.50-0.85): Two plausible matches, unclear which is correct
  → concept_top1 = best match qname
  → concept_top2 = second best qname

• NOT CONFIDENT (<0.50): No clear match or very uncertain
  → concept_top1 = "UNMATCHED"
  → concept_top2 = best guess qname (or null if no reasonable guess)

Use historical values in the catalog as a HINT for confidence, but do not reject
based on magnitude differences alone (step-changes like acquisitions are legitimate).

OUTPUT FORMAT:
• concept_top1: Exact qname from catalog OR "UNMATCHED"
• concept_top2: Second best qname OR null (OPTIONAL - omit if confident)
• matched_period: "YYYY-MM-DD" (instant) or "YYYY-MM-DD→YYYY-MM-DD" (duration)
• matched_unit: Must be one of the units listed in the catalog's UNITS section
• matched_dimension: Exact dimension qname from catalog (only if segmented)
• matched_member: Exact member qname from catalog (only if segmented)
• confidence: Float 0.0-1.0
• reasoning: Brief explanation (1-2 sentences)
```

---

## STEP 3: Few-Shot Examples (6 Examples)

### 3.1 Example 1: Confident Match (High Confidence, No Ambiguity)

```python
ExampleData(
    text="Intercontinental Exchange reported net income of $2.75 billion for fiscal year 2024.",
    extractions=[
        Extraction(
            extraction_class="financial_fact",
            extraction_text="net income of $2.75 billion for fiscal year 2024",
            attributes={
                "concept_top1": "us-gaap:NetIncomeLoss",
                "concept_top2": None,
                "matched_period": "2024-01-01→2024-12-31",
                "matched_unit": "USD",
                "confidence": 0.95,
                "reasoning": "Explicit net income for full year, exact match in catalog with consistent historical value"
            }
        )
    ]
)
```

### 3.2 Example 2: Confident Match (Segmented Data)

```python
ExampleData(
    text="The Exchanges segment generated revenues of $4.1 billion for the full year.",
    extractions=[
        Extraction(
            extraction_class="financial_fact",
            extraction_text="Exchanges segment generated revenues of $4.1 billion",
            attributes={
                "concept_top1": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                "concept_top2": None,
                "matched_period": "2024-01-01→2024-12-31",
                "matched_unit": "USD",
                "matched_dimension": "us-gaap:StatementBusinessSegmentsAxis",
                "matched_member": "ice:ExchangesSegmentMember",
                "confidence": 0.92,
                "reasoning": "Clear segment revenue with explicit segment name matching catalog dimension/member"
            }
        )
    ]
)
```

### 3.3 Example 3: Ambiguous Match (Two Plausible Concepts)

```python
ExampleData(
    text="Operating costs totaled $1.8 billion in Q2, driven by technology and personnel expenses.",
    extractions=[
        Extraction(
            extraction_class="financial_fact",
            extraction_text="Operating costs totaled $1.8 billion in Q2",
            attributes={
                "concept_top1": "us-gaap:OperatingExpenses",
                "concept_top2": "us-gaap:CostsAndExpenses",
                "matched_period": "2025-04-01→2025-06-30",
                "matched_unit": "USD",
                "confidence": 0.70,
                "reasoning": "Could be OperatingExpenses or broader CostsAndExpenses - both plausible from context"
            }
        )
    ]
)
```

### 3.4 Example 4: Ambiguous Match (Segment-Specific Term)

```python
ExampleData(
    text="Transaction-based revenue grew to $450 million, reflecting increased trading activity.",
    extractions=[
        Extraction(
            extraction_class="financial_fact",
            extraction_text="Transaction-based revenue grew to $450 million",
            attributes={
                "concept_top1": "UNMATCHED",
                "concept_top2": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                "matched_period": "2025-04-01→2025-06-30",
                "matched_unit": "USD",
                "confidence": 0.45,
                "reasoning": "Transaction-based revenue may be segment-specific, unclear if it maps to general revenue concept"
            }
        )
    ]
)
```

### 3.5 Example 5: Confident Match (Per-Share Value)

```python
ExampleData(
    text="Diluted earnings per share were $4.80 for 2024, compared to $4.28 in the prior year.",
    extractions=[
        Extraction(
            extraction_class="financial_fact",
            extraction_text="Diluted earnings per share were $4.80 for 2024",
            attributes={
                "concept_top1": "us-gaap:EarningsPerShareDiluted",
                "concept_top2": None,
                "matched_period": "2024-01-01→2024-12-31",
                "matched_unit": "USD/share",
                "confidence": 0.95,
                "reasoning": "Explicit diluted EPS, matches catalog value exactly"
            }
        )
    ]
)
```

### 3.6 Example 6: Not Confident (Non-Financial / No Match)

```python
ExampleData(
    text="The company added 250 new employees during the quarter, bringing total headcount to 12,500.",
    extractions=[
        Extraction(
            extraction_class="financial_fact",
            extraction_text="total headcount to 12,500",
            attributes={
                "concept_top1": "UNMATCHED",
                "concept_top2": None,
                "matched_period": "2025-06-30",
                "matched_unit": "pure",
                "confidence": 0.30,
                "reasoning": "Employee headcount is operational data, no matching XBRL financial concept in catalog"
            }
        )
    ]
)
```

---

## STEP 4: LangExtract Configuration

```python
import langextract as lx

result = lx.extract(
    text_or_documents = eight_k_text,
    prompt_description = PROMPT_DESCRIPTION,
    examples = EXAMPLES,  # 6 examples above
    additional_context = xbrl_catalog.to_llm_context(),  # From xbrl_catalog.py
    model_id = "gemini-2.5-flash",
    extraction_passes = 1,              # Precision-first; increase if recall is low
    max_workers = 10,
    max_char_buffer = 2000,
    temperature = 0.1,                  # Low temp = less hallucination
    use_schema_constraints = True
)
```

### Configuration Rationale

| Parameter             | Value               | Rationale                                        |
|-----------------------|---------------------|--------------------------------------------------|
| `extraction_passes`   | 1                   | Precision-first; add passes later if recall low |
| `temperature`         | 0.1                 | Low variance, reduce hallucination               |
| `max_char_buffer`     | 2000                | Standard context window                          |
| `use_schema_constraints` | True             | Enforce output structure                         |

---

## STEP 5: Post-Processing Pipeline

### 5.1 Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FOR EACH EXTRACTION FROM LANGEXTRACT                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5.1.1  VALIDATE concept_top1                                                   │
│                                                                                 │
│  IF concept_top1 in valid_qnames_set → keep                                     │
│  ELIF concept_top1 == "UNMATCHED" → keep                                        │
│  ELSE → log_warning("Invalid qname: {qname}"), set to "UNMATCHED"               │
│                                                                                 │
│  ⚠️  NO FUZZY MATCHING - invalid qnames become UNMATCHED                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5.1.2  VALIDATE concept_top2                                                   │
│                                                                                 │
│  IF concept_top2 is None → keep as None                                         │
│  ELIF concept_top2 in valid_qnames_set → keep                                   │
│  ELSE → log_warning("Invalid qname: {qname}"), set to None                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5.1.3  PARSE VALUE DETERMINISTICALLY                                           │
│                                                                                 │
│  value_parsed = parse_number_from_text(extraction_text)                         │
│                                                                                 │
│  ⚠️  THIS IS THE ONLY TRUSTED NUMERIC VALUE                                     │
│  ⚠️  DO NOT USE ANY VALUE FROM LLM OUTPUT                                       │
│                                                                                 │
│  Examples:                                                                      │
│  • "$24.4 billion" → 24400000000                                                │
│  • "$2.75 billion" → 2750000000                                                 │
│  • "$4.80" → 4.80                                                               │
│  • "$450 million" → 450000000                                                   │
│  • "12,500" → 12500                                                             │
│  • "23.5%" → 0.235 (if unit is "pure")                                          │
│                                                                                 │
│  IF parse fails → value_parsed = None, flag for REVIEW                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5.1.4  VALIDATE & NORMALIZE PERIOD FORMAT                                      │
│                                                                                 │
│  Must match: "YYYY-MM-DD" OR "YYYY-MM-DD→YYYY-MM-DD"                            │
│                                                                                 │
│  NORMALIZE ARROWS: "->" or " to " → "→" (models may output different formats)   │
│  Example: "2024-01-01 to 2024-12-31" → "2024-01-01→2024-12-31"                  │
│                                                                                 │
│  NORMALIZE ZERO-LENGTH: If duration has start == end, convert to instant        │
│  Example: "2025-06-30→2025-06-30" → "2025-06-30"                                │
│                                                                                 │
│  IF invalid format after normalization → flag for REVIEW                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5.1.5  VALIDATE UNIT                                                           │
│                                                                                 │
│  Valid units: From catalog's UNITS section (company-specific, e.g., USD, EUR)   │
│                                                                                 │
│  IF matched_unit in catalog_units → keep                                        │
│  ELIF matched_unit not in catalog_units → status = "REVIEW" (unknown unit)      │
│  Post-processing maps canonical → Neo4j taxonomy (USD → iso4217:USD, etc.)      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5.1.6  DETERMINE STATUS                                                        │
│                                                                                 │
│  COMMIT_THRESHOLD = 0.90                                                        │
│                                                                                 │
│  IF any hard failure (parse error, invalid period):                             │
│      status = "REVIEW"                                                          │
│      committed = False                                                          │
│                                                                                 │
│  ELIF concept_top1 != "UNMATCHED" AND confidence >= COMMIT_THRESHOLD:           │
│      status = "COMMITTED"                                                       │
│      committed = True                                                           │
│                                                                                 │
│  ELSE:                                                                          │
│      status = "CANDIDATE_ONLY"                                                  │
│      committed = False                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Value Parsing Function (Priority-Based)

**CRITICAL**: The parser uses **priority-based matching**, not "first match".
This prevents the bug where "increased 10% to $2.75 billion" would return 10 instead of 2.75B.

**Priority Order**:
1. Parentheses negative: `($2.3 billion)` → -2300000000 (accounting convention)
2. Currency + multiplier: `$2.75 billion`, `$450M` (strongest positive signal)
3. Currency + large number: `$2,750,000,000`
4. Multiplier alone: `2.75 billion`
5. Percentage: `23.5%` (only if unit is "pure")
6. Largest number found (fallback)

```python
import re
from typing import Optional

MULTIPLIERS = {
    "trillion": 1e12, "t": 1e12,
    "billion": 1e9, "b": 1e9,
    "million": 1e6, "m": 1e6,
    "thousand": 1e3, "k": 1e3,
}


def parse_number_from_text(text: str, unit: str = None) -> Optional[float]:
    """
    Parse the PRIMARY numeric value from extraction text using priority-based matching.

    This is the ONLY source of truth for numeric values.
    DO NOT trust any numeric output from the LLM.

    CRITICAL: Uses priority-based matching to avoid "first match" bugs.
    Example: "increased 10% to $2.75 billion"
      - Buggy (first match): returns 10 ❌
      - Correct (priority): returns 2,750,000,000 ✓

    Priority order:
    1. Parentheses negative: "($2.3 billion)" → -2300000000
    2. Currency + multiplier: "$2.75 billion" (strongest signal)
    3. Currency + large number: "$2,750,000,000"
    4. Multiplier alone: "2.75 billion"
    5. Percentage: "23.5%" (only if unit is "pure")
    6. Largest number found (fallback)

    Args:
        text: The extraction_text from LangExtract
        unit: Optional unit hint (for percentage handling)

    Returns:
        Parsed float value, or None if unparseable

    Examples:
        "($2.3 billion)" → -2300000000.0 (negative!)
        "(loss of €450M)" → -450000000.0 (negative, euro)
        "increased 10% to $2.75 billion" → 2750000000.0 (not 10!)
        "€2.3B in European sales" → 2300000000.0 (euro)
        "GBP 500 million" → 500000000.0 (ISO code)
        "$24.4 billion" → 24400000000.0
        "$4.80" → 4.80
        "€3.50 per share" → 3.50 (euro EPS)
        "12,500" → 12500.0
        "23.5%" (unit="pure") → 0.235
    """
    if not text:
        return None

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 0: Parentheses negative (accounting convention)
    # "($2.3 billion)", "(loss of €450M)", "(2.3 billion)" → negative value
    # Strategy: Extract content inside parens, parse normally, negate result
    # ═══════════════════════════════════════════════════════════════════════
    paren_match = re.search(r'\(([^)]+)\)', text)
    if paren_match:
        inner_text = paren_match.group(1)
        # Currency pattern: $ € £ or ISO codes
        curr = r'(?:[$€£]|(?:USD|EUR|GBP|JPY|CAD|CHF)\s*)'
        # Look for currency + multiplier inside parens
        inner_currency = re.search(
            curr + r'([\d,]+\.?\d*)\s*(trillion|billion|million|thousand|[TBMK])?\b',
            inner_text, re.IGNORECASE
        )
        if inner_currency:
            num_str = inner_currency.group(1)
            mult = inner_currency.group(2)
            if mult:
                return -_apply_multiplier(num_str, mult)
            else:
                return -float(num_str.replace(",", ""))
        # Also check for number + multiplier without currency
        inner_mult = re.search(
            r'([\d,]+\.?\d*)\s*(trillion|billion|million|thousand|[TBMK])\b',
            inner_text, re.IGNORECASE
        )
        if inner_mult:
            return -_apply_multiplier(inner_mult.group(1), inner_mult.group(2))

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 1: Currency + multiplier (e.g., "$2.75 billion", "€450M", "GBP 2.3B")
    # Supports: $ € £ and ISO codes (USD, EUR, GBP, etc.)
    # ═══════════════════════════════════════════════════════════════════════
    # Currency symbols: $ € £ or ISO codes like USD/EUR/GBP before the number
    currency_pattern = r'(?:[$€£]|(?:USD|EUR|GBP|JPY|CAD|CHF)\s*)'
    match = re.search(
        currency_pattern + r'([\d,]+\.?\d*)\s*(trillion|billion|million|thousand|[TBMK])\b',
        text, re.IGNORECASE
    )
    if match:
        return _apply_multiplier(match.group(1), match.group(2))

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 2: Currency + large number (e.g., "$2,750,000,000", "€500,000")
    # No multiplier word, but has currency symbol/code and large number
    # ═══════════════════════════════════════════════════════════════════════
    for match in re.finditer(currency_pattern + r'([\d,]+\.?\d*)', text, re.IGNORECASE):
        value = float(match.group(1).replace(",", ""))
        if value >= 1000:  # Large enough to be a real financial value
            return value

    # Also handle small currency amounts (for EPS like "$4.80", "€3.50")
    match = re.search(currency_pattern + r'([\d,]+\.?\d*)', text, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", ""))

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 3: Multiplier without currency (e.g., "2.75 billion revenue")
    # ═══════════════════════════════════════════════════════════════════════
    match = re.search(
        r'([\d,]+\.?\d*)\s*(trillion|billion|million|thousand)\b',
        text, re.IGNORECASE
    )
    if match:
        return _apply_multiplier(match.group(1), match.group(2))

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 4: Percentage (only for "pure" unit)
    # ═══════════════════════════════════════════════════════════════════════
    if unit == "pure":
        match = re.search(r'([\d.]+)\s*%', text)
        if match:
            return float(match.group(1)) / 100

    # ═══════════════════════════════════════════════════════════════════════
    # PRIORITY 5: Fallback - largest number found
    # This catches cases like "headcount to 12,500"
    # ═══════════════════════════════════════════════════════════════════════
    numbers = re.findall(r'[\d,]+\.?\d*', text)
    if numbers:
        values = []
        for n in numbers:
            cleaned = n.replace(",", "")
            if cleaned and cleaned != ".":
                try:
                    values.append(float(cleaned))
                except ValueError:
                    continue
        if values:
            return max(values)  # Return largest, most likely the actual value

    return None


def _apply_multiplier(num_str: str, multiplier: str) -> float:
    """Apply multiplier word/letter to number string."""
    num = float(num_str.replace(",", ""))
    m = multiplier.lower() if len(multiplier) > 1 else multiplier.lower()
    return num * MULTIPLIERS.get(m, 1)
```

**Test Cases**:

| Input | Expected | Notes |
|-------|----------|-------|
| "($2.3 billion)" | -2,300,000,000 | Parentheses = negative |
| "(loss of $450M)" | -450,000,000 | Parentheses + letter multiplier |
| "(€150M loss)" | -150,000,000 | Parentheses + euro symbol |
| "increased 10% to $2.75 billion" | 2,750,000,000 | Priority: $ + multiplier > % |
| "Revenue grew 15% to $6.5 billion" | 6,500,000,000 | Priority: $ + multiplier > % |
| "$450M in revenue" | 450,000,000 | Letter multiplier (M) |
| "€2.3B in European sales" | 2,300,000,000 | Euro + letter multiplier |
| "GBP 500 million" | 500,000,000 | ISO code + word multiplier |
| "EUR 1.2 billion revenue" | 1,200,000,000 | ISO code + word multiplier |
| "net income of $2.75 billion" | 2,750,000,000 | Word multiplier |
| "Diluted EPS of $4.80" | 4.80 | Small currency (no multiplier) |
| "€3.50 per share" | 3.50 | Euro small amount |
| "total headcount to 12,500" | 12,500 | Fallback to largest number |
| "margin of 23.5%" (unit=pure) | 0.235 | Percentage conversion |

### 5.3 Status Determination Logic

```python
COMMIT_THRESHOLD = 0.90

def determine_status(
    concept_top1: str,
    confidence: float,
    value_parsed: Optional[float],
    period_valid: bool,
    unit_valid: bool
) -> tuple[str, bool]:
    """
    Determine extraction status based on validation results.

    Args:
        concept_top1: Matched concept qname or "UNMATCHED"
        confidence: LLM confidence score (0.0-1.0)
        value_parsed: Parsed numeric value (None if parse failed)
        period_valid: Whether period format is valid after normalization
        unit_valid: Whether unit is in catalog's UNITS section

    Returns:
        (status, committed) tuple
    """
    # Hard failures → REVIEW
    if value_parsed is None or not period_valid or not unit_valid:
        return ("REVIEW", False)

    # High confidence + valid concept → COMMITTED
    if concept_top1 != "UNMATCHED" and confidence >= COMMIT_THRESHOLD:
        return ("COMMITTED", True)

    # Everything else → CANDIDATE_ONLY
    return ("CANDIDATE_ONLY", False)
```

---

## STEP 6: Output Structure

### Final Output Schema

```json
{
    // From LangExtract
    "extraction_text": "net income of $2.75 billion for fiscal year 2024",
    "char_start": 45,
    "char_end": 92,
    "concept_top1": "us-gaap:NetIncomeLoss",
    "concept_top2": null,
    "matched_period": "2024-01-01→2024-12-31",
    "matched_unit": "USD",
    "confidence": 0.95,
    "reasoning": "Explicit net income, matches catalog with consistent history",

    // Optional (when segmented)
    "matched_dimension": null,
    "matched_member": null,

    // Added by post-processing
    "value_parsed": 2750000000,
    "committed": true,
    "status": "COMMITTED"
}
```

### Status Definitions

| Status           | Meaning                                  | Action                     |
|------------------|------------------------------------------|----------------------------|
| `COMMITTED`      | High confidence (≥0.90) + valid qname    | Auto-link to Neo4j         |
| `CANDIDATE_ONLY` | Low confidence OR UNMATCHED concept_top1 | Store but flag for review  |
| `REVIEW`         | Parse failure / invalid period format    | Manual review required     |

### Confidence Bands Summary

| Band             | Range       | concept_top1    | concept_top2     | Status           |
|------------------|-------------|-----------------|------------------|------------------|
| **Confident**    | 0.90 - 1.00 | Valid qname     | null (omitted)   | `COMMITTED`      |
| **Ambiguous**    | 0.50 - 0.85 | Valid qname     | Valid qname      | `CANDIDATE_ONLY` |
| **Not Confident**| 0.00 - 0.50 | `"UNMATCHED"`   | Best guess/null  | `CANDIDATE_ONLY` |

---

## STEP 7: Logging

| Event                    | Level | Log Data                              |
|--------------------------|-------|---------------------------------------|
| Extraction complete      | INFO  | company, filing_id, count, duration   |
| Invalid qname detected   | WARN  | qname, extraction_text                |
| Parse failure            | WARN  | extraction_text, error                |
| Status assigned          | DEBUG | extraction_id, status, confidence     |
| Neo4j link created       | INFO  | extraction_id, concept_qname          |

---

## STEP 8: Implementation Checklist

### Already Complete

- [x] XBRL Catalog Generator (`xbrl_catalog.py`)
  - Fetches company XBRL schema from Neo4j
  - Generates LLM-friendly `to_llm_context()` output
  - Includes qnames, labels, historical values, dimensions/members

### To Implement

- [ ] **1. Create Extraction Schema** (`extraction_schema.py`)
  - Define `FinancialFact` dataclass matching schema above
  - Define `ExtractionResult` wrapper with metadata

- [ ] **2. Write Prompt + Examples** (`extraction_config.py`)
  - `PROMPT_DESCRIPTION` constant
  - `EXAMPLES` list with 6 ExampleData objects

- [ ] **3. Build LangExtract Wrapper** (`extractor.py`)
  - `extract_facts(text: str, cik: str) -> List[RawExtraction]`
  - Handles LangExtract call with catalog injection

- [ ] **4. Build Post-Processing Pipeline** (`postprocessor.py`)
  - `validate_qname(qname: str, valid_set: Set[str]) -> str`
  - `parse_number_from_text(text: str, unit: str) -> Optional[float]`
  - `normalize_period(period: str) -> str` - normalizes arrows (`->`, ` to ` → `→`), converts `start→start` to instant
  - `validate_period(period: str) -> bool`
  - `validate_unit(unit: str, catalog_units: Set[str]) -> str` - validates against catalog's UNITS section
  - `map_unit_to_neo4j(unit: str) -> str` - maps `USD` → `iso4217:USD` etc.
  - `determine_status(...) -> Tuple[str, bool]`
  - `postprocess(raw: List[RawExtraction], valid_qnames: Set[str], catalog_units: Set[str]) -> List[ProcessedFact]`

- [ ] **5. Test & Iterate**
  - Run on 3-5 real 8-K filings from `sample_data/`
  - Check precision (no wrong links)
  - Check recall (not missing obvious facts)
  - Tune prompt/examples based on errors

---

## Summary: What We Use vs. What We Don't

### What We Use

| Component           | Value                                                        |
|---------------------|--------------------------------------------------------------|
| Extraction class    | Single: `financial_fact`                                     |
| Concept matching    | Top-2: `concept_top1`, `concept_top2` (top2 is optional)     |
| Value handling      | LLM extracts text → we parse `value_parsed` deterministically|
| Unit vocabulary     | Company-specific from catalog UNITS section (post-process maps to Neo4j) |
| Period normalization| Normalize arrows (`->`, `to` → `→`), `start→start` → instant |
| Commit threshold    | 0.90                                                         |
| Confidence bands    | Confident (0.90+), Ambiguous (0.50-0.85), Not Confident (<0.50) |
| extraction_passes   | 1 (increase if recall is low)                                |
| Statuses            | `COMMITTED`, `CANDIDATE_ONLY`, `REVIEW`                      |

### What We Don't Use

| Removed                       | Reason                               |
|-------------------------------|--------------------------------------|
| Multiple extraction classes   | Unnecessary complexity               |
| Fuzzy qname matching          | Creates silent wrong links           |
| LLM numeric values            | Unreliable; parse deterministically  |
| Magnitude-based rejection     | Legitimate step-changes exist        |
| CORRECTED status              | No fuzzy matching = no corrections   |
| Multi-pass extraction         | Start with 1, add if needed          |
| Required concept_top2         | Only needed when ambiguous           |

---

## Appendix A: XBRL Catalog Format Reference

### Design Principle: PURE DATA, NO INSTRUCTIONS

The catalog contains **only reference data** - no output instructions, no formatting rules, no warnings.
All instructions live in `prompt_description` (single source of truth).

**Why?**
- Avoids prompt↔context instruction conflicts
- Reduces token waste (no duplicate instructions)
- Clear separation: catalog = data, prompt = rules
- Easier maintenance (update instructions in one place)

### Catalog Format

The `xbrl_catalog.to_llm_context()` generates approximately 15,000 characters (~3,800 tokens):

```
<<<BEGIN_XBRL_REFERENCE_DATA>>>
════════════════════════════════════════════════════════════════════════
COMPANY: INTERCONTINENTAL EXCHANGE INC (ICE)
CIK: 0001571949 | Industry: FinancialDataAndStockExchanges | Sector: FinancialServices
════════════════════════════════════════════════════════════════════════

LEGEND:
• qname = unique concept identifier (e.g., us-gaap:Revenues)
• label = human-readable name
• balance: credit = ↑equity/liability | debit = ↑assets/expenses

────────────────────────────────────────────────────────────────────────
CONCEPTS (top 100 by frequency)
────────────────────────────────────────────────────────────────────────
── TOP CONCEPTS (with history for magnitude validation) ──
us-gaap:NetIncomeLoss | Net Income (Loss) | credit
  History: $700M (10-Q, 2025-04-01→2025-06-30), $2.7B (10-K, 2024-01-01→2024-12-31)
us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | Revenue | credit
  History: $3.3B (10-Q, 2025-04-01→2025-06-30), $6.5B (10-K, 2024-01-01→2024-12-31)
...

── ADDITIONAL CONCEPTS (70 more) ──
us-gaap:InterestExpense | Interest Expense | debit
...

────────────────────────────────────────────────────────────────────────
PERIODS (45 unique)
────────────────────────────────────────────────────────────────────────
Duration: 2025-04-01→2025-06-30, 2025-01-01→2025-06-30, 2024-01-01→2024-12-31
Instant: 2025-06-30, 2025-03-31, 2024-12-31, 2024-09-30

────────────────────────────────────────────────────────────────────────
UNITS (5 types)
────────────────────────────────────────────────────────────────────────
USD | shares | pure | USD/share

────────────────────────────────────────────────────────────────────────
DIMENSIONS → MEMBERS (active in these filings)
────────────────────────────────────────────────────────────────────────
us-gaap:StatementBusinessSegmentsAxis:
  → ice:ExchangesSegmentMember
  → ice:FixedIncomeAndDataServicesMember
  → ice:MortgageTechnologyMember
...

════════════════════════════════════════════════════════════════════════
TOTALS: 12,450 facts | 500 concepts | 45 periods | 5 units | 45 members
════════════════════════════════════════════════════════════════════════
<<<END_XBRL_REFERENCE_DATA>>>
```

### Key Format Details

- **Delimiters**: `<<<BEGIN_XBRL_REFERENCE_DATA>>>` / `<<<END_XBRL_REFERENCE_DATA>>>` mark boundaries
- **History format**: `$value (form, period)` e.g., `$700M (10-Q, 2025-04-01→2025-06-30)`
- **Period format**: Duration uses `start→end`, instant uses single date; LLM may output `->` or `to` (normalize in post-processing)
- **Units**: Company-specific from XBRL data (e.g., `USD | EUR | shares | pure | USD/share`), not a fixed global list
- **Pure data**: No instructions, no UNMATCHED fallback (that's defined in prompt only)

---

## Appendix B: Why These Design Decisions?

### Why Top-2 Candidates?
Single-match forces a precision/recall tradeoff. With top-2:
- Confident extractions → `concept_top1` only, auto-commit
- Ambiguous extractions → both candidates, human chooses
- No match → `UNMATCHED`, preserved for manual review

### Why No Fuzzy Matching?
Fuzzy matching (e.g., difflib) creates **silent wrong links**. If the LLM outputs `us-gaap:Revenue` (invalid) and we fuzzy-match to `us-gaap:Revenues` (valid), we've created a link that looks correct but might be semantically wrong. Better to flag as `UNMATCHED` and let humans decide.

### Why Deterministic Value Parsing?
LLMs are unreliable at numeric parsing. "$24.4 billion" might become:
- 24.4 (forgot multiplier)
- 2440000000 (wrong multiplier)
- 24400000000 (correct)

By parsing `extraction_text` ourselves, we ensure consistent, auditable values.

### Why concept_top2 is Optional?
When the LLM is confident, forcing a second candidate creates noise. The LLM would either:
- Invent a spurious second match
- Output the same concept twice
- Pick something random

Better to allow `null` when confident.

### Why 0.50-0.85 for Ambiguous Band?
- Below 0.50: The LLM is essentially guessing
- Above 0.85: Close enough to confident to consider auto-commit risky
- 0.50-0.85: Clear "uncertain but has ideas" territory

### Why Priority-Based Value Parsing?
The "first match" regex approach has a critical bug:
```
"Revenue increased 10% to $2.75 billion"
First match: 10 ❌
Correct: 2,750,000,000 ✓
```

Priority-based matching checks patterns in order of signal strength:
1. Currency + multiplier (strongest signal)
2. Currency + large number
3. Multiplier alone
4. Percentage (only if unit="pure")
5. Largest number (fallback)

This ensures we grab the VALUE, not the percentage or change amount.

### Why Pure Data Catalog (No Instructions)?
The XBRL catalog contains ONLY reference data - no output instructions.

**Problem with instructions in both places:**
- Prompt says "output concept_top1", catalog says "output matched_concept" → conflict
- LLM doesn't know which is authoritative
- Updates require changing two places → drift risk

**Solution:** Catalog = pure data, Prompt = all instructions (single source of truth).

---

*Status: Ready for Implementation*