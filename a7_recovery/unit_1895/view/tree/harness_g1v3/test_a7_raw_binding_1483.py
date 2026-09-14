# -*- coding: utf-8 -*-
"""THE RAW-ROW BINDING (Codex SEQ 1483).

The SEQ 1301 ledger compared only COUNTS - raw files versus official rows -
so a raw file whose bytes were edited, or two files whose contents were
swapped, still counted as the paid answers. Codex proved both on copies.

ONE owner in `raw_transport` now derives, from the official rows and the
attempt, the exact filename and the exact UTF-8 text `save_raw` writes for
each row. `a1_preserve` writes through it and the ledger verifies through it:
the raw directory must hold exactly the expected names, and every file's
bytes must equal its row's text, or the attempt is refused before any call
is counted. Calls are the verified bindings, never the schedule, never typed.

Mutations run on disposable copies; the real evidence is read only.
"""
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as A6                                    # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import raw_transport as RT                                       # noqa: E402
import test_a7_runstates_1470 as RS                              # noqa: E402

REFUSED_RUN = "/tmp/a7_v3_prepared_run_1479"
RETRY = os.path.join(G.PRIMARY, "retry")


def _rows(run):
    with io.open(os.path.join(run, "receipt.json"), encoding="utf-8") as fh:
        return RT.a1_readable_rows(json.load(fh).get("states"))


def _attempt(run):
    with io.open(os.path.join(run, RT.FINALIZATION_NAME),
                 encoding="utf-8") as fh:
        return json.load(fh)["attempt"]


def _row_for(rows, run):
    want = os.path.abspath(run)
    return [r for r in rows if os.path.abspath(r.get("run_dir") or "") == want]


# ============================================================= 1. the owner
def test_the_one_binding_owner_names_exactly_what_a1_preserve_writes(tmp_path):
    """Filename and bytes per official row, from one owner; the writer and the
    verifier both consume it, including the no-text fallback."""
    rows = [{"text": "alpha"}, {"text": None}, "not a row",
            {"text": "γ — unicode"}]
    raw = str(tmp_path / "raw")
    records = RT.a1_preserve(rows, raw, 1)
    bindings = RT.a1_raw_bindings(rows, 1)
    assert len(bindings) == len(rows) == len(records)
    assert [os.path.basename(r["path"]) for r in records] == \
        sorted(os.listdir(raw))
    for (stem, text), rec in zip(bindings, records):
        assert os.path.basename(rec["path"]).startswith(stem)
        with io.open(rec["path"], "rb") as fh:
            assert fh.read() == text.encode("utf-8")
    assert RT.a1_raw_binding_problems(str(tmp_path), rows, 1) == []
    # the attempt is part of the name: attempt 2 binds to files that are not there
    assert RT.a1_raw_binding_problems(str(tmp_path), rows, 2)


def test_a6_owns_no_filename_or_fallback_text_rule():
    with io.open(os.path.join(_HERE, "a6_launch_freeze.py"),
                 encoding="utf-8") as fh:
        src = fh.read()
    # the filename rule, the stem rule and the no-text fallback all live in
    # raw_transport; A6 reads the official rows and asks the owner
    for fragment in (".raw.json", "%05d", "attempt%", 'else ""'):
        assert fragment not in src, fragment
    assert "a1_raw_binding_problems(" in src


# ============================================== 2. the three positive controls
@pytest.mark.parametrize("run", [G.PRIMARY, RETRY, REFUSED_RUN])
def test_every_real_producer_attempt_binds_every_returned_row_exactly(run):
    if not os.path.isfile(os.path.join(run, RT.FINALIZATION_NAME)):
        pytest.skip("%s is absent" % run)
    rows = _rows(run)
    assert rows, "a producer attempt with no returned rows binds nothing"
    assert RT.a1_raw_binding_problems(run, rows, _attempt(run)) == []
    # the attempt's spend is read by SUPPLYING the run that owns it, not from
    # the baseline (no producer history lives there now, Codex SEQ 1516): a
    # retry attempt is owned by its parent run.
    owner = os.path.dirname(run) \
        if os.path.basename(run) == os.path.basename(RETRY) else run
    total, ledger_rows = A6.ledger(owner)
    mine = _row_for(ledger_rows, run)
    assert len(mine) == 1, [r["stage"] for r in ledger_rows]
    assert mine[0]["calls"] == len(rows) == \
        len(os.listdir(os.path.join(run, "raw")))
    assert mine[0]["raw_tree"] == F.raw_tree(run)["sha256"]
    assert total == sum(r["calls"] for r in ledger_rows)


@pytest.mark.skipif(not os.path.isfile(os.path.join(REFUSED_RUN,
                                                     RT.FINALIZATION_NAME)),
                    reason="the refused producer run is absent")
def test_the_stopped_run_is_counted_yet_still_unselectable():
    with pytest.raises(ValueError) as exc:
        PR.load(REFUSED_RUN)
    assert "does not hold" in str(exc.value)


# ======================================================= 3. the five mutations
def _edit_one_byte(raw):
    name = sorted(os.listdir(raw))[0]
    with io.open(os.path.join(raw, name), "ab") as fh:
        fh.write(b" ")


def _swap_two(raw):
    a, b = sorted(os.listdir(raw))[:2]
    pa, pb = os.path.join(raw, a), os.path.join(raw, b)
    with io.open(pa, "rb") as fh:
        ta = fh.read()
    with io.open(pb, "rb") as fh:
        tb = fh.read()
    assert ta != tb, "the control needs two different answers to swap"
    with io.open(pa, "wb") as fh:
        fh.write(tb)
    with io.open(pb, "wb") as fh:
        fh.write(ta)


def _rename_one(raw):
    name = sorted(os.listdir(raw))[0]
    os.rename(os.path.join(raw, name), os.path.join(raw, "99999" + name[5:]))


def _add_one(raw):
    name = sorted(os.listdir(raw))[-1]
    shutil.copyfile(os.path.join(raw, name),
                    os.path.join(raw, "99999" + name[5:]))


def _delete_one(raw):
    os.unlink(os.path.join(raw, sorted(os.listdir(raw))[0]))


@pytest.mark.parametrize("label,mutate", [
    ("same-name one-byte edit", _edit_one_byte),
    ("two files' contents swapped", _swap_two),
    ("one file renamed", _rename_one),
    ("one file added", _add_one),
    ("one file deleted", _delete_one),
])
def test_each_raw_mutation_REFUSES_before_anything_is_counted(tmp_path, label,
                                                              mutate):
    run = RS._lawful_zero_retry(tmp_path, "mut")
    base, _r = A6.ledger()
    control, rows = A6.ledger(run)              # the lawful copy counts
    added = _row_for(rows, run)
    assert len(added) == 1 and control == base + added[0]["calls"], label
    mutate(os.path.join(run, "raw"))
    assert RT.a1_raw_binding_problems(run, _rows(run), 1), label
    with pytest.raises(ValueError) as exc:
        A6.ledger(run)
    assert "raw" in str(exc.value), (label, str(exc.value)[:200])


# ===================================================== 4. retained controls
def test_a_distinct_current_run_adds_and_the_same_run_counts_once(tmp_path):
    """A distinct supplied run adds its attempts; supplying the SAME run again
    is a pure read that counts once, never a running sum. The old cross-history
    double-reach is gone with PRODUCER_HISTORY (Codex SEQ 1516)."""
    base, _rows = A6.ledger()
    run = RS._lawful_zero_retry(tmp_path, "distinct")
    total, rows_run = A6.ledger(run)
    added = [r for r in rows_run if r["stage"].startswith("current_producer")]
    assert [r["stage"] for r in added] == ["current_producer_primary"], added
    assert total == base + added[0]["calls"]
    again, rows_again = A6.ledger(run)
    assert again == total and len(rows_again) == len(rows_run)
    assert len(_row_for(rows_again, run)) == 1
