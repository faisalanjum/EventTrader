export const meta = {
  name: 'driver-fold',
  description: 'Fold N child Driver catalogs into a parent SEED (HierarchicalCatalogPlan §2b/D5): deterministic combine (fold_catalogs.py part-a) → same-name review queue → AI review (SAME/DIFFERENT/UNCLEAR, evidence views via the §12.8 draw) → Refute on every SAME union (+ §11.18 perspective-forced 2nd Refute on high-blast fusions, AND-vote) → same_name_review.json → deterministic part-b writes the parent seed + fold_sidecars.json. Args = { parent_run_id, scope_name, scope_level: "sector"|"global", children: [child run_ids under runs/] }. The parent reconcile + fold validation run AFTERWARDS (build_tree.js).',
  phases: [
    { title: 'PartA',  detail: 'deterministic collapse + cross-child grouping + collision queue + SEED_MAX guard (code)' },
    { title: 'Draw',   detail: '§12.8 deterministic evidence views for every collision (code)' },
    { title: 'Review', detail: 'one AI reviewer per collision: SAME / DIFFERENT(+assignments) / UNCLEAR' },
    { title: 'Refute', detail: 'independent skeptic per SAME union; high-blast gets a 2nd perspective-forced Refute (AND)' },
    { title: 'PartB',  detail: 'same_name_review.json → deterministic seed assembly + fold_sidecars.json (code)' },
  ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})   // harness may stringify args
const PARENT = A.parent_run_id || ''
const SCOPE_NAME = A.scope_name || ''
const SCOPE_LEVEL = A.scope_level || ''
const CHILDREN = Array.isArray(A.children) ? A.children : []
if (!PARENT || !SCOPE_NAME || !['sector', 'global'].includes(SCOPE_LEVEL) || CHILDREN.length < 2)
  throw new Error('fold_catalogs.js requires args = { parent_run_id, scope_name, scope_level: sector|global, children: [>=2 child run_ids] }')
const PDIR = `${DIR}/runs/${PARENT}`
const CDIRS = CHILDREN.map(c => `${DIR}/runs/${c}`)

const EXACT_MEANING_RULE = `For any proposed union (treating two same-named drivers as ONE), verify all three are true:
1. same object or metric   2. same scope   3. same mechanism
If any one is false or unclear, they are NOT the same driver.`

const PARTA_SCHEMA = { type:'object', additionalProperties:false, required:['ok','passthrough','collisions','collision_names','collision_meta','notes'], properties:{
  ok:{type:'boolean'}, passthrough:{type:'integer'}, collisions:{type:'integer'},
  collision_names:{type:'array', items:{type:'string'}},
  collision_meta:{type:'object', additionalProperties:true, description:'name -> {n_companies, n_children} from the part-a summary'},
  notes:{type:'string'} } }

const DRAW_SCHEMA = { type:'object', additionalProperties:false, required:['ok','items','notes'], properties:{
  ok:{type:'boolean'}, items:{type:'integer'}, notes:{type:'string'} } }

const REVIEW_SCHEMA = { type:'object', additionalProperties:false, required:['collision_name','verdict','new_names','assignments','why'], properties:{
  collision_name:{type:'string'},
  verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']},
  new_names:{type:'array', items:{type:'string'}, description:'DIFFERENT only: more-specific lower_snake names drawn ONLY from the existing evidence; else []'},
  assignments:{type:'array', items:{type:'object', additionalProperties:false, required:['child_run_id','to'], properties:{ child_run_id:{type:'string'}, to:{type:'string'} }}, description:'DIFFERENT only: which child occurrence goes to which new name (every occurrence exactly once); else []'},
  why:{type:'string'} } }

const REFUTE1_SCHEMA = { type:'object', additionalProperties:false, required:['survives','why'], properties:{
  survives:{type:'boolean', description:'TRUE only if you CANNOT refute that all occurrences are the EXACT same object AND scope AND mechanism; any doubt = FALSE'}, why:{type:'string'} } }

const REFUTE2_SCHEMA = { type:'object', additionalProperties:false, required:['object','scope','mechanism','survives'], properties:{
  object:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  scope:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  mechanism:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  survives:{type:'boolean', description:'must equal object.pass AND scope.pass AND mechanism.pass'} } }

const PARTB_SCHEMA = { type:'object', additionalProperties:false, required:['ok','sha_line'], properties:{ ok:{type:'boolean'}, sha_line:{type:'string'} } }

const pyView = (name, view) => `${PY} -c "import json;d=json.load(open('${PDIR}/fold_queue_views.json'));items=d['items'] if isinstance(d,dict) and 'items' in d else d;it=next(i for i in items if i['name']==${JSON.stringify(JSON.stringify(name)).slice(1,-1)});print(json.dumps({'name':it['name'],'sides':[{'side_key':s['side_key'],'refs':s['${view}'],'total_refs':s.get('total_refs')} for s in it['sides']]}))"`

phase('PartA')
const partA = await agent(`Run this EXACT command with Bash (step 0 = the BILLING GUARD, a subscription-only hard condition; then the deterministic combine — collapses each child's SAME_AS clusters, groups across children, queues identical-name collisions; HARD-FAILS on SEED_MAX):
test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; } && ${PY} ${DIR}/workflows/fold_catalogs.py part-a ${PDIR} --scope-name ${JSON.stringify(SCOPE_NAME)} --scope-level ${SCOPE_LEVEL} --children ${CDIRS.join(' ')}
Return ok=true + passthrough/collisions/collision_names/collision_meta from the printed one-line JSON summary (collision_meta = the name -> {n_companies, n_children} object), notes="". If it exits NON-ZERO: ok=false, zeros/empties, notes = the exact error output.`, {schema:PARTA_SCHEMA, model:'opus', label:'part-a', phase:'PartA'})
if (!partA.ok) throw new Error(`fold part-a failed: ${partA.notes}`)

let reviews = [], splitMap = []
if (partA.collisions > 0) {
  phase('Draw')
  const draw = await agent(`Run this EXACT command with Bash (deterministic §12.8 evidence views for the same-name review):
${PY} ${DIR}/workflows/fold_catalogs.py draw ${PDIR}
Return ok=true + items from its printed summary, notes="". Non-zero exit: ok=false, items=0, notes = exact error.`, {schema:DRAW_SCHEMA, model:'opus', label:'draw', phase:'Draw'})
  if (!draw.ok) throw new Error(`fold draw failed: ${draw.notes}`)

  phase('Review')
  const verdicts = (await parallel(partA.collision_names.map(nm => () => agent(`You are the SAME-NAME REVIEW (HierarchicalCatalogPlan D5). The identical driver_name "${nm}" was coined independently in ${ (partA.collision_meta[nm]||{}).n_children || 'several' } child catalogs. Identical spelling is NOT proof of identical meaning — judge from the EVIDENCE only.
Read ${DIR}/DriverOntology.md (naming rules). LOAD YOUR EVIDENCE VIEW: run Bash:
${pyView(nm, 'view1')}
(sides are listed smallest-first; each side = one child catalog's occurrence with up to 20 representative refs; full evidence stays stored.)
${EXACT_MEANING_RULE}
ONE verdict:
- SAME = every occurrence names the EXACT same reusable cause (object + scope + mechanism all match). (An independent skeptic will still try to break this.)
- DIFFERENT = a true homonym: the occurrences name different causes. Then coin MORE-SPECIFIC lower_snake_case names drawn ONLY from words in the evidence (per DriverOntology — no invented nouns, no company tickers), one per distinct meaning, and assign EVERY child occurrence (by child_run_id, exactly once) to one new name.
- UNCLEAR = evidence is too thin/mixed to decide → park (fail-close; never guess).
Return REVIEW_SCHEMA (collision_name="${nm}").`, {schema:REVIEW_SCHEMA, model:'opus', label:`review:${nm}`, phase:'Review'}))) ).filter(Boolean)
  if (verdicts.length !== partA.collision_names.length) throw new Error(`same-name review lost ${partA.collision_names.length - verdicts.length} verdict(s) — fail-close.`)

  phase('Refute')
  const sameOnes = verdicts.filter(v => v.verdict === 'SAME')
  const refuted = new Set()
  if (sameOnes.length) {
    const r1s = await parallel(sameOnes.map(v => () => agent(`You are an INDEPENDENT skeptic. A reviewer says the same-named driver "${v.collision_name}" from multiple child catalogs is ONE driver (a UNION = a fusion). Your ONLY job: try to BREAK it. Default survives=FALSE.
LOAD THE EVIDENCE VIEW: run Bash:
${pyView(v.collision_name, 'view1')}
${EXACT_MEANING_RULE}
survives=TRUE only if, reading the quotes across ALL sides, you genuinely cannot refute that they are the EXACT same object AND scope AND mechanism. Different brand/segment vs company-wide, different metric/geography/mechanism, or mixed evidence -> FALSE. Return REFUTE1_SCHEMA.`, {schema:REFUTE1_SCHEMA, model:'opus', label:`refute:${v.collision_name}`, phase:'Refute'}).then(r => ({name:v.collision_name, r}))))
    for (const x of (r1s.filter(Boolean))) if (!(x.r && x.r.survives === true)) refuted.add(x.name)
    // §11.18 high-blast: >=8 companies OR (global fold AND >=2 children) -> 2nd perspective-forced Refute, AND-vote, view2
    const highBlast = sameOnes.filter(v => !refuted.has(v.collision_name)).filter(v => { const m = partA.collision_meta[v.collision_name] || {}; return (m.n_companies || 0) >= 8 || (SCOPE_LEVEL === 'global' && (m.n_children || 0) >= 2) })
    if (highBlast.length) {
      const r2s = await parallel(highBlast.map(v => () => agent(`You are a SECOND, independent skeptic on a HIGH-BLAST fusion (it spans many companies — a wrong merge here becomes a false cross-company trading signal). The union under test: same-named driver "${v.collision_name}" across child catalogs.
LOAD YOUR EVIDENCE VIEW (a DIFFERENT, disjoint view from the first skeptic's): run Bash:
${pyView(v.collision_name, 'view2')}
(If view2 refs are empty for a side, that side had <21 refs — judge from what is shown plus the side metadata.)
You MUST separately judge each of the three lenses, each backed by a QUOTE from the view:
- object: do ALL sides name the same object/metric?  - scope: the same scope (brand/segment vs company-wide, geography)?  - mechanism: the same causal mechanism?
survives MUST equal object.pass AND scope.pass AND mechanism.pass. Any FALSE or missing -> the union dies (fail-close). Return REFUTE2_SCHEMA.`, {schema:REFUTE2_SCHEMA, model:'opus', label:`refute2:${v.collision_name}`, phase:'Refute'}).then(r => ({name:v.collision_name, r}))))
      for (const x of (r2s.filter(Boolean))) { const ok = x.r && x.r.survives === true && x.r.object && x.r.object.pass === true && x.r.scope && x.r.scope.pass === true && x.r.mechanism && x.r.mechanism.pass === true; if (!ok) refuted.add(x.name) }
      const r2names = new Set(r2s.filter(Boolean).map(x => x.name)); for (const v of highBlast) if (!r2names.has(v.collision_name)) refuted.add(v.collision_name)  // missing verdict = refuted
    }
    const r1names = new Set(r1s.filter(Boolean).map(x => x.name)); for (const v of sameOnes) if (!r1names.has(v.collision_name)) refuted.add(v.collision_name)
  }
  // assemble the review file content: refuted SAME -> UNCLEAR (fail-close)
  reviews = verdicts.map(v => {
    if (v.verdict === 'SAME') {
      if (refuted.has(v.collision_name)) return { collision_name: v.collision_name, verdict: 'UNCLEAR', why: `SAME union refuted by skeptic (fail-close): ${v.why}` }
      return { collision_name: v.collision_name, verdict: 'SAME', why: v.why, refute_survived: true }
    }
    if (v.verdict === 'DIFFERENT') return { collision_name: v.collision_name, verdict: 'DIFFERENT', new_names: v.new_names, why: v.why }
    return { collision_name: v.collision_name, verdict: 'UNCLEAR', why: v.why }
  })
  splitMap = verdicts.filter(v => v.verdict === 'DIFFERENT').map(v => ({ from: v.collision_name, to: v.new_names, assignments: v.assignments }))
}

phase('PartB')
const reviewFile = { reviews, split_map: splitMap }
const partB = await agent(`Two steps, EXACT, in order:
1) Use the Write tool to save this EXACT JSON (byte-for-byte) to ${PDIR}/same_name_review.json:
${JSON.stringify(reviewFile)}
2) Run with Bash: ${PY} ${DIR}/workflows/fold_catalogs.py part-b ${PDIR} --review ${PDIR}/same_name_review.json
   (deterministic code: applies the review, writes the parent seed.json + fold_sidecars.json, prints a one-line JSON summary)
Return ok=true + sha_line = the exact printed summary line. Non-zero exit: ok=false, sha_line = the exact error. Do NOT compose any seed content yourself.`, {schema:PARTB_SCHEMA, model:'opus', label:'part-b', phase:'PartB'})
if (!partB.ok) throw new Error(`fold part-b failed: ${partB.sha_line}`)

return { parent_run_id: PARENT, scope_name: SCOPE_NAME, scope_level: SCOPE_LEVEL, children: CHILDREN,
  passthrough: partA.passthrough, collisions: partA.collisions,
  verdict_counts: { SAME: reviews.filter(r => r.verdict === 'SAME').length, DIFFERENT: reviews.filter(r => r.verdict === 'DIFFERENT').length, UNCLEAR: reviews.filter(r => r.verdict === 'UNCLEAR').length },
  partB: partB.sha_line }
