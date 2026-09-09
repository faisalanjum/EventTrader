"""A5 — the still-unrun EXP-5 reader kit, versioned. Codex SEQ 1400.

WHAT THIS OWNER ADDS, and nothing else:
  * the A5 ACTIVE ARM SCHEDULE  - P1 sonnet_run1, P2 sonnet_run2, both exact
    Sonnet 5 / high / independent. P3-P5, Qwen, GPT, Opus, Haiku and every
    fallback or escalation are ABSENT from the active plan; the frozen 156-call
    manifest keeps them as historical evidence and is never rewritten.
  * the A4 FINAL LOCK BINDING  - the signed final-key lock (Codex SEQ 1512/1513),
                                 its receipt and the key identity it binds: path
                                 plus sha256 each, refused if any moves.
  * the A5 MANIFEST            - counts DERIVED from live bytes, never typed.

WHAT IT REUSES AND NEVER RECREATES. One owner per rule:
  packets + prompts   build_launch_manifest._one_item_packets  (the proved
                      production shape: stable instructions, readable menu,
                      complete ordered event, exactly one located item last)
  prompt text         build_exp5_contract.build_prompt
  reply normalizer    a1_reader.normalize / .validate / .read_one
  occurrence locator  driver.core verify_occurrence, via a1_reader
  exact-Decimal parse raw_transport.parse_exact and its fence envelope
  inventory + events  build_launch_manifest.INVENTORY / _events
  capacity            build_launch_manifest.measured_capacity
There is no second schema, parser, source locator, retry engine, scorer, pass
bar or production rule here, and no old-shape adapter or derived reply copy.
"""
import collections
import hashlib
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_launch_manifest as BLM
import build_exp5_contract as BEC
import build_kfields_key_targeted as _T
import a1_reader
import raw_transport

#: The SIGNED A4 final key this kit reads against (Codex SEQ 1513 item 2): the
#: final lock, its receipt and the key identity it binds, all resolved from
#: `_HERE`. The earlier V6 lock (c1d4deb2...) is superseded history.
#: WHERE AN APPROVED KEY'S EXPECTED IDENTITY COMES FROM. These two logical
#: paths are read-only rows of this run's own binding, written and verified by
#: the boundary BEFORE any consumer starts. The expectation is therefore frozen
#: independently of whatever candidate directory is offered later - which is
#: the whole point, and is the same mechanism build_kfields_key already uses
#: for the approved source lock.
#:
#: WHY THIS REPLACED AN EARLIER ATTEMPT. That attempt computed the expected
#: hashes from the very files it was approving, so "the served bytes match what
#: we just read from the served bytes" was a tautology: a coherently changed
#: lock with its receipt re-bound in the same directory was ACCEPTED, and only
#: an incoherent pair refused. Reading a directory proves where a file is, not
#: that anyone approved it (Codex SEQ 1934/1935).
APPROVED_LOCK_PIN = "/tmp/a7_approved_key/a4_final_key_lock.json"
APPROVED_RECEIPT_PIN = "/tmp/a7_approved_key/a4_final_key_lock_receipt.json"


def _binding_pin(logical):
    """The sha this run's own frozen binding pins for `logical`, or None."""
    path = os.environ.get("A7_RUN_BINDING")
    if not path or not os.path.isfile(path):
        return None
    want = None
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            row = line.rstrip("\n").split("\t")
            if len(row) == 4 and row[0] == logical and row[3] == "ro":
                want = row[2]
    return want


APPROVED_KEY_DIR = os.environ.get("A7_APPROVED_KEY_DIR") or ""
if APPROVED_KEY_DIR:
    A4_LOCK_DIR = os.path.normpath(APPROVED_KEY_DIR)
    A4_LOCK_PATH = os.path.join(A4_LOCK_DIR, "a4_final_key_lock.json")
    A4_LOCK_SHA = _binding_pin(APPROVED_LOCK_PIN)
    A4_LOCK_RECEIPT_SHA = _binding_pin(APPROVED_RECEIPT_PIN)
    # AN ABSENT APPROVAL REFUSES. It is never replaced by a hash taken from
    # the offered file, and it never falls back to the historical selection:
    # a run that asks for an approved key and has no approval for it is a run
    # that cannot proceed.
    if not A4_LOCK_SHA or not A4_LOCK_RECEIPT_SHA:
        raise ValueError(
            "an approved key was named at %s, but this run's binding pins no "
            "read-only approval for it at %s and %s"
            % (A4_LOCK_DIR, APPROVED_LOCK_PIN, APPROVED_RECEIPT_PIN))
else:
    A4_LOCK_DIR = os.path.normpath(os.path.join(
        _HERE, os.pardir, "runs", "kf-a4-final-20260829T1226Z"))
    A4_LOCK_PATH = os.path.join(A4_LOCK_DIR, "a4_final_key_lock.json")
    A4_LOCK_SHA = "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"
    A4_LOCK_RECEIPT_SHA = "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3"


def a4_lock_receipt_path():
    return os.path.join(os.path.dirname(A4_LOCK_PATH), "a4_final_key_lock_receipt.json")


#: The CORRECTED inventory the signed A4 key was materialized over (Codex SEQ
#: 1514). The original one_item_benchmark_inventory.json stays the historical
#: A1 input; A5 selects this only after its live bytes match the A4 lock's
#: provenance corrected_inventory_sha256. Resolved from the shared owner.
CORRECTED_INVENTORY_PATH = _T.CORRECTED_INVENTORY


def corrected_inventory():
    """The corrected inventory path, refused unless its live bytes are exactly
    the corrected_inventory_sha256 the signed A4 lock's provenance binds. The
    original inventory is never selected here; a missing or drifted corrected
    file refuses before any packet is built."""
    if APPROVED_KEY_DIR:
        bad = approved_inventory_problems()
        if bad:
            raise ValueError(bad[0])
        return approved_inventory()[1]
    lock = a4_lock()
    want = _bound_artifact(lock, "provenance")["provenance"]["corrected_inventory_sha256"]
    if not os.path.isfile(CORRECTED_INVENTORY_PATH):
        raise ValueError("the corrected inventory is missing at %s" % CORRECTED_INVENTORY_PATH)
    got = hashlib.sha256(io.open(CORRECTED_INVENTORY_PATH, "rb").read()).hexdigest()
    if got != want:
        raise ValueError("the corrected inventory %s is not the one the A4 key "
                         "was built over (%s)" % (got, want))
    return CORRECTED_INVENTORY_PATH

#: The ONLY active arm IDs. The full rows are DERIVED from the frozen kit by
#: active_arms(); copying tier/effort/role here let the manifest claim invented
#: values while the launch bytes stayed Sonnet/high (Codex SEQ 1403 item 4).
ACTIVE_ARM_IDS = ("P1", "P2")


def active_arms():
    """The complete active rows, read ONCE from the frozen kit."""
    kept = [a for a in frozen_kit()["arms"] if a["arm"] in set(ACTIVE_ARM_IDS)]
    if len(kept) != len(ACTIVE_ARM_IDS):
        raise ValueError("the frozen kit does not carry every active arm id")
    return [collections.OrderedDict(
        [("arm", a["arm"]), ("role", a["role"]), ("tier", a["tier"]),
         ("effort", a["effort"]), ("active", True)]) for a in kept]

#: The frozen, still-unrun 156-call kit. Historical evidence; never rewritten.
# THE CANONICAL FILE IN THIS TREE, resolved from `_HERE`. This pointed at a
# copy in a session scratchpad outside the tree - the same bytes, but reachable
# only from one machine and one session. `FROZEN_KIT_SHA` below is unchanged
# and still refuses anything that is not the original commit's bytes.
FROZEN_KIT_PATH = os.path.join(_HERE, "launch_exp5_readers.manifest.json")
FROZEN_KIT_SHA = "bf9323bc3bdc75a45a7381ac97cf0d4e1403f8754f5ac419abe1136f589c3070"
FROZEN_KIT_COMMIT = "0dd71956e942c889c70fede4e547f4737a39cff0"


def frozen_kit():
    """The original 156-call kit, refused unless its bytes are the pinned ones.

    Read from the extracted frozen bytes, NOT from the harness copy: that copy
    has since been rebuilt and its prompt hashes differ, so deriving from it
    would silently describe a drifted kit as the historical one.
    """
    if not os.path.isfile(FROZEN_KIT_PATH):
        raise ValueError("the frozen EXP-5 kit is missing at %s"
                         % FROZEN_KIT_PATH)
    raw = io.open(FROZEN_KIT_PATH, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != FROZEN_KIT_SHA:
        raise ValueError("the frozen EXP-5 kit moved: %s is not the pinned %s"
                         % (got, FROZEN_KIT_SHA))
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("made_calls") != 0:
        raise ValueError("the frozen kit no longer reads made_calls=0")
    if (doc.get("kfields_lock") or {}).get("sha256") is not None:
        raise ValueError("the frozen kit's reviewed-key hash is not null")
    return doc


def arm_of_lane():
    """THE one arm selection, DERIVED: retained frozen rows -> transport lanes.

    Codex SEQ 1402 item 1. The transport suffix stays L1/L2 because the frozen
    launcher owner emits it; this is the single explicit mapping that makes the
    retained P-rows drive every call, receipt and scorer identity, rather than
    a decorative second schedule beside them.
    """
    kept = active_arms()
    if len(kept) != BLM.LANES_PER_PACKET:
        raise ValueError("the frozen kit retains %d active arms but the "
                         "transport has %d lanes"
                         % (len(kept), BLM.LANES_PER_PACKET))
    return collections.OrderedDict(
        ("L%d" % (n + 1), collections.OrderedDict(
            [("arm", a["arm"]), ("role", a["role"]), ("tier", a["tier"]),
             ("effort", a["effort"])]))
        for n, a in enumerate(kept))


def arm_for_call(lane_id):
    """The P-row that owns one emitted call. Refuses an unmapped lane."""
    suffix = lane_id.rsplit("/", 1)[-1]
    m = arm_of_lane()
    if suffix not in m:
        raise ValueError("call lane %r maps to no active arm" % lane_id)
    return m[suffix]


def retired_arms():
    """DERIVED, never typed: everything the frozen kit planned that this
    active plan does not run."""
    doc = frozen_kit()
    active = set(ACTIVE_ARM_IDS)
    out = ["%s %s" % (a["arm"], a["role"]) for a in doc["arms"]
           if a["arm"] not in active]
    out += [k for k in sorted(doc)
            if k.endswith("_fallback") or k.endswith("_contingency")]
    return out

#: The role that selects the canonical one-item/four-field path.
ONE_ITEM_ROLE_NAME = "drafter"
#: THE ACTIVE PRODUCER CONTRACT ERA for the CURRENT A5 plan - 196 packets over
#: P1/P2. Read from the one owner rather than restated, so the packets, the
#: bundle and the pins can never name different versions. The retired 156-call
#: five-arm freeze keeps its own v1 bytes as history and is never re-versioned.
def contract_era():
    return BLM.PRODUCER_CONTRACT_SUFFIX

#: The A5 launcher name prefix. The plan carries it, so the shared
#: receipt/contract/audit path resolves it without being told.
LAUNCHER_PREFIX = "exp5_a5_"

#: The reply-validation route A5 runs on. Read from its owner so a
#: rename there cannot leave this plan naming a route that is gone.
RT_DOOR = raw_transport.A1_DOOR

MANIFEST_NAME = "a5_exp5_reader.manifest.json"

#: The A2 runtime freeze every lane must carry. Codex SEQ 1401 item 2 pins it.
A2_FREEZE_NAME = "a2_runtime_freeze.json"
A2_FREEZE_SHA = "c534022d391e409f48ae65a0ded6bbf7eb428d4a92a00407646cad77f8ef794a"
RUNTIME_MODEL_ID = "claude-sonnet-5"


def a2_freeze():
    """The pinned A2 runtime freeze, refused unless its bytes are exact."""
    path = os.path.join(_HERE, A2_FREEZE_NAME)
    if not os.path.isfile(path):
        raise ValueError("the A2 runtime freeze is missing at %s" % path)
    raw = io.open(path, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != A2_FREEZE_SHA:
        raise ValueError("the A2 runtime freeze moved: %s is not the pinned %s"
                         % (got, A2_FREEZE_SHA))
    return json.loads(raw.decode("utf-8"))


def bundle():
    """The REAL launcher bytes, ordered calls and per-event menu back-map.

    Derived by the existing owner, which reads the frozen inventory outward and
    never the plan's own totals. Its default role is the canonical one-item
    path, so these are the same four-field prompts `packets()` returns.
    """
    a2_freeze()                                  # refuse on any freeze drift
    d = BLM.derive_expected(RUNTIME_MODEL_ID, contract_suffix=contract_era(),
                            inventory=corrected_inventory())
    events = d["events"]
    backmap = collections.OrderedDict(
        (e["source_id"], e.get("menu_display_to_original") or {})
        for e in events)
    return d, backmap


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pinned_file(path, sha, what):
    if not os.path.isfile(path):
        raise ValueError("the %s is missing at %s" % (what, path))
    raw = io.open(path, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != sha:
        raise ValueError("the %s moved: %s is not the pinned %s" % (what, got, sha))
    return json.loads(raw.decode("utf-8"))


def a4_lock():
    """The signed A4 final lock, refused unless its bytes and its receipt's are
    exactly the pinned ones and the receipt binds this lock."""
    doc = _pinned_file(A4_LOCK_PATH, A4_LOCK_SHA, "A4 final lock")
    if doc.get("state") != "LOCKED" or doc["signer"]["signed"] is not True \
            or doc["signer"]["blocked"] != []:
        raise ValueError("the A4 final lock is not a signed LOCKED document")
    rec = _pinned_file(a4_lock_receipt_path(), A4_LOCK_RECEIPT_SHA, "A4 final lock receipt")
    if rec.get("lock_sha256") != A4_LOCK_SHA or rec.get("every_bound_value_refuses_when_mutated") is not True:
        raise ValueError("the A4 final lock receipt does not bind this lock")
    return doc


def _bound_artifact(lock, name):
    """One artifact the lock binds by hash, read beside it and refused on drift."""
    return _pinned_file(os.path.join(os.path.dirname(A4_LOCK_PATH), name + ".json"),
                        lock["artifacts"][name], "A4 lock-bound " + name)


def locked_sources(lock=None):
    """The 36 ordered event source ids the locked key seals, from the key
    identity the lock binds (the ordered exact raw shards)."""
    lock = lock or a4_lock()
    return [s["source_id"] for s in _bound_artifact(lock, "key_identity")["key_shards"]]


def approved_inventory():
    """The inventory the approved key was materialized over, IDENTIFIED.

    Each hop is a hash the previous hop binds, so this names one exact file
    rather than describing a shape:

        the approved lock
          -> artifacts.key_identity
          -> key_identity.bindings.final_package (path + sha256)
          -> that manifest's bound.inventory

    -> (want_sha, served_path). Nothing is re-signed and no new key field is
    added; every value already exists in the chain the lock binds.
    """
    import build_kfields_key as K
    lock = a4_lock()
    ident = _bound_artifact(lock, "key_identity")
    fp = ident["bindings"]["final_package"]
    manifest = _pinned_file(fp["path"], fp["sha256"],
                            "final package manifest the key identity binds")
    want = manifest["bound"]["inventory"]
    served = os.path.join(os.path.dirname(K.APPROVED_SOURCE_LOCK),
                          "final_inventory.json")
    return want, served


def approved_inventory_problems():
    """The served inventory against the identity the approved key binds.

    A ROW COUNT CANNOT DO THIS JOB. Comparing the key's rows_accounted with
    the number of records in whatever inventory is served is passed equally
    well by a different inventory of the same size, or by the same one
    reordered. Identity is the hash, and the chain above already carries it
    (Codex SEQ 1935).
    """
    try:
        want, served = approved_inventory()
    except BaseException as exc:                      # noqa: BLE001 - by design
        return ["the approved key's inventory binding cannot be followed: %s"
                % str(exc)[:130]]
    if not os.path.isfile(served):
        return ["the approved inventory is missing at %s" % served]
    live = hashlib.sha256(io.open(served, "rb").read()).hexdigest()
    if live != want:
        return ["the served inventory %s is not the one the approved key "
                "binds (%s)" % (live, want)]
    return []


def inventory_problems(lock=None):
    """A5 serves the CORRECTED inventory the signed key was materialized over;
    the A4 lock's provenance pins its sha, and the live corrected file must BE
    that one. A reordered or original inventory silently renders different
    packets while the lock still reads LOCKED (Codex SEQ 1402 item 3, 1514)."""
    if APPROVED_KEY_DIR:
        return approved_inventory_problems()
    lock = lock or a4_lock()
    try:
        pinned = _bound_artifact(lock, "provenance")["provenance"]["corrected_inventory_sha256"]
    except ValueError as exc:
        return [str(exc)]
    if not os.path.isfile(CORRECTED_INVENTORY_PATH):
        return ["the corrected inventory is missing at %s" % CORRECTED_INVENTORY_PATH]
    live = hashlib.sha256(io.open(CORRECTED_INVENTORY_PATH, "rb").read()).hexdigest()
    if live != pinned:
        return ["the live corrected inventory %s is not the one the A4 lock "
                "binds (%s)" % (live, pinned)]
    return []


def packets():
    """The final ordered item/control packets, from the ONE packet owner."""
    bad = inventory_problems()
    if bad:
        raise ValueError(bad[0])
    events = BLM._events()
    order = locked_sources()
    seen = [e["source_id"] for e in events]
    if sorted(seen) != sorted(order):
        raise ValueError("the frozen events and the locked key disagree: "
                         "%d vs %d" % (len(seen), len(order)))
    if seen != order:
        raise ValueError("the frozen events are not in the locked key's order")
    # THE CANONICAL ONE-ITEM PATH, reused not restated. build_exp5_contract
    # gates the approved one-item/four-field amendment on role == "drafter";
    # role_rules calls the other role "the disabled producer" and leaves its
    # rules un-amended. Passing "producer" rendered the OLD dense three-field
    # contract with a model-emitted source locator while the manifest claimed
    # four fields (Codex SEQ 1401). This is that one-word correction.
    return BLM._one_item_packets(events, role=ONE_ITEM_ROLE_NAME,
                                 contract_suffix=contract_era(),
                                 inventory=corrected_inventory())


def plan():
    """The A5 manifest. Every count is DERIVED here, never typed."""
    lock = a4_lock()
    pks, prompts = packets()
    _bundle = bundle()
    n_packets = len(pks)
    n_calls = n_packets * len(ACTIVE_ARM_IDS)
    cap = BLM.measured_capacity(pks, prompts)
    return collections.OrderedDict([
        ("plan", "A5 EXP-5 one-item reader kit"),
        # the door names the REPLY-VALIDATION route, not the experiment
        ("door", RT_DOOR),
        # THE ERA THIS PLAN IS FOR, recorded once beside the pins it explains
        ("contract_suffix", contract_era()),
        # the protected pins come from their ONE owner, derived from the live
        # files at build time; the finalizer proves them again after the calls
        ("pins", collections.OrderedDict(
            (k, BLM._sha(v))
            for k, v in sorted(BLM._protected_pins(contract_era()).items()))),
        ("frozen_kit", collections.OrderedDict([
            ("path", FROZEN_KIT_PATH), ("sha256", FROZEN_KIT_SHA),
            ("commit", FROZEN_KIT_COMMIT), ("made_calls", 0),
            ("reviewed_key_sha256", None)])),
        ("a4_lock", collections.OrderedDict([
            ("path", A4_LOCK_PATH), ("sha256", A4_LOCK_SHA),
            ("receipt_path", a4_lock_receipt_path()), ("receipt_sha256", A4_LOCK_RECEIPT_SHA),
            ("schema", lock["schema"]), ("state", lock["state"]),
            ("signed", lock["signer"]["signed"]),
            ("key_identity_sha256", lock["artifacts"]["key_identity"]),
            ("events", len(locked_sources(lock)))])),
        ("n_events", len(locked_sources(lock))),
        ("n_packets", n_packets),
        ("arms", [dict(a) for a in active_arms()]),
        ("planned_producer_calls", n_calls),
        ("retired_from_active_plan", retired_arms()),
        ("made_calls", 0),
        ("reply_shape", list(a1_reader.REPLY_KEYS)),
        ("prompt_role", ONE_ITEM_ROLE_NAME),
        ("owners", collections.OrderedDict([
            ("packets", "build_launch_manifest._one_item_packets"),
            ("prompt", "build_exp5_contract.build_prompt"),
            ("normalizer", "a1_reader.normalize"),
            ("validator", "a1_reader.validate"),
            ("raw_parser", "raw_transport.parse_exact"),
            ("reader_owner_sha256", a1_reader.owner_sha256()),
            ("kit_owner_sha256", _sha_text(
                io.open(os.path.join(_HERE, "build_a5_exp5_kit.py"),
                        encoding="utf-8").read()))])),
        ("a2_runtime_freeze", collections.OrderedDict([
            ("path", A2_FREEZE_NAME), ("sha256", A2_FREEZE_SHA),
            ("runtime_model_id", RUNTIME_MODEL_ID),
            ("effort", BLM.PINNED_EFFORT),
            ("agentType", BLM.PINNED_AGENT_TYPE),
            ("disallowedTools", list(BLM.A1_DISALLOWED)),
            (BLM.OUTPUT_TOKENS_VAR, BLM.MAX_OUTPUT_TOKENS_SETTING),
            ("transport", "Claude Code Workflow agent(), subscription")])),
        ("capacity", cap),
        ("prompt_sha256", collections.OrderedDict(
            (k, _sha_text(v)) for k, v in sorted(prompts.items()))),
        ("launcher_sha256", collections.OrderedDict(
            (k, _sha_text(v)) for k, v in sorted(_bundle[0]["launchers"].items()))),
        ("ordered_calls", [list(c) for c in _bundle[0]["calls"]]),
        ("menu_backmap_sha256", _sha_text(
            json.dumps(_bundle[1], indent=1, sort_keys=True))),
        ("menu_backmap_sizes", collections.OrderedDict(
            (k, len(v)) for k, v in sorted(_bundle[1].items()))),
        ("inventory_path", corrected_inventory()),
        ("inventory_sha256", hashlib.sha256(
            io.open(corrected_inventory(), "rb").read()).hexdigest()),
        ("bound_inputs", collections.OrderedDict([
            ("inventory_sha256", hashlib.sha256(
                io.open(corrected_inventory(), "rb").read()).hexdigest()),
            ("event_source_sha256", collections.OrderedDict(
                (e["source_id"], hashlib.sha256(io.open(
                    os.path.join(BLM._REPO, e["input_path"]), "rb").read()
                ).hexdigest()) for e in sorted(_bundle[0]["events"],
                                               key=lambda x: x["source_id"]))),
            ("prompt_owner_sha256", _sha_text(io.open(
                os.path.join(_HERE, "build_exp5_contract.py"),
                encoding="utf-8").read())),
            ("packet_owner_sha256", _sha_text(io.open(
                os.path.join(_HERE, "build_launch_manifest.py"),
                encoding="utf-8").read())),
            ("raw_parser_sha256", _sha_text(io.open(
                os.path.join(_HERE, "raw_transport.py"),
                encoding="utf-8").read())),
            ("scorer_sha256", _sha_text(io.open(
                os.path.join(_HERE, "scorers", "score_exp5.py"),
                encoding="utf-8").read())),
            ("matcher_sha256", _sha_text(io.open(
                os.path.join(BLM._REPO, "driver", "core", "fact_match.py"),
                encoding="utf-8").read()))])),
        ("arm_of_lane", arm_of_lane()),
    ])


BUNDLE_NAME = "a5_launcher.bundle.json"
LAUNCHER_DIRNAME = "launchers_a5"


def K_load(path):
    """Read one JSON artifact."""
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def a5_bundle_path(run_dir):
    """Where THIS run persists its own launcher bundle."""
    return os.path.join(run_dir, "plan", BUNDLE_NAME)


def persist_launchers(run_dir):
    """Codex SEQ 1405 A: the exact UNARMED A5 launcher bytes and their bundle
    rows, written under <run>/plan/ BEFORE anything callable is published.

    The rows use the existing A1 bundle shape and carry hashes the existing
    owners already derived. Nothing here points at, copies truth from, or falls
    back to A1's committed launcher bundle.
    """
    d, _back = bundle()
    ldir = os.path.join(run_dir, "plan", LAUNCHER_DIRNAME)
    os.makedirs(ldir, exist_ok=True)
    by_event = collections.OrderedDict()
    for pk in d["packets"]:
        by_event.setdefault(pk["source_id"], []).append(pk)
    events = {e["source_id"]: e for e in d["events"]}
    slices, largest = [], 0
    for sid, body in sorted(d["launchers"].items()):
        path = os.path.join(ldir, "%s%s.workflow.js" % (LAUNCHER_PREFIX, sid))
        io.open(path + ".tmp", "w", encoding="utf-8").write(body)
        os.replace(path + ".tmp", path)
        raw = io.open(path, "rb").read()
        largest = max(largest, len(raw))
        ev = events[sid]
        slices.append(collections.OrderedDict([
            ("source_id", sid),
            ("launcher", os.path.relpath(path, BLM._REPO)),
            ("bytes", len(raw)),
            ("sha256", hashlib.sha256(raw).hexdigest()),
            ("input_path", ev["input_path"]),
            ("input_sha256", ev["input_sha256"]),
            ("packets", [{"packet_id": q["packet_id"],
                          "prompt_sha256": q["prompt_sha256"],
                          "lanes": [l["lane_id"] for l in q["lanes"]]}
                         for q in by_event[sid]])]))
    doc = collections.OrderedDict([
        ("bundle", "a5-exp5-launchers"),
        ("largest_launcher_bytes", largest),
        ("n_calls", len(d["calls"])),
        ("n_packets", len(d["packets"])),
        ("n_slices", len(slices)),
        ("slices", slices),
        ("workflow_max_bytes", BLM.WORKFLOW_MAX_BYTES)])
    return doc, slices


def a5_manifest_path(run_dir):
    """Where THIS run persists the A5 manifest the receipt binds."""
    return os.path.join(run_dir, "plan", MANIFEST_NAME)


def a5_plan_doc(run_dir=None):
    """The A5 plan the SHARED transport serializers read.

    Built here from the same derivation the manifest uses - never accepted from
    a caller - so the receipt, the args and the launchers describe one schedule.
    """
    d, _back = bundle()
    doc = collections.OrderedDict([
        # The door names the REPLY VALIDATION ROUTE, not the experiment: A5 is
        # the sparse one-item path, so it declares that route. The experiment
        # is identified by launcher_prefix and manifest_path.
        ("door", RT_DOOR),
        ("runtime_model_id", RUNTIME_MODEL_ID),
        ("launcher_prefix", LAUNCHER_PREFIX),
        ("events", d["events"]),
        ("packets", d["packets"])])
    if run_dir is not None:
        doc["manifest_path"] = a5_manifest_path(run_dir)
        doc["bundle_path"] = a5_bundle_path(run_dir)
    return doc


def a5_calls():
    """The exact ordered (packet_id, lane_id) schedule. 196 x the active arms."""
    d, _back = bundle()
    calls = [tuple(c) for c in d["calls"]]
    want = len(d["packets"]) * len(ACTIVE_ARM_IDS)
    if len(calls) != want or len(set(calls)) != want:
        raise ValueError("the A5 schedule is %d calls (%d unique), not %d"
                         % (len(calls), len(set(calls)), want))
    for _pid, lid in calls:
        arm_for_call(lid)                 # refuses an unmapped lane
    return calls


def prepare(run_dir):
    """Arm THIS A5 schedule through the ONE shared publisher and gate.

    Codex SEQ 1403 items 1-3. prepare() now:
      * BUILDS and PERSISTS the A5 manifest/bundle pair first, so the receipt
        binds bytes that actually exist on disk;
      * runs the SHARED build_launch_manifest.preflight against THAT pair, so
        the 128000 setting, the frozen inventory, the frozen source manifest,
        the inventory validator, the exact derivation and the launcher-size
        checks all run before any callable file appears;
      * publishes through the shared receipt builder, told which plan it is.
    Nothing here re-implements a gate and no caller supplies a plan.
    """
    import raw_transport as RT
    if os.path.isdir(run_dir) and os.listdir(run_dir):
        return {"ok": False, "problems": ["output directory is not fresh"],
                "invocations": []}
    a2_freeze()
    bad = inventory_problems()
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}

    # NO GATE RUNS HERE. This called the shared gate BEFORE this run's own
    # manifest and bundle existed, so it could only check the COMMITTED A1
    # pair at the DEFAULT era - it proved a pair this run never serves. The
    # gate now runs once, below, against the exact persisted pair
    # (Codex SEQ 1470 item 2).

    # the A5 manifest is PERSISTED first, so the receipt can bind bytes that
    # exist on disk rather than a description of them.
    # THE WHOLE PUBLICATION IS RESERVED BEFORE THE FIRST CHILD WRITE.
    # `exist_ok=True` reserved nothing: two builders both proceeded, and the
    # loser rewrote the winner's launcher and bundle bytes on its way to being
    # refused at the manifest. `mkdir` is atomic and fails if the directory
    # exists, so the first builder to create `plan/` owns the run and the
    # second never writes a single child (Codex SEQ 1472 item 1).
    plan_dir = os.path.join(run_dir, "plan")
    # THE PARENT IS RACE-SAFE; the reservation is still `mkdir(plan_dir)`
    # alone. Two calls could both see an absent run_dir and one would raise
    # out of `makedirs` instead of returning the clean loser refusal below
    # (Codex SEQ 1473 item 4).
    os.makedirs(run_dir, exist_ok=True)
    try:
        os.mkdir(plan_dir)
    except OSError:
        return {"ok": False, "invocations": [],
                "problems": ["%s is already reserved by another publication; "
                             "a run is published once and never rewritten"
                             % plan_dir]}
    # A (Codex SEQ 1405): the exact UNARMED launcher bytes and their bundle
    # rows are persisted BEFORE anything callable exists, and the plan names
    # them. Nothing falls back to A1's committed launcher bundle.
    bdoc, _slices = persist_launchers(run_dir)
    bpath = a5_bundle_path(run_dir)
    btext = json.dumps(bdoc, indent=1)
    io.open(bpath + ".tmp", "w", encoding="utf-8").write(btext)
    os.replace(bpath + ".tmp", bpath)
    a5_manifest = os.path.join(plan_dir, MANIFEST_NAME)
    # THE PERSISTED MANIFEST IS THE TRANSPORT PLAN. Codex SEQ 1404 item 1: it
    # must carry everything needed to rederive the 196 packets, 392 calls,
    # launcher prefix and bytes - so the descriptive manifest and the plan are
    # ONE document, not two that can disagree.
    doc = plan()
    doc.update(a5_plan_doc(run_dir))
    doc["bundle_sha256"] = _sha_text(btext)
    # THE BINDINGS THE SHARED GATE REQUIRES, so this pair can actually be
    # gated: the frozen inventory and source manifest it was built from, and
    # its own derived call count. Absent, the gate could not check them.
    doc["inventory_path"] = corrected_inventory()
    doc["inventory_sha256"] = BLM._sha(corrected_inventory())
    doc["source_manifest_sha256"] = BLM._sha(
        os.path.join(BLM.KF, "draft_inputs.hashes.json"))
    # A MALFORMED PLAN IS REFUSED BY THE GATE, not crashed on here: a doc with
    # no ordered calls records 0, and the gate then says so against its own
    # derived 392 instead of raising out of the builder.
    doc["n_calls"] = len(doc.get("ordered_calls") or [])
    doc["call_ceiling"] = doc["n_calls"]
    # THE PLAN DECLARES ITS OWN CALL BUDGET, derived exactly as the A1 plan
    # derives its own and through the SAME retry-limit owner. Without it the
    # shared pre-call gate could not check this pair at all.
    _retries = RT.A1_MAX_ATTEMPTS - 1
    _n = doc["n_calls"]
    doc["budget"] = collections.OrderedDict([
        ("primary_calls", _n),
        ("retry_cap", _n * _retries),
        ("all_in_max", _n * (1 + _retries))])
    # A PLAN MAY NOT CONTRADICT ITS OWN DERIVATION. The declared totals are
    # descriptive; the packets/calls are derived. A drifted total produced a
    # self-consistent, contract-clean receipt until this check existed.
    drift = []
    if doc.get("n_packets") != len(doc["packets"]):
        drift.append("n_packets %r is not the %d packets it carries"
                     % (doc.get("n_packets"), len(doc["packets"])))
    if doc.get("n_events") != len(doc["events"]):
        drift.append("n_events %r is not the %d events it carries"
                     % (doc.get("n_events"), len(doc["events"])))
    if doc.get("planned_producer_calls") != \
            len(doc["packets"]) * len(ACTIVE_ARM_IDS):
        drift.append("planned_producer_calls %r is not packets x arms"
                     % doc.get("planned_producer_calls"))
    if doc.get("launcher_prefix") != LAUNCHER_PREFIX:
        drift.append("the plan names launcher prefix %r, not %r"
                     % (doc.get("launcher_prefix"), LAUNCHER_PREFIX))
    if doc.get("door") != RT_DOOR:
        drift.append("the plan names door %r, not the sparse one-item route %r"
                     % (doc.get("door"), RT_DOOR))
    if drift:
        return {"ok": False, "problems": drift, "invocations": []}
    text = json.dumps(doc, indent=1)
    # ATOMIC AND WRITE-ONCE, through the one shared primitive. `os.replace`
    # is atomic REPLACEMENT: two builders could both pass the freshness check
    # and overwrite each other's plan, and neither would learn.
    RT.write_new(a5_manifest, text)
    if _sha_text(io.open(a5_manifest, encoding="utf-8").read()) != \
            _sha_text(text):
        raise ValueError("the persisted A5 manifest is not the built one")

    # NO GATE CALL HERE. `_a1_publish` below gates the exact persisted pair,
    # so calling the same preflight here made the launch pass through two
    # gates and left two places that could disagree about which pair was
    # checked. The private publisher is the SOLE gate (Codex SEQ 1471 item 1).

    calls = a5_calls()
    # C (Codex SEQ 1405): A5 publishes through THE private publisher. Its own
    # receipt/launcher writer is gone, so there is one serializer, one receipt
    # contract and one set of durable writes.
    out = RT._a1_publish(run_dir, calls, 1)
    if not out.get("ok"):
        return {"ok": False, "problems": out.get("problems") or ["publish "
                "refused"], "invocations": []}
    rec = K_load(os.path.join(run_dir, "receipt.json"))
    if rec.get("manifest_sha256") != _sha_text(text):
        return {"ok": False, "invocations": [],
                "problems": ["the published receipt does not bind the "
                             "persisted A5 manifest"]}
    _d, backmap = bundle()
    bm = os.path.join(run_dir, "a5_menu_backmap.json")
    io.open(bm + ".tmp", "w", encoding="utf-8").write(
        json.dumps(backmap, indent=1, sort_keys=True))
    os.replace(bm + ".tmp", bm)
    out["a5_manifest_sha256"] = rec["manifest_sha256"]
    return out


def build(out_dir):
    """Write the A5 manifest deterministically. No calls, ever."""
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    doc = plan()
    text = json.dumps(doc, indent=1)
    path = os.path.join(out_dir, MANIFEST_NAME)
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(text)
    os.replace(tmp, path)
    # the runnable bytes themselves, one launcher per event
    d, backmap = bundle()
    # UNARMED TEMPLATE BYTES. These carry `const RECEIPT = null` until
    # prepare() arms them; the honest name says so rather than implying a
    # runnable launcher (Codex SEQ 1402 item 2).
    ldir = os.path.join(out_dir, "unarmed_launcher_templates_a5")
    os.path.isdir(ldir) or os.makedirs(ldir)
    for sid, body in sorted(d["launchers"].items()):
        lp = os.path.join(ldir, "exp5_a5_%s.template.js" % sid)
        io.open(lp + ".tmp", "w", encoding="utf-8").write(body)
        os.replace(lp + ".tmp", lp)
    bp = os.path.join(out_dir, "a5_menu_backmap.json")
    io.open(bp + ".tmp", "w", encoding="utf-8").write(
        json.dumps(backmap, indent=1, sort_keys=True))
    os.replace(bp + ".tmp", bp)
    return path, _sha_text(text), doc
