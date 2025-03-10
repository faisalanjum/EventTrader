from __future__ import annotations
from XBRL.validation import ValidationMixin  # Use absolute import
# from validation import ValidationMixin
from XBRL.utils import *

# Import classes that have been moved to other modules
from XBRL.xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType, PRESENTATION_EDGE_UNIQUE_PROPS, CALCULATION_EDGE_UNIQUE_PROPS, ReportElementClassifier
from XBRL.xbrl_basic_nodes import Context, Period, Unit, AdminReportNode, CompanyNode, DateNode, ReportNode
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
    from .Neo4jManager import Neo4jManager

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
# AdminReportNode class has been moved to xbrl_basic_nodes.py and is imported from there
# CompanyNode class has been moved to xbrl_basic_nodes.py and is imported from there
# DateNode class has been moved to xbrl_basic_nodes.py and is imported from there
# ReportNode class has been moved to xbrl_basic_nodes.py and is imported from there
# Fact class has been moved to xbrl_reporting.py and is imported from there

# These utility functions have been moved to utils.py
# create_date_range, create_date_relationships, get_company_info, get_report_info


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

# Classes have been moved to their respective modules:
# - GuidanceConcept -> xbrl_concept_nodes.py
# - Dimension, Domain, Member, Hypercube -> xbrl_dimensions.py
# - Network, Presentation, Calculation -> xbrl_networks.py
# - process_report, Fact -> xbrl_processor.py

