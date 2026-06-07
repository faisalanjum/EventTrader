export const meta = {
  name: 'driver-menu-build',
  description: 'Driver-catalog SEED build for ANY industry. Step 0: resolve_driver_scope.py turns args.industry into the ticker list (default Restaurants). Step A: fetch_company_sources.py pulls ALL non-news sources (8-K/10-K/10-Q + transcripts + fiscal KPIs) WITH real text + each event source_id; NO >2% filter. Step B: 1 blind subagent per company coins candidate driver_names (each with source_id) from real content per DriverOntology. Step C: deterministic JS grouping into per-driver records writes _menu_<slug>_seed.json. Read-only Neo4j; no graph writes. Pass args = { industry: "<name>" }.',
  phases: [
    { title: 'Resolve',  detail: 'resolve_driver_scope.py: args.industry → tickers (default Restaurants)' },
    { title: 'Fetch',    detail: 'fetch_company_sources.py → _sources_<ticker>.json (real text + source_id, tagged)' },
    { title: 'Menus',    detail: 'one blind subagent per company coins names + source_id from real content' },
    { title: 'Converge', detail: 'JS groups candidates → per-driver records; write _menu_<slug>_seed.json' },
  ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'

const SCOPE_SCHEMA = { type:'object', additionalProperties:true, required:['slug','tickers'], properties:{
  scope_name:{type:'string'}, slug:{type:'string'}, tickers:{type:'array', items:{type:'string'}}, n_tickers:{type:'integer'} } }

const MENU_SCHEMA = { type:'object', additionalProperties:false,
  required:['ticker','candidate_count','candidates','skipped_count','notes'],
  properties:{
    ticker:{type:'string'}, candidate_count:{type:'integer'},
    candidates:{type:'array', items:{type:'object', additionalProperties:false,
      required:['driver_name','evidence_quote','source_type','source_id','date','xbrl_or_null'],
      properties:{ driver_name:{type:'string'}, evidence_quote:{type:'string', description:'actual words from the source content (or the raw KPI label) that justify it'}, source_type:{type:'string', description:'8-K / 10-K / 10-Q / transcript / fiscal.ai-kpi'}, source_id:{type:'string', description:'the events[].source_id of the event you quoted; for a KPI use "fiscal_ai:<ticker>:<metric>"'}, date:{type:'string', description:'event date YYYY-MM-DD; "" for a KPI'}, xbrl_or_null:{type:'string'} }}},
    skipped_count:{type:'integer'}, notes:{type:'array', items:{type:'string'}} } }

const CONV_SCHEMA = { type:'object', additionalProperties:false,
  required:['file_written','total_candidates','total_distinct_drivers'],
  properties:{ file_written:{type:'string'}, total_candidates:{type:'integer'}, total_distinct_drivers:{type:'integer'} } }

const RULES = `NAMING RULES (authority = ${DIR}/DriverOntology.md — READ it; summary for speed):
- driver_name = the reusable CAUSE as a specific lower_snake_case noun. As specific as the evidence allows; NEVER a broad/category word alone (no bare demand/macro/sector/sentiment).
- Order: concrete thing or actor -> needed detail -> metric/mechanism. e.g. restaurant_traffic, same_store_sales, oil_price.
- EARNINGS convention: {metric}_surprise (reported vs consensus) or {metric}_guidance (forward outlook): eps_surprise, revenue_surprise, revenue_guidance, gross_margin_guidance. beat/miss/raised/lowered are NOT in the name.
- BANNED inside the name: state/verbs (beat, cut, declined, transition, opening, growth), direction/impact (long/short), dates/quarters/years, numbers/magnitudes/units (bps, percent, usd), ANY company ticker or legal name (own OR peer), person names, source/provider labels, XBRL prefixes, metaphors/sentiment, bare category words, stopwords. (Products/brands/segments ARE allowed: a brand metric like taco_bell_same_store_sales is its OWN driver, separate from same_store_sales.)
- Keep standard phrases whole: gross_margin, free_cash_flow, same_store_sales, net_interest_margin.
- Vague text -> SKIP (don't invent).
- fiscal.ai KPI labels are RAW SUGGESTIONS ONLY: rewrite each into a standard driver_name; never use the raw label as the NAME.`

const industry = (args && args.industry) || 'Restaurants'

phase('Resolve')
const scope = await agent(`Run this EXACT command with Bash and return its JSON output (parse stdout into the schema):
${PY} ${DIR}/workflows/resolve_driver_scope.py --industry ${JSON.stringify(industry)}
It prints { scope_name, slug, tickers, n_tickers }. If it exits NON-ZERO, report the exact error and do NOT invent tickers (return an empty tickers array).`, {schema:SCOPE_SCHEMA, label:'resolve', phase:'Resolve'})
const SLUG = scope.slug, TICKERS = scope.tickers || [], INDUSTRY = scope.scope_name || industry
if (!TICKERS.length) throw new Error(`resolve_driver_scope.py returned 0 tickers for industry "${industry}" — stopping (prevents fetch_company_sources.py defaulting to SBUX).`)

phase('Fetch')
const fetched = await agent(`Run this EXACT command with Bash (it pulls all non-news sources WITH real text for the ${TICKERS.length} ${INDUSTRY} companies and writes _sources_<ticker>.json):
${PY} ${DIR}/workflows/fetch_company_sources.py ${TICKERS.join(' ')}
Then report the per-ticker summary lines it printed (event counts + chars + empty count) and confirm every ticker wrote a file with empty=0. If any ticker errored or has empty>5, say so explicitly.`, {label:'fetch-sources', phase:'Fetch'})

phase('Menus')
const menus = (await parallel(TICKERS.map(t => () => agent(`Repo root /home/faisal/EventMarketDB. You build the candidate driver-name menu for ONE company only: ${t}. You are BLIND — you see only ${t}, no other company's names, no shared catalog.

${RULES}

LOAD THIS COMPANY'S REAL SOURCE TEXT: run Bash \`cat ${DIR}/_sources_${t}.json\` to load the full file (it is LARGE — use cat or python via Bash; do NOT use the Read tool, it truncates). The JSON has:
- fiscal_kpis: [raw KPI names]  → rewrite each into a standard driver_name.
- events: [{source_id, source_type, date, daily_stock, high_signal, is_earnings, content}] → content is the REAL document text (MD&A, Risk Factors, EX-99.1 press releases, prepared remarks, Q&A). source_id = the stable id of that event.

TASK: REVIEW EVERY event in the list IN ORDER before finalizing (do not skim or stop early; later events count too), and from the fiscal KPIs plus any event text with source-grounded evidence, coin SPECIFIC candidate driver_names per the rules. Not judging the true driver — just plausible, source-grounded candidate names from real material. MINE THE PROSE for narrative drivers too (input/commodity costs, tariffs, labor/wages, traffic vs pricing, demand, FX, specific products/segments), not just headline metrics. Skip vague items.
For each candidate return: driver_name, evidence_quote, source_type, source_id, date, xbrl_or_null ("null" if none obvious). EVIDENCE is EITHER (a) a real quote from an event's content → source_id = that event's source_id, source_type + date = that event's; OR (b) a fiscal.ai KPI you rewrote → source_type = "fiscal.ai-kpi", source_id = "fiscal_ai:${t}:<metric>", date = "", evidence_quote = the raw KPI label.
Dedup within ${t} only. Return the MENU_SCHEMA object.`, {schema:MENU_SCHEMA, label:`menu:${t}`, phase:'Menus'}))) ).filter(Boolean)

phase('Converge')
// Deterministic grouping (structure -> code): ONE record per DISTINCT driver_name, every candidate's evidence preserved.
const byName = {}
for (const m of menus) for (const c of (m.candidates || [])) {
  const k = (c.driver_name || '').trim()
  if (!k) continue
  if (!byName[k]) byName[k] = { driver_name:k, canonical_name:k, _companies:new Set(), evidence_refs:[], optional_links:{ xbrl_concept:null, xbrl_member:null, guidance_ref:null } }
  byName[k]._companies.add(m.ticker)
  byName[k].evidence_refs.push({ company:m.ticker, source_type:c.source_type, source_id:c.source_id, date:c.date, quote:c.evidence_quote })
  const xb = (c.xbrl_or_null || '').trim()
  if (xb && xb.toLowerCase() !== 'null' && !byName[k].optional_links.xbrl_concept) byName[k].optional_links.xbrl_concept = xb
}
const catalog = Object.values(byName).map(r => ({ driver_name:r.driver_name, canonical_name:r.canonical_name, companies:[...r._companies], evidence_refs:r.evidence_refs, optional_links:r.optional_links }))
const shared_drivers = catalog.filter(r => r.companies.length >= 2).map(r => ({ driver_name:r.driver_name, companies:r.companies }))
const total_candidates = catalog.reduce((s,r) => s + r.evidence_refs.length, 0)
const seed = { industry:INDUSTRY, catalog, analysis:{ shared_drivers, total_distinct_drivers:catalog.length, total_candidates } }

const conv = await agent(`Write this EXACT JSON verbatim (do NOT alter, summarize, reorder, or reformat the data — write it byte-for-byte) to ${DIR}/_menu_${SLUG}_seed.json using the Write tool. Then return CONV_SCHEMA with file_written + the counts (total_distinct_drivers=${catalog.length}, total_candidates=${total_candidates}).

SEED JSON:
${JSON.stringify(seed)}`, {schema:CONV_SCHEMA, label:'write-seed', phase:'Converge'})

return { industry:INDUSTRY, slug:SLUG, n_tickers:TICKERS.length, fetch_summary: (fetched||'').slice(0,1500), menu_counts: menus.map(m=>({t:m.ticker, n:m.candidate_count, skipped:m.skipped_count})), distinct_drivers: catalog.length, total_candidates, converge: conv }
