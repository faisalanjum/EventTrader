"""Throwaway diagnostic: when does the V3 raw set lose labels?"""
import os, sys, json
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final as F                                  # noqa: E402
import test_kfields_final_1379 as T9                             # noqa: E402
from test_kfields_final_1387 import dec, split                   # noqa: E402,F401
from test_kfields_final_1384 import world                        # noqa: E402,F401
from test_kfields_final_1390 import v4, build_v4_call            # noqa: E402,F401
K, EV = F.K, T9.EV


def _look(tag, b3, b4):
    for name, b in (("b3", b3), ("b4", b4)):
        F._accepted_shards_cached.cache_clear()      # FRESH every time
        sh, raws, bad = F.accepted_shards(b.decision, b, "decision")
        print("  %-10s %s raws=%d bad=%s" % (tag, name, len(raws), bad[:2]))
    r = os.path.join(b3.decision, K.RECEIPT_NAME)
    print("  %-10s v3 receipt sha=%s" % (tag, F.INV.sha_file(r)[:16]))


def test_diag(v4, dec, tmp_path):
    b3, b4 = v4["b3"], v4["b4"]
    labels = F.v4_labels(b4)
    print("\n--- diagnostic ---")
    _look("start", b3, b4)
    out = str(tmp_path / "c")
    print("  prepare_v4 ->", F.prepare_v4(out, b3)["ok"])
    _look("after prep", b3, b4)
    p = build_v4_call(dec["session"], b3, labels[0], v4["answers"][labels[0]],
                      run_id="wfc_0")
    print("  built call for", labels[0])
    _look("after call", b3, b4)
    F.record_state(out, p)
    _look("after rec", b3, b4)
    # the exact transition that failed: the SECOND label
    import traceback
    try:
        p2 = build_v4_call(dec["session"], b3, labels[1],
                           v4["answers"][labels[1]], run_id="wfc_1")
        print("  built call for", labels[1])
        _look("after b2", b3, b4)
        F.record_state(out, p2)
        _look("after rec2", b3, b4)
        print("  SECOND RECORD OK - not reproduced here")
    except Exception:
        traceback.print_exc()
        # what did the RECONSTRUCTED bound see?
        rec = F.K._load(os.path.join(out, F.K.RECEIPT_NAME))
        print("  receipt bound block:", json.dumps(rec.get("bound"))[:300])
