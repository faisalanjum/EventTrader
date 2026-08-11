"""NAME-13 per-X spell-out residue guard (owner ruling 2026-08-11).

The owner deleted BOTH the sole `eps` canonical-name exception and the
open-class "familiar acronyms" sentence, so every stated per-X denominator is
written out (`earnings_per_share`). This file guards that the retired wording
does not survive anywhere it would still be READ AS LAW or SERVED TO A MODEL.

SCOPE IS A CLOSED, HARD-CODED LIST OF 8 FILES, and that is deliberate:

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
SERVED_CONTRACT = "experiments/harness/exp5_item_contract.md"


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


def test_the_SERVED_item_contract_still_carries_it_because_that_hold_is_DELIBERATE():
    """THE ONE ACCEPTED EXCEPTION, asserted POSITIVELY rather than skipped.

    `exp5_item_contract.md` is a GENERATED, hash-pinned artifact. Regenerating
    it belongs to the separate "Core contract migration + freeze" step, because
    its generator and the launch manifest are still on the retired 37-field
    PreparedFactV1 shape while the live contract is v2 (34 total / 32
    model-owned). Editing the contract here would change its sha and break the
    very pins that migration defers — so the reason lives in THIS file and the
    contract stays byte-identical.

    While it still serves the old sentence, K-fields GO#1 stays disabled and
    unfired; drafters must never be run on stale law.

    When the migration lands, this assertion FLIPS to zero. That flip is the
    guard telling you the hold is over — update it deliberately; do not paper
    over it, and do not pre-emptively relax it to make a future run green.
    """
    assert RETIRED in _read(SERVED_CONTRACT), (
        f"{SERVED_CONTRACT} no longer carries the retired sentence. If the EXP-5 "
        f"contract migration has LANDED, this is correct — move this file into "
        f"CLEAN_SIX and delete this test. If it has not, the served contract was "
        f"edited out of band and its hash pins are now wrong.")
