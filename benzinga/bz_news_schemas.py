from pydantic import BaseModel, field_validator, ValidationError
from typing import List, Optional, Any
from datetime import datetime

# Existing models for WebSocket
class Security(BaseModel):
    symbol: str
    exchange: str
    primary: bool

class Image(BaseModel):
    size: str
    url: str

class Content(BaseModel):
    id: int
    revision_id: int
    type: str
    title: str
    body: str
    authors: List[str]
    teaser: Optional[str]
    url: str
    channels: List[str]
    securities: List[Security]
    created_at: str
    updated_at: str
    tags: Optional[List[Any]] = []
    image: Optional[List[Image]] = None

class NewsData(BaseModel):
    action: str
    id: int
    timestamp: str
    content: Content

class BenzingaNews(BaseModel):
    api_version: str
    kind: str
    data: NewsData

    class Config:
        extra = "allow"  # Allows additional fields without raising errors


    @classmethod
    def from_rest_api(cls, data: dict) -> "UnifiedNews":
        """Convert REST API data to unified format"""
        try:
            news = UnifiedNews(
                id=str(data.get('id', 'No ID')),
                title=data.get('title', 'No Title'),
                body=data.get('body', ''),
                teaser=data.get('teaser', None),
                authors=[data.get('author', 'Unknown')],
                symbols=[stock['name'] for stock in data.get('stocks', [])],
                channels=[channel['name'] for channel in data.get('channels', [])],
                tags=[tag['name'] for tag in data.get('tags', [])],
                created=data.get('created', 'Unknown Date'),
                updated=data.get('updated', 'Unknown Date'),
                url=data.get('url', 'No URL')
            )
            return news
        except ValidationError as e:
            print(f"Validation failed for data: {data}")
            print(f"Error: {e}")
            raise



    @classmethod
    def from_websocket(cls, news: "BenzingaNews") -> "UnifiedNews":
        content = news.data.content
        try:
            return UnifiedNews(
                id=str(content.id),
                title=content.title,
                body=content.body,
                teaser=content.teaser,
                authors=content.authors,
                symbols=[sec.symbol for sec in content.securities],
                channels=content.channels,
                tags=content.tags,
                created=content.created_at,
                updated=content.updated_at,
                url=content.url
            )
        except ValidationError as e:
            print(f"Validation failed: {e}")  # This will show which fields are problematic
            raise


class UnifiedNews(BaseModel):
    """Unified news model for both REST API and WebSocket data"""
    id: str 
    title: str
    body: str 
    teaser: Optional[str]
    authors: List[str]  
    symbols: List[str]
    channels: List[str]
    tags: List[str]
    created: str
    updated: str
    url: str

    @field_validator('symbols')
    def symbols_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("News must have at least one symbol")
        return v