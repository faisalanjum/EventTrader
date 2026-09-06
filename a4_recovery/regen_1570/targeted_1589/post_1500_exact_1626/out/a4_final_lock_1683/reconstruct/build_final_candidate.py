# -*- coding: utf-8 -*-
"""Run the actual final-candidate builder once (Codex SEQ 1739).

The builder is the recorded one (original 87448 whole write carried by the recorded edit at
87696); it materializes the 196-item candidate and freezes the unrun signer packet through
the owners alone. Nothing here decides anything: this stage only runs it and reports what it
wrote. The two-identical-builds proof is the checker's own first test.
"""
import hashlib, io, os, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
BUILDER = S + "/lock/build_final_key_candidate.py"
WANT_BUILDER = "c9235c77fb018b22b7c54d7058c4bb8b54338df89800ebf29438433b937d4ab4"

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
got = sha(BUILDER)
print("builder %s  %d bytes" % (got, os.path.getsize(BUILDER)), flush=True)
if got != WANT_BUILDER:
    sys.exit("REFUSE: the bound builder is not the recorded one")
r = subprocess.run([PY3, "-B", "-u", BUILDER], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, cwd=H, timeout=1800,
                   env=dict(os.environ, PYTHONPATH=H + ":/home/faisal/EventMarketDB"))
print((r.stdout or "").strip()[-2500:], flush=True)
if r.returncode:
    print((r.stderr or "")[-1500:], flush=True)
    sys.exit("REFUSE: the candidate builder did not run")
sys.path.insert(0, S + "/lock")
import build_final_key_candidate as C                              # noqa: E402
out = C.DEFAULT_OUT
if not os.path.isdir(out):
    sys.exit("REFUSE: %s was not written" % out)
for dp, _dn, fn in os.walk(out):
    for f in sorted(fn):
        q = os.path.join(dp, f)
        print("   %-58s %s" % (os.path.relpath(q, out), sha(q)[:16]), flush=True)
problems = C.verify(out)
print("verify problems:", problems, flush=True)
# Anything the verifier reports is a refusal, whatever it says: this stage may not
# declare success over a candidate its own verifier does not accept.
if problems:
    sys.exit("REFUSE: the verifier reported problems: %r" % (problems,))
print("BUILD_CANDIDATE_OK", flush=True)
