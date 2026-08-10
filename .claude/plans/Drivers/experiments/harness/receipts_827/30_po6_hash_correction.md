# CORRECTION — one hash mis-transcribed in commit 0ae6453b (P-O6 PREP)

Commit `0ae6453b` ("P-O6 PREP COMPLETE") states the regenerated receipt hashes.
One of the three is WRONG in that message. Amend/rewrite is forbidden, so the
correction lives here, where the index will carry it.

| receipt | commit message says | TRUE sha256 prefix |
|---|---|---|
| 15_reviewer_case_map.json | `2c918f96` | `2c918f96` ✅ |
| 21_hardcoding_inventory.json | `9cf6e48c` | `9cf6e48c` ✅ |
| 22_decision_rules.json | `a6aacd87` ❌ | **`a6aaccd8`** |

Full: `a6aaccd87149c29d...` — I dropped one `c` reading it off a terminal line
by eye instead of recomputing it into the message. The digits are otherwise in
order, which is exactly what makes this kind of error survive a glance.

## What is and is not affected

* The FILES are correct and unchanged. Nothing was regenerated wrongly; only the
  human-readable line in a commit message is wrong.
* The hash chain still verifies: `22_decision_rules.json` records
  `derived_from_sha256 = 9cf6e48ce36d23a7...` and `21_hardcoding_inventory.json`
  really does hash to `9cf6e48c...`. That binding was checked mechanically, not
  by eye, and it holds.
* `03_commands_and_hashes.txt` derives every hash it prints. It was regenerated
  after these three and carries the TRUE value for 22.
* The authorized delta ledger recomputes all 116 hashes from disk; it is
  unaffected.

## How it was caught

The SENDGATE claim verifier. Every hex token in an outbound message must be
backed by a claim that recomputes it from disk, so the wrong prefix failed
before the message could be sent. The same discipline was not applied to the
commit message, which is how it got in there in the first place.

## The rule this reinforces

A hash written by a human is a claim, not a measurement. Recompute it into the
text; never read one off a scrollback line.

A second, smaller error surfaced in the same check: a claim command tried to
read `15_reviewer_case_map.json` out of commit `1592bab4`, where it does not
exist — that file was staged-added and first COMMITTED at `0ae6453b`. The
"before" hash quoted for it (`6b67c4ca`) came from disk prior to regeneration,
which is legitimate, but the commit it was attributed to was not.
