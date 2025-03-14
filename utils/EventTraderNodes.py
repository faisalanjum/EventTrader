from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
import json
from enum import Enum
from utils.date_utils import parse_date  # Import our date parsing utility

# Import node types from XBRLClasses
from XBRL.XBRLClasses import NodeType, RelationType, CompanyNode as XBRLCompanyNode

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
class CompanyNode(XBRLCompanyNode): 
    """
    EventTrader-specific extension of CompanyNode.
    Inherits from XBRLClasses.CompanyNode to maintain compatibility while allowing
    for EventTrader-specific extensions or overrides.
    """
    
    # No need to redefine fields as they're inherited from the parent class
    # The parent class already defines:
    # cik: str
    # name: Optional[str] = None
    # ticker: Optional[str] = None
    # etc.
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'CompanyNode':
        """
        Enhanced version of from_neo4j with EventTrader-specific handling
        """
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
class SectionNode(Neo4jNode):
    """
    Section node in Neo4j for SEC filing sections
    Example: "10-K-1" = "Business"
    """
    code: str          # e.g., "10-K-1", "10-Q-part1item1", "8-K-1-1"
    label: str         # e.g., "Business", "Financial Statements", "Entry into Material Agreement"
    category: str      # e.g., "10-K-SECTIONS", "10-Q-SECTIONS", "8-K-SECTIONS"
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.SECTION
        
    @property
    def id(self) -> str:
        return self.code
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "category": self.category,
            "displayLabel": self.label
        }
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'SectionNode':
        code = props.get('code', '')
        if not code:
            raise ValueError("Missing required code field for SectionNode")
            
        return cls(
            code=code,
            label=props.get('label', ''),
            category=props.get('category', '')
        )

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

class ReportNode(Neo4jNode):
    """Node representing an SEC report/filing in Neo4j"""
    
    def __init__(self, id, form_type=None, description=None, primary_document_url=None, 
                 accession_no=None, cik=None, company_name=None, filed_at=None, 
                 created=None, updated=None, period_of_report=None, is_xml=None,
                 link_to_txt=None, link_to_html=None, link_to_filing_details=None):
        super().__init__()
        self.form_type = form_type
        self.description = description
        self.primary_document_url = primary_document_url
        self.accession_no = accession_no
        self.cik = cik
        self.company_name = company_name
        self.filed_at = filed_at
        self.created = created
        self.updated = updated
        self.period_of_report = period_of_report
        self.is_xml = is_xml
        self.link_to_txt = link_to_txt
        self.link_to_html = link_to_html
        self.link_to_filing_details = link_to_filing_details
        
    @property
    def node_type(self) -> NodeType:
        return NodeType.REPORT
    
    @property
    def id(self) -> str:
        return self.accession_no
    
    @property
    def properties(self) -> Dict[str, Any]:
        props = {
            'id': self.accession_no,
            'form_type': self.form_type,
            'description': self.description,
            'primary_document_url': self.primary_document_url,
            'accession_no': self.accession_no,
            'cik': self.cik,
            'company_name': self.company_name,
            'filed_at': self.filed_at,
            'created': self.created.isoformat() if self.created else "",
            'updated': self.updated.isoformat() if self.updated else "",
            'period_of_report': self.period_of_report,
            'is_xml': self.is_xml,
            'link_to_txt': self.link_to_txt,
            'link_to_html': self.link_to_html,
            'link_to_filing_details': self.link_to_filing_details
        }
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'ReportNode':
        return cls(
            id=props.get('accession_no'),
            form_type=props.get('form_type'),
            description=props.get('description'),
            primary_document_url=props.get('primary_document_url'),
            accession_no=props.get('accession_no'),
            cik=props.get('cik'),
            company_name=props.get('company_name'),
            filed_at=props.get('filed_at'),
            created=parse_date(props.get('created', '')),
            updated=parse_date(props.get('updated', '')),
            period_of_report=props.get('period_of_report'),
            is_xml=props.get('is_xml'),
            link_to_txt=props.get('link_to_txt'),
            link_to_html=props.get('link_to_html'),
            link_to_filing_details=props.get('link_to_filing_details')
        )