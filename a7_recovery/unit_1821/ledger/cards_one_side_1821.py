# -*- coding: utf-8 -*-
"""Emit the real model cards for ONE paired (owner, inventory) side.

argv: <owner path> <inventory path|DERIVE> <label>
Owner and document must match: the validation owner refuses a corrected owner
served a stale document, which is correct behaviour, so each side is rendered
in its own process with its own pair.
"""
import collections, hashlib, importlib.util, io, json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
CAND, RUN, OUT = (S + "/g1_precall_cand_1525", S + "/g1_precall_run_1525",
                  "/tmp/a7_logs_1781")
PIN = {"root": "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0",
       "run_digest": "ec50dc6e9af2e6efc5dd5e4114c0d6dc0f09b77070a9760aece3839f3bffab71",
       "run_files": 471}
owner, inv_path, label = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
spec = importlib.util.spec_from_file_location("a7_reference_inventory", owner)
REF = importlib.util.module_from_spec(spec)
sys.modules["a7_reference_inventory"] = REF
spec.loader.exec_module(REF)
assert REF.__file__ == owner, REF.__file__
import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as C                                    # noqa: E402
import a7_g23_build as B                                         # noqa: E402
assert sys.modules["a7_reference_inventory"].__file__ == owner
usha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

exp = json.load(io.open(A + "/unit_1820/candidate/EXPECTED_CARDS_14.json",
                        encoding="utf-8"))
wanted = [(r["source_id"], r["gold_idx"]) for r in exp["rows"]]
_r, doc, _l, _p = C.evidence(CAND, RUN, PIN["root"], PIN["run_digest"],
                             PIN["run_files"])
run, (key, _i) = doc["producer_identity"], G.live_key()
if inv_path == "DERIVE":
    inv_path = OUT + "/candidate_reference_inventory.json"
    if os.path.exists(inv_path):
        os.remove(inv_path)
    REF.write(REF.expected_document(run), inv_path)
REF.INVENTORY_PATH = inv_path
B._INVENTORY.clear()
served = REF.validate(inv_path, run)
rows = []
for sid, gi in wanted:
    card = B.reference_card(key[sid][gi], sid, gi, run)
    text = G._pretty(card)
    rows.append(collections.OrderedDict([
        ("source_id", sid), ("gold_idx", gi), ("card_text", text),
        ("card_bytes", len(text.encode("utf-8"))), ("card_sha256", usha(text)),
        ("reference_name", card["reference_name"]),
        ("quote_sha256", G._sha(card["quote"])),
        ("values", list(card["values"]))]))
io.open("%s/CARDS_%s.json" % (OUT, label), "w", encoding="utf-8").write(
    json.dumps(collections.OrderedDict([
        ("label", label), ("owner", owner), ("owner_sha256", fsha(owner)),
        ("overrides", len(REF.SPAN_OVERRIDES)),
        ("inventory", inv_path), ("inventory_sha256", fsha(inv_path)),
        ("inventory_rows_validated", len(served)), ("rows", rows)]), indent=1) + "\n")
print("  %-10s owner %s (%d overrides)  inventory %s  cards %d"
      % (label, fsha(owner)[:16], len(REF.SPAN_OVERRIDES),
         fsha(inv_path)[:16], len(rows)))
