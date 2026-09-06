# -*- coding: utf-8 -*-
"""Red-first proofs for the final 196-item candidate and its frozen signer packet
(Codex SEQ 1510 item 5). Lawful control first, then each refusal, every refusal
from an existing owner or the seam's own re-derivation."""
import collections, copy, decimal, hashlib, io, json, os, shutil, sys
import pytest
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
for p in (H, "/home/faisal/EventMarketDB", S + "/lock"):
    p in sys.path or sys.path.insert(0, p)
import build_kfields_final as F                                  # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_final_key_candidate as C                            # noqa: E402
OUT = C.DEFAULT_OUT
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()   # noqa: E731
_cand = pytest.mark.skipif(not os.path.isdir(OUT), reason="the candidate is absent")


@_cand
def test_the_candidate_rebuilds_byte_identical_and_verifies(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    ha, _fc, _c, ma = C.build(a); hb, _fc2, _c2, mb = C.build(b)
    assert ha == hb                                                  # reproducible from the owners alone
    for n, h in ha.items():
        path = os.path.join(OUT, "signer", n) if n.startswith(("signer_prompt", "final_sign", "signer.manifest")) else os.path.join(OUT, n)
        assert sha(path) == h, n                                     # the frozen candidate IS the live derivation
    assert C.verify(OUT) == []
    assert ma["prompt_sha256"] == mb["prompt_sha256"] and ma["script_bytes"] == mb["script_bytes"] < ma["transport_limit_bytes"]
    ident = json.load(io.open(os.path.join(OUT, "key_identity.json"), encoding="utf-8"))
    assert ident["counts"]["events"] == 36 and ident["counts"]["unique_rows"] == 196 and ident["counts"]["replaced"] == 11 and len(ident["key_shards"]) == 36
    val = json.load(io.open(os.path.join(OUT, "validator_receipt.json"), encoding="utf-8"))
    assert val["problems"] == [] and val["counts"]["open_issues"] == 0 and val["counts"]["tags_below_floor"] == [] and val["counts"]["rows_accounted"] == 196


@_cand
def test_a_mutated_candidate_byte_refuses(tmp_path):
    d = str(tmp_path / "cand"); shutil.copytree(OUT, d)
    p = os.path.join(d, "key_identity.json"); io.open(p, "a", encoding="utf-8").write(" ")
    assert "key_identity.json" in C.verify(d)


@_cand
def test_a_composed_event_is_shown_as_its_two_real_component_raws():
    man = json.load(io.open(os.path.join(OUT, "signer", "signer.manifest.json"), encoding="utf-8"))
    prov = json.load(io.open(os.path.join(OUT, "provenance.json"), encoding="utf-8"))["provenance"]["events"]
    prompt = io.open(os.path.join(OUT, "signer", "signer_prompt.txt"), encoding="utf-8").read()
    composed = [s for s, e in prov.items() if e["composed"]]
    assert len(composed) == 8 and len(man["shards"]) == 28 + 2 * 8
    for sid in composed:
        assert prompt.count("--- shard %s [COMPOSED: base component" % sid) == 1 and prompt.count("--- shard %s [COMPOSED: targeted component" % sid) == 1
        assert prov[sid]["base_raw_sha256"] in prompt and prov[sid]["targeted_raw_sha256"] in prompt
        assert "--- shard %s sha256" % sid not in prompt               # never one synthesized raw for a composed event
    for s, e in prov.items():
        if not e["composed"]:
            assert prompt.count("--- shard %s sha256 %s ---" % (s, e["raw_sha256"])) == 1


@pytest.mark.parametrize("how", ["binding_elsewhere", "open_issue_left"])
def test_the_candidate_refuses_a_moved_binding_or_a_remaining_issue(how, tmp_path, monkeypatch):
    if how == "binding_elsewhere":
        b = json.load(io.open(FT.CORR3_BINDING, encoding="utf-8")); b["run_dir"] = str(tmp_path / "elsewhere")
        p = str(tmp_path / "binding.json"); io.open(p, "w", encoding="utf-8").write(json.dumps(b, indent=1))
        monkeypatch.setattr(FT, "CORR3_BINDING", p)
        with pytest.raises(ValueError, match="not the bound"):
            C.compose()
    else:
        real = FT.accepted_shards; run3 = os.path.abspath(C.RUNS[2])
        def forged(run):
            sh, rw, bad = real(run)
            if os.path.abspath(run) == run3:
                sh = copy.deepcopy(sh); next(iter(sh.values()))["open_issues"] = [collections.OrderedDict([("what", "device"), ("why", "device")])]
            return sh, rw, bad
        monkeypatch.setattr(FT, "accepted_shards", forged)
        FT._bound_cached.cache_clear()
        _k, _s, _sh, _r, _p, _c, problems = C.compose()
        assert any("open issues block" in x for x in problems)
        with pytest.raises(SystemExit):
            C.build(str(tmp_path / "refused"))
        assert os.path.exists(str(tmp_path / "refused" / "refusal.json"))


def test_the_signer_gate_is_frozen_and_never_retries_meaning():
    ok, bad = F.read_signature('{"signed": true, "blocked": [], "why": "reproduced"}'); assert ok["signed"] is True and bad == []
    ok, bad = F.read_signature('{"signed": false, "blocked": ["count 3 differs"], "why": "not reproduced"}'); assert ok["signed"] is False and bad == []   # a lawful refusal: final, never retried
    _o, bad = F.read_signature('{"signed": true, "blocked": ["x"], "why": "y"}'); assert bad            # contradictory: structurally invalid
    _o, bad = F.read_signature("not json at all"); assert bad                                        # structurally invalid
    _o, bad = F.read_signature(None); assert bad                                                     # transport: no text
    assert F.RETRYABLE == ("invalid_response",)                       # the SIGNER's owner: a transport refusal is final
    man = json.load(io.open(os.path.join(OUT, "signer", "signer.manifest.json"), encoding="utf-8")) if os.path.isdir(OUT) else None
    if man:
        assert man["state"] == "frozen, unrun" and man["budget"]["primaries"] == 1 and man["budget"]["retry_cap"] == 1
        assert man["budget"]["after_clean"] == man["budget"]["before"] + 1 and man["budget"]["worst"] == man["budget"]["before"] + 2 and man["budget"]["worst"] <= 6000
        assert man["retry_law"]["owner"] == "build_kfields_final.RETRYABLE" and man["retry_law"]["retryable"] == list(F.RETRYABLE)
        assert "transport_no_answer" not in man["retry_law"]["retryable"] and "final" in man["gate"]["transport_no_answer"].lower()


# ------------------------------- Codex SEQ 1511: the four wrapper corrections
@_cand
def test_exact_numeric_identity_is_never_serialized_and_a_stray_decimal_raises():
    assert not os.path.exists(os.path.join(OUT, "final_key.json"))       # no serialized key, no preview
    ident = json.load(io.open(os.path.join(OUT, "key_identity.json"), encoding="utf-8"))
    assert ident["authoritative"] is True and ident["loader"]["module"] == "build_kfields_final_targeted" and ident["loader"]["entry"] == "full_materialize"
    assert ident["loader"]["sha256"] == sha(FT.__file__) and ident["materializer"]["sha256"] == sha(F.__file__)
    for shard in ident["key_shards"]:
        for comp in shard["components"]:
            assert len(comp["sha256"]) == 64 and int(comp["sha256"], 16) >= 0
    key, sidecar, _sh, _r, _p, _c, problems = C.compose()
    assert problems == []
    def leaves(o):
        if isinstance(o, dict):
            for v in o.values(): yield from leaves(v)
        elif isinstance(o, list):
            for v in o: yield from leaves(v)
        else: yield o
    decimals = sum(1 for v in leaves(key) if isinstance(v, decimal.Decimal))
    assert decimals > 0                                                  # the exact types live in memory and in the raw shards only
    for name in ("key_identity.json", "sidecar.json", "provenance.json", "validator_receipt.json"):
        text = io.open(os.path.join(OUT, name), encoding="utf-8").read()
        assert '"' + "13.5" + '"' not in text or name == "sidecar.json"  # no stringified number in wrapper metadata
        json.dumps(json.loads(text))                                     # strict round trip
    with pytest.raises(TypeError):
        C.dumps({"stray": decimal.Decimal("13.5")})                      # strict: a stray Decimal raises, no encoder


@_cand
def test_the_composed_row_maps_are_exported_by_the_composition_owner_and_verified_independently():
    prov = json.load(io.open(os.path.join(OUT, "provenance.json"), encoding="utf-8"))["provenance"]["events"]
    b = FT._baseline()[0]
    full = {t["source_id"]: t for t in F.event_tasks(b.evidence)}
    partial = FT._by_source(FT.DOOR)
    composed = [s for s, e in prov.items() if e["composed"]]
    assert len(composed) == 8
    for sid in composed:
        e = prov[sid]
        assert e["base_row_order"] == full[sid]["rows"] and e["targeted_row_order"] == partial[sid]["rows"]
        assert set(e["replaced"]) <= set(e["targeted_row_order"]) <= set(e["base_row_order"])
        assert len(set(e["base_row_order"])) == len(e["base_row_order"]) and len(set(e["targeted_row_order"])) == len(e["targeted_row_order"])
    prompt = io.open(os.path.join(OUT, "signer", "signer_prompt.txt"), encoding="utf-8").read()
    head = prompt[:prompt.find(HR._boundary())]
    assert "[COMPOSITION MAP]" in head and "[RESOLVED HISTORY]" in head and head.find("[RESOLVED HISTORY]") < head.find("[ROLE]")
    shown = json.loads(head.split("[COMPOSITION MAP]\n", 1)[1].split("\n\n[ROLE]", 1)[0])   # the trusted map, exactly as the signer reads it
    assert list(shown) == composed
    for sid in composed:
        assert shown[sid]["base_row_order"] == prov[sid]["base_row_order"] and shown[sid]["targeted_row_order"] == prov[sid]["targeted_row_order"]
        assert shown[sid]["replaced"] == prov[sid]["replaced"] and shown[sid]["base_raw_sha256"] == prov[sid]["base_raw_sha256"] and shown[sid]["targeted_raw_sha256"] == prov[sid]["targeted_raw_sha256"]


@pytest.mark.parametrize("how", ["drop", "reorder", "duplicate", "wrong_packet"])
def test_a_mutated_composed_row_map_refuses_after_a_lawful_control(how, monkeypatch):
    real = FT.full_successor
    assert C.compose()[6] == []                                          # the lawful control, first
    def forged(*runs):
        sh, rw, pv, pb = real(*runs); pv = copy.deepcopy(pv)
        sid = [s for s, e in pv["events"].items() if e["composed"]][0]; e = pv["events"][sid]
        if how == "drop": e["base_row_order"] = e["base_row_order"][1:]
        elif how == "reorder": e["targeted_row_order"] = list(reversed(e["targeted_row_order"]))
        elif how == "duplicate": e["base_row_order"] = e["base_row_order"] + e["base_row_order"][:1]
        else: e["targeted_row_order"] = ["9999999999-99-999999#999"] + e["targeted_row_order"][1:]
        return sh, rw, pv, pb
    monkeypatch.setattr(FT, "full_successor", forged)
    problems = C.compose()[6]
    assert any("composition map" in p for p in problems), problems


@_cand
def test_the_resolved_history_definitions_precede_the_boundary_and_the_launcher_carries_the_same_prompt():
    prompt = io.open(os.path.join(OUT, "signer", "signer_prompt.txt"), encoding="utf-8").read()
    script = io.open(os.path.join(OUT, "signer", "final_sign.attempt1.js"), encoding="utf-8").read()
    cut = prompt.find(HR._boundary()); assert cut > 0
    head = prompt[:cut]
    for phrase in ("record_kind_conflicts", "already-resolved", "phase1_ambiguities", "retained first-pass", "ambiguity_note", "settled judgment", "open_issues"):
        assert phrase in head
    assert head.count("[RESOLVED HISTORY]") == 1 and prompt.count("[BOUNDARY]") == 1
    assert json.dumps(prompt) in script                                  # the launcher runs exactly this prompt
    assert len(script.encode("utf-8")) < 524288
