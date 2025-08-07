
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

---

## Critical Findings from Deep Analysis

### Content Node Types in 8-Ks
1. **ExtractedSectionContent**: 48,541 instances, avg 1.4KB (parsed sections)
2. **ExhibitContent**: 19,604 instances, avg 49.7KB (attached documents, 35x larger!)
3. **FilingTextContent**: 459 instances, avg 695KB (fallback for parsing failures)

### Key Discovery: Data Location Varies by Event Type
| Event Type | Count | Have Exhibits | Primary Data Location |
|------------|-------|---------------|----------------------|
| Results of Operations | 8,027 | 93.3% | EX-99.1 press release |
| Acquisitions | 164 | 83.5% | Both section + exhibit |
| Material Agreements | 2,399 | 68.9% | Exhibit (EX-10.x) |
| Personnel Changes | 4,830 | 56.9% | Section itself |
| Material Impairments | 49 | 34.7% | Section itself |
| Voting Results | 2,254 | 20.6% | Section only |

**Critical Insight**: 33.5% of 8-Ks have NO exhibits - data only in sections!

### Optimal Strategy: Three-Bucket Approach

#### Bucket 1: Section-Primary (Extract Section Only)
- Voting Results, Material Impairments, Personnel Changes
- ~7,100 sections with data directly embedded
- Cost: $50

#### Bucket 2: Exhibit-Primary (Skip Section, Extract Exhibit)  
- Results of Operations → EX-99.1 press releases
- ~7,500 exhibits with rich financial data
- Cost: $150

#### Bucket 3: Hybrid (Extract Both & Merge)
- Acquisitions, Material Agreements
- ~2,500 events needing both sources
- Cost: $50

### Source-Linked Architecture (Key Innovation)
```cypher
// Every extracted node traces back to source
(Impairment {amount: 162500000})
    -[:EXTRACTED_FROM]->(ExtractedSectionContent {id: 'esc_123'})
    
// Enables surgical text access when needed (not broad search)
MATCH (i:Impairment)-[:EXTRACTED_FROM]->(source)
WHERE i.amount > 100000000
RETURN i.amount, source.content  // Direct traversal, no search
```

### Coverage Analysis
- **With sections only**: 45% coverage (miss earnings data)
- **With exhibits only**: 66.5% coverage (miss impairments, votes)
- **With both + smart routing**: 99.9% coverage
- **Text search elimination**: 99.9% (only 0.1% truly novel keywords)

### XBRL Linkage Enhancement via Company Context
- Load company's XBRL taxonomy from their 10-K/10-Q
- Use their specific Members (executives, segments, acquisitions)
- Result: 81% linkage (vs 45% without context)
- Example: "SolarCity" → tsla:SolarCityMember (already exists!)

### Implementation Notes
- **Single specialist** with routing logic (not multiple sub-agents)
- **Deduplication** needed when both section + exhibit extracted
- **Boilerplate filtering** critical (~60% of section text is legal disclaimers)



### Guidance

 - Maybe can link guidnace for each type of section etc. above
 - use sec-api to search for guidance from 10-K/10-Q seperately to make a comprehensive set

#### Other report types like 425, 6-k, SC TO-I, SCHEDULE 13D, SC 14D9
 - ignore or handle with simple regex


  extraction_priority = {
      "MUST EXTRACT": [
          "8-K",        # 22,495 reports - material events
      ],

      "ALREADY STRUCTURED": [
          "10-K",       # 2,091 reports - have XBRL
          "10-Q",       # 5,383 reports - have XBRL
      ],

      "SKIP (Low Value)": [
          "425",        # 711 - merger comms, mostly narrative
          "6-K",        # 26 - foreign, no standard
          "SC TO-I",    # 8 - too few
          "SC 14D9",    # 4 - too few
      ],

      "MAYBE (If Needed)": [
          "SCHEDULE 13D",  # 276 - ownership, simple facts
      ]
  }
