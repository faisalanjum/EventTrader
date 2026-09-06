# -*- coding: utf-8 -*-
"""Reproduce the existing G1 candidate through the REAL A7 caller.

Codex SEQ 1773 item 3. The proof starts at the existing PR.current over the
reconstructed completed run at its accepted freeze - no historical-era test
fixture - and then uses G1's own write/freeze path. Two successful builds at
the same identity, into two fresh A7-only directories, so determinism is shown
by two SUCCESSES and never by two equal failures.

Every target below is an END assertion. Nothing here is fitted to one.
"""
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
RUN = S + "/a6_a5run_1515"
OUT = "/tmp/a7_logs_1773"
A, B = "/tmp/a7_candidate_a_1773", "/tmp/a7_candidate_b_1773"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

WANT_CANDIDATE = "2be60129ee18c99996b31079b155d3f4558bec4141e1d3574cdb8b3129c7746a"
WANT_PROMPTS = "02e9d2259d0cc2567dad56786d6457893629c16eb62128c88872288f76e00122"
ACCEPTED_FREEZE = "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d"
CHECKS = []


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok, got, want))
    print("  %-5s %-24s %s" % ("ok" if ok else "BAD", name, got))
    return ok


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def build(out_dir, G, ident):
    path, problems = G.write(out_dir, ident)
    if problems:
        raise SystemExit("the candidate refuses: %s" % problems[:3])
    return path


def main():
    import a7_prepared_run as PR
    import a7_g1_build as G

    # the era gate, over the real completed run at its accepted freeze
    ident = PR.current(RUN, ACCEPTED_FREEZE)
    print("identity: era %s, %d scheduled, freeze %s"
          % (ident["contract_suffix"], ident["scheduled_calls"],
             ident["a6_freeze_sha256"][:16]))

    pa = build(A, G, ident)
    pb = build(B, G, ident)
    check("candidate_A", fsha(pa), WANT_CANDIDATE)
    check("candidate_B", fsha(pb), WANT_CANDIDATE)

    doc = json.load(io.open(pa, encoding="utf-8"))
    # the prompt tree is digested by the owner's own helper over the written
    # prompt files, exactly as the root records it
    check("prompt_tree", G.prompt_tree_sha(A, doc), WANT_PROMPTS)
    check("lanes", doc["launchers"]["count"], 206)
    check("batches", doc["batching"]["batches"], 103)
    check("batch_rows", len(doc["batch_rows"]), 103)
    check("questions", doc["questions"], 444)
    check("question_bindings", len(doc["question_bindings"]), 444)
    check("prompt_pins", len({r["prompt_sha256"] for r in doc["batch_rows"]}), 103)
    check("grader_owner", doc["launchers"]["owner_sha256"],
          "806a7560002a14ed5f3a4c79a78d85be0fac8abf773f8fdf9457c3d902e8abd6")
    pdir = os.path.join(A, G.PROMPT_DIRNAME)
    check("prompt_files", len([n for n in os.listdir(pdir)
                               if n.endswith(".prompt.txt")]), 103)
    # the two builds are identical file for file, not merely equal at the root
    names = sorted(os.listdir(pdir))
    same = all(fsha(os.path.join(A, G.PROMPT_DIRNAME, n))
               == fsha(os.path.join(B, G.PROMPT_DIRNAME, n)) for n in names)
    check("both_builds_identical", same, True)

    os.makedirs(OUT, exist_ok=True)
    io.open(OUT + "/CANDIDATE_CHECKS.tsv", "w", encoding="utf-8").write(
        "".join("%s\t%s\t%s\t%s\n" % (n, "ok" if k else "BAD", g, w)
                for n, k, g, w in CHECKS))
    bad = [n for n, k, _g, _w in CHECKS if not k]
    print("\n%d checks, %d bad %s" % (len(CHECKS), len(bad), bad or ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
