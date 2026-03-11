# Arelle Untapped APIs — Validated Findings and Migration Notes

**Status**: Items 1, 2, 4, and 5 have been empirically characterized on a 50-filing stratified sample as of 2026-03-10. No XBRL pipeline code has been changed yet.

**Current runtime**: `arelle-release==2.38.20`

**Important scope note**: The findings below are strong sample-based evidence, not a literal 100% proof over all `8,189` filings.

---

## High-Level Conclusions

1. **Items 1+2 are safe refactors.**
   `rootConcepts` and `fromModelObject()` reproduced the same concept trees as the current manual logic across the tested sample.

2. **Items 1+2 are mainly maintainability wins, not major accuracy wins.**
   The current tree-building logic is already producing equivalent results on the sample.

3. **Item 4 is not just a tolerance issue.**
   There is a real **coverage gap**: on the sample, Calc 1.1 evaluated `23,836` parent/context/unit summation groups, while the current pipeline validated only `11,232` of them.

4. **Item 5 is a real nondeterminism problem.**
   The current duplicate-primary selection is unstable. A deterministic final tie-break removes that instability on the sample, but it is not a zero-risk change because canonical fact IDs and downstream edge keys can change.

5. **The Arelle upgrade itself is not the source of the observed output drift.**
   On a controlled AAPL replay, Arelle `2.35.0` and `2.38.20` produced the same raw facts, raw relationships, and raw network counts. The instability came from the pipeline's duplicate-primary selection.

---

## Environment and Upgrade Findings

- The venv is now on `arelle-release==2.38.20`.
- The old `arelle==2.2` fork was removed.
- Removing the fork initially broke the shared `arelle` namespace until `arelle-release` was force-reinstalled.
- Current import health is good: `Version`, `Cntlr`, `XbrlConst`, and the pipeline modules import successfully.
- On a controlled side-by-side replay of Apple filing `0000320193-25-000073`:
  - `2.35.0` and `2.38.20` produced the same raw Arelle parse
  - `769` raw facts
  - `495` raw presentation relationships
  - `109` raw calculation relationships
  - `66` discovered networks
- Therefore:
  - raw network extraction did not materially change on that filing
  - downstream fact and edge drift came from duplicate-primary instability, not from Arelle changing the underlying parse
- Performance improvement from the upgrade is plausible, but not yet benchmarked rigorously enough to claim as proven.

---

## Validation Basis

All empirical validation discussed below was read-only:

- no pipeline code changes during the runs
- no Neo4j writes during the runs
- output written under `/tmp`
- sample: `50` filings
- sample mix:
  - `25` `10-K`
  - `6` `10-K/A`
  - `14` `10-Q`
  - `5` `10-Q/A`

The repo currently contains Claude-created validation scripts and JSON files, but the conclusions below reflect independent Codex validation runs executed from `/tmp`.

---

## 1. Root Concept Discovery — `rootConcepts`

**Current**

`xbrl_networks.py` computes roots manually by subtracting child IDs from parent IDs.

**Replacement**

Use `ModelRelationshipSet.rootConcepts`.

```python
rel_set = model_xbrl.relationshipSet(XbrlConst.parentChild, network_uri)
roots = rel_set.rootConcepts
```

**Why this is still worth doing**

- less custom code
- less manual set arithmetic
- clearer alignment with Arelle's own graph model
- likely some modest caching/performance benefit

**What it does not do**

- does not materially improve tree accuracy by itself on the tested sample

**Risk**

Low.

**Validation**

Passed on the 50-filing sample when compared against the current manual logic.

---

## 2. Tree Walking — `fromModelObject()`

**Current**

`xbrl_networks.py` flattens all relationships into custom adjacency maps, computes roots, then recursively rebuilds trees.

**Replacement**

Walk the directed graph directly from Arelle:

```python
rel_set = model_xbrl.relationshipSet(XbrlConst.parentChild, network_uri)

def walk(concept, level):
    for rel in rel_set.fromModelObject(concept):
        child = rel.toModelObject
        walk(child, level + 1)
```

**Why this is still worth doing**

- simpler code path
- fewer intermediate structures
- easier to debug
- closer to Arelle's internal relationship model

**What it does not do**

- does not fix duplicate handling
- does not fix calculation tolerance semantics
- does not change downstream fact-level graph behavior by itself

**Risk**

Low, assuming concept ID formatting stays unchanged.

**Validation**

Passed on the 50-filing sample when compared against the current manual logic.

---

## Items 1+2 Validation Results

### Main conclusion

The old manual tree logic and the Arelle-native `rootConcepts` + `fromModelObject()` traversal produced equivalent concept trees across the tested sample.

### Verified outcome

- `50/50` filings passed
- `0` mismatches
- `0` load errors

This de-risks the refactor for tree construction itself.

### Important interpretation

This is a **safe cleanup**, not the biggest accuracy opportunity in the pipeline.

---

## 3. Fact Lookups — Cached indexes such as `factsByQname`

**Current**

The pipeline iterates `factsInInstance` multiple times across several build phases.

**Available Arelle helpers**

- `factsByQname`
- `factsByLocalName`
- `factsByDimMemQname(...)`
- `factsByPeriodType(...)`
- `nonNilFactsInInstance`

**Assessment**

This is still a promising optimization/refactor area, but it has **not** been independently validated yet in the same way Items 1, 2, 4, and 5 have.

**Risk**

Likely low for `factsByQname`, but dimensional and period helpers should still be spot-checked before assuming perfect drop-in equivalence.

**Recommendation**

Treat this as a performance and code-simplicity refactor, not a proven accuracy fix.

---

## 4. Calculation Validation — Calc 1.1 vs current `0.1%` rule

**Current**

`xbrl_processor.py` validates a parent sum using:

```python
percent_diff = abs(parent_value - total_sum) / abs(parent_value)
is_match = percent_diff < 0.001
```

This is a fixed percentage rule, not an XBRL-decimals-aware rule.

**Arelle alternative**

Use Arelle Calc 1.1 round-to-nearest semantics via `ValidateXbrlCalcs`.

**Important finding**

The problem is not only "wrong tolerance." The larger issue is that the current pipeline and Calc 1.1 are not evaluating the same set of parent/context/unit summation groups.

### Item 4 validated counts

On the 50-filing sample:

| Metric | Count |
|--------|------:|
| Old groups evaluated by current pipeline | `11,232` |
| Groups evaluated by Calc 1.1 | `23,836` |
| Both valid | `10,287` |
| Both invalid | `833` |
| Old valid, new invalid | `21` |
| Old invalid, new valid | `91` |
| New only | `12,604` |

### What the numbers mean

- On the overlapping `11,232` groups, agreement was `99.0%`.
- But the current pipeline only covered about `47.1%` of the groups Calc 1.1 evaluated on the sample.
- So the bigger gap is **coverage**, not just tolerance accuracy.

### Likely source of the coverage gap

The current pipeline only validates groups that survive several earlier filters:

1. facts are first routed through the current fact lookup strategy
2. calculation fact-to-fact relationships are only formed when parent and child facts match by exact `context_id` and unit
3. `check_calculation_steps()` only sees those preassembled groups

Calc 1.1 binds calculation participants directly from the XBRL model using Arelle's own context/unit normalization and decimals semantics, so it reaches many groups the current pipeline never gets to.

### Examples of real semantic disagreement

Representative `old_valid_new_invalid` cases:

- AEP `WeightedAverageNumberOfDilutedSharesOutstanding`
  - current rule: valid
  - Calc 1.1: invalid
- AIG `ProfitLoss`
  - current rule: valid
  - Calc 1.1: invalid

Representative `old_invalid_new_valid` cases:

- AFL `DefinedBenefitPlanAmountsRecognizedInOtherComprehensiveIncomeLossNetGainLossBeforeTax`
  - current rule: invalid
  - Calc 1.1: valid
- AIG `Liabilities`
  - current rule: invalid
  - Calc 1.1: valid

### Risk

High if changed directly.

This is not a simple "swap the tolerance constant" change. It can change:

- which groups are validated at all
- which groups pass or fail
- potentially which fact-to-fact calculation edges are retained downstream

### Recommendation

Treat Item 4 as a **semantic migration**, not a small refactor.

---

## 5. Duplicate Fact Detection — deterministic tie-break vs current instability

**Current**

`_build_facts()` selects a primary duplicate using:

1. higher `decimals`
2. then longer significant-digit string
3. then nothing else

If those tie, the winner depends on iteration order.

**Minimal safer improvement**

Preserve the current policy, but add a deterministic final tie-break such as `fact.id` or `fact.u_id`.

**Arelle-native tooling**

`ValidateDuplicateFacts` and `DuplicateFactSet` provide spec-aware duplicate analysis, but a full migration to those semantics is a bigger step than just making the current code deterministic.

### Item 5 validated counts

On the 50-filing sample:

| Metric | Count |
|--------|------:|
| Duplicate fact groups | `15,349` |
| Ambiguous groups under current rules | `15,140` |
| Changed winner on first deterministic replay | `7,709` |
| Value-safe changed groups | `7,709` |
| Complete changed groups | `7,656` |
| Consistent-but-not-complete changed groups | `53` |
| Filings rerun for instability check | `45` |
| Current unstable groups across reruns | `11,422` |
| Deterministic unstable groups across reruns | `0` |

### What the numbers mean

- `98.6%` of duplicate groups were ambiguous under the current rule set.
- `50.9%` of ambiguous groups changed winner when a deterministic final tie-break was applied.
- `75.4%` of ambiguous groups showed instability across reruns of the current logic.
- The deterministic rule eliminated observed instability on the sample.

### Important nuance

This does **not** mean zero regression risk.

Why not:

- your `Fact.id` is the fact `u_id`
- duplicate remapping changes which fact becomes canonical
- relationship rewriting uses `primary_fact`
- therefore downstream fact IDs and relationship keys can change even when the value is the same

So the risk profile is:

- **low data-correctness risk** for most changed groups
- **non-zero identity churn risk** for facts and downstream graph edges

### Recommendation

Do not frame this as "0% regression risk."

The safest rollout order is:

1. keep the current selection policy
2. add only a deterministic final tie-break
3. shadow-run and measure resulting fact-ID and edge-key churn
4. only then consider a fuller `DuplicateFactSet` migration

---

## Side-by-Side Upgrade Finding

On the controlled Apple replay under isolated Arelle `2.35.0` and `2.38.20` imports:

- raw facts matched
- raw presentation relationship counts matched
- raw calculation relationship counts matched
- discovered network counts matched

This matters because it narrows the source of output drift:

- the upgrade itself did not materially change raw network extraction on that filing
- duplicate-primary instability in the pipeline remained the main cause of downstream fact-ID and calculation-edge drift

---

## What Is Actually Proven

### Proven on the 50-filing sample

- Item 1 root discovery is safe to refactor.
- Item 2 tree walking is safe to refactor.
- Item 5 current duplicate-primary selection is nondeterministic.
- A deterministic final tie-break removes the observed instability on the sample.
- Item 4 current calc validation differs from Calc 1.1 both in acceptance semantics and in coverage.

### Not proven yet

- corpus-wide proof over all `8,189` filings
- exact end-to-end production impact of Item 5 on fact IDs and edge IDs across the full corpus
- performance gain from Items 1+2 or from the Arelle upgrade
- full drop-in equivalence for Item 3 cached fact indexes

---

## Recommended Implementation Order

1. **Item 5a**: add a deterministic final tie-break to the current duplicate-primary logic
2. **Items 1+2**: refactor tree extraction to `rootConcepts` + `fromModelObject()`
3. **Item 3**: introduce cached fact lookups where they clearly preserve semantics
4. **Item 4**: decide whether to keep current graph-building semantics and add Calc 1.1 QA, or move the actual calculation acceptance logic toward Arelle semantics

---

## Simple Explanation of the 12,604-Group Coverage Gap

The short version:

- Calc 1.1 found `23,836` parent/context/unit calculation groups to check.
- The current pipeline only checked `11,232` of them.
- The difference is `12,604` groups.

That means the problem is bigger than "our tolerance is a little off."

It means the current pipeline is **not even reaching** a large number of calculation groups that exist in the XBRL model. In other words, before the code gets to the `0.1%` tolerance check, it has already filtered out or failed to assemble many groups that Calc 1.1 can still validate.

So:

- **tolerance problem** = "we checked the group, but judged it with the wrong rule"
- **coverage problem** = "we never checked the group at all"

Item 4 has both problems.
