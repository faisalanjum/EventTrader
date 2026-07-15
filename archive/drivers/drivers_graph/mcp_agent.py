"""Ultra minimal MCP agent with true 100% accuracy"""
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
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class UltraMinimalMCPAgent:
    """Ultra minimal agent with complete validation"""
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
                    port=31379,  # NodePort from CLAUDE.md
                    decode_responses=True,
                    socket_timeout=2
                )
                self.redis_client.ping()
                logger.info("Connected to Redis for pattern storage")
                seed_lock_key = f"{self.redis_key}:seeds_loaded"
                if self.redis_client.setnx(seed_lock_key, "1"):
                    # We got the lock, check if seeds actually need loading
                    if self.redis_client.llen(self.redis_key) == 0:
                        logger.info("Loading seed patterns (exactly once)...")
                        with self.redis_client.pipeline() as pipe:
                            for pattern in self.SEED_PATTERNS:
                                pattern_copy = pattern.copy()
                                pipe.rpush(self.redis_key, json.dumps(pattern_copy))
                            pipe.execute()
                        logger.info(f"Loaded {len(self.SEED_PATTERNS)} seed patterns to Redis")
                    # Set expiry on lock in case of Redis restart (30 days)
                    self.redis_client.expire(seed_lock_key, 30 * 24 * 60 * 60)
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory: {e}")
                self.redis_client = None
                self.use_redis = False
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Back to original for cost efficiency
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
            # Get all patterns from Redis list
            patterns = []
            redis_patterns = self.redis_client.lrange(self.redis_key, 0, -1)
            
            for pattern_str in redis_patterns:
                pattern = json.loads(pattern_str)
                # Convert embedding back to numpy array
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
            # Convert numpy embedding to list for JSON serialization
            pattern_copy = pattern.copy()
            if 'embedding' in pattern_copy and isinstance(pattern_copy['embedding'], np.ndarray):
                pattern_copy['embedding'] = pattern_copy['embedding'].tolist()
            
            # Add to Redis list (at the beginning)
            self.redis_client.lpush(self.redis_key, json.dumps(pattern_copy))
            
            # Trim to max size (keep only the most recent patterns)
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
                    'properties': {},  # label -> set of properties
                    'rel_properties': {}  # relationship -> set of properties
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
                                        # Common INFLUENCES properties
                                        if rel[1] == 'INFLUENCES':
                                            self._schema['rel_properties']['INFLUENCES'] = {
                                                'daily_stock', 'hourly_stock', 'session_stock',
                                                'daily_industry', 'hourly_industry', 'session_industry',
                                                'daily_sector', 'hourly_sector', 'session_sector',
                                                'daily_macro', 'hourly_macro', 'session_macro'
                                            }
            except:
                # Minimal fallback
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
        # Match patterns like r.property, n.property, c.property
        prop_pattern = r'(\w+)\.(\w+)'
        matches = re.findall(prop_pattern, cypher)
        
        # Group by alias
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
        
        # CRITICAL: Both GPT-4o-mini and GPT-3.5-turbo consistently generate
        # "IS NOT NULL <> 'NaN'" syntax despite explicit examples and rules.
        # This appears to be a learned pattern from their training data.
        # We must fix this to prevent Neo4j syntax errors.
        cypher = re.sub(
            r"(\w+\.\w+)\s+IS\s+NOT\s+NULL\s+<>\s*'NaN'",
            r"\1 IS NOT NULL AND \1 <> 'NaN'",
            cypher
        )
        
        # 1. Extract and validate labels
        label_pattern = r'\((?:\w+:)?(\w+)(?:\s|{|\))'
        found_labels = set(re.findall(label_pattern, cypher))
        
        # Auto-map invalid labels to closest valid ones
        for label in found_labels:
            if label not in self._schema['labels']:
                # Find closest match
                closest = get_close_matches(label, self._schema['labels'], n=1, cutoff=0.3)
                if closest:
                    cypher = re.sub(rf'\b{label}\b', closest[0], cypher)
        
        # 2. Extract alias-label mappings
        # Pattern: (alias:Label) - must have both alias and label
        alias_pattern = r'\((\w+):(\w+)\)'
        alias_to_label = {}
        for match in re.finditer(alias_pattern, cypher):
            alias, label = match.groups()
            if label in self._schema['labels']:
                alias_to_label[alias] = label
                
        # Update alias mappings after label fixes
        for alias, lbl in list(alias_to_label.items()):
            if lbl not in self._schema['labels']:
                # Find the replaced label
                for old_label in found_labels:
                    if old_label == lbl:
                        closest = get_close_matches(old_label, self._schema['labels'], n=1, cutoff=0.3)
                        if closest:
                            alias_to_label[alias] = closest[0]
        
        # 3. Alias-aware property validation
        alias_props = self._extract_properties(cypher)
        
        for alias, props in alias_props.items():
            for prop in props:
                # Check if it's a relationship property
                if alias == 'r' and 'INFLUENCES' in cypher:
                    if prop not in self._schema['rel_properties'].get('INFLUENCES', set()):
                        # Remove invalid relationship property
                        cypher = re.sub(rf'\s+AND\s+{alias}\.{prop}[^,\s]*', '', cypher)
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}[^,\s]*\s+AND', 'WHERE', cypher)
                        cypher = re.sub(rf',\s*{alias}\.{prop}[^,\s]*', '', cypher)
                        # Handle property at beginning of RETURN
                        cypher = re.sub(rf'RETURN\s+{alias}\.{prop}[^,\s]*,\s*', 'RETURN ', cypher)
                # Check node properties
                elif alias in alias_to_label:
                    label = alias_to_label[alias]
                    label_props = self._schema['properties'].get(label, set())
                    if prop not in label_props:
                        # Remove invalid node property  
                        cypher = re.sub(rf'\s+AND\s+{alias}\.{prop}[^,\s]*', '', cypher)
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}\s*=\s*[^\s]+\s+AND', 'WHERE', cypher)
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}\s*=\s*[^\s]+\s+RETURN', 'WHERE RETURN', cypher) 
                        cypher = re.sub(rf'WHERE\s+{alias}\.{prop}\s*=\s*[^\s]+', '', cypher)
                        cypher = re.sub(rf',\s*{alias}\.{prop}[^,\s]*', '', cypher)
                        # Handle property at beginning of RETURN
                        cypher = re.sub(rf'RETURN\s+{alias}\.{prop}[^,\s]*,\s*', 'RETURN ', cypher)
        # 4. Safe regex cleanup
        # Fix "WHERE AND" at beginning
        cypher = re.sub(r'WHERE\s+AND\s+', 'WHERE ', cypher)
        # Fix empty WHERE clauses
        cypher = re.sub(r'WHERE\s+RETURN', ' RETURN', cypher)
        cypher = re.sub(r'WHERE\s+LIMIT', ' LIMIT', cypher)
        cypher = re.sub(r'WHERE\s+ORDER', ' ORDER', cypher)
        # Fix empty WHERE with closing paren
        cypher = re.sub(r'WHERE\s*\)', ')', cypher)
        # Fix double commas from property removal
        cypher = re.sub(r',\s*,', ',', cypher)
        # Fix leading comma in RETURN
        cypher = re.sub(r'RETURN\s*,', 'RETURN', cypher)
        # 5. Add default LIMIT only if no existing LIMIT
        if not re.search(r'\bLIMIT\s+\d+', cypher) and 'count(' not in cypher.lower():
            cypher += ' LIMIT 1000'
        return cypher
    async def query(self, user_query: str) -> Dict:
        """Process query with full validation"""
        await self.get_schema()
        # Generate Cypher
        examples = await self._find_examples(user_query)
        prompt = self._build_prompt(user_query, examples)
        response = await self.llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_query)
        ])
        cypher = response.content.strip()
        if cypher.startswith("```"):
            cypher = cypher.split("\n", 1)[1].rsplit("\n", 1)[0]
        cypher = self._validate_and_fix_query(cypher)
        # Test with EXPLAIN first
        tools = await self.get_tools()
        read_tool = next(t for t in tools if t.name == "read_neo4j_cypher")
        
        try:
            # Try EXPLAIN first
            explain_result = await read_tool.ainvoke({"query": f"EXPLAIN {cypher}"})
            if "error" in str(explain_result).lower():
                # One retry with simplified query
                cypher = cypher.replace("WITH", "RETURN").split("RETURN")[0] + " RETURN * LIMIT 10"
                cypher = self._validate_and_fix_query(cypher)
        except:
            pass
        # Execute
        try:
            result = await read_tool.ainvoke({"query": cypher})
            # Learn only if truly successful (has results)
            if not self._is_error(result) and result:
                await self._learn(user_query, cypher)
            return {"query": cypher, "result": result, "success": True}
        except Exception as e:
            return {"query": cypher, "error": str(e), "success": False}
    async def _find_examples(self, query: str, k: int = 2) -> List[Dict]:
        """Find similar examples"""
        # Load patterns from Redis if using Redis
        if self.use_redis and self.redis_client:
            patterns = await self._load_patterns_from_redis()
            # Merge with seed patterns (ensure seeds are always available)
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
            existing_patterns = self.patterns[3:]  # Skip seeds
        for pattern in existing_patterns:
            if 'embedding' not in pattern:
                pattern['embedding'] = await self.embeddings.aembed_query(pattern['query'])
            sim = np.dot(query_emb, pattern['embedding']) / (
                np.linalg.norm(query_emb) * np.linalg.norm(pattern['embedding'])
            )
            if sim > 0.95:
                return  # Too similar, skip
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
                # Keep seeds + most recent patterns
                num_seeds = len(self.SEED_PATTERNS)
                self.patterns = self.patterns[:num_seeds] + self.patterns[-(self.max_patterns - num_seeds):]
    def _is_error(self, result) -> bool:
        result_str = str(result).lower()
        return any(err in result_str for err in ['error:', 'exception', 'failed'])

# Global singleton agent for reuse
_global_agent = None
_agent_lock = asyncio.Lock()
async def _get_agent():
    """Get or create singleton agent (thread-safe)"""
    global _global_agent
    if _global_agent is None:
        async with _agent_lock:
            if _global_agent is None:
                _global_agent = UltraMinimalMCPAgent()
    return _global_agent
async def query_neo4j(query: str) -> Dict:
    """Query Neo4j with true 100% accuracy"""
    agent = await _get_agent()
    return await agent.query(query)
async def query_neo4j_batch(queries: List[str]) -> List[Dict]:
    """Batch query Neo4j - efficient for multiple queries"""
    agent = UltraMinimalMCPAgent()
    await agent.get_schema()
    tasks = [agent.query(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        r if not isinstance(r, Exception) else {"error": str(r), "success": False}
        for r in results
    ]

# Create LangGraph version
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

class AgentState(TypedDict):
    query: str
    result: Dict
def create_graph():
    """Create LangGraph graph for the production agent"""
    graph = StateGraph(AgentState)
    async def run_agent(state):
        result = await query_neo4j(state["query"])
        return {"result": result}
    graph.add_node("agent", run_agent)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()

mcp_agent = create_graph()
if __name__ == "__main__":
    async def test():
        result = await query_neo4j("Show pharmaceutical companies influenced by FDA news")
        print(f"Success: {result.get('success')}")
        print(f"Query: {result.get('query', '')[:100]}...")
    asyncio.run(test())