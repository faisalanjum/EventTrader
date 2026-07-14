#!/usr/bin/env python3
"""Codex (ChatGPT) reader runner — same prompt + 5 rules as relocate_batch.js, run via
`codex exec` so the bulk harvest bills the ChatGPT account, not Claude. Per-gid outputs are
checkpointed (resume = skip existing); final flatten matches relocate_out_<set>.json.

    venv/bin/python scripts/driver_seed/relocate_probe/codex_reader.py \
        --set exam_annual --gids 0-22 --model gpt-5.5 --workers 6
"""
import os, re, json, glob, argparse, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))

SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "found": {"type": "boolean"},
                       "candidate_index": {"type": ["integer", "null"]},
                       "value": {"type": "string"}, "quote": {"type": "string"},
                       "period_evidence": {"type": "string"}},
        "required": ["id", "found", "candidate_index", "value", "quote", "period_evidence"],
        "additionalProperties": False}}},
    "required": ["results"], "additionalProperties": False,
}

# IDENTICAL wording to relocate_batch.js (comparability) + a JSON-only closing line.
PROMPT = (
    "You re-find SEVERAL company metrics' values for specific periods in ONE set of document excerpts. "
    "100% precision is required; abstaining on any metric is correct and expected — never guess.\n\n"
    "Read {path} = {{ticker, cases:[{{id, kpi, period_type, period_target, address}}...], candidates:[...]}}.\n"
    "- Each case's address = that metric's identity from an earlier disclosure: label, caption, siblings, unit, "
    "lock_row (how it read in an EARLIER period — RECOGNITION only; its number will differ, never copy it), "
    "and possibly measurement ('gaap' = plain unadjusted figure; 'adjusted' = adjusted/non-GAAP; absent = unknown).\n"
    "- candidates = excerpts from the target document, SHARED by all cases. Each may be a TABLE ROW or a SENTENCE.\n\n"
    "For EACH case independently, choose the ONE candidate satisfying ALL FIVE rules; if none does, found=false for that case:\n"
    "1. METRIC KIND — same kind as the address (a profit is not a revenue is not a margin is not a count).\n"
    "2. SLICE — same segment/geography/product/entity as the address (label + siblings), not a different slice, subtotal, or superset.\n"
    "3. PERIOD — the number must be the TARGET period: a period_type figure (annual = FULL YEAR; quarterly = a SINGLE "
    "three-month quarter, never six-/nine-month or year-to-date) ending period_target. Prove it from a column header "
    "OR the sentence's own words; no period evidence -> found=false.\n"
    "4. CONSISTENCY — if the candidate also shows the EARLIER (lock) period, that figure must agree with lock_row's number.\n"
    "5. MEASUREMENT — if the text offers BOTH plain/GAAP and adjusted figures, take the one matching address.measurement; "
    "unknown measurement + both flavors present -> found=false; explicitly different flavor -> found=false.\n"
    "TIE-BREAK (never a filter): between two qualifying candidates prefer the one whose section words match address.caption.\n\n"
    "Per case set: value = ONLY that metric's target-period number; quote = the row/sentence copied VERBATIM IN FULL; "
    "period_evidence = the exact words proving the period. Your FINAL message must be ONLY the JSON object "
    '{{"results":[one entry per case, same ids]}} — no prose, no markdown fences.'
)


def parse_json(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        return None
    try:
        out = json.loads(m.group(0))
        return out if isinstance(out.get('results'), list) else None
    except json.JSONDecodeError:
        return None


def run_gid(gdir, odir, g, model, schema_path):
    dst = f'{odir}/gbatch_{g}.json'
    if os.path.exists(dst):
        return 'cached'
    prompt = PROMPT.format(path=f'{gdir}/gbatch_{g}.json')
    for attempt in range(2):
        with tempfile.NamedTemporaryFile('r', suffix='.txt', delete=False) as lm:
            pass
        r = subprocess.run(
            ['codex', 'exec', '-m', model, '--sandbox', 'read-only', '--ephemeral',
             '--skip-git-repo-check', '--output-schema', schema_path,
             '-o', lm.name, prompt + ('' if not attempt else '\nReturn ONLY the JSON object.')],
            capture_output=True, text=True, timeout=1200, cwd=HERE)
        out = parse_json(open(lm.name).read() if os.path.exists(lm.name) else '')
        os.unlink(lm.name)
        if out:
            json.dump({'gid': g, 'results': out['results']}, open(dst, 'w'))
            return 'ok'
    return f'FAIL (rc={r.returncode}) {r.stderr[-200:]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', required=True)
    ap.add_argument('--gids', required=True, help='e.g. 0-22 or 3,7,9')
    ap.add_argument('--model', default='gpt-5.5')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    gids = []
    for part in a.gids.split(','):
        gids += list(range(int(part.split('-')[0]), int(part.split('-')[1]) + 1)) if '-' in part else [int(part)]
    gdir = f'{HERE}/gbatches_{a.set}'
    odir = f'{HERE}/codex_out_{a.set}'; os.makedirs(odir, exist_ok=True)
    schema_path = f'{odir}/_schema.json'
    json.dump(SCHEMA, open(schema_path, 'w'))
    with ThreadPoolExecutor(a.workers) as ex:
        st = list(ex.map(lambda g: run_gid(gdir, odir, g, a.model, schema_path), gids))
    for g, s in zip(gids, st):
        if s != 'ok' and s != 'cached':
            print(f'  gid {g}: {s}')
    # flatten to grader shape
    records = []
    for f in glob.glob(f'{odir}/gbatch_*.json'):
        gb = json.load(open(f))
        records += [{'i': r['id'], 'found': r.get('found', False), 'value': r.get('value', ''),
                     'quote': r.get('quote', ''), 'period_evidence': r.get('period_evidence', ''),
                     'gid': gb['gid']} for r in gb['results']]
    path = f'{HERE}/relocate_out_{a.set}_codex.json'
    json.dump({'records': sorted(records, key=lambda r: r['i'])}, open(path, 'w'), indent=1)
    ok = sum(1 for s in st if s in ('ok', 'cached'))
    print(f"[{a.set}] {ok}/{len(gids)} calls ok | {len(records)} records -> {path}")


if __name__ == '__main__':
    main()
