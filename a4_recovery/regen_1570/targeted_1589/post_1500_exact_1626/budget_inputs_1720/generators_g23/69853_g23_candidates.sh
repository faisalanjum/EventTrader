V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
p = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
     "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/a7_g23_run.py")
s = io.open(p, encoding="utf-8").read(); o = s
s = s.replace('''def write(out_dir, primary=G.PRIMARY):''',
'''# ------------------------------------------- the task-kind seam, both ways --
#: each kind's own rules block; the batch owner renders exactly one of them
KIND_RULES = {"G2": B.meaning_rules, "G3": B.extras_rules}


def kind_binding(doc, batch_id):
    """The machine-only binding both G2 and G3 parsers need: the exact
    question ids this batch asked, reconstructed from the frozen candidate and
    never from the reply."""
    rows = [r for r in doc["batch_rows"] if r["batch_id"] == batch_id]
    if len(rows) != 1:
        raise ValueError("%s names %d batch rows" % (batch_id, len(rows)))
    return collections.OrderedDict([("question_ids",
                                     list(rows[0]["question_ids"]))])


G.register_task_kind("G2", kind_binding, B.read_meaning_reply)
G.register_task_kind("G3", kind_binding, B.read_extras_reply)


def kind_candidate(kind, doc, rows, identity):
    """ONE kind's candidate, in the shape the EXISTING lifecycle consumes.

    Same fields `freeze_root`, `prompt_tree_sha` and `load_frozen` already
    read for G1 - `batch_rows`, `launchers.owner_sha256`, `rules_block_sha256`
    - plus `task_kind`, which is the only new field and the only thing the
    seam dispatches on. Nothing here is a second lifecycle.
    """
    rules = KIND_RULES[kind]()
    launch = G.launchers(rows)
    return collections.OrderedDict([
        ("schema", SCHEMA), ("task_kind", kind),
        ("key_identity", identity),
        ("rules_block_sha256", G._sha(rules)),
        ("batch_rows", rows),
        ("batching", collections.OrderedDict([
            ("max_items_per_call", B.MAX_ITEMS_PER_CALL),
            ("batches", len(rows))])),
        ("launchers", collections.OrderedDict([
            ("owner_sha256", G.owner_hashes()["grade_batch_owner"]),
            ("count", len(launch)),
            ("lanes_per_batch", len(G.GRADER_LANES)),
            ("rows", launch)])),
        ("questions", sum(len(r["question_ids"]) for r in rows)),
        ("population", doc["g2"] if kind == "G2" else doc["g3"]),
        ("made_calls", 0)])


def write_kind(out_dir, kind, doc, prompts, identity):
    """Write ONE kind's candidate where the lifecycle expects to load it."""
    rows = [r for r in doc["batching"]["rows"]
            if r["batch_id"].startswith(kind + "-")]
    pdir = os.path.join(out_dir, PROMPT_DIRNAME)
    if not os.path.isdir(pdir):
        os.makedirs(pdir)
    for row in rows:
        with io.open(os.path.join(out_dir, row["prompt_path"]), "w",
                     encoding="utf-8") as fh:
            fh.write(prompts[row["batch_id"]])
    path = os.path.join(out_dir, G.CANDIDATE_NAME)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(G._pretty(kind_candidate(kind, doc, rows, identity)) + "\\n")
    return path, G._sha_file(path)


def write(out_dir, primary=G.PRIMARY):''')
assert s != o
io.open(p, "w", encoding="utf-8").write(s)
print("per-kind candidate writer + seam registration")
PY
cd "$V3" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 2400 /home/faisal/EventMarketDB/venv/bin/python3 -c "
import a7_g1_build as G, a7_g23_run as R, os, shutil
doc, prompts, problems = R.freeze()
assert not problems, problems[:2]
_key, identity = G.live_key()
for kind in ('G2', 'G3'):
    d = '/tmp/a7_%s_candidate' % kind.lower()
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    path, sha = R.write_kind(d, kind, doc, prompts, identity)
    print('%s -> %s  sha %s' % (kind, path.rsplit('/',1)[-1], sha[:16]))
    loaded, got = G.load_frozen(d, sha)
    print('   load_frozen OK | task_kind=%s | batch_rows=%d | rules=%s' % (
        G.task_kind(loaded), len(loaded['batch_rows']), loaded['rules_block_sha256'][:12]))
    b, pr = G.binding_and_parser(G.task_kind(loaded))
    print('   parser=%s | binding ids=%d' % (pr.__name__, len(b(loaded, loaded['batch_rows'][0]['batch_id'])['question_ids'])))
" 2>&1 | grep -v WARNING | tail -10