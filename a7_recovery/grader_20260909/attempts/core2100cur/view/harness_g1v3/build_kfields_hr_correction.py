"""Codex SEQ 1375 — the four-call group-shape correction packet. BUILD ONLY.

11 of the 21 group attempts put a single sparse fact row directly under
`members[].settled`, where the frozen reader requires the complete four-field
item reply. Three retries recovered, four did not. Those four are this packet's
whole denominator.

THIS FILE OWNS EXACTLY TWO THINGS: the derived denominator, and one structural
sentence in the group wrapper. Everything else - the tasks, the source, the
menu, the located items, the semantic rules, the boundary, the reply validator,
the official proof, the raw capture, the accounting and the launcher shape - is
imported from the released A4 hard-review builder and used unchanged. The
reader is NOT widened: the four old replies stay failed evidence.

The prefix is not re-assembled here. It is the released builder's own group
prefix with its own output block spliced out and the corrected one spliced in,
so every byte outside that block is identical by construction rather than by
inspection.
"""
import collections
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_hard_review as HR                           # noqa: E402

K = HR.K
INV = HR.INV

DOOR = "a4_hard_review_group_shape_correction"
MANIFEST_NAME = "correction.manifest.json"
PREFIX_NAME = "prompt_prefix_group.txt"

#: Codex SEQ 1375 binds this packet to those two exact finalizations. They are
#: his hashes, quoted with their authority, and a mismatch refuses the build.
PARENT_PRIMARY_SHA = ("92e4a63c7e907656f6dbf754d5edeba3174a453578806897b26a5"
                      "cb46684efad")
PARENT_CHILD_SHA = ("8e8ce1c7907396c836e3baee034e0b884cea675a1647bc98a266e65"
                    "6fab61dbd")

#: The one retryable class, named once. Only a schema-invalid new answer may
#: earn the packet's single identical-prompt retry.
RETRYABLE = HR.RETRYABLE
MAX_ATTEMPTS = HR.MAX_ATTEMPTS
BLINDS = HR.BLINDS
GLOBAL_CEILING = HR.GLOBAL_CEILING


# ------------------------------------------------------- the denominator ----
def correction_labels(run_dir, evidence_dir):
    """THE four. Derived from the attempt-2 invalid rows, never hand-listed.

    Bound to both frozen finalizations by hash: a different parent, a different
    outcome set, a different count or a different order all refuse here rather
    than quietly reviewing the wrong calls.
    """
    prim = os.path.join(run_dir, HR.FINALIZATION_NAME)
    kid = os.path.join(run_dir, "retry", HR.FINALIZATION_NAME)
    for path, want, name in ((prim, PARENT_PRIMARY_SHA, "primary"),
                             (kid, PARENT_CHILD_SHA, "child")):
        if not os.path.isfile(path):
            raise ValueError("the %s finalization is missing" % name)
        if INV.sha_file(path) != want:
            raise ValueError("the %s finalization is not the bound one" % name)

    doc = K._load(kid)
    if doc.get("attempt") != MAX_ATTEMPTS:
        raise ValueError("the bound child is not attempt %d" % MAX_ATTEMPTS)
    if doc.get("retry"):
        raise ValueError("the bound child still names a retry set")
    labels = [lab for lab, outcome, _why in doc["outcomes"]
              if outcome == "invalid_response"]

    canon = HR.canonical_calls(evidence_dir)
    ordered = [lab for lab in canon if lab in set(labels)]
    if sorted(labels) != sorted(ordered) or labels != ordered:
        raise ValueError("the invalid rows are not in canonical order")
    by = HR._by_label(evidence_dir)
    for lab in labels:
        if lab not in by:
            raise ValueError("%s is not a scheduled A4 call" % lab)
        if by[lab][0]["kind"] != "group":
            raise ValueError("%s is not a group call" % lab)
    return labels


# -------------------------------------------------------------- the fix -----
def group_output():
    """The released wrapper with ONE structural sentence corrected.

    Only the `settled` description moves. It now names the four item-reply keys
    mechanically and says `facts` is the array that holds the sparse fact rows,
    which is exactly the shape 11 of 21 group attempts got wrong. No example,
    no semantic rule, no threshold and no new key is added.
    """
    old = HR._output("group")
    was = "\n".join([
        "    `settled` is the reply the [OUTPUT] section above defines for",
        "    that item, in its sparse shape."])
    now = "\n".join([
        "    `settled` is the reply the [OUTPUT] section above defines for",
        "    that item: ONE JSON object whose keys are EXACTLY these four,",
        "    with no others: %s."
        % ", ".join("`%s`" % k for k in HR.ITEM_REPLY_KEYS),
        "    `facts` is the ARRAY that holds the sparse fact rows.",
        "    All four keys are required, including any that are empty."])
    if old.count(was) != 1:
        raise ValueError("the released group wrapper no longer carries the "
                         "sentence this correction replaces")
    return old.replace(was, now, 1)


def prompt_prefix():
    """The released group prefix, with only the corrected block spliced in."""
    base = HR.prompt_prefix("group")
    old = HR._output("group")
    if base.count(old) != 1:
        raise ValueError("the released prefix no longer embeds its own group "
                         "output block exactly once")
    return base.replace(old, group_output(), 1)


def blind_prompt(task):
    """Corrected instructions, the live boundary, then the UNCHANGED data."""
    if task["kind"] != "group":
        raise ValueError("this correction reviews group tasks only")
    return prompt_prefix() + json.dumps(HR.payload(task), indent=1)


def render_launcher(task, blind, attempt=1):
    """The RELEASED launcher, with only its one PROMPT line transformed.

    Codex SEQ 1376 item 1: writing the launcher body out again here was a copy,
    however faithful, and contradicted this file's own single-owner claim. HR
    owns every other byte - the meta, the agent options, the returned object,
    and the blind/attempt bounds it already enforces.
    """
    base = HR.render_launcher(task, blind, attempt)
    was = "const PROMPT = " + json.dumps(HR.blind_prompt(task))
    now = "const PROMPT = " + json.dumps(blind_prompt(task))
    if base.count(was) != 1:
        raise ValueError("the released launcher no longer carries its prompt "
                         "line exactly once")
    return base.replace(was, now, 1)


def read_reply(text, task):
    """THE UNCHANGED READER. Named here only so no caller reaches for another."""
    return HR.read_reply(text, task)


# ----------------------------------------------------------- the package ----
def _ledger_before(run_dir, evidence_dir):
    """MEASURED: the A4 baseline plus what BOTH hard-review attempts spent."""
    spent = 0
    for base in (run_dir, os.path.join(run_dir, "retry")):
        fin = os.path.join(base, HR.FINALIZATION_NAME)
        spent += K._load(fin)["ledger"]["scheduled"]
    return HR._ledger_before(evidence_dir) + spent


def manifest(run_dir, evidence_dir, pkg_dir):
    """Everything this correction would depend on, pinned. Writes nothing."""
    labels = correction_labels(run_dir, evidence_dir)
    by = HR._by_label(evidence_dir)
    rows, scripts = [], []
    for lab in labels:
        task, blind = by[lab]
        text = blind_prompt(task)
        script = render_launcher(task, blind)
        scripts.append(len(script.encode("utf-8")))
        rows.append(collections.OrderedDict([
            ("label", lab), ("task_id", task["task_id"]), ("blind", blind),
            ("members", list(task["members"])),
            ("payload_sha256", K._sha(json.dumps(HR.payload(task),
                                                 sort_keys=True))),
            ("prompt_sha256", K._sha(text)),
            ("prompt_bytes", len(text.encode("utf-8"))),
            ("script_sha256", K._sha(script)),
            ("script_bytes", len(script.encode("utf-8")))]))

    before = _ledger_before(run_dir, evidence_dir)
    primaries = len(rows)
    return collections.OrderedDict([
        ("door", DOOR),
        ("authority", "Codex SEQ 1375"),
        ("corrects", "the group-shape class in the A4 hard review"),
        ("parent", collections.OrderedDict([
            ("run_id", os.path.basename(os.path.abspath(run_dir))),
            ("primary_finalization_sha256", PARENT_PRIMARY_SHA),
            ("child_finalization_sha256", PARENT_CHILD_SHA)])),
        ("derived_from", HR._derived_from(evidence_dir)),
        ("released_package_manifest_sha256", INV.sha_file(
            os.path.join(pkg_dir, HR.MANIFEST_NAME))),
        ("released_builder_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_hard_review.py"))),
        ("released_group_prefix_sha256", K._sha(HR.prompt_prefix("group"))),
        ("corrected_group_prefix_sha256", K._sha(prompt_prefix())),
        ("item_reply_keys", list(HR.ITEM_REPLY_KEYS)),
        ("transport", K._transport_block()),
        ("budget", collections.OrderedDict([
            ("before", before), ("primaries", primaries),
            ("after_primaries", before + primaries),
            ("max_attempts_per_call", MAX_ATTEMPTS),
            ("worst_case_total", primaries * MAX_ATTEMPTS),
            ("worst_case_after", before + primaries * MAX_ATTEMPTS),
            ("global_ceiling", GLOBAL_CEILING)])),
        ("counts", collections.OrderedDict([
            ("calls", primaries),
            ("tasks", len(set(r["task_id"] for r in rows))),
            ("reviewed_packets", len(set(k for r in rows
                                         for k in r["members"])))])),
        ("capacity", collections.OrderedDict([
            ("unit", "UTF-8 bytes of the serialized launcher script the "
                     "runtime actually runs; never summed"),
            ("transport_limit_bytes", K.TRANSPORT_LIMIT),
            ("largest_script_bytes", max(scripts)),
            ("smallest_script_bytes", min(scripts)),
            ("largest_prompt_bytes", max(r["prompt_bytes"] for r in rows)),
            ("at_or_over_transport_limit",
             sorted(r["label"] for r in rows
                    if r["script_bytes"] >= K.TRANSPORT_LIMIT))])),
        ("calls", rows),
        ("call_order", [r["label"] for r in rows])])


def build(out_dir, run_dir, evidence_dir, pkg_dir):
    """Write the frozen correction packet. Launches nothing."""
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    doc = manifest(run_dir, evidence_dir, pkg_dir)
    HR._atomic(os.path.join(out_dir, MANIFEST_NAME), json.dumps(doc, indent=1))
    HR._atomic(os.path.join(out_dir, PREFIX_NAME), prompt_prefix())
    return doc


def package_problems(out_dir, run_dir, evidence_dir, pkg_dir):
    """Re-derive from the live owners and compare. -> [problems]"""
    path = os.path.join(out_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return ["no correction manifest at %s" % out_dir]
    pinned = K._load(path)
    bad = []
    try:
        want = manifest(run_dir, evidence_dir, pkg_dir)
    except ValueError as exc:                         # noqa: BLE001 - by design
        return ["the correction no longer derives: %s" % exc]
    if K._sha(json.dumps(pinned, sort_keys=True)) \
            != K._sha(json.dumps(want, sort_keys=True)):
        for field in ("door", "parent", "derived_from", "transport", "budget",
                      "counts", "capacity", "call_order", "item_reply_keys",
                      "released_package_manifest_sha256",
                      "released_builder_sha256",
                      "released_group_prefix_sha256",
                      "corrected_group_prefix_sha256"):
            if pinned.get(field) != want[field]:
                bad.append("the pinned %s is not the live one" % field)
        pin = {r["label"]: r for r in pinned.get("calls") or []}
        wnt = {r["label"]: r for r in want["calls"]}
        for lab in sorted(set(pin) | set(wnt)):
            if lab not in pin:
                bad.append("%s is missing from the packet" % lab)
            elif lab not in wnt:
                bad.append("%s is in the packet but does not derive" % lab)
            elif pin[lab] != wnt[lab]:
                bad.append("%s is not the live call" % lab)
        if [r["label"] for r in pinned.get("calls") or []] \
                != [r["label"] for r in want["calls"]]:
            bad.append("the packaged calls are out of canonical order")
        if not bad:
            bad.append("the packet differs from the live derivation")
    shipped = os.path.join(out_dir, PREFIX_NAME)
    if not os.path.isfile(shipped) or K._read(shipped) != prompt_prefix():
        bad.append("the shipped corrected prefix is not the live one")
    return bad


def prompt_problems(run_dir, evidence_dir):
    """Only the one block moved, and the corrected shape is actually named."""
    bad, boundary = [], HR._boundary()
    released = HR.prompt_prefix("group")
    corrected = prompt_prefix()
    cut_r, cut_c = released.find(boundary), corrected.find(boundary)
    if cut_r < 0 or cut_c < 0:
        return ["the live boundary is missing from a prefix"]
    if released[cut_r:] != corrected[cut_c:]:
        bad.append("something below the boundary changed")
    if released[:cut_r].replace(HR._output("group"), group_output(), 1) \
            != corrected[:cut_c]:
        bad.append("more than the group output block changed above the "
                   "boundary")
    by = HR._by_label(evidence_dir)
    for lab in correction_labels(run_dir, evidence_dir):
        task, _blind = by[lab]
        text = blind_prompt(task)
        if not text.startswith(corrected):
            bad.append("%s: the prompt is not the corrected prefix" % lab)
        if json.dumps(HR.payload(task), indent=1) != text[len(corrected):]:
            bad.append("%s: the untrusted payload is not the released one"
                       % lab)
        for key in HR.ITEM_REPLY_KEYS:
            if ("`%s`" % key) not in text[:text.find(boundary)]:
                bad.append("%s: the corrected shape does not name %s"
                           % (lab, key))
    return bad


def preflight(out_dir, run_dir, evidence_dir, pkg_dir):
    """The one gate before any correction call is ever made."""
    problems = list(package_problems(out_dir, run_dir, evidence_dir, pkg_dir))
    problems += prompt_problems(run_dir, evidence_dir)
    path = os.path.join(out_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return {"ok": False, "problems": problems, "manifest": None}
    doc = K._load(path)
    if doc["capacity"]["at_or_over_transport_limit"]:
        problems.append("a launcher script is at or over the transport limit")
    if doc["capacity"]["transport_limit_bytes"] != K.TRANSPORT_LIMIT:
        problems.append("the pinned transport limit is not the live one")
    order = doc["call_order"]
    if len(set(order)) != len(order):
        problems.append("the same call is scheduled twice")
    if order != correction_labels(run_dir, evidence_dir):
        problems.append("the pinned call order is not the derived one")
    if doc["budget"]["worst_case_after"] > GLOBAL_CEILING:
        problems.append("the worst case would break the global ceiling %d"
                        % GLOBAL_CEILING)
    return {"ok": not problems, "problems": problems, "manifest": doc}


# --------------------------------------------------- the sibling run half ---
# Codex SEQ 1376 item 2. This half owns THREE things and nothing else: the
# corrected receipt identity, the derived four-label denominator, and the
# corrected prompt/launcher hashes. Every check that is not "which prompt" is
# delegated: K._official_proof for the model, effort, tool, transcript and
# continuation proof; AUD._official_location for where a state may live;
# K.direct_result for the returned object; HR.record_state for appending one
# unique state; HR.read_reply for meaning; HR._atomic for every write.

Bound = collections.namedtuple("Bound", "packet run evidence released")

RECEIPT_IMMUTABLE = ("run_id", "door", "attempt", "allowed", "parent",
                     "transport", "manifest_sha256", "correction_of",
                     "prompts")
RESULT_FIELDS = HR.RESULT_FIELDS
NO_ANSWER = HR.NO_ANSWER


def expected_receipt(out_dir, bound, attempt, labels, parent=None):
    """THE typed expectation, carrying the CORRECTED prompt hashes."""
    by = HR._by_label(bound.evidence)
    man = os.path.join(bound.packet, MANIFEST_NAME)
    return collections.OrderedDict([
        ("run_id", os.path.basename(os.path.abspath(out_dir))),
        ("door", DOOR), ("attempt", attempt),
        ("allowed", list(labels)),
        ("parent", parent),
        ("transport", K._transport_block()),
        ("manifest_sha256", INV.sha_file(man) if os.path.isfile(man) else None),
        ("correction_of", collections.OrderedDict([
            ("primary_finalization_sha256", PARENT_PRIMARY_SHA),
            ("child_finalization_sha256", PARENT_CHILD_SHA)])),
        ("prompts", collections.OrderedDict(
            (lab, K._sha(blind_prompt(by[lab][0]))) for lab in labels)),
        ("states", [])])


def _write_receipt(out_dir, bound, attempt, labels, parent=None):
    receipt = expected_receipt(out_dir, bound, attempt, labels, parent)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    HR._atomic(os.path.join(out_dir, HR.RECEIPT_NAME),
               json.dumps(receipt, indent=1))
    return receipt


def _expected_for(out_dir, bound, receipt):
    """What THIS run's receipt must be. Attempt 1 is always the derived four."""
    attempt = receipt.get("attempt")
    if attempt == 1:
        return expected_receipt(out_dir, bound, 1,
                                correction_labels(bound.run, bound.evidence),
                                None), []
    if attempt != MAX_ATTEMPTS:
        return None, ["attempt %r is outside 1..%d" % (attempt, MAX_ATTEMPTS)]
    pdir = os.path.dirname(os.path.abspath(out_dir))
    pfin = os.path.join(pdir, HR.FINALIZATION_NAME)
    if not os.path.isfile(pfin):
        return None, ["a child with no finalized parent is an orphan"]
    doc = K._load(pfin)
    parent = collections.OrderedDict([
        ("run_id", doc.get("run_id")),
        ("finalization_sha256", INV.sha_file(pfin))])
    return expected_receipt(out_dir, bound, MAX_ATTEMPTS,
                            list(doc.get("retry") or []), parent), []


def receipt_problems(out_dir, bound, receipt):
    """Why this receipt is not the one the correction owner would have written."""
    if not isinstance(receipt, dict):
        return ["the receipt is not an object"]
    want, bad = _expected_for(out_dir, bound, receipt)
    if want is None:
        return bad
    for field in RECEIPT_IMMUTABLE:
        if receipt.get(field) != want[field]:
            bad.append("receipt.%s is not the expected value" % field)
    labels = list(receipt.get("allowed") or [])
    if len(set(labels)) != len(labels):
        bad.append("the receipt names a call twice")
    if not isinstance(receipt.get("states"), list):
        bad.append("receipt.states is not a list")
    if set(receipt) != set(RECEIPT_IMMUTABLE) | {"states"}:
        bad.append("the receipt carries unexpected fields")
    return bad


def _invocations(out_dir, bound, labels, attempt):
    """The exact runnable calls: ordered scriptPath + args, written here."""
    by = HR._by_label(bound.evidence)
    script_dir = os.path.join(out_dir, "scripts")
    os.path.isdir(script_dir) or os.makedirs(script_dir)
    out = []
    for label in labels:
        task, blind = by[label]
        text = render_launcher(task, blind, attempt)
        path = os.path.join(script_dir, "%s.attempt%d.js"
                            % (label.replace("/", "_"), attempt))
        HR._atomic(path, text)
        out.append(collections.OrderedDict([
            ("label", label), ("attempt", attempt),
            ("scriptPath", path), ("args", None),
            ("script_sha256", K._sha(text))]))
    return out


def prepare_run(out_dir, bound):
    """Publish THE correction primary: exactly the derived four, in order.

    Takes no caller labels and no subset: the denominator is derived here.
    """
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        return {"ok": False, "problems": ["output directory is not fresh"],
                "invocations": []}
    bad = preflight(bound.packet, bound.run, bound.evidence,
                    bound.released)["problems"]
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    labels = correction_labels(bound.run, bound.evidence)
    _write_receipt(out_dir, bound, 1, labels)
    return {"ok": True, "problems": [],
            "invocations": _invocations(out_dir, bound, labels, 1)}


def record_state(out_dir, state_path):
    """One unique official state, appended by the released recorder."""
    return HR.record_state(out_dir, state_path)


def run_evidence(out_dir, bound, receipt):
    """Per-call proof. Only the prompt and launcher are this file's; the model,
    effort, tool, transcript and continuation proof is K._official_proof."""
    by = HR._by_label(bound.evidence)
    attempt = receipt.get("attempt")
    allowed = set(receipt.get("allowed") or [])
    out, problems = collections.OrderedDict(), []
    runs, agents, responses = set(), set(), set()

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
            problems.append("%s: state is unreadable (%s)"
                            % (run_id, str(exc)[:80]))
            continue
        if not isinstance(doc, dict):
            problems.append("%s: state is not an object" % run_id)
            continue

        session_dir, session_id = HR.AUD._official_location(state)
        if session_dir is None:
            bad.append("the state is not where the runtime puts an official one")
        elif session_id != K.PARENT_SESSION:
            bad.append("parent session %r is not the frozen one" % session_id)
        if doc.get("runId") != run_id:
            bad.append("state runId %r is not its own official name"
                       % doc.get("runId"))
        if doc.get("runId") in runs:
            bad.append("run id %r is reused" % doc.get("runId"))
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
            problems.append("%s: names %r, which is not a scheduled call"
                            % (run_id, label))
            continue
        if label not in allowed:
            problems.append("%s: %s is not allowed by this receipt"
                            % (run_id, label))
            continue
        if label in out:
            problems.append("%s: %s was already served" % (run_id, label))
            continue
        task, blind = by[label]

        want_script = render_launcher(task, blind, attempt)
        if doc.get("script") != want_script:
            bad.append("the state did not run the corrected launcher bytes")
        sp = doc.get("scriptPath")
        if sp is not None:
            if not (isinstance(sp, str) and os.path.isfile(sp)):
                bad.append("scriptPath %r is not a readable file" % sp)
            elif INV.sha_file(sp) != K._sha(want_script):
                bad.append("the scriptPath bytes are not the corrected launcher")

        got = K.direct_result(doc)
        if got is None:
            bad.append("the state carries no returned result object")
        else:
            if set(got) != set(RESULT_FIELDS):
                bad.append("the returned object's keys are %s, not exactly %s"
                           % (sorted(got), sorted(RESULT_FIELDS)))
            for field, want in (("task_id", task["task_id"]),
                                ("kind", task["kind"]),
                                ("members", list(task["members"])),
                                ("blind", blind), ("attempt", attempt),
                                ("model", K.MODEL), ("effort", K.EFFORT),
                                ("agentType", K.AGENT_TYPE)):
                if got.get(field) != want:
                    bad.append("result %s is %r, not %r"
                               % (field, got.get(field), want))

        if row.get("state") == "done":
            if row.get("agentId") in agents:
                bad.append("agent id %r is reused" % row.get("agentId"))
            agents.add(row.get("agentId"))
            final, complete, why = K._official_proof(state, blind_prompt(task))
            bad += why
            tp = os.path.join(session_dir or "", "subagents", "workflows",
                              run_id, "agent-%s.jsonl" % row.get("agentId"))
            recs = HR.AUD._jsonl(tp) if os.path.isfile(tp) else None
            if recs is None:
                bad.append("the transcript cannot be read whole")
            else:
                if {r.get("agentId") for r in recs} != {row.get("agentId")}:
                    bad.append("a transcript record carries a foreign agentId")
                if {r.get("sessionId") for r in recs} != {K.PARENT_SESSION}:
                    bad.append("a transcript record carries a foreign sessionId")
                ids = {(r.get("message") or {}).get("id") for r in recs
                       if r.get("type") == "assistant"}
                if ids & responses:
                    bad.append("a response id is reused across the run")
                responses |= ids
            if got is not None and got.get("text") != final:
                bad.append("the returned text is not the proved final segment")
            if bad:
                _refuse(label, bad[0], bad)
                continue
            out[label] = ("proved", "", complete)
            continue

        if row.get("state") == "error":
            bad += HR.AUD._rejection(row, K.AGENT_TYPE, K.EFFORT)
            if got is not None and got.get("text") is not None:
                bad.append("a lane rejected before any model response cannot "
                           "carry answer text")
            if K._spawned_transcripts(session_dir, run_id):
                bad.append("a lane rejected before any model response cannot "
                           "have spawned a worker transcript")
            if not K._recorded_zero(doc.get("totalToolCalls")):
                bad.append("totalToolCalls is %r, not a recorded integer zero, "
                           "so zero tool use is not proved"
                           % (doc.get("totalToolCalls"),))
            if bad:
                _refuse(label, bad[0], bad)
                continue
            out[label] = ("transport_no_answer", NO_ANSWER, None)
            continue

        why = "the agent row is %r, not 'done'" % row.get("state")
        _refuse(label, why, bad + [why])
    return out, problems


def finalize(out_dir, bound):
    """Raw first, then proof, then the released strict reader. One outcome each."""
    receipt = K._load(os.path.join(out_dir, HR.RECEIPT_NAME))
    attempt = receipt.get("attempt")
    by = HR._by_label(bound.evidence)
    raw_dir = os.path.join(out_dir, "raw")
    os.path.isdir(raw_dir) or os.makedirs(raw_dir)

    harvested = []
    for state in receipt.get("states") or []:
        run_id = (os.path.splitext(os.path.basename(state))[0]
                  if isinstance(state, str) else "unreadable")
        try:
            got = K.direct_result(json.loads(K._read(state)))
        except Exception:                             # noqa: BLE001 - by design
            got = None
        for n, text in enumerate([got.get("text")] if got else []):
            if not isinstance(text, str):
                continue
            name = "%s.%03d.raw.json" % (run_id, n)
            HR._atomic(os.path.join(raw_dir, name), text)
            harvested.append(name)

    receipt_bad = receipt_problems(out_dir, bound, receipt)
    allowed = list(receipt.get("allowed") or [])
    if receipt_bad:
        problems, outcomes = [], collections.OrderedDict(
            (lab, ("unproved", "the receipt is not the owner's"))
            for lab in allowed)
    else:
        proved, problems = run_evidence(out_dir, bound, receipt)
        outcomes = collections.OrderedDict()
        for label, (state, why, text) in proved.items():
            if state != "proved":
                outcomes[label] = (state, why)
                continue
            HR._atomic(os.path.join(raw_dir, "%s.attempt%s.proved.json"
                                    % (label.replace("/", "_"), attempt)), text)
            _obj, bad = HR.read_reply(text, by[label][0])
            outcomes[label] = ("valid", "") if not bad \
                else ("invalid_response", bad[0])
    for label in allowed:
        outcomes.setdefault(label, ("missing", "no official state"))

    counts = collections.Counter(o for o, _w in outcomes.values())
    ledger = collections.OrderedDict(
        [("scheduled", len(allowed))]
        + [(name, counts.get(name, 0)) for name in
           ("valid", "invalid_response", "transport_no_answer", "unproved",
            "missing")])
    complete = (not receipt_bad and not problems
                and set(outcomes) == set(allowed)
                and counts.get("missing", 0) == 0
                and counts.get("unproved", 0) == 0)
    retry = [lab for lab in allowed
             if outcomes[lab][0] in RETRYABLE] if complete else []
    if attempt != 1:
        retry = []

    doc = collections.OrderedDict([
        ("door", DOOR), ("attempt", attempt),
        ("run_id", receipt.get("run_id")),
        ("receipt_sha256", INV.sha_file(os.path.join(out_dir,
                                                     HR.RECEIPT_NAME))),
        ("manifest_sha256", receipt.get("manifest_sha256")),
        ("correction_of", receipt.get("correction_of")),
        ("harvested_raw", harvested),
        ("primary_complete", complete),
        ("problems", receipt_bad + problems),
        ("outcomes", [[lab, o, w] for lab, (o, w) in outcomes.items()]),
        ("ledger", ledger),
        ("budget", _budget_after(bound, attempt, len(allowed))),
        ("retry", retry)])
    HR._atomic(os.path.join(out_dir, HR.FINALIZATION_NAME),
               json.dumps(doc, indent=1))

    child = _publish_child(out_dir, bound, doc)
    if child:
        doc["child"] = child
    return doc


def _budget_after(bound, attempt, scheduled):
    """The durable budget line for THIS attempt. Exact, never estimated."""
    before = _ledger_before(bound.run, bound.evidence)
    primaries = len(correction_labels(bound.run, bound.evidence))
    spent = primaries + scheduled if attempt == MAX_ATTEMPTS else scheduled
    return collections.OrderedDict([
        ("ledger_before", before), ("this_attempt", scheduled),
        ("spent_so_far", spent), ("ledger_after", before + spent),
        ("frozen_primaries", primaries),
        ("worst_case_total", primaries * MAX_ATTEMPTS),
        ("global_ceiling", GLOBAL_CEILING),
        ("within_ceiling", before + primaries * MAX_ATTEMPTS
         <= GLOBAL_CEILING)])


def _publish_child(out_dir, bound, doc):
    """At most ONE parent-bound child, for the exact schema-invalid rows."""
    labels = list(doc.get("retry") or [])
    if not labels or doc.get("attempt") != 1 \
            or not doc.get("primary_complete"):
        return None
    child_dir = os.path.join(out_dir, "retry")
    if os.path.isdir(child_dir) and os.listdir(child_dir):
        return None
    _write_receipt(child_dir, bound, MAX_ATTEMPTS, labels,
                   parent=collections.OrderedDict([
                       ("run_id", doc["run_id"]),
                       ("finalization_sha256", INV.sha_file(
                           os.path.join(out_dir, HR.FINALIZATION_NAME)))]))
    receipt = K._load(os.path.join(child_dir, HR.RECEIPT_NAME))
    if receipt_problems(child_dir, bound, receipt):
        return None
    return {"dir": child_dir, "problems": [],
            "invocations": _invocations(child_dir, bound, labels,
                                        MAX_ATTEMPTS)}
