S=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad; PY=/home/faisal/EventMarketDB/venv/bin/python3
sed -e 's#RUN = "/tmp/a4_hard_review_run_1495"#RUN = "/tmp/a4_final_targeted_run_1500"#' -e 's#hard_review_targeted_1493/hard_review.manifest.json#final_targeted_1499/final_targeted.manifest.json#' $S/evidence_1495.py > $S/evidence_1500.py
cat >> $S/evidence_1500.py <<'EOF'


def events():
    """Per event (mechanical parse of the proved shard text, never a judgment):
    rows, facts, abstentions, exclusions, open issues, leads agreeing/disagreeing."""
    out = []
    for p in sorted(glob.glob(RUN + "/raw/*.attempt1.proved.json")):
        d = parse(p); sid = d["source_id"]
        facts = sum(len(r["settled"]["facts"]) for r in d["rows"]); abst = sum(len(r["settled"]["abstentions"]) for r in d["rows"])
        excl = sum(1 for r in d["rows"] if r["final_outcome"] != "fact")
        agree = sum(1 for l in d["lead_reconciliation"] if l["agrees"] is True); dis = sum(1 for l in d["lead_reconciliation"] if l["agrees"] is False)
        out.append("   %s  rows %d  facts %d  abstentions %d  non-fact rows %d  open_issues %d  leads agree %d / disagree %d"
                   % (sid, len(d["rows"]), facts, abst, excl, len(d["open_issues"]), agree, dis))
    return "\n".join(out)


def run_ids():
    return "\n".join("   %s  %s" % (os.path.splitext(os.path.basename(s))[0], (lambda d: [r for r in d["workflowProgress"] if r.get("type") == "workflow_agent"][0]["label"])(J(s))) for s in J(RUN + "/receipt.json")["states"])


if __name__ == "__main__" and sys.argv[1] in ("events", "run_ids"):
    print(events() if sys.argv[1] == "events" else run_ids())
EOF
python3 - <<'EOF'
p="/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/evidence_1500.py"; s=open(p).read()
# the original dispatcher raises on unknown commands before the appended one runs; route the two new names first
s=s.replace('if __name__ == "__main__":\n    cmd = sys.argv[1]\n    if cmd == "trans":', 'if __name__ == "__main__" and sys.argv[1] not in ("events", "run_ids"):\n    cmd = sys.argv[1]\n    if cmd == "trans":')
# the hard-review pair table does not apply here
s=s.replace('    elif cmd == "rows": print(rows()[0])\n', '')
open(p,"w").write(s); print("evidence_1500.py ready")
EOF
for c in trans transn states serial tokens tokmin tokmax tools reads mid modelset completed agents events run_ids; do printf "%-10s " $c; $PY -B $S/evidence_1500.py $c 2>&1 | grep -v WARNING; done
