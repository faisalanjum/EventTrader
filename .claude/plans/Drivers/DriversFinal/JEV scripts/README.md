# JEV scripts

The scripts, prompts and frozen labels behind `../JEV.md` (session of 2026-09-29). Read `../JEV.md` first: it has the results, the prompts word for word, and the traps. Nothing here writes to Neo4j or the repo; every Jev call costs cents.

## How to run
- `cd` into this folder; scripts use relative file names.
- Jev key: read from `/home/faisal/EventMarketDB/.env` (`TYPESAFE_API_KEY`); never stored in these files.
- Scripts that read Neo4j (`pull_*`, `prelabel_*`, `build_more.py`, `build_extra.py`) need `/home/faisal/EventMarketDB/venv/bin/python3` (it has the `neo4j` driver). The rest run with `python3`.
- Not included, regenerate: `h1_raw.json` (run `pull_h1.py`, needs Neo4j) and every `results_*.json` (rerun the `run_*.py` for that test; the whole session cost about $1.1, so any one test is cents).

## Shared modules
`jevlib.py` input builder (§3.8) · `prompts_v3.py` API call + round-1 prompts · `variants.py` prompts V0 to V6 · `old_prompts.py` first prompts · `surprise_prompts.py` · `card_prompts.py` · `more_prompts.py` (baseline, horizon, slice kind; `HORIZON2`/`SLICE2` are the post-ruling versions).

## Each test, in run order (section of JEV.md)
| Test | Scripts |
|---|---|
| Fact type, round 1 (§3.1–3.4) | `jev_type_test.py`, `build_v3.py`, `run_v3.py`, `run_h3.py`, `build_h5.py`, `run_v4.py`, `report.py` |
| Redo with the first reviewer's rulings (§3.5–3.6) | `prepare_redo.py`, `run_redo.py`, `score_redo.py`, `score2.py`, `ablate.py`, `score_ablate.py`, `triage_final.py`, `qm2.py` |
| Second reviewer's rulings, V4 to V6 (§3.11) | `build_rekey.py`, `run_rekey.py`, `score_rekey.py`, `build_extra.py`, `run_extra.py`, `run_v5.py`, `run_v6.py`, `score_v5.py` |
| Surprise (§3.12) | `pull_surprise.py`, `prelabel_surprise.py`, `run_surprise.py`, `score_surprise.py` |
| Fact card: state, unit, span (§3.13) | `build_card.py`, `run_card.py`, `score_card.py` |
| Baseline, horizon, slice kind (§3.14–3.15) | `build_more.py`, `pull_horizon.py`, `prelabel_horizon.py`, `run_more.py`, `score_more.py`, `rescore_keys.py`, `run_rescore.py` |
| The 220-rule fit map (§4) | `classify.py` (writes `rules_vs_jev.json` / `.md`) |

## Frozen labels and inputs (JSON)
Round 1 and redo: `fixtures*.json`, `redo_items.json`, `items_final.json`, `items_extra.json`, `adjudication_verdicts.json`, `adj_index.json`. Surprise: `surprise_candidates.json`, `surprise_items.json` (hash `b43d406630dce0a8`). Fact card: `card_items.json`, `card_adjudicated.json`. Baseline/horizon/slice: `items_more.json` (`ca1fa5c4364f6b7a`), `items_more2.json` (slice keys after my rulings, `0e425c40d60ac99c`), `horizon_candidates.json`, `items_horizon.json` (`ad311b3a4e8e1105`). Prompts: `V6.json` (recommended candidate), `QC4.json` (round 1 final).

## Traps
- Never let a label field share a name with the input field (`build_card.py` had this bug; labels are now `L_*` and every runner asserts the input).
- Answer keys are the earlier model's labels (`experiments/runs/kf-*`), the older `GuidanceUpdate` fields (not a valid key), or my own labels frozen before each run. Check `JEV.md` for which is which.
- Some scripts were edited in place during the session; use the run order above rather than the file names alone.
