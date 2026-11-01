export const meta = {
  name: 'concept-link-longtail',
  description: 'Run the matcher on 1,395 self-labeled long-tail concepts to measure recall',
  phases: [{ title: 'Match', detail: 'per company: resolve humanized concept labels back to qnames' }],
}

const CLP = '/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp'
const tickers = ['ACN','AIR','ALV','ASO','AVGO','BRZE','BURL','CCL','CHWY','CMC','CNM','CTAS','DLTR','DOCU','DRI','FDX','FIVE','GIS','GME','HQY','KBH','LULU','MU','NFE','OLLI','OXM','PAYX','PHR','SAIC','SMTC','WGO']

const PROMPT = (t) => `You are a precise XBRL concept matcher. Read ${CLP}/longtail/${t}.json.
It has "menu" (the concepts this company reports: {qname,label,usage}) and "queries" (an array with
"slug" = a metric name; ignore any other fields).

For EACH query slug, pick the ONE menu qname that IS exactly that metric (same accounting line), or null.
SAME metric only — a related-but-different line is NOT a match (cost-of-revenue ≠ revenue; a subtotal ≠
the total; basic ≠ diluted). When two menu concepts are equally the metric, pick higher usage. When the
slug is genuinely ambiguous among near-duplicate concepts, abstain (null).

Write ${CLP}/longtail_picks/${t}.json = JSON array [{"slug","qname"(or null)}], covering every query slug
exactly once. Return only "${t}: <n_links>/<total>".`

phase('Match')
await parallel(tickers.map(t => () => agent(PROMPT(t), { label: `lt:${t}`, phase: 'Match' })))
return { companies: tickers.length, out: `${CLP}/longtail_picks` }
