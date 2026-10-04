# SEC live download (exploratory, not decided)

**Goal:** every new filing that becomes a Neo4j `Report` also gets its complete original files within seconds,
linked by the same ID (accession number = `Report.id`).

**Idea (keeps the sec-api subscription):**
1. The old pipeline hears each filing from sec-api and keeps only our companies and forms
   (`redisDB/ReportProcessor.py`, `_process_item`). There, one added line puts the filing's accession, CIK and form
   on a new Redis list. Hooking earlier, when a filing first enters Redis, was rejected: nothing is filtered yet
   (thousands of other filings) and it saves almost no time.
2. One always-on worker pod on minisforum2 takes each item and runs the existing one-filing code
   (`driver/prepare/get/full_run.py`, `_filing`), saving into `/home/faisal/data/sec_filings`.
3. Safety net: every 10 minutes, compare Neo4j's Report IDs with what is saved; fetch anything missing.
4. Retries: at most 5 tries with growing waits (1 min, 10 min, 1 h, 6 h, 24 h); then the filing stays FAILED and is
   reported for a person to check. Filings SEC does not serve end there too.
5. Same rules as the historical run: one worker, at most 5 SEC requests/second, stop on HTTP 403, no historical run
   at the same time.

**Open questions:** use the old pipeline's `reports:confirmed_in_neo4j` Redis set for the safety net instead of
querying Neo4j? Safety-net interval?

**Before building:** tests with fakes (a new filing; one needing SEC proof; the same filing twice → saved once; SEC
errors then success; restart mid-filing; worker down → safety net catches up; HTTP 403 stops it; retry cap reached);
owner OK; Codex review; the old pipeline running with its subscriptions.
