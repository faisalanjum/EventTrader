export const meta = {
  name: 'driver-build-tree',
  description: 'Tree orchestrator (HierarchicalCatalogPlan §4/§6/§11.20). THREE modes via args: (1) { list: true } = READ-ONLY tree audit (join query; strict-tree fail-loud; audit/calibration only — never a production gate, does NOT fold). (2) { fold: { scope_name, scope_level: sector|global, children: [EXPLICIT run_ids] } } = Phase-1 single fold -> reconcile -> D8 validate, fail-closed. (3) { walk: { leaf_runs: {"<industry>": "<run_id>"}, taxonomy?: {"<sector>": ["<industry>", ...]}, require_complete?: bool } } = Phase-2 WALK-AND-FOLD: folds each sector from its industry leaf runs, then the global from the sector outputs; taxonomy omitted -> discovered from Neo4j (join query, exact raw strings); require_complete=true -> a tree industry without a leaf run HARD-FAILS (production); false (default, calibration) -> sectors with missing leaves are SKIPPED with a loud log. Over-size = deterministic HARD-FAIL in fold part-a / reconcile guard (sub-split batching lives in reconcile; part-a-side batching = future). No "latest", no meaning, every step fail-closed.',
  phases: [
    { title: 'Stamp', detail: 'UTC stamp + input checks (fail-close)' },
    { title: 'Tree',  detail: 'taxonomy override OR read-only join-query discovery + strict-tree checks' },
    { title: 'Folds', detail: 'per-level: fold_catalogs.js -> reconcile.js -> validate --fold (each gate hard-fails the run)' },
    { title: 'Measure', detail: 'OUTPUT-only run report (context sizes, collisions, verdicts) — batching never reads it' },
  ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})   // harness may stringify args

const LIST_PYTHON = `${PY} - <<'EOF'
import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('/home/faisal/EventMarketDB')/'.env', override=True)
from neo4j import GraphDatabase
drv = GraphDatabase.driver(os.getenv('NEO4J_URI','bolt://10.102.222.120:7687'), auth=(os.getenv('NEO4J_USERNAME','neo4j'), os.getenv('NEO4J_PASSWORD')))
tree, i2s, t2i, errs = {}, {}, {}, []
with drv.session() as s:
    for r in s.run('MATCH (c:Company) WHERE c.sector IS NOT NULL AND c.industry IS NOT NULL AND c.ticker IS NOT NULL RETURN c.sector AS s, c.industry AS i, c.ticker AS t'):
        sec, ind, tk = r['s'], r['i'], r['t']   # EXACT raw graph strings — never slugified (§11.20.8)
        if ind in i2s and i2s[ind] != sec: errs.append(f'MULTI-PARENT industry: {ind} -> {i2s[ind]} AND {sec}')
        if tk in t2i and t2i[tk] != ind: errs.append(f'MULTI-PARENT ticker: {tk} -> {t2i[tk]} AND {ind}')
        i2s[ind] = sec; t2i[tk] = ind
        tree.setdefault(sec, {}).setdefault(ind, []).append(tk)
drv.close()
taxonomy = {sec: sorted(tree[sec]) for sec in sorted(tree)}
print(json.dumps({'taxonomy': taxonomy, 'errors': errs, 'sectors': len(tree), 'industries': len(i2s)}, sort_keys=True))
EOF`

// ---------- READ-ONLY --list MODE (audit/calibration only; §11.20 keys 1-3, 7-8) ----------
if (A.list === true) {
  phase('Tree')
  const LIST_SCHEMA = { type:'object', additionalProperties:false, required:['ok','report'], properties:{ ok:{type:'boolean'}, report:{type:'string'} } }
  const out = await agent(`READ-ONLY Neo4j tree audit (never a production gate; prints for visibility only). Run with Bash:
${LIST_PYTHON}
If the printed errors list is NON-EMPTY, this is a STRICT-TREE failure — say so loudly. Return ok = (errors empty) and report = the counts + errors + the sector list with industry counts.`, {schema:LIST_SCHEMA, model:'opus', label:'tree-list', phase:'Tree'})
  if (!out.ok) throw new Error(`STRICT-TREE FAIL (multi-parent/orphan): ${out.report}`)
  log('Tree audit (read-only; not a gate): ' + out.report.slice(0, 600))
  return { mode: 'list', report: out.report }
}

// ---------- shared fold step: fold_catalogs.js -> reconcile.js -> validate --fold ----------
const FV_SCHEMA = { type:'object', additionalProperties:false, required:['passed','output'], properties:{ passed:{type:'boolean'}, output:{type:'string'} } }
async function runFold(scopeName, scopeLevel, children, utc) {
  const slug = scopeName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '')
  const parent = `${utc}_${scopeLevel}_${slug}`
  const ph = `Folds`
  log(`[${scopeLevel}:${scopeName}] folding ${children.length} children -> ${parent}`)
  const foldRes = await workflow({ scriptPath: `${DIR}/workflows/fold_catalogs.js` },
    { parent_run_id: parent, scope_name: scopeName, scope_level: scopeLevel, children })
  log(`[${scopeLevel}:${scopeName}] fold: passthrough=${foldRes.passthrough} collisions=${foldRes.collisions} verdicts=${JSON.stringify(foldRes.verdict_counts)}`)
  const recRes = await workflow({ scriptPath: `${DIR}/workflows/reconcile.js` }, { run_id: parent })
  const fv = await agent(`Run this EXACT Bash command (the D8 fold-level structure gate; writes fold_validation.txt and reports the REAL exit code):
${PY} ${DIR}/workflows/validate_catalog.py ${DIR}/runs/${parent}/seed.json ${DIR}/runs/${parent}/catalog.json ${DIR}/runs/${parent}/approved.json --fold ${children.map(c => `${DIR}/runs/${c}/catalog.json`).join(' ')} --review ${DIR}/runs/${parent}/same_name_review.json --sidecars ${DIR}/runs/${parent}/fold_sidecars.json | tee ${DIR}/runs/${parent}/fold_validation.txt ; echo "exit=\${PIPESTATUS[0]}"
Return passed = (exit==0) and output = the validator's verbatim output (trimmed to the failing checks if it failed). Do not fix anything. (validator rev3 — deep-variant legit set)`, {schema:FV_SCHEMA, model:'opus', label:`fold-validate:${slug}`, phase:ph})
  if (!fv.passed) throw new Error(`FOLD VALIDATION FAILED for ${parent}: ${fv.output.slice(0, 800)}`)
  return { parent, fold: foldRes, reconcile: recRes }
}

phase('Stamp')
const STAMP_SCHEMA = { type:'object', additionalProperties:false, required:['utc_stamp','checks_ok','notes'], properties:{
  utc_stamp:{type:'string'}, checks_ok:{type:'boolean'}, notes:{type:'string'} } }

// ---------- EXPLICIT FOLD MODE (Phase-1) ----------
if (A.fold) {
  const F = A.fold
  const CHILDREN = Array.isArray(F.children) ? F.children : []
  if (!F.scope_name || !['sector', 'global'].includes(F.scope_level) || CHILDREN.length < 2)
    throw new Error('fold mode requires { fold: { scope_name, scope_level: sector|global, children: [>=2 EXPLICIT run_ids] } }')
  const stamp = await agent(`Run with Bash, in order:
0) BILLING GUARD (subscription-only hard condition): test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; }
   If it prints BILLING-GUARD FAIL, STOP: return checks_ok=false and that exact line as notes.
1) date -u +%Y-%m-%d_%H%M%S
2) Confirm every child has catalog.json AND approved.json: ls ${CHILDREN.map(c => `${DIR}/runs/${c}/catalog.json ${DIR}/runs/${c}/approved.json`).join(' ')}
Return utc_stamp = the date output, checks_ok = true only if EVERY file exists (ls exit 0), notes = any missing paths verbatim.`, {schema:STAMP_SCHEMA, model:'opus', label:'stamp+check', phase:'Stamp'})
  if (!stamp.checks_ok) throw new Error(`child run dirs incomplete: ${stamp.notes}`)
  phase('Folds')
  const res = await runFold(F.scope_name, F.scope_level, CHILDREN, stamp.utc_stamp)
  return { mode: 'fold', parent_run_id: res.parent, children: CHILDREN, fold: res.fold, reconcile: res.reconcile, fold_validation: 'PASSED' }
}

// ---------- WALK-AND-FOLD MODE (Phase-2; §11.20) ----------
const W = A.walk
if (!W || typeof W.leaf_runs !== 'object' || !Object.keys(W.leaf_runs || {}).length)
  throw new Error('build_tree.js requires { list: true } | { fold: {...} } | { walk: { leaf_runs: {"<industry>": "<run_id>"}, taxonomy?, require_complete? } }')
const LEAF_RUNS = W.leaf_runs
const REQUIRE_COMPLETE = W.require_complete === true

const leafIds = Object.values(LEAF_RUNS)
const stamp = await agent(`Run with Bash, in order:
0) BILLING GUARD (subscription-only hard condition): test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; }
   If it prints BILLING-GUARD FAIL, STOP: return checks_ok=false and that exact line as notes.
1) date -u +%Y-%m-%d_%H%M%S
2) Confirm every leaf run has catalog.json AND approved.json: ls ${leafIds.map(c => `${DIR}/runs/${c}/catalog.json ${DIR}/runs/${c}/approved.json`).join(' ')}
Return utc_stamp = the date output, checks_ok = true only if EVERY file exists (ls exit 0), notes = any missing paths verbatim.`, {schema:STAMP_SCHEMA, model:'opus', label:'stamp+check', phase:'Stamp'})
if (!stamp.checks_ok) throw new Error(`leaf run dirs incomplete (need catalog.json + approved.json): ${stamp.notes}`)
const UTC = stamp.utc_stamp

phase('Tree')
let TAXONOMY = W.taxonomy || null   // calibration override: {"<sector>": ["<industry>", ...]}
if (!TAXONOMY) {
  const TREE_SCHEMA = { type:'object', additionalProperties:false, required:['ok','taxonomy','notes'], properties:{
    ok:{type:'boolean'}, taxonomy:{type:'object', additionalProperties:true, description:'sector -> [industry names] from the printed JSON'}, notes:{type:'string'} } }
  const disc = await agent(`READ-ONLY Neo4j taxonomy discovery (join query; exact raw strings; strict-tree fail-loud). Run with Bash:
${LIST_PYTHON}
Return ok = (errors list empty), taxonomy = the printed taxonomy object VERBATIM, notes = the errors if any.`, {schema:TREE_SCHEMA, model:'opus', label:'discover-tree', phase:'Tree'})
  if (!disc.ok) throw new Error(`STRICT-TREE FAIL: ${disc.notes}`)
  TAXONOMY = disc.taxonomy
}
// deterministic, byte-stable walk order (§11.20.1)
const SECTORS = Object.keys(TAXONOMY).sort()
const known = new Set()
for (const s of SECTORS) for (const ind of TAXONOMY[s]) known.add(ind)
const orphanLeaves = Object.keys(LEAF_RUNS).filter(ind => !known.has(ind))
if (orphanLeaves.length) throw new Error(`leaf_runs industries not in the taxonomy: ${orphanLeaves.join(', ')} (exact raw strings required — §11.20.8)`)

phase('Folds')
const sectorOutputs = []   // run_ids feeding the global fold
const report = { utc: UTC, sectors: [], skipped_sectors: [], global: null }
for (const sec of SECTORS) {
  const inds = [...TAXONOMY[sec]].sort()
  const have = inds.filter(i => LEAF_RUNS[i])
  const missing = inds.filter(i => !LEAF_RUNS[i])
  if (missing.length && REQUIRE_COMPLETE) throw new Error(`sector "${sec}" missing leaf runs for: ${missing.join(', ')} (require_complete=true)`)
  if (!have.length) { report.skipped_sectors.push({ sector: sec, reason: 'no leaf runs' }); continue }
  if (missing.length) log(`[walk] sector "${sec}": folding ${have.length}/${inds.length} industries (missing: ${missing.join(', ')}) — calibration mode`)
  if (have.length === 1) {
    // degenerate 1-child level: pass the leaf through as the sector output (no fold of one; logged, §11.20.7-adjacent)
    log(`[walk] sector "${sec}": single leaf "${have[0]}" passes through (no 1-child fold)`)
    sectorOutputs.push(LEAF_RUNS[have[0]])
    report.sectors.push({ sector: sec, passthrough_leaf: LEAF_RUNS[have[0]] })
    continue
  }
  const res = await runFold(sec, 'sector', have.map(i => LEAF_RUNS[i]), UTC)
  sectorOutputs.push(res.parent)
  report.sectors.push({ sector: sec, parent: res.parent, collisions: res.fold.collisions, verdicts: res.fold.verdict_counts })
}
if (!sectorOutputs.length) throw new Error('walk produced zero sector outputs — nothing to fold globally')
let globalParent = null
if (sectorOutputs.length === 1) {
  log(`[walk] single sector output — it IS the global result (degenerate collapse, §11.20.6)`)
  globalParent = sectorOutputs[0]
  report.global = { passthrough: globalParent }
} else {
  const res = await runFold('GLOBAL', 'global', sectorOutputs, UTC)
  globalParent = res.parent
  report.global = { parent: res.parent, collisions: res.fold.collisions, verdicts: res.fold.verdict_counts }
}

phase('Measure')
// OUTPUT only (§6 Phase 2.3): sizes + a deterministic token-overlap duplicate-rate sample, graded ONCE.
const MEASURE_SCHEMA = { type:'object', additionalProperties:false, required:['ok','summary'], properties:{ ok:{type:'boolean'}, summary:{type:'string'} } }
const meas = await agent(`Two steps with Bash (OUTPUT-only measurement; nothing reads this downstream):
1) ${PY} -c "import json;d=json.load(open('${DIR}/runs/${globalParent}/catalog.json'));recs=d.get('catalog') or [];names=[r['driver_name'] for r in recs];import itertools;tok=lambda n:set(n.split('_'));pairs=[(a,b) for a,b in itertools.combinations(sorted(names),2) if len(tok(a)&tok(b))>=2 and a!=b][:10];print(json.dumps({'records':len(recs),'sample_pairs':pairs}))"
2) For the printed sample_pairs (possible missed duplicates — token overlap is only a SUGGESTION), judge each pair ONCE: same exact driver (object+scope+mechanism) or different? Count how many look like REAL missed duplicates.
3) Use the Write tool to save {"records": N, "sample_pairs": [...], "judged_missed_duplicates": M, "notes": "..."} to ${DIR}/runs/${globalParent}/walk_measure.json
Return ok=true and summary = one line with records + sampled + judged-missed counts.`, {schema:MEASURE_SCHEMA, model:'opus', label:'measure', phase:'Measure'})
log(`measure: ${meas.summary}`)

return { mode: 'walk', utc: UTC, global_run_id: globalParent, report }
