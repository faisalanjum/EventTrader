V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
p = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
     "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/a7_g23_run.py")
s = io.open(p, encoding="utf-8").read(); o = s
s = s.replace('''        ("population_is_a_floor", True),
        ("rebuild_required_after", REBUILD_AFTER),
        ("floor_note",
         "A G2 pair is matched by the deterministic matcher or by an agreed "
         "G1 ruling; with G1 unrun only the first exists. These batches are "
         "owed however G1 rules, and G1 can only add more."),''',
'''        # THE TWO POPULATIONS MOVE IN OPPOSITE DIRECTIONS, so one flag for
        # both was simply false.
        ("g2_population_is_a_floor", True),
        ("g3_population_is_a_ceiling", True),
        ("rebuild_required_after", REBUILD_AFTER),
        ("floor_note",
         "A G2 pair is matched by the deterministic matcher or by an agreed "
         "G1 ruling; with G1 unrun only the first exists, so G1 can only ADD "
         "pairs. These G2 batches are a FLOOR."),
        ("ceiling_note",
         "A G3 obligation is a produced record the scorer still calls "
         "unresolved. A G1 ruling can MATCH such a record and remove its "
         "obligation, so G1 can only REMOVE extras. These G3 batches are a "
         "CEILING."),''')
assert s != o
io.open(p, "w", encoding="utf-8").write(s)
print("floor/ceiling split")
PY
cd "$V3"; rm -rf /tmp/a7_g23_route_audit /tmp/a7_g23_candidate2
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 2400 /home/faisal/EventMarketDB/venv/bin/python3 a7_g23_run.py /tmp/a7_g23_candidate2 2>&1 | grep -v WARNING | tail -10