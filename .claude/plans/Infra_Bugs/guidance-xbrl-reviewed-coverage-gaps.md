# Guidance XBRL Reviewed Coverage Gaps

**Created**: 2026-04-02
**Status**: OPEN
**Impact**: `xbrl_qname` coverage is still partly nondeterministic; concept links depend on a mix of reviewed rules, agent survivors, and cache availability
**Fix**: extend reviewed label coverage, review survivor qnames one by one, and harden concept-cache fallback behavior

---

## Summary

The current XBRL concept issue is not "the deterministic resolver was never built". The file exists and is active:

- `.claude/skills/earnings-orchestrator/scripts/concept_resolver.py`
- `guidance_write_cli.py` calls `apply_concept_resolution()` before concept inheritance

The real open problem is narrower and more subtle:

1. the reviewed label table is incomplete relative to the label slugs now present in the graph
2. reviewed labels still preserve some agent-found "survivor" qnames when the table does not recognize them
3. concept repair has no self-healing fallback when the concept cache is missing or empty
4. the concept cache itself is scoped to recent `10-K` + `10-Q` facts only, so some `8-K`-driven guidance metrics cannot be resolved from current cache contents

So the current system is hybrid, not fully deterministic.

---

## Current code path

Current order in `guidance_write_cli.py`:

1. `_ensure_ids()` canonicalizes the item and computes IDs
2. `load_concept_cache(ticker)` loads `/tmp/concept_cache_{ticker}.json`
3. `apply_concept_resolution(valid_items, concept_rows)` runs deterministic reviewed repair
4. same-label concept inheritance fills null siblings within the batch
5. `resolve_concept_family()` sets `concept_family_qname`

Important asymmetry:

- member matching has a live fallback in write mode when `/tmp/member_map_{ticker}.json` is missing
- concept matching has no equivalent live fallback; if the concept cache is missing or empty, concept repair becomes a no-op

---

## 2026-04-02 Live Graph Audit

Database-wide bucket summary by current resolver status:

- reviewed labels with non-null qname: **2,643**
- reviewed labels with null qname: **128**
- force-null-by-policy labels with non-null qname: **4**
- force-null-by-policy labels with null qname: **1,390**
- unhandled labels with non-null qname: **1,276**
- unhandled labels with null qname: **2,850**

This is the most important top-line result:

- the reviewed table is doing useful work
- but a very large number of live links still sit outside the reviewed table entirely

---

## Failure Mode 1 — Unreviewed labels are still a major live population

High-volume labels that are NOT in `CONCEPT_CANDIDATES` but already have non-null links in the graph:

| Metric | Total | Linked | Unlinked | Current qname behavior |
|--------|------:|-------:|---------:|------------------------|
| `diluted_share_count` | 219 | 209 | 10 | mostly `WeightedAverageNumberOfDilutedSharesOutstanding`, but also basic/outstanding variants |
| `net_sales` | 201 | 197 | 4 | revenue-family qnames only |
| `effective_tax_rate` | 163 | 122 | 41 | mostly `EffectiveIncomeTaxRateContinuingOperations`, but 2 rows use `IncomeTaxExpenseBenefit` |
| `adjusted_eps` | 143 | 75 | 68 | all linked rows use `EarningsPerShareDiluted` |
| `weighted_average_basic_shares_outstanding` | 30 | 26 | 4 | `WeightedAverageNumberOfSharesOutstandingBasic` |
| `adjusted_eps_diluted` | 23 | 13 | 10 | `EarningsPerShareDiluted` |
| `weighted_average_diluted_shares_outstanding` | 21 | 19 | 2 | `WeightedAverageNumberOfDilutedSharesOutstanding` |
| `non_gaap_eps` | 18 | 3 | 15 | `EarningsPerShareDiluted` |
| `adjusted_diluted_eps` | 6 | 5 | 1 | `EarningsPerShareDiluted` |
| `basic_share_count` | 12 | 12 | 0 | `WeightedAverageNumberOfSharesOutstandingBasic` |
| `basic_shares_outstanding` | 3 | 3 | 0 | `WeightedAverageNumberOfSharesOutstandingBasic` |

Interpretation:

- some of these are easy reviewed-label additions (`adjusted_eps`, `non_gaap_eps`, `adjusted_eps_diluted`, `adjusted_diluted_eps`)
- some require one-by-one validation because qname diversity is real (`diluted_share_count`, `effective_tax_rate`)

This is the main reason the March corpus-mining conclusion ("no registry changes warranted") is too optimistic for the current live label universe.

---

## Failure Mode 2 — Reviewed labels still rely on "survivor" qnames

For reviewed labels, the current resolver does NOT fully override the agent in every case.

When `resolve_xbrl_qname()` returns `None` but the item already has a cache-valid `xbrl_qname`, `apply_concept_resolution()` preserves that qname instead of clearing it.

That creates a survivor population for reviewed labels:

| Reviewed label | Survivor qnames observed in live graph | Why it matters |
|---------------|-----------------------------------------|----------------|
| `capex` | `nfe:CapitalExpenditures` | not in reviewed candidate list |
| `tax_rate` | `us-gaap:IncomeTaxExpenseBenefit` | risky / likely wrong for a rate metric |
| `interest_expense` | `InterestIncomeExpenseNet`, `InterestExpenseNonoperating`, `InterestIncomeExpenseNonoperatingNet` | needs one-by-one validation |
| `operating_cash_flow` | `NetCashProvidedByUsedInOperatingActivities`, `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` | probably safe synonym expansion |
| `opex` | `SellingGeneralAndAdministrativeExpense` | semantically risky; likely not always exact |
| `restructuring_charges` | `RestructuringSettlementAndImpairmentProvisions` | needs validation |
| `interest_income` | `InvestmentIncomeNonoperating` | needs validation |
| `operating_expenses` | `CostsAndExpenses` | broad and likely not always exact |

This is the strongest proof that issue 2 is now a coverage/review problem, not a missing-module problem.

---

## Failure Mode 3 — Concept cache scope leaves real gaps

`QUERY_2A` in `warmup_cache.py` only looks at:

- the latest `10-K`
- subsequent `10-Q`s
- numeric facts
- consolidated contexts only

It does NOT include `8-K` filings.

That matters because a meaningful share of current guidance is extracted from `8-K`s and transcripts quoting `8-K` outlook tables.

### Concrete example: MU `opex`

Null `opex` links are concentrated in `MU`:

- `MU`: 44 null `opex` rows
- `ASO`: 1
- `NFE`: 1

By source type for `MU` `opex`:

- `8k`: 24 rows, all null
- `transcript`: 20 rows, all null

Direct replay of `QUERY_2A` for `MU` on 2026-04-02 returned 276 concept rows and showed:

- `ResearchAndDevelopmentExpense`
- `OperatingIncomeLoss`
- `EffectiveIncomeTaxRateContinuingOperations`
- `SellingGeneralAndAdministrativeExpense`

But **not** `OperatingExpenses`.

Interpretation:

- the reviewed `opex -> OperatingExpenses` rule cannot fire for `MU`
- some survivor rows elsewhere use `SellingGeneralAndAdministrativeExpense`, but that mapping is not obviously exact enough to bless globally
- this is exactly why survivor qnames must be reviewed one by one, not bulk-added mechanically

### Concrete example: SMTC `tax_rate`

Null `tax_rate` links are concentrated in `SMTC`:

- `SMTC`: 22 null `tax_rate` rows
- `ASO`: 6

Source breakdown for `SMTC`:

- `8k`: 13 rows, all null
- `transcript`: 9 null rows + 1 survivor row linked to `IncomeTaxExpenseBenefit`

Direct replay of `QUERY_2A` for `SMTC` on 2026-04-02 returned **0 concept rows**, despite `SMTC` having:

- 4 `10-K`s
- 9 `10-Q`s
- 41 `8-K`s

Interpretation:

- concept repair for `SMTC` is currently a no-op because the cache is empty
- the single linked transcript row is an agent survivor, not a deterministic reviewed resolution
- this is the clearest proof that concept matching needs a fallback or stronger warmup guarantee

---

## Failure Mode 4 — Some offline analysis used a different label vocabulary

The March 2026 concept-fallback analysis under:

- `earnings-analysis/consensus_exploration/concept_fallbacks/20260329_082021/`

did not contain the key live slugs now driving misses, including:

- `adjusted_eps`
- `effective_tax_rate`
- `net_sales`
- `diluted_share_count`
- `weighted_average_basic_shares_outstanding`
- `weighted_average_diluted_shares_outstanding`

So the conclusion in `40_concept_candidate_decisions.md` that no reviewed-candidate registry changes were warranted is not enough for the current live guidance label vocabulary.

---

## What should be added first

### Safe first-wave reviewed additions

These look high-confidence because the live graph already converges on a single qname family:

- `adjusted_eps` -> `EarningsPerShareDiluted`
- `non_gaap_eps` -> `EarningsPerShareDiluted`
- `adjusted_eps_diluted` -> `EarningsPerShareDiluted`
- `adjusted_diluted_eps` -> `EarningsPerShareDiluted`
- `net_sales` -> revenue-family candidates already used for `revenue`
- `weighted_average_basic_shares_outstanding` -> `WeightedAverageNumberOfSharesOutstandingBasic`
- `weighted_average_diluted_shares_outstanding` -> `WeightedAverageNumberOfDilutedSharesOutstanding`

The next bucket is "likely correct but still worth spot-validating before hardening":

- `effective_tax_rate` -> same candidate list as `tax_rate`
- `basic_share_count` / `basic_shares_outstanding` -> `WeightedAverageNumberOfSharesOutstandingBasic`

### Ready-to-paste `CONCEPT_CANDIDATES` additions

These are the highest-confidence additions based on current live links and current resolver semantics:

```python
    'adjusted_eps': (
        'EarningsPerShareDiluted',
    ),
    'non_gaap_eps': (
        'EarningsPerShareDiluted',
    ),
    'adjusted_eps_diluted': (
        'EarningsPerShareDiluted',
    ),
    'adjusted_diluted_eps': (
        'EarningsPerShareDiluted',
    ),
    'net_sales': (
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'RevenueFromContractWithCustomerIncludingAssessedTax',
        'SalesRevenueNet',
        'Revenues',
    ),
    'weighted_average_basic_shares_outstanding': (
        'WeightedAverageNumberOfSharesOutstandingBasic',
    ),
    'weighted_average_diluted_shares_outstanding': (
        'WeightedAverageNumberOfDilutedSharesOutstanding',
    ),
```

Add tests alongside them. Each new slug should get:

- a direct resolution test against the expected qname
- a pass-through / unhandled test for a nearby non-reviewed variant if ambiguity still exists

### Paste after spot-validation, not blindly

These are close to ready, but the live graph still shows enough semantic ambiguity that the final tuple should be confirmed against source phrasing first:

```python
    'effective_tax_rate': (
        'EffectiveIncomeTaxRateContinuingOperations',
        'EffectiveIncomeTaxRate',
    ),
    'basic_share_count': (
        'WeightedAverageNumberOfSharesOutstandingBasic',
    ),
    'basic_shares_outstanding': (
        'WeightedAverageNumberOfSharesOutstandingBasic',
    ),
```

Why these stay in a second bucket:

- `effective_tax_rate` is mostly clean, but 2 live rows currently use `IncomeTaxExpenseBenefit`, so the source examples should be spot-checked before hardening the reviewed rule.
- `basic_share_count` and `basic_shares_outstanding` currently converge on `WeightedAverageNumberOfSharesOutstandingBasic`, but those phrases can drift semantically toward end-period shares outstanding in some companies. Keep them reviewed, not assumed.

### Needs one-by-one review before adding

- `diluted_share_count`
- `opex` survivor mappings to SG&A / CostsAndExpenses
- `tax_rate` survivor mapping to `IncomeTaxExpenseBenefit`
- `interest_expense` survivor variants
- `restructuring_charges` survivor variant

These are exactly the cases where "extend reviewed label coverage" must remain hand-reviewed, not automated.

---

## Proposed fix order

### Fix 1: extend reviewed label coverage for obvious synonym families

Add the high-confidence labels above to `CONCEPT_CANDIDATES` and add tests for each.

### Fix 2: review survivor qnames explicitly before canonizing them

For every survivor qname listed in this doc:

- confirm it is semantically exact enough for the label
- then either add it to the candidate tuple or intentionally reject it and document why

### Fix 3: add concept fallback behavior

Concept matching currently lacks the resilience that member matching already has.

Options:

- best: live fallback query when `/tmp/concept_cache_{ticker}.json` is missing or empty
- acceptable: fail loud when concept cache is absent instead of silently skipping repair

### Fix 4: revisit cache scope for 8-K-driven guidance

Decide whether the current `10-K` + `10-Q` cache scope is acceptable for `8-K` guidance extraction.

If not, evaluate:

- adding relevant `8-K` concept usage into the warmup cache
- or using a fallback query against the company's current Concept nodes

### Fix 5: backfill historical rows after reviewed coverage expands

Once the reviewed table is widened:

- re-run affected companies
- or run a direct backfill for clearly safe synonym additions

---

## Current conclusion

Issue 2 should now be thought of as:

- not "build a concept resolver"
- but "finish converting the current hybrid concept system into a truly reviewed one"

The active work is:

1. widen reviewed label coverage to match the labels we actually write
2. validate survivor qnames one by one
3. add a cache-missing / cache-empty fallback path

Until then, concept linking remains partly deterministic, partly opportunistic, and partly absent.
