// K-fields A1 — ONE LAUNCHER PER FROZEN SOURCE EVENT.
// The whole-plan script was 17,161,588 bytes and the Workflow transport rejects
// any script at or over 524,288 bytes before args or calls (Core 1019), so the
// plan is sliced by source event. The stable instructions + menu + event are
// stored ONCE as HEAD; each packet stores only its own item text. Every agent
// still receives the EXACT full assembled prompt: HEAD + that item slice, whose
// sha256 the bundle pins.
// Replies return RAW TEXT. There is deliberately no `schema:` on any agent call:
// it would make the workflow parse the reply in JavaScript, whose doubles
// collapse exact numbers before Python ever sees them.
export const meta = {
  name: 'kfields-a1-one-item',
  description: 'K-fields A1: one already-located item per packet, read twice by blind Sonnet 5 high lean-probe lanes',
  phases: [
    { title: 'Draft-L1', detail: 'first blind read, one per packet' },
    { title: 'Draft-L2', detail: 'second blind read, one per packet' },
  ],
}
__SLICE__
// THE GATE IS A RECEIPT, NOT A HABIT. This committed file carries RECEIPT=null
// and therefore cannot call anything. Only the run coordinator, and only after
// a preflight that passed for THIS fresh run directory and these exact frozen
// bytes, writes a run-specific copy with the receipt filled in. A direct run of
// the generic launcher makes zero calls (Codex SEQ 1313 item 5 / E).
if (RECEIPT === null || typeof RECEIPT !== 'object')
  throw new Error('refusing to call: no preflight receipt - run the coordinator, not this file')
if (RECEIPT.source_id !== SOURCE_ID) throw new Error(`receipt is for ${RECEIPT.source_id}, this launcher is ${SOURCE_ID}`)
if (RECEIPT.input_sha256 !== INPUT_SHA) throw new Error('receipt input hash does not match this launcher')
if (!Array.isArray(RECEIPT.allowed) || RECEIPT.allowed.length === 0)
  throw new Error('receipt names no allowed calls')

const PACKETS = typeof args === 'string' ? JSON.parse(args) : args
if (!Array.isArray(PACKETS) || PACKETS.length === 0) throw new Error('args must be a non-empty array')

const ATTEMPT = PACKETS[0].attempt === undefined ? 1 : PACKETS[0].attempt
if (!ALLOWED_ATTEMPTS.includes(ATTEMPT))
  throw new Error(`refusing to call: attempt ${JSON.stringify(ATTEMPT)} is not one of ${JSON.stringify(ALLOWED_ATTEMPTS)}`)
if (RECEIPT.attempt !== ATTEMPT) throw new Error(`receipt is for attempt ${RECEIPT.attempt}, args say ${ATTEMPT}`)
// THE OUTPUT SETTING IS PROVED BY THE GATE, NOT READ HERE. The Workflow VM has
// no `process` and no `process.env` (official zero-agent run wf_6b9b6293-5aa),
// so reading it made the launcher refuse before its first agent EVERY time -
// and only a fake runner that injected `process` could hide that. The Python
// preflight reads the real environment; the receipt carries what it saw.
if (RECEIPT.max_output_tokens !== MAX_OUTPUT_TOKENS_SETTING)
  throw new Error(`receipt records ${JSON.stringify(RECEIPT.max_output_tokens)} for the output setting, not ${MAX_OUTPUT_TOKENS_SETTING} - the gate that saw it did not authorise this run`)

// THE EXACT CALL SUBSET. A retry of one (packet, lane) must run that one call -
// expanding it to the whole event, or to the sibling lane, spends calls nobody
// approved (Codex SEQ 1313 item 4). Each arg names a packet and MAY name one
// lane; without a lane the packet's planned lanes all run.
const allowed = new Set(RECEIPT.allowed.map(p => `${p[0]} ${p[1]}`))
const CALLS = []
const seenArg = new Set()
for (const p of PACKETS) {
  if (!(p.packet_id in ITEMS)) throw new Error(`unknown packet ${p.packet_id} - not in this locked slice`)
  if (p.source_id !== SOURCE_ID) throw new Error(`packet ${p.packet_id} is not from ${SOURCE_ID}`)
  const got = p.input_path || p.path
  if (got !== INPUT_PATH) throw new Error(`swapped/wrong input for ${p.packet_id}: ${got}`)
  const a = p.attempt === undefined ? 1 : p.attempt
  if (a !== ATTEMPT) throw new Error(`packet ${p.packet_id} carries attempt ${a}, the launch is attempt ${ATTEMPT}`)
  const lanes = LANES[p.packet_id]
  if (!Array.isArray(lanes) || lanes.length !== EXPECTED_LANES_PER_PACKET)
    throw new Error(`packet ${p.packet_id} does not carry exactly ${EXPECTED_LANES_PER_PACKET} lanes`)
  const wanted = p.lane_id === undefined ? lanes : lanes.filter(l => l.lane_id === p.lane_id)
  if (wanted.length === 0) throw new Error(`packet ${p.packet_id} has no lane ${p.lane_id}`)
  for (const lane of wanted) {
    const sig = `${p.packet_id} ${lane.lane_id}`
    if (seenArg.has(sig)) throw new Error(`args repeat call ${lane.lane_id}`)
    seenArg.add(sig)
    if (!allowed.has(sig)) throw new Error(`call ${lane.lane_id} is not in the preflight receipt`)
    if (lane.model !== PINNED_MODEL || lane.effort !== PINNED_EFFORT || lane.agentType !== PINNED_AGENT_TYPE)
      throw new Error(`packet ${p.packet_id} lane ${lane.lane_id} is not the pinned ${PINNED_MODEL}/${PINNED_EFFORT}/${PINNED_AGENT_TYPE}`)
    CALLS.push({ packet_id: p.packet_id, lane })
  }
}
// EXACT EQUALITY, not "no more than". A receipt allowing 14 calls accepted args
// naming one packet and made two calls with no error (Codex SEQ 1314 item 2):
// a strict subset is as wrong as an extra, because nobody authorised THIS run.
if (CALLS.length !== RECEIPT.allowed.length)
  throw new Error(`args compute ${CALLS.length} calls, the receipt allows exactly ${RECEIPT.allowed.length}`)
for (const sig of allowed)
  if (!seenArg.has(sig)) throw new Error(`the receipt allows ${sig}, which these args do not request`)

const prompt = (pid) => {
  const slice = ITEMS[pid]
  if (slice === undefined) throw new Error(`no item slice for ${pid}`)
  return HEAD + slice
}
// SERIAL BY LAW (Codex SEQ 1355 item 3). The frozen CALLS list, its order and
// every row below are unchanged; only the number in flight is. A whole slice
// launched at once is what the service refused, so exactly one agent() is
// outstanding at a time. A call that comes back without a string keeps its
// attempted row as failed evidence and NO later call is launched from this
// invocation - the audit refuses that row rather than the run guessing.
const results = []
for (const call of CALLS) {
  let text = null
  try {
    text = await agent(prompt(call.packet_id), {
      // the label IS the lane id, exactly: a truncated label cannot bind an
      // official per-agent transcript row back to the call that was scheduled
      label: call.lane.lane_id,
      phase: call.lane.lane_id.endsWith('/L1') ? 'Draft-L1' : 'Draft-L2',
      model: call.lane.model, effort: call.lane.effort,
      agentType: call.lane.agentType,
      disallowedTools: PINNED_DISALLOWED_TOOLS,
    })
  } catch (e) {
    text = null
  }
  results.push({
    packet_id: call.packet_id, source_id: SOURCE_ID,
    lane_id: call.lane.lane_id, model: call.lane.model,
    effort: call.lane.effort, agentType: call.lane.agentType,
    attempt: ATTEMPT, runtime_model_id: RUNTIME_MODEL_ID,
    input_sha256: INPUT_SHA, prompt_sha256: PROMPT_SHA[call.packet_id],
    text: typeof text === 'string' ? text : null,
  })
  if (typeof text !== 'string') break
}
const rows = results.filter(Boolean)
log(`drafted ${rows.length} calls for ${SOURCE_ID} at attempt ${ATTEMPT}`)
return { source_id: SOURCE_ID, packets: PACKETS.length, calls: rows.length, results: rows }
