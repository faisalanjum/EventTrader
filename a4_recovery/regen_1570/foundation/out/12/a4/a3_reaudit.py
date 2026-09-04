"""THE A3 protected re-audit, and the measured list of live bytes it depends on.

Codex SEQ 1358 item 1: before any pinned live owner changes, A3 must still be
exactly reconstructible, and any dependence on mutable live bytes must be
REPORTED, not patched around.

Nothing here is hand-listed. The dependency set is DERIVED three ways:
  * the modules the verification actually imported (sys.modules, filtered to the
    experiments tree) - so an import added tomorrow appears by itself;
  * the plan's own declared protected pins;
  * the plan's own declared per-event input paths.
Run it before a change and after it: the printed digest must be identical.

    a3_reaudit.py            -> print the re-audit and the dependency digest
    a3_reaudit.py <out.json> -> also write the frozen digest for comparison
"""
import hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
     "/scratchpad")
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
sys.path.insert(0, X + "/harness")
T = io.open(S + "/a3_serial_dir.txt", encoding="utf-8").read().strip()

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    import raw_transport as RT
    import build_launch_manifest as blm

    fin = json.load(io.open(T + "/finalization.json", encoding="utf-8"))
    child = json.load(io.open(T + "/retry/finalization.json", encoding="utf-8"))
    plan = RT.a1_plan()

    problems = RT.a1_primary_evidence_problems(fin, plan, T)
    print("A3 PRIMARY RE-AUDIT: %s"
          % ("CLEAN" if not problems else "REFUSED %s" % problems[:3]))
    print("  ledger      %s" % json.dumps(fin["ledger"], sort_keys=True))
    print("  child ledger %s" % json.dumps(child["ledger"], sort_keys=True))
    print("  retry keys recomputed from the finalization: %s"
          % [list(k) for k in RT.a1_primary_retry_keys(fin, plan)])

    # ---- the live bytes this verification actually touched --------------
    dep = {}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if f and os.path.abspath(f).startswith(os.path.abspath(X)):
            dep[os.path.relpath(f, X)] = sha(f)
    dep[os.path.relpath(RT.a1_plan_path(), X)] = sha(RT.a1_plan_path())
    for name, path in blm._protected_pins().items():
        dep[os.path.relpath(path, X)] = sha(path)
    for e in plan.get("events", []):
        p = os.path.join(blm._REPO, e["input_path"])
        dep[os.path.relpath(p, X)] = sha(p)

    digest = hashlib.sha256(
        json.dumps(dep, sort_keys=True).encode("utf-8")).hexdigest()
    print("\nLIVE BYTES A3 VERIFICATION DEPENDS ON: %d files" % len(dep))
    for k in sorted(dep):
        if not k.startswith("keys/K-fields/draft_inputs/"):
            print("  %s  %s" % (dep[k][:12], k))
    ins = [k for k in dep if k.startswith("keys/K-fields/draft_inputs/")]
    print("  ... plus %d frozen draft_inputs/*.json named by the plan" % len(ins))
    print("DEPENDENCY DIGEST %s" % digest)

    if len(sys.argv) > 1:
        io.open(sys.argv[1], "w", encoding="utf-8").write(
            json.dumps({"digest": digest, "files": dep,
                        "primary_problems": problems}, indent=1, sort_keys=True))
        print("wrote %s" % sys.argv[1])
    raise SystemExit(0 if not problems else 1)


if __name__ == "__main__":
    main()
