from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
import json

# Import node types from XBRLClasses
from XBRL.XBRLClasses import NodeType, RelationType

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
class NewsNode(Neo4jNode):
    """News node in Neo4j"""
    news_id: str  # Unique identifier
    title: str = ""
    body: str = ""
    teaser: Optional[str] = None
    created_at: Optional[datetime] = None  # Creation timestamp
    updated_at: Optional[datetime] = None  # Update timestamp
    url: str = ""
    authors: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    market_session: str = ""  # e.g., "market_open", "market_closed"
    
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
            'id': self.news_id,
            'title': self.title,
            'body': self.body,
            'teaser': self.teaser or "",  # Ensure teaser is never None
            'url': self.url,
            'market_session': self.market_session
        }
        
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
    def from_neo4j(cls, props: Dict[str, Any]) -> NewsNode:
        """Create NewsNode from Neo4j properties"""
        # Parse datetime fields
        created_at = None
        if 'created_at' in props:
            try:
                created_at = datetime.fromisoformat(props['created_at'])
            except:
                pass
                
        updated_at = None
        if 'updated_at' in props:
            try:
                updated_at = datetime.fromisoformat(props['updated_at'])
            except:
                pass
        
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
            title=props.get('title', ''),
            body=props.get('body', ''),
            teaser=props.get('teaser'),
            created_at=created_at,
            updated_at=updated_at,
            url=props.get('url', ''),
            authors=authors,
            channels=channels,
            tags=tags,
            market_session=props.get('market_session', '')
        ) 