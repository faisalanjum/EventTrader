# ponytail: THE ONE bound review receipt of the third round (Codex SEQ 1507 + 1508): the accepted key's remaining
# open issue copied VERBATIM by code, the four already-reviewed findings copied EXACTLY from the 1507 receipt, and
# the reviewer's two new findings on the tag/note event in his own words. Written once; nothing here decides.
import collections, hashlib, io, json, sys
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, raw_transport as RT
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
OLD = S + "/a4_final_review_receipt_1507.json"
old = json.load(io.open(OLD, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
shards, _raws, _origins = FT._lead(FT.CORR3_DOOR)  # the accepted key after run 1506, through the bindings
findings = collections.OrderedDict()
for sid, shard in shards.items():                    # every open issue the accepted key still carries, verbatim
    for x in shard["open_issues"]:
        findings.setdefault(sid, []).append(collections.OrderedDict(
            [("kind", "open_issue"), ("what", x["what"]), ("why", x["why"])]))
def reviewer(sid, text, rules, source):
    findings.setdefault(sid, []).append(collections.OrderedDict(
        [("kind", "reviewer_finding"), ("source", source), ("text", text), ("rules", rules)]))
E1 = "0001041061-25-000109"
kept = [f for f in old["findings"][E1] if f["kind"] == "reviewer_finding"]; assert len(kept) == 4
for f in kept:                                       # retained exactly (SEQ 1508 item 3)
    reviewer(E1, f["text"], list(f["rules"]), f["source"])
E2 = "0001171843-26-001288"
assert shards[E2]["open_issues"] == []
reviewer(E2, "`portion_versus_whole` is wrong. The source defines net inventory as merchandise inventory less accounts "
             "payable. That is arithmetic netting of two balances, not OD-17's business-population qualifier or subset. "
             "The tag must not survive.", ["decision rule 10", "OD-17"], "Codex SEQ 1508")
reviewer(E2, "The ambiguity_note is also wrong. This same release explicitly says \"second quarter (12 weeks) ended "
             "February 14, 2026\" and labels the table \"2nd Quarter, FY2026\"; that full-event text directly governs the "
             "February 14 inventory instant under decision rule 6. Q2/FY2026 is supported, not genuinely uncertain.",
             ["decision rule 6"], "Codex SEQ 1508")
lead = FT._phase(FT.CORR2_DOOR)["binding"]
doc = collections.OrderedDict([
    ("schema", FT.REVIEW_SCHEMA), ("authority", "Codex SEQ 1507 + 1508"),
    ("supersedes", collections.OrderedDict([("path", OLD), ("sha256", sha(OLD))])),
    (FT._round(FT.CORR3_DOOR)["receipt_key"], collections.OrderedDict([
        ("binding_path", lead), ("binding_sha256", sha(lead)), ("run_dir", FT._closed_run(FT.CORR2_DOOR))])),
    ("findings", findings)])
OUT = FT.CORR3_REVIEW_RECEIPT
RT.write_new(OUT, json.dumps(doc, indent=1, ensure_ascii=False))
print("receipt", OUT, sha(OUT))
print("events with findings:", [(s[-6:], [f["kind"] for f in v]) for s, v in findings.items()])
print("population:", [e[-6:] for e in FT.correction_events(FT.CORR3_DOOR)])
