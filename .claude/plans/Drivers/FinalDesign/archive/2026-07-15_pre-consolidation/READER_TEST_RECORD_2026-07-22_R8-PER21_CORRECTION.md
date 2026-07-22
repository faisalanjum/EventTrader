# CORRECTION — 2026-07-22 — the R8-PER21 first run's PASS is WITHDRAWN on regrade

**This file supersedes the VERDICT of `READER_TEST_RECORD_2026-07-22_R8-PER21.md` (that record is preserved
unedited beside this one, append-only law). Corrected verdict: 9/10 — Q2 FAIL → the certification claimed
for commit `c87d81bf60d6f9cc0ef9e7c34274ff690754f4fc` DOES NOT STAND.** The regrade was triggered by an
external (ChatGPT) review; the owner ordered the read-only reproduction and this correction sequence.

## 1. The regrade (the locked rule applied without rescue)

- The reader's Q2 write step listed, for the official text-only 8-K fixture:
  `edges OF_DRIVER(...)/FROM_SOURCE/HAS_PERIOD/MAPS_TO_MEMBER(slice_part product:iphone)` — a DEFINITE,
  unconditioned assertion, in the same sentence that DID condition its other optional items ("born-complete
  **if** revenue's first fact"; "**best-effort** `MAPS_TO_CONCEPT`").
- The law: `MAPS_TO_MEMBER` "needs both axis and member" (FINAL_DESIGN §5.2, the member-link enrichment
  clause). The fixture supplies no XBRL context; the reader named neither an axis nor a member node — it
  could not, none exists in the fixture. The checklist requires citing the clause whose condition the
  fixture actually satisfies; this condition is not satisfied.
- The original grade's defenses — "§7.3 says zero-or-more on any lane", "the fixture doesn't state XBRL
  context is absent", "the reader states the condition in its Q7" — are RESCUE READINGS. The locked grading
  law ("most-natural parse governs; a false fact on that parse = FAIL; **no rescue readings**") forbids all
  three: cardinality is not a presence license; an invented unstated possibility is a rescue; a generic
  caveat elsewhere does not repair a definite claim here. The R12-era certified answer for the SAME fixture
  listed only `OF_DRIVER`/`FROM_SOURCE`/`HAS_PERIOD` + the best-effort concept link — the correct treatment.
- Materiality: an engineer following the failed walk would mint member links from text slices — the exact
  behavior the step-7 member-link law (fact-level XBRL verification; refs never trusted) exists to block.
- Q1, Q3-Q10 grades stand as recorded, including the three PER-21 delta reads (boundary sentence ·
  pairing-CLOSED + financial-classification OPEN items · crosswalk row), which were exact.

## 2. Two process findings owned with this correction

1. **The record commit `6e4b0db` broke R8(c)'s letter** — "the record added AFTER the test without changing
   the seven tested files" (STATUS §4 R8(c)) — by bundling STATUS truth-line edits with the record. Proof:
   `git diff c87d81b..6e4b0db` across the seven pinned files touches exactly one (STATUS, 11 lines); the
   other six are byte-identical. The rerun below uses the conditional-pointer mechanism (the run-15
   pointer-before-record pattern) so no post-test edit of any tested file is ever needed.
2. **"Battery green at every commit" was overstated** in session reporting: measured runs were at the
   pre-sequence tree, the post-`cad2b8f` tree, and the post-`6e4b0db` tree — commits `2fbae3a` and
   `c87d81b` were argued green by construction, not separately checked out and run. Wording corrected;
   the rerun's battery runs AT the tested commit.

## 3. The repair (owner GO, sequence locked)

Pre-test commit = THIS correction file + the STATUS truth-fix (the false "DISCHARGED: PASS 10/10" sentence
replaced by a conditional discharge naming the planned rerun record — no failure specifics in STATUS, so
the fresh reader cannot be coached; the detail lives only in this archive file, which the prompt forbids
the reader to open). Then: full battery at that exact commit → ONE fresh blank-context reader, prompt
byte-identical to the official set (no hint of the previous mistake; the member-edge bar lives in GRADING
only) → ONE result-only commit adding `READER_TEST_RECORD_2026-07-22_R8-PER21-run2.md` (PASS or FAIL),
touching none of the seven tested files. PASS requires 10/10 AND 7/7 unchanged pins. On PASS the
conditional sentence in STATUS becomes true with no further edit; on FAIL the result is recorded and work
stops for owner adjudication. Push remains blocked (owner order + the Fiscal FinalPlan standing hold).
