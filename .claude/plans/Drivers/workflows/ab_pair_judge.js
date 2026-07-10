export const meta = {
  name: 'ab-pair-judge',
  description: 'Decision-④ A/B arm harness: judge a chosen idx list of PINNED repair candidates with TODAY S EXACT per-pair prompt (byte-identical to repair_duplicates.js PAIR_REVIEW_PROMPT), write verdicts to a file. NO suggest, NO apply, NO catalog mutation — pure measurement. args = { run_id, idx: [ints], out: "filename.json" }.',
  phases: [ { title: 'Fetch', detail: 'show-clerks pull pinned candidates (hash-bound, <=3 per clerk)' }, { title: 'Judge', detail: 'one per-pair judge per idx — byte-identical single-pair prompt' }, { title: 'Record', detail: 'verdicts file written with rv/h32 expect binding' } ],
}

const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY  = '/home/faisal/EventMarketDB/venv/bin/python3'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
const RUN_ID = A.run_id || ''
const IDX = Array.isArray(A.idx) ? A.idx.map(Number) : null
const OUT = A.out || ''
if (!RUN_ID || !IDX || !IDX.length || !OUT || !/^[A-Za-z0-9._-]+$/.test(OUT)) throw new Error('ab_pair_judge requires args = { run_id, idx:[ints], out:"filename.json" }')
const RUN_DIR = `${DIR}/runs/${RUN_ID}`

const EXACT_MEANING_RULE = `Approve SAME only if all three are true:
1. same object or metric
2. same scope
3. same mechanism
If any one is false or unclear, verdict is DIFFERENT or UNCLEAR.`
// VERBATIM copy of repair_duplicates.js PAIR_REVIEW_PROMPT — byte-identical judging basis.
const PAIR_REVIEW_PROMPT = c => `You are the duplicate-repair judge. A deterministic suggester found a possible missed duplicate pair. Embeddings/token overlap only suggested it; YOU decide exact meaning from evidence.
Candidate JSON:
${JSON.stringify(c)}
${EXACT_MEANING_RULE}
MF-02 (cross-flavor guard): different flavors of one topic — base vs \`_guidance\` vs \`_surprise\` — are NEVER the same driver; never SAME_AS, never a cross-flavor rewrite target.
Return REVIEW_SCHEMA. Copy a and b EXACTLY as given in the candidate (the same two strings). SAME means add reversible SAME_AS. DIFFERENT/UNCLEAR means keep separate.`
const REVIEW_SCHEMA = { type:'object', additionalProperties:false, required:['a','b','verdict','why'], properties:{
  a:{type:'string'}, b:{type:'string'}, verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']}, why:{type:'string'} } }
const SHOW_SCHEMA = { type:'object', additionalProperties:false, required:['candidates','page_h32'], properties:{
  candidates:{type:'array', items:{type:'object', additionalProperties:true}}, page_h32:{type:'integer'} } }
const APPLY_SCHEMA = { type:'object', additionalProperties:false, required:['ok','summary'], properties:{ ok:{type:'boolean'}, summary:{type:'string'} } }
const norm = s => (s||'').trim().toLowerCase()
const h32 = s => { let h = 0; for (let i = 0; i < s.length; i++) h = ((Math.imul(h, 31) + s.charCodeAt(i)) >>> 0); return h }
const clean = s => (s || '').replace(/[\u0000-\u001f]/g, ' ')
const canon = v => { if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']'
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}'
  return JSON.stringify(v) }

phase('Fetch')
const sorted = [...IDX].sort((x, y) => x - y)
const candByIdx = {}
for (let s = 0; s < sorted.length; s += 3) {
  const grp = sorted.slice(s, s + 3)
  // billing guard prepended 2026-06-12 (gap: this harness spawns many opus agents but had
  // no step-0 guard — the only entry workflow without one); judging prompt bytes untouched.
  const shown = await agent(`Run with Bash:
test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; } && ${PY} ${DIR}/workflows/repair_duplicates.py show ${RUN_DIR} --idx ${grp.join(',')}
Return the printed JSON exactly as SHOW_SCHEMA.`, {schema:SHOW_SCHEMA, model:'opus', label:`ab-show:${grp.join(',')}`, phase:'Fetch'})
  if (!shown) throw new Error('ab show clerk died — fail-close.')
  if (h32(canon(shown.candidates)) !== shown.page_h32) throw new Error('ab show relay drift — fail-close.')
  if (JSON.stringify(shown.candidates.map(c => c.idx)) !== JSON.stringify(grp)) throw new Error('ab show idx mismatch — fail-close.')
  for (const c of shown.candidates) candByIdx[c.idx] = c
}

phase('Judge')
const verdicts = (await parallel(sorted.map(i => () => {
  const { idx, ...c } = candByIdx[i]
  return agent(PAIR_REVIEW_PROMPT(c), {schema:REVIEW_SCHEMA, model:'opus', label:`ab-pair:${c.a}:${c.b}`, phase:'Judge'}).then(v => ({i, c, v}))
}))).filter(Boolean)
if (verdicts.length !== sorted.length) throw new Error(`ab pair-judge lost ${sorted.length - verdicts.length} verdict(s) — fail-close.`)
for (const r of verdicts) {
  if (norm(r.v.a) !== norm(r.c.a) || norm(r.v.b) !== norm(r.c.b))
    throw new Error(`ab pair mismatch: judged "${r.v.a}|${r.v.b}" assigned "${r.c.a}|${r.c.b}" — fail-close.`)
}

phase('Record')
const fileObj = { arm: 'per_pair', run_id: RUN_ID, reviews: verdicts.map(r => ({ idx: r.i, a: r.c.a, b: r.c.b, verdict: r.v.verdict, why: clean(r.v.why) })) }
const fileJson = JSON.stringify(fileObj)
const FILE_H32 = h32(fileJson)
const rec = await agent(`Use the Write tool to save this exact JSON (byte-for-byte) to ${RUN_DIR}/${OUT}:
${fileJson}
Then run with Bash (verifies the written bytes match the source string — row count AND content hash; non-zero exit on any mismatch):
${PY} -c "import sys,json; sys.path.insert(0,'${DIR}/workflows'); from assemble_catalog import h32; raw=open('${RUN_DIR}/${OUT}').read().rstrip(chr(10)); assert h32(raw)==${FILE_H32}, 'H32 MISMATCH: file does not match source string'; print(json.dumps({'rv':len(json.loads(raw)['reviews']),'h32_ok':True}))"
Return ok=true and summary = the printed JSON; non-zero exit -> ok=false + exact error.`, {schema:APPLY_SCHEMA, model:'opus', label:'ab-record', phase:'Record'})
if (!rec || !rec.ok) throw new Error(`ab record failed: ${rec && rec.summary}`)
const counts = { SAME: 0, DIFFERENT: 0, UNCLEAR: 0 }
for (const r of fileObj.reviews) counts[r.verdict]++
return { run_id: RUN_ID, judged: fileObj.reviews.length, counts, out: OUT, expect_h32: h32(fileJson) }
