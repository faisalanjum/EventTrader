import io, sys
p = sys.argv[1] + "/build_kfields_final_targeted.py"; s = io.open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]; s = s.replace(old, new)
rep('''# Codex SEQ 1507: the third round over exactly the events whose accepted shard
# still carries an open issue after run 1506, with the locked A4 owner's exact
# final-decision block served in the common correction prefix.
CORR3_DOOR = "a4_final_targeted_correction_3"
CORR3_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr3_1507")
CORR3_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1507.json"
CORR3_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1507.json")''',
    '''# Codex SEQ 1507/1508: the third round over exactly the events the bound
# review receipt names (the one still carrying an open issue and the one whose
# accepted tag and note the reviewer proved wrong), with the locked A4 owner's
# exact final-decision block served in the common correction prefix.
CORR3_DOOR = "a4_final_targeted_correction_3"
CORR3_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr3_1508")
CORR3_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1508.json"
CORR3_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1508.json")''')
rep('''            "launcher_name": CORR_LAUNCHER_NAME + "-3", "authority": "Codex SEQ 1507",
            "origin": "final_targeted_correction_3", "receipt_key": "lead_binding",
            "population": _open_issue_population}}[door]''',
    '''            "launcher_name": CORR_LAUNCHER_NAME + "-3", "authority": "Codex SEQ 1508",
            "origin": "final_targeted_correction_3", "receipt_key": "lead_binding",
            "population": _review_population}}[door]''')
io.open(p, "w", encoding="utf-8").write(s); print("FT patched for SEQ 1508")
