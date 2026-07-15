Following is a **broad list of considerations** which we still have to deliberate to get a final structure or PRD before starting actual coding. 

1. Determine all specialist agents
    - Provide @drivers/docs/NEO4J_SCHEMA_v3.md as well as other related documents to claude and ask it to determine what agents we need, how many and with what exact responsibilities making sure not to burden a single analyst with too much responsibility and also let claude first understand the database before making that determination

2. For each agent, make sure to create almost all queries but make these as basic lego blocks as possible so any complex query can be made by combing these

3. We need a way to also provide the react agent with another tool that uses similarity search to retrive complex queries so that we do not waste tokens. and these queries can be stored in redis upto say a limit of 1000 or so indefinetely. 
    - Importantly we need a mechanism to store only successfull COMPLEX queries which can be common (not specilist specific) and also we can parametrize them or create proper labels/descriptions with parametr placeholders rather than specifics to enable similarity search - nothing is finalize yet. 

**To be determined**
4. - if our current structure be able to breakdown complex queries into simpoler ones, route it to individual specilists and then send back.
5. - should sec-api keyword search tool as well as perplexity sec api as well as generic online search be made part of this system or should be linked to another bot since ideally these ones should be restricted to just the database? 

**Reuse whats already present in @driver folder across different projects so don't reinvent the wheel**
**Note**
 - We already have a very detailed list of questions
 - we already created detailed similarity search, redis integration etc keeping all nuances in mind
 - Infact start by first understanding all features already implemented in this folder so we have a strong basis to begin with

## 8-K Specialist Enhancement with LangExtract

### Context
Analysis of 22,495 8-K reports shows 48,541 ExtractedSectionContent instances across 26 section types. Currently these are text blobs requiring regex/text search at query time.

### Extraction Opportunity
- **Extractable facts**: ~45% of 8-K text contains financial amounts, dates, entity names
- **XBRL linkage**: 81% of extracted entities can map to XBRL concepts when using company-specific taxonomies from their 10-K/10-Q filings (772 of 794 companies have these)
- **Section patterns**: Different section types (MaterialImpairments, DepartureofDirectors, etc.) follow consistent SEC-mandated structures

### Proposed Approach
1. Extract facts from 8-K sections into structured nodes (Amount, Date, Person, Company)
2. Link to company's existing XBRL taxonomy members where applicable
3. Preserve remaining context as properties on nodes
4. Mark boilerplate/references for filtering

### Cost Estimate
- One-time historical: ~$290 (Gemini 2.5 Pro for 68M tokens)
- Ongoing: ~$438/year for new filings

### What Needs Research
- **Exhibit parsing**: 97% of ResultsofOperations sections just reference EX-99.1 exhibits - should we parse exhibits (avg 23KB) or just sections (avg 1KB)?
- **Extraction schemas**: Need to define specific extraction patterns for each of 26 section types
- **Company taxonomy loading**: Efficient method to load/cache company-specific XBRL taxonomies for context
- **Incremental updates**: Strategy for processing new 8-Ks daily without reprocessing

### Expected Benefit
- Query performance: 100x faster than text search
- Enables aggregation queries impossible with text
- 90% of queries answerable from extracted nodes, 10% fallback to original text





