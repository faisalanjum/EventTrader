# Continuation — sentence comparison complete

The owner asked what functionality works versus remains unreliable. Answer using `capability_status.md`; do not give an invented completion percentage or claim complete extraction.

Exec session **65010** completed successfully and was collected. **No inference is still running.** Do not restart it. All 673 local answers were received and checked against frozen request/reference hashes and original positions. Model `pplx-decider-v1.3:8bit`; 729.94 seconds, 60,073 input tokens, two native sequences; finished 2026-11-15 19:26:40 EST.

Read `sentence_screen/README.md` and the saved scores/source review. At .25: 21/22 positive controls retained, 8/8 negative controls excluded, 104/673 sentences selected. All 12 positive-labelled parent passages retained, but S483's adjusted-margin exclusion still missed. Other selected statements are past/current results or ambiguous outlook; passing eight negative controls does not establish precision. Post-result source review covers all 104 selections, without changing the frozen controls.

The three structural alternatives now have results: passages, existing utterances, direct sentences. Sentence targeting has a coverage/cost tradeoff, but no safe discard or full-record result. Do not stack another prompt repair or tune the threshold to S483. Four extraction classes remain open: worded values, implied measure association, several worded forecasts, and complete modifier/assumption copying. The earlier bounded repair chains stay stopped.

`capability_status.md`, `procedure_reconciliation.md` and `progress.md` are current. The main strategy, rulebook and local model adapter hashes are unchanged. No production/database changes, hosted fallback, commit or push. No subagents. Active goal remains incomplete; no external blocker established.

Next work must reconcile actual complete-record requirements and a coherent procedure from the measured components, rather than relaunch single-example probes or call retained source text a completed record. Existing source inventories and review material already exist; do not rebuild them from scratch. Preserve every unresolved outcome and the current-rule distinction from legacy guidance rows.
