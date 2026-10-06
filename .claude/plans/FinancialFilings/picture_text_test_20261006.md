# Picture-text test (2026-10-06)

Question: does FinancialFilings already give the text inside pictures in SEC filings (our OCR need)?
Test filing: CF Industries 8-K, accession 0001104659-24-055837 (Q1 2024; EX-99.1 = slide deck as JPG images; our OCR test picture 041 is slide 14).
Access: REST API `api.financialreports.eu`, header `X-API-Key`, key in `EventMarketDB/.env` as `FINANCIALFILINGS_API_KEY` (added 2026-10-06; owner will rotate it).

| FinancialFilings record | What it is | Markdown | Slide text? |
|---|---|---|---|
| 11838012 "FORM 8-K" (ZIP, 7.1 MB) | the SEC 8-K with the image deck | 4,071 chars | **No**: the 8-K cover only; the EX-99.1 slide images are absent |
| 59211457 "Q1 2024 (Presentation)" (PDF from the company, not SEC) | the same deck as a PDF | 40,081 chars | **Yes**, with flaws (below) |

Slide 14 (sensitivity table) in the PDF Markdown vs the picture:
- all 49 values right;
- column title split across cells: `|CF|Realized|Natural Ga|s Cost ($/|MMBtu)|`;
- row title "CF Realized Urea Price ($/ton)" missing, so the reader cannot tell the $300-$600 rows are urea prices;
- chart slides: text read from pictures (marked `<!-- End of picture text -->`, 17 times), but axis numbers and labels run together.

Verdict: it does not cover SEC filings whose content is pictures (it skips the exhibit images). It helps only when the company also posted a PDF of the deck, and even then relationships (titles, axes) can be lost. Our OCR route stays needed.

Calls: company lookup by CIK, one filing list, two Markdown retrievals (all 200); two earlier searches timed out (503). Credits are not shown in the response headers; at list price about 26 credits at most, within the 500 free each month.

## Second pass (owner: "are you 100% certain?"), same day, no credits used

- **Whole API checked** (OpenAPI schema v1.4.0, 51 endpoints, every description): the only content endpoint is `/filings/{id}/markdown/` (`format=md|json`; json wraps the same text). No endpoint, field or description mentions images, OCR, pictures, charts or exhibits. Docs pages (developers, reference, nlp-ready-filings, mcp) read raw: same.
- **Package checked** (`document` link, public CDN, not an API call): record 11838012 is accession 0001104659-24-055837 (40 files, 25 JPG slides; `exhibits/tm2413105d1_ex99-1img014.jpg` = our picture 041, same bytes). FinancialFilings' Markdown converts only `main_document/tm2413105d1_8k.htm`; `exhibits/tm2413105d1_ex99-1.htm` is not converted at all.
- **Found:** that exhibit page carries the filer's own hidden text layer: after each slide image a 1-px white paragraph with the slide's text (slide 14: all 49 values, "CF Realized Urea Price", "$725M"), in shuffled order and with some split words ("n itr ogen"). Not yet measured how common this is across our pictures.

**Correction (same day, after the offline replay):** that slide text is not hidden by the grader's visibility rules (tiny or white text is still drawn), and the HTML route already outputs it. On scanned pages it is itself an OCR layer with errors, so it is not always exact. Details: PrepareTools.md, "Filer's slide text beside pictures".
