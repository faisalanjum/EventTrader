from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Type, Union
from datetime import datetime
import json
from enum import Enum
from utils.date_utils import parse_date  # Import our date parsing utility
import pandas as pd

# Import node types from XBRLClasses but avoid circular imports
from XBRL.xbrl_core import NodeType, RelationType
from abc import ABC, abstractmethod


# Base Neo4jNode class definition
class Neo4jNode(ABC):
    """Base class for Neo4j nodes"""
    
    @property
    @abstractmethod
    def node_type(self) -> NodeType:
        """Return node type"""
        raise NotImplementedError("Subclasses must implement node_type")
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Return node ID"""
        raise NotImplementedError("Subclasses must implement id")
    
    @property
    @abstractmethod
    def properties(self) -> Dict[str, Any]:
        """Return node properties"""
        raise NotImplementedError("Subclasses must implement properties")
    
    @classmethod
    @abstractmethod
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
    
    # New fiscal year end fields
    fiscal_year_end_month: Optional[int] = None
    fiscal_year_end_day: Optional[int] = None
    
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
            'fiscal_year_end_month': self.fiscal_year_end_month,
            'fiscal_year_end_day': self.fiscal_year_end_day
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
            'cusip': 'cusip',
            'figi': 'figi',
            'class_figi': 'class_figi',
            'sic': 'sic',
            'sic_name': 'sic_name',
            'sector_etf': 'sector_etf',
            'industry_etf': 'industry_etf',
            'ipo_date': 'ipo_date',
            'fiscal_year_end_month': 'fiscal_year_end_month',
            'fiscal_year_end_day': 'fiscal_year_end_day'
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

@dataclass
class DateNode(Neo4jNode):
    """
    Date node in Neo4j representing a market date with session information.
    Contains market session times for current, previous, and next trading days.
    """
    date_str: str  # Date in string format YYYY-MM-DD
    is_trading_day: bool = True  # Whether the date is a trading day
    
    # Time dictionary values as strings (for storage)
    pre_market_current_day: Optional[str] = None
    market_open_current_day: Optional[str] = None
    market_close_current_day: Optional[str] = None
    post_market_current_day: Optional[str] = None

    pre_market_previous_day: Optional[str] = None
    market_open_previous_day: Optional[str] = None
    market_close_previous_day: Optional[str] = None
    post_market_previous_day: Optional[str] = None
    
    pre_market_next_day: Optional[str] = None
    market_open_next_day: Optional[str] = None
    market_close_next_day: Optional[str] = None
    post_market_next_day: Optional[str] = None
    
    @staticmethod
    def _extract_date_from_timestamp(timestamp: Optional[str]) -> Optional[str]:
        """Extract date part (YYYY-MM-DD) from a timestamp string"""
        if not timestamp:
            return None
            
        # Use pandas for reliable date extraction
        try:
            return pd.Timestamp(timestamp).strftime('%Y-%m-%d')
        except:
            return None
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.DATE
    
    @property
    def id(self) -> str:
        """Use date as the unique identifier"""
        return self.date_str
    
    @property
    def previous_trading_date(self) -> Optional[str]:
        """Extract previous trading date from market_close_previous_day"""
        return self._extract_date_from_timestamp(self.market_close_previous_day)
    
    @property
    def next_trading_date(self) -> Optional[str]:
        """Extract next trading date from market_close_next_day"""
        return self._extract_date_from_timestamp(self.market_close_next_day)
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Return node properties for Neo4j"""
        props = {
            'id': self.id,
            'date': self.date_str,
            'is_trading_day': self.is_trading_day
        }
        
        # Add previous and next trading dates if available
        prev_date = self.previous_trading_date
        if prev_date:
            props['previous_trading_date'] = prev_date
            
        next_date = self.next_trading_date
        if next_date:
            props['next_trading_date'] = next_date
        
        # Add all time properties if they exist
        time_props = {
            'pre_market_current_day': self.pre_market_current_day,
            'market_open_current_day': self.market_open_current_day,
            'market_close_current_day': self.market_close_current_day,
            'post_market_current_day': self.post_market_current_day,
            'pre_market_previous_day': self.pre_market_previous_day,
            'market_open_previous_day': self.market_open_previous_day,
            'market_close_previous_day': self.market_close_previous_day,
            'post_market_previous_day': self.post_market_previous_day,
            'pre_market_next_day': self.pre_market_next_day,
            'market_open_next_day': self.market_open_next_day,
            'market_close_next_day': self.market_close_next_day,
            'post_market_next_day': self.post_market_next_day
        }
        
        # Only include non-None time properties
        props.update({k: v for k, v in time_props.items() if v is not None})
        
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'DateNode':
        """Create DateNode from Neo4j properties"""
        # Required fields
        if 'date' not in props:
            raise ValueError("Missing required field 'date' for DateNode")
            
        # Create instance with required fields
        date_node = cls(
            date_str=props['date'],
            is_trading_day=props.get('is_trading_day', True)
        )
        
        # Set time properties
        time_fields = [
            'pre_market_current_day', 'market_open_current_day', 'market_close_current_day', 'post_market_current_day',
            'pre_market_previous_day', 'market_open_previous_day', 'market_close_previous_day', 'post_market_previous_day',
            'pre_market_next_day', 'market_open_next_day', 'market_close_next_day', 'post_market_next_day'
        ]
        
        for field in time_fields:
            if field in props and props[field] not in (None, "", "null"):
                setattr(date_node, field, props[field])
                
        return date_node
    


@dataclass
class DividendNode(Neo4jNode):
    """
    Dividend node in Neo4j representing a dividend declaration by a company.
    Contains information about dividend amount, type, dates, and frequency.
    """
    ticker: str                  # Ticker symbol of the company
    declaration_date: str        # Date the dividend was declared
    cash_amount: float           # Dividend amount per share
    

    # Optional fields
    ex_dividend_date: Optional[str] = None # Ex-dividend date - Now Optional
    dividend_type: Optional[str] = None    # Type of dividend (Regular, Special, LongTermGain, ShortTermGain)    
    currency: Optional[str] = None
    frequency: Optional[str] = None
    pay_date: Optional[str] = None
    record_date: Optional[str] = None
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.DIVIDEND
    
    @property
    def id(self) -> str:
        """
        Use composite of ticker, declaration date, and type as unique identifier.
        Uses 'UNKNOWN' for type if it's missing or None.
        """
        # Use a consistent placeholder if dividend_type is None or empty string
        type_part = self.dividend_type if self.dividend_type else "UNKNOWN"
        return f"{self.ticker}_{self.declaration_date}_{type_part}"
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Return node properties for Neo4j"""
        props = {
            'id': self.id,
            'ticker': self.ticker,
            'declaration_date': self.declaration_date,
            'cash_amount': self.cash_amount,
            # No longer include ex_dividend_date/dividend_type here by default
            # They will be added below if they have a value and compatible type
        }
        
        # Add ALL optional properties if they exist AND have a Neo4j-compatible type
        optional_props_values = {
            'ex_dividend_date': self.ex_dividend_date, # Added here
            'dividend_type': self.dividend_type,       # Added here
            'currency': self.currency,
            'frequency': self.frequency,
            'pay_date': self.pay_date,
            'record_date': self.record_date
        }
        
        for key, value in optional_props_values.items():
            # Check if value exists and is a type Neo4j can store directly
            # Allowed: str, int, float, bool. Excludes dict, list, etc.
            if value is not None and isinstance(value, (str, int, float, bool)):
                props[key] = value
            # Optionally log if a value is skipped due to type
            elif value is not None:
                 # Using print as logger might not be configured here
                 print(f"WARNING: Skipping property '{key}' for DividendNode {self.id} due to incompatible type: {type(value)}")

        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'DividendNode':
        """Create DividendNode from Neo4j properties"""
        # Required fields
        required_fields = ['ticker', 'declaration_date', 'cash_amount']
        for field in required_fields:
            if field not in props:
                raise ValueError(f"Missing required field '{field}' for DividendNode")
        
        # Create instance with required fields
        dividend_node = cls(
            ticker=props['ticker'],
            declaration_date=props['declaration_date'],
            cash_amount=float(props['cash_amount']),
            ex_dividend_date=props.get('ex_dividend_date'),
            dividend_type=props.get('dividend_type'),
            currency=props.get('currency'),
            frequency=props.get('frequency'),
            pay_date=props.get('pay_date'),
            record_date=props.get('record_date')
        )
        
        # Set optional properties
        optional_fields = ['ex_dividend_date', 'dividend_type', 'currency', 'frequency', 'pay_date', 'record_date']
        
        for field in optional_fields:
            # Ensure the property exists and is not just an empty string or null representation
            if field in props and props[field] not in (None, "", "null"):
                # Assign directly; type checking happens during property generation
                setattr(dividend_node, field, props[field])
                
        return dividend_node
    
    @classmethod
    def from_dividend_data(cls, dividend_data: Dict[str, Any]) -> 'DividendNode':
        """Create DividendNode from the get_dividends function output, ensuring Python types."""
        
        # --- Strict Type Enforcement --- 
        # Ensure required fields are strings
        ticker_val = str(dividend_data['ticker'])
        declaration_date_val = str(dividend_data['declaration_date'])
        
        try:
            # Ensure cash_amount is standard Python float
            cash_amount_val = float(dividend_data['cash_amount'])
        except (ValueError, TypeError, KeyError):
            # Handle cases where cash_amount might be missing or non-numeric unexpectedly
            print(f"ERROR: Invalid or missing cash_amount '{dividend_data.get('cash_amount')}' for {ticker_val}. Setting to 0.0")
            cash_amount_val = 0.0

        # Handle optional fields, ensuring standard Python string types or None
        def ensure_str_or_none(key):
            val = dividend_data.get(key)
            # Explicitly convert to str only if it's not None, otherwise keep None
            return str(val) if val is not None else None

        ex_dividend_date_val = ensure_str_or_none('ex_dividend_date')
        dividend_type_val = ensure_str_or_none('dividend_type')
        currency_val = ensure_str_or_none('currency')
        pay_date_val = ensure_str_or_none('pay_date')
        record_date_val = ensure_str_or_none('record_date')

        # Handle frequency specifically: Check if it's int/float or str
        frequency_raw = dividend_data.get('frequency')
        frequency_val = None
        if isinstance(frequency_raw, (int, float)): # Allow float conversion just in case
            # Store as standard Python int if it came as number
            frequency_val = int(frequency_raw)
            # Optional: Log that we are storing the integer representation
            # print(f"INFO: Storing frequency as integer {frequency_val} for {ticker_val}")
        elif frequency_raw is not None:
            # Store as standard Python string otherwise
            frequency_val = str(frequency_raw)
        # If frequency_raw is None, frequency_val remains None
        # --- End Strict Type Enforcement ---

        # Create the instance using the strictly typed values
        return cls(
            ticker=ticker_val,
            declaration_date=declaration_date_val,
            dividend_type=dividend_type_val,
            cash_amount=cash_amount_val,
            ex_dividend_date=ex_dividend_date_val,
            currency=currency_val,
            frequency=frequency_val, # Now guaranteed to be standard int, str, or None
            pay_date=pay_date_val,
            record_date=record_date_val
        )
    



@dataclass
class SplitNode(Neo4jNode):
    """
    Split node in Neo4j representing a stock split by a company.
    Contains information about split ratio, execution date, and identifier.
    """
    ticker: str                  # Ticker symbol of the company
    execution_date: str          # Date the split was executed
    split_from: float            # Original number of shares
    
    
    # Optional fields
    split_to: Optional[float] = None      # New number of shares after split
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.SPLIT
    
    @property
    def id(self) -> str:
        """
        Use composite of ticker, execution date, and split ratio as unique identifier.
        Uses 'UNKNOWN' for ratio if split_to is missing or None.
        """
        # Use a consistent placeholder if split_to is None or empty string
        ratio_part = f"{self.split_from}_{self.split_to}" if self.split_to else f"{self.split_from}_UNKNOWN"
        return f"{self.ticker}_{self.execution_date}_{ratio_part}"
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Return node properties for Neo4j"""
        props = {
            'id': self.id,
            'ticker': self.ticker,
            'execution_date': self.execution_date,
            'split_from': self.split_from,
            # No longer include split_to here by default
            # It will be added below if it has a value and compatible type
        }
        
        # Add ALL optional properties if they exist AND have a Neo4j-compatible type
        optional_props_values = {
            'split_to': self.split_to,       
        }
        
        for key, value in optional_props_values.items():
            # Check if value exists and is a type Neo4j can store directly
            # Allowed: str, int, float, bool. Excludes dict, list, etc.
            if value is not None and isinstance(value, (str, int, float, bool)):
                props[key] = value
            # Optionally log if a value is skipped due to type
            elif value is not None:
                 # Using print as logger might not be configured here
                 print(f"WARNING: Skipping property '{key}' for SplitNode {self.id} due to incompatible type: {type(value)}")

        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'SplitNode':
        """Create SplitNode from Neo4j properties"""
        # Required fields
        required_fields = ['ticker', 'execution_date', 'split_from']
        for field in required_fields:
            if field not in props:
                raise ValueError(f"Missing required field '{field}' for SplitNode")
        
        # Create instance with required fields
        split_node = cls(
            ticker=props['ticker'],
            execution_date=props['execution_date'],
            split_from=float(props['split_from']),
            split_to=props.get('split_to')
        )
        
        # Set optional properties
        optional_fields = ['split_to']
        
        for field in optional_fields:
            # Ensure the property exists and is not just an empty string or null representation
            if field in props and props[field] not in (None, "", "null"):
                # Assign directly; type checking happens during property generation
                setattr(split_node, field, props[field])
                
        return split_node
    
    @classmethod
    def from_split_data(cls, split_data: Dict[str, Any]) -> 'SplitNode':
        """Create SplitNode from the get_splits function output, ensuring Python types."""
        
        # --- Strict Type Enforcement --- 
        # Ensure required fields are strings
        ticker_val = str(split_data['ticker'])
        execution_date_val = str(split_data['execution_date'])
        
        try:
            # Ensure split_from is standard Python float
            split_from_val = float(split_data['split_from'])
        except (ValueError, TypeError, KeyError):
            # Handle cases where split_from might be missing or non-numeric unexpectedly
            print(f"ERROR: Invalid or missing split_from '{split_data.get('split_from')}' for {ticker_val}. Setting to 1.0")
            split_from_val = 1.0
            
        # Handle split_to specifically with numeric validation
        try:
            split_to_val = float(split_data['split_to']) if split_data.get('split_to') is not None else None
        except (ValueError, TypeError):
            # Handle cases where split_to might be non-numeric unexpectedly
            print(f"ERROR: Invalid split_to '{split_data.get('split_to')}' for {ticker_val}. Setting to None")
            split_to_val = None

        # Handle optional fields, ensuring standard Python string types or None
        def ensure_str_or_none(key):
            val = split_data.get(key)
            # Explicitly convert to str only if it's not None, otherwise keep None
            return str(val) if val is not None else None

        # Create the instance using the strictly typed values
        return cls(
            ticker=ticker_val,
            execution_date=execution_date_val,
            split_from=split_from_val,
            split_to=split_to_val
        )
    
    @property
    def is_future(self) -> bool:
        """Determine if this split's execution date is in the future."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            return self.execution_date > today
        except:
            # Handle potential invalid date format gracefully
            return False # Or raise an error, depending on desired strictness
    

#### Transcripts related classes

@dataclass
class TranscriptNodeData:
    """Data container for transcript node data"""
    
    # Required fields
    id: str                           # Unique transcript ID (e.g., "DAL_2025_1")
    symbol: str                       # Ticker symbol
    company_name: str                 # Full company name
    conference_datetime: str          # ISO format datetime
    fiscal_quarter: int               # Required fiscal quarter
    fiscal_year: int                  # Required fiscal year
    
    # Optional fields
    formType: str = ""                # Type of transcript (e.g., "TRANSCRIPT_Q1") 
    calendar_quarter: Optional[int] = None
    calendar_year: Optional[int] = None
    created: Optional[str] = None     # ISO datetime for creation
    updated: Optional[str] = None     # ISO datetime for update
    speakers: Dict[str, str] = field(default_factory=dict)


class TranscriptNode(Neo4jNode):
    """Transcript node for earnings call transcripts"""
    
    def __init__(self, id, symbol, company_name, conference_datetime, fiscal_quarter, fiscal_year, 
                 formType="", calendar_quarter=None, calendar_year=None, created=None, updated=None, speakers=None):
        # Create data container
        self.data = TranscriptNodeData(
            id=id,
            symbol=symbol,
            company_name=company_name,
            conference_datetime=conference_datetime,
            fiscal_quarter=fiscal_quarter,
            fiscal_year=fiscal_year,
            formType=formType,
            calendar_quarter=calendar_quarter,
            calendar_year=calendar_year,
            created=created,
            updated=updated,
            speakers=speakers or {}
        )
    
    @property
    def id(self) -> str:
        return self.data.id
        
    @property
    def symbol(self) -> str:
        return self.data.symbol
        
    @property
    def company_name(self) -> str:
        return self.data.company_name
        
    @property
    def conference_datetime(self) -> str:
        return self.data.conference_datetime
        
    @property
    def fiscal_quarter(self) -> int:
        return self.data.fiscal_quarter
        
    @property
    def fiscal_year(self) -> int:
        return self.data.fiscal_year
        
    @property
    def formType(self) -> str:
        return self.data.formType
        
    @formType.setter
    def formType(self, value):
        self.data.formType = value
        
    @property
    def calendar_quarter(self) -> Optional[int]:
        return self.data.calendar_quarter
        
    @calendar_quarter.setter
    def calendar_quarter(self, value):
        self.data.calendar_quarter = value
        
    @property
    def calendar_year(self) -> Optional[int]:
        return self.data.calendar_year
        
    @calendar_year.setter
    def calendar_year(self, value):
        self.data.calendar_year = value
        
    @property
    def created(self) -> Optional[str]:
        return self.data.created
        
    @created.setter
    def created(self, value):
        self.data.created = value
        
    @property
    def updated(self) -> Optional[str]:
        return self.data.updated
        
    @updated.setter
    def updated(self, value):
        self.data.updated = value
        
    @property
    def speakers(self) -> Dict[str, str]:
        return self.data.speakers
        
    @speakers.setter
    def speakers(self, value):
        self.data.speakers = value
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.TRANSCRIPT
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            "id": self.id,
            "symbol": self.symbol,
            "company_name": self.company_name,
            "conference_datetime": self.conference_datetime,
            "fiscal_quarter": self.fiscal_quarter,
            "fiscal_year": self.fiscal_year
        }
        
        # Add optional string fields if they exist
        if self.formType:
            props["formType"] = self.formType
            
        # Add optional integer fields if they exist    
        if self.calendar_quarter is not None:
            props["calendar_quarter"] = self.calendar_quarter
        if self.calendar_year is not None:
            props["calendar_year"] = self.calendar_year
            
        # Add datetime fields if present
        if self.created:
            props["created"] = self.created
        if self.updated:
            props["updated"] = self.updated
            
        # Add complex fields as JSON strings
        if self.speakers:
            props["speakers"] = json.dumps(self.speakers)
            
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'TranscriptNode':
        # Check required fields
        required_fields = ['id', 'symbol', 'company_name', 'conference_datetime', 'fiscal_quarter', 'fiscal_year']
        for field in required_fields:
            if field not in props:
                raise ValueError(f"Missing required field '{field}' for TranscriptNode")
        
        # Convert integer fields if they're stored as strings
        fiscal_quarter = props['fiscal_quarter']
        fiscal_year = props['fiscal_year']
        
        if isinstance(fiscal_quarter, str):
            fiscal_quarter = int(fiscal_quarter)
        if isinstance(fiscal_year, str):
            fiscal_year = int(fiscal_year)
            
        # Create instance with required fields
        instance = cls(
            id=props["id"],
            symbol=props["symbol"],
            company_name=props["company_name"],
            conference_datetime=props["conference_datetime"],
            fiscal_quarter=fiscal_quarter,
            fiscal_year=fiscal_year
        )
        
        # Set optional string fields
        if "formType" in props:
            instance.formType = props["formType"]
            
        # Set optional integer fields with proper conversion
        int_fields = ['calendar_quarter', 'calendar_year']
        for field in int_fields:
            if field in props and props[field] is not None:
                try:
                    # Convert to int if it's a string
                    if isinstance(props[field], str):
                        setattr(instance, field, int(props[field]))
                    else:
                        setattr(instance, field, props[field])
                except (ValueError, TypeError):
                    # Skip if conversion fails
                    pass
                    
        # Set string fields
        for field in ['created', 'updated']:
            if field in props and props[field]:
                setattr(instance, field, props[field])
                
        # Parse speakers JSON if available
        if "speakers" in props and props["speakers"]:
            try:
                instance.speakers = json.loads(props["speakers"])
            except:
                instance.speakers = {}
                
        return instance


class PreparedRemarkNode(Neo4jNode):
    """Node for prepared remarks section of a transcript"""
    
    def __init__(self, id: str, content: Optional[Union[str, List[str]]] = None):
        self._id = id
        self.content = content

    @property
    def id(self) -> str:
        """Return node ID"""
        return self._id

    @property
    def node_type(self) -> NodeType:
        return NodeType.PREPARED_REMARK

    @property
    def properties(self) -> Dict[str, Any]:
        props = {"id": self.id}
        if self.content:
            try:
                if isinstance(self.content, (list, dict)):
                    props["content"] = json.dumps(self.content)
                else:
                    props["content"] = self.content
            except Exception as e:
                # Fallback to string representation if JSON serialization fails
                props["content"] = str(self.content)
        return props

    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'PreparedRemarkNode':
        if "id" not in props:
            raise ValueError("Missing required field 'id' for PreparedRemarkNode")
            
        content = None
        if "content" in props and props["content"]:
            try:
                content = json.loads(props["content"])
            except:
                content = props["content"]
        return cls(id=props["id"], content=content)


class FullTranscriptTextNode(Neo4jNode):
    """Node for full transcript text content"""
    
    def __init__(self, id: str, content: Optional[str] = None):
        self._id = id
        self.content = content

    @property
    def id(self) -> str:
        """Return node ID"""
        return self._id

    @property
    def node_type(self) -> NodeType:
        return NodeType.FULL_TRANSCRIPT_TEXT

    @property
    def properties(self) -> Dict[str, Any]:
        props = {"id": self.id}
        if self.content:
            # For very long content, consider truncation if needed
            if len(self.content) > 1000000:  # Arbitrary limit of 1MB
                props["content"] = self.content[:1000000] + "... [truncated]"
            else:
                props["content"] = self.content
        return props

    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'FullTranscriptTextNode':
        if "id" not in props:
            raise ValueError("Missing required field 'id' for FullTranscriptTextNode")
            
        return cls(id=props["id"], content=props.get("content"))


class QuestionAnswerNode(Neo4jNode):
    """Node for question and answer section of a transcript"""
    
    def __init__(self, id: str, content: Optional[Union[str, List[str]]] = None, 
                 speaker_roles: Optional[Dict[str, str]] = None):
        self._id = id
        self.content = content
        self.speaker_roles = speaker_roles

    @property
    def id(self) -> str:
        """Return node ID"""
        return self._id

    @property
    def node_type(self) -> NodeType:
        return NodeType.QUESTION_ANSWER

    @property
    def properties(self) -> Dict[str, Any]:
        props = {"id": self.id}
        
        if self.content:
            try:
                if isinstance(self.content, (list, dict)):
                    props["content"] = json.dumps(self.content)
                else:
                    props["content"] = self.content
            except Exception as e:
                # Fallback to string representation if JSON serialization fails
                props["content"] = str(self.content)
        
        if self.speaker_roles:
            try:
                props["speaker_roles"] = json.dumps(self.speaker_roles)
            except Exception as e:
                # Fallback if JSON serialization fails
                props["speaker_roles"] = str(self.speaker_roles)
        
        return props

    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'QuestionAnswerNode':
        if "id" not in props:
            raise ValueError("Missing required field 'id' for QuestionAnswerNode")
            
        content = None
        speaker_roles = None
        
        if "content" in props and props["content"]:
            try:
                content = json.loads(props["content"])
            except:
                content = props["content"]
        
        if "speaker_roles" in props and props["speaker_roles"]:
            try:
                speaker_roles = json.loads(props["speaker_roles"])
            except:
                speaker_roles = None
                
        return cls(id=props["id"], content=content, speaker_roles=speaker_roles)


@dataclass
class QAExchangeNodeData:
    id: str
    transcript_id: str
    sequence: int = 0
    exchanges: List[Dict[str, Any]] = field(default_factory=list)
    questioner: Optional[str] = None
    questioner_title: Optional[str] = None
    responders: Optional[str] = None
    responder_title: Optional[str] = None
    embedding: Optional[List[float]] = None  # ✅ NEW


class QAExchangeNode(Neo4jNode):
    def __init__(self, **kwargs):
        self.data = QAExchangeNodeData(**kwargs)

    @property
    def id(self): return self.data.id
    @property
    def node_type(self): return NodeType.QA_EXCHANGE

    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            "id": self.data.id,
            "transcript_id": self.data.transcript_id,
            "sequence": self.data.sequence,
            "exchanges": json.dumps(self.data.exchanges),
        }
        if self.data.questioner:
            props["questioner"] = self.data.questioner
        if self.data.questioner_title:
            props["questioner_title"] = self.data.questioner_title
        if self.data.responders:
            props["responders"] = self.data.responders
        if self.data.responder_title:
            props["responder_title"] = self.data.responder_title
        if self.data.embedding is not None:
            props["embedding"] = self.data.embedding
        return props

    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'QAExchangeNode':
        exchanges_data = props.get("exchanges", [])
        exchanges = []
        
        if exchanges_data:
            try:
                if isinstance(exchanges_data, str):
                    exchanges = json.loads(exchanges_data)
                else:
                    exchanges = exchanges_data
            except:
                exchanges = []
            
        return cls(
            id=props["id"],
            transcript_id=props["transcript_id"],
            sequence=int(props.get("sequence", 0)),
            exchanges=exchanges,
            questioner=props.get("questioner"),
            questioner_title=props.get("questioner_title"),
            responders=props.get("responders"),
            responder_title=props.get("responder_title"),
            embedding=props.get("embedding")
        )
