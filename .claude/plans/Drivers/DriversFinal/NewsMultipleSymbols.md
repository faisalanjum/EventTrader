# News that names several companies

**Decided 2026-10-03 (owner, Fable, Codex); processing and research-saving rules clarified 2026-11-13. Not built yet.**

## Design
- A story is saved once.
- It keeps the news feed's full ticker list (`symbols`), saved before we drop companies we don't track.
- Count the distinct tickers in that list:

| Tickers | Links from the story |
|---|---|
| 1 total ticker, tracked | `INFLUENCES` to that company, plus sector, industry and market links (as today) |
| 2 or more total tickers, at least 1 tracked | `MENTIONS` to each company we track; no sector, industry or market links |
| none we track | skip new ordinary feed stories; selected research evidence may be saved under the exception below, without Company links |

- Each company link carries that company's price moves in today's measuring windows (hourly, session, daily), for the stock, its sector, its industry and the market.
- These numbers show what the price did. They do not prove the story caused it.
- A missing number stays missing and never replaces a good one.

## Research exception — no tracked tickers

Save an original published article or announcement explicitly selected as research evidence even when it has no tracked company tickers. New ordinary feed stories with no tracked tickers remain skipped. Newer versions of already saved stories still follow the edit rules, including when the last tracked ticker is removed.

**Why:** a Fed article may help explain Apple's move without naming Apple. Keep the existing News type and source/version evidence; reuse the article's record when already identified. Saving it does not prove an effect. Do not invent company tags, INFLUENCES/MENTIONS links or source-return numbers. Any supported stock effect belongs on Date's EXPLAINED_BY link to the source-backed DriverUpdate. Stories with tracked tickers still follow the table above.

This saving exception replaces the former blanket skip rule, not the ordinary feed filter; it adds no source type or new story-to-company relationship. A company-specific DriverUpdate still needs its own FOR_COMPANY link, independently of the article's tags. Research-discovered filings and earnings calls retain their Report/Transcript types; their facts use the same subject rules as News facts. See [EXPLAINED_BY.md §§6.1–6.2](EXPLAINED_BY.md#62-research-articles-without-tracked-tickers--saving-rule) for scope, example and implementation requirements.

## When a story changes
- A newer version (real times compared with time zones) replaces the text and ticker list. Its links are fixed in the same step, removing obsolete company, sector, industry and market links. Good price numbers and still-valid company work are kept; changed text may need processing again.
- A late price update for the same company and measuring window still fills missing numbers, even after an edit, but never changes the text, ticker list or times.
- An older or partial version, or the same input read again, changes nothing.

## Reading
- Similar-news searches (the `neo4j-vector-search` agent; the two Python scripts if still used): count both link types, apply company, sector and time limits *before* picking the best results (e.g. score only the eligible stories), and keep each search's current result limit.
- Show the ticker count next to a story, as context only.
- Predictor and learner readers change in their planned rewrite. Until then they don't see `MENTIONS`.
- `DriverUpdate → FOR_COMPANY → Company` identifies whose fact it is: exactly one link for a company-specific fact, none for a genuinely shared fact. Unresolved company-specific facts stay skipped/held. Keep the company in the fact ID, with no stored subject-ID property; EXPLAINED_BY separately identifies whose stock is affected.
- Company-specific fact extraction stays off until FOR_COMPANY, fact IDs and company context consistently identify each subject, and work on one company cannot block, overwrite or falsely complete another's. One whole-story job may handle all companies; only separate company jobs require company-specific selection, locks, completion marks and saved-result keys. A partial read cannot complete the whole story. See [EXPLAINED_BY.md §6.1](EXPLAINED_BY.md#61-minimal-fact-company-resolution--agreed) for validation, the walkthrough and retry rules.

## Before switching on
- Look-ahead check (hides future prices from predictions): name `MENTIONS` in its instructions; block the 3 fields it misses (`session_sector`, `session_industry`, `session_macro`) in both `pit_gate.py` and `filters/rules.json`.
- Time rule, both link types: a later edit or added ticker is never treated as known when the story first came out, and unfinished price windows never show in earlier views. If the earlier version isn't stored, its earlier text and companies count as unverified.
- Fix-up scripts and docs that assume one company per story: include `MENTIONS`.
- Massive news reader:
  - `published` → created, `last_updated` → updated;
  - keep real time zones (today `bz_news_schemas.py:307` drops them, and `news.py:298` compares times as text);
  - re-check an overlapping time window on every check (edits to older stories can still be missed; accepted);
  - match category names regardless of capital letters.
- Access: our Massive key gets neither Benzinga News nor the one-second prices that today's calculator needs for all price moves. The old Benzinga key is dead.

## Not in this change
- Broad automatic ingestion of new stories with no tracked tickers remains out of scope; the selected-research exception above is the only change to that skip rule.
- Bulk downloading historical multi-company news; selectively retrieving an older article for research is allowed under the exception above.
- Driver fact ownership (rules 3.9, P4): the cross-source design is agreed in EXPLAINED_BY.md §6.1; its rule/contract reconciliation and implementation remain pending.

Evidence (in `~/.claude/projects/-home-faisal-EventMarketDB/backups/`): Fable `claude_news_links_review_20261003/FINDINGS.md`; Codex `codex_news_semantics_review_20261003/SEVEN_ADDITIONS_REVIEW.txt` and `NEWS_MULTIPLE_SYMBOLS_PLAN_REVIEW.txt`. Codex's older `NEWS_LINK_PROPOSAL.txt` is out of date on ticker counting.
