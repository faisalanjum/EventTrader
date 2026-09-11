"""Read the exact saved TEST signature failure; generate nothing."""
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT / 'TEST_codex_join2009_a/TEST_RESULT.json').read_text())
os.environ.pop('A7_APPROVED_KEY_DIR', None)
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R
sys.path.insert(0, str(UNIT.parent / 'unit_1955/lock_owners'))
import signer_proof as SP
with R.candidate_scope(saved['review'], saved['review_package'],
                       saved['key_run'], saved['key_package']):
    session = '/home/faisal/.claude/projects/-home-faisal-EventMarketDB/' + R.K.PARENT_SESSION
    proof, bad = SP.prove(saved['candidate'] + '/signer', saved['signer_manifest'],
                          1, 'wf_TEST_signature_codex_signed2009_b', session, {})
    print(json.dumps({'proof':proof, 'problems':bad}, indent=1))
