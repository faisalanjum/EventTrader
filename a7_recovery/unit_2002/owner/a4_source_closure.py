# -*- coding: utf-8 -*-
"""THE SOURCE-ONLY KEY CLOSURE (Codex SEQ 2000).

`build_kfields_hard_review` owns the ONE hard-review lifecycle - prompt,
manifest, package identity, receipt, official-state proof, raw-first
write-once finalizer, parser, invalid-only child, no third attempt - over a
small private context (Codex SEQ 1492 item B). `build_kfields_final` owns the
final adjudication, the materializer, the signing gate, the signer and the
lock. This module supplies the source-only context to those owners and nothing
else. It is the exact pattern `build_kfields_hard_review_targeted` already
uses, over this door's population instead of the corrected-inventory diff.

  * the population is derived from the PROVED INITIAL SHARDS: every event whose
    own reply left something unresolved - an open issue, a group it returned
    null, or a row the locked materializer flagged as a record-kind conflict.
    Never a literal list, never caller-supplied ids, and never a judgment about
    the flags' text: no reason word is read anywhere in this module.
  * one task per affected event, carrying ALL of that event's located rows, so
    every flag of that event is credited exactly once and no row is reviewed by
    two tasks (`coverage_problems`' own rule).
  * each task is read by exactly the owner's two independent blind Sonnet
    calls, whose instructions come from `HR._prompt_prefix` - which serves
    `C.ONE_ITEM_ROLE` for an item and `HR._GROUP_ROLE` for a group, so the
    canonical target-scope instruction the initial key prefix omitted is
    present in the closure instructions (Codex SEQ 2000 item 1).
  * the proved readings are then handed to the existing final adjudication as
    LEADS, through the locked owner's own `event_leads` seam; the final key is
    settled by this door's isolated non-Sonnet key role, never by a reviewer
    and never by an exposed parent session.

NO MODEL IS CALLED by this module and nothing here signs, grades or decides a
meaning. It prepares and it proves.
"""
import collections
import contextlib
import functools
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCE_OWNER = os.path.join(
    os.path.dirname(os.path.dirname(_HERE)), "unit_1997", "owner")
for _p in (_HERE, _SOURCE_OWNER):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import a4_source_key as SK                                        # noqa: E402

F = SK.F
HR = SK.HR
K = SK.K
C = SK.C
INV = SK.INV
RT = SK.RT

DOOR = "a4_source_only_key_closure_2000"
ORIGIN = "source_only_key_closure"
SUFFIX = SK.SUFFIX
AUTHORITY = ("Codex SEQ 2000: complete and prove the source-only key-closure "
             "connection on the existing owners, without model calls")
STEP = "live Step 1 A4 - the source-only key closure"

#: the initial collection this closure closes. It is READ as preserved
#: evidence and never written, appended to or re-finalized.
INITIAL_RUN = os.path.join(os.path.dirname(SK.PKG_DIR),
                           "source_only_1997_collect")
#: this phase's own package, beside the initial one and never inside it
PKG_DIR = os.path.join(K._X, "kfields_key_a4", "closure_2000")
MANIFEST_NAME = HR.MANIFEST_NAME
PREFIX_ITEM = "prompt_prefix_item.txt"
PREFIX_GROUP = "prompt_prefix_group.txt"


# ------------------------------------------------- the affected population --
@functools.lru_cache(maxsize=None)
def _initial():
    """The proved initial shards and their exact raw texts. READ ONLY.

    Through the source owner's own resume interface, so this module can never
    disagree with it about what a proved result is.
    """
    shards, raws, bad = SK.accepted_shards(INITIAL_RUN, package=SK.PKG_DIR)
    if bad:
        raise ValueError("the initial collection does not read back: %s"
                         % bad[:3])
    return shards, raws


@functools.lru_cache(maxsize=None)
def _conflicts():
    """{packet_id: the locked materializer's own record-kind conflict row}.

    THE OWNER DECIDES IT. `proposed_record_kind` and `final_outcome` are two
    different vocabularies; comparing them here would invent a crosswalk, and
    `F.materialize` already publishes the answer.
    """
    shards, _raws = _initial()
    _key, sidecar, problems = SK.materialize(shards)
    if problems:
        raise ValueError("the initial collection does not materialize: %s"
                         % problems[:3])
    return collections.OrderedDict(
        (m["packet_id"], m) for m in sidecar["record_kind_conflicts"])


def unresolved(source_id=None):
    """Every STILL-OPEN structured outcome of the initial replies, in order.

    Three kinds, each a field of the locked reply schema or of the locked
    materializer's own accounting - never a reading of any sentence:

      open_issue        the reply's own claim that something blocks a safe
                        final answer, with its 1-based index in that reply;
      unsettled_group   a group the reply returned `null` for;
      record_kind_conflict  a row the locked materializer flagged.

    An abstention is NOT one of them: the frozen inventory deliberately carries
    negative and lawful-abstention controls (`SK.unresolved_outcomes`).
    """
    shards, raws = _initial()
    conflicts = _conflicts()
    by = {t["source_id"]: t for t in SK.tasks()}
    out = []
    for task in SK.tasks():
        sid = task["source_id"]
        if source_id is not None and sid != source_id:
            continue
        shard = shards.get(sid)
        if shard is None:
            continue
        members = list(by[sid]["groups"].values())
        for n, g in enumerate(shard.get("groups") or []):
            if g.get("members_are_one_fact") is None:
                out.append(collections.OrderedDict([
                    ("source_id", sid), ("kind", "unsettled_group"),
                    ("index", n + 1),
                    ("members", list(members[n]) if n < len(members) else [])]))
        for n, _issue in enumerate(shard.get("open_issues") or []):
            out.append(collections.OrderedDict([
                ("source_id", sid), ("kind", "open_issue"), ("index", n + 1),
                ("members", [])]))
        for n, packet in enumerate(task["rows"]):
            if packet in conflicts:
                out.append(collections.OrderedDict([
                    ("source_id", sid), ("kind", "record_kind_conflict"),
                    ("index", n + 1), ("members", [packet])]))
    return out


#: recorded review QUESTIONS about a source-only reply, as DATA. The code below
#: never reads a source id, a word or a note out of them: it re-measures the
#: bytes each one names and refuses the finding if they moved.
FINDINGS_FILE = os.path.join(_HERE, "source_only_findings.json")


@functools.lru_cache(maxsize=None)
def findings():
    """Every recorded finding whose named bytes still measure as recorded.

    A finding is a review QUESTION, not a correction. It is admitted only when
    its own raw reply, its executed script and the prompt this door derives all
    hash to exactly what the record names, so a finding can never be pointed at
    bytes it was not written from. -> (admitted, problems)
    """
    if not os.path.isfile(FINDINGS_FILE):
        return (), ()
    doc = K._load(FINDINGS_FILE)
    by = {t["source_id"]: t for t in SK.tasks()}
    admitted, problems = [], []
    for row in doc["findings"]:
        sid, fid = row["source_id"], row["finding_id"]
        task = by.get(sid)
        if task is None:
            problems.append("%s: %s is not a scheduled event" % (fid, sid))
            continue
        raw = os.path.join(INITIAL_RUN, "raw", sid + ".attempt1.proved.json")
        script = os.path.join(INITIAL_RUN, "scripts", sid + ".attempt1.js")
        bad = []
        for name, got in (
                ("raw_sha256",
                 K._sha(K._read(raw)) if os.path.isfile(raw) else None),
                ("script_sha256",
                 INV.sha_file(script) if os.path.isfile(script) else None),
                ("prompt_sha256", K._sha(SK.prompt(task)))):
            if got != row[name]:
                bad.append("%s: %s is %s, not the recorded %s"
                           % (fid, name, got, row[name]))
        problems += bad
        if not bad:
            admitted.append(collections.OrderedDict(row))
    return tuple(admitted), tuple(problems)


def affected():
    """The source ids that owe a reading, in frozen inventory order.

    Two derived reasons, unioned ONCE so no event is read twice:
      * its own reply left something unresolved, or
      * a recorded, hash-bound finding raises a question about that reply.
    An event with neither is NOT added; adding it would manufacture work.
    """
    owed = {u["source_id"] for u in unresolved()}
    owed |= {f["source_id"] for f in findings()[0]}
    return [t["source_id"] for t in SK.tasks() if t["source_id"] in owed]


def tasks():
    """One task per affected event, carrying ALL of that event's rows.

    Kind is the locked owner's own distinction, decided by the population and
    not by a caller: one located row is an `item` task and reads the singular
    role; several are a `group` task and read the plural one.
    """
    by = {t["source_id"]: t for t in SK.tasks()}
    out = []
    for n, sid in enumerate(affected()):
        rows = list(by[sid]["rows"])
        out.append(collections.OrderedDict([
            ("task_id", "sokc-%03d" % n),
            ("kind", "item" if len(rows) == 1 else "group"),
            ("origin", ORIGIN), ("members", rows)]))
    return out


def population_problems(built):
    """The population is exactly the affected events, once each, in order.

    Every check is one-to-one against a derived expectation; none of them is a
    threshold, a sample or a literal.
    """
    by = {t["source_id"]: t for t in SK.tasks()}
    want = [list(by[sid]["rows"]) for sid in affected()]
    bad = []
    if [t["members"] for t in built] != want:
        bad.append("the tasks are not the affected events' complete rows in "
                   "frozen order")
    if [t["task_id"] for t in built] != ["sokc-%03d" % n
                                         for n in range(len(want))]:
        bad.append("the task ids are not the derived ones")
    if any(t["origin"] != ORIGIN for t in built):
        bad.append("a task is not a source-only closure task")
    for t in built:
        if t["kind"] != ("item" if len(t["members"]) == 1 else "group"):
            bad.append("%s: kind %r does not match its %d members"
                       % (t["task_id"], t["kind"], len(t["members"])))
    covered = [k for t in built for k in t["members"]]
    if len(set(covered)) != len(covered):
        bad.append("a row is reviewed by more than one task")
    items = SK.items()
    stray = [k for k in covered if k not in items]
    if stray:
        bad.append("a task names an unscheduled row: %s" % stray[:3])
    # every still-open outcome AND every admitted finding must be carried by
    # exactly one task, and nothing else may be
    admitted, finding_problems = findings()
    bad += ["a recorded finding is refused: %s" % p for p in finding_problems]
    owed = {u["source_id"] for u in unresolved()}
    owed |= {f["source_id"] for f in admitted}
    got = {items[k]["source_id"] for k in covered}
    if got != owed:
        bad.append("the covered events are not the events that owe a reading "
                   "(missing %s, extra %s)"
                   % (sorted(owed - got)[:3], sorted(got - owed)[:3]))
    return bad


# ------------------------------------------------------------ the context --
def _initial_evidence():
    """THE preserved initial collection, by path and hash. Never shown to a
    call: it is provenance for the package, not input to a reviewer."""
    return collections.OrderedDict([
        ("run_dir", INITIAL_RUN),
        ("receipt_sha256", INV.sha_file(
            os.path.join(INITIAL_RUN, K.RECEIPT_NAME))),
        ("finalization_sha256", INV.sha_file(
            os.path.join(INITIAL_RUN, K.FINALIZATION_NAME))),
        ("raw_tree", F.raw_tree(INITIAL_RUN))])


def _derived_from():
    return collections.OrderedDict([
        ("key_owner_sha256", INV.sha_file(K.__file__.rstrip("c"))),
        ("hard_review_owner_sha256", INV.sha_file(HR.__file__.rstrip("c"))),
        ("final_owner_sha256", INV.sha_file(F.__file__.rstrip("c"))),
        ("source_key_owner_sha256", INV.sha_file(SK.__file__.rstrip("c"))),
        ("closure_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "a4_source_closure.py"))),
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("source_key_manifest_sha256", K._sha(json.dumps(SK.manifest()))),
        ("contract_package_sha256", INV.sha_file(C.package_path(SUFFIX))),
        ("initial_collection", _initial_evidence()),
        ("affected_events", affected())])


def ledger_before():
    """MEASURED: this sample's own A3 spend plus what the initial collection's
    own finalizations actually scheduled. The same shape `HR._ledger_before`
    uses, read from THIS door's run instead of the historical one."""
    spent = 0
    for base in (INITIAL_RUN, os.path.join(INITIAL_RUN, "retry")):
        fin = os.path.join(base, K.FINALIZATION_NAME)
        if os.path.isfile(fin):
            spent += K._load(fin)["ledger"]["scheduled"]
    return K.ledger_before() + spent


def _ctx():
    """THE complete package context this module serves."""
    return {"items": SK.items(), "tasks": tasks(), "suffix": SUFFIX,
            "derived_from": _derived_from(),
            "before": ledger_before(), "ceiling": HR.GLOBAL_CEILING,
            "authority": AUTHORITY, "step": STEP}


# --------------------------------- the hard-review lifecycle, unchanged -----
def prompt_prefix(kind):
    return HR._prompt_prefix(SUFFIX, kind)


def blind_prompt(task):
    return HR._blind_prompt(_ctx(), task)


def render_launcher(task, blind, attempt=1):
    return HR._render_launcher(_ctx(), task, blind, attempt)


def canonical_calls():
    return HR._canonical_of(_ctx())


def by_label():
    return HR._by_label_of(_ctx())


def read_reply(text, task):
    return HR._read_reply(_ctx(), text, task)


def manifest():
    """The complete manifest; the population is proved first. Writes nothing."""
    ctx = _ctx()
    bad = population_problems(ctx["tasks"])
    if bad:
        raise ValueError("population refused: %s" % bad[:3])
    return HR._manifest(ctx)


def build(out_dir):
    """Write the frozen package ONCE. Launches nothing, calls nothing."""
    doc = manifest()
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    text = json.dumps(doc, indent=1)
    RT.write_new(os.path.join(out_dir, MANIFEST_NAME), text)
    RT.write_new(os.path.join(out_dir, PREFIX_ITEM), prompt_prefix("item"))
    RT.write_new(os.path.join(out_dir, PREFIX_GROUP), prompt_prefix("group"))
    doc["manifest_sha256"] = K._sha(text)
    return doc


def package_problems(pkg_dir):
    ctx = _ctx()
    bad = population_problems(ctx["tasks"])
    if bad:
        return bad
    return HR._package_problems(ctx, pkg_dir)


def prompt_order_problems():
    return HR._prompt_order_problems(_ctx())


def preflight(pkg_dir=None):
    return HR._preflight(_ctx(), pkg_dir or PKG_DIR)


def expected_receipt(out_dir, pkg_dir=None, attempt=1, labels=None,
                     parent=None):
    ctx = _ctx()
    return HR._expected_receipt(ctx, out_dir, pkg_dir or PKG_DIR, attempt,
                                labels if labels is not None
                                else HR._canonical_of(ctx), parent)


def receipt_problems(out_dir, receipt, pkg_dir=None):
    return HR._receipt_problems(_ctx(), out_dir, pkg_dir or PKG_DIR, receipt)


def prepare_run(out_dir, pkg_dir=None):
    """THE ONE public door: the whole package must rebuild identically and
    pass the shared gate, then the shared receipt owner publishes exactly the
    frozen calls, in order. It launches nothing."""
    pkg_dir = pkg_dir or PKG_DIR
    bad = package_problems(pkg_dir)
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    return HR._prepare_run(_ctx(), out_dir, pkg_dir)


record_state = HR.record_state


def run_evidence(out_dir, receipt, pkg_dir=None):
    return HR._run_evidence(_ctx(), out_dir, pkg_dir or PKG_DIR, receipt)


def finalize(out_dir, pkg_dir=None):
    return HR._finalize(_ctx(), out_dir, pkg_dir or PKG_DIR)


# ---------------------------------- the proved readings and what they feed --
def readings(run_dir, pkg_dir=None):
    """-> ({call label: (state, why, RAW text)}, [problems])

    THE EXISTING OWNERS ONLY: the run's own validated receipt, then its
    run-level evidence, then this context's own parser. Nothing is invented and
    no reading is repaired; a call that is not there stays MISSING and a reply
    the parser rejects stays INVALID.
    """
    pkg_dir = pkg_dir or PKG_DIR
    ctx = _ctx()
    by = HR._by_label_of(ctx)
    problems = []
    if not os.path.isfile(os.path.join(run_dir, K.RECEIPT_NAME)):
        return collections.OrderedDict(), ["%s carries no %s"
                                           % (run_dir, K.RECEIPT_NAME)]
    # THE PRIMARY, THEN ITS LAWFUL INVALID-ONLY CHILD. First VALID wins, so a
    # successful primary is never displaced by a later attempt and a child that
    # answers an already-valid label cannot serve it twice. The same order the
    # locked owner uses for its own two sources.
    best = collections.OrderedDict()
    for base in (run_dir, os.path.join(run_dir, "retry")):
        rpath = os.path.join(base, K.RECEIPT_NAME)
        if not os.path.isfile(rpath):
            continue
        receipt = K._load(rpath)
        problems += HR._receipt_problems(ctx, base, pkg_dir, receipt)
        got, probs = HR._run_evidence(ctx, base, pkg_dir, receipt)
        problems += probs
        for label, (state, why, text) in got.items():
            if best.get(label, ("", "", None))[0] == "valid":
                continue                  # a served label is never re-served
            if state != "proved":
                best[label] = (state, why, None)
                continue
            _obj, bad = HR._read_reply(ctx, text, by[label][0])
            best[label] = (("invalid_response", "; ".join(bad[:2]), None)
                           if bad else ("valid", "", text))
    out = collections.OrderedDict()
    for label in HR._canonical_of(ctx):
        out[label] = best.get(
            label, ("missing", "no run of this stage carries it", None))
    return out, problems


def required_readings():
    """Every blind reading this closure owes, named by ITS OWN frozen task
    population. It is derived here, once, and NEVER from a later shard: a
    cleared final answer must not erase the review obligation."""
    return canonical_calls()


def reading_problems(run_dir=None, pkg_dir=None):
    """One named problem per owed reading that is not valid. An absent run is
    not silence - every owed reading is then reported missing."""
    if run_dir is None:
        return ["the hard-review reading %s is missing: no run of this stage "
                "carries it" % label for label in required_readings()]
    got, problems = readings(run_dir, pkg_dir)
    bad = ["the hard review reports: %s" % p for p in problems]
    for label in required_readings():
        state, why, _text = got.get(
            label, ("missing", "no run of this stage carries it", None))
        if state != "valid":
            bad.append("the hard-review reading %s is %s: %s"
                       % (label, state, why or "-"))
    return bad


def leads_by_source(got):
    """{source_id: the leads its own event's proved readings make}.

    THE READINGS ARE MEASURED OUTSIDE ANY SCOPE and handed in, because the
    reviewers are the tested Sonnet role while the key owner is this door's
    isolated non-Sonnet role: proving a Sonnet reading while the key role is
    bound would judge it against the wrong model identity.
    """
    items = SK.items()
    out = collections.OrderedDict()
    for task in tasks():
        found = []
        for blind in HR.BLINDS:
            label = HR.call_label(task["task_id"], blind)
            state, _why, text = got.get(label, ("missing", "", None))
            if state == "valid":
                found.append(collections.OrderedDict([
                    ("lead_id", label), ("origin", ORIGIN),
                    ("member_index", None), ("sha256", K._sha(text)),
                    ("reply", text)]))
        out[items[task["members"][0]]["source_id"]] = found
    return out


# ------------------------------ the closure final-adjudication instructions --
# THE INITIAL PROMPT IS NOT THE CLOSURE PROMPT, and swapping the lead owner
# alone could never connect them: `SK._scope` binds the locked final prompt to
# the INITIAL source-only one, which carries no lead block and no plural target
# scope, so a forwarded lead was never rendered (Codex SEQ 2001 item 1).
#
# The closure prompt below is composed from the SAME existing owners the locked
# final prompt uses, at this door's contract era. Two things differ from the
# initial one, and only two: the lead-reconciliation paragraph of the locked
# output card is NOT replaced (leads now exist, so the locked request is
# truthful), and the canonical plural target-scope owner is served beside the
# locked role. Nothing is copied, reworded or invented.
PAYLOAD_KEYS = ("menu", "event", "rows", "groups", "leads")

#: the source owner's OWN enumeration, captured once at import. The closure
#: scope rebinds `SK.prompt_problems` to the wrapper below, so the wrapper must
#: hold the original rather than look it up and call itself.
_SK_PROMPT_PROBLEMS = SK.prompt_problems


def closure_role():
    return F._ROLE + "\n\n" + HR._GROUP_ROLE


def closure_prefix():
    """The locked final prefix at this door's contract era, with the canonical
    target scope, and with the lead request left standing."""
    return (
        "[ROLE]\n%s\n\n" % closure_role()
        + "[RULES]\n%s\n\n" % C.role_rules("drafter", SUFFIX)
        + "[OUTPUT]\n%s\n\n" % C.one_item_output_section().rstrip()
        + "[THE GATE]\nThe `%s` gate, quoted exactly:\n\n%s\n\n"
        % (F.GOLD_ONLY[0], SK.BIR.gate_text().rstrip())
        + "[TAG RULES]\n%s\n\n" % SK.BIR.crosswalk_text().rstrip()
        + "[A4 FINAL TASK]\n%s\n\n" % F._task_section()
        + "[A4 FINAL OUTPUT]\n%s\n\n" % F._output_section()
        + "[BOUNDARY]\n%s\n\n" % HR._boundary_at(SUFFIX)
        + "%s\n\n" % C.INJECTION_CONTROL
        + "[INPUT]\n")


def closure_payload(task, by_source):
    """menu, event, rows, groups, then this event's proved readings LAST.

    The locked owner's own payload, called the way its caller does; the only
    thing supplied is which leads exist.
    """
    # The locked payload reads its items from the hard-review owner, whose own
    # door derives them from the A3 evidence a source-only key may not read.
    # The source owner already supplies the frozen items for the length of its
    # scope; this supplies the SAME items for the length of this ONE call, so
    # the payload works with or without that scope and nothing outlives it.
    real_leads, real_items = F.event_leads, HR._items
    F.event_leads = lambda _bound, t: list(by_source.get(t["source_id"], []))
    HR._items = lambda: SK.items()
    try:
        return F.payload(SK.bound(INITIAL_RUN, SK.PKG_DIR), task)
    finally:
        F.event_leads, HR._items = real_leads, real_items


def closure_prompt_problems(task, by_source):
    """EVERY model-visible byte of one closure prompt, enumerated.

    The locked door's own enumeration for the four source blocks, plus the one
    block it does not have: each lead must be exactly one of THIS event's
    proved readings, by hash, and nothing else may appear.
    """
    bad = list(_SK_PROMPT_PROBLEMS(task))
    data = closure_payload(task, by_source)
    want = {l["lead_id"]: l for l in by_source.get(task["source_id"], [])}
    got = data.get("leads") or []
    if [l.get("lead_id") for l in got] != list(want):
        bad.append("the leads are %s, not this event's proved readings %s"
                   % ([l.get("lead_id") for l in got], list(want)))
        return bad
    for lead in got:
        mine = want[lead["lead_id"]]
        if lead.get("reply") != mine["reply"] \
                or lead.get("sha256") != K._sha(mine["reply"]):
            bad.append("%s: the lead is not the proved reading it names"
                       % lead["lead_id"])
    return bad


@contextlib.contextmanager
def _prompt_scope(by_source):
    """One closure interpretation for every existing source-owner entry point.

    A request, its finalizer and its resume parser must see the same leads.
    Bind no role until the public owner enters its own scope, preserving the
    independent-role check before publication. Initial behavior is restored
    on exit; the preserved initial collection is never reinterpreted here.
    """
    saved = collections.OrderedDict(
        (name, getattr(SK, name)) for name in
        ("prompt", "prompt_prefix", "payload", "PAYLOAD_KEYS",
         "prompt_problems", "_scope", "read_shard", "role", "output_section"))

    def own_leads(task):
        return list(by_source.get(task["source_id"], []))

    @contextlib.contextmanager
    def scope(bind_role=False):
        with saved["_scope"](bind_role=bind_role):
            original = F.event_leads
            F.event_leads = lambda _bound, task: own_leads(task)
            try:
                yield
            finally:
                F.event_leads = original

    def read_shard(text, task):
        with scope():
            return F.read_shard(text, task, own_leads(task))

    SK.prompt_prefix = closure_prefix
    SK.payload = lambda task: closure_payload(task, by_source)
    SK.PAYLOAD_KEYS = PAYLOAD_KEYS
    SK.prompt = lambda task: (closure_prefix() + json.dumps(
        closure_payload(task, by_source), indent=1))
    SK.prompt_problems = lambda task: closure_prompt_problems(task, by_source)
    SK._scope = scope
    SK.read_shard = read_shard
    SK.role = closure_role
    SK.output_section = F._output_section
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(SK, name, value)


@contextlib.contextmanager
def _closure_scope(by_source):
    """The same binding when calling the locked final owner directly."""
    with _prompt_scope(by_source):
        with SK._scope(bind_role=True):
            yield


@contextlib.contextmanager
def final_scope(review_run, review_package, bind_role=False):
    """The final phase's proved inputs, budget and existing callable owners.

    Review evidence is checked before binding the non-Sonnet key role. Public
    source-owner doors bind that role themselves; direct F consumers request
    bind_role=True. No model, package or evidence is written by this scope.
    """
    got, run_problems = readings(review_run, review_package)
    owed = required_readings()
    bad = list(run_problems)
    bad += ["%s is %s" % (label, got.get(label, ("missing",))[0])
            for label in owed if got.get(label, ("missing",))[0] != "valid"]
    evidence = collections.OrderedDict()
    for base in (review_run, os.path.join(review_run, "retry")):
        receipt_path = os.path.join(base, K.RECEIPT_NAME)
        if not os.path.isfile(receipt_path):
            continue
        final_path = os.path.join(base, K.FINALIZATION_NAME)
        if not os.path.isfile(final_path):
            bad.append("the review attempt is not finalized: %s" % base)
            continue
        fin = K._load(final_path)
        scheduled = (fin.get("ledger") or {}).get("scheduled")
        if type(scheduled) is not int or scheduled != len(
                K._load(receipt_path)["allowed"]):
            bad.append("the review closeout count differs from its receipt")
        if fin.get("receipt_sha256") != INV.sha_file(receipt_path) \
                or fin.get("primary_complete") is not True or fin.get("problems"):
            bad.append("the review closeout is not complete and receipt-bound")
        evidence[base] = {"receipt_sha256": INV.sha_file(receipt_path),
                          "finalization_sha256": INV.sha_file(final_path)}
    if bad:
        raise ValueError("final source-key phase is not ready: %s" % bad)
    by_source = leads_by_source(got)
    prior = F.Bound(package=review_package, evidence=INITIAL_RUN,
                    hr=review_run, fix=None, events=None,
                    hr_package=review_package)
    before = F._ledger_before(prior)
    outcomes = {label: (state, why, text, ORIGIN)
                for label, (state, why, text) in got.items()}
    saved_sk = {name: getattr(SK, name)
                for name in ("manifest", "budget", "preflight", "_owners")}
    saved_f = {name: getattr(F, name)
               for name in ("required_readings", "_hard_outcomes", "_ledger_before")}

    def budget():
        result = saved_sk["budget"]()
        # The existing final owner schedules one signer after its event calls.
        planned = result["planned_key_calls"] + 1
        worst = planned * result["max_attempts_per_call"]
        result.update(before=before, planned_signer=1, planned_total=planned,
                      planned_note="the independent signature remains separately gated",
                      after_planned=before + planned, worst_case_total=worst,
                      worst_case_after=before + worst, package_ceiling=before + worst)
        return result

    def owners():
        result = saved_sk["_owners"]()
        result["source_only_closure_owner"] = INV.sha_file(__file__)
        result["source_only_closure_findings"] = INV.sha_file(FINDINGS_FILE)
        result["closure_review_manifest"] = INV.sha_file(
            os.path.join(review_package, MANIFEST_NAME))
        return result

    def manifest():
        result = saved_sk["manifest"]()
        result["counts"]["leads_shown"] = sum(map(len, by_source.values()))
        result["hard_review"] = {"package": review_package, "run": review_run,
                                  "owed": list(owed), "evidence": evidence}
        result["remaining_gates_in_order"] = [
            "orchestration approval for final source-only adjudication",
            "raw-first finalization and invalid-only retry through the existing owner",
            "independent signature and lock", "A5/A6 binding, then A7 grading"]
        return result

    def preflight(package):
        problems = (list(SK.package_problems(package)) + SK.population_problems()
                    + SK.source_problems() + SK.role_problems())
        path = os.path.join(package, SK.MANIFEST_NAME)
        if not os.path.isfile(path):
            return {"ok": False, "problems": problems, "manifest": None}
        doc = K._load(path)
        for task in SK.tasks():
            problems += SK.prompt_problems(task)
        if doc["capacity"]["at_or_over_transport_limit"]:
            problems.append("a final request is at or over the transport limit")
        if doc["budget"]["worst_case_after"] > SK.GLOBAL_CEILING:
            problems.append("the final phase would exceed its existing call ceiling")
        return {"ok": not problems, "problems": problems, "manifest": doc}

    served = lambda _bound: (dict(outcomes), list(run_problems))
    served.cache_clear = lambda: None
    try:
        SK.manifest, SK.budget, SK.preflight, SK._owners = (
            manifest, budget, preflight, owners)
        F.required_readings = lambda _bound: list(owed)
        F._hard_outcomes = served
        F._ledger_before = lambda _bound: before
        with _prompt_scope(by_source):
            with contextlib.ExitStack() as stack:
                if bind_role:
                    stack.enter_context(SK._scope(bind_role=True))
                yield {"readings": got, "by_source": by_source, "before": before}
    finally:
        for name, value in saved_sk.items():
            setattr(SK, name, value)
        for name, value in saved_f.items():
            setattr(F, name, value)


def signing_checks(run_dir=None, pkg_dir=None, key_run=None, key_package=None):
    """THE LOCKED SIGNING GATE over this door's closed key.

    The owed readings come from the FROZEN task population above, so a shard
    that no longer carries an open issue cannot make the obligation disappear.
    When a reading is absent or invalid the gate is given that fact and returns
    its own refusal unchanged; nothing here reports success on its behalf.
    """
    if key_run is not None:
        if key_package is None:
            raise ValueError("a final key run must name its own final package")
        try:
            with final_scope(run_dir, pkg_dir, bind_role=True):
                bound = SK.bound(key_run, key_package)
                bad = F.package_problems(key_package, bound)
                gate = ({"ok": False, "stops": bad, "counts": None} if bad
                        else F.signing_gate(key_run, bound))
        except ValueError as exc:
            gate = {"ok": False, "stops": [str(exc)], "counts": None}
        return dict(gate, owed_blind_readings=required_readings(),
                    run_problems=[], unresolved=unresolved())
    owed = required_readings()
    got, run_problems = ((collections.OrderedDict(), []) if run_dir is None
                         else readings(run_dir, pkg_dir))
    stops = reading_problems(run_dir, pkg_dir)
    outcomes = {label: (state, why, text, ORIGIN)
                for label, (state, why, text) in got.items()}
    # Without a final run, report the PRESERVED INITIAL settlements. Their
    # unresolved issues remain visible; this is not a final-key approval.
    with _closure_scope(leads_by_source(got)):
        real_readings = F.required_readings
        real_outcomes = F._hard_outcomes
        real_shards = F.accepted_shards
        shards, raws = _initial()
        F.accepted_shards = lambda *_a, **_k: (
            collections.OrderedDict(shards),
            collections.OrderedDict(raws), [])
        F.required_readings = lambda _bound: list(owed)
        # THE RUN-LEVEL ERRORS TRAVEL WITH THE READINGS. Handing the gate an
        # empty problem list hid a receipt or duplicate fault: the readings all
        # looked valid and `hard_reading_problems` had nothing to report, so a
        # run the owners had already refused could reach the signature
        # (Codex SEQ 2001 item 2). The gate now gets exactly what was measured.
        served = lambda _bound: (dict(outcomes),        # noqa: E731 - one expr
                                 list(run_problems))
        served.cache_clear = lambda: None              # the locked owner clears
        F._hard_outcomes = served
        try:
            gate = F.signing_gate(INITIAL_RUN, SK.bound(INITIAL_RUN, SK.PKG_DIR))
        finally:
            F.accepted_shards = real_shards
            F.required_readings = real_readings
            F._hard_outcomes = real_outcomes
    gate = dict(gate)
    gate["owed_blind_readings"] = owed
    gate["reading_problems"] = stops
    gate["run_problems"] = list(run_problems)
    gate["unresolved"] = unresolved()
    return gate


def limitations():
    """What this closure does NOT prove. Stated, never discovered later."""
    return [
        "A group task's `members_are_one_fact` answers whether ALL of that "
        "task's members state one underlying fact. It is NOT an answer about "
        "any smaller subset of them, and no accounting here reports it as one.",
        "No model has been called under this module. Every reading is either "
        "absent or supplied by a caller, and the signing gate refuses while "
        "any owed reading is absent or invalid.",
        "The closure prepares and proves a route. It performs no semantic "
        "adjudication, no signature and no grading; those remain later, "
        "separately approved calls.",
    ]
