"""EXP-5 / K-fields PROMPT-CONTRACT builder — ONE builder, ONE envelope (step2 §3).

WHAT THIS EMITS. One assembled prompt string per role, in the WorkOrder order:

    [ROLE]      the role header — the ONLY difference between the two prompts
    [RULES]     the compact active-rules card
    [OUTPUT]    the envelope + schema, cross-checked against the Core owners
    [BOUNDARY]  the untrusted-evidence line
    [EVENT]     the event placeholder — ALWAYS LAST

WHERE EVERY SENTENCE COMES FROM. No semantic sentence is authored here. The
role headers, rules, output prose and boundary line are lifted verbatim from
the accepted implementation lead (rev-4 PART A, §§A1-A4), addressed by stable
heading and hash-pinned. The structural names come from the committed Core V2
owners and are generated, never copied:

    reply envelope    driver_write_cli.V2_REPLY_KEYS
    fact-level keys   prepared_fact_v2.PreparedFactV2._FACT_KEYS
    item fields       prepared_fact_v2.ITEM_FIELDS
    numeric slots     prepared_fact_v2.NUMERIC_SLOTS
    slot shape        slot_convert.SLOT_KEYS
    unit vocabulary   slot_convert.CANONICAL_UNITS
    abstention shape  driver_write_cli.V2_ABSTENTION_KEYS
    never emitted     prepared_fact_v2.SOURCE_OWNED_FIELDS

ONE SCHEMA OWNER (step2 §2) IS ENFORCED, NOT ASSERTED. PART A's typed skeleton
carries per-field type detail that Core does not export, so it is kept verbatim
AND cross-checked against Core on every build: a field that Core has and the
skeleton lacks (or the reverse) is a hard build failure. The two can therefore
never drift apart silently.

TEXT-ONLY (step2 §5). No XBRL engine, field, or construction rule belongs in
this kit. The prompt states only that the source-owned XBRL fields are
forbidden — the names come from Core, and the whole FINAL_DESIGN unit section
(whose XBRL-backed paragraph teaches how an XBRL fact is built) is NOT imported.

WHAT WAS DELETED AND WHY. The previous builder assembled the card from FIFTEEN
blocks pinned by exact line ranges into FROZEN copies of pre-consolidation
documents. That topology is the dependency this file exists to delete, not to
repair: the live files moved, the line scan was never re-pointed, and run
against the live work order it raised IndexError hunting a sentinel that no
longer exists.

Note for the record: that previous builder was never a tracked file, while the
card and manifest it emitted ARE tracked (4d473822). A committed artefact whose
generator is untracked cannot be reproduced from a clean checkout; this file
ends that by being the tracked generator of everything it writes.

15_CandidateFactPacket.md is a PROTECTED V1 baseline and is never read here.

Run:  venv/bin/python3 harness/build_exp5_contract.py [--out DIR]
"""
import argparse
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)

# The accepted implementation lead. Addressed by stable heading, never by line
# number, so the file may grow without silently serving the wrong text.
_PKG = os.path.join(_HERE, "exp5_rev4_package.md")
_ROLE_HEADERS = "### A1."
_RULES = "### A2."
_OUTPUT = "### A3."
_BOUNDARY = "### A4."

EVENT_PLACEHOLDER = "<<EVENT>>"   # the launcher substitutes the event here


def _section(path, heading):
    """The text from `heading` up to the next heading of the same or higher
    level. A pin that resolves to anything other than exactly one place is a
    hard failure — the deleted topology failed by silently serving wrong text,
    so neither an absent nor a duplicated heading may resolve quietly."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)
    depth = len(heading) - len(heading.lstrip("#"))
    starts = [i for i, line in enumerate(lines) if line.startswith(heading)]
    if len(starts) != 1:
        raise SystemExit(
            f"HEADING {'MISSING' if not starts else 'AMBIGUOUS'}: {heading!r} "
            f"matched {len(starts)}x in {os.path.basename(path)} — the live "
            f"owner moved; fix the pin, never guess")
    start = starts[0]
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if s.startswith("#") and len(s) - len(s.lstrip("#")) <= depth:
            end = j
            break
    return "".join(lines[start:end])


def _fences(text):
    """The fenced blocks of a section, in order, without their fences."""
    return re.findall(r"^```[^\n]*\n(.*?)^```", text, re.S | re.M)


def role_prompt_headers():
    """{role: verbatim header}, discovered from A1's own labels. The role set
    is read from the authority, never listed here, so a role added upstream is
    carried without editing this builder."""
    a1 = _section(_PKG, _ROLE_HEADERS)
    labels = re.findall(r"^\*\*(.+?):\*\*", a1, re.M)
    blocks = _fences(a1)
    if not labels or len(labels) != len(blocks):
        raise SystemExit(f"A1: {len(labels)} role labels vs {len(blocks)} "
                         f"blocks — the role headers moved; fix the pin")
    return {l.strip().lower(): b.strip() for l, b in zip(labels, blocks)}


def core_structure_card():
    """The structural half — generated from the Core owners, never copied."""
    from driver.core.prepared_fact_v2 import (ITEM_FIELDS, NUMERIC_SLOTS,
                                              SOURCE_OWNED_FIELDS,
                                              PreparedFactV2)
    from driver.core.slot_convert import CANONICAL_UNITS, SLOT_KEYS
    from driver.core.driver_write_cli import (V2_ABSTENTION_KEYS,
                                              V2_REPLY_KEYS)
    j = " · ".join
    return (
        f"- reply envelope: {j(V2_REPLY_KEYS)}\n"
        f"- each fact carries exactly: {j(PreparedFactV2._FACT_KEYS)}\n"
        f"- each `item` carries exactly these {len(ITEM_FIELDS)} fields: "
        f"{j(ITEM_FIELDS)}\n"
        f"- each POPULATED numeric slot ({j(NUMERIC_SLOTS)}) is an object with "
        f"exactly: {j(SLOT_KEYS)}\n"
        f"- `level_unit` / `change_unit` come from this vocabulary only: "
        f"{j(CANONICAL_UNITS)}\n"
        f"- each abstention carries exactly: {j(V2_ABSTENTION_KEYS)}\n"
        f"- NEVER emit these source-owned fields: {j(SOURCE_OWNED_FIELDS)}. "
        f"This exam is TEXT-ONLY: no XBRL field, proof, or dimension.\n")


def _skeleton_surfaces(skeleton):
    """Every structural surface the copied skeleton declares, as ordered tuples.

    Keyed the same way the Core owners are, so the comparison below is one loop
    over pairs rather than six bespoke checks. The skeleton is real JSON (every
    placeholder is a quoted string), so it is PARSED, never pattern-matched: a
    regex name-set could only ever prove "no Core name is missing" and could not
    see an EXTRA key, which is exactly how a copy becomes a second schema owner.
    """
    from driver.core.slot_convert import SLOT_KEYS
    doc = json.loads(skeleton)
    # Read each nested surface DEFENSIVELY: a renamed or dropped top-level key
    # must be reported as drift in the surface that owns it, not crash the
    # reader with a message that names no surface at all.
    fact = (doc.get("facts") or [{}])[0]
    item = fact.get("item") or {}
    abstention = (doc.get("abstentions") or [{}])[0]
    # WHICH FIELDS ARE SLOTS is decided by CORE's own key names appearing
    # together in a placeholder — the structural marker — never by descriptive
    # wording like "3-key object", which would be a vocabulary this builder
    # invented and would stop matching the day the prose is reworded.
    #
    # EVERY slot must carry the marker, not just the first. A3 used to spell the
    # shape once and back-reference it ("the same 3-key object") for the other
    # four; under that form a copied `"level_high": "<string>"` would still have
    # passed, because only the field NAME was being checked. The back-references
    # are gone and each slot now carries the marker, so this surface is real.
    spells_out = tuple(f for f, v in item.items()
                       if isinstance(v, str) and all(k in v for k in SLOT_KEYS))
    keys = ()
    if spells_out:
        shapes = {item[f][item[f].find("{") + 1:item[f].find("}")]
                  for f in spells_out if "{" in item[f]}
        if len(shapes) == 1:
            keys = tuple(k.strip() for k in shapes.pop().split(",") if k.strip())
    return {
        "reply envelope": tuple(doc),
        "fact keys": tuple(fact),
        "item fields": tuple(item),
        "slot-spelling fields": spells_out,
        "slot keys": keys,
        "abstention keys": tuple(abstention),
    }


def output_section():
    """A3 verbatim, with EVERY copied structural surface cross-checked against
    its Core owner, so no part of the answer shape can drift silently (§2)."""
    from driver.core.prepared_fact_v2 import (ITEM_FIELDS, NUMERIC_SLOTS,
                                              PreparedFactV2)
    from driver.core.slot_convert import SLOT_KEYS
    from driver.core.driver_write_cli import (V2_ABSTENTION_KEYS, V2_REPLY_KEYS)
    a3 = _section(_PKG, _OUTPUT)
    blocks = _fences(a3)
    if len(blocks) != 1:
        raise SystemExit(f"A3: expected one typed skeleton, found {len(blocks)}")
    try:
        declared = _skeleton_surfaces(blocks[0])
    except (ValueError, KeyError, IndexError) as e:
        raise SystemExit(f"A3: typed skeleton is not the expected envelope ({e})")
    owners = {
        "reply envelope": tuple(V2_REPLY_KEYS),
        "fact keys": tuple(PreparedFactV2._FACT_KEYS),
        "item fields": tuple(ITEM_FIELDS),
        # EVERY Core numeric slot must carry the marker, in Core's order.
        "slot-spelling fields": tuple(NUMERIC_SLOTS),
        "slot keys": tuple(SLOT_KEYS),
        "abstention keys": tuple(V2_ABSTENTION_KEYS),
    }
    for surface, owned in owners.items():
        got = declared[surface]
        if got != owned:
            raise SystemExit(
                f"SCHEMA DRIFT in {surface!r}: the PART A skeleton is not Core's "
                f"contract — extra={[k for k in got if k not in owned]} "
                f"missing={[k for k in owned if k not in got]} "
                f"order_only={sorted(got) == sorted(owned)}")
    return a3.rstrip() + "\n\n" + core_structure_card()


def build_prompt(role, headers=None):
    """One assembled prompt. Only the role header differs between roles."""
    headers = headers or role_prompt_headers()
    if role not in headers:
        raise SystemExit(f"unknown role {role!r}; A1 declares {sorted(headers)}")
    return (
        f"[ROLE]\n{headers[role]}\n\n"
        f"[RULES]\n{_section(_PKG, _RULES).rstrip()}\n\n"
        f"[OUTPUT]\n{output_section().rstrip()}\n\n"
        f"[BOUNDARY]\n{_fences(_section(_PKG, _BOUNDARY))[0].strip()}\n\n"
        f"[EVENT]\n{EVENT_PLACEHOLDER}\n")


def build(out_dir=_HERE):
    headers = role_prompt_headers()
    os.makedirs(out_dir, exist_ok=True)   # before the FIRST write, not after
    manifest, shas = [], {}
    for role in sorted(headers):
        text = build_prompt(role, headers)
        sha = hashlib.sha256(text.encode()).hexdigest()
        shas[role] = sha
        name = f"exp5_prompt_{role}.md"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)
        manifest.append({"role": role, "file": name, "sha256": sha,
                         "bytes": len(text.encode())})
    src = [{"title": t, "source": os.path.relpath(_PKG, _REPO), "heading": h,
            "sha256": hashlib.sha256(_section(_PKG, h).encode()).hexdigest()}
           for t, h in (("role headers", _ROLE_HEADERS), ("active rules", _RULES),
                        ("output envelope", _OUTPUT), ("boundary", _BOUNDARY))]
    doc = {"version": "v2-prompt-contract",
           "structure_owner": "driver.core (generated, not copied)",
           "event_placeholder": EVENT_PLACEHOLDER,
           "prompts": manifest, "blocks": src}
    with open(os.path.join(out_dir, "exp5_prompt_contract.manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    return shas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=_HERE)
    a = ap.parse_args()
    for role, sha in sorted(build(a.out).items()):
        print(f"{role}\t{sha}")
