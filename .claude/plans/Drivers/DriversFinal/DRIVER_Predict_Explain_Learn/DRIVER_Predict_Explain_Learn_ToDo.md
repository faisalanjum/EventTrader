# Driver design review to-do

The aim is one clear design for making a paper call, explaining a stock move and learning from the result. This is the discussion list. Current plan rules are starting points. The owner, Claude and Codex decide changes together under the [working instructions](DRIVER_Predict_Explain_Learn_Instructions.md) and the [current rulebook](../DRIVER_RULES.md).

The owner confirmed items 1 and 2 in this order. The remaining order is proposed. Settle evidence, timing and reviews before deciding what a call must save. Items 17–18 check implementation and documents. The source labels cover 45 workbook questions, 24 margin notes and two earlier owner issues (E1 and E2). Each source label opens the original issue note or the owner’s message in these two notebooks.

## Who acts and what evidence counts

- [ ] **1. What starts evidence gathering, a prediction or a review? Who does each job?**

  **Why.** “All triggers; all conditions; who can create them, and when and why?” Evidence gathering, a call and a review may start at different times. Rule 8.16 processes relevant reports, transcripts and news even on quiet days. A significant move starts research even without news. Reuse saved evidence first.

  The notes propose three historical triggers (earnings, between-quarter moves, watched Drivers) and two live/replay call triggers (earnings releases, watchlist hits). They assign moves to different agents. Which list governs which job? Is price research daily only? A watched update must be verified before it triggers a call. A completed move can prompt a later prediction on new information.

  Rule 1.4 gives the Predictor a read role for Drivers. Either agent may submit evidence under 2.34. Only the shared process verifies evidence, reuses or creates the Driver, and saves the update. Should a Predictor start by creating updates or propose a separate future concern or context update? Does the Learner maintain the watchlist or supply daily judgments and review calls? Clarify the blank third item. For IDs, timestamps, change detection, eligibility and grading, decide what code does and what the model judges. Results must hold across retries. Summarize the answer in one row per trigger, naming who acts, who verifies and what gets saved. Test a quiet filing, a move without news and a qualifying update while a call is open.

  [4.1](#41-which-trigger-design-is-current) · [4.2](#42-who-creates-driverupdates-and-when) · [4.4](#44-a-driverupdate-that-matches-the-watchlist) · [8.1](#81-code-owned-values) · [N.12](#n12-the-learners-primary-task) | [Update triggers](References/EXPLAINED_BY.md#1-one-update-process-two-triggers) · [Call triggers](References/DRIVER_LearnerPredictor.md#predictor)

- [ ] **2. Whose DriverUpdate is it, and whose stock moved?**

  **Why.** “never linking a driverUpdate if it's linked to multiple companies” could mean the story or the occurrence. Without a subject, can we retrieve company history or match a watchlist before any price explanation exists?

  Rules 3.2 and 3.9–3.11 distinguish source owner, subject company and affected stock. A company-specific update has one immutable `FOR_COMPANY` link and the subject in its ID, with no extra subject field. A genuinely shared update has none. Hold or skip an unresolved subject. Compare dropping `FOR_COMPANY` and `MAPS_TO_MEMBER` whenever the source names several companies. Trace source and Driver links, periods, company calendars, filing concepts and breakdowns, guidance confirmations or withdrawals, surprises, causes and offsets. Period IDs and dates identify the period. Fiscal meaning stays with the update. A shared update needs its own period evidence.

  Test equal revenue for two companies in one story, A’s filing reporting B’s metric, equal-valued separate deals versus retries, and one deal or Fed decision affecting stocks differently, including an unnamed company. Each stock can have its own direction and strength. Enable extraction only when IDs, links and context agree. With one story job or separate company jobs, A’s partial read or retry cannot finish or overwrite B’s work.

  **Reviewer concern.** Rule 3.9 says News needs no owner, then says to skip extraction without a unique owner. Which sources require the check? Test two clear company subjects in one story.

  [1.1](#11-company-links-when-a-source-names-several-companies) · [1.2](#12-company-history-without-for_company) · [1.3](#13-watchlist-triggers-without-for_company) · [1.4](#14-one-shared-fact-explaining-several-companies) · [1.5](#15-other-company-specific-links) · [N.2](#n2-using-date--company) · [N.3](#n3-company-specific-fact-extraction-stays-off-until) · [N.4](#n4-the-cross-source-design-) · [N.5](#n5-whose-fact-vs-whose-stock) | [Company and source examples](References/EXPLAINED_BY.md#6-source-and-company-examples-simple-retrieval) · [News extraction](References/NewsMultipleSymbols.md#reading)

- [ ] **3. What may each agent see, how does it get it, and by when?**

  **Why.** A replay must reproduce what was knowable. The Predictor receives a briefing without direct database or web access. The Learner may search the database within its cutoff. Compare prompt-only access for both. Earlier Learner tooling allowed research. Who retrieves missing originals? Must each input be a DriverUpdate, or can quotes, documents, prices, calls and reviews supply context?

  Prove the exact source version was public strictly before the cutoff. Even source text can disclose the outcome (rule 1.25). Prior price windows must have ended and their verified results been available. Record each judgment’s actual save time and evidence cutoff. Its evidence cutoff must be no later than the call cutoff. The daily field list and rule A2.3 omit this second time.

  Use only shared history already available when live input closes or at the simulated replay cutoff. Backfills designated at launch contribute to shared history, but their calls remain replays. A replay may also use earlier completed steps of its own ID. Its latest eligible judgment or withdrawal overrides the same key only in that replay.

  [3.4](#34-whether-everything-the-predictor-uses-is-a-driverupdate) · [3.5](#35-agents-without-database-access) · [N.11](#n11-the-learners-evidence-cutoff) | [Input cutoff](References/DRIVER_LearnerPredictor.md#input-cutoff) · [Explanation fields](References/EXPLAINED_BY.md#5-what-each-explanation-stores)

- [ ] **4. When do we create or reuse a Driver? When do we save a DriverUpdate?**

  **Why.** A recurring topic and one occurrence need different tests. A price crossing or an analyst’s concern is a lead. The owner named “fiscal KPI”, “fiscal AI KPIs”, “perplexity KPIs”, “perplexity search we have”, “distill KPIs” and “distill search we have”. KPI means a measure of company performance. Confirm whether the first two overlap.

  **Driver.** Reuse an existing meaning. Creating one requires its first proven update (2.35). After initial company context, the first accepted metric new to that company triggers one oldest-first search of covered history within the 12 months before proven publication (8.16). If time is unknown, keep the update and skip the search. Results trigger no further search. Historical work must leave room for live work.

  **DriverUpdate.** The update workflow has tested gathering supporting passages cheaply. Decide what proceeds, what proves an update or no update, and what coverage and research budget apply. Final records, links, no-update outcomes and downstream cost remain untested. Fresh guidance is usable before a daily explanation. `CAUSED_BY` and `OFFSET_BY` require two supported updates and a quoted connection in the same source event.

  **Reviewer concerns.** Rule 1.14 allows a known name for targeted checks. Open discovery starts from the source. Where do the target names come from, and how would a new risk be found? A known name alone proves neither a match nor whole-source coverage (8.10). The shared creator is proposed. Reading copies is tested. Separate design rules from Workflow v2 operating steps. Reconcile the explanation checklist’s four update types, the rulebook’s five (including outside expectations) and Workflow v2’s tentative “others?”.

  [E1](DRIVER_Predict_Explain_Learn_Instructions.md#57-codex-only--2026-11-27-095446-pm-est) · [4.3](#43-the-normal-driverupdate-workflow) · [N.13](#n13-facts-usable-without-explained_by) | [Gathering evidence](../DriverWorkflow/DriverUpdateWorkflow.md) · [Proposed checker](../DriverWorkflow/SharedCreator.md) · [Reading copies](../DriverWorkflow/BaseAndCopies.md)

- [ ] **5. Which news stories do we save, and which companies do they link to?**

  **Why.** A broad story can move a stock it never names. Save one News record per story. Count distinct original feed tickers before filtering. One total ticker, tracked, gets `INFLUENCES` plus sector, industry and market links. Two or more total tickers get only `MENTIONS` to tracked companies, even with one tracked and one untracked. Skip new ordinary stories with none tracked. Selected original research, such as an untagged Fed release, may be saved without inventing company links. The November 28 check found 348,669 saved stories linked to one company, one linked to none and none linked to several.

  Must research start from a company’s move? Should single-ticker research always use `MENTIONS`? Today the same News type and link rules apply. Filings and transcripts retain their types. Selective historical retrieval is allowed. Bulk loading is outside this change. The notes describe multi-ticker stories as generally broad. Ticker counts and measured returns alone prove no cause. Each company link carries hourly, session and daily stock, sector, industry and market returns. The calculator selects sector and industry benchmarks by company. SPY is the market benchmark.

  [7.1](#71-when-a-research-article-is-saved) · [7.2](#72-a-research-articles-company-links) · [N.1](#n1-multi-ticker-news-is-usually-generic) · [N.6](#n6-multi-company-stories-and-mentions) · [N.15](#n15-relative-returns-without-sector-and-market-links) · [N.17](#n17-news-type-) · [N.21](#n21-historical-backfilling) | [News link rules](References/NewsMultipleSymbols.md#design) · [Research exception](References/NewsMultipleSymbols.md#research-exception--no-tracked-tickers) · [Return calculator](../../../../../eventReturns/EventReturnsManager.py)

- [ ] **6. When a story changes, what survives and what could an earlier call see?**

  **Why.** An edit changes what could have been known about a company. A newer complete version replaces text, tickers and affected links together. Retain valid prices and company work. Reprocess changed text as needed. Test one ticker becoming many, the reverse, and removal of the last tracked ticker. Older versions, partial versions and retries leave the record intact.

  A late price fills only a missing value for the same company/window and leaves the story and times alone. The checked records held the latest version. Rule 7.6 allows a saved quote and version reference for research. An earlier call needs proof of wording and ticker membership as of its cutoff. What proof is worth keeping when old versions are unavailable?

  [7.3](#73-unintended-effects-of-story-edits) · [7.4](#74-whether-the-unverified-rule-is-worth-it) · [N.16](#n16-last-tracked-ticker-removed) | [Story edits](References/NewsMultipleSymbols.md#when-a-story-changes) · [Evidence for older edits](../DriverWorkflow/DriverDataAndCodeIssues.md#r5-edited-news-entry-18)

## Price moves, calls and reviews

- [ ] **7. Which measured price move is large enough to investigate?**

  **Why.** The boundary controls research and watchlist eligibility. The note says “above a threshold of, say, 2.2%”. The Learner plan uses an absolute stock-minus-SPY gap of **at least 2.20 percentage points** over the same hour, session or day. Hour and session checks need a timed source. Otherwise use regular close to regular close. Rule 10.1 leaves significance settings open. Decide benchmark, window and boundary.

  **Reviewer check.** In the November 28, 2026 check across 831 trading dates, 153,038 of 655,858 stored company-day pairs qualify inclusively. Exactly 959 equal 2.20. Strictly greater gives 152,079. Binary floating-point arithmetic counted 152,813 as inclusive. One investigation may cover several company-days. Test −2.38% versus −0.18%, early closes, an intraday move without a timed source and missing prices. Rule 10.1 requires verified returns or exclusion. Use a verified saved daily return or closes verified on the same split-adjusted basis. Missing stays unknown.

  [4.7](#47-the-learners-triggers-and-threshold) | [Proposed threshold](References/DRIVER_LearnerPredictor.md#qualifying-move) · [Open return checks](../DriverWorkflow/DriverDataAndCodeIssues.md#return-measurements) · [Closing-price check](../DriverWorkflow/DriverDataAndCodeIssues.md#entry-22-daily-returns-against-their-own-closing-prices)

- [ ] **8. Does an explanation cover an hour, a session or a trading day?**

  **Why.** A stock can rise in the morning and give it all back by the close. Today `Date → EXPLAINED_BY → DriverUpdate` records a contribution to one company’s regular close-to-close move. Several updates may explain a day, even pushing against its net direction. One update may explain several days or companies, each with support. An intraday move can prompt research with a directional call, a no-trade call or no call. Where should an intraday cause go? An hourly call’s update warrants a daily link only with evidence for the day.

  Distinguish event time, source publication, financial period, trading Date and judgment time. For newly public information, first consider the window ending at the first actual regular close strictly after publication. Test two sources across a close, an exact or early close, after hours, weekends and holidays. Thursday’s update may contribute Friday. Saturday reporting may document Friday’s event. An event first occurring Saturday cannot cause Friday’s move. A transcript’s call start does not time individual remarks. A missing one-second feed limits verification. Clarify “Ques #1” if it affects this choice.

  [2.1](#21-linking-a-driverupdate-from-an-hourly-call-to-a-date) · [2.2](#22-explained_by-for-hourly-moves) · [5.6](#56-a-driverupdates-source-date-and-its-date-links) · [N.7](#n7-two-driverupdates-across-the-close) · [N.8](#n8-the-fridaysaturday-table) · [N.9](#n9-post-market-sources-and-the-next-date) | [Date and window table](References/EXPLAINED_BY.md#3-which-date-a-judgment-explains) · [Evidence for a day](References/EXPLAINED_BY.md#4-which-facts-may-explain-that-date)

- [ ] **9. What enters or leaves a company’s watchlist, and what starts a call?**

  **Why.** Outside earnings, the watchlist determines which new source versions trigger predictions. The plan derives it from available explanations of a company’s qualifying close-to-close moves. Define entry, expiry, removal after a correction and lookup at a past cutoff. Does anything need separate storage?

  Earnings releases always trigger calls. Other new public versions, including transcripts, need a verified match. For a company-specific update, match Driver and subject to the earlier explaining update. A shared update matches only shared entries for that Driver. Market-wide changes reach all matching watchers. Limited events reach named parties among them. Unclear scope keeps the update without a call. Test a common Driver that matches many watchers, a first event with no watchlist entry and a new match while a call is open. Holding, exiting or adding to a position is separate.

  [4.6](#46-the-driver-watchlist-triggering-and-storage) | [Watchlist matching](References/DRIVER_LearnerPredictor.md#predictor)

- [ ] **10. How do we grade buy, sell and no-trade calls?**

  **Why.** Verified prices can grade a call even when its cause is unknown. Which existing ticker-and-time calculations use the right endpoints? A source’s daily return can include hours before a decision. Fix the chosen window’s end when saving the call. Start from its live save time or simulated replay decision time. Enter at the first verified tradable price strictly after that start.

  Save `100 × (end price − entry price) / entry price` once, rounded to two decimals. Positive wins a buy, negative wins a sell, zero wins neither. Record the move skipped by a no-trade call without a directional grade. Entry at or beyond the end, or a missing or unverified endpoint, leaves the call ungraded. The 3:30 p.m. EST earnings-call test ended its hour at 4:30 and session at 4:00. Its daily return began at the previous close. Test a paper decision at 3:30, after close, with zero return and with missing prices.

  **Worked example.** The stock closes at 100, then 103 the next day (+3.00%). SPY gains 0.50%, so the 2.50-point gap qualifies for research under item 7’s proposed threshold. A buy entered at 105 and closed at 103 loses 1.90%. Conversely, a buy gaining 1% while SPY gains 4% still wins.

  [6.1](#61-grading-with-the-existing-return-calculation) · [6.2](#62-what-counts-as-a-win) | [Grading](References/DRIVER_LearnerPredictor.md#grading) · [Existing window code](../../../../../eventReturns/EventReturnsManager.py) · [Measured earnings-call windows](../DriverWorkflow/DriverDataAndCodeIssues.md#entry-17-when-the-transcript-was-public)

- [ ] **11. When does the Learner review, and which calls or days can it cover?**

  **Why.** Timing determines available evidence and when one investigation can serve two purposes. Decide whether to record the trigger from a fixed list. Check all four occasions.

  **Call ends.** Briefly review every live call, including no trade, or only review a no-trade call after an exceptional move in its window? A deeper review due for the same event may cover both. Clarify the unfinished “Aside, if there was no BUY/SELL” note.

  **Large move.** Investigate even without news or a call. Why wait until the close of the first trading day *after* the window’s Eastern end date? Why use that close as the replay cutoff? Decide whether one review may cover several calls or days. Each daily judgment still needs evidence for its company and day.

  **Before earnings.** Use the release date known at the prior trading day’s evening scan. Revisit each qualifying move once at the first preview after its initial review, explained or unexplained. **After earnings.** Distinguish predicting from reviewing results. Live review waits for the transcript. Replay stops just before the next release or at replay end, whichever comes first. If the release date was unknown at preview, catch up moves due a second look. Later evidence can correct an explanation.

  [4.5](#45-reviewing-calls-with-no-trade) · [4.8](#48-the-learners-review-schedule) · [2.3](#23-recording-why-the-learner-was-triggered) · [2.4](#24-investigations-per-day) | [Four review occasions](References/DRIVER_LearnerPredictor.md#learner-reviews)

- [ ] **12. Should a review link to the update judged to explain a particular call’s window?**

  **Why.** “Which update did the Learner identify for this call’s window?” This requires evidence for that hour, session or day. Today each completed review saves its company, event or windows, calls reviewed, feedback, cutoff, save time and replay ID if applicable. Retries reuse it.

  Distinguish what the Predictor relied on, what the Learner considered or cited (proposed `CITED`), and what it judged explanatory. For each proposed link, who needs to query the answer directly, and would the saved feedback suffice? One call already supplies the interval when the review covers exactly that window. A joint morning/afternoon review must identify the call for each call-specific finding. A no-call review can still cite evidence, including an older update. If a separate review record is unnecessary, where do its author, scope and findings go? Clarify the diagram’s unlabeled Call 1 arrow to dU3.

  **Reviewer concern.** A common “Unknown Driver” conflicts with rule 2.35’s proven first update. Distinguish an unexplained but reviewed move from one never reviewed. A missing daily link leaves the effect unknown.

  [E2](DRIVER_Predict_Explain_Learn_Instructions.md#60-codex-only--2026-11-27-095831-pm-est) · [3.7](#37-showing-one-review-across-several-calls) · [3.8](#38-cited-links-from-the-learner) · [2.5](#25-showing-a-review-across-time-horizons) · [3.9](#39-an-unknown-driver-for-moves-without-an-explanation) | [Review record and findings](References/DRIVER_LearnerPredictor.md#learner-reviews) · [Daily explanations](References/EXPLAINED_BY.md#2-what-links-to-what)

## What reviews and future calls need

- [ ] **13. When can a review say the Predictor missed or misjudged an update?**

  **Why.** The next call needs to know whether to improve its reasoning or the briefing it received. For each explaining update the call did not cite, check the current four findings. **Shown but uncited** requires its ID or its exact supporting passage from the cited version in the saved input. This is a possible oversight. **Public but absent** requires proof both of public availability by the cutoff and of absence from that input. **First public later** requires evidence of when it first became public. Use **unknown** when the record cannot tell.

  For a cited update, identify over- or underweighting only when the saved reason and evidence for the call’s own window support it. A whole-day judgment alone cannot establish the cause of an hour’s move. Decide which lessons to retain for later calls.

  [3.6](#36-classifying-the-updates-a-call-didnt-cite) | [Review feedback](References/DRIVER_LearnerPredictor.md#learner-reviews)

- [ ] **14. Which histories and past examples help the next prediction?**

  **Why.** How often calls worked and how often a Driver helped explain a move answer different questions. The plan calculates both on demand for the company, industry or sector, each with its own count. Count each graded buy/sell citing the Driver once. Show wins and total by horizon, with live and replay separate. Only live calls measure paper-trading performance. Separately, count distinct affected company-days explained, retaining direction and strength. Overlapping calls and repeated reports can reflect one move.

  Decide how to show losses, no-trades, ungraded calls and quiet days as well as wins. For the briefing, consider the new update and quote, older updates of its Driver, calls that used them, their reviews, explained days and prior price action. A new trigger can lead a call to cite older evidence. Decide whether to include original documents, which earlier feedback to retain, and whether similar changes come first. Apply item 3’s cutoff to everything shown.

  [3.3](#33-what-the-next-predictions-briefing-contains) · [6.3](#63-measuring-and-showing-performance) · [6.4](#64-driver-histories) · [N.14](#n14-counting-by-horizon-live-and-replay-separate) | [Histories](References/DRIVER_LearnerPredictor.md#driver-histories) · [Briefing](References/DRIVER_LearnerPredictor.md#input-cutoff)

- [ ] **15. Which explanation fields earn their place, and how are judgments corrected?**

  **Why.** “Rethink each field one at a time, and keep only what's required, and why.” The plan stores eight fields. `company_id` identifies the affected company. `reason` explains how the update contributed that day. `stock_impact` records upward (`long`) or downward (`short`) pressure. `weightage` measures strength (0.1–1.0 by tenths, or absent). `confidence` measures certainty (0–100 by tens). `llm_producer` identifies the judge, `produced_mode` records live/backfill, and `created` gives the actual save time. Item 3 covers the Learner’s additional evidence cutoff.

  Does strength help across multiple calls or explanations? Strengths vary independently, need not add to 100%, and repeated claims do not establish independent support. Rules A2.4–A2.6 allow relative measures on read. Unknown strengths stay unknown. Assess judgments together by net direction, size and ranking. Why keep explanation mode alongside the call’s live/replay mode? **Reviewer check.** All 796 company tickers were unique when checked. Documented renames include MMC → MRSH and PSTG → P. Could a ticker replace `company_id` across a rename?

  Each judgment is keyed by trading Date, affected company, DriverUpdate and producer. The latest valid completed judgment wins across live/backfill by fixed save time. Replace all fields, clearing newly unknown values. Retries retain their times, older arrivals lose and equal-time conflicts are held. Only explicit withdrawal removes a judgment. Omission, failure or a partial run changes nothing. An older arrival after withdrawal cannot restore it. Earlier overwritten judgments disappear from this shared view. Can a past call still be audited from its own saved evidence?

  [5.1](#51-which-explained_by-fields-are-required) · [5.2](#52-company_id-or-ticker) · [5.3](#53-the-strength-field-weightage) · [5.4](#54-the-livebackfill-mode) · [5.5](#55-the-identity-and-replacement-rules) | [Fields and replacement](References/EXPLAINED_BY.md#5-what-each-explanation-stores) · [Ticker renames](../distilla.md)

- [ ] **16. What is the smallest call record that still supports grading, review and history?**

  **Why.** A later reviewer needs to distinguish everything shown from what the Predictor actually used. The graph record links the company and verified cited updates. It stores IDs for every update shown. Could links alone prove both sets? Is a fixed input copy retrievable by fingerprint necessary to check a quote or prove absence? Should the call link to a Date, and which trading Date applies after the close or when a window crosses it?

  The plan keeps one call per company and triggering source ID/version in live use and separately in each replay. Multiple qualifying updates in one version or retries reuse it. Two publications repeating a claim can each qualify. Use items 10–14 to justify the fields. It keeps buy/sell/no trade, reason, model, live/replay mode and replay ID when applicable, input cutoff, save time, horizon and fixed end. Add the verified result once available.

  [3.1](#31-linking-each-call-to-a-date) · [3.2](#32-recording-update-ids-or-linking) · [N.10](#n10-sealing-calls) | [Call record](References/DRIVER_LearnerPredictor.md#predictor) · [Grade](References/DRIVER_LearnerPredictor.md#grading)

## Implementation and document checks

- [ ] **17. Can the news provider and reader deliver the agreed behavior?**

  **Why.** Missing prices or an edit dated too early can invalidate a call. Verify actual Massive and IBKR access to stories, edits, original ticker lists and usable endpoint prices after the Benzinga subscription ended. The News plan reports that the tested Massive key lacked Benzinga news and the required one-second prices. Check current access before relying on either provider.

  Map `published` to `created` and `last_updated` to `updated`. The ISO parser relabels offsets as UTC. The provider-specific format converts them. The writer compares timestamps as text. Test equivalent instants with different offsets. Poll an overlapping time range to catch edits and document that older edits can still be missed. Match categories regardless of capitalization so a spelling such as ‘Earnings’ or ‘earnings’ gets the same treatment.

  Hide unfinished stock and benchmark returns on both `INFLUENCES` and `MENTIONS`. Both safeguards omit `session_sector`, `session_industry` and `session_macro`. Include `MENTIONS` in existing readers, fix-up scripts and instructions. Similar-news searches must apply company, sector and time filters before ranking, preserve their current result limits and show ticker counts. Older Predictor and Learner readers see only the original link type.

  [7.5](#75-replacing-benzinga) · [7.6](#76-time-zones-in-the-news-reader) · [N.18](#n18-the-look-ahead-check) · [N.19](#n19-the-overlapping-time-window) · [N.20](#n20-category-names-in-any-capitals) | [News checks](References/NewsMultipleSymbols.md#before-switching-on) · [Time parser](../../../../../benzinga/bz_news_schemas.py) · [News writer](../../../../../neograph/mixins/news.py) · [Time guard](../../../../hooks/pit_gate.py) · [Filter rules](../../../../filters/rules.json)

- [ ] **18. Which document references are stale, and what work remains open?**

  **Why.** A new implementer needs to know what is agreed, proposed or already done. The current authority is `DRIVER_RULES.md`. Two references in the explanation plan still name `DRIVER_RULES_Categorized.md`. The older `FINAL_DESIGN.md` reached a company through the source. Check which entries were settled (company links, replacements and decision-time evidence) and which still need work, including the source reader and writer contracts. Preserve genuine open choices on source coverage, historical research and resource limits. The old operating algorithm is an unapproved proposal. Ask what the otherwise blank “Explained_BY” heading meant when this item comes up.

  The former return-measurement section and the handoff’s outstanding code, data and prompt work were moved and pushed in `e8957f6fa`. That move is complete. Return checks R1–R8 and the mixed-basis closing-price check remain open. During the later combined rewrite, send technical work to its existing home and account for every approved move, merge or removal.

  [8.2](#82-which-rules-file-explained_by-should-reconcile) · [N.22](#n22-explained_by-heading) · [N.23](#n23-moving-8-to-a-separate-file) · [N.24](#n24-final_designmds-older-company-link-rule) | [Remaining-work list](References/EXPLAINED_BY.md#7-remaining-decisions-and-implementation-work) · [Code, data and prompt issues](../DriverWorkflow/DriverDataAndCodeIssues.md) · [Historical design](../../FinalDesign/FINAL_DESIGN.md)

## Original issue notes

These 45 questions and 24 margin notes come from an AI transcription of the owner’s annotated PDFs. Quoted notes preserve the transcription, including unfinished wording. The question and alternative-view labels describe the organizer’s reading. Confirm any ambiguity with the owner.

Unprefixed pages refer to *EXPLAINED_BY*. DLP means *DRIVER_LearnerPredictor*, NMS means *NewsMultipleSymbols*, and *Issues* is the single handwritten issues page. Page and section numbers refer to the annotated copies. The 18 decisions above give the current plan context and links. The two issues raised directly in conversation are linked there as E1 and E2.

<details>
<summary>Read the original questions, wording and marked passages</summary>

### 1.1 Company links when a source names several companies

**Question:** When one source (news, report or transcript) names several companies, should each driverUpdate from it still link to a company (FOR_COMPANY) and to XBRL slices (MAPS_TO_MEMBER)?

The workbook cites EXPLAINED_BY §6.1; DRIVER_RULES 3.9, 6.9.

**Alternative view:** the source decides. A driverUpdate from a source that names several companies gets no FOR_COMPANY and no MAPS_TO_MEMBER. Both links are company-specific, and "whose fact" doesn't apply to such a driverUpdate. EXPLAINED_BY.company_id already ties it to each company whose stock it affects.

**#15 note (Issues):** "This below is different from my earlier idea of never linking a driverUpdate if it's linked to multiple companies. Thoroughly check which approach is better, and why."
- "This below" is the passage pasted under the note (EXPLAINED_BY p10–p11). Its first sentence is ticked: "FOR_COMPANY identifies whose fact it is; EXPLAINED_BY.company_id identifies whose price move it explains."

**From notes:** #6 (p4), #15 (p10), #23 (NMS p3), #35 diagram 2 (NMS p5), #11 "another rule" (p7).

### 1.2 Company history without FOR_COMPANY

**Question:** If a driverUpdate has no FOR_COMPANY link (the alternative view in 1.1), can we still see the company's history?

The workbook cites EXPLAINED_BY §6.1 rule 7.

**p12 note:** "Check if history becomes traceable for every configuration we have discussed for linking driverUpdate to the Company, Source."

**From notes:** note between #5 and #6, p12 margin note.

### 1.3 Watchlist triggers without FOR_COMPANY

**Question:** If a driverUpdate has no FOR_COMPANY link (the alternative view in 1.1), can watchlist triggers still work by using EXPLAINED_BY.company_id instead?

The workbook cites DLP p5.

**Alternative view:** EXPLAINED_BY.company_id is enough. The Driver's trigger can still be found through the driverUpdate's EXPLAINED_BY links, which always carry the company ID, separately for each company.

**From notes:** #45 (DLP p5).

### 1.4 One shared fact explaining several companies

**Question:** Should one genuinely shared fact, such as a deal that affects both the buyer and the seller, explain each company's stock move through its own EXPLAINED_BY link?

The workbook cites EXPLAINED_BY §6; DRIVER_RULES 3.9.

**p10 note:** "not sure", with an arrow to "A genuinely shared deal fact may explain both companies through separate links."

In the left margin, a brace over the AAPL/MSFT, Fed and deal rows is labeled "driverUpdate affects Multiple Companies". A line runs from it to a box: "See Multiple News Symbol.md handwritten Notes".

**From notes:** #14 (p10).

### 1.5 Other company-specific links

**Question:** Under the alternative view in 1.1, a driverUpdate from a source that names several companies has no FOR_COMPANY and no MAPS_TO_MEMBER, because both are company-specific. Does it have other company-specific links that it should also leave out?

The workbook cites DRIVER_RULES 3.2, 3.9, 3.36 and its links table.

**NMS p5 note** (on the diagram where news MENTIONS two companies): "But no "for Company", since this news is about multiple companies. Similarly no "Maps to Member", since that's also company-specific. But check in case I missed any other company-specific link!"

**From notes:** #35 (NMS p5).

### 2.1 Linking a driverUpdate from an hourly call to a Date

**Question:** Suppose the Predictor created a driverUpdate as part of a call over, say, an hourly horizon, and the Learner later reviewed it. Do we also link that driverUpdate to a Date with EXPLAINED_BY?

The workbook cites EXPLAINED_BY §1, §3, §4; DLP.

**p3 note:** "means still allowed?", beside the underlined "An hourly/session trigger does not automatically establish a daily explanation."

**p5 note:** "This may be key for, say, Ques #1 on the first page: Date → Explained_BY → driverUpdate, when this call is based on an hourly horizon."
- A line runs from it down the left margin to the starred sentence "No DailyCompanyMoveEvent node, special multi-company News type, or copied time-window fields on every explanation are needed."

**From notes:** #4 (p1), p3 and p5 margin notes.

### 2.2 EXPLAINED_BY for hourly moves

**Question:** Should EXPLAINED_BY also cover hourly moves, not only daily ones?

The workbook cites EXPLAINED_BY §2, §3, §5; DLP.

**Alternative view:** EXPLAINED_BY can also cover hourly moves.

**p6 note**, with an arrow from the boxed "Crossing a boundary does not automatically justify links to both Dates. Do not reuse a source's Thursday return as the result for a Friday explanation.": "Which indicates assigning hourly explained-by is fine."

**p8 note**, on `reason`, with "this Date's period" circled: "How about using hourly?"

**DLP p10 note:** "Also: if the daily return wasn't significant, so there's no daily Learner review, but the stock rose over the hour (via an hourly call, or with no call/hold when the actual return was good), still create EXPLAINED_BY and link this Learner."

**p5 marks:** a bar and a tick beside "For this daily design, all EXPLAINED_BY links start at Date…".

**From notes:** #8 (p6), #12③ (p8), #58 (DLP p10).

### 2.3 Recording why the Learner was triggered

**Question:** Should we record, as an ENUM, why the Learner was triggered?

The workbook cites DLP, Learner reviews.

**DLP p10 note** (the last sentence of the note quoted in 2.2): "So record an ENUM for why the Learner was triggered."

**From notes:** #58 (DLP p10).

### 2.4 Investigations per day

**Question:** Should investigations be done per day (one or more each day), with none spanning several days?

The workbook cites EXPLAINED_BY §4, p7–8.

**p7 margin note:** "Actually, given our design, does it make sense to do 1 or more investigations per day, but not across days?"
- Beside the paragraph "A separate investigation per day is not required…" are a "!", a double bar and a tick, and "can support Thursday and Friday together, using the same evidence" is underlined.

**From notes:** #11 (p7).

### 2.5 Showing a review across time horizons

**Question:** The Learner creates each EXPLAINED_BY link, but the link is specific to a Date, not to a call. How do we show the Learner's review when time horizons differ, for example when the Learner considered driverUpdates from two dates?

The workbook cites DLP; EXPLAINED_BY §4.

**DLP p10 note**, the fourth item under "How do we show the Learner's review for, say: …": "the difference in time horizon, meaning when the Learner considered driverUpdates from 2 dates, etc."
- The number ⑤ is crossed out, which merges it into ④.

**From notes:** #58 ④ (DLP p10).

### 3.1 Linking each call to a Date

**Question:** Besides the driverUpdates it cites and its company, should each call also link to a Date node?

The workbook cites DLP, Predictor.

**Alternative view:** the call is a single node that links to three node types: the driverUpdates it uses, the Date and the company.

**DLP p1 note:** "Overall, every driverUpdate the predictor cites in a single call it makes needs to be linked to those driverUpdates and a Date node! The Learner will link Date to driverUpdates using Explained_BY, while it will review this call made by the predictor (if available)."
- Meaning: each call links to the driverUpdates it cites and to a Date node.

**DLP p9 note:**
- "The Predictor uses these ① 3 driverUpdates to make a call on this ② Date for this ③ Company."
- "Then the Predictor call can be a single node linking to these 3 node types, with fields such as direction (3 choices), the time it was made, any other reasoning, etc."
- "Note: so far, Date is not linked to driverUpdate."

**DLP p10 diagram:** Call 1 links to the company and the date; Call 2 links to the date.

**From notes:** #37 (DLP p1), #57 (DLP p9), #58 diagram (DLP p10).

### 3.2 Recording update IDs, or linking

**Question:** If each call links directly to the driverUpdates, do we still need to record their IDs?

The workbook cites DLP.

**Alternative view:** instead of recording driverUpdate IDs, the call links directly to the driverUpdate nodes.

**DLP p2 note**, joined by a line to "Here its update ID is in the saved input": "Instead, if each call already links to each driverUpdate, do we really need to show the update ID?"

**DLP p5 note**, just above the bullet "Show each supplied DriverUpdate's ID and keep it in the call's input record…": "But what if we link each driverUpdate to its call?"
- Meaning: instead of recording driverUpdate IDs, the call should link directly to the driverUpdate nodes.
- On the same page, "mode", "(live or replay)" and "input cutoff" are circled.

**From notes:** #38 (DLP p2), #47 (DLP p5).

### 3.3 What the next prediction's briefing contains

**Question:** What should the briefing for the next prediction contain?

The workbook cites DLP, Picture D and input cutoff.

**DLP p3 note**, with an arrow from Picture D's "Calls citing sales forecasts" box: "Tentative:
1. Create driverUpdates.
2. See previous driverUpdates linked to this Driver, and where calls were made using them.
3. Related reviews for those calls.
4. Days linked to this Driver (EXPLAINED_BY).
5. Generic previous price action."

**From notes:** #39 (DLP p3).

### 3.4 Whether everything the Predictor uses is a driverUpdate

**Question:** Are driverUpdates the only information the Predictor uses to make a call? And under DRIVER_RULES, can everything it uses be converted into a Driver/driverUpdate?

The workbook cites DLP, Predictor and input cutoff.

**DLP p9 notes**, under a diagram of driverUpdate 1 from yesterday's News, driverUpdates 2 and 3 from today's Report, and the company:
- "Q1: Are we 100% certain this is the only information the Predictor uses? Ideally, any information the Predictor uses to make a call should be made a driverUpdate. But based on our DriverRules.md, can everything be converted into a Driver/driverUpdate?"
- "But remember: the Predictor is triggered by new driverUpdates, but it can cite older driverUpdates to make a prediction."

**From notes:** #57 (DLP p9).

### 3.5 Agents without database access

**Question:** Should both the Predictor and the Learner run without database (MCP) access, and get all their context in the prompt?

The workbook cites DLP, input cutoff and Learner reviews; EXPLAINED_BY §1.

**Alternative view:** use agents with no MCP access, like the earlier Predictor and Learner.
- Those agents ran from specific skills, with no database read access and no web search, and got all their context in the prompt. That made them point-in-time by construction.
- The skills still need adapting to the new design.

**DLP p6 note**, in the input-cutoff section: "Instead, we use agents with no MCP access, similar to the earlier versions of the Predictor and Learner."

**DLP p8 note:** "TBD", circled, on "The Learner may search the database directly, using the existing views for DriverUpdates (rule 7.11)."

**From notes:** #48 (DLP p6, p8).

### 3.6 Classifying the updates a call didn't cite

**Question:** Are these the right rules for classifying the explaining updates that a call didn't cite?

The workbook cites DLP, Learner reviews.

**DLP p8 note:** "Not sure about these rules yet!", with a bracket beside this paragraph. The "it" in "each explaining update it did not cite" is marked "Predictor".

**DLP p2 marks:** "public but absent", "first public later" and "unknown" are circled, in "Other findings are public but absent, first public later, or unknown when the evidence cannot tell."

**From notes:** #55 (DLP p8), #38 (DLP p2).

### 3.7 Showing one review across several calls

**Question:** The Learner creates each EXPLAINED_BY link, but the link is specific to a Date, not to a call. How do we show the Learner's review when there are 2 calls on the same date, or when the Learner created EXPLAINED_BY without a Predictor call?

The workbook cites DLP, Picture C and Learner reviews.

**DLP p10 notes:**
- **Beside the second case:** "Maybe don't need a separate learner node!"
- **Under "① The way to show reviews for multiple calls by the Learner:"**
  - (a) "Suppose calls don't trigger reviews (the proposal that only BUY/SELL calls trigger a review, unless returns at the call's horizon are extraordinary). No extraordinary return happened at the call's horizon (assumed to be different from the daily return), but the daily return was significant. Then one Learner review links to both calls (2 review links), and to all the driverUpdates it created EXPLAINED_BY links for."
  - (b) "If calls do trigger separate reviews (or only 1 triggered a review), there are separate Learner nodes, each with its own review links. So the Learner's review links are tied to the Learner that created that review."
- **Diagram:** one Learner REVIEWS both Call 1 and Call 2, captioned "Assuming a single learner was used to evaluate both calls (such as when no review was triggered)."

**DLP p9 note:** "Q2: The Learner reviews this call."

**From notes:** #58 issues 1 and 3, ① (a)–(b) and diagram (DLP p10); #57 Q2 (DLP p9).

### 3.8 CITED links from the Learner

**Question:** For each review, how do we show which driverUpdates the Learner considered instead? Should the Learner link to them with CITED, as a call does, even when they're from a different date?

The workbook cites DLP.

**DLP p10 notes:**
- **Issue 2:** "for each review, what the Learner considered instead, in terms of driverUpdates".
- **(c)** "Also link driverUpdates with "CITED" to the Learner that created it, even if that's from a different date." An arrow leads down to: "Any inconsistencies with how we are thinking about it?"
- **(d)** "Also, when no call triggered a review but the daily return was significant enough for the Learner to create EXPLAINED_BY, this Learner can still create CITED links to those driverUpdates."
- **(e)** "The same goes for Predictor calls (CITED links to driverUpdates)."
- **Diagram:** the Learner CITES dU3 and dU4, the same driverUpdates the date links to with EXPLAINED_BY. Call 1 CITES dU1 and dU2, and has an unlabeled arrow to dU3.

**From notes:** #58 issue 2, ① (c)–(e) and diagram (DLP p10).

### 3.9 An "Unknown Driver" for moves without an explanation

**Question:** When the Learner can't find an explanation, should it link with CITED to an "Unknown Driver" (common to all), in the interim?

The workbook cites EXPLAINED_BY §1; DLP, Learner reviews.

**DLP p10 note:** "② Maybe when the Learner can't find an explanation, in the interim we link the Learner with CITED to an "Unknown Driver" (common to all)?"

**EXPLAINED_BY p3 mark:** "If evidence does not support an explanation, leave the move unexplained" is underlined.

**From notes:** #58 ② (DLP p10).

### 4.1 Which trigger design is current

**Question:** Do DLP's triggers replace the two triggers in EXPLAINED_BY §1?

**Alternative view:** DLP's triggers replace §1's. The information trigger is "not relevant now", and the price trigger's move means "Daily moves as captured by Date nodes".

**p2 note**, above §1: "This design choice now seems old (see Driver.LearnerPredictor.md, which is current), since for historical there are 3 broader triggers for driverUpdate creation…" The rest of the note is in 4.2.
- On the same page, "two triggers" is circled and "daily timing" is underlined.

**p2 notes on §1:**
- Beside the information trigger: "not relevant now!"
- Under the price trigger, with an arrow from the underlined "useful related publication": "Daily moves as captured by Date nodes."

**p3 note**, with a bracket over §1: "Again nice to borrow some generic points but triggers & rules here are replaced by Driver_PredictorLearner.md!"

**Issues note**, headed "Predictor & Learner": "Exact triggers; exact scope, structure (links);" followed by a blank third item.

**From notes:** #5 (p2), #2 (Issues), p2 and p3 margin notes.

### 4.2 Who creates driverUpdates, and when

**Question:** What are all the triggers and conditions for creating driverUpdates? Who can create them, when and why?

**Alternative view:** the Predictor creates driverUpdates when it's invoked, and the Learner may create them for EXPLAINED_BY. The p2 note lists 3 broader triggers for historical processing (maybe the same live). The DLP p4 note lists 2 triggering conditions for both replay and live.

**p2 note**, above §1, continued from 4.1: "…since for historical there are 3 broader triggers for driverUpdate creation: ① every earnings season ② significant moves between quarters ③ checklisted driver triggered. All 3 are done by the predictor, while the learner reviews and may create driverUpdates for EXPLAINED BY!"
- A circled callout beside it: "& maybe same for live!"

**DLP p4 note**, beside the Predictor section: "Triggering conditions for both replay and live: ① earnings release ② driver watchlist. Process: the Predictor always starts by creating driverUpdates when invoked, but the watchlist only uses EXPLAINED_BY links (made by the Learner)."
- In the Predictor section, "each earnings release", "triggers a separate call", "verified DriverUpdate matching the company's watchlist" and "even while an earlier call is open" are underlined.

**Issues note:** "All triggers; all conditions; who can create them, and when and why?"

**From notes:** #1 (Issues), #5 (p2), #43 (DLP p4).

### 4.3 The "normal DriverUpdate workflow"

**Question:** What exactly is the "normal DriverUpdate workflow" that both agents' discoveries follow, and why and how is it used?

**DLP p8 note**, under the underlined "normal DriverUpdate workflow": "Exactly what, why & How?"

**From notes:** #54 (DLP p8).

### 4.4 A driverUpdate that matches the watchlist

**Question:** Suppose a driverUpdate is detected because it's on the company's Driver watchlist. Is it done separately, without the Predictor? And may the Predictor create a separate driverUpdate when it sees a possible future concern, or for context?

**Issues notes** (Scenario #1):
- "Also, let's assume a driverUpdate is detected (since this driverUpdate was in this company's driver watchlist)."
- (a) "Is this driverUpdate done separately, without even needing the predictor?"
- (b) "But the predictor may generate a separate driverUpdate if it finds this could be a future concern, or for context (offset by/etc)."

**From notes:** #10 (a)–(b) (Issues).

### 4.5 Reviewing calls with no trade

**Question:** If the Predictor makes no BUY or SELL call, should the Learner skip reviewing it unless the (hourly/session or daily) return turns out to be above the threshold?

The workbook cites DLP.

**Alternative view:** the Learner reviews a no-trade call only if the return turns out to be above the threshold.

**Issues notes** (Scenario #1, continued):
- (c) "And let's say the predictor did not make a BUY or a SELL call. Ideally the learner should not review it unless the (hourly/session or daily) return turned out to be more than the threshold. Yes or No?"
- (d) "Aside, if there was no BUY/SELL by the predictor (although we still create the Call node)…" The note stops there.

**DLP p10 note**, in suggestion (a) (see 3.7): "the proposal that only BUY/SELL calls trigger a review, unless returns at the call's horizon are extraordinary".

**From notes:** #10 (c)–(d) (Issues), #58 ① (a) (DLP p10).

### 4.6 The Driver watchlist: triggering and storage

**Question:** What is the exact triggering and storage mechanism for the "DRIVER watchlist"?

The workbook cites DLP.

**DLP p1 note**, at the top of the page: "Determine the exact triggering and storage mechanism for the "DRIVER watchlist"."
- On the same page, "tentative" is circled.

**DLP p5 marks**, on the matching rules: "A market-wide change triggers all matching watchers" is ticked, and "scope is unclear, keep the update without triggering a call" is underlined.

**From notes:** #36 (DLP p1).

### 4.7 The Learner's triggers and threshold

**Question:** Should the Learner create or update driverUpdates through EXPLAINED_BY on two triggers: when it reviews Predictor calls, and when a move is above a threshold of, say, 2.2% for all 3 horizons?

**DLP p4 note**, at the bottom of the page: "The Learner creates/updates DriverUpdates via EXPLAINED_BY under these triggers: ① when it reviews Predictor calls ② when a move is above a threshold of, say, 2.2% (for all 3 horizons)."

**From notes:** #44 (DLP p4).

### 4.8 The Learner's review schedule

**Question:** What should the Learner's review schedule be? Each of its four rows has a note: a "?", a "Why?", a "TBD" or a question.

The workbook cites DLP, Learner reviews.

**DLP p7 notes:**
- "?" on the underlined "A deeper review due then for the same event covers both."
- "Why?" on "At the close of the first trading day after the qualifying window's end date (Eastern time)".
- "?" on the circled "replay cutoff".
- "TBD" on the earnings-preview row, where "preview" is circled.
- On the after-earnings row: "But isn't that the predictor's job?", and "TBD" with a bar beside the row.

**From notes:** #53 (DLP p7).

### 5.1 Which EXPLAINED_BY fields are required

**Question:** Which EXPLAINED_BY fields are required, and why? The notes ask to rethink each field one at a time and keep only what's required.

The workbook cites EXPLAINED_BY §5; DLP.

**Issues note:** "Rethink each field one at a time, and keep only what's required, and why."
- Its numbered items are in 5.2 (①, company_id), 5.3 (② and ④, strength) and 2.2 (③, reason).

**From notes:** #12 (Issues).

### 5.2 company_id or ticker

**Question:** Should EXPLAINED_BY identify the affected company by its ticker, if the ticker is unique, instead of `company_id`?

The workbook cites EXPLAINED_BY §2, §5.

**Alternative view:** use the ticker if it's unique.

**Issues note** (①, from p8): "company_id → let's use the ticker if it's unique."

**p8 note**, with an arrow from the circled "Stable ID": "Ticker seems fine."

**From notes:** #12 ① (Issues, p8).

### 5.3 The strength field (weightage)

**Question:** Why is there a strength field, and is it required? Does strength make sense when there may be several calls per day and the reviewer may link several EXPLAINED_BYs?

The workbook cites EXPLAINED_BY §4, §5, §6.

**p7 note**, boxed: "Now, since we may have several calls per day and the reviewer may link several EXPLAINED_BYs, I'm not sure strength would make sense!"
- On the same page, "strength" is circled in "…reason, direction, strength and confidence."

**p8 note**, beside the §5 heading: "what about strength?"

**p9 note:** "Or is it talking abt weightage?", with an arrow to the circled "strength" in `confidence`'s "Separate from strength.", which has a "?" after it.

**Issues notes:**
- ② "Why is there a strength field, and is it required?"
- ④ "Given that we use multiple learner reviews daily and propose using them across various horizons, maybe "weightage" makes sense."

**p11 mark:** "summed weights" is circled.

**From notes:** #11 box (p7), #12 ② and ④ (Issues; p8, p9).

### 5.4 The live/backfill mode

**Question:** Why does each EXPLAINED_BY link store a live/backfill mode?

**DLP p4 note:** "why?", with an arrow from the circled "live/backfill" in the daily EXPLAINED_BY row of the fields table.

**From notes:** #42 (DLP p4).

### 5.5 The identity and replacement rules

**Question:** Are the identity and replacement rules for explanations right and clearly written? The note beside them says "didn't read perfectly".

The workbook cites EXPLAINED_BY §5.

**p9 note**, down the left margin beside a bracket over these four bullets: "didn't read perfectly".

**From notes:** p9 margin note.

### 5.6 A driverUpdate's source date and its Date links

**Question:** Is this right: a driverUpdate links to its source, with the source's publication date, but may still link to Date nodes through EXPLAINED_BY when needed?

The workbook cites EXPLAINED_BY §2, §4.

**p7 note**, at the top of the page: "So my understanding is that driverUpdates/facts link to their source with its publication date, but may still link to Date nodes via EXPLAINED_BY if needed!"
- A curved line links it to the §4 opening paragraph, which has a double bar, ticks and underlines.
- On the same page, the printed "facts" is relabelled "driverUpdates".

**From notes:** #11 (p7).

### 6.1 Grading with the existing return calculation

**Question:** Why can't grading use the exact mechanism already used to calculate hourly, session and daily returns, given a ticker and timestamp?

The workbook cites DLP, Grading and qualifying move.

**DLP p7 note**, at the top of the page, with a bracket down the left margin: "Why can't we use the exact mechanism we used for calculating hourly, session and daily returns, given a ticker and timestamp?"
- On DLP p6, "live save time or replay decision time to fix the end of the" is underlined.

**From notes:** #50 (DLP p7).

### 6.2 What counts as a win

**Question:** What should count as a win?

The workbook cites DLP, Grading.

**DLP p7 note**, beside the circled "wins": "To be thought!"

**From notes:** #51 (DLP p7).

### 6.3 Measuring and showing performance

**Question:** How should paper-trading performance be measured and shown?

The workbook cites DLP, Grading.

**DLP p7 note**, with an arrow from the underlined "paper-trading performance": "This performance, and how to show it, is to be decided!"

**From notes:** #52 (DLP p7).

### 6.4 Driver histories

**Question:** How should the Driver histories be counted? The note marks the call-outcomes count "TBD".

The workbook cites DLP, Driver histories.

**DLP p8 note:** "TBD", with a bar beside "Call outcomes".
- "each with its own count" and "distinct affected company-days linked" are underlined.

**From notes:** #56 (DLP p8).

### 7.1 When a research article is saved

**Question:** Is this assumption right: an article or research news node is saved only when researching a ticker move, and it may link to more than one ticker, for example when it's about a whole sector or macro news?

The workbook cites NMS; EXPLAINED_BY §6.2.

**NMS p2 note**, at the top of the page, with an arrow from the boxed "even when it has no tracked company tickers": "My assumption is that only when we are researching a ticker move do we save an article/research news-type node. Of course it may link to more than one ticker if, for example, it's about a sector as a whole or macro news."

**NMS p4 note**, on the underlined "Broad automatic ingestion of new stories with no tracked tickers remains out of scope": "But as mentioned, that also always starts with a company in mind first."

**From notes:** #18 (NMS p2), #32 (NMS p4).

### 7.2 A research article's company links

**Question:** Is a research article just like a news node, with a MENTIONS link to the company or companies? Does that hold even when it links to a single company, so that it only ever uses MENTIONS, never INFLUENCES?

The workbook cites NMS.

**NMS p2 note**, after the research-exception section: "Super simply, this research article is just like a news node, albeit with a "Mention" link to the company or companies. (Check if this assumption is true even if this news node links only to a single company. So only use Mention, never Influence?)"
- On the same page, "Do not invent company tags, INFLUENCES/MENTIONS links or source-return numbers." and "Any supported stock effect belongs on Date's EXPLAINED_BY link…" are joined by an arrow.

**From notes:** #21 (NMS p2).

### 7.3 Unintended effects of story edits

**Question:** Does the rule for edited stories have any negative unintended consequences?

The workbook cites NMS, "When a story changes".

**NMS p2 note**, with a line from the first bullet: "Sounds fine, but we need to ensure it has no negative unintended consequences."

**From notes:** #22 (NMS p2).

### 7.4 Whether the "unverified" rule is worth it

**Question:** Is it necessary to treat an unstored earlier version's text and companies as unverified? What benefit does it give, and is it worth it, since earlier news versions aren't saved?

The workbook cites NMS, "Before switching on".

**NMS p4 note**, at the top of the page: "Is this necessary, what benefit do we get from it, and is it worth it, since earlier news versions are not saved!"
- It refers to the last sentence of the time rule, where "earlier version isn't stored … unverified" is underlined.

**From notes:** #26 (NMS p4).

### 7.5 Replacing Benzinga

**Question:** With the Benzinga subscription gone, should news come from Massive or from IBKR (which includes Benzinga news)?

The workbook cites NMS, "Before switching on".

**NMS p4 note**, from the circled "Massive" in "Massive news reader": "With the Benzinga subscription gone, we may have to replace it with Massive or IBKR (which includes BNZ news)."

**From notes:** #28 (NMS p4).

### 7.6 Time zones in the news reader

**Question:** Does the news code keep real time zones? The doc says it doesn't; the note expected it to be correct already.

The workbook cites NMS, Massive news reader.

**NMS p4 note**, from the circled "time zones": "to be checked, since I thought it was already correct!"

**From notes:** #29 (NMS p4).

### 8.1 Code-owned values

**Question:** Wherever the docs say "code-owned", should the model write that value instead, in its normal process, so there's no extra machinery?

**Issues note** (relates to p9): "Wherever it says "Code owned", we need to think about whether it makes sense to just have the model write it instead, in its normal process, so as to have no extra machinery."

**p9 note**, from the circled "code-owned" in "IDs, timestamps and change detection are code-owned": "To think if easier way?"

**From notes:** #13 (Issues, p9).

### 8.2 Which rules file EXPLAINED_BY should reconcile

**Question:** EXPLAINED_BY names DRIVER_RULES_Categorized.md as the rules file to reconcile. Should it name DRIVER_RULES.md instead?

The workbook cites EXPLAINED_BY.

**Alternative view:** DRIVER_RULES_Categorized.md is the older design; DRIVER_RULES.md is the latest.

**p2 note**, boxed at the top of the page, with an arrow from the underlined "DRIVER_RULES_Categorized.md": "No, Categorized is older design, latest is Driver_Rules.md."

**From notes:** p2 margin note.

### N.1 Multi-ticker news is usually generic

**NMS p1 note**, joined by a line to a star on the "2 or more total tickers, at least 1 tracked" row: "Makes sense, since when a news story is about more than 1 company, even if not all are tracked, it usually means it's generic."

**Passage** (NMS link table): "2 or more total tickers, at least 1 tracked": "MENTIONS to each company we track; no sector, industry or market links".

**From notes:** #17 (NMS p1).

### N.2 "using Date & Company"

**NMS p3 note**, added after "EXPLAINED_BY separately identifies whose stock is affected.": "using Date & Company".
- In the same bullet, "DriverUpdate" is circled and "none for a genuinely shared fact" is underlined, with "=" beside the bullet.

**Passage** (NMS): "DriverUpdate → FOR_COMPANY → Company identifies whose fact it is: exactly one link for a company-specific fact, none for a genuinely shared fact. … Keep the company in the fact ID, with no stored subject-ID property; EXPLAINED_BY separately identifies whose stock is affected."

**From notes:** #24 (NMS p3).

### N.3 "Company-specific fact extraction stays off until…"

**NMS p3 note**, with a bracket over the bullet: "Not clear what it means or implies, and whether it contradicts the rule above!"
- The rule above is the FOR_COMPANY bullet (N.2).

**Passage** (NMS): "Company-specific fact extraction stays off until FOR_COMPANY, fact IDs and company context consistently identify each subject, and work on one company cannot block, overwrite or falsely complete another's. One whole-story job may handle all companies; only separate company jobs require company-specific selection, locks, completion marks and saved-result keys. A partial read cannot complete the whole story."

**From notes:** #25 (NMS p3).

### N.4 "the cross-source design ?"

**NMS p5 marks:** "the cross-source design" is underlined, with a "?" and an arrow.

**Passage** (NMS, "Not in this change"): "Driver fact ownership (rules 3.2, 3.9): the cross-source design is agreed in EXPLAINED_BY.md §6.1; its rule/contract reconciliation and implementation remain pending."

**From notes:** #34 (NMS p5).

### N.5 Whose fact vs. whose stock

**p4 note**, on the FOR_COMPANY row, with an arrow to the circled `company_id`: "whose fact is it → not necessarily whose stock it affects (for which we have …)".
- Also on p4: "whose fact it is, not necessarily whose stock it affects" is underlined, "none for a genuinely shared fact" is boxed, and the FOR_COMPANY and EXPLAINED_BY lines of the opening diagram are ticked.
- A diagram at the bottom of the page: Date ("trading day") → Explained_BY → driverUpdate → Driver, Source, Company, Driver Period.

**Passage** (EXPLAINED_BY §2):
- "DriverUpdate → FOR_COMPANY → Company": "Exactly one subject company for a company-specific fact; none for a genuinely shared fact. This is whose fact it is, not necessarily whose stock it affects."
- "Date → EXPLAINED_BY → DriverUpdate": "company_id must resolve to the affected Company.id."

**From notes:** p4 margin note.

### N.6 Multi-company stories and MENTIONS

**p5 note**, with an arrow to "No DailyCompanyMoveEvent node, special multi-company News type, or copied time-window fields on every explanation are needed.": "since will be determined by 'Mention' linkages?"
- Meaning, confirmed by the author: no special multi-company News type is needed, because MENTIONS links already show that a story is multi-company.
- Other marks on p5: "explanation does not duplicate or replace it" and "Do not keep competing daily explanations on the source nodes" are underlined; "closing times" and `company_id` are circled.

**Passage** (EXPLAINED_BY §2): "Use the existing Date node and its closing times. No DailyCompanyMoveEvent node, special multi-company News type, or copied time-window fields on every explanation are needed. A Date node is shared across companies; the explanation's company_id identifies whose move is being explained."

**From notes:** p5 margin note.

### N.7 Two driverUpdates across the close

**p6 note**, above the publication-time table: "Predictor calls are typically triggered on driverUpdates created from a single source. But when the learner is reviewing, it may consider 2 driverUpdates (sources) sitting across the market-close dividing line. In that case the date may link to 2 driverUpdates (using EXPLAINED_BY), but which may not follow this rule?"
- Side note: "Actually, each individual one should still follow the same rule."
- "This rule" is the publication-time rule in the table below the note.

**Passage** (EXPLAINED_BY §3, p6):
- "For newly public information, first consider the window ending at the first regular-market close strictly after that source version became public". The table below it gives the first daily Date for each publication time.
- "This table suggests an initial window; it does not assign a causal link or forbid evidence from other dates." "forbid evidence from other dates" is circled, with "=".

**From notes:** #7 (p6).

### N.8 The Friday/Saturday table

**p7 marks:** ticks on the "Friday announcement" and "Thursday announcement" rows, and underlines in the Thursday row. No words.

**Passage** (EXPLAINED_BY §4 table):
- "Friday announcement contributes to Friday's move": "Link Friday to its fact. An unrelated Friday announcement gets no explanation link."
- "Thursday announcement contributes to Friday's move": "Friday may link to that earlier fact if evidence supports its contribution on Friday. Its publication time remains Thursday; a Thursday link is not a prerequisite."
- "Saturday article documents an event that affected Friday": "It may support a later-written explanation of Friday. Preserve Saturday as the article's publication time."
- "The event first happens Saturday": "It cannot cause Friday's already-completed move. Likewise, a midday announcement cannot cause movement before publication merely because it shares the same Date."

**From notes:** #9 (p7).

### N.9 Post-market sources and the next Date

**p5 note**, at the §3 heading: "From previous trading close to today's close, so my assumption is driverUpdates created from sources (such as news) published post-market are considered in the next Date."

**Passage** (EXPLAINED_BY §3):
- "Date identifies the trading day at the end of the measured daily period: the previous trading day's regular close → this trading day's regular close."
- In the publication-time table, "On a trading day: exactly at or after the regular close, including after hours or late evening": "The next trading day."

**From notes:** p5 margin note.

### N.10 Sealing calls

**DLP p5 marks:** two "?"s with arrows: one at "version," in "triggering source ID and version,", and one at the underlined "Multiple qualifying updates in one version and retries reuse that call".

**Passage** (DLP, Predictor): "Seal one graph record per company, triggering source ID and version, separately for live calls and for each replay. Multiple qualifying updates in one version and retries reuse that call. Separate publications may each qualify even when they repeat the same claim."

**From notes:** #46 (DLP p5).

### N.11 The Learner's evidence cutoff

**DLP p6 note:** "why?", with an arrow from the underlined "Use either only when it is available in…".
- The paragraph is bracketed, with "!" beside it, and "evidence cutoff" is circled.

**Passage** (DLP, input cutoff): "Each review and daily explanation keeps its actual save time (created) and the Learner's evidence cutoff. Use either only when it is available in the call's history and its evidence cutoff is at or before the call's input cutoff."

**From notes:** #49 (DLP p6).

### N.12 The Learner's primary task

**DLP p4 note**, at the top of the page: "Basically, the primary task of the Learner is to (1) create the Driver watchlist using EXPLAINED_BY and (2) review calls."

**Passage:** none; the note heads the page, above the table of saved items (Prediction, Learner review, Daily EXPLAINED_BY link).

**From notes:** #41 (DLP p4).

### N.13 Facts usable without EXPLAINED_BY

**p3 note**, with an arrow to the example: "of course, that should be obvious since that's how live trading happens."

**Passage** (EXPLAINED_BY §1): "Facts can be saved and used for trading without an EXPLAINED_BY link. For example, newly issued guidance can inform a decision before a measurable price reaction exists."

**From notes:** p3 margin note.

### N.14 Counting by horizon; live and replay separate

**DLP p3 notes:** "Why?" after "counted by horizon", and "Why?" under the circled "live and replay kept separate".

**Passage** (DLP, Picture D): "The two histories are calculated separately for a company, industry or sector. Call results are counted by horizon, with live and replay kept separate."

**From notes:** #40 (DLP p3).

### N.15 Relative returns without sector and market links

**NMS p1 note**, at the top of the page: "But if there's no sector, industry or market link, we won't be able to calculate relative return, so think hard first."
- In the link table, "Current schema" is written beside "1 total ticker, tracked", and INFLUENCES and MENTIONS are circled.

**Passage** (NMS):
- "2 or more total tickers, at least 1 tracked": "MENTIONS to each company we track; no sector, industry or market links".
- "Each company link carries that company's price moves in today's measuring windows (hourly, session, daily), for the stock, its sector, its industry and the market."

**From notes:** #16 (NMS p1).

### N.16 Last tracked ticker removed

**NMS p2 note:** "Not clear!", with an arrow from the end of the passage.

**Passage** (NMS, research exception): "Newer versions of already saved stories still follow the edit rules, including when the last tracked ticker is removed."

**From notes:** #19 (NMS p2).

### N.17 "News type ?"

**NMS p2 marks:** "News type" is circled, with a "?" and an arrow.

**Passage** (NMS, research exception): "Keep the existing News type and source/version evidence; reuse the article's record when already identified."

**From notes:** #20 (NMS p2).

### N.18 The look-ahead check

**NMS p4 note:** "not clear", circled, with a bracket over the bullet.

**Passage** (NMS, "Before switching on"): "Look-ahead check (hides future prices from predictions): name MENTIONS in its instructions; block the 3 fields it misses (session_sector, session_industry, session_macro) in both pit_gate.py and filters/rules.json."

**From notes:** #27 (NMS p4).

### N.19 The overlapping time window

**NMS p4 note:** "not clear why", circled, with an arrow to the bullet.

**Passage** (NMS, Massive news reader): "re-check an overlapping time window on every check (edits to older stories can still be missed; accepted);"

**From notes:** #30 (NMS p4).

### N.20 Category names in any capitals

**NMS p4 note:** "Why?", with an arrow from the bullet.

**Passage** (NMS, Massive news reader): "match category names regardless of capital letters."

**From notes:** #31 (NMS p4).

### N.21 Historical backfilling

**NMS p5 note**, at the top of the page, with an arrow to the bullet: "Historical backfilling for News ("Mention"-ing) several tracked tickers."

**Passage** (NMS, "Not in this change"): "Bulk downloading historical multi-company news; selectively retrieving an older article for research is allowed under the exception above."

**From notes:** #33 (NMS p5).

### N.22 "Explained_BY" heading

**Issues:** the heading "Explained_BY" (item 3), with nothing under it.

**From notes:** #3 (Issues).

### N.23 Moving §8 to a separate file

**p1 note**, beside a bracket over §8 (pp 19–27) in the contents: "these seem to be more related to code & data issues?"

**p19 note**, at the §8 heading: "from here all the way to page 27 (along with design-decision handoff in driver/prompts) should be a separate file?"

**Current docs:** `EXPLAINED_BY.md` no longer contains §8. `DriverWorkflow/DriverDataAndCodeIssues.md` has a "Return measurements" section with findings R1–R8. DLP and DRIVER_RULES 10.1 link to it.

**From notes:** p1 and p19 margin notes.

### N.24 FINAL_DESIGN.md's older company-link rule

**p2 note**, under the underlined "older company-link rule": "what was it? Is it relevant now?"

**Passage** (EXPLAINED_BY header): "For this revision, FINAL_DESIGN.md is unmaintained background, not an update target; its older company-link rule does not override the agreement here."

**From notes:** p2 margin note.

</details>
