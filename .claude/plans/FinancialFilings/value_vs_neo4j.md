# FinancialFilings value versus the current Neo4j database

Snapshot: 2026-08-09

## Decision

Use FinancialFilings, exposed here through the `FinancialReports` MCP, as an **on-demand add-on**. Do not copy its full feed into Neo4j and do not replace the current SEC pipeline.

Its clearest added value is:

1. Markdown that keeps filing tables readable.
2. Global filings and a common filing-type system across regulators.
3. ISIN, LEI, FIGI, legal-entity, and international listing data.
4. Simple, standardized financial statements for supported European companies.
5. Newer filing discovery when the local graph is behind.

The current database is still clearly better for detailed SEC facts, company-event links, price reactions, transcript Q&A, and queries across connected data.

## What is already in Neo4j

These are live read-only counts, not estimates from code.

| Source or derived layer | Live data | What it adds |
|---|---:|---|
| SEC filings through SEC-API | 42,633 reports | Filing metadata, sections, exhibits, text, statement JSON, and detailed XBRL |
| Benzinga | 348,670 news items | News body, tags, channels, companies, and event returns |
| EarningsCall API | 9,608 transcripts | Prepared remarks and speaker-level Q&A |
| Polygon | 4,556 dividends; 40 splits | Corporate actions and price data used for event returns |
| Derived transcript layer | 170,654 Q&A exchanges | Ordered speaker exchanges; 170,328 have embeddings |
| Derived risk layer | 39,821 risk classifications | Searchable filing-risk analysis |
| Event links | 1,560,935 `INFLUENCES` links | Company, sector, industry, and market returns after each event |

Redis is the working queue and cache. It is not another original data source. OpenAI is used for derived labels and embeddings, not as the source of a filing or market fact.

The live Redis universe contains 783 companies. Neo4j contains 796 company nodes, including old or extra rows. Of those, 795 have at least one report.

### Filing coverage in the live graph

| Form | Reports |
|---|---:|
| 8-K | 29,672 |
| 10-Q | 7,301 |
| 10-K | 2,993 |
| 425 | 1,206 |
| 8-K/A | 631 |
| Schedule 13D/A | 531 |
| Other accepted forms | 299 |
| **Total** | **42,633** |

There are only 12 stored SEC form types. The graph has no 20-F, proxy, Form 4, ESG, AGM, debt, dividend, or general foreign-regulator filing collection.

The local snapshot currently stops at **2026-04-28** for reports and news. FinancialFilings says it refreshes daily, and its coverage page showed filings through 2026-08-08 when checked. That makes it a useful freshness fallback in this environment.

## How a filing is stored now

```text
Company <- PRIMARY_FILER - Report
                           |-- HAS_SECTION --> plain-text filing sections
                           |-- HAS_EXHIBIT --> plain-text exhibits
                           |-- HAS_FILING_TEXT --> plain full filing text
                           |-- HAS_FINANCIAL_STATEMENT --> raw SEC tag JSON
                           |-- HAS_XBRL --> filing XBRL root
                           |                 ^
                           |                 |-- REPORTS -- Fact
                           |                                  |-- Concept
                           |                                  |-- Context / period / unit
                           |                                  |-- Dimension / member
                           |                                  |-- Calculation / presentation links
                           |-- INFLUENCES --> company / sector / industry / market
                                                with event returns
```

Live content coverage:

| Stored content | Reports with it | Share of reports |
|---|---:|---:|
| Named sections | 40,678 | 95.4% |
| Exhibits | 25,262 | 59.3% |
| Full filing text node | 2,689 | 6.3% |
| Four-statement SEC JSON | 10,029 | 23.5% |
| Detailed XBRL graph | 10,468 | 24.6% |

The XBRL layer is substantial: 13,775,616 facts, 618,754 concepts, 4,712,054 contexts, and 955,960 dimensions. It keeps issuer tags, values, periods, units, dimensions, members, and calculation and presentation links. This is more detailed than a fixed normalized statement.

The weaker local format is the reading layer. Sections and non-section filings are plain text. Financial statement nodes are large JSON objects keyed by SEC tags, so a simple peer comparison needs tag mapping and period-selection logic.

## What FinancialFilings adds

The vendor documentation describes:

- about 80,000 companies across roughly 60 markets and 80 regulator sources;
- 11 broad disclosure groups and 31 common report types;
- filings searchable by company, country, regulator, filing type, language, date, fiscal period, ISIN, and LEI;
- filing content converted to GitHub-style Markdown;
- 126 normalized financial line items arranged like a standard income statement, balance sheet, and cash-flow statement;
- point-in-time financial queries and separate source filings for restatements;
- daily filing refreshes.

Important limits:

- The MCP tool itself says structured financials are currently mainly ESEF/European data and are often empty for U.S. SEC companies.
- The normalized feed is easier to use but loses the long tail of issuer-specific facts and XBRL relationships kept in Neo4j.
- The MCP can search inside one filing, while Neo4j already has full-text indexes across all sections, exhibits, filing text, facts, news, and transcripts.
- Vendor marketing says headings are preserved, but the live Apple test below did not produce semantic Markdown headings in the first 50,000 characters.

## Exact structure and format comparison

| Need | Better source | Exact reason |
|---|---|---|
| Read a table in a filing | FinancialFilings | Markdown table columns are preserved; local section text flattens the layout |
| Jump directly to a known 10-K/10-Q/8-K item | Neo4j | Each item is already a separate named section node |
| Search all local filing content | Neo4j | Live full-text indexes cover sections, exhibits, filing text, financial JSON, and text facts |
| Read one long filing with less cleanup | FinancialFilings | It removes repeated page noise and keeps Markdown tables and emphasis |
| Depend on semantic heading levels | Neither is complete | Neo4j has explicit SEC item nodes; the tested vendor sample had no `#` headings |
| Compare standard line items across supported European companies | FinancialFilings | The response is already organized as period -> statement -> line item, with depth and parent fields |
| Inspect an issuer-specific SEC fact | Neo4j | It keeps the raw tag, context, period, unit, dimensions, members, and calculation links |
| Reproduce a point-in-time normalized comparison | FinancialFilings | It has an `as_of` view and lists contributing source filings |
| Trace a raw SEC fact to its filing | Neo4j | Every fact links back to its filing; the original SEC URLs are stored |
| Trace a normalized number to its source | FinancialFilings | Its statement response can include `source_filing` and `sources`, subject to source-unmasking access |
| Classify filings across countries | FinancialFilings | One common hierarchy covers financial reporting, ESG, governance, debt, M&A, dividends, and more |
| Link a disclosure to market reaction | Neo4j | The graph already stores stock, sector, industry, and market returns on event links |
| Analyze earnings-call dialogue | Neo4j | Q&A is split into ordered speaker exchanges and nearly all exchanges have embeddings |
| Resolve international entities and listings | FinancialFilings | It exposes ISIN, LEI, FIGI, legal address, legal form, exchanges, and indices; the live Company nodes mainly have ticker and CIK |

### Is their format better?

**For reading and model input: partly yes.** Preserved Markdown tables are a real improvement over the local plain text. A standard 126-line-item statement is also much easier to feed into a comparison than raw SEC tags.

**For data meaning and detail: no.** The current XBRL graph is richer. It keeps facts that do not fit the vendor's standard list and retains contexts, dimensions, units, issuer extensions, and statement relationships.

**For filing navigation: mixed.** FinancialFilings has cleaner documents, but the actual Apple sample did not use Markdown heading levels. The current graph's explicit SEC item nodes are more reliable for queries such as “all Risk Factors sections.”

## Best incremental uses

### 1. On-demand Markdown for table-heavy filings

Use FinancialFilings only when local plain text loses a table or layout that matters. One annual report lookup plus premium Markdown costs 13 credits. Do not download every 10-K or 10-Q again.

### 2. Fill filing-type gaps

Use it for documents the current allow-list does not ingest: foreign annual reports, 20-F, proxy and governance documents, ESG reports, dividend notices, debt documents, and broader M&A disclosures.

### 3. Add stable international identifiers

The strongest metadata gain is ISIN/LEI/FIGI and legal-entity data. This would improve matching for the 37 unresolved universe companies and reduce ticker-based mistakes. Store it locally only after a separate, approved database-write plan.

### 4. Use normalized financials only for a named comparison

The 40-credit endpoint is worthwhile when a supported European company or a cross-country peer comparison is the actual task. It is not a good default for this mostly U.S.-listed universe, and it should not replace the detailed SEC XBRL graph.

### 5. Use it as a freshness fallback

When the local ingestion is behind, query FinancialFilings for the latest document and keep the public source link. The permanent fix for a stale local pipeline is still to repair the local ingestion, not to make paid calls forever.

## What not to buy twice

- Routine U.S. SEC filing metadata already present in Neo4j.
- All-company bulk Markdown when only a few tables need better formatting.
- U.S. structured financials without first knowing the company is supported.
- Earnings transcripts already stored as speaker-level Q&A.
- Market-return calculations already connected to news, reports, and transcripts.

## Smallest useful operating rule

```text
Need a document the graph lacks? -------- yes --> use FinancialFilings metadata
             |
             no
             v
Did local plain text lose a needed table? yes --> retrieve that one Markdown filing
             |
             no
             v
Need normalized European peer numbers? -- yes --> consider one 40-credit call
             |
             no
             v
Use Neo4j
```

This keeps FinancialFilings as a targeted quality and coverage layer. It avoids creating a second copy of data the graph already models better.

## Final live MCP check

The final test used the same Apple 2025 10-K already present in Neo4j:

- Local report: SEC accession `0000320193-25-000079`, released 2025-10-31.
- FinancialFilings record: filing ID `9293573`, also released 2025-10-31.
- Returned sample: 50,390 characters and 327 lines.
- Markdown evidence: 49 table rows and 4 table separators in the returned sample.
- Heading evidence: zero `#`-style Markdown headings in the returned sample.
- Result: tables were materially better than local plain text, but section structure was not better than the graph's explicit item nodes.

Credit use for this review:

| Call | Result | Credits |
|---|---|---:|
| Latest Apple 10-K metadata | Success | 1 |
| Apple 10-K premium Markdown | Success | 12 |
| Structured financials | Skipped | 0 |
| **Total** | **2 successful calls** | **13** |

At list price this is $0.13 and 2.6% of the 500-credit monthly free allowance. Across the earlier coverage work and this review, known successful calls account for **25 credits**. The MCP does not show the account balance, and the two earlier rejected requests may or may not have been charged.

## Sources

- [FinancialFilings MCP](https://financialfilings.com/mcp/)
- [Developer documentation](https://financialfilings.com/developers/)
- [Company and filing coverage](https://financialfilings.com/companies/stats/)
- [Financial Reporting Classification Framework](https://financialfilings.com/financial-reporting-classification-framework/)
- [Filing types](https://financialfilings.com/filings/filing-types/)
- [Standardized financials](https://financialfilings.com/standardized-financials/)
- [NLP-ready filing Markdown](https://financialfilings.com/nlp-ready-filings/)
- [Pay-as-you-go pricing](https://financialfilings.com/payg/?source=footer)
- [Local data-flow overview](../../../docs/data_flow.md)
- [Local SEC enrichment code](../../../redisDB/ReportProcessor.py)
- [Local graph node definitions](../../../neograph/EventTraderNodes.py)
- [Local graph report writer](../../../neograph/mixins/report.py)
