"""
XBRL Processing Package

This package provides a complete solution for processing XBRL documents,
extracting data, and storing it in a Neo4j graph database.
"""

# IMPORTANT: The import order matters for producing identical output.

# Import common dependencies first
from .common_imports import (
    # Re-export useful types
    List, Dict, Optional, Any, Union, Set, Type, Tuple, 
    dataclass, field, fields, 
    ABC, abstractmethod,
    defaultdict, OrderedDict,
    datetime, date, timedelta,
    ModelXbrl, ModelFact, ModelContext, ModelConcept
)

# First import core definitions
from .xbrl_core import (
    Neo4jNode, NodeType, RelationType, GroupingType, ReportElementClassifier,
    PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS
)

# Import utility functions
from .utils import (
    clean_number, 
    resolve_primary_fact_relationships
)

# Import basic node implementations first
from .xbrl_basic_nodes import (
    Context, Period, Unit, 
    CompanyNode, ReportNode
)

# Import concept node implementations
from .xbrl_concept_nodes import Concept, GuidanceConcept, AbstractConcept

# Import dimension-related classes
from .xbrl_dimensions import Dimension, Domain, Member, Hypercube

# Import taxonomy
from .xbrl_taxonomy import Taxonomy

# Import network-related classes
from .xbrl_networks import Network, Presentation, Calculation, PresentationNode, CalculationNode

# Import reporting classes
from .xbrl_reporting import Fact

# Import the process_report class from our wrapper
from .xbrl_processor import process_report

# Define what's exposed in the package namespace
__all__ = [
    # Core definitions
    'Neo4jNode', 'NodeType', 'RelationType', 'GroupingType', 'ReportElementClassifier',
    'PRESENTATION_EDGE_UNIQUE_PROPS', 'CALCULATION_EDGE_UNIQUE_PROPS',
    
    # Basic node implementations
    'Context', 'Period', 'Unit',
    'CompanyNode', 'ReportNode',
    
    # Concept node implementations
    'Concept', 'GuidanceConcept', 'AbstractConcept',
    
    # Taxonomy
    'Taxonomy',
    
    # Dimension-related classes
    'Dimension', 'Domain', 'Member', 'Hypercube',
    
    # Network-related classes
    'Network', 'Presentation', 'Calculation', 'PresentationNode', 'CalculationNode',
    
    # Reporting classes
    'Fact',
    
    # Utility functions
    'clean_number',
    'resolve_primary_fact_relationships',
    
    # Process report class
    'process_report',
    
    # Re-exported types for convenience
    'List', 'Dict', 'Optional', 'Any', 'Union', 'Set', 'Type', 'Tuple',
    'dataclass', 'field', 'fields',
    'ABC', 'abstractmethod',
    'defaultdict', 'OrderedDict',
    'datetime', 'date', 'timedelta',
    'ModelXbrl', 'ModelFact', 'ModelContext', 'ModelConcept'
]