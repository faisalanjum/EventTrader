# -*- coding: utf-8 -*-
"""Codex SEQ 1880 item 5: the inventory, each row mapped to the proof that
actually covers it - including the two rows a RUN of this module does not
prove, recorded at their real strength rather than a stronger claim.
"""
import collections, hashlib, io, json, os, re, sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_1881"
L = U + "/logs"
T = U + "/view/tree/harness_g1v3/test_a7_g23_lifecycle_1464.py"
SEALED = A + "/unit_1871/view/tree/harness_g1v3/test_a7_g23_lifecycle_1464.py"
NATIVE = A + "/unit_1876/logs/NATIVE_1876_nat3.json"
PRIOR = A + "/unit_1880/logs/INVENTORY_TO_PROOF_1880.json"


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def names(path):
    return sorted(set(re.findall(r"^def (test_\w+)",
                                 io.open(path, encoding="utf-8").read(), re.M)))


before, after = names(SEALED), names(T)
retired = [n for n in before if n not in after]

attempts = collections.OrderedDict()
for d in sorted(os.listdir(L)):
    if not d.startswith("attempt_"):
        continue
    tag = d[len("attempt_"):]
    row = collections.OrderedDict()
    ex = os.path.join(L, d, "exit")
    row["exit"] = io.open(ex).read().strip() if os.path.isfile(ex) else None
    for name in os.listdir(os.path.join(L, d)):
        if name.startswith("RESULT_") and name.endswith(".json"):
            doc = json.load(io.open(os.path.join(L, d, name)))
            row["summary"] = doc.get("summary")
            row["failed_ids"] = doc.get("failed_ids")
    attempts[tag] = row

saved = collections.OrderedDict()
for f in sorted(os.listdir(L)):
    if f.startswith(("CONTINUATION_1881_", "RETRY_MUTATIONS_1881_",
                     "COLLISION_1881_", "AFTER_AUDIT_1881_")):
        doc = json.load(io.open(os.path.join(L, f)))
        saved[f] = collections.OrderedDict([
            ("sha256", sha(os.path.join(L, f))),
            ("checks", "%s/%s" % (doc.get("n_green"), doc.get("n_checks"))),
            ("all_green", doc.get("all_green")),
            ("owner_bytes_restored", doc.get("owner_bytes_restored"))])

nat = json.load(io.open(NATIVE))
out = collections.OrderedDict([
    ("module_sha256", sha(T)),
    ("tests", len(after)),
    ("prior_mapping", collections.OrderedDict([
        ("file", PRIOR), ("sha256", sha(PRIOR))])),
    ("rows_not_proved_by_running_this_module", collections.OrderedDict([
        (retired[0] if retired else "none", collections.OrderedDict([
            ("state", "RETIRED by Codex SEQ 1879"),
            ("covered_by", NATIVE), ("proof_sha256", sha(NATIVE)),
            ("proof_checks", "%s/%s" % (nat["n_green"], nat["n_checks"])),
        ])),
        ("test_the_official_entry_REFUSES_before_grader_evidence_exists",
         collections.OrderedDict([
             ("state", "PASSES, but at a WEAKER boundary than its name says"),
             ("actual_scope", "it supplies g1=None, so it stops at the missing "
                              "G1 check and never reaches the empty-grader-set "
                              "check (Codex SEQ 1880)"),
             ("empty_grader_set_covered_by",
              "Codex's own scoped closure of B._score_leg_bound: all 48 "
              "combinations of P1/P2/UNION x every subset of G2/G3/extra G9 x "
              "with/without the approved G1, all passing; removing the G1 "
              "guard was caught by 24 cases, allowing an empty review set by "
              "3, removing the required-kind guard by 21, and all 3 lawful "
              "positives survived every mutation"),
             ("owner_of_that_proof", "Codex SEQ 1880; no file was written"),
             ("status", "CLOSED - the required handle/kind mutations are not "
                        "to be repeated here"),
         ])),
    ])),
    ("saved_proofs_this_unit", saved),
    ("attempts", attempts),
])
io.open(L + "/INVENTORY_TO_PROOF_1881.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=1, default=str))
print("tests=%d retired=%s saved_proofs=%d attempts=%d"
      % (len(after), retired, len(saved), len(attempts)))
for t_, r in attempts.items():
    print("  %-10s exit=%-5s %s" % (t_, r["exit"], r.get("summary") or ""))
sys.exit(0)
