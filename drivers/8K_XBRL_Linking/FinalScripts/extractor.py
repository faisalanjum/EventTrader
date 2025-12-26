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
from typing import Optional, Set, Union
from dataclasses import dataclass

from langextract import LangExtract, Extraction

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


def extract_facts(
    text: str,
    catalog: Union["XBRLCatalog", CatalogContext],
    filing_id: Optional[str] = None,
    model: str = "gemini-2.0-flash",
) -> ExtractionResult:
    """
    Extract financial facts from 8-K text using XBRL catalog context.

    Args:
        text: The 8-K document text to extract from
        catalog: Either an XBRLCatalog object or CatalogContext with:
                 - valid_qnames: Set of valid concept qnames
                 - valid_units: Set of valid units (e.g., {"USD", "shares", "pure"})
                 - llm_context: Pre-rendered catalog context string
        filing_id: Optional filing identifier for tracking
        model: LangExtract model to use (default: gemini-2.0-flash)

    Returns:
        ExtractionResult with processed facts and statistics
    """
    # Extract catalog data
    if hasattr(catalog, 'to_llm_context'):
        # XBRLCatalog object
        valid_qnames = set(catalog.concepts.keys())
        valid_units = _extract_canonical_units(catalog)
        llm_context = catalog.to_llm_context()
        cik = catalog.cik
        company_name = catalog.company_name
    else:
        # CatalogContext
        valid_qnames = catalog.valid_qnames
        valid_units = catalog.valid_units
        llm_context = catalog.llm_context
        cik = catalog.cik
        company_name = catalog.company_name

    # Build full context: document + catalog
    full_context = f"{text}\n\n{llm_context}"

    # Initialize LangExtract
    extractor = LangExtract(
        model=model,
        description=PROMPT_DESCRIPTION,
        examples=EXAMPLES
    )

    # Run extraction
    logger.info(f"Extracting facts from {len(text)} chars with {len(valid_qnames)} concepts")
    extractions = extractor.extract(full_context)

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

    return result


def _map_to_raw(extractions: list, source_text_length: int) -> list:
    """
    Map LangExtract Extraction objects to RawExtraction dataclasses.

    Filters out extractions where char_end > source_text_length,
    as these point into the appended catalog context, not the 8-K.
    """
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

        attrs = getattr(ext, 'attributes', {}) or {}

        # Extract required fields with defaults
        concept_top1 = attrs.get('concept_top1') or UNMATCHED
        matched_period = attrs.get('matched_period') or ''
        matched_unit = attrs.get('matched_unit') or ''
        confidence = float(attrs.get('confidence', 0.0))
        reasoning = attrs.get('reasoning') or ''

        # Optional fields
        concept_top2 = attrs.get('concept_top2')
        matched_dimension = attrs.get('matched_dimension')
        matched_member = attrs.get('matched_member')

        raw.append(RawExtraction(
            extraction_text=getattr(ext, 'extraction_text', ''),
            char_start=getattr(ext, 'char_start', 0),
            char_end=getattr(ext, 'char_end', 0),
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


def _extract_canonical_units(catalog) -> Set[str]:
    """
    Extract canonical unit names from catalog.

    Converts XBRL unit qnames to canonical format:
    - iso4217:USD → USD
    - iso4217:USDshares → USD/share
    - shares → shares
    - pure → pure
    """
    canonical = set()

    for uname, info in catalog.units.items():
        utype = info.get("type", "")

        if utype == "monetaryItemType" and uname.startswith("iso4217:"):
            canonical.add(uname.split(":")[1])
        elif utype == "perShareItemType" and uname.startswith("iso4217:"):
            currency = uname.split(":")[1].replace("shares", "")
            canonical.add(f"{currency}/share")
        elif utype == "sharesItemType" or uname == "shares":
            canonical.add("shares")
        elif uname == "pure":
            canonical.add("pure")

    # Ensure common defaults
    if not canonical:
        canonical = {"USD", "shares", "pure", "USD/share"}

    return canonical
