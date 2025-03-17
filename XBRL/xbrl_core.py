"""
This module contains core classes and constants for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.

IMPORTANT: When using dictionaries or sets, ensure they are iterated in a
deterministic order to match the original implementation. Consider using 
OrderedDict or sorted() when dealing with keys to maintain consistent output.
"""

# Import common dependencies
from .common_imports import *

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .xbrl_basic_nodes import Context, Period, Unit, AdminReportNode, CompanyNode, DateNode, ReportNode
    from .xbrl_concept_nodes import Concept, GuidanceConcept, AbstractConcept
    from .xbrl_taxonomy import Taxonomy
    from .xbrl_dimensions import Dimension, Domain, Member, Hypercube
    from .xbrl_networks import Network, Presentation, Calculation, PresentationNode, CalculationNode
    from .xbrl_reporting import Fact
    from .xbrl_processor import process_report


# Constants for edge properties
PRESENTATION_EDGE_UNIQUE_PROPS = [
    'cik',           # Company identifier
    'report_id',     # Filing identifier
    'network_name',  # Network context
    'parent_id',     # Parent concept
    'child_id',      # Child concept
    'parent_level',  # Position in hierarchy
    'child_level'    # Position in hierarchy
]

CALCULATION_EDGE_UNIQUE_PROPS = [
    'cik',           # Company identifier
    'report_id',     # Filing identifier
    'network_name',  # Network context
    'parent_id',     # Parent concept
    'child_id',      # Child concept
    'context_id'     # Shared context including dimensions
]

# Enum Classes
class GroupingType(Enum):
    CONTEXT = "context"
    PERIOD = "period"


# Commenting out unused types here so they don't create unneccessary nodes in create_indexes
class NodeType(Enum):
    """XBRL node types in Neo4j"""
    
    LINE_ITEMS = "LineItems"
    CONCEPT = "Concept"
    ABSTRACT = "Abstract"
    
    COMPANY = "Company"
    ENTITY = "Entity" # Not using this for now
    REPORT = "Report"

    FACT = "Fact"
    CONTEXT = "Context"
    PERIOD = "Period"
    UNIT = "Unit"           
    OTHER = "Other" # Keep this as it's used as default fallback - 'Other' NodeType is created in create_indexes
    HYPERCUBE = "HyperCube" # Keep this as it's used for table structures determination in presentation hierarchy

    # NAMESPACE = "Namespace"  # Commenting out unused types
    # LINKBASE = "Linkbase"   # that appear in schema but 
    # RESOURCE = "Resource"   # have no actual nodes
    GUIDANCE = "Guidance"    # Keep this for guidance/documentation elements
    # DEPRECATED = "deprecated"
    
    NEWS = "News"  # Added for NewsNode support
    SECTOR = "Sector"  # Added for SectorNode support
    INDUSTRY = "Industry"  # Added for IndustryNode support
    MARKET_INDEX = "MarketIndex"  # Added for MarketIndex support
    
    DIMENSION = "Dimension"
    DOMAIN = "Domain"
    MEMBER = "Member"
    
    DATE = "Date"
    ADMIN_REPORT = "AdminReport"




# Reconcile with Neo4j and remove rest 
class RelationType(Enum):
    """XBRL relationship types"""
    HAS_FACT = "HAS_FACT"
    HAS_CONCEPT = "HAS_CONCEPT"
    HAS_DIMENSION = "HAS_DIMENSION"
    HAS_MEMBER = "HAS_MEMBER"       # Domain/Dimension -> Member
    FACT_MEMBER = "FACT_MEMBER"     # Fact -> Member
    FACT_DIMENSION = "FACT_DIMENSION" # Fact -> Dimension
    HAS_DOMAIN = "HAS_DOMAIN"       # Dimension -> Domain
    PARENT_OF = "PARENT_OF"         # Parent Member -> Child Member
    HAS_DEFAULT = "HAS_DEFAULT"     # Dimension -> Default Member
    MEMBER_OF = "MEMBER_OF"         # Member to Parent Member
    IN_TAXONOMY = "IN_TAXONOMY"     # Dimension/Member to Taxonomy
    CONTAINS = "CONTAINS"          # For Report->Fact relationships
    REPORTS = "REPORTS"            # For Fact->Report relationships
    BELONGS_TO = "BELONGS_TO"
    IN_CONTEXT = "IN_CONTEXT"       # Fact to Context
    HAS_PERIOD = "HAS_PERIOD"       # Context to Period
    HAS_UNIT = "HAS_UNIT"           # Fact to Unit
    PARENT_CHILD = "PARENT_CHILD"   # Presentation hierarchy
    CALCULATION = "CALCULATION"     # Calculation relationships
    DEFINITION = "DEFINITION"       # Definition relationships
    HAS_LABEL = "HAS_LABEL"         # Concept to Label
    HAS_REFERENCE = "HAS_REFERENCE" # Concept to Reference
    NEXT = "NEXT"                   # Next date
    HAS_PRICE = "HAS_PRICE"         # from Date to Entity/Company
    HAS_SUB_REPORT = "HAS_SUB_REPORT"  # For 10-K -> FYE and 10-Q -> Quarters relationships
    REPORTED_ON = "REPORTED_ON"     # From DateNode to ReportNode
    PRESENTATION_EDGE = "PRESENTATION_EDGE" # From Fact to Fact
    CALCULATION_EDGE = "CALCULATION_EDGE" # From Fact to Fact
    FILED_BY = "FILED_BY"           # From Report to Company
    HAS_CATEGORY = "HAS_CATEGORY"   # Report -> AdminReport
    FOR_COMPANY = "FOR_COMPANY"       # Context -> Company
    PROVIDES_GUIDANCE = "PROVIDES_GUIDANCE"  # From Guidance concept to related concept
    INFLUENCES = "INFLUENCES"       # Report/News -> Company relationships
    RELATED_TO = "RELATED_TO"       # Company -> Company relationship as defined by related field in polygon
    


class ReportElementClassifier:
    LINKBASE_ELEMENTS = [
        'link:part', 'xl:extended', 'xl:arc', 'xl:simple', 
        'xl:resource', 'xl:documentation', 'xl:locator', 
        'link:linkbase', 'link:definition', 'link:usedOn', 
        'link:roleType', 'link:arcroleType'
    ]
    
    DATE_ELEMENTS = [
        'xbrli:instant', 'xbrli:startDate', 'xbrli:endDate', 
        'dei:eventDateTime', 'xbrli:forever'
    ]

    @staticmethod
    def get_substitution_group(concept: Any) -> str:
        return (str(concept.substitutionGroupQname) 
                if concept.substitutionGroupQname else "N/A")

    @staticmethod
    def get_local_type(concept: Any) -> str:
        return (str(concept.typeQname.localName) 
                if concept.typeQname else '')

    @staticmethod
    def check_nillable(concept: Any) -> bool:
        return (concept.nillable == 'true')

    @staticmethod
    def check_duration(concept: Any) -> bool:
        return (concept.periodType == 'duration')

    @classmethod
    def classify(cls, concept: Any) -> NodeType:
        qname_str = str(concept.qname)
        sub_group = cls.get_substitution_group(concept)
        local_type = cls.get_local_type(concept)
        nillable = cls.check_nillable(concept)
        duration = cls.check_duration(concept)

        # Initial classification
        category = cls._initial_classify(concept, qname_str, sub_group, 
                                      local_type, nillable, duration)
        
        # Integrated post-classification
        if category == NodeType.OTHER:
            category = cls._post_classify_single(concept, qname_str, sub_group)
        
        return category

    @classmethod
    def _initial_classify(cls, concept, qname_str, sub_group, local_type, 
                         nillable, duration) -> NodeType:
        # 1. Basic Concept
        if not concept.isAbstract and sub_group == 'xbrli:item':
            return NodeType.CONCEPT
        
        # 2. Hypercube [Table]
        if (concept.isAbstract and 
            sub_group == 'xbrldt:hypercubeItem' and
            duration and nillable):
            return NodeType.HYPERCUBE
        
        # 3. Dimension [Axis] - here we could also just use "concept.isDimensionItem"
        if (concept.isAbstract and 
            sub_group == 'xbrldt:dimensionItem' and 
            duration and nillable):
            return NodeType.DIMENSION
        
        # 4. Member [Domain/Member]
        if ((any(qname_str.endswith(suffix) for suffix in ["Domain", "domain", "Member"]) or 
             local_type == 'domainItemType') and 
            duration and nillable):
            return NodeType.MEMBER
        
        # 5. Abstract
        if any(qname_str.endswith(suffix) for suffix in [
            "Abstract", "Hierarchy", "RollUp", 
            "RollForward", "Rollforward"
        ]) and concept.isAbstract:
            return NodeType.ABSTRACT
        
        # 6. LineItems
        if "LineItems" in qname_str and duration and nillable:
            return NodeType.LINE_ITEMS
        
        # 7. Guidance
        if local_type == 'guidanceItemType' or "guidance" in qname_str.lower():
            return NodeType.GUIDANCE

        # Return OTHER for everything else
        return NodeType.OTHER

    @classmethod
    def _post_classify_single(cls, concept, qname_str, sub_group) -> NodeType:
        """Additional classification checks for special cases"""
        # Remove LINKBASE check since we commented it out
        # if sub_group in cls.LINKBASE_ELEMENTS:
        #     return NodeType.LINKBASE
        
        return NodeType.OTHER


    @classmethod
    def wrap_concept(cls, concept: Any, model_xbrl: ModelXbrl, network_uri: str) -> 'Union[Any, None]':
        """Wrap a ModelConcept into the appropriate node type based on classification"""
        # Import dimensions classes inside the method to avoid circular imports
        from .xbrl_dimensions import Dimension, Domain, Member
        
        if not concept:
            print("DEBUG - Received None concept")
            return None
            
        print(f"\nDEBUG - wrap_concept called for: {getattr(concept, 'qname', 'No qname')}")
        print(f"DEBUG - Original type: {type(concept)}")
        
        # Store the qname before any transformations
        original_qname = getattr(concept, 'qname', None)
        
        # Get the ModelConcept depending on what type we received
        if isinstance(concept, (AbstractConcept, Concept)):
            model_concept = getattr(concept, 'model_concept', None)
            if model_concept is None:
                print(f"DEBUG - No model_concept found in {type(concept).__name__}")
                return None
                
            # Only try to set qname if model_concept exists
            if not hasattr(model_concept, 'qname') and original_qname:
                try:
                    setattr(model_concept, 'qname', original_qname)
                except AttributeError:
                    print(f"DEBUG - Could not set qname on model_concept")
                    return None
                    
            print(f"DEBUG - Getting model_concept from {type(concept).__name__}")
        else:
            model_concept = concept
            print(f"DEBUG - Using original concept")

        # Verify we have a valid concept with qname
        if not hasattr(model_concept, 'qname'):
            print(f"DEBUG - Missing qname, attempting to restore from original")
            if original_qname:
                try:
                    setattr(model_concept, 'qname', original_qname)
                except AttributeError:
                    print(f"DEBUG - Cannot restore qname")
                    return None
            else:
                print(f"DEBUG - No qname available")
                return None

        if isinstance(model_concept, ModelConcept):
            category = cls.classify(model_concept)
            print(f"DEBUG - Classified as: {category}")
            
            # Rest of the wrapping logic remains the same
            if category == NodeType.DIMENSION:
                return Dimension(
                    model_xbrl=model_xbrl,
                    item=model_concept,
                    network_uri=network_uri
                )
            elif category == NodeType.MEMBER:
                return Member(
                    model_xbrl=model_xbrl,
                    item=model_concept,
                    parent_qname=None,
                    level=0
                )
            elif category == NodeType.DOMAIN:
                return Domain(
                    model_xbrl=model_xbrl,
                    item=model_concept
                )
            elif category in [NodeType.ABSTRACT, NodeType.LINE_ITEMS]:
                return AbstractConcept(model_concept)
            elif category == NodeType.HYPERCUBE:
                return AbstractConcept(model_concept)
                
            print(f"DEBUG - No wrapper created for category: {category}")
        else:
            print(f"DEBUG - Invalid concept: missing qname")
        return None


class Neo4jNode(ABC):
    """Abstract base class for nodes in the XBRL graph."""
    
    @property
    @abstractmethod
    def node_type(self) -> NodeType:
        """Return the type of the node."""
        pass
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Return a unique identifier for the node."""
        pass
        
    @property
    @abstractmethod
    def properties(self) -> Dict[str, Any]:
        """Return properties to store in Neo4j."""
        pass
    
    @classmethod
    def from_neo4j(cls, properties: Dict[str, Any]):
        """Create instance from Neo4j properties"""
        # Clean properties and convert "null" to None
        cleaned_props = {
            k: None if v == "null" else v
            for k, v in properties.items()
            if k not in {'id', 'elementId'} and not k.startswith('_')
        }
        
        # Get the constructor parameters
        init_params = {
            k: cleaned_props.get(k)
            for k in cls.__init__.__code__.co_varnames[1:]  # Skip 'self'
            if k in cleaned_props
        }
        
        return cls(**init_params)