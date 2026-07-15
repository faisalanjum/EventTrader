"""MCP Agent Final - Tiered models with proper Redis integration"""
import json
import numpy as np
import re
from typing import List, Dict, Optional
import asyncio
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

logger = logging.getLogger(__name__)

# Constants
MAX_STEPS = 50  # Increased for complex queries
ESCALATION_THRESHOLD = 5  # Switch to Claude after 5 failures
MAX_RESULT_LENGTH = 5000  # Maximum characters to return to LLM
MAX_RESULT_ROWS = 50  # Maximum rows to return


class MinimalTieredAgent:
    """Minimal agent with tiered model escalation and result limiting"""
    
    SEED_PATTERNS = [
        # Basic patterns
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
        # Date patterns
        {
            "query": "Find recent 10-Q reports",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' AND datetime(r.created) > datetime() - duration('P60D') RETURN c.ticker, r.created ORDER BY r.created DESC LIMIT 20"
        },
        {
            "query": "Find companies that filed 10-K in the last 90 days",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-K' AND datetime(r.created) > datetime() - duration('P90D') RETURN c.ticker, r.created, r.formType ORDER BY r.created DESC LIMIT 20"
        },
        # Comparison patterns
        {
            "query": "Find news that drove stock down more than market",
            "cypher": "MATCH (n:News)-[rel:INFLUENCES]->(c:Company) WHERE rel.daily_stock < rel.daily_macro - 2.0 RETURN n.title, c.ticker, rel.daily_stock, rel.daily_macro ORDER BY rel.daily_stock LIMIT 20"
        },
        {
            "query": "Find companies outperforming SPY by 3%",
            "cypher": "MATCH (n:News)-[rel:INFLUENCES]->(c:Company) WHERE rel.daily_stock > rel.daily_macro + 3.0 RETURN n.title, c.ticker, rel.daily_stock, rel.daily_macro, rel.daily_stock - rel.daily_macro as excess_return ORDER BY excess_return DESC LIMIT 20"
        },
        # Date matching patterns
        {
            "query": "Find news on same day as report",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date RETURN c.ticker, n.title, report_date LIMIT 20"
        },
        {
            "query": "Find companies with news affecting returns on report filing date",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date AND rel.daily_stock IS NOT NULL RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, report_date ORDER BY rel.daily_stock LIMIT 20"
        },
        # Fact patterns
        {
            "query": "Get NetIncomeLoss from company reports",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' AND f.is_numeric = 'true' RETURN c.ticker, f.value, r.created ORDER BY r.created DESC LIMIT 20"
        },
        {
            "query": "Get revenue facts from 10-K reports",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE r.formType = '10-K' AND con.qname CONTAINS 'Revenue' AND f.is_numeric = 'true' RETURN c.ticker, con.qname, f.value, r.created ORDER BY r.created DESC LIMIT 20"
        },
        # Complex multi-condition
        {
            "query": "Find 10-Q filings where same-day news drove returns below market",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date AND rel.daily_stock < rel.daily_macro RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, r.formType ORDER BY rel.daily_stock LIMIT 20"
        },
        # Complex with fact retrieval - FIXED SYNTAX
        {
            "query": "Find companies with 10-Q filings, same-day news impact, and get their NetIncomeLoss",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' AND datetime(r.created) > datetime() - duration('P60D') WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date AND rel.daily_stock < rel.daily_macro - 4.0 WITH c, n, r, rel OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' AND f.is_numeric = 'true' RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, r.formType, f.value as NetIncomeLoss LIMIT 10"
        },
        # Another complex pattern with proper joins
        {
            "query": "Find 10-Q filings in last 60 days with same-day negative news impact and NetIncomeLoss",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' AND datetime(r.created) > datetime() - duration('P60D') WITH c, r MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = date(datetime(r.created)) AND rel.daily_stock < rel.daily_macro - 4.0 OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, r.formType, f.value as NetIncomeLoss ORDER BY rel.daily_stock LIMIT 10"
        }
    ]
    
    def __init__(self, use_redis: bool = True):
        self.patterns = self.SEED_PATTERNS.copy()
        self.use_redis = use_redis
        self.redis_client = None
        self.redis_key = "admin:neo4j_patterns"  # Original namespace
        self.max_patterns = 500  # Increased from 50
        
        # Initialize Redis with proper pattern loading
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=31379,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2
                )
                # Quick ping with timeout
                self.redis_client.ping()
                logger.info("Connected to Redis for pattern storage")
                
                # Load existing patterns count
                pattern_count = self.redis_client.llen(self.redis_key)
                logger.info(f"Found {pattern_count} patterns in Redis")
                
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory: {e}")
                self.redis_client = None
                self.use_redis = False
        
        # Tiered models
        self.tier1_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=2048,  # Increased from 256
            api_key=keys.OPENAI_API_KEY
        )
        self.tier2_llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0,
            max_tokens=2048,
            api_key=keys.ANTHROPIC_API_KEY
        )
        self.current_tier = 1
        
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
        self._tools = None
    
    async def get_tools(self):
        if self._tools is None:
            self._tools = await self.mcp_client.get_tools()
        return self._tools
    
    def _limit_results(self, result: str) -> tuple[str, bool]:
        """Limit results to avoid overwhelming LLM and reduce costs"""
        if not result or result == '[]':
            return result, False
        
        # Try to parse as JSON array
        try:
            data = json.loads(result)
            if isinstance(data, list):
                original_count = len(data)
                
                # Limit number of rows
                if original_count > MAX_RESULT_ROWS:
                    data = data[:MAX_RESULT_ROWS]
                    limited_result = json.dumps(data, indent=2)
                    
                    # Add truncation notice
                    truncation_msg = f"\n\n[TRUNCATED: Showing {MAX_RESULT_ROWS} of {original_count} results]"
                    return limited_result + truncation_msg, True
                
                # Check character length
                result_str = json.dumps(data, indent=2)
                if len(result_str) > MAX_RESULT_LENGTH:
                    # Progressively reduce rows until under limit
                    while len(result_str) > MAX_RESULT_LENGTH and len(data) > 1:
                        data = data[:len(data)-1]
                        result_str = json.dumps(data, indent=2)
                    
                    truncation_msg = f"\n\n[TRUNCATED: Showing {len(data)} of {original_count} results due to size limit]"
                    return result_str + truncation_msg, True
                
                return result, False
            
        except json.JSONDecodeError:
            # Not JSON, just truncate by characters
            if len(result) > MAX_RESULT_LENGTH:
                return result[:MAX_RESULT_LENGTH] + "\n\n[TRUNCATED: Result too large]", True
        
        return result, False
    
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
            
            # Add to Redis list (at the beginning like original)
            self.redis_client.lpush(self.redis_key, json.dumps(pattern_copy))
            
            # Trim to max size (keep only the most recent patterns)
            self.redis_client.ltrim(self.redis_key, 0, self.max_patterns - 1)
            
        except Exception as e:
            logger.warning(f"Failed to save pattern to Redis: {e}")
    
    def _validate_and_fix_query(self, cypher: str) -> str:
        """Minimal validation - only fix known issues"""
        # Fix the NaN syntax error
        cypher = re.sub(
            r"(\w+\.\w+)\s+IS\s+NOT\s+NULL\s+<>\s*'NaN'",
            r"\1 IS NOT NULL AND \1 <> 'NaN'",
            cypher
        )
        
        # Fix nested MATCH-RETURN syntax error
        # Replace (MATCH ... RETURN ...) with OPTIONAL MATCH
        nested_match_pattern = r'\(\s*MATCH\s+.*?\s+RETURN\s+.*?\)\s*AS\s+\w+'
        if re.search(nested_match_pattern, cypher, re.DOTALL):
            logger.warning("Detected invalid nested MATCH-RETURN, will regenerate")
            # Return None to force regeneration
            return None
        
        # Add LIMIT if missing (but respect existing limits)
        if not re.search(r'\bLIMIT\s+\d+', cypher) and 'count(' not in cypher.lower():
            cypher += ' LIMIT 100'  # Default limit for safety
        
        return cypher
    
    async def query_generate(self, user_query: str, errors: List[str] = None) -> str:
        """Generate Cypher with model escalation"""
        # Escalate to tier 2 after threshold failures
        if errors and len(errors) >= ESCALATION_THRESHOLD and self.current_tier == 1:
            self.current_tier = 2
            logger.info("Escalating to Claude-3.5-Sonnet for complex query")
        
        # Select model based on tier
        llm = self.tier1_llm if self.current_tier == 1 else self.tier2_llm
        model_name = "GPT-4o-mini" if self.current_tier == 1 else "Claude-3.5-Sonnet"
        logger.info(f"Using {model_name} for generation")
        
        # Find similar examples
        examples = await self._find_examples(user_query)
        prompt = self._build_prompt(user_query, examples)
        
        # Add error feedback if provided
        if errors:
            prompt += "\n\nPrevious attempts failed with these errors:"
            for i, err in enumerate(errors[-3:], 1):  # Last 3 errors
                # Limit error length to avoid token overflow
                err_msg = err[:500] if len(err) > 500 else err
                prompt += f"\n{i}. {err_msg}"
        
        response = await llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_query)
        ])
        
        cypher = response.content.strip()
        
        # Extract cypher from code blocks
        if "```" in cypher:
            # Find content between ```cypher or ```sql or just ```
            import re
            match = re.search(r'```(?:cypher|sql)?\s*\n(.*?)\n```', cypher, re.DOTALL)
            if match:
                cypher = match.group(1).strip()
        
        # Remove any "Cypher:" prefix if the model includes it
        if cypher.lower().startswith("cypher:"):
            cypher = cypher[7:].strip()
        
        # If the response contains explanatory text, try to extract just the query
        if "MATCH" in cypher and ("\n\n" in cypher or "Let me" in cypher):
            # Find the MATCH statement and everything after it
            match_pos = cypher.find("MATCH")
            if match_pos > 0:
                cypher = cypher[match_pos:]
                # Remove any trailing explanations
                if "\n\n" in cypher:
                    cypher = cypher.split("\n\n")[0]
        
        validated_cypher = self._validate_and_fix_query(cypher)
        if validated_cypher is None:
            # Invalid syntax detected, add to errors and regenerate
            if errors is None:
                errors = []
            errors.append("Generated query contains invalid nested MATCH-RETURN syntax")
            return await self.query_generate(user_query, errors)
        
        return validated_cypher
    
    async def query_execute(self, cypher: str) -> Dict:
        """Execute Cypher query and limit results"""
        tools = await self.get_tools()
        read_tool = next(t for t in tools if t.name == "read_neo4j_cypher")
        
        try:
            result = await read_tool.ainvoke({"query": cypher})
            
            # Limit results to avoid overwhelming the LLM
            limited_result, was_truncated = self._limit_results(result)
            
            return {
                "result": limited_result, 
                "cypher": cypher,
                "truncated": was_truncated
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _find_examples(self, query: str, k: int = 3) -> List[Dict]:
        """Find similar examples from Redis + seeds"""
        # Load patterns from Redis if using Redis
        if self.use_redis and self.redis_client:
            patterns = await self._load_patterns_from_redis()
            # Merge with seed patterns to ensure seeds are always available
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
            if sim > 0.5:  # Same threshold as original
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
            "\nCRITICAL RULES:",
            "1. For NULL/NaN checks, use: WHERE r.property IS NOT NULL AND r.property <> 'NaN'",
            "2. For date filtering, use: datetime(r.created) > datetime() - duration('P60D')",
            "3. For date matching, use: date(datetime(n.created)) = date(datetime(r.created))",
            "4. INFLUENCES properties (daily_stock, daily_macro) are floats - compare directly",
            "5. For facts, traverse: Report -[:HAS_XBRL]-> XBRLNode <-[:REPORTS]- Fact",
            "6. Always include LIMIT clause to control result size",
            "7. NEVER use nested MATCH-RETURN inside a RETURN clause - use OPTIONAL MATCH or WITH",
            "8. For complex joins, use WITH to pass data between query parts",
            "\nGenerate Cypher query following the EXACT patterns from examples."
        ])
        
        return "\n".join(prompt)
    
    async def _learn(self, query: str, cypher: str, result_count: int = 0):
        """Learn from successful queries - saves to Redis"""
        # Only learn if we got meaningful results
        if result_count == 0:
            logger.info("Skipping learning - query returned no results")
            return
        
        query_emb = await self.embeddings.aembed_query(query)
        
        # Load existing patterns from Redis
        if self.use_redis and self.redis_client:
            existing_patterns = await self._load_patterns_from_redis()
        else:
            existing_patterns = self.patterns[len(self.SEED_PATTERNS):]  # Skip seeds
        
        # Check for duplicates with same threshold as original (0.95)
        for pattern in existing_patterns:
            if 'embedding' not in pattern:
                pattern['embedding'] = await self.embeddings.aembed_query(pattern['query'])
            
            sim = np.dot(query_emb, pattern['embedding']) / (
                np.linalg.norm(query_emb) * np.linalg.norm(pattern['embedding'])
            )
            if sim > 0.95:
                logger.info("Skipping learning - too similar to existing pattern")
                return  # Too similar, skip
        
        new_pattern = {
            "query": query,
            "cypher": cypher,
            "embedding": query_emb,
            "result_count": result_count  # Track how many results it returned
        }
        
        if self.use_redis and self.redis_client:
            await self._save_pattern_to_redis(new_pattern)
            logger.info(f"Saved new pattern to Redis with {result_count} results")
        else:
            self.patterns.append(new_pattern)
            if len(self.patterns) > self.max_patterns:
                # Keep seeds + most recent patterns
                num_seeds = len(self.SEED_PATTERNS)
                self.patterns = self.patterns[:num_seeds] + self.patterns[-(self.max_patterns - num_seeds):]
            logger.info(f"Learned new pattern with {result_count} results (in-memory)")
    
    def reset_tier(self):
        """Reset to cheaper model after success"""
        if self.current_tier != 1:
            logger.info("Resetting to GPT-4o-mini after success")
            self.current_tier = 1
    
    def _is_error(self, result) -> bool:
        """Check if result contains an error"""
        result_str = str(result).lower()
        return any(err in result_str for err in ['error:', 'exception', 'failed'])


# Simple direct implementation without LangGraph
async def query_neo4j_simple(query: str) -> Dict:
    """Simple query implementation without LangGraph"""
    agent = MinimalTieredAgent()  # Uses Redis by default
    
    errors = []
    for attempt in range(MAX_STEPS):
        try:
            # Generate query
            cypher = await agent.query_generate(query, errors if errors else None)
            logger.info(f"Attempt {attempt + 1} - Generated: {cypher[:100]}...")
            
            # Execute query
            result = await agent.query_execute(cypher)
            
            # Check result
            if "error" in result:
                errors.append(result["error"])
                continue
            
            raw_result = result.get("result", "")
            if raw_result == '[]' or not raw_result:
                errors.append("Query returned no results")
                continue
            
            # Check for Neo4j errors in result
            if isinstance(raw_result, str):
                neo4j_error_patterns = [
                    "Neo.ClientError", "Neo.DatabaseError", 
                    "Invalid input", "Unknown function",
                    "Variable .* not defined", "Type mismatch",
                    "Syntax error", "Expected"
                ]
                
                error_found = False
                for pattern in neo4j_error_patterns:
                    if re.search(pattern, raw_result, re.IGNORECASE):
                        error_msg = raw_result
                        if "message:" in error_msg:
                            error_msg = error_msg.split("message:")[1].strip()
                        errors.append(error_msg[:500])
                        error_found = True
                        break
                
                if error_found:
                    continue
            
            # Success! Count results and learn
            try:
                parsed = json.loads(raw_result.split('\n\n[TRUNCATED')[0])
                result_count = len(parsed) if isinstance(parsed, list) else 1
            except:
                result_count = 1
            
            # Learn only on success (like original)
            if not agent._is_error(raw_result) and result_count > 0:
                await agent._learn(query, cypher, result_count)
            
            agent.reset_tier()
            
            return {
                "query": cypher,
                "result": raw_result,
                "success": True,
                "attempts": attempt + 1,
                "model_used": "Claude-3.5-Sonnet" if agent.current_tier == 2 else "GPT-4o-mini",
                "was_truncated": result.get("truncated", False)
            }
            
        except Exception as e:
            errors.append(str(e))
    
    # Failed after all attempts
    return {
        "error": "All attempts failed",
        "last_errors": errors[-2:],
        "success": False,
        "attempts": len(errors),
        "model_used": "Claude-3.5-Sonnet" if agent.current_tier == 2 else "GPT-4o-mini"
    }


# Export the simple version as the main function
query_neo4j = query_neo4j_simple


if __name__ == "__main__":
    async def test():
        # Test with complex query
        complex_query = """Find the 10 companies that filed a 10-Q in the last 60 days 
        where a same-day news item drove the company's daily_stock return 
        at least 4% below the SPY's daily_macro return, and return the 
        news headline, ticker, daily_stock, daily_macro, report formType, 
        and that report's latest NetIncomeLoss fact value."""
        
        print("Testing with complex query...")
        result = await query_neo4j(complex_query)
        print(f"Success: {result.get('success')} (Attempts: {result.get('attempts', 0)})")
        print(f"Model used: {result.get('model_used')}")
        print(f"Results truncated: {result.get('was_truncated', False)}")
        
        if result.get('success'):
            print(f"Query: {result.get('query', '')[:200]}...")
            print(f"Results: {result.get('result', '')[:500]}...")
        else:
            print(f"Errors: {result.get('last_errors', [])}")
    
    asyncio.run(test())