"""
This module contains taxonomy-related implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Local imports
from .validation import ValidationMixin
from .utils import *
from .xbrl_core import Neo4jNode, NodeType, RelationType
from .xbrl_dimensions import Dimension, Domain, Member

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # Dimension, Domain, Member already imported above
    from .xbrl_networks import Network, Presentation, Calculation
    from .xbrl_processor import process_report
    from .xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType, PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS, ReportElementClassifier
    from .xbrl_basic_nodes import Context, Period, Unit
    from neograph.EventTraderNodes import CompanyNode, ReportNode
    from .xbrl_concept_nodes import Concept, GuidanceConcept, AbstractConcept

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




@dataclass
class Taxonomy:
    model_xbrl: ModelXbrl
    dimensions: List['Dimension'] = field(default_factory=list)
    _dimension_lookup: Dict[str, 'Dimension'] = field(default_factory=dict)
    
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
    def get_all_members(self) -> List['Member']:
        """Get all members across all dimensions"""
        return [
            member 
            for dim in self.dimensions 
            if dim.members_dict
            for member in dim.members_dict.values()
        ]

    # Not used anywhere
    def get_dimension_members(self, dimension_qname: str) -> List['Member']:
        """Get members for a specific dimension"""
        dimension = self._dimension_lookup.get(dimension_qname)         # Using lookup table to get Dimension Instance
        if dimension and dimension.members_dict:
            return list(dimension.members_dict.values())
        return []    
