"""NAME-13 per-X spell-out residue guard (owner ruling 2026-08-11).

The owner deleted BOTH the sole `eps` canonical-name exception and the
open-class "familiar acronyms" sentence, so every stated per-X denominator is
written out (`earnings_per_share`). This file guards that the retired wording
does not survive anywhere it would still be READ AS LAW or SERVED TO A MODEL.

SCOPE IS A CLOSED, HARD-CODED LIST OF 9 FILES, and that is deliberate:

  * The tree carries ~777 untracked files (evidence dumps, frozen run
    artifacts, superseded drafts). A repo-wide scan would be slow and would
    fail on history that is SUPPOSED to keep the old words.
  * So there is no "any new file" clause and no exemption list to maintain.
    A file is checked only if it is named below. A new live surface is added
    here deliberately, by a human, or it is not guarded — that is a smaller
    and more honest failure mode than a walker with a growing skip-list.

The retired sentence is never reproduced in full in the guarded records
themselves; those describe it instead, so this guard cannot be defeated (or
tripped) by a document quoting the very rule it retired.
"""
import io
import os

import re

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_DRIVERS = os.path.dirname(os.path.dirname(_HERE))          # .claude/plans/Drivers

# The retired open-class sentence, by its stable core phrase.
RETIRED = "already include the denominator"

# The new Note, required VERBATIM in every served rulebook. Kept as one string
# so a partial or paraphrased rollout fails instead of half-passing.
NOTE = (
    "- **Note:** Write the per-X denominator out in the name: \\`EPS\\` / "
    "\"earnings per share\" → \\`earnings_per_share\\`; \\`DPS\\` → "
    "\\`dividend_per_share\\`. If you cannot verify what a per-X acronym expands "
    "to, do not guess — skip that candidate. Per-X only; non-per-X terms "
    "(\\`ebitda\\`, \\`free_cash_flow\\`, \\`fed_rate\\`) are unaffected."
)

# 1-6: live law, the three served rulebooks, and the two decision records.
CLEAN_SIX = (
    "FinalDesign/FINAL_DESIGN.md",
    "workflows/gate.js",
    "workflows/reconcile.js",
    "workflows/menu_build.js",
    "FinalDesign/STATUS_AND_HISTORY.md",
    "experiments/WORKORDER_STATUS.md",
)
RULEBOOKS = ("workflows/gate.js", "workflows/reconcile.js", "workflows/menu_build.js")
PACKAGE = "experiments/harness/exp5_rev4_package.md"
# BOTH generated role prompts are now the served surface: the single stale V1
# card is deleted, and one builder emits one envelope for both roles.
SERVED_PROMPTS = ("experiments/harness/exp5_prompt_drafter.md",
                  "experiments/harness/exp5_prompt_producer.md")


def _norm(text):
    """Whitespace-normalised: the prompts hard-wrap their sentences, so a
    line-sensitive check would miss a phrase that is present."""
    return re.sub(r"\s+", " ", text)


def _read(rel):
    path = os.path.join(_DRIVERS, rel)
    if not os.path.exists(path):
        pytest.fail(f"guarded file is missing: {rel} — the closed list is stale, fix the list")
    return io.open(path, encoding="utf-8").read()


@pytest.mark.parametrize("rel", CLEAN_SIX)
def test_the_retired_acronym_sentence_is_GONE_from_live_law_and_records(rel):
    """Zero occurrences. Live law, every served rulebook, and both records."""
    n = _read(rel).count(RETIRED)
    assert n == 0, f"{rel} still carries the retired per-X acronym rule ({n}x)"


@pytest.mark.parametrize("rel", RULEBOOKS)
def test_every_served_rulebook_carries_the_new_spell_out_Note_VERBATIM(rel):
    """Deleting the old rule is only half the ruling — the new one must be served."""
    assert NOTE in _read(rel), f"{rel} is missing the NAME-13 spell-out Note verbatim"


def test_the_three_rulebooks_carry_the_IDENTICAL_Note():
    """The three builders must not drift apart on the rule they serve."""
    got = {rel: _read(rel).count(NOTE) for rel in RULEBOOKS}
    assert set(got.values()) == {1}, f"Note count per rulebook must be exactly 1 each: {got}"


def test_the_package_keeps_the_retired_sentence_ONLY_in_its_frozen_ledger():
    """`exp5_rev4_package.md` records its own history. The REV-4F/4G ledger
    entries QUOTE the retired sentence as the thing that was changed, and
    rewriting history to match a later ruling is exactly what an audit ledger
    must never do. So the sentence is allowed there — and NOWHERE else in the
    file, which is what actually gets served or scored."""
    text = _read(PACKAGE)
    hits = [i for i, line in enumerate(text.splitlines(), 1) if RETIRED in line]
    assert len(hits) <= 2, (
        f"the retired sentence appears on {len(hits)} lines of {PACKAGE} "
        f"(lines {hits}); at most the two frozen REV-4F/4G ledger lines may keep it")
    for ln in hits:
        line = text.splitlines()[ln - 1]
        assert "REV-4" in line or line.lstrip().startswith("("), (
            f"{PACKAGE}:{ln} keeps the retired sentence but is not a frozen "
            f"REV-4F/4G ledger line: {line.strip()[:120]}")


def test_both_SERVED_prompts_carry_the_CURRENT_perX_rule_and_not_the_retired_one():
    """THE HOLD IS OVER, UPDATED DELIBERATELY (Codex SEQ 1085).

    This assertion used to require the served card to STILL carry the retired
    open-class sentence, because its generator was stuck on the V1 shape and
    regenerating it would have broken the pins that migration deferred. That
    migration has now landed: the stale card is deleted and one Step-2 builder
    emits both role prompts on the V2 shape.

    So the guard flips, as its own note said it would — it is not relaxed and not
    deleted. It now requires, of BOTH prompts, that the retired sentence is gone
    and the owner-approved spell-out/abstain rule is present. The required text is
    reused verbatim from the NOTE above; no acronym list or interpretation is
    added here. Comparison is whitespace-normalised because the prompt hard-wraps.
    """
    required = [_norm(x) for x in (
        'Write the per-X denominator out in the name',
        'If you cannot verify what a per-X acronym expands to, do not guess',
    )]
    for rel in SERVED_PROMPTS:
        flat = _norm(_read(rel))
        assert _norm(RETIRED) not in flat, (
            f"{rel} still serves the RETIRED open-class sentence")
        for phrase in required:
            assert phrase in flat, (
                f"{rel} does not carry the current owner rule: {phrase!r}")
