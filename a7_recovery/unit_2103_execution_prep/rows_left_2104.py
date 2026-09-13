"""How many root primary rows this run still needs called.

REUSES THE ORIGINAL OWNER. G.lane_states decides each primary lane's current
state from the finalizations' `uncalled` lists, taking only attempt-1 segments
and letting the LATEST one that names a lane decide it.

The earlier version unioned every finalization's `validity` rows instead. The
transport-refusal closure writes validity [[lane, False], ...] AND uncalled
[lanes] for the SAME lanes (a7_g1_workflow_gate.py lines 476 and 479), so a
finalized-but-never-called primary appeared in validity and was counted as
finished - the driver would then stop with real rows still uncalled. Codex
SEQ 2109 raised it; unit_2109_rowsleft_check reproduces it and this fixes it.

No second lane-state or retry engine is introduced here.
"""
import io
import json
import os
import sys

#: the durable owner location, beside this unit either on the host or under the
#: boundary mount - the same bytes the map serves as the harness view.
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'unit_2006/harness_g1v3')
if HARNESS not in sys.path:
    sys.path.insert(0, HARNESS)
import a7_g1_build as G                                            # noqa: E402

run = sys.argv[1]
root = json.load(io.open(os.path.join(run, 'root.json')))
states = G.lane_states(run)
print(len([r['lane_id'] for r in root['rows']
           if states.get(r['lane_id']) != 'called']))
