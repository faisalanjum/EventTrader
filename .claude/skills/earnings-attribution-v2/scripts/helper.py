#!/usr/bin/env python3
"""
Earnings Attribution Helper Script
Validates input data and checks for required fields.

Usage:
    python scripts/helper.py <accession_number>
    python scripts/helper.py validate <output_file>

Examples:
    python scripts/helper.py 0001193125-23-123456
    python scripts/helper.py validate analysis.md
"""

import sys
import re
from pathlib import Path


def validate_accession_number(accession: str) -> dict:
    """Validate SEC accession number format."""
    # Format: 0001193125-23-123456 (CIK-YY-NNNNNN)
    pattern = r'^\d{10}-\d{2}-\d{6}$'

    if not re.match(pattern, accession):
        return {
            "valid": False,
            "error": f"Invalid accession format: {accession}",
            "expected": "NNNNNNNNNN-YY-NNNNNN (e.g., 0001193125-23-123456)"
        }

    return {"valid": True, "accession": accession}


def validate_output_format(filepath: str) -> dict:
    """Validate that output file has required sections per output_template.md."""
    path = Path(filepath)

    if not path.exists():
        return {"valid": False, "error": f"File not found: {filepath}"}

    content = path.read_text()

    # Required sections per output_template.md (surprise-based, ranked confidence)
    required_sections = [
        ("# Attribution Analysis:", "Missing report title"),
        ("## Report Metadata", "Missing Report Metadata section"),
        ("## Returns Summary", "Missing Returns Summary section"),
        ("## Evidence Ledger", "Missing Evidence Ledger section"),
        ("## Executive Summary", "Missing Executive Summary section"),
        ("## Surprise Analysis", "Missing Surprise Analysis section"),
        ("## Attribution", "Missing Attribution section"),
        ("### Primary Driver", "Missing Primary Driver in Attribution"),
        ("## Data Sources Used", "Missing Data Sources Used section"),
        ("## Confidence Assessment", "Missing Confidence Assessment section"),
        ("## Historical Context", "Missing Historical Context section"),
    ]

    errors = []
    for section, error_msg in required_sections:
        if section not in content:
            errors.append(error_msg)

    # Check for surprise table (should have Expected/Actual/Surprise columns)
    if "| Metric |" not in content or "Surprise" not in content:
        errors.append("Missing surprise calculation table")

    # Check for confidence level declaration
    confidence_levels = ["High", "Medium", "Insufficient"]
    has_confidence = any(
        f"**Overall Confidence**: {level}" in content or
        f"Confidence**: {level}" in content
        for level in confidence_levels
    )
    if not has_confidence:
        errors.append("Missing confidence level (High/Medium/Insufficient)")

    # Evidence Ledger checks
    ledger_rows = 0
    ledger_valid_rows = 0
    in_ledger = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Evidence Ledger"):
            in_ledger = True
            continue
        if in_ledger and stripped.startswith("## "):
            break
        if in_ledger and stripped.startswith("|") and "Metric" not in stripped and "---" not in stripped:
            ledger_rows += 1
            cols = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cols) >= 4:
                source_val = cols[2]
                date_val = cols[3]
                if source_val and date_val and "{" not in source_val and "}" not in source_val and "{" not in date_val and "}" not in date_val:
                    ledger_valid_rows += 1

    if ledger_rows < 1:
        errors.append("Evidence Ledger has no data rows")
    if ledger_valid_rows < 1:
        errors.append("Evidence Ledger rows must include real Source + Date values (no placeholders)")

    # Check for at least 2 data sources in the Data Sources Used section
    source_rows = 0
    in_sources = False
    for line in content.splitlines():
        stripped = line.strip()
        if "Data Sources Used" in stripped:
            in_sources = True
            continue
        if in_sources and stripped.startswith("## "):
            break
        if in_sources and stripped.startswith("|") and "Source" not in stripped and "---" not in stripped:
            source_rows += 1

    if source_rows < 2:
        errors.append("Insufficient data sources documented (need at least 2)")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "message": "Output format validated successfully"}


def main():
    if len(sys.argv) < 2:
        print("Usage: python helper.py <accession_number>")
        print("       python helper.py validate <output_file>")
        sys.exit(1)

    if sys.argv[1] == "validate":
        if len(sys.argv) < 3:
            print("Error: Missing output file path")
            sys.exit(1)
        result = validate_output_format(sys.argv[2])
    else:
        result = validate_accession_number(sys.argv[1])

    if result.get("valid"):
        print("OK:", result.get("message", result.get("accession", "Valid")))
        sys.exit(0)
    else:
        print("ERROR:", result.get("error", result.get("errors", "Unknown error")))
        sys.exit(1)


if __name__ == "__main__":
    main()
