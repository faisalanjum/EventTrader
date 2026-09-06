# -*- coding: utf-8 -*-
"""Isolated tests for the two placement rules (Codex SEQ 1700, isolated per 1702).

Nothing here may touch the live projection, so neither test runs the placer
against the unit: the placer is checked at its own decision seam, and the
reconstruction's refusal is exercised with its destination pointed at a private
disposable tree. The live bench, runs, manifest and session store are digested
before and after and must come out byte-identical - that proof is itself one of
the checks, so an accidentally mutating test fails instead of polluting.
"""
import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
SCRATCH = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
           "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
sys.path.insert(0, UNIT + "/launcher")
import boundary                                          # the unit's digest owner

LIVE = {"bench": UNIT + "/bench", "runs": UNIT + "/runs",
        "manifest": UNIT + "/manifest/PROJECTION_PLACED.tsv",
        "session_store": UNIT + "/session_store"}

failures = []
ran = [0]


def check(name, ok, detail=""):
    ran[0] += 1
    print("%s %s%s" % ("ok  " if ok else "BAD ", name, "" if ok else "  <- " + detail))
    if not ok:
        failures.append(name)


def digests():
    return {k: boundary.source_sha(v) for k, v in LIVE.items()}


def test_the_placer_has_one_acceptance_route():
    """The expected hash may come from the canonical pin table and nowhere else."""
    src = io.open(UNIT + "/tests/place_missing.py", encoding="utf-8").read()
    tree = ast.parse(src)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for el in (t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]):
                    if isinstance(el, ast.Name):
                        names.add(el.id)
    check("no basename-unanimity resolver", "unanimous_byte" not in names,
          "place_missing still defines unanimous_byte")
    check("no first-same-suffix directory route", "dir_placed" not in names,
          "place_missing still defines dir_placed")

    sources = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "want_sha" for t in n.targets):
            v = n.value
            sources.append(isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                           and v.func.attr == "get"
                           and isinstance(v.func.value, ast.Name) and v.func.value.id == "pins")
    check("every expected hash comes from the canonical pins",
          bool(sources) and all(sources),
          "want_sha assigned from %d source(s), pins-only=%s" % (len(sources), sources))


def test_a_preserved_destination_makes_the_reconstruction_refuse():
    """Exercised against a DISPOSABLE destination, never the live runs directory."""
    tmp = tempfile.mkdtemp(prefix="placement_rules_", dir=SCRATCH)
    try:
        dest = os.path.join(tmp, "a7_v3_prepared_run_1479")
        os.makedirs(dest)
        io.open(dest + "/receipt.json", "w", encoding="utf-8").write("{}\n")
        before = boundary.dir_manifest_sha(dest)
        r = subprocess.run(
            [PY, "-B", UNIT + "/launcher/era_v3_1479.py"], capture_output=True, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", KEEP_DIR=tmp,
                     V3_PINS=P + "/pins_1636.json",
                     V3_TSV=P + "/inputs/history_store/WORKFLOWS.tsv", V3_LABEL="v3_1479"))
        out = r.stdout + r.stderr
        check("a preserved destination is refused before any work",
              r.returncode == 4 and "already preserved" in out,
              "rc=%s out=%s" % (r.returncode, out[-300:]))
        check("the preserved destination is untouched",
              boundary.dir_manifest_sha(dest) == before, "contents changed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_the_placer_normalizes_and_refuses_escapes():
    """The owner's OWN escape predicate, evaluated on samples - the script is
    never run, so no live state can move."""
    tree = ast.parse(io.open(UNIT + "/tests/place_missing.py", encoding="utf-8").read())
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "escapes" for t in n.targets))
    cond = ast.unparse(node.value.generators[0].ifs[0])
    escapes = lambda path: bool(eval(cond, {"os": os, "w": os.path.normpath(path)}))

    inside = (".claude/plans/Drivers/experiments/harness_g1v3/.."
              "/keys/K-fields/draft_inputs.hashes.json")
    check("a path that normalizes back inside the bench is accepted",
          os.path.normpath(inside) == ".claude/plans/Drivers/experiments/keys/K-fields"
                                      "/draft_inputs.hashes.json" and not escapes(inside),
          "normalized to %r, escapes=%s" % (os.path.normpath(inside), escapes(inside)))
    check("an absolute path is refused", escapes("/etc/passwd"), "not refused")
    check("a path escaping the bench with ../ is refused",
          escapes("../outside.txt") and escapes("a/../../outside.txt"), "not refused")


def test_the_v3_epoch_contract_manifest_is_the_one_the_plan_pins():
    """The single-field epoch confusion, pinned in both directions: the
    constructed v3 view must carry the epoch manifest the historical plan pins,
    and that plan must still be the one pins_1636 requires. The 2026-08-25
    document is prior-state evidence, never the v3_1479 active file."""
    EPOCH = ("c80f5c7f90fe3902f55f6a5e9c0bfaaa93454b1e31c2368e0938be4325fb005d")
    PLAN = ("804a3b190042244fddcc9349b0442a55cafed8bf2225270d02f2411078c4ed51")
    f = (UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
                "/exp5_prompt_contract.manifest.v3.json")
    got = boundary.file_sha(f)
    check("the v3 view resolves the epoch contract manifest", got == EPOCH, got[:16])
    pins = json.load(io.open(P + "/pins_1636.json", encoding="utf-8"))["pins"]
    check("the exact v3 A5 plan is still the pinned one",
          pins["manifest"] == PLAN, pins["manifest"][:16])


before = digests()
test_the_placer_has_one_acceptance_route()
test_a_preserved_destination_makes_the_reconstruction_refuse()
test_the_placer_normalizes_and_refuses_escapes()
test_the_v3_epoch_contract_manifest_is_the_one_the_plan_pins()
after = digests()
moved = [k for k in before if before[k] != after[k]]
check("the live bench, runs, manifest and session store are byte-identical",
      not moved, "changed: %s" % moved)

print("\n%d checks, %d failed %s" % (ran[0], len(failures), failures))
sys.exit(1 if failures else 0)
