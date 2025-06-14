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
    from .xbrl_basic_nodes import Context, Period, Unit
    from neograph.EventTraderNodes import CompanyNode, ReportNode
    # from neograph.EventTraderNodes import AdminReportNode
    from .xbrl_concept_nodes import Concept, GuidanceConcept, AbstractConcept
    from .xbrl_taxonomy import Taxonomy
    from .xbrl_dimensions import Dimension, Domain, Member, Hypercube
    from .xbrl_networks import Network, Presentation, Calculation, PresentationNode, CalculationNode
    from .xbrl_reporting import Fact
    from .xbrl_processor import process_report

import logging
logger = logging.getLogger(__name__)

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
    'cik',            # Company identifier
    'report_id',      # Filing identifier / XBRL instance
    'network_uri',    # Canonical link-role URI (always unique)
    'parent_id',      # Parent fact unique id
    'child_id',       # Child fact unique id
    'context_id',     # Period/entity/dimensions slice
    'weight'          # Arc weight (+1, ‑1, 120%, etc.)
]

# Enum Classes
class GroupingType(Enum):
    CONTEXT = "context"
    PERIOD = "period"


# Commenting out unused types here so they don't create unneccessary nodes in create_indexes
class NodeType(Enum):
    """XBRL node types"""
    CONCEPT = "Concept"
    ABSTRACT = "Abstract"
    FACT = "Fact"
    PERIOD = "Period"
    UNIT = "Unit"
    CONTEXT = "Context" # Includes dimensions & members?
    REPORT = "Report"    # Filing
    COMPANY = "Company"  # Entity
    XBRLNODE = "XBRLNode"  # Changed from XBRL to XBRLNODE
    
    # Table structures - used in presentation hierarchy
    LINE_ITEMS = "LineItems"
    
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
    ADMIN_SECTION = "AdminSection"  # Added for SEC filing sections
    FINANCIAL_STATEMENT = "FinancialStatement"  # Added for financial statement types
    
    # Content nodes for SEC filings
    EXTRACTED_SECTION = "ExtractedSectionContent"  # Section content from SEC filings
    EXHIBIT = "ExhibitContent"  # Exhibit content from SEC filings
    FINANCIAL_DATA = "FinancialStatementContent"  # Financial statement data points
    FILING_TEXT = "FilingTextContent"  # Full filing text content

    # Transcript nodes
    TRANSCRIPT = "Transcript"  # Earnings call transcript
    PREPARED_REMARK = "PreparedRemark"  # Prepared remarks section of transcript
    QUESTION_ANSWER = "QuestionAnswer"  # Q&A section of transcript
    QA_EXCHANGE = "QAExchange"  # Individual Q&A exchange
    FULL_TRANSCRIPT_TEXT = "FullTranscriptText"  # Full text of transcript
    
    # Dividend node
    DIVIDEND = "Dividend"  # Dividend declaration information
    SPLIT = "Split"  # Split information





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
    CONTAINS = "CONTAINS"          # For XBRL->Fact relationships
    REPORTS = "REPORTS"            # For Fact->XBRL relationships
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
    HAS_SUB_SECTION = "HAS_SUB_SECTION"  # For section categories to individual sections
    HAS_SUB_STATEMENT = "HAS_SUB_STATEMENT"  # For financial statement categories to statement types
    REPORTED_ON = "REPORTED_ON"     # Between date and report (deprecated)
    PRESENTATION_EDGE = "PRESENTATION_EDGE" # From Fact to Fact
    CALCULATION_EDGE = "CALCULATION_EDGE" # From Fact to Fact
    FILED_BY = "FILED_BY"           # From Report to Company
    HAS_CATEGORY = "HAS_CATEGORY"   # Report -> AdminReport
    FOR_COMPANY = "FOR_COMPANY"     # Context -> Company
    PROVIDES_GUIDANCE = "PROVIDES_GUIDANCE"  # From Guidance concept to related concept
    INFLUENCES = "INFLUENCES"
    PRIMARY_FILER = "PRIMARY_FILER"   # Report -> Company (primary filer)
    REFERENCED_IN = "REFERENCED_IN"   # Report -> Company (mentioned in the report)
    RELATED_TO = "RELATED_TO"       # Company -> Company relationship
    HAS_XBRL = "HAS_XBRL"          # ReportNode -> XBRLNode relationship (single direction)
    HAS_SECTION = "HAS_SECTION"     # Report -> ExtractedSectionContent relationship
    HAS_EXHIBIT = "HAS_EXHIBIT"     # Report -> ExhibitContent relationship
    HAS_FINANCIAL_STATEMENT = "HAS_FINANCIAL_STATEMENT"  # Report -> FinancialStatementContent relationship
    HAS_FILING_TEXT = "HAS_FILING_TEXT"  # Report -> FilingTextContent relationship

        # Transcript relationships
    HAS_TRANSCRIPT = "HAS_TRANSCRIPT"  # Company -> Transcript relationship
    HAS_PREPARED_REMARKS = "HAS_PREPARED_REMARKS"  # Transcript -> PreparedRemark relationship
    HAS_QA_SECTION = "HAS_QA_SECTION"  # Transcript -> QuestionAnswer relationship
    HAS_FULL_TEXT = "HAS_FULL_TEXT"  # Transcript -> FullTranscriptText relationship
    HAS_QA_EXCHANGE = "HAS_QA_EXCHANGE"  # Transcript/QuestionAnswer -> QAExchange relationship
    NEXT_EXCHANGE = "NEXT_EXCHANGE"  # QAExchange -> Next QAExchange relationship

    HAS_DIVIDEND = "HAS_DIVIDEND"  # Date -> Dividend relationship
    DECLARED_DIVIDEND = "DECLARED_DIVIDEND"  # Company -> Dividend relationship

    HAS_SPLIT = "HAS_SPLIT"  # Date -> Split relationship
    DECLARED_SPLIT = "DECLARED_SPLIT"  # Company -> Split relationship



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
            logger.debug("DEBUG - Received None concept")
            return None
            
        logger.debug(f"DEBUG - wrap_concept called for: {getattr(concept, 'qname', 'No qname')}")
        logger.debug(f"DEBUG - Original type: {type(concept)}")
        
        # Store the qname before any transformations
        original_qname = getattr(concept, 'qname', None)
        
        # Get the ModelConcept depending on what type we received
        if isinstance(concept, (AbstractConcept, Concept)):
            model_concept = getattr(concept, 'model_concept', None)
            if model_concept is None:
                logger.debug(f"DEBUG - No model_concept found in {type(concept).__name__}")
                return None
                
            # Only try to set qname if model_concept exists
            if not hasattr(model_concept, 'qname') and original_qname:
                try:
                    setattr(model_concept, 'qname', original_qname)
                except AttributeError:
                    logger.debug(f"DEBUG - Could not set qname on model_concept")
                    return None
                    
            logger.debug(f"DEBUG - Getting model_concept from {type(concept).__name__}")
        else:
            model_concept = concept
            logger.debug(f"DEBUG - Using original concept")

        # Verify we have a valid concept with qname
        if not hasattr(model_concept, 'qname'):
            logger.debug(f"DEBUG - Missing qname, attempting to restore from original")
            if original_qname:
                try:
                    setattr(model_concept, 'qname', original_qname)
                except AttributeError:
                    logger.debug(f"DEBUG - Cannot restore qname")
                    return None
            else:
                logger.debug(f"DEBUG - No qname available")
                return None

        if isinstance(model_concept, ModelConcept):
            category = cls.classify(model_concept)
            logger.debug(f"DEBUG - Classified as: {category}")
            
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
                
            logger.debug(f"DEBUG - No wrapper created for category: {category}")
        else:
            logger.debug(f"DEBUG - Invalid concept: missing qname")
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

@dataclass
class XBRLNode(Neo4jNode):
    """
    An intermediary node that handles all XBRL processing.
    This node sits between ReportNode and all other XBRL components.
    """
    primaryDocumentUrl: str  # Primary identifier matching ReportNode
    cik: str                # Company identifier 
    report_id: str          # Reference to original ReportNode id
    accessionNo: Optional[str] = None  # Match ReportNode accessionNo for relationship creation
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.XBRLNODE
        
    @property
    def id(self) -> str:
        """Use primaryDocumentUrl as unique identifier"""
        return self.primaryDocumentUrl
        
    @property
    def display(self) -> str:
        """Returns display name for the XBRL node"""
        # Extract accession number from primaryDocumentUrl
        # Example URL: https://www.sec.gov/Archives/edgar/data/1856028/000162828024010049/sdig-20231231_htm.xml
        try:
            accession_no = self.accessionNo or self.primaryDocumentUrl.split('/')[7]  # Get the accession number part
            return f"XBRL_{accession_no}"
        except (IndexError, AttributeError):
            return f"XBRL_{self.report_id}"  # Fallback to report_id if URL parsing fails
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Properties for Neo4j node"""
        props = {
            'id': self.id,
            'primaryDocumentUrl': self.primaryDocumentUrl,
            'cik': self.cik,
            'report_id': self.report_id,
            'displayLabel': self.display
        }
        
        # Add accessionNo if available (for newer nodes)
        if self.accessionNo:
            props['accessionNo'] = self.accessionNo
            
        return props