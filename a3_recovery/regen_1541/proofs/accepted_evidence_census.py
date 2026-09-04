#!/usr/bin/env python3
"""Exact attempt/evidence accounting of the invrev_run4 review (Codex SEQ 1561 item 2).

Derived ONLY from the 38 saved rows of attempts.json plus the restored ledger. Each
row is bound to one state (evidence/workflow_states/<basename(state_path)>), one
transcript (evidence/subagent_records/<workflow>/agent-<agent_id>.jsonl) and one raw
answer (invrev_run4/replies/<raw_name>); the three quarantined calls of the ledger are
bound to the nine files the ledger pins by sha256 (state, transcript, journal each), and
their three ancillary metadata files are counted and hashed but are NOT ledger-pinned.

Nothing here parses or judges a reply. The existing owners do, exactly as the harvest
did: audit_worker_access._chain proves the transcript's complete answer, which the
state's result and the raw answer must equal byte for byte; raw_transport.parse_reply
and build_inventory_review._reply_shape decide schema validity. A schema-invalid attempt
is preserved and bound as PAID evidence; it is never called accepted. Bytes are bound
once (`--bind`, evidence/ATTEMPT_EVIDENCE.tsv) and verified ever after.

`--strict` (Codex SEQ 1562 item 1) calls the ONE existing strict owner,
build_inventory_review._attempt_evidence, for every saved attempt with the frozen prompt
text, the one official parent session the rows name and shared seen sets: official
location and parent session, state runId, exactly one agent and its id, pinned model,
agent type and rendered launcher, zero tool calls, transcript input digest, every
assistant record's model / session / agent / effort, the ordered continuation chain, raw
equality, globally unique run / agent / transcript / raw / response identities; and the
one-retry rule by its owner, build_inventory_review._retry_lawful. The owner reads the
OFFICIAL paths, so `--in-namespace` re-runs the census inside a private mount namespace
where tmpfs masks the live session records and the rows' package copies are projected at
their pinned historical paths (`--projected`): the location rule is met, never weakened,
and no live record is read. Outside that projection strict mode refuses.

Schema-valid JSON is NOT a finalized answer: the accounting names
`sources_with_schema_valid_latest_attempt`, and meaning adjudication remains A4's.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments", "harness")
RUN = os.path.join("bench", ".claude", "plans", "Drivers", "experiments", "invrev_run4")
LEDGER = os.path.join(RUN, "transport_proof_replacements.json")
ATTEMPTS = os.path.join(RUN, "attempts.json")
IDENTITY = os.path.join("evidence", "ledger_identity.json")
BINDING = os.path.join("evidence", "ATTEMPT_EVIDENCE.tsv")
STRICT = os.path.join("reports", "strict_attempt_identity.json")
STATES_TSV = os.path.join("evidence", "workflow_states", "WORKFLOW_STATES.tsv")
RECORDS_TSV = os.path.join("evidence", "subagent_records", "SUBAGENT_RECORDS.tsv")
PINNED_KINDS = ("state", "transcript", "journal")


def _owners():
    """The accepted owners, imported from the package's own harness copy."""
    os.environ.setdefault("GUIDANCE_SCRIPTS_DIR",
                          os.path.join(R, "bench", ".claude", "skills", "earnings-orchestrator", "scripts"))
    if HARNESS not in sys.path:
        sys.path.insert(0, HARNESS)
    import raw_transport as RT
    import build_inventory_review as BIR
    import audit_worker_access as AUD
    return RT, BIR, AUD


def _sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def _rows(root):
    return json.load(io.open(os.path.join(root, ATTEMPTS), encoding="utf-8"))


def row_paths(row):
    """-> {kind: relpath} for one saved attempt row, from the row's own fields."""
    state = os.path.basename(row["state_path"])
    wf = state[:-len(".json")]
    return {"state": os.path.join("evidence", "workflow_states", state),
            "transcript": os.path.join("evidence", "subagent_records", wf, "agent-%s.jsonl" % row["agent_id"]),
            "raw": os.path.join(RUN, "replies", row["raw_name"])}


def _quarantine(root):
    """-> [(ledger row, {'state': rel, 'transcript': rel, 'journal': rel}, meta rel)]."""
    rows = json.loads(io.open(os.path.join(root, LEDGER), "rb").read().decode("utf-8"))
    out = []
    for r in rows:
        q = r["quarantined_call"]
        d = os.path.join(RUN, "quarantine", "%s.attempt1" % r["source_id"])
        out.append((r, {"state": os.path.join(d, q["run_id"] + ".json"),
                        "transcript": os.path.join(d, "agent-%s.jsonl" % q["agent_id"]),
                        "journal": os.path.join(d, "journal.jsonl")},
                    os.path.join(d, "agent-%s.meta.json" % q["agent_id"])))
    return out


def needed_paths(root):
    """Every relpath the census reads, so a private copy can be complete."""
    out = [ATTEMPTS, LEDGER, IDENTITY, STATES_TSV, RECORDS_TSV]
    for row in _rows(root):
        out.extend(row_paths(row).values())
    if os.path.isfile(os.path.join(root, LEDGER)):
        for _r, files, meta in _quarantine(root):
            out.extend(files.values())
            out.append(meta)
    if os.path.isfile(os.path.join(root, BINDING)):
        out.append(BINDING)
    return [p for p in out if os.path.exists(os.path.join(root, p))]


def first_path(root, kind):
    if kind == "ledger":
        return LEDGER
    return row_paths(_rows(root)[0])[kind]


def parsed_reply(root, row):
    """The owner's parse of one raw answer (for controls that re-bind a variant)."""
    RT, _BIR, _AUD = _owners()
    return RT.parse_reply(io.open(os.path.join(root, row_paths(row)["raw"]), encoding="utf-8", newline="").read())


def _pinned(root, rel_tsv):
    fp = os.path.join(root, rel_tsv)
    if not os.path.isfile(fp):
        return None
    out = {}
    for ln in io.open(fp, encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            f, b, s, hist = (ln.split("\t") + [""])[:4]
            out[f] = (int(b), s, hist)
    return out


def census(root, bind=False):
    RT, BIR, AUD = _owners()
    defects, bound = [], []
    root = os.path.abspath(root)
    P = lambda rel: os.path.join(root, rel)

    # THE LEDGER, BY ITS IDENTITY
    ident = json.load(io.open(P(IDENTITY), encoding="utf-8"))
    ledger_rows = []
    if not os.path.isfile(P(LEDGER)):
        defects.append("ledger missing: %s" % LEDGER)
    else:
        raw = io.open(P(LEDGER), "rb").read()
        if len(raw) != ident["size"] or hashlib.sha256(raw).hexdigest() != ident["sha256"]:
            defects.append("ledger hash/size differs from evidence/ledger_identity.json")
        try:
            ledger_rows = json.loads(raw.decode("utf-8"))
        except ValueError:
            defects.append("ledger does not parse")
        for r in ledger_rows:
            if r.get("class") != "transport_proof_replacement":
                defects.append("ledger row %s has class %r" % (r.get("source_id"), r.get("class")))

    # THE QUARANTINE: nine ledger-pinned files, three ancillary metadata files
    pinned_files, meta_files, meta_hashes = 0, 0, set()
    for r, files, meta in (_quarantine(root) if ledger_rows else []):
        q = r["quarantined_call"]
        for kind in PINNED_KINDS:
            rel = files[kind]
            if not os.path.isfile(P(rel)):
                defects.append("quarantine %s missing for %s: %s" % (kind, r["source_id"], rel))
                continue
            pinned_files += 1
            if _sha(P(rel)) != q.get(kind + "_sha256"):
                defects.append("quarantine %s of %s does not hash to the ledger's %s_sha256" % (kind, r["source_id"], kind))
        if os.path.isfile(P(meta)):
            meta_files += 1
            meta_hashes.add(_sha(P(meta)))
        else:
            defects.append("quarantine metadata missing for %s: %s" % (r["source_id"], meta))
    quarantine = {"ledger_pinned_files": pinned_files, "metadata_files": meta_files,
                  "metadata_sha256": sorted(meta_hashes),
                  "ledger_has_meta_sha256": any("meta_sha256" in r.get("quarantined_call", {}) for r in ledger_rows)}

    # THE 38 SAVED ATTEMPT ROWS: identities unique, files present, chain exact
    rows = _rows(root)
    for key, name in ((lambda r: (r["task"], r["ordinal"], r["attempt"]), "task/ordinal/attempt"),
                      (lambda r: r["agent_id"], "agent_id"), (lambda r: r["raw_name"], "raw_name"),
                      (lambda r: os.path.basename(r["state_path"]), "state"),
                      (lambda r: (r["source_id"], r["attempt"]), "source/attempt")):
        seen = {}
        for r in rows:
            k = key(r)
            if k in seen:
                defects.append("duplicate %s identity %r (rows %d and %d)" % (name, k, seen[k], r["ordinal"]))
            seen[k] = r["ordinal"]
    pinned_states, pinned_records = _pinned(root, STATES_TSV), _pinned(root, RECORDS_TSV)
    valid, invalid, chain_mismatches = [], [], 0
    for r in rows:
        paths = row_paths(r)
        present = True
        for kind, rel in paths.items():
            if not os.path.isfile(P(rel)):
                defects.append("%s missing for %s attempt %d: %s" % ("raw answer" if kind == "raw" else kind, r["source_id"], r["attempt"], rel))
                present = False
                continue
            bound.append((kind, rel, os.path.getsize(P(rel)), _sha(P(rel))))
        if not present:
            continue
        # THE STATE names this agent and is complete; its bytes are pinned
        state_result = None
        try:
            st = json.load(io.open(P(paths["state"]), encoding="utf-8"))
            agents = [x for x in st.get("workflowProgress") or [] if x.get("type") == "workflow_agent"]
            if st.get("status") != "completed":
                defects.append("state of %s attempt %d is %r, not completed" % (r["source_id"], r["attempt"], st.get("status")))
            if len(agents) != 1 or agents[0].get("agentId") != r["agent_id"]:
                defects.append("state of %s attempt %d names agent(s) %s, not the row's agent %s"
                               % (r["source_id"], r["attempt"], [a.get("agentId") for a in agents], r["agent_id"]))
            state_result = st.get("result")
        except ValueError:
            defects.append("state of %s attempt %d does not parse" % (r["source_id"], r["attempt"]))
        if pinned_states is not None:
            pin = pinned_states.get(os.path.basename(paths["state"]))
            if pin is None or pin[1] != _sha(P(paths["state"])):
                defects.append("state of %s attempt %d does not hash to WORKFLOW_STATES.tsv" % (r["source_id"], r["attempt"]))
        # THE TRANSCRIPT CHAIN, by the accepted owner; its bytes are pinned
        raw_text = io.open(P(paths["raw"]), encoding="utf-8", newline="").read()
        recs = AUD._jsonl(P(paths["transcript"]))
        if recs is None:
            defects.append("transcript of %s attempt %d is not readable whole" % (r["source_id"], r["attempt"]))
            complete = None
        else:
            bad, _final, complete = AUD._chain(recs, [x for x in recs if x.get("type") == "assistant"])
            if bad or complete is None:
                defects.append("transcript of %s attempt %d: chain problems %s" % (r["source_id"], r["attempt"], (bad or ["no answer"])[:2]))
        if pinned_records is not None:
            rel_in_tsv = os.path.relpath(paths["transcript"], os.path.join("evidence", "subagent_records"))
            pin = pinned_records.get(rel_in_tsv)
            if pin is None or pin[1] != _sha(P(paths["transcript"])):
                defects.append("transcript of %s attempt %d does not hash to SUBAGENT_RECORDS.tsv" % (r["source_id"], r["attempt"]))
        # EXACT EQUALITY: state result == transcript's complete answer == raw answer
        if complete is not None and complete != raw_text:
            defects.append("transcript of %s attempt %d: complete answer differs from the raw answer" % (r["source_id"], r["attempt"]))
            chain_mismatches += 1
        if state_result is not None and state_result != raw_text:
            defects.append("state of %s attempt %d: result differs from the raw answer" % (r["source_id"], r["attempt"]))
            chain_mismatches += 1
        # VALIDITY, by the owners: parse, then the total door; the source must be this row's
        verdict = {"source_id": r["source_id"], "attempt": r["attempt"], "ordinal": r["ordinal"], "problems": []}
        try:
            obj = RT.parse_reply(raw_text)
        except Exception as exc:                                       # noqa: BLE001 - the owner's refusal
            verdict["problems"] = ["parse: %s" % str(exc)[:120]]
            invalid.append(verdict)
            continue
        if not isinstance(obj, dict) or obj.get("source_id") != r["source_id"]:
            defects.append("raw answer of %s attempt %d names source %r, not the row's source"
                           % (r["source_id"], r["attempt"], obj.get("source_id") if isinstance(obj, dict) else None))
        shape = BIR._reply_shape(r["source_id"], obj)
        if shape:
            verdict["problems"] = [str(s)[:160] for s in shape[:3]]
            invalid.append(verdict)
        else:
            valid.append(verdict)

    # THE ACCOUNTING. Schema validity is a FORMAT fact about a source's LATEST attempt;
    # nothing here finalizes a meaning - that adjudication is A4's, not A3's.
    sources = {r["source_id"] for r in rows}
    latest = {}
    for r in rows:
        if r["attempt"] >= latest.get(r["source_id"], (0,))[0]:
            latest[r["source_id"]] = (r["attempt"], r["ordinal"])
    valid_keys = {(v["source_id"], v["attempt"], v["ordinal"]) for v in valid}
    latest_valid = {s for s, (a, o) in latest.items() if (s, a, o) in valid_keys}
    replacements = []
    for inv in invalid:
        later = [v for v in valid if v["source_id"] == inv["source_id"] and v["attempt"] == inv["attempt"] + 1]
        if later:
            replacements.append({"source_id": inv["source_id"], "attempt": later[0]["attempt"], "schema_valid": True})
        # an invalid attempt with no later valid one is not a binding defect: it is paid
        # evidence whose source has no final result, and the accounting says so
    accounting = {"paid_calls": len(rows) + len(ledger_rows), "saved_attempt_rows": len(rows),
                  "quarantined_calls": len(ledger_rows), "unique_sources": len(sources),
                  "schema_valid_attempts": len(valid), "schema_invalid_attempts": len(invalid),
                  "sources_with_schema_valid_latest_attempt": len(latest_valid),
                  "meaning_finalized_answers_at_a3": 0, "meaning_adjudication_owner": "A4",
                  "chain_mismatches": chain_mismatches, "files_bound": len(bound)}

    # BYTES, BOUND ONCE AND VERIFIED EVER AFTER
    if bind:
        io.open(P(BINDING), "w", encoding="utf-8").write(
            "kind\tfile\tbytes\tsha256\n" + "".join("%s\t%s\t%d\t%s\n" % b for b in sorted(bound, key=lambda b: (b[0], b[1]))))
    elif os.path.isfile(P(BINDING)):
        want = {}
        for ln in io.open(P(BINDING), encoding="utf-8").read().split("\n")[1:]:
            if ln.strip():
                k, f, b, s = ln.split("\t")
                want[(k, f)] = (int(b), s)
        have = {(b[0], b[1]) for b in bound}
        for kind, rel, size, digest in bound:
            pin = want.get((kind, rel))
            if pin is None:
                defects.append("%s unbound: %s is not in ATTEMPT_EVIDENCE.tsv" % (kind, rel))
            elif pin != (size, digest):
                defects.append("%s hash mismatch against ATTEMPT_EVIDENCE.tsv: %s" % ("raw answer" if kind == "raw" else kind, rel))
        for (kind, rel) in want:
            if (kind, rel) not in have:
                defects.append("%s bound but not reached by any row: %s" % (kind, rel))
    else:
        defects.append("ATTEMPT_EVIDENCE.tsv absent: the set is not bound")
    return {"rows": len(rows), "files_bound": len(bound), "ledger_rows": len(ledger_rows),
            "accounting": accounting, "schema_valid": valid, "schema_invalid": invalid,
            "lawful_attempt2_replacements": replacements, "quarantine": quarantine,
            "defects": defects, "bound": bind}


def _tmpfs(path):
    """True when `path` is a tmpfs mount point in THIS mount namespace - the mask that
    hides the live session records behind the projection."""
    for ln in io.open("/proc/self/mountinfo", encoding="utf-8"):
        f = ln.split()
        if f[4] == path:
            return f[f.index("-") + 1] == "tmpfs"
    return False


def official_roots(root):
    """-> (parent session, official states dir, official records dir) the saved rows name,
    by the owner's own location rule: exactly one session, under an existing official
    directory. Nothing is created; a foreign or absent session refuses."""
    _RT, _BIR, AUD = _owners()
    rows = _rows(root)
    locs = {AUD._official_location(r["state_path"]) for r in rows}
    if len(locs) != 1 or (None, None) in locs:
        raise SystemExit("REFUSED: the %d rows do not name exactly one official parent session: %s"
                         % (len(rows), sorted(str(l[1]) for l in locs)))
    session_dir, session = locs.pop()
    sroot, rroot = os.path.join(session_dir, "workflows"), os.path.join(session_dir, "subagents", "workflows")
    if not (os.path.isdir(sroot) and os.path.isdir(rroot)):
        raise SystemExit("REFUSED: the official session directory %s does not exist; nothing is created" % session_dir)
    return session, sroot, rroot


def project_official(root):
    """Inside the namespace: copy each row's state and transcript from the package to its
    PINNED historical path under the two masked roots - bytes verified against the mount
    authority first, the path verified against the row's own official path, nothing
    written outside the masks. -> files projected"""
    _session, sroot, rroot = official_roots(root)
    if not (_tmpfs(sroot) and _tmpfs(rroot)):
        raise SystemExit("REFUSED: not inside the projection: %s and %s are not tmpfs masks" % (sroot, rroot))
    tables = {"state": (os.path.join("evidence", "workflow_states"), _pinned(root, STATES_TSV) or {}),
              "transcript": (os.path.join("evidence", "subagent_records"), _pinned(root, RECORDS_TSV) or {})}
    n = 0
    for r in _rows(root):
        paths = row_paths(r)
        for kind, (base, table) in tables.items():
            rel = paths[kind]
            key = os.path.relpath(rel, base)
            pin = table.get(key)
            if pin is None:
                raise SystemExit("REFUSED: %s is not pinned in its mount authority" % rel)
            hist = os.path.expanduser(pin[2])
            want = r["state_path"] if kind == "state" else os.path.join(rroot, key)
            if hist != want:
                raise SystemExit("REFUSED: %s is pinned at %s, not at the row's official path %s" % (rel, hist, want))
            data = io.open(os.path.join(root, rel), "rb").read()
            if len(data) != pin[0] or hashlib.sha256(data).hexdigest() != pin[1]:
                raise SystemExit("REFUSED: %s does not hash to its mount authority" % rel)
            os.makedirs(os.path.dirname(hist), exist_ok=True)
            io.open(hist, "wb").write(data)
            n += 1
    return n


def in_namespace(root, argv):
    """Re-run this census inside a private mount namespace: tmpfs over the official states
    and records directories (the live session records are masked), the rows' package
    copies projected there, and nothing else visible at those paths. -> exit status"""
    import shlex
    _session, sroot, rroot = official_roots(root)
    inner = " && ".join(["mount -t tmpfs none %s" % shlex.quote(sroot),
                         "mount -t tmpfs none %s" % shlex.quote(rroot),
                         "exec %s -B %s --projected %s" % (shlex.quote(sys.executable), shlex.quote(os.path.abspath(__file__)),
                                                            " ".join(shlex.quote(a) for a in argv if a != "--in-namespace"))])
    r = subprocess.run(["unshare", "-rm", "--propagation", "private", "/bin/bash", "-c", inner],
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return r.returncode


def strict(root):
    """The strict identity of every saved attempt, by the ONE existing owner, on the
    projected official paths. -> report (or a refusal outside the projection)"""
    _RT, BIR, _AUD = _owners()
    session, sroot, rroot = official_roots(root)
    if not (_tmpfs(sroot) and _tmpfs(rroot)):
        return {"refused": "not inside the projection: %s and %s are not tmpfs masks, so a read there "
                           "would be a LIVE session record" % (sroot, rroot)}
    rows = sorted(_rows(root), key=lambda r: (BIR.TASKS.index(r["task"]) if r["task"] in BIR.TASKS else -1,
                                              r["ordinal"], r["attempt"]))
    seen = {k: set() for k in ("run", "agent", "transcript", "raw", "response")}
    replies = os.path.join(root, RUN, "replies")
    failures = []
    for r in rows:
        where = "%s %d (%s) attempt %d" % (r["task"], r["ordinal"], r["source_id"], r["attempt"])
        bad = BIR._attempt_evidence(r, where, BIR.prompt_text(r["source_id"]), replies, session, seen)
        if bad:
            failures.append({"source_id": r["source_id"], "attempt": r["attempt"], "problems": [str(b) for b in bad]})
    by_source = {}
    for r in rows:
        by_source.setdefault(r["source_id"], []).append(r)
    retried = sorted(s for s, rs in by_source.items() if len(rs) > 1)
    unlawful = []
    for s in retried:
        first = min(by_source[s], key=lambda r: r["attempt"])
        lawful, why = BIR._retry_lawful(os.path.join(replies, first["raw_name"]))
        if not lawful:
            unlawful.append({"source_id": s, "why": str(why)})
    return {"rows": len(rows), "parent_session": session, "owner": "build_inventory_review._attempt_evidence",
            "retry_owner": "build_inventory_review._retry_lawful", "failures": failures,
            "unique": {k: len(v) for k, v in seen.items()}, "retries": len(retried), "unlawful_retries": unlawful}


def main(argv):
    root = os.path.abspath(argv[argv.index("--root") + 1]) if "--root" in argv else R
    if "--strict" in argv and "--in-namespace" in argv:
        return in_namespace(root, argv)
    if "--projected" in argv:
        print("projected %d official files from the package copies" % project_official(root))
    rep = census(root, bind="--bind" in argv)
    os.makedirs(os.path.join(root, "reports"), exist_ok=True)
    json.dump(rep, io.open(os.path.join(root, "reports", "accepted_evidence_census.json"), "w", encoding="utf-8"), indent=1)
    a, q = rep["accounting"], rep["quarantine"]
    print("attempt-evidence accounting: %d paid calls = %d saved attempt rows + %d quarantined | %d unique sources | "
          "%d schema-valid + %d schema-invalid attempts | %d sources with a schema-valid latest attempt, "
          "%d meaning-finalized answers at A3 (meaning is %s's) | chain mismatches %d | "
          "%d files bound | quarantine: %d ledger-pinned + %d metadata (%d distinct hash) | defects %d%s"
          % (a["paid_calls"], a["saved_attempt_rows"], a["quarantined_calls"], a["unique_sources"],
             a["schema_valid_attempts"], a["schema_invalid_attempts"], a["sources_with_schema_valid_latest_attempt"],
             a["meaning_finalized_answers_at_a3"], a["meaning_adjudication_owner"], a["chain_mismatches"],
             a["files_bound"], q["ledger_pinned_files"], q["metadata_files"], len(q["metadata_sha256"]),
             len(rep["defects"]), " (BOUND)" if rep["bound"] else ""))
    for v in rep["schema_invalid"]:
        print("  schema-invalid: %s attempt %d: %s" % (v["source_id"], v["attempt"], v["problems"][0] if v["problems"] else ""))
    for d in rep["defects"][:40]:
        print("  DEFECT", d)
    rc = 1 if rep["defects"] else 0
    if "--strict" in argv:
        s = strict(root)
        json.dump(s, io.open(os.path.join(root, STRICT), "w", encoding="utf-8"), indent=1)
        if "refused" in s:
            print("STRICT REFUSED: " + s["refused"])
            return 1
        u = s["unique"]
        print("strict attempt identity: %d rows by %s | parent session %s | failures %d | unique run %d agent %d "
              "transcript %d raw %d response %d | retries %d by %s, unlawful %d"
              % (s["rows"], s["owner"], s["parent_session"], len(s["failures"]), u["run"], u["agent"], u["transcript"],
                 u["raw"], u["response"], s["retries"], s["retry_owner"], len(s["unlawful_retries"])))
        for f in s["failures"]:
            print("  STRICT FAIL %s attempt %d: %s" % (f["source_id"], f["attempt"], f["problems"][0][:220]))
        for x in s["unlawful_retries"]:
            print("  UNLAWFUL RETRY %s: %s" % (x["source_id"], x["why"][:200]))
        rc = rc or (1 if s["failures"] or s["unlawful_retries"] else 0)
    return rc


_owners()          # the owners are loaded WITH this module: a lazy import is hidden growth for whoever calls first


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
