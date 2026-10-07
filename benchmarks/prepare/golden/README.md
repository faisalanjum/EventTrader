# Golden set — the frozen key the Prepare benchmark grades against

**What it is.** 457 reviewed answer records (Step 3 of Prepare): 249 development + 118 stratified control + 90 held-out
targets (eight supplemental targets are separate), with accepted alternatives, 5 excluded fields, source anchors into the original filings, and the scoring contract
(rules E1–E17). Reviewed by two independent reviewers; package **1134** was reviewed as final (`CODEX_ROUND2_UPDATE_20261003.md` inside it); **package 2 (`FINAL_KEY_FOR_CODEX_20261003_2014`)** supersedes it with the same 457 answers: SL Green table-context declarations in the support map, the split catalog pinned, and the contract addendum `CONTRACT_DECISIONS_R3.json` (six clarifications, proposed for Codex's check). **Package 3 (`FINAL_KEY_FOR_CODEX_20261004_0557`, active 2026-10-05 to 2026-10-07)**: three header-path corrections under the owner's decision (c), Park's reviewed header support, and the contract addendum `CONTRACT_DECISIONS_R4.json` (picture text approximate with critical-token flags, three declared page-number exclusions, continuous paragraphs by page mapping, the XML-route exception, the OCR adoption rule); the three changed records re-verified and stamped, everything else byte-identical to package 2. Codex approved it in round 14; the pointer was switched after his gate on the grader's round 19. **Package 4 (`FINAL_KEY_FOR_CODEX_20261006_1753`) is the active package since 2026-10-07**: the ten released held-out corrections of Codex's `CODEX_HELDOUT_R1_VERDICT` through the existing mechanisms (two `segment_or_basis` decisions, eight reviewed support declarations; named in the package's own manifest), the two changed records re-verified and stamped, the contract declarations R4 unchanged, everything else byte-identical to package 3. It is a regression-key change, not the answer key of a new exam. Codex approved it (`CODEX_JOINED_NUMBERS_VERDICT`); the pointer was switched after his integration gate on `9382f5d2e`.

**Where it lives (outside the repo, on purpose).** `/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/FINAL_KEY_FOR_CODEX_20261006_1753` — the answers, the originals (`bundled/packets/*/sources`) and the
raw model answers stay out of git. `PACKAGE.json` here pins the path and the SHA-256 of every file that matters; the package's
own manifest pins all 1,881 packet files. The package folder is immutable: corrections go through a new package, never edits.

**Rules.** `CONVERTER_COMPARISON.md`, `CLAUDE_KEY_README.md` (E1–E17 under "Equivalences and preservation rules") and
`CONTRACT_DECISIONS_R2.json`, `CONTRACT_DECISIONS_R3.json` and `CONTRACT_DECISIONS_R4.json` are verbatim copies of the package files; `check_package.py` fails if a copy drifts from the package.

**Check it.** `python3 benchmarks/prepare/golden/check_package.py` — verifies every recorded hash, then runs the package's own gate
(`VERIFY_PACKAGE.py`: files, packets, every packet source file, raw answers, verification stamps).

**Backup.** Everything under `/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002` (all packages, `bundled/`, raw answers) must be in backed-up storage; nothing of it is in
git. After a restore, run the check above; a changed byte anywhere fails it.

**Held-out answers are restricted** to reviewers: nobody building a converter reads them. The grader prints held-out results as
aggregates only unless `--heldout-detail` is passed, and no held-out record or file name appears in this folder (checked when the
copies were made).
