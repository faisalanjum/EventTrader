# SEC live download (exploratory, not decided)

**Goal:** every new filing that becomes a Neo4j `Report` also gets its complete original files as fast as possible,
linked by the same ID (accession number = `Report.id`). Seconds is the target, to be measured with bursts, big
filings and SEC delays.

**Idea (keeps the sec-api subscription):**
1. The old pipeline hears each filing from sec-api and keeps only our companies and forms
   (`redisDB/ReportProcessor.py`, `_process_item`). There, one added line puts the filing's accession, original CIK
   (the pipeline can replace or clear it) and form on a new Redis list. Hooking earlier, when a filing first enters
   Redis, was rejected: nothing is filtered yet (thousands of other filings) and it saves almost no time.
2. One always-on worker pod on minisforum2 takes each item and runs the downloader's full per-filing handling from
   `driver/prepare/get/full_run.py` (result records; stops on HTTP 403, storage errors and low disk; memory limit),
   not `_filing` alone, saving into `/home/faisal/data/sec_filings`. An item leaves the list only after its result
   is saved, so a crash loses nothing.
3. Safety net: every 10 minutes, compare Neo4j's Report IDs (not the Redis confirmation set, which can miss updates)
   with the recorded download results; fetch anything missing, within the retry cap.
4. Retries: first try, then up to 5 retries after 1 min, 10 min, 1 h, 6 h and 24 h, never delaying new filings. Each
   retry downloads again from SEC instead of re-reading a bad saved copy. Then the filing stays FAILED and is reported
   for a person to check; filings SEC does not serve end there too.
5. Same rules as the historical run: one worker, at most 5 SEC requests/second counting the old pipeline's own SEC
   downloads (they run outside our limiter), stop on HTTP 403, no historical run at the same time.

**Open questions:** how often should the safety net run? How much SEC traffic does the old pipeline make?

**Before building:** tests with fakes (a new filing; one needing SEC proof; the same filing twice → saved once; a
burst of filings; a big filing; SEC not ready yet; SEC errors then success; a bad saved copy; restart mid-filing;
worker down → safety net catches up; HTTP 403 stops it; retry cap reached); owner OK; Codex review; the old pipeline
running with its subscriptions.
