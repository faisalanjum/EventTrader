import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from utils.date_utils import parse_news_dates, parse_date 
from utils.redis_constants import RedisKeys


from ..EventTraderNodes import (
    PreparedRemarkNode, QuestionAnswerNode,
    FullTranscriptTextNode, QAExchangeNode, TranscriptNode
)



logger = logging.getLogger(__name__)

class TranscriptMixin:
    """
    Handles processing and storage of transcript data into Neo4j.
    """

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
                        raw = self.event_trader_redis.history_client.get(key)
                        if not raw:
                            logger.warning(f"No data found for key {key}")
                            continue

                        data = json.loads(raw)
                        transcript_id = data.get("id") or key.split(":")[-1]
                        namespace = key.split(":")[1] if "withreturns" in key else ""

                        success = self._process_deduplicated_transcript(transcript_id, data)
                        if success:
                            processed += 1
                            if namespace == "withreturns":
                                try:
                                    self.event_trader_redis.history_client.client.delete(key)
                                    logger.info(f"Deleted processed withreturns key: {key}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete key {key}: {e}")
                        else:
                            failed += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to process key {key}: {e}")
                        failed += 1

            logger.info(f"Transcript processing complete: {processed} success, {failed} failed")
            return processed > 0 or failed == 0

        except Exception as e:
            logger.error(f"Critical error in process_transcripts_to_neo4j: {e}")
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

            return self._execute_transcript_database_operations(
                transcript_id, transcript_node, valid_symbols,
                company_params, sector_params, industry_params, market_params, timestamps,
                transcript_data
            )
        except Exception as e:
            logger.error(f"Error processing transcript {transcript_id}: {e}")
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
            logger.error(f"Error executing DB ops for transcript {transcript_id}: {e}")
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
            for idx, pair in enumerate(transcript_data["qa_pairs"]):
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
                
                exchanges = flatten_exchanges(exchanges_raw)
                
                if exchanges:
                    exch_id = f"{transcript_id}_qa__{idx}"
                    exchange_ids.append(exch_id)
                    nodes_to_create.append(QAExchangeNode(
                        id=exch_id,
                        transcript_id=transcript_id,
                        exchanges=exchanges,
                        questioner=pair.get("questioner"),
                        questioner_title=pair.get("questioner_title"),
                        responders=pair.get("responders"),
                        responder_title=pair.get("responder_title"),
                        sequence=idx
                    ))
                    add_rel("Transcript", transcript_id, "QAExchange", exch_id, "HAS_QA_EXCHANGE")

            for i in range(len(exchange_ids) - 1):
                add_rel("QAExchange", exchange_ids[i], "QAExchange", exchange_ids[i + 1], "NEXT_EXCHANGE")

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

