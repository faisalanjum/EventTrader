# -*- coding: utf-8 -*-
"""Reconstruct ONE demanded historical run - /tmp/a7_v3_prepared_run_1479 -
under its own era owner closure, inside the private boundary (Codex SEQ 1698).

The A6 ledger demands this run next. It is rebuilt by the recorded route only:
A5.prepare, A6.freeze/write, the one AUD.record_state of the one official state
the preserved inventory carries, and ONE a1_finalize - run under an interpreter
without lxml, which is the recorded condition its published refusal bytes were
produced under. Nothing is edited and no module is swapped in process: the era
owners arrive as read-only binds from the frozen v3 import closure, and the one
official state arrives through the read-only session-store bind.

Every published identity is checked against its pin BEFORE anything is
preserved, and the run tree is preserved only if every check holds - so a near
miss cannot enter the projection.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
HV = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
V3 = "/tmp/a7_v3_prepared_run_1479"
FREEZE = "/tmp/a7_a6_freeze_1479"
SESS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB"
        "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
NO_LXML_PY = "/usr/bin/python3"

PINS = json.load(io.open(os.environ["V3_PINS"], encoding="utf-8"))["pins"]
TSV = os.environ["V3_TSV"]
KEEP = os.environ["KEEP_DIR"]
LABEL = os.environ["V3_LABEL"]

# A destination a successful era already preserved is FINAL. Refuse before any
# work rather than rebuild over it, so a rerun can never delete or overwrite a
# proved run tree (Codex SEQ 1700).
DEST = os.path.join(KEEP, os.path.basename(V3))
if os.path.exists(DEST):
    print("REFUSED: %s is already preserved; a proved run is never rebuilt over"
          % DEST)
    raise SystemExit(4)

CHECKS = []


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %s : %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:88],
                            "" if ok else "  != %s" % str(want)[:88]), flush=True)
    return ok


rows = [l.split("\t") for l in io.open(TSV, encoding="utf-8").read().splitlines()[1:]]
row = [r for r in rows if r[0] == LABEL]
check("the inventory carries exactly one state for this run", len(row), 1)
wf = row[0][1]
sp = SESS + "/workflows/%s.json" % wf
check("the one official state is readable at its historical path", os.path.isfile(sp), True)
check("official state sha256 == inventory", fsha(sp), PINS["state"])

os.chdir(HV)
sys.path.insert(0, HV)
import build_a5_exp5_kit as A5           # noqa: E402
import a6_launch_freeze as A6            # noqa: E402
import audit_worker_access as AUD        # noqa: E402
import raw_transport as RT               # noqa: E402
import build_kfields_final as F          # noqa: E402

got = A5.prepare(V3)
check("A5.prepare ok", got.get("ok"), True)
check("A5.prepare problems", list(got.get("problems") or []), [])
check("zero-state receipt", fsha(V3 + "/receipt.json"), PINS["zero_state_receipt"])
check("plan manifest", fsha(V3 + "/plan/a5_exp5_reader.manifest.json"), PINS["manifest"])
check("launcher bundle", fsha(V3 + "/plan/a5_launcher.bundle.json"), PINS["bundle"])

rec0 = json.load(io.open(V3 + "/receipt.json", encoding="utf-8"))
check("receipt schedules 392 calls, zero states",
      (len(rec0["allowed"]), len(rec0.get("states") or [])), (392, 0))
check("receipt max_output_tokens", str(rec0.get("max_output_tokens")), "128000")

doc = A6.freeze(V3)
check("A6 freeze problems", list(A6.problems(doc) or []), [])
A6.write(V3, FREEZE)
check("freeze doc", fsha(FREEZE + "/a6_exp5_launch_freeze.json"), PINS["freeze"])

AUD.record_state(V3 + "/receipt.json", rec0["run_id"], sp)
check("state-bound receipt", fsha(V3 + "/receipt.json"), PINS["state_bound_receipt"])
rec1 = json.load(io.open(V3 + "/receipt.json", encoding="utf-8"))
check("the receipt now holds the one official state",
      [os.path.basename(x)[:-5] for x in rec1["states"]], [wf])

# ONE finalize, under the recorded no-lxml interpreter, so its refusal bytes
# are the published ones.
check("the finalize interpreter has no lxml (the recorded condition)",
      subprocess.run([NO_LXML_PY, "-c", "import lxml"], capture_output=True).returncode != 0,
      True)
drv = S + "/v3_finalize_driver.py"
io.open(drv, "w", encoding="utf-8").write(
    "import json, raw_transport as RT\n"
    "out = RT.a1_finalize(%r)\n"
    "print(json.dumps({'ledger': out['ledger'], 'validity_n': len(out['validity']),"
    " 'retry': out['retry'], 'attempt': out['attempt'],"
    " 'outcomes': dict(__import__('collections').Counter(o[1] for o in out['outcomes']))}))\n" % V3)
# the driver lives in the writable scratch root, so the harness has to be on
# its import path explicitly - cwd alone does not put it there
p = subprocess.run([NO_LXML_PY, "-B", drv], cwd=HV, capture_output=True, text=True,
                   env=dict(os.environ, PYTHONPATH=HV))
print((p.stdout or "")[-800:])
if p.returncode:
    print((p.stderr or "")[-1500:])
check("finalize driver rc", p.returncode, 0)
jl = [l for l in p.stdout.splitlines() if l.startswith("{")]
fj = json.loads(jl[-1]) if jl else None
check("finalize called once (attempt 1, no retry)", (fj and fj["attempt"], fj and fj["retry"]), (1, []))
check("published finalization == pinned refusal",
      fsha(V3 + "/finalization.json"), PINS["finalization"])
check("closeout ledger", fj and fj["ledger"],
      {"integrity_refusal": 18, "spawned_without_answer": 374, "scheduled": 392, "missing": 0})
check("closeout has zero validity rows and no retry", (fj and fj["validity_n"], fj and fj["retry"]), (0, []))
check("closeout classification", fj and fj["outcomes"], {"served": 18})
check("answers/ is absent (a refusal, not accepted answers)", os.path.exists(V3 + "/answers"), False)

raw = F.raw_tree(V3)
check("raw tree over 18 files == pinned", (raw["sha256"], raw["files"]), (PINS["raw_tree"], 18))
shell_raw = subprocess.run("cd %s/raw && sha256sum * | sha256sum | cut -d' ' -f1" % V3,
                           shell=True, capture_output=True, text=True).stdout.strip()
check("historical shell-form raw digest == pinned", shell_raw, PINS["shell_raw"])

# the era transport has no raw<->rows binding owner; that check belongs to a
# LATER transport, and calling it here would be an anachronism. The era proves
# the same thing through the row count and the pinned raw tree above.
rows18 = RT.a1_readable_rows(rec1["states"])
check("18 official returned rows", len(rows18), 18)

bad = [n for n, ok in CHECKS if not ok]
print("checks: %d  failed: %d  %s" % (len(CHECKS), len(bad), bad[:6]), flush=True)
if bad:
    print("REFUSED: nothing preserved")
    sys.exit(2)

dst = DEST
shutil.copytree(V3, dst)
check("preserved copy receipt", fsha(dst + "/receipt.json"), PINS["state_bound_receipt"])
check("preserved copy finalization", fsha(dst + "/finalization.json"), PINS["finalization"])
if [n for n, ok in CHECKS if not ok]:
    shutil.rmtree(dst)
    print("REFUSED: preserved copy mismatch")
    sys.exit(3)
print("PRESERVED %s" % dst)
