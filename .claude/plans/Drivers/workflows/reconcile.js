export const meta = {
  name: 'driver-reconcile-restaurants',
  description: 'Step 2 reconcile over the Restaurants seed menu: (Dedup) canonical + reversible SAME_AS for EXACT-same-meaning only — never brand→generic; (Gate) independent admit/rewrite/scope-route/skip per DriverOntology. Review-file only; no graph writes; no merges/deletes.',
  phases: [ { title: 'Review', detail: 'dedup proposer + independent gate, in parallel' }, { title: 'Write', detail: 'merge into the clean catalog review file' } ],
}

const SEED = '/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_seed.json'
const ONT  = '/home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology.md'

const DEDUP_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_links','rejected_pairs','notes'], properties:{
  same_as_links:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, why:{type:'string'} }}, description:'reversible SAME_AS: exact same meaning AND scope only'},
  rejected_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why_kept_separate'], properties:{ a:{type:'string'}, b:{type:'string'}, why_kept_separate:{type:'string'} }}, description:'looked similar but different scope (e.g. brand vs company-wide) -> NOT linked'},
  notes:{type:'array', items:{type:'string'}} } }

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{ driver_name:{type:'string'}, verdict:{type:'string', description:'admit | rewrite | scope_route | skip'}, rewrite_to:{type:'string', description:'target name if verdict=rewrite, else ""'}, reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true, description:'admit/rewrite/scope_route/skip totals'} } }

const WRITE_SCHEMA = { type:'object', additionalProperties:false, required:['file_written','final_catalog_count','same_as_count','rewrite_count','skip_count','scope_route_count','summary'], properties:{
  file_written:{type:'string'}, final_catalog_count:{type:'integer'}, same_as_count:{type:'integer'}, rewrite_count:{type:'integer'}, skip_count:{type:'integer'}, scope_route_count:{type:'integer'}, summary:{type:'string'} } }

phase('Review')
const [dedup, gate] = await parallel([
  () => agent(`Read ${ONT} (the rules) and ${SEED} (keys: menus[].candidates[].driver_name, plus analysis.exact_dup_pairs which are PROPOSALS to validate). Collect the DISTINCT driver_names.
TASK = propose final reversible SAME_AS links over them. STRICT rules:
- SAME_AS ONLY when EXACT same meaning AND same scope (true synonym / spelling / word-order / acronym): e.g. systemwide_sales=system_wide_sales, average_ticket=average_check, unit_count=restaurant_unit_count, average_restaurant_sales=average_unit_volume.
- NEVER SAME_AS a brand/segment metric to its company-wide form (taco_bell_same_store_sales ≠ same_store_sales) and NEVER link two different brands/segments/geographies — those are SEPARATE drivers; keep both. List those under rejected_pairs with why.
- For each link pick the CANONICAL (shortest standard form, R6) + the variant. Reversible only; never delete or merge nodes.
Return DEDUP_SCHEMA.`, {schema:DEDUP_SCHEMA, label:'dedup', phase:'Review'}),
  () => agent(`You are an INDEPENDENT admission gate — judge each name FRESH and skeptically; do NOT assume the producer that coined it was right. Read ${ONT} and collect the DISTINCT driver_names from ${SEED} (menus[].candidates[].driver_name).
For EACH distinct name give ONE verdict per DriverOntology:
- admit = clean reusable cause, follows every rule.
- rewrite = a fixable rule-break; give rewrite_to. (e.g. ceo_transition→management_change; restaurant_openings / restaurant_closure / unit_growth → net_new_units; *_unit_growth → *_unit_count; debt_refinancing → debt_financing.)
- scope_route = market reaction/flow/macro, not a Phase-1 fundamental (news already excluded, so expect ~0).
- skip = one-off tied to a single event/quarter (R10), too vague, or not a reusable driver.
KEEP brand/segment-specific names (R9 allows them; they are NOT violations). Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, label:'gate', phase:'Review'}),
])

phase('Write')
const out = await agent(`Read ${SEED}. Merge the two independent reviews below into the final clean Restaurants catalog and WRITE it (Write tool) to /home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_catalog.json.
SAME_AS proposals: ${JSON.stringify(dedup).slice(0,40000)}
Gate verdicts: ${JSON.stringify(gate).slice(0,40000)}
Catalog file shape = { industry:'Restaurants', final_drivers:[{driver_name, n_companies, kind:'core|brand|segment'}], same_as:[{canonical,variant}], rewrites:[{from,to}], skips:[{driver_name,why}], scope_routes:[{driver_name,lane}], counts:{...} }.
final_drivers = admitted names + rewrite TARGETS (dedup variants and skips removed). Return WRITE_SCHEMA (compact; do not echo the whole catalog).`, {schema:WRITE_SCHEMA, label:'write', phase:'Write'})

return out
