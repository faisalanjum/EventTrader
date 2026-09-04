# -*- coding: utf-8 -*-
"""REPLAY of the exact reconciliation owner (Codex SEQ 1596). NOT an owner.

Inside a private projected world it (1) records the red: the projected reconciliation_final.json
fails the historical pin, and sets it aside unaltered; (2) projects the archived instruction
1342 into the masked mailbox at the path the owner reads; (3) runs the exact, unmodified owner
with variant `final` as history ran it; (4) compares the JSON and rendered text with the pins,
derives the independent checks from the output and the archive, and exports every byte and
identity; (5) runs the two smallest negative controls (identity and COV-row boundaries).
"""
import collections, hashlib, io, json, os, re, shutil, subprocess, sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
RUN = S + "/invrev_run4"
E = S + "/bench_1306/.claude/plans/Drivers/experiments"
MAILBOX = os.path.expanduser("~/.core827-orchestrator")
HOME = os.environ["RECON_1342_HOME"]
PINS = json.load(io.open(HOME + "/pins_1596.json", encoding="utf-8"))
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
OWNER = S + "/build_reconciliation.py"                    # the owner's historical path (transcript line 30855)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


def _tsv(path, rows):
    io.open(path, "w", encoding="utf-8").write("".join("\t".join(str(c) for c in r) + "\n" for r in rows))


def place():
    shutil.copyfile(HOME + "/owner/build_reconciliation.py", OWNER)
    if sha(read(OWNER)) != PINS["owner_sha256"]:
        raise RuntimeError("the owner is not the exact bytes Codex named")
    os.makedirs(MAILBOX, exist_ok=True)
    shutil.copyfile(HOME + "/archives/archive_CODEX_1342.md", MAILBOX + "/archive_CODEX_1342.md")
    if sha(read(MAILBOX + "/archive_CODEX_1342.md")) != PINS["archive_1342_sha256"]:
        raise RuntimeError("the archived instruction is not the bytes Codex named")
    # the `proposal` variant (the COV-row negative control only) reads the archived instruction 1340
    shutil.copyfile(HOME + "/archives/archive_CODEX_1340.md", MAILBOX + "/archive_CODEX_1340.md")
    return [("archive_CODEX_1342.md", sha(read(MAILBOX + "/archive_CODEX_1342.md"))), ("archive_CODEX_1340.md (control only)", sha(read(MAILBOX + "/archive_CODEX_1340.md"))), ("build_reconciliation.py", sha(read(OWNER)))]


def red(out):
    """The projected artifact fails the historical pin; it is set aside, never overwritten."""
    p = RUN + "/reconciliation_final.json"; got = sha(read(p))
    aside = RUN + "/projected_before_replay"; os.makedirs(aside)
    for n in ("reconciliation_final.json", "reconciliation_final.txt"):
        shutil.move(RUN + "/" + n, aside + "/" + n)
    line = "RED projected reconciliation_final.json %s vs pin %s %s (set aside, unaltered)" % (got, PINS["target_json_sha256"], "FAILS" if got != PINS["target_json_sha256"] else "MEETS")
    io.open(out + "/red.txt", "w", encoding="utf-8").write(line + "\n"); print(line)
    return got != PINS["target_json_sha256"]


def run_owner(variant, log):
    p = subprocess.run([PY, "-B", OWNER, variant], capture_output=True, text=True, cwd=S,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="/home/faisal/EventMarketDB"))
    io.open(log, "w", encoding="utf-8").write("rc=%d\n--- stdout\n%s\n--- stderr\n%s" % (p.returncode, p.stdout, p.stderr))
    if p.returncode != 0:
        raise RuntimeError("owner rc=%d: %s" % (p.returncode, p.stderr.strip().splitlines()[-1:] ))
    stem = "/reconciliation_final" if variant == "final" else "/reconciliation_proposal"
    return read(RUN + stem + ".json"), read(RUN + stem + ".txt")


def archive_expectations():
    """The COV-seq-1 fields and the final census, read from the archived instruction's own text."""
    t = io.open(HOME + "/archives/archive_CODEX_1342.md", encoding="utf-8").read()
    field = lambda name: re.search(r"`%s`: `([^`]*)`" % name, t).group(1)
    tags = re.findall(r"applicable hidden tags: (.*)", t)[0]
    return {"source_id": field("source_id"), "part_ref": field("part_ref"), "raw_label_or_claim": field("raw_label_or_claim"),
            "proposed_record_kind": field("proposed_record_kind"), "proposed_hard_classes": re.findall(r"`([a-z_]+)`", tags),
            "occurrence_in_part": None, "text": t}


def checks(doc):
    exp = archive_expectations(); rows = []
    cov = [c for c in doc["coverage_selections"] if c["id"] == "COV-seq-1"]
    rows.append(("resolutions", len(doc["resolutions"]), 72)); rows.append(("changes", len(doc["changes"]), 95)); rows.append(("COV-seq-1 count", len(cov), 1))
    if cov:
        r = cov[0]["effect"]["row"]
        for k in ("source_id", "part_ref", "raw_label_or_claim", "proposed_record_kind", "proposed_hard_classes", "occurrence_in_part"):
            rows.append(("COV-seq-1 " + k, r[k], exp[k]))
        rows.append(("COV-seq-1 quote in archive", r["quote"] in exp["text"], True))
    inv = doc["proposed_inventory"]; n = sum(len(v) for v in inv.values())
    rows.append(("rows", n, 196)); rows.append(("events", len(inv), 36))
    a = doc["counts"]["after"]
    m = re.search(r"(\d+) real items, (\d+) negative controls, (\d+) lawful abstention controls", exp["text"])
    rows.append(("kind real_item", a["kinds"].get("real_item"), int(m.group(1)))); rows.append(("kind negative_control", a["kinds"].get("negative_control"), int(m.group(2)))); rows.append(("kind lawful_abstention_control", a["kinds"].get("lawful_abstention_control"), int(m.group(3))))
    m2 = re.search(r"point (\d+), losses/sign (\d+), sequential (\d+)", exp["text"])
    rows.append(("tag point_range_floor_ceiling", a["tags"]["point_range_floor_ceiling"], int(m2.group(1)))); rows.append(("tag losses_and_sign", a["tags"]["losses_and_sign"], int(m2.group(2)))); rows.append(("tag sequential_comparison", a["tags"]["sequential_comparison"], int(m2.group(3))))
    return [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in rows]


def inputs_manifest(doc):
    x = doc["inputs"]; rows = [("field", "recorded_by_owner", "world_file_sha256")]
    rows.append(("instruction seq %s" % x["instruction"]["seq"], x["instruction"]["sha256"], sha(read(MAILBOX + "/archive_CODEX_%d.md" % x["instruction"]["seq"]))))
    rows.append(("package_manifest", x["package_manifest_sha256"], sha(read(E + "/inventory_review/package.manifest.json"))))
    rows.append(("inventory", x["inventory_sha256"], sha(read(E + "/one_item_benchmark_inventory.json"))))
    rows.append(("prefix", x["prefix_sha256"], sha(read(E + "/inventory_review/prefix.md"))))
    rows.append(("pending_ledger rows %d" % x["pending_ledger"]["rows"], x["pending_ledger"]["sha256"], sha(read(RUN + "/pending_ledger.json"))))
    rows.append(("attempts.json", "", sha(read(RUN + "/attempts.json"))))
    for a in x["accepted_raws"]:
        rows.append(("raw %s attempt %s %s" % (a["source_id"], a["attempt"], a["raw_name"]), a["sha256"], sha(read(RUN + "/replies/" + a["raw_name"]))))
    for s in x["sources"]:
        rows.append(("source %s" % s["source_id"], s["input_sha256"], sha(read(E + "/inventory_review/inputs/%s.json" % s["source_id"]))))
    return rows


def dependencies():
    code = ("import sys, json, hashlib\nsys.path.insert(0, %r)\nimport raw_transport, validate_benchmark_inventory\nrows=[]\n"
            "for n, m in sorted(sys.modules.items()):\n    f = getattr(m, '__file__', None)\n    if f and f.startswith(%r): rows.append((n, f.replace(%r, ''), hashlib.sha256(open(f, 'rb').read()).hexdigest()))\nprint(json.dumps(rows))") % (E + "/harness", S, S + "/")
    p = subprocess.run([PY, "-B", "-c", code], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return json.loads(p.stdout.strip().splitlines()[-1])


def main(tag):
    out = HOME + "/out/" + tag; os.makedirs(out, exist_ok=True)
    placed = place()
    _tsv(out + "/PLACED.tsv", [("file", "sha256")] + placed)
    is_red = red(out)
    j, t = run_owner("final", out + "/owner_final.log")
    io.open(out + "/reconciliation_final.replayed.json", "wb").write(j); io.open(out + "/reconciliation_final.replayed.txt", "wb").write(t)
    doc = json.loads(j.decode("utf-8"), object_pairs_hook=collections.OrderedDict)
    jm, tm = sha(j) == PINS["target_json_sha256"], sha(t) == PINS["target_text_sha256"]
    lines = ["red: projected artifact fails the pin: %s" % is_red,
             "json got %s want %s %s" % (sha(j), PINS["target_json_sha256"], "MATCH" if jm else "DIFF"),
             "text got %s want %s %s" % (sha(t), PINS["target_text_sha256"], "MATCH" if tm else "DIFF")]
    ck = checks(doc); _tsv(out + "/CHECKS.tsv", [("check", "got", "want", "status")] + ck); lines += ["check %s: %s vs %s %s" % c for c in ck]
    im = inputs_manifest(doc); _tsv(out + "/INPUTS.tsv", im)
    first = next((r for r in im[1:] if r[1] and r[1] != r[2]), None); lines.append("first input field the owner recorded differently from the world file: %s" % (first,))
    _tsv(out + "/DEPENDENCIES.tsv", [("module", "path", "sha256")] + [tuple(r) for r in dependencies()])
    # NEGATIVE CONTROLS, the two smallest: the identity boundary and the COV-row boundary
    ap = MAILBOX + "/archive_CODEX_1342.md"; orig = read(ap); io.open(ap, "wb").write(orig + b"\n")
    try:
        j2, t2 = run_owner("final", out + "/control_identity.log")
    finally:
        io.open(ap, "wb").write(orig)
    lines.append("control identity (archive +1 byte): json %s %s the lawful json, text %s %s the lawful text" % (sha(j2)[:16], "differs from" if j2 != j else "EQUALS", sha(t2)[:16], "equals" if t2 == t else "differs from"))
    j3, t3 = run_owner("proposal", out + "/control_cov.log"); d3 = json.loads(j3.decode("utf-8"))
    lines.append("control COV-row (variant proposal): COV-seq-1 count %d, rows %d, json %s %s the lawful json" % (sum(1 for c in d3["coverage_selections"] if c["id"] == "COV-seq-1"), sum(len(v) for v in d3["proposed_inventory"].values()), sha(j3)[:16], "differs from" if j3 != j else "EQUALS"))
    # the lawful artifact is rebuilt last so the world ends in the lawful state
    j4, t4 = run_owner("final", out + "/owner_final_again.log"); lines.append("lawful rebuild equals first: json %s text %s" % (j4 == j, t4 == t))
    lines.append("RESULT " + ("MATCH" if jm and tm else "DIFF"))
    io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n"); print("\n".join(lines))
    return 0 if (jm and tm) else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
