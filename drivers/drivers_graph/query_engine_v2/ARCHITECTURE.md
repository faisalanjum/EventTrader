# Query Engine Architecture - Visual Guide

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER QUESTION                           │
│                   "Show me Apple's revenue"                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LLM ROUTER (GPT-4)                        │
│                                                                  │
│  System Prompt: "You can only output JSON with these intents:   │
│  - fact_lookup                                                   │
│  - compare_two_entities_metric                                   │
│  - entity_list                                                   │
│  - ... (57 more templates)                                       │
│  - unknown (if no match)"                                        │
│                                                                  │
│  Output: {"intent": "fact_lookup",                               │
│          "params": {"ticker": "AAPL",                            │
│                    "form": "10-K",                               │
│                    "qname": "us-gaap:Revenue"}}                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TEMPLATE EXECUTOR                           │
│                                                                  │
│  1. Load template from library:                                  │
│     templates["fact_lookup"] = {                                 │
│       "cypher": "MATCH (c:Company {ticker:$ticker})..."          │
│       "params": ["ticker", "form", "qname"]                     │
│     }                                                            │
│                                                                  │
│  2. Validate all params present ✓                                │
│                                                                  │
│  3. Replace structural elements:                                 │
│     $Label → Company, $Rel → HAS_FACT                            │
│                                                                  │
│  4. Execute with parameters:                                     │
│     neo4j.run(cypher, {ticker: "AAPL", ...})                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                          NEO4J DATABASE                          │
│                                                                  │
│  🔵 Company ──HAS_REPORT──> 📄 Report                            │
│       │                          │                               │
│       │                          └──HAS_XBRL──> 📊 XBRLNode      │
│       │                                              │           │
│       └──────────HAS_FACT────────────────────> 💰 Fact          │
│                                                                  │
│  Returns: [{revenue: "$394.3B", date: "2023-09-30"}]            │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Unknown Query Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER QUESTION                           │
│                      "Who owns unicorns?"                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LLM ROUTER (GPT-4)                        │
│                                                                  │
│  Thinks: "Hmm, no template for ownership queries..."             │
│                                                                  │
│  Output: {"intent": "unknown",                                   │
│          "params": {},                                           │
│          "reason": "No template for ownership queries"}          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         LOGGING SYSTEM                           │
│                                                                  │
│  📝 unknown_queries.log:                                         │
│  2024-01-20T10:15:23 | Who owns unicorns? | No ownership...     │
│                                                                  │
│  Response to user:                                               │
│  "❓ Unknown query type                                          │
│   📝 Reason: No template for ownership queries                   │
│   💡 This query type needs a new template to be added.           │
│   📋 Query logged for future template development"               │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DEVELOPER ACTION                            │
│                                                                  │
│  1. Check unknown_queries.log                                    │
│  2. Design ownership query in Neo4j Browser                      │
│  3. Add to skeletonTemplates.csv:                               │
│     "company_ownership,ticker,limit,Shows company ownership,     │
│      MATCH (c:Company {ticker:$ticker})<-[:OWNS]-(o:Owner)..."  │
│  4. Run: python update_templates.py                              │
│  5. Test: python query_cli.py                                    │
│     > Who owns Apple?                                            │
│     ✅ Template: company_ownership                               │
└─────────────────────────────────────────────────────────────────┘
```

## 📂 Data Flow Through Files

```
skeletonTemplates.csv (Human editable)
         │
         │ python load_skeletons.py
         ▼
template_library.json (Machine readable)
         │
         ├──────────────────────┐
         │                      │
         ▼                      ▼
generate_router_prompt.py    run_template.py
         │                      │
         ▼                      │
router_prompt.txt               │
         │                      │
         ▼                      │
    llm_router.py ──────────────┘
         │
         ▼
    query_cli.py (User interface)
```

## 🛡️ Safety Guarantees

### What CAN Happen ✅
- Pre-written queries execute exactly as tested
- Parameters get safely injected
- Unknown queries get logged
- Fallback queries run if no results

### What CAN'T Happen ❌
- LLM writes arbitrary Cypher (it only outputs template names)
- SQL injection (parameters are sanitized by Neo4j driver)
- Infinite loops (all queries have LIMIT)
- Schema damage (only SELECT queries, no mutations)

## 🎯 Key Design Principles

1. **Separation of Concerns**
   - LLM: Intent classification only
   - Templates: Query logic
   - Executor: Parameter handling
   - Logger: Improvement tracking

2. **Fail Safe, Not Silent**
   - Unknown → Log & inform user
   - No results → Try recovery template
   - Error → Clear error message

3. **Continuous Improvement**
   - Every "unknown" is an opportunity
   - Templates grow organically
   - System gets smarter over time

4. **Developer Friendly**
   - One CSV to edit
   - One command to update
   - Clear logs to review
   - Simple testing CLI