#!/usr/bin/env python3
"""EXP-0: verify uploaded verdict files against the run's recorded content hashes + structure (0 LLM).
Exit nonzero if any file is corrupt/short so scoring does not proceed on bad data. args: RUNDIR KEY"""
import json
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/harness")
import key_lint as K

RUNDIR, KEY = sys.argv[1], sys.argv[2]
# FILE_H32 values returned by the completed v1.2 run (workflow wgit9tlr6)
EXPECT = {"g_sonnet_a": 2163886048, "g_sonnet_b": 2197237812, "g_opus": 2181820746}
keyset = set(r["pair_id"] for _l, r in K.load_records(KEY))
ok = True
for arm, exp in EXPECT.items():
    f = RUNDIR + "/verdicts." + arm + ".json"
    raw = open(f, encoding="utf-8").read().rstrip("\n")
    h = K.h32(raw)
    blob = json.loads(raw)
    pids = [v["pair_id"] for v in blob["verdicts"]]
    h_match = (h == exp)
    struct = (len(pids) == 160 and set(pids) == keyset
              and all(v.get("verdict") in ("SAME", "DIFFERENT", None) for v in blob["verdicts"]))
    ok = ok and struct and h_match
    print("%-12s h32=%d expect=%d %s | struct_ok=%s (n=%d pids_match=%s invalid=%d)"
          % (arm, h, exp, "HASH_MATCH" if h_match else "HASH_MISMATCH", struct, len(pids), set(pids) == keyset, blob.get("invalid")))
print("ALL_VERIFIED", ok)
sys.exit(0 if ok else 4)
