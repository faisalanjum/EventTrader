# SEC live download (exploratory, not decided)

**Goal:** each new filing that becomes a Neo4j `Report` also gets its complete original files, linked by the same ID
(accession = `Report.id`), as fast as possible (target: seconds, to be measured).

**Idea (keeps the sec-api subscription):**
1. **Queue:** after the old pipeline's company/form filter (`redisDB/ReportProcessor.py`, `_process_item`), one added
   line queues accession, original CIK (the pipeline may change it) and form in Redis. An earlier hook was rejected:
   unfiltered and no faster.
2. **Worker:** one always-on pod on minisforum2 runs `driver/prepare/get/full_run.py`'s full per-filing handling
   (records; 403, storage and disk stops; memory limit) into `/home/faisal/data/sec_filings`. An item leaves the
   queue only after its result is saved.
3. **Safety net:** every 10 min, Neo4j Report IDs vs recorded results (not the Redis confirmation set); fetch what is
   missing, within the retry cap.
4. **Retries:** first try + up to 5 (1 min, 10 min, 1 h, 6 h, 24 h), never delaying new filings; each re-downloads
   from SEC; then FAILED, for a person.
5. **Rules:** one worker; ≤5 SEC requests/s including the old pipeline's own SEC downloads; stop on 403; no
   historical run at the same time.

**Open:** safety-net interval; the old pipeline's SEC traffic.

**Before building:** fake-based tests (new filing, one needing SEC proof, duplicate, burst, big filing, SEC not ready,
SEC errors, bad saved copy, restart, worker down, 403, retry cap); owner OK; Codex review; old pipeline running.
