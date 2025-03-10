"""
This module contains fact and reporting-related implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Local imports
from .validation import ValidationMixin
from .utils import *
from .xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType
from .xbrl_basic_nodes import Context, Period, Unit
from .xbrl_concept_nodes import Concept

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .xbrl_processor import process_report
    # Concept already imported above
    from .xbrl_networks import Network, Presentation, Calculation
    from .xbrl_taxonomy import Taxonomy
    from .xbrl_dimensions import Dimension, Domain, Member, Hypercube  
    # Context, Period, Unit already imported above

# Handle circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .xbrl_processor import process_report


@dataclass
class Fact(Neo4jNode):
    model_fact: ModelFact
    _report: 'process_report' = field(repr=False, default=None) 
    refers_to: Optional['Fact'] = None  # 

    # Globally unique fact identifier
    u_id: str = field(init=False)        # Globally u_id (see _generate_unique_fact_id)

    # Fact properties
    qname: str = field(init=False)  # Its 'concept' name
    fact_id: str = field(init=False)   # Original fact ID from the XBRL document (e.g., f-32)
    value: str = field(init=False)    
    context_id: str = field(init=False)    
    decimals: Optional[int] = field(init=False, default=None)
            
    # To Link:
    concept: Optional['Concept'] = field(init=False, default=None)
    unit: Optional['Unit'] = field(init=False, default=None)
    period: Optional['Period'] = field(init=False, default=None)

    # dims_members: Optional[List[Tuple[Dimension, Member]]] = field(init=False, default_factory=list)
    # Note: In fact, for each dimension, there can be only one member 
    dims_members: Optional[List[Tuple[Any, Any]]] = field(init=False, default_factory=list)
    

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
        # Import inside method to avoid circular imports
        from .xbrl_dimensions import Dimension, Member
        
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

