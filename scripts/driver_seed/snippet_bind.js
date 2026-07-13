export const meta = {
  name: 'snippet-bind',
  description: 'Bind residual KPIs to quotes from pre-located snippets (no filing reads, no Neo4j)',
  phases: [{ title: 'Bind' }],
}

// args: { path: 'data/driver_catalog_seed/partN/llm_batches.json', lo, hi } or { idx:[...] }
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PATH = A.path
// LOCKED DECISION (2026-07-12): effort = 'high' for BOTH agents. A controlled A/B on 20 batches
// showed 'medium' saves only ~9% tokens but LOSES ~8% recall (missed 7 real KPIs) — rejected,
// because precision AND recall must stay unchanged. Do NOT lower this without a fresh A/B that
// proves recall+precision hold. The bind_effort/verify_effort args exist ONLY for such experiments.
const BIND_EFF = A.bind_effort || 'high'
const VERIFY_EFF = A.verify_effort || 'high'
const idx = []
if (Array.isArray(A.idx) && A.idx.length) { for (const i of A.idx) idx.push(i) }
else { for (let i = (A.lo || 0); i < (A.hi || (A.lo || 0) + 1); i++) idx.push(i) }

const SCHEMA = {
  type: 'object',
  properties: {
    bindings: { type: 'array', items: { type: 'object', properties: {
      kpi: { type: 'string' },
      found: { type: 'boolean' },
      quote: { type: 'string', description: 'The ENTIRE chosen candidate string, copied character-for-character and IN FULL (do not shorten or clip it). Empty if none qualifies.' },
      candidate_index: { type: 'number', description: 'which candidate you used (0-based); -1 if none' },
    }, required: ['kpi', 'found', 'quote'] } },
  }, required: ['bindings'],
}

phase('Bind')
const out = await pipeline(idx,
  (i) => agent(
    `You bind reported company KPIs to the exact verbatim text that states them. 100% precision is required; abstaining is correct and expected.\n\n` +
    `Read ${PATH} and take the batch at index ${i} (0-based): {ticker, form, period, kpis:[{kpi, value, fmt, candidates:[...]}]}. If no such index, return {bindings:[]}.\n` +
    `Each KPI's "candidates" are text excerpts ALREADY located from that company's filing for that period — every one of them literally contains the target value. Your ONLY job is to decide which candidate (if any) actually states THIS KPI, and to copy the quote out of it. Do NOT fetch anything; do NOT use any tools; work solely from the given text.\n\n` +
    `For each kpi, pick the ONE candidate that satisfies ALL of:\n` +
    `- the excerpt contains THIS KPI's own line/segment label positioned next to the target value (not merely somewhere in the excerpt);\n` +
    `- the value is the CURRENT period's figure, not a prior-period comparative column and not a forecast;\n` +
    `- the label is not a different line, a subtotal, or a superset of this KPI;\n` +
    `- if a label is reused for several segments/entities, the excerpt must carry the qualifier pinning it to THIS one.\n\n` +
    `Then set candidate_index to that candidate, and set quote to the ENTIRE candidate string copied IN FULL — the whole excerpt, character-for-character, do NOT shorten or clip it (the full row/headers are what make it verifiable). Do not paraphrase, reorder, or reformat any number.\n` +
    `If no candidate satisfies all of the above, set found=false, quote="", candidate_index=-1. Abstaining on a genuinely ambiguous one is correct.`,
    { label: `bind:${i}`, phase: 'Bind', schema: SCHEMA, agentType: 'general-purpose',
      model: 'sonnet', effort: BIND_EFF }
  ).then(r => ({ i, bindings: (r && r.bindings) || [] })))

// Fix A: the quote is the FULL candidate the model copied (whole row + headers), not a clip.
const need = []
for (const r of out.filter(Boolean))
  for (const b of r.bindings)
    if (b.found && b.quote)
      need.push({ batch: r.i, kpi: b.kpi, quote: b.quote })

// Fix B (cheap verify): one agent per batch re-judges ONLY "is this the right line?" from the
// quote text — no filing read, no Neo4j. Catches wrong-line picks.
phase('Verify')
const VSCHEMA = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object',
  properties: { kpi: { type: 'string' }, correct: { type: 'boolean' } }, required: ['kpi', 'correct'] } } },
  required: ['verdicts'] }
const byBatch = {}
for (const n of need) (byBatch[n.batch] = byBatch[n.batch] || []).push(n)
const verified = await parallel(Object.keys(byBatch).map(bi => () =>
  agent(
    `Verify KPI->quote bindings. For EACH, decide correct=true ONLY if a careful reader of the quote would agree the number is THIS kpi's value for the period — right line/segment (not a neighbouring or prior-period column, not a subtotal/superset). Judge from the quote text alone; do NOT fetch anything.\n\n` +
    JSON.stringify(byBatch[bi].map(n => ({ kpi: n.kpi, quote: n.quote }))),
    { label: `verify:${bi}`, phase: 'Verify', schema: VSCHEMA, agentType: 'general-purpose',
      model: 'sonnet', effort: VERIFY_EFF }
  ).then(v => ({ bi, verdicts: (v && v.verdicts) || [] }))))

const okKpi = {}
for (const v of verified.filter(Boolean))
  for (const d of v.verdicts) if (d.correct) okKpi[`${v.bi}|${d.kpi}`] = true

const records = need
  .filter(n => okKpi[`${n.batch}|${n.kpi}`])
  .map(n => ({ batch: n.batch, kpi: n.kpi, tier: 'T3-llm', quote: n.quote, source_type: 'section' }))
return { batches: out.length, bound_pre_verify: need.length, confirmed: records.length, records }
