#!/usr/bin/env python3
"""Flatten a batched-workflow output file into relocate_out_<set>.json for the graders.

    venv/bin/python scripts/driver_seed/relocate_probe/ungroup.py <workflow_output.json> --set exam_annual
"""
import os, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument('outfile'); ap.add_argument('--set', required=True)
a = ap.parse_args()
groups = json.load(open(a.outfile))['result']['groups']
records = [{'i': r['id'], 'found': r.get('found', False), 'value': r.get('value', ''),
            'quote': r.get('quote', ''), 'period_evidence': r.get('period_evidence', ''),
            'gid': g['gid']} for g in groups for r in g['results']]
path = f'{HERE}/relocate_out_{a.set}.json'
json.dump({'records': sorted(records, key=lambda r: r['i'])}, open(path, 'w'), indent=1)
print(f"[{a.set}] {len(records)} records <- {len(groups)} groups -> {path}")
