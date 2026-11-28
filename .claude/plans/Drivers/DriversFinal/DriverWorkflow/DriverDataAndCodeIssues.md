# Driver data, code and prompt checks

The [current Driver rules](../DRIVER_RULES.md) govern. The entries retain the original issue numbers. Read the November 18–21, 2026 checks with `git show 976ad380c:driver/Prompts/design_discussion_handoff.txt`.

## Return measurements

R1–R8 are open. Before returns trigger research or grade a prediction, verify the measurements or exclude them (rule 10.1). Use the **Which Date a judgment explains** table for publication boundaries. Rules A2.7 and 7.6 govern daily returns and proof of publication. [Daily explanation plan](../DRIVER_Predict_Explain_Learn/References/EXPLAINED_BY.md)

### R1. Early closes

The November 13 audit found 157 News stories and 12 Reports affected, including filing `0001193125-23-181188`. For November 24, 2023 at 3 PM EST, the helper returned an hourly window of 4–5 AM EST, a session end of 9:35 AM EST and a daily end of 1 PM EST that same day. The expected daily window was November 24 at 1 PM EST to November 27 at 4 PM EST. On November 25, 2026 the daily error reproduced and both [ordinary-day controls](#november-13-audit-baselines) passed. Check all three windows against actual regular and extended hours.

### R2. Inconsistent source dates

Twelve News stories had an earlier daily end for another reason. `bzNews_19018768` records creation on January 5, 2022 at 9 AM EST and a daily end on January 5, 2021 at 4 PM EST. Establish which field is wrong using the original source version and the writer.

### R3. Publication return versus company daily return

TENX filing `0000950170-25-071382`, public May 14, 2025 at 4:09:24 PM EDT, had `daily_stock = −1.37%` for the May 15 close. The same company’s `HAS_PRICE.daily_return` was +0.35%. Stored closes of 5.68 and 5.70 give +0.3521%. Trace the actual endpoint prices, bar times, adjustments, trade eligibility and data versions. The daily summary uses grouped bars. The publication path uses second-level bars. Its price helper can look back up to five days and drops the chosen bar’s timestamp. Verify the caller’s actual endpoints. The cause is unresolved.

### R4. Missing return windows

9,608 Transcripts and 9 Reports lacked a saved daily schedule. Of those Transcripts, 9,373 had daily returns. Reconstruct the intended windows, then verify the prices and times actually used. Untraceable measurements stay unverified.

#### Entry 17. When the transcript was public

On November 18, all 9,608 Transcripts had `created` and `updated` equal to call start. The transcript processor copies `conference_datetime` into both fields. None of their Redis tracking keys supplied `ingested_at`. Apple’s January 29, 2026 call began at 5 PM EST. An answer 1,471 seconds into the recording was still in the future at 5:05 PM EST. [Transcript processor](../../../../../redisDB/TranscriptProcessor.py#L520)

**Passing return-window check.** For a test call on January 29, 2026 at 3:30 PM EST, the hourly window was 3:30–4:30 PM EST, the session window was 3:30–4 PM EST and the daily window ran from January 28 at 4 PM EST to January 29 at 4 PM EST. A 9 PM EST test call that night started its hour at the next premarket open, January 30 at 4 AM EST. See [R1](#r1-early-closes) for early closes. The base processor passes `created` to the scheduler, and the returns manager uses the call time and scheduled ends to select price pairs. [Event time](../../../../../redisDB/BaseProcessor.py#L377) · [Price pairs](../../../../../eventReturns/EventReturnsManager.py#L287)

On November 21 the input accepted a blank public time and required a time zone for known times. Verify saving, citing and ordinary research with a blank time. Test historical reads without a receipt and with public-access receipts for the exact version before, at and after the decision. Only the earlier receipt qualifies when publication time is otherwise unknown.

### R5. Edited news (Entry 18)

`bzNews_47218826`, `bzNews_50489449` and `bzNews_50957341` had one stored body each and daily ends matching `updated`. The last showed 3:29 AM EST and 4:06 PM EST on March 2, 2026. The window may be correct for the edit. Trace the cited version, schedule and return together. Test older, equal and newer updates, including equivalent times with different offsets. After replacement, the saved quote supports ordinary research. Earlier public availability needs separate proof. [News plan](../DRIVER_Predict_Explain_Learn/References/NewsMultipleSymbols.md)

### R6. Release exactly at the close

Report `0000016058-23-000183` was published December 27, 2023 at 4 PM EST. Its saved daily window ended at that instant. The expected end was December 28 at 4 PM EST. Test just before, exactly at and just after both ordinary and early closes.

### R7. Price timestamps on early-close days

Of 655,858 company price records, 649,552 timestamps matched the regular close. The other 6,306 said 4 PM Eastern on days that closed at 1 PM. Verify what the provider and `HAS_PRICE` writer timestamp. Distinguish bar time, period end and availability before judging the price value.

### R8. Missing or unusable values

The full source inventory found five nonfinite daily returns (one News and four Reports) and one list-valued Report hourly return. `_norm_ret` takes the first list element and checks for NaN. Exercise each consumer with a missing value, list, NaN, infinity, zero and a valid nonzero return. Exclude unusable values from numerical comparisons and retain their unknown status.

### November 13 audit baselines

Compare `returns_schedule.daily` with the first XNYS regular close strictly after the stored `created` time. Verify the publication time of the cited version separately. All 1,213 Date records matched the calendar after decoding `is_trading_day` strings `1` and `0`.

| Source | Calendar match | Needs review | No schedule | Total |
|---|---:|---:|---:|---:|
| News | 348,498 | 172 | 0 | 348,670 |
| Report | 42,611 | 13 | 9 | 42,633 |
| Transcript | 0 | 0 | 9,608 | 9,608 |
| Total | 391,109 | 185 | 9,617 | 400,911 |

The 185 cases comprise R1 (169), R2 (12), R5 (3) and R6 (1). For R3, select the trading Date from the saved daily end in `America/Toronto`. Join that Date’s `HAS_PRICE` to the **same Company**. Compare its `daily_return` with the source relationship’s `daily_stock`.

| Source relationship | Finite pairs | Gap over 0.02 percentage points | Opposite signs |
|---|---:|---:|---:|
| News `INFLUENCES` | 231,940 | 106,353 | 918 |
| Report `PRIMARY_FILER` | 41,384 | 21,599 | 167 |
| Report `REFERENCED_IN` | 445 | 246 | 3 |

The corrected check used `abs(a-b) > 0.020001` for floating-point rounding. Opposite signs require one strictly positive and one strictly negative finite value. Another 117,660 pairs lacked a value and two were nonfinite. Counts are relationships. Transcripts lacked schedules. When rerunning, include any newly supported relationship types.

**Controls.** AAPL Report `0000320193-23-000005`, published February 2, 2023 at 4:30:33 PM EST, selected February 3 at 4 PM EST. Both returns were +2.44% from 150.82 to 154.50. On February 2 an 11 AM EST input selects that day’s close and a 4:30 PM EST input selects the next trading close.

**Reproduction.** The 12 audited Python files matched revision `2783e7d5c` on November 25. The audit used `exchange_calendars` 4.10 (XNYS regular closes and adjacent sessions) and `polygon-api-client` 1.14.4 (grouped daily and aggregate prices).

- Trace windows through `utils/market_session.py` (`MarketSessionClassifier`) and `eventReturns/EventReturnsManager.py` (`_calculate_return_times`). Check late prices in `eventReturns/ReturnsProcessor.py` and price selection in `eventReturns/polygonClass.py` (`get_daily_market_summary`, `get_returns_indexed`, `get_last_trade`).
- Trace stored dates and prices through `neograph/Neo4jInitializer.py` and `neograph/EventTraderNodes.py`. Trace source versions through `neograph/mixins/news.py`, `redisDB/TranscriptProcessor.py` and `transcripts/EarningsCallTranscripts.py`. Find `_norm_ret` in `scripts/earnings/builders/inter_quarter_context.py`.
- Optional raw reports in `/tmp/driver_explanation_review_a6f51esx/` are `timing_review_20261113.json`, `return_comparison_corrected_20261113.json`, `audit_returns.json`, `native_checks.json` and `timing_review_source_hashes_20261113.json`. The corrected comparison supersedes the earlier counts in `window_audit.json`.

To close R1–R8, rerun each applicable population read-only. Record revision, library versions, Eastern audit time, counts and reasons for valid, affected, missing and unverifiable records. Cover premarket, regular and after-hours releases, early closes, holidays, weekends, daylight-saving changes and edits. Identify effects on trading dates, returns and signs, triggers, grades, earlier evidence or metadata. Test the responsible helper or writer with positive controls and regressions. Verify saved records separately. Database repairs require owner approval.

### Entry 22. Daily returns against their own closing prices

**Saved returns verified November 21, 2026.** On November 18, 811 of 655,858 records lacked the same company’s preceding trading-day price. Of 655,047 comparable pairs, 654,807 matched exactly and another 189 were within 0.02 percentage points. Split-adjusted closes confirmed 48 of the 51 flagged returns. The three Xerox corrections were July 21, 2025 (+2.57% to +2.56%), July 23, 2025 (+14.06% to +14.07%) and February 9, 2026 (+35.54% to −9.64%). All 51 saved returns were read back and verified.

**Stored closing prices still need verification.** The table counts gaps over one percentage point between the saved return and the percentage change in the same company’s stored closes on consecutive trading days, rounded to two decimals.

| Read-only check (2026) | FTV | HPP | LESL | NFLX | NOW | XRX | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| November 18 | 4 | 9 | 9 | 9 | 9 | 11 | 51 |
| November 25, 11:32 AM EST | 4 | 9 | 9 | 9 | 9 | 10 | 50 |

**Lead for the price check.** All six companies had gaps on 2024-02-06, 2024-02-07, 2025-03-14 and 2025-03-17. All except FTV also had gaps on 2025-07-16, 2025-07-17, 2025-07-21, 2025-07-22 and 2025-07-23. XRX alone had a gap on 2026-01-26. Each date identifies a return comparison. Trace both that day’s price load and the preceding trading day’s load to test whether a shared import introduced different split adjustments.

Netflix’s stored closes for July 21–23, 2025 were 123.327, 1,190.08 and 117.678. The raw July 22–23 pair implies −90.11%. Adjusting July 22 to 119.008 for the 10-for-1 split puts all three closes on the same basis and reproduces the saved returns of −3.50% and −1.12%.

Under rule 10.1, use a verified saved daily return. Recalculate only from closes verified on the same split-adjusted basis and exclude unverified measurements. Before any price repair, establish which prices already include the split adjustment. Applying it twice changes the return. The [publication return comparison](#r3-publication-return-versus-company-daily-return) remains open.

## Other Driver code and data checks

Unless another path is given, the functions below are in `driver_reference/core/`. Verify each through the caller used in the build.

### Entry 6. Open a saved citation

In AMG 8-K `0001004434-23-000015`, Item 2.02 points to Exhibit 99.1 (`amgq12023ex991.htm`). On November 21 the prepared file yielded the cash-flow row label, header, quarter dates and both amounts. The 2023 value `(3.2)` occupies bytes `[17066, 17071)`. Recover this evidence from a saved fact in the original exhibit version. Verify an altered digit fails (1.17, 9.4).

### Entry 8. Combine two accounts of one figure

`driver_fusion.fuse_event` combined complementary fields and identical amounts, but kept 10.0 and 10.04 separate in either order. It also kept 10.0 and 11.04 separate. Test one filing that prints “$10.0M, up 5%” and tags the same revenue as $10,040,000. Expect one fact with $10.04M, 5% growth and both locations in either order. Test a true conflict and an eligible precision upgrade after saving. Check identity, original evidence and upgrade history. If proof cannot be retained, verify the saved fact survives and the item records the gap (5.2–5.5, A1).

### Entry 16. Trace a fact to its model calls

Decider recorded a model ID and request start. Sonnet recorded a message timestamp. The reference writer returned item numbers and available fact IDs. Trace a saved fact to both reader and checker through the existing log. Verify one record per call with its step, exact model ID, request start with time zone and matching items.

### Entry 19. Filings missing a company link

On November 18, 390 of 42,633 Reports lacked `PRIMARY_FILER`. Among 39,966 ordinary filings, 12 8-Ks, eight 10-Ks and one 10-Q lacked it. All 809 amendments to those forms had it. Of the 21, six had multiple filers and no primary number, seven VNOM records had a different number, two lookups failed on short numbers, and six have an exact match today with the original cause unknown.

In `XBRL/xbrl_processor.py:get_company_by_cik`, `794170` and `1488139` missed. `0000794170` and `0001488139` found Toll Brothers and Ameresco. Toll filing `0000794170-26-000056` lacked the link and `0000794170-25-000066` had it. Test both forms through intake and `neograph/mixins/report.py`, including a mismatch and a verified missing filer with no permitted retry (logged extraction skip). Padding explains the reproduced lookups. The historical cause remains unverified.

### Entry 20. Measure the cost of company history

Measure elapsed time and cost for one company’s initial history and subsequent searches. Record shortlist size, batch size and full-search frequency. Estimate costs at 1,000, 5,000 and 20,000 names. Use the results to choose coverage and budgets before routine searches. The next trials cover two companies, then ten. [Company workflow](DriverWorkflow.md#company-workflow)

### Entry 23. Filing dates versus an older saved period

For Darden FY2026 Q3, `driver_period_resolver.ensure_driver_period` chose December 1, 2025–February 28, 2026 when given both the old Guidance dates and the filing window. With only the filing window or explicit source dates it returned November 24, 2025–February 22, 2026. Test filing priority in the integrated caller using `0000940944-25-000071` and `0000940944-26-000009` (3.43, 8.11).

### Catalog search, placement and work tracking

- **Find a saved name.** Test word and meaning search across companies, exact names across types, incomplete families and concurrent additions. Place a known match in every batch position. Compare a complete no-match with an unread batch before permitting creation (2.43, 5.8).
- **Choose a name.** Test at most two distinct, source-supported saved-name proposals, an occupied exact name, “500 workers” and an unidentified “total of 500.” For equally fitting names, exercise source wording, the subject’s direct fact counts, first-fact creation time and alphabetical name in order. Shared facts skip the count. With several names shown, grade placement, synonym suggestions and warnings separately using the cheapest qualified model per task. In the Celanese fixture the operating-profit quotes support `operating_profit` and contradict `gross_profit`. Replacing the defining quote with a forecast must reverse acceptance. Hide the expected answers (2.20, 2.40–2.47, 8.12–8.13). [Saved-name fixture](../../../../../tests/driver/createDriver/fixtures/reuse_saved_driver.json)
- **Track completed work.** Finish four of five requested fact types. Rebatching or showing context leaves the fifth due. Check source version, original passage or cells, requested type and company for split jobs. Distinguish an empty success, failed write and permitted reread. A prose/table repeat yielded one planned fact under one Driver and two under twin names. Replay under its original name planned no write. Test both routes in joined history. A later publication has its own dated fact (5.2, 5.5, 8.14–8.16).

### Twelve trigger cases

| Case | Check through the normal workflow |
|---|---|
| 1. Synonym proposal | Show two saved definitions to the ordinary fact checker. Verify one independent check for an eligible new pair, reuse its verdict on repeat, skip an already joined pair and let the incoming fact proceed independently (5.6). |
| 2. Wrong join | In a three-name indirect join, log a contradiction without changing the join. Test an owner correction and restoration. A genuine pair refusal still blocks restoration (6.18, 7.1). |
| 3. Declared rename | Count accepted company facts from the declaring filing. Skip an unused name. After a May 10 approval, an April 10 duplicate leaves the note dated May 10 and ineligible on April 30. Compare raw and requested joined histories. Accept Cushman `0001628369-25-000005` for a pure rename. Refuse Ares `0001628280-24-021890` for a changed business, and the EQT `0000033213-26-000018` and Performance Food `0001618673-25-000012` passages for missing measurement evidence (6.13–6.17). |
| 4. Changes after a rename | A tag change (West `0000105770-26-000049`) or revised figure (HPE $1,147M to $1,076M) leaves the note active. Two old names leading to one new name switch both notes off. The numerical switch-off test was retired (6.16, 6.18). |
| 5. Optional filing links | Save ready facts first. Try linking newly accepted eligible facts once, grouped by source version. Only 10-Qs, 10-Ks and their amendments wait for their own tags or retry limit. Other sources use eligible tags already loaded. A blank starts no search. Once A1 is enabled, a newly active filing-line link starts its separate eligible history (6.7–6.8, A1). |
| 6. Held earnings 8-K | Only a 10-Q or 10-K proving the same company and quarter can reopen the job. Recheck the facts against the original 8-K (3.44, 8.15). |
| 7. Unclear first state | A full read leaves the first state of a new plain-named Driver unknown. Expect a logged skip. Test the allowed name-ending exception as a control (2.37). |
| 8. Missing proof when combining | Run the evidence-loss case in [Entry 8](#entry-8-combine-two-accounts-of-one-figure). A hold requires a permitted trigger (8.15). |
| 9. Late source | Process unfinished work within coverage at the source’s own public time. Verify expected sources before marking a search complete (7.6, 8.14–8.16). |
| 10. First company metric | After initial context, the first accepted metric new to a company starts one covered search in the 12 months before the source’s proven public time. Test the same metric at a second company (separate search), unknown public time (save only) and a fact found by the search (no further search). See 8.16. |
| 11. Reviewed lists | Refresh the catalog and filing breakdown lists outside routine work. Exercise a normal run without a person present (1.21, 3.16, 3.21, 8.3). |
| 12. Missed facts | A missing surprise companion triggers a whole-event reread. A wholly missed claim has no direct trigger. Test permitted recovery by retry, targeted history or quarterly review. A weaker reread preserves the saved fact (4.15, 5.5, 8.14–8.16). |

## Fact-finding prompt

The November 17 template and review (`73f87e915`) predate the November 18–20 decisions. The review’s `remaining_design_gaps` lists G1–G5. The current rulebook settles all five. Align the prompt, review and downstream code. The renderer currently selects by source type only. [Prompt](../../../../../driver/Prompts/find_facts.txt) · [Review](../../../../../driver/Prompts/find_facts_review.json) · [Renderer](../../../../../driver/createDriverUpdate/prompt.py)

### Agreed requirements for the prompt edit

1. Show the owner the exact wording and get approval before editing the existing template. Preserve wording outside the agreed corrections and necessary moves.
2. Write shared instructions once. Test them with each fact type (`metric`, `guidance`, `surprise`, `action_event`, `expectation`) and with all five, including required companion facts.
3. Add only the source-specific differences needed for filings, transcripts, news and other text. The existing admission rules govern which source types can be saved.
4. Use ordered checks and a final self-check. Preserve necessary conditions and exceptions in plain language. Review and test independently.
5. Review discovery and field resolution within their existing workflow. Model-call layout and cost experiments are separate decisions.
6. Check each change against the full rules and its intended use. Add a field or rule only for a demonstrated error. Test equivalent inputs for consistent output.
7. Read the current rules and related plans for each discrepancy. Apply settled decisions, record any implementation check and ask the owner about one genuinely open behavior at a time.

### Five settled decisions to test

| Review ID | Prompt, writer and reader checks |
|---|---|
| G1. Forecast attribution | Exercise confirmed, reported-unconfirmed and outside forecasts. One article reporting and confirming one outlook gives one confirmed fact. Separate publications retain their own facts and times. A newer unconfirmed $12B report must leave a confirmed $10B outlook current. `_lane_matrix` rejects `company_confirmed=false`. `_conflicts` distinguishes the flags during combining. The reference writer excludes confirmation from `SIGNATURE_FIELDS` and treats it as replaceable in `_LWW_FIELDS`. Its in-memory write plan changed `true` to `false` on otherwise identical input. Before relaxing the validator, test that a weaker reread preserves confirmation and its evidence (5.5). Test one bank across signers, equal estimates from different banks, and a numberless reaffirmation or withdrawal without a prior unit, which the reference writer previously held (4.9, 9.2, 9.11). |
| G2. Withdrawals | Save a company withdrawal once as an action. Read current guidance before and after it, with a narrow or blanket scope, a stated exception, no prior fact at save time, a later replacement and a retelling. Apply the effective withdrawal before ranking. Exercise numberless updates (4.18–4.21). |
| G3. Table dashes | The template says “keep dashes unresolved.” Discovery passes the dash and applicable explanation with both original locations to field resolution. An explicit source definition for that cell yields zero. A tagged zero alone or an unrelated or conflicting note leaves the dash unresolved. Test an ordinary printed zero and a stated nonzero bound alongside them (10.4). |
| G4. Company prediction of another party’s action | The template still skips these predictions. Test “we expect FDA approval” as `action_event/forecast` and “if approved” as a condition. Preserve attribution, negation, stage and the exact action condition. Test exact wording for a numberless metric alongside it. The reference validator accepts `conditions` and `value_text` only on guidance (4.7–4.8, 10.5). |
| G5. Waiting and retrying | Test temporary source unavailability, an unsupported claim after the required full read, a rule violation and a valid refusal on unchanged evidence. Verify the corresponding permitted retry, logged skip, rejection and final refusal. A later source gets its own event (8.14–8.15). |

**Movement check.** In `driver_reference/core/driver_validators.py`, `_movement` requires the revised range midpoint to agree with the stated direction. For 90–110 revised to 95–105, test “we raised guidance” as `raised` and “we revised guidance” as `reaffirmed` under 4.4. Test storage and the subsequent read.

**Discovery checks.** Exercise every prompt combination above. Two separately stated actual period values in prose or a table give two candidates with locations. A growth rate alone supplies no prior amount. A surprise-only request still needs the same-source actual or confirmed outlook. Keep source-stated returns visible and withhold system-calculated returns. After the approved prompt edit, update the review’s clause mappings and fingerprints. Run the renderer tests and these behavior checks. [Renderer tests](../../../../../tests/driver/createDriverUpdate/test_prompt.py)
