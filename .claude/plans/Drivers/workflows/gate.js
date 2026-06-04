export const meta = {
  name: 'driver-gate-g2',
  description: 'G2 — INDEPENDENT admission gate (reusable). Rules each candidate driver_name: reuse / admit / rewrite / scope-route / skip, per DriverOntology, fail-closed (never delete/merge; err specific). Reusable in BATCH reconcile AND LIVE production (per new name). Pass names+catalog via args; defaults to the Restaurants seed. IMPROVE: swap in a different model for true independence; add async/provisional-admit for live latency.',
  phases: [ { title: 'Gate' } ],
}

const ONT = '/home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology.md'
// args = { names: [..candidate driver_names..], catalog: [..already-admitted names, for the reuse check..] }
const names   = (args && args.names) || null
const catalog = (args && args.catalog) || []

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{
    driver_name:{type:'string'},
    verdict:{type:'string', description:'reuse | admit | rewrite | scope_route | skip'},
    reuse_name:{type:'string', description:'existing catalog name to reuse, if verdict=reuse, else ""'},
    rewrite_to:{type:'string', description:'fixed name if verdict=rewrite, else ""'},
    lane:{type:'string', description:'target lane if verdict=scope_route (e.g. news/trading), else ""'},
    reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true} } }

phase('Gate')
const namesClause = names
  ? `Judge exactly these candidate names: ${JSON.stringify(names)}.`
  : `No names passed via args — read /home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_seed.json and collect the distinct menus[].candidates[].driver_name.`
const catClause = catalog.length
  ? `EXISTING CATALOG (verdict=reuse if a candidate is the EXACT same cause as one of these): ${JSON.stringify(catalog)}.`
  : `(No prior catalog supplied — verdict=reuse only if two candidates are exact-same.)`

const res = await agent(`You are an INDEPENDENT admission gate — judge each candidate driver_name FRESH and skeptically; do NOT assume whoever coined it was right. Read ${ONT} (the rules).
${namesClause}
${catClause}
For EACH name give ONE verdict per DriverOntology:
- reuse = EXACT same cause AND scope as an existing catalog name (name it in reuse_name). Brand/segment ≠ company-wide form — do NOT call that reuse.
- admit = clean, reusable, new cause; follows every rule.
- rewrite = fixable rule-break; give rewrite_to (e.g. ceo_transition→management_change; restaurant_openings/unit_growth→net_new_units; debt_refinancing→debt_financing).
- scope_route = market reaction / flow / macro, not a Phase-1 fundamental; give the lane (e.g. news/trading).
- skip = one-off tied to a single event/quarter (R10), vague, or not a reusable driver.
Fail-closed: never delete or merge; keep brand/segment-specific names (R9 allows them); err specific. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, label:'g2-gate', phase:'Gate'})
return res
