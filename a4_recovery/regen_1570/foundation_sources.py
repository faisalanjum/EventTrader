"""The exact callable closure of the A4 foundation and where each byte stands in history
(Codex SEQ 1579 items 2-4, corrected by SEQ 1581). One table, inputs/FOUNDATION_PROJECTION.tsv:

    phase  historical_path  candidate_path  bytes  sha256

`copy` assembles the candidate under foundation/ from the enumerated sources only: the committed A3
package rows (its own PROJECTION.tsv: bench inputs, the A3 run, the A3 official states and records),
the A3 bench's repo `driver` package, skills scripts, law files and harness directory (minus the two
files history held differently), the pinned overlays the A3 bench does not carry (hard-review owner
from file-history; correction owner, final owner and key_lint from stage-1), the historical
build_launch_manifest.py and phase-1 key owner and the three exact scratch tools preserved under
regen_1566 (each pin-checked at copy), the corrected key owner (file-history), the five package
texts, the two preliminary derived files (hash comparison only, never projected), the frozen
official corpus at the official state and record paths, and every saved state's launcher script at
its historical scriptPath (bytes = the state's own embedded script; the runtime writes it there when the
owner arms that call, so the run directories start empty).

Two pairs of rows share one historical path on purpose: the key owner's `epoch1` (13d00b1f, projected
before the run) and `epoch2` (a289601b, what the path holds after the phase-1 anchors are met), and the
inventory's `inventory1` (the 168-proposal b137e87e the review-package build sees) and `inventory2`
(the final 57a1cdd0 restored before phase 1). The review package itself (39 files) is never projected:
the real owner writes it. The two archives the owner quotes are projected into the masked mailbox. `verify` re-hashes every candidate byte and requires every owner pin.

    foundation_sources.py copy        assemble the candidate and write the table
    foundation_sources.py verify      re-check every candidate byte and pin
    foundation_sources.py project [table]              namespace only: rows to historical paths
    foundation_sources.py verify-view [--after-run]     namespace only: the projected view holds
"""
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(R, "inputs", "FOUNDATION_PROJECTION.tsv")
PINS = os.path.join(R, "inputs", "FOUNDATION_PINS.tsv")
CENSUS = os.path.join(R, "inputs", "A4_OFFICIAL_RESULTS.tsv")
CORPUS = os.path.join(R, "inputs", "a4_official")
A3 = "/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541"
FH = os.path.expanduser("~/.claude/file-history/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
STAGE1 = "/home/faisal/.core827_backups/recovery_1531/regen_1539/builds/stage1/tree/.claude/plans/Drivers/experiments/harness_g1v3"
R66 = "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1566/evidence"
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
BENCH = S + "/bench_1306"
X = BENCH + "/.claude/plans/Drivers/experiments"
HARNESS = X + "/harness"
SESS = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
BENCH_DIRS = ("driver", ".claude/skills/earnings-orchestrator/scripts", ".claude/plans/Drivers/FinalDesign",
              ".claude/plans/Drivers/experiments/harness")
HELD_DIFFERENTLY = ("build_launch_manifest.py", "build_kfields_key.py")   # history's bytes come from the rows below
OVERLAYS = (("build_kfields_hard_review.py", FH + "/dffa453cc8971216@v2"),
            ("build_kfields_hr_correction.py", STAGE1 + "/build_kfields_hr_correction.py"),
            ("build_kfields_final.py", STAGE1 + "/build_kfields_final.py"),
            ("key_lint.py", STAGE1 + "/key_lint.py"),
            ("build_launch_manifest.py", R66 + "/derived/harness/build_launch_manifest.py"))
EPOCHS = (("epoch1", "phase1", R66 + "/a4/build_kfields_key.13d00b1f.py"),
          ("epoch2", "post", FH + "/bf2596971ecbb1dd@v3"))
TOOLS = (("a3_reaudit.py", S + "/a4/a3_reaudit.py"), ("a4_regrade.py", S + "/a4_regrade.py"), ("a4_conflicts.py", S + "/a4_conflicts.py"))
TEXTS = ("owner_rulings_1383.txt", "decision_rules_1387.txt", "v4_findings_1390.txt", "v5_findings_1394.txt", "v6_findings_1396.txt")
DERIVED = ("regrade_1370.json", "conflicts_1370.json")
EVIDENCE_RELS = ("a3_serial_dir.txt", "invrev_run4/", "lock/candidate/")   # K reads these at the scratch root too
RUN1 = X + "/runs/kf-a4-phase1-196-20260821T163310Z"
INVENTORY = X + "/one_item_benchmark_inventory.json"
B137 = ("/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541/builds/b137/out/one_item_benchmark_inventory.json",
        "/home/faisal/.core827_backups/recovery_1531/regen_1541/builds/b137/out/one_item_benchmark_inventory.json")
TRANSCRIPT = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
FREEZE_RECORD = 29153                                   # the run that froze the review package (its RE-FROZEN receipt)
MAILBOX = os.path.expanduser("~/.core827-orchestrator")
ARCHIVES = ("archive_CODEX_1330.md", "archive_CODEX_1333.md")
REVIEW_OUT = X + "/inventory_review/"                    # rebuilt by the real owner; never projected


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _read(p):
    return io.open(p, "rb").read()


def pins(scope):
    out = {}
    for l in io.open(PINS, encoding="utf-8").read().split("\n")[1:]:
        if l.strip():
            sc, name, sha = l.split("\t")
            if sc == scope:
                out[name] = sha
    return out


def census():
    rows = []
    for l in io.open(CENSUS, encoding="utf-8").read().split("\n")[1:]:
        if l.strip():
            rows.append(l.split("\t"))
    return rows


def _refuse(msg):
    raise SystemExit("REFUSED: " + msg)


def _pair(a, b):
    """The two epoch pairs that lawfully share one historical path."""
    return {a, b} in ({"epoch1", "epoch2"}, {"inventory1", "inventory2"})


def _put(src_bytes, rel):
    dst = os.path.join(R, rel)
    if os.path.exists(dst):
        if _read(dst) != src_bytes:
            _refuse("%s exists with different bytes" % rel)
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    io.open(dst, "wb").write(src_bytes)


def enumerate_rows():
    """-> [(phase, historical, candidate_rel, source_path or None, expected sha or None)] before copying."""
    rows, owner_pins = [], pins("owner")
    for l in io.open(os.path.join(A3, "evidence", "PROJECTION.tsv"), encoding="utf-8").read().split("\n")[1:]:
        if not l.strip():
            continue
        ph, hist, rel, _b, sha = l.split("\t")
        if hist.startswith(REVIEW_OUT):
            continue                                  # the inventory-history stage rebuilds all 39
        if hist == INVENTORY:
            rows.append(("inventory2", hist, "foundation/a3/" + rel, os.path.join(A3, rel), pins("inventory")["final"]))
            continue
        rows.append(("a3-" + ph, hist, "foundation/a3/" + rel, os.path.join(A3, rel), sha))
        for ev in EVIDENCE_RELS:
            if hist.startswith(X + "/" + ev):
                rows.append(("evidence", S + "/" + hist[len(X) + 1:], "foundation/a3/" + rel, os.path.join(A3, rel), sha))
    for d in BENCH_DIRS:
        base = os.path.join(A3, "bench", d)
        for dp, _dirs, files in os.walk(base):
            for f in sorted(files):
                if dp == base and d.endswith("/harness") and f in HELD_DIFFERENTLY:
                    continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, os.path.join(A3, "bench"))
                rows.append(("bench", BENCH + "/" + rel, "foundation/bench/" + rel, p, owner_pins.get(f) if dp == base and d.endswith("/harness") else None))
    for name, src in OVERLAYS:
        rows.append(("owner", HARNESS + "/" + name, "foundation/bench/.claude/plans/Drivers/experiments/harness/" + name, src, owner_pins[name]))
    for ph, epoch, src in EPOCHS:
        sha = pins("epoch")[epoch]
        rows.append((ph, HARNESS + "/build_kfields_key.py", "foundation/owners/build_kfields_key.%s.py" % sha[:8], src, sha))
    for name, hist in TOOLS:
        rows.append(("tool", hist, "foundation/tools/" + name, R66 + "/a4/" + name, pins("tool")[name]))
    hist_sha = pins("inventory")["history"]
    rows.append(("inventory1", INVENTORY, "foundation/inventory/one_item_benchmark_inventory.%s.json" % hist_sha[:8], B137[0], hist_sha))
    for name in ARCHIVES:
        rows.append(("archive", os.path.join(MAILBOX, name), "foundation/archives/" + name, os.path.join(MAILBOX, name), pins("archive")[name]))
    for name in TEXTS:
        rows.append(("text", HARNESS + "/" + name, "foundation/bench/.claude/plans/Drivers/experiments/harness/" + name, os.path.join(R, "experiments", "harness_g1v3", name), None))
    for name in DERIVED:
        rows.append(("derived", RUN1 + "/" + name, "foundation/a4_derived/" + name, R66 + "/a4_phase1_run/" + name, pins("derived")[name]))
    for phase, attempt, label, wf, ssha, asha, jsha, scsha, spath in census():
        d = os.path.join(CORPUS, wf)
        agent = [f for f in os.listdir(d) if f.startswith("agent-")]
        if len(agent) != 1:
            _refuse("%s: %d agent transcripts in the corpus" % (wf, len(agent)))
        rows.append(("state", SESS + "/workflows/" + wf + ".json", "inputs/a4_official/%s/%s.json" % (wf, wf), None, ssha))
        rows.append(("record", SESS + "/subagents/workflows/%s/%s" % (wf, agent[0]), "inputs/a4_official/%s/%s" % (wf, agent[0]), None, asha))
        rows.append(("record", SESS + "/subagents/workflows/%s/journal.jsonl" % wf, "inputs/a4_official/%s/journal.jsonl" % wf, None, jsha))
        rows.append(("script", spath, "state:" + wf, None, scsha))
    return rows


def _freeze_receipt():
    """{name: sha256} from the RE-FROZEN receipt the review-package freeze printed (record 29153)."""
    with io.open(TRANSCRIPT, "rb") as fh:
        for n, raw in enumerate(fh, 1):
            if n == FREEZE_RECORD:
                rec = json.loads(raw)
                break
        else:
            _refuse("transcript record %d is absent" % FREEZE_RECORD)
    text = ""
    for c in (rec.get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_result":
            x = c.get("content")
            text = x if isinstance(x, str) else "".join(p.get("text", "") for p in x if isinstance(p, dict))
    out = {}
    for line in text.split("=== RE-FROZEN ===", 1)[-1].split("\n"):
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            out[os.path.basename(parts[1])] = parts[0]
    return out


def candidate_bytes(rel, root=R):
    """The bytes a table row stands for: a candidate file, or a state's embedded script."""
    if rel.startswith("state:"):
        wf = rel[6:]
        d = json.loads(_read(os.path.join(root, "inputs", "a4_official", wf, wf + ".json")).decode("utf-8"))
        return d["script"].encode("utf-8")
    return _read(os.path.join(root, rel))


def copy():
    rows, out, seen = enumerate_rows(), [], {}
    for ph, hist, rel, src, want in rows:
        if hist in seen and not _pair(ph, seen[hist]):
            _refuse("historical path %s claimed twice (%s, %s)" % (hist, seen[hist], ph))
        seen[hist] = ph
        if src is not None:
            if not os.path.isfile(src) or os.path.islink(src):
                _refuse("source missing or not a regular file: %s" % src)
            b = _read(src)
            if want is not None and _sha(b) != want:
                _refuse("%s is %s, not the pinned %s" % (src, _sha(b)[:16], want[:16]))
            if ph == "inventory1":
                if any(not os.path.isfile(p) or _read(p) != b for p in B137):
                    _refuse("the preserved b137 inventory copies are not identical")
                if _sha(b) not in _freeze_receipt().get("one_item_benchmark_inventory.json", ""):
                    _refuse("the b137 inventory is not the one transcript record %d froze" % FREEZE_RECORD)
            _put(b, rel)
        b = candidate_bytes(rel)
        if want is not None and _sha(b) != want:
            _refuse("%s is %s, not the pinned %s" % (rel, _sha(b)[:16], want[:16]))
        out.append((ph, hist, rel, len(b), _sha(b)))
    os.makedirs(os.path.dirname(TABLE), exist_ok=True)
    with io.open(TABLE, "w", encoding="utf-8") as fh:
        fh.write("phase\thistorical_path\tcandidate_path\tbytes\tsha256\n")
        for r in sorted(out, key=lambda r: (r[1], r[0])):
            fh.write("%s\t%s\t%s\t%d\t%s\n" % r)
    print("foundation sources: %d rows written" % len(out))
    return verify()


def load(table=TABLE):
    out = []
    for l in io.open(table, encoding="utf-8").read().split("\n")[1:]:
        if l.strip():
            ph, hist, rel, b, sha = l.split("\t")
            out.append((ph, hist, rel, int(b), sha))
    return out


def problems(table=TABLE, root=R):
    """Every candidate byte against the table, every owner pin at the harness path, no repeated
    historical path but the epoch pair, the phase-1 owner and tools pinned."""
    bad = []
    if not os.path.isfile(table):
        return ["projection table missing"]
    rows = load(table)
    seen, at_path = {}, {}
    for ph, hist, rel, size, sha in rows:
        if hist in seen and not _pair(ph, seen[hist]):
            bad.append("duplicate historical path %s" % hist)
        seen[hist] = ph
        try:
            b = candidate_bytes(rel, root)
        except Exception as exc:                      # noqa: BLE001 - by design
            bad.append("%s: cannot read the candidate bytes (%s)" % (rel, type(exc).__name__))
            continue
        if len(b) != size or _sha(b) != sha:
            bad.append("%s: candidate bytes %d/%s differ from the table %s/%s" % (rel, len(b), _sha(b)[:16], size, sha[:16]))
        if hist.startswith(HARNESS + "/") and "/" not in hist[len(HARNESS) + 1:]:
            at_path.setdefault(os.path.basename(hist), {})[ph] = _sha(b)
    for name, want in pins("owner").items():
        got = at_path.get(name, {})
        have = got.get("epoch2") if name == "build_kfields_key.py" else (list(got.values()) or [None])[0]
        if have != want:
            bad.append("owner %s is %s at the harness path, not the pinned %s" % (name, (have or "absent")[:16], want[:16]))
    for epoch, want in pins("epoch").items():
        ph = "epoch1" if epoch == "phase1" else "epoch2"
        if at_path.get("build_kfields_key.py", {}).get(ph) != want:
            bad.append("key owner epoch %s is not the pinned %s" % (epoch, want[:16]))
    tool_rows = {os.path.basename(h): s for ph, h, r, b, s in rows if ph == "tool"}
    for name, want in pins("tool").items():
        if tool_rows.get(name) != want:
            bad.append("tool %s is %s, not the pinned %s" % (name, (tool_rows.get(name) or "absent")[:16], want[:16]))
    for name, want in pins("derived").items():
        p = os.path.join(root, "foundation", "a4_derived", name)
        if not os.path.isfile(p) or _sha(_read(p)) != want:
            bad.append("derived %s is not the pinned %s" % (name, want[:16]))
    by_phase = {}
    for ph, hist, rel, size, sha in rows:
        by_phase.setdefault(ph, {})[os.path.basename(hist)] = sha
    for epoch, ph in (("history", "inventory1"), ("final", "inventory2")):
        if by_phase.get(ph, {}).get(os.path.basename(INVENTORY)) != pins("inventory")[epoch]:
            bad.append("inventory epoch %s is not the pinned %s" % (epoch, pins("inventory")[epoch][:16]))
    for name, want in pins("archive").items():
        if by_phase.get("archive", {}).get(name) != want:
            bad.append("archive %s is not the pinned %s" % (name, want[:16]))
    if any(hist.startswith(REVIEW_OUT) for _ph, hist, _r, _b, _s in rows):
        bad.append("a review-package output is projected; the owner must write all of them")
    return bad


def verify():
    bad = problems()
    for b in bad[:20]:
        print("PROBLEM " + b)
    print("foundation sources: %s" % ("every candidate byte holds (%d rows)" % len(load()) if not bad else "REFUSED (%d problems)" % len(bad)))
    return 1 if bad else 0


def project(table=TABLE):
    """Inside the namespace: every projectable row copied to its historical path."""
    if not os.path.ismount("/tmp"):
        _refuse("project may only run inside the private namespace (no private /tmp)")
    n = 0
    for ph, hist, rel, size, sha in load(table):
        if ph in ("derived", "epoch2", "inventory2", "script"):
            continue                                  # written by the runtime where history armed them
        b = candidate_bytes(rel)
        if len(b) != size or _sha(b) != sha:
            _refuse("%s drifted before projection" % rel)
        os.makedirs(os.path.dirname(hist), exist_ok=True)
        if os.path.exists(hist):
            if _read(hist) != b:
                _refuse("%s already holds different bytes" % hist)
        else:
            io.open(hist, "wb").write(b)
        n += 1
    print("projected %d files at their historical paths" % n)
    return 0


def verify_view(after_run=False, table=TABLE):
    """Inside the namespace: every projected row holds at its historical path; after the run the
    key owner path holds epoch 2 and the two derived files stand freshly in the phase-1 run."""
    bad = []
    late = ("derived", "epoch2", "inventory2", "script")  # written by the runtime, held after the run
    early = ("epoch1", "inventory1")                     # projected before the run, replaced by the runtime
    for ph, hist, rel, size, sha in load(table):
        if (ph in late and not after_run) or (ph in early and after_run):
            continue
        if ph == "script" and not os.path.isdir(hist.split("/runs/", 1)[0] + "/runs/" + hist.split("/runs/", 1)[1].split("/", 1)[0]):
            continue                                  # a launcher exists only once its run was armed
        if not os.path.isfile(hist) or os.path.islink(hist):
            bad.append("missing projected file %s" % hist)
        elif os.path.getsize(hist) != size or _sha(_read(hist)) != sha:
            bad.append("projected bytes changed: %s" % hist)
    for b in bad[:20]:
        print("PROBLEM " + b)
    print("projection view (%s): %s" % ("after the run" if after_run else "before the run", "every row holds" if not bad else "REFUSED (%d problems)" % len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["copy"]:
        sys.exit(copy())
    if cmd == ["verify"]:
        sys.exit(verify())
    if cmd == ["project"]:
        sys.exit(project(sys.argv[2] if len(sys.argv) > 2 else TABLE))
    if cmd == ["verify-view"]:
        sys.exit(verify_view("--after-run" in sys.argv, next((a for a in sys.argv[2:] if not a.startswith("--")), TABLE)))
    sys.exit("usage: foundation_sources.py copy|verify|project [table]|verify-view [table] [--after-run]")
