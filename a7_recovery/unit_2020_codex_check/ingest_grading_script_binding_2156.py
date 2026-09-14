"""Use the unchanged collection operator with the reviewed location binding.

No Workflow call is made. Only the already completed, externally named run
is ingested; the original publication and native records remain untouched.
"""
import json
import os
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_grading_script_binding_2156 as T

if os.environ['A7_GRADING_COMMAND'] != 'ingest':
    raise ValueError('this bounded entry only ingests the completed run')
operator = HERE / 'run_grading_2086.py'
assert G._sha_file(str(operator)) == 'd9c3f598fd0ecc2ac5714403cc6e75d25ae3e0c1c48484eacafbad8906827c78'
with T.scope(os.environ['A7_SCRIPT_BINDING'], json.loads(os.environ['A7_SCRIPT_BINDING_PINS'])):
    runpy.run_path(str(operator), run_name='__main__')
