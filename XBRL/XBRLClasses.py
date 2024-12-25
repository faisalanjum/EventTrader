from __future__ import annotations
from XBRL.validation import ValidationMixin  # Use absolute import


# dataclasses and typing imports
from dataclasses import dataclass, field, fields
from typing import List, Dict, Optional, Any, Union, Set, Type, Tuple
from abc import ABC, abstractmethod
from neo4j import GraphDatabase, Driver

# Python imports
import pandas as pd
import re
import html
import sys
from collections import defaultdict
from datetime import timedelta, date, datetime


# Arelle imports
from arelle import Cntlr, ModelDocument, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ModelValue import QName
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelFact, ModelContext, ModelUnit
from arelle.ModelXbrl import ModelXbrl
from enum import Enum


class GroupingType(Enum):
    CONTEXT = "context"
    PERIOD = "period"

def detect_duplicate_facts(facts: List[Fact]) -> Tuple[Dict[str, Fact], Dict[str, str]]:
    """Detect duplicate facts and return primary facts and duplicate mapping"""
    primary_facts = {}
    duplicate_map = {}
    
    for fact in facts:
        canonical_key = f"{fact.concept.qname}:{fact.context_id}:{fact.unit}"
        
        if canonical_key in primary_facts:
            primary = primary_facts[canonical_key]
            # Compare precision
            if (fact.decimals is not None and primary.decimals is not None and 
                fact.decimals > primary.decimals):
                # New fact has better precision - update primary
                duplicate_map[primary.u_id] = fact.u_id
                primary_facts[canonical_key] = fact
            else:
                # Keep existing primary
                duplicate_map[fact.u_id] = primary.u_id
        else:
            primary_facts[canonical_key] = fact
            
    return primary_facts, duplicate_map


# region Generic Classes
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


class NodeType(Enum):
    """XBRL node types in Neo4j"""
    
    LINE_ITEMS = "LineItems"
    CONCEPT = "Concept"
    ABSTRACT = "Abstract"
    
    COMPANY = "Company"
    ENTITY = "Entity" # Not using this for now
    REPORT = "Report"

    FACT = "Fact"
    CONTEXT = "Context"
    PERIOD = "Period"
    UNIT = "Unit"           
    
    HYPERCUBE = "HyperCube"
    DIMENSION = "Dimension"
    DOMAIN = "Domain"
    MEMBER = "Member"
    
    NAMESPACE = "Namespace" 
    LINKBASE = "Linkbase"  
    RESOURCE = "Resource"  

    GUIDANCE = "Guidance"
    DEPRECATED = "deprecated"
    DATE = "Date"
    OTHER = "Other"
    ADMIN_REPORT = "AdminReport"



class RelationType(Enum):
    """XBRL relationship types"""
    HAS_FACT = "HAS_FACT"
    HAS_CONCEPT = "HAS_CONCEPT"
    HAS_DIMENSION = "HAS_DIMENSION"
    HAS_MEMBER = "HAS_MEMBER"       # Domain/Dimension -> Member
    FACT_MEMBER = "FACT_MEMBER"     # Fact -> Member
    FACT_DIMENSION = "FACT_DIMENSION" # Fact -> Dimension
    HAS_DOMAIN = "HAS_DOMAIN"       # Dimension -> Domain
    PARENT_OF = "PARENT_OF"         # Parent Member -> Child Member
    HAS_DEFAULT = "HAS_DEFAULT"     # Dimension -> Default Member
    MEMBER_OF = "MEMBER_OF"         # Member to Parent Member
    IN_TAXONOMY = "IN_TAXONOMY"     # Dimension/Member to Taxonomy
    REPORTS = "REPORTS"
    BELONGS_TO = "BELONGS_TO"
    IN_CONTEXT = "IN_CONTEXT"       # Fact to Context
    HAS_PERIOD = "HAS_PERIOD"       # Context to Period
    HAS_UNIT = "HAS_UNIT"           # Fact to Unit
    PARENT_CHILD = "PARENT_CHILD"   # Presentation hierarchy
    CALCULATION = "CALCULATION"     # Calculation relationships
    DEFINITION = "DEFINITION"       # Definition relationships
    HAS_LABEL = "HAS_LABEL"         # Concept to Label
    HAS_REFERENCE = "HAS_REFERENCE" # Concept to Reference
    NEXT = "NEXT"                   # Next date
    HAS_PRICE = "HAS_PRICE"         # from Date to Entity/Company
    HAS_SUB_REPORT = "HAS_SUB_REPORT"  # For 10-K -> FYE and 10-Q -> Quarters relationships
    REPORTED_ON = "REPORTED_ON"     # From DateNode to ReportNode
    PRESENTATION_EDGE = "PRESENTATION_EDGE" # From Fact to Fact

    



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
    def classify(cls, concept: Any) -> NodeType:
        qname_str = str(concept.qname)
        sub_group = cls.get_substitution_group(concept)
        local_type = cls.get_local_type(concept)
        nillable = cls.check_nillable(concept)
        duration = cls.check_duration(concept)

        # Initial classification
        category = cls._initial_classify(concept, qname_str, sub_group, 
                                      local_type, nillable, duration)
        
        # Integrated post-classification
        if category == NodeType.OTHER:
            category = cls._post_classify_single(concept, qname_str, sub_group)
        
        return category

    @classmethod
    def _initial_classify(cls, concept, qname_str, sub_group, local_type, 
                         nillable, duration) -> NodeType:
        # 1. Basic Concept
        if not concept.isAbstract and sub_group == 'xbrli:item':
            return NodeType.CONCEPT
        
        # 2. Hypercube [Table]
        if (concept.isAbstract and 
            sub_group == 'xbrldt:hypercubeItem' and
            duration and nillable):
            return NodeType.HYPERCUBE
        
        # 3. Dimension [Axis] - here we could also just use "concept.isDimensionItem"
        if (concept.isAbstract and 
            sub_group == 'xbrldt:dimensionItem' and 
            duration and nillable):
            return NodeType.DIMENSION
        
        # 4. Member [Domain/Member]
        if ((any(qname_str.endswith(suffix) for suffix in ["Domain", "domain", "Member"]) or 
             local_type == 'domainItemType') and 
            duration and nillable):
            return NodeType.MEMBER
        
        # 5. Abstract
        if any(qname_str.endswith(suffix) for suffix in [
            "Abstract", "Hierarchy", "RollUp", 
            "RollForward", "Rollforward"
        ]) and concept.isAbstract:
            return NodeType.ABSTRACT
        
        # 6. LineItems
        if "LineItems" in qname_str and duration and nillable:
            return NodeType.LINE_ITEMS
        
        # 7. Guidance
        if local_type == 'guidanceItemType' or "guidance" in qname_str.lower():
            return NodeType.GUIDANCE
        
        # 8. Deprecated
        if "deprecated" in qname_str.lower() or "deprecated" in local_type.lower():
            return NodeType.DEPRECATED

        return NodeType.OTHER

    @classmethod
    def _post_classify_single(cls, concept, qname_str, sub_group) -> NodeType:
        # Rule 1: IsDomainMember -> *Member
        if concept.isDomainMember:
            return NodeType.MEMBER
            
        # Rule 2: Abstract -> *Abstract
        if concept.isAbstract:
            return NodeType.ABSTRACT
            
        # Rule 3: LinkbaseElement SubstitutionGroups
        if sub_group in cls.LINKBASE_ELEMENTS:
            return NodeType.LINKBASE
            
        # Rule 4: Date Elements
        if qname_str in cls.DATE_ELEMENTS:
            return NodeType.DATE
            
        return NodeType.OTHER



    # For first figuring out the category of ReportElements and then wrapping them in the appropriate class
    @classmethod
    def wrap_concept(cls, concept: Any, model_xbrl: ModelXbrl, network_uri: str) -> Union[Dimension, AbstractConcept, Member, Domain, None]:
        """Wrap ModelConcept in appropriate class based on its category"""
        if not concept:
            print("DEBUG - Received None concept")
            return None
            
        print(f"\nDEBUG - wrap_concept called for: {getattr(concept, 'qname', 'No qname')}")
        print(f"DEBUG - Original type: {type(concept)}")
        
        # Store the qname before any transformations
        original_qname = getattr(concept, 'qname', None)
        
        # Get the ModelConcept depending on what type we received
        if isinstance(concept, (AbstractConcept, Concept)):
            model_concept = getattr(concept, 'model_concept', None)
            if model_concept is None:
                print(f"DEBUG - No model_concept found in {type(concept).__name__}")
                return None
                
            # Only try to set qname if model_concept exists
            if not hasattr(model_concept, 'qname') and original_qname:
                try:
                    setattr(model_concept, 'qname', original_qname)
                except AttributeError:
                    print(f"DEBUG - Could not set qname on model_concept")
                    return None
                    
            print(f"DEBUG - Getting model_concept from {type(concept).__name__}")
        else:
            model_concept = concept
            print(f"DEBUG - Using original concept")

        # Verify we have a valid concept with qname
        if not hasattr(model_concept, 'qname'):
            print(f"DEBUG - Missing qname, attempting to restore from original")
            if original_qname:
                try:
                    setattr(model_concept, 'qname', original_qname)
                except AttributeError:
                    print(f"DEBUG - Cannot restore qname")
                    return None
            else:
                print(f"DEBUG - No qname available")
                return None

        if isinstance(model_concept, ModelConcept):
            category = cls.classify(model_concept)
            print(f"DEBUG - Classified as: {category}")
            
            # Rest of the wrapping logic remains the same
            if category == NodeType.DIMENSION:
                return Dimension(
                    model_xbrl=model_xbrl,
                    item=model_concept,
                    network_uri=network_uri
                )
            elif category == NodeType.MEMBER:
                return Member(
                    model_xbrl=model_xbrl,
                    item=model_concept,
                    parent_qname=None,
                    level=0
                )
            elif category == NodeType.DOMAIN:
                return Domain(
                    model_xbrl=model_xbrl,
                    item=model_concept
                )
            elif category in [NodeType.ABSTRACT, NodeType.LINE_ITEMS]:
                return AbstractConcept(model_concept)
            elif category == NodeType.HYPERCUBE:
                return AbstractConcept(model_concept)
                
            print(f"DEBUG - No wrapper created for category: {category}")
        else:
            print(f"DEBUG - Invalid concept: missing qname")
        return None
    

# endregion


@dataclass
class process_report:

    # Config 
    instance_file: str
    neo4j: Neo4jManager
    log_file: str = field(default='ErrorLog.txt', repr=False)
    testing: bool = field(default=True)  # Add testing flag as configurable
    model_xbrl: ModelXbrl = field(init=False, repr=False)

    # TODO: Can remove this later
    report_metadata: Dict[str, object] = field(init=False, default_factory=dict)
    
    # Common Nodes
    concepts: List[Concept] = field(init=False, default_factory=list, repr=False)
    contexts: List[Context] = field(init=False, default_factory=list, repr=False)

    # abstracts includes Abstracts, LineItems, Hypercube, Axis (Dimensions), Members
    abstracts: List[AbstractConcept] = field(init=False, default_factory=list, repr=False) # Used in Presentation Class
    pure_abstracts: List[AbstractConcept] = field(init=False, default_factory=list, repr=False) # Used in Presentation Class
    periods: List[Period] = field(init=False, default_factory=list, repr=False)
    units: List[Unit] = field(init=False, default_factory=list, repr=False)
    dates: List[DateNode] = field(init=False, default_factory=list)
    admin_reports: List[AdminReportNode] = field(init=False, default_factory=list)

    # Report-specific Nodes
    facts: List[Fact] = field(init=False, default_factory=list, repr=False)    
    dimensions: List[Dimension] = field(init=False, default_factory=list, repr=False)    
    taxonomy: Taxonomy = field(init=False)

    # Lookup Tables - TODO: Can we remove this?
    _concept_lookup: Dict[str, Concept] = field(init=False, default_factory=dict, repr=False) # Used in Linking Fact to Concept
    _abstract_lookup: Dict[str, AbstractConcept] = field(init=False, default_factory=dict, repr=False)
    
    
     # TODO
     # networks: List[Network] = field(init=False, default_factory=list, repr=False)
     
    def __post_init__(self):
        
        self._primary_facts: Dict[str, Fact] = {}  # canonical_key -> primary fact
        self._duplicate_map: Dict[str, str] = {}   # duplicate_uid -> primary_uid
        
        self.initialize_date_nodes(start_dt = "2024-12-01")     # Later remove these from process_report 
        self.load_xbrl()                                        # Required to fetch Company node
        self.initialize_entity_node()                           # Company Node Creation
        self.initialize_admin_reports()                         # Admin Reports Node Creation   
        self.initialize_report_node(cik = self.entity.cik)      # Report Node Creation
        # self.extract_report_metadata()                         # TODO: Remove this later

        self.populate_common_nodes()  # First handle common nodes
        self.populate_company_nodes() # Also creates Abstract Nodes in Neo4j
        self.populate_report_nodes()  # Then handle report-specific nodes
        # self.validate_all_facts(group_by=GroupingType.CONTEXT) # choose between GroupingType.CONTEXT or GroupingType.PERIOD
        self.link_validated_facts()

    def initialize_date_nodes(self, start_dt: str):
        """One-time initialization of date nodes"""
        try:
            self.dates = create_date_range(start_dt)
            relationships = create_date_relationships(self.dates)
            self.neo4j._export_nodes([self.dates])
            self.neo4j.merge_relationships(relationships)
            
        except Exception as e:
            print(f"Error initializing date nodes: {e}")

    def initialize_entity_node(self):
        """Initialize company node and create relationships with dates"""
        try:
            # Get company info and create entity
            cik, name, fiscal_year_end = get_company_info(self.model_xbrl)        
            self.entity = CompanyNode(cik=cik, name=name, fiscal_year_end=fiscal_year_end)

            # Create/Merge company node
            self.neo4j._export_nodes([self.entity])

            # Create relationships between dates and company with price data
            date_entity_relationships = []
            
            # Assuming self.dates contains all date nodes
            for date_node in self.dates:
                
                # TODO: Replace with actual price data source
                price_data = {'price': 100.0,  'returns': 0.01, 'session': 'Close','time': '12:01:52'} # placeholder
                
                # Create relationship from date to company with price properties
                date_entity_relationships.append(
                    (date_node, self.entity, RelationType.HAS_PRICE, price_data))

            # Merge relationships with properties
            self.neo4j.merge_relationships(date_entity_relationships)
            # print(f"Created {len(date_entity_relationships)} {RelationType.HAS_PRICE.value} relationships from {self.dates[0].__class__.__name__} to {self.entity.__class__.__name__}")
                
        except Exception as e:
            print(f"Error initializing company node: {e}")


    def initialize_admin_reports(self):
        """Initialize admin report hierarchy"""
        
        # Store admin report nodes in class
        self.admin_reports = [
            # Parent nodes
            *[AdminReportNode(code=t, label=l, category=t) 
            for t, l in {
                "10-K": "10-K Reports",
                "10-Q": "10-Q Reports", 
                "8-K": "8-K Reports"
            }.items()],
            
            # Child nodes
            *[AdminReportNode(code=f"10-K_FYE-{m}31", label=f"FYE {m}/31", category="10-K") 
            for m in ['03', '06', '09', '12']],
            *[AdminReportNode(code=f"10-Q_Q{q}", label=f"Q{q} Filing", category="10-Q") 
            for q in range(1, 5)]
        ]
        
        # Create parent-child relationships
        rels = [(p, c, RelationType.HAS_SUB_REPORT) 
                for p in self.admin_reports[:3]  # Parent nodes
                for c in self.admin_reports[3:]  # Child nodes
                if p.code == c.category]
        
        self.neo4j._export_nodes([self.admin_reports])
        self.neo4j.merge_relationships(rels)


    def initialize_report_node(self, cik: str):
        """Initialize report node and link to admin report and date"""
        doc_type, period_end_date, is_amendment = get_report_info(self.model_xbrl)
        
        # Strip "/A" from doc_type if present
        doc_type = doc_type.split('/')[0]  # Convert "10-Q/A" to "10-Q"


        print(f"Processing {doc_type} report for {period_end_date}")
        
        # Create report node
        self.report = ReportNode(formType=doc_type, periodEnd=period_end_date,
                            isAmendment=is_amendment, instanceFile=self.instance_file, cik=cik)
        
        month = datetime.strptime(period_end_date, '%Y-%m-%d').month
        
        # Find matching admin report
        if doc_type == "8-K":
            target = next(n for n in self.admin_reports if n.code == "8-K")
        else:
            sub_reports = [n for n in self.admin_reports if n.category == doc_type]
            if doc_type == "10-K":
                # Find closest FYE month
                target = min(sub_reports, 
                            key=lambda n: abs(int(n.code[-4:-2]) - month))
            else:  # 10-Q
                # Find closest quartermerge_relationships
                report_quarter = (month - 1) // 3 + 1
                target = min(sub_reports,
                            key=lambda n: abs(int(n.code[-1]) if n.code[-1].isdigit() else 0 - report_quarter))
        
        # Find closest date node
        filed_date = datetime.strptime(self.report.filedAt[:10], '%Y-%m-%d')
        date_node = min(self.dates, key=lambda d: abs((datetime(d.year, d.month, d.day) - filed_date).days))
        
        # Merge nodes and relationships
        self.neo4j._export_nodes([self.report])
        self.neo4j.merge_relationships([
            (self.report, target, RelationType.BELONGS_TO),
            (date_node, self.report, RelationType.REPORTED_ON, {
                'price': 100.0, # Place Holder Values - change later
                'returns': 0.01,
                'session': 'Close',
                'time': '12:01:52'
            }) ])



    # def link_validated_facts(self) -> None:
    #     """Link validated facts using presentation network hierarchy"""
    #     relationships = []
    #     dimensional_nodes = []  # New: collect dimensional nodes for merging
    #     debug_counts = defaultdict(int)
        
    #     for network in self.networks:
    #         if not network.isPresentation:
    #             continue
                
    #         network.report = self
    #         network.taxonomy = self.taxonomy
    #         validated_facts = network.validate_facts()

    #         fact_lookup: Dict[str, List[Fact]] = defaultdict(list)
    #         for fact in validated_facts:
    #             fact_lookup[fact.concept.u_id].append(fact)
            
    #         abstract_lookup = {abstract.u_id: abstract for abstract in self.pure_abstracts}
            
    #         for node in network.presentation.nodes.values():
    #             parent_concept = node.concept
    #             if not parent_concept:
    #                 continue
                    
    #             # Wrap parent in appropriate class
    #             print(f"Processing parent: {parent_concept.qname}")
    #             parent_node = ReportElementClassifier.wrap_concept(parent_concept, self.model_xbrl, network.network_uri)
    #             print(f"Wrapped as: {type(parent_node).__name__}")
                
    #             if isinstance(parent_node, (Dimension, Member, Domain)):
    #                 print(f"Adding to dimensional_nodes")
    #                 dimensional_nodes.append(parent_node)
    #             elif not parent_node:
    #                 parent_node = abstract_lookup.get(parent_concept.u_id)
    #                 print(f"Falling back to abstract_lookup")
    #             if not parent_node:
    #                 continue
                    
    #             for child_id in node.children:
    #                 child_node = network.presentation.nodes[child_id]
    #                 child_concept = child_node.concept
    #                 if not child_concept:
    #                     continue
                        
    #                 # Wrap child in appropriate class
    #                 wrapped_child = ReportElementClassifier.wrap_concept(child_concept, self.model_xbrl, network.network_uri)
    #                 if isinstance(wrapped_child, (Dimension, Member, Domain)):
    #                     dimensional_nodes.append(wrapped_child)
    #                 elif not wrapped_child:
    #                     wrapped_child = abstract_lookup.get(child_concept.u_id)
    #                 if not wrapped_child and child_concept.u_id not in fact_lookup:
    #                     continue

    #                 # Rest of the code remains exactly the same
    #                 rel_props = {
    #                     'network_uri': network.network_uri,
    #                     'network_name': network.name,
    #                     'report_instance': self.report.instanceFile,
    #                     'parent_level': node.level,
    #                     'parent_order': node.order,
    #                     'child_level': child_node.level,
    #                     'child_order': child_node.order
    #                 }

    #                 if wrapped_child:
    #                     relationships.append((parent_node, wrapped_child, RelationType.PRESENTATION_EDGE, rel_props))
    #                     debug_counts['abstract_to_abstract'] += 1

    #                 if child_concept.u_id in fact_lookup:
    #                     for fact in fact_lookup[child_concept.u_id]:
    #                         relationships.append((parent_node, fact, RelationType.PRESENTATION_EDGE, rel_props))
    #                         debug_counts['abstract_to_fact'] += 1

    #     # Merge dimensional nodes first
    #     if dimensional_nodes:
    #         self.neo4j.merge_nodes(dimensional_nodes)
            
    #     # Then merge relationships
    #     if relationships:
    #         self.neo4j.merge_relationships(relationships)



    def link_validated_facts(self) -> None:
        """Link validated facts using presentation network hierarchy"""
        relationships = []
        debug_counts = defaultdict(int)
        
        for network in self.networks:
            if not network.isPresentation:
                continue

            print(f"\nProcessing network: {network.name}")
            relationships_before = len(relationships)


            network.report = self
            network.taxonomy = self.taxonomy
            validated_facts = network.validate_facts()

            # Debug print for StockholdersEquity facts
            stockholders_equity_facts = [f for f in validated_facts if f.qname == 'us-gaap:StockholdersEquity']
            if stockholders_equity_facts:
                print("\nFound StockholdersEquity facts in validated_facts:")
                for fact in stockholders_equity_facts:
                    print(f"Value: {fact.value}, Context: {fact.context_id}, Primary: {fact.is_primary}")


            # Debug print to understand fact structure
            # for fact in validated_facts:
            #     print("*"*100)
            #     print(f"Network: {network.name}")
            #     print(f"Fact: {fact.qname}")
            #     print(f"Context: {fact.context_id}")
            #     if fact.context:
            #         print(f"Dimensions: {fact.context.qnameDims}")
            

            # Group facts by concept, maintaining all facts for each concept
            fact_lookup: Dict[str, List[Fact]] = defaultdict(list)
            for fact in validated_facts:
                fact_lookup[fact.concept.u_id].append(fact)


                # Debug if this is StockholdersEquity
                if fact.qname == 'us-gaap:StockholdersEquity':
                    print(f"\nAdding to fact_lookup:")
                    print(f"Concept u_id: {fact.concept.u_id}")
                    print(f"Fact value: {fact.value}")
                    print(f"Is primary: {fact.is_primary}")


            abstract_lookup = {abstract.u_id: abstract for abstract in self.pure_abstracts}
            
            for node in network.presentation.nodes.values():
                # if not node.children:
                #     continue
                    
                parent_node = node.concept
                parent_u_id = parent_node.u_id if parent_node else None
                if not parent_u_id:
                    continue
                    
                for child_id in node.children:
                    child_node = network.presentation.nodes[child_id]
                    child_u_id = child_node.concept.u_id if child_node.concept else None
                    
                    if not child_u_id:
                        continue

                # Debug for StockholdersEquity - safely check concept qname
                    if (child_node.concept is not None and 
                        hasattr(child_node.concept, 'qname') and 
                        child_node.concept.qname == 'us-gaap:StockholdersEquity'):
                        print(f"\nProcessing StockholdersEquity node:")
                        print(f"Child u_id: {child_u_id}")
                        print(f"Facts in lookup: {[f.value for f in fact_lookup.get(child_u_id, [])]}")
                        print(f"Parent in abstract_lookup: {parent_u_id in abstract_lookup}")
                        print(f"Child in fact_lookup: {child_u_id in fact_lookup}")

                    # Additional debug for all nodes
                    if child_node.concept is None:
                        print(f"\nFound node with None concept:")
                        print(f"Node ID: {child_id}")
                        print(f"Parent node qname: {parent_node.qname if parent_node else 'None'}")

                        
                    rel_props = {
                        'network_uri': network.network_uri,
                        'network_name': network.name,
                        'company_cik': self.entity.cik,
                        'report_instance': self.report.instanceFile,
                        'parent_level': node.level,
                        'parent_order': node.order,
                        'child_level': child_node.level,
                        'child_order': child_node.order
                    }
                    

                    # print(f"Checking parent: {parent_node.qname}, child: {child_node.concept.qname}")
                    # print(f"Fact: {fact}")
                    # print(f"Parent in abstract_lookup: {parent_u_id in abstract_lookup}, Child in abstract_lookup: {child_u_id in abstract_lookup}")

                    # Link Abstract -> Abstract
                    if parent_u_id in abstract_lookup and child_u_id in abstract_lookup:
                        relationships.append((
                            abstract_lookup[parent_u_id],
                            abstract_lookup[child_u_id],
                            RelationType.PRESENTATION_EDGE,
                            rel_props
                        ))
                        debug_counts['abstract_to_abstract'] += 1

                    # Link Abstract -> Facts (now handling multiple facts per concept)
                    if parent_u_id in abstract_lookup and child_u_id in fact_lookup:
                        for fact in fact_lookup[child_u_id]:

                            # DEBUG for StockholdersEquity
                            if fact.qname == 'us-gaap:StockholdersEquity':
                                print(f"\nCreating StockholdersEquity relationship:")
                                print(f"Network: {network.name}")
                                print(f"Parent: {abstract_lookup[parent_u_id].qname}")
                                print(f"Fact value: {fact.value}")
                                print(f"Fact context: {fact.context_id}")
                                print(f"Is primary: {fact.is_primary}")


                            relationships.append((
                                abstract_lookup[parent_u_id],
                                fact,
                                RelationType.PRESENTATION_EDGE,
                                rel_props
                            ))
                            debug_counts['abstract_to_fact'] += 1


            relationships_added = len(relationships) - relationships_before
            print(f"Relationships added in this network: {relationships_added}")
            if network.name == "Condensed Consolidated Balance Sheets (Unaudited)":
                print("\nBalance Sheet Network Details:")
                print(f"Abstract concepts count: {len(abstract_lookup)}")
                print(f"Facts count: {len(fact_lookup)}")
                # Print a few example relationships being created
                for rel in relationships[-5:]:  # Last 5 relationships
                    if isinstance(rel[1], Fact) and rel[1].qname == 'us-gaap:StockholdersEquity':
                        print(f"Relationship: {rel[0].qname} -> {rel[1].qname} ({rel[1].value})")


        # Create relationships in Neo4j
        if relationships:
            self.neo4j.merge_relationships(relationships)
            
        print("\nRelationship Creation Summary:")
        print(f"Total relationships created: {len(relationships)}")
        for rel_type, count in debug_counts.items():
            print(f"{rel_type}: {count}")




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

        # contexts are company-specific 
        self._build_contexts()  # 4. Build contexts - but only nodes, not relationships
        

        # Upload to Neo4j only common nodes first
        self.neo4j._export_nodes([self.concepts, self.periods, self.units, self.contexts], testing=False)
        
        # Load complete set from Neo4j
        self.concepts = self.neo4j.load_nodes_as_instances(NodeType.CONCEPT, Concept)
        self.periods = self.neo4j.load_nodes_as_instances(NodeType.PERIOD, Period)
        self.units = self.neo4j.load_nodes_as_instances(NodeType.UNIT, Unit)
        
        print(f"Loaded common nodes from Neo4j: {len(self.concepts)} concepts, {len(self.periods)} periods, {len(self.units)} units")
        self._concept_lookup = {node.id: node for node in self.concepts} 
        

    def populate_company_nodes(self):
        """Build and sync company-specific nodes (Dimensions, Members) with Neo4j"""        
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")

        # Build taxonomy-wide dimensions
        self.taxonomy = Taxonomy(self.model_xbrl)
        self.taxonomy.build_dimensions()

        # Here we should load_nodes_as_instances from both self.taxonomy.dimensions, self.taxonomy.members, domains as well as member hierarchies

        # Collect all nodes
        all_domains = [dim.domain for dim in self.taxonomy.dimensions if dim.domain is not None]
        all_members = [member for dim in self.taxonomy.dimensions 
                    if dim.members_dict 
                    for member in dim.members_dict.values()]
        

        # Export nodes to Neo4j
        self.neo4j._export_nodes([
            self.taxonomy.dimensions,  # Dimensions
            all_domains,              # Domains
            all_members               # Members
        ], testing=False)

        # Export relationships
        relationships = []
        relationships.extend(self.taxonomy.get_dimension_domain_relationships())
        relationships.extend(self.taxonomy.get_dimension_member_relationships())
        relationships.extend(self.taxonomy.get_member_hierarchy_relationships())
        
        if relationships:
            self.neo4j.merge_relationships(relationships)
        
        self._build_networks()

        # populate_company_nodes calls _build_hierarchy which inturn calls _build_abstracts (which are common nodes & not company-specific) & fills self.abstracts
        abstracts_lineItems = [abs for abs in self.abstracts if abs.category in ['Abstract', 'LineItems']]

        self.neo4j._export_nodes([abstracts_lineItems], testing=False) # Only export Abstracts & LineItems 
        # self.neo4j._export_nodes([self.abstracts], testing=False) # Only export Abstracts & LineItems 

        self.pure_abstracts = self.neo4j.load_nodes_as_instances(NodeType.ABSTRACT, AbstractConcept)


    def populate_report_nodes(self):
        """Build and export report-specific nodes (Facts, Dimensions)"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")

        self._build_facts()       # 5. Build facts
        
        # Upload to Neo4j report-specific nodes - # Testing=False since otherwise it will clear the db
        self.neo4j._export_nodes([self.facts], testing=False) 

        # Define relationship types to export
        rel_types = [(Fact, Concept, RelationType.HAS_CONCEPT),
                     (Fact, Unit, RelationType.HAS_UNIT),
                     (Fact, Period, RelationType.HAS_PERIOD)]
        
        self._export_relationships(rel_types)        
        
        # Export fact-dimension relationships
        fact_dim_relationships = self._build_fact_dimension_relationships()
        if fact_dim_relationships:
            self.neo4j.merge_relationships(fact_dim_relationships)


        # Export context relationships
        context_relationships = self._build_context_relationships()
        if context_relationships:
            self.neo4j.merge_relationships(context_relationships)


        # Export fact-context relationships
        fact_context_relationships = self._build_fact_context_relationships()
        if fact_context_relationships:
            self.neo4j.merge_relationships(fact_context_relationships)

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
        valid_facts = [fact for fact in self.model_xbrl.factsInInstance 
                    if not (fact.id and fact.id.startswith('hidden-fact'))]
                    
        for model_fact in valid_facts:
            fact = Fact(model_fact=model_fact, _report=self)  # Pass self as report reference

            model_concept = model_fact.concept
            concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"
            concept = self._concept_lookup.get(concept_id)
            
            if not concept: 
                print(f"Warning: No concept found for fact {fact.fact_id}")
                continue
                
            # Create canonical key using model_concept
            canonical_key = f"{model_concept.qname}:{fact.context_id}:{fact.unit}"
            
            # Check for duplicates
            if canonical_key in self._primary_facts:
                primary = self._primary_facts[canonical_key]
                fact_decimals = fact.decimals if fact.decimals is not None else float('-inf')
                primary_decimals = primary.decimals if primary.decimals is not None else float('-inf')
                if fact_decimals > primary_decimals:

                    self._duplicate_map[primary.u_id] = fact.u_id
                    self._primary_facts[canonical_key] = fact
                else:
                    self._duplicate_map[fact.u_id] = primary.u_id
            else:
                self._primary_facts[canonical_key] = fact
            
            concept.add_fact(fact)
            self.facts.append(fact)
            
        print(f"Built {len(self.facts)} facts ({len(self._primary_facts)} unique)")

    # def _build_facts(self):
    #     """Build facts with two-way concept relationships"""
    #     # Filter out hidden facts right at the source
    #     valid_facts = [fact for fact in self.model_xbrl.factsInInstance 
    #                 if not (fact.id and fact.id.startswith('hidden-fact'))]
                    

    #     for model_fact in valid_facts:
    #         fact = Fact(model_fact=model_fact)

    #         model_concept = model_fact.concept
    #         concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"
    #         concept = self._concept_lookup.get(concept_id)
    #         if not concept: 
    #             print(f"Warning: No concept found for fact {fact.fact_id}")
    #             continue
    #         else:
    #            # Only linking concept.facts since fact.concept = concept done in export_            
    #            # # Also this is not done for Neo4j nodes but for internal classes only                  
    #             concept.add_fact(fact) 
            
    #         self.facts.append(fact)
    #     print(f"Built {len(self.facts)} unique facts")    


    def _build_contexts(self):
        """Build context objects from the model"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        contexts_dict = {}
        
        for model_context in self.model_xbrl.contexts.values():
            try:
                # Period handling
                if model_context.isInstantPeriod:
                    period_type = "instant"
                    start_date = model_context.instantDatetime.strftime('%Y-%m-%d')
                    end_date = None
                elif model_context.isStartEndPeriod:
                    period_type = "duration"
                    start_date = model_context.startDatetime.strftime('%Y-%m-%d')
                    end_date = model_context.endDatetime.strftime('%Y-%m-%d')
                else:
                    period_type = "forever"
                    start_date = None
                    end_date = None
                
                period = Period(
                    period_type=period_type,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Get CIK from entity identifier
                _, identifier = model_context.entityIdentifier
                cik = identifier.lstrip('0')  # Remove leading zeros as per CompanyNode
                
                # Get dimensions and members
                dimension_u_ids = []
                member_u_ids = []
                if model_context.qnameDims:
                    for dim_qname, member in model_context.qnameDims.items():
                        # Get company_id from the same source as Dimension class
                        company_id = self.model_xbrl.modelDocument.uri.split('/')[-3]
                        
                        # Create dimension u_id matching Dimension class format
                        dim_u_id = f"{company_id}:{dim_qname.namespaceURI}:{dim_qname}"

                        dimension_u_ids.append(dim_u_id)
                        
                        if hasattr(member, 'memberQname'):
                            # Create member u_id matching Member class format
                            mem_u_id = f"{company_id}:{member.memberQname.namespaceURI}:{member.memberQname}"
                            member_u_ids.append(mem_u_id)

                context = Context(
                    context_id=model_context.id,
                    cik=cik,
                    period_u_id=period.u_id,
                    dimension_u_ids=dimension_u_ids,
                    member_u_ids=member_u_ids
                )
                
                contexts_dict[context.u_id] = context
                    
            except Exception as e:
                print(f"Error processing context {model_context.id}: {e}")
        
        self.contexts = list(contexts_dict.values())
        print(f"Built {len(self.contexts)} unique contexts")



    def _build_context_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between contexts and their related nodes"""
        context_relationships = []
        
        for context in self.contexts:
            # Context -> Period
            period = next((p for p in self.periods if p.u_id == context.period_u_id), None)
            if period:
                context_relationships.append((context, period, RelationType.HAS_PERIOD))
            
            # Context -> Company
            context_relationships.append((context, self.entity, RelationType.BELONGS_TO))
            
            # Context -> Dimensions
            for dim_id in context.dimension_u_ids:
                dim = next((d for d in self.taxonomy.dimensions if d.u_id == dim_id), None)
                if dim:
                    context_relationships.append((context, dim, RelationType.HAS_DIMENSION))
            
            # Context -> Members
            for mem_id in context.member_u_ids:
                for dim in self.taxonomy.dimensions:
                    member = next((m for m in dim.members_dict.values() if m.u_id == mem_id), None)
                    if member:
                        context_relationships.append((context, member, RelationType.HAS_MEMBER))
                        break
                        
        return context_relationships

    def _build_fact_dimension_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between facts and their dimensions/members"""
        relationships = []

        # Create lookup dictionaries using QName objects
        dim_lookup = {dim.u_id: dim for dim in self.taxonomy.dimensions}
        member_lookup = {}

        for dim in self.taxonomy.dimensions:
            for member_qname_str, member in dim.members_dict.items():
                member_lookup[member.u_id] = member 

        # Process each fact's dimensions
        for fact in self.facts:
            if not fact.dims_members:
                continue

            for dim_concept, member_concept in fact.dims_members:
                if not dim_concept:
                    continue

                taxonomy_dim = dim_lookup.get(dim_concept.u_id)
                if not taxonomy_dim:
                    continue

                # If we have a member, try to link through it
                if member_concept:
                    member = member_lookup.get(member_concept.u_id)
                    if member:
                        relationships.append((fact, member, RelationType.FACT_MEMBER))
                        continue  # Proceed to next dimension-member pair

                # If no member or member not found, link directly to dimension
                relationships.append((fact, taxonomy_dim, RelationType.FACT_DIMENSION))
                
        return relationships

    def _build_fact_context_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between facts and their contexts"""
        fact_context_relationships = []
        
        for fact in self.facts:
            # Find matching context using context_id
            context = next((ctx for ctx in self.contexts 
                        if ctx.context_id == fact.context_id), None)
            if context:
                fact_context_relationships.append((fact, context, RelationType.IN_CONTEXT))
        
        print(f"Built {len(fact_context_relationships)} fact-context relationships")
        return fact_context_relationships

    # def _build_fact_dimension_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
    #     """Build relationships between facts and their dimensions/members"""
    #     relationships = []
    #     dim_count = 0
    #     member_count = 0

    #     # Create lookup dictionaries using QName objects
    #     dim_lookup = {dim.item.qname: dim for dim in self.taxonomy.dimensions}
    #     member_lookup = {}

    #     for dim in self.taxonomy.dimensions:
    #         for member_qname_str, member in dim.members_dict.items():
    #             member_qname = member.item.qname  # Assuming member.item has qname
    #             member_lookup[member_qname] = member

    #     # Process each fact's dimensions
    #     for fact in self.facts:
    #         if not fact.dims_members:
    #             continue

    #         for dim_concept, member_concept in fact.dims_members:
    #             if not dim_concept:
    #                 continue

    #             dim_qname = dim_concept.qname
    #             taxonomy_dim = dim_lookup.get(dim_qname)
    #             if not taxonomy_dim:
    #                 continue

    #             # If we have a member, try to link through it
    #             if member_concept:
    #                 member_qname = member_concept.qname
    #                 member = member_lookup.get(member_qname)
    #                 if member:
    #                     relationships.append((fact, member, RelationType.HAS_MEMBER))
    #                     member_count += 1
    #                     continue  # Proceed to next dimension-member pair

    #             # If no member or member not found, link directly to dimension
    #             relationships.append((fact, taxonomy_dim, RelationType.HAS_DIMENSION))
    #             dim_count += 1

    #     print(f"\nBuilt fact relationships: {dim_count} direct dimensions, {member_count} members")
    #     print(f"Facts with dimension relationships: {len(set(r[0].u_id for r in relationships))}")
    #     return relationships

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

        # 2. Link presentation concepts first - also _build_abstracts in build_hierarchy
        for network in self.networks:
            # Create Presentation Class
            if network.isPresentation:
                network.presentation = Presentation(
                    network_uri=network.network_uri,
                    model_xbrl=self.model_xbrl,
                    process_report=self  # Pass report reference to access/create concepts and abstracts
                )
                            
        # 3. Adding hypercubes after networks are complete which in turn builds dimensions
        for network in self.networks:
            network.add_hypercubes(self.model_xbrl)
            for hypercube in network.hypercubes:                
                hypercube._link_hypercube_concepts(self.concepts, self.abstracts)


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
                        



@dataclass
class Context(Neo4jNode):
    context_id: str
    cik: str  # This should match CompanyNode's cik
    period_u_id: str
    dimension_u_ids: List[str] = field(default_factory=list)
    member_u_ids: List[str] = field(default_factory=list)
    u_id: str = field(init=False)

    def __post_init__(self):
        self.generate_id()

    def __hash__(self):
        return hash(self.u_id)

    def __eq__(self, other):
        if isinstance(other, Context):
            return self.u_id == other.u_id
        return False


    def generate_id(self):
        """Generate a unique ID for the context based on company, period, and dimensional qualifiers"""
        # Clean and prepare components that define context's semantic identity
        components = [
            # str(self.context_id).strip(),             # Removed ID as it's report-specific but we are making context company-specific
            str(self.cik).strip(),                    # Company identifier
            str(self.period_u_id).strip(),            # Period identifier
            "_".join(sorted(self.dimension_u_ids)) if self.dimension_u_ids else "no_dims",  # Dimensional qualifiers
            "_".join(sorted(self.member_u_ids)) if self.member_u_ids else "no_mems"        # Member values
        ]
        
        # Join components and create hash
        unique_key = "_".join(filter(None, components))
        self.u_id = str(abs(hash(unique_key)))  # Using abs() to avoid negative numbers
        
        # Debug print
        # print(f"\nContext ID Components:")
        # print(f"1. CIK: {self.cik}")
        # print(f"2. Period ID: {self.period_u_id}")
        # print(f"3. Dimensions: {self.dimension_u_ids or 'no_dims'}")
        # print(f"4. Members: {self.member_u_ids or 'no_mems'}")
        # print(f"Final u_id: {self.u_id}")


    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        return NodeType.CONTEXT

    @property
    def id(self) -> str:
        return self.u_id

    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "u_id": self.id,
            "context_id": self.context_id,
            "cik": self.cik,
            "period_u_id": self.period_u_id,
            "dimension_u_ids": self.dimension_u_ids,
            "member_u_ids": self.member_u_ids
        }






# region : Common/Macro Nodes ########################

@dataclass
class Taxonomy:
    model_xbrl: ModelXbrl
    dimensions: List[Dimension] = field(default_factory=list)
    _dimension_lookup: Dict[str, Dimension] = field(default_factory=dict)
    
    def build_dimensions(self):
        """Build taxonomy-wide dimensions and their hierarchies"""
        
        dim_dom_rel_set = self.model_xbrl.relationshipSet(XbrlConst.dimensionDomain) # Get dimension-domain relationships first                
        
        for concept in self.model_xbrl.qnameConcepts.values():                       # Find all dimensions in taxonomy
            if concept.isDimensionItem: 
                try:
                    # Indicates taxonomy-wide context
                    dimension = Dimension(model_xbrl=self.model_xbrl, item=concept, network_uri=None)
                    
                    # Get domain first - Note: Typically Domain qname ends with 'Domain' but sometimes it ends with 'Member'
                    if dim_dom_rel_set:
                        for rel in dim_dom_rel_set.fromModelObject(concept):
                            if rel.toModelObject is not None:
                                dimension.domain = Domain(model_xbrl=self.model_xbrl,item=rel.toModelObject)
                                break
                    
                    # Build members only after domain is potentially set
                    dimension._build_members()
                    
                    self.dimensions.append(dimension)                    
                    self._dimension_lookup[dimension.qname] = dimension     # Building lookup table for dimensions
                    
                except Exception as e:
                    print(f"Error creating dimension {concept.qname}: {str(e)}")



    def get_dimension_domain_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Get all dimension-domain relationships"""
        relationships = []
        for dimension in self.dimensions: 
            if dimension.domain:
                # Connect dimension to domain
                relationships.append((dimension, dimension.domain, RelationType.HAS_DOMAIN))
        return relationships
    

    def get_dimension_member_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Get all dimension-member relationships"""
        relationships = []
        
        for dimension in self.dimensions:
            if dimension.domain:
                # Connect only top-level members to domain
                for member in dimension.members_dict.values():
                    # Only connect members that don't have a parent (top-level members)
                    if not member.parent_qname:
                        relationships.append((dimension.domain, member, RelationType.HAS_MEMBER))
        
        return relationships

    def get_member_hierarchy_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Get member-to-member hierarchy relationships"""
        relationships = []
        for dimension in self.dimensions:
            if dimension.members_dict:
                for member in dimension.members_dict.values():
                    # This leaves Domain out of the hierarchy since no parent_qname, in anycase build_members fills members_dict only with members
                    if member.parent_qname:                                 
                        parent = dimension.members_dict.get(member.parent_qname)
                        if parent:
                            relationships.append((parent, member, RelationType.PARENT_OF))
        return relationships
    
    # Not used anywhere
    def get_all_members(self) -> List[Member]:
        """Get all members across all dimensions"""
        return [
            member 
            for dim in self.dimensions 
            if dim.members_dict
            for member in dim.members_dict.values()
        ]

    # Not used anywhere
    def get_dimension_members(self, dimension_qname: str) -> List[Member]:
        """Get members for a specific dimension"""
        dimension = self._dimension_lookup.get(dimension_qname)         # Using lookup table to get Dimension Instance
        if dimension and dimension.members_dict:
            return list(dimension.members_dict.values())
        return []    



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
    category: Optional[str] = None
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
            self.category = ReportElementClassifier.classify(self.model_concept).value

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
            "type_local": self.type_local,
            "category": self.category
        }        


# TODO: Already using Category in Concept so remove it from AbstractConcept

@dataclass
class AbstractConcept(Concept):
    category: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.model_concept is not None:  # Only validate if creating from XBRL
            if not self.model_concept.isAbstract:
                raise ValueError("Cannot create AbstractConcept from non-abstract concept")
            self.category = ReportElementClassifier.classify(self.model_concept).value
        # When loading from Neo4j, category will be set directly from properties

    @property
    def is_abstract(self) -> bool:
        return True

    @property
    def node_type(self) -> NodeType:
        return NodeType.ABSTRACT

    @property
    def properties(self) -> Dict[str, Any]:
        props = super().properties
        props['category'] = self.category
        return props

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
    

# endregion : Common/Macro Nodes ########################


@dataclass
class AdminReportNode(Neo4jNode):
    code: str          # e.g., "10-K_FYE-1231", "10-Q_Q1", "8-K"
    label: str         # e.g., "Annual Report (December)", "Q1 Report"
    category: str      # e.g., "10-K", "10-Q", "8-K"
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.ADMIN_REPORT
        
    @property
    def id(self) -> str:
        return self.code
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "category": self.category,
            "displayLabel": self.label
        }

# region : Company Nodes ########################


# TODO: Once we have sec-api subscription, can remove Optional from fields. 

@dataclass
class CompanyNode(Neo4jNode):
    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    fiscal_year_end: Optional[str] = None

    def __post_init__(self):
        # Ensure CIK is properly formatted (10 digits with leading zeros)
        self.cik = self.cik.zfill(10)
        
    def display(self):
        """Returns display name for the entity"""
        if self.ticker:
            return f"{self.name} ({self.ticker})"
        return self.name

    @property
    def node_type(self) -> NodeType:
        return NodeType.COMPANY

    @property
    def id(self) -> str:
        """Use CIK as unique identifier"""
        return self.cik

    @property
    def properties(self) -> Dict[str, Any]:
        """
        Returns properties for Neo4j node
        Filters out None values to keep the node clean
        """
        props = {
            'id': self.id,
            'cik': self.cik,
            'name': self.name,
            'displayLabel': self.display()
        }
        
        # Add optional properties if they exist
        optional_props = {
            'ticker': self.ticker,
            'exchange': self.exchange,
            'sector': self.sector,
            'industry': self.industry,
            'fiscal_year_end': self.fiscal_year_end
        }
        
        # Only include non-None optional properties
        props.update({k: v for k, v in optional_props.items() if v is not None})
        
        return props


@dataclass
class DateNode(Neo4jNode):
    year: int
    month: int
    day: int

    def __post_init__(self):
        self.date = datetime(self.year, self.month, self.day)

    def display(self):
        return self.date.strftime("%Y-%m-%d")
        
    @property
    def node_type(self) -> NodeType:
        return NodeType.DATE
        
    @property
    def id(self) -> str:
        return self.display()
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            'id': self.display(),
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'quarter': f"Q{(self.month-1)//3 + 1}",
            'displayLabel': self.display() 
        }


@dataclass
class Network(ValidationMixin):
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
    
    report: Optional['process_report'] = None # Inorder to validate facts, we need to pass the report

    # Add field to store validated facts
    validated_facts: List[Fact] = field(init=False, default_factory=list)


    def add_hypercubes(self, model_xbrl) -> None:
        """Add hypercubes if this is a definition network"""
        if not self.isDefinition:
            return
                
        # 1. Get the specific definition network relationships
        for rel_type in [XbrlConst.all, XbrlConst.notAll]:
            # Important: Specify the network_uri when getting relationships
            rel_set = model_xbrl.relationshipSet(rel_type, self.network_uri)
            if not rel_set:
                continue
                
            # 2. Process relationships in this specific network
            for rel in rel_set.modelRelationships:
                if (rel.toModelObject is not None and 
                    hasattr(rel.toModelObject, 'isHypercubeItem') and 
                    rel.toModelObject.isHypercubeItem):
                    
                    hypercube = Hypercube(
                        model_xbrl=self.model_xbrl,
                        hypercube_item=rel.toModelObject,
                        network_uri=self.network_uri
                    )
                    self.hypercubes.append(hypercube)


    # def add_hypercubes(self, model_xbrl) -> None:
    #     """Add hypercubes if this is a definition network"""
    #     if not self.isDefinition:
    #         return
            
    #     # for rel in model_xbrl.relationshipSet(XbrlConst.all).modelRelationships:
    #     #     if (rel.linkrole == self.network_uri and 
    #     #         rel.toModelObject is not None and 
    #     #         hasattr(rel.toModelObject, 'isHypercubeItem') and 
    #     #         rel.toModelObject.isHypercubeItem):
                
    #     #         hypercube = Hypercube(
    #     #             model_xbrl = self.model_xbrl,
    #     #             hypercube_item=rel.toModelObject,
    #     #             network_uri=self.network_uri
    #     #         )
    #     #         self.hypercubes.append(hypercube)

    #     # Check both 'all' and 'notAll' relationships
    #     for rel_type in [XbrlConst.all, XbrlConst.notAll]:
    #         for rel in model_xbrl.relationshipSet(rel_type).modelRelationships:
    #             if (rel.linkrole == self.network_uri and 
    #                 rel.toModelObject is not None and 
    #                 hasattr(rel.toModelObject, 'isHypercubeItem') and 
    #                 rel.toModelObject.isHypercubeItem):
                    
    #                 hypercube = Hypercube(
    #                     model_xbrl = self.model_xbrl,
    #                     hypercube_item=rel.toModelObject,
    #                     network_uri=self.network_uri
    #                 )
    #                 self.hypercubes.append(hypercube)
    

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
    

    # def validate_facts(self) -> List[Fact]:
    #     """Validates facts according to presentation network definition algorithm"""

    #     print(f"\nNetwork {self.name}:")

    #     # Step 1: Facts -> Concepts -> PN
    #     facts_in_pn = self._get_facts_in_presentation_network()        
    #     print(f"Found {len(facts_in_pn)} facts in presentation network")
        
    #     # Split facts based on hypercube presence
    #     facts_not_in_hc = self._get_facts_not_in_hypercubes(facts_in_pn) or set()
    #     facts_in_hc = self._get_facts_in_hypercubes(facts_in_pn) or set()
    #     print(f"Split facts: {len(facts_not_in_hc)} not in hypercubes, {len(facts_in_hc)} in hypercubes")

    #     # Process facts not in hypercubes
    #     filtered_non_hc_facts = self._filter_facts_without_dimensions(facts_not_in_hc) or set()
    #     print(f"Filtered non-hypercube facts: {len(filtered_non_hc_facts)}")
        
    #     # Process facts in hypercubes
    #     filtered_hc_facts = self._process_hypercube_facts(facts_in_hc) or set()
    #     print(f"Filtered hypercube facts: {len(filtered_hc_facts)}")
        
    #     # Validation checks
    #     all_validated_facts = self._perform_validation_checks(filtered_non_hc_facts, filtered_hc_facts)
    #     print(f"Final validated facts: {len(all_validated_facts)}\n")
        
    #     return all_validated_facts


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
    process_report: process_report
    
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
                    self._build_abstracts(model_obj)
            
            # Track parent-child relationship with order
            if parent_id not in parent_child_map:
                parent_child_map[parent_id] = []
            parent_child_map[parent_id].append((child_id, rel.order or 0))
        
        # Second pass: Build nodes with correct levels
        self._build_nodes(parent_child_map)
    

    def _build_abstracts(self, model_concept: ModelConcept) -> None:
        """Create AbstractConcept if not already exists"""
        concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"

        if (concept_id not in self.process_report._concept_lookup and 
            concept_id not in self.process_report._abstract_lookup):
            try:
                abstract = AbstractConcept(model_concept)
                self.process_report.abstracts.append(abstract)
                self.process_report._abstract_lookup[abstract.id] = abstract  # Using .id property
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
        return (self.process_report._concept_lookup.get(concept_id) or 
                self.process_report._abstract_lookup.get(concept_id))
    
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


    # def _build_dimensions(self) -> None:
    #     """Build dimension objects from model_xbrl matching this hypercube"""
        
    #     # 1. Get hypercube-dimension relationships for specific network
    #     # print(f"Fetching hypercube-dimension relationships for network: {self.network_uri}")
    #     hc_dim_rel_set = self.model_xbrl.relationshipSet(
    #         XbrlConst.hypercubeDimension, 
    #         self.network_uri
    #     )
    #     if not hc_dim_rel_set:
    #         # print("No hypercube-dimension relationships found.")
    #         return

    #     # print(f"Total relationships in hypercube-dimension set: {len(hc_dim_rel_set.modelRelationships)}")
            
    #     # 2. Get relationships FROM this hypercube
    #     # print(f"Fetching relationships from hypercube: {self.hypercube_item.qname}")
    #     relationships = hc_dim_rel_set.fromModelObject(self.hypercube_item)
    #     if not relationships:
    #         # print(f"No relationships found from hypercube: {self.hypercube_item.qname}")
    #         return

    #     # print(f"Total relationships from hypercube {self.hypercube_item.qname}: {len(relationships)}")
            
    #     # 3. Process each dimension relationship
    #     for rel in relationships:
    #         dim_object = rel.toModelObject
    #         # print(f"Processing relationship: from {rel.fromModelObject.qname} to {rel.toModelObject.qname if rel.toModelObject else 'None'}")
            
    #         if dim_object is None:
    #             # print("Dimension object is None. Skipping this relationship.")
    #             continue
            
    #         if not dim_object.isDimensionItem:
    #             # print(f"{dim_object.qname} is not a dimension item. Skipping.")
    #             continue
                
    #         try:
    #             # Create dimension with network context
    #             # print(f"Creating Dimension object for: {dim_object.qname}")
    #             dimension = Dimension(
    #                 model_xbrl=self.model_xbrl,
    #                 item=dim_object,
    #                 network_uri=self.network_uri
    #             )
                
    #             # Add validation to ensure dimension is properly connected
    #             if self._validate_dimension_connection(dim_object):
    #                 # print(f"Dimension {dim_object.qname} validated and added.")
    #                 self.dimensions.append(dimension)
    #             else:
    #                 # print(f"Dimension {dim_object.qname} failed validation. Skipping.")
    #                 pass

    #         except Exception as e:
    #             # print(f"Error processing dimension {dim_object.qname}: {e}")
    #             continue

    # def _validate_dimension_connection(self, dim_object) -> bool:
    #     """Validate that dimension is properly connected in this network"""
    #     # print(f"Validating connection for dimension: {dim_object.qname}")

    #     # Check if dimension is directly connected to this hypercube
    #     hc_dim_rels = self.model_xbrl.relationshipSet(
    #         XbrlConst.hypercubeDimension, 
    #         self.network_uri
    #     )

    #     if not hc_dim_rels:
    #         # print(f"No hypercube-dimension relationships found for validation in network: {self.network_uri}")
    #         return False

    #     for rel in hc_dim_rels.modelRelationships:
    #         # print(f"Checking relationship: from {rel.fromModelObject.qname} to {rel.toModelObject.qname}")
    #         if rel.fromModelObject == self.hypercube_item and rel.toModelObject == dim_object:
    #             # print(f"Dimension {dim_object.qname} is properly connected to hypercube {self.hypercube_item.qname}.")
    #             return True

    #     # print(f"Dimension {dim_object.qname} is NOT connected to hypercube {self.hypercube_item.qname}.")
    #     return False


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
                    item=dim_object,
                    network_uri=self.network_uri
                )
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

@dataclass
class Dimension(Neo4jNode):
    """Dimension with its domain and members"""
    model_xbrl: ModelXbrl
    item: ModelConcept
    network_uri: Optional[str] = None
    
    # Core properties
    name: str = field(init=False)
    qname: str = field(init=False)
    label: str = field(init=False)
    u_id: Optional[str] = field(init=False, default=None)
    
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
    def id(self) -> str:
        """For Neo4j MERGE"""
        return self.u_id
        
    @property
    def node_type(self) -> NodeType:
        return NodeType.DIMENSION
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "u_id": self.id, # this returns the u_id    
            "qname": self.qname,
            "name": self.name,
            "label": self.label,
            "is_explicit": self.is_explicit,
            "is_typed": self.is_typed,
            "network_uri": self.network_uri,            
        }


    def __hash__(self):
        """Use u_id for hashing since it's unique"""
        # return hash(self.u_id) if self.u_id is not None else 0
        return hash(self.u_id)
        
    def __eq__(self, other):
        """Compare dimensions based on their u_id"""
        if not isinstance(other, Dimension):
            return NotImplemented
        return self.u_id == other.u_id

    @property
    def members(self) -> List[Member]:
        """Get unique members sorted by level"""
        return sorted(self.members_dict.values(), key=lambda x: x.level)

    # Returns a dictionary grouping members by their hierarchical depth (levels). - works only for explicit dimensions
    @property
    def members_by_level(self) -> Dict[int, List[Member]]:
        """Get members organized by their hierarchy level"""
        levels: Dict[int, List[Member]] = {}
        for member in self.members:
            if member.level not in levels:
                levels[member.level] = []
            levels[member.level].append(member)
        return levels

    # Returns a dictionary of parent-to-child member relationships for hierarchical lineage analysis.- applies only to explicit dimensions since typed dimensions don't have predefined member relationships.
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
        
        # TODO: Also need to add Entity ID/CIK/name to this ID since dimensions will be specific to a company
        # Set id first
        if self.item is not None: 
            # TODO: company_id(Gets CIK from URL) is a workaround, ideally get it from report.entity.cik 
            # but need to pass process_report it all the way here
            company_id = self.model_xbrl.modelDocument.uri.split('/')[-3]  
            self.u_id = f"{company_id}:{self.item.qname.namespaceURI}:{self.item.qname}"


        # Core properties
        self.name = str(self.item.qname.localName)
        self.qname = str(self.item.qname)
        # self.id = str(self.dimension.objectId())
        self.label = self.item.label() if hasattr(self.item, 'label') else None
            
        
        # Dimension type
        self.is_explicit = bool(getattr(self.item, 'isExplicitDimension', False))
        self.is_typed = bool(getattr(self.item, 'isTypedDimension', False))
        
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
                
        dim_dom_rel_set = (
            self.model_xbrl.relationshipSet(XbrlConst.dimensionDomain, self.network_uri)
            if self.network_uri else
            self.model_xbrl.relationshipSet(XbrlConst.dimensionDomain)
        )


        if not dim_dom_rel_set: return
                
        relationships = dim_dom_rel_set.fromModelObject(self.item)
        if not relationships: return
                
        # Process first domain relationship
        for rel in relationships:
            domain_object = rel.toModelObject
            
            if domain_object is None: continue
            
            try:
                self.domain = Domain(
                    model_xbrl=self.model_xbrl,
                    item=domain_object
                )
                break  # Take the first valid domain
            except Exception as e:
                print(f"Error creating domain for {self.qname}: {str(e)}")
                continue
    
    def _build_members(self) -> None:
        """Build hierarchical member relationships"""
        
        if not self.is_explicit:return                
        if not self.domain: return


        dom_mem_rel_set = (
            self.model_xbrl.relationshipSet(XbrlConst.domainMember, self.network_uri)
            if self.network_uri else
            self.model_xbrl.relationshipSet(XbrlConst.domainMember)
        )

        # dom_mem_rel_set = self.model_xbrl.relationshipSet(XbrlConst.domainMember, self.network_uri)
        # dom_mem_rel_set = self.model_xbrl.relationshipSet(XbrlConst.domainMember)

        if not dom_mem_rel_set: return
        
        def add_members_recursive(source_object: ModelConcept, parent_qname: Optional[str] = None, level: int = 0) -> None:

            relationships = dom_mem_rel_set.fromModelObject(source_object)            
            for rel in relationships:
                member_object = rel.toModelObject
                
                if member_object is None: continue                    
                if not hasattr(member_object, 'isDomainMember'): continue
                    
                try:
                    member = Member( model_xbrl=self.model_xbrl, item=member_object, parent_qname=parent_qname, level=level)                    
                    self.add_member(member)                    
                    # Process children
                    add_members_recursive(member_object, str(member_object.qname), level + 1)
                        
                except Exception as e:
                    print(f"Error creating member {member_object.qname}: {str(e)}")
                    continue
        
        # Start with domain being the source object
        add_members_recursive(self.domain.item)

    # Exclude domain itself from members
    def add_member(self, member: Member) -> None:
        """Add member if not already present and not the domain itself""" 
        if member.qname not in self.members_dict and member.qname != self.domain.qname:
            self.members_dict[member.qname] = member
        else:
            pass


    def _set_default_member(self) -> None:
        """Set default member if exists"""
        default_rel_set = (
            self.model_xbrl.relationshipSet(XbrlConst.dimensionDefault, self.network_uri)
            if self.network_uri else
            self.model_xbrl.relationshipSet(XbrlConst.dimensionDefault)
        )

        if not default_rel_set: return
            
        # Get relationships using fromModelObject
        relationships = default_rel_set.fromModelObject(self.item)
        if not relationships: return
        
        # Debug: Print all relationships for this dimension
        # rel_list = list(relationships)
        # for rel in rel_list:
        #     print(f"Default relationship - From: {rel.fromModelObject.qname} -> To: {rel.toModelObject.qname}")
            
        try:
            default_rel = next(iter(relationships))
            default_domain_obj = default_rel.toModelObject
            
            if default_domain_obj is None: return
                
            # Create Member object from the domain that's set as default
            self.default_member = Member(
                model_xbrl=self.model_xbrl,
                item=default_domain_obj,
                parent_qname=None,
                level=0)
            
            # Add to members collection
            self.add_member(self.default_member)
                
        except Exception as e:
            print(f"Error setting default member for {self.qname}: {str(e)}")


@dataclass
class Member(Neo4jNode):
    """Represents a dimension member in a hierarchical structure"""
    model_xbrl: ModelXbrl
    item: ModelConcept
    qname: str = field(init=False)
    label: str = field(init=False)
    parent_qname: Optional[str] = None
    level: int = 0
    u_id: Optional[str] = None
    
    def __post_init__(self):
        self.qname = str(self.item.qname)
        # self.label = self.member.label() if hasattr(self.member, 'label') else None
        # self.label = self.member.qname.localName if hasattr(self.member, 'qname') else None
        self.label = self.item.qname.localName.replace('Member', '') if hasattr(self.item, 'qname') else None

        
        # TODO: Also need to add Entity ID/CIK/name to this ID since members will be specific to a company
        if self.item is not None:

            # TODO: company_id(Gets CIK from URL) is a workaround, ideally get it from report.entity.cik 
            # but need to pass process_report it all the way here
            company_id = self.model_xbrl.modelDocument.uri.split('/')[-3]  
            self.u_id = f"{company_id}:{self.item.qname.namespaceURI}:{self.item.qname}"

    @property
    def id(self) -> str:
        return self.u_id
        
    @property
    def node_type(self) -> NodeType:
        return NodeType.MEMBER
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "u_id": self.id, # this returns the u_id
            "qname": self.qname,
            "label": self.label,
            "level": self.level,
            "parent_qname": self.parent_qname
        }

    def __hash__(self):
        return hash(self.u_id)
        
    def __eq__(self, other):
        if not isinstance(other, Member):
            return NotImplemented
        return self.u_id == other.u_id


@dataclass
class Domain(Member):
    """Represents a dimension domain"""

    def __post_init__(self):
        # Call Member's __post_init__ to initialize shared attributes
        super().__post_init__()

        # Remove 'Domain' from the label if present
        if self.label:
            self.label = self.label.replace('Domain', '')

        # Set parent_qname to None and level to 0 for Domain
        self.parent_qname = None
        self.level = 0

    @property
    def node_type(self) -> NodeType:
        return NodeType.DOMAIN

    def __hash__(self):
        return hash(self.u_id) if self.u_id is not None else 0
        
    def __eq__(self, other):
        if not isinstance(other, Domain):
            return NotImplemented
        return self.u_id == other.u_id





# @dataclass
# class Domain(Neo4jNode): 
#     """Represents a dimension domain"""
#     model_xbrl: ModelXbrl
#     domain: ModelConcept
#     qname: str = field(init=False)
#     label: str = field(init=False)
#     type: str = field(init=False)
#     u_id: Optional[str] = field(init=False, default=None)

    
#     def __post_init__(self):
        
#         #TODO: Also need to add Entity ID/CIK/name to this ID since domains will be specific to a company
#         if self.domain is not None:

#             # TODO: company_id(Gets CIK from URL) is a workaround, ideally get it from report.entity.cik 
#             # but need to pass process_report it all the way here
#             company_id = self.model_xbrl.modelDocument.uri.split('/')[-3]  
#             self.u_id = f"{company_id}:{self.domain.qname.namespaceURI}:{self.domain.qname}"

#         self.qname = str(self.domain.qname)
#         self.label = self.domain.label() if hasattr(self.domain, 'label') else None
#         self.type = self.domain.typeQname.localName if hasattr(self.domain, 'typeQname') else None

#     @property
#     def id(self) -> str:
#         """For Neo4j MERGE"""
#         return self.u_id
        
#     @property
#     def node_type(self) -> NodeType:
#         return NodeType.DOMAIN
        
#     @property
#     def properties(self) -> Dict[str, Any]:
#         return {
#             "qname": self.qname,
#             "label": self.label,
#             "type": self.type
#         }


# endregion : Company Nodes ########################



# region : Instance/Report Nodes ########################


@dataclass
class ReportNode(Neo4jNode):
    # source: https://sec-api.io/docs/query-api
    formType: str
    periodEnd: str          # event date for 8-K, period end for 10-K/Q
    isAmendment: bool
    instanceFile: str       # instance file name - sec_api - maybe able to get it from dataFiles field in sec_api 
    cik: str                                             # Change this to Ticker when moving to sec_api
    
    # TODO: Will be supplied by sec-api 
    filedAt: Optional[str] = "2024-12-02T16:06:24-04:00"

    # TODO: Will be supplied by sec-api 
    accessionNo: Optional[str] = None
    periodOfReport: Optional[str] = None     # official filing period date

    # for admin purposes
    insertedAt: Optional[str] = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    status: Optional[bool] = False           # Once a report has been uploaded, make this True

    def __post_init__(self):
        self.cik = self.cik.zfill(10)
        self.period_date = datetime.strptime(self.periodEnd, '%Y-%m-%d')
    
    def get_fiscal_period(self) -> str:
        """Get fiscal period (Q1-Q4 or FYE MM/DD)"""
        month = self.period_date.month
        if self.formType == "10-K":
            return f"FYE {month:02d}/31"
        return f"Q{(month-1)//3 + 1}"
    
    def find_matching_sub_report(self, parent: AdminReportNode) -> AdminReportNode:
        """Find matching sub-report based on period end date"""
        sub_reports = [n for n in self.admin_reports 
                      if n.category == parent.code]
        return min(sub_reports, 
                  key=lambda x: abs(x.get_date() - self.period_date))

        
    def display(self) -> str:
        """Returns display name for the report"""
        date = datetime.strptime(self.periodEnd, '%Y-%m-%d')
        amendment = "A" if self.isAmendment else ""
        period = ("8K" if self.formType == "8-K" else
                 f"Q{(date.month - 1) // 3 + 1}" if self.formType == "10-Q" 
                 else f"FY{date.year}")
        # return f"{self.cik}_{date.year}_{period}{amendment}" # Later use Ticker when we have sec-api
        return f"{date.year}_{period}{amendment}" # Later use Ticker when we have sec-api
        
        
    @property
    def node_type(self) -> NodeType:
        """Returns node type for Neo4j"""
        return NodeType.REPORT
        
    @property
    def id(self) -> str:
        """Use instanceFile as unique identifier"""
        return self.instanceFile
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Returns properties for Neo4j node"""
        props = {
            'id': self.id,
            'formType': self.formType,
            'periodEnd': self.periodEnd,
            'isAmendment': self.isAmendment,
            'instanceFile': self.instanceFile,
            'filedAt': self.filedAt,
            'cik': self.cik,
            'displayLabel': self.display(),
            'insertedAt': self.insertedAt,
            'status': self.status
        }
        
        # Add optional properties if they exist
        optional_props = {
            'accessionNo': self.accessionNo,
            'periodOfReport': self.periodOfReport
        }
        
        # Only include non-None optional properties
        props.update({k: v for k, v in optional_props.items() if v is not None})
        
        return props    

@dataclass
class Fact(Neo4jNode):
    model_fact: ModelFact
    _report: 'process_report' = field(repr=False, default=None)  # Add this line
    refers_to: Optional[Fact] = None  # 

    # Globally unique fact identifier
    u_id: str = field(init=False)        # Globally u_id (see _generate_unique_fact_id)

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

    # dims_members: Optional[List[Tuple[Dimension, Member]]] = field(init=False, default_factory=list)
    # Note: In fact, for each dimension, there can be only one member 
    dims_members: Optional[List[Tuple[ModelConcept, ModelConcept]]] = field(init=False, default_factory=list)
    

    def __getattr__(self, name):
        """Automatically redirect any attribute access to the actual fact"""
        return getattr(self.model_fact, name)


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
        # self.value = self.model_fact.sValue if self.model_fact.isNumeric else self._extract_text(self.model_fact.value)

        self.context_id = self.model_fact.contextID                        
        self.decimals = self.model_fact.decimals        
 
        # All Links to other Nodes
        # TODO: Instead of linking to XBRL concept, link to actual  class
        # self.concept = self.model_fact.concept 
        self.unit = self.model_fact.unitID
        self._set_period()
        self._set_dimensions() # Facts can have only 1 member per dimension although can be linked to many dimensions

    @property
    def is_nil(self) -> bool:
        """Check if the fact is nil."""
        return self.model_fact.isNil
    
    @property
    def is_numeric(self) -> bool:
        """Check if the fact is numeric."""
        return self.model_fact.isNumeric    
    

    @property
    def is_primary(self) -> bool:
        """Check if this is a primary fact"""
        return self.u_id not in self._report._duplicate_map
        
    @property
    def primary_fact(self) -> 'Fact':
        """Get primary version of this fact"""
        if not self.is_primary:
            primary_uid = self._report._duplicate_map[self.u_id]
            return next(f for f in self._report.facts 
                       if f.u_id == primary_uid)
        return self

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
        if not context:
            self.period = None
            return
            
        period_parts = ['instant' if context.isInstantPeriod else 'duration' if context.isStartEndPeriod else 'forever']
        if context.isInstantPeriod:
            period_parts.append(context.instantDatetime.strftime('%Y-%m-%d'))
        elif context.isStartEndPeriod:
            period_parts.extend([context.startDatetime.strftime('%Y-%m-%d'), context.endDatetime.strftime('%Y-%m-%d')])
        
        self.period = '_'.join(period_parts)



    # def _set_period(self) -> None:
    #     """Set the period property based on context"""
    #     context = self.model_fact.context
    #     if context is None or len(context) == 0:
    #         self.period = None
    #         return
            
    #     if getattr(context, 'isInstantPeriod', False):
    #         self.period = context.instantDatetime.strftime('%Y-%m-%d')
    #     elif getattr(context, 'isStartEndPeriod', False):
    #         self.period = f"{context.startDatetime.strftime('%Y-%m-%d')} to {context.endDatetime.strftime('%Y-%m-%d')}"
    #     else:
    #         self.period = "Forever"


# According to the XBRL Dimensions 1.0 specification:
# For Explicit Dimensions:
    # A dimension MUST have at least one domain
    # The domain is declared using dimension-domain relationships
    # The domain can have child members (using domain-member relationships)
# For Typed Dimensions: 
    # No domain is required
    # Values are defined by an XML Schema type

    def _set_dimensions(self) -> None:
        """Set dimensions and members using ModelConcept objects for explicit dims
        and typed values for typed dims"""
        # Check both segDimValues and scenDimValues as per XBRL spec
        dim_values = getattr(self.model_fact.context, 'segDimValues', {})
        dim_values.update(getattr(self.model_fact.context, 'scenDimValues', {}))
        
        if not dim_values:
            # print(f"No dimensions found for fact {self.u_id}")
            return
            
        for dim_concept, dim_value in dim_values.items():
            try:
                fact_dimension = Dimension(model_xbrl=self.model_fact.modelXbrl, item=dim_concept, network_uri=None)
                # For explicit dimensions, use the member ModelConcept
                if hasattr(dim_value, 'isExplicit') and dim_value.isExplicit:
                    if hasattr(dim_value, 'member') and dim_value.member is not None:
                        fact_member = Member(model_xbrl=self.model_fact.modelXbrl, item = dim_value.member, parent_qname=None, level=0) 
                        # self.dims_members.append((dim_concept, dim_value.member))
                        self.dims_members.append((fact_dimension, fact_member))
                        # print(f"Added explicit dimension: {dim_concept.qname}, member: {dim_value.member.qname}")
                        
                # For typed dimensions, use the typed value
                elif hasattr(dim_value, 'isTyped') and dim_value.isTyped:
                    if hasattr(dim_value, 'typedMember') and dim_value.typedMember is not None:
                        typed_concept = dim_value.dimension  # Use the dimension's concept as base
                        fact_member = Member(model_xbrl=self.model_fact.modelXbrl, item = typed_concept, parent_qname=None, level=0) 
                        # self.dims_members.append((dim_concept, dim_value.typedMember.stringValue))
                        self.dims_members.append((fact_dimension, fact_member))
                        # print(f"Added typed dimension: {dim_concept.qname}, value: {dim_value.typedMember.stringValue}")
                        
                else:
                    print(f"Dimension {dim_concept.qname} is neither explicit nor typed")
                    
            except AttributeError as e:
                print(f"Warning: Could not process dimension value for {dim_concept}: {e}")




    # # To be Used when Linking to Dimension and Member Nodes
    # def _set_dimensions(self) -> None:
    #     """Set dimensions and members using same logic as original"""
    #     if hasattr(self.model_fact.context, 'qnameDims') and self.model_fact.context.qnameDims:
    #         for dim_qname, dim_value in self.model_fact.context.qnameDims.items():            
                
    #             #TODO: For now going ahead with qname as ID for both Dimension and Member
    #             #  but change it to match unique identifier so we can map to exact node in neo4j,
    #             #  just like we did with other nodes
    #             self.dims_members.append((str(dim_qname), 
    #                 str(dim_value.memberQname) if dim_value.isExplicit
    #                 else dim_value.typedMember.stringValue if dim_value.isTyped
    #                 else "Unknown"
    #             ))

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

            # Collections containing collections can not be stored in properties.
            # 'dims_members': self.dims_members if self.dims_members is not None else None,
        }


    def __hash__(self):
        return hash(self.u_id)


# endregion : Instance/Report Nodes ########################



# region : Neo4j Manager ########################

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
            
    # def create_indexes(self):
    #     """Create indexes and constraints for all node types if they don't exist"""
    #     try:
    #         with self.driver.session() as session:
    #             # Get existing constraints
    #             existing_constraints = {
    #                 constraint['name']: constraint['labelsOrTypes'][0]
    #                 for constraint in session.run("SHOW CONSTRAINTS").data()
    #             }
                
    #             # Create missing constraints
    #             for node_type in NodeType:
    #                 constraint_name = f"constraint_{node_type.value.lower()}_id_unique"
                    
    #                 # Only create if it doesn't exist
    #                 if constraint_name not in existing_constraints:
    #                     session.run(f"""
    #                     CREATE CONSTRAINT {constraint_name}
    #                     FOR (n:`{node_type.value}`)
    #                     REQUIRE n.id IS UNIQUE
    #                     """)
    #                     # print(f"Created constraint for {node_type.value}")
    #                 else:
    #                     # print(f"Constraint for {node_type.value} already exists")
    #                     pass
                        
    #     except Exception as e:
    #         raise RuntimeError(f"Failed to create indexes: {e}")
        

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
                
                # Create relationship constraints
                rel_constraint_name = "constraint_presentation_edge_unique"
                if rel_constraint_name not in existing_constraints:
                    session.run("""
                    CREATE CONSTRAINT constraint_presentation_edge_unique
                    FOR ()-[r:PRESENTATION_EDGE]-()
                    REQUIRE (r.source_id, r.target_id, r.network_id) IS UNIQUE
                    """)
                    print(f"Created constraint for PRESENTATION_EDGE relationships")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to create indexes: {e}")


            
    def merge_nodes(self, nodes: List[Neo4jNode], batch_size: int = 1000) -> None:
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


    def _process_fact_relationships(self, relationships: List[Tuple]) -> List[Tuple]:
        """Pre-process relationships to handle fact duplicates"""
        # Quick check if any facts involved
        if not any(isinstance(source, Fact) or isinstance(target, Fact) 
                for source, target, *_ in relationships):
            return relationships
            
        processed = []
        for rel in relationships:
            source, target, rel_type, *props = rel


            # Debug for StockholdersEquity facts
            if isinstance(target, Fact) and target.qname == 'us-gaap:StockholdersEquity':
                print("\nProcessing StockholdersEquity relationship:")
                print(f"Network: {props[0].get('network_name', 'Unknown')}")  # Add network name
                print(f"Original value: {target.value}")
                print(f"Original context: {target.context_id}")
                print(f"Is primary: {target.is_primary}")
                print(f"Primary fact value: {target.primary_fact.value}")
                print(f"Primary fact context: {target.primary_fact.context_id}")
                print(f"Source type: {type(source).__name__}")
                print(f"Source ID: {source.id if hasattr(source, 'id') else 'N/A'}")





            # Convert facts to primary versions
            if isinstance(source, Fact):
                source = source.primary_fact
            if isinstance(target, Fact):
                target = target.primary_fact
            
            # Skip self-referential relationships
            if source.id == target.id: continue

            processed.append((source, target, rel_type, *props))
        
        return processed



    # def merge_relationships(self, relationships: List[Tuple]) -> None:
    #     """Merge relationships into Neo4j database.
        
    #     Creates unique relationship types for fact-based relationships in different networks
    #     to prevent overwriting of identical facts that appear in multiple networks.
        
    #     Args:
    #         relationships: List of tuples containing (source, target, rel_type, properties)
    #     """
    #     counts = defaultdict(lambda: {'count': 0, 'source': '', 'target': ''})
        
    #     relationships = self._process_fact_relationships(relationships)

    #     with self.driver.session() as session:
    #         for rel in relationships:
    #             source, target, rel_type, *props = rel
    #             properties = props[0] if props else {}
                
    #             # Determine if this is a network-specific relationship
    #             is_network_relationship = (
    #                 ('network_name' in properties or 'network_uri' in properties) and 
    #                 isinstance(target, Fact)
    #             )
                
    #             if is_network_relationship:
    #                 # For network-based fact relationships, create network-specific type
    #                 # Use network_uri for unique identification, falling back to network_name if URI not available
    #                 network_id = (properties.get('network_uri', '') or properties.get('network_name', '')).split('/')[-1]
    #                 network_rel_type = f"{rel_type.value}_NET_{network_id}"
                    
    #                 # Debug logging for network relationships
    #                 if target.qname == 'us-gaap:StockholdersEquity':
    #                     print(f"\nCreating network-specific relationship:")
    #                     print(f"Network: {properties.get('network_name', 'Unknown')}")
    #                     print(f"Relationship type: {network_rel_type}")
    #                     print(f"Fact value: {target.value}")
    #             else:
    #                 # For non-network relationships (abstract-to-abstract or other types),
    #                 # use the original relationship type
    #                 network_rel_type = rel_type.value
                
    #             # Create or merge the relationship in Neo4j
    #             session.run(f"""
    #                 MATCH (s {{id: $source_id}})
    #                 MATCH (t {{id: $target_id}})
    #                 MERGE (s)-[r:{network_rel_type}]->(t)
    #                 SET r += $properties
    #             """, {
    #                 "source_id": source.id,
    #                 "target_id": target.id,
    #                 "properties": properties
    #             })
                
    #             # Update counts for logging
    #             counts[network_rel_type].update({
    #                 'count': counts[network_rel_type]['count'] + 1, 
    #                 'source': source.__class__.__name__, 
    #                 'target': target.__class__.__name__
    #             })
        
    #     # Log relationship creation summary
    #     print("\nRelationship Creation Summary:")
    #     for rel_type, info in counts.items():
    #         print(f"Created {info['count']} {rel_type} relationships from {info['source']} to {info['target']}")




    def merge_relationships(self, relationships: List[Union[Tuple[Neo4jNode, Neo4jNode, RelationType], Tuple[Neo4jNode, Neo4jNode, RelationType, Dict[str, Any]]]]) -> None:
        counts = defaultdict(lambda: {'count': 0, 'source': '', 'target': ''})
        
        relationships = self._process_fact_relationships(relationships)

        with self.driver.session() as session:
            for rel in relationships:
                source, target, rel_type, *props = rel
                properties = props[0] if props else {}
                
                # Only addition: Special handling for PRESENTATION_EDGE with network info
                if (rel_type == RelationType.PRESENTATION_EDGE and 
                    isinstance(target, Fact) and 
                    ('network_uri' in properties or 'network_name' in properties)):
                    
                    network_id = properties.get('network_uri', properties.get('network_name', '')).split('/')[-1]
                    company_cik = properties.get('company_cik')  # Get CIK from properties
                    
                    # Changed: Pass merge criteria as parameters instead of inline
                    session.run("""
                        MATCH (s {id: $source_id})
                        MATCH (t {id: $target_id})
                        MERGE (s)-[r:PRESENTATION_EDGE {source_id: $merge_source_id, 
                                target_id: $merge_target_id, 
                                network_id: $merge_network_id,
                                company_cik: $company_cik
                            }]->(t)
                        SET r += $properties
                    """, {
                        "source_id": source.id,
                        "target_id": target.id,
                        "merge_source_id": source.id,
                        "merge_target_id": target.id,
                        "merge_network_id": network_id,
                        "company_cik": company_cik,
                        "properties": properties
                    })
                else:
                    # Original code unchanged for all other cases
                    session.run(f"""
                        MATCH (s {{id: $source_id}})
                        MATCH (t {{id: $target_id}})
                        MERGE (s)-[r:{rel_type.value}]->(t)
                        SET r += $properties
                    """, {
                        "source_id": source.id,
                        "target_id": target.id,
                        "properties": properties
                    })
                
                counts[rel_type.value].update({'count': counts[rel_type.value]['count'] + 1, 
                                        'source': source.__class__.__name__, 
                                        'target': target.__class__.__name__})
        
        for rel_type, info in counts.items():
            print(f"Created {info['count']} {rel_type} relationships from {info['source']} to {info['target']}")



    # def merge_relationships(self, relationships: List[Union[Tuple[Neo4jNode, Neo4jNode, RelationType], Tuple[Neo4jNode, Neo4jNode, RelationType, Dict[str, Any]]]]) -> None:
        
    #     counts = defaultdict(lambda: {'count': 0, 'source': '', 'target': ''})
        
    #     relationships = self._process_fact_relationships(relationships)


    #     with self.driver.session() as session:
    #         for rel in relationships:
    #             source, target, rel_type, *props = rel
    #             properties = props[0] if props else {}
                
    #             session.run(f"""
    #                 MATCH (s {{id: $source_id}})
    #                 MATCH (t {{id: $target_id}})
    #                 MERGE (s)-[r:{rel_type.value}]->(t)
    #                 SET r += $properties
    #             """, {
    #                 "source_id": source.id,
    #                 "target_id": target.id,
    #                 "properties": properties
    #             })
    #             counts[rel_type.value].update({'count': counts[rel_type.value]['count'] + 1, 
    #                                         'source': source.__class__.__name__, 
    #                                         'target': target.__class__.__name__})
        
    #     for rel_type, info in counts.items():
    #         print(f"Created {info['count']} {rel_type} relationships from {info['source']} to {info['target']}")

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



# endregion : Neo4j Manager ########################



# region : Admin/Helpers ########################

# TODO: This is temporary - later take dateNode creation outside 
def create_date_range(start: str, end: str = None) -> List[DateNode]:
    s = datetime.strptime(start, "%Y-%m-%d").date()  # Convert to date
    e = datetime.now().date() if end is None else datetime.strptime(end, "%Y-%m-%d").date()  # Convert to date
    return [DateNode(d.year, d.month, d.day) 
            for d in (s + timedelta(days=i) for i in range((e-s).days + 1))]

# TODO: This is temporary - later take dateNode creation outside 
def create_date_relationships(dates: List[DateNode]) -> List[Tuple[DateNode, DateNode, RelationType]]:
    relationships = []
    for i in range(len(dates) - 1):
        relationships.append((dates[i], dates[i + 1], RelationType.NEXT)) 
    return relationships


# TODO: To be replaced later by actual sec-api - This is temporary
def get_company_info(model_xbrl):
    # model_xbrl = get_model_xbrl(instance_url)
    cik = next((context.entityIdentifier[1].lstrip('0') 
                for context in model_xbrl.contexts.values() 
                if context.entityIdentifier and 'cik' in context.entityIdentifier[0].lower()), None)
    name = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'EntityRegistrantName'), None)
    fiscal_year_end = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'CurrentFiscalYearEndDate'), None)
    return cik, name, fiscal_year_end

# TODO: To be replaced later by actual sec-api - This is temporary
def get_report_info(model_xbrl):
    doc_type = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentType'), None)
    period_end_date = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentPeriodEndDate'), None)
    is_amendment = next((fact.value.lower() == 'true' for fact in model_xbrl.facts 
                        if fact.qname.localName == 'AmendmentFlag'), False)
    
    return doc_type, period_end_date, is_amendment  



def count_report_hierarchy(report: process_report) -> None:
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

# endregion : Admin/Helpers ########################