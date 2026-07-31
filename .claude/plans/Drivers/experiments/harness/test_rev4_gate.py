"""Saved gate proofs (the review demanded these as real tests, not hand-runs):
GREEN on the real rev-4 patch · RED on a deliberate old-rule reintroduction ·
every Part-F row maps to a real added line in the patch."""
import io, os, subprocess, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(_HERE, "rev4_coverage_check.py")
PATCH = os.path.join(_HERE, "exp5_rev4_docs.patch")

def _run(patch):
    return subprocess.run([sys.executable, GATE, patch], capture_output=True, text=True)

def test_gate_green_on_the_real_patch():
    r = _run(PATCH)
    assert r.returncode == 0, r.stdout + r.stderr

def test_gate_red_when_an_old_rule_is_reintroduced():
    s = io.open(PATCH, encoding="utf-8").read()
    bad = s.replace("`occurrence_in_part` is PER-PART:", "`occurrence` is a GLOBAL 1-based count —", 1)
    assert bad != s
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as f:
        f.write(bad); tmp = f.name
    r = _run(tmp)
    os.unlink(tmp)
    assert r.returncode != 0, "gate stayed green on a reintroduced global-count rule"
    assert "GLOBAL 1-based count" in r.stdout

def _added_by_file(patch_text):
    """Map each patched file -> its ADDED lines only (per-file, not patch-wide)."""
    out, cur = {}, None
    for ln in patch_text.splitlines():
        if ln.startswith("+++ b/"):
            cur = ln[6:].strip().split("/")[-1]; out.setdefault(cur, [])
        elif ln.startswith("+") and not ln.startswith("+++") and cur:
            out[cur].append(ln[1:])
    return {f: "\n".join(v) for f, v in out.items()}

def test_every_part_f_row_maps_to_its_own_files_hunks():
    """Every Part-F row: either a token that must appear in THAT FILE's added
    lines, or an explicit NO_CHANGE row that must have NO hunk at all."""
    F = [
        ("FINAL_DESIGN.md", "OD-11 is applied by the MODEL"),                      # F1
        ("FINAL_DESIGN.md", "never derives a unit or scale from a name"),          # F2 resolver
        ("FINAL_DESIGN.md", "per_x` signal and the ADMISSION KERNEL"),             # F2 per-X
        ("FINAL_DESIGN.md", "attacked by hidden-grading fixtures"),                # F1 monitor
        ("15_CandidateFactPacket.md", "RE-FREEZE PENDING [O-a"),                   # F4 label
        ("15_CandidateFactPacket.md", "ix.scale"),                                 # F4 D.2 row
        ("15_CandidateFactPacket.md", "Applied exactly ONCE"),                     # F4 per-X peel
        ("BUILD_AND_OPERATIONS.md", "PENDING OWNER SIGN-OFF O-d"),                 # F5 contract v4
        ("BUILD_AND_OPERATIONS.md", "hint-era 29+7/parity gate is RETIRED"),       # F5 gate
        ("BUILD_AND_OPERATIONS.md", "per-slot statement intake"),                  # F5 CLI order
        ("BUILD_AND_OPERATIONS.md", "shims are RETIRED"),                          # F5 shim
        ("FableExperimentWorkOrder.md", "the 32 model-owned fields:"),             # F7 list
        ("FableExperimentWorkOrder.md", "v2.2-rev4 AMENDMENT BLOCK"),              # F7 block
        ("FableExperimentWorkOrder.md", "RETIRED (rev-4): EXP-5 uses the shared"), # F7 dep row
        ("protocol.md", "BOTH roles emit the SAME envelope"),                      # F9
        ("exp5_scoring_spec_v3.md", "PROVEN (built in the v2.0 arc)"),             # F6 transport
        ("exp5_scoring_spec_v3.md", "rev-4 Part D law"),                           # F6 matcher
        ("OWNER_DECISION_value_text_numeric.md", "CORRECTED 2026-07-26"),          # F11
        ("FINAL_DESIGN.md", "OWNER-APPROVED 2026-07-26, form O3"),                 # F14
        ("15_CandidateFactPacket.md", "Applied exactly ONCE"),                     # F4 per-X
        ("exp5_scoring_spec_v3.md", "HISTORY — superseded matching algorithm"),    # F6 history
        ("FableExperimentWorkOrder.md", "value, scale_multiplier, unit_scale_evidence"),  # F7 grading
        ("BUILD_AND_OPERATIONS.md", "the MODEL decides unit/scale/time meaning"),  # F5 ownership
        ("15_CandidateFactPacket.md", "SUBMITS raw evidence"),                     # 4f boundary sentence
        ("BUILD_AND_OPERATIONS.md", "RE-STAMPED by the O-a v2.0 re-freeze sweep"), # 4f pin marker
        ("FableExperimentWorkOrder.md", "exact one-to-one bijection"),             # 4f fixpoint word
        ("exp5_scoring_spec_v3.md", "> **v3 (superseded by the rev-4 Part D law)**"),  # 4f history form
    ]
    NO_CHANGE = ["ChannelContract.md"]   # F: verified no-change rows must have NO hunk
    # BLOCKED TARGETS, read from the patch builder — the ONE owner of that list.
    # A row whose document cannot be patched from the committed tree must have no
    # hunk, and the builder fails if such a document would build cleanly, so this
    # is an accounted-for gap and not an excuse.
    import sys as _s
    _s.path.insert(0, _HERE)
    from rev4_build_patch import BLOCKED
    blocked_names = {b.rsplit("/", 1)[-1] for b in BLOCKED}
    patch = io.open(PATCH, encoding="utf-8").read()
    added = _added_by_file(patch)
    missing = [f"{f}: {tok!r}" for f, tok in F
               if f not in blocked_names and tok not in added.get(f, "")]
    assert not missing, f"Part-F rows with no hunk IN THEIR OWN FILE: {missing}"
    leaked = [f for f in blocked_names if f in added]
    assert not leaked, f"blocked target(s) unexpectedly carry hunks: {leaked}"
    wrong = [f for f in NO_CHANGE if f in added]
    assert not wrong, f"NO-CHANGE rows that unexpectedly have hunks: {wrong}"
    # completeness the other way: every patched file is covered by >=1 F row
    covered = {f for f, _ in F}
    uncovered = [f for f in added if f not in covered]
    assert not uncovered, f"patched files with NO Part-F row check: {uncovered}"


def _check_dispositions(pkg_path):
    """Parse Part F FROM the package at pkg_path; every row must resolve per
    its tag: hunk -> its doc has added lines in the patch; no-change -> no
    hunk; artifact -> the named file exists; implementation/package -> counted."""
    import re
    pkg = io.open(pkg_path, encoding="utf-8").read()
    rows = re.findall(r"^\| (F\d+) \| ([^|]+) \|.*\[disposition=([A-Za-z0-9:._-]+)\]", pkg, re.M)
    ids = [r[0] for r in rows]
    assert sorted(ids) == sorted({f"F{i}" for i in range(1, 15)}), f"need exactly one each of F1-F14, got {sorted(ids)}"
    # `blocked` is a FIFTH disposition, added because a row can be genuinely
    # unpatchable: its document is not Core's to stage and its committed text is
    # not the base these edits were authored against. It is not a soft option —
    # the document must appear in the patch builder's BLOCKED list (one owner),
    # must carry no hunk, and the builder itself fails if it would build cleanly.
    KNOWN = {"hunk", "no-change", "package", "implementation", "blocked"}
    bad = [(fid, d) for fid, _, d in rows if d not in KNOWN and not d.startswith("artifact:")]
    assert not bad, f"unknown dispositions: {bad}"
    import sys as _s
    _s.path.insert(0, _HERE)
    from rev4_build_patch import BLOCKED
    blocked_names = {b.rsplit("/", 1)[-1] for b in BLOCKED}
    added = _added_by_file(io.open(PATCH, encoding="utf-8").read())
    fails = []
    for fid, doc, disp in rows:
        doc = doc.strip().split(" ")[0].split(":")[0].split("/")[-1]
        if disp == "hunk":
            base = doc if doc.endswith(".md") else None
            if base and base in blocked_names:
                fails.append(f"{fid}: {base} is a BLOCKED target, so claiming a "
                             f"hunk is a stale package claim")
            elif base and base not in added: fails.append(f"{fid}: no hunks for {base}")
        elif disp == "blocked":
            if doc not in blocked_names:
                fails.append(f"{fid}: {doc} is not in the builder's BLOCKED list "
                             f"— 'blocked' is not a disposition a row may award "
                             f"itself")
            if doc in added:
                fails.append(f"{fid}: {doc} is blocked yet carries hunks")
        elif disp == "no-change":
            # row-level no-change: the FILE may carry other rows' hunks; only a
            # file whose EVERY row is no-change must have zero hunks
            hunk_docs = {d.strip().split(" ")[0].split(":")[0].split("/")[-1]
                         for _, d, dd in rows if dd == "hunk"}
            if doc in added and doc not in hunk_docs:
                fails.append(f"{fid}: unexpected hunks for {doc}")
        elif disp.startswith("artifact:"):
            if not os.path.exists(os.path.join(_HERE, disp.split(":", 1)[1])): fails.append(f"{fid}: artifact missing")
    assert not fails, fails


def test_part_f_dispositions_derived_from_the_package():
    _check_dispositions(os.path.join(_HERE, "exp5_rev4_package.md"))


def test_malformed_disposition_is_rejected():
    """The reviewer's typo-mutation attack, saved — on a TEMP COPY (the live
    package is never written; the old version wrote to it and a crash between
    write and restore would have left the tree mutated), asserting the
    SPECIFIC unknown-dispositions detector so an unrelated failure can never
    green this test."""
    orig = io.open(os.path.join(_HERE, "exp5_rev4_package.md"), encoding="utf-8").read()
    mutated = orig.replace("[disposition=hunk]", "[disposition=typo]", 1)
    assert mutated != orig
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as f:
        f.write(mutated)
        tmp = f.name
    failed_msg = None
    try:
        try:
            _check_dispositions(tmp)
        except AssertionError as e:
            failed_msg = str(e)
    finally:
        os.unlink(tmp)
    assert failed_msg is not None, "a typo disposition slipped through the derived test"
    assert "unknown dispositions" in failed_msg and "typo" in failed_msg, (
        f"failed on the WRONG detector: {failed_msg}")


def _a3_skeleton():
    import re
    pkg = io.open(os.path.join(_HERE, "exp5_rev4_package.md"), encoding="utf-8").read()
    part_a = pkg.split("## PART A")[1].split("## PART B")[0]
    a3 = part_a.split("### A3")[1].split("### A4")[0]
    return pkg, part_a, re.search(r"```\n(.*?)```", a3, re.S).group(1)


def test_package_self_checks():
    """The Part-J surface checks, SAVED (they were advertised as run but never
    saved as a test — reviewer-caught): no ellipses, the A3 skeleton is VALID
    JSON with exactly the 32 item keys, no law-code labels and no external
    file references inside Part A (the model-facing prompt).

    Parsing uses raw_transport.parse_exact, NOT json.loads — plain json.loads
    silently keeps the LAST of duplicate keys, so a duplicated driver_state
    still counted as '32 fields' (reviewer-reproduced false green)."""
    import re
    sys.path.insert(0, _HERE)
    import raw_transport
    pkg, part_a, skeleton = _a3_skeleton()
    assert "…" not in pkg, "unicode ellipsis in the package"
    assert "..." not in pkg, "three-dot sequence in the package"
    obj = raw_transport.parse_exact(skeleton)   # strict: rejects duplicate keys
    item = obj["facts"][0]["item"]
    assert len(item) == 32, f"A3 item has {len(item)} keys, not 32"
    fact = obj["facts"][0]
    assert set(fact) == {"fact_type", "part_ref", "occurrence_in_part", "per_x", "item"}
    assert set(obj) == {"source_id", "facts", "abstentions"}
    law_codes = re.findall(
        r"\b(?:NAME|OD|DU|FACT|UNIT|PER|FS|XC|MF)-\d+\b", part_a)
    assert not law_codes, f"law-code labels leak into the prompt: {law_codes}"
    ext_refs = re.findall(r"[A-Za-z0-9_/]+\.(?:md|py|json[l]?)\b", part_a)
    assert not ext_refs, f"external file references in Part A: {ext_refs}"


def test_duplicate_key_in_skeleton_is_rejected():
    """In-memory mutation: duplicating an item key must FAIL the strict parse
    (plain json.loads accepted it silently — the reviewer's false green)."""
    sys.path.insert(0, _HERE)
    import raw_transport
    _, _, skeleton = _a3_skeleton()
    line = '"driver_state": "<the lane\'s enum, Rule 4>",'
    assert skeleton.count(line) == 1
    mutated = skeleton.replace(line, line + "\n      " + line, 1)
    try:
        raw_transport.parse_exact(mutated)
        raise AssertionError("duplicate driver_state slipped through parse_exact")
    except raw_transport.RawTransportError:
        pass


def test_plan_v2_corrected_phrases_stay_corrected():
    """Regression pins for the three rev-4h Plan-v2 corrections."""
    plan = io.open(os.path.join(_HERE, "FableExperimentPlan_v2.md"), encoding="utf-8").read()
    assert "market-moving" not in plan, "the du_worthy correction regressed"
    assert "`du_worthy` fact (the locked DU-03 gate" in plan
    assert "LEGACY-ONLY evidence" in plan, "the resolver legacy-warning regressed"
    assert "SOLELY through the production `run_event` dry-run" in plan, \
        "the one-rule-engine statement regressed"
