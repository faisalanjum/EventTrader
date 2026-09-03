"""A producer's product must be the RIGHT bytes, and its call outcome is a separate
fact (Codex SEQ 1549).

Presence is not correctness. The report recorded the product's identity but compared it
to nothing, so a producer that wrote `BROKEN` to the required path read `applied`. And
the call's historical outcome was credited from local replay alone: a terminated,
outstanding or missing call could still be counted as a success because deterministic
replay happened to produce bytes.

Every expected identity below comes from `products/EXPECTED_PRODUCTS.tsv`, which is
derived from each product's own independent source - a literal `Write`, the committed
bytes served by git, or a deterministic reconstruction whose route lands on an
already-accepted owner pin - never from the report under test.
"""
import contextlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
sys.path.insert(0, R)
import branch_inventory as BI                                 # noqa: E402
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402

H = "bench_1306/.claude/plans/Drivers/experiments/harness/"
ROUTES = ((H + "raw_transport.py", 32847), (H + "audit_worker_access.py", 33828),
          (H + "test_harness_guards.py", 34187))


def expected():
    """-> {line: (path, bytes, sha256)} from the independent evidence file."""
    out = {}
    for row in io.open(os.path.join(R, "products", "EXPECTED_PRODUCTS.tsv"),
                       encoding="utf-8"):
        if row.startswith("#") or not row.strip():
            continue
        line, path, nbytes, sha = row.split("\t")[:4]
        out[int(line)] = (path, int(nbytes), sha)
    return out


def classify(owner, upto):
    with contextlib.redirect_stdout(io.StringIO()):
        return BI.classify(owner, upto)


def test_all_seven_live_products_reconcile_against_their_pins():
    """The complete live set, from all three routes - not a sample of two."""
    want = expected()
    assert len(want) == 7, sorted(want)
    seen = {}
    for owner, upto in ROUTES:
        _rows, _detail, _text, products = classify(owner, upto)
        for line, row in products.items():
            path, nbytes, sha = want[line]
            assert row["path"] == path, (line, row["path"])
            assert row["bytes"] == nbytes, (line, row["bytes"], nbytes)
            assert row["sha256"] == sha, (line, row["sha256"], sha)
            assert row["product_status"] == "correct", (line, row)
            assert row["call_outcome"] == "completed", (line, row)
            assert row["finalizable"] is True, (line, row)
            seen[line] = True
    assert sorted(seen) == sorted(want), sorted(seen)


def test_a_present_but_WRONG_product_fails_closed(monkeypatch):
    """The case that used to read `applied`: right path, present, nonempty, wrong bytes."""
    owner, upto = ROUTES[1]
    with contextlib.redirect_stdout(io.StringIO()):
        _recs, producers = CR.route_records(owner, CR.tree_origin("bench_1306")[0], upto)
    real = RT.apply_saved_edits

    def corrupt(text, records, basename, prepare=None, side=None, result=None):
        line = list(records)[0]
        if line in producers:
            side[producers[line]] = "BROKEN\n"
            return text, {}
        return real(text, records, basename, prepare, side, result)
    monkeypatch.setattr(RT, "apply_saved_edits", corrupt)
    rows, _detail, _text, products = classify(owner, upto)
    for row in products.values():
        assert row["product_status"] == "wrong", row
        assert row["present"] is True          # the identity is still recorded
        assert row["finalizable"] is False, row


def test_a_call_that_returns_without_its_product_FAILS_CLOSED(monkeypatch):
    def no_product(text, records, basename, prepare=None, side=None, result=None):
        return text, {}
    monkeypatch.setattr(RT, "apply_saved_edits", no_product)
    rows, _detail, _text, products = classify(*ROUTES[1])
    for row in products.values():
        assert row["product_status"] == "missing", row
        assert row["present"] is False
        assert row["finalizable"] is False, row


def test_a_product_written_before_a_FAILURE_keeps_both_facts(monkeypatch):
    owner, upto = ROUTES[1]
    with contextlib.redirect_stdout(io.StringIO()):
        _recs, producers = CR.route_records(owner, CR.tree_origin("bench_1306")[0], upto)
    real = RT.apply_saved_edits

    def write_then_raise(text, records, basename, prepare=None, side=None, result=None):
        line = list(records)[0]
        if line in producers:
            side[producers[line]] = "PRODUCT\n"
            raise RuntimeError("after the product")
        return real(text, records, basename, prepare, side, result)
    monkeypatch.setattr(RT, "apply_saved_edits", write_then_raise)
    _rows, _detail, _text, products = classify(owner, upto)
    for row in products.values():
        # both facts, on their own axes - neither overwriting the other
        assert row["product_status"] == "wrong", row
        assert row["call_outcome"] in ("faithfully-failed", "refused"), row
        assert row["present"] is True
        assert row["bytes"] == len("PRODUCT\n")
        assert row["sha256"] and len(row["sha256"]) == 64
        assert row["finalizable"] is False, row


def test_a_TERMINATED_producer_never_executes_and_never_reads_applied(monkeypatch):
    """Termination is decided before any producer runs, exactly as for an owner."""
    owner, upto = ROUTES[1]
    monkeypatch.setattr(RT, "shell_terminated", lambda result: True)
    ran = []
    real = RT.apply_saved_edits

    def watch(text, records, basename, prepare=None, side=None, result=None):
        ran.append(list(records)[0])
        return real(text, records, basename, prepare, side, result)
    monkeypatch.setattr(RT, "apply_saved_edits", watch)
    rows, _detail, _text, products = classify(owner, upto)
    assert not ran, ran
    for row in products.values():
        assert row["call_outcome"] == "terminated", row
        assert row["product_status"] == "not-attempted", row


def test_a_producer_with_no_saved_result_is_not_credited(monkeypatch):
    """Local replay producing bytes does not make history's call a success."""
    owner, upto = ROUTES[1]
    monkeypatch.setattr(RT, "saved_result", lambda line, path=None: None)
    monkeypatch.setattr(RT, "result_present", lambda line, path=None: False)
    rows, _detail, _text, products = classify(owner, upto)
    for row in products.values():
        assert row["call_outcome"] == "missing-result", row
        assert row["finalizable"] is False, row


def test_the_report_lists_producer_waits_and_misses(monkeypatch):
    """A producer wait or miss must appear in the report's own line lists."""
    owner, upto = ROUTES[1]
    monkeypatch.setattr(RT, "saved_result", lambda line, path=None: None)
    monkeypatch.setattr(RT, "result_present", lambda line, path=None: False)
    _rows, _detail, _text, products = classify(owner, upto)
    report = BI.producer_report(products)
    assert report["call_states"]["missing-result"] == [25442, 25450], report
