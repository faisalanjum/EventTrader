# -*- coding: utf-8 -*-
"""Drive both paired sides, then join them into the 14 old/new model cards."""
import collections, hashlib, io, json, os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U, OUT = A + "/unit_1821", "/tmp/a7_logs_1781"
FROZEN = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
          "targeted_1589/post_1500_exact_1626/budget_inputs_1720/out_g23/"
          "tmp__a7_reference_inventory.json")
CODEX = {"old_sha": "a3afa11c35e1022dff6ea3ff70de2d4397266c4fbe75fda9623560cac2e00572",
         "new_sha": "611690a4b5bf1dc28018f44aed901ce9c11e7d1e3193a670e1fad9aab68d66c3",
         "old_bytes": 216, "new_bytes": 213, "row": ["0000027904-26-000022", 2]}
SIDES = [("old", H + "/a7_reference_inventory.py", FROZEN),
         ("new", A + "/unit_1820/candidate/a7_reference_inventory.py", "DERIVE")]
for label, owner, inv in SIDES:
    r = subprocess.run([sys.executable, "-B", U + "/ledger/cards_one_side_1821.py",
                        owner, inv, label], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stderr.write(r.stderr[-1200:]); sys.exit(1)
old = json.load(io.open(OUT + "/CARDS_old.json", encoding="utf-8"))
new = json.load(io.open(OUT + "/CARDS_new.json", encoding="utf-8"))
o = {(r["source_id"], r["gold_idx"]): r for r in old["rows"]}
n = {(r["source_id"], r["gold_idx"]): r for r in new["rows"]}
rows = []
for k in sorted(o):
    rows.append(collections.OrderedDict([
        ("source_id", k[0]), ("gold_idx", k[1]),
        ("old_reference_name", o[k]["reference_name"]),
        ("new_reference_name", n[k]["reference_name"]),
        ("old_card_text", o[k]["card_text"]), ("new_card_text", n[k]["card_text"]),
        ("old_card_bytes", o[k]["card_bytes"]), ("new_card_bytes", n[k]["card_bytes"]),
        ("old_card_sha256", o[k]["card_sha256"]),
        ("new_card_sha256", n[k]["card_sha256"]),
        ("quote_unchanged", o[k]["quote_sha256"] == n[k]["quote_sha256"]),
        ("values_unchanged", o[k]["values"] == n[k]["values"])]))
hit = next(r for r in rows if [r["source_id"], r["gold_idx"]] == CODEX["row"])
checks = collections.OrderedDict([
    ("codex_old_sha256", hit["old_card_sha256"] == CODEX["old_sha"]),
    ("codex_new_sha256", hit["new_card_sha256"] == CODEX["new_sha"]),
    ("codex_old_bytes", hit["old_card_bytes"] == CODEX["old_bytes"]),
    ("codex_new_bytes", hit["new_card_bytes"] == CODEX["new_bytes"]),
    ("only_the_name_moved", all(r["quote_unchanged"] and r["values_unchanged"]
                                for r in rows)),
    ("frozen_document_untouched",
     hashlib.sha256(io.open(FROZEN, "rb").read()).hexdigest()
     == "ae81caf4936c43432fe27d5ac686dfa090539c615620ce029eaeb00b2f900106")])
io.open(OUT + "/MODEL_CARDS_1821.json", "w", encoding="utf-8").write(json.dumps(
    collections.OrderedDict([
        ("serializer", "a7_g23_build.reference_card then a7_g1_build._pretty"),
        ("old_side", {k: old[k] for k in ("owner_sha256", "overrides",
                                          "inventory_sha256")}),
        ("new_side", {k: new[k] for k in ("owner_sha256", "overrides",
                                          "inventory_sha256")}),
        ("rows", rows), ("reviewer_cross_check", checks)]), indent=1) + "\n")
for k, v in checks.items():
    print("  %-28s %s" % (k, v))
print("  %s g%s" % tuple(CODEX["row"]))
print("    old %d B %s  %r" % (hit["old_card_bytes"], hit["old_card_sha256"][:16],
                               hit["old_reference_name"]))
print("    new %d B %s  %r" % (hit["new_card_bytes"], hit["new_card_sha256"][:16],
                               hit["new_reference_name"]))
