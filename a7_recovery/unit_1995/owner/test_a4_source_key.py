# -*- coding: utf-8 -*-
"""TEST evidence for the CORRECTED source-only A4 key preparation (Codex 1989).

Every fixture is labelled TEST and lives in the boundary's tmpfs. No production
artifact is written, no historical receipt is invented, no model is called and
no TEST binding is ever used against the real package. Each proof carries an
independently calculated positive control and at least one negative control.
Prints ONE JSON object; exits 0 only when every check passed.
"""
import builtins
import collections
import io
import json
import os
import shutil
import sys

OWNER = os.path.dirname(os.path.abspath(__file__))
if OWNER not in sys.path:
    sys.path.insert(0, OWNER)
import a4_source_key as SK                                        # noqa: E402

TMP = "/tmp/TEST_a4_source_key_1989"
RESULTS = collections.OrderedDict()
FAILED = []
SONNET = None


def check(name, ok, detail=""):
    RESULTS[name] = collections.OrderedDict([("passed", bool(ok)),
                                             ("detail", detail)])
    if not ok:
        FAILED.append(name)
    return bool(ok)


def refuses(fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False, "it returned instead of refusing"
    except Exception as exc:                          # noqa: BLE001 - by design
        return True, str(exc)[:200]


def fresh(name):
    path = os.path.join(TMP, name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path


def declare(kind, alias, runtime=None, **over):
    kind = over.pop("kind", kind)
    doc = {"kind": kind, "model_alias": alias,
           "runtime_model_id": runtime or "TEST-independent-runtime",
           "effort": SK.K.EFFORT,
           "agentType": SK.K.AGENT_TYPE,
           "disallowedTools": list(SK.K.DISALLOWED),
           "max_output_tokens": SK.K.MAX_OUTPUT,
           "transport": "TEST declaration, not a proof"}
    doc.update(over)
    os.path.isdir(TMP) or os.makedirs(TMP)
    path = os.path.join(TMP, "TEST_role_%s.json" % kind.lower())
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc))
    return path


# ------------------------------------------------ the population and prompt --
def test_population_and_prompt():
    tasks = SK.tasks()
    frozen = [pid for pid, _r in SK.inventory()]
    flat = [p for t in tasks for p in t["rows"]]
    check("population/every frozen row scheduled once in frozen order",
          flat == frozen and len(set(flat)) == len(flat),
          "%d rows over %d events" % (len(flat), len(tasks)))
    check("population/derives clean",
          SK.population_problems() == [] and SK.plan_problems() == [])
    cov = SK.coverage()
    check("population/all source events accounted",
          len(cov) == len(SK.plan()["events"])
          and sum(c["located_rows"] for c in cov) == len(frozen),
          "%d events, %d scheduled" % (len(cov), len(tasks)))
    check("population/NEGATIVE a dropped row refuses",
          SK.population_problems([dict(t, rows=t["rows"][1:]) if n == 0 else t
                                  for n, t in enumerate(tasks)]) != [])
    bad = {t["source_id"]: SK.prompt_problems(t) for t in tasks}
    check("prompt/every rendered prompt enumerates to its owners",
          not {k: v for k, v in bad.items() if v},
          json.dumps(sorted(k for k, v in bad.items() if v)[:3]))
    check("source/the served source is the frozen one",
          SK.source_problems() == [], json.dumps(SK.source_problems()[:2]))

    run = SK.K._read(os.path.join(SK.K.EVIDENCE, "a3_serial_dir.txt")).strip()
    opened, real_open, real_io = [], builtins.open, io.open
    builtins.open = lambda p, *a, **k: (opened.append(str(p)),
                                        real_open(p, *a, **k))[1]
    io.open = lambda p, *a, **k: (opened.append(str(p)), real_io(p, *a, **k))[1]
    try:
        [SK.prompt(t) for t in tasks]
    finally:
        builtins.open, io.open = real_open, real_io
    check("prompt/no evaluated reply is read while rendering",
          not [p for p in opened if p.startswith(run)],
          "%d run paths opened" % len([p for p in opened if p.startswith(run)]))

    reader = SK.K.source_input
    cache = SK.HR._source

    def altered(sid):
        v = json.loads(json.dumps(reader(sid), default=str))
        v["text_parts"][0]["content"] += "\nTEST altered frozen source."
        return v

    SK.K.source_input = altered
    SK.HR._source = lambda sid: (altered(sid),) + cache(sid)[1:]
    try:
        check("source/NEGATIVE altered source text is caught",
              SK.source_problems() != [],
              json.dumps(SK.source_problems()[:1])[:200])
    finally:
        SK.K.source_input, SK.HR._source = reader, cache


# ------------------------------------------------- the independent key seat --
def test_key_role_seat():
    global SONNET
    SONNET = SK.sonnet_role_untouched()
    real = SK.KEY_ROLE_FILE
    check("seat/no role is declared, so nothing publishes and nothing renders",
          SK.key_role() is None and SK.role_problems() != []
          and refuses(SK.render_launcher, SK.tasks()[0])[0],
          json.dumps(SK.role_problems())[:200])
    check("seat/the manifest declares no observed proof and names what is "
          "missing", SK.observed_proof() is None
          and set(SK.missing_live_proof()) >= {"what", "why_it_is_missing"})

    SK.KEY_ROLE_FILE = declare("LIVE", SK.K.MODEL, SK.K.RUNTIME_MODEL_ID)
    try:
        check("seat/NEGATIVE the model under test may not own this key",
              any("under test" in p for p in SK.role_problems()),
              json.dumps(SK.role_problems())[:220])
    finally:
        SK.KEY_ROLE_FILE = real
    for field, value, label in (("effort", "TEST-not-high", "a changed effort"),
                                ("disallowedTools", [], "an emptied tool policy"),
                                ("max_output_tokens", 1, "a shrunken output limit"),
                                ("kind", "TEST-not-a-kind", "an unknown kind")):
        SK.KEY_ROLE_FILE = (declare(value, "TEST-declared-key-owner")
                            if field == "kind" else
                            declare("LIVE", "TEST-declared-key-owner",
                                    **{field: value}))
        try:
            check("seat/NEGATIVE %s refuses" % label, SK.role_problems() != [],
                  json.dumps(SK.role_problems())[:160])
        finally:
            SK.KEY_ROLE_FILE = real

    SK.KEY_ROLE_FILE = declare("TEST", "TEST-declared-key-owner")
    try:
        check("seat/POSITIVE CONTROL a well-formed TEST role is accepted",
              SK.role_problems() == [], json.dumps(SK.role_problems())[:200])
        text = SK.render_launcher(SK.tasks()[0])
        check("seat/a request renders from the DECLARATION alone",
              "TEST-declared-key-owner" in text
              and json.dumps(SK.K.MODEL) not in text,
              "%d bytes" % len(text.encode()))
        check("seat/NO BOOTSTRAP DEADLOCK: rendering needed no completed call",
              SK.observed_proof() is None)
        check("seat/a TEST binding may never publish a real call",
              SK.prepare_run(os.path.join(TMP, "TEST_run"))["problems"] != []
              and SK.prepare_run(os.path.join(TMP, "TEST_run"),
                                 test_binding=True)["problems"] != [],
              "refused against the real package even as a test binding")
    finally:
        SK.KEY_ROLE_FILE = real
    check("seat/the tested Sonnet role is identical after every operation",
          SK.sonnet_role_untouched() == SONNET,
          "hard review still %s/%s" % (SK.K.MODEL, SK.K.EFFORT))
    check("seat/the hard reviewers stay two blind calls on the tested role",
          SK.hard_review_plan()["blinds_per_task"] == list(SK.HR.BLINDS)
          and "Sonnet" in SK.hard_review_plan()["model"])


# ------------------------------------------------------ the wired lifecycle --
def test_lifecycle():
    real = SK.KEY_ROLE_FILE
    SK.KEY_ROLE_FILE = declare("TEST", "TEST-declared-key-owner")
    pkg = fresh("package")
    try:
        SK.build(pkg)
        check("lifecycle/the package re-derives from the live owners",
              SK.package_problems(pkg) == [],
              json.dumps(SK.package_problems(pkg)[:2]))
        rec = SK.expected_receipt(os.path.join(TMP, "run"), package=pkg)
        check("lifecycle/the locked owner writes this door's typed expectation",
              rec["door"] == SK.DOOR and rec["phase"] == "events"
              and len(rec["prompts"]) == len(SK.tasks())
              and rec["transport"]["model_alias"] == "TEST-declared-key-owner"
              and rec["states"] == [],
              "door=%s prompts=%d" % (rec["door"], len(rec["prompts"])))
        run = os.path.join(TMP, "run")
        got = SK.prepare_run(run, package=pkg, test_binding=True)
        check("lifecycle/prepare publishes one request per event, in order",
              got["ok"] and len(got["invocations"]) == len(SK.tasks())
              and [i["label"] for i in got["invocations"]]
              == [t["source_id"] for t in SK.tasks()],
              json.dumps(got["problems"])[:200])
        check("lifecycle/every published request is a written script file",
              all(os.path.isfile(i["scriptPath"])
                  and SK.K._sha(SK.K._read(i["scriptPath"]))
                  == i["script_sha256"] for i in got["invocations"]))
        check("lifecycle/NEGATIVE a second prepare into the same directory "
              "refuses", not SK.prepare_run(run, package=pkg,
                                            test_binding=True)["ok"])
        plan = SK.resume_plan(run, package=pkg)
        check("lifecycle/resume shows every label still owed and none served",
              plan["published"] and plan["served"] == []
              and len(plan["owed"]) == len(SK.tasks()),
              "owed=%d served=%d" % (len(plan["owed"]), len(plan["served"])))
        out = SK.finalize(run, package=pkg)
        check("lifecycle/finalize runs raw-first over an empty run and keeps "
              "every label visible",
              isinstance(out, dict)
              and os.path.isdir(os.path.join(run, "raw")),
              json.dumps(sorted(out))[:200] if isinstance(out, dict) else str(out))
        # FOREIGN ROLE: a real state recorded on the TESTED role is refused
        state = _one_official_state()
        if state:
            bad = SK.record_state(run, state)
            proved, problems = SK.run_evidence(
                run, SK.K._load(os.path.join(run, SK.K.RECEIPT_NAME)),
                package=pkg)
            check("lifecycle/NEGATIVE a foreign-role state cannot serve a "
                  "label", bool(problems) and not [
                      lab for lab, v in proved.items() if v[0] == "proved"],
                  json.dumps((bad or problems)[:1])[:220])
        else:
            check("lifecycle/NEGATIVE a foreign-role state cannot serve a "
                  "label", False, "no official state was available to test with")
        plan2 = SK.resume_plan(run, package=pkg)
        check("lifecycle/a refused state serves nothing and repeats nothing",
              plan2["served"] == [] and plan2["never_repeat"] == [])
    finally:
        SK.KEY_ROLE_FILE = real
    check("lifecycle/the tested Sonnet role is still identical",
          SK.sonnet_role_untouched() == SONNET)


def _one_official_state():
    import glob
    for q in sorted(glob.glob("/home/faisal/.claude/projects/*/*/workflows/"
                              "*.json")):
        try:
            d = json.loads(io.open(q, encoding="utf-8").read())
        except Exception:                             # noqa: BLE001
            continue
        rows = [r for r in (d.get("workflowProgress") or [])
                if r.get("type") == "workflow_agent"]
        if len(rows) == 1 and d.get("status") == "completed" \
                and rows[0].get("toolCalls") == 0 and rows[0].get("agentType"):
            return q
    return None


# ------------------------- the parser, the accounting and the signing checks --
def _fact(name, state="reported", rich=False):
    item = collections.OrderedDict([("driver_name", name),
                                    ("driver_state", state)])
    if rich:
        # SOURCE-GROUNDED, and nothing more: the quantity the frozen quote
        # states, in the slot shape the production owner requires, with the
        # verbatim span it was read from. No period is invented, because the
        # quote states none.
        slot = collections.OrderedDict([("value", -0.58),
                                        ("scale_multiplier", 1),
                                        ("unit_scale_evidence", "$ (0.58)")])
        item.update([("level_low", slot), ("level_high", dict(slot)),
                     ("level_unit", "usd"),
                     ("measurement_raw_spans", ["$ (0.58)"])])
        return collections.OrderedDict([
            ("fact_type", "metric"), ("per_x", "share"), ("item", item)])
    return collections.OrderedDict([
        ("fact_type", "metric"), ("per_x", None), ("item", item)])


RICH = [False]


def _shard(task, facts_for=None, groups_null=True, issues=None, **over):
    """A TEST reply. `facts_for` maps a row index to a list of (name, reference)."""
    facts_for = facts_for or {}
    rows, review = [], []
    for n, pid in enumerate(task["rows"]):
        got = facts_for.get(n, [])
        rows.append(collections.OrderedDict([
            ("row_index", n + 1),
            ("settled", collections.OrderedDict([
                ("source_id", task["source_id"]),
                ("facts", [_fact(name, rich=RICH[0]) for name, _ref in got]),
                ("abstentions", [] if got else [
                    {"reason": "TEST fixture: this control emits no fact"}]),
                ("continuity_hints", [])])),
            ("final_outcome", "fact" if got else "exclusion"),
            ("record_kind_note", "TEST fixture: settled from the source alone")]))
        for i, (_name, ref) in enumerate(got):
            review.append(collections.OrderedDict([
                ("row_index", n + 1), ("fact_index", i), ("hard_classes", []),
                ("du_worthy", True),
                ("gold_extra", {"expectation_comparison_present": False}),
                ("ambiguity_note", None), ("reference_name", ref)]))
    doc = collections.OrderedDict([
        ("source_id", task["source_id"]), ("rows", rows), ("review", review),
        ("groups", [collections.OrderedDict([
            ("member_row_indexes", [task["rows"].index(m) + 1 for m in members]),
            ("members_are_one_fact", None if groups_null else False),
            ("reason", "TEST fixture")])
            for members in task["groups"].values()]),
        ("lead_reconciliation", []), ("open_issues", issues or [])])
    doc.update(over)
    return json.dumps(doc, indent=1)


def test_parser_accounting_and_signing():
    tasks = SK.tasks()
    one = tasks[0]
    rows = dict(SK.inventory())
    pid = one["rows"][0]
    quote = rows[pid]["quote"]
    ref = rows[pid]["raw_label_or_claim"]
    check("facts/the TEST reference is a verbatim span of the frozen quote",
          ref in quote, "%r in %r" % (ref[:40], quote[:60]))

    text = _shard(one, facts_for={0: [(ref, ref)]})
    obj, bad = SK.read_shard(text, one)
    check("facts/POSITIVE CONTROL a source-grounded TEST fact is accepted",
          obj is not None and not bad, json.dumps(bad[:2])[:300])
    if obj is None:
        return
    got = obj["rows"][pid]["facts"][0]
    flat = json.dumps(got, default=str)
    check("facts/the accepted fact keeps its own source binding",
          quote in flat and rows[pid]["part_ref"] in flat,
          "fact keys %s" % json.dumps(sorted(got))[:200])

    shards = collections.OrderedDict()
    for t in tasks:
        o, why = SK.read_shard(
            _shard(t, facts_for={0: [(ref, ref)]} if t is one else None), t)
        if o is None:
            check("facts/every event has a lawful TEST shard", False,
                  "%s: %s" % (t["source_id"], why[:1]))
            return
        shards[t["source_id"]] = o
    key, sidecar, problems = SK.materialize(shards)
    check("facts/POSITIVE CONTROL the key materializes with a real fact",
          not problems and len(sidecar["packet_to_gold"]) == len(SK.inventory()),
          "%d rows, %d problems" % (len(sidecar["packet_to_gold"]),
                                    len(problems)))
    c = SK.counts(key, sidecar)
    check("facts/the locked counts see the accepted fact and its gold fields",
          c["accepted_facts"] == 1 and c["du_worthy_facts"] == 1
          and len(sidecar["review_rows"]) == 1
          and sidecar["review_rows"][0]["packet_id"] == pid,
          json.dumps({k: c[k] for k in ("accepted_facts", "du_worthy_facts",
                                        "rows_accounted", "controls",
                                        "exclusions", "abstentions")}))
    gate = SK.signing_checks(shards)
    check("signing/an unresolved outcome stops the gate on its owed blind "
          "readings", not gate["ok"] and gate["unresolved"]
          and gate["owed_blind_readings"]
          and all(u["kind"] in ("unsettled_group", "open_issue")
                  for u in gate["unresolved"]),
          json.dumps(gate["stops"][:2])[:260])
    settled = collections.OrderedDict()
    for t in tasks:
        o, why = SK.read_shard(
            _shard(t, facts_for={0: [(ref, ref)]} if t is one else None,
                   groups_null=False), t)
        if o is None:
            check("signing/every event has a settled TEST shard", False,
                  "%s: %s" % (t["source_id"], why[:1]))
            return
        settled[t["source_id"]] = o
    gate = SK.signing_checks(settled)
    check("signing/with nothing unresolved the gate reaches the live floors "
          "and still refuses",
          not gate["ok"] and not gate["owed_blind_readings"]
          and any("floor" in x for x in gate["stops"]),
          json.dumps(gate["stops"][:2])[:300])
    shards = settled

    # the negatives that must never reach a signature
    missing = collections.OrderedDict(shards)
    missing.pop(tasks[1]["source_id"])
    check("signing/NEGATIVE a missing event cannot be signed",
          not SK.signing_checks(missing)["ok"],
          json.dumps(SK.signing_checks(missing)["stops"][:1])[:200])
    drift = collections.OrderedDict(shards)
    drift[tasks[1]["source_id"]] = shards[tasks[2]["source_id"]]
    check("signing/NEGATIVE a drifted event cannot be signed",
          not SK.signing_checks(drift)["ok"])
    dup_text = _shard(one, facts_for={0: [(ref, ref), (ref, ref)]},
                      groups_null=False)
    dup, why = SK.read_shard(dup_text, one)
    if dup is not None:
        d = collections.OrderedDict(shards)
        d[one["source_id"]] = dup
        stops = SK.signing_checks(d)["stops"]
        check("signing/NEGATIVE an exact duplicate fact cannot be signed",
              any("repeats an earlier fact" in x or "duplicate" in x
                  for x in stops), json.dumps(stops[:2])[:300])
    else:
        check("signing/NEGATIVE an exact duplicate fact cannot be signed",
              True, "the locked reader refused it first: %s" % why[:1])
    issue = collections.OrderedDict(shards)
    o, _w = SK.read_shard(
        _shard(one, facts_for={0: [(ref, ref)]}, groups_null=False,
               issues=[{"what": "TEST open issue", "why": "TEST"}]), one)
    if o is not None:
        issue[one["source_id"]] = o
        g = SK.signing_checks(issue)
        check("signing/NEGATIVE an open issue cannot be signed",
              not g["ok"] and (any("open issue" in x for x in g["stops"])
                               or g["owed_blind_readings"]),
              json.dumps(g["stops"][:2])[:260])
    promoted = _shard(one, facts_for={0: [(ref, ref)]}, groups_null=True)
    check("signing/NEGATIVE an invalid reply is refused by the locked reader",
          SK.read_shard("TEST: not a reply", one)[1] != []
          and SK.read_shard(_shard(one, source_id="TEST_OTHER"), one)[1] != [])
    del promoted


def test_codex_1990_reproductions():
    """Codex SEQ 1990's four demonstrated gaps, as this door's own red tests."""
    real = SK.KEY_ROLE_FILE
    pkg = fresh("package1990")
    SK.KEY_ROLE_FILE = declare("TEST", "TEST-independent-key",
                               "TEST-independent-runtime")
    try:
        # 1. the declared runtime must survive the read AND the binding
        got = SK.key_role()
        check("1990/the declared runtime survives the declaration read",
              got.get("runtime_model_id") == "TEST-independent-runtime",
              "read back %r" % got.get("runtime_model_id"))
        with SK._key_role_binding():
            effective = SK.K.RUNTIME_MODEL_ID
        check("1990/the binding serves the declared runtime, never the tested "
              "one", effective == "TEST-independent-runtime",
              "effective %r" % effective)
        SK.KEY_ROLE_FILE = declare("TEST", "TEST-independent-key",
                                   SK.K.RUNTIME_MODEL_ID)
        check("1990/NEGATIVE the tested runtime is refused whatever the alias",
              SK.role_problems() != [],
              json.dumps(SK.role_problems())[:200])
        SK.KEY_ROLE_FILE = declare("TEST", "TEST-independent-key",
                                   "TEST-independent-runtime")

        # 2. the public finalizer must complete the parser callback
        SK.build(pkg)
        run = os.path.join(TMP, "run1990")
        prep = SK.prepare_run(run, package=pkg, test_binding=True)
        first = SK.tasks()[0]
        label = first["source_id"]
        rows = dict(SK.inventory())
        ref = rows[first["rows"][0]]["raw_label_or_claim"]
        RICH[0] = True
        text = _shard(first, facts_for={0: [(ref, ref)]})
        RICH[0] = False
        _o, _why = SK.read_shard(text, first)
        check("1990/POSITIVE the richer source-grounded fact parses",
              _o is not None and not _why, json.dumps(_why[:3])[:400])
        state = os.path.join(TMP, "TEST_state.json")
        io.open(state, "w", encoding="utf-8").write(json.dumps(
            {"result": {"text": text},
             "workflowProgress": [{"type": "workflow_agent", "label": label}]}))
        SK.record_state(run, state)
        real_run = SK.F.run_evidence
        SK.F.run_evidence = lambda *a, **k: (
            collections.OrderedDict([(label, ("proved", "", text))]), [])
        try:
            try:
                fin = SK.finalize(run, package=pkg)
                raised = None
            except Exception as exc:                  # noqa: BLE001
                fin, raised = None, repr(exc)[:200]
            rows = {r[0]: r[1] for r in (fin or {}).get("outcomes") or []}
            check("1990/the public finalizer completes its parser callback",
                  raised is None and rows.get(label) == "valid",
                  raised or json.dumps(rows.get(label))[:200])
            check("1990/raw bytes are saved before any parse",
                  os.path.isfile(os.path.join(run, "raw",
                                              "TEST_state.raw.json")))
            if fin is not None:
                got = SK.accepted_shards(run, package=pkg)
                check("1990/accepted_shards reads the same accepted result",
                      label in got[0], json.dumps(got[2][:2])[:200])
        finally:
            SK.F.run_evidence = real_run

        # 3. resume must not credit transport-proved bytes that do not parse
        run2 = os.path.join(TMP, "run1990b")
        SK.prepare_run(run2, package=pkg, test_binding=True)
        SK.record_state(run2, state)
        SK.F.run_evidence = lambda *a, **k: (
            collections.OrderedDict([(label, ("proved", "", "TEST not JSON"))]),
            [])
        try:
            plan = SK.resume_plan(run2, package=pkg)
            check("1990/NEGATIVE proved-but-unparseable bytes are not served",
                  label not in plan["served"] and label in plan["retryable"],
                  json.dumps({k: plan[k] for k in ("served", "retryable")})[:220])
        finally:
            SK.F.run_evidence = real_run
        # A HAND-WRITTEN CLOSEOUT EARNS NOTHING. Codex SEQ 1991 stopped the
        # work because my earlier expectation here required the opposite: his
        # synthetic closeout was built to show a field-shape mismatch, never to
        # certify a completed call, and believing it credited 33 results from a
        # receipt that recorded none. The genuine positive control runs through
        # the real lifecycle instead, in unit_1992/ledger/lifecycle_1992.py.
        done = fresh("finalized1992")
        rec = SK.expected_receipt(done, package=pkg)
        io.open(os.path.join(done, SK.K.RECEIPT_NAME), "w",
                encoding="utf-8").write(json.dumps(rec, indent=1))
        os.makedirs(os.path.join(done, "raw"), exist_ok=True)
        io.open(os.path.join(done, "raw", "TEST_state.raw.json"), "w",
                encoding="utf-8").write(text)
        io.open(os.path.join(done, SK.K.FINALIZATION_NAME), "w",
                encoding="utf-8").write(json.dumps({
                    "door": SK.DOOR, "phase": "events", "attempt": 1,
                    "run_id": rec["run_id"],
                    "receipt_sha256": SK.INV.sha_file(
                        os.path.join(done, SK.K.RECEIPT_NAME)),
                    "manifest_sha256": rec["manifest_sha256"],
                    "bound": rec["bound"],
                    "harvested_raw": ["TEST_state.raw.json"],
                    "phase_complete": False, "problems": [], "retry": [],
                    "outcomes": [[x, "valid" if x == label else "missing", ""]
                                 for x in rec["allowed"]]}, indent=1))
        plan = SK.resume_plan(done, package=pkg)
        check("1992/NEGATIVE a hand-written closeout earns no credit",
              plan["served"] == [] and len(plan["owed"]) == len(SK.tasks())
              and any("its own evidence does not" in p
                      for p in plan["problems"]),
              json.dumps({"served": plan["served"],
                          "problems": plan["problems"][:2]})[:320])
        check("1992/the receipt of that closeout records no call at all",
              (SK.K._load(os.path.join(done, SK.K.RECEIPT_NAME)).get("states")
               or []) == [])

        # 4. the signing seam must route through the authoritative gate
        seen = []
        real_gate = SK.F.signing_gate
        SK.F.signing_gate = lambda *a, **k: (seen.append(a) or {
            "ok": False, "stops": ["TEST sentinel gate"], "counts": None})
        try:
            SK.signing_checks({})
        except Exception:                             # noqa: BLE001
            pass
        finally:
            SK.F.signing_gate = real_gate
        check("1990/signing routes through the locked gate, not a copy",
              bool(seen), "the locked signing_gate was %scalled"
              % ("" if seen else "NOT "))
    finally:
        SK.KEY_ROLE_FILE = real


def test_package_and_regression():
    pkg = fresh("package2")
    doc = SK.build(pkg)
    check("package/it writes exactly its two files",
          sorted(os.listdir(pkg)) == sorted([SK.MANIFEST_NAME, SK.PREFIX_NAME]))
    check("package/it declares itself unarmed with no arming mechanism",
          doc["armed"] is False and not hasattr(SK, "arming_problems")
          and not hasattr(SK, "ARMED_RECORD")
          and doc["budget"]["calls_made_by_this_package"] == 0)
    pre = SK.preflight(pkg)
    check("package/preflight refuses for exactly the undeclared role",
          not pre["ok"] and pre["problems"] == SK.role_problems(),
          json.dumps(pre["problems"])[:300])
    path = os.path.join(pkg, SK.MANIFEST_NAME)
    saved = io.open(path, encoding="utf-8").read()
    io.open(path, "w", encoding="utf-8").write(json.dumps(
        dict(json.loads(saved), call_order=list(reversed(doc["call_order"]))),
        indent=1))
    check("package/NEGATIVE a reordered call list is caught",
          SK.package_problems(pkg) != [])
    io.open(path, "w", encoding="utf-8").write(saved)
    check("package/the restored manifest re-derives again",
          SK.package_problems(pkg) == [])
    check("package/NEGATIVE arming one package cannot arm another",
          not hasattr(SK, "ARMED_RECORD"),
          "the mechanism Codex broke no longer exists")


def main():
    for fn in (test_population_and_prompt, test_key_role_seat, test_lifecycle,
               test_parser_accounting_and_signing,
               test_codex_1990_reproductions, test_package_and_regression):
        try:
            fn()
        except Exception as exc:                      # noqa: BLE001 - reported
            check("%s/RAISED" % fn.__name__, False,
                  "%s filename=%r" % (repr(exc)[:300],
                                      getattr(exc, "filename", None)))
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    out = collections.OrderedDict([
        ("suite", "TEST a4_source_key 1989"),
        ("owner_sha256", SK.INV.sha_file(os.path.join(OWNER,
                                                      "a4_source_key.py"))),
        ("test_sha256", SK.INV.sha_file(os.path.abspath(__file__))),
        ("checks", len(RESULTS)), ("failed", FAILED),
        ("all_passed", not FAILED), ("results", RESULTS)])
    print(json.dumps(out, indent=1, default=str))
    return 0 if not FAILED else 3


if __name__ == "__main__":
    sys.exit(main())
