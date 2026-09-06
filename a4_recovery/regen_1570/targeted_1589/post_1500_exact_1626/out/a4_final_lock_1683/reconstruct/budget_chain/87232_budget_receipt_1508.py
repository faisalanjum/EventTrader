import io, sys
S = sys.argv[1]; p = S + "/budget_receipt_1508.py"; s = io.open(p, encoding="utf-8").read()
old = '("owner", "build_kfields_final_targeted.correction_events(CORR3_DOOR): exactly the events whose accepted shard still carries an open issue named by the bound review receipt x F.MAX_ATTEMPTS")'
new = '("owner", "build_kfields_final_targeted.correction_events(CORR3_DOOR): exactly the events with findings in the bound review receipt x F.MAX_ATTEMPTS")'
assert s.count(old) == 1; s = s.replace(old, new)
s = s.replace("(Codex SEQ 1508 item 6)", "(Codex SEQ 1508 item 6, owner sentence corrected per SEQ 1509 item 1)")
io.open(p, "w", encoding="utf-8").write(s); print("budget generator corrected")
