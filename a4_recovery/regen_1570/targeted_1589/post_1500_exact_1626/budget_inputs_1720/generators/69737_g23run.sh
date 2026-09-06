V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
p = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
     "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/a7_g23_run.py")
s = io.open(p, encoding="utf-8").read(); o = s
s = s.replace('''def write(out_dir, primary=G.PRIMARY):''',
'''#: the ceiling the Work Order fixes. Not ours to move.
CEILING = 6000


def call_plan(g2_launchers, g3_launchers):
    """-> the WHOLE remaining bill, and a retry cap that fits under the ceiling.

    Every primary is counted, including the fresh exact-v3 producer run that
    the current G1 population does NOT yet reflect: G1 today grades v1 producer
    output, so its numbers are a diagnostic, not a frozen population.

    THE RETRY CAP IS HEADROOM, NOT A PER-ROW RESERVATION. Reserving one retry
    for every row would book more than twice the primaries for a failure mode
    measured at roughly one call in six hundred. The cap is simply what is left
    under the ceiling, declared as a hard stop, and reported beside the
    observed-rate expectation so nobody reads it as an expectation.
    """
    spent, _prov = G.all_prior_calls()
    producer = G.REQUIRED["answers"]
    g1 = len(G.GRADER_LANES) * G.freeze()[0]["batching"]["batches"]
    primaries = producer + g1 + g2_launchers + g3_launchers
    after = spent + primaries
    return collections.OrderedDict([
        ("spent_before", spent),
        ("producer_v3", producer),
        ("g1", g1), ("g2", g2_launchers), ("g3", g3_launchers),
        ("primaries", primaries),
        ("after_primaries", after),
        ("ceiling", CEILING),
        ("retry_cap", max(0, CEILING - after)),
        ("under_ceiling", after < CEILING),
        ("note", "G1/G2/G3 counts are shapes from v1 producer output and must "
                 "be re-derived after the fresh v3 producer run"),
    ])


def write(out_dir, primary=G.PRIMARY):''')
s = s.replace('''        ("made_calls", 0)])''',
'''        ("call_plan", call_plan(len(launch), 0) if False else
         call_plan(sum(1 for r in launch if r["batch_id"].startswith("G2-")),
                   sum(1 for r in launch if r["batch_id"].startswith("G3-")))),
        ("made_calls", 0)])''')
assert s != o
io.open(p, "w", encoding="utf-8").write(s)
print("call_plan added")
PY
cd "$V3"; rm -rf /tmp/a7_g23_route_audit /tmp/a7_g23_candidate3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 2400 /home/faisal/EventMarketDB/venv/bin/python3 -c "
import a7_g23_run as R, json
doc, prompts, problems = R.freeze()
print('problems:', problems[:2])
print(json.dumps(doc['call_plan'], indent=1))
" 2>&1 | grep -v WARNING | tail -20