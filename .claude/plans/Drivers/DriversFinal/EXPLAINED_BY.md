# EXPLAINED_BY — working specification

Updated 2026-11-13. Records the agreed shared update process, its two triggers and daily timing, within the working graph design. Remaining decisions are named in section 7. The detailed operating algorithm is being refined in the [scratchpad](EXPLAINED_BY_SCRATCHPAD.md). After the discussion is complete, reconcile [DRIVER_RULES_Categorized.md](DRIVER_RULES_Categorized.md) as the final implementation plan. This document does not mean the workflow is already built.

For this revision, FINAL_DESIGN.md is unmaintained background, not an update target; its older company-link rule does not override the agreement here.

**Keep source-backed company information current. Use significant price moves to trigger deeper research, then link supported explanations to the relevant trading Date(s).** The goal is to trace evidence, track Drivers across companies and time, and use that knowledge for trading.

## 1. One update process, two triggers

1. **Information trigger:** process relevant new Reports, News and Transcripts to discover Drivers or update existing ones, whether or not prices moved. Preserve the source and the publication time of the version being used. Historical sources used to establish company context go through this same update process; the detailed source-selection policy remains under discussion.
2. **Price trigger:** a significant observed move starts deeper analysis. It may be a publication's measured reaction or a move without a useful related publication. The significance threshold and which measurements trigger this work remain to be decided; this document does not invent them.
3. For a price-triggered investigation, reuse saved DriverUpdates and supporting evidence first, then research missing evidence as needed. This may happen after the trading day. Newly found evidence enters the same source-backed update process; an AI explanation by itself is not a source fact. If evidence does not support an explanation, leave the move unexplained.
4. AI judges which source-backed facts, if any, contributed to the observed move and why. It may use newly extracted or already saved DriverUpdates, including supported earlier information. Source timing suggests where to look; it does not prove an effect.
5. Associate each supported daily judgment with the affected company and the trading Date(s) whose moves it explains, using the rules below. Dates are the destination for explanations. An hourly/session trigger does not automatically establish a daily explanation.
6. Code validates the source/fact references, affected Company ID, trading Date and required fields, then saves through the existing shared validation/writing path. Extending that path to this design remains implementation work. Code must not require source publication to fall inside the daily window. AI supplies the meaning judgment; code does not infer causation from timestamps alone.

The significant-move check governs deeper explanation work, not whether a valid fact may exist. Facts can be saved and used for trading without an EXPLAINED_BY link. For example, newly issued guidance can inform a decision before a measurable price reaction exists. No link means no recorded explanation, not proof that the fact had no effect. Historical and live processing use these same rules; later research must never become information supposedly known for an earlier trade. Initial context, ongoing updates and history filling must reuse the regular update process rather than separate company-model machinery.

## 2. What links to what

A **Driver** is the reusable meaning; a **DriverUpdate** is one recorded, source-backed fact occurrence. **EXPLAINED_BY** is a relationship carrying a judgment about that fact's effect on one company's daily move.

When this version is built, Guidance is replaced by Driver with `fact_type = guidance`, and GuidanceUpdate by DriverUpdate.

```text
DriverUpdate ──FROM_SOURCE──────────────► Report / News / Transcript
DriverUpdate ──OF_DRIVER────────────────► Driver
DriverUpdate ──FOR_COMPANY──────────────► Company (company-specific facts only)

Date ──EXPLAINED_BY {company_id, ...}───► DriverUpdate
Date ──HAS_PRICE────────────────────────► Company
```

| Relationship | Meaning and rule |
|---|---|
| `DriverUpdate → FROM_SOURCE → source` | Exactly one source for this fact occurrence. Keep its quote/location and cited version traceable. Date is never its source. |
| `DriverUpdate → OF_DRIVER → Driver` | Exactly one Driver supplies the reusable meaning. Many fact occurrences may belong to the same Driver. |
| `DriverUpdate → FOR_COMPANY → Company` | Exactly one subject company for a company-specific fact; none for a genuinely shared fact. This is whose fact it is, not necessarily whose stock it affects. An unresolved subject is held/skipped, never stored as shared. |
| `Date → EXPLAINED_BY → DriverUpdate` | “This fact is judged to have pushed this company's price up or down during this daily period.” `company_id` must resolve to the affected `Company.id`. |
| `Date → HAS_PRICE → Company` | The existing relationship stores that company's daily price result. The explanation does not duplicate or replace it. |

For this daily design, all EXPLAINED_BY links start at Date, including explanations arising from filings, news and transcripts. Do not keep competing daily explanations on the source nodes. Source-to-company links remain available for their existing purposes; they do not by themselves prove causation.

Use the existing Date node and its closing times. No DailyCompanyMoveEvent node, special multi-company News type, or copied time-window fields on every explanation are needed. A Date node is shared across companies; the explanation's `company_id` identifies whose move is being explained.

## 3. Which Date a judgment explains

**Date identifies the trading day at the end of the measured daily period: the previous trading day's regular close → this trading day's regular close.** It does not replace the source's publication date or the fact's financial reporting period.

```text
Daily return (%) = round(100 × (current close / previous trading close − 1), 2)
```

Use the existing split-adjusted daily closing prices on the price relationships. There is no separate after-hours percentage added. Example: Thursday close $100 → overnight $110 → Friday close $108 gives Friday **+8%**. A temporary overnight rise that reverses is not retained as a separate gain. Friday's previous trading day need not be Thursday if there is a holiday.

For **newly public information**, first consider the window ending at the **first regular-market close strictly after that source version became public**:

| Publication time | First daily Date to consider |
|---|---|
| On a trading day: before dawn, premarket, or regular trading before the close | That trading day. |
| On a trading day: exactly at or after the regular close, including after hours or late evening | The next trading day. |
| Weekend or market holiday | The next trading day. |
| Exactly at or after an early close | The next trading day; use the actual close, not a fixed 4 PM rule. |

Use the existing exchange calendar, timezone-aware times and actual closes, including daylight-saving changes. Display times in `America/Toronto` with EST/EDT. This table suggests an initial window; it does not assign a causal link or forbid evidence from other dates.

A real example: AAPL report `0000320193-23-000005` was published on February 2, 2023 at **4:30:33 PM EST**. Its first daily window ends February 3: $150.82 → $154.50, **+2.44%**. February 2's **+3.71%** had already finished before publication.

Source daily returns normally aim at the same closing interval as the corresponding Date. Use Date's price relationship as the common daily result for this view. Source hourly/session measurements describe other periods, sometimes crossing a regular close; retain their start/end times. Crossing a boundary does not automatically justify links to both Dates. Do not reuse a source's Thursday return as the result for a Friday explanation.

The daily result includes movement before a midday publication. An EXPLAINED_BY link does not claim the fact caused the entire percentage, explain a particular intraday jump, or represent profit achievable after reading the source. A fact's assessed push may oppose the day's net direction.

## 4. Which facts may explain that Date

Choose links by supported contribution to the move, not by publication-date membership. Publication inside the daily window does not automatically earn a link; publication outside it does not automatically exclude one.

| Case | Rule |
|---|---|
| Friday announcement contributes to Friday's move | Link Friday to its fact. An unrelated Friday announcement gets no explanation link. |
| Thursday announcement contributes to Friday's move | Friday may link to that earlier fact if evidence supports its contribution on Friday. Its publication time remains Thursday; a Thursday link is not a prerequisite. |
| Saturday article documents an event that affected Friday | It may support a later-written explanation of Friday. Preserve Saturday as the article's publication time. |
| The event first happens Saturday | It cannot cause Friday's already-completed move. Likewise, a midday announcement cannot cause movement before publication merely because it shares the same Date. |

One day may have several explaining facts. **The same DriverUpdate may explain several days and several companies.** Keep the fact once; each explanation link has its own affected company, reason, direction, strength and confidence. Linking it to another Date does not make it newly published on that Date.

**A separate investigation per day is not required.** One event analysis can support Thursday and Friday together, using the same evidence. If it only establishes Thursday's contribution, do not automatically copy the link to Friday. Extra day-by-day research is not required merely to fill links; each saved link needs a supported judgment for its own company/day.

Preserve when the cited information became public and when the judgment was made. A later edit is not information known at the original publication time. Unknown earlier availability stays unverified. Later evidence may explain the past but must not appear as knowledge available for an earlier trade; `live`/`backfill` alone does not establish that distinction.

Fresh facts remain usable before the daily period finishes. Its final return is then unknown. An assessment made before a later price move occurs is a prediction of that move, not an explanation of an observed outcome. Adding a Date link never changes those times.

## 5. What each explanation stores

The reason is the explanation maker's judgment; the source quote remains with the fact. Retain the existing judgment fields and their independent meanings:

| Field | Meaning |
|---|---|
| `company_id` | Stable ID of the affected Company, not a ticker and not automatically the source's owner. |
| `reason` | Short explanation of why this fact contributed to this company's move during this Date's period. |
| `stock_impact` | `long` or `short`: upward or downward pressure, not necessarily the net return. |
| `weightage` | Assessed strength: 0.1–1.0 in steps of 0.1, or absent if unknown. Not a causal percentage; never force strengths to sum to 100%. |
| `confidence` | Confidence in the attribution: 0–100 in steps of 10. Separate from strength. |
| `llm_producer`, `produced_mode` | Who made the judgment and its existing `live`/`backfill` mode. Different producers may disagree. |
| `created` | When the current judgment became available. Code stamps each completed result once; replacement uses the new result's time, retries preserve it. Never backdate it to the explained Date or source publication time. |

**Agreed identity: Date + affected company + DriverUpdate ID + producer. Keep only the latest valid completed judgment for each key.** IDs, timestamps and change detection are code-owned.

- Replace all judgment fields, including reason, mode and `created`; clear optional values now unknown. Different facts and producers keep separate links. Newer judgments win in either `live` or `backfill` mode, replacing the old live-over-backfill priority.
- Order results by their fixed `created` time, not database arrival. Exact retries change nothing; older results cannot overwrite newer ones. Hold conflicting results with equal timestamps.
- Change only reassessed keys. Remove an explanation only when explicitly withdrawn; omission, failed or incomplete work does not remove links or facts. The existing job/write path must also reject delayed older results after withdrawal; verify this before activation.
- Keep no explanation-version history in this graph view. Exclude judgments produced after a trading decision's time. Overwritten earlier judgments are unavailable here; evaluate past trades from decisions/inputs actually recorded before their outcomes, or treat that history as unavailable.

## 6. Source and company examples; simple retrieval

These examples are illustrative, including company tickers that may not be in the current database.

| Source/evidence | Facts and explanations |
|---|---|
| A report about AAPL raising its forecast | One forecast fact → Report; Date → EXPLAINED_BY `[AAPL]` → that fact. Single-company News and Transcript work identically. |
| One news story gives AAPL and MSFT revenue figures | Two company-specific facts → the same News. Each affected company's daily explanation points to the relevant fact. The facts may share a reusable revenue Driver. |
| One news story reports a Fed decision | One shared fact → News; separate company-specific explanation links may point to it. Their directions and strengths can differ. |
| One announcement reports a deal affecting buyer and seller | A genuinely shared deal fact may explain both companies through separate links. Sharing is not limited to macro events. Separate claims remain separate facts. |
| Research finds evidence explaining a move | Save the original supporting article/announcement, preserve its timing, and link its fact to the explained Date. Search or an AI answer is not a substitute for the original evidence. |

**FOR_COMPANY identifies whose fact it is; EXPLAINED_BY.company_id identifies whose price move it explains.** One article containing AAPL's and MSFT's revenue therefore produces two distinct company-specific updates linked to the same News, each with FOR_COMPANY to its own subject. Each update's identity, financial periods and history follow that subject, even when it explains another company's stock move. Section 6.1 records the agreed storage and processing rules. Keep a genuinely shared fact, such as one acquisition, once, without FOR_COMPANY.

**The affected company need not be mentioned in the source.** For example, `Date → EXPLAINED_BY {company_id: B} → DriverUpdate about A` is allowed when a supported reason connects A's event to B's daily price move. Reuse the same DriverUpdate and source; do not invent a source mention of B. A company tag alone does not establish an effect. This allowance requires no automatic search across competitors or suppliers.

NewsMultipleSymbols.md's `INFLUENCES`/`MENTIONS` design describes source-company connections and measurements. It does not decide EXPLAINED_BY or resolve fact ownership. An explanation for a company does not require an existing source-return relationship to that company; its shorter source-specific returns may therefore be unavailable.

**Remove “filing wins” for this daily design.** Good earnings and separate afternoon news can both matter. A filing's presence or later arrival must not suppress other supported daily explanations.

**Agreed initial duplicate handling:** allow separate links for the same claim reported by different sources, avoiding extra cross-source matching. Accept repeated evidence, but do not treat link counts or summed weights as independent trading support. Replays reuse the same explanation key under section 5. This replaces A2.2's one-source-per-claim restriction.

Read by the question being asked:

- **Company/day:** select Date's EXPLAINED_BY links with that `company_id`, keeping producers distinct; join the same Date's HAS_PRICE to that Company for the daily result. Missing or unusable returns stay unknown, never zero.
- **Source:** follow incoming FROM_SOURCE to its facts, then incoming EXPLAINED_BY to their company/day judgments.
- **Driver:** follow incoming OF_DRIVER to its facts, then their sources and explanation links to trace history across companies and days. Repeated reports of one move are not independent trading outcomes.

Evaluate trading usefulness using decisions recorded before their outcomes, including unsuccessful signals and quiet days; explanations collected only after large moves are insufficient.

### 6.1 Minimal fact-company resolution — agreed

**Store whose fact it is with `DriverUpdate → FOR_COMPANY → Company`, replacing the earlier stored `subject_company_id` proposal.** EXPLAINED_BY's `company_id` still identifies whose stock it affects. This reuses the existing guidance/company link pattern and lets company reads reach facts without price explanations. The design is agreed; implementation remains pending.

| Fact in one story | `FOR_COMPANY` |
|---|---|
| Apple's revenue outlook | One link to Apple's existing Company node |
| Microsoft's revenue outlook | One link to Microsoft's existing Company node |
| A Fed decision or genuinely shared deal event | No link |

Each fact links to that story and may explain several companies' moves. Apple/Microsoft are illustrative; required IDs must exist in the company catalogue.

**Applies to News, Reports and Transcripts.** Reports keep their filing/filer identity; Transcripts keep their company-call identity. Their fact extraction, IDs and company-dependent lookups must still use each fact's subject. Example: A's acquisition filing states B's revenue; the Report remains A's filing, while that DriverUpdate identifies B and uses B's calendar/history. Keeping the source nodes does not leave their fact processing unchanged.

1. **Subject:** every company-specific fact has exactly one FOR_COMPANY link to the existing Company identified by its quote/context, even when the source already has one owner. The subject is immutable with the fact ID. Genuinely shared facts have no link; never infer a missing subject from the source owner. An unresolved company-specific subject, including a company absent from the catalogue, uses the existing skip/hold outcome and reason; do not store it as shared or create a placeholder Company. Several affected stocks do not make a company-specific fact ownerless.
2. **Identity:** retain `du:{source_id}:{driver_name}:{fact_scope}` and add a code-owned `subject_company=<Company.id>` scope part for company-specific facts. Processing carries the resolved `subject_company_id` to build the ID and link; it is not stored as a DriverUpdate property. The same validated Company ID governs combining, conflict detection and history. The link target must match the ID's company; shared facts have neither that scope part nor FOR_COMPANY. Two companies' equal figures remain separate. Subject is not a new Driver name or slice.
3. **Distinct facts:** "A buys B for $1 billion; C buys D for $1 billion" describes two deals, even with the same source, Driver and amount. Different IDs are required; shared facts and discrete actions use their existing `source_location` (exact original passage/cells and version) in scope. Replays of the same occurrence keep its ID; ambiguous locations need refinement or rejection. This extends 5.9's location-protection pattern and the combining rules. Repeated occurrences at different locations may remain initially, without counting as independent support. The current value-based `quote_hash` cannot distinguish equal-valued deals. Location identifies the occurrence, not a history series across sources.
4. **Processing:** one job per story is optional. One `story123` job may handle both companies; separate jobs need `story123:Apple` and `story123:Microsoft` work keys for selection, locks, completion and saved results (illustrative labels). Fact IDs identify subjects in either layout. No company's work may block, overwrite or falsely complete another's. A whole-story job finishes only after its full input is accounted for as saved/skipped/held, with reasons for non-written outcomes; Apple alone cannot finish the story. Unchanged reruns reuse facts. Retain existing atomic-write and source-version rules.
5. **Company context:** reuse existing period, history, segment/slice and XBRL functions with each fact's subject, resolving context once per company in the job. Guidance confirmation, prior-guidance/withdrawal and surprise matching must use that same subject. Preserve exact source dates and existing calendar checks; calendar-versus-fiscal interpretation is per fact. Shared facts borrow no participant's fiscal calendar. Required periods need their own supported basis. XBRL attachments still need proof for the correct source, company, period, measure, units and slice; identifying a subject does not let News borrow another filing's numeric evidence. Existing supported unbound-text behavior remains available.
6. **Admission and write:** replace 3.9's blanket one-owner gate. Every fact still has exactly one FROM_SOURCE and one OF_DRIVER; the source may describe zero, one or many companies. Keep source-type, evidence and version requirements, including Report filer and Transcript call identity; section 6.2 covers News saving. Save the fact and required links together. On creation and reuse, validate FOR_COMPANY's zero/one count and agreement with the fact ID; a relationship alone does not prove the subject is correct. Conflicting subjects are held, never silently relinked or given a second subject.
7. **Reading:** find a company's own facts through incoming FOR_COMPANY, including facts with no EXPLAINED_BY. Find assessed price effects through EXPLAINED_BY's `company_id`. Retrieve shared facts through their Driver/source and any explanations. A missing company link on a company-scoped fact ID is invalid, not shared. Source mentions supply candidates, not proof that every fact concerns every named company. No stored Driver-to-Company relationship is needed.

**One-story example:** save the News once; read it; extract Apple's and Microsoft's facts with their quotes; assign each subject and its company context; reuse/create the appropriate Driver(s); build separate company-aware fact IDs; save both DriverUpdates, each with FROM_SOURCE to that News, OF_DRIVER to its Driver and FOR_COMPANY to its own Company. Complete the task under rule 4 above. EXPLAINED_BY is a separate judgment, not required to create these facts.

**Reuse:** `Asset` does not require one company; the period resolver accepts company context. Use the existing relationship-writing pattern for FOR_COMPANY. Update input fields, IDs, combining/validation and company-context callers; do not add a stored subject property. No new node type, registry, job framework or extra AI call is required.

**Prior checks:** 796 unique Company IDs; no Driver/DriverUpdate nodes. Report `0001193125-25-168142` distinguishes filer UNP from referenced NSC. Read-only company/fiscal lookups worked. The reference writer merged equal-valued different-company inputs sharing the old ID; true repeats also merged. The period resolver accepted a periodless shared action and rejected a fiscal-year claim without company context. These are design checks, not production validation.

The subsequent read-only review confirmed all 8,432 GuidanceUpdates have exactly one FOR_COMPANY. The current Driver input/ID checks and writer do not yet support the agreed subject rule; the existing guidance pattern is a reuse point for its planned replacement, not proof Driver writing is ready.

**Implementation handoff:** reconcile 3.1–3.3/3.9 and affected 5.2–5.5/5.9 rules in DRIVER_RULES_Categorized.md at the end of this discussion. Before building, align the active input/writer/read contracts and tests, including ChannelContract.md, BUILD_AND_OPERATIONS.md, company-dependent reads and the news extraction gate, and the Learner's prompt (scripts/earnings/earnings_orchestrator.py passes ACTUAL_RETURN: allowed for historical explanations under the new A2.5, but its output must follow A2 and predictions must never see the outcome). Recheck actual engine entry points; `driver_reference/core` is reference behavior, not proof of deployment.

Before activation, test all four fact types and supported sources: different companies with equal/unequal values, true replays, different fiscal calendars, shared facts, two equal-valued deals, unresolved subjects, missing/extra/wrong FOR_COMPANY links, ID/link disagreement, atomic writes, guidance confirmation/withdrawal, financial attachments, partial reads, edits, retries and concurrent submissions. Include accepted, skipped and held outcomes. This plan update makes no runtime code or database changes.

### 6.2 Research articles without tracked tickers — saving rule

**Save an original published article or announcement explicitly selected as research evidence even when it has no tracked company tickers. New ordinary feed stories with no tracked tickers remain skipped. Newer versions of already saved stories still follow the edit rules, including when the last tracked ticker is removed.** This exception replaces the former blanket skip rule in [NewsMultipleSymbols.md](NewsMultipleSymbols.md); it is recorded in the plan, not implemented by this edit.

**Why:** evidence can explain a company's move without naming that company. A News node still represents one published article, whether found through the feed or research. Reuse its existing record when already identified; preserve original evidence and publication/version times. An AI explanation or search snippet cannot substitute for the source.

Selective retrieval of older research articles is allowed; bulk historical news downloads remain outside this change.

**Links:** keep the existing ticker-based INFLUENCES/MENTIONS rules when applicable. With no tracked tickers, no News-to-Company link is required. Do not invent tags, source-company links or source-return measurements because research concerns a company. A company-specific fact still needs its own FOR_COMPANY under section 6.1, independently of the article's tags. Saving evidence does not itself establish a price effect.

**Example:** save an untagged Fed article as News; its Fed DriverUpdate links FROM_SOURCE to it. A supported `Date → EXPLAINED_BY {company_id: Apple} → DriverUpdate` records Apple's assessed effect. No `MENTIONS → Apple` link is needed.

This saving exception concerns News only. Research that finds an SEC filing or company earnings call keeps the existing Report or Transcript type and required identity; their facts follow section 6.1. Other source formats are not automatically admitted. Implement through the existing source-saving path, keeping the ordinary feed filter and checking both admitted research evidence and skipped feed stories.

## 7. Remaining decisions and implementation work

The remaining design choices here are significant-move settings and the detailed source/research policy. Fact identity, latest-explanation replacement and the point-in-time rule are agreed; their implementation and final rulebook/contract reconciliation remain work.

| Item | Required decision or reconciliation |
|---|---|
| Significant move | Choose the benchmark, per-period thresholds and measured intervals, including moves without a source. None has been chosen here. |
| Operating algorithm | Agree the starting source set, ongoing source coverage, history limits and research budget. Reuse the same update process throughout; see the scratchpad proposal. |
| Fact subject/ownership | Agreed in section 6.1: FOR_COMPANY for the subject, company in the fact ID, no stored subject property. Reconcile the named rules/contracts and verify implementation; no mandatory job count. |
| Repeated reporting and explanation identity | Agreed in sections 5–6: separate source facts may coexist; the latest valid judgment replaces the same explanation key. Reconcile A2.2/A2.4 and remove live-over-backfill priority. Verify replacements, retries, withdrawals, delayed writes and decision-time filtering. |
| Explanation versus prediction | Agreed below. Reconcile A2.5/1.14/7.6 and P7 with historical explanations seeing observed returns, while predictions use only information available at their decision time. |
| Research-source admission | Saving rule settled in section 6.2 and NewsMultipleSymbols.md: selected original research evidence may have no tracked tickers; ordinary feed filtering remains. Implementation and validation are still required. |
| Final graph and contract alignment | Replace source/DCM daily targets and A2.7 filing suppression; preserve A2.8's source-backed facts rule. Align 3.12, A2.3, P3 and the active verdict contract, including company, reason, identity and change detection. |

**Agreed replacement for A2.5:**

> Historical explanations may use observed returns and later evidence, but predictions must use only information available at the decision time, and later explanations must never be presented as earlier predictions.

The [scratchpad](EXPLAINED_BY_SCRATCHPAD.md) retains supporting review notes. Section 8 below contains the return-measurement findings and required follow-up so the owner and next bot do not need to read the scratchpad to find this work. Those findings do not add automatic daily investigations to this design. Finish the remaining discussion, finalize this document, then reconcile DRIVER_RULES_Categorized.md before implementation.

## 8. Return measurements — open checks for the next bot

**Status: documented, not fixed or cleared for trading validation.** These findings concern existing calculation code and saved price data; they do not by themselves require a different graph design. Before using these returns to select significant moves or evaluate Drivers, recheck the current code and database, resolve the affected cases or explicitly exclude unverified measurements from that evaluation, and report whether any agreed rule above needs reconsideration. Do not change graph rules merely to accommodate a bad timestamp or price.

The counts below come from the **November 13, 2026 read-only audit**, not a promise that the database is unchanged. During this handoff, all 12 previously reviewed Python files still matched their saved hashes, and a fresh local reproduction still failed the early-close case; ordinary-day daily checks passed. This handoff did **not** rerun the full database census or change runtime code/data. All example times below use `America/Toronto` with EST/EDT.

### Findings, exact examples and required checks

| Item | Finding and its limit | What the next bot must check |
|---|---|---|
| R1. Early-close error | **169 sources: 157 News + 12 Reports.** For November 24, 2023 at **3 PM EST**, the helper assigns a daily end of **1 PM EST that day**, before publication. Its hourly window is **4–5 AM EST** and session end **9:35 AM EST**, also before publication. | Reproduce in `MarketSessionClassifier` before fixing it. The agreed daily rule instead selects **November 24, 1 PM EST → November 27, 4 PM EST**. Inspect all regular/extended-session branches, including hardcoded 4 PM checks; use native calendar closes. An early regular close does not by itself establish the extended-hours closing time. Check daily, hourly and session paths together. |
| R2. Inconsistent source dates | **12 News** have daily ends on earlier dates for reasons other than R1. Example: `bzNews_19018768` has `created` **January 5, 2022, 9 AM EST**, but daily end **January 5, 2021, 4 PM EST**. Which stored field is wrong is not established. | Check original publication/version evidence and the write path. Do not blindly recalculate from `created` until the timestamp is verified. Leave unverifiable earlier availability unknown. |
| R3. Conflicting daily returns | TENX Report `0000950170-25-071382`, published **May 14, 2025, 4:09:24 PM EDT**, has daily end **May 15, 4 PM EDT** and `daily_stock = −1.37%`; that Date's Company price edge has `daily_return = +0.35%`. Stored closes **5.68 → 5.70** independently yield **+0.3521%**. The underlying price-input cause is not proven. | Compare the actual start/end prices, selected bar timestamps, adjustment settings, trade eligibility and data versions used by both calculation paths. Date summaries use grouped daily bars; source returns use second-aggregate endpoints, potentially with backward fallback. Matching intended windows does not establish identical valid inputs. Recalculate independently; do not assume either feed is correct merely because its arithmetic works. |
| R4. Missing saved windows | **9,608 Transcripts + 9 Reports** have no saved daily schedule. **9,373** of those Transcripts have daily return values, so missing schedules do not mean missing returns. | Establish the actual source availability and reconstruct start/end windows from verified evidence and the relevant calculation path. Conference start does not establish when the full transcript or later Q&A became available. A reconstructed intended window alone does not prove which prices a historical calculation actually used. Unverified measurements remain unverified. |
| R5. Edited News | **3 cases:** `bzNews_47218826`, `bzNews_50489449`, `bzNews_50957341`. Daily ends match later `updated` times rather than original `created` times. This may be valid for revised content. | Identify the source version measured and its availability; inspect how text, timestamps, schedules and return updates are written together. Do not attach today's edited text to an earlier trading decision or automatically replace a valid edited-version window with the original one. |
| R6. Publication exactly at close | Report `0000016058-23-000183`, **December 27, 2023, 4 PM EST**, has a daily window ending at that instant. This is a boundary convention to reconcile, distinct from R1's clear before-publication error. | Apply section 3's agreed **strictly after publication** rule: the first daily window ends **December 28, 2023, 4 PM EST**. Check exact-close behavior on ordinary and early-closing days, including nearby timestamps. |
| R7. Early-close price timestamps | **6,306 Company price edges** say 4 PM Eastern on days whose actual regular close was 1 PM Eastern. This establishes a timestamp mismatch, not that the closing-price values are wrong. | Inspect the Date-to-Company `HAS_PRICE` writer and provider timestamp meaning. Compare with Date's actual calendar close; distinguish period-end time, trade/bar time and when the data became available. Do not infer an earlier information leak or wrong price solely from a late timestamp. |
| R8. Missing/unusable returns | The earlier full source-value inventory found **5 nonfinite daily returns: 1 News + 4 Reports**, plus **one list-valued Report hourly return**. Other returns are absent. Missing and invalid values are not zero. | Audit the full current population and each consumer's type/missing-value handling. Inspect and reuse existing normalization where appropriate; check its actual handling of lists, NaN and infinity rather than assuming every case is covered. Report unusable values separately and exclude them from numerical comparisons and significance tests until resolved. |

### Audit baselines to reproduce

Compare saved daily ends with the native exchange calendar's first regular close strictly after the **stored source time**, while separately checking whether that time really belongs to the cited content version. A timestamp match alone does not verify publication history.

| Source | Matched stored source time/calendar | Needs review | No saved daily schedule | Total |
|---|---:|---:|---:|---:|
| News | 348,498 | 172 | 0 | 348,670 |
| Report | 42,611 | 13 | 9 | 42,633 |
| Transcript | 0 | 0 | 9,608 | 9,608 |
| Total | 391,109 | 185 | 9,617 | 400,911 |

The **185** review cases are R1 **169** + R2 **12** + R5 **3** + R6 **1**. Do not add the missing schedules to that category or classify all review cases as proven bugs. The original audit also checked **1,213 Date nodes** against the calendar and **655,858 Company–Date price edges**; **649,552** price timestamps matched the calendar close and **6,306** were later than the early close. Decode stored `is_trading_day` string values `1`/`0` explicitly when checking Date fields.

For return disagreements, the earlier comparison selected Date from `returns_schedule.daily` converted to Eastern, joined that Date's `HAS_PRICE` to the **same Company**, and compared source-edge `daily_stock` with `daily_return`. It found:

| Source → Company relationship | Finite paired values | Difference greater than 0.02 percentage points | Strictly opposite signs |
|---|---:|---:|---:|
| News `INFLUENCES` | 231,940 | 106,353 | 918 |
| Report `PRIMARY_FILER` | 41,384 | 21,599 | 167 |
| Report `REFERENCED_IN` | 445 | 246 | 3 |

Another **117,660** pairs lacked at least one value and **2** pairs were nonfinite. These paired counts have a different scope from R8's full source inventory. They are relationship comparisons, not independent events/trades or proof every paired period is valid. Transcripts were excluded from this comparison because schedules were absent. Recheck any newly supported relationship types too. Exclude missing/nonfinite values explicitly and test opposite signs with `(a < 0 and b > 0) or (b < 0 and a > 0)`, not a multiplication shortcut that mishandles NaN.

**Positive controls:** AAPL Report `0000320193-23-000005`, published **February 2, 2023, 4:30:33 PM EST**, has daily end **February 3, 4 PM EST**; source and Date both give **+2.44%** from **150.82 → 154.50**. Locally, February 2, 2023 at **11 AM EST** selects a daily end that afternoon at 4 PM, and **4:30 PM EST** selects February 3 at 4 PM; both still pass. Keep valid cases alongside failure cases so a fix cannot simply shift every source to the next day.

### Code and evidence to inspect

- `utils/market_session.py`: `MarketSessionClassifier.get_market_session`, `get_trading_hours`, `get_session_data_structure`, `get_start_time`, `get_end_time`, `get_interval_start_time`, `get_interval_end_time`, `get_1d_impact_times`.
- `eventReturns/EventReturnsManager.py`: `_calculate_return_times` and the price-calculation path; `eventReturns/ReturnsProcessor.py`: readiness, scheduling and late-price updates.
- `eventReturns/polygonClass.py`: `get_daily_market_summary`, `get_returns_indexed`, `get_last_trade`. The latter selects second-aggregate closes and can look backward up to five days; the caller currently loses the selected bar's timestamp. Verify actual endpoint freshness and valid fallback behavior.
- `neograph/Neo4jInitializer.py` and `neograph/EventTraderNodes.py`: Date fields and `HAS_PRICE` values/timestamps; `neograph/mixins/news.py` and `redisDB/TranscriptProcessor.py`: source creation, edits and availability; `scripts/earnings/builders/inter_quarter_context.py:_norm_ret`: existing return normalization.
- Native packages checked: **exchange_calendars 4.10** (`XNYS`, `session_close`, `date_to_session`, `previous_session`, `next_session`) and **polygon-api-client 1.14.4** (`get_grouped_daily_aggs` and aggregate requests). Recheck the installed versions and native APIs before changing code; the regular-close calendar capability already exists.
- Prior machine-readable evidence, if still available: `/tmp/driver_explanation_review_a6f51esx/` contains `timing_review_20261113.json`, `return_comparison_corrected_20261113.json`, `audit_returns.json`, `native_checks.json` and `timing_review_source_hashes_20261113.json`. Temporary files are supporting evidence only; this section records the required findings independently. The corrected comparison supersedes the affected counts in `window_audit.json`. If files are gone, rerun the stated checks rather than assuming the issue disappeared.

### Instructions and completion report for the next bot

1. **Recheck before concluding.** Read current code and relevant plans; record the code revision/hashes, installed versions and audit time in Eastern. Run read-only Neo4j checks over the complete applicable population, preserving counts and reasons for valid, mismatching, missing and unverified cases. Do not describe this older audit as a new database check.
2. **Check the whole class of errors.** Test ordinary days, before/premarket, regular trading, after-hours/closed-market releases, exact and early closes, weekends, holidays, daylight-saving changes and source edits. Derive expected boundaries independently from the native calendar and verified extended-hours policy. Examine hourly/session starts and ends as well as daily ends; native capabilities must be inspected and exercised before custom logic is added.
3. **Fix at the existing boundary when repair work is authorized.** First reproduce failures with tests; then make the smallest general fix in the existing helper/writer, with positive controls, focused and relevant regression suites. A code fix does not repair saved database records automatically. **Database writes require the owner's explicit approval.** This documentation request itself authorizes no repairs, migrations or paid data/model runs.
4. **Report the actual impact.** For each R1–R8 item, state whether it changes the selected Date, the measured return/sign, significant-move selection, prediction-time information availability or only metadata. Identify affected saved records and any explanations/evaluation results requiring recheck. Keep section 3's daily meaning unless evidence demonstrates a design conflict; bring any such conflict to the owner before changing that rule. Preserve the agreed point-in-time rule in section 7.
5. **Close the loop in this document.** Update R1–R8 here with status, current counts, evidence, tests, remaining uncertainty and any approved correction. Finish with a short owner-readable statement of what is fixed, what remains unverified and whether the measurements are usable for the proposed trading evaluation. Do not mark the work complete because tests pass or the issue is described. Reconcile the final findings with DRIVER_RULES_Categorized.md during the agreed final-plan update.
