export const meta = {
  name: 'exp0-grader-probe',
  description: 'EXP-0 grader-qualification runner. For each arm (g_sonnet_a/g_sonnet_b -> sonnet, g_opus -> opus): verify the locked key sha, project the BLIND K-pairs.v1.1 pairs server-side, fetch them in hash-verified chunks, then judge one pair per agent() call with ONE byte-identical prompt (model slot only). Raw evidence only (kernel section 9 smoke-alarm blindness): gold/family/provenance/rival never reach the grader. Writes verdicts.<arm>.json per arm; NO catalog/Neo4j mutation. args = { run_id, arms:[{arm,n,page_h32}], batch }.',
  phases: [
    { title: 'Guard', detail: 'billing guard + key sha verify + blind projection written server-side (haiku)' },
    { title: 'Fetch', detail: 'hash-verified chunked fetch of the blind pairs (haiku)' },
    { title: 'Judge', detail: 'one grader per pair, byte-identical prompt, arm model slot' },
    { title: 'Record', detail: 'verdicts.<arm>.json written + h32-verified' },
  ],
}

const EXP = '/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments'
const DIR = '/home/faisal/EventMarketDB/.claude/plans/Drivers'   // workflows/ has assemble_catalog.h32
const PY = '/home/faisal/EventMarketDB/venv/bin/python3'
const HARNESS = `${EXP}/harness`

const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
const RUN_ID = A.run_id || ''
const ARMS = Array.isArray(A.arms) ? A.arms : null
const BATCH = Number.isInteger(A.batch) ? A.batch : 10
const KEY = A.key || `${EXP}/keys/K-pairs/K-pairs.v1.1.jsonl`
const LOCK = A.lock || `${EXP}/keys/K-pairs/K-pairs.v1.1.lock.json`
const PROTOCOL = A.protocol || `${EXP}/keys/K-pairs/protocol.md`
const ARM_MODEL = { g_sonnet_a: 'sonnet', g_sonnet_b: 'sonnet', g_opus: 'opus' }
if (!RUN_ID || !ARMS || !ARMS.length) throw new Error('grader_probe requires { run_id, arms:[{arm,n,page_h32}], batch? }')
const RUN_DIR = `${EXP}/exp0_graders/runs/${RUN_ID}`

const h32 = s => { let h = 0; for (let i = 0; i < s.length; i++) h = ((Math.imul(h, 31) + s.charCodeAt(i)) >>> 0); return h }
const canon = v => Array.isArray(v) ? '[' + v.map(canon).join(',') + ']'
  : (v && typeof v === 'object') ? '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}'
  : JSON.stringify(v)
const clean = s => (s || '').split('').map(c => c.charCodeAt(0) < 32 ? ' ' : c).join('')

// Byte-identical grader prompt (protocol section 6 contract). Model varies per arm; these bytes do NOT.
const GRADER_PROMPT = p => `You are a driver-identity grader. A deterministic step proposed that two business drivers (causes of a company's results) MIGHT be the same underlying driver. Decide from the raw evidence ONLY.

Default to DIFFERENT: treat the two as different causes UNLESS the evidence compels sameness. Over-merging is permanent damage; over-splitting is cheap and reversible.

Approve SAME only if ALL THREE hold, each backed by a verbatim quote from that side:
1. same OBJECT — the same underlying thing/metric is described.
2. same SCOPE — the same business population AND ownership class (e.g. company-owned vs franchised, segment vs consolidated, gross vs net).
3. same MECHANISM — the same causal driver, not a merely correlated or downstream effect.
If any one is false or unclear -> DIFFERENT.

SIDE A:
${JSON.stringify(p.side_a)}
SIDE B:
${JSON.stringify(p.side_b)}

Cite ONE verbatim quote from EACH side (copy characters exactly from that side's quotes). Then return the schema with pair_id exactly "${p.pair_id}".`

const VERDICT_SCHEMA = { type: 'object', additionalProperties: false, required: ['pair_id', 'verdict', 'cited_a', 'cited_b', 'reason'],
  properties: { pair_id: { type: 'string' }, verdict: { type: 'string', enum: ['SAME', 'DIFFERENT'] },
    cited_a: { type: 'string' }, cited_b: { type: 'string' }, reason: { type: 'string' } } }
const GUARD_SCHEMA = { type: 'object', additionalProperties: false, required: ['ok', 'page_h32', 'n'],
  properties: { ok: { type: 'boolean' }, page_h32: { type: 'integer' }, n: { type: 'integer' } } }
const BATCH_SCHEMA = { type: 'object', additionalProperties: false, required: ['pairs'],
  properties: { pairs: { type: 'array', items: { type: 'object', additionalProperties: true } } } }
const APPLY_SCHEMA = { type: 'object', additionalProperties: false, required: ['ok', 'summary'],
  properties: { ok: { type: 'boolean' }, summary: { type: 'string' } } }

const summary = []
for (const spec of ARMS) {
  const ARM = spec.arm, N = spec.n, PAGE_H32 = spec.page_h32
  const MODEL = ARM_MODEL[ARM]
  if (!MODEL) throw new Error(`EXP-0 unknown arm ${ARM}`)
  const OUT = `verdicts.${ARM}.json`, BLIND = `${RUN_DIR}/blind.${ARM}.json`

  phase('Guard')
  const guard = await agent(`Run with Bash (fail-close; do not invent output):
test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present — subscription-only policy (CLAUDE.md)"; exit 9; }
${PY} ${HARNESS}/sha_lock.py verify --key ${KEY} --lock ${LOCK} --protocol ${PROTOCOL} >/dev/null || { echo "KEY-SHA-VERIFY-FAIL"; exit 8; }
${PY} ${HARNESS}/key_lint.py blind --key ${KEY} --arm ${ARM} > ${BLIND} || { echo "BLIND-FAIL"; exit 7; }
${PY} -c "import json;d=json.load(open('${BLIND}'));print(json.dumps({'ok':True,'page_h32':d['page_h32'],'n':d['n']}))"
Return that exact printed JSON as GUARD_SCHEMA.`, { schema: GUARD_SCHEMA, model: 'haiku', label: `guard:${ARM}`, phase: 'Guard' })
  if (!guard || !guard.ok) throw new Error(`EXP-0 ${ARM} GUARD failed (billing / key-sha / blind).`)
  if (guard.page_h32 !== PAGE_H32 || guard.n !== N) throw new Error(`EXP-0 ${ARM} guard mismatch: on-disk {page_h32:${guard.page_h32},n:${guard.n}} != args {page_h32:${PAGE_H32},n:${N}} — fail-close.`)

  phase('Fetch')
  const starts = []; for (let s = 0; s < N; s += BATCH) starts.push(s)
  const batches = await parallel(starts.map(s => () => agent(`Run with Bash and return the printed JSON EXACTLY as BATCH_SCHEMA (copy it byte-for-byte; do NOT summarize, reorder, or alter any character):
${PY} -c "import json;d=json.load(open('${BLIND}'));print(json.dumps({'pairs':d['pairs'][${s}:${s + BATCH}]}))"`,
    { schema: BATCH_SCHEMA, model: 'haiku', label: `fetch:${ARM}:${s}`, phase: 'Fetch' }).then(r => ({ s, pairs: (r && r.pairs) || null }))))
  if (batches.some(b => !b.pairs)) throw new Error(`EXP-0 ${ARM} FETCH failed: ${batches.filter(b => !b.pairs).length} empty batch(es).`)
  batches.sort((x, y) => x.s - y.s)
  const PAIRS = batches.flatMap(b => b.pairs)
  if (PAIRS.length !== N) throw new Error(`EXP-0 ${ARM} FETCH count ${PAIRS.length} != ${N}.`)
  if (new Set(PAIRS.map(p => p.pair_id)).size !== N) throw new Error(`EXP-0 ${ARM} FETCH duplicate/missing pair_ids.`)
  const got = h32(canon(PAIRS))
  if (got !== PAGE_H32) throw new Error(`EXP-0 ${ARM} INTEGRITY FAIL: assembled h32 ${got} != page_h32 ${PAGE_H32} — blind relay corrupted, fail-close.`)

  phase('Judge')
  const results = await parallel(PAIRS.map(p => () =>
    agent(GRADER_PROMPT(p), { schema: VERDICT_SCHEMA, model: MODEL, label: `g:${ARM}:${p.pair_id}`, phase: 'Judge' }).then(v => ({ p, v }))))
  const verdicts = []; let invalid = 0
  for (const r of results) {
    if (!r || !r.v) { invalid++; verdicts.push({ pair_id: r ? r.p.pair_id : null, verdict: null, cited_a: '', cited_b: '', reason: 'INVALID_OR_DIED' }); continue }
    if (r.v.pair_id !== r.p.pair_id) throw new Error(`EXP-0 ${ARM} pair_id echo mismatch: got ${r.v.pair_id}, sent ${r.p.pair_id} — fail-close.`)
    verdicts.push({ pair_id: r.p.pair_id, verdict: r.v.verdict, cited_a: clean(r.v.cited_a), cited_b: clean(r.v.cited_b), reason: clean(r.v.reason) })
  }
  if (verdicts.length !== N) throw new Error(`EXP-0 ${ARM} lost verdicts: ${N - verdicts.length}.`)

  phase('Record')
  const counts = { SAME: 0, DIFFERENT: 0, INVALID: invalid }
  for (const v of verdicts) if (v.verdict === 'SAME' || v.verdict === 'DIFFERENT') counts[v.verdict]++
  const fileObj = { exp_id: 'EXP-0', arm: ARM, run_id: RUN_ID, key_sha_page_h32: PAGE_H32, judged: verdicts.length - invalid, invalid, counts, verdicts }
  const fileJson = JSON.stringify(fileObj)
  const FILE_H32 = h32(fileJson)
  const rec = await agent(`Use the Write tool to save this exact JSON (byte-for-byte) to ${RUN_DIR}/${OUT}:
${fileJson}
Then run with Bash (verifies the written bytes; non-zero exit on mismatch):
${PY} -c "import sys,json;sys.path.insert(0,'${DIR}/workflows');from assemble_catalog import h32;raw=open('${RUN_DIR}/${OUT}').read().rstrip(chr(10));assert h32(raw)==${FILE_H32},'H32 MISMATCH';print('OK',len(json.loads(raw)['verdicts']))"
Return ok=true and summary = the printed line; non-zero exit -> ok=false + the exact error.`, { schema: APPLY_SCHEMA, model: 'haiku', label: `record:${ARM}`, phase: 'Record' })
  if (!rec || !rec.ok) throw new Error(`EXP-0 ${ARM} RECORD failed: ${rec && rec.summary}`)
  summary.push({ arm: ARM, model: MODEL, judged: fileObj.judged, invalid, counts, out: OUT })
  log(`${ARM} done: judged ${fileObj.judged}, invalid ${invalid}, SAME ${counts.SAME}, DIFFERENT ${counts.DIFFERENT}`)
}
return { run_id: RUN_ID, arms: summary }
