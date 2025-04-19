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
            logger.error(f"Error queueing XBRL for report {report_id}: {error_msg}")
            
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
            # Try to acquire semaphore before processing
            acquired = self.xbrl_semaphore.acquire(timeout=5)
            if not acquired:
                # Cannot acquire - update status and exit
                with self.manager.driver.session() as session:
                    # Use transaction function for automatic retry on deadlocks
                    def update_pending_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                            id=report_id, status="PENDING", error="System resource limit reached"
                        )
                    session.execute_write(update_pending_status)
                logger.info(f"Resource limit reached for report {report_id}, will retry later")
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
                        
                        # Process the report and store the processor instance
                        xbrl_processor = process_report(
                            neo4j=neo4j_manager,
                            cik=processed_cik,
                            accessionNo=processed_accessionNo,
                            testing=False
                        )
                        
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
                    logger.error(f"Error in XBRL processing for report {report_id} after {mins}m {secs}s: {e}")
                    
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



    # def _xbrl_worker_task(self, report_id, cik, accessionNo):
    #     """Process a single XBRL report in background"""
    #     # Create a new session for this thread
    #     with self.manager.driver.session() as session:
    #         start_time = time.time()  # Start timing
    #         try:
    #             # Mark as processing
    #             session.run(
    #                 "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
    #                 id=report_id, status="PROCESSING"
    #             )
                
    #             # Import needed components
    #             from XBRL.xbrl_processor import process_report, get_company_by_cik, get_report_by_accessionNo
    #             from neograph.Neo4jManager import Neo4jManager
                
    #             # Create a dedicated Neo4j connection for this task
    #             neo4j_manager = Neo4jManager(
    #                 uri=self.uri,
    #                 username=self.username,
    #                 password=self.password
    #             )
                
    #             # Track the XBRL processor instance for proper cleanup
    #             xbrl_processor = None
                
    #             try:
    #                 # Use the existing helper functions to get Report and Company nodes
    #                 report_node = get_report_by_accessionNo(neo4j_manager, accessionNo)
    #                 if not report_node:
    #                     logger.error(f"Report with accessionNo {accessionNo} not found in Neo4j")
    #                     session.run(
    #                         "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
    #                         id=report_id, status="FAILED", error="Report not found in Neo4j"
    #                     )
    #                     return
                        
    #                 company_node = get_company_by_cik(neo4j_manager, report_node.cik)
    #                 if not company_node:
    #                     logger.error(f"Company with CIK {report_node.cik} not found in Neo4j")
    #                     session.run(
    #                         "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
    #                         id=report_id, status="FAILED", error="Company not found in Neo4j"
    #                     )
    #                     return
                    
    #                 # Use the properly formatted values from the Neo4j nodes
    #                 processed_cik = company_node.cik
    #                 processed_accessionNo = report_node.accessionNo
                    
    #                 logger.info(f"Processing XBRL for report {report_id} (CIK: {processed_cik}, AccessionNo: {processed_accessionNo})")
                    
    #                 # Process the report and store the processor instance
    #                 xbrl_processor = process_report(
    #                     neo4j=neo4j_manager,
    #                     cik=processed_cik,
    #                     accessionNo=processed_accessionNo,
    #                     testing=False
    #                 )
                    
    #                 # Mark as completed
    #                 session.run(
    #                     "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
    #                     id=report_id, status="COMPLETED"
    #                 )
    #                 # Log completion time
    #                 elapsed = time.time() - start_time
    #                 mins, secs = divmod(int(elapsed), 60)
    #                 logger.info(f"Completed XBRL processing for report {report_id} in {mins}m {secs}s")
                    
    #                 # Add delay after each successful processing to allow for resource cleanup
    #                 time.sleep(3)  # 3 second delay to allow for resource cleanup
                    
    #             finally:
    #                 # Explicitly clean up XBRL resources
    #                 if xbrl_processor:
    #                     try:
    #                         xbrl_processor.close_resources()
    #                         logger.info(f"Cleaned up XBRL resources for report {report_id}")
    #                     except Exception as e:
    #                         logger.warning(f"Failed to clean up XBRL resources for report {report_id}: {e}")
                    
    #                 # Always close the manager
    #                 neo4j_manager.close()
                    
    #         except Exception as e:
    #             # Log error with timing
    #             elapsed = time.time() - start_time
    #             mins, secs = divmod(int(elapsed), 60)
    #             logger.error(f"Error in XBRL processing for report {report_id} after {mins}m {secs}s: {e}")
    #             session.run(
    #                 "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
    #                 id=report_id, status="FAILED", error=str(e)
    #             )
