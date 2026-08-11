export const meta = {
  name: 'ab-lean',
  description: 'A/B: general-purpose vs lean-probe on the SAME real batches (per-batch files), same bind+verify logic. Tests recall parity + token saving.',
  phases: [{ title: 'GP-bind' }, { title: 'GP-verify' }, { title: 'Lean-bind' }, { title: 'Lean-verify' }],
}
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const IDX = A.idx
const DIR = 'data/driver_catalog_seed/part1/test_batches'

const BSCHEMA = { type: 'object', properties: { bindings: { type: 'array', items: { type: 'object', properties: {
  kpi: { type: 'string' }, found: { type: 'boolean' }, quote: { type: 'string' } }, required: ['kpi', 'found', 'quote'] } } }, required: ['bindings'] }
const VSCHEMA = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
  kpi: { type: 'string' }, correct: { type: 'boolean' } }, required: ['kpi', 'correct'] } } }, required: ['verdicts'] }

const bindPrompt = (i) =>
  `You bind reported company KPIs to the exact verbatim text that states them. 100% precision is required; abstaining is correct and expected.\n\n` +
  `Read ${DIR}/batch_${i}.json — it is {ticker, form, period, kpis:[{kpi, value, fmt, candidates:[...]}]}.\n` +
  `Each KPI's "candidates" are text excerpts ALREADY located from that company's filing — every one literally contains the target value. Decide which candidate (if any) actually states THIS KPI and copy the quote out of it. Do NOT fetch anything else.\n\n` +
  `For each kpi pick the ONE candidate whose excerpt contains THIS KPI's own line/segment label next to the target value, is the CURRENT period's figure (not a prior-period column, not a forecast), is not a different line / subtotal / superset, and (if a label is reused across segments) carries the qualifier pinning it to THIS one.\n` +
  `Set quote to the ENTIRE chosen candidate copied IN FULL (whole row/headers, character-for-character; do not shorten). If none qualifies set found=false, quote="". Abstaining on a genuinely ambiguous one is correct.`

const verifyPrompt = (items) =>
  `Verify KPI->quote bindings. For EACH, correct=true ONLY if a careful reader of the quote would agree the number is THIS kpi's value for the period — right line/segment (not a neighbouring or prior-period column, not a subtotal/superset). Judge from the quote text alone; do NOT fetch anything.\n\n` +
  JSON.stringify(items)

async function arm(name, bindPhase, verifyPhase, agentType) {
  const binds = await pipeline(IDX,
    (i) => agent(bindPrompt(i), { label: `${name}-bind:${i}`, phase: bindPhase, schema: BSCHEMA, agentType, model: 'sonnet', effort: 'high' })
      .then(r => ({ i, bindings: (r && r.bindings || []).filter(b => b.found && b.quote) })),
    ({ i, bindings }) => {
      if (!bindings.length) return { i, bindings: [], verdicts: [] }
      return agent(verifyPrompt(bindings.map(b => ({ kpi: b.kpi, quote: b.quote }))),
        { label: `${name}-verify:${i}`, phase: verifyPhase, schema: VSCHEMA, agentType, model: 'sonnet', effort: 'high' })
        .then(v => ({ i, bindings, verdicts: (v && v.verdicts || []) }))
    })
  const recs = []
  for (const r of binds.filter(Boolean)) {
    const ok = {}; for (const d of r.verdicts) if (d.correct) ok[d.kpi] = true
    for (const b of r.bindings) if (ok[b.kpi]) recs.push({ batch: r.i, kpi: b.kpi, quote: b.quote })
  }
  return recs
}

const gp = await arm('gp', 'GP-bind', 'GP-verify', 'general-purpose')
const lean = await arm('lean', 'Lean-bind', 'Lean-verify', 'lean-probe')
return { gp_confirmed: gp.length, lean_confirmed: lean.length, gp, lean }
