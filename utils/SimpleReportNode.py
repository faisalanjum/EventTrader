from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from XBRL.xbrl_core import NodeType

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

@dataclass
class SimpleReportNode(Neo4jNode):
    """
    A simplified ReportNode class with just the essential fields needed for XBRL processing.
    This class is designed to be created outside the XBRL processor and passed in.
    """
    accessionNo: str
    primaryDocumentUrl: str
    cik: str
    
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
        return {
            "accessionNo": self.accessionNo,
            "primaryDocumentUrl": self.primaryDocumentUrl,
            "cik": self.cik,
            # Neo4j requirements
            "id": self.id
        } 