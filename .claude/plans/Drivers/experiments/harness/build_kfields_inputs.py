"""K-fields draft-input builder v3 — IMMUTABLE manifest, write-nothing checks.

Modes:
  (default) check: READ-ONLY. Loads the FROZEN manifest
            (draft_inputs.hashes.json) and verifies the draft_inputs dir
            against it — FAIL on a missing file, an EXTRA file, or a changed
            hash. Optionally also recomputes each input from sources and
            reports drift (the frozen bytes stay the instrument). Writes
            NOTHING — no file, no manifest, ever.
  --write   FIRST MATERIALIZATION ONLY: refuses if draft_inputs/ is non-empty
            OR the manifest already exists. Writes the 36 inputs, then the
            manifest ONCE (36 per-file sha256 + one combined). After this the
            manifest is FROZEN — no mode ever rewrites it.

Field note: each input's `packet_sha256` is the WP-FA SOURCE-CONTENT hash
copied from the event fixture's own `sha256` field — a CONTENT hash, NOT the
byte hash of the fixture file. Menu rule: prior public 10-K/Q(/A) filings at
`created <= event_time` (approved ≤; date T00:00:00 anchors keep the current
filing's intraday timestamp out of its own menu).
Run from experiments/:
  venv/bin/python harness/build_kfields_inputs.py [--write] [--recompute]"""
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(_HERE, "..", "fixtures", "events")
OUT = os.path.join(_HERE, "..", "keys", "K-fields", "draft_inputs")
HASHES = os.path.join(_HERE, "..", "keys", "K-fields",
                      "draft_inputs.hashes.json")


def compose(fn, ev_dir=EV):
    sys.path.insert(0, _HERE)
    from slice_menu_probe import menu_for
    p = json.load(open(os.path.join(ev_dir, fn)))
    ts = p["date"] + "T00:00:00" if len(p["date"]) == 10 else p["date"]
    tokens, raw, logs = menu_for(p["ticker"], ts)
    doc = {"source_id": p["source_id"], "source_type": p["source_type"],
           "ticker": p["ticker"], "fye_month": p["fye_month"],
           "event_date": p["date"], "packet_sha256": p["sha256"],
           "text_parts": p["text_parts"], "menu_tokens": tokens,
           "menu_n_raw": len(raw), "menu_logs_n": len(logs)}
    return json.dumps(doc, sort_keys=True).encode()


def check(out_dir=OUT, hashes_path=HASHES, recompute=False, ev_dir=EV):
    """Read-only verification against the FROZEN manifest. Writes nothing."""
    if not os.path.exists(hashes_path):
        print("FAIL: frozen manifest missing — nothing to verify against")
        return 1
    frozen = json.load(open(hashes_path))
    problems = []
    on_disk = {x for x in os.listdir(out_dir)
               if x.endswith(".json")} if os.path.isdir(out_dir) else set()
    expected = set(frozen["files"])
    for fn in sorted(expected - on_disk):
        problems.append(f"MISSING frozen file: {fn}")
    for fn in sorted(on_disk - expected):
        problems.append(f"EXTRA file not in the frozen manifest: {fn}")
    combined = hashlib.sha256()
    for fn in sorted(expected & on_disk):
        data = open(os.path.join(out_dir, fn), "rb").read()
        got = hashlib.sha256(data).hexdigest()
        if got != frozen["files"][fn]:
            problems.append(f"CHANGED: {fn} sha {got[:12]} != frozen "
                            f"{frozen['files'][fn][:12]}")
        combined.update(data)
    if not problems and combined.hexdigest() != frozen["combined_sha256"]:
        problems.append("combined hash mismatch despite per-file match "
                        "(ordering corruption)")
    if recompute and not problems:
        for fn in sorted(expected):
            if compose(fn, ev_dir) != open(os.path.join(out_dir, fn),
                                           "rb").read():
                problems.append(f"RECOMPUTE-DRIFT: {fn} (graph/law moved; the "
                                f"FROZEN file remains the instrument)")
    print(f"checked {len(expected)} manifest entries; problems: "
          f"{len(problems)}")
    for p in problems[:12]:
        print(" ", p)
    if not problems:
        print("verify: frozen inputs intact"
              + (" and byte-reproducible" if recompute else ""))
    return 1 if problems else 0


def write(out_dir=OUT, hashes_path=HASHES, ev_dir=EV):
    """First materialization ONLY; then the manifest freezes forever."""
    if os.path.exists(hashes_path):
        print("REFUSED: the frozen manifest already exists — it is immutable.")
        return 2
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        print("REFUSED: draft_inputs/ is not empty — frozen exam inputs are "
              "never overwritten.")
        return 2
    os.makedirs(out_dir, exist_ok=True)
    per, combined = {}, hashlib.sha256()
    for fn in sorted(os.listdir(ev_dir)):
        data = compose(fn, ev_dir)
        with open(os.path.join(out_dir, fn), "wb") as f:
            f.write(data)
        per[fn] = hashlib.sha256(data).hexdigest()
        combined.update(data)
    doc = {"combined_sha256": combined.hexdigest(), "files": per,
           "n": len(per), "frozen": True,
           "note": "IMMUTABLE after creation. packet_sha256 inside each input "
                   "= WP-FA SOURCE-CONTENT hash (never the fixture file's "
                   "byte hash); menu rule = created <= event_time (approved)"}
    with open(hashes_path, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    print(f"materialized {len(per)} inputs; manifest FROZEN "
          f"{doc['combined_sha256']}")
    return 0


if __name__ == "__main__":
    if "--write" in sys.argv:
        sys.exit(write())
    sys.exit(check(recompute="--recompute" in sys.argv))
