# -*- coding: utf-8 -*-
"""Intended-failure mutations of the new rule (Codex SEQ 1794 item 4).

Each mutant disables EXACTLY ONE of the four things the corrected rule now
requires - position, outer record type, presence, payload bytes - and the suite
must name the corresponding forgery as a failure while the lawful control still
passes. A mutant that changes nothing, or that breaks the control, is itself a
finding: it would mean the test proves less than it claims.

The owner is restored from its own bytes in every case, including on error.
"""
import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEW = UNIT + "/view/harness_g1v3"
OWNER = VIEW + "/audit_worker_access.py"
SUITE = "test_g1_declared_input_1792.py"
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
CONTROL = "test_control_every_newly_served_worker_passes_with_its_declared_input"

MUTANTS = [
    ("position_not_required",
     "    if i != index or not isinstance(rec, dict):",
     "    if not isinstance(rec, dict):  # MUTANT: any position accepted",
     "test_a_displaced_input_is_refused_where_it_actually_sits"),
    ("outer_type_not_required",
     '    if rec.get("type") != kind or rec.get("message") is not None:',
     '    if rec.get("message") is not None:  # MUTANT: any outer type accepted',
     "test_the_forgeries_codex_proved_are_refused"),
    ("presence_not_required",
     "    if expected_input is not None and not seen:",
     "    if False:  # MUTANT: a declared input may simply be absent",
     "test_a_missing_input_is_refused_by_name"),
    ("payload_not_required",
     '    return hashlib.sha256(canon.encode("utf-8")).hexdigest() == want',
     "    return True  # MUTANT: any payload accepted",
     "test_an_undeclared_payload_is_refused"),
]


def suite(label):
    argv = [PY, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
            "--no-header", "-rf", SUITE]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=VIEW,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/logs/mutant_%s.log" % (UNIT, label), "w", encoding="utf-8").write(
        "COMMAND: %s\nCWD: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n"
        "--- EXIT ---\n%d\n" % (" ".join(argv), VIEW, r.stdout, r.stderr,
                                r.returncode))
    failed = [f.split("::")[-1].split("[")[0]
              for f in re.findall(r"^FAILED (\S+)", r.stdout, re.M)]
    return failed, r.returncode


def main():
    original = io.open(OWNER, encoding="utf-8").read()
    before, rc = suite("control_before")
    if before or rc != 0:
        print("REFUSED: the unmutated suite is not green: %s" % before[:4])
        return 1
    records, bad = [], []
    try:
        for name, anchor, replacement, must_fail in MUTANTS:
            if original.count(anchor) != 1:
                print("  %-24s ANCHOR NOT UNIQUE (%d)"
                      % (name, original.count(anchor)))
                bad.append(name)
                continue
            io.open(OWNER, "w", encoding="utf-8").write(
                original.replace(anchor, replacement, 1))
            failed, code = suite(name)
            caught = must_fail in failed
            control_ok = CONTROL not in failed
            ok = caught and control_ok
            if not ok:
                bad.append(name)
            records.append(collections.OrderedDict([
                ("mutant", name), ("disabled", anchor.strip()),
                ("test_that_must_fail", must_fail), ("it_failed", caught),
                ("lawful_control_still_passes", control_ok),
                ("failures", len(failed)), ("failed_tests", failed[:8]),
                ("exit", code), ("intended_failure_proved", ok)]))
            print("  %-24s failures %-3d caught %-5s control ok %-5s  %s"
                  % (name, len(failed), caught, control_ok,
                     "ok" if ok else "<-- NOT PROVED"))
    finally:
        io.open(OWNER, "w", encoding="utf-8").write(original)
    restored = hashlib.sha256(io.open(OWNER, "rb").read()).hexdigest()
    after, rc = suite("control_after")
    io.open(UNIT + "/logs/MUTANT_RECORDS_1794.json", "w",
            encoding="utf-8").write(json.dumps(collections.OrderedDict([
                ("suite", SUITE), ("lawful_control", CONTROL),
                ("owner_restored_sha256", restored),
                ("owner_unchanged", restored == hashlib.sha256(
                    original.encode("utf-8")).hexdigest()),
                ("green_before", not before), ("green_after", not after and rc == 0),
                ("not_proved", bad), ("mutants", records)]), indent=1) + "\n")
    print("  owner restored : %s  suite green again: %s"
          % (restored[:16], not after and rc == 0))
    return 1 if bad or after else 0


if __name__ == "__main__":
    sys.exit(main())
