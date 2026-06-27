#!/usr/bin/env python3
"""Converged INDEPENDENT ground truth (non-LLM): canonical us-gaap concept FAMILIES (documented
standard concepts) ∩ each company's menu, cross-validated by value-anchoring + structural signature.

Non-circular: the canonical concept for "revenue" (us-gaap:Revenues / RevenueFromContractWithCustomer…)
is documented taxonomy fact, NOT derived from the matcher's answer. Non-LLM throughout.

Outputs gt_dataset.json = { "TICKER|metric": {gt:[qnames], primary, in_menu, struct} } for core metrics,
and a value-anchor agreement report (validates the canonical map against signal A).
Also lets scoring flag a link into a DIFFERENT metric's family, or a structural contradiction, as
CONFIRMED-WRONG with no LLM.
"""
import json, pathlib, collections

CLRV = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")

# Canonical us-gaap LOCAL-NAME families per core metric + expected structural signature.
# balance: credit/debit/None(either); ptype: duration/instant; itype substring on type_local
# (monetary/perShare/shares/pure). None = don't enforce.
CANON = {
  "revenue":            (["Revenues","RevenueFromContractWithCustomerExcludingAssessedTax","RevenueFromContractWithCustomerIncludingAssessedTax","SalesRevenueNet","SalesRevenueGoodsNet","RevenuesNetOfInterestExpense"], "credit","duration"),
  "net_sales":          (["Revenues","RevenueFromContractWithCustomerExcludingAssessedTax","RevenueFromContractWithCustomerIncludingAssessedTax","SalesRevenueNet","SalesRevenueGoodsNet"], "credit","duration"),
  "cost_of_revenue":    (["CostOfRevenue","CostOfGoodsAndServicesSold","CostOfGoodsSold","CostOfGoodsAndServicesSoldExcludingDepreciationDepletionAndAmortization"], "debit","duration"),
  "cost_of_goods_sold": (["CostOfGoodsAndServicesSold","CostOfGoodsSold","CostOfRevenue"], "debit","duration"),
  "gross_profit":       (["GrossProfit"], "credit","duration"),
  "operating_income":   (["OperatingIncomeLoss"], None,"duration"),
  "net_income":         (["NetIncomeLoss","ProfitLoss","NetIncomeLossAvailableToCommonStockholdersBasic"], "credit","duration"),
  "sg_a":               (["SellingGeneralAndAdministrativeExpense"], "debit","duration"),
  "g_a":                (["GeneralAndAdministrativeExpense"], "debit","duration"),
  "r_d":                (["ResearchAndDevelopmentExpense","ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"], "debit","duration"),
  "operating_expenses": (["OperatingExpenses","CostsAndExpenses","OperatingCostsAndExpenses"], "debit","duration"),
  "interest_expense":   (["InterestExpense","InterestExpenseDebt","InterestExpenseNonoperating","InterestIncomeExpenseNet","InterestIncomeExpenseNonoperatingNet"], None,"duration"),
  "income_tax_expense": (["IncomeTaxExpenseBenefit","CurrentIncomeTaxExpenseBenefit"], "debit","duration"),
  "tax_expense":        (["IncomeTaxExpenseBenefit","CurrentIncomeTaxExpenseBenefit"], "debit","duration"),
  "d_a":                (["DepreciationDepletionAndAmortization","DepreciationAmortizationAndAccretionNet","DepreciationAndAmortization","Depreciation"], None,"duration"),
  "depreciation_and_amortization": (["DepreciationDepletionAndAmortization","DepreciationAndAmortization","DepreciationAmortizationAndAccretionNet"], None,"duration"),
  "eps":                (["EarningsPerShareDiluted"], None,"duration"),
  "diluted_eps":        (["EarningsPerShareDiluted"], None,"duration"),
  "basic_eps":          (["EarningsPerShareBasic"], None,"duration"),
  "operating_cash_flow":(["NetCashProvidedByUsedInOperatingActivities","NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"], None,"duration"),
  "capex":              (["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsToAcquireProductiveAssets","PaymentsForCapitalImprovements","PaymentsToAcquireOtherPropertyPlantAndEquipment"], "debit","duration"),
  "capital_expenditures":(["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsToAcquireProductiveAssets","PaymentsForCapitalImprovements"], "debit","duration"),
  "cash":               (["CashAndCashEquivalentsAtCarryingValue","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"], "debit","instant"),
  "total_assets":       (["Assets"], "debit","instant"),
  "total_debt":         (["LongTermDebt","LongTermDebtNoncurrent","DebtLongtermAndShorttermCombinedAmount","LongTermDebtAndCapitalLeaseObligations"], "credit","instant"),
  "stockholders_equity":(["StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "credit","instant"),
  "inventory":          (["InventoryNet"], "debit","instant"),
  "diluted_share_count":(["WeightedAverageNumberOfDilutedSharesOutstanding"], None,"duration"),
  "basic_share_count":  (["WeightedAverageNumberOfSharesOutstandingBasic"], None,"duration"),
  "shares_outstanding": (["CommonStockSharesOutstanding","CommonStockSharesIssued"], None,"instant"),
  "dividend_per_share": (["CommonStockDividendsPerShareDeclared","CommonStockDividendsPerShareCashPaid"], None,"duration"),
  "dividends_per_share":(["CommonStockDividendsPerShareDeclared","CommonStockDividendsPerShareCashPaid"], None,"duration"),
  "restructuring_charges":(["RestructuringCharges","RestructuringCostsAndAssetImpairmentCharges"], "debit","duration"),
  "stock_based_compensation":(["ShareBasedCompensation","AllocatedShareBasedCompensationExpense"], "debit","duration"),
}

# GT-completeness pass: concepts adjudicated as genuinely the metric BY us-gaap/dei DEFINITION
# (industry-specific + partnership/MLP + common variants), independent of the matcher's choice.
EXTRA = {
  "revenue": ["RegulatedAndUnregulatedOperatingRevenue"],
  "net_sales": ["RegulatedAndUnregulatedOperatingRevenue"],
  "cost_of_revenue": ["CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization","CostOfRevenueCostOfGoodsSold","OperatingCostOfSales"],
  "cost_of_goods_sold": ["CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization","CostOfRevenueCostOfGoodsSold","OperatingCostOfSales"],
  "operating_income": ["OperatingIncomeLossIncludingIncomeLossFromEquityMethodInvestments"],
  "r_d": ["ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost"],
  "interest_expense": ["InterestAndDebtExpense","InterestExpenseOperating"],
  "d_a": ["DepreciationDepletionAndAmortizationExcludingAmortizationOfDeferredSalesCommissions","DepreciationDepletionAndAmortizationExcludingAmortizationOfDebtIssuanceCosts","DepreciationAndAmortizationNetOfAmortizationOfDebtIssuanceCosts"],
  "depreciation_and_amortization": ["DepreciationDepletionAndAmortizationExcludingAmortizationOfDeferredSalesCommissions"],
  "capex": ["PaymentsForCapitalExpenditures","PaymentToCapitalExpenditures","PaymentsToAcquireCapitalExpendituresNet","PaymentsForConstructionInProcess"],
  "capital_expenditures": ["PaymentsForCapitalExpenditures","PaymentsForConstructionInProcess"],
  "cash": ["Cash","CashAndCashEquivalentsExcludingRestrictedCash"],
  "total_debt": ["LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities","DebtAndCapitalLeaseObligations","ShortAndLongTermDebt","DebtLongTermAndShortTermCombinedAmountNet"],
  "stockholders_equity": ["PartnersCapital"],
  "inventory": ["AirlineRelatedInventoryNet","RetailRelatedInventoryMerchandise","InventoryRealEstate","PublicUtilitiesInventory","InventoryFinishedGoodsNetOfReserves","InventoryNetOfAllowancesCustomerAdvancesAndProgressBillings"],
  "diluted_share_count": ["WeightedAverageLimitedPartnershipUnitsOutstandingDiluted","WeightedAverageNumberOfCommonAndCommonEquivalentSharesOutstanding"],
  "basic_share_count": ["WeightedAverageLimitedPartnershipUnitsOutstanding"],
  "shares_outstanding": ["EntityCommonStockSharesOutstanding"],
  "eps": ["NetIncomeLossNetOfTaxPerOutstandingLimitedPartnershipUnitDiluted"],
  "basic_eps": ["NetIncomeLossPerOutstandingLimitedPartnershipUnitBasicNetOfTax"],
  "dividend_per_share": ["DistributionMadeToLimitedPartnerDistributionsDeclaredPerUnit","CommonStockDividendsAndDividendEquivalentsPerShareDeclared"],
  "dividends_per_share": ["DistributionMadeToLimitedPartnerDistributionsDeclaredPerUnit"],
  "restructuring_charges": ["RestructuringCosts","RestructuringSettlementAndImpairmentProvisions","RestructuringAndRelatedCostIncurredCost","RestructuringExitandImpairmentCharges","RestructuringAndOtherChargesNet","RestructuringChargesAndAssetWriteOffs"],
  "stock_based_compensation": ["AllocatedShareBasedCompensationExpenseEquityAndLiability"],
}
for _m, _ls in EXTRA.items():
    locals_, bal, pt = CANON[_m]
    CANON[_m] = (locals_ + _ls, bal, pt)

def localname(qn): return qn.split(":",1)[1] if ":" in qn else qn

# reverse index: local-name -> set of metrics it's canonical for (to flag cross-family wrong links)
LOCAL2METRIC = collections.defaultdict(set)
for met,(locals_,_,_) in CANON.items():
    for ln in locals_: LOCAL2METRIC[ln].add(met)

def load_menus():
    menus = {}
    for f in (CLRV/"menus").glob("*.json"):
        rows = json.loads(f.read_text())
        menus[f.stem] = {r["qname"]: r for r in rows if r.get("qname")}
    return menus

def main():
    menus = load_menus()
    gt_anchor = json.loads((CLRV/"gt_anchor.json").read_text())
    gt = {}
    for t, menu in menus.items():
        bylocal = collections.defaultdict(list)
        for qn, r in menu.items(): bylocal[localname(qn)].append(r)
        for met,(locals_,bal,pt) in CANON.items():
            present = []
            for ln in locals_:
                for r in bylocal.get(ln, []):
                    present.append(r)
            if present:
                present.sort(key=lambda r: -int(r.get("usage") or 0))
                gt[f"{t}|{met}"] = {"gt":[r["qname"] for r in present],
                                    "primary": present[0]["qname"], "in_menu": True,
                                    "exp_balance": bal, "exp_ptype": pt}
            else:
                gt[f"{t}|{met}"] = {"gt": [], "primary": None, "in_menu": False,
                                    "exp_balance": bal, "exp_ptype": pt}
    (CLRV/"gt_dataset.json").write_text(json.dumps(gt))
    (CLRV/"local2metric.json").write_text(json.dumps({k:sorted(v) for k,v in LOCAL2METRIC.items()}))
    # coverage + value-anchor cross-validation
    in_menu = [k for k,v in gt.items() if v["in_menu"]]
    print(f"companies with menus: {len(menus)}")
    print(f"GT cells: {len(gt)} ; with concept in menu: {len(in_menu)}")
    # validate canonical GT vs value-anchor (signal A) on guidance cos
    agree = disagree = 0; dis_ex=[]
    for k, q in gt_anchor.items():
        if k in gt and gt[k]["in_menu"]:
            if q in gt[k]["gt"]: agree += 1
            else: disagree += 1; dis_ex.append((k, localname(q), [localname(x) for x in gt[k]["gt"]]))
    print(f"\nvalue-anchor (signal A) vs canonical GT, where both exist: agree={agree} disagree={disagree}")
    print("  (disagreements are usually value-anchor COINCIDENCES, confirming A alone is noisy:)")
    for k,va,g in dis_ex[:15]: print(f"    {k}: VA={va}  canonGT={g}")
    # per-metric menu coverage across all companies
    print("\n=== per-metric: companies that report it (concept in menu) ===")
    cov = collections.Counter()
    for k,v in gt.items():
        if v["in_menu"]: cov[k.split('|',1)[1]] += 1
    for met,n in cov.most_common():
        print(f"  {met:28s} {n}/{len(menus)}")

if __name__ == "__main__":
    main()
