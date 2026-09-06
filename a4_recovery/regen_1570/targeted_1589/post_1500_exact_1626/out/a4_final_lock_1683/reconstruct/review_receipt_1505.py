# ponytail: THE ONE bound review receipt of the second round (Codex SEQ 1505): the accepted
# correction shards' own open issues copied VERBATIM by code, plus the reviewer's two rulings in
# his own words, each naming the existing rules it applies. Written once; nothing here decides.
import collections, hashlib, io, json, sys
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, raw_transport as RT
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

shards, _raws = FT.bound_shards(FT.CORR_DOOR)
findings = collections.OrderedDict()
for sid, shard in shards.items():                    # every open issue the accepted key still carries, verbatim
    for x in shard["open_issues"]:
        findings.setdefault(sid, []).append(collections.OrderedDict(
            [("kind", "open_issue"), ("what", x["what"]), ("why", x["why"])]))

def reviewer(sid, text, rules):
    findings.setdefault(sid, []).append(collections.OrderedDict(
        [("kind", "reviewer_finding"), ("source", "Codex SEQ 1505"), ("text", text), ("rules", rules)]))

# SEQ 1505, verbatim; the rules are the ones the same ruling named in SEQ 1502 for this event
reviewer("0000940944-26-000009",
         "Reject 0000940944-26-000009 as closure-grade, although its two exclusions are safe. Both rows already "
         "produce zero facts, so their overlap cannot duplicate an accepted fact. Note 7 is outside the frozen "
         "evidence and cannot be borrowed. Neither point changes the frozen answer: both rows remain exclusions "
         "with zero facts and open_issues must be empty.",
         ["Rule 1.4", "Rule 3.2"])
# SEQ 1505, verbatim; the rules it names
reviewer("0001041061-25-000109",
         "Reject both accepted facts in 0001041061-25-000109. The reply itself says the exact segment identity "
         "remains unresolved and the dash is not a stated digit, yet it guessed a menu token by naming symmetry "
         "and converted the dash to zero. Existing Rules 1.4, 5, and 7 resolve this fail-closed: do not choose "
         "either token, do not turn the dash into a number, do not invent dates, and abstain/exclude the row "
         "with zero facts and no remaining open issue.",
         ["Rule 1.4", "Rule 5", "Rule 7"])

lead = FT._phase(FT.CORR_DOOR)["binding"]
doc = collections.OrderedDict([
    ("schema", FT.REVIEW_SCHEMA), ("authority", "Codex SEQ 1505"),
    (FT._ROUNDS[FT.CORR2_DOOR]["receipt_key"], collections.OrderedDict([
        ("binding_path", lead), ("binding_sha256", sha(lead)), ("run_dir", FT._closed_run(FT.CORR_DOOR))])),
    ("findings", findings)])
OUT = FT.CORR2_REVIEW_RECEIPT
RT.write_new(OUT, json.dumps(doc, indent=1, ensure_ascii=False))
print("receipt", OUT, sha(OUT))
print("events with findings:", [(s[-6:], [f["kind"] for f in v]) for s, v in findings.items()])
print("population:", [e[-6:] for e in FT.correction_events(FT.CORR2_DOOR)])
