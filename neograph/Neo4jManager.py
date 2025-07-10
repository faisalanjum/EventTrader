from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union, Tuple, Type, TYPE_CHECKING
from collections import defaultdict
from neo4j import GraphDatabase, Driver
import time
import pandas as pd
import time
import logging
import json
import neo4j.exceptions # Import exceptions
import tenacity # Import tenacity
import random # Import random for jitter
# Split imports: TYPE_CHECKING for type hints, direct imports for runtime needs
if TYPE_CHECKING:
    from XBRL.xbrl_core import Neo4jNode

# Import needed classes and enums for runtime
from XBRL.xbrl_core import NodeType, RelationType, PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS
from XBRL.xbrl_reporting import Fact

from XBRL.utils import resolve_primary_fact_relationships, clean_number

# Import feature flags for configuration
from config.feature_flags import (
    NEO4J_MAX_CONNECTION_LIFETIME, 
    NEO4J_KEEP_ALIVE, 
    NEO4J_MAX_CONNECTION_POOL_SIZE,
    ENABLE_BULK_NODE_MERGE_XBRL
)

logger = logging.getLogger(__name__)

# Custom retry condition that checks for defunct connections
def is_defunct_connection_error(exception):
    """Check if the exception indicates a defunct connection"""
    error_str = str(exception).lower()
    return any(phrase in error_str for phrase in ["defunct", "failed to read", "closed connection"])

def retry_if_defunct_connection(exception):
    """Retry if the exception indicates a defunct connection"""
    return is_defunct_connection_error(exception)

def before_retry_refresh_connection(retry_state):
    """Callback to refresh connection before retry if it's a defunct connection error"""
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if is_defunct_connection_error(exception):
            logger.info("Detected defunct connection in retry, triggering connection refresh")
            # Get the singleton manager and refresh it
            from .Neo4jConnection import get_manager
            try:
                manager = get_manager()
                if manager:
                    manager.ensure_healthy_connection()
            except Exception as e:
                logger.error(f"Failed to refresh connection in retry callback: {e}")

# Define retry conditions using tenacity
retry_on_neo4j_transient_error = tenacity.retry(
    stop=tenacity.stop_after_attempt(3), # Retry 2 times after initial failure (total 3 attempts)
    wait=tenacity.wait_exponential(multiplier=1, min=0.5, max=3) + tenacity.wait_random(0, 0.5), # Exponential backoff with jitter
    retry=(
        tenacity.retry_if_exception_type(neo4j.exceptions.ServiceUnavailable) |
        tenacity.retry_if_exception_type(neo4j.exceptions.SessionExpired) |
        tenacity.retry_if_exception_type(neo4j.exceptions.TransientError) |
        tenacity.retry_if_exception_type(OSError) | # From original logs
        tenacity.retry_if_exception_type(TimeoutError) | # From original logs
        tenacity.retry_if_exception(retry_if_defunct_connection) # Handle defunct connections
    ),
    before=before_retry_refresh_connection, # Refresh connection before retry for defunct connections
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), # Log before retrying
    reraise=True # IMPORTANT: Re-raise the exception if all retries fail
)

# region : Neo4j Manager ########################

@dataclass
class Neo4jManager:
    uri: str
    username: str
    password: str
    driver: Driver = field(init=False)

    PRESENTATION_CONSTRAINT_NAME = "constraint_presentation_edge_unique"
    CALCULATION_CONSTRAINT_NAME = "constraint_calculation_edge_unique"

    # --- batching configuration (relationships) ---------------------------
    # Keep transactions comfortably below Neo4j's default 60-second timeout
    # while still being large enough to minimise commit overhead.
    # Raising it to 1000 halves the chunk count; lowering to 250 doubles safety margin.
    REL_BATCH_SIZE: int = 1000  # tuned via production logs; change in one place only

    # Only change this single method to use a special case with retry_error_callback
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=0.5, min=0.2, max=2),
        retry=(
            tenacity.retry_if_exception_type(neo4j.exceptions.ServiceUnavailable) |
            tenacity.retry_if_exception_type(neo4j.exceptions.SessionExpired) |
            tenacity.retry_if_exception_type(neo4j.exceptions.TransientError) |
            tenacity.retry_if_exception_type(OSError) |
            tenacity.retry_if_exception_type(TimeoutError)
        ),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        retry_error_callback=lambda _: False  # Return False when retries are exhausted
    )
    def test_connection(self) -> bool:
        """Test Neo4j connection"""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def __post_init__(self):
        try:
            # Configure driver settings for better handling of long-running tasks/concurrency
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password),
                max_connection_lifetime=NEO4J_MAX_CONNECTION_LIFETIME,
                keep_alive=NEO4J_KEEP_ALIVE,
                max_connection_pool_size=NEO4J_MAX_CONNECTION_POOL_SIZE
            )
            # test_connection now has implicit retry. It will raise if retries fail.
            if not self.test_connection():
                # This case might be less likely now as test_connection reraises
                raise ConnectionError("test_connection returned False unexpectedly")
        except Exception as e:
            # Catch exceptions reraised by test_connection or driver init errors
            raise ConnectionError(f"Neo4j initialization failed: {e}")
    
    def close(self):
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def ensure_healthy_connection(self):
        """Check connection health and refresh if needed"""
        try:
            # Test the connection with a simple query
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "defunct" in error_str or "closed" in error_str or "failed to read" in error_str:
                logger.warning(f"Detected unhealthy connection: {e}")
                logger.info("Attempting to refresh Neo4j driver...")
                try:
                    # Close existing driver
                    self.close()
                    # Reinitialize the driver
                    self.__post_init__()
                    logger.info("Successfully refreshed Neo4j driver")
                    return True
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh Neo4j driver: {refresh_error}")
                    return False
            else:
                # Other types of errors, don't attempt refresh
                logger.error(f"Neo4j connection error (not refreshing): {e}")
                return False
                        
    @retry_on_neo4j_transient_error
    def clear_db(self):
        """Development only: Clear database and verify it's empty"""
        try:
            with self.driver.session() as session:
                # Get and drop all constraints
                constraints = session.run("SHOW CONSTRAINTS").data()
                for constraint in constraints:
                    session.run(f"DROP CONSTRAINT {constraint['name']} IF EXISTS")
                
                # Get and drop all indexes
                indexes = session.run("SHOW INDEXES").data()
                for index in indexes:
                    session.run(f"DROP INDEX {index['name']} IF EXISTS")
                
                # Delete all nodes and relationships
                session.run("MATCH (n) DETACH DELETE n")
                
                # Verify database is empty
                result = session.run("MATCH (n) RETURN count(n) as count").single()
                node_count = result["count"]
                
                if node_count > 0:
                    # Log error instead of raising immediately if possible, but raise is safer for dev
                    logger.error(f"Database not fully cleared. {node_count} nodes remaining.")
                    raise RuntimeError(f"Database not fully cleared. {node_count} nodes remaining.")
                    
                logger.info("Database cleared successfully")

        except Exception as e:
            # Log the exception before raising
            logger.error(f"Failed to clear database: {e}", exc_info=True)
            raise RuntimeError(f"Failed to clear database: {e}")

    @retry_on_neo4j_transient_error
    def create_indexes(self):
        """Create indexes and constraints for both nodes and relationships"""
        try:
            # Use a retry pattern specifically for schema operations
            max_attempts = 3
            backoff_time = 0.5
            
            for attempt in range(max_attempts):
                try:
                    with self.driver.session() as session:
                        # Get existing constraints
                        existing_constraints = {
                            constraint['name']: constraint['labelsOrTypes'][0]
                            for constraint in session.run("SHOW CONSTRAINTS").data()
                        }
                        
                        # Create node constraints
                        for node_type in NodeType:
                            constraint_name = f"constraint_{node_type.value.lower()}_id_unique"
                            if constraint_name not in existing_constraints:
                                session.run(f"""
                                CREATE CONSTRAINT {constraint_name}
                                FOR (n:`{node_type.value}`)
                                REQUIRE n.id IS UNIQUE
                                """)
                        
                        # Presentation Edge constraint
                        rel_constraint_name = "constraint_presentation_edge_unique"
                        if rel_constraint_name not in existing_constraints:
                            props = ", ".join(f"r.{prop}" for prop in PRESENTATION_EDGE_UNIQUE_PROPS)
                            session.run(f"""
                            CREATE CONSTRAINT {rel_constraint_name} IF NOT EXISTS
                            FOR ()-[r:PRESENTATION_EDGE]-()
                            REQUIRE ({props}) IS UNIQUE
                            """)
                            logger.info(f"Created constraint for PRESENTATION_EDGE relationships")
                            
                        # Calculation Edge constraint
                        rel_constraint_name = "constraint_calculation_edge_unique"
                        if rel_constraint_name not in existing_constraints:
                            props = ", ".join(f"r.{prop}" for prop in CALCULATION_EDGE_UNIQUE_PROPS)
                            session.run(f"""
                            CREATE CONSTRAINT {rel_constraint_name} IF NOT EXISTS
                            FOR ()-[r:CALCULATION_EDGE]-()
                            REQUIRE ({props}) IS UNIQUE
                            """)
                            logger.info(f"Created constraint for CALCULATION_EDGE relationships")
                            
                        # HAS_CONCEPT relationship key constraint
                        rel_constraint_name = "hasConcept_key"
                        if rel_constraint_name not in existing_constraints:
                            session.run(f"""
                            CREATE CONSTRAINT {rel_constraint_name} IF NOT EXISTS
                            FOR ()-[r:HAS_CONCEPT]-()
                            REQUIRE r.key IS UNIQUE
                            """)
                            logger.info(f"Created key constraint for HAS_CONCEPT relationships")
                            
                        # HAS_UNIT relationship key constraint  
                        rel_constraint_name = "hasUnit_key"
                        if rel_constraint_name not in existing_constraints:
                            session.run(f"""
                            CREATE CONSTRAINT {rel_constraint_name} IF NOT EXISTS
                            FOR ()-[r:HAS_UNIT]-()
                            REQUIRE r.key IS UNIQUE
                            """)
                            logger.info(f"Created key constraint for HAS_UNIT relationships")
                            
                        # HAS_PERIOD relationship key constraint
                        rel_constraint_name = "hasPeriod_key"
                        if rel_constraint_name not in existing_constraints:
                            session.run(f"""
                            CREATE CONSTRAINT {rel_constraint_name} IF NOT EXISTS
                            FOR ()-[r:HAS_PERIOD]-()
                            REQUIRE r.key IS UNIQUE
                            """)
                            logger.info(f"Created key constraint for HAS_PERIOD relationships")
                        
                        # Create lookup index for id property across all nodes
                        # This speeds up queries that search by id without knowing the label
                        existing_indexes = {
                            index['name'] for index in session.run("SHOW INDEXES").data()
                        }
                        lookup_index_name = "id_lookup_index"
                        if lookup_index_name not in existing_indexes:
                            session.run("""
                            CREATE LOOKUP INDEX id_lookup_index IF NOT EXISTS
                            FOR (n) ON (n.id)
                            """)
                            logger.info(f"Created lookup index for id property across all nodes")
                    
                    # If we get here without exception, we're done
                    break
                    
                except Exception as e:
                    error_message = str(e)
                    
                    # Don't retry if constraint already exists - this is normal in concurrent environment
                    if "EquivalentSchemaRuleAlreadyExists" in error_message:
                        logger.info("Some constraints already exist, continuing...")
                        break
                        
                    # Only retry on specific transient errors
                    if "TransientError" in error_message or "DeadlockDetected" in error_message:
                        if attempt < max_attempts - 1:
                            sleep_time = backoff_time * (2 ** attempt)
                            logger.warning(f"Transient error creating indexes, retrying in {sleep_time:.2f} seconds...")
                            time.sleep(sleep_time)
                            continue
                    
                    # Otherwise re-raise the exception
                    raise

        except Exception as e:
            logger.error(f"Failed to create indexes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create indexes: {e}")



    # def create_indexes(self):
    #     """Create indexes and constraints for both nodes and relationships"""
    #     try:
    #         with self.driver.session() as session:
    #             # Get existing constraints
    #             existing_constraints = {
    #                 constraint['name']: constraint['labelsOrTypes'][0]
    #                 for constraint in session.run("SHOW CONSTRAINTS").data()
    #             }
                
    #             # Create node constraints
    #             for node_type in NodeType:
    #                 constraint_name = f"constraint_{node_type.value.lower()}_id_unique"
    #                 if constraint_name not in existing_constraints:
    #                     session.run(f"""
    #                     CREATE CONSTRAINT {constraint_name}
    #                     FOR (n:`{node_type.value}`)
    #                     REQUIRE n.id IS UNIQUE
    #                     """)
                
    #             # Create relationship constraints
    #             rel_constraint_name = "constraint_presentation_edge_unique"
    #             if rel_constraint_name not in existing_constraints:
    #                 session.run("""
    #                 CREATE CONSTRAINT constraint_presentation_edge_unique
    #                 FOR ()-[r:PRESENTATION_EDGE]-()
    #                 REQUIRE (r.source_id, r.target_id, r.network_id) IS UNIQUE
    #                 """)
    #                 print(f"Created constraint for PRESENTATION_EDGE relationships")
                    
    #     except Exception as e:
    #         raise RuntimeError(f"Failed to create indexes: {e}")


    @retry_on_neo4j_transient_error            
    def merge_nodes_bulk(self, nodes: List['Neo4jNode'], batch_size:int = 5000) -> None:
        """Merge nodes using a single UNWIND per label (much faster). Only used by XBRL path."""
        if not nodes:
            return

        # Helper functions reused from original merge_nodes
        def format_value(v):
            if isinstance(v, (int, float)):
                return f"{v:,.3f}".rstrip('0').rstrip('.') if isinstance(v, float) else f"{v:,}"
            return v

        def sanitize_value(v):
            if isinstance(v, list):
                return [item for item in v if item is not None]
            if isinstance(v, dict):
                return {k: val for k, val in v.items() if val is not None}
            return v

        # Group rows by node label so we can keep one MERGE statement per label.
        rows_by_label: Dict[str, list] = defaultdict(list)

        skipped = 0
        for node in nodes:
            if node.id is None:
                skipped += 1
                continue

            props = {}
            for k, v in node.properties.items():
                if k == 'id':
                    continue
                if v is None:
                    props[k] = "null"
                else:
                    props[k] = format_value(sanitize_value(v))

            rows_by_label[node.node_type.value].append({"id": node.id, "props": props})

        try:
            with self.driver.session() as session:
                for label, rows in rows_by_label.items():
                    for i in range(0, len(rows), batch_size):
                        chunk = rows[i:i+batch_size]
                        def merge_tx(tx, _rows=chunk, _label=label):
                            tx.run(
                                f"""
                                UNWIND $rows AS row
                                MERGE (n:`{_label}` {{id: row.id}})
                                SET   n += row.props
                                """, {"rows": _rows})
                        session.execute_write(merge_tx)

            logger.info(f"Bulk-merged {len(nodes)-skipped} nodes across {len(rows_by_label)} labels (skipped {skipped}).")
        except neo4j.exceptions.TransientError as e:
            # Check if it's a deadlock error
            if "DeadlockDetected" in str(e):
                logger.warning(f"Deadlock detected in bulk merge, falling back to single-node transactions: {e}")
                # Fall back to regular merge_nodes which processes one-by-one
                # Temporarily disable bulk mode to ensure we use single transactions
                prev_bulk = getattr(self, "_use_bulk", False)
                self._use_bulk = False
                try:
                    self.merge_nodes(nodes, batch_size=batch_size)
                finally:
                    self._use_bulk = prev_bulk
                return
            else:
                # For other transient errors, let the retry decorator handle it
                raise
        except Exception as e:
            logger.error(f"Failed bulk merge: {e}", exc_info=True)
            raise RuntimeError(f"Failed bulk merge: {e}")


    # ------------------------------------------------------------------
    # Original merge_nodes now delegates based on feature flag
    @retry_on_neo4j_transient_error            
    def merge_nodes(self, nodes: List['Neo4jNode'], batch_size: int = 2000) -> None:
        """Merge nodes into Neo4j database with batching"""
        from config.feature_flags import ENABLE_BULK_NODE_MERGE_XBRL
        # If flag on AND caller explicitly wants speed they should call bulk directly.
        # We keep original behaviour here for safety.

        if ENABLE_BULK_NODE_MERGE_XBRL and getattr(self, "_use_bulk", False):
            return self.merge_nodes_bulk(nodes, batch_size=batch_size)

        if not nodes:
            return

        try:
            with self.driver.session() as session:
                skipped_nodes = []
                
                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i + batch_size]
                    
                    for node in batch:
                        # Skip nodes with null IDs
                        if node.id is None: 
                            skipped_nodes.append(node)
                            continue

                        # Format numeric value property
                        def format_value(v):
                            if isinstance(v, (int, float)):
                                return f"{v:,.3f}".rstrip('0').rstrip('.') if isinstance(v, float) else f"{v:,}"
                            return v
                        
                        # Sanitize collections to remove null values
                        def sanitize_value(v):
                            # Handle lists - remove any None/null values
                            if isinstance(v, list):
                                return [item for item in v if item is not None]
                            # Handle dictionaries - remove entries with None/null values
                            elif isinstance(v, dict):
                                return {k: val for k, val in v.items() if val is not None}
                            # Return the value as is for non-collections
                            return v

                        # Exclude id from properties and sanitize collections
                        properties = {}
                        for k, v in node.properties.items():
                            if k != 'id':

                                if v is None:
                                    properties[k] = "null"
                                else:
                                    # First sanitize collections, then format values
                                    sanitized_value = sanitize_value(v)
                                    properties[k] = format_value(sanitized_value)

                                # This did not help with solving issues like this so reverting to above: "neograph.mixins.reconcile - ERROR - Error reconciling date nodes: Expected structure, found marker A3"
                                # New logic: Pass Python None directly
                                # Sanitize first (removes None from lists/dicts), then format
                                # sanitized_value = sanitize_value(v)
                                # # Pass Python None directly if value is None after potential sanitization
                                # properties[k] = None if sanitized_value is None else format_value(sanitized_value)
                        
                        query = f"""
                        MERGE (n:{node.node_type.value} {{id: $id}})
                        ON CREATE SET n += $properties
                        ON MATCH SET n += $properties
                        """
                        
                        # Use execute_write for automatic retry on deadlocks
                        def merge_node_tx(tx):
                            return tx.run(query, {"id": node.id, "properties": properties})
                        
                        session.execute_write(merge_node_tx)
                
                if skipped_nodes:
                    logger.warning(f"Warning: Skipped {len(skipped_nodes)} nodes with null IDs")
                    # Log only the first few skipped nodes at DEBUG level to avoid clutter
                    for node in skipped_nodes[:3]:
                        logger.debug(f"Skipped Node type: {node.node_type.value}, Properties: {node.properties}")
                        
        except Exception as e:
            logger.error(f"Failed to merge nodes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to merge nodes: {e}")

    def _filter_duplicate_facts(self, nodes: List[Neo4jNode]) -> List[Neo4jNode]:
        """Filter out duplicate facts, keeping only primary facts"""
        if nodes and isinstance(nodes[0], Fact):
            return [node for node in nodes if node.is_primary]
        return nodes

    @retry_on_neo4j_transient_error
    def _export_nodes(self, collections: List[Union['Neo4jNode', List['Neo4jNode']]], testing: bool = False, *, bulk: bool = False):
        """Export specified collections of nodes to Neo4j"""
        try:
            # Use bulk flag to hint at merge strategy for this call only
            prev_setting = getattr(self, "_use_bulk", False)
            self._use_bulk = bulk
            if testing:
                self.clear_db()
            
            # Check if indexes exist before creating them
            with self.driver.session() as session:
                # Use a transaction to ensure atomicity
                indexes_needed = False
                with session.begin_transaction() as tx:
                    # Get existing constraints (just need names)
                    existing_constraints = {
                        constraint['name'] 
                        for constraint in tx.run("SHOW CONSTRAINTS").data()
                    }
                    
                    # Check if we need to create any indexes
                    for node_type in NodeType:
                        constraint_name = f"constraint_{node_type.value.lower()}_id_unique"
                        if constraint_name not in existing_constraints:
                            indexes_needed = True
                            break
                    
                    # Also check for relationship constraints
                    rel_constraints_to_check = [
                        "constraint_presentation_edge_unique",
                        "constraint_calculation_edge_unique", 
                        "hasConcept_key",
                        "hasUnit_key",
                        "hasPeriod_key"
                    ]
                    for rel_constraint in rel_constraints_to_check:
                        if rel_constraint not in existing_constraints:
                            indexes_needed = True
                            break
                
                # Only create indexes if necessary, outside the transaction
                if indexes_needed:
                    try:
                        self.create_indexes()
                    except Exception as e:
                        # If indexes already exist (from a concurrent process), just continue
                        if "EquivalentSchemaRuleAlreadyExists" in str(e):
                            logger.info("Indexes already exist, continuing with node creation")
                        else:
                            raise
            
            nodes = []
            for collection in collections:
                if collection:
                    # Handle both single nodes and collections
                    if isinstance(collection, list):
                        # Log at DEBUG level as this can be verbose
                        filtered = self._filter_duplicate_facts(collection)
                        nodes.extend(filtered)

                        if filtered:
                             logger.debug(f"Adding {len(filtered)} {type(filtered[0]).__name__} nodes")
                             
                    else:
                        logger.debug(f"Adding single {type(collection).__name__} node")
                        nodes.append(collection)
            
            if nodes:
                self.merge_nodes(nodes)
                logger.info("Node export completed successfully")
                
            # Restore previous setting to avoid side-effects
            self._use_bulk = prev_setting
        except Exception as e:
            logger.error(f"Export to Neo4j failed: {e}", exc_info=True)
            raise RuntimeError(f"Export to Neo4j failed: {e}")

    @retry_on_neo4j_transient_error
    def merge_relationships(self, relationships: List[Union[Tuple[Neo4jNode, Neo4jNode, RelationType], Tuple[Neo4jNode, Neo4jNode, RelationType, Dict[str, Any]]]]) -> None:
        counts = defaultdict(lambda: {'count': 0, 'source': '', 'target': ''})
        relationships = resolve_primary_fact_relationships(relationships)
        
        # Group relationships by type for batch processing
        grouped_rels = defaultdict(list)
        
        network_specific_relationships = {
            RelationType.PRESENTATION_EDGE,
            RelationType.CALCULATION_EDGE,
        }

        def get_network_merge_props(source_id: str, target_id: str, properties: Dict) -> Dict[str, Any]:
            """Get core network relationship properties maintaining uniqueness"""
            network_id = properties.get('network_uri', properties.get('network_name', '')).split('/')[-1]
            company_cik = properties.get('company_cik')
            
            return {
                "merge_source_id": source_id,
                "merge_target_id": target_id,
                "merge_network_id": network_id,
                "company_cik": company_cik
            }

        # First pass: collect statistics and group relationships
        for rel in relationships:
            source, target, rel_type, *props = rel
            properties = props[0] if props else {}

            # Group relationships by type
            grouped_rels[rel_type].append((source, target, properties))

        
        # Second pass: batch process relationships
        with self.driver.session() as session:
            total_written = 0
            for rel_type, rels in grouped_rels.items():

                # Build the full parameter list once (old behaviour)
                all_params = []
                for source, target, properties in rels:
                    if (rel_type in network_specific_relationships and 
                        isinstance(target, Fact) and 
                        ('network_uri' in properties or 'network_name' in properties)):
                        
                        merge_props = get_network_merge_props(source.id, target.id, properties)
                        all_params.append({
                            "source_id": source.id,
                            "target_id": target.id,
                            **merge_props,
                            "properties": properties
                        })
                    else:
                        all_params.append({
                            "source_id": source.id,
                            "target_id": target.id,
                            "properties": properties
                        })

                # === new: chunked execution ==================================
                if all_params:

                    def create_relationships_tx(tx, params, *, rel_type=rel_type, 
                                             network_specific=network_specific_relationships):
                        """Transaction body – identical to original, with parameterised list 'params'."""
                        if rel_type in network_specific:
                            tx.run(f"""
                                UNWIND $params AS param
                                MATCH (s {{id: param.source_id}})
                                MATCH (t {{id: param.target_id}})
                                WITH s, t, param
                                WHERE param.properties.company_cik IS NOT NULL 
                                AND param.properties.report_id IS NOT NULL
                                AND param.properties.network_uri IS NOT NULL
                                AND ('{rel_type.value}' <> 'CALCULATION_EDGE' OR param.properties.context_id IS NOT NULL)
                                MERGE (s)-[r:{rel_type.value} {{
                                    cik: param.properties.company_cik,
                                    report_id: param.properties.report_id,
                                    network_uri: param.properties.network_uri,
                                    parent_id: param.source_id,
                                    child_id: param.target_id,
                                    context_id: CASE 
                                        WHEN '{rel_type.value}' = 'CALCULATION_EDGE' 
                                        THEN param.properties.context_id 
                                        ELSE coalesce(param.properties.context_id, 'default')
                                    END,
                                    weight: param.properties.weight
                                }}]->(t)
                                SET r += param.properties
                            """, {"params": params})
                        elif rel_type in {RelationType.HAS_CONCEPT, RelationType.HAS_UNIT, RelationType.HAS_PERIOD}:
                            # Special handling for fact lookup relationships with key property
                            tx.run(f"""
                                UNWIND $params AS param
                                MATCH (s {{id: param.source_id}})
                                MATCH (t {{id: param.target_id}})
                                MERGE (s)-[r:{rel_type.value} {{key: param.source_id}}]->(t)
                                SET r += param.properties
                            """, {"params": params})
                        else:
                            tx.run(f"""
                                UNWIND $params AS param
                                MATCH (s {{id: param.source_id}})
                                MATCH (t {{id: param.target_id}})
                                MERGE (s)-[r:{rel_type.value}]->(t)
                                SET r += param.properties
                            """, {"params": params})

                    # Split all_params into chunks - smaller for fact lookups
                    # Define fact lookup relationships that need smaller batch size
                    fact_lookup_rels = {RelationType.HAS_CONCEPT, RelationType.HAS_UNIT, RelationType.HAS_PERIOD}
                    batch_size = 500 if rel_type in fact_lookup_rels else self.REL_BATCH_SIZE
                    
                    for i in range(0, len(all_params), batch_size):
                        chunk = all_params[i:i + batch_size]
                        try:
                            session.execute_write(create_relationships_tx, chunk)
                            total_written += len(chunk)
                        except Exception as e:
                            logger.warning(f"Chunk of {len(chunk)} {rel_type.value} relations failed – retrying individually. Error: {e}")
                            # Fallback: attempt each relation separately so that other
                            # good rows are not lost due to one bad row
                            for single in chunk:
                                try:
                                    session.execute_write(create_relationships_tx, [single])  # simplified call
                                    total_written += 1
                                except Exception as e_single:
                                    logger.error(f"Permanent failure inserting relationship: {single} | {e_single}", exc_info=True)

                counts[rel_type.value].update({
                    'count': len(rels),
                    'source': rels[0][0].__class__.__name__,
                    'target': rels[0][1].__class__.__name__
                })

        # Print summary
        for rel_type, info in counts.items():
            logger.info(f"Created {info['count']} {rel_type} relationships from {info['source']} to {info['target']}")

    @retry_on_neo4j_transient_error
    def get_neo4j_db_counts(self) -> Dict[str, Dict[str, int]]:
        """Get count of nodes and relationships by type."""
        try:
            with self.driver.session() as session:
                # Node counts
                node_query = """
                MATCH (n)
                RETURN labels(n)[0] as node_type, count(n) as count
                ORDER BY count DESC
                """
                node_counts = {row["node_type"]: row["count"] for row in session.run(node_query)}
                complete_node_counts = {nt.value: node_counts.get(nt.value, 0) for nt in NodeType}
                
                # Relationship counts
                rel_query = """
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
                """
                rel_counts = {row["rel_type"]: row["count"] for row in session.run(rel_query)}
                complete_rel_counts = {rt.value: rel_counts.get(rt.value, 0) for rt in RelationType}
                
                # Ensure printing only occurs if there are non-zero nodes or relationships
                total_nodes = sum(complete_node_counts.values())
                total_relationships = sum(complete_rel_counts.values())
                
                if total_nodes > 0 or total_relationships > 0:
                    # Print node counts
                    if total_nodes > 0:
                        logger.info("Node counts in Neo4j:")
                        for node_type, count in complete_node_counts.items():
                            if count > 0:  # Only print non-zero nodes
                                logger.info(f"{node_type:<15} : {count:>8,d} nodes")
                        logger.info(f"{'Total':<15} : {total_nodes:>8,d} nodes")
                    
                    # Print relationship counts
                    if total_relationships > 0:
                        logger.info("Relationship counts in Neo4j:")
                        for rel_type, count in complete_rel_counts.items():
                            if count > 0:  # Only print non-zero relationships
                                logger.info(f"{rel_type:<15} : {count:>8,d} relationships")
                        logger.info(f"{'Total':<15} : {total_relationships:>8,d} relationships")
                
        except Exception as e:
            logger.error(f"Error getting node and relationship counts: {e}", exc_info=True)
            return {
                "nodes": {nt.value: 0 for nt in NodeType},
                "relationships": {rt.value: 0 for rt in RelationType}
            }

    @retry_on_neo4j_transient_error
    def load_nodes_as_instances(self, node_type: NodeType, class_type: Type[Neo4jNode]) -> List[Neo4jNode]:
        """Load Neo4j nodes as class instances"""
        try:
            with self.driver.session() as session:
                query = f"MATCH (n:{node_type.value}) RETURN n"
                result = session.run(query)
                instances = [class_type.from_neo4j(dict(record["n"].items())) 
                            for record in result]
                logger.info(f"Loaded {len(instances)} {node_type.value} instances from Neo4j")
                return instances
        except Exception as e:
            logger.error(f"Failed to load {node_type.value} nodes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load {node_type.value} nodes: {e}")

    @retry_on_neo4j_transient_error
    def validate_neo4j_calculations(self) -> None:
        """Validates all calculation relationships stored in Neo4j by checking summations."""
        
        # query = """        
        # MATCH (parent:Fact)-[r:CALCULATION_EDGE]->(child:Fact) 
        # WITH 
        #     parent,
        #     r.network_uri as network_uri,
        #     r.context_id as context_id,
        #     r.network_name as network_name,
        #     COLLECT({
        #         child: child,
        #         weight: r.weight,
        #         order: r.order
        #     }) as children
        # ORDER BY network_uri, context_id, parent.id
        # RETURN 
        #     parent,
        #     network_uri,
        #     network_name,
        #     context_id,
        #     children
        # """
        
        
        query = """        
        MATCH (parent:Fact)-[r:CALCULATION_EDGE]->(child:Fact) 
        WITH 
            parent,
            r.network_uri as network_uri,
            COALESCE(r.context_id, r.period_ref) as context_id,
            r.network_name as network_name,
            COLLECT({
                child: child,
                weight: r.weight,
                order: r.order
            }) as children
        ORDER BY network_uri, context_id, parent.id
        RETURN 
            parent,
            network_uri,
            network_name,
            context_id,
            children
        """
        matches = 0
        non_matches = 0
        network_stats = defaultdict(lambda: {'matches': 0, 'non_matches': 0})
        
        try:
            with self.driver.session() as session:
                results = session.run(query)
                
                for record in results:
                    parent = record['parent']
                    network_uri = record['network_uri']
                    network_name = record['network_name']
                    context_id = record['context_id']
                    children = record['children']
                    
                    # print(f"\nCalculation Group:")
                    # print(f"Network: {network_name}")
                    # print(f"Network URI: {network_uri}")
                    # print(f"Context ID: {context_id}")
                    # print(f"Parent: {parent['qname']} = {parent['value']}")
                    
                    total_sum = 0
                    # print("\nChildren:")
                    for child in sorted(children, key=lambda x: float(x['order'] or 0)):
                        child_fact = child['child']
                        weight = float(child['weight'])
                        value = clean_number(child_fact['value'])
                        weighted_value = value * weight
                        total_sum += weighted_value
                        
                        # print(f"{child_fact['qname']} = {child_fact['value']} × {weight} = {weighted_value:,.2f}")
                    
                    parent_value = clean_number(parent['value'])
                    percent_diff = abs(parent_value - total_sum) if parent_value == 0 else abs(parent_value - total_sum) / abs(parent_value)
                    # is_match = percent_diff < 0.01  # 1% tolerance
                    is_match = percent_diff < 0.001  # 0.1% tolerance
                    
                    # print(f"\nTotal Sum: {total_sum:,.2f}")
                    # print(f"Parent Value: {parent_value:,.2f}")
                    # print(f"Difference: {abs(parent_value - total_sum):,.2f} ({percent_diff:.2%})")
                    # print(f"Match: {'Yes' if is_match else 'No'}")
                    # print("="*80)
                    
                    matches += 1 if is_match else 0
                    non_matches += 1 if not is_match else 0
                    network_stats[network_name]['matches'] += 1 if is_match else 0
                    network_stats[network_name]['non_matches'] += 1 if not is_match else 0
                
                logger.info(f"Neo4j Calculation Summary:")
                logger.info(f"Total Matches: {matches}")
                logger.info(f"Total Non-Matches: {non_matches}")
                if matches + non_matches > 0:
                    logger.info(f"Overall Match Rate: {matches/(matches+non_matches)*100:.1f}%")
                    
                    for network, stats in network_stats.items():
                        total = stats['matches'] + stats['non_matches']
                        if total > 0:
                            match_rate = stats['matches']/total * 100
                            # print(f"\n{network}:")
                            # print(f"Matches: {stats['matches']}")
                            # print(f"Non-Matches: {stats['non_matches']}")
                            # print(f"Match Rate: {match_rate:.1f}%")
                    
        except Exception as e:
            logger.error(f"Failed to validate calculations: {e}", exc_info=True)
            raise RuntimeError(f"Failed to validate calculations: {e}")





    def get_relationship_properties(self, source_id: str, target_id: str, properties: Dict) -> Dict[str, Any]:
        """Prepare relationship properties ensuring uniqueness"""
        # Verify required properties
        if not all(key in properties for key in ['company_cik', 'report_id']):
            raise ValueError("Missing required properties: company_cik and report_id")
            
        base_props = {
            "cik": properties['company_cik'],
            "report_id": properties['report_id'],
            "network_uri": properties.get('network_uri', ''),
            "network_name": properties.get('network_name', '') or properties.get('network_uri', '').split('/')[-1],
            "parent_id": source_id,
            "child_id": target_id
        }
        
        if properties.get('rel_type') == RelationType.PRESENTATION_EDGE:
            if not all(key in properties for key in ['parent_level', 'child_level']):
                raise ValueError("Missing required properties for presentation edge")
            return {
                **base_props,
                "parent_level": int(properties['parent_level']),
                "child_level": int(properties['child_level'])
            }
        else:  # CALCULATION_EDGE
            if 'context_id' not in properties:
                raise ValueError("Missing required context_id for calculation edge")
            return {
                **base_props,
                "context_id": properties['context_id'],
                "weight": properties.get('weight')
            }



    # Usage: 
    # calc_df = report.neo4j.fetch_relationships(RelationType.CALCULATION_EDGE)
    # pres_df = report.neo4j.fetch_relationships(RelationType.PRESENTATION_EDGE) 
    @retry_on_neo4j_transient_error
    def fetch_relationships(self, edge_type: RelationType) -> pd.DataFrame:
        """Fetches relationships with all properties"""
        calc_props = """
            r.weight as weight, 
            r.order as order, 
            r.context_id as context_id
        """
        pres_props = """
            r.parent_level as parent_level,
            r.child_level as child_level,
            r.parent_order as parent_order,
            r.child_order as child_order
        """
        
        base_props = """
            r.cik as cik,
            r.report_id as report_id,
            r.network_name as network_name,
            r.network_uri as network_uri,
            r.network_role as network_role,
            p.id as parent_id,
            c.id as child_id
        """
        
        query = f"""
        MATCH (p)-[r:{edge_type.value}]->(c)
        RETURN 
            {base_props},
            {calc_props if edge_type == RelationType.CALCULATION_EDGE else pres_props}
        """
        
        # Use a with-statement to properly close the session
        with self.driver.session() as session:
            result = session.run(query)
            # Convert to list first and then to DataFrame to ensure the cursor is consumed
            # before the session closes
            return pd.DataFrame([dict(r) for r in result])

    @retry_on_neo4j_transient_error
    def create_relationships(self, source_label, source_id_field, source_id_value, 
                            target_label, target_match_clause, rel_type, params,
                            target_create_properties=None, target_set_properties=None):
        """
        Generic method to create relationships between nodes with UNWIND batching.
        
        Args:
            source_label: Label of the source node (e.g., 'Report')
            source_id_field: Field name for the source ID (e.g., 'id')
            source_id_value: Value of the source ID
            target_label: Label of the target node (e.g., 'Company')
            target_match_clause: Cypher to match/create target nodes (e.g., '{cik: param.cik}')
            rel_type: Relationship type (e.g., 'INFLUENCES')
            params: List of parameter dictionaries for the UNWIND operation
            target_create_properties: Optional ON CREATE SET properties for target nodes
            target_set_properties: Optional SET properties for target nodes
            
        Returns:
            Count of relationships created      
        """
        if not params:
            return 0
            
        # Build target node creation/update logic
        target_creation = f"MERGE (target:{target_label} {target_match_clause})"
        
        if target_create_properties:
            target_creation += f"\nON CREATE SET {target_create_properties}"
            
        if target_set_properties:
            target_creation += f"\nSET {target_set_properties}"
        
        # Build the query
        query = f"""
        MATCH (source:{source_label} {{{source_id_field}: $source_id}})
        UNWIND $params AS param
        {target_creation}
        MERGE (source)-[rel:{rel_type}]->(target)
        SET rel += param.properties
        RETURN count(rel) as relationship_count
        """
        
        # Execute the query with retry logic for deadlocks
        with self.driver.session() as session:
            def create_relationships_tx(tx):
                return tx.run(query, {
                    "source_id": source_id_value,
                    "params": params
                }).single()
            
            # Get the count of relationships created using execute_write for automatic retry
            record = session.execute_write(create_relationships_tx)
            count = record["relationship_count"] if record else 0
            
            return count

    @retry_on_neo4j_transient_error
    def execute_cypher_query(self, query, parameters):
        """
        Execute a Cypher query with the given parameters.
        
        Args:
            query (str): The complete Cypher query to execute
            parameters (dict): Parameters for the query
            
        Returns:
            The single record result or None
        """
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return result.single()

    @retry_on_neo4j_transient_error
    def execute_cypher_query_all(self,
                                 query: str,
                                 parameters: dict | None = None):
        """
        Run a Cypher statement and **always** return the full result‑set as
        list[dict].

        (Keeps execute_cypher_query() pristine and backward‑compatible.)
        """
        parameters = parameters or {}
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [r.data() for r in result]

    @retry_on_neo4j_transient_error
    def create_report_category_relationship(self, report_id, form_type):
        """
        Create an IN_CATEGORY relationship between a report and its category.
        
        Args:
            report_id (str): The report ID
            form_type (str): The form type code (e.g., "10-K")
            
        Returns:
            bool: Whether the relationship was created
        """
        query = """
        MATCH (r:Report {id: $report_id})
        MATCH (a:AdminReport {code: $form_type})
        MERGE (r)-[:IN_CATEGORY]->(a)
        RETURN count(*) as count
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                "report_id": report_id,
                "form_type": form_type
            })
            
            record = result.single()
            return record and record["count"] > 0

    @retry_on_neo4j_transient_error
    def create_hierarchical_relationships(self, child_label, parent_label, relationship_type="BELONGS_TO", 
                                          match_property=None, parent_id_property="id", child_condition=None, parent_id_value=None):
        """
        Create hierarchical relationships between child and parent nodes efficiently.
        
        Args:
            child_label: Label of child nodes (e.g., 'Sector', 'Industry')
            parent_label: Label of parent nodes (e.g., 'MarketIndex', 'Sector')
            relationship_type: Type of relationship (default: 'BELONGS_TO')
            match_property: Property on child that references parent ID (default: None)
            parent_id_property: Property on parent for matching (default: 'id')
            child_condition: Additional WHERE condition for child nodes (default: None)
            parent_id_value: Specific value for parent ID (e.g., 'SPY' for MarketIndex)
        
        Returns:
            int: Number of relationships created
        """
        try:
            # Construct WHERE clause
            conditions = [f"NOT (c)-[:{relationship_type}]->(:{parent_label})"]
            
            if match_property:
                conditions.append(f"c.{match_property} IS NOT NULL AND c.{match_property} <> ''")
                
            if child_condition:
                conditions.append(child_condition)
            
            # Construct parent matching
            params = {}
            if match_property:
                parent_match = f"{{{parent_id_property}: c.{match_property}}}"
            elif parent_id_value:
                parent_match = f"{{{parent_id_property}: $parent_id_value}}"
                params["parent_id_value"] = parent_id_value
            else:
                parent_match = ""
            
            # Complete query
            query = f"""
            MATCH (c:{child_label})
            WHERE {" AND ".join(conditions)}
            MATCH (p:{parent_label} {parent_match})
            MERGE (c)-[r:{relationship_type}]->(p)
            RETURN count(r) AS count
            """
            
            # Execute
            with self.driver.session() as session:
                result = session.run(query, params)
                record = result.single()
                return record["count"] if record else 0
                
        except Exception as e:
            raise RuntimeError(f"Failed to create hierarchical relationships: {e}")

    @retry_on_neo4j_transient_error
    def link_companies_to_industries(self):
        """
        Specialized function to link companies to industries using multiple strategies:
        1. Normalize industry names and link by exact match
        2. Link by case-insensitive name match
        3. Create missing industries for orphans and link them
        4. Link new industries to their sectors
        5. Remove direct company->sector links
        
        Returns:
            dict: Counts of relationships created by each strategy
        """
        # Define queries as constants for better readability
        NORMALIZE_QUERY = """
        MATCH (c:Company)
        WHERE c.industry IS NOT NULL AND c.industry <> ''
        SET c.industry_normalized = replace(c.industry, " ", "")
        """
        
        DIRECT_MATCH_QUERY = """
        MATCH (c:Company)
        WHERE c.industry_normalized IS NOT NULL AND c.industry_normalized <> ''
        MATCH (i:Industry {id: c.industry_normalized})
        MERGE (c)-[:BELONGS_TO]->(i)
        RETURN count(*) as connected
        """
        
        NAME_MATCH_QUERY = """
        MATCH (c:Company)
        WHERE c.industry IS NOT NULL AND c.industry <> ''
        AND NOT (c)-[:BELONGS_TO]->(:Industry)
        MATCH (i:Industry)
        WHERE toLower(trim(i.name)) = toLower(trim(c.industry))
        MERGE (c)-[:BELONGS_TO]->(i)
        RETURN count(*) as connected
        """
        
        FIND_ORPHANS_QUERY = """
        MATCH (c:Company)
        WHERE NOT (c)-[:BELONGS_TO]->(:Industry)
        AND c.industry IS NOT NULL AND c.industry <> ''
        RETURN c.id as id, c.ticker as ticker, c.industry as industry, 
               c.sector as sector
        """
        
        CREATE_INDUSTRY_QUERY = """
        MERGE (i:Industry {id: $industry_id})
        ON CREATE SET i.name = $industry_name,
                     i.sector_id = $sector_id
        WITH i
        MATCH (c:Company {id: $company_id})
        MERGE (c)-[:BELONGS_TO]->(i)
        """
        
        LINK_INDUSTRIES_QUERY = """
        MATCH (i:Industry)
        WHERE i.sector_id IS NOT NULL AND i.sector_id <> ''
        AND NOT (i)-[:BELONGS_TO]->(:Sector)
        MATCH (s:Sector {id: i.sector_id})
        MERGE (i)-[:BELONGS_TO]->(s)
        RETURN count(*) as linked
        """
        
        REMOVE_DIRECT_LINKS_QUERY = """
        MATCH (c:Company)-[r:BELONGS_TO]->(s:Sector)
        DELETE r
        RETURN count(r) as removed
        """
        
        try:
            results = {}
            
            with self.driver.session() as session:
                # Step 1: Normalize company industry names
                session.run(NORMALIZE_QUERY)
                
                # Step 2: Link by exact normalized match
                direct_result = session.run(DIRECT_MATCH_QUERY)
                direct_connected = direct_result.single()["connected"]
                results["direct_match"] = direct_connected
                
                # Step 3: Link by case-insensitive name match
                name_result = session.run(NAME_MATCH_QUERY)
                name_connected = name_result.single()["connected"]
                results["name_match"] = name_connected
                
                # Step 4: Find orphaned companies
                orphaned = session.run(FIND_ORPHANS_QUERY).data()
                
                # Step 5: Create industries for orphaned companies
                created_count = 0
                for company in orphaned:
                    company_id = company["id"]
                    industry_name = company["industry"]
                    sector_name = company.get("sector", "")
                    
                    # Generate normalized industry ID
                    industry_id = industry_name.replace(" ", "")
                    
                    # Determine sector ID
                    sector_id = sector_name.replace(" ", "") if sector_name else ""
                    
                    # Create industry node with proper sector relationship
                    session.run(CREATE_INDUSTRY_QUERY, {
                        "industry_id": industry_id,
                        "industry_name": industry_name,
                        "sector_id": sector_id,
                        "company_id": company_id
                    })
                    created_count += 1
                
                results["created_for_orphans"] = created_count
                
                # Step 6: Link new industries to sectors
                industry_sector_result = session.run(LINK_INDUSTRIES_QUERY)
                industry_sector_linked = industry_sector_result.single()["linked"]
                results["industries_linked_to_sectors"] = industry_sector_linked
                
                # Step 7: Remove direct company->sector links
                removed_result = session.run(REMOVE_DIRECT_LINKS_QUERY)
                direct_links_removed = removed_result.single()["removed"]
                results["direct_company_sector_links_removed"] = direct_links_removed
                
                return results
                
        except Exception as e:
            raise RuntimeError(f"Failed to link companies to industries: {e}")

    @retry_on_neo4j_transient_error
    def create_company_relationships_batch(self, relationship_pairs, relationship_type="RELATED_TO", batch_size=100):
        """
        Create bidirectional relationships between companies efficiently in batches.
        
        Args:
            relationship_pairs: List of (source_cik, target_cik, properties) tuples
            relationship_type: Type of relationship (default: 'RELATED_TO')
            batch_size: Size of batches for processing
            
        Returns:
            int: Number of relationships created
        """
        if not relationship_pairs:
            return 0
            
        try:
            # Single query with UNWIND for better performance
            query = f"""
            UNWIND $batch_params AS param
            MATCH (source:Company {{id: param.source_cik}})
            MATCH (target:Company {{id: param.target_cik}})
            MERGE (source)-[r:{relationship_type}]-(target)
            ON CREATE SET r += param.props
            RETURN count(r) as count
            """
            
            total_count = 0
            
            # Process in batches to avoid transaction size limits
            with self.driver.session() as session:
                for i in range(0, len(relationship_pairs), batch_size):
                    batch = relationship_pairs[i:i+batch_size]
                    
                    # Prepare batch parameters in one format
                    batch_params = [
                        {
                            "source_cik": source_cik,
                            "target_cik": target_cik,
                            "props": props
                        }
                        for source_cik, target_cik, props in batch
                    ]
                    
                    # Execute batch creation
                    result = session.run(query, {"batch_params": batch_params})
                    record = result.single()
                    if record:
                        total_count += record["count"]
            
            return total_count
                
        except Exception as e:
            raise RuntimeError(f"Failed to create company relationships: {e}")

    @retry_on_neo4j_transient_error
    def create_price_relationships_batch(self, batch_params):
        """
        Create HAS_PRICE relationships between Date nodes and entity nodes.
        Uses proper transaction management to prevent deadlocks.
        
        Args:
            batch_params: List of dictionaries with date_id, entity_id, and properties
            
        Returns:
            int: Number of relationships created
        """
        if not batch_params:
            return 0
            
        # Create the query to execute
        query = """
        UNWIND $params AS param
        MATCH (d:Date {id: param.date_id})
        MATCH (e) WHERE e.id = param.entity_id
        MERGE (d)-[r:HAS_PRICE]->(e)
        SET r += param.properties
        RETURN count(r) as count
        """
        
        # Use session with write transaction for proper deadlock handling
        with self.driver.session() as session:
            def create_rels_tx(tx):
                result = tx.run(query, {"params": batch_params})
                record = result.single()
                return record["count"] if record else 0
                
            try:
                # execute_write automatically retries on deadlock
                count = session.execute_write(create_rels_tx)
                return count
            except Exception as e:
                # Use the module logger
                logger.error(f"Error creating price relationships: {e}", exc_info=True) # Changed logger, added exc_info
                return 0

    @retry_on_neo4j_transient_error
    def merge_presentation_edges(self, relationships: List[Tuple[Neo4jNode, Neo4jNode, Dict[str, Any]]]) -> None:
        """Merges PRESENTATION_EDGE relationships using a MERGE clause that 
        matches the specific uniqueness constraint for this relationship type.
        Assumes input list contains only tuples of (source_node, target_node, properties_dict).
        """
        if not relationships:
            logger.info("No PRESENTATION_EDGE relationships provided to merge.")
            return

        # Import RelationType locally if not available globally or handle potential import issues
        try:
             from XBRL.xbrl_core import RelationType
        except ImportError:
             # Handle case where RelationType might need a different import path or is already available
             # This is a fallback, ideally imports are handled at the module level
             if 'RelationType' not in globals():
                  logger.error("Error: RelationType not found for merge_presentation_edges")
                  return 
        
        rel_type = RelationType.PRESENTATION_EDGE # Specific type for this function
        batch_params = []
        # Safely get source/target types from the first element if list is not empty
        source_type = relationships[0][0].__class__.__name__ if relationships else "UnknownSource"
        target_type = relationships[0][1].__class__.__name__ if relationships else "UnknownTarget"

        for source, target, properties in relationships:
            # Validate required properties for the MERGE key exist
            required_keys = {'company_cik', 'report_id', 'network_name', 'parent_level', 'child_level'}
            if not required_keys.issubset(properties.keys()):
                 logger.warning(f"Warning: Skipping relationship between {getattr(source, 'id', '?')} and {getattr(target, 'id', '?')} due to missing required properties for MERGE: {required_keys - properties.keys()}")
                 continue
            
            # Ensure levels are convertible to integers
            try:
                parent_lvl = properties['parent_level']
                child_lvl = properties['child_level']
                int(parent_lvl)
                int(child_lvl)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Warning: Skipping relationship between {getattr(source, 'id', '?')} and {getattr(target, 'id', '?')} due to missing or non-integer level properties: {e}")
                continue

            batch_params.append({
                "source_id": source.id,
                "target_id": target.id,
                "properties": properties # Pass the full properties dict
            })

        if not batch_params:
            logger.info("No valid PRESENTATION_EDGE relationships remained after validation.")
            return

        # Transaction body (unchanged) – parameterised chunk
        def merge_presentation_tx(tx, params_chunk):
            # Use the correct MERGE key matching the constraint
            # Ensure levels are converted to integers in the key
            # Ensure APOC is available for the ON MATCH SET clause
            tx.run(f"""
                UNWIND $params AS param
                MATCH (s {{id: param.source_id}})
                MATCH (t {{id: param.target_id}})
                MERGE (s)-[r:{rel_type.value} {{ 
                    cik: param.properties.company_cik, 
                    report_id: param.properties.report_id, 
                    network_name: param.properties.network_name, 
                    parent_id: param.source_id, 
                    child_id: param.target_id, 
                    parent_level: toInteger(param.properties.parent_level), 
                    child_level: toInteger(param.properties.child_level) 
                }}]->(t)
                ON CREATE SET r = param.properties 
                ON MATCH SET r += apoc.map.clean(param.properties, 
                                 ['cik', 'report_id', 'network_name', 'parent_id', 'child_id', 'parent_level', 'child_level'], 
                                 [null])
            """, {"params": params_chunk})
            # ON CREATE: Set all properties initially.
            # ON MATCH: Add properties NOT used in the MERGE key, using apoc.map.clean to avoid overwriting key props.

        # Execute in manageable chunks with fallback
        with self.driver.session() as session:
            total_written = 0
            for i in range(0, len(batch_params), self.REL_BATCH_SIZE):
                chunk = batch_params[i:i + self.REL_BATCH_SIZE]
                try:
                    session.execute_write(merge_presentation_tx, chunk)
                    total_written += len(chunk)
                except Exception as e:
                    logger.warning(f"Chunk of {len(chunk)} PRESENTATION_EDGE relations failed – retrying individually. Error: {e}")
                    for single in chunk:
                        try:
                            session.execute_write(merge_presentation_tx, [single])
                            total_written += 1
                        except Exception as e_single:
                            logger.error(f"Permanent failure inserting presentation edge: {single} | {e_single}", exc_info=True)

            logger.info(f"Merged {total_written} {rel_type.value} relationships from {source_type} to {target_type}")
    # <<< END NEW METHOD FOR PRESENTATION EDGES >>>

# endregion : Neo4j Manager ########################