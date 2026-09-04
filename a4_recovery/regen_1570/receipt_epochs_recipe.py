"""The receipt epochs (Codex SEQ 1586): every A4 run's receipt bound the package that existed in its
era (manifest_sha256 and the bound block), and the pre-correction V1 receipt carried no v1_evidence key.
The exact era fields survive in durable Codex-rollout captures of the historical receipts and
finalizations (the probe blob store of regen_1537, each blob named by its own sha256). This recipe copies
only those eight captures into the candidate with their provenance rows, derives one small epoch file per
era run (manifest_sha256, bound, the receipt's key order), and reproduces every historical receipt and
finalization hash Codex named from the candidate alone: the epoch, the frozen census, the saved states
(their embedded launchers carry the prompt) and the pinned earlier evidence. The build reads only the
epoch files, never the blobs, the backups or a transcript.

    receipt_epochs_recipe.py copy      copy the captures, derive the epochs, verify every hash
    receipt_epochs_recipe.py verify    recompute every hash from the candidate inputs only
"""
import collections
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)
import foundation_sources as FS  # noqa: E402

STORE = "/home/faisal/.core827_backups/recovery_1531/regen_1537/probe"   # provenance only; the build never reads it
OUT = os.path.join(R, "inputs", "receipt_epochs")
BLOBDIR = os.path.join(OUT, "captures")
PROVENANCE = os.path.join(OUT, "PROVENANCE.tsv")
OD = collections.OrderedDict
#: capture (its own sha256 prefix) -> (what it prints, run kind). Each is one Codex rollout command's output.
CAPTURES = OD([
    ("b6289a14807c35ea", ("finalization", "final")),     # jq of the V1 finalization: the V1 era's manifest and bound
    ("0c75ac4dd1d201c3", ("bound", "corr")),             # jq .bound of the V2 receipt
    ("6a708779494d7ead", ("receipt", "decision")),       # jq of the prepared V3 receipt
    ("5e5dc8b98ffc1ef8", ("receipt", "v4corr")),         # a sha256sum line, then jq of the prepared V4 receipt
    ("9bd0f639572c2a9b", ("receipt", "v5corr")),         # jq of the prepared V5 receipt
    ("79865333c6962c87", ("receipt", "v6corr")),         # jq -S (keys sorted) of the prepared V6 receipt
    ("9d6fbf406652beac", ("receipt", "signer")),         # jq of the recorded signer receipt
    ("b531927e19521f06", ("finalization", "signer")),    # cat of the signer finalization, then the state
])
KINDS = ("final", "corr", "decision", "v4corr", "v5corr", "v6corr", "signer")
PHASE = {"final": "events", "corr": "corrections", "decision": "decision", "v4corr": "decision_correction",
         "v5corr": "decision_correction_v5", "v6corr": "decision_correction_v6", "signer": "signer"}
HISTORY = {"decision": ("v1", "v2"), "decision_correction": ("v1", "v2", "v3"), "decision_correction_v5": ("v1", "v2", "v3", "v4"),
           "decision_correction_v6": ("v1", "v2", "v3", "v4", "v5")}
V = {"v1": "final", "v2": "corr", "v3": "decision", "v4": "v4corr", "v5": "v5corr"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dumps(obj):
    return json.dumps(obj, indent=1).encode("utf-8")


def refuse(msg):
    raise SystemExit("REFUSED: " + msg)


def first_object(text):
    """The first JSON object in a capture, key order preserved."""
    return json.JSONDecoder(object_pairs_hook=OD).raw_decode(text, text.index("{"))[0]


def root(kind):
    roots = sorted({r[0] for r in FS.census() if r[0].startswith("kf-a4-" + kind + "-")})
    if len(roots) != 1:
        refuse("%d census run roots for %s" % (len(roots), kind))
    return roots[0]


def rows(kind, attempt):
    return [r for r in FS.census() if r[0] == root(kind) and r[1] == attempt]


def prompt_sha(wf):
    """The prompt a saved state ran: the string constant its own embedded launcher carries."""
    script = FS.candidate_bytes("state:" + wf).decode("utf-8")
    i = script.index("const PROMPT = ") + len("const PROMPT = ")
    return sha(json.JSONDecoder().raw_decode(script, i)[0].encode("utf-8"))


def state_path(wf):
    return os.path.join(FS.SESS, "workflows", wf + ".json")


def run_pins(kind):
    """A run's pinned receipt / finalization / raw tree, then its retry's, in the owner's key order."""
    p, out = FS.pins(root(kind)), OD()
    for rel, attempt in (("", "primary"), ("retry/", "retry")):
        if not rows(kind, attempt):
            continue
        out[rel + "receipt.json"] = p[rel.replace("/", " ") + "receipt"]
        out[rel + "finalization.json"] = p[rel.replace("/", " ") + "finalization"]
        out[rel + "raw_tree"] = OD([("files", 2 * len(rows(kind, attempt))), ("sha256", p[rel.replace("/", " ") + "raw tree"])])
    return out


def history(phase):
    if phase == "corrections":
        return run_pins("final")
    return OD((tag, run_pins(V[tag])) for tag in HISTORY.get(phase, ()))


def capture_text(name):
    return io.open(os.path.join(BLOBDIR, name), "rb").read().decode("utf-8")


def epoch_path(kind):
    return os.path.join(OUT, kind + ".json")


def derive_epochs():
    """One epoch per era run whose receipt bound an earlier package: manifest, bound, receipt key order."""
    fields = list(first_object(capture_text("6a708779494d7ead")).keys())      # the owner's receipt key order, from a receipt
    out = OD()
    fin1 = first_object(capture_text("b6289a14807c35ea"))
    out["final"] = OD([("manifest_sha256", fin1["manifest_sha256"]), ("bound", fin1["bound"]), ("fields", [f for f in fields if f != "v1_evidence"])])
    out["corr"] = OD([("manifest_sha256", FS.pins(root("corr"))["era manifest"]), ("bound", first_object(capture_text("0c75ac4dd1d201c3"))), ("fields", fields)])
    for name, (role, kind) in CAPTURES.items():
        if role == "receipt" and kind in ("decision", "v4corr", "v5corr"):
            obj = first_object(capture_text(name))
            out[kind] = OD([("manifest_sha256", obj["manifest_sha256"]), ("bound", obj["bound"]), ("fields", list(obj.keys()))])
    return out


def reconstruct():
    """Every historical receipt and finalization Codex SEQ 1586 named, from the candidate inputs only.
    -> OrderedDict((run root, name) -> (bytes, sha256))."""
    got = OD()
    signer = first_object(capture_text("9d6fbf406652beac"))
    transport = signer["transport"]
    for kind in KINDS:
        rt, phase = root(kind), PHASE[kind]
        for attempt, rel in (("primary", ""), ("retry", "retry ")):
            rs = rows(kind, attempt)
            if not rs:
                continue
            labels = [r[2] for r in rs]
            if os.path.isfile(epoch_path(kind)):
                ep = json.loads(io.open(epoch_path(kind), "rb").read().decode("utf-8"), object_pairs_hook=OD)
                manifest, bound, fields = ep["manifest_sha256"], ep["bound"], ep["fields"]
            else:                                          # the V6 and signer eras are the current package's
                manifest, bound, fields = signer["manifest_sha256"], signer["bound"], list(signer.keys())
            parent = None if attempt == "primary" else OD([("run_id", rt), ("finalization_sha256", FS.pins(rt)["finalization"])])
            full = OD([("run_id", rt if attempt == "primary" else "retry"), ("door", signer["door"]), ("phase", phase),
                       ("attempt", 1 if attempt == "primary" else 2), ("allowed", labels), ("parent", parent), ("transport", transport),
                       ("manifest_sha256", manifest), ("bound", bound), ("v1_evidence", history(phase)),
                       ("prompts", OD((r[2], prompt_sha(r[3])) for r in rs)), ("states", [state_path(r[3]) for r in rs])])
            rec = OD((k, full[k]) for k in fields)
            if attempt == "primary" and (kind in ("corr", "v6corr")):
                b = dumps(OD(rec, states=[]))
                got[(rt, "prepared receipt")] = (b, sha(b))
            b = dumps(rec)
            got[(rt, rel + "receipt")] = (b, sha(b))
    for name, (role, kind) in CAPTURES.items():
        if role == "finalization":
            b = dumps(first_object(capture_text(name)))
            got[(root(kind), "finalization")] = (b, sha(b))
    # the captured V6 prepared receipt was printed with every key sorted: restore the owner's orders from the reconstruction
    name = [n for n, (role, k) in CAPTURES.items() if k == "v6corr"][0]
    want = json.loads(got[(root("v6corr"), "prepared receipt")][0].decode("utf-8"), object_pairs_hook=OD)
    b = dumps(_reorder(first_object(capture_text(name)), want))
    got[(root("v6corr"), "captured prepared receipt")] = (b, sha(b))
    b = dumps(signer)
    got[(root("signer"), "captured receipt")] = (b, sha(b))
    return got


def _reorder(obj, like):
    """`obj` with every nested key order taken from `like` (same key sets); lists kept."""
    if isinstance(obj, dict) and isinstance(like, dict):
        if set(obj) != set(like):
            refuse("key sets differ: %s vs %s" % (sorted(obj), sorted(like)))
        return OD((k, _reorder(obj[k], like[k])) for k in like)
    return obj


def problems():
    """Every reconstructed hash against the pins; every capture against its own name; every epoch file against its pin."""
    bad = []
    for name in CAPTURES:
        p = os.path.join(BLOBDIR, name)
        if not os.path.isfile(p):
            bad.append("capture %s missing" % name); continue
        if not sha(io.open(p, "rb").read()).startswith(name):
            bad.append("capture %s is not its own sha256" % name)
    if bad:
        return bad
    want = derive_epochs()
    for kind, ep in want.items():
        p = epoch_path(kind)
        if not os.path.isfile(p) or io.open(p, "rb").read() != dumps(ep):
            bad.append("epoch %s.json is not the derivation from the captures" % kind)
        if sha(dumps(ep)) != FS.pins("receipt_epoch").get(kind + ".json"):
            bad.append("epoch %s.json is not the pinned bytes" % kind)
    if bad:
        return bad
    for (rt, name), (b, h) in reconstruct().items():
        pin = FS.pins(rt).get(name.replace("captured prepared ", "prepared ").replace("captured ", ""))
        if h != pin:
            bad.append("%s / %s reconstructs to %s (%d bytes), not the pinned %s" % (rt[:20], name, h[:16], len(b), (pin or "none")[:16]))
    return bad


def copy():
    os.makedirs(BLOBDIR, exist_ok=True)
    idx = [l.rstrip("\n").split("\t") for l in io.open(os.path.join(STORE, "index.tsv"), encoding="utf-8") if l.strip()]
    prov = ["capture\tsha256\tbytes\trollout_line\trollout_id\tcommand\n"]
    for name in CAPTURES:
        b = io.open(os.path.join(STORE, "blobs", name), "rb").read()
        if not sha(b).startswith(name):
            refuse("store capture %s is not its own sha256" % name)
        dst = os.path.join(BLOBDIR, name)
        if os.path.exists(dst) and io.open(dst, "rb").read() != b:
            refuse("capture %s exists with different bytes" % name)
        io.open(dst, "wb").write(b)
        row = [r for r in idx if len(r) == 8 and r[7] == name]
        if len(row) != 1:
            refuse("%d provenance rows for capture %s" % (len(row), name))
        prov.append("%s\t%s\t%d\t%s\t%s\t%s\n" % (name, sha(b), len(b), row[0][1], row[0][2], row[0][4]))
    io.open(PROVENANCE, "w", encoding="utf-8").write("".join(prov))
    for kind, ep in derive_epochs().items():
        io.open(epoch_path(kind), "wb").write(dumps(ep))
        print("epoch %-8s manifest %s bound %d keys fields %d  sha %s" % (kind, ep["manifest_sha256"][:16], len(ep["bound"]), len(ep["fields"]), sha(dumps(ep))[:16]))
    for (rt, name), (b, h) in reconstruct().items():
        pin = FS.pins(rt).get(name.replace("captured prepared ", "prepared ").replace("captured ", ""))
        print("%-36s %-28s %6d bytes %s %s" % (rt[:36], name, len(b), h[:16], "MATCH" if h == pin else "DIFF vs " + (pin or "none")[:16]))
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["copy"]:
        sys.exit(copy())
    if sys.argv[1:2] == ["verify"]:
        bad = problems()
        for b in bad:
            print("PROBLEM " + b)
        print("receipt epochs: %s" % ("every reconstruction holds" if not bad else "REFUSED (%d problems)" % len(bad)))
        sys.exit(1 if bad else 0)
    sys.exit("usage: receipt_epochs_recipe.py copy|verify")
