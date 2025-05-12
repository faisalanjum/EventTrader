import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from utils.date_utils import parse_news_dates, parse_date 
from redisDB.redis_constants import RedisKeys
from config.feature_flags import QA_CLASSIFICATION_MODEL, QA_SUBSTANTIAL_WORD_COUNT


from ..EventTraderNodes import (
    PreparedRemarkNode, QuestionAnswerNode,
    FullTranscriptTextNode, QAExchangeNode, TranscriptNode
)



logger = logging.getLogger(__name__)

class TranscriptMixin:
    """
    Handles processing and storage of transcript data into Neo4j.
    """

    def _is_qa_content_substantial(self, combined_text: str) -> bool:
        """
        Checks if QA content is substantial (>= 15 words) or, if shorter,
        uses an LLM to determine if it's more than just filler/salutations.
        """
        word_count = len(combined_text.split())

        if word_count >= QA_SUBSTANTIAL_WORD_COUNT:
            logger.debug(f"QA content substantial based on word count ({word_count} >= {QA_SUBSTANTIAL_WORD_COUNT}).")
            return True # Substantial based on length

        # If short, check with LLM (if available)
        if not hasattr(self, 'openai_client') or not self.openai_client or \
           not hasattr(self, 'rate_limiter') or not self.rate_limiter:
            logger.warning(f"Skipping LLM check for short QA content (words={word_count}) due to missing OpenAI client/rate limiter in Neo4jProcessor.")
            return True # Default to substantial

        # Get model from feature flags
        llm_model = QA_CLASSIFICATION_MODEL
        try:
            self.rate_limiter.wait_if_needed(llm_model)
        except Exception as rate_limit_err:
             logger.error(f"Rate limiter check failed for model {llm_model}: {rate_limit_err}. Skipping LLM check.", exc_info=True)
             return True # Default to substantial

        # Define the output schema
        output_schema = { 
            "type": "object",
            "properties": {
                "is_filler_only": {
                    "type": "boolean",
                    "description": "True if the text contains ONLY conversational filler, greetings, acknowledgements, or thank yous, with no substantial question or answer content. False otherwise."
                }
            },
            "required": ["is_filler_only"],
            "additionalProperties": False
        }

        # Prepare prompt messages
        messages = [
            {"role": "system", "content": "You are an assistant classifying short text snippets based on provided schema."}, 
            {"role": "user", "content": f"Analyze the following text from an earnings call Q&A exchange. Determine if it ONLY contains conversational filler (greetings, thanks, acknowledgements) with no substantial info. Output according to the 'qa_filler_check' schema.\n\nText:\n\"\"\"\n{combined_text}\n\"\"\""}
        ]

        try:
            response = self.openai_client.responses.create(
                model=llm_model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "qa_filler_check", # Schema name
                        "strict": True,
                        "schema": output_schema
                    }
                },
                temperature=0.0 # Deterministic output
            )

            # Parse the structured response
            is_just_filler = False # Default assumption if parsing fails
            if response.output and len(response.output) > 0:
                # Check for refusal first
                is_refusal = any(item.type in ["response.refusal.delta", "response.refusal.done"] 
                                 for item in response.output[0].content)
                if is_refusal:
                    logger.warning(f"Model {llm_model} refused the QA filler check request for content: '{combined_text[:50]}...'")
                    return True # Default to substantial on refusal
                
                # Find the output_text content block
                for item in response.output[0].content:
                    if item.type == "output_text":
                        try:
                            parsed = json.loads(item.text)
                            if "is_filler_only" in parsed and isinstance(parsed["is_filler_only"], bool):
                                is_just_filler = parsed["is_filler_only"]
                                logger.info(f"LLM check for QA (words={word_count}): Content='{combined_text}...'. Is filler={is_just_filler}")
                                break # Found valid result
                            else:
                                logger.warning(f"LLM check for QA (words={word_count}, model={llm_model}): Invalid JSON structure in response: {item.text}")
                        except json.JSONDecodeError:
                             logger.warning(f"LLM check for QA (words={word_count}, model={llm_model}): Failed to decode JSON from response: {item.text}")
                        except Exception as parse_err:
                             logger.error(f"LLM check for QA (words={word_count}, model={llm_model}): Error parsing response item {item.text}: {parse_err}", exc_info=True)
                    # If loop finishes without break, parsing failed or block wasn't found
                    else: 
                        logger.warning(f"LLM check for QA (words={word_count}, model={llm_model}): No 'output_text' block found in response.")

            else:
                 logger.warning(f"LLM check for QA (words={word_count}, model={llm_model}): No output received from API.")

            # Return TRUE (substantial) if the LLM determined it was FALSE (not just filler)
            return not is_just_filler

        except Exception as e:
            logger.error(f"LLM check failed for QA content (words={word_count}, model={llm_model}): {e}", exc_info=True)
            return True # Default to substantial on API error

    def _finalize_transcript_batch(self, delete_client, redis_key, transcript_id, success, namespace, failure_reason=None):
        """
        Atomic finalization of transcript processing:
        1. For success=True + withreturns: verify meta before deleting key
        2. For success=False: mark as failed
        """
        meta_key = f"tracking:meta:{RedisKeys.SOURCE_TRANSCRIPTS}:{transcript_id}"
        try:
            if success:
                # Step 1: Always make sure inserted_into_neo4j_at is marked
                delete_client.mark_lifecycle_timestamp(meta_key, "inserted_into_neo4j_at")
                
                # Step 2: Only delete withreturns keys and verify mark exists first
                if namespace == RedisKeys.SUFFIX_WITHRETURNS:
                    if delete_client.client.hexists(meta_key, "inserted_into_neo4j_at"):
                        delete_client.client.delete(redis_key)
                        logger.info(f"Deleted processed withreturns key: {redis_key}")
                    else:
                        logger.warning(f"Not deleting {redis_key} - meta tracking not confirmed")
            else:
                # For failures, mark failed_at with reason
                delete_client.mark_lifecycle_timestamp(meta_key, "failed_at", reason=failure_reason or "neo4j_insertion_failed")
                
        except Exception as e:
            logger.error(f"Error in transcript finalization for {transcript_id}: {e}", exc_info=True)

    def process_transcripts_to_neo4j(self, batch_size=5, max_items=None, include_without_returns=True) -> bool:
        """
        Process transcript items from Redis to Neo4j.
        Minimal v1 implementation following news/report pattern.
        """

        try:
            if not self.manager:
                if not self.connect():
                    logger.error("Cannot connect to Neo4j")
                    return False

            if not hasattr(self, 'event_trader_redis') or not self.event_trader_redis or not self.event_trader_redis.history_client:
                logger.warning("No Redis history client available for transcript processing")
                return False

            # Get withreturns keys
            withreturns_pattern = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                key_type=RedisKeys.SUFFIX_WITHRETURNS,
                identifier="*"
            )
            withreturns_keys = list(self.event_trader_redis.history_client.client.scan_iter(match=withreturns_pattern))
            logger.info(f"Found {len(withreturns_keys)} transcripts with returns")

            # Get withoutreturns keys
            withoutreturns_keys = []
            if include_without_returns:
                withoutreturns_pattern = RedisKeys.get_key(
                    source_type=RedisKeys.SOURCE_TRANSCRIPTS,
                    key_type=RedisKeys.SUFFIX_WITHOUTRETURNS,
                    identifier="*"
                )
                withoutreturns_keys = list(self.event_trader_redis.history_client.client.scan_iter(match=withoutreturns_pattern))
                logger.info(f"Found {len(withoutreturns_keys)} transcripts without returns")

            # Combine keys
            all_keys = withreturns_keys + withoutreturns_keys
            if not all_keys:
                logger.info("No transcript keys found to process")
                return True

            if max_items:
                all_keys = all_keys[:max_items]

            total = len(all_keys)
            processed = 0
            failed = 0

            for i in range(0, total, batch_size):
                batch = all_keys[i:i + batch_size]
                logger.info(f"Processing batch {i // batch_size + 1}, items {i + 1}–{i + len(batch)} of {total}")

                for key in batch:
                    try:
                        # Extract namespace precisely from key structure
                        namespace = key.split(":")[1]  # 'withreturns' or 'withoutreturns'
                        
                        # Try history_client first, fallback to live_client
                        delete_client = self.event_trader_redis.history_client
                        raw = delete_client.get(key)
                        
                        if not raw:
                            raw = self.event_trader_redis.live_client.get(key)
                            if raw:
                                delete_client = self.event_trader_redis.live_client
                                logger.warning(f"[FALLBACK] Found {key} in live_client instead of history_client")
                        
                        # If we didn't find raw data, still finalize with failure
                        if not raw:
                            self._finalize_transcript_batch(
                                delete_client=delete_client,
                                redis_key=key,
                                transcript_id=key.split(":")[-1],
                                success=False,
                                namespace=namespace,
                                failure_reason="raw_missing"
                            )
                            logger.warning(f"No data found for key {key}")
                            failed += 1
                            continue
                        
                        # Process the data
                        data = json.loads(raw)
                        transcript_id = data.get("id") or key.split(":")[-1]
                        
                        success = self._process_deduplicated_transcript(transcript_id, data)
                        
                        # Always finalize with atomic meta tracking
                        self._finalize_transcript_batch(
                            delete_client=delete_client,
                            redis_key=key, 
                            transcript_id=transcript_id,
                            success=success,
                            namespace=namespace,
                            failure_reason="neo4j_insertion_failed"
                        )
                        
                        processed += int(success)
                        failed += int(not success)
                            
                    except Exception as e:
                        logger.error(f"Failed to process key {key}: {e}", exc_info=True)
                        failed += 1

            logger.info(f"Transcript processing complete: {processed} success, {failed} failed")
            return processed > 0 or failed == 0

        except Exception as e:
            logger.error(f"Critical error in process_transcripts_to_neo4j: {e}", exc_info=True)
            return False



    def _prepare_transcript_data(self, transcript_id, transcript_data):
        """
        Prepare transcript data for processing, extracting necessary information.

        Returns:
            tuple: (transcript_node, valid_symbols, company_params, sector_params, 
                    industry_params, market_params, timestamps)
        """
        # Get ticker to CIK mappings from universe data
        universe_data = self._get_universe()
        ticker_to_cik = {}
        for symbol, data in universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                ticker_to_cik[symbol.upper()] = str(cik).zfill(10)

        # Create TranscriptNode
        transcript_node = self._create_transcript_node_from_data(transcript_id, transcript_data)

        # Extract symbols
        symbols = self._extract_symbols_from_data(transcript_data)

        # Timestamps
        created_at = parse_date(transcript_data.get('created')) if transcript_data.get('created') else None
        updated_at = parse_date(transcript_data.get('updated')) if transcript_data.get('updated') else None
        filed_str = created_at.isoformat() if created_at else ""
        updated_str = updated_at.isoformat() if updated_at else filed_str

        # Prepare relationship params
        valid_symbols, company_params, sector_params, industry_params, market_params = self._prepare_entity_relationship_params(
            data_item=transcript_data,
            symbols=symbols,
            universe_data=universe_data,
            ticker_to_cik=ticker_to_cik,
            timestamp=filed_str
        )

        timestamps = (created_at, updated_at, filed_str, updated_str)
        return transcript_node, valid_symbols, company_params, sector_params, industry_params, market_params, timestamps


    def _process_deduplicated_transcript(self, transcript_id, transcript_data):
        """
        Process transcript data with deduplication and relationship generation.
        """
        logger.debug(f"Processing deduplicated transcript {transcript_id}")
        try:
            transcript_node, valid_symbols, company_params, sector_params, industry_params, market_params, timestamps = \
                self._prepare_transcript_data(transcript_id, transcript_data)

            success = self._execute_transcript_database_operations(
                transcript_id, transcript_node, valid_symbols,
                company_params, sector_params, industry_params, market_params, timestamps,
                transcript_data
            )

            # We no longer do meta tracking here, it's handled by _finalize_transcript_batch
            return success
        except Exception as e:
            logger.error(f"Error processing transcript {transcript_id}: {e}", exc_info=True)
            return False




    def _execute_transcript_database_operations(self, transcript_id, transcript_node, valid_symbols,
                                               company_params, sector_params, industry_params, market_params, timestamps,
                                               transcript_data=None):
        """
        Execute all database operations for a transcript.
        """
        try:
            # 1. Merge the Transcript node
            self.manager.merge_nodes([transcript_node])
            logger.info(f"Merged transcript node: {transcript_id}")

            # 2. Create HAS_TRANSCRIPT relationship from Company to Transcript
            primary_symbol = transcript_node.symbol.upper()
            universe_data = self._get_universe()
            cik = universe_data.get(primary_symbol, {}).get("cik", "").strip().zfill(10)

            if cik:
                self.manager.create_relationships(
                    source_label="Company",
                    source_id_field="cik",
                    source_id_value=cik,
                    target_label="Transcript",
                    target_match_clause="{id: '" + transcript_id + "'}",
                    rel_type="HAS_TRANSCRIPT",
                    params=[{"properties": {}}]
                )
                logger.info(f"Created HAS_TRANSCRIPT relationship for {primary_symbol} ({cik})")

            # 3. Create INFLUENCES relationships
            with self.manager.driver.session() as session:
                self._create_influences_relationships(session, transcript_id, "Transcript", "Company", company_params)
                self._create_influences_relationships(session, transcript_id, "Transcript", "Sector", sector_params)
                self._create_influences_relationships(session, transcript_id, "Transcript", "Industry", industry_params)
                self._create_influences_relationships(session, transcript_id, "Transcript", "MarketIndex", market_params)

            # 4. Create and link additional transcript content nodes
            if transcript_data:
                self._process_transcript_content(transcript_id, transcript_data)

            return True

        except Exception as e:
            logger.error(f"Error executing DB ops for transcript {transcript_id}: {e}", exc_info=True)
            return False


    def _process_transcript_content(self, transcript_id, transcript_data):


        nodes_to_create = []
        relationships = []
        
        # Create QAExchange vector-index once before generating embeddings
        self._create_qaexchange_vector_index()

        def add_rel(source_label, source_id, target_label, target_id, rel_type):
            relationships.append({
                "source_label": source_label,
                "source_id": source_id,
                "target_label": target_label,
                "target_id": target_id,
                "rel_type": rel_type
            })

        has_pr = bool(transcript_data.get("prepared_remarks"))
        has_qa_pairs = bool(transcript_data.get("qa_pairs"))
        has_qa = bool(transcript_data.get("questions_and_answers"))
        has_full = bool(transcript_data.get("full_transcript"))

        # Level 1: Prepared Remarks
        if has_pr:
            pr_id = f"{transcript_id}_pr"
            nodes_to_create.append(PreparedRemarkNode(id=pr_id, content=transcript_data["prepared_remarks"]))
            add_rel("Transcript", transcript_id, "PreparedRemark", pr_id, "HAS_PREPARED_REMARKS")

        # Level 2: QAExchangeNode from qa_pairs
        if has_qa_pairs:
            exchange_ids = []
            nodes_to_create_objects = [] # List to hold actual Node objects
            relationships_to_create_params = [] # Batch relationship creation parameters
            last_valid_node_id = None
            current_valid_sequence_number = 0 # Sequence for *valid* nodes

            for original_idx, pair in enumerate(transcript_data["qa_pairs"]):
                exchanges_raw = pair.get("exchanges", [])
                if isinstance(exchanges_raw, str):
                    try:
                        exchanges_raw = json.loads(exchanges_raw)
                    except Exception:
                        exchanges_raw = []
                
                # Flatten exchanges to avoid nested maps that Neo4j can't store
                def flatten_exchanges(raw_exchanges):
                    flat = []
                    for entry in raw_exchanges:
                        if "question" in entry and isinstance(entry["question"], dict):
                            flat.append({
                                "role": "question",
                                **entry["question"]
                            })
                        elif "answer" in entry and isinstance(entry["answer"], dict):
                            flat.append({
                                "role": "answer",
                                **entry["answer"]
                            })
                    return flat
                
                current_exchanges_list = flatten_exchanges(exchanges_raw)
                
                if current_exchanges_list: # Only proceed if there are flattened exchanges
                    exch_id = f"{transcript_id}_qa__{current_valid_sequence_number}" # Use valid sequence number

                    # --- Filter Logic Integration --- 
                    # Generate text exactly like embedding process
                    combined_text = " ".join(
                        entry.get("text", "")
                        for entry in current_exchanges_list 
                        if entry.get("role") in {"question", "answer"}
                    ).strip()

                    # Call the check
                    is_substantial = self._is_qa_content_substantial(combined_text)
                    # --- End Filter Logic Integration ---

                    if is_substantial:
                        # Prepare node parameters dictionary first
                        node_params_dict = {
                            "id": exch_id,
                            "transcript_id": transcript_id,
                            "exchanges": json.dumps(current_exchanges_list), # Stringify here
                            "questioner": pair.get("questioner"),
                            "questioner_title": pair.get("questioner_title"),
                            "responders": pair.get("responders"),
                            "responder_title": pair.get("responder_title"),
                            "sequence": current_valid_sequence_number # Use valid sequence
                        }
                        # Create the Node object and add it to the list
                        nodes_to_create_objects.append(QAExchangeNode(**node_params_dict))
                        exchange_ids.append(exch_id) # Keep track of IDs for linking

                        # Prepare relationship to Transcript
                        relationships_to_create_params.append({ 
                           "source_label": "Transcript", "source_id": transcript_id, 
                           "target_label": "QAExchange", "target_id": exch_id, 
                           "rel_type": "HAS_QA_EXCHANGE"
                        })

                        # Prepare relationship to previous valid node
                        if last_valid_node_id:
                             relationships_to_create_params.append({
                                "source_label": "QAExchange", "source_id": last_valid_node_id,
                                "target_label": "QAExchange", "target_id": exch_id,
                                "rel_type": "NEXT_EXCHANGE"
                             })

                        # Update pointers
                        last_valid_node_id = exch_id
                        current_valid_sequence_number += 1
                    else:
                        logger.info(f"Skipping QA pair {original_idx} for {transcript_id} - not substantial (words={len(combined_text.split())}).")
                

            # Batch create nodes using merge_nodes with Node objects
            if nodes_to_create_objects:
                self.manager.merge_nodes(nodes_to_create_objects)
                logger.info(f"Batch created/merged {len(nodes_to_create_objects)} QAExchange nodes for {transcript_id}.")
            
            # Create relationships one by one (or using existing batch methods if manager has them)
            if relationships_to_create_params:
                logger.info(f"Creating {len(relationships_to_create_params)} QA relationships for {transcript_id}...")
                for rel in relationships_to_create_params:
                     try:
                        self.manager.create_relationships(
                            source_label=rel["source_label"],
                            source_id_field="id",
                            source_id_value=rel["source_id"],
                            target_label=rel["target_label"],
                            target_match_clause=f"{{id: '{rel['target_id']}'}}",
                            rel_type=rel["rel_type"],
                            params=[{"properties": {}}]
                        )
                     except Exception as rel_err:
                         logger.error(f"Failed to create relationship {rel}: {rel_err}", exc_info=True)
                logger.info(f"Finished creating QA relationships for {transcript_id}.")

        # Level 2 fallback: QuestionAnswerNode (used if no qa_pairs)
        elif has_qa:
            qa_id = f"{transcript_id}_qa"
            nodes_to_create.append(QuestionAnswerNode(
                id=qa_id,
                content=transcript_data["questions_and_answers"],
                speaker_roles=transcript_data.get("speaker_roles_LLM")
            ))
            add_rel("Transcript", transcript_id, "QuestionAnswer", qa_id, "HAS_QA_SECTION")

        # Level 3 fallback: FullTranscriptTextNode
        elif has_full:
            full_id = f"{transcript_id}_full"
            nodes_to_create.append(FullTranscriptTextNode(id=full_id, content=transcript_data["full_transcript"]))
            add_rel("Transcript", transcript_id, "FullTranscriptText", full_id, "HAS_FULL_TEXT")

        # Save all nodes and relationships
        if nodes_to_create:
            self.manager.merge_nodes(nodes_to_create)
            for rel in relationships:
                self.manager.create_relationships(
                    source_label=rel["source_label"],
                    source_id_field="id",
                    source_id_value=rel["source_id"],
                    target_label=rel["target_label"],
                    target_match_clause=f"{{id: '{rel['target_id']}'}}",
                    rel_type=rel["rel_type"],
                    params=[{"properties": {}}]
                )
                logger.info(f"Created {rel['rel_type']} relationship for transcript {transcript_id}")

            

    def _create_transcript_node_from_data(self, transcript_id, transcript_data):
        """Create a TranscriptNode from transcript data"""
        # TranscriptNode is now imported at the top of the file
        
        def safe_int(val, default=0):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def safe_dict(val):
            if isinstance(val, dict):
                return val
            try:
                return json.loads(val)
            except:
                return {}

        return TranscriptNode(
            id=transcript_id,
            symbol=transcript_data.get("symbol", ""),
            company_name=transcript_data.get("company_name", ""),
            conference_datetime=transcript_data.get("conference_datetime", ""),
            fiscal_quarter=safe_int(transcript_data.get("fiscal_quarter")),
            fiscal_year=safe_int(transcript_data.get("fiscal_year")),
            formType=transcript_data.get("formType", ""),
            calendar_quarter=transcript_data.get("calendar_quarter"),
            calendar_year=transcript_data.get("calendar_year"),
            created=transcript_data.get("created"),
            updated=transcript_data.get("updated"),
            speakers=safe_dict(transcript_data.get("speakers", {}))
        )



    # def _process_transcript_content(self, transcript_id, transcript_data):
    #     """Process additional transcript content nodes"""
    #     from ..EventTraderNodes import PreparedRemarkNode, QuestionAnswerNode, FullTranscriptTextNode
        
    #     nodes_to_create = []
    #     relationships = []
        
    #     # Create PreparedRemarkNode if data exists
    #     if prepared_remarks := transcript_data.get("prepared_remarks"):
    #         pr_id = f"{transcript_id}_pr"
    #         nodes_to_create.append(PreparedRemarkNode(id=pr_id, content=prepared_remarks))
    #         relationships.append({
    #             "source_label": "Transcript",
    #             "source_id": transcript_id,
    #             "target_label": "PreparedRemark",
    #             "target_id": pr_id,
    #             "rel_type": "HAS_PREPARED_REMARKS"
    #         })
            
    #     # Create QuestionAnswerNode if data exists
    #     if qa_section := transcript_data.get("questions_and_answers"):
    #         qa_id = f"{transcript_id}_qa"
    #         nodes_to_create.append(QuestionAnswerNode(
    #             id=qa_id, 
    #             content=qa_section,
    #             speaker_roles=transcript_data.get("speaker_roles_LLM")
    #         ))
    #         relationships.append({
    #             "source_label": "Transcript",
    #             "source_id": transcript_id,
    #             "target_label": "QuestionAnswer",
    #             "target_id": qa_id,
    #             "rel_type": "HAS_QA_SECTION"
    #         })
            
    #     # Create FullTranscriptTextNode if data exists
    #     if full_text := transcript_data.get("full_transcript"):
    #         full_id = f"{transcript_id}_full"
    #         nodes_to_create.append(FullTranscriptTextNode(id=full_id, content=full_text))
    #         relationships.append({
    #             "source_label": "Transcript",
    #             "source_id": transcript_id,
    #             "target_label": "FullTranscriptText",
    #             "target_id": full_id,
    #             "rel_type": "HAS_FULL_TEXT"
    #         })
        
    #     # Save nodes and create relationships if any were created
    #     if nodes_to_create:
    #         # Merge all nodes in one batch
    #         self.manager.merge_nodes(nodes_to_create)
            
    #         # Create relationships
    #         for rel in relationships:
    #             self.manager.create_relationships(
    #                 source_label=rel["source_label"],
    #                 source_id_field="id",
    #                 source_id_value=rel["source_id"],
    #                 target_label=rel["target_label"],
    #                 target_match_clause=f"{{id: '{rel['target_id']}'}}",
    #                 rel_type=rel["rel_type"],
    #                 params=[{"properties": {}}]
    #             )
    #             logger.info(f"Created {rel['rel_type']} relationship for transcript {transcript_id}")

