"""Freeze the zero-agent probe and prove it is what it claims to be.

The probe exists to answer ONE question: will the platform read and execute a
workflow script that lives at a recovery path? For the answer to mean anything
the script must contain nothing that could fail for its own reasons - so this
checks the CODE, with comments and strings stripped, for every construct the
task forbids, and records the frozen identity.

Reads and writes only inside this unit.
"""
import collections
import hashlib
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'transport_path_probe_2102.js')
OUT = os.path.join(HERE, 'PROBE_IDENTITY_2102.json')
#: everything the task forbids inside the script, plus the two things that make
#: a workflow spawn work at all. Each must be absent from the CODE.
FORBIDDEN = ('agent(', 'phase(', 'pipeline(', 'parallel(', 'require(',
             'import ', 'fetch(', 'XMLHttpRequest', 'readFile', 'writeFile',
             'child_process', 'spawn(', 'execSync', 'process.env')

source = io.open(SCRIPT, encoding='utf-8').read()
# comments and string literals are documentation, not behaviour
code = re.sub(r'/\*.*?\*/', ' ', source, flags=re.S)
code = re.sub(r'(?m)//.*$', ' ', code)
code = re.sub(r"'[^'\n]*'", "''", code)
code = re.sub(r'"[^"\n]*"', '""', code)

found = {token: code.count(token) for token in FORBIDDEN if token in code}
assert not found, 'the probe is not inert: %s' % found
assert code.count('export const meta') == 1, 'exactly one meta block required'
assert code.count('return') == 1, 'the probe returns once and does nothing else'

record = collections.OrderedDict([
    ('kind', 'frozen zero-agent Workflow transport probe'),
    ('question', 'will the platform read and execute a workflow script that '
                 'lives under EventMarketDB-driver-recovery'),
    ('script_path', SCRIPT),
    ('script_tree', 'recovery' if '/EventMarketDB-driver-recovery/' in SCRIPT
     else 'other'),
    ('script_sha256', hashlib.sha256(
        io.open(SCRIPT, 'rb').read()).hexdigest()),
    ('script_bytes', os.path.getsize(SCRIPT)),
    ('forbidden_constructs_in_code', found),
    ('checked_for', list(FORBIDDEN)),
    ('agents_it_can_spawn', 0),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('script     ', SCRIPT)
print('tree       ', record['script_tree'])
print('sha256     ', record['script_sha256'])
print('bytes      ', record['script_bytes'])
print('forbidden constructs in code:', found or 'NONE')
print('wrote', OUT)
