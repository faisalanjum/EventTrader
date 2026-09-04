"""The signed-V6 baseline continuation's own boundaries, each beside a positive control (Codex SEQ
1585 item 6). A reordered census joins the same states while a swapped state mapping refuses at the
script identity; the measured-value anchor refuses a wrong receipt, finalization or raw tree; the
V6 accounting refuses a dropped, reordered or duplicated shard, a wrong inventory-row count, a wrong
origin mix and an open issue; the recorded-state accounting refuses a missing, duplicated or surplus
state. The two continuation builds are checked in test_foundation.py beside the foundation builds;
the boundaries that need the projected world (the real owners) live in test_v6_world.py. No coverage
framework.
"""
import collections
import io
import json
import os
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import foundation as FD  # noqa: E402
import foundation_sources as FS  # noqa: E402


def _rows(kind):
    root = FD.run_root(kind)
    return root, [r for r in FS.census() if r[0] == root and r[1] == "primary"]


def test_a_reordered_census_joins_the_same_states_and_a_swapped_mapping_refuses_at_the_script_identity(tmp_path, monkeypatch, capsys):
    root, rows = _rows("v6corr")
    assert len(rows) > 1
    assert FD.census_index(list(reversed(rows))) == FD.census_index(rows)
    monkeypatch.setattr(FD, "official_state", lambda wf: (os.path.join(FS.CORPUS, wf, wf + ".json"),
                                                          json.loads(FS.candidate_bytes("inputs/a4_official/%s/%s.json" % (wf, wf)).decode("utf-8"))))
    own = {r[2]: FS.candidate_bytes("state:" + r[3]) for r in rows}          # each label's own embedded launcher

    def idx_with(mapping):
        return {(r[0], r[1], r[2]): {"wf": mapping.get(r[2], r[3]), "state_sha256": r[4], "script_sha256": r[7],
                                     "script_path": str(tmp_path / (r[2] + ".js"))} for r in rows}
    invocations = [{"label": r[2]} for r in rows]
    recorded = []
    FD.record_all(idx_with({}), root, "primary", str(tmp_path / "run"), invocations, "label",
                  lambda run_dir, sp: recorded.append(sp) or [], lambda inv, path: own[inv["label"]])
    assert len(recorded) == len(rows) and all((tmp_path / (r[2] + ".js")).is_file() for r in rows)
    for f in tmp_path.glob("*.js"):
        f.unlink()
    swapped = {rows[0][2]: rows[1][3], rows[1][2]: rows[0][3]}
    with pytest.raises(SystemExit):
        FD.record_all(idx_with(swapped), root, "primary", str(tmp_path / "run"), invocations, "label",
                      lambda run_dir, sp: recorded.append(sp) or [], lambda inv, path: own[inv["label"]])
    assert "are not one script" in capsys.readouterr().out


def test_the_measured_anchor_refuses_a_wrong_receipt_finalization_or_raw_tree(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(FD, "LOG", str(tmp_path))
    root = FD.run_root("final")
    for name in ("receipt", "finalization", "raw tree"):
        FD.anchor_value(root, name, FS.pins(root)[name])
    for name in ("receipt", "finalization", "raw tree"):
        with pytest.raises(SystemExit):
            FD.anchor_value(root, name, "0" * 64)
        assert "anchor %s / %s" % (root, name) in capsys.readouterr().out
    rows = [l.split("\t") for l in io.open(os.path.join(str(tmp_path), "ANCHORS.tsv"), encoding="utf-8").read().split("\n") if l.strip()]
    assert [r[4] for r in rows] == ["ok"] * 3 + ["MISMATCH"] * 3


def _lawful_v6():
    p = FS.pins("v6")
    n = int(p["shards"])
    order = ["event%02d" % i for i in range(n)]
    origins, i = collections.OrderedDict(), 0
    for tag in [k for k in p if k.startswith("a4_final_")]:      # the owner's origin names, pinned with their counts
        for _ in range(int(p[tag])):
            origins[order[i]] = tag
            i += 1
    assert i == n
    shards = collections.OrderedDict((s, {"open_issues": []}) for s in order)
    counts = {"events_accounted": n, "rows_accounted": int(p["rows"]), "open_issues": 0}
    return order, shards, origins, counts


def _move_first_to_end(d):
    k = next(iter(d))
    d[k] = d.pop(k)


@pytest.mark.parametrize("name,mutate,expected", [
    ("dropped shard", lambda o, s, g, c: s.popitem(), "in order"),
    ("reordered shards", lambda o, s, g, c: _move_first_to_end(s), "in order"),
    ("duplicated inventory row", lambda o, s, g, c: c.update(rows_accounted=c["rows_accounted"] + 1), "inventory rows"),
    ("missing inventory row", lambda o, s, g, c: c.update(rows_accounted=c["rows_accounted"] - 1), "inventory rows"),
    ("wrong origin mix", lambda o, s, g, c: g.update({o[0]: g[o[-1]]}), "origins"),
    ("open issue in a shard", lambda o, s, g, c: s[o[0]]["open_issues"].append("left open"), "open issue"),
    ("open issue counted", lambda o, s, g, c: c.update(open_issues=1), "open issue"),
])
def test_the_v6_accounting_refuses_each_mismatch(name, mutate, expected):
    order, shards, origins, counts = _lawful_v6()
    assert FD.v6_accounting_problems(order, shards, origins, counts) == []
    mutate(order, shards, origins, counts)
    bad = FD.v6_accounting_problems(order, shards, origins, counts)
    assert bad and any(expected in b for b in bad), (name, bad)


def test_the_recorded_state_accounting_refuses_a_missing_duplicated_or_surplus_state():
    idx = FD.census_index()
    roots = {FD.run_root(k) for _s, k, _f in FD.V} | {FD.run_root("signer")}
    recorded = [os.path.join(FS.SESS, "workflows", r[3] + ".json") for r in FS.census() if r[0] in roots]
    assert len(recorded) == int(FS.pins("v6")["states"])
    assert FD.recorded_states_problems(idx, roots, recorded) == []
    for name, mutated, expected in [("missing", recorded[1:], "never recorded"), ("duplicated", recorded + recorded[:1], "recorded twice"),
                                    ("surplus", recorded + [os.path.join(FS.SESS, "workflows", "wf_not-saved.json")], "not saved")]:
        bad = FD.recorded_states_problems(idx, roots, mutated)
        assert bad and any(expected in b for b in bad), (name, bad)
