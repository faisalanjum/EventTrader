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
// hardcoded one machine's home directory into a committed artifact.
const BASE = '.claude/plans/Drivers/experiments'
const CONTRACT = BASE + '/harness/exp5_item_contract.md'
const WRAPPER = BASE + '/keys/K-fields/drafting_wrapper.md'
// NOTE: there is deliberately NO schema object here and NO `schema:` on the
// agent calls. `schema:` makes the workflow parse the reply in JavaScript, whose
// IEEE-754 doubles collapse high-precision numbers (proven: 1.00000000000000000001
// and ...02 both become 1) BEFORE Python runs. Agents return raw TEXT; the
// AUTHORITATIVE contract lives in Python — raw_transport.py saves the text
// unchanged, parses it with parse_float=Decimal, and kf_lint enforces the
// 37 model-owned fields (derived from PreparedFactV1) on the exact values.
const prompt = (sid, path) =>
  `You are a BLIND gold-key drafter for one source event.\n` +
  `1. Read ${WRAPPER} (your instructions — including the EXACT-INPUT rule).\n` +
  `2. Read ${CONTRACT} (the verbatim field law — apply it exactly).\n` +
  `3. Read ${path} — the event: text_parts (the ONLY evidence), ticker, fye_month, event_date, and menu_tokens (the PIT slice menu).\n` +
  `Read ONLY those three files. Label EVERY DriverUpdate-worthy fact per the wrapper's DU-03 gate, from the event text alone. ` +
  `Every item must contain ALL 37 model-owned fields explicitly (null where the source does not state it). Quotes must be verbatim substrings of the text_parts content (no length limit). ` +
  `Return the JSON object for source_id ${sid}.`
const EVENTS = typeof args === 'string' ? JSON.parse(args) : args
__GUARD__
const results = await pipeline(
  EVENTS,
  ev => parallel([
    () => agent(prompt(ev.source_id, ev.input_path || ev.path),
      { label: `S:${ev.ticker}:${String(ev.source_id).slice(-6)}`, phase: 'Draft-Sonnet',
        model: 'sonnet', effort: 'high', agentType: 'lean-probe' }),
    () => agent(prompt(ev.source_id, ev.input_path || ev.path),
      { label: `O:${ev.ticker}:${String(ev.source_id).slice(-6)}`, phase: 'Draft-Opus',
        model: 'opus', effort: 'high', agentType: 'lean-probe' }),
  ]).then(([s, o]) => ({ source_id: ev.source_id, ticker: ev.ticker, sonnet: s, opus: o }))
)
const done = results.filter(Boolean)
log(`drafted ${done.length}/${EVENTS.length} events`)
return { events: done.length, results: done }
