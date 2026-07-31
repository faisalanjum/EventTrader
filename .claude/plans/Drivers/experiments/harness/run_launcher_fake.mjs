// Executes the GENERATED launcher with FAKE agents (no AI, no network).
// Proves: it parses, binds to the 36 manifest events, spawns 2 arms each with
// lean-probe/high and NO `schema:`, and returns RAW TEXT strings.
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8')
const events = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'))
const calls = []
const agent = async (prompt, opts) => {           // fake agent
  calls.push(opts)
  if ('schema' in (opts || {})) throw new Error('FAIL: launcher passed schema: -> JS would parse numbers')
  return '{"source_id":"X","facts":[],"n":1.00000000000000000001}'   // RAW TEXT
}
const parallel = async (thunks) => Promise.all(thunks.map(t => t()))
const pipeline = async (items, ...stages) => {
  const out = []
  for (const it of items) { let v = it; for (const st of stages) v = await st(v); out.push(v) }
  return out
}
const log = () => {}
const body = src.replace(/^export const meta = \{[\s\S]*?\n\}\n/m, '')
const fn = new Function('agent','parallel','pipeline','log','args',
                        `return (async () => { ${body} })()`)
const res = await fn(agent, parallel, pipeline, log, events)
console.log(JSON.stringify({
  returned_events: res.events,
  rows: res.results.length,
  agent_calls: calls.length,
  all_lean_probe: calls.every(c => c.agentType === 'lean-probe'),
  all_high: calls.every(c => c.effort === 'high'),
  models: [...new Set(calls.map(c => c.model))].sort(),
  any_schema: calls.some(c => 'schema' in c),
  first_arm_is_raw_string: typeof res.results[0].sonnet === 'string',
  digits_intact: res.results[0].sonnet.includes('1.00000000000000000001'),
}))
