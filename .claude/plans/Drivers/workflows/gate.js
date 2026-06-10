export const meta = {
  name: 'driver-gate-g2',
  description: 'G2 — INDEPENDENT admission gate (reusable). One test per candidate driver_name: is it a VALID, REUSABLE driver? Verdict = reuse / admit / rewrite / skip, per DriverOntology, fail-closed (never delete/merge; err specific). No route bucket; no fundamental/news split (a producer concern, not a catalog one). Reusable in BATCH reconcile AND LIVE production (per new name, against the live catalog). Pass evidence-bearing candidates + catalog via args; defaults to the Restaurants seed.',
  phases: [ { title: 'Gate' } ],
}

const ONT  = '/home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology.md'
// args = { candidates: [{driver_name, evidence_refs:[{company,source_type,source_id,date,quote}]}], catalog: [..already-admitted names, for the reuse check..] }
const cands   = (args && args.candidates) || null
const catalog = (args && args.catalog) || []
if (!cands || !cands.length) throw new Error('gate.js requires args.candidates (the stale _menu_restaurants_seed.json default was removed — the file no longer exists).')

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{
    driver_name:{type:'string'},
    verdict:{type:'string', enum:['reuse','admit','rewrite','skip'], description:'reuse | admit | rewrite | skip'},
    reuse_name:{type:'string', description:'existing catalog name to reuse, if verdict=reuse, else ""'},
    rewrite_to:{type:'string', description:'fixed name if verdict=rewrite (WORDING-ONLY), else ""'},
    reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true} } }

phase('Gate')
const candsClause = `Judge exactly these candidates — EACH carries its evidence_refs[{company,source_type,source_id,date,quote}]; judge from the evidence, NOT the bare name: ${JSON.stringify(cands)}.`
const catClause = catalog.length
  ? `EXISTING CATALOG (verdict=reuse if a candidate is the EXACT same cause as one of these): ${JSON.stringify(catalog)}.`
  : `(No prior catalog supplied — verdict=reuse only if two candidates are exact-same.)`

const res = await agent(`You are an INDEPENDENT admission gate — judge each candidate driver_name FRESH and skeptically; do NOT assume whoever coined it was right. Read ${ONT} (the rules).
${candsClause}
${catClause}
THE ONE TEST: is this a VALID, REUSABLE, consistently-nameable Driver? Judge from the EVIDENCE (each name's evidence_refs), not the bare name string. For EACH name give ONE verdict:
- reuse = EXACT same cause AND scope as an existing catalog name (put it in reuse_name). A brand/segment metric is NOT the same as its company-wide form — do NOT call that reuse.
- admit = a valid reusable cause that follows every rule. (Brand/segment-specific names ARE valid drivers — admit them.)
- rewrite = right driver, fixable WORDING-ONLY rule-break; give rewrite_to (must NOT change the meaning).
- skip = vague, rule-breaking, or tied to ONE specific event/date/quarter/headline (NOT a reusable class). Reusability is about the CLASS not the count: a reusable event class (e.g. government_shutdown, food_safety_incident, goodwill_impairment) is ADMITTED even if seen once; only a name bound to a single instance is skipped.
For any reuse or rewrite, first verify same object + same scope + same mechanism; if any is false or unclear, do NOT reuse/rewrite — keep separate / admit separately / skip. If a name's evidence is missing, vague, or MIXED (different meanings across companies), do not admit/reuse blindly — prefer keep-separate/skip; rewrite only if it is a pure wording fix.
Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; a valid reusable driver is admitted. Fail-closed: never delete or merge; err specific. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, label:'g2-gate', phase:'Gate'})
return res
