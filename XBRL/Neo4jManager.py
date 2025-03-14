from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union, Tuple, Type, TYPE_CHECKING
from collections import defaultdict
from neo4j import GraphDatabase, Driver
import pandas as pd
# Split imports: TYPE_CHECKING for type hints, direct imports for runtime needs
if TYPE_CHECKING:
    from .XBRLClasses import Neo4jNode

# Import needed classes and enums for runtime
from .XBRLClasses import (PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS, NodeType, RelationType, Fact)

from .utils import resolve_primary_fact_relationships, clean_number


# region : Neo4j Manager ########################

@dataclass
class Neo4jManager:
    uri: str
    username: str
    password: str
    driver: Driver = field(init=False)

    PRESENTATION_CONSTRAINT_NAME = "constraint_presentation_edge_unique"
    CALCULATION_CONSTRAINT_NAME = "constraint_calculation_edge_unique"


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
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            if not self.test_connection():
                raise ConnectionError("Failed to connect to Neo4j")
        except Exception as e:
            raise ConnectionError(f"Neo4j initialization failed: {e}")
    
    def close(self):
        if hasattr(self, 'driver'):
            self.driver.close()
                        
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
                    raise RuntimeError(f"Database not fully cleared. {node_count} nodes remaining.")
                    
                print("Database cleared successfully")

        except Exception as e:
            raise RuntimeError(f"Failed to clear database: {e}")




    def create_indexes(self):
        """Create indexes and constraints for both nodes and relationships"""
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
                    print(f"Created constraint for PRESENTATION_EDGE relationships")
                    
                # Calculation Edge constraint
                rel_constraint_name = "constraint_calculation_edge_unique"
                if rel_constraint_name not in existing_constraints:
                    props = ", ".join(f"r.{prop}" for prop in CALCULATION_EDGE_UNIQUE_PROPS)
                    session.run(f"""
                    CREATE CONSTRAINT {rel_constraint_name} IF NOT EXISTS
                    FOR ()-[r:CALCULATION_EDGE]-()
                    REQUIRE ({props}) IS UNIQUE
                    """)
                    print(f"Created constraint for CALCULATION_EDGE relationships")

        except Exception as e:
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


            
    def merge_nodes(self, nodes: List[Neo4jNode], batch_size: int = 2000) -> None:
        """Merge nodes into Neo4j database with batching"""
        if not nodes: return

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

                        # Exclude id from properties
                        properties = {
                            k: (format_value(v) if v is not None else "null")
                            for k, v in node.properties.items()
                            if k != 'id'
                        }
                        
                        query = f"""
                        MERGE (n:{node.node_type.value} {{id: $id}})
                        ON CREATE SET n += $properties
                        ON MATCH SET n += $properties
                        """
                        
                        session.run(query, { "id": node.id, "properties": properties })
                
                print(f"Created {len(nodes)} {nodes[0].__class__.__name__} nodes")

                if skipped_nodes:
                    print(f"Warning: Skipped {len(skipped_nodes)} nodes with null IDs")
                    print("First few skipped nodes:")
                    for node in skipped_nodes[:3]:
                        print(f"Node type: {node.node_type.value}, Properties: {node.properties}")
                        
        except Exception as e:
            raise RuntimeError(f"Failed to merge nodes: {e}")


    def _filter_duplicate_facts(self, nodes: List[Neo4jNode]) -> List[Neo4jNode]:
        """Filter out duplicate facts, keeping only primary facts"""
        if nodes and isinstance(nodes[0], Fact):
            return [node for node in nodes if node.is_primary]
        return nodes


    def _export_nodes(self, collections: List[Union[Neo4jNode, List[Neo4jNode]]], testing: bool = False):
        """Export specified collections of nodes to Neo4j"""
        try:
            if testing:
                self.clear_db()
            
            # Always ensure indexes/constraints exist
            self.create_indexes()
            
            nodes = []
            for collection in collections:
                if collection:
                    # Handle both single nodes and collections
                    if isinstance(collection, list):
                        # print(f"Adding {len(collection)} {type(collection[0]).__name__} nodes")
                        # nodes.extend(collection)
                        filtered = self._filter_duplicate_facts(collection)
                        print(f"Adding {len(filtered)} {type(filtered[0]).__name__} nodes")
                        nodes.extend(filtered)
                    else:
                        print(f"Adding single {type(collection).__name__} node")
                        nodes.append(collection)
            
            if nodes:
                self.merge_nodes(nodes)
                print("Export completed successfully")
                
        except Exception as e:
            raise RuntimeError(f"Export to Neo4j failed: {e}")





    # def merge_relationships(self, relationships: List[Union[Tuple[Neo4jNode, Neo4jNode, RelationType], Tuple[Neo4jNode, Neo4jNode, RelationType, Dict[str, Any]]]]) -> None:
    #     counts = defaultdict(lambda: {'count': 0, 'source': '', 'target': ''})
    #     relationships = resolve_primary_fact_relationships(relationships)

    #     network_specific_relationships = {
    #         RelationType.PRESENTATION_EDGE,
    #         RelationType.CALCULATION_EDGE,
    #     }

    #     def get_network_merge_props(source_id: str, target_id: str, properties: Dict) -> Dict[str, Any]:
    #         """Get core network relationship properties maintaining uniqueness"""
    #         return {
    #             "merge_source_id": source_id,
    #             "merge_target_id": target_id,
    #             "merge_network_id": properties.get('network_uri', properties.get('network_name', '')).split('/')[-1],
    #             "company_cik": properties.get('company_cik')
    #         }

    #     with self.driver.session() as session:
    #         for rel in relationships:
    #             source, target, rel_type, *props = rel
    #             properties = props[0] if props else {}
                
    #             if (rel_type in network_specific_relationships and 
    #                 isinstance(target, Fact) and 
    #                 ('network_uri' in properties or 'network_name' in properties)):

    #                 merge_props = get_network_merge_props(source.id, target.id, properties)
                    
    #                 # Keep the critical MERGE structure explicit
    #                 session.run(f"""
    #                     MATCH (s {{id: $source_id}})
    #                     MATCH (t {{id: $target_id}})
    #                     MERGE (s)-[r:{rel_type.value} {{
    #                         source_id: $merge_source_id,
    #                         target_id: $merge_target_id,
    #                         network_id: $merge_network_id,
    #                         company_cik: $company_cik
    #                     }}]->(t)
    #                     SET r += $properties
    #                 """, {
    #                     "source_id": source.id,
    #                     "target_id": target.id,
    #                     **merge_props,
    #                     "properties": properties
    #                 })
    #             else:
    #                 session.run(f"""
    #                     MATCH (s {{id: $source_id}})
    #                     MATCH (t {{id: $target_id}})
    #                     MERGE (s)-[r:{rel_type.value}]->(t)
    #                     SET r += $properties
    #                 """, {
    #                     "source_id": source.id,
    #                     "target_id": target.id,
    #                     "properties": properties
    #                 })
                
    #             counts[rel_type.value].update({
    #                 'count': counts[rel_type.value]['count'] + 1, 
    #                 'source': source.__class__.__name__, 
    #                 'target': target.__class__.__name__
    #             })
        
    #     for rel_type, info in counts.items():
    #         print(f"Created {info['count']} {rel_type} relationships from {info['source']} to {info['target']}")


    # FASTER VERSION
    def merge_relationships(self, relationships: List[Union[Tuple[Neo4jNode, Neo4jNode, RelationType], Tuple[Neo4jNode, Neo4jNode, RelationType, Dict[str, Any]]]]) -> None:
        counts = defaultdict(lambda: {'count': 0, 'source': '', 'target': '', 'skipped': 0})
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
            for rel_type, rels in grouped_rels.items():
                success_count = 0
                skipped_count = 0
                
                for source, target, properties in rels:
                    try:
                        if (rel_type in network_specific_relationships and 
                            isinstance(target, Fact) and 
                            ('network_uri' in properties or 'network_name' in properties)):
                            
                            merge_props = get_network_merge_props(source.id, target.id, properties)
                            
                            # Use individual MERGE to handle constraints better
                            session.run(f"""
                                MATCH (s {{id: $source_id}})
                                MATCH (t {{id: $target_id}})
                                WITH s, t
                                WHERE $props.company_cik IS NOT NULL 
                                AND $props.report_id IS NOT NULL
                                AND $props.network_uri IS NOT NULL
                                AND ('{rel_type.value}' <> 'CALCULATION_EDGE' OR $props.context_id IS NOT NULL)
                                MERGE (s)-[r:{rel_type.value} {{
                                    cik: $props.company_cik,
                                    report_id: $props.report_id,
                                    network_name: $props.network_uri,
                                    parent_id: $source_id,
                                    child_id: $target_id,
                                    context_id: CASE 
                                        WHEN '{rel_type.value}' = 'CALCULATION_EDGE' 
                                        THEN $props.context_id 
                                        ELSE coalesce($props.context_id, 'default')
                                    END
                                }}]->(t)
                                SET r += $props
                            """, {
                                "source_id": source.id,
                                "target_id": target.id,
                                "props": properties
                            })
                        
                        else:
                            # For non-network relationships
                            session.run(f"""
                                MATCH (s {{id: $source_id}})
                                MATCH (t {{id: $target_id}})
                                MERGE (s)-[r:{rel_type.value}]->(t)
                                SET r += $props
                            """, {
                                "source_id": source.id,
                                "target_id": target.id,
                                "props": properties
                            })
                        
                        success_count += 1
                        
                    except Exception as e:
                        # Skip constraint violations and continue
                        if "ConstraintValidationFailed" in str(e):
                            skipped_count += 1
                        else:
                            # Re-raise for other errors
                            raise

                counts[rel_type.value].update({
                    'count': success_count,
                    'skipped': skipped_count,
                    'source': rels[0][0].__class__.__name__,
                    'target': rels[0][1].__class__.__name__
                })

        # Print results
        for rel_type, info in counts.items():
            print(f"Created {info['count']} {rel_type} relationships from {info['source']} to {info['target']}")
            if info['skipped'] > 0:
                print(f"  Skipped {info['skipped']} existing relationships")







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
                        print("\nNode counts in Neo4j:")
                        print("-" * 40)
                        for node_type, count in complete_node_counts.items():
                            if count > 0:  # Only print non-zero nodes
                                print(f"{node_type:<15} : {count:>8,d} nodes")
                        print("-" * 40)
                        print(f"{'Total':<15} : {total_nodes:>8,d} nodes")
                    
                    # Print relationship counts
                    if total_relationships > 0:
                        print("\nRelationship counts in Neo4j:")
                        print("-" * 40)
                        for rel_type, count in complete_rel_counts.items():
                            if count > 0:  # Only print non-zero relationships
                                print(f"{rel_type:<15} : {count:>8,d} relationships")
                        print("-" * 40)
                        print(f"{'Total':<15} : {total_relationships:>8,d} relationships")
                
        except Exception as e:
            print(f"Error getting node and relationship counts: {e}")
            return {
                "nodes": {nt.value: 0 for nt in NodeType},
                "relationships": {rt.value: 0 for rt in RelationType}
            }

    def load_nodes_as_instances(self, node_type: NodeType, class_type: Type[Neo4jNode]) -> List[Neo4jNode]:
        """Load Neo4j nodes as class instances"""
        try:
            with self.driver.session() as session:
                query = f"MATCH (n:{node_type.value}) RETURN n"
                result = session.run(query)
                instances = [class_type.from_neo4j(dict(record["n"].items())) 
                            for record in result]
                print(f"Loaded {len(instances)} {node_type.value} instances from Neo4j")
                return instances
        except Exception as e:
            raise RuntimeError(f"Failed to load {node_type.value} nodes: {e}")



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
                
                print(f"\nNeo4j Calculation Summary:")
                print(f"Total Matches: {matches}")
                print(f"Total Non-Matches: {non_matches}")
                if matches + non_matches > 0:
                    print(f"Overall Match Rate: {matches/(matches+non_matches)*100:.1f}%")
                    
                    # print("\nBreakdown by Network:")
                    for network, stats in network_stats.items():
                        total = stats['matches'] + stats['non_matches']
                        if total > 0:
                            match_rate = stats['matches']/total * 100
                            # print(f"\n{network}:")
                            # print(f"Matches: {stats['matches']}")
                            # print(f"Non-Matches: {stats['non_matches']}")
                            # print(f"Match Rate: {match_rate:.1f}%")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to validate calculations: {e}")





    def get_relationship_properties(self, source_id: str, target_id: str, properties: Dict) -> Dict[str, Any]:
        """Prepare relationship properties ensuring uniqueness"""
        # Verify required properties
        if not all(key in properties for key in ['company_cik', 'report_id']):
            raise ValueError("Missing required properties: company_cik and report_id")
            
        base_props = {
            "cik": properties['company_cik'],
            "report_id": properties['report_id'],
            "network_name": properties.get('network_uri', '').split('/')[-1],
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
                "context_id": properties['context_id']
            }


    # Usage: 
    # calc_df = report.neo4j.fetch_relationships(RelationType.CALCULATION_EDGE)
    # pres_df = report.neo4j.fetch_relationships(RelationType.PRESENTATION_EDGE)    
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
        
        return pd.DataFrame([dict(r) for r in self.driver.session().run(query)])

    # def fetch_relationships(self, edge_type: RelationType) -> pd.DataFrame:
    #     """Fetches relationships from Neo4j as DataFrame."""
    #     calc_props = "r.weight as weight, r.order as order, r.context_id as context_id"
    #     pres_props = "r.parent_level as parent_level, r.parent_order as parent_order, r.child_level as child_level, r.child_order as child_order"
        
    #     query = f"""
    #     MATCH (p)-[r:{edge_type.value}]->(c)
    #     RETURN p.id as parent_id, p.qname as parent_qname, p.value as parent_value,
    #         c.id as child_id, c.qname as child_qname, c.value as child_value,
    #         r.network_uri as network_uri, r.network_name as network_name,
    #         r.company_cik as cik, r.report_instance as report_instance,
    #         {calc_props if edge_type == RelationType.CALCULATION_EDGE else pres_props}
    #     """
        
    #     return pd.DataFrame([dict(r) for r in self.driver.session().run(query)])

# endregion : Neo4j Manager ########################