"""Does this segment's failure repeat the defect G2 already demonstrated?

Codex SEQ 2105: if G3 shows the same systematic quoted-null/format problem,
preserve the evidence and STOP rather than multiplying a known defect. So the
retry has to be gated on whether the reason is new or already known.

The known signature is READ from G2's own finalizations, never typed here - if
G2's recorded reasons change, this follows them, and a genuinely new G3 reason
is not silently swept into the known bucket.

    python3 -B known_defect_2105.py <finalization path>
prints REPEATS_KNOWN_DEFECT or NEW_OR_NONE.
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
UNIT = os.path.join(A7, 'unit_2103_g23_grading')
FINALIZATION = sys.argv[1]
#: the kind whose failures are already diagnosed and owned by Codex
KNOWN_FROM = 'G2'


def reasons_of(path):
    """The reason texts a finalization records, with question ids stripped."""
    doc = json.load(io.open(path))
    out = set()
    for lane, problems in (doc.get('problems') or {}).items():
        for why in problems:
            out.add(why.split(' ', 1)[-1])
    return out


known = set()
for path in glob.glob(os.path.join(UNIT, KNOWN_FROM, 'run',
                                   'finalization.seg*.json')):
    known |= reasons_of(path)

mine = reasons_of(FINALIZATION)
repeats = sorted(mine & known)
novel = sorted(mine - known)

print('known %s reasons: %d' % (KNOWN_FROM, len(known)))
for why in sorted(known):
    print('   known : %s' % why[:90])
for why in repeats:
    print('   REPEAT: %s' % why[:90])
for why in novel:
    print('   NEW   : %s' % why[:90])
print('REPEATS_KNOWN_DEFECT' if repeats else 'NEW_OR_NONE')
