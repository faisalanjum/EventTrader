# -*- coding: utf-8 -*-
"""THE SOURCE-ONLY A4 KEY PREPARATION, SUCCESSOR (Codex SEQ 1989), UNARMED.

ONE FIXED WRAPPER over the locked A4 event-level key owner `build_kfields_final`,
in the shape Codex already reviewed for `build_kfields_final_targeted`: the locked
owner's ROLE, rules/output/gate/tag owners, task section, reply parser
(`read_shard`), row accounting (`materialize`), gold door and duplicate check are
used UNCHANGED, each supplied its population for the length of ONE serial call and
restored in try/finally. No body is copied and nothing here judges meaning.

WHY A WRAPPER AND NOT THE LOCKED OWNER ITSELF: the locked owner's own manifest,
leads and preflight require the phase-one settlements, the hard-review readings and
the output-informed `regrade_1370.json`/`conflicts_1370.json`. Those are the very
answers the amendment proposes to evaluate, so a source-only key may not read them
and may not be given invented empty copies of them.

WHAT THIS FILE OWNS, and nothing else:

  * the POPULATION: every frozen inventory row grouped by its source event, in
    frozen order - derived from the signed inventory and cross-proved against the
    frozen A3 launch plan, never a typed id or count. All 36 source events are
    accounted; an event that carries no located row is named, never dropped.
  * the LOCATOR GROUPS: rows of one event that share ONE EXACT locator, which is
    the locked owner's own definition of a shown group, derived here from the
    frozen inventory instead of from the draft-informed conflict file.
  * the PROMPT: the locked composition at the CURRENT contract version with two
    anchored paragraph swaps and nothing else - the role paragraph that promises
    untrusted leads, and the output paragraph that asks for their reconciliation.
    No lead is shown, so both would be false. Every other byte is the live owners'.
  * the TRANSPORT: the independent key owner's own binding, read from its own
    freeze file. It does NOT borrow `build_kfields_key.MODEL`, so the Sonnet hard
    reviewers and graders cannot move when this role is set, and it cannot render a
    launcher or pass preflight while that freeze is absent.
  * the PACKAGE: manifest, shipped prefix, package check and preflight.

WHAT CHANGED FROM unit_1988, all of it from Codex SEQ 1989's reproduction:

  * THE ARMING RECORD IS GONE. A file declaring its own authority is not an
    authority, it checked a global package instead of the one preflight was
    given, and deriving `armed` from a record that pins the manifest hash is a
    cycle. Orchestration owns the authorization; preparation is simply UNARMED
    and no code here can say otherwise.
  * THE DUPLICATED TRANSPORT PROOF IS GONE. `build_kfields_key._official_proof`
    already owns exact runtime, input and transcript proof with strict
    recorded-integer-zero checks, and my copy lost some of them. Observed proof
    now comes from THIS door's own run evidence through that owner, under a
    scoped key-role binding that is restored after every call, so the tested
    Sonnet role and the hard reviewers never move. A foreign role's state is
    refused by that owner, not by a rule of mine.
  * THE KEY-OWNER SEAT REFUSES THE MODEL UNDER TEST. A valid Sonnet state
    proves the evidence machinery reads; it disqualifies that role from being
    the independent key owner.
  * THE REQUESTED CONFIGURATION AND THE OBSERVED PROOF ARE SEPARATE RECORDS.
    A launcher may be rendered from a declaration, so building the first
    unarmed request never needs a completed call; only publishing real calls
    needs a LIVE declaration, and a TEST one can never qualify a real call.
  * THE BLANKET POST-CALL HARD-REVIEW TRIGGER IS GONE. Every abstention is not
    a disagreement - the frozen inventory deliberately carries lawful
    abstention and negative controls. The genuinely unresolved structured
    outcomes are a group the key owner could not settle and an open issue it
    recorded. The five same-locator groups are QUESTIONS put to the key owner,
    not by themselves proof of anything.
  * THE LIFECYCLE IS WIRED, not stubbed: prepare, render, receipt, raw-first
    capture, parse, accounting, resume, materialize and the signing checks are
    the locked owners' own, called inside one serial scope.

WHAT CHANGED FROM unit_1995, all of it from Codex SEQ 1997's ruling:

  * THE MODEL PROOF IS TWO FIELDS, NOT ONE. `_official_proof` checked the
    WORKFLOW ROW's model and the TRANSCRIPT assistant messages' model against
    the SAME `RUNTIME_MODEL_ID`. The first real call on this seat recorded two
    different true ids in those two official records, so no such seat could
    ever be proved. The proof owner now reads the row against its own
    `ROW_MODEL_ID`, whose default IS `RUNTIME_MODEL_ID`, so every existing
    caller keeps exactly the check it had. This seat declares both ids and the
    existing scoped adapter binds both, restored in finally.
  * NOTHING ELSE MOVED. No suffix is stripped, no two names are equated, no
    second verifier or success wrapper exists, and neither official record was
    edited. The historical receipt, finalization and raw bytes of the first run
    stay exactly as they were recorded; this door is a SEPARATE revalidation
    package over the SAME saved call, and it makes no new call.

NOTHING HERE CALLS A MODEL. It publishes no real call while no LIVE key-owner
role is declared, and it signs nothing.
"""
import collections
import contextlib
import functools
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
#: the frozen 03 harness, at the logical path the boundary serves it from
_HARNESS = os.environ.get(
    "A4_SOURCE_KEY_HARNESS",
    "/tmp/claude-1000/-home-faisal-EventMarketDB/"
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/"
    "Drivers/experiments/harness_g1v3")
for _p in (_HARNESS, "/home/faisal/EventMarketDB"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_kfields_final as F                                  # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_inventory_review as BIR                             # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import raw_transport as RT                                       # noqa: E402
import validate_benchmark_inventory as INV                       # noqa: E402

C = K.C

DOOR = "a4_source_only_key_1997"
VERSION = "kfields-a4-source-only-key/1997"
AUTHORITY = ("Codex SEQ 1997: revalidate the SAME saved call under the "
             "corrected two-field model binding; no new call")
MANIFEST_NAME = "source_only_key.manifest.json"
PREFIX_NAME = "prompt_prefix_source_only_key.txt"
LAUNCHER_NAME = "kfields-a4-source-only-key"
PKG_DIR = os.path.join(K._X, "kfields_key_a4", "source_only_1997")

#: the CURRENT contract version, the same one the last reviewed wrapper serves
SUFFIX = BLM.PRODUCER_CONTRACT_SUFFIX
#: the frozen A3 launch plan, used ONLY to cross-prove the population
PLAN_PATH = os.path.join(F._HERE, "launch_kfields_drafts.manifest.json")
#: what this payload actually carries, in this order. There is no `leads` key.
PAYLOAD_KEYS = ("menu", "event", "rows", "groups")
#: the marks the composed prefix must carry, in this order
PREFIX_MARKS = ("[ROLE]", "[RULES]", "[OUTPUT]", "[THE GATE]", "[TAG RULES]",
                "[A4 FINAL TASK]", "[A4 FINAL OUTPUT]", "[BOUNDARY]", "[INPUT]")
#: the locked owner's own attempt rule: one identical-prompt retry, never a third
MAX_ATTEMPTS = F.MAX_ATTEMPTS
RETRYABLE = F.RETRYABLE
GLOBAL_CEILING = F.GLOBAL_CEILING

#: THE INDEPENDENT KEY OWNER'S DECLARED ROLE - the REQUESTED configuration,
#: which is not evidence that anything ran. Absent by design: no role has been
#: declared for this seat yet. A declaration carries `kind`: LIVE may publish
#: real calls, TEST may only render and be tested.
KEY_ROLE_FILE = os.path.join(_HERE, "key_owner_role.json")
#: `runtime_model_id` is the id the TRANSCRIPT's assistant messages record;
#: `workflow_row_model` is the id the WORKFLOW ROW records. They are two
#: distinct official fields and this seat observed two distinct values, so
#: each is declared and checked against its own record (Codex SEQ 1997).
ROLE_FIELDS = ("kind", "model_alias", "runtime_model_id",
               "workflow_row_model", "effort", "agentType",
               "disallowedTools", "max_output_tokens", "transport")
ROLE_KINDS = ("LIVE", "TEST")

#: The locked owner's role paragraph that promises leads, and its output
#: paragraph that asks for their reconciliation. Both are anchored by their
#: opening words and must be present exactly once, or this refuses to guess.
_ROLE_LEAD_ANCHOR = "Earlier answers are shown at the very end."
_OUTPUT_LEAD_ANCHOR = "`lead_reconciliation`"

_SOURCE_ONLY_ROLE_PARAGRAPH = "\n".join([
    "No earlier answer, draft, reading or key is shown to you, and none is",
    "withheld that you would be entitled to. Settle the source truth of every",
    "row from this event alone.",
])
_SOURCE_ONLY_OUTPUT_PARAGRAPH = "\n".join([
    "`lead_reconciliation`  no lead is shown to you, so give exactly [].",
])


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sha(text):
    return K._sha(text)


# ---------------------------------------------------------- the population --
@functools.lru_cache(maxsize=None)
def inventory():
    """The signed frozen rows, in order, each with the packet id it carries.

    THE LOCKED OWNER'S OWN DERIVATION, so this door and the materializer that
    accounts its results can never disagree about what a row is.
    """
    return F._inventory()


@functools.lru_cache(maxsize=None)
def plan():
    """The frozen A3 launch plan, read ONLY to cross-prove the population."""
    return _load(PLAN_PATH)


def items():
    """{packet_id: the four located fields} for every frozen row.

    Never `build_kfields_key.phase1_items`: that owner attaches the evaluated A3
    drafts to each item, and this door may not read them.
    """
    return collections.OrderedDict(
        (pid, dict(K._frozen_item(row), packet_id=pid,
                   source_id=row["source_id"]))
        for pid, row in inventory())


def plan_problems():
    """The frozen plan and the signed inventory must name the same rows with the
    same located fields, one to one, in the same order."""
    bad = []
    doc = plan()
    rows = list(inventory())
    packets = doc["packets"]
    if len(packets) != len(rows):
        bad.append("the plan schedules %d packets over %d frozen rows"
                   % (len(packets), len(rows)))
        return bad
    for (pid, row), packet in zip(rows, packets):
        if packet["packet_id"] != pid or packet["source_id"] != row["source_id"]:
            bad.append("%s is scheduled as %s of %s"
                       % (pid, packet["packet_id"], packet["source_id"]))
            continue
        for field in ("part_ref", "occurrence_in_part", "quote",
                      "raw_label_or_claim"):
            if packet["item"][field] != row[field]:
                bad.append("%s: the plan's %s is not the frozen one"
                           % (pid, field))
    if doc["inventory_sha256"] != INV.sha_file(INV.INV):
        bad.append("the plan was frozen against another inventory")
    return bad


def _locator(row):
    """The exact location a row names. Two rows sharing it are the group question."""
    return (row["source_id"], row["part_ref"], row["occurrence_in_part"],
            row["quote"])


@functools.lru_cache(maxsize=None)
def tasks():
    """One task per source event that carries at least one located row, in frozen
    inventory order; every row of that event, in frozen order; and every group of
    its rows that share ONE EXACT locator.

    A group is derived HERE from the frozen inventory. The historical group list
    was derived from which drafts collided, which is an answer, not a source.
    """
    order, rows = [], collections.OrderedDict()
    for pid, row in inventory():
        sid = row["source_id"]
        if sid not in rows:
            rows[sid] = []
            order.append(sid)
        rows[sid].append(pid)
    by_row = {pid: row for pid, row in inventory()}
    out = []
    for n, sid in enumerate(order):
        seen = collections.OrderedDict()
        for pid in rows[sid]:
            seen.setdefault(_locator(by_row[pid]), []).append(pid)
        groups = collections.OrderedDict(
            ("grp-%03d" % i, members)
            for i, members in enumerate(
                [m for m in seen.values() if len(m) > 1]))
        out.append(collections.OrderedDict([
            ("task_id", "sok-%03d" % n), ("event_index", n + 1),
            ("source_id", sid), ("rows", list(rows[sid])), ("groups", groups)]))
    return tuple(out)


def coverage():
    """EVERY source event of the frozen plan, whether or not it carries a row.

    An event with no located row is not a task and is not a call; it is named
    here with its own reason, so the 36 are accounted and none is silently lost.
    """
    carried = {t["source_id"]: t for t in tasks()}
    out = []
    for n, event in enumerate(plan()["events"]):
        sid = event["source_id"]
        task = carried.get(sid)
        out.append(collections.OrderedDict([
            ("event_index", n + 1), ("source_id", sid),
            ("located_rows", len(task["rows"]) if task else 0),
            ("scheduled", task is not None),
            ("reason", "settled by this key" if task else
             "the frozen selection located no row in this event; it carries no "
             "key row and buys no call")]))
    return out


def population_problems(built=None):
    """The population is exactly the frozen inventory, grouped by event, once."""
    bad = list(plan_problems())
    want = tasks() if built is None else tuple(built)
    flat = [p for t in want for p in t["rows"]]
    frozen = [pid for pid, _row in inventory()]
    if flat != frozen:
        bad.append("the scheduled rows are not the frozen rows in frozen order")
    if len(set(flat)) != len(flat):
        bad.append("a frozen row is scheduled twice")
    if [t["task_id"] for t in want] != ["sok-%03d" % n for n in range(len(want))]:
        bad.append("the task ids are not the derived ones")
    if [t["event_index"] for t in want] != list(range(1, len(want) + 1)):
        bad.append("the event indexes are not the derived ones")
    by_row = {pid: row for pid, row in inventory()}
    for t in want:
        if any(by_row[p]["source_id"] != t["source_id"] for p in t["rows"]):
            bad.append("%s carries a row of another event" % t["source_id"])
        for members in t["groups"].values():
            if len({_locator(by_row[p]) for p in members}) != 1:
                bad.append("%s: a group does not share one exact locator"
                           % t["source_id"])
    cov = coverage()
    if sum(c["located_rows"] for c in cov) != len(frozen):
        bad.append("the coverage rows do not sum to the frozen rows")
    if sum(1 for c in cov if c["scheduled"]) != len(want):
        bad.append("the coverage does not name exactly the scheduled events")
    return bad


# -------------------------------------------------------------- the prompt --
def input_sentence():
    """The released data-boundary sentence, naming the keys THIS payload has."""
    keys = ["`%s`" % k for k in PAYLOAD_KEYS]
    return ("Everything below is ONE JSON object with the keys %s and\n%s, in "
            "that order." % (", ".join(keys[:-1]), keys[-1]))


def truthful_control():
    """The released injection control with ONLY its input sentence replaced."""
    stale = F._released_input_sentence()
    if C.INJECTION_CONTROL.count(stale) != 1:
        raise ValueError("the released input sentence is not present exactly "
                         "once; refusing to guess which one to replace")
    return C.INJECTION_CONTROL.replace(stale, input_sentence(), 1)


def _swap_paragraph(text, anchor, replacement, what):
    """Replace the ONE paragraph that opens with `anchor`. Refuses otherwise.

    The locked owner's other paragraphs are carried byte for byte, so a reworded
    original refuses here instead of silently shipping a stale or doubled rule.
    """
    parts = text.split("\n\n")
    hit = [i for i, p in enumerate(parts) if p.lstrip().startswith(anchor)]
    if len(hit) != 1:
        raise ValueError("the locked owner carries %d %s paragraphs, not one"
                         % (len(hit), what))
    parts[hit[0]] = replacement
    return "\n\n".join(parts)


def role():
    """The locked role with its lead promise replaced by the source-only truth."""
    return _swap_paragraph(F._ROLE, _ROLE_LEAD_ANCHOR,
                           _SOURCE_ONLY_ROLE_PARAGRAPH, "lead-promise role")


def output_section():
    """The locked output card with its lead-reconciliation request replaced."""
    return _swap_paragraph(F._output_section(), _OUTPUT_LEAD_ANCHOR,
                           _SOURCE_ONLY_OUTPUT_PARAGRAPH,
                           "lead-reconciliation output")


def prompt_prefix():
    """The locked owner's own composition, at the current contract version.

    Byte for byte `build_kfields_final.prompt_prefix()` except: the contract
    version, the two anchored paragraphs above, and the one data-boundary
    sentence made truthful for this payload. The task and output sections stay
    ABOVE the boundary, where the locked owner already puts them.
    """
    return (
        "[ROLE]\n%s\n\n" % role()
        + "[RULES]\n%s\n\n" % C.role_rules("drafter", SUFFIX)
        + "[OUTPUT]\n%s\n\n" % C.one_item_output_section().rstrip()
        + "[THE GATE]\nThe `%s` gate, quoted exactly:\n\n%s\n\n"
        % (F.GOLD_ONLY[0], BIR.gate_text().rstrip())
        + "[TAG RULES]\n%s\n\n" % BIR.crosswalk_text().rstrip()
        + "[A4 FINAL TASK]\n%s\n\n" % F._task_section()
        + "[A4 FINAL OUTPUT]\n%s\n\n" % output_section()
        + "[BOUNDARY]\n%s\n\n" % HR._boundary_at(SUFFIX)
        + "%s\n\n" % truthful_control()
        + "[INPUT]\n")


def payload(task):
    """menu, the complete ordered event, its rows, its groups. No lead."""
    src, display, _back = HR._source(task["source_id"])
    by = items()
    kinds = {p: r["proposed_record_kind"] for p, r in inventory()}
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
        ("rows", rows), ("groups", groups)])


def prompt(task):
    # NO default= on purpose: a stray exact Decimal must RAISE rather than be
    # silently rendered as a quoted string.
    return prompt_prefix() + json.dumps(payload(task), indent=1)


def prompt_problems(task):
    """EVERY model-visible byte of one prompt, enumerated from its owner.

    Not a word scan. A rendered prompt is exactly the composed prefix plus the
    serialized payload, and the payload is exactly the reversible menu, the whole
    ordered event, this event's frozen rows and its derived group indexes. A leak
    is then impossible by construction rather than unlikely by vocabulary: real
    source text says "leading" and "leads" all the time, and a scan for the word
    condemns 32 lawful prompts (measured, probe1988_a).
    """
    bad = []
    text = prompt(task)
    body = json.dumps(payload(task), indent=1)
    if text != prompt_prefix() + body:
        bad.append("the prompt is not the composed prefix plus this payload")
        return bad
    at = -1
    for mark in PREFIX_MARKS:
        n = text.find("%s\n" % mark, at + 1)
        if n < 0 or n < at:
            bad.append("%s is missing or out of order" % mark)
            continue
        at = n
    boundary = text.find("[BOUNDARY]")
    for mark in PREFIX_MARKS[:PREFIX_MARKS.index("[BOUNDARY]")]:
        if not 0 <= text.find(mark) < boundary:
            bad.append("%s does not sit above the untrusted-data boundary"
                       % mark)
    if text.count("[INPUT]") != 1 or text.find("[INPUT]") < boundary:
        bad.append("the input mark is not the one below the boundary")

    data = payload(task)
    if list(data) != list(PAYLOAD_KEYS):
        bad.append("the payload keys are %s, not %s"
                   % (list(data), list(PAYLOAD_KEYS)))
        return bad
    src, display, back = HR._source(task["source_id"])
    if list(data["menu"]) != list(display):
        bad.append("the menu is not this source's readable menu")
    if len(set(display)) != len(display) or any(
            K.a1_reader.restore_menu_pick(d, back) != t
            for d, t in zip(display, src["menu_tokens"])):
        bad.append("the menu does not restore to its own tokens")
    if list(data["event"]) != list(HR.EVENT_VIEW) or any(
            data["event"][k] != src[k] for k in HR.EVENT_VIEW):
        bad.append("the event block is not the frozen source view")
    by_row = dict(inventory())
    want_row_keys = ["row_index", "proposed_record_kind", "part_ref",
                     "occurrence_in_part", "quote", "raw_label_or_claim"]
    if len(data["rows"]) != len(task["rows"]):
        bad.append("the payload does not carry every located row of this event")
        return bad
    for n, (row, pid) in enumerate(zip(data["rows"], task["rows"])):
        frozen = by_row[pid]
        if list(row) != want_row_keys:
            bad.append("%s: the row fields are %s" % (pid, list(row)))
            continue
        if row["row_index"] != n + 1:
            bad.append("%s: the row index is %r" % (pid, row["row_index"]))
        if row["proposed_record_kind"] != frozen["proposed_record_kind"]:
            bad.append("%s: the proposed record kind is not the frozen one"
                       % pid)
        for field in ("part_ref", "occurrence_in_part", "quote",
                      "raw_label_or_claim"):
            if row[field] != frozen[field]:
                bad.append("%s: the payload's %s is not the frozen one"
                           % (pid, field))
    index_of = {p: n + 1 for n, p in enumerate(task["rows"])}
    want_groups = [[index_of[m] for m in members]
                   for members in task["groups"].values()]
    got = [g.get("member_row_indexes") for g in data["groups"]]
    if [list(g) for g in data["groups"]] != [["member_row_indexes"]] * len(
            data["groups"]) or got != want_groups:
        bad.append("the group block is not exactly the derived member indexes")
    return bad


# ----------------------------------------------------------- the transport --
def key_role():
    """The DECLARED key-owner configuration, or None. Requested, never proved."""
    if not os.path.isfile(KEY_ROLE_FILE):
        return None
    doc = _load(KEY_ROLE_FILE)
    return collections.OrderedDict(
        (k, doc[k]) for k in ROLE_FIELDS if k in doc)


def role_problems():
    """Why this declaration may not sit in the independent key-owner seat.

    A declaration is a REQUEST. It is checked for shape, and for the one
    admission rule the amendment states: the key owner may not be the model
    under test. A valid Sonnet state proves the evidence machinery reads; it
    disqualifies that role from this seat.
    """
    doc = key_role()
    if doc is None:
        return ["no key-owner role is declared at %s: the independent key "
                "owner's model, effort, agent type, tool policy and output "
                "limit are UNDECLARED, so this door publishes no call"
                % KEY_ROLE_FILE]
    bad = ["the declaration does not name %s" % f
           for f in ROLE_FIELDS if f not in doc]
    if bad:
        return bad
    if doc["kind"] not in ROLE_KINDS:
        bad.append("kind %r is not one of %s" % (doc["kind"], list(ROLE_KINDS)))
    # THE RUNTIME IDENTITY IS THE ADMISSION FACT, not the alias: Codex SEQ 1990
    # declared an independent alias against the tested runtime and this seat
    # accepted it, because the runtime was never read at all.
    if doc["model_alias"] == K.MODEL:
        bad.append("the declared alias IS the alias under test (%s); it may "
                   "read evidence but may not own this key" % K.MODEL)
    if doc["runtime_model_id"] == K.RUNTIME_MODEL_ID:
        bad.append("the declared runtime IS the runtime under test (%s); it "
                   "may read evidence but may not own this key"
                   % K.RUNTIME_MODEL_ID)
    if doc["workflow_row_model"] == K.ROW_MODEL_ID:
        bad.append("the declared workflow row model IS the row model under "
                   "test (%s); it may read evidence but may not own this key"
                   % K.ROW_MODEL_ID)
    for field in ("runtime_model_id", "workflow_row_model"):
        if not (isinstance(doc[field], str) and doc[field].strip()):
            bad.append("the declared %s is not a name" % field)
    if doc["effort"] != K.EFFORT:
        bad.append("effort %r is not the reviewed %r" % (doc["effort"],
                                                         K.EFFORT))
    if list(doc["disallowedTools"]) != list(K.DISALLOWED):
        bad.append("the tool policy %r is not the reviewed %r"
                   % (doc["disallowedTools"], list(K.DISALLOWED)))
    if str(doc["max_output_tokens"]) != str(K.MAX_OUTPUT):
        bad.append("the output limit %r is not the reviewed %r"
                   % (doc["max_output_tokens"], K.MAX_OUTPUT))
    return bad


def live_role_problems():
    """Why no REAL call may be published. A TEST declaration never qualifies."""
    bad = list(role_problems())
    doc = key_role()
    if not bad and doc["kind"] != "LIVE":
        bad.append("the declared role is %s, which may render and be tested "
                   "but may never qualify a real call" % doc["kind"])
    return bad


def observed_proof():
    """What actually ran on this seat. NOTHING yet, and nothing is manufactured.

    Observed proof is not a foreign state read out of the store: it is this
    door's OWN run evidence, proved by build_kfields_key._official_proof under
    the scoped key-role binding below. Until a run exists there is no observed
    proof, and that is recorded as a missing LIVE capability, never filled in.
    """
    return None


def missing_live_proof():
    """The one capability this preparation cannot supply, named exactly."""
    return collections.OrderedDict([
        ("what", "one completed subscription workflow call on the declared "
                 "key-owner role, recorded as an official single-agent, "
                 "tool-free state with its transcript"),
        ("why_it_is_missing", "no such call has been made on any non-tested "
                              "role, so the runtime model id that answers the "
                              "declared alias is unobserved"),
        ("who_may_make_it", "a later bounded task Codex opens; this door "
                            "renders the request but publishes no call"),
        ("what_it_would_prove", "the alias-to-runtime-id binding, the agent "
                                "type, the tool policy and the effort the "
                                "runtime actually applies"),
        ("what_is_NOT_a_substitute", "a state recorded on the tested Sonnet "
                                     "role, a hand-written file, or an "
                                     "inherited session default with tools")])


#: the tested role's values, saved while the key-role binding is in force
_SAVED = []
#: the tested role's own transport block, saved while the seat's is served
_REAL_BLOCK = []


@contextlib.contextmanager
def _unbound():
    """Lift the key-role binding for THIS door's OWN checks.

    Codex SEQ 1989's run proved why: with the binding in force, every check
    that reads the tested role's constants read the key role's instead, so the
    package re-derivation disagreed with itself and the seat's own admission
    rule compared the declared alias to a copy of itself. Only the locked
    evidence owner may see the key role; everything of mine sees the tested one.
    """
    if not _SAVED and not _REAL_BLOCK:
        yield
        return
    current = [(n, getattr(K, n)) for n, _v in (_SAVED[-1] if _SAVED else ())]
    for n, v in (_SAVED[-1] if _SAVED else ()):
        setattr(K, n, v)
    block = K._transport_block
    if _REAL_BLOCK:
        K._transport_block = _REAL_BLOCK[-1]
    try:
        yield
    finally:
        K._transport_block = block
        for n, v in current:
            setattr(K, n, v)


def key_transport():
    """The transport block a receipt pins for THIS seat: the declared role."""
    doc = key_role()
    if doc is None:
        raise ValueError(role_problems()[0])
    return collections.OrderedDict([
        ("model_alias", doc["model_alias"]),
        ("runtime_model_id", doc["runtime_model_id"]),
        ("workflow_row_model", doc["workflow_row_model"]),
        ("effort", doc["effort"]), ("agentType", doc["agentType"]),
        ("disallowedTools", list(doc["disallowedTools"])),
        ("CLAUDE_CODE_MAX_OUTPUT_TOKENS", doc["max_output_tokens"]),
        ("parent_session_id", K.PARENT_SESSION),
        ("transport", doc["transport"]),
        ("declared_only", "a requested configuration; the runtime identity is "
                          "observed only from a completed call")])


@contextlib.contextmanager
def _key_role_binding():
    """The locked evidence owner, bound to THIS seat for ONE serial scope.

    build_kfields_key._official_proof keeps its own strict checks and reads the
    model, effort, agent type and tool policy from its module. They are set to
    the declared key role here and restored in finally, so the tested Sonnet
    role and the hard reviewers are never changed globally.
    """
    doc = key_role()
    if doc is None:
        raise ValueError(role_problems()[0])
    names = (("MODEL", doc["model_alias"]), ("EFFORT", doc["effort"]),
             ("AGENT_TYPE", doc["agentType"]),
             ("DISALLOWED", tuple(doc["disallowedTools"])),
             ("MAX_OUTPUT", doc["max_output_tokens"]),
             ("RUNTIME_MODEL_ID", doc["runtime_model_id"]),
             # the WORKFLOW ROW's own id: a separate official field, which the
             # proof owner checked against the transcript's id (Codex 1997)
             ("ROW_MODEL_ID", doc["workflow_row_model"]))
    saved = [(n, getattr(K, n)) for n, _v in names]
    _SAVED.append(saved)
    for n, v in names:
        setattr(K, n, v)
    try:
        yield doc
    finally:
        _SAVED.pop()
        for n, v in saved:
            setattr(K, n, v)


def render_launcher(task, attempt=1):
    """The released transport body, rendered for THIS seat.

    NO BOOTSTRAP DEADLOCK: a request is rendered from the DECLARED
    configuration, so the first unarmed request never needs a completed call.
    The body itself is the released owner's, written nowhere here.
    """
    if not (isinstance(attempt, int) and 1 <= attempt <= MAX_ATTEMPTS):
        raise ValueError("attempt %r is outside 1..%d" % (attempt,
                                                          MAX_ATTEMPTS))
    # THIS DOOR'S OWN check, always against the tested role's constants: the
    # renderer is called from inside the locked owner's scope, where the seat's
    # binding is in force, and a check that read it there would compare the
    # declared alias to a copy of itself (Codex SEQ 1989).
    bad = _own(role_problems)
    if bad:
        raise ValueError(bad[0])
    call = collections.OrderedDict([("source_id", task["source_id"]),
                                    ("event_index", task["event_index"]),
                                    ("rows", list(task["rows"])),
                                    ("attempt", attempt)])
    with _key_role_binding():
        return HR.launcher_text(
            call, prompt(task), task["source_id"], "Adjudicate", LAUNCHER_NAME,
            "K-fields A4 source-only key: one independent key owner settles "
            "every located row of one event from its source alone",
            ["source_id: CALL.source_id, event_index: CALL.event_index",
             "rows: CALL.rows"])


def sonnet_role_untouched():
    """The tested Sonnet role, re-measured. This door must never change it."""
    return collections.OrderedDict([
        ("tested_transport", K._transport_block()),
        ("hard_review_model", K.MODEL), ("hard_review_effort", K.EFFORT),
        ("hard_review_agent_type", K.AGENT_TYPE),
        ("hard_review_row_model", K.ROW_MODEL_ID),
        ("hard_review_disallowed", list(K.DISALLOWED)),
        ("blinds_per_hard_task", list(HR.BLINDS))])


def source_problems():
    """THE SERVED SOURCE IS THE FROZEN ONE (Codex SEQ 1988's gate probe).

    The probe replaced the source provider in memory, rebuilt the package and
    watched it certify altered event text as the frozen benchmark, because every
    derived hash agreed with every other derived hash. So each event is bound to
    TWO independent things: the frozen plan's own recorded file identity, and the
    file itself read here, compared to whatever the payload will actually render.
    """
    bad = []
    pins = {e["source_id"]: e for e in plan()["events"]}
    for task in tasks():
        sid = task["source_id"]
        pin = pins.get(sid)
        path = os.path.join(BLM.INPUTS, sid + ".json")
        if pin is None:
            bad.append("%s: the frozen plan records no source for this event"
                       % sid)
            continue
        if not os.path.isfile(path):
            bad.append("%s: its frozen source file is not served" % sid)
            continue
        if INV.sha_file(path) != pin["input_sha256"]:
            bad.append("%s: the served source file is not the frozen one" % sid)
        served, _display, _back = HR._source(sid)
        if served != _load(path):
            bad.append("%s: the source the payload renders is not the file it "
                       "names" % sid)
    return bad


def _owners():
    """Every file whose bytes decide what this door renders or accounts."""
    names = ("build_kfields_final.py", "build_kfields_hard_review.py",
             "build_kfields_key.py", "build_inventory_review.py",
             "build_launch_manifest.py", "raw_transport.py", "kf_lint.py",
             "audit_worker_access.py", "validate_benchmark_inventory.py",
             "a1_reader.py", "build_exp5_contract.py",
             "launch_kfields_drafts.manifest.json")
    out = collections.OrderedDict(
        (n, INV.sha_file(os.path.join(F._HERE, n))) for n in names)
    out["source_only_key_owner"] = INV.sha_file(os.path.abspath(__file__))
    out["inventory"] = INV.sha_file(INV.INV)
    out["approved_source_lock"] = INV.sha_file(K.APPROVED_SOURCE_LOCK)
    return out


def budget():
    """MEASURED from this sample's own A3 receipts, never carried as a number."""
    before = K.ledger_before()
    planned = len(tasks())
    return collections.OrderedDict([
        ("before", before), ("planned_key_calls", planned),
        ("planned_signer", 0),
        ("planned_note", "the signature is a later gate and buys no call here"),
        ("after_planned", before + planned),
        ("max_attempts_per_call", MAX_ATTEMPTS),
        ("retry_cap", MAX_ATTEMPTS - 1),
        ("retry_cap_meaning", "PER CALL, invalid replies only, never a run total"),
        ("retryable_states", list(RETRYABLE)),
        ("worst_case_total", planned * MAX_ATTEMPTS),
        ("worst_case_after", before + planned * MAX_ATTEMPTS),
        ("package_ceiling", before + planned * MAX_ATTEMPTS),
        ("global_ceiling", GLOBAL_CEILING),
        ("calls_made_by_this_package", 0)])


def capacity(prompts):
    """The serialized prompt, plus the released body it will be carried in.

    The body is MEASURED from the released transport owner with an empty prompt;
    it is an estimate until the key owner's own alias is proved, and it is named
    as one rather than pinned.
    """
    call = collections.OrderedDict([("source_id", ""), ("event_index", 0),
                                    ("rows", []), ("attempt", 1)])
    overhead = len(HR.launcher_text(
        call, "", "", "Adjudicate", LAUNCHER_NAME, "measurement only",
        ["source_id: CALL.source_id, event_index: CALL.event_index",
         "rows: CALL.rows"]).encode("utf-8"))
    serial = [len(json.dumps(t).encode("utf-8")) for t in prompts]
    return collections.OrderedDict([
        ("unit", "UTF-8 bytes of the serialized prompt plus the released "
                 "launcher body; never summed across calls"),
        ("transport_limit_bytes", K.TRANSPORT_LIMIT),
        ("released_body_bytes", overhead),
        ("released_body_source", "build_kfields_hard_review.launcher_text with "
                                 "an empty prompt; the key owner's own alias "
                                 "will change it by the alias length"),
        ("largest_prompt_bytes", max(len(p.encode("utf-8")) for p in prompts)),
        ("smallest_prompt_bytes", min(len(p.encode("utf-8")) for p in prompts)),
        ("largest_serialized_call_bytes", max(serial) + overhead),
        ("at_or_over_transport_limit",
         [n + 1 for n, s in enumerate(serial)
          if s + overhead >= K.TRANSPORT_LIMIT])])


def group_questions():
    """The same-locator groups, as QUESTIONS put to the key owner.

    Two rows of one event that name one exact locator raise a real source
    question - are they one fact or two - and the locked output card already
    asks it. They are NOT by themselves a duplicate, a disagreement or a
    reason for an extra review; what they are is derived from the frozen
    inventory and shown in the payload.
    """
    return [collections.OrderedDict([
        ("source_id", t["source_id"]), ("group_id", gid), ("members", list(m))])
        for t in tasks() for gid, m in t["groups"].items()]


def unresolved_outcomes(shards):
    """The STRUCTURED outcomes that leave something genuinely unresolved.

    Read from the locked reply shape, never from a vocabulary of reason words:
      * a group the key owner returned `null` - it says the evidence and rules
        could not settle it, and the locked materializer already refuses to
        promote anything under it;
      * an open issue - the reply's own claim that something blocks a safe
        final answer.
    An ABSTENTION IS NOT ONE OF THEM. The frozen inventory deliberately carries
    31 negative controls and four lawful abstention controls; treating their
    lawful empty settlements as disagreements would manufacture a universal
    extra pass over the whole sample.
    """
    out = []
    by = {t["source_id"]: t for t in tasks()}
    for sid, shard in shards.items():
        task = by.get(sid)
        if task is None:
            continue
        members = list(task["groups"].values())
        for n, g in enumerate(shard.get("groups") or []):
            if g.get("members_are_one_fact") is None:
                out.append(collections.OrderedDict([
                    ("source_id", sid), ("kind", "unsettled_group"),
                    ("members", list(members[n]) if n < len(members) else [])]))
        for issue in shard.get("open_issues") or []:
            out.append(collections.OrderedDict([
                ("source_id", sid), ("kind", "open_issue"),
                ("what", issue.get("what"))]))
    return out


def hard_review_plan(shards=None):
    """What independent review this route owes, under the existing A4 rule.

    BEFORE the call nothing is owed and nothing is scheduled: the existing
    triggers - an unresolved selection and an item both drafts rejected - are
    properties of the evaluated drafts, which a source-only key may not read.
    AFTER the call the owed population is exactly the structured unresolved
    outcomes above, each still reviewed by the existing owner's two blind
    Sonnet calls. There is no universal extra pass and nothing is hidden.
    """
    questions = group_questions()
    plan = collections.OrderedDict([
        ("owner", "build_kfields_hard_review, unchanged, two blind calls per "
                  "task on the tested Sonnet role"),
        ("model", "unchanged: the tested Sonnet role, never this door's"),
        ("blinds_per_task", list(HR.BLINDS)),
        ("pre_call_owed", 0),
        ("pre_call_note", "the existing triggers are draft properties this "
                          "door may not read; none is owed before the call"),
        ("group_questions_asked_in_the_prompt", questions),
        ("group_question_count", len(questions)),
        ("post_call_trigger", "the reply's own structured unresolved outcomes: "
                              "a group returned null, and an open issue. An "
                              "abstention is NOT one; the inventory carries "
                              "lawful abstention and negative controls."),
    ])
    if shards is None:
        plan["post_call_owed"] = "NOT DERIVABLE BEFORE THE CALL"
    else:
        owed = unresolved_outcomes(shards)
        plan["post_call_owed"] = len(owed)
        plan["post_call_tasks"] = owed
        plan["post_call_calls"] = len(owed) * len(HR.BLINDS)
    return plan


def manifest():
    """Everything the key calls and their later accounting depend on."""
    built = tasks()
    prompts = [prompt(t) for t in built]
    rows = []
    for task, text in zip(built, prompts):
        rows.append(collections.OrderedDict([
            ("task_id", task["task_id"]), ("source_id", task["source_id"]),
            ("event_index", task["event_index"]),
            ("rows", list(task["rows"])),
            ("groups", [list(v) for v in task["groups"].values()]),
            ("prompt_sha256", _sha(text)),
            ("prompt_bytes", len(text.encode("utf-8")))]))
    cov = coverage()
    return collections.OrderedDict([
        ("door", DOOR), ("version", VERSION), ("authority", AUTHORITY),
        ("base_commit", INV.BASE_COMMIT),
        ("armed", False),
        ("arming", "owned by orchestration, never by a file this "
                   "unit can write; nothing here can set armed true"),
        ("bound", _owners()),
        ("contract_suffix", SUFFIX),
        ("rules_sha256", _sha(C.role_rules("drafter", SUFFIX))),
        ("output_card_sha256", _sha(C.one_item_output_section().rstrip())),
        ("gate_text_sha256", _sha(BIR.gate_text())),
        ("crosswalk_text_sha256", _sha(BIR.crosswalk_text())),
        ("boundary_sha256", _sha(HR._boundary_at(SUFFIX))),
        ("injection_control_sha256", _sha(truthful_control())),
        ("task_section_sha256", _sha(F._task_section())),
        ("locked_role_sha256", _sha(F._ROLE)),
        ("locked_output_section_sha256", _sha(F._output_section())),
        ("role_sha256", _sha(role())),
        ("output_section_sha256", _sha(output_section())),
        ("prefix_sha256", _sha(prompt_prefix())),
        ("payload_keys", list(PAYLOAD_KEYS)),
        ("reply_keys", list(F.REPLY_KEYS)),
        ("requested_key_role", key_role()),
        ("requested_key_role_problems", role_problems()),
        ("live_publication_problems", live_role_problems()),
        ("observed_key_role_proof", observed_proof()),
        ("missing_live_proof", missing_live_proof()),
        ("source_problems", source_problems()),
        ("source_pins", collections.OrderedDict(
            (e["source_id"], collections.OrderedDict([
                ("input_path", e["input_path"]),
                ("input_sha256", e["input_sha256"])]))
            for e in plan()["events"])),
        ("source_manifest", _load(INV.INV)["source_manifest"]),
        ("sonnet_role_untouched", sonnet_role_untouched()),
        ("gold_door", collections.OrderedDict([
            ("gold_only", list(F.GOLD_ONLY)),
            ("gold_extra_keys", list(F.GOLD_EXTRA_KEYS)),
            ("hard_classes", list(F.HARD_CLASSES)),
            ("tag_floor", INV.TAG_FLOOR),
            ("class_floor", BIR.CLASS_FLOOR),
            ("sequential_class", BIR.SEQUENTIAL_CLASS),
            ("sequential_floor", BIR.SEQUENTIAL_FLOOR)])),
        ("counts", collections.OrderedDict([
            ("source_events", len(cov)),
            ("events_scheduled", len(rows)),
            ("events_with_no_located_row",
             [c["source_id"] for c in cov if not c["scheduled"]]),
            ("frozen_rows", len(inventory())),
            ("rows_scheduled", sum(len(r["rows"]) for r in rows)),
            ("locator_groups", sum(len(r["groups"]) for r in rows)),
            ("leads_shown", 0)])),
        ("coverage", cov),
        ("hard_review", hard_review_plan()),
        ("budget", budget()),
        ("capacity", capacity(prompts)),
        ("events", rows),
        ("call_order", [r["source_id"] for r in rows]),
        ("remaining_gates_in_order", [
            "Codex's written authorization to arm this door",
            "a LIVE key-owner role declaration for this seat",
            "one completed call on it, which is the only thing that can "
            "observe its runtime identity",
            "preflight() again at launch",
            "one workflow call per scheduled event, serially, one agent in "
            "flight, rendered launcher bytes only",
            "raw-first capture, then the locked reader",
            "the invalid-only retry, at most once per call",
            "the hard-disagreement reviews this run's own result triggers, on "
            "the unchanged Sonnet role",
            "the locked materializer, gold door and duplicate check",
            "independent signing and lock through their existing owners",
            "A5/A6, then A7"])]
        + list(RT.approved_lane_input_fields().items()))


def build(out_dir):
    """Write the frozen package. Launches nothing and arms nothing."""
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    doc = manifest()
    HR._atomic(os.path.join(out_dir, MANIFEST_NAME), json.dumps(doc, indent=1))
    HR._atomic(os.path.join(out_dir, PREFIX_NAME), prompt_prefix())
    return doc


def package_problems(out_dir):
    """Re-derive from the live owners and compare. -> [problems]"""
    path = os.path.join(out_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return ["no source-only key manifest at %s" % out_dir]
    pinned, bad = _load(path), []
    want = manifest()
    if _sha(json.dumps(pinned, sort_keys=True)) \
            != _sha(json.dumps(want, sort_keys=True)):
        for field in ("door", "version", "base_commit", "armed", "bound",
                      "contract_suffix", "rules_sha256", "output_card_sha256",
                      "gate_text_sha256", "crosswalk_text_sha256",
                      "boundary_sha256", "injection_control_sha256",
                      "task_section_sha256", "locked_role_sha256",
                      "locked_output_section_sha256", "role_sha256",
                      "output_section_sha256", "prefix_sha256", "payload_keys",
                      "reply_keys", "requested_key_role",
                      "sonnet_role_untouched",
                      "gold_door", "counts", "coverage", "hard_review",
                      "budget", "capacity", "call_order"):
            if pinned.get(field) != want[field]:
                bad.append("the pinned %s is not the live one" % field)
        pin = {r["source_id"]: r for r in pinned.get("events") or []}
        wnt = {r["source_id"]: r for r in want["events"]}
        for sid in sorted(set(pin) | set(wnt)):
            if sid not in pin:
                bad.append("%s is missing from the package" % sid)
            elif sid not in wnt:
                bad.append("%s is in the package but does not derive" % sid)
            elif pin[sid] != wnt[sid]:
                bad.append("%s is not the live event" % sid)
        if not bad:
            bad.append("the package differs from the live derivation")
    shipped = os.path.join(out_dir, PREFIX_NAME)
    if not os.path.isfile(shipped) or K._read(shipped) != prompt_prefix():
        bad.append("the shipped prefix is not the live one")
    extra = sorted(set(os.listdir(out_dir)) - {MANIFEST_NAME, PREFIX_NAME})
    if extra:
        bad.append("the package carries files it does not own: %s" % extra[:3])
    return bad


def preflight(out_dir):
    """The one gate before any key call. It cannot pass while UNARMED."""
    problems = list(package_problems(out_dir))
    problems += population_problems()
    problems += source_problems()
    problems += role_problems()
    path = os.path.join(out_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return {"ok": False, "problems": problems, "manifest": None}
    doc = _load(path)
    for task in tasks():
        problems += ["%s: %s" % (task["source_id"], p)
                     for p in prompt_problems(task)]
    if doc["capacity"]["at_or_over_transport_limit"]:
        problems.append("a call is at or over the transport limit")
    order = doc["call_order"]
    if len(set(order)) != len(order):
        problems.append("the same event is scheduled twice")
    if order != [t["source_id"] for t in tasks()]:
        problems.append("the pinned call order is not the frozen one")
    if doc["counts"]["rows_scheduled"] != len(inventory()):
        problems.append("the package does not cover all %d frozen rows"
                        % len(inventory()))
    if doc["counts"]["leads_shown"]:
        problems.append("a lead is shown to the key owner")
    b = doc["budget"]
    live = b["before"] + b["planned_key_calls"] * b["max_attempts_per_call"]
    if b["package_ceiling"] != live:
        problems.append("the pinned package ceiling %r is not the derived %d"
                        % (b["package_ceiling"], live))
    if b["worst_case_after"] > b["package_ceiling"]:
        problems.append("the worst case %d breaks the package ceiling %d"
                        % (b["worst_case_after"], b["package_ceiling"]))
    if b["worst_case_after"] > GLOBAL_CEILING:
        problems.append("the worst case would break the global ceiling %d"
                        % GLOBAL_CEILING)
    if b["calls_made_by_this_package"]:
        problems.append("this package has made a call")
    return {"ok": not problems, "problems": problems, "manifest": doc}


# ------------------------------- the locked reader and the locked accounting --
def read_shard(text, task):
    """THE LOCKED OWNER'S READER, given this door's frozen items for ONE serial
    call and restored in try/finally. No lead is supplied, so the locked reader
    itself requires `lead_reconciliation` to be exactly []."""
    with _scope():
        return F.read_shard(text, task, [])


#: The locked materializer reads ONE phase-one artifact, for a REPORTING field
#: that gates nothing. This door has no phase-one stage, so the honest value is
#: empty - and it is declared here for the length of one call rather than written
#: to disk as an invented historical receipt.
_NO_PHASE1 = "__source_only_1988_has_no_phase_one__"


def materialize(shards):
    """THE LOCKED OWNER'S MATERIALIZER over this door's population.

    Called inside the one serial scope above. Every row rule, group rule, gold
    field and accounting line is the locked owner's own; the only thing this
    door supplies is which events exist and the honest absence of a phase-one
    stage it never had. -> (key, sidecar, problems)
    """
    conflicts = os.path.join(_NO_PHASE1, "conflicts_1370.json")
    del _ASKED[:]
    with _scope():
        key, sidecar, problems = F.materialize(_NO_PHASE1, shards)
    problems = list(problems)
    if _ASKED.count(conflicts) != 1:
        problems.append("the locked materializer asked for the absent "
                        "phase-one artifact %d times, not once"
                        % _ASKED.count(conflicts))
    for sid, n in F.same_event_duplicates(key):
        problems.append("%s: fact %d repeats an earlier fact of the same event "
                        "exactly; the key owner must reconcile it once"
                        % (sid, n))
    problems += ["gold door: %s" % e for e in F.key_problems(key)]
    return key, sidecar, problems


def counts(key, sidecar):
    """The locked owner's own count block over this door's key."""
    return F.counts(key, sidecar)


# ------------------------------------------------------- the run lifecycle --
# NOTHING BELOW IS A NEW LIFECYCLE. The locked event owner already owns the
# receipt, the raw-first capture, the official-state proof, the parse, the
# accounting, the fixed invalid-only child and the resume; each is called here
# inside ONE serial scope that supplies this door's population, its prompt and
# its launcher, and restores every owner afterwards. The key-role binding is
# entered only where a real call's identity is proved, so the tested Sonnet
# role and the hard reviewers are never changed globally.
_ASKED = []


def _own(fn, *a):
    """Run one of THIS door's checks with the key-role binding lifted."""
    with _unbound():
        return fn(*a)


@contextlib.contextmanager
def _scope(bind_role=False):
    """Give the locked owner this door's population for one serial scope."""
    built = tasks()
    conflicts = os.path.join(_NO_PHASE1, "conflicts_1370.json")
    frozen_items = items()
    swaps = [("event_tasks", lambda _evidence: built),
             # NO LEAD REACHES THE LOCKED READER, from either caller: the
             # finalizer and accepted_shards both supply event_leads, and both
             # went to the historical owner (Codex SEQ 1990 item 2).
             ("event_leads", lambda _bound, _task: []),
             ("render_launcher", lambda task, bound, attempt=1:
              render_launcher(task, attempt)),
             ("final_prompt", lambda bound, task: prompt(task)),
             ("package_problems", lambda pkg, bound: _own(package_problems,
                                                           pkg)),
             ("preflight", lambda pkg, bound: _own(preflight, pkg)),
             ("DOOR", DOOR), ("MANIFEST_NAME", MANIFEST_NAME),
             ("PREFIX_NAME", PREFIX_NAME), ("LAUNCHER_NAME", LAUNCHER_NAME)]
    saved = [(n, getattr(F, n)) for n, _v in swaps]
    real_load = K._load
    real_items = HR._items
    HR._items = lambda: frozen_items

    def load(path):
        _ASKED.append(path)
        if path == conflicts:
            return {"model_reported_ambiguities": []}
        return real_load(path)

    for name, value in swaps:
        setattr(F, name, value)
    K._load = load
    real_block = K._transport_block
    stack = contextlib.ExitStack()
    try:
        if bind_role:
            stack.enter_context(_key_role_binding())
            _REAL_BLOCK.append(real_block)
            K._transport_block = key_transport
        yield
    finally:
        if bind_role and _REAL_BLOCK:
            _REAL_BLOCK.pop()
        K._transport_block = real_block
        stack.close()
        K._load = real_load
        HR._items = real_items
        for name, value in saved:
            setattr(F, name, value)


def bound(run_dir=None, package=None):
    """This door's Bound: THE package it is given, no phase-one evidence.

    The package is a parameter, not a module constant: Codex SEQ 1989's
    reproduction armed one package by naming another, because a gate consulted
    a global instead of the directory it was handed.
    """
    return F.Bound(package=package or PKG_DIR, evidence=_NO_PHASE1, hr=None,
                   fix=None, events=run_dir, hr_package=None)


def expected_receipt(out_dir, attempt=1, allowed=None, package=None):
    """The locked owner's typed expectation for this door's event phase."""
    with _scope(bind_role=True):
        labels = ([t["source_id"] for t in tasks()] if allowed is None
                  else list(allowed))
        return F.expected_receipt(out_dir, bound(package=package), "events",
                                  attempt, labels)


def prepare_run(out_dir, package=None, test_binding=False):
    """Publish this door's event phase. REFUSES while no LIVE role is declared.

    A rendered request needs only a declaration, so the first unarmed request
    never waits on a completed call. Publishing needs a role that may make real
    calls, and orchestration still decides when. `test_binding` lets the suite
    exercise this exact interface, and it can never qualify a real call: it is
    honoured only for a role declared TEST and never against the real package.
    """
    if test_binding:
        bad = list(role_problems())
        doc = key_role()
        if not bad and doc["kind"] != "TEST":
            bad = ["a test binding must declare kind TEST, not %s" % doc["kind"]]
        if not bad and os.path.abspath(package or PKG_DIR) \
                == os.path.abspath(PKG_DIR):
            bad = ["a TEST binding may never publish against the real package"]
    else:
        bad = live_role_problems()
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    with _scope(bind_role=True):
        return F.prepare_events(out_dir, bound(package=package))


def record_state(out_dir, state_path):
    """The locked owner's own append-one-unique-state recorder."""
    return F.record_state(out_dir, state_path)


def run_evidence(out_dir, receipt, package=None):
    """The locked owner's per-call proof, under this seat's role binding."""
    with _scope(bind_role=True):
        return F.run_evidence(out_dir, bound(package=package), receipt)


def finalize(out_dir, package=None):
    """The locked owner's RAW-FIRST, write-once finalizer over this population.

    Paid bytes are written before any receipt, identity or parse check; that
    order is the owner's, not a rule restated here.
    """
    with _scope(bind_role=True):
        return F.finalize(out_dir, bound(package=package))


def accepted_shards(run_dir, package=None):
    """The accepted shards and their exact raw texts, from the locked owner.

    This is the RESUME interface: a successful saved result is read back from
    the finalized run and is never called again.
    """
    with _scope(bind_role=True):
        return F.accepted_shards(run_dir, bound(run_dir, package),
                                 "events")


def _base_pass(base, by, package):
    """ONE evidence pass over ONE attempt directory, through the existing owners.

    Its validated receipt, the existing per-call proof and the existing parser,
    once. Every later question - who owns an accepted answer, what each label's
    current outcome is, what may still be retried - is answered from this, not
    from a second rule engine. -> a dict, or None when nothing was published.
    """
    rpath = os.path.join(base, K.RECEIPT_NAME)
    if not os.path.isfile(rpath):
        return None
    rec = _load(rpath)
    problems = []
    with _scope(bind_role=True):
        problems += F.receipt_problems(base, bound(base, package), rec)
    got, probs = run_evidence(base, rec, package)
    problems += probs
    outcomes = collections.OrderedDict()
    for label, (state, _why, text) in got.items():
        if state != "proved":
            outcomes[label] = (state, None)
            continue
        # A PROVED CALL IS NOT AN ANSWER. The locked parser decides.
        obj, bad = (read_shard(text, by[label]) if label in by
                    else (None, ["not one of this door's events"]))
        del obj
        outcomes[label] = ("invalid_response" if bad else "valid", text)
    fin = os.path.join(base, K.FINALIZATION_NAME)
    return {"base": base, "receipt": rec, "attempt": rec.get("attempt"),
            "allowed": list(rec.get("allowed") or []), "outcomes": outcomes,
            "problems": problems,
            "finalization": _load(fin) if os.path.isfile(fin) else None}


def resume_plan(run_dir, package=None):
    """What a resumed run still owes, from ONE evidence pass per attempt.

    A result is credited only from the attempt that actually produced it: the
    owning base's validated receipt, the existing per-call proof of its bytes,
    THAT attempt's own kept proved artifact, and the existing reader's valid
    interpretation. Remaining eligibility comes from every base's own recorded
    attempt against the existing cap, and a historical closeout is judged
    against ITS OWN proved outcomes, never against today's remaining work
    (Codex SEQ 1994).
    """
    labels = [t["source_id"] for t in tasks()]
    rpath = os.path.join(run_dir, K.RECEIPT_NAME)
    if not os.path.isfile(rpath):
        return {"published": False, "allowed": labels, "served": [],
                "owed": labels, "retryable": [], "outcomes": {},
                "never_repeat": [], "finalized": False,
                "problems": ["no receipt: nothing was published"]}
    receipt = _load(rpath)
    allowed = list(receipt.get("allowed") or [])
    by = {t["source_id"]: t for t in tasks()}
    problems = list(_own(package_problems, package or PKG_DIR))
    passes = [x for x in (_base_pass(run_dir, by, package),
                          _base_pass(os.path.join(run_dir, "retry"), by,
                                     package)) if x]
    for x in passes:
        problems += x["problems"]
    finalized = any(x["finalization"] is not None for x in passes
                    if x["base"] == run_dir)
    if problems and passes and passes[0]["problems"]:
        return {"published": True, "allowed": allowed, "served": [],
                "owed": allowed, "retryable": [], "outcomes": {},
                "never_repeat": [], "finalized": finalized,
                "problems": problems}

    # WHO OWNS AN ACCEPTED ANSWER: the first attempt, in order, whose own
    # evidence both proved and parsed it. A base whose receipt is not the
    # owner's credits nothing.
    accepted = collections.OrderedDict()
    for x in passes:
        if x["problems"]:
            continue
        for label, (state, text) in x["outcomes"].items():
            if state == "valid" and label in allowed and label not in accepted:
                accepted[label] = (x, text)

    # THAT ATTEMPT'S OWN KEPT ARTIFACT, and no other. A matching file under an
    # attempt the run never made may not stand in for a changed authoritative
    # one, so the path is resolved from the owning base and its recorded
    # attempt rather than searched for.
    changed = []
    for label, (x, text) in accepted.items():
        kept = os.path.join(x["base"], "raw", "%s.attempt%s.proved.json"
                            % (label.replace("/", "_"), x["attempt"]))
        same = K._stored_matches(kept, text)
        # The FINALIZER is what keeps this artifact, so before that attempt has
        # closed out there is nothing stored and nothing to disagree with; the
        # call is still proved and parsed. Once it has closed out, the artifact
        # must exist and must be the answer this run accepted.
        if same is False or (same is None and x["finalization"] is not None):
            problems.append("%s: attempt %s did not keep the proved answer it "
                            "accepted" % (label, x["attempt"]))
            changed.append(label)

    # THE KEPT TRANSPORT BYTES are a different artifact with different correct
    # bytes: the final segment that state returned. A fault here is reported
    # wherever it is found, and it withdraws credit only from the attempt that
    # actually owns the accepted answer.
    for x in passes:
        for state in x["receipt"].get("states") or []:
            if not isinstance(state, str) or not os.path.isfile(state):
                continue
            doc_s = _load(state)
            label = K._state_label(doc_s)
            segment = (K.direct_result(doc_s) or {}).get("text")
            kept = os.path.join(x["base"], "raw", "%s.raw.json"
                                % os.path.splitext(os.path.basename(state))[0])
            if isinstance(segment, str) \
                    and K._stored_matches(kept, segment) is False:
                problems.append("%s: attempt %s did not keep the transport "
                                "bytes that state returned"
                                % (label, x["attempt"]))
                if accepted.get(label, (None,))[0] is x:
                    changed.append(label)

    served = [lab for lab in allowed
              if lab in accepted and lab not in set(changed)]
    rank = {"valid": 3, "invalid_response": 2}
    outcomes = collections.OrderedDict()
    for x in passes:
        for label, (state, _text) in x["outcomes"].items():
            if label not in allowed:
                continue
            if rank.get(state, 1) >= rank.get(outcomes.get(label), 0):
                outcomes[label] = state
    for lab in allowed:
        outcomes.setdefault(lab, "missing")
    for lab in changed:
        outcomes[lab] = "unproved"

    # THE CAP APPLIES TO EVERY BASE, INCLUDING THIS ONE. A label already
    # attempted at the last allowed attempt is exhausted; its terminal outcome
    # stays visible and is never rerolled.
    exhausted = {lab for x in passes
                 if (x["attempt"] or 0) >= MAX_ATTEMPTS for lab in x["allowed"]}
    retryable = [lab for lab in allowed
                 if lab not in set(served)
                 and outcomes.get(lab) in RETRYABLE
                 and lab not in exhausted]

    # EACH CLOSEOUT AGAINST ITS OWN PROVED ATTEMPT. A parent that lawfully
    # published a retry is not a forgery because a later child exhausted it.
    for x in passes:
        doc = x["finalization"]
        if doc is None:
            continue
        claimed = {r[0]: r[1] for r in (doc.get("outcomes") or [])
                   if isinstance(r, (list, tuple)) and len(r) >= 2}
        over = sorted(lab for lab, st in claimed.items() if st == "valid"
                      and x["outcomes"].get(lab, (None,))[0] != "valid")
        if over:
            problems.append("the attempt %s closeout calls %d labels valid that "
                            "its own evidence does not, first %s"
                            % (x["attempt"], len(over), over[0]))
        baseless = sorted(lab for lab in (doc.get("retry") or [])
                          if lab not in x["allowed"]
                          or x["outcomes"].get(lab, (None,))[0] not in RETRYABLE
                          or (x["attempt"] or 0) >= MAX_ATTEMPTS)
        if baseless:
            problems.append("the attempt %s closeout claims %d retries its own "
                            "outcomes do not support, first %s"
                            % (x["attempt"], len(baseless), baseless[0]))

    return {"published": True, "allowed": allowed, "served": served,
            "owed": [lab for lab in allowed if lab not in set(served)],
            "retryable": sorted(set(retryable)), "outcomes": outcomes,
            "never_repeat": served, "finalized": finalized,
            "problems": problems}


def owed_review_labels(shards):
    """The blind readings this run's OWN unresolved outcomes owe.

    Named through the existing hard-review owner's own label rule, two blind
    readings per genuinely unresolved outcome. Not a stub: while those readings
    do not exist, the locked gate reports each one missing and refuses.
    """
    return [HR.call_label("sok-hr-%03d" % n, blind)
            for n, _u in enumerate(unresolved_outcomes(shards))
            for blind in HR.BLINDS]


def signing_checks(shards, run_dir=None, package=None, raws=None):
    """THE LOCKED SIGNING GATE, over this door's source-only context.

    Codex SEQ 1990 item 4: the previous version re-decided the floors, the open
    issues and the duplicates itself while claiming to own no second gate. It
    now supplies that gate its accepted shards and the readings this run owes,
    and returns the gate's own verdict unchanged.
    """
    with _scope():
        real_shards = F.accepted_shards
        real_readings = F.required_readings
        real_outcomes = F._hard_outcomes
        F.accepted_shards = lambda *_a, **_k: (
            collections.OrderedDict(shards),
            collections.OrderedDict(raws or {}), [])
        F.required_readings = lambda _bound: owed_review_labels(shards)
        # THE FACT, not a pass: this door has run no hard review, so it holds no
        # valid readings. The gate then reports every owed reading missing and
        # REFUSES; nothing here reports success on its behalf.
        empty = lambda _bound: ({}, [])            # noqa: E731 - one expression
        empty.cache_clear = lambda: None           # the locked owner clears it
        F._hard_outcomes = empty
        try:
            gate = F.signing_gate(run_dir or PKG_DIR, bound(run_dir, package))
        finally:
            F.accepted_shards = real_shards
            F.required_readings = real_readings
            F._hard_outcomes = real_outcomes
    gate = dict(gate)
    gate["unresolved"] = unresolved_outcomes(shards)
    gate["owed_blind_readings"] = owed_review_labels(shards)
    return gate
