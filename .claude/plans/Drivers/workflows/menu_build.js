export const meta = {
  name: 'driver-menu-pilot-restaurants',
  description: 'Blind per-company driver-name menu build (SEED sources = filings + transcripts + fiscal.ai KPIs; NO news; ALL events with >2% daily_stock, no cap), then a convergence/dedup pass. Read-only on Neo4j; writes one review file; no graph writes. News/macro drivers accrete LIVE in production, not in the seed.',
  phases: [
    { title: 'Probe', detail: 'detect the events+returns query + fiscal.ai KPI query (once)' },
    { title: 'Menus', detail: '14 companies named in parallel, fully blind' },
    { title: 'Converge', detail: 'dedup + cross-company sharing + pass-checks; write review file' },
  ],
}

const PROBE_SCHEMA = { type:'object', additionalProperties:false,
  required:['events_cypher','fiscalai_query','return_field','sample_ticker','sample_count','notes'],
  properties:{
    events_cypher:{type:'string', description:'a PARAMETERIZED read Cypher (param $ticker) returning that company’s 8-K/10-K/10-Q/Transcript events (NO news) with abs(daily_stock) >= 2.0 (percent points): source_type, date, text snippet (<=600 chars), daily_stock. ALL qualifying rows (NO limit), order by abs(daily_stock) desc.'},
    fiscalai_query:{type:'string', description:'the exact sqlite3/python query to list a ticker’s operational KPI names from data/fiscal_ai_segments/fiscal_segments.sqlite (section=Key Performance Indicators)'},
    return_field:{type:'string', description:'which property/relationship holds the daily stock return + the market-relative one'},
    sample_ticker:{type:'string'}, sample_count:{type:'string', description:'#events the query returned for the sample ticker'},
    notes:{type:'array', items:{type:'string'}},
  } }

const MENU_SCHEMA = { type:'object', additionalProperties:false,
  required:['ticker','candidate_count','candidates','skipped_count','notes'],
  properties:{
    ticker:{type:'string'},
    candidate_count:{type:'integer'},
    candidates:{type:'array', items:{type:'object', additionalProperties:false,
      required:['driver_name','evidence_quote','source_type','date','xbrl_or_null'],
      properties:{ driver_name:{type:'string'}, evidence_quote:{type:'string'}, source_type:{type:'string', description:'8-k / 10-k / 10-q / transcript / fiscal.ai-kpi'}, date:{type:'string'}, xbrl_or_null:{type:'string', description:'XBRL concept/member if an obvious anchor, else "null"'} }}},
    skipped_count:{type:'integer', description:'# events skipped as too vague to name'},
    notes:{type:'array', items:{type:'string'}},
  } }

const CONV_SCHEMA = { type:'object', additionalProperties:false,
  required:['file_written','total_candidates','total_distinct_names','shared_names','exact_dup_pairs','pass_violations','convergence_summary'],
  properties:{
    file_written:{type:'string'},
    total_candidates:{type:'integer'}, total_distinct_names:{type:'integer'},
    shared_names:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','companies'], properties:{ driver_name:{type:'string'}, companies:{type:'array', items:{type:'string'}} }}, description:'names independently coined by >=2 companies (the convergence signal)'},
    exact_dup_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why'], properties:{ a:{type:'string'}, b:{type:'string'}, why:{type:'string'} }}, description:'different strings, same meaning -> SAME_AS review'},
    pass_violations:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','company','rule'], properties:{ driver_name:{type:'string'}, company:{type:'string'}, rule:{type:'string'} }}},
    convergence_summary:{type:'string'},
  } }

const RULES = `NAMING RULES (authority = .claude/plans/Drivers/DriverOntology.md — READ it; summary for speed):
- driver_name = the reusable CAUSE as a specific lower_snake_case noun. As specific as the evidence allows; NEVER a broad/category word alone (no bare demand/macro/sector/sentiment).
- Order: concrete thing or actor -> needed detail -> metric/mechanism. e.g. restaurant_traffic, same_store_sales, cmg_digital_sales, oil_price.
- EARNINGS convention: {metric}_surprise (reported vs consensus) or {metric}_guidance (forward outlook): eps_surprise, revenue_surprise, revenue_guidance, gross_margin_guidance. beat/miss/raised/lowered are NOT in the name.
- BANNED inside the name: state/verbs (beat, cut, declined), direction/impact (long/short, bullish), dates/quarters/years, numbers/magnitudes/units (bps, percent, usd), ANY company ticker or legal name (the company itself OR a peer), person names, source/provider labels, XBRL prefixes, metaphors/sentiment, bare category words, stopwords. (Products/brands/segments ARE allowed even if one company has them.)
- Keep standard phrases whole: gross_margin, free_cash_flow, same_store_sales, net_interest_margin.
- Vague text -> SKIP (don't invent).
- fiscal.ai KPI labels are RAW SUGGESTIONS ONLY: rewrite each into a standard driver_name (e.g. "Comparable Store Sales Growth" -> same_store_sales); never use the raw label.`

phase('Probe')
const probe = await agent(`Repo root /home/faisal/EventMarketDB. Read-only DB probe (no writes).
Load the Neo4j tool via ToolSearch ("select:mcp__neo4j-cypher__read_neo4j_cypher"; also get_neo4j_schema if useful).
GOAL: produce TWO reusable queries the per-company agents will run:
1) events_cypher (param $ticker): for that company, return its 8-K / 10-K / 10-Q / Transcript events — **EXCLUDE News** — whose ABSOLUTE daily_stock return is >= 2.0. (Returns are PERCENT POINTS, not decimals, stored on the event→Company edge: (Transcript)-[:INFLUENCES]->(Company) and (Report)-[:PRIMARY_FILER]->(Company); Report.formType gives '8-K'/'10-K'/'10-Q'; r.daily_stock = raw daily return.) Return: source_type, date, a text snippet (<=600 chars), and r.daily_stock. **NO limit — return ALL qualifying events.** Order by abs(r.daily_stock) desc. TEST on $ticker='SBUX' and report the row count + 2 sample rows. (News is intentionally excluded — news/macro drivers accrete LIVE in production, not in the seed.)
2) fiscalai_query: the exact command (python3 + sqlite3 on data/fiscal_ai_segments/fiscal_segments.sqlite) to list a ticker's operational KPI metric_names (section='Key Performance Indicators'). Test on SBUX.
Return the working queries verbatim so they can be reused. If returns can't be filtered cleanly, report exactly what return fields DO exist so we can adapt.`, {schema:PROBE_SCHEMA, label:'probe', phase:'Probe'})

phase('Menus')
const TICKERS = ['SBUX','MCD','CMG','YUM','DRI','TXRH','SHAK','WING','CAKE','EAT','PZZA','CBRL','BLMN','QSR']
const pj = JSON.stringify({events_cypher:probe?.events_cypher||'', fiscalai_query:probe?.fiscalai_query||''})
const menus = (await parallel(TICKERS.map(t => () => agent(`Repo root /home/faisal/EventMarketDB. You build the candidate driver-name menu for ONE company only: ${t}. You are BLIND — you see only ${t}, no other company's names, no shared catalog. Coin names from scratch per the rules.

${RULES}

DATA (run these; load Neo4j tool via ToolSearch "select:mcp__neo4j-cypher__read_neo4j_cypher"; use Bash for sqlite):
- Events: run this Cypher with $ticker='${t}':  ${'```'}${(probe&&probe.events_cypher)||''}${'```'}
- fiscal.ai KPIs: ${'```'}${(probe&&probe.fiscalai_query)||''}${'```'} (replace the ticker with ${t})
PROBE CONTEXT: ${pj}

TASK: From (a) the company's fiscal.ai KPI names [rewrite each to a standard driver_name] and (b) the text of its >2%-move events, coin a list of SPECIFIC candidate driver_names per the rules. You are NOT judging whether each was the true driver — just plausible, source-grounded candidate names. Skip vague items. For each candidate return: driver_name, a short evidence_quote (the words that justify it), source_type, date, and an XBRL concept/member only if obvious (else "null"). Dedup within ${t} only. Return the MENU_SCHEMA object.`, {schema:MENU_SCHEMA, label:`menu:${t}`, phase:'Menus'}))) ).filter(Boolean)

phase('Converge')
const menusJson = JSON.stringify(menus)
const conv = await agent(`Repo root /home/faisal/EventMarketDB. You receive ${menus.length} per-company driver-name menus (Restaurants industry), each coined BLIND (no company saw another's names). 

MENUS (json): ${menusJson.slice(0, 60000)}

DO:
1) Write the full data to /home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_seed.json (a JSON with: per-company menus, plus the analysis below). Use the Write tool.
2) SHARED NAMES: list every driver_name independently coined by >=2 different companies (this is the blind-convergence signal — e.g. did multiple chains all land on same_store_sales / restaurant_traffic?). Include the company list per name.
3) EXACT-MEANING DUPLICATES: different strings that mean the SAME thing (e.g. guest_count vs customer_transactions, same_store_sales vs comparable_sales) -> for SAME_AS review. Only EXACT same meaning, not merely related.
4) PASS-CHECK VIOLATIONS: any driver_name that breaks a rule — broad/category word, a company ticker/legal name (own or peer), or state/impact/date/magnitude baked in.
5) Stats: total candidates, total distinct names, and a 2-3 sentence convergence_summary answering: did blind producers converge (lots of shared names) or fragment (mostly singletons)? 
Return the CONV_SCHEMA object (compact — do NOT echo all raw candidates back, they're in the file).`, {schema:CONV_SCHEMA, label:'converge', phase:'Converge'})

return { probe:{return_field:probe?.return_field, sample_count:probe?.sample_count, notes:probe?.notes}, menu_counts: menus.map(m=>({t:m.ticker, n:m.candidate_count, skipped:m.skipped_count})), converge: conv }
