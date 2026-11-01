export const meta = {
  name: 'concept-link-panel',
  description: 'Perspective-diverse 3-lens verification of audit-set concept links',
  phases: [{ title: 'Panel', detail: 'each link judged by same-value, filer-intent, name-precision lenses' }],
}

const CLP = '/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp'
const tickers = ['ACN','AIR','ALV','ASO','AVGO','BURL','CCL','CHWY','CMC','CNM','CTAS','DLTR','DOCU','DRI','FDX','FIVE','GIS','GME','HQY','LULU','MU','NFE','OLLI','OXM','PAYX','PHR','SAIC','SMTC','WGO']

const LENSES = {
  value: `LENS = SAME-VALUE. Refute (real=false) if the XBRL fact for this concept would carry a
DIFFERENT numeric value than the metric names: GAAP vs non-GAAP/adjusted, gross vs net, a subtotal
vs the total, a per-share vs absolute, basic vs diluted mismatch, cost vs the revenue it offsets.
Confirm (real=true) only if the fact's value IS the metric's value.`,
  filer: `LENS = FILER-INTENT. Refute if a filer preparing this company's statements would NOT tag THIS
concept for THIS metric — wrong statement (cash-flow item tagged for an income metric), a
related-but-different line, or a dimension/member instead of the consolidated line. Confirm only if a
filer would naturally use this exact concept for this metric.`,
  name: `LENS = NAME-PRECISION. Refute if the concept's standard label denotes a BROADER or NARROWER or
DIFFERENT accounting line than the metric name (depreciation vs depreciation+depletion+amortization
only when the slug is strictly narrower; revenue vs cost-of-revenue; income-tax vs net-income).
Confirm only if the label denotes the SAME line the metric names (synonyms/abbreviations OK).`,
}

phase('Panel')
const jobs = []
for (const t of tickers) {
  for (const [lens, desc] of Object.entries(LENSES)) {
    jobs.push(() => agent(
      `You are a STRICT XBRL link auditor. Default to real=false when uncertain — a wrong link is the
cardinal sin. Read ${CLP}/panel_in/${t}.json: an array of {slug, qname, concept_label} — proposed
links for company ${t}.

${desc}

For EACH link, output your verdict under THIS lens only. Write ${CLP}/panel_out/${t}_${lens}.json =
JSON array [{"slug","qname","real":true|false,"why":"<=12 words"}] covering every input link.
Return only "${t}/${lens}: <n_real>/<total> real".`,
      { label: `${lens}:${t}`, phase: 'Panel' }))
  }
}
await parallel(jobs)
return { links: 124, companies: tickers.length, lenses: 3, out: `${CLP}/panel_out` }
