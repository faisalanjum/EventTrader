# -*- coding: utf-8 -*-
"""STAGE 2: the G2/G3 lifecycle and the ACTUAL score consumer
(Codex SEQ 1942 item 2).

The unit_1876 contract on the CURRENT inputs: the G2/G3 candidate is derived
from THIS G1 by its own owner, both kinds go the whole native path, and the
real official_tier_decision runs ONCE.

    R.write(from THIS G1) -> write_kind -> freeze_root -> publish_run
      -> preflight -> save_results -> official TEST state -> finalize_segment
      -> whole_answers -> C.evidence -> complete_g23 -> persist_g23
      -> load_g23  ... then B.official_tier_decision, once

Differences from 1876, and nothing else: the producer, G1 and inputs are the
current ones; no historical preflight file and no repinned old candidate; the
expected event/leg population is DERIVED from the live inputs rather than
compared with a number written here.

The G2/G3 answers are explicitly UNRESOLVED at both doors - null is lawful
there and must stay unresolved: not missing, which is a refusal, and not
credited, which would manufacture a score. A false decision is a truthful TEST
result; nothing here changes a TEST meaning to make one true.
"""
import collections, hashlib, io, json, os, sys

TAG = os.environ["A7_TAG"]; ATT = os.environ["A7_ATTEMPT_DIR"]
os.makedirs(ATT, exist_ok=True)
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
RECOVERY = "/home/faisal/EventMarketDB-driver-recovery"
sys.path.insert(0, VIEW)
sys.path.insert(0, "/home/faisal/EventMarketDB")
sys.path.insert(0, RECOVERY)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CAND_KEY = os.environ["A7_CANDIDATE_DIR"]; ROOT = os.environ["A7_LIFECYCLE_ROOT"]
os.environ["A7_APPROVED_KEY_DIR"] = CAND_KEY
PROJECTS = os.path.join(ROOT, "TEST_projects")
TEST_LABEL = "SYNTHETIC_TEST_G23_UNRESOLVED_ANSWERS_NOT_QUALIFICATION"

import audit_worker_access as AUD                                 # noqa: E402
AUD.PROJECTS_ROOT = PROJECTS
io.open(S + "/a3_serial_dir.txt", "w", encoding="utf-8").write(
    os.path.join(ROOT, "a3") + "\n")
import driver.core.driver_validators as _DV                       # noqa: E402,F401
import a7_g1_build as G                                           # noqa: E402
import a7_g23_build as B                                          # noqa: E402
import a7_g23_run as R                                            # noqa: E402
import a7_g1_complete_v2 as CV                                    # noqa: E402
import a7_prepared_run as PR                                      # noqa: E402
import a7_reference_inventory as REF                              # noqa: E402
import build_a5_exp5_kit as A5                                    # noqa: E402
import g1_fake_state as FAKE                                      # noqa: E402
import fresh_target as FT                                         # noqa: E402

PRODUCER = "/tmp/a7_logs_1781/attempt_mut5/positive/run"
G1_ATT = "/tmp/a7_logs_1781/attempt_g1a"
AUDIT_ROOT = "/tmp/a7_g23_route_audit"
BENCH = S + "/bench_1306"
WORK = FT.new_dir(os.path.join(ATT, "native"))
AUDIT = FT.new_dir(os.path.join(AUDIT_ROOT, "native_" + TAG))
res = collections.OrderedDict(tag=TAG, kind="G23_NATIVE_CURRENT",
                              label=TEST_LABEL)
checks = collections.OrderedDict()


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def unresolved_reply(kind, qids):
    """The kind's own lawful reply, every answer explicitly UNRESOLVED.
    Keys and aspect names come from the OWNER, never from a list written here."""
    if kind == "G2":
        k_id, k_val = B.MEANING_REPLY_KEYS
        return json.dumps([{k_id: q,
                            k_val: {f: None for f in B.meaning_fields()}}
                           for q in qids])
    k_id, k_val = B.EXTRAS_REPLY_KEYS
    return json.dumps([{k_id: q, k_val: None} for q in qids])


def drive_kind(kind, cand_dir, doc_path):
    run_dir = os.path.join(WORK, "%s_run" % kind)
    csha = G._sha_file(doc_path)
    root, root_sha, probs = G.freeze_root(cand_dir, run_dir, csha)
    if probs:
        return {"freeze_root": [str(p)[:150] for p in probs[:2]]}
    lanes = [r["lane_id"] for r in root["rows"]]
    ident, probs = G.publish_run(cand_dir, run_dir, root_sha, lanes)
    if probs:
        return {"publish": [str(p)[:150] for p in probs[:2]]}
    n, rec = ident["segment"], ident["receipt_sha256"]
    packet, probs = G.preflight(cand_dir, run_dir, n, root_sha, rec)
    if probs:
        return {"preflight": [str(p)[:150] for p in probs[:2]]}
    receipt = G.load_receipt(run_dir, n)
    kdoc = G._read(doc_path)
    binding, _parser = G.binding_and_parser(kind)
    rows, answers = [], {}
    for arg in packet["args"]:
        bound = binding(kdoc, arg["batch_id"])
        qids = [q["question_id"] if isinstance(q, dict) else q
                for q in bound["question_ids"]]
        text = unresolved_reply(kind, qids)
        row = collections.OrderedDict((f, arg.get(f)) for f in G.RESULT_BINDING)
        row["invocation_sha256"] = receipt["invocation_sha256"]
        row["text"] = text
        row["error"] = None
        rows.append(row)
        answers[arg["lane_id"]] = text
    acc, probs = G.save_results(run_dir, n, rows, root_sha, rec)
    if probs:
        return {"save": [str(p)[:150] for p in probs[:2]]}
    before = getattr(AUD, "PROJECTS_ROOT", None)
    try:
        st = FAKE.build(os.path.dirname(run_dir), run_dir, n, G,
                        answers=answers, errors={})
        probs = G.record_official_state(run_dir, n, st, root_sha, rec)
        if probs:
            return {"state": [str(p)[:150] for p in probs[:2]]}
        final, rulings, probs = G.finalize_segment(cand_dir, run_dir, n,
                                                   root_sha, rec)
    finally:
        AUD.PROJECTS_ROOT = before
    if final is None:
        return {"finalize": [str(p)[:150] for p in (probs or [])[:2]]}
    whole, whole_probs = G.whole_answers(run_dir, n)
    if whole_probs or whole is None:
        return {"whole_answers": [str(p)[:160] for p in (whole_probs or [])[:2]]}
    ident23 = CV.g23_identity(root_sha, run_dir)
    _r, cdoc, lanes_rec, ev_probs = CV.evidence(
        cand_dir, run_dir, root_sha, ident23.get("run_digest"),
        ident23.get("run_files"))
    if ev_probs:
        return {"evidence": [str(p)[:160] for p in ev_probs[:2]]}
    result, cprobs = CV.complete_g23(cdoc, CV.relations_from_run(lanes_rec),
                                     ident23)
    if cprobs:
        return {"complete": [str(p)[:160] for p in cprobs[:2]]}
    comp_path, comp_sha = CV.persist_g23(cand_dir, result)
    reloaded = CV.load_g23(cand_dir, comp_sha, root_sha, run_dir)
    FT.new_file(os.path.join(WORK, "%s_saved.json" % kind),
                json.dumps({"raw_replies": answers, "whole_answers": whole,
                            "completion": result}, indent=1, default=str))
    return {"segment": n, "root_sha256": root_sha, "run_dir": run_dir,
            "receipt_sha256": rec, "completion_sha256": comp_sha,
            "lanes": len(lanes), "retry": len(final.get("retry") or []),
            "uncalled": len(final.get("uncalled") or []),
            "whole_lanes": len(whole),
            "credited": len(result.get("credited") or {}),
            "unresolved": len(result.get("unresolved") or []),
            "reload_matches": G._plain(reloaded) == G._plain(result)}


SC = os.path.join(VIEW, "scorers", "score_exp5_current.py")
B.bind_grading_scorer(SC, sha(SC))
run = PR.load(PRODUCER)
g1 = json.load(io.open(os.path.join(G1_ATT, "G1_PINS_g1a.json"),
                       encoding="utf-8"))
g1 = {"candidate_dir": g1["candidate_dir"], "run_dir": g1["run_dir"],
      "pins": g1["pins"]}
res["reused_g1"] = {"candidate_dir": g1["candidate_dir"],
                    "run_dir": g1["run_dir"],
                    "root_sha256": g1["pins"]["root_sha256"]}
res["producer_run_dir"] = run["run_dir"]

REF.INVENTORY_PATH = os.path.join(WORK, "candidate_reference_inventory.json")
REF.write(REF.expected_document(run), REF.INVENTORY_PATH)
REF.validate(REF.INVENTORY_PATH, run)
res["reference_inventory"] = sha(REF.INVENTORY_PATH)

MANIFEST = os.path.join(PRODUCER, "plan", "a5_exp5_reader.manifest.json")
inputs = B.load_verified_inputs(MANIFEST, run, BENCH)
res["inputs"] = {"manifest_sha256": sha(MANIFEST), "n": len(inputs)}

# ---- the CURRENT G2/G3 candidate, derived from THIS G1 by its own owner ---
cand_dir = FT.new_dir(os.path.join(WORK, "g23_candidate"))
# `primary` is the prepared-run IDENTITY, not a path - the owner refuses a
# bare path on purpose, which is the same binding rule G.run_of enforces.
cpath, cprobs = R.write(cand_dir, primary=run, g1=g1, inputs=inputs,
                        audit_root=AUDIT)
res["g23_write_problems"] = [str(p)[:170] for p in (cprobs or [])[:3]]
checks["1_the_G23_candidate_is_derived_from_this_G1"] = (
    cpath is not None and not cprobs)
if cpath is not None and not cprobs:
    cand_doc = G._read(cpath)
    res["g23_candidate_sha256"] = sha(cpath)
    res["g23_made_calls"] = cand_doc.get("made_calls")
    want_id = B.g1_identity(g1)
    res["g23_g1_identity"] = cand_doc.get("g1_identity")
    checks["2_the_candidate_belongs_to_that_exact_G1"] = (
        cand_doc.get("g1_identity") == want_id and cand_doc.get("made_calls") == 0)
    pdir = os.path.join(cand_dir, R.PROMPT_DIRNAME)
    prompts = {f[:-len(".prompt.txt")]:
               io.open(os.path.join(pdir, f), encoding="utf-8").read()
               for f in os.listdir(pdir) if f.endswith(".prompt.txt")}
    res["g23_prompts"] = len(prompts)
    _key, identity = G.live_key()

    # THE REQUIRED POPULATION, from the owner that computes it - not inferred
    # from a publish error. The G1 TEST answers deliberately link NOTHING, so
    # if the G2/G3 obligations derived from that lifecycle are empty, empty is
    # the truthful accounting and no question may be manufactured to fill it
    # (Codex SEQ 1942 item 2).
    g2p, g3p, arms, gold, pmeta, pprobs, unroutable, derived = R.populations(
        primary=run, audit_root=AUDIT, g1=g1)
    res["populations"] = collections.OrderedDict([
        ("g2_keys", len(g2p)),
        ("g2_pairs", sum(len(v) for v in g2p.values())),
        ("g3_keys", len(g3p)),
        ("g3_obligations", sum(len(v) for v in g3p.values())),
        ("arms", sorted(arms) if hasattr(arms, "__iter__") else None),
        ("gold_events", len(gold) if hasattr(gold, "__len__") else None),
        ("problems", [str(x)[:150] for x in (pprobs or [])[:3]]),
        ("unroutable", len(unroutable or [])),
        ("resolutions", len((derived or {}).get("resolutions") or {}))])
    res["population_is_empty"] = (res["populations"]["g2_pairs"] == 0
                                  and res["populations"]["g3_obligations"] == 0)
    checks["3_the_required_population_is_derived_by_its_owner"] = (
        not pprobs and res["populations"]["resolutions"] > 0)

    kinds = collections.OrderedDict()
    for kind in ("G2", "G3"):
        out_dir = FT.new_dir(os.path.join(WORK, "%s_cand" % kind))
        kpath, _ks = R.write_kind(out_dir, kind, cand_doc, prompts, identity)
        kdoc = G._read(kpath)
        # THE FIELD THE SCHEMA OWNS. a7_g23_run.kind_candidate
        # publishes the batches as `batch_rows`; the only top-level
        # `rows` in that document is inside `launchers`, so the old
        # lookup was always None and called every kind empty. It is
        # subscripted, not defaulted: a missing required field is a
        # refusal, never an empty population (Codex SEQ 1943).
        rows = kdoc["batch_rows"]
        if not rows:
            # EMPTY IS THE ANSWER, and it is accounted rather than forced.
            kinds[kind] = {"lanes": 0, "empty_population": True,
                           "candidate_sha256": G._sha_file(kpath)}
            continue
        kinds[kind] = drive_kind(kind, out_dir, kpath)
    res["kinds"] = kinds
    all_empty = all(k.get("empty_population") for k in kinds.values())
    res["both_kinds_empty"] = all_empty
    checks["4_each_kind_is_either_completed_or_accounted_empty"] = all(
        k.get("empty_population") is True
        or (k.get("completion_sha256") and k.get("reload_matches")
            and k.get("retry") == 0 and k.get("uncalled") == 0)
        for k in kinds.values())

    if checks["4_each_kind_is_either_completed_or_accounted_empty"]:
        # THE EXPECTED POPULATION, DERIVED from the live inputs
        legs = list(A5.ACTIVE_ARM_IDS) + [G.LEG_UNION]
        events = sorted({r["source_id"] for r in
                         REF.read(REF.INVENTORY_PATH)["rows"]}) \
            if False else sorted(G.gold_by_event()[0])
        res["derived"] = {"events": len(events), "legs": len(legs),
                          "expected_event_leg_routes": len(events) * len(legs)}

        counts = collections.Counter()
        seen_routes, seen_completions = set(), set()
        real_refuse, real_route, real_load = B.refuse, B.route_for, CV.load_g23

        def c_refuse(*a, **k):
            counts["g1_validation"] += 1
            return real_refuse(*a, **k)

        def c_route(arm_by_event, audit_dir, groups_by_sid=None):
            counts["event_leg_routes"] += 1
            for sid in arm_by_event:
                seen_routes.add((os.path.basename(audit_dir), sid))
            return real_route(arm_by_event, audit_dir, groups_by_sid)

        def c_load(out_dir, expect_sha, root_sha, run_dir):
            counts["completion_loads"] += 1
            seen_completions.add(expect_sha)
            return real_load(out_dir, expect_sha, root_sha, run_dir)

        # WHAT EACH LEG ACTUALLY OBLIGES, derived from the populations the
        # owner returned. Handing both kinds to every leg is what the consumer
        # refused with "this leg obliges grader evidence for nothing; missing
        # [], extra ['G2','G3']" - and it was right: with no-link G1 answers
        # nothing is obliged, so the truthful input is no grader source. This
        # derives the set per leg instead of always passing both; it does not
        # change any TEST meaning to make a decision come out true.
        def obliged(leg):
            out = {}
            if any(k.split("|", 1)[0] == leg and v for k, v in g2p.items()):
                out["G2"] = True
            if any(k.split("|", 1)[0] == leg and v for k, v in g3p.items()):
                out["G3"] = True
            return sorted(out)

        sources_by_leg = collections.OrderedDict()
        res["obliged_kinds_by_leg"] = {}
        for leg in legs:
            want = obliged(leg)
            res["obliged_kinds_by_leg"][leg] = want
            sources_by_leg[leg] = {
                k: {"run_dir": kinds[k].get("run_dir"),
                    "root_sha256": kinds[k].get("root_sha256"),
                    "completion_sha256": kinds[k].get("completion_sha256")}
                for k in want}

        B.refuse, B.route_for, CV.load_g23 = c_refuse, c_route, c_load
        try:
            decisions, results = B.official_tier_decision(run, sources_by_leg,
                                                          AUDIT, g1)
            failure = None
        except BaseException as exc:                  # noqa: BLE001 - by design
            decisions, results, failure = None, None, "%s: %s" % (
                type(exc).__name__, str(exc)[:400])
        finally:
            B.refuse, B.route_for, CV.load_g23 = (real_refuse, real_route,
                                                  real_load)
        res["tier"] = collections.OrderedDict([
            ("failure", failure), ("decisions", decisions),
            ("counts", dict(counts)),
            ("distinct_event_leg_routes", len(seen_routes)),
            ("distinct_completions", sorted(seen_completions))])
        res["score_objects"] = results
        FT.new_file(os.path.join(WORK, "SCORE_OBJECTS.json"),
                    json.dumps({"decisions": decisions, "results": results},
                               indent=1, default=str))
        checks["5_the_tier_decision_returns_both_claims"] = (
            failure is None and decisions is not None
            and sorted(decisions) == sorted(A5.ACTIVE_ARM_IDS))
        checks["6_three_whole_score_objects_are_returned"] = (
            results is not None and sorted(results) == sorted(legs)
            and all(r is not None for r in results.values()))
        checks["7_the_lifecycle_is_validated_exactly_once"] = (
            counts.get("g1_validation") == 1)
        checks["8_every_derived_event_leg_route_happened_exactly_once"] = (
            len(seen_routes) == res["derived"]["expected_event_leg_routes"]
            and counts.get("event_leg_routes")
            == res["derived"]["expected_event_leg_routes"])
        # With an empty population there is no completion to load, and that
        # is accounted rather than asserted away.
        want_comp = {k["completion_sha256"] for k in kinds.values()
                     if k.get("completion_sha256")}
        checks["9_every_existing_completion_is_loaded_exactly_once"] = (
            seen_completions == want_comp
            and counts.get("completion_loads", 0) == len(want_comp))

for k in ("inputs", "g23_prompts", "g23_made_calls", "populations",
          "population_is_empty", "kinds", "obliged_kinds_by_leg",
          "derived", "tier"):
    if k in res:
        print("  %-20s %s" % (k, json.dumps(res[k], default=str)[:150]))

res["checks"] = checks
ok = bool(checks) and all(checks.values())
res["all_green"] = ok
io.open(os.path.join(ATT, "G23_%s.json" % TAG), "w",
        encoding="utf-8").write(json.dumps(res, indent=2, default=str) + "\n")
print("%d/%d -> %s" % (sum(1 for v in checks.values() if v), len(checks), ok))
for k, v in checks.items():
    print("  %s %s" % ("GREEN" if v else "RED  ", k))
sys.exit(0 if ok else 1)
