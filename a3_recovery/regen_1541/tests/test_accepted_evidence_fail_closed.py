"""The 41/38/36/2/3 attempt-evidence accounting fails CLOSED (Codex SEQ 1561 item 2).

The census binds every one of the 38 saved attempt rows to one state, one transcript
and one raw answer, and the three quarantined calls to the nine files the ledger pins
(plus three ancillary metadata files, manifest-bound only). Parsing and shape belong to
the existing owners - raw_transport.parse_reply, build_inventory_review._reply_shape,
audit_worker_access._chain - the census only binds and counts. These controls prove
that missing or one-byte-altered files refuse, that identity mismatches refuse, that a
same-source parseable reply with a missing required field or an extra nested field
stays schema-invalid when re-bound, and that the accounting is exactly 41 paid calls,
38 saved rows, 36 unique sources, 36 schema-valid attempts, 2 schema-invalid attempt-1
replies each replaced by a lawful schema-valid attempt 2, 3 quarantined calls.
"""
import hashlib
import io
import json
import os
import shutil
import sys

import pytest

R = os.path.join(os.path.dirname(__file__), "..")
sys.path[:0] = [os.path.join(R, "proofs")]
import accepted_evidence_census as AEC  # noqa: E402

RUN = "bench/.claude/plans/Drivers/experiments/invrev_run4"


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    """A private copy of exactly the files the census reads, bound afresh."""
    root = str(tmp_path_factory.mktemp("pkg"))
    for rel in AEC.needed_paths(R):
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(R, rel), dst)
    rep = AEC.census(root, bind=True)
    assert rep["defects"] == [], rep["defects"][:5]
    return root


def _fresh(package, tmp_path):
    root = str(tmp_path / "pkg")
    shutil.copytree(package, root)
    return root


def _flip(path):
    b = bytearray(io.open(path, "rb").read())
    b[len(b) // 2] ^= 0x01
    io.open(path, "wb").write(bytes(b))


def _rows(root):
    return json.load(io.open(os.path.join(root, RUN, "attempts.json"), encoding="utf-8"))


def _rebind_reply(root, row, text):
    """Replace one attempt's reply everywhere it is recorded - raw file, state result,
    transcript terminal answer - so only the CONTENT differs, never the chain."""
    paths = AEC.row_paths(row)
    io.open(os.path.join(root, paths["raw"]), "w", encoding="utf-8", newline="").write(text)
    sp = os.path.join(root, paths["state"])
    st = json.load(io.open(sp, encoding="utf-8"))
    st["result"] = text
    io.open(sp, "w", encoding="utf-8").write(json.dumps(st))
    tp = os.path.join(root, paths["transcript"])
    recs = [json.loads(l) for l in io.open(tp, encoding="utf-8") if l.strip()]
    last = [r for r in recs if r.get("type") == "assistant"][-1]
    last["message"]["content"] = [{"type": "text", "text": text}]
    io.open(tp, "w", encoding="utf-8").write("".join(json.dumps(r) + "\n" for r in recs))
    # the private copy's mount authorities pin the rewritten bytes: this control is
    # about schema validity under re-binding, not about the pins
    for tsv, rel in ((AEC.STATES_TSV, os.path.basename(paths["state"])),
                     (AEC.RECORDS_TSV, os.path.relpath(paths["transcript"], os.path.join("evidence", "subagent_records")))):
        fp = os.path.join(root, tsv)
        target = os.path.join(root, paths["state"] if tsv == AEC.STATES_TSV else paths["transcript"])
        digest = hashlib.sha256(io.open(target, "rb").read()).hexdigest()
        lines = io.open(fp, encoding="utf-8").read().split("\n")
        out = []
        for l in lines:
            if l.startswith(rel + "\t"):
                f, _b, _s, rest = l.split("\t", 3)
                l = "\t".join([f, str(os.path.getsize(target)), digest, rest])
            out.append(l)
        io.open(fp, "w", encoding="utf-8").write("\n".join(out))


def test_the_exact_accounting(package):
    rep = AEC.census(package)
    assert rep["defects"] == []
    a = rep["accounting"]
    assert (a["paid_calls"], a["saved_attempt_rows"], a["quarantined_calls"]) == (41, 38, 3)
    assert a["unique_sources"] == 36 and a["final_source_results"] == 36
    assert a["schema_valid_attempts"] == 36 and a["schema_invalid_attempts"] == 2
    assert a["chain_mismatches"] == 0 and a["files_bound"] == 114
    # the two invalid replies are attempt 1 of their sources, each replaced by a
    # schema-valid attempt 2 - the two lawful replacements, named by the owner
    inv = rep["schema_invalid"]
    assert len(inv) == 2 and all(x["attempt"] == 1 for x in inv)
    assert sorted(x["source_id"] for x in rep["lawful_attempt2_replacements"]) == sorted(x["source_id"] for x in inv)
    assert all(x["attempt"] == 2 and x["schema_valid"] for x in rep["lawful_attempt2_replacements"])
    assert all(x["problems"] for x in inv)               # the owner's own reason, kept


def test_quarantine_binding_is_nine_ledger_pinned_plus_three_metadata(package):
    rep = AEC.census(package)
    q = rep["quarantine"]
    assert q["ledger_pinned_files"] == 9 and q["metadata_files"] == 3
    assert len(q["metadata_sha256"]) == 1                # one identical metadata hash
    assert q["ledger_has_meta_sha256"] is False


@pytest.mark.parametrize("kind", ["ledger", "state", "transcript", "raw"])
def test_a_missing_file_is_refused(package, tmp_path, kind):
    root = _fresh(package, tmp_path)
    os.remove(os.path.join(root, AEC.first_path(root, kind)))
    assert any(kind in d for d in AEC.census(root)["defects"])


@pytest.mark.parametrize("kind", ["ledger", "state", "transcript", "raw"])
def test_a_one_byte_alteration_is_refused(package, tmp_path, kind):
    root = _fresh(package, tmp_path)
    _flip(os.path.join(root, AEC.first_path(root, kind)))
    assert any(kind in d for d in AEC.census(root)["defects"])


def test_a_state_transcript_or_raw_identity_mismatch_refuses_separately(package, tmp_path):
    rows = _rows(package)
    row = [r for r in rows if r["attempt"] == 1][0]
    for kind in ("state", "transcript", "raw"):
        root = _fresh(package, tmp_path / kind)
        p = os.path.join(root, AEC.row_paths(row)[kind])
        text = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8", newline="").write(text.replace(row["source_id"], "SOMEONE-ELSE", 1))
        rep = AEC.census(root, bind=True)               # re-bound by bytes: identity still refuses
        assert any(kind in d for d in rep["defects"]), (kind, rep["defects"][:3])


def test_a_parseable_same_source_reply_missing_a_required_field_stays_invalid(package, tmp_path):
    root = _fresh(package, tmp_path)
    rows = _rows(root)
    base = AEC.census(root)
    valid_sid = [x["source_id"] for x in base["schema_valid"] if x["attempt"] == 1][0]
    row = [r for r in rows if r["source_id"] == valid_sid and r["attempt"] == 1][0]
    doc = AEC.parsed_reply(root, row)
    doc.pop("verdicts")
    _rebind_reply(root, row, "```json\n" + json.dumps(doc, default=str) + "\n```")
    rep = AEC.census(root, bind=True)
    assert rep["defects"] == []                         # bound and preserved as paid evidence
    assert any(x["source_id"] == valid_sid and x["attempt"] == 1 for x in rep["schema_invalid"])
    assert rep["accounting"]["schema_invalid_attempts"] == 3
    assert rep["accounting"]["final_source_results"] == 35     # that source has no final result now


def test_a_parseable_same_source_reply_with_an_extra_nested_field_stays_invalid(package, tmp_path):
    root = _fresh(package, tmp_path)
    rows = _rows(root)
    base = AEC.census(root)
    valid_sid = [x["source_id"] for x in base["schema_valid"] if x["attempt"] == 1][0]
    row = [r for r in rows if r["source_id"] == valid_sid and r["attempt"] == 1][0]
    doc = AEC.parsed_reply(root, row)
    doc["verdicts"][0]["quote_check"] = {"extra": True}
    _rebind_reply(root, row, "```json\n" + json.dumps(doc, default=str) + "\n```")
    rep = AEC.census(root, bind=True)
    assert rep["defects"] == []
    assert any(x["source_id"] == valid_sid and x["attempt"] == 1 for x in rep["schema_invalid"])


def test_a_quarantine_file_altered_breaks_the_ledger_binding(package, tmp_path):
    root = _fresh(package, tmp_path)
    q = os.path.join(root, RUN, "quarantine")
    d = sorted(os.listdir(q))[0]
    _flip(os.path.join(q, d, "journal.jsonl"))
    assert any("quarantine" in x for x in AEC.census(root)["defects"])


def test_the_exact_accounting_on_the_package():
    """The same accounting on the package itself, fixture-free for the exact-credit audit."""
    rep = AEC.census(R)
    assert rep["defects"] == []
    a = rep["accounting"]
    assert (a["paid_calls"], a["saved_attempt_rows"], a["quarantined_calls"]) == (41, 38, 3)
    assert a["unique_sources"] == 36 and a["final_source_results"] == 36
    assert a["schema_valid_attempts"] == 36 and a["schema_invalid_attempts"] == 2
    assert len(rep["lawful_attempt2_replacements"]) == 2
