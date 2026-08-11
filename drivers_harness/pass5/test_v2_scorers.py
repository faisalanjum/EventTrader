"""Critical tests for v2_scorers — the scorer MUST catch over-merge / collapse-to-generic
(the v1 #1 failure) and reward a distinct producer. Offline (use_embeddings=False; core-match
is the over-merge signal). Uses the real stream ground + synthetic producer registries."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v2_schema import Registry
from v2_stream import Stream
import v2_scorers as S

ST = Stream()
GROUND = ST.relatedness_ground()


def _producer(core_fn):
    """Build a registry where each ground event emits the core given by core_fn(axis,bucket,eid,idx)."""
    reg = Registry()
    for axis, buckets in GROUND.items():
        for bucket, eids in buckets.items():
            for i, eid in enumerate(eids):
                metric, mech = core_fn(axis, bucket, eid, i)
                reg.admit_event(eid, ST.sidechannel(eid)["ticker"],
                                [{"metric": metric, "mechanism": mech, "direction": "long", "state": "up"}],
                                date="2024-01-01")
    return reg


def _distinct(axis, bucket, eid, i):
    return (bucket, "x")            # each ground bucket -> its OWN distinct core (faithful)

def _collapse(axis, bucket, eid, i):
    return (axis, "generic")        # too-COARSE: all buckets in an axis share one core

def _oversplit(axis, bucket, eid, i):
    return (f"{bucket}{abs(hash(eid)) % 100000}", "x")   # too-FINE: a unique core per event


def test_distinct_producer_high_precision_AND_recall():
    rel = S.relatedness(_producer(_distinct), ST, use_embeddings=False)
    for axis in ("metric_sib", "seg_sib", "object_sib", "peer"):
        assert rel[axis]["reuse_precision"] >= 0.95, (axis, rel[axis])
        assert rel[axis]["reuse_recall"] >= 0.95, (axis, rel[axis])

def test_collapse_FAILS_precision():
    rel = S.relatedness(_producer(_collapse), ST, use_embeddings=False)
    for axis in ("metric_sib", "seg_sib", "object_sib"):
        nb = rel[axis]["n_buckets"]
        assert rel[axis]["reuse_precision"] <= (1.0 / nb) + 0.25, (axis, rel[axis])   # collapse -> low precision
        assert rel[axis]["reuse_recall"] >= 0.9                                       # ...but recall stays high

def test_oversplit_FAILS_recall():
    rel = S.relatedness(_producer(_oversplit), ST, use_embeddings=False)
    for axis in ("metric_sib", "seg_sib", "object_sib", "peer"):
        assert rel[axis]["reuse_recall"] <= 0.1, (axis, rel[axis])    # over-split -> recall collapses (no reuse)

def test_collapse_detected_by_convergence_sentinel():
    reg = _producer(_collapse)
    conv = S.convergence(reg, ST, use_embeddings=False)
    assert conv["n_collapses"] > 0                      # the sentinel FLAGS the merge
    # specifically the metric-sibling collapse (revenue vs eps guidance) is caught
    axes = {c["axis"] for c in conv["collapses"]}
    assert "metric_sib" in axes and "object_sib" in axes

def test_distinct_producer_no_collapse():
    reg = _producer(_distinct)
    conv = S.convergence(reg, ST, use_embeddings=False)
    assert conv["n_collapses"] == 0

def test_object_sib_revcapex_overmerge_caught():
    # the canonical killer: datacenter_revenue vs datacenter_capex merged -> caught
    reg = _producer(lambda axis, b, eid, i: ("datacenter", "x") if axis == "object_sib" and b.startswith("datacenter")
                    else (b, "x"))
    conv = S.convergence(reg, ST, use_embeddings=False)
    merged = [c for c in conv["collapses"] if set(c["buckets"]) == {"datacenter_revenue", "datacenter_capex"}]
    assert merged, conv["collapses"]                    # rev-vs-capex merge is flagged

def test_direction_and_reject_objective():
    reg = _producer(_distinct)
    d = S.direction(reg, ST)
    assert 0.0 <= d["direction_accuracy"] <= 1.0 and d["n"] > 100
    rj = S.reject(reg, ST)
    # the synthetic producer emitted on NON-reject ground only -> reject events untouched -> precision 1.0
    assert rj["reject_precision"] == 1.0


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
