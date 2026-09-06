# -*- coding: utf-8 -*-
"""Run the existing final-candidate test gate the way it is meant to run (Codex SEQ 1739).

The gate is a pytest module and has no executable main: running it as a plain script runs
NOTHING. This stage is the recorded invocation (original 87488) - pytest, from $S/lock, with
importlib import mode and no cache - over the module that lives there.

It is a gate, not a report: a non-zero return code fails, and so does a run that collected
nothing or skipped a test, because the candidate-dependent tests skip themselves when the
candidate is absent and a skip must never read as a pass.
"""
import hashlib, io, os, re, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
LOCK = S + "/lock"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
MODULE = "check_final_key_candidate.py"
WANT_MODULE = "dd4e321d7009887da0813fda85badbfe78083f86c887c3283cd277126c48151d"

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
got = sha(os.path.join(LOCK, MODULE))
print("test module %s  %d bytes" % (got, os.path.getsize(os.path.join(LOCK, MODULE))), flush=True)
if got != WANT_MODULE:
    sys.exit("REFUSE: the bound test module is not the recorded gate")

#: THE FROZEN SELECTION (Codex SEQ 1741 item 2): the four cases whose execution is still
#: owed today. The rest of this module is covered by the actual historical execution at
#: original 87726/87817, its single-test patch 87823 and the passing rerun 87835, and is
#: REUSED, not claimed as executed here.
SELECTED = ("test_a_composed_event_is_shown_as_its_two_real_component_raws",
            "test_the_signer_gate_is_frozen_and_never_retries_meaning",
            "test_the_composed_row_maps_are_exported_by_the_composition_owner_and_verified_independently",
            "test_the_resolved_history_definitions_precede_the_boundary_and_the_launcher_carries_the_same_prompt")
r = subprocess.run([PY3, "-B", "-m", "pytest"]
                   + ["%s::%s" % (MODULE, t) for t in SELECTED]
                   + ["--import-mode=importlib",
                    "-p", "no:cacheprovider", "-q", "--no-header", "-rfEs"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=LOCK,
                   timeout=3600, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
out = (r.stdout or "") + (r.stderr or "")
print(out.strip()[-4000:], flush=True)
print("pytest rc=%s" % r.returncode, flush=True)
tail = [l for l in out.strip().splitlines() if re.search(r"\b\d+ (passed|failed|error|skipped)", l)]
line = tail[-1] if tail else ""
counts = dict((k, int(n)) for n, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|xfailed)", line))
print("outcomes %s" % counts, flush=True)
if r.returncode:
    sys.exit("REFUSE: the test gate failed")
if counts.get("passed") != len(SELECTED):
    sys.exit("REFUSE: %r passed, not the %d selected cases"
             % (counts.get("passed"), len(SELECTED)))
if counts.get("skipped") or counts.get("failed") or counts.get("error") or counts.get("errors"):
    sys.exit("REFUSE: a skipped or failing test is not a pass (%s)" % counts)
print("executed today:", ", ".join(SELECTED), flush=True)
print("CHECK_CANDIDATE_OK", counts, flush=True)
