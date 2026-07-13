export const meta = {
  name: 'relocate-probe',
  description: 'Blind-relocate a text driver into a DIFFERENT period filing. Two-signal column picker (period TYPE + DATE from the header; no magnitude, no lock-value anchor). Bind + verify, Sonnet high. Never sees the target value.',
  phases: [{ title: 'Bind' }, { title: 'Verify' }],
}
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const IDX = A.idx
const DIR = A.dir

const BSCHEMA = { type: 'object', properties: {
  found: { type: 'boolean' },
  candidate_index: { type: 'number' },
  value: { type: 'string', description: 'ONLY the single target-period number you read, exactly as written (e.g. "6,115" or "$ 768.9 million")' },
  quote: { type: 'string', description: 'the ENTIRE chosen line/row copied in full, character-for-character' },
}, required: ['found', 'value', 'quote'] }
const VSCHEMA = { type: 'object', properties: { correct: { type: 'boolean' } }, required: ['correct'] }

const bindPrompt = (i) =>
  `You re-find ONE company KPI's value in a NEW (target-period) filing, using a stored ADDRESS of where it was disclosed before. 100% precision is required; abstaining is correct and expected.\n\n` +
  `Read ${DIR}/batch_${i}.json = {kpi, period_type, period_target, period_lock, address, candidates:[...]}.\n` +
  `- address: label, caption (title of the table it lived in), siblings (other row-labels in that table), unit, lock_row (an EARLIER period's line — its NUMBER differs from the target; use it ONLY to recognise the right line, never copy its number).\n` +
  `- period_type + period_target: the EXACT period to read — a "period_type" period ending on period_target.\n` +
  `- candidates: excerpts from the TARGET-period filing, each with its caption.\n\n` +
  `Do this in order:\n` +
  `1. TABLE — pick the candidate that is the SAME disclosure as the address: its caption and surrounding row-labels match the address's caption/siblings, AND it contains THIS kpi's own label as a distinct line. If none matches, found=false.\n` +
  `2. LINE — within it, take THIS kpi's own row (its label + unit), not a subtotal, superset, different metric, or different slice.\n` +
  `3. COLUMN — read the value in the column for the TARGET period, using TWO header signals that must BOTH match:\n` +
  `   (a) period TYPE: if period_type is "annual" the column must be a full-year figure ("year ended"/"fiscal year"); if "quarterly" it must be a single three-month quarter ("three months ended") — NOT a six-/nine-month or year-to-date column;\n` +
  `   (b) period DATE: the column whose header names period_target (its year / end-date).\n` +
  `   If a table shows several period lengths (e.g. a quarter column AND a year-to-date column), you MUST take the one whose length matches period_type. If explicit period headers are absent, the most recent period is the first/leftmost value. If you cannot identify the target column with confidence, set found=false.\n\n` +
  `Set value to ONLY that one target-period number, and quote to the ENTIRE row/line copied verbatim IN FULL (character-for-character; do not reformat numbers). The target number differs from lock_row's number.\n` +
  `Return {found, candidate_index, value, quote}.`

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
    if (!r.found) return { ...r, correct: false }
    return agent(verifyPrompt(r.i, r.value, r.quote),
      { label: `verify:${r.i}`, phase: 'Verify', schema: VSCHEMA,
        agentType: 'general-purpose', model: 'sonnet', effort: 'high' })
      .then(v => ({ ...r, correct: !!(v && v.correct) }))
  })
return { records }
