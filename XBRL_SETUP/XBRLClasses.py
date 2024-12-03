from __future__ import annotations  # Enable forward references

# dataclasses and typing imports
from dataclasses import dataclass, field, fields
from typing import List, Dict, Optional, Any, Union, Set
from abc import ABC, abstractmethod
from neo4j import GraphDatabase, Driver

# Python imports
import pandas as pd
import re
import html
from collections import defaultdict
from datetime import timedelta, date


# Arelle imports
from arelle import Cntlr, ModelDocument, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ModelValue import QName
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelFact, ModelContext, ModelUnit
from arelle.ModelXbrl import ModelXbrl
from enum import Enum




class NodeType(Enum):
    """XBRL node types in Neo4j"""
    COMPANY = "Company"
    FACT = "Fact"
    CONCEPT = "Concept"
    DIMENSION = "Dimension"
    MEMBER = "Member"
    HYPERCUBE = "Hypercube"
    CONTEXT = "Context"
    PERIOD = "Period"
    UNIT = "Unit"           # Added for numeric facts
    NAMESPACE = "Namespace" # Added for prefix management
    LINKBASE = "Linkbase"  # Added for relationships
    RESOURCE = "Resource"  # Added for labels, references

class RelationType(Enum):
    """XBRL relationship types"""
    HAS_FACT = "HAS_FACT"
    HAS_CONCEPT = "HAS_CONCEPT"
    HAS_DIMENSION = "HAS_DIMENSION"
    HAS_MEMBER = "HAS_MEMBER"
    REPORTS = "REPORTS"
    BELONGS_TO = "BELONGS_TO"
    IN_CONTEXT = "IN_CONTEXT"      # Fact to Context
    HAS_PERIOD = "HAS_PERIOD"      # Context to Period
    HAS_UNIT = "HAS_UNIT"         # Fact to Unit
    PARENT_CHILD = "PARENT_CHILD" # Presentation hierarchy
    CALCULATION = "CALCULATION"    # Calculation relationships
    DEFINITION = "DEFINITION"      # Definition relationships
    HAS_LABEL = "HAS_LABEL"       # Concept to Label
    HAS_REFERENCE = "HAS_REFERENCE" # Concept to Reference


class Neo4jNode(ABC):
    """Abstract base class for Neo4j nodes"""
    
    @property
    @abstractmethod
    def node_type(self) -> NodeType:
        """Node type for Neo4j categorization"""
        pass
        
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for MERGE operations"""
        pass
        
    @property
    @abstractmethod
    def properties(self) -> Dict[str, Any]:
        """Node properties (excluding id)"""
        pass




######################### CONCEPTS START ####################################################


@dataclass
class Concept(Neo4jNode):
    model_concept: ModelConcept # The original ModelConcept object
    qname: str = field(init=False) # Unique ID

    # Properties
    concept_type: str = field(init=False) # self.model_concept.niceType is short but clubs multiple types (dtr_types, dtr_types1)
    period_type: str = field(init=False)  
    namespace: str = field(init=False)
    label: Optional[str] = field(init=False, default=None)
    balance: Optional[str] = field(init=False, default=None)
    type_local: Optional[str] = field(init=False, default=None)    
    
    # TODO:
    # facts: List[Fact] = field(init=False, default_factory=list)
    # hypercubes: Optional[List[str]] = field(default_factory=list)  # Hypercubes associated in the Definition Network
    # presentation_parents: Dict[str, 'Concept'] = field(init=False, default_factory=dict)
    # presentation_children: Dict[str, List['Concept']] = field(init=False, default_factory=dict)
    # presentation_level: Dict[str, int] = field(init=False, default_factory=dict)
    # presentation_order: Dict[str, float] = field(init=False, default_factory=dict)


    def __post_init__(self):        
        self.qname = str(self.model_concept.qname) # Unique ID

        # Properties
        self.concept_type = str(self.model_concept.typeQname) if self.model_concept.typeQname else "N/A"
        self.period_type = self.model_concept.periodType or "N/A"
        self.namespace = self.model_concept.qname.namespaceURI.strip()
        self.label = self.model_concept.label(lang="en")            
        self.balance = self.model_concept.balance
        self.type_local = self.model_concept.baseXsdType
        
    def __hash__(self):
        # Use a unique attribute for hashing, such as qname
        return hash(self.qname)

    def __eq__(self, other):
        # Ensure equality is based on the same attribute used for hashing
        if isinstance(other, Concept):
            return self.qname == other.qname
        return False

    def add_fact(self, fact: Fact) -> None:
        """Add fact reference to concept"""
        self.facts.append(fact)

    # def __repr__(self) -> str:
    #     """Match ModelObject's repr format"""
    #     return f"Concept[{self.qname}, {self.category}, line {self.source_line}]"

    @property
    def is_numeric(self) -> bool:
        return self.model_concept.isNumeric
        
    @property
    def is_monetary(self) -> bool:
        return self.model_concept.isMonetary
        
    @property
    def is_text_block(self) -> bool:
        return self.model_concept.isTextBlock
    
    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        """Used for Neo4j node labeling"""
        return NodeType.CONCEPT
        
    @property
    def id(self) -> str:
        """Unique identifier for Neo4j MERGE"""
        return self.qname
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Actual node properties in Neo4j"""
        return {
            "concept_type": self.concept_type,
            "period_type": self.period_type,
            "namespace": self.namespace,
            "label": self.label,
            "balance": self.balance, # To be used later in Relationships
            "type_local": self.type_local
        }
        

   

######################### CONCEPTS END ####################################################


############################### Report Class START #######################################################

@dataclass
class Report:

    # Add Other Report Elements

    instance_file: str
    neo4j: Neo4jManager
    log_file: str = field(default='ErrorLog.txt', repr=False)
    testing: bool = field(default=False)  # Add testing flag as configurable

    model_xbrl: ModelXbrl = field(init=False, repr=False)
    report_metadata: Dict[str, object] = field(init=False, default_factory=dict)
    
    # Core collections
    concepts: List[Concept] = field(init=False, default_factory=list, repr=False)
    facts: List[Fact] = field(init=False, default_factory=list, repr=False)
    dimensions: List[Dimension] = field(init=False, default_factory=list, repr=False)
 
     # TODO
     # networks: List[Network] = field(init=False, default_factory=list, repr=False)
    # _concept_lookup: Dict[str, Concept] = field(init=False, default_factory=dict, repr=False)

    def __post_init__(self):
        self.load_xbrl()
        self.extract_report_metadata()
        self.populate_fields()        
        self.export_to_neo4j(self.testing)  # Use instance testing flag

        # self.build_relationships()

    def load_xbrl(self):
        # Initialize the controller
        controller = Cntlr.Cntlr(logFileName=self.log_file, logFileMode='w', logFileEncoding='utf-8')
        controller.modelManager.formulaOptions = FormulaOptions()

        # Load the model_xbrl
        try:
            self.model_xbrl = controller.modelManager.load(filesource=FileSource.FileSource(self.instance_file), discover=True)
        except Exception as e: 
            raise RuntimeError(f"Error loading XBRL model: {e}")

    # Review it - See Notes.txt
    def extract_report_metadata(self):
        ctx = list(self.model_xbrl.contexts.values())[0]  # First context for metadata
        self.report_metadata = {
            # "company_name": ctx.entityIdentifier[1],
            "file_name": self.model_xbrl.modelDocument.basename,
            "entity_id": ctx.entityIdentifier[1],
            "start_date": ctx.startDatetime.date() if ctx.isStartEndPeriod else None,
            "end_date": (ctx.endDatetime - timedelta(days=1)).date() if ctx.isStartEndPeriod else ctx.endDatetime.date() if ctx.isInstantPeriod else None,
            "period_start": ctx.period[0].stringValue if ctx.isStartEndPeriod else None,
            "period_end": ctx.period[1].stringValue if ctx.isStartEndPeriod else ctx.period[0].stringValue if ctx.isInstantPeriod else None,
            "period_type": "duration" if ctx.isStartEndPeriod else "instant" if ctx.isInstantPeriod else "forever" }


    def populate_fields(self):
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
        
        self._build_concepts()  # 1. Build concepts first
        # self._build_facts()     # 3. Build facts with validation
        # self._build_networks()  # 2. Build networks and hierarchies
        # self._build_dimensions() # 4. Build dimensions

    def export_to_neo4j(self, testing: bool = False) -> None:
            """Export selected node types to Neo4j"""
            try:
                if testing:
                    self.neo4j.clear_db()
                    self.neo4j.create_indexes()
                
                nodes = []
                # collections = [self.concepts, self.facts, self.dimensions]
                collections = [self.concepts]
                
                if not any(collections):  # Check if all collections are empty
                    print("Warning: No nodes to export")
                    return
                    
                for collection in collections:
                    if collection:  # Only extend if collection exists and has items
                        nodes.extend(collection)
                
                if nodes:
                    self.neo4j.merge_nodes(nodes)
                    
            except Exception as e:
                raise RuntimeError(f"Export to Neo4j failed: {e}")

    def _build_concepts(self):
        """Build concept objects from the model."""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        self.concepts = []
        
        # Explanation: 'model_xbrl.factsByQname.keys()' has concepts' qnames so we use fact.concept from model_xbrl.factsInInstance to fetch the concepts
        unique_concepts = {fact.concept for fact in self.model_xbrl.factsInInstance if fact.concept.qname in self.model_xbrl.factsByQname.keys()}
        self.concepts = [Concept(concept) for concept in unique_concepts]
        
        print(f"Built {len(self.concepts)} concepts") 

    # TODO: Here its not able to find the concept for some facts
    def _build_facts(self):
        """Build facts with two-way concept relationships"""
        for model_fact in self.model_xbrl.factsInInstance:
            fact = Fact(model_fact=model_fact)
            concept = self._concept_lookup.get(fact.qname)
            if not concept: 
                print(f"Warning: No concept found for fact {fact.fact_id}")
                continue
                
            # Two-way linking
            fact.concept = concept
            concept.add_fact(fact)
            
            self.facts.append(fact)


    # 1. Build networks - Also builds hypercubes in networks with isDefinition = True
    def _build_networks(self):
        """Build all networks from the model_xbrl"""
        
        # Define relationship types to check
        relationship_sets = [
            XbrlConst.parentChild,       # parent-child relationships - presentation
            XbrlConst.summationItem,     # calculation relationships  - calculation
            XbrlConst.all,               # all relationships (primary item requires dimension members) - definition
            XbrlConst.notAll,            # notAll relationships (primary item excludes dimension members) - definition
            XbrlConst.dimensionDefault,  # dimension-default relationships - definition
            XbrlConst.dimensionDomain,   # dimension-domain relationships - definition
            XbrlConst.domainMember,      # domain-member relationships - definition
            XbrlConst.hypercubeDimension # hypercube-dimension relationships - definition
        ]
        
        # linkrole: 'http://strongholddigitalmining.com/role/CONSOLIDATEDBALANCESHEETS'
        # role_name: (0000003 - Statement - CONSOLIDATED BALANCE SHEETS)
    
        # Use a list comprehension to create Network instances
        self.networks = [
            Network(
                model_xbrl = self.model_xbrl,
                name =' - '.join(parts[2:]), network_uri=uri,
                id=parts[0],
                category=parts[1],
                relationship_sets=[rel_set]
            )
            for rel_set in relationship_sets
            for rel in self.model_xbrl.relationshipSet(rel_set).modelRelationships

            # Skip if  is missing
            if (role_name := self.model_xbrl.roleTypeName(roleURI=(uri := rel.linkrole))) 
            and len(parts := [p.strip() for p in role_name.split(' - ')]) >= 3 ] # Need at least ID, Category, and Description
        

        # 1. Network deduplication with relationship set merging
        unique_networks = {}
        for network in self.networks:
            key = (network.network_uri, network.name, network.id, network.category)
            if key in unique_networks:
                # Add any new relationship sets that aren't already present
                unique_networks[key].relationship_sets.extend(
                    rs for rs in network.relationship_sets 
                    if rs not in unique_networks[key].relationship_sets)
            else:
                unique_networks[key] = network
        
        self.networks = list(unique_networks.values())

        # 2. Link presentation concepts first
        for network in self.networks:
            if network.isPresentation:
                network._link_presentation_concepts(self.concepts)

                
        # 3. Adding hypercubes after networks are complete which in turn builds dimensions
        for network in self.networks:
            network.add_hypercubes(self.model_xbrl)
            for hypercube in network.hypercubes:
                hypercube._link_concepts(self.concepts)



############################### Report Class END #######################################################




############################### Hypercube Class START #######################################################

@dataclass
class Hypercube:
    """Represents a hypercube (table) in an XBRL definition network"""
    model_xbrl: ModelXbrl
    hypercube_item: Any  # The ModelObject representing the hypercube
    network_uri: str     # Reference back to parent network
    dimensions: List[Dimension] = field(init=False) # Dimensions related to the hypercube
    concepts: List[Concept] = field(init=False)  # Concepts related to the hypercube

    def __post_init__(self):
        """Initialize derived attributes from hypercube_item"""
        if not (hasattr(self.hypercube_item, 'isHypercubeItem') and 
                self.hypercube_item.isHypercubeItem):
            raise ValueError("Object must be a hypercube item")
            
        self.qname = self.hypercube_item.qname
        self.dimensions = [] 
        self.concepts = []  # Initialize concepts list here
        self._build_dimensions()


    def _build_dimensions(self) -> None:
        """Build dimension objects from model_xbrl matching this hypercube"""
        
        hc_dim_rel_set = self.model_xbrl.relationshipSet(XbrlConst.hypercubeDimension, self.network_uri)
        if not hc_dim_rel_set:
            return
            
        relationships = hc_dim_rel_set.fromModelObject(self.hypercube_item)
        
        if not relationships:
            print("No dimension relationships found")
            return
            
        # Debug the relationships
        for rel in relationships:
            dim_object = rel.toModelObject
            if dim_object is None: continue
            
            try:
                dimension = Dimension(
                    model_xbrl=self.model_xbrl,
                    dimension=dim_object)
                
                self.dimensions.append(dimension)
            
            except Exception as e: continue

    # Get all concepts related to a hypercube
    def _link_concepts(self, report_concepts: List[Concept]) -> None:
        all_set = self.model_xbrl.relationshipSet(XbrlConst.all, self.network_uri)
        not_all_set = self.model_xbrl.relationshipSet(XbrlConst.notAll, self.network_uri)
        domain_member = self.model_xbrl.relationshipSet(XbrlConst.domainMember, self.network_uri)
        
        def collect_domain_members(concept):
            if concept is not None:
                if not concept.isAbstract:
                    # Find matching concept in report_concepts
                    concept_qname = str(concept.qname)
                    matching_concept = next(
                        (c for c in report_concepts if str(c.qname) == concept_qname), 
                        None )
                    
                    if matching_concept:
                        self.concepts.append(matching_concept)
                
                # Recursively collect domain members
                for member_rel in domain_member.fromModelObject(concept):
                    collect_domain_members(member_rel.toModelObject)
        
        # Process 'all' relationships
        if all_set:
            for rel in all_set.modelRelationships:
                if (rel.toModelObject is not None and 
                    rel.toModelObject == self.hypercube_item):
                    collect_domain_members(rel.fromModelObject)
        
        # Process 'notAll' relationships
        if not_all_set:
            for rel in not_all_set.modelRelationships:
                if (rel.fromModelObject is not None and 
                    rel.fromModelObject == self.hypercube_item):
                    collect_domain_members(rel.toModelObject)
    @property
    def name(self) -> str:
        """Human-readable name of the hypercube"""
        return self.hypercube_item.name
        
    @property
    def id(self) -> str:
        """ID attribute of the hypercube"""
        return self.hypercube_item.id if hasattr(self.hypercube_item, 'id') else None

############################### Hypercube Class END #######################################################


############################### Network Class START #######################################################


@dataclass
class Network:
    """Represents a single network (extended link role) in the XBRL document"""
    model_xbrl: ModelXbrl
    name: str
    network_uri: str
    id: str
    category: str
    relationship_sets: List[str] = field(default_factory=list)
    hypercubes: List[Hypercube] = field(init=False, default_factory=list)
    concepts: List[Concept] = field(init=False, default_factory=list)  # This was missing
    
    def add_hypercubes(self, model_xbrl) -> None:
        """Add hypercubes if this is a definition network"""
        if not self.isDefinition:
            return
            
        for rel in model_xbrl.relationshipSet(XbrlConst.all).modelRelationships:
            if (rel.linkrole == self.network_uri and 
                rel.toModelObject is not None and 
                hasattr(rel.toModelObject, 'isHypercubeItem') and 
                rel.toModelObject.isHypercubeItem):
                
                hypercube = Hypercube(
                    model_xbrl = self.model_xbrl,
                    hypercube_item=rel.toModelObject,
                    network_uri=self.network_uri
                )
                self.hypercubes.append(hypercube)

    @property
    def isPresentation(self) -> bool:
        """Indicates if network contains presentation relationships"""
        return XbrlConst.parentChild in self.relationship_sets

    @property
    def isCalculation(self) -> bool:
        """Indicates if network contains calculation relationships"""
        return XbrlConst.summationItem in self.relationship_sets

    @property 
    def isDefinition(self) -> bool:
        """Indicates if network contains definition relationships"""
        return any(rel in self.relationship_sets for rel in [
            XbrlConst.all,
            XbrlConst.notAll,
            XbrlConst.dimensionDefault,
            XbrlConst.dimensionDomain,
            XbrlConst.domainMember,
            XbrlConst.hypercubeDimension
        ])

    @property
    def networkType(self) -> str:
        """Returns the detailed category type of the network"""
        if self.category == 'Statement':
            return 'Statement'
        elif self.category == 'Document':
            return 'Document'
        elif self.category == 'Disclosure':
            if '(Tables)' in self.name:
                return 'Tables'
            elif '(Policies)' in self.name:
                return 'Policies'
            elif '(Details)' in self.name:
                return 'Details'
            else:
                return 'FootNotes'
        return 'Other'

    # def _link_presentation_concepts(self, report_concepts: List[Concept]) -> None:
    #     """Link concepts in presentation networks and build hierarchy"""
    #     if not self.isPresentation:
    #         return
                
    #     rel_set = self.model_xbrl.relationshipSet(XbrlConst.parentChild, self.network_uri)
    #     if not rel_set:
    #         return

    #     # Process all relationships instead of trying to find roots
    #     for rel in rel_set.modelRelationships:
    #         from_obj = rel.fromModelObject
    #         to_obj = rel.toModelObject
            
    #         # Process both source and target concepts
    #         for model_object in (from_obj, to_obj):
    #             if model_object is None:
    #                 continue
                    
    #             # Find matching concept
    #             current = next(
    #                 (c for c in report_concepts if str(c.qname) == str(model_object.qname)), 
    #                 None)
                
    #             if current and current not in self.concepts:
    #                 self.concepts.append(current)
                    
    #         # Set parent-child relationship if both concepts exist
    #         if from_obj is not None and to_obj is not None:
    #             from_concept = next(
    #                 (c for c in report_concepts if str(c.qname) == str(from_obj.qname)), 
    #                 None)
    #             to_concept = next(
    #                 (c for c in report_concepts if str(c.qname) == str(to_obj.qname)), 
    #                 None)
                
    #             # if from_concept and to_concept:
    #             #     to_concept.presentation_parents[self.network_uri] = from_concept.qname
    #             #     from_concept.presentation_children.setdefault(self.network_uri, []).append(to_concept.qname)
    #             #     to_concept.presentation_level[self.network_uri] = rel.order

    #                 # Store the actual Concept objects instead of just qnames
    #             if from_concept and to_concept: 
    #                 to_concept.presentation_parents[self.network_uri] = from_concept
    #                 from_concept.presentation_children.setdefault(self.network_uri, []).append(to_concept)
                    
    #                 # Calculate proper level based on parent's level
    #                 parent_level = from_concept.presentation_level.get(self.network_uri, 0)
    #                 to_concept.presentation_level[self.network_uri] = parent_level + 1
    #                 to_concept.presentation_order[self.network_uri] = float(rel.order)


    def _link_presentation_concepts(self, report_concepts: List[Concept]) -> None:
        """Link concepts in presentation networks and build hierarchy"""
        if not self.isPresentation:
            print(f"Network {self.network_uri} is not a presentation network")
            return
                
        rel_set = self.model_xbrl.relationshipSet(XbrlConst.parentChild, self.network_uri)
        if not rel_set:
            print(f"No relationship set found for network {self.network_uri}")
            return

        # Debug counters
        processed_rels = 0
        linked_concepts = 0

        # Process all relationships
        for rel in rel_set.modelRelationships:
            from_obj = rel.fromModelObject
            to_obj = rel.toModelObject
            
            if from_obj is None or to_obj is None:
                continue
                
            # Find concepts and add to network
            from_concept = next(
                (c for c in report_concepts if str(c.qname) == str(from_obj.qname)), 
                None)
            to_concept = next(
                (c for c in report_concepts if str(c.qname) == str(to_obj.qname)), 
                None)
                
            
            if from_concept and to_concept:
                try:
                    # Set relationships
                    to_concept.presentation_parents[self.network_uri] = from_concept
                    from_concept.presentation_children.setdefault(self.network_uri, []).append(to_concept)
                    
                    # Set level and order
                    parent_level = from_concept.presentation_level.get(self.network_uri, 0)
                    to_concept.presentation_level[self.network_uri] = parent_level + 1
                    to_concept.presentation_order[self.network_uri] = float(rel.order)
                    
                    linked_concepts += 1
                    print(f"Successfully linked concepts")
                    
                except Exception as e:
                    print(f"Error linking concepts: {e}")
            else:
                print(f"Concepts not found in report_concepts")
                
            processed_rels += 1
        
        print(f"\nNetwork {self.network_uri}:")
        print(f"- Processed {processed_rels} relationships")
        print(f"- Linked {linked_concepts} concept pairs")

######################### Network Class END #######################################################




######################### Definitions Classes START #######################################################


@dataclass
class Member:
    """Represents a dimension member in a hierarchical structure"""
    model_xbrl: ModelXbrl
    member: ModelConcept
    qname: str = field(init=False)
    label: str = field(init=False)
    parent_qname: Optional[str] = None
    level: int = 0
    
    def __post_init__(self):
        self.qname = str(self.member.qname)
        self.label = self.member.label() if hasattr(self.member, 'label') else None

@dataclass
class Domain:
    """Represents a dimension domain"""
    model_xbrl: ModelXbrl
    domain: ModelConcept
    qname: str = field(init=False)
    label: str = field(init=False)
    type: str = field(init=False)
    
    def __post_init__(self):
        self.qname = str(self.domain.qname)
        self.label = self.domain.label() if hasattr(self.domain, 'label') else None
        self.type = self.domain.typeQname.localName if hasattr(self.domain, 'typeQname') else None


@dataclass
class Dimension:
    """Dimension with its domain and members"""
    model_xbrl: ModelXbrl
    dimension: ModelConcept

    
    # Core properties
    name: str = field(init=False)
    qname: str = field(init=False)
    id: str = field(init=False)
    label: str = field(init=False)
    
    # Dimension type
    is_explicit: bool = field(init=False)
    is_typed: bool = field(init=False)
    
    # Related objects
    domain: Optional[Domain] = field(init=False, default=None)
    members_dict: Dict[str, Member] = field(default_factory=dict)  # For storing members
    default_member: Optional[Member] = field(init=False, default=None)
    
    # Collections - ToDo
    # facts: List[Fact] = field(init=False, default_factory=list)
    # concepts: List[Concept] = field(init=False, default_factory=list)
    # hypercubes: List[str] = field(default_factory=list)
    
    # network: str = field(init=False, default="")


    @property
    def members(self) -> List[Member]:
        """Get unique members sorted by level"""
        return sorted(self.members_dict.values(), key=lambda x: x.level)

    @property
    def members_by_level(self) -> Dict[int, List[Member]]:
        """Get members organized by their hierarchy level"""
        levels: Dict[int, List[Member]] = {}
        for member in self.members:
            if member.level not in levels:
                levels[member.level] = []
            levels[member.level].append(member)
        return levels
    
    @property
    def member_hierarchy(self) -> Dict[str, List[str]]:
        """Get parent-child relationships between members"""
        hierarchy: Dict[str, List[str]] = {}
        for member in self.members:
            parent_qname = str(member.parent_qname) if member.parent_qname else None
            if parent_qname not in hierarchy:
                hierarchy[parent_qname] = []
            hierarchy[parent_qname].append(str(member.qname))
        return hierarchy

    def __post_init__(self):
        # Core properties
        self.name = str(self.dimension.qname.localName)
        self.qname = str(self.dimension.qname)
        self.id = str(self.dimension.objectId())
        self.label = self.dimension.label() if hasattr(self.dimension, 'label') else None
        
        # Dimension type
        self.is_explicit = bool(getattr(self.dimension, 'isExplicitDimension', False))
        self.is_typed = bool(getattr(self.dimension, 'isTypedDimension', False))
        
        self._build_relationships()
    
    def _build_relationships(self) -> None:
        """Build all relationships"""
        self._build_domain()
        if self.domain:  # Only build members if domain exists
            self._build_members()
            self._set_default_member()


    def _build_domain(self) -> None:
        """Build domain relationship for this dimension"""        
        if not self.is_explicit: return
                
        dim_dom_rel_set = self.model_xbrl.relationshipSet(XbrlConst.dimensionDomain)
        if not dim_dom_rel_set: return
                
        relationships = dim_dom_rel_set.fromModelObject(self.dimension)
        if not relationships: return
                
        # Process first domain relationship
        for rel in relationships:
            domain_object = rel.toModelObject
            
            if domain_object is None: continue
                
            try:
                self.domain = Domain(
                    model_xbrl=self.model_xbrl,
                    domain=domain_object
                )
                break  # Take the first valid domain
            except Exception as e:
                print(f"Error creating domain for {self.qname}: {str(e)}")
                continue

    def add_member(self, member: Member) -> None:
        """Add member if not already present"""
        if member.qname not in self.members_dict:
            self.members_dict[member.qname] = member
        else:
            pass
    
    def _build_members(self) -> None:
        """Build hierarchical member relationships"""
        
        if not self.is_explicit:return
                
        if not self.domain: return
                
        dom_mem_rel_set = self.model_xbrl.relationshipSet(XbrlConst.domainMember)
        if not dom_mem_rel_set: return
        
        def add_members_recursive(source_object: ModelConcept, parent_qname: Optional[str] = None, level: int = 0) -> None:
            
            relationships = dom_mem_rel_set.fromModelObject(source_object)
            
            
            for rel in relationships:
                member_object = rel.toModelObject

                
                if member_object is None:
                    continue
                    
                if not hasattr(member_object, 'isDomainMember'):
                    continue
                    
                try:
                    member = Member(
                        model_xbrl=self.model_xbrl,
                        member=member_object,
                        parent_qname=parent_qname,
                        level=level
                    )
                    
                    self.add_member(member)
                    
                    # Process children
                    add_members_recursive(member_object, str(member_object.qname), level + 1)
                        
                except Exception as e:
                    print(f"Error creating member {member_object.qname}: {str(e)}")
                    continue
        
        add_members_recursive(self.domain.domain)

    def _set_default_member(self) -> None:
        """Set default member if exists"""
        default_rel_set = self.model_xbrl.relationshipSet(XbrlConst.dimensionDefault)
        if not default_rel_set: return
            
        # Get relationships using fromModelObject
        relationships = default_rel_set.fromModelObject(self.dimension)
        if not relationships: return
        
        # Debug: Print all relationships for this dimension
        rel_list = list(relationships)
        # for rel in rel_list:
        #     print(f"Default relationship - From: {rel.fromModelObject.qname} -> To: {rel.toModelObject.qname}")
            
        try:
            default_rel = next(iter(relationships))
            default_domain_obj = default_rel.toModelObject
            
            if default_domain_obj is None: return
                
            # Create Member object from the domain that's set as default
            self.default_member = Member(
                model_xbrl=self.model_xbrl,
                member=default_domain_obj,
                parent_qname=None,
                level=0)
            
            # Add to members collection
            self.add_member(self.default_member)
                
        except Exception as e:
            print(f"Error setting default member for {self.qname}: {str(e)}")

######################### Definitions Classes END #######################################################

######################### Neo4j Setup START #####################################################

@dataclass
class Neo4jManager:
    uri: str
    username: str
    password: str
    driver: Driver = field(init=False)
    
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
        """Development only: Clear database"""
        try:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        except Exception as e:
            raise RuntimeError(f"Failed to clear database: {e}")
            
    def create_indexes(self):
        """Create indexes for all node types"""
        try:
            with self.driver.session() as session:
                for node_type in NodeType:
                    session.run(f"""
                    CREATE INDEX IF NOT EXISTS FOR (n:`{node_type.value}`)
                    ON (n.id)
                    """)
        except Exception as e:
            raise RuntimeError(f"Failed to create indexes: {e}")
        
    def merge_nodes(self, nodes: List[Neo4jNode], batch_size: int = 1000) -> None:
        if not nodes:
            return
                
        if batch_size <= 0:
            raise ValueError("Batch size must be positive")
        
        try:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                node_label = batch[0].node_type.value
                
                # Convert None to null in properties
                batch_data = [{
                    "id": node.id,
                    "properties": {
                        k: (v if v is not None else "null") 
                        for k, v in node.properties.items()
                    }
                } for node in batch]
                
                query = """
                UNWIND $batch as node
                MERGE (n {id: node.id})
                SET n:%s
                SET n += node.properties
                """ % node_label
                
                with self.driver.session() as session:
                    session.run(query, batch=batch_data)
        except Exception as e:
            raise RuntimeError(f"Failed to merge nodes: {e}")


    def get_node_counts(self) -> Dict[str, int]:
        """Get count of nodes by type"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (n)
                RETURN labels(n)[0] as node_type, count(n) as count
                """
                result = session.run(query)
                counts = {row["node_type"]: row["count"] for row in result}
                
                # Print summary
                print("\nNode counts in Neo4j:")
                for node_type, count in counts.items():
                    print(f"{node_type}: {count} nodes")
                    
                return counts
        except Exception as e:
            print(f"Error getting node counts: {e}")
            return {}


######################### Neo4j Setup END #####################################################




#############################FACT CLASS START########################################
@dataclass
class Fact:
    model_fact: ModelFact
    concept: 'Concept' = field(init=False)  # Reference to concept instance - One-way reference
    

    # Fact properties
    fact_id: str = field(init=False)
    qname: str = field(init=False)  # Changed from 'concept' to 'qname' for clarity

    context_id: str = field(init=False)
    unit_id: Optional[str] = field(init=False, default=None)
    value: str = field(init=False)
    
    # Unit properties
    unit_ref: Optional[str] = field(init=False, default=None)
    unit_symbol: Optional[str] = field(init=False, default=None)
    unit_measures: Optional[str] = field(init=False, default=None)
    utr_entries: Optional[List[str]] = field(init=False, default=None)  # Changed to List
    
    # Numeric properties
    decimals: Optional[int] = field(init=False, default=None)
    is_numeric: bool = field(init=False, default=False)
    is_nil: bool = field(init=False, default=False)
    
    # Context properties
    period: Optional[str] = field(init=False, default=None)
    
    # Dimension properties - These are all likley incorrect - need to check
    dimensions: List[str] = field(init=False, default_factory=list)
    members: List[str] = field(init=False, default_factory=list)
    enumeration_types: Optional[Dict] = field(init=False, default=None)
    

    def __post_init__(self):
        """Initialize all fields from model_fact after dataclass creation"""
        if not isinstance(self.model_fact, ModelFact):
            raise TypeError("model_fact must be ModelFact type")
            
        # Core properties
        self.fact_id = self.model_fact.id or "N/A"
        self.qname = str(self.model_fact.qname)
        self.context_id = self.model_fact.contextID
        self.unit_id = self.model_fact.unitID
        self.value = self._extract_text(self.model_fact.value)
        
        # Unit properties
        self.unit_ref = self._normalize_unit_id(self.model_fact.unitID)
        self.unit_symbol = self.model_fact.unitSymbol() if hasattr(self.model_fact, 'unitSymbol') else None
        # self.unit_measures = (
        #     ', '.join([str(measure) for measure in self.model_fact.unit.measures[0]]) 
        #     if self.model_fact.unit and hasattr(self.model_fact.unit, 'measures') 
        #     and self.model_fact.unit.measures else None
        # )

        self.unit_measures = ', '.join(str(measure) for measure in self.model_fact.unit.measures[0]) if getattr(self.model_fact.unit, 'measures', None) else None

        self.utr_entries = ", ".join(map(str, self.model_fact.utrEntries)) if self.model_fact.utrEntries else None
        
        # Numeric properties
        self.decimals = self.model_fact.decimals
        self.is_numeric = self.model_fact.isNumeric
        self.is_nil = self.model_fact.isNil
        
        # Context properties
        self._set_period()
        self._set_dimensions()
        self._set_enumeration_types()

    def __repr__(self) -> str:
        """Match ModelObject's repr format"""
        return f"Fact[{self.concept}, {self.value}, context {self.context_id}]"

    @staticmethod
    def _normalize_unit_id(unit_id: str) -> Optional[str]:
        """Convert unit IDs to standard format"""
        if not unit_id:
            return None
        if isinstance(unit_id, str) and unit_id.startswith('u-'):
            return unit_id
        if hasattr(unit_id, 'id'):
            return f"u-{unit_id.id}"
        return f"u-{abs(hash(str(unit_id))) % 10000}"

    @staticmethod
    def _extract_text(value: str) -> str:
        """Extract text from HTML/XML content"""
        return re.sub('<[^>]+>', '', html.unescape(value)) if '<' in value and '>' in value else value

    def _set_period(self) -> None:
        """Set the period property based on context"""
        context = self.model_fact.context
        if context is None or len(context) == 0:
            self.period = None
            return
            
        if getattr(context, 'isInstantPeriod', False):
            self.period = context.instantDatetime.strftime('%Y-%m-%d')
        elif getattr(context, 'isStartEndPeriod', False):
            self.period = f"{context.startDatetime.strftime('%Y-%m-%d')} to {context.endDatetime.strftime('%Y-%m-%d')}"
        else:
            self.period = "Forever"

    # INCORRECTLY Fetching values - Also doesn;t contain all as in sheet
    # "EnumerationTypes": ", ".join([f"{k}={getattr(v, 'value', str(v))}" for k, v in concept.facets.items()]) if concept.facets else None,
    def _set_enumeration_types(self) -> None:
        """Set enumeration types using same logic as original"""
        concept = self.model_fact.concept
        if concept.facets:
            self.enumeration_types = {
                k: [str(v).split('[')[0].strip() for v in vals] 
                if isinstance(vals, (list, tuple)) 
                else {
                    str(enum_val).split('[')[0].strip() 
                    for enum_val in vals.enumeration.values()
                } if hasattr(vals, 'enumeration') else str(vals)
                for k, vals in concept.facets.items()
            }
        elif concept.isEnumeration and concept.enumeration:
            self.enumeration_types = [str(m).split('[')[0].strip() 
                                    for m in concept.enumeration]
        else:
            self.enumeration_types = None


    def _set_dimensions(self) -> None:
        """Set dimensions and members using same logic as original"""
        if hasattr(self.model_fact.context, 'qnameDims'):
            for dim_qname, dim_value in self.model_fact.context.qnameDims.items():
                self.dimensions.append(str(dim_qname))
                member = (
                    str(dim_value.memberQname) if dim_value.isExplicit
                    else dim_value.typedMember.stringValue if dim_value.isTyped
                    else "Unknown"
                )
                self.members.append(member)


    def to_dict(self) -> Dict:
        """Convert fact to dictionary format matching original DataFrame"""
        return {
            "FactID": self.fact_id,
            "Concept": self.concept,
            "ContextID": self.context_id,
            "UnitID": self.unit_id,
            "Value": self.value,
            "UnitRef": self.unit_ref,
            "UnitSymbol": self.unit_symbol,
            "Unit": self.unit_measures,
            "UtrEntries": self.utr_entries,
            "Decimals": self.decimals,
            "IsNumeric": self.is_numeric,
            "IsNil": self.is_nil,
            "Period": self.period,
            "Dimensions": self.dimensions,
            "Members": self.members,
            "EnumerationTypes": self.enumeration_types
        }

    def to_cypher(self):
        """Generate Cypher query from fact"""
        return super().to_cypher("Fact", self.to_dict())
    

#############################FACT CLASS END########################################    



#  ###########THIS VALIDATION LOGIC INSIDE FACT CLASS IS ARBITRARY - NEEDS TO BE FIXED#########################

    def validate(self, network: Network) -> bool:
        """Validate the Fact against its Concept within the given Network."""
        # Step 1: Check if the Concept is part of the Network
        if self.concept not in [rel.target_concept for rel in network.relationships]:
            return False  # Concept not in Network

        # Step 2: If Network is Definition, perform dimensional validation
        if network.network_type == NetworkType.DEFINITION:
            # Find the Hypercube associated with the Concept
            hypercube = self._find_hypercube(network)
            if hypercube:
                return self._validate_dimensions(hypercube)
            else:
                # No Hypercube found; validation depends on your rules
                pass

        # Step 3: Additional validations for other Network types if necessary

        return True  # If all validations pass

    def _find_hypercube(self, network: Network) -> Optional[Hypercube]:
        """Find the Hypercube associated with the Concept in the Network."""
        for rel in network.relationships:
            if rel.source_concept == self.concept and rel.hypercube:
                return rel.hypercube
        return None

    def _validate_dimensions(self, hypercube: Hypercube) -> bool:
        """Validate the Fact's Dimensions against the Hypercube."""
        # Implement your validation logic here
        # For example, check if all required Dimensions are present
        required_dims = set(dim.id for dim in hypercube.dimensions)
        fact_dims = set(dim.id for dim in self.context.dimensions.keys())

        if hypercube.is_closed:
            # Closed Hypercube: Fact must not have Dimensions outside the Hypercube
            if not fact_dims <= required_dims:
                return False

        # Check for "all" or "notAll" arcroles
        if hypercube.all_arcrole == "all":
            # Fact must have all Dimensions in the Hypercube
            if not required_dims <= fact_dims:
                return False

        # Additional dimension/member validation as needed

        return True
    





######################### ReportElementCategorization START ################################

class ElementCategory(Enum):
    CONCEPT = "Concept"
    HYPERCUBE = "HyperCube"
    DIMENSION = "Dimension"
    MEMBER = "*Member"
    ABSTRACT = "*Abstract"
    LINE_ITEMS = "*LineItems"
    GUIDANCE = "*Guidance"
    DEPRECATED = "deprecated"
    LINKBASE = "LinkbaseElement"
    DATE = "DateElement"
    OTHER = "Other"

class ReportElementClassifier:
    LINKBASE_ELEMENTS = [
        'link:part', 'xl:extended', 'xl:arc', 'xl:simple', 
        'xl:resource', 'xl:documentation', 'xl:locator', 
        'link:linkbase', 'link:definition', 'link:usedOn', 
        'link:roleType', 'link:arcroleType'
    ]
    
    DATE_ELEMENTS = [
        'xbrli:instant', 'xbrli:startDate', 'xbrli:endDate', 
        'dei:eventDateTime', 'xbrli:forever'
    ]

    @staticmethod
    def get_substitution_group(concept: Any) -> str:
        return (str(concept.substitutionGroupQname) 
                if concept.substitutionGroupQname else "N/A")

    @staticmethod
    def get_local_type(concept: Any) -> str:
        return (str(concept.typeQname.localName) 
                if concept.typeQname else '')

    @staticmethod
    def check_nillable(concept: Any) -> bool:
        return (concept.nillable == 'true')

    @staticmethod
    def check_duration(concept: Any) -> bool:
        return (concept.periodType == 'duration')

    @classmethod
    def classify(cls, concept: Any) -> ElementCategory:
        qname_str = str(concept.qname)
        sub_group = cls.get_substitution_group(concept)
        local_type = cls.get_local_type(concept)
        nillable = cls.check_nillable(concept)
        duration = cls.check_duration(concept)

        # Initial classification
        category = cls._initial_classify(concept, qname_str, sub_group, 
                                      local_type, nillable, duration)
        
        # Integrated post-classification
        if category == ElementCategory.OTHER:
            category = cls._post_classify_single(concept, qname_str, sub_group)
        
        return category

    @classmethod
    def _initial_classify(cls, concept, qname_str, sub_group, local_type, 
                         nillable, duration) -> ElementCategory:
        # 1. Basic Concept
        if not concept.isAbstract and sub_group == 'xbrli:item':
            return ElementCategory.CONCEPT
        
        # 2. Hypercube [Table]
        if (concept.isAbstract and 
            sub_group == 'xbrldt:hypercubeItem' and
            duration and nillable):
            return ElementCategory.HYPERCUBE
        
        # 3. Dimension [Axis]
        if (concept.isAbstract and 
            sub_group == 'xbrldt:dimensionItem' and 
            duration and nillable):
            return ElementCategory.DIMENSION
        
        # 4. Member [Domain/Member]
        if ((any(qname_str.endswith(suffix) for suffix in ["Domain", "domain", "Member"]) or 
             local_type == 'domainItemType') and 
            duration and nillable):
            return ElementCategory.MEMBER
        
        # 5. Abstract
        if any(qname_str.endswith(suffix) for suffix in [
            "Abstract", "Hierarchy", "RollUp", 
            "RollForward", "Rollforward"
        ]) and concept.isAbstract:
            return ElementCategory.ABSTRACT
        
        # 6. LineItems
        if "LineItems" in qname_str and duration and nillable:
            return ElementCategory.LINE_ITEMS
        
        # 7. Guidance
        if local_type == 'guidanceItemType' or "guidance" in qname_str.lower():
            return ElementCategory.GUIDANCE
        
        # 8. Deprecated
        if "deprecated" in qname_str.lower() or "deprecated" in local_type.lower():
            return ElementCategory.DEPRECATED

        return ElementCategory.OTHER

    @classmethod
    def _post_classify_single(cls, concept, qname_str, sub_group) -> ElementCategory:
        # Rule 1: IsDomainMember -> *Member
        if concept.isDomainMember:
            return ElementCategory.MEMBER
            
        # Rule 2: Abstract -> *Abstract
        if concept.isAbstract:
            return ElementCategory.ABSTRACT
            
        # Rule 3: LinkbaseElement SubstitutionGroups
        if sub_group in cls.LINKBASE_ELEMENTS:
            return ElementCategory.LINKBASE
            
        # Rule 4: Date Elements
        if qname_str in cls.DATE_ELEMENTS:
            return ElementCategory.DATE
            
        return ElementCategory.OTHER



######################### ReportElementCategorization END ################################

######################### OTHER CLASSES (TO consider) START ####################################################

@dataclass
class Entity:
    identifier: str
    scheme: str  # E.g., "http://www.sec.gov/CIK"

@dataclass
class Unit:
    id: str
    measures: List[str]  # E.g., ["iso4217:USD"]


@dataclass
# class Context:
#     id: str
#     period: Period
#     entity: Entity
#     dimensions: Dict[Dimension, Member] = field(default_factory=dict)


@dataclass
class Period:
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    instant_date: Optional[date] = None

    @property
    def is_duration(self) -> bool:
        return self.start_date is not None and self.end_date is not None

    @property
    def is_instant(self) -> bool:
        return self.instant_date is not None


######################### OTHER CLASSES (TO consider) END ####################################################






@dataclass
class FactRelationship:
    """Represents validated relationship between facts"""
    source_fact_id: str
    target_fact_id: str
    relationship_type: str
    network_role: str  # Non-default argument
    context_id: str  # Non-default argument
    order: float  # Non-default argument
    details: Dict[str, str] = field(default_factory=dict)  # Default argument
    validation_details: Dict[str, Any] = field(default_factory=dict)  # Default argument

    def to_dict(self):
        return {
            "source_fact_id": self.source_fact_id,
            "target_fact_id": self.target_fact_id,
            "relationship_type": self.relationship_type,
            **self.details,
        }
    
    def to_cypher(self):
        return super().to_cypher("Fact", self.to_dict())



# A relationship class to capture the dynamic relationship between a Concept and a Hypercube.

@dataclass
class ConceptToHypercube:
    concept: Concept
    # hypercube: Hypercube
    network_id: str  # Network this relationship is valid in


@dataclass
class Relationship:
    source_concept: Concept
    target_concept: Concept
    arcrole: str  # E.g., "parent-child", "summation-item"
    order: Optional[float] = None
    weight: Optional[float] = None  # For calculation relationships
    preferred_label: Optional[str] = None  # For presentation relationships
    # Definition-specific properties:
    # hypercube: Optional[Hypercube] = None
    context_element: Optional[str] = None  # "segment" or "scenario"
    closed: Optional[bool] = None
    usable: Optional[bool] = None



# RELATIONSHIP MANAGER 
@dataclass
class RelationshipManager:
    
    @staticmethod
    def build_presentation_map(facts: List[Fact]) -> Dict[str, List[str]]:
        """Dynamically create a presentation map from facts."""
        presentation_map = defaultdict(list)
        # for fact in facts:
        #     parent_dimension = fact.dimensions.get("parent", "root")
        #     presentation_map[parent_dimension].append(fact.id)
        return dict(presentation_map)

    @staticmethod
    def generate_presentation_links(facts: List[Fact], concepts: List[Concept]) -> List[FactRelationship]:
        """Generate presentation links using the dynamic presentation map."""
        presentation_map = RelationshipManager.build_presentation_map(facts)
        links = [
            FactRelationship(source_fact_id=parent_id, target_fact_id=child_id, relationship_type="presentation")
            for parent_id, child_ids in presentation_map.items()
            for child_id in child_ids
        ]
        return links

    @staticmethod
    def validate_presentation_links(relationships: List[FactRelationship]) -> List[FactRelationship]:
        """Mark relationships as validated."""
        for rel in relationships:
            rel.details["validated"] = True
        return relationships


######################### OTHER CLASSES (TO consider) START ####################################################



# UTILITIES

# Global Export Function - A utility to convert all dataclass objects into Neo4j-compatible Cypher queries:
def export_to_neo4j(nodes: List[object], relationships: List[FactRelationship]) -> str:
    # return "\n".join(node.to_cypher() for node in nodes + relationships if hasattr(node, "to_cypher")for fact in facts:)
    return None





######################### Other Report Elements START ####################################################

class ReportElement:
    """Represents a single report element with all its properties and categorization"""
    pass
# Category
# Concept            12355
# *Abstract           2607
# *Member             2510
# HyperCube            371
# *LineItems           367
# Dimension            298
# LinkbaseElement       42
# Other                 30
# *Guidance              6
# DateElement            5
# deprecated             2
######################### Other Report Elements END ####################################################




######################### VALIDATION FUNCTIONS START #####################################################

def validate_report_hierarchy(report: Report) -> None:
    """Exhaustive validation of the report hierarchy."""
    print("\nEXHAUSTIVE REPORT HIERARCHY VALIDATION")
    print("=" * 50)

    # Base Report Stats
    print("\nReport Base")
    print(f"├→ Report Metadata Keys: {len(report.report_metadata)}")
    print(f"├→ Facts: {len(report.facts)}")
    print(f"├→ Concepts: {len(report.concepts)}")
    print(f"└→ Networks: {len(report.networks)}")

    # Networks
    print("\nReport → Networks")
    total_networks = len(report.networks)
    unique_networks = len(set(network.network_uri for network in report.networks))
    print(f"├→ Total Networks: {total_networks}")
    print(f"└→ Unique Network Names: {unique_networks}")

    # Networks → Hypercubes
    print("\nReport → Networks → Hypercubes")
    total_hypercubes = sum(len(network.hypercubes) for network in report.networks)
    unique_hypercubes = len(set(hypercube.qname for network in report.networks for hypercube in network.hypercubes))
    print(f"├→ Total Hypercubes: {total_hypercubes}")
    print(f"└→ Unique Hypercube Names: {unique_hypercubes}")

    # Networks → Hypercubes → Dimensions
    print("\nReport → Networks → Hypercubes → Dimensions")
    total_dimensions = sum(len(hypercube.dimensions) for network in report.networks for hypercube in network.hypercubes)
    unique_dimensions = len(set(dimension.qname for network in report.networks for hypercube in network.hypercubes for dimension in hypercube.dimensions))
    print(f"├→ Total Dimensions: {total_dimensions}")
    print(f"└→ Unique Dimensions: {unique_dimensions}")

    # Networks → Hypercubes → Concepts
    print("\nReport → Networks → Hypercubes → Concepts")
    total_hypercube_concepts = sum(len(hypercube.concepts) for network in report.networks for hypercube in network.hypercubes)
    unique_hypercube_concepts = len(set(concept.qname for network in report.networks for hypercube in network.hypercubes for concept in hypercube.concepts))
    print(f"├→ Total Hypercube Concepts: {total_hypercube_concepts}")
    print(f"└→ Unique Hypercube Concepts: {unique_hypercube_concepts}")

    # Networks → Hypercubes → Dimensions → Members
    print("\nReport → Networks → Hypercubes → Dimensions → Members")
    total_members = sum(len(dimension.members_dict) for network in report.networks for hypercube in network.hypercubes for dimension in hypercube.dimensions)
    unique_members = len(set(member.qname for network in report.networks for hypercube in network.hypercubes for dimension in hypercube.dimensions for member in dimension.members))
    print(f"├→ Total Dimension Members: {total_members}")
    print(f"└→ Unique Dimension Members: {unique_members}")

    # Networks → Hypercubes → Dimensions → Default Members
    print("\nReport → Networks → Hypercubes → Dimensions → Default Members")
    default_members = set()
    for network in report.networks:
        for hypercube in network.hypercubes:
            for dimension in hypercube.dimensions:
                if dimension.default_member:
                    default_members.add(dimension.default_member.qname)
    print(f"├→ Total Default Members: {len(default_members)}")
    print(f"└→ Unique Default Members: {len(default_members)}")

    # Networks → Hypercubes → Dimensions → Domains
    print("\nReport → Networks → Hypercubes → Dimensions → Domains")
    total_domains = sum(1 for network in report.networks for hypercube in network.hypercubes for dimension in hypercube.dimensions if dimension.domain)
    unique_domains = len(set(dimension.domain.qname for network in report.networks for hypercube in network.hypercubes for dimension in hypercube.dimensions if dimension.domain))
    print(f"├→ Total Domains: {total_domains}")
    print(f"└→ Unique Domains: {unique_domains}")

    # Networks → Concepts
    print("\nReport → Networks → Concepts")
    total_network_concepts = sum(len(network.concepts) for network in report.networks)
    unique_network_concepts = len(set(concept.qname for network in report.networks for concept in network.concepts))
    print(f"├→ Total Concepts in Networks: {total_network_concepts}")
    print(f"└→ Unique Concepts in Networks: {unique_network_concepts}")

    # Facts → Relationships
    print("\nReport → Facts → Relationships")
    print(f"├→ Facts → Concepts: {sum(1 for fact in report.facts if fact.concept)}")
    print(f"├→ Facts → Units: {sum(1 for fact in report.facts if fact.unit_id)}")
    print(f"├→ Facts → Dimensions: {sum(1 for fact in report.facts if fact.dimensions)}")
    print(f"├→ Facts → Context: {sum(1 for fact in report.facts if fact.context_id)}")
    print(f"└→ Facts → Period: {sum(1 for fact in report.facts if fact.period)}")

    # Concept Relationships
    print("\nReport → Concept Relationships")
    print(f"├→ Concepts → Facts: {sum(len(concept.facts) for concept in report.concepts)}")
    print(f"├→ Concepts → Networks: {sum(1 for concept in report.concepts if any(concept in network.concepts for network in report.networks))}")
    print(f"├→ Concepts → Hypercubes: {sum(1 for concept in report.concepts if any(concept in hypercube.concepts for network in report.networks for hypercube in network.hypercubes))}")
    print(f"├→ Concepts → Parents: {sum(1 for concept in report.concepts if concept.presentation_parents)}")
    print(f"└→ Concepts → Children: {sum(len(concept.presentation_children) for concept in report.concepts)}")

######################### VALIDATION FUNCTIONS END #####################################################
