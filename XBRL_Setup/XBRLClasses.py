from __future__ import annotations  # Enable forward references

# dataclasses and typing imports
from dataclasses import dataclass, field, fields
from typing import List, Dict, Optional, Any, Union, Set, Type, Tuple
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


@dataclass
class Neo4jRelationship:
    source: Neo4jNode
    target: Neo4jNode
    rel_type: RelationType

class NodeType(Enum):
    """XBRL node types in Neo4j"""
    COMPANY = "Company"
    FACT = "Fact"
    CONCEPT = "Concept"
    DIMENSION = "Dimension"
    MEMBER = "Member"
    HYPERCUBE = "HyperCube"
    CONTEXT = "Context"
    PERIOD = "Period"
    UNIT = "Unit"           # Added for numeric facts
    NAMESPACE = "Namespace" # Added for prefix management
    LINKBASE = "Linkbase"  # Added for relationships
    RESOURCE = "Resource"  # Added for labels, references
    ABSTRACT = "Abstract"
    LINE_ITEMS = "LineItems"
    GUIDANCE = "Guidance"
    DEPRECATED = "deprecated"
    DATE = "DateElement"
    OTHER = "Other"



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
        pass
        
    @property
    @abstractmethod
    def id(self) -> str:
        pass
        
    @property
    @abstractmethod
    def properties(self) -> Dict[str, Any]:
        pass

    @classmethod
    def from_neo4j(cls, properties: Dict[str, Any]):
        """Create instance from Neo4j properties"""
        # Clean properties and convert "null" to None
        cleaned_props = {
            k: None if v == "null" else v
            for k, v in properties.items()
            if k not in {'id', 'elementId'} and not k.startswith('_')
        }
        
        # Get the constructor parameters
        init_params = {
            k: cleaned_props.get(k)
            for k in cls.__init__.__code__.co_varnames[1:]  # Skip 'self'
            if k in cleaned_props
        }
        
        return cls(**init_params)


######################### CONCEPTS START ####################################################


@dataclass
class Concept(Neo4jNode):
    model_concept: Optional[ModelConcept] = None # The original ModelConcept object
    u_id: Optional[str] = None
    
    # Change init=False to have defaults for Neo4j loading
    qname: Optional[str] = None
    concept_type: Optional[str] = None
    period_type: Optional[str] = None
    namespace: Optional[str] = None
    label: Optional[str] = None
    balance: Optional[str] = None
    type_local: Optional[str] = None    
    
    facts: List[Fact] = field(init=False, default_factory=list)
    # hypercubes: Optional[List[str]] = field(default_factory=list)  # Hypercubes associated in the Definition Network

    def __post_init__(self):
        if self.model_concept is not None:
            # Initialize from XBRL source
            self.u_id = f"{self.model_concept.qname.namespaceURI}:{self.model_concept.qname}"
            self.qname = str(self.model_concept.qname)
            self.concept_type = str(self.model_concept.typeQname) if self.model_concept.typeQname else "N/A"
            self.period_type = self.model_concept.periodType or "N/A"
            self.namespace = self.model_concept.qname.namespaceURI.strip()
            self.label = self.model_concept.label(lang="en")            
            self.balance = self.model_concept.balance
            self.type_local = self.model_concept.baseXsdType
        elif not self.u_id:
            raise ValueError("Either model_concept or properties must be provided")


    def __hash__(self):
        # Use a unique attribute for hashing, such as qname
        return hash(self.u_id)

    def __eq__(self, other):
        # Ensure equality is based on the same attribute used for hashing
        if isinstance(other, Concept):
            return self.u_id == other.u_id
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
        """u_id for Neo4j MERGE"""
        return self.u_id
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Actual node properties in Neo4j"""
        return {
            "qname": self.qname,
            "u_id": self.id, # this returns the u_id
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
    testing: bool = field(default=True)  # Add testing flag as configurable

    model_xbrl: ModelXbrl = field(init=False, repr=False)
    report_metadata: Dict[str, object] = field(init=False, default_factory=dict)
    
    # Core collections
    concepts: List[Concept] = field(init=False, default_factory=list, repr=False)
    abstracts: List[AbstractConcept] = field(init=False, default_factory=list, repr=False) # Used in Presentation Class
    periods: List[Period] = field(init=False, default_factory=list, repr=False)
    units: List[Unit] = field(init=False, default_factory=list, repr=False)
    facts: List[Fact] = field(init=False, default_factory=list, repr=False)
    dimensions: List[Dimension] = field(init=False, default_factory=list, repr=False)

    _concept_lookup: Dict[str, Concept] = field(init=False, default_factory=dict, repr=False)
    _abstract_lookup: Dict[str, AbstractConcept] = field(init=False, default_factory=dict, repr=False)
    
     # TODO
     # networks: List[Network] = field(init=False, default_factory=list, repr=False)
     
    def __post_init__(self):
        self.load_xbrl()
        self.extract_report_metadata()
        self.populate_common_nodes()  # First handle common nodes
        self.populate_report_nodes()  # Then handle report-specific nodes

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


    def populate_common_nodes(self):
        """Build and sync common nodes (Concepts, Periods, Units) with Neo4j"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        # Build common nodes from XBRL
        self._build_concepts() # 1. Build concepts first
        self._build_periods()   # 2. Build periods
        self._build_units()    # 3. Build units
        
        # Upload to Neo4j only common nodes first
        self._export_nodes([self.concepts, self.periods, self.units], testing=False)
        
        # Load complete set from Neo4j
        self.concepts = self.neo4j.load_nodes_as_instances(NodeType.CONCEPT, Concept)
        self.periods = self.neo4j.load_nodes_as_instances(NodeType.PERIOD, Period)
        self.units = self.neo4j.load_nodes_as_instances(NodeType.UNIT, Unit)
        
        print(f"Loaded common nodes from Neo4j: {len(self.concepts)} concepts, {len(self.periods)} periods, {len(self.units)} units")
        self._concept_lookup = {node.id: node for node in self.concepts} 


    def populate_report_nodes(self):
        """Build and export report-specific nodes (Facts, Dimensions)"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
  
        self._build_facts()         # 4. Build facts
        self._build_networks()    # 5. Build networks, dimensions and hierarchies
        
        # Upload to Neo4j report-specific nodes - # Testing=False since otherwise it will clear the db
        self._export_nodes([self.facts], testing=False) 

        # Define relationship types to export
        rel_types = [(Fact, Concept, RelationType.HAS_CONCEPT),
                     (Fact, Unit, RelationType.HAS_UNIT),
                     (Fact, Period, RelationType.HAS_PERIOD)]
        
        self._export_relationships(rel_types)        
        print(f"Built report nodes: {len(self.facts)} facts")


    def _build_concepts(self):
        """Build concept objects from the model."""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        self.concepts = []
        
        # Explanation: 'model_xbrl.factsByQname.keys()' has concepts' qnames so we use fact.concept from model_xbrl.factsInInstance to fetch the concepts
        unique_concepts = {fact.concept for fact in self.model_xbrl.factsInInstance if fact.concept.qname in self.model_xbrl.factsByQname.keys()}
        self.concepts = [Concept(concept) for concept in unique_concepts]
        
        print(f"Built {len(self.concepts)} unique concepts") 


    def _build_units(self):
        """Build unique unit objects from the model."""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
                
        units_dict = {}  # Use dict for uniqueness
        for fact in self.model_xbrl.factsInInstance:
            if hasattr(fact, 'unitID') and fact.unitID:  # Only check for unitID
                try:
                    unit = Unit(model_fact=fact)
                    if unit.string_value or unit.unit_reference:  # Only add if we have some identifying info
                        units_dict[unit.id] = unit
                except Exception as e:
                    print(f"Error processing unit for fact {fact.id}: {e}")
        
        self.units = list(units_dict.values())
        print(f"Built {len(self.units)} unique units") 


    def _build_periods(self) -> None:
        """Build unique period objects from contexts"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        periods_dict = {}  # Use dict for uniqueness
        
        for ctxt_id, context in self.model_xbrl.contexts.items():
            try:
                # Determine period type
                period_type = ("instant" if getattr(context, "isInstantPeriod", False)
                            else "duration" if getattr(context, "isStartEndPeriod", False)
                            else "forever")
                
                # Extract dates
                start_date = None
                end_date = None
                
                if period_type == "instant":
                    start_date = context.instantDatetime.strftime('%Y-%m-%d')
                elif period_type == "duration":
                    start_date = context.startDatetime.strftime('%Y-%m-%d')
                    end_date = context.endDatetime.strftime('%Y-%m-%d')
                    
                # Create period
                period = Period(
                    period_type=period_type,
                    start_date=start_date,
                    end_date=end_date,
                    context_ids=[ctxt_id]
                )
                
                # Add to dict using _id as key for uniqueness
                if period.u_id in periods_dict:
                    # periods_dict[period.u_id].merge_context(ctxt_id)
                    # print(f"Merged context {ctxt_id} into existing period {period.u_id}")
                    pass        
                else:
                    periods_dict[period.u_id] = period
                    
            except Exception as e:
                print(f"Error processing context {ctxt_id}: {e}")
        
        self.periods = list(periods_dict.values())
        print(f"Built {len(self.periods)} unique periods")

    def _build_facts(self):
        """Build facts with two-way concept relationships"""
        for model_fact in self.model_xbrl.factsInInstance:
            fact = Fact(model_fact=model_fact)

            model_concept = model_fact.concept
            concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"
            concept = self._concept_lookup.get(concept_id)
            if not concept: 
                print(f"Warning: No concept found for fact {fact.fact_id}")
                continue
            else:
               # Only linking concept.facts since fact.concept = concept done in export_            
               # # Also this is not done for Neo4j nodes but for internal classes only                  
                concept.add_fact(fact) 
            
            self.facts.append(fact)
        print(f"Built {len(self.facts)} unique facts")    


    # 1. Build networks - Also builds hypercubes in networks with isDefinition = True
    def _build_networks(self):
        """Builds networks specific to this filing instance. Networks are report-specific sections."""
        
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
    
        # Create networks for each section of this specific report (e.g., Balance Sheet, Income Statement, Notes)
        self.networks = [
            Network(
                model_xbrl = self.model_xbrl,
                name =' - '.join(parts[2:]), 
                network_uri=uri,
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
            # Create Presentation Class
            if network.isPresentation:
                network.presentation = Presentation(
                    network_uri=network.network_uri,
                    model_xbrl=self.model_xbrl,
                    report=self  # Pass report reference to access/create concepts and abstracts
            )
            
                
        # 3. Adding hypercubes after networks are complete which in turn builds dimensions
        for network in self.networks:
            network.add_hypercubes(self.model_xbrl)
            for hypercube in network.hypercubes:                
                hypercube._link_hypercube_concepts(self.concepts, self.abstracts)

    def _export_nodes(self, collections: List[List[Neo4jNode]], testing: bool = False):
        """Export specified collections of nodes to Neo4j"""
        try:
            if testing:
                self.neo4j.clear_db()
            
            # Always ensure indexes/constraints exist
            self.neo4j.create_indexes()
            
            nodes = []
            for collection in collections:
                if collection:
                    print(f"Adding {len(collection)} {type(collection[0]).__name__} nodes")
                    nodes.extend(collection)
            
            if nodes:
                self.neo4j.merge_nodes(nodes)
                print("Export completed successfully")
                
        except Exception as e:
            raise RuntimeError(f"Export to Neo4j failed: {e}")
        

    def _export_relationships(self, rel_types: List[Tuple[Type[Neo4jNode], Type[Neo4jNode], RelationType]]) -> None:
        """Export relationships based on node type pairs and explicit relationship types"""
        relationships = []
        
        # Here source is always assumed to be a Fact instance
        def create_temp_target(source, target_type):
            """Create a temporary target instance based on the source instance and target type."""
            if target_type == Concept:
                return Concept(model_concept=source.model_fact.concept)
            elif target_type == Unit:
                return Unit(model_fact=source.model_fact)
            elif target_type == Period:
                context = source.model_fact.context
                # Use exact same logic as _build_periods
                period_type = ("instant" if getattr(context, "isInstantPeriod", False)
                            else "duration" if getattr(context, "isStartEndPeriod", False)
                            else "forever")
                return Period(
                    period_type=period_type,
                    start_date=context.instantDatetime.strftime('%Y-%m-%d') if context.isInstantPeriod 
                        else context.startDatetime.strftime('%Y-%m-%d'),
                    end_date=context.endDatetime.strftime('%Y-%m-%d') 
                        if context.isStartEndPeriod else None
                )
            return None

        for source_type, target_type, rel_type in rel_types:
            try:
                collection = getattr(self, f"{target_type.__name__.lower()}s") # such as self.concepts, self.units etc - note lower()
                target_lookup = {node.id: node for node in collection} # Mapping of actual class instances
                
                for source in getattr(self, f"{source_type.__name__.lower()}s"):
                    if temp_target := create_temp_target(source, target_type):
                        
                        # target is the actual class instances
                        if target := target_lookup.get(temp_target.id):
                            relationships.append((source, target, rel_type))
                            # Sets Fact instance to point to the corresponding target instance ((e.g., concept, unit, period))
                            setattr(source, target_type.__name__.lower(), target) # Like fact.concept etc
                            
            except (AttributeError, KeyError) as e:
                print(f"Skipping {source_type.__name__} -> {target_type.__name__}: {e}")
        
        if relationships:
            self.neo4j.merge_relationships(relationships)
                        

############################### Report Class END #######################################################

############################### Presentation Class START #######################################################

@dataclass
class PresentationNode:
    """
    Node in the presentation hierarchy.
    Stores structural information without duplicating concept data.
    """
    concept_id: str
    order: float
    level: int
    children: List[str] = field(default_factory=list)  # List of child concept_ids
    concept: Optional[Union[Concept, AbstractConcept]] = None  # Actual Concept Instance (Concept or AbstractConcept)
    
    def __hash__(self) -> int:
        return hash(self.concept_id)

@dataclass
class Presentation:
    """
    Manages presentation relationships between concepts using a flat dictionary structure.
    Links to existing Concept/AbstractConcept instances in Report.
    """
    network_uri: str
    model_xbrl: ModelXbrl
    report: Report
    
    nodes: Dict[str, PresentationNode] = field(init=False, default_factory=dict)
    
    def __post_init__(self) -> None:
        """Initialize presentation hierarchy"""
        try:
            self._build_hierarchy()
        except Exception as e:
            raise ValueError(f"Failed to build presentation hierarchy: {e}")
    
    def _build_hierarchy(self) -> None:
        """Build presentation hierarchy and create abstract concepts as needed"""
        rel_set = self.model_xbrl.relationshipSet(XbrlConst.parentChild, self.network_uri)
        if not rel_set:
            return
            
        # First pass: Create nodes and track parent-child relationships
        parent_child_map: Dict[str, List[tuple[str, float]]] = {}  # parent_id -> [(child_id, order)]
        
        for rel in rel_set.modelRelationships:
            parent_id = f"{rel.fromModelObject.qname.namespaceURI}:{rel.fromModelObject.qname}"
            child_id = f"{rel.toModelObject.qname.namespaceURI}:{rel.toModelObject.qname}"
            
            # Handle abstract concepts
            for model_obj in (rel.fromModelObject, rel.toModelObject):
                if model_obj.isAbstract:
                    self._ensure_abstract_exists(model_obj)
            
            # Track parent-child relationship with order
            if parent_id not in parent_child_map:
                parent_child_map[parent_id] = []
            parent_child_map[parent_id].append((child_id, rel.order or 0))
        
        # Second pass: Build nodes with correct levels
        self._build_nodes(parent_child_map)
    
    # Not sure what purpose it solves?
    def _ensure_abstract_exists(self, model_concept: ModelConcept) -> None:
        """Create AbstractConcept if not already exists"""
        concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"

        if (concept_id not in self.report._concept_lookup and 
            concept_id not in self.report._abstract_lookup):
            try:
                abstract = AbstractConcept(model_concept)
                self.report.abstracts.append(abstract)
                self.report._abstract_lookup[abstract.id] = abstract  # Using .id property
            except Exception as e:
                raise ValueError(f"Failed to create AbstractConcept {concept_id}: {e}")
        
    def _build_nodes(self, parent_child_map: Dict[str, List[tuple[str, float]]]) -> None:
        """Build nodes with correct levels and children"""
        def build_node(concept_id: str, level: int) -> None:
            if concept_id not in self.nodes:
                children = parent_child_map.get(concept_id, [])
                children.sort(key=lambda x: x[1])
                
                # Get concept instance from report
                concept_instance = self.get_concept(concept_id)
                
                # Create node with concept instance
                self.nodes[concept_id] = PresentationNode(
                    concept_id=concept_id,
                    order=1,
                    level=level,
                    children=[child_id for child_id, _ in children],
                    concept=concept_instance  # Add concept instance
                )
                
                # Process children
                for child_id, order in children:
                    build_node(child_id, level + 1)
                    self.nodes[child_id].order = order
        
        # Find and process root nodes
        all_parents = set(parent_child_map.keys())
        all_children = {child for children in parent_child_map.values() 
                    for child, _ in children}
        root_ids = all_parents - all_children
        
        for i, root_id in enumerate(sorted(root_ids), 1):
            build_node(root_id, 1)
            self.nodes[root_id].order = i


    def get_node(self, concept_id: str) -> Optional[PresentationNode]:
        """Get presentation node by concept_id"""
        return self.nodes.get(concept_id)
    
    def get_concept(self, concept_id: str) -> Optional[Union[Concept, AbstractConcept]]:
        """Get concept instance for a node using u_id"""
        return (self.report._concept_lookup.get(concept_id) or 
                self.report._abstract_lookup.get(concept_id))
    
    def get_children(self, node: PresentationNode) -> List[PresentationNode]:
        """Get child nodes for a given node"""
        return [self.nodes[child_id] for child_id in node.children]
    
    @property
    def roots(self) -> Set[PresentationNode]:
        """Get root nodes (parents that are not children of any other concept)"""
        all_parents = {concept_id for concept_id, node in self.nodes.items() 
                      if node.children}
        all_children = {child_id for node in self.nodes.values() 
                       for child_id in node.children}
        root_ids = all_parents - all_children
        return {self.nodes[concept_id] for concept_id in root_ids}

############################### Presentation Class END #######################################################

############################### Abstract Class START #######################################################

@dataclass
class AbstractConcept(Concept):
    def __post_init__(self):
        super().__post_init__()
        if not self.model_concept.isAbstract:
            raise ValueError("Cannot create AbstractConcept from non-abstract concept")
    
    @property
    def is_abstract(self) -> bool:
        return True

############################### Abstract Class END #######################################################


############################### Hypercube Class START #######################################################

@dataclass
class Hypercube:
    """Represents a hypercube (table) in an XBRL definition network"""
    model_xbrl: ModelXbrl
    hypercube_item: Any  # hypercube modelConcept, ends with 'Table' (Target of 'all' relationship)    
    network_uri: str     # Reference back to parent network
    dimensions: List[Dimension] = field(init=False) # Dimensions related to the hypercube
    concepts: List[Concept] = field(init=False)  # Concepts related to the hypercube
    abstracts: List[Concept] = field(init=False)  # These are Lineitems, abstracts typically used to organize concepts
    lineitems: List[Concept] = field(init=False)  # These are Lineitems, abstracts typically used to organize concepts
    is_all: bool = field(init=False)  # True for 'all', False for 'notAll'
    closed: bool = field(init=False)  # Value of closed attribute

    def _get_hypercube_properties(self) -> tuple[bool, bool]:
        """Get hypercube relationship type (is_all) and closed attribute.
        Returns: (is_all, closed)"""
        # Check for 'all' relationship
        all_rels = self.model_xbrl.relationshipSet(XbrlConst.all, self.network_uri).modelRelationships
        for rel in all_rels:
            if rel.toModelObject is not None and rel.toModelObject == self.hypercube_item:
                return True, getattr(rel, 'closed', 'false').lower() == 'true'  # Convert to bool
        
        # Check for 'notAll' relationship
        not_all_rels = self.model_xbrl.relationshipSet(XbrlConst.notAll, self.network_uri).modelRelationships
        for rel in not_all_rels:
            if rel.toModelObject is not None and rel.toModelObject == self.hypercube_item:
                return False, getattr(rel, 'closed', 'false').lower() == 'true'  # Convert to bool
        
        raise ValueError(f"Hypercube {self.hypercube_item.qname} has neither 'all' nor 'notAll' relationship")    

    def __post_init__(self):
        """Initialize derived attributes from hypercube_item"""
        if not (hasattr(self.hypercube_item, 'isHypercubeItem') and 
                self.hypercube_item.isHypercubeItem):
            raise ValueError("Object must be a hypercube item")
            
        self.qname = self.hypercube_item.qname
        self.dimensions = [] 
        self.concepts = []  # Initialize concepts list here
        self.abstracts = []  # Initialize abstracts list here
        self.lineitems = []  # Initialize lineitems list here

        self.is_all, self.closed = self._get_hypercube_properties()
        self._build_dimensions()


    def _build_dimensions(self) -> None:
        """Build dimension objects from model_xbrl matching this hypercube"""
        
        hc_dim_rel_set = self.model_xbrl.relationshipSet(XbrlConst.hypercubeDimension, self.network_uri)
        if not hc_dim_rel_set: return
            
        relationships = hc_dim_rel_set.fromModelObject(self.hypercube_item)
        if not relationships: return
            
        # Get Target of 'hypercubeDimension' relationship
        for rel in relationships:
            dim_object = rel.toModelObject
            if dim_object is None: continue
            
            try:
                dimension = Dimension(
                    model_xbrl=self.model_xbrl,
                    dimension=dim_object)
                self.dimensions.append(dimension)
            
            except Exception as e: continue

    # Get all concepts related to a hypercube: All dimensions in a hypercube apply to all concepts in that hypercube (as per the specification)
    def _link_hypercube_concepts(self, report_concepts: List[Concept], report_abstracts: List[AbstractConcept]) -> None:
        all_set = self.model_xbrl.relationshipSet(XbrlConst.all, self.network_uri)
        not_all_set = self.model_xbrl.relationshipSet(XbrlConst.notAll, self.network_uri)
        domain_member = self.model_xbrl.relationshipSet(XbrlConst.domainMember, self.network_uri)
        
        def collect_domain_members(concept):
            if concept is not None:
                if not concept.isAbstract:
                    # Find matching concept in report_concepts
                    concept_id = f"{concept.qname.namespaceURI}:{concept.qname}"
                    matching_concept = next( (c for c in report_concepts if c.id == concept_id), None)
                    
                    if matching_concept:
                        self.concepts.append(matching_concept)
                else:
                    # Abstracts found in this Hypercube; storing it here in case it is needed
                    abstract_id = f"{concept.qname.namespaceURI}:{concept.qname}"
                    matching_abstract = next( (a for a in report_abstracts if a.id == abstract_id), None)
                    if matching_abstract:
                        self.abstracts.append(matching_abstract)
                    else:
                        # Lineitems found in this Hypercube; storing it here in case it is needed
                        self.lineitems.append(concept)
                        # Here we could instead add it to report.abstracts but those are for Presentation network and not this hypercube

                # Recursively collect domain members
                for member_rel in domain_member.fromModelObject(concept):
                    collect_domain_members(member_rel.toModelObject)
                
        
        # Process 'all' relationships
        if all_set:
            for rel in all_set.modelRelationships:
                if (rel.toModelObject is not None and 
                    rel.toModelObject == self.hypercube_item):
                    collect_domain_members(rel.fromModelObject)

        # Process 'notAll' relationships - Not 100% sure about this logic but SEC anyway forbids negative (notAll) hypercubes        
        
        if not_all_set:
            for rel in not_all_set.modelRelationships:
                if (rel.toModelObject is not None and 
                    rel.toModelObject == self.hypercube_item):  # Check hypercube as target
                    collect_domain_members(rel.fromModelObject)  # Process from primary item


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
    """Represents a specific section of the report (e.g., 'Balance Sheet', 'Income Statement', 'Notes').
    Each network has a unique URI like 'http://company.com/role/BALANCESHEET'"""

    model_xbrl: ModelXbrl
    name: str
    network_uri: str
    id: str
    category: str # Note you can simply use "network.networkType" to get type of network
    concepts: List[Concept] = field(init=False, default_factory=list) 

    relationship_sets: List[str] = field(default_factory=list) # check if this is needed
    hypercubes: List[Hypercube] = field(init=False, default_factory=list)
    presentation: Optional[Presentation] = field(init=False, default=None)

    
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
        """Create indexes and constraints for all node types if they don't exist"""
        try:
            with self.driver.session() as session:
                # Get existing constraints
                existing_constraints = {
                    constraint['name']: constraint['labelsOrTypes'][0]
                    for constraint in session.run("SHOW CONSTRAINTS").data()
                }
                
                # Create missing constraints
                for node_type in NodeType:
                    constraint_name = f"constraint_{node_type.value.lower()}_id_unique"
                    
                    # Only create if it doesn't exist
                    if constraint_name not in existing_constraints:
                        session.run(f"""
                        CREATE CONSTRAINT {constraint_name}
                        FOR (n:`{node_type.value}`)
                        REQUIRE n.id IS UNIQUE
                        """)
                        # print(f"Created constraint for {node_type.value}")
                    else:
                        # print(f"Constraint for {node_type.value} already exists")
                        pass
                        
        except Exception as e:
            raise RuntimeError(f"Failed to create indexes: {e}")
            
    def merge_nodes(self, nodes: List[Neo4jNode], batch_size: int = 1000) -> None:
        """Merge nodes into Neo4j database with batching"""
        if not nodes:
            return
            
        try:
            with self.driver.session() as session:
                skipped_nodes = []
                
                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i + batch_size]
                    
                    for node in batch:
                        # Skip nodes with null IDs
                        if node.id is None:  # This is correct - uses the property
                            skipped_nodes.append(node)
                            continue
                            
                        # Exclude id from properties
                        properties = {
                            k: (v if v is not None else "null")
                            for k, v in node.properties.items()
                            if k != 'id'
                        }
                        
                        query = f"""
                        MERGE (n:{node.node_type.value} {{id: $id}})
                        ON CREATE SET n += $properties
                        ON MATCH SET n += $properties
                        """
                        
                        session.run(query, {
                            "id": node.id,  # This is correct - uses the property
                            "properties": properties
                        })
                
                if skipped_nodes:
                    print(f"Warning: Skipped {len(skipped_nodes)} nodes with null IDs")
                    print("First few skipped nodes:")
                    for node in skipped_nodes[:3]:
                        print(f"Node type: {node.node_type.value}, Properties: {node.properties}")
                        
        except Exception as e:
            raise RuntimeError(f"Failed to merge nodes: {e}")


    def merge_relationships(self, relationships: List[Tuple[Neo4jNode, Neo4jNode, RelationType]]) -> None:
        """Export relationships to Neo4j"""
        with self.driver.session() as session:
            for source, target, rel_type in relationships:
                session.run(f"""
                    MATCH (s {{id: $source_id}})
                    MATCH (t {{id: $target_id}})
                    MERGE (s)-[r:{rel_type.value}]->(t)
                """, {
                    "source_id": source.id,
                    "target_id": target.id
                })

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


######################### Neo4j Setup END #####################################################




#############################FACT CLASS START########################################
@dataclass
class Fact(Neo4jNode):
    model_fact: ModelFact
    
    # Globally unique fact identifier
    u_id: str = field(init=False)        # Globally u_id (URI + UUID)

    # Fact properties
    qname: str = field(init=False)  # Its 'concept' name
    fact_id: str = field(init=False)   # Original fact ID from the XBRL document (e.g., f-32)
    value: str = field(init=False)    
    context_id: str = field(init=False)    
    decimals: Optional[int] = field(init=False, default=None)
            
    # To Link:
    concept: Optional[Concept] = field(init=False, default=None)
    unit: Optional[Unit] = field(init=False, default=None)
    period: Optional[Period] = field(init=False, default=None)
 
    # TODO: Dimension properties - These are all likley incorrect - need to check
    dimensions: Optional[List[Dimension]] = field(init=False, default_factory=list)
    members: Optional[List[Member]] = field(init=False, default_factory=list)
    
    def __post_init__(self):
        """Initialize all fields from model_fact after dataclass creation"""
        if not isinstance(self.model_fact, ModelFact):
            raise TypeError("model_fact must be ModelFact type")
            
        # Globally unique fact identifier
        self.u_id = self._generate_unique_fact_id()

        # Fact properties
        self.qname = str(self.model_fact.qname)
        self.fact_id = self.model_fact.id # Only specific to this report like f-32
        self.value = None if self.model_fact.isNil else (self.model_fact.sValue if self.model_fact.isNumeric else self._extract_text(self.model_fact.value))
        self.context_id = self.model_fact.contextID                        
        self.decimals = self.model_fact.decimals        
 
        # All Links to other Nodes
        # TODO: Instead of linking to XBRL concept, link to actual  class
        # self.concept = self.model_fact.concept 
        # self.unit = self.model_fact.unitID
        # self._set_period()
        # self._set_dimensions() # TODO: Looks like its only fetching 1 member per dimensions

    @property
    def is_nil(self) -> bool:
        """Check if the fact is nil."""
        return self.model_fact.isNil
    
    @property
    def is_numeric(self) -> bool:
        """Check if the fact is numeric."""
        return self.model_fact.isNumeric    

    def _generate_unique_fact_id(self) -> str:
        components = [
            str(self.model_fact.modelDocument.uri),    # Which report
            str(self.model_fact.qname),                # Which concept
            str(self.model_fact.contextID),            # When (period) and who (entity)
            str(self.model_fact.unitID) if hasattr(self.model_fact, 'unitID') else None,  # In what unit (if numeric)
            str(self.model_fact.id)                    # Original fact ID to handle duplicates within same report
        ]
        return "_".join(filter(None, components))


    @staticmethod
    def _extract_text(value: str) -> str:
        """Extract text from HTML/XML content"""
        return re.sub('<[^>]+>', '', html.unescape(value)) if '<' in value and '>' in value else value

    # To be Used when Linking to Period Node
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

    # To be Used when Linking to Dimension and Member Nodes
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

    # def __repr__(self) -> str:
    #     """Match ModelObject's repr format"""
    #     return f"Fact[{self.concept}, {self.value}, context {self.context_id}]"

    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        """Define the Neo4j node type"""
        return NodeType.FACT
        
    @property
    def id(self) -> str:
        """Unique identifier for Neo4j"""
        return self.u_id
            
    @property
    def properties(self) -> Dict[str, Any]:
        """Properties for Neo4j node"""
        return {
            "id": self.id,  # Add this line to ensure id is used for MERGE
            "u_id": self.u_id,  # Keep this for reference
            "qname": self.qname,
            "fact_id": self.fact_id,
            "value": self.value,
            "context_id": self.context_id,
            "decimals": self.decimals,
            "is_nil": self.is_nil,
            "is_numeric": self.is_numeric,
            # References to other nodes (will be used for relationships)
            "concept_ref": str(self.model_fact.concept.qname) if self.model_fact.concept is not None else None,
            "unit_ref": self.unit if self.unit is not None else None,
            "period_ref": self.period if self.period is not None else None,
            # Optional dimension info
            "dimensions": self.dimensions if self.dimensions is not None else None,
            "members": self.members if self.members is not None else None
        }


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



# @dataclass
# class Context:
#     id: str
#     period: Period
#     entity: Entityƒç
#     dimensions: Dict[Dimension, Member] = field(default_factory=dict)


######################### Period Class START ####################################################

@dataclass
class Period(Neo4jNode):
    period_type: str  # Required field, no default
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    # context_ids: List[str] = field(default_factory=list)
    context_ids: Optional[List[str]] = field(default_factory=list)  # Optional, defaults to an empty list
    u_id: str = field(init=False)

    def __post_init__(self):
        if self.period_type == "duration" and not (self.start_date and self.end_date):
            raise ValueError("Duration periods must have both start and end dates")
        if self.period_type == "instant" and not self.start_date:
            raise ValueError("Instant periods must have a start date")
        self.generate_id()

    def __hash__(self):
        return hash(self.u_id)

    def __eq__(self, other):
        if isinstance(other, Period):
            return self.u_id == other.u_id
        return False

    @property
    def is_duration(self) -> bool:
        return self.start_date is not None and self.end_date is not None

    @property
    def is_instant(self) -> bool:
        return self.start_date is not None and self.end_date is None

    def generate_id(self):
        """Generate a unique ID for the period."""
        id_parts = [self.period_type]
        if self.start_date:
            id_parts.append(self.start_date)
        if self.end_date:
            id_parts.append(self.end_date)
        self.u_id = "_".join(id_parts)

    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        return NodeType.PERIOD
        
    @property
    def id(self) -> str:
        return self.u_id
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "u_id": self.id,# This returns u_id
            "period_type": self.period_type,
            "start_date": self.start_date,
            "end_date": self.end_date
            # "context_ids": self.context_ids # TODO: Add this back in relation to Facts but after adding report_metadata
        }

    def merge_context(self, context_id: str) -> None:
        """Add a context ID if it's not already present"""
        if context_id not in self.context_ids:
            self.context_ids.append(context_id)

######################### Period END ####################################################



######################### Unit Class START ####################################################


@dataclass
class Unit(Neo4jNode):
    """ Units are uniquely identified by their string_value (e.g. 'iso4217:USD', 'shares').
    Non-numeric facts have no unit information and as such excluded from Unit nodes."""
        
    model_fact: Optional[ModelFact] = None
    u_id: Optional[str] = None
    
    # All these will be set in post_init
    string_value: Optional[str] = None
    is_divide: Optional[bool] = None
    unit_reference: Optional[str] = None
    registry_id: Optional[str] = None
    is_simple_unit: Optional[bool] = None
    item_type: Optional[str] = None
    namespace: Optional[str] = None
    status: Optional[str] = None

    def __post_init__(self):
        """Process the model_fact to initialize all unit attributes"""
        if self.model_fact is None:  # Skip if loading from Neo4j
            return
        
        unit = getattr(self.model_fact, 'unit', None)
        self.is_divide = getattr(unit, "isDivide", None)
        self.string_value = getattr(unit, "stringValue", None)
        self.unit_reference = self._normalize_unit_id(self.model_fact.unitID)
        
        # Process UTR entries
        utr_entry = next(iter(self.model_fact.utrEntries), None) if self.model_fact.utrEntries else None
        self.registry_id = getattr(utr_entry, "id", None)
        self.is_simple_unit = getattr(utr_entry, "isSimple", None)
        self.item_type = getattr(utr_entry, "itemType", None)
        self.namespace = getattr(utr_entry, "nsUnit", None)
        self.status = getattr(utr_entry, "status", None)
        
        self.u_id = self.generate_uid() # UTR ID + String Value

    def generate_uid(self):
        # Defensive cleaning - handle any possible input
        clean_ns = str(self.namespace).strip() if self.namespace is not None else ""
        clean_val = str(self.string_value).strip() if self.string_value is not None else ""
        
        # If we have both, combine them
        if clean_ns and clean_val:
            return f"{clean_ns}_{clean_val}"
        # If we only have value, return it
        elif clean_val:
            return clean_val
        # If neither, return None
        return None
            

    def __hash__(self):
        """Enable using Unit objects in sets and as dict keys"""
        return hash(self.u_id)

    def __eq__(self, other):
        """Enable comparison between Unit objects"""
        if isinstance(other, Unit):
            return self.u_id == other.u_id
        return False

    @staticmethod
    def _normalize_unit_id(unit_id: Any) -> Optional[str]:
        if not unit_id:
            return None
        if isinstance(unit_id, str) and unit_id.startswith("u-"):
            return unit_id
        if hasattr(unit_id, "id"):
            return f"u-{unit_id.id}"
        return f"u-{abs(hash(str(unit_id))) % 10000}"

    @property
    def is_simple(self) -> bool:
        """Check if the unit is a simple unit based on registry data"""
        return bool(self.is_simple_unit)
    
    @property
    def is_registered(self) -> bool:
        """Check if the unit is registered in UTR"""
        return self.registry_id is not None
    
    @property
    def is_active(self) -> bool:
        """Check if the unit is active based on status"""
        return self.status == "active" if self.status else False

    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        """Define the Neo4j node type"""
        return NodeType.UNIT
        
    @property
    def id(self) -> str:
        """u_id for Neo4j"""
        return self.u_id
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Actual node properties in Neo4j"""
        return {
            "id": self.id,
            "name": self.string_value,  # Using string_value as name
            "is_divide": self.is_divide,
            "is_simple_unit": self.is_simple_unit,
            "item_type": self.item_type,
            "namespace": self.namespace,
            "registry_id": self.registry_id,
            "status": self.status,
            # "string_value": self.string_value,
            "u_id": self.u_id,
            "unit_reference": self.unit_reference
        }

 
    def __repr__(self) -> str:
        """String representation of the Unit"""
        return f"Unit(id={self.id}, type={self.item_type or 'unknown'})"  # Changed self._id to self.id
    
    
######################### Unit Class END ####################################################


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



######################### Counting Function START #####################################################

def count_report_hierarchy(report: Report) -> None:
    """Exhaustive validation of the report hierarchy."""
    print("\nREPORT ELEMENT COUNT BY HIERARCHY")
    print("=" * 50)

    # Base Report Stats
    print("\nReport Base")
    print(f"├→ Report Metadata Keys: {len(report.report_metadata)}")
    print(f"├→ Facts: {len(report.facts)}")
    print(f"├→ Concepts: {len(report.concepts)}")
    print(f"├→ Abstracts: {len(report.abstracts)}")
    print(f"├→ Periods: {len(report.periods)}")
    print(f"├→ Units: {len(report.units)}")
    print(f"└→ Networks: {len(report.networks)}")


    # Networks by Category
    print("\nReport → Networks → Categories")
    network_categories = {}
    for network in report.networks:
        network_categories[network.category] = network_categories.get(network.category, 0) + 1
    for category, count in sorted(network_categories.items()):
        print(f"├→ {category}: {count}")
    print(f"└→ Total Categories: {len(network_categories)}")

    # Networks by Type (network.network_type)
    print("\nReport → Networks → Types")
    network_types = {}
    for network in report.networks:
        network_types[network.networkType] = network_types.get(network.networkType, 0) + 1
    for network_type, count in sorted(network_types.items()):
        print(f"├→ {network_type}: {count}")
    print(f"└→ Total Types: {len(network_types)}")

    # DifferentNetworks (.isPresentation, .isCalculation, .isDefinition)
    print("\nReport → Networks")
    total_networks = len(report.networks)
    presentation_networks = sum(1 for network in report.networks if network.isPresentation)
    calculation_networks = sum(1 for network in report.networks if network.isCalculation)
    definition_networks = sum(1 for network in report.networks if network.isDefinition)
    print(f"├→ Total Networks: {total_networks}")
    print(f"├→ Presentation Networks: {presentation_networks}")
    print(f"├→ Calculation Networks: {calculation_networks}")
    print(f"└→ Definition Networks: {definition_networks}")




    # Presentation Hierarchies
    print("\nReport → Networks → Presentations")
    presentations = [network.presentation for network in report.networks if network.presentation]
    total_presentation_nodes = sum(len(p.nodes) for p in presentations)
    root_nodes = sum(len(p.roots) for p in presentations)
    print(f"├→ Total Presentations: {len(presentations)}")
    print(f"├→ Total Nodes: {total_presentation_nodes}")
    print(f"└→ Root Nodes: {root_nodes}")

    # Networks → Hypercubes
    print("\nReport → Networks → Hypercubes")
    total_hypercubes = sum(len(network.hypercubes) for network in report.networks)
    unique_hypercubes = len({hypercube.qname for network in report.networks 
                            for hypercube in network.hypercubes})
    print(f"├→ Total Hypercubes: {total_hypercubes}")
    print(f"└→ Unique Hypercube Names: {unique_hypercubes}")

    # Networks → Hypercubes → Concepts
    print("\nReport → Networks → Hypercubes → Concepts")
    total_hypercube_concepts = sum(len(hypercube.concepts) for network in report.networks 
                                 for hypercube in network.hypercubes)
    unique_hypercube_concepts = len({concept.qname for network in report.networks 
                                   for hypercube in network.hypercubes 
                                   for concept in hypercube.concepts})
    print(f"├→ Total Hypercube Concepts: {total_hypercube_concepts}")
    print(f"└→ Unique Hypercube Concepts: {unique_hypercube_concepts}")

    # Networks → Hypercubes → Concepts → Abstracts
    print("\nReport → Networks → Hypercubes → Abstracts")
    total_hypercube_abstracts = sum(len(hypercube.abstracts) for network in report.networks 
                                 for hypercube in network.hypercubes)
    unique_hypercube_abstracts = len({abstract.qname for network in report.networks 
                                   for hypercube in network.hypercubes 
                                   for abstract in hypercube.abstracts})
    print(f"├→ Total Hypercube Abstracts: {total_hypercube_abstracts}")
    print(f"└→ Unique Hypercube Abstracts: {unique_hypercube_abstracts}")

    # Networks → Hypercubes → Concepts → Lineitems
    print("\nReport → Networks → Hypercubes → Lineitems")
    total_hypercube_lineitems = sum(len(hypercube.lineitems) for network in report.networks 
                                 for hypercube in network.hypercubes)
    unique_hypercube_lineitems = len({lineitem.qname for network in report.networks 
                                   for hypercube in network.hypercubes 
                                   for lineitem in hypercube.lineitems})
    print(f"├→ Total Hypercube Lineitems: {total_hypercube_lineitems}")
    print(f"└→ Unique Hypercube Lineitems: {unique_hypercube_lineitems}")

    # Networks → Hypercubes → Dimensions
    print("\nReport → Networks → Hypercubes → Dimensions")
    total_dimensions = sum(len(hypercube.dimensions) for network in report.networks 
                         for hypercube in network.hypercubes)
    unique_dimensions = len({dimension.qname for network in report.networks 
                           for hypercube in network.hypercubes 
                           for dimension in hypercube.dimensions})
    print(f"├→ Total Dimensions: {total_dimensions}")
    print(f"└→ Unique Dimensions: {unique_dimensions}")

    # Networks → Hypercubes → Dimensions → Members
    print("\nReport → Networks → Hypercubes → Dimensions → Members")
    total_members = sum(len(dimension.members_dict) for network in report.networks 
                       for hypercube in network.hypercubes 
                       for dimension in hypercube.dimensions)
    unique_members = len({member.qname for network in report.networks 
                         for hypercube in network.hypercubes 
                         for dimension in hypercube.dimensions 
                         for member in dimension.members})
    print(f"├→ Total Members: {total_members}")
    print(f"└→ Unique Members: {unique_members}")

    # Networks → Hypercubes → Dimensions → Default Members
    print("\nReport → Networks → Hypercubes → Dimensions → Default Members")
    default_members = set()
    total_default_members = 0
    for network in report.networks:
        for hypercube in network.hypercubes:
            for dimension in hypercube.dimensions:
                if dimension.default_member:
                    total_default_members += 1
                    default_members.add(dimension.default_member.qname)
    print(f"├→ Total Default Members: {total_default_members}")
    print(f"└→ Unique Default Members: {len(default_members)}")

    # Networks → Hypercubes → Dimensions → Domains
    print("\nReport → Networks → Hypercubes → Dimensions → Domains")
    total_domains = sum(1 for network in report.networks 
                       for hypercube in network.hypercubes 
                       for dimension in hypercube.dimensions 
                       if dimension.domain)
    unique_domains = len({dimension.domain.qname for network in report.networks 
                         for hypercube in network.hypercubes 
                         for dimension in hypercube.dimensions 
                         if dimension.domain})
    print(f"├→ Total Domains: {total_domains}")
    print(f"└→ Unique Domains: {unique_domains}")

    # Facts → Relationships
    print("\nReport → Facts → Relationships")
    print(f"├→ Facts → Concepts: {sum(1 for fact in report.facts if fact.concept)}")
    print(f"├→ Facts → Units: {sum(1 for fact in report.facts if fact.unit)}")
    print(f"├→ Facts → Periods: {sum(1 for fact in report.facts if fact.period)}")
    print(f"└→ Facts → Context IDs: {sum(1 for fact in report.facts if fact.context_id)}")

    # Neo4j Stats (if available)
    # if hasattr(report.neo4j, 'get_neo4j_db_counts'):
    #     print("\nNeo4j Database Stats")
    #     report.neo4j.get_neo4j_db_counts()

######################### Counting Function END #####################################################