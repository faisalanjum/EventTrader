# Financial supplements and investor presentations

Snapshot: 2026-08-09

## Decision

FinancialFilings does **not** provide a strong new financial-supplement source for the current U.S. universe. Most useful supplements are already filed as SEC `EX-99.x` exhibits and stored in Neo4j.

It has one narrow potential benefit for investor presentations:

1. converting PDF exhibits that the local pipeline currently stores as unreadable bytes; and
2. finding presentations posted only on company investor-relations websites rather than filed with the SEC.

The vendor's presentation and supplement labels are too noisy to trust as a bulk feed. Keep it as an on-demand fallback, not a regular integration.

## What Neo4j already has

The live graph contains 38,946 exhibit-content nodes.

| Exhibit | Count |
|---|---:|
| `EX-99.1` | 18,449 |
| `EX-99.2` | 3,592 |
| `EX-99.3` | 541 |

Keyword checks found:

- 1,669 exhibits mentioning an investor presentation, investor day, or investor update;
- 5,345 exhibits mentioning financial or supplemental information; and
- clear quarterly supplements for Digital Realty, VICI, Realty Income, Kilroy, Brixmor, Raymond James, and others.

These are keyword matches, not perfect document classifications. They prove that the content class is already present in the graph.

Examples from the live graph:

| Company | Local evidence |
|---|---|
| Digital Realty | 14 exhibit matches for financial supplements |
| VICI | 26 supplement matches and 2 presentation matches |
| Realty Income | 9 supplement matches and 2 presentation matches |
| American Tower | 35 presentation matches |
| Goldman Sachs | 4 presentation matches |

The earnings workflow already reads `EX-99.1` fully and retains other `EX-99.x` exhibits for reference. Therefore, SEC-filed earnings releases, supplements, and presentations are not a new source category.

## The real local gap: binary PDFs

The exhibit downloader treats every response as text. For a PDF, it stores content beginning with `%PDF` followed by compressed binary characters.

The live graph contains **204 PDF-like exhibit nodes** in this unusable form. Confirmed examples include LULU, DELL, TRIP, MET, and other universe companies.

This means the graph may know that a presentation exists and retain its filing relationship, while being unable to search or read the slides. FinancialFilings Markdown conversion could be useful for these specific documents.

The smaller long-term fix is to detect PDF content and parse it correctly in the local exhibit pipeline. That would repair the existing source rather than paying repeatedly for the same SEC document.

## What the FinancialFilings searches returned

Three metadata-only MCP searches were made.

### U.S. investor presentations

FinancialFilings reported 29,885 records labelled `IP`.

The newest 100 contained:

| File package | Records |
|---|---:|
| ZIP | 78 |
| PDF | 18 |
| MP3 | 4 |

The results mixed genuine earnings presentations with Form 424B3 prospectuses, free-writing prospectuses, ordinary 8-K packages, and MP3 files. Therefore, 29,885 is not a reliable count of genuine slide presentations.

Some real issuer-hosted presentations were present, including recent Kraft Heinz, Celanese, KKR, and Light & Wonder documents. A presentation published only on an investor-relations site would be absent from the current SEC-only pipeline and could be genuinely incremental.

### U.S. financial supplement data

FinancialFilings reported 339 records labelled `XLSX`, but the newest 100 contained:

| File package | Records |
|---|---:|
| ZIP | 58 |
| PDF | 29 |
| XLS | 4 |
| XLSX | 3 |
| XML | 3 |
| HTML | 3 |

The label means “financial supplement data”; it does not mean the record is an Excel spreadsheet. Many results were ordinary SEC filing packages or PDFs.

One example was PNC's first-quarter 2026 financial supplement. The [original SEC filing](https://www.sec.gov/Archives/edgar/data/713676/000071367626000026/0000713676-26-000026-index.htm) shows that it is already `EX-99.2` inside an 8-K. The local pipeline is designed to ingest that exhibit, so FinancialFilings does not provide a new underlying source.

### Digital Realty universe check

A company-specific search returned 15 FinancialFilings records:

- all 15 were labelled investor presentations;
- all were old SEC 8-K or Form 425 ZIP packages from 2013-2020; and
- no financial-supplement records were returned.

Neo4j already contains 14 Digital Realty supplement matches from the current local period. This shows that the vendor taxonomy can miss supplements we already have while classifying old SEC packages as presentations.

## Exact value to us

| Possible use | Value |
|---|---|
| SEC-filed HTML supplement | None or very low; already ingested |
| SEC-filed HTML presentation | None or very low; already ingested |
| SEC-filed PDF presentation | Useful fallback because local PDF text is broken |
| Issuer-site-only presentation | Potentially useful and genuinely new |
| Actual standalone XLS/XLSX supplement | Potentially useful, but rare in the tested U.S. results |
| Vendor presentation/supplement label | Too noisy for automated bulk use |

## Recommended rule

```text
Is it already a readable EX-99 exhibit? ---- yes --> use Neo4j
                 |
                 no
                 v
Is the local exhibit an unreadable PDF? ---- yes --> use FinancialFilings once
                 |
                 no
                 v
Is it posted only on the issuer's IR site? - yes --> consider FinancialFilings
                 |
                 no
                 v
No added value
```

Do not bulk-fetch the vendor's `IP` or `XLSX` categories. Search for a specific company and period only when the normal SEC packet is missing a needed presentation or contains an unreadable PDF.

## Credit note

This review made **3 successful filing-metadata searches**, used **3 credits**, and had **0 failures**. No Markdown or document-content request was made.
