"""The grading context must remain the bytes the producer actually read."""
import copy
import hashlib
import json
import os

import pytest

import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as R
from test_a7_trace_1471 import run, current_g1 as g1  # current completed no-AI proof


@pytest.fixture(scope="module")
def inputs(run):
    bench = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    return B.load_verified_inputs(os.path.join(
        run["run_dir"], "plan/a5_exp5_reader.manifest.json"), run, bench)


def _freeze(run, inputs, g1, out):
    doc, prompts, problems = R.freeze(run, inputs=inputs, g1=g1, audit_root=str(out))
    assert problems == [], problems
    assert sum(len(v) for v in doc["g2_pairs"].values()) > 0
    return doc, prompts


@pytest.mark.parametrize("warm", [False, True])
def test_mutable_path_and_hash_cannot_change_the_public_nonempty_g2(run, inputs, g1, tmp_path, warm):
    if not warm:
        G._MATERIALIZED.clear()  # exercise the actual cold validation path too
    control, prompts = _freeze(run, inputs, g1, tmp_path / "control")
    key = next(k for k, pairs in control["g2_pairs"].items() if pairs)
    sid = key.split("|", 1)[1]
    row = inputs["rows"][sid]
    with open(os.path.join(inputs["root"], row["input_path"]), encoding="utf-8") as stream:
        raw = json.load(stream)
    alternate = copy.deepcopy(raw)
    alternate["fye_month"] = 11 if raw["fye_month"] != 11 else 12
    assert alternate["source_id"] == sid == raw["source_id"]
    assert B.event_context(alternate) != B.event_context(raw)
    path = tmp_path / "alternate_same_source.json"
    path.write_text(json.dumps(alternate), encoding="utf-8")
    forged = copy.deepcopy(inputs)
    forged["rows"][sid] = {"input_path": str(path),
                            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    # The entire alternate file and its hash agree, but that is not the file
    # the ORIGINAL producer manifest authorized. The public entry must refuse.
    with pytest.raises(ValueError, match="manifest|input.*(changed|differ|bind)"):
        R.freeze(run, inputs=forged, g1=g1, audit_root=str(tmp_path / "forged"))
    restored, restored_prompts = _freeze(run, inputs, g1, tmp_path / "restored")
    assert restored["g2_pairs"] == control["g2_pairs"]
    assert restored_prompts == prompts


@pytest.mark.parametrize("field", ["manifest_sha256", "a5_manifest_sha256", "manifest_path", "rows"])
def test_changed_manifest_claim_is_not_an_authority(run, inputs, g1, tmp_path, field):
    _freeze(run, inputs, g1, tmp_path / "control")
    forged = copy.deepcopy(inputs)
    if field == "rows":
        forged[field].pop(next(iter(forged[field])))
    elif field == "manifest_path":
        path = tmp_path / "foreign_manifest.json"
        original = os.path.join(run["run_dir"], "plan/a5_exp5_reader.manifest.json")
        doc = json.load(open(original, encoding="utf-8"))
        doc["events"][0]["input_sha256"] = "0" * 64
        path.write_text(json.dumps(doc), encoding="utf-8")
        forged[field] = str(path)
    else:
        forged[field] = "0" * 64
    with pytest.raises((ValueError, KeyError)):
        R.freeze(run, inputs=forged, g1=g1, audit_root=str(tmp_path / "forged"))


def test_identical_bytes_under_a_durable_root_alias_are_allowed(run, inputs, g1, tmp_path):
    control, prompts = _freeze(run, inputs, g1, tmp_path / "control")
    alias = tmp_path / "same_inputs"
    alias.symlink_to(inputs["root"], target_is_directory=True)
    rebound = dict(inputs, root=str(alias))
    same, same_prompts = _freeze(run, rebound, g1, tmp_path / "alias")
    assert same["g2_pairs"] == control["g2_pairs"]
    assert same_prompts == prompts


@pytest.mark.parametrize("fault", ["missing", "bytes", "wrong_source"])
def test_the_manifest_row_cannot_be_replaced_at_its_approved_path(run, inputs, g1, tmp_path, fault):
    control, _ = _freeze(run, inputs, g1, tmp_path / "control")
    sid = next(k.split("|", 1)[1] for k, pairs in control["g2_pairs"].items() if pairs)
    row = inputs["rows"][sid]
    source = os.path.join(inputs["root"], row["input_path"])
    root = tmp_path / "different_inputs"
    path = root / row["input_path"]
    path.parent.mkdir(parents=True)
    if fault != "missing":
        raw = json.load(open(source, encoding="utf-8"))
        if fault == "wrong_source":
            raw["source_id"] = "different_source"
        else:
            raw["fye_month"] = 11 if raw["fye_month"] != 11 else 12
        path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises((ValueError, IOError)):
        R.freeze(run, inputs=dict(inputs, root=str(root)), g1=g1,
                 audit_root=str(tmp_path / "wrong"))
