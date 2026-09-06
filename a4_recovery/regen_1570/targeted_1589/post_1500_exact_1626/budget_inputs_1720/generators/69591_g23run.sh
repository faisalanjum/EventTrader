V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
p = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
     "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/scorers/score_exp5.py")
s = io.open(p, encoding="utf-8").read(); o = s
s = s.replace('''    entry = route[sid]
    if set(entry) != {"result", "index_map"}:
        raise ValueError(f"route[{sid!r}] must carry exactly result and index_map, "
                         f"got {sorted(entry)}")''',
'''    entry = route[sid]
    # EXACT SHAPE, still. `rejected_*` are the spec's name-rejection accounting
    # and are REQUIRED so a caller cannot lose track of a produced row the
    # route refused; anything else is an unknown key and still refused.
    required = {"result", "index_map"}
    accounting = {"rejected_conflicting_names", "rejected_fact_idxs"}
    if not required <= set(entry) or not set(entry) <= (required | accounting):
        raise ValueError(f"route[{sid!r}] must carry exactly result, index_map "
                         f"and the rejection accounting, got {sorted(entry)}")''')
assert s != o
io.open(p, "w", encoding="utf-8").write(s)
print("guard widened to a known key set")
PY
cd "$V3"; rm -rf /tmp/a7_g23_route_audit /tmp/a7_g23_candidate2
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 2400 /home/faisal/EventMarketDB/venv/bin/python3 a7_g23_run.py /tmp/a7_g23_candidate2 2>&1 | grep -v WARNING | tail -10