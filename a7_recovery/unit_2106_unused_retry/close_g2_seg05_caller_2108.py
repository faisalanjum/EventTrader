"""The one-shot caller for the REAL G2 segment-5 closure. NOT run yet.

Every owner it depends on is pinned EXTERNALLY, by a value written here as the
constant it is and compared before use - including the closure file itself, so
this is a pinned executable rather than a prose instruction. A prose call with
no closure hash check would let an edited closure run under a reviewed name.

Runs inside the boundary through the existing operator, because the receipt's
invocation and state paths only resolve under the mount. Zero model calls.
"""
import hashlib
import io
import json
import os
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
HERE = os.path.join(A7, 'unit_2106_unused_retry')
FORMAT_DIR = os.path.join(A7, 'unit_2020_codex_check')
VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl')
LAUNCH_PATH = os.path.join(A7, 'unit_2103_g23_grading/G2/LAUNCH.json')
SEGMENT = 5

#: EXTERNAL PINS. Supplied, never measured-and-accepted.
EXPECT_CLOSURE = 'e72647b3a0d3f5a4ffddd7752ff18dd32229cf87dfea540141cc4189f3a96998'
EXPECT_GATE = 'e2386da5f64260acdc7da1a1b44c40c3fcad5a624affd3755b01448ce32d0703'
EXPECT_CODE = '7aeabc6b236d425de3fed02c250f1cf3744296107015d273fb2c395e8fa680f8'
EXPECT_RULE = '76b83ceb2dcf0bb6079c90399c103df7aa0a3cca29dbc411d918ffc89b66881b'
EXPECT_ROOT = '1ee010cf06a9a726c5e12c4893031dbdad075f4f39a09c0f92298bbafa8a6a18'
EXPECT_RECEIPT = 'b04fe0d4668b9be916a855a6146b1dcfbd83b920e221d124afff7fd8d67b80b2'


def sha_file(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


closure_file = os.path.join(HERE, 'a7_unused_retry_closure_2106.py')
got = sha_file(closure_file)
if got != EXPECT_CLOSURE:
    raise SystemExit('REFUSED: the closure file is %s, not the approved %s'
                     % (got, EXPECT_CLOSURE))

sys.path[:0] = [HERE, VIEW, FORMAT_DIR, os.path.join(A7, 'unit_2009/owner')]
os.chdir(VIEW)
import a7_unused_retry_closure_2106 as CL                          # noqa: E402
import a7_g1_build as G                                            # noqa: E402
import a7_g23_build as B                                           # noqa: E402

launch = json.load(io.open(LAUNCH_PATH))
B.bind_grading_scorer(
    os.path.join(os.path.dirname(G.__file__), 'scorers/score_exp5_current.py'),
    launch['owners']['grading_scorer'])

final, problems = CL.close(
    VIEW, FORMAT_DIR, launch['candidate_dir'], launch['run_dir'], SEGMENT,
    EXPECT_ROOT, EXPECT_RECEIPT, EXPECT_GATE, EXPECT_CODE, EXPECT_RULE,
    SESSION)
print(G._plain({'closed': final is not None, 'problems': problems,
                'final': final, 'closure_sha256': got, 'model_calls': 0}))
raise SystemExit(0 if final is not None else 1)
