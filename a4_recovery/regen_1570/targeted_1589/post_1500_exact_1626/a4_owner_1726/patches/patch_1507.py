import io, sys
H = sys.argv[1]
def patch(path, edits):
    s = io.open(path, encoding="utf-8").read()
    for old, new, n in edits:
        assert s.count(old) == n, (path[-40:], s.count(old), old[:70]); s = s.replace(old, new)
    io.open(path, "w", encoding="utf-8").write(s)

patch(H + "/build_kfields_final_targeted.py", [
('''CORR_PREFIX_MARKS = PREFIX_MARKS + ("[A4 CORRECTION TASK]",)''',
 '''CORR_PREFIX_MARKS = PREFIX_MARKS + ("[FINAL DECISION RULES]", "[A4 CORRECTION TASK]")''', 1),
('''CORR2_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr2_binding.json")
CORRECTION_DOORS = (CORR_DOOR, CORR2_DOOR)      # the rounds, in the order their overlays apply
''', '''CORR2_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr2_binding.json")
# Codex SEQ 1507: the third round over exactly the events whose accepted shard
# still carries an open issue after run 1506, with the locked A4 owner's exact
# final-decision block served in the common correction prefix.
CORR3_DOOR = "a4_final_targeted_correction_3"
CORR3_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr3_1507")
CORR3_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1507.json"
CORR3_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1507.json")
CORR3_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr3_binding.json")
CORRECTION_DOORS = (CORR_DOOR, CORR2_DOOR, CORR3_DOOR)   # the rounds, in the order their overlays apply
#: every lead origin this wrapper emits starts with this stem; a lead id is the rest of it over the event
_ORIGIN_STEM = "final_targeted_"
''', 1),
('''        CORR2_DOOR: {
            "pkg_dir": CORR2_PKG_DIR, "budget_receipt": CORR2_BUDGET_RECEIPT,
            "review_receipt": CORR2_REVIEW_RECEIPT, "binding": CORR2_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME + "-2", "authority": "Codex SEQ 1505",
            "origin": "final_targeted_correction_2", "receipt_key": "lead_binding",
            "population": _open_issue_population}}[door]
''', '''        CORR2_DOOR: {
            "pkg_dir": CORR2_PKG_DIR, "budget_receipt": CORR2_BUDGET_RECEIPT,
            "review_receipt": CORR2_REVIEW_RECEIPT, "binding": CORR2_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME + "-2", "authority": "Codex SEQ 1505",
            "origin": "final_targeted_correction_2", "receipt_key": "lead_binding",
            "population": _open_issue_population},
        CORR3_DOOR: {
            "pkg_dir": CORR3_PKG_DIR, "budget_receipt": CORR3_BUDGET_RECEIPT,
            "review_receipt": CORR3_REVIEW_RECEIPT, "binding": CORR3_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME + "-3", "authority": "Codex SEQ 1507",
            "origin": "final_targeted_correction_3", "receipt_key": "lead_binding",
            "population": _open_issue_population}}[door]
''', 1),
('''    raw, origin = raws[sid], origins[sid]
    return [collections.OrderedDict([
        ("lead_id", "%s/%s" % (origin.rsplit("_", 1)[-1], sid)), ("origin", origin),
        ("sha256", _sha(raw)), ("reply", raw)])]
''', '''    raw, origin = raws[sid], origins[sid]
    if not origin.startswith(_ORIGIN_STEM):
        raise ValueError("%s: lead origin %r is not this wrapper's" % (sid, origin))
    return [collections.OrderedDict([
        ("lead_id", "%s/%s" % (origin[len(_ORIGIN_STEM):], sid)), ("origin", origin),
        ("sha256", _sha(raw)), ("reply", raw)])]
''', 1),
('''def correction_prefix():
    """The primary prefix, transformed - never re-composed: the one input
    sentence made truthful for this payload and the correction task joining
    the trusted block; every other byte is the primary prefix's own."""
    base, marker = prompt_prefix(), "[BOUNDARY]\\n"
    if base.count(marker) != 1:
        raise ValueError("the primary prefix no longer carries one boundary")
    stale = input_sentence()
    if base.count(stale) != 1:
        raise ValueError("the primary input sentence is not present exactly once")
    base = base.replace(stale, correction_input_sentence(), 1)
    head, tail = base.split(marker, 1)
    return head + "[A4 CORRECTION TASK]\\n%s\\n\\n" % _CORRECTION_TASK + marker + tail
''', '''def _decision_block():
    """The locked A4 owner's exact ten-line final-decision block, read from
    its owning artifact through the owner's own accessor and served in the
    owner's own section shape (build_kfields_final.decision_prefix). Never
    copied, never paraphrased."""
    return "[FINAL DECISION RULES]\\n%s\\n\\n" % F._decision_rules_source().rstrip()


def correction_prefix():
    """The primary prefix, transformed - never re-composed: the one input
    sentence made truthful for this payload, then the owner's final-decision
    block and the correction task joining the trusted block above the
    boundary (Codex SEQ 1507 item 4); every other byte is the primary
    prefix's own."""
    base, marker = prompt_prefix(), "[BOUNDARY]\\n"
    if base.count(marker) != 1:
        raise ValueError("the primary prefix no longer carries one boundary")
    stale = input_sentence()
    if base.count(stale) != 1:
        raise ValueError("the primary input sentence is not present exactly once")
    base = base.replace(stale, correction_input_sentence(), 1)
    head, tail = base.split(marker, 1)
    return head + _decision_block() + "[A4 CORRECTION TASK]\\n%s\\n\\n" % _CORRECTION_TASK + marker + tail
''', 1),
('''        if "[RULES]\\n%s\\n\\n" % rules not in text[:cut]:
            bad.append("%s: the current rules are not served whole and first"
                       % where)
''', '''        if "[RULES]\\n%s\\n\\n" % rules not in text[:cut]:
            bad.append("%s: the current rules are not served whole and first"
                       % where)
        if ph["door"] != DOOR and text[:cut].count(_decision_block()) != 1:
            bad.append("%s: the owner's final-decision block is not served exactly once" % where)
''', 1),
('''    d["review_receipt"] = collections.OrderedDict([
        ("path", r["review_receipt"]), ("sha256", INV.sha_file(r["review_receipt"]))])
    return d
''', '''    d["review_receipt"] = collections.OrderedDict([
        ("path", r["review_receipt"]), ("sha256", INV.sha_file(r["review_receipt"]))])
    rules = os.path.join(F._HERE, F.DECISION_RULES_NAME)
    d["decision_rules"] = collections.OrderedDict([("path", rules), ("sha256", INV.sha_file(rules))])
    return d
''', 1),
('''        ("correction_task_sha256", _sha(_CORRECTION_TASK)),
        ("boundary_sha256", _sha(HR._boundary_at(SUFFIX))),''',
 '''        ("correction_task_sha256", _sha(_CORRECTION_TASK)),
        ("decision_rules_sha256", _sha(F._decision_rules_source())),
        ("boundary_sha256", _sha(HR._boundary_at(SUFFIX))),''', 1),
])

patch(H + "/a6_launch_freeze.py", [
('''                   "final_targeted_dir.txt", "final_targeted_corr_dir.txt")''',
 '''                   "final_targeted_dir.txt", "final_targeted_corr_dir.txt",
                   "final_targeted_corr2_dir.txt")''', 1),
('''    # THE SUCCESSOR FINAL CORRECTION (Codex SEQ 1505 item 1): the same owner
    # re-proves its bound correction run against the PINNED package it ran
    # under and returns one proved row per attempt; this owner only records
    # it. Counting a run accepts none of its outputs.
    for spent in _FT.proved_spend(_read_ptr("final_targeted_corr_dir.txt"), _FT.CORR_DOOR):
        total += spent["calls"]
        rows.append(collections.OrderedDict([
            ("stage", "final_targeted_correction_%s"
             % ("primary" if spent["attempt"] == 1 else "retry")),
            ("run_dir", spent["run_dir"]),
            ("receipt_sha256", spent["receipt_sha256"]),
            ("finalization_sha256", spent["finalization_sha256"]),
            ("raw_tree", spent["raw_tree"]),
            ("calls", spent["calls"])]))
''', '''    # THE SUCCESSOR FINAL CORRECTION ROUNDS (Codex SEQ 1505 item 1, SEQ 1507
    # item 1): the same owner re-proves each bound correction run against the
    # PINNED package it ran under and returns one proved row per attempt;
    # this owner only records it, under the round's own origin name.
    # Counting a run accepts none of its outputs.
    for door, pointer in ((_FT.CORR_DOOR, "final_targeted_corr_dir.txt"),
                          (_FT.CORR2_DOOR, "final_targeted_corr2_dir.txt")):
        for spent in _FT.proved_spend(_read_ptr(pointer), door):
            total += spent["calls"]
            rows.append(collections.OrderedDict([
                ("stage", "%s_%s" % (_FT._round(door)["origin"],
                                     "primary" if spent["attempt"] == 1 else "retry")),
                ("run_dir", spent["run_dir"]),
                ("receipt_sha256", spent["receipt_sha256"]),
                ("finalization_sha256", spent["finalization_sha256"]),
                ("raw_tree", spent["raw_tree"]),
                ("calls", spent["calls"])]))
''', 1),
])

# the closed rounds' suites: "not one prompt byte moved" becomes "moved by exactly the owner's block"
patch(H + "/test_a4_second_correction_1505.py", [
('''    pinned = _load(os.path.join(FT.CORR_PKG_DIR, FT.CORR_MANIFEST_NAME))
    live = FT.manifest(CORR2)
    prefix = FT.correction_prefix()
    assert K._sha(prefix) == pinned["prefix_sha256"] == live["prefix_sha256"]
''', '''    pinned = _load(os.path.join(FT.CORR_PKG_DIR, FT.CORR_MANIFEST_NAME))
    pinned2 = _load(os.path.join(FT.CORR2_PKG_DIR, FT.CORR_MANIFEST_NAME))
    live = FT.manifest(CORR2)
    prefix = FT.correction_prefix()
    assert pinned2["prefix_sha256"] == pinned["prefix_sha256"]        # the frozen round-two prefix is round one's, byte for byte
    block = "[FINAL DECISION RULES]\\n%s\\n\\n" % F._decision_rules_source().rstrip()
    shipped = K._read(os.path.join(FT.CORR2_PKG_DIR, FT.CORR_PREFIX_NAME))
    assert prefix == shipped.replace("[A4 CORRECTION TASK]\\n", block + "[A4 CORRECTION TASK]\\n", 1)   # the live one moved by exactly the owner's block (SEQ 1507)
    assert K._sha(prefix) == live["prefix_sha256"]
''', 1),
('''        assert text.startswith(prefix)
        body = json.loads(text[len(prefix):], object_pairs_hook=collections.OrderedDict)
        assert list(body) == list(FT.CORR_PAYLOAD_KEYS) and list(body)[-1] == "reviewer_findings"
        assert [dict(l) for l in body["leads"]] == [{''',
 '''        assert text.startswith(prefix)
        body = json.loads(text[len(prefix):], object_pairs_hook=collections.OrderedDict)
        assert list(body) == list(FT.CORR_PAYLOAD_KEYS) and list(body)[-1] == "reviewer_findings"
        assert [dict(l) for l in body["leads"]] == [{''', 1),
])
patch(H + "/test_a4_final_targeted_correction_1501.py", [
('''    assert live["prefix_sha256"] == manifest["prefix_sha256"]     # not one prompt byte moved
    assert [r["prompt_sha256"] for r in live["tasks"]] == [r["prompt_sha256"] for r in manifest["tasks"]]
''', '''    block = "[FINAL DECISION RULES]\\n%s\\n\\n" % F._decision_rules_source().rstrip()
    shipped = K._read(os.path.join(FT.CORR_PKG_DIR, FT.CORR_PREFIX_NAME))
    assert K._read(os.path.join(live_pkg, FT.CORR_PREFIX_NAME)) == shipped.replace("[A4 CORRECTION TASK]\\n", block + "[A4 CORRECTION TASK]\\n", 1)   # moved by exactly the owner's block (SEQ 1507)
    assert [r["payload_sha256"] for r in live["tasks"]] == [r["payload_sha256"] for r in manifest["tasks"]]   # not one data byte moved
''', 1),
])
print("patched")
