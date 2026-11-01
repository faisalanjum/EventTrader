# Does FinancialFilings make the Prepare step easier? (2026-10-06, Fable)

Question: Prepare turns SEC HTML/XML filings into faithful, source-anchored evidence for a final AI reader. Could FinancialFilings' "AI-ready Markdown"
replace or shortcut that — and if their method is visible, what can we learn from it?

Method: their full API description (OpenAPI 1.4.0, 51 endpoints), developer pages, GitHub organisation and free sample files read; then two of our own
development filings fetched through the API with the owner's key and compared with the source as the browser shows it, by our scanner (`Visible`).
Folder: `prepare_work/financialfilings_20261006/` (`ff.py` client, `compare.py`, the markdowns, `calls.jsonl` with every call's rate-limit headers).

## Short answer

**No for Prepare.** Their Markdown is a plain-text conversion of the SEC package's *main document only*: no exhibits (70 % of our corpus is 8-Ks whose
content is in EX-99.x), no source positions, no headings, no pictures; and on the same 10-Q it is less faithful than our route (a period header lost,
comment text printed as words, spaces inserted inside numbers). Their method is not published; what their output shows is a generic text extraction.

## The two tests (our development filings, accession = their `source_filing_id`, so the mapping is direct)

**Berry Global 10-Q, `0001140361-25-003207` (their filing 55837417; iXBRL main document).** Markdown 68,584 characters, 370 table rows, 0 headings, 0 images.
| Measured against the source as the browser shows it | Result |
|---|---|
| source visible words present, in order | 9,171 of 9,263 = **99.0 %**; 92 missing, 111 added |
| words added that the filing never shows | the XML declaration and HTML comments printed as text: `xml version='1.0' encoding='ASCII'? Licensed to: Summit, a Broadridge Company …`, `PROfilePageNumberReset%Num%2%%%`, and `<a id="x"><!--Anchor--></a>` printed as the word **"Anchor"** — inside the company's name: `Be Anchor rry Global Group, Inc.` (lines 57, 89, 93) |
| spaces inserted at inline-tag boundaries | `1.00 %` (source `1.00%`), `( 812 ) 424-2904`, `101 Oakley Street , Evansville , Indiana , 47710` — the class of defect we just fixed in our own route (tool-added spaces) |
| table cells with text | source 1,448 (40 tables) → markdown 1,202 |
| balance-sheet period headers | source `December 28, 2024 | September 28, 2024` → markdown `December 28, 2024` only — **the second column's period is lost** |
| income-statement columns | header `Quarterly Period Ended — December 28, 2024 | December 30, 2023` in columns 2–3, values `$ 2,385 | $ | 2,333` in columns 2–4: the 2023 header does not stand over the 2023 value (the `$` cells shift rows unevenly) |
| cover facts the EdgarTools route had lost (`December 28, 2024`, `001-35672`) | present (their converter reads through the iXBRL wrappers) |
| hidden iXBRL header | not printed here; but their own free sample (`common/example_input.md`, an ESEF report) opens with 437 KB of hidden XBRL context ids on one line |
| `format=json` | the same Markdown bytes; no structure |

**State Street 8-K, `0000093751-26-000008` (their filing 17271175, type "ER").** Markdown **5,127 characters = the 8-K cover and the Item 9.01 exhibit list**.
Exhibit 99.2 (the earnings addendum: 12,965 visible words, 7,905 table cells in our source) and 99.1/99.3 are **not converted**. The other session found the
same on a CF Industries 8-K (`picture_text_test_20261006.md`): only `main_document/` of the SEC package is processed.

## What their method looks like (no code is public)
- GitHub `financial-reports`: an MCP server (a thin client over the API), auto-generated Python/TypeScript SDKs, a cookbook. Hugging Face: a filing-*type*
  classifier (Jina-v3 embeddings + XGBoost) and the FRCF taxonomy. **The converter is server-side and undisclosed.**
- The output's fingerprints: text nodes joined with a space (hence `1.00 %`), comments and the `<?xml?>` declaration not stripped, `colspan` collapsed
  (headers lost), `$` and value cells merged in some rows and not others, no heading detection, no images, main document only; PDFs go through a
  PDF-to-Markdown converter that emits `<!-- End of picture text -->` markers (the other session's deck test).
- **Their own cookbook (`analysis/enrich-markdown`) says the standard Markdown lacks "proper tables, hierarchical headings, and clean lists" and
  recommends sending the whole filing to Gemini 2.5 Flash to "beautify" it** (prompt rule: "Do NOT omit any text") — the opposite of our contract: a model
  rewriting the document, no source link, and the free sample shows the model dressing the leaked XBRL header up as a "Data Records" section (611 headings).

## Against the owner's four priorities (PrepareTools.md)
| Priority | FinancialFilings for Prepare |
|---|---|
| fully automatic | yes, but the conversion is theirs: a defect (lost header, "Anchor") cannot be fixed by us, only reported |
| minimal generic code | would replace our route with an API call — but we would still need the exhibits route, the anchors, and a fidelity check on every file |
| faithful meaning + exact source links | **fails**: no positions; a period header lost; words that are not in the filing |
| cost | 6–12 credits ($0.06–0.12) per document, main document only; 42,633 filings ≈ $1,800–5,100 at list, more with exhibits if they ever convert them |

## Where it could still help (not Prepare)
- Filing discovery/freshness and the common filing-type taxonomy for non-SEC documents (the August notes) — unchanged.
- As a free lesson: the two fidelity classes their output shows (text-node joins, comment leaks) are exactly what our scanner-based gates catch; nothing to copy.

## Calls and cost today (this session)
2 company lookups, 2 filing lists, 3 Markdown retrievals (one 10-Q twice: md + json; one 8-K), 1 rejected request (406, wrong Accept header), all under
3 s; headers say `monthly-limit: Unlimited` (pay-as-you-go), credits not shown — at list price 22–40 credits (≤ $0.40), within the 500 free per month
together with the other session's ≈ 26. No further credits needed for this question.
