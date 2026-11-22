# Does the filing reader keep the meaning?

**Across 100 randomly selected pieces, 14 groups clearly lacked meaning on the first read. After the next reader could ask one question, 13 still did.** Two more pieces were debatable. These counts concern what a reader could establish from each group. A disclosure can also appear elsewhere in the filing.

## Four fresh filings

| Filing | Pieces reviewed | Clear losses before | Clear losses after |
|---|---:|---:|---:|
| Goosehead Insurance 10-K | 25 | 1 | 1 |
| Roku 10-K | 25 | 2 | 2 |
| Moderna 10-Q | 25 | 3 | 3 |
| Allegiant Travel 10-Q | 25 | 8 | 7 |
| **Total** | **100** | **14** | **13** |

The 13 remaining losses had three causes visible in the answers.

- **Five groups never reached the next reader.** Three discarded pieces named the patent owner, the person making a certification, or the officer who signed and when. Two scanned assignment forms named the companies involved. The model called them useless twice, so the picture check left both open.
- **Five groups looked complete to the reader.** For example, Goosehead’s CFO exhibit certified fiscal 2022 inside an annual filing for 2023. The group identified the officer and omitted the passage giving the year. The reader answered `READY`.
- **Three questions left a gap.** Roku’s reply repeated a trading-plan question without the conditions that govern closed-window trading. On Allegiant, one reply named the correct contractual definition but failed the required output format. Another supplied part of an indemnity definition and still omitted the filed limits on damages. A different Allegiant question fully recovered the broker’s identity.

The two disputed introductions describe the scope of Roku’s audit procedures and Moderna’s investment table. Both can support the following material. Treating them as substantive groups in their own right raises the final count to 15. The per-piece reviews also record narrower disagreements, including how much of a relative reporting period must be spelled out.

All 100 assigned IDs received an answer. **98 passed the response checks.** Of these, 38 were marked useless and 60 reached the reader that could ask a question. It asked seven. Related but unnecessary attachments increased from 3 of 71 selected links to 6 of 79. The review identified no link applying the wrong subject or period. The small, clustered sample supports no general error bound for all filings.

## Does giving each copy fewer pieces help?

All four settings used the same cached Installed Building Products filing and prompt. Each piece was assigned once per run. The 8- and 17-copy tests followed the original comparison, with up to six calls in parallel. The last column includes the same $0.718 filing load once per setting.

| Work per copy | Valid answers | Meaning check on the same 14 pieces | Elapsed after load | Copies alone | With filing load |
|---|---:|---|---:|---:|---:|
| 1 copy × 340 pieces | 340/340 | 3 lost meaning | 89 seconds | $0.165 | $0.88 |
| 4 copies × 85 pieces | 340/340 | All 14 retained meaning | 35 seconds | $0.224 | $0.94 |
| 8 copies × 42–43 pieces | 340/340 | All 14 retained meaning | 27 seconds | $0.331 | $1.05 |
| 17 copies × 20 pieces | 318/340 | 13 retained meaning, 1 missing a valid answer | 33 seconds | $0.560 | $1.28 |

The four copies recovered the month of a share purchase and the word “consolidated” for two financial statements. Their answers differed from the single copy on 21 of 340 pieces. The 14 meaning checks came from the earlier pilot and covered three of the four ranges. The remaining 326 pieces received format and coverage checks. At 8 and 17 copies, one checked passage also received unnecessary loan history. At 17 copies, one reply repeated its entire 20-piece range and another omitted two IDs. The cost shown includes those attempts. Each size ran once on this filing, so its production accuracy and best batch size are still unknown.

Each copy read the same 179,161 tokens from cache. That represented about **1.8 cents per copy** for the shared text alone. With one copy per piece, 340 cache reads would represent **$6.09** before the filing load or the copies’ reasoning and answers. Giving two similar readers each of the four 85-piece assignments would represent about **$1.17** including the load if their work cost the same as in the measured run. These two figures are estimates. [Frozen size comparison, replies and costs](cache_size_evidence.json.gz)

## How the counts were verified

The approved Sonnet 5.5 high prompt stayed fixed. The four new issuers followed the previous filing selection order. A fixed random draw selected 25 pieces per issuer from all original text, tables, headings and pictures. Source-first reviews were locked before the first call on each new filing. Reviewers checked every selected original, each discard, any support the reader received and every attempted repair. The reviews credit passages that convey the same meaning. The original scanned pages were available to both readers and reviewers.

The first experiment used five full-filing bases and 13 copies. Five copies did the initial work, seven answered specific questions, and one retried both rejected pictures. Another 60 independent calls saw only their selected passages. The four-copy comparison reused the existing IBP base. These 82 calls represented **$5.34 at list prices**. The later size comparison reused that base for 25 additional copies representing **$0.89**, bringing the total to **$6.23** across 107 calls. All calls used the subscription with paid overage disabled. The random sample measures the Sonnet reader on the four eligible filings. The deployed fact extractor and the Decider require their own tests. [Frozen assignments, original excerpts and images, individual grades, replies and first 82 call records](random_audit_evidence.json.gz)
