# Selected 10-K driver context reader

This is the current selection for retrieving the original filing evidence for each requested driver. Hosted Perplexity Decider does the main reading. Google's Gemma helps find exact passages, and Gemini file slicing checks charts. The saved run covers ten names supplied together for Palo Alto Networks’ fiscal 2023 Form 10-K, accession `0001327567-23-000024`.

**The recorded benchmark passed. Production readiness is still open.** This package can reproduce that run offline. Its completeness on new filings and the largest reliable batch size still need testing.

[Read the ten driver packets](packets.md) · [Replay the result](replay.py) · [Exact follow-up checks](followup_checks.json) · [Source and provider receipts](recorded_run.zip)

## Measured result

| Source check | Result |
| --- | ---: |
| Earlier required context details | 36 of 36 |
| Earlier unrelated passages excluded | 10 of 10 |
| Disputed passage decisions | 8 of 8 |
| Additional context and relevance checks | 15 of 15 |
| Historical financial-tag locations kept | 6 of 6 |
| Decisions on the shareholder-return chart | 10 of 10 |
| Newly checked contract details in two originals | 5 of 5 |
| Newly checked unrelated details excluded | 4 of 4 |
| Sentence showing which sales the distributor terms cover | 1 of 1 |
| Capital requirements excluded from subscription gross profit | 1 of 1 |

The measures overlap. Three of the ten names produced empty packets. The previous 180 passage assignments are preserved. Seven additions across three drivers contain 3,611 original characters in 15 sentence assignments. The seven additions all have an identifiable connection to the request. Some sentences include context about other products or inputs.

The combined API cost was **US$0.03986340** for the filing and all ten names, about 3.5% below the matched original hosted Decider cost of **US$0.04130152**. Perplexity billed 1,982,090 input tokens at US$0.02 per million. Gemini billed 2,216 input tokens at US$0.10 per million for the chart check, including 1,696 text tokens and 520 image tokens. The final sentence-selection step used 5,154 of those paid Decider tokens and seven zero-price Gemma calls. These are the recorded rates and usage for this job.

The measured stages total **about 83 seconds** with prepared inputs, including about 16 seconds for the new search and checks. This is a sum of measured stages. A cold end-to-end run starting with raw filing bytes still needs timing. Earlier tests generated reusable wording for 29 names together in 33.9 seconds. The experimental lookup now generates missing terms automatically.

## How the passages are selected

The text input comes from the original SEC HTML filing and its text exhibits, split into numbered passages and tables. The figure check uses a PDF rendered from the filing with the original image. Each output packet is keyed by the supplied driver name. It contains original wording with source file and byte positions, plus exact character ranges for shortened excerpts. A financial figure keeps the label and scope the company printed.

1. Hosted Perplexity Decider (`pplx-decider-v1.3`) reads all 1,380 prepared filing passages against each supplied name. A second read uses the company’s own statements as references.
2. Follow source relationships, rows, accounting notes and unusual repeated company wording. Check the original evidence for each disputed connection. Google's hosted text model (`gemma-4-31b-it`) can suggest exact quotes. Decider checks their meaning and scope. The prepared text includes exhibits for which the structural note parser reported syntax errors.
3. Search the whole filing for two originals containing the same six consecutive words. Start at a supported original. Identify prose containing a meaningful word from the requested name using SQLite’s native full-text search. On this filing 24 additional name/passage pairs qualified.
4. Free hosted Gemma selects original sentences from those passages. If the selected sentences omit the term identifying the subject, keep the nearest sentence from that same original containing it. Hosted Decider checks the selected wording against the earlier issuer statements. It accepted seven of twelve proposals. Only the original source wording goes into a packet.
5. Send the original figure-bearing page and its text layer to `gemini-decision-1` using file slicing. The only chart was the shareholder-return chart on page 38 of the 102-page rendering. All ten driver packets correctly omitted it.

## Why this version is selected

In a matched comparison, a newer reader recovered the same five late contract details and returned all four later distractions. This reader recovered all five and excluded all four with 187 passage assignments across the ten names. One paragraph shows why sentence selection matters. It gives distributor billing and renewal terms alongside a distributor's 49.7% share of company revenue. The subscription-billings packet keeps the terms and omits the revenue share. The exact wording checked for each outcome is recorded in the [follow-up checks](followup_checks.json).

## Reproduce the recorded job

From this directory, use Python 3 with SQLite FTS5. The replay reads the included files locally and requires no API key.

```sh
python3 replay.py
python3 replay.py --driver "Subscription Billings"
python3 replay.py --json
```

The replay reconstructs the selections from the archived replies, verifies the original bytes and every new sentence interval, checks the eligible search results, and totals paid usage. The `--driver` option filters the ten recorded names. Running the complete method on a new filing still requires the research stages.

The archive includes the prepared filing index, original source bytes for the returned passages, rendered page evidence, exact prompts and responses, 36 research source files under `code/`, and checksums. The outer manifest records the checks and hashes the README, replay, packets, answer checks and archive. [Recorded run](recorded_run.zip) · [Package manifest](manifest.json)

## Evidence beyond the original checks

A source review of 54 previously ungraded passages found meaningful evidence unique to each of two earlier readers. Reviewing sources selected by one or both readers cannot measure what both missed. A broader reader recovered the two contract passages and included all four newly checked unwanted details. The selected version preserves the contract terms and excludes those details. This review did not establish overall precision.

A different first-pass reader was tested on WEC Energy. Following a source connection recovered a separate 2022 refund reversal that increased transmission earnings. That filing provides an independent example of an indirect detail an earlier perfect spot-check score missed. The two complete filing methods have different first stages.

Before production, freeze one runnable method and test it on previously unseen companies. Audit samples of both returned and omitted material against the original filing, including charts, footnotes and cross-referenced tables. Measure elapsed time and total cost from raw input. Then test the same names alone and in progressively larger batches, in different orders and with an optional prior fact. Ten names is the batch size documented here.
