# ponytail: THE ONE bound review receipt of the third round (Codex SEQ 1507): the accepted key's remaining
# open issue copied VERBATIM by code, plus the reviewer's four findings in his own words, each naming the
# existing rules it applies. Written once; nothing here decides.
import collections, hashlib, io, json, sys
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, raw_transport as RT
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

shards, _raws, _origins = FT._lead(FT.CORR3_DOOR)  # the accepted key after run 1506, through the bindings
findings = collections.OrderedDict()
for sid, shard in shards.items():                    # every open issue the accepted key still carries, verbatim
    for x in shard["open_issues"]:
        findings.setdefault(sid, []).append(collections.OrderedDict(
            [("kind", "open_issue"), ("what", x["what"]), ("why", x["why"])]))

def reviewer(sid, text, rules):
    findings.setdefault(sid, []).append(collections.OrderedDict(
        [("kind", "reviewer_finding"), ("source", "Codex SEQ 1507"), ("text", text), ("rules", rules)]))

E = "0001041061-25-000109"
reviewer(E, "The active exact decision rule at decision_rules_1387.txt rule 5 says that when multiple same-kind menu "
            "tokens remain indistinguishable, the model uses one source-grounded off-menu value and tags ambiguous_menus; "
            "FINAL_DESIGN.md section 5.2/FS-18 also says an unsure producer coins new. The answer instead claims this "
            "case has no lawful fallback and drops both real facts.", ["decision rule 5", "Rule 7"])
reviewer(E, "The answer twice interprets the source dash as a rounded zero, contrary to Rule 5.4 and the prior reviewed "
            "ruling. A dash is not a stated digit. Do not preserve that claim in the key or sidecar.", ["Rule 5.4"])
reviewer(E, "The source safely states the quarterly -2 versus +1 comparison and separately states the YTD prior -2 and "
            "82 B/(W) while showing a dash for the current level. The model, not code, must settle the exact lawful "
            "fields under Rules 4-7, but it must not discard a supported fact merely because one numeric slot is "
            "unavailable, invent zero, invent dates, or choose either ambiguous existing menu identity.",
            ["Rule 4", "Rule 5", "Rule 6", "Rule 7"])
reviewer(E, "Its one open_issue is therefore not an authority conflict: the already-active rule supplies a lawful "
            "off-menu answer. Residual ambiguity belongs in each accepted fact's ambiguity_note; open_issues must be "
            "empty.", ["Rule 1.4", "decision rule 5"])

lead = FT._phase(FT.CORR2_DOOR)["binding"]
doc = collections.OrderedDict([
    ("schema", FT.REVIEW_SCHEMA), ("authority", "Codex SEQ 1507"),
    (FT._round(FT.CORR3_DOOR)["receipt_key"], collections.OrderedDict([
        ("binding_path", lead), ("binding_sha256", sha(lead)), ("run_dir", FT._closed_run(FT.CORR2_DOOR))])),
    ("findings", findings)])
OUT = FT.CORR3_REVIEW_RECEIPT
RT.write_new(OUT, json.dumps(doc, indent=1, ensure_ascii=False))
print("receipt", OUT, sha(OUT))
print("events with findings:", [(s[-6:], [f["kind"] for f in v]) for s, v in findings.items()])
print("population:", [e[-6:] for e in FT.correction_events(FT.CORR3_DOOR)])
