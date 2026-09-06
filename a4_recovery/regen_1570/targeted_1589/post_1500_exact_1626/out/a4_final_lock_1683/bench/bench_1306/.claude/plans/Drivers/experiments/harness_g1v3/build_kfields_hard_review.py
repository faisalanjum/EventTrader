"""Codex SEQ 1372 — the finite double-blind hard review of the A4 key.

This is the hard-disagreement part of live Step 1 A4 ("Build and lock the
K-fields answer key"), not A5. Nothing here calls a model by itself.

WHAT MAKES A TASK is structural, never a name: an unresolved key, a selected
item whose settlement matched neither draft, or an exact-locator group. No
packet id, quote, keyword, example or threshold appears in this file.

WHAT THE BLIND CALLER SEES, in this order:
    role, rules, output card, this review's task and its output wrapper
    ---- the live boundary and injection control ----
    ONE JSON object: menu, event, item

The instructions sit ABOVE the boundary because the boundary says everything
below it is untrusted evidence. The SEQ 1371 build put the task BELOW it, so
all 35 prompts declared their own task to be data and all 7 group prompts still
carried the singular one-item role (Codex SEQ 1372). The rules and the output
card are the live owners' own bytes; only the role, task and wrapper are
written here, and no fact schema is copied.

CODE MAY prove identity, location, schema, counts and exact field differences.
CODE MAY NOT choose a semantic winner, vote, repair, match words or convert a
synonym. The two blind answers are evidence for the final independent review.
"""
import collections
import functools
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_key as K                                    # noqa: E402

INV = K.INV                       #: the owner's own hasher, never a second one
C = K.C                           #: the live semantic rules / output owner
AUD = K.AUD                       #: the official-state audit owner

DOOR = "a4_hard_review_double_blind"
BLINDS = (1, 2)                     #: two independent blind readers per task
MAX_ATTEMPTS = K.MAX_ATTEMPTS       #: one identical-prompt retry, never a third
RECEIPT_NAME = K.RECEIPT_NAME
FINALIZATION_NAME = K.FINALIZATION_NAME
MANIFEST_NAME = "hard_review.manifest.json"
LAUNCHER_NAME = "kfields-a4-hard-review"

#: Codex SEQ 1371/1372 state the global call ceiling. It is his number, not a
#: measurement of mine, so it is named here with its authority and checked
#: hard - a missing ceiling must never mean "no ceiling".
GLOBAL_CEILING = 4382

ITEM_REPLY_KEYS = tuple(K.a1_reader.REPLY_KEYS)
GROUP_REPLY_KEYS = ("members", "members_are_one_fact", "reason")
MEMBER_KEYS = ("member_index", "settled")

#: The five event fields the live one-item payload carries, in its order.
EVENT_VIEW = ("source_id", "ticker", "event_date", "fye_month", "text_parts")

#: What one hard-review launcher returns. Proved field by field.
RESULT_FIELDS = ("task_id", "kind", "members", "blind", "attempt", "model",
                 "effort", "agentType", "text")

RECEIPT_IMMUTABLE = ("run_id", "door", "attempt", "allowed", "parent",
                     "transport", "manifest_sha256", "derived_from", "prompts")


@functools.lru_cache(maxsize=None)
def _items():
    """The frozen scheduled items, by key. Read once; the owner owns them."""
    return {i["packet_id"]: i for i in K.phase1_items()}


@functools.lru_cache(maxsize=None)
def _source(source_id):
    """One frozen source with its readable menu. Read once, never mutated."""
    src = K.source_input(source_id)
    display, back = K.a1_reader.readable_menu(src["menu_tokens"])
    return src, tuple(display), back


def _boundary_at(suffix):
    """The live boundary line of ONE contract version, from its owner."""
    return C._fences(C._section(C.package_path(suffix), C._BOUNDARY))[0].strip()


def _boundary():
    """The live boundary line, from the one owner that declares it."""
    return _boundary_at("")


# ------------------------------------------------- the private package context
# THE ONE LIFECYCLE OVER A SMALL DATA CONTEXT (Codex SEQ 1492 item B), the
# pattern build_kfields_key got at SEQ 1488: {items, tasks, suffix,
# derived_from, before, ceiling[, budget_receipt]}. The historical public door
# builds it from its evidence directory; a fixed targeted wrapper builds its
# own complete one. No public parameter chooses a subset.
def _default(evidence_dir):
    return {"items": _items(), "tasks": tasks(evidence_dir), "suffix": "",
            "derived_from": _derived_from(evidence_dir),
            "before": _ledger_before(evidence_dir), "ceiling": GLOBAL_CEILING,
            "authority": "Codex SEQ 1372",
            "step": "live Step 1 A4 - the hard-disagreement review"}


def _static():
    """The context the evidence-free public helpers use: frozen items, the
    version-1 contract."""
    return {"items": _items(), "suffix": ""}


# --------------------------------------------------------- the prompt -------
#: The plural role. There is no live owner to reuse for it: `C.ONE_ITEM_ROLE`
#: is singular by construction, and a group task is a genuinely different
#: multi-item task (Codex SEQ 1373 item 2). Everything a single reading must
#: obey still comes from [RULES] and [OUTPUT]; this only says how many targets
#: there are and that each is decided on its own evidence.
_GROUP_ROLE = "\n".join([
    'You are an independent reviewer reading SEVERAL already-located items from the event',
    "below. Each item's `raw_label_or_claim` names the one target meaning to interpret for",
    "that item, and it lies inside that item's already-located quote. The complete event is",
    'CONTEXT so you can interpret those targets correctly; it is NOT a request to find other',
    'facts. Interpret those targets only. Any one of them may yield more than one fact only',
    'where the RULES below already require a sibling or a basis split.',
    "Each item's source location is already fixed and supplied to you: never copy, choose,",
    'repair, extend or emit it. Where evidence you would need is missing, abstain instead',
    'of extending or replacing it.'])


def _role(kind):
    """The live singular owner for one item; the local plural role for a group.

    The one-item role is `C.ONE_ITEM_ROLE` BYTE FOR BYTE. A near-copy of it
    read the same but duplicated every behaviour-changing target, context,
    sibling/basis, locator and abstention rule, so changing the real owner left
    this package silently stale and still passing preflight (Codex SEQ 1373).
    """
    if kind == "item":
        return C.ONE_ITEM_ROLE
    if kind == "group":
        return _GROUP_ROLE
    raise ValueError("unknown task kind %r" % kind)


_TASK = {
    "item": "\n".join([
        "Everything above defines what a lawful reply means; obey it exactly.",
        "Settle the one located item from the event alone. No other reader's",
        "answer is shown to you, and none exists for you to agree or disagree",
        "with.",
        "",
        "Genuine ambiguity is an ANSWER, not a failure. Record it through the",
        "lawful abstention branch rather than resolving it by guessing."]),
    "group": "\n".join([
        "Everything above defines what a lawful reply means; obey it exactly.",
        "The `item` key below carries SEVERAL located items, each with its own",
        "`member_index`. Settle each one independently first, from the event",
        "alone and on its own evidence. Only then answer the one further",
        "question this review asks. No other reader's answer is shown to you,",
        "and none exists for you to agree or disagree with.",
        "",
        "Genuine ambiguity is an ANSWER, not a failure. Record it through the",
        "lawful abstention branch rather than resolving it by guessing."]),
}


def _output(kind):
    """This review's wrapper only. The reply's MEANING stays with [OUTPUT]."""
    if kind == "item":
        return "\n".join([
            "Reply with ONE JSON object and nothing else - no prose before or",
            "after it, no second object. Plain JSON, or exactly one fenced",
            "JSON block.",
            "",
            "It is exactly the reply the [OUTPUT] section above defines, for",
            "the one located item: the sparse shape %s."
            % ", ".join("`%s`" % k for k in ITEM_REPLY_KEYS),
            "",
            "Emit no key that is not named there."])
    return "\n".join([
        "Reply with ONE JSON object and nothing else - no prose before or",
        "after it, no second object. Plain JSON, or exactly one fenced JSON",
        "block. Its keys are EXACTLY these three, with no others: %s."
        % ", ".join("`%s`" % k for k in GROUP_REPLY_KEYS),
        "",
        "`members`",
        "    one row per located item, in the order the items are given,",
        "    each an object with keys %s."
        % ", ".join("`%s`" % k for k in MEMBER_KEYS),
        "    `member_index` echoes that item's own index exactly.",
        "    `settled` is the reply the [OUTPUT] section above defines for",
        "    that item, in its sparse shape.",
        "",
        "`members_are_one_fact`",
        "    a real JSON `true`, `false` or `null`, never a string.",
        "    true  - every member above expresses ONE underlying fact.",
        "    false - they are distinct facts.",
        "    null  - the evidence and the rules cannot safely settle it.",
        "    `null` is a real answer here, not a failure. Use it rather than",
        "    guessing either way.",
        "",
        "`reason`",
        "    one nonempty sentence, in your own words, giving the evidence",
        "    for that judgment.",
        "",
        "Every field is required. Emit no key that is not named here."])


def _prompt_prefix(suffix, kind):
    """The trusted instruction block, ABOVE the boundary.

    `role_rules` and `one_item_output_section` are the live semantic owners,
    served whole and unsummarised, exactly as `C.build_prompt("drafter")`
    serves them, at ONE named contract version. Only the role, the task and
    this review's output wrapper are written here, and the boundary plus
    injection control are the live bytes, unchanged, so everything below them
    really is data.
    """
    return (
        "[ROLE]\n%s\n\n" % _role(kind)
        + "[RULES]\n%s\n\n" % C.role_rules("drafter", suffix)
        + "[OUTPUT]\n%s\n\n" % C.one_item_output_section().rstrip()
        + "[A4 HARD REVIEW TASK]\n%s\n\n" % _TASK[kind]
        + "[A4 HARD REVIEW OUTPUT]\n%s\n\n" % _output(kind)
        + "[BOUNDARY]\n%s\n\n" % _boundary_at(suffix)
        + "%s\n\n" % C.INJECTION_CONTROL
        + "[INPUT]\n")


def prompt_prefix(kind):
    return _prompt_prefix("", kind)


def _payload(items, task):
    """The ONE untrusted JSON object: menu, event, item. The live A3 shape.

    A group's `item` is the list of its located items, each carrying the
    code-owned `member_index` that binds a reply row to a member. The index is
    scaffolding this review owns, never source data, so no source-owned field
    is duplicated and no packet identity is shown.
    """
    keys = task["members"]
    sids = sorted(set(items[k]["source_id"] for k in keys))
    if len(sids) != 1:
        raise ValueError("a task spans %d sources" % len(sids))
    src, display, _back = _source(sids[0])
    view = collections.OrderedDict((k, src[k]) for k in EVENT_VIEW)
    if task["kind"] == "item":
        one = K._frozen_item(items[keys[0]])
    else:
        one = [dict(K._frozen_item(items[k]), member_index=n + 1)
               for n, k in enumerate(keys)]
    return collections.OrderedDict([("menu", list(display)), ("event", view),
                                    ("item", one)])


def payload(task):
    return _payload(_items(), task)


def _blind_prompt(ctx, task):
    """Trusted instructions, the live boundary, then only the data."""
    return _prompt_prefix(ctx["suffix"], task["kind"]) \
        + json.dumps(_payload(ctx["items"], task), indent=1)


def blind_prompt(task):
    return _blind_prompt(_static(), task)


def call_label(task_id, blind):
    """THE call identity. The launcher's agent label IS this string."""
    return "%s/b%d" % (task_id, blind)


def render_launcher(task, blind, attempt=1):
    return _render_launcher(_static(), task, blind, attempt)


def _render_launcher(ctx, task, blind, attempt=1):
    """One agent() call, nothing else. Blind index and attempt are identity.

    Both are bounded here rather than at the caller: a third blind reader or a
    third attempt is a different experiment, and the only place that can refuse
    it for every caller is the renderer itself.
    """
    if blind not in BLINDS:
        raise ValueError("blind %r is not one of the %d frozen blind readers"
                         % (blind, len(BLINDS)))
    if not (isinstance(attempt, int) and 1 <= attempt <= MAX_ATTEMPTS):
        raise ValueError("attempt %r is outside 1..%d" % (attempt,
                                                          MAX_ATTEMPTS))
    call = collections.OrderedDict([("task_id", task["task_id"]),
                                    ("kind", task["kind"]),
                                    ("members", list(task["members"])),
                                    ("blind", blind), ("attempt", attempt)])
    return "\n".join([
        "export const meta = {",
        "  name: '%s'," % LAUNCHER_NAME,
        "  description: 'K-fields A4 hard review: one independent blind"
        " reading of one already-located task',",
        "  phases: [{ title: 'Review' }],",
        "}",
        "const CALL = " + json.dumps(call),
        "const PROMPT = " + json.dumps(_blind_prompt(ctx, task)),
        "let text = null",
        "try {",
        "  text = await agent(PROMPT, {",
        "    label: " + json.dumps(call_label(task["task_id"], blind)) + ",",
        "    phase: 'Review',",
        "    model: " + json.dumps(K.MODEL) + ", effort: "
        + json.dumps(K.EFFORT) + ",",
        "    agentType: " + json.dumps(K.AGENT_TYPE) + ",",
        "    disallowedTools: " + json.dumps(list(K.DISALLOWED)) + ",",
        "  })",
        "} catch (e) { text = null }",
        "return { task_id: CALL.task_id, kind: CALL.kind,",
        "         members: CALL.members, blind: CALL.blind,",
        "         attempt: CALL.attempt, model: " + json.dumps(K.MODEL) + ",",
        "         effort: " + json.dumps(K.EFFORT) + ",",
        "         agentType: " + json.dumps(K.AGENT_TYPE) + ",",
        "         text: typeof text === 'string' ? text : null }",
        "",
    ])


# ---------------------------------------------------------- the 35 tasks ----
def _corrected(run_dir):
    """The two frozen corrected artifacts, by their own names."""
    return (K._load(os.path.join(run_dir, "regrade_1370.json")),
            K._load(os.path.join(run_dir, "conflicts_1370.json")))


def tasks(run_dir):
    """THE 35. Derived structurally, in one deterministic order.

    unresolved keys, then selected both-rejected items that are not already a
    member of a locator group, then one task per group. The overlap is credited
    once, to its group, because there the relationship IS the question.
    """
    regrade, inventory = _corrected(run_dir)
    items = _items()
    unresolved = list(regrade["selection"]["unresolved"])
    both = [e["packet_id"] for e in inventory["items_both_drafts_rejected"]]
    groups = inventory["conflicting_locator_groups"]
    grouped = [m["packet_id"] for g in groups for m in g["members"]]

    out = []
    for key in unresolved:
        out.append(collections.OrderedDict([
            ("kind", "item"), ("origin", "unresolved"), ("members", [key])]))
    for key in both:
        if key not in set(grouped):
            out.append(collections.OrderedDict([
                ("kind", "item"), ("origin", "both_drafts_rejected"),
                ("members", [key])]))
    for group in groups:
        out.append(collections.OrderedDict([
            ("kind", "group"), ("origin", "locator_conflict"),
            ("members", [m["packet_id"] for m in group["members"]])]))
    for n, task in enumerate(out):
        task["task_id"] = "hr-%03d" % n
        task.move_to_end("task_id", last=False)
        for key in task["members"]:
            if key not in items:
                raise ValueError("task names an unscheduled key: %s" % key)
    return out


def coverage_problems(run_dir, built):
    """One-to-one against every frozen input. A mismatch stops the build."""
    regrade, inventory = _corrected(run_dir)
    unresolved = set(regrade["selection"]["unresolved"])
    both = set(e["packet_id"] for e in inventory["items_both_drafts_rejected"])
    groups = inventory["conflicting_locator_groups"]
    grouped = set(m["packet_id"] for g in groups for m in g["members"])
    bad = []

    ids = [t["task_id"] for t in built]
    if len(set(ids)) != len(ids):
        bad.append("a task id is used twice")
    if ids != ["hr-%03d" % n for n in range(len(built))]:
        bad.append("the tasks are not in their derived order")

    covered = [k for t in built for k in t["members"]]
    if len(set(covered)) != len(covered):
        bad.append("a packet is reviewed by more than one task")
    covered = set(covered)
    for name, want in (("unresolved", unresolved), ("both-rejected", both)):
        missing = sorted(want - covered)
        if missing:
            bad.append("%s not covered: %s" % (name, missing[:3]))
    want_groups = sorted(tuple(sorted(m["packet_id"] for m in g["members"]))
                         for g in groups)
    got_groups = sorted(tuple(sorted(t["members"])) for t in built
                        if t["kind"] == "group")
    if got_groups != want_groups:
        bad.append("the group tasks are not the frozen groups")
    if covered - (unresolved | both | grouped):
        bad.append("a task reviews a packet no frozen input names")

    n_solo = len(both - grouped)
    if len(built) != len(unresolved) + n_solo + len(groups):
        bad.append("task count is not unresolved + solo both-rejected + groups")
    return bad


def _canonical_of(ctx):
    """THE denominator: every call label, in the context's derived order."""
    return [call_label(t["task_id"], b) for t in ctx["tasks"] for b in BLINDS]


def canonical_calls(run_dir):
    """THE denominator: 70 call labels, in their derived order."""
    return _canonical_of(_default(run_dir))


def _by_label_of(ctx):
    """{call label: (task, blind)} for every scheduled call."""
    return {call_label(t["task_id"], b): (t, b)
            for t in ctx["tasks"] for b in BLINDS}


def _by_label(run_dir):
    return _by_label_of(_default(run_dir))


# --------------------------------------------------------------- replies ----
def _settled(raw, item):
    """One member's settled reply, through the EXISTING reader. -> (obj, bad)

    Exactly the two calls `completed_draft` makes, with the same arguments and
    no schema of its own. The one difference is that it KEEPS the reader's
    problem list instead of collapsing it to None: a draft only needs to know
    it cannot be compared, but a blind reviewer's rejected answer has to say
    why, or an invalid call is undiagnosable - which is the exact failure that
    cost 44 paid calls in A4.
    """
    _src, _display, back = _source(item["source_id"])
    frozen = K._frozen_item(item)
    done, bad = K.a1_reader.normalize(raw, frozen, item["source_id"], back)
    if bad:
        return None, list(bad)
    worse = K.a1_reader.validate(done, frozen,
                                 K.source_parts(item["source_id"])) or []
    return (None, list(worse)) if worse else (done, [])


def read_reply(text, task):
    return _read_reply(_static(), text, task)


def _read_reply(ctx, text, task):
    """Raw blind answer -> validated settled reply(s). Whole task or nothing."""
    items = ctx["items"]
    if not isinstance(text, str):
        return None, ["no reply text: %s" % type(text).__name__]
    try:
        obj = K.RT.parse_reply(text)
    except Exception as exc:                          # noqa: BLE001 - by design
        return None, ["not one lawful JSON object: %s" % str(exc)[:120]]
    if not isinstance(obj, dict):
        return None, ["the reply is %s, not an object" % type(obj).__name__]

    if task["kind"] == "item":
        if set(obj) != set(ITEM_REPLY_KEYS):
            return None, ["keys are %s, not exactly %s"
                          % (sorted(obj), sorted(ITEM_REPLY_KEYS))]
        done, bad = _settled(obj, items[task["members"][0]])
        return (None, bad) if bad else ({"settled": done}, [])

    if set(obj) != set(GROUP_REPLY_KEYS):
        return None, ["keys are %s, not exactly %s"
                      % (sorted(obj), sorted(GROUP_REPLY_KEYS))]
    rows = obj["members"]
    if not isinstance(rows, list) or len(rows) != len(task["members"]):
        return None, ["members must be %d rows, one per group member"
                      % len(task["members"])]
    problems, out = [], collections.OrderedDict()
    for n, (row, key) in enumerate(zip(rows, task["members"])):
        if not isinstance(row, dict) or set(row) != set(MEMBER_KEYS):
            problems.append("member row %d is not exactly %s"
                            % (n + 1, sorted(MEMBER_KEYS)))
            continue
        if row["member_index"] != n + 1:
            problems.append("member row %d echoes index %r; the rows are out "
                            "of order" % (n + 1, row["member_index"]))
            continue
        done, bad = _settled(row["settled"], items[key])
        problems += ["%s: %s" % (key, b) for b in bad]
        if not bad:
            out[key] = done
    # THE TYPED JUDGMENT. `null` is a real semantic answer, so the check is on
    # the JSON type, never on the truth value: `if not verdict` would have
    # thrown away every lawful false and every lawful null alike.
    verdict = obj["members_are_one_fact"]
    if not (verdict is None or verdict is True or verdict is False):
        problems.append("members_are_one_fact is %r, not a real JSON true, "
                        "false or null" % (verdict,))
    if not (isinstance(obj["reason"], str) and obj["reason"].strip()):
        problems.append("reason is not a nonempty string")
    if problems:
        return None, problems
    return {"members": out, "members_are_one_fact": verdict,
            "reason": obj["reason"]}, []


# ---------------------------------------------------------- the package -----
def _ledger_before(run_dir):
    """MEASURED: the A4 baseline plus what the A4 receipts actually spent."""
    spent = 0
    for base in (run_dir, os.path.join(run_dir, "retry")):
        fin = os.path.join(base, FINALIZATION_NAME)
        if os.path.isfile(fin):
            spent += K._load(fin)["ledger"]["scheduled"]
    return K.LEDGER_BEFORE + spent


def _derived_from(run_dir):
    return collections.OrderedDict([
        ("owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_key.py"))),
        ("regrade_sha256", INV.sha_file(
            os.path.join(run_dir, "regrade_1370.json"))),
        ("conflicts_sha256", INV.sha_file(
            os.path.join(run_dir, "conflicts_1370.json"))),
        ("a4_receipt_sha256", INV.sha_file(
            os.path.join(run_dir, RECEIPT_NAME))),
        ("a4_finalization_sha256", INV.sha_file(
            os.path.join(run_dir, FINALIZATION_NAME)))])


def manifest(run_dir):
    """Everything this run would depend on, pinned. Pure; writes nothing."""
    built = tasks(run_dir)
    bad = coverage_problems(run_dir, built)
    if bad:
        raise ValueError("coverage refused: %s" % bad[:3])
    return _manifest(_default(run_dir))


def _manifest(ctx):
    """The complete manifest of ONE context; the caller has already proved
    the context's population. Pure; writes nothing."""
    built, items = ctx["tasks"], ctx["items"]

    rows, sources, calls = [], collections.OrderedDict(), []
    for task in built:
        text = _blind_prompt(ctx, task)
        sid = items[task["members"][0]]["source_id"]
        if sid not in sources:
            src, display, back = _source(sid)
            sources[sid] = collections.OrderedDict([
                ("source_id", sid),
                ("source_sha256", K._sha(json.dumps(src, sort_keys=True,
                                                    default=str))),
                ("menu_display_sha256", K._sha("\n".join(display))),
                ("menu_back_sha256",
                 K._sha(json.dumps(back, sort_keys=True)))])
        scripts = []
        row = collections.OrderedDict([
            ("task_id", task["task_id"]), ("kind", task["kind"]),
            ("origin", task["origin"]), ("members", list(task["members"])),
            ("source_id", sid),
            ("payload_sha256", K._sha(json.dumps(_payload(items, task),
                                                 sort_keys=True))),
            ("prompt_sha256", K._sha(text)),
            ("prompt_bytes", len(text.encode("utf-8")))])
        for blind in BLINDS:
            script = _render_launcher(ctx, task, blind)
            row["blind%d_script_sha256" % blind] = K._sha(script)
            scripts.append(len(script.encode("utf-8")))
            calls.append(call_label(task["task_id"], blind))
        row["largest_script_bytes"] = max(scripts)
        rows.append(row)

    over = sorted(r["task_id"] for r in rows
                  if r["largest_script_bytes"] >= K.TRANSPORT_LIMIT)
    primaries = len(rows) * len(BLINDS)
    before, suffix = ctx["before"], ctx["suffix"]
    budget = [("before", before), ("primaries", primaries),
              ("after_primaries", before + primaries),
              ("max_attempts_per_call", MAX_ATTEMPTS),
              ("worst_case_total", primaries * MAX_ATTEMPTS),
              ("worst_case_after", before + primaries * MAX_ATTEMPTS),
              ("global_ceiling", ctx["ceiling"])]
    # a context bound to a budget receipt carries that binding; the frozen
    # version-1 context carries exactly its historical fields
    budget += [("budget_receipt_sha256", ctx["budget_receipt"])] \
        if ctx.get("budget_receipt") else []
    return collections.OrderedDict([
        ("door", DOOR),
        ("authority", ctx["authority"]),
        ("step", ctx["step"]),
        ("derived_from", ctx["derived_from"]),
        ("item_role_sha256", K._sha(C.ONE_ITEM_ROLE)),
        ("semantic_rules_sha256", K._sha(C.role_rules("drafter", suffix))),
        ("output_card_sha256", K._sha(C.one_item_output_section().rstrip())),
        ("boundary_sha256", K._sha(_boundary_at(suffix))),
        ("injection_control_sha256", K._sha(C.INJECTION_CONTROL)),
        ("prefix_item_sha256", K._sha(_prompt_prefix(suffix, "item"))),
        ("prefix_group_sha256", K._sha(_prompt_prefix(suffix, "group"))),
        ("transport", K._transport_block()),
        ("budget", collections.OrderedDict(budget)),
        ("counts", collections.OrderedDict([
            ("tasks", len(rows)),
            ("item_tasks", sum(1 for r in rows if r["kind"] == "item")),
            ("group_tasks", sum(1 for r in rows if r["kind"] == "group")),
            ("reviewed_packets", len(set(k for r in rows
                                         for k in r["members"]))),
            ("primary_calls", primaries)])),
        ("capacity", collections.OrderedDict([
            ("unit", "UTF-8 bytes of the serialized launcher script the "
                     "runtime actually runs; never summed"),
            ("transport_limit_bytes", K.TRANSPORT_LIMIT),
            ("largest_script_bytes", max(r["largest_script_bytes"]
                                         for r in rows)),
            ("smallest_script_bytes", min(r["largest_script_bytes"]
                                          for r in rows)),
            ("largest_prompt_bytes", max(r["prompt_bytes"] for r in rows)),
            ("at_or_over_transport_limit", over)])),
        ("sources", list(sources.values())),
        ("tasks", rows),
        ("call_order", calls)]
        + ([("contract_suffix", suffix)] if suffix else []))


def _atomic(path, text):
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(text)
    os.replace(tmp, path)


def build(out_dir, run_dir):
    """Write the frozen package. Launches nothing, calls nothing."""
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    doc = manifest(run_dir)
    _atomic(os.path.join(out_dir, MANIFEST_NAME), json.dumps(doc, indent=1))
    for kind in ("item", "group"):
        _atomic(os.path.join(out_dir, "prompt_prefix_%s.txt" % kind),
                prompt_prefix(kind))
    return doc


def package_problems(out_dir, run_dir):
    """Re-derive everything from the live owners and compare. -> [problems]"""
    try:
        manifest(run_dir)                     # coverage, at the public door
    except ValueError as exc:                         # noqa: BLE001 - by design
        return ["the tasks no longer derive: %s" % exc]
    return _package_problems(_default(run_dir), out_dir)


def _package_problems(ctx, out_dir):
    """The whole rebuilt manifest against the pinned one. -> [problems]"""
    path = os.path.join(out_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return ["no manifest at %s" % out_dir]
    pinned = K._load(path)
    bad = []
    want = _manifest(ctx)
    if K._sha(json.dumps(pinned, sort_keys=True)) \
            != K._sha(json.dumps(want, sort_keys=True)):
        for field in ("door", "item_role_sha256", "semantic_rules_sha256",
                      "output_card_sha256",
                      "boundary_sha256", "injection_control_sha256",
                      "prefix_item_sha256", "prefix_group_sha256",
                      "transport", "budget", "counts", "capacity", "sources",
                      "call_order", "derived_from", "contract_suffix"):
            if pinned.get(field) != want.get(field):
                bad.append("the pinned %s is not the live one" % field)
        pin_by = {r["task_id"]: r for r in pinned.get("tasks") or []}
        want_by = {r["task_id"]: r for r in want["tasks"]}
        for key in sorted(set(pin_by) | set(want_by)):
            if key not in pin_by:
                bad.append("%s is missing from the package" % key)
            elif key not in want_by:
                bad.append("%s is in the package but does not derive" % key)
            elif pin_by[key] != want_by[key]:
                bad.append("%s is not the live task" % key)
        if [r["task_id"] for r in pinned.get("tasks") or []] \
                != [r["task_id"] for r in want["tasks"]]:
            bad.append("the packaged tasks are out of their derived order")
        if not bad:
            bad.append("the package differs from the live derivation")
    for kind in sorted({t["kind"] for t in ctx["tasks"]}):
        shipped = os.path.join(out_dir, "prompt_prefix_%s.txt" % kind)
        if not os.path.isfile(shipped) \
                or K._read(shipped) != _prompt_prefix(ctx["suffix"], kind):
            bad.append("the shipped %s prefix is not the live one" % kind)
    return bad


def prompt_order_problems(run_dir):
    return _prompt_order_problems(_default(run_dir))


def _prompt_order_problems(ctx):
    """The check the SEQ 1371 build did not have. -> [problems]

    Trusted instructions ABOVE the boundary, untrusted data below it, and no
    group prompt carrying the singular one-item role.
    """
    bad, boundary = [], _boundary_at(ctx["suffix"])
    for task in ctx["tasks"]:
        text, where = _blind_prompt(ctx, task), task["task_id"]
        cut = text.find(boundary)
        if cut < 0:
            bad.append("%s: the live boundary is missing" % where)
            continue
        for mark in ("[ROLE]", "[RULES]", "[OUTPUT]", "[A4 HARD REVIEW TASK]",
                     "[A4 HARD REVIEW OUTPUT]"):
            at = text.find(mark)
            if at < 0:
                bad.append("%s: %s is missing" % (where, mark))
            elif at > cut:
                bad.append("%s: %s sits below the boundary, so the call is "
                           "told its own task is data" % (where, mark))
        if text.find(C.INJECTION_CONTROL) < cut:
            bad.append("%s: the injection control precedes the boundary"
                       % where)
        if text.rfind("[INPUT]") < cut:
            bad.append("%s: the data does not follow the boundary" % where)
        if task["kind"] == "group" and C.ONE_ITEM_ROLE in text:
            bad.append("%s: a group prompt carries the singular one-item role"
                       % where)
        if not text.startswith(_prompt_prefix(ctx["suffix"], task["kind"])):
            bad.append("%s: the instruction block is not the live prefix"
                       % where)
    return bad


def preflight(out_dir, run_dir):
    """The one gate before any hard-review call is ever made."""
    bad = package_problems(out_dir, run_dir)
    if any(b.startswith("the tasks no longer derive") for b in bad):
        return {"ok": False, "problems": bad, "manifest": None}
    return _preflight(_default(run_dir), out_dir)


def _preflight(ctx, out_dir):
    problems = list(_package_problems(ctx, out_dir))
    problems += _prompt_order_problems(ctx)
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
    if order != _canonical_of(ctx):
        problems.append("the pinned call order is not the derived one")
    if doc["budget"]["worst_case_after"] > ctx["ceiling"]:
        problems.append("the worst case would break the global ceiling %d"
                        % ctx["ceiling"])
    return {"ok": not problems, "problems": problems, "manifest": doc}


# ------------------------------------------------------- the run lifecycle --
# Codex SEQ 1372 D. The proof, receipt, record and fixed-child PATTERN is the
# A4 owner's, reused rather than reinvented; only the call identity differs -
# a hard-review call is (task, blind, attempt), not one packet id. Nothing here
# re-implements semantic validation: `read_reply` above is the only reader.

NO_ANSWER = K.NO_ANSWER
RETRYABLE = K.RETRYABLE


def expected_receipt(out_dir, pkg_dir, evidence_dir, attempt, labels,
                     parent=None):
    return _expected_receipt(_default(evidence_dir), out_dir, pkg_dir, attempt,
                             labels, parent)


def _expected_receipt(ctx, out_dir, pkg_dir, attempt, labels, parent=None):
    """THE typed expectation. Used to WRITE a receipt and to CHECK one."""
    by_label = _by_label_of(ctx)
    man = os.path.join(pkg_dir, MANIFEST_NAME)
    return collections.OrderedDict([
        ("run_id", os.path.basename(os.path.abspath(out_dir))),
        ("door", DOOR), ("attempt", attempt),
        ("allowed", list(labels)),
        ("parent", parent),
        ("transport", K._transport_block()),
        ("manifest_sha256", INV.sha_file(man) if os.path.isfile(man) else None),
        ("derived_from", ctx["derived_from"]),
        ("prompts", collections.OrderedDict(
            (lab, K._sha(_blind_prompt(ctx, by_label[lab][0])))
            for lab in labels)),
        ("states", [])])


def _write_receipt(ctx, out_dir, pkg_dir, attempt, labels, parent=None):
    receipt = _expected_receipt(ctx, out_dir, pkg_dir, attempt, labels, parent)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    # WRITE-ONCE through the transport's own owner (Codex SEQ 1488/1492)
    K.RT.write_new(os.path.join(out_dir, RECEIPT_NAME),
                   json.dumps(receipt, indent=1))
    return receipt


def _expected_for(ctx, out_dir, pkg_dir, receipt):
    """What THIS run's receipt must be, derived from canon and the parent."""
    attempt = receipt.get("attempt")
    if attempt == 1:
        return _expected_receipt(ctx, out_dir, pkg_dir, 1, _canonical_of(ctx),
                                 None), []
    if attempt != MAX_ATTEMPTS:
        return None, ["attempt %r is outside 1..%d" % (attempt, MAX_ATTEMPTS)]
    pdir = os.path.dirname(os.path.abspath(out_dir))
    pfin = os.path.join(pdir, FINALIZATION_NAME)
    if not os.path.isfile(pfin):
        return None, ["a child with no finalized parent is an orphan"]
    doc = K._load(pfin)
    parent = collections.OrderedDict([
        ("run_id", doc.get("run_id")),
        ("finalization_sha256", INV.sha_file(pfin))])
    return _expected_receipt(ctx, out_dir, pkg_dir, MAX_ATTEMPTS,
                             list(doc.get("retry") or []), parent), []


def receipt_problems(out_dir, pkg_dir, evidence_dir, receipt):
    return _receipt_problems(_default(evidence_dir), out_dir, pkg_dir, receipt)


def _receipt_problems(ctx, out_dir, pkg_dir, receipt):
    """Why this receipt is not the one the owner would have written."""
    if not isinstance(receipt, dict):
        return ["the receipt is not an object"]
    want, bad = _expected_for(ctx, out_dir, pkg_dir, receipt)
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


def _invocations(ctx, out_dir, labels, attempt):
    """The exact runnable calls: ordered scriptPath + args, never rebuilt.

    The bytes are written here, by the one renderer, so the operator cannot
    substitute a script of its own: the state's `scriptPath` must hash to
    exactly what this wrote.
    """
    by_label = _by_label_of(ctx)
    script_dir = os.path.join(out_dir, "scripts")
    os.path.isdir(script_dir) or os.makedirs(script_dir)
    out = []
    for label in labels:
        task, blind = by_label[label]
        text = _render_launcher(ctx, task, blind, attempt)
        path = os.path.join(script_dir, "%s.attempt%d.js"
                            % (label.replace("/", "_"), attempt))
        _atomic(path, text)
        out.append(collections.OrderedDict([
            ("label", label), ("attempt", attempt),
            ("scriptPath", path), ("args", None),
            ("script_sha256", K._sha(text))]))
    return out


def prepare_run(out_dir, pkg_dir, evidence_dir):
    """Publish THE canonical primary: exactly the frozen 70, in order."""
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        return {"ok": False, "problems": ["output directory is not fresh"],
                "invocations": []}
    bad = preflight(pkg_dir, evidence_dir)["problems"]
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    return _prepare_run(_default(evidence_dir), out_dir, pkg_dir)


def _prepare_run(ctx, out_dir, pkg_dir):
    """Publish THE canonical primary of ONE context: every call, in order,
    behind the one gate."""
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        return {"ok": False, "problems": ["output directory is not fresh"],
                "invocations": []}
    bad = _preflight(ctx, pkg_dir)["problems"]
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    labels = _canonical_of(ctx)
    _write_receipt(ctx, out_dir, pkg_dir, 1, labels)
    return {"ok": True, "problems": [],
            "invocations": _invocations(ctx, out_dir, labels, 1)}


def record_state(out_dir, state_path):
    """Append ONE unique official state to the receipt, atomically."""
    return K.record_state(out_dir, state_path)


def run_evidence(out_dir, pkg_dir, evidence_dir, receipt):
    return _run_evidence(_default(evidence_dir), out_dir, pkg_dir, receipt)


def _run_evidence(ctx, out_dir, pkg_dir, receipt):
    """THE run-level proof. -> {label: (outcome, why, text)}, problems

    ORDER IS THE LAW HERE, exactly as in the A4 owner: every COMMON check runs
    before anything branches on the agent row state, so a hand-written file can
    never earn the one paid retry without first being proved official.
    """
    by_label = _by_label_of(ctx)
    pinned = {}
    man = os.path.join(pkg_dir, MANIFEST_NAME)
    if os.path.isfile(man):
        pinned = {r["task_id"]: r for r in K._load(man)["tasks"]}
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

        # ---- COMMON CHECK 1: an official state of the frozen session
        session_dir, session_id = AUD._official_location(state)
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
        if label not in by_label:
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
        task, blind = by_label[label]

        # ---- COMMON CHECK 2: the reviewed BASE launcher, then THIS attempt's
        base = _render_launcher(ctx, task, blind, 1)
        want_key = "blind%d_script_sha256" % blind
        if pinned.get(task["task_id"], {}).get(want_key) not in (None,
                                                                 K._sha(base)):
            bad.append("the manifest pins a different base launcher for this "
                       "call")
        want_script = _render_launcher(ctx, task, blind, attempt)
        if doc.get("script") != want_script:
            bad.append("the state did not run the pinned launcher bytes")
        sp = doc.get("scriptPath")
        if sp is not None:
            if not (isinstance(sp, str) and os.path.isfile(sp)):
                bad.append("scriptPath %r is not a readable file" % sp)
            elif INV.sha_file(sp) != K._sha(want_script):
                bad.append("the scriptPath bytes are not the pinned launcher")

        # ---- COMMON CHECK 3: the exact returned object identity
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

        # ---- ONLY NOW may the row state decide anything
        if row.get("state") == "done":
            if row.get("agentId") in agents:
                bad.append("agent id %r is reused" % row.get("agentId"))
            agents.add(row.get("agentId"))
            final, complete, why = K._official_proof(state,
                                                     _blind_prompt(ctx, task))
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
            out[label] = ("proved", "", complete)     # only COMPLETE is parsed
            continue

        if row.get("state") == "error":
            bad += AUD._rejection(row, K.AGENT_TYPE, K.EFFORT)
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


def finalize(out_dir, pkg_dir, evidence_dir):
    return _finalize(_default(evidence_dir), out_dir, pkg_dir)


def _finalize(ctx, out_dir, pkg_dir):
    """Raw first, then the run-level proof, then parse. One outcome per call.
    Raw bytes, proved answers and the finalization are written ONCE through
    the transport's own owner; an already stored answer counts only when its
    bytes equal the official text (the A4 owner's SEQ 1488/1489 law)."""
    receipt = K._load(os.path.join(out_dir, RECEIPT_NAME))
    attempt = receipt.get("attempt")
    by_label = _by_label_of(ctx)
    raw_dir = os.path.join(out_dir, "raw")
    os.path.isdir(raw_dir) or os.makedirs(raw_dir)

    # ---- PAID BYTES FIRST, before any receipt, identity or parse check.
    harvested, mismatch = [], collections.OrderedDict()
    for state in receipt.get("states") or []:
        run_id = (os.path.splitext(os.path.basename(state))[0]
                  if isinstance(state, str) else "unreadable")
        try:
            doc = json.loads(K._read(state))
            got = K.direct_result(doc)
        except Exception:                             # noqa: BLE001 - by design
            doc, got = None, None
        rows = [r for r in ((doc if isinstance(doc, dict) else {})
                            .get("workflowProgress") or [])
                if isinstance(r, dict) and r.get("type") == "workflow_agent"]
        label = rows[0].get("label") if len(rows) == 1 else None
        for n, text in enumerate([got.get("text")] if got else []):
            if not isinstance(text, str):
                continue
            name = "%s.%03d" % (run_id, n)
            path = os.path.join(raw_dir, K.RT._raw_filename(name))
            same = K._stored_matches(path, text)
            if same is None:
                K.RT.save_raw(text, raw_dir, name)
            elif same is False:
                mismatch[label or run_id] = ("the stored raw answer %s is not "
                                             "the official returned text"
                                             % os.path.basename(path))
            harvested.append(os.path.basename(path))

    receipt_bad = _receipt_problems(ctx, out_dir, pkg_dir, receipt)
    allowed = list(receipt.get("allowed") or [])

    # A receipt fault preserves raw and stops everything else: no parse, no
    # credit, no child.
    if receipt_bad:
        problems, outcomes = [], collections.OrderedDict(
            (lab, ("unproved", "the receipt is not the owner's"))
            for lab in allowed)
    else:
        proved, problems = _run_evidence(ctx, out_dir, pkg_dir, receipt)
        outcomes = collections.OrderedDict()
        for label, (state, why, text) in proved.items():
            if state != "proved" or label in mismatch:
                outcomes[label] = (state, why) if state != "proved" \
                    else ("unproved", mismatch[label])
                continue
            path = os.path.join(raw_dir, "%s.attempt%s.proved.json"
                                % (label.replace("/", "_"), attempt))
            same = K._stored_matches(path, text)
            if same is None:
                K.RT.write_new(path, text)
            elif same is False:
                mismatch[label] = ("the stored proved answer %s is not the "
                                   "official returned text"
                                   % os.path.basename(path))
                outcomes[label] = ("unproved", mismatch[label])
                continue
            _obj, bad = _read_reply(ctx, text, by_label[label][0])
            outcomes[label] = ("valid", "") if not bad \
                else ("invalid_response", bad[0])
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
           ("valid", "invalid_response", "transport_no_answer", "unproved",
            "missing")])

    # ---- THE CHILD GATE. A child may only follow a COMPLETE, clean primary.
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
        ("receipt_sha256", INV.sha_file(os.path.join(out_dir, RECEIPT_NAME))),
        ("manifest_sha256", receipt.get("manifest_sha256")),
        ("derived_from", receipt.get("derived_from")),
        ("harvested_raw", harvested),
        ("primary_complete", complete),
        ("problems", receipt_bad + problems),
        ("outcomes", [[lab, o, w] for lab, (o, w) in outcomes.items()]),
        ("ledger", ledger),
        ("budget", _budget_after(ctx, attempt, len(allowed))),
        ("retry", retry)])
    # WRITE-ONCE: a second closeout of the same run is refused here
    K.RT.write_new(os.path.join(out_dir, FINALIZATION_NAME),
                   json.dumps(doc, indent=1))

    child = _publish_child(ctx, out_dir, pkg_dir, doc)
    if child:
        doc["child"] = child
    return doc


def _budget_after(ctx, attempt, scheduled):
    """The durable budget line for THIS attempt. Exact, never estimated."""
    before = ctx["before"]
    primaries = len(ctx["tasks"]) * len(BLINDS)
    spent = primaries + scheduled if attempt == MAX_ATTEMPTS else scheduled
    return collections.OrderedDict([
        ("ledger_before", before), ("this_attempt", scheduled),
        ("spent_so_far", spent), ("ledger_after", before + spent),
        ("frozen_primaries", primaries),
        ("worst_case_total", primaries * MAX_ATTEMPTS),
        ("global_ceiling", ctx["ceiling"]),
        ("within_ceiling", before + primaries * MAX_ATTEMPTS
         <= ctx["ceiling"])])


def _publish_child(ctx, out_dir, pkg_dir, doc):
    """At most ONE parent-bound child, published here, and RUNNABLE.

    The operator never reconstructs a script or a label: the exact validated
    invocations come back from the same renderer and receipt owner.
    """
    labels = list(doc.get("retry") or [])
    if not labels or doc.get("attempt") != 1 \
            or not doc.get("primary_complete"):
        return None
    child_dir = os.path.join(out_dir, "retry")
    if os.path.isdir(child_dir) and os.listdir(child_dir):
        return None
    _write_receipt(ctx, child_dir, pkg_dir, MAX_ATTEMPTS, labels,
                   parent=collections.OrderedDict([
                       ("run_id", doc["run_id"]),
                       ("finalization_sha256", INV.sha_file(
                           os.path.join(out_dir, FINALIZATION_NAME)))]))
    receipt = K._load(os.path.join(child_dir, RECEIPT_NAME))
    bad = _receipt_problems(ctx, child_dir, pkg_dir, receipt)
    if bad:                                   # never hand back an unlawful child
        return None
    return {"dir": child_dir, "problems": [],
            "invocations": _invocations(ctx, child_dir, labels, MAX_ATTEMPTS)}
