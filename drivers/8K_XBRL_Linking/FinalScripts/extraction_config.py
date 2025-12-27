"""
Extraction Configuration for 8-K XBRL Fact Extraction

Contains:
- PROMPT_DESCRIPTION: Instructions for LangExtract
- EXAMPLES: Few-shot examples for LangExtract
- Constants: Thresholds

Note: Unit validation uses catalog.units, not a hardcoded set.
Each company has its own XBRL schema with specific units.
"""

from langextract.data import ExampleData, Extraction

# =============================================================================
# CONSTANTS
# =============================================================================

COMMIT_THRESHOLD = 0.90

# =============================================================================
# PROMPT DESCRIPTION
# =============================================================================

PROMPT_DESCRIPTION = """
ROLE:
You are extracting financial facts from SEC 8-K filings and matching them
to XBRL concepts from the company's XBRL catalog provided in the context.

The context contains XBRL reference data wrapped in <<<BEGIN_XBRL_REFERENCE_DATA>>>
and <<<END_XBRL_REFERENCE_DATA>>> markers. Use this data to match your extractions.

EXTRACTION RULES:
• Extract EXACT text spans from the document (do not paraphrase)
• Extract quantitative FINANCIAL metrics only (revenue, income, EPS, assets, etc.)
• Exclude operational metrics (headcount, customers, subscribers, etc.)
• Include the numeric value and any period context in the extraction

MATCHING RULES:
• Use ONLY qnames that appear in the catalog - NEVER invent or modify qnames
• Match each extraction to a concept qname from the CONCEPTS list in the catalog
• For segmented data, use dimension/member qnames EXACTLY as they appear in the catalog
• If no concept in the catalog matches, use "UNMATCHED" for concept_top1
• If unsure, output "UNMATCHED" with an optional concept_top2 as your best guess

PERIOD MATCHING:
• Companies have different fiscal year ends - check the FISCAL CALENDAR section in the catalog for this company's quarter/year dates

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
""".strip()

# =============================================================================
# FEW-SHOT EXAMPLES
#
# Note on units: Examples use standard XBRL units (USD, shares, pure, USD/share).
# The prompt instructs the model to pick from the catalog's UNITS section.
# =============================================================================

EXAMPLES = [
    # -------------------------------------------------------------------------
    # Example 1: Confident Match (Net Income)
    # -------------------------------------------------------------------------
    ExampleData(
        text="The company reported net income of $2.75 billion for fiscal year 2024.",
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
    ),

    # -------------------------------------------------------------------------
    # Example 2: Uncertain Match (Revenue - varies by filer)
    # Revenue concepts vary: Revenues, RevenueFromContractWithCustomer, etc.
    # Model should check catalog for the exact qname this company uses.
    # -------------------------------------------------------------------------
    ExampleData(
        text="Total revenues reached $8.5 billion for the full year, up 10% from prior year.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Total revenues reached $8.5 billion for the full year",
                attributes={
                    "concept_top1": "UNMATCHED",
                    "concept_top2": "us-gaap:Revenues",
                    "matched_period": "2024-01-01→2024-12-31",
                    "matched_unit": "USD",
                    "confidence": 0.60,
                    "reasoning": "Revenue concept varies by filer; choose exact qname from catalog"
                }
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # Example 3: Ambiguous Match (Two Plausible Concepts)
    # -------------------------------------------------------------------------
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
    ),

    # -------------------------------------------------------------------------
    # Example 4: Low Confidence (Company-Specific Term)
    # -------------------------------------------------------------------------
    ExampleData(
        text="Transaction-based revenue grew to $450 million, reflecting increased trading activity.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Transaction-based revenue grew to $450 million",
                attributes={
                    "concept_top1": "UNMATCHED",
                    "concept_top2": "us-gaap:Revenues",
                    "matched_period": "2025-04-01→2025-06-30",
                    "matched_unit": "USD",
                    "confidence": 0.45,
                    "reasoning": "Transaction-based revenue is company-specific breakdown, unclear if it maps to general revenue concept"
                }
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # Example 5: Confident Match (Per-Share Value)
    # -------------------------------------------------------------------------
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
    ),

    # -------------------------------------------------------------------------
    # Example 6: Not Confident (Non-GAAP / Adjusted Metric)
    # -------------------------------------------------------------------------
    ExampleData(
        text="Adjusted EBITDA reached $3.2 billion for the quarter, up 12% year-over-year.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Adjusted EBITDA reached $3.2 billion for the quarter",
                attributes={
                    "concept_top1": "UNMATCHED",
                    "concept_top2": None,
                    "matched_period": "2025-04-01→2025-06-30",
                    "matched_unit": "USD",
                    "confidence": 0.35,
                    "reasoning": "Adjusted EBITDA is a non-GAAP measure, no standard XBRL concept in catalog"
                }
            )
        ]
    ),
]
