// THE ONE FAKE LAUNCH RUNNER. Executes GENERATED launchers with fake agents
// (no AI, no network), the way the Workflow runtime executes them: the script
// body inside an async function, with `agent` / `parallel` / `pipeline` / `log`
// / `args` supplied as hooks. The ONE source transform is dropping the `export`
// keyword, which is only legal at module top level.
//
// Proves what a text grep cannot: that every launcher PARSES, binds to its
// locked packets, spawns the planned lanes with the pinned runtime identity and
// NO `schema:` (which would make JS parse the reply and collapse exact digits),
// runs its own pre-call gate, and returns RAW TEXT strings.
//
// Config: {launchers:[{path,args}], env:{...}, replies:{sha256:text}|null,
//          default_reply:string}. With `replies`, the fake agent answers by the
// sha256 OF THE PROMPT IT RECEIVED, so a worker served any other bytes fails
// the run instead of quietly answering.
import fs from 'node:fs'
import crypto from 'node:crypto'

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const sha = s => crypto.createHash('sha256').update(s, 'utf8').digest('hex')

const rows = [], calls = [], errors = []
let maxActive = 0
for (const slice of cfg.launchers) {
  const src = fs.readFileSync(slice.path, 'utf8').replace('export const meta', 'const meta')
  let active = 0
  const agent = async (prompt, opts) => {
    const h = sha(prompt)
    calls.push({ prompt_sha256: h, chars: prompt.length, schema: 'schema' in (opts || {}), ...opts })
    // HOW MANY ARE IN FLIGHT AT ONCE. The launcher must be serial, so the fake
    // yields once before answering: without a real suspension point every call
    // would resolve before the next began and a burst would look serial.
    active += 1
    if (active > maxActive) maxActive = active
    try {
      await new Promise(r => setImmediate(r))
      if (!cfg.replies) return cfg.default_reply
      const text = cfg.replies[h]
      // undefined = bytes nobody pinned, still a hard failure. An EXPLICIT null
      // is the runtime's own no-answer, which a control needs to simulate.
      if (text === undefined) throw new Error(`agent was served UNPINNED prompt bytes (${h})`)
      return text
    } finally {
      active -= 1
    }
  }
  const parallel = async thunks => Promise.all(thunks.map(t => t()))
  const pipeline = async (items, ...stages) => Promise.all(items.map(async (it, i) => {
    let v = it
    for (const st of stages) v = await st(v, it, i)
    return v
  }))
  const log = () => {}
  // THE REAL VM HAS NO `process`. Injecting one is what hid a launcher that
  // refused before its first agent on every real run (Codex SEQ 1315 item 1),
  // so the fake shadows it with `undefined` unless a control asks otherwise.
  const proc = cfg.provide_process ? { env: cfg.env } : undefined
  try {
    const fn = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'log', 'process', src)
    const out = await fn(slice.args, agent, parallel, pipeline, log, proc)
    rows.push(...(out.results || []))
  } catch (e) {
    errors.push(`${slice.path}: ${e.message}`)
  }
}
process.stdout.write(JSON.stringify({ rows, calls, errors, maxActive }))
