Full XBRL execution path in the current codebase
===================================================
1.	Flags & infrastructure
•	config.feature_flags.ENABLE_XBRL_PROCESSING – master on/off switch (default True).• XBRL_WORKER_THREADS – size of the thread-pool.
•	InitializationMixin.__init__
o	creates self.xbrl_semaphore=threading.BoundedSemaphore(4) (hard cap on simultaneous heavy jobs).
o	builds self.xbrl_executor = ThreadPoolExecutor(max_workers=XBRL_WORKER_THREADS, …) only if the flag above is on.

2.	Normal ingestion path
•	ReportProcessor finishes the heavy SEC -> Redis step.
•	Neo4jProcessor (ReportMixin) pulls the JSON and inside _execute_report_database_operations runs:

      if  self.enable_xbrl
          and not self.xbrl_processed              # session-level guard
          and report_props['is_xml'] is True
          and report_props['cik']                  # must know company
          and report_props['xbrl_status'] not in ('COMPLETED','PROCESSING','SKIPPED'):
              self._process_xbrl(session, report_id, cik, accessionNo)

3.	Startup reconciliation path - DataManagerCentral builds one Neo4jProcessor and immediately calls
 neo4j_processor.reconcile_xbrl_after_connect()

The mixin method does:
   _reconcile_interrupted_xbrl_tasks()
       → MATCH reports WHERE xbrl_status IN ['QUEUED','PROCESSING']
       → for each: self._process_xbrl(...)
(PENDING is not included – see note at the end.)

4.	Queueing – XbrlMixin._process_xbrl
Marks the report xbrl_status="QUEUED" in Neo4j.• self.xbrl_executor.submit(self._xbrl_worker_task, report_id, cik, accessionNo) – this is the single entry-point that ever starts _xbrl_worker_task.

5.	Worker thread – _xbrl_worker_task
1.	Tries self.xbrl_semaphore.acquire(timeout=5).
• Failure → sets xbrl_status="PENDING" and returns.
2.	Success → sets xbrl_status="PROCESSING".
3.	Looks up Report and Company nodes.
1.	Runs the heavy XBRL.xbrl_processor.process_report(...) wrapped in a 3-attempt retry loop.
5.	On success → xbrl_status="COMPLETED".
•	On final failure → xbrl_status="FAILED".
6.	Releases the semaphore.

Status timeline therefore is: 
   QUEUED  →  (semaphore ok?)  → PROCESSING → COMPLETED
                         ↘ (no slot) ↘
                           PENDING   (no automatic re-try unless requeued)            
      
       6. Thread-pool & shutdown
•	The pool lives on the Neo4jProcessor instance; InitializationMixin.close() shuts it down when the processor stops.
•	Each worker holds the semaphore only for the duration of process_report.

Why PENDING is not in the reconciliation query?
PENDING happens only when the executor could not grab the semaphore (i.e. all worker threads are already busy).The intent seems to be that a subsequent call to _process_xbrl from the ingestion path will notice xbrl_status='PENDING' (which is not excluded by the condition above) and immediately re-queue the report once resources free up. In practice:• Fresh ingestion will eventually revisit the report and queue it again.• After a restart the record would stay PENDING, because the reconciliation routine currently looks only at QUEUED and PROCESSING. If you want automatic recovery after restarts, simply add 'PENDING' to that MATCH list. Cross-checks in other mixins 

•	mixins.reconcile.py and mixins.pubsub.py never start XBRL; they only manipulate Neo4j nodes or listen to pub/sub.
•	self.xbrl_processed is a per-processor flag used only to throttle within one batch; it isn’t flipped anywhere else, so the first report that triggers XBRL in a given call of _execute_report_database_operations sets the flag and prevents a second submission during that same call (the next Neo4jProcessor run resets it via a new instance).

Bottom line
•	There are exactly two call-sites, both funnelling through _process_xbrl → ThreadPoolExecutor.submit, and every actual heavy lifting thread starts in _xbrl_worker_task.
•	If you need PENDING reports to self-heal after a crash, extend the reconciliation query to include that status; otherwise the flow is already self-contained and isolated from the rest of the system.
