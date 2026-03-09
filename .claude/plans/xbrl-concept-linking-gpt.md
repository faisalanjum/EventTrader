# Extraction Linking Review: XBRL Concept and Member Reliability

Date: 2026-03-09

## Scope

This note captures the findings, live-graph checks, reasoning, and recommended design for guidance extraction linkage to:

- XBRL concepts
- XBRL members

It was written under these constraints:

- No manual review step
- No separate post-processing phase
- Must be as close as possible to 100% recall and 100% precision

---

## Executive Summary

The core problem is not "how do we make the LLM choose better?".

The real problem is that the current system writes links to versioned XBRL nodes, while guidance is referring to logical business identities:

- concept identity
- member identity

Those are not the same as a specific taxonomy-year `Concept` node or `Member` node.

From first principles:

1. If the system stores links to versioned nodes as the source of truth, it will drift.
2. If the system uses fuzzy ranking among semantically similar concepts, it will eventually guess wrong.
3. If the system links derived metrics to "close enough" base concepts, precision is already lost.

The most reliable minimal design is:

1. Make concept truth be `xbrl_qname` only.
2. Make member truth be stable company-local member identity, not `member_u_id`.
3. Resolve both inline in the write path.
4. Emit links only for exact semantic matches.
5. Leave derived / non-exact metrics null by policy.

This is the closest possible design to 100% reliability without manual review.

---

## Bottom-Line Conclusion

Literal 100% automatic precision and 100% automatic recall is not achievable if the system is forced to:

- link every extracted metric
- link directly to taxonomy-version nodes
- make no abstentions

However, a 100%-precision design for emitted links is achievable if the system changes the meaning of "the link":

- concept link = exact `qname`
- member link = exact `(company, axis_qname, member_qname)` identity

That is the most important design shift in this document.

---

## Live Findings

These findings were verified against the same Neo4j the write path uses (`bolt://localhost:30687`).

### 1. Versioned-node ambiguity is massive

Observed live counts:

- `Concept` nodes: `467,963`
- `Member` nodes: `1,240,344`
- `GuidanceUpdate` nodes: `74`
- concept qnames with multiple taxonomy versions: `87,388`
- member labels duplicated globally: `66,438`

Implication:

- direct node-edge linking is inherently unstable if the link target is a versioned node

### 2. Current concept edges are not exact-node reliable

The current writer resolves concept edges with:

- `MATCH (con:Concept {qname: $xbrl_qname})`
- `WITH gu, con LIMIT 1`

Current implementation:

- `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py`

Observed live behavior:

- 2024 and 2025 guidance items are often linked to `2022` `Concept` nodes

That is semantically acceptable only if `qname` is the true identity and the exact node is treated as incidental.

If the exact node matters, current behavior is not reliable.

### 3. Current member edges are also not exact-node reliable

Observed live behavior for AAPL:

- 2024 revenue segment guidance links to 2022 member versions such as:
  - `aapl:IPhoneMember`
  - `aapl:MacMember`
  - `us-gaap:ServiceMember`

Again, this is only acceptable if member qname is the true identity and the exact `u_id` is not.

### 4. Usage ranking is not a safe concept resolver

#### CRM tax rate

In CRM's live concept cache, the following all appear:

- `us-gaap:EffectiveIncomeTaxRateContinuingOperations`
- multiple `IncomeTaxReconciliation*` amount concepts

Observed issue:

- several wrong reconciliation concepts have higher usage than the correct percent concept

Implication:

- "pick highest usage" is not trustworthy by itself

#### AAPL revenue

In AAPL's live concept cache, both of these appear strongly:

- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
- `us-gaap:ContractWithCustomerLiabilityRevenueRecognized`

Implication:

- lexical matching on "revenue" is not sufficient

### 5. Member ambiguity is much more tractable than concept ambiguity

Company-local normalized collisions in 2B-style member data:

- AAPL: `0`
- CRM: `1` typo-only collision
- QCOM: `2` case-variant collisions

Implication:

- company-local member linking can be made deterministic with stronger normalization and axis filtering

### 6. One doc assumption was stale / false in the live graph

Prior written assumption:

- QCOM `Qct/Qtl` members were not available in the context-derived member cache

Live finding:

- QCOM `QctMember` and `QtlMember` are present in the 2B-style context data

Implication:

- the best member solution should use cleaned company-local context/member-family construction, not broad fallback search

### 7. Current member normalization has a real blind spot

Current function:

- `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`
- `normalize_for_member_match()`

Observed live mismatch:

- `Subscription & Support` normalizes to `subscriptionsupport`
- `SubscriptionandSupport` normalizes to `subscriptionandsupport`

These do not match.

This means a real company-local business segment can be missed by the current logic.

### 8. Some current concept mappings are semantically lossy

Examples:

- `gross_margin -> GrossProfit`
- `operating_margin -> OperatingIncomeLoss`

These are not exact semantic matches.

They may be useful as anchors, but they are not exact concept links.

If the goal is strict precision, they must be null or moved to a different field such as an optional anchor.

---

## First-Principles Design Rule

If the system must be as close as possible to 100% reliable, then:

- never store a lossy or approximate link as if it were exact

That means:

- exact concept link only for exact concept-equivalent metrics
- exact member link only for exact company-local member identities
- no fuzzy best-effort link masquerading as truth

---

## Recommended Minimalistic Plan

This is the recommended design under the user's constraints:

- no manual review
- no post-processing phase
- minimal code surface
- highest possible reliability

### 1. Change the authoritative storage model

Make concept truth:

- `gu.xbrl_qname`

Do not treat stored `MAPS_TO_CONCEPT` as authoritative.

Make member truth:

- `gu.member_refs`

Where each member ref is a stable string:

```text
axis_qname|member_qname
```

Company is already implied by `FOR_COMPANY`.

This avoids writing stale taxonomy-year node identities as truth.

### 2. Resolve links inline in the write path

Do all linking inside:

- `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py`

No prompt-owned linking.
No later repair phase.
No manual step.

The LLM should extract only:

- label / metric meaning
- segment text
- period
- basis
- quote
- values

The code should own:

- concept identity
- member identity

### 3. Use an exact concept whitelist, not fuzzy matching

Only the following kinds of labels should receive exact concept links:

- `revenue`
- `eps`
- `opex`
- `oine`
- `tax_rate`
- `dividend_per_share`
- `restructuring_costs`
- `restructuring_cash_payments`

Potentially others may be added, but only when they are exact semantic matches.

Everything else stays null.

That includes:

- `gross_margin`
- `operating_margin`
- `fcf`
- growth metrics
- comparative / derived metrics

Those are not exact XBRL concepts and should not be force-linked.

### 4. Add hard concept gates

Concept resolution must use graph metadata, not just qname substrings.

Required gates:

- `concept_type` must match the extracted unit class
  - `percentItemType` for tax-rate-type metrics
  - `perShareItemType` for EPS / DPS
  - monetary types for revenue / opex / restructuring amounts
- `period_type` must be compatible
- explicit exclude patterns must remove disclosure / reconciliation / roll-forward concepts

This is critical because live data showed:

- usage ranking alone is wrong for CRM tax rate

### 5. Replace broad member search with company-local business member resolution

Build the member lookup from 2B-style company-local context data only.

Restrict axes to business-relevant ones:

- `StatementBusinessSegmentsAxis`
- `ProductOrServiceAxis`
- `StatementGeographicalAxis`
- optionally `MajorCustomersAxis` when explicitly relevant

Do not use broad `MATCH (m:Member)` fallback as the authority.

### 6. Strengthen member normalization

Current normalization is too weak.

Required normalization behavior:

- casefold
- strip punctuation
- split camel case
- normalize `&` to `and`
- remove `member` / `segment`
- singularize where safe
- preserve acronyms like `QCT` / `QTL`

Match rule:

- exact normalized equality only

No fuzzy matching unless it is encoded as an explicit alias rule.

### 7. If a physical node edge is needed, derive it, do not trust it

If downstream consumers require a real `Concept` or `Member` node:

- derive it from stable identity at read time

Examples:

- concept node = latest/current `Concept` with matching `qname`
- member node = latest/current company-local `Member` with matching `member_qname` and `axis_qname`

This is not a post-processing phase for extraction.
It is a read-model derivation.

That distinction matters.

---

## Why This Plan Is Better Than "Improve the LLM"

Because the live graph showed:

- concept ambiguity is structural, not stylistic
- member-version ambiguity is structural, not stylistic
- broad lexical ranking can be actively wrong
- current exact-node edges are stale by construction

An LLM can help extract meaning from text.
It cannot make taxonomy-version drift disappear.

Only a stable-identity model can do that.

---

## Closest-to-100 Reliability Profile

Under this plan:

- concept precision on emitted links: effectively 100%, because only exact semantic families link
- member precision on emitted links: effectively 100%, because exact normalized company-local business member matching is used
- overall recall on exact-linkable cases: very high
- overall recall on all extracted metrics: intentionally lower for derived metrics, because null is more correct than a fake exact link

This is the correct tradeoff if precision matters.

---

## Important Tradeoff

If the business insists on linking derived metrics too, then the system must distinguish:

- exact concept link
- approximate anchor concept

Those are different things and should not share the same field.

If they share one field, precision is already lost.

---

## Concrete Files Implicated

Current relevant code:

- `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py`
- `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py`
- `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`
- `.claude/skills/extract/types/guidance/core-contract.md`
- `.claude/skills/extract/types/guidance/primary-pass.md`
- `.claude/skills/extract/types/guidance/enrichment-pass.md`
- `.claude/skills/extract/queries-common.md`

Current problematic behaviors:

- concept edge via qname + arbitrary `LIMIT 1`
- member fallback via broad company-wide member search
- weak member normalization
- prompt-owned concept/member decisions

---

## Live Scripts Used

The following scripts or equivalent queries were used during analysis.

### A. Graph size and duplication check

```bash
venv/bin/python - <<'PY'
from neo4j import GraphDatabase
uri='bolt://localhost:30687'
user='neo4j'
pw='Next2020#'
qs = {
  'concept_nodes': 'MATCH (c:Concept) RETURN count(c) as n',
  'member_nodes': 'MATCH (m:Member) RETURN count(m) as n',
  'guidance_updates': 'MATCH (gu:GuidanceUpdate) RETURN count(gu) as n',
  'duplicate_qnames': 'MATCH (c:Concept) WITH c.qname as q, count(*) as n WHERE n > 1 RETURN count(*) as qnames_with_dupes, max(n) as max_versions',
  'duplicate_member_labels': 'MATCH (m:Member) WITH toLower(m.label) as label, count(*) as n WHERE n > 1 RETURN count(*) as labels_with_dupes, max(n) as max_versions',
}
with GraphDatabase.driver(uri, auth=(user,pw)) as driver:
    with driver.session() as s:
        for name,q in qs.items():
            print(name, s.run(q).single().data())
PY
```

### B. Concept cache inspection

```bash
venv/bin/python - <<'PY'
from neo4j import GraphDatabase
uri='bolt://localhost:30687'
user='neo4j'
pw='Next2020#'
QUERY_2A = """
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE rk.formType = '10-K'
WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last_10k_date
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q']
  AND r.created >= last_10k_date
  AND f.is_numeric = '1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
WITH con.qname AS qname, con.label AS label, count(f) AS usage
ORDER BY usage DESC
RETURN qname, label, usage
"""
with GraphDatabase.driver(uri, auth=(user,pw)) as driver:
    with driver.session() as s:
        rows = s.run(QUERY_2A, ticker='CRM').data()
        for row in rows[:50]:
            print(row)
PY
```

### C. Member cache inspection

```bash
venv/bin/python - <<'PY'
from neo4j import GraphDatabase
uri='bolt://localhost:30687'
user='neo4j'
pw='Next2020#'
QUERY_2B = """
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE size(ctx.dimension_u_ids) > 0 AND size(ctx.member_u_ids) > 0
UNWIND range(0, size(ctx.member_u_ids)-1) AS i
WITH ctx.dimension_u_ids[i] AS dim_u_id, ctx.member_u_ids[i] AS mem_u_id
WHERE dim_u_id IS NOT NULL AND mem_u_id IS NOT NULL
  AND (
    dim_u_id CONTAINS 'Axis'
    OR dim_u_id CONTAINS 'Segment'
    OR dim_u_id CONTAINS 'Product'
    OR dim_u_id CONTAINS 'Geography'
    OR dim_u_id CONTAINS 'Region'
  )
WITH DISTINCT dim_u_id, mem_u_id
WITH dim_u_id, mem_u_id,
     split(mem_u_id, ':')[0] AS mem_cik_raw
WITH dim_u_id, mem_u_id,
     CASE
       WHEN mem_cik_raw =~ '^[0-9]+$'
       THEN toString(toInteger(mem_cik_raw)) + substring(mem_u_id, size(mem_cik_raw))
       ELSE mem_u_id
     END AS mem_u_id_nopad
MATCH (m:Member)
WHERE m.u_id = mem_u_id OR m.u_id = mem_u_id_nopad
WITH m.qname AS member_qname,
     m.u_id AS member_u_id,
     m.label AS member_label,
     dim_u_id,
     split(dim_u_id, ':') AS dim_parts,
     count(*) AS usage
WITH member_qname,
     member_u_id,
     member_label,
     dim_u_id AS axis_u_id,
     dim_parts[size(dim_parts)-2] + ':' + dim_parts[size(dim_parts)-1] AS axis_qname,
     usage
ORDER BY member_qname, usage DESC
WITH member_qname,
     collect({
       member_u_id: member_u_id,
       member_label: member_label,
       axis_qname: axis_qname,
       axis_u_id: axis_u_id,
       usage: usage
     }) AS versions
RETURN member_qname,
       versions[0].member_u_id AS best_member_u_id,
       versions[0].member_label AS best_member_label,
       versions[0].axis_qname AS best_axis_qname,
       versions[0].axis_u_id AS best_axis_u_id,
       versions[0].usage AS best_usage,
       reduce(total = 0, v IN versions | total + v.usage) AS total_usage
"""
with GraphDatabase.driver(uri, auth=(user,pw)) as driver:
    with driver.session() as s:
        rows = s.run(QUERY_2B, ticker='QCOM').data()
        for row in rows[:50]:
            print(row)
PY
```

### D. Current normalization blind-spot check

```bash
venv/bin/python - <<'PY'
import sys
sys.path.insert(0, '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts')
import guidance_ids
vals = [
 ('Subscription & Support', guidance_ids.normalize_for_member_match('Subscription & Support')),
 ('SubscriptionandSupport', guidance_ids.normalize_for_member_match('SubscriptionandSupport')),
 ('Wearables, Home and Accessories', guidance_ids.normalize_for_member_match('Wearables, Home and Accessories')),
 ('WearablesHomeandAccessories', guidance_ids.normalize_for_member_match('WearablesHomeandAccessories')),
]
for raw, norm in vals:
    print(raw, '=>', norm)
PY
```

### E. Current exact-node edge version check

```bash
venv/bin/python - <<'PY'
from neo4j import GraphDatabase
uri='bolt://localhost:30687'
user='neo4j'
pw='Next2020#'
q = """
MATCH (gu:GuidanceUpdate {id:$id})-[:MAPS_TO_CONCEPT]->(c:Concept)
RETURN gu.id as id, gu.xbrl_qname as xq, c.u_id as concept_u_id, c.namespace as ns
"""
ids = [
  'gu:AAPL_2024-02-01T17.00:revenue:gp_2024-01-01_2024-03-31:unknown:total',
  'gu:AAPL_2024-02-01T17.00:tax_rate:gp_2024-01-01_2024-03-31:unknown:total',
]
with GraphDatabase.driver(uri, auth=(user,pw)) as driver:
    with driver.session() as s:
        for id_ in ids:
            print(s.run(q, id=id_).single().data())
PY
```

---

## Final Recommendation

If implementing only one design change, make it this:

**Do not store taxonomy-version node edges as the authoritative concept/member truth.**

Instead:

- concept truth = `xbrl_qname`
- member truth = `axis_qname|member_qname`

Then make the write path resolve those identities exactly and inline.

That is the smallest design that removes the largest number of failure modes.

