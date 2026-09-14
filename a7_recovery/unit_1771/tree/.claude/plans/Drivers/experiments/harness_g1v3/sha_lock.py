#!/usr/bin/env python3
"""WP-KEYS lock writer + verifier (0 LLM, no network). WorkOrder section 1.4.

  lock   --key <jsonl> --protocol <md> [--locked-by fable] [--drafted-by <id>] [--locked-at <iso>]
         [--out <lock.json>] [--allow-mined] [--force]
         Runs key_lint first; REFUSES to lock a key that does not lint clean (override with --force).
         Writes <K>.lock.json = {file, sha256(jsonl bytes), n_records, strata, locked_by, locked_at,
         drafted_by, protocol_sha256, lint_clean}.  A locked key is immutable; fixes need a NEW version.

  verify --key <jsonl> --lock <lock.json> [--protocol <md>]
         Recompute sha256(jsonl) vs lock.sha256 (+ protocol vs protocol_sha256 when --protocol given).
         Exit 0 on match; non-zero + message on mismatch. Pre-first-call runner check AND scorer re-verify."""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import key_lint


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _strata(stats):
    return {"planted_different": stats["gold_DIFFERENT"], "planted_same": stats["gold_SAME"],
            "mined": stats["mined"], "by_family_different": stats["by_family_DIFFERENT"]}


def cmd_lock(a):
    ok, errs, stats = key_lint.lint_key(a.key, allow_mined=a.allow_mined)
    if not ok and not a.force:
        print("REFUSE-LOCK: key does not lint clean:", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
    out = a.out or (os.path.splitext(a.key)[0] + ".lock.json")
    if os.path.exists(out) and not a.force:
        print("REFUSE-LOCK: %s exists (locked keys are immutable; use a new version)" % out, file=sys.stderr)
        sys.exit(1)
    from datetime import datetime, timezone
    lock = {"file": os.path.basename(a.key), "sha256": sha256_file(a.key), "n_records": stats["n_records"],
            "strata": _strata(stats), "locked_by": a.locked_by,
            "locked_at": a.locked_at or datetime.now(timezone.utc).isoformat(),
            "drafted_by": a.drafted_by, "protocol_sha256": sha256_file(a.protocol), "lint_clean": ok}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(lock, fh, indent=2, sort_keys=True)
    print(json.dumps({"wrote": out, "sha256": lock["sha256"], "protocol_sha256": lock["protocol_sha256"],
                      "n_records": lock["n_records"], "strata": lock["strata"], "lint_clean": ok}, sort_keys=True))


def cmd_verify(a):
    lock = json.load(open(a.lock, encoding="utf-8"))
    problems = []
    got = sha256_file(a.key)
    if got != lock.get("sha256"):
        problems.append("KEY SHA MISMATCH: file=%s lock=%s" % (got, lock.get("sha256")))
    if a.protocol:
        pgot = sha256_file(a.protocol)
        if pgot != lock.get("protocol_sha256"):
            problems.append("PROTOCOL SHA MISMATCH: file=%s lock=%s" % (pgot, lock.get("protocol_sha256")))
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        sys.exit(2)
    print(json.dumps({"verified": True, "key": os.path.basename(a.key), "sha256": got}, sort_keys=True))


def main(argv=None):
    ap = argparse.ArgumentParser(description="WP-KEYS lock writer + verifier (0 LLM)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("lock")
    pl.add_argument("--key", required=True); pl.add_argument("--protocol", required=True)
    pl.add_argument("--locked-by", default="fable"); pl.add_argument("--drafted-by", default="unset")
    pl.add_argument("--locked-at", default=None); pl.add_argument("--out", default=None)
    pl.add_argument("--allow-mined", action="store_true"); pl.add_argument("--force", action="store_true")
    pl.set_defaults(func=cmd_lock)
    pv = sub.add_parser("verify")
    pv.add_argument("--key", required=True); pv.add_argument("--lock", required=True); pv.add_argument("--protocol", default=None)
    pv.set_defaults(func=cmd_verify)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
