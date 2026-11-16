# Exclude known metadata from numeric questions

**Verified:** on the live standard cohort of 9,167 transcripts, code can exclude verified speaker-header numbers from numeric candidate questions while preserving every digit in the stored speech. Keep the original text, speakers and timestamps visible as context and available for quotes. This is narrower than Claude's suggestion to hide the markers from the model altogether.

| Stored material | Utterances | Verified headers | Unmatched, unchanged | Numeric questions before → after |
| --- | ---: | ---: | ---: | ---: |
| Prepared remarks | 57,261 | 57,257 | 4 | 1,042,246 → 984,964 |
| Q&A | 384,582 | 384,507 | 75 | 936,722 → 552,158 |
| Total | 441,843 | 441,764 | 79 | 1,978,968 → 1,537,122 |

That removes **441,846 questions (22.3%)** in the numeric-question stage. The earlier six-call sample's roughly 35% metadata rate was not the whole-cohort rate. No model latency or accuracy improvement is claimed: changing a grouped request can change its answers and still needs testing in the complete procedure.

## Small implementation and native check

The source-owning ingestion code at `transcripts/EarningsCallTranscripts.py:329` constructs `speaker [rounded_start_time]: speech`. Q&A entries also store the speaker separately. The graph retains each source's own speaker map. Existing `scripts/driver_seed/relocate_probe/phase2/m1_transcript_census.py::SPEAKER` already recognizes this prefix, and `spoken_text` removes it.

The temporary adapter `../metadata_candidates.py` reuses that matcher, verifies the name against the source metadata (and Q&A entry speaker when present), and starts numeric candidate enumeration at the speech boundary. The existing helper returns joined text without original offsets; that is the only gap the adapter fills. No speaker-name list, finance terms, fuzzy matching or company-specific branch is added. Unmatched metadata keeps the original candidates.

Tests first reproduced the missing adapter, then an actual boundary defect: if speech touches the colon, filtering whole original tokens would lose the first spoken number. Starting native token enumeration at the body position fixed the whole boundary class. Tests cover matching headers, names containing digits, mismatches, absent metadata, body citations, header-like text inside speech, and no whitespace at the boundary. Positive controls accompany the exclusions.

The read-only live audit checked every included utterance: exact original offsets, equality with the native spoken-body path, and complete digit coverage. Every unmatched case is recorded with source/block/entry/reason in `live_audit.json`. The 79 unmatched headers were not repaired or discarded. Counts and native/adapter hashes reconcile in `verification.json`.

This is a preparation component, **not** guidance recall, complete extraction, or proof that the stored transcript equals the original publication. No source text, production code, model runtime or database content changed. No inference was run. The helper is not yet wired into a new full pipeline; the frozen prior experiments remain reproducible.
