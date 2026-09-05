"""The exact historical a7_budget_receipt_1493.json from the recovered a7_budget_receipt_1492.json (Codex SEQ 1612 item 1).

A deterministic historical-artifact transform, not a budget owner: the predecessor's complete ordered document is
required whole, its completed_rows must still sum to its completed_before, its G1/G2/G3 shape hashes and values are
carried unchanged; only the schema moves from /1492 to /1493 and the key-review stage gains binding_path and
binding_sha256 after run_dir - exactly what the recorded budget_receipt_1493.py (derived/, provenance) added over
budget_receipt_1492.py - then the owner's internal canonical hash is recomputed and the document is serialized in the
owner's form: json.dumps(doc, indent=1, default=str), no final newline, written once."""
import collections, hashlib, io, json, os, sys

BINDING_PATH = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/targeted_binding.json"


def transform(predecessor_bytes, binding_sha256, binding_path=BINDING_PATH):
    doc = json.loads(predecessor_bytes.decode("utf-8"), object_pairs_hook=collections.OrderedDict)
    if doc.get("schema") != "a7_call_budget_receipt/1492":
        raise ValueError("the predecessor is not the 1492 receipt")
    if sum(r["calls"] for r in doc["completed_rows"]) != doc["completed_before"]:
        raise ValueError("the predecessor's completed_rows do not sum to its completed_before")
    body = collections.OrderedDict((k, v) for k, v in doc.items() if k != "receipt_sha256")
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    if hashlib.sha256(canon.encode("utf-8")).hexdigest() != doc.get("receipt_sha256"):
        raise ValueError("the predecessor's own canonical hash does not hold")
    shapes = {s["stage"]: (s.get("shape_artifact"), s.get("shape_artifact_sha256"), s.get("shape")) for s in body["stages"] if s["stage"] in ("g1", "g2", "g3")}
    out = collections.OrderedDict()
    for k, v in body.items():
        if k == "schema":
            out[k] = "a7_call_budget_receipt/1493"
        elif k == "stages":
            stages = []
            for s in v:
                if s["stage"] == "key_review":
                    ns = collections.OrderedDict()
                    for sk, sv in s.items():
                        ns[sk] = sv
                        if sk == "run_dir":
                            ns["binding_path"] = binding_path; ns["binding_sha256"] = binding_sha256
                    stages.append(ns)
                else:
                    stages.append(s)
            out[k] = stages
        else:
            out[k] = v
    if {s["stage"]: (s.get("shape_artifact"), s.get("shape_artifact_sha256"), s.get("shape")) for s in out["stages"] if s["stage"] in ("g1", "g2", "g3")} != shapes:
        raise ValueError("a G1/G2/G3 shape changed")
    canon = json.dumps(out, sort_keys=True, separators=(",", ":"), default=str)
    out["receipt_sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return json.dumps(out, indent=1, default=str).encode("utf-8")


def main(argv):
    src, dst, binding = argv[1], argv[2], argv[3]
    bsha = hashlib.sha256(open(binding, "rb").read()).hexdigest()
    out = transform(open(src, "rb").read(), bsha)
    if os.path.exists(dst):
        raise SystemExit("refusing to overwrite %s" % dst)
    tmp = dst + ".tmp"; io.open(tmp, "wb").write(out); os.replace(tmp, dst)
    print(len(out), hashlib.sha256(out).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
