// A7 G1 — THE SHARED GRADER BATCH OWNER.
// One agent() per launcher row, serial, blind. The rendered prompt bytes live
// in this file's own BOUND value — which the publication receipt hashes — and
// the Workflow arguments carry IDENTITY ONLY, so a whole packet can be handed
// to the transport without transcribing a hundred kilobytes of prompt. This
// file never assembles, edits, truncates or re-orders a prompt: it passes the
// exact string it holds, so the bytes the builder froze are the bytes the model
// reads.
//
// IT DELIBERATELY DOES NOT HASH THEM. Prompt integrity is owned ONCE, in the
// Python publication gate: the externally approved receipt hashes this whole
// file including its prompts, preflight refuses if these bytes move, and the
// official state's persisted copy is audited against that same pin afterwards.
// A hash computed HERE would live inside the very file it claims to protect,
// could not survive whole-file replacement, and duplicated stronger evidence -
// and the primitive it needed does not exist in this sandbox anyway, which is
// how it took a real launch down before any agent ran. Do not re-add one.
// Replies return RAW TEXT and there is
// deliberately no `schema:` on the call — a JavaScript-side parse would
// collapse exact values before the Python response owner ever sees them.
//
// BOUND is null in the committed owner and is REPLACED, in the run-specific
// copy the publisher writes, by that run's exact execution identity. A copy
// that still carries null is a live script, not a published one, and refuses.
export const meta = {
  name: 'a7-g1-grade-batch',
  description: 'A7 G1 identity grading: one blind Sonnet 5 high lean-probe read per launcher row',
  phases: [
    { title: 'G1', detail: 'one blind identity reading per launcher row' },
  ],
}
const BOUND = null
const PINNED_MODEL = "sonnet"
const PINNED_EFFORT = "high"
const PINNED_AGENT_TYPE = "lean-probe"
const PINNED_DISALLOWED_TOOLS = ["Read"]
const RUNTIME_MODEL_ID = "claude-sonnet-5"
const MAX_OUTPUT_TOKENS_SETTING = "128000"
// THE EXACT ARGUMENT SHAPE. A missing key and an extra key are both refusals:
// arguments nobody published are not this run's, and a stray `prompt` key would
// reintroduce the very bytes this file is here to hold.
const ARG_KEYS = ["agentType", "attempt", "batch_id", "candidate_sha256",
                  "disallowedTools", "effort", "lane_id", "max_output_tokens",
                  "model", "ordinal", "prompt_sha256", "runtime_model_id"]

const ROWS = typeof args === 'string' ? JSON.parse(args) : args
if (!Array.isArray(ROWS) || ROWS.length === 0) {
  throw new Error('grade_batch expects a non-empty array of launcher rows')
}
for (const row of ROWS) {
  if (row === null || typeof row !== 'object' || Array.isArray(row)) {
    throw new Error('a launcher row is not an object')
  }
  const keys = Object.keys(row).sort()
  if (keys.length !== ARG_KEYS.length ||
      !keys.every((k, i) => k === ARG_KEYS[i])) {
    throw new Error(`launcher row carries [${keys}], not the published argument keys`)
  }
  for (const field of ['batch_id', 'lane_id', 'prompt_sha256',
                       'candidate_sha256']) {
    if (typeof row[field] !== 'string' || row[field].length === 0) {
      throw new Error(`launcher row is missing ${field}`)
    }
  }
  if (!Number.isInteger(row.ordinal) || !Number.isInteger(row.attempt)) {
    throw new Error(`launcher row ${row.lane_id} carries no ordinal/attempt`)
  }
}
// THE PUBLISHED EXECUTION IDENTITY, checked BEFORE the first call and again
// before every later one. A run-specific copy that is handed rows from another
// publication, another candidate or another attempt refuses rather than
// spending anything.
if (BOUND === null) {
  throw new Error('this is the unbound owner; run the published run-specific copy')
}
const samePins = (row) =>
  row.model === PINNED_MODEL && row.effort === PINNED_EFFORT &&
  row.agentType === PINNED_AGENT_TYPE &&
  row.runtime_model_id === RUNTIME_MODEL_ID &&
  row.max_output_tokens === MAX_OUTPUT_TOKENS_SETTING &&
  Array.isArray(row.disallowedTools) &&
  row.disallowedTools.length === PINNED_DISALLOWED_TOOLS.length &&
  row.disallowedTools.every((t, i) => t === PINNED_DISALLOWED_TOOLS[i])
// -> the exact prompt bytes for this row, or it throws and nothing is sent.
const bind = (row, index) => {
  if (row.candidate_sha256 !== BOUND.candidate_sha256 ||
      row.batch_id !== BOUND.batch_ids[index] ||
      row.attempt !== BOUND.attempt) {
    throw new Error(`launcher row ${row.lane_id} is not part of this publication`)
  }
  if (!samePins(row)) {
    throw new Error(`launcher row ${row.lane_id} does not carry the frozen lane`)
  }
  if (row.prompt_sha256 !== BOUND.prompt_sha256[index]) {
    throw new Error(`launcher row ${row.lane_id} is paired with another row's prompt`)
  }
  const prompt = BOUND.prompts[index]
  if (typeof prompt !== 'string' || prompt.length === 0) {
    throw new Error(`launcher row ${row.lane_id} binds no prompt`)
  }
  return prompt
}
if (ROWS.length !== BOUND.lane_ids.length) {
  throw new Error(`this publication has ${BOUND.lane_ids.length} rows, not ${ROWS.length}`)
}
// ONE BOUND PROMPT PER PUBLISHED ROW, or there is no run: a short, long or
// re-ordered prompt list would silently pair bytes with the wrong identity.
if (!Array.isArray(BOUND.prompts) ||
    BOUND.prompts.length !== ROWS.length ||
    BOUND.prompt_sha256.length !== ROWS.length) {
  throw new Error(`this publication binds ${Array.isArray(BOUND.prompts) ? BOUND.prompts.length : 'no'} prompts for ${ROWS.length} rows`)
}
for (let i = 0; i < ROWS.length; i += 1) {
  if (ROWS[i].lane_id !== BOUND.lane_ids[i] ||
      ROWS[i].ordinal !== BOUND.ordinals[i] ||
      ROWS[i].batch_id !== BOUND.batch_ids[i] ||
      ROWS[i].prompt_sha256 !== BOUND.prompt_sha256[i]) {
    throw new Error(`row ${i} is not the published row ${BOUND.lane_ids[i]}`)
  }
  bind(ROWS[i], i)
}

// SERIAL BY LAW. Exactly one agent() is outstanding at a time, and a row that
// comes back without a string stops this invocation rather than letting a
// later row be launched from evidence nobody audited.
const results = []
for (let index = 0; index < ROWS.length; index += 1) {
  const row = ROWS[index]
  let text = null
  let error = null
  const prompt = bind(row, index)         // again, immediately before the call
  try {
    text = await agent(prompt, {
      // the label IS the lane id, exactly: a truncated label cannot bind an
      // official per-agent transcript row back to the batch that was scheduled
      label: row.lane_id,
      phase: 'G1',
      model: PINNED_MODEL,
      effort: PINNED_EFFORT,
      agentType: PINNED_AGENT_TYPE,
      disallowedTools: PINNED_DISALLOWED_TOOLS,
    })
  } catch (e) {
    // PRESERVE THE FAILURE. Collapsing an agent exception into a bare null
    // destroys the only evidence of WHY a paid row produced nothing, and the
    // response owner then cannot tell a refusal from a transport fault.
    text = null
    error = String((e && e.message) || e)
  }
  results.push({
    batch_id: row.batch_id,
    lane_id: row.lane_id,
    ordinal: row.ordinal,
    attempt: row.attempt,
    model: PINNED_MODEL,
    effort: PINNED_EFFORT,
    agentType: PINNED_AGENT_TYPE,
    runtime_model_id: RUNTIME_MODEL_ID,
    // EVERY lane pin travels back, so the response owner can bind what was
    // actually asked rather than trusting the row that asked it
    disallowedTools: PINNED_DISALLOWED_TOOLS,
    max_output_tokens: MAX_OUTPUT_TOKENS_SETTING,
    prompt_sha256: row.prompt_sha256,
    candidate_sha256: row.candidate_sha256,
    // the invocation hash is the PUBLICATION's, not a claim the row
    // makes about itself - a row cannot carry the hash of the file it
    // is inside
    invocation_sha256: BOUND.invocation_sha256,
    text: typeof text === 'string' ? text : null,
    error: error,
  })
  if (typeof text !== 'string') break
}
log(`graded ${results.length} of ${ROWS.length} launcher rows`)
return { rows: ROWS.length, calls: results.length, results: results }
