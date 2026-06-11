export const meta = {
  name: 'driver-repair-duplicates',
  description: 'Required duplicate-repair pass (§13.2): code suggests possible missed SAME_AS pairs, AI judges exact meaning, code applies approved links through assemble_catalog.py, then validate_catalog.py checks structure. C5 batched lane (args.batch_size>1, DEFAULT 1 = per-pair byte-identical): k-pair batched PROPOSER judges (hard name-disjoint, h32-shuffled, paged via args.page_size default 600 — a page size, never a cap) + every batched SAME re-judged by a BLIND per-pair confirm with the identical single-pair prompt before apply; python plan/show CLIs are the pure-code spine; apply enforces plan-vs-review P2. Embeddings/token overlap suggest only; AI decides meaning; code writes links.',
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
// C5 batched lane (OFF by default — batching is a judge-input change gated on its A/B):
// batch_size=1 = today's per-pair path byte-identical; >1 = batched PROPOSER + blind
// per-pair CONFIRM (every batched SAME re-judged in isolation with TODAY'S EXACT prompt
// before apply — the terminal merge direction never rests on a batched context).
const BATCH_K = Number.isInteger(A.batch_size) ? A.batch_size : 1
const PAGE_SIZE = Number.isInteger(A.page_size) ? A.page_size : 600
// Batched mode NEVER inherits a cap: default limit 0 = ALL pairs (owner rule: 600 is a page
// size, not a limit; every pair gets a verdict). Per-pair mode keeps today's 200 default.
const LIMIT = Number.isInteger(A.limit) ? A.limit : (BATCH_K > 1 ? 0 : 200)
const USE_EMBEDDINGS = A.use_embeddings !== false
if (!RUN_ID) throw new Error('repair_duplicates.js requires args = { run_id, limit? }')
const RUN_DIR = `${DIR}/runs/${RUN_ID}`

const EXACT_MEANING_RULE = `Approve SAME only if all three are true:
1. same object or metric
2. same scope
3. same mechanism
If any one is false or unclear, verdict is DIFFERENT or UNCLEAR.`

// Shared verbatim by the per-pair lane AND the batched confirm lane — byte-identical
// judging prompts by construction (the confirm judge never learns a proposer said SAME).
const PAIR_REVIEW_PROMPT = c => `You are the duplicate-repair judge. A deterministic suggester found a possible missed duplicate pair. Embeddings/token overlap only suggested it; YOU decide exact meaning from evidence.
Candidate JSON:
${JSON.stringify(c)}
${EXACT_MEANING_RULE}
Return REVIEW_SCHEMA. Copy a and b EXACTLY as given in the candidate (the same two strings). SAME means add reversible SAME_AS. DIFFERENT/UNCLEAR means keep separate.`
const REFUTE2_PROMPT = c => `SECOND independent skeptic for a HIGH-BLAST duplicate repair SAME_AS. This pair spans ${c.n_companies} companies. A wrong link becomes a false cross-company read-through.
Candidate JSON:
${JSON.stringify(c)}
Judge each lens separately with quote support: same object, same scope, same mechanism. survives=true only if all three pass. Default false.`

const SUGGEST_SCHEMA = { type:'object', additionalProperties:false, required:['count','candidates','pairs_h32','cands_h32','limit_used','use_embeddings'], properties:{
  count:{type:'integer'}, clipped:{type:'integer', description:'pairs dropped by --limit (0 = none)'}, candidates:{type:'array', items:{type:'object', additionalProperties:true}},
  pairs_h32:{type:'integer', description:'code-printed h32 over the a|b pair lines'}, cands_h32:{type:'integer', description:'code-printed h32 over the canonical candidates JSON'},
  limit_used:{type:'integer'}, use_embeddings:{type:'boolean'} } }
const REVIEW_SCHEMA = { type:'object', additionalProperties:false, required:['a','b','verdict','why'], properties:{
  a:{type:'string'}, b:{type:'string'}, verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']}, why:{type:'string'} } }
const REFUTE2_SCHEMA = { type:'object', additionalProperties:false, required:['object','scope','mechanism','survives'], properties:{
  object:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  scope:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  mechanism:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}},
  survives:{type:'boolean'} } }
const APPLY_SCHEMA = { type:'object', additionalProperties:false, required:['ok','summary'], properties:{ ok:{type:'boolean'}, summary:{type:'string'} } }
const VAL_SCHEMA = { type:'object', additionalProperties:false, required:['passed','output'], properties:{ passed:{type:'boolean'}, output:{type:'string'} } }

const norm = s => (s||'').trim().toLowerCase()
const h32 = s => { let h = 0; for (let i = 0; i < s.length; i++) h = ((Math.imul(h, 31) + s.charCodeAt(i)) >>> 0); return h }
const clean = s => (s || '').replace(/[\u0000-\u001f]/g, ' ')   // audit-text cleanup: control chars in judge NOTES -> spaces at file-build time (post-judgment; never names/verdicts)

const SUGGEST_SLIM_SCHEMA = { type:'object', additionalProperties:false, required:['count','clipped','pairs_h32','cands_h32','limit_used','use_embeddings'], properties:{
  count:{type:'integer'}, clipped:{type:'integer'}, pairs_h32:{type:'integer'}, cands_h32:{type:'integer'},
  limit_used:{type:'integer'}, use_embeddings:{type:'boolean'} } }

phase('Suggest')
// C5 slim relay (batched mode): the agent returns counts/hashes/params ONLY — the full
// candidates blob lives on DISK (pinned file), where plan/show/apply read and enforce it.
// Per-pair mode keeps the full relay + content-hash verification (today's path).
const SUGGEST_CMD = `Run with Bash:
test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; } && ${PY} ${DIR}/workflows/repair_duplicates.py suggest ${RUN_DIR} --limit ${LIMIT}${USE_EMBEDDINGS ? ' --use-embeddings' : ''}`
const suggested = BATCH_K > 1
  ? await agent(`${SUGGEST_CMD} --print-summary
Return the printed JSON exactly as SUGGEST_SLIM_SCHEMA.`, {schema:SUGGEST_SLIM_SCHEMA, model:'opus', label:'repair-suggest', phase:'Suggest'})
  : await agent(`${SUGGEST_CMD}
Return the printed JSON exactly as SUGGEST_SCHEMA.`, {schema:SUGGEST_SCHEMA, model:'opus', label:'repair-suggest', phase:'Suggest'})
if (!suggested) throw new Error('repair suggest agent died — fail-close.')
if (suggested.limit_used !== LIMIT || suggested.use_embeddings !== USE_EMBEDDINGS) throw new Error(`repair-suggest ran with wrong params (limit=${suggested.limit_used} embeddings=${suggested.use_embeddings}, commanded limit=${LIMIT} embeddings=${USE_EMBEDDINGS}) — relay dropped/changed a flag; fail-close.`)
const canon = v => { if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']'
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}'
  return JSON.stringify(v) }
if (BATCH_K > 1) {
  // owner rule: in batched mode EVERY pair must be reviewed — a clip is a hard failure,
  // never a log line (per-pair mode keeps today's loud-log behavior below).
  if ((suggested.clipped | 0) > 0) throw new Error(`repair-suggest clipped ${suggested.clipped} pair(s) in BATCHED mode — every pair must be reviewed; remove the limit (0 = no cap) or raise it. Fail-close.`)
} else {
  // C5-study today-bug fix (per-pair lane): the relay carries the FULL candidates JSON —
  // bind the relayed copy to the code-printed truth so an abridged/reordered/mutated copy
  // can never silently skip or mislead judges (the fan-out judges read THIS copy).
  const cands = suggested.candidates || []
  if (cands.length !== suggested.count) throw new Error(`repair-suggest relay drift: ${cands.length} candidates relayed vs count=${suggested.count} — fail-close.`)
  if (h32(cands.map(c => `${c.a}|${c.b}`).join(String.fromCharCode(10))) !== suggested.pairs_h32) throw new Error('repair-suggest relay drift: pair list != code-printed pairs_h32 — fail-close.')
  if (h32(canon(cands)) !== suggested.cands_h32) throw new Error('repair-suggest relay drift: candidate content != code-printed cands_h32 — fail-close.')
  if ((suggested.clipped | 0) > 0) log(`repair-suggest: limit dropped ${suggested.clipped} candidate pair(s) — raise --limit to sweep them in a later pass (NO silent caps)`)
}
if (!suggested.count) return { run_id: RUN_ID, candidates: 0, approved: 0, validation: 'SKIPPED no candidates' }

phase('Review')
let reviewFile
if (BATCH_K <= 1) {
// ===== per-pair lane (today's path, byte-identical prompts) =====
const reviews = (await parallel((suggested.candidates || []).map(c => () => agent(PAIR_REVIEW_PROMPT(c), {schema:REVIEW_SCHEMA, model:'opus', label:`repair:${c.a}:${c.b}`, phase:'Review'}).then(v => ({candidate:c, verdict:v}))))).filter(Boolean)
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
    const r2 = await agent(REFUTE2_PROMPT(c), {schema:REFUTE2_SCHEMA, model:'opus', label:`repair-refute2:${c.a}:${c.b}`, phase:'Review'})
    const ok = r2 && r2.survives === true && r2.object && r2.object.pass === true && r2.scope && r2.scope.pass === true && r2.mechanism && r2.mechanism.pass === true
    if (ok) v.high_blast_refute2_survived = true
    else v.verdict = 'UNCLEAR'
  }
}
reviewFile = { reviews: reviews.map(r => ({ ...r.verdict, why: clean(r.verdict.why) })) }
} else {
// ===== C5 batched lane: PROPOSER batches + blind per-pair CONFIRM (spec: C5_BatchedRepair.md) =====
const PLAN_SCHEMA2 = { type:'object', additionalProperties:false, required:['ok','n_candidates','pages','batches','batch_counts','cands_sha256'], properties:{
  ok:{type:'boolean'}, n_candidates:{type:'integer'}, pages:{type:'integer'}, batches:{type:'integer'},
  batch_counts:{type:'array', items:{type:'integer'}}, cands_sha256:{type:'string'} } }
const BATCH_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['idx','a','b','verdict','why'], properties:{
    idx:{type:'integer'}, a:{type:'string'}, b:{type:'string'}, verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']}, why:{type:'string'} }}} } }
const SHOW_SCHEMA = { type:'object', additionalProperties:false, required:['candidates','page_h32'], properties:{
  candidates:{type:'array', items:{type:'object', additionalProperties:true}}, page_h32:{type:'integer'} } }

// deterministic plan: pure code composes pages (PAGE_SIZE is a page size, NEVER a cap),
// hard name-disjoint batches (collisions open fresh batches = per-pair by construction),
// h32-shuffled order (breaks the similarity-ranked anchoring adjacency), batch files on disk.
const plan = await agent(`Run with Bash:
${PY} ${DIR}/workflows/repair_duplicates.py plan ${RUN_DIR} --k ${BATCH_K} --page-size ${PAGE_SIZE}
Return the printed JSON exactly as PLAN_SCHEMA2.`, {schema:PLAN_SCHEMA2, model:'opus', label:'repair-plan', phase:'Review'})
if (!plan || !plan.ok) throw new Error('repair plan agent died/failed — fail-close.')
if (plan.n_candidates !== suggested.count) throw new Error(`repair plan covers ${plan.n_candidates} pairs but suggest pinned ${suggested.count} — mixed generations; fail-close.`)
log(`C5 batched lane: ${plan.n_candidates} pairs -> ${plan.batches} batch(es) over ${plan.pages} page(s) of ${PAGE_SIZE} (k=${BATCH_K}); every batched SAME gets a blind per-pair confirm`)

// PROPOSER fan-out: each judge Reads its own code-written batch file (no giant relay).
const batchOuts = (await parallel(plan.batch_counts.map((cnt, bid) => () => agent(`You are the duplicate-repair judge. Read the file ${RUN_DIR}/repair_batches/batch_${String(bid).padStart(4, '0')}.json with the Read tool — it contains { batch_id, pairs: [...] } with ${cnt} candidate pair(s) (each { idx, a, b, reason, n_companies, sides }). A deterministic suggester found each as a possible missed duplicate; embeddings/token overlap only suggested them; YOU decide exact meaning from evidence. Judge EVERY pair INDEPENDENTLY — never let one pair's verdict influence another.
${EXACT_MEANING_RULE}
Return BATCH_SCHEMA: exactly one verdict per pair, copying idx, a and b EXACTLY as given in that pair. SAME means propose a reversible SAME_AS (a blind second judge will re-check it in isolation). DIFFERENT/UNCLEAR means keep separate.`, {schema:BATCH_SCHEMA, model:'opus', label:`repair-batch:${bid}`, phase:'Review'}).then(v => ({bid, cnt, v}))))).filter(Boolean)
if (batchOuts.length !== plan.batches) throw new Error(`repair batched review lost ${plan.batches - batchOuts.length} batch(es) — fail-close, no partial review.`)
const rows = []
for (const b of batchOuts) {
  const vs = (b.v && b.v.verdicts) || []
  if (vs.length !== b.cnt) throw new Error(`repair batch ${b.bid} returned ${vs.length} verdicts for ${b.cnt} pairs — fail-close.`)
  const seen = new Set()
  for (const v of vs) {
    if (seen.has(v.idx)) throw new Error(`repair batch ${b.bid} duplicated idx ${v.idx} — fail-close.`)
    seen.add(v.idx)
    rows.push(v)
  }
}

// CONFIRM lane: fetch each SAME pair's PINNED candidate via code (show; hash-bound relay,
// <=3 per clerk keeps worst-case prints under the Bash output cap), then re-judge in
// ISOLATION with the byte-identical per-pair prompt. The confirm verdict is FINAL.
const sameIdx = rows.filter(r => r.verdict === 'SAME').map(r => r.idx).sort((x, y) => x - y)
const candByIdx = {}
for (let s = 0; s < sameIdx.length; s += 3) {
  const grp = sameIdx.slice(s, s + 3)
  const shown = await agent(`Run with Bash:
${PY} ${DIR}/workflows/repair_duplicates.py show ${RUN_DIR} --idx ${grp.join(',')}
Return the printed JSON exactly as SHOW_SCHEMA.`, {schema:SHOW_SCHEMA, model:'opus', label:`repair-show:${grp.join(',')}`, phase:'Review'})
  if (!shown) throw new Error('repair show clerk died — fail-close.')
  if (h32(canon(shown.candidates)) !== shown.page_h32) throw new Error('repair show relay drift: candidates != code-printed page_h32 — fail-close.')
  const gotIdx = shown.candidates.map(c => c.idx)
  if (JSON.stringify(gotIdx) !== JSON.stringify(grp)) throw new Error(`repair show returned idx ${gotIdx.join(',')} for requested ${grp.join(',')} — fail-close.`)
  for (const c of shown.candidates) candByIdx[c.idx] = c
}
const confirms = (await parallel(sameIdx.map(i => () => {
  const { idx, ...c } = candByIdx[i]
  return agent(PAIR_REVIEW_PROMPT(c), {schema:REVIEW_SCHEMA, model:'opus', label:`repair-confirm:${c.a}:${c.b}`, phase:'Review'}).then(v => ({i, c, v}))
}))).filter(Boolean)
if (confirms.length !== sameIdx.length) throw new Error(`repair confirm lost ${sameIdx.length - confirms.length} verdict(s) — fail-close.`)
for (const r of confirms) {
  if (norm(r.v.a) !== norm(r.c.a) || norm(r.v.b) !== norm(r.c.b))
    throw new Error(`repair confirm pair mismatch: judged "${r.v.a}|${r.v.b}" but assigned "${r.c.a}|${r.c.b}" — fail-close.`)
}

// merge: confirm verdicts are FINAL for proposed SAMEs (names from the PINNED candidate);
// proposer DIFFERENT/UNCLEAR rows stand (under-merge direction, recoverable).
const confirmByIdx = {}
for (const r of confirms) confirmByIdx[r.i] = r
const finalRows = rows.map(r => {
  if (r.verdict !== 'SAME') return r
  const cf = confirmByIdx[r.idx]
  return { idx: r.idx, a: cf.c.a, b: cf.c.b, verdict: cf.v.verdict, why: cf.v.why, confirmed: true }
})

// high-blast (>=8 companies) confirmed SAMEs additionally face the second skeptic — three
// independent judgments total, per-pair, exactly like today.
for (const r of finalRows) {
  if (r.verdict === 'SAME' && (candByIdx[r.idx].n_companies || 0) >= 8) {
    const { idx, ...c } = candByIdx[r.idx]
    const r2 = await agent(REFUTE2_PROMPT(c), {schema:REFUTE2_SCHEMA, model:'opus', label:`repair-refute2:${c.a}:${c.b}`, phase:'Review'})
    const ok = r2 && r2.survives === true && r2.object && r2.object.pass === true && r2.scope && r2.scope.pass === true && r2.mechanism && r2.mechanism.pass === true
    if (ok) r.high_blast_refute2_survived = true
    else r.verdict = 'UNCLEAR'
  }
}
reviewFile = { reviews: finalRows.map(r => ({ ...r, why: clean(r.why) })) }
}

phase('Apply')

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
