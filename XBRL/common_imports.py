"""
Common imports module for the XBRL package.

This module centralizes common imports used across the XBRL processing modules,
helping to reduce code duplication and manage dependencies effectively.
"""

# Standard library imports
from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field, fields
from datetime import datetime, date, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any, Union, Set, Type, Tuple, OrderedDict, TypeVar, Generic

# Third-party imports
import pandas as pd
import re
import html
import sys
import os
import copy
from neo4j import GraphDatabase, Driver

# Arelle imports
from arelle import Cntlr, ModelDocument, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ModelValue import QName
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelFact, ModelContext, ModelUnit
from arelle.ModelXbrl import ModelXbrl

# Type aliases for type checking
T = TypeVar('T')
NodeT = TypeVar('NodeT', bound='Neo4jNode') 