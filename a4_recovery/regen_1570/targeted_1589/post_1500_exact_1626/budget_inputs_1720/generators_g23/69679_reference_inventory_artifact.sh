V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
cd "$V3" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 1800 /home/faisal/EventMarketDB/venv/bin/python3 -c "
import a7_g1_build as G, a7_reference_inventory as INV, collections, os, io, json
key, identity = G.live_key()
rows, problems = INV.build(key)
assert not problems, problems[:3]
doc = collections.OrderedDict([
    ('schema', INV.SCHEMA),
    ('key_identity', identity),
    ('rows', rows),
    ('rows_total', len(rows)),
    ('override_rows', sum(1 for r in rows if r['name_from_override'])),
    ('ledger_added_rows', sum(1 for r in rows if r['added_by_ledger'])),
    ('final_role_free_values', sum(len(r['values']) for r in rows)),
    ('evidence_origins', dict(collections.Counter(r['evidence_origin'] for r in rows))),
])
# the previous file is history: keep it, write the corrected one beside it
old = INV.INVENTORY_PATH
if os.path.exists(old):
    os.rename(old, old.replace('.json', '.superseded_1464.json'))
sha = INV.write(doc)
print('inventory rewritten:', old)
print('sha256   :', sha)
print('rows     :', doc['rows_total'], '| overrides', doc['override_rows'],
      '| ledger-added', doc['ledger_added_rows'], '| values', doc['final_role_free_values'])
print('origins  :', doc['evidence_origins'])
# and it must now VALIDATE
proved = INV.validate(key, G.accepted_positions)
print('validate :', len(proved), 'rows proved')
" 2>&1 | grep -v WARNING | tail -8