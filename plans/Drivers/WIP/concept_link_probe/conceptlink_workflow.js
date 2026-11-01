export const meta = {
  name: 'concept-link-census',
  description: 'LLM-pick-from-menu concept matcher + adversarial refute, over all guidance companies',
  phases: [
    { title: 'Pick', detail: 'per-company: resolve each slug to a menu qname or NONE' },
    { title: 'Verify', detail: 'per-company: adversarially refute every emitted link' },
  ],
}

const CLP = '/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp'
const tickers = ['ACN','AIR','ALV','ASO','AVGO','BRZE','BURL','CCL','CHWY','CMC','CNM','CTAS','DLTR','DOCU','DRI','FDX','FIVE','GIS','GME','HQY','KBH','LULU','MU','NFE','OLLI','OXM','PAYX','PHR','SAIC','SMTC','WGO']

const PICK = (t) => `You are a precise XBRL concept matcher. Read ${CLP}/bundles_per/${t}.json.
It has "menu" (the concepts this company reports: {qname,label,usage} — the ONLY allowed answers),
"pos_slugs" (real metric names), "neg_slugs" (conceptless drivers).

For EACH slug in pos_slugs AND neg_slugs, pick the ONE menu qname that IS exactly that metric
(the same accounting line a filer tags for it), or null.

PRECISION RULES (a WRONG link is the cardinal sin; unsure → null):
1. SAME metric only. A related-but-different line is NOT a match:
   cost_of_revenue/cogs ≠ revenue; income_taxes_paid ≠ net_income; income_tax_expense ≠ net_income;
   operating_cash_flow ≠ operating_income; gross_profit($) is for "gross_profit" but NOT "gross_margin"(%).
2. basic vs diluted EPS/shares are DIFFERENT — match the one named; bare "eps"/"share_count" with BOTH
   in menu → prefer diluted, confidence med.
3. Abstain (null) for: ratios/margins (operating_margin, gross_margin, ebitda_margin, net_margin),
   EBITDA/adjusted EBITDA, free cash flow/FCF (no single us-gaap line), any *_growth/*_yoy/*_change,
   and non-financial/macro/event drivers (oil_price, ceo_resignation, tariffs...). neg_slugs are null
   UNLESS a menu concept genuinely IS that exact line.
4. Two menu concepts equally the metric (e.g. Revenues & RevenueFromContractWithCustomer...) → higher
   usage, confidence med. adjusted_/non_gaap_ prefix → same GAAP concept as base (adjusted_eps →
   EarningsPerShareDiluted) med; but adjusted_ebitda stays null.

Write ${CLP}/picks/${t}.json = JSON array [{"slug","qname"(or null),"confidence":"high"|"med"|"low","reason":"<=10 words"}],
covering EVERY pos_slug and neg_slug exactly once. Return only "${t}: <n_links> links".`

const VERIFY = (t) => `You are an adversarial XBRL link auditor. Your job: REFUTE wrong links. Default to
refuted=true when uncertain — a wrong link is the cardinal sin.
Read ${CLP}/picks/${t}.json (emitted links) and ${CLP}/bundles_per/${t}.json (the menu).
For EACH entry whose "qname" is NOT null, decide if the slug→qname link is the SAME accounting metric.
REFUTE (real=false) if the concept is a related-but-different line (cost vs revenue, tax vs income,
cash-flow vs income, a ratio mapped to a $ concept, basic vs diluted mismatch, a segment/subtotal
instead of the consolidated line, or any semantic mismatch). CONFIRM (real=true) only if it is
unambiguously the same metric the slug names.
Write ${CLP}/verdicts/${t}.json = JSON array [{"slug","qname","real":true|false,"why":"<=12 words"}]
for every non-null link. Return only "${t}: <n_refuted> refuted of <n_links>".`

phase('Pick')
await parallel(tickers.map(t => () => agent(PICK(t), { label: `pick:${t}`, phase: 'Pick' })))

phase('Verify')
await parallel(tickers.map(t => () => agent(VERIFY(t), { label: `verify:${t}`, phase: 'Verify' })))

return { companies: tickers.length, picksDir: `${CLP}/picks`, verdictsDir: `${CLP}/verdicts` }
