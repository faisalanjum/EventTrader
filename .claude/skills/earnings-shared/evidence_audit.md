# Evidence Audit Checklist (Required)

Use this before finalizing any report. If any box fails, downgrade confidence or mark Insufficient.

## Evidence Ledger Rules
- Every numeric claim appears in the Evidence Ledger—including numbers in Contributing Factors, Historical Context, and Notes.
- Every ledger entry has a source and date.
- Derived numbers list inputs + formula in Notes. Verify arithmetic: re-compute to confirm the result is correct.
- Qualitative claims (e.g., "second-highest ever") don't require ledger entry, but the underlying number does.
- Temporal claims (e.g., "highest in X years", "Nth consecutive") require source + date in Notes.
- Guidance entries must include the covered period (FY/Q), even when it differs from the filing period.
- All numeric values in Executive Summary, Surprise Analysis, Attribution, and Confidence must match the Evidence Ledger (no drift or alternate figures).
- If consensus sources conflict, explicitly pick one value (with rationale) and recompute all surprises using it; note the alternate in Notes.

## Comparison Rules
- Compare like-for-like only (same fiscal period and same metric definition).
- Cross-period comparisons are labeled “context only” and never used for surprise.

## Returns Integrity
- Returns use `daily_stock IS NOT NULL` and `NOT isNaN(...)`.

## Source Integrity
- Primary driver has at least one primary filing quote plus one independent confirmation.
- Conflicts are explicitly noted (no silent selection).
- Evidence Ledger sources must be consistent with Data Sources Used claims (e.g., if ledger cites News, don't claim Perplexity in Data Sources).
- If Data Sources marks a source "Used", the report must contain at least one explicit citation (quote, excerpt, or specific reference) from that source.

## Output Integrity
- Evidence Ledger is complete and referenced in Surprise Analysis and Attribution.
- Historical Context contains only evidence-backed claims.
- Calculated values must be labeled as calculated; do not present computed numbers as quoted source statements.

## Completeness Check
- Surprise Analysis table values must match Evidence Ledger values exactly (no inline rounding).
- If a number appears anywhere in the report, it exists in the ledger.
