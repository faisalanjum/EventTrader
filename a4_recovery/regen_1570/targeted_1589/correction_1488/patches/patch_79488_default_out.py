import io
S="/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
p = S+"/lock/build_final_lock_v2.py"; t = io.open(p, encoding="utf-8").read()
old = 'DEFAULT_OUT = os.path.join(LOCK_DIR, "candidate_v2_1487")'
assert t.count(old) == 1
t = t.replace(old, '#: candidate_v2_1487 is history (unbound receipt); 1488 carries the file-hash binding\nDEFAULT_OUT = os.path.join(LOCK_DIR, "candidate_v2_1488")')
io.open(p, "w", encoding="utf-8").write(t); print("L2 DEFAULT_OUT -> candidate_v2_1488")
p = S+"/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/build_kfields_key_targeted.py"; t = io.open(p, encoding="utf-8").read()
def rep(old, new):
    global t
    assert t.count(old) == 1, old[:60]; t = t.replace(old, new)
rep('''#: the current call-budget receipt this stage's budget is bound to, by hash
BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1488.json"''',
'''#: the current call-budget receipt this stage's budget is bound to, by hash
BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1488.json"
#: the correction receipt that derived the corrected inventory from the
#: reviewed source receipt; it carries that receipt's file hash and digest
CORRECTION_RECEIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(K._X))))), "lock", "candidate_v2_1488",
    "correction_receipt.json")''')
rep('''def _correction_block(corrected_path):
    return collections.OrderedDict([
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("corrected_inventory_path", os.path.abspath(corrected_path)),
        ("corrected_inventory_sha256", INV.sha_file(corrected_path)),''',
'''def _correction_block(corrected_path):
    """The correction, bound end to end: frozen inventory -> reviewed source
    receipt (file hash + digest, from the correction receipt that applied
    it) -> corrected inventory -> targets. A correction receipt that did not
    derive THIS corrected inventory refuses (Codex SEQ 1488 item 4)."""
    cr = _load(CORRECTION_RECEIPT)
    if cr.get("versioned_inventory_path") != os.path.abspath(corrected_path) \\
            or INV.sha_file(cr["versioned_inventory_path"]) != \\
            INV.sha_file(corrected_path):
        raise ValueError("the correction receipt %s did not derive %s"
                         % (CORRECTION_RECEIPT, corrected_path))
    return collections.OrderedDict([
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("correction_receipt_path", CORRECTION_RECEIPT),
        ("correction_receipt_sha256", INV.sha_file(CORRECTION_RECEIPT)),
        ("source_receipt", collections.OrderedDict(
            (k, cr["source_receipt"][k])
            for k in ("path", "file_sha256", "receipt_sha256"))),
        ("corrected_inventory_path", os.path.abspath(corrected_path)),
        ("corrected_inventory_sha256", INV.sha_file(corrected_path)),''')
io.open(p, "w", encoding="utf-8").write(t); print("T correction block bound to the correction receipt")
