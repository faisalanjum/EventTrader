"""The exact saved A4 model-result corpus, frozen from the official session store (Codex SEQ 1578).

Every workflow state whose scriptPath lies below one of the ten historical A4 run roots, with its one
workflow-agent transcript and its workflow journal, copied byte-exact into inputs/a4_official/<wf>/ and
listed in inputs/A4_OFFICIAL_RESULTS.tsv (phase = run root, attempt, label, wf, the four hashes, the
script path; rows sorted). Selection is by scriptPath alone, never by timestamp or command order. The
row count, the census bytes and hash and the four aggregate byte totals are pinned; every state must be
completed with no tool call and exactly one done workflow-agent row on the pinned model. `verify`
re-derives everything from candidate bytes only and never reads the store. Answer meaning is not read.

    official_results.py copy     copy the corpus from the official store, write the census, verify
    official_results.py verify   re-derive from the candidate and compare
"""
import glob
import hashlib
import io
import json
import os
import re
import shutil
import sys

R = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(R, "inputs", "a4_official")
CENSUS = os.path.join(R, "inputs", "A4_OFFICIAL_RESULTS.tsv")
OFFICIAL = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
RUNS = (
    "kf-a4-phase1-196-20260821T163310Z", "kf-a4-hardreview-70-20260822T015053Z", "kf-a4-hrfix-4-20260822T050131Z",
    "kf-a4-final-36-20260822T162832Z", "kf-a4-corr-32-20260823T030745Z", "kf-a4-decision-36-20260823T075249Z",
    "kf-a4-v4corr-21-20260823T122628Z", "kf-a4-v5corr-4-20260823T164833Z", "kf-a4-v6corr-3-20260823T171830Z",
    "kf-a4-signer-20260823T180519Z")
MODEL = "claude-sonnet-5"
HEADER = "phase\tattempt\tlabel\twf\tstate_sha256\tagent_sha256\tjournal_sha256\tscript_sha256\tscript_path\n"
FIELDS = ("phase", "attempt", "label", "wf", "state_sha256", "agent_sha256", "journal_sha256", "script_sha256", "script_path")
PINS = {"rows": 456, "census_bytes": 252444, "census_sha256": "e03e5a30409db9ce36bb5eba7d3587abe6105b1cf45afd52edd8c264e9057709",
        "state_bytes": 60426349, "agent_bytes": 77860819, "journal_bytes": 2542224, "script_bytes": 54416312}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _read(p):
    return io.open(p, "rb").read()


def _regular(p):
    return os.path.isfile(p) and not os.path.islink(p)


def identity(state_bytes, wf):
    """One state's census identity from its bytes -> ((phase, attempt, label, wf, script_path), agent id,
    script bytes, problems). Every requirement of the source gate is checked here, meaning is not."""
    bad = []
    try:
        d = json.loads(state_bytes.decode("utf-8"))
        assert isinstance(d, dict)
    except Exception:                                  # noqa: BLE001 - by design
        return None, "", b"", ["%s: the state is not a JSON object" % wf]
    if d.get("runId") != wf:
        bad.append("%s: state runId %r is not the workflow id" % (wf, d.get("runId")))
    if d.get("status") != "completed":
        bad.append("%s: state status %r is not completed" % (wf, d.get("status")))
    if d.get("totalToolCalls") != 0:
        bad.append("%s: totalToolCalls %r is not 0" % (wf, d.get("totalToolCalls")))
    agents = [r for r in (d.get("workflowProgress") or []) if isinstance(r, dict) and r.get("type") == "workflow_agent"]
    if len(agents) != 1:
        bad.append("%s: %d workflow_agent rows, not exactly one" % (wf, len(agents)))
    a = agents[0] if agents else {}
    if a.get("state") != "done":
        bad.append("%s: the agent row state %r is not done" % (wf, a.get("state")))
    if a.get("model") != MODEL:
        bad.append("%s: the agent model %r is not %s" % (wf, a.get("model"), MODEL))
    label, aid = a.get("label") or "", a.get("agentId") or ""
    if not (wf and label and aid):
        bad.append("%s: workflow id, agent id or label is empty" % wf)
    sp = d.get("scriptPath") or ""
    m = re.search(r"/runs/([^/]+)/(.+)$", sp)
    phase = m.group(1) if m and m.group(1) in RUNS else ""
    if not phase:
        bad.append("%s: scriptPath %r is not below one of the ten run roots" % (wf, sp))
    attempt = "retry" if m and m.group(2).startswith("retry/") else "primary"
    script = d.get("script")
    if not isinstance(script, str):
        bad.append("%s: the state carries no script text" % wf)
    return (phase, attempt, label, wf, sp), aid, (script or "").encode("utf-8"), bad


def derive(corpus):
    """Every corpus entry from candidate bytes only -> (rows, byte totals, problems)."""
    rows, problems, seen = [], [], {}
    totals = {"state": 0, "agent": 0, "journal": 0, "script": 0}
    if not os.path.isdir(corpus):
        return rows, totals, ["corpus directory missing: %s" % corpus]
    for wf in sorted(os.listdir(corpus)):
        d = os.path.join(corpus, wf)
        if not os.path.isdir(d) or os.path.islink(d):
            problems.append("extra corpus entry %s" % wf)
            continue
        sp = os.path.join(d, wf + ".json")
        if not _regular(sp):
            problems.append("%s: state file missing" % wf)
            continue
        sb = _read(sp)
        ident, aid, script, bad = identity(sb, wf)
        problems += bad
        if ident is not None:
            key = ident[:3]                            # (run root, attempt, label), whatever the files hold
            if key in seen:
                problems.append("%s: duplicate identity %s also held by %s" % (wf, key, seen[key]))
            seen[key] = wf
        ap, jp = os.path.join(d, "agent-%s.jsonl" % aid), os.path.join(d, "journal.jsonl")
        for f in sorted(os.listdir(d)):
            if f not in (wf + ".json", "agent-%s.jsonl" % aid, "journal.jsonl"):
                problems.append("%s: extra corpus file %s" % (wf, f))
        for what, p in (("agent transcript", ap), ("journal", jp)):
            if not _regular(p):
                problems.append("%s: %s missing" % (wf, what))
        if ident is None or not (_regular(ap) and _regular(jp)):
            continue
        ab, jb = _read(ap), _read(jp)
        totals["state"] += len(sb); totals["agent"] += len(ab); totals["journal"] += len(jb); totals["script"] += len(script)
        phase, attempt, label, _wf, spath = ident
        rows.append([phase, attempt, label, wf, _sha(sb), _sha(ab), _sha(jb), _sha(script), spath])
    return rows, totals, problems


def render(rows):
    return (HEADER + "".join(line + "\n" for line in sorted("\t".join(r) for r in rows))).encode("utf-8")


def problems(corpus=CORPUS, census=CENSUS, pins=PINS):
    """Everything that stops the corpus from being accepted, from candidate bytes only."""
    if not _regular(census):
        return ["census file missing: %s" % census]
    text = _read(census)
    bad = []
    if not text.startswith(HEADER.encode("utf-8")):
        bad.append("the census header is not the fixed header")
    body = text.decode("utf-8", "replace")[len(HEADER):]
    lines = body.split("\n")
    if lines[-1] != "":
        bad.append("the census does not end with one LF")
    recs = [l.split("\t") for l in lines[:-1]]
    if any(len(r) != len(FIELDS) for r in recs):
        bad.append("a census row does not carry exactly %d fields" % len(FIELDS))
    recs = [r for r in recs if len(r) == len(FIELDS)]
    if [ "\t".join(r) for r in recs] != sorted("\t".join(r) for r in recs):
        bad.append("the census rows are not sorted")
    wfs = [r[3] for r in recs]
    if len(set(wfs)) != len(wfs):
        bad.append("duplicate workflow id in the census")
    keys = [tuple(r[:3]) for r in recs]
    if len(set(keys)) != len(keys):
        bad.append("duplicate (run root, attempt, label) identity in the census")
    rows, totals, derived_bad = derive(corpus)
    bad += derived_bad
    by_wf = {r[3]: r for r in rows}
    for r in recs:
        got = by_wf.get(r[3])
        if got is None:
            bad.append("%s: listed in the census but not in the corpus" % r[3])
            continue
        for i, name in enumerate(FIELDS):
            if got[i] != r[i]:
                bad.append("%s: census %s %r differs from the candidate bytes %r" % (r[3], name, r[i][:24], got[i][:24]))
    for wf in by_wf:
        if wf not in set(wfs):
            bad.append("%s: in the corpus but not in the census" % wf)
    if render(rows) != text:
        bad.append("the census text does not re-derive from the candidate bytes")
    if len(rows) != pins["rows"]:
        bad.append("%d corpus rows, not the pinned %d" % (len(rows), pins["rows"]))
    if len(text) != pins["census_bytes"] or _sha(text) != pins["census_sha256"]:
        bad.append("the census is %d bytes %s, not the pinned %d bytes %s" % (len(text), _sha(text)[:16], pins["census_bytes"], pins["census_sha256"][:16]))
    for k in ("state", "agent", "journal", "script"):
        if totals[k] != pins[k + "_bytes"]:
            bad.append("%s bytes %d, not the pinned %d" % (k, totals[k], pins[k + "_bytes"]))
    return bad


def _copy_exact(src, dst):
    if not _regular(src):
        raise SystemExit("REFUSED: official file missing: %s" % src)
    b = _read(src)
    if os.path.exists(dst):
        if _read(dst) != b:
            raise SystemExit("REFUSED: %s exists with different bytes" % dst)
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def copy():
    """Select by scriptPath alone, refuse anything below a run root that fails the gate, copy exact bytes,
    write the census from the candidate bytes, then verify. Nothing is written before the selection holds."""
    picked = []
    for p in sorted(glob.glob(os.path.join(OFFICIAL, "workflows", "wf_*.json"))):
        wf = os.path.basename(p)[:-5]
        b = _read(p)
        try:
            sp = (json.loads(b.decode("utf-8")) or {}).get("scriptPath") or ""
        except Exception:                              # noqa: BLE001 - by design
            continue
        m = re.search(r"/runs/([^/]+)/", sp)
        if not m or m.group(1) not in RUNS:
            continue
        ident, aid, _script, bad = identity(b, wf)
        if bad:
            raise SystemExit("REFUSED: %s" % "; ".join(bad))
        picked.append((wf, aid, p))
    if len(picked) != PINS["rows"]:
        raise SystemExit("REFUSED: %d states below the ten run roots, not the pinned %d" % (len(picked), PINS["rows"]))
    for wf, aid, p in picked:
        sub = os.path.join(OFFICIAL, "subagents", "workflows", wf)
        _copy_exact(p, os.path.join(CORPUS, wf, wf + ".json"))
        _copy_exact(os.path.join(sub, "agent-%s.jsonl" % aid), os.path.join(CORPUS, wf, "agent-%s.jsonl" % aid))
        _copy_exact(os.path.join(sub, "journal.jsonl"), os.path.join(CORPUS, wf, "journal.jsonl"))
    rows, _totals, bad = derive(CORPUS)
    if bad:
        raise SystemExit("REFUSED: " + "; ".join(bad[:5]))
    io.open(CENSUS, "wb").write(render(rows))
    print("copied %d states with transcripts and journals; census written" % len(rows))
    return verify()


def verify():
    bad = problems()
    if bad:
        for b in bad[:20]:
            print("PROBLEM " + b)
        print("official results: REFUSED (%d problems)" % len(bad))
        return 1
    rows, totals, _bad = derive(CORPUS)
    per = {}
    for r in rows:
        per[(r[0], r[1])] = per.get((r[0], r[1]), 0) + 1
    for k in sorted(per):
        print("  %-40s %-7s %3d" % (k[0], k[1], per[k]))
    print("official results: %d states hold; census %s; bytes state %d agent %d journal %d script %d"
          % (len(rows), _sha(_read(CENSUS)), totals["state"], totals["agent"], totals["journal"], totals["script"]))
    return 0


if __name__ == "__main__":
    sys.exit(verify() if sys.argv[1:] == ["verify"] else copy())
