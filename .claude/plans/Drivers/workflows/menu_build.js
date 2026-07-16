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
      required:['driver_name','evidence_quote','source_type','source_id','date'],
      properties:{ driver_name:{type:'string'}, evidence_quote:{type:'string', description:'actual words from the source content (or the raw KPI label) that justify it'}, source_type:{type:'string', description:'8-K / 10-K / 10-Q / transcript / fiscal.ai-kpi'}, source_id:{type:'string', description:'the events[].source_id of the event you quoted; for a KPI use "fiscal_ai:<ticker>:<metric>"'}, date:{type:'string', description:'event date YYYY-MM-DD; "" for a KPI'} }}},
    skipped_count:{type:'integer'}, notes:{type:'array', items:{type:'string'}} } }

const CONV_SCHEMA = { type:'object', additionalProperties:false,
  required:['ok','seed_sha256','total_candidates','total_distinct_drivers','notes'],
  properties:{ ok:{type:'boolean'}, seed_sha256:{type:'string'}, total_candidates:{type:'integer'}, total_distinct_drivers:{type:'integer'}, notes:{type:'string'} } }

const REC_SCHEMA = { type:'object', additionalProperties:false, required:['files_written'],
  properties:{ files_written:{type:'array', items:{type:'string'}}, git_commit:{type:'string'} } }

const RULES = `NAMING RULES — authority = FINAL_DESIGN.md §3 (NAME-01…19), inlined verbatim below from the archived 02_DriverCatalog.md, synced to current law at NAME-17 — OD-21 2026-07-16 (readers cannot fetch docs, PIPE-16). Coin names per these rules exactly.

## Naming rules

### A. Core naming rules

#### NAME-01 — A driver name is the cause only  \`[LOCKED]\`
- **Rule:** The driver name is the reusable causal noun the evidence is about. What happened (the state), the direction, the size, the date, the company, the period, the units, and the raw quote all live in OTHER fields — never the name.

#### NAME-02 — One name per driver; no aliases list  \`[LOCKED]\`
- **Rule:** A driver stores exactly one name. Spelling, plural, acronym, and word-order variants of the same cause are the SAME canonical form — reuse it, never coin a duplicate. There is no "aliases" list on the driver. A true duplicate found later is joined to its canonical by a reversible "same-as" link, and each node keeps its own evidence.

#### NAME-03 — Open vocabulary  \`[LOCKED]\`
- **Rule:** Names use an open vocabulary. Every important noun in a name must come from the source material or an existing catalog driver — never a fixed, closed word-list.

#### NAME-04 — As specific as the evidence allows  \`[LOCKED]\`
- **Rule:** Name the cause as specific as the evidence allows. Never coin a broad or category name — breadth is not chosen; it emerges only when the same exact name is reused across events or companies.

#### NAME-05 — Name format  \`[LOCKED]\`
- **Rule:** A driver name has only lowercase ASCII letters, digits, and underscores; starts with a letter; never ends with an underscore; has no double underscores; and is at least 2 characters.

#### NAME-06 — Word order  \`[LOCKED]\`
- **Rule:** When coining a multi-part name, order the parts: concrete thing or actor → needed detail → metric or mechanism. ("Thing or actor" = a commodity, customer group, or policy body like the Fed / OPEC.) Brand/segment/place parts are sliced off first (NAME-10), so they don't appear here. Examples: \`hyperscaler_capex\`, \`restaurant_traffic\`, \`oil_price\`, \`fed_rate\`.
- **Note (singular-by-default — owner 2026-07-11):** SINGULAR BY DEFAULT — coin the singular form of a count noun (\`store_closure\` not \`store_closures\`, \`tariff\` not \`tariffs\`): the name is the cause CLASS; how many, how big, and how often live in the fact's fields, never the name. Keep the plural ONLY when (a) the plural is the standard financial/business term for that concept — the form it is normally reported under (\`earnings\`, \`bookings\`, \`sales\`, \`savings\`, \`futures\`, \`receivables\`) — or (b) the singular would name a DIFFERENT concept (\`product_returns\` — a "return" is an investment concept). The exception list is illustrative, never exhaustive — the two-part test decides (NAME-19). Locked whole phrases (NAME-08) are never singularized (\`same_store_sales\`).

#### NAME-07 — Familiar names win  \`[LOCKED]\`
- **Rule:** Use the familiar form: \`fed_rate\`, \`yield_curve\`, \`oil_price\`, \`tariff_policy\`, \`fda_approval\`. **Precedence (owner 2026-07-11):** the familiar short form applies only when the source does not itself distinguish a specific named sibling instrument or benchmark within that family; when the source names the sibling (SOFR vs the fed-funds family → coin \`sofr_rate\`), NAME-04 specificity wins. Familiarity is a fallback for undifferentiated mentions, never a license to flatten stated specificity. (Commodity benchmarks: already NAME-12(c).)

#### NAME-08 — Keep standard financial phrases whole  \`[LOCKED]\`
- **Rule:** \`gross_margin\`, \`free_cash_flow\`, \`net_interest_margin\`, \`same_store_sales\` stay whole.
- **Note (signed-driver pin — OD-12, owner 2026-07-06 · 66 §0.R OD-12):** a loss/deficit is the NEGATIVE region of the standard signed metric, not a separate cause — coin \`net_income\` / \`operating_margin\` / \`eps\`, never a loss-magnitude driver (\`net_loss\` / \`loss_margin\` / \`loss_per_share\`). The loss is stored as a negative value (09 §3), so two producers can't fork on \`loss_margin=+5\` vs \`operating_margin=−5\`. Consistent with NAME-15 (what-happened / size are not in the name).

#### NAME-09 — One cause per name (split multiples; short; a noun)  \`[LOCKED]\`
- **Rule:** A name carries exactly one cause. Two+ independent causes → a separate driver each, never bundled (\`asset_impairment_and_lease_termination\` → split). Keep names short; if it takes many words to be specific, it's probably two drivers. Reads as a noun.

### B. Name vs slice

#### NAME-10 — Own measured company parts → the slice, not the name  \`[LOCKED]\`
- **Rule:** Segment, geography, product, customer, channel, and entity_ownership are slices ONLY when the quote clearly frames them as the reporting company's own measured part. Stored slice kinds are FS-06's six kinds; "brand" is a source word, not a stored kind. Capture every such qualifier with FS-02 multi-slice. Examples: Apple reports iPhone sales → \`sales\` + \`slice=product:iphone\`; Nike revenue in China → \`revenue\` + \`slice=geography:china\`; supplier orders from Walmart → \`orders\` + \`slice=customer:walmart\`.

#### NAME-11 — External or unclear objects stay in the name  \`[LOCKED]\`
- **Rule:** Ask in order, stop at the first hit:
  - **0.** Strip freestanding direction/impact words first (rose, headwind, generic pressure…) — never in the name. Exception: a word like \`pressure\` may stay only when it is part of a specific reusable market force (\`glp1_pressure\`), not a generic effect word.
  - **1.** Is the qualifier clearly the reporting company's own measured part (segment/geography/product/customer/channel/entity_ownership)? → **SLICE** it under NAME-10.
  - **2.** Is the qualifier an external object, actor, platform, policy, event, or product causing the outcome? → keep it in the **NAME** (\`iphone_demand\`, \`aws_outage\`, \`china_lockdown\`, \`freight_cost_pressure\`, \`tiktok_ban\`).
  - **3.** Is the role unclear, or would stripping the qualifier leave only a vague fragment (\`demand\`, \`ban\`, \`pressure\`, \`outage\`)? → keep it in the **NAME**.
- **Customer pin:** \`customer:walmart\` is a slice only when the metric measures the reporting company's own business with Walmart (orders/revenue from Walmart). If Walmart's independent action is the cause, keep Walmart in the name (\`walmart_price_cuts\`).
- **Vendor pin:** Do not add a vendor slice kind here. A vendor/platform as an external cause stays in the name (\`aws_outage\`, \`aws_spending\`) unless a later owner rule creates a vendor slice.
- **Portion pin (OD-17):** a qualifier naming a PORTION of the measured quantity is never a slice — it stays in the name (see OD-17 below).

#### OD-17 — Portion qualifiers & non-population aggregates
- **Rule (core):** A qualifier naming which PORTION of the company's own measured quantity is counted — and that is not one of the six slice kinds, not a period window, and not a measurement version — stays in the NAME (\`current_rpo\`, \`fee_earning_aum\`, \`funded_backlog\`). Different portion = different driver, never SAME_AS the bare form. If unclear whether a word is a window or a portion, keep it in the name; never drop it.
- **(a) All-parts aggregates (population test):** a stated aggregate maps to FS-10's omitted slice ONLY when its population is the consolidated reporting entity ("total company", "consolidated", "group"). An aggregate crossing the ownership boundary or curating a subset is NEVER the omitted slice: network/system aggregates (\`systemwide_sales\`, \`gmv\`, \`total_payment_volume\`) are their own whole-phrase Drivers (NAME-08 posture); curated subsets ("core operations", ex-items, pro-forma combined) keep their qualifier — never mapped to the consolidated series.
- **(b) Residual buckets:** a company-stated residual ("Other", "Rest of World", "Corporate unallocated") is a LEGAL slice value of its stated kind (\`segment:other\`) — never a name token, never dropped. Residuals are company-specific and their composition may drift across periods: guards in 03 FS-07 note.
- **(c) Accounting constructs:** pure consolidation artifacts (eliminations, fair-value levels, reconciling items) are excluded as slice values AND as Driver names — never coin an eliminations Driver; drop-and-log (FS-20's log). An eliminations-driven mover is recorded as a fact on the AFFECTED reported metric (e.g. \`operating_income\`, lane state, quote carrying the eliminations mechanism) — evidence is never dropped.

### C. What's in / out of a name

#### NAME-12 — What's allowed IN the name  \`[LOCKED]\`
- **Rule:** In the name: (a) the cause; (b) per-X denominators (\`oil_price_per_barrel\`, \`dividend_per_share\`); (c) benchmark identity when a commodity has named, differently-priced benchmarks (\`brent_oil_price\` vs \`wti_oil_price\`); (d) terminal \`_guidance\` / \`_surprise\` suffixes under NAME-17. Nothing else.

#### NAME-13 — Per-X goes in the name (business AND physical)  \`[LOCKED]\`
- **Rule:** Transcribe whatever per-X the source states — business (\`per_share\`, \`per_square_foot\`) AND physical (\`per_barrel\`, \`per_tonne\`, \`per_hour\`), no judgment. Stated → oil at $80/barrel → \`oil_price_per_barrel\`; not stated → oil rose 8% → \`oil_price\`. Different per-X = a different driver (\`oil_price_per_barrel\` ≠ \`oil_price_per_tonne\`), never same-as. No per-X unit — the unit stays the base (usually \`usd\`/\`count\`).
- **Note:** Standard financial acronyms that already include the denominator keep their familiar name: \`eps\` is valid and does not need to become \`earnings_per_share\`.

#### NAME-14 — The version of a number is NOT in the name  \`[LOCKED]\`
- **Rule:** The version of a number (adjusted, diluted, basic, constant-currency, core, cash…) goes in the **measurement** slot INSIDE fact_scope — a sibling of the slice, NOT a 7th slice kind. \`adjusted eps\` → name=\`eps\`, measurement=\`{adjusted}\`. Store the specific stated word (case/whitespace/punctuation normalized); default empty (never assume gaap); gaap/non_gaap is a read-time view, never stored. A measurement word re-expresses the SAME quantity through a different lens; a word that changes WHICH portion is counted is never a measurement token — it belongs in the name (OD-17).

#### NAME-15 — What's kept OUT of the name  \`[LOCKED]\`
- **Rule:** Out of the name → into other fields: direction/impact (→ verdict), what-happened (→ driver_state), date/period (→ DriverPeriod), company (→ linked company), units & size (→ number fields), raw quote (→ quote). The name is only the cause.

#### NAME-16 — The full "banned inside a name" list  \`[LOCKED]\`
- **Rule:** None appear in a name (rejected even if the source uses them):
  1. state words → driver_state *[OK: stable nouns/metric phrases ending -ing/-ed: \`pricing\`, \`bookings\`, \`operating_margin\`]*
  2. direction/polarity → verdict
  3. motion/change nouns → driver_state
  4. the reporting company's own name/brand (redundant — the fact already links to the company), and any incidental co-mentioned entity adding no causal specificity (an analyst, executive, law firm, or counterparty named in passing) *[OK: an external company, platform, institution, or person whose own independent action or state IS the stated cause (NAME-11 test 2): \`fed_rate\`, \`opec_supply\`, \`fda_approval\`, \`walmart_price_cuts\`, \`aws_outage\`, \`tiktok_ban\`]*
  5. period tokens
  6. numbers/sizes/bare units (\`bps\`, \`percent\`, \`usd\`)
  7. source-type labels
  8. provider/vendor labels as metadata *[OK when the vendor/platform is the external cause under NAME-11: \`aws_outage\`, \`aws_spending\`]*
  9. XBRL prefixes
  10. metaphors/sentiment/effect-on-stock words *[OK only when the word is part of a specific reusable market force, e.g. \`glp1_pressure\`; generic "pressure" stays banned]*
  11. a bare category word alone (\`macro\`, \`sector\`, \`demand\`, \`sentiment\`)
  12. vague descriptors too broad to name a cause
  13. glue words (\`the\`, \`of\`, \`in\`, \`and\`, \`to\`, \`for\`)

### D. Family, gate & meta

#### NAME-17 — Metric-family suffix stays in the name  \`[LOCKED]\`
- **Rule:** Name metric + mechanism: \`{metric}_surprise\` (a delivered actual OR a promised guide compared with a cross-party expectation; ONE surprise driver holds all three surprise types: actual_vs_consensus, actual_vs_guidance, guidance_vs_consensus — OD-21, synced 2026-07-16), \`{metric}_guidance\` (forward outlook) — \`eps_surprise\`, \`revenue_guidance\`. Suffix stays in the name AND fact_type is a separate permanent field. The base \`{metric}\` is a separate driver linked by \`BASE_METRIC\` (never same-as). Beat/miss/raised → driver_state, never the name.

#### NAME-18 — The new-driver gate  \`[LOCKED]\`
- **Rule:** Propose a new driver only when ALL hold: (a) no existing name means the same cause; (b) it satisfies every naming rule; (c) each important noun comes from the source or an existing driver; (d) it's attached to ≥1 causal claim with real evidence; (e) it's a reusable CLASS, not bound to a single instance (\`government_shutdown\` OK even once; \`q1_2026_shutdown_effect\` rejected); (f) if the rules leave >1 candidate name → reject as ambiguous; (g) if the evidence is vague or names no reusable cause → skip, never invent.

#### NAME-19 — Rule changes use one general principle, never sector examples  \`[LOCKED]\`
- **Rule:** Any change to the naming rules must be a single general principle, not sector-specific examples. Examples overfit — named domains pass while unnamed ones break on held-out data.

fiscal.ai KPI labels are RAW SUGGESTIONS ONLY: rewrite each into a standard driver_name per the rules above; never use the raw label as the NAME.`

// Harness quirk: args may arrive JSON-encoded as a string — parse defensively.
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
// Model slots (args-overridable; owner 2026-07-10): reader = PLACEHOLDER — WP-FC-RUN MUST pass EXP-2's
// adopted (model + effort); clerks/mechanical relays = sonnet, engine-default effort. No haiku/opus defaults.
const _M = (A.models && typeof A.models === 'object') ? A.models : {}
const MODELS = { reader: _M.reader || null, reader_effort: _M.reader_effort || null, clerk: _M.clerk || 'sonnet' }
const MODEL_IDS = { sonnet: 'claude-sonnet-5', opus: 'claude-opus-4-8', fable: 'claude-fable-5', haiku: 'claude-haiku-4-5-20251001' }
const rid = a => (a == null ? null : (MODEL_IDS[a] || a))   // resolve alias -> exact model ID at run time; an explicit ID passes through
const MODELS_PROV = { reader: { alias: MODELS.reader, id: rid(MODELS.reader), effort: MODELS.reader_effort }, clerk: { alias: MODELS.clerk, id: rid(MODELS.clerk) } }
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
Return scope_name, slug, tickers, n_tickers from (1) and utc_stamp from (2). If (1) exits NON-ZERO, report the exact error and return an empty tickers array (do NOT invent tickers).`, {schema:SCOPE_SCHEMA, model:MODELS.clerk, label:'resolve', phase:'Resolve'})
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
Then report the per-ticker summary lines, confirm sources_manifest.json AND scope_resolved.json were written, and confirm every ticker wrote a file with empty=0. If any ticker errored or has empty>5, say so explicitly.`, {model:MODELS.clerk, label:'fetch-sources', phase:'Fetch'})

phase('Chunk')
const chunk = await agent(`Run BOTH commands with Bash, in order (deterministic chunker — splits the uncapped sources into bounded blind-bot inputs at natural boundaries; never drops a byte):
1) ${PY} ${DIR}/workflows/chunk_company_sources.py ${RUN_DIR}
   (writes ${RUN_DIR}/chunks/<TICKER>__chunk_NNN.json + chunks_manifest.json; prints a one-line JSON summary with chunk_ids)
2) ${PY} ${DIR}/workflows/chunk_company_sources.py ${RUN_DIR} --verify
   (the §8.7c byte-exact conservation proof; prints "VERIFY OK" or fails)
Return ok=true + chunk_ids = the exact list from command 1's summary JSON + notes = command 2's output line. If EITHER exits NON-ZERO: ok=false, chunk_ids=[], notes = the exact error output.`, {schema:CHUNK_SCHEMA, model:MODELS.clerk, label:'chunk', phase:'Chunk'})
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
Return the fields of the FINAL printed JSON line VERBATIM. If it exits NON-ZERO: all=-1, done=0, todo=[], done_counts={}, tickers=[], notes = the exact error output.`, {schema:PLAN_SCHEMA, model:MODELS.clerk, label:'resume-plan', phase:'Chunk'})
if (!plan || plan.all < 0) throw new Error(`A2 resume plan failed for ${RUN_ID}: ${plan && plan.notes}`)
log(`A2 RESUME ${RUN_ID}: ${plan.done}/${plan.all} chunk menus already valid on disk — fanning out only ${plan.todo.length} reader(s)`)
}
const TODO_CHUNKS = RESUME ? plan.todo : FRESH_CHUNK_IDS
const N_CHUNKS = RESUME ? plan.all : FRESH_CHUNK_IDS.length

phase('Menus')
// Blind reader model/effort are NOT defaulted (owner 2026-07-10): WP-FC-RUN passes EXP-2's adopted reader.
if (TODO_CHUNKS.length > 0 && !MODELS.reader) throw new Error('menu_build: MODELS.reader not set — WP-FC-RUN must pass EXP-2 adopted reader (model + effort); no default.')
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
For each candidate return: driver_name, evidence_quote, source_type, source_id, date. EVIDENCE is EITHER (a) a real quote from an event's content → source_id = that event's source_id, source_type + date = that event's; OR (b) a fiscal.ai KPI you rewrote → source_type = "fiscal.ai-kpi", source_id = "fiscal_ai:${t}:<metric>", date = "", evidence_quote = the raw KPI label.
Dedup within this chunk only. Set ticker="${t}" and chunk_id="${cid}".
FINAL STEP before returning: use the Write tool to save the EXACT JSON object you are about to return (same fields, same content, compact JSON) to ${RUN_DIR}/menus/${cid}.json — the deterministic seed builder reads that file; a count cross-check will fail the run if it diverges from your return. Then return the MENU_SCHEMA object.`, {schema:MENU_SCHEMA, model:MODELS.reader, effort:MODELS.reader_effort, label:`menu:${cid}`, phase:'Menus'}) }))).filter(Boolean)
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
Return ok=true + seed_sha256/total_distinct_drivers/total_candidates from the printed summary JSON, notes="". If it exits NON-ZERO: ok=false, counts=0, notes = the exact error output. Do NOT edit any files.`, {schema:CONV_SCHEMA, model:MODELS.clerk, label:'build-seed', phase:'Converge'})
if (!conv.ok) throw new Error(`build_seed.py failed: ${conv.notes}`)

phase('Record')
// A2: on resume the run dir's OWN sources define the ticker set (code-listed by the plan).
const REC_TICKERS = RESUME ? plan.tickers : TICKERS
const rec = await agent(`Write TWO files with the Write tool into ${RUN_DIR}:
1) scope.json — write this EXACT JSON: ${JSON.stringify({ industry:INDUSTRY, slug:SLUG, tickers:REC_TICKERS })}
2) manifest.json — FIRST run Bash \`git -C ${DIR} rev-parse HEAD\` to get the code commit sha, THEN write this JSON with <COMMIT> replaced by that sha:
{ "run_id":"${RUN_ID}", "industry":${JSON.stringify(INDUSTRY)}, "slug":"${SLUG}", "utc_stamp":"${scope.utc_stamp}", "n_tickers":${REC_TICKERS.length}, "tickers":${JSON.stringify(REC_TICKERS)}, "subset":${RESUME ? 'null' : JSON.stringify(SUBSET)}, "test_subset":${RESUME ? 'null' : (SUBSET ? 'true' : 'false')}, "resumed":${RESUME ? 'true' : 'false'}, "args":${JSON.stringify(RESUME ? { industry, resume_run_id: RESUME } : { industry })}, "git_commit":"<COMMIT>", "n_chunks":${N_CHUNKS}, "seed_sha256":"${conv.seed_sha256}", "seed_counts":{ "distinct_drivers":${conv.total_distinct_drivers}, "total_candidates":${conv.total_candidates} }, "models":${JSON.stringify(MODELS_PROV)} }
Return files_written (the two paths) + git_commit (the sha you used).`, {schema:REC_SCHEMA, model:MODELS.clerk, label:'record', phase:'Record'})

return { run_id:RUN_ID, run_dir:RUN_DIR, industry:INDUSTRY, slug:SLUG, n_tickers:REC_TICKERS.length, subset:RESUME ? null : SUBSET, resumed:!!RESUME, n_chunks:N_CHUNKS, readers_run:TODO_CHUNKS.length, distinct_drivers:conv.total_distinct_drivers, total_candidates:conv.total_candidates, seed_sha256:conv.seed_sha256, fetch_summary:(fetched||'').slice(0,800), record:rec }
