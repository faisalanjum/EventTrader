# ponytail: ONE call-budget receipt from LIVE owners (Codex SEQ 1507 item 7), the 1505 receipt's
# shape with the completed second correction moved into completed_before and the third correction
# added as a stage. No total is typed: every count is read from the owner that defines it.
import collections, hashlib, io, json, os, sys
H = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import a6_launch_freeze as A6, a7_g1_build as G, a7_g23_build as GB, build_a5_exp5_kit as A5
import build_kfields_key as K, build_kfields_hard_review as HR, build_kfields_final as F
import build_launch_manifest as BLM, raw_transport as RT, a7_key_correction as KC
import build_kfields_key_targeted as T, build_kfields_hard_review_targeted as HRT, build_kfields_final_targeted as FT
OUT = "/tmp/a7_budget_receipt_1507.json"
STOPPED = "/tmp/a7_v3_prepared_run_1479"
G3 = "/tmp/a7_g3_candidate/a7_g1_candidate.json"
G2 = "/tmp/a7_g2_candidate/a7_g1_candidate.json"
G1C = "/tmp/a7_g1_event_run4/root.json"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

completed, rows = A6.ledger()
CB = FT._phase(FT.CORR_DOOR)["binding"]; CB2 = FT._phase(FT.CORR2_DOOR)["binding"]
EV3 = FT.correction_events(FT.CORR3_DOOR)
ceiling = G.CEILING
targets = T.targets()
events = collections.OrderedDict()
for pid in targets:                                  # the eight event tasks: the diff grouped by source event, in its order
    events.setdefault(pid.split("#")[0], []).append(pid)
lim = RT.a1_limits(RT.a1_plan_for_run(STOPPED))
n_events = len(BLM._events())
legs = len(A5.ACTIVE_ARM_IDS) + 1
_key, ident = KC.current_key()
g2c = json.load(io.open(G2, encoding="utf-8")); g3c = json.load(io.open(G3, encoding="utf-8"))
g1c = json.load(io.open(G1C, encoding="utf-8"))
signer_max = F.MAX_ATTEMPTS

stages = [
    collections.OrderedDict([("stage", "key_review"), ("owner", "a6_launch_freeze.ledger rows targeted_key_review_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("targeted_key_review"))), ("binding_path", T.BINDING), ("binding_sha256", sha(T.BINDING)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "hard_review"), ("owner", "a6_launch_freeze.ledger rows hard_review_targeted_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("hard_review_targeted"))), ("binding_path", HRT.BINDING), ("binding_sha256", sha(HRT.BINDING)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "final_adjudication"), ("owner", "a6_launch_freeze.ledger rows final_targeted_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_") and not r["stage"].startswith("final_targeted_correction"))), ("binding_path", FT.BINDING), ("binding_sha256", sha(FT.BINDING)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "final_correction"), ("owner", "a6_launch_freeze.ledger rows final_targeted_correction_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"] == "final_targeted_correction_primary" or r["stage"] == "final_targeted_correction_retry")), ("binding_path", CB), ("binding_sha256", sha(CB)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "final_correction_2"), ("owner", "a6_launch_freeze.ledger rows final_targeted_correction_2_* (DONE, counted in completed_before)"),
        ("actual", sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_correction_2"))), ("binding_path", CB2), ("binding_sha256", sha(CB2)),
        ("shape", 0), ("min", 0), ("max", 0)]),
    collections.OrderedDict([("stage", "final_correction_3"), ("owner", "build_kfields_final_targeted.correction_events(CORR3_DOOR): exactly the events whose accepted shard still carries an open issue after run 1506 x F.MAX_ATTEMPTS"),
        ("events", len(EV3)), ("targets", sum(len(t["rows"]) for t in FT.correction_tasks(FT.CORR3_DOOR))), ("max_attempts", F.MAX_ATTEMPTS),
        ("review_receipt", FT.CORR3_REVIEW_RECEIPT), ("review_receipt_sha256", sha(FT.CORR3_REVIEW_RECEIPT)),
        ("shape", len(EV3)), ("min", len(EV3)), ("max", len(EV3) * F.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "key_signing"), ("owner", "build_kfields_final signer x MAX_ATTEMPTS (reserved, not rendered now)"),
        ("primaries", 1), ("max_attempts", signer_max), ("shape", 1), ("min", 1), ("max", signer_max)]),
    collections.OrderedDict([("stage", "producer"), ("owner", "raw_transport.a1_limits(plan of the stopped run)"),
        ("primaries", lim["primary_calls"]), ("retry_cap", lim["retry_cap"]),
        ("shape", lim["primary_calls"]), ("min", lim["primary_calls"]), ("max", lim["all_in_max"])]),
    collections.OrderedDict([("stage", "g1"), ("owner", "a7_g1_build: one call per (leg, event) with unmatched gold, GRADER_LANES x MAX_ATTEMPTS"),
        ("legs", legs), ("events", n_events), ("lanes", len(G.GRADER_LANES)), ("max_attempts", G.MAX_ATTEMPTS),
        ("shape", len(g1c["rows"])), ("shape_artifact", G1C), ("shape_artifact_sha256", sha(G1C)),
        ("min", 0), ("max", legs * n_events * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "g2"), ("owner", "a7_g23_build.pack_batches: <= MAX_ITEMS_PER_CALL matched pairs per call, per leg, x lanes x MAX_ATTEMPTS"),
        ("accepted_key_rows", ident["accepted_rows"]), ("max_items_per_call", GB.MAX_ITEMS_PER_CALL), ("legs", legs), ("lanes", len(G.GRADER_LANES)),
        ("shape", g2c["launchers"]["count"]), ("shape_artifact", G2), ("shape_artifact_sha256", sha(G2)),
        ("min", 0), ("max", -(-ident["accepted_rows"] // GB.MAX_ITEMS_PER_CALL) * legs * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "g3"), ("owner", "a7_g23_build.pack_batches over unmatched PRODUCED records: not derivable before the producer run"),
        ("shape", g3c["launchers"]["count"]), ("questions", g3c["questions"]), ("batches", g3c["batching"]["batches"]),
        ("shape_artifact", G3), ("shape_artifact_sha256", sha(G3)),
        ("min", 0), ("max", None), ("max_note", "bounded only by the produced count, which exists after the producer run; the lawful cap is the remaining headroom")]),
]
adj = stages[5]; sig = stages[6]
closeout = collections.OrderedDict([
    ("before", completed), ("correction_after_clean", completed + adj["shape"]), ("correction_worst", completed + adj["max"]),
    ("signer_primaries", sig["primaries"]), ("signer_retry_cap", sig["max"] - sig["primaries"]),
    ("a4_closeout_clean", completed + adj["shape"] + sig["shape"]), ("a4_closeout_worst", completed + adj["max"] + sig["max"]),
    ("ceiling", ceiling), ("worst_fits_ceiling", completed + adj["max"] + sig["max"] <= ceiling)])
min_total = completed + sum(s["min"] for s in stages)
max_known = completed + sum(s["max"] for s in stages if s["max"] is not None)
expected_shape = completed + sum(s["shape"] for s in stages)
doc = collections.OrderedDict([
    ("schema", "a7_call_budget_receipt/1507"),
    ("completed_before", completed), ("completed_before_owner", "a6_launch_freeze.ledger()"),
    ("completed_rows", rows), ("ceiling", ceiling), ("ceiling_owner", "a7_g1_build.CEILING"),
    ("stages", stages), ("a4_closeout", closeout),
    ("minimum_total", min_total), ("minimum_fits_ceiling", min_total <= ceiling),
    ("expected_shape_total", expected_shape), ("expected_shape_note", "the provisional no-retry shape: primaries at the latest accepted zero-call artifacts, no retries; every stage population is re-derived by its owner after key settlement, the producer run and G1"),
    ("headroom_at_shape", ceiling - expected_shape),
    ("known_maximum_subtotal", max_known), ("known_maximum_note", "the sum of every DERIVABLE structural maximum; it is not an absolute maximum"),
    ("absolute_maximum", None), ("absolute_maximum_note", "unknown before the producer run: G3's maximum depends on the produced count"),
    ("known_maximum_fits_ceiling", max_known <= ceiling),
    ("calls_armed", 0)])
canon = json.dumps(doc, sort_keys=True, separators=(",", ":"), default=str)
doc["receipt_sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
RT.write_new(OUT, json.dumps(doc, indent=1, default=str))
print(json.dumps({k: doc[k] for k in ("completed_before", "ceiling", "minimum_total", "expected_shape_total", "headroom_at_shape", "known_maximum_subtotal", "known_maximum_fits_ceiling")}))
print("closeout:", json.dumps(closeout))
print("receipt:", doc["receipt_sha256"], OUT)
