"""RED first: the five package source texts must be absent or wrong until materialised, and every
recipe input must be exact (Codex SEQ 1575 item 4). GREEN after package_texts_recipe.py has run.

Every check reads the candidate only. The negative cases run the recipes against a private copy
of the inputs: one byte changed refuses at the source hash; and with the source pin rebound to the
changed file, a missing marker, a lost numbered line or a lost denominator line still refuses, so
each layer holds on its own. A refused recipe writes nothing.
"""
import hashlib
import io
import os
import re
import shutil
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import package_texts_recipe as PT  # noqa: E402

H = os.path.join(R, "experiments", "harness_g1v3")
NAMES = sorted(PT.PINS)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


@pytest.mark.parametrize("name", NAMES)
def test_each_text_is_its_recipe_bytes(name):
    p = os.path.join(H, name)
    assert os.path.isfile(p), "%s not materialised" % name
    b = io.open(p, "rb").read()
    _src, _src_sha, size, newlines, out_sha = PT.PINS[name]
    assert (len(b), b.count(b"\n"), _sha(b)) == (size, newlines, out_sha)


def test_verify_holds_on_the_candidate():
    assert PT.verify() == 0


def _private_inputs(tmp_path, monkeypatch):
    priv = tmp_path / "package_texts"
    shutil.copytree(PT.IN, priv)
    monkeypatch.setattr(PT, "IN", str(priv))
    monkeypatch.setattr(PT, "OUT", str(tmp_path / "out"))
    return priv


def _refuses(tmp_path):
    with pytest.raises(SystemExit) as ex:
        PT.build()
    assert str(ex.value).startswith("REFUSED")
    assert not os.path.exists(tmp_path / "out"), "a refused recipe must write nothing"


@pytest.mark.parametrize("name", NAMES)
def test_a_changed_byte_in_a_recipe_input_refuses_at_the_source_hash(name, tmp_path, monkeypatch):
    priv = _private_inputs(tmp_path, monkeypatch)
    p = priv / PT.PINS[name][0]
    b = bytearray(io.open(p, "rb").read())
    b[len(b) // 2] ^= 0x01
    io.open(p, "wb").write(bytes(b))
    _refuses(tmp_path)


def _lose_second_numbered_line(s):
    j = s.index("\n2. ", s.index("## A."))
    return s[:j] + "\n2) " + s[j + 4:]


def _add_a_finding_outside_the_denominator(s):
    """One more well-formed numbered finding, placed before the first, with an id the denominator never names."""
    m = re.search(r"^[0-9]+\. \S+ ", s, re.M)
    extra = "9. 0000000000-00-000000 An extra well-formed finding whose id the frozen denominator does not name.\n\n"
    return s[:m.start()] + extra + s[m.start():]


@pytest.mark.parametrize("name,mutate", [
    ("owner_rulings_1383.txt", lambda s: s.replace("KNOWN CLASS-WIDE ACCEPTANCE CONSEQUENCES", "KNOWN CLASS-WIDE", 1)),
    ("decision_rules_1387.txt", lambda s: s.replace("## B.", "## C.", 1)),
    ("v4_findings_1390.txt", _lose_second_numbered_line),
    ("v6_findings_1396.txt", lambda s: s.replace("\n  0000027904-26-000013\n", "\n", 1)),
    ("v6_findings_1396.txt", _add_a_finding_outside_the_denominator),
])
def test_a_rebound_source_still_refuses_on_marker_count_or_order(name, mutate, tmp_path, monkeypatch):
    priv = _private_inputs(tmp_path, monkeypatch)
    src, src_sha, size, newlines, out_sha = PT.PINS[name]
    p = priv / src
    s = io.open(p, encoding="utf-8").read()
    m = mutate(s)
    assert m != s, "the mutation must change the source"
    io.open(p, "w", encoding="utf-8", newline="").write(m)
    pins = dict(PT.PINS)
    pins[name] = (src, _sha(m.encode("utf-8")), size, newlines, out_sha)
    monkeypatch.setattr(PT, "PINS", pins)
    _refuses(tmp_path)


def test_the_unchanged_inputs_build_all_five_in_a_private_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(PT, "OUT", str(tmp_path / "out"))
    assert PT.build() == 0
    for name in NAMES:
        assert _sha(io.open(tmp_path / "out" / name, "rb").read()) == PT.PINS[name][4]
