V=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v2
cd "$V" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 1800 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io, json, os, sys
sys.path.insert(0, os.getcwd())
import a7_g1_build as G
import a7_g1_workflow_gate as W
OUT, RUN = "/tmp/a7_g1_v16_event", "/tmp/a7_g1_event_run4"
CAND = G._sha_file(os.path.join(OUT, G.CANDIDATE_NAME))
assert not os.path.exists(RUN), "run4 already exists"
print("candidate pin        :", CAND)

root, rsha, problems = G.freeze_root(OUT, RUN, CAND)
print("freeze_root problems :", problems)
print("root sha256          :", rsha)
print("root rows            :", len(root["rows"]))
print("root candidate       :", root["candidate_sha256"])
print("root prompt tree     :", root["prompt_tree_sha256"])
print("root rules block     :", root["rules_block_sha256"])
print("root max_attempts    :", root["max_attempts"])
print("root max_output      :", root["max_output_tokens"])
print("root lane pins       :", json.dumps(root["lane"], sort_keys=True))
print("ROOT OWNER MAP:")
for k, v in sorted(root["owners"].items()):
    print("   %-22s %s" % (k, v))

lanes, size, probs = W.next_admissible(OUT, RUN, rsha)
print("\nnext_admissible problems:", probs)
print("derived lanes           :", len(lanes), lanes)
print("predicted script bytes  :", size)
print("gate owner sha256       :", W.owner_sha256())
print("gate byte limit         :", W.SCRIPT_BYTE_LIMIT)
PY