"""A5 — the still-unrun EXP-5 reader kit, versioned. Codex SEQ 1400.

WHAT THIS OWNER ADDS, and nothing else:
  * the A5 ACTIVE ARM SCHEDULE  - P1 sonnet_run1, P2 sonnet_run2, both exact
    Sonnet 5 / high / independent. P3-P5, Qwen, GPT, Opus, Haiku and every
    fallback or escalation are ABSENT from the active plan; the frozen 156-call
    manifest keeps them as historical evidence and is never rewritten.
  * the A4 V6 LOCK BINDING     - path plus sha256, refused if either moves.
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
import a1_reader
import raw_transport

#: The A4 V6 key this kit reads against. Codex SEQ 1400 item 3 pins both.
A4_V6_LOCK_PATH = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/runs/kf-a4-signer-20260823T180519Z/a4_detailed_key_lock_v6.json"
A4_V6_LOCK_SHA = "c1d4deb2c12a257326ffb03434a28ecad2ec51282864e7b26f2ccdd0f7dd80c9"

#: The ONLY active arms. Both Sonnet 5 at high effort, independent runs.
ACTIVE_ARMS = (
    collections.OrderedDict([("arm", "P1"), ("role", "sonnet_run1"),
                             ("tier", "sonnet"), ("effort", "high"),
                             ("scope", "all_items"), ("active", True)]),
    collections.OrderedDict([("arm", "P2"), ("role", "sonnet_run2"),
                             ("tier", "sonnet"), ("effort", "high"),
                             ("scope", "all_items"), ("active", True)]),
)

#: Retired from the ACTIVE plan, retained in the frozen 156-call manifest.
RETIRED_ARMS = ("P3 haiku_run1", "P4 haiku_run2", "P5 opus_ref",
                "conditional_cheap_fallback", "od11_contingency")

MANIFEST_NAME = "a5_exp5_reader.manifest.json"


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def a4_lock():
    """The locked A4 key, refused unless its bytes are exactly the pinned ones."""
    if not os.path.isfile(A4_V6_LOCK_PATH):
        raise ValueError("the A4 V6 lock is missing at %s" % A4_V6_LOCK_PATH)
    raw = io.open(A4_V6_LOCK_PATH, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != A4_V6_LOCK_SHA:
        raise ValueError("the A4 V6 lock moved: %s is not the pinned %s"
                         % (got, A4_V6_LOCK_SHA))
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("state") != "LOCKED" or not doc["signature"]["signed"]:
        raise ValueError("the A4 V6 lock is not a signed LOCKED document")
    return doc


def locked_sources(lock=None):
    """The 36 ordered event source ids the locked key seals."""
    lock = lock or a4_lock()
    return [s["source_id"] for s in lock["key_shards"]]


def packets():
    """The final ordered item/control packets, from the ONE packet owner."""
    events = BLM._events()
    order = locked_sources()
    seen = [e["source_id"] for e in events]
    if sorted(seen) != sorted(order):
        raise ValueError("the frozen events and the locked key disagree: "
                         "%d vs %d" % (len(seen), len(order)))
    if seen != order:
        raise ValueError("the frozen events are not in the locked key's order")
    return BLM._one_item_packets(events, role="producer")


def plan():
    """The A5 manifest. Every count is DERIVED here, never typed."""
    lock = a4_lock()
    pks, prompts = packets()
    n_packets = len(pks)
    n_calls = n_packets * len(ACTIVE_ARMS)
    cap = BLM.measured_capacity(pks, prompts)
    return collections.OrderedDict([
        ("plan", "A5 EXP-5 one-item reader kit"),
        ("door", BLM.DOOR if hasattr(BLM, "DOOR") else "a5"),
        ("a4_v6_lock", collections.OrderedDict([
            ("path", A4_V6_LOCK_PATH), ("sha256", A4_V6_LOCK_SHA),
            ("state", lock["state"]),
            ("key_shards", len(lock["key_shards"]))])),
        ("n_events", len(locked_sources(lock))),
        ("n_packets", n_packets),
        ("arms", [dict(a) for a in ACTIVE_ARMS]),
        ("planned_producer_calls", n_calls),
        ("retired_from_active_plan", list(RETIRED_ARMS)),
        ("made_calls", 0),
        ("reply_shape", list(a1_reader.REPLY_KEYS)
         if hasattr(a1_reader, "REPLY_KEYS")
         else ["source_id", "facts", "abstentions", "continuity_hints"]),
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
        ("capacity", cap),
        ("prompt_sha256", collections.OrderedDict(
            (k, _sha_text(v)) for k, v in sorted(prompts.items()))),
    ])


def build(out_dir):
    """Write the A5 manifest deterministically. No calls, ever."""
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    doc = plan()
    text = json.dumps(doc, indent=1)
    path = os.path.join(out_dir, MANIFEST_NAME)
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(text)
    os.replace(tmp, path)
    return path, _sha_text(text), doc
