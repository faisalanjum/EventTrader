export const meta = {
  name: 'driver-menu-build',
  description: 'Driver-catalog SEED build for ANY industry, into a self-contained run folder. Step 0: resolve_driver_scope.py turns args.industry into tickers + a run_id (default Restaurants). Step A: fetch_company_sources.py --run-dir pulls ALL non-news sources WITH real text + each event source_id into runs/<run_id>/sources/ and writes sources_manifest.json (sha256 per file). Step B: 1 blind subagent per company coins candidate driver_names (each with source_id). Step C: deterministic JS grouping writes runs/<run_id>/seed.json. Step D: write scope.json + manifest.json (args, git commit, counts). Read-only Neo4j. Pass args = { industry: "<name>" }; returns run_id (pass it to reconcile.js). A2 resume: args = { industry, resume_run_id: "<RUN_ID>" } re-enters an existing run dir and fans out ONLY the chunks without a valid menu (fetch+chunk frozen).',
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
// A2 PER-CHUNK RESUME (CostCutting Class A2, provably zero-loss): pass args.resume_run_id to
// land in an EXISTING run dir whose fetch+chunk completed — resume_menus.py (pure code)
// re-proves the chunk stage byte-exact, validates existing menus fail-close, and fans out
// ONLY the missing/invalid chunks. Finished readers are never re-paid; readers that do run
// see byte-identical inputs. Fresh runs (no resume_run_id): all judge inputs byte-identical
// (the record clerk's manifest gains a "resumed":false provenance field only).
let RESUME = null
if (A.resume_run_id !== undefined && A.resume_run_id !== null) {
  RESUME = String(A.resume_run_id).trim()
  if (!RESUME) throw new Error('resume_run_id is empty/whitespace — pass the exact RUN_ID of the dead run')
  if (!/^[A-Za-z0-9._-]+$/.test(RESUME)) throw new Error(`resume_run_id "${RESUME}" has characters outside [A-Za-z0-9._-] — refusing (it becomes a path inside shell commands)`)
}
if (RESUME && SUBSET) throw new Error('resume_run_id cannot be combined with args.tickers — the existing run dir\'s sources define the ticker set')
// Stage-0 #8: the ticker list travels CODE-TO-CODE via this scope file (resolver writes it,
// fetch reads it, the chunker cross-checks it) — a relay-dropped ticker can no longer
// silently remove a company from the seed. Path is computed HERE from the trusted args.
const JSSLUG = industry.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '')
const SCOPE_FILE = `${DIR}/runs/_scope_${JSSLUG}.json`

phase('Resolve')
const scope = await agent(`Run these commands with Bash, in order, and return the combined JSON (schema fields):
0) BILLING GUARD (subscription-only hard condition): test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; }
   If it prints BILLING-GUARD FAIL, STOP: return an empty tickers array and put that exact line in scope_name.
1) ${PY} ${DIR}/workflows/resolve_driver_scope.py --industry ${JSON.stringify(industry)} --out ${SCOPE_FILE}   (prints { scope_name, slug, tickers, n_tickers } and writes the code-to-code scope file)
2) date -u +%Y-%m-%d_%H%M%S   (the UTC run timestamp)
Return scope_name, slug, tickers, n_tickers from (1) and utc_stamp from (2). If (1) exits NON-ZERO, report the exact error and return an empty tickers array (do NOT invent tickers).`, {schema:SCOPE_SCHEMA, model:'opus', label:'resolve', phase:'Resolve'})
const SLUG = scope.slug, INDUSTRY = scope.scope_name || industry
let TICKERS = scope.tickers || []
if (SUBSET) {
  const bad = SUBSET.filter(t => !TICKERS.includes(t))
  if (bad.length) throw new Error(`subset tickers not in industry "${industry}": ${bad.join(', ')}`)
  TICKERS = SUBSET
}
if (!TICKERS.length) throw new Error(`resolve_driver_scope.py returned 0 tickers for industry "${industry}" — stopping (the fetcher hard-errors on zero tickers; this throw is the workflow-side guard).`)
if (RESUME && !RESUME.endsWith(`_${SLUG}`)) throw new Error(`resume_run_id "${RESUME}" does not end with "_${SLUG}" — wrong industry?`)
const RUN_ID = RESUME || `${scope.utc_stamp}_${SLUG}`
const RUN_DIR = `${DIR}/runs/${RUN_ID}`

let fetched = '', plan = null, FRESH_CHUNK_IDS = null
const PLAN_SCHEMA = { type:'object', additionalProperties:false, required:['all','done','todo','done_counts','tickers','notes'], properties:{
  all:{type:'integer'}, done:{type:'integer'}, todo:{type:'array', items:{type:'string'}},
  done_counts:{type:'object', additionalProperties:{type:'integer'}, description:'ticker -> non-blank candidate count of the REUSED valid menus (code-computed integers)'},
  tickers:{type:'array', items:{type:'string'}}, notes:{type:'string'} } }
if (!RESUME) {
phase('Fetch')
fetched = await agent(`Run this EXACT command with Bash (pulls all non-news sources WITH real text for the ${TICKERS.length} ${INDUSTRY} companies into the run dir; the ticker list is read CODE-TO-CODE from the scope file — Stage-0 #8; writes sources_manifest.json + scope_resolved.json):
${PY} ${DIR}/workflows/fetch_company_sources.py --scope ${SCOPE_FILE}${SUBSET ? ` --subset ${SUBSET.join(',')}` : ''} --run-dir ${RUN_DIR}
Then report the per-ticker summary lines, confirm sources_manifest.json AND scope_resolved.json were written, and confirm every ticker wrote a file with empty=0. If any ticker errored or has empty>5, say so explicitly.`, {model:'opus', label:'fetch-sources', phase:'Fetch'})

phase('Chunk')
const chunk = await agent(`Run BOTH commands with Bash, in order (deterministic chunker — splits the uncapped sources into bounded blind-bot inputs at natural boundaries; never drops a byte):
1) ${PY} ${DIR}/workflows/chunk_company_sources.py ${RUN_DIR}
   (writes ${RUN_DIR}/chunks/<TICKER>__chunk_NNN.json + chunks_manifest.json; prints a one-line JSON summary with chunk_ids)
2) ${PY} ${DIR}/workflows/chunk_company_sources.py ${RUN_DIR} --verify
   (the §8.7c byte-exact conservation proof; prints "VERIFY OK" or fails)
Return ok=true + chunk_ids = the exact list from command 1's summary JSON + notes = command 2's output line. If EITHER exits NON-ZERO: ok=false, chunk_ids=[], notes = the exact error output.`, {schema:CHUNK_SCHEMA, model:'opus', label:'chunk', phase:'Chunk'})
if (!chunk.ok || !chunk.chunk_ids.length) throw new Error(`chunk_company_sources.py failed: ${chunk.notes}`)
FRESH_CHUNK_IDS = chunk.chunk_ids
} else {
phase('Chunk')
// A2 resume: fetch+chunk are FROZEN (re-fetching could change sources and mix generations);
// the deterministic planner re-proves the chunk stage and lists only the chunks still needing
// a reader. Relay drift is backstopped: an under-relayed todo leaves menu files missing ->
// build_seed's Stage-0 #2 chunk-coverage check hard-fails; count drift -> --expect hard-fails.
plan = await agent(`Run this EXACT command with Bash (deterministic A2 resume plan — re-proves the §8.7c byte-exact chunk stage, validates every existing menu fail-close, and lists ONLY the chunks still needing a reader):
${PY} ${DIR}/workflows/resume_menus.py ${RUN_DIR}
Return the fields of the FINAL printed JSON line VERBATIM. If it exits NON-ZERO: all=-1, done=0, todo=[], done_counts={}, tickers=[], notes = the exact error output.`, {schema:PLAN_SCHEMA, model:'opus', label:'resume-plan', phase:'Chunk'})
if (!plan || plan.all < 0) throw new Error(`A2 resume plan failed for ${RUN_ID}: ${plan && plan.notes}`)
log(`A2 RESUME ${RUN_ID}: ${plan.done}/${plan.all} chunk menus already valid on disk — fanning out only ${plan.todo.length} reader(s)`)
}
const TODO_CHUNKS = RESUME ? plan.todo : FRESH_CHUNK_IDS
const N_CHUNKS = RESUME ? plan.all : FRESH_CHUNK_IDS.length

phase('Menus')
// A1 WINDOW DISCIPLINE (CostCutting Class A1): large fan-outs should start on a FRESH 5-hour
// window and never share it with research/audit agents (a measured 47% window drain killed a
// real run). If this run dies mid-fan-out, NOTHING is lost: relaunch with
// args = { industry, resume_run_id: "<this RUN_ID>" } and only missing chunks re-run (A2).
log(`A1 WINDOW DISCIPLINE: fanning out ${TODO_CHUNKS.length} reader(s). Big bursts belong on a fresh 5-hour window, unshared with side work. If this dies: relaunch with args = { industry: ${JSON.stringify(industry)}, resume_run_id: "${RUN_ID}" } — only missing chunks re-run.`)
const menus = TODO_CHUNKS.length === 0 ? [] : (await parallel(TODO_CHUNKS.map(cid => { const t = cid.split('__')[0]; return () => agent(`Repo root /home/faisal/EventMarketDB. You build the candidate driver-name menu for ONE CHUNK of ONE company: ${cid} (ticker ${t}). You are BLIND — you see only this chunk, no other company's names, no shared catalog.

${RULES}

LOAD THIS CHUNK'S REAL SOURCE TEXT: run Bash \`cat ${RUN_DIR}/chunks/${cid}.json\` (use cat or python via Bash; do NOT use the Read tool, it truncates). The JSON has:
- fiscal_kpis: [raw KPI names] (present only on chunk_001) → rewrite each into a standard driver_name.
- events: [{source_id, source_type, date, part_index, part_count, content}] → content is REAL document text (MD&A, Risk Factors, EX-99.1 press releases, prepared remarks, Q&A). If part_count > 1 you are seeing ONE PART of a larger document — coin names only from what you can see; other parts are handled by other bots and re-union later. source_id = the stable id of the event (NOT the part).

TASK: REVIEW EVERY event in the list IN ORDER before finalizing (do not skim or stop early; later events count too), and from the fiscal KPIs plus any event text with source-grounded evidence, coin SPECIFIC candidate driver_names per the rules. Not judging the true driver — just plausible, source-grounded candidate names from real material. MINE THE PROSE for narrative drivers too (input/commodity costs, tariffs, labor/wages, traffic vs pricing, demand, FX, specific products/segments), not just headline metrics. Skip vague items.
For each candidate return: driver_name, evidence_quote, source_type, source_id, date, xbrl_or_null ("null" if none obvious). EVIDENCE is EITHER (a) a real quote from an event's content → source_id = that event's source_id, source_type + date = that event's; OR (b) a fiscal.ai KPI you rewrote → source_type = "fiscal.ai-kpi", source_id = "fiscal_ai:${t}:<metric>", date = "", evidence_quote = the raw KPI label.
Dedup within this chunk only. Set ticker="${t}" and chunk_id="${cid}".
FINAL STEP before returning: use the Write tool to save the EXACT JSON object you are about to return (same fields, same content, compact JSON) to ${RUN_DIR}/menus/${cid}.json — the deterministic seed builder reads that file; a count cross-check will fail the run if it diverges from your return. Then return the MENU_SCHEMA object.`, {schema:MENU_SCHEMA, model:'fable', label:`menu:${cid}`, phase:'Menus'}) }))).filter(Boolean)
// §8.7a HARD-FAIL: every fanned-out chunk must come back as a processed menu (closes the .filter(Boolean) gap)
const gotIds = new Set(menus.map(m => m.chunk_id))
const missing = TODO_CHUNKS.filter(c => !gotIds.has(c))
if (missing.length) throw new Error(`chunk(s) NOT processed: ${missing.join(', ')} — fail-close, not proceeding with a partial seed (§8.7a).`)

phase('Converge')
// Deterministic grouping + seed WRITE = CODE (E2 + §11.14 via build_seed.py — pytest-covered; the AI never transports the seed).
// A2: reused menus contribute their CODE-COMPUTED counts (resume plan); fresh readers their returned counts.
const expectCounts = RESUME ? { ...plan.done_counts } : {}
for (const m of menus) expectCounts[m.ticker] = (expectCounts[m.ticker] || 0) + (m.candidates || []).filter(c => (c.driver_name || '').trim()).length
const conv = await agent(`Run this EXACT command with Bash (deterministic code: reads ${RUN_DIR}/menus/*.json, groups by lower-cased driver_name, dedups evidence by the 5-tuple, writes ${RUN_DIR}/seed.json, prints a one-line JSON summary; the --expect cross-check HARD-FAILS on any bot-file divergence):
${PY} ${DIR}/workflows/build_seed.py ${RUN_DIR} --industry ${JSON.stringify(INDUSTRY)} --slug ${SLUG} --run-id ${RUN_ID} --expect '${JSON.stringify(expectCounts)}'
Return ok=true + seed_sha256/total_distinct_drivers/total_candidates from the printed summary JSON, notes="". If it exits NON-ZERO: ok=false, counts=0, notes = the exact error output. Do NOT edit any files.`, {schema:CONV_SCHEMA, model:'opus', label:'build-seed', phase:'Converge'})
if (!conv.ok) throw new Error(`build_seed.py failed: ${conv.notes}`)

phase('Record')
// A2: on resume the run dir's OWN sources define the ticker set (code-listed by the plan).
const REC_TICKERS = RESUME ? plan.tickers : TICKERS
const rec = await agent(`Write TWO files with the Write tool into ${RUN_DIR}:
1) scope.json — write this EXACT JSON: ${JSON.stringify({ industry:INDUSTRY, slug:SLUG, tickers:REC_TICKERS })}
2) manifest.json — FIRST run Bash \`git -C ${DIR} rev-parse HEAD\` to get the code commit sha, THEN write this JSON with <COMMIT> replaced by that sha:
{ "run_id":"${RUN_ID}", "industry":${JSON.stringify(INDUSTRY)}, "slug":"${SLUG}", "utc_stamp":"${scope.utc_stamp}", "n_tickers":${REC_TICKERS.length}, "tickers":${JSON.stringify(REC_TICKERS)}, "subset":${RESUME ? 'null' : JSON.stringify(SUBSET)}, "test_subset":${RESUME ? 'null' : (SUBSET ? 'true' : 'false')}, "resumed":${RESUME ? 'true' : 'false'}, "args":${JSON.stringify(RESUME ? { industry, resume_run_id: RESUME } : { industry })}, "git_commit":"<COMMIT>", "n_chunks":${N_CHUNKS}, "seed_sha256":"${conv.seed_sha256}", "seed_counts":{ "distinct_drivers":${conv.total_distinct_drivers}, "total_candidates":${conv.total_candidates} } }
Return files_written (the two paths) + git_commit (the sha you used).`, {schema:REC_SCHEMA, model:'opus', label:'record', phase:'Record'})

return { run_id:RUN_ID, run_dir:RUN_DIR, industry:INDUSTRY, slug:SLUG, n_tickers:REC_TICKERS.length, subset:RESUME ? null : SUBSET, resumed:!!RESUME, n_chunks:N_CHUNKS, readers_run:TODO_CHUNKS.length, distinct_drivers:conv.total_distinct_drivers, total_candidates:conv.total_candidates, seed_sha256:conv.seed_sha256, fetch_summary:(fetched||'').slice(0,800), record:rec }
