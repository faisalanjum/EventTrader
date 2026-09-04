"""The receipt epochs and their seam, each boundary beside a positive control (Codex SEQ 1586). The
recipe reproduces every historical receipt and finalization hash from the candidate inputs; a
changed capture byte, a changed or reordered epoch file, a reordered census, a swapped workflow
identity and a changed prompt each refuse at the recipe. The seam re-binds the owner's expected
receipt to an era only by its manifest, bound and key set, names a run's kind from its root, and
touches nothing for a run of the current era. The owner-boundary cases on the built world are in
test_v6_world.py. No coverage framework.
"""
import collections
import io
import json
import os
import shutil
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import foundation_sources as FS  # noqa: E402
import receipt_epoch as RE  # noqa: E402
import receipt_epochs_recipe as REC  # noqa: E402

OD = collections.OrderedDict


def test_every_reconstruction_holds():
    assert REC.problems() == []
    got = REC.reconstruct()
    pinned = {(rt, n): FS.pins(rt).get(n.replace("captured prepared ", "prepared ").replace("captured ", "")) for rt, n in got}
    assert all(pinned.values()) and all(got[k][1] == pinned[k] for k in got), [k for k in got if got[k][1] != pinned[k]]
    assert len(got) == 15


def _private(tmp_path, monkeypatch):
    """The recipe's inputs on a private copy: captures, epochs, pins, census."""
    out = tmp_path / "receipt_epochs"
    shutil.copytree(REC.OUT, out)
    monkeypatch.setattr(REC, "OUT", str(out))
    monkeypatch.setattr(REC, "BLOBDIR", str(out / "captures"))
    census = tmp_path / "census.tsv"
    shutil.copyfile(FS.CENSUS, census)
    monkeypatch.setattr(FS, "CENSUS", str(census))
    return out, census


def _flip(path):
    b = bytearray(io.open(path, "rb").read()); b[len(b) // 2] ^= 0x01; io.open(path, "wb").write(bytes(b))


def _reorder_epoch(path):
    d = json.loads(io.open(path, "rb").read().decode("utf-8"), object_pairs_hook=OD)
    d["bound"] = OD(reversed(list(d["bound"].items())))
    io.open(path, "wb").write(json.dumps(d, indent=1).encode("utf-8"))


def _swap_census(census, kind):
    lines = io.open(census, encoding="utf-8").read().split("\n")
    root = REC.root(kind)
    idx = [i for i, l in enumerate(lines) if l.startswith(root + "\t")]
    a, b = lines[idx[0]].split("\t"), lines[idx[1]].split("\t")
    a[3], b[3] = b[3], a[3]                       # the two labels now name each other's saved workflow
    lines[idx[0]], lines[idx[1]] = "\t".join(a), "\t".join(b)
    io.open(census, "w", encoding="utf-8").write("\n".join(lines))


def _reverse_census(census):
    lines = io.open(census, encoding="utf-8").read().split("\n")
    body = [l for l in lines[1:] if l.strip()]
    io.open(census, "w", encoding="utf-8").write("\n".join([lines[0]] + list(reversed(body))) + "\n")


@pytest.mark.parametrize("name,mutate,expected", [
    ("capture byte", lambda out, census: _flip(out / "captures" / "0c75ac4dd1d201c3"), "not its own sha256"),
    ("epoch byte", lambda out, census: _flip(out / "corr.json"), "corr.json is not the derivation"),
    ("epoch key order", lambda out, census: _reorder_epoch(out / "v4corr.json"), "v4corr.json is not the derivation"),
    ("census state order", lambda out, census: _reverse_census(census), "reconstructs to"),
    ("swapped workflow identity", lambda out, census: _swap_census(census, "v5corr"), "reconstructs to"),
])
def test_the_recipe_refuses(name, mutate, expected, tmp_path, monkeypatch):
    out, census = _private(tmp_path, monkeypatch)
    assert REC.problems() == []
    mutate(out, census)
    bad = REC.problems()
    assert bad and any(expected in b for b in bad), (name, bad)


def test_a_changed_prompt_refuses_at_the_recipe(tmp_path, monkeypatch):
    _private(tmp_path, monkeypatch)
    wf = REC.rows("v6corr", "primary")[0][3]
    real = FS.candidate_bytes

    def tampered(rel, root=FS.R):
        b = real(rel, root)
        return b.replace(b'const PROMPT = "', b'const PROMPT = " ', 1) if rel == "state:" + wf else b
    monkeypatch.setattr(FS, "candidate_bytes", tampered)
    bad = REC.problems()
    assert bad and any("v6corr" in b and "reconstructs to" in b for b in bad), bad


# ---- the seam's own rules ----
def test_the_seam_names_a_runs_kind_from_its_root_and_its_retry():
    root = REC.root("v4corr")
    assert RE.kind_of("/x/runs/" + root) == "v4corr" and RE.kind_of("/x/runs/" + root + "/retry") == "v4corr"
    assert RE.kind_of("/x/runs/" + REC.root("signer")) == "signer"


def test_the_seam_rebinding_changes_only_manifest_bound_and_key_set():
    ep = RE.epoch("final")
    fields = json.loads(io.open(REC.epoch_path("decision"), "rb").read().decode("utf-8"), object_pairs_hook=OD)["fields"]
    expected = OD((k, {"manifest_sha256": "m", "bound": {"x": 1}, "states": [], "v1_evidence": {}}.get(k, k)) for k in fields)
    got = RE.era_receipt(expected, ep)
    assert list(got) == [k for k in fields if k != "v1_evidence"]
    assert got["manifest_sha256"] == ep["manifest_sha256"] and got["bound"] == ep["bound"]
    assert all(got[k] == expected[k] for k in got if k not in ("manifest_sha256", "bound"))
    assert RE.epoch("v6corr") is None and RE.epoch("signer") is None


def test_the_seam_refuses_an_epoch_file_that_is_not_the_pinned_bytes(tmp_path, monkeypatch):
    out = tmp_path / "epochs"; shutil.copytree(RE.EPOCHS, out)
    monkeypatch.setattr(RE, "EPOCHS", str(out))
    assert RE.epoch("corr") is not None
    _flip(out / "corr.json")
    with pytest.raises(SystemExit):
        RE.epoch("corr")
