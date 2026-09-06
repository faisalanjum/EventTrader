# -*- coding: utf-8 -*-
"""Host-side mutant driver (Codex SEQ 1782 item 1).

The boundary binds the owner READ-ONLY - correctly - so a mutant is applied to
this unit's PRIVATE view on the host, the map is re-pinned, the suite runs
inside the unchanged boundary, and the owner is restored immediately. Each
mutant must produce failures AND leave its lawful control passing.
"""
import io, json, os, re, subprocess, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = UNIT + "/view/harness_g1v3/audit_worker_access.py"
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
PY_ = "/home/faisal/EventMarketDB/venv/bin/python3"

MUTANTS = [
    ("bypass_cached_metadata", "def _resumed_cached_row(pr, rid_dir, lane):",
     "def _resumed_cached_row(pr, rid_dir, lane):\n    return True  # MUTANT",
     "test_a_lawful_cached_state_is_accepted"),
    ("bypass_script_identity", "def _same_published_script(claim, published):",
     "def _same_published_script(claim, published):\n    return True  # MUTANT",
     "test_control_the_exact_published_script_path_is_accepted"),
    ("bypass_transcript_check",
     '        problems += ["%s: %s" % (label, w) for w in why]',
     "        problems += []  # MUTANT: transcript findings dropped",
     "test_control_the_unchanged_fresh_state_is_accepted"),
]


def suite(label):
    subprocess.run([sys.executable, UNIT + "/build_a7_map_1781.py"],
                   capture_output=True, cwd=UNIT)
    subprocess.run([PY_, "-B", L + "/launcher/boundary.py", "--host",
                    UNIT + "/a7_map_1781.tsv", UNIT + "/ledger/run_tests_1781.py",
                    label], capture_output=True, text=True, timeout=600)
    log = UNIT + "/logs/tests_%s.log" % label
    out = io.open(log, encoding="utf-8").read() if os.path.isfile(log) else ""
    failed = [f.split("::")[-1].split("[")[0]
              for f in re.findall(r"^FAILED (\S+)", out, re.M)]
    exit_line = re.search(r"--- EXIT ---\n(-?\d+)", out)
    return failed, (int(exit_line.group(1)) if exit_line else None)


def main():
    original = io.open(OWNER, encoding="utf-8").read()
    records, bad = [], []
    try:
        for name, anchor, replacement, control in MUTANTS:
            if original.count(anchor) != 1:
                print("  %-24s ANCHOR NOT UNIQUE" % name); bad.append(name); continue
            io.open(OWNER, "w", encoding="utf-8").write(
                original.replace(anchor, replacement, 1))
            failed, code = suite("mutant_" + name)
            control_ok = control not in failed
            ok = bool(failed) and control_ok
            records.append({"mutant": name, "disabled": anchor.strip(),
                            "failures": len(failed), "failed_tests": failed[:6],
                            "lawful_control": control,
                            "control_still_passes": control_ok,
                            "nested_pytest_exit": code, "sufficient": ok})
            print("  %-24s failures=%-3d control_passes=%-5s nested_exit=%s  %s"
                  % (name, len(failed), control_ok, code,
                     "OK" if ok else "INSUFFICIENT"))
            if not ok:
                bad.append(name)
            io.open(OWNER, "w", encoding="utf-8").write(original)
    finally:
        io.open(OWNER, "w", encoding="utf-8").write(original)
        subprocess.run([sys.executable, UNIT + "/build_a7_map_1781.py"],
                       capture_output=True, cwd=UNIT)
    io.open(UNIT + "/logs/MUTANT_RECORDS.json", "w", encoding="utf-8").write(
        json.dumps(records, indent=1) + "\n")
    restored = io.open(OWNER, encoding="utf-8").read() == original
    print("owner restored byte-for-byte:", restored)
    print("%d mutants, %d insufficient %s" % (len(MUTANTS), len(bad), bad or ""))
    return 1 if (bad or not restored) else 0


if __name__ == "__main__":
    sys.exit(main())
