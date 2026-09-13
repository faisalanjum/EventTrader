"""What the one probe invocation actually established.

The distinction the task demands is between a PATH refusal and a
script-syntax/runtime error, with no silent inference of one from the other.
Two measured facts separate them here:

  * the refusal text names the scriptPath and states the path-admissibility
    rule. It says nothing about syntax, the meta block or a runtime fault.
  * no workflow was created. A script that was read and failed to parse would
    have produced a workflow run; there is none.

So the platform did NOT read or execute the file. What it would do with the
file's CONTENT is therefore untested, and this does not claim otherwise -
testing that would need the second route the task forbids.
"""
import collections
import glob
import hashlib
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'transport_path_probe_2102.js')
RESULT = os.path.join(HERE, 'PROBE_RESULT_2102.txt')
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')
OUT = os.path.join(HERE, 'PROBE_OUTCOME_2102.json')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


refusal = io.open(RESULT, encoding='utf-8').read()
after = os.path.getmtime(SCRIPT)
created = [p for p in glob.glob(os.path.join(SESSION, 'workflows', '*'))
           if os.path.getmtime(p) > after]

record = collections.OrderedDict([
    ('kind', 'one zero-agent Workflow transport probe, not retried'),
    ('invocations', 1),
    ('script_path', SCRIPT),
    ('script_sha256', sha(SCRIPT)),
    ('result_path', RESULT),
    ('result_sha256', sha(RESULT)),
    ('platform_read_or_executed_the_file', False),
    ('refusal_names_the_scriptpath', SCRIPT in refusal),
    ('refusal_mentions_syntax_or_runtime', any(
        word in refusal.lower() for word in
        ('syntax', 'parse', 'unexpected token', 'meta', 'runtime', 'exception'))),
    ('workflows_created_after_the_probe', len(created)),
    ('workers_spawned', 0),
    ('model_calls', 0),
    ('the_exact_requirement_the_platform_states', [
        'a script path this tool returned',
        'or a file you can already read (the working directory or a directory '
        'you have added)']),
    ('recovery_tree_is_neither', True),
    ('not_attempted_here', [
        'no second route, no retry, no link, no copy',
        'no settings, hook or permission change to add the directory',
        'the script content is therefore unvalidated by the platform']),
])
assert record['invocations'] == 1
assert not record['refusal_mentions_syntax_or_runtime'], 'not a clean path refusal'
assert record['refusal_names_the_scriptpath'], 'the refusal does not name the path'
assert record['workflows_created_after_the_probe'] == 0
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('platform read/executed the file :', record['platform_read_or_executed_the_file'])
print('refusal names the scriptPath    :', record['refusal_names_the_scriptpath'])
print('refusal mentions syntax/runtime :', record['refusal_mentions_syntax_or_runtime'])
print('workflows created               :', record['workflows_created_after_the_probe'])
print('wrote', OUT)
