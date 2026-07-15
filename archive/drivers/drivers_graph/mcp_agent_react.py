"""True ReAct Agent - Minimalist architecture with visible multi-node flow"""
import json
import numpy as np
import re
from typing import List, Dict, Set, Optional
from datetime import datetime
import asyncio
from difflib import get_close_matches
import os
from pathlib import Path
from dotenv import load_dotenv
import redis
import logging

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

from eventtrader import keys
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# Constants
MAX_STEPS = 10


class UltraMinimalMCPAgent:
    """Ultra minimal agent with tiered model support"""
    SEED_PATTERNS = [
        {
            "query": "Find News influencing Company with maximum daily_stock values",
            "cypher": "MATCH (n:News)-[r:INFLUENCES]->(c:Company) WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN' WITH n, c, toFloat(r.daily_stock) as daily_return WHERE NOT isNaN(daily_return) RETURN n.title, c.ticker, daily_return ORDER BY daily_return DESC LIMIT 10"
        },
        {
            "query": "Count all INFLUENCES relationships",  
            "cypher": "MATCH ()-[r:INFLUENCES]->() RETURN count(r)"
        },
        {
            "query": "Average returns from influences",
            "cypher": "MATCH ()-[r:INFLUENCES]->() WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN' WITH toFloat(r.daily_stock) as value WHERE NOT isNaN(value) RETURN AVG(value) as avg_return"
        },
        {
            "query": "Find recent 10-Q reports",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' AND datetime(r.created) > datetime() - duration('P60D') RETURN c.ticker, r.created ORDER BY r.created DESC LIMIT 20"
        },
        {
            "query": "Find news that drove stock down more than market",
            "cypher": "MATCH (n:News)-[rel:INFLUENCES]->(c:Company) WHERE rel.daily_stock < rel.daily_macro - 2.0 RETURN n.title, c.ticker, rel.daily_stock, rel.daily_macro ORDER BY rel.daily_stock LIMIT 20"
        },
        {
            "query": "Find news on same day as report",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date RETURN c.ticker, n.title, report_date LIMIT 20"
        },
        {
            "query": "Get NetIncomeLoss from company reports",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' AND f.is_numeric = 'true' RETURN c.ticker, f.value, r.created ORDER BY r.created DESC LIMIT 20"
        },
        {
            "query": "Find companies with news affecting returns on report filing date",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date AND rel.daily_stock IS NOT NULL RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, report_date ORDER BY rel.daily_stock LIMIT 20"
        }
    ]
    
    def __init__(self, use_redis: bool = True):
        self.patterns = self.SEED_PATTERNS.copy()
        self._schema = None
        self._tools = None
        self.use_redis = use_redis
        self.redis_client = None
        self.redis_key = "admin:neo4j_patterns"
        self.max_patterns = 50
        
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=31379,
                    decode_responses=True,
                    socket_timeout=2
                )
                self.redis_client.ping()
                logger.info("Connected to Redis for pattern storage")
                seed_lock_key = f"{self.redis_key}:seeds_loaded"
                if self.redis_client.setnx(seed_lock_key, "1"):
                    if self.redis_client.llen(self.redis_key) == 0:
                        logger.info("Loading seed patterns...")
                        with self.redis_client.pipeline() as pipe:
                            for pattern in self.SEED_PATTERNS:
                                pattern_copy = pattern.copy()
                                pipe.rpush(self.redis_key, json.dumps(pattern_copy))
                            pipe.execute()
                        logger.info(f"Loaded {len(self.SEED_PATTERNS)} seed patterns to Redis")
                    self.redis_client.expire(seed_lock_key, 30 * 24 * 60 * 60)
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory: {e}")
                self.redis_client = None
                self.use_redis = False
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=256,
            api_key=keys.OPENAI_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=keys.OPENAI_API_KEY
        )
        self.mcp_client = MultiServerMCPClient({
            "neo4j": {
                "url": "http://localhost:31380/mcp",
                "transport": "streamable_http",
            }
        })
    
    async def get_tools(self):
        if self._tools is None:
            self._tools = await self.mcp_client.get_tools()
        return self._tools
    
    async def _load_patterns_from_redis(self) -> List[Dict]:
        """Load patterns from Redis"""
        if not self.redis_client:
            return []
        try:
            patterns = []
            redis_patterns = self.redis_client.lrange(self.redis_key, 0, -1)
            
            for pattern_str in redis_patterns:
                pattern = json.loads(pattern_str)
                if 'embedding' in pattern and pattern['embedding']:
                    pattern['embedding'] = np.array(pattern['embedding'])
                patterns.append(pattern)
            
            return patterns
        except Exception as e:
            logger.warning(f"Failed to load patterns from Redis: {e}")
            return []
    
    async def _save_pattern_to_redis(self, pattern: Dict):
        """Save a single pattern to Redis"""
        if not self.redis_client:
            return
        try:
            pattern_copy = pattern.copy()
            if 'embedding' in pattern_copy and isinstance(pattern_copy['embedding'], np.ndarray):
                pattern_copy['embedding'] = pattern_copy['embedding'].tolist()
            
            self.redis_client.lpush(self.redis_key, json.dumps(pattern_copy))
            self.redis_client.ltrim(self.redis_key, 0, self.max_patterns - 1)
            
        except Exception as e:
            logger.warning(f"Failed to save pattern to Redis: {e}")
    
    async def get_schema(self):
        """Load schema with fallback"""
        if self._schema is None:
            try:
                tools = await self.get_tools()
                schema_tool = next(t for t in tools if t.name == "get_neo4j_schema")
                schema_result = await schema_tool.ainvoke({})
                
                self._schema = {
                    'labels': set(),
                    'relationships': set(),
                    'properties': {},
                    'rel_properties': {}
                }
                
                if isinstance(schema_result, str):
                    schema_data = json.loads(schema_result)
                    for item in schema_data:
                        label = item.get('label', '')
                        if label:
                            self._schema['labels'].add(label)
                            attrs = item.get('attributes', {})
                            self._schema['properties'][label] = set(attrs.keys())
                            
                            rels = item.get('relationships', {})
                            for rel_name, rel_list in rels.items():
                                for rel in rel_list:
                                    if isinstance(rel, list) and len(rel) > 1:
                                        self._schema['relationships'].add(rel[1])
                                        if rel[1] == 'INFLUENCES':
                                            self._schema['rel_properties']['INFLUENCES'] = {
                                                'daily_stock', 'hourly_stock', 'session_stock',
                                                'daily_industry', 'hourly_industry', 'session_industry',
                                                'daily_sector', 'hourly_sector', 'session_sector',
                                                'daily_macro', 'hourly_macro', 'session_macro'
                                            }
            except:
                self._schema = {
                    'labels': {'Company', 'News', 'Report', 'Industry', 'Sector', 'Date'},
                    'relationships': {'INFLUENCES', 'HAS_PRICE', 'BELONGS_TO'},
                    'properties': {
                        'Company': {'ticker', 'name', 'industry'},
                        'News': {'title', 'created'},
                        'Report': {'formType', 'created'}
                    },
                    'rel_properties': {
                        'INFLUENCES': {'daily_stock', 'daily_industry', 'daily_sector'}
                    }
                }
        return self._schema
    
    def _extract_properties(self, cypher: str) -> Dict[str, Set[str]]:
        """Extract all property references from query by alias"""
        prop_pattern = r'(\w+)\.(\w+)'
        matches = re.findall(prop_pattern, cypher)
        
        alias_props = {}
        for alias, prop in matches:
            if alias not in alias_props:
                alias_props[alias] = set()
            alias_props[alias].add(prop)
        return alias_props
    
    def _validate_and_fix_query(self, cypher: str) -> str:
        """Validate all aspects and fix if possible"""
        if not self._schema:
            return cypher
        
        # Fix common syntax error
        cypher = re.sub(
            r"(\w+\.\w+)\s+IS\s+NOT\s+NULL\s+<>\s*'NaN'",
            r"\1 IS NOT NULL AND \1 <> 'NaN'",
            cypher
        )
        
        # Extract and validate labels
        label_pattern = r'\((?:\w+:)?(\w+)(?:\s|{|\))'
        found_labels = set(re.findall(label_pattern, cypher))
        
        for label in found_labels:
            if label not in self._schema['labels']:
                closest = get_close_matches(label, self._schema['labels'], n=1, cutoff=0.3)
                if closest:
                    cypher = re.sub(rf'\b{label}\b', closest[0], cypher)
        
        # Extract alias-label mappings
        alias_pattern = r'\((\w+):(\w+)\)'
        alias_to_label = {}
        for match in re.finditer(alias_pattern, cypher):
            alias, label = match.groups()
            if label in self._schema['labels']:
                alias_to_label[alias] = label
        
        # Update alias mappings after label fixes
        for alias, lbl in list(alias_to_label.items()):
            if lbl not in self._schema['labels']:
                for old_label in found_labels:
                    if old_label == lbl:
                        closest = get_close_matches(old_label, self._schema['labels'], n=1, cutoff=0.3)
                        if closest:
                            alias_to_label[alias] = closest[0]
        
        # Alias-aware property validation
        alias_props = self._extract_properties(cypher)
        
        for alias, props in alias_props.items():
            for prop in props:
                if alias == 'r' and 'INFLUENCES' in cypher:
                    if prop not in self._schema['rel_properties'].get('INFLUENCES', set()):
                        cypher = re.sub(rf'\s+AND\s+{alias}\.{prop}[^,\s]*', '', cypher)
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}[^,\s]*\s+AND', 'WHERE', cypher)
                        cypher = re.sub(rf',\s*{alias}\.{prop}[^,\s]*', '', cypher)
                        cypher = re.sub(rf'RETURN\s+{alias}\.{prop}[^,\s]*,\s*', 'RETURN ', cypher)
                elif alias in alias_to_label:
                    label = alias_to_label[alias]
                    label_props = self._schema['properties'].get(label, set())
                    if prop not in label_props:
                        cypher = re.sub(rf'\s+AND\s+{alias}\.{prop}[^,\s]*', '', cypher)
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}\s*=\s*[^\s]+\s+AND', 'WHERE', cypher)
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}\s*=\s*[^\s]+\s+RETURN', 'WHERE RETURN', cypher) 
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}\s*=\s*[^\s]+', '', cypher)
                        cypher = re.sub(rf',\s*{alias}\.{prop}[^,\s]*', '', cypher)
                        cypher = re.sub(rf'RETURN\s+{alias}\.{prop}[^,\s]*,\s*', 'RETURN ', cypher)
        
        # Safe regex cleanup
        cypher = re.sub(r'WHERE\s+AND\s+', 'WHERE ', cypher)
        cypher = re.sub(r'WHERE\s+RETURN', ' RETURN', cypher)
        cypher = re.sub(r'WHERE\s+LIMIT', ' LIMIT', cypher)
        cypher = re.sub(r'WHERE\s+ORDER', ' ORDER', cypher)
        cypher = re.sub(r'WHERE\s*\)', ')', cypher)
        cypher = re.sub(r',\s*,', ',', cypher)
        cypher = re.sub(r'RETURN\s*,', 'RETURN', cypher)
        
        if not re.search(r'\bLIMIT\s+\d+', cypher) and 'count(' not in cypher.lower():
            cypher += ' LIMIT 1000'
        
        return cypher
    
    async def query_generate(self, user_query: str, errors: List[str] = None) -> str:
        """Generate Cypher query - modified to accept errors parameter"""
        await self.get_schema()
        
        # Generate Cypher
        examples = await self._find_examples(user_query)
        prompt = self._build_prompt(user_query, examples)
        
        # Add error feedback if provided
        if errors:
            prompt += "\n\nPrevious attempts failed:"
            for i, err in enumerate(errors[-2:], 1):  # Only use last 2 errors
                enhanced = self._enhance_feedback(err)
                prompt += f"\n{i}. {enhanced}"
        
        response = await self.llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_query)
        ])
        
        cypher = response.content.strip()
        if cypher.startswith("```"):
            cypher = cypher.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        cypher = self._validate_and_fix_query(cypher)
        return cypher
    
    async def query_execute(self, cypher: str) -> Dict:
        """Execute Cypher query and return raw result or error"""
        tools = await self.get_tools()
        read_tool = next(t for t in tools if t.name == "read_neo4j_cypher")
        
        # Test with EXPLAIN first
        try:
            explain_result = await read_tool.ainvoke({"query": f"EXPLAIN {cypher}"})
            if "error" in str(explain_result).lower():
                return {"error": str(explain_result)}
        except Exception as e:
            return {"error": f"EXPLAIN failed: {str(e)}"}
        
        # Execute
        try:
            result = await read_tool.ainvoke({"query": cypher})
            return {"result": result, "cypher": cypher}
        except Exception as e:
            return {"error": str(e)}
    
    def _enhance_feedback(self, feedback: str) -> str:
        """Convert raw error to actionable guidance"""
        feedback_lower = feedback.lower()
        
        if 'unknown property' in feedback_lower:
            prop_match = re.search(r"property[:\s]+['\"`]?(\w+)['\"`]?", feedback, re.IGNORECASE)
            if prop_match:
                bad_prop = prop_match.group(1)
                return f"Property '{bad_prop}' doesn't exist. Use: daily_stock, hourly_stock, session_stock for returns"
        
        elif 'unknown relationship' in feedback_lower:
            return "Use INFLUENCES for news->company relationships, PRIMARY_FILER for report->company"
        
        elif 'no results' in feedback_lower or feedback == '[]':
            return "No results. Try: 1) Remove time filters, 2) Use different return type (hourly/daily), 3) Check if data exists"
        
        elif 'syntax error' in feedback_lower:
            return "Syntax error. Remember: WHERE prop IS NOT NULL AND prop <> 'NaN'"
        
        return feedback[:500]
    
    async def _find_examples(self, query: str, k: int = 2) -> List[Dict]:
        """Find similar examples"""
        if self.use_redis and self.redis_client:
            patterns = await self._load_patterns_from_redis()
            all_patterns = self.SEED_PATTERNS + patterns
        else:
            all_patterns = self.patterns
        
        if not all_patterns:
            return []
        
        query_emb = await self.embeddings.aembed_query(query)
        scores = []
        
        for pattern in all_patterns:
            if 'embedding' not in pattern:
                pattern['embedding'] = await self.embeddings.aembed_query(pattern['query'])
            sim = np.dot(query_emb, pattern['embedding']) / (
                np.linalg.norm(query_emb) * np.linalg.norm(pattern['embedding'])
            )
            if sim > 0.5:
                scores.append((sim, pattern))
        
        scores.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scores[:k]]
    
    def _build_prompt(self, query: str, examples: List[Dict]) -> str:
        prompt = ["You are a Neo4j Cypher query generator. Follow the examples EXACTLY."]
        
        if examples:
            prompt.append("\nExamples showing CORRECT syntax:")
            for i, ex in enumerate(examples, 1):
                prompt.append(f"\nExample {i}:")
                prompt.append(f"User: {ex['query']}")
                prompt.append(f"Cypher: {ex['cypher']}")
        
        prompt.extend([
            "\nCRITICAL RULES - FOLLOW EXACTLY:",
            "1. For NULL/NaN checks, ALWAYS use this pattern:",
            "   CORRECT: WHERE r.property IS NOT NULL AND r.property <> 'NaN'",
            "   WRONG: WHERE r.property IS NOT NULL <> 'NaN'",
            "2. Use toFloat() and check NOT isNaN() for numeric operations",
            "3. Include relevant properties in RETURN (e.g., c.ticker for companies)",
            "\nGenerate Cypher query following the EXACT pattern from the examples."
        ])
        
        return "\n".join(prompt)
    
    async def _learn(self, query: str, cypher: str):
        """Learn with strict size limit"""
        query_emb = await self.embeddings.aembed_query(query)
        
        if self.use_redis and self.redis_client:
            existing_patterns = await self._load_patterns_from_redis()
        else:
            existing_patterns = self.patterns[3:]
        
        for pattern in existing_patterns:
            if 'embedding' not in pattern:
                pattern['embedding'] = await self.embeddings.aembed_query(pattern['query'])
            sim = np.dot(query_emb, pattern['embedding']) / (
                np.linalg.norm(query_emb) * np.linalg.norm(pattern['embedding'])
            )
            if sim > 0.95:
                return
        
        new_pattern = {
            "query": query,
            "cypher": cypher,
            "embedding": query_emb
        }
        
        if self.use_redis and self.redis_client:
            await self._save_pattern_to_redis(new_pattern)
        else:
            self.patterns.append(new_pattern)
            if len(self.patterns) > self.max_patterns:
                num_seeds = len(self.SEED_PATTERNS)
                self.patterns = self.patterns[:num_seeds] + self.patterns[-(self.max_patterns - num_seeds):]
    
    def _is_error(self, result) -> bool:
        result_str = str(result).lower()
        return any(err in result_str for err in ['error:', 'exception', 'failed'])


# State definition
class AgentState(TypedDict):
    query: str
    errors: List[str]
    result: Optional[Dict]
    cypher: Optional[str]  # Current cypher query
    last_result: Optional[Dict]  # Last execution result


# Global agent
_global_agent = None
_agent_lock = asyncio.Lock()


async def _get_agent():
    """Get or create singleton agent"""
    global _global_agent
    if _global_agent is None:
        async with _agent_lock:
            if _global_agent is None:
                _global_agent = UltraMinimalMCPAgent()
    return _global_agent


def create_graph():
    """Create the true ReAct graph"""
    graph = StateGraph(AgentState)
    
    async def agent_generate(state):
        """Generate Cypher based on query and error history"""
        agent = await _get_agent()
        cypher = await agent.query_generate(
            state["query"], 
            state.get("errors", [])
        )
        logger.info(f"Generated Cypher: {cypher[:100]}...")
        return {"cypher": cypher}
    
    async def tool_execute(state):
        """Execute the generated Cypher"""
        agent = await _get_agent()
        result = await agent.query_execute(state["cypher"])
        return {"last_result": result}
    
    async def check_result(state):
        """Check if result is OK and handle accordingly"""
        agent = await _get_agent()
        result = state["last_result"]
        
        # Check for errors
        if "error" in result:
            errors = state.get("errors", []) + [result["error"]]
            return {"errors": errors, "result": None}
        
        # Check for empty results
        raw_result = result.get("result", "")
        if raw_result == '[]' or not raw_result:
            errors = state.get("errors", []) + ["Query returned no results"]
            return {"errors": errors, "result": None}
        
        # Check if result looks like an error
        if agent._is_error(raw_result):
            errors = state.get("errors", []) + [str(raw_result)]
            return {"errors": errors, "result": None}
        
        # Success! Learn and return
        await agent._learn(state["query"], result["cypher"])
        return {"result": result}
    
    def should_continue(state):
        """Decide whether to continue or end"""
        # Check if we have a successful result
        if state.get("result") is not None:
            return "end"
        
        # Check if we've exceeded max attempts
        if len(state.get("errors", [])) >= MAX_STEPS:
            return "end"
        
        # Otherwise, continue
        return "generate"
    
    # Add nodes
    graph.add_node("generate", agent_generate)
    graph.add_node("execute", tool_execute)
    graph.add_node("check", check_result)
    
    # Add edges
    graph.set_entry_point("generate")
    graph.add_edge("generate", "execute")
    graph.add_edge("execute", "check")
    graph.add_conditional_edges(
        "check",
        should_continue,
        {
            "generate": "generate",
            "end": END
        }
    )
    
    return graph.compile()


# Create the graph
mcp_agent = create_graph()


# Backwards compatibility function
async def query_neo4j(query: str) -> Dict:
    """Query Neo4j with true ReAct architecture"""
    agent = await _get_agent()
    result = await mcp_agent.ainvoke({
        "query": query,
        "errors": [],
        "result": None,
        "cypher": None,
        "last_result": None
    })
    
    if result.get("result"):
        return {
            "query": result["result"]["cypher"],
            "result": result["result"]["result"],
            "success": True,
            "attempts": len(result.get("errors", [])) + 1
        }
    else:
        return {
            "error": "All attempts failed",
            "last_errors": result.get("errors", [])[-2:],
            "success": False,
            "attempts": len(result.get("errors", []))
        }


if __name__ == "__main__":
    async def test():
        result = await query_neo4j("which Company seems to have the highest hourly returns related news lately")
        print(f"Success: {result.get('success')} (Attempts: {result.get('attempts', 0)})")
        print(f"Query: {result.get('query', '')[:100]}...")
    asyncio.run(test())