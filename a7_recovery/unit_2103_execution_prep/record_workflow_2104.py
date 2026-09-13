"""Stamp the returned workflow id and call time into a launch note.

The note was written BEFORE the call with these two fields null; this fills
them once and refuses to overwrite a note that already names a workflow, so a
second call can never be recorded over the first.

    python3 -B record_workflow_2104.py <kind> <segment> <workflow id>
"""
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
KIND, SEGMENT, WORKFLOW = sys.argv[1], int(sys.argv[2]), sys.argv[3]
PATH = os.path.join(A7, 'unit_2103_g23_grading', KIND,
                    'LAUNCH_NOTE_SEG%02d.json' % SEGMENT)

note = json.load(io.open(PATH), object_pairs_hook=lambda p: __import__(
    'collections').OrderedDict(p))
assert note['workflow_id'] is None, \
    '%s already names workflow %s' % (PATH, note['workflow_id'])
assert note['kind'] == KIND and note['segment'] == SEGMENT
note['workflow_id'] = WORKFLOW
note['called_at_utc'] = datetime.datetime.now(
    datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
tmp = PATH + '.tmp'
with io.open(tmp, 'w', encoding='utf-8') as fh:
    fh.write(json.dumps(note, indent=1) + '\n')
os.replace(tmp, PATH)
print('%s segment %d -> workflow %s at %s'
      % (KIND, SEGMENT, WORKFLOW, note['called_at_utc']))
