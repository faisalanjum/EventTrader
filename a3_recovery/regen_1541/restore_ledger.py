#!/usr/bin/env python3
"""ONE-TIME RECOVERY TOOL, not a proof step: restore the transport-proof replacement
ledger from the EXACT surviving bytes, without transcript replay (Codex SEQ 1560 item 1).

Every field is measured: the row shape and its constant strings are history's own print
of the one-row ledger (frozen record 29581); the quarantined identities are the twelve
quarantine files (run id and agent id from their names, sha256 from their bytes); the
authorisations are the tuples record 29746 printed; the replacement run ids are the
harvest calls history ran for each source (29591/29607, 29758, 30066), the replacement
agent ids what those calls printed. The result is written ONLY if its size and sha256
equal the identity Codex stated, read from the archived packet - never typed here.
"""
import hashlib
import io
import json
import os
import re
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R, "ledger"))
import replay_transcript as RT                                   # noqa: E402

RUN = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments", "invrev_run4")
OUT = os.path.join(RUN, "transport_proof_replacements.json")
IDENTITY = os.path.join(R, "evidence", "ledger_identity.json")
TEMPLATE_RECORD = 29581          # history printed the one-row ledger here
AUTH_RECORD = 29746              # history printed (source_id, class, authorized_by) here
# the harvest call that ran each replacement: (record, source_id, run id on its line)
REPLACEMENT_CALLS = {"0000764478-25-000057": 29591,
                     "0000940944-26-000005": 29758,
                     "MCD_2026-02-11T16.30": 30066}


def _sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def _harvest_call(n):
    """-> (run id, agent id or None) of the harvest call at record n, from its own line
    and its own printed result."""
    cmd = RT.bash_command(RT.lines({n})[n])
    m = re.search(r'harvest\.py"?\s+\d+\s+\S+\s+(wf_[0-9a-f-]+)\s+\d+', cmd)
    res = RT.saved_result(n) or ""
    a = re.search(r"agent ([0-9a-f]{17})", res)
    return m.group(1), (a.group(1) if a else None)


def rows():
    printed = RT.saved_result(TEMPLATE_RECORD)
    template = json.loads(printed[printed.index("["):])[0]
    auth = {sid: a for sid, _cls, a in eval(RT.saved_result(AUTH_RECORD).split("\n")[0])}
    qdir = os.path.join(RUN, "quarantine")
    out = []
    for d in sorted(os.listdir(qdir), key=lambda d: list(REPLACEMENT_CALLS).index(d.rsplit(".attempt", 1)[0])):
        sid = d.rsplit(".attempt", 1)[0]
        dd = os.path.join(qdir, d)
        state = [f for f in os.listdir(dd) if f.startswith("wf_") and f.endswith(".json")][0]
        agent = [f for f in os.listdir(dd) if f.startswith("agent-") and f.endswith(".jsonl")][0]
        q = template["quarantined_call"]
        qc = {"run_id": state[:-len(".json")], "agent_id": agent[len("agent-"):-len(".jsonl")],
              "why": q["why"], "semantic_credit": q["semantic_credit"],
              "counts_against_74_ceiling": q["counts_against_74_ceiling"],
              "state_sha256": _sha(os.path.join(dd, state)),
              "transcript_sha256": _sha(os.path.join(dd, agent)),
              "journal_sha256": _sha(os.path.join(dd, "journal.jsonl"))}
        run_id, agent_id = _harvest_call(REPLACEMENT_CALLS[sid])
        rc = {"run_id": run_id}
        if agent_id:
            rc["agent_id"] = agent_id
        rc["is_accepted_attempt"] = template["replacement_call"]["is_accepted_attempt"]
        rc["outside_retry_class"] = template["replacement_call"]["outside_retry_class"]
        # the MCD authorisation is the standing rule of SEQ 1339, as record 30051 recorded
        out.append({"class": template["class"],
                    "authorized_by": auth.get(sid, auth["0000940944-26-000005"]),
                    "source_id": sid, "quarantined_call": qc, "replacement_call": rc})
    assert out[0] == template, "row 1 must equal history's own print"
    return out


def main():
    ident = json.load(io.open(IDENTITY, encoding="utf-8"))
    data = json.dumps(rows(), indent=1).encode("utf-8")
    size, digest = len(data), hashlib.sha256(data).hexdigest()
    print("assembled %d bytes sha256 %s" % (size, digest))
    if size != ident["size"] or digest != ident["sha256"]:
        print("REFUSED: identity differs from %s (%d, %s)" % (IDENTITY, ident["size"], ident["sha256"]))
        return 1
    io.open(OUT, "wb").write(data)
    print("written %s" % os.path.relpath(OUT, R))
    # THE RESUME PATH'S FIXED-INPUT LIST NAMES THE LEDGER BY ITS MEASURED IDENTITY, so
    # verify_fixed_inputs.py re-checks these bytes on every run; one row, replaced if
    # present, never duplicated
    tsv = os.path.join(R, "evidence", "RESUME_INPUTS.tsv")
    rel = os.path.relpath(OUT, R)
    lines = [l for l in io.open(tsv, encoding="utf-8").read().split("\n") if l.strip()]
    lines = [l for l in lines if not l.startswith(rel + "\t")]
    lines.append("%s\t%d\t%s\trestored from the exact surviving bytes by restore_ledger.py "
                 "(records %d, %d, harvest calls %s; twelve quarantine files); identity = "
                 "Codex SEQ 1560" % (rel, size, digest, TEMPLATE_RECORD, AUTH_RECORD,
                                     sorted(REPLACEMENT_CALLS.values())))
    io.open(tsv, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("RESUME_INPUTS.tsv: ledger row written (%d rows)" % (len(lines) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
