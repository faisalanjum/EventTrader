export const meta = {
  name: 'driver-repair-duplicates',
  description: 'Required duplicate-repair pass (§13.2): code suggests possible missed SAME_AS pairs, AI judges exact meaning, code applies approved links through assemble_catalog.py, then validate_catalog.py checks structure. Embeddings/token overlap suggest only; AI decides meaning; code writes links.',
  phases: [
    { title: 'Suggest', detail: 'repair_duplicates.py suggest writes repair_candidates.json (code; no meaning)' },
    { title: 'Review', detail: 'AI judges each candidate SAME/DIFFERENT/UNCLEAR from evidence; high-blast SAME gets 2nd Refute' },
    { title: 'Apply', detail: 'repair_duplicates.py apply appends approved SAME_AS and reassembles catalog/approved (code)' },
    { title: 'Validate', detail: 'validate_catalog.py hard-fails broken structure' },
  ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
const RUN_ID = A.run_id || ''
const LIMIT = Number.isInteger(A.limit) ? A.limit : 200
const USE_EMBEDDINGS = A.use_embeddings !== false
if (!RUN_ID) throw new Error('repair_duplicates.js requires args = { run_id, limit? }')
const RUN_DIR = `${DIR}/runs/${RUN_ID}`

const EXACT_MEANING_RULE = `Approve SAME only if all three are true:
1. same object or metric
2. same scope
3. same mechanism
If any one is false or unclear, verdict is DIFFERENT or UNCLEAR.`

const SUGGEST_SCHEMA = { type:'object', additionalProperties:false, required:['count','candidates'], properties:{
  count:{type:'integer'}, clipped:{type:'integer', description:'pairs dropped by --limit (0 = none)'}, candidates:{type:'array', items:{type:'object', additionalProperties:true}} } }
const REVIEW_SCHEMA = { type:'object', additionalProperties:false, required:['a','b','verdict','why'], properties:{
  a:{type:'string'}, b:{type:'string'}, verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']}, why:{type:'string'} } }
const REFUTE2_SCHEMA = { type:'object', additionalProperties:false, required:['object','scope','mechanism','survives'], properties:{
  object:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  scope:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  mechanism:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  survives:{type:'boolean'} } }
const APPLY_SCHEMA = { type:'object', additionalProperties:false, required:['ok','summary'], properties:{ ok:{type:'boolean'}, summary:{type:'string'} } }
const VAL_SCHEMA = { type:'object', additionalProperties:false, required:['passed','output'], properties:{ passed:{type:'boolean'}, output:{type:'string'} } }

phase('Suggest')
const suggested = await agent(`Run with Bash:
test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; } && ${PY} ${DIR}/workflows/repair_duplicates.py suggest ${RUN_DIR} --limit ${LIMIT}${USE_EMBEDDINGS ? ' --use-embeddings' : ''}
Return the printed JSON exactly as SUGGEST_SCHEMA.`, {schema:SUGGEST_SCHEMA, model:'opus', label:'repair-suggest', phase:'Suggest'})
if (!suggested) throw new Error('repair suggest agent died — fail-close.')
if ((suggested.clipped | 0) > 0) log(`repair-suggest: limit dropped ${suggested.clipped} candidate pair(s) — raise --limit to sweep them in a later pass (NO silent caps)`)
if (!suggested.count) return { run_id: RUN_ID, candidates: 0, approved: 0, validation: 'SKIPPED no candidates' }

phase('Review')
const norm = s => (s||'').trim().toLowerCase()
const h32 = s => { let h = 0; for (let i = 0; i < s.length; i++) h = ((Math.imul(h, 31) + s.charCodeAt(i)) >>> 0); return h }
const clean = s => (s || '').replace(/[\u0000-\u001f]/g, ' ')   // audit-text cleanup: control chars in judge NOTES -> spaces at file-build time (post-judgment; never names/verdicts)
const reviews = (await parallel((suggested.candidates || []).map(c => () => agent(`You are the duplicate-repair judge. A deterministic suggester found a possible missed duplicate pair. Embeddings/token overlap only suggested it; YOU decide exact meaning from evidence.
Candidate JSON:
${JSON.stringify(c)}
${EXACT_MEANING_RULE}
Return REVIEW_SCHEMA. Copy a and b EXACTLY as given in the candidate (the same two strings). SAME means add reversible SAME_AS. DIFFERENT/UNCLEAR means keep separate.`, {schema:REVIEW_SCHEMA, model:'opus', label:`repair:${c.a}:${c.b}`, phase:'Review'}).then(v => ({candidate:c, verdict:v}))))).filter(Boolean)
if (reviews.length !== suggested.candidates.length) throw new Error(`repair review lost ${suggested.candidates.length - reviews.length} verdict(s) — fail-close.`)
// Stage-0 #7: a verdict must name the pair it was ASSIGNED — a transposed verdict would
// link two real records the judgment never covered (no other code path catches it).
for (const row of reviews) {
  if (norm(row.verdict.a) !== norm(row.candidate.a) || norm(row.verdict.b) !== norm(row.candidate.b))
    throw new Error(`repair review pair mismatch: judged "${row.verdict.a}|${row.verdict.b}" but assigned "${row.candidate.a}|${row.candidate.b}" — fail-close.`)
}

for (const row of reviews) {
  const c = row.candidate
  const v = row.verdict
  if (v.verdict === 'SAME' && (c.n_companies || 0) >= 8) {
    const r2 = await agent(`SECOND independent skeptic for a HIGH-BLAST duplicate repair SAME_AS. This pair spans ${c.n_companies} companies. A wrong link becomes a false cross-company read-through.
Candidate JSON:
${JSON.stringify(c)}
Judge each lens separately with quote support: same object, same scope, same mechanism. survives=true only if all three pass. Default false.`, {schema:REFUTE2_SCHEMA, model:'opus', label:`repair-refute2:${c.a}:${c.b}`, phase:'Review'})
    const ok = r2 && r2.survives === true && r2.object && r2.object.pass === true && r2.scope && r2.scope.pass === true && r2.mechanism && r2.mechanism.pass === true
    if (ok) v.high_blast_refute2_survived = true
    else v.verdict = 'UNCLEAR'
  }
}

phase('Apply')
const reviewFile = { reviews: reviews.map(r => ({ ...r.verdict, why: clean(r.verdict.why) })) }
// Stage-0 #5: bind the agent-written review file to THIS source string (count + h32).
const reviewJson = JSON.stringify(reviewFile)
const applied = await agent(`Use the Write tool to save this exact JSON (byte-for-byte) to ${RUN_DIR}/repair_review.json:
${reviewJson}
Then run with Bash:
${PY} ${DIR}/workflows/repair_duplicates.py apply ${RUN_DIR} --review ${RUN_DIR}/repair_review.json --expect 'rv=${reviewFile.reviews.length},h32=${h32(reviewJson)}'
Return ok=true and summary = the printed JSON. If the command exits non-zero, ok=false and summary = exact error.`, {schema:APPLY_SCHEMA, model:'opus', label:'repair-apply', phase:'Apply'})
if (!applied || !applied.ok) throw new Error(`repair apply failed: ${applied && applied.summary}`)

phase('Validate')
const val = await agent(`Run with Bash:
${PY} ${DIR}/workflows/validate_catalog.py ${RUN_DIR}/seed.json ${RUN_DIR}/catalog.json ${RUN_DIR}/approved.json $([ -f ${RUN_DIR}/same_name_review.json ] && echo "--review ${RUN_DIR}/same_name_review.json") | tee ${RUN_DIR}/repair_validation.txt ; echo "exit=\${PIPESTATUS[0]}"
Return passed=(exit==0) and output=verbatim validator output.`, {schema:VAL_SCHEMA, model:'opus', label:'repair-validate', phase:'Validate'})
if (!val || !val.passed) throw new Error(`repair validation failed: ${val && val.output}`)

return { run_id: RUN_ID, candidates: suggested.count, approved: reviewFile.reviews.filter(r => r.verdict === 'SAME').length, apply: applied.summary, validation: 'PASSED' }
