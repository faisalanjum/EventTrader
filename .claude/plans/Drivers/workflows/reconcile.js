export const meta = {
  name: 'driver-reconcile',
  description: 'Step 2 reconcile over a per-industry seed catalog (args.run_id = the exact menu_build run; reads runs/<run_id>/seed.json, writes catalog.json + approved.json + decisions.json + validation.txt there): (Dedup) canonical + reversible SAME_AS for exact-same-meaning only = the REUSE arm; (Gate) independent admit/rewrite/skip per DriverOntology; (Refute) skeptic breaks bad SAME_AS + meaning-changing rewrites; (Assemble) DETERMINISTIC CODE writes the catalog (assemble_catalog.py ports the 5-way precedence; HierarchicalCatalogPlan §11.19 — the writer cannot fabricate a fusion); (Validate) incl. the D1 fusion-approval check. Review-file only; no graph writes; no merges/deletes. Roll-up/rewrite targets must be COINED names.',
  phases: [ { title: 'Guard', detail: '§11.11 SEED_MAX measure; over caps → deterministic name-sorted review batches (cross-batch SAME_AS = accepted residual)' }, { title: 'Review', detail: 'dedup proposer + independent gate, in parallel (per batch)' }, { title: 'Refute', detail: 'independent skeptic breaks bad SAME_AS + meaning-changing rewrites; JS filters them out' }, { title: 'SameName', detail: 'leaf flag-triggered D5 (rare): review flagged mixed-meaning unions → SAME(Refute-confirmed)/DIFFERENT(split+mini-gate)/UNCLEAR(park)' }, { title: 'Assemble', detail: 'JS lists → decisions.json (+ same_name_review.json) → assemble_catalog.py (code writes catalog.json + approved.json, prints sha)' }, { title: 'Validate', detail: 'deterministic structure check incl. D1 fusion-approval (zero judgment); HARD-FAIL if broken' } ],
}

const DIR    = '/home/faisal/EventMarketDB/.claude/plans/Drivers'
const PY     = '/home/faisal/EventMarketDB/venv/bin/python3'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})   // harness may stringify args
const RUN_ID = A.run_id || ''
if (!RUN_ID) throw new Error('reconcile.js requires args.run_id (e.g. "2026-06-07_143205_restaurants" from menu_build). Refusing to guess "latest".')
const RUN_DIR = `${DIR}/runs/${RUN_ID}`
const SEED = `${RUN_DIR}/seed.json`
const CAT  = `${RUN_DIR}/catalog.json`
const ONT  = `${DIR}/DriverOntology.md`
const EXACT_MEANING_RULE = `For any proposed SAME_AS, reuse, or rewrite, first verify all three are true:
1. same object or metric
2. same scope
3. same mechanism

If any one is false or unclear, do not SAME_AS, reuse, or rewrite. Keep the names separate, admit separately, or skip.
A rewrite may only change wording. It must not change the underlying driver.`

const evidenceRule = (f) => `EVIDENCE: each driver_name is ONE catalog[] record in ${f}, with evidence_refs[] = [{company, source_type, source_id, date, quote}] (one entry per company/event that coined it). Judge from the EVIDENCE, not the bare name string. If evidence is missing, vague, or MIXED (the quotes show different meanings across companies), do not fold or admit blindly — keep separate or skip. If evidence is MIXED, PREFER keep-separate over rewrite, unless the rewrite is ONLY a wording fix (never one that changes meaning).`

const MIXED_FLAGS = { type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','why','n_companies'], properties:{ driver_name:{type:'string'}, why:{type:'string'}, n_companies:{type:'integer'} }}, description:'flag-triggered D5: names whose OWN evidence shows TWO+ different real-world meanings (a mixed same-name union); [] if none' }

const DEDUP_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_links','rejected_pairs','mixed_flags','notes'], properties:{
  mixed_flags: MIXED_FLAGS,
    same_as_links:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, why:{type:'string'} }}, description:'reversible SAME_AS: exact same meaning only; canonical MUST be a coined driver_name'},
  rejected_pairs:{type:'array', items:{type:'object', additionalProperties:false, required:['a','b','why_kept_separate'], properties:{ a:{type:'string'}, b:{type:'string'}, why_kept_separate:{type:'string'} }}, description:'looked similar but failed the exact-meaning rule -> NOT linked'},
  notes:{type:'array', items:{type:'string'}} } }

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts','mixed_flags'], properties:{
  mixed_flags: MIXED_FLAGS,
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{ driver_name:{type:'string'}, verdict:{type:'string', enum:['admit','rewrite','skip'], description:'admit | rewrite | skip'}, rewrite_to:{type:'string', description:'target name if verdict=rewrite (MUST be a coined driver_name), else ""'}, reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true, description:'admit/rewrite/skip totals'} } }

const REFUTE_SCHEMA = { type:'object', additionalProperties:false, required:['same_as_verdicts','rewrite_verdicts'], properties:{
  same_as_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['canonical','variant','survives','why'], properties:{ canonical:{type:'string'}, variant:{type:'string'}, survives:{type:'boolean', description:'TRUE only if you CANNOT refute they are the EXACT same object AND scope AND mechanism; any doubt = FALSE'}, why:{type:'string'} }}},
  rewrite_verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','rewrite_to','survives','why'], properties:{ driver_name:{type:'string'}, rewrite_to:{type:'string'}, survives:{type:'boolean', description:'TRUE only if the rewrite is provably WORDING-ONLY (identical meaning); any change of object/scope/mechanism = FALSE'}, why:{type:'string'} }}} } }

const ASSEMBLE_SCHEMA = { type:'object', additionalProperties:false, required:['ok','sha_line'], properties:{
  ok:{type:'boolean'}, sha_line:{type:'string', description:'the exact ASSEMBLED... line printed by assemble_catalog.py (or the exact error output if ok=false)'} } }

phase('Guard')
// §11.11 SEED_MAX guard — deterministic, BEFORE any AI call (fail-close; sub-split required if it trips).
const GUARD_SCHEMA = { type:'object', additionalProperties:false, required:['records','chars','ok'], properties:{ records:{type:'integer'}, chars:{type:'integer'}, ok:{type:'boolean'} } }
const guard = await agent(`Run these with Bash, in order. Step 0 — BILLING GUARD (subscription-only hard condition): test -z "$ANTHROPIC_API_KEY" || { echo "BILLING-GUARD FAIL: ANTHROPIC_API_KEY present in env — refusing to run (subscription-only policy, CLAUDE.md)"; exit 9; }
If step 0 prints BILLING-GUARD FAIL, STOP and return records=-1, chars=-1, ok=false. Otherwise run this EXACT command and return the printed JSON fields verbatim:
${PY} -c "import json;d=json.load(open('${SEED}'));c=d.get('catalog') or [];s=len(json.dumps(c,separators=(',',':'),ensure_ascii=False));print(json.dumps({'records':len(c),'chars':s,'ok':len(c)<=400 and s<=300000}))"`, {schema:GUARD_SCHEMA, model:'opus', label:'seed-max-guard', phase:'Guard'})
if (!guard || guard.records < 0) throw new Error('BILLING-GUARD: ANTHROPIC_API_KEY present in env (or guard agent died) — refusing to run; subscription-only policy (CLAUDE.md).')
let BATCH_FILES = [SEED]
if (!guard.ok) {
  // §11.11 sub-split: name-sorted contiguous review batches (records are already sorted by driver_name).
  // Cross-batch SAME_AS misses = the ACCEPTED residual (under-merge, safe direction; late-duplicate repair
  // is the catch-up). Assembly + validation still run over the WHOLE seed (code has no size limit).
  const SLICE_SCHEMA = { type:'object', additionalProperties:false, required:['ok','files','notes'], properties:{ ok:{type:'boolean'}, files:{type:'array', items:{type:'string'}}, notes:{type:'string'} } }
  const slice = await agent(`Run this EXACT script with Bash (deterministic slicing of the seed into review batches under the §11.11 caps):
${PY} - <<'EOF'
import json
d=json.load(open('${SEED}'))
recs=d.get('catalog') or []
batches,cur,chars=[],[],0
for r in recs:
    s=len(json.dumps(r,separators=(',',':'),ensure_ascii=False))
    if cur and (len(cur)>=400 or chars+s>300000):
        batches.append(cur); cur,chars=[],0
    cur.append(r); chars+=s
if cur: batches.append(cur)
files=[]
for i,b in enumerate(batches,1):
    p='${RUN_DIR}/seed_batch_%03d.json'%i
    open(p,'w').write(json.dumps({'industry':d.get('industry'),'catalog':b,'analysis':{}},indent=1,ensure_ascii=False)+'\\n')
    files.append(p)
print(json.dumps({'files':files,'sizes':[len(b) for b in batches]}))
EOF
Return ok=true + files (exact list from the printed JSON), notes = the sizes. Non-zero exit: ok=false, files=[], notes = the exact error.`, {schema:SLICE_SCHEMA, model:'opus', label:'slice', phase:'Guard'})
  if (!slice.ok || !slice.files.length) throw new Error(`seed slicing failed: ${slice.notes}`)
  BATCH_FILES = slice.files
  log(`SEED over §11.11 caps (records=${guard.records}, chars=${guard.chars}) → ${BATCH_FILES.length} name-sorted review batches; cross-batch SAME_AS = accepted residual`)
}

phase('Review')
const norm = s => (s||'').trim().toLowerCase()
const survivingLinks = [], appliedRewrites = [], parkedRewrites = [], allGateVerdicts = [], allMixedFlags = []
for (let bi = 0; bi < BATCH_FILES.length; bi++) {
  const bf = BATCH_FILES[bi]
  const tag = BATCH_FILES.length > 1 ? ` [batch ${bi + 1}/${BATCH_FILES.length}]` : ''
  const batchNote = BATCH_FILES.length > 1 ? ' (This file is ONE name-sorted batch of a larger seed — judge only what is in it.)' : ''
  const [dedup, gate] = await parallel([
    () => agent(`Read ${ONT} (the rules) and ${bf} — it is { catalog:[ {driver_name, canonical_name, companies, evidence_refs:[{company,source_type,source_id,date,quote}], optional_links} ] }. The driver_names are already DISTINCT (one record each).${batchNote}
TASK = propose final reversible SAME_AS links over them. STRICT rules:
- ${EXACT_MEANING_RULE}
- ${evidenceRule(bf)}
- NEVER link names with different scopes, brands, segments, geographies, objects, metrics, or mechanisms. List those under rejected_pairs with why.
- FLAG-TRIGGERED D5 (rare): if ONE record's OWN evidence quotes show TWO+ DIFFERENT real-world meanings (a same-name union of different causes across companies), add it to mixed_flags [{driver_name, why, n_companies}] — a separate review will split or park it. Flag ONLY genuinely mixed-meaning unions; same-meaning convergence across companies is GOOD and never flagged. mixed_flags=[] if none.
- For each link pick the CANONICAL (shortest standard form, R6 — and it MUST be one of the COINED driver_names in the catalog, never an invented name) + the variant. Reversible only; never delete or merge nodes.
Return DEDUP_SCHEMA.`, {schema:DEDUP_SCHEMA, model:'opus', label:`dedup${tag}`, phase:'Review'}),
    () => agent(`You are an INDEPENDENT admission gate — judge each name FRESH and skeptically; do NOT assume the producer that coined it was right. Read ${ONT} and the catalog[] records in ${bf} (each = {driver_name, companies, evidence_refs}).${batchNote}
THE ONE TEST: is this a VALID, REUSABLE, consistently-nameable Driver? Give EACH driver_name ONE verdict:
- admit = a valid reusable cause that follows every rule. (Brand/segment-specific names ARE valid drivers — admit them.)
- rewrite = right driver, fixable WORDING-ONLY rule-break; give rewrite_to. It must NOT change the meaning AND must be a name some company already coined (an existing driver_name in the catalog). If no coined clean form exists, admit as-is or skip — do NOT invent a new name.
- skip = vague, rule-breaking, or tied to ONE specific event/date/quarter/headline (NOT a reusable class).
  Reusability is about the CLASS, not the count: a reusable event class (e.g. government_shutdown, food_safety_incident, goodwill_impairment, ceo_change) is ADMITTED even if it appears once; only a name bound to a single instance (e.g. q1_2026_shutdown_effect) is skipped.
${EXACT_MEANING_RULE}
${evidenceRule(bf)}
Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; if it is a valid reusable driver, admit it. KEEP brand/segment-specific names.
FLAG-TRIGGERED D5 (rare): if a record's OWN evidence shows TWO+ DIFFERENT real-world meanings under one name (a mixed same-name union), give it verdict=admit AND add it to mixed_flags [{driver_name, why, n_companies}] — a separate review will split or park it; do NOT skip it merely for being mixed. mixed_flags=[] if none. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, model:'opus', label:`gate${tag}`, phase:'Review'}),
  ])
  if (!dedup || !gate) throw new Error(`Review batch ${bi + 1}/${BATCH_FILES.length}: ${!dedup ? 'dedup' : ''}${!dedup && !gate ? '+' : ''}${!gate ? 'gate' : ''} agent died (likely session limit / API error) — fail-close, no partial review.`)

  const refute = await agent(`You are an INDEPENDENT skeptic. Your ONLY job: BREAK fusions — decisions that fold two DIFFERENT drivers into one. Read ${bf} — each driver_name is a catalog[] record with evidence_refs[{company, source_type, source_id, date, quote}]. For BOTH lists, default survives=FALSE; mark TRUE only if you genuinely cannot refute it.

1) PROPOSED SAME_AS LINKS (canonical <= variant): ${JSON.stringify(dedup.same_as_links)}
   survives=TRUE only if, reading BOTH names' evidence quotes, they are the EXACT same object AND scope AND mechanism (the 3-check). Different brand/segment vs company-wide, different metric/geography/mechanism, or mixed evidence -> FALSE.

2) PROPOSED REWRITES (driver_name -> rewrite_to): ${JSON.stringify((gate.verdicts||[]).filter(v => v.verdict==='rewrite').map(v => ({driver_name:v.driver_name, rewrite_to:v.rewrite_to})))}
   survives=TRUE only if the rewrite is provably WORDING-ONLY: rewrite_to means the IDENTICAL driver the evidence describes (a pure spelling / standard-phrase / word-order fix). Any change of object/scope/mechanism -> FALSE.

Return REFUTE_SCHEMA: one verdict for EVERY link and EVERY rewrite, each with a one-line why.`, {schema:REFUTE_SCHEMA, model:'opus', label:`refute${tag}`, phase:'Refute'})

  // JS mechanically FILTERS rejected decisions (per batch). Missing verdict -> not survives -> never fuse (fail-close).
  const linkOk = new Map((refute.same_as_verdicts||[]).map(v => [`${norm(v.canonical)}|${norm(v.variant)}`, v.survives === true]))
  const rwOk   = new Map((refute.rewrite_verdicts||[]).map(v => [`${norm(v.driver_name)}|${norm(v.rewrite_to)}`, v.survives === true]))
  survivingLinks.push(...(dedup.same_as_links||[]).filter(l => linkOk.get(`${norm(l.canonical)}|${norm(l.variant)}`) === true).map(l => ({canonical:l.canonical, variant:l.variant})))
  const gateRewrites = (gate.verdicts||[]).filter(v => v.verdict==='rewrite')
  appliedRewrites.push(...gateRewrites.filter(v => rwOk.get(`${norm(v.driver_name)}|${norm(v.rewrite_to)}`) === true).map(v => ({from:v.driver_name, to:v.rewrite_to})))
  parkedRewrites.push(...gateRewrites.filter(v => rwOk.get(`${norm(v.driver_name)}|${norm(v.rewrite_to)}`) !== true).map(v => { const s=(refute.rewrite_verdicts||[]).find(x => norm(x.driver_name)===norm(v.driver_name) && norm(x.rewrite_to)===norm(v.rewrite_to)); return {driver_name:v.driver_name, proposed_to:v.rewrite_to, why:(s&&s.why)||'unverified by skeptic'} }))
  allGateVerdicts.push(...(gate.verdicts||[]))
  allMixedFlags.push(...(dedup.mixed_flags||[]), ...(gate.mixed_flags||[]))
}

// ---- LEAF FLAG-TRIGGERED D5 (HierarchicalCatalogPlan D5 leaf path; 10th pass) ----
const flagsByName = {}
for (const f of allMixedFlags) {
  const k = norm(f.driver_name); if (k && !flagsByName[k]) flagsByName[k] = f
}
const flagged = Object.values(flagsByName)
let leafReviews = [], leafSplitMap = []
if (flagged.length) {
  phase('SameName')
  const LEAF_REVIEW_SCHEMA = { type:'object', additionalProperties:false, required:['collision_name','verdict','new_names','assignments','why'], properties:{
    collision_name:{type:'string'}, verdict:{type:'string', enum:['SAME','DIFFERENT','UNCLEAR']},
    new_names:{type:'array', items:{type:'string'}},
    assignments:{type:'array', items:{type:'object', additionalProperties:false, required:['company','to'], properties:{ company:{type:'string'}, to:{type:'string'}, ref_idx:{type:'array', items:{type:'string'}, description:'the idx values (r1, r2, ...) of the refs that go to this name — copied from the view; omit on at most ONE row per company = that row takes ALL remaining refs of the company'} }}},
    why:{type:'string'} } }
  const LEAF_REFUTE_SCHEMA = { type:'object', additionalProperties:false, required:['survives','why'], properties:{ survives:{type:'boolean'}, why:{type:'string'} } }
  const MINIGATE_SCHEMA = { type:'object', additionalProperties:false, required:['all_admit','reasons'], properties:{ all_admit:{type:'boolean'}, reasons:{type:'string'} } }
  const pyRec = (nm) => `${PY} -c "import json;d=json.load(open('${SEED}'));r=next(x for x in d['catalog'] if (x.get('driver_name') or '').strip().lower()=='${nm}')
k=lambda e:((e.get('company') or '').strip().lower(),(e.get('source_type') or '').strip().lower(),(e.get('source_id') or '').strip().lower(),(e.get('date') or '').strip().lower(),(e.get('quote') or '').strip())
allr=sorted(r['evidence_refs'],key=k)
view=[dict(e, idx='r%d'%(i+1)) for i,e in enumerate(allr)]
gs={}
for e in view: gs.setdefault((e.get('company') or '').strip(),[]).append(e)
names=sorted((x.get('driver_name') or '').strip().lower() for x in d['catalog'])
print(json.dumps({'name':r['driver_name'],'existing_seed_names':names,'sides':[{'company':c,'refs':v} for c,v in sorted(gs.items(), key=lambda kv:(len(kv[1]),kv[0]))]}))"`
  const rawReviews = (await parallel(flagged.map(f => () => agent(`SAME-NAME REVIEW (leaf, flag-triggered — HierarchicalCatalogPlan D5). The single record "${norm(f.driver_name)}" was FLAGGED as possibly mixing different meanings under one name (reviewer note: ${f.why}).
Read ${ONT}. LOAD THE EVIDENCE (grouped per company, smallest side first): run Bash:
${pyRec(norm(f.driver_name))}
${EXACT_MEANING_RULE}
ONE verdict:
- SAME = all quotes name the EXACT same reusable cause (the flag was a false alarm). An independent skeptic will still try to break this.
- DIFFERENT = a true homonym: coin MORE-SPECIFIC lower_snake_case names ONLY from words in the evidence (per DriverOntology; no tickers/company names), one per distinct meaning. HARD CONSTRAINT: every new name must be genuinely NEW — check it against the view's existing_seed_names list; if your natural choice already exists there, add a distinguishing evidence word to make it more specific (a near-duplicate is fine — dedup links exact duplicates later; a COLLISION hard-fails). Then PARTITION BY INDEX: every ref in the view carries an 'idx' (r1, r2, ...). An assignment row = {company, to, ref_idx: ["r1", "r4", ...]} — the listed refs go to that name. You may OMIT ref_idx on AT MOST ONE row per company: that row takes ALL remaining refs of that company (the remainder). Rules: every ref ends up with exactly one name (code enforces it); every 'to' name must receive at least one ref; two no-ref_idx rows for the same company is an ERROR. Just read each quote, decide which meaning it shows, and copy its idx.
- UNCLEAR = too thin/mixed to decide → park (fail-close).
Return LEAF_REVIEW_SCHEMA (collision_name = "${norm(f.driver_name)}").`, {schema:LEAF_REVIEW_SCHEMA, model:'opus', label:`d5:${norm(f.driver_name)}`, phase:'SameName'}))) ).filter(Boolean)
  if (rawReviews.length !== flagged.length) throw new Error(`leaf D5 review lost ${flagged.length - rawReviews.length} verdict(s) — fail-close.`)
  for (const v of rawReviews) {
    const nm = norm(v.collision_name)
    if (v.verdict === 'SAME') {
      const r1 = await agent(`INDEPENDENT skeptic on a flagged same-name union: "${nm}" (one leaf record spanning companies). Try to BREAK the claim that all its evidence names ONE driver. Default survives=FALSE.
LOAD THE EVIDENCE: run Bash:
${pyRec(nm)}
${EXACT_MEANING_RULE}
survives=TRUE only if you genuinely cannot refute exact same object AND scope AND mechanism across ALL quotes. Return LEAF_REFUTE_SCHEMA.`, {schema:LEAF_REFUTE_SCHEMA, model:'opus', label:`d5-refute:${nm}`, phase:'SameName'})
      let ok = r1 && r1.survives === true
      if (ok && ((flagsByName[nm] || {}).n_companies || 0) >= 8) {   // §11.18 high-blast at leaf
        const r2 = await agent(`SECOND independent skeptic (HIGH-BLAST union: many companies). Same union "${nm}". Judge EACH lens with a quote: same OBJECT? same SCOPE? same MECHANISM? survives = all three pass.
LOAD: run Bash:
${pyRec(nm)}
Return JSON per schema.`, {schema:{ type:'object', additionalProperties:false, required:['object','scope','mechanism','survives'], properties:{ object:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}}, scope:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}}, mechanism:{type:'object', additionalProperties:false, required:['pass','quote'], properties:{pass:{type:'boolean'}, quote:{type:'string'}}}, survives:{type:'boolean'} }}, model:'opus', label:`d5-refute2:${nm}`, phase:'SameName'})
        ok = !!(r2 && r2.survives === true && r2.object && r2.object.pass === true && r2.scope && r2.scope.pass === true && r2.mechanism && r2.mechanism.pass === true)
      }
      leafReviews.push(ok ? { collision_name: nm, verdict: 'SAME', why: v.why, refute_survived: true }
                          : { collision_name: nm, verdict: 'UNCLEAR', why: `SAME refuted by skeptic (fail-close): ${v.why}` })
    } else if (v.verdict === 'DIFFERENT') {
      const mg = await agent(`Mini-G2 on ${v.new_names.length} proposed split names (from the homonym split of "${nm}"): ${JSON.stringify(v.new_names)}. Read ${ONT}. all_admit=TRUE only if EVERY name is a valid, reusable, rule-following lower_snake driver name (no tickers, no states, not vague). Return MINIGATE_SCHEMA.`, {schema:MINIGATE_SCHEMA, model:'opus', label:`d5-gate:${nm}`, phase:'SameName'})
      if (mg && mg.all_admit === true) {
        leafReviews.push({ collision_name: nm, verdict: 'DIFFERENT', new_names: v.new_names, why: v.why })
        leafSplitMap.push({ from: nm, to: v.new_names, assignments: v.assignments.map(a => { const row = { company: a.company, to: a.to }; if (Array.isArray(a.ref_idx) && a.ref_idx.length) row.ref_idx = a.ref_idx; return row }) })
      } else {
        leafReviews.push({ collision_name: nm, verdict: 'UNCLEAR', why: `split names failed mini-gate (${(mg && mg.reasons) || 'no verdict'}) — parked fail-close: ${v.why}` })
      }
    } else leafReviews.push({ collision_name: nm, verdict: 'UNCLEAR', why: v.why })
  }
}
// Names re-shaped by the review (split-from + parked) must NOT be referenced by any decision (assembler hard-fails).
const reshaped = new Set(leafReviews.filter(r => r.verdict !== 'SAME').map(r => r.collision_name))
const touches = (...names) => names.some(n => reshaped.has(norm(n)))

phase('Assemble')
// Deterministic assembly (HierarchicalCatalogPlan §11.19): the 5-way precedence runs in CODE
// (assemble_catalog.py, pytest-covered). The agent below is a dumb pen for the SMALL decisions.json
// + a Bash runner; it never composes catalog content, so it cannot fabricate a fusion.
const decisions = {
  gate_verdicts: allGateVerdicts.filter(v => !touches(v.driver_name, v.rewrite_to)).map(v => ({ driver_name: v.driver_name, verdict: v.verdict, rewrite_to: v.rewrite_to || '', reason: v.reason || '' })),
  approved_same_as: survivingLinks.filter(l => !touches(l.variant, l.canonical)).map(l => ({ variant: l.variant, canonical: l.canonical })),
  approved_rewrites: appliedRewrites.filter(r => !touches(r.from, r.to)).map(r => ({ from: r.from, to: r.to })),
  parked_rewrites: parkedRewrites.filter(p => !touches(p.driver_name, p.proposed_to)),
}
const reviewStep = flagged.length ? `1b) Use the Write tool to save this EXACT JSON (byte-for-byte) to ${RUN_DIR}/same_name_review.json:
${JSON.stringify({ reviews: leafReviews, split_map: leafSplitMap })}
` : ''
const out = await agent(`Steps (assembler rev2 — STAR-flattened canonicals), EXACT, in order:
1) Use the Write tool to save this EXACT JSON (byte-for-byte, do not reformat) to ${RUN_DIR}/decisions.json:
${JSON.stringify(decisions)}
${reviewStep}2) Run with Bash: ${PY} ${DIR}/workflows/assemble_catalog.py ${RUN_DIR}${flagged.length ? ` --review ${RUN_DIR}/same_name_review.json` : ''}
   (deterministic code: reads seed.json + decisions.json from DISK, applies the 5-way precedence, writes catalog.json + approved.json, prints an "ASSEMBLED ..." line with the catalog sha256 + counts)
Return ok=true and sha_line = the exact printed ASSEMBLED line. If the script exits NON-ZERO: ok=false, sha_line = the exact error output. Do NOT edit or compose any catalog content yourself.`, {schema:ASSEMBLE_SCHEMA, model:'opus', label:'assemble', phase:'Assemble'})
if (!out) throw new Error('Assemble agent died (likely session limit / API error) — fail-close.')
if (!out.ok) throw new Error(`assemble_catalog.py failed: ${out.sha_line}`)

phase('Validate')
const validation = await agent(`Run this EXACT Bash command (validator rev2 — transitive D1; it writes the validator output to validation.txt in the run dir AND reports the validator's real exit code; the 3rd arg enables the D1 fusion-approval + same_as_variants checks):
${PY} ${DIR}/workflows/validate_catalog.py ${SEED} ${CAT} ${RUN_DIR}/approved.json${flagged.length ? ` --review ${RUN_DIR}/same_name_review.json` : ''} | tee ${RUN_DIR}/validation.txt ; echo "exit=\${PIPESTATUS[0]}"
This is a deterministic structure check (no judgment). If exit is NON-ZERO, begin your reply with "VALIDATION FAILED" and paste the exact failing checks + names. If exit is 0, begin with "VALIDATION PASSED". Do not fix anything; just report.`, {model:'opus', label:'validate', phase:'Validate'})
if (!validation) throw new Error('Validate agent died (likely session limit / API error) — fail-close.')

return { assembled: out.sha_line, counts: { same_as: survivingLinks.length, rewrites_applied: appliedRewrites.length, rewrites_parked: parkedRewrites.length, d5_flags: flagged.length, d5_verdicts: leafReviews.map(r => r.verdict) }, validation }
