# Can the reader tell which notes matter?

**The current prompt still misses needed definitions and includes unnecessary calculations.** Two independent reads of lululemon’s annual report made both errors on the same pieces.

| Prespecified check | First read | Repeat |
|---|---:|---:|
| UPS and lululemon. Keep a qualification needed to understand the main statement. | 8 of 10 | 9 of 10 |
| UPS and lululemon. Omit a nearby or marked note that supplies only extra detail. | 5 of 6 | 5 of 6 |
| Omnicom. Preserve a changed earnings definition or complete a footnote split across a page. | 3 of 3 | 3 of 3 |
| Omnicom. Leave the next year’s paragraph out of a statement about 2025. | 2 of 2 | 2 of 2 |

The Omnicom checks use three related pieces. Two read the same sentence in opposite directions. All three filings were new to this experiment. The counts measure the specific decisions shown in the table.

## What the reader actually saw

- **A missing definition.** In lululemon’s segment table, both reads returned the pointer to Note 2. Neither supplied the text explaining that inbound freight is a product cost and running a distribution center is an *other cost of sales*. The reader given only the selected material could reconcile the totals and still could not tell those categories apart.
- **Extra arithmetic.** The same readers both attached a marked note giving the standard working-capital subtraction and its rounded inputs. The table already stated the date, unit and **$156.336 million excluding cash**. Removing that note preserves all three rows. Both readers correctly kept a different note explaining that a **$314.27** average exercise price covers only stock options.
- **A difference between reads.** Both UPS readers found the rules for calculating shareholder return. On the separate award table, only the repeat identified the correct comparison group as UPS Class B shares ranked against the individual S&P 500 companies in the index **at the start of the period**. The first read kept the payout thresholds while losing that distinction.
- **A real page break.** Omnicom’s footnote ends a page at “The net”. Both reads found the continuation giving a **$2,141.4 million** reduction in 2025 operating income and **$8.50** reduction per diluted share. When assigned the continuation, both recovered the three costs it referred to. Both left out the next paragraph about 2024. On the parent table, both kept the separate note explaining the revised EBITA definition.

## How the test was checked

The original filing reviews, assignments and scoring decisions were fixed before the first model call on each filing. Each Sonnet 5.5 reader used high reasoning and saw the entire filing and its exhibits. Two copies received the same assigned IDs. A separate reader described each first answer using only the selected original pieces. Equivalent evidence counted. Each repeat was checked against the filing.

One disputed UPS example was scored separately. Its table already labels its stock-option row as the effect of **dilutive** securities. I treated a nearby count of excluded options as extra detail under the owner’s main-statement rule. The source reviewer considered it necessary. The first read omitted it, and the repeat included it. The dispute is outside the counts above.

The readers returned all **30 requested answers on 15 distinct pieces**. They chose exactly the same links on 9 of 15. Nine model calls represented **$2.04 at list prices**, with paid overage disabled. The six copies read **99.76% of their input tokens from cache**. These costs cover Sonnet. The original-source review and filing preparation are separate.

**Keep the approved prompt as the baseline.** A mark tells the reader where to look. The test for attaching the note is whether it supplies a meaning the main piece needs. When it points elsewhere for that meaning, the reader needs the actual definition. This distinction can be tested on new issuers without adding company names, filing layouts or accounting phrases to the reader. [Frozen prompt, filed excerpts, both sets of answers and grades](footnote_evidence.json.gz) · [Independent review of the original 67 answers](RESULTS.md#recheck-of-the-67-original-answers)

## Can one question recover missing evidence?

During fact extraction, let the reader ask one specific question when the selected pieces leave a statement unclear. Look up that question once in the cached filing and add the original passages that answer it. Leave any point the filing still cannot settle unresolved.

| Check on the two known misses, each read twice | Needed detail reached the reader |
|---|---:|
| Approved first pass | 1 of 4 |
| First pass with a stronger definition instruction | 3 of 4 |
| Ask for missing evidence in general | 2 of 4 |
| Give the filing reader the earlier reader’s account of what was unclear | 3 of 4 in valid replies |

The first two rows compare the original UPS and lululemon assignments. For the last two, both readers started with the same groups that had missed both definitions. The wording change also dropped “consolidated” from an AMG balance sheet. The reader given the earlier account found the right passage in all four attempts, but one UPS reply repeated its answers and failed validation. Both lululemon replies also added an unnecessary earnings table to a separate group.

**Test on a different filing.** I selected two statements from Snowflake’s 10-Q and showed each to a reader twice in separate sessions, once with the needed passage and once with only that passage removed. When the marked note was missing, the reader asked what it said and recovered the original **$141 million reclassification**. When the unmarked definition was missing, it asked how Snowflake calculated **151% net revenue retention** and recovered the customer group and calculation. Each lookup returned exactly the missing passage. Both complete groups prompted no question.

The two cached lookups together represented **$0.033** at list prices. The four short group reads and initial filing load brought the Snowflake test to **$0.55**. Across the experiments in this section, 24 Sonnet 5.5 high calls represented **$3.51**, with paid overage disabled. The Snowflake gaps were deliberately created. How often the actual fact reader notices naturally missing context remains unmeasured. [Test instructions, original passages, answers, checks and costs](context_repair_evidence.json.gz)
