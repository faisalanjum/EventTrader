"""The A4 foundation runtime: the exact historical lifecycle replayed from the frozen census through
the real owner APIs inside the projected historical tree (Codex SEQ 1579, corrected by SEQ 1581).

Stages, each in its own interpreter and chosen from the state of the projected tree, never by the
caller: `inventory` (the real review-package owner rebuilds its 39 files over the 168-proposal
inventory, held to the freeze receipt, then the final inventory is restored); `phase1` under key-owner epoch 13d00b1f (the A3 baseline by the exact re-audit script, the
phase-1 package, prepare, 196 records, finalize, the owner-derived retries, finalize); `bridge` (the
one lawful swap to epoch a289601b, then the exact regrade and conflict builders); `hardreview`
(package, prepare, 70 records, finalize, the owner-derived retries, finalize); `correction`
(package, prepare, 4 records, finalize); `final` (the seven-file package). Every saved state is
selected by the census join (run root, attempt, label) in the owner's returned order; before each
record_state the owner-rendered launcher, the state's embedded script and the projected file bytes
must be identical. Every anchor is checked where it is produced; the first mismatch refuses and
reports. A model is never called.

    foundation.py step                run the one stage the projected tree calls for
    foundation.py run <out_root>      run every remaining stage, then export the output tree
    foundation.py red-probe           the RED probes against the preliminary view
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)
import foundation_sources as FS  # noqa: E402

S, BENCH, X, HARNESS, SESS = FS.S, FS.BENCH, FS.X, FS.HARNESS, FS.SESS
PY = sys.executable
MARKER = S + "/.foundation_projection"
BASELINE = S + "/a4/a3_baseline.json"
POINTER = S + "/a4_dir.txt"
LOG = S + "/a4_foundation"
PKG1 = X + "/kfields_key_a4/phase1"
HRPKG = X + "/kfields_hard_review"
FIXD = X + "/kfields_hr_correction"
PKGF = X + "/kfields_final"
#: the two key-owner epochs and the two inventory epochs: the stage decides, the caller never does
EPOCH_OF = {"phase1": "phase1", "bridge": "post", "hardreview": "post", "correction": "post", "final": "post"}
INVENTORY_OF = {"inventory": "history"}              # every later stage needs the restored final inventory
INVENTORY = FS.INVENTORY
REVIEW = X + "/inventory_review"
PACKAGE_FILES = {"hard-review_package": {"hard_review.manifest.json": "hard_review.manifest.json", "item prefix": "prompt_prefix_item.txt", "group prefix": "prompt_prefix_group.txt"},
                 "correction_package": {"manifest": "correction.manifest.json", "prefix": "prompt_prefix_group.txt"}}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha(io.open(p, "rb").read()) if os.path.isfile(p) else None


def refuse(msg):
    print("REFUSED: " + msg)
    raise SystemExit(2)


def run_root(kind):
    roots = [sc for sc in {r[0] for r in _pin_rows()} if sc.startswith("kf-a4-" + kind + "-")]
    if len(roots) != 1:
        refuse("the pins name %d run roots for %s" % (len(roots), kind))
    return roots[0]


def _pin_rows():
    return [l.split("\t") for l in io.open(FS.PINS, encoding="utf-8").read().split("\n")[1:] if l.strip()]


def pin(scope, name):
    v = FS.pins(scope).get(name)
    if v is None:
        refuse("no pin for %s / %s" % (scope, name))
    return v


def anchor(scope, name, path):
    """Record one anchor; refuse at the first mismatch."""
    got = sha_file(path)
    want = pin(scope, name)
    os.makedirs(LOG, exist_ok=True)
    io.open(os.path.join(LOG, "ANCHORS.tsv"), "a", encoding="utf-8").write("%s\t%s\t%s\t%s\t%s\n" % (scope, name, want, got, "ok" if got == want else "MISMATCH"))
    if got != want:
        refuse("anchor %s / %s: %s is %s, not the pinned %s" % (scope, name, path, (got or "absent")[:16], want[:16]))
    print("  anchor ok  %-36s %-28s %s" % (scope[:36], name, want[:16]))


def inside_projection():
    return os.path.isfile(MARKER) and os.path.isfile(HARNESS + "/build_kfields_key.py") and os.path.ismount("/tmp")


def harness_epoch(harness=HARNESS):
    got = sha_file(os.path.join(harness, "build_kfields_key.py"))
    for epoch, want in FS.pins("epoch").items():
        if got == want:
            return epoch
    return None


def epoch_problems(stage, harness=HARNESS):
    want = EPOCH_OF.get(stage)
    got = harness_epoch(harness)
    if want is None:
        return ["unknown stage %r" % stage]
    if got != want:
        return ["stage %s needs key-owner epoch %s at %s, found %s" % (stage, want, harness, got or "no pinned epoch")]
    return []


def inventory_epoch(path=INVENTORY):
    got = sha_file(path)
    for epoch, want in FS.pins("inventory").items():
        if got == want:
            return epoch
    return None


def inventory_problems(stage, path=INVENTORY):
    want = INVENTORY_OF.get(stage, "final")
    got = inventory_epoch(path)
    if got != want:
        return ["stage %s needs the %s inventory at %s, found %s" % (stage, want, path, got or "no pinned inventory")]
    return []


def restore_final_inventory():
    """The one lawful inventory swap: the history bytes at the path, replaced by the final inventory."""
    if inventory_epoch() != "history":
        refuse("the final inventory may only replace the history inventory at %s" % INVENTORY)
    rel = [r[2] for r in FS.load() if r[0] == "inventory2"]
    if len(rel) != 1:
        refuse("the projection names %d final inventories" % len(rel))
    b = FS.candidate_bytes(rel[0])
    if sha(b) != pin("inventory", "final"):
        refuse("the candidate final inventory is not the pinned bytes")
    io.open(INVENTORY, "wb").write(b)


def git_identity_problems(repo=BENCH):
    """The owner's base_tree() must derive the frozen commit's tree from a read-only object store."""
    r = subprocess.run(["git", "-C", repo, "rev-parse", pin("git", "base_commit") + "^{tree}"], capture_output=True, text=True)
    got = r.stdout.strip() if r.returncode == 0 else ""
    if got != pin("git", "base_tree"):
        return ["git identity at %s: base tree %s, not the pinned %s" % (repo, got or "underivable", pin("git", "base_tree")[:16])]
    return []


def invrev_problems(pkg_dir):
    """The freshly built review package against the freeze-record anchors and its own manifest."""
    bad = []
    for name in ("prefix.md", "package.manifest.json", "final_sign_input.template.json"):
        got, want = sha_file(os.path.join(pkg_dir, name)), pin("invrev", name)
        if got != want:
            bad.append("review package %s is %s, not the pinned %s" % (name, (got or "absent")[:16], want[:16]))
    mp = os.path.join(pkg_dir, "package.manifest.json")
    if not os.path.isfile(mp):
        return bad
    m = json.loads(io.open(mp, "rb").read().decode("utf-8"))
    events = m.get("events") or []
    if len(events) != int(pin("invrev", "events")):
        bad.append("%d events, not the pinned %s" % (len(events), pin("invrev", "events")))
    if str((m.get("inventory") or {}).get("proposals")) != pin("invrev", "proposals"):
        bad.append("%s proposals shipped, not the pinned %s" % ((m.get("inventory") or {}).get("proposals"), pin("invrev", "proposals")))
    joined, n = hashlib.sha256(), 0
    for e in events:
        p = os.path.join(pkg_dir, "inputs", e["source_id"] + ".json")
        if not os.path.isfile(p):
            bad.append("generated input %s is missing" % e["source_id"])
            continue
        b = io.open(p, "rb").read()
        joined.update(b)
        n += 1
        if sha(b) != e.get("input_sha256_shipped"):
            bad.append("generated input %s is not its manifest's input_sha256_shipped" % e["source_id"])
    inputs_dir = os.path.join(pkg_dir, "inputs")
    files = sorted(os.listdir(inputs_dir)) if os.path.isdir(inputs_dir) else []
    if len(files) != int(pin("invrev", "inputs")) or n != len(files):
        bad.append("%d generated inputs, not the pinned %s" % (len(files), pin("invrev", "inputs")))
    if joined.hexdigest() != pin("invrev", "inputs_combined"):
        bad.append("inputs combined in manifest order %s, not the pinned %s" % (joined.hexdigest()[:16], pin("invrev", "inputs_combined")[:16]))
    return bad


def enter_post_epoch():
    """The one lawful swap: phase-1 epoch bytes at the path, replaced by the corrected owner."""
    if harness_epoch() != "phase1":
        refuse("the post epoch may only follow the phase-1 epoch at %s" % HARNESS)
    rel = [r[2] for r in FS.load() if r[0] == "epoch2"]
    if len(rel) != 1:
        refuse("the projection names %d epoch-2 owners" % len(rel))
    b = FS.candidate_bytes(rel[0])
    if sha(b) != pin("epoch", "post"):
        refuse("the candidate epoch-2 owner is not the pinned bytes")
    io.open(os.path.join(HARNESS, "build_kfields_key.py"), "wb").write(b)


def census_index(rows=None):
    idx = {}
    for phase, attempt, label, wf, ssha, asha, jsha, scsha, spath in (FS.census() if rows is None else rows):
        key = (phase, attempt, label)
        if key in idx:
            refuse("census holds %s twice" % (key,))
        idx[key] = {"wf": wf, "state_sha256": ssha, "script_sha256": scsha, "script_path": spath}
    return idx


def join(idx, run, attempt, label):
    row = idx.get((run, attempt, label))
    if row is None:
        refuse("no saved state for (%s, %s, %s)" % (run, attempt, label))
    return row


def check_script(rendered, embedded, on_disk, expected_sha, where):
    hashes = (sha(rendered), sha(embedded), sha(on_disk))
    if len(set(hashes)) != 1 or hashes[0] != expected_sha:
        refuse("%s: rendered %s / embedded %s / projected %s / census %s are not one script"
               % (where, hashes[0][:16], hashes[1][:16], hashes[2][:16], expected_sha[:16]))


def official_state(wf):
    p = os.path.join(SESS, "workflows", wf + ".json")
    if not os.path.isfile(p):
        refuse("official state %s is not projected" % p)
    return p, json.loads(io.open(p, "rb").read().decode("utf-8"))


def record_all(idx, run, attempt, run_dir, invocations, label_key, record_state, rendered_of):
    """Every invocation in the owner's order: join, render, triple-check, record."""
    for inv in invocations:
        label = inv[label_key]
        row = join(idx, run, attempt, label)
        path = row["script_path"]
        rendered = rendered_of(inv, path)
        state_path, state = official_state(row["wf"])
        embedded = state["script"].encode("utf-8")
        if not os.path.isfile(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "wb").write(rendered)           # the launcher where history armed it
        on_disk = io.open(path, "rb").read()
        check_script(rendered, embedded, on_disk, row["script_sha256"], "%s/%s/%s" % (run, attempt, label))
        bad = record_state(run_dir, state_path)
        if bad:
            refuse("record_state(%s, %s): %s" % (run_dir, row["wf"], bad))
    print("  recorded %d %s states of %s" % (len(invocations), attempt, run))


def retry_count(idx, run):
    return sum(1 for (r, a, _l) in idx if r == run and a == "retry")


def _tool(name, *args):
    """Run one exact scratch tool at its historical path; refuse on non-zero exit."""
    path = {"a3_reaudit.py": S + "/a4/a3_reaudit.py", "a4_regrade.py": S + "/a4_regrade.py", "a4_conflicts.py": S + "/a4_conflicts.py"}[name]
    if sha_file(path) != pin("tool", name):
        refuse("%s at %s is not the pinned tool" % (name, path))
    r = subprocess.run([PY, "-B", path] + list(args), cwd=BENCH, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    os.makedirs(LOG, exist_ok=True)
    io.open(os.path.join(LOG, name + ".out"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    if r.returncode != 0:
        refuse("%s exited %d: %s" % (name, r.returncode, (r.stderr or r.stdout)[-400:]))
    return r.stdout


def stage():
    """The one stage the projected tree calls for."""
    p1 = run_root("phase1"); hr = run_root("hardreview"); fx = run_root("hrfix")
    RUN1, HRRUN, FIXRUN = X + "/runs/" + p1, X + "/runs/" + hr, X + "/runs/" + fx
    ok = lambda scope, name, path: sha_file(path) == FS.pins(scope).get(name)
    if invrev_problems(REVIEW):
        return "inventory"
    if not all([ok("phase-1_package", "phase1.manifest.json", PKG1 + "/phase1.manifest.json"), ok("phase-1_package", "rules.txt", PKG1 + "/rules.txt"),
                ok(p1, "receipt", RUN1 + "/receipt.json"), ok(p1, "finalization", RUN1 + "/finalization.json"),
                ok(p1, "retry receipt", RUN1 + "/retry/receipt.json"), ok(p1, "retry finalization", RUN1 + "/retry/finalization.json")]):
        return "phase1"
    if not all(ok("derived", n, RUN1 + "/" + n) for n in FS.DERIVED):
        return "bridge"
    if not all([ok(hr, "receipt", HRRUN + "/receipt.json"), ok(hr, "finalization", HRRUN + "/finalization.json"),
                ok(hr, "retry receipt", HRRUN + "/retry/receipt.json"), ok(hr, "retry finalization", HRRUN + "/retry/finalization.json")]):
        return "hardreview"
    if not all([ok(fx, "receipt", FIXRUN + "/receipt.json"), ok(fx, "finalization", FIXRUN + "/finalization.json")]):
        return "correction"
    if not all(ok("final_seven-file_package", n, PKGF + "/" + n) for n in FS.pins("final_seven-file_package")):
        return "final"
    return "done"


def _owners():
    sys.path.insert(0, HARNESS)
    os.chdir(BENCH)


def baseline_problems(doc):
    """The freshly produced A3 baseline against the pinned facts: digest, file count, no problem."""
    bad = []
    if doc.get("digest") != pin("baseline", "digest"):
        bad.append("baseline digest %s is not the pinned %s" % (str(doc.get("digest"))[:16], pin("baseline", "digest")[:16]))
    if len(doc.get("files") or {}) != int(pin("baseline", "files")):
        bad.append("baseline lists %d files, not the pinned %s" % (len(doc.get("files") or {}), pin("baseline", "files")))
    if doc.get("primary_problems"):
        bad.append("baseline records primary problems: %s" % doc.get("primary_problems")[:2])
    return bad


def stage_inventory():
    """The inventory-history stage: the real owner rebuilds its 39-file review package over the
    168-proposal inventory, held to the freeze receipt; then the final inventory is restored."""
    bad = git_identity_problems()
    if bad:
        refuse(bad[0])
    print("  git identity: base tree %s derived read-only" % pin("git", "base_tree")[:16])
    if os.path.exists(REVIEW):
        refuse("the review package directory exists before the owner builds it: %s" % REVIEW)
    owner = os.path.join(HARNESS, "build_inventory_review.py")
    if sha_file(owner) != pin("owner", "build_inventory_review.py"):
        refuse("the review-package owner at %s is not the pinned bytes" % owner)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    os.makedirs(LOG, exist_ok=True)
    out = subprocess.run([PY, "-B", owner], cwd=HARNESS, capture_output=True, text=True, env=env)
    io.open(os.path.join(LOG, "build_inventory_review.out"), "w", encoding="utf-8").write(out.stdout + out.stderr)
    m = re.search(r"events: (\d+)\s+proposals shipped: (\d+)", out.stdout)
    if out.returncode != 0 or "PACKAGE: PASS" not in out.stdout or not m:
        refuse("review-package build exited %d without PACKAGE: PASS: %s" % (out.returncode, (out.stderr or out.stdout)[-300:]))
    if (m.group(1), m.group(2)) != (pin("invrev", "events"), pin("invrev", "proposals")):
        refuse("the owner built %s events and %s proposals, not the pinned %s / %s" % (m.group(1), m.group(2), pin("invrev", "events"), pin("invrev", "proposals")))
    ver = subprocess.run([PY, "-B", owner, "--verify"], cwd=HARNESS, capture_output=True, text=True, env=env)
    io.open(os.path.join(LOG, "build_inventory_review.verify.out"), "w", encoding="utf-8").write(ver.stdout + ver.stderr)
    if ver.returncode != 0 or "VERIFY: PASS" not in ver.stdout:
        refuse("review-package verify exited %d without VERIFY: PASS" % ver.returncode)
    print("  review package: %s events, %s proposals, builder PASS, verify PASS" % (m.group(1), m.group(2)))
    bad = invrev_problems(REVIEW)
    if bad:
        refuse(bad[0])
    for name in ("prefix.md", "package.manifest.json", "final_sign_input.template.json"):
        anchor("invrev", name, os.path.join(REVIEW, name))
    print("  review inputs: %s files equal their manifest entries; combined in manifest order %s" % (pin("invrev", "inputs"), pin("invrev", "inputs_combined")[:16]))
    restore_final_inventory()
    anchor("inventory", "final", INVENTORY)


def stage_phase1(idx):
    RUN1 = X + "/runs/" + run_root("phase1")
    if os.path.exists(BASELINE):
        refuse("a baseline already exists at %s; the run must produce it" % BASELINE)
    _tool("a3_reaudit.py", BASELINE)
    anchor("baseline", "a3_baseline.json", BASELINE)
    doc = json.loads(io.open(BASELINE, "rb").read().decode("utf-8"))
    bad = baseline_problems(doc)
    if bad:
        refuse(bad[0])
    print("  baseline: digest %s, %d files, 0 primary problems" % (doc["digest"][:16], len(doc["files"])))
    _owners()
    import build_kfields_key as K
    if not K.__file__.startswith(HARNESS + "/") or sha_file(K.__file__) != pin("epoch", "phase1"):
        refuse("the imported key owner is not the projected phase-1 epoch")
    K.build_phase1(PKG1)
    anchor("phase-1_package", "phase1.manifest.json", PKG1 + "/phase1.manifest.json")
    anchor("phase-1_package", "rules.txt", PKG1 + "/rules.txt")
    out = K.prepare_run(RUN1)
    if not out.get("ok"):
        refuse("phase-1 prepare: %s" % out.get("problems"))
    p1 = run_root("phase1")
    record_all(idx, p1, "primary", RUN1, out["invocations"], "packet_id", K.record_state, lambda inv, path: inv["script"].encode("utf-8"))
    anchor(p1, "receipt", RUN1 + "/receipt.json")
    doc = K.finalize(RUN1)
    anchor(p1, "finalization", RUN1 + "/finalization.json")
    child = doc.get("child")
    if not child or len(child["invocations"]) != retry_count(idx, p1):
        refuse("the owner derived %s retries, the census holds %d" % (len(child["invocations"]) if child else "no", retry_count(idx, p1)))
    record_all(idx, p1, "retry", child["dir"], child["invocations"], "packet_id", K.record_state, lambda inv, path: inv["script"].encode("utf-8"))
    anchor(p1, "retry receipt", RUN1 + "/retry/receipt.json")
    kid = K.finalize(RUN1 + "/retry")
    anchor(p1, "retry finalization", RUN1 + "/retry/finalization.json")
    if kid.get("retry") or kid.get("child"):
        refuse("the phase-1 child names a third attempt")


def stage_bridge():
    RUN1 = X + "/runs/" + run_root("phase1")
    enter_post_epoch()
    io.open(POINTER, "wb").write((RUN1 + "\n").encode("utf-8"))
    _tool("a4_regrade.py")
    anchor("derived", "regrade_1370.json", RUN1 + "/regrade_1370.json")
    rg = json.loads(io.open(RUN1 + "/regrade_1370.json", "rb").read().decode("utf-8"))
    facts = {"primary_valid": rg["primary"]["ledger_after"]["valid"], "primary_invalid": rg["primary"]["ledger_after"]["invalid_response"],
             "child_valid": rg["child"]["ledger_after"]["valid"], "child_invalid": rg["child"]["ledger_after"]["invalid_response"],
             "selected": rg["selection"]["usable"], "surplus": rg["selection"]["child_surplus"], "unresolved": len(rg["selection"]["unresolved"])}
    for k, v in facts.items():
        if str(v) != pin("regrade", k):
            refuse("regrade %s is %s, not the pinned %s" % (k, v, pin("regrade", k)))
    print("  regrade facts: %s" % facts)
    _tool("a4_conflicts.py")
    anchor("derived", "conflicts_1370.json", RUN1 + "/conflicts_1370.json")
    cf = json.loads(io.open(RUN1 + "/conflicts_1370.json", "rb").read().decode("utf-8"))
    facts = {"valid_envelopes": cf["valid_envelopes_read"], "ambiguities": cf["counts"]["model_reported_ambiguities"],
             "both_rejected": cf["counts"]["items_both_drafts_rejected"], "locator_groups": cf["counts"]["conflicting_locator_groups"]}
    for k, v in facts.items():
        if str(v) != pin("conflicts", k):
            refuse("conflicts %s is %s, not the pinned %s" % (k, v, pin("conflicts", k)))
    print("  conflict facts: %s" % facts)
    for name in FS.DERIVED:
        same = sha_file(RUN1 + "/" + name) == sha_file(os.path.join(R, "foundation", "a4_derived", name))
        print("  fresh %s equals the preliminary copy: %s" % (name, same))


def _script_from_owner(inv, path):
    if inv.get("scriptPath") != path:
        refuse("the owner armed %s, the census places the launcher at %s" % (inv.get("scriptPath"), path))
    b = io.open(inv["scriptPath"], "rb").read()
    if sha(b) != inv.get("script_sha256"):
        refuse("the owner's launcher at %s is not its own script_sha256" % path)
    return b


def stage_hardreview(idx):
    RUN1, hr = X + "/runs/" + run_root("phase1"), run_root("hardreview")
    HRRUN = X + "/runs/" + hr
    _owners()
    import build_kfields_hard_review as HR
    HR.build(HRPKG, RUN1)
    for name, fname in PACKAGE_FILES["hard-review_package"].items():
        anchor("hard-review_package", name, HRPKG + "/" + fname)
    prep = HR.prepare_run(HRRUN, HRPKG, RUN1)
    if not prep.get("ok"):
        refuse("hard-review prepare: %s" % prep.get("problems"))
    record_all(idx, hr, "primary", HRRUN, prep["invocations"], "label", HR.record_state, _script_from_owner)
    anchor(hr, "receipt", HRRUN + "/receipt.json")
    doc = HR.finalize(HRRUN, HRPKG, RUN1)
    anchor(hr, "finalization", HRRUN + "/finalization.json")
    child = doc.get("child")
    if not child or len(child["invocations"]) != retry_count(idx, hr):
        refuse("the owner derived %s hard-review retries, the census holds %d" % (len(child["invocations"]) if child else "no", retry_count(idx, hr)))
    record_all(idx, hr, "retry", child["dir"], child["invocations"], "label", HR.record_state, _script_from_owner)
    anchor(hr, "retry receipt", HRRUN + "/retry/receipt.json")
    kid = HR.finalize(HRRUN + "/retry", HRPKG, RUN1)
    anchor(hr, "retry finalization", HRRUN + "/retry/finalization.json")
    if kid.get("retry") or kid.get("child"):
        refuse("the hard-review child names a third attempt")


def stage_correction(idx):
    RUN1, HRRUN, fx = X + "/runs/" + run_root("phase1"), X + "/runs/" + run_root("hardreview"), run_root("hrfix")
    FIXRUN = X + "/runs/" + fx
    _owners()
    import build_kfields_hr_correction as FIX
    FIX.build(FIXD, HRRUN, RUN1, HRPKG)
    for name, fname in PACKAGE_FILES["correction_package"].items():
        anchor("correction_package", name, FIXD + "/" + fname)
    bound = FIX.Bound(FIXD, HRRUN, RUN1, HRPKG)
    prep = FIX.prepare_run(FIXRUN, bound)
    if not prep.get("ok"):
        refuse("correction prepare: %s" % prep.get("problems"))
    record_all(idx, fx, "primary", FIXRUN, prep["invocations"], "label", FIX.record_state, _script_from_owner)
    anchor(fx, "receipt", FIXRUN + "/receipt.json")
    doc = FIX.finalize(FIXRUN, bound)
    anchor(fx, "finalization", FIXRUN + "/finalization.json")
    if doc.get("retry") or doc.get("child"):
        refuse("the correction run names a retry")


def stage_final():
    RUN1, HRRUN, FIXRUN = (X + "/runs/" + run_root(k) for k in ("phase1", "hardreview", "hrfix"))
    _owners()
    import build_kfields_final as F
    F.build(PKGF, RUN1, HRRUN, FIXRUN)
    for name in FS.pins("final_seven-file_package"):
        anchor("final_seven-file_package", name, PKGF + "/" + name)


def step():
    if not inside_projection():
        refuse("not inside the projected historical tree (no projection marker, harness or private /tmp)")
    st = stage()
    print("STAGE %s" % st)
    if st == "done":
        return 0
    bad = (epoch_problems(st) if st not in ("bridge", "inventory") else []) + inventory_problems(st)
    if bad:
        refuse(bad[0])
    idx = census_index() if st not in ("inventory", "bridge", "final") else None
    {"inventory": stage_inventory, "phase1": lambda: stage_phase1(idx), "bridge": stage_bridge, "hardreview": lambda: stage_hardreview(idx),
     "correction": lambda: stage_correction(idx), "final": stage_final}[st]()
    print("STAGE %s complete" % st)
    return 0


def export(out_root):
    os.makedirs(out_root, exist_ok=True)
    roots = [REVIEW, X + "/kfields_key_a4", HRPKG, FIXD, PKGF, S + "/a4", POINTER, LOG] + [X + "/runs/" + run_root(k) for k in ("phase1", "hardreview", "hrfix")]
    rows = []
    for root in roots:
        paths = [root] if os.path.isfile(root) else [os.path.join(dp, f) for dp, _d, fs in os.walk(root) for f in fs] if os.path.isdir(root) else []
        for p in paths:
            rel = os.path.relpath(p, S)
            dst = os.path.join(out_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(p, dst)
            b = io.open(p, "rb").read()
            rows.append((rel, len(b), sha(b)))
    rows.sort()
    text = "path\tbytes\tsha256\n" + "".join("%s\t%d\t%s\n" % r for r in rows)
    io.open(os.path.join(out_root, "TREE.tsv"), "w", encoding="utf-8").write(text)
    print("exported %d files, %d bytes; tree sha256 %s" % (len(rows), sum(r[1] for r in rows), sha(text.encode("utf-8"))))


def run(out_root):
    if os.path.isdir(out_root) and os.listdir(out_root):
        refuse("output root is not empty: %s" % out_root)   # a fresh empty root, before any build work
    if not inside_projection():
        refuse("not inside the projected historical tree")
    for _ in range(9):
        st = stage()
        if st == "done":
            break
        r = subprocess.run([PY, "-B", os.path.abspath(__file__), "step"], cwd=BENCH, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if r.returncode != 0:
            print("FOUNDATION REFUSED at stage %s" % st)
            export(out_root)                          # whatever was produced, for the report
            return r.returncode
    if stage() != "done":
        refuse("the tree is not complete after every stage")
    export(out_root)
    return 0


def red_probe():
    """Against the preliminary view: the A3-package launch manifest, no baseline, one key epoch."""
    if not inside_projection():
        refuse("not inside the projected historical tree")
    red = 0
    probe = S + "/a4/a3_baseline.probe.json"
    out = _tool("a3_reaudit.py", probe) if sha_file(S + "/a4/a3_reaudit.py") == pin("tool", "a3_reaudit.py") else ""
    digest = json.loads(io.open(probe, "rb").read().decode("utf-8"))["digest"] if os.path.isfile(probe) else None
    print("RED1 launch manifest at the harness path %s; re-audit digest %s vs pinned %s -> %s"
          % ((sha_file(HARNESS + "/build_launch_manifest.py") or "absent")[:16], (digest or "none")[:16], pin("baseline", "digest")[:16], "RED (mismatch)" if digest != pin("baseline", "digest") else "GREEN"))
    red += digest != pin("baseline", "digest")
    _owners()
    import build_kfields_key as K
    try:
        probs = K.preflight()["problems"]
        verdict = "RED (preflight refused: %s)" % probs[:2] if probs else "GREEN"
    except Exception as exc:                          # noqa: BLE001 - by design
        verdict, probs = "RED (preflight raised %s)" % type(exc).__name__, [str(exc)]
    print("RED2 no baseline at %s -> %s" % (BASELINE, verdict))
    red += bool(probs)
    bad = epoch_problems("phase1")
    print("RED3 single key epoch %s at the harness path for stage phase1 -> %s" % (harness_epoch() or "none", "RED (%s)" % bad[0] if bad else "GREEN"))
    red += bool(bad)
    print("RED probes: %d of 3 refuse" % red)
    return 0 if red == 3 else 1


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["step"]:
        sys.exit(step())
    if cmd == ["run"] and len(sys.argv) > 2:
        sys.exit(run(sys.argv[2]))
    if cmd == ["red-probe"]:
        sys.exit(red_probe())
    sys.exit("usage: foundation.py step | run <out_root> | red-probe")
