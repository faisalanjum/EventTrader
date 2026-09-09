"""Reproduce the old key with its frozen owners, ONLY as historical test data.

This does not qualify an old run under the current key/signing workflow.
The current workflow is tested separately against the current native fixture.
"""
import hashlib
import json
import os
import pickle
import sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness"
sys.path.insert(0, H)
import a6_launch_freeze as A6
import a7_g1_build as G
import a7_key_correction as KC
import build_kfields_final as F
import build_kfields_hard_review as HR

out = os.environ["A7_ATTEMPT_DIR"]
os.makedirs(out, exist_ok=True)
bound = A6.bound()
lock = G._read(os.path.join(A6._read_ptr("signer_dir.txt"), "a4_detailed_key_lock_v6.json"))
for owner, module in (("final_owner_loader", F), ("hard_review_owner", HR),
                      ("a4_key_owner", F.K)):
    assert os.path.dirname(module.__file__) == H, module.__file__
    assert G._sha_file(module.__file__) == lock["bound_owners"][owner]
key, sidecar = G.gold_by_event()
corrected, problems = KC.apply(key, KC.load())
assert problems == [], problems
assert json.loads(G._plain(corrected)) == G._read("/tmp/a7_key_v9_gold.json")
path = out + "/historical_v6_key.TEST.pickle"
with open(path, "xb") as stream:
    pickle.dump((key, sidecar), stream, protocol=4)
result = {"label": "HISTORICAL_TEST_DATA_NOT_CURRENT_KEY_APPROVAL",
          "fixture": path, "sha256": G._sha_file(path),
          "v6_lock_sha256": G._sha_file(os.path.join(A6._read_ptr("signer_dir.txt"), "a4_detailed_key_lock_v6.json")),
          "corrected_saved_sha256": G._sha_file("/tmp/a7_key_v9_gold.json"),
          "base_facts": sum(len(fs) for fs in key.values()),
          "corrected_facts": sum(len(fs) for fs in corrected.values()),
          "loaded_modules": {n: m.__file__ for n, m in sys.modules.items()
                             if getattr(m, "__file__", "").startswith(H)}}
with open(out + "/HISTORICAL_KEY_FIXTURE.json", "x") as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))
