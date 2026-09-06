// Execute the GENERATED reader launcher against FAKE agents and report the
// realised schedule, or the REFUSAL that stopped it. No model is contacted.
//
// `--lock=<sha>` / `--id-<tier>=<exact>` supply the RUN INPUTS the launcher's
// two start gates require. `--plan-lock=<sha>` rewrites the launcher's own
// EXPECTED lock IN A TEMPORARY COPY ONLY — never the committed file — so the
// lawful positive control can be exercised without inventing a reviewed lock in
// the real plan.
import { readFileSync } from 'node:fs'
const argv = process.argv.slice(2)
const flag = (n) => { const a = argv.find(x => x.startsWith(`--${n}=`)); return a ? a.slice(n.length + 3) : null }
const [script, manifest] = argv.filter(a => !a.startsWith('--'))
const man = JSON.parse(readFileSync(manifest, 'utf8'))
const calls = []
const runtime = {}
if (flag('lock')) runtime.kfields_lock_sha256 = flag('lock')
const ids = {}
for (const a of argv) { const m = a.match(/^--id-([a-z0-9_]+)=(.*)$/); if (m) ids[m[1]] = m[2] }
if (Object.keys(ids).length) runtime.model_ids = ids
// PHASE 2: `--retry=<json>` carries the pairs Python classified INVALID.
const retryArg = flag('retry')
if (retryArg) runtime.retry = JSON.parse(retryArg)
// `--bad=<sid>` makes the fake agent answer OFF-CONTRACT for that event on the
// FIRST launch only, so a retry can be exercised with no model.
const bad = flag('bad')
const mutatePrompt = argv.includes('--mutate-prompt')
globalThis.args = argv.includes('--bare-args') ? man.events
                                               : { events: man.events, runtime }
globalThis.agent = async (prompt, opts) => {
  // RECORD THE ACTUAL PROMPT BYTES (Codex SEQ 1161.1). Comparing the launcher's
  // emitted hash to itself proves nothing: a mutant could send a changed prompt
  // while emitting the untouched PROMPT_SHA. The control hashes THESE bytes
  // independently.
  calls.push({ ...opts, _prompt: prompt })
  const sid = FULL_ID[opts.label]
  // `--retry-also-bad` makes the RETRY answer off-contract too, so "a second
  // invalid stops" can be exercised.
  const retryAlsoBad = argv.includes('--retry-also-bad')
  const off = bad && sid === bad && (!runtime.retry || retryAlsoBad)
  return JSON.stringify(off ? { source_id: sid, nonsense: true }
                            : { source_id: sid, facts: [], abstentions: [] })
}
globalThis.parallel = (ts) => Promise.all(ts.map(t => t()))
globalThis.pipeline = async (items, ...stages) => {
  const out = []
  for (const it of items) { let v = it; for (const st of stages) v = await st(v); out.push(v) }
  return out
}
globalThis.log = () => {}
globalThis.phase = () => {}
// label -> full source_id, so the fake agent can echo the right event
const FULL_ID = {}
for (const e of man.events)
  for (const a of man.arms)
    FULL_ID[`${a.arm}:${e.ticker}:${String(e.source_id).slice(-6)}`] = e.source_id
let src = readFileSync(script, 'utf8').replace(/^export const meta/m, 'const meta')
if (mutatePrompt)  // send changed bytes, leave the emitted PROMPT_SHA untouched
  src = src.replace('agent(prompt(s.source_id), {',
                    "agent(prompt(s.source_id) + '\\n(mutated)', {")
const planLock = flag('plan-lock')
if (planLock) src = src.replace(/const KFIELDS_LOCK_SHA256 = null/,
                                `const KFIELDS_LOCK_SHA256 = ${JSON.stringify(planLock)}`)
try {
  const res = await (new (Object.getPrototypeOf(async function(){}).constructor)(
    // the launcher's OWN return is the result; appending another `return`
    // after it is unreachable and silently produced an empty `results`
    src))()
  const byArm = {}
  for (const c of calls) { const a = c.phase.split('-')[0]; byArm[a] = (byArm[a]||0)+1 }
  console.log(JSON.stringify({ ok: true, total: calls.length, planned: res.planned,
    byArm, models: [...new Set(calls.map(c => c.model))].sort(),
    agentTypes: [...new Set(calls.map(c => c.agentType))],
    rows: res.results || [],
    sent: calls.map(c => ({ label: c.label, prompt: c._prompt })) }))
} catch (e) {
  console.log(JSON.stringify({ ok: false, refused: String(e.message), calls: calls.length }))
}
