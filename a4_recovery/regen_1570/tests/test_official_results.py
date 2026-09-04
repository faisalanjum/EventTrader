"""RED first: the frozen A4 official-results corpus must be absent until copied; then every refusal
class of the source-freeze owner holds, each beside a positive control (Codex SEQ 1578).

The negative cases work on a private two-workflow copy of the candidate corpus whose census and pins
are rebound to its own bytes, so the unmutated copy reports no problem; each case applies one mutation
and the owner must name that defect. Nothing outside the candidate is read; no coverage framework.
"""
import hashlib
import io
import json
import os
import shutil
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import official_results as OR  # noqa: E402


def test_the_whole_corpus_and_census_hold():
    assert OR.verify() == 0


def test_verify_reads_nothing_outside_the_candidate(monkeypatch):
    monkeypatch.setattr(OR, "OFFICIAL", os.path.join(str(R), "no-such-store"))
    assert OR.problems() == []


def _private(tmp_path):
    wfs = sorted(os.listdir(OR.CORPUS))[:2]
    priv = tmp_path / "a4_official"
    priv.mkdir()
    for wf in wfs:
        shutil.copytree(os.path.join(OR.CORPUS, wf), priv / wf)
    return priv, tmp_path / "census.tsv", wfs


def _accept(priv, census):
    """The census and pins of the private corpus as it now stands: the positive control."""
    rows, totals, bad = OR.derive(str(priv))
    assert bad == [], bad
    text = OR.render(rows)
    io.open(census, "wb").write(text)
    return {"rows": len(rows), "census_bytes": len(text), "census_sha256": hashlib.sha256(text).hexdigest(),
            "state_bytes": totals["state"], "agent_bytes": totals["agent"], "journal_bytes": totals["journal"], "script_bytes": totals["script"]}


def _state(priv, wf):
    return json.loads(io.open(priv / wf / (wf + ".json"), encoding="utf-8").read())


def _put_state(priv, wf, d):
    io.open(priv / wf / (wf + ".json"), "w", encoding="utf-8").write(json.dumps(d))


def _agent_row(d):
    return [r for r in d["workflowProgress"] if r.get("type") == "workflow_agent"][0]


def _flip(path):
    b = bytearray(io.open(path, "rb").read())
    b[len(b) // 2] ^= 0x01
    io.open(path, "wb").write(bytes(b))


def _set(field, value):
    def mutate(priv, census, wfs, pins):
        d = _state(priv, wfs[0])
        d[field] = value
        _put_state(priv, wfs[0], d)
    return mutate


def _set_agent(field, value):
    def mutate(priv, census, wfs, pins):
        d = _state(priv, wfs[0])
        _agent_row(d)[field] = value
        _put_state(priv, wfs[0], d)
    return mutate


def _agent_rows(count):
    def mutate(priv, census, wfs, pins):
        d = _state(priv, wfs[0])
        row = _agent_row(d)
        d["workflowProgress"] = [r for r in d["workflowProgress"] if r.get("type") != "workflow_agent"] + [dict(row)] * count
        _put_state(priv, wfs[0], d)
    return mutate


def _census_lines(census):
    return io.open(census, encoding="utf-8").read().split("\n")


def _write_census(census, lines):
    io.open(census, "w", encoding="utf-8", newline="").write("\n".join(lines))


def _edit_row_field(index, value):
    def mutate(priv, census, wfs, pins):
        lines = _census_lines(census)
        f = lines[1].split("\t")
        f[index] = value
        lines[1] = "\t".join(f)
        _write_census(census, lines)
    return mutate


def _swap_rows(priv, census, wfs, pins):
    lines = _census_lines(census)
    lines[1], lines[2] = lines[2], lines[1]
    _write_census(census, lines)


def _duplicate_row(priv, census, wfs, pins):
    lines = _census_lines(census)
    _write_census(census, lines[:2] + [lines[1]] + lines[2:])


def _duplicate_identity_in_corpus(priv, census, wfs, pins):
    d = _state(priv, wfs[0])
    d["runId"] = wfs[1]
    _put_state(priv, wfs[1], d)


def _wrong_census_hash(priv, census, wfs, pins):
    pins["census_sha256"] = hashlib.sha256(b"drift").hexdigest()


CASES = [
    ("missing corpus file", lambda priv, census, wfs, pins: os.remove(priv / wfs[0] / "journal.jsonl"), "journal missing"),
    ("extra corpus file", lambda priv, census, wfs, pins: io.open(priv / wfs[0] / "extra.txt", "wb").write(b"x"), "extra corpus file"),
    ("extra corpus entry", lambda priv, census, wfs, pins: io.open(priv / "stray", "wb").write(b"x"), "extra corpus entry"),
    ("changed state byte", lambda priv, census, wfs, pins: io.open(priv / wfs[0] / (wfs[0] + ".json"), "ab").write(b"\n"), "state_sha256"),
    ("changed transcript byte", lambda priv, census, wfs, pins: _flip(priv / wfs[0] / [f for f in os.listdir(priv / wfs[0]) if f.startswith("agent-")][0]), "agent_sha256"),
    ("changed journal byte", lambda priv, census, wfs, pins: _flip(priv / wfs[0] / "journal.jsonl"), "journal_sha256"),
    ("duplicate identity in the census", _duplicate_row, "duplicate"),
    ("duplicate identity in the corpus", _duplicate_identity_in_corpus, "duplicate identity"),
    ("wrong run root", _set("scriptPath", "/x/runs/kf-a3-one-item-196x2-final-20260821T052108Z/scripts/a.js"), "not below one of the ten run roots"),
    ("wrong attempt", _edit_row_field(1, "retry"), "census attempt"),
    ("state/workflow id mismatch", _set("runId", "wf_someone-else"), "is not the workflow id"),
    ("absent agent row", _agent_rows(0), "0 workflow_agent rows"),
    ("second agent row", _agent_rows(2), "2 workflow_agent rows"),
    ("non-done agent", _set_agent("state", "running"), "is not done"),
    ("non-completed state", _set("status", "failed"), "is not completed"),
    ("nonzero tools", _set("totalToolCalls", 3), "is not 0"),
    ("wrong model", _set_agent("model", "claude-opus-5"), "is not claude-sonnet-5"),
    ("manifest row drift", _edit_row_field(4, "0" * 64), "census state_sha256"),
    ("manifest order drift", _swap_rows, "not sorted"),
    ("manifest hash drift", _wrong_census_hash, "not the pinned"),
]


@pytest.mark.parametrize("name,mutate,expected", CASES, ids=[c[0] for c in CASES])
def test_each_refusal_class_holds_beside_its_positive_control(name, mutate, expected, tmp_path):
    priv, census, wfs = _private(tmp_path)
    pins = _accept(priv, census)
    assert OR.problems(str(priv), str(census), pins) == [], "the positive control must be clean"
    mutate(priv, census, wfs, pins)
    bad = OR.problems(str(priv), str(census), pins)
    assert bad, "%s must refuse" % name
    assert any(expected in b for b in bad), (name, bad)
