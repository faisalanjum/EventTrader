#!/usr/bin/env python3
"""Record Fable's dual-CIK ruling across EXP-1 outputs (READ/WRITE files only; no Neo4j, no LLM).
Preserves existing register entries; appends only. args: TS RUNDIR"""
import json, sys, os
TS = sys.argv[1]; RUNDIR = sys.argv[2]
BASE = '/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments'

RULE = ("No aliasing rule ships in EXP-1. After normal normalization, if a dimension/member node still does not "
        "resolve -> SKIP the whole affected fact + count slice_pairing_dualcik_unresolved. NO qname-only matching; "
        "NO cross-CIK/global alias matching; do NOT drop AAL.")
SUBCASE = {
    "ruled_by": "Fable 2026-07-09",
    "case": "dual-CIK filer/entity (AAL: filer Group cik 6201 carries entity Inc cik 4515 docs). Dimension/Member nodes stored under entity cik 4515; contexts reference filer cik 6201 -> unresolved after zero-pad normalization.",
    "rule": RULE,
    "scope": "AAL-only (11/12 companies pair clean). Touches REAL slice axes (entity/product/geography); 701 would-materialize facts skipped (dualcik_scope_proof.json).",
    "deferred_to": "O12 bundle (ingestion repair / possible future certified recovery)"}


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


# 1. ra_0004.json
ra = {
    "id": "ra_0004",
    "raised_in": "EXP-1 dry-run PART-2 dual-CIK slice-pairing scope pass",
    "doc": "XBRLIntegrationDesign 5.2 P4d/P4f · O13 axis<->member · O12",
    "rule": "dual-CIK unresolved slice reference handling",
    "case_ref": "AAL filer cik 6201 / entity cik 4515; dim/member nodes under entity cik; contexts reference filer cik -> lookup misses after normalization",
    "description": "Scope pass over all 60 FA filings (dualcik_scope_proof.json): AAL-ONLY (11/12 companies pair cleanly). AAL: 2587 pairing failures, 701 would-materialize, unresolved SLICE axes entity=1410 product=513 geography=104 (e.g. AAL revenue by product/service on srt:ProductOrServiceAxis). Touches real slices + materialized facts.",
    "fable_ruling": RULE,
    "status": "closed_resolved_fable",
    "resolution": "Fable 2026-07-09: skip+count slice_pairing_dualcik_unresolved, no aliasing. Ingestion-repair / possible future certified recovery deferred to O12.",
    "o12_ref": "o12_bundle.json#dualcik_ingestion_repair"}
json.dump(ra, open(BASE + '/exhibits/ra_0004.json', 'w'), indent=2, sort_keys=True)
print('wrote exhibits/ra_0004.json')

# 2. ambiguity_register.json (SHARED - preserve existing, append only)
p = BASE + '/exp1_xbrl/ambiguity_register.json'
reg = load(p, {'exp_id': 'EXP-1', 'entries_open': [], 'entries_resolved': []})
reg.setdefault('entries_resolved', [])
reg.setdefault('entries_open', [])
if not any(e.get('ref') == 'ra_0004' for e in reg['entries_resolved']):
    reg['entries_resolved'].append({
        "ref": "ra_0004", "area": "axis<->member dual-CIK subcase (P4d/P4f/O13)",
        "status": "closed_resolved_fable",
        "resolution": "skip+count slice_pairing_dualcik_unresolved; NO aliasing / qname-only / cross-CIK; AAL kept",
        "goes_to": "O12 bundle (ingestion repair / future certified recovery)"})
json.dump(reg, open(p, 'w'), indent=2, sort_keys=True)
print('appended ra_0004 to ambiguity_register.json (entries_open=%d preserved)' % len(reg['entries_open']))

# 3. manifest skip_counters (Fable ruling itself is written by the materializer FABLE_RULINGS on the dry3 rerun)
mp = BASE + '/' + RUNDIR + '/manifest.json'
m = load(mp, {})
sc = m.get('skip_counters', [])
if 'slice_pairing_dualcik_unresolved' not in sc:
    m['skip_counters'] = sc + ['slice_pairing_dualcik_unresolved']
json.dump(m, open(mp, 'w'), indent=2, sort_keys=True)
print('manifest skip_counters updated')

# 4. census.json binding_b_axis_member.dualcik_subcase (+ schema_bindings_probe.json canonical)
for cp, key in [(BASE + '/exp1_xbrl/census.json', 'schema_bindings'), (BASE + '/exp1_xbrl/schema_bindings_probe.json', None)]:
    d = load(cp, None)
    if d is None:
        print('skip (missing):', cp); continue
    root = d.get(key) if key else d
    if isinstance(root, dict) and 'binding_b_axis_member' in root:
        root['binding_b_axis_member']['dualcik_subcase'] = SUBCASE
        json.dump(d, open(cp, 'w'), indent=2, sort_keys=True)
        print('dualcik_subcase added to', os.path.basename(cp))
    else:
        print('binding_b_axis_member not found in', os.path.basename(cp))

# 5. O12 bundle
op = BASE + '/exp1_xbrl/o12_bundle.json'
o12 = load(op, {"bundle": "O12 XBRL pin-amendment / ratification bundle (EXP-1 findings)", "entries": []})
o12.setdefault('entries', [])
if not any(e.get('id') == 'dualcik_ingestion_repair' for e in o12['entries']):
    o12['entries'].append({
        "id": "dualcik_ingestion_repair", "raised_by": "EXP-1 dual-CIK scope (ra_0004)",
        "fable_ruling_in_exp1": "skip+count, no aliasing (dualcik_unresolved_slice_skip)",
        "issue": "dual-filer (AAL Group cik 6201 / Inc entity cik 4515) stores dimension/member nodes under the ENTITY cik while contexts reference the FILER cik -> real slice facts (revenue by product/geo/entity) skipped. AAL-only in this corpus; 701 would-materialize facts lost.",
        "candidate_repair": "INGESTION-side: store/index dim/member nodes so filer-cik contexts resolve, OR record a VALIDATED filer<->entity cik map at load. Possible future CERTIFIED recovery of the skipped AAL slice facts once a safe resolution ships. This is NOT an EXP-1 aliasing rule.",
        "status": "open_for_owner_ratification"})
json.dump(o12, open(op, 'w'), indent=2, sort_keys=True)
print('o12_bundle.json updated')

# 6. WORKORDER_STATUS log
wp = BASE + '/WORKORDER_STATUS.md'
with open(wp, 'a') as fh:
    fh.write('\n- ' + TS + ' EXP-1 dual-CIK ruling APPLIED (Fable 2026-07-09): unresolved dim/member node after normalization -> skip whole fact + count slice_pairing_dualcik_unresolved; NO aliasing/qname-only/cross-CIK; AAL kept. Recorded ra_0004, ambiguity_register (closed), census binding_b.dualcik_subcase, o12_bundle (ingestion repair / future certified recovery). O13/P4f otherwise unchanged.\n')
print('WORKORDER_STATUS.md logged')
print('ALL_6_RECORDED')
