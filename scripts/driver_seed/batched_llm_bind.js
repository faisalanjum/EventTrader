export const meta = {
  name: 'batched-llm-bind',
  description: 'Bind residual fiscal.ai KPIs to verbatim SEC quotes, batched per company-period',
  phases: [{ title: 'Extract' }, { title: 'Verify' }],
}

// args: { path: 'data/driver_catalog_seed/partN/llm_batches.json', lo: 0, hi: 15 }
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PATH = A.path
const LO = A.lo || 0
const HI = A.hi

const CY = `Fetch this company-period's filing corpus (load mcp__neo4j-cypher__read_neo4j_cypher via ToolSearch first). Run BOTH:
(a) 10-Q/10-K XBRL + sections:
  MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) WHERE r.periodOfReport STARTS WITH $period
  OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
  OPTIONAL MATCH (r)-[:HAS_SECTION]->(x:ExtractedSectionContent)
  RETURN elementId(f) AS fid, f.statement_type AS stype, f.value AS xbrl, elementId(x) AS xid, x.section_name AS sec, x.content AS text
(b) the earnings 8-K press release (announce date is 5-75 days AFTER the period end):
  MATCH (r:Report {formType:'8-K'})-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) WHERE r.periodOfReport >= $lo AND r.periodOfReport <= $hi
  MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent) WHERE e.exhibit_number IN ['EX-99.1','EX-99','99.1']
  RETURN elementId(e) AS eid, e.content AS text
  ($lo = period + 5 days, $hi = period + 75 days.)`

const EXTRACT_SCHEMA = {
  type: 'object',
  properties: {
    bindings: { type: 'array', items: { type: 'object', properties: {
      kpi: { type: 'string' },
      found: { type: 'boolean' },
      quote: { type: 'string', description: 'EXACT copy-paste substring of a node content that states this KPI = its value for this period, at FULL precision. Empty if not found.' },
      value_as_written: { type: 'string', description: 'how the number appears verbatim in the quote' },
      source_type: { type: 'string', description: 'financial_statement_table | section_mdna | exhibit_ex99 | none' },
      source_element_id: { type: 'string', description: 'elementId of the node the quote came from' },
    }, required: ['kpi', 'found', 'quote', 'source_type'] } },
  }, required: ['bindings'],
}
const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      kpi: { type: 'string' },
      confirmed: { type: 'boolean', description: 'true ONLY if quote is a literal substring, contains the value at FULL precision bound to THIS metric line (right segment/dimension, not prior-year, not guidance, not a subtotal/superset mislabel, not coarse-rounded). Filer synonyms for the same line are OK.' },
      final_quote: { type: 'string' },
      reason: { type: 'string' },
    }, required: ['kpi', 'confirmed', 'final_quote'] } },
  }, required: ['verdicts'],
}

phase('Extract')
// explicit batch list wins; otherwise the [LO,HI) range
const idx = []
if (Array.isArray(A.idx) && A.idx.length) {
  for (const i of A.idx) idx.push(i)
} else {
  for (let i = LO; i < (HI || LO + 1); i++) idx.push(i)
}

const out = await pipeline(idx,
  (i) => agent(
    `You bind a company's reported KPI values to their EXACT verbatim quote in SEC filings. This seeds a Driver Catalog and demands 100% precision — abstaining is correct when unsure.\n\n` +
    `Read ${PATH} and take the batch at index ${i} (0-based). It has {ticker, form, period, kpis:[{kpi,value,fmt,is_currency}]}. If the file has no such index, return {bindings:[]}.\n\n` +
    `${CY}\n\n` +
    `Then for EACH kpi in the batch, find the ONE exact verbatim quote proving kpi = value for this period. ALL of these are required or you MUST set found=false:\n` +
    `- FULL PRECISION: the quote must contain the target value at every significant digit. A figure rounded to fewer digits does not prove the exact value. If the closest figure in the filing differs from the target value in any digit, that is a mismatch: abstain.\n` +
    `- LABEL REQUIRED: the quote must contain THIS KPI's own line/segment label adjacent to the value. A bare number, or a number picked from an unlabeled multi-number row by column position, does not prove the binding: abstain.\n` +
    `- DISAMBIGUATE: if the same line label is used for more than one segment/entity/period in the filing, the quote must include the qualifier that pins the number to THIS one. A quote that does not uniquely identify this KPI: abstain.\n` +
    `- PRIMARY CURRENT-PERIOD SOURCE ONLY: use the as-filed current-period statement / segment note / press-release table. Do not use prior-year columns, guidance, or pro-forma / recast / restated / multi-period trend schedules whose figures may differ from the as-filed number.\n` +
    `- If you cannot satisfy ALL of the above, set found=false. Many will be absent — abstaining is correct and expected.\n` +
    `Return one binding per kpi with the node's source_element_id.`,
    { label: `extract:${i}`, phase: 'Extract', schema: EXTRACT_SCHEMA, agentType: 'general-purpose',
      model: 'sonnet', effort: 'max' }
  ).then(r => ({ i, extract: r })),
  ({ i, extract }) => {
    const found = (extract && extract.bindings || []).filter(b => b.found && b.quote)
    if (!found.length) return { i, verdicts: [] }
    return agent(
      `Adversarially verify proposed KPI->quote bindings for one company-period. DEFAULT the confirmed flag to FALSE whenever anything is off.\n\n` +
      `Read ${PATH} batch index ${i} for the {ticker, form, period} context. Load mcp__neo4j-cypher__read_neo4j_cypher via ToolSearch. For EACH binding below, re-fetch its node ( MATCH (n) WHERE elementId(n)=$id RETURN n.content, n.value ). Set confirmed=false unless EVERY check passes:\n` +
      `  1. LITERAL SUBSTRING: the quote is a verbatim substring of the node content.\n` +
      `  2. FULL-PRECISION VALUE: the exact target value is literally in the quote at every digit; a figure that differs in any digit (including a shorter rounding) is a mismatch, reject.\n` +
      `  3. LABEL IN QUOTE: the quote contains THIS KPI's own line/segment label adjacent to the value. If it is a bare number or the binding relies on column position in an unlabeled row, reject.\n` +
      `  4. DISAMBIGUATED: if the same label serves another segment/entity/period in the filing, the quote must carry the qualifier pinning it to THIS one; otherwise reject.\n` +
      `  5. PRIMARY CURRENT-PERIOD: as-filed current-period figure, not prior-year, guidance, pro-forma, recast, or trend schedule; not a subtotal/superset mislabel. Faithful filer synonyms for the SAME line are OK.\n\n` +
      `Bindings:\n${JSON.stringify(found.map(b => ({ kpi: b.kpi, quote: b.quote, source_element_id: b.source_element_id, value_as_written: b.value_as_written })))}\n\n` +
      `confirmed=true only if all 5 hold. Trim final_quote to the minimal substring that carries BOTH this KPI's label and its value. When in any doubt, confirmed=false.`,
      { label: `verify:${i}`, phase: 'Verify', schema: VERIFY_SCHEMA, agentType: 'general-purpose',
        model: 'sonnet', effort: 'max' }
    ).then(v => ({ i, extract, verify: v }))
  })

// stitch confirmed bindings
const records = []
for (const r of out.filter(Boolean)) {
  const vmap = {}
  for (const v of (r.verify && r.verify.verdicts || [])) vmap[v.kpi] = v
  for (const b of (r.extract && r.extract.bindings || [])) {
    const v = vmap[b.kpi]
    if (b.found && v && v.confirmed) {
      records.push({ batch: r.i, kpi: b.kpi, tier: 'T3-llm', quote: v.final_quote || b.quote,
        value_as_written: b.value_as_written, source_type: b.source_type, source_element_id: b.source_element_id })
    }
  }
}
const nExtract = out.filter(Boolean).reduce((s, r) => s + ((r.extract && r.extract.bindings || []).filter(b => b.found).length), 0)
return { batches: out.length, extracted_found: nExtract, confirmed: records.length, records }
