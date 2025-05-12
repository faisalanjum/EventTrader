import logging
import time

from XBRL.xbrl_processor import process_report, get_company_by_cik, get_report_by_accessionNo
from ..Neo4jConnection import get_manager


logger = logging.getLogger(__name__)

class XbrlMixin:
    """
    Handles processing of XBRL data related to financial reports.
    Uses a thread pool for potentially long-running tasks.
    """

    def reconcile_xbrl_after_connect(self):
        """
        Call this method after Neo4j connection is established to ensure
        XBRL reconciliation happens correctly.
        """
        if hasattr(self, 'enable_xbrl') and self.enable_xbrl and self.manager and self.manager.driver and self.xbrl_executor:
            logger.info("Performing XBRL reconciliation post-connection...")
            self._reconcile_interrupted_xbrl_tasks()
        else:
            if not hasattr(self, 'enable_xbrl') or not self.enable_xbrl:
                logger.info("XBRL reconciliation skipped - feature disabled")
            elif not self.manager or not self.manager.driver:
                logger.warning("Cannot perform XBRL reconciliation - Neo4j connection not available")
            elif not self.xbrl_executor:
                logger.warning("Cannot perform XBRL reconciliation - XBRL executor not initialized")

    def _process_xbrl(self, session, report_id, cik, accessionNo):
        """
        Queue an XBRL report for background processing.
        
        Args:
            session: Neo4j session
            report_id: Report ID
            cik: Company CIK
            accessionNo: Report accession number
            
        Returns:
            bool: Success status for queueing (not processing)
        """
        # If XBRL processing is disabled, skip processing and update the report status
        if not self.enable_xbrl:
            logger.info(f"XBRL processing is disabled via feature flag - skipping report {report_id}")
            def update_skipped_status(tx):
                tx.run(
                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                    id=report_id, status="SKIPPED", error="XBRL processing disabled by feature flag"
                )
            session.execute_write(update_skipped_status)
            return True
            
        try:
            # Update status to QUEUED - using transaction function for automatic retry
            def update_queued_status(tx):
                tx.run(
                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                    id=report_id, status="QUEUED"
                )
            session.execute_write(update_queued_status)
            
            # Add a small delay before submitting to reduce contention
            time.sleep(0.1)  # 100ms delay to stagger job submissions
            
            # Submit task to thread pool and return immediately
            self.xbrl_executor.submit(
                self._xbrl_worker_task, 
                report_id, 
                cik, 
                accessionNo
            )
            
            logger.info(f"Queued report {report_id} for background XBRL processing")
            return True
            
        except Exception as e:
            error_msg = str(e)[:255]  # Limit error message length
            logger.error(f"Error queueing XBRL for report {report_id}: {error_msg}", exc_info=True)
            
            # Update status to FAILED - using transaction function for automatic retry
            def update_failed_status(tx):
                tx.run(
                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                    id=report_id, status="FAILED", error=str(e)
                )
            session.execute_write(update_failed_status)
            return False

            

    def _xbrl_worker_task(self, report_id, cik, accessionNo):
        """Process a single XBRL report in background"""
        # Add semaphore acquisition flag
        acquired = False
        
        try:
            # --- attempt to acquire the semaphore up to 3 times (5 s each) before giving up ---
            max_acquire_attempts = 3
            for attempt in range(max_acquire_attempts):
                acquired = self.xbrl_semaphore.acquire(timeout=5)
                if acquired:
                    break  # success
                if attempt < max_acquire_attempts - 1:
                    # Brief pause before next attempt; status is still QUEUED
                    time.sleep(1)

            if not acquired:
                # Could not acquire after retries – mark as PENDING so hourly reconciliation can pick it up
                with self.manager.driver.session() as session:
                    def update_pending_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                            id=report_id, status="PENDING", error="System resource limit reached"
                        )
                    session.execute_write(update_pending_status)
                logger.info(f"Resource limit reached for report {report_id} after {max_acquire_attempts} attempts; will retry later")
                return
                
            # Create a new session for this thread
            with self.manager.driver.session() as session:
                start_time = time.time()  # Start timing
                try:
                    # Mark as processing - using transaction function for automatic retry
                    def update_processing_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                            id=report_id, status="PROCESSING"
                        )
                    session.execute_write(update_processing_status)
                    
                    # Import needed components

                    
                    # Use the singleton Neo4j manager
                    neo4j_manager = get_manager()
                    
                    # Track the XBRL processor instance for proper cleanup
                    xbrl_processor = None
                    
                    try:
                        # Use the existing helper functions to get Report and Company nodes
                        report_node = get_report_by_accessionNo(neo4j_manager, accessionNo)
                        if not report_node:
                            logger.error(f"Report with accessionNo {accessionNo} not found in Neo4j")
                            def update_failed_status(tx):
                                tx.run(
                                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                                    id=report_id, status="FAILED", error="Report not found in Neo4j"
                                )
                            session.execute_write(update_failed_status)
                            return
                            
                        company_node = get_company_by_cik(neo4j_manager, report_node.cik)
                        if not company_node:
                            logger.error(f"Company with CIK {report_node.cik} not found in Neo4j")
                            def update_failed_status(tx):
                                tx.run(
                                    "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                                    id=report_id, status="FAILED", error="Company not found in Neo4j"
                                )
                            session.execute_write(update_failed_status)
                            return
                        
                        # Use the properly formatted values from the Neo4j nodes
                        processed_cik = company_node.cik
                        processed_accessionNo = report_node.accessionNo
                        
                        logger.info(f"Processing XBRL for report {report_id} (CIK: {processed_cik}, AccessionNo: {processed_accessionNo})")
                        
                        # --- simple retry loop (max 3 attempts) around heavy export ---
                        attempts_left = 3
                        while attempts_left:
                            try:
                                xbrl_processor = process_report(
                                    neo4j=neo4j_manager,
                                    cik=processed_cik,
                                    accessionNo=processed_accessionNo,
                                    testing=False
                                )
                                break  # success
                            except Exception as inner:
                                attempts_left -= 1
                                logger.error(
                                    "process_report failed for %s (attempts left %d): %s",
                                    report_id,
                                    attempts_left,
                                    inner,
                                )
                                if attempts_left == 0:
                                    raise  # bubble to outer except => status FAILED
                                time.sleep(2)  # brief back-off before retry
                        # --- end retry loop ---
                        
                        # Mark as completed - using transaction function for automatic retry
                        def update_completed_status(tx):
                            tx.run(
                                "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                                id=report_id, status="COMPLETED"
                            )
                        session.execute_write(update_completed_status)
                        
                        # Log completion time
                        elapsed = time.time() - start_time
                        mins, secs = divmod(int(elapsed), 60)
                        logger.info(f"Completed XBRL processing for report {report_id} in {mins}m {secs}s")
                        
                        # Add delay after each successful processing to allow for resource cleanup
                        time.sleep(3)  # 3 second delay to allow for resource cleanup
                        
                    finally:
                        # Explicitly clean up XBRL resources
                        if xbrl_processor:
                            try:
                                xbrl_processor.close_resources()
                                logger.info(f"Cleaned up XBRL resources for report {report_id}")
                            except Exception as e:
                                logger.warning(f"Failed to clean up XBRL resources for report {report_id}: {e}")
                        
                        # Don't close the singleton manager
                        pass
                        
                except Exception as e:
                    # Log error with timing
                    elapsed = time.time() - start_time
                    mins, secs = divmod(int(elapsed), 60)
                    logger.error(f"Error in XBRL processing for report {report_id} after {mins}m {secs}s: {e}", exc_info=True)
                    
                    # Update status to FAILED - using transaction function for automatic retry
                    def update_failed_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                            id=report_id, status="FAILED", error=str(e)
                        )
                    session.execute_write(update_failed_status)
        finally:
            # Release semaphore if acquired
            if acquired:
                self.xbrl_semaphore.release()


    def _reconcile_interrupted_xbrl_tasks(self):
        """
        Find reports stuck in QUEUED or PROCESSING state and re-queue them for XBRL processing.
        This should be called during initialization.
        """
        if not self.enable_xbrl:
            logger.info("XBRL reconciliation skipped as XBRL processing is disabled.")
            return
            
        logger.info("Checking for interrupted XBRL tasks (status QUEUED or PROCESSING)...")
        try:
            with self.manager.driver.session() as session:
                # Find reports that need reconciliation - not keeping 'SKIPPED' since it helps us keep some reports from Not processing (manually lets say)                
                records = session.run(
                    """
                    MATCH (r:Report)
                    WHERE r.xbrl_status IN ['QUEUED', 'PROCESSING', 'PENDING']
                    RETURN r.id AS report_id, r.cik AS cik, r.accessionNo AS accessionNo
                    """
                ).data()
                
                # Incase want to add only fetch repots which are longer than 1 hour old
                    #                   AND (
                    #     r.updated IS NULL OR
                    #     datetime(r.updated) < datetime() - duration({hours: 1})
                    #   )


                if not records:
                    logger.info("No interrupted XBRL tasks found.")
                    return
                    
                logger.info(f"Found {len(records)} reports needing XBRL reconciliation. Re-queueing...")
                requeued_count = 0
                failed_count = 0
                
                for record in records:
                    try:
                        # Re-queue using the existing _process_xbrl method
                        # It will update status to QUEUED and submit to the executor
                        # Need to pass the session object
                        success = self._process_xbrl(
                            session=session, # Pass the existing session
                            report_id=record['report_id'],
                            cik=record['cik'],
                            accessionNo=record['accessionNo']
                        )
                        if success:
                            requeued_count += 1
                        else:
                            failed_count += 1
                    except Exception as e_inner:
                        logger.error(f"Error re-queueing XBRL for report {record.get('report_id', 'N/A')}: {e_inner}", exc_info=True)
                        failed_count += 1
                        
                logger.info(f"XBRL Reconciliation Summary: Re-queued={requeued_count}, Failed-to-queue={failed_count}")
                
        except Exception as e:
            logger.error(f"Error during XBRL reconciliation query: {e}", exc_info=True)


    # def _xbrl_worker_task(self, report_id, cik, accessionNo):
    # ... rest of the file
