export const meta = {
  name: 'relocate-batch',
  description: 'BATCHED reader A/B: one call binds ALL of a company-period group\'s metrics',
  phases: [{ title: 'BatchBind' }],
}
// #770 batching lever. Same 5 rules + tie-break as relocate.js — the ONLY variable is N
// addresses per call (caps enforced upstream: <=8 cases, <=100KB candidates). Quality bar:
// answers must match the certified one-by-one outputs.
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const DIR = A.dir
const GIDS = A.gids

const SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'integer' },
          found: { type: 'boolean' },
          candidate_index: { type: ['integer', 'null'] },
          value: { type: 'string' },
          quote: { type: 'string' },
          period_evidence: { type: 'string' },
        },
        required: ['id', 'found', 'value', 'quote'],
      },
    },
  },
  required: ['results'],
}

const prompt = (g) =>
  `You re-find SEVERAL company metrics' values for specific periods in ONE set of document excerpts. ` +
  `100% precision is required; abstaining on any metric is correct and expected — never guess.\n\n` +
  `Read ${DIR}/gbatch_${g}.json = {ticker, cases:[{id, kpi, period_type, period_target, address}...], candidates:[...]}.\n` +
  `- Each case's address = that metric's identity from an earlier disclosure: label, caption, siblings, unit, ` +
  `lock_row (how it read in an EARLIER period — RECOGNITION only; its number will differ, never copy it), ` +
  `and possibly measurement ('gaap' = plain unadjusted figure; 'adjusted' = adjusted/non-GAAP; absent = unknown).\n` +
  `- candidates = excerpts from the target document, SHARED by all cases. Each may be a TABLE ROW or a SENTENCE.\n\n` +
  `For EACH case independently, choose the ONE candidate satisfying ALL FIVE rules; if none does, found=false for that case:\n` +
  `1. METRIC KIND — same kind as the address (a profit is not a revenue is not a margin is not a count).\n` +
  `2. SLICE — same segment/geography/product/entity as the address (label + siblings), not a different slice, subtotal, or superset.\n` +
  `3. PERIOD — the number must be the TARGET period: a period_type figure (annual = FULL YEAR; quarterly = a SINGLE ` +
  `three-month quarter, never six-/nine-month or year-to-date) ending period_target. Prove it from a column header ` +
  `OR the sentence's own words; no period evidence -> found=false.\n` +
  `4. CONSISTENCY — if the candidate also shows the EARLIER (lock) period, that figure must agree with lock_row's number.\n` +
  `5. MEASUREMENT — if the text offers BOTH plain/GAAP and adjusted figures, take the one matching address.measurement; ` +
  `unknown measurement + both flavors present -> found=false; explicitly different flavor -> found=false.\n` +
  `TIE-BREAK (never a filter): between two qualifying candidates prefer the one whose section words match address.caption.\n\n` +
  `Per case set: value = ONLY that metric's target-period number; quote = the row/sentence copied VERBATIM IN FULL; ` +
  `period_evidence = the exact words proving the period. Return {results:[one entry per case, same ids]}.`

phase('BatchBind')
const out = await pipeline(GIDS,
  (g) => agent(prompt(g), { label: `gbind:${g}`, phase: 'BatchBind', schema: SCHEMA,
      agentType: 'general-purpose', model: 'sonnet', effort: 'high' })
    .then(r => ({ gid: g, results: (r && r.results) || [] })))
return { groups: out.filter(Boolean) }
