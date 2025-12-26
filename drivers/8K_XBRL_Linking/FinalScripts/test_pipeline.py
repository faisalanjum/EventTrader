#!/usr/bin/env python3
"""
Test Script for 8-K XBRL Extraction Pipeline

Run tests step-by-step:
    python test_pipeline.py --unit          # Unit tests (no Neo4j/LLM)
    python test_pipeline.py --postprocess   # Test postprocessor with mock data
    python test_pipeline.py --catalog DELL  # Test catalog fetch from Neo4j
    python test_pipeline.py --extract DELL  # Full pipeline with real 8-K

Requirements:
    pip install langextract neo4j python-dotenv
"""

import sys
import os
import argparse
from typing import Set

# Ensure imports resolve from FinalScripts and Experiments directories
BASE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS_DIR = os.path.abspath(os.path.join(BASE, "..", "Experiments"))
sys.path.insert(0, BASE)
sys.path.insert(0, EXPERIMENTS_DIR)

# =============================================================================
# UNIT TESTS - No external dependencies
# =============================================================================

def test_value_parsing():
    """Test priority-based value parsing."""
    from postprocessor import parse_number_from_text

    tests = [
        # (text, unit, expected_value, description)
        ("net income of $2.75 billion", None, 2_750_000_000, "Currency + multiplier"),
        ("revenue increased 10% to $2.75 billion", None, 2_750_000_000, "Priority over percentage"),
        ("($2.3 billion)", None, -2_300_000_000, "Parentheses negative"),
        ("loss of ($450 million)", None, -450_000_000, "Parentheses negative with context"),
        ("EPS of $4.80", None, 4.80, "Small currency amount"),
        ("$2,750,000,000 in assets", None, 2_750_000_000, "Large number with commas"),
        ("2.75 billion shares", None, 2_750_000_000, "Multiplier without currency"),
        ("margin of 23.5%", "pure", 0.235, "Percentage with ratio unit"),
        ("margin of 23.5%", "USD", None, "Percentage rejected for USD"),
        ("reported in 2024", None, 2024, "Year as fallback"),
        ("grew 15.5% in 2024", None, 15.5, "Prefer decimal over year"),
        ("(10%) decline", None, None, "Percentage in parens - not negative"),
    ]

    print("\n=== VALUE PARSING TESTS ===\n")
    passed = 0
    failed = 0

    for text, unit, expected, desc in tests:
        value, error = parse_number_from_text(text, unit)

        if expected is None:
            success = value is None or error is not None
        else:
            success = value is not None and abs(value - expected) < 0.01

        status = "✓" if success else "✗"
        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status} {desc}")
        print(f"  Input: \"{text}\" (unit={unit})")
        print(f"  Expected: {expected}, Got: {value}")
        if error:
            print(f"  Error: {error}")
        print()

    print(f"Results: {passed}/{passed+failed} passed")
    return failed == 0


def test_period_normalization():
    """Test period normalization and validation."""
    from postprocessor import normalize_period, validate_period

    tests = [
        # (input, expected_normalized, should_be_valid, description)
        ("2024-12-31", "2024-12-31", True, "Instant - no change"),
        ("2024-01-01→2024-12-31", "2024-01-01→2024-12-31", True, "Duration - no change"),
        ("2024-06-30→2024-06-30", "2024-06-30", True, "Same start/end → instant"),
        ("2024-01-01-->2024-12-31", "2024-01-01→2024-12-31", True, "Arrow variant -->"),
        ("2024-01-01->2024-12-31", "2024-01-01→2024-12-31", True, "Arrow variant ->"),
        ("2024-01-01 - 2024-12-31", "2024-01-01→2024-12-31", True, "Arrow variant ' - '"),
        ("2024-01-01 → 2024-12-31", "2024-01-01→2024-12-31", True, "Spaces around arrow"),
        ("2024-01-01 to 2024-12-31", "2024-01-01→2024-12-31", True, "Arrow variant ' to '"),
        ("invalid", "invalid", False, "Invalid format"),
        ("2024-13-01", "2024-13-01", False, "Invalid month"),
    ]

    print("\n=== PERIOD NORMALIZATION TESTS ===\n")
    passed = 0
    failed = 0

    for input_period, expected, should_be_valid, desc in tests:
        normalized, was_normalized = normalize_period(input_period)
        is_valid = validate_period(normalized)

        success = (normalized == expected) and (is_valid == should_be_valid)
        status = "✓" if success else "✗"

        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status} {desc}")
        print(f"  Input: \"{input_period}\"")
        print(f"  Normalized: \"{normalized}\" (changed={was_normalized})")
        print(f"  Valid: {is_valid} (expected {should_be_valid})")
        print()

    print(f"Results: {passed}/{passed+failed} passed")
    return failed == 0


def test_qname_validation():
    """Test qname validation against catalog."""
    from postprocessor import validate_qname

    valid_qnames = {
        "us-gaap:Revenues",
        "us-gaap:NetIncomeLoss",
        "us-gaap:Assets",
        "ice:TransactionRevenue",
    }

    tests = [
        # (qname, expected_result, expected_valid, description)
        ("us-gaap:Revenues", "us-gaap:Revenues", True, "Valid qname"),
        ("us-gaap:NetIncomeLoss", "us-gaap:NetIncomeLoss", True, "Valid qname"),
        ("us-gaap:FakeConceptXYZ", "UNMATCHED", False, "Invalid qname → UNMATCHED"),
        ("UNMATCHED", "UNMATCHED", True, "UNMATCHED passthrough"),
        ("", "UNMATCHED", False, "Empty string → UNMATCHED"),
    ]

    print("\n=== QNAME VALIDATION TESTS ===\n")
    passed = 0
    failed = 0

    for qname, expected_result, expected_valid, desc in tests:
        result, was_valid = validate_qname(qname, valid_qnames)

        success = (result == expected_result) and (was_valid == expected_valid)
        status = "✓" if success else "✗"

        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status} {desc}")
        print(f"  Input: \"{qname}\"")
        print(f"  Result: \"{result}\" (valid={was_valid})")
        print()

    print(f"Results: {passed}/{passed+failed} passed")
    return failed == 0


def test_status_determination():
    """Test status determination logic."""
    from postprocessor import determine_status
    from extraction_schema import ExtractionStatus

    tests = [
        # (concept, confidence, value, period_valid, qname_valid, unit_valid, expected_status, desc)
        ("us-gaap:Revenues", 0.95, 1000.0, True, True, True, ExtractionStatus.COMMITTED, "High confidence valid"),
        ("us-gaap:Revenues", 0.85, 1000.0, True, True, True, ExtractionStatus.CANDIDATE_ONLY, "Below threshold"),
        ("UNMATCHED", 0.95, 1000.0, True, True, True, ExtractionStatus.CANDIDATE_ONLY, "UNMATCHED concept"),
        ("us-gaap:Revenues", 0.95, None, True, True, True, ExtractionStatus.REVIEW, "Parse failed"),
        ("us-gaap:Revenues", 0.95, 1000.0, False, True, True, ExtractionStatus.REVIEW, "Invalid period"),
        ("us-gaap:Revenues", 0.95, 1000.0, True, True, False, ExtractionStatus.REVIEW, "Invalid unit"),
        ("us-gaap:FakeConcept", 0.95, 1000.0, True, False, True, ExtractionStatus.CANDIDATE_ONLY, "Invalid qname"),
    ]

    print("\n=== STATUS DETERMINATION TESTS ===\n")
    passed = 0
    failed = 0

    for concept, conf, value, period_v, qname_v, unit_v, expected, desc in tests:
        status, committed = determine_status(concept, conf, value, period_v, qname_v, unit_v)

        success = status == expected
        status_str = "✓" if success else "✗"

        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status_str} {desc}")
        print(f"  Got: {status.value}, Expected: {expected.value}")
        print()

    print(f"Results: {passed}/{passed+failed} passed")
    return failed == 0


def run_unit_tests():
    """Run all unit tests."""
    print("\n" + "=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    results = [
        ("Value Parsing", test_value_parsing()),
        ("Period Normalization", test_period_normalization()),
        ("Qname Validation", test_qname_validation()),
        ("Status Determination", test_status_determination()),
    ]

    print("\n" + "=" * 60)
    print("UNIT TEST SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    return all_passed


# =============================================================================
# POSTPROCESSOR TEST - With mock LangExtract output
# =============================================================================

def test_postprocessor():
    """Test postprocessor with mock RawExtraction data."""
    from extraction_schema import RawExtraction, ExtractionStatus
    from postprocessor import postprocess

    print("\n" + "=" * 60)
    print("TESTING POSTPROCESSOR WITH MOCK DATA")
    print("=" * 60)

    # Mock catalog data
    valid_qnames = {
        "us-gaap:Revenues",
        "us-gaap:NetIncomeLoss",
        "us-gaap:EarningsPerShareDiluted",
        "us-gaap:Assets",
    }
    valid_units = {"USD", "USD/share", "shares", "pure"}

    # Mock extractions (as if from LangExtract)
    raw_extractions = [
        RawExtraction(
            extraction_text="net income of $2.75 billion for fiscal year 2024",
            char_start=100,
            char_end=150,
            concept_top1="us-gaap:NetIncomeLoss",
            matched_period="2024-01-01→2024-12-31",
            matched_unit="USD",
            confidence=0.95,
            reasoning="Explicit net income, exact catalog match",
        ),
        RawExtraction(
            extraction_text="diluted EPS of $4.80",
            char_start=200,
            char_end=220,
            concept_top1="us-gaap:EarningsPerShareDiluted",
            matched_period="2024-01-01→2024-12-31",
            matched_unit="USD/share",
            confidence=0.92,
            reasoning="Diluted EPS value",
        ),
        RawExtraction(
            extraction_text="revenue grew to $8.5 billion",
            char_start=300,
            char_end=330,
            concept_top1="UNMATCHED",
            concept_top2="us-gaap:Revenues",
            matched_period="2024-01-01→2024-12-31",
            matched_unit="USD",
            confidence=0.60,
            reasoning="Revenue concept varies by filer",
        ),
        RawExtraction(
            extraction_text="reported loss of ($450 million)",
            char_start=400,
            char_end=435,
            concept_top1="us-gaap:NetIncomeLoss",
            matched_period="2024-04-01→2024-06-30",
            matched_unit="USD",
            confidence=0.88,
            reasoning="Quarterly net loss in parentheses",
        ),
        RawExtraction(
            extraction_text="some text without clear number",
            char_start=500,
            char_end=530,
            concept_top1="us-gaap:Assets",
            matched_period="2024-12-31",
            matched_unit="USD",
            confidence=0.70,
            reasoning="No numeric value found",
        ),
    ]

    # Run postprocessor
    processed = postprocess(raw_extractions, valid_qnames, valid_units)

    # Display results
    print(f"\nProcessed {len(processed)} facts:\n")

    for i, fact in enumerate(processed, 1):
        print(f"--- Fact {i} ---")
        print(f"  Text: \"{fact.extraction_text[:50]}...\"")
        print(f"  Concept: {fact.concept_top1}")
        print(f"  Value: {fact.value_parsed}")
        print(f"  Period: {fact.matched_period}")
        print(f"  Unit: {fact.matched_unit} (valid={fact.unit_valid})")
        print(f"  Status: {fact.status.value}")
        print(f"  Committed: {fact.committed}")
        if fact.parse_error:
            print(f"  Parse Error: {fact.parse_error}")
        print()

    # Summary
    committed = sum(1 for f in processed if f.status == ExtractionStatus.COMMITTED)
    candidate = sum(1 for f in processed if f.status == ExtractionStatus.CANDIDATE_ONLY)
    review = sum(1 for f in processed if f.status == ExtractionStatus.REVIEW)

    print(f"Summary: {committed} COMMITTED, {candidate} CANDIDATE_ONLY, {review} REVIEW")

    return True


# =============================================================================
# CATALOG TEST - Fetch from Neo4j
# =============================================================================

def test_catalog(ticker: str):
    """Test catalog fetch from Neo4j."""
    print("\n" + "=" * 60)
    print(f"TESTING CATALOG FETCH FOR {ticker}")
    print("=" * 60)

    try:
        from xbrl_catalog import xbrl_catalog, print_catalog_summary

        catalog = xbrl_catalog(ticker, limit_filings=2)
        print_catalog_summary(catalog)

        print("\n--- Valid Qnames (first 20) ---")
        for qname in list(catalog.concepts.keys())[:20]:
            print(f"  {qname}")

        print(f"\n--- Valid Units ---")
        for unit in catalog.units.keys():
            print(f"  {unit}")

        print("\n--- LLM Context Preview (first 2000 chars) ---")
        context = catalog.to_llm_context()
        print(context[:2000] + "...")

        return catalog

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# FULL PIPELINE TEST - With real 8-K
# =============================================================================

# Sample data directory
SAMPLE_DATA_DIR = "/home/faisal/EventMarketDB/drivers/8K_XBRL_Linking/sample_data"

# Default sample files (ticker -> file path)
SAMPLE_FILES = {
    "DELL": "DELL_1571996_2025-08-28_000157199625000096/exhibit_EX-99.1.txt",
}


def load_sample_8k(ticker: str = None, file_path: str = None) -> tuple:
    """
    Load sample 8-K text from file.

    Args:
        ticker: Ticker to look up in SAMPLE_FILES
        file_path: Direct path to file (overrides ticker)

    Returns:
        Tuple of (text, file_path_used)
    """
    import os

    if file_path:
        path = file_path
    elif ticker and ticker.upper() in SAMPLE_FILES:
        path = os.path.join(SAMPLE_DATA_DIR, SAMPLE_FILES[ticker.upper()])
    else:
        # List available samples
        print(f"\nAvailable samples in {SAMPLE_DATA_DIR}:")
        if os.path.exists(SAMPLE_DATA_DIR):
            for item in os.listdir(SAMPLE_DATA_DIR):
                print(f"  - {item}")
        return None, None

    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None, None

    with open(path, 'r') as f:
        text = f.read()

    return text, path


def test_full_pipeline(ticker: str, file_path: str = None):
    """Test full extraction pipeline."""
    print("\n" + "=" * 60)
    print(f"TESTING FULL PIPELINE FOR {ticker}")
    print("=" * 60)

    # Step 0: Load 8-K text
    print("\n[Step 0] Loading 8-K document...")
    text, path_used = load_sample_8k(ticker, file_path)
    if not text:
        print("  ✗ No sample file found. Use --file to specify a path.")
        return False
    print(f"  ✓ Loaded {len(text):,} chars from {path_used}")

    # Step 1: Fetch catalog
    print("\n[Step 1] Fetching XBRL catalog from Neo4j...")
    try:
        from xbrl_catalog import xbrl_catalog
        catalog = xbrl_catalog(ticker, limit_filings=2)
        print(f"  ✓ Catalog loaded: {len(catalog.concepts)} concepts, {len(catalog.units)} units")
    except Exception as e:
        print(f"  ✗ Failed to fetch catalog: {e}")
        return False

    # Step 2: Run extraction
    print("\n[Step 2] Running LangExtract on 8-K...")
    try:
        from extractor import extract_facts

        result = extract_facts(
            text=text,
            catalog=catalog,
            filing_id=path_used
        )
        print(f"  ✓ Extraction complete: {result.total_extracted} facts extracted")

    except ImportError as e:
        print(f"  ✗ Import error (is langextract installed?): {e}")
        print("\n  To install: pip install langextract")
        return False
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Display results
    print("\n[Step 3] Results:")
    print(f"  COMMITTED: {result.committed_count}")
    print(f"  CANDIDATE_ONLY: {result.candidate_count}")
    print(f"  REVIEW: {result.review_count}")

    print("\n--- Extracted Facts ---")
    for i, fact in enumerate(result.facts, 1):
        print(f"\n[{i}] {fact.status.value}")
        print(f"    Text: \"{fact.extraction_text[:60]}...\"")
        print(f"    Concept: {fact.concept_top1}")
        if fact.concept_top2:
            print(f"    Concept2: {fact.concept_top2}")
        print(f"    Value: {fact.value_parsed:,.2f}" if fact.value_parsed else "    Value: None")
        print(f"    Period: {fact.matched_period}")
        print(f"    Unit: {fact.matched_unit}")
        print(f"    Confidence: {fact.confidence:.2f}")
        print(f"    Reasoning: {fact.reasoning}")
        if fact.parse_error:
            print(f"    Parse Error: {fact.parse_error}")

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test 8-K XBRL Extraction Pipeline")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--postprocess", action="store_true", help="Test postprocessor with mock data")
    parser.add_argument("--catalog", type=str, help="Test catalog fetch for ticker (e.g., DELL)")
    parser.add_argument("--extract", type=str, help="Test full pipeline for ticker (e.g., DELL)")
    parser.add_argument("--file", type=str, help="Path to 8-K file (use with --extract)")
    parser.add_argument("--all", type=str, help="Run all tests for ticker")

    args = parser.parse_args()

    # Default to showing help
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n\nQuick start:")
        print("  python test_pipeline.py --unit              # Unit tests (no deps)")
        print("  python test_pipeline.py --postprocess       # Mock postprocessor test")
        print("  python test_pipeline.py --catalog DELL      # Test Neo4j catalog")
        print("  python test_pipeline.py --extract DELL      # Full pipeline (uses sample_data)")
        print("  python test_pipeline.py --extract DELL --file /path/to/8k.txt")
        print("  python test_pipeline.py --all DELL          # Run everything")
        return

    if args.unit or args.all:
        run_unit_tests()

    if args.postprocess or args.all:
        test_postprocessor()

    if args.catalog:
        test_catalog(args.catalog)
    elif args.all:
        test_catalog(args.all)

    if args.extract:
        test_full_pipeline(args.extract, args.file)
    elif args.all:
        test_full_pipeline(args.all, args.file)


if __name__ == "__main__":
    main()
