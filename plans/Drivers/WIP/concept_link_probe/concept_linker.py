#!/usr/bin/env python3
"""DriverUpdate → XBRL Concept linker (the deliverable algorithm).

link(company, slug, menu, llm) -> qname or None

Deterministic guards (G0 event/macro, G1 derived/ratio, G2 non-GAAP) abstain up front on the
metric KINDS that have no exact GAAP line concept — these encode the schema's fact_type routing
+ the GAAP/non-GAAP rule, NOT a per-metric dictionary. Everything else goes to the LLM, which
picks the one menu concept that IS the metric (or NONE), and an adversarial verify that abstains
when it can refute the pick.

`menu`  = the company's reported concepts: [{"qname","label","usage"}]  (built by QUERY_2A).
`llm`   = a callable(prompt:str)->str. In production wire to claude_agent_sdk (subscription,
          NO api key — see CLAUDE.md). Pluggable so the logic is testable without a live model.

Value is NOT an input: inference is value-withheld. Value+period anchoring is the offline
answer-key/auditor (see labeler.py), never an inference signal.
"""
import re, json

# G0 — events / macro-exogenous causes (in production: fact_type == action_event, or an
# exogenous cause). No company line item IS the event. Minimal seed patterns; production routes
# by fact_type so this list is not load-bearing.
G0 = re.compile(r"(resignation|appointment|acquisition_announcement|buyback_authoriz|"
                r"share_buyback|repurchase_authoriz|dividend_initiation|stock_split|downgrade|"
                r"upgrade|litigation|settlement|recall|breach|closure|strike|approval|"
                r"contract_award|refinanc|^oil_price|gas_price|interest_rates?$|exchange_impact|"
                r"commodity_costs?$|^inflation$|^tariffs?$|weather|freight_costs?$)")
# G1 — ratios / derived / growth. No exact GAAP line concept (a $ subtotal is a DIFFERENT metric).
# NB: effective/tax_rate is deliberately NOT here (us-gaap:EffectiveIncomeTaxRate… is real).
G1 = re.compile(r"(margin$|_margin|_growth|_yoy|_change$|_ratio$|^roic$|^roe$|^roa$|^roce$|"
                r"^ebitda|_ebitda|^fcf$|free_cash_flow|_per_square|_penetration|_mix$|_turns$)")
# G2 — non-GAAP/adjusted. The adjusted value ≠ the GAAP concept's fact; the base metric carries
# the concept via BASE_METRIC.
G2 = re.compile(r"^(adjusted_|non_gaap_|underlying_|core_|organic_|pro_forma_)")

def guard(slug):
    """Return the guard name that abstains this slug, or None to proceed to the LLM."""
    s = (slug or "").lower()
    if G2.match(s):            return "G2_nongaap"
    if G0.search(s):           return "G0_event_macro"
    if G1.search(s):           return "G1_derived_ratio"
    return None

PICK_PROMPT = """You are a precise XBRL concept matcher. Company {ticker}.
Menu (the ONLY allowed answers): {menu}
Metric: "{slug}"
Pick the ONE menu qname that IS exactly this metric (the same accounting line a filer tags), or null.
SAME metric only — a related-but-different line is NOT a match (cost-of-revenue≠revenue;
income-tax≠net-income; a subtotal≠the total; basic≠diluted). Two equal candidates → higher usage.
Output JSON: {{"qname": "us-gaap:..." or null}}"""

VERIFY_PROMPT = """STRICT XBRL link auditor — default to refuted when unsure (a wrong link is the
cardinal sin). Company {ticker}. Proposed: metric "{slug}" -> {qname} (label: "{label}").
Refute if the concept is a related-but-different line, a different value (GAAP vs non-GAAP, gross
vs net, subtotal vs total), the wrong statement, or a dimension instead of the consolidated line.
Output JSON: {{"real": true|false}}"""

def _parse_qname(txt):
    m = re.search(r'"qname"\s*:\s*"([^"]+)"', txt or "")
    return m.group(1) if m else None

def _parse_real(txt):
    m = re.search(r'"real"\s*:\s*(true|false)', (txt or "").lower())
    return m.group(1) == "true" if m else False   # default refuted

def link(ticker, slug, menu, llm):
    """Resolve (company, metric) -> qname or None. Value-withheld. llm: callable(str)->str."""
    if guard(slug):
        return None
    menu_str = "; ".join(f'{c["qname"]}|{c.get("label","")}' for c in menu)
    pick = _parse_qname(llm(PICK_PROMPT.format(ticker=ticker, slug=slug, menu=menu_str)))
    if not pick:
        return None
    if pick not in {c["qname"] for c in menu}:      # no hallucinated concepts
        return None
    label = next((c.get("label") for c in menu if c["qname"] == pick), "")
    real = _parse_real(llm(VERIFY_PROMPT.format(ticker=ticker, slug=slug, qname=pick, label=label)))
    return pick if real else None


def demo():
    """Self-check: guards are deterministic; decision logic honors pick + refute. No live LLM."""
    # G0/G1/G2 abstain
    assert guard("ceo_resignation") == "G0_event_macro"
    assert guard("oil_price") == "G0_event_macro"
    assert guard("gross_margin") == "G1_derived_ratio"
    assert guard("ebitda") == "G1_derived_ratio"
    assert guard("revenue_growth") == "G1_derived_ratio"
    assert guard("adjusted_eps") == "G2_nongaap"
    assert guard("non_gaap_net_income") == "G2_nongaap"
    # real metrics pass the guard
    assert guard("revenue") is None
    assert guard("tax_rate") is None and guard("effective_tax_rate") is None   # real concept
    assert guard("capex") is None and guard("sg_a") is None

    menu = [{"qname": "us-gaap:Revenues", "label": "Revenues", "usage": 9},
            {"qname": "us-gaap:CostOfRevenue", "label": "Cost of Revenue", "usage": 9}]
    # stub LLM: picks Revenues for revenue, confirms real
    def good(p):
        if "matcher" in p: return '{"qname": "us-gaap:Revenues"}'
        return '{"real": true}'
    assert link("X", "revenue", menu, good) == "us-gaap:Revenues"
    # guarded slug never calls the LLM
    assert link("X", "ebitda", menu, good) is None
    # adversary refutes -> abstain
    def refute(p):
        if "matcher" in p: return '{"qname": "us-gaap:CostOfRevenue"}'
        return '{"real": false}'
    assert link("X", "revenue", menu, refute) is None
    # hallucinated qname (not in menu) -> abstain
    def hallu(p):
        if "matcher" in p: return '{"qname": "us-gaap:MadeUpConcept"}'
        return '{"real": true}'
    assert link("X", "revenue", menu, hallu) is None
    print("concept_linker demo: OK")


if __name__ == "__main__":
    demo()
