"""Independent, read-only closure composition checks over every live task.

TEST leads check wiring, never source meaning. No model, package, receipt,
signature or key write occurs. The candidate and all borrowed globals must
remain unchanged after the checks, including an exceptional scope exit.
"""
import hashlib
import json
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2001/owner")
import a4_source_closure as CL


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


owners = (CL, CL.SK, CL.F, CL.HR, CL.K)
hashes = {m.__file__: sha(m.__file__) for m in owners}
tasks = CL.SK.tasks()
saved = {(m.__name__, name): getattr(m, name)
         for m, names in (
             (CL.SK, ("prompt", "payload", "prompt_prefix", "prompt_problems", "PAYLOAD_KEYS")),
             (CL.F, ("final_prompt", "event_leads", "render_launcher", "package_problems")),
             (CL.HR, ("_items",)),
             (CL.K, ("MODEL", "RUNTIME_MODEL_ID", "ROW_MODEL_ID")))
         for name in names if hasattr(m, name)}
initial = {t["source_id"]: CL.SK.prompt(t) for t in tasks}
leads = {}
for n, task in enumerate(tasks):
    marker = "TEST_ONLY_SEPARATE_SOURCE_%d" % n
    leads[task["source_id"]] = [{"lead_id": marker, "origin": "TEST_ONLY",
        "member_index": None, "sha256": hashlib.sha256(marker.encode()).hexdigest(),
        "reply": marker}]

results = []
for task in tasks:
    sid = task["source_id"]
    bound = CL.SK.bound(CL.INITIAL_RUN, CL.SK.PKG_DIR)
    with CL._closure_scope(leads):
        prompt = CL.F.final_prompt(bound, task)
        payload = json.loads(prompt.rsplit("[INPUT]\n", 1)[1])
        problems = CL.SK.prompt_problems(task)
        rendered = CL.F.render_launcher(task, bound)
        result = {"source_id": sid,
                  "keys": list(payload),
                  "exact_own_leads": payload["leads"] == leads[sid],
                  "canonical_scope": CL.HR._GROUP_ROLE in prompt,
                  "prompt_problems": problems,
                  "launcher_contains_own_lead": leads[sid][0]["reply"] in rendered}
        results.append(result)

try:
    with CL._closure_scope(leads):
        raise RuntimeError("TEST_ONLY_EXCEPTIONAL_RESTORE")
except RuntimeError as error:
    assert str(error) == "TEST_ONLY_EXCEPTIONAL_RESTORE"

modules = {m.__name__: m for m in owners}
restored = all(getattr(modules[module], name) is value
               for (module, name), value in saved.items())
initial_unchanged = all(CL.SK.prompt(t) == initial[t["source_id"]] for t in tasks)
stable = all(sha(path) == digest for path, digest in hashes.items())
assert restored and initial_unchanged and stable, (restored, initial_unchanged, stable)
print(json.dumps({"test_only": True, "owners": hashes, "tasks": len(tasks),
                  "rows": sum(len(t["rows"]) for t in tasks),
                  "results": results, "globals_restored": restored,
                  "initial_prompts_unchanged": initial_unchanged,
                  "owners_unchanged": stable, "model_calls": 0}, indent=1))
