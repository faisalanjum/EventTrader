# ponytail: THE ONE bound review receipt (Codex SEQ 1501): the primary shards' own open issues copied
# VERBATIM by code, plus the reviewer's findings in his own words (SEQ 1501 items 1-2 and the three
# law statements), each naming the existing rules it points at. Written once; nothing here decides.
import collections, hashlib, io, json, sys
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, raw_transport as RT
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

shards, _raws = FT.primary_shards()
findings = collections.OrderedDict()
for sid, shard in shards.items():                    # every open issue, verbatim, in shard order
    for x in shard["open_issues"]:
        findings.setdefault(sid, []).append(collections.OrderedDict(
            [("kind", "open_issue"), ("what", x["what"]), ("why", x["why"])]))

def reviewer(sid, text, rules):
    findings.setdefault(sid, []).append(collections.OrderedDict(
        [("kind", "reviewer_finding"), ("source", "Codex SEQ 1501/1502"), ("text", text), ("rules", rules)]))

# SEQ 1501 item 1, verbatim
reviewer("0000027904-26-000022",
         "0000027904-26-000022 adds 2026-01-01 and 2026-03-31 as exact duration dates. The quote states "
         "“Three Months Ended March 31” and Q1/FY framing, but not both exact endpoints. Current Rule 6 says "
         "unstated fields stay null and a one-endpoint duration uses the matching fiscal framing, not an invented "
         "start date. Preserve the fact, values and fiscal framing; the current exact-date fields are not accepted.",
         ["Rule 6"])
# SEQ 1501 item 2, verbatim
reviewer("0001041061-25-000109",
         "0001041061-25-000109 accepts a slice after expressly finding that two menu tokens are indistinguishable, "
         "converts a source dash into numeric zero without a stated number, and adds a 2025-01-01 YTD start date not "
         "stated by the source. Rule 1.4 and Rule 7 require fail-closed handling when the slice cannot be resolved; "
         "Rule 5 requires a numeric slot’s number to be source-stated; Rule 6 forbids the invented duration "
         "endpoint. The current two accepted facts are not safe key truth.",
         ["Rule 1.4", "Rule 7", "Rule 5", "Rule 6"])
# SEQ 1502 item 2: only the applicable event-specific review context, verbatim from Codex
reviewer("0000006201-26-000031",
         "judge the frozen located items only; source-discovery completeness is separate; reconcile the "
         "duplicated underlying loss figure once.", ["Rule 1.5"])
reviewer("0000940944-26-000005",
         "distinct quarter and YTD facts are allowed; the contiguous tax qualifier remains one whole "
         "measurement entry.", ["Rule 6", "Rule 8"])
reviewer("0000940944-26-000009",
         "judge only the frozen quote; reconcile the overlapping rows; a combined cause with no separable "
         "source numbers may be excluded; never borrow Note 7 or other outside evidence.", ["Rule 1.4", "Rule 3.2"])
# 0000027904-26-000022 keeps the exact-date correction (SEQ 1501 item 1) already recorded above;
# 0001041061-25-000109 retains only the exact Habit issues already stated (SEQ 1501 item 2) recorded above.

doc = collections.OrderedDict([
    ("schema", FT.REVIEW_SCHEMA), ("authority", "Codex SEQ 1501"),
    ("primary_binding", collections.OrderedDict([
        ("binding_path", FT.BINDING), ("binding_sha256", sha(FT.BINDING)), ("run_dir", FT._closed_run())])),
    ("findings", findings)])
OUT = S + "/a4_final_review_receipt_1502.json"
RT.write_new(OUT, json.dumps(doc, indent=1, ensure_ascii=False))
print("receipt", OUT, sha(OUT))
print("events with findings:", [(s[-6:], len(v)) for s, v in findings.items()])
