import io, sys
S = sys.argv[1]
s = io.open(S + "/budget_receipt_1505.py", encoding="utf-8").read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]; s = s.replace(old, new)
rep('(Codex SEQ 1505 item 5), the 1501 receipt\'s\n# shape with the completed first correction moved into completed_before and the second correction\n# added as a stage.',
    '(Codex SEQ 1507 item 7), the 1505 receipt\'s\n# shape with the completed second correction moved into completed_before and the third correction\n# added as a stage.')
rep('OUT = "/tmp/a7_budget_receipt_1505.json"', 'OUT = "/tmp/a7_budget_receipt_1507.json"')
rep('''    collections.OrderedDict([("stage", "final_correction_2"), ("owner", "build_kfields_final_targeted.correction_events(CORR2_DOOR): exactly the events whose accepted shard still carries an open issue x F.MAX_ATTEMPTS"),
        ("events", len(EV2)), ("targets", sum(len(t["rows"]) for t in FT.correction_tasks(FT.CORR2_DOOR))), ("max_attempts", F.MAX_ATTEMPTS),
        ("review_receipt", FT.CORR2_REVIEW_RECEIPT), ("review_receipt_sha256", sha(FT.CORR2_REVIEW_RECEIPT)),
        ("shape", len(EV2)), ("min", len(EV2)), ("max", len(EV2) * F.MAX_ATTEMPTS)]),''',
    '''    collections.OrderedDict([("stage", "final_correction_2"), ("owner", "a6_launch_freeze.ledger rows final_targeted_correction_2_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_correction_2"))), ("binding_path", CB2), ("binding_sha256", sha(CB2)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "final_correction_3"), ("owner", "build_kfields_final_targeted.correction_events(CORR3_DOOR): exactly the events whose accepted shard still carries an open issue after run 1506 x F.MAX_ATTEMPTS"),
        ("events", len(EV3)), ("targets", sum(len(t["rows"]) for t in FT.correction_tasks(FT.CORR3_DOOR))), ("max_attempts", F.MAX_ATTEMPTS),
        ("review_receipt", FT.CORR3_REVIEW_RECEIPT), ("review_receipt_sha256", sha(FT.CORR3_REVIEW_RECEIPT)),
        ("shape", len(EV3)), ("min", len(EV3)), ("max", len(EV3) * F.MAX_ATTEMPTS)]),''')
rep('''CB = FT._phase(FT.CORR_DOOR)["binding"]
EV2 = FT.correction_events(FT.CORR2_DOOR)
''', '''CB = FT._phase(FT.CORR_DOOR)["binding"]; CB2 = FT._phase(FT.CORR2_DOOR)["binding"]
EV3 = FT.correction_events(FT.CORR3_DOOR)
''')
rep('''("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_correction"))), ("binding_path", CB), ("binding_sha256", sha(CB)),''',
    '''("actual", sum(r["calls"] for r in rows if r["stage"] == "final_targeted_correction_primary" or r["stage"] == "final_targeted_correction_retry")), ("binding_path", CB), ("binding_sha256", sha(CB)),''')
rep('adj = stages[4]; sig = stages[5]', 'adj = stages[5]; sig = stages[6]')
rep('("schema", "a7_call_budget_receipt/1505")', '("schema", "a7_call_budget_receipt/1507")')
io.open(S + "/budget_receipt_1507.py", "w", encoding="utf-8").write(s)
b = io.open(S + "/build_corr2_1505.py", encoding="utf-8").read()
b = b.replace("D = FT.CORR2_DOOR", "D = FT.CORR3_DOOR").replace("scratch_corr2_build_", "scratch_corr3_build_").replace("FT.CORR2_PKG_DIR", "FT.CORR3_PKG_DIR").replace("build the second correction package", "build the third correction package")
assert "CORR2" not in b, [l for l in b.splitlines() if "CORR2" in l]
io.open(S + "/build_corr3_1507.py", "w", encoding="utf-8").write(b); print("receipt/budget/build scripts written")
