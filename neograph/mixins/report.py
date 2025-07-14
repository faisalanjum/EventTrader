# neograph/mixins/report.py

# --- Add necessary imports used by the methods below ---
import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple

from redisDB.redis_constants import RedisKeys
from utils.date_utils import parse_news_dates, parse_date  
from XBRL.xbrl_core import NodeType, RelationType

from ..EventTraderNodes import (
    ReportNode,
    ExtractedSectionContent,
    ExhibitContent,
    FilingTextContent,
    FinancialStatementContent,
    CompanyNode
)
logger = logging.getLogger(__name__)

class ReportMixin:
    """
    Handles processing and storage of report data (e.g., 8-K, 10-K) into Neo4j.
    Includes section, exhibit, financial statement, and XBRL handling.
    """

    def _finalize_report_batch(self, delete_client, redis_key, report_id, success, namespace, failure_reason=None):
        """
        Atomic finalization of report processing:
        1. For success=True + withreturns: verify meta before deleting key
        2. For success=False: mark as failed
        """
        meta_key = f"tracking:meta:{RedisKeys.SOURCE_REPORTS}:{report_id}"
        pipe = None # Initialize pipe to None
        try:
            if success:
                # Use an explicit pipeline for atomicity and efficiency
                pipe = delete_client.client.pipeline()

                # Step 1: Always make sure inserted_into_neo4j_at is marked
                # mark_lifecycle_timestamp will use the external_pipe if provided
                delete_client.mark_lifecycle_timestamp(
                    meta_key, 
                    "inserted_into_neo4j_at", 
                    external_pipe=pipe
                )
                
                # Step 2: Only delete withreturns keys (conditionally added to the same pipe)
                if namespace == RedisKeys.SUFFIX_WITHRETURNS:
                    # The hexists check previously here is removed. 
                    # inserted_into_neo4j_at is being set in this same pipeline, 
                    # and the guard in process_reports_to_neo4j should prevent this path 
                    # if the field was already set from a prior run. Atomicity of the pipeline ensures this is safe.
                    pipe.delete(redis_key)
                    logger.info(f"(Pipeline) Queued deletion for processed withreturns key: {redis_key}")
                
                pipe.execute()
                logger.info(f"Successfully finalized report {report_id} (success path).")

            else:
                # For failures, mark failed_at with reason, but only if not already successfully inserted
                if not delete_client.client.hexists(meta_key, "inserted_into_neo4j_at"):
                    # This will create its own pipeline internally if external_pipe is not passed
                    delete_client.mark_lifecycle_timestamp(meta_key, "failed_at", reason=failure_reason or "neo4j_insertion_failed")
                    logger.info(f"Marked report {report_id} as failed with reason: {failure_reason or 'neo4j_insertion_failed'}")
                else:
                    logger.warning(f"Report {report_id} (key {redis_key}) processing resulted in failure, but 'inserted_into_neo4j_at' already exists in meta. Not setting 'failed_at' to avoid contradiction.")
                
        except Exception as e:
            logger.error(f"Error in report finalization for {report_id}: {e}", exc_info=True)
            # If pipeline was started but execute failed, ensure it's discarded to prevent issues
            if pipe: # Check if pipe was initialized
                try:
                    pipe.reset()
                except Exception as e_pipe_reset:
                    logger.error(f"Error resetting pipeline during exception handling for {report_id}: {e_pipe_reset}")

    def process_reports_to_neo4j(self, batch_size=100, max_items=None, include_without_returns=True) -> bool:
        """
        Process SEC reports from Redis to Neo4j
        Similar to process_news_to_neo4j but for SEC reports
        
        Args:
            batch_size: Number of records to process at once
            max_items: Maximum number of items to process (None for all)
            include_without_returns: Whether to include reports without returns
            
        Returns:
            bool: True if processing is complete, False if it was interrupted
        """

        
        # Get Redis instance if available
        if not self.event_trader_redis:
            logger.error("No Redis instance available, cannot process reports")
            return False
            
        # Process reports with returns
        withreturns_keys = []
        try:
            # Get report keys with returns using safer pattern construction
            withreturns_pattern = RedisKeys.get_returns_keys(RedisKeys.SOURCE_REPORTS)['withreturns'] + ":*"
            withreturns_keys = list(self.event_trader_redis.history_client.client.scan_iter(match=withreturns_pattern))
            
            if max_items is not None:
                withreturns_keys = withreturns_keys[:max_items]
                
            logger.info(f"Found {len(withreturns_keys)} reports with returns")
        except Exception as e:
            logger.error(f"Error getting withreturns keys: {e}")
            
        # Process reports without returns if requested
        withoutreturns_keys = []
        if include_without_returns:
            try:
                # Get report keys without returns using safer pattern construction
                withoutreturns_pattern = RedisKeys.get_returns_keys(RedisKeys.SOURCE_REPORTS)['withoutreturns'] + ":*"
                withoutreturns_keys = list(self.event_trader_redis.history_client.client.scan_iter(match=withoutreturns_pattern))
                
                if max_items is not None:
                    withoutreturns_keys = withoutreturns_keys[:max_items]
                    
                logger.info(f"Found {len(withoutreturns_keys)} reports without returns")
            except Exception as e:
                logger.error(f"Error getting withoutreturns keys: {e}")
                
        # Combine both key sets
        all_keys = withreturns_keys + withoutreturns_keys
        if not all_keys:
            logger.info("No report keys found to process")
            return True
            
        total_reports = len(all_keys)
        logger.info(f"Processing {total_reports} total reports")
        
        # Process in batches
        processed_count = 0
        error_count = 0
        skipped_duplicate_count = 0 # Initialize new counter
        
        for batch_start in range(0, len(all_keys), batch_size):
            batch_keys = all_keys[batch_start:batch_start + batch_size]
            batch_size_actual = len(batch_keys)
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}, items {batch_start+1}-{batch_start+batch_size_actual} of {total_reports}")
            
            # Process each report in the batch
            for key in batch_keys:
                try:
                    # Extract key parts and namespace
                    parts = key.split(':')
                    report_id = parts[-1] if len(parts) > 0 else key
                    namespace = parts[1] if len(parts) > 1 else ""  # 'withreturns' or 'withoutreturns'
                    
                    # Try history_client first, fallback to live_client if needed
                    # Default to history_client for delete_client, and for initial get
                    # This client will also be used for meta checks and key deletion in the guard.
                    delete_client = self.event_trader_redis.history_client
                    
                    # --- BEGIN GUARD ---
                    meta_key_for_guard = f"tracking:meta:{RedisKeys.SOURCE_REPORTS}:{report_id}"
                    if delete_client.client.hexists(meta_key_for_guard, "inserted_into_neo4j_at"):
                        logger.info(f"[SKIP] Report {report_id} (from key {key}) already has 'inserted_into_neo4j_at'. Skipping main processing.")
                        if namespace == RedisKeys.SUFFIX_WITHRETURNS:
                            try:
                                delete_client.client.delete(key)
                                logger.info(f"[SKIP] Removed duplicate/stale key {key} for already processed report {report_id}")
                            except Exception as e_del:
                                logger.warning(f"[SKIP] Could not delete duplicate/stale key {key}: {e_del}")
                        skipped_duplicate_count += 1 # Use dedicated counter
                        continue # Skip to the next key in the batch
                    # --- END GUARD ---
                    
                    raw_data = delete_client.get(key)
                    
                    if not raw_data:
                        raw_data = self.event_trader_redis.live_client.get(key)
                        if raw_data:
                            delete_client = self.event_trader_redis.live_client
                            logger.warning(f"[FALLBACK] Found {key} in live_client instead of history_client")
                    
                    # If no data found, mark failure and continue
                    if not raw_data:
                        self._finalize_report_batch(
                            delete_client=delete_client,
                            redis_key=key,
                            report_id=report_id,
                            success=False,
                            namespace=namespace,
                            failure_reason="raw_missing"
                        )
                        logger.warning(f"No data found for key {key}")
                        error_count += 1
                        continue
                        
                    # Parse JSON data and process
                    report_data = json.loads(raw_data)
                    success = self._process_deduplicated_report(report_id, report_data)
                    
                    # Finalize processing with proper cleanup
                    self._finalize_report_batch(
                        delete_client=delete_client,
                        redis_key=key,
                        report_id=report_id,
                        success=success,
                        namespace=namespace,
                        failure_reason="neo4j_insertion_failed"
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing report key {key}: {e}", exc_info=True)
                    error_count += 1
                
            logger.info(f"Processed batch {batch_start//batch_size + 1}/{(len(all_keys) + batch_size - 1)//batch_size}")
            
        # Summary and status
        logger.info(f"Finished processing reports to Neo4j. Processed: {processed_count}, Errors: {error_count}, Skipped Duplicates: {skipped_duplicate_count}")
        
        return processed_count > 0 or error_count == 0



    def _prepare_report_data(self, report_id, report_data):
        """
        Prepare report data for processing, extracting all necessary information.
        
        Args:
            report_id: Unique identifier for the report (accessionNo)
            report_data: Dictionary containing report data
            
        Returns:
            tuple: (report_node, node_properties, valid_symbols, company_params, sector_params, 
                   industry_params, market_params, report_timestamps)
                where report_timestamps is a tuple of (filed_at, updated_at, filed_str, updated_str)
        """
        # Get universe data for ticker-to-CIK mappings
        universe_data = self._get_universe()
        ticker_to_cik = {}
        for symbol, data in universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
        
        # 1. Create ReportNode from report data
        report_node = self._create_report_node_from_data(report_id, report_data)
        
        # 2. Extract and process symbols using the unified method
        symbols = self._extract_symbols_from_data(report_data)
        symbols_json = json.dumps(symbols)
        
        # Get timestamps for parameters and conditional updates
        filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
        updated_at = parse_date(report_data.get('updated')) if report_data.get('updated') else None
        
        filed_str = filed_at.isoformat() if filed_at else ""
        updated_str = updated_at.isoformat() if updated_at else filed_str
        
        # 3. Use the common method to prepare relationship parameters
        valid_symbols, company_params, sector_params, industry_params, market_params = self._prepare_entity_relationship_params(
            data_item=report_data,
            symbols=symbols,
            universe_data=universe_data,
            ticker_to_cik=ticker_to_cik,
            timestamp=filed_str
        )
        
        # 4. Get node properties from ReportNode
        node_properties = report_node.properties
        
        # Return all prepared data
        report_timestamps = (filed_at, updated_at, filed_str, updated_str)
        return (report_node, node_properties, valid_symbols, company_params, 
                sector_params, industry_params, market_params, report_timestamps)



    def _process_deduplicated_report(self, report_id, report_data):
        """
        Process report data with deduplication, standardized fields, and efficient symbol relationships.
        Uses a hash-based MERGE pattern with conditional updates based on timestamps.
        
        Args:
            report_id: Unique identifier for the report (accessionNo)
            report_data: Dictionary containing report data
            
        Returns:
            bool: Success status
        """
        logger.critical(f"Processing deduplicated report {report_id}")
        
        try:
            # Prepare all report data
            accession_no = report_id[:20]
            report_node, node_properties, valid_symbols, company_params, sector_params, industry_params, market_params, report_timestamps = self._prepare_report_data(accession_no, report_data)
            
            # Execute all database operations
            success = self._execute_report_database_operations(
                accession_no, report_node, node_properties, valid_symbols,
                company_params, sector_params, industry_params, market_params,
                report_timestamps
            )

            if success:
                # with a single physical Redis, "history" - That's the one every reader expects, so we must use it when we write meta hashes. Using live_client would prefix the key with live: and no guard would ever see it. Hence we keep history_client unconditionally.
                meta_key = f"tracking:meta:{RedisKeys.SOURCE_REPORTS}:{report_id}"
                self.event_trader_redis.history_client.mark_lifecycle_timestamp(
                    meta_key, "inserted_into_neo4j_at"
                )

            return success
        except Exception as e:
            logger.error(f"Error processing report {report_id}: {e}", exc_info=True)
            return False




    def _execute_report_database_operations(self, report_id, report_node, node_properties, valid_symbols, 
                                           company_params, sector_params, industry_params, market_params, 
                                           report_timestamps):
        """
        Execute all database operations for a report.
        
        Args:
            report_id: Unique identifier for the report
            report_node: ReportNode object
            node_properties: Dictionary of node properties
            valid_symbols: List of valid symbols
            company_params: Parameters for company relationships
            sector_params: Parameters for sector relationships
            industry_params: Parameters for industry relationships
            market_params: Parameters for market index relationships
            report_timestamps: Tuple of (filed_at, updated_at, filed_str, updated_str)
            
        Returns:
            bool: Success status
        """
        filed_at, updated_at, filed_str, updated_str = report_timestamps
        
        # Build Cypher query for fields
        on_create_parts = []
        
        # Add all properties from node_properties
        for key, value in node_properties.items():
            on_create_parts.append(f"r.{key} = ${key}")
        
        # Build ON MATCH SET parts with conditional updates for content fields
        on_match_parts = [
            "r.description = CASE WHEN $updated > r.updated THEN $description ELSE r.description END",
            "r.formType = CASE WHEN $updated > r.updated THEN $formType ELSE r.formType END",
            "r.periodOfReport = CASE WHEN $updated > r.updated THEN $periodOfReport ELSE r.periodOfReport END",
            "r.effectivenessDate = CASE WHEN $updated > r.updated THEN $effectivenessDate ELSE r.effectivenessDate END",
            "r.updated = CASE WHEN $updated > r.updated THEN $updated ELSE r.updated END",
            "r.primaryDocumentUrl = $primaryDocumentUrl",
            "r.linkToHtml = $linkToHtml",
            "r.linkToTxt = $linkToTxt",
            "r.linkToFilingDetails = $linkToFilingDetails",
            "r.exhibits = $exhibits",
            "r.entities = $entities",
            "r.items = $items",
            "r.symbols = $symbols",
            "r.is_xml = $is_xml",
            "r.isAmendment = $isAmendment",
            "r.accessionNo = $id",
            "r.id = $id",
            "r.market_session = $market_session",
            "r.returns_schedule = $returns_schedule",
            "r.extracted_sections = CASE WHEN $updated > r.updated THEN $extracted_sections ELSE r.extracted_sections END",
            "r.financial_statements = CASE WHEN $updated > r.updated THEN $financial_statements ELSE r.financial_statements END",
            "r.exhibit_contents = CASE WHEN $updated > r.updated THEN $exhibit_contents ELSE r.exhibit_contents END",
            "r.filing_text_content = CASE WHEN $updated > r.updated THEN $filing_text_content ELSE r.filing_text_content END",
            "r.xbrl_status = CASE WHEN $updated > r.updated AND $xbrl_status IS NOT NULL THEN $xbrl_status ELSE r.xbrl_status END",
            "r.created = $created"
        ]

            # "r.xbrl_status = CASE WHEN $updated > r.updated THEN $xbrl_status ELSE r.xbrl_status END",

        # Create parameter dictionary from node_properties
        query_params = {
            "updated": updated_str,  # For conditional updates
        }
        
        # Add all node properties to query params
        for key, value in node_properties.items():
            query_params[key] = value
        
        # Ensure all referenced parameters exist (even if they weren't in node_properties)
        required_params = ["periodOfReport", "effectivenessDate", "financial_statements", "exhibit_contents", 
                         "extracted_sections", "market_session", "returns_schedule", "filing_text_content", "items"]
        
        for param in required_params:
            if param not in query_params:
                if param in ["financial_statements", "exhibit_contents", "extracted_sections", "returns_schedule"]:
                    # These need to be JSON strings
                    query_params[param] = json.dumps({})
                elif param == "filing_text_content":
                    # This is a text field that can be null
                    query_params[param] = None
                elif param == "items":
                    # Default items to empty array as JSON string
                    query_params[param] = json.dumps([])
                else:
                    # Default to empty string for other fields
                    query_params[param] = ""
        
        # Construct the complete Cypher query
        # Use id for MERGE since it has unique constraint, ensuring proper deduplication
        report_merge_query = f"""
        MERGE (r:Report {{id: $id}})
        ON CREATE SET {', '.join(on_create_parts)}
        ON MATCH SET {', '.join(on_match_parts)}
        RETURN r
        """
        
        with self.manager.driver.session() as session:
            # Execute the query using Neo4jManager
            record = self.manager.execute_cypher_query(report_merge_query, query_params)
            
            # Process the result
            if not record:
                logger.error(f"Failed to create or update report node {report_id}")
                return False
            
            # Get the created/updated report
            report_props = dict(record["r"].items())
            
            # Process extracted sections if present
            if report_node.extracted_sections:
                section_data = {
                    'extracted_sections': report_node.extracted_sections,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_section_nodes_from_report(report_id, section_data)
            
            # Process exhibit contents if present
            if report_node.exhibit_contents:
                exhibit_data = {
                    'exhibit_contents': report_node.exhibit_contents,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_exhibit_nodes_from_report(report_id, exhibit_data)
            
            # Process financial statements if present
            if report_node.financial_statements:
                financial_data = {
                    'financial_statements': report_node.financial_statements,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_financial_statement_nodes_from_report(report_id, financial_data)
            
            # Process filing text content if present
            if report_node.filing_text_content:
                filing_text_data = {
                    'filing_text_content': report_node.filing_text_content,
                    'formType': report_node.formType,
                    'cik': report_node.cik,
                    'created': report_node.created
                }
                self._create_filing_text_content_nodes_from_report(report_id, filing_text_data)
            
            # Check if this report is eligible for XBRL processing and we haven't processed one yet
            # Import flags to check processing method and exclusion list
            from config.feature_flags import ENABLE_KUBERNETES_XBRL, PRESERVE_XBRL_FAILED_STATUS
            
            # Build exclusion list based on feature flag
            excluded_statuses = ['COMPLETED', 'PROCESSING', 'SKIPPED', 'REFERENCE_ONLY']
            if PRESERVE_XBRL_FAILED_STATUS:
                excluded_statuses.append('FAILED')
            
            if (self.enable_xbrl and  # Only if XBRL processing is enabled via feature flags
                not self.xbrl_processed and
                report_props.get('is_xml') == True and 
                report_props.get('cik') and
                report_props.get('xbrl_status') not in excluded_statuses):
                
                # if ENABLE_KUBERNETES_XBRL:
                #     # Use Kubernetes worker pods (queue-based approach)
                #     if self.event_trader_redis:
                #         xbrl_queue = RedisKeys.XBRL_QUEUE
                #         self.event_trader_redis.history_client.push_to_queue(xbrl_queue, json.dumps({
                #             "report_id": report_props["id"],
                #             "accession": report_props["accessionNo"],
                #             "cik": report_props["cik"],
                #             "form_type": report_props["formType"]
                #         }))
                #         logger.info(f"[Kube]: Queued XBRL processing for {report_props['id']} via Kubernetes workers")
                #     else:
                #         logger.warning(f"[Kube]: Cannot queue XBRL processing for {report_props['id']}: Redis client not available")
                # else:
                #     # Use local thread pool with semaphore (original approach)
                #     self._process_xbrl(
                #         session=session,
                #         report_id=report_props["id"],
                #         cik=report_props["cik"],
                #         accessionNo=report_props["accessionNo"]
                #     )

                if ENABLE_KUBERNETES_XBRL:
                    # Use Kubernetes worker pods (queue-based approach)
                    # Now using _enqueue_xbrl for consistent status management
                    self._enqueue_xbrl(
                        session=session,
                        report_id=report_props["id"],
                        cik=report_props["cik"],
                        accessionNo=report_props["accessionNo"],
                        form_type=report_props.get("formType", "")
                    )
                else:
                    # Use local thread pool with semaphore (original approach)
                    self._enqueue_xbrl(
                        session=session,
                        report_id=report_props["id"],
                        cik=report_props["cik"],
                        accessionNo=report_props["accessionNo"],
                        form_type=form_type if 'form_type' in locals() else report_props.get("formType", "")
                    )




            # Skip processing if no symbols found
            if not valid_symbols:
                logger.warning(f"No valid symbols found for report {report_id}")
                return True
                
            # ----- Use helper method for efficient batch processing of relationships -----
            
            # Split company parameters into primary filer and referenced companies
            primary_filer_params = []
            referenced_in_params = []
            report_cik = report_props.get("cik")
            
            for param in company_params:
                if report_cik and param['cik'] == report_cik:
                    primary_filer_params.append(param)
                else:
                    referenced_in_params.append(param)
            
            # Deduplicate both lists by CIK to prevent any possibility of duplicate relationships
            primary_filer_params = list({param['cik']: param for param in primary_filer_params}.values())
            referenced_in_params = list({param['cik']: param for param in referenced_in_params}.values())
            
            # Create PRIMARY_FILER relationships directly using Neo4jManager
            if primary_filer_params:
                self.manager.create_relationships(
                    source_label="Report", 
                    source_id_field="id", 
                    source_id_value=report_id,
                    target_label="Company", 
                    target_match_clause="{cik: param.cik}", 
                    rel_type=RelationType.PRIMARY_FILER.value, 
                    params=primary_filer_params
                )
                logger.info(f"Created {len(primary_filer_params)} PRIMARY_FILER relationships to companies")
            
            # Create REFERENCED_IN relationships directly using Neo4jManager
            if referenced_in_params:
                self.manager.create_relationships(
                    source_label="Report", 
                    source_id_field="id", 
                    source_id_value=report_id,
                    target_label="Company", 
                    target_match_clause="{cik: param.cik}", 
                    rel_type=RelationType.REFERENCED_IN.value, 
                    params=referenced_in_params
                )
                logger.info(f"Created {len(referenced_in_params)} REFERENCED_IN relationships to companies")
            
            # Create other INFLUENCES relationships as before
            self._create_influences_relationships(session, report_id, "Report", "Sector", sector_params)
            self._create_influences_relationships(session, report_id, "Report", "Industry", industry_params)
            self._create_influences_relationships(session, report_id, "Report", "MarketIndex", market_params)
            
            # 5. Create Report Category relationships
            # Extract form type from report_node instead of report_data
            form_type = report_node.formType.split('/')[0] if report_node.formType else ""  # Extract base form type without amendments
            if form_type:
                # Here we are linking to ADMIN Nodes
                self.manager.create_report_category_relationship(report_id, form_type)
            
            return True



    def _create_report_node_from_data(self, report_id, report_data):
        """Create a ReportNode instance from report data"""
        
        # Process required fields
        cik = report_data.get('cik', '')
        if cik:
            cik = str(cik).zfill(10)
            
        primary_document_url = report_data.get('primaryDocumentUrl', '')
        
        # Create report node with required fields
        report_node = ReportNode(
            accessionNo=report_id,
            primaryDocumentUrl=primary_document_url,
            cik=cik
        )
        
        # Extract timestamps with proper parsing
        filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
        updated_at = parse_date(report_data.get('updated')) if report_data.get('updated') else None
        
        # Process basic fields
        form_type = report_data.get('formType', '')
        
        # Derive isAmendment from formType if not explicitly set
        is_amendment = report_data.get('isAmendment', False)
        if not is_amendment and form_type and '/A' in form_type:
            is_amendment = True
            
        # Set basic fields
        report_node.formType = form_type
        report_node.created = report_data.get('created', '')
        report_node.is_xml = bool(report_data.get('is_xml', False))
        report_node.isAmendment = is_amendment
        report_node.description = report_data.get('description', '')
        report_node.periodOfReport = report_data.get('periodOfReport', '')
        report_node.effectivenessDate = report_data.get('effectivenessDate', '')
        report_node.linkToHtml = report_data.get('linkToHtml', '')
        report_node.linkToTxt = report_data.get('linkToTxt', '')
        report_node.linkToFilingDetails = report_data.get('linkToFilingDetails', '')
        
        # Set complex fields - these will be serialized by ReportNode properties method
        report_node.exhibits = report_data.get('exhibits', {})
        report_node.entities = report_data.get('entities', [])
        report_node.items = report_data.get('items', [])
        report_node.symbols = report_data.get('symbols', [])
        report_node.extracted_sections = report_data.get('extracted_sections', {})
        report_node.financial_statements = report_data.get('financial_statements', {})
        report_node.exhibit_contents = report_data.get('exhibit_contents', {})
        report_node.filing_text_content = report_data.get('filing_text_content', None)
        
        # Set xbrl_status flag
        report_node.xbrl_status = report_data.get('xbrl_status', None)
        
        # Extract market session and returns schedule using helper methods
        report_node.market_session = self._extract_market_session(report_data)
        report_node.returns_schedule = self._extract_returns_schedule(report_data)
            
        return report_node


    def _create_section_nodes_from_report(self, report_id, report_data):
        """
        Create section nodes from report extracted_sections and link them to the report
        
        Args:
            report_id: Report accession number
            report_data: Report data with extracted_sections, formType, cik, and created
        
        Returns:
            List of created section nodes
        """
        
        # Skip if no extracted sections
        extracted_sections = report_data.get('extracted_sections')
        if not extracted_sections:
            return []
        
        try:
            # Get report information needed for section nodes
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create section nodes
            section_nodes = []
            
            for section_name, content in extracted_sections.items():
                # Skip sections with null content
                if content is None:
                    logger.warning(f"Skipping section {section_name} with null content for report {report_id}")
                    continue
                
                # Create unique ID from report ID and section name
                content_id = f"{report_id}_{section_name}"
                
                # Create section content node
                section_node = ExtractedSectionContent(
                    content_id=content_id,
                    filing_id=report_id,
                    form_type=form_type,
                    section_name=section_name,
                    content=content,
                    filer_cik=cik,
                    filed_at=filed_at
                )
                
                section_nodes.append(section_node)
            
            # Create the nodes
            if section_nodes:
                self.manager.merge_nodes(section_nodes)
                logger.info(f"Created {len(section_nodes)} section content nodes for report {report_id}")
                
                # Create relationships
                relationships = []
                for section_node in section_nodes:
                    relationships.append((
                        ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                        section_node,
                        RelationType.HAS_SECTION
                    ))
                
                if relationships:
                    self.manager.merge_relationships(relationships)
                    logger.info(f"Created {len(relationships)} HAS_SECTION relationships for report {report_id}")
            
            return section_nodes
        
        except Exception as e:
            logger.error(f"Error creating section nodes for report {report_id}: {e}", exc_info=True)
            return []


    def _create_exhibit_nodes_from_report(self, report_id, report_data):
        """
        Create exhibit nodes from report exhibit_contents and link them to the report
        
        Args:
            report_id: Report accession number
            report_data: Report data with exhibit_contents, formType, cik, and created
        
        Returns:
            List of created exhibit nodes
        """
        
        # Skip if no exhibit contents
        exhibit_contents = report_data.get('exhibit_contents')
        if not exhibit_contents:
            return []
        
        try:
            # Make sure exhibit_contents is a dictionary if it's a JSON string
            if isinstance(exhibit_contents, str):
                exhibit_contents = json.loads(exhibit_contents)
            
            # Get report information needed for exhibit nodes
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create exhibit nodes
            exhibit_nodes = []
            
            for exhibit_number, content in exhibit_contents.items():
                if not content:
                    continue
                
                # Create unique ID from report ID and exhibit number
                content_id = f"{report_id}_EX-{exhibit_number}"
                
                # Handle different content formats
                content_str = content
                if isinstance(content, dict) and 'text' in content:
                    content_str = content['text']
                elif not isinstance(content, str):
                    content_str = str(content)
                
                # Create exhibit content node
                exhibit_node = ExhibitContent(
                    content_id=content_id,
                    filing_id=report_id,
                    form_type=form_type,
                    exhibit_number=exhibit_number,
                    content=content_str,
                    filer_cik=cik,
                    filed_at=filed_at
                )
                
                exhibit_nodes.append(exhibit_node)
            
            # Create the nodes
            if exhibit_nodes:
                self.manager.merge_nodes(exhibit_nodes)
                logger.info(f"Created {len(exhibit_nodes)} exhibit content nodes for report {report_id}")
                
                # Create relationships
                relationships = []
                for exhibit_node in exhibit_nodes:
                    relationships.append((
                        ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                        exhibit_node,
                        RelationType.HAS_EXHIBIT
                    ))
                
                if relationships:
                    self.manager.merge_relationships(relationships)
                    logger.info(f"Created {len(relationships)} HAS_EXHIBIT relationships for report {report_id}")
            
            return exhibit_nodes
        
        except Exception as e:
            logger.error(f"Error creating exhibit nodes for report {report_id}: {e}", exc_info=True)
            return []


    def _create_filing_text_content_nodes_from_report(self, report_id, report_data):
        """
        Create filing text content node from report filing_text_content and link it to the report
        
        Args:
            report_id: Report accession number
            report_data: Report data with filing_text_content, formType, cik, and created
        
        Returns:
            List containing the created filing text content node, or empty list if none created
        """
        
        # Skip if no filing text content
        filing_text_content = report_data.get('filing_text_content')
        if not filing_text_content:
            return []
        
        try:
            # Get report information needed for the filing text content node
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create unique ID for this filing text content
            content_id = f"{report_id}_text"
            
            # Create filing text content node
            filing_text_node = FilingTextContent(
                content_id=content_id,
                filing_id=report_id,
                form_type=form_type,
                content=filing_text_content,
                filer_cik=cik,
                filed_at=filed_at
            )
            
            # Create the node using Neo4jManager's merge_nodes method
            self.manager.merge_nodes([filing_text_node])
            logger.info(f"Created filing text content node for report {report_id}")
            
            # Create relationship using Neo4jManager's merge_relationships method
            relationship = [(
                ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                filing_text_node,
                RelationType.HAS_FILING_TEXT
            )]
            
            self.manager.merge_relationships(relationship)
            logger.info(f"Created HAS_FILING_TEXT relationship for report {report_id}")
            
            return [filing_text_node]
        
        except Exception as e:
            logger.error(f"Error creating filing text content node for report {report_id}: {e}", exc_info=True)
            return []


    def _create_financial_statement_nodes_from_report(self, report_id, report_data):
        """
        Create financial statement nodes from report financial_statements and link them to the report.
        Creates at most 4 nodes - one for each statement type (BalanceSheets, StatementsOfIncome, etc.)
        
        Args:
            report_id: Report accession number
            report_data: Report data with financial_statements, formType, cik, and created
    
        Returns:
            List of created financial statement nodes
        """
        
        
        # Skip if no financial statements
        financial_statements = report_data.get('financial_statements')
        if not financial_statements:
            return []
        
        try:
            # Make sure financial_statements is a dictionary if it's a JSON string
            if isinstance(financial_statements, str):
                financial_statements = json.loads(financial_statements)
            
            # Get report information needed for financial statement nodes
            form_type = report_data.get('formType', '')
            cik = report_data.get('cik', '')
            filed_at = report_data.get('created', '')
            
            # Create financial statement nodes - one for each statement type
            financial_nodes = []
            
            # Process each statement type (BalanceSheets, StatementsOfIncome, etc.)
            for statement_type, metrics in financial_statements.items():
                if not metrics:
                    continue
                
                # Create unique ID for this statement type
                content_id = f"{report_id}_{statement_type}"
                
                # Store the entire content as JSON
                content_json = json.dumps(metrics)
                
                # Create financial statement content node
                financial_node = FinancialStatementContent(
                    content_id=content_id,
                    filing_id=report_id,
                    form_type=form_type,
                    statement_type=statement_type,
                    value=content_json,  # Store the entire content as JSON
                    filer_cik=cik,
                    filed_at=filed_at
                )
                
                financial_nodes.append(financial_node)
            
            # Create the nodes using Neo4jManager's merge_nodes method
            if financial_nodes:
                self.manager.merge_nodes(financial_nodes)
                logger.info(f"Created {len(financial_nodes)} financial statement content nodes for report {report_id}")
                
                # Create relationships using Neo4jManager's merge_relationships method
                relationships = []
                for financial_node in financial_nodes:
                    relationships.append((
                        ReportNode(accessionNo=report_id, primaryDocumentUrl='', cik=''),
                        financial_node,
                        RelationType.HAS_FINANCIAL_STATEMENT
                    ))
                
                if relationships:
                    self.manager.merge_relationships(relationships)
                    logger.info(f"Created {len(relationships)} HAS_FINANCIAL_STATEMENT relationships for report {report_id}")
            
            return financial_nodes
        
        except Exception as e:
            logger.error(f"Error creating financial statement nodes for report {report_id}: {e}", exc_info=True)
            return []



    
    def _process_report_companies(self, report_json: Dict[str, Any], company_nodes: Dict[str, 'CompanyNode']):
        """
        Extract and create company nodes from report data
        
        Args:
            report_json: The report JSON data
            company_nodes: Dictionary to store company nodes (cik -> node)
        """
        
        # Get universe data for mapping
        universe_data = self._get_universe()
        ticker_to_cik = {}
        for symbol, data in universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
        
        # Extract symbols using the unified method
        symbols = self._extract_symbols_from_data(report_json)
        
        # Create company nodes for all symbols
        for symbol in symbols:
            symbol_upper = symbol.upper()
            cik = ticker_to_cik.get(symbol_upper)
            if not cik:
                logger.warning(f"No CIK found for symbol {symbol_upper}")
                continue
                
            # Skip if we already processed this company
            if cik in company_nodes:
                continue
                
            # Get company data
            company_data = universe_data.get(symbol_upper, {})
            name = company_data.get('company_name', company_data.get('name', symbol_upper))
                
            # Create company node
            company = CompanyNode(
                cik=cik,
                name=name,
                ticker=symbol_upper
            )
                
            # Add additional fields if available
            for field in ['exchange', 'sector', 'industry', 'sic', 'sic_name']:
                if field in company_data:
                    setattr(company, field, company_data[field])
                
            company_nodes[cik] = company



    def _prepare_report_relationships(self, report_data, symbols, universe_data, ticker_to_cik):
        """Prepare relationship parameters for symbols"""
        # Extract timestamps with proper parsing
        filed_at = parse_date(report_data.get('filedAt')) if report_data.get('filedAt') else None
        filed_str = filed_at.isoformat() if filed_at else ""
        
        # Delegate to the common method
        return self._prepare_entity_relationship_params(
            data_item=report_data,
            symbols=symbols,
            universe_data=universe_data,
            ticker_to_cik=ticker_to_cik,
            timestamp=filed_str
        )

