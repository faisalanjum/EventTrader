# Golden set — the frozen key the Prepare benchmark grades against

**What it is.** 457 reviewed answer records (Step 3 of Prepare) over 249 development + 90 held-out
targets, with accepted alternatives, 5 excluded fields, source anchors into the original filings, and the scoring contract
(rules E1–E17). Reviewed by two independent reviewers; package **1134** is final (`CODEX_ROUND2_UPDATE_20261003.md` inside it).

**Where it lives (outside the repo, on purpose).** `/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/FINAL_KEY_FOR_CODEX_20261003_1134` — the answers, the originals (`bundled/packets/*/sources`) and the
raw model answers stay out of git. `PACKAGE.json` here pins the path and the SHA-256 of every file that matters; the package's
own manifest pins all 1,881 packet files. The package folder is immutable: corrections go through a new package, never edits.

**Rules.** `CONVERTER_COMPARISON.md`, `CLAUDE_KEY_README.md` (E1–E17 under "Equivalences and preservation rules") and
`CONTRACT_DECISIONS_R2.json` are verbatim copies of the package files; `check_package.py` fails if a copy drifts from the package.

**Check it.** `python3 benchmarks/prepare/golden/check_package.py` — verifies every recorded hash, then runs the package's own gate
(`VERIFY_PACKAGE.py`: files, packets, every packet source file, raw answers, verification stamps).

**Backup.** Everything under `/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002` (all packages, `bundled/`, raw answers) must be in backed-up storage; nothing of it is in
git. After a restore, run the check above; a changed byte anywhere fails it.

**Held-out answers are restricted** to reviewers: nobody building a converter reads them. The grader prints held-out results as
aggregates only unless `--heldout-detail` is passed, and no held-out record or file name appears in this folder (checked when the
copies were made).
