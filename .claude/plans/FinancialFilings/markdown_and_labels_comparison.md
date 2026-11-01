# FinancialFilings Markdown and filing labels versus Neo4j

Snapshot: 2026-08-09

## Short answer

FinancialFilings Markdown is **meaningfully better for tables**, but it is not better in every way.

- FinancialFilings is better when a person or model must understand rows and columns.
- Neo4j is better when the task starts with a known SEC section such as Risk Factors or Management Discussion.
- Neo4j XBRL is better for exact financial facts and calculations.
- FinancialFilings' common labels are useful for mixing filings from different countries. They add little for the current SEC-only forms.

The practical rule is: **pay for their Markdown only when layout matters, and add their common label beside the raw SEC form rather than replacing it.**

## Same Apple 2025 10-K: exact comparison

### What Neo4j has

The Apple filing is `0000320193-25-000079`.

| Local structure | Result |
|---|---:|
| Named section nodes | 21 |
| Section text | 202,390 characters |
| Markdown table rows | 0 |
| HTML tables | 0 |
| Full filing text node | 0 |
| Raw financial statement JSON nodes | 4 |

The local graph is excellent at section lookup. For example, Risk Factors, Business, Cybersecurity, and Management Discussion are separate nodes.

The problem is table layout. The local financial section contains a table boundary, but the rows and columns are flattened:

```text
##TABLE_START Years ended September 27, 2025 September 28, 2024 ...
Net sales: Products $307,003 $294,866 $298,085 Services 109,158 ...
##TABLE_END
```

The numbers are present, but a reader or model must infer which number belongs to which year and row.

### What FinancialFilings has

The matching FinancialFilings record is filing `9293573`. Its Markdown keeps the same statement as a real table:

| Net sales | 2025 | 2024 | 2023 |
|---|---:|---:|---:|
| Products | $307,003 | $294,866 | $298,085 |
| Services | 109,158 | 96,169 | 85,200 |
| Total | 416,161 | 391,035 | 383,285 |

This is a real improvement. The year-to-value relationship is explicit, so models are less likely to attach a value to the wrong year.

The same improvement appears in the cover page, table of contents, segment sales, product sales, margins, expenses, cash flow, and footnote tables. The [public Apple filing page](https://financialfilings.com/filings/apple-inc/annual-report/2025/9293573/) shows these preserved columns.

## How different is the Markdown?

| Feature | Neo4j now | FinancialFilings | Difference that matters? |
|---|---|---|---|
| Words and narrative | Clean plain text by SEC section | Clean filing text | Small |
| Tables | Boundary markers, but rows and columns flattened | Markdown rows and columns | **Large** |
| Section lookup | Separate named nodes for 10-K, 10-Q, and 8-K items | One long document plus text search | Neo4j is better |
| Full document | Often absent as one node | Whole filing, including cover and contents | FinancialFilings is better |
| Semantic Markdown headings | Not used | Not reliable in the tested MCP output | Small or no gain |
| Exact facts | Raw statement JSON plus detailed XBRL graph | Text tables; optional normalized feed | Neo4j is richer |
| Page noise | Some page labels remain | Mostly removed | Moderate |

The paid MCP sample returned 50,390 characters with 49 table rows and four table separators. It had **zero `#`-style headings**. Therefore, “much better Markdown” is true for tables and document cleanup, but not for semantic heading structure.

### Effect on model questions

| Question | Best source |
|---|---|
| “Summarize Apple's Risk Factors” | Neo4j section node |
| “Compare 2025, 2024, and 2023 product sales” | FinancialFilings Markdown table |
| “Give every fact using a product dimension” | Neo4j XBRL graph |
| “Read the complete filing in order” | FinancialFilings Markdown |
| “Search Risk Factors across every company” | Neo4j full-text index |

## Common filing labels

### Current Neo4j labels

The live graph stores the regulator's exact SEC form in `Report.formType`. It currently has 12 values, including `10-K`, `10-Q`, `8-K`, amendments, `6-K`, `425`, Schedule 13D, and tender-offer forms.

This is precise but U.S.-specific. The graph currently has no populated common filing-category relationships.

For Apple:

```text
formType = 10-K
```

### FinancialFilings labels

FinancialFilings adds a hierarchy:

```text
broad disclosure group -> report type -> detailed publication type
11 groups                 31 types       100+ detailed labels
```

For the tested Apple filing, the MCP returned:

```text
category = Financial Reporting & Info
type code = 10-K
type name = Annual Report
```

Its 11 broad groups cover annual meetings, financial reporting, investment vehicles, investor communication, listing changes, management and pay, equity, debt, ESG, M&A/legal, and other regulatory filings. The [FRCF documentation](https://financialfilings.com/financial-reporting-classification-framework/) explains the three levels.

### Is that better than ours?

For the current U.S. filing set, **only slightly**. `10-K`, `10-Q`, and `8-K` are already exact and familiar. A broad category does not improve most current queries.

For international or mixed document sets, **yes**. A local quarterly report, a U.S. 10-Q, and another country's interim report can share a common “Interim / Quarterly Report” meaning even though their regulator codes differ.

There are three cautions:

1. Keep the raw regulator code. A common label is broader and can hide details such as amendments.
2. The labels are assigned by an automated classifier, so they are not guaranteed to be correct.
3. The vendor's public pages currently disagree on whether there are 30 or 31 active report types. The framework says 31; the filing-types page header says 30. Treat the taxonomy as versioned data.

## Recommended local design

If these labels are adopted later, keep both values:

```text
raw_form_type = 10-K
common_category = Financial Reporting
common_report_type = Annual Report
taxonomy_version = FRCF 3.0
```

For the 12 forms already accepted by the pipeline, a small local mapping is enough. There is no reason to pay for a metadata call on every existing SEC filing. FinancialFilings labels become valuable when adding non-SEC documents that do not already fit the local form list.

No Neo4j changes were made for this comparison.

## Credit note

This follow-up used **0 new FinancialFilings credits**. It reused the previously paid Apple MCP sample and read the vendor's public filing and taxonomy pages.
