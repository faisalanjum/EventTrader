# -*- coding: utf-8 -*-
"""In-world tests for the candidate_v2_1488 correction unit (Codex SEQ 1594): the green control
reproduces the four historical outputs; one mutation per input identity or used field the 1488
owner reads refuses or misses the targets. Runs only inside the recovery world, after the adapter
has derived the 1488 owner at its historical path; the owner is imported through the adapter's single
historical import route, never a second one."""
import hashlib, io, json, os, shutil, sys
import pytest

HOME = os.environ.get("CORR_1488_HOME", "")
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
LOCK = S + "/lock"
pytestmark = pytest.mark.skipif(not (HOME and os.path.ismount("/tmp")), reason="only inside the recovery world")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


@pytest.fixture(scope="module")
def L2():
    pins = json.load(io.open(HOME + "/pins_1594.json", encoding="utf-8"))
    if HOME not in sys.path:
        sys.path.insert(0, HOME)
    import recovery_1488 as A
    mod = A.historical_import_route()                 # THE ONE shared import route (transcript line 79488)
    assert sha(read(mod.__file__)) == pins["owner_1488_sha256"]
    mod._TARGETS = {"final_inventory.json": pins["final_inventory"], "adjudication_sidecar.json": pins["adjudication_sidecar"],
                    "validator_receipt.json": pins["validator_receipt"], "correction_receipt.json": pins["correction_receipt"]}
    return mod


def build(L2, out_dir, receipt_path=None, versioned_path=False):
    try:
        return L2.build(str(out_dir), receipt_path or L2.RECEIPT_PATH, versioned_path=versioned_path)["hashes"]
    except Exception as e:                       # a refusal is an outcome, recorded as such
        return ("REFUSED", "%s: %s" % (type(e).__name__, str(e)[:140]))


def test_green_control_reproduces_the_four_outputs(L2, tmp_path):
    assert build(L2, tmp_path / "g") == L2._TARGETS


def _receipt_doc(L2):
    return json.loads(read(L2.RECEIPT_PATH).decode("utf-8"))


def _digest(doc):
    body = {k: v for k, v in doc.items() if k != "receipt_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _write(path, doc):
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1, ensure_ascii=False))


def test_receipt_file_bytes_whitespace_refused(L2, tmp_path):
    p = tmp_path / "r.json"; io.open(p, "wb").write(read(L2.RECEIPT_PATH) + b"\n")
    got = build(L2, tmp_path / "o", str(p)); assert got[0] == "REFUSED" and "file sha256" in got[1]


def test_receipt_span_changed_with_recomputed_digest_refused(L2, tmp_path):
    doc = _receipt_doc(L2); row = [r for r in doc["rows"] if r.get("outcome") == "EXTENDABLE"][0]
    row["proposed_span"]["span"] += " "; doc["receipt_sha256"] = _digest(doc)
    p = tmp_path / "r.json"; _write(p, doc)
    got = build(L2, tmp_path / "o", str(p)); assert got[0] == "REFUSED" and "file sha256" in got[1]


@pytest.mark.parametrize("field", ["schema", "receipt_sha256", "packet_id", "rows_count"])
def test_receipt_inner_identity_refused_even_with_its_own_file_hash(L2, tmp_path, field):
    doc = _receipt_doc(L2)
    if field == "schema":
        doc["schema"] += "x"
    elif field == "receipt_sha256":
        doc["receipt_sha256"] = ("0" if doc["receipt_sha256"][0] != "0" else "1") + doc["receipt_sha256"][1:]
    elif field == "packet_id":
        doc["rows"][0]["packet_id"] += "x"; doc["receipt_sha256"] = _digest(doc)
    else:
        doc["rows"] = doc["rows"][:-1]; doc["receipt_sha256"] = _digest(doc)
    p = tmp_path / "r.json"; _write(p, doc)
    with pytest.raises(ValueError):
        L2.load_receipt(str(p), expected_file_sha256=sha(read(p)))      # the pin satisfied; the inner identity must refuse
    assert build(L2, tmp_path / "g") == L2._TARGETS                        # the green control beside it


def _mutate_file(path, fn):
    orig = read(path)
    io.open(path, "wb").write(fn(orig))
    return orig


def _restore(path, orig):
    io.open(path, "wb").write(orig)


def test_frozen_inventory_record_changed_refused(L2, tmp_path):
    p = L2.INV.INV; orig = _mutate_file(p, lambda b: b.replace(b'"quote": "', b'"quote": " ', 1))
    try:
        got = build(L2, tmp_path / "o"); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert build(L2, tmp_path / "g") == L2._TARGETS


def test_reconciliation_change_removed_refused_or_missed(L2, tmp_path):
    p = L2.L.RECON; orig = read(p); doc = json.loads(orig.decode("utf-8")); doc["changes"] = doc["changes"][:-1]
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1, ensure_ascii=False))
    try:
        got = build(L2, tmp_path / "o"); assert got != L2._TARGETS
    finally:
        _restore(p, orig)
    assert build(L2, tmp_path / "g") == L2._TARGETS


def test_accepted_reply_byte_refused(L2, tmp_path):
    best = L2.L.accepted(); sid = sorted(best)[0]; p = os.path.join(L2.L.RUN, "replies", best[sid]["raw_name"])
    orig = _mutate_file(p, lambda b: b + b" ")
    try:
        got = build(L2, tmp_path / "o"); assert got != L2._TARGETS
    finally:
        _restore(p, orig)
    assert build(L2, tmp_path / "g") == L2._TARGETS


def test_source_part_quote_text_corrupted_refused(L2, tmp_path):
    """One character inside a located quote's source occurrence, named by the receipt's first
    EXTENDABLE row (old_locator.quote), is changed; the quote no longer locates, so the seam refuses."""
    row = [r for r in _receipt_doc(L2)["rows"] if r.get("outcome") == "EXTENDABLE"][0]
    sid, part, quote = row["source_id"], row["part_ref"], row["old_locator"]["quote"]
    p = L2.L.X + "/inventory_review/inputs/%s.json" % sid
    orig = read(p); doc = json.loads(orig.decode("utf-8"))
    tp = [x for x in doc["event"]["text_parts"] if x["part"] == part][0]
    assert quote in tp["content"]
    tp["content"] = tp["content"].replace(quote, quote[1:], 1)
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    try:
        got = build(L2, tmp_path / "o"); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert build(L2, tmp_path / "g") == L2._TARGETS


def test_preexisting_different_output_refused(L2, tmp_path):
    o = tmp_path / "o"; o.mkdir(); io.open(o / "final_inventory.json", "w").write("{}")
    got = build(L2, o); assert got[0] == "REFUSED" and "different bytes" in got[1]


def test_preexisting_different_versioned_inventory_refused(L2, tmp_path):
    v = tmp_path / "v.json"; io.open(v, "w").write("{}")
    got = build(L2, tmp_path / "o", versioned_path=str(v)); assert got[0] == "REFUSED" and "different bytes" in got[1]


def test_missing_receipt_refused(L2, tmp_path):
    got = build(L2, tmp_path / "o", str(tmp_path / "absent.json")); assert got[0] == "REFUSED"
