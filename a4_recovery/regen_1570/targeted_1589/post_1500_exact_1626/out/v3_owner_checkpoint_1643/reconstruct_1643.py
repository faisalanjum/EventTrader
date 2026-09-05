# -*- coding: utf-8 -*-
"""Codex SEQ 1643: materialize the two exact pre-1482 owners by SHORT checkpoint replay, reusing the existing engine
hard_review_1495/derive_hr_1495.py (source-loaded, never altered). a6_launch_freeze.py is its recorded 19-step cat/append/block
chain stopping after physical line 75130; raw_transport.py is the preserved base raw_transport_64429e5f.py plus the four
recorded blocks at 72839/73303/73534/73562. Endpoints are OUTPUT checks. Publish the two owners only together, after both match.
One deterministic run; on any mismatch or refusal, write the failure and publish nothing."""
import hashlib, io, json, os, sys, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
T = "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
ENGINE_DIR = T + "/hard_review_1495"; sys.path.insert(0, ENGINE_DIR)
import derive_hr_1495 as D
sha = lambda b: hashlib.sha256(b).hexdigest(); fsha = lambda p: sha(io.open(p, "rb").read())
RAW_BASE = T + "/post_1500_exact_1626/inputs/owners/raw_transport_64429e5f.py"
RAW_BASE_SHA = "64429e5fb59d19b63bbabe4af8809177755c3822a400e976532c579e15d77df5"
A6_STEPS = [(55324, "cat"), (55327, "append"), (55336, "append"), (55339, "append"), (55345, "block"),
            (72690, "block"), (73797, "block"), (74049, "block"), (74070, "block"), (74370, "block"),
            (74380, "block"), (74645, "block"), (74848, "block"), (74873, "block"), (74935, "block"),
            (74940, "block"), (75104, "block"), (75112, "block"), (75130, "block")]
RAW_STEPS = [(72839, "block"), (73303, "block"), (73534, "block"), (73562, "block")]
A6_TARGET = "1250c47f29ee9725e7313d95d8e0ad19666bc8ba98767cacec5311f46b5202f5"; A6_BYTES = 26988
RAW_TARGET = "b3ea04bfe7cd7562bf746d59d904f40330ecbfb302e9f51be92348679c35d795"
CHECKPOINT_LINES = (77189, 77959)                    # the physical tool-result lines that independently print the raw pre-edit hash
A6_DERIVATION_COPIES = [ENGINE_DIR + "/derived/DERIVATION.tsv", ENGINE_DIR + "/derived_probe/DERIVATION.tsv", ENGINE_DIR + "/derived_probe2/DERIVATION.tsv"]


def jsonl_line_sha(ln):
    if D._lines is None:                             # load the transcript read-only; never route a tool-result line through record()
        with io.open(D.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
            D._lines = fh.readlines()
    if not (1 <= ln <= len(D._lines)):
        raise IndexError("physical line %d out of range (1..%d)" % (ln, len(D._lines)))
    return sha(D._lines[ln - 1].encode("utf-8"))


def rows_for(name, log):
    out = []
    for r in log:
        kind, ln = r[0], r[1]
        if kind == "base":
            out.append((name, "base", "-", "-", "-", "-", r[4], r[5])); continue
        out.append((name, kind, ln, r[2], jsonl_line_sha(ln), r[3], r[4], r[5]))
    return out


def main():
    scratch = HERE + "/scratch"; os.makedirs(scratch, exist_ok=True)
    result = {"command": "python -B reconstruct_1643.py", "engine": {"file": ENGINE_DIR + "/derive_hr_1495.py", "sha256": fsha(ENGINE_DIR + "/derive_hr_1495.py")}}
    # raw base must equal the preserved sha before anything is applied
    if not os.path.isfile(RAW_BASE) or fsha(RAW_BASE) != RAW_BASE_SHA:
        result["error"] = "raw base is not the preserved %s (got %s)" % (RAW_BASE_SHA[:16], fsha(RAW_BASE)[:16] if os.path.isfile(RAW_BASE) else "missing")
        io.open(HERE + "/FAILURE.json", "w").write(json.dumps(result, indent=1) + "\n"); print("REFUSED:", result["error"]); return 2
    try:
        a6_text, a6_log = D.derive("a6_launch_freeze.py", A6_STEPS, scratch, base=None)
        raw_text, raw_log = D.derive("raw_transport.py", RAW_STEPS, scratch, base=RAW_BASE)
    except Exception as exc:
        result["error"] = "engine refused: %s: %s" % (type(exc).__name__, str(exc)[:200]); result["traceback"] = traceback.format_exc()
        io.open(HERE + "/FAILURE.json", "w").write(json.dumps(result, indent=1, default=str) + "\n"); print("REFUSED:", result["error"]); return 2
    a6_sha, a6_len = sha(a6_text.encode("utf-8")), len(a6_text.encode("utf-8"))
    raw_sha, raw_len = sha(raw_text.encode("utf-8")), len(raw_text.encode("utf-8"))
    a6_ok = a6_sha == A6_TARGET and a6_len == A6_BYTES
    raw_ok = raw_sha == RAW_TARGET
    result["a6"] = {"sha256": a6_sha, "bytes": a6_len, "target": A6_TARGET, "target_bytes": A6_BYTES, "match": a6_ok}
    result["raw"] = {"sha256": raw_sha, "bytes": raw_len, "target": RAW_TARGET, "match": raw_ok, "base_sha256": RAW_BASE_SHA}
    all_rows = rows_for("a6_launch_freeze.py", a6_log) + rows_for("raw_transport.py", raw_log)
    if not (a6_ok and raw_ok):                        # refuse: publish neither owner
        result["published"] = False; io.open(HERE + "/FAILURE.json", "w").write(json.dumps(result, indent=1) + "\n")
        io.open(HERE + "/DERIVATION.tsv", "w").write("file\tstep\ttranscript_line\ttimestamp\tjsonl_line_sha256\tcount\tresult_sha256\tresult_bytes\n" + "".join("\t".join(str(x) for x in r) + "\n" for r in all_rows))
        print("ENDPOINT MISS a6=%s raw=%s -> published nothing" % (a6_ok, raw_ok)); return 2
    # both match: publish the two owners together, the derivation table, and the manifest
    io.open(HERE + "/a6_launch_freeze.py", "w", encoding="utf-8", newline="").write(a6_text)
    io.open(HERE + "/raw_transport.py", "w", encoding="utf-8", newline="").write(raw_text)
    io.open(HERE + "/DERIVATION.tsv", "w").write("file\tstep\ttranscript_line\ttimestamp\tjsonl_line_sha256\tcount\tresult_sha256\tresult_bytes\n" + "".join("\t".join(str(x) for x in r) + "\n" for r in all_rows))
    man = [("caller reconstruct_1643.py", fsha(HERE + "/reconstruct_1643.py")),
           ("engine derive_hr_1495.py", fsha(ENGINE_DIR + "/derive_hr_1495.py")),
           ("raw base raw_transport_64429e5f.py", fsha(RAW_BASE)),
           ("DERIVATION.tsv", fsha(HERE + "/DERIVATION.tsv")),
           ("a6_launch_freeze.py", fsha(HERE + "/a6_launch_freeze.py")),
           ("raw_transport.py", fsha(HERE + "/raw_transport.py"))]
    for ln in CHECKPOINT_LINES: man.append(("transcript_line_%d (raw pre-edit hash print)" % ln, jsonl_line_sha(ln)))
    for p in A6_DERIVATION_COPIES:
        if os.path.isfile(p): man.append(("a6_endpoint_evidence %s" % os.path.relpath(p, T), fsha(p)))
    io.open(HERE + "/MANIFEST.tsv", "w").write("".join("%s\t%s\n" % (n, h) for n, h in man))
    result["published"] = True; io.open(HERE + "/RESULT.json", "w").write(json.dumps(result, indent=1) + "\n")
    print("PUBLISHED a6 %s (%d B) raw %s -> both endpoints match" % (a6_sha[:16], a6_len, raw_sha[:16])); return 0


if __name__ == "__main__":
    try: rc = main()
    except BaseException: traceback.print_exc(); rc = 1
    sys.exit(rc)
