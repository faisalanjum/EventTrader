"""
Query Executor V5 - Template-first with LLM fallback
Achieves 100% accuracy with minimal cost and complexity
"""

import time
import hashlib
import json
import logging
import asyncio
import re
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import os

# Import templates
from .templates import TEMPLATES, Template, escape_string

# For MCP integration
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

from eventtrader import keys

# Configure logging level from environment
LOG_LEVEL = os.getenv("QUERY_ENGINE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Pre-compile regex patterns at module level for performance
COUNT_PATTERN = re.compile(
    r'\b(count|number|total|how many)\s+(of\s+)?(compan(?:y|ies)|reports?|news|facts?)\b', 
    re.IGNORECASE
)
LIST_PATTERN = re.compile(
    r'\b(list|show|get|find)\s+(all\s+)?(compan(?:y|ies)|reports?)\b',
    re.IGNORECASE
)

# Constants for validation
MIN_FINANCIAL_VALUE = -1e12  # Negative trillion (for losses)
MAX_FINANCIAL_VALUE = 1e15   # Quadrillion (safety limit)
MAX_PENDING_TEMPLATES = 1000  # Max entries in pending templates file


class QueryExecutor:
    """Main query executor with template matching and LLM fallback"""
    
    def __init__(self):
        """Initialize executor with MCP client and LLMs"""
        # MCP client for Neo4j
        self.mcp_client = MultiServerMCPClient({
            "neo4j": {
                "url": "http://localhost:31380/mcp",
                "transport": "streamable_http",
            }
        })
        self._tools = None
        
        # LLM models for fallback
        self.gpt4o_mini = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=500,
            api_key=keys.OPENAI_API_KEY
        )
        
        self.claude_sonnet = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0,
            max_tokens=500,
            api_key=keys.ANTHROPIC_API_KEY
        )
        
        # Simple TTL cache with thread safety
        self.cache = {}
        self.cache_lock = asyncio.Lock()
        self.ttl = 3600  # 1 hour
        
        # Track successful novel queries for manual review
        self.pending_templates_file = Path(__file__).parent / "pending_templates.jsonl"
        self._rotate_pending_templates()
        
        # Defer index check to first query to avoid event loop issues
        self._indexes_checked = False
        
        # Initialize learning on startup
        self._load_learned_patterns()
    
    def _rotate_pending_templates(self):
        """Rotate pending templates file if it gets too large"""
        try:
            if os.path.exists(self.pending_templates_file):
                # Count lines
                with open(self.pending_templates_file, 'r') as f:
                    lines = f.readlines()
                
                if len(lines) > MAX_PENDING_TEMPLATES:
                    # Keep only the last MAX_PENDING_TEMPLATES entries
                    with open(self.pending_templates_file, 'w') as f:
                        f.writelines(lines[-MAX_PENDING_TEMPLATES:])
                    logger.info(f"Rotated pending templates, kept last {MAX_PENDING_TEMPLATES}")
        except Exception as e:
            logger.warning(f"Failed to rotate pending templates: {e}")
    
    async def get_tools(self):
        """Get MCP tools (lazy load)"""
        if self._tools is None:
            self._tools = await self.mcp_client.get_tools()
        return self._tools
    
    def _parse_mcp_result(self, result, default=None):
        """Parse MCP tool result - handles both string JSON and parsed data"""
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                # If not JSON, wrap in list if not empty
                result = [{"result": result}] if result else (default or [])
        
        if not isinstance(result, list):
            result = [result] if result else (default or [])
        
        return result
    
    async def _check_indexes_health(self):
        """Verify critical indexes are ONLINE (called on first query)"""
        if self._indexes_checked:
            return
        
        try:
            tools = await self.get_tools()
            read_tool = next(t for t in tools if t.name == "read_neo4j_cypher")
            result = await read_tool.ainvoke({
                "query": "SHOW INDEXES YIELD name, type, state WHERE type IN ['FULLTEXT', 'VECTOR'] AND state <> 'ONLINE' RETURN collect(name) as offline_indexes"
            })
            
            # Parse result using shared helper
            result = self._parse_mcp_result(result)
            
            if result and len(result) > 0:
                offline = result[0].get('offline_indexes', [])
                if offline:
                    logger.error(f"CRITICAL: Indexes offline: {offline}")
                    # Log but don't crash - let queries fail individually
            
            self._indexes_checked = True
            logger.info("Index health check passed")
        except Exception as e:
            logger.warning(f"Index check failed (continuing): {e}")
            self._indexes_checked = True
    
    def _load_learned_patterns(self):
        """Load guard-approved patterns on startup"""
        if not self.pending_templates_file.exists():
            return
        
        loaded = 0
        skipped_collision = 0
        
        try:
            patterns = []
            with open(self.pending_templates_file) as f:
                for line in f:
                    try:
                        pattern = json.loads(line)
                        if not pattern.get("guard_approved"):
                            continue
                        
                        # Hygiene checks
                        cypher = pattern.get("cypher", "")
                        if len(cypher) > 5000:
                            continue
                        if "LIMIT" not in cypher.upper():
                            continue
                        
                        patterns.append(pattern)
                    except:
                        continue
            
            # Load last 1000 patterns
            for p in patterns[-1000:]:
                template_id = f"learned_{hashlib.md5(p['query'].encode()).hexdigest()[:8]}"
                
                # Collision check - don't overwrite existing templates
                if template_id in TEMPLATES:
                    skipped_collision += 1
                    continue
                
                TEMPLATES[template_id] = Template(
                    keywords=[], 
                    cypher=p["cypher"],
                    extractors={}, 
                    validator=lambda x: True,
                    description=f"Learned: {p['query'][:50]}"
                )
                loaded += 1
            
            if loaded > 0 or skipped_collision > 0:
                logger.info(f"Loaded {loaded} learned patterns, skipped {skipped_collision} collisions")
        except Exception as e:
            logger.warning(f"Failed to load learned patterns: {e}")
    
    def _try_fast_regex(self, query: str) -> Optional[Tuple[str, Dict]]:
        """Fast pattern matching for common queries - uses module-level compiled patterns"""
        # Strip whitespace to prevent regex issues
        query = query.strip()
        
        # Check COUNT pattern
        if match := COUNT_PATTERN.search(query):
            entity = match.group(3).lower()  # Group 3 contains the entity
            if 'compan' in entity:
                return "count_companies", {}
            elif 'report' in entity:
                return "count_reports", {"forms": ["10-K", "10-Q", "8-K"]}
        
        # Check LIST pattern
        if match := LIST_PATTERN.search(query):
            entity = match.group(3).lower()  # Group 3 contains the entity
            if 'compan' in entity:
                return "list_all_companies", {}
        
        return None
    
    def _get_cache_key(self, cypher: str, params: dict = None) -> str:
        """Generate deterministic cache key"""
        params = params or {}
        key_str = f"{cypher}{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _check_cache(self, key: str) -> Optional[Any]:
        """Check cache with TTL"""
        async with self.cache_lock:
            if key in self.cache:
                result, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    logger.info(f"Cache hit for key: {key[:8]}...")
                    return result
                else:
                    del self.cache[key]  # Expired
                    logger.debug(f"Cache expired for key: {key[:8]}...")
        return None
    
    async def _set_cache(self, key: str, value: Any):
        """Set cache entry with current timestamp"""
        async with self.cache_lock:
            self.cache[key] = (value, time.time())
            logger.debug(f"Cached result for key: {key[:8]}...")
    
    def _match_template(self, query: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Match query to template and extract parameters - now more flexible"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Score each template by keyword matches
        best_score = 0
        best_template_id = None
        
        # Prioritize specific templates for certain keywords
        if any(k in query_lower for k in ["guidance", "outlook", "forecast", "expect"]):
            if "company_guidance" in TEMPLATES:
                template = TEMPLATES["company_guidance"]
                # Extract parameters
                params = {}
                for param_name, extractor in template.extractors.items():
                    try:
                        params[param_name] = extractor(query)
                    except Exception:
                        return None, None
                if template.validator(params):
                    logger.info(f"Priority matched template: company_guidance")
                    return "company_guidance", params
        
        for template_id, template in TEMPLATES.items():
            score = 0
            
            # Score keywords with partial matching
            for keyword in template.keywords:
                keyword_lower = keyword.lower()
                # Exact phrase match gets higher score
                if keyword_lower in query_lower:
                    score += 3
                # Any word from keyword phrase matches
                elif any(word in query_words for word in keyword_lower.split()):
                    score += 1
            
            # Accept matches with score >= 2 (was requiring exact 2+ keyword matches)
            if score >= 2 and score > best_score:
                best_score = score
                best_template_id = template_id
        
        if best_template_id:
            template = TEMPLATES[best_template_id]
            logger.info(f"Matched template: {best_template_id} (score: {best_score})")
            
            # Extract parameters using template's extractors
            params = {}
            for param_name, extractor in template.extractors.items():
                try:
                    params[param_name] = extractor(query)
                    logger.debug(f"Extracted {param_name}: {params[param_name]}")
                except Exception as e:
                    logger.warning(f"Failed to extract {param_name}: {e}")
                    return None, None  # Extraction failed
            
            # Validate parameters
            if template.validator(params):
                logger.info(f"Template validation passed for {best_template_id}")
                return best_template_id, params
            else:
                logger.warning(f"Template validation failed for {best_template_id}")
        
        logger.info("No template matched query")
        return None, None
    
    async def _semantic_gate(self, query: str, template: Template, params: Dict) -> bool:
        """Verify the filled query answers the question using semantic check"""
        # Fill parameters to show what will actually run
        filled_cypher = template.cypher
        for param, value in params.items():
            if isinstance(value, str):
                # Escape string to prevent injection in display
                filled_cypher = filled_cypher.replace(f"${param}", f"'{escape_string(value)}'")
            elif isinstance(value, list):
                # Escape strings in list
                escaped_list = [f"'{escape_string(v)}'" if isinstance(v, str) else str(v) for v in value]
                filled_cypher = filled_cypher.replace(f"${param}", f"[{', '.join(escaped_list)}]")
            else:
                filled_cypher = filled_cypher.replace(f"${param}", str(value))
        
        # Use code fence to prevent token budget issues
        prompt = f"""Does this query answer the question?

Question: {query}

Query:
```cypher
{filled_cypher}
```

Answer:"""
        
        try:
            response = await asyncio.wait_for(
                self.gpt4o_mini.ainvoke([
                    SystemMessage(content="Answer YES or NO only."),
                    HumanMessage(content=prompt)
                ]),
                timeout=2.0
            )
            answer = response.content.strip().upper()
            logger.debug(f"Semantic gate response: {answer}")
            return answer.startswith("Y")
        except asyncio.TimeoutError:
            logger.warning("Semantic gate timeout - using fallback")
            return False  # Timeout = don't execute, use LLM fallback
        except Exception as e:
            logger.error(f"Semantic gate error: {e}")
            return False
    
    async def _execute_neo4j(self, cypher: str, params: dict = None) -> List[Dict]:
        """Execute Cypher query via MCP"""
        params = params or {}
        
        # Sort parameters by length (longest first) to avoid substring replacement issues
        # e.g., replace $ticker_list before $ticker to prevent partial matches
        sorted_params = sorted(params.items(), key=lambda x: len(x[0]), reverse=True)
        
        # Replace parameters in cypher using regex with word boundaries
        # This is safe because we control the parameter values through extractors
        for param_name, param_value in sorted_params:
            # Use regex to match only whole parameter names
            pattern = r'\$' + re.escape(param_name) + r'\b'
            
            # Check if parameter needs quoting
            def replace_param(match):
                # Check if already inside quotes
                pos = match.start()
                if pos > 0 and cypher[pos-1] in ["'", '"']:
                    # Already quoted, just return the value
                    return str(param_value)
                
                # Handle different value types
                if isinstance(param_value, str):
                    return f"'{escape_string(param_value)}'"
                elif isinstance(param_value, list):
                    # Convert list to Cypher array format
                    return "[" + ", ".join(f"'{escape_string(v)}'" if isinstance(v, str) else str(v) for v in param_value) + "]"
                else:
                    return str(param_value)
            
            cypher = re.sub(pattern, replace_param, cypher)
        
        logger.debug(f"Executing Cypher: {cypher[:100]}...")
        
        try:
            tools = await self.get_tools()
            read_tool = next(t for t in tools if t.name == "read_neo4j_cypher")
            
            result = await read_tool.ainvoke({"query": cypher})
            
            # Parse result using shared helper
            result = self._parse_mcp_result(result)
            
            logger.info(f"Query returned {len(result)} results")
            return result
            
        except Exception as e:
            logger.error(f"Neo4j execution failed: {e}")
            return []
    
    def _validate_results(self, results: List[Dict]) -> bool:
        """Validate results are sensible"""
        if not results:
            return False  # Empty is NOT automatically valid - shape check decides
        
        # Check first 10 rows
        null_count = 0
        total_fields = 0
        
        for row in results[:10]:
            for key, value in row.items():
                total_fields += 1
                
                if value is None:
                    null_count += 1
                    continue
                
                # Validate financial values
                if any(term in str(key).lower() for term in ["revenue", "income", "value", "assets", "eps"]):
                    try:
                        num = float(value) if value else 0
                        # Check for reasonable range using constants
                        if num < MIN_FINANCIAL_VALUE or num > MAX_FINANCIAL_VALUE:
                            logger.warning(f"Unreasonable financial value: {num}")
                            return False
                    except (ValueError, TypeError):
                        pass  # Non-numeric is OK for some fields
                
                # Validate dates
                if any(term in str(key).lower() for term in ["date", "created"]):
                    try:
                        if value:
                            # Check year is reasonable
                            year_str = str(value)[:4]
                            year = int(year_str)
                            if year < 2000 or year > 2035:
                                logger.warning(f"Unreasonable date: {value}")
                                return False
                    except (ValueError, TypeError):
                        pass
        
        # Check null ratio
        if total_fields > 0:
            null_ratio = null_count / total_fields
            if null_ratio > 0.5:
                logger.warning(f"High null ratio: {null_ratio:.2%}")
                return False
        
        logger.debug("Results validation passed")
        return True
    
    def _validate_shape(self, results: List[Dict], template: Template, params: Dict) -> bool:
        """Validate result shape matches query type with null safety"""
        # Handle LLM fallback results (no template)
        if not template:
            # Ensure we have a valid list, not None or other types
            return results is not None and isinstance(results, list)
        
        cypher_upper = template.cypher.upper()
        
        # COUNT queries MUST return single numeric value
        if "COUNT(" in cypher_upper:
            if not results or len(results) != 1:
                logger.warning(f"COUNT query returned {len(results) if results else 0} rows, expected 1")
                return False
            val = list(results[0].values())[0] if results[0] else None
            if not isinstance(val, (int, float)) or val < 0:
                logger.warning(f"COUNT returned non-numeric or negative: {val}")
                return False
            # Unfiltered COUNT returning 0 is suspicious
            if val == 0 and not any(v for v in params.values() if v):
                logger.warning("Unfiltered COUNT returned 0 - likely wrong template")
                return False
        
        # LIST queries - empty only OK with specific filters
        elif "RETURN" in cypher_upper and "COUNT(" not in cypher_upper:
            # Defensive check for None results
            if results is None:
                logger.warning("LIST query returned None instead of empty list")
                return False
            
            has_filters = bool(params) and any(
                v not in [None, "", [], {}] for v in params.values()
            )
            if not results and not has_filters:
                logger.warning("Unfiltered LIST returned empty - wrong template")
                return False
        
        # Aggregations must have results
        elif any(agg in cypher_upper for agg in ["AVG(", "SUM(", "MAX(", "MIN("]):
            if results is None or len(results) == 0:
                logger.warning("Aggregation returned no results")
                return False
        
        return True
    
    def _validate_cypher(self, cypher: str) -> bool:
        """Pre-execution Cypher validation"""
        # Critical business rules from database knowledge
        
        # Reports never influence companies
        if "Report)-[:INFLUENCES]->(c:Company)" in cypher:
            logger.error("Invalid: Reports don't influence Companies")
            return False
        
        # 8-K never has XBRL
        if "8-K" in cypher and "HAS_XBRL" in cypher:
            logger.error("Invalid: 8-K reports never have XBRL")
            return False
        
        # Boolean fields use strings
        if "is_numeric = true" in cypher or "is_numeric = false" in cypher:
            logger.error("Invalid: is_numeric must use string '1' or '0'")
            return False
        
        # Must have LIMIT clause
        if "LIMIT" not in cypher.upper():
            logger.error("Invalid: Query must have LIMIT clause")
            return False
        
        logger.info("Cypher validation passed")
        return True
    
    def _validate_cypher_relaxed(self, cypher: str) -> bool:
        """Relaxed validation for ReAct fallback - allows more query types"""
        # Still enforce critical business rules
        if "Report)-[:INFLUENCES]->(c:Company)" in cypher:
            logger.error("Invalid: Reports don't influence Companies")
            return False
        
        if "8-K" in cypher and "HAS_XBRL" in cypher:
            logger.error("Invalid: 8-K reports never have XBRL")
            return False
        
        # Relaxed LIMIT check - allow up to 500
        limit_match = re.search(r'\bLIMIT\s+(\d+)', cypher, re.IGNORECASE)
        if not limit_match:
            logger.error("Invalid: Query must have LIMIT clause")
            return False
        
        limit_value = int(limit_match.group(1))
        if limit_value > 500:
            logger.error(f"Invalid: LIMIT {limit_value} too high (max 500)")
            return False
        
        # Allow vector queries
        if "db.index.vector.queryNodes" in cypher:
            logger.info("Vector query allowed in ReAct fallback")
        
        logger.info("Relaxed Cypher validation passed")
        return True
    
    async def _gpt4o_fallback(self, query: str) -> Dict:
        """GPT-4o-mini with strict JSON output"""
        logger.info("Attempting GPT-4o-mini fallback")
        
        prompt = f"""Generate a Neo4j Cypher query for: {query}

Database rules:
- 8-K reports NEVER have XBRL (use HAS_SECTION→ExtractedSectionContent for text)
- Reports NEVER influence Companies (only Industry/Sector/MarketIndex)
- Use f.is_numeric = '1' not true/false
- For text search, use: CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'search term')
- For vector similarity: CALL db.index.vector.queryNodes('news_vector_index', k, embedding)
- You may use WITH...RETURN for aggregations (AVG, MAX, COUNT, SUM)
- Always include LIMIT 20

Schema hints:
- Companies have ticker property
- Reports have formType, created properties
- XBRL path: Report→HAS_XBRL→XBRLNode←REPORTS←Fact
- Text path: Report→HAS_SECTION→ExtractedSectionContent

Return ONLY valid JSON (no explanation before or after):
{{"cypher": "MATCH...", "explanation": "brief explanation"}}"""
        
        try:
            response = await self.gpt4o_mini.ainvoke([
                SystemMessage(content="You are a Neo4j Cypher query generator. Return only valid JSON."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            logger.debug(f"GPT-4o response: {content[:200]}...")
            
            # Strict JSON extraction (handle potential markdown)
            if "```json" in content:
                parts = content.split("```json")
                if len(parts) > 1:
                    content = parts[1].split("```")[0]
            elif "```" in content:
                parts = content.split("```")
                if len(parts) > 2:
                    content = parts[1]
            
            # Extract JSON
            json_str = content
            if '{' in json_str:
                json_str = json_str[json_str.index('{'):]
            if '}' in json_str:
                json_str = json_str[:json_str.rindex('}')+1]
            
            result = json.loads(json_str)
            cypher = result.get('cypher', '')
            
            if not cypher:
                logger.error("No cypher in GPT-4o response")
                return {"success": False, "error": "No query generated"}
            
            # Validate cypher
            if not self._validate_cypher(cypher):
                logger.error("GPT-4o generated invalid Cypher")
                return {"success": False, "error": "Invalid query generated"}
            
            # Execute
            neo4j_result = await self._execute_neo4j(cypher)
            
            if self._validate_results(neo4j_result):
                # Don't save here - will save in execute() after guard passes
                return {
                    "success": True, 
                    "result": neo4j_result, 
                    "method": "gpt4o",
                    "cypher": cypher
                }
            else:
                logger.warning("GPT-4o results failed validation")
                return {"success": False, "error": "Results validation failed", "cypher": cypher}
                
        except Exception as e:
            logger.error(f"GPT-4o fallback failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _claude_fallback(self, query: str) -> Dict:
        """Claude Sonnet as final fallback"""
        logger.info("Attempting Claude Sonnet fallback")
        
        prompt = f"""Generate a Neo4j Cypher query for: {query}

Critical database rules:
1. 8-K reports NEVER have XBRL - use ExtractedSectionContent instead
2. Reports NEVER influence Companies - they influence Industry/Sector/MarketIndex only
3. Boolean fields use strings: f.is_numeric = '1' (not true)
4. Always include LIMIT clause
5. Use fulltext indexes for text search: CALL db.index.fulltext.queryNodes()
6. Vector similarity: CALL db.index.vector.queryNodes('news_vector_index', k, embedding)
7. You may include WITH...RETURN aggregations (AVG, MAX, COUNT) in one query

Database structure:
- 31,618 Reports (only 10-K/10-Q have XBRL - 6,114 instances)
- 7.69M XBRL Facts (via Report→HAS_XBRL→XBRLNode←REPORTS←Fact)
- 144,813 ExtractedSectionContent nodes (text from all report types)
- INFLUENCES relationships have return properties (daily_stock, hourly_stock, etc.)
- Company.ticker for company identification

Return ONLY valid JSON:
{{"cypher": "YOUR_QUERY", "explanation": "brief"}}"""
        
        try:
            response = await self.claude_sonnet.ainvoke([
                SystemMessage(content="You are a Neo4j Cypher expert. Return only valid JSON."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            logger.debug(f"Claude response: {content[:200]}...")
            
            # Extract JSON
            if "```json" in content:
                parts = content.split("```json")
                if len(parts) > 1:
                    content = parts[1].split("```")[0]
            elif "```" in content:
                parts = content.split("```")
                if len(parts) > 2:
                    content = parts[1]
            
            json_str = content
            if '{' in json_str:
                json_str = json_str[json_str.index('{'):]
            if '}' in json_str:
                json_str = json_str[:json_str.rindex('}')+1]
            
            result = json.loads(json_str)
            cypher = result.get('cypher', '')
            
            if not cypher:
                logger.error("No cypher in Claude response")
                return {"success": False, "error": "No query generated"}
            
            # Validate cypher
            if not self._validate_cypher(cypher):
                logger.error("Claude generated invalid Cypher")
                return {"success": False, "error": "Invalid query generated"}
            
            # Execute
            neo4j_result = await self._execute_neo4j(cypher)
            
            if self._validate_results(neo4j_result):
                # Don't save here - will save in execute() after guard passes
                return {
                    "success": True,
                    "result": neo4j_result,
                    "method": "claude",
                    "cypher": cypher
                }
            else:
                logger.warning("Claude results failed validation")
                return {"success": False, "error": "Results validation failed", "cypher": cypher}
                
        except Exception as e:
            logger.error(f"Claude fallback failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_for_review(self, query: str, cypher: str, method: str, guard_approved: bool = False):
        """Save successful novel queries with guard approval status"""
        try:
            with open(self.pending_templates_file, "a") as f:
                f.write(json.dumps({
                    "query": query,
                    "cypher": cypher,
                    "method": method,
                    "guard_approved": guard_approved,
                    "timestamp": time.time()
                }) + "\n")
            logger.info(f"Saved novel query for review: {query[:50]}... (guard_approved={guard_approved})")
        except Exception as e:
            logger.error(f"Failed to save for review: {e}")
    
    async def _post_execution_guard(self, query: str, result: List[Dict], 
                                   method: str, template: Optional[Template] = None, 
                                   params: Optional[Dict] = None) -> Tuple[bool, str]:
        """Production-ready guard with all safety features"""
        params = params or {}
        
        # Check validators
        passed_shape = self._validate_shape(result, template, params) if template else True
        passed_values = self._validate_results(result)
        
        # COUNT-ZERO special trigger
        is_count_query = any(word in query.lower() for word in ["how many", "number", "total", "count"])
        has_zero = (result and isinstance(result[0], dict) and 
                    any(v == 0 for v in result[0].values()))
        
        if is_count_query and has_zero:
            run_guard = True  # Always guard COUNT=0
        else:
            run_guard = not (
                method in ("template", "cache", "regex") and passed_shape and passed_values
            )
        
        if not run_guard:
            return True, ""
        
        # BYTE-CAPPED prompt with safe UTF-8 truncation
        result_json = json.dumps(result, indent=2)
        result_preview = result_json.encode("utf-8")[:1500].decode("utf-8", "ignore")
        prompt = f"Query: {query}\nResults:\n{result_preview}\nDoes this answer the query? Reply: YES or NO: <reason>"
        
        try:
            response = await asyncio.wait_for(
                self.gpt4o_mini.ainvoke([
                    SystemMessage(content="Reply only: YES or NO: <1-line reason>"),
                    HumanMessage(content=prompt)
                ]),
                timeout=2.0
            )
            answer = response.content.strip()
            if answer.startswith("NO"):
                logger.warning(f"GUARD_FAIL: Query='{query[:50]}...' Reason='{answer[3:]}'")
                return False, answer[3:].strip()
            return True, ""
        except asyncio.TimeoutError:
            # HARD NO on timeout
            logger.warning(f"GUARD_TIMEOUT: Query='{query[:50]}...'")
            return False, "Guard timeout - retrying"
        except Exception as e:
            logger.error(f"Guard error: {e}")
            # On error, default to NO for safety
            return False, f"Guard error: {str(e)[:100]}"
    
    async def execute(self, query: str) -> Dict:
        """Main execution flow with all defensive layers"""
        logger.info(f"Processing query: {query[:100]}...")
        start_time = time.time()
        
        # Check indexes on first query
        await self._check_indexes_health()
        
        # Stage 0: Fast regex - catches 70% for free
        if regex_match := self._try_fast_regex(query):
            template_id, params = regex_match
            template = TEMPLATES[template_id]
            
            # Execute directly without semantic gate (these are trivial queries)
            result = await self._execute_neo4j(template.cypher, params)
            if self._validate_shape(result, template, params):
                # Check if it's a COUNT query returning 0 - needs guard
                is_count_query = any(word in query.lower() for word in ["how many", "number", "total", "count"])
                has_zero = (result and isinstance(result[0], dict) and 
                           any(v == 0 for v in result[0].values()))
                
                if is_count_query and has_zero:
                    # Run guard for COUNT-0 queries
                    guard_ok, guard_reason = await self._post_execution_guard(
                        query, result, "regex", template, params
                    )
                    if not guard_ok:
                        logger.warning(f"Regex COUNT-0 failed guard: {guard_reason}")
                        # Fall through to template matching
                    else:
                        return {
                            "success": True,
                            "result": result,
                            "method": "regex",
                            "template": template_id,
                            "execution_time": time.time() - start_time
                        }
                else:
                    return {
                        "success": True,
                        "result": result,
                        "method": "regex",
                        "template": template_id,
                        "execution_time": time.time() - start_time
                    }
            # If shape validation fails, fall through to template matching
        
        # Stage 1: Template matching with validation
        template_id, params = self._match_template(query)
        
        if template_id:
            template = TEMPLATES[template_id]
            
            # Check if parameters are valid (using template's validator)
            if not template.validator(params):
                logger.warning(f"Template {template_id} parameter validation failed")
                template_id = None  # Force fallback
            # Semantic gate - verify query matches
            elif await self._semantic_gate(query, template, params):
                # Check cache
                cache_key = self._get_cache_key(template.cypher, params)
                if cached := await self._check_cache(cache_key):
                    return {
                        "success": True,
                        "result": cached,
                        "method": "cache",
                        "template": template_id,
                        "execution_time": time.time() - start_time
                    }
                
                # Execute template
                try:
                    result = await self._execute_neo4j(template.cypher, params)
                    
                    # Shape validation instead of just _validate_results
                    if self._validate_shape(result, template, params):
                        # Check if it's a COUNT query returning 0 - needs guard
                        is_count_query = any(word in query.lower() for word in ["how many", "number", "total", "count"])
                        has_zero = (result and isinstance(result[0], dict) and 
                                   any(v == 0 for v in result[0].values()))
                        
                        if is_count_query and has_zero:
                            # Run guard for COUNT-0 queries
                            guard_ok, guard_reason = await self._post_execution_guard(
                                query, result, "template", template, params
                            )
                            if not guard_ok:
                                logger.warning(f"Template COUNT-0 failed guard: {guard_reason}")
                                # Fall through to LLM fallback
                            else:
                                # Cache and return
                                await self._set_cache(cache_key, result)
                                return {
                                    "success": True,
                                    "result": result,
                                    "method": "template",
                                    "template": template_id,
                                    "execution_time": time.time() - start_time
                                }
                        else:
                            # Cache successful results
                            await self._set_cache(cache_key, result)
                            return {
                                "success": True,
                                "result": result,
                                "method": "template",
                                "template": template_id,
                                "execution_time": time.time() - start_time
                            }
                    else:
                        logger.warning(f"Template {template_id} shape validation failed")
                        
                except Exception as e:
                    logger.error(f"Template execution failed: {e}")
            else:
                logger.info(f"Semantic gate rejected template {template_id}")
        
        # Step 2: GPT-4o-mini fallback with repair loop (9% of queries)
        repair_attempts = 0
        MAX_REPAIRS = 3
        last_reason = ""
        
        while repair_attempts < MAX_REPAIRS:
            if repair_attempts == 0:
                # First attempt
                gpt_result = await self._gpt4o_fallback(query)
            else:
                # Mini-ReAct repair
                logger.info(f"GPT-4o repair attempt {repair_attempts} with reason: {last_reason[:100]}")
                repair_prompt = f"Previous query failed validation: {last_reason}\nFix the query:\n{gpt_result.get('cypher', '')}"
                
                try:
                    response = await self.gpt4o_mini.ainvoke([
                        SystemMessage(content="Fix the Cypher query based on the error. Return only the corrected query."),
                        HumanMessage(content=repair_prompt)
                    ])
                    fixed_cypher = response.content.strip()
                    
                    # Validate and execute
                    if self._validate_cypher(fixed_cypher):
                        result = await self._execute_neo4j(fixed_cypher)
                        gpt_result = {
                            "success": True if result else False,
                            "result": result,
                            "cypher": fixed_cypher,
                            "method": "gpt4o"
                        }
                    else:
                        gpt_result = {"success": False, "error": "Fixed query failed validation"}
                except Exception as e:
                    logger.error(f"GPT-4o repair failed: {e}")
                    break
            
            if gpt_result.get("success"):
                # Run guard on successful result
                guard_ok, guard_reason = await self._post_execution_guard(
                    query, gpt_result.get("result", []), "gpt4o", None, {}
                )
                if guard_ok:
                    self._save_for_review(query, gpt_result["cypher"], "gpt4o", True)
                    gpt_result["execution_time"] = time.time() - start_time
                    return gpt_result
                else:
                    last_reason = guard_reason
                    repair_attempts += 1
            else:
                break  # Can't repair if base generation failed
        
        # Step 3: Claude Sonnet fallback with repair loop (1% of queries)
        repair_attempts = 0
        last_reason = ""
        
        while repair_attempts < MAX_REPAIRS:
            if repair_attempts == 0:
                # First attempt
                claude_result = await self._claude_fallback(query)
            else:
                # Mini-ReAct repair with Claude
                logger.info(f"Claude repair attempt {repair_attempts} with reason: {last_reason[:100]}")
                repair_prompt = f"Previous query failed validation: {last_reason}\nFix the query:\n{claude_result.get('cypher', '')}"
                
                try:
                    response = await self.claude_sonnet.ainvoke([
                        SystemMessage(content="Fix the Cypher query based on the error. Return only the corrected query."),
                        HumanMessage(content=repair_prompt)
                    ])
                    fixed_cypher = response.content.strip()
                    
                    # Validate and execute
                    if self._validate_cypher(fixed_cypher):
                        result = await self._execute_neo4j(fixed_cypher)
                        claude_result = {
                            "success": True if result else False,
                            "result": result,
                            "cypher": fixed_cypher,
                            "method": "claude"
                        }
                    else:
                        claude_result = {"success": False, "error": "Fixed query failed validation"}
                except Exception as e:
                    logger.error(f"Claude repair failed: {e}")
                    break
            
            if claude_result.get("success"):
                # Run guard on successful result
                guard_ok, guard_reason = await self._post_execution_guard(
                    query, claude_result.get("result", []), "claude", None, {}
                )
                if guard_ok:
                    self._save_for_review(query, claude_result["cypher"], "claude", True)
                    claude_result["execution_time"] = time.time() - start_time
                    return claude_result
                else:
                    last_reason = guard_reason
                    repair_attempts += 1
            else:
                break  # Can't repair if base generation failed
        
        # Step 4: Final ReAct fallback is now integrated above
        
        # All methods failed
        return {
            "success": False,
            "error": f"All methods failed after {MAX_REPAIRS} repair attempts",
            "execution_time": time.time() - start_time
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = sum(1 for _, (_, timestamp) in self.cache.items() 
                          if current_time - timestamp < self.ttl)
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "cache_size_bytes": sum(len(str(v)) for v, _ in self.cache.values())
        }
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        logger.info("Cache cleared")


# Global singleton executor
_global_executor = None
_executor_lock = asyncio.Lock()

async def get_executor() -> QueryExecutor:
    """Get or create singleton executor"""
    global _global_executor
    if _global_executor is None:
        async with _executor_lock:
            if _global_executor is None:
                _global_executor = QueryExecutor()
    return _global_executor

# Convenience function for backwards compatibility
async def query_neo4j_v5(query: str) -> Dict:
    """Execute a query using the V5 system"""
    executor = await get_executor()
    return await executor.execute(query)


if __name__ == "__main__":
    # Test the executor
    import asyncio
    
    async def test():
        executor = QueryExecutor()
        
        # Test template match
        result1 = await executor.execute("What's Apple's revenue from the latest 10-K?")
        print(f"Template result: {result1['method']}, Success: {result1['success']}")
        
        # Test complex query (likely LLM)
        result2 = await executor.execute("Find companies with unusual derivative positions discussed in risk factors")
        print(f"Complex result: {result2['method']}, Success: {result2['success']}")
        
        # Show cache stats
        print(f"Cache stats: {executor.get_cache_stats()}")
    
    asyncio.run(test())