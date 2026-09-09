"""Cold TEST producer -> G1 -> nonempty G2/G3 -> official decision.

Uses the existing fake transport/transcript fixtures, never a live model.
One key fact and one deliberately extra fact exercise the actual route;
other packets abstain. These manufactured replies earn no experiment credit.
"""
import collections
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

S = Path("/tmp/claude-1000/-home-faisal-EventMarketDB/"
         "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
BENCH = S / "bench_1306"
H = BENCH / ".claude/plans/Drivers/experiments/harness_g1v3"
ATT = Path(os.environ["A7_ATTEMPT_DIR"])
sys.path.insert(0, str(H))
assert not any(n == "driver" or n.startswith("driver.") for n in sys.modules)

import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as R
import a7_g1_complete_v2 as CV
import a7_prepared_run as PR
import a7_reference_inventory as REF
import a1_reader
import audit_worker_access as AUD
import build_a5_exp5_kit as A5
import build_launch_manifest as BLM
import g1_fake_state as FAKE
import raw_transport as RT
import test_harness_guards as TG
from kf_lint import GOLD_ONLY


def save(path, doc):
    RT.write_new(str(path), json.dumps(doc, indent=2, default=str) + "\n")


def check(problems):
    assert not problems, problems[:5]


def drive(kind, candidate, document, destination):
    return FAKE.complete_test_run(kind, candidate, document, destination, AUD.PROJECTS_ROOT)

ATT.mkdir(parents=True, exist_ok=True)
AUD.PROJECTS_ROOT = os.environ.get("A7_FIXTURE_PROJECTS", str(ATT / "TEST_projects"))
BLM.build()
scorer = H / "scorers/score_exp5_current.py"
B.bind_grading_scorer(str(scorer), G._sha_file(str(scorer)))
producer = ATT / "producer"
prep = A5.prepare(str(producer))
assert prep["ok"], prep.get("problems")
plan = RT.a1_plan_for_run(str(producer))
gold, _key_identity = G.live_key()
seed = None
for packet in plan["packets"]:
    for fact in gold[packet["source_id"]]:
        item = packet["item"]
        if (fact.get("du_worthy") is True and fact["item"]["quote"] == item["quote"]
                and fact["part_ref"] == item["part_ref"]
                and fact["occurrence_in_part"] == item["occurrence_in_part"]):
            seed = packet, fact
            break
    if seed is not None:
        break
assert seed is not None, "the pinned key and producer have no common TEST control"
packet, fact = seed
sparse = {k: copy.deepcopy(v) for k, v in fact.items()
          if k not in GOLD_ONLY and k not in a1_reader.SOURCE_BINDING_FIELDS}
sparse["item"] = {k: v for k, v in sparse["item"].items()
                  if k not in a1_reader.SOURCE_BINDING_FIELDS}
event = next(e for e in plan["events"] if e["source_id"] == packet["source_id"])
inverse_menu = {v: k for k, v in event.get("menu_display_to_original", {}).items()}
sparse["item"]["slice_parts"] = [inverse_menu.get(v, v)
                                   for v in sparse["item"]["slice_parts"]]
extra = copy.deepcopy(sparse)
extra["item"].update(driver_name="test_extra", time_type="duration",
                     period_start_date="2025-01-01",
                     period_end_date="2025-12-31")
replies = {p["prompt_sha256"]: json.dumps({
    "source_id": p["source_id"], "facts": [],
    "abstentions": [{"reason": "TEST control abstention"}], "continuity_hints": []})
    for p in plan["packets"]}
replies[packet["prompt_sha256"]] = G._plain({
    "source_id": packet["source_id"], "facts": [sparse, extra],
    "abstentions": [], "continuity_hints": []})
native = FAKE.declared_input_record()
assert native, "native input declaration must be served"
original_transcript = TG._a1_transcript


def transcript(prompt, answer, model, uuid0="u0", uuid1="u1",
               agent_id="a01", session_id="sess"):
    rows = original_transcript(prompt, answer, model, uuid0, uuid1, agent_id, session_id)
    rows.insert(native["record_index"], {
        "type": native["record_type"], "uuid": "input-" + uuid0,
        "agentId": agent_id, "sessionId": session_id,
        native["payload_field"]: copy.deepcopy(native["payload"])})
    for before, after in zip(rows, rows[1:]):
        after["parentUuid"] = before["uuid"]
    return rows


scratch = ATT / "transport"
scratch.mkdir()
TG._a1_transcript = transcript
try:
    count = TG._a1_execute(H, scratch, prep, plan, AUD.PROJECTS_ROOT,
                           replies, "grader_" + os.environ["A7_TAG"])
finally:
    TG._a1_transcript = original_transcript
assert count == len(plan["packets"]) * len(plan["arms"])
final = RT.a1_finalize(str(producer))
assert final["ledger"]["primary_valid"] == count, final["ledger"]
assert not final["retry"]
audit = AUD.audit(str(producer / "receipt.json"))
check(audit["problems"])
assert len(audit["outcomes"]) == count and {r[1] for r in audit["outcomes"]} == {"served"}
run = PR.load(str(producer))
PR.current(str(producer), run["a6_freeze_sha256"])
save(ATT / "PRODUCER.json", run)
print("TEST producer finalized: %d/%d; cold dependencies resolved." % (count, count), flush=True)

REF.INVENTORY_PATH = str(ATT / "reference_inventory.json")
REF.write(REF.expected_document(run), REF.INVENTORY_PATH)
REF.validate(REF.INVENTORY_PATH, run)
g1_cand = ATT / "g1_candidate"
g1_cand.mkdir()
path, problems = G.write(str(g1_cand), run)
check(problems)
g1 = drive("G1", g1_cand, Path(path), ATT / "g1_run")
save(ATT / "G1_PINS.json", g1)
print("G1 complete through the real lifecycle.", flush=True)

inputs = B.load_verified_inputs(str(producer / "plan/a5_exp5_reader.manifest.json"),
                                 run, str(BENCH))
candidate = ATT / "g23_candidate"
candidate.mkdir()
path, problems = R.write(str(candidate), primary=run, g1=g1, inputs=inputs,
                          audit_root=str(ATT / "route_audit"))
check(problems)
doc = G._read(path)
assert sum(len(v) for v in doc["g2_pairs"].values()) > 0, doc["g2_pairs"]
assert sum(len(v) for v in doc["g3_idxs"].values()) > 0, doc["g3_idxs"]
prompts = {p.name[:-len(".prompt.txt")]: p.read_text()
           for p in (candidate / R.PROMPT_DIRNAME).glob("*.prompt.txt")}
_key, identity = G.live_key()
sources = {}
for kind in ("G2", "G3"):
    cand = ATT / (kind + "_candidate")
    cand.mkdir()
    document, _sha = R.write_kind(str(cand), kind, doc, prompts, identity)
    sources[kind] = drive(kind, cand, Path(document), ATT / (kind + "_run"))
    print("%s complete through the real lifecycle: %d lanes." %
          (kind, sources[kind]["lanes"]), flush=True)
by_leg = {leg: {kind: {field: sources[kind][field] for field in
                      ("run_dir", "root_sha256", "completion_sha256")}
                 for kind, population in (("G2", doc["g2_pairs"]),
                                          ("G3", doc["g3_idxs"]))
                 if any(k.split("|", 1)[0] == leg and v
                        for k, v in population.items())}
          for leg in ("P1", "P2", G.LEG_UNION)}
decisions, scores = B.official_tier_decision(run, by_leg, str(ATT / "score_audit"), g1)
assert set(decisions) == set(A5.ACTIVE_ARM_IDS)
assert set(scores) == set(A5.ACTIVE_ARM_IDS) | {G.LEG_UNION}
assert all(s is not None for s in scores.values())
# Every extra judgment in this TEST fixture is deliberately unresolved. The
# official result must be INCONCLUSIVE, not merely something other than PASS.
assert decisions == dict.fromkeys(A5.ACTIVE_ARM_IDS, None), decisions
expected_gold = sum(f.get("du_worthy") is True for facts in gold.values() for f in facts)
assert all(s["gold_n"] == expected_gold and s["matched"] == 1 for s in scores.values()), scores
decision = {"decisions": decisions, "scores": scores}
save(ATT / "OFFICIAL_DECISION.json", decision)
save(ATT / "OFFLINE_PATH.json", {
    "label": "SYNTHETIC_TEST_ONLY_NOT_MODEL_QUALIFICATION", "model_calls": 0,
    "producer": run, "g1": g1, "sources": sources, "g23_candidate": str(candidate),
    "g2_pairs": doc["g2_pairs"], "g3_idxs": doc["g3_idxs"], "decision": decision,
    "loaded_driver_modules": {n: m.__file__ for n, m in sys.modules.items()
                               if n.startswith("driver.") and getattr(m, "__file__", None)}})
print("Cold offline path saved; the TEST score is not A7 qualification.", flush=True)
