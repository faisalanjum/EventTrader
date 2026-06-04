export const meta = {
  name: 'driver-menu-build',
  description: 'Driver-catalog SEED build. Step A: fetch_company_sources.py pulls ALL non-news sources (8-K/10-K/10-Q + transcripts + fiscal KPIs) WITH real text (MD&A, Risk Factors, EX-99.1 press releases, prepared remarks + Q&A), targeted + truncated, tagged (high_signal, is_earnings); NO >2% filter. Step B: 1 blind subagent per company coins candidate driver_names from that real content per DriverOntology. Step C: convergence/dedup pass writes the seed review file. Read-only Neo4j; no graph writes.',
  phases: [
    { title: 'Fetch',    detail: 'fetch_company_sources.py → _sources_<ticker>.json (real text, tagged)' },
    { title: 'Menus',    detail: 'one blind subagent per company coins names from real content' },
    { title: 'Converge', detail: 'dedup + cross-company sharing + pass-checks; write seed file' },
  ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'
const TICKERS = ['SBUX','MCD','CMG','YUM','DRI','TXRH','SHAK','WING','CAKE','EAT','PZZA','CBRL','BLMN','QSR']

const MENU_SCHEMA = { type:'object', additionalProperties:false,
  required:['ticker','candidate_count','candidates','skipped_count','notes'],
  properties:{
    ticker:{type:'string'}, candidate_count:{type:'integer'},
    candidates:{type:'array', items:{type:'object', additionalProperties:false,
      required:['driver_name','evidence_quote','source_type','date','xbrl_or_null'],
      properties:{ driver_name:{type:'string'}, evidence_quote:{type:'string', description:'actual words from the source content that justify it'}, source_type:{type:'string', description:'8-k / 10-k / 10-q / transcript / fiscal.ai-kpi'}, date:{type:'string'}, xbrl_or_null:{type:'string'} }}},
    skipped_count:{type:'integer'}, notes:{type:'array', items:{type:'string'}} } }

const CONV_SCHEMA = { type:'object', additionalProperties:false,
  required:['file_written','total_candidates','total_distinct_names','shared_names','exact_dup_pairs','pass_violations','convergence_summary'],
  properties:{
    file_written:{type:'string'}, total_candidates:{type:'integer'}, total_distinct_names:{type:'integer'},
    shared_names:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','companies'], properties:{ driver_name:{type:'string'}, companies:{type:'array', items:{type:'string'}} }}},
    exact_dup_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why'], properties:{ a:{type:'string'}, b:{type:'string'}, why:{type:'string'} }}},
    pass_violations:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','company','rule'], properties:{ driver_name:{type:'string'}, company:{type:'string'}, rule:{type:'string'} }}},
    convergence_summary:{type:'string'} } }

const RULES = `NAMING RULES (authority = ${DIR}/DriverOntology.md — READ it; summary for speed):
- driver_name = the reusable CAUSE as a specific lower_snake_case noun. As specific as the evidence allows; NEVER a broad/category word alone (no bare demand/macro/sector/sentiment).
- Order: concrete thing or actor -> needed detail -> metric/mechanism. e.g. restaurant_traffic, same_store_sales, oil_price.
- EARNINGS convention: {metric}_surprise (reported vs consensus) or {metric}_guidance (forward outlook): eps_surprise, revenue_surprise, revenue_guidance, gross_margin_guidance. beat/miss/raised/lowered are NOT in the name.
- BANNED inside the name: state/verbs (beat, cut, declined, transition, opening, growth), direction/impact (long/short), dates/quarters/years, numbers/magnitudes/units (bps, percent, usd), ANY company ticker or legal name (own OR peer), person names, source/provider labels, XBRL prefixes, metaphors/sentiment, bare category words, stopwords. (Products/brands/segments ARE allowed: a brand metric like taco_bell_same_store_sales is its OWN driver, separate from same_store_sales.)
- Keep standard phrases whole: gross_margin, free_cash_flow, same_store_sales, net_interest_margin.
- Vague text -> SKIP (don't invent).
- fiscal.ai KPI labels are RAW SUGGESTIONS ONLY: rewrite each into a standard driver_name; never use the raw label.`

phase('Fetch')
const fetched = await agent(`Run this EXACT command with Bash (it pulls all non-news sources WITH real text for the 14 Restaurants companies and writes _sources_<ticker>.json):
${PY} ${DIR}/workflows/fetch_company_sources.py ${TICKERS.join(' ')}
Then report the per-ticker summary lines it printed (event counts + chars + empty count) and confirm every ticker wrote a file with empty=0. If any ticker errored or has empty>5, say so explicitly.`, {label:'fetch-sources', phase:'Fetch'})

phase('Menus')
const menus = (await parallel(TICKERS.map(t => () => agent(`Repo root /home/faisal/EventMarketDB. You build the candidate driver-name menu for ONE company only: ${t}. You are BLIND — you see only ${t}, no other company's names, no shared catalog.

${RULES}

LOAD THIS COMPANY'S REAL SOURCE TEXT: run Bash \`cat ${DIR}/_sources_${t}.json\` to load the full file (it is LARGE — use cat or python via Bash; do NOT use the Read tool, it truncates). The JSON has:
- fiscal_kpis: [raw KPI names]  → rewrite each into a standard driver_name.
- events: [{source_type, date, daily_stock, high_signal, is_earnings, content}] → content is the REAL document text (MD&A, Risk Factors, EX-99.1 press releases, prepared remarks, Q&A).

TASK: from the fiscal KPIs AND the real text of the events, coin a list of SPECIFIC candidate driver_names per the rules. Not judging the true driver — just plausible, source-grounded candidate names from real material. MINE THE PROSE for narrative drivers too (input/commodity costs, tariffs, labor/wages, traffic vs pricing, demand, FX, specific products/segments), not just headline metrics. Skip vague items. For each candidate return: driver_name, a short evidence_quote (actual words from the content), source_type, date, xbrl_or_null ("null" if none obvious). Dedup within ${t} only. Return the MENU_SCHEMA object.`, {schema:MENU_SCHEMA, label:`menu:${t}`, phase:'Menus'}))) ).filter(Boolean)

phase('Converge')
const menusJson = JSON.stringify(menus)
const conv = await agent(`Repo root /home/faisal/EventMarketDB. You receive ${menus.length} per-company driver-name menus (Restaurants), each coined BLIND from that company's real source text.

MENUS (json): ${menusJson.slice(0, 90000)}

DO:
1) Write the full data to ${DIR}/_menu_restaurants_seed.json (per-company menus + the analysis below). Use the Write tool.
2) SHARED NAMES: every driver_name independently coined by >=2 companies (the blind-convergence signal). Include the company list per name.
3) EXACT-MEANING DUPLICATES: different strings, SAME meaning AND scope (e.g. average_ticket vs average_check) -> SAME_AS review. A brand/segment metric (taco_bell_same_store_sales) is NOT a duplicate of the company-wide form (same_store_sales) — keep separate.
4) PASS-CHECK VIOLATIONS: any name breaking a rule — broad/category word, a company ticker/legal name (own or peer), or state/impact/date/magnitude baked in.
5) Stats: total candidates, total distinct names, and a 2-3 sentence convergence_summary (did blind producers converge, and did the richer text surface narrative drivers beyond the headline metrics?).
Return the CONV_SCHEMA object (compact; do NOT echo raw candidates, they're in the file).`, {schema:CONV_SCHEMA, label:'converge', phase:'Converge'})

return { fetch_summary: (fetched||'').slice(0,1500), menu_counts: menus.map(m=>({t:m.ticker, n:m.candidate_count, skipped:m.skipped_count})), converge: conv }
