export const meta = {
  name: 'driver-reconcile',
  description: 'Step 2 reconcile over a per-industry seed catalog (args.run_id = the exact menu_build run; reads runs/<run_id>/seed.json, writes catalog.json + validation.txt there; per-driver records with evidence_refs): (Dedup) canonical + reversible SAME_AS for exact-same-meaning only = the REUSE arm; (Gate) independent admit/rewrite/skip per DriverOntology; (Refute) skeptic breaks bad SAME_AS + meaning-changing rewrites; (Write) assemble per-driver records with canonical_name + side-lists. Review-file only; no graph writes; no merges/deletes. Roll-up/rewrite targets must be COINED names.',
  phases: [ { title: 'Review', detail: 'dedup proposer + independent gate, in parallel' }, { title: 'Refute', detail: 'independent skeptic breaks bad SAME_AS + meaning-changing rewrites; JS filters them out' }, { title: 'Write', detail: 'assemble per-driver records (set canonical_name) + skips/unresolved side-lists' }, { title: 'Validate', detail: 'deterministic structure check (zero judgment); HARD-FAIL if broken' } ],
}

const DIR    = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY     = '/home/faisal/EventMarketDB/venv/bin/python3'
const RUN_ID = (args && args.run_id) || ''
if (!RUN_ID) throw new Error('reconcile.js requires args.run_id (e.g. "2026-06-07_143205_restaurants" from menu_build). Refusing to guess "latest".')
const RUN_DIR = `${DIR}/runs/${RUN_ID}`
const SEED = `${RUN_DIR}/seed.json`
const CAT  = `${RUN_DIR}/catalog.json`
const ONT  = `${DIR}/DriverOntology.md`
const EXACT_MEANING_RULE = `For any proposed SAME_AS, reuse, or rewrite, first verify all three are true:
1. same object or metric
2. same scope
3. same mechanism

If any one is false or unclear, do not SAME_AS, reuse, or rewrite. Keep the names separate, admit separately, or skip.
A rewrite may only change wording. It must not change the underlying driver.`

const EVIDENCE_RULE = `EVIDENCE: each driver_name is ONE catalog[] record in ${SEED}, with evidence_refs[] = [{company, source_type, source_id, date, quote}] (one entry per company/event that coined it). Judge from the EVIDENCE, not the bare name string. If evidence is missing, vague, or MIXED (the quotes show different meanings across companies), do not fold or admit blindly — keep separate or skip. If evidence is MIXED, PREFER keep-separate over rewrite, unless the rewrite is ONLY a wording fix (never one that changes meaning).`

const DEDUP_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_links','rejected_pairs','notes'], properties:{
    same_as_links:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, why:{type:'string'} }}, description:'reversible SAME_AS: exact same meaning only; canonical MUST be a coined driver_name'},
  rejected_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why_kept_separate'], properties:{ a:{type:'string'}, b:{type:'string'}, why_kept_separate:{type:'string'} }}, description:'looked similar but failed the exact-meaning rule -> NOT linked'},
  notes:{type:'array', items:{type:'string'}} } }

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{ driver_name:{type:'string'}, verdict:{type:'string', enum:['admit','rewrite','skip'], description:'admit | rewrite | skip'}, rewrite_to:{type:'string', description:'target name if verdict=rewrite (MUST be a coined driver_name), else ""'}, reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true, description:'admit/rewrite/skip totals'} } }

const REFUTE_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_verdicts','rewrite_verdicts'], properties:{
  same_as_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','survives','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, survives:{type:'boolean', description:'TRUE only if you CANNOT refute they are the EXACT same object AND scope AND mechanism; any doubt = FALSE'}, why:{type:'string'} }}},
  rewrite_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','rewrite_to','survives','why'], properties:{ driver_name:{type:'string'}, rewrite_to:{type:'string'}, survives:{type:'boolean', description:'TRUE only if the rewrite is provably WORDING-ONLY (identical meaning); any change of object/scope/mechanism = FALSE'}, why:{type:'string'} }}} } }

const WRITE_SCHEMA = { type:'object', additionalProperties:false, required:['file_written','catalog_count','same_as_count','rewrite_count','skip_count','unresolved_rewrite_count','summary'], properties:{
  file_written:{type:'string'}, catalog_count:{type:'integer'}, same_as_count:{type:'integer'}, rewrite_count:{type:'integer'}, skip_count:{type:'integer'}, unresolved_rewrite_count:{type:'integer'}, summary:{type:'string'} } }

phase('Review')
const [dedup, gate] = await parallel([
  () => agent(`Read ${ONT} (the rules) and ${SEED} — it is { catalog:[ {driver_name, canonical_name, companies, evidence_refs:[{company,source_type,source_id,date,quote}], optional_links} ], analysis }. The driver_names are already DISTINCT (one record each).
TASK = propose final reversible SAME_AS links over them. STRICT rules:
- ${EXACT_MEANING_RULE}
- ${EVIDENCE_RULE}
- NEVER link names with different scopes, brands, segments, geographies, objects, metrics, or mechanisms. List those under rejected_pairs with why.
- For each link pick the CANONICAL (shortest standard form, R6 — and it MUST be one of the COINED driver_names in the catalog, never an invented name) + the variant. Reversible only; never delete or merge nodes.
Return DEDUP_SCHEMA.`, {schema:DEDUP_SCHEMA, label:'dedup', phase:'Review'}),
  () => agent(`You are an INDEPENDENT admission gate — judge each name FRESH and skeptically; do NOT assume the producer that coined it was right. Read ${ONT} and the catalog[] records in ${SEED} (each = {driver_name, companies, evidence_refs}).
THE ONE TEST: is this a VALID, REUSABLE, consistently-nameable Driver? Give EACH driver_name ONE verdict:
- admit = a valid reusable cause that follows every rule. (Brand/segment-specific names ARE valid drivers — admit them.)
- rewrite = right driver, fixable WORDING-ONLY rule-break; give rewrite_to. It must NOT change the meaning AND must be a name some company already coined (an existing driver_name in the catalog). If no coined clean form exists, admit as-is or skip — do NOT invent a new name.
- skip = vague, rule-breaking, or tied to ONE specific event/date/quarter/headline (NOT a reusable class).
  Reusability is about the CLASS, not the count: a reusable event class (e.g. government_shutdown, food_safety_incident, goodwill_impairment, ceo_change) is ADMITTED even if it appears once; only a name bound to a single instance (e.g. q1_2026_shutdown_effect) is skipped.
${EXACT_MEANING_RULE}
${EVIDENCE_RULE}
Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; if it is a valid reusable driver, admit it. KEEP brand/segment-specific names. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, label:'gate', phase:'Review'}),
])

phase('Refute')
const refute = await agent(`You are an INDEPENDENT skeptic. Your ONLY job: BREAK fusions — decisions that fold two DIFFERENT drivers into one. Read ${SEED} — each driver_name is a catalog[] record with evidence_refs[{company, source_type, source_id, date, quote}]. For BOTH lists, default survives=FALSE; mark TRUE only if you genuinely cannot refute it.

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
const out = await agent(`Read ${SEED} — it is { industry, catalog:[ {driver_name, canonical_name, companies, evidence_refs, optional_links} ], analysis }. Each record's canonical_name currently equals its own driver_name. Decide each record's fate from the SKEPTIC-FILTERED lists below, assemble the FINAL catalog, and WRITE it (Write tool) to ${CAT}.

GATE verdicts (admit/skip only; rewrites are in the lists below, NOT here): ${JSON.stringify(gate.verdicts)}
APPROVED same_as (variant -> canonical): ${JSON.stringify(survivingLinks)}
APPROVED rewrites (from -> to): ${JSON.stringify(appliedRewrites)}
PARKED rewrites (refuted; set aside): ${JSON.stringify(parkedRewrites)}

For EACH seed record (driver_name X) apply this EXACT precedence (FIRST match wins):
1. X gate verdict = skip                          -> add {driver_name:X, why:<gate reason>} to skips[]; X is NOT a catalog record. (SKIP WINS over any same_as/rewrite — fail-close: never fold a skipped name.)
2. X is an APPROVED same_as .variant AND its canonical is a KEPT name (not skipped, not a parked rewrite) -> catalog record; canonical_name = that canonical.
3. X is an APPROVED rewrite .from AND its target is a KEPT name (not skipped, not a parked rewrite) -> catalog record; canonical_name = that target.
4. X is a PARKED rewrite .driver_name             -> add {driver_name:X, proposed_to, why} to unresolved_rewrites[]; X is NOT a catalog record.
5. otherwise (admit; or a same_as/rewrite whose target was skipped or parked) -> catalog record; canonical_name = X (itself).

For EVERY catalog record: COPY driver_name, companies, evidence_refs, optional_links VERBATIM from the seed record — change ONLY canonical_name. Never invent, drop, reorder, or edit an evidence_ref.
File shape = { industry:(copy from the seed's "industry" value), catalog:[ {driver_name, canonical_name, companies, evidence_refs, optional_links} ], skips:[{driver_name, why}], unresolved_rewrites:[{driver_name, proposed_to, why}], counts:{keep, same_as, rewrite, skip, unresolved} }.
Every canonical_name MUST be the driver_name of some catalog record whose canonical_name == itself (targets are coined names). NO kind field, NO route/scope bucket.
Return WRITE_SCHEMA (compact; do not echo the catalog).`, {schema:WRITE_SCHEMA, label:'write', phase:'Write'})

phase('Validate')
const validation = await agent(`Run this EXACT Bash command (it writes the validator output to validation.txt in the run dir AND reports the validator's real exit code):
${PY} ${DIR}/workflows/validate_catalog.py ${SEED} ${CAT} | tee ${RUN_DIR}/validation.txt ; echo "exit=\${PIPESTATUS[0]}"
This is a deterministic structure check (no judgment). If exit is NON-ZERO, begin your reply with "VALIDATION FAILED" and paste the exact failing checks + names. If exit is 0, begin with "VALIDATION PASSED". Do not fix anything; just report.`, {label:'validate', phase:'Validate'})

return { catalog: out, validation }
