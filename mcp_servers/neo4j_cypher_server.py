#!/usr/bin/env python3
"""
MCP Server for Neo4j Cypher queries
Provides an interface to execute Cypher queries against the Neo4j database
"""

import os
import asyncio
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult
from neo4j import AsyncGraphDatabase
import json

# Neo4j connection settings from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-bolt.neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


class Neo4jCypherServer:
    def __init__(self):
        self.server = Server("neo4j-cypher")
        self.driver = None
        
        # Register handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
        
    async def initialize(self):
        """Initialize Neo4j connection"""
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
    async def cleanup(self):
        """Cleanup Neo4j connection"""
        if self.driver:
            await self.driver.close()
            
    async def list_tools(self) -> List[Tool]:
        """List available tools"""
        return [
            Tool(
                name="execute_cypher",
                description="Execute a Cypher query against the Neo4j database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The Cypher query to execute"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Parameters for the Cypher query",
                            "default": {}
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_schema",
                description="Get the current Neo4j database schema",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[CallToolResult]:
        """Execute a tool"""
        if name == "execute_cypher":
            return await self.execute_cypher(
                arguments.get("query", ""),
                arguments.get("parameters", {})
            )
        elif name == "get_schema":
            return await self.get_schema()
        else:
            return [CallToolResult(
                content=[TextContent(text=f"Unknown tool: {name}")],
                is_error=True
            )]
            
    async def execute_cypher(self, query: str, parameters: Dict[str, Any]) -> List[CallToolResult]:
        """Execute a Cypher query"""
        try:
            async with self.driver.session() as session:
                result = await session.run(query, parameters)
                records = [record.data() async for record in result]
                
                return [CallToolResult(
                    content=[TextContent(
                        text=json.dumps({
                            "success": True,
                            "records": records,
                            "count": len(records)
                        }, indent=2, default=str)
                    )]
                )]
        except Exception as e:
            return [CallToolResult(
                content=[TextContent(
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )],
                is_error=True
            )]
            
    async def get_schema(self) -> List[CallToolResult]:
        """Get database schema"""
        try:
            async with self.driver.session() as session:
                # Get node labels
                labels_result = await session.run("CALL db.labels()")
                labels = [record["label"] async for record in labels_result]
                
                # Get relationship types
                rels_result = await session.run("CALL db.relationshipTypes()")
                relationships = [record["relationshipType"] async for record in rels_result]
                
                # Get indexes
                indexes_result = await session.run("SHOW INDEXES")
                indexes = [record.data() async for record in indexes_result]
                
                return [CallToolResult(
                    content=[TextContent(
                        text=json.dumps({
                            "success": True,
                            "labels": labels,
                            "relationships": relationships,
                            "indexes": indexes
                        }, indent=2, default=str)
                    )]
                )]
        except Exception as e:
            return [CallToolResult(
                content=[TextContent(
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )],
                is_error=True
            )]


async def main():
    """Main entry point"""
    import sys
    from mcp.server.stdio import stdio_server
    
    server = Neo4jCypherServer()
    
    # Initialize Neo4j connection
    await server.initialize()
    
    try:
        # Run the MCP server with stdio
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=InitializationOptions(
                    server_name="neo4j-cypher",
                    server_version="1.0.0",
                    capabilities={}
                )
            )
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())