"""Read-only check of the old hard-review run with its matching package."""
import hashlib
import json
import os
import sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
sys.path.insert(0, X + "/harness_g1v3")
import a6_launch_freeze as A6
import build_kfields_final as F
import build_kfields_hard_review as HR
import a7_g1_build as G

bound = A6.bound()._replace(hr_package=X + "/kfields_hard_review")
receipt = json.load(open(bound.hr + "/receipt.json"))
path = bound.hr_package + "/" + HR.MANIFEST_NAME
assert hashlib.sha256(open(path, "rb").read()).hexdigest() == receipt["manifest_sha256"]
result = {"bound": bound._asdict()}
try:
    shards, raws, origins, problems = F.v6_shards(bound)
    result.update(shards=len(shards), problems=problems)
    if not problems:
        key, sidecar, problems = F.materialize(bound.evidence, shards)
        result.update(key_sha256=G._sha(G._plain(key)), materialize_problems=problems)
except Exception as exc:
    result["error"] = str(exc)
with open(os.environ["A7_ATTEMPT_DIR"] + "/HISTORICAL_PROBE.json", "x") as stream:
    json.dump(result, stream, indent=2, default=str)
print(json.dumps(result, indent=2, default=str))
