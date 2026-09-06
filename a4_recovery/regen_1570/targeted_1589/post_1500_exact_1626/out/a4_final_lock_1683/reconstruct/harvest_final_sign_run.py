# -*- coding: utf-8 -*-
"""Harvest the ONE saved final-key signer call - no new call (Codex SEQ 1739).

The signer already ran once, in this session, and its official Workflow state is still in
the session store. This stage runs the recorded harvester over THAT state: the harvester
proves the state, the transcript, the prompt bytes, the launcher bytes, the model, effort,
agent type and zero tool use through the shared owners, saves the raw before parsing, and
parses only with build_kfields_final.read_signature.

The run id and attempt are the recorded ones; nothing here re-runs a model.
"""
import os, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
HARVEST = S + "/lock/harvest_final_sign.py"
RUN_ID, ATTEMPT = "wf_8dedf1de-a52", "1"

r = subprocess.run([PY3, "-B", "-u", HARVEST, RUN_ID, ATTEMPT], capture_output=True,
                   text=True, stdin=subprocess.DEVNULL, cwd=H, timeout=1800,
                   env=dict(os.environ, PYTHONPATH=H + ":/home/faisal/EventMarketDB"))
print((r.stdout or "").strip()[-2000:], flush=True)
if r.returncode:
    print((r.stderr or "")[-1200:], flush=True)
    sys.exit("REFUSE: the harvester returned %d (0 = signed, no lock without it)"
             % r.returncode)
print("HARVEST_OK", flush=True)
