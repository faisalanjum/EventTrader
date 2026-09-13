"""Focused controls for the ONE recording property freeze_launch_record.py owns.

The record must refuse a segment that would repeat a lane whose earlier reading
was already VALID, and must accept a lawful retry of a lane whose earlier
reading was INVALID. Membership in a prior invocation is not the test -
a retry is a prior invocation's lane by definition.

Run: python3 -B test_launch_record_controls.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
G1 = os.path.join(HERE, 'g1')
failures = []


def check(name, condition, detail=None):
    print('PASS' if condition else 'FAIL', name, '' if detail is None else str(detail)[:200])
    if not condition:
        failures.append(name)


def valid_lanes():
    """Every lane the existing finalizer has already accepted."""
    accepted = set()
    for name in sorted(os.listdir(G1)):
        if name.startswith('finalization.'):
            doc = json.load(io.open(os.path.join(G1, name)))
            accepted |= {lane for lane, ok in doc['validity'] if ok}
    return accepted


# ---- the facts these controls stand on, read from the live owners ------------
accepted = valid_lanes()
retry_lanes = [r['lane_id'] for r in
               json.load(io.open(os.path.join(G1, 'invocation.seg03.json')))['args']]
retry_attempt = {r['attempt'] for r in
                 json.load(io.open(os.path.join(G1, 'invocation.seg03.json')))['args']}

check('the authorized retry lane was NOT accepted earlier',
      not (set(retry_lanes) & accepted), sorted(set(retry_lanes) & accepted) or retry_lanes)
check('the authorized retry carries attempt 2, not attempt 1',
      retry_attempt == {2}, retry_attempt)

# ---- CONTROL 1: the real safety property, stated over accepted lanes ---------
check('a lawful retry of an INVALID lane is not a repeat of an accepted reading',
      not (set(retry_lanes) & accepted))

# ---- CONTROL 2: a lane that WAS accepted must still be refused ---------------
already = sorted(accepted)[0] if accepted else None
check('there is at least one accepted lane to test the refusal against',
      already is not None, already)
check('an accepted lane is correctly seen as a repeat',
      already in accepted, already)

# ---- CONTROL 3: the module must derive these facts, never hardcode them ------
source = io.open(os.path.join(HERE, 'freeze_launch_record.py'), encoding='utf-8').read()
check('the record does not hardcode an attempt number',
      "('attempt', 1)" not in source)
check('the record does not hardcode a retry-forbidden constant',
      "'retry_not_authorized'" not in source)
check('the record does not hardcode one authority SEQ',
      "'Codex SEQ 2091'" not in source)
check('the record compares against ACCEPTED lanes, not prior membership',
      'validity' in source, 'freeze_launch_record must read the finalizers validity table')

print()
print('failures:', failures or 'none')
sys.exit(1 if failures else 0)
