export const meta = {
  name: 'relocate-probe',
  description: 'Blind-relocate a text driver into a DIFFERENT period filing. Two-signal column picker (period TYPE + DATE from the header; no magnitude, no lock-value anchor). Bind + verify, Sonnet high. Never sees the target value.',
  phases: [{ title: 'Bind' }, { title: 'Verify' }],
}
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const IDX = A.idx
const DIR = A.dir
const BIND_ONLY = A.bind_only        // skip verify (net-negative) — grade the raw bind during iteration

const BSCHEMA = { type: 'object', properties: {
  found: { type: 'boolean' },
  candidate_index: { type: 'number' },
  value: { type: 'string', description: 'ONLY the single target-period number you read, exactly as written (e.g. "6,115" or "$ 768.9 million")' },
  quote: { type: 'string', description: 'the ENTIRE chosen line/row/sentence copied in full, character-for-character' },
  period_evidence: { type: 'string', description: 'the exact header words or sentence phrase that prove the number is the TARGET period; "" if abstaining' },
}, required: ['found', 'value', 'quote'] }
const VSCHEMA = { type: 'object', properties: { correct: { type: 'boolean' } }, required: ['correct'] }

const bindPrompt = (i) =>
  `You re-find ONE company metric's value for a specific period in a NEW document. 100% precision is required; abstaining is correct and expected — never guess.\n\n` +
  `Read ${DIR}/batch_${i}.json = {kpi, period_type, period_target, address, candidates:[...]}.\n` +
  `- address = the metric's identity from an earlier disclosure: label, caption, siblings (labels near it), unit, lock_row (how it read in an EARLIER period — for RECOGNITION only; its number will differ, never copy it).\n` +
  `- candidates = excerpts from the target document. Each may be a TABLE ROW or a plain SENTENCE — the rules below apply the same way to both.\n\n` +
  `Choose the ONE candidate that satisfies ALL FOUR; if none does, found=false:\n` +
  `1. METRIC KIND — the SAME kind as the address: a profit is not a revenue is not a margin is not a count; and "adjusted"/"organic"/"non-GAAP" vs the plain GAAP figure is part of the identity — do not swap them.\n` +
  `2. SLICE — the SAME segment / geography / product / entity as the address (matching its label + siblings), not a different slice, a subtotal, or a superset.\n` +
  `3. PERIOD — the number must be the TARGET period: a ${'`'}period_type${'`'} figure (annual = a FULL YEAR; quarterly = a SINGLE three-month quarter, never a six-/nine-month or year-to-date figure) for the period ending period_target. Prove it from EITHER a column header OR the sentence's own words (e.g. "for fiscal 2025", "in the quarter ended June 30"). If you cannot see period evidence, found=false — do NOT default to the first, largest, or leftmost number.\n` +
  `4. CONSISTENCY — if the candidate also shows the EARLIER (lock) period, that earlier figure must agree with lock_row's number; if it clearly disagrees, this is a different line → found=false.\n\n` +
  `Set value to ONLY the target-period number; quote to the ENTIRE row/sentence copied verbatim IN FULL (character-for-character; do not reformat numbers); period_evidence to the exact header words or phrase proving the period.\n` +
  `Return {found, candidate_index, value, quote, period_evidence}.`

const verifyPrompt = (i, value, quote) =>
  `Verify one KPI->value binding for a specific period. Read ${DIR}/batch_${i}.json for {kpi, period_type, period_target, address} (context only).\n` +
  `Proposed value: ${JSON.stringify(value)}\nProposed quote: ${JSON.stringify(quote)}\n\n` +
  `Set correct=true ONLY if ALL hold, judging from the text alone (do NOT fetch anything else):\n` +
  `- LINE: the quote is THIS kpi — same metric AND same slice as the address (its label/caption/siblings), same unit — not a look-alike, subtotal, superset, or different metric.\n` +
  `- COLUMN: the proposed value is the column for the TARGET period by BOTH header signals — the period_type length (annual = full year; quarterly = a single three-month quarter, NOT six-/nine-month/year-to-date) AND the period_target date — and value is that column's number, not a neighbouring period's.\n` +
  `If anything is uncertain, correct=false.`

phase('Bind')
const records = await pipeline(IDX,
  (i) => agent(bindPrompt(i), { label: `bind:${i}`, phase: 'Bind', schema: BSCHEMA,
      agentType: 'general-purpose', model: 'sonnet', effort: 'high' })
    .then(r => ({ i, found: !!(r && r.found && r.quote && r.value), quote: (r && r.quote) || '',
                  value: (r && r.value) || '', candidate_index: (r && r.candidate_index) })),
  (r) => {
    if (BIND_ONLY) return { ...r, correct: r.found }
    if (!r.found) return { ...r, correct: false }
    return agent(verifyPrompt(r.i, r.value, r.quote),
      { label: `verify:${r.i}`, phase: 'Verify', schema: VSCHEMA,
        agentType: 'general-purpose', model: 'sonnet', effort: 'high' })
      .then(v => ({ ...r, correct: !!(v && v.correct) }))
  })
return { records }
