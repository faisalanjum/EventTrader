# 8-K XBRL Linking Pipeline - Infrastructure & Architecture Guide

## Overview

This is a **LLM-powered fact extraction pipeline** that:
1. Takes an 8-K filing text document
2. Fetches the company's XBRL catalog from Neo4j (from 10-K/10-Q filings)
3. Uses LangExtract to extract financial facts and match them to XBRL concepts
4. Post-processes extractions with validation, parsing, and status determination

---

## Recommended Learning Order

```
                    ┌─────────────────────────────┐
                    │  1. extraction_schema.py    │ ◄── START HERE
                    │     (The Foundation)        │     117 lines
                    │     Data structures only    │     No dependencies
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│ 2. extraction_  │    │ 3. xbrl_catalog.py  │    │ 4. postprocessor│
│    config.py    │    │   (Data Source)     │    │    .py          │
│ (LLM Brain)     │    │   1950 lines        │    │ (Quality Control│
│  214 lines      │    │   Neo4j → Catalog   │    │  509 lines      │
└────────┬────────┘    └─────────┬───────────┘    └────────┬────────┘
         │                       │                         │
         │     PROMPT +          │    XBRLCatalog          │   Validation
         │     EXAMPLES          │    to_llm_context()     │   + Parsing
         │                       │                         │
         └───────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────┐
                    │     5. extractor.py         │
                    │     (The Orchestrator)      │
                    │     206 lines               │
                    │     Ties everything together│
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │  6. test_pipeline.py        │
                    │  7. pipeline_test.ipynb     │
                    │  8. Xtract.ipynb            │
                    │     (See it in action)      │
                    └─────────────────────────────┘
```

---

# File-by-File Deep Dive

---

## 1. `extraction_schema.py` (117 lines)

**Purpose**: Data classes representing the extraction pipeline output

### Data Structures

| Class | Purpose | Key Fields |
|-------|---------|------------|
| `RawExtraction` | LLM output before validation | `extraction_text`, `char_start/end`, `concept_top1/top2`, `matched_period`, `matched_unit`, `confidence`, `reasoning` |
| `ProcessedFact` | After validation/parsing | All above + `value_parsed`, `status`, `committed`, validation flags |
| `ExtractionResult` | Complete pipeline result | `cik`, `company_name`, `facts[]`, statistics |

### ExtractionStatus Enum

```python
COMMITTED       → High confidence, auto-link to Neo4j
CANDIDATE_ONLY  → Low confidence or UNMATCHED, needs review
REVIEW          → Parse failure or validation error
```

### RawExtraction Fields

**Core fields (from LangExtract):**
- `extraction_text: str` - The exact text span extracted
- `char_start: int` - Start position in document
- `char_end: int` - End position in document

**LLM-provided matching:**
- `concept_top1: str` - Best match qname OR "UNMATCHED"
- `matched_period: str` - "YYYY-MM-DD" or "YYYY-MM-DD→YYYY-MM-DD"
- `matched_unit: str` - Unit from catalog UNITS section
- `confidence: float` - 0.0 to 1.0
- `reasoning: str` - Brief explanation

**Optional fields:**
- `concept_top2: Optional[str]` - Second best qname (for ambiguous cases)
- `matched_dimension: Optional[str]` - When fact is segmented
- `matched_member: Optional[str]` - When fact is segmented

### ProcessedFact Additional Fields

- `value_parsed: Optional[float]` - Deterministically parsed from extraction_text
- `committed: bool` - True if auto-linking to Neo4j
- `status: ExtractionStatus` - COMMITTED / CANDIDATE_ONLY / REVIEW
- `qname_valid: bool` - Was concept_top1 in valid set?
- `unit_valid: bool` - Was matched_unit in canonical set?
- `period_normalized: bool` - Was period format normalized?
- `parse_error: Optional[str]` - Error message if parsing failed

### ExtractionResult Structure

```python
@dataclass
class ExtractionResult:
    cik: str
    company_name: str
    filing_id: Optional[str] = None
    facts: List[ProcessedFact] = field(default_factory=list)

    # Statistics
    total_extracted: int = 0
    committed_count: int = 0
    candidate_count: int = 0
    review_count: int = 0

    # Metadata
    source_text_length: int = 0
    catalog_token_estimate: int = 0

    def compute_stats(self):
        """Compute statistics from facts list."""
```

### Critical Constant

```python
UNMATCHED = "UNMATCHED"  # Used when no catalog concept matches
```

### Mental Model

```
LLM outputs → RawExtraction (unvalidated, could be wrong)
                    ↓
            postprocess()
                    ↓
            ProcessedFact (validated, parsed, status assigned)
                    ↓
            ExtractionResult (aggregated with statistics)
```

### Key Questions to Answer

1. What are the 4 optional fields in `RawExtraction` and why are they optional?
2. What's the difference between `committed` (bool) and `status` (enum) in `ProcessedFact`?
3. Why does `ExtractionResult.compute_stats()` exist instead of computing on access?

---

## 2. `extraction_config.py` (214 lines)

**Purpose**: Configuration for the 8-K XBRL fact extraction pipeline

### Constants

```python
COMMIT_THRESHOLD = 0.90  # Facts with confidence >= 90% get auto-committed
```

### PROMPT_DESCRIPTION (76 lines)

Defines what the LLM should do:

**ROLE:**
> You are extracting financial facts from SEC 8-K filings and matching them to XBRL concepts from the company's XBRL catalog provided in the context.

**EXTRACTION RULES:**
- Extract EXACT text spans from the document (do not paraphrase)
- Extract quantitative FINANCIAL metrics only (revenue, income, EPS, assets, etc.)
- Exclude operational metrics (headcount, customers, subscribers, etc.)
- Include the numeric value and any period context in the extraction

**MATCHING RULES:**
- Use ONLY qnames that appear in the catalog - NEVER invent or modify qnames
- Match each extraction to a concept qname from the CONCEPTS list in the catalog
- For segmented data, use dimension/member qnames EXACTLY as they appear
- If no concept matches, use "UNMATCHED" for concept_top1

**CONFIDENCE GUIDELINES:**

| Confidence | Scenario | concept_top1 | concept_top2 |
|------------|----------|--------------|--------------|
| 0.90+ | CONFIDENT - One clear match | qname from catalog | null (omit) |
| 0.50-0.85 | AMBIGUOUS - Two plausible matches | best match qname | second best qname |
| <0.50 | NOT CONFIDENT - No clear match | "UNMATCHED" | best guess or null |

**OUTPUT FORMAT:**
- `concept_top1`: Exact qname from catalog OR "UNMATCHED"
- `concept_top2`: Second best qname OR null (OPTIONAL)
- `matched_period`: "YYYY-MM-DD" (instant) or "YYYY-MM-DD→YYYY-MM-DD" (duration)
- `matched_unit`: Must be one of the units listed in the catalog's UNITS section
- `matched_dimension`: Exact dimension qname from catalog (only if segmented)
- `matched_member`: Exact member qname from catalog (only if segmented)
- `confidence`: Float 0.0-1.0
- `reasoning`: Brief explanation (1-2 sentences)

### EXAMPLES (6 few-shot examples)

Each example teaches the LLM a specific scenario:

| # | Scenario | Concept | Confidence | Teaching Point |
|---|----------|---------|------------|----------------|
| 1 | High confidence Net Income | `us-gaap:NetIncomeLoss` | 0.95 | Exact match, concept_top2=null |
| 2 | Revenue varies by filer | `UNMATCHED` | 0.60 | Use UNMATCHED when unsure, top2=best guess |
| 3 | Ambiguous Operating Costs | `us-gaap:OperatingExpenses` | 0.70 | Two plausible matches, provide both |
| 4 | Company-specific term | `UNMATCHED` | 0.45 | Low confidence, unclear mapping |
| 5 | Diluted EPS | `us-gaap:EarningsPerShareDiluted` | 0.95 | Per-share values, unit=USD/share |
| 6 | Non-GAAP metric | `UNMATCHED` | 0.35 | Adjusted EBITDA has no XBRL concept |

### Key Questions to Answer

1. What's the COMMIT_THRESHOLD value and where else is it defined?
2. How do the 6 examples cover different confidence scenarios?
3. What output format does the prompt specify?

---

## 3. `xbrl_catalog.py` (1951 lines)

**Purpose**: Neo4j integration for fetching company XBRL data

### Critical Insight

**Only 10-K, 10-Q, 10-K/A, and 10-Q/A have XBRL data. 8-K does NOT.**

```python
XBRL_FORM_TYPES = ["10-K", "10-Q", "10-K/A", "10-Q/A"]
```

### Data Classes

#### XBRLFact

Individual XBRL fact with full context:
```python
@dataclass
class XBRLFact:
    concept_label: str
    concept_qname: str
    value: str
    is_numeric: bool
    decimals: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    period_type: str  # instant or duration
    unit: Optional[str]
    balance: Optional[str]  # credit, debit, or null
    dimensional_context: List[Dict[str, str]]  # [{dimension: label, member: label}, ...]
    context_id: Optional[str]
    report_accession: Optional[str]
```

#### XBRLFiling

Single SEC filing with facts:
```python
@dataclass
class XBRLFiling:
    accession_no: str
    form_type: str
    period_of_report: str
    xbrl_id: Optional[str]
    facts: List[XBRLFact]
    key_metrics: Dict[str, Dict]
```

#### XBRLCatalog

Complete company catalog (the main output):
```python
@dataclass
class XBRLCatalog:
    cik: str
    company_name: str
    ticker: str
    industry: str
    sector: str

    # Filings with their facts
    filings: List[XBRLFiling]

    # Normalized reference tables (with fact counts)
    concepts: Dict[str, Dict[str, Any]]   # qname → {label, balance, period_type, fact_count}
    periods: Dict[str, Dict[str, Any]]    # period_id → {type, start/end/date, fact_count}
    units: Dict[str, Dict[str, Any]]      # unit_name → {type, is_simple, fact_count}
    dimensions: Dict[str, Dict[str, Any]] # dimension_qname → {label, member_count}
    members: Dict[str, Dict[str, Any]]    # member_qname → {label, dimension, fact_count}

    # Relationship structures
    calculation_network: Dict[str, List[Dict[str, Any]]]
    presentation_sections: Dict[str, List[str]]
```

### The Key Method: `to_llm_context()`

Generates LLM-optimized text (lines 577-969):

```
<<<BEGIN_XBRL_REFERENCE_DATA>>>
COMPANY: DELL TECHNOLOGIES INC (DELL)
CIK: 0001571996 | Industry: ComputerHardware | Sector: Technology

LEGEND:
• qname = unique concept identifier (e.g., us-gaap:Revenues)
• label = human-readable name
• balance: credit = ↑equity/liability | debit = ↑assets/expenses

────────────────────────────────────────────────────────────────────────
FILINGS (2 reports, 3,536 total facts)
────────────────────────────────────────────────────────────────────────
10-Q 2025-05-02 [1,231 facts]
10-K 2025-01-31 [2,305 facts] | Revenue=..., NetIncome=..., Assets=...

────────────────────────────────────────────────────────────────────────
CONCEPTS (814 total, top 100 shown)
────────────────────────────────────────────────────────────────────────
── TOP CONCEPTS (with history for magnitude validation) ──
us-gaap:Revenues | Revenues | credit
  History: $23.4B (10-Q, 2025-02-01→2025-05-02), $22.2B (10-Q, ...)

────────────────────────────────────────────────────────────────────────
PERIODS (X unique)
────────────────────────────────────────────────────────────────────────
Instant: 2025-05-03, 2025-02-01, ...
Duration: 2025-02-01→2025-05-02, ...

────────────────────────────────────────────────────────────────────────
UNITS
────────────────────────────────────────────────────────────────────────
USD | shares | pure | USD/share

<<<END_XBRL_REFERENCE_DATA>>>
```

### XBRL Date Normalization

XBRL uses exclusive end dates. The catalog normalizes them (lines 727-746):

```python
end_dt = datetime.strptime(pe[:10], "%Y-%m-%d")
end_normalized = (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
# 2024-01-01 to 2024-12-32 (exclusive) → 2024-01-01→2024-12-31 (inclusive)
```

### Unit Canonicalization

```python
def _canonical_unit(unit: str) -> str:
    # iso4217:USD       → USD
    # iso4217:USDshares → USD/share
    # shares            → shares
    # pure              → pure
```

### Main Fetch Function

```python
def get_xbrl_catalog(
    cik: str,
    form_types: Optional[List[str]] = None,  # Defaults to XBRL_FORM_TYPES
    limit_filings: Optional[int] = None,
    include_relationships: bool = True,
    driver=None
) -> XBRLCatalog:
```

**Neo4j queries fetch:**
1. Company info (cik, name, ticker, industry, sector)
2. Filings with HAS_XBRL relationship
3. Facts per filing (with dimensional context)
4. Normalized concepts/periods/units/members
5. Calculation relationships (with network/statement grouping)
6. Presentation structure

### Convenience Entry Point

```python
def xbrl_catalog(identifier: str, **kwargs) -> XBRLCatalog:
    """Smart fetcher - accepts either CIK or ticker."""
    # If looks like CIK (digits), use directly
    # Otherwise, look up by ticker first
```

### Key Questions to Answer

1. Why does `XBRL_FORM_TYPES` only include 10-K/10-Q variants (not 8-K)?
2. How does `_canonical_unit()` convert XBRL units?
3. What's the purpose of the `<<<BEGIN/END_XBRL_REFERENCE_DATA>>>` markers?

---

## 4. `postprocessor.py` (509 lines)

**Purpose**: Post-processing pipeline for validation and status determination

### Value Parsing: `parse_number_from_text()`

**Priority-based matching (CRITICAL to avoid "first match" bugs):**

| Priority | Pattern | Example | Result |
|----------|---------|---------|--------|
| 0 | Parentheses-negative | `($2.3 billion)` | -2,300,000,000 |
| 1 | Currency + multiplier | `$2.75 billion` | 2,750,000,000 |
| 2 | Currency + large number | `$2,750,000,000` | 2,750,000,000 |
| 3 | Multiplier alone | `2.75 billion` | 2,750,000,000 |
| 4 | Percentage (ratio units) | `23.5%` (unit=pure) | 0.235 |
| 5 | Smart fallback | Prefer decimals, avoid years | varies |

**Why priority-based?**
```python
# Example: "increased 10% to $2.75 billion"
#   - Buggy (first match): returns 10
#   - Correct (priority): returns 2,750,000,000
```

**Critical edge cases:**
- `"($2.3 billion)"` → -2.3B (accounting loss convention)
- `"(10%) decline"` → None (percentage in parens is NOT negative)
- `"margin of 23.5%"` with unit="USD" → None (percentage rejected for non-ratio)

**MULTIPLIERS dict:**
```python
MULTIPLIERS = {
    "trillion": 1e12, "t": 1e12,
    "billion": 1e9, "b": 1e9,
    "million": 1e6, "m": 1e6,
    "thousand": 1e3, "k": 1e3,
}
```

### Period Normalization: `normalize_period()`

**Arrow variant normalization:**
```python
ARROW_VARIANTS = ['-->', '->', '—>', '–>', ' - ', ' – ', ' — ', ' to ']
# All normalize to '→'
```

**Special handling:**
- `"2024-06-30→2024-06-30"` (same start/end) → `"2024-06-30"` (instant)
- Strips whitespace around arrows

### Period Validation: `validate_period()`

Must match:
- Instant: `YYYY-MM-DD`
- Duration: `YYYY-MM-DD→YYYY-MM-DD`

Also validates:
- Dates are real (no 2024-13-45)
- Start <= End for durations

### Qname Validation: `validate_qname()`

**NO FUZZY MATCHING - invalid qnames become UNMATCHED:**

```python
def validate_qname(qname: str, valid_qnames: Set[str]) -> Tuple[str, bool]:
    if not qname:
        return UNMATCHED, False
    if qname == UNMATCHED:
        return UNMATCHED, True
    if qname in valid_qnames:
        return qname, True
    # Invalid qname
    logger.warning(f"Invalid qname '{qname}' not in catalog, setting to UNMATCHED")
    return UNMATCHED, False
```

### Unit Validation: `validate_unit()`

**Case-insensitive matching:**
```python
def validate_unit(unit: str, valid_units: Set[str]) -> Tuple[str, bool]:
    if unit in valid_units:
        return unit, True
    # Check case-insensitive
    unit_lower = unit.lower()
    for valid_unit in valid_units:
        if valid_unit.lower() == unit_lower:
            return valid_unit, True  # Return catalog's version
    return unit, False
```

### Status Determination: `determine_status()`

```python
def determine_status(
    concept_top1: str,
    confidence: float,
    value_parsed: Optional[float],
    period_valid: bool,
    qname_valid: bool,
    unit_valid: bool
) -> Tuple[ExtractionStatus, bool]:

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
        confidence >= COMMIT_THRESHOLD):  # 0.90
        return ExtractionStatus.COMMITTED, True

    # Everything else → CANDIDATE_ONLY
    return ExtractionStatus.CANDIDATE_ONLY, False
```

### Main Function: `postprocess()`

```python
def postprocess(
    raw_extractions: List[RawExtraction],
    valid_qnames: Set[str],
    valid_units: Set[str]
) -> List[ProcessedFact]:
```

**Processing steps:**
1. Validate concept_top1 (invalid → UNMATCHED)
2. Validate concept_top2 (invalid → None)
3. Normalize and validate period
4. Validate unit
5. Parse value deterministically
6. Determine status
7. Create ProcessedFact with all validation flags

### Key Questions to Answer

1. Why does parentheses-negative have highest priority (0)?
2. What arrow variants are normalized to `→`?
3. What three conditions cause REVIEW status?

---

## 5. `extractor.py` (206 lines)

**Purpose**: Thin wrapper that orchestrates the extraction pipeline

### CatalogContext Dataclass

For when you want to pass catalog data directly:
```python
@dataclass
class CatalogContext:
    valid_qnames: Set[str]
    valid_units: Set[str]
    llm_context: str
    cik: str = ""
    company_name: str = ""
```

### Main Entry Point: `extract_facts()`

```python
def extract_facts(
    text: str,
    catalog: Union["XBRLCatalog", CatalogContext],
    filing_id: Optional[str] = None,
    model: str = "gemini-2.0-flash",  # DEFAULT MODEL
) -> ExtractionResult:
```

**Data flow inside:**

```python
# 1. Extract catalog data
if hasattr(catalog, 'to_llm_context'):
    valid_qnames = set(catalog.concepts.keys())
    valid_units = _extract_canonical_units(catalog)
    llm_context = catalog.to_llm_context()
else:
    # Use CatalogContext directly
    valid_qnames = catalog.valid_qnames
    valid_units = catalog.valid_units
    llm_context = catalog.llm_context

# 2. Build full context
full_context = f"{text}\n\n{llm_context}"

# 3. Initialize LangExtract
extractor = LangExtract(
    model=model,
    description=PROMPT_DESCRIPTION,
    examples=EXAMPLES
)

# 4. Run extraction
extractions = extractor.extract(full_context)

# 5. Map to RawExtraction (FILTERING HAPPENS HERE)
raw_extractions = _map_to_raw(extractions, source_text_length=len(text))

# 6. Postprocess
processed_facts = postprocess(raw_extractions, valid_qnames, valid_units)

# 7. Build result
result = ExtractionResult(...)
result.compute_stats()
return result
```

### Critical Filter: `_map_to_raw()`

**Prevents extracting from catalog context:**

```python
def _map_to_raw(extractions: list, source_text_length: int) -> list:
    raw = []
    for ext in extractions:
        # Skip non-financial extractions
        if getattr(ext, 'extraction_class', '') != 'financial_fact':
            continue

        # Skip extractions pointing into catalog context
        char_end = getattr(ext, 'char_end', 0)
        if char_end > source_text_length:
            logger.debug(f"Dropping extraction at char_end={char_end} (beyond source text)")
            continue

        # ... map to RawExtraction
```

**Why this matters:**
- Full context = `text + "\n\n" + llm_context`
- LangExtract might extract from the catalog examples
- Solution: Filter extractions where `char_end > source_text_length`

### Unit Canonicalization: `_extract_canonical_units()`

```python
def _extract_canonical_units(catalog) -> Set[str]:
    canonical = set()
    for uname, info in catalog.units.items():
        utype = info.get("type", "")
        if utype == "monetaryItemType" and uname.startswith("iso4217:"):
            canonical.add(uname.split(":")[1])  # USD
        elif utype == "perShareItemType" and uname.startswith("iso4217:"):
            currency = uname.split(":")[1].replace("shares", "")
            canonical.add(f"{currency}/share")  # USD/share
        elif utype == "sharesItemType" or uname == "shares":
            canonical.add("shares")
        elif uname == "pure":
            canonical.add("pure")

    if not canonical:
        canonical = {"USD", "shares", "pure", "USD/share"}
    return canonical
```

### Key Questions to Answer

1. Why filter extractions where `char_end > source_text_length`?
2. What's the default model used?
3. What does `CatalogContext` provide vs `XBRLCatalog`?

---

## 6. `test_pipeline.py` (539 lines)

**Purpose**: Test script for step-by-step pipeline testing

### Command-Line Interface

```bash
python test_pipeline.py --unit          # Unit tests (no external deps)
python test_pipeline.py --postprocess   # Test postprocessor with mock data
python test_pipeline.py --catalog DELL  # Test catalog fetch from Neo4j
python test_pipeline.py --extract DELL  # Full pipeline with real 8-K
python test_pipeline.py --file PATH     # Specify 8-K file
python test_pipeline.py --all DELL      # Run everything
```

### Unit Tests

| Test | Count | What It Tests |
|------|-------|---------------|
| `test_value_parsing()` | 12 cases | Priority-based parsing, negatives, percentages |
| `test_period_normalization()` | 10 cases | Arrow variants, instant/duration, validation |
| `test_qname_validation()` | 5 cases | Valid/invalid qnames, UNMATCHED passthrough |
| `test_status_determination()` | 7 cases | COMMITTED/CANDIDATE_ONLY/REVIEW logic |

### Sample Data

```python
SAMPLE_DATA_DIR = "/home/faisal/EventMarketDB/drivers/8K_XBRL_Linking/sample_data"
SAMPLE_FILES = {
    "DELL": "DELL_1571996_2025-08-28_000157199625000096/exhibit_EX-99.1.txt",
}
```

### Test Functions

- `run_unit_tests()` - All unit tests, no external deps
- `test_postprocessor()` - Mock RawExtraction data through postprocess()
- `test_catalog(ticker)` - Real Neo4j fetch
- `test_full_pipeline(ticker, file_path)` - End-to-end with sample 8-K

---

## 7. `pipeline_test.ipynb` (219,516 bytes)

**Purpose**: Interactive Jupyter notebook for testing

### Sections

| Cell Range | What It Tests |
|------------|---------------|
| 1-6 | Individual unit tests (parsing, validation) |
| 7 | Catalog fetch from Neo4j |
| 8-9 | Real LangExtract call |
| 10 | Save results (JSONL + HTML) |

### Notable Results from DELL Test

```
Catalog: 814 concepts, 12 units, 3,536 facts from 2 filings
LLM context: ~26,000 characters
Model: gemini-2.5-pro
Temperature: 0.3
Raw extractions: 144 financial_fact (after filtering catalog context)
```

---

## 8. `Xtract.ipynb` (307,836 bytes)

**Purpose**: Similar to pipeline_test.ipynb but with configurable model

### Config Cell

```python
model_name = "gemini-2.0-flash"  # gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash
suppress_parse_errors_value = False
TICKER = "DELL"
filings_count = 2
```

### Key Differences from pipeline_test.ipynb

- Configurable model at top
- `suppress_parse_errors_value` option
- Different results based on model (278 extractions with gemini-2.5-flash vs 144)

---

# Architecture Diagram

```
┌─────────────┐     ┌───────────────┐
│  8-K Text   │     │   Neo4j DB    │
│  (28K chars)│     │  (10-K/10-Q)  │
└──────┬──────┘     └───────┬───────┘
       │                    │
       │             xbrl_catalog()
       │                    │
       │            ┌───────▼───────┐
       │            │  XBRLCatalog  │
       │            │  814 concepts │
       │            │  12 units     │
       │            └───────┬───────┘
       │                    │
       │            to_llm_context()
       │                    │
       ▼                    ▼
┌──────────────────────────────────┐
│         extract_facts()          │
│                                  │
│  text + catalog_context (54K+)  │
│              │                   │
│       LangExtract.extract()      │
│              │                   │
│     _map_to_raw() [FILTER]       │
│              │                   │
│        postprocess()             │
│              │                   │
└──────────────┼───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│        ExtractionResult          │
│  ├─ COMMITTED: X                 │
│  ├─ CANDIDATE_ONLY: Y            │
│  └─ REVIEW: Z                    │
└──────────────────────────────────┘
```

---

# Critical Implementation Details

## 1. The Catalog Context Filtering Problem

When LangExtract processes `text + catalog_context`, it might extract facts from the catalog examples too. The fix at `extractor.py:139-143`:

```python
char_end = getattr(ext, 'char_end', 0)
if char_end > source_text_length:
    logger.debug(f"Dropping extraction at char_end={char_end} (beyond source text)")
    continue
```

## 2. Priority-Based Parsing vs First-Match

The comment at `postprocessor.py:47-51` explains why:
```python
# Example: "increased 10% to $2.75 billion"
#   - Buggy (first match): returns 10
#   - Correct (priority): returns 2,750,000,000
```

## 3. XBRL Date Normalization

XBRL uses exclusive end dates. The catalog normalizes them at `xbrl_catalog.py:736-744`:
```python
end_dt = datetime.strptime(pe[:10], "%Y-%m-%d")
end_normalized = (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
```

## 4. Historical Values for Magnitude Validation

The top 30 concepts get historical values in `to_llm_context()` so the LLM can sanity-check extracted values. But the prompt warns:
> "Use historical values as a HINT for confidence, but do not reject based on magnitude differences alone (step-changes like acquisitions are legitimate)."

---

# Revamp Strategy

If you want to **revamp** this pipeline, here's what to focus on:

| Area | Current State | Potential Revamp |
|------|---------------|------------------|
| **Schema** | Fixed 3-class structure | Add confidence breakdown, source attribution |
| **Prompt** | Single 76-line prompt | Modular prompts per extraction type |
| **Parsing** | Regex-based, priority ordered | Consider using LLM for parsing too |
| **Catalog** | Monolithic 26K context | Chunk by statement type (BS/IS/CF) |
| **Status** | Binary threshold (0.90) | Graduated confidence with human review queue |

---

# File Sizes Reference

| File | Lines | Purpose |
|------|-------|---------|
| `extraction_schema.py` | 117 | Data structures |
| `extraction_config.py` | 214 | LLM prompt + examples |
| `extractor.py` | 206 | Orchestration |
| `postprocessor.py` | 509 | Validation + parsing |
| `xbrl_catalog.py` | 1951 | Neo4j integration |
| `test_pipeline.py` | 539 | CLI tests |
| `pipeline_test.ipynb` | - | Interactive testing |
| `Xtract.ipynb` | - | Configurable testing |
