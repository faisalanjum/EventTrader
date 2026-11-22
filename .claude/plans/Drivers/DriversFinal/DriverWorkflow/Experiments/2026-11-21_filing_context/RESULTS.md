# Filing context experiment · November 21, 2026

**Hold production.** The reader returned all 241 requested answer lines across 26 live Sonnet 5.5 calls. They cover 69 distinct pieces from four filings. The original prompt failed on 6 of 31 pieces from two companies held out of prompt development. The revised prompt failed on 5 of 31. In each run, two failures were company logos. Dropping them broke the picture rule and lost no disclosure. Retrying both logos left three errors on the revised run. Two lost meaning, and one kept a heading that only introduced other material.

## How errors were found

Code checked the assigned numbers, labels, support IDs and call completion. A separate reviewer read the original filing, including each piece the model called useless. Readers given only the selected material described what each main piece said. Reviewers then removed each proposed attachment and identified what the main statement would lose. A wrong label, lost meaning, or unnecessary attachment counted as an error on that piece. Reasonable alternative source locations and disputed readings are recorded separately. Two readers agreeing did not establish correctness.

The independent readers saw only the selected groups for the original Installed Building Products (IBP) pilot and for the revised prompt on the two new companies. The AMG runs were checked directly against the filed sources. The initial IBP display included the text and original picture but omitted filenames and byte addresses. I checked the groups again with those fields restored. The auditor’s exhibit filename hints at the firm. Its full signing name appears in the missing signature. The new companies used the documented display, and their independent readings of the original filings were saved before either prompt was run on them.

## Pieces with no confirmed error

| Filing and targets | Original, high | Revised, high | Revised, extra-high | Narrow revision, high |
|---|---:|---:|---:|---:|
| Installed Building Products 10-K, development pilot | 17/24 | 19/24 | 21/24 | 10/12¹ |
| Affiliated Managers Group 8-K, known distant-note test | 9/12 | 8/12 | — | 8/12 |
| ON Semiconductor 10-Q, first use | 14/15 | 13/15 | — | — |
| Simply Good Foods 10-K, first use | 11/16 | 13/16 | — | 11/16² |

¹ The narrow run used only the original 12-piece A assignment in one direct call. ² Simply Good Foods was a development case by the time the narrow version was written. Scores above use first answers. In the IBP pilot, the two copies agreed exactly on 10/12 pieces with each high prompt and 9/12 at extra-high. The counts are group-level judgments on selected pieces. They cannot establish production precision, recall, or final fact accuracy.

## Recheck of the 67 original answers

Of the 16 flagged pieces, **five lost meaning, nine had only related extra material, and two discarded logos**. One of the five also included a redundant question. I found no wrong-subject attachment among those ten recorded extra links. Removing the surplus from the nine extra-only groups saves 3,759 characters of displayed source text. The individual extras range from 56 to 1,092 characters. The two logos contained no disclosure.

The five losses were the starting date of IBP’s forecast, the year of AMG’s quarter, the auditor signing IBP’s consent, the policy and people covered in Simply Good Foods’ exhibit, and the discarded officer’s signing block. On AMG’s earnings calculation the original prompt found all three paragraphs of note (1). Two revisions lost the continuations, including one without the new instruction to remove links. The runs establish the regression. They do not isolate its cause.

- **Report dates.** I verified the SEC header in all seven filings used across the two experiments. IBP’s report period ends December 31, 2025. The same filing also reports shares outstanding as of February 19, 2026. AMG’s 8-K header gives the event date of May 1, 2023. The press release itself gives the first quarter of 2023 in piece 55. A source-supplied report date is useful background. Each figure still needs evidence for the date that governs it.
- **Exhibit titles.** IBP’s exhibit list links all six local exhibits. Its consent row names Deloitte. Its CFO certification row links the exhibit number to the CFO file and the description to the CEO file. Simply Good Foods’ index identifies its insider trading policy, while the actual covered audience appears inside the exhibit. A clearly linked original title can help identify a document. Its speaker and audience still depend on the text.
- **Signature wording.** In one separate Sonnet replay I removed only “a signature that only authenticates” and its comma from the test prompt. The full filing, 16 assignments and settings matched the original call. The reader recovered the officer’s name, titles and date and linked the signature to Exhibit 31.1 and the officer’s certification statement. The selected text did not name Section 302. Fourteen answer lines were identical. The other changed line dropped a redundant heading from the auditor’s consent. This known-case replay represented $0.76 at list prices. Its effect on fresh signature cases is unmeasured. [Recount, original source excerpts and exact replay](footnote_evidence.json.gz)

## What changed the decision

- **Attribution.** Both original IBP copies returned the auditor’s consent without the signature naming Deloitte & Touche LLP. Both revised copies supplied piece 1292. On the other two companies, both prompts supplied the correct names in all five first-person auditor and officer checks. In the Simply Good Foods policy, the revision found the policy title but still omitted the passage identifying who “you” covers.
- **Footnotes.** The AMG reader found the changed definition 31 pieces away in every version. But both rewritten prompts stopped at the first paragraph of a different numbered note on two tables. The omitted paragraphs explain how the share count and earnings numerator change. For Q1 2023, dividing the printed $134.5 million by 39.9 million gives $3.37. Using the adjusted $138.6 million gives the reported $3.47. The original prompt retained the assumptions. The native filing stores these paragraphs as separate pieces with no shared paragraph ID.
- **Precision.** Removing the individual swap rates or the breakdown of excluded shares left the respective IBP main statements intact. Some runs still attached loan history or a generic lead-in. In the extra-high run all five previously confirmed extra links disappeared. Its primary copy also dropped “consolidated” from both financial statements. The other copy kept both titles.
- **Discarded material.** Both prompts discarded the two company logos despite the instruction to keep pictures. Both also discarded a completed block giving an officer’s name and titles. The narrow change recovered that block but left its specific certification unidentified. It still missed the AMG note continuations. This failed the narrow version’s predeclared stopping check.

## Repair tested

The reply checker now uses the original image marker. A `useless` answer for a picture leaves that row open and preserves the other answers. The check caught all four recorded logo errors in the two matched prompt runs and kept the other 58 answers. Offline checks exercised all 17 image occurrences and all 3,454 other pieces across these four source views.

All five images in the three annual and quarterly filings received `keep` when assigned explicitly as images. They included two charts and three logo occurrences. Both charts retained the $100 investment and dividend-reinvestment assumptions. Only the IBP chart also received the table giving exact point values. Retrying **only the two rejected IDs** from sessions that held the original filing recovered both logos. Three errors remained on the new companies. The revised prompt kept a bare heading, discarded an officer’s completed title block, and omitted the passage identifying whom a policy covers. [Reply check and retry instructions](README.md#3-check-replies-and-assemble-the-groups-offline)

## Cost and limits

The 26 model calls ran from 12:53:54 PM to 1:23:32 PM EST (America/Toronto). The CLI’s total was **$7.96 at list prices**. All calls used the subscription with paid overage disabled. This measures the Sonnet calls. Independent review and local filing preparation are outside that figure.

The original four-call IBP pilot took 30.2 seconds and represented $0.83 at list prices. Its three copies read **99.8% of their input tokens from cache**. The revised pilot took 45.7 seconds at high and 122.8 seconds at extra-high. The two single-ID recovery forks together represented $0.054 at list prices. Fork costs were calculated after subtracting the parent session’s inherited total.

The new quarterly and annual filings were selected by a fixed hash order from 81 and 19 eligible local packages respectively. Eligibility required one filer, verified HTML for the report and filed exhibits, and 350,000–2,500,000 combined HTML bytes. Targets combined a fixed sample of text, headings, tables and images with specific speaker and time checks. The entire selected filing was visible on every reading. The AMG test also included its original eight-page courtesy PDF.

At the end of the pilot, the 340-piece load test was still pending. A follow-up tested qualifications and detail-only calculations on fresh UPS, lululemon and Omnicom filings. A later run completed the load comparison and independently reviewed 100 random pieces across four other issuers. [Load and random-sample results](RANDOM_AUDIT.md) · [Footnote test](FOOTNOTE_TEST.md) · [Original run evidence](run_evidence.tar.gz) · [Release rules](../../../DRIVER_RULES.md)
