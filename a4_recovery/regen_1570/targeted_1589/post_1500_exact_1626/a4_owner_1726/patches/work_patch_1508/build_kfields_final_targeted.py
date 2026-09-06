"""THE SUCCESSOR FINAL ADJUDICATION OF THE CORRECTED ITEMS (Codex SEQ 1496).

ONE FIXED VERSIONED WRAPPER over the current A4 final-adjudication owner,
`build_kfields_final`. That owner is the locked loader of the signed key: its
ROLE, task section, output section, reply parser (`read_shard`), row
accounting law, same-event duplicate check, gold door, launcher
transformation and canonical raw-tree digest are used here UNCHANGED. Only
what is genuinely this package's is written here:

  * the POPULATION: the complete corrected-inventory diff grouped by its
    source event, in the diff's order - eight ordered event tasks, each
    carrying every corrected item of its event, so same-event repeats and
    multi-period facts are decided together; never a typed id list;
  * the LEADS: the accepted targeted key-review result when one exists and
    both blind hard-review results, read ONLY after both bound runs re-prove
    through their accounting owners, shown as the raw bytes they were emitted
    as, labelled untrusted, last in the prompt; no Codex proposal, no old key
    answer, no majority, no sibling event;
  * the CONTRACT VERSION: the byte-identical CURRENT v3 rules/output owners
    first, composed exactly as the locked owner composes its own prefix;
  * the lifecycle IDENTITY (one frozen event per call, F.RESULT_FIELDS) and
    the budget bound by hash to the current derived budget receipt.

The locked owner's reader validates rows against the FROZEN items and its
materializer is population-bound to the frozen 36 events and 196 rows; the
V6 lock pins that owner's bytes. So `read_shard` and `materialize` below are
the locked functions themselves, each called inside ONE serial try/finally
scope that supplies the corrected items / the eight-task population and
restores every owner after success or error (Codex SEQ 1497 item 4). No
body is copied and nothing here judges meaning.

No model is called by this module; nothing here reads the key.
"""
import collections
import copy
import functools
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_inventory_review as BIR                             # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_hard_review_targeted as HRT                 # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import raw_transport as RT                                       # noqa: E402

INV = K.INV
C = K.C
AUD = K.AUD

DOOR = "a4_final_targeted_adjudication"
#: THE fixed version this wrapper serves; a receipt of another version refuses
VERSION = "kfields-a4-final-targeted/1496"
#: THE contract version the adjudicator reads: the current producer era
SUFFIX = BLM.PRODUCER_CONTRACT_SUFFIX
MANIFEST_NAME = "final_targeted.manifest.json"
PREFIX_NAME = "prompt_prefix_final_targeted.txt"
LAUNCHER_NAME = "kfields-a4-final-targeted-adjudication"
PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_1499")
#: THIS wrapper's own live bytes, bound into every manifest and receipt it
#: derives (Codex SEQ 1497 item 1): the code cannot change after a freeze
#: without closing the gate.
_OWNER = os.path.abspath(__file__)
#: the current derived budget receipt this stage's numbers are bound to
BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1496.json"
MAX_ATTEMPTS = F.MAX_ATTEMPTS
#: attempt 2 ONLY for an invalid response or a PROVED transport no-answer
RETRYABLE = K.RETRYABLE
RESULT_FIELDS = F.RESULT_FIELDS
RECEIPT_IMMUTABLE = ("run_id", "door", "version", "attempt", "allowed",
                     "parent", "transport", "manifest_sha256", "derived_from",
                     "prompts")
#: the only two lead origins; anything else is leakage
LEAD_ORIGINS = ("targeted_key_review", "hard_review_blind")
#: the trusted section headers, in order, all ABOVE the boundary
PREFIX_MARKS = ("[ROLE]", "[RULES]", "[OUTPUT]", "[THE GATE]", "[TAG RULES]",
                "[A4 FINAL TASK]", "[A4 FINAL OUTPUT]")
PAYLOAD_KEYS = ("menu", "event", "rows", "groups", "leads")
#: the separate signer this closeout reserves and never renders here
SIGNER_RESERVE = collections.OrderedDict([("primaries", 1), ("retry_cap", 1)])
#: THE IMMUTABLE PRIMARY EVIDENCE BINDING (Codex SEQ 1501 item 1): the
#: finalized primary run by receipt, finalization, every raw/proved byte, the
#: canonical raw tree AND the package it ran under. A finalized run whose
#: package has since moved on is closed history (the locked owner's law): it
#: is proved against those pinned bytes, never re-derived live.
BINDING = os.path.join(K.EVIDENCE, "final_targeted_binding.json")
BINDING_SCHEMA = "a4-final-targeted-evidence-binding/1"
#: THE ONE BOUND REVIEW RECEIPT the correction population derives from
#: (Codex SEQ 1501 item 2): the primary shards' own open issues, copied
#: verbatim, plus the reviewer's findings, each pointing at existing rules.
REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1502.json")
REVIEW_SCHEMA = "a4-final-review-receipt/1"
FINDING_KINDS = ("open_issue", "reviewer_finding")
#: the correction phase: the same lifecycle, keyed by the receipt's door
CORR_DOOR = "a4_final_targeted_correction"
CORR_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr_1503")
CORR_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1501.json"
CORR_MANIFEST_NAME = "final_targeted_correction.manifest.json"
CORR_PREFIX_NAME = "prompt_prefix_final_targeted_correction.txt"
CORR_LAUNCHER_NAME = "kfields-a4-final-targeted-correction"
CORR_LEAD_ORIGIN = "final_targeted_primary"
CORR_PAYLOAD_KEYS = PAYLOAD_KEYS + ("reviewer_findings",)
CORR_PREFIX_MARKS = PREFIX_MARKS + ("[FINAL DECISION RULES]", "[A4 CORRECTION TASK]")
CORR_LEAD_KEYS = ("lead_id", "origin", "sha256", "reply")

# Codex SEQ 1505: the second correction round over exactly the events whose
# accepted shard still carries an open issue. Its own package, budget receipt
# and review receipt; everything else is the correction phase's.
CORR_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr_binding.json")
CORR2_DOOR = "a4_final_targeted_correction_2"
CORR2_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr2_1505")
CORR2_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1505.json"
CORR2_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1505.json")
CORR2_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr2_binding.json")
# Codex SEQ 1507/1508: the third round over exactly the events the bound
# review receipt names (the one still carrying an open issue and the one whose
# accepted tag and note the reviewer proved wrong), with the locked A4 owner's
# exact final-decision block served in the common correction prefix.
CORR3_DOOR = "a4_final_targeted_correction_3"
CORR3_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr3_1508")
CORR3_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1508.json"
CORR3_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1508.json")
CORR3_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr3_binding.json")
CORRECTION_DOORS = (CORR_DOOR, CORR2_DOOR, CORR3_DOOR)   # the rounds, in the order their overlays apply
#: every lead origin this wrapper emits starts with this stem; a lead id is the rest of it over the event
_ORIGIN_STEM = "final_targeted_"
_DOORS = (DOOR,) + CORRECTION_DOORS


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: Cached evidence may be reused INSIDE one operation and never across one
#: (the locked owner's accepted rule, Codex SEQ 1385/1497): the OUTERMOST
#: build/gate/prepare/finalize/load operation clears the lead cache, so every
#: safety-critical operation starts from a fresh owner proof; nested reads
#: reuse it.
_OP_DEPTH = [0]


def _operation(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if _OP_DEPTH[0] == 0:
            _leads_cached.cache_clear()
            _bound_cached.cache_clear()
        _OP_DEPTH[0] += 1
        try:
            return fn(*args, **kwargs)
        finally:
            _OP_DEPTH[0] -= 1
    return wrapper


def _sha(text):
    return K._sha(text)


# ---------------------------------------------------------- the population --
def items():
    """The corrected located items, by key (the targeted owner's binding)."""
    return {i["packet_id"]: i for i in T.targeted_items()}


def _a4_run():
    """The phase-one run whose frozen locator groups the hard review derived."""
    with io.open(os.path.join(K.EVIDENCE, "a4_dir.txt"), encoding="utf-8") as fh:
        return fh.read().strip()


def event_tasks():
    """THE eight: the complete corrected diff grouped by source event, in the
    diff's order of first appearance; every corrected item of an event in its
    one task. A locator group is carried only where two or more of ITS members
    are corrected items of that event."""
    by = items()
    order, rows = [], collections.OrderedDict()
    for pid in T.targets():
        if pid not in by:
            raise ValueError("target %s is not a corrected item" % pid)
        sid = by[pid]["source_id"]
        if sid not in rows:
            rows[sid] = []
            order.append(sid)
        rows[sid].append(pid)
    grouped = collections.OrderedDict()
    for t in HR.tasks(_a4_run()):
        if t["kind"] == "group":
            grouped[t["task_id"]] = list(t["members"])
    out = []
    for n, sid in enumerate(order):
        groups = collections.OrderedDict()
        for gid, members in grouped.items():
            here = [p for p in rows[sid] if p in members]
            if len(here) > 1:
                groups[gid] = here
        out.append(collections.OrderedDict([
            ("task_id", "fta-%03d" % n), ("event_index", n + 1),
            ("source_id", sid), ("rows", list(rows[sid])), ("groups", groups)]))
    return out


def population_problems(built):
    """The population is exactly the diff grouped by event, once each."""
    bad = []
    want = event_tasks()
    if [t["rows"] for t in built] != [t["rows"] for t in want]:
        bad.append("the tasks are not the complete corrected diff grouped by "
                   "event in order")
    if [t["task_id"] for t in built] != ["fta-%03d" % n for n in range(len(want))]:
        bad.append("the task ids are not the derived ones")
    if [t["source_id"] for t in built] != [t["source_id"] for t in want] or \
            [t["event_index"] for t in built] != list(range(1, len(want) + 1)):
        bad.append("the events are not the derived ones in order")
    if [dict(t["groups"]) for t in built] != [dict(t["groups"]) for t in want]:
        bad.append("the locator groups are not the derived ones")
    flat = [p for t in built for p in t["rows"]]
    if sorted(flat) != sorted(T.targets()) or len(set(flat)) != len(flat):
        bad.append("a corrected item is missing, extra or repeated")
    by = items()
    if any(by[p]["source_id"] != t["source_id"] for t in built for p in t["rows"]):
        bad.append("a task carries an item of another event")
    return bad


# --------------------------------------------------------------- the leads --
def _bound_run(binding):
    return _load(binding)["run_dir"]


@functools.lru_cache(maxsize=None)
def _leads_cached(targeted_binding_sha, hard_review_binding_sha):
    """{packet: [(lead_id, origin, sha256, raw text)]} - read ONLY after both
    bound runs re-prove through their own accounting owners, which refuse any
    missing, foreign or tampered byte. Keyed by the two immutable bindings."""
    del targeted_binding_sha, hard_review_binding_sha      # part of the key
    out = collections.defaultdict(list)
    for row in T.proved_spend(_bound_run(T.BINDING)):
        fin = _load(os.path.join(row["run_dir"], K.FINALIZATION_NAME))
        for label, outcome, _why in fin["outcomes"]:
            if outcome != "valid":
                continue
            text = K._read(os.path.join(
                row["run_dir"], "raw", "%s.attempt%d.proved.json"
                % (label.replace("#", "_"), row["attempt"])))
            out[label].append(("targeted/%s" % label, LEAD_ORIGINS[0],
                               _sha(text), text))
    by_label = {HR.call_label(t["task_id"], b): t["members"][0]
                for t in HRT.tasks() for b in HR.BLINDS}
    for row in HRT.proved_spend(_bound_run(HRT.BINDING)):
        fin = _load(os.path.join(row["run_dir"], K.FINALIZATION_NAME))
        for label, outcome, _why in fin["outcomes"]:
            if outcome != "valid":
                continue
            text = K._read(os.path.join(
                row["run_dir"], "raw", "%s.attempt%d.proved.json"
                % (label.replace("/", "_"), row["attempt"])))
            out[by_label[label]].append((label, LEAD_ORIGINS[1], _sha(text),
                                         text))
    return dict(out)


def leads():
    """Callers get COPIES; nothing they mutate reaches the cache (SEQ 1490)."""
    cached = _leads_cached(INV.sha_file(T.BINDING), INV.sha_file(HRT.BINDING))
    return {k: list(v) for k, v in cached.items()}


def event_leads(task):
    """Every raw independent lead for this task's rows, hash-bound, in row
    order: the accepted targeted key-review result when one exists, then the
    two blind readings. Nothing is scored, ranked, counted or merged here."""
    out = []
    for n, packet in enumerate(task["rows"]):
        for lead_id, origin, sha, text in leads().get(packet, []):
            out.append(collections.OrderedDict([
                ("lead_id", "%s/row%d" % (lead_id, n + 1)),
                ("row_index", n + 1), ("origin", origin),
                ("sha256", sha), ("reply", text)]))
    return out


# -------------------------------------------------------------- the prompt --
def input_sentence():
    """The released 'what the data looks like' sentence, naming the keys THIS
    payload actually has, in their order - derived, never typed."""
    keys = ["`%s`" % k for k in PAYLOAD_KEYS]
    return ("Everything below is ONE JSON object with the keys %s and\n%s, in "
            "that order." % (", ".join(keys[:-1]), keys[-1]))


def truthful_control():
    """The released injection control with ONLY its input sentence replaced
    (Codex SEQ 1497 item 3). The stale sentence is anchored through the locked
    owner; if it is not present exactly once this refuses rather than guess."""
    stale = F._released_input_sentence()
    if C.INJECTION_CONTROL.count(stale) != 1:
        raise ValueError("the released input sentence is not present exactly "
                         "once; refusing to guess which one to replace")
    return C.INJECTION_CONTROL.replace(stale, input_sentence(), 1)


def _prefix(suffix):
    """The locked owner's own composition, at ONE named contract version.
    With the empty suffix this is `F.prompt_prefix()` byte for byte, except
    the one data-boundary sentence made truthful for this payload."""
    return (
        "[ROLE]\n%s\n\n" % F._ROLE
        + "[RULES]\n%s\n\n" % C.role_rules("drafter", suffix)
        + "[OUTPUT]\n%s\n\n" % C.one_item_output_section().rstrip()
        + "[THE GATE]\nThe `%s` gate, quoted exactly:\n\n%s\n\n"
        % (F.GOLD_ONLY[0], BIR.gate_text().rstrip())
        + "[TAG RULES]\n%s\n\n" % BIR.crosswalk_text().rstrip()
        + "[A4 FINAL TASK]\n%s\n\n" % F._task_section()
        + "[A4 FINAL OUTPUT]\n%s\n\n" % F._output_section()
        + "[BOUNDARY]\n%s\n\n" % HR._boundary_at(suffix)
        + "%s\n\n" % truthful_control()
        + "[INPUT]\n")


def prompt_prefix():
    return _prefix(SUFFIX)


def _payload(task):
    """menu, the complete ordered event, the corrected rows, groups, then the
    untrusted leads LAST. The locked owner's own row shape."""
    src, display, _back = HR._source(task["source_id"])
    by = items()
    kinds = {p: r["proposed_record_kind"] for p, r in F._inventory()}
    rows = [collections.OrderedDict(
        [("row_index", n + 1), ("proposed_record_kind", kinds[p])]
        + list(K._frozen_item(by[p]).items()))
        for n, p in enumerate(task["rows"])]
    index_of = {p: n + 1 for n, p in enumerate(task["rows"])}
    groups = [collections.OrderedDict([
        ("member_row_indexes", [index_of[m] for m in members])])
        for members in task["groups"].values()]
    return collections.OrderedDict([
        ("menu", list(display)),
        ("event", collections.OrderedDict((k, src[k]) for k in HR.EVENT_VIEW)),
        ("rows", rows), ("groups", groups), ("leads", event_leads(task))])


def payload(task):
    return _payload(task)


def final_prompt(task):
    # NO default= on purpose: every lead is already raw text, so a stray exact
    # Decimal must RAISE rather than be silently rendered as a quoted string.
    return prompt_prefix() + json.dumps(_payload(task), indent=1)


def render_launcher(task, attempt=1):
    """The released hard-review launcher, transformed exactly as the locked
    owner transforms it - never a twin. The transport lines arrive as the
    released owner wrote them."""
    if not (isinstance(attempt, int) and 1 <= attempt <= MAX_ATTEMPTS):
        raise ValueError("attempt %r is outside 1..%d" % (attempt, MAX_ATTEMPTS))
    base = HRT.render_launcher(HRT.tasks()[0], HR.BLINDS[0], attempt)
    call = collections.OrderedDict([("source_id", task["source_id"]),
                                    ("event_index", task["event_index"]),
                                    ("rows", list(task["rows"])),
                                    ("attempt", attempt)])
    lines = base.split("\n")
    F._swap(lines, "  name:", "  name: '%s'," % LAUNCHER_NAME, "meta name")
    F._swap(lines, "  description:",
            "  description: 'K-fields A4 final targeted adjudication: one "
            "independent key owner settles every corrected row of one event',",
            "description")
    F._swap(lines, "  phases:", "  phases: [{ title: 'Adjudicate' }],", "phases")
    F._swap(lines, "const CALL = ", "const CALL = " + json.dumps(call), "CALL")
    F._swap(lines, "const PROMPT = ", "const PROMPT = "
            + json.dumps(final_prompt(task)), "PROMPT")
    F._swap(lines, "    label:",
            "    label: " + json.dumps(task["source_id"]) + ",", "label")
    F._swap(lines, "    phase:", "    phase: 'Adjudicate',", "phase")
    F._swap(lines, "return { task_id:",
            "return { source_id: CALL.source_id, event_index: CALL.event_index,",
            "return head")
    F._swap(lines, "         members: CALL.members", "         rows: CALL.rows,",
            "return members")
    return "\n".join(lines)


# ------------------------------------------------------------- the package --
def _derived_from():
    return collections.OrderedDict([
        ("key_owner_sha256", INV.sha_file(os.path.join(_HERE, "build_kfields_key.py"))),
        ("targeted_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_key_targeted.py"))),
        ("hard_review_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_hard_review.py"))),
        ("hard_review_targeted_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_hard_review_targeted.py"))),
        ("final_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_final.py"))),
        ("final_targeted_owner_sha256", INV.sha_file(_OWNER)),
        ("inventory_review_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_inventory_review.py"))),
        ("raw_parser_sha256", INV.sha_file(os.path.join(_HERE, "raw_transport.py"))),
        ("gold_door_sha256", INV.sha_file(os.path.join(_HERE, "kf_lint.py"))),
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("corrected_inventory_sha256", INV.sha_file(T.CORRECTED_INVENTORY)),
        ("correction_receipt_sha256", INV.sha_file(T.CORRECTION_RECEIPT)),
        ("targets", T.targets()),
        ("contract_package_sha256", INV.sha_file(C.package_path(SUFFIX))),
        ("locator_groups_sha256", INV.sha_file(
            os.path.join(_a4_run(), "conflicts_1370.json"))),
        ("targeted_binding", collections.OrderedDict([
            ("binding_path", T.BINDING), ("binding_sha256", INV.sha_file(T.BINDING)),
            ("run_dir", _bound_run(T.BINDING))])),
        ("hard_review_binding", collections.OrderedDict([
            ("binding_path", HRT.BINDING),
            ("binding_sha256", INV.sha_file(HRT.BINDING)),
            ("run_dir", _bound_run(HRT.BINDING))]))])


def _budget(primaries, receipt_path=None):
    """This stage's budget, bound by hash to the current budget receipt: the
    completed-before figure and the ceiling are that receipt's, never typed."""
    receipt_path = receipt_path or BUDGET_RECEIPT
    receipt = _load(receipt_path)
    before, ceiling = receipt["completed_before"], receipt["ceiling"]
    worst = before + primaries * MAX_ATTEMPTS
    return collections.OrderedDict([
        ("budget_receipt_path", receipt_path),
        ("budget_receipt_sha256", INV.sha_file(receipt_path)),
        ("before", before), ("primaries", primaries),
        ("max_attempts_per_call", MAX_ATTEMPTS),
        ("after_primaries", before + primaries),
        ("worst_case_after", worst),
        ("signer_reserve", collections.OrderedDict(SIGNER_RESERVE)),
        ("a4_closeout_clean", before + primaries + SIGNER_RESERVE["primaries"]),
        ("a4_closeout_worst", worst + SIGNER_RESERVE["primaries"]
         + SIGNER_RESERVE["retry_cap"]),
        ("global_ceiling", ceiling)])


@_operation
def manifest(door=None):
    """The complete manifest of ONE phase; the population is proved first.
    Writes nothing."""
    if door not in (None, DOOR):
        return _correction_manifest(door)
    tasks = event_tasks()
    bad = population_problems(tasks)
    if bad:
        raise ValueError("population refused: %s" % bad[:3])
    rows, scripts = [], []
    for task in tasks:
        text = final_prompt(task)
        script = render_launcher(task)
        scripts.append(len(script.encode("utf-8")))
        rows.append(collections.OrderedDict([
            ("task_id", task["task_id"]), ("event_index", task["event_index"]),
            ("source_id", task["source_id"]), ("rows", list(task["rows"])),
            ("groups", [list(v) for v in task["groups"].values()]),
            ("leads", [collections.OrderedDict(
                [("lead_id", x["lead_id"]), ("row_index", x["row_index"]),
                 ("origin", x["origin"]), ("sha256", x["sha256"])])
                for x in event_leads(task)]),
            ("payload_sha256", _sha(json.dumps(_payload(task), sort_keys=True))),
            ("prompt_sha256", _sha(text)),
            ("prompt_bytes", len(text.encode("utf-8"))),
            ("script_sha256", _sha(script)), ("script_bytes", scripts[-1])]))
    prefix = prompt_prefix()
    return collections.OrderedDict([
        ("door", DOOR), ("version", VERSION), ("authority", "Codex SEQ 1496"),
        ("step", "live Step 1 A4 - the successor final adjudication of the "
                 "corrected items"),
        ("contract_suffix", SUFFIX),
        ("derived_from", _derived_from()),
        ("role_sha256", _sha(F._ROLE)),
        ("semantic_rules_sha256", _sha(C.role_rules("drafter", SUFFIX))),
        ("output_card_sha256", _sha(C.one_item_output_section().rstrip())),
        ("gate_text_sha256", _sha(BIR.gate_text())),
        ("crosswalk_text_sha256", _sha(BIR.crosswalk_text())),
        ("task_section_sha256", _sha(F._task_section())),
        ("output_section_sha256", _sha(F._output_section())),
        ("boundary_sha256", _sha(HR._boundary_at(SUFFIX))),
        ("injection_control_sha256", _sha(truthful_control())),
        ("prefix_sha256", _sha(prefix)),
        ("prefix_bytes", len(prefix.encode("utf-8"))),
        ("transport", K._transport_block()),
        ("budget", _budget(len(rows))),
        ("counts", collections.OrderedDict([
            ("tasks", len(rows)),
            ("targets", sum(len(r["rows"]) for r in rows)),
            ("groups", sum(len(r["groups"]) for r in rows)),
            ("leads", sum(len(r["leads"]) for r in rows)),
            ("leads_by_origin", collections.OrderedDict(
                (o, sum(1 for r in rows for x in r["leads"] if x["origin"] == o))
                for o in LEAD_ORIGINS)),
            ("primary_calls", len(rows))])),
        ("capacity", collections.OrderedDict([
            ("unit", "UTF-8 bytes of the serialized launcher script the "
                     "runtime actually runs; never summed"),
            ("transport_limit_bytes", K.TRANSPORT_LIMIT),
            ("largest_script_bytes", max(scripts)),
            ("smallest_script_bytes", min(scripts)),
            ("largest_prompt_bytes", max(r["prompt_bytes"] for r in rows)),
            ("at_or_over_transport_limit",
             sorted(r["source_id"] for r, n in zip(rows, scripts)
                    if n >= K.TRANSPORT_LIMIT))])),
        ("tasks", rows),
        ("call_order", [r["source_id"] for r in rows])])


@_operation
def build(out_dir, door=None):
    """Write the frozen package of ONE phase ONCE. Launches nothing."""
    ph = _phase(door)
    doc = manifest(ph["door"])
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    text = json.dumps(doc, indent=1)
    RT.write_new(os.path.join(out_dir, ph["manifest"]), text)
    RT.write_new(os.path.join(out_dir, ph["prefix_name"]), ph["prefix"]())
    doc["manifest_sha256"] = _sha(text)
    return doc


@_operation
def package_problems(pkg_dir=None, door=None):
    """The whole rebuilt manifest and the shipped prefix against the package."""
    ph = _phase(door)
    pkg_dir = pkg_dir or ph["pkg_dir"]
    path = os.path.join(pkg_dir, ph["manifest"])
    if not os.path.isfile(path):
        return ["no manifest at %s" % pkg_dir]
    # EXPECTED failures - a missing, unreadable or malformed file, a refusing
    # evidence owner - are named problems, never a traceback out of a gate
    # (Codex SEQ 1498); programming errors are not caught.
    try:
        pinned = K._load(path)
    except (OSError, ValueError) as exc:
        return ["the packaged manifest cannot be read: %s" % exc]
    if not isinstance(pinned, dict):
        return ["the packaged manifest is not an object"]
    try:
        want = json.loads(json.dumps(manifest(ph["door"])))
    except (OSError, ValueError) as exc:
        return ["the manifest cannot be rebuilt: %s" % exc]
    bad = []
    if pinned != want:
        for field in want:
            if field == "tasks":
                continue
            if pinned.get(field) != want[field]:
                bad.append("the pinned %s is not the live one" % field)
        pin_by = {r["task_id"]: r for r in pinned.get("tasks") or []}
        for key in sorted(set(pin_by) | {r["task_id"] for r in want["tasks"]}):
            live = [r for r in want["tasks"] if r["task_id"] == key]
            if key not in pin_by:
                bad.append("%s is missing from the package" % key)
            elif not live:
                bad.append("%s is in the package but does not derive" % key)
            elif pin_by[key] != live[0]:
                bad.append("%s is not the live task" % key)
        if [r["task_id"] for r in pinned.get("tasks") or []] != \
                [r["task_id"] for r in want["tasks"]]:
            bad.append("the packaged tasks are out of their derived order")
        bad += ["manifest carries %r, which the rebuild does not" % k
                for k in pinned if k not in want]
        if not bad:
            bad.append("the package differs from the live derivation")
    shipped = os.path.join(pkg_dir, ph["prefix_name"])
    try:
        same = K._read(shipped) == ph["prefix"]()
    except (OSError, ValueError):
        same = False
    if not same:
        bad.append("the shipped prefix is not the live one")
    return bad


@_operation
def prompt_order_problems(door=None):
    """Trusted instructions above the boundary in their fixed order, the
    byte-identical current rules first among them, only the data below, the
    leads (and, in the correction phase, the findings) last and only of the
    lawful origins. -> [problems]"""
    ph = _phase(door)
    bad, boundary = [], HR._boundary_at(SUFFIX)
    prefix, rules = ph["prefix"](), C.role_rules("drafter", SUFFIX)
    control, stale = ph["control"](), F._released_input_sentence()
    stale_too = [] if ph["door"] == DOOR else [input_sentence()]
    for task in ph["tasks"]():
        text, where = ph["prompt"](task), task["task_id"]
        cut = text.find(boundary)
        if cut < 0:
            bad.append("%s: the live boundary is missing" % where)
            continue
        if text.count("[BOUNDARY]\n") != 1:
            bad.append("%s: the boundary does not appear exactly once" % where)
        heads = [l for l in text[:cut].splitlines()
                 if l.startswith("[") and l.endswith("]")]
        if heads != list(ph["marks"]) + ["[BOUNDARY]"]:
            bad.append("%s: the trusted sections above the boundary are %s, "
                       "not the fixed ones" % (where, heads))
        if "[RULES]\n%s\n\n" % rules not in text[:cut]:
            bad.append("%s: the current rules are not served whole and first"
                       % where)
        if ph["door"] != DOOR and text[:cut].count(_decision_block()) != 1:
            bad.append("%s: the owner's final-decision block is not served exactly once" % where)
        if text.find(control) < cut:
            bad.append("%s: the truthful injection control does not follow the "
                       "boundary" % where)
        if stale in text or any(x in text for x in stale_too):
            bad.append("%s: a stale input sentence names keys the payload does "
                       "not have" % where)
        if text.rfind("[INPUT]\n") < cut:
            bad.append("%s: the data does not follow the boundary" % where)
        if not text.startswith(prefix):
            bad.append("%s: the instruction block is not the live prefix" % where)
        body = text[len(prefix):]
        try:
            obj = json.loads(body, object_pairs_hook=collections.OrderedDict)
        except ValueError:
            bad.append("%s: the data is not one JSON object" % where)
            continue
        if list(obj) != list(ph["payload_keys"]):
            bad.append("%s: the payload keys are %s, not %s with the data last"
                       % (where, list(obj), list(ph["payload_keys"])))
            continue
        if "`%s`" % list(obj)[-1] not in ph["sentence"]():
            bad.append("%s: the input sentence does not name the rendered keys" % where)
        for lead in obj["leads"]:
            if lead.get("origin") not in ph["lead_origins"] or \
                    set(lead) != set(ph["lead_keys"]):
                bad.append("%s: a lead is not a raw lead of a lawful origin"
                           % where)
            elif _sha(lead["reply"]) != lead["sha256"]:
                bad.append("%s: a lead's bytes are not its bound hash" % where)
        for finding in obj.get("reviewer_findings") or []:
            if finding.get("kind") not in FINDING_KINDS:
                bad.append("%s: a finding is not of a lawful kind" % where)
    return bad


def budget_problems(doc):
    """The pinned budget against the receipt it binds and the LIVE ledger."""
    b, bad = doc["budget"], []
    receipt_path = _phase(doc.get("door"))["budget_receipt"]
    try:
        if INV.sha_file(receipt_path) != b["budget_receipt_sha256"]:
            raise ValueError("the file's sha256 is not the pinned one")
        receipt = _load(receipt_path)
    except (OSError, ValueError) as exc:      # missing, unreadable, malformed or not the bound bytes
        bad.append("the budget receipt is not the bound one: %s" % exc)
        return bad
    n = doc["counts"]["primary_calls"]
    for field, want in (("before", receipt["completed_before"]),
                        ("primaries", n),
                        ("after_primaries", receipt["completed_before"] + n),
                        ("worst_case_after", receipt["completed_before"] + n * MAX_ATTEMPTS),
                        ("a4_closeout_clean", receipt["completed_before"] + n
                         + SIGNER_RESERVE["primaries"]),
                        ("a4_closeout_worst", receipt["completed_before"]
                         + n * MAX_ATTEMPTS + SIGNER_RESERVE["primaries"]
                         + SIGNER_RESERVE["retry_cap"]),
                        ("global_ceiling", receipt["ceiling"])):
        if b.get(field) != want:
            bad.append("budget.%s is %r, not the derived %r" % (field, b.get(field), want))
    if b["a4_closeout_worst"] > b["global_ceiling"]:
        bad.append("the worst closeout would break the global ceiling")
    import a6_launch_freeze as A6
    try:
        live = A6.ledger()[0]
    except (OSError, ValueError) as exc:      # a refusing or missing evidence owner is a
        bad.append("the live ledger cannot be derived: %s" % exc)   # reported refusal, never a traceback
        return bad
    if live != b["before"]:
        bad.append("the live ledger is %d, not the bound before %d"
                   % (live, b["before"]))
    return bad


@_operation
def preflight(pkg_dir=None, door=None):
    """The one gate before any call of ONE phase is ever made."""
    ph = _phase(door)
    pkg_dir = pkg_dir or ph["pkg_dir"]
    problems = list(package_problems(pkg_dir, ph["door"]))
    if problems:
        # TERMINAL (Codex SEQ 1499): the package owner has proved this package
        # is not usable, so nothing below may consume its bytes - no prompt
        # rendering, no packaged field, no budget read.
        return {"ok": False, "problems": problems, "manifest": None}
    try:
        problems += prompt_order_problems(ph["door"])
    except (OSError, ValueError) as exc:      # a refusing or missing evidence owner is a
        problems.append("the prompts cannot be rendered: %s" % exc)   # reported refusal, never a traceback out of a gate
    path = os.path.join(pkg_dir, ph["manifest"])
    if not os.path.isfile(path):
        return {"ok": False, "problems": problems, "manifest": None}
    try:
        doc = K._load(path)
    except (OSError, ValueError) as exc:
        problems.append("the packaged manifest cannot be read: %s" % exc)
        return {"ok": False, "problems": problems, "manifest": None}
    if not isinstance(doc, dict) or any(
            k not in doc for k in ("version", "capacity", "call_order", "budget", "counts")):
        problems.append("the packaged manifest is not this wrapper's shape")
        return {"ok": False, "problems": problems, "manifest": None}
    if doc["capacity"]["at_or_over_transport_limit"]:
        problems.append("a launcher script is at or over the transport limit")
    if doc["capacity"]["transport_limit_bytes"] != K.TRANSPORT_LIMIT:
        problems.append("the pinned transport limit is not the live one")
    order = doc["call_order"]
    if len(set(order)) != len(order):
        problems.append("the same event is scheduled twice")
    if order != [t["source_id"] for t in ph["tasks"]()]:
        problems.append("the pinned call order is not the derived one")
    if doc.get("door") != ph["door"]:
        problems.append("the package is not this phase's")
    if doc.get("version") != VERSION:
        problems.append("the package is not this wrapper's version")
    problems += budget_problems(doc)
    return {"ok": not problems, "problems": problems, "manifest": doc}


# --------------------------------------------------------- the shard read ---
def read_shard(text, task, supplied_leads):
    """THE LOCKED OWNER'S READER, given the corrected items for the length of
    ONE serial call: `HR._items` is supplied and restored in try/finally.
    Measured before this was written: bound to the frozen quotes, the locked
    reader refuses 10 of the 11 lawful blind replies, because the corrected
    quotes are exactly what carry the scale marker."""
    corrected = items()
    real = HR._items
    HR._items = lambda: corrected
    try:
        return F.read_shard(text, task, supplied_leads)
    finally:
        HR._items = real


# ------------------------------------------------------- the run lifecycle --
# The proof, receipt, record and fixed-child PATTERN of the locked owner's
# event phase, over this population; every check that is not "which event" is
# the shared owners': K._official_proof, AUD._official_location,
# K.direct_result, HR.record_state, K._stored_matches, RT.write_new.
def _phase(door=None):
    """THE phases this wrapper serves - the primary and each correction round
    - resolved from module globals at call time. The same lifecycle serves
    all of them; only what a phase genuinely owns differs - its door,
    package, budget receipt, binding, population, prompt, launcher, leads,
    payload shape and sentence."""
    if door in (None, DOOR):
        return {"door": DOOR, "pkg_dir": PKG_DIR, "manifest": MANIFEST_NAME,
                "prefix_name": PREFIX_NAME, "budget_receipt": BUDGET_RECEIPT,
                "binding": BINDING,
                "tasks": event_tasks, "prompt": final_prompt,
                "launcher": render_launcher, "leads": event_leads,
                "payload": _payload,
                "prefix": prompt_prefix, "control": truthful_control,
                "sentence": input_sentence, "marks": PREFIX_MARKS,
                "payload_keys": PAYLOAD_KEYS, "lead_origins": LEAD_ORIGINS,
                "lead_keys": ("lead_id", "row_index", "origin", "sha256", "reply"),
                "derived_from": _derived_from}
    if door in CORRECTION_DOORS:
        r, P = _round(door), functools.partial
        earlier = CORRECTION_DOORS[:CORRECTION_DOORS.index(door)]
        return {"door": door, "pkg_dir": r["pkg_dir"],
                "manifest": CORR_MANIFEST_NAME, "prefix_name": CORR_PREFIX_NAME,
                "budget_receipt": r["budget_receipt"], "binding": r["binding"],
                "tasks": P(correction_tasks, door),
                "prompt": P(correction_prompt, door=door),
                "launcher": P(render_correction_launcher, door=door),
                "leads": P(correction_leads, door=door),
                "payload": P(correction_payload, door=door),
                "prefix": correction_prefix, "control": correction_control,
                "sentence": correction_input_sentence, "marks": CORR_PREFIX_MARKS,
                "payload_keys": CORR_PAYLOAD_KEYS,
                "lead_origins": (CORR_LEAD_ORIGIN,) + tuple(_round(d)["origin"] for d in earlier),
                "lead_keys": CORR_LEAD_KEYS,
                "derived_from": P(_correction_derived_from, door)}
    raise ValueError("%r is not a door of this wrapper" % (door,))


def _by_source(door=None):
    return {t["source_id"]: t for t in _phase(door)["tasks"]()}


def expected_receipt(out_dir, attempt, allowed, parent=None, door=None):
    ph = _phase(door)
    by = _by_source(ph["door"])
    man = os.path.join(ph["pkg_dir"], ph["manifest"])
    return collections.OrderedDict([
        ("run_id", os.path.basename(os.path.abspath(out_dir))),
        ("door", ph["door"]), ("version", VERSION), ("attempt", attempt),
        ("allowed", list(allowed)), ("parent", parent),
        ("transport", K._transport_block()),
        ("manifest_sha256", INV.sha_file(man) if os.path.isfile(man) else None),
        ("derived_from", ph["derived_from"]()),
        ("prompts", collections.OrderedDict(
            (sid, _sha(ph["prompt"](by[sid]))) for sid in allowed)),
        ("states", [])])


def _write_receipt(out_dir, attempt, allowed, parent=None, door=None):
    receipt = expected_receipt(out_dir, attempt, allowed, parent, door)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    RT.write_new(os.path.join(out_dir, K.RECEIPT_NAME),
                 json.dumps(receipt, indent=1))
    return receipt


def _expected_for(out_dir, receipt):
    attempt = receipt.get("attempt")
    try:
        ph = _phase(receipt.get("door"))
    except ValueError as exc:
        return None, [str(exc)]
    if attempt == 1:
        return expected_receipt(out_dir, 1,
                                [t["source_id"] for t in ph["tasks"]()],
                                None, ph["door"]), []
    if attempt != MAX_ATTEMPTS:
        return None, ["attempt %r is outside 1..%d" % (attempt, MAX_ATTEMPTS)]
    pfin = os.path.join(os.path.dirname(os.path.abspath(out_dir)),
                        K.FINALIZATION_NAME)
    if not os.path.isfile(pfin):
        return None, ["a child with no finalized parent is an orphan"]
    doc = K._load(pfin)
    parent = collections.OrderedDict([
        ("run_id", doc.get("run_id")),
        ("finalization_sha256", INV.sha_file(pfin))])
    return expected_receipt(out_dir, MAX_ATTEMPTS,
                            list(doc.get("retry") or []), parent,
                            ph["door"]), []


def receipt_problems(out_dir, receipt):
    if not isinstance(receipt, dict):
        return ["the receipt is not an object"]
    want, bad = _expected_for(out_dir, receipt)
    if want is None:
        return bad
    for field in RECEIPT_IMMUTABLE:
        if receipt.get(field) != want[field]:
            bad.append("receipt.%s is not the expected value" % field)
    if not isinstance(receipt.get("states"), list):
        bad.append("receipt.states is not a list")
    if set(receipt) != set(RECEIPT_IMMUTABLE) | {"states"}:
        bad.append("the receipt carries unexpected fields")
    return bad


def _invocations(out_dir, allowed, attempt, door=None):
    ph = _phase(door)
    by = _by_source(ph["door"])
    script_dir = os.path.join(out_dir, "scripts")
    os.path.isdir(script_dir) or os.makedirs(script_dir)
    out = []
    for sid in allowed:
        text = ph["launcher"](by[sid], attempt)
        path = os.path.join(script_dir, "%s.attempt%d.js" % (sid, attempt))
        HR._atomic(path, text)
        out.append(collections.OrderedDict([
            ("label", sid), ("attempt", attempt), ("scriptPath", path),
            ("args", None), ("script_sha256", _sha(text))]))
    return out


@_operation
def prepare_run(out_dir, door=None):
    """THE ONE public door of a phase: a fresh directory, the whole gate,
    then exactly that phase's frozen calls, in order."""
    ph = _phase(door)
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        return {"ok": False, "problems": ["output directory is not fresh"],
                "invocations": []}
    bad = preflight(ph["pkg_dir"], ph["door"])["problems"]
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    allowed = [t["source_id"] for t in ph["tasks"]()]
    _write_receipt(out_dir, 1, allowed, None, ph["door"])
    return {"ok": True, "problems": [],
            "invocations": _invocations(out_dir, allowed, 1, ph["door"])}


def prepare_correction_run(out_dir, door=CORR_DOOR):
    return prepare_run(out_dir, door)


record_state = HR.record_state


def run_evidence(out_dir, receipt, prompt_of=None, script_of=None):
    """THE run-level proof. -> {label: (outcome, why, text)}, problems.
    Every COMMON check runs before anything branches on the agent row state.
    `prompt_of` / `script_of` let a CLOSED run be proved against its pinned
    prefix and launcher bytes instead of the live derivation."""
    try:
        ph = _phase(receipt.get("door"))
    except ValueError as exc:
        return collections.OrderedDict(), [str(exc)]
    by = _by_source(ph["door"])
    prompt_of = prompt_of or ph["prompt"]
    script_of = script_of or ph["launcher"]
    attempt = receipt.get("attempt")
    allowed = set(receipt.get("allowed") or [])
    out, problems = collections.OrderedDict(), []
    runs, agents, responses, requests = set(), set(), set(), set()
    if receipt.get("parent"):                    # a child is fresh across its parent
        r, a, m, q = F._spent_identities_uncached(
            os.path.dirname(os.path.abspath(out_dir)))
        runs |= r; agents |= a; responses |= m; requests |= q
    for other in _DOORS:                         # freshness is across PHASES (the locked owner's
        if other != ph["door"] and _closed_run(other):   # law): no identity of another phase's
            r, a, m, q = F._spent_identities_uncached(_closed_run(other))   # bound run may serve this call
            runs |= r; agents |= a; responses |= m; requests |= q

    def _refuse(label, why, bad):
        problems.extend("%s: %s" % (label, b) for b in bad or [why])
        out[label] = ("unproved", why, None)

    for state in receipt.get("states") or []:
        run_id = (os.path.splitext(os.path.basename(state))[0]
                  if isinstance(state, str) else "unreadable")
        bad = []
        try:
            doc = K._load(state)
        except Exception as exc:                      # noqa: BLE001 - by design
            problems.append("%s: state unreadable (%s)" % (run_id, str(exc)[:80]))
            continue
        if not isinstance(doc, dict):
            problems.append("%s: state is not an object" % run_id)
            continue
        session_dir, session_id = AUD._official_location(state)
        if session_dir is None:
            bad.append("the state is not where the runtime puts an official one")
        elif session_id != K.PARENT_SESSION:
            bad.append("parent session %r is not the frozen one" % session_id)
        if doc.get("runId") != run_id:
            bad.append("state runId %r is not its own official name" % doc.get("runId"))
        if doc.get("runId") in runs:
            bad.append("run id %r was already spent" % doc.get("runId"))
        runs.add(doc.get("runId"))
        if doc.get("status") != "completed":
            bad.append("state status is %r" % doc.get("status"))
        rows = [r for r in (doc.get("workflowProgress") or [])
                if r.get("type") == "workflow_agent"]
        if len(rows) != 1:
            problems.append("%s: %d agent rows; one call runs exactly one"
                            % (run_id, len(rows)))
            continue
        row = rows[0]
        label = row.get("label")
        if label not in by:
            problems.append("%s: names %r, which is not a scheduled event" % (run_id, label))
            continue
        if label not in allowed:
            problems.append("%s: %s is not allowed by this receipt" % (run_id, label))
            continue
        if label in out:
            problems.append("%s: %s was already served" % (run_id, label))
            continue
        task = by[label]
        want_script = script_of(task, attempt)
        if doc.get("script") != want_script:
            bad.append("the state did not run the pinned launcher bytes")
        sp = doc.get("scriptPath")
        if sp is not None:
            if not (isinstance(sp, str) and os.path.isfile(sp)):
                bad.append("scriptPath %r is not a readable file" % sp)
            elif INV.sha_file(sp) != _sha(want_script):
                bad.append("the scriptPath bytes are not the pinned launcher")
        got = K.direct_result(doc)
        if got is None:
            bad.append("the state carries no returned result object")
        else:
            if set(got) != set(RESULT_FIELDS):
                bad.append("the returned object's keys are %s, not exactly %s"
                           % (sorted(got), sorted(RESULT_FIELDS)))
            for field, want in (("source_id", label),
                                ("event_index", task["event_index"]),
                                ("rows", list(task["rows"])), ("attempt", attempt),
                                ("model", K.MODEL), ("effort", K.EFFORT),
                                ("agentType", K.AGENT_TYPE)):
                if got.get(field) != want:
                    bad.append("result %s is %r, not %r" % (field, got.get(field), want))
        if row.get("state") == "done":
            if row.get("agentId") in agents:
                bad.append("agent id %r was already spent" % row.get("agentId"))
            agents.add(row.get("agentId"))
            final, complete, why = K._official_proof(state, prompt_of(task))
            bad += why
            tp = os.path.join(session_dir or "", "subagents", "workflows",
                              run_id, "agent-%s.jsonl" % row.get("agentId"))
            recs = AUD._jsonl(tp) if os.path.isfile(tp) else None
            if recs is None:
                bad.append("the transcript cannot be read whole")
            else:
                if {r.get("agentId") for r in recs} != {row.get("agentId")}:
                    bad.append("a transcript record carries a foreign agentId")
                if {r.get("sessionId") for r in recs} != {K.PARENT_SESSION}:
                    bad.append("a transcript record carries a foreign sessionId")
                asst = [r for r in recs if r.get("type") == "assistant"]
                ids = {(r.get("message") or {}).get("id") for r in asst}
                if ids & responses:
                    bad.append("a response id was already spent")
                responses |= ids
                rq = {r.get("requestId") for r in asst}
                if rq & requests:
                    bad.append("a request id was already spent")
                requests |= rq
            if got is not None and got.get("text") != final:
                bad.append("the returned text is not the proved final segment")
            if bad:
                _refuse(label, bad[0], bad)
                continue
            out[label] = ("proved", "", complete)
            continue
        if row.get("state") == "error":
            bad += AUD._rejection(row, K.AGENT_TYPE, K.EFFORT)
            if got is not None and got.get("text") is not None:
                bad.append("a pre-agent rejection cannot carry answer text")
            if K._spawned_transcripts(session_dir, run_id):
                bad.append("a pre-agent rejection cannot have spawned a worker")
            if not K._recorded_zero(doc.get("totalToolCalls")):
                bad.append("totalToolCalls is %r, not a recorded integer zero"
                           % (doc.get("totalToolCalls"),))
            if bad:
                _refuse(label, bad[0], bad)
                continue
            out[label] = ("transport_no_answer", K.NO_ANSWER, None)
            continue
        why = "the agent row is %r, not 'done'" % row.get("state")
        _refuse(label, why, bad + [why])
    return out, problems


def _budget_after(attempt, scheduled, door=None):
    ph = _phase(door)
    b = _budget(len(ph["tasks"]()), ph["budget_receipt"])
    spent = b["primaries"] + scheduled if attempt == MAX_ATTEMPTS else scheduled
    return collections.OrderedDict([
        ("ledger_before", b["before"]), ("this_attempt", scheduled),
        ("spent_so_far", spent), ("ledger_after", b["before"] + spent),
        ("frozen_primaries", b["primaries"]),
        ("worst_case_after", b["worst_case_after"]),
        ("a4_closeout_clean", b["a4_closeout_clean"]),
        ("a4_closeout_worst", b["a4_closeout_worst"]),
        ("global_ceiling", b["global_ceiling"]),
        ("within_ceiling", b["a4_closeout_worst"] <= b["global_ceiling"])])


@_operation
def finalize(out_dir):
    """Raw first, then the run-level proof, then ONE parse of each exact
    shard through the locked owner's parser. Write-once throughout."""
    receipt = K._load(os.path.join(out_dir, K.RECEIPT_NAME))
    attempt = receipt.get("attempt")
    ph = _phase(receipt.get("door"))
    by = _by_source(ph["door"])
    raw_dir = os.path.join(out_dir, "raw")
    os.path.isdir(raw_dir) or os.makedirs(raw_dir)
    harvested, mismatch = [], collections.OrderedDict()
    for state in receipt.get("states") or []:
        run_id = (os.path.splitext(os.path.basename(state))[0]
                  if isinstance(state, str) else "unreadable")
        try:
            doc = json.loads(K._read(state))
            got = K.direct_result(doc)
        except Exception:                             # noqa: BLE001 - by design
            doc, got = None, None
        label = K._state_label(doc)
        text = (got or {}).get("text")
        if isinstance(text, str):
            name = "%s.000" % run_id
            path = os.path.join(raw_dir, RT._raw_filename(name))
            same = K._stored_matches(path, text)
            if same is None:
                RT.save_raw(text, raw_dir, name)
            elif same is False:
                mismatch[label or run_id] = ("the stored raw answer %s is not the "
                                             "official returned text"
                                             % os.path.basename(path))
            harvested.append(os.path.basename(path))

    receipt_bad = package_problems(ph["pkg_dir"], ph["door"]) + receipt_problems(out_dir, receipt)
    allowed = list(receipt.get("allowed") or [])
    if receipt_bad:
        problems, outcomes = [], collections.OrderedDict(
            (lab, ("unproved", "the receipt is not the owner's")) for lab in allowed)
    else:
        proved, problems = run_evidence(out_dir, receipt)
        outcomes = collections.OrderedDict()
        for label, (state, why, text) in proved.items():
            if state != "proved" or label in mismatch:
                outcomes[label] = (state, why) if state != "proved" \
                    else ("unproved", mismatch[label])
                continue
            path = os.path.join(raw_dir, "%s.attempt%s.proved.json" % (label, attempt))
            same = K._stored_matches(path, text)
            if same is None:
                RT.write_new(path, text)
            elif same is False:
                mismatch[label] = ("the stored proved answer %s is not the "
                                   "official returned text" % os.path.basename(path))
                outcomes[label] = ("unproved", mismatch[label])
                continue
            _obj, bad = read_shard(text, by[label], ph["leads"](by[label]))
            outcomes[label] = ("valid", "") if not bad else ("invalid_response", bad[0])
    for label, why in mismatch.items():
        if label in allowed:
            outcomes[label] = ("unproved", why)
        problems.append("%s: %s" % (label, why))
    for label in allowed:
        outcomes.setdefault(label, ("missing", "no official state"))
    counts = collections.Counter(o for o, _w in outcomes.values())
    ledger = collections.OrderedDict(
        [("scheduled", len(allowed))]
        + [(name, counts.get(name, 0)) for name in
           ("valid", "invalid_response", "transport_no_answer", "unproved", "missing")])
    complete = (not receipt_bad and not problems
                and set(outcomes) == set(allowed)
                and counts.get("missing", 0) == 0
                and counts.get("unproved", 0) == 0)
    retry = [lab for lab in allowed if outcomes[lab][0] in RETRYABLE] \
        if complete and attempt == 1 else []
    doc = collections.OrderedDict([
        ("door", ph["door"]), ("version", VERSION), ("attempt", attempt),
        ("run_id", receipt.get("run_id")),
        ("receipt_sha256", INV.sha_file(os.path.join(out_dir, K.RECEIPT_NAME))),
        ("manifest_sha256", receipt.get("manifest_sha256")),
        ("derived_from", receipt.get("derived_from")),
        ("harvested_raw", harvested),
        ("primary_complete", complete),
        ("problems", receipt_bad + problems),
        ("outcomes", [[lab, o, w] for lab, (o, w) in outcomes.items()]),
        ("ledger", ledger),
        ("budget", _budget_after(attempt, len(allowed), ph["door"])),
        ("retry", retry)])
    RT.write_new(os.path.join(out_dir, K.FINALIZATION_NAME),
                 json.dumps(doc, indent=1))
    child = _publish_child(out_dir, doc)
    if child:
        doc["child"] = child
    return doc


def _publish_child(out_dir, doc):
    """At most ONE parent-bound child, identical prompts, published RUNNABLE."""
    labels = list(doc.get("retry") or [])
    if not labels or doc.get("attempt") != 1 or not doc.get("primary_complete"):
        return None
    child_dir = os.path.join(out_dir, "retry")
    if os.path.isdir(child_dir) and os.listdir(child_dir):
        return None
    ph = _phase(doc.get("door"))
    if preflight(ph["pkg_dir"], ph["door"])["problems"]:
        return None
    _write_receipt(child_dir, MAX_ATTEMPTS, labels,
                   parent=collections.OrderedDict([
                       ("run_id", doc["run_id"]),
                       ("finalization_sha256", INV.sha_file(
                           os.path.join(out_dir, K.FINALIZATION_NAME)))]),
                   door=ph["door"])
    receipt = K._load(os.path.join(child_dir, K.RECEIPT_NAME))
    if receipt_problems(child_dir, receipt):
        return None
    return {"dir": child_dir, "problems": [],
            "invocations": _invocations(child_dir, labels, MAX_ATTEMPTS, ph["door"])}


# ------------------------------------------------------- the materializer --
@_operation
def accepted_shards(run_dir):
    """The accepted shards of a FINALIZED successor run and their exact raw
    texts, re-proved: -> (shards, raws, problems). First valid wins across
    the primary and its one child."""
    shards, raws, bad = collections.OrderedDict(), collections.OrderedDict(), []
    by, ph, prompt_of = None, None, None
    for base in (run_dir, os.path.join(run_dir, "retry")):
        fin_path = os.path.join(base, K.FINALIZATION_NAME)
        if not os.path.isfile(fin_path):
            continue
        try:
            fin = K._load(fin_path)
            receipt = K._load(os.path.join(base, K.RECEIPT_NAME))
        except (OSError, ValueError) as exc:
            bad.append("%s: the finalization or receipt cannot be read: %s" % (base, exc))
            continue
        if not isinstance(fin, dict) or fin.get("door") not in _DOORS \
                or fin.get("version") != VERSION:
            bad.append("%s is not a finalized run of this wrapper" % base)
            continue
        if fin.get("receipt_sha256") != INV.sha_file(os.path.join(base, K.RECEIPT_NAME)):
            bad.append("%s: the receipt changed after finalization" % base)
            continue
        if ph is None:
            ph = _phase(fin.get("door")); by = _by_source(ph["door"])
            # A BOUND RUN IS CLOSED HISTORY: proved against its pinned package
            closed = _closed_run(ph["door"])
            if os.path.abspath(run_dir) == closed:
                pinned = _closed_pins(base, ph["door"])
                bad += _closed_receipt_problems(base, receipt, 1, pinned, ph["door"])
                prompt_of = lambda task, _p=pinned, _d=ph["door"]: _pinned_prompt(_p["package_dir"], task, _d)   # noqa: E731
                script_of = lambda task, attempt, _b=base: _pinned_script(_b, task, attempt)    # noqa: E731
        if prompt_of is None:
            bad += receipt_problems(base, receipt)
            script_of = None
        proved, probs = run_evidence(base, receipt, prompt_of, script_of)
        bad += probs
        for label, (state, _why, text) in proved.items():
            if state != "proved" or label in shards:
                continue
            stored = os.path.join(base, "raw", "%s.attempt%s.proved.json"
                                  % (label, receipt.get("attempt")))
            if K._stored_matches(stored, text) is not True:
                bad.append("%s: the stored shard is not the official text" % label)
                continue
            obj, why = read_shard(text, by[label], ph["leads"](by[label]))
            if not why:
                shards[label], raws[label] = obj, text
    return shards, raws, bad


# ---------------------------------- the completed runs, bound and counted --
# Codex SEQ 1501 item 1 / SEQ 1505 item 1: the targeted-run binding/pointer
# pattern over THIS lifecycle, one binding per door. The immutable binding
# decides which attempts exist, what their receipt, finalization, every
# raw/proved file and canonical raw tree ARE, and which package they ran
# under; a6_launch_freeze.ledger() only records the proved row. A FINALIZED
# run whose package has since moved on (this wrapper binds its own bytes, so
# every later change moves it) is CLOSED HISTORY: it is proved against the
# pinned package, never the live derivation - the locked owner's own law
# (build_kfields_final._receipt_still_the_proved_one).
_FINAL_OUTCOMES = ("valid", "invalid_response", "transport_no_answer")


def _measured_attempt(base, attempt):
    row = T._measured_attempt(base, attempt)
    row["raw_tree"] = F.raw_tree(base)
    return row


def write_binding(run_dir, pkg_dir, door=None):
    """Freeze one door's finalized run ONCE, with the package its receipt
    names by hash. Write-once through the transport's owner; never rewritten."""
    ph = _phase(door)
    run_dir = os.path.abspath(run_dir)
    rec = _load(os.path.join(run_dir, K.RECEIPT_NAME))
    man = os.path.join(pkg_dir, ph["manifest"])
    if INV.sha_file(man) != rec.get("manifest_sha256"):
        raise ValueError("%s is not the package this run's receipt names" % pkg_dir)
    attempts = [_measured_attempt(run_dir, 1)]
    child = os.path.join(run_dir, "retry")
    if os.path.isdir(child):
        attempts.append(_measured_attempt(child, MAX_ATTEMPTS))
    doc = collections.OrderedDict([
        ("schema", BINDING_SCHEMA), ("run_dir", run_dir),
        ("package", collections.OrderedDict([
            ("dir", os.path.abspath(pkg_dir)),
            ("manifest_sha256", INV.sha_file(man)),
            ("prefix_sha256", INV.sha_file(os.path.join(pkg_dir, ph["prefix_name"])))])),
        ("attempts", attempts)])
    RT.write_new(ph["binding"], json.dumps(doc, indent=1))
    return doc


def _closed_run(door=None):
    """One door's bound run directory, or None before its binding."""
    binding = _phase(door)["binding"]
    if not os.path.isfile(binding):
        return None
    return os.path.abspath(_load(binding)["run_dir"])


def _closed_pins(base, door=None):
    """The pinned package of one door's bound run, re-measured: dir, manifest doc."""
    ph = _phase(door)
    pkg = _load(ph["binding"])["package"]
    man = os.path.join(pkg["dir"], ph["manifest"])
    if not os.path.isfile(man) or INV.sha_file(man) != pkg["manifest_sha256"]:
        raise ValueError("the pinned package %s is not the bound one" % pkg["dir"])
    if INV.sha_file(os.path.join(pkg["dir"], ph["prefix_name"])) != pkg["prefix_sha256"]:
        raise ValueError("the pinned prefix is not the bound one")
    return {"package_dir": pkg["dir"], "manifest": _load(man),
            "manifest_sha256": pkg["manifest_sha256"]}


def _pinned_prompt(package_dir, task, door=None):
    """The prompt a CLOSED run received: the package's shipped prefix bytes
    plus the payload derived from the immutable bound evidence."""
    ph = _phase(door)
    return K._read(os.path.join(package_dir, ph["prefix_name"])) \
        + json.dumps(ph["payload"](task), indent=1)


def _pinned_script(base, task, attempt):
    """The launcher bytes a CLOSED run's state must carry: the script the
    receipt owner wrote into the run, whose hash the pinned manifest names."""
    return K._read(os.path.join(base, "scripts", "%s.attempt%d.js"
                                % (task["source_id"], attempt)))


def _closed_receipt_problems(base, rec, attempt, pinned, door=None):
    """The receipt of closed history must be exactly what the PINNED package
    derived; every prompt must be the pinned prefix plus the bound payload;
    every stored script must be the pinned launcher."""
    ph = _phase(door)
    man, bad = pinned["manifest"], []
    by_task = {r["source_id"]: r for r in man["tasks"]}
    tasks = _by_source(ph["door"])
    if attempt == 1:
        allowed, parent = list(man["call_order"]), None
    else:
        pfin = os.path.join(os.path.dirname(os.path.abspath(base)), K.FINALIZATION_NAME)
        if not os.path.isfile(pfin):
            return ["a child with no finalized parent is an orphan"]
        pdoc = K._load(pfin)
        allowed = list(pdoc.get("retry") or [])
        parent = collections.OrderedDict([("run_id", pdoc.get("run_id")),
                                          ("finalization_sha256", INV.sha_file(pfin))])
    want = collections.OrderedDict([
        ("run_id", os.path.basename(os.path.abspath(base))),
        ("door", ph["door"]), ("version", VERSION), ("attempt", attempt),
        ("allowed", allowed), ("parent", parent),
        ("transport", K._transport_block()),
        ("manifest_sha256", pinned["manifest_sha256"]),
        ("derived_from", man["derived_from"]),
        ("prompts", collections.OrderedDict(
            (sid, by_task[sid]["prompt_sha256"]) for sid in allowed))])
    for field in RECEIPT_IMMUTABLE:
        if rec.get(field) != want[field]:
            bad.append("receipt.%s is not the pinned package's" % field)
    if not isinstance(rec.get("states"), list):
        bad.append("receipt.states is not a list")
    if set(rec) != set(RECEIPT_IMMUTABLE) | {"states"}:
        bad.append("the receipt carries unexpected fields")
    for sid in allowed:
        if _sha(_pinned_prompt(pinned["package_dir"], tasks[sid], ph["door"])) != want["prompts"][sid]:
            bad.append("%s: the pinned prefix plus the bound payload is not the receipt's prompt" % sid)
        script = os.path.join(base, "scripts", "%s.attempt%d.js" % (sid, attempt))
        if not os.path.isfile(script) or INV.sha_file(script) != by_task[sid]["script_sha256"]:
            bad.append("%s: the stored launcher is not the pinned one" % sid)
    return bad


def proved_spend(run_dir, door=None):
    """READ-ONLY. The calls one door's FINALIZED bound run actually spent, re-proved:
    the binding identity (receipt, finalization, every raw/proved byte,
    canonical raw tree, pinned package), the receipt against the PINNED
    package, the finalization binding that receipt and closed clean and
    complete, every official state through run_evidence against the pinned
    prompt and launcher, every stored byte equal to the official text, every
    outcome RE-DERIVED through the locked reader, the allowed identities
    served once, the raw tree holding exactly the preserved files, the child
    owed by the outcomes owned by the binding. Any missing, foreign,
    unexpected or tampered byte refuses the WHOLE spend.
    -> [{run_dir, attempt, receipt_sha256, finalization_sha256, raw_tree,
         raw_files, calls}]"""
    ph = _phase(door)
    binding = _load(ph["binding"])
    if binding.get("schema") != BINDING_SCHEMA or \
            binding.get("run_dir") != os.path.abspath(run_dir):
        raise ValueError("%s is not the bound %s run %s"
                         % (run_dir, ph["door"], binding.get("run_dir")))
    bound = {a["attempt"]: a for a in binding["attempts"]}
    present = [1] + ([MAX_ATTEMPTS] if os.path.isdir(os.path.join(run_dir, "retry")) else [])
    if sorted(bound) != present:
        raise ValueError("%s carries attempts %s; the binding owns %s"
                         % (run_dir, present, sorted(bound)))
    pinned = _closed_pins(run_dir, ph["door"])
    tasks = _by_source(ph["door"])
    rows = []
    for attempt in sorted(bound):
        base = bound[attempt]["dir"]
        rec_path = os.path.join(base, K.RECEIPT_NAME)
        fin_path = os.path.join(base, K.FINALIZATION_NAME)
        for p in (rec_path, fin_path):
            if not os.path.isfile(p):
                raise ValueError("%s: missing %s" % (base, os.path.basename(p)))
        if _measured_attempt(base, attempt) != bound[attempt]:
            raise ValueError("%s: the receipt, finalization, raw tree or a raw "
                             "byte is not the bound identity" % base)
        rec, fin = _load(rec_path), _load(fin_path)
        bad = _closed_receipt_problems(base, rec, attempt, pinned, ph["door"])
        allowed = list(rec.get("allowed") or [])
        if rec.get("attempt") != attempt:
            bad.append("receipt attempt %r is not %d" % (rec.get("attempt"), attempt))
        for field, was, want in (
                ("attempt", fin.get("attempt"), attempt),
                ("door", fin.get("door"), ph["door"]),
                ("version", fin.get("version"), VERSION),
                ("run_id", fin.get("run_id"), rec.get("run_id")),
                ("receipt_sha256", fin.get("receipt_sha256"), INV.sha_file(rec_path)),
                ("manifest_sha256", fin.get("manifest_sha256"), rec.get("manifest_sha256")),
                ("derived_from", fin.get("derived_from"), rec.get("derived_from")),
                ("problems", list(fin.get("problems") or []), []),
                ("primary_complete", fin.get("primary_complete"), True)):
            if was != want:
                bad.append("the finalization's %s is not the derived value" % field)
        outcomes = [tuple(o) for o in (fin.get("outcomes") or [])]
        if [o[0] for o in outcomes] != allowed:
            bad.append("the finalization's outcomes are not the allowed calls in order")
        if any(o[1] not in _FINAL_OUTCOMES for o in outcomes):
            bad.append("a finalized outcome is not a complete one")
        led = fin.get("ledger") or {}
        if led.get("scheduled") != len(allowed) or \
                sum(v for k, v in led.items() if k != "scheduled") != len(allowed) \
                or led.get("unproved") or led.get("missing"):
            bad.append("the finalization's ledger is not the derived count")
        states = list(rec.get("states") or [])
        if len(set(states)) != len(states):
            bad.append("a state is recorded twice")
        if len(states) != len(allowed):
            bad.append("%d states for %d allowed calls" % (len(states), len(allowed)))
        proved, problems = run_evidence(
            base, rec, lambda t, _p=pinned, _d=ph["door"]: _pinned_prompt(_p["package_dir"], t, _d),
            lambda t, a, _b=base: _pinned_script(_b, t, a))
        bad += problems
        derived, expected_files = collections.OrderedDict(), []
        for state in states:
            run_id = os.path.splitext(os.path.basename(state))[0]
            try:
                label = K._state_label(json.loads(K._read(state)))
            except Exception as exc:                  # noqa: BLE001 - by design
                bad.append("%s: state unreadable (%s)" % (run_id, str(exc)[:60]))
                continue
            got = proved.get(label)
            if not got or got[0] not in ("proved", "transport_no_answer"):
                bad.append("%s: %s is not proved" % (run_id, label))
                continue
            if got[0] == "proved":
                text = got[2]
                raw = os.path.join(base, "raw", RT._raw_filename("%s.000" % run_id))
                proved_file = os.path.join(base, "raw", "%s.attempt%s.proved.json" % (label, attempt))
                for path in (raw, proved_file):
                    if K._stored_matches(path, text) is not True:
                        bad.append("%s is not the official text" % os.path.basename(path))
                expected_files += [os.path.basename(raw), os.path.basename(proved_file)]
                _obj, why = read_shard(text, tasks[label], ph["leads"](tasks[label]))
                derived[label] = "valid" if not why else "invalid_response"
            else:
                derived[label] = "transport_no_answer"
        if set(proved) != set(allowed):
            bad.append("the proved labels are not the allowed ones")
        if [(o[0], o[1]) for o in outcomes] != list(derived.items()):
            bad.append("a stored outcome is not the re-derived one")
        counted = collections.Counter(derived.values())
        if any(led.get(name) != counted.get(name, 0) for name in _FINAL_OUTCOMES):
            bad.append("the finalization's ledger is not the re-derived count")
        raw_dir = os.path.join(base, "raw")
        listing = sorted(os.listdir(raw_dir)) if os.path.isdir(raw_dir) else []
        if listing != sorted(expected_files):
            bad.append("the raw tree does not hold exactly the preserved files")
        if list(fin.get("harvested_raw") or []) != \
                [f for f in expected_files if f.endswith(RT._raw_filename(""))]:
            bad.append("the finalization's harvested list is not the preserved raw files")
        owed = [lab for lab, kind in derived.items() if kind in RETRYABLE] if attempt == 1 else []
        if list(fin.get("retry") or []) != owed:
            bad.append("the finalization's retry is not the derived one")
        if owed and MAX_ATTEMPTS not in bound:
            bad.append("the primary owes a child the binding does not own")
        if attempt == MAX_ATTEMPTS and fin.get("retry") != []:
            bad.append("a child names a successor; there is no third attempt")
        if bad:
            raise ValueError("%s: this run's spend cannot be counted: %s" % (base, bad[:3]))
        rows.append(collections.OrderedDict([
            ("run_dir", base), ("attempt", attempt),
            ("receipt_sha256", INV.sha_file(rec_path)),
            ("finalization_sha256", INV.sha_file(fin_path)),
            ("raw_tree", bound[attempt]["raw_tree"]["sha256"]),
            ("raw_files", bound[attempt]["raw_tree"]["files"]),
            ("calls", len(states))]))
    return rows


# --------------------------------------------------- the correction phase --
# Codex SEQ 1501 items 2-7 / SEQ 1505 items 2-3: the locked owner's
# decision-correction PATTERN through this one wrapper - the same rules first,
# the complete event, the affected rows, the exact prior settlement as an
# untrusted lead and the reviewer's findings LAST; the same reader,
# materializer and raw lifecycle. Each ROUND corrects the accepted key before
# it (the bound primary with every earlier round's bound overlay). The
# population is DERIVED, never listed: from the bound review receipt (round
# one) or from the open issues the accepted key still carries (round two);
# either way the receipt must carry each event's own open issues verbatim and
# may add reviewer findings that point at existing rules. No semantic string
# decides anything here.
def _review_population(shards, findings, order):
    """Round one (Codex SEQ 1501): every event whose bound review entry is nonempty."""
    del shards
    return [sid for sid in order if findings.get(sid)]


def _open_issue_population(shards, findings, order):
    """Round two (Codex SEQ 1505 item 2): exactly the events whose accepted
    shard still carries an open issue; the receipt must cover exactly them."""
    pop = [sid for sid in order if shards[sid]["open_issues"]]
    if [sid for sid in order if findings.get(sid)] != pop:
        raise ValueError("the review receipt does not cover exactly the events "
                         "with an open issue")
    return pop


def _round(door):
    """What one correction round genuinely owns, resolved from module globals
    at call time (so a forged global reaches every gate); nothing else
    differs between rounds."""
    return {
        CORR_DOOR: {
            "pkg_dir": CORR_PKG_DIR, "budget_receipt": CORR_BUDGET_RECEIPT,
            "review_receipt": REVIEW_RECEIPT, "binding": CORR_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME, "authority": "Codex SEQ 1501",
            "origin": "final_targeted_correction", "receipt_key": "primary_binding",
            "population": _review_population},
        CORR2_DOOR: {
            "pkg_dir": CORR2_PKG_DIR, "budget_receipt": CORR2_BUDGET_RECEIPT,
            "review_receipt": CORR2_REVIEW_RECEIPT, "binding": CORR2_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME + "-2", "authority": "Codex SEQ 1505",
            "origin": "final_targeted_correction_2", "receipt_key": "lead_binding",
            "population": _open_issue_population},
        CORR3_DOOR: {
            "pkg_dir": CORR3_PKG_DIR, "budget_receipt": CORR3_BUDGET_RECEIPT,
            "review_receipt": CORR3_REVIEW_RECEIPT, "binding": CORR3_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME + "-3", "authority": "Codex SEQ 1508",
            "origin": "final_targeted_correction_3", "receipt_key": "lead_binding",
            "population": _review_population}}[door]


def _lead_door(door):
    """The door whose bound run a round reviews: the round before it, or the primary."""
    earlier = CORRECTION_DOORS[:CORRECTION_DOORS.index(door)]
    return earlier[-1] if earlier else DOOR


@functools.lru_cache(maxsize=None)
def _bound_cached(door, binding_sha):
    """One door's bound shards and raw texts, proved once per operation: the
    binding identity through proved_spend, the parse through the shared
    accepted_shards over the pinned prefix. Keyed by the immutable binding."""
    del binding_sha
    run = _closed_run(door)
    if run is None:
        raise ValueError("no %s run is bound" % door)
    proved_spend(run, door)
    shards, raws, bad = accepted_shards(run)
    if bad:
        raise ValueError("the bound %s run does not re-prove: %s" % (door, bad[:2]))
    return shards, raws


def bound_shards(door):
    """Callers get COPIES; nothing they mutate reaches the cache."""
    shards, raws = _bound_cached(door, INV.sha_file(_phase(door)["binding"]))
    return (collections.OrderedDict((k, copy.deepcopy(v)) for k, v in shards.items()),
            collections.OrderedDict(raws))


def primary_shards():
    return bound_shards(DOOR)


def _lead(door):
    """What a round corrects: the accepted key before it - the bound primary
    with every earlier round's BOUND overlay. -> (shards, raws, origins)"""
    earlier = CORRECTION_DOORS[:CORRECTION_DOORS.index(door)]
    runs = [_closed_run(d) for d in earlier]
    if None in runs:
        raise ValueError("the %s run is not bound" % earlier[runs.index(None)])
    shards, raws, origins, bad = _successor(*runs)      # inside whatever operation is running
    if bad:
        raise ValueError("the accepted key before %s does not re-prove: %s" % (door, bad[:2]))
    return shards, raws, origins


def _review_receipt(door=CORR_DOOR):
    r, lead = _round(door), _lead_door(door)
    doc = _load(r["review_receipt"])
    if doc.get("schema") != REVIEW_SCHEMA:
        raise ValueError("the review receipt is not of this schema")
    binding = _phase(lead)["binding"]
    pb = doc.get(r["receipt_key"]) or {}
    if pb.get("binding_path") != binding or pb.get("binding_sha256") != INV.sha_file(binding) \
            or pb.get("run_dir") != _closed_run(lead):
        raise ValueError("the review receipt is not bound to the accepted %s run" % lead)
    return doc


def correction_events(door=CORR_DOOR):
    """THE population of one round, derived through the round's own rule, in
    primary order. The receipt must carry each event's own open issues
    verbatim and completely; a reviewer finding must be a nonempty text
    naming at least one existing rule."""
    rec = _review_receipt(door)
    shards, _raws, _origins = _lead(door)
    findings = rec.get("findings") or {}
    order = list(shards)
    for sid in findings:
        if sid not in order:
            raise ValueError("%s is not a primary event" % sid)
    for sid in order:
        entries = findings.get(sid) or []
        declared = [collections.OrderedDict([("what", f.get("what")), ("why", f.get("why"))])
                    for f in entries if f.get("kind") == "open_issue"]
        issues = [collections.OrderedDict([("what", x["what"]), ("why", x["why"])])
                  for x in shards[sid]["open_issues"]]
        if declared != issues:
            raise ValueError("%s: the review receipt does not carry the accepted "
                             "shard's open issues verbatim and completely" % sid)
        for f in entries:
            if f.get("kind") not in FINDING_KINDS:
                raise ValueError("%s: a finding is not of a lawful kind" % sid)
            if f.get("kind") == "reviewer_finding" and not (
                    isinstance(f.get("text"), str) and f["text"].strip()
                    and isinstance(f.get("rules"), list) and f["rules"]):
                raise ValueError("%s: a reviewer finding has no text or names no rule" % sid)
    return _round(door)["population"](shards, findings, order)


def correction_tasks(door=CORR_DOOR):
    by = {t["source_id"]: t for t in event_tasks()}
    return [collections.OrderedDict([
        ("task_id", "ftc-%03d" % n), ("event_index", by[sid]["event_index"]),
        ("source_id", sid), ("rows", list(by[sid]["rows"])),
        ("groups", collections.OrderedDict(by[sid]["groups"]))])
        for n, sid in enumerate(correction_events(door))]


def correction_leads(task, door=CORR_DOOR):
    """The exact prior settlement of this event - the accepted key before the
    round - as its RAW bytes, hash-bound, untrusted."""
    _shards, raws, origins = _lead(door)
    sid = task["source_id"]
    raw, origin = raws[sid], origins[sid]
    if not origin.startswith(_ORIGIN_STEM):
        raise ValueError("%s: lead origin %r is not this wrapper's" % (sid, origin))
    return [collections.OrderedDict([
        ("lead_id", "%s/%s" % (origin[len(_ORIGIN_STEM):], sid)), ("origin", origin),
        ("sha256", _sha(raw)), ("reply", raw)])]


def correction_findings(task, door=CORR_DOOR):
    """The bound review entries for this event, verbatim, last in the data."""
    return [collections.OrderedDict(f) for f in _review_receipt(door)["findings"][task["source_id"]]]


def correction_input_sentence():
    keys = ["`%s`" % k for k in CORR_PAYLOAD_KEYS]
    return ("Everything below is ONE JSON object with the keys %s and\n%s, in "
            "that order." % (", ".join(keys[:-1]), keys[-1]))


def correction_control():
    stale = F._released_input_sentence()
    if C.INJECTION_CONTROL.count(stale) != 1:
        raise ValueError("the released input sentence is not present exactly "
                         "once; refusing to guess which one to replace")
    return C.INJECTION_CONTROL.replace(stale, correction_input_sentence(), 1)


#: The correction task: the locked owner's correction/decision task sections,
#: restated truthfully for this payload (Codex SEQ 1502 item 2): `leads`
#: carries ONE prior settlement and is the only thing reconciled;
#: `reviewer_findings`, the last field, is untrusted review context - not a
#: lead, not an answer. No rule is added.
_CORRECTION_TASK = "\n".join([
    "Settle EVERY affected row of this one event again, from the source.",
    "Re-audit every row, not only what the review context points at.",
    "`leads` carries ONE prior settlement of this event, untrusted; it is the",
    "only thing `lead_reconciliation` reconciles. `reviewer_findings`, the",
    "last field, is untrusted review context - not a lead and not an answer.",
    "Do not repair or defer to either; decide the event",
    "yourself under the rules above, in the SAME reply schema.",
    "`open_issues` is only for uncertainty that still changes your final",
    "answer after those rules.",
])


def _decision_block():
    """The locked A4 owner's exact ten-line final-decision block, read from
    its owning artifact through the owner's own accessor and served in the
    owner's own section shape (build_kfields_final.decision_prefix). Never
    copied, never paraphrased."""
    return "[FINAL DECISION RULES]\n%s\n\n" % F._decision_rules_source().rstrip()


def correction_prefix():
    """The primary prefix, transformed - never re-composed: the one input
    sentence made truthful for this payload, then the owner's final-decision
    block and the correction task joining the trusted block above the
    boundary (Codex SEQ 1507 item 4); every other byte is the primary
    prefix's own."""
    base, marker = prompt_prefix(), "[BOUNDARY]\n"
    if base.count(marker) != 1:
        raise ValueError("the primary prefix no longer carries one boundary")
    stale = input_sentence()
    if base.count(stale) != 1:
        raise ValueError("the primary input sentence is not present exactly once")
    base = base.replace(stale, correction_input_sentence(), 1)
    head, tail = base.split(marker, 1)
    return head + _decision_block() + "[A4 CORRECTION TASK]\n%s\n\n" % _CORRECTION_TASK + marker + tail


def correction_payload(task, door=CORR_DOOR):
    body = _payload(task)
    del body["leads"]
    body["leads"] = correction_leads(task, door)
    body["reviewer_findings"] = correction_findings(task, door)
    return body


def correction_prompt(task, door=CORR_DOOR):
    return correction_prefix() + json.dumps(correction_payload(task, door), indent=1)


def render_correction_launcher(task, attempt=1, door=CORR_DOOR):
    """The primary launcher again, transformed. Transport bytes untouched."""
    lines = render_launcher(task, attempt).split("\n")
    F._swap(lines, "  name:", "  name: '%s'," % _round(door)["launcher_name"], "meta name")
    F._swap(lines, "  description:",
            "  description: 'K-fields A4 final targeted correction: one "
            "independent key owner re-settles every corrected row of one event "
            "under the reviewer findings',", "description")
    F._swap(lines, "const PROMPT = ", "const PROMPT = "
            + json.dumps(correction_prompt(task, door)), "PROMPT")
    return "\n".join(lines)


def _correction_derived_from(door=CORR_DOOR):
    d, r, lead = _derived_from(), _round(door), _lead_door(door)
    binding = _phase(lead)["binding"]
    pkg = _load(binding)["package"]
    d[r["receipt_key"]] = collections.OrderedDict([
        ("binding_path", binding), ("binding_sha256", INV.sha_file(binding)),
        ("run_dir", _closed_run(lead)), ("package_dir", pkg["dir"]),
        ("manifest_sha256", pkg["manifest_sha256"])])
    d["review_receipt"] = collections.OrderedDict([
        ("path", r["review_receipt"]), ("sha256", INV.sha_file(r["review_receipt"]))])
    rules = os.path.join(F._HERE, F.DECISION_RULES_NAME)
    d["decision_rules"] = collections.OrderedDict([("path", rules), ("sha256", INV.sha_file(rules))])
    return d


def _correction_manifest(door=CORR_DOOR):
    tasks = correction_tasks(door)
    if not tasks:
        raise ValueError("population refused: no event carries a finding")
    _shards, raws, origins = _lead(door)
    population = {t["source_id"] for t in tasks}
    rows, scripts = [], []
    for task in tasks:
        text = correction_prompt(task, door)
        script = render_correction_launcher(task, door=door)
        scripts.append(len(script.encode("utf-8")))
        rows.append(collections.OrderedDict([
            ("task_id", task["task_id"]), ("event_index", task["event_index"]),
            ("source_id", task["source_id"]), ("rows", list(task["rows"])),
            ("groups", [list(v) for v in task["groups"].values()]),
            ("leads", [collections.OrderedDict(
                [("lead_id", x["lead_id"]), ("origin", x["origin"]), ("sha256", x["sha256"])])
                for x in correction_leads(task, door)]),
            ("findings", [collections.OrderedDict(
                [("kind", f["kind"]), ("sha256", _sha(json.dumps(f, sort_keys=True)))])
                for f in correction_findings(task, door)]),
            ("payload_sha256", _sha(json.dumps(correction_payload(task, door), sort_keys=True))),
            ("prompt_sha256", _sha(text)),
            ("prompt_bytes", len(text.encode("utf-8"))),
            ("script_sha256", _sha(script)), ("script_bytes", scripts[-1])]))
    prefix = correction_prefix()
    return collections.OrderedDict([
        ("door", door), ("version", VERSION), ("authority", _round(door)["authority"]),
        ("step", "live Step 1 A4 - the correction of the successor final "
                 "adjudication under the reviewer findings"),
        ("contract_suffix", SUFFIX),
        ("derived_from", _correction_derived_from(door)),
        ("role_sha256", _sha(F._ROLE)),
        ("semantic_rules_sha256", _sha(C.role_rules("drafter", SUFFIX))),
        ("output_card_sha256", _sha(C.one_item_output_section().rstrip())),
        ("gate_text_sha256", _sha(BIR.gate_text())),
        ("crosswalk_text_sha256", _sha(BIR.crosswalk_text())),
        ("task_section_sha256", _sha(F._task_section())),
        ("output_section_sha256", _sha(F._output_section())),
        ("correction_task_sha256", _sha(_CORRECTION_TASK)),
        ("decision_rules_sha256", _sha(F._decision_rules_source())),
        ("boundary_sha256", _sha(HR._boundary_at(SUFFIX))),
        ("injection_control_sha256", _sha(correction_control())),
        ("prefix_sha256", _sha(prefix)),
        ("prefix_bytes", len(prefix.encode("utf-8"))),
        ("transport", K._transport_block()),
        ("budget", _budget(len(rows), _round(door)["budget_receipt"])),
        ("counts", collections.OrderedDict([
            ("tasks", len(rows)),
            ("targets", sum(len(r["rows"]) for r in rows)),
            ("groups", sum(len(r["groups"]) for r in rows)),
            ("leads", sum(len(r["leads"]) for r in rows)),
            ("findings", sum(len(r["findings"]) for r in rows)),
            ("preserved_events", sum(1 for t in event_tasks() if t["source_id"] not in population)),
            ("primary_calls", len(rows))])),
        ("capacity", collections.OrderedDict([
            ("unit", "UTF-8 bytes of the serialized launcher script the "
                     "runtime actually runs; never summed"),
            ("transport_limit_bytes", K.TRANSPORT_LIMIT),
            ("largest_script_bytes", max(scripts)),
            ("smallest_script_bytes", min(scripts)),
            ("largest_prompt_bytes", max(r["prompt_bytes"] for r in rows)),
            ("at_or_over_transport_limit",
             sorted(r["source_id"] for r, n in zip(rows, scripts)
                    if n >= K.TRANSPORT_LIMIT))])),
        ("preserved", [collections.OrderedDict([
            ("source_id", t["source_id"]), ("origin", origins[t["source_id"]]),
            ("raw_sha256", _sha(raws[t["source_id"]]))])
            for t in event_tasks() if t["source_id"] not in population]),
        ("tasks", rows),
        ("call_order", [r["source_id"] for r in rows])])


def build_correction(out_dir, door=CORR_DOOR):
    return build(out_dir, door)


def correction_package_problems(pkg_dir=None, door=CORR_DOOR):
    return package_problems(pkg_dir, door)


def correction_preflight(pkg_dir=None, door=CORR_DOOR):
    return preflight(pkg_dir, door)


def _overlay(door, run):
    """One round's accepted shards: through its binding when the run is the
    bound one, else re-proved directly. -> (shards, raws, problems)"""
    if os.path.abspath(run) == _closed_run(door):
        shards, raws = bound_shards(door)
        return shards, raws, []
    return accepted_shards(run)


def _successor(*runs):
    """The accepted key after the given correction runs, one per round in
    door order: the bound primary with each round's accepted replacements
    over exactly that round's derived population. A later round without the
    earlier one is refused. -> (shards, raws, origins, problems), primary
    order throughout."""
    if len(runs) > len(CORRECTION_DOORS):
        raise ValueError("%d correction runs for %d rounds" % (len(runs), len(CORRECTION_DOORS)))
    shards, raws = primary_shards()
    origins = collections.OrderedDict((s, CORR_LEAD_ORIGIN) for s in shards)
    bad = []
    for n, (door, run) in enumerate(zip(CORRECTION_DOORS, runs)):
        if run is None:
            if any(r is not None for r in runs[n + 1:]):
                raise ValueError("a later round is given without the %s run" % door)
            break
        wanted = set(correction_events(door))
        repl, rraws, rbad = _overlay(door, run)
        bad += rbad
        for sid, shard in repl.items():
            if sid not in wanted:
                bad.append("%s: a correction outside the derived population" % sid)
                continue
            shards[sid], raws[sid], origins[sid] = shard, rraws[sid], _round(door)["origin"]
        missing = sorted(wanted - set(repl))
        if missing:
            bad.append("%d affected events have no accepted correction: %s" % (len(missing), missing[:3]))
    return shards, raws, origins, bad


successor_shards = _operation(_successor)        # THE public door: proved once per operation


def _bound_proved(door, run):
    """{event: {sha256 of every proved text the binding holds}} when `run` is
    the door's bound run; None for any other run (nothing bound to compare)."""
    if run is None or os.path.abspath(run) != _closed_run(door):
        return None
    out = {}
    for attempt in _load(_phase(door)["binding"])["attempts"]:
        for name, sha in attempt["raw_files"].items():
            if name.endswith(".proved.json"):
                out.setdefault(name.split(".attempt")[0], set()).add(sha)
    return out


@_operation
def preservation_problems(*runs):
    """Nothing unaffected moves: every event not replaced by a later round
    keeps the exact shard of the last BOUND round that settled it (the
    primary's, or an earlier correction's, byte for byte), the bound primary
    itself re-proves, and the locked A4 history still holds (the ledger's own
    locked rows)."""
    bad = []
    try:
        proved_spend(_closed_run())
    except ValueError as exc:
        return ["the bound primary does not re-prove: %s" % exc]
    _shards, raws, origins, sbad = successor_shards(*runs)
    bad += sbad
    settled = collections.OrderedDict([(DOOR, _closed_run())])
    for door, run in zip(CORRECTION_DOORS, runs):
        if run is None:
            break
        settled[door] = run
    populations = {d: set(correction_events(d)) for d in settled if d != DOOR}
    for sid in _shards:
        door = DOOR
        for d in populations:
            if sid in populations[d]:
                door = d
        want = CORR_LEAD_ORIGIN if door == DOOR else _round(door)["origin"]
        if origins.get(sid) != want:
            bad.append("%s: the shard is not the %s's" % (sid, want))
            continue
        bound = _bound_proved(door, settled[door])
        if bound is not None and _sha(raws[sid]) not in bound.get(sid, ()):
            bad.append("%s: a preserved event's shard is not the bound %s's" % (sid, want))
    import a6_launch_freeze as A6
    try:
        A6._locked_rows()
    except ValueError as exc:
        bad.append("the locked A4 history no longer holds: %s" % exc)
    return bad


# ----------------------------------- the full 196-row successor composition --
# Codex SEQ 1502 item 1: the eventual key is the SIGNED baseline (36 events /
# 196 rows through the locked owner and the bound history) with exactly the
# eleven targeted results overlaid by packet id; every other row, the full
# event order and the full baseline groups are preserved; F.materialize is
# the sole materializer over the corrected full inventory. A composed event is
# not one model reply: its provenance binds the base and targeted component
# hashes and no synthesized JSON is ever presented as raw model evidence.
def _baseline():
    """The signed V6 key through the locked owner. -> (bound, shards, raws, origins)"""
    import a6_launch_freeze as A6
    b = A6.bound()
    shards, raws, origins, bad = F.v6_shards(b)
    if bad:
        raise ValueError("the signed baseline does not re-prove: %s" % bad[:2])
    return b, shards, raws, origins


def _corrected_inventory():
    """The corrected FULL inventory in the locked owner's own shape."""
    records = T._load(T.CORRECTED_INVENTORY)["records"]
    return tuple(("%s#%03d" % (r["source_id"], n), r) for n, r in enumerate(records))


@_operation
def full_successor(*runs):
    """-> (shards, raws, provenance, problems) over the full 36 events in the
    signed order. Untouched events keep their base shard and raw text; an
    affected event gets exactly its changed packets' rows, outcomes and
    review rows (re-indexed to the full event positions) from the targeted
    result, keeps every other row, and carries raw None with the two
    component hashes in its provenance."""
    b, base, braws, borigins = _baseline()
    targeted, traws, torigins, problems = successor_shards(*runs)
    diff = set(T.targets())
    full_tasks = {t["source_id"]: t for t in F.event_tasks(b.evidence)}
    partial = _by_source(DOOR)
    shards, raws = collections.OrderedDict(), collections.OrderedDict()
    events = collections.OrderedDict()
    for sid in [t["source_id"] for t in F.event_tasks(b.evidence)]:
        fshard = copy.deepcopy(base[sid])
        if sid not in targeted:
            shards[sid], raws[sid] = fshard, braws[sid]
            events[sid] = collections.OrderedDict([
                ("composed", False), ("origin", borigins[sid]),
                ("raw_sha256", _sha(braws[sid]))])
            continue
        task, tshard = full_tasks[sid], targeted[sid]
        replaced = [p for p in task["rows"] if p in diff]
        for members in task["groups"].values():
            if set(members) & diff:
                problems.append("%s: a changed packet sits in a full locator group; "
                                "composition refuses" % sid)
        if set(tshard["rows"]) != set(replaced) or set(partial[sid]["rows"]) != set(replaced):
            problems.append("%s: the targeted result does not settle exactly the "
                            "event's changed packets" % sid)
            shards[sid], raws[sid] = fshard, None
            events[sid] = collections.OrderedDict([("composed", True), ("replaced", [])])
            continue
        index = {p: n + 1 for n, p in enumerate(task["rows"])}
        tindex = {n + 1: p for n, p in enumerate(partial[sid]["rows"])}
        review = [r for r in fshard["review"]
                  if task["rows"][r["row_index"] - 1] not in diff]
        for r in tshard["review"]:
            pid = tindex.get(r["row_index"])
            if pid is None:
                problems.append("%s: a targeted review row names no targeted row" % sid)
                continue
            nr = collections.OrderedDict(r)
            nr["row_index"] = index[pid]
            review.append(nr)
        review.sort(key=lambda r: (r["row_index"], r["fact_index"]))
        for pid in replaced:
            fshard["rows"][pid] = copy.deepcopy(tshard["rows"][pid])
            fshard["outcomes"][pid] = tshard["outcomes"][pid]
        fshard["review"] = review
        fshard["open_issues"] = list(fshard["open_issues"]) + list(tshard["open_issues"])
        fshard["lead_reconciliation"] = list(fshard["lead_reconciliation"]) \
            + list(tshard["lead_reconciliation"])
        shards[sid], raws[sid] = fshard, None
        events[sid] = collections.OrderedDict([
            ("composed", True), ("base_origin", borigins[sid]),
            ("base_raw_sha256", _sha(braws[sid])),
            ("targeted_origin", torigins[sid]),
            ("targeted_raw_sha256", _sha(traws[sid])),
            ("replaced", replaced)])
    provenance = collections.OrderedDict([
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("corrected_inventory_sha256", INV.sha_file(T.CORRECTED_INVENTORY)),
        ("events", events)])
    return shards, raws, provenance, problems


@_operation
def full_counts(*runs):
    shards, _raws, prov, _problems = full_successor(*runs)
    b = _baseline()[0]
    tasks = {t["source_id"]: t for t in F.event_tasks(b.evidence)}
    composed = [s for s in shards if prov["events"][s]["composed"]]
    rows = [p for s in shards for p in shards[s]["rows"]]
    replaced = sum(len(prov["events"][s].get("replaced", [])) for s in composed)
    return collections.OrderedDict([
        ("events", len(shards)), ("rows", len(rows)), ("unique_rows", len(set(rows))),
        ("replaced", replaced), ("preserved", len(rows) - replaced),
        ("untouched_events", len(shards) - len(composed)),
        ("untouched_rows", sum(len(tasks[s]["rows"]) for s in shards if s not in composed)),
        ("affected_events", len(composed)),
        ("affected_unchanged_rows", sum(len(tasks[s]["rows"]) for s in composed) - replaced)])


@_operation
def full_preservation_problems(*runs):
    """Nothing unaffected moves in the 196-row key: exactly the corrected
    diff is replaced, every other row equals the signed baseline, every
    untouched shard is byte-preserved, every composed event's component
    hashes are live, every review index is a full event position, no changed
    packet sits in a group, and the bound history still holds."""
    bad = []
    try:
        b, base, braws, _o = _baseline()
        shards, raws, prov, problems = full_successor(*runs)
        targeted, traws, _to, _tb = successor_shards(*runs)
    except ValueError as exc:
        return ["the successor cannot be composed: %s" % exc]
    bad += problems
    diff = set(T.targets())
    tasks = {t["source_id"]: t for t in F.event_tasks(b.evidence)}
    if list(shards) != list(base) or len(shards) != len(tasks):
        bad.append("the composed key is not the signed baseline's event set in order")
    rows = [p for s in shards for p in shards[s]["rows"]]
    if len(rows) != len(set(rows)) or set(rows) != {p for t in tasks.values() for p in t["rows"]}:
        bad.append("a row is missing or duplicated")
    replaced = {p for s in shards if prov["events"][s]["composed"]
                for p in prov["events"][s].get("replaced", [])}
    if replaced != diff:
        bad.append("the replacement set is not the corrected diff")
    if prov["corrected_inventory_sha256"] != INV.sha_file(T.CORRECTED_INVENTORY):
        bad.append("the provenance is not bound to the corrected inventory")
    for sid in shards:
        ev, task = prov["events"][sid], tasks[sid]
        for members in task["groups"].values():
            if set(members) & diff:
                bad.append("%s: a changed packet sits in a locator group" % sid)
        if shards[sid]["groups"] != base[sid]["groups"]:
            bad.append("%s: the full baseline groups are not preserved" % sid)
        for pid in task["rows"]:
            if pid in diff:
                continue
            if shards[sid]["rows"].get(pid) != base[sid]["rows"].get(pid) or \
                    shards[sid]["outcomes"].get(pid) != base[sid]["outcomes"].get(pid):
                bad.append("%s: an unchanged row moved" % pid)
        for r in shards[sid]["review"]:
            if not 1 <= r["row_index"] <= len(task["rows"]):
                bad.append("%s: a review row index is not a full event position" % sid)
        if not ev["composed"]:
            if raws[sid] != braws[sid] or shards[sid] != base[sid] or ev["raw_sha256"] != _sha(braws[sid]):
                bad.append("%s: an untouched shard is not byte-preserved" % sid)
            continue
        if raws[sid] is not None:
            bad.append("%s: a composed event presents synthesized text as raw evidence" % sid)
        if ev.get("base_raw_sha256") != _sha(braws[sid]) or \
                ev.get("targeted_raw_sha256") != _sha(traws.get(sid, "")):
            bad.append("%s: a component hash is not the live one" % sid)
        want = sorted([r for r in base[sid]["review"] if task["rows"][r["row_index"] - 1] not in diff]
                      + [dict(x, row_index=task["rows"].index(_by_source(DOOR)[sid]["rows"][x["row_index"] - 1]) + 1)
                         for x in targeted[sid]["review"] if 1 <= x["row_index"] <= len(_by_source(DOOR)[sid]["rows"])],
                      key=lambda r: (r["row_index"], r["fact_index"]))
        if [dict(r) for r in shards[sid]["review"]] != want:
            bad.append("%s: the review rows are not the base rows plus the remapped targeted rows" % sid)
        for pid in ev["replaced"]:
            if shards[sid]["rows"][pid] != targeted[sid]["rows"].get(pid):
                bad.append("%s: a replaced row is not the targeted result" % pid)
    bad += preservation_problems(*runs)
    return bad


@_operation
def full_materialize(*runs):
    """THE LOCKED OWNER'S MATERIALIZER over the composed 196-row key and the
    corrected full inventory, supplied to F._inventory for one serial call
    and restored in try/finally; then the owner's own same-event-duplicate
    and gold-door checks. -> (key, sidecar, problems)"""
    b, _base, _braws, _o = _baseline()
    shards, _raws, _prov, problems = full_successor(*runs)
    inventory = _corrected_inventory()
    real_inventory = F._inventory
    F._inventory = lambda: inventory
    try:
        key, sidecar, more = F.materialize(b.evidence, shards)
    finally:
        F._inventory = real_inventory
    problems = list(problems) + list(more)
    for sid, n in F.same_event_duplicates(key):
        problems.append("%s: fact %d repeats an earlier fact of the same event "
                        "exactly; the adjudicator must reconcile it once" % (sid, n))
    problems += ["gold door: %s" % e for e in F.key_problems(key)]
    return key, sidecar, problems
