"""The administrative receipt-epoch seam (Codex SEQ 1586), recovery-only.

Every A4 run's receipt bound the package of its own era: its manifest_sha256 and its bound block, and
before the corrections the receipt carried no v1_evidence key. The current final owner derives every
other receipt field exactly as history did (allowed order, prompt hashes, transport, history pins), so
an era receipt is the owner's own expected receipt re-bound to the era's pinned manifest, bound and key
set (inputs/receipt_epochs/<kind>.json, derived from the durable captures by receipt_epochs_recipe.py).

`install` replaces the owner's receipt check with one that, for a receipt naming a pinned era's manifest,
compares the receipt to that era-bound expectation, requires the complete bytes on disk to equal the
pinned historical hash, and requires every recorded state to stand at its allowed position with its
launcher's bytes at its scriptPath; any other receipt goes to the owner untouched. `rebind` rewrites the
receipt the owner has just prepared into its era form. Nothing here decides meaning: run_evidence, the
parser, the retry, the composition, the signer and the lock stay the owner's.
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

EPOCHS = os.path.join(R, "inputs", "receipt_epochs")
ORIGINAL = None                                        # the owner's receipt_problems, kept by install()


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def kind_of(out_dir):
    """A run's census kind from its root directory name (the retry child names its parent's)."""
    root = run_root_of(out_dir)
    parts = root.split("-") if root else []
    return parts[2] if len(parts) > 3 and parts[:2] == ["kf", "a4"] else None


def run_root_of(out_dir):
    d = os.path.abspath(out_dir)
    if os.path.basename(d) == "retry":
        d = os.path.dirname(d)
    return os.path.basename(d)


def epoch(kind):
    """The pinned era fields of a run kind, or None when that run bound the current package."""
    p = os.path.join(EPOCHS, str(kind) + ".json")
    if kind is None or not os.path.isfile(p):
        return None
    b = io.open(p, "rb").read()
    if _sha(b) != FS.pins("receipt_epoch").get(kind + ".json"):
        raise SystemExit("REFUSED: epoch %s.json is not the pinned bytes" % kind)
    return json.loads(b.decode("utf-8"), object_pairs_hook=collections.OrderedDict)


def era_receipt(expected, ep):
    """The owner's expected receipt re-bound to the era: its manifest, its bound, its key set and order."""
    out = collections.OrderedDict((k, expected[k]) for k in ep["fields"] if k in expected)
    out["manifest_sha256"] = ep["manifest_sha256"]
    out["bound"] = ep["bound"]
    return out


def rebind(F, out_dir):
    """Rewrite the receipt the owner has just prepared into its era form. -> True when re-bound."""
    ep = epoch(kind_of(out_dir))
    if ep is None:
        return False
    path = os.path.join(out_dir, F.K.RECEIPT_NAME)
    receipt = json.loads(io.open(path, "rb").read().decode("utf-8"), object_pairs_hook=collections.OrderedDict)
    F.HR._atomic(path, json.dumps(era_receipt(receipt, ep), indent=1))
    return True


def install(F):
    """The owner's receipt check, seamed for the pinned eras; idempotent."""
    global ORIGINAL
    if ORIGINAL is None:
        ORIGINAL = F.receipt_problems

    def receipt_problems(out_dir, bound, receipt):
        ep = epoch(kind_of(out_dir))
        if ep is None or not isinstance(receipt, dict) or receipt.get("manifest_sha256") != ep["manifest_sha256"]:
            return ORIGINAL(out_dir, bound, receipt)
        want, bad = F._expected_for(out_dir, bound, receipt)
        if want is None:
            return bad
        want = era_receipt(want, ep)
        for field in F.RECEIPT_IMMUTABLE:
            if field in want and receipt.get(field) != want[field]:
                bad.append("receipt.%s is not the era-bound expected value" % field)
        if set(receipt) != set(want) | {"states"}:
            bad.append("the receipt carries unexpected fields")
        name = "retry receipt" if os.path.basename(os.path.abspath(out_dir)) == "retry" else "receipt"
        pinned = FS.pins(run_root_of(out_dir)).get(name)
        on_disk = os.path.join(out_dir, F.K.RECEIPT_NAME)
        got = _sha(io.open(on_disk, "rb").read()) if os.path.isfile(on_disk) else "absent"
        if got != pinned:
            bad.append("the era receipt bytes %s are not the pinned %s" % (got[:16], (pinned or "none")[:16]))
        allowed = list(receipt.get("allowed") or [])
        for i, state in enumerate(list(receipt.get("states") or [])):
            try:
                doc = F.K._load(state)
            except Exception as exc:                  # noqa: BLE001 - by design
                bad.append("state %d cannot be read (%s)" % (i, type(exc).__name__))
                continue
            rows = [r for r in (doc.get("workflowProgress") or []) if r.get("type") == "workflow_agent"]
            label = rows[0].get("label") if len(rows) == 1 else None
            if i >= len(allowed) or label != allowed[i]:
                bad.append("recorded state %d (%s) is not the saved state of %s" % (i, os.path.basename(str(state)), allowed[i] if i < len(allowed) else "no allowed label"))
            sp = doc.get("scriptPath")
            if not (isinstance(sp, str) and os.path.isfile(sp)) or io.open(sp, "rb").read() != str(doc.get("script") or "").encode("utf-8"):
                bad.append("state %s: the projected launcher at its scriptPath is not its embedded script" % os.path.basename(str(state)))
        return bad
    F.receipt_problems = receipt_problems
    return receipt_problems
