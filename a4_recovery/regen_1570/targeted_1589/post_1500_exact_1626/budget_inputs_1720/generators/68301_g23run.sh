V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
p = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
     "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/a7_g23_build.py")
s = io.open(p, encoding="utf-8").read(); o = s

# expose the rendered question rows so a BATCH can carry the rules exactly once
s = s.replace('''    return collections.OrderedDict([
        ("leg", leg), ("source_id", source_id),
        ("pairs", [list(p) for p in pairs]),
        ("question_ids", [q["question_id"] for q in questions]),
        ("prompt", text), ("prompt_sha256", G._sha(text))])''',
'''    return collections.OrderedDict([
        ("leg", leg), ("source_id", source_id),
        ("pairs", [list(p) for p in pairs]),
        ("question_ids", [q["question_id"] for q in questions]),
        # the rendered rows, so a batch can carry the rules block ONCE instead
        # of repeating it per event
        ("questions", questions),
        ("prompt", text), ("prompt_sha256", G._sha(text))])''')
s = s.replace('''    return collections.OrderedDict([
        ("leg", leg), ("source_id", source_id),
        ("produced_idxs", list(produced_idxs)),
        ("question_ids", [q["question_id"] for q in questions]),
        ("prompt", text), ("prompt_sha256", G._sha(text))])''',
'''    return collections.OrderedDict([
        ("leg", leg), ("source_id", source_id),
        ("produced_idxs", list(produced_idxs)),
        ("question_ids", [q["question_id"] for q in questions]),
        ("questions", questions),
        ("reference_cards", body["reference_cards"]),
        ("prompt", text), ("prompt_sha256", G._sha(text))])''')

# ONE call = one rules block + the questions of every event in the batch
s = s.replace('''def read_extras_reply(text, packet):''',
'''def batch_packet(kind, packets):
    """-> ONE call carrying several events' questions under ONE rules block.

    `pack_batches` guarantees at most one item per SOURCE EVENT in a batch, so
    the question rows never collide. The rules are rendered once: repeating
    them per event would multiply the prompt without adding a single
    instruction, and the grader would read the same rules ten times.
    """
    if kind not in ("G2", "G3"):
        raise ValueError("a batch is G2 or G3, not %r" % (kind,))
    rules = meaning_rules() if kind == "G2" else extras_rules()
    rows, cards, ids = [], [], []
    for packet in packets:
        rows.extend(packet["questions"])
        ids.extend(packet["question_ids"])
        if kind == "G3":
            cards.extend(packet["reference_cards"])
    if len(set(ids)) != len(ids):
        raise ValueError("a batch repeats a question id")
    body = collections.OrderedDict([("questions", rows)])
    if kind == "G3":
        body["reference_cards"] = cards
    text = rules + G._pretty(body) + "\\n"
    return collections.OrderedDict([
        ("kind", kind), ("question_ids", ids),
        ("legs", [p["leg"] for p in packets]),
        ("source_ids", [p["source_id"] for p in packets]),
        ("prompt", text), ("prompt_sha256", G._sha(text))])


def read_extras_reply(text, packet):''')
assert s != o and s.count("def batch_packet") == 1
io.open(p, "w", encoding="utf-8").write(s)
print("batch_packet added")
PY
# point the run module at it
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
p = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
     "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/a7_g23_run.py")
s = io.open(p, encoding="utf-8").read(); o = s
s = s.replace('''def _g2_packet_for(gold, arms, batch_id, batch):
    """ONE G2 call. A batch holds at most one item per SOURCE EVENT, so each
    entry is packed as its own event packet and the parts are concatenated by
    the packet owner - never re-rendered here."""
    parts, qids = [], []
    for key, pair in batch:
        leg, sid = key.split("|", 1)
        packet = B.meaning_packet(leg, sid, [pair], gold[sid],
                                  arms[leg][sid]["facts"])
        parts.append(packet["prompt"])
        qids.extend(q["question_id"] for q in packet["questions"])
    return {"prompt": "\\n".join(parts), "question_ids": qids}


def _g3_packet_for(gold, arms, batch_id, batch):
    parts, qids = [], []
    for key, produced_idx in batch:
        leg, sid = key.split("|", 1)
        srcs = [(gi, gold[sid][gi])
                for gi in G.accepted_positions(gold[sid])]
        packet = B.extras_packet(leg, sid, [produced_idx],
                                 arms[leg][sid]["facts"], srcs)
        parts.append(packet["prompt"])
        qids.extend(q["question_id"] for q in packet["questions"])
    return {"prompt": "\\n".join(parts), "question_ids": qids}''',
'''def _g2_packet_for(gold, arms, batch):
    """ONE G2 call: the packet owner renders the bytes, this only groups."""
    return B.batch_packet("G2", [
        B.meaning_packet(key.split("|", 1)[0], key.split("|", 1)[1], [pair],
                         gold[key.split("|", 1)[1]],
                         arms[key.split("|", 1)[0]][
                             key.split("|", 1)[1]]["facts"])
        for key, pair in batch])


def _g3_packet_for(gold, arms, batch):
    packets = []
    for key, produced_idx in batch:
        leg, sid = key.split("|", 1)
        srcs = [(gi, gold[sid][gi]) for gi in G.accepted_positions(gold[sid])]
        packets.append(B.extras_packet(leg, sid, [produced_idx],
                                       arms[leg][sid]["facts"], srcs))
    return B.batch_packet("G3", packets)''')
s = s.replace('''        "G2", g2_batches, lambda bid, b: _g2_packet_for(gold, arms, bid, b))''',
'''        "G2", g2_batches, lambda bid, b: _g2_packet_for(gold, arms, b))''')
s = s.replace('''        "G3", g3_batches, lambda bid, b: _g3_packet_for(gold, arms, bid, b))''',
'''        "G3", g3_batches, lambda bid, b: _g3_packet_for(gold, arms, b))''')
assert s != o
io.open(p, "w", encoding="utf-8").write(s)
print("run module rewired")
PY
cd "$V3" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 3000 /home/faisal/EventMarketDB/venv/bin/python3 a7_g23_run.py /tmp/a7_g23_candidate 2>&1 | tail -14