import io
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
s = io.open(S + "/budget_receipt_1501.py", encoding="utf-8").read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]; s = s.replace(old, new)
rep('# ponytail: ONE call-budget receipt from LIVE owners (Codex SEQ 1496 item 5), the 1493 receipt\'s\n# shape with the completed hard review moved into completed_before and the successor adjudication\n# added as a stage.',
    '# ponytail: ONE call-budget receipt from LIVE owners (Codex SEQ 1505 item 5), the 1501 receipt\'s\n# shape with the completed first correction moved into completed_before and the second correction\n# added as a stage.')
rep('OUT = "/tmp/a7_budget_receipt_1501.json"', 'OUT = "/tmp/a7_budget_receipt_1505.json"')
rep('''    collections.OrderedDict([("stage", "final_correction"), ("owner", "build_kfields_final_targeted.correction_events: every primary event whose bound review entry is nonempty x F.MAX_ATTEMPTS"),
        ("events", len(FT.correction_events())), ("targets", sum(len(t["rows"]) for t in FT.correction_tasks())), ("max_attempts", F.MAX_ATTEMPTS),
        ("review_receipt", FT.REVIEW_RECEIPT), ("review_receipt_sha256", sha(FT.REVIEW_RECEIPT)),
        ("shape", len(FT.correction_events())), ("min", len(FT.correction_events())), ("max", len(FT.correction_events()) * F.MAX_ATTEMPTS)]),''',
    '''    collections.OrderedDict([("stage", "final_correction"), ("owner", "a6_launch_freeze.ledger rows final_targeted_correction_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_correction"))), ("binding_path", CB), ("binding_sha256", sha(CB)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "final_correction_2"), ("owner", "build_kfields_final_targeted.correction_events(CORR2_DOOR): exactly the events whose accepted shard still carries an open issue x F.MAX_ATTEMPTS"),
        ("events", len(EV2)), ("targets", sum(len(t["rows"]) for t in FT.correction_tasks(FT.CORR2_DOOR))), ("max_attempts", F.MAX_ATTEMPTS),
        ("review_receipt", FT.CORR2_REVIEW_RECEIPT), ("review_receipt_sha256", sha(FT.CORR2_REVIEW_RECEIPT)),
        ("shape", len(EV2)), ("min", len(EV2)), ("max", len(EV2) * F.MAX_ATTEMPTS)]),''')
rep('''completed, rows = A6.ledger()
''', '''completed, rows = A6.ledger()
CB = FT._phase(FT.CORR_DOOR)["binding"]
EV2 = FT.correction_events(FT.CORR2_DOOR)
''')
rep('''        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted"))), ("binding_path", FT.BINDING), ("binding_sha256", sha(FT.BINDING)),''',
    '''        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_") and not r["stage"].startswith("final_targeted_correction"))), ("binding_path", FT.BINDING), ("binding_sha256", sha(FT.BINDING)),''')
rep('adj = stages[3]; sig = stages[4]', 'adj = stages[4]; sig = stages[5]')
rep('("schema", "a7_call_budget_receipt/1501")', '("schema", "a7_call_budget_receipt/1505")')
io.open(S + "/budget_receipt_1505.py", "w", encoding="utf-8").write(s); print("budget generator written")
