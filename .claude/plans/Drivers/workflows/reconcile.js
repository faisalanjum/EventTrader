export const meta = {
  name: 'driver-reconcile-restaurants',
  description: 'Step 2 reconcile over the Restaurants seed menu: (Dedup) canonical + reversible SAME_AS for exact-same-meaning only = the REUSE arm; (Gate) independent admit/rewrite/skip per DriverOntology (one test: valid reusable driver?). Review-file only; no graph writes; no merges/deletes.',
  phases: [ { title: 'Review', detail: 'dedup proposer + independent gate, in parallel' }, { title: 'Refute', detail: 'independent skeptic breaks bad SAME_AS + meaning-changing rewrites; JS filters them out' }, { title: 'Write', detail: 'assemble the clean catalog from the skeptic-filtered lists' }, { title: 'Validate', detail: 'deterministic structure check (zero judgment); HARD-FAIL if broken' } ],
}

const DIR  = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY   = '/home/faisal/EventMarketDB/venv/bin/python3'
const CAT  = '/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_catalog.json'
const SEED = '/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_seed.json'
const ONT  = '/home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology.md'
const EXACT_MEANING_RULE = `For any proposed SAME_AS, reuse, or rewrite, first verify all three are true:
1. same object or metric
2. same scope
3. same mechanism

If any one is false or unclear, do not SAME_AS, reuse, or rewrite. Keep the names separate, admit separately, or skip.
A rewrite may only change wording. It must not change the underlying driver.`

const EVIDENCE_RULE = `EVIDENCE: each distinct driver_name has one or more candidate records in ${SEED} (across the company menus), each with a quote (the actual source words) + source + date. Judge from the EVIDENCE, not the bare name string. If evidence is missing, vague, or MIXED (the quotes show different meanings across companies), do not fold or admit blindly — keep separate or skip. If evidence is MIXED, PREFER keep-separate over rewrite, unless the rewrite is ONLY a wording fix (never one that changes meaning).`

const DEDUP_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_links','rejected_pairs','notes'], properties:{
    same_as_links:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, why:{type:'string'} }}, description:'reversible SAME_AS: exact same meaning only'},
  rejected_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why_kept_separate'], properties:{ a:{type:'string'}, b:{type:'string'}, why_kept_separate:{type:'string'} }}, description:'looked similar but failed the exact-meaning rule -> NOT linked'},
  notes:{type:'array', items:{type:'string'}} } }

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{ driver_name:{type:'string'}, verdict:{type:'string', enum:['admit','rewrite','skip'], description:'admit | rewrite | skip'}, rewrite_to:{type:'string', description:'target name if verdict=rewrite, else ""'}, reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true, description:'admit/rewrite/skip totals'} } }

const REFUTE_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_verdicts','rewrite_verdicts'], properties:{
  same_as_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','survives','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, survives:{type:'boolean', description:'TRUE only if you CANNOT refute they are the EXACT same object AND scope AND mechanism; any doubt = FALSE'}, why:{type:'string'} }}},
  rewrite_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','rewrite_to','survives','why'], properties:{ driver_name:{type:'string'}, rewrite_to:{type:'string'}, survives:{type:'boolean', description:'TRUE only if the rewrite is provably WORDING-ONLY (identical meaning); any change of object/scope/mechanism = FALSE'}, why:{type:'string'} }}} } }

const WRITE_SCHEMA = { type:'object', additionalProperties:false, required:['file_written','final_catalog_count','same_as_count','rewrite_count','skip_count','unresolved_rewrite_count','summary'], properties:{
  file_written:{type:'string'}, final_catalog_count:{type:'integer'}, same_as_count:{type:'integer'}, rewrite_count:{type:'integer'}, skip_count:{type:'integer'}, unresolved_rewrite_count:{type:'integer'}, summary:{type:'string'} } }

phase('Review')
const [dedup, gate] = await parallel([
  () => agent(`Read ${ONT} (the rules) and ${SEED} (keys: menus[].candidates[].driver_name, plus analysis.exact_dup_pairs which are PROPOSALS to validate). Collect the DISTINCT driver_names.
TASK = propose final reversible SAME_AS links over them. STRICT rules:
- ${EXACT_MEANING_RULE}
- ${EVIDENCE_RULE}
- NEVER link names with different scopes, brands, segments, geographies, objects, metrics, or mechanisms. List those under rejected_pairs with why.
- For each link pick the CANONICAL (shortest standard form, R6) + the variant. Reversible only; never delete or merge nodes.
Return DEDUP_SCHEMA.`, {schema:DEDUP_SCHEMA, label:'dedup', phase:'Review'}),
  () => agent(`You are an INDEPENDENT admission gate — judge each name FRESH and skeptically; do NOT assume the producer that coined it was right. Read ${ONT} and collect the DISTINCT driver_names from ${SEED} (menus[].candidates[].driver_name).
THE ONE TEST: is this a VALID, REUSABLE, consistently-nameable Driver? Give EACH distinct name ONE verdict:
- admit = a valid reusable cause that follows every rule. (Brand/segment-specific names ARE valid drivers — admit them.)
- rewrite = right driver, fixable WORDING-ONLY rule-break; give rewrite_to (must NOT change the meaning).
- skip = vague, rule-breaking, or tied to ONE specific event/date/quarter/headline (NOT a reusable class).
  Reusability is about the CLASS, not the count: a reusable event class (e.g. government_shutdown, food_safety_incident, goodwill_impairment, ceo_change) is ADMITTED even if it appears once; only a name bound to a single instance (e.g. q1_2026_shutdown_effect) is skipped.
${EXACT_MEANING_RULE}
${EVIDENCE_RULE}
Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; if it is a valid reusable driver, admit it. KEEP brand/segment-specific names. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, label:'gate', phase:'Review'}),
])

phase('Refute')
const refute = await agent(`You are an INDEPENDENT skeptic. Your ONLY job: BREAK fusions — decisions that fold two DIFFERENT drivers into one. Read ${SEED} for each name's evidence (menus[].candidates[] = {driver_name, quote, source, date}, across the company menus). For BOTH lists, default survives=FALSE; mark TRUE only if you genuinely cannot refute it.

1) PROPOSED SAME_AS LINKS (canonical <= variant): ${JSON.stringify(dedup.same_as_links)}
   survives=TRUE only if, reading BOTH names' evidence quotes, they are the EXACT same object AND scope AND mechanism (the 3-check). Different brand/segment vs company-wide, different metric/geography/mechanism, or mixed evidence -> FALSE.

2) PROPOSED REWRITES (driver_name -> rewrite_to): ${JSON.stringify((gate.verdicts||[]).filter(v => v.verdict==='rewrite').map(v => ({driver_name:v.driver_name, rewrite_to:v.rewrite_to})))}
   survives=TRUE only if the rewrite is provably WORDING-ONLY: rewrite_to means the IDENTICAL driver the evidence describes (a pure spelling / standard-phrase / word-order fix). Any change of object/scope/mechanism -> FALSE.

Return REFUTE_SCHEMA: one verdict for EVERY link and EVERY rewrite, each with a one-line why.`, {schema:REFUTE_SCHEMA, label:'refute', phase:'Refute'})

// JS mechanically FILTERS rejected decisions out of the writer's INPUT (the skeptic made the judgment; this only applies its booleans). Missing verdict -> not survives -> never fuse (fail-close).
const norm = s => (s||'').trim().toLowerCase()
const linkOk = new Map((refute.same_as_verdicts||[]).map(v => [`${norm(v.canonical)}|${norm(v.variant)}`, v.survives === true]))
const rwOk   = new Map((refute.rewrite_verdicts||[]).map(v => [`${norm(v.driver_name)}|${norm(v.rewrite_to)}`, v.survives === true]))
const survivingLinks  = (dedup.same_as_links||[]).filter(l => linkOk.get(`${norm(l.canonical)}|${norm(l.variant)}`) === true).map(l => ({canonical:l.canonical, variant:l.variant}))
const gateRewrites    = (gate.verdicts||[]).filter(v => v.verdict==='rewrite')
const appliedRewrites = gateRewrites.filter(v => rwOk.get(`${norm(v.driver_name)}|${norm(v.rewrite_to)}`) === true).map(v => ({from:v.driver_name, to:v.rewrite_to}))
const parkedRewrites  = gateRewrites.filter(v => rwOk.get(`${norm(v.driver_name)}|${norm(v.rewrite_to)}`) !== true).map(v => { const s=(refute.rewrite_verdicts||[]).find(x => norm(x.driver_name)===norm(v.driver_name) && norm(x.rewrite_to)===norm(v.rewrite_to)); return {driver_name:v.driver_name, proposed_to:v.rewrite_to, why:(s&&s.why)||'unverified by skeptic'} })

phase('Write')
const out = await agent(`Read ${SEED}. Assemble the final clean Restaurants catalog from the SKEPTIC-FILTERED lists below and WRITE it (Write tool) to /home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_catalog.json.
GATE verdicts (use for admit/skip ONLY; for rewrites use the two lists below, NOT these): ${JSON.stringify(gate.verdicts)}
APPROVED same_as (skeptic-filtered — copy EXACTLY, add none, drop none): ${JSON.stringify(survivingLinks)}
APPROVED rewrites (skeptic-filtered — copy EXACTLY, add none, drop none): ${JSON.stringify(appliedRewrites)}
PARKED rewrites (refuted — copy VERBATIM into unresolved_rewrites; do NOT apply, do NOT put in final or skips): ${JSON.stringify(parkedRewrites)}
Catalog file shape = { industry:'Restaurants', final_drivers:[{driver_name, n_companies}], same_as:[{canonical,variant}], rewrites:[{from,to}], skips:[{driver_name,why}], unresolved_rewrites:[{driver_name, proposed_to, why}], counts:{...} }.
RULES (exactly):
- same_as MUST equal the APPROVED same_as list exactly (no additions, no removals).
- rewrites MUST equal the APPROVED rewrites list exactly (no additions, no removals).
- unresolved_rewrites MUST equal the PARKED rewrites list verbatim.
- final_drivers = gate-admitted names + approved rewrite TARGETS; REMOVE same_as variants, skips, and parked-rewrite names. A name whose only proposed link was dropped resolves by its OWN gate verdict (admit -> final, skip -> skips).
- NO kind field, NO route/scope bucket.
Return WRITE_SCHEMA (compact; do not echo the whole catalog).`, {schema:WRITE_SCHEMA, label:'write', phase:'Write'})

phase('Validate')
const validation = await agent(`Run this EXACT Bash command and report its full stdout AND its exit code:
${PY} ${DIR}/workflows/validate_catalog.py ${SEED} ${CAT}
This is a deterministic structure check (no judgment). If it exits NON-ZERO, begin your reply with "VALIDATION FAILED" and paste the exact failing checks + names. If it exits 0, begin with "VALIDATION PASSED". Do not fix anything; just report.`, {label:'validate', phase:'Validate'})

return { catalog: out, validation }
