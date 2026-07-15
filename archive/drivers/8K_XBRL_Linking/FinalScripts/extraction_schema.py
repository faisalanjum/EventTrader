"""
Extraction Schema for 8-K XBRL Fact Extraction

Data classes representing:
- RawExtraction: Output from LangExtract (before validation)
- ProcessedFact: After post-processing (with value_parsed, status, etc.)
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ExtractionStatus(Enum):
    """Status of a processed extraction."""
    COMMITTED = "COMMITTED"          # High confidence, auto-link to Neo4j
    CANDIDATE_ONLY = "CANDIDATE_ONLY"  # Low confidence or UNMATCHED, needs review
    REVIEW = "REVIEW"                # Parse failure or validation error


@dataclass
class RawExtraction:
    """
    Raw extraction output from LangExtract.

    These are the LLM-provided attributes before any validation.
    """
    # Core extraction (from LangExtract)
    extraction_text: str
    char_start: int
    char_end: int

    # LLM-provided matching
    concept_top1: str                    # Best match qname OR "UNMATCHED"
    matched_period: str                  # "YYYY-MM-DD" or "YYYY-MM-DD→YYYY-MM-DD"
    matched_unit: str                    # Unit from catalog UNITS section
    confidence: float                    # 0.0 to 1.0
    reasoning: str                       # Brief explanation

    # Optional fields (with defaults)
    concept_top2: Optional[str] = None   # Second best qname (optional)
    matched_dimension: Optional[str] = None  # When fact is segmented
    matched_member: Optional[str] = None     # When fact is segmented


@dataclass
class ProcessedFact:
    """
    Fully processed and validated extraction.

    Includes all original fields plus post-processing additions.
    """
    # === Original extraction fields ===
    extraction_text: str
    char_start: int
    char_end: int

    # === Validated/normalized matching ===
    concept_top1: str                    # Validated qname or "UNMATCHED"
    matched_period: str                  # Normalized period
    matched_unit: str                    # Unit from catalog UNITS section
    confidence: float
    reasoning: str

    # Optional fields
    concept_top2: Optional[str] = None   # Validated qname or None
    matched_dimension: Optional[str] = None
    matched_member: Optional[str] = None

    # === Post-processing additions ===
    value_parsed: Optional[float] = None  # Deterministically parsed from extraction_text
    committed: bool = False               # True if auto-linking to Neo4j
    status: ExtractionStatus = ExtractionStatus.CANDIDATE_ONLY

    # Validation flags (for debugging/review)
    qname_valid: bool = True              # Was concept_top1 in valid set?
    unit_valid: bool = True               # Was matched_unit in canonical set?
    period_normalized: bool = False       # Was period format normalized?
    parse_error: Optional[str] = None     # Error message if parsing failed


@dataclass
class ExtractionResult:
    """
    Complete result from extraction pipeline.

    Contains all processed facts plus metadata about the extraction run.
    """
    # Identification
    cik: str
    company_name: str
    filing_id: Optional[str] = None

    # Results
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
        self.total_extracted = len(self.facts)
        self.committed_count = sum(1 for f in self.facts if f.status == ExtractionStatus.COMMITTED)
        self.candidate_count = sum(1 for f in self.facts if f.status == ExtractionStatus.CANDIDATE_ONLY)
        self.review_count = sum(1 for f in self.facts if f.status == ExtractionStatus.REVIEW)


# Type alias for clarity
UNMATCHED = "UNMATCHED"
