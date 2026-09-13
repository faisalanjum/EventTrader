"""Copy one workflow's native evidence into the durable unit, byte-exactly.

Codex step 4: preserve the official state, the journal, every referenced native
worker transcript and meta, and the raw result bytes, BEFORE ingestion - and
alter no native record.

Addressed by the SPECIFIC kind and segment, never by listing a directory: the
unit root now also holds a file Codex added, and a listing-driven copier would
treat it as a run.

    python3 -B preserve_native_2104.py <kind> <segment> <workflow id>

Every copy is re-hashed against its source. An existing destination that
differs is refused, so a re-run can never rewrite preserved evidence.
"""
import collections
import hashlib
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')
KIND, SEGMENT, WORKFLOW = sys.argv[1], int(sys.argv[2]), sys.argv[3]
TAG = 'seg%02d' % SEGMENT
UNIT = os.path.join(A7, 'unit_2103_g23_grading', KIND)
RUN = os.path.join(UNIT, 'run')
DEST = os.path.join(UNIT, 'native', TAG, WORKFLOW)
TRANSCRIPTS = os.path.join(SESSION, 'subagents/workflows', WORKFLOW)
OFFICIAL = os.path.join(SESSION, 'workflows', WORKFLOW + '.json')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def keep(source, name):
    """Copy one native file in, re-hash it, and never overwrite a different one."""
    target = os.path.join(DEST, name)
    digest = sha(source)
    if os.path.exists(target):
        assert sha(target) == digest, \
            'preserved %s already differs; refusing to overwrite' % name
    else:
        os.path.isdir(os.path.dirname(target)) or os.makedirs(os.path.dirname(target))
        shutil.copyfile(source, target)
        assert sha(target) == digest, 'the copy of %s does not match' % name
    return collections.OrderedDict([
        ('name', name), ('source', source), ('sha256', digest),
        ('bytes', os.path.getsize(target))])

# the launch note is the only thing that says which workflow this segment owns
note = json.load(io.open(os.path.join(UNIT, 'LAUNCH_NOTE_%s.json' % TAG.upper())))
assert note['workflow_id'] == WORKFLOW, \
    'this segment was launched as %s, not %s' % (note['workflow_id'], WORKFLOW)

kept = []
assert os.path.isfile(OFFICIAL), 'the official workflow state does not exist yet'
kept.append(keep(OFFICIAL, 'official_state.json'))
# the workflow's own transcript directory: journal plus every agent file it names
assert os.path.isdir(TRANSCRIPTS), TRANSCRIPTS
for name in sorted(os.listdir(TRANSCRIPTS)):
    kept.append(keep(os.path.join(TRANSCRIPTS, name), os.path.join('transcripts', name)))

# whatever native worker states the official record itself references
state = json.load(io.open(OFFICIAL))
referenced = []
for value in json.dumps(state).split('"'):
    if value.startswith(SESSION) and os.path.isfile(value) and value != OFFICIAL:
        if value not in referenced:
            referenced.append(value)
for path in referenced:
    kept.append(keep(path, os.path.join('referenced', os.path.basename(path))))

record = collections.OrderedDict([
    ('kind', KIND), ('segment', SEGMENT), ('workflow_id', WORKFLOW),
    ('preserved_under', DEST),
    ('official_state_sha256', kept[0]['sha256']),
    ('files', kept), ('file_count', len(kept)),
    ('referenced_native_files', len(referenced)),
    ('native_records_altered', 0)])
out = os.path.join(DEST, 'PRESERVED.json')
with io.open(out, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('preserved %d files for %s %s under %s' % (len(kept), KIND, TAG, DEST))
for f in kept:
    print('   %-46s %s %8d B' % (f['name'], f['sha256'][:16], f['bytes']))
print('wrote', out)
