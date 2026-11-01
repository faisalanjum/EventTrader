# News that names several companies

**Decided 2026-10-03 (owner, Fable, Codex). Not built yet.**

## Design
- A story is saved once.
- It keeps the news feed's full ticker list (`symbols`), saved before we drop companies we don't track.
- Count the distinct tickers in that list:

| Tickers | Links from the story |
|---|---|
| 1 | `INFLUENCES` to that company, plus sector, industry and market links (as today) |
| 2 or more | `MENTIONS` to each company we track; no sector, industry or market links |
| none we track | story not saved (as today) |

- Each company link carries that company's price moves in today's measuring windows (hourly, session, daily), for the stock, its sector, its industry and the market.
- These numbers show what the price did. They do not prove the story caused it.
- A missing number stays missing and never replaces a good one.

## When a story changes
- A newer version (real times compared with time zones) replaces the text and ticker list. Its links are fixed in the same step, removing obsolete company, sector, industry and market links. Good price numbers and still-valid company work are kept; changed text may need processing again.
- A late price update for the same company and measuring window still fills missing numbers, even after an edit, but never changes the text, ticker list or times.
- An older or partial version, or the same input read again, changes nothing.

## Reading
- Similar-news searches (the `neo4j-vector-search` agent; the two Python scripts if still used): count both link types, apply company, sector and time limits *before* picking the best results (e.g. score only the eligible stories), and keep each search's current result limit.
- Show the ticker count next to a story, as context only.
- Predictor and learner readers change in their planned rewrite. Until then they don't see `MENTIONS`.
- Company-specific fact extraction stays off until the company is part of fact IDs, job picks, job locks, "done" marks and saved results, so work on one company can't block or overwrite another's.

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
- Stories with no ticker, or only untracked ones like SPY (e.g. "Fed cuts rates"): still skipped.
- Downloading past multi-company stories.
- Who owns a news fact for Driver facts (rules 3.9, P4): still open.

Evidence (in `~/.claude/projects/-home-faisal-EventMarketDB/backups/`): Fable `claude_news_links_review_20261003/FINDINGS.md`; Codex `codex_news_semantics_review_20261003/SEVEN_ADDITIONS_REVIEW.txt` and `NEWS_MULTIPLE_SYMBOLS_PLAN_REVIEW.txt`. Codex's older `NEWS_LINK_PROPOSAL.txt` is out of date on ticker counting.
