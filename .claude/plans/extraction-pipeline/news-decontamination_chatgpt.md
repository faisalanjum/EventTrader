Changed only 3 files. No Python/runtime/Kubernetes code was edited. No Neo4j writes/schema changes were made.

  Files

  - news.md:1
  - news-queries.md:1
  - news-primary.md:1

  1. assets/news.md

  - Reworded the intro from “Per-source extraction rules” to “Per-source profile” at news.md:3.
  - Replaced the old one-line data-structure statement with a stricter source-shape definition: “flat, single-node source; no
    child content nodes; no hierarchical sections” at news.md:10.
  - Rebuilt the field table at news.md:14.
  - Changed n.id description from generic “Unique Benzinga news ID” to canonical bzNews_* wording at news.md:18.
  - Changed n.title description from “often contains complete forward-looking content” to a pure source fact: populated on all
    current nodes at news.md:19.
  - Changed n.body description from “may be empty (~12%)” to “empty on a meaningful minority” at news.md:20.
  - Changed n.teaser description from “often truncated version of body” to “supplemental text when present” at news.md:21.
  - Changed n.created description from a raw field label to a behavioral rule: default public point-in-time unless type
    contract says otherwise at news.md:22.
  - Added n.updated row at news.md:23.
  - Added n.url row at news.md:24.
  - Added n.authors row and explicitly documented it as a JSON array string at news.md:25.
  - Changed n.channels from vague “comma-separated / JSON-like” to exact “JSON array string” and explicitly marked it as a
    routing hint, not truth source, at news.md:26.
  - Changed n.tags from generic “topic tags” to exact “JSON array string” plus editorial-metadata note at news.md:27.
  - Added n.market_session row at news.md:28.
  - Added n.returns_schedule row and documented it as a JSON object string with hourly/session/daily windows at news.md:29.
  - Added an entirely new “Relationship Context” section at news.md:31.
  - Added the News -> Company rule with exact current-graph note “0 or 1 company; one outlier is companyless” at news.md:34.
  - Added sector, industry, and market-index edge notes at news.md:35, news.md:36, and news.md:37.
  - Added the rule “use edges for routing/context, but article text is authority for attribution” at news.md:39.
  - Added a new “Current Graph Notes” section at news.md:41.
  - Added the note that title, created, updated, url, authors, channels, market_session, and returns_schedule are populated on
    all current nodes at news.md:43.
  - Added the note that body is empty on roughly 10% of current nodes at news.md:44.
  - Added the note that current graph shows no teaser-without-body pattern at news.md:45.
  - Deleted the entire old “Channel Filter (Pre-LLM Gate)” section.
  - Deleted the old “Primary Channels” table.
  - Deleted the old “Secondary Channels” table.
  - Deleted the old hardcoded 4-channel query example.
  - Deleted the old “Supplementary Fulltext Recall” block with guidance OR outlook OR expects ....
  - Deleted the entire old “Scan Scope” section with title/body guidance examples.
  - Deleted the old headline examples for Apple/Tesla/Microsoft/Amazon.
  - Deleted the old body-content bullets that mixed source behavior with guidance semantics.
  - Added a new generic “Content Fetch Order” section at news.md:49.
  - Added “Step 1: Load the News payload” and pointed it to query 6A at news.md:51.
  - Added “Step 2: Use discovery queries when batching” with 6B/6C/6D/6E roles at news.md:55.
  - Added “Step 3: Read the text fields in this order” with title, then body, then teaser at news.md:62.
  - Added a new “Revision Semantics” section at news.md:68.
  - Added the rule that updated is revision metadata and ingest keeps newest title/body/teaser by updated while always
    refreshing metadata fields at news.md:71.
  - Added the rule that disclosure timing should default to created unless the type explicitly models revisions at news.md:72.
  - Deleted the entire old “Period Identification” section.
  - Deleted the old period-pattern table.
  - Deleted the old asset-level given_date rule.
  - Deleted the old asset-level source_key rule.
  - Deleted the entire old “Basis, Segment, Quality Filters” section.
  - Deleted the News-specific “basis defaults to unknown” statement.
  - Deleted the duplicated given_date / source_key section under basis/quality.
  - Added a new generic “Source Interpretation Traps” section at news.md:76.
  - Added the generic mixed-attribution warning at news.md:78.
  - Added the rule that channels and tags are routing hints, not acceptance rules, at news.md:79.
  - Added the rule that relationship context is not enough for attribution at news.md:80.
  - Added the rule that period semantics must be derived by type-specific logic because News has no embedded fiscal-period
    fields at news.md:81.
  - Deleted the entire old “Duplicate Resolution” section.
  - Rewrote the empty-content table at news.md:85.
  - Changed the first empty-content case to explicitly mention teaser-empty at news.md:89.
  - Changed the second case to say title + body are standard and teaser is optional help at news.md:90.
  - Added a new third case for title empty but body or teaser present at news.md:91.
  - Changed the terminal empty case from only title/body empty to title/body/teaser all empty at news.md:92.
  - Replaced the version footer with a new v1.2 note describing the source-only rewrite at news.md:95.

  2. assets/news-queries.md

  - Changed the intro from “news articles” to “News nodes” at news-queries.md:3.
  - Renamed 6A from “News Content by ID” to “News Payload by ID” at news-queries.md:9.
  - Expanded 6A from returning 4 fields to returning 12 fields at news-queries.md:11.
  - Added n.id, n.teaser, n.updated, n.url, n.authors, n.tags, n.market_session, and n.returns_schedule to 6A.
  - Changed the 6A empty check from “both title and body empty” to “title, body, and teaser all empty” at news-queries.md:27.
  - Added a note that authors, channels, tags, and returns_schedule are JSON strings in Neo4j at news-queries.md:28.
  - Renamed 6B from hardcoded channel-filtered news to “All News for Company (Date Range Required)” at news-queries.md:30.
  - Deleted the old hardcoded channel filter from 6B.
  - Added n.teaser, n.updated, n.market_session, and n.url to 6B at news-queries.md:38.
  - Changed 6B ordering from ascending to descending at news-queries.md:47.
  - Repurposed 6C from “All News for Company” to “Channel-Filtered Company News (Caller-Supplied Channels)” at news-
    queries.md:50.
  - Added the rule “Use only when the extraction type defines a channel strategy” at news-queries.md:52.
  - Changed 6C to use $channels input rather than hardcoded channel names at news-queries.md:58.
  - Implemented exact-ish JSON-string membership matching in 6C with CONTAINS ('"' + channel + '"') at news-queries.md:58.
  - Added n.updated and n.market_session to 6C at news-queries.md:62.
  - Replaced old 6D “News with Body Content” with “News Influence Context by ID” at news-queries.md:69.
  - Deleted the old 6D body-fetch query.
  - Added optional matches to Company, Sector, Industry, and MarketIndex in 6D at news-queries.md:72.
  - Added collected outputs company_tickers, company_names, sectors, industries, and market_indexes in 6D at news-
    queries.md:77.
  - Replaced old 6E “Earnings Beat/Miss News (for Context)” with “Company News by Market Session” at news-queries.md:86.
  - Deleted the old hardcoded n.channels CONTAINS 'Earnings' filter from 6E.
  - Added n.market_session = $market_session filter in 6E at news-queries.md:94.
  - Added n.updated and n.market_session to the 6E return at news-queries.md:95.
  - Changed 6E ordering from ascending to descending at news-queries.md:102.

  3. types/guidance/assets/news-primary.md

  - Kept the file in place as the only guidance-specific News rules file at news-primary.md:1.
  - Changed routing step 2 from “for batch processing: 6B” to “for batch processing: 6C with caller-supplied channels” at news-
    primary.md:9.
  - Added a new “Recommended guidance channels for batch discovery” block at news-primary.md:11.
  - Added core channels Guidance, Earnings, Previews, Management at news-primary.md:12.
  - Added optional recall expansion channels Earnings Beats, Earnings Misses at news-primary.md:13.
  - Added the warning that channel matches are recall aids only, not proof of company-issued guidance, at news-primary.md:15.
  - Replaced the old one-line “Critical Rule: Company Guidance ONLY” section with a fuller “Attribution Rule (News-Specific)”
    section at news-primary.md:19.
  - Added the sentence that News mixes company statements, analyst commentary, reporter narration, and third-party quotes in
    the same item at news-primary.md:21.
  - Added the explicit skip list “analysts, consensus, the Street, price targets, rating actions, unnamed third parties” at
    news-primary.md:23.
  - Added the rule “when attribution is ambiguous, skip the item; err toward precision” at news-primary.md:25.
  - Deleted the entire old “What to Extract from News” table.
  - Deleted the entire old explicit analyst-estimates phrase table.
  - Deleted the old “Other Exclusions” bullet list covering sentiment, pure actuals, analyst ratings, and price targets.
  - Added a new “Title / Body / Teaser Handling” section at news-primary.md:27.
  - Added the rule “Always inspect the title” at news-primary.md:29.
  - Added the rule “Inspect the body when present” at news-primary.md:30.
  - Added the rule that teaser can be used when it has the clearest quoted guidance language at news-primary.md:31.
  - Added the anti-duplication rule for repeated headline/teaser/body restatements at news-primary.md:32.
  - Kept the prior-period-values table but promoted it to its own top-level section at news-primary.md:34.
  - Kept the reaffirmation verb table at news-primary.md:42.
  - Kept reaffirmation rule 1 unchanged at news-primary.md:53.
  - Kept reaffirmation rule 2 unchanged at news-primary.md:54.
  - Deleted the old reaffirmation rule 3 about deterministic IDs/provenance because that belongs to the type contract, not the
    News-specific file.
  - Left the quote prefix [News] unchanged at news-primary.md:56.
  - Changed the source_key row wording from “always, regardless of whether guidance was in title or body” to “canonical news
    source key, even when guidance was found in body or teaser” at news-primary.md:67.
  - Left given_date = n.created unchanged at news-primary.md:68.
  - Left source_refs = [] unchanged at news-primary.md:69.
  - Expanded the section row to include "teaser" in addition to "title" and "body" at news-primary.md:70.

  What I did not change

  - No edits to EventTraderNodes.py:674, news.py:282, or bz_news_schemas.py:6. I only used them to ground the rewrite in the
    actual data contract.
  - No agent/orchestrator code changes.
  - No trigger/worker changes.
  - No tests or schemas added.
  - No commits made.

  Verification I ran

  - Verified generic News files are clean: rg -w "guidance" returns no matches in news.md:1 and news-queries.md:1.
  - Live-validated the new 6A, 6C, 6D, and 6E queries against Neo4j.
  - Diff scope was exactly these 3 files.