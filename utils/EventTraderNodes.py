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
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'SectorNode':
        sector_id = props.get('id', '')
        if not sector_id:
            raise ValueError("Missing required id field for SectorNode")
            
        return cls(
            node_id=sector_id,
            name=props.get('name', None)
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
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'IndustryNode':
        industry_id = props.get('id', '')
        if not industry_id:
            raise ValueError("Missing required id field for IndustryNode")
            
        return cls(
            node_id=industry_id,
            name=props.get('name', None),
            sector_id=props.get('sector_id', None)
        )

@dataclass
class NewsNode(Neo4jNode):
    """News node in Neo4j"""
    news_id: str  # Unique identifier
    title: Optional[str] = None
    body: Optional[str] = None
    teaser: Optional[str] = None
    created_at: Optional[datetime] = None  # Creation timestamp
    updated_at: Optional[datetime] = None  # Update timestamp
    url: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    market_session: Optional[str] = None  # e.g., "market_open", "market_closed"
    
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
        """Return node properties for Neo4j"""
        # Always include all fields, even if empty
        props = {
            'id': self.news_id
        }
        
        # Add optional string fields
        for field in ['title', 'body', 'teaser', 'url', 'market_session']:
            value = getattr(self, field)
            if value is not None:
                props[field] = value
            else:
                props[field] = ""
        
        # Convert datetime to string for Neo4j
        if self.created_at:
            props['created_at'] = self.created_at.isoformat()
        else:
            props['created_at'] = ""
            
        if self.updated_at:
            props['updated_at'] = self.updated_at.isoformat()
        else:
            props['updated_at'] = ""
        
        # Convert lists to JSON strings - always include even if empty
        props['authors'] = json.dumps(self.authors or [])
        props['channels'] = json.dumps(self.channels or [])
        props['tags'] = json.dumps(self.tags or [])
        
        return props
    
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'NewsNode':
        """Create NewsNode from Neo4j properties"""
        # Parse datetime fields using our new utility
        created_at = parse_date(props.get('created_at', '')) if 'created_at' in props else None
        updated_at = parse_date(props.get('updated_at', '')) if 'updated_at' in props else None
        
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
        
        return cls(
            news_id=props.get('id', ''),
            title=props.get('title', None),
            body=props.get('body', None),
            teaser=props.get('teaser', None),
            created_at=created_at,
            updated_at=updated_at,
            url=props.get('url', None),
            authors=authors,
            channels=channels,
            tags=tags,
            market_session=props.get('market_session', None)
        ) 