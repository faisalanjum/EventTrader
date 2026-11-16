# Claude-supplied review material

Everything here except this page is an unchanged copy of `/tmp/claude_decider_review_20261115/`. Start with the supplied [README.txt](README.txt).

| File | What it establishes |
| --- | --- |
| [reviews.json](reviews.json), [brief.md](brief.md) | Three reviews / 66 findings about the earlier summary plan and Claude's value-first draft, **not the later detailed strategy**. Findings require independent verification. |
| [final_review_20261115.md](final_review_20261115.md) | Later supplied review recommendations; not proof of implementation or success. |
| [draft_inventory_69.json](draft_inventory_69.json) | Draft 75-row inventory: 69 core and six borderline entries. Not an adjudicated quote-level answer key. |
| [locate_boundaries.py](locate_boundaries.py) | Short-text Locate test; normally makes model calls. Its `--compare` path compares saved files. |
| [locate_before.json](locate_before.json), [locate_after.json](locate_after.json) | Supplied before/after punctuation-fix evidence: 45 → 56 of 60 expected short-text spans; numeric spans 28/28 after, four name misses remain. This does not measure complete transcript extraction. |
| [USAGE.md](USAGE.md) | Mac runtime usage notes as supplied; not a new check of the running service. |

**Replay limit:** `4c_ref_answers.json`, `eval_set.json` and `inputs_acme_report.json` are referenced by the external test but absent from the supplied package. Existing results are preserved; a full rerun is not self-contained. No external model tests were repeated to create this archive.

Codex's saved responses to the recommendations are in [all_66_dispositions.json](../experiment/all_66_dispositions.json), [final_review_assessment.md](../experiment/final_review_assessment.md) and the experiment's history notes. The [latest results summary](../readme.md) separates measured outcomes from proposals.
