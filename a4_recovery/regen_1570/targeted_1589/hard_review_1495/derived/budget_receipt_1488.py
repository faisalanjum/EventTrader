# ponytail: ONE call-budget receipt from LIVE owners (Codex SEQ 1487 item 5).
# No total is typed: every count is read from the owner that defines it, and
# every structural maximum is a product of owner constants. G1/G2/G3 expected
# shapes are read from the frozen zero-call artifacts on disk, by hash.
import collections, hashlib, io, json, os, sys
H = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import a6_launch_freeze as A6, a7_g1_build as G, a7_g23_build as GB, build_a5_exp5_kit as A5
import build_kfields_key as K, build_kfields_hard_review as HR, build_kfields_final as F
import build_launch_manifest as BLM, raw_transport as RT, a7_key_correction as KC
import build_kfields_key_targeted as T
OUT = "/tmp/a7_budget_receipt_1488.json"
V2 = os.path.join(H, "..", "one_item_benchmark_inventory.v2_1487.json")
STOPPED = "/tmp/a7_v3_prepared_run_1479"
G3 = "/tmp/a7_g3_candidate/a7_g1_candidate.json"     # latest accepted G3: 357 questions, 46 batches, 92 calls
G2 = "/tmp/a7_g2_candidate/a7_g1_candidate.json"     # latest accepted G2: 140 questions, 17 batches, 34 calls
G1C = "/tmp/a7_g1_event_run4/root.json"          # the event-scoped G1 run: 210 root lanes, 7 finalized segments
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

completed, rows = A6.ledger()
ceiling = G.CEILING
targets = T.targets(V2)
lim = RT.a1_limits(RT.a1_plan_for_run(STOPPED))
events = len(BLM._events())
legs = len(A5.ACTIVE_ARM_IDS) + 1                 # P1, P2 and UNION
_key, ident = KC.current_key()
g2c = json.load(io.open(G2, encoding="utf-8")); g3c = json.load(io.open(G3, encoding="utf-8"))
g1c = json.load(io.open(G1C, encoding="utf-8"))
g1_lanes_shape = len(g1c["rows"])
g2_shape = g2c["launchers"]["count"]
g3_shape = g3c["launchers"]["count"]

stages = [
    collections.OrderedDict([("stage", "key_review"), ("owner", "build_kfields_key_targeted.targets x build_kfields_key.MAX_ATTEMPTS"),
        ("primaries", len(targets)), ("max_attempts", K.MAX_ATTEMPTS),
        ("shape", len(targets)), ("min", len(targets)), ("max", len(targets) * K.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "hard_review"), ("owner", "build_kfields_hard_review: tasks are structural (unresolved / neither draft / exact-locator group); BLINDS x MAX_ATTEMPTS"),
        ("tasks_max", len(targets)), ("exact_locator_groups_among_targets", len(targets) - len({(r["source_id"], r["part_ref"], r["quote"]) for r in [json.load(io.open(V2, encoding="utf-8"))["records"][int(p.rsplit("#", 1)[1])] for p in targets]})),
        ("blinds", len(HR.BLINDS)), ("max_attempts", HR.MAX_ATTEMPTS),
        ("shape", 0), ("min", 0), ("max", len(targets) * len(HR.BLINDS) * HR.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "key_signing"), ("owner", "build_kfields_final signer x MAX_ATTEMPTS"),
        ("primaries", 1), ("max_attempts", F.MAX_ATTEMPTS), ("shape", 1), ("min", 1), ("max", F.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "producer"), ("owner", "raw_transport.a1_limits(plan of the stopped run)"),
        ("primaries", lim["primary_calls"]), ("retry_cap", lim["retry_cap"]),
        ("shape", lim["primary_calls"]), ("min", lim["primary_calls"]), ("max", lim["all_in_max"])]),
    collections.OrderedDict([("stage", "g1"), ("owner", "a7_g1_build: one call per (leg, event) with unmatched gold, GRADER_LANES x MAX_ATTEMPTS"),
        ("legs", legs), ("events", events), ("lanes", len(G.GRADER_LANES)), ("max_attempts", G.MAX_ATTEMPTS),
        ("shape", g1_lanes_shape), ("shape_artifact", G1C), ("shape_artifact_sha256", sha(G1C)),
        ("min", 0), ("max", legs * events * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "g2"), ("owner", "a7_g23_build.pack_batches: <= MAX_ITEMS_PER_CALL matched pairs per call, per leg, x lanes x MAX_ATTEMPTS"),
        ("accepted_key_rows", ident["accepted_rows"]), ("max_items_per_call", GB.MAX_ITEMS_PER_CALL), ("legs", legs), ("lanes", len(G.GRADER_LANES)),
        ("shape", g2_shape), ("shape_artifact", G2), ("shape_artifact_sha256", sha(G2)),
        ("min", 0), ("max", -(-ident["accepted_rows"] // GB.MAX_ITEMS_PER_CALL) * legs * len(G.GRADER_LANES) * G.MAX_ATTEMPTS)]),
    collections.OrderedDict([("stage", "g3"), ("owner", "a7_g23_build.pack_batches over unmatched PRODUCED records: not derivable before the producer run"),
        ("shape", g3_shape), ("questions", g3c["questions"]), ("batches", g3c["batching"]["batches"]),
        ("shape_artifact", G3), ("shape_artifact_sha256", sha(G3)),
        ("min", 0), ("max", None), ("max_note", "bounded only by the produced count, which exists after the producer run; the lawful cap is the remaining headroom (a7_g23_run: the retry cap is headroom, not a per-row reservation)")]),
]
min_total = completed + sum(s["min"] for s in stages)
max_known = completed + sum(s["max"] for s in stages if s["max"] is not None)
expected_shape = completed + sum(s["shape"] for s in stages)
doc = collections.OrderedDict([
    ("schema", "a7_call_budget_receipt/1488"),
    ("completed_before", completed), ("completed_before_owner", "a6_launch_freeze.ledger()"),
    ("completed_rows", rows), ("ceiling", ceiling), ("ceiling_owner", "a7_g1_build.CEILING"),
    ("stages", stages),
    ("minimum_total", min_total), ("minimum_fits_ceiling", min_total <= ceiling),
    ("expected_shape_total", expected_shape), ("expected_shape_note", "the provisional no-retry shape: primaries at the latest accepted zero-call artifacts, no retries, no hard-review task; every stage population is re-derived by its owner after key settlement, the producer run and G1"),
    ("headroom_at_shape", ceiling - expected_shape),
    ("known_maximum_subtotal", max_known), ("known_maximum_note", "the sum of every DERIVABLE structural maximum; it is not an absolute maximum"),
    ("absolute_maximum", None), ("absolute_maximum_note", "unknown before the producer run: G3's maximum depends on the produced count"),
    ("known_maximum_fits_ceiling", max_known <= ceiling),
    ("smallest_lawful_predeclared_bound", collections.OrderedDict([
        ("bound", ceiling), ("primaries_declared", min_total),
        ("headroom_for_retries_hard_review_and_g3", ceiling - min_total),
        ("rule", "every future call is checked against the ceiling before it is armed; retries, hard-review tasks and G3 batches are headroom, never per-row reservations, and the run stops at the ceiling")])),
    ("calls_armed", 0)])
canon = json.dumps(doc, sort_keys=True, separators=(",", ":"), default=str)
doc["receipt_sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, indent=1, default=str))
print(json.dumps({k: doc[k] for k in ("completed_before", "ceiling", "minimum_total", "expected_shape_total", "headroom_at_shape", "known_maximum_subtotal", "known_maximum_fits_ceiling", "absolute_maximum")}))
print("stages:", [(s["stage"], s["min"], s["max"]) for s in stages])
print("receipt:", doc["receipt_sha256"], OUT)
