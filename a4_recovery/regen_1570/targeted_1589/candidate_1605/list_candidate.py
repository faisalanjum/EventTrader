"""The candidate tree of targeted_run_1491 (Codex SEQ 1605): inputs + code + pins + the derived owner and its
derivation table, and (with 'full') the accepted outputs of out/attempt6. Three files are PROVENANCE-ONLY recovery evidence, never
opened at runtime and no dependency of any world: derive_owner_1491.py, OWNER_DERIVATION.tsv and
inputs/binding_heredoc_82632.txt (the fourth column names the class). Excluded by construction: out/attempt1
(the failed probe), out/attempt2 (the test-defect run), out/attempt3 (green, closure classes unnormalized), out/attempt4 (green, absolute paths in two tables), out/attempt5 (green, two mislabeled test bodies), out/failed_1603 (the zero-pair owner and table, the interrupted substitute), out/probe_*,
and every tooling directory. Paths are printed relative to the repository root, sha256 and size beside them."""
import hashlib, io, os, sys
REPO = "/home/faisal/EventMarketDB-driver-recovery"; REL = "a4_recovery/regen_1570/targeted_1589/targeted_run_1491"; U = REPO + "/" + REL
def tree(rel):
    out = []
    for dp, dn, fn in os.walk(U + "/" + rel):
        for f in fn: out.append(os.path.relpath(os.path.join(dp, f), U))
    return sorted(out)
paths = ["recover_run_1491.py", "run_1491.sh", "test_run_1491.py", "derive_owner_1491.py", "build_kfields_key_targeted.py", "OWNER_DERIVATION.tsv", "pins_1601.json"] + tree("inputs")
if len(sys.argv) > 1 and sys.argv[1] == "full":
    paths += tree("out/attempt6") + ["out/attempt6_world_log.txt"]
PROVENANCE = {"derive_owner_1491.py", "OWNER_DERIVATION.tsv", "inputs/binding_heredoc_82632.txt"}
for p in sorted(paths):
    b = open(U + "/" + p, "rb").read(); print("%s/%s\t%s\t%d\t%s" % (REL, p, hashlib.sha256(b).hexdigest(), len(b), "provenance" if p in PROVENANCE else "candidate"))
