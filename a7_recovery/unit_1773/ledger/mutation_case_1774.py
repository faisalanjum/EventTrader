# -*- coding: utf-8 -*-
"""ONE mutation case, at the run's OWN logical identity (Codex SEQ 1774 item 1).

The driver binds a private copy of the completed run at the SAME logical path,
so the copy is a lawful run rather than one that refuses merely for its path -
that is the flaw in the retained mutation tests. Each case therefore proves the
CONTROL first, then mutates exactly one thing, then requires the intended
owner's refusal, matched on what the refusal SAYS.

usage (inside the boundary): mutation_case_1774.py <case>
"""
import hashlib, io, json, os, shutil, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
RUN = S + "/a6_a5run_1515"
FOREIGN = "/tmp/a6_prepared_run"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

ACCEPTED = "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d"
RECEIPT = "c43457c99231edb36f3d479848f1ea9ac63fcc84d095755c5a1b8d7a2109b8c4"
FINAL = "04b53cddf63528933cd99afe1b215061d2a07d8f4bc2fb0738014dd50aa30880"
CANDIDATE = "2be60129ee18c99996b31079b155d3f4558bec4141e1d3574cdb8b3129c7746a"
PROMPTS = "02e9d2259d0cc2567dad56786d6457893629c16eb62128c88872288f76e00122"

import a7_prepared_run as PR                                     # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import raw_transport as RT                                       # noqa: E402


def control():
    """The positive control: without it no refusal below means anything."""
    ident = PR.current(RUN, ACCEPTED)
    assert ident["receipt_sha256"] == RECEIPT, ident["receipt_sha256"]
    assert ident["finalizations"]["primary"] == FINAL
    assert ident["a6_freeze_sha256"] == ACCEPTED
    assert ident["scheduled_calls"] == 392
    assert ident["executed"]["run_files"] == 861
    return ident


def refuses(*needles, **kw):
    want = kw.get("expect", ACCEPTED)
    try:
        PR.current(RUN, want)
    except ValueError as exc:
        said = str(exc).lower()
        assert any(n in said for n in needles), "refused, but for: %s" % said
        return said
    raise AssertionError("NO REFUSAL: the mutation went undetected")


def jload(p):
    return json.load(io.open(p, encoding="utf-8"))


def build(out):
    ident = PR.current(RUN, ACCEPTED)
    path, problems = G.write(out, ident)
    assert not problems, problems[:2]
    return path, jload(path)


def case_control():
    control()
    return "the unmutated private copy carries the accepted identity"


def case_missing_receipt():
    control()
    os.unlink(os.path.join(RUN, "receipt.json"))
    return refuses("no receipt", "not a prepared run")


def case_foreign_receipt():
    control()
    assert os.path.isfile(os.path.join(FOREIGN, "receipt.json")), "no other run bound"
    shutil.copyfile(os.path.join(FOREIGN, "receipt.json"),
                    os.path.join(RUN, "receipt.json"))
    return refuses("receipt", "run_id", "does not hold")


def case_changed_receipt():
    control()
    p = os.path.join(RUN, "receipt.json")
    rec = jload(p); rec["injected_field"] = 1
    io.open(p, "wb").write(RT.receipt_bytes(rec))
    return refuses("receipt", "does not hold")


def case_changed_finalization():
    control()
    p = os.path.join(RUN, "finalization.json")
    fin = jload(p)
    fin["ledger"] = dict(fin["ledger"],
                         primary_valid=fin["ledger"]["primary_valid"] + 1)
    io.open(p, "w", encoding="utf-8").write(json.dumps(fin, indent=1))
    return refuses("finalization", "does not hold")


def case_changed_raw():
    control()
    raw = os.path.join(RUN, "raw")
    with io.open(os.path.join(raw, sorted(os.listdir(raw))[0]), "ab") as fh:
        fh.write(b" ")
    return refuses("raw", "finalization", "freeze", "does not hold")


def case_missing_finalization():
    control()
    os.unlink(os.path.join(RUN, "finalization.json"))
    return refuses("finalization", "holds", "no finalization")


def case_wrong_freeze():
    control()
    return refuses("freezes to", expect="0" * 64)


def case_wrong_era():
    ident = control()
    p = os.path.join(RUN, "plan", PR.A5_MANIFEST)
    man = jload(p)
    man["contract_suffix"] = ident["contract_suffix"] + ".other"
    io.open(p, "w", encoding="utf-8").write(json.dumps(man, indent=1))
    return refuses("era", "freeze", "does not hold", "manifest")


def case_candidate_control():
    path, doc = build("/tmp/a7_mut_out")
    got = hashlib.sha256(io.open(path, "rb").read()).hexdigest()
    assert got == CANDIDATE, got
    assert G.prompt_tree_sha("/tmp/a7_mut_out", doc) == PROMPTS
    assert doc["launchers"]["count"] == 206 and doc["batching"]["batches"] == 103
    assert doc["questions"] == 444
    return "candidate %s, prompt tree %s, 206/103/444" % (got[:16], PROMPTS[:16])


def case_changed_prompt():
    out = "/tmp/a7_mut_out"
    path, doc = build(out)
    before = G.prompt_tree_sha(out, doc)
    assert before == PROMPTS
    with io.open(os.path.join(out, doc["batch_rows"][0]["prompt_path"]), "ab") as fh:
        fh.write(b" ")
    after = G.prompt_tree_sha(out, doc)
    assert after != before, "a changed prompt byte did NOT change the tree"
    return "prompt tree moved %s -> %s" % (before[:16], after[:16])


def case_changed_question():
    path, doc = build("/tmp/a7_mut_out")
    before = hashlib.sha256(io.open(path, "rb").read()).hexdigest()
    doc["question_bindings"][0] = dict(doc["question_bindings"][0],
                                       question_id="not-a-real-question")
    after = hashlib.sha256((G._pretty(doc) + "\n").encode("utf-8")).hexdigest()
    assert after != before and after != CANDIDATE
    return "candidate moved %s -> %s" % (before[:16], after[:16])


def case_short_population():
    path, doc = build("/tmp/a7_mut_out")
    assert len(doc["batch_rows"]) == 103
    doc["batch_rows"] = doc["batch_rows"][:-1]
    after = hashlib.sha256((G._pretty(doc) + "\n").encode("utf-8")).hexdigest()
    assert after != CANDIDATE
    return "102 of 103 batches no longer the accepted candidate (%s)" % after[:16]


CASES = {n[5:]: f for n, f in sorted(globals().items()) if n.startswith("case_")}

if __name__ == "__main__":
    name = sys.argv[1]
    print("CASE %s" % name)
    print("RESULT %s" % CASES[name]())
    print("OK")
