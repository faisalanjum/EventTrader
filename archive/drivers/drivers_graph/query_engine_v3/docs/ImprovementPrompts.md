# Query Engine v3 - Design Review and Analysis Prompt

## Primary Task
Conduct a comprehensive technical review of the Query Engine v3 design document (DESIGN.md in this directory). Your goal is to first thoroughly understand the design, then evaluate its effectiveness for handling complex financial investigations.

## System Purpose
Query Engine v3 is designed to handle natural language queries about financial data with:

**Critical Requirements** (in priority order):
1. **100% accuracy for complex queries** - Must correctly handle multi-faceted investigations like:
   - **Guidance tracking & impact**: "Find all guidance for AAPL this quarter, show how it changed vs previous periods, and identify which guidance changes moved the stock price"
   - **Revenue trend analysis**: "Show revenue changes across all quarters starting from latest (system must identify latest), with stock price reactions to each earnings"
   - **True driver identification**: "Among 15 events on June 11 for AAPL (earnings, news, analyst reports), what was the TRUE driver of the 7% move and why?"
   - **Multi-period guidance evolution**: "Track how Apple's iPhone revenue guidance evolved over last 4 quarters and correlate with actual results"
   - **Complex attribution**: "Which specific metric surprise in the earnings (revenue, margins, guidance) caused the after-hours spike?"

2. **Efficient routing for simple queries** - Direct queries should bypass iteration when possible

## Essential Context

### What We're Building On
- **Current System**: query_engine_v2 has 60 working Cypher templates but lacks investigation capabilities
- **Infrastructure**: Neo4j (port 30687), Redis cache (31379), Kubernetes cluster
- **Integration Target**: Will be a tool within a larger LangGraph/React agent system

### Key Files to Reference
1. **This directory**: DESIGN.md (the main document to review)
2. **Parent directory**: `../query_engine_v2/` - Current implementation showing what works
3. **Use case**: `../../agenticDrivers/eventAttribution.ipynb` - Real attribution problem
4. **Infrastructure**: `../../../CLAUDE.md` - Kubernetes and database setup

## Review Structure

### Phase 1: Deep Understanding (Do This First)
Read the entire DESIGN.md and understand:

1. **Architecture Flow**
   - How does a query move through the system?
   - When does iteration happen vs single-pass?
   - How do specialists coordinate?

2. **Core Innovation**
   - What is "hint-guided iteration" and why is it valuable?
   - How do specialists provide hints for next steps?
   - Why is this better than pre-defined workflows?

3. **Technical Constraints**
   - Neo4j STRUCTURAL_PARAMS (Section 4.1, lines 67-79) - Labels, relationships, and property names require string substitution
   - Regular values CAN be parameterized (e.g., ticker='AAPL')
   - Token limits require progressive summarization at 50K+

### Phase 2: Critical Evaluation

#### A. Complex Query Handling
**Evaluate accuracy for complex investigations**:
- Can it track guidance changes across multiple quarters and identify which changes moved prices?
- Will it correctly identify the TRUE driver among 15-20 events on a single day?
- Can it correlate specific metric surprises (revenue beat, margin miss) with price movements?
- How does it determine "latest quarter" and work backwards through time series?
- Can it distinguish between correlation and causation in event attribution?

#### B. Specialist Design
**Evaluate the 4-specialist model** (XBRL, Transcript, News, Market):
- Is this the right division of expertise for complex investigations?
- How do specialists coordinate to avoid gaps in coverage?
- Do specialists provide actionable hints for iteration?

#### C. Iteration Mechanism for Complex Queries
**Critical for accuracy**:
- Is 3 iterations sufficient for complex multi-factor investigations?
- Does the confidence threshold (0.85) ensure accurate conclusions?
- How does hint-guided iteration prevent infinite loops?

#### D. Simple Query Routing
**Single concern**: Can simple queries bypass iteration and go directly to templates?

### Phase 3: Specific Technical Concerns

1. **Caching Strategy**
   - 1-hour TTL for financial data - appropriate?
   - Cache invalidation during market hours?
   - What about real-time vs historical queries?

2. **Confidence Scoring** (Section 4.2, lines 205-230)
   - Is the weighted average approach (60% data, 40% LLM) justified?
   - How do confidence scores propagate through iterations?
   - Will downstream systems trust these scores?

3. **Performance at Scale**
   - Parallel specialist execution - coordination overhead?
   - Redis bottlenecks with multiple concurrent investigations?
   - Token explosion with complex multi-day analyses?

4. **Pattern Specialist** (Section 16 - Future Enhancement)
   - Is the causal memory concept feasible?
   - Minimum viable dataset size for useful patterns?
   - How would this integrate without disrupting current flow?

## Key Questions to Answer

### For Complex Queries (Primary Focus)
1. Can it track guidance evolution across quarters and identify price-moving changes?
2. Will it correctly identify TRUE drivers vs coincidental events?
3. Can it figure out temporal context (e.g., "latest quarter") without being told?
4. How does it correlate specific metric surprises with price reactions?
5. Can it handle multi-step reasoning (guidance → expectation → surprise → price move)?

### For Simple Queries
1. Can they bypass iteration and go straight to templates?

### Implementation Readiness
1. What's missing from the design that would block implementation?
2. Are the code examples (Sections 4.2, 4.3) complete enough?
3. How are edge cases handled (timeouts, connection failures)?

## Deliverables

### 1. Understanding Confirmation
- Summarize the design in your own words (2-3 paragraphs)
- List the key innovations and why they matter
- Identify which problems this solves vs query_engine_v2

### 2. Critical Analysis
- **Strengths**: What works well and why?
- **Weaknesses**: What could fail or cause issues?
- **Gaps**: What's missing or unclear?

### 3. Improvement Recommendations
Focus on:
- **Temporal reasoning**: How the system identifies "latest" and works backwards
- **Causation vs correlation**: Methods to determine TRUE drivers
- **Guidance tracking**: Comparing guidance across time periods and to actuals
- **Price impact correlation**: Linking specific metrics to price movements
- **Simple query routing**: Direct path to bypass iteration when appropriate

### 4. Feasibility Assessment
- **Implementation difficulty**: 1-10 scale with justification
- **Maintenance burden**: How complex to maintain/extend?
- **Success probability**: Will this achieve its goals?

## Important Reminders

1. **Complex queries are the priority** - 100% accuracy for investigations is non-negotiable
2. **Understand before critiquing** - Ensure you grasp the design's intentions
3. **Think about production** - This handles real financial data with real money at stake
4. **Respect constraints** - Neo4j structural limitations are real and solved via string substitution
5. **Be specific** - Vague concerns aren't actionable; provide concrete examples

## Success Criteria for Your Review

Your review succeeds if:
1. You've validated the system can achieve 100% accuracy for complex investigations
2. You've confirmed simple queries can bypass unnecessary complexity
3. Someone could implement this system from your analysis + the design doc
4. You've identified any risks that could compromise accuracy
5. Your recommendations would improve accuracy or reduce complexity without sacrificing it

Begin by reading DESIGN.md completely, then structure your response according to the deliverables above.