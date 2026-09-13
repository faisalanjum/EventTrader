"""Is there ANY preserved lineage sealed under the CURRENT key owner?

Codex: reuse a valid existing current fixture before making another. So this
looks, rather than assuming there is none. Every receipt.json under the
recovery tree that carries a derived_from.owner_sha256 is read and grouped by
the owner it was sealed under.

Prints: <receipts carrying an owner> <distinct owner eras> <sealed under the
current owner>. Reads only.
"""
import collections
import hashlib
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
CURRENT = hashlib.sha256(io.open(
    os.path.join(A7, 'unit_2008/harness_g1v3/build_kfields_key.py'),
    'rb').read()).hexdigest()

eras = collections.Counter()
for root, dirs, files in os.walk(A7):
    dirs[:] = [d for d in dirs if d != '.git']
    if 'receipt.json' not in files:
        continue
    try:
        doc = json.load(io.open(os.path.join(root, 'receipt.json')))
    except Exception:
        continue                       # not every receipt.json is this shape
    owner = (doc.get('derived_from') or {}).get('owner_sha256') \
        if isinstance(doc.get('derived_from'), dict) else None
    if owner:
        eras[owner] += 1
print('%d %d %d' % (sum(eras.values()), len(eras), eras.get(CURRENT, 0)))
