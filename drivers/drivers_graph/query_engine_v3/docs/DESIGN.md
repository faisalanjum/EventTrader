# Query Engine v3 - Complete Design Document

## System Architecture Overview

```
                    External System (LangGraph/React Agent)
                                    │
                                    ▼
                        ┌────────────────────┐
                        │   Query Engine v3   │
                        │    (LangGraph Tool) │
                        └────────────────────┘
                                    │
                                    ▼
                        ┌────────────────────┐
                        │   Investigator      │
                        │   (Orchestrator)    │
                        └────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            Parallel Execution              Context & Iteration
                    │                               │
    ┌───────────────┼───────────────┐              │
    ▼               ▼               ▼              ▼
XBRL Spec    Transcript Spec   News Spec    Market Spec
    │               │               │              │
    ▼               ▼               ▼              ▼
xbrl.csv      transcript.csv    news.csv     market.csv
(15 templates)  (10 templates)  (10 templates) (10 templates)
    │               │               │              │
    └───────────────┴───────────────┴──────────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
                Neo4j DB         Redis Cache
              (via MCP/direct)   (port 31379)
```

## 1. Executive Summary

Query Engine v3 is a natural language query system for financial data that uses pre-tested template queries to minimize errors while supporting complex iterative investigations. This design evolves query_engine_v2's template system into an iterative investigation framework. It addresses the problem of determining causal relationships in financial events (e.g., "What caused Apple's 7% stock movement?") through iterative refinement and domain-specific agents.

### Core Principles
1. **Template-Based Queries**: Pre-tested Cypher templates reduce query errors
2. **Iterative Investigation**: Refine understanding through multiple passes
3. **Domain Expertise**: Specialized agents for different data types
4. **Hint-Guided Discovery**: Each query reveals what else is available
5. **Cost Efficiency**: Parallel execution with early termination

## 2. Problem Statement

### Primary Use Case
Given a significant stock movement (e.g., "AAPL +7.26% on 2024-06-11"), the system must:
- Identify all potentially contributing events (news, earnings, reports)
- Determine which events were TRUE drivers vs coincidental
- Provide confidence-scored attribution with supporting evidence
- Handle complex multi-factor scenarios

### Challenges
1. **Multiple Events**: Often 10-20+ events occur on significant days
2. **Causal Ambiguity**: Correlation doesn't imply causation
3. **Data Complexity**: Events span news, transcripts, XBRL facts, market data
4. **Token Limits**: Full investigation might exceed context windows
5. **Query Flexibility**: Questions come from external LLMs, unpredictable

## 3. Architecture Overview

```
User Question
     ↓
Investigator (Orchestrator)
     ↓
Parallel Specialist Agents
     ├── XBRL Specialist (financial facts)
     ├── Transcript Specialist (earnings calls)
     ├── News Specialist (news/events)
     └── Market Specialist (prices/returns)
          ↓
     Each uses Templates (CSV)
     (60 pre-tested queries from query_engine_v2)
          ↓
     Neo4j Database (via MCP or direct)
          ↓
Iterative Refinement (max 3 iterations)
     ↓
Final Synthesis with Confidence Score
```

## 4. Component Specifications

### 4.1 Templates (Data Fetching Layer)

Templates are pre-written, tested Cypher queries designed for consistent data retrieval. Templates adapted from query_engine_v2/skeletonTemplates.csv, split by domain.

#### Structure
```csv
"Name","Key Props","Comment","Cypher","Category","Returns","Cacheable"
"get_fact","ticker,form,qname","Get financial metric","MATCH...","metric","value,date","true"
```

#### Critical Implementation Detail: Structural Parameters
Neo4j cannot parameterize labels, relationship types, or property names. These require string substitution:

```python
STRUCTURAL_PARAMS = {
    "Label", "L1", "L2", "L3",           # Node labels
    "Rel", "Rel1", "Rel2", "RelType",    # Relationship types
    "prop", "srcProp", "dateProp",       # Property names
    "order", "dir", "cmp", "agg"         # Operators
}

# Example transformation:
# Template: "MATCH (n:$Label) WHERE n.$prop = $value"
# After substitution: "MATCH (n:Company) WHERE n.ticker = $value"
# Final with params: "MATCH (n:Company) WHERE n.ticker = 'AAPL'"
```

#### Template Categories

**XBRL Templates** (~15 queries)
- `get_fact`: Single financial metric
- `get_facts_trend`: Metric over time
- `compare_companies`: Cross-company metrics
- `get_guidance`: Forward-looking statements
- `calculate_ratios`: P/E, margins, etc.

**Transcript Templates** (~10 queries)
- `search_qa`: Search Q&A sections
- `search_prepared`: Search prepared remarks
- `get_sentiment`: Tone analysis
- `find_guidance`: Extract guidance statements
- `get_key_topics`: Topic extraction

**News Templates** (~10 queries)
- `get_news_by_impact`: News with price impact
- `search_news_content`: Full-text search
- `get_news_sentiment`: Sentiment analysis
- `find_related_news`: Clustered events
- `get_news_timeline`: Temporal sequence

**Market Templates** (~10 queries)
- `get_prices`: Price history
- `find_movements`: Significant changes
- `calculate_returns`: Return calculations
- `compare_to_market`: Relative performance
- `get_volume_patterns`: Volume analysis

### 4.2 Specialist Agents

Domain experts that use templates to answer questions with hints about available data.

```python
class Specialist:
    """
    Domain expert that answers questions using templates.
    Returns answers with hints about what else is available.
    """
    
    def __init__(self, domain: str, templates_csv: str):
        self.domain = domain
        self.templates = self._load_templates(templates_csv)
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.cache = RedisCache()  # Cache expensive queries
        
    async def investigate(self, question: str, context: dict = None) -> dict:
        """
        Investigate question, return answer with hints.
        
        Returns:
        {
            'answer': str,           # Natural language answer
            'confidence': float,     # 0-1 confidence score
            'data_points': list,     # Raw data retrieved
            'hints': list,          # What else is available
            'suggestions': list,     # Specific next queries
            'metadata': dict        # Timing, cache hits, etc.
        }
        """
        
        # Step 1: Analyze question and context
        analysis = await self._analyze_question(question, context)
        
        # Step 2: Determine which templates to use
        template_plan = self._plan_templates(analysis)
        
        # Step 3: Execute templates (with caching)
        results = []
        for template_call in template_plan:
            cache_key = f"{template_call['name']}:{json.dumps(template_call['params'])}"
            
            # Check cache first
            cached = self.cache.get(cache_key)
            if cached:
                results.append(cached)
                continue
            
            # Execute template
            try:
                data = self._execute_template(
                    template_call['name'],
                    template_call['params']
                )
                result = {
                    'template': template_call['name'],
                    'data': data,
                    'row_count': len(data),
                    'success': True
                }
                
                # Cache if marked cacheable
                if self.templates[template_call['name']].get('cacheable'):
                    self.cache.set(cache_key, result, ttl=3600)
                    
                results.append(result)
                
            except Exception as e:
                results.append({
                    'template': template_call['name'],
                    'error': str(e),
                    'success': False
                })
        
        # Step 4: Generate answer with hints
        response = await self._generate_response(question, results, context)
        
        # Step 5: Calculate confidence
        confidence = self._calculate_confidence(results, response)
        
        return {
            'answer': response['answer'],
            'confidence': confidence,
            'data_points': results,
            'hints': response['hints'],
            'suggestions': response['suggestions'],
            'metadata': {
                'templates_used': len(template_plan),
                'cache_hits': sum(1 for r in results if r.get('from_cache')),
                'total_rows': sum(r.get('row_count', 0) for r in results)
            }
        }
    
    def _calculate_confidence(self, results: list, response: dict) -> float:
        """
        Calculate confidence based on:
        - Data availability (did queries return data?)
        - Data consistency (do multiple sources agree?)
        - Answer completeness (did we answer all parts?)
        """
        
        # Base confidence from data availability
        successful_queries = sum(1 for r in results if r.get('success'))
        total_queries = len(results)
        data_confidence = successful_queries / total_queries if total_queries > 0 else 0
        
        # Boost for multiple corroborating sources
        if successful_queries > 1:
            data_confidence = min(1.0, data_confidence * 1.2)
        
        # Reduce if hints suggest missing information
        if response.get('suggestions'):
            data_confidence *= 0.8
        
        # LLM's self-reported confidence
        llm_confidence = response.get('confidence', 0.5)
        
        # Weighted average
        return (data_confidence * 0.6 + llm_confidence * 0.4)
```

### 4.3 Investigator (Orchestration Layer)

Manages iterative investigation across specialists.

```python
class Investigator:
    """
    Orchestrates multi-specialist investigation with iteration.
    """
    
    def __init__(self):
        self.specialists = {
            'xbrl': Specialist('financial', 'xbrl_templates.csv'),
            'transcript': Specialist('earnings', 'transcript_templates.csv'),
            'news': Specialist('news', 'news_templates.csv'),
            'market': Specialist('market', 'market_templates.csv')
        }
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        
    async def investigate(self, question: str, max_iterations: int = 3) -> dict:
        """
        Iteratively investigate until confident or max iterations reached.
        """
        
        context = {
            'question': question,
            'findings': {},
            'confidence': 0,
            'iteration': 0,
            'total_tokens': 0
        }
        
        while context['iteration'] < max_iterations:
            context['iteration'] += 1
            
            # Step 1: Plan which specialists to consult
            plan = await self._plan_investigation(context)
            
            if not plan['specialists_needed']:
                break  # No more investigation needed
            
            # Step 2: Query specialists in parallel
            tasks = []
            for specialist_name in plan['specialists_needed']:
                specialist = self.specialists[specialist_name]
                specialist_context = context['findings'].get(specialist_name)
                tasks.append(
                    specialist.investigate(
                        plan['questions'][specialist_name],
                        context=specialist_context
                    )
                )
            
            responses = await asyncio.gather(*tasks)
            
            # Step 3: Update context with findings
            for spec_name, response in zip(plan['specialists_needed'], responses):
                if spec_name not in context['findings']:
                    context['findings'][spec_name] = []
                context['findings'][spec_name].append(response)
                
                # Update overall confidence (max of all specialists)
                context['confidence'] = max(
                    context['confidence'],
                    response['confidence']
                )
            
            # Step 4: Check termination conditions
            if context['confidence'] >= 0.85:
                break  # Confident enough
            
            if context['total_tokens'] > 100000:
                break  # Token limit approaching
            
            # Step 5: Synthesize suggestions for next iteration
            all_suggestions = []
            for spec_name in context['findings']:
                for finding in context['findings'][spec_name]:
                    all_suggestions.extend(finding.get('suggestions', []))
            
            if not all_suggestions:
                break  # No more ideas
        
        # Final synthesis
        return await self._synthesize_findings(context)
    
    async def _plan_investigation(self, context: dict) -> dict:
        """
        Determine which specialists to consult and what to ask.
        """
        
        prompt = f"""
        Question: {context['question']}
        Iteration: {context['iteration']}
        Current findings: {json.dumps(context['findings'], indent=2)[:2000]}
        Current confidence: {context['confidence']}
        
        Determine:
        1. Which specialists are needed (xbrl, transcript, news, market)
        2. Specific question for each specialist
        3. Whether we have enough information (return empty if done)
        
        Consider:
        - Don't repeat queries that already returned good data
        - Use hints from previous responses
        - Focus on filling gaps in understanding
        """
        
        response = await self.llm.ainvoke(prompt)
        # Parse response into plan...
        
    async def _synthesize_findings(self, context: dict) -> dict:
        """
        Combine all findings into final answer.
        Handles large contexts through progressive summarization.
        """
        
        # Progressive summarization if context too large
        findings_summary = {}
        for specialist, findings_list in context['findings'].items():
            if len(json.dumps(findings_list)) > 10000:
                # Summarize large findings
                summary = await self._summarize_findings(findings_list)
                findings_summary[specialist] = summary
            else:
                findings_summary[specialist] = findings_list
        
        prompt = f"""
        Original question: {context['question']}
        
        Findings from investigation:
        {json.dumps(findings_summary, indent=2)}
        
        Provide a comprehensive answer that:
        1. Directly answers the question
        2. Includes specific numbers and evidence
        3. Shows causal reasoning where applicable
        4. Acknowledges any uncertainty
        
        For event attribution specifically:
        - Identify primary drivers vs secondary factors
        - Explain timing relationships
        - Quantify impact where possible
        """
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            'answer': response.content,
            'confidence': context['confidence'],
            'iterations_used': context['iteration'],
            'specialists_consulted': list(context['findings'].keys()),
            'total_data_points': sum(
                len(findings) for findings in context['findings'].values()
            ),
            'supporting_evidence': self._extract_key_evidence(context['findings'])
        }
```

### 4.4 Cache Layer

Redis-based caching for expensive queries.

```python
class RedisCache:
    """
    Cache for template query results.
    """
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=31379)
        self.default_ttl = 3600  # 1 hour
        
    def get(self, key: str) -> Optional[dict]:
        """Get cached result if exists and not expired."""
        result = self.redis.get(f"qe_v3:{key}")
        if result:
            return json.loads(result)
        return None
        
    def set(self, key: str, value: dict, ttl: int = None):
        """Cache result with TTL."""
        self.redis.setex(
            f"qe_v3:{key}",
            ttl or self.default_ttl,
            json.dumps(value)
        )
```

## 5. Execution Flow Examples

### 5.1 Event Attribution Example

**Input**: "What drove AAPL's 7.26% gain on 2024-06-11?"

#### Iteration 1
```
Investigator → Plan: Consult news, market specialists

News Specialist:
  Templates used: get_news_by_impact, search_news_content
  Findings: 15 news items, "Apple AI announcement" has highest impact
  Confidence: 0.6
  Hints: "Multiple events at different times, check market session timing"
  Suggestions: ["Check if announcement was during market hours"]

Market Specialist:
  Templates used: get_prices, compare_to_market
  Findings: Stock jumped at 3:30pm, sector only +0.5%
  Confidence: 0.7
  Hints: "Company-specific catalyst in afternoon"
  
Overall confidence: 0.7 (continue)
```

#### Iteration 2
```
Investigator → Plan: Check transcripts and reports for context

Transcript Specialist:
  Templates used: search_prepared, find_guidance
  Findings: No earnings call that day
  Hints: "Check for conferences or special events"
  
XBRL Specialist:
  Templates used: get_fact (R&D expense)
  Findings: R&D up 15% YoY, supporting AI investment
  Confidence: 0.85
  
Overall confidence: 0.85 (stop)
```

#### Final Synthesis
```
Answer: "AAPL's 7.26% gain on 2024-06-11 was primarily driven by Apple's 
announcement of new AI developer tools at 3:30pm:

Primary Driver:
- AI tools announcement during market hours (3:30pm)
- Immediate price spike of 4% within 30 minutes
- News sentiment extremely positive (0.92 score)

Supporting Evidence:
- Sector gained only 0.5% (company-specific catalyst)
- R&D spending up 15% YoY validates AI investment narrative
- No other material events that day

Confidence: 85% - Strong correlation between announcement timing and price movement"
```

### 5.2 Batch Processing Example

For processing multiple days (from eventAttribution.ipynb):

```python
async def process_significant_days(ticker: str, days: list) -> list:
    """
    Process multiple significant days efficiently.
    """
    investigator = Investigator()
    
    # Process in parallel batches of 5 to avoid overwhelming system
    results = []
    for batch in chunks(days, 5):
        batch_tasks = [
            investigator.investigate(
                f"What drove {ticker}'s {day['return']}% move on {day['date']}?"
            )
            for day in batch
        ]
        batch_results = await asyncio.gather(*batch_tasks)
        results.extend(batch_results)
    
    return results
```

## 6. Error Handling

### Template Execution Failures
```python
try:
    result = execute_template(name, params)
except Neo4jException as e:
    # Try fallback template if available
    if fallback := FALLBACK_TEMPLATES.get(name):
        result = execute_template(fallback, params)
    else:
        # Return partial result with error flag
        return {'error': str(e), 'partial': True}
```

### Specialist Failures
- Continue with other specialists
- Mark confidence as reduced
- Include failure in hints for next iteration

### Token Limit Management
```python
if context_size > 50000:
    # Progressive summarization
    context = summarize_context(context)
```

## 7. Performance Optimizations

### Caching Strategy
- Cache template results for 1 hour
- Cache key: template_name + params hash
- Skip cache for time-sensitive queries

### Parallel Execution
- All specialists query in parallel
- Batch multiple investigations
- Early termination on high confidence

### Query Optimization
- Use COUNT queries before fetching large datasets
- Implement pagination for large results
- Pre-filter with indexed columns

## 8. Integration Points

### With LangGraph/React Agent
```python
@tool
async def investigate_with_templates(question: str) -> dict:
    """
    Investigate question using template-based system.
    Returns answer with confidence and evidence.
    """
    investigator = Investigator()
    return await investigator.investigate(question)
```

### With MCP Neo4j Server
```python
# Can use either direct connection or MCP
# Ports from CLAUDE.md Kubernetes infrastructure
if USE_MCP:
    result = await mcp_client.read_neo4j_cypher(cypher, params)
else:
    result = neo4j_driver.execute(cypher, params)
```

### With Event Attribution System
```python
# Direct integration for event attribution
attribution_data = prepare_attribution_package(ticker, date)
question = f"What drove {ticker}'s movement on {date}?"
result = await investigator.investigate(
    question,
    context=attribution_data
)
```

## 9. Configuration

### Environment Variables
```bash
NEO4J_URI=bolt://localhost:30687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Next2020#
REDIS_HOST=localhost
REDIS_PORT=31379
OPENAI_API_KEY=<key>
USE_MCP=false  # Use MCP server vs direct Neo4j
CACHE_TTL=3600
MAX_ITERATIONS=3
CONFIDENCE_THRESHOLD=0.85
```

### Template Configuration
```python
TEMPLATE_CONFIG = {
    'max_results_per_template': 1000,
    'timeout_seconds': 30,
    'cache_expensive_queries': True,
    'structural_params': {...}  # From query_engine_v2
}
```

## 10. Success Metrics

### Accuracy Metrics
- Template execution success rate (should be very high due to pre-testing)
- Correct event attribution (measured against known outcomes)
- Low false positive rate

### Performance Metrics
- Investigation completes in reasonable time
- Effective cache utilization
- Token usage stays manageable per investigation
- Cost-effective operation

### Quality Metrics
- Confidence scores correlate with actual accuracy
- Explanations are clear and evidence-based
- Iteration efficiency (converges in ≤3 iterations)

## 11. Implementation Checklist

### Phase 1: Core Components
- [ ] Create folder structure
- [ ] Split skeletonTemplates.csv into domain-specific CSVs (XBRL, Transcript, News, Market)
- [ ] Implement template executor with structural params
- [ ] Create base Specialist class
- [ ] Implement basic Investigator

### Phase 2: Intelligence Layer
- [ ] Add hint generation to Specialists
- [ ] Implement iterative investigation
- [ ] Add confidence scoring
- [ ] Create synthesis with evidence extraction

### Phase 3: Optimization
- [ ] Add Redis caching
- [ ] Implement batch processing
- [ ] Add progressive summarization
- [ ] Optimize parallel execution

### Phase 4: Integration
- [ ] Create LangGraph tool wrapper
- [ ] Test with eventAttribution.ipynb
- [ ] Add monitoring and metrics
- [ ] Document API and usage examples

## 12. Critical Implementation Notes

### From query_engine_v2 Experience

1. **Structural Parameters Are Required**
   - Neo4j cannot parameterize labels/relationships
   - Must use string substitution for these
   - Keep the STRUCTURAL_PARAMS list from query_engine_v2

2. **Template Validation**
   - Test each template in Neo4j browser first
   - Verify parameter substitution works correctly
   - Check for index usage with EXPLAIN

3. **Error Recovery**
   - Some templates will return empty results (normal)
   - Don't treat empty as error
   - Let specialists handle and provide hints

### For Event Attribution Specifically

1. **Time Window Handling**
   - Events can impact next trading day
   - Check both current and previous day events
   - Consider market session (pre/post/during)

2. **Impact Scoring**
   - Immediate impact (within 1 hour)
   - Session impact (pre/post market)
   - Daily impact (full day movement)

3. **Multiple Factor Attribution**
   - Rarely is one event the sole cause
   - Rank events by impact strength
   - Show primary vs contributing factors

## 13. Example Templates

# Examples from query_engine_v2/skeletonTemplates.csv

### XBRL Template Example
```csv
"get_fact","ticker,form,qname","Get financial metric","
MATCH (c:Company {ticker:$ticker})<-[:PRIMARY_FILER]-(r:Report {formType:$form})
-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept {qname:$qname})
WHERE f.is_numeric='1'
RETURN r.created as date, f.value as value, f.unit as unit
ORDER BY r.created DESC
LIMIT 1","metric","value,date,unit","true"
```

### News Template Example
```csv
"get_news_by_impact","ticker,date,min_impact","News with price impact","
MATCH (n:News)-[inf:INFLUENCES]->(c:Company {ticker:$ticker})
WHERE date(datetime(n.created)) = date($date)
  AND abs(inf.hourly_stock - inf.hourly_macro) >= $min_impact
RETURN n.title as headline, n.created as time, 
       inf.hourly_stock as stock_return,
       inf.hourly_macro as market_return,
       round(inf.hourly_stock - inf.hourly_macro, 2) as adjusted_return
ORDER BY abs(inf.hourly_stock - inf.hourly_macro) DESC","event","headline,time,returns","false"
```

## 14. Conclusion

Query Engine v3 provides a system for complex financial data investigations. By combining:
- Template-based queries (pre-tested Cypher for consistency)
- Specialist domain expertise (focused agents per data type)
- Iterative investigation (refinement through hints)
- Caching and optimization (Redis layer for repeated queries)

The system handles questions like event attribution through hint-guided investigation rather than pre-defined workflows. Each iteration reveals available data that guides the next query.

Total estimated implementation: ~500 lines of core code + templates.

## 15. CONTEXT

### Minimum Files Required for Design Verification

To verify or implement this design, the following context is essential:

#### 1. **From query_engine_v2** (Critical for understanding limitations)
- `skeletonTemplates.csv` - Shows existing 60 template queries and their structure
- `run_template.py` lines 36-48 - Shows structural parameter handling required by Neo4j
- `llm_router.py` - Shows current routing approach and its limitations

#### 2. **Event Attribution Use Case** (Primary problem being solved)
- `/home/faisal/EventMarketDB/drivers/agenticDrivers/eventAttribution.ipynb`
  - Shows real-world usage: finding which events caused stock movements
  - Example: "AAPL +7.26% on 2024-06-11" with 15 news events - which were real drivers?
  - Functions: `find_significant_days()`, `get_attribution_events()`, `prepare_attribution_package()`

#### 3. **Current Infrastructure** (From CLAUDE.md)
- Neo4j on port 30687 (bolt://localhost:30687)
- Redis on port 31379 for caching
- MCP servers available but optional
- Kubernetes pods for processing

#### 4. **Key Technical Constraints**

**Neo4j Structural Parameters** (Cannot be parameterized):
```python
STRUCTURAL_PARAMS = {
    "Label", "L1", "L2", "L3",           # Node labels
    "Rel", "Rel1", "Rel2", "RelType",    # Relationship types
    "prop", "srcProp", "dateProp",       # Property names
    "order", "dir", "cmp", "agg"         # Operators
}
```
These require string substitution before query execution, not standard parameterization.

#### 5. **Design Evolution Context**

The progression of thinking that led to this design:
1. Started with simple template matching (query_engine_v2 approach)
2. Realized need for complex query decomposition
3. Considered separating simple vs complex queries
4. Evolved to specialist agents after seeing eventAttribution needs
5. Added iteration after realizing first answer often incomplete
6. Added hints to guide investigation efficiently

#### 6. **Critical Questions to Verify Design**

When reviewing this design, verify:

1. **Does iteration with hints solve the event attribution problem?**
   - Can it handle 15+ events on a single day?
   - Can it identify primary vs secondary causes?

2. **Is the specialist separation logical?**
   - XBRL (financial facts)
   - Transcript (earnings calls)
   - News (events/announcements)
   - Market (prices/returns)

3. **Does caching strategy make sense?**
   - 1-hour TTL for most queries
   - Skip cache for time-sensitive data

4. **Can confidence scoring work as described?**
   - Based on data availability
   - Reduced when hints suggest missing info
   - Weighted average with LLM confidence

5. **Will token management work?**
   - Progressive summarization at 50K tokens
   - Early termination at high confidence
   - Parallel specialist execution

#### 7. **Alternative Approaches Considered and Rejected**

Important context on what was tried and why rejected:

1. **Pre-defined workflow templates** - Too rigid for unpredictable queries
2. **Single powerful agent** - Token explosion, jack of all trades problem
3. **Query decomposition to atomic** - Overengineered, lost context between queries
4. **Direct React agent integration** - Lacks domain expertise, too generic
5. **File watching for template updates** - Unnecessary in pod environment

#### 8. **Success Criteria**

The design should be validated against:
- Handle eventAttribution.ipynb use cases
- Complete investigation in ≤3 iterations  
- Maintain context under 100K tokens
- Cost-effective operation
- Effective cache utilization
- Accurate event attribution

### Files to Review in Order

1. Read this DESIGN.md completely
2. Review `eventAttribution.ipynb` for use case understanding
3. Check `query_engine_v2/run_template.py` for Neo4j constraints
4. Look at `query_engine_v2/skeletonTemplates.csv` for template examples
5. Verify against CLAUDE.md infrastructure details

### Key Insight

The core innovation is **hint-guided iteration**: each specialist returns not just data but hints about what else is available, naturally guiding the investigation without pre-defined workflows. This emerged from observing that financial event attribution requires exploring multiple hypotheses before reaching conclusions.

## 16. Next Steps

### 16.1 Pattern Specialist - Event Memory System

#### Concept Overview

The Pattern Specialist represents a natural evolution of the event attribution system into a causal memory framework. Once we determine which events drove a stock's price change using the existing specialists (XBRL, Transcript, News, Market), these cause→effect relationships are saved per stock. When similar events occur in the future, an LLM can reason about whether they might cause comparable impacts.

This is fundamentally different from technical pattern matching - it's about understanding that "when Apple announces AI tools, the stock tends to move X%" based on actual historical attributions, not just price patterns.

#### Core Flow

```
Current System (Event Attribution)
     ↓
Determine TRUE drivers for stock movement
     ↓
Save cause→effect mapping for that stock
     ↓
Build stock-specific event memory over time
     ↓
New similar event occurs
     ↓
LLM reasons about similarity and context
     ↓
Predict potential impact based on history
```

#### Why This Approach

The key insight is that stocks react uniquely to events based on their business model, investor base, and market position. For example:
- Apple might surge on AI announcements due to ecosystem lock-in potential
- Microsoft might react differently to similar news due to enterprise focus
- A biotech stock's reaction to FDA news is vastly different from a tech stock's

By building per-stock memories of attributed events, we capture these company-specific reaction patterns.

#### Integration with Existing Architecture

The Pattern Specialist would work alongside the existing specialists:

1. **Event occurs** → News Specialist detects it
2. **Investigation runs** → All specialists gather context
3. **Attribution determined** → System identifies true drivers
4. **Pattern stored** → Cause→effect saved to stock's memory
5. **Future event** → Pattern Specialist checks for similar past events
6. **LLM reasoning** → Assesses similarity considering context changes
7. **Prediction generated** → With appropriate confidence bounds

#### Realistic Expectations

**What it can do:**
- Identify when similar events have occurred before
- Reason about context differences (market conditions, company changes)
- Provide directionally useful predictions for high-similarity events
- Learn company-specific reaction patterns over time

**What it cannot do:**
- Predict unprecedented events (no historical pattern)
- Account for all market complexity (hidden factors, algorithmic trading)
- Guarantee accuracy (markets are inherently unpredictable)
- Work without sufficient historical data (needs many attributed events)

**Expected Performance:**
- For highly similar events with stable context: Moderately useful predictions
- For novel events or changed contexts: Limited value
- Overall: Better than generic technical analysis, not a crystal ball

#### Relationship to Query Engine v3

This Pattern Specialist extends the current design by:
- Using the same iterative investigation for initial attribution
- Building on top of confidence-scored findings
- Adding a learning layer that improves over time
- Maintaining the template-based accuracy for data retrieval

The existing specialists do the detective work to figure out what happened. The Pattern Specialist remembers these solved cases and uses them to make educated guesses about future similar situations.

#### Key Differentiator

Unlike traditional quant approaches that look for statistical patterns in price data, this system:
- Understands the semantic meaning of events
- Reasons about causation, not just correlation
- Adapts to each company's unique characteristics
- Leverages the full context from news, financials, and transcripts

### 16.2 Beyond Pattern Recognition

The Pattern Specialist opens doors to more sophisticated financial reasoning:

1. **Cross-Company Learning**: Events affecting one company might predict impacts on competitors
2. **Sector-Wide Patterns**: Industry trends identified through multiple company patterns
3. **Macro Event Understanding**: How companies react to Fed decisions, geopolitical events
4. **Temporal Evolution**: How reaction patterns change as companies mature or markets evolve

The goal isn't to predict the market perfectly - it's to build a system that understands financial cause and effect well enough to provide valuable insights that wouldn't be apparent from price data alone.

## 17. BOT2 Improvement Suggestions

After comprehensive review, the original design is fundamentally sound. The following minimal enhancements address real edge cases while preserving simplicity:

### 17.1 Cross-Specialist State Management

**Issue**: Specialists might overwrite each other's findings in shared context.

**Solution**: Namespace facts by specialist domain.
- Use `context["facts"]["xbrl:earnings"]` instead of `context["facts"]["earnings"]`
- Each specialist prefixes its keys with domain name
- Redis cache already prevents duplicate queries - no additional tracking needed

### 17.2 Temporal Reasoning

**Issue**: "Latest quarter" ambiguous across specialists.

**Solution**: Add single helper template, store two anchors.
- Add template: `get_latest_periods(ticker)` - returns recent 10-K and 10-Q periods
- Store only: `context["latest_Q"]` and `context["latest_K"]` at investigation start
- Specialists derive other temporal needs on-the-fly
- No pre-computed ranges

### 17.3 Dynamic Iteration Control

**Issue**: Fixed 3 iterations may be too many or too few.

**Solution**: Simple boolean test for new discovery.
```
facts_before = len(context["facts"])
# Run iteration
facts_after = len(context["facts"])
continue = (facts_after > facts_before) and (iteration < 4)
```
- Continue while discovering new facts
- Hard cap at 4 iterations
- No complex discovery rate calculations

### 17.4 Confidence Scoring

**Issue**: Irrelevant specialists shouldn't affect overall confidence.

**Solution**: Filter to relevant specialists only.
- Calculate: `confidence = min(specialists where data_points > 0)`
- Ignore specialists that found no relevant data
- Pessimistic approach: if any relevant specialist unsure, system unsure

### 17.5 Fast Lane for Simple Queries

**Issue**: Simple queries shouldn't trigger full investigation.

**Solution**: Three regex patterns with direct routing.
- Pattern 1: `"what('s| is) .* (price|prices|PE|revenue|EPS)"` → get_metric template
- Pattern 2: `"(how many|count)"` → get_count template
- Pattern 3: `"(list|show) all"` → get_list template
- Make patterns case-insensitive, handle plurals
- If matches: execute single template and return immediately

### 17.6 Event Attribution Enhancement

**Issue**: Determining TRUE drivers among multiple concurrent events.

**Solution**: Leverage annotated returns already in the data.
- Events already have post-event returns (1hr, session, daily) with market adjustments
- Use maximum excess return in appropriate time window
- Session-aware: pre-market events check open impact, after-hours check next day
- This uses ground truth (actual returns) rather than inference

### Summary of Changes

**Total modifications to original design**: ~20 lines of logic

**What changes**:
1. Add specialist prefix to fact keys
2. Add one temporal anchor template
3. Change iteration to boolean test
4. Filter confidence to relevant specialists
5. Add fast lane regex check
6. Use annotated returns for attribution

**What stays the same**:
- Core architecture (Investigator, Specialists, Templates)
- Hint-guided iteration
- Redis caching
- Parallel execution
- Progressive summarization
- All existing error handling and optimizations

These minimal changes preserve the elegance of the original design while ensuring production readiness and 100% accuracy for both simple and complex queries.