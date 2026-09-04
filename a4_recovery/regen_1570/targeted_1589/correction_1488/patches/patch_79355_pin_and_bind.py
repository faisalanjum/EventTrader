import io, hashlib
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
p = S + "/lock/build_final_lock_v2.py"; t = io.open(p, encoding="utf-8").read()
def rep(old, new):
    global t
    assert t.count(old) == 1, old[:70]; t = t.replace(old, new)
pin = hashlib.sha256(open("/tmp/a7_source_locator_audit_1486.json", "rb").read()).hexdigest()
rep('''RECEIPT_PATH = "/tmp/a7_source_locator_audit_1486.json"''',
'''RECEIPT_PATH = "/tmp/a7_source_locator_audit_1486.json"
#: THE reviewed receipt, pinned by its exact FILE bytes (Codex SEQ 1488 item
#: 4); the internal digest is recomputed, never trusted from the file.
SOURCE_RECEIPT_SHA256 = "%s"
SOURCE_RECEIPT_SCHEMA = "a7_source_locator_class_audit/1486"''' % pin)
rep('''def _order():''',
'''def load_receipt(path, expected_file_sha256=SOURCE_RECEIPT_SHA256):
    """-> (doc, file_sha256, receipt_sha256). The reviewed receipt, bound by
    its exact file bytes, its recomputed canonical digest, its schema and the
    full 196-row packet identity against the frozen inventory. Any mismatch
    refuses before a single change is derived."""
    raw = io.open(path, "rb").read()
    file_sha = hashlib.sha256(raw).hexdigest()
    if file_sha != expected_file_sha256:
        raise ValueError("the source receipt's file sha256 is %s, not the "
                         "reviewed %s" % (file_sha, expected_file_sha256))
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("schema") != SOURCE_RECEIPT_SCHEMA:
        raise ValueError("the source receipt schema is %r" % doc.get("schema"))
    body = {k: v for k, v in doc.items() if k != "receipt_sha256"}
    digest = hashlib.sha256(json.dumps(
        body, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()
    if digest != doc.get("receipt_sha256"):
        raise ValueError("the source receipt's recomputed digest %s is not "
                         "its recorded %s" % (digest, doc.get("receipt_sha256")))
    frozen = json.load(io.open(INV.INV, encoding="utf-8"))["records"]
    rows = doc.get("rows") or []
    if len(rows) != len(frozen):
        raise ValueError("the source receipt carries %d rows for %d frozen "
                         "records" % (len(rows), len(frozen)))
    for n, (row, rec) in enumerate(zip(rows, frozen)):
        want = "%s#%03d" % (rec["source_id"], n)
        if row.get("packet_id") != want or row.get("source_id") != rec["source_id"]:
            raise ValueError("row %d: packet identity %r/%r is not the frozen "
                             "%r" % (n, row.get("packet_id"),
                                     row.get("source_id"), want))
    return doc, file_sha, digest


def _order():''')
rep('''def materialize(receipt):
    """Derive every output text. Writes nothing."""
    frozen = json.load(io.open(INV.INV, encoding="utf-8"))''',
'''def materialize(receipt_path=RECEIPT_PATH):
    """Derive every output text from the BOUND receipt. Writes nothing."""
    receipt, file_sha, digest = load_receipt(receipt_path)
    frozen = json.load(io.open(INV.INV, encoding="utf-8"))''')
rep('''        ("source_correction", collections.OrderedDict([
            ("receipt_sha256", receipt["receipt_sha256"]),
            ("changes", changes)])),''',
'''        ("source_correction", collections.OrderedDict([
            ("receipt_file_sha256", file_sha),
            ("receipt_sha256", digest),
            ("changes", changes)])),''')
rep('''        ("source_receipt", collections.OrderedDict([
            ("path", RECEIPT_PATH), ("receipt_sha256", receipt["receipt_sha256"])])),''',
'''        ("source_receipt", collections.OrderedDict([
            ("path", receipt_path), ("file_sha256", file_sha),
            ("receipt_sha256", digest)])),''')
rep('''def _write_new(path, text):
    """Write-once: an existing identical file is fine; a different one refuses."""
    if os.path.exists(path):
        if io.open(path, encoding="utf-8").read() == text:
            return
        raise ValueError("%s exists with different bytes; never overwritten"
                         % path)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def build(out_dir, receipt, versioned_path=None):
    """Materialize into `out_dir` and publish the versioned inventory beside
    the frozen one. Refuses with a written reason before any inventory exists."""
    out = materialize(receipt)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    if out["problems"]:
        io.open(os.path.join(out_dir, "refusal.json"), "w",
                encoding="utf-8").write(json.dumps(
                    {"problems": out["problems"]}, indent=1))
        raise ValueError("refused: %s" % out["problems"][:3])
    for name, key in (("final_inventory.json", "inventory_text"),
                      ("adjudication_sidecar.json", "sidecar_text"),
                      ("validator_receipt.json", "receipt_text"),
                      ("correction_receipt.json", "correction_text")):
        _write_new(os.path.join(out_dir, name), out[key])
    if versioned_path is not False:
        _write_new(versioned_path or VERSIONED_INVENTORY, out["inventory_text"])''',
'''def _already_published(path, text):
    """An existing artifact may only be the SAME bytes; different bytes
    refuse. Nothing is ever overwritten."""
    if not os.path.exists(path):
        return False
    if io.open(path, encoding="utf-8").read() != text:
        raise ValueError("%s exists with different bytes; never overwritten"
                         % path)
    return True


def build(out_dir, receipt_path=RECEIPT_PATH, versioned_path=None):
    """Materialize into `out_dir` and publish the versioned inventory beside
    the frozen one, every artifact through the transport's write-once owner.
    Refuses with a written reason before any inventory exists."""
    out = materialize(receipt_path)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    if out["problems"]:
        RT.write_new(os.path.join(out_dir, "refusal.json"), json.dumps(
            {"problems": out["problems"]}, indent=1))
        raise ValueError("refused: %s" % out["problems"][:3])
    for name, key in (("final_inventory.json", "inventory_text"),
                      ("adjudication_sidecar.json", "sidecar_text"),
                      ("validator_receipt.json", "receipt_text"),
                      ("correction_receipt.json", "correction_text")):
        if not _already_published(os.path.join(out_dir, name), out[key]):
            RT.write_new(os.path.join(out_dir, name), out[key])
    if versioned_path is not False:
        target = versioned_path or VERSIONED_INVENTORY
        if not _already_published(target, out["inventory_text"]):
            RT.write_new(target, out["inventory_text"])''')
rep('''if __name__ == "__main__":
    receipt = json.load(io.open(RECEIPT_PATH, encoding="utf-8"))
    got = build(DEFAULT_OUT, receipt)''',
'''if __name__ == "__main__":
    got = build(DEFAULT_OUT, RECEIPT_PATH)''')
io.open(p, "w", encoding="utf-8").write(t); print("build_final_lock_v2.py patched; pin", pin[:16])

# ---- the 1487 test file: the API moved (receipt path, one door)
p = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/test_a7_source_correction_1487.py"
t = io.open(p, encoding="utf-8").read()
def rep2(old, new):
    global t
    assert t.count(old) == 1, old[:70]; t = t.replace(old, new)
rep2('''    out = L2.materialize(receipt)
    assert out["problems"] == []''', '''    out = L2.materialize(RECEIPT)
    assert out["problems"] == []''')
rep2('''    a = L2.build(str(tmp_path / "one"), receipt)
    b = L2.build(str(tmp_path / "two"), receipt)''', '''    a = L2.build(str(tmp_path / "one"), RECEIPT, versioned_path=False)
    b = L2.build(str(tmp_path / "two"), RECEIPT, versioned_path=False)''')
# the two lifecycle tests of 1487 are superseded by the 1488 file
start = t.index("@_needs_v2\ndef test_prepare_run_writes_a_write_once_receipt_naming_exactly_the_targets(")
end = t.index("def test_the_targeted_builder_cannot_see_the_key():")
t = t[:start] + "# the receipt/lifecycle proofs moved to test_a7_source_correction_1488.py,\n# where the ONE shared lifecycle serves the targeted package (Codex SEQ 1488).\n\n\n" + t[end:]
rep2('''    doc = T.build_targeted(str(tmp_path / "pkg"), V2)
    frozen_doc = _load(FROZEN_PKG)''', '''    doc = T.build_targeted(str(tmp_path / "pkg"), V2)
    frozen_doc = _load(FROZEN_PKG)
    assert doc["budget"]["before"] != 3990''')
io.open(p, "w", encoding="utf-8").write(t); print("1487 tests updated")

# ---- budget receipt v1488 from the latest accepted artifacts
p = S + "/budget_receipt_1487.py"; t = io.open(p, encoding="utf-8").read()
t = t.replace('OUT = "/tmp/a7_budget_receipt_1487.json"', 'OUT = "/tmp/a7_budget_receipt_1488.json"')
t = t.replace('G23 = "/tmp/a7_g23_candidate/a7_g23_candidate.json"', 'G3 = "/tmp/a7_g3_candidate/a7_g1_candidate.json"     # latest accepted G3: 357 questions, 46 batches, 92 calls\nG2 = "/tmp/a7_g2_candidate/a7_g1_candidate.json"     # latest accepted G2: 140 questions, 17 batches, 34 calls')
t = t.replace('g23 = json.load(io.open(G23, encoding="utf-8"))', 'g2c = json.load(io.open(G2, encoding="utf-8")); g3c = json.load(io.open(G3, encoding="utf-8"))')
t = t.replace('g2_shape = g23["launchers"]["count"]              # 17 batches x 2 lanes, zero-call frozen\ng3_shape = g23["g3"]["batches"] * g23["launchers"]["lanes_per_batch"]', 'g2_shape = g2c["launchers"]["count"]\ng3_shape = g3c["launchers"]["count"]')
t = t.replace('''        ("primaries", len(targets)), ("max_attempts", K.MAX_ATTEMPTS),
        ("min", len(targets)), ("max", len(targets) * K.MAX_ATTEMPTS)]),''', '''        ("primaries", len(targets)), ("max_attempts", K.MAX_ATTEMPTS),
        ("shape", len(targets)), ("min", len(targets)), ("max", len(targets) * K.MAX_ATTEMPTS)]),''')
t = t.replace('''        ("min", 0), ("max", len(targets) * len(HR.BLINDS) * HR.MAX_ATTEMPTS)]),''', '''        ("shape", 0), ("min", 0), ("max", len(targets) * len(HR.BLINDS) * HR.MAX_ATTEMPTS)]),''')
t = t.replace('''        ("primaries", 1), ("max_attempts", F.MAX_ATTEMPTS), ("min", 1), ("max", F.MAX_ATTEMPTS)]),''', '''        ("primaries", 1), ("max_attempts", F.MAX_ATTEMPTS), ("shape", 1), ("min", 1), ("max", F.MAX_ATTEMPTS)]),''')
t = t.replace('''        ("min", lim["primary_calls"]), ("max", lim["all_in_max"])]),''', '''        ("shape", lim["primary_calls"]), ("min", lim["primary_calls"]), ("max", lim["all_in_max"])]),''')
t = t.replace('''        ("shape_from_frozen_completion", g1_lanes_shape), ("shape_artifact", G1C), ("shape_artifact_sha256", sha(G1C)),
        ("min", 0), ("max", legs * events * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),''', '''        ("shape", g1_lanes_shape), ("shape_artifact", G1C), ("shape_artifact_sha256", sha(G1C)),
        ("min", 0), ("max", legs * events * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),''')
t = t.replace('''        ("shape_from_frozen_candidate", g2_shape), ("shape_artifact_sha256", sha(G23)),
        ("min", 0), ("max", -(-ident["accepted_rows"] // GB.MAX_ITEMS_PER_CALL) * legs * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),''', '''        ("shape", g2_shape), ("shape_artifact", G2), ("shape_artifact_sha256", sha(G2)),
        ("min", 0), ("max", -(-ident["accepted_rows"] // GB.MAX_ITEMS_PER_CALL) * legs * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),''')
t = t.replace('''        ("shape_from_frozen_candidate", g3_shape), ("unroutable_event_legs_in_that_candidate", g23["g3"]["unroutable_event_legs"]),
        ("shape_artifact_sha256", sha(G23)),
        ("min", 0), ("max", None), ("max_note", "bounded only by the produced count, which exists after the producer run; the lawful cap is the remaining headroom (a7_g23_run: the retry cap is headroom, not a per-row reservation)")]),''', '''        ("shape", g3_shape), ("questions", g3c["questions"]), ("batches", g3c["batching"]["batches"]),
        ("shape_artifact", G3), ("shape_artifact_sha256", sha(G3)),
        ("min", 0), ("max", None), ("max_note", "bounded only by the produced count, which exists after the producer run; the lawful cap is the remaining headroom (a7_g23_run: the retry cap is headroom, not a per-row reservation)")]),''')
t = t.replace('''min_total = completed + sum(s["min"] for s in stages)
max_known = completed + sum(s["max"] for s in stages if s["max"] is not None)
expected_shape = completed + len(targets) + 1 + lim["primary_calls"] + (g1_lanes_shape or 0) + g2_shape + g3_shape''', '''min_total = completed + sum(s["min"] for s in stages)
max_known = completed + sum(s["max"] for s in stages if s["max"] is not None)
expected_shape = completed + sum(s["shape"] for s in stages)''')
t = t.replace('''    ("schema", "a7_call_budget_receipt/1487"),''', '''    ("schema", "a7_call_budget_receipt/1488"),''')
t = t.replace('''    ("expected_shape_total", expected_shape), ("expected_shape_note", "primaries at the frozen zero-call shapes, no retries, no hard-review task; G3 shape 0 with 29 unroutable event-legs in that candidate"),
    ("maximum_total", max_known), ("maximum_note", "sum of every derivable structural maximum; G3's maximum is not derivable before the producer run"),
    ("maximum_fits_ceiling", max_known <= ceiling),''', '''    ("expected_shape_total", expected_shape), ("expected_shape_note", "the provisional no-retry shape: primaries at the latest accepted zero-call artifacts, no retries, no hard-review task; every stage population is re-derived by its owner after key settlement, the producer run and G1"),
    ("headroom_at_shape", ceiling - expected_shape),
    ("known_maximum_subtotal", max_known), ("known_maximum_note", "the sum of every DERIVABLE structural maximum; it is not an absolute maximum"),
    ("absolute_maximum", None), ("absolute_maximum_note", "unknown before the producer run: G3's maximum depends on the produced count"),
    ("known_maximum_fits_ceiling", max_known <= ceiling),''')
t = t.replace('''print(json.dumps({k: doc[k] for k in ("completed_before", "ceiling", "minimum_total", "expected_shape_total", "maximum_total", "maximum_fits_ceiling")}))''', '''print(json.dumps({k: doc[k] for k in ("completed_before", "ceiling", "minimum_total", "expected_shape_total", "headroom_at_shape", "known_maximum_subtotal", "known_maximum_fits_ceiling", "absolute_maximum")}))''')
io.open(S + "/budget_receipt_1488.py", "w", encoding="utf-8").write(t); print("budget_receipt_1488.py written")
