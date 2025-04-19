from __future__ import annotations
from XBRL.validation import ValidationMixin  # Use absolute import
# from validation import ValidationMixin
from XBRL.utils import *

# Import classes that have been moved to other modules
from XBRL.xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType, PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS, ReportElementClassifier
from XBRL.xbrl_basic_nodes import Context, Period, Unit
from neograph.EventTraderNodes import CompanyNode, ReportNode
from XBRL.xbrl_concept_nodes import Concept, GuidanceConcept, AbstractConcept
from XBRL.xbrl_taxonomy import Taxonomy
from XBRL.xbrl_dimensions import Dimension, Domain, Member, Hypercube
from XBRL.xbrl_networks import Network, Presentation, Calculation, PresentationNode, CalculationNode
from XBRL.xbrl_processor import process_report, Fact

# dataclasses and typing imports
from dataclasses import dataclass, field, fields
from typing import List, Dict, Optional, Any, Union, Set, Type, Tuple, TypeVar, Generic, Callable
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from neograph.Neo4jManager import Neo4jManager

# Arelle imports
from arelle import Cntlr, ModelDocument, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ModelValue import QName
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelFact, ModelContext, ModelUnit
from arelle.ModelXbrl import ModelXbrl
from enum import Enum


# GroupingType class has been moved to xbrl_core.py and is imported from there
# Neo4jNode class has been moved to xbrl_core.py and is imported from there
# process_report class has been moved to xbrl_processor.py and is imported from there
# Context class has been moved to xbrl_basic_nodes.py and is imported from there
# Period class has been moved to xbrl_basic_nodes.py and is imported from there
# Unit class has been moved to xbrl_basic_nodes.py and is imported from there
# ReportNode class has been moved to xbrl_basic_nodes.py and is imported from there
# Fact class has been moved to xbrl_reporting.py and is imported from there

# These utility functions have been moved to utils.py
# create_date_range, create_date_relationships were removed


def count_report_hierarchy(report) -> None:
    """
    Exhaustive validation of the report hierarchy.
    Counts all elements in the report structure and relationships between them.
    
    Args:
        report: A report instance with XBRL data
    """
    print("\nREPORT ELEMENT COUNT BY HIERARCHY")
    print("=" * 50)

    # Report Base Stats - only count what we know exists
    print("\nReport Base")
    print(f"├→ Facts: {len(getattr(report, 'facts', []))}")
    print(f"├→ Concepts: {len(getattr(report, 'concepts', []))}")
    print(f"├→ Abstracts: {len(getattr(report, 'abstracts', []))}")
    print(f"├→ Periods: {len(getattr(report, 'periods', []))}")
    print(f"├→ Units: {len(getattr(report, 'units', []))}")
    print(f"└→ Networks: {len(getattr(report, 'networks', []))}")

    # Skip further processing if no networks are available
    if not hasattr(report, 'networks') or not report.networks:
        print("\nNo networks available in the report.")
        return

    # Networks by Category
    print("\nReport → Networks → Categories")
    network_categories = {}
    for network in report.networks:
        category = getattr(network, 'category', 'Unknown')
        network_categories[category] = network_categories.get(category, 0) + 1
    
    for category, count in sorted(network_categories.items()):
        print(f"├→ {category}: {count}")
    print(f"└→ Total Categories: {len(network_categories)}")

    # Network Types by relationship types (.isPresentation, .isCalculation, .isDefinition)
    print("\nReport → Networks")
    total_networks = len(report.networks)
    
    # Safely check if attributes exist and are callable
    def safe_network_check(network, attr_name):
        try:
            attr = getattr(network, attr_name, None)
            if attr is None:
                return False
            elif callable(attr):
                return attr()
            else:
                return bool(attr)
        except Exception:
            return False
    
    presentation_networks = sum(1 for network in report.networks 
                              if safe_network_check(network, 'isPresentation'))
    calculation_networks = sum(1 for network in report.networks 
                             if safe_network_check(network, 'isCalculation'))
    definition_networks = sum(1 for network in report.networks 
                            if safe_network_check(network, 'isDefinition'))
    
    print(f"├→ Total Networks: {total_networks}")
    print(f"├→ Presentation Networks: {presentation_networks}")
    print(f"├→ Calculation Networks: {calculation_networks}")
    print(f"└→ Definition Networks: {definition_networks}")

    # Presentation Hierarchies - safely access properties
    print("\nReport → Networks → Presentations")
    presentations = []
    for network in report.networks:
        if hasattr(network, 'presentation') and network.presentation is not None:
            presentations.append(network.presentation)
    
    # Safely count nodes in presentations
    total_presentation_nodes = 0
    for p in presentations:
        try:
            if hasattr(p, 'nodes'):
                total_presentation_nodes += len(p.nodes)
        except Exception:
            pass
            
    # Safely count root nodes
    root_nodes = 0
    for p in presentations:
        try:
            if hasattr(p, 'roots'):
                if isinstance(p.roots, (list, tuple, set)):
                    root_nodes += len(p.roots)
                elif hasattr(p.roots, '__len__'):
                    root_nodes += len(p.roots)
        except Exception:
            pass
            
    print(f"├→ Total Presentations: {len(presentations)}")
    print(f"├→ Total Nodes: {total_presentation_nodes}")
    print(f"└→ Root Nodes: {root_nodes}")

    # Networks → Hypercubes - safely count hypercubes
    print("\nReport → Networks → Hypercubes")
    total_hypercubes = 0
    unique_hypercube_qnames = set()
    
    for network in report.networks:
        try:
            if hasattr(network, 'hypercubes'):
                total_hypercubes += len(network.hypercubes)
                for hypercube in network.hypercubes:
                    if hasattr(hypercube, 'qname'):
                        unique_hypercube_qnames.add(str(hypercube.qname))
        except Exception:
            pass
            
    print(f"├→ Total Hypercubes: {total_hypercubes}")
    print(f"└→ Unique Hypercube Names: {len(unique_hypercube_qnames)}")

    # Networks → Hypercubes → Concepts
    print("\nReport → Networks → Hypercubes → Concepts")
    total_hypercube_concepts = 0
    unique_hypercube_concept_qnames = set()
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if hasattr(hypercube, 'concepts'):
                    total_hypercube_concepts += len(hypercube.concepts)
                    for concept in hypercube.concepts:
                        if hasattr(concept, 'qname'):
                            unique_hypercube_concept_qnames.add(str(concept.qname))
        except Exception:
            pass
            
    print(f"├→ Total Hypercube Concepts: {total_hypercube_concepts}")
    print(f"└→ Unique Hypercube Concepts: {len(unique_hypercube_concept_qnames)}")

    # Networks → Hypercubes → Abstracts
    print("\nReport → Networks → Hypercubes → Abstracts")
    total_hypercube_abstracts = 0
    unique_hypercube_abstract_qnames = set()
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if hasattr(hypercube, 'abstracts'):
                    total_hypercube_abstracts += len(hypercube.abstracts)
                    for abstract in hypercube.abstracts:
                        if hasattr(abstract, 'qname'):
                            unique_hypercube_abstract_qnames.add(str(abstract.qname))
        except Exception:
            pass
            
    print(f"├→ Total Hypercube Abstracts: {total_hypercube_abstracts}")
    print(f"└→ Unique Hypercube Abstracts: {len(unique_hypercube_abstract_qnames)}")

    # Networks → Hypercubes → Lineitems
    print("\nReport → Networks → Hypercubes → Lineitems")
    total_hypercube_lineitems = 0
    unique_hypercube_lineitem_qnames = set()
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if hasattr(hypercube, 'lineitems'):
                    total_hypercube_lineitems += len(hypercube.lineitems)
                    for lineitem in hypercube.lineitems:
                        if hasattr(lineitem, 'qname'):
                            unique_hypercube_lineitem_qnames.add(str(lineitem.qname))
        except Exception:
            pass
            
    print(f"├→ Total Hypercube Lineitems: {total_hypercube_lineitems}")
    print(f"└→ Unique Hypercube Lineitems: {len(unique_hypercube_lineitem_qnames)}")

    # Networks → Hypercubes → Dimensions
    print("\nReport → Networks → Hypercubes → Dimensions")
    total_dimensions = 0
    unique_dimension_qnames = set()
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if hasattr(hypercube, 'dimensions'):
                    total_dimensions += len(hypercube.dimensions)
                    for dimension in hypercube.dimensions:
                        if hasattr(dimension, 'qname'):
                            unique_dimension_qnames.add(str(dimension.qname))
        except Exception:
            pass
            
    print(f"├→ Total Dimensions: {total_dimensions}")
    print(f"└→ Unique Dimensions: {len(unique_dimension_qnames)}")

    # Networks → Hypercubes → Dimensions → Members
    print("\nReport → Networks → Hypercubes → Dimensions → Members")
    total_members = 0
    unique_member_qnames = set()
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if not hasattr(hypercube, 'dimensions'):
                    continue
                    
                for dimension in hypercube.dimensions:
                    # Handle both members_dict and members properties
                    if hasattr(dimension, 'members_dict'):
                        total_members += len(dimension.members_dict)
                        for member in dimension.members_dict.values():
                            if hasattr(member, 'qname'):
                                unique_member_qnames.add(str(member.qname))
                    elif hasattr(dimension, 'members'):
                        # This might be a property method or a list
                        members = dimension.members
                        if callable(members):
                            members = members()
                            
                        if isinstance(members, (list, tuple, set, dict)):
                            total_members += len(members)
                            for member in members:
                                if hasattr(member, 'qname'):
                                    unique_member_qnames.add(str(member.qname))
        except Exception:
            pass
            
    print(f"├→ Total Members: {total_members}")
    print(f"└→ Unique Members: {len(unique_member_qnames)}")

    # Networks → Hypercubes → Dimensions → Default Members
    print("\nReport → Networks → Hypercubes → Dimensions → Default Members")
    default_members = set()
    total_default_members = 0
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if not hasattr(hypercube, 'dimensions'):
                    continue
                    
                for dimension in hypercube.dimensions:
                    if hasattr(dimension, 'default_member') and dimension.default_member:
                        total_default_members += 1
                        if hasattr(dimension.default_member, 'qname'):
                            default_members.add(str(dimension.default_member.qname))
        except Exception:
            pass
            
    print(f"├→ Total Default Members: {total_default_members}")
    print(f"└→ Unique Default Members: {len(default_members)}")

    # Networks → Hypercubes → Dimensions → Domains
    print("\nReport → Networks → Hypercubes → Dimensions → Domains")
    total_domains = 0
    unique_domain_qnames = set()
    
    for network in report.networks:
        try:
            if not hasattr(network, 'hypercubes'):
                continue
                
            for hypercube in network.hypercubes:
                if not hasattr(hypercube, 'dimensions'):
                    continue
                    
                for dimension in hypercube.dimensions:
                    if hasattr(dimension, 'domain') and dimension.domain:
                        total_domains += 1
                        if hasattr(dimension.domain, 'qname'):
                            unique_domain_qnames.add(str(dimension.domain.qname))
        except Exception:
            pass
            
    print(f"├→ Total Domains: {total_domains}")
    print(f"└→ Unique Domains: {len(unique_domain_qnames)}")

    # Facts → Relationships
    print("\nReport → Facts → Relationships")
    
    # Safely count fact-to-concept relationships
    facts_with_concepts = 0
    for fact in getattr(report, 'facts', []):
        try:
            if hasattr(fact, 'concept') and fact.concept:
                facts_with_concepts += 1
        except Exception:
            pass
            
    # Safely count fact-to-unit relationships  
    facts_with_units = 0
    for fact in getattr(report, 'facts', []):
        try:
            if hasattr(fact, 'unit') and fact.unit:
                facts_with_units += 1
        except Exception:
            pass
            
    # Safely count fact-to-period relationships
    facts_with_periods = 0
    for fact in getattr(report, 'facts', []):
        try:
            if hasattr(fact, 'period') and fact.period:
                facts_with_periods += 1
        except Exception:
            pass
            
    # Safely count fact-to-context relationships
    facts_with_contexts = 0
    for fact in getattr(report, 'facts', []):
        try:
            if hasattr(fact, 'context_id') and fact.context_id:
                facts_with_contexts += 1
        except Exception:
            pass
            
    print(f"├→ Facts → Concepts: {facts_with_concepts}")
    print(f"├→ Facts → Units: {facts_with_units}")
    print(f"├→ Facts → Periods: {facts_with_periods}")
    print(f"└→ Facts → Context IDs: {facts_with_contexts}")

    # Neo4j Database Stats (if available)
    if hasattr(report, 'neo4j') and hasattr(report.neo4j, 'get_neo4j_db_counts'):
        print("\nNeo4j Database Stats")
        try:
            report.neo4j.get_neo4j_db_counts()
        except Exception as e:
            print(f"Error getting Neo4j stats: {e}")

# endregion : Admin/Helpers ########################

# Classes have been moved to their respective modules:
# - GuidanceConcept -> xbrl_concept_nodes.py
# - Dimension, Domain, Member, Hypercube -> xbrl_dimensions.py
# - Network, Presentation, Calculation -> xbrl_networks.py
# - process_report, Fact -> xbrl_processor.py

