from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
import json
from enum import Enum
from utils.date_utils import parse_date  # Import our date parsing utility

# Import node types from XBRLClasses
from XBRL.XBRLClasses import NodeType, RelationType, CompanyNode as XBRLCompanyNode, ReportNode as XBRLReportNode

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
class ReportNode(XBRLReportNode):
    """
    EventTrader-specific extension of ReportNode.
    Inherits from XBRLClasses.ReportNode to maintain compatibility while allowing
    for EventTrader-specific extensions or overrides.
    
    Fields are mapped from SEC API and Redis data to the XBRL structure.
    """
    
    # No need to redefine core fields as they're inherited from the parent class
    # The parent class already defines:
    # formType: str
    # periodEnd: str
    # isAmendment: bool
    # primaryDocumentUrl: str
    # cik: str
    
    # Additional fields from SEC API/Redis not in XBRL base class
    description: Optional[str] = None
    is_xml: Optional[bool] = None
    companyName: Optional[str] = None
    linkToTxt: Optional[str] = None
    linkToHtml: Optional[str] = None
    linkToFilingDetails: Optional[str] = None
    effectivenessDate: Optional[str] = None
    exhibits: Optional[Dict[str, Any]] = field(default_factory=dict)
    items: Optional[List[str]] = field(default_factory=list)
    symbols: Optional[List[str]] = field(default_factory=list)
    entities: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    extracted_sections: Optional[Dict[str, Any]] = field(default_factory=dict)
    financial_statements: Optional[Dict[str, Any]] = field(default_factory=dict)
    exhibit_contents: Optional[Dict[str, Any]] = field(default_factory=dict)
    created: Optional[str] = None
    updated: Optional[str] = None
    
    # Override id property to use accessionNo as the unique identifier
    @property
    def id(self) -> str:
        """Use accessionNo as unique identifier"""
        if not self.accessionNo:
            raise ValueError("Missing required accessionNo for ReportNode")
        return self.accessionNo
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'ReportNode':
        """
        Create a ReportNode from Neo4j properties
        """
        # Check for required fields
        required_fields = ['formType', 'periodEnd', 'isAmendment', 'cik']
        
        missing_fields = [field for field in required_fields if field not in props]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Ensure we have either primaryDocumentUrl or instanceFile
        if 'primaryDocumentUrl' not in props and 'instanceFile' not in props:
            raise ValueError("Either primaryDocumentUrl or instanceFile is required")
            
        # Performance optimization: use primaryDocumentUrl directly if available, otherwise use instanceFile
        primary_document_url = props.get('primaryDocumentUrl', props.get('instanceFile', ''))
        
        # Map fields from Neo4j properties to ReportNode fields
        # First set required fields
        report = cls(
            formType=props.get('formType', ''),
            periodEnd=props.get('periodEnd', ''),
            isAmendment=props.get('isAmendment', False),
            primaryDocumentUrl=primary_document_url,
            cik=props.get('cik', '')
        )
        
        # Make sure accessionNo is set
        report.accessionNo = props.get('accessionNo', '')
        
        # Map optional fields directly
        optional_fields = [
            'filedAt', 'periodOfReport', 'insertedAt', 'status',
            'description', 'is_xml', 'companyName',
            'linkToTxt', 'linkToHtml', 'linkToFilingDetails', 'effectivenessDate',
            'created', 'updated'
        ]
        
        for field in optional_fields:
            if field in props and props[field] is not None:
                setattr(report, field, props[field])
                
        # Handle serialized complex fields
        complex_fields = {
            'exhibits': dict,
            'items': list,
            'symbols': list,
            'entities': list,
            'extracted_sections': dict,
            'financial_statements': dict,
            'exhibit_contents': dict
        }
        
        for field, field_type in complex_fields.items():
            if field in props and props[field]:
                # Try to deserialize if stored as JSON
                try:
                    if isinstance(props[field], str):
                        setattr(report, field, json.loads(props[field]))
                    else:
                        setattr(report, field, props[field])
                except (json.JSONDecodeError, TypeError):
                    # If deserializing fails, keep as is
                    setattr(report, field, props[field])
                        
        return report
    
    @property
    def properties(self) -> Dict[str, Any]:
        """
        Returns enhanced properties for Neo4j node with EventTrader-specific fields
        Overrides the base class method to include additional fields
        """
        # Get base properties from parent class
        props = super().properties
        
        # Override id with accessionNo
        props['id'] = self.id
        
        # Add EventTrader-specific properties
        additional_props = {
            'primaryDocumentUrl': self.primaryDocumentUrl,
            'description': self.description,
            'is_xml': self.is_xml,
            'companyName': self.companyName,
            'linkToTxt': self.linkToTxt,
            'linkToHtml': self.linkToHtml,
            'linkToFilingDetails': self.linkToFilingDetails,
            'effectivenessDate': self.effectivenessDate,
            'created': self.created,
            'updated': self.updated
        }
        
        # Add non-None additional properties
        props.update({k: v for k, v in additional_props.items() if v is not None})
        
        # Handle complex fields by serializing to JSON
        if self.exhibits:
            props['exhibits'] = json.dumps(self.exhibits)
        if self.items:
            props['items'] = json.dumps(self.items)
        if self.symbols:
            props['symbols'] = json.dumps(self.symbols)
        if self.entities:
            props['entities'] = json.dumps(self.entities)
        if self.extracted_sections:
            props['extracted_sections'] = json.dumps(self.extracted_sections)
        if self.financial_statements:
            props['financial_statements'] = json.dumps(self.financial_statements)
        if self.exhibit_contents:
            props['exhibit_contents'] = json.dumps(self.exhibit_contents)
        
        return props
    
    @classmethod
    def from_redis(cls, redis_data: Dict[str, Any]) -> 'ReportNode':
        """
        Create a ReportNode from Redis data
        Mainly used for SEC filings and reports
        """
        # Required checks
        required_fields = ['formType', 'filedAt']
        missing_fields = [field for field in required_fields if field not in redis_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Determine instance file (primaryDocumentUrl)
        instance_file = ''
        instance_field = 'primaryDocumentUrl'
        
        # Try different possible field names for instance file
        for field in ['primaryDocumentUrl', 'instanceFile', 'linkToFilingDetails']:
            if redis_data.get(field):
                instance_file = redis_data[field]
                instance_field = field
                break
            
        # If we have a sourceHTML, use that as a fallback
        if not instance_file and redis_data.get('sourceHTML'):
            instance_file = redis_data['sourceHTML']
        
        # Extract CIK from cik or entities
        cik = redis_data.get('cik', '')
        
        # If no CIK directly, try to extract from entities
        if not cik and redis_data.get('entities'):
            cik = redis_data['entities'][0].get('cik', '')
        
        # Performance optimization: create the instance directly with all required fields
        # Create instance with required fields
        report = cls(
            formType=redis_data.get('formType', 'UNKNOWN'),
            # Map periodEnd - use periodOfReport if available, otherwise use filedAt
            periodEnd=redis_data.get('periodOfReport', redis_data.get('filedAt', '')[:10]),
            isAmendment=('/A' in redis_data.get('formType', '') or '[Amend]' in redis_data.get('description', '')),
            primaryDocumentUrl=instance_file,
            cik=cik
        )
        
        # Store the original data for later access to metadata and returns
        report._original_data = redis_data
        
        # Set accessionNo explicitly as it's our primary identifier
        report.accessionNo = redis_data.get('accessionNo', '')
        
        return report



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