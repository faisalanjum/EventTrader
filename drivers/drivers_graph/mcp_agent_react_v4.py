"""MCP Agent React V3 - LLM self-validation for 100% semantic accuracy"""
import json
import numpy as np
import re
from typing import List, Dict, Optional, Tuple
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
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# Constants
MAX_STEPS = 20  # Increased for complex queries without Opus
ESCALATION_THRESHOLD = 3  # Switch to Claude Sonnet after 3 failures
MAX_RESULT_LENGTH = 5000  # Maximum characters to return to LLM
MAX_RESULT_ROWS = 50  # Maximum rows to return


class MinimalTieredAgent:
    """Agent with LLM self-validation for semantic correctness"""
    
    # These are TEACHING EXAMPLES for few-shot learning, NOT hardcoded solutions
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
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' AND f.is_numeric = '1' RETURN c.ticker, f.value, r.created ORDER BY r.created DESC LIMIT 20"
        },
        {
            "query": "Get revenue facts from 10-K reports",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE r.formType = '10-K' AND con.qname CONTAINS 'Revenue' AND f.is_numeric = '1' RETURN c.ticker, con.qname, f.value, r.created ORDER BY r.created DESC LIMIT 20"
        },
        # Complex multi-condition
        {
            "query": "Find 10-Q filings where same-day news drove returns below market",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date AND rel.daily_stock < rel.daily_macro RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, r.formType ORDER BY rel.daily_stock LIMIT 20"
        },
        # Complex with fact retrieval - UPDATED with DISTINCT pattern
        {
            "query": "Find companies with 10-Q filings, same-day news impact, and get their NetIncomeLoss",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' AND datetime(r.created) > datetime() - duration('P60D') WITH c, r, date(datetime(r.created)) as report_date MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = report_date AND rel.daily_stock < rel.daily_macro - 4.0 WITH c, r, n, rel OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' AND f.is_numeric = '1' WITH c, r, n, rel, f ORDER BY f.period_ref DESC WITH c, COLLECT({news: n, rel: rel, report: r, fact: f})[0] as data RETURN c.ticker, data.news.title as title, data.rel.daily_stock as daily_stock, data.rel.daily_macro as daily_macro, data.report.formType as formType, data.fact.value as NetIncomeLoss LIMIT 10"
        },
        # Pattern showing DISTINCT companies when requested
        {
            "query": "Find 5 distinct companies with recent news impact",
            "cypher": "MATCH (n:News)-[:INFLUENCES]->(c:Company) WHERE datetime(n.created) > datetime() - duration('P30D') WITH c, COUNT(n) as news_count ORDER BY news_count DESC LIMIT 5 RETURN c.ticker, news_count"
        },
        # Pattern for complex query with DISTINCT companies and proper fact retrieval
        {
            "query": "Find 10 distinct companies with 10-Q filings and news-driven underperformance with NetIncomeLoss",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-Q' AND datetime(r.created) > datetime() - duration('P60D') WITH c, r MATCH (n:News)-[rel:INFLUENCES]->(c) WHERE date(datetime(n.created)) = date(datetime(r.created)) AND rel.daily_stock < rel.daily_macro - 4.0 WITH DISTINCT c, COLLECT({news: n, rel: rel, report: r})[0] as data OPTIONAL MATCH (data.report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE con.qname = 'us-gaap:NetIncomeLoss' AND f.is_numeric = '1' WITH c, data, f ORDER BY f.period_ref DESC WITH c, data, COLLECT(f)[0] as latest_fact RETURN c.ticker, data.news.title as title, data.rel.daily_stock as daily_stock, data.rel.daily_macro as daily_macro, data.report.formType as formType, latest_fact.value as NetIncomeLoss LIMIT 10"
        },
        # Pattern showing hourly returns
        {
            "query": "Find news with significant hourly stock impact",
            "cypher": "MATCH (n:News)-[r:INFLUENCES]->(c:Company) WHERE r.hourly_stock > 5.0 RETURN n.title, c.ticker, r.hourly_stock ORDER BY r.hourly_stock DESC LIMIT 10"
        },
        # Pattern showing session returns
        {
            "query": "Find pre-market news impacts",
            "cypher": "MATCH (n:News)-[r:INFLUENCES]->(c:Company) WHERE r.session_stock < -3.0 AND n.market_session = 'pre_market' RETURN n.title, c.ticker, r.session_stock, n.market_session ORDER BY r.session_stock LIMIT 10"
        },
        # Pattern showing industry level returns
        {
            "query": "Find news affecting industry returns",
            "cypher": "MATCH (n:News)-[r:INFLUENCES]->(i:Industry) WHERE r.daily_industry < -2.0 RETURN n.title, i.name, r.daily_industry ORDER BY r.daily_industry LIMIT 10"
        },
        # Pattern showing sector level returns
        {
            "query": "Find news impacting sector performance",
            "cypher": "MATCH (n:News)-[r:INFLUENCES]->(s:Sector) WHERE r.daily_sector > 1.5 RETURN n.title, s.name, r.daily_sector ORDER BY r.daily_sector DESC LIMIT 10"
        },
        # Pattern with REFERENCED_IN relationship
        {
            "query": "Find companies referenced in recent reports",
            "cypher": "MATCH (c:Company)<-[:REFERENCED_IN]-(r:Report) WHERE datetime(r.created) > datetime() - duration('P30D') RETURN c.ticker, r.formType, r.created ORDER BY r.created DESC LIMIT 20"
        },
        # Pattern showing Report influences Market levels (NOT Company)
        {
            "query": "Find reports affecting industry performance",
            "cypher": "MATCH (r:Report)-[rel:INFLUENCES]->(i:Industry) WHERE r.formType = '10-K' AND rel.daily_industry > 2.0 RETURN r.accessionNo, i.name, rel.daily_industry ORDER BY rel.daily_industry DESC LIMIT 10"
        },
        # Transcript patterns (major data type)
        {
            "query": "Find earnings call transcripts for a company",
            "cypher": "MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t:Transcript) WHERE c.ticker = 'AAPL' RETURN t.conference_datetime, t.fiscal_quarter, t.fiscal_year ORDER BY t.conference_datetime DESC LIMIT 10"
        },
        {
            "query": "Find transcripts affecting company returns",
            "cypher": "MATCH (t:Transcript)-[rel:INFLUENCES]->(c:Company) WHERE rel.daily_stock < -3.0 RETURN c.ticker, t.conference_datetime, rel.daily_stock, rel.daily_macro ORDER BY rel.daily_stock LIMIT 10"
        },
        # BELONGS_TO hierarchy traversal
        {
            "query": "Find all companies in a specific industry",
            "cypher": "MATCH (c:Company)-[:BELONGS_TO]->(i:Industry) WHERE i.name = 'Software' RETURN c.ticker, c.name, c.mkt_cap ORDER BY c.mkt_cap DESC LIMIT 20"
        },
        {
            "query": "Traverse full hierarchy from company to market",
            "cypher": "MATCH path = (c:Company)-[:BELONGS_TO]->(i:Industry)-[:BELONGS_TO]->(s:Sector)-[:BELONGS_TO]->(m:MarketIndex) WHERE c.ticker = 'AAPL' RETURN c.ticker, i.name as industry, s.name as sector, m.ticker as market"
        },
        # HAS_PRICE time series pattern
        {
            "query": "Get company price history for date range",
            "cypher": "MATCH (d:Date)-[p:HAS_PRICE]->(c:Company) WHERE c.ticker = 'AAPL' AND date(d.date) >= date('2024-01-01') AND date(d.date) <= date('2024-01-31') RETURN d.date, p.open, p.high, p.low, p.close, p.volume ORDER BY d.date"
        },
        # QAExchange pattern with transcript components
        {
            "query": "Find Q&A exchanges in earnings calls",
            "cypher": "MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(qa:QAExchange) WHERE t.symbol = 'AAPL' AND qa.questioner CONTAINS 'analyst' RETURN qa.questioner, qa.questioner_title, qa.exchanges ORDER BY qa.sequence LIMIT 5"
        },
        # Pattern showing combined conditions with NULL checks
        {
            "query": "Find companies with complete financial data",
            "cypher": "MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report) WHERE r.formType = '10-K' AND r.periodOfReport IS NOT NULL AND c.mkt_cap IS NOT NULL AND c.employees IS NOT NULL RETURN c.ticker, c.mkt_cap, c.employees, r.periodOfReport ORDER BY c.mkt_cap DESC LIMIT 10"
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
            model="claude-sonnet-4-20250514",
            temperature=0,
            max_tokens=4096,  # Increased for better reasoning
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
    
    def _extract_return_columns(self, cypher: str) -> List[str]:
        """Extract all columns from RETURN clause"""
        if 'RETURN' not in cypher:
            return []
        
        return_part = cypher.split('RETURN')[-1]
        # Remove ORDER BY, LIMIT, etc
        return_part = re.split(r'\b(ORDER BY|LIMIT|$)', return_part)[0]
        
        # Find all alias.property patterns
        columns = re.findall(r'\b(\w+\.\w+)\b', return_part)
        
        # Also find 'as alias' patterns
        as_patterns = re.findall(r'\bas\s+(\w+)\b', return_part, re.IGNORECASE)
        
        # Combine and remove duplicates
        all_columns = list(set(columns))
        
        return all_columns
    
    def _validate_semantic_correctness(self, data: List[dict], expectations: dict) -> List[str]:
        """Validate results against LLM-defined expectations"""
        errors = []
        
        if not isinstance(data, list):
            return ["Result is not a list"]
        
        # 1. Check distinct entities
        if "distinct_companies" in expectations and data:
            tickers = {row.get("c.ticker") for row in data if "c.ticker" in row}
            expected = expectations["distinct_companies"]
            actual = len(tickers)
            if actual < expected:
                ticker_list = list(tickers)[:5]  # Show first 5
                errors.append(f"Expected {expected} distinct companies but got {actual}: {ticker_list}...")
        
        # 2. Check required columns exist and aren't mostly null
        for col in expectations.get("required_columns", []):
            if not data:
                continue
                
            # Check if column exists
            if data and col not in data[0]:
                errors.append(f"Missing expected column: {col}")
                continue
            
            # Check null ratio
            null_count = sum(1 for row in data if row.get(col) is None)
            null_ratio = null_count / len(data) if data else 1.0
            
            # Check ALL columns for null ratios (v4 enhancement)
            fact_keywords = ['revenue', 'income', 'loss', 'assets', 'earnings', 'value', 'netincomeloss']
            if any(keyword in col.lower() for keyword in fact_keywords):
                # Fact columns: 80% threshold
                if null_ratio > 0.8:
                    errors.append(f"Column {col} is {null_ratio*100:.0f}% null (only {len(data)-null_count}/{len(data)} have values)")
            else:
                # Non-fact columns: 50% threshold
                if null_ratio > 0.5:
                    errors.append(f"Column {col} is {null_ratio*100:.0f}% null")
        
        # 3. Check boolean expectations (has_revenue, has_netincome, etc)
        for key, expected in expectations.items():
            if key.startswith("has_") and expected is True:
                fact_name = key[4:]  # Remove "has_" prefix
                
                # Look for any column containing this fact name
                fact_found = False
                for row in data[:10]:  # Check first 10 rows
                    for col_name, value in row.items():
                        if fact_name.lower() in col_name.lower() and value is not None:
                            fact_found = True
                            break
                    if fact_found:
                        break
                
                if not fact_found:
                    errors.append(f"Expected {fact_name} values but none found (checked first 10 rows)")
        
        # 4. Check minimum results
        if "min_results" in expectations:
            expected_min = expectations["min_results"]
            actual = len(data)
            if actual < expected_min:
                errors.append(f"Expected at least {expected_min} results but got {actual}")
        
        return errors
    
    async def query_generate(self, user_query: str, errors: List[str] = None) -> Tuple[str, dict]:
        """Generate Cypher query AND expectations for semantic validation"""
        # Escalate to tier 2 after threshold failures
        if errors and len(errors) >= ESCALATION_THRESHOLD and self.current_tier == 1:
            self.current_tier = 2
            logger.info("Escalating to Claude Sonnet 4 for complex query")
        
        # Select model based on tier
        llm = self.tier1_llm if self.current_tier == 1 else self.tier2_llm
        model_name = "GPT-4o-mini" if self.current_tier == 1 else "Claude Sonnet 4"
        logger.info(f"Using {model_name} for generation")
        
        # Find similar examples
        examples = await self._find_examples(user_query)
        prompt = self._build_prompt(user_query, examples)
        
        # Add expectation instructions
        prompt += """

After generating the Cypher query, provide your expectations in JSON format.
Use EXPECT: prefix followed by JSON on the same line.

Example formats:
- For distinct entities: EXPECT: {"distinct_companies": 10}
- For required values: EXPECT: {"has_revenue": true, "has_netincome": true}
- For minimum results: EXPECT: {"min_results": 5}
- Combined: EXPECT: {"distinct_companies": 5, "has_revenue": true, "required_columns": ["c.ticker", "n.title"]}

Your expectations should reflect what the query MUST deliver to be correct.
"""
        
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
        
        content = response.content.strip()
        
        # Extract Cypher and expectations
        if "EXPECT:" in content:
            parts = content.split("EXPECT:", 1)
            cypher = parts[0].strip()
            try:
                expect_json = parts[1].strip()
                # Remove any trailing text after JSON
                if expect_json.startswith("{"):
                    # Find the closing brace
                    brace_count = 0
                    end_pos = 0
                    for i, char in enumerate(expect_json):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                    expect_json = expect_json[:end_pos]
                expectations = json.loads(expect_json)
            except Exception as e:
                logger.warning(f"Failed to parse expectations JSON: {e}, content: {parts[1][:200]}...")
                expectations = {}
        else:
            cypher = content
            expectations = {}
        
        # Clean up Cypher (remove code blocks, prefixes)
        if "```" in cypher:
            match = re.search(r'```(?:cypher|sql)?\s*\n(.*?)\n```', cypher, re.DOTALL)
            if match:
                cypher = match.group(1).strip()
        
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
        
        # Apply ONLY the NaN fix
        cypher = re.sub(
            r"(\w+\.\w+)\s+IS\s+NOT\s+NULL\s+<>\s*'NaN'",
            r"\1 IS NOT NULL AND \1 <> 'NaN'",
            cypher
        )
        
        # Auto-extract RETURN columns
        return_cols = self._extract_return_columns(cypher)
        
        # Ensure RETURN columns are in expectations
        if return_cols:
            if "required_columns" not in expectations:
                expectations["required_columns"] = return_cols
            else:
                for col in return_cols:
                    if col not in expectations["required_columns"]:
                        expectations["required_columns"].append(col)
        
        # Ensure at least one expectation
        if not expectations or all(not v for v in expectations.values()):
            expectations["min_results"] = 1
        
        # Add LIMIT if missing (but respect existing limits)
        if not re.search(r'\bLIMIT\s+\d+', cypher) and 'count(' not in cypher.lower():
            cypher += ' LIMIT 100'  # Default limit for safety
        
        return cypher, expectations
    
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
        
        query_emb = np.array(await self.embeddings.aembed_query(query))
        scores = []
        
        for pattern in all_patterns:
            if 'embedding' not in pattern:
                pattern['embedding'] = np.array(await self.embeddings.aembed_query(pattern['query']))
            
            # Ensure both are numpy arrays
            query_vec = np.array(query_emb) if not isinstance(query_emb, np.ndarray) else query_emb
            pattern_vec = np.array(pattern['embedding']) if not isinstance(pattern['embedding'], np.ndarray) else pattern['embedding']
            
            sim = np.dot(query_vec, pattern_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(pattern_vec)
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
            "9. If the query asks for 'N companies', ensure you return N DISTINCT companies",
            "10. For fact retrieval (Revenue, NetIncomeLoss, etc), use OPTIONAL MATCH pattern after main query",
            "11. Structure complex queries with WITH clauses to maintain context between joins",
            "12. Fact.is_numeric uses string '1' or '0', not boolean true/false",
            "13. Report NEVER INFLUENCES Company - only Industry/Sector/MarketIndex",
            "14. Return properties include: hourly_*, session_*, daily_* for stock/industry/sector/macro levels",
            "15. Company.employees is stored as string with commas (e.g., '6,600')",
            "16. REFERENCED_IN relationship exists similar to PRIMARY_FILER with return properties",
            "17. QAExchange.responders is comma-separated string, not a list",
            "18. Transcript also INFLUENCES entities like News/Report (check t.formType)",
            "19. HAS_PRICE has 9 mandatory properties: open, high, low, close, volume, vwap, transactions, otc, source",
            "20. Use indexed fields for filtering when possible: all nodes have id index, News/QAExchange have vector indexes",
            "21. Date properties: only 68% have current_day market times, use IS NOT NULL checks",
            "\nGenerate Cypher query following the EXACT patterns from examples."
        ])
        
        return "\n".join(prompt)
    
    async def _learn(self, query: str, cypher: str, result_count: int = 0):
        """Learn from successful queries - saves to Redis"""
        # Only learn if we got meaningful results
        if result_count == 0:
            logger.info("Skipping learning - query returned no results")
            return
        
        query_emb = np.array(await self.embeddings.aembed_query(query))
        
        # Load existing patterns from Redis
        if self.use_redis and self.redis_client:
            existing_patterns = await self._load_patterns_from_redis()
        else:
            existing_patterns = self.patterns[len(self.SEED_PATTERNS):]  # Skip seeds
        
        # Check for duplicates with same threshold as original (0.95)
        for pattern in existing_patterns:
            if 'embedding' not in pattern:
                pattern['embedding'] = np.array(await self.embeddings.aembed_query(pattern['query']))
            
            # Ensure both are numpy arrays
            query_vec = np.array(query_emb) if not isinstance(query_emb, np.ndarray) else query_emb
            pattern_vec = np.array(pattern['embedding']) if not isinstance(pattern['embedding'], np.ndarray) else pattern['embedding']
            
            sim = np.dot(query_vec, pattern_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(pattern_vec)
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


# State definition for LangGraph
class AgentState(TypedDict):
    query: str
    errors: List[str]
    result: Optional[Dict]
    cypher: Optional[str]
    expectations: Optional[dict]  # NEW: LLM-defined success criteria
    last_result: Optional[Dict]
    current_tier: int  # Track which model tier we're using
    was_truncated: bool  # Track if results were truncated


# Global agent singleton
_global_agent = None
_agent_lock = asyncio.Lock()


async def _get_agent():
    """Get or create singleton agent"""
    global _global_agent
    if _global_agent is None:
        async with _agent_lock:
            if _global_agent is None:
                _global_agent = MinimalTieredAgent()
    return _global_agent


def create_graph():
    """Create the minimal tiered ReAct graph with semantic validation"""
    graph = StateGraph(AgentState)
    
    async def agent_generate(state):
        """Generate Cypher AND expectations based on query and error history"""
        agent = await _get_agent()
        cypher, expectations = await agent.query_generate(
            state["query"], 
            state.get("errors", [])
        )
        logger.info(f"Generated Cypher: {cypher[:100]}...")
        logger.info(f"Expectations: {expectations}")
        return {
            "cypher": cypher, 
            "expectations": expectations,
            "current_tier": agent.current_tier
        }
    
    async def tool_execute(state):
        """Execute the generated Cypher"""
        agent = await _get_agent()
        result = await agent.query_execute(state["cypher"])
        return {"last_result": result}
    
    async def check_result(state):
        """Check both syntax and semantic correctness"""
        agent = await _get_agent()
        result = state["last_result"]
        expectations = state.get("expectations", {})
        
        # Check for execution errors
        if "error" in result:
            errors = state.get("errors", []) + [result["error"]]
            return {"errors": errors, "result": None}
        
        # Check for empty results
        raw_result = result.get("result", "")
        if raw_result == '[]' or not raw_result:
            # Empty might be valid - check expectations
            if expectations.get("min_results", 0) > 0:
                errors = state.get("errors", []) + ["Query returned no results but expected some"]
                return {"errors": errors, "result": None}
        
        # Check if the result contains an error message
        # Be more specific - check for Neo4j error patterns
        if isinstance(raw_result, str):
            # Check for common Neo4j error patterns
            neo4j_error_patterns = [
                "Neo.ClientError", "Neo.DatabaseError", 
                "Invalid input", "Unknown function",
                "Variable .* not defined", "Type mismatch",
                "Syntax error", "Expected"
            ]
            
            for pattern in neo4j_error_patterns:
                if re.search(pattern, raw_result, re.IGNORECASE):
                    # Extract the error message
                    error_msg = raw_result
                    if "message:" in error_msg:
                        error_msg = error_msg.split("message:")[1].strip()
                    errors = state.get("errors", []) + [error_msg[:500]]
                    return {"errors": errors, "result": None}
        
        # Parse results for semantic validation
        try:
            data = json.loads(raw_result.split('\n\n[TRUNCATED')[0])
            
            # SEMANTIC VALIDATION - this is the key innovation
            if expectations:
                semantic_errors = agent._validate_semantic_correctness(data, expectations)
                
                if semantic_errors:
                    # Include preview of actual results for context
                    preview = json.dumps(data[:2], indent=2) if data else "[]"
                    error_msg = f"Semantic validation failed: {'; '.join(semantic_errors)}\nActual data preview: {preview[:300]}..."
                    errors = state.get("errors", []) + [error_msg]
                    return {"errors": errors, "result": None}
            
            # Success! Calculate result count for learning
            result_count = len(data) if isinstance(data, list) else 1
            
        except json.JSONDecodeError:
            # Non-JSON result, treat as success if no errors
            result_count = 1
        
        # Learn ONLY from semantically valid results
        await agent._learn(state["query"], result["cypher"], result_count)
        agent.reset_tier()
        
        return {
            "result": result, 
            "current_tier": 1,
            "was_truncated": result.get("truncated", False)
        }
    
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
    """Query Neo4j with LLM self-validation for semantic correctness"""
    # Use custom recursion limit for complex queries
    config = {"recursion_limit": MAX_STEPS + 10}  # Add buffer for complex queries (30 total)
    
    result = await mcp_agent.ainvoke({
        "query": query,
        "errors": [],
        "result": None,
        "cypher": None,
        "expectations": None,
        "last_result": None,
        "current_tier": 1,
        "was_truncated": False
    }, config=config)
    
    if result.get("result"):
        return {
            "query": result["result"]["cypher"],
            "result": result["result"]["result"],
            "success": True,
            "attempts": len(result.get("errors", [])) + 1,
            "model_used": "Claude Sonnet 4" if result.get("current_tier", 1) == 2 else "GPT-4o-mini",
            "was_truncated": result.get("was_truncated", False)
        }
    else:
        return {
            "error": "All attempts failed",
            "last_errors": result.get("errors", [])[-2:],
            "success": False,
            "attempts": len(result.get("errors", [])),
            "model_used": "Claude Sonnet 4" if result.get("current_tier", 1) == 2 else "GPT-4o-mini"
        }


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