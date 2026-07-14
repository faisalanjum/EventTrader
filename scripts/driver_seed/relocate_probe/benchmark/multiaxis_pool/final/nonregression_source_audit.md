# Read-only non-regression and source audit

Date: 2026-07-13

## Short result

- The fresh regression rerun passed every saved floor.
- Annual: 132 correct, 2 wrong, 8 abstained among 142 gradeable cases; 98.5% precision and 93.0% recall.
- Quarterly: 37 correct, 1 wrong, 2 abstained; 97.4% precision and 92.5% recall; no year-to-date picks.
- Headline transcript: 7 correct, 0 wrong, 33 abstained; 100% precision and 17.5% recall.
- A new audit of clearly identified one-axis quarterly cases found 15/15 correct. This is an audit of the saved run, not a separately certified split.
- My audit wrote only under `/tmp`. Its first before/after `git status` hash matched: `91917f47a75db0ce815390fbff28643973244366dc85b7490c59b486ff58f28b`. Later, a separate running process changed project files, so the whole shared workspace did not remain unchanged. I did not stop, edit, or undo that work.

## Saved files checked

| set | truth rows | batch files | output rows | truth SHA-256 | output SHA-256 |
|---|---:|---:|---:|---|---|
| annual validation | 150 | 150 | 150 | `574d419c71d2536a49b310ec7af95f4957019abd579003af9c653cc22a78e01f` | `4ed050916104bb7072c7c30392ebfa98d10e2c21596c0ac2a065623c8321544d` |
| quarterly | 40 | 40 | 40 | `ca32cf7421ecda0acfad5e131d7d41675d1d2af9ec54d83f5461b4fffeeb13b3` | `6f7d731d676112257ea9d67b1d900e177d94ff813d3e07e0aab4e78aa05577a5` |
| headline transcript | 40 | 40 | 40 | `cb76f0a2f77f455b0f2fcc4ff4dcc023435db927ea90903fb21a82a09344ccae` | `64b01a7470c3a0b50d42b7ceb5da952a5defd48f639b2ab33c12aab1cb0c2c17` |
| older detailed transcript | 40 | 40 | missing | `ec9e66b5edb480bc3272ff88546cffe3314a217b898d5d4e30c0d25056dd7589` | missing |

The older detailed transcript result cannot be rerun because `relocate_out_transcript.json` is absent. Its 2-correct / 0-wrong result exists only as a saved note in `STATE.md`.

## Fresh grader reruns

| set | correct | wrong | abstain | precision | recall | extra |
|---|---:|---:|---:|---:|---:|---|
| annual validation | 132 | 2 | 8 | 98.5% | 93.0% | 8 more cases were not gradeable because the reference value was absent from the current filing/release source |
| quarterly | 37 | 1 | 2 | 97.4% | 92.5% | 0 year-to-date picks |
| headline transcript | 7 | 0 | 33 | 100.0% | 17.5% | all 7 emitted quotes passed the saved quote and number gates |

`regress.py` calls the transcript headline set `headline`. It does cover that transcript set, but it does not cover the older detailed transcript set.

The frozen benchmark was rerun again after the separate process changed `link_lib.py` and `grade_quarterly.py`; it still passed with the same scores. That checker snapshot had these hashes:

- `link_lib.py`: `c31dc75f6b87f706e4c6bd1b7569429a0e335f5e5eacb745c2686963b829de5e`
- `grade_quarterly.py`: `5a8919e7e7fe412648b6fdfa6fa1684e8999627d9d22cd0410560118606372ed`
- `regress.py`: `96a2d8c22491953cceac3df37e796592809eed18a5f93c00473843f45539d999`

## Source coverage

Here, “rounded numeric” only means that a compatible number occurs somewhere. It is an upper bound, because the number can belong to another metric.

| set | full source, lossless | full source, rounded numeric | saved candidates, lossless | saved candidates, rounded numeric | saved output |
|---|---:|---:|---:|---:|---|
| annual validation | not separately queried | not a pure source count; the annual grader marked 142/150 gradeable using correct outputs or a broader filing/release/XBRL check | 138/150 | 131/150 | 132 correct |
| quarterly | not separately queried | not separately queried | 39/40 | 39/40; either helper covers 40/40 | 37 correct |
| headline transcript | 4/40 | 13/40 | 4/40 | 11/40 | 7 correct |
| detailed transcript | 2/40 | 14/40 | 2/40 | 8/40 | output missing |

For the headline transcript set, four saved candidate batches had a matching number but the system abstained. Inspection showed unrelated look-alikes, such as `$160 million` for another expense when the target metric was depreciation. Therefore 11/40 is not 11 true answers.

The saved independent 2+-XBRL-axis audit was inspected but not rerun. It has 156 cases: 153/156 have a rounded target number in the whole filing source, 130/156 have it in saved candidates, and 117/156 also have the saved identity words. Its raw XBRL axis counts are 117 two-axis, 34 three-axis, and 5 four-axis cases. These axes were not fully classified as business versus accounting axes, so this is source coverage, not proof of multi-business-slice behavior.

## Clean headline and one-axis audit

The old quarterly `type` field is not a real axis count; it used the number of words in a member name. I therefore used the saved identity reconstruction and kept only rows with exactly one identity choice.

| clean subset | cases | candidate coverage | correct | wrong | abstain | precision | recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| headline total, 0 axes | 11 | 11/11 | 10 | 0 | 1 | 100% | 90.9% |
| one axis | 15 | 15/15 | 15 | 0 | 0 | 100% | 100% |

This reconstruction excludes 12 of the 40 quarterly rows because their identity was missing or had more than one choice. It uses the same case ids, tickers, periods, and values as the saved quarterly set; five metric labels are from the earlier naming version. Treat these numbers as a new audit, not a frozen certification.

The separate 40-case headline transcript builder explicitly selected zero-axis facts, so that population is also a real headline-total test. Its low recall is caused by transcript content, not axis confusion.

## Real source-transfer cases

The live read-only trace found that all seven emitted headline targets came from transcript candidates. Five lock rows were found in the filing and not the press release; two lock rows came from the press release instead.

Small real filing-to-transcript set:

| id | company | period | metric | source value | transcript answer |
|---:|---|---|---|---:|---|
| 0 | AA | 2025-09-30 | revenue | 2,995,000,000 | `$3 billion` |
| 4 | AAPL | 2025-12-27 | revenue | 143,756,000,000 | `$143.8 billion` |
| 35 | ADBE | 2026-02-27 | revenue | 6,398,000,000 | `$6.40 billion` |

The raw source trace found two “pure” filing-to-press-release paths, where the lock text was found only in the filing and the chosen target candidate only in the press release. One of them is not a clean functional test: ACMR id 19 used the known-bad `8.4%` percentage row as its lock context, even though it later reached the right release table.

| id | company | lock period | target period | metric | answer |
|---:|---|---|---|---|---|
| 0 | AA | 2025-06-30 | 2025-09-30 | revenue | `2,995` million |
| 19 | ACMR | 2024-09-30 | 2025-03-31 | advanced-packaging revenue | `15,148` thousand; exclude from a clean test because its lock context is wrong |

Two more AEIS cases have valid filing lock rows and release-only target candidates: id 37, Semiconductor Equipment revenue `196.6` million, and id 38, Industrial and Medical revenue `71.2` million. Their lock rows also occur in the earlier press release, so they are weaker proof of a filing-only start.

Recommended small filing-to-release test set: AA id 0 plus AEIS ids 37 and 38. Keep ACMR id 19 only as a negative test for rejecting a bad lock context.

## Saved checks versus new work

Saved-file checks:

- row counts, batch counts, and hashes for the three benchmark sets;
- absence of the older transcript output;
- the independent 156-case multi-axis source report.

New read-only reruns:

- `regress.py` and the three individual graders;
- value-presence checks over saved candidates;
- clean zero-axis and one-axis grading using reconstructed identities;
- live transcript source coverage and filing/release/transcript source tracing.

## Exact commands

```bash
git status --porcelain=v1 | sha256sum

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -B scripts/driver_seed/relocate_probe/regress.py

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -B scripts/driver_seed/relocate_probe/grade.py --set validation --root scripts/driver_seed/relocate_probe/benchmark

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -B scripts/driver_seed/relocate_probe/grade_quarterly.py --set quarterly --root scripts/driver_seed/relocate_probe/benchmark

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -B scripts/driver_seed/relocate_probe/grade_quarterly.py --set headline --root scripts/driver_seed/relocate_probe/benchmark

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -B /tmp/relocate_multi_axis.mrogHs/audits/nonregression_source_audit.py --live --output /tmp/relocate_multi_axis.mrogHs/audits/nonregression_source_audit.json

sha256sum /tmp/relocate_multi_axis.mrogHs/audits/nonregression_source_audit.py /tmp/relocate_multi_axis.mrogHs/audits/nonregression_source_audit.json
```

Audit script SHA-256: `bca7e7271fa81d1597b86e75605e198ebaddaeb12f1419d5795cb4c9566faa86`

JSON result SHA-256: `cbd61401d4abc8590ccd627f61c9cc2292550546041469f519b4e628a1d8f071`

## Documentation mismatches found

- The first annual table in `STATE.md` still says 97.8% / 92.3%; the current saved regression floor and fresh result are 98.5% / 93.0%.
- The older detailed transcript note says 37 pairs, while the current truth and batch folders contain 40. Because its output is missing, the saved 2/2 claim cannot be regraded.
- Quarterly per-`type` results must not be described as real per-axis results. The old labels are word-count labels, not axis counts.

## Concurrent workspace activity

Near the end of the audit, an external Claude process was still running `prep_oracle.py --n 40` followed by `prep_headline.py --n 40` directly in the project. It rewrote non-benchmark probe files and changed the two checker files named above. The frozen `benchmark/` artifacts used here kept the hashes listed in this report. This audit therefore proves the benchmark result for the named artifact and checker hashes; it does not claim that every project file stayed still during the run.
