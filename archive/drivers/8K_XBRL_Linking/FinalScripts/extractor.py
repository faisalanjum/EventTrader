"""
8-K XBRL Fact Extractor

Thin wrapper that orchestrates:
1. LangExtract call with XBRL catalog context
2. Mapping outputs to RawExtraction
3. Postprocessing (validation, parsing, status)
4. Returning ExtractionResult

All extraction rules live in:
- extraction_config.py (prompt + examples)
- postprocessor.py (validation + parsing)
"""

import logging
from typing import Optional, Set, Tuple, Union
from dataclasses import dataclass

import langextract as lx
from langextract.core.data import Extraction, AnnotatedDocument

from extraction_schema import (
    RawExtraction,
    ProcessedFact,
    ExtractionResult,
    UNMATCHED
)
from extraction_config import PROMPT_DESCRIPTION, EXAMPLES
from postprocessor import postprocess

logger = logging.getLogger(__name__)


@dataclass
class CatalogContext:
    """
    Pre-extracted catalog data for extraction.

    Use this when you want to pass catalog data directly
    instead of an XBRLCatalog object.
    """
    valid_qnames: Set[str]
    valid_units: Set[str]
    llm_context: str
    cik: str = ""
    company_name: str = ""
    valid_dimensions: Set[str] = None
    valid_members: Set[str] = None

    def __post_init__(self):
        # Initialize empty sets if not provided
        if self.valid_dimensions is None:
            self.valid_dimensions = set()
        if self.valid_members is None:
            self.valid_members = set()


def extract_facts(
    text: str,
    catalog: Union["XBRLCatalog", CatalogContext],
    filing_id: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    max_workers: Optional[int] = None,
    batch_length: Optional[int] = None,
    max_output_tokens: Optional[int] = None,
    max_char_buffer: int = 4000,
    suppress_parse_errors: bool = False,
    debug: bool = False,
    use_schema_constraints: bool = True,
    extraction_passes: int = 1,
) -> ExtractionResult:
    """
    Production function: Extract financial facts from 8-K text.

    Returns only ExtractionResult. For debugging/visualization, use extract_facts_debug().
    """
    result, _ = _extract_core(
        text=text,
        catalog=catalog,
        filing_id=filing_id,
        model=model,
        max_workers=max_workers,
        batch_length=batch_length,
        max_output_tokens=max_output_tokens,
        max_char_buffer=max_char_buffer,
        suppress_parse_errors=suppress_parse_errors,
        debug=debug,
        use_schema_constraints=use_schema_constraints,
        extraction_passes=extraction_passes,
    )
    return result


def extract_facts_debug(
    text: str,
    catalog: Union["XBRLCatalog", CatalogContext],
    filing_id: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    max_workers: Optional[int] = None,
    batch_length: Optional[int] = None,
    max_output_tokens: Optional[int] = None,
    max_char_buffer: int = 4000,
    suppress_parse_errors: bool = False,
    debug: bool = False,
    use_schema_constraints: bool = True,
    extraction_passes: int = 1,
) -> Tuple[ExtractionResult, AnnotatedDocument]:
    """
    Debug function: Extract financial facts and return annotated document.

    Returns both ExtractionResult and AnnotatedDocument for visualization.
    Use this in notebooks to access raw LangExtract output for inspection.
    """
    return _extract_core(
        text=text,
        catalog=catalog,
        filing_id=filing_id,
        model=model,
        max_workers=max_workers,
        batch_length=batch_length,
        max_output_tokens=max_output_tokens,
        max_char_buffer=max_char_buffer,
        suppress_parse_errors=suppress_parse_errors,
        debug=debug,
        use_schema_constraints=use_schema_constraints,
        extraction_passes=extraction_passes,
    )


def _extract_core(
    text: str,
    catalog: Union["XBRLCatalog", CatalogContext],
    filing_id: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    max_workers: Optional[int] = None,
    batch_length: Optional[int] = None,
    max_output_tokens: Optional[int] = None,
    max_char_buffer: int = 4000,
    suppress_parse_errors: bool = False,
    debug: bool = False,
    use_schema_constraints: bool = True,
    extraction_passes: int = 1,
) -> Tuple[ExtractionResult, AnnotatedDocument]:
    """
    Core extraction logic. Returns both ExtractionResult and AnnotatedDocument.

    Args:
        text: The 8-K document text to extract from
        catalog: Either an XBRLCatalog object or CatalogContext with:
                 - valid_qnames: Set of valid concept qnames
                 - valid_units: Set of valid units (e.g., {"USD", "shares", "pure"})
                 - llm_context: Pre-rendered catalog context string
        filing_id: Optional filing identifier for tracking
        model: LangExtract model ID (default: gemini-2.5-flash)
               Examples: gemini-2.5-flash, gemini-2.5-pro, gpt-4.1-nano, gpt-4.1, gpt-4o
        max_workers: Maximum parallel workers for concurrent processing (default: None = LangExtract default)
        batch_length: Number of chunks per batch (default: None = LangExtract default)
        max_output_tokens: Maximum output tokens for LLM (default: None = LangExtract default)
                          Examples: 65536 for gemini-2.5-flash, 32768 for gpt-4.1-nano
        max_char_buffer: Maximum characters per chunk (default: 4000)
        suppress_parse_errors: Whether to suppress parsing errors (default: False)
        debug: Whether to enable debug logging (default: False)
        use_schema_constraints: Whether to use LLM structured output mode (default: True)
                               Set to False for Gemini models to avoid truncation/malformed JSON bugs

    Returns:
        Tuple of (ExtractionResult, AnnotatedDocument)
    """
    # Extract catalog data
    if hasattr(catalog, 'to_llm_context'):
        # XBRLCatalog object
        valid_qnames = set(catalog.concepts.keys())
        # Simple validation: any unit in the catalog is valid (no conversion needed)
        valid_units = set(catalog.units.keys())
        # Use latest_per_form_type=True for one 10-K + one 10-Q value per concept
        llm_context = catalog.to_llm_context(latest_per_form_type=True)
        cik = catalog.cik
        company_name = catalog.company_name
    else:
        # CatalogContext
        valid_qnames = catalog.valid_qnames
        valid_units = catalog.valid_units
        llm_context = catalog.llm_context
        cik = catalog.cik
        company_name = catalog.company_name

    # Run extraction using lx.extract() with additional_context
    # The catalog is passed as additional_context (not concatenated) so:
    # - Only document text is chunked
    # - Each chunk gets the full catalog as reference context
    # - Character positions are relative to document text only
    logger.info(f"Extracting facts from {len(text)} chars with {len(valid_qnames)} concepts")

    # Build kwargs for lx.extract - only include non-None values
    extract_kwargs = {
        "text_or_documents": text,
        "prompt_description": PROMPT_DESCRIPTION,
        "examples": EXAMPLES,
        "model_id": model,
        "additional_context": llm_context,
        "max_char_buffer": max_char_buffer,
        "resolver_params": {"suppress_parse_errors": suppress_parse_errors},
        "debug": debug,
        "show_progress": True,
        "use_schema_constraints": use_schema_constraints,
    }

    # Add optional parameters only if specified
    if max_workers is not None:
        extract_kwargs["max_workers"] = max_workers
    if batch_length is not None:
        extract_kwargs["batch_length"] = batch_length
    if max_output_tokens is not None:
        extract_kwargs["language_model_params"] = {"max_output_tokens": max_output_tokens}
    if extraction_passes > 1:
        extract_kwargs["extraction_passes"] = extraction_passes

    annotated_doc = lx.extract(**extract_kwargs)
    extractions = annotated_doc.extractions or []

    # Map to RawExtraction, filtering out extractions from catalog context
    raw_extractions = _map_to_raw(extractions, source_text_length=len(text))
    logger.info(f"LangExtract returned {len(raw_extractions)} extractions")

    # Postprocess
    processed_facts = postprocess(raw_extractions, valid_qnames, valid_units)

    # Build result
    result = ExtractionResult(
        cik=cik,
        company_name=company_name,
        filing_id=filing_id,
        facts=processed_facts,
        source_text_length=len(text),
        catalog_token_estimate=len(llm_context) // 4  # Rough estimate
    )
    result.compute_stats()

    logger.info(
        f"Extraction complete: {result.committed_count} committed, "
        f"{result.candidate_count} candidates, {result.review_count} review"
    )

    return result, annotated_doc


def _map_to_raw(extractions: list, source_text_length: int) -> list:
    """
    Map LangExtract Extraction objects to RawExtraction dataclasses.

    With the additional_context approach, char positions should always be
    relative to the document text. The char_end > source_text_length filter
    is a safety check that should rarely trigger.
    """
    raw = []

    for ext in extractions:
        # Skip non-financial extractions
        if getattr(ext, 'extraction_class', '') != 'financial_fact':
            continue

        # New API: char_interval is a CharInterval object with start_pos/end_pos
        char_interval = getattr(ext, 'char_interval', None)
        char_start = char_interval.start_pos if char_interval else 0
        char_end = char_interval.end_pos if char_interval else 0

        # Safety check - should rarely trigger with additional_context approach
        if char_end > source_text_length:
            logger.warning(
                f"Skipping extraction: char_end={char_end} > source_text_length={source_text_length} "
                f"(text: '{getattr(ext, 'extraction_text', '')[:50]}...')"
            )
            continue

        attrs = getattr(ext, 'attributes', {}) or {}

        # Extract required fields with defaults
        concept_top1 = attrs.get('concept_top1') or UNMATCHED
        matched_period = attrs.get('matched_period') or ''
        matched_unit = attrs.get('matched_unit') or ''

        # Safe float conversion for confidence
        try:
            confidence = float(attrs.get('confidence', 0.0))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse confidence '{attrs.get('confidence')}', using 0.0")
            confidence = 0.0

        reasoning = attrs.get('reasoning') or ''

        # Optional fields
        concept_top2 = attrs.get('concept_top2')
        matched_dimension = attrs.get('matched_dimension')
        matched_member = attrs.get('matched_member')

        raw.append(RawExtraction(
            extraction_text=getattr(ext, 'extraction_text', ''),
            char_start=char_start,
            char_end=char_end,
            concept_top1=concept_top1,
            matched_period=matched_period,
            matched_unit=matched_unit,
            confidence=confidence,
            reasoning=reasoning,
            concept_top2=concept_top2,
            matched_dimension=matched_dimension,
            matched_member=matched_member
        ))

    return raw


# NOTE: _extract_canonical_units is no longer used. Unit validation now uses
# raw unit names from catalog.units.keys() directly. Keeping for reference.
#
# def _extract_canonical_units(catalog) -> Set[str]:
#     """
#     Extract canonical unit names from catalog.
#
#     Converts XBRL unit qnames to canonical format:
#     - iso4217:USD → USD
#     - iso4217:USDshares → USD/share
#     - shares → shares
#     - pure → pure
#     """
#     canonical = set()
#
#     for uname, info in catalog.units.items():
#         utype = info.get("type", "")
#
#         if utype == "monetaryItemType" and uname.startswith("iso4217:"):
#             canonical.add(uname.split(":")[1])
#         elif utype == "perShareItemType" and uname.startswith("iso4217:"):
#             currency = uname.split(":")[1].replace("shares", "")
#             canonical.add(f"{currency}/share")
#         elif utype == "sharesItemType" or uname == "shares":
#             canonical.add("shares")
#         elif uname == "pure":
#             canonical.add("pure")
#
#     # Ensure common defaults
#     if not canonical:
#         canonical = {"USD", "shares", "pure", "USD/share"}
#
#     return canonical
