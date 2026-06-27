#!/usr/bin/env python3
"""Emit a Workflow JS that runs the EXACT concept_linker pick+verify (the algorithm under test)
on every company, one agent per company. Guard already applied in probe_build (faithful: guarded
slugs abstain before the LLM). Each agent is the `llm` the module would call.

Usage: python gen_matcher_workflow.py <run_number>  → writes run_matcher_run{N}.js
"""
import sys, json, pathlib

CLRV = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")
HERE = pathlib.Path(".claude/plans/Drivers/WIP/concept_link_revalidation")
run = int(sys.argv[1]) if len(sys.argv) > 1 else 1

# restrict to the locked cohort (companies that completed run 1) if present
cohort = CLRV/"cohort274.txt"
if cohort.exists():
    tickers = sorted(cohort.read_text().split())
else:
    tickers = sorted(p.stem for p in (CLRV/"probe").glob("*.json"))
CLRV_S = str(CLRV)

# Faithful embedding of concept_linker.PICK_PROMPT + VERIFY_PROMPT, applied per metric independently.
prompt = (
 'You are the LLM inside an XBRL concept-matcher. Read ' + CLRV_S + '/probe/${t}.json '
 '(fields: menu=[{qname,label,usage}] = the ONLY allowed answers; metrics=[slugs]).\\n'
 'For EACH metric, run TWO independent steps, treating every metric in isolation:\\n'
 'STEP 1 PICK: Pick the ONE menu qname that IS exactly this metric (the same accounting line a filer '
 'tags), or null. SAME metric only — a related-but-different line is NOT a match (cost-of-revenue'
 '\\u2260revenue; income-tax\\u2260net-income; a subtotal\\u2260the total; basic\\u2260diluted). Two equal '
 'candidates \\u2192 higher usage.\\n'
 'STEP 2 VERIFY (only if PICK is non-null): STRICT auditor, default to refuted when unsure (a wrong link '
 'is the cardinal sin). Refute if the concept is a related-but-different line, a different value (GAAP vs '
 'non-GAAP, gross vs net, subtotal vs total), the wrong statement, or a dimension instead of the '
 'consolidated line. Output real=true only if it survives.\\n'
 'Write ' + CLRV_S + '/run' + str(run) + '/${t}.json = a JSON array '
 '[{"slug","qname": "us-gaap:..." or null,"real": true|false}] covering EVERY metric exactly once '
 '(real=false when qname is null). Return only "${t}: done".'
)

js = f"""export const meta = {{
  name: 'concept-link-revalidate-run{run}',
  description: 'Faithful concept_linker pick+verify over ALL {len(tickers)} companies (run {run}/3, stability)',
  phases: [{{ title: 'Match', detail: 'one agent per company runs the exact pick+verify' }}],
}}
const tickers = {json.dumps(tickers)}
const PROMPT = (t) => `{prompt}`
phase('Match')
await parallel(tickers.map(t => () => agent(PROMPT(t), {{ label: `r{run}:${{t}}`, phase: 'Match' }})))
return {{ run: {run}, companies: tickers.length, out: '{CLRV_S}/run{run}' }}
"""
(CLRV/f"run{run}").mkdir(exist_ok=True)
outp = HERE/f"run_matcher_run{run}.js"
outp.write_text(js)
print(f"wrote {outp} for run {run}: {len(tickers)} companies")
