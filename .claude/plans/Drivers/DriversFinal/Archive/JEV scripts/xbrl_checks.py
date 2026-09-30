"""(2026-09-30 fix: guard words now match whole words only; before, "ratio" matched inside "operations" and blocked real line items. Still a crude word list: see JEV.md §6.9.) Code checks written FRESH from the rule text (not from the old linker code): guards = rule 6.4 (+ FINAL_DESIGN XC-05 G0-G2), vetoes = rule 6.6 A-D. They can only REFUSE a link.
`concept` = dict(q, label, pt (period_type), ct (concept_type)). `name` = the metric name, lowercase words. Run this file to execute its self-check."""
G0 = ("resignation", "buyback", "repurchase", "oil price", "interest rate", "tariff", "weather")                       # events and macro causes
G1 = ("margin", "growth", "ratio", "return on", "roic", "ebitda", "free cash flow", "per square", "mix")              # ratios, derived and growth figures (tax rates are NOT here)
G2 = ("adjusted", "non-gaap", "non gaap", "core", "organic", "pro forma")                                              # non-GAAP or adjusted
import re
def _has(n, words): return next((w for w in words if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", n)), None)   # whole words only: "ratio" must not match "operations"
def guard(name):
    n = name.lower(); return (f"G0:{w}" if (w := _has(n, G0)) else None) or (f"G1:{w}" if (w := _has(n, G1)) else None) or (f"G2:{w}" if (w := _has(n, G2)) else None)
def local(q): return q.split(":")[-1]
def veto(name, c):
    """Return the code of the first veto that fires, else None."""
    n = name.lower(); lq = local(c["q"]); ct = (c.get("ct") or "").lower()
    if ("shares outstanding" in n and "weighted" not in n and "average" not in n) and c["pt"] != "instant": return "A:point-in-time share count must be an instant"
    if any(w in n for w in ("earnings per share", "shares outstanding", "share count")) and "basic" not in n and "Basic" in lq: return "B:bare EPS or share count means diluted, never basic"
    if "per share" in n and "pershare" not in ct: return "C:per-share metric must not map to a total-dollar line"
    if "selling general and administrative" in n and lq in ("GeneralAndAdministrativeExpense", "SellingAndMarketingExpense", "SellingExpense", "MarketingExpense"): return "D:SG&A vs a component"
    if n == "operating expenses" and lq == "SellingGeneralAndAdministrativeExpense": return "D:operating expenses vs SG&A"
    if n == "total debt" and lq == "NotesPayable": return "D:total debt vs notes payable"
    return None
if __name__ == "__main__":
    inst = dict(pt="instant", ct="xbrli:sharesItemType"); dur = dict(pt="duration", ct="xbrli:sharesItemType")
    assert guard("free cash flow") and guard("adjusted ebitda") and guard("gross margin") and guard("revenue growth rate") and guard("adjusted earnings per share") and guard("share buyback")
    assert guard("income tax expense") is None and guard("effective tax rate") is None and guard("net income") is None and guard("research and development expense") is None
    assert veto("shares outstanding", dict(q="us-gaap:WeightedAverageNumberOfSharesOutstandingBasic", **dur))
    assert veto("shares outstanding", dict(q="dei:EntityCommonStockSharesOutstanding", **inst)) is None
    assert veto("earnings per share", dict(q="us-gaap:EarningsPerShareBasic", pt="duration", ct="us-gaap:perShareItemType")).startswith("B")
    assert veto("earnings per share", dict(q="us-gaap:EarningsPerShareDiluted", pt="duration", ct="us-gaap:perShareItemType")) is None
    assert veto("basic earnings per share", dict(q="us-gaap:EarningsPerShareBasic", pt="duration", ct="us-gaap:perShareItemType")) is None
    assert veto("dividend per share", dict(q="us-gaap:PaymentsOfDividends", pt="duration", ct="xbrli:monetaryItemType")).startswith("C")
    assert veto("selling general and administrative expense", dict(q="us-gaap:GeneralAndAdministrativeExpense", pt="duration", ct="xbrli:monetaryItemType")).startswith("D")
    assert veto("operating expenses", dict(q="us-gaap:SellingGeneralAndAdministrativeExpense", pt="duration", ct="xbrli:monetaryItemType")).startswith("D")
    assert veto("total debt", dict(q="us-gaap:NotesPayable", pt="instant", ct="xbrli:monetaryItemType")).startswith("D")
    assert veto("total revenue", dict(q="us-gaap:Revenues", pt="duration", ct="xbrli:monetaryItemType")) is None
    assert guard("investing cash flow from discontinued operations") is None and guard("net cash provided by operating activities") is None and guard("median duration of response") is None
    assert guard("leverage ratio") and guard("expense ratio") and guard("adjusted net income") and guard("net margin")
    print("xbrl_checks self-check passed")
