"""RED first: the two recipe owners must be absent or wrong until materialised, and every
recipe input must be exact (Codex SEQ 1572). GREEN after owners_recipe.py has run.

Every check reads the candidate only. The negative cases run the recipe against a private
copy of its inputs with one byte changed, so a corrupted input refuses at the recipe and
writes nothing; the positive control is the unchanged input set.
"""
import hashlib
import io
import os
import shutil
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import owners_recipe as OR  # noqa: E402

H = os.path.join(R, "experiments", "harness_g1v3")


def _sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def test_the_a6_owner_is_the_recipe_bytes():
    p = os.path.join(H, "a6_launch_freeze.py")
    assert os.path.isfile(p), "a6_launch_freeze.py not materialised"
    assert os.path.getsize(p) == OR.A6["bytes"] and _sha(p) == OR.A6["sha256"]


def test_the_raw_transport_owner_is_the_recipe_bytes():
    p = os.path.join(H, "raw_transport.py")
    assert os.path.isfile(p), "raw_transport.py not materialised"
    b = io.open(p, "rb").read()
    assert len(b) == OR.RAW["bytes"] and b.count(b"\n") == OR.RAW["newlines"] and b.endswith(b"\n")
    assert hashlib.sha256(b).hexdigest() == OR.RAW["sha256"]


def test_verify_holds_on_the_candidate():
    assert OR.verify() == 0


@pytest.mark.parametrize("name", ["blob_5ae25b1d9248ea60", "blob_2b8667dc9614c965", "stage1_raw_transport.py", "transcript_record_91763.json"])
def test_a_changed_recipe_input_refuses(name, tmp_path, monkeypatch):
    src = OR.IN
    priv = tmp_path / "owner_recipes"
    shutil.copytree(src, priv)
    p = priv / name
    b = bytearray(io.open(p, "rb").read())
    b[len(b) // 2] ^= 0x01
    io.open(p, "wb").write(bytes(b))
    monkeypatch.setattr(OR, "IN", str(priv))
    monkeypatch.setattr(OR, "OUT", str(tmp_path / "out"))
    with pytest.raises(SystemExit) as ex:
        OR.build()
    assert str(ex.value).startswith("REFUSED")
    assert not os.path.exists(tmp_path / "out"), "a refused recipe must write nothing"


def test_the_unchanged_inputs_build_both_owners_in_a_private_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(OR, "OUT", str(tmp_path / "out"))
    assert OR.build() == 0
    assert _sha(str(tmp_path / "out" / "a6_launch_freeze.py")) == OR.A6["sha256"]
    assert _sha(str(tmp_path / "out" / "raw_transport.py")) == OR.RAW["sha256"]
