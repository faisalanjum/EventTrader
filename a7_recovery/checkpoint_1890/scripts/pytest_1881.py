# -*- coding: utf-8 -*-
"""Codex SEQ 1877: run a NAMED set of the affected G23 lifecycle tests.

One payload, one pytest child, one durable attempt directory. What to run is
given as A7_PYTEST_ARGS so an attempt is named by the caller, not guessed here.

WHY THE BASETEMP IS DURABLE: a green count is not evidence that the intended
boundary was reached (Codex SEQ 1877). pytest's tmp_path lives on the
boundary's tmpfs and vanishes with the namespace, so this points --basetemp at
the attempt's own durable directory and then INVENTORIES the artifacts the
tests actually wrote - the published root and receipt, the raw captures, the
accounting, the finalization and the bound whole answers. That inventory is
read off the tests' own output; no assertion here is weakened, added or
substituted for theirs.
"""
import collections, io, json, os, re, shlex, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
ATT = os.environ["A7_ATTEMPT_DIR"]
TAG = os.environ["A7_TAG"]
ARGS = shlex.split(os.environ["A7_PYTEST_ARGS"])

sys.path.insert(0, VIEW)
import a7_g1_build as G                                          # noqa: E402

# NO PYTHONPATH FORCING AND NO SEPARATE PROBE. Forcing the MAIN repo onto the
# path bound the wrong production owners, and an xbrl_attach probe could not
# see it because that file is byte-identical in both trees (Codex SEQ 1878).
# The test module itself now binds the RECOVERY package in native_1876's own
# import order and asserts the approved validators hash INSIDE the child; the
# pin it must match is passed through unchanged.
env = dict(os.environ)
route_module = ["asserted in-child against A7_DRIVER_VALIDATORS_SHA",
                env.get("A7_DRIVER_VALIDATORS_SHA", "UNSET")]

basetemp = os.path.join(ATT, "pytest_tmp")
op, ep = os.path.join(ATT, "pytest.stdout"), os.path.join(ATT, "pytest.stderr")
with io.open(op, "w", encoding="utf-8") as so, \
     io.open(ep, "w", encoding="utf-8") as se:
    rc = subprocess.Popen(
        [sys.executable, "-B", "-m", "pytest", "-q", "--no-header", "-rf",
         "-p", "no:cacheprovider", "--basetemp", basetemp] + ARGS,
        cwd=VIEW, stdout=so, stderr=se, text=True, env=env).wait()

txt = io.open(op, encoding="utf-8").read()
lines = [l for l in txt.strip().splitlines() if l.strip()]
summary = lines[-1] if lines else ""


def boundaries(root):
    """What the tests' own runs left on disk, per published run directory."""
    out = collections.OrderedDict()
    for base, dirs, _files in os.walk(root):
        for d in sorted(dirs):
            if not d.startswith("run_"):
                continue
            run = os.path.join(base, d)
            raw = os.path.join(run, G.RAW_DIRNAME)
            whole = os.path.join(run, G.WHOLE_DIRNAME)
            names = sorted(os.listdir(run))
            out[os.path.relpath(run, root)] = collections.OrderedDict([
                ("root", "root.json" in names),
                ("receipt", any(n.startswith("receipt.") for n in names)),
                ("accounting", any(n.startswith("accounting.") for n in names)),
                ("finalization",
                 any(n.startswith("finalization.") for n in names)),
                ("raw_captures",
                 len(os.listdir(raw)) if os.path.isdir(raw) else 0),
                ("whole_answer_files",
                 len(os.listdir(whole)) if os.path.isdir(whole) else 0),
            ])
    return out


inv = boundaries(basetemp) if os.path.isdir(basetemp) else {}
reached = collections.OrderedDict([
    ("run_dirs", len(inv)),
    ("published_root", sum(1 for v in inv.values() if v["root"])),
    ("published_receipt", sum(1 for v in inv.values() if v["receipt"])),
    ("raw_captured", sum(1 for v in inv.values() if v["raw_captures"])),
    ("accounted", sum(1 for v in inv.values() if v["accounting"])),
    ("finalized", sum(1 for v in inv.values() if v["finalization"])),
    ("whole_answers_bound",
     sum(1 for v in inv.values() if v["whole_answer_files"])),
])
res = collections.OrderedDict([
    ("tag", TAG), ("pytest_args", ARGS), ("child_exit", rc),
    ("summary", summary),
    ("failed_ids", re.findall(r"^FAILED (\S+)", txt, re.M)),
    ("error_ids", re.findall(r"^ERROR (\S+)", txt, re.M)),
    ("boundaries_reached", reached),
    ("per_run", inv),
    ("route_module", route_module),
    ("named", {k: os.environ.get(k) for k in
               ("A7_PRODUCER_IDENTITY", "A7_G1_PINS", "A7_G23_CANDIDATE",
                "A7_DRIVER_VALIDATORS_SHA")}),
])
io.open(os.path.join(ATT, "RESULT_%s.json" % TAG), "w",
        encoding="utf-8").write(json.dumps(res, indent=1, default=str))
print("child exit:", rc)
print(summary)
print("boundaries reached:", json.dumps(reached))
print("route module:", route_module[0])
if res["failed_ids"]:
    print("failed:", "\n         ".join(res["failed_ids"][:12]))
print("stderr tail:", "".join(io.open(ep, encoding="utf-8").readlines()[-4:]))
sys.exit(rc)
