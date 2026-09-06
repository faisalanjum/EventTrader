V=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v2
OUT=/tmp/a7_g1_v16_event
[ -d "$OUT" ] && chmod -R u+w "$OUT"; rm -rf "$OUT"
cd "$V" && timeout 1800 /home/faisal/EventMarketDB/venv/bin/python3 - "$OUT" <<'PY'
import io, json, os, sys
sys.path.insert(0, os.getcwd()); import a7_g1_build as G
out=sys.argv[1]
path, problems = G.write(out); print("problems:", problems)
doc, sha = G.load_frozen(out, G._sha_file(path))
print("candidate sha256  :", sha)
print("schema            :", doc["schema"])
b=doc["budget"]
print("BUDGET spent_before=%d initial=%d after_initial=%d after_max=%d ceiling=%d under=%s"
      % (b["spent_before"], b["initial_grader_calls"], b["after_initial"],
         b["after_max"], b["ceiling"], b["under_ceiling"]))
pv=b["prior_g1_calls"]
print("prior G1 provenance: run_dir=%s total=%d files=%d" % (pv["run_dir"], pv["total"], len(pv["files"])))
print("  first file       : %s scheduled=%d" % (os.path.basename(pv["files"][0]["path"]), pv["files"][0]["scheduled"]))
print("owners pinned      :", ", ".join(sorted(doc["launchers"] and G.owner_hashes())))
print("events/calls       :", len(doc["batch_rows"]), "/", doc["launchers"]["count"])
print("armed_calls        :", doc["armed_calls"])
print("questions/produced :", doc["questions"], "/", sum(len(r["produced_idxs"]) for r in doc["batch_rows"]))
sz=sorted(r["prompt_bytes"] for r in doc["batch_rows"])
print("bytes min/med/max/total:", sz[0], sz[len(sz)//2], sz[-1], sum(sz))
print("prompt tree        :", G.prompt_tree_sha(out, doc))
print("rules sha          :", doc["rules_block_sha256"])
PY
chmod -R a-w "$OUT"
echo "rebuild determinism:"
cd "$V" && timeout 1800 /home/faisal/EventMarketDB/venv/bin/python3 -c "
import os,sys,tempfile; sys.path.insert(0,os.getcwd()); import a7_g1_build as G
d=tempfile.mkdtemp(); p,_=G.write(d); print(' second build:', G._sha_file(p))"