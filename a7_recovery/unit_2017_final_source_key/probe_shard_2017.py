# -*- coding: utf-8 -*-
"""READ-ONLY probe: what shape does the owner's accepted shard actually have?

Prints structure only - keys, types and lengths - so the closeout counts the
real thing instead of a shape I assumed. No model call, nothing written.
"""
import collections
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A7 + "/unit_2009/owner")
import a4_review_composite as R                                    # noqa: E402

SK = R.SK
RUN = os.environ["A7_RUN"]
PKG = os.environ["A7_PACKAGE"]
REVIEW_RUN = os.path.join(os.path.dirname(R.OLD_RUN), "review_2015")
REVIEW_PKG = os.path.join(os.path.dirname(R.OLD_RUN), "closure_2015")


def shape(value, depth=0):
    if isinstance(value, dict):
        return collections.OrderedDict(
            (k, shape(v, depth + 1) if depth < 2 else type(v).__name__)
            for k, v in list(value.items())[:12])
    if isinstance(value, list):
        return ["list[%d]" % len(value)] + (
            [shape(value[0], depth + 1)] if value and depth < 2 else [])
    return type(value).__name__


with R.final_scope(REVIEW_RUN, REVIEW_PKG):
    shards, raws, bad = SK.accepted_shards(RUN, package=PKG)
    out = collections.OrderedDict()
    out["counts"] = {"shards": len(shards), "raws": len(raws), "problems": bad}
    out["shards_type"] = type(shards).__name__
    first = sorted(shards)[0] if isinstance(shards, dict) else None
    out["first_key"] = first
    doc = shards[first] if first is not None else (
        shards[0] if isinstance(shards, list) and shards else None)
    out["first_shard_shape"] = shape(doc)
    if isinstance(doc, dict) and isinstance(doc.get("rows"), list) and doc["rows"]:
        out["first_row_type"] = type(doc["rows"][0]).__name__
        out["first_row"] = (shape(doc["rows"][0])
                            if isinstance(doc["rows"][0], dict)
                            else str(doc["rows"][0])[:120])
    rk = raws[first] if isinstance(raws, dict) and first in raws else None
    out["first_raw_type"] = type(rk).__name__
    out["first_raw_head"] = str(rk)[:160] if rk is not None else None
print(json.dumps(out, indent=1, default=str))
