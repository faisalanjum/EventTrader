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
• If no concept in the catalog matches, use "UNMATCHED" for concept_top1
• If unsure, output "UNMATCHED" with an optional concept_top2 as your best guess

DIMENSIONAL DATA (SEGMENTS):
XBRL uses dimensional taxonomy to segment data (by business unit, geography, product, etc.):

• DIMENSION (Axis): Category of segmentation. Standard axes have us-gaap: or srt: prefix.
  Common: us-gaap:StatementBusinessSegmentsAxis, us-gaap:StatementGeographicalAxis,
  srt:ProductOrServiceAxis, us-gaap:StatementClassOfStockAxis

• MEMBER: Specific segment value. Can be standard (us-gaap:, srt:) or company-specific.
  Standard members: srt:AmericasMember, srt:EuropeMember, us-gaap:OperatingSegmentsMember
  Company-specific members: Look up EXACTLY from catalog's DIMENSIONS → MEMBERS section

WHEN TO USE matched_dimension / matched_member:
• USE when text mentions a SPECIFIC segment, region, or product line
• OMIT when text is company-wide/consolidated (no segment breakdown)
• ALWAYS look up the exact member qname from the catalog - never guess or invent member names

PERIOD MATCHING:
• Companies have different fiscal year ends - check the FISCAL CALENDAR section in the catalog for this company's quarter/year dates

VALID VALUES FOR concept_top1 / concept_top2:
• Any exact qname from the CONCEPTS list in the catalog (e.g., "us-gaap:NetIncomeLoss")
• "UNMATCHED" - use this when no concept in the catalog applies

CONFIDENCE GUIDELINES:

CRITICAL RULE: concept_top2 and confidence are LINKED:
• If you output concept_top2, your confidence MUST be < 0.90
• If confidence >= 0.90, you MUST NOT output concept_top2 (set to null)
• Confidence reflects certainty in the SPECIFIC concept_top1 choice, not the general category

• CONFIDENT (0.90+): One clear, unambiguous match - NO ALTERNATIVES
  → concept_top1 = qname from catalog
  → concept_top2 = null (MUST omit - do NOT provide alternatives when confident)

• AMBIGUOUS (0.50-0.85): Two plausible matches, genuinely uncertain which is correct
  → concept_top1 = best match qname
  → concept_top2 = second best qname

• NOT CONFIDENT (<0.50): No clear match or very uncertain
  → concept_top1 = "UNMATCHED"
  → concept_top2 = best guess qname (or null if no reasonable guess)

Example: "Total revenue was $10B" with both us-gaap:Revenues and
us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax in catalog:
• If catalog shows company consistently uses one → confidence 0.92, concept_top2 = null
• If both appear equally → confidence 0.75, concept_top2 = the other one

Use historical values in the catalog as a HINT for confidence, but do not reject
based on magnitude differences alone (step-changes like acquisitions are legitimate).

OUTPUT FORMAT (STRICT JSON - each field must be a single value, never lists or multiline):
• concept_top1: Exact qname from catalog OR "UNMATCHED" (SINGLE STRING)
• concept_top2: Second best qname OR null (SINGLE STRING or null)
• matched_period: "YYYY-MM-DD" (instant) or "YYYY-MM-DD→YYYY-MM-DD" (duration)
• matched_unit: Must be one of the units listed in the catalog's UNITS section (SINGLE STRING)
• matched_dimension: Exact dimension qname from catalog, e.g. "us-gaap:StatementBusinessSegmentsAxis" (SINGLE STRING or omit)
• matched_member: Exact member qname from catalog, e.g. "dell:InfrastructureSolutionsGroupMember" (SINGLE STRING or omit)
  CRITICAL: matched_member must be ONE qname only. Never copy the catalog listing format. Never include multiple members, arrows, or fact counts.
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

    # -------------------------------------------------------------------------
    # Example 7: Segmented Data WITH Dimension/Member (Geographic)
    # When text mentions a specific region/geography, include dimension + member.
    # Uses STANDARD srt: members (AmericasMember, EuropeMember, AsiaPacificMember)
    # that exist across most companies' catalogs - fully generic pattern.
    # -------------------------------------------------------------------------
    ExampleData(
        text="Americas region revenue was $12.4 billion for the quarter, up 8% year-over-year.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Americas region revenue was $12.4 billion for the quarter",
                attributes={
                    "concept_top1": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                    "concept_top2": None,
                    "matched_period": "2025-04-01→2025-06-30",
                    "matched_unit": "USD",
                    "matched_dimension": "us-gaap:StatementGeographicalAxis",
                    "matched_member": "srt:AmericasMember",
                    "confidence": 0.92,
                    "reasoning": "Region-specific revenue for Americas; dimension is standard axis, member is standard SRT geographic member from catalog"
                }
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # Example 8: Consolidated Data WITHOUT Dimension/Member (Contrast)
    # When text is company-wide (not broken down by segment), OMIT dimension/member.
    # This contrasts with Example 7 to show when NOT to use dimensional fields.
    # -------------------------------------------------------------------------
    ExampleData(
        text="Total consolidated revenue for the company reached $22.3 billion in Q2 2025.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Total consolidated revenue for the company reached $22.3 billion in Q2 2025",
                attributes={
                    "concept_top1": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                    "concept_top2": None,
                    "matched_period": "2025-04-01→2025-06-30",
                    "matched_unit": "USD",
                    "confidence": 0.93,
                    "reasoning": "Company-wide consolidated revenue, no segment breakdown - dimension/member fields omitted"
                }
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # Example 9: Business Segment with Company-Specific Member
    # For business segments, the member qname uses a company-specific prefix.
    # CRITICAL: Look up the exact member qname from the catalog's DIMENSIONS AND MEMBERS
    # section. Output ONLY the qname string (e.g., "company:SegmentMember"), never the
    # full catalog reference format with labels and fact counts.
    # -------------------------------------------------------------------------
    ExampleData(
        text="The Cloud Services segment generated operating income of $2.8 billion for Q2.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Cloud Services segment generated operating income of $2.8 billion for Q2",
                attributes={
                    "concept_top1": "us-gaap:OperatingIncomeLoss",
                    "concept_top2": None,
                    "matched_period": "2025-04-01→2025-06-30",
                    "matched_unit": "USD",
                    "matched_dimension": "us-gaap:StatementBusinessSegmentsAxis",
                    "matched_member": "us-gaap:OperatingSegmentsMember",
                    "confidence": 0.88,
                    "reasoning": "Segment operating income; if catalog has specific member for Cloud Services, use it; otherwise use standard us-gaap:OperatingSegmentsMember"
                }
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # Example 10: High Confidence with Similar Concepts - NO concept_top2
    # CRITICAL: When confident (0.90+), do NOT output concept_top2 even if
    # similar concepts exist. Pick the one the catalog shows the company uses.
    # This example shows: similar revenue concepts exist but we pick ONE.
    # -------------------------------------------------------------------------
    ExampleData(
        text="Record revenue of $29.8 billion in Q2, driven by strong AI demand.",
        extractions=[
            Extraction(
                extraction_class="financial_fact",
                extraction_text="Record revenue of $29.8 billion in Q2",
                attributes={
                    "concept_top1": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                    "concept_top2": None,
                    "matched_period": "2025-04-01→2025-06-30",
                    "matched_unit": "USD",
                    "confidence": 0.94,
                    "reasoning": "Catalog shows company uses ASC 606 revenue concept with matching historical values; high confidence means no concept_top2"
                }
            )
        ]
    ),
]
