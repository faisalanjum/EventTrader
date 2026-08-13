// K-fields GO #1 official drafting workflow (persisted; v5-contract era).
// Launch via the Workflow tool with {scriptPath: <this file>} and args =
// the events array from launch_kfields_drafts.manifest.json (source_id,
// ticker, input_path per event). EVERY worker runs on agentType lean-probe
// (Read-only — Bash/Glob/Grep structurally impossible), effort high,
// byte-identical prompts except the model slot. Replies return RAW TEXT;
// Python (raw_transport + kf_lint) parses exactly and enforces the contract.
export const meta = {
  name: 'kfields-dual-draft-v2',
  description: 'K-fields GO #1: 72 blind gold drafts (36 events x sonnet+opus @ high, lean-probe)',
  phases: [
    { title: 'Draft-Sonnet', detail: '36 blind drafts, one per event' },
    { title: 'Draft-Opus', detail: '36 blind drafts, one per event' },
  ],
}
// REPO-RELATIVE, resolved by the Workflow caller from the repository root —
// the same convention as the manifest's input_path fields. The absolute form
// NOTE: there is deliberately NO schema object here and NO `schema:` on the
// agent calls. `schema:` makes the workflow parse the reply in JavaScript, whose
// IEEE-754 doubles collapse high-precision numbers (proven: 1.00000000000000000001
// and ...02 both become 1) BEFORE Python runs. Agents return raw TEXT; the
// AUTHORITATIVE contract lives in Python — raw_transport.py saves the text
// unchanged, parses it with parse_float=Decimal, and kf_lint enforces the
// V2 item shape on the exact values (the Step-2 builder owns that shape).
// STEP 3 §2 (Codex SEQ 1089): the worker receives ONE COMPLETE PREASSEMBLED
// PROMPT and nothing else. It is built trusted-side by build_launch_manifest.py
// from the single Step-2 builder output, with the event view substituted LAST at
// the builder's own placeholder. No repository path is sent and no file is read
// by a worker; the retired V1 field-count instruction is gone with the shape
// that defined it. PROMPTS is emitted with the guard table below.
const prompt = (sid) => {
  const p = PROMPTS[sid]
  if (!p) throw new Error(`no preassembled prompt for ${sid}`)
  return p
}

const EVENTS = typeof args === 'string' ? JSON.parse(args) : args
__GUARD__
const results = await pipeline(
  EVENTS,
  ev => parallel([
    () => agent(prompt(ev.source_id),
      { label: `S:${ev.ticker}:${String(ev.source_id).slice(-6)}`, phase: 'Draft-Sonnet',
        model: 'sonnet', effort: 'high', agentType: 'lean-probe' }),
    () => agent(prompt(ev.source_id),
      { label: `O:${ev.ticker}:${String(ev.source_id).slice(-6)}`, phase: 'Draft-Opus',
        model: 'opus', effort: 'high', agentType: 'lean-probe' }),
  ]).then(([s, o]) => ({ source_id: ev.source_id, ticker: ev.ticker, sonnet: s, opus: o }))
)
const done = results.filter(Boolean)
log(`drafted ${done.length}/${EVENTS.length} events`)
return { events: done.length, results: done }
