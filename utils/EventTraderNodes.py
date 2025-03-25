from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
import json
from enum import Enum
from utils.date_utils import parse_date  # Import our date parsing utility

# Import node types from XBRLClasses but avoid circular imports
from XBRL.xbrl_core import NodeType, RelationType

# Base Neo4jNode class definition
@dataclass
class Neo4jNode:
    """Base class for Neo4j nodes"""
    
    @property
    def node_type(self) -> NodeType:
        """Return node type"""
        raise NotImplementedError("Subclasses must implement node_type")
    
    @property
    def id(self) -> str:
        """Return node ID"""
        raise NotImplementedError("Subclasses must implement id")
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Return node properties"""
        raise NotImplementedError("Subclasses must implement properties")
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> Neo4jNode:
        """Create instance from Neo4j properties"""
        raise NotImplementedError("Subclasses must implement from_neo4j")


@dataclass
class ReportNode(Neo4jNode):
    """
    ReportNode class representing SEC filings with extended metadata.
    
    This class is used for storing, processing, and retrieving SEC filing information.
    It maintains compatibility with the XBRL processor while adding additional fields
    from SEC API and other sources.
    """
    # Required fields - these must always be present
    accessionNo: str                      # UniqueIdentifier/id – prevents duplicate reports
    primaryDocumentUrl: str               # URL to the primary document (either xml or txt)
    cik: str                              # Company CIK
    
    # Important fields that may be empty but should be included
    formType: str = ""                    # e.g., "10-K", "10-Q", "8-K"
    created: str = ""                     # Same as filedAt but in New York Time
    is_xml: bool = False                  # Indicates if primary doc is XML
    
    # Fields that might be missing in some records
    market_session: Optional[str] = None  # Taken from metadata.event.market_session
    returns_schedule: Dict[str, str] = field(default_factory=dict)  # Schedule for returns calculation
    
    # Optional fields
    xbrl_status: Optional[str] = None   # Processing status flag for XBRL data (QUEUED, PROCESSING, COMPLETED, FAILED)
    isAmendment: Optional[bool] = None    # Whether the report is an amendment
    description: Optional[str] = None     # Brief description of the report
    periodOfReport: Optional[str] = None  # Period the report covers
    linkToTxt: Optional[str] = None       # Link to text version
    linkToHtml: Optional[str] = None      # Link to HTML version
    linkToFilingDetails: Optional[str] = None  # Link to filing details
    effectivenessDate: Optional[str] = None    # Effectiveness date if applicable
    exhibits: Optional[Dict[str, Any]] = None  # Exhibits included in the filing
    items: Optional[List[str]] = None     # Items covered in the filing
    symbols: Optional[List[str]] = None   # Stock symbols mentioned
    entities: Optional[List[Dict[str, Any]]] = None  # Related entities
    extracted_sections: Optional[Dict[str, str]] = None  # Extracted sections from filing
    financial_statements: Optional[Any] = None  # Extracted financial statements
    exhibit_contents: Optional[Any] = None      # Contents of exhibits
    filing_text_content: Optional[str] = None   # Full text content of filing
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.REPORT
    
    @property
    def id(self) -> str:
        """Use accessionNo as the unique identifier"""
        return self.accessionNo
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Return node properties for Neo4j"""
        # Start with required properties
        props = {
            "id": self.id,
            "accessionNo": self.accessionNo,
            "primaryDocumentUrl": self.primaryDocumentUrl,
            "cik": self.cik,
            "formType": self.formType,
            "created": self.created,
            "is_xml": self.is_xml,
            "xbrl_status": self.xbrl_status
        }
        
        # Add market_session if present
        if self.market_session is not None:
            props["market_session"] = self.market_session
        
        # Add returns_schedule as JSON string if it has items
        if self.returns_schedule:
            props["returns_schedule"] = json.dumps(self.returns_schedule)
        
        # Add optional properties if they exist
        optional_props = {
            "isAmendment": self.isAmendment,
            "description": self.description,
            "periodOfReport": self.periodOfReport,
            "linkToTxt": self.linkToTxt,
            "linkToHtml": self.linkToHtml,
            "linkToFilingDetails": self.linkToFilingDetails,
            "effectivenessDate": self.effectivenessDate
        }
        
        # Only include non-None optional properties
        props.update({k: v for k, v in optional_props.items() if v is not None})
        
        # Handle complex types - serialize to JSON strings
        if self.exhibits is not None:
            props["exhibits"] = json.dumps(self.exhibits)
        if self.items is not None:
            props["items"] = json.dumps(self.items)
        if self.symbols is not None:
            props["symbols"] = json.dumps(self.symbols)
        if self.entities is not None:
            props["entities"] = json.dumps(self.entities)
        if self.extracted_sections is not None:
            props["extracted_sections"] = json.dumps(self.extracted_sections)
        if self.exhibit_contents is not None:
            props["exhibit_contents"] = json.dumps(self.exhibit_contents)
        if self.financial_statements is not None:
            props["financial_statements"] = json.dumps(self.financial_statements)
            
        # Skip storing large binary/text content directly in Neo4j
        # These fields should be separately stored or referenced
        # filing_text_content
        
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'ReportNode':
        """Create a ReportNode instance from Neo4j properties"""
        # Check required fields for backward compatibility
        if 'accessionNo' not in props:
            raise ValueError("Missing required accessionNo for ReportNode")
            
        if 'primaryDocumentUrl' not in props:
            raise ValueError("Missing required primaryDocumentUrl for ReportNode")
            
        # Create instance with required fields
        instance = cls(
            accessionNo=props['accessionNo'],
            primaryDocumentUrl=props['primaryDocumentUrl'],
            cik=props.get('cik', ''),
            formType=props.get('formType', ''),
            created=props.get('created', ''),
            is_xml=props.get('is_xml', False)
        )
        
        # Handle boolean conversion for is_xml
        if isinstance(instance.is_xml, str):
            instance.is_xml = instance.is_xml.lower() == 'true'
        
        # Set market_session if available
        if 'market_session' in props and props['market_session']:
            instance.market_session = props['market_session']
            
        # Parse returns_schedule
        if 'returns_schedule' in props and props['returns_schedule']:
            try:
                returns_schedule = json.loads(props['returns_schedule'])
                instance.returns_schedule = returns_schedule
            except:
                pass
        
        # Set optional fields
        if 'xbrl_status' in props:
            instance.xbrl_status = props['xbrl_status']
        
        # Set string fields
        string_fields = ['description', 'periodOfReport', 'linkToTxt', 'linkToHtml', 
                         'linkToFilingDetails', 'effectivenessDate']
        for field in string_fields:
            if field in props and props[field]:
                setattr(instance, field, props[field])
                
        # Set boolean fields
        if 'isAmendment' in props:
            isAmendment = props['isAmendment']
            if isinstance(isAmendment, str):
                isAmendment = isAmendment.lower() == 'true'
            instance.isAmendment = isAmendment
        
        # Parse JSON fields
        json_fields = [
            ('exhibits', {}), 
            ('items', []), 
            ('symbols', []), 
            ('entities', []),
            ('extracted_sections', {})
        ]
        
        for field_name, default_value in json_fields:
            if field_name in props and props[field_name]:
                try:
                    setattr(instance, field_name, json.loads(props[field_name]))
                except:
                    setattr(instance, field_name, default_value)
        
        return instance



# Direct implementation of CompanyNode without inheritance
@dataclass
class CompanyNode(Neo4jNode):
    cik: str
    name: Optional[str] = None  # Check if it matters to make it Optional
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    fiscal_year_end: Optional[str] = None

    # Add fields that may not be in the class definition but are accessed in properties method
    cusip: Optional[str] = None
    figi: Optional[str] = None
    class_figi: Optional[str] = None
    sic: Optional[str] = None
    sic_name: Optional[str] = None
    sector_etf: Optional[str] = None
    industry_etf: Optional[str] = None
    mkt_cap: Optional[float] = None
    employees: Optional[int] = None
    shares_out: Optional[float] = None
    ipo_date: Optional[str] = None
    
    def __post_init__(self):
        # Ensure CIK is properly formatted (10 digits with leading zeros)
        self.cik = self.cik.zfill(10)
        
    def display(self):
        """Returns display name for the entity"""
        if self.ticker:
            return f"{self.name} ({self.ticker})"
        return self.name

    @property
    def node_type(self) -> NodeType:
        return NodeType.COMPANY

    @property
    def id(self) -> str:
        """Use CIK as unique identifier"""
        return self.cik

    @property
    def properties(self) -> Dict[str, Any]:
        """
        Returns properties for Neo4j node
        Filters out None values to keep the node clean
        """
        props = {
            'id': self.id,
            'cik': self.cik,
            'name': self.name,
            'displayLabel': self.display()
        }
        
        # Add optional properties if they exist
        optional_props = {
            'ticker': self.ticker,
            'exchange': self.exchange,
            'sector': self.sector,
            'industry': self.industry,
            'cusip': self.cusip,
            'figi': self.figi,
            'class_figi': self.class_figi,
            'sic': self.sic,
            'sic_name': self.sic_name,
            'sector_etf': self.sector_etf,
            'industry_etf': self.industry_etf,
            'mkt_cap': self.mkt_cap,
            'employees': self.employees,
            'shares_out': self.shares_out,
            'ipo_date': self.ipo_date,
            'fiscal_year_end': self.fiscal_year_end
        }
        
        # Only include non-None optional properties
        props.update({k: v for k, v in optional_props.items() if v is not None})
        
        return props
        
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'CompanyNode':
        """Create CompanyNode from Neo4j properties"""
        # Required field
        if 'cik' not in props:
            raise ValueError("Missing required field 'cik' for CompanyNode")
        
        # Initialize with required fields
        company = cls(cik=props['cik'])
        
        # Map neo4j properties to attributes
        field_mappings = {
            'name': 'name',
            'ticker': 'ticker',
            'exchange': 'exchange',
            'sector': 'sector',
            'industry': 'industry',
            'fiscal_year_end': 'fiscal_year_end',
            'cusip': 'cusip',
            'figi': 'figi',
            'class_figi': 'class_figi',
            'sic': 'sic',
            'sic_name': 'sic_name',
            'sector_etf': 'sector_etf',
            'industry_etf': 'industry_etf',
            'ipo_date': 'ipo_date'
        }
        
        # Set string and simple fields
        for neo4j_field, attr_name in field_mappings.items():
            if neo4j_field in props and props[neo4j_field] not in (None, "", "null"):
                setattr(company, attr_name, props[neo4j_field])
        
        # Handle numeric fields with special parsing
        if 'mkt_cap' in props and props['mkt_cap'] not in (None, "", "null"):
            try:
                mkt_cap_value = props['mkt_cap']
                if isinstance(mkt_cap_value, (int, float)):
                    company.mkt_cap = float(mkt_cap_value)
                else:
                    # Try to clean the string if it contains commas, etc.
                    clean_val = str(mkt_cap_value).replace(',', '').replace('$', '').strip()
                    company.mkt_cap = float(clean_val)
            except (ValueError, TypeError):
                pass
        
        if 'employees' in props and props['employees'] not in (None, "", "null"):
            try:
                employees_value = props['employees']
                if isinstance(employees_value, (int, float)):
                    company.employees = int(employees_value)
                else:
                    # Try to clean the string if it contains commas, etc.
                    clean_val = str(employees_value).replace(',', '').strip()
                    company.employees = int(float(clean_val))
            except (ValueError, TypeError):
                pass
        
        if 'shares_out' in props and props['shares_out'] not in (None, "", "null"):
            try:
                shares_value = props['shares_out']
                if isinstance(shares_value, (int, float)):
                    company.shares_out = float(shares_value)
                else:
                    # Try to clean the string if it contains commas, etc.
                    clean_val = str(shares_value).replace(',', '').strip()
                    company.shares_out = float(clean_val)
            except (ValueError, TypeError):
                pass
        
        return company

@dataclass
class AdminReportNode(Neo4jNode):
    """
    Admin report node for categorizing SEC filings.
    Used in the report hierarchy. 
    
    Args:
        code: Unique code (e.g., '10-K', '10-K_FYE-0331')
        label: Display label (e.g., '10-K Reports', 'FYE 03/31')
        category: Category for grouping (e.g., '10-K')
    """
    code: str      # Unique identifier
    label: str     # Display label
    category: str  # Category for grouping
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.ADMIN_REPORT
    
    @property
    def id(self) -> str:
        """Use code as unique identifier"""
        return self.code
    
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'label': self.label,
            'category': self.category,
            'displayLabel': self.label
        }
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'AdminReportNode':
        """Create AdminReportNode from Neo4j properties"""
        # Required fields
        if 'code' not in props:
            raise ValueError("Missing required field 'code' for AdminReportNode")
        
        return cls(
            code=props['code'],
            label=props.get('label', ''),
            category=props.get('category', '')
        )
    
    def get_date(self) -> Optional[datetime]:
        """Extract date from code for comparison"""
        try:
            if "_FYE-" in self.code:
                month_day = self.code.split("_FYE-")[1]
                month = int(month_day[:2])
                day = int(month_day[2:])
                return datetime(2000, month, day)  # Year doesn't matter for comparison
            elif "_Q" in self.code:
                quarter = int(self.code.split("_Q")[1])
                month = (quarter * 3) - 2  # Q1 -> 1, Q2 -> 4, Q3 -> 7, Q4 -> 10
                return datetime(2000, month, 1)  # Year doesn't matter for comparison
        except Exception:
            pass
        return None

@dataclass
class AdminSectionNode(Neo4jNode):
    """
    Admin section node for SEC filing sections.
    Used to categorize document sections for analysis.
    
    Args:
        code: Unique code (e.g., '1', '1A', '1-1')
        label: Display label (e.g., 'Business', 'EntryintoaMaterialDefinitiveAgreement')
        category: Category for grouping (e.g., '10-K', '10-Q', '8-K')
    """
    code: str      # Unique identifier (section number/code)
    label: str     # Display label (section name)
    category: str  # Category for grouping (report type)
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.ADMIN_SECTION
    
    @property
    def id(self) -> str:
        """Use code and category as unique identifier"""
        return f"{self.category}_{self.code}"
    
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'label': self.label,
            'category': self.category,
            'displayLabel': self.label
        }
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'AdminSectionNode':
        """Create AdminSectionNode from Neo4j properties"""
        # Required fields
        if 'code' not in props:
            raise ValueError("Missing required field 'code' for AdminSectionNode")
        
        return cls(
            code=props['code'],
            label=props.get('label', ''),
            category=props.get('category', '')
        )

@dataclass
class FinancialStatementNode(Neo4jNode):
    """
    Financial statement node for SEC filing financial statements.
    Used to categorize financial statement types for analysis.
    
    Args:
        code: Unique code (e.g., 'BalanceSheets', 'StatementsOfIncome')
        label: Display label (e.g., 'Balance Sheets', 'Statements of Income')
        category: Category for grouping (e.g., 'Financial Statements')
        description: Optional description of the statement type
    """
    code: str                    # Unique identifier (statement type code)
    label: str                   # Display label (statement type name)
    category: str                # Category for grouping
    description: Optional[str] = None  # Optional description
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.FINANCIAL_STATEMENT
    
    @property
    def id(self) -> str:
        """Use code as unique identifier"""
        return self.code
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.id,
            'code': self.code,
            'label': self.label,
            'category': self.category,
            'displayLabel': self.label
        }
        if self.description:
            props['description'] = self.description
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'FinancialStatementNode':
        """Create FinancialStatementNode from Neo4j properties"""
        # Required fields
        if 'code' not in props:
            raise ValueError("Missing required field 'code' for FinancialStatementNode")
        
        return cls(
            code=props['code'],
            label=props.get('label', ''),
            category=props.get('category', ''),
            description=props.get('description', None)
        )

@dataclass
class MarketIndexNode(Neo4jNode):
    """Market Index node in Neo4j (e.g., S&P 500 'SPY')"""
    ticker: str  # ETF ticker (unique identifier)
    name: Optional[str] = None  # Full name 
    description: Optional[str] = None
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.MARKET_INDEX
    
    @property
    def id(self) -> str:
        return self.ticker
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.ticker
        }
        if self.name is not None:
            props['name'] = self.name
        if self.description is not None:
            props['description'] = self.description
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'MarketIndexNode':
        ticker = props.get('id', '')
        return cls(
            ticker=ticker,
            name=props.get('name', None),
            description=props.get('description', None)
        )

@dataclass
class SectorNode(Neo4jNode):
    """
    Sector node in Neo4j
    Example: XLF = "Financials"
    """
    node_id: str  # ETF ticker (e.g. 'XLF')
    name: Optional[str] = None  # Sector name (e.g. 'Financials')
    etf: Optional[str] = None  # ETF ticker associated with this sector
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.SECTOR
    
    @property
    def id(self) -> str:
        return self.node_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {'id': self.id}
        if self.name is not None:
            props['name'] = self.name
        if self.etf is not None:
            props['etf'] = self.etf
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'SectorNode':
        sector_id = props.get('id', '')
        if not sector_id:
            raise ValueError("Missing required id field for SectorNode")
            
        return cls(
            node_id=sector_id,
            name=props.get('name', None),
            etf=props.get('etf', None)
        )

@dataclass
class IndustryNode(Neo4jNode):
    """
    Industry node in Neo4j
    Example: KIE = "Insurance", sector_id = "XLF"
    """
    node_id: str  # Industry ETF ticker (e.g. 'KIE')
    name: Optional[str] = None  # Industry name (e.g. 'Insurance')
    sector_id: Optional[str] = None  # Parent sector ETF (e.g. 'XLF')
    etf: Optional[str] = None  # ETF ticker associated with this industry
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.INDUSTRY
    
    @property
    def id(self) -> str:
        return self.node_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {'id': self.id}
        if self.name is not None:
            props['name'] = self.name
        if self.sector_id is not None:
            props['sector_id'] = self.sector_id
        if self.etf is not None:
            props['etf'] = self.etf
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'IndustryNode':
        industry_id = props.get('id', '')
        if not industry_id:
            raise ValueError("Missing required id field for IndustryNode")
            
        return cls(
            node_id=industry_id,
            name=props.get('name', None),
            sector_id=props.get('sector_id', None),
            etf=props.get('etf', None)
        )

@dataclass
class NewsNode(Neo4jNode):
    """News node in Neo4j"""
    news_id: str  # Unique identifier
    title: Optional[str] = None
    body: Optional[str] = None  # Primary content field
    teaser: Optional[str] = None
    created: Optional[datetime] = None  # Creation timestamp
    updated: Optional[datetime] = None  # Update timestamp
    url: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    market_session: Optional[str] = None  # e.g., "market_open", "market_closed"
    returns_schedule: Dict[str, str] = field(default_factory=dict)  # Schedule for returns calculation
    
    @property
    def node_type(self) -> NodeType:
        """Return node type"""
        return NodeType.NEWS
    
    @property
    def id(self) -> str:
        """Return unique ID"""
        return self.news_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Return node properties for Neo4j with standardized field names"""
        # Always include all fields, even if empty
        props = {
            'id': self.news_id,
            'title': self.title or "",
            'body': self.body or "",
            'teaser': self.teaser or "",
            'url': self.url or "",
            'market_session': self.market_session or ""
        }
        
        # Convert datetime to string for Neo4j
        if self.created:
            props['created'] = self.created.isoformat()
        else:
            props['created'] = ""
            
        if self.updated:
            props['updated'] = self.updated.isoformat()
        else:
            props['updated'] = ""
        
        # Convert lists to JSON strings - always include even if empty
        props['authors'] = json.dumps(self.authors or [])
        props['channels'] = json.dumps(self.channels or [])
        props['tags'] = json.dumps(self.tags or [])
        
        # Add returns_schedule as JSON string
        props['returns_schedule'] = json.dumps(self.returns_schedule or {})
        
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'NewsNode':
        """Create NewsNode from Neo4j properties with standardized field handling"""
        # Parse datetime fields using our utility
        created = parse_date(props.get('created', ''))
        updated = parse_date(props.get('updated', ''))
        
        # Parse JSON list fields
        authors = []
        if 'authors' in props and props['authors']:
            try:
                authors = json.loads(props['authors'])
            except:
                pass
                
        channels = []
        if 'channels' in props and props['channels']:
            try:
                channels = json.loads(props['channels'])
            except:
                pass
                
        tags = []
        if 'tags' in props and props['tags']:
            try:
                tags = json.loads(props['tags'])
            except:
                pass
        
        # Parse returns_schedule
        returns_schedule = {}
        if 'returns_schedule' in props and props['returns_schedule']:
            try:
                returns_schedule = json.loads(props['returns_schedule'])
            except:
                pass
        
        return cls(
            news_id=props.get('id', ''),
            title=props.get('title', None),
            body=props.get('body', None),
            teaser=props.get('teaser', None),
            created=created,
            updated=updated,
            url=props.get('url', None),
            authors=authors,
            channels=channels,
            tags=tags,
            market_session=props.get('market_session', None),
            returns_schedule=returns_schedule
        )

@dataclass
class FilingTextContent(Neo4jNode):
    """Node for full filing text content."""
    content_id: str            # Unique identifier
    filing_id: str             # Related filing accession number
    form_type: str             # 10-K, 10-Q, 8-K, SCHEDULE 13D, etc.
    content: str               # Full text content
    filer_cik: Optional[str] = None  # Company CIK
    filed_at: Optional[str] = None   # Filing date
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.FILING_TEXT
    
    @property
    def id(self) -> str:
        return self.content_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.id,
            'filing_id': self.filing_id,
            'form_type': self.form_type,
            'content': self.content
        }
        if self.filer_cik:
            props['filer_cik'] = self.filer_cik
        if self.filed_at:
            props['filed_at'] = self.filed_at
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'FilingTextContent':
        if 'id' not in props:
            raise ValueError("Missing required field 'id' for FilingTextContent")
        return cls(
            content_id=props['id'],
            filing_id=props.get('filing_id', ''),
            form_type=props.get('form_type', ''),
            content=props.get('content', ''),
            filer_cik=props.get('filer_cik'),
            filed_at=props.get('filed_at')
        )

@dataclass
class ExtractedSectionContent(Neo4jNode):
    """Node for SEC filing extracted section content."""
    content_id: str            # Unique identifier
    filing_id: str             # Related filing accession number
    form_type: str             # 10-K, 10-Q, 8-K
    section_name: str          # Section name (e.g., "RiskFactors")
    content: str               # Actual text content
    content_length: int = 0    # Length of content in characters
    filer_cik: Optional[str] = None  # Company CIK
    filed_at: Optional[str] = None   # Filing date
    
    def __post_init__(self):
        """Ensure content_length is set if not provided"""
        if self.content and self.content_length == 0:
            self.content_length = len(self.content)
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.EXTRACTED_SECTION
    
    @property
    def id(self) -> str:
        return self.content_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.id,
            'filing_id': self.filing_id,
            'form_type': self.form_type,
            'section_name': self.section_name,
            'content': self.content,
            'content_length': self.content_length
        }
        if self.filer_cik:
            props['filer_cik'] = self.filer_cik
        if self.filed_at:
            props['filed_at'] = self.filed_at
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'ExtractedSectionContent':
        """Create instance from Neo4j properties"""
        if 'id' not in props:
            raise ValueError("Missing required field 'id' for ExtractedSectionContent")
        
        # Parse content_length as int
        content_length = 0
        if 'content_length' in props:
            try:
                content_length = int(props['content_length'])
            except (ValueError, TypeError):
                pass
                
        return cls(
            content_id=props['id'],
            filing_id=props.get('filing_id', ''),
            form_type=props.get('form_type', ''),
            section_name=props.get('section_name', ''),
            content=props.get('content', ''),
            content_length=content_length,
            filer_cik=props.get('filer_cik'),
            filed_at=props.get('filed_at')
        )

@dataclass
class ExhibitContent(Neo4jNode):
    """Node for SEC filing exhibit content."""
    content_id: str            # Unique identifier
    filing_id: str             # Related filing accession number
    form_type: str             # 10-K, 10-Q, 8-K
    exhibit_number: str        # EX-10.1, EX-99.1, etc.
    content: str               # Actual text content or URL
    filer_cik: Optional[str] = None  # Company CIK
    filed_at: Optional[str] = None   # Filing date
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.EXHIBIT
    
    @property
    def id(self) -> str:
        return self.content_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.id,
            'filing_id': self.filing_id,
            'form_type': self.form_type,
            'exhibit_number': self.exhibit_number,
            'content': self.content
        }
        if self.filer_cik:
            props['filer_cik'] = self.filer_cik
        if self.filed_at:
            props['filed_at'] = self.filed_at
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'ExhibitContent':
        if 'id' not in props:
            raise ValueError("Missing required field 'id' for ExhibitContent")
        return cls(
            content_id=props['id'],
            filing_id=props.get('filing_id', ''),
            form_type=props.get('form_type', ''),
            exhibit_number=props.get('exhibit_number', ''),
            content=props.get('content', ''),
            filer_cik=props.get('filer_cik'),
            filed_at=props.get('filed_at')
        )

@dataclass
class FinancialStatementContent(Neo4jNode):
    """Node for financial statement data point."""
    content_id: str            # Unique identifier
    filing_id: str             # Related filing accession number
    form_type: str             # 10-K, 10-Q
    statement_type: str        # BalanceSheets, StatementsOfIncome, etc.
    value: str                 # Actual value (contains entire statement data as JSON)
    filer_cik: Optional[str] = None  # Company CIK
    filed_at: Optional[str] = None   # Filing date
    period_end: Optional[str] = None # Period end date
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.FINANCIAL_DATA
    
    @property
    def id(self) -> str:
        return self.content_id
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.id,
            'filing_id': self.filing_id,
            'form_type': self.form_type,
            'statement_type': self.statement_type,
            'value': self.value
        }
        if self.filer_cik:
            props['filer_cik'] = self.filer_cik
        if self.filed_at:
            props['filed_at'] = self.filed_at
        if self.period_end:
            props['period_end'] = self.period_end
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'FinancialStatementContent':
        if 'id' not in props:
            raise ValueError("Missing required field 'id' for FinancialStatementContent")
        return cls(
            content_id=props['id'],
            filing_id=props.get('filing_id', ''),
            form_type=props.get('form_type', ''),
            statement_type=props.get('statement_type', ''),
            value=props.get('value', ''),
            filer_cik=props.get('filer_cik'),
            filed_at=props.get('filed_at'),
            period_end=props.get('period_end')
        )