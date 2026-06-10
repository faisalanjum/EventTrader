export const meta = {
  name: 'driver-menu-build',
  description: 'Driver-catalog SEED build for ANY industry, into a self-contained run folder. Step 0: resolve_driver_scope.py turns args.industry into tickers + a run_id (default Restaurants). Step A: fetch_company_sources.py --run-dir pulls ALL non-news sources WITH real text + each event source_id into runs/<run_id>/sources/ and writes sources_manifest.json (sha256 per file). Step B: 1 blind subagent per company coins candidate driver_names (each with source_id). Step C: deterministic JS grouping writes runs/<run_id>/seed.json. Step D: write scope.json + manifest.json (args, git commit, counts). Read-only Neo4j. Pass args = { industry: "<name>" }; returns run_id (pass it to reconcile.js).',
  phases: [
    { title: 'Resolve',  detail: 'resolve_driver_scope.py + date -u → tickers + run_id (default Restaurants)' },
    { title: 'Fetch',    detail: 'fetch_company_sources.py --run-dir → FULL structured sources (uncapped) + sources_manifest.json' },
    { title: 'Chunk',    detail: 'chunk_company_sources.py → bounded chunks/ at natural boundaries + byte-exact conservation proof (§8.7c)' },
    { title: 'Menus',    detail: 'one blind subagent per CHUNK file coins names + source_id from real content' },
    { title: 'Converge', detail: 'build_seed.py groups deterministically (code) → runs/<run_id>/seed.json + sha' },
    { title: 'Record',   detail: 'write scope.json + manifest.json (args · git commit · tickers · chunks · seed sha + counts)' },
  ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'

const SCOPE_SCHEMA = { type:'object', additionalProperties:true, required:['slug','tickers','utc_stamp'], properties:{
  scope_name:{type:'string'}, slug:{type:'string'}, tickers:{type:'array', items:{type:'string'}}, n_tickers:{type:'integer'},
  utc_stamp:{type:'string', description:'output of `date -u +%Y-%m-%d_%H%M%S` (the run timestamp)'} } }

const CHUNK_SCHEMA = { type:'object', additionalProperties:false, required:['ok','chunk_ids','notes'],
  properties:{ ok:{type:'boolean'}, chunk_ids:{type:'array', items:{type:'string'}}, notes:{type:'string'} } }

const MENU_SCHEMA = { type:'object', additionalProperties:false,
  required:['ticker','chunk_id','candidate_count','candidates','skipped_count','notes'],
  properties:{
    ticker:{type:'string'}, chunk_id:{type:'string'}, candidate_count:{type:'integer'},
    candidates:{type:'array', items:{type:'object', additionalProperties:false,
      required:['driver_name','evidence_quote','source_type','source_id','date','xbrl_or_null'],
      properties:{ driver_name:{type:'string'}, evidence_quote:{type:'string', description:'actual words from the source content (or the raw KPI label) that justify it'}, source_type:{type:'string', description:'8-K / 10-K / 10-Q / transcript / fiscal.ai-kpi'}, source_id:{type:'string', description:'the events[].source_id of the event you quoted; for a KPI use "fiscal_ai:<ticker>:<metric>"'}, date:{type:'string', description:'event date YYYY-MM-DD; "" for a KPI'}, xbrl_or_null:{type:'string'} }}},
    skipped_count:{type:'integer'}, notes:{type:'array', items:{type:'string'}} } }

const CONV_SCHEMA = { type:'object', additionalProperties:false,
  required:['ok','seed_sha256','total_candidates','total_distinct_drivers','notes'],
  properties:{ ok:{type:'boolean'}, seed_sha256:{type:'string'}, total_candidates:{type:'integer'}, total_distinct_drivers:{type:'integer'}, notes:{type:'string'} } }

const REC_SCHEMA = { type:'object', additionalProperties:false, required:['files_written'],
  properties:{ files_written:{type:'array', items:{type:'string'}}, git_commit:{type:'string'} } }

const RULES = `NAMING RULES (authority = ${DIR}/DriverOntology.md — READ it; summary for speed):
- driver_name = the reusable CAUSE as a specific lower_snake_case noun. As specific as the evidence allows; NEVER a broad/category word alone (no bare demand/macro/sector/sentiment).
- Order: concrete thing or actor -> needed detail -> metric/mechanism. e.g. restaurant_traffic, same_store_sales, oil_price.
- EARNINGS convention: {metric}_surprise (reported vs consensus) or {metric}_guidance (forward outlook): eps_surprise, revenue_surprise, revenue_guidance, gross_margin_guidance. beat/miss/raised/lowered are NOT in the name.
- BANNED inside the name: state/verbs (beat, cut, declined, transition, opening, growth), direction/impact (long/short), dates/quarters/years, numbers/magnitudes/units (bps, percent, usd), ANY company ticker or legal name (own OR peer), person names, source/provider labels, XBRL prefixes, metaphors/sentiment, bare category words, stopwords. (Products/brands/segments ARE allowed: a brand metric like taco_bell_same_store_sales is its OWN driver, separate from same_store_sales.)
- Keep standard phrases whole: gross_margin, free_cash_flow, same_store_sales, net_interest_margin.
- Vague text -> SKIP (don't invent).
- fiscal.ai KPI labels are RAW SUGGESTIONS ONLY: rewrite each into a standard driver_name; never use the raw label as the NAME.`

// Harness quirk: args may arrive JSON-encoded as a string — parse defensively.
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
const industry = A.industry || 'Restaurants'
// TEST-ONLY subset override (recorded in manifest): args.tickers = explicit ticker list ⊆ the industry.
const SUBSET = (Array.isArray(A.tickers) && A.tickers.length) ? A.tickers.map(t => String(t).trim().toUpperCase()) : null

phase('Resolve')
const scope = await agent(`Run BOTH commands with Bash and return the combined JSON (schema fields):
1) ${PY} ${DIR}/workflows/resolve_driver_scope.py --industry ${JSON.stringify(industry)}   (prints { scope_name, slug, tickers, n_tickers })
2) date -u +%Y-%m-%d_%H%M%S   (the UTC run timestamp)
Return scope_name, slug, tickers, n_tickers from (1) and utc_stamp from (2). If (1) exits NON-ZERO, report the exact error and return an empty tickers array (do NOT invent tickers).`, {schema:SCOPE_SCHEMA, label:'resolve', phase:'Resolve'})
const SLUG = scope.slug, INDUSTRY = scope.scope_name || industry
let TICKERS = scope.tickers || []
if (SUBSET) {
  const bad = SUBSET.filter(t => !TICKERS.includes(t))
  if (bad.length) throw new Error(`subset tickers not in industry "${industry}": ${bad.join(', ')}`)
  TICKERS = SUBSET
}
if (!TICKERS.length) throw new Error(`resolve_driver_scope.py returned 0 tickers for industry "${industry}" — stopping (the fetcher hard-errors on zero tickers; this throw is the workflow-side guard).`)
const RUN_ID = `${scope.utc_stamp}_${SLUG}`
const RUN_DIR = `${DIR}/runs/${RUN_ID}`

phase('Fetch')
const fetched = await agent(`Run this EXACT command with Bash (pulls all non-news sources WITH real text for the ${TICKERS.length} ${INDUSTRY} companies into the run dir, and writes sources_manifest.json with a sha256 per file):
${PY} ${DIR}/workflows/fetch_company_sources.py ${TICKERS.join(' ')} --run-dir ${RUN_DIR}
Then report the per-ticker summary lines, confirm sources_manifest.json was written, and confirm every ticker wrote a file with empty=0. If any ticker errored or has empty>5, say so explicitly.`, {label:'fetch-sources', phase:'Fetch'})

phase('Chunk')
const chunk = await agent(`Run BOTH commands with Bash, in order (deterministic chunker — splits the uncapped sources into bounded blind-bot inputs at natural boundaries; never drops a byte):
1) ${PY} ${DIR}/workflows/chunk_company_sources.py ${RUN_DIR}
   (writes ${RUN_DIR}/chunks/<TICKER>__chunk_NNN.json + chunks_manifest.json; prints a one-line JSON summary with chunk_ids)
2) ${PY} ${DIR}/workflows/chunk_company_sources.py ${RUN_DIR} --verify
   (the §8.7c byte-exact conservation proof; prints "VERIFY OK" or fails)
Return ok=true + chunk_ids = the exact list from command 1's summary JSON + notes = command 2's output line. If EITHER exits NON-ZERO: ok=false, chunk_ids=[], notes = the exact error output.`, {schema:CHUNK_SCHEMA, label:'chunk', phase:'Chunk'})
if (!chunk.ok || !chunk.chunk_ids.length) throw new Error(`chunk_company_sources.py failed: ${chunk.notes}`)

phase('Menus')
const menus = (await parallel(chunk.chunk_ids.map(cid => { const t = cid.split('__')[0]; return () => agent(`Repo root /home/faisal/EventMarketDB. You build the candidate driver-name menu for ONE CHUNK of ONE company: ${cid} (ticker ${t}). You are BLIND — you see only this chunk, no other company's names, no shared catalog.

${RULES}

LOAD THIS CHUNK'S REAL SOURCE TEXT: run Bash \`cat ${RUN_DIR}/chunks/${cid}.json\` (use cat or python via Bash; do NOT use the Read tool, it truncates). The JSON has:
- fiscal_kpis: [raw KPI names] (present only on chunk_001) → rewrite each into a standard driver_name.
- events: [{source_id, source_type, date, part_index, part_count, content}] → content is REAL document text (MD&A, Risk Factors, EX-99.1 press releases, prepared remarks, Q&A). If part_count > 1 you are seeing ONE PART of a larger document — coin names only from what you can see; other parts are handled by other bots and re-union later. source_id = the stable id of the event (NOT the part).

TASK: REVIEW EVERY event in the list IN ORDER before finalizing (do not skim or stop early; later events count too), and from the fiscal KPIs plus any event text with source-grounded evidence, coin SPECIFIC candidate driver_names per the rules. Not judging the true driver — just plausible, source-grounded candidate names from real material. MINE THE PROSE for narrative drivers too (input/commodity costs, tariffs, labor/wages, traffic vs pricing, demand, FX, specific products/segments), not just headline metrics. Skip vague items.
For each candidate return: driver_name, evidence_quote, source_type, source_id, date, xbrl_or_null ("null" if none obvious). EVIDENCE is EITHER (a) a real quote from an event's content → source_id = that event's source_id, source_type + date = that event's; OR (b) a fiscal.ai KPI you rewrote → source_type = "fiscal.ai-kpi", source_id = "fiscal_ai:${t}:<metric>", date = "", evidence_quote = the raw KPI label.
Dedup within this chunk only. Set ticker="${t}" and chunk_id="${cid}".
FINAL STEP before returning: use the Write tool to save the EXACT JSON object you are about to return (same fields, same content, compact JSON) to ${RUN_DIR}/menus/${cid}.json — the deterministic seed builder reads that file; a count cross-check will fail the run if it diverges from your return. Then return the MENU_SCHEMA object.`, {schema:MENU_SCHEMA, label:`menu:${cid}`, phase:'Menus'}) }))).filter(Boolean)
// §8.7a HARD-FAIL: every chunk in the manifest must come back as a processed menu (closes the .filter(Boolean) gap)
const gotIds = new Set(menus.map(m => m.chunk_id))
const missing = chunk.chunk_ids.filter(c => !gotIds.has(c))
if (missing.length) throw new Error(`chunk(s) NOT processed: ${missing.join(', ')} — fail-close, not proceeding with a partial seed (§8.7a).`)

phase('Converge')
// Deterministic grouping + seed WRITE = CODE (E2 + §11.14 via build_seed.py — pytest-covered; the AI never transports the seed).
const expectCounts = {}
for (const m of menus) expectCounts[m.ticker] = (expectCounts[m.ticker] || 0) + (m.candidates || []).filter(c => (c.driver_name || '').trim()).length
const conv = await agent(`Run this EXACT command with Bash (deterministic code: reads ${RUN_DIR}/menus/*.json, groups by lower-cased driver_name, dedups evidence by the 5-tuple, writes ${RUN_DIR}/seed.json, prints a one-line JSON summary; the --expect cross-check HARD-FAILS on any bot-file divergence):
${PY} ${DIR}/workflows/build_seed.py ${RUN_DIR} --industry ${JSON.stringify(INDUSTRY)} --slug ${SLUG} --run-id ${RUN_ID} --expect '${JSON.stringify(expectCounts)}'
Return ok=true + seed_sha256/total_distinct_drivers/total_candidates from the printed summary JSON, notes="". If it exits NON-ZERO: ok=false, counts=0, notes = the exact error output. Do NOT edit any files.`, {schema:CONV_SCHEMA, label:'build-seed', phase:'Converge'})
if (!conv.ok) throw new Error(`build_seed.py failed: ${conv.notes}`)

phase('Record')
const rec = await agent(`Write TWO files with the Write tool into ${RUN_DIR}:
1) scope.json — write this EXACT JSON: ${JSON.stringify({ industry:INDUSTRY, slug:SLUG, tickers:TICKERS })}
2) manifest.json — FIRST run Bash \`git -C ${DIR} rev-parse HEAD\` to get the code commit sha, THEN write this JSON with <COMMIT> replaced by that sha:
{ "run_id":"${RUN_ID}", "industry":${JSON.stringify(INDUSTRY)}, "slug":"${SLUG}", "utc_stamp":"${scope.utc_stamp}", "n_tickers":${TICKERS.length}, "tickers":${JSON.stringify(TICKERS)}, "subset":${JSON.stringify(SUBSET)}, "test_subset":${SUBSET ? 'true' : 'false'}, "args":${JSON.stringify({ industry })}, "git_commit":"<COMMIT>", "n_chunks":${chunk.chunk_ids.length}, "seed_sha256":"${conv.seed_sha256}", "seed_counts":{ "distinct_drivers":${conv.total_distinct_drivers}, "total_candidates":${conv.total_candidates} } }
Return files_written (the two paths) + git_commit (the sha you used).`, {schema:REC_SCHEMA, label:'record', phase:'Record'})

return { run_id:RUN_ID, run_dir:RUN_DIR, industry:INDUSTRY, slug:SLUG, n_tickers:TICKERS.length, subset:SUBSET, n_chunks:chunk.chunk_ids.length, distinct_drivers:conv.total_distinct_drivers, total_candidates:conv.total_candidates, seed_sha256:conv.seed_sha256, fetch_summary:(fetched||'').slice(0,800), record:rec }
