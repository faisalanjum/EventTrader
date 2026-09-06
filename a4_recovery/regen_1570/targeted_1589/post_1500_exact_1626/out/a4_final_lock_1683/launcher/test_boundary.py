# -*- coding: utf-8 -*-
"""Smallest recovery-boundary test (Codex SEQ 1683 step1 / 1687): one positive,
three ordered negatives, host /tmp proven clean before and after. No owners."""
import io, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
BOUND = os.path.join(HERE, "boundary.py")
PAYLOAD = os.path.join(HERE, "payload_probe.py")
VP = sys.executable
R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a4_recovery/regen_1570/targeted_1589"
SRC = T + "/targeted_run_1491/out/attempt6/A"            # real durable run_dir
LOGICAL = "/tmp/a4_targeted_run_1491"                     # its identity-bearing name
HOST_MARKERS = ["/tmp/a4_targeted_run_1491", "/tmp/a4_hard_review_run_1495",
                "/tmp/a4_final_targeted_run_1500", "/tmp/a4_boundary_out"]

sys.path.insert(0, HERE)
import boundary  # noqa: E402

def host_clean():
    return [m for m in HOST_MARKERS if os.path.exists(m)]

def run(mapfile, payload=PAYLOAD):
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([VP, "-B", BOUND, "--host", mapfile, payload],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr

def write_map(path, rows):
    io.open(path, "w", encoding="utf-8").write("".join("\t".join(r) + "\n" for r in rows))

OUT = []
tmp = tempfile.mkdtemp(prefix="boundary_test_", dir=HERE)  # NOT /tmp: tmpfs would shadow it in the ns
outdir = os.path.join(tmp, "out"); os.makedirs(outdir)
sha_ok = boundary.source_sha(SRC)               # correct dir-manifest sha (host truth)

leaked_before = host_clean()

# POSITIVE: valid ro input bind + rw output bind; payload resolves + re-proves inside ns
posmap = os.path.join(tmp, "pos.tsv")
write_map(posmap, [[LOGICAL, SRC, sha_ok, "ro"],
                   ["/tmp/a4_boundary_out", outdir, "-", "rw"]])
rc, so, se = run(posmap)
prod = os.path.isfile(os.path.join(outdir, "probe.txt"))
OUT.append(("positive", rc == 0 and "PAYLOAD_OK" in so and "ro_enforced=True" in so and prod and not host_clean(),
            "rc=%s out=%r prod=%s host_leak=%s" % (rc, so.strip(), prod, host_clean())))

# NEG-A: missing bind target -> refuse before any namespace
nam = os.path.join(tmp, "na.tsv"); write_map(nam, [[LOGICAL, SRC + "__nope", sha_ok, "ro"]])
rc, so, se = run(nam)
OUT.append(("neg_missing_target", rc == 3 and "missing bind target" in se and not host_clean(),
            "rc=%s se=%r host_leak=%s" % (rc, se.strip(), host_clean())))

# NEG-B: changed bound byte (sha mismatch) -> refuse
nbm = os.path.join(tmp, "nb.tsv"); bad = "0" * 64; write_map(nbm, [[LOGICAL, SRC, bad, "ro"]])
rc, so, se = run(nbm)
OUT.append(("neg_changed_byte", rc == 3 and "sha mismatch" in se and not host_clean(),
            "rc=%s se=%r host_leak=%s" % (rc, se.strip(), host_clean())))

# NEG-C: logical path escapes the /tmp map -> refuse
ncm = os.path.join(tmp, "nc.tsv"); write_map(ncm, [["/tmp/../etc/a4_escape", SRC, sha_ok, "ro"]])
rc, so, se = run(ncm)
OUT.append(("neg_escape_map", rc == 3 and "escape" in se and not host_clean(),
            "rc=%s se=%r host_leak=%s" % (rc, se.strip(), host_clean())))

leaked_after = host_clean()
shutil.rmtree(tmp, ignore_errors=True)

lines = ["Recovery-boundary test (Codex SEQ 1683 step1 / 1687)  venv=%s" % VP,
         "positive source: %s" % SRC, "dir-manifest sha: %s" % sha_ok,
         "host markers clean before: %s   after: %s" % (not leaked_before, not leaked_after), ""]
allok = not leaked_before and not leaked_after
for name, ok, detail in OUT:
    allok = allok and ok
    lines.append("[%s] %-20s %s" % ("ok" if ok else "BAD", name, detail))
lines.append(""); lines.append("SUMMARY: %s" % ("BOUNDARY HOLDS" if allok else "BOUNDARY FAILED"))
io.open(os.path.join(HERE, "BOUNDARY.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if allok else 1)
