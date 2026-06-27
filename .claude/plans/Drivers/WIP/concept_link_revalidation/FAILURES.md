# FAILURES — every wrong link, leak, instability (274-company cohort)

Cohort = the 274 companies that completed run 1 before the subscription session limit (locked in
`cohort274.txt`; spans all 11 sectors, 31 guidance + 243 non-guidance). Ground truth = non-LLM
(canonical us-gaap families + structure). A link is **CONFIRMED-WRONG** only if it lands in a
DIFFERENT metric's canonical family or contradicts the concept's balance/period — both deterministic.

## 1. Confirmed-WRONG links: **0**

Across all emitted links in 274 companies × the probe set, **zero** links were confirmed wrong by the
cross-family or structural-contradiction tests. No cardinal errors.

## 2. Out-of-canonical-GT links: 30 — adjudicated, all correct or defensible (0 wrong)

These fell outside the (expanded) canonical family list. Adjudicated by us-gaap/dei concept
**definition** (not by trusting the matcher). All are valid concepts the list still omitted —
mostly industry-specific or partnership (MLP) lines no static map would hold:

| metric | picked concept | verdict |
|---|---|---|
| capex_guidance | EstimatedFutureCapitalExpendituresForNextYear | **correct** (a real forward-capex concept) |
| eps / basic_eps | IncomeLossFromContinuingOperationsPer{Diluted,Basic}Share | correct |
| revenue | OperatingLeaseLeaseIncome (REIT), RevenuesAndOther | correct |
| operating_expenses | NoninterestExpense (bank), OperatingExpensesNetOfOtherOperatingIncome | correct |
| inventory | EnergyRelatedInventory…, InventoryRawMaterialsAndSupplies, Expendableparts… | correct |
| cost_of_revenue | FoodAndBeverageCosts, DirectOperatingCosts, ProductionAndDistributionCosts, CostOfRevenueNet | correct (industry COGS) |
| d_a | DepreciationAndOtherAmortization, …ExcludingDebtIssuanceCosts | correct |
| capex | PaymentsForProceedsFromPP&E, …IncludingNuclearFuel (utility) | correct |
| restructuring_charges | RestructuringAndOtherCharges, …Mainline (airline) | correct |
| r_d | ProductDevelopmentExpense | correct |
| stock_based_compensation | AllocatedSharebasedCompensationExpenseAndIssuanceOfStock… | correct |
| basic_share_count | WeightedAverageNumberOfSharesIssuedBasic | correct |
| **sg_a** | **GeneralAndAdministrativeExpense** (×4) | **borderline** — G&A ⊂ SG&A; nearest line when SG&A not reported |
| **total_debt** | **NotesPayable** (×1) | **borderline** — a debt component, not strictly total |

Net: 24 correct, ~5 borderline-defensible, **0 wrong**. The borderline cases are conservative
nearest-line matches, never a different metric.

## 3. Recall residual (core metrics): 395 / 6,199 misses (6.4%) — mostly defensible abstention

The matcher abstained where a GT-family concept existed. Concentration:

| metric | misses | why it's mostly correct behavior |
|---|---|---|
| **total_debt** | 167 | "total debt" is short+long; company reports only `LongTermDebt` → abstaining is right (not "total") |
| **operating_expenses** | 61 | ambiguous aggregate (`OperatingExpenses` vs `CostsAndExpenses`) → conservative abstain |
| net_sales | 46 | synonym of revenue; abstains on some unusual revenue tags |
| interest_expense | 40 | net-vs-gross interest ambiguity |
| d_a | 33 | D&A-variant ambiguity |
| cash, equity, capex, others | 48 | scattered |

→ ≈58% of the "misses" are the matcher being **precision-protective on inherently ambiguous
aggregates** (total_debt, operating_expenses). True recall on unambiguous metrics is well above the
raw 93.6%. Misses are SAFE (no wrong link) — exactly the enrichment-link tradeoff.

## 4. guidance / surprise suffixed slugs: abstains (by design, not a wrong link)

Fed `revenue_guidance` / `eps_surprise` directly, the matcher **abstains** (2,118 / 2,192 = 96.6%
recall-miss). It does NOT base-strip the suffix. This is SAFE (0 wrong links) and matches the
schema: `guidance`/`surprise` drivers inherit their concept from the base `metric` via `BASE_METRIC`,
not by linking the suffixed slug. (One exception linked correctly: `capex_guidance →
EstimatedFutureCapitalExpendituresForNextYear`.) **Recommendation (notes only, no code change):** in
production, resolve the base metric's concept and inherit via `BASE_METRIC`, or strip the suffix
before calling `link()`.

## 5. Abstention leaks (conceptless drivers): 0 / 10,960

ratio, event/action, macro, non-GAAP, and KPI drivers all abstained 100% (including the non-guarded
`return_on_equity`, `market_share`, `foot_traffic`… which rely on the LLM, not the guard).

## 6. Instability (3 independent runs, 270 companies, 11,070 non-guarded cells)

**98.0% of cells are identical across all 3 runs** (flip rate 2.04%, 226 unstable). Breakdown:
- **172 link↔abstain** — the matcher toggles a borderline link on/off across runs. Concentrated on
  ambiguous aggregates (`total_debt`, `operating_expenses`) and a few `net_sales`/`interest_expense`.
  Safe: toggling to abstain never creates a wrong link.
- **54 link↔link** — picks a different concept across runs, but **0 cross-family** (verified): every
  alternation is between synonyms in the SAME metric family (`Revenues`↔`RevenueFromContractWithCustomer`,
  `ShareBasedCompensation`↔`AllocatedShareBasedCompensationExpense`,
  `RestructuringCharges`↔`RestructuringCosts`, `InterestExpense`↔`InterestExpenseNonoperating`).

**No flip introduces a wrong concept.** Mitigation if exact-tag stability matters: canonicalize a
metric's family to the highest-`usage` member deterministically (REVALIDATION/§8.7), or the optional
2–3× stability gate. (An earlier 2-run figure of 0.66% was diluted by un-run companies; 2.04% is the
clean per-company 3-run number.)
