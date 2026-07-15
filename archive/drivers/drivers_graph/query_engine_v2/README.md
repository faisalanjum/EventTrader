# Neo4j Query Engine v2 - Complete Guide

## 🎯 What This Is (In Simple Terms)

Think of this as a **smart translator** that converts your questions into database queries:
- You ask: "Show me Apple's revenue"  
- System finds the right pre-written query template
- Executes it safely against Neo4j
- Returns results

**The key insight**: The AI never writes database queries. It only picks from a menu of pre-tested queries. This makes it 100% safe.

## 🏗️ How It Works (Step by Step)

```
1. You type a question in English
   ↓
2. OpenAI GPT looks at your question
   ↓
3. GPT outputs: {"intent": "fact_lookup", "params": {"ticker": "AAPL", ...}}
   ↓
4. System looks up "fact_lookup" in template library
   ↓
5. Fills in the parameters (AAPL, etc.)
   ↓
6. Runs the pre-written Cypher query
   ↓
7. You get results
```

### What Happens When No Template Matches?

```
1. You ask: "Who owns unicorns?"
   ↓
2. GPT outputs: {"intent": "unknown", "reason": "No ownership queries"}
   ↓
3. System logs this to unknown_queries.log
   ↓
4. You get a polite message saying we need to add this template
   ↓
5. Developer later adds a new template for ownership queries
```

## 📁 File Structure Explained

```
query_engine_v2/
├── skeletonTemplates.csv          # The master list of all queries (CSV format)
├── templates/
│   └── template_library.json      # Same queries in JSON (auto-generated)
├── load_skeletons.py              # Converts CSV → JSON
├── update_templates.py            # Updates everything when you change CSV
├── generate_router_prompt.py      # Creates instructions for GPT
├── router_prompt.txt              # The instructions GPT uses
├── llm_router.py                  # The brain - talks to OpenAI
├── run_template.py                # Executes queries against Neo4j
├── query_cli.py                   # Command-line interface
├── unknown_queries.log            # Queries we couldn't handle (for improvement)
└── README.md                      # This file
```

## 🔧 Template Format - Complete Guide

Each template in `skeletonTemplates.csv` has 4 columns:

### 1. Name (Template ID)
- **Format**: lowercase_with_underscores
- **Examples**: `fact_lookup`, `compare_two_entities_metric`
- **Rules**: 
  - Must be unique
  - Use descriptive names
  - No spaces or special characters

### 2. Key Props (Parameters)
- **Format**: comma-separated list
- **Examples**: `ticker, form, qname` or `from, to, limit`
- **Common Parameters**:
  - `ticker` - Company stock symbol (AAPL, MSFT, etc.)
  - `form` - SEC form type (10-K, 10-Q, 8-K)
  - `qname` - GAAP concept name (us-gaap:Revenue)
  - `from`, `to` - Date range in YYYY-MM-DD format
  - `limit` - Maximum results to return
  - `days` - Number of days (for recent queries)
  - `Label` - Neo4j node type (Company, Report, News)
  - `prop` - Property name to search/filter
  - `value` - Value to match
  - `index` - Full-text index name
  - `order` - Sort order (ASC, DESC)

### 3. Comment (Description)
- **Format**: Brief human-readable description
- **Examples**: 
  - "Compare metric for two tickers"
  - "Recent news articles for a company"
- **Purpose**: Helps GPT understand when to use this template

### 4. Cypher (The Query)
- **Format**: Valid Neo4j Cypher query with $parameters
- **Example**:
  ```cypher
  MATCH (c:Company {ticker:$ticker})
  RETURN c.name, c.mkt_cap
  LIMIT $limit
  ```
- **Parameter Rules**:
  - Use `$param` for values Neo4j can parameterize
  - Use `$Label`, `$Rel` etc. for structural elements (these get string-replaced)

## 📝 Adding New Templates - Step by Step

### Scenario: Users keep asking "What companies are in the healthcare sector?"

#### Step 1: Check unknown_queries.log
```
2024-01-15T10:23:45 | What healthcare companies do you have? | No template for sector filtering
2024-01-15T14:11:22 | Show me all healthcare stocks | No template for sector filtering
```

#### Step 2: Write the Cypher Query
First, test in Neo4j Browser:
```cypher
MATCH (c:Company {sector: 'Healthcare'})
RETURN c.ticker, c.name, c.mkt_cap
ORDER BY c.mkt_cap DESC
LIMIT 20
```

#### Step 3: Add to skeletonTemplates.csv
Open the CSV and add a new row:
```csv
companies_by_sector,"sector, limit",List companies in a specific sector,"MATCH (c:Company {sector:$sector}) RETURN c.ticker, c.name, c.mkt_cap ORDER BY c.mkt_cap DESC LIMIT $limit"
```

#### Step 4: Update Everything
```bash
python update_templates.py
```

This automatically:
- Converts CSV to JSON
- Updates the GPT prompt with the new template
- Makes it immediately available

#### Step 5: Test It
```bash
python query_cli.py
> Show me healthcare companies
✅ Template: companies_by_sector
📊 Results: 20 rows
```

## 🎨 Common Template Patterns

### 1. Entity Listing
```csv
list_all_X,"limit",List all X entities,"MATCH (n:X) RETURN n LIMIT $limit"
```

### 2. Property Search
```csv
find_X_by_Y,"Y_value, limit",Find X where Y equals value,"MATCH (n:X {Y:$Y_value}) RETURN n LIMIT $limit"
```

### 3. Relationship Traversal
```csv
X_to_Y,"x_id, limit",Find Y connected to X,"MATCH (x:X {id:$x_id})-[:RELATES_TO]->(y:Y) RETURN y LIMIT $limit"
```

### 4. Time-Based Queries
```csv
recent_X,"days, limit",Recent X within N days,"MATCH (x:X) WHERE x.created > datetime() - duration({days:$days}) RETURN x ORDER BY x.created DESC LIMIT $limit"
```

### 5. Aggregations
```csv
count_X_by_Y,"",Count X grouped by Y,"MATCH (x:X) RETURN x.Y as category, COUNT(x) as count ORDER BY count DESC"
```

## 🚨 Important Rules for Templates

### DO ✅
- Test every query in Neo4j Browser first
- Use descriptive template names
- Include appropriate LIMIT clauses
- Use parameters for all variable values
- Add comments explaining what the query does

### DON'T ❌
- Don't use dynamic property names (Neo4j limitation)
- Don't create overly complex queries (break into multiple templates)
- Don't forget to escape special characters in CSV
- Don't use parameters for Labels or Relationship types (use string replacement)

## 🔍 Debugging Templates

### Query Returns No Results?
1. Check if parameters are correct
2. Look at recovery logic in `run_template.py`
3. Test the exact query in Neo4j Browser

### GPT Picks Wrong Template?
1. Update the comment in CSV to be more specific
2. Check if template name is descriptive enough
3. Look for conflicting templates with similar purposes

### Parameter Errors?
1. Verify parameter names match exactly in CSV and Cypher
2. Check if you need string replacement (Label, Rel) vs parameters
3. Ensure date formats are YYYY-MM-DD

## 📊 Parameter Types Reference

| Parameter | Type | Example | Used For |
|-----------|------|---------|----------|
| ticker | String | "AAPL" | Company stock symbol |
| form | String | "10-K" | SEC form type |
| qname | String | "us-gaap:Revenue" | XBRL concept name |
| from/to | Date | "2024-01-01" | Date ranges |
| limit | Integer | 10 | Result count |
| days | Integer | 30 | Recent time windows |
| Label | String | "Company" | Neo4j node labels |
| Rel | String | "HAS_PRICE" | Relationship types |
| prop | String | "name" | Property names |
| value | Any | "Apple" | Property values |
| order | String | "DESC" | Sort direction |
| industry | String | "Technology" | Industry name |
| sector | String | "Healthcare" | Sector name |

## 🚀 Quick Start for New Developers

1. **First Time Setup**:
   ```bash
   pip install langchain-openai neo4j
   export OPENAI_API_KEY='your-key'
   ```

2. **Run Interactive CLI**:
   ```bash
   python query_cli.py
   ```

3. **Check What Users Are Asking For**:
   ```bash
   cat unknown_queries.log
   ```

4. **Add New Template**:
   - Edit `skeletonTemplates.csv`
   - Run `python update_templates.py`
   - Test with `python query_cli.py`

## 💡 Pro Tips

1. **Start Simple**: Begin with basic queries, add complexity later
2. **Use Existing Patterns**: Copy similar templates and modify
3. **Test Everything**: Every query should work in Neo4j Browser first
4. **Think Like Users**: Name templates based on what users ask for
5. **Document Well**: Good comments help GPT pick the right template

## 🔄 Workflow Summary

```
User asks question
    ↓
If it works → Great! ✅
    ↓
If "unknown" → Check log → Add template → Update → Test → Ship 🚀
```

That's it! The system grows smarter with each new template you add.