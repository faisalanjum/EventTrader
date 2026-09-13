"""Put ONE newly published segment's script at the scriptPath it names.

The one-shot 2103 materializer walked the unit directory; that is now unsafe,
because the unit root also holds a file Codex added. This takes the kind and
segment explicitly and touches nothing else.

    python3 -B materialize_segment_2104.py <kind> <segment>

Same guarantees as before: destination read from the published invocation,
source checked against the receipt first, regular file written, a differing
existing file refused rather than overwritten, bytes re-hashed from disk.
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
KIND, SEGMENT = sys.argv[1], int(sys.argv[2])
TAG = 'seg%02d' % SEGMENT
RUN = os.path.join(A7, 'unit_2103_g23_grading', KIND, 'run')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


receipt = json.load(io.open(os.path.join(RUN, 'receipt.%s.json' % TAG)))
invocation = json.load(io.open(os.path.join(RUN, 'invocation.%s.json' % TAG)))
source = os.path.join(RUN, 'grade_batch.%s.js' % TAG)
destination = invocation['scriptPath']

assert destination == receipt['script_path'], \
    'the invocation and the receipt name different scripts'
assert os.path.basename(destination) == 'grade_batch.%s.js' % TAG, destination
measured = sha(source)
assert measured == receipt['script_sha256'], \
    'the durable source is %s, the receipt publishes %s' % (
        measured, receipt['script_sha256'])

reused = False
if os.path.lexists(destination):
    assert not os.path.islink(destination), 'the destination is a symlink'
    assert sha(destination) == measured, \
        'a DIFFERENT file already occupies %s; refusing to overwrite' % destination
    reused = True
else:
    os.path.isdir(os.path.dirname(destination)) or os.makedirs(
        os.path.dirname(destination))
    shutil.copyfile(source, destination)

written = sha(destination)
info = os.lstat(destination)
assert written == measured, 'the written bytes are %s' % written
assert os.path.isfile(destination) and not os.path.islink(destination)
assert info.st_nlink == 1, '%d links - not an independent copy' % info.st_nlink

print(json.dumps(collections.OrderedDict([
    ('kind', KIND), ('segment', SEGMENT),
    ('execution_path', destination), ('sha256', written),
    ('bytes', os.path.getsize(destination)),
    ('regular_file', True), ('hard_links', info.st_nlink),
    ('reused_identical_existing', reused),
    ('lanes', [a['lane_id'] for a in invocation['args']]),
    ('attempts', sorted({a['attempt'] for a in invocation['args']})),
]), indent=1))
