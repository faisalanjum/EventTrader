"""
This module contains basic node implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Import node types from core module
from .xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType

# Note: ReportNode and CompanyNode are imported directly from neograph.EventTraderNodes
# where needed to avoid circular imports

from arelle.ModelInstanceObject import ModelFact, ModelContext


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
    



