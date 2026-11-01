# FinancialFilings coverage check

Snapshot: 2026-08-09

## Result

| Item | Count |
|---|---:|
| Live Redis universe | 783 |
| Confirmed in FinancialFilings | 746 |
| Unresolved identifiers | 37 |
| Confirmed lower-bound coverage | 95.3% |

The 37 unresolved rows are **not proven missing**. Most are foreign-incorporated companies whose U.S.-traded CUSIP cannot be converted by adding a simple `US` prefix. No further service calls were made after this was identified.

## Assessments

- [Overall value versus Neo4j](value_vs_neo4j.md)
- [Focused Markdown and filing-label comparison](markdown_and_labels_comparison.md)
- [Financial supplements and investor presentations](supplements_and_presentations.md)
- [Picture text in SEC filings (2026-10-06)](picture_text_test_20261006.md) — no: exhibits are not converted
- [Does it make the Prepare step easier? (2026-10-06)](prepare_fidelity_check_20261006.md) — **no**: main document only, no source positions, no headings; on our 10-Q a period header is lost and comment text is printed as words

## Match evidence

| Evidence | Companies |
|---|---:|
| Exact FIGI match | 683 |
| Primary derived ISIN match | 59 |
| Secondary derived ISIN plus company-name match | 4 |
| Needs a separate identifier lookup | 37 |
| Total | 783 |

The complete company-by-company result is in [universe.md](universe.md).

## Sources and method

- The live universe came from Redis using read-only commands.
- Redis contained 783 unique symbols: 451 NYS, 328 NAS, 3 TSE, and 1 BATS.
- All 783 rows had a company name, CIK, and at least one CUSIP.
- CUSIPs were converted locally to candidate ISINs where safe.
- FinancialFilings' batch ISIN lookup was used in 11 groups of at most 100 identifiers.
- A company was confirmed only by an exact FIGI, a primary derived ISIN, or a secondary derived ISIN with a matching company name.

## Request and credit note

This coverage check made **13 FinancialFilings MCP requests**:

- 11 successful batch lookups
- 2 rejected requests that returned no data: one oversized page and one oversized identifier list

There was also **1 earlier successful connection-test request**, **2 successful requests for the value comparison**, and **3 successful supplement/presentation searches**, making **19 requests in this conversation**: 17 successful and 2 rejected.

Known successful-call cost is **28 credits**: 12 credits before the value comparison, 13 credits for one Apple filing lookup and one premium Markdown retrieval, and 3 credits for the supplement/presentation review. The MCP does not expose the account balance, and the two rejected requests may or may not have been charged.

FinancialFilings does not expose account balance or credit usage through the connected tools, so the exact number of free credits deducted is not visible here. Rejected requests may or may not count. After every future FinancialFilings use, report:

- requests made;
- successful and failed requests;
- known credit cost, if the service returns one; otherwise state that the cost is not visible.

## Pricing reference

Pay only for the API calls you make. Add a card to lift the trial cap. Usage is billed in credits, where **1 credit = $0.01**, and the first **500 credits each month are free**. There is no plan or minimum, and you can cancel anytime.

| Request type | Credits | Price |
|---|---:|---:|
| Filing metadata and search | 1 | $0.01 per request |
| Filing Markdown | 6 | $0.06 per request |
| Premium filing Markdown | 12 | $0.12 per request |
| Structured financials | 40 | $0.40 per request |

Premium filing Markdown includes annual reports, earnings releases, and transcripts.

Volume pricing:

- More than 50,000 credits per month: $0.007 per credit
- More than 500,000 credits per month: $0.005 per credit

The monthly free allowance is 500 credits.
