"""
This module contains dimension-related implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Local imports
from .validation import ValidationMixin
from .utils import *
from .xbrl_core import Neo4jNode, NodeType, RelationType
from .xbrl_concept_nodes import Concept, AbstractConcept

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .xbrl_processor import process_report, Fact
    from .xbrl_taxonomy import Taxonomy
    from .xbrl_networks import Network, Presentation, Calculation, PresentationNode, CalculationNode
    from .xbrl_reporting import Fact

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
import copy


# Arelle imports
from arelle import Cntlr, ModelDocument, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ModelValue import QName
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelFact, ModelContext, ModelUnit
from arelle.ModelXbrl import ModelXbrl
from enum import Enum

# Handle circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .xbrl_processor import process_report, Fact



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
    domain: Optional['Domain'] = field(init=False, default=None)
    members_dict: Dict[str, 'Member'] = field(default_factory=dict)  # For storing members
    default_member: Optional['Member'] = field(init=False, default=None)
    
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
    def members(self) -> List['Member']:
        """Get unique members sorted by level"""
        return sorted(self.members_dict.values(), key=lambda x: x.level)

    # Returns a dictionary grouping members by their hierarchical depth (levels). - works only for explicit dimensions
    @property
    def members_by_level(self) -> Dict[int, List['Member']]:
        """Get members organized by their hierarchy level"""
        levels: Dict[int, List['Member']] = {}
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
    def add_member(self, member: 'Member') -> None:
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
class Hypercube:
    """Represents a hypercube (table) in an XBRL definition network"""
    model_xbrl: ModelXbrl
    hypercube_item: Any  # hypercube modelConcept, ends with 'Table' (Target of 'all' relationship)    
    network_uri: str     # Reference back to parent network
    dimensions: List[Dimension] = field(init=False) # Dimensions related to the hypercube
    concepts: List['Concept'] = field(init=False)  # Concepts related to the hypercube
    abstracts: List['Concept'] = field(init=False)  # These are Lineitems, abstracts typically used to organize concepts
    lineitems: List['Concept'] = field(init=False)  # These are Lineitems, abstracts typically used to organize concepts
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
                    item=dim_object,
                    network_uri=self.network_uri
                )
                self.dimensions.append(dimension)
            
            except Exception as e: continue

    # Get all concepts related to a hypercube: All dimensions in a hypercube apply to all concepts in that hypercube (as per the specification)
    def _link_hypercube_concepts(self, report_concepts: List['Concept'], report_abstracts: List['AbstractConcept']) -> None:
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
