export const meta = {
  name: 'driver-reconcile',
  description: 'Step 2 reconcile over a per-industry seed catalog (args.run_id = the exact menu_build run; reads runs/<run_id>/seed.json, writes catalog.json + approved.json + decisions.json + validation.txt there): (Dedup) canonical + reversible SAME_AS for exact-same-meaning only = the REUSE arm; (Gate) independent admit/rewrite/skip per the 02 NAME rules; (Refute) skeptic breaks bad SAME_AS + meaning-changing rewrites; (Assemble) DETERMINISTIC CODE writes the catalog (assemble_catalog.py ports the 5-way precedence; HierarchicalCatalogPlan §11.19 — the writer cannot fabricate a fusion); (Validate) incl. the D1 fusion-approval check. Review-file only; no graph writes; no merges/deletes. Roll-up/rewrite targets must be COINED names.',
  phases: [ { title: 'Guard', detail: '§11.11 SEED_MAX measure; over caps → deterministic name-sorted review batches (cross-batch SAME_AS = accepted residual)' }, { title: 'Review', detail: 'dedup proposer + independent gate, in parallel (per batch)' }, { title: 'Refute', detail: 'independent skeptic breaks bad SAME_AS + meaning-changing rewrites; JS filters them out' }, { title: 'SameName', detail: 'leaf flag-triggered D5 (rare): review flagged mixed-meaning unions → SAME(Refute-confirmed)/DIFFERENT(split+mini-gate)/UNCLEAR(park)' }, { title: 'Assemble', detail: 'JS lists → decisions.json (+ same_name_review.json) → assemble_catalog.py (code writes catalog.json + approved.json, prints sha)' }, { title: 'Validate', detail: 'deterministic structure check incl. D1 fusion-approval (zero judgment); HARD-FAIL if broken' } ],
}

const DIR    = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY     = '/home/faisal/EventMarketDB/venv/bin/python3'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})   // harness may stringify args
// Model slots (args-overridable; owner 2026-07-10): strong judges = sonnet @ effort high; clerks/mechanical
// relays = sonnet, engine-default effort. No haiku/opus defaults.
const _M = (A.models && typeof A.models === 'object') ? A.models : {}
const MODELS = { dedup: _M.dedup || 'sonnet', gate: _M.gate || 'sonnet', refute: _M.refute || 'sonnet', d5: _M.d5 || 'sonnet', clerk: _M.clerk || 'sonnet' }
const MODEL_IDS = { sonnet: 'claude-sonnet-5', opus: 'claude-opus-4-8', fable: 'claude-fable-5', haiku: 'claude-haiku-4-5-20251001' }
const rid = a => (a == null ? null : (MODEL_IDS[a] || a))   // resolve alias -> exact model ID at run time; an explicit ID passes through
const MODELS_PROV = { effort_strong: 'high', dedup: { alias: MODELS.dedup, id: rid(MODELS.dedup) }, gate: { alias: MODELS.gate, id: rid(MODELS.gate) }, refute: { alias: MODELS.refute, id: rid(MODELS.refute) }, d5: { alias: MODELS.d5, id: rid(MODELS.d5) }, clerk: { alias: MODELS.clerk, id: rid(MODELS.clerk) } }
const RUN_ID = A.run_id || ''
if (!RUN_ID) throw new Error('reconcile.js requires args.run_id (e.g. "2026-06-07_143205_restaurants" from menu_build). Refusing to guess "latest".')
const RUN_DIR = `${DIR}/runs/${RUN_ID}`
const SEED = `${RUN_DIR}/seed.json`
const CAT  = `${RUN_DIR}/catalog.json`
const ONT  = `${DIR}/FinalDesign/02_DriverCatalog.md`
// PIPE-16: naming judges derive the rulebook from 02_DriverCatalog.md NAME-01…19, inlined verbatim (readers cannot fetch docs).
const RULEBOOK = `## Naming rules

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
- **Rule:** Name metric + mechanism: \`{metric}_surprise\` (actual vs expected), \`{metric}_guidance\` (forward outlook) — \`eps_surprise\`, \`revenue_guidance\`. Suffix stays in the name AND fact_type is a separate permanent field. The base \`{metric}\` is a separate driver linked by \`BASE_METRIC\` (never same-as). Beat/miss/raised → driver_state, never the name.

#### NAME-18 — The new-driver gate  \`[LOCKED]\`
- **Rule:** Propose a new driver only when ALL hold: (a) no existing name means the same cause; (b) it satisfies every naming rule; (c) each important noun comes from the source or an existing driver; (d) it's attached to ≥1 causal claim with real evidence; (e) it's a reusable CLASS, not bound to a single instance (\`government_shutdown\` OK even once; \`q1_2026_shutdown_effect\` rejected); (f) if the rules leave >1 candidate name → reject as ambiguous; (g) if the evidence is vague or names no reusable cause → skip, never invent.

#### NAME-19 — Rule changes use one general principle, never sector examples  \`[LOCKED]\`
- **Rule:** Any change to the naming rules must be a single general principle, not sector-specific examples. Examples overfit — named domains pass while unnamed ones break on held-out data.`
const MF02 = `MF-02 (cross-flavor guard): different flavors of one topic — base vs \`_guidance\` vs \`_surprise\` — are NEVER the same driver; never SAME_AS, never a cross-flavor rewrite target.`
const EXACT_MEANING_RULE = `For any proposed SAME_AS, reuse, or rewrite, first verify all three are true:
1. same object or metric
2. same scope
3. same mechanism

If any one is false or unclear, do not SAME_AS, reuse, or rewrite. Keep the names separate, admit separately, or skip.
A rewrite may only change wording. It must not change the underlying driver.`

const evidenceRule = (f) => `EVIDENCE: each driver_name is ONE catalog[] record in ${f}, with evidence_refs[] = [{company, source_type, source_id, date, quote}] (one entry per company/event that coined it). Judge from the EVIDENCE, not the bare name string. If evidence is missing, vague, or MIXED (the quotes show different meanings across companies), do not fold or admit blindly — keep separate or skip. If evidence is MIXED, PREFER keep-separate over rewrite, unless the rewrite is ONLY a wording fix (never one that changes meaning).`

const MIXED_FLAGS = { type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','why','n_companies'], properties:{ driver_name:{type:'string'}, why:{type:'string'}, n_companies:{type:'integer'} }}, description:'flag-triggered D5: names whose OWN evidence shows TWO+ different real-world meanings (a mixed same-name union); [] if none' }

const DEDUP_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_links','rejected_pairs','mixed_flags','notes'], properties:{
  mixed_flags: MIXED_FLAGS,
    same_as_links:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, why:{type:'string'} }}, description:'reversible SAME_AS: exact same meaning only; canonical MUST be a coined driver_name'},
  rejected_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why_kept_separate'], properties:{ a:{type:'string'}, b:{type:'string'}, why_kept_separate:{type:'string'} }}, description:'looked similar but failed the exact-meaning rule -> NOT linked'},
  notes:{type:'array', items:{type:'string'}} } }

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts','mixed_flags'], properties:{
  mixed_flags: MIXED_FLAGS,
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{ driver_name:{type:'string'}, verdict:{type:'string', enum:['admit','rewrite','skip'], description:'admit | rewrite | skip'}, rewrite_to:{type:'string', description:'target name if verdict=rewrite (MUST be a coined driver_name), else ""'}, reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true, description:'admit/rewrite/skip totals'} } }

const REFUTE_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_verdicts','rewrite_verdicts'], properties:{
  same_as_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','survives','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, survives:{type:'boolean', description:'TRUE only if you CANNOT refute they are the EXACT same object AND scope AND mechanism; any doubt = FALSE'}, why:{type:'string'} }}},
  rewrite_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','rewrite_to','survives','why'], properties:{ driver_name:{type:'string'}, rewrite_to:{type:'string'}, survives:{type:'boolean', description:'TRUE only if the rewrite is provably WORDING-ONLY (identical meaning); any change of object/scope/mechanism = FALSE'}, why:{type:'string'} }}} } }

const ASSEMBLE_SCHEMA = { type:'object', additionalProperties:false, required:['ok','sha_line'], properties:{
  ok:{type:'boolean'}, sha_line:{type:'string', description:'the exact ASSEMBLED... line printed by assemble_catalog.py (or the exact error output if ok=false)'} } }

phase('Guard')
// §11.11 SEED_MAX guard — deterministic, BEFORE any AI call (fail-close; sub-split required if it trips).
const GUARD_SCHEMA = { type:'object', additionalProperties:false, required:['records','chars','ok'], properties:{ records:{type:'integer'}, chars:{type:'integer'}, ok:{type:'boolean'} } }
const guard = await agent(`Run these with Bash, in order. Step 0 — BILLING GUARD (subscription-only hard condition): test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; }
If step 0 prints BILLING-GUARD FAIL, STOP and return records=-1, chars=-1, ok=false. Otherwise run this EXACT command and return the printed JSON fields verbatim:
${PY} -c "import json;d=json.load(open('${SEED}'));c=d.get('catalog') or [];s=len(json.dumps(c,separators=(',',':'),ensure_ascii=False));print(json.dumps({'records':len(c),'chars':s,'ok':len(c)<=400 and s<=300000}))"`, {schema:GUARD_SCHEMA, model:MODELS.clerk, label:'seed-max-guard', phase:'Guard'})
if (!guard || guard.records < 0) throw new Error('BILLING-GUARD: ANTHROPIC_API_KEY present in env (or guard agent died) — refusing to run; subscription-only policy (CLAUDE.md).')
// §11.11 sub-split — ALWAYS slice (12th pass rev3, owner-confirmed condition): review prompts must only
// ever read CODE-capped batch files; no guard-relay value may route the full oversized seed into an AI
// prompt. slice_seed.py decides 1-vs-N deterministically (under-cap seed = one batch). Cross-batch
// SAME_AS misses = the ACCEPTED residual (under-merge, safe direction; the §13.2 repair pass is the
// catch-up). Assembly + validation still run over the WHOLE seed (code has no size limit).
const SLICE_SCHEMA = { type:'object', additionalProperties:false, required:['ok','files','notes'], properties:{ ok:{type:'boolean'}, files:{type:'array', items:{type:'string'}}, notes:{type:'string'} } }
const slice = await agent(`Run this EXACT command with Bash (deterministic slicing of the seed into review batches under the §11.11 caps — the proven slicer, now a tested CLI):
${PY} ${DIR}/workflows/slice_seed.py ${RUN_DIR}
Return ok=true + files (exact list from the printed JSON), notes = the printed notes. Non-zero exit: ok=false, files=[], notes = the exact error.`, {schema:SLICE_SCHEMA, model:MODELS.clerk, label:'slice', phase:'Guard'})
if (!slice || !slice.ok || !slice.files.length) throw new Error(`seed slicing failed: ${slice && slice.notes}`)
const BATCH_FILES = slice.files
if (!guard.ok) log(`SEED over §11.11 caps (records=${guard.records}, chars=${guard.chars}) → ${BATCH_FILES.length} name-sorted review batches; cross-batch SAME_AS = accepted residual`)

phase('Review')
const norm = s => (s||'').trim().toLowerCase()
// Stage-0 #4/#5 write-fidelity hash (assemble_catalog.h32 reproduces this exactly):
const h32 = s => { let h = 0; for (let i = 0; i < s.length; i++) h = ((Math.imul(h, 31) + s.charCodeAt(i)) >>> 0); return h }
// Audit-text cleanup (owner-approved): control chars (newline/tab) in judge NOTE text become
// spaces at FILE-BUILD time only — after all judging, never touching names/verdicts — so a
// multi-line "why" can never make the relay-written JSON unparseable (probe-verified risk).
const clean = s => (s || '').replace(/[\u0000-\u001f]/g, ' ')
const survivingLinks = [], appliedRewrites = [], parkedRewrites = [], allGateVerdicts = [], allMixedFlags = [], hbRefute2 = []
for (let bi = 0; bi < BATCH_FILES.length; bi++) {
  const bf = BATCH_FILES[bi]
  const tag = BATCH_FILES.length > 1 ? ` [batch ${bi + 1}/${BATCH_FILES.length}]` : ''
  const batchNote = BATCH_FILES.length > 1 ? ' (This file is ONE name-sorted batch of a larger seed — judge only what is in it.)' : ''
  const [dedup, gate] = await parallel([
    () => agent(`NAMING RULES — authority = 02_DriverCatalog.md NAME-01…19 (inlined verbatim; PIPE-16):
${RULEBOOK}
${MF02}

Now read ${bf} — it is { catalog:[ {driver_name, canonical_name, companies, evidence_refs:[{company,source_type,source_id,date,quote}]} ] }. The driver_names are already DISTINCT (one record each).${batchNote}
TASK = propose final reversible SAME_AS links over them. STRICT rules:
- ${EXACT_MEANING_RULE}
- ${evidenceRule(bf)}
- NEVER link names with different scopes, geographies, objects, metrics, or mechanisms. List those under rejected_pairs with why.
- FLAG-TRIGGERED D5 (rare): if ONE record's OWN evidence quotes show TWO+ DIFFERENT real-world meanings (a same-name union of different causes across companies), add it to mixed_flags [{driver_name, why, n_companies}] — a separate review will split or park it. Flag ONLY genuinely mixed-meaning unions; same-meaning convergence across companies is GOOD and never flagged. mixed_flags=[] if none.
- For each link pick the CANONICAL (shortest standard form, NAME-06/08 — and it MUST be one of the COINED driver_names in the catalog, never an invented name) + the variant. Reversible only; never delete or merge nodes. A singular/plural pair naming the same concept is a wording variant — fold to one form; if meaning may differ (booking/bookings), keep separate.
Return DEDUP_SCHEMA.`, {schema:DEDUP_SCHEMA, model:MODELS.dedup, effort:'high', label:`dedup${tag}`, phase:'Review'}),
    () => agent(`You are an INDEPENDENT admission gate — judge each name FRESH and skeptically; do NOT assume the producer that coined it was right.
NAMING RULES — authority = 02_DriverCatalog.md NAME-01…19 (inlined verbatim; PIPE-16):
${RULEBOOK}
${MF02}

Read the catalog[] records in ${bf} (each = {driver_name, companies, evidence_refs}).${batchNote}
THE ONE TEST: is this a VALID, REUSABLE, consistently-nameable Driver? Give EACH driver_name ONE verdict:
- admit = a valid reusable cause that follows every rule.
- rewrite = right driver, fixable WORDING-ONLY rule-break; give rewrite_to. It must NOT change the meaning AND must be a name some company already coined (an existing driver_name in the catalog). If no coined clean form exists, admit as-is or skip — do NOT invent a new name.
- skip = vague, rule-breaking, or tied to ONE specific event/date/quarter/headline (NOT a reusable class).
  Reusability is about the CLASS, not the count: a reusable event class (e.g. government_shutdown, food_safety_incident, goodwill_impairment, ceo_change) is ADMITTED even if it appears once; only a name bound to a single instance (e.g. q1_2026_shutdown_effect) is skipped.
${EXACT_MEANING_RULE}
${evidenceRule(bf)}
Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; if it is a valid reusable driver, admit it.
FLAG-TRIGGERED D5 (rare): if a record's OWN evidence shows TWO+ DIFFERENT real-world meanings under one name (a mixed same-name union), give it verdict=admit AND add it to mixed_flags [{driver_name, why, n_companies}] — a separate review will split or park it; do NOT skip it merely for being mixed. mixed_flags=[] if none. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, model:MODELS.gate, effort:'high', label:`gate${tag}`, phase:'Review'}),
  ])
  if (!dedup || !gate) throw new Error(`Review batch ${bi + 1}/${BATCH_FILES.length}: ${!dedup ? 'dedup' : ''}${!dedup && !gate ? '+' : ''}${!gate ? 'gate' : ''} agent died (likely session limit / API error) — fail-close, no partial review.`)

  const refute = await agent(`You are an INDEPENDENT skeptic. Your ONLY job: BREAK fusions — decisions that fold two DIFFERENT drivers into one. Read ${bf} — each driver_name is a catalog[] record with evidence_refs[{company, source_type, source_id, date, quote}]. For BOTH lists, default survives=FALSE; mark TRUE only if you genuinely cannot refute it.
${MF02}

1) PROPOSED SAME_AS LINKS (canonical <= variant): ${JSON.stringify(dedup.same_as_links)}
   survives=TRUE only if, reading BOTH names' evidence quotes, they are the EXACT same object AND scope AND mechanism (the 3-check). Different metric/geography/mechanism, or mixed evidence -> FALSE.

2) PROPOSED REWRITES (driver_name -> rewrite_to): ${JSON.stringify((gate.verdicts||[]).filter(v => v.verdict==='rewrite').map(v => ({driver_name:v.driver_name, rewrite_to:v.rewrite_to})))}
   survives=TRUE only if the rewrite is provably WORDING-ONLY: rewrite_to means the IDENTICAL driver the evidence describes (a pure spelling / standard-phrase / word-order fix). Any change of object/scope/mechanism -> FALSE.

Return REFUTE_SCHEMA: one verdict for EVERY link and EVERY rewrite, each with a one-line why.`, {schema:REFUTE_SCHEMA, model:MODELS.refute, effort:'high', label:`refute${tag}`, phase:'Refute'})

  if (!refute) throw new Error(`Review batch ${bi + 1}/${BATCH_FILES.length}: refute agent died (likely session limit / API error) — fail-close, no unrefuted fusions.`)
  // JS mechanically FILTERS rejected decisions (per batch). Missing verdict -> not survives -> never fuse (fail-close).
  const linkOk = new Map((refute.same_as_verdicts||[]).map(v => [`${norm(v.canonical)}|${norm(v.variant)}`, v.survives === true]))
  const rwOk   = new Map((refute.rewrite_verdicts||[]).map(v => [`${norm(v.driver_name)}|${norm(v.rewrite_to)}`, v.survives === true]))
  let batchLinks = (dedup.same_as_links||[]).filter(l => linkOk.get(`${norm(l.canonical)}|${norm(l.variant)}`) === true).map(l => ({canonical:l.canonical, variant:l.variant}))
  const gateRewrites = (gate.verdicts||[]).filter(v => v.verdict==='rewrite')
  let batchApplied = gateRewrites.filter(v => rwOk.get(`${norm(v.driver_name)}|${norm(v.rewrite_to)}`) === true).map(v => ({from:v.driver_name, to:v.rewrite_to}))
  const batchParked = gateRewrites.filter(v => rwOk.get(`${norm(v.driver_name)}|${norm(v.rewrite_to)}`) !== true).map(v => { const s=(refute.rewrite_verdicts||[]).find(x => norm(x.driver_name)===norm(v.driver_name) && norm(x.rewrite_to)===norm(v.rewrite_to)); return {driver_name:v.driver_name, proposed_to:v.rewrite_to, why:(s&&s.why)||'unverified by skeptic'} })

  // §11.18 HIGH-BLAST second skeptic (12th pass rev2, owner-approved): EVERY surviving fusion touching
  // >= 8 distinct companies — ordinary SAME_AS and rewrites, not just same-name unions — gets a SECOND,
  // independent, perspective-forced Refute (object/scope/mechanism each evidence-quoted), AND-voted with
  // the first. Blast counts are computed by CODE from the batch file (a mechanical count must never be
  // AI-copied — an under-copied count would silently skip the skeptic); the relay agent only echoes the
  // printed JSON, and the relay is tamper-evident (checksum + completeness, mismatch = HARD-FAIL).
  // Refuted/unavailable -> link dropped (kept separate) / rewrite parked. 1-company runs: no-op.
  const HB = 8
  let hbItems = []
  const fusionPairs = [...batchLinks.map(l => ({kind:'link', a:l.canonical, b:l.variant, item:l})),
                       ...batchApplied.map(r => ({kind:'rewrite', a:r.from, b:r.to, item:r}))]
  if (fusionPairs.length) {
    const COUNT_SCHEMA = {type:'object', additionalProperties:false, required:['counts','total'], properties:{ counts:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','n'], properties:{a:{type:'string'}, b:{type:'string'}, n:{type:'integer'}}}}, total:{type:'integer'} }}
    const pairsJson = JSON.stringify(fusionPairs.map(p => ({a:p.a, b:p.b})))
    const cnt = await agent(`Run this EXACT script with Bash and return the printed JSON VERBATIM per the schema (counts[], total). Do not compute anything yourself.
${PY} - <<'PYEOF'
import json
d=json.load(open('${bf}'))
by={(r.get('driver_name') or '').strip().lower(): set(r.get('companies') or []) for r in d['catalog']}
pairs=json.loads(${JSON.stringify(pairsJson)})
out=[{'a':p['a'],'b':p['b'],'n':len(by.get((p['a'] or '').strip().lower(),set())|by.get((p['b'] or '').strip().lower(),set()))} for p in pairs]
print(json.dumps({'counts':out,'total':sum(x['n'] for x in out)}))
PYEOF`, {schema:COUNT_SCHEMA, model:MODELS.clerk, label:`blast-count${tag}`, phase:'Refute'})
    if (!cnt) throw new Error(`blast-count agent died (batch ${bi + 1}) — fail-close, cannot verify fusion blast radii.`)
    if (cnt.counts.length !== fusionPairs.length || cnt.total !== cnt.counts.reduce((s, x) => s + x.n, 0))
      throw new Error(`blast-count relay integrity check failed (batch ${bi + 1}: got ${cnt.counts.length}/${fusionPairs.length} pairs, checksum ${cnt.counts.reduce((s, x) => s + x.n, 0)} vs ${cnt.total}) — fail-close.`)
    const nOf = new Map(cnt.counts.map(x => [`${norm(x.a)}|${norm(x.b)}`, x.n]))
    for (const p of fusionPairs) {
      const n = nOf.get(`${norm(p.a)}|${norm(p.b)}`)
      if (typeof n !== 'number') throw new Error(`blast-count missing pair ${p.a}|${p.b} (batch ${bi + 1}) — fail-close.`)
      p.n = n
    }
    hbItems = fusionPairs.filter(p => p.n >= HB)
  }
  if (hbItems.length) {
    const DIM = {type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string', description:'verbatim supporting quote pair (one per record) if pass=true, else why it fails'}}}
    const HB_SCHEMA = {type:'object', additionalProperties:false, required:['object','scope','mechanism','survives'], properties:{object:DIM, scope:DIM, mechanism:DIM, survives:{type:'boolean'}}}
    log(`[batch ${bi + 1}] high-blast 2nd skeptic on ${hbItems.length} fusion(s) (>= ${HB} companies)`)
    const verdicts = await parallel(hbItems.map(it => () => agent(`You are the SECOND, INDEPENDENT merge skeptic — a high-blast review: this fusion spans ${it.n} companies, so a wrong merge becomes a wrong cross-company trading read-through. In ${bf}, find the catalog[] records named "${it.a}" and "${it.b}". Judge the proposed ${it.kind === 'link' ? `SAME_AS (${it.b} folds into ${it.a})` : `rewrite (${it.a} -> ${it.b})`} DIMENSION BY DIMENSION from the two records' evidence quotes: for EACH of object / scope / mechanism, pass=true ONLY if you can cite verbatim quotes from BOTH records showing they are identical on that dimension; anything you cannot evidence -> pass=false. survives=true ONLY if all three dimensions pass. Default = false (keep separate). Do not defer to any earlier reviewer.`, {schema:HB_SCHEMA, model:MODELS.refute, effort:'high', label:`refute2${tag}:${it.b}`, phase:'Refute'}).then(v => ({it, v})).catch(() => ({it, v:null}))))
    const judged = new Map(verdicts.filter(Boolean).map(r => [r.it, r.v]))
    for (const it of hbItems) {
      const v = judged.get(it)
      const ok = v && v.survives === true && v.object && v.object.pass && v.scope && v.scope.pass && v.mechanism && v.mechanism.pass
      hbRefute2.push({ kind: it.kind, a: it.a, b: it.b, n: it.n, survives: !!ok })   // PROOF -> decisions.json -> approved.json -> validator backstop
      if (!ok) {
        if (it.kind === 'link') batchLinks = batchLinks.filter(l => l !== it.item)
        else { batchApplied = batchApplied.filter(x => x !== it.item); batchParked.push({driver_name:it.a, proposed_to:it.b, why: v ? 'refuted by high-blast second skeptic' : 'high-blast second skeptic unavailable — fail-close'}) }
      }
    }
  }
  survivingLinks.push(...batchLinks.map(l => ({canonical:l.canonical, variant:l.variant})))
  appliedRewrites.push(...batchApplied.map(r => ({from:r.from, to:r.to})))
  parkedRewrites.push(...batchParked)
  allGateVerdicts.push(...(gate.verdicts||[]))
  allMixedFlags.push(...(dedup.mixed_flags||[]), ...(gate.mixed_flags||[]))
}

// ---- LEAF FLAG-TRIGGERED D5 (HierarchicalCatalogPlan D5 leaf path; 10th pass) ----
const flagsByName = {}
for (const f of allMixedFlags) {
  const k = norm(f.driver_name); if (k && !flagsByName[k]) flagsByName[k] = f
}
const flagged = Object.values(flagsByName)
let leafReviews = [], leafSplitMap = []
let d5N = new Map()   // flagged name -> TRUE company count, computed by CODE (12th pass rev2)
if (flagged.length) {
  phase('SameName')
  // The high-blast trigger count is mechanical — CODE computes it from the seed; the agent only relays
  // the printed JSON (tamper-evident: completeness + checksum, mismatch = HARD-FAIL). Never AI-copied.
  const D5COUNT_SCHEMA = { type:'object', additionalProperties:false, required:['counts','total'], properties:{ counts:{type:'array', items:{type:'object', additionalProperties:false, required:['name','n'], properties:{name:{type:'string'}, n:{type:'integer'}}}}, total:{type:'integer'} }}
  const d5cnt = await agent(`Run this EXACT script with Bash and return the printed JSON VERBATIM per the schema (counts[], total). Do not compute anything yourself.
${PY} - <<'PYEOF'
import json
d=json.load(open('${SEED}'))
by={(r.get('driver_name') or '').strip().lower(): set(r.get('companies') or []) for r in d['catalog']}
names=json.loads(${JSON.stringify(JSON.stringify(flagged.map(f => norm(f.driver_name))))})
out=[{'name':n,'n':len(by.get(n,set()))} for n in names]
print(json.dumps({'counts':out,'total':sum(x['n'] for x in out)}))
PYEOF`, {schema:D5COUNT_SCHEMA, model:MODELS.clerk, label:'d5-blast-count', phase:'SameName'})
  if (!d5cnt) throw new Error('d5 blast-count agent died — fail-close.')
  if (d5cnt.counts.length !== flagged.length || d5cnt.total !== d5cnt.counts.reduce((s, x) => s + x.n, 0))
    throw new Error(`d5 blast-count relay integrity check failed (${d5cnt.counts.length}/${flagged.length} names, checksum) — fail-close.`)
  d5N = new Map(d5cnt.counts.map(x => [norm(x.name), x.n]))
  const LEAF_REVIEW_SCHEMA = { type:'object', additionalProperties:false, required:['collision_name','verdict','new_names','assignments','why'], properties:{
    collision_name:{type:'string'}, verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']},
    new_names:{type:'array', items:{type:'string'}},
    assignments:{type:'array', items:{type:'object', additionalProperties:false, required:['company','to'], properties:{ company:{type:'string'}, to:{type:'string'}, ref_idx:{type:'array', items:{type:'string'}, description:'the idx values (r1, r2, ...) of the refs that go to this name — copied from the view; omit on at most ONE row per company = that row takes ALL remaining refs of the company'} }}},
    why:{type:'string'} } }
  const LEAF_REFUTE_SCHEMA = { type:'object', additionalProperties:false, required:['survives','why'], properties:{ survives:{type:'boolean'}, why:{type:'string'} } }
  const MINIGATE_SCHEMA = { type:'object', additionalProperties:false, required:['all_admit','reasons'], properties:{ all_admit:{type:'boolean'}, reasons:{type:'string'} } }
  const pyRec = (nm) => `${PY} -c "import json;d=json.load(open('${SEED}'));r=next(x for x in d['catalog'] if (x.get('driver_name') or '').strip().lower()=='${nm}')
k=lambda e:((e.get('company') or '').strip().lower(),(e.get('source_type') or '').strip().lower(),(e.get('source_id') or '').strip().lower(),(e.get('date') or '').strip().lower(),(e.get('quote') or '').strip())
allr=sorted(r['evidence_refs'],key=k)
view=[dict(e, idx='r%d'%(i+1)) for i,e in enumerate(allr)][:200]
gs={}
for e in view: gs.setdefault((e.get('company') or '').strip(),[]).append(e)
names=sorted((x.get('driver_name') or '').strip().lower() for x in d['catalog'])
print(json.dumps({'name':r['driver_name'],'total_refs':len(allr),'truncated':len(allr)>200,'existing_seed_names':names,'sides':[{'company':c,'refs':v} for c,v in sorted(gs.items(), key=lambda kv:(len(kv[1]),kv[0]))]}))"`
  const rawReviews = (await parallel(flagged.map(f => () => agent(`SAME-NAME REVIEW (leaf, flag-triggered — HierarchicalCatalogPlan D5). The single record "${norm(f.driver_name)}" was FLAGGED as possibly mixing different meanings under one name (reviewer note: ${f.why}).
Read ${ONT}. LOAD THE EVIDENCE (grouped per company, smallest side first): run Bash:
${pyRec(norm(f.driver_name))}
${EXACT_MEANING_RULE}
ONE verdict:
- SAME = all quotes name the EXACT same reusable cause (the flag was a false alarm). An independent skeptic will still try to break this.
- DIFFERENT = a true homonym: coin MORE-SPECIFIC lower_snake_case names ONLY from words in the evidence (per the NAME rules; no tickers/company names), one per distinct meaning. HARD CONSTRAINT: every new name must be genuinely NEW — check it against the view's existing_seed_names list; if your natural choice already exists there, add a distinguishing evidence word to make it more specific (a near-duplicate is fine — dedup links exact duplicates later; a COLLISION hard-fails). Then PARTITION BY INDEX: every ref in the view carries an 'idx' (r1, r2, ...). An assignment row = {company, to, ref_idx: ["r1", "r4", ...]} — the listed refs go to that name. You may OMIT ref_idx on AT MOST ONE row per company: that row takes ALL remaining refs of that company (the remainder). Rules: every ref ends up with exactly one name (code enforces it); every 'to' name must receive at least one ref; two no-ref_idx rows for the same company is an ERROR. Just read each quote, decide which meaning it shows, and copy its idx.
- UNCLEAR = too thin/mixed to decide → park (fail-close).
TRUNCATION RULE (12th pass rev3): if the view shows truncated:true you are seeing only 200 of total_refs — a complete split partition is impossible from a partial view, so DIFFERENT is FORBIDDEN: return SAME (skeptics still check it) or UNCLEAR (park) only.
Return LEAF_REVIEW_SCHEMA (collision_name = "${norm(f.driver_name)}").`, {schema:LEAF_REVIEW_SCHEMA, model:MODELS.d5, effort:'high', label:`d5:${norm(f.driver_name)}`, phase:'SameName'}))) ).filter(Boolean)
  if (rawReviews.length !== flagged.length) throw new Error(`leaf D5 review lost ${flagged.length - rawReviews.length} verdict(s) — fail-close.`)
  for (const v of rawReviews) {
    const nm = norm(v.collision_name)
    if (v.verdict === 'SAME') {
      const r1 = await agent(`INDEPENDENT skeptic on a flagged same-name union: "${nm}" (one leaf record spanning companies). Try to BREAK the claim that all its evidence names ONE driver. Default survives=FALSE.
LOAD THE EVIDENCE: run Bash:
${pyRec(nm)}
${EXACT_MEANING_RULE}
survives=TRUE only if you genuinely cannot refute exact same object AND scope AND mechanism across ALL quotes. Return LEAF_REFUTE_SCHEMA.`, {schema:LEAF_REFUTE_SCHEMA, model:MODELS.d5, effort:'high', label:`d5-refute:${nm}`, phase:'SameName'})
      let ok = r1 && r1.survives === true
      const hbD5 = (d5N.has(nm) ? d5N.get(nm) : Infinity) >= 8
      if (ok && hbD5) {   // §11.18 high-blast at leaf — CODE-computed count; unknown name -> MORE scrutiny, never less
        const r2 = await agent(`SECOND independent skeptic (HIGH-BLAST union: many companies). Same union "${nm}". Judge EACH lens with a quote: same OBJECT? same SCOPE? same MECHANISM? survives = all three pass.
LOAD: run Bash:
${pyRec(nm)}
Return JSON per schema.`, {schema:{ type:'object', additionalProperties:false, required:['object','scope','mechanism','survives'], properties:{ object:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}}, scope:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}}, mechanism:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}}, survives:{type:'boolean'} }}, model:MODELS.d5, effort:'high', label:`d5-refute2:${nm}`, phase:'SameName'})
        ok = !!(r2 && r2.survives === true && r2.object && r2.object.pass === true && r2.scope && r2.scope.pass === true && r2.mechanism && r2.mechanism.pass === true)
      }
      leafReviews.push(ok ? { collision_name: nm, verdict: 'SAME', why: v.why, refute_survived: true, ...(hbD5 ? { high_blast_refute2_survived: true } : {}) }
                          : { collision_name: nm, verdict: 'UNCLEAR', why: `SAME refuted by skeptic (fail-close): ${v.why}` })
    } else if (v.verdict === 'DIFFERENT') {
      const mg = await agent(`Mini-G2 on ${v.new_names.length} proposed split names (from the homonym split of "${nm}"): ${JSON.stringify(v.new_names)}. Read ${ONT}. all_admit=TRUE only if EVERY name is a valid, reusable, rule-following lower_snake driver name (no tickers, no states, not vague). Return MINIGATE_SCHEMA.`, {schema:MINIGATE_SCHEMA, model:MODELS.gate, effort:'high', label:`d5-gate:${nm}`, phase:'SameName'})
      if (mg && mg.all_admit === true) {
        leafReviews.push({ collision_name: nm, verdict: 'DIFFERENT', new_names: v.new_names, why: v.why })
        leafSplitMap.push({ from: nm, to: v.new_names, assignments: v.assignments.map(a => { const row = { company: a.company, to: a.to }; if (Array.isArray(a.ref_idx) && a.ref_idx.length) row.ref_idx = a.ref_idx; return row }) })
      } else {
        leafReviews.push({ collision_name: nm, verdict: 'UNCLEAR', why: `split names failed mini-gate (${(mg && mg.reasons) || 'no verdict'}) — parked fail-close: ${v.why}` })
      }
    } else leafReviews.push({ collision_name: nm, verdict: 'UNCLEAR', why: v.why })
  }
}
// Names re-shaped by the review (split-from + parked) must NOT be referenced by any decision (assembler hard-fails).
const reshaped = new Set(leafReviews.filter(r => r.verdict !== 'SAME').map(r => r.collision_name))
const touches = (...names) => names.some(n => reshaped.has(norm(n)))

phase('Assemble')
// Deterministic assembly (HierarchicalCatalogPlan §11.19): the 5-way precedence runs in CODE
// (assemble_catalog.py, pytest-covered). The agent below is a dumb pen for the SMALL decisions.json
// + a Bash runner; it never composes catalog content, so it cannot fabricate a fusion.
const decisions = {
  gate_verdicts: allGateVerdicts.filter(v => !touches(v.driver_name, v.rewrite_to)).map(v => ({ driver_name: v.driver_name, verdict: v.verdict, rewrite_to: v.rewrite_to || '', reason: clean(v.reason) })),
  approved_same_as: survivingLinks.filter(l => !touches(l.variant, l.canonical)).map(l => ({ variant: l.variant, canonical: l.canonical })),
  approved_rewrites: appliedRewrites.filter(r => !touches(r.from, r.to)).map(r => ({ from: r.from, to: r.to })),
  parked_rewrites: parkedRewrites.filter(p => !touches(p.driver_name, p.proposed_to)).map(p => ({ driver_name: p.driver_name, proposed_to: p.proposed_to, why: clean(p.why) })),
  high_blast_refute2: hbRefute2.filter(x => !touches(x.a, x.b)),
}
// Stage-0 #4/#5: the agent re-types these JSON strings to disk; the CLI verifies the
// on-disk files against counts + h32 computed HERE from the source strings (relay-write
// fidelity — a dropped/added/edited row or any reformat hard-fails assemble_catalog.py).
const decisionsJson = JSON.stringify(decisions)
const decExpect = `gv=${decisions.gate_verdicts.length},sa=${decisions.approved_same_as.length},rw=${decisions.approved_rewrites.length},pk=${decisions.parked_rewrites.length},hb=${decisions.high_blast_refute2.length},h32=${h32(decisionsJson)}`
const reviewJson = flagged.length ? JSON.stringify({ reviews: leafReviews.map(r => ({ ...r, why: clean(r.why) })), split_map: leafSplitMap }) : null
const reviewArgs = flagged.length ? ` --review ${RUN_DIR}/same_name_review.json --expect-review 'rv=${leafReviews.length},sm=${leafSplitMap.length},h32=${h32(reviewJson)}'` : ''
const reviewStep = flagged.length ? `1b) Use the Write tool to save this EXACT JSON (byte-for-byte) to ${RUN_DIR}/same_name_review.json:
${reviewJson}
` : ''
const out = await agent(`Steps (assembler rev3 — Stage-0 write-fidelity expects), EXACT, in order:
1) Use the Write tool to save this EXACT JSON (byte-for-byte, do not reformat) to ${RUN_DIR}/decisions.json:
${decisionsJson}
${reviewStep}2) Run with Bash: ${PY} ${DIR}/workflows/assemble_catalog.py ${RUN_DIR} --expect '${decExpect}'${reviewArgs}
   (deterministic code: reads seed.json + decisions.json from DISK, applies the 5-way precedence, writes catalog.json + approved.json, prints an "ASSEMBLED ..." line with the catalog sha256 + counts)
Return ok=true and sha_line = the exact printed ASSEMBLED line. If the script exits NON-ZERO: ok=false, sha_line = the exact error output. Do NOT edit or compose any catalog content yourself.`, {schema:ASSEMBLE_SCHEMA, model:MODELS.clerk, label:'assemble', phase:'Assemble'})
if (!out) throw new Error('Assemble agent died (likely session limit / API error) — fail-close.')
if (!out.ok) throw new Error(`assemble_catalog.py failed: ${out.sha_line}`)

phase('Validate')
const validation = await agent(`Run this EXACT Bash command (validator rev2 — transitive D1; it writes the validator output to validation.txt in the run dir AND reports the validator's real exit code; the 3rd arg enables the D1 fusion-approval + same_as_variants checks):
${PY} ${DIR}/workflows/validate_catalog.py ${SEED} ${CAT} ${RUN_DIR}/approved.json${flagged.length ? ` --review ${RUN_DIR}/same_name_review.json` : ''} | tee ${RUN_DIR}/validation.txt ; echo "exit=\${PIPESTATUS[0]}"
This is a deterministic structure check (no judgment). If exit is NON-ZERO, begin your reply with "VALIDATION FAILED" and paste the exact failing checks + names. If exit is 0, begin with "VALIDATION PASSED". Do not fix anything; just report.`, {model:MODELS.clerk, label:'validate', phase:'Validate'})
if (!validation) throw new Error('Validate agent died (likely session limit / API error) — fail-close.')

// F4: persist the resolved model map (provenance) to the run dir.
await agent(`Use the Write tool to save EXACTLY this JSON (byte-for-byte) to ${RUN_DIR}/reconcile_models.json:
${JSON.stringify(MODELS_PROV)}
Then return {ok:true}.`, {schema:{ type:'object', additionalProperties:true, required:['ok'], properties:{ ok:{type:'boolean'} } }, model:MODELS.clerk, label:'record-models', phase:'Validate'})

return { assembled: out.sha_line, counts: { same_as: survivingLinks.length, rewrites_applied: appliedRewrites.length, rewrites_parked: parkedRewrites.length, d5_flags: flagged.length, d5_verdicts: leafReviews.map(r => r.verdict) }, validation }
