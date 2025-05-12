# neograph/mixins/embedding.py

# --- Add necessary imports used by the methods below ---
import logging
import json
import os
import asyncio
from hashlib import sha256
from typing import Dict, List, Any

from eventtrader.keys import OPENAI_API_KEY
from config.feature_flags import (
    CHROMADB_PERSIST_DIRECTORY,
    ENABLE_NEWS_EMBEDDINGS,
    OPENAI_EMBEDDING_MODEL,
    USE_CHROMADB_CACHING,
    OPENAI_EMBEDDING_DIMENSIONS,
    OPENAI_EMBED_CUTOFF,
    NEWS_VECTOR_INDEX_NAME,
    QAEXCHANGE_VECTOR_INDEX_NAME,
    ENABLE_QAEXCHANGE_EMBEDDINGS,
    MAX_EMBEDDING_CHARS,
    NEWS_EMBEDDING_BATCH_SIZE,
    QAEXCHANGE_EMBEDDING_BATCH_SIZE
)

# Updated path for local import
from openai_local.openai_parallel_embeddings import process_embeddings_in_parallel
from openai_local.openai_token_counter import truncate_for_embeddings, count_tokens

logger = logging.getLogger(__name__)

class EmbeddingMixin:
    """
    Handles vector embeddings, interaction with ChromaDB, and vector similarity search.
    """
    
    def create_vector_index(self, label, property_name, index_name=None, dimensions=1536, similarity_function="cosine"):
        """
        Create a vector index for any node type and property
        
        Args:
            label (str): Node label (e.g., 'News', 'Report', 'Company')
            property_name (str): Property name to index (e.g., 'embedding')
            index_name (str, optional): Name of the index. If None, will be generated
            dimensions (int): Number of dimensions in the vector
            similarity_function (str): Similarity function ('cosine', 'euclidean', or 'dot')
            
        Returns:
            bool: Success status
        """
        if not self.manager and not self.connect():
            return False
        
        try:
            # Generate index name if not provided
            if not index_name:
                index_name = f"{label.lower()}_{property_name}_vector_idx"
            
            # Check if index exists
            query = "SHOW VECTOR INDEXES WHERE name = $index_name"
            result = self.manager.execute_cypher_query(query, {"index_name": index_name})
            
            if result and (isinstance(result, list) and len(result) > 0 or 
                          not isinstance(result, list) and result):
                logger.debug(f"Vector index '{index_name}' already exists")
                
                # Don't create regular index on large embedding property to avoid size limitations
                # null_index_query = f"""
                # CREATE INDEX {label.lower()}_{property_name}_null_idx IF NOT EXISTS 
                # FOR (n:{label}) ON (n.{property_name})
                # """
                # self.manager.execute_cypher_query(null_index_query, {})
                # logger.debug(f"Created index for {label}.{property_name} property")
                
                return True
                
            # Create vector index
            create_query = f"""
            CREATE VECTOR INDEX {index_name}  IF NOT EXISTS
            FOR (n:{label}) ON (n.{property_name})
            OPTIONS {{indexConfig: {{
              `vector.dimensions`: {dimensions},
              `vector.similarity_function`: '{similarity_function}'
            }}}}
            """
            
            self.manager.execute_cypher_query(create_query, {})
            logger.info(f"Created vector index '{index_name}' for {label}.{property_name}")
            
            # Don't create regular index on large embedding property to avoid size limitations
            # null_index_query = f"""
            # CREATE INDEX {label.lower()}_{property_name}_null_idx IF NOT EXISTS 
            # FOR (n:{label}) ON (n.{property_name})
            # """
            # self.manager.execute_cypher_query(null_index_query, {})
            # logger.debug(f"Created index for {label}.{property_name} property")
            
            return True
                
        except Exception as e:
            logger.error(f"Error creating vector index: {e}", exc_info=True)
            return False

    def _create_news_vector_index(self):
        """Create a vector index for News nodes if it doesn't exist"""
        
        return self.create_vector_index(
            label="News", 
            property_name="embedding", 
            index_name=NEWS_VECTOR_INDEX_NAME,
            dimensions=OPENAI_EMBEDDING_DIMENSIONS
        )
    

    def _create_qaexchange_vector_index(self):
       """Create a vector index for QAExchange nodes if it doesn't exist"""
       
       return self.create_vector_index(
           label="QAExchange", 
           property_name="embedding", 
           index_name=QAEXCHANGE_VECTOR_INDEX_NAME,
           dimensions=OPENAI_EMBEDDING_DIMENSIONS
       )



    def _fetch_chromadb_embeddings(self, all_items, batch_size=100):
        """
        Perform batch lookups in ChromaDB for cached embeddings.
        """
        
        
        cached_embeddings = {}
        nodes_needing_embeddings = []
        
        try:
            logger.info(f"[EMBED-FLOW] Starting ChromaDB batch lookup for {len(all_items)} items")
            
            for batch_start in range(0, len(all_items), batch_size):
                batch = all_items[batch_start:batch_start + batch_size]
                
                # Create batch data
                content_hashes = []
                hash_to_item = {}
                
                for item in batch:
                    node_id = item["id"]
                    content = item["content"]
                    content_hash = sha256(content.encode()).hexdigest()
                    content_hashes.append(content_hash)
                    hash_to_item[content_hash] = {"id": node_id, "content": content}
                
                # Batch lookup in ChromaDB
                chroma_result = self.chroma_collection.get(ids=content_hashes, include=['embeddings'])
                
                # Process results
                if (chroma_result and chroma_result.get('ids') and 
                    len(chroma_result['ids']) > 0 and 'embeddings' in chroma_result):
                    
                    found_hashes = set()
                    for i, hash_id in enumerate(chroma_result['ids']):
                        if i < len(chroma_result['embeddings']):
                            item_data = hash_to_item[hash_id]
                            cached_embeddings[item_data["id"]] = {
                                "embedding": chroma_result['embeddings'][i],
                                "content": item_data["content"]
                            }
                            found_hashes.add(hash_id)
                
                    # Add items not found to nodes_needing_embeddings
                    for hash_id, item_data in hash_to_item.items():
                        if hash_id not in found_hashes:
                            nodes_needing_embeddings.append(item_data)
                else:
                    # If this batch lookup failed completely, add all items from this batch to nodes_needing_embeddings
                    nodes_needing_embeddings.extend(hash_to_item.values())
        
            logger.info(f"[EMBED-FLOW] ChromaDB batch returned {len(cached_embeddings)}/{len(all_items)} cached embeddings")
            
        except Exception as e:
            logger.warning(f"Error in batch ChromaDB lookup: {e}")
            # Add all remaining items to nodes_needing_embeddings
            for item in all_items:
                if item["id"] not in cached_embeddings:
                    nodes_needing_embeddings.append({"id": item["id"], "content": item["content"]})
        
        return cached_embeddings, nodes_needing_embeddings

    def _store_cached_embeddings_in_neo4j(self, label, id_property, embedding_property, cached_embeddings, batch_size=100):
        """
        Update Neo4j nodes with cached embeddings in batch.
        """
        if not cached_embeddings:
            return 0
            
        total_cached = 0
        
        try:
            batch_params = [{"id": node_id, "embedding": data["embedding"]} 
                           for node_id, data in cached_embeddings.items()]
            
            # Process in sub-batches
            for i in range(0, len(batch_params), batch_size):
                sub_batch = batch_params[i:i + batch_size]
                
                try:
                    store_query = f"""
                    UNWIND $batch AS item
                    MATCH (n:{label} {{{id_property}: item.id}})
                    WHERE n.{embedding_property} IS NULL 
                    CALL db.create.setNodeVectorProperty(n, "{embedding_property}", item.embedding)
                    RETURN count(n) AS processed
                    """
                    
                    result = self.manager.execute_cypher_query(store_query, {"batch": sub_batch})
                    processed = result.get("processed", 0) if result else 0
                    total_cached += processed
                except Exception as e:
                    logger.error(f"Error applying cached embeddings batch: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error in batch update: {e}", exc_info=True)
        
        return total_cached

    def batch_embeddings_for_nodes(self, label, id_property, content_property, embedding_property="embedding", 
                                       batch_size=50, max_items=None, create_index=True, check_chromadb=True):
        """Generate embeddings for any node type using Neo4j's GenAI integration"""

        
        results = {"processed": 0, "error": 0, "cached": 0}
        
        # Early exit checks
        if not ENABLE_NEWS_EMBEDDINGS:
            return {"status": "skipped", "reason": "embeddings disabled", **results}
        if not OPENAI_API_KEY:
            return {"status": "error", "reason": "missing API key", **results}
        if not self.manager and not self.connect():
            return {"status": "error", "reason": "Neo4j connection failed", **results}
        
        try:
            # Configure ChromaDB usage
            use_chromadb = check_chromadb and USE_CHROMADB_CACHING
            if use_chromadb and self.chroma_collection is None:
                self._initialize_chroma_db()
                if self.chroma_collection is None:
                    use_chromadb = False
                    logger.warning("[EMBED-FLOW] ChromaDB collection is not initialized, continuing without caching")
            
            # Create vector index if needed
            if create_index:
                self.create_vector_index(label=label, property_name=embedding_property,
                                        dimensions=OPENAI_EMBEDDING_DIMENSIONS)
            
            # Find nodes needing embeddings
            query = f"""
            MATCH (n:{label})
            WHERE n.{embedding_property} IS NULL AND n.{content_property} IS NOT NULL
            WITH n, n.{content_property} AS content
            WHERE trim(content) <> ''
            RETURN n.{id_property} as id, content
            """
            if max_items:
                query += f" LIMIT {max_items}"
            
            # all_items = self.manager.execute_cypher_query(query, {})
            all_items = self.manager.execute_cypher_query_all(query, {})
            
            # Handle empty results
            if not all_items:
                logger.info(f"[EMBED-FLOW] No {label} items found needing embeddings")
                return {"status": "completed", "reason": "no items needed embeddings", **results}
            if not isinstance(all_items, list):
                all_items = [all_items]
            if len(all_items) == 0:
                logger.info(f"[EMBED-FLOW] No {label} items found needing embeddings")
                return {"status": "completed", "reason": "no items needed embeddings", **results}
            
            logger.info(f"[EMBED-FLOW] Found {len(all_items)} {label} nodes needing embeddings")
            
            # Get cached embeddings and nodes needing embeddings
            cached_embeddings = {}
            if use_chromadb:
                cached_embeddings, nodes_needing_embeddings = self._fetch_chromadb_embeddings(all_items, batch_size=100)
            else:
                nodes_needing_embeddings = [{"id": item["id"], "content": item["content"]} for item in all_items]
            
            # Apply cached embeddings in batch
            if cached_embeddings:
                total_cached = self._store_cached_embeddings_in_neo4j(
                    label=label, id_property=id_property, embedding_property=embedding_property,
                    cached_embeddings=cached_embeddings
                )
                results["cached"] = total_cached
                logger.info(f"Applied {total_cached} cached embeddings from ChromaDB")
            
            # Generate new embeddings for remaining nodes
            if nodes_needing_embeddings:
                logger.info(f"Generating embeddings for {len(nodes_needing_embeddings)} {label} nodes")
                
                # Prepare lists for batch processing
                all_nodes = [node["id"] for node in nodes_needing_embeddings]
                all_contents = [node["content"] for node in nodes_needing_embeddings]
                
                # Truncate all contents to token limit
                all_contents = [truncate_for_embeddings(content, OPENAI_EMBEDDING_MODEL) for content in all_contents]
                
                # NEW CODE: Use parallel OpenAI implementation for larger batches
                if len(nodes_needing_embeddings) >= OPENAI_EMBED_CUTOFF:
                    try:
                        logger.info(f"[EMBED-FLOW] Using parallel OpenAI embeddings for {len(nodes_needing_embeddings)} items")
                        
                        embeddings = asyncio.run(process_embeddings_in_parallel(
                            texts=all_contents,
                            model=OPENAI_EMBEDDING_MODEL,
                            api_key=OPENAI_API_KEY
                        ))
                        
                        # Process results
                        processed = 0
                        for i, embedding in enumerate(embeddings):
                            if embedding:
                                # Store in Neo4j
                                set_query = f"""
                                MATCH (n:{label} {{{id_property}: $nodeId}})
                                WHERE n.{embedding_property} IS NULL
                                CALL db.create.setNodeVectorProperty(n, "{embedding_property}", $embedding)
                                RETURN count(n) AS updated
                                """
                                result = self.manager.execute_cypher_query(set_query, {
                                    "nodeId": all_nodes[i],
                                    "embedding": embedding
                                })
                                if result and result.get("updated", 0) > 0:
                                    processed += 1
                                    
                                    # Store in ChromaDB if enabled
                                    if use_chromadb:
                                        try:
                                            content_hash = sha256(all_contents[i].encode()).hexdigest()
                                            self.chroma_collection.add(
                                                ids=[content_hash],
                                                documents=[all_contents[i]],
                                                embeddings=[embedding]
                                            )
                                        except Exception as e:
                                            if "Insert of existing embedding ID" not in str(e):
                                                logger.warning(f"Error storing in ChromaDB: {e}")
                        
                        # After processing all embeddings, update results and return
                        results["processed"] = processed
                        logger.info(f"[EMBED-FLOW] Completed parallel OpenAI embedding: {results}")
                        return {"status": "completed", **results, "total": len(all_items)}
                        
                    except Exception as e:
                        # Fall back to Neo4j approach on error
                        logger.warning(f"[EMBED-FLOW] Parallel OpenAI embedding failed, falling back to Neo4j integration: {e}")
                        # Continue to original code below
                
                # Updated query that works around Neo4j's limitations with complex expressions in WITH clauses
                concurrent_query = f"""
                // First, pre-compute the batch indices
                WITH $nodes AS nodes, $contents AS contents, $batch_size AS batchSize
                WITH nodes, contents, batchSize, size(nodes) AS total
                UNWIND range(0, total-1, batchSize) AS batchStart
                WITH batchStart, 
                     CASE WHEN batchStart + batchSize > size(nodes) THEN size(nodes) ELSE batchStart + batchSize END AS batchEnd,
                     nodes, contents

                // Now process each batch with concurrent transactions
                CALL {{
                    WITH batchStart, batchEnd, nodes, contents
                    UNWIND range(batchStart, batchEnd-1) AS i
                    WITH i, nodes[i] AS nodeId, contents[i] AS content, collect(i) AS indices, collect(contents[i]) AS batchContents
                    WITH indices, batchContents, collect(nodeId) AS batchNodes, $config AS config
                    
                    // Process the whole batch at once for efficiency
                    CALL genai.vector.encodeBatch(batchContents, 'OpenAI', config)
                    YIELD index, vector
                    
                    // Map back to the right node
                    WITH batchNodes[index] AS nodeId, vector
                    
                    // Apply to Neo4j node
                    MATCH (n:{label} {{{id_property}: nodeId}})
                    WHERE n.{embedding_property} IS NULL
                    CALL db.create.setNodeVectorProperty(n, "{embedding_property}", vector)
                    RETURN nodeId
                }} IN TRANSACTIONS OF 1 ROW

                // Count total processed nodes
                RETURN count(*) as processed
                """
                
                try:
                    result = self.manager.execute_cypher_query(concurrent_query, {
                        "nodes": all_nodes, "contents": all_contents, "batch_size": batch_size,
                        "config": {"token": OPENAI_API_KEY, "model": OPENAI_EMBEDDING_MODEL}
                    })
                    
                    processed = result.get("processed", 0) if result else 0
                    results["processed"] = processed
                    
                    if processed > 0:
                        # Log successful embedding generation
                        logger.info(f"[EMBED-FLOW] Neo4j encodeBatch generated {processed}/{len(nodes_needing_embeddings)} embeddings successfully")
                    else:
                        # 6. Embedding Generation Failure Path
                        logger.warning(f"[EMBED-FLOW] Neo4j encodeBatch FAILED to generate any embeddings for {len(nodes_needing_embeddings)} items")
                    
                    # Store new embeddings in ChromaDB if enabled
                    if use_chromadb and processed > 0:
                        fetch_query = f"""
                        MATCH (n:{label})
                        WHERE n.{id_property} IN $nodes AND n.{embedding_property} IS NOT NULL
                        RETURN n.{id_property} as id, n.{embedding_property} as embedding
                        LIMIT 1000
                        """
                        
                        embeddings_result = self.manager.execute_cypher_query(fetch_query, {"nodes": all_nodes})
                        if embeddings_result:
                            if not isinstance(embeddings_result, list):
                                embeddings_result = [embeddings_result]
                            
                            for item in embeddings_result:
                                try:
                                    node_id = item["id"]
                                    embedding = item["embedding"]
                                    node_data = next((n for n in nodes_needing_embeddings if n["id"] == node_id), None)
                                    
                                    if node_data and embedding:
                                        content_hash = sha256(node_data["content"].encode()).hexdigest()
                                        try:
                                            self.chroma_collection.add(
                                                ids=[content_hash],
                                                documents=[node_data["content"]],
                                                embeddings=[embedding]
                                            )
                                        except Exception as inner_e:
                                            if "Insert of existing embedding ID" not in str(inner_e):
                                                raise
                                except Exception as e:
                                    logger.warning(f"Error storing embedding in ChromaDB for {node_id}: {e}")
                
                except Exception as e:
                    # 6. Embedding Generation Failure Path
                    logger.error(f"[EMBED-FLOW] Failed to generate embeddings: {str(e)}", exc_info=True)
                    results["error"] += 1
            
            # Log completion of batch embedding generation
            logger.info(f"[EMBED-FLOW] Completed batch embedding generation: {results}")
            return {"status": "completed", **results, "total": len(all_items)}
        
        except Exception as e:
            # 6. Embedding Generation Failure Path
            logger.error(f"[EMBED-FLOW] Exception in batch_embeddings_for_nodes: {str(e)}", exc_info=True)
            return {"status": "error", "reason": str(e), **results}

    def batch_process_news_embeddings(self, batch_size=NEWS_EMBEDDING_BATCH_SIZE, create_index=True, max_items=None):
        """
        Generate embeddings for News nodes using Neo4j's GenAI integration.
        This is a specialized wrapper around batch_embeddings_for_nodes just for News nodes.
        
        Args:
            batch_size (int): Number of items to process in each batch
            create_index (bool): Whether to create a vector index if it doesn't exist
            max_items (int, optional): Maximum number of items to process
            
        Returns:
            dict: Results of the embedding process
        """
        # For the News node type, we need special content construction from multiple fields
        # So first, we'll get all news records without embeddings using a custom query

        
        # 1. Batch News Processing Path - initialization
        logger.info(f"[EMBED-FLOW] Starting auto embedding generation via batch_process_news_embeddings")
        
        if not ENABLE_NEWS_EMBEDDINGS:
            return {"status": "skipped", "reason": "embeddings disabled", "processed": 0, "error": 0, "cached": 0}
        
        # Log batch parameters at the beginning of actual processing
        logger.info(f"[EMBED-FLOW] Batch process news embeddings started with batch_size={batch_size}, max_items={max_items}")
        
        # Create vector index if needed
        if create_index:
            self._create_news_vector_index()
            
        # Custom query to find news needing embeddings and prepare content
        query = """
        MATCH (n:News)
        WHERE n.embedding IS NULL
        WITH n,
             CASE 
                WHEN n.body IS NOT NULL AND trim(n.body) <> '' 
                THEN n.body
                ELSE CASE 
                    WHEN n.title IS NOT NULL AND n.teaser IS NOT NULL 
                    THEN n.title + ' ' + n.teaser
                    WHEN n.title IS NOT NULL 
                    THEN n.title
                    WHEN n.teaser IS NOT NULL 
                    THEN n.teaser
                    ELSE ''
                END
             END AS content
        WHERE trim(content) <> ''
        RETURN n.id as id, content
        """
        
        if max_items:
            query += f" LIMIT {max_items}"
        
        # Get all news items needing embeddings
        # all_items = self.manager.execute_cypher_query(query, {})
        all_items = self.manager.execute_cypher_query_all(query, {})
        all_items = self._coerce_record(all_items)
        
        # Convert to list if needed and handle empty results
        if all_items and not isinstance(all_items, list):
            all_items = [all_items]
        
        # 4. No Embeddings Needed Path
        if not all_items or len(all_items) == 0:
            logger.info(f"[EMBED-FLOW] No news items found needing embeddings")
            return {"status": "completed", "reason": "no items needed embeddings", "processed": 0, "error": 0, "cached": 0}
        
        # Log the number of items found    
        logger.info(f"[EMBED-FLOW] Found {len(all_items)} news items needing embeddings")
            
        # For each news item, save the content to a temporary property so we can use the generic method
        for item in all_items:
            save_query = """
            MATCH (n:News {id: $id})
            SET n._temp_content = $content
            """
            self.manager.execute_cypher_query(save_query, {"id": item["id"], "content": item["content"]})
        
        # Use the generic method with the temporary property
        logger.info(f"[EMBED-FLOW] Calling batch_embeddings_for_nodes with prepared content")
        results = self.batch_embeddings_for_nodes(
            label="News",
            id_property="id",
            content_property="_temp_content",
            embedding_property="embedding",
            batch_size=batch_size,
            max_items=max_items,
            create_index=False,  # Already created above
            check_chromadb=True
        )
        
        # Clean up the temporary property
        cleanup_query = """
        MATCH (n:News)
        WHERE n._temp_content IS NOT NULL
        REMOVE n._temp_content
        """
        self.manager.execute_cypher_query(cleanup_query, {})
        
        # Log completion with results
        logger.info(f"[EMBED-FLOW] batch_process_news_embeddings completed with results: {results}")
        return results


    def batch_process_qaexchange_embeddings(self, batch_size=QAEXCHANGE_EMBEDDING_BATCH_SIZE, create_index=True, max_items=None):
        """Generate embeddings for QAExchange nodes using existing infrastructure"""
 
        if not ENABLE_QAEXCHANGE_EMBEDDINGS:
            return {"status": "skipped", "reason": "embeddings disabled", "processed": 0, "error": 0, "cached": 0}
        
        logger.info(f"[EMBED-FLOW-QA] Starting QAExchange embedding generation with batch_size={batch_size}, max_items={max_items}")
        
        # Create vector index if needed
        if create_index:
            self._create_qaexchange_vector_index()
            
        # Custom Cypher query to find nodes and extract text from exchanges property
        query = """
        MATCH (q:QAExchange)
        WHERE q.embedding IS NULL AND q.exchanges IS NOT NULL
        RETURN q.id AS id, q.exchanges AS raw_exchanges
        """


        
        if max_items:
            query += f" LIMIT {max_items}"
        
        # Get nodes needing embeddings
        # all_items = self.manager.execute_cypher_query(query, {})
        all_items = self.manager.execute_cypher_query_all(query, {})
        all_items = self._coerce_record(all_items)
        # Handle empty results
        if all_items and not isinstance(all_items, list):
            all_items = [all_items]
        
        if not all_items or len(all_items) == 0:
            logger.info("[EMBED-FLOW-QA] No QAExchange nodes found needing embeddings initially.")
            return {"status": "completed", "reason": "no items needed embeddings", "processed": 0, "error": 0, "cached": 0}
        
        logger.info(f"[EMBED-FLOW-QA] Found {len(all_items)} QAExchange nodes potentially needing embeddings.")
        
        # Store content in temporary property
        nodes_with_temp_content_set = 0
        skipped_empty_content = 0
        logger.info(f"[EMBED-FLOW-QA] Starting to set _temp_content for {len(all_items)} nodes...")
        for item in all_items:
            try:
                exchanges = json.loads(item.get("raw_exchanges", "[]"))
                logger.debug(f"[EMBED-FLOW-QA] Exchanges for node {item.get('id')}: types={[type(entry).__name__ for entry in exchanges[:5]]}...")
            except Exception as e:
                logger.warning(f"Failed to parse exchanges for {item.get('id')}: {e}")
                exchanges = []

            # Count different types of entries for logging
            dict_entries = sum(1 for entry in exchanges if isinstance(entry, dict))
            str_entries = sum(1 for entry in exchanges if isinstance(entry, str))
            other_entries = len(exchanges) - dict_entries - str_entries
            
            logger.info(f"[EMBED-FLOW-QA] Node {item.get('id')} has {len(exchanges)} entries: {dict_entries} dicts, {str_entries} strings, {other_entries} other types")
            
            # Extract text from exchanges based on role
            content = " ".join(
                entry.get("text", "") if isinstance(entry, dict) and entry.get("role") in {"question", "answer"}
                else entry if isinstance(entry, str)
                else ""
                for entry in exchanges
            ).strip()
            
            # Use proper token counting and truncation
            content = truncate_for_embeddings(content, OPENAI_EMBEDDING_MODEL)
            
            if not content:
                # logger.debug(f"[EMBED-FLOW-QA] Skipping node {item.get('id')} due to empty content")
                skipped_empty_content += 1
                continue  # Skip empty ones

            save_query = """
            MATCH (q:QAExchange {id: $id})
            SET q._temp_content = $content
            RETURN count(q) as updated_count
            """
            try:
                # Add result check
                result = self.manager.execute_cypher_query(save_query, {"id": item["id"], "content": content})
                if result and result.get('updated_count', 0) > 0:
                    nodes_with_temp_content_set += 1
                else:
                    logger.warning(f"[EMBED-FLOW-QA] Failed to set _temp_content for node {item.get('id')}")
            except Exception as e_set:
                logger.error(f"[EMBED-FLOW-QA] Error setting _temp_content for node {item.get('id')}: {e_set}")

        logger.info(f"[EMBED-FLOW-QA] Finished setting _temp_content. Set on {nodes_with_temp_content_set} nodes. Skipped {skipped_empty_content} due to empty content.")
        
        # Use generic batch_embeddings_for_nodes with the temporary property
        logger.info(f"[EMBED-FLOW-QA] Calling batch_embeddings_for_nodes for QAExchange using _temp_content.")
        results = self.batch_embeddings_for_nodes(
            label="QAExchange",
            id_property="id",
            content_property="_temp_content",
            embedding_property="embedding",
            batch_size=batch_size,
            max_items=max_items,
            create_index=False,
            check_chromadb=True
        )
        
        logger.info(f"[EMBED-FLOW-QA] Returned from batch_embeddings_for_nodes. Result: {results}")

        # Clean up temporary property
        logger.info(f"[EMBED-FLOW-QA] Cleaning up _temp_content property for QAExchange nodes.")
        cleanup_query = """
        MATCH (q:QAExchange)
        WHERE q._temp_content IS NOT NULL
        REMOVE q._temp_content
        RETURN count(q) as cleaned_count
        """
        try:
            cleanup_result = self.manager.execute_cypher_query(cleanup_query, {})
            logger.info(f"[EMBED-FLOW-QA] Cleaned up _temp_content for {cleanup_result.get('cleaned_count', 'unknown')} nodes.")
        except Exception as e_clean:
             logger.error(f"[EMBED-FLOW-QA] Error cleaning up _temp_content: {e_clean}", exc_info=True)

        logger.info(f"[EMBED-FLOW-QA] QAExchange embedding processing completed with final results: {results}")
        return results


    def _create_news_embedding(self, news_id):
        """Generate embedding for a single news item using Neo4j's GenAI function"""
        if not self.manager and not self.connect():
            return False
            
        try:
            if not OPENAI_API_KEY:
                return False
            
            logger.info(f"[EMBED-FLOW] Creating single news embedding for news_id={news_id}")
            
            # First, get the content for this news item
            content_query = """
            MATCH (n:News {id: $news_id})
            WHERE n.embedding IS NULL 
            WITH n, 
                 CASE 
                    WHEN n.body IS NOT NULL AND trim(n.body) <> '' 
                    THEN n.body
                    ELSE CASE 
                        WHEN n.title IS NOT NULL AND n.teaser IS NOT NULL 
                        THEN n.title + ' ' + n.teaser
                        WHEN n.title IS NOT NULL 
                        THEN n.title
                        WHEN n.teaser IS NOT NULL 
                        THEN n.teaser
                        ELSE ''
                    END
                 END AS content
            WHERE trim(content) <> ''
            RETURN n.id as id, content
            """
            
            result = self.manager.execute_cypher_query(content_query, {"news_id": news_id})
            result = self._coerce_record(result)
            
            if not result or not result.get("content"):
                return False
                
            content = result.get("content")
            
            # Truncate text to token limit using tiktoken
            content = truncate_for_embeddings(content, OPENAI_EMBEDDING_MODEL)
            
            embedding = None
            
            # Check if we should try to get embedding from ChromaDB first
            if USE_CHROMADB_CACHING and self.chroma_collection is not None:
                try:
                    content_hash = sha256(content.encode()).hexdigest()
                    logger.debug(f"Checking ChromaDB for news {news_id} with content hash {content_hash}")
                    # Always include embeddings parameter
                    chroma_result = self.chroma_collection.get(ids=[content_hash], include=['embeddings'])
                    
                    # Simple, robust check for valid embeddings
                    if (chroma_result and 
                        'ids' in chroma_result and 
                        len(chroma_result['ids']) > 0 and
                        'embeddings' in chroma_result and 
                        chroma_result['embeddings'] is not None and 
                        len(chroma_result['embeddings']) > 0):
                        
                        # We found an existing embedding in ChromaDB
                        embedding = chroma_result['embeddings'][0]
                        logger.info(f"Retrieved embedding from ChromaDB for news {news_id}")
                        
                        # Store the cached embedding in Neo4j
                        store_query = """
                        MATCH (n:News {id: $news_id})
                        WHERE n.embedding IS NULL 
                        CALL db.create.setNodeVectorProperty(n, "embedding", $embedding)
                        RETURN count(n) AS processed
                        """
                        
                        result = self.manager.execute_cypher_query(store_query, {
                            "news_id": news_id,
                            "embedding": embedding
                        })
                        
                        logger.info(f"[EMBED-FLOW] Successfully generated embedding for news {news_id}")
                        return result and result.get("processed", 0) > 0
                        
                except Exception as e:
                    logger.warning(f"Error checking ChromaDB: {e}")
            
            # If we didn't find an embedding in ChromaDB, generate a new one
            # Use Neo4j's genai.vector.encodeBatch to generate embedding and set it directly
            logger.info(f"[EMBED-FLOW] Executing Neo4j encodeBatch for single news item {news_id}")
            query = """
            MATCH (n:News {id: $news_id})
            WHERE n.embedding IS NULL
            WITH n, $content AS content, $config AS config
            CALL genai.vector.encodeBatch([content], "OpenAI", config) 
            YIELD index, vector
            WITH n, vector
            CALL db.create.setNodeVectorProperty(n, "embedding", vector)
            RETURN count(n) AS processed, vector AS embedding
            """
            
            result = self.manager.execute_cypher_query(query, {
                "news_id": news_id, 
                "content": content,
                "config": {
                    "token": OPENAI_API_KEY,
                    "model": OPENAI_EMBEDDING_MODEL
                }
            })
            
            success = result and result.get("processed", 0) > 0
            
            # Store in ChromaDB for future reuse if successful
            if success and self.chroma_collection is not None and result.get("embedding"):
                try:
                    content_hash = sha256(content.encode()).hexdigest()
                    
                    # Check if this embedding already exists in ChromaDB before adding
                    check_result = self.chroma_collection.get(ids=[content_hash], include=['embeddings'])
                    if (check_result and 
                        'ids' in check_result and 
                        len(check_result['ids']) > 0 and
                        'embeddings' in check_result and 
                        check_result['embeddings'] is not None and 
                        len(check_result['embeddings']) > 0):
                        # Already exists, no need to add again
                        logger.debug(f"Embedding already exists in ChromaDB for {news_id}")
                    else:
                        # Doesn't exist, add it - Use upsert to prevent race condition issues
                        try:
                            self.chroma_collection.add(
                                ids=[content_hash],
                                documents=[content],
                                embeddings=[result["embedding"]]
                            )
                            logger.info(f"Stored new embedding in ChromaDB for news {news_id}")
                        except Exception as inner_e:
                            if "Insert of existing embedding ID" in str(inner_e):
                                logger.debug(f"Embedding already exists in ChromaDB - concurrent insert detected")
                            else:
                                raise inner_e
                except Exception as e:
                    if "Insert of existing embedding ID" in str(e):
                        logger.debug(f"Embedding already exists in ChromaDB")
                    else:
                        logger.warning(f"Failed to store embedding in ChromaDB: {e}")
            
            if success:
                logger.info(f"[EMBED-FLOW] Successfully generated embedding for news {news_id}")
            else:
                logger.error(f"[EMBED-FLOW] Failed to generate embedding for news {news_id}, result: {result}")
                
            return success
        except Exception as e:
            logger.error(f"[EMBED-FLOW] Exception creating single news embedding: {str(e)}", exc_info=True)
            return False



    
    def _create_qaexchange_embedding(self, qa_id):
        """Generate embedding for a single QAExchange item"""
        if not self.manager and not self.connect():
            return False
            
        try:

            
            if not OPENAI_API_KEY or not ENABLE_QAEXCHANGE_EMBEDDINGS:
                return False
            
            logger.info(f"Creating single QAExchange embedding for qa_id={qa_id}")
            
            # Get the content for this QAExchange item
            content_query = """
            MATCH (q:QAExchange {id: $qa_id})
            WHERE q.embedding IS NULL AND q.exchanges IS NOT NULL
            RETURN q.id AS id, q.exchanges AS raw_exchanges
            """
            
            result = self.manager.execute_cypher_query(content_query, {"qa_id": qa_id})
            result = self._coerce_record(result)
            
            if not result:
                return False
            
            # Parse the exchanges JSON in Python
            try:
                exchanges = json.loads(result.get("raw_exchanges", "[]"))
                logger.debug(f"[EMBED-FLOW-QA] Exchanges for node {result.get('id')}: types={[type(entry).__name__ for entry in exchanges[:5]]}...")
            except Exception as e:
                logger.warning(f"Failed to parse exchanges for {qa_id}: {e}")
                exchanges = []
            
            # Count different types of entries for logging
            dict_entries = sum(1 for entry in exchanges if isinstance(entry, dict))
            str_entries = sum(1 for entry in exchanges if isinstance(entry, str))
            other_entries = len(exchanges) - dict_entries - str_entries
            
            logger.info(f"[EMBED-FLOW-QA] Node {result.get('id')} has {len(exchanges)} entries: {dict_entries} dicts, {str_entries} strings, {other_entries} other types")
            
            # Extract text from exchanges based on role
            content = " ".join(
                entry.get("text", "") if isinstance(entry, dict) and entry.get("role") in {"question", "answer"}
                else entry if isinstance(entry, str)
                else ""
                for entry in exchanges
            ).strip()
            
            # Use proper token counting and truncation
            content = truncate_for_embeddings(content, OPENAI_EMBEDDING_MODEL)
            
            if not content:
                return False
            
            embedding = None
            
            # Check if we should try to get embedding from ChromaDB first
            if USE_CHROMADB_CACHING and self.chroma_collection is not None:
                try:
                    
                    content_hash = sha256(content.encode()).hexdigest()
                    logger.debug(f"Checking ChromaDB for QAExchange {qa_id} with content hash {content_hash}")
                    # Always include embeddings parameter
                    chroma_result = self.chroma_collection.get(ids=[content_hash], include=['embeddings'])
                    
                    # Simple, robust check for valid embeddings
                    if (chroma_result and 
                        'ids' in chroma_result and 
                        len(chroma_result['ids']) > 0 and
                        'embeddings' in chroma_result and 
                        chroma_result['embeddings'] is not None and 
                        len(chroma_result['embeddings']) > 0):
                        
                        # We found an existing embedding in ChromaDB
                        embedding = chroma_result['embeddings'][0]
                        logger.info(f"Retrieved embedding from ChromaDB for QAExchange {qa_id}")
                        
                        # Store the cached embedding in Neo4j
                        store_query = """
                        MATCH (q:QAExchange {id: $qa_id})
                        WHERE q.embedding IS NULL 
                        CALL db.create.setNodeVectorProperty(q, "embedding", $embedding)
                        RETURN count(q) AS processed
                        """
                        
                        result = self.manager.execute_cypher_query(store_query, {
                            "qa_id": qa_id,
                            "embedding": embedding
                        })
                        
                        logger.info(f"Successfully applied cached embedding for QAExchange {qa_id}")
                        return result and result.get("processed", 0) > 0
                        
                except Exception as e:
                    logger.warning(f"Error checking ChromaDB: {e}")
            
            # If we didn't find an embedding in ChromaDB, generate a new one
            # Use Neo4j's genai.vector.encodeBatch to generate embedding and set it directly
            logger.info(f"Executing Neo4j encodeBatch for single QAExchange item {qa_id}")
            query = """
            MATCH (q:QAExchange {id: $qa_id})
            WHERE q.embedding IS NULL
            WITH q, $content AS content, $config AS config
            CALL genai.vector.encodeBatch([content], "OpenAI", config) 
            YIELD index, vector
            WITH q, vector
            CALL db.create.setNodeVectorProperty(q, "embedding", vector)
            RETURN count(q) AS processed, vector AS embedding
            """
            
            result = self.manager.execute_cypher_query(query, {
                "qa_id": qa_id, 
                "content": content,
                "config": {
                    "token": OPENAI_API_KEY,
                    "model": OPENAI_EMBEDDING_MODEL
                }
            })
            
            success = result and result.get("processed", 0) > 0
            
            # Store in ChromaDB for future reuse if successful
            if success and self.chroma_collection is not None and result.get("embedding"):
                try:
                    content_hash = sha256(content.encode()).hexdigest()
                    
                    # Check if this embedding already exists in ChromaDB before adding
                    check_result = self.chroma_collection.get(ids=[content_hash], include=['embeddings'])
                    if (check_result and 
                        'ids' in check_result and 
                        len(check_result['ids']) > 0 and
                        'embeddings' in check_result and 
                        check_result['embeddings'] is not None and 
                        len(check_result['embeddings']) > 0):
                        # Already exists, no need to add again
                        logger.debug(f"Embedding already exists in ChromaDB for {qa_id}")
                    else:
                        # Doesn't exist, add it - Use upsert to prevent race condition issues
                        try:
                            self.chroma_collection.add(
                                ids=[content_hash],
                                documents=[content],
                                embeddings=[result["embedding"]]
                            )
                            logger.info(f"Stored new embedding in ChromaDB for QAExchange {qa_id}")
                        except Exception as inner_e:
                            if "Insert of existing embedding ID" in str(inner_e):
                                logger.debug(f"Embedding already exists in ChromaDB - concurrent insert detected")
                            else:
                                raise inner_e
                except Exception as e:
                    if "Insert of existing embedding ID" in str(e):
                        logger.debug(f"Embedding already exists in ChromaDB")
                    else:
                        logger.warning(f"Failed to store embedding in ChromaDB: {e}")
            
            if success:
                logger.info(f"Successfully generated embedding for QAExchange {qa_id}")
            else:
                logger.warning(f"Failed to generate embedding for QAExchange {qa_id}, result: {result}")
                
            return success
        except Exception as e:
            logger.error(f"Exception in _create_qaexchange_embedding: {str(e)}", exc_info=True)
            return False
    



    def vector_similarity_search(self, query_text, node_label="News", embedding_property="embedding", 
                             id_property="id", limit=10, min_score=0.7, return_properties=None):
        """
        Search for nodes using vector similarity to a query text
        
        Args:
            query_text (str): The text query to search for
            node_label (str): Node label to search in (e.g., 'News', 'Report')
            embedding_property (str): Property containing embeddings
            id_property (str): Property to identify nodes
            limit (int): Maximum number of results to return
            min_score (float): Minimum similarity score (0.0-1.0)
            return_properties (list): List of properties to return for each node
            
        Returns:
            list: List of nodes with similarity scores
        """

        
        try:
            if not self.manager and not self.connect():
                logger.error("Cannot connect to Neo4j")
                return []
                
            if not OPENAI_API_KEY:
                logger.error("Missing OpenAI API key")
                return []
                
            # Truncate query to token limit
            query_text = truncate_for_embeddings(query_text, OPENAI_EMBEDDING_MODEL)
            
            # Generate embedding for query text
            embedding_query = """
            WITH $query_text AS text, $config AS config
            CALL genai.vector.encodeBatch([text], 'OpenAI', config) 
            YIELD index, vector
            RETURN vector AS query_embedding
            """
            
            result = self.manager.execute_cypher_query(embedding_query, {
                "query_text": query_text,
                "config": {"token": OPENAI_API_KEY, "model": OPENAI_EMBEDDING_MODEL}
            })
            
            if not result or not result.get("query_embedding"):
                # 8. Vector Similarity Search Failure Path
                logger.error("[EMBED-FLOW] Failed to generate embedding for search query")
                return []
            
            query_embedding = result["query_embedding"]
            
            # Build properties to return
            if not return_properties:
                return_properties = [id_property]
            
            return_clause = ", ".join([f"node.{prop} AS {prop}" for prop in return_properties])
            return_clause = f"node.{id_property} AS id, {return_clause}, score"
            
            # 7. Vector Similarity Search Path
            logger.info(f"[EMBED-FLOW] Successfully encoded search query, searching for {limit} results with min_score={min_score}")
            
            # Perform vector similarity search
            search_query = f"""
            WITH $query_embedding AS query_embedding
            MATCH (node:{node_label})
            WHERE node.{embedding_property} IS NOT NULL
            WITH node, 
                 vector.similarity.cosine(node.{embedding_property}, query_embedding) AS score
            WHERE score >= $min_score  
            RETURN {return_clause}
            ORDER BY score DESC
            LIMIT $limit
            """

            results = self.manager.execute_cypher_query_all(search_query, {
                "query_embedding": query_embedding,
                "min_score": min_score,
                "limit": limit
            })


            # Should be faster than above but check if it works: Perform vector similarity search
            # search_query = f"""
            # CALL db.index.vector.queryNodes($index_name, $query_embedding, $limit)
            # YIELD node, score
            # WHERE score >= $min_score
            # RETURN node.{id_property} AS id, {", ".join([f"node.{prop} AS {prop}" for prop in return_properties])}, score
            # ORDER BY score DESC
            # """

            # from utils.feature_flags import NEWS_VECTOR_INDEX_NAME

            # results = self.manager.execute_cypher_query(search_query, {
            #     "index_name": NEWS_VECTOR_INDEX_NAME,
            #     "query_embedding": query_embedding,
            #     "min_score": min_score,
            #     "limit": limit
            # })



            # Ensure results is a list
            if results and not isinstance(results, list):
                results = [results]
            
            # 7. Vector Similarity Search Path - results
            logger.info(f"[EMBED-FLOW] Vector similarity search returned {len(results) if results else 0} results")
            return results or []
            
        except Exception as e:
            logger.error(f"Error in vector similarity search: {e}", exc_info=True)
            return []


    def check_chromadb_status(self):
        """
        Check the status of ChromaDB configuration and data persistence
        
        Returns:
            dict: Status information about ChromaDB configuration
        """
        if not hasattr(self, 'chroma_client') or self.chroma_client is None:
            return {
                "initialized": False,
                "reason": "ChromaDB client not initialized"
            }
            

        
        # Get absolute path
        abs_persist_dir = os.path.abspath(CHROMADB_PERSIST_DIRECTORY)
        
        # Check directory existence and permissions
        dir_exists = os.path.exists(abs_persist_dir)
        dir_is_writable = os.access(abs_persist_dir, os.W_OK) if dir_exists else False
        
        # Check directory contents for debugging
        dir_contents = os.listdir(abs_persist_dir) if dir_exists else []
        
        # Get more detailed listing with ls -la if directory exists but appears empty
        detailed_listing = None
        if dir_exists and not dir_contents:
            try:
                import subprocess
                result = subprocess.run(['ls', '-la', abs_persist_dir], capture_output=True, text=True)
                detailed_listing = result.stdout
            except Exception as e:
                detailed_listing = f"Error getting detailed listing: {e}"
        
        # Get ChromaDB version for debugging
        chromadb_version = None
        try:
            import pkg_resources
            chromadb_version = pkg_resources.get_distribution("chromadb").version
        except Exception:
            chromadb_version = "unknown"
        
        # Check for collections in database
        collections = []
        collection_count = {}
        try:
            collections = self.chroma_client.list_collections()
            collection_names = [c.name for c in collections]
            
            # Get item count in each collection
            for collection in collections:
                try:
                    count = collection.count()
                    collection_count[collection.name] = count
                except Exception as e:
                    collection_count[collection.name] = f"Error: {str(e)}"
        except Exception as e:
            collections = [f"Error listing collections: {e}"]
        
        # Check if we have a news collection specifically
        news_collection_exists = False
        news_collection_count = 0
        
        # if hasattr(self, 'chroma_collection') and self.chroma_collection is not None:
        if self.chroma_collection is not None:
            news_collection_exists = True
            try:
                news_collection_count = self.chroma_collection.count()
            except Exception as e:
                news_collection_count = f"Error: {str(e)}"
        
        # Determine client type - PersistentClient or regular Client with settings
        client_type = type(self.chroma_client).__name__
        
        # Check persistence implementation
        persistence_impl = None
        if client_type == "Client" and hasattr(self.chroma_client, "_settings"):
            try:
                settings = self.chroma_client._settings
                
                if hasattr(settings, "chroma_db_impl"):
                    persistence_impl = settings.chroma_db_impl
                elif hasattr(settings, "values") and "chroma_db_impl" in settings.values:
                    persistence_impl = settings.values["chroma_db_impl"]
                else:
                    persistence_impl = "unknown"
            except Exception as e:
                persistence_impl = f"Error checking implementation: {e}"
                
        return {
            "initialized": True,
            "chromadb_version": chromadb_version,
            "client_type": client_type,
            "persistence_impl": persistence_impl,
            "persist_directory": {
                "path": abs_persist_dir,
                "exists": dir_exists,
                "writable": dir_is_writable,
                "contents": dir_contents[:10] if len(dir_contents) > 10 else dir_contents,
                "total_files": len(dir_contents),
                "detailed_listing": detailed_listing
            },
            "collections": {
                "names": [c.name for c in collections] if isinstance(collections, list) else collections,
                "count": len(collections) if isinstance(collections, list) else 0,
                "items_per_collection": collection_count
            },
            "news_collection": {
                "exists": news_collection_exists,
                "count": news_collection_count
            }
        }

