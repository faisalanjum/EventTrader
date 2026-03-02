# Member Matching Fix — Move from LLM to Code

**Date**: 2026-03-02
**Issues**: #61, #62
**Status**: Proposal — empirically validated, ready to implement

---

## Problem Statement

`MAPS_TO_MEMBER` edges are missing on segment-qualified GuidanceUpdate nodes. 18 segment items exist across AAPL/IBM/NTAP — 3 have no member edge. Root cause: member matching is 100% LLM-driven with no code fallback. The LLM non-deterministically fails to match segment text to XBRL member labels.

---

## Root Cause (Empirically Proven)

### Architectural asymmetry: Concepts vs Members

**Concept matching (works 100%):**
```
LLM writes text string → xbrl_qname: "us-gaap:Revenues"
         ↓
Code resolves → MATCH (con:Concept {qname: $xbrl_qname})
         ↓
Code creates edge → MERGE (gu)-[:MAPS_TO_CONCEPT]->(con)
```
Plus code-level concept inheritance (`guidance_write_cli.py:197-205`): if Revenue(Total) has a qname, all Revenue(segment) items get it too.

**Member matching (broken):**
```
LLM receives large cache (63KB for NTAP, 158 entries)
         ↓
LLM must text-match "Public Cloud" against "PublicCloud" labels
         ↓
LLM must extract exact u_id: "1002047:http://www.netapp.com/20230127:ntap:PublicCloudMember"
         ↓
LLM writes u_id into member_u_ids array (or [] on failure)
         ↓
Code blindly passes through → MATCH (m:Member {u_id: member_u_id})
```

The LLM does ALL the work for members. The code does NONE.

### Proof: LLM matching is non-deterministic

**Same CamelCase pattern — different outcomes:**

| Company | Segment Text | Member Label | LLM Result |
|---------|-------------|-------------|------------|
| IBM | Transaction Processing | TransactionProcessing | MATCHED |
| AAPL | Wearables, Home and Accessories | WearablesHomeandAccessories | MATCHED |
| **NTAP** | **Public Cloud** | **PublicCloud** | **FAILED** |
| **IBM** | **Red Hat** | **RedHat** | **FAILED (different cause)** |

IBM "Transaction Processing" → "TransactionProcessing" is structurally identical to NTAP "Public Cloud" → "PublicCloud". Yet IBM succeeded and NTAP failed.

### Cache size is NOT the cause

- AAPL: 83 members → matching worked
- NTAP: 158 members → matching **failed**
- IBM: **451 members** → matching **worked** (except Red Hat)

IBM has 3× more members than NTAP yet its matching worked.

### Two distinct sub-causes proven

**Sub-cause A: LLM skipped matching (NTAP)**
- 2B cache contains `ntap:PublicCloudMember` (label: "PublicCloud", axis: srt:ProductOrServiceAxis, 22 usages)
- Agent received the data but set `member_u_ids: []`
- Confirmed: all 16 NTAP P1 items have `member_u_ids: []` in `/tmp/gu_NTAP_NTAP_2023-02-22T17.00.00-05.00.json`
- Items 7 and 14 have `segment: "Public Cloud"` with empty `member_u_ids`

**Sub-cause B: Member absent from 2B cache (IBM Red Hat)**
- `ibm:RedHatMember` (label: "RedHat") exists as a Member node in Neo4j
- But has **zero XBRL facts**: `MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member {qname: 'ibm:RedHatMember'}) RETURN count(f)` → 0
- 2B query discovers members through Context nodes (which only exist for members with facts)
- No facts → no Context → invisible to 2B → agent can't match what it never sees

### Where AAPL succeeded — and why it's not replicable

AAPL P1 JSON shows the LLM populated member_u_ids for 5 segment items:
```
Item 1: segment=iPhone      → IPhoneMember                        ✓
Item 2: segment=Mac          → MacMember                           ✓
Item 3: segment=iPad         → IPadMember                          ✓
Item 4: segment=WH&A         → WearablesHomeandAccessoriesMember   ✓ (creative!)
Item 5: segment=Services     → ServiceMember                       ✓
```

The WH&A match ("Wearables, Home and Accessories" → "WearablesHomeandAccessories") goes FAR beyond the spec's normalization rules. The LLM used common-sense reasoning. This cannot be relied upon — it's non-deterministic.

### Code path trace — zero code-level member matching exists

- `guidance_write_cli.py` lines 197-205: concept inheritance only (xbrl_qname propagation)
- `guidance_write_cli.py`: NO member matching code anywhere
- `guidance_writer.py` lines 357-367: blindly writes whatever `member_u_ids` the JSON provides
- `_build_member_query()`: `MATCH (m:Member {u_id: member_u_id})` — just creates edges from pre-resolved u_ids

### Spec ambiguity confirmed

SKILL.md §7 says: "Normalize both sides: lowercase, strip whitespace, remove tokens `member` and `segment`, light singularization"

"Strip whitespace" is ambiguous:
- Trim interpretation: "public cloud" (keeps internal space) ≠ "publiccloud"
- Remove-all interpretation: "publiccloud" = "publiccloud" → match

Even with remove-all, AAPL WH&A can't match ("wearables,homeandaccessory" ≠ "wearableshomeandaccessory" — comma). Yet the LLM matched it.

---

## Proposed Fix

### Architecture: Make members work like concepts

```
LLM writes segment text → segment: "Public Cloud"    (already does this)
         ↓
Code normalizes + matches → find Member by label
         ↓
Code populates member_u_ids
         ↓
Code creates edge → MERGE (gu)-[:MAPS_TO_MEMBER]->(m)
```

### Normalization function

Two operations, no hardcoded word lists:

```python
import re

def normalize_for_member_match(s):
    """Collapse to lowercase alphanumeric, strip XBRL suffixes, handle trailing-s plural."""
    s = re.sub(r'[^a-z0-9]', '', s.lower())       # strip ALL non-alphanumeric
    s = s.replace('member', '').replace('segment', '')  # strip XBRL suffixes
    if s.endswith('s'):
        s = s[:-1]                                   # strip trailing 's' (plural)
    return s
```

### Empirical test results (2026-03-02)

Tested against ALL 18 segment items across AAPL (1918 candidate members), IBM (2459), NTAP (2040):

| Method | Correct | New (fixes gaps) | False Positive | No Match |
|--------|---------|-------------------|---------------|----------|
| `exact` (normalize only) | 11/18 | 3/18 | **0/18** | 4/18 |
| **`trailing_s`** (normalize + strip trailing s) | **15/18** | **3/18** | **0/18** | **0/18** |
| `startswith` (fuzzy prefix) | 15/18 | 3/18 | **11/18** | 0/18 |

**`trailing_s` = 18/18 match rate, 0 false positives.**

The 4 items `exact` missed: all AAPL "Services" → `us-gaap:ServiceMember` (label "Service"). Plural mismatch.

The 3 "new match" items are exactly the 3 broken items this fix targets:
- NTAP Cloud Revenue (Public Cloud) → `ntap:PublicCloudMember`
- NTAP Gross Margin (Public Cloud) → `ntap:PublicCloudMember`
- IBM Revenue (Red Hat) → `ibm:RedHatMember`

`startswith` eliminated — produces 63 false positives for "Public Cloud" (matches CasinoMember, FutureMember, RetailMember, etc.)

### Every known segment ↔ member pair validated

```
normalize("Public Cloud")                      = "publiccloud"
normalize("PublicCloud") - strip member/segment = "publiccloud"     → MATCH ✓

normalize("Transaction Processing")            = "transactionprocessing"
normalize("TransactionProcessing")             = "transactionprocessing"  → MATCH ✓

normalize("Red Hat")                           = "redhat"
normalize("RedHat")                            = "redhat"           → MATCH ✓

normalize("Wearables, Home and Accessories")   = "wearableshomeandaccessories"
normalize("WearablesHomeandAccessories")       = "wearableshomeandaccessories"  → MATCH ✓

normalize("Services")                          = "services" → strip 's' → "service"
normalize("Service")                           = "service"  → strip 's' → "servic"
Wait — "service" → strip trailing 's' would give... no, the function checks endswith('s'):
  "services" ends with 's' → "service"
  "service" ends with 's' → ... no! "service" ends with 'e', not 's'.

Correction: normalize_for_member_match("Services"):
  re.sub → "services" → strip member/segment → "services" → endswith('s') → "service"
normalize_for_member_match("Service"):     [member label after strip_xbrl_suffix]
  re.sub → "service" → strip member/segment → "service" → endswith('e') → "service"
Both = "service" → MATCH ✓

normalize("iPhone")                            = "iphone"
normalize("IPhone")                            = "iphone"           → MATCH ✓

normalize("Mac")                               = "mac"
normalize("Mac")                               = "mac"              → MATCH ✓

normalize("iPad")                              = "ipad"
normalize("IPad")                              = "ipad"             → MATCH ✓
```

### Member cache: query ALL members, not just 2B

**Why**: 2B misses members with zero XBRL facts (IBM RedHatMember proven: 0 facts → 0 Contexts → invisible to 2B).

**How**: Query by company CIK prefix instead of going through Context:

```cypher
MATCH (m:Member)
WHERE m.u_id STARTS WITH $cik_unpadded OR m.u_id STARTS WITH $cik_padded
RETURN DISTINCT m.qname AS qname, m.label AS label,
       collect(DISTINCT m.u_id) AS u_ids
```

Handles CIK zero-padding mismatch (Company.cik = `0001002047`, Member.u_id starts with `1002047:`).

Also include shared us-gaap/srt members (e.g., `us-gaap:ServiceMember` for AAPL "Services"):

```cypher
MATCH (m:Member)
WHERE m.qname STARTS WITH 'us-gaap:' OR m.qname STARTS WITH 'srt:'
RETURN DISTINCT m.qname AS qname, m.label AS label,
       collect(DISTINCT m.u_id) AS u_ids
```

Member counts per company (direct query, unfiltered):
- AAPL: 383 company + 1535 shared = 1918 total
- IBM: 924 company + 1535 shared = 2459 total
- NTAP: 505 company + 1535 shared = 2040 total

All tested with **0 false positives** despite the large candidate sets.

### Ambiguity: multiple matches

"Public Cloud" matches both `ntap:PublicCloudMember` and `ntap:PublicCloudSegmentMember` (after stripping 'segment' suffix, both normalize to "publiccloud"). Both are valid members on relevant axes. Include ALL matches in `member_u_ids` — the spec allows 0..N member edges per GuidanceUpdate.

### Edge case: Segment-suffix members (747 distinct labels, 1087 qnames graph-wide)

**Status: SAFE — handled by `.replace('segment', '')`**

747 distinct Member labels end with "Segment" (e.g., `AmericasSegment`, `PublicCloudSegment`, `CorporateNonSegment`). The `strip_xbrl_suffix()` function strips 'segment' via `.replace('segment', '')`, which correctly removes this suffix:

- `PublicCloudSegment` → normalize → `"publiccloudsegment"` → replace → `"publiccloud"` → matches "Public Cloud" ✓
- `AmericasSegment` → normalize → `"americassegment"` → replace → `"americas"` → trailing_s → `"america"` → matches "Americas" ✓

**Mid-word occurrences**: 20 labels contain "segment" mid-word (e.g., `AdjustmentOfIntersegmentRevenues`, `AllOtherSubsegments`). The `.replace()` mangles these (`"adjustmentofinterrevenues"`) but this CANNOT cause false positives because:
1. Replace only runs on the member label side, not on segment text
2. Natural-language segment text (e.g., "Software", "Cloud") would never normalize to a mangled string
3. Empirically validated: 0 false positives across 1918-2459 candidates per company including all Segment-suffix members

**Why the earlier analysis flagged this**: Their normalizer did NOT strip 'segment'. Ours does.

### Where to put the code

`guidance_write_cli.py`, write-mode path, after concept inheritance (line 205), before `write_guidance_batch()` (line 231). ~20 lines.

**Placement rationale**: mirrors concept inheritance location. Only runs in write mode (needs Neo4j for member cache query). Dry-run stays offline — matches concept edge behavior (concept edges also only created in write mode).

**Guard conditions** (strictly additive, 0% regression risk):
1. Only fires when `member_u_ids` is empty/null
2. Only fires when `segment != 'Total'`
3. Never overwrites LLM-provided member_u_ids

### What changes in the LLM pipeline

1. `guidance-extract.md` Step 4 pt.5 (member match instruction): **remove or demote to optional hint**. Code handles it.
2. `SKILL.md` §7 member matching section: update to note code-level fallback
3. 2B cache in agent prompt: **can be removed** to save context tokens (code does matching now)
4. `member_u_ids` field in agent JSON: still supported (LLM can pre-populate if confident), but code fills in gaps

---

## Implementation Plan

1. Add `normalize_for_member_match()` to `guidance_ids.py`
2. Add member cache query + matching logic to `guidance_write_cli.py` (write-mode path)
3. Add tests for normalization function
4. Update agent prompts (remove/demote member matching from LLM responsibility)
5. Re-run NTAP extraction to verify fix (dry-run first)
6. Update issue tracker (#61, #62)

---

## Test script

Full test script at `/tmp/test_member_matching.py` — runs against live Neo4j, validates all 18 segment items against full member sets per company. Key assertions:
- 0 false positives
- 18/18 match rate with trailing_s method
- All 3 broken items (NTAP ×2, IBM ×1) get correct new matches

---

## Appendix: Raw data

### NTAP P1 JSON — items with segment != "Total"

```json
Item 7: {"label": "Cloud Revenue", "segment": "Public Cloud", "member_u_ids": []}
Item 14: {"label": "Gross Margin", "segment": "Public Cloud", "member_u_ids": []}
```
Source: `/tmp/gu_NTAP_NTAP_2023-02-22T17.00.00-05.00.json`

### AAPL P1 JSON — items where LLM DID match (for comparison)

```json
Item 1: {"label": "Revenue", "segment": "iPhone",      "member_u_ids": ["320193:...aapl:IPhoneMember"]}
Item 2: {"label": "Revenue", "segment": "Mac",          "member_u_ids": ["320193:...aapl:MacMember"]}
Item 3: {"label": "Revenue", "segment": "iPad",         "member_u_ids": ["320193:...aapl:IPadMember"]}
Item 4: {"label": "Revenue", "segment": "WH&A",         "member_u_ids": ["320193:...aapl:WearablesHomeandAccessoriesMember"]}
Item 5: {"label": "Revenue", "segment": "Services",     "member_u_ids": ["320193:...us-gaap:ServiceMember"]}
```
Source: `/tmp/gu_AAPL_AAPL_2023-11-03T17.00.00-04.00.json`

### IBM P1 JSON — mixed results

```json
Item 2: {"label": "Revenue", "segment": "Software",                "member_u_ids": ["51143:...ibm:SoftwareMember"]}        ✓
Item 3: {"label": "Revenue", "segment": "Red Hat",                 "member_u_ids": []}                                     ✗
Item 4: {"label": "Revenue", "segment": "Transaction Processing",  "member_u_ids": ["51143:...ibm:TransactionProcessingMember"]}  ✓
Item 5: {"label": "Revenue", "segment": "Infrastructure",          "member_u_ids": ["51143:...ibm:InfrastructureMember"]}   ✓
Item 9: {"label": "Revenue", "segment": "Automation",              "member_u_ids": ["51143:...ibm:AutomationMember"]}       ✓
Item 10:{"label": "Revenue", "segment": "Data",                    "member_u_ids": ["51143:...ibm:DataMember"]}             ✓
```
Source: `/tmp/gu_IBM_IBM_2025-07-23T17.00.00-04.00.json`

### Neo4j state — all MAPS_TO_MEMBER edges (15 total)

```
AAPL: IPhoneMember, MacMember, IPadMember, WearablesHomeandAccessoriesMember, ServiceMember (×4 transcripts)
IBM: TransactionProcessingMember, InfrastructureMember, SoftwareMember, AutomationMember, DataMember (×2 periods)
NTAP: 0 edges
```

### Member node properties (key fields)

```
ntap:PublicCloudMember:
  u_id: "1002047:http://www.netapp.com/20230127:ntap:PublicCloudMember"
  label: "PublicCloud"        ← CamelCase, no spaces
  qname: "ntap:PublicCloudMember"
  name: null                  ← always null
  axis: null                  ← not stored on Member node; derived from Context

aapl:IPhoneMember:
  u_id: "320193:http://www.apple.com/20221231:aapl:IPhoneMember"
  label: "IPhone"
  qname: "aapl:IPhoneMember"
  name: null
  axis: null

ibm:RedHatMember:
  u_id: "51143:http://www.ibm.com/20221231:ibm:RedHatMember"
  label: "RedHat"
  qname: "ibm:RedHatMember"
  ZERO XBRL facts → invisible to 2B query → never in agent cache
```

### IBM Red Hat — why 2B misses it

```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member {qname: 'ibm:RedHatMember'})
RETURN count(f)
→ 0
```

IBM does not break out Red Hat financials via XBRL dimensions in their SEC filings. The Member node exists from the taxonomy definition but has no associated facts. The 2B query discovers members through Context nodes, which only exist when facts use that member in a dimension. Zero facts → zero Contexts → invisible.

### 2B cache sizes

| Company | 2B members (Context-filtered) | ALL members (direct query) | Shared (us-gaap/srt) |
|---------|-------------------------------|----------------------------|----------------------|
| AAPL | 83 | 383 | 1535 |
| IBM | 451 | 924 | 1535 |
| NTAP | 158 | 505 | 1535 |
