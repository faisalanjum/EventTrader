"""
This module contains network-related implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Local imports
from .validation import ValidationMixin
from .utils import *
from .xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType
from .xbrl_core import PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS, ReportElementClassifier
from .xbrl_concept_nodes import Concept, AbstractConcept
from .xbrl_dimensions import Hypercube

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .xbrl_processor import process_report
    from .xbrl_reporting import Fact
    from .xbrl_dimensions import Dimension, Domain, Member  # Hypercube already imported above
    from .xbrl_taxonomy import Taxonomy
    from .Neo4jManager import Neo4jManager



# class XbrlConst:
#     parentChild = "http://www.xbrl.org/2003/arcrole/parent-child"
#     summationItem = "http://www.xbrl.org/2003/arcrole/summation-item"
#     all = "http://xbrl.org/int/dim/arcrole/all"
#     notAll = "http://xbrl.org/int/dim/arcrole/notAll"
#     dimensionDefault = "http://xbrl.org/int/dim/arcrole/dimension-default"
#     dimensionDomain = "http://xbrl.org/int/dim/arcrole/dimension-domain"
#     domainMember = "http://xbrl.org/int/dim/arcrole/domain-member"
#     hypercubeDimension = "http://xbrl.org/int/dim/arcrole/hypercube-dimension"


@dataclass
class PresentationNode:
    concept_id: str
    order: float
    level: int
    children: List[str] = field(default_factory=list)
    concept: Optional[Union['Concept', 'AbstractConcept']] = None
    
    def __hash__(self) -> int:
        return hash(self.concept_id)


@dataclass
class Presentation:
    network_uri: str
    model_xbrl: ModelXbrl
    process_report: 'process_report'
    
    nodes: Dict[str, PresentationNode] = field(init=False, default_factory=dict)
    validated_facts: List['Fact'] = field(init=False, default_factory=list)
    fact_lookup: Dict[str, List['Fact']] = field(init=False, 
                                              default_factory=lambda: defaultdict(list))
    
    def __post_init__(self) -> None:
        try:
            self._build_hierarchy()
        except Exception as e:
            raise ValueError(f"Failed to build presentation hierarchy: {e}")
    
    def _build_hierarchy(self) -> None:
        rel_set = self.model_xbrl.relationshipSet(XbrlConst.parentChild, self.network_uri)
        if not rel_set:
            return
            
        parent_child_map: Dict[str, List[tuple[str, float]]] = {}
        
        for rel in rel_set.modelRelationships:
            parent_id = f"{rel.fromModelObject.qname.namespaceURI}:{rel.fromModelObject.qname}"
            child_id = f"{rel.toModelObject.qname.namespaceURI}:{rel.toModelObject.qname}"
            
            for model_obj in (rel.fromModelObject, rel.toModelObject):
                if model_obj.isAbstract:
                    self._build_abstracts(model_obj)
            

            if parent_id not in parent_child_map:
                parent_child_map[parent_id] = []
            parent_child_map[parent_id].append((child_id, rel.order or 0))
        
        self._build_nodes(parent_child_map)

    def _build_abstracts(self, model_concept: ModelConcept) -> None:
        concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"
        
        if (concept_id not in self.process_report._concept_lookup and 
            concept_id not in self.process_report._abstract_lookup):
            try:
                abstract = AbstractConcept(model_concept)
                self.process_report.abstracts.append(abstract)
                self.process_report._abstract_lookup[abstract.id] = abstract
            except Exception as e:
                raise ValueError(f"Failed to create AbstractConcept {concept_id}: {e}")
    
    def _build_nodes(self, parent_child_map: Dict[str, List[tuple[str, float]]]) -> None:
        def build_node(concept_id: str, level: int) -> None:
            if concept_id not in self.nodes:
                children = sorted(parent_child_map.get(concept_id, []), key=lambda x: x[1])
                self.nodes[concept_id] = PresentationNode(
                    concept_id=concept_id,
                    order=1,
                    level=level,
                    children=[child_id for child_id, _ in children],
                    concept=self.get_concept(concept_id)
                )
                
                for child_id, order in children:
                    build_node(child_id, level + 1)
                    self.nodes[child_id].order = order
        
        root_ids = (set(parent_child_map.keys()) - 
                   {child for children in parent_child_map.values() 
                    for child, _ in children})
        
        for i, root_id in enumerate(sorted(root_ids), 1):
            build_node(root_id, 1)
            self.nodes[root_id].order = i

    def get_concept(self, concept_id: str) -> Optional[Union['Concept', 'AbstractConcept']]:
        return (self.process_report._concept_lookup.get(concept_id) or 
                self.process_report._abstract_lookup.get(concept_id))
    
    def get_node(self, concept_id: str) -> Optional[PresentationNode]:
        return self.nodes.get(concept_id)
    
    def get_children(self, node: PresentationNode) -> List[PresentationNode]:
        return [self.nodes[child_id] for child_id in node.children]
    
    @property
    def roots(self) -> Set[PresentationNode]:
        all_parents = {concept_id for concept_id, node in self.nodes.items() 
                      if node.children}
        all_children = {child_id for node in self.nodes.values() 
                       for child_id in node.children}
        return {self.nodes[concept_id] for concept_id in all_parents - all_children}



@dataclass
class CalculationNode:
    concept_id: str
    weight: float
    order: float
    level: int
    concept: Optional['Concept'] = None
    children: List[str] = field(default_factory=list)
    
    def __hash__(self) -> int:
        return hash(self.concept_id)


@dataclass
class Calculation:
    network_uri: str
    model_xbrl: ModelXbrl
    name: str
    process_report: 'process_report'
    
    nodes: Dict[str, CalculationNode] = field(init=False, default_factory=dict)
    validated_facts: List['Fact'] = field(init=False, default_factory=list)
    fact_lookup: Dict[str, List['Fact']] = field(init=False, 
                                              default_factory=lambda: defaultdict(list))
    
    def __post_init__(self) -> None:
        try:
            self._build_hierarchy()
        except Exception as e:
            raise ValueError(f"Failed to build calculation hierarchy: {e}")

    def _build_hierarchy(self) -> None:
        rel_set = self.model_xbrl.relationshipSet(XbrlConst.summationItem, self.network_uri)
        if not rel_set:
            return
                
        parent_child_map: Dict[str, List[tuple[str, float, float]]] = {}
        
        for rel in rel_set.modelRelationships:
            try:
                parent_id = f"{rel.fromModelObject.qname.namespaceURI}:{rel.fromModelObject.qname}"
                child_id = f"{rel.toModelObject.qname.namespaceURI}:{rel.toModelObject.qname}"
                # parent_child_map[parent_id].append((child_id, rel.weight, rel.order or 1.0))
                if parent_id not in parent_child_map:
                    parent_child_map[parent_id] = []
                parent_child_map[parent_id].append((child_id, rel.weight, rel.order or 1.0))


            except AttributeError as e:
                print(f"DEBUG - Error processing relationship: {e}")
        
        self._build_nodes(parent_child_map)

    def _build_nodes(self, parent_child_map: Dict[str, List[tuple[str, float, float]]]) -> None:
        
        def build_node(concept_id: str, level: int) -> None:
            if concept_id not in self.nodes:
                children = sorted(parent_child_map.get(concept_id, []), key=lambda x: x[2])
                self.nodes[concept_id] = CalculationNode(
                    concept_id=concept_id,
                    weight=1.0,
                    order=1.0,
                    level=level,
                    children=[child_id for child_id, _, _ in children],
                    concept=self.get_concept(concept_id)
                )
                
                for child_id, weight, order in children:
                    build_node(child_id, level + 1)
                    child_node = self.nodes[child_id]
                    child_node.weight = weight
                    child_node.order = order
        
        root_ids = (set(parent_child_map.keys()) - 
                   {child for children in parent_child_map.values() 
                    for child, _, _ in children})
        
        for i, root_id in enumerate(sorted(root_ids), 1):
            build_node(root_id, 1)
            self.nodes[root_id].order = i


    def get_concept(self, concept_id: str) -> Optional['Concept']:
        return self.process_report._concept_lookup.get(concept_id)
    
    def get_node(self, concept_id: str) -> Optional[CalculationNode]:
        return self.nodes.get(concept_id)
    
    def get_children(self, node: CalculationNode) -> List[CalculationNode]:
        return [self.nodes[child_id] for child_id in node.children]
    
    @property
    def roots(self) -> Set[CalculationNode]:
        all_parents = {concept_id for concept_id, node in self.nodes.items() 
                      if node.children}
        all_children = {child_id for node in self.nodes.values() 
                       for child_id in node.children}
        return {self.nodes[concept_id] for concept_id in all_parents - all_children}



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
    concepts: List['Concept'] = field(init=False, default_factory=list) 

    relationship_sets: List[str] = field(default_factory=list) # check if this is needed
    hypercubes: List['Hypercube'] = field(init=False, default_factory=list)
    presentation: Optional[Presentation] = field(init=False, default=None)
    calculation: Optional[Calculation] = field(init=False, default=None)
    
    report: Optional['process_report'] = None # Inorder to validate facts, we need to pass the report
    taxonomy: Optional['Taxonomy'] = None 

    # Add field to store validated facts
    validated_facts: List['Fact'] = field(init=False, default_factory=list)


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
