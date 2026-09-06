import io, sys
p = sys.argv[1] + "/lock/check_final_key_candidate.py"; s = io.open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]; s = s.replace(old, new)
rep('''import collections, copy, hashlib, io, json, os, shutil, sys
import pytest''', '''import collections, copy, decimal, hashlib, io, json, os, shutil, sys
import pytest''')
rep('''import build_kfields_final as F                                  # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_final_key_candidate as C                            # noqa: E402''', '''import build_kfields_final as F                                  # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_final_key_candidate as C                            # noqa: E402''')
# ---- test 1 now reads the identity file, not a serialized key
rep('''    key = json.load(io.open(os.path.join(OUT, "final_key.json"), encoding="utf-8"))
    assert key["counts"]["events"] == 36 and key["counts"]["unique_rows"] == 196 and key["counts"]["replaced"] == 11 and len(key["key"]) == 36
''', '''    ident = json.load(io.open(os.path.join(OUT, "key_identity.json"), encoding="utf-8"))
    assert ident["counts"]["events"] == 36 and ident["counts"]["unique_rows"] == 196 and ident["counts"]["replaced"] == 11 and len(ident["key_shards"]) == 36
''')
rep('''    p = os.path.join(d, "final_key.json"); io.open(p, "a", encoding="utf-8").write(" ")
    assert "final_key.json" in C.verify(d)
''', '''    p = os.path.join(d, "key_identity.json"); io.open(p, "a", encoding="utf-8").write(" ")
    assert "key_identity.json" in C.verify(d)
''')
rep('''    assert FT.RETRYABLE == ("invalid_response", "transport_no_answer")
    man = json.load(io.open(os.path.join(OUT, "signer", "signer.manifest.json"), encoding="utf-8")) if os.path.isdir(OUT) else None
    if man:
        assert man["state"] == "frozen, unrun" and man["budget"]["primaries"] == 1 and man["budget"]["retry_cap"] == 1
        assert man["budget"]["after_clean"] == man["budget"]["before"] + 1 and man["budget"]["worst"] == man["budget"]["before"] + 2 and man["budget"]["worst"] <= 6000
''', '''    assert F.RETRYABLE == ("invalid_response",)                       # the SIGNER's owner: a transport refusal is final
    man = json.load(io.open(os.path.join(OUT, "signer", "signer.manifest.json"), encoding="utf-8")) if os.path.isdir(OUT) else None
    if man:
        assert man["state"] == "frozen, unrun" and man["budget"]["primaries"] == 1 and man["budget"]["retry_cap"] == 1
        assert man["budget"]["after_clean"] == man["budget"]["before"] + 1 and man["budget"]["worst"] == man["budget"]["before"] + 2 and man["budget"]["worst"] <= 6000
        assert man["retry_law"]["owner"] == "build_kfields_final.RETRYABLE" and man["retry_law"]["retryable"] == list(F.RETRYABLE)
        assert "transport_no_answer" not in man["retry_law"]["retryable"] and "final" in man["gate"]["transport_no_answer"].lower()
''')
s += '''

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
    for sid in composed:
        assert json.dumps(prov[sid]["base_row_order"]) in head and json.dumps(prov[sid]["targeted_row_order"]) in head


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
'''
io.open(p, "w", encoding="utf-8").write(s); print("tests extended")
