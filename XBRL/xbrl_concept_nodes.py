"""
This module contains concept-related node implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Local imports
from .validation import ValidationMixin
from .utils import *
from .xbrl_core import Neo4jNode, NodeType, ReportElementClassifier

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
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
    facts: List['Fact'] = field(init=False, default_factory=list)
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

    def add_fact(self, fact: 'Fact') -> None:
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



@dataclass
class GuidanceConcept(Concept):
    """Represents a guidance concept that provides documentation/instructions"""
    guidance_text: Optional[str] = None
    target_concepts: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if self.model_concept is not None:
            self.guidance_text = self._extract_guidance_text()
            self.target_concepts = self._find_target_concepts()
    
    def _extract_guidance_text(self) -> Optional[str]:
        """Extract guidance text from concept documentation"""
        if hasattr(self.model_concept, 'documentation'):
            return self.model_concept.documentation
        return None
        
    def _find_target_concepts(self) -> List[str]:
        """Find concepts this guidance applies to based on concept properties"""
        target_concepts = []
        
        if not self.model_concept:
            return target_concepts

        qname = str(self.model_concept.qname)
        
        # Handle specific guidance types based on their purpose
        if "UseNameOfCryptoAssetAsValueForMemberUnderCryptoAssetDomainGuidance" in qname:
            # Look for crypto asset domain and its members
            for concept in self.model_concept.modelXbrl.qnameConcepts.values():
                if "CryptoAssetDomain" in str(concept.qname):
                    target_concepts.append(str(concept.qname))
                    
        elif "UseFinancialStatementLineItemElementsWithDimensionElementsForBalancesOfVariableInterestEntityVieGuidance" in qname:
            # Look for VIE-related concepts
            for concept in self.model_concept.modelXbrl.qnameConcepts.values():
                concept_name = str(concept.qname)
                if any(term in concept_name for term in ["VariableInterestEntity", "VIE"]):
                    target_concepts.append(concept_name)
                    
        elif "ElementNameAndStandardLabelInMaturityNumericLowerEndToNumericHigherEndDateMeasureMember" in qname:
            # Look for maturity-related concepts
            for concept in self.model_concept.modelXbrl.qnameConcepts.values():
                concept_name = str(concept.qname)
                if any(term in concept_name for term in ["Maturity", "DateMeasure"]):
                    target_concepts.append(concept_name)
                    
        elif "ForInformationOnModelingAccountingChangesSeeImplementationGuide" in qname:
            # Look for accounting change related concepts
            for concept in self.model_concept.modelXbrl.qnameConcepts.values():
                concept_name = str(concept.qname)
                if "AccountingChange" in concept_name:
                    target_concepts.append(concept_name)
        
        print(f"\nGuidance concept: {qname}")
        if target_concepts:
            print(f"Found {len(target_concepts)} target concepts:")
            for target in target_concepts:
                print(f"  - {target}")
        else:
            print("No target concepts found")
        
        return target_concepts



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