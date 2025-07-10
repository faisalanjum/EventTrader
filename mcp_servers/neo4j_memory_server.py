#!/usr/bin/env python3
"""
MCP Server for Neo4j Memory operations
Provides memory/caching capabilities for Neo4j data
"""

import os
import asyncio
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult
from neo4j import AsyncGraphDatabase
import json
from datetime import datetime
from collections import defaultdict


# Neo4j connection settings from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-bolt.neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


class Neo4jMemoryServer:
    def __init__(self):
        self.server = Server("neo4j-memory")
        self.driver = None
        self.memory_store = defaultdict(dict)  # In-memory cache
        
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
                name="cache_query",
                description="Cache the results of a Cypher query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key for storing the results"
                        },
                        "query": {
                            "type": "string",
                            "description": "The Cypher query to execute and cache"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Parameters for the Cypher query",
                            "default": {}
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "Time to live in seconds (default: 3600)",
                            "default": 3600
                        }
                    },
                    "required": ["key", "query"]
                }
            ),
            Tool(
                name="get_cached",
                description="Retrieve cached query results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Cache key to retrieve"
                        }
                    },
                    "required": ["key"]
                }
            ),
            Tool(
                name="invalidate_cache",
                description="Invalidate cached entries",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Pattern to match cache keys (supports wildcards)",
                            "default": "*"
                        }
                    }
                }
            ),
            Tool(
                name="get_node_summary",
                description="Get a summary of nodes by label with caching",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of node labels to summarize"
                        }
                    }
                }
            )
        ]
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[CallToolResult]:
        """Execute a tool"""
        if name == "cache_query":
            return await self.cache_query(
                arguments.get("key", ""),
                arguments.get("query", ""),
                arguments.get("parameters", {}),
                arguments.get("ttl", 3600)
            )
        elif name == "get_cached":
            return await self.get_cached(arguments.get("key", ""))
        elif name == "invalidate_cache":
            return await self.invalidate_cache(arguments.get("pattern", "*"))
        elif name == "get_node_summary":
            return await self.get_node_summary(arguments.get("labels", []))
        else:
            return [CallToolResult(
                content=[TextContent(text=f"Unknown tool: {name}")],
                is_error=True
            )]
            
    async def cache_query(self, key: str, query: str, parameters: Dict[str, Any], ttl: int) -> List[CallToolResult]:
        """Execute and cache a query"""
        try:
            async with self.driver.session() as session:
                result = await session.run(query, parameters)
                records = [record.data() async for record in result]
                
                # Store in cache with metadata
                self.memory_store[key] = {
                    "data": records,
                    "timestamp": datetime.utcnow().isoformat(),
                    "ttl": ttl,
                    "query": query,
                    "parameters": parameters
                }
                
                return [CallToolResult(
                    content=[TextContent(
                        text=json.dumps({
                            "success": True,
                            "key": key,
                            "records_cached": len(records),
                            "ttl": ttl
                        }, indent=2)
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
            
    async def get_cached(self, key: str) -> List[CallToolResult]:
        """Retrieve cached data"""
        if key in self.memory_store:
            cache_entry = self.memory_store[key]
            
            # Check if expired
            cached_time = datetime.fromisoformat(cache_entry["timestamp"])
            age = (datetime.utcnow() - cached_time).total_seconds()
            
            if age > cache_entry["ttl"]:
                del self.memory_store[key]
                return [CallToolResult(
                    content=[TextContent(
                        text=json.dumps({
                            "success": False,
                            "error": "Cache entry expired"
                        }, indent=2)
                    )]
                )]
            
            return [CallToolResult(
                content=[TextContent(
                    text=json.dumps({
                        "success": True,
                        "data": cache_entry["data"],
                        "age_seconds": int(age),
                        "ttl": cache_entry["ttl"]
                    }, indent=2, default=str)
                )]
            )]
        else:
            return [CallToolResult(
                content=[TextContent(
                    text=json.dumps({
                        "success": False,
                        "error": "Key not found in cache"
                    }, indent=2)
                )]
            )]
            
    async def invalidate_cache(self, pattern: str) -> List[CallToolResult]:
        """Invalidate cache entries matching pattern"""
        import fnmatch
        
        invalidated = []
        keys_to_remove = []
        
        for key in self.memory_store:
            if fnmatch.fnmatch(key, pattern):
                keys_to_remove.append(key)
                invalidated.append(key)
                
        for key in keys_to_remove:
            del self.memory_store[key]
            
        return [CallToolResult(
            content=[TextContent(
                text=json.dumps({
                    "success": True,
                    "invalidated": invalidated,
                    "count": len(invalidated)
                }, indent=2)
            )]
        )]
        
    async def get_node_summary(self, labels: List[str]) -> List[CallToolResult]:
        """Get summary of nodes by label with caching"""
        cache_key = f"node_summary:{':'.join(sorted(labels))}"
        
        # Try to get from cache first
        cached_result = await self.get_cached(cache_key)
        if cached_result[0].content[0].text.find('"success": true') != -1:
            return cached_result
            
        # Otherwise, query and cache
        try:
            summaries = {}
            async with self.driver.session() as session:
                for label in labels:
                    # Get count
                    count_result = await session.run(
                        f"MATCH (n:{label}) RETURN count(n) as count"
                    )
                    count = await count_result.single()
                    
                    # Get sample properties
                    props_result = await session.run(
                        f"MATCH (n:{label}) RETURN keys(n) as props LIMIT 5"
                    )
                    all_props = set()
                    async for record in props_result:
                        all_props.update(record["props"])
                    
                    summaries[label] = {
                        "count": count["count"],
                        "properties": list(all_props)
                    }
                    
            # Cache the results
            await self.cache_query(cache_key, "", {}, 3600)
            self.memory_store[cache_key]["data"] = summaries
            
            return [CallToolResult(
                content=[TextContent(
                    text=json.dumps({
                        "success": True,
                        "summaries": summaries
                    }, indent=2)
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
    
    server = Neo4jMemoryServer()
    
    # Initialize Neo4j connection
    await server.initialize()
    
    try:
        # Run the MCP server with stdio
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=InitializationOptions(
                    server_name="neo4j-memory",
                    server_version="1.0.0",
                    capabilities={}
                )
            )
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())