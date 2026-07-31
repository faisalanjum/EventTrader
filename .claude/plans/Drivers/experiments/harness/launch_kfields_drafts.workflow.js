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
const EXPECTED = {"0000006201-26-000031": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000006201-26-000031.json", "0000006201-26-000032": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000006201-26-000032.json", "0000027904-26-000013": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000027904-26-000013.json", "0000027904-26-000020": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000027904-26-000020.json", "0000027904-26-000022": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000027904-26-000022.json", "0000063908-26-000032": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000063908-26-000032.json", "0000092380-26-000044": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000092380-26-000044.json", "0000764478-25-000057": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000764478-25-000057.json", "0000764478-26-000005": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000764478-26-000005.json", "0000898173-26-000006": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000898173-26-000006.json", "0000940944-25-000038": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000940944-25-000038.json", "0000940944-26-000005": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000940944-26-000005.json", "0000940944-26-000009": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0000940944-26-000009.json", "0001041061-25-000109": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001041061-25-000109.json", "0001041061-26-000003": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001041061-26-000003.json", "0001041061-26-000084": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001041061-26-000084.json", "0001058090-26-000007": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001058090-26-000007.json", "0001104659-25-102611": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001104659-25-102611.json", "0001104659-25-105631": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001104659-25-105631.json", "0001104659-25-118458": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001104659-25-118458.json", "0001104659-26-017090": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001104659-26-017090.json", "0001104659-26-027061": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001104659-26-027061.json", "0001104659-26-032757": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001104659-26-032757.json", "0001171843-26-001288": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/0001171843-26-001288.json", "AAL_2026-04-23T08.30": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/AAL_2026-04-23T08.30.json", "BBY_2026-03-03T08.00": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/BBY_2026-03-03T08.00.json", "CMG_2026-02-03T16.30": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/CMG_2026-02-03T16.30.json", "DAL_2026-04-08T10.00": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/DAL_2026-04-08T10.00.json", "DRI_2026-03-19T08.30": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/DRI_2026-03-19T08.30.json", "MCD_2026-02-11T16.30": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/MCD_2026-02-11T16.30.json", "ULTA_2026-03-12T16.30": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/ULTA_2026-03-12T16.30.json", "YUM_2026-02-04T08.15": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/YUM_2026-02-04T08.15.json", "bzNews_42014391": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/bzNews_42014391.json", "bzNews_49256211": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/bzNews_49256211.json", "bzNews_50877032": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/bzNews_50877032.json", "bzNews_51962983": ".claude/plans/Drivers/experiments/keys/K-fields/draft_inputs/bzNews_51962983.json"}
if (!Array.isArray(EVENTS)) throw new Error('args must be an array')
const ids = EVENTS.map(e => e.source_id)
if (new Set(ids).size !== Object.keys(EXPECTED).length ||
    ids.length !== Object.keys(EXPECTED).length)
  throw new Error(`args must carry EXACTLY the ${Object.keys(EXPECTED).length} locked events, no duplicates`)
for (const e of EVENTS) {
  const want = EXPECTED[e.source_id]
  if (!want) throw new Error(`unknown event ${e.source_id} — not in the locked manifest`)
  const got = e.input_path || e.path
  if (got !== want) throw new Error(`swapped/wrong input for ${e.source_id}: ${got}`)
}
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
