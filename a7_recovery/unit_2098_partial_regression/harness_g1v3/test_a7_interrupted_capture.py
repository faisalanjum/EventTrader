"""An official error row without a saved capture must refuse, never crash."""
import collections
import json
import os

import pytest

import a7_g1_build as G
import audit_worker_access as AUD
import g1_fake_state as FAKE
from test_a7_trace_1471 import run, current_g1


@pytest.mark.parametrize("error_at,captures,valid", [
    (1, 2, True),       # matching last error: lawful interrupted result
    (1, 1, False),      # last error was never captured
    (1, 0, False),      # no captures at all
    (None, 2, True),    # two completed answers
    (None, 1, False),   # completed answer missing its capture
    (None, 3, False),   # extra capture
    (0, 2, False),      # an errored row cannot precede another attempted row
])
def test_real_finalizer_handles_every_interrupted_capture_shape(
        current_g1, tmp_path, error_at, captures, valid):
    candidate = current_g1["candidate_dir"]
    document = os.path.join(candidate, G.CANDIDATE_NAME)
    run_dir = str(tmp_path / "run")
    root, root_sha, problems = G.freeze_root(candidate, run_dir, G._sha_file(document))
    assert problems == [], problems
    lanes = [r["lane_id"] for r in root["rows"]][:2]
    identity, problems = G.publish_run(candidate, run_dir, root_sha, lanes)
    assert problems == [], problems
    segment, receipt_sha = identity["segment"], identity["receipt_sha256"]
    packet, problems = G.preflight(candidate, run_dir, segment, root_sha, receipt_sha)
    assert problems == [], problems
    receipt = G.load_receipt(run_dir, segment)
    doc = G._read(document)
    answers, errors, results = {}, {}, []
    for i, arg in enumerate(packet["args"]):
        bound = G.binding_and_parser("G1")[0](doc, arg["batch_id"])
        text = json.dumps([{"question_id": q["question_id"], "produced_idxs": []}
                           for q in bound["questions"]])
        error = "TEST interrupted" if i == error_at else None
        text = None if error else text
        row = collections.OrderedDict((k, arg.get(k)) for k in G.RESULT_BINDING)
        row.update(invocation_sha256=receipt["invocation_sha256"], text=text, error=error)
        results.append(row)
        answers[arg["lane_id"]] = text
        if error:
            errors[arg["lane_id"]] = error
    supplied = (results + results[:1])[:captures]
    G.save_results(run_dir, segment, supplied, root_sha, receipt_sha)
    state = FAKE.build(str(tmp_path), run_dir, segment, G,
                       answers=answers, errors=errors, projects_root=AUD.PROJECTS_ROOT,
                       run_id="wf_interrupt_" + G._sha(run_dir)[:20])
    assert G.record_official_state(run_dir, segment, state, root_sha, receipt_sha) == []
    # A missing capture is not repaired or generated to complete this test.
    # The public finalizer itself must return a named refusal without credit.
    final, rulings, problems = G.finalize_segment(candidate, run_dir, segment,
                                                  root_sha, receipt_sha)
    if valid:
        assert final is not None and problems == [], problems
        assert len(final["validity"]) == len(lanes)
        if error_at is not None:
            assert sum(bool(v) for _lane, v in final["validity"]) == 1
    else:
        assert final is None and rulings == {} and problems
        if captures != len(lanes):
            assert any("capture" in str(p) for p in problems), problems
