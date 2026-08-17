# QF-01 choice-v2 development test

Goal: test only whether Qwen chooses the correct source-table cell.

```text
real HTML → clean numbered choices → Qwen number/null → exact code reconstruction
```

The source parser builds every choice without the hidden key. Qwen never copies
IDs, labels, values, or headers. The hidden key only proves that the expected
cell exists once and scores the final choice.

Prepared state:

- 93 separate calls; no batching;
- reasoning off, temperature 0, fixed 65,536 context;
- one completed answer only; no answer retry or repair;
- 93/93 expected cells found exactly once in source-built choices;
- 12 focused tests and the original 37-check Fiscal validator pass;
- transport failures can resume, but completed answers can never be retried;
- no Qwen development call has run.

After a separate owner GO:

```bash
cd /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/QwenTests/table_evidence/choice_v2
/home/faisal/EventMarketDB/venv/bin/python choice_v2.py verify
/home/faisal/EventMarketDB/venv/bin/python choice_v2.py run
/home/faisal/EventMarketDB/venv/bin/python choice_v2.py score
```

Passing means 93 correct, 0 wrong, 0 abstained, and 0 invalid. Because these
cases have already been opened for development, even 93/93 is not an unseen
production certification.
