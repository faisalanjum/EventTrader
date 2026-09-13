# -*- coding: utf-8 -*-
"""The NEW explicitly versioned source-key task text (Codex SEQ 2063).

It builds ONE thing: the prefix a new source-only phase serves. That prefix is
the prefix this package already serves, with exactly TWO anchored spans
replaced. Nothing else moves, no frozen owner is edited in place, and no
historical prompt, script or result is relabelled.

Why each span moves, from the measured evidence:

  * SPAN A, owned by `HR._GROUP_ROLE` and appended to the served role by
    `SK.role()`, permits several facts from one target ONLY for "a sibling or
    a basis split". The served Rule 2 already requires independent causes to
    split. DRI transcript row 5 met both at once - two independently announced
    causes in one located target - and raised an open issue about the
    instruction clash rather than about the source. The closed list is
    replaced by a reference to the splits the RULES already require; the
    located-target-only scope and the ban on discovering adjacent facts are
    kept word for word.

  * SPAN B, owned by `F._task_section`, says ambiguity is an answer but never
    says a permitted uncertain outcome is COMPLETE. Reviewers therefore open an
    issue whenever a later owner might choose differently. The replacement says
    a permitted outcome that faithfully accounts for the source is complete and
    its residue belongs in the note or reason field the schema already has,
    and closes with the bounded restatement of the obligations that already
    bind (Codex SEQ 2064 item 1): a known wrong fact or identity, an omitted
    required row, and an unresolved required group or coverage decision. That
    wording deliberately does NOT say "required evidence you could not
    record", which could be read as a new ban on a lawfully omitted optional
    field or a counted abstention.

No examples, no word list, no semantic default, no new outcome field, and no
instruction to suppress an issue. The model still decides meaning.
"""
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / "unit_2009/owner"))
sys.path.insert(0, str(A7 / "unit_2023_source_correction"))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
F, K, SK, HR, INV = R.F, R.K, R.SK, R.HR, R.INV

VERSION = "a7-source-task/2063"

#: C2023's OWN base reader, captured before any successor swaps that
#: name at C2023. A phase that serves THIS repaired prefix binds it at
#: `C2023._served_prefix` so the existing prefix builder picks it up;
#: reading the live attribute here would then call this function again
#: and recurse forever (measured, attempt core_clo2065_b).
_C2023_SERVED_PREFIX = C2023._served_prefix

#: SPAN A - quoted from HR._GROUP_ROLE, so a reworded owner makes this anchor
#: miss and this module refuse, rather than silently serving the old text.
SPAN_A_OLD = ("Any one of them may yield more than one fact only\n"
              "where the RULES below already require a sibling or a basis split.")
SPAN_A_NEW = ("Any one of them may yield more than one fact only\n"
              "where the RULES below already require a split.")

#: SPAN B - quoted from F._task_section, same anchoring discipline.
SPAN_B_OLD = ("Genuine ambiguity is an ANSWER, not a failure. Record it rather than\n"
              "resolving it by guessing, and put anything that blocks a safe final\n"
              "answer in the open-issue branch.")
SPAN_B_NEW = "\n".join([
    "Genuine ambiguity is an ANSWER, not a failure. Apply the ordered rules",
    "above and the outcomes they already permit, and never resolve ambiguity",
    "by guessing.",
    "",
    "When a permitted outcome faithfully accounts for the source, that row is",
    "COMPLETE. Put whatever uncertainty remains in the note or reason field",
    "this schema already gives you.",
    "",
    "Use the open-issue branch only for a specific source or contract decision",
    "that these rules cannot lawfully settle, and say what prevents settlement.",
    "That a later reader might judge differently is not, by itself, an",
    "unsettled decision.",
    "",
    "The accepted result must not contain a known wrong fact or identity, omit",
    "a required row, or leave a required group or coverage decision unresolved.",
])


def _replace_once(text, old, new, what):
    """Anchored, exactly-once replacement. Anything else REFUSES.

    A silent miss would serve the old instruction under a new version name,
    which is the whole failure this module exists to prevent.
    """
    n = text.count(old)
    if n != 1:
        raise ValueError("the %s anchor appears %d times, not once: this "
                         "prefix is not the one this version was written "
                         "against" % (what, n))
    if new in text:
        raise ValueError("the %s replacement is already present" % what)
    return text.replace(old, new, 1)


def served_prefix(bound):
    """The served source-only prefix with exactly the two spans replaced."""
    base = _C2023_SERVED_PREFIX(bound)
    out = _replace_once(base, SPAN_A_OLD, SPAN_A_NEW, "group-role split")
    out = _replace_once(out, SPAN_B_OLD, SPAN_B_NEW, "ambiguity paragraph")
    return out


def provenance(bound):
    """What this version changed, measured - never asserted."""
    import collections
    base = _C2023_SERVED_PREFIX(bound)
    new = served_prefix(bound)
    return collections.OrderedDict([
        ("version", VERSION),
        ("served_prefix_sha256", K._sha(base)),
        ("new_prefix_sha256", K._sha(new)),
        ("bytes_before", len(base)), ("bytes_after", len(new)),
        ("spans_replaced", 2),
        ("span_a_owner", "build_kfields_hard_review._GROUP_ROLE via a4_source_key.role"),
        ("span_b_owner", "build_kfields_final._task_section"),
        ("group_role_owner_sha256", K._sha(HR._GROUP_ROLE)),
        ("task_section_owner_sha256", K._sha(F._task_section())),
        ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
        ("frozen_owners_edited", 0), ("model_calls", 0)])
