# -*- coding: utf-8 -*-
"""In-world tests for the SEQ 1486 locator-receipt recovery (Codex SEQ 1592 item 5): the common
lawful control reproduces both target hashes; one mutation per used-field class, per capacity
maximum and per external identity refuses or misses the target. Runs only inside the recovery world."""
import copy, hashlib, os, sys
import pytest

HOME = os.environ.get("LOCATOR_1486_HOME", "")
if HOME and HOME not in sys.path:
    sys.path.insert(0, HOME)
pytestmark = pytest.mark.skipif(not (HOME and os.path.ismount("/tmp")), reason="only inside the recovery world")


@pytest.fixture(scope="module")
def world():
    import recovery_adapter as A
    A.derive_pointers()
    A.derive_a1_plan()
    assert A.a3_proof() == []
    manifest, freeze, _prov, prompts = A.derive_projections()
    return {"A": A, "manifest": manifest, "freeze": freeze, "prompts": prompts, "ids": A.identities(), "targets": A.targets()}


def run(world, manifest=None, freeze=None, ids=None):
    A = world["A"]
    A.write_projections(manifest or world["manifest"], freeze or world["freeze"], A.owner_paths(A.owner_source()))
    try:
        r = A.run_owner(ids or world["ids"])
    except Exception as e:                      # a refusal is an outcome, recorded as such
        return ("REFUSED", "%s: %s" % (type(e).__name__, str(e)[:120]))
    return (r["receipt_sha256"], r["file_sha256"])


def test_lawful_control_reproduces_both_target_hashes(world):
    assert run(world) == world["targets"]


def test_population_196_rechecked(world):
    packets = world["manifest"]["packets"]
    ids = [p["packet_id"] for p in packets]
    assert len(ids) == 196 and len(set(ids)) == 196
    for p in packets:
        text = world["prompts"][p["packet_id"]]
        assert p["prompt_chars"] == len(text)
        assert p["prompt_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert [a["arm"] for a in world["manifest"]["arms"]] and all(set(a) == {"arm", "role", "tier", "effort", "active"} for a in world["manifest"]["arms"])


def _flip(h):
    return ("0" if h[0] != "0" else "1") + h[1:]


def mutants(world):
    m, f, ids = world["manifest"], world["freeze"], world["ids"]
    def M(**kw):
        d = copy.deepcopy(m); d.update(kw); return d
    out = []
    out.append(("role", M(prompt_role="producer"), f, ids))
    out.append(("contract_suffix", M(contract_suffix=""), f, ids))
    d = copy.deepcopy(m); d["packets"][0]["packet_id"] += "x"; out.append(("packet_id", d, f, ids))
    d = copy.deepcopy(m); d["packets"][0]["prompt_sha256"] = _flip(d["packets"][0]["prompt_sha256"]); out.append(("packet_prompt_sha256", d, f, ids))
    d = copy.deepcopy(m)
    for p in d["packets"]:
        p["prompt_chars"] += 1
    out.append(("packet_prompt_chars", d, f, ids))
    out.append(("arms_ids_only", M(arms=[a["arm"] for a in m["arms"]]), f, ids))
    d = copy.deepcopy(m); d["arms"][0].pop("tier"); out.append(("arms_missing_field", d, f, ids))
    out.append(("arms_order", M(arms=list(reversed(copy.deepcopy(m["arms"])))), f, ids))
    g = copy.deepcopy(f); g["counts"]["capacity"]["prompt_chars_max"] -= 1; out.append(("capacity_prompt_chars_max", m, g, ids))
    g = copy.deepcopy(f); g["counts"]["capacity"]["prompt_utf8_bytes_max"] -= 1; out.append(("capacity_prompt_utf8_bytes_max", m, g, ids))
    out.append(("manifest_identity", m, f, dict(ids, manifest=_flip(ids["manifest"]))))
    out.append(("freeze_identity", m, f, dict(ids, freeze=_flip(ids["freeze"]))))
    return out


NAMES = ["role", "contract_suffix", "packet_id", "packet_prompt_sha256", "packet_prompt_chars", "arms_ids_only",
         "arms_missing_field", "arms_order", "capacity_prompt_chars_max", "capacity_prompt_utf8_bytes_max",
         "manifest_identity", "freeze_identity"]


@pytest.mark.parametrize("name", NAMES)
def test_mutation_refuses_or_misses_target(world, name):
    row = dict((r[0], r) for r in mutants(world))[name]
    got = run(world, row[1], row[2], row[3])
    print("MUTATION %s -> %s" % (name, got))
    assert got != world["targets"]
