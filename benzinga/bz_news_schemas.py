from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Any
from datetime import datetime
import pytz

class UnifiedNews(BaseModel):
    """Unified news model for both REST API and WebSocket data"""
    id: str
    symbols: List[str]
    created: str
    updated: str
    
    # Optional fields
    title: Optional[str] = None
    teaser: Optional[str] = None
    body: Optional[str] = None
    authors: List[str] = []
    channels: List[str] = []
    tags: List[str] = []
    url: Optional[str] = None

    @field_validator('created', 'updated')
    def normalize_dates(cls, v: str) -> str:
        return normalize_date(v)

    @model_validator(mode='after')
    def validate_all(cls, values):
        """Single place for all business rules"""
        errors = []
        
        # Check ID
        if not values.id:
            errors.append("News must have an ID")
            
        # Check symbols not empty
        if not values.symbols:
            errors.append("News must have at least one symbol")
            
        # Check content exists
        if not any([values.title, values.teaser, values.body]):
            errors.append("News must have content")
            
        if errors:
            raise ValueError(", ".join(errors))
        return values

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")
        return v

    @field_validator('title', 'teaser', 'body')
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None
        return v

# REST API Models
class RestAPIStock(BaseModel):
    """Stock with name field"""
    name: str

class RestAPIChannel(BaseModel):
    """Channel with name field"""
    name: str

class RestAPITag(BaseModel):
    """Tag with name field"""
    name: str

class ImageInfo(BaseModel):
    """Image information from API"""
    size: str
    url: str

class BzRestAPINews(BaseModel):
    """Schema for REST API news format"""
    id: int
    title: str
    author: str
    stocks: List[RestAPIStock]
    created: str
    updated: str
    url: str
    teaser: Optional[str]
    body: str
    channels: List[RestAPIChannel]
    tags: List[RestAPITag]
    image: Optional[List[ImageInfo]] = None  # Make image field optional

    model_config = {
        "extra": "forbid",  # Still forbid other unknown fields
        "str_strip_whitespace": True
    }

    def to_unified(self) -> UnifiedNews:
        """Convert to unified format"""
        symbols = [s.name for s in self.stocks] if self.stocks else []
        
        return UnifiedNews(
            id=str(self.id),
            symbols=symbols,  # This triggers validation if empty
            created=self.created,  # Will be normalized by UnifiedNews validator
            updated=self.updated,  # Will be normalized by UnifiedNews validator
            title=self.title if self.title else None,
            teaser=self.teaser if self.teaser else None,
            body=self.body if self.body else None,
            authors=[self.author] if self.author else [],  # Convert single to list
            channels=[c.name for c in self.channels] if self.channels else [],
            tags=[t.name for t in self.tags] if self.tags else [],
            url=self.url if self.url else None
        )

# WebSocket Models
class Security(BaseModel):
    """Security with symbol, exchange, and primary flag"""
    symbol: str
    exchange: Optional[str]
    primary: bool

class Content(BaseModel):
    """Content section of WebSocket message"""
    id: int
    title: str
    body: str
    authors: List[str]
    teaser: Optional[str]
    url: str
    securities: List[Security]
    channels: List[str]
    tags: List[str]
    created_at: str
    updated_at: str
    revision_id: Optional[int]
    type: Optional[str]
    image: Optional[List[ImageInfo]] = None

    def to_unified(self) -> UnifiedNews:
        """Convert to unified format"""
        return UnifiedNews(
            id=str(self.id),
            symbols=[sec.symbol for sec in self.securities],
            created=self.created_at,
            updated=self.updated_at,
            title=self.title if self.title else None,
            teaser=self.teaser if self.teaser else None,
            body=self.body if self.body else None,
            authors=self.authors if self.authors else [],
            channels=self.channels if self.channels else [],
            tags=self.tags if self.tags else [],
            url=self.url if self.url else None
        )

class NewsData(BaseModel):
    """Data section of WebSocket message"""
    action: str
    id: int
    timestamp: str
    content: Content

class BzWebSocketNews(BaseModel):
    """WebSocket news format"""
    api_version: str
    kind: str
    data: NewsData

    def to_unified(self) -> UnifiedNews:
        """Convert to unified format"""
        content = self.data.content
        # Extract symbols from securities
        symbols = [sec.symbol for sec in content.securities] if content.securities else []
        
        return UnifiedNews(
            id=str(content.id),
            symbols=symbols,  # Convert from securities to symbols list
            created=content.created_at,  # Will be normalized by validator
            updated=content.updated_at,  # Will be normalized by validator
            title=content.title if content.title else None,
            teaser=content.teaser if content.teaser else None,
            body=content.body if content.body else None,
            authors=content.authors if content.authors else [],
            channels=content.channels if content.channels else [],
            tags=content.tags if content.tags else [],
            url=content.url if content.url else None
        )

def normalize_date(date_str: str) -> str:
    """Convert any date format to ISO format in UTC"""
    # Handle REST API format: "Tue, 23 Jan 2024 13:30:00 -0400"
    try:
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    except ValueError:
        # Handle WebSocket format: "2024-01-23T04:03:09.000Z"
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    
    return dt.astimezone(pytz.UTC).isoformat()