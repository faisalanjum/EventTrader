# -*- coding: utf-8 -*-
"""Preserve the complete raw outcome of the seg-5 run (Codex SEQ 1802).

Waits, read-only, until the runtime makes the run's evidence available, then
copies every transcript, agent, meta and journal file plus the official state
durably into unit_1802/capture BEFORE anything parses them. It counts starts,
returns, refusals, errors and missing rows separately, and never cancels,
retries or abandons the call.
"""
import collections, hashlib, io, json, os, shutil, sys, time
SID = "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
RID = "wf_feabb3a2-628"
P = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/%s" % SID)
D = os.path.join(P, "subagents", "workflows", RID)
STATE = os.path.join(P, "workflows", RID + ".json")
U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = U + "/capture"
EXPECT = 40
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def journal():
    recs = []
    if os.path.isfile(os.path.join(D, "journal.jsonl")):
        for line in io.open(os.path.join(D, "journal.jsonl"), encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    recs.append({"type": "unparsed"})
    return recs


def snapshot(tag):
    dest = os.path.join(OUT, tag)
    if os.path.isdir(D):
        shutil.copytree(D, os.path.join(dest, RID), dirs_exist_ok=True)
    if os.path.isfile(STATE):
        os.makedirs(dest, exist_ok=True)
        shutil.copyfile(STATE, os.path.join(dest, RID + ".json"))
    return dest


def main():
    deadline = time.time() + 3300
    while time.time() < deadline:
        recs = journal()
        results = [r for r in recs if r.get("type") == "result"]
        if os.path.isfile(STATE) and len(results) >= EXPECT:
            break
        time.sleep(10)
    dest = snapshot("after")
    recs = journal()
    starts = [r for r in recs if r.get("type") == "started"]
    results = [r for r in recs if r.get("type") == "result"]
    files = sorted(os.listdir(D)) if os.path.isdir(D) else []
    transcripts = [f for f in files if f.startswith("agent-") and f.endswith(".jsonl")]
    empty = [r.get("agentId") for r in results if not (r.get("result") or "").strip()]
    st = json.load(io.open(STATE, encoding="utf-8")) if os.path.isfile(STATE) else None
    rows = [x for x in (st or {}).get("workflowProgress", [])
            if x.get("type") == "workflow_agent" and x.get("agentId")]
    doc = collections.OrderedDict([
        ("run_id", RID), ("task_id", "wxrar4p8v"),
        ("captured_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("official_state_present", os.path.isfile(STATE)),
        ("official_state_sha256", fsha(STATE) if os.path.isfile(STATE) else None),
        ("official_state_bytes", os.path.getsize(STATE) if os.path.isfile(STATE) else None),
        ("state_status", (st or {}).get("status")),
        ("counts", collections.OrderedDict([
            ("expected_new_starts", EXPECT),
            ("journal_started", len(starts)),
            ("journal_results", len(results)),
            ("distinct_started_agents", len({r.get("agentId") for r in starts})),
            ("distinct_result_agents", len({r.get("agentId") for r in results})),
            ("started_without_result",
             len({r.get("agentId") for r in starts} - {r.get("agentId") for r in results})),
            ("empty_results", len(empty)),
            ("official_agent_rows", len(rows)),
            ("rows_in_error", len([x for x in rows if x.get("state") == "error"])),
            ("rows_done", len([x for x in rows if x.get("state") == "done"])),
            ("rows_cached_claim", len([x for x in rows if x.get("cached")])),
            ("transcript_files", len(transcripts)),
            ("all_files_in_run_dir", len(files))])),
        ("started_without_result_ids",
         sorted({r.get("agentId") for r in starts} - {r.get("agentId") for r in results})),
        ("empty_result_ids", empty),
        ("files", collections.OrderedDict(
            (f, {"bytes": os.path.getsize(os.path.join(D, f)),
                 "sha256": fsha(os.path.join(D, f))}) for f in files)),
        ("preserved_under", dest),
        ("nothing_parsed_by_an_owner_yet", True)])
    io.open(U + "/capture/OUTCOME_1802.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    c = doc["counts"]
    print("  official state : %s  status %s" % (doc["official_state_present"], doc["state_status"]))
    print("  started %d | results %d | started-without-result %d | empty %d"
          % (c["journal_started"], c["journal_results"], c["started_without_result"],
             c["empty_results"]))
    print("  official rows %d (done %d, error %d, cached-claim %d) | transcripts %d"
          % (c["official_agent_rows"], c["rows_done"], c["rows_in_error"],
             c["rows_cached_claim"], c["transcript_files"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
